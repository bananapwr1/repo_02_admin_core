"""
Middleware для проверки прав администратора
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config.settings import settings

logger = logging.getLogger(__name__)


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка прав администратора"""
        
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)
        
        # Доступ строго администраторам из конфигурации
        if not settings.ADMIN_IDS:
            logger.error("❌ ADMIN_USER_ID/ADMIN_IDS не настроен — блокируем доступ по умолчанию")
            if isinstance(event, Message):
                await event.answer("🚫 Доступ запрещён. Администратор не настроен.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Доступ запрещён.", show_alert=True)
            return
        
        # Проверяем права
        if user_id not in settings.ADMIN_IDS:
            logger.warning(f"🚫 Пользователь {user_id} попытался получить доступ к админ-панели")
            
            if isinstance(event, Message):
                await event.answer("🚫 У вас нет доступа к админ-панели.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 У вас нет доступа к этой функции.", show_alert=True)
            
            return
        
        # Логируем действия админа
        if isinstance(event, Message):
            logger.info(f"👤 Админ {user_id}: {event.text}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"👤 Админ {user_id}: callback {event.data}")
        
        # Продолжаем обработку
        return await handler(event, data)
