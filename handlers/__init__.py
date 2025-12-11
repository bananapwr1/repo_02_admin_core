"""
Инициализация всех обработчиков
"""
from aiogram import Router
from . import (
    start_handler,
    users_handler,
    strategies_handler,
    tokens_handler,
    logs_handler,
    ai_chat_handler,
    settings_handler
)


def setup_routers() -> Router:
    """Настройка всех роутеров"""
    main_router = Router()
    
    # Регистрируем все роутеры
    main_router.include_router(start_handler.router)
    main_router.include_router(users_handler.router)
    main_router.include_router(strategies_handler.router)
    main_router.include_router(tokens_handler.router)
    main_router.include_router(logs_handler.router)
    main_router.include_router(ai_chat_handler.router)
    main_router.include_router(settings_handler.router)
    
    return main_router


__all__ = ["setup_routers"]
