# 📚 Примеры Использования Admin Core

## 🎯 Обзор

Этот документ содержит практические примеры использования новой функциональности Admin Core.

---

## 1️⃣ Генерация Ключа Шифрования

### Метод 1: Через Python
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Метод 2: Через скрипт
```python
from cryptography.fernet import Fernet

# Генерируем ключ
key = Fernet.generate_key()
print(f"Ваш ключ шифрования:\n{key.decode()}")

# Сохраните этот ключ в .env файл
# ENCRYPTION_KEY=полученный_ключ
```

---

## 2️⃣ Использование Сервиса Уведомлений

### Базовое использование

```python
from services import get_notification_service
from aiogram import Bot

# Создаем бота
bot = Bot(token="YOUR_BOT_TOKEN")

# Получаем сервис уведомлений
notification_service = get_notification_service(bot)

# Отправка различных типов уведомлений

# INFO - Информационное сообщение
await notification_service.send_notification(
    "Система работает нормально",
    level="INFO"
)

# WARNING - Предупреждение
await notification_service.send_notification(
    "Обнаружена аномальная активность",
    level="WARNING"
)

# ERROR - Ошибка
await notification_service.send_notification(
    "Ошибка выполнения операции",
    level="ERROR"
)

# CRITICAL - Критическая ошибка
await notification_service.send_notification(
    "Критическая ошибка системы!",
    level="CRITICAL"
)
```

### Специальные уведомления

```python
# Уведомление о запуске
await notification_service.notify_startup()

# Уведомление об остановке
await notification_service.notify_shutdown()

# Уведомление об ошибке БД
await notification_service.notify_database_error(
    "Connection timeout to Supabase"
)

# Уведомление об ошибке шифрования
await notification_service.notify_encryption_error(
    "Invalid encryption key"
)

# Уведомление о создании стратегии
await notification_service.notify_strategy_created(
    strategy_name="My Strategy",
    strategy_id=123
)

# Уведомление об активации стратегии
await notification_service.notify_strategy_activated(
    strategy_name="My Strategy",
    strategy_id=123
)

# Уведомление о деактивации стратегии
await notification_service.notify_strategy_deactivated(
    strategy_name="My Strategy",
    strategy_id=123
)
```

---

## 3️⃣ Работа с Шифрованием

### Базовое шифрование

```python
from services.strategy_manager_service import EncryptionService

# Создаем сервис
encryption = EncryptionService()

# Проверяем доступность
if not encryption.is_available():
    print("Шифрование недоступно. Проверьте ENCRYPTION_KEY")
    exit(1)

# Шифруем строку
api_key = "my_secret_binance_api_key"
encrypted_api_key = encryption.encrypt(api_key)
print(f"Зашифровано: {encrypted_api_key}")

# Расшифровываем
decrypted_api_key = encryption.decrypt(encrypted_api_key)
print(f"Расшифровано: {decrypted_api_key}")
```

### Шифрование JSON

```python
# Шифруем словарь
credentials = {
    "exchange": "binance",
    "api_key": "abc123",
    "secret_key": "xyz789",
    "permissions": ["read", "trade"]
}

encrypted_json = encryption.encrypt_json(credentials)
print(f"JSON зашифрован: {encrypted_json[:50]}...")

# Расшифровываем
decrypted_credentials = encryption.decrypt_json(encrypted_json)
print(f"API Key: {decrypted_credentials['api_key']}")
```

---

## 4️⃣ Управление Стратегиями

### Создание простой стратегии

```python
from services import get_strategy_manager

# Получаем менеджер
strategy_manager = get_strategy_manager()

# Создаем стратегию
strategy_id = await strategy_manager.create_strategy(
    name="Simple RSI Strategy",
    description="Buy when RSI < 30, Sell when RSI > 70",
    is_active=False,
    assets_to_monitor=["BTC/USDT"],
    timeframe="1h",
    indicators={
        "rsi": {
            "period": 14
        }
    },
    entry_rules={
        "rsi_below": 30
    },
    exit_rules={
        "rsi_above": 70
    },
    risk_management={
        "max_loss_percent": 2.0
    }
)

print(f"Стратегия создана с ID: {strategy_id}")
```

### Создание стратегии с конфиденциальными данными

