"""
Конфигурация Admin Panel Bot
"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings:
    """Настройки приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN_ADMIN", "")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # OpenAI для AI-чата стратегий
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # Список ID админов (через запятую в .env)
    ADMIN_IDS: list[int] = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
        if admin_id.strip()
    ]
    
    # Настройки бота
    BOT_NAME: str = os.getenv("BOT_NAME", "Trading Admin Panel")
    WELCOME_MESSAGE: str = os.getenv("WELCOME_MESSAGE", "Добро пожаловать в админ-панель!")
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных переменных"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN_ADMIN не установлен")
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY не установлены")
        if not cls.ADMIN_IDS:
            print("⚠️ ADMIN_IDS не установлен, все пользователи будут иметь доступ!")
        return True


settings = Settings()
