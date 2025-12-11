"""
Клавиатуры для админ-панели
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Пользователи"),
                KeyboardButton(text="📊 Статистика")
            ],
            [
                KeyboardButton(text="🎯 Стратегии"),
                KeyboardButton(text="🧠 AI Чат")
            ],
            [
                KeyboardButton(text="🎫 Токены"),
                KeyboardButton(text="📝 Логи")
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="ℹ️ Помощь")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления пользователями"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="users_search")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_user_action_keyboard(user_id: int, is_blocked: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура действий с конкретным пользователем"""
    block_text = "✅ Разблокировать" if is_blocked else "🚫 Заблокировать"
    block_action = f"unblock_{user_id}" if is_blocked else f"block_{user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=block_text, callback_data=block_action)],
        [InlineKeyboardButton(text="💎 Изменить подписку", callback_data=f"subscription_{user_id}")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"user_stats_{user_id}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="users_list")]
    ])
    return keyboard


def get_subscription_types_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Trial (7 дней)", callback_data=f"subs_trial_{user_id}")],
        [InlineKeyboardButton(text="💎 VIP (30 дней)", callback_data=f"subs_vip_{user_id}")],
        [InlineKeyboardButton(text="📈 Long Only (30 дней)", callback_data=f"subs_long_{user_id}")],
        [InlineKeyboardButton(text="📉 Short Only (30 дней)", callback_data=f"subs_short_{user_id}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"user_{user_id}")]
    ])
    return keyboard


def get_strategies_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления стратегиями"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список стратегий", callback_data="strategies_list")],
        [InlineKeyboardButton(text="✅ Активная стратегия", callback_data="strategy_active")],
        [InlineKeyboardButton(text="➕ Создать новую", callback_data="strategy_create")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_strategy_action_keyboard(strategy_id: int, is_active: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура действий со стратегией"""
    buttons = []
    
    if not is_active:
        buttons.append([InlineKeyboardButton(text="✅ Активировать", callback_data=f"strategy_activate_{strategy_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="⏸ Деактивировать", callback_data=f"strategy_deactivate_{strategy_id}")])
    
    buttons.extend([
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"strategy_stats_{strategy_id}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="strategies_list")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tokens_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления токенами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список токенов", callback_data="tokens_list")],
        [InlineKeyboardButton(text="➕ Создать токен", callback_data="token_create")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_token_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа токена"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Одноразовый", callback_data="token_type_single")],
        [InlineKeyboardButton(text="♾️ Многоразовый (5)", callback_data="token_type_multi_5")],
        [InlineKeyboardButton(text="♾️ Многоразовый (10)", callback_data="token_type_multi_10")],
        [InlineKeyboardButton(text="♾️ Неограниченный", callback_data="token_type_unlimited")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="tokens_menu")]
    ])
    return keyboard


def get_token_subscription_keyboard(max_uses: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора подписки для токена"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Trial", callback_data=f"token_sub_trial_{max_uses}")],
        [InlineKeyboardButton(text="💎 VIP", callback_data=f"token_sub_vip_{max_uses}")],
        [InlineKeyboardButton(text="📈 Long Only", callback_data=f"token_sub_long_{max_uses}")],
        [InlineKeyboardButton(text="📉 Short Only", callback_data=f"token_sub_short_{max_uses}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="tokens_menu")]
    ])
    return keyboard


def get_logs_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню просмотра логов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Системные логи", callback_data="logs_system")],
        [InlineKeyboardButton(text="🧠 Логи решений AI", callback_data="logs_decisions")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="logs_refresh")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_ai_chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура AI-чата"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить стратегию", callback_data="ai_save_strategy")],
        [InlineKeyboardButton(text="📊 Показать статистику", callback_data="ai_show_stats")],
        [InlineKeyboardButton(text="🔄 Новый диалог", callback_data="ai_new_chat")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_confirmation_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{data}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
        ]
    ])
    return keyboard


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard


def get_pagination_keyboard(
    current_page: int, 
    total_pages: int, 
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """Клавиатура пагинации"""
    buttons = []
    
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_page_{current_page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_page_{current_page+1}"))
    
    buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
