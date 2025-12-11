import os
import logging
import asyncio
import requests
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
# from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT # Раскомментируйте, когда будете интегрировать LLM
from typing import List, Dict, Any, Optional

# ============================ КОНФИГУРАЦИЯ ============================
load_dotenv()

# Новый токен для админского бота
BOT_TOKEN = os.getenv("BOT_TOKEN") # 7945037510:AAFdm4vYfd_nvBX_R1SAIoZhbJPwFebrdTQ
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

# ВАЖНО: список администраторов
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "7746862973") # Замените на свой ID
ADMIN_IDS: List[int] = [int(i.strip()) for i in ADMIN_IDS_STR.split(',')]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not all([BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("❌ Отсутствуют ключевые переменные окружения для Bot #2.")

# Состояния FSM для админ-чата
(WAITING_FOR_STRATEGY_INPUT,) = range(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========================== КЛАССЫ И УТИЛИТЫ ==========================

class SupabaseManager:
    """Управление Supabase для чтения/записи данных ядра."""
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation' # Запрашиваем полный ответ для админа
        }

    def request(self, table, method='GET', data=None, filters=None):
        """Универсальный запрос к Supabase"""
        url = f"{self.url}/rest/v1/{table}"
        if filters:
            url += f"?{filters}"
        
        try:
            if method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == 'GET':
                response = requests.get(url, headers=self.headers)
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.content else {'status': 'success'}
            
            logger.error(f"Supabase error ({method} on {table}): Status {response.status_code}, Body: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Supabase network error: {e}")
            return None

    async def save_strategy_settings(self, admin_id: int, settings: Dict[str, Any]):
        """Сохранение/обновление настроек стратегии"""
        # В Supabase должна быть таблица 'strategy_settings'
        data = {
            'admin_id': admin_id,
            'parameters': settings,
            'updated_at': datetime.now().isoformat()
        }
        # Ищем существующую запись по admin_id, чтобы сделать upsert (если таблица настроена как RLS/Primary Key)
        # В простейшем случае: всегда обновляем единственную запись или вставляем новую.
        return self.request('strategy_settings', 'POST', data)

    async def get_strategy_settings(self):
        """Чтение текущих настроек стратегии"""
        # Читаем последнюю активную стратегию
        return self.request('strategy_settings', filters='order=updated_at.desc&limit=1')

    async def save_screenshot(self, admin_id: int, image_url: str, caption: str):
        """Сохранение скриншота для анализа ядром PA"""
        data = {
            'admin_id': admin_id,
            'image_url': image_url,
            'caption': caption,
            'analyzed': False,
            'created_at': datetime.now().isoformat()
        }
        return self.request('admin_screenshots', 'POST', data)

# Инициализация
db_core = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)

# =========================== ХЭНДЛЕРЫ КОМАНД ===========================

def is_admin(user_id: int) -> bool:
    """Проверка прав администратора."""
    return user_id in ADMIN_IDS

async def admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Универсальная проверка, прерывающая выполнение для не-админов."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.effective_message.reply_text("❌ У вас нет прав администратора для доступа к Ядру-Интерфейсу.")
        return False
    return True

async def manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """👑 Главное меню администратора."""
    if not await admin_check(update, context): return
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Настроить Стратегию", callback_data='admin_set_strategy')],
        [InlineKeyboardButton("🧠 Чат со Стратегией (/chat)", callback_data='admin_start_llm')],
        [InlineKeyboardButton("📜 Логи Ядра", callback_data='admin_view_logs')],
        [InlineKeyboardButton("📊 Статистика Сделок", callback_data='admin_view_stats')],
        [InlineKeyboardButton("⬆️ Прислать Скриншот", callback_data='admin_upload_photo')]
    ]
    
    await update.message.reply_text(
        "👑 *Админ-Меню Ядра*\n\n"
        "Управление AI Core, LLM-обучением и синхронизацией.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def set_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Парсинг и установка настроек стратегии."""
    if not await admin_check(update, context): return
    
    # Пример: /set_strategy RSI=14, MACD_Fast=12, Min_Confidence=95
    text = update.message.text
    try:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await update.message.reply_text("💡 *Формат:* `/set_strategy RSI=14, MACD_Fast=12, ...`")
            return
            
        settings_str = parts[1]
        settings: Dict[str, Any] = {}
        
        for item in settings_str.split(','):
            key_value = item.strip().split('=')
            if len(key_value) == 2:
                key = key_value[0].strip()
                value_str = key_value[1].strip()
                # Попытка преобразовать значение в число, иначе оставить строкой
                try:
                    settings[key] = float(value_str) if '.' in value_str else int(value_str)
                except ValueError:
                    settings[key] = value_str
        
        if not settings:
            await update.message.reply_text("❌ Не удалось разобрать настройки. Проверьте формат.")
            return

        success = await db_core.save_strategy_settings(update.effective_user.id, settings)
        
        if success:
            await update.message.reply_text(
                "✅ *НАСТРОЙКИ СТРАТЕГИИ СОХРАНЕНЫ*\n\n"
                f"Ядро PA начнет использовать новые параметры:\n`{json.dumps(settings, indent=2)}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ *Ошибка сохранения в Supabase*.")
            
    except Exception as e:
        logger.error(f"Error processing set_strategy: {e}")
        await update.message.reply_text("❌ Произошла внутренняя ошибка при обработке команды.")

async def handle_admin_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await admin_check(update, context): return
    
    data = query.data
    
    if data == 'admin_upload_photo':
        await query.edit_message_text(
            "⬆️ *Загрузка Скриншота*\n\n"
            "Пришлите мне скриншот с подписью (опционально) для анализа ядром PA.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data='manager')]]),
            parse_mode='Markdown'
        )
    elif data == 'admin_start_llm':
        await query.edit_message_text(
            "🧠 *Чат со Стратегией (LLM)*\n\n"
            "Введите свой вопрос или инструкцию для AI (например: 'Повысить уверенность до 95%').",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data='manager')]]),
            parse_mode='Markdown'
        )
        return WAITING_FOR_STRATEGY_INPUT
    
    elif data == 'manager':
        # Возврат в админ-меню
        await manager_command(update, context)


