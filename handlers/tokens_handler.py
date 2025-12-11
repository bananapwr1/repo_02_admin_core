"""
Обработчик управления токенами приглашения
"""
import logging
import secrets
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from keyboards import get_tokens_menu_keyboard, get_token_type_keyboard, get_token_subscription_keyboard
from utils import format_token_info

logger = logging.getLogger(__name__)
router = Router()


def generate_token(length: int = 16) -> str:
    """Генерация безопасного токена"""
    return secrets.token_urlsafe(length)[:length].replace('_', '-').replace('-', 'X')


@router.message(F.text == "🎫 Токены")
async def tokens_menu(message: Message):
    """Главное меню токенов"""
    await message.answer(
        "🎫 <b>Управление токенами приглашения</b>\n\nВыберите действие:",
        reply_markup=get_tokens_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tokens_list")
async def show_tokens_list(callback: CallbackQuery):
    """Показать список токенов"""
    await callback.answer()
    
    tokens = await db.get_all_tokens()
    
    if not tokens:
        await callback.message.edit_text(
            "📋 <b>Список токенов пуст</b>\n\nСоздайте новый токен!",
            reply_markup=get_tokens_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "🎫 <b>Список токенов приглашения</b>\n\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    
    for token in tokens[:10]:  # Показываем последние 10
        status_emoji = "✅" if token.get('is_active') else "❌"
        token_str = token.get('token', 'N/A')
        uses = f"{token.get('current_uses', 0)}/{token.get('max_uses', '∞')}"
        sub_type = token.get('subscription_type', 'trial')
        
        text += f"{status_emoji} <code>{token_str}</code> - {sub_type} ({uses})\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {token_str[:12]}... ({uses})",
                callback_data=f"token_info_{token_str}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="➕ Создать токен", callback_data="token_create")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("token_info_"))
async def show_token_info(callback: CallbackQuery):
    """Показать информацию о токене"""
    await callback.answer()
    
    token_str = callback.data.replace("token_info_", "")
    tokens = await db.get_all_tokens()
    token = next((t for t in tokens if t.get('token') == token_str), None)
    
    if not token:
        await callback.answer("❌ Токен не найден", show_alert=True)
        return
    
    text = format_token_info(token)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    
    if token.get('is_active'):
        buttons.append([InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"token_deactivate_{token_str}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 К списку", callback_data="tokens_list")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "token_create")
async def create_token_step1(callback: CallbackQuery):
    """Шаг 1: Выбор типа токена"""
    await callback.answer()
    
    text = """
➕ <b>Создание токена приглашения</b>

Выберите тип токена:

1️⃣ <b>Одноразовый</b> - может быть использован только один раз
♾️ <b>Многоразовый</b> - может быть использован несколько раз
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_token_type_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("token_type_"))
async def create_token_step2(callback: CallbackQuery):
    """Шаг 2: Выбор типа подписки"""
    await callback.answer()
    
    token_type = callback.data.replace("token_type_", "")
    
    # Определяем количество использований
    max_uses_map = {
        'single': 1,
        'multi_5': 5,
        'multi_10': 10,
        'unlimited': 999999
    }
    
    max_uses = max_uses_map.get(token_type, 1)
    
    text = f"""
➕ <b>Создание токена</b>

Тип: {"Одноразовый" if max_uses == 1 else f"Многоразовый ({max_uses})"}

Выберите тип подписки для токена:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_token_subscription_keyboard(max_uses),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("token_sub_"))
async def create_token_final(callback: CallbackQuery):
    """Финальный шаг: Создание токена"""
    await callback.answer("⏳ Создание токена...")
    
    parts = callback.data.split("_")
    sub_type = parts[2]
    max_uses = int(parts[3])
    
    # Генерируем токен
    token = generate_token()
    
    # Сохраняем в БД
    success = await db.create_invite_token(
        token=token,
        max_uses=max_uses,
        subscription_type=sub_type,
        created_by=callback.from_user.id
    )
    
    if success:
        text = f"""
✅ <b>Токен успешно создан!</b>

🎫 Токен: <code>{token}</code>

💎 Тип подписки: {sub_type}
🔢 Максимум использований: {max_uses if max_uses < 999999 else '∞'}
👤 Создатель: {callback.from_user.username or callback.from_user.id}

<i>Отправьте этот токен пользователю для регистрации</i>
"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К списку токенов", callback_data="tokens_list")],
            [InlineKeyboardButton(text="➕ Создать еще", callback_data="token_create")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
        logger.info(f"Админ {callback.from_user.id} создал токен {token} ({sub_type}, {max_uses} uses)")
    else:
        await callback.answer("❌ Ошибка создания токена", show_alert=True)


@router.callback_query(F.data.startswith("token_deactivate_"))
async def deactivate_token(callback: CallbackQuery):
    """Деактивировать токен"""
    token_str = callback.data.replace("token_deactivate_", "")
    
    success = await db.deactivate_token(token_str)
    
    if success:
        await callback.answer("✅ Токен деактивирован", show_alert=True)
        callback.data = f"token_info_{token_str}"
        await show_token_info(callback)
    else:
        await callback.answer("❌ Ошибка деактивации", show_alert=True)


@router.callback_query(F.data == "tokens_menu")
async def back_to_tokens_menu(callback: CallbackQuery):
    """Вернуться в меню токенов"""
    await callback.answer()
    await callback.message.edit_text(
        "🎫 <b>Управление токенами приглашения</b>\n\nВыберите действие:",
        reply_markup=get_tokens_menu_keyboard(),
        parse_mode="HTML"
    )
