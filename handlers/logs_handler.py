"""
Обработчик просмотра логов и мониторинга
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database import db
from keyboards import get_core_analysis_keyboard
from utils import format_decision_log

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🧠 Логика Анализа Ядра")
async def core_analysis_menu(message: Message):
    """Экран логики анализа Ядра: последние 10–20 записей decision logs"""
    await _render_core_analysis(message)


@router.callback_query(F.data.in_({"core_analysis_refresh"}))
async def core_analysis_refresh(callback: CallbackQuery):
    await callback.answer("🔄 Обновление...")
    await _render_core_analysis(callback.message, edit=True)


async def _render_core_analysis(message: Message, edit: bool = False):
    logs = await db.get_decision_logs(limit=20)
    
    if not logs:
        text = (
            "🧠 <b>Логика Анализа Ядра</b>\n\n"
            "📋 <b>Записей пока нет</b>\n\n"
            "Ядро ещё не записывало рассуждения/решения."
        )
    else:
        text = "🧠 <b>Логика Анализа Ядра</b>\n\n<i>Последние решения (10–20):</i>\n\n"
        for log in logs[:15]:
            text += format_decision_log(log)
            text += "\n" + "─" * 30 + "\n"
    
    if edit and getattr(message, "edit_text", None):
        await message.edit_text(text, reply_markup=get_core_analysis_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=get_core_analysis_keyboard(), parse_mode="HTML")
