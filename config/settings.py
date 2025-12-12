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
    ADMIN_CHAT_ID: Optional[int] = int(os.getenv("ADMIN_CHAT_ID", "0")) if os.getenv("ADMIN_CHAT_ID") else None
    
    # Единственный администратор (Repo 02 должен быть доступен только ему)
    ADMIN_USER_ID: Optional[int] = (
        int(os.getenv("ADMIN_USER_ID", "0")) if os.getenv("ADMIN_USER_ID") else None
    )
    
    # Supabase - ВАЖНО: используется Service Role Key для полного доступа
    # Admin Core (Repo 02) требует Service Role Key для управления всеми данными
    # UI/Trading Bot (Repo 01) использует NEXT_PUBLIC_SUPABASE_KEY (ограниченный доступ)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Ключ шифрования для конфиденциальных данных
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    
    # Список ID админов (legacy; по ТЗ предпочтительно ADMIN_USER_ID)
    _ADMIN_IDS_RAW: list[int] = [
        int(admin_id.strip())
        for admin_id in os.getenv("ADMIN_IDS", "").split(",")
        if admin_id.strip()
    ]
    
    @property
    def ADMIN_IDS(self) -> list[int]:
        """Список админов. Если задан ADMIN_USER_ID — доступ только ему."""
        if self.ADMIN_USER_ID:
            return [self.ADMIN_USER_ID]
        return self._ADMIN_IDS_RAW
    
    # Настройки бота
    BOT_NAME: str = os.getenv("BOT_NAME", "Trading Admin Panel")
    WELCOME_MESSAGE: str = os.getenv("WELCOME_MESSAGE", "Добро пожаловать в админ-панель!")

    # Интервал фонового цикла Ядра (секунды)
    CORE_LOOP_INTERVAL_SECONDS: int = int(os.getenv("CORE_LOOP_INTERVAL_SECONDS", "60"))
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных переменных"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN_ADMIN не установлен")
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY не установлены")
        # Repo 02: доступ строго одному админу
        if not cls.ADMIN_USER_ID and not cls._ADMIN_IDS_RAW:
            raise ValueError("ADMIN_USER_ID (или legacy ADMIN_IDS) не установлен — доступ админ-панели не защищён")
        if not cls.ADMIN_CHAT_ID:
            print("⚠️ ADMIN_CHAT_ID не установлен, системные уведомления не будут отправляться!")
        if not cls.ENCRYPTION_KEY:
            print("⚠️ ENCRYPTION_KEY не установлен, шифрование конфиденциальных данных будет недоступно!")
        return True


settings = Settings()
