"""
Сервис управления стратегиями с шифрованием
Обеспечивает безопасное хранение и управление торговыми стратегиями
"""
import logging
import json
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet, InvalidToken
from database import db
from config.settings import settings
from services.notification_service import get_notification_service

logger = logging.getLogger(__name__)


class EncryptionService:
    """Сервис шифрования/расшифровки данных"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Инициализация сервиса шифрования
        
        Args:
            encryption_key: Ключ шифрования (base64). Если не указан, берется из настроек.
        """
        self.encryption_key = encryption_key or settings.ENCRYPTION_KEY
        self.cipher_suite: Optional[Fernet] = None
        
        if self.encryption_key:
            try:
                # Проверяем формат ключа
                key_bytes = self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key
                self.cipher_suite = Fernet(key_bytes)
                logger.info("✅ Сервис шифрования инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации шифрования: {e}")
                self.cipher_suite = None
        else:
            logger.warning("⚠️ SUPABASE_ENCRYPTION_KEY не установлен, шифрование недоступно")
    
    def is_available(self) -> bool:
        """Проверка доступности шифрования"""
        return self.cipher_suite is not None
    
    def encrypt(self, data: str) -> Optional[str]:
        """
        Зашифровать данные
        
        Args:
            data: Строка для шифрования
        
        Returns:
            Зашифрованная строка или None при ошибке
        """
        if not self.is_available():
            logger.warning("⚠️ Шифрование недоступно, данные не зашифрованы")
            return None
        
        try:
            encrypted_bytes = self.cipher_suite.encrypt(data.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования: {e}")
            return None
    
    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Расшифровать данные
        
        Args:
            encrypted_data: Зашифрованная строка
        
        Returns:
            Расшифрованная строка или None при ошибке
        """
        if not self.is_available():
            logger.warning("⚠️ Шифрование недоступно, данные не расшифрованы")
            return None
        
        try:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("❌ Неверный ключ шифрования или поврежденные данные")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка расшифровки: {e}")
            return None
    
    def encrypt_json(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Зашифровать JSON-данные
        
        Args:
            data: Словарь для шифрования
        
        Returns:
            Зашифрованная строка JSON или None при ошибке
        """
        try:
            json_string = json.dumps(data, ensure_ascii=False)
            return self.encrypt(json_string)
        except Exception as e:
            logger.error(f"❌ Ошибка сериализации JSON перед шифрованием: {e}")
            return None
    
    def decrypt_json(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        Расшифровать JSON-данные
        
        Args:
            encrypted_data: Зашифрованная строка JSON
        
        Returns:
            Расшифрованный словарь или None при ошибке
        """
        try:
            decrypted_string = self.decrypt(encrypted_data)
            if decrypted_string:
                return json.loads(decrypted_string)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка десериализации JSON после расшифровки: {e}")
            return None


class StrategyManagerService:
    """Сервис управления торговыми стратегиями"""
    
    def __init__(self):
        """Инициализация сервиса управления стратегиями"""
        self.encryption_service = EncryptionService()
        self.notification_service = get_notification_service()
        
        # Поля, которые должны быть зашифрованы
        self.encrypted_fields = [
            "api_keys",           # API ключи бирж
            "secret_keys",        # Секретные ключи
            "private_params",     # Приватные параметры
            "credentials"         # Учетные данные
        ]
    
    def _encrypt_sensitive_data(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Зашифровать конфиденциальные поля стратегии
        
        Args:
            strategy_data: Данные стратегии
        
        Returns:
            Данные с зашифрованными полями
        """
        if not self.encryption_service.is_available():
            logger.warning("⚠️ Шифрование недоступно, конфиденциальные данные не защищены")
            return strategy_data
        
        encrypted_data = strategy_data.copy()
        
        for field in self.encrypted_fields:
            if field in encrypted_data and encrypted_data[field]:
                # Шифруем поле, если оно присутствует и не пустое
                encrypted_value = self.encryption_service.encrypt_json(encrypted_data[field])
                if encrypted_value:
                    encrypted_data[f"{field}_encrypted"] = encrypted_value
                    # Удаляем оригинальное поле для безопасности
                    del encrypted_data[field]
                else:
                    logger.error(f"❌ Не удалось зашифровать поле '{field}'")
        
        return encrypted_data
    
    def _decrypt_sensitive_data(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Расшифровать конфиденциальные поля стратегии
        
        Args:
            strategy_data: Данные стратегии из БД
        
        Returns:
            Данные с расшифрованными полями
        """
        if not self.encryption_service.is_available():
            return strategy_data
        
        decrypted_data = strategy_data.copy()
        
        for field in self.encrypted_fields:
            encrypted_field = f"{field}_encrypted"
            if encrypted_field in decrypted_data and decrypted_data[encrypted_field]:
                # Расшифровываем поле
                decrypted_value = self.encryption_service.decrypt_json(decrypted_data[encrypted_field])
                if decrypted_value:
                    decrypted_data[field] = decrypted_value
                    # Удаляем зашифрованное поле из результата
                    del decrypted_data[encrypted_field]
                else:
                    logger.error(f"❌ Не удалось расшифровать поле '{field}'")
                    # Оставляем зашифрованное поле на месте
        
        return decrypted_data
    
    async def create_strategy(
        self,
        name: str,
        description: Optional[str] = None,
        is_active: bool = False,
        assets_to_monitor: Optional[List[str]] = None,
        timeframe: str = "1h",
        indicators: Optional[Dict[str, Any]] = None,
        entry_rules: Optional[Dict[str, Any]] = None,
        exit_rules: Optional[Dict[str, Any]] = None,
        risk_management: Optional[Dict[str, Any]] = None,
        api_keys: Optional[Dict[str, str]] = None,
        secret_keys: Optional[Dict[str, str]] = None,
        private_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Создать новую торговую стратегию
        
        Args:
            name: Название стратегии
            description: Описание стратегии
            is_active: Активна ли стратегия
            assets_to_monitor: Список активов для мониторинга
            timeframe: Таймфрейм (1h, 4h, 1d)
            indicators: Настройки индикаторов
            entry_rules: Правила входа
            exit_rules: Правила выхода
            risk_management: Управление рисками
            api_keys: API ключи (будут зашифрованы)
            secret_keys: Секретные ключи (будут зашифрованы)
            private_params: Приватные параметры (будут зашифрованы)
        Returns:
            ID созданной стратегии или None при ошибке
        """
        try:
            logger.info(f"📊 Создание новой стратегии: {name}")
            
            # Подготовка данных стратегии
            strategy_data = {
                "name": name,
                "description": description,
                "is_active": is_active,
                "assets_to_monitor": assets_to_monitor or [],
                "timeframe": timeframe,
                "indicators": indicators or {},
                "entry_rules": entry_rules or {},
                "exit_rules": exit_rules or {},
                "risk_management": risk_management or {}
            }
            
            # Добавляем конфиденциальные данные (если есть)
            if api_keys:
                strategy_data["api_keys"] = api_keys
            if secret_keys:
                strategy_data["secret_keys"] = secret_keys
            if private_params:
                strategy_data["private_params"] = private_params
            
            # Шифруем конфиденциальные поля
            encrypted_strategy_data = self._encrypt_sensitive_data(strategy_data)
            
            # Сохраняем в базу данных (используется Service Role Key через SUPABASE_SERVICE_KEY)
            success = await db.create_strategy(encrypted_strategy_data)
            
            if success:
                # Получаем ID созданной стратегии
                strategies = await db.get_all_strategies()
                created_strategy = next(
                    (s for s in strategies if s["name"] == name),
                    None
                )
                
                if created_strategy:
                    strategy_id = created_strategy["id"]
                    logger.info(f"✅ Стратегия '{name}' успешно создана (ID: {strategy_id})")
                    
                    # Отправляем уведомление
                    await self.notification_service.notify_strategy_created(name, strategy_id)
                    if is_active:
                        await self.notification_service.notify_strategy_activated(name, strategy_id)
                    
                    return strategy_id
            
            logger.error(f"❌ Не удалось создать стратегию '{name}'")
            return None
            
        except Exception as e:
            error_msg = f"Ошибка при создании стратегии '{name}': {e}"
            logger.error(f"❌ {error_msg}")
            await self.notification_service.notify_error(error_msg, "STRATEGY_CREATE")
            return None
    
    async def get_all_strategies(self, decrypt: bool = True) -> List[Dict[str, Any]]:
        """
        Получить все стратегии
        
        Args:
            decrypt: Расшифровывать ли конфиденциальные данные
        
        Returns:
            Список стратегий
        """
        try:
            strategies = await db.get_all_strategies()
            
            if decrypt and self.encryption_service.is_available():
                return [self._decrypt_sensitive_data(s) for s in strategies]
            
            return strategies
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения стратегий: {e}")
            return []
    
    async def get_active_strategies(self, decrypt: bool = True) -> List[Dict[str, Any]]:
        """
        Получить активные стратегии
        
        Args:
            decrypt: Расшифровывать ли конфиденциальные данные
        
        Returns:
            Список активных стратегий
        """
        try:
            all_strategies = await self.get_all_strategies(decrypt=decrypt)
            return [s for s in all_strategies if s.get("is_active", False)]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных стратегий: {e}")
            return []
    
    async def get_strategy_by_id(
        self, 
        strategy_id: int, 
        decrypt: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Получить стратегию по ID
        
        Args:
            strategy_id: ID стратегии
            decrypt: Расшифровывать ли конфиденциальные данные
        
        Returns:
            Данные стратегии или None
        """
        try:
            strategies = await self.get_all_strategies(decrypt=decrypt)
            return next((s for s in strategies if s["id"] == strategy_id), None)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения стратегии {strategy_id}: {e}")
            return None
    
    async def activate_strategy(self, strategy_id: int) -> bool:
        """
        Активировать стратегию
        
        Args:
            strategy_id: ID стратегии
        
        Returns:
            True если успешно активирована
        """
        try:
            logger.info(f"🔄 Активация стратегии ID: {strategy_id}")
            
            # Получаем данные стратегии
            strategy = await self.get_strategy_by_id(strategy_id, decrypt=False)
            if not strategy:
                logger.error(f"❌ Стратегия {strategy_id} не найдена")
                return False
            
            # Активируем стратегию (автоматически деактивируются другие)
            success = await db.update_strategy_status(strategy_id, is_active=True)
            
            if success:
                logger.info(f"✅ Стратегия '{strategy['name']}' активирована")
                await self.notification_service.notify_strategy_activated(
                    strategy["name"], 
                    strategy_id
                )
                return True
            
            logger.error(f"❌ Не удалось активировать стратегию {strategy_id}")
            return False
            
        except Exception as e:
            error_msg = f"Ошибка активации стратегии {strategy_id}: {e}"
            logger.error(f"❌ {error_msg}")
            await self.notification_service.notify_error(error_msg, "STRATEGY_ACTIVATE")
            return False
    
    async def deactivate_strategy(self, strategy_id: int) -> bool:
        """
        Деактивировать стратегию
        
        Args:
            strategy_id: ID стратегии
        
        Returns:
            True если успешно деактивирована
        """
        try:
            logger.info(f"🔄 Деактивация стратегии ID: {strategy_id}")
            
            # Получаем данные стратегии
            strategy = await self.get_strategy_by_id(strategy_id, decrypt=False)
            if not strategy:
                logger.error(f"❌ Стратегия {strategy_id} не найдена")
                return False
            
            # Деактивируем стратегию
            success = await db.update_strategy_status(strategy_id, is_active=False)
            
            if success:
                logger.info(f"✅ Стратегия '{strategy['name']}' деактивирована")
                await self.notification_service.notify_strategy_deactivated(
                    strategy["name"], 
                    strategy_id
                )
                return True
            
            logger.error(f"❌ Не удалось деактивировать стратегию {strategy_id}")
            return False
            
        except Exception as e:
            error_msg = f"Ошибка деактивации стратегии {strategy_id}: {e}"
            logger.error(f"❌ {error_msg}")
            await self.notification_service.notify_error(error_msg, "STRATEGY_DEACTIVATE")
            return False
    
    async def toggle_strategy_status(self, strategy_id: int) -> bool:
        """
        Переключить статус стратегии (активна/неактивна)
        
        Args:
            strategy_id: ID стратегии
        
        Returns:
            True если успешно переключено
        """
        try:
            strategy = await self.get_strategy_by_id(strategy_id, decrypt=False)
            if not strategy:
                return False
            
            is_currently_active = strategy.get("is_active", False)
            
            if is_currently_active:
                return await self.deactivate_strategy(strategy_id)
            else:
                return await self.activate_strategy(strategy_id)
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения статуса стратегии {strategy_id}: {e}")
            return False

    async def update_strategy(self, strategy_id: int, updates: Dict[str, Any]) -> bool:
        """
        Обновить стратегию (с поддержкой шифрования конфиденциальных полей).
        Обновляет только переданные поля.
        """
        try:
            if not updates:
                return True

            # Конвертируем "обычные" конфиденциальные поля в *_encrypted
            prepared = self._encrypt_sensitive_data(updates)

            success = await db.update_strategy(strategy_id, prepared)
            if not success:
                return False

            logger.info(f"✅ Стратегия {strategy_id} обновлена")
            return True
        except Exception as e:
            error_msg = f"Ошибка обновления стратегии {strategy_id}: {e}"
            logger.error(f"❌ {error_msg}")
            await self.notification_service.notify_error(error_msg, "STRATEGY_UPDATE")
            return False


# Singleton instance
_strategy_manager: Optional[StrategyManagerService] = None


def get_strategy_manager() -> StrategyManagerService:
    """Получить экземпляр менеджера стратегий (Singleton)"""
    global _strategy_manager
    
    if _strategy_manager is None:
        _strategy_manager = StrategyManagerService()
    
    return _strategy_manager
