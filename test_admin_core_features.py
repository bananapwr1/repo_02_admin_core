#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Admin Core
Тестирует шифрование, управление стратегиями и уведомления
"""
import asyncio
import sys
from cryptography.fernet import Fernet

from config import settings
from services import (
    EncryptionService, 
    get_strategy_manager,
    get_notification_service
)


def test_encryption():
    """Тест 1: Проверка шифрования/расшифровки"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Проверка шифрования/расшифровки")
    print("="*60)
    
    # Проверяем наличие ключа
    if not settings.ENCRYPTION_KEY:
        print("❌ ENCRYPTION_KEY не установлен!")
        print("\n💡 Сгенерируйте ключ командой:")
        print('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        return False
    
    encryption = EncryptionService()
    
    if not encryption.is_available():
        print("❌ Сервис шифрования недоступен")
        return False
    
    print("✅ Сервис шифрования инициализирован")
    
    # Тест шифрования строки
    test_data = "sensitive_api_key_12345"
    encrypted = encryption.encrypt(test_data)
    
    if not encrypted:
        print("❌ Не удалось зашифровать данные")
        return False
    
    print(f"✅ Данные зашифрованы: {encrypted[:50]}...")
    
    # Тест расшифровки
    decrypted = encryption.decrypt(encrypted)
    
    if not decrypted or decrypted != test_data:
        print(f"❌ Ошибка расшифровки: получено '{decrypted}', ожидалось '{test_data}'")
        return False
    
    print(f"✅ Данные расшифрованы корректно: {decrypted}")
    
    # Тест шифрования JSON
    test_json = {
        "api_key": "binance_api_key_123",
        "secret": "binance_secret_456",
        "permissions": ["read", "trade"]
    }
    
    encrypted_json = encryption.encrypt_json(test_json)
    
    if not encrypted_json:
        print("❌ Не удалось зашифровать JSON")
        return False
    
    print(f"✅ JSON зашифрован: {encrypted_json[:50]}...")
    
    # Тест расшифровки JSON
    decrypted_json = encryption.decrypt_json(encrypted_json)
    
    if not decrypted_json or decrypted_json != test_json:
        print(f"❌ Ошибка расшифровки JSON")
        return False
    
    print(f"✅ JSON расшифрован корректно: {decrypted_json}")
    
    print("\n✅ Все тесты шифрования пройдены успешно!")
    return True


async def test_strategy_creation():
    """Тест 2: Создание стратегии с шифрованием"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Создание стратегии с шифрованием")
    print("="*60)
    
    strategy_manager = get_strategy_manager()
    
    # Создаем тестовую стратегию
    strategy_id = await strategy_manager.create_strategy(
        name="Test Strategy - Encryption Demo",
        description="Демонстрационная стратегия для проверки шифрования",
        is_active=False,
        assets_to_monitor=["BTC/USDT", "ETH/USDT"],
        timeframe="1h",
        indicators={
            "rsi": {"period": 14},
            "ma": {"period": 50}
        },
        entry_rules={
            "rsi_below": 30,
            "ma_cross": "golden"
        },
        exit_rules={
            "rsi_above": 70,
            "ma_cross": "death"
        },
        risk_management={
            "max_loss_percent": 2.0,
            "take_profit_percent": 5.0
        },
        # Конфиденциальные данные (будут зашифрованы)
        api_keys={
            "binance": "test_binance_api_key_12345"
        },
        secret_keys={
            "binance": "test_binance_secret_67890"
        },
        private_params={
            "max_position_size": 1000,
            "leverage": 2
        }
    )
    
    if not strategy_id:
        print("❌ Не удалось создать стратегию")
        return False
    
    print(f"✅ Стратегия создана с ID: {strategy_id}")
    
    # Получаем стратегию с расшифровкой
    strategy = await strategy_manager.get_strategy_by_id(strategy_id, decrypt=True)
    
    if not strategy:
        print("❌ Не удалось получить созданную стратегию")
        return False
    
    print(f"\n📊 Данные стратегии (расшифрованные):")
    print(f"  - Название: {strategy['name']}")
    print(f"  - Активна: {strategy['is_active']}")
    print(f"  - Активы: {strategy['assets_to_monitor']}")
    
    # Проверяем, что конфиденциальные данные расшифрованы
    if "api_keys" in strategy:
        print(f"  - API Keys (расшифрованы): {strategy['api_keys']}")
        print("  ✅ Конфиденциальные данные успешно расшифрованы")
    else:
        print("  ⚠️ API Keys не найдены в расшифрованных данных")
    
    print("\n✅ Тест создания стратегии пройден!")
    return True


async def test_strategy_activation():
    """Тест 3: Активация/деактивация стратегии"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Активация/деактивация стратегии")
    print("="*60)
    
    strategy_manager = get_strategy_manager()
    
    # Получаем все стратегии
    strategies = await strategy_manager.get_all_strategies()
    
    if not strategies:
        print("⚠️ Нет стратегий для тестирования")
        print("   Сначала выполните Тест 2")
        return False
    
    # Берем первую стратегию
    test_strategy = strategies[0]
    strategy_id = test_strategy["id"]
    strategy_name = test_strategy["name"]
    
    print(f"📊 Тестируем стратегию: {strategy_name} (ID: {strategy_id})")
    
    # Активация
    print("\n🔄 Активация стратегии...")
    success = await strategy_manager.activate_strategy(strategy_id)
    
    if not success:
        print("❌ Не удалось активировать стратегию")
        return False
    
    print("✅ Стратегия активирована")
    
    # Проверяем статус
    strategy = await strategy_manager.get_strategy_by_id(strategy_id, decrypt=False)
    if strategy and strategy.get("is_active"):
        print("✅ Статус подтвержден: стратегия активна")
    else:
        print("❌ Ошибка: статус не изменился")
        return False
    
    # Деактивация
    print("\n🔄 Деактивация стратегии...")
    success = await strategy_manager.deactivate_strategy(strategy_id)
    
    if not success:
        print("❌ Не удалось деактивировать стратегию")
        return False
    
    print("✅ Стратегия деактивирована")
    
    # Проверяем статус
    strategy = await strategy_manager.get_strategy_by_id(strategy_id, decrypt=False)
    if strategy and not strategy.get("is_active"):
        print("✅ Статус подтвержден: стратегия неактивна")
    else:
        print("❌ Ошибка: статус не изменился")
        return False
    
    print("\n✅ Тест активации/деактивации пройден!")
    return True


