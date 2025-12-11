"""
Dynamic Strategy Switcher
Сервис для автоматического переключения стратегий на основе:
- Времени суток (пиковые часы, сессии)
- Волатильности рынка
- Трендов и рыночных условий
- Производительности текущей стратегии
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from database import db
from services.data_aggregation_service import aggregation_service, MarketConditions
from services.strategy_templates_service import strategy_templates_service, StrategyTemplate

logger = logging.getLogger(__name__)


class SwitchReason(Enum):
    """Причины переключения стратегии"""
    TIME_SESSION_CHANGE = "time_session_change"
    VOLATILITY_CHANGE = "volatility_change"
    POOR_PERFORMANCE = "poor_performance"
    MARKET_CONDITION_CHANGE = "market_condition_change"
    MANUAL_OVERRIDE = "manual_override"
    SCHEDULED_SWITCH = "scheduled_switch"


@dataclass
class StrategySwitch:
    """Информация о переключении стратегии"""
    timestamp: datetime
    from_strategy: Optional[str]
    to_strategy: str
    reason: SwitchReason
    market_conditions: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    confidence: float  # 0.0 - 1.0


class DynamicStrategySwitcher:
    """Умный переключатель стратегий"""
    
    def __init__(self):
        self.check_interval = 300  # Проверка каждые 5 минут
        self.switch_history: List[StrategySwitch] = []
        self.current_strategy_start_time: Optional[datetime] = None
        self.min_strategy_duration = 3600  # Минимум 1 час на стратегию
        self.performance_check_window = 24  # Часов для анализа производительности
        
        # Пороги для переключения
        self.thresholds = {
            "min_win_rate": 0.35,
            "max_drawdown_percent": 20.0,
            "min_confidence": 0.6,
            "volatility_change_threshold": 3.0  # % изменения волатильности
        }
        
        # Расписание принудительных проверок
        self.scheduled_check_hours = [0, 8, 16]  # UTC часы для проверки
        
        self.is_running = False
    
    # ==================== ОСНОВНАЯ ЛОГИКА ====================
    
    async def start_auto_switching(self):
        """Запустить автоматическое переключение стратегий"""
        if self.is_running:
            logger.warning("⚠️ Автопереключение уже запущено")
            return
        
        self.is_running = True
        logger.info("🔄 Автоматическое переключение стратегий запущено")
        
        while self.is_running:
            try:
                await self._check_and_switch_if_needed()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле переключения: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    def stop_auto_switching(self):
        """Остановить автоматическое переключение"""
        self.is_running = False
        logger.info("🛑 Автоматическое переключение остановлено")
    
    async def _check_and_switch_if_needed(self):
        """Проверить условия и переключить стратегию если необходимо"""
        
        logger.debug("🔍 Проверка необходимости переключения стратегии...")
        
        # Получаем текущие рыночные условия
        market_conditions = await aggregation_service.get_market_conditions()
        
        # Получаем активную стратегию
        current_strategy = await db.get_active_strategy()
        
        # Анализируем производительность текущей стратегии
        performance = await self._analyze_current_performance(current_strategy)
        
        # Определяем, нужно ли переключение
        switch_decision = await self._evaluate_switch_decision(
            current_strategy,
            market_conditions,
            performance
        )
        
        if switch_decision:
            await self._execute_strategy_switch(
                switch_decision['new_strategy'],
                switch_decision['reason'],
                market_conditions,
                performance
            )
    
    # ==================== АНАЛИЗ И ПРИНЯТИЕ РЕШЕНИЙ ====================
    
    async def _evaluate_switch_decision(
        self,
        current_strategy: Optional[Dict[str, Any]],
        market_conditions: MarketConditions,
        performance: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Оценить необходимость переключения стратегии"""
        
        # Проверяем минимальное время работы текущей стратегии
        if not self._can_switch_now():
            logger.debug("⏳ Слишком рано для переключения стратегии")
            return None
        
        current_strategy_name = current_strategy.get('name', 'None') if current_strategy else 'None'
        
        # Причина 1: Плохая производительность
        if self._is_performance_poor(performance):
            logger.warning(f"📉 Плохая производительность текущей стратегии '{current_strategy_name}'")
            recommended = await strategy_templates_service.recommend_template(
                asdict(market_conditions) if hasattr(market_conditions, '__dataclass_fields__') else market_conditions.__dict__
            )
            return {
                'new_strategy': recommended,
                'reason': SwitchReason.POOR_PERFORMANCE,
                'confidence': 0.8
            }
        
        # Причина 2: Изменение рыночных условий
        optimal_strategy = await self._find_optimal_strategy_for_conditions(market_conditions)
        
        if optimal_strategy and optimal_strategy != self._extract_template_type(current_strategy):
            logger.info(f"🔄 Рыночные условия изменились, рекомендуется '{optimal_strategy}'")
            return {
                'new_strategy': optimal_strategy,
                'reason': SwitchReason.MARKET_CONDITION_CHANGE,
                'confidence': 0.7
            }
        
        # Причина 3: Изменение торговой сессии
        if self._is_session_change_significant(market_conditions):
            recommended = await strategy_templates_service.recommend_template(
                asdict(market_conditions) if hasattr(market_conditions, '__dataclass_fields__') else market_conditions.__dict__
            )
            logger.info(f"🌍 Смена торговой сессии, рекомендуется '{recommended}'")
            return {
                'new_strategy': recommended,
                'reason': SwitchReason.TIME_SESSION_CHANGE,
                'confidence': 0.65
            }
        
        # Причина 4: Запланированная проверка
        if self._is_scheduled_check_time():
            optimal = await self._find_optimal_strategy_for_conditions(market_conditions)
            if optimal and optimal != self._extract_template_type(current_strategy):
                return {
                    'new_strategy': optimal,
                    'reason': SwitchReason.SCHEDULED_SWITCH,
                    'confidence': 0.6
                }
        
        logger.debug("✅ Переключение не требуется")
        return None
    
    async def _find_optimal_strategy_for_conditions(
        self,
        conditions: MarketConditions
    ) -> str:
        """Найти оптимальную стратегию для текущих условий"""
        
        # Преобразуем MarketConditions в словарь
        conditions_dict = {
            'overall_volatility': conditions.overall_volatility,
            'market_trend': conditions.market_trend,
            'time_of_day': conditions.time_of_day,
            'is_peak_hours': conditions.is_peak_hours,
            'trading_volume': conditions.trading_volume
        }
        
        # Используем рекомендацию из сервиса шаблонов
        recommended = await strategy_templates_service.recommend_template(conditions_dict)
        
        return recommended
    
    def _extract_template_type(self, strategy: Optional[Dict[str, Any]]) -> Optional[str]:
        """Извлечь тип шаблона из стратегии"""
        if not strategy:
            return None
        
        name = strategy.get('name', '').lower()
        
        # Определяем тип на основе названия
        if 'scalp' in name:
            return 'scalping'
        elif 'momentum' in name or 'trend' in name:
            return 'momentum'
        elif 'reversion' in name or 'range' in name:
            return 'mean_reversion'
        elif 'breakout' in name:
            return 'breakout'
        
        return None
    
    # ==================== ПРОВЕРКИ УСЛОВИЙ ====================
    
    def _can_switch_now(self) -> bool:
        """Проверить, можно ли переключить стратегию сейчас"""
        if not self.current_strategy_start_time:
            return True
        
        elapsed = (datetime.utcnow() - self.current_strategy_start_time).total_seconds()
        return elapsed >= self.min_strategy_duration
    
    def _is_performance_poor(self, performance: Dict[str, Any]) -> bool:
        """Проверить, плохая ли производительность"""
        
        if not performance or performance.get('total_trades', 0) < 5:
            # Недостаточно данных для оценки
            return False
        
        win_rate = performance.get('win_rate', 1.0)
        drawdown = performance.get('max_drawdown', 0.0)
        net_profit = performance.get('net_profit', 0.0)
        
        # Критерии плохой производительности
        is_poor = (
            win_rate < self.thresholds['min_win_rate'] or
            drawdown > self.thresholds['max_drawdown_percent'] or
            net_profit < -100  # Убыток больше 100 единиц
        )
        
        if is_poor:
            logger.warning(
                f"⚠️ Плохая производительность: "
                f"WinRate={win_rate:.2%}, Drawdown={drawdown:.2f}, NetProfit={net_profit:.2f}"
            )
        
        return is_poor
    
    def _is_session_change_significant(self, conditions: MarketConditions) -> bool:
        """Проверить, значительно ли изменилась торговая сессия"""
        
        # Проверяем время последнего переключения
        if self.switch_history:
            last_switch = self.switch_history[-1]
            time_since_switch = (datetime.utcnow() - last_switch.timestamp).total_seconds() / 3600
            
            # Если недавно переключались по причине сессии, не переключаем снова
            if time_since_switch < 4 and last_switch.reason == SwitchReason.TIME_SESSION_CHANGE:
                return False
        
        # Проверяем, перекрытие сессий или пиковые часы
        return conditions.is_peak_hours or 'overlap' in conditions.time_of_day
    
    def _is_scheduled_check_time(self) -> bool:
        """Проверить, настало ли время запланированной проверки"""
        current_hour = datetime.utcnow().hour
        return current_hour in self.scheduled_check_hours
    
    # ==================== АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ ====================
    
    async def _analyze_current_performance(
        self,
        strategy: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Проанализировать производительность текущей стратегии"""
        
        if not strategy:
            return {}
        
        try:
            # Получаем статистику торговли
            stats = await db.get_trading_statistics()
            
            # Для более детального анализа можно использовать aggregation_service
            # но пока используем базовую статистику
            
            performance = {
                'total_trades': stats.get('total_trades', 0),
                'total_signals': stats.get('total_signals', 0),
                'win_rate': 0.5,  # Заглушка, нужно расширить БД
                'net_profit': 0.0,
                'max_drawdown': 0.0,
                'active_users': stats.get('active_users', 0)
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Ошибка анализа производительности: {e}")
            return {}
    
    # ==================== ВЫПОЛНЕНИЕ ПЕРЕКЛЮЧЕНИЯ ====================
    
    async def _execute_strategy_switch(
        self,
        new_strategy_template: str,
        reason: SwitchReason,
        market_conditions: MarketConditions,
        performance: Dict[str, Any]
    ):
        """Выполнить переключение стратегии"""
        
        try:
            logger.info(f"🔄 Переключение стратегии на '{new_strategy_template}' (причина: {reason.value})")
            
            # Получаем текущую активную стратегию
            current_strategy = await db.get_active_strategy()
            current_name = current_strategy.get('name', 'None') if current_strategy else 'None'
            
            # Деактивируем текущую стратегию
            if current_strategy:
                await db.update_strategy_status(current_strategy['id'], False)
            
            # Сохраняем новую стратегию из шаблона
            success = await strategy_templates_service.save_template_as_strategy(new_strategy_template)
            
            if not success:
                logger.error(f"❌ Не удалось сохранить стратегию из шаблона '{new_strategy_template}'")
                return
            
            # Получаем только что созданную стратегию и активируем её
            strategies = await db.get_all_strategies()
            new_strategy = strategies[0] if strategies else None
            
            if new_strategy:
                await db.update_strategy_status(new_strategy['id'], True)
                logger.info(f"✅ Стратегия '{new_strategy_template}' активирована")
            
            # Записываем переключение в историю
            switch_record = StrategySwitch(
                timestamp=datetime.utcnow(),
                from_strategy=current_name,
                to_strategy=new_strategy_template,
                reason=reason,
                market_conditions=asdict(market_conditions) if hasattr(market_conditions, '__dataclass_fields__') else market_conditions.__dict__,
                performance_metrics=performance,
                confidence=0.75
            )
            
            self.switch_history.append(switch_record)
            self.current_strategy_start_time = datetime.utcnow()
            
            # Логируем в БД
            await self._log_switch_to_db(switch_record)
            
            logger.info(
                f"✅ Переключение завершено: '{current_name}' -> '{new_strategy_template}' "
                f"(причина: {reason.value})"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка при переключении стратегии: {e}")
    
    async def _log_switch_to_db(self, switch: StrategySwitch):
        """Логировать переключение в базу данных"""
        try:
            await db.client.table("system_logs").insert({
                "level": "INFO",
                "message": f"Strategy switched: {switch.from_strategy} -> {switch.to_strategy}",
                "details": {
                    "reason": switch.reason.value,
                    "market_conditions": switch.market_conditions,
                    "performance": switch.performance_metrics,
                    "confidence": switch.confidence
                },
                "source": "dynamic_strategy_switcher"
            }).execute()
        except Exception as e:
            logger.error(f"Ошибка логирования переключения: {e}")
    
    # ==================== РУЧНОЕ УПРАВЛЕНИЕ ====================
    
    async def manual_switch(
        self,
        template_name: str,
        reason: str = "Manual override"
    ) -> bool:
        """Ручное переключение стратегии"""
        
        logger.info(f"👤 Ручное переключение на '{template_name}'")
        
        market_conditions = await aggregation_service.get_market_conditions()
        
        await self._execute_strategy_switch(
            template_name,
            SwitchReason.MANUAL_OVERRIDE,
            market_conditions,
            {"manual": True}
        )
        
        return True
    
    # ==================== ОТЧЕТЫ И СТАТИСТИКА ====================
    
    def get_switch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить историю переключений"""
        recent = self.switch_history[-limit:]
        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'from': s.from_strategy,
                'to': s.to_strategy,
                'reason': s.reason.value,
                'confidence': s.confidence
            }
            for s in recent
        ]
    
    def get_current_strategy_uptime(self) -> float:
        """Получить время работы текущей стратегии (в часах)"""
        if not self.current_strategy_start_time:
            return 0.0
        
        elapsed = datetime.utcnow() - self.current_strategy_start_time
        return elapsed.total_seconds() / 3600
    
    async def get_status_report(self) -> Dict[str, Any]:
        """Получить отчет о состоянии переключателя"""
        
        current_strategy = await db.get_active_strategy()
        market_conditions = await aggregation_service.get_market_conditions()
        
        return {
            'is_running': self.is_running,
            'current_strategy': current_strategy.get('name') if current_strategy else None,
            'uptime_hours': self.get_current_strategy_uptime(),
            'total_switches': len(self.switch_history),
            'recent_switches': self.get_switch_history(5),
            'market_conditions': {
                'volatility': market_conditions.overall_volatility,
                'trend': market_conditions.market_trend,
                'session': market_conditions.time_of_day,
                'is_peak': market_conditions.is_peak_hours
            },
            'next_check_in': self.check_interval
        }


# Singleton
dynamic_switcher = DynamicStrategySwitcher()


# Функция для импорта asdict
def asdict(obj):
    """Преобразовать dataclass в словарь"""
    if hasattr(obj, '__dataclass_fields__'):
        from dataclasses import asdict as dc_asdict
        return dc_asdict(obj)
    return obj.__dict__
