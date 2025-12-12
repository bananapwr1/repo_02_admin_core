"""
Обработчик управления пользователями
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from keyboards import (
    get_users_menu_keyboard,
    get_user_action_keyboard,
    get_subscription_types_keyboard,
    get_pagination_keyboard
)
from utils import format_user_info, paginate_list, validate_telegram_id
from utils import safe_delete_message, show_menu

logger = logging.getLogger(__name__)
router = Router()


class UserManagementStates(StatesGroup):
    """Состояния для управления пользователями"""
    waiting_for_user_id = State()


@router.message(F.text.contains("Пользователи"))
async def users_menu(message: Message, state: FSMContext):
    """Главное меню управления пользователями"""
    await show_menu(
        bot=message.bot,
        chat_id=message.chat.id,
        state=state,
        text="👥 <b>Управление пользователями</b>\n\nВыберите действие:",
        reply_markup=get_users_menu_keyboard(),
        parse_mode="HTML",
        prefer_edit=True,
    )


@router.message(Command("users"))
async def cmd_users(message: Message, state: FSMContext):
    """Команда: /users"""
    await safe_delete_message(message)
    await users_menu(message, state)  # type: ignore[arg-type]


@router.callback_query(F.data == "nav:users")
async def nav_users(callback: CallbackQuery, state: FSMContext):
    """Навигация из главного меню (inline)"""
    await callback.answer()
    if not callback.message:
        return
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\nВыберите действие:",
        reply_markup=get_users_menu_keyboard(),
        parse_mode="HTML",
    )
    await state.update_data(ui_last_menu_message_id=callback.message.message_id, ui_last_menu_chat_id=callback.message.chat.id)


@router.callback_query(F.data == "users_list")
async def show_users_list(callback: CallbackQuery):
    """Показать список пользователей"""
    await callback.answer()
    
    users = await db.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "📋 <b>Список пользователей пуст</b>",
            reply_markup=get_users_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Пагинация
    page = 1
    users_page, total_pages = paginate_list(users, page, per_page=5)
    
    text = f"👥 <b>Список пользователей</b> (стр. {page}/{total_pages})\n\n"
    
    for user in users_page:
        status_emoji = "🚫" if user.get('is_blocked') else "✅"
        sub_type = user.get('subscription_type', 'none')
        text += f"{status_emoji} <code>{user.get('telegram_id')}</code> - {user.get('username', 'N/A')} ({sub_type})\n"
    
    text += f"\n<i>Всего пользователей: {len(users)}</i>"
    
    # Создаем инлайн-кнопки для каждого пользователя
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    for user in users_page:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {user.get('username', user.get('telegram_id'))}",
                callback_data=f"user_{user.get('telegram_id')}"
            )
        ])
    
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page+1}"))
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("user_"))
async def show_user_info(callback: CallbackQuery):
    """Показать информацию о пользователе"""
    await callback.answer()
    
    user_id = int(callback.data.split("_")[1])
    user = await db.get_user_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    text = format_user_info(user)
    keyboard = get_user_action_keyboard(user_id, user.get('is_blocked', False))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("block_"))
async def block_user(callback: CallbackQuery):
    """Заблокировать пользователя"""
    user_id = int(callback.data.split("_")[1])
    
    success = await db.update_user_status(user_id, is_blocked=True)
    
    if success:
        await callback.answer("✅ Пользователь заблокирован", show_alert=True)
        # Обновляем информацию
        await show_user_info(callback)
    else:
        await callback.answer("❌ Ошибка блокировки", show_alert=True)


@router.callback_query(F.data.startswith("unblock_"))
async def unblock_user(callback: CallbackQuery):
    """Разблокировать пользователя"""
    user_id = int(callback.data.split("_")[1])
    
    success = await db.update_user_status(user_id, is_blocked=False)
    
    if success:
        await callback.answer("✅ Пользователь разблокирован", show_alert=True)
        await show_user_info(callback)
    else:
        await callback.answer("❌ Ошибка разблокировки", show_alert=True)


@router.callback_query(F.data.startswith("subscription_"))
async def change_subscription(callback: CallbackQuery):
    """Изменить подписку пользователя"""
    await callback.answer()
    
    user_id = int(callback.data.split("_")[1])
    
    text = f"💎 <b>Выбор подписки для пользователя {user_id}</b>\n\nВыберите тип подписки:"
    keyboard = get_subscription_types_keyboard(user_id)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("subs_"))
async def apply_subscription(callback: CallbackQuery):
    """Применить подписку"""
    parts = callback.data.split("_")
    sub_type = parts[1]
    user_id = int(parts[2])
    
    # Определяем срок подписки
    days_map = {
        'trial': 7,
        'vip': 30,
        'long': 30,
        'short': 30
    }
    
    days = days_map.get(sub_type, 30)
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
    
    success = await db.update_user_subscription(user_id, sub_type, expires_at)
    
    if success:
        await callback.answer(f"✅ Подписка {sub_type} выдана на {days} дней", show_alert=True)
        # Возвращаемся к информации о пользователе
        callback.data = f"user_{user_id}"
        await show_user_info(callback)
    else:
        await callback.answer("❌ Ошибка обновления подписки", show_alert=True)


@router.callback_query(F.data == "users_search")
async def search_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на поиск пользователя"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\nОтправьте Telegram ID пользователя:",
        parse_mode="HTML"
    )
    
    await state.set_state(UserManagementStates.waiting_for_user_id)


@router.message(UserManagementStates.waiting_for_user_id)
async def search_user_by_id(message: Message, state: FSMContext):
    """Поиск пользователя по ID"""
    user_id = validate_telegram_id(message.text)
    await safe_delete_message(message)
    
    if not user_id:
        await message.answer("❌ Некорректный Telegram ID. Попробуйте снова:")
        return
    
    user = await db.get_user_by_id(user_id)
    
    if not user:
        await message.answer(
            f"❌ Пользователь с ID {user_id} не найден.\n\nПопробуйте другой ID:",
        )
        return
    
    await state.clear()
    
    text = format_user_info(user)
    keyboard = get_user_action_keyboard(user_id, user.get('is_blocked', False))
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("user_stats_"))
async def show_user_statistics(callback: CallbackQuery):
    """Показать статистику пользователя"""
    await callback.answer()
    
    user_id = int(callback.data.split("_")[2])
    
    # Здесь можно добавить получение детальной статистики из БД
    text = f"""
📊 <b>Статистика пользователя {user_id}</b>

🎯 Всего сигналов получено: N/A
💹 Активных позиций: N/A
💰 P&L: N/A

<i>Функция в разработке</i>
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"user_{user_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
