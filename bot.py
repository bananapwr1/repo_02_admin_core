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
from services.notification_service import get_notification_service

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
    logger.info("🚀 Admin Core запускается...")
    
    # Инициализируем сервис уведомлений с экземпляром бота
    notification_service = get_notification_service(bot)
    
    # Проверяем конфигурацию
    try:
        settings.validate()
        logger.info("✅ Конфигурация проверена")
    except Exception as e:
        error_msg = f"Ошибка конфигурации: {e}"
        logger.error(f"❌ {error_msg}")
        await notification_service.notify_error(error_msg, "CONFIG")
        raise
    
    # Проверяем подключение к Supabase
    try:
        from database import db
        await db.get_all_users()
        logger.info("✅ Подключение к Supabase установлено (используется Service Role Key)")
    except Exception as e:
        error_msg = f"Ошибка подключения к Supabase: {e}"
        logger.error(f"❌ {error_msg}")
        await notification_service.notify_database_error(str(e))
        raise
    
    # Проверяем доступность шифрования
    if not settings.ENCRYPTION_KEY:
        logger.warning("⚠️ SUPABASE_ENCRYPTION_KEY не установлен, шифрование конфиденциальных данных недоступно")
    
    # Отправляем уведомление о запуске через сервис уведомлений
    await notification_service.notify_startup()

    # Запускаем автономный цикл Ядра (генерация сигналов + reasoning logs)
    try:
        from services.trading_core_service import get_trading_core

        core = get_trading_core()
        bot._core_stop_event = asyncio.Event()  # type: ignore[attr-defined]
        bot._core_task = asyncio.create_task(  # type: ignore[attr-defined]
            core.run_forever(settings.CORE_LOOP_INTERVAL_SECONDS, stop_event=bot._core_stop_event)  # type: ignore[attr-defined]
        )
        logger.info("🧠 Фоновый цикл Ядра запущен")
    except Exception as e:
        # Не валим бот полностью — просто фиксируем, чтобы админ мог починить окружение/стратегии
        logger.error(f"❌ Не удалось запустить фоновый цикл Ядра: {e}")
    
    # Дополнительно отправляем уведомления всем админам
    if settings.ADMIN_IDS:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "✅ <b>Admin Core запущен!</b>\n\n"
                    "🔐 Service Role Key активен\n"
                    "📊 Система готова к управлению стратегиями",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    logger.info("✅ Admin Core успешно запущен!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("🛑 Admin Core останавливается...")
    
    # Уведомляем через сервис уведомлений
    notification_service = get_notification_service(bot)
    await notification_service.notify_shutdown()

    # Останавливаем цикл Ядра, если он был запущен
    try:
        stop_event = getattr(bot, "_core_stop_event", None)
        task = getattr(bot, "_core_task", None)
        if stop_event:
            stop_event.set()
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass
        logger.info("🧠 Фоновый цикл Ядра остановлен")
    except Exception:
        pass
    
    # Дополнительно уведомляем всех админов
    if settings.ADMIN_IDS:
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🛑 <b>Admin Core остановлен</b>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
    
    logger.info("✅ Admin Core остановлен")


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
        error_msg = f"Критическая ошибка при работе бота: {e}"
        logger.error(f"❌ {error_msg}")
        
        # Уведомляем об ошибке
        try:
            notification_service = get_notification_service(bot)
            await notification_service.notify_error(error_msg, "RUNTIME")
        except:
            pass
        
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
