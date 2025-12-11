"""
AI Strategy Service
Сервис для диалоговой разработки торговых стратегий с использованием OpenAI
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import AsyncOpenAI
from config.settings import settings
from database import db

logger = logging.getLogger(__name__)


class AIStrategyService:
    """Сервис для работы с AI-чатом разработки стратегий"""
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.warning("⚠️ OPENAI_API_KEY не установлен, AI-чат недоступен")
        
        # Хранилище контекста диалогов (user_id -> messages)
        self.conversations: Dict[int, List[Dict[str, str]]] = {}
    
    def get_system_prompt(self) -> str:
        """Системный промпт для AI-ассистента стратегий"""
        return """Ты - AI-ассистент для разработки торговых стратегий на финансовых рынках (Forex, криптовалюты).

Твоя задача:
1. Анализировать предоставленные исторические данные и статистику
2. Обсуждать с администратором торговые стратегии
3. Предлагать конкретные правила и условия для стратегий
4. После согласования с администратором - генерировать финальную стратегию в JSON формате

Формат стратегии для сохранения:
{
    "name": "Название стратегии",
    "description": "Подробное описание логики",
    "assets_to_monitor": ["BTCUSDT", "EURUSD=X"],
    "timeframe": "1h",
    "indicators": {
        "rsi": {"period": 14, "oversold": 30, "overbought": 70},
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "ema": {"periods": [20, 50, 200]}
    },
    "entry_rules": {
        "long": "RSI < 30 AND MACD cross UP AND price > EMA20",
        "short": "RSI > 70 AND MACD cross DOWN AND price < EMA20"
    },
    "exit_rules": {
        "take_profit": 2.0,
        "stop_loss": 1.0,
        "trailing_stop": true
    },
    "risk_management": {
        "max_position_size": 10.0,
        "max_daily_trades": 5,
        "max_drawdown": 15.0
    }
}

Когда администратор готов сохранить стратегию, отправь сообщение в формате:
SAVE_STRATEGY:
[JSON стратегии]

Будь конкретным, используй технический анализ и обоснованные решения."""

    async def get_trading_context(self) -> str:
        """Получить контекст текущей торговой активности"""
        try:
            # Получаем статистику
            stats = await db.get_trading_statistics()
            
            # Получаем последние логи решений
            decision_logs = await db.get_decision_logs(limit=10)
            
            # Получаем активную стратегию
            active_strategy = await db.get_active_strategy()
            
            context = f"""
📊 ТЕКУЩАЯ СТАТИСТИКА:
- Всего сигналов: {stats.get('total_signals', 0)}
- Всего трейдов: {stats.get('total_trades', 0)}
- Активных пользователей: {stats.get('active_users', 0)}

🎯 АКТИВНАЯ СТРАТЕГИЯ:
{json.dumps(active_strategy, indent=2, ensure_ascii=False) if active_strategy else "Нет активной стратегии"}

📝 ПОСЛЕДНИЕ РЕШЕНИЯ AI:
"""
            for log in decision_logs[:5]:
                context += f"- {log.get('created_at', '')}: {log.get('reasoning', 'N/A')[:100]}...\n"
            
            return context
        except Exception as e:
            logger.error(f"Ошибка получения контекста: {e}")
            return "Не удалось загрузить контекст торговли."
    
    def init_conversation(self, user_id: int):
        """Инициализация нового диалога"""
        self.conversations[user_id] = [
            {
                "role": "system",
                "content": self.get_system_prompt()
            }
        ]
    
    async def send_message(self, user_id: int, message: str) -> str:
        """Отправить сообщение AI и получить ответ"""
        if not self.client:
            return "❌ AI-чат недоступен. Установите OPENAI_API_KEY в настройках."
        
        # Инициализируем диалог если его нет
        if user_id not in self.conversations:
            self.init_conversation(user_id)
        
        # Добавляем сообщение пользователя
        self.conversations[user_id].append({
            "role": "user",
            "content": message
        })
        
        try:
            # Получаем ответ от OpenAI
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=self.conversations[user_id],
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Сохраняем ответ в историю
            self.conversations[user_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Ошибка AI-чата: {e}")
            return f"❌ Ошибка при обращении к AI: {str(e)}"
    
    async def process_message_with_context(self, user_id: int, message: str) -> tuple[str, Optional[Dict]]:
        """
        Обработать сообщение с учетом контекста торговли
        Возвращает (ответ, стратегия_для_сохранения или None)
        """
        # Если это первое сообщение, добавляем контекст
        if user_id not in self.conversations or len(self.conversations[user_id]) <= 1:
            context = await self.get_trading_context()
            message = f"{context}\n\n---\n\nАдминистратор: {message}"
        
        response = await self.send_message(user_id, message)
        
        # Проверяем, хочет ли AI сохранить стратегию
        strategy_data = None
        if "SAVE_STRATEGY:" in response:
            try:
                # Извлекаем JSON стратегии
                json_start = response.index("{")
                json_end = response.rindex("}") + 1
                strategy_json = response[json_start:json_end]
                strategy_data = json.loads(strategy_json)
                
                # Добавляем служебные поля
                strategy_data["is_active"] = False
                strategy_data["created_at"] = datetime.utcnow().isoformat()
                strategy_data["created_by_ai"] = True
                
            except Exception as e:
                logger.error(f"Ошибка парсинга стратегии: {e}")
        
        return response, strategy_data
    
    def reset_conversation(self, user_id: int):
        """Сбросить диалог пользователя"""
        if user_id in self.conversations:
            del self.conversations[user_id]
        self.init_conversation(user_id)
    
    def get_conversation_history(self, user_id: int) -> List[Dict[str, str]]:
        """Получить историю диалога"""
        return self.conversations.get(user_id, [])
    
    async def save_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """Сохранить стратегию в базу данных"""
        try:
            success = await db.create_strategy(strategy_data)
            if success:
                logger.info(f"✅ Стратегия '{strategy_data.get('name')}' сохранена")
            return success
        except Exception as e:
            logger.error(f"Ошибка сохранения стратегии: {e}")
            return False
    
    async def analyze_strategy_performance(self, strategy_id: int) -> str:
        """Анализ производительности стратегии"""
        if not self.client:
            return "AI-анализ недоступен"
        
        try:
            # Получаем данные о стратегии и её результатах
            strategies = await db.get_all_strategies()
            strategy = next((s for s in strategies if s['id'] == strategy_id), None)
            
            if not strategy:
                return "Стратегия не найдена"
            
            # Получаем статистику
            stats = await db.get_trading_statistics()
            
            # Формируем запрос к AI
            prompt = f"""
Проанализируй производительность следующей торговой стратегии:

Стратегия: {json.dumps(strategy, indent=2, ensure_ascii=False)}

Статистика: {json.dumps(stats, indent=2, ensure_ascii=False)}

Предоставь:
1. Анализ сильных сторон стратегии
2. Выявленные слабые места
3. Рекомендации по улучшению
4. Предложения по оптимизации параметров
"""
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка анализа стратегии: {e}")
            return f"Ошибка анализа: {str(e)}"


# Singleton
ai_service = AIStrategyService()
