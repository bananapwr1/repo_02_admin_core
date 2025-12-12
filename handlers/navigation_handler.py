"""
Глобальная навигация (Домой/Назад/Noop) и чистый UI.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_inline_keyboard
from utils import safe_delete_message, show_menu

logger = logging.getLogger(__name__)
router = Router()


MAIN_MENU_TEXT = (
    "🎛 <b>Главное меню</b>\n\n"
    "Выберите раздел:\n\n"
    "Команды:\n"
    "• /menu — главное меню\n"
    "• /strategies — стратегии\n"
    "• /analysis — логику ядра\n"
    "• /settings — настройки\n"
    "• /users — пользователи\n"
    "• /tokens — токены\n"
)


async def render_main_menu(message: Message, state: FSMContext, *, prefer_edit: bool = True) -> None:
    # Пытаемся держать один "экран меню" (inline) + оставляем reply-клавиатуру как fallback
    await show_menu(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=MAIN_MENU_TEXT,
        reply_markup=get_main_menu_inline_keyboard(),
        parse_mode="HTML",
        prefer_edit=prefer_edit,
    )


@router.message(Command("menu", "home"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    # Удаляем команду пользователя, чтобы чат не засорять
    await safe_delete_message(message)
    await render_main_menu(message, state, prefer_edit=False)


@router.callback_query(F.data.in_({"nav:home", "main_menu"}))
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    # В callback у нас есть сообщение — редактируем его, не плодим новые
    if callback.message:
        await callback.message.edit_text(
            MAIN_MENU_TEXT,
            reply_markup=get_main_menu_inline_keyboard(),
            parse_mode="HTML",
        )
        await state.update_data(
            ui_last_menu_message_id=callback.message.message_id,
            ui_last_menu_chat_id=callback.message.chat.id,
        )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(F.text == "🏠 Главное меню")
async def menu_text_fallback(message: Message, state: FSMContext) -> None:
    # Если у пользователя осталась reply-клавиатура
    await render_main_menu(message, state, prefer_edit=False)


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def fallback_unknown_text(message: Message, state: FSMContext) -> None:
    """
    Если админ написал что-то вне сценариев (и это не команда),
    возвращаем в меню и не засоряем чат.
    """
    await safe_delete_message(message)
    await render_main_menu(message, state, prefer_edit=False)

