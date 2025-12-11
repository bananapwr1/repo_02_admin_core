"""
Supabase Database Connector
Модуль для работы с базой данных Supabase
"""
import logging
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from config.settings import settings

logger = logging.getLogger(__name__)


class SupabaseConnector:
    """Класс для взаимодействия с Supabase"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._connect()
    
    def _connect(self):
        """Подключение к Supabase"""
        try:
            self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("✅ Успешное подключение к Supabase")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Supabase: {e}")
            raise
    
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
