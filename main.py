#!/usr/bin/env python3
"""
CORE MANAGER BOT (Bot #2)
Админский интерфейс для управления торговым ядром
Только для ADMIN_IDS
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from supabase import create_client, Client
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения
load_dotenv()

# ============== НАСТРОЙКИ ==============
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Проверка обязательных переменных
if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY, ADMIN_IDS]):
    raise ValueError("Missing required environment variables!")

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============
def check_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def admin_only(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not check_admin(user_id):
            await update.message.reply_text(
                "⛔ У вас нет доступа к этому боту.\n"
                "Это админский интерфейс торгового ядра."
            )
            return
        
        return await func(update, context)
    
    return wrapper

def call_claude_api(prompt: str, system_prompt: str = None) -> Optional[str]:
    """Вызов Claude API через Anthropic"""
    if not ANTHROPIC_API_KEY:
        return "❌ ANTHROPIC_API_KEY не настроен"
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    messages = [{"role": "user", "content": prompt}]
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1000,
        "messages": messages
    }
    
    if system_prompt:
        data["system"] = system_prompt
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("content", [{}])[0].get("text", "Нет ответа")
        else:
            return f"❌ Ошибка API: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"❌ Исключение при вызове Claude: {str(e)}"

# ============== КОМАНДЫ АДМИНИСТРАТОРА ==============
@admin_only
async def start_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню управления ядром"""
    keyboard = [
        [InlineKeyboardButton("⚙️ Стратегии", callback_data="strategies_menu")],
        [InlineKeyboardButton("📊 AI-рассуждения", callback_data="ai_reasoning_menu")],
        [InlineKeyboardButton("🕵️ Парсер чатов", callback_data="parser_menu")],
        [InlineKeyboardButton("🤖 Авто-торговля", callback_data="autotrade_menu")],
        [InlineKeyboardButton("📈 Статистика", callback_data="stats_menu")],
        [InlineKeyboardButton("💬 Чат со стратегией", callback_data="chat_strategy")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text="🧠 **Управление торговым ядром**\n\n"
             "Выберите раздел:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@admin_only
async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка/изменение стратегии через Supabase"""
    if not context.args:
        await update.message.reply_text(
            "**Формат команды:**\n"
            "`/set_strategy название параметры`\n\n"
            "**Пример:**\n"
            "`/set_strategy Aggressive_RSI rsi_period=14 rsi_oversold=30 volume_threshold=1.5`\n\n"
            "**Доступные параметры:**\n"
            "- `rsi_period`: период RSI (7-21)\n"
            "- `rsi_oversold`: уровень перепроданности (20-40)\n"
            "- `rsi_overbought`: уровень перекупленности (60-80)\n"
            "- `macd_fast`: быстрая EMA (8-15)\n"
            "- `macd_slow`: медленная EMA (20-30)\n"
            "- `confidence_threshold`: мин. уверенность (50-90)\n"
            "- `for_autotrade`: true/false"
        )
        return
    
    strategy_name = context.args[0]
    parameters = {}
    
    # Парсинг параметров
    for arg in context.args[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            
            # Преобразование значений
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # Оставляем как строку
            
            parameters[key] = value
    
    # Сохраняем в Supabase
    try:
        result = supabase.table("strategy_settings").upsert({
            "admin_id": update.effective_user.id,
            "strategy_name": strategy_name,
            "parameters": parameters,
            "is_active": True,
            "for_autotrade": parameters.get("for_autotrade", False),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        strategy_id = result.data[0]['id'] if result.data else "N/A"
        
        await update.message.reply_text(
            f"✅ **Стратегия сохранена!**\n\n"
            f"**ID:** {strategy_id}\n"
            f"**Название:** {strategy_name}\n"
            f"**Параметры:**\n```json\n{json.dumps(parameters, indent=2, ensure_ascii=False)}\n```\n\n"
            f"Торговое ядро автоматически обновит настройки в течение 1 минуты.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Стратегия сохранена в Supabase: {strategy_name}")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения стратегии: {e}")
        await update.message.reply_text(
            f"❌ **Ошибка сохранения:**\n```\n{str(e)}\n```",
            parse_mode='Markdown'
        )

@admin_only
async def ai_reasoning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать последние AI-рассуждения"""
    limit = 5
    if context.args and context.args[0].isdigit():
        limit = min(int(context.args[0]), 20)
    
    try:
        response = supabase.table("ai_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        if not response.data:
            await update.message.reply_text("🤷 Нет AI-рассуждений в базе.")
            return
        
        message = f"🧠 **Последние {len(response.data)} AI-рассуждений:**\n\n"
        
        for i, log in enumerate(response.data, 1):
            signal_type = log.get('signal_type', 'Unknown')
            confidence = log.get('confidence', 0) * 100
            created_at = log.get('created_at', 'N/A')[:19]
            
            message += f"**{i}. {signal_type.upper()}**\n"
            message += f"   ⌚ {created_at}\n"
            message += f"   🎯 Уверенность: {confidence:.1f}%\n"
            
            reasoning = log.get('reasoning', '')
            if reasoning:
                # Обрезаем длинный текст
                if len(reasoning) > 150:
                    reasoning = reasoning[:150] + "..."
                message += f"   💭 {reasoning}\n"
            
            message += f"   ────────\n"
        
        await update.message.reply_text(
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения AI логов: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}"
        )

@admin_only
async def chat_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Чат с Claude о стратегиях"""
    if not context.args:
        await update.message.reply_text(
            "💬 **Чат со стратегией**\n\n"
            "Задайте вопрос о торговых стратегиях, AI-анализе или настройках ядра.\n\n"
            "**Формат:** `/chat ваш вопрос`\n"
            "**Примеры:**\n"
            "• `/chat Как улучшить точность RSI стратегии?`\n"
            "• `/chat Какие параметры MACD самые эффективные?`\n"
            "• `/chat Проанализируй последние 10 сигналов`"
        )
        return
    
    question = " ".join(context.args)
    
    # Получаем текущие стратегии для контекста
    try:
        strategies = supabase.table("strategy_settings") \
            .select("*") \
            .eq("is_active", True) \
            .execute()
        
        strategy_context = ""
        if strategies.data:
            strategy_context = "\n**Активные стратегии:**"
            for strat in strategies.data:
                strategy_context += f"\n- {strat['strategy_name']}: {strat.get('parameters', {})}"
    except Exception as e:
        strategy_context = f"\n⚠️ Не удалось загрузить стратегии: {e}"
    
    system_prompt = (
        "Ты - AI-помощник для управления торговым ядром. "
        "Отвечай кратко, технично, с фокусом на практическую реализацию. "
        "Предлагай конкретные параметры для улучшения стратегий. "
        "Если нужны данные из базы - скажи, какие именно."
    )
    
    full_prompt = (
        f"**Вопрос администратора:** {question}\n\n"
        f"{strategy_context}\n\n"
        f"Дай рекомендации по улучшению, настройке параметров или созданию новых стратегий. "
        f"Если вопрос требует данных из базы - укажи, какие данные нужны для полного ответа."
    )
    
    # Показываем "печатает..."
    typing_msg = await update.message.reply_text("🤔 Claude думает...")
    
    # Вызываем Claude API
    response = call_claude_api(full_prompt, system_prompt)
    
    # Удаляем сообщение "печатает..."
    await typing_msg.delete()
    
    # Отправляем ответ
    if response and not response.startswith("❌"):
        await update.message.reply_text(
            f"💡 **Claude отвечает:**\n\n{response}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Ошибка API:**\n{response}"
        )

@admin_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка скриншотов от администратора"""
    try:
        # Получаем фото
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        # Здесь должна быть логика сохранения фото (в Supabase storage или другой сервис)
        # Пока сохраняем только информацию о фото
        
        supabase.table("admin_screenshots").insert({
            "admin_id": update.effective_user.id,
            "file_id": file.file_id,
            "caption": update.message.caption or "",
            "analyzed": False,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        await update.message.reply_text(
            "📸 **Скриншот сохранен!**\n\n"
            "Ядро проанализирует его в течение нескольких минут.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await update.message.reply_text(
            f"❌ Ошибка обработки скриншота: {str(e)}"
        )

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику ядра"""
    try:
        # Получаем общую статистику
        signals_count = supabase.table("ai_signals") \
            .select("id", count="exact") \
            .execute()
        
        users_count = supabase.table("signal_requests") \
            .select("user_id", count="exact") \
            .execute()
        
        successful_signals = supabase.table("ai_signals") \
            .select("id", count="exact") \
            .gt("confidence", 0.7) \
            .execute()
        
        message = (
            "📊 **Статистика торгового ядра**\n\n"
            f"• Всего сигналов: {signals_count.count or 0}\n"
            f"• Успешных сигналов (confidence > 70%): {successful_signals.count or 0}\n"
            f"• Активных пользователей: {users_count.count or 0}\n"
            f"• Активных стратегий: {get_active_strategies_count()}\n\n"
            "Для детальной статистики используйте /stats_detailed"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

def get_active_strategies_count() -> int:
    """Получить количество активных стратегий"""
    try:
        result = supabase.table("strategy_settings") \
            .select("id", count="exact") \
            .eq("is_active", True) \
            .execute()
        return result.count or 0
    except:
        return 0

# ============== ОБРАБОТЧИКИ INLINE КНОПОК ==============
@admin_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "strategies_menu":
        await show_strategies_menu(query)
    elif data == "ai_reasoning_menu":
        await ai_reasoning_from_button(query)
    elif data == "parser_menu":
        await parser_menu(query)
    elif data == "autotrade_menu":
        await autotrade_menu(query)
    elif data == "stats_menu":
        await stats_from_button(query)
    elif data == "chat_strategy":
        await chat_strategy_from_button(query)
    else:
        await query.edit_message_text("Неизвестная команда")

async def show_strategies_menu(query):
    """Меню стратегий"""
    keyboard = [
        [InlineKeyboardButton("📋 Список стратегий", callback_data="list_strategies")],
        [InlineKeyboardButton("➕ Новая стратегия", callback_data="new_strategy")],
        [InlineKeyboardButton("⚙️ Редактировать", callback_data="edit_strategy")],
        [InlineKeyboardButton("📊 Тест стратегии", callback_data="test_strategy")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text="⚙️ **Управление стратегиями**\n\n"
             "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def ai_reasoning_from_button(query):
    """AI-рассуждения из кнопки"""
    await query.edit_message_text(
        text="📊 **AI-рассуждения**\n\n"
             "Используйте команду:\n"
             "`/ai_reasoning [количество]`\n\n"
             "Пример: `/ai_reasoning 10`\n"
             "Покажет последние 10 AI-рассуждений.",
        parse_mode='Markdown'
    )

async def parser_menu(query):
    """Меню парсера"""
    keyboard = [
        [InlineKeyboardButton("📊 Статус парсера", callback_data="parser_status")],
        [InlineKeyboardButton("🔄 Исторический парсинг", callback_data="parser_historical")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="parser_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text="🕵️ **Парсер Telegram чатов**\n\n"
             "Мониторинг сигналов из ваших чатов.\n"
             "Быстрый чат: постоянно\n"
             "Премиум чат: раз в день + пре-сигналы",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def autotrade_menu(query):
    """Меню авто-торговли"""
    keyboard = [
        [InlineKeyboardButton("🚀 Запуск демо", callback_data="start_demo")],
        [InlineKeyboardButton("⏸️ Пауза", callback_data="pause_autotrade")],
        [InlineKeyboardButton("📊 Статистика", callback_data="autotrade_stats")],
        [InlineKeyboardButton("⚙️ Настройки риска", callback_data="risk_settings")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text="🤖 **Авто-торговля**\n\n"
             "Текущий статус: ⏸️ Неактивна\n"
             "Исполнитель: Amvera\n"
             "Режим: Демо",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def stats_from_button(query):
    """Статистика из кнопки"""
    await query.edit_message_text(
        text="📈 **Статистика**\n\n"
             "Используйте команды:\n"
             "• `/stats` - общая статистика\n"
             "• `/stats_detailed` - детальная\n"
             "• `/stats_signals` - по сигналам\n"
             "• `/stats_users` - по пользователям",
        parse_mode='Markdown'
    )

async def chat_strategy_from_button(query):
    """Чат со стратегией из кнопки"""
    await query.edit_message_text(
        text="💬 **Чат со стратегией**\n\n"
             "Используйте команду:\n"
             "`/chat ваш вопрос`\n\n"
             "Примеры вопросов:\n"
             "• Как улучшить точность RSI?\n"
             "• Какие лучшие параметры MACD?\n"
             "• Проанализируй последние сигналы",
        parse_mode='Markdown'
    )

# ============== ОСНОВНАЯ ФУНКЦИЯ ==============
def main():
    """Запуск бота #2"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start_manager))
    application.add_handler(CommandHandler("manager", start_manager))
    application.add_handler(CommandHandler("set_strategy", set_strategy))
    application.add_handler(CommandHandler("ai_reasoning", ai_reasoning_command))
    application.add_handler(CommandHandler("chat", chat_strategy_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запуск бота
    logger.info("Bot #2 (Core Manager) starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