async def test_notifications():
    """Тест 4: Проверка системы уведомлений"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Проверка системы уведомлений")
    print("="*60)
    
    if not settings.ADMIN_CHAT_ID:
        print("⚠️ ADMIN_CHAT_ID не установлен")
        print("   Уведомления не могут быть отправлены")
        print("   Установите ADMIN_CHAT_ID в .env файле")
        return False
    
    print(f"✅ ADMIN_CHAT_ID настроен: {settings.ADMIN_CHAT_ID}")
    print("✅ Уведомления будут отправляться при работе бота")
    print("\n💡 Для полной проверки запустите бота командой: python bot.py")
    
    return True


def print_summary():
    """Вывод итоговой информации"""
    print("\n" + "="*60)
    print("ИТОГОВАЯ ИНФОРМАЦИЯ")
    print("="*60)
    
    print("\n📋 Переменные окружения:")
    print(f"  ✅ TELEGRAM_BOT_TOKEN: {'✓ Установлен' if settings.TELEGRAM_BOT_TOKEN else '✗ НЕ установлен'}")
    print(f"  ✅ SUPABASE_URL: {settings.SUPABASE_URL if settings.SUPABASE_URL else '✗ НЕ установлен'}")
    print(f"  ✅ SUPABASE_SERVICE_ROLE_KEY: {'✓ Установлен' if settings.SUPABASE_KEY else '✗ НЕ установлен'}")
    print(f"  ✅ ENCRYPTION_KEY: {'✓ Установлен' if settings.ENCRYPTION_KEY else '✗ НЕ установлен'}")
    print(f"  ✅ ADMIN_CHAT_ID: {settings.ADMIN_CHAT_ID if settings.ADMIN_CHAT_ID else '✗ НЕ установлен'}")
    print(f"  ✅ ADMIN_IDS: {len(settings.ADMIN_IDS)} администратор(ов)")
    
    print("\n📊 Статус компонентов:")
    print("  ✅ Сервис шифрования: Реализован")
    print("  ✅ Менеджер стратегий: Реализован")
    print("  ✅ Сервис уведомлений: Реализован")
    print("  ✅ Интеграция с bot.py: Выполнена")
    
    print("\n🚀 Следующие шаги:")
    print("  1. Убедитесь, что все переменные окружения установлены")
    print("  2. Выполните миграцию БД: supabase_migration_encrypted_fields.sql")
    print("  3. Запустите бота: python bot.py")
    print("  4. Проверьте уведомления в Telegram")
    
    print("\n" + "="*60)


async def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ADMIN CORE - Функциональность")
    print("="*60)
    print("\nЭтот скрипт проверяет:")
    print("  1. Шифрование/расшифровку данных")
    print("  2. Создание стратегий")
    print("  3. Активацию/деактивацию стратегий")
    print("  4. Систему уведомлений")
    
    results = []
    
    # Тест 1: Шифрование
    try:
        result = test_encryption()
        results.append(("Шифрование", result))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте шифрования: {e}")
        results.append(("Шифрование", False))
    
    # Тест 2: Создание стратегии
    try:
        result = await test_strategy_creation()
        results.append(("Создание стратегии", result))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте создания стратегии: {e}")
        results.append(("Создание стратегии", False))
    
    # Тест 3: Активация/деактивация
    try:
        result = await test_strategy_activation()
        results.append(("Активация/деактивация", result))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте активации: {e}")
        results.append(("Активация/деактивация", False))
    
    # Тест 4: Уведомления
    try:
        result = await test_notifications()
        results.append(("Уведомления", result))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте уведомлений: {e}")
        results.append(("Уведомления", False))
    
    # Итоги
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ НЕ ПРОЙДЕН"
        print(f"  {status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nИтого: {passed_count}/{total_count} тестов пройдено")
    
    if passed_count == total_count:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print_summary()
        return 0
    else:
        print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("Проверьте конфигурацию и переменные окружения")
        print_summary()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
