"""
Обработчик настроек бота
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    """Состояния для настроек"""
    editing_name = State()
    editing_welcome = State()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    bot_settings = await db.get_bot_settings()
    
    text = f"""
⚙️ <b>Настройки бота</b>

📛 Название: {bot_settings.get('name', settings.BOT_NAME) if bot_settings else settings.BOT_NAME}
👋 Приветствие: {bot_settings.get('welcome_message', settings.WELCOME_MESSAGE)[:50] if bot_settings else settings.WELCOME_MESSAGE[:50]}...

<i>Выберите параметр для редактирования:</i>
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Изменить название", callback_data="settings_edit_name")],
        [InlineKeyboardButton(text="👋 Изменить приветствие", callback_data="settings_edit_welcome")],
        [InlineKeyboardButton(text="ℹ️ Системная информация", callback_data="settings_info")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "ℹ️ Помощь")
async def help_menu(message: Message):
    """Помощь"""
    from handlers.start_handler import cmd_help
    await cmd_help(message)


@router.callback_query(F.data == "settings_info")
async def show_system_info(callback: CallbackQuery):
    """Показать системную информацию"""
    await callback.answer()
    
    import sys
    import aiogram
    
    stats = await db.get_trading_statistics()
    
    text = f"""
ℹ️ <b>Системная информация</b>

<b>Бот:</b>
├ Название: {settings.BOT_NAME}
├ Версия aiogram: {aiogram.__version__}
└ Python: {sys.version.split()[0]}

<b>База данных:</b>
├ Supabase: ✅ Подключено
└ URL: {settings.SUPABASE_URL}

<b>AI:</b>
├ OpenAI: {"✅ Настроен" if settings.OPENAI_API_KEY else "❌ Не настроен"}
└ Модель: {settings.OPENAI_MODEL if settings.OPENAI_API_KEY else "N/A"}

<b>Администраторы:</b>
└ Количество: {len(settings.ADMIN_IDS)}

<b>Статистика:</b>
├ Пользователей: {stats.get('active_users', 0)}
├ Сигналов: {stats.get('total_signals', 0)}
└ Трейдов: {stats.get('total_trades', 0)}
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "settings_menu")
async def back_to_settings(callback: CallbackQuery):
    """Вернуться в настройки"""
    await callback.answer()
    
    bot_settings = await db.get_bot_settings()
    
    text = f"""
⚙️ <b>Настройки бота</b>

📛 Название: {bot_settings.get('name', settings.BOT_NAME) if bot_settings else settings.BOT_NAME}
👋 Приветствие: {bot_settings.get('welcome_message', settings.WELCOME_MESSAGE)[:50] if bot_settings else settings.WELCOME_MESSAGE[:50]}...

<i>Выберите параметр для редактирования:</i>
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Изменить название", callback_data="settings_edit_name")],
        [InlineKeyboardButton(text="👋 Изменить приветствие", callback_data="settings_edit_welcome")],
        [InlineKeyboardButton(text="ℹ️ Системная информация", callback_data="settings_info")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.answer()
    from keyboards import get_main_menu_keyboard
    
    await callback.message.answer(
        "🎛 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустой callback (для неактивных кнопок)"""
    await callback.answer()