```python
# Создаем стратегию с API ключами (они будут зашифрованы)
strategy_id = await strategy_manager.create_strategy(
    name="Binance Trading Bot",
    description="Automated trading on Binance",
    is_active=True,
    assets_to_monitor=["BTC/USDT", "ETH/USDT"],
    timeframe="4h",
    indicators={
        "rsi": {"period": 14},
        "macd": {"fast": 12, "slow": 26, "signal": 9}
    },
    entry_rules={
        "rsi_below": 30,
        "macd_cross": "bullish"
    },
    exit_rules={
        "rsi_above": 70,
        "macd_cross": "bearish"
    },
    risk_management={
        "max_loss_percent": 2.0,
        "take_profit_percent": 5.0,
        "stop_loss_percent": 1.5
    },
    # Конфиденциальные данные (автоматически шифруются)
    api_keys={
        "binance": "your_binance_api_key"
    },
    secret_keys={
        "binance": "your_binance_secret_key"
    },
    private_params={
        "max_position_size": 1000,
        "leverage": 3,
        "trading_fee": 0.1
    }
)

print(f"Стратегия с шифрованием создана: {strategy_id}")
```

### Получение стратегий

```python
# Получить все стратегии (с расшифровкой)
all_strategies = await strategy_manager.get_all_strategies(decrypt=True)
print(f"Всего стратегий: {len(all_strategies)}")

for strategy in all_strategies:
    print(f"- {strategy['name']} (ID: {strategy['id']}, Активна: {strategy['is_active']})")

# Получить только активные стратегии
active_strategies = await strategy_manager.get_active_strategies()
print(f"Активных стратегий: {len(active_strategies)}")

# Получить конкретную стратегию
strategy = await strategy_manager.get_strategy_by_id(123, decrypt=True)
if strategy:
    print(f"Найдена стратегия: {strategy['name']}")
    
    # Доступ к расшифрованным данным
    if "api_keys" in strategy:
        print(f"API Keys: {strategy['api_keys']}")
```

### Активация и деактивация

```python
# Активировать стратегию
success = await strategy_manager.activate_strategy(123)
if success:
    print("✅ Стратегия активирована")
    # Автоматически отправлено уведомление администратору

# Деактивировать стратегию
success = await strategy_manager.deactivate_strategy(123)
if success:
    print("✅ Стратегия деактивирована")
    # Автоматически отправлено уведомление администратору

# Переключить статус (toggle)
success = await strategy_manager.toggle_strategy_status(123)
```

---

## 5️⃣ Интеграция в Telegram Handler

### Пример handler для создания стратегии

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services import get_strategy_manager

router = Router()

# Состояния для FSM
class StrategyCreation(StatesGroup):
    name = State()
    description = State()
    assets = State()
    # ... другие состояния

@router.message(F.text == "➕ Создать стратегию")
async def start_strategy_creation(message: Message, state: FSMContext):
    """Начало создания стратегии"""
    await message.answer(
        "📊 Создание новой стратегии\n\n"
        "Введите название стратегии:"
    )
    await state.set_state(StrategyCreation.name)

