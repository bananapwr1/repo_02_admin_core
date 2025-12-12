"""
Обработчик настроек бота
"""
import logging
import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import settings
from keyboards import get_core_settings_keyboard
from services.core_settings_service import get_core_settings_service
from utils import safe_delete_message, show_menu

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    """Состояния для настроек"""
    editing_secret_value = State()


SUPPORTED_SECRETS: dict[str, dict[str, str]] = {
    "exchange_credentials": {"title": "Exchange credentials", "hint": "Вставьте JSON или строку (например api_key/secret)."},
}


def _mask(value: str | None, keep: int = 4) -> str:
    if not value:
        return "—"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}***{value[-keep:]}"


@router.message(F.text.contains("Настройки Бота Ядра"))
async def settings_menu(message: Message, state: FSMContext):
    """Меню настроек Ядра"""
    text = (
        "⚙️ <b>Настройки Бота Ядра</b>\n\n"
        "Раздел для управления внутренними настройками и секретами (ключи/токены).\n"
    )
    await show_menu(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text=text,
        reply_markup=get_core_settings_keyboard(),
        parse_mode="HTML",
        prefer_edit=True,
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Команда: /settings"""
    await safe_delete_message(message)
    await settings_menu(message, state)  # type: ignore[arg-type]


@router.callback_query(F.data == "nav:settings")
async def nav_settings(callback: CallbackQuery, state: FSMContext):
    """Навигация из главного меню (inline)"""
    await callback.answer()
    if not callback.message:
        return
    text = (
        "⚙️ <b>Настройки Бота Ядра</b>\n\n"
        "Раздел для управления внутренними настройками и секретами (ключи/токены).\n"
    )
    await callback.message.edit_text(text, reply_markup=get_core_settings_keyboard(), parse_mode="HTML")
    await state.update_data(ui_last_menu_message_id=callback.message.message_id, ui_last_menu_chat_id=callback.message.chat.id)


@router.callback_query(F.data == "core_settings_info")
async def show_system_info(callback: CallbackQuery):
    """Показать системную информацию"""
    await callback.answer()
    
    import sys
    import aiogram

    text = f"""
ℹ️ <b>Системная информация</b>

<b>Бот:</b>
├ Название: {settings.BOT_NAME}
├ Версия aiogram: {aiogram.__version__}
└ Python: {sys.version.split()[0]}

<b>База данных:</b>
├ Supabase: ✅ Подключено
└ BASE_URL: {settings.SUPABASE_URL}

<b>Шифрование:</b>
└ SUPABASE_ENCRYPTION_KEY: {"✅ Настроен" if settings.ENCRYPTION_KEY else "❌ Не настроен"}

<b>Администратор:</b>
└ ADMIN_USER_ID: {settings.ADMIN_USER_ID or "N/A"}
"""
    await callback.message.edit_text(text, reply_markup=get_core_settings_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "core_settings_secrets")
async def core_secrets_menu(callback: CallbackQuery):
    """Просмотр/изменение секретов Ядра (шифруются)"""
    await callback.answer()
    service = get_core_settings_service()
    enc_ok = service.is_encryption_available()

    lines: list[str] = [
        "🔑 <b>Ключи/Токены (секреты)</b>",
        "",
        f"🔐 Шифрование: {'✅ доступно' if enc_ok else '❌ недоступно (нужен SUPABASE_ENCRYPTION_KEY)'}",
        "",
        "<b>Env (только просмотр):</b>",
        f"• SUPABASE_SERVICE_KEY (или SUPABASE_KEY): {_mask(settings.SUPABASE_KEY)}",
        "",
        "<b>Supabase (core_settings):</b>",
    ]

    for key, meta in SUPPORTED_SECRETS.items():
        current = await service.get_secret(key) if enc_ok else None
        status = "✅ задан" if current else "—"
        lines.append(f"• {meta['title']}: {status} ({_mask(current)})")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for key, meta in SUPPORTED_SECRETS.items():
        rows.append([InlineKeyboardButton(text=f"✏️ Установить: {meta['title']}", callback_data=f"core_settings_set_{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("core_settings_set_"))
async def core_secret_set_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    key = callback.data.replace("core_settings_set_", "")
    meta = SUPPORTED_SECRETS.get(key)
    if not meta:
        await callback.answer("❌ Неизвестный ключ", show_alert=True)
        return

    service = get_core_settings_service()
    if not service.is_encryption_available():
        await callback.answer("❌ SUPABASE_ENCRYPTION_KEY не настроен", show_alert=True)
        return

    await state.set_state(SettingsStates.editing_secret_value)
    await state.update_data(secret_key=key)

    await callback.message.edit_text(
        f"✏️ <b>Установка секрета:</b> {meta['title']}\n\n"
        f"{meta['hint']}\n\n"
        "<i>Отправьте значение одним сообщением. Для отмены: /menu</i>",
        parse_mode="HTML",
    )


@router.message(SettingsStates.editing_secret_value)
async def core_secret_set_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("secret_key")
    meta = SUPPORTED_SECRETS.get(key or "")
    if not key or not meta:
        await state.clear()
        await message.answer("❌ Состояние потеряно. Откройте /menu и попробуйте ещё раз.")
        return

    value = (message.text or "").strip()
    if not value:
        await message.answer("❌ Пустое значение. Отправьте ещё раз:")
        return

    if key == "exchange_credentials" and value.startswith("{"):
        try:
            json.loads(value)
        except Exception:
            await message.answer("❌ Невалидный JSON. Исправьте и отправьте ещё раз:")
            return

    service = get_core_settings_service()
    ok = await service.set_secret(key, value)
    await state.clear()
    await safe_delete_message(message)

    if ok:
        await show_menu(
            bot=message.bot,
            chat_id=message.chat.id,
            state=state,
            text=(
                f"✅ <b>Секрет сохранён:</b> {meta['title']}\n\n"
                "Сохранено в Supabase в зашифрованном виде."
            ),
            reply_markup=get_core_settings_keyboard(),
            parse_mode="HTML",
            prefer_edit=True,
        )
    else:
        await show_menu(
            bot=message.bot,
            chat_id=message.chat.id,
            state=state,
            text="❌ Не удалось сохранить секрет. Проверьте SUPABASE_ENCRYPTION_KEY и таблицу core_settings в Supabase.",
            reply_markup=get_core_settings_keyboard(),
            parse_mode="HTML",
            prefer_edit=True,
        )


 # home/noop обработчики вынесены в handlers/navigation_handler.py
