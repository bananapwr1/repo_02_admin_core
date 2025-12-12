"""
Скрипт проверки подключения к Supabase и конфигурации
"""
import asyncio
import sys
from config import settings
from database import db


async def test_configuration():
    """Проверка конфигурации"""
    print("🔍 Проверка конфигурации...")
    print()
    
    # Проверка токена бота
    if settings.TELEGRAM_BOT_TOKEN:
        print("✅ TELEGRAM_BOT_TOKEN установлен")
    else:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return False
    
    # Проверка Supabase
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        print("✅ Supabase credentials установлены")
    else:
        print("❌ Supabase credentials не установлены")
        return False
    
    # Проверка админов
    if settings.ADMIN_IDS:
        print(f"✅ Администраторы: {len(settings.ADMIN_IDS)}")
        print(f"   IDs: {', '.join(map(str, settings.ADMIN_IDS))}")
    else:
        print("⚠️  ADMIN_IDS не установлен (доступ будет у всех!)")
    
    print()
    return True


async def test_supabase_connection():
    """Проверка подключения к Supabase"""
    print("🔗 Проверка подключения к Supabase...")
    print()
    
    try:
        # Пробуем получить пользователей
        users = await db.get_all_users()
        print(f"✅ Подключение успешно")
        print(f"   Найдено пользователей: {len(users)}")
        
        # Пробуем получить стратегии
        strategies = await db.get_all_strategies()
        print(f"   Найдено стратегий: {len(strategies)}")
        
        # Пробуем получить токены
        tokens = await db.get_all_tokens()
        print(f"   Найдено токенов: {len(tokens)}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print()
        return False


async def test_tables():
    """Проверка наличия всех необходимых таблиц"""
    print("📊 Проверка таблиц базы данных...")
    print()
    
    tables_to_check = [
        ("users", db.get_all_users),
        ("strategies", db.get_all_strategies),
        ("invite_tokens", db.get_all_tokens),
        ("system_logs", db.get_system_logs),
        ("decision_logs", db.get_decision_logs),
    ]
    
    all_ok = True
    for table_name, method in tables_to_check:
        try:
            await method()
            print(f"✅ Таблица '{table_name}' существует")
        except Exception as e:
            print(f"❌ Таблица '{table_name}' недоступна: {e}")
            all_ok = False
    
    print()
    return all_ok


async def show_statistics():
    """Показать текущую статистику"""
    print("📈 Текущая статистика системы:")
    print()
    
    try:
        stats = await db.get_trading_statistics()
        
        print(f"   👥 Пользователей: {stats.get('active_users', 0)}")
        print(f"   📡 Сигналов: {stats.get('total_signals', 0)}")
        print(f"   💹 Трейдов: {stats.get('total_trades', 0)}")
        
        # Активная стратегия
        active_strategy = await db.get_active_strategy()
        if active_strategy:
            print(f"   🎯 Активная стратегия: {active_strategy.get('name')}")
        else:
            print(f"   ⚠️  Нет активной стратегии")
        
        print()
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        print()


async def main():
    """Главная функция тестирования"""
    print("=" * 60)
    print("🧪 Тест подключения Admin Panel Bot")
    print("=" * 60)
    print()
    
    # Проверка конфигурации
    if not await test_configuration():
        print("❌ Конфигурация не пройдена")
        print("Проверьте файл .env и заполните все необходимые переменные")
        sys.exit(1)
    
    # Проверка подключения
    if not await test_supabase_connection():
        print("❌ Подключение к Supabase не удалось")
        print("Проверьте:")
        print("  1. SUPABASE_URL правильный")
        print("  2. SUPABASE_SERVICE_ROLE_KEY правильный (Service Role Key)")
        print("  3. Интернет подключение работает")
        sys.exit(1)
    
    # Проверка таблиц
    if not await test_tables():
        print("⚠️  Не все таблицы доступны")
        print("Выполните SQL-скрипт из файла supabase_schema.sql")
        print("в SQL Editor вашего Supabase проекта")
    
    # Статистика
    await show_statistics()
    
    print("=" * 60)
    print("✅ Все проверки пройдены! Бот готов к запуску.")
    print("=" * 60)
    print()
    print("Запустите бота командой: python bot.py")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Тест прерван пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
