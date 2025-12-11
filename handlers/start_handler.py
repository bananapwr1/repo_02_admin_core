"""
Обработчик команды /start и главного меню
"""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards import get_main_menu_keyboard
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start", "menu"))
async def cmd_start(message: Message):
    """Главное меню (/start или /menu)"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    logger.info(f"Админ {user_id} ({username}) запустил бота")
    
    welcome_text = f"""
🎛 <b>{settings.BOT_NAME}</b>

Добро пожаловать, <b>{username}</b>!

Это <b>админский интерфейс Admin Core</b> для управления Ядром.

🔐 <b>Доступ:</b> только для ADMIN_USER_ID
🗄 <b>База:</b> Supabase через <b>SUPABASE_SERVICE_ROLE_KEY</b>

Выберите раздел:
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 <b>Справка по командам</b>

<b>Основные команды:</b>
/start, /menu - Главное меню
/help - Эта справка

<b>Разделы меню:</b>
🎯 Управление Стратегиями - создать/редактировать/активировать
🧠 Логика Анализа Ядра - последние решения/рассуждения (decision logs)
⚙️ Настройки Бота Ядра - ключи/токены и системная информация
"""
    await message.answer(help_text, parse_mode="HTML")
