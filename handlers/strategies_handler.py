"""
Обработчик управления стратегиями
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from keyboards import get_strategies_menu_keyboard, get_strategy_action_keyboard
from utils import format_strategy_info, paginate_list

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🎯 Стратегии")
async def strategies_menu(message: Message):
    """Главное меню стратегий"""
    await message.answer(
        "🎯 <b>Управление стратегиями</b>\n\nВыберите действие:",
        reply_markup=get_strategies_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "strategies_list")
async def show_strategies_list(callback: CallbackQuery):
    """Показать список всех стратегий"""
    await callback.answer()
    
    strategies = await db.get_all_strategies()
    
    if not strategies:
        await callback.message.edit_text(
            "📋 <b>Список стратегий пуст</b>\n\nСоздайте новую стратегию через AI-чат!",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "🎯 <b>Список стратегий</b>\n\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    
    for strategy in strategies:
        status_emoji = "✅" if strategy.get('is_active') else "⏸"
        name = strategy.get('name', 'Unnamed')
        strategy_id = strategy.get('id')
        
        text += f"{status_emoji} {name}\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {name}",
                callback_data=f"strategy_{strategy_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("strategy_") and not F.data.contains("activate") and not F.data.contains("deactivate") and not F.data.contains("stats"))
async def show_strategy_info(callback: CallbackQuery):
    """Показать информацию о стратегии"""
    await callback.answer()
    
    strategy_id = int(callback.data.split("_")[1])
    strategies = await db.get_all_strategies()
    strategy = next((s for s in strategies if s.get('id') == strategy_id), None)
    
    if not strategy:
        await callback.answer("❌ Стратегия не найдена", show_alert=True)
        return
    
    text = format_strategy_info(strategy)
    keyboard = get_strategy_action_keyboard(strategy_id, strategy.get('is_active', False))
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("strategy_activate_"))
async def activate_strategy(callback: CallbackQuery):
    """Активировать стратегию"""
    strategy_id = int(callback.data.split("_")[2])
    
    success = await db.update_strategy_status(strategy_id, is_active=True)
    
    if success:
        await callback.answer("✅ Стратегия активирована", show_alert=True)
        logger.info(f"Стратегия {strategy_id} активирована админом {callback.from_user.id}")
        # Обновляем информацию
        callback.data = f"strategy_{strategy_id}"
        await show_strategy_info(callback)
    else:
        await callback.answer("❌ Ошибка активации", show_alert=True)


@router.callback_query(F.data.startswith("strategy_deactivate_"))
async def deactivate_strategy(callback: CallbackQuery):
    """Деактивировать стратегию"""
    strategy_id = int(callback.data.split("_")[2])
    
    success = await db.update_strategy_status(strategy_id, is_active=False)
    
    if success:
        await callback.answer("✅ Стратегия деактивирована", show_alert=True)
        callback.data = f"strategy_{strategy_id}"
        await show_strategy_info(callback)
    else:
        await callback.answer("❌ Ошибка деактивации", show_alert=True)


@router.callback_query(F.data == "strategy_active")
async def show_active_strategy(callback: CallbackQuery):
    """Показать активную стратегию"""
    await callback.answer()
    
    strategy = await db.get_active_strategy()
    
    if not strategy:
        await callback.message.edit_text(
            "⚠️ <b>Нет активной стратегии</b>\n\nСоздайте и активируйте стратегию через AI-чат!",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "✅ <b>Текущая активная стратегия</b>\n\n" + format_strategy_info(strategy)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏸ Деактивировать", callback_data=f"strategy_deactivate_{strategy.get('id')}")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"strategy_stats_{strategy.get('id')}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="strategies_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("strategy_stats_"))
async def show_strategy_statistics(callback: CallbackQuery):
    """Показать статистику стратегии"""
    await callback.answer("📊 Загрузка статистики...", show_alert=False)
    
    strategy_id = int(callback.data.split("_")[2])
    
    # Получаем анализ от AI
    from services import ai_service
    analysis = await ai_service.analyze_strategy_performance(strategy_id)
    
    text = f"📊 <b>Анализ производительности стратегии</b>\n\n{analysis}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"strategy_{strategy_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "strategy_create")
async def create_strategy_prompt(callback: CallbackQuery):
    """Подсказка по созданию стратегии"""
    await callback.answer()
    
    text = """
➕ <b>Создание новой стратегии</b>

Для создания стратегии используйте AI-чат:

1. Нажмите кнопку "🧠 AI Чат" в главном меню
2. Опишите желаемую стратегию
3. AI предложит оптимальные параметры
4. После согласования AI сгенерирует готовую стратегию
5. Активируйте её в разделе стратегий

<i>AI имеет доступ к актуальной статистике и может предложить оптимальные параметры!</i>
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Открыть AI Чат", callback_data="ai_chat_start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="strategies_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
