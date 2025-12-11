"""
Обработчик просмотра логов и мониторинга
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from keyboards import get_logs_menu_keyboard
from utils import format_log_entry, format_decision_log, format_statistics

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "📝 Логи")
async def logs_menu(message: Message):
    """Главное меню логов"""
    await message.answer(
        "📝 <b>Логи и мониторинг</b>\n\nВыберите тип логов:",
        reply_markup=get_logs_menu_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать общую статистику"""
    stats = await db.get_trading_statistics()
    active_strategy = await db.get_active_strategy()
    
    if active_strategy:
        stats['active_strategy_name'] = active_strategy.get('name', 'N/A')
    else:
        stats['active_strategy_name'] = '❌ Нет активной стратегии'
    
    text = format_statistics(stats)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_refresh")],
        [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="stats_detailed")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "logs_system")
async def show_system_logs(callback: CallbackQuery):
    """Показать системные логи"""
    await callback.answer("📡 Загрузка логов...")
    
    logs = await db.get_system_logs(limit=20)
    
    if not logs:
        text = "📋 <b>Системные логи пусты</b>\n\nНет записей в журнале."
    else:
        text = "🔧 <b>Системные логи</b>\n\n"
        
        for log in logs[:10]:  # Показываем последние 10
            text += format_log_entry(log)
            text += "\n"
        
        text += f"\n<i>Показано {len(logs[:10])} из {len(logs)} записей</i>"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="logs_system")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="logs_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "logs_decisions")
async def show_decision_logs(callback: CallbackQuery):
    """Показать логи решений AI"""
    await callback.answer("🧠 Загрузка логов решений...")
    
    logs = await db.get_decision_logs(limit=10)
    
    if not logs:
        text = "📋 <b>Логи решений AI пусты</b>\n\nНет записей о принятых решениях."
    else:
        text = "🧠 <b>Логи решений AI</b>\n\n"
        text += "<i>Последние решения торгового ядра:</i>\n\n"
        
        for log in logs[:5]:  # Показываем последние 5
            text += format_decision_log(log)
            text += "\n" + "─" * 30 + "\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="logs_decisions")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="logs_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "logs_refresh")
async def refresh_logs(callback: CallbackQuery):
    """Обновить логи"""
    await callback.answer("🔄 Обновление...", show_alert=False)
    
    # Перенаправляем на текущий тип логов
    await show_system_logs(callback)


@router.callback_query(F.data == "logs_menu")
async def back_to_logs_menu(callback: CallbackQuery):
    """Вернуться в меню логов"""
    await callback.answer()
    await callback.message.edit_text(
        "📝 <b>Логи и мониторинг</b>\n\nВыберите тип логов:",
        reply_markup=get_logs_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "stats_refresh")
async def refresh_statistics(callback: CallbackQuery):
    """Обновить статистику"""
    await callback.answer("🔄 Обновление статистики...")
    
    stats = await db.get_trading_statistics()
    active_strategy = await db.get_active_strategy()
    
    if active_strategy:
        stats['active_strategy_name'] = active_strategy.get('name', 'N/A')
    else:
        stats['active_strategy_name'] = '❌ Нет активной стратегии'
    
    text = format_statistics(stats)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_refresh")],
        [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="stats_detailed")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "stats_detailed")
async def show_detailed_statistics(callback: CallbackQuery):
    """Показать подробную статистику"""
    await callback.answer("📊 Загрузка подробной статистики...")
    
    stats = await db.get_trading_statistics()
    strategies = await db.get_all_strategies()
    users = await db.get_all_users()
    
    active_users = len([u for u in users if not u.get('is_blocked')])
    blocked_users = len([u for u in users if u.get('is_blocked')])
    
    text = f"""
📊 <b>Подробная статистика системы</b>

👥 <b>Пользователи:</b>
├ Всего: {len(users)}
├ Активных: {active_users}
└ Заблокированных: {blocked_users}

🎯 <b>Стратегии:</b>
├ Всего: {len(strategies)}
└ Активных: {len([s for s in strategies if s.get('is_active')])}

📡 <b>Сигналы:</b>
└ Всего отправлено: {stats.get('total_signals', 0)}

💹 <b>Трейды:</b>
└ Всего выполнено: {stats.get('total_trades', 0)}

⏰ <b>Последнее обновление:</b>
└ {format_statistics(stats).split('Последнее обновление:')[1].strip() if 'Последнее обновление:' in format_statistics(stats) else 'N/A'}
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats_detailed")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="stats_refresh")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
