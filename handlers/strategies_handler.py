"""
Обработчик управления стратегиями
"""
import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards import (
    get_strategies_menu_keyboard,
    get_strategy_action_keyboard,
    get_strategy_edit_menu_keyboard,
)
from services.strategy_manager_service import get_strategy_manager
from utils import (
    format_strategy_info,
    validate_strategy_name,
    validate_timeframe,
    sanitize_input,
)

logger = logging.getLogger(__name__)
router = Router()


class StrategyWizardStates(StatesGroup):
    waiting_name = State()
    waiting_symbols = State()
    waiting_timeframe = State()
    waiting_indicators = State()
    waiting_risk_level = State()
    waiting_private_params = State()
    confirming = State()


class StrategyEditStates(StatesGroup):
    waiting_new_value = State()


@router.message(F.text == "🎯 Управление Стратегиями")
async def strategies_menu(message: Message):
    """Меню управления стратегиями"""
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
            "📋 <b>Список стратегий пуст</b>\n\nСоздайте новую стратегию через мастер создания.",
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


@router.callback_query(F.data.startswith("strategy_"))
async def show_strategy_info(callback: CallbackQuery):
    """Показать информацию о стратегии"""
    await callback.answer()

    parts = callback.data.split("_")
    if len(parts) != 2:
        # Это не "strategy_<id>" (а, например, strategy_activate_*)
        return

    strategy_id = int(parts[1])
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

    manager = get_strategy_manager()
    success = await manager.activate_strategy(strategy_id)
    
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

    manager = get_strategy_manager()
    success = await manager.deactivate_strategy(strategy_id)
    
    if success:
        await callback.answer("✅ Стратегия деактивирована", show_alert=True)
        callback.data = f"strategy_{strategy_id}"
        await show_strategy_info(callback)
    else:
        await callback.answer("❌ Ошибка деактивации", show_alert=True)


@router.callback_query(F.data.startswith("strategy_edit_"))
async def strategy_edit_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    strategy_id = int(callback.data.split("_")[2])
    await state.clear()
    await callback.message.edit_text(
        f"✏️ <b>Редактирование стратегии</b> (ID: <code>{strategy_id}</code>)\n\nВыберите поле:",
        reply_markup=get_strategy_edit_menu_keyboard(strategy_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("strategy_edit_field_"))
async def strategy_edit_field_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # format: strategy_edit_field_<field>_<id>
    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return

    field = parts[3]
    strategy_id = int(parts[4])

    field_titles = {
        "name": "Название",
        "symbols": "Symbol(ы) (через запятую)",
        "timeframe": "Timeframe (например 1m,5m,15m,1h,4h,1d)",
        "indicators": "Indicators (JSON)",
        "risk": "Risk level (low/medium/high)",
        "private": "Private params (JSON или строка)",
    }
    title = field_titles.get(field, field)

    await state.set_state(StrategyEditStates.waiting_new_value)
    await state.update_data(strategy_edit_strategy_id=strategy_id, strategy_edit_field=field)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование:</b> {title}\n\n"
        "Отправьте новое значение одним сообщением.\n"
        "<i>Для очистки приватных параметров отправьте: clear</i>\n\n"
        "<i>Отмена: /menu</i>",
        parse_mode="HTML",
    )


