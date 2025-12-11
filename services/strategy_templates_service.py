"""
Strategy Templates Service
Сервис для управления шаблонными стратегиями и их параметрами
Позволяет создавать, настраивать и применять стратегии на основе шаблонов
"""
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
from database import db

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Типы торговых стратегий"""
    SCALPING = "scalping"
    MOMENTUM = "momentum"
    SWING = "swing"
    CONTRARIAN = "contrarian"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"


class TimeFrame(Enum):
    """Временные интервалы"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


@dataclass
class IndicatorConfig:
    """Конфигурация индикатора"""
    name: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # Вес индикатора в принятии решений


@dataclass
class RiskManagement:
    """Параметры управления рисками"""
    max_position_size_percent: float = 10.0  # % от капитала
    max_positions: int = 3
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0
    trailing_stop_enabled: bool = True
    trailing_stop_percent: float = 1.5
    max_daily_loss_percent: float = 5.0
    max_drawdown_percent: float = 15.0


@dataclass
class EntryRules:
    """Правила входа в позицию"""
    required_confirmations: int = 2  # Сколько индикаторов должны совпадать
    min_signal_strength: float = 0.6  # Минимальная уверенность (0.0 - 1.0)
    allowed_time_sessions: List[str] = field(default_factory=lambda: ['all'])
    avoid_high_impact_news: bool = True
    min_volatility: float = 0.5
    max_volatility: float = 10.0


@dataclass
class ExitRules:
    """Правила выхода из позиции"""
    use_trailing_stop: bool = True
    exit_on_opposite_signal: bool = True
    max_trade_duration_hours: float = 24.0
    partial_exit_enabled: bool = False
    partial_exit_levels: List[float] = field(default_factory=lambda: [50.0, 75.0])


@dataclass
class StrategyTemplate:
    """Шаблон торговой стратегии"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    strategy_type: StrategyType = StrategyType.SWING
    
    # Параметры стратегии
    assets: List[str] = field(default_factory=list)
    timeframe: TimeFrame = TimeFrame.H1
    
    # Индикаторы
    indicators: List[IndicatorConfig] = field(default_factory=list)
    
    # Правила
    entry_rules: EntryRules = field(default_factory=EntryRules)
    exit_rules: ExitRules = field(default_factory=ExitRules)
    risk_management: RiskManagement = field(default_factory=RiskManagement)
    
    # Метаданные
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by_template: str = ""
    performance_score: float = 0.0  # Оценка эффективности (0-100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для сохранения"""
        data = asdict(self)
        # Преобразуем Enum в строки
        data['strategy_type'] = self.strategy_type.value
        data['timeframe'] = self.timeframe.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyTemplate':
        """Создать из словаря"""
        # Преобразуем строки в Enum
        if 'strategy_type' in data:
            data['strategy_type'] = StrategyType(data['strategy_type'])
        if 'timeframe' in data:
            data['timeframe'] = TimeFrame(data['timeframe'])
        
        # Преобразуем вложенные объекты
        if 'indicators' in data and isinstance(data['indicators'], list):
            data['indicators'] = [
                IndicatorConfig(**ind) if isinstance(ind, dict) else ind
                for ind in data['indicators']
            ]
        if 'entry_rules' in data and isinstance(data['entry_rules'], dict):
            data['entry_rules'] = EntryRules(**data['entry_rules'])
        if 'exit_rules' in data and isinstance(data['exit_rules'], dict):
            data['exit_rules'] = ExitRules(**data['exit_rules'])
        if 'risk_management' in data and isinstance(data['risk_management'], dict):
            data['risk_management'] = RiskManagement(**data['risk_management'])
        
        # Преобразуем даты
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        return cls(**data)


