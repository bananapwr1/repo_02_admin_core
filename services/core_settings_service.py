"""
Сервис хранения внутренних настроек/секретов Ядра в Supabase.
Секреты шифруются с использованием ENCRYPTION_KEY (Fernet).
"""

import logging
from typing import Optional

from database import db
from services.strategy_manager_service import EncryptionService

logger = logging.getLogger(__name__)


class CoreSettingsService:
    """CRUD для зашифрованных настроек Ядра"""

    def __init__(self):
        self.encryption = EncryptionService()

    def is_encryption_available(self) -> bool:
        return self.encryption.is_available()

    async def get_secret(self, key: str) -> Optional[str]:
        """Получить секрет (в расшифрованном виде)."""
        record = await db.get_core_setting(key)
        if not record:
            return None

        encrypted_value = record.get("value_encrypted")
        if not encrypted_value:
            return None

        if not self.encryption.is_available():
            # Никогда не возвращаем зашифрованное значение в интерфейс как есть
            return None

        return self.encryption.decrypt(encrypted_value)

    async def set_secret(self, key: str, value: str) -> bool:
        """Сохранить секрет (в БД — только зашифрованный)."""
        if not self.encryption.is_available():
            logger.warning("ENCRYPTION_KEY не настроен — отказ сохранения секрета")
            return False

        encrypted_value = self.encryption.encrypt(value)
        if not encrypted_value:
            return False

        return await db.set_core_setting(key=key, value_encrypted=encrypted_value)


_core_settings_service: Optional[CoreSettingsService] = None


def get_core_settings_service() -> CoreSettingsService:
    global _core_settings_service
    if _core_settings_service is None:
        _core_settings_service = CoreSettingsService()
    return _core_settings_service

