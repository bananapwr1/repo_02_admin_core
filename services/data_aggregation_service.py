"""
Data Aggregation Service
Сервис для сбора, структурирования и агрегации статистики по торговым активам
Собирает данные за день, неделю и месяц для анализа и принятия решений
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
from database import db

logger = logging.getLogger(__name__)


@dataclass
class AssetStatistics:
    """Статистика по активу за определенный период"""
    asset: str
    period: str  # 'daily', 'weekly', 'monthly'
    start_date: datetime
    end_date: datetime
    
    # Торговая статистика
    total_signals: int = 0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    win_rate: float = 0.0
    
    # Финансовая статистика
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    average_profit: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    # Рыночная статистика
    average_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    price_volatility: float = 0.0
    
    # Индикаторы эффективности
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    average_trade_duration: float = 0.0  # в часах
    
    # Метаданные
    aggregated_at: datetime = None
    data_quality_score: float = 1.0  # 0.0 - 1.0
    

@dataclass
class MarketConditions:
    """Условия рынка на текущий момент"""
    timestamp: datetime
    active_assets: List[str]
    
    # Общие рыночные показатели
    overall_volatility: str  # 'low', 'medium', 'high'
    market_trend: str  # 'bullish', 'bearish', 'sideways'
    trading_volume: str  # 'low', 'medium', 'high'
    
    # Временные факторы
    time_of_day: str  # 'asian_session', 'european_session', 'american_session', 'overlap'
    is_peak_hours: bool
    day_of_week: str
    
    # Рекомендации
    recommended_strategy_type: str  # 'scalping', 'swing', 'momentum', 'contrarian'
    risk_level: str  # 'low', 'medium', 'high'


class DataAggregationService:
    """Сервис агрегации данных для принятия торговых решений"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 минут
        self.last_update = {}
    
    # ==================== СБОР СТАТИСТИКИ ПО АКТИВАМ ====================
    
    async def get_asset_statistics(
        self, 
        asset: str, 
        period: str = 'daily'
    ) -> AssetStatistics:
        """Получить статистику по активу за период"""
        
        # Определяем временные рамки
        end_date = datetime.utcnow()
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=1)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            raise ValueError(f"Неизвестный период: {period}")
        
        # Проверяем кэш
        cache_key = f"{asset}_{period}"
        if self._is_cache_valid(cache_key):
            logger.info(f"📦 Возврат из кэша: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"📊 Сбор статистики для {asset} за период {period}")
        
        # Создаем объект статистики
        stats = AssetStatistics(
            asset=asset,
            period=period,
            start_date=start_date,
            end_date=end_date,
            aggregated_at=datetime.utcnow()
        )
        
        try:
            # Получаем сигналы за период
            signals = await self._get_signals_for_period(asset, start_date, end_date)
            stats.total_signals = len(signals)
            
            # Получаем трейды за период
            trades = await self._get_trades_for_period(asset, start_date, end_date)
            stats.total_trades = len(trades)
            
            # Анализируем трейды
            if trades:
                stats = self._analyze_trades(stats, trades)
            
            # Анализируем ценовую динамику
            stats = await self._analyze_price_data(stats, signals)
            
            # Рассчитываем дополнительные метрики
            stats = self._calculate_advanced_metrics(stats, trades)
            
            # Сохраняем в кэш
            self.cache[cache_key] = stats
            self.last_update[cache_key] = datetime.utcnow()
            
            logger.info(f"✅ Статистика для {asset} собрана успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора статистики для {asset}: {e}")
            stats.data_quality_score = 0.0
        
        return stats
    
    async def get_all_assets_statistics(
        self, 
        assets: List[str], 
        period: str = 'daily'
    ) -> Dict[str, AssetStatistics]:
        """Получить статистику по всем активам за период"""
        logger.info(f"📊 Сбор статистики по {len(assets)} активам")
        
        results = {}
        tasks = [self.get_asset_statistics(asset, period) for asset in assets]
        
        stats_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for asset, stats in zip(assets, stats_list):
            if isinstance(stats, Exception):
                logger.error(f"Ошибка для {asset}: {stats}")
                continue
            results[asset] = stats
        
        return results
    
    # ==================== АНАЛИЗ ТРЕЙДОВ ====================
    
    def _analyze_trades(self, stats: AssetStatistics, trades: List[Dict]) -> AssetStatistics:
        """Анализ результатов трейдов"""
        
        successful = [t for t in trades if t.get('profit_loss', 0) > 0]
        failed = [t for t in trades if t.get('profit_loss', 0) < 0]
        
        stats.successful_trades = len(successful)
        stats.failed_trades = len(failed)
        
        if stats.total_trades > 0:
            stats.win_rate = stats.successful_trades / stats.total_trades
        
        # Финансовая статистика
        profits = [t['profit_loss'] for t in successful]
        losses = [abs(t['profit_loss']) for t in failed]
        
        if profits:
            stats.total_profit = sum(profits)
            stats.max_profit = max(profits)
            stats.average_profit = stats.total_profit / len(profits)
        
        if losses:
            stats.total_loss = sum(losses)
            stats.max_loss = max(losses)
        
        stats.net_profit = stats.total_profit - stats.total_loss
        
        # Длительность трейдов
        durations = []
        for trade in trades:
            if trade.get('created_at') and trade.get('closed_at'):
                try:
                    created = datetime.fromisoformat(str(trade['created_at']).replace('Z', '+00:00'))
                    closed = datetime.fromisoformat(str(trade['closed_at']).replace('Z', '+00:00'))
                    duration = (closed - created).total_seconds() / 3600  # в часах
                    durations.append(duration)
                except:
                    pass
        
        if durations:
            stats.average_trade_duration = sum(durations) / len(durations)
        
        return stats
    
    async def _analyze_price_data(self, stats: AssetStatistics, signals: List[Dict]) -> AssetStatistics:
        """Анализ ценовой динамики"""
        
        prices = [s.get('price', 0) for s in signals if s.get('price')]
        
        if prices:
            stats.average_price = sum(prices) / len(prices)
            stats.min_price = min(prices)
            stats.max_price = max(prices)
            
            # Волатильность (стандартное отклонение / среднее)
            if stats.average_price > 0:
                variance = sum((p - stats.average_price) ** 2 for p in prices) / len(prices)
                std_dev = variance ** 0.5
                stats.price_volatility = (std_dev / stats.average_price) * 100
        
        return stats
    
    def _calculate_advanced_metrics(self, stats: AssetStatistics, trades: List[Dict]) -> AssetStatistics:
        """Расчет продвинутых метрик"""
        
        if not trades or stats.total_trades == 0:
            return stats
        
        # Sharpe Ratio (упрощенная версия)
        returns = [t.get('profit_loss', 0) for t in trades]
        if returns:
            avg_return = sum(returns) / len(returns)
            if len(returns) > 1:
                variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
                std_dev = variance ** 0.5
                if std_dev > 0:
                    stats.sharpe_ratio = avg_return / std_dev
        
        # Maximum Drawdown
        cumulative_returns = []
        cumulative = 0
        for trade in trades:
            cumulative += trade.get('profit_loss', 0)
            cumulative_returns.append(cumulative)
        
        if cumulative_returns:
            peak = cumulative_returns[0]
            max_dd = 0
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_dd:
                    max_dd = drawdown
            stats.max_drawdown = max_dd
        
        return stats
    
    # ==================== АНАЛИЗ РЫНОЧНЫХ УСЛОВИЙ ====================
    
    async def get_market_conditions(self) -> MarketConditions:
        """Получить текущие рыночные условия"""
        
        now = datetime.utcnow()
        
        # Получаем активные стратегии для определения активов
        strategies = await db.get_all_strategies()
        active_strategy = await db.get_active_strategy()
        
        active_assets = []
        if active_strategy:
            active_assets = active_strategy.get('assets_to_monitor', [])
        
        # Определяем время суток (UTC)
        hour = now.hour
        time_of_day = self._get_trading_session(hour)
        is_peak_hours = self._is_peak_hours(hour, now.weekday())
        
        # Анализируем общую волатильность
        overall_volatility = await self._calculate_overall_volatility(active_assets)
        
        # Определяем тренд рынка
        market_trend = await self._determine_market_trend(active_assets)
        
        # Рекомендуемый тип стратегии
        recommended_strategy = self._recommend_strategy_type(
            time_of_day, 
            overall_volatility, 
            market_trend
        )
        
        conditions = MarketConditions(
            timestamp=now,
            active_assets=active_assets,
            overall_volatility=overall_volatility,
            market_trend=market_trend,
            trading_volume='medium',  # Можно расширить
            time_of_day=time_of_day,
            is_peak_hours=is_peak_hours,
            day_of_week=now.strftime('%A'),
            recommended_strategy_type=recommended_strategy,
            risk_level=self._calculate_risk_level(overall_volatility, is_peak_hours)
        )
        
        logger.info(f"📈 Рыночные условия: {time_of_day}, {overall_volatility} volatility, {market_trend} trend")
        
        return conditions
    
    def _get_trading_session(self, hour: int) -> str:
        """Определить торговую сессию по времени UTC"""
        if 0 <= hour < 8:
            return 'asian_session'
        elif 8 <= hour < 12:
            return 'overlap_asian_european'
        elif 12 <= hour < 16:
            return 'european_session'
        elif 16 <= hour < 20:
            return 'overlap_european_american'
        else:
            return 'american_session'
    
    def _is_peak_hours(self, hour: int, weekday: int) -> bool:
        """Определить пиковые часы торговли"""
        # Выходные - не пиковые часы
        if weekday >= 5:  # Суббота, Воскресенье
            return False
        
        # Пиковые часы: перекрытие сессий и активные торговые часы
        # UTC: 8-12 (Asian/European overlap), 16-20 (European/American overlap)
        return 8 <= hour < 12 or 16 <= hour < 20
    
    async def _calculate_overall_volatility(self, assets: List[str]) -> str:
        """Рассчитать общую волатильность рынка"""
        if not assets:
            return 'medium'
        
        try:
            # Получаем статистику по активам за последний день
            stats = await self.get_all_assets_statistics(assets, period='daily')
            
            if not stats:
                return 'medium'
            
            # Средняя волатильность по всем активам
            volatilities = [s.price_volatility for s in stats.values() if s.price_volatility > 0]
            
            if not volatilities:
                return 'medium'
            
            avg_volatility = sum(volatilities) / len(volatilities)
            
            # Классификация
            if avg_volatility < 2.0:
                return 'low'
            elif avg_volatility < 5.0:
                return 'medium'
            else:
                return 'high'
                
        except Exception as e:
            logger.error(f"Ошибка расчета волатильности: {e}")
            return 'medium'
    
    async def _determine_market_trend(self, assets: List[str]) -> str:
        """Определить общий тренд рынка"""
        if not assets:
            return 'sideways'
        
        try:
            # Получаем последние сигналы
            stats = await self.get_all_assets_statistics(assets, period='daily')
            
            if not stats:
                return 'sideways'
            
            # Подсчитываем бычьи и медвежьи сигналы
            bullish_count = 0
            bearish_count = 0
            
            for asset_stats in stats.values():
                if asset_stats.net_profit > 0:
                    bullish_count += 1
                elif asset_stats.net_profit < 0:
                    bearish_count += 1
            
            total = bullish_count + bearish_count
            if total == 0:
                return 'sideways'
            
            bullish_ratio = bullish_count / total
            
            if bullish_ratio > 0.6:
                return 'bullish'
            elif bullish_ratio < 0.4:
                return 'bearish'
            else:
                return 'sideways'
                
        except Exception as e:
            logger.error(f"Ошибка определения тренда: {e}")
            return 'sideways'
    
    def _recommend_strategy_type(
        self, 
        time_of_day: str, 
        volatility: str, 
        trend: str
    ) -> str:
        """Рекомендовать тип стратегии на основе условий"""
        
        # Высокая волатильность + пиковые часы = скальпинг
        if volatility == 'high' and 'overlap' in time_of_day:
            return 'scalping'
        
        # Низкая волатильность = contrarian (поиск разворотов)
        if volatility == 'low':
            return 'contrarian'
        
        # Явный тренд = momentum
        if trend in ['bullish', 'bearish'] and volatility == 'medium':
            return 'momentum'
        
        # Средние условия = swing trading
        return 'swing'
    
    def _calculate_risk_level(self, volatility: str, is_peak_hours: bool) -> str:
        """Рассчитать уровень риска"""
        if volatility == 'high':
            return 'high'
        elif volatility == 'low' and not is_peak_hours:
            return 'low'
        else:
            return 'medium'
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    async def _get_signals_for_period(
        self, 
        asset: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """Получить сигналы за период"""
        try:
            signals = await db.get_signals_by_date_range(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                asset=asset
            )
            return signals
        except Exception as e:
            logger.error(f"Ошибка получения сигналов для {asset}: {e}")
            return []
    
    async def _get_trades_for_period(
        self, 
        asset: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """Получить трейды за период"""
        try:
            trades = await db.get_trades_by_date_range(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                asset=asset
            )
            return trades
        except Exception as e:
            logger.error(f"Ошибка получения трейдов для {asset}: {e}")
            return []
    
    def _is_cache_valid(self, key: str) -> bool:
        """Проверить валидность кэша"""
        if key not in self.cache or key not in self.last_update:
            return False
        
        age = (datetime.utcnow() - self.last_update[key]).total_seconds()
        return age < self.cache_ttl
    
    def clear_cache(self):
        """Очистить кэш"""
        self.cache.clear()
        self.last_update.clear()
        logger.info("🗑️ Кэш очищен")
    
    # ==================== СОХРАНЕНИЕ АГРЕГИРОВАННЫХ ДАННЫХ ====================
    
    async def save_aggregated_statistics(self, asset: str, period: str):
        """Сохранить агрегированную статистику в БД для исторического анализа"""
        try:
            stats = await self.get_asset_statistics(asset, period)
            
            # Сохраняем в system_logs для исторического анализа
            await db.client.table("system_logs").insert({
                "level": "INFO",
                "message": f"Aggregated statistics for {asset} ({period})",
                "details": asdict(stats),
                "source": "data_aggregation_service"
            }).execute()
            
            logger.info(f"💾 Статистика для {asset} ({period}) сохранена")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")


# Singleton
aggregation_service = DataAggregationService()
