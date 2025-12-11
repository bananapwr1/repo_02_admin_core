"""
Клавиатуры для админ-панели
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню управления Ядром (Repo 02)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 Управление Стратегиями"),
            ],
            [
                KeyboardButton(text="🧠 Логика Анализа Ядра"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки Бота Ядра"),
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
        [InlineKeyboardButton(text="➕ Создать Новую Стратегию", callback_data="strategy_create_wizard")],
        [InlineKeyboardButton(text="📋 Список/Редактировать Стратегии", callback_data="strategies_list")],
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
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"strategy_edit_{strategy_id}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="strategies_list")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_strategy_edit_menu_keyboard(strategy_id: int) -> InlineKeyboardMarkup:
    """Меню выбора поля для редактирования стратегии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Название", callback_data=f"strategy_edit_field_name_{strategy_id}")],
        [InlineKeyboardButton(text="📈 Symbol(ы)", callback_data=f"strategy_edit_field_symbols_{strategy_id}")],
        [InlineKeyboardButton(text="⏰ Timeframe", callback_data=f"strategy_edit_field_timeframe_{strategy_id}")],
        [InlineKeyboardButton(text="📊 Indicators (JSON)", callback_data=f"strategy_edit_field_indicators_{strategy_id}")],
        [InlineKeyboardButton(text="🛡 Risk level", callback_data=f"strategy_edit_field_risk_{strategy_id}")],
        [InlineKeyboardButton(text="🔐 Private params (JSON)", callback_data=f"strategy_edit_field_private_{strategy_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"strategy_{strategy_id}")]
    ])


def get_core_analysis_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура экрана логики анализа Ядра"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="core_analysis_refresh")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def get_core_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек Ядра"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Ключи/Токены (секреты)", callback_data="core_settings_secrets")],
        [InlineKeyboardButton(text="ℹ️ Системная информация", callback_data="core_settings_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