@router.message(StrategyEditStates.waiting_new_value)
async def strategy_edit_field_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    strategy_id = data.get("strategy_edit_strategy_id")
    field = data.get("strategy_edit_field")

    if not strategy_id or not field:
        await state.clear()
        await message.answer("❌ Состояние потеряно. Откройте /menu и попробуйте ещё раз.")
        return

    raw = sanitize_input(message.text or "", max_length=5000)
    if not raw:
        await message.answer("❌ Пустое значение. Отправьте ещё раз:")
        return

    manager = get_strategy_manager()
    updates: dict = {}

    if field == "name":
        if not validate_strategy_name(raw):
            await message.answer("❌ Некорректное название. Минимум 3, максимум 100 символов. Отправьте ещё раз:")
            return
        updates["name"] = raw

    elif field == "symbols":
        symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
        if not symbols:
            await message.answer("❌ Не удалось распознать symbols. Пример: BTCUSDT, ETHUSDT")
            return
        updates["assets_to_monitor"] = symbols

    elif field == "timeframe":
        tf = raw.strip()
        if not validate_timeframe(tf):
            await message.answer("❌ Некорректный timeframe. Пример: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w")
            return
        updates["timeframe"] = tf

    elif field == "indicators":
        if raw.lower() == "skip":
            updates["indicators"] = {}
        else:
            try:
                updates["indicators"] = json.loads(raw)
            except Exception:
                await message.answer("❌ Некорректный JSON. Отправьте корректный JSON или 'skip':")
                return

    elif field == "risk":
        risk = raw.lower()
        if risk not in {"low", "medium", "high"}:
            await message.answer("❌ Некорректный risk_level. Допустимо: low, medium, high")
            return
        updates["risk_management"] = {"risk_level": risk}

    elif field == "private":
        if raw.lower() == "clear":
            updates["private_params_encrypted"] = None
        elif raw.lower() == "skip":
            updates["private_params_encrypted"] = None
        else:
            if raw.startswith("{"):
                try:
                    updates["private_params"] = json.loads(raw)
                except Exception:
                    await message.answer("❌ Некорректный JSON. Отправьте JSON или 'clear':")
                    return
            else:
                updates["private_params"] = {"raw": raw}

    else:
        await message.answer("❌ Неизвестное поле редактирования.")
        await state.clear()
        return

    ok = await manager.update_strategy(int(strategy_id), updates)
    await state.clear()

    if ok:
        await message.answer(
            "✅ <b>Стратегия обновлена</b>",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "❌ Ошибка обновления стратегии.",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "strategy_create_wizard")
async def strategy_create_wizard_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(StrategyWizardStates.waiting_name)
    await callback.message.edit_text(
        "➕ <b>Создание новой стратегии</b>\n\n"
        "Шаг 1/6: Введите <b>название</b> стратегии (3–100 символов).\n\n"
        "<i>Отмена: /menu</i>",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_name)
async def strategy_create_wizard_name(message: Message, state: FSMContext):
    name = sanitize_input(message.text or "", max_length=200)
    if not validate_strategy_name(name):
        await message.answer("❌ Некорректное название. Минимум 3, максимум 100 символов. Попробуйте ещё раз:")
        return

    await state.update_data(name=name)
    await state.set_state(StrategyWizardStates.waiting_symbols)
    await message.answer(
        "Шаг 2/6: Введите <b>symbol(ы)</b> через запятую (например: BTCUSDT, ETHUSDT):",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_symbols)
async def strategy_create_wizard_symbols(message: Message, state: FSMContext):
    raw = sanitize_input(message.text or "", max_length=500)
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not symbols:
        await message.answer("❌ Не удалось распознать symbols. Пример: BTCUSDT, ETHUSDT")
        return

    await state.update_data(symbols=symbols)
    await state.set_state(StrategyWizardStates.waiting_timeframe)
    await message.answer(
        "Шаг 3/6: Введите <b>timeframe</b> (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w):",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_timeframe)
async def strategy_create_wizard_timeframe(message: Message, state: FSMContext):
    tf = sanitize_input(message.text or "", max_length=10).strip()
    if not validate_timeframe(tf):
        await message.answer("❌ Некорректный timeframe. Пример: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w")
        return

    await state.update_data(timeframe=tf)
    await state.set_state(StrategyWizardStates.waiting_indicators)
    await message.answer(
        "Шаг 4/6: Введите <b>indicators</b> в JSON (или отправьте <code>skip</code>).\n\n"
        "Пример:\n"
        "<code>{\"rsi\": {\"period\": 14}, \"ema\": {\"fast\": 12, \"slow\": 26}}</code>",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_indicators)
async def strategy_create_wizard_indicators(message: Message, state: FSMContext):
    raw = sanitize_input(message.text or "", max_length=5000)
    if raw.lower() == "skip":
        indicators = {}
    else:
        try:
            indicators = json.loads(raw)
        except Exception:
            await message.answer("❌ Некорректный JSON. Отправьте корректный JSON или 'skip':")
            return

    await state.update_data(indicators=indicators)
    await state.set_state(StrategyWizardStates.waiting_risk_level)
    await message.answer(
        "Шаг 5/6: Введите <b>risk_level</b> (low / medium / high):",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_risk_level)