# =========================== FSM (LLM Chat) ===========================

async def llm_chat_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода для LLM-чата."""
    if not await admin_check(update, context): return
    
    user_input = update.message.text
    user_id = update.effective_user.id
    
    # 1. Заглушка для LLM-логики
    
    # if ANTHROPIC_API_KEY:
    #     client = Anthropic(api_key=ANTHROPIC_API_KEY)
    #     prompt = f"{HUMAN_PROMPT} Текущие настройки стратегии: {current_settings}. Пользователь {user_id} говорит: '{user_input}'. Проанализируй и предложи изменения в формате JSON."
    #     response = client.messages.create(
    #         model="claude-3-sonnet-20240229", 
    #         max_tokens=1000, 
    #         messages=[{"role": "user", "content": prompt}]
    #     ).content[0].text
    # else:
    response = "Извините, LLM-ключ не настроен. Но я бы ответил, что нужно повысить порог RSI до 75."

    await update.message.reply_text(
        f"🧠 *Ответ AI по стратегии:*\n\n"
        f"```{response}```\n\n"
        "Введите следующий вопрос или /manager для выхода.",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_STRATEGY_INPUT # Остаемся в состоянии чата

# =========================== Хэндлер Фото ===========================

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка скриншота от администратора."""
    if not await admin_check(update, context): return
    
    user_id = update.effective_user.id
    message = update.effective_message
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Получаем ссылку на файл (Telegram File API)
    file_obj = await context.bot.get_file(file_id)
    file_url = file_obj.file_path
    
    caption = message.caption or 'Нет подписи'
    
    # 1. Сохранение в Supabase
    success = await db_core.save_screenshot(user_id, file_url, caption)
    
    if success:
        await message.reply_text(
            "✅ *Скриншот отправлен на анализ!*\n\n"
            "Ядро PA получит ссылку и проанализирует изображение.\n"
            f"URL: `{file_url}`\n"
            f"Подпись: *{caption}*",
            parse_mode='Markdown'
        )
    else:
        await message.reply_text("❌ *Ошибка сохранения скриншота в Supabase*.")


# =========================== ЗАПУСК БОТА ===========================

async def set_admin_commands(application: Application):
    """Установка команд бота."""
    commands = [BotCommand(command, description) for command, description in [
        ("manager", "👑 Главное меню администратора"),
        ("set_strategy", "⚙️ Установить стратегию"),
        ("chat", "🧠 Чат со Стратегией"),
    ]]
    await application.bot.set_my_commands(commands)

def main():
    application = Application.builder().token(BOT_TOKEN).post_init(set_admin_commands).build()
    
    # Хэндлер для основной команды менеджера
    application.add_handler(CommandHandler("manager", manager_command))
    application.add_handler(CommandHandler("set_strategy", set_strategy_command))
    
    # Хэндлер для фото (скриншотов)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Хэндлер для FSM (LLM Chat)
    llm_chat_handler = ConversationHandler(
        entry_points=[CommandHandler("chat", llm_chat_input), CallbackQueryHandler(llm_chat_input, pattern='^admin_start_llm$')],
        states={
            WAITING_FOR_STRATEGY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, llm_chat_input)],
        },
        fallbacks=[CommandHandler('manager', manager_command)]
    )
    application.add_handler(llm_chat_handler)
    
    # Хэндлер для CallbackQuery
    application.add_handler(CallbackQueryHandler(handle_admin_callback_query))
    
    logger.info("🚀 Core Manager Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
