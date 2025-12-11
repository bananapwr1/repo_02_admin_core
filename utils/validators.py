"""
Валидаторы для проверки данных
"""
import re
from typing import Optional


def validate_telegram_id(telegram_id: str) -> Optional[int]:
    """Проверка корректности Telegram ID"""
    try:
        tid = int(telegram_id)
        if tid > 0:
            return tid
    except ValueError:
        pass
    return None


def validate_subscription_type(sub_type: str) -> bool:
    """Проверка типа подписки"""
    valid_types = ['trial', 'vip', 'long', 'short', 'long_short', 'free']
    return sub_type.lower() in valid_types


def validate_token(token: str) -> bool:
    """Проверка формата токена"""
    # Токен должен содержать только буквы, цифры, дефисы
    pattern = r'^[A-Za-z0-9\-_]{8,64}$'
    return bool(re.match(pattern, token))


def validate_strategy_name(name: str) -> bool:
    """Проверка имени стратегии"""
    return len(name) >= 3 and len(name) <= 100


def validate_assets_list(assets: list) -> bool:
    """Проверка списка активов"""
    if not assets or not isinstance(assets, list):
        return False
    
    for asset in assets:
        if not isinstance(asset, str) or len(asset) < 3:
            return False
    
    return True


def validate_timeframe(timeframe: str) -> bool:
    """Проверка таймфрейма"""
    valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    return timeframe in valid_timeframes


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Очистка пользовательского ввода"""
    # Удаляем опасные символы
    text = text.strip()
    
    # Ограничиваем длину
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def is_valid_email(email: str) -> bool:
    """Проверка email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
