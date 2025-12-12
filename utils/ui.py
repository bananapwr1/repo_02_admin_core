"""
UI helpers for chat cleanliness:
- Keep a single "menu" message per chat/user and edit/replace it.
- Best-effort deletion of user commands / intermediate messages.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Any

from aiogram import Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext


async def safe_delete_message(message: Optional[Message]) -> None:
    """Best-effort message deletion (ignore all errors)."""
    if not message:
        return
    try:
        await message.delete()
    except Exception:
        return


async def safe_delete_by_id(bot: Bot, chat_id: int, message_id: int) -> None:
    """Best-effort deletion by ids (ignore all errors)."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        return


async def show_menu(
    *,
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    reply_markup: Any,
    parse_mode: str = "HTML",
    prefer_edit: bool = True,
) -> int:
    """
    Render a single menu message:
    - Try to edit previously stored menu message (if prefer_edit).
    - Otherwise delete previous menu message and send a new one.
    """
    data = await state.get_data()
    last_menu_message_id = data.get("ui_last_menu_message_id")
    last_menu_chat_id = data.get("ui_last_menu_chat_id")

    if prefer_edit and last_menu_message_id and last_menu_chat_id == chat_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(last_menu_message_id),
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return int(last_menu_message_id)
        except Exception:
            # fallback to sending a fresh menu
            pass

    # Replace old menu with a new message
    if last_menu_message_id and last_menu_chat_id == chat_id:
        await safe_delete_by_id(bot, chat_id, int(last_menu_message_id))

    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    await state.update_data(ui_last_menu_message_id=msg.message_id, ui_last_menu_chat_id=chat_id)
    return msg.message_id


async def send_ephemeral(
    *,
    bot: Bot,
    chat_id: int,
    text: str,
    ttl_seconds: int = 10,
    reply_markup: Any = None,
    parse_mode: str = "HTML",
) -> None:
    """Send a message and auto-delete it after ttl_seconds."""
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def _delete_later() -> None:
        try:
            await asyncio.sleep(max(1, int(ttl_seconds)))
            await safe_delete_by_id(bot, chat_id, msg.message_id)
        except Exception:
            return

    asyncio.create_task(_delete_later())

