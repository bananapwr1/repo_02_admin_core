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
    # Требуется ровно одна переменная:
    #   TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Единственный администратор (Repo 02 должен быть доступен только ему)
    ADMIN_USER_ID: Optional[int] = (
        int(os.getenv("ADMIN_USER_ID", "0")) if os.getenv("ADMIN_USER_ID") else None
    )
    
    # Supabase - ВАЖНО: используется Service Role Key для полного доступа
    # Требуются ровно две переменные:
    #   SUPABASE_BASE_URL
    #   SUPABASE_SERVICE_KEY (или SUPABASE_KEY)
    SUPABASE_URL: str = os.getenv("SUPABASE_BASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    # Внутренний алиас для существующего кода (НЕ отдельная env-переменная)
    SUPABASE_KEY: str = SUPABASE_SERVICE_KEY
    
    # Ключ шифрования для конфиденциальных данных
    # Требуется ровно одна переменная:
    #   SUPABASE_ENCRYPTION_KEY
    ENCRYPTION_KEY: str = os.getenv("SUPABASE_ENCRYPTION_KEY", "")
    
    @property
    def ADMIN_IDS(self) -> list[int]:
        """Список админов. Repo 02: доступ строго ADMIN_USER_ID."""
        return [self.ADMIN_USER_ID] if self.ADMIN_USER_ID else []
    
    # Настройки бота
    # (НЕ читаются из env — чтобы не раздувать конфигурацию)
    BOT_NAME: str = "Trading Admin Panel"
    WELCOME_MESSAGE: str = "Добро пожаловать в админ-панель!"

    # Интервал фонового цикла Ядра (секунды)
    # (НЕ читается из env — чтобы не раздувать конфигурацию)
    CORE_LOOP_INTERVAL_SECONDS: int = 60
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных переменных"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_BASE_URL или SUPABASE_SERVICE_KEY (или SUPABASE_KEY) не установлены")
        # Repo 02: доступ строго одному админу
        if not cls.ADMIN_USER_ID:
            raise ValueError("ADMIN_USER_ID не установлен — доступ админ-панели не защищён")
        if not cls.ENCRYPTION_KEY:
            print("⚠️ SUPABASE_ENCRYPTION_KEY не установлен, шифрование конфиденциальных данных будет недоступно!")
        return True


settings = Settings()
