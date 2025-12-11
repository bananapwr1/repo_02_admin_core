"""
Services для Admin Core
Управление стратегиями, уведомлениями и AI-функционалом
"""

from .ai_strategy_service import ai_service
from .notification_service import NotificationService, get_notification_service
from .strategy_manager_service import (
    StrategyManagerService,
    EncryptionService,
    get_strategy_manager
)
from .core_settings_service import CoreSettingsService, get_core_settings_service

__all__ = [
    # AI Services
    "ai_service",
    
    # Сервис уведомлений
    "NotificationService",
    "get_notification_service",
    
    # Сервис управления стратегиями
    "StrategyManagerService",
    "EncryptionService",
    "get_strategy_manager",
    
    # Внутренние настройки/секреты Ядра
    "CoreSettingsService",
    "get_core_settings_service",
]
