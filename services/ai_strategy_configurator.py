"""
AI Strategy Configurator (Smart Configurator)
Умный настройщик стратегий на основе анализа данных, статистики и рыночных условий
Работает НЕ через чат, а через анализ данных и автоматическую настройку параметров
"""
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from database import db
from services.data_aggregation_service import aggregation_service, AssetStatistics
from services.strategy_templates_service import (
    strategy_templates_service, 
    StrategyTemplate,
    RiskManagement
)

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationRecommendation:
    """Рекомендация по настройке стратегии"""
    parameter_path: str  # Например: "risk_management.stop_loss_percent"
    current_value: Any
    recommended_value: Any
    reason: str
    confidence: float  # 0.0 - 1.0
    impact: str  # "low", "medium", "high"


@dataclass
class StrategyAnalysis:
    """Результат анализа стратегии"""
    strategy_name: str
    overall_score: float  # 0-100
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[ConfigurationRecommendation]
    market_fit: str  # "excellent", "good", "poor"
    suggested_adjustments: Dict[str, Any]


class AIStrategyConfigurator:
    """Умный конфигуратор стратегий на основе данных"""
    
    def __init__(self):
        self.analysis_history: List[StrategyAnalysis] = []
        self.optimization_cycles = 0
        
        # Пороговые значения для оценки
        self.performance_thresholds = {
            'excellent_win_rate': 0.65,
            'good_win_rate': 0.50,
            'poor_win_rate': 0.35,
            'max_acceptable_drawdown': 20.0,
            'min_sharpe_ratio': 0.5,
            'min_trades_for_analysis': 10
        }
    
    # ==================== ОСНОВНОЙ АНАЛИЗ И НАСТРОЙКА ====================
    
    async def analyze_and_configure_strategy(
        self,
        strategy: Dict[str, Any],
        time_period_days: int = 7
    ) -> StrategyAnalysis:
        """
        Проанализировать стратегию и предложить оптимальную конфигурацию
        Это основной метод умного настройщика
        """
        
        strategy_name = strategy.get('name', 'Unknown')
        logger.info(f"🧠 Анализ и настройка стратегии '{strategy_name}'")
        
        # 1. Собираем статистику по активам стратегии
        assets = strategy.get('assets_to_monitor', [])
        if not assets:
            logger.warning("⚠️ У стратегии нет активов для мониторинга")
            assets = ['BTCUSDT']  # Дефолтный актив
        
        # Получаем агрегированную статистику
        period = 'weekly' if time_period_days >= 7 else 'daily'
        stats_by_asset = await aggregation_service.get_all_assets_statistics(assets, period)
        
        # 2. Анализируем текущие рыночные условия
        market_conditions = await aggregation_service.get_market_conditions()
        
        # 3. Оцениваем производительность
        performance_score, strengths, weaknesses = self._evaluate_performance(stats_by_asset)
        
        # 4. Определяем соответствие рынку
        market_fit = self._assess_market_fit(strategy, market_conditions, stats_by_asset)
        
        # 5. Генерируем рекомендации по настройке
        recommendations = self._generate_recommendations(
            strategy,
            stats_by_asset,
            market_conditions,
            weaknesses
        )
        
        # 6. Формируем пакет предлагаемых изменений
        suggested_adjustments = self._compile_adjustments(recommendations)
        
        # Создаем результат анализа
        analysis = StrategyAnalysis(
            strategy_name=strategy_name,
            overall_score=performance_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            market_fit=market_fit,
            suggested_adjustments=suggested_adjustments
        )
        
        self.analysis_history.append(analysis)
        
        logger.info(
            f"✅ Анализ завершен: Оценка={performance_score:.1f}/100, "
            f"Соответствие рынку={market_fit}, "
            f"Рекомендаций={len(recommendations)}"
        )
        
        return analysis
    
    async def auto_optimize_strategy(
        self,
        strategy_id: int,
        apply_changes: bool = False
    ) -> Tuple[StrategyAnalysis, Optional[Dict[str, Any]]]:
        """
        Автоматическая оптимизация стратегии
        Возвращает (анализ, оптимизированная_стратегия)
        """
        
        logger.info(f"🔧 Автооптимизация стратегии ID={strategy_id}")
        
        # Получаем текущую стратегию
        strategies = await db.get_all_strategies()
        strategy = next((s for s in strategies if s.get('id') == strategy_id), None)
        
        if not strategy:
            raise ValueError(f"Стратегия с ID {strategy_id} не найдена")
        
        # Анализируем
        analysis = await self.analyze_and_configure_strategy(strategy)
        
        # Если оценка слишком низкая, предлагаем смену стратегии
        if analysis.overall_score < 30:
            logger.warning(
                f"⚠️ Стратегия показывает очень низкую эффективность ({analysis.overall_score:.1f}/100). "
                f"Рекомендуется переключение на другую стратегию."
            )
        
        # Применяем оптимизацию
        optimized_strategy = None
        if apply_changes and analysis.suggested_adjustments:
            optimized_strategy = await self._apply_optimizations(
                strategy,
                analysis.suggested_adjustments
            )
            logger.info("✅ Оптимизация применена")
        
        self.optimization_cycles += 1
        
        return analysis, optimized_strategy
    
    # ==================== ОЦЕНКА ПРОИЗВОДИТЕЛЬНОСТИ ====================
    
    def _evaluate_performance(
        self,
        stats_by_asset: Dict[str, AssetStatistics]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Оценить производительность на основе статистики
        Возвращает (оценка, сильные_стороны, слабые_стороны)
        """
        
        if not stats_by_asset:
            return 50.0, [], ["Недостаточно данных для анализа"]
        
        # Агрегируем метрики по всем активам
        total_trades = sum(s.total_trades for s in stats_by_asset.values())
        avg_win_rate = sum(s.win_rate for s in stats_by_asset.values()) / len(stats_by_asset)
        total_net_profit = sum(s.net_profit for s in stats_by_asset.values())
        avg_sharpe = sum(s.sharpe_ratio for s in stats_by_asset.values()) / len(stats_by_asset)
        max_drawdown = max(s.max_drawdown for s in stats_by_asset.values())
        
        strengths = []
        weaknesses = []
        score = 50.0  # Базовая оценка
        
        # Проверяем достаточность данных
        if total_trades < self.performance_thresholds['min_trades_for_analysis']:
            weaknesses.append(f"Недостаточно трейдов для полного анализа ({total_trades} < {self.performance_thresholds['min_trades_for_analysis']})")
            return score, strengths, weaknesses
        
        # Оценка винрейта
        if avg_win_rate >= self.performance_thresholds['excellent_win_rate']:
            strengths.append(f"Отличный винрейт: {avg_win_rate:.1%}")
            score += 20
        elif avg_win_rate >= self.performance_thresholds['good_win_rate']:
            strengths.append(f"Хороший винрейт: {avg_win_rate:.1%}")
            score += 10
        elif avg_win_rate < self.performance_thresholds['poor_win_rate']:
            weaknesses.append(f"Низкий винрейт: {avg_win_rate:.1%}")
            score -= 15
        
        # Оценка прибыльности
        if total_net_profit > 0:
            strengths.append(f"Положительная чистая прибыль: {total_net_profit:.2f}")
            score += 15
        else:
            weaknesses.append(f"Отрицательная чистая прибыль: {total_net_profit:.2f}")
            score -= 20
        
        # Оценка Sharpe Ratio
        if avg_sharpe >= self.performance_thresholds['min_sharpe_ratio']:
            strengths.append(f"Хороший риск-профиль (Sharpe: {avg_sharpe:.2f})")
            score += 10
        elif avg_sharpe < 0:
            weaknesses.append(f"Плохой риск-профиль (Sharpe: {avg_sharpe:.2f})")
            score -= 10
        
        # Оценка просадки
        if max_drawdown > self.performance_thresholds['max_acceptable_drawdown']:
            weaknesses.append(f"Высокая максимальная просадка: {max_drawdown:.2f}%")
            score -= 15
        else:
            strengths.append(f"Контролируемая просадка: {max_drawdown:.2f}%")
            score += 10
        
        # Оценка волатильности результатов
        volatilities = [s.price_volatility for s in stats_by_asset.values()]
        avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0
        
        if 1.0 < avg_volatility < 5.0:
            strengths.append(f"Оптимальная волатильность торговли: {avg_volatility:.2f}%")
            score += 5
        elif avg_volatility > 10.0:
            weaknesses.append(f"Очень высокая волатильность: {avg_volatility:.2f}%")
            score -= 10
        
        # Ограничиваем оценку в диапазоне 0-100
        score = max(0, min(100, score))
        
        return score, strengths, weaknesses
    
    def _assess_market_fit(
        self,
        strategy: Dict[str, Any],
        market_conditions: Any,
        stats: Dict[str, AssetStatistics]
    ) -> str:
        """Оценить соответствие стратегии текущему рынку"""
        
        # Извлекаем тип стратегии из названия
        strategy_name = strategy.get('name', '').lower()
        
        volatility = market_conditions.overall_volatility
        trend = market_conditions.market_trend
        is_peak = market_conditions.is_peak_hours
        
        # Логика оценки соответствия
        fit_score = 0
        
        # Scalping стратегии
        if 'scalp' in strategy_name:
            if volatility == 'high' and is_peak:
                fit_score = 3  # Отлично
            elif volatility == 'medium':
                fit_score = 2  # Хорошо
            else:
                fit_score = 1  # Плохо
        
        # Momentum стратегии
        elif 'momentum' in strategy_name or 'trend' in strategy_name:
            if trend in ['bullish', 'bearish'] and volatility in ['medium', 'high']:
                fit_score = 3
            elif trend != 'sideways':
                fit_score = 2
            else:
                fit_score = 1
        
        # Mean reversion стратегии
        elif 'reversion' in strategy_name or 'range' in strategy_name:
            if volatility == 'low' and trend == 'sideways':
                fit_score = 3
            elif volatility == 'low':
                fit_score = 2
            else:
                fit_score = 1
        
        # Breakout стратегии
        elif 'breakout' in strategy_name:
            if volatility == 'high' and trend != 'sideways':
                fit_score = 3
            elif volatility == 'high':
                fit_score = 2
            else:
                fit_score = 1
        
        else:
            fit_score = 2  # Неизвестный тип, средняя оценка
        
        # Преобразуем в текстовую оценку
        if fit_score >= 3:
            return "excellent"
        elif fit_score >= 2:
            return "good"
        else:
            return "poor"
    
    # ==================== ГЕНЕРАЦИЯ РЕКОМЕНДАЦИЙ ====================
    
    def _generate_recommendations(
        self,
        strategy: Dict[str, Any],
        stats: Dict[str, AssetStatistics],
        market_conditions: Any,
        weaknesses: List[str]
    ) -> List[ConfigurationRecommendation]:
        """Сгенерировать рекомендации по улучшению стратегии"""
        
        recommendations = []
        
        if not stats:
            return recommendations
        
        # Агрегируем метрики
        avg_win_rate = sum(s.win_rate for s in stats.values()) / len(stats)
        max_drawdown = max(s.max_drawdown for s in stats.values())
        total_net_profit = sum(s.net_profit for s in stats.values())
        
        # Рекомендация 1: Корректировка stop-loss при высокой просадке
        if max_drawdown > 15.0:
            current_sl = self._extract_risk_param(strategy, 'stop_loss_percent', 2.0)
            new_sl = current_sl * 0.8  # Уменьшаем на 20%
            
            recommendations.append(ConfigurationRecommendation(
                parameter_path="risk_management.stop_loss_percent",
                current_value=current_sl,
                recommended_value=round(new_sl, 2),
                reason=f"Высокая максимальная просадка ({max_drawdown:.2f}%). Уменьшение stop-loss поможет ограничить потери.",
                confidence=0.85,
                impact="high"
            ))
        
        # Рекомендация 2: Корректировка take-profit при низком винрейте
        if avg_win_rate < 0.45 and total_net_profit < 0:
            current_tp = self._extract_risk_param(strategy, 'take_profit_percent', 4.0)
            new_tp = current_tp * 0.7  # Берем прибыль раньше
            
            recommendations.append(ConfigurationRecommendation(
                parameter_path="risk_management.take_profit_percent",
                current_value=current_tp,
                recommended_value=round(new_tp, 2),
                reason=f"Низкий винрейт ({avg_win_rate:.1%}). Более ранний take-profit может увеличить количество успешных сделок.",
                confidence=0.75,
                impact="medium"
            ))
        
        # Рекомендация 3: Снижение размера позиции при убыточности
        if total_net_profit < -50:
            current_pos = self._extract_risk_param(strategy, 'max_position_size_percent', 10.0)
            new_pos = current_pos * 0.7
            
            recommendations.append(ConfigurationRecommendation(
                parameter_path="risk_management.max_position_size_percent",
                current_value=current_pos,
                recommended_value=round(new_pos, 1),
                reason="Убыточная торговля. Снижение размера позиции уменьшит риски.",
                confidence=0.9,
                impact="high"
            ))
        
        # Рекомендация 4: Увеличение фильтров при низком винрейте
        if avg_win_rate < 0.40:
            recommendations.append(ConfigurationRecommendation(
                parameter_path="entry_rules.min_signal_strength",
                current_value=0.6,
                recommended_value=0.75,
                reason=f"Низкий винрейт ({avg_win_rate:.1%}). Более строгая фильтрация сигналов может улучшить качество входов.",
                confidence=0.8,
                impact="medium"
            ))
        
        # Рекомендация 5: Изменение таймфрейма при неподходящих условиях
        current_timeframe = strategy.get('timeframe', '1h')
        if market_conditions.overall_volatility == 'high' and current_timeframe in ['4h', '1d']:
            recommendations.append(ConfigurationRecommendation(
                parameter_path="timeframe",
                current_value=current_timeframe,
                recommended_value='1h',
                reason="Высокая волатильность. Меньший таймфрейм позволит быстрее реагировать на изменения.",
                confidence=0.65,
                impact="medium"
            ))
        
        # Рекомендация 6: Включение trailing stop при хорошем винрейте
        if avg_win_rate > 0.6 and total_net_profit > 0:
            recommendations.append(ConfigurationRecommendation(
                parameter_path="risk_management.trailing_stop_enabled",
                current_value=False,
                recommended_value=True,
                reason="Высокий винрейт и прибыльность. Trailing stop поможет максимизировать прибыль.",
                confidence=0.7,
                impact="low"
            ))
        
        logger.info(f"💡 Сгенерировано {len(recommendations)} рекомендаций")
        
        return recommendations
    
    def _extract_risk_param(
        self,
        strategy: Dict[str, Any],
        param_name: str,
        default: float
    ) -> float:
        """Извлечь параметр управления рисками из стратегии"""
        risk_mgmt = strategy.get('risk_management', {})
        if isinstance(risk_mgmt, dict):
            return risk_mgmt.get(param_name, default)
        return default
    
    def _compile_adjustments(
        self,
        recommendations: List[ConfigurationRecommendation]
    ) -> Dict[str, Any]:
        """Скомпилировать рекомендации в структуру изменений"""
        
        adjustments = {}
        
        for rec in recommendations:
            # Разбираем путь параметра
            parts = rec.parameter_path.split('.')
            
            # Создаем вложенную структуру
            current = adjustments
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Устанавливаем значение
            current[parts[-1]] = rec.recommended_value
        
        return adjustments
    
    # ==================== ПРИМЕНЕНИЕ ОПТИМИЗАЦИИ ====================
    
    async def _apply_optimizations(
        self,
        strategy: Dict[str, Any],
        adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Применить оптимизации к стратегии"""
        
        strategy_id = strategy.get('id')
        if not strategy_id:
            logger.error("У стратегии нет ID, невозможно применить изменения")
            return strategy
        
        # Глубокое слияние изменений
        optimized = self._deep_merge(strategy.copy(), adjustments)
        
        # Обновляем метаданные
        optimized['updated_at'] = datetime.utcnow().isoformat()
        
        try:
            # Сохраняем обновленную стратегию
            # Так как у нас нет метода update_strategy, создаем новую с обновленными параметрами
            # и деактивируем старую
            await db.update_strategy_status(strategy_id, False)
            
            # Создаем оптимизированную версию
            new_strategy_data = {
                "name": f"{optimized['name']} (Optimized)",
                "description": optimized.get('description', '') + " [AI Optimized]",
                "is_active": False,
                "assets_to_monitor": optimized.get('assets_to_monitor', []),
                "timeframe": optimized.get('timeframe', '1h'),
                "indicators": optimized.get('indicators', {}),
                "entry_rules": optimized.get('entry_rules', {}),
                "exit_rules": optimized.get('exit_rules', {}),
                "risk_management": optimized.get('risk_management', {}),
                "created_by_ai": True
            }
            
            await db.create_strategy(new_strategy_data)
            
            logger.info(f"✅ Создана оптимизированная версия стратегии '{optimized['name']}'")
            
            # Логируем оптимизацию
            await db.client.table("system_logs").insert({
                "level": "INFO",
                "message": f"Strategy optimized: {strategy['name']}",
                "details": {
                    "original_strategy_id": strategy_id,
                    "adjustments": adjustments,
                    "optimization_cycle": self.optimization_cycles
                },
                "source": "ai_strategy_configurator"
            }).execute()
            
        except Exception as e:
            logger.error(f"Ошибка применения оптимизации: {e}")
        
        return optimized
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Глубокое слияние словарей"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    # ==================== ОТЧЕТЫ И СТАТИСТИКА ====================
    
    def get_analysis_report(self, analysis: StrategyAnalysis) -> str:
        """Получить текстовый отчет анализа"""
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║         ОТЧЕТ АНАЛИЗА СТРАТЕГИИ: {analysis.strategy_name:<25}║
╚══════════════════════════════════════════════════════════════╝

📊 ОБЩАЯ ОЦЕНКА: {analysis.overall_score:.1f}/100
🎯 СООТВЕТСТВИЕ РЫНКУ: {analysis.market_fit.upper()}

✅ СИЛЬНЫЕ СТОРОНЫ:
"""
        for strength in analysis.strengths:
            report += f"   • {strength}\n"
        
        if not analysis.strengths:
            report += "   • Нет выявленных сильных сторон\n"
        
        report += "\n⚠️ СЛАБЫЕ СТОРОНЫ:\n"
        for weakness in analysis.weaknesses:
            report += f"   • {weakness}\n"
        
        if not analysis.weaknesses:
            report += "   • Нет выявленных слабых сторон\n"
        
        report += f"\n💡 РЕКОМЕНДАЦИИ ({len(analysis.recommendations)}):\n"
        for i, rec in enumerate(analysis.recommendations, 1):
            report += f"   {i}. {rec.parameter_path}\n"
            report += f"      {rec.current_value} → {rec.recommended_value}\n"
            report += f"      Причина: {rec.reason}\n"
            report += f"      Уверенность: {rec.confidence:.0%}, Влияние: {rec.impact}\n\n"
        
        if not analysis.recommendations:
            report += "   • Текущая конфигурация оптимальна\n"
        
        report += "═" * 64 + "\n"
        
        return report
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Получить историю оптимизаций"""
        return [
            {
                'strategy_name': a.strategy_name,
                'score': a.overall_score,
                'market_fit': a.market_fit,
                'recommendations_count': len(a.recommendations)
            }
            for a in self.analysis_history
        ]


# Singleton
ai_configurator = AIStrategyConfigurator()
