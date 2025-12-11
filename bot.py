"""
Telegram Admin Panel Bot (Bot-2)
Админ-панель для управления Trading Core (Bot-1)
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import settings
from handlers import setup_routers
from middleware import AdminMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('admin_bot.log')
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("🚀 Admin Panel Bot запускается...")
    
    # Проверяем конфигурацию
    try:
        settings.validate()
        logger.info("✅ Конфигурация проверена")
    except Exception as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        raise
    
    # Проверяем подключение к Supabase
    try:
        from database import db
        await db.get_all_users()
        logger.info("✅ Подключение к Supabase установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Supabase: {e}")
        raise
    
    # Отправляем уведомление админам о запуске
    if settings.ADMIN_IDS:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "✅ <b>Admin Panel Bot запущен!</b>\n\nБот готов к работе.",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    logger.info("✅ Admin Panel Bot успешно запущен!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("🛑 Admin Panel Bot останавливается...")
    
    # Уведомляем админов об остановке
    if settings.ADMIN_IDS:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🛑 <b>Admin Panel Bot остановлен</b>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
    
    logger.info("✅ Admin Panel Bot остановлен")


async def main():
    """Главная функция запуска бота"""
    
    # Инициализация бота
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем middleware
    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(AdminMiddleware())
    
    # Регистрируем роутеры
    main_router = setup_routers()
    dp.include_router(main_router)
    
    # Регистрируем обработчики старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем polling
    try:
        logger.info("🤖 Запуск polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске: {e}")
        sys.exit(1)
