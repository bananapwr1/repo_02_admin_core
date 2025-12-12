"""
Обработчик команды /start и главного меню
"""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_inline_keyboard
from config.settings import settings
from utils import safe_delete_message, show_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Главное меню (/start или /menu)"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    logger.info(f"Админ {user_id} ({username}) запустил бота")
    
    # Удаляем команду /start, чтобы чат не засорять
    await safe_delete_message(message)

    welcome_text = (
        f"🎛 <b>{settings.BOT_NAME}</b>\n\n"
        f"Добро пожаловать, <b>{username}</b>!\n\n"
        "Это <b>админский интерфейс Admin Core</b> для управления Ядром.\n\n"
        "Выберите раздел (или используйте команды):\n"
        "• /menu • /strategies • /analysis • /settings • /users • /tokens"
    )

    await show_menu(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=welcome_text,
        reply_markup=get_main_menu_inline_keyboard(),
        parse_mode="HTML",
        prefer_edit=False,
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 <b>Справка по командам</b>

<b>Основные команды:</b>
/start, /menu - Главное меню
/help - Эта справка
/strategies - Управление стратегиями
/analysis - Логика анализа ядра
/settings - Настройки
/users - Пользователи
/tokens - Токены приглашения

<b>Разделы меню:</b>
🎯 Управление Стратегиями - создать/редактировать/активировать
🧠 Логика Анализа Ядра - последние решения/рассуждения (decision logs)
⚙️ Настройки Бота Ядра - ключи/токены и системная информация
"""
    await message.answer(help_text, parse_mode="HTML")
