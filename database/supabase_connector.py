"""
Supabase Database Connector
Модуль для работы с базой данных Supabase
"""
import logging
import asyncio
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from config.settings import settings
import httpx

logger = logging.getLogger(__name__)


class SupabaseConnector:
    """Класс для взаимодействия с Supabase"""
    
    def __init__(self, auto_connect: bool = True):
        self.client: Optional[Client] = None
        self.max_retries = 3
        self.retry_delay = 2  # секунды
        if auto_connect:
            self._connect()

    def _ensure_connected(self):
        """Ленивая инициализация клиента (чтобы импорт модулей не падал без env)."""
        if self.client is None:
            self._connect()
    
    def _validate_credentials(self):
        """Валидация учетных данных Supabase"""
        if not settings.SUPABASE_URL:
            raise ValueError("SUPABASE_URL не установлен")
        
        if not settings.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY не установлен")
        
        # Проверка формата URL
        if not settings.SUPABASE_URL.startswith("https://"):
            raise ValueError("SUPABASE_URL должен начинаться с https://")
        
        # Проверка длины ключа (Service Role Key обычно длинный)
        if len(settings.SUPABASE_KEY) < 100:
            logger.warning(
                "⚠️ ПРЕДУПРЕЖДЕНИЕ: Ключ Supabase слишком короткий! "
                "Убедитесь, что вы используете Service Role Key, а не Anon Key. "
                f"Длина текущего ключа: {len(settings.SUPABASE_KEY)} символов. "
                "Service Role Key обычно 200+ символов."
            )
        
        logger.info(f"🔑 Длина ключа Supabase: {len(settings.SUPABASE_KEY)} символов")
        logger.info(f"🌐 Supabase URL: {settings.SUPABASE_URL}")
    
    def _connect(self):
        """Подключение к Supabase с повторными попытками"""
        self._validate_credentials()
        
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔄 Попытка подключения к Supabase ({attempt}/{self.max_retries})...")
                logger.info(f"📍 URL: {settings.SUPABASE_URL}")
                logger.info(f"🔑 Используется Service Role Key (длина: {len(settings.SUPABASE_KEY)} символов)")
                
                # Создаем клиент с увеличенным таймаутом
                # ВАЖНО: Используем SUPABASE_SERVICE_ROLE_KEY для полного доступа к базе (обход RLS)
                self.client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY,
                    options={
                        "timeout": 30,  # 30 секунд таймаут
                    }
                )
                
                # Проверяем соединение простым запросом
                try:
                    # Пробуем получить данные из таблицы users (если пусто, то пусто)
                    test_response = self.client.table("users").select("telegram_id").limit(1).execute()
                    logger.info("✅ Успешное подключение к Supabase и проверка доступа к таблице 'users'")
                    logger.info("✅ Service Role Key работает корректно (полный доступ к базе)")
                    return
                except Exception as test_error:
                    test_error_str = str(test_error).lower()
                    # Если ошибка связана с API key
                    if "invalid api key" in test_error_str or "jwt" in test_error_str or "unauthorized" in test_error_str:
                        raise ValueError(
                            f"❌ Неверный API ключ! Проверьте SUPABASE_SERVICE_ROLE_KEY в .env файле. "
                            f"Убедитесь, что используете Service Role Key (не Anon Key). "
                            f"Service Role Key должен быть длиной 200+ символов и начинаться с 'eyJ'. "
                            f"Ошибка: {test_error}"
                        )
                    # Если таблица не существует
                    elif "relation" in test_error_str and "does not exist" in test_error_str:
                        logger.error(
                            f"❌ Таблица 'users' не существует! "
                            f"Выполните SQL скрипт из файла supabase_schema.sql для создания всех необходимых таблиц."
                        )
                    raise
                    
            except Exception as e:
                last_error = e
                logger.error(f"❌ Попытка {attempt} не удалась: {e}")
                
                if attempt < self.max_retries:
                    logger.info(f"⏳ Повторная попытка через {self.retry_delay} секунд...")
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error("❌ Все попытки подключения исчерпаны")
        
        # Если дошли сюда, значит все попытки провалились
        raise ConnectionError(
            f"Не удалось подключиться к Supabase после {self.max_retries} попыток. "
            f"Последняя ошибка: {last_error}"
        )
    
    async def _retry_operation(self, operation, *args, **kwargs):
        """Универсальный метод для повторения операций при сетевых ошибках"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return await operation(*args, **kwargs) if asyncio.iscoroutinefunction(operation) else operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Проверяем, является ли это временной сетевой ошибкой
                is_retryable = any(keyword in error_msg for keyword in [
                    "timeout", "connection", "network", "http", "temporary"
                ])
                
                if is_retryable and attempt < self.max_retries:
                    logger.warning(f"⚠️ Временная ошибка при операции (попытка {attempt}/{self.max_retries}): {e}")
                    await asyncio.sleep(self.retry_delay) if asyncio.iscoroutinefunction(operation) else None
                else:
                    raise
        
        raise last_error
    
    # ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================
    
    async def get_all_users(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить список всех пользователей
        Args:
            limit: Ограничение количества записей (None = все)
        """
        try:
            self._ensure_connected()
            query = self.client.table("users").select("*").order("created_at", desc=True)
            if limit:
                query = query.limit(limit)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.error(
                    f"❌ Таблица 'users' не существует в базе данных! "
                    f"Выполните SQL скрипт из файла supabase_schema.sql для создания таблиц. "
                    f"Ошибка: {e}"
                )
            else:
                logger.error(f"Ошибка получения пользователей: {e}")
            return []
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        try:
            self._ensure_connected()
            response = self.client.table("users").select("*").eq("telegram_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None
    
    async def update_user_status(self, user_id: int, is_blocked: bool) -> bool:
        """Блокировка/разблокировка пользователя"""
        try:
            self._ensure_connected()
            self.client.table("users").update({"is_blocked": is_blocked}).eq("telegram_id", user_id).execute()
            status = "заблокирован" if is_blocked else "разблокирован"
            logger.info(f"Пользователь {user_id} {status}")
            return True
        except Exception as e:
            logger.error(f"Ошибка изменения статуса пользователя {user_id}: {e}")
            return False
    
    async def update_user_subscription(
        self, 
        user_id: int, 
        subscription_type: str,
        expires_at: str
    ) -> bool:
        """Обновить подписку пользователя"""
        try:
            self._ensure_connected()
            self.client.table("users").update({
                "subscription_type": subscription_type,
                "subscription_expires_at": expires_at
            }).eq("telegram_id", user_id).execute()
            logger.info(f"Подписка пользователя {user_id} обновлена: {subscription_type} до {expires_at}")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления подписки: {e}")
            return False
    
    # ==================== ТОКЕНЫ ПРИГЛАШЕНИЯ ====================
    
    async def create_invite_token(
        self, 
        token: str,
        max_uses: int = 1,
        subscription_type: str = "trial",
        created_by: int = None
    ) -> bool:
        """Создать токен приглашения"""
        try:
            self._ensure_connected()
            self.client.table("invite_tokens").insert({
                "token": token,
                "max_uses": max_uses,
                "current_uses": 0,
                "subscription_type": subscription_type,
                "created_by": created_by,
                "is_active": True
            }).execute()
            logger.info(f"✅ Токен {token} успешно создан")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.error(
                    f"❌ Таблица 'invite_tokens' не существует в базе данных! "
                    f"Выполните SQL скрипт из файла supabase_schema.sql для создания таблиц. "
                    f"Ошибка: {e}"
                )
            elif "duplicate key" in error_msg or "unique constraint" in error_msg:
                logger.error(f"❌ Токен '{token}' уже существует: {e}")
            else:
                logger.error(f"❌ Ошибка создания токена: {e}")
            return False
    
    async def get_all_tokens(self) -> List[Dict[str, Any]]:
        """Получить все токены"""
        try:
            self._ensure_connected()
            response = self.client.table("invite_tokens").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.error(
                    f"❌ Таблица 'invite_tokens' не существует в базе данных! "
                    f"Выполните SQL скрипт из файла supabase_schema.sql для создания таблиц. "
                    f"Ошибка: {e}"
                )
            else:
                logger.error(f"Ошибка получения токенов: {e}")
            return []
    
    async def deactivate_token(self, token: str) -> bool:
        """Деактивировать токен"""
        try:
            self._ensure_connected()
            self.client.table("invite_tokens").update({"is_active": False}).eq("token", token).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка деактивации токена: {e}")
            return False
    
    # ==================== СТРАТЕГИИ ====================
    
    async def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Получить все стратегии"""
        try:
            self._ensure_connected()
            response = self.client.table("strategies").select("*").order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.error(
                    f"❌ Таблица 'strategies' не существует в базе данных! "
                    f"Выполните SQL скрипт из файла supabase_schema.sql для создания таблиц. "
                    f"Ошибка: {e}"
                )
            else:
                logger.error(f"Ошибка получения стратегий: {e}")
            return []
    
    async def get_active_strategy(self) -> Optional[Dict[str, Any]]:
        """Получить активную стратегию"""
        try:
            self._ensure_connected()
            response = self.client.table("strategies").select("*").eq("is_active", True).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения активной стратегии: {e}")
            return None
    
    async def create_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """Создать новую стратегию"""
        try:
            self._ensure_connected()
            # Деактивируем все предыдущие стратегии
            if strategy_data.get("is_active", False):
                self.client.table("strategies").update({"is_active": False}).neq("id", 0).execute()
            
            # Создаем новую
            self.client.table("strategies").insert(strategy_data).execute()
            logger.info(f"✅ Стратегия '{strategy_data.get('name')}' успешно создана")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "relation" in error_msg and "does not exist" in error_msg:
                logger.error(
                    f"❌ Таблица 'strategies' не существует в базе данных! "
                    f"Выполните SQL скрипт из файла supabase_schema.sql для создания таблиц. "
                    f"Ошибка: {e}"
                )
            elif "duplicate key" in error_msg or "unique constraint" in error_msg:
                logger.error(f"❌ Стратегия с таким именем уже существует: {e}")
            else:
                logger.error(f"❌ Ошибка создания стратегии: {e}")
            return False
    
    async def update_strategy_status(self, strategy_id: int, is_active: bool) -> bool:
        """Обновить статус стратегии"""
        try:
            self._ensure_connected()
            if is_active:
                # Деактивируем все другие
                self.client.table("strategies").update({"is_active": False}).neq("id", strategy_id).execute()
            
            self.client.table("strategies").update({"is_active": is_active}).eq("id", strategy_id).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса стратегии: {e}")
            return False

    async def update_strategy(self, strategy_id: int, updates: Dict[str, Any]) -> bool:
        """Обновить поля стратегии (кроме статуса)."""
        try:
            self._ensure_connected()
            if not updates:
                return True
            self.client.table("strategies").update(updates).eq("id", strategy_id).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления стратегии {strategy_id}: {e}")
            return False
    
    # ==================== ЛОГИ И МОНИТОРИНГ ====================
    
    async def get_system_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить системные логи"""
        try:
            self._ensure_connected()
            response = self.client.table("system_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения логов: {e}")
            return []
    
    async def get_decision_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить логи принятия решений AI"""
        try:
            self._ensure_connected()
            response = self.client.table("decision_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения логов решений: {e}")
            return []
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """Получить общую статистику трейдинга"""
        try:
            self._ensure_connected()
            # Получаем данные о сигналах
            signals = self.client.table("signals").select("*").execute()
            
            # Получаем данные о трейдах
            trades = self.client.table("trades").select("*").execute()
            
            stats = {
                "total_signals": len(signals.data) if signals.data else 0,
                "total_trades": len(trades.data) if trades.data else 0,
                "active_users": len(await self.get_all_users()),
            }
            
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    # ==================== ФИЛЬТРАЦИЯ ДАННЫХ ПО ДАТАМ ====================
    
    async def get_signals_by_date_range(
        self,
        start_date: str,
        end_date: str,
        asset: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить сигналы за период времени
        Args:
            start_date: Начальная дата (ISO формат)
            end_date: Конечная дата (ISO формат)
            asset: Фильтр по активу (опционально)
        """
        try:
            self._ensure_connected()
            query = (
                self.client.table("signals")
                .select("*")
                .gte("created_at", start_date)
                .lte("created_at", end_date)
            )
            
            if asset:
                query = query.eq("asset", asset)
            
            response = query.order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения сигналов за период: {e}")
            return []
    
    async def get_trades_by_date_range(
        self,
        start_date: str,
        end_date: str,
        asset: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить трейды за период времени
        Args:
            start_date: Начальная дата (ISO формат)
            end_date: Конечная дата (ISO формат)
            asset: Фильтр по активу (опционально)
            status: Фильтр по статусу (опционально)
        """
        try:
            self._ensure_connected()
            query = (
                self.client.table("trades")
                .select("*")
                .gte("created_at", start_date)
                .lte("created_at", end_date)
            )
            
            if asset:
                query = query.eq("asset", asset)
            if status:
                query = query.eq("status", status)
            
            response = query.order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения трейдов за период: {e}")
            return []
    
    # ==================== НАСТРОЙКИ БОТА ====================
    
    async def get_bot_settings(self) -> Optional[Dict[str, Any]]:
        """Получить настройки бота"""
        try:
            self._ensure_connected()
            response = self.client.table("bot_settings").select("*").limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return None
    
    async def update_bot_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Обновить настройки бота"""
        try:
            self._ensure_connected()
            # Проверяем, есть ли запись
            existing = await self.get_bot_settings()
            if existing:
                self.client.table("bot_settings").update(settings_data).eq("id", existing["id"]).execute()
            else:
                self.client.table("bot_settings").insert(settings_data).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления настроек: {e}")
            return False

    # ==================== ВНУТРЕННИЕ НАСТРОЙКИ/СЕКРЕТЫ ЯДРА ====================

    async def get_core_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """Получить запись core_settings по ключу."""
        try:
            self._ensure_connected()
            response = self.client.table("core_settings").select("*").eq("key", key).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения core_settings[{key}]: {e}")
            return None

    async def set_core_setting(self, key: str, value_encrypted: str) -> bool:
        """Создать/обновить запись core_settings (value_encrypted)."""
        try:
            self._ensure_connected()
            existing = await self.get_core_setting(key)
            if existing:
                self.client.table("core_settings").update(
                    {"value_encrypted": value_encrypted}
                ).eq("id", existing["id"]).execute()
            else:
                self.client.table("core_settings").insert(
                    {"key": key, "value_encrypted": value_encrypted}
                ).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения core_settings[{key}]: {e}")
            return False


# Singleton
db = SupabaseConnector(auto_connect=False)