async def strategy_create_wizard_risk(message: Message, state: FSMContext):
    risk = sanitize_input(message.text or "", max_length=20).lower().strip()
    if risk not in {"low", "medium", "high"}:
        await message.answer("❌ Некорректный risk_level. Допустимо: low, medium, high")
        return

    await state.update_data(risk_level=risk)
    await state.set_state(StrategyWizardStates.waiting_private_params)
    await message.answer(
        "Шаг 6/6: (опционально) Отправьте <b>конфиденциальные параметры</b> (JSON) — они будут зашифрованы.\n"
        "Или отправьте <code>skip</code>.\n\n"
        "Пример:\n"
        "<code>{\"exchange\": \"binance\", \"api_key\": \"...\", \"api_secret\": \"...\"}</code>",
        parse_mode="HTML",
    )


@router.message(StrategyWizardStates.waiting_private_params)
async def strategy_create_wizard_private(message: Message, state: FSMContext):
    raw = sanitize_input(message.text or "", max_length=8000)
    private_params = None
    if raw.lower() != "skip":
        if raw.startswith("{"):
            try:
                private_params = json.loads(raw)
            except Exception:
                await message.answer("❌ Некорректный JSON. Отправьте корректный JSON или 'skip':")
                return
        else:
            private_params = {"raw": raw}

    await state.update_data(private_params=private_params)
    data = await state.get_data()

    summary = (
        "✅ <b>Проверьте конфигурацию стратегии</b>\n\n"
        f"📛 Название: <b>{data.get('name')}</b>\n"
        f"📈 Symbol(ы): <code>{', '.join(data.get('symbols', []))}</code>\n"
        f"⏰ Timeframe: <code>{data.get('timeframe')}</code>\n"
        f"🛡 Risk level: <code>{data.get('risk_level')}</code>\n"
        f"📊 Indicators: <code>{json.dumps(data.get('indicators', {}), ensure_ascii=False)[:500]}</code>\n"
        f"🔐 Private params: <b>{'заданы (будут зашифрованы)' if data.get('private_params') else 'нет'}</b>\n\n"
        "Сохранить стратегию?"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить и Активировать", callback_data="strategy_wizard_save_active")],
        [InlineKeyboardButton(text="💾 Сохранить (не активировать)", callback_data="strategy_wizard_save_inactive")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="strategy_wizard_cancel")],
    ])

    await state.set_state(StrategyWizardStates.confirming)
    await message.answer(summary, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.in_({"strategy_wizard_save_active", "strategy_wizard_save_inactive"}))
async def strategy_wizard_save(callback: CallbackQuery, state: FSMContext):
    await callback.answer("💾 Сохранение...")
    data = await state.get_data()
    if not data.get("name"):
        await state.clear()
        await callback.message.edit_text("❌ Данные мастера потеряны. Откройте /menu и начните заново.", parse_mode="HTML")
        return

    is_active = callback.data == "strategy_wizard_save_active"

    manager = get_strategy_manager()
    strategy_id = await manager.create_strategy(
        name=data["name"],
        description=None,
        is_active=is_active,
        assets_to_monitor=data.get("symbols") or [],
        timeframe=data.get("timeframe") or "1h",
        indicators=data.get("indicators") or {},
        risk_management={"risk_level": data.get("risk_level")},
        private_params=data.get("private_params"),
        created_by_ai=False,
    )

    await state.clear()

    if strategy_id:
        await callback.message.edit_text(
            "✅ <b>Стратегия сохранена</b>\n\n"
            f"🆔 ID: <code>{strategy_id}</code>\n"
            f"📛 Название: <b>{data['name']}</b>\n"
            f"📊 Статус: <b>{'active' if is_active else 'inactive'}</b>",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Не удалось сохранить стратегию</b>\n\nПроверьте подключение к Supabase и схему таблиц.",
            reply_markup=get_strategies_menu_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "strategy_wizard_cancel")
async def strategy_wizard_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание стратегии отменено.",
        reply_markup=get_strategies_menu_keyboard(),
        parse_mode="HTML",
    )
