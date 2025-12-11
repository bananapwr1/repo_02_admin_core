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
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.max_retries = 3
        self.retry_delay = 2  # секунды
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
                
                # Создаем клиент с увеличенным таймаутом
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
                    logger.info("✅ Успешное подключение к Supabase и проверка доступа к таблице")
                    return
                except Exception as test_error:
                    # Если ошибка связана с API key
                    if "Invalid API key" in str(test_error) or "JWT" in str(test_error):
                        raise ValueError(
                            f"❌ Неверный API ключ! Проверьте SUPABASE_KEY_FOR_ADMIN в .env файле. "
                            f"Убедитесь, что используете Service Role Key, а не Anon Key. "
                            f"Ошибка: {test_error}"
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
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получить список всех пользователей"""
        try:
            response = self.client.table("users").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        try:
            response = self.client.table("users").select("*").eq("telegram_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None
    
    async def update_user_status(self, user_id: int, is_blocked: bool) -> bool:
        """Блокировка/разблокировка пользователя"""
        try:
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
            self.client.table("invite_tokens").insert({
                "token": token,
                "max_uses": max_uses,
                "current_uses": 0,
                "subscription_type": subscription_type,
                "created_by": created_by,
                "is_active": True
            }).execute()
            logger.info(f"Токен {token} создан")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания токена: {e}")
            return False
    
    async def get_all_tokens(self) -> List[Dict[str, Any]]:
        """Получить все токены"""
        try:
            response = self.client.table("invite_tokens").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения токенов: {e}")
            return []
    
    async def deactivate_token(self, token: str) -> bool:
        """Деактивировать токен"""
        try:
            self.client.table("invite_tokens").update({"is_active": False}).eq("token", token).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка деактивации токена: {e}")
            return False
    
    # ==================== СТРАТЕГИИ ====================
    
    async def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Получить все стратегии"""
        try:
            response = self.client.table("strategies").select("*").order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения стратегий: {e}")
            return []
    
    async def get_active_strategy(self) -> Optional[Dict[str, Any]]:
        """Получить активную стратегию"""
        try:
            response = self.client.table("strategies").select("*").eq("is_active", True).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения активной стратегии: {e}")
            return None
    
    async def create_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """Создать новую стратегию"""
        try:
            # Деактивируем все предыдущие стратегии
            if strategy_data.get("is_active", False):
                self.client.table("strategies").update({"is_active": False}).neq("id", 0).execute()
            
            # Создаем новую
            self.client.table("strategies").insert(strategy_data).execute()
            logger.info(f"Стратегия '{strategy_data.get('name')}' создана")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания стратегии: {e}")
            return False
    
    async def update_strategy_status(self, strategy_id: int, is_active: bool) -> bool:
        """Обновить статус стратегии"""
        try:
            if is_active:
                # Деактивируем все другие
                self.client.table("strategies").update({"is_active": False}).neq("id", strategy_id).execute()
            
            self.client.table("strategies").update({"is_active": is_active}).eq("id", strategy_id).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса стратегии: {e}")
            return False
    
    # ==================== ЛОГИ И МОНИТОРИНГ ====================
    
    async def get_system_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить системные логи"""
        try:
            response = self.client.table("system_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения логов: {e}")
            return []
    
    async def get_decision_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить логи принятия решений AI"""
        try:
            response = self.client.table("decision_logs").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Ошибка получения логов решений: {e}")
            return []
    
    async def get_trading_statistics(self) -> Dict[str, Any]:
        """Получить общую статистику трейдинга"""
        try:
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
    
    # ==================== НАСТРОЙКИ БОТА ====================
    
    async def get_bot_settings(self) -> Optional[Dict[str, Any]]:
        """Получить настройки бота"""
        try:
            response = self.client.table("bot_settings").select("*").limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return None
    
    async def update_bot_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Обновить настройки бота"""
        try:
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


# Singleton
db = SupabaseConnector()
