"""
Trading Logic Core (Repo 02)

Автономное ядро, которое:
 - читает активные стратегии из Supabase
 - получает рыночные данные (минимально: Binance public klines)
 - вычисляет индикаторы по шаблонам
 - генерирует сигналы LONG/SHORT только при точном выполнении условий
 - сохраняет "логику рассуждений" (reasoning logs) в decision_logs
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from database import db
from services.strategy_manager_service import get_strategy_manager

logger = logging.getLogger(__name__)


# ----------------------------- utils -----------------------------


def _tf_to_binance_interval(timeframe: str) -> Optional[str]:
    tf = (timeframe or "").strip().lower()
    mapping = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1d",
        "3d": "3d",
        "1w": "1w",
    }
    return mapping.get(tf)


def _tf_to_minutes(timeframe: str) -> Optional[int]:
    tf = (timeframe or "").strip().lower()
    if tf.endswith("m"):
        try:
            return int(tf[:-1])
        except Exception:
            return None
    if tf.endswith("h"):
        try:
            return int(tf[:-1]) * 60
        except Exception:
            return None
    if tf.endswith("d"):
        try:
            return int(tf[:-1]) * 60 * 24
        except Exception:
            return None
    if tf.endswith("w"):
        try:
            return int(tf[:-1]) * 60 * 24 * 7
        except Exception:
            return None
    return None


def _sma(values: List[float], period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def _std(values: List[float], period: int) -> Optional[float]:
    m = _sma(values, period)
    if m is None:
        return None
    window = values[-period:]
    var = sum((x - m) ** 2 for x in window) / period
    return math.sqrt(var)


def _ema_series(values: List[float], period: int) -> Optional[List[float]]:
    if period <= 0 or len(values) < period:
        return None
    k = 2 / (period + 1)
    ema: List[float] = []
    # seed with SMA
    seed = sum(values[:period]) / period
    ema.append(seed)
    for price in values[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def _ema_last(values: List[float], period: int) -> Optional[float]:
    s = _ema_series(values, period)
    return s[-1] if s else None


def _rsi(values: List[float], period: int = 14) -> Optional[float]:
    if period <= 0 or len(values) < period + 1:
        return None

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses += -delta

    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
    if len(values) < slow + signal:
        return None
    ema_fast = _ema_series(values, fast)
    ema_slow = _ema_series(values, slow)
    if not ema_fast or not ema_slow:
        return None

    # Align lengths: ema_fast starts at fast, ema_slow starts at slow
    # Convert them back to same "time axis" by trimming the longer prefix.
    # ema_fast length: len(values)-fast+1 ; ema_slow length: len(values)-slow+1
    # We align on the tail.
    min_len = min(len(ema_fast), len(ema_slow))
    ema_fast_al = ema_fast[-min_len:]
    ema_slow_al = ema_slow[-min_len:]
    macd_line = [a - b for a, b in zip(ema_fast_al, ema_slow_al)]
    signal_line_series = _ema_series(macd_line, signal)
    if not signal_line_series:
        return None
    macd_last = macd_line[-1]
    signal_last = signal_line_series[-1]
    hist_last = macd_last - signal_last
    return {"macd": macd_last, "signal": signal_last, "hist": hist_last}


# ----------------------------- data model -----------------------------


@dataclass
class IndicatorCheck:
    indicator: str
    current_value: Any
    condition: str
    result: bool
    decision_bias: str  # "LONG" | "SHORT" | "NEUTRAL"


@dataclass
class CoreDecision:
    asset: str
    strategy_id: int
    strategy_name: str
    timeframe: str
    exchange: str
    signal: str  # "LONG" | "SHORT" | "HOLD"
    confidence: float  # 0..100
    checks: List[IndicatorCheck]
    price: Optional[float] = None

    def to_decision_log_record(self) -> Dict[str, Any]:
        reasoning_lines: List[str] = []
        reasoning_lines.append(f"Стратегия: {self.strategy_name} (ID: {self.strategy_id})")
        reasoning_lines.append(f"Актив: {self.asset} | Биржа: {self.exchange} | TF: {self.timeframe}")
        reasoning_lines.append("")
        if self.checks:
            for c in self.checks:
                res = "TRUE" if c.result else "FALSE"
                reasoning_lines.append(
                    f"- {c.indicator}: {c.current_value} -> {c.condition} => {res} (в пользу: {c.decision_bias})"
                )
        else:
            reasoning_lines.append("- Нет активных условий по индикаторам (или нет данных).")
        reasoning_lines.append("")
        reasoning_lines.append(f"Финальное решение: {self.signal}")

        return {
            "asset": self.asset,
            "signal_type": self.signal,
            "reasoning": "\n".join(reasoning_lines),
            "confidence": float(self.confidence),
            "indicators_data": {
                "strategy_id": self.strategy_id,
                "strategy_name": self.strategy_name,
                "timeframe": self.timeframe,
                "exchange": self.exchange,
                "price": self.price,
                "checks": [
                    {
                        "indicator": c.indicator,
                        "current_value": c.current_value,
                        "condition": c.condition,
                        "result": c.result,
                        "decision_bias": c.decision_bias,
                    }
                    for c in self.checks
                ],
                "final_decision": self.signal,
            },
        }


# ----------------------------- market data -----------------------------


class BinancePublicMarketDataProvider:
    """
    Минимальный провайдер рыночных данных через публичный REST Binance.
    Не требует API ключей. Подходит для crypto-пар формата BTCUSDT.
    """

    BASE_URL = "https://api.binance.com"

    async def fetch_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        interval = _tf_to_binance_interval(timeframe)
        if not interval:
            return None

        url = f"{self.BASE_URL}/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}

        owns_session = session is None
        if owns_session:
            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"Binance klines error {resp.status} for {symbol}: {body[:200]}")
                    return None
                data = await resp.json()
                # https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
                out = []
                for k in data:
                    out.append(
                        {
                            "open_time": int(k[0]),
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                            "close_time": int(k[6]),
                        }
                    )
                return out
        except Exception as e:
            logger.warning(f"Binance fetch_klines failed for {symbol}: {e}")
            return None
        finally:
            if owns_session and session:
                await session.close()


# ----------------------------- core -----------------------------


class TradingLogicCore:
    """
    Ядро проверяет активные стратегии и пишет:
      - decision_logs (всегда)
      - signals (только если LONG/SHORT)
    """

    def __init__(self, market_data_provider: Optional[BinancePublicMarketDataProvider] = None):
        self.market = market_data_provider or BinancePublicMarketDataProvider()

    def _normalize_indicators(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw = strategy.get("indicators") or {}
        # 1) template-format: {"list": [{name, parameters, enabled, weight}, ...]}
        if isinstance(raw, dict) and isinstance(raw.get("list"), list):
            return [i for i in raw["list"] if isinstance(i, dict)]

        # 2) wizard-format: {"rsi": {...}, "ema": {...}}
        if isinstance(raw, dict):
            out: List[Dict[str, Any]] = []
            for key, params in raw.items():
                if not isinstance(key, str):
                    continue
                name = key.strip().upper()
                out.append(
                    {
                        "name": name,
                        "enabled": True,
                        "parameters": params if isinstance(params, dict) else {},
                        "weight": 1.0,
                    }
                )
            return out

        return []

    def _extract_entry_constraints(self, strategy: Dict[str, Any]) -> Tuple[int, float]:
        entry_rules = strategy.get("entry_rules") or {}
        required_confirmations = 1
        min_strength = 0.6

        if isinstance(entry_rules, dict):
            try:
                required_confirmations = int(entry_rules.get("required_confirmations", required_confirmations))
            except Exception:
                pass
            try:
                min_strength = float(entry_rules.get("min_signal_strength", min_strength))
            except Exception:
                pass

        required_confirmations = max(1, required_confirmations)
        min_strength = max(0.0, min(1.0, min_strength))
        return required_confirmations, min_strength

    async def evaluate_strategy_for_asset(
        self,
        strategy: Dict[str, Any],
        asset: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> CoreDecision:
        strategy_id = int(strategy.get("id") or 0)
        strategy_name = str(strategy.get("name") or "Unnamed")
        timeframe = str(strategy.get("timeframe") or "1h")
        exchange = "binance"

        indicators = self._normalize_indicators(strategy)
        required_confirmations, min_strength = self._extract_entry_constraints(strategy)

        klines = await self.market.fetch_klines(asset, timeframe=timeframe, limit=250, session=session)
        closes: List[float] = [k["close"] for k in klines] if klines else []
        last_close = closes[-1] if closes else None

        checks: List[IndicatorCheck] = []
        long_hits = 0
        short_hits = 0
        long_weight = 0.0
        short_weight = 0.0
        total_weight = 0.0

        if not closes:
            return CoreDecision(
                asset=asset,
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                timeframe=timeframe,
                exchange=exchange,
                signal="HOLD",
                confidence=0.0,
                checks=[],
                price=last_close,
            )

        for ind in indicators:
            name = str(ind.get("name") or "").strip()
            if not name:
                continue
            enabled = bool(ind.get("enabled", True))
            if not enabled:
                continue
            params = ind.get("parameters") if isinstance(ind.get("parameters"), dict) else {}
            weight = float(ind.get("weight", 1.0) or 1.0)
            total_weight += max(weight, 0.0)

            key = name.upper()

            # RSI
            if key in {"RSI", "R_S_I", "Rsi"}:
                period = int(params.get("period", 14) or 14)
                oversold = float(params.get("oversold", 30) or 30)
                overbought = float(params.get("overbought", 70) or 70)
                rsi_val = _rsi(closes, period)
                if rsi_val is None:
                    checks.append(
                        IndicatorCheck("RSI", None, f"RSI(period={period}) available", False, "NEUTRAL")
                    )
                    continue
                is_long = rsi_val <= oversold
                is_short = rsi_val >= overbought

                if is_long:
                    long_hits += 1
                    long_weight += weight
                if is_short:
                    short_hits += 1
                    short_weight += weight

                # Для лога: фиксируем "условие стратегии" как шаблон
                if is_long:
                    cond = f"RSI ≤ {oversold} (перепроданность)"
                    bias = "LONG"
                    res = True
                elif is_short:
                    cond = f"RSI ≥ {overbought} (перекупленность)"
                    bias = "SHORT"
                    res = True
                else:
                    # показываем оба условия как контекст
                    cond = f"RSI ≤ {oversold} или RSI ≥ {overbought}"
                    bias = "NEUTRAL"
                    res = False

                checks.append(
                    IndicatorCheck(
                        indicator="RSI",
                        current_value=round(rsi_val, 2),
                        condition=cond,
                        result=res,
                        decision_bias=bias,
                    )
                )
                continue

            # EMA crossover
            if key in {"EMA", "E_M_A"}:
                fast = int(params.get("fast_period", params.get("fast", 12)) or 12)
                slow = int(params.get("slow_period", params.get("slow", 26)) or 26)
                ema_fast = _ema_last(closes, fast)
                ema_slow = _ema_last(closes, slow)
                if ema_fast is None or ema_slow is None:
                    checks.append(
                        IndicatorCheck("EMA", None, f"EMA({fast})/EMA({slow}) available", False, "NEUTRAL")
                    )
                    continue
                is_long = ema_fast > ema_slow
                is_short = ema_fast < ema_slow
                # Здесь "точное выполнение" = строгий знак сравнения.
                if is_long:
                    long_hits += 1
                    long_weight += weight
                if is_short:
                    short_hits += 1
                    short_weight += weight

                cond = f"EMA({fast}) > EMA({slow})" if is_long else f"EMA({fast}) < EMA({slow})" if is_short else f"EMA({fast}) ≠ EMA({slow})"
                bias = "LONG" if is_long else "SHORT" if is_short else "NEUTRAL"
                res = bool(is_long or is_short)

                checks.append(
                    IndicatorCheck(
                        indicator="EMA",
                        current_value={"ema_fast": round(ema_fast, 6), "ema_slow": round(ema_slow, 6)},
                        condition=cond,
                        result=res,
                        decision_bias=bias,
                    )
                )
                continue

            # MACD
            if key in {"MACD"}:
                fast = int(params.get("fast", 12) or 12)
                slow = int(params.get("slow", 26) or 26)
                signal = int(params.get("signal", 9) or 9)
                m = _macd(closes, fast=fast, slow=slow, signal=signal)
                if not m:
                    checks.append(
                        IndicatorCheck("MACD", None, f"MACD({fast},{slow},{signal}) available", False, "NEUTRAL")
                    )
                    continue

                is_long = m["macd"] > m["signal"]
                is_short = m["macd"] < m["signal"]
                if is_long:
                    long_hits += 1
                    long_weight += weight
                if is_short:
                    short_hits += 1
                    short_weight += weight

                cond = "MACD > Signal" if is_long else "MACD < Signal" if is_short else "MACD ≈ Signal"
                bias = "LONG" if is_long else "SHORT" if is_short else "NEUTRAL"
                res = bool(is_long or is_short)

                checks.append(
                    IndicatorCheck(
                        indicator="MACD",
                        current_value={k: round(v, 6) for k, v in m.items()},
                        condition=cond,
                        result=res,
                        decision_bias=bias,
                    )
                )
                continue

            # Bollinger Bands
            if key in {"BOLLINGER BANDS", "BOLLINGER", "BB"}:
                period = int(params.get("period", 20) or 20)
                std_mult = float(params.get("std_dev", params.get("std", 2)) or 2)
                mid = _sma(closes, period)
                sd = _std(closes, period)
                if mid is None or sd is None or last_close is None:
                    checks.append(
                        IndicatorCheck("Bollinger Bands", None, f"BB(period={period}) available", False, "NEUTRAL")
                    )
                    continue
                upper = mid + std_mult * sd
                lower = mid - std_mult * sd
                is_long = last_close <= lower
                is_short = last_close >= upper
                if is_long:
                    long_hits += 1
                    long_weight += weight
                if is_short:
                    short_hits += 1
                    short_weight += weight

                if is_long:
                    cond = "Цена ≤ Нижняя полоса BB"
                    bias = "LONG"
                    res = True
                elif is_short:
                    cond = "Цена ≥ Верхняя полоса BB"
                    bias = "SHORT"
                    res = True
                else:
                    cond = "Цена внутри полос BB"
                    bias = "NEUTRAL"
                    res = False

                checks.append(
                    IndicatorCheck(
                        indicator="Bollinger Bands",
                        current_value={
                            "close": round(last_close, 6),
                            "lower": round(lower, 6),
                            "mid": round(mid, 6),
                            "upper": round(upper, 6),
                        },
                        condition=cond,
                        result=res,
                        decision_bias=bias,
                    )
                )
                continue

            # Unknown indicator (kept for admin transparency)
            checks.append(
                IndicatorCheck(
                    indicator=name,
                    current_value=None,
                    condition="Индикатор не поддержан ядром (пропуск)",
                    result=False,
                    decision_bias="NEUTRAL",
                )
            )

        # Decision logic (strict & template-based)
        # - генерируем сигнал только если есть достаточное число подтверждений
        # - и нет "противоположных" подтверждений
        total_weight = total_weight or max(long_weight + short_weight, 1.0)
        long_strength = long_weight / total_weight
        short_strength = short_weight / total_weight

        signal_out = "HOLD"
        conf = 0.0
        if long_hits >= required_confirmations and short_hits == 0 and long_strength >= min_strength:
            signal_out = "LONG"
            conf = round(long_strength * 100, 2)
        elif short_hits >= required_confirmations and long_hits == 0 and short_strength >= min_strength:
            signal_out = "SHORT"
            conf = round(short_strength * 100, 2)

        return CoreDecision(
            asset=asset,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            timeframe=timeframe,
            exchange=exchange,
            signal=signal_out,
            confidence=conf,
            checks=checks,
            price=last_close,
        )

    async def run_once(self) -> int:
        """
        Один прогон ядра: для всех активных стратегий по всем их активам.
        Возвращает количество обработанных "asset checks".
        """
        manager = get_strategy_manager()
        strategies = await manager.get_active_strategies(decrypt=True)
        if not strategies:
            return 0

        processed = 0
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            for strategy in strategies:
                assets = strategy.get("assets_to_monitor") or []
                if not isinstance(assets, list):
                    continue
                for asset in assets:
                    if not isinstance(asset, str) or not asset.strip():
                        continue
                    asset = asset.strip().upper()
                    decision = await self.evaluate_strategy_for_asset(strategy, asset, session=session)
                    await db.create_decision_log(decision.to_decision_log_record())

                    if decision.signal in {"LONG", "SHORT"}:
                        await db.create_signal(
                            {
                                "asset": decision.asset,
                                "signal_type": decision.signal,
                                "price": decision.price,
                                "amount": None,
                                "timeframe": _tf_to_minutes(decision.timeframe),
                                "strategy_id": decision.strategy_id or None,
                            }
                        )
                    processed += 1
        return processed

    async def run_forever(self, interval_seconds: int = 60, *, stop_event: Optional[asyncio.Event] = None):
        """
        Фоновый цикл ядра. Безопасно переживает сетевые ошибки.
        """
        interval_seconds = max(10, int(interval_seconds or 60))
        stop_event = stop_event or asyncio.Event()

        logger.info(f"🧠 TradingLogicCore loop started (interval={interval_seconds}s)")
        while not stop_event.is_set():
            try:
                processed = await self.run_once()
                if processed:
                    logger.info(f"🧠 TradingLogicCore: processed {processed} asset checks")
            except Exception as e:
                logger.error(f"TradingLogicCore loop error: {e}")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                continue


# Singleton
_core: Optional[TradingLogicCore] = None


def get_trading_core() -> TradingLogicCore:
    global _core
    if _core is None:
        _core = TradingLogicCore()
    return _core

