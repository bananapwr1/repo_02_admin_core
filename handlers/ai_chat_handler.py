"""
Обработчик AI-чата для разработки стратегий
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services import ai_service
from keyboards import get_ai_chat_keyboard
from database import db

logger = logging.getLogger(__name__)
router = Router()


class AIStrategyStates(StatesGroup):
    """Состояния для AI-чата"""
    chatting = State()
    confirming_save = State()


@router.message(F.text == "🧠 AI Чат")
async def ai_chat_start_button(message: Message, state: FSMContext):
    """Запуск AI-чата через кнопку"""
    await start_ai_chat(message, state)


@router.callback_query(F.data == "ai_chat_start")
async def ai_chat_start_callback(callback: CallbackQuery, state: FSMContext):
    """Запуск AI-чата через callback"""
    await callback.answer()
    await start_ai_chat(callback.message, state)


async def start_ai_chat(message: Message, state: FSMContext):
    """Инициализация AI-чата"""
    user_id = message.from_user.id
    
    # Сбрасываем предыдущий диалог
    ai_service.reset_conversation(user_id)
    
    text = """
🧠 <b>AI-ассистент разработки стратегий</b>

Добро пожаловать в диалоговый интерфейс создания торговых стратегий!

<b>Что я могу:</b>
• Анализировать текущую торговую статистику
• Предлагать оптимальные параметры стратегий
• Обсуждать торговую логику и правила
• Генерировать готовые стратегии в JSON-формате

<b>Как работать:</b>
1. Опишите желаемую стратегию или задайте вопрос
2. Я проанализирую данные и предложу решение
3. После обсуждения я сгенерирую готовую стратегию
4. Вы сможете сохранить её в систему

<i>Напишите ваш запрос или вопрос о стратегии...</i>

<b>Примеры запросов:</b>
• "Предложи стратегию для BTC на основе RSI"
• "Какие активы сейчас наиболее волатильны?"
• "Создай стратегию для скальпинга на EUR/USD"
• "Оптимизируй текущую стратегию"
"""
    
    await message.answer(text, reply_markup=get_ai_chat_keyboard(), parse_mode="HTML")
    await state.set_state(AIStrategyStates.chatting)


@router.message(AIStrategyStates.chatting)
async def process_ai_message(message: Message, state: FSMContext):
    """Обработка сообщений в AI-чате"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Показываем, что бот думает
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Обрабатываем сообщение через AI
    response, strategy_data = await ai_service.process_message_with_context(user_id, user_message)
    
    # Если AI предложил сохранить стратегию
    if strategy_data:
        # Сохраняем данные стратегии в состоянии
        await state.update_data(strategy_data=strategy_data)
        
        text = f"""
💾 <b>AI предложил сохранить стратегию</b>

{response}

<b>Сохранить эту стратегию?</b>
"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="ai_confirm_save"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="ai_cancel_save")
            ],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AIStrategyStates.confirming_save)
    else:
        # Обычный ответ
        # Разбиваем длинные ответы
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="HTML")
        else:
            await message.answer(response, reply_markup=get_ai_chat_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "ai_confirm_save")
async def confirm_save_strategy(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сохранения стратегии"""
    await callback.answer("💾 Сохранение стратегии...")
    
    data = await state.get_data()
    strategy_data = data.get('strategy_data')
    
    if not strategy_data:
        await callback.message.edit_text("❌ Данные стратегии потеряны. Начните заново.")
        await state.clear()
        return
    
    # Сохраняем стратегию
    success = await ai_service.save_strategy(strategy_data)
    
    if success:
        text = f"""
✅ <b>Стратегия успешно сохранена!</b>

📝 Название: {strategy_data.get('name', 'N/A')}
📊 Активы: {', '.join(strategy_data.get('assets_to_monitor', []))}

Стратегия добавлена в систему. Вы можете активировать её в разделе "🎯 Стратегии".

<i>Хотите продолжить диалог или вернуться в меню?</i>
"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 К стратегиям", callback_data="strategies_list")],
            [InlineKeyboardButton(text="🔄 Новый диалог", callback_data="ai_new_chat")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.clear()
        
        logger.info(f"Админ {callback.from_user.id} сохранил стратегию через AI: {strategy_data.get('name')}")
    else:
        await callback.answer("❌ Ошибка сохранения стратегии", show_alert=True)


@router.callback_query(F.data == "ai_cancel_save")
async def cancel_save_strategy(callback: CallbackQuery, state: FSMContext):
    """Отмена сохранения стратегии"""
    await callback.answer("Сохранение отменено")
    
    await callback.message.edit_text(
        "❌ Сохранение отменено. Продолжайте диалог или начните заново.",
        reply_markup=get_ai_chat_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AIStrategyStates.chatting)


@router.callback_query(F.data == "ai_new_chat")
async def new_ai_chat(callback: CallbackQuery, state: FSMContext):
    """Начать новый диалог"""
    await callback.answer("🔄 Новый диалог")
    await start_ai_chat(callback.message, state)


@router.callback_query(F.data == "ai_save_strategy")
async def manual_save_request(callback: CallbackQuery, state: FSMContext):
    """Запрос на сохранение стратегии"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    # Отправляем специальный запрос к AI
    response, strategy_data = await ai_service.process_message_with_context(
        user_id,
        "Пожалуйста, сгенерируй финальную стратегию на основе нашего диалога в формате SAVE_STRATEGY"
    )
    
    if strategy_data:
        await state.update_data(strategy_data=strategy_data)
        
        text = f"""
💾 <b>Готово к сохранению</b>

{response}

<b>Сохранить эту стратегию?</b>
"""
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="ai_confirm_save"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="ai_cancel_save")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(AIStrategyStates.confirming_save)
    else:
        await callback.message.answer(
            response,
            reply_markup=get_ai_chat_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "ai_show_stats")
async def show_ai_stats(callback: CallbackQuery):
    """Показать статистику в AI-чате"""
    await callback.answer("📊 Загрузка статистики...")
    
    context = await ai_service.get_trading_context()
    
    await callback.message.answer(
        f"📊 <b>Текущая статистика системы</b>\n\n{context}",
        reply_markup=get_ai_chat_keyboard(),
        parse_mode="HTML"
    )
