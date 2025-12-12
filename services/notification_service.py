"""
Сервис уведомлений для Admin Core
Отправляет системные уведомления администраторам через Telegram
"""
import logging
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений администраторам"""
    
    def __init__(self, bot: Optional[Bot] = None):
        """
        Инициализация сервиса уведомлений
        
        Args:
            bot: Экземпляр Telegram бота (если None, будет создан новый)
        """
        self.bot = bot
        # Repo 02: единый администратор, уведомления отправляем ему же
        self.admin_chat_id = settings.ADMIN_USER_ID
        self._bot_token = settings.TELEGRAM_BOT_TOKEN
    
    async def _get_bot(self) -> Optional[Bot]:
        """Получить экземпляр бота"""
        if self.bot:
            return self.bot
        
        # Если бот не передан, создаем новый экземпляр
        if self._bot_token:
            return Bot(token=self._bot_token)
        
        return None
    
    async def send_notification(
        self, 
        message: str, 
        level: str = "INFO",
        parse_mode: ParseMode = ParseMode.HTML
    ) -> bool:
        """
        Отправить уведомление администратору
        
        Args:
            message: Текст сообщения
            level: Уровень важности (INFO, WARNING, ERROR, CRITICAL)
            parse_mode: Режим парсинга (HTML или Markdown)
        
        Returns:
            bool: True если уведомление отправлено успешно
        """
        if not self.admin_chat_id:
            logger.warning("⚠️ ADMIN_USER_ID не установлен, уведомление не отправлено")
            return False
        
        try:
            bot = await self._get_bot()
            if not bot:
                logger.error("❌ Не удалось получить экземпляр бота для отправки уведомления")
                return False
            
            # Добавляем эмодзи в зависимости от уровня
            emoji_map = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🔥"
            }
            emoji = emoji_map.get(level.upper(), "📢")
            
            formatted_message = f"{emoji} <b>{level.upper()}</b>\n\n{message}"
            
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=formatted_message,
                parse_mode=parse_mode
            )
            
            logger.info(f"✅ Уведомление отправлено администратору (уровень: {level})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
            return False
    
    async def notify_startup(self) -> bool:
        """Уведомление о запуске Admin Core"""
        message = (
            "<b>Admin Core запущен успешно!</b>\n\n"
            "✅ Подключение к Supabase установлено\n"
            "✅ Система готова к работе\n"
            "✅ Service Role Key активен (полный доступ к БД)"
        )
        return await self.send_notification(message, level="INFO")
    
    async def notify_shutdown(self) -> bool:
        """Уведомление об остановке Admin Core"""
        message = "<b>Admin Core остановлен</b>"
        return await self.send_notification(message, level="WARNING")
    
    async def notify_error(self, error_message: str, error_type: str = "SYSTEM") -> bool:
        """
        Уведомление о критической ошибке
        
        Args:
            error_message: Описание ошибки
            error_type: Тип ошибки (SYSTEM, DATABASE, ENCRYPTION, etc.)
        """
        message = (
            f"<b>Критическая ошибка: {error_type}</b>\n\n"
            f"<code>{error_message}</code>\n\n"
            "Требуется внимание администратора!"
        )
        return await self.send_notification(message, level="CRITICAL")
    
    async def notify_database_error(self, error_message: str) -> bool:
        """Уведомление об ошибке подключения к Supabase"""
        message = (
            "<b>Ошибка подключения к Supabase</b>\n\n"
            f"<code>{error_message}</code>\n\n"
            "Проверьте:\n"
            "• SUPABASE_BASE_URL\n"
            "• SUPABASE_SERVICE_KEY (или SUPABASE_KEY)\n"
            "• Доступность Supabase API"
        )
        return await self.send_notification(message, level="CRITICAL")
    
    async def notify_encryption_error(self, error_message: str) -> bool:
        """Уведомление об ошибке шифрования"""
        message = (
            "<b>Ошибка шифрования данных</b>\n\n"
            f"<code>{error_message}</code>\n\n"
            "Проверьте SUPABASE_ENCRYPTION_KEY в конфигурации"
        )
        return await self.send_notification(message, level="ERROR")
    
    async def notify_strategy_created(self, strategy_name: str, strategy_id: int) -> bool:
        """Уведомление о создании новой стратегии"""
        message = (
            f"<b>Создана новая стратегия</b>\n\n"
            f"📊 Название: <b>{strategy_name}</b>\n"
            f"🆔 ID: <code>{strategy_id}</code>"
        )
        return await self.send_notification(message, level="INFO")
    
    async def notify_strategy_activated(self, strategy_name: str, strategy_id: int) -> bool:
        """Уведомление об активации стратегии"""
        message = (
            f"<b>Стратегия активирована</b>\n\n"
            f"📊 Название: <b>{strategy_name}</b>\n"
            f"🆔 ID: <code>{strategy_id}</code>\n"
            f"✅ Статус: <b>АКТИВНА</b>"
        )
        return await self.send_notification(message, level="INFO")
    
    async def notify_strategy_deactivated(self, strategy_name: str, strategy_id: int) -> bool:
        """Уведомление о деактивации стратегии"""
        message = (
            f"<b>Стратегия деактивирована</b>\n\n"
            f"📊 Название: <b>{strategy_name}</b>\n"
            f"🆔 ID: <code>{strategy_id}</code>\n"
            f"⏸️ Статус: <b>НЕАКТИВНА</b>"
        )
        return await self.send_notification(message, level="WARNING")


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(bot: Optional[Bot] = None) -> NotificationService:
    """
    Получить экземпляр сервиса уведомлений (Singleton)
    
    Args:
        bot: Экземпляр Telegram бота
    """
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService(bot)
    elif bot and not _notification_service.bot:
        # Обновляем бота, если он был передан
        _notification_service.bot = bot
    
    return _notification_service