@router.message(StrategyCreation.name)
async def process_strategy_name(message: Message, state: FSMContext):
    """Обработка названия стратегии"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "Введите описание стратегии:"
    )
    await state.set_state(StrategyCreation.description)

# ... остальные состояния ...

@router.message(StrategyCreation.final_confirm)
async def create_strategy_final(message: Message, state: FSMContext):
    """Финальное создание стратегии"""
    if message.text.lower() != "подтвердить":
        await state.clear()
        await message.answer("❌ Создание стратегии отменено")
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    # Создаем стратегию
    strategy_manager = get_strategy_manager()
    
    strategy_id = await strategy_manager.create_strategy(
        name=data['name'],
        description=data['description'],
        assets_to_monitor=data['assets'],
        # ... другие параметры
    )
    
    if strategy_id:
        await message.answer(
            f"✅ Стратегия успешно создана!\n\n"
            f"🆔 ID: {strategy_id}\n"
            f"📊 Название: {data['name']}\n\n"
            f"Стратегия автоматически сохранена в базе данных.\n"
            f"Конфиденциальные данные зашифрованы."
        )
    else:
        await message.answer("❌ Ошибка создания стратегии")
    
    await state.clear()
```

### Пример handler для управления стратегиями

```python
@router.callback_query(F.data.startswith("strategy_activate_"))
async def activate_strategy_callback(callback: CallbackQuery):
    """Активация стратегии"""
    strategy_id = int(callback.data.split("_")[-1])
    
    strategy_manager = get_strategy_manager()
    success = await strategy_manager.activate_strategy(strategy_id)
    
    if success:
        await callback.answer("✅ Стратегия активирована", show_alert=True)
        # Уведомление автоматически отправлено администратору
    else:
        await callback.answer("❌ Ошибка активации", show_alert=True)

@router.callback_query(F.data.startswith("strategy_deactivate_"))
async def deactivate_strategy_callback(callback: CallbackQuery):
    """Деактивация стратегии"""
    strategy_id = int(callback.data.split("_")[-1])
    
    strategy_manager = get_strategy_manager()
    success = await strategy_manager.deactivate_strategy(strategy_id)
    
    if success:
        await callback.answer("⏸️ Стратегия деактивирована", show_alert=True)
    else:
        await callback.answer("❌ Ошибка деактивации", show_alert=True)

@router.message(F.text == "📊 Список стратегий")
async def list_strategies(message: Message):
    """Список всех стратегий"""
    strategy_manager = get_strategy_manager()
    strategies = await strategy_manager.get_all_strategies(decrypt=False)
    
    if not strategies:
        await message.answer("📭 Стратегий пока нет")
        return
    
    text = "📊 <b>Список стратегий:</b>\n\n"
    
    for strategy in strategies:
        status = "🟢 Активна" if strategy['is_active'] else "⚪️ Неактивна"
        text += f"🆔 {strategy['id']} | {status}\n"
        text += f"📌 {strategy['name']}\n"
        text += f"📝 {strategy['description']}\n"
        text += f"🎯 Активы: {', '.join(strategy['assets_to_monitor'])}\n"
        text += "─" * 30 + "\n"
    
    await message.answer(text)
```

---

## 6️⃣ Проверка Работоспособности

### Тестовый скрипт

```bash
# Запустите тестовый скрипт
python test_admin_core_features.py
```

Этот скрипт проверит:
- ✅ Шифрование/расшифровку
- ✅ Создание стратегий
- ✅ Активацию/деактивацию
- ✅ Систему уведомлений

### Ручная проверка

```python
import asyncio
from services import get_strategy_manager, get_notification_service
from aiogram import Bot

async def test():
    # Тест менеджера стратегий
    manager = get_strategy_manager()
    
    # Создаем тестовую стратегию
    strategy_id = await manager.create_strategy(
        name="Test Strategy",
        description="Test",
        is_active=False,
        assets_to_monitor=["BTC/USDT"]
    )
    print(f"Создана стратегия: {strategy_id}")
    
    # Тест уведомлений
    bot = Bot(token="YOUR_TOKEN")
    notifier = get_notification_service(bot)
    
    await notifier.send_notification(
        "Тестовое уведомление",
        level="INFO"
    )
    print("Уведомление отправлено")

# Запуск
asyncio.run(test())
```

---

## 7️⃣ Лучшие Практики

### ✅ DO (Делайте)

1. **Всегда шифруйте конфиденциальные данные:**
   ```python
   # Правильно
   strategy_id = await strategy_manager.create_strategy(
       name="My Strategy",
       api_keys={"binance": "secret_key"}  # Автоматически зашифруется
   )
   ```

2. **Используйте расшифровку только когда нужно:**
   ```python
   # Для отображения списка - не нужна расшифровка
   strategies = await strategy_manager.get_all_strategies(decrypt=False)
   
   # Для использования API keys - нужна расшифровка
   strategy = await strategy_manager.get_strategy_by_id(123, decrypt=True)
   api_key = strategy['api_keys']['binance']
   ```

3. **Обрабатывайте ошибки:**
   ```python
   try:
       strategy_id = await strategy_manager.create_strategy(...)
       if not strategy_id:
           logger.error("Не удалось создать стратегию")
   except Exception as e:
       logger.error(f"Ошибка: {e}")
       await notifier.notify_error(str(e), "STRATEGY_CREATE")
   ```

### ❌ DON'T (Не делайте)

1. **Не храните расшифрованные ключи в логах:**
   ```python
   # Неправильно
   logger.info(f"API Key: {strategy['api_keys']}")  # ❌
   
   # Правильно
   logger.info(f"Стратегия загружена: {strategy['name']}")  # ✅
   ```

2. **Не передавайте Service Role Key в UI:**
   ```python
   # В Admin Core - правильно
   SUPABASE_KEY = settings.SUPABASE_KEY  # Service Role Key ✅
   
   # В UI Bot - используйте ограниченный ключ
   SUPABASE_KEY = settings.NEXT_PUBLIC_SUPABASE_KEY  # Anon Key ✅
   ```

3. **Не забывайте про уведомления:**
   ```python
   # После важных операций
   await strategy_manager.activate_strategy(123)
   # Уведомление отправляется автоматически ✅
   ```

---

## 📝 Заключение

Эти примеры демонстрируют основные сценарии использования новой функциональности Admin Core. 

Для более подробной информации см.:
- `ADMIN_CORE_IMPLEMENTATION.md` - Полная документация
- `test_admin_core_features.py` - Тестовый скрипт
- `services/strategy_manager_service.py` - Исходный код

**Дата:** 11 декабря 2025  
**Версия:** 1.0