class StrategyTemplatesService:
    """Сервис управления шаблонами стратегий"""
    
    def __init__(self):
        self.templates_cache: Dict[str, StrategyTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Инициализация встроенных шаблонов стратегий"""
        
        # Шаблон 1: Scalping Strategy
        scalping = StrategyTemplate(
            name="High Frequency Scalping",
            description="Стратегия быстрых сделок на малых таймфреймах с высокой частотой",
            strategy_type=StrategyType.SCALPING,
            timeframe=TimeFrame.M5,
            assets=["BTCUSDT", "ETHUSDT", "EURUSD"],
            indicators=[
                IndicatorConfig(
                    name="EMA",
                    parameters={"fast_period": 5, "slow_period": 20},
                    weight=1.2
                ),
                IndicatorConfig(
                    name="RSI",
                    parameters={"period": 7, "oversold": 30, "overbought": 70},
                    weight=1.0
                ),
                IndicatorConfig(
                    name="MACD",
                    parameters={"fast": 12, "slow": 26, "signal": 9},
                    weight=0.8
                )
            ],
            entry_rules=EntryRules(
                required_confirmations=2,
                min_signal_strength=0.7,
                allowed_time_sessions=['overlap_european_american', 'overlap_asian_european'],
                min_volatility=1.0,
                max_volatility=5.0
            ),
            exit_rules=ExitRules(
                use_trailing_stop=True,
                exit_on_opposite_signal=True,
                max_trade_duration_hours=2.0
            ),
            risk_management=RiskManagement(
                max_position_size_percent=5.0,
                max_positions=5,
                stop_loss_percent=1.0,
                take_profit_percent=2.0,
                trailing_stop_percent=0.5
            ),
            created_by_template="built-in"
        )
        
        # Шаблон 2: Momentum Strategy
        momentum = StrategyTemplate(
            name="Trend Momentum Following",
            description="Стратегия следования за трендом с использованием импульса",
            strategy_type=StrategyType.MOMENTUM,
            timeframe=TimeFrame.H1,
            assets=["BTCUSDT", "EURUSD", "GBPUSD"],
            indicators=[
                IndicatorConfig(
                    name="EMA",
                    parameters={"fast_period": 20, "slow_period": 50, "long_period": 200},
                    weight=1.5
                ),
                IndicatorConfig(
                    name="ADX",
                    parameters={"period": 14, "trend_threshold": 25},
                    weight=1.3
                ),
                IndicatorConfig(
                    name="MACD",
                    parameters={"fast": 12, "slow": 26, "signal": 9},
                    weight=1.0
                )
            ],
            entry_rules=EntryRules(
                required_confirmations=2,
                min_signal_strength=0.65,
                allowed_time_sessions=['all'],
                min_volatility=2.0,
                max_volatility=15.0
            ),
            exit_rules=ExitRules(
                use_trailing_stop=True,
                exit_on_opposite_signal=False,
                max_trade_duration_hours=48.0
            ),
            risk_management=RiskManagement(
                max_position_size_percent=15.0,
                max_positions=3,
                stop_loss_percent=3.0,
                take_profit_percent=6.0,
                trailing_stop_percent=2.0
            ),
            created_by_template="built-in"
        )
        
        # Шаблон 3: Mean Reversion Strategy
        mean_reversion = StrategyTemplate(
            name="Mean Reversion Range Trading",
            description="Стратегия торговли в диапазоне с возвратом к среднему",
            strategy_type=StrategyType.MEAN_REVERSION,
            timeframe=TimeFrame.H4,
            assets=["EURUSD", "USDJPY", "GBPUSD"],
            indicators=[
                IndicatorConfig(
                    name="Bollinger Bands",
                    parameters={"period": 20, "std_dev": 2},
                    weight=1.5
                ),
                IndicatorConfig(
                    name="RSI",
                    parameters={"period": 14, "oversold": 30, "overbought": 70},
                    weight=1.2
                ),
                IndicatorConfig(
                    name="Stochastic",
                    parameters={"k_period": 14, "d_period": 3},
                    weight=1.0
                )
            ],
            entry_rules=EntryRules(
                required_confirmations=2,
                min_signal_strength=0.6,
                allowed_time_sessions=['all'],
                min_volatility=0.5,
                max_volatility=3.0
            ),
            exit_rules=ExitRules(
                use_trailing_stop=False,
                exit_on_opposite_signal=True,
                max_trade_duration_hours=72.0,
                partial_exit_enabled=True,
                partial_exit_levels=[50.0]
            ),
            risk_management=RiskManagement(
                max_position_size_percent=12.0,
                max_positions=2,
                stop_loss_percent=2.5,
                take_profit_percent=5.0,
                trailing_stop_enabled=False
            ),
            created_by_template="built-in"
        )
        
        # Шаблон 4: Breakout Strategy
        breakout = StrategyTemplate(
            name="Volatility Breakout",
            description="Стратегия пробоя уровней с увеличением волатильности",
            strategy_type=StrategyType.BREAKOUT,
            timeframe=TimeFrame.H1,
            assets=["BTCUSDT", "ETHUSDT"],
            indicators=[
                IndicatorConfig(
                    name="ATR",
                    parameters={"period": 14},
                    weight=1.5
                ),
                IndicatorConfig(
                    name="Volume",
                    parameters={"ma_period": 20},
                    weight=1.3
                ),
                IndicatorConfig(
                    name="Support/Resistance",
                    parameters={"lookback": 50},
                    weight=1.2
                )
            ],
            entry_rules=EntryRules(
                required_confirmations=2,
                min_signal_strength=0.75,
                allowed_time_sessions=['overlap_european_american'],
                min_volatility=3.0,
                max_volatility=20.0
            ),
            exit_rules=ExitRules(
                use_trailing_stop=True,
                exit_on_opposite_signal=True,
                max_trade_duration_hours=24.0
            ),
            risk_management=RiskManagement(
                max_position_size_percent=10.0,
                max_positions=2,
                stop_loss_percent=2.0,
                take_profit_percent=5.0,
                trailing_stop_percent=1.5
            ),
            created_by_template="built-in"
        )
        
        # Сохраняем шаблоны в кэш
        self.templates_cache = {
            "scalping": scalping,
            "momentum": momentum,
            "mean_reversion": mean_reversion,
            "breakout": breakout
        }
        
        logger.info(f"✅ Загружено {len(self.templates_cache)} встроенных шаблонов стратегий")
    
    # ==================== УПРАВЛЕНИЕ ШАБЛОНАМИ ====================
    
    def get_template(self, template_name: str) -> Optional[StrategyTemplate]:
        """Получить шаблон по имени"""
        return self.templates_cache.get(template_name)
    
    def get_all_templates(self) -> Dict[str, StrategyTemplate]:
        """Получить все доступные шаблоны"""
        return self.templates_cache.copy()
    
    def list_template_names(self) -> List[str]:
        """Получить список названий шаблонов"""
        return list(self.templates_cache.keys())
    
    async def save_template_as_strategy(
        self, 
        template_name: str, 
        custom_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Сохранить шаблон как активную стратегию в БД"""
        
        template = self.get_template(template_name)
        if not template:
            logger.error(f"Шаблон '{template_name}' не найден")
            return False
        
        # Применяем кастомные параметры если есть
        if custom_params:
            template = self._apply_custom_params(template, custom_params)
        
        # Подготавливаем данные для сохранения
        strategy_data = {
            "name": template.name,
            "description": template.description,
            "is_active": False,  # Не активируем автоматически
            "assets_to_monitor": template.assets,
            "timeframe": template.timeframe.value,
            "indicators": {
                "list": [
                    {
                        "name": ind.name,
                        "enabled": ind.enabled,
                        "parameters": ind.parameters,
                        "weight": ind.weight
                    }
                    for ind in template.indicators
                ]
            },
            "entry_rules": asdict(template.entry_rules),
            "exit_rules": asdict(template.exit_rules),
            "risk_management": asdict(template.risk_management),
            "created_by_ai": False
        }
        
        try:
            success = await db.create_strategy(strategy_data)
            if success:
                logger.info(f"✅ Шаблон '{template_name}' сохранен как стратегия")
            return success
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения шаблона: {e}")
            return False
    
    def _apply_custom_params(
        self, 
        template: StrategyTemplate, 
        custom_params: Dict[str, Any]
    ) -> StrategyTemplate:
        """Применить кастомные параметры к шаблону"""
        
        # Создаем копию шаблона
        import copy
        modified = copy.deepcopy(template)
        
        # Применяем изменения
        if 'assets' in custom_params:
            modified.assets = custom_params['assets']
        
        if 'timeframe' in custom_params:
            modified.timeframe = TimeFrame(custom_params['timeframe'])
        
        if 'risk_management' in custom_params:
            for key, value in custom_params['risk_management'].items():
                if hasattr(modified.risk_management, key):
                    setattr(modified.risk_management, key, value)
        
        if 'entry_rules' in custom_params:
            for key, value in custom_params['entry_rules'].items():
                if hasattr(modified.entry_rules, key):
                    setattr(modified.entry_rules, key, value)
        
        modified.updated_at = datetime.utcnow()
        
        return modified
    
    # ==================== УМНАЯ НАСТРОЙКА СТРАТЕГИЙ ====================
    
    async def recommend_template(
        self, 
        market_conditions: Dict[str, Any]
    ) -> str:
        """Рекомендовать шаблон на основе рыночных условий"""
        
        volatility = market_conditions.get('overall_volatility', 'medium')
        trend = market_conditions.get('market_trend', 'sideways')
        time_of_day = market_conditions.get('time_of_day', 'all')
        
        # Логика выбора шаблона
        if volatility == 'high' and 'overlap' in time_of_day:
            return "scalping"
        
        elif trend in ['bullish', 'bearish'] and volatility == 'medium':
            return "momentum"
        
        elif volatility == 'low' and trend == 'sideways':
            return "mean_reversion"
        
        elif volatility == 'high' and trend != 'sideways':
            return "breakout"
        
        else:
            # По умолчанию - momentum (универсальная стратегия)
            return "momentum"
    
    async def auto_adjust_template_parameters(
        self,
        template_name: str,
        recent_performance: Dict[str, Any]
    ) -> StrategyTemplate:
        """Автоматическая настройка параметров шаблона на основе производительности"""
        
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Шаблон '{template_name}' не найден")
        
        import copy
        adjusted = copy.deepcopy(template)
        
        # Анализ производительности
        win_rate = recent_performance.get('win_rate', 0.5)
        avg_profit = recent_performance.get('average_profit', 0)
        max_drawdown = recent_performance.get('max_drawdown', 0)
        
        # Корректировки на основе производительности
        
        # Если низкий винрейт - ужесточаем фильтры входа
        if win_rate < 0.4:
            adjusted.entry_rules.required_confirmations += 1
            adjusted.entry_rules.min_signal_strength += 0.1
            logger.info(f"📉 Низкий винрейт ({win_rate:.2%}), ужесточаем фильтры входа")
        
        # Если высокий винрейт - можем ослабить фильтры
        elif win_rate > 0.7:
            if adjusted.entry_rules.min_signal_strength > 0.5:
                adjusted.entry_rules.min_signal_strength -= 0.05
            logger.info(f"📈 Высокий винрейт ({win_rate:.2%}), ослабляем фильтры")
        
        # Если большая просадка - снижаем размер позиции
        if max_drawdown > adjusted.risk_management.max_drawdown_percent * 0.7:
            adjusted.risk_management.max_position_size_percent *= 0.8
            adjusted.risk_management.max_positions = max(1, adjusted.risk_management.max_positions - 1)
            logger.info(f"⚠️ Большая просадка ({max_drawdown:.2f}%), снижаем риски")
        
        # Если средняя прибыль низкая - увеличиваем тейк-профит
        if 0 < avg_profit < adjusted.risk_management.stop_loss_percent:
            adjusted.risk_management.take_profit_percent *= 1.2
            logger.info(f"💰 Низкая средняя прибыль, увеличиваем тейк-профит")
        
        adjusted.updated_at = datetime.utcnow()
        
        return adjusted
    
    # ==================== АНАЛИЗ И СРАВНЕНИЕ ====================
    
    def compare_templates(
        self, 
        template_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Сравнить несколько шаблонов"""
        
        comparison = {}
        
        for name in template_names:
            template = self.get_template(name)
            if not template:
                continue
            
            comparison[name] = {
                "type": template.strategy_type.value,
                "timeframe": template.timeframe.value,
                "risk_level": self._calculate_risk_score(template),
                "complexity": len(template.indicators),
                "recommended_for": self._get_recommended_conditions(template)
            }
        
        return comparison
    
    def _calculate_risk_score(self, template: StrategyTemplate) -> str:
        """Рассчитать уровень риска стратегии"""
        risk = template.risk_management
        
        score = (
            risk.max_position_size_percent * 0.3 +
            risk.max_positions * 2 +
            risk.stop_loss_percent * 5
        )
        
        if score < 20:
            return "low"
        elif score < 40:
            return "medium"
        else:
            return "high"
    
    def _get_recommended_conditions(self, template: StrategyTemplate) -> List[str]:
        """Получить рекомендуемые условия для стратегии"""
        conditions = []
        
        if template.strategy_type == StrategyType.SCALPING:
            conditions = ["high_volatility", "peak_hours", "tight_spreads"]
        elif template.strategy_type == StrategyType.MOMENTUM:
            conditions = ["trending_market", "medium_volatility", "clear_direction"]
        elif template.strategy_type == StrategyType.MEAN_REVERSION:
            conditions = ["low_volatility", "ranging_market", "established_levels"]
        elif template.strategy_type == StrategyType.BREAKOUT:
            conditions = ["high_volume", "approaching_key_levels", "increasing_volatility"]
        
        return conditions


# Singleton
strategy_templates_service = StrategyTemplatesService()
