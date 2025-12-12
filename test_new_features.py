"""
Тестирование новых возможностей Admin Core 2.0
Проверка всех сервисов и функций
"""
import asyncio
import sys
from datetime import datetime, timedelta

from config import settings
from database import db
from services.data_aggregation_service import aggregation_service
from services.strategy_templates_service import strategy_templates_service
from services.dynamic_strategy_switcher import dynamic_switcher


def print_section(title: str):
    """Красивый вывод секции"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_connection():
    """Тест 1: Проверка подключения к Supabase"""
    print_section("ТЕСТ 1: Подключение к Supabase")
    
    try:
        # Проверяем наличие ключа
        key_length = len(settings.SUPABASE_KEY)
        print(f"✓ Переменная SUPABASE_SERVICE_KEY (или SUPABASE_KEY) загружена")
        print(f"  Длина ключа: {key_length} символов")
        
        if key_length < 100:
            print(f"  ⚠️ ВНИМАНИЕ: Ключ слишком короткий! Используйте Service Role Key.")
            return False
        else:
            print(f"  ✓ Длина ключа соответствует Service Role Key")
        
        # Проверяем подключение
        users = await db.get_all_users(limit=1)
        print(f"✓ Подключение к Supabase успешно")
        print(f"  Тестовый запрос к таблице users выполнен")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка подключения: {e}")
        return False


async def test_data_aggregation():
    """Тест 2: Сервис агрегации данных"""
    print_section("ТЕСТ 2: Data Aggregation Service")
    
    try:
        # Тест 1: Рыночные условия
        print("\n📊 Получение рыночных условий...")
        conditions = await aggregation_service.get_market_conditions()
        
        print(f"✓ Рыночные условия получены:")
        print(f"  • Волатильность: {conditions.overall_volatility}")
        print(f"  • Тренд: {conditions.market_trend}")
        print(f"  • Сессия: {conditions.time_of_day}")
        print(f"  • Пиковые часы: {'Да' if conditions.is_peak_hours else 'Нет'}")
        print(f"  • Рекомендуемая стратегия: {conditions.recommended_strategy_type}")
        
        # Тест 2: Статистика по активу
        print("\n📈 Получение статистики по активу BTCUSDT...")
        stats = await aggregation_service.get_asset_statistics("BTCUSDT", period="daily")
        
        print(f"✓ Статистика получена:")
        print(f"  • Период: {stats.period}")
        print(f"  • Всего сигналов: {stats.total_signals}")
        print(f"  • Всего трейдов: {stats.total_trades}")
        print(f"  • Винрейт: {stats.win_rate:.1%}")
        print(f"  • Чистая прибыль: {stats.net_profit:.2f}")
        print(f"  • Качество данных: {stats.data_quality_score:.0%}")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


async def test_strategy_templates():
    """Тест 3: Шаблоны стратегий"""
    print_section("ТЕСТ 3: Strategy Templates Service")
    
    try:
        # Список доступных шаблонов
        templates = strategy_templates_service.list_template_names()
        print(f"\n✓ Загружено шаблонов: {len(templates)}")
        
        for name in templates:
            template = strategy_templates_service.get_template(name)
            print(f"\n  📋 {template.name}")
            print(f"     Тип: {template.strategy_type.value}")
            print(f"     Таймфрейм: {template.timeframe.value}")
            print(f"     Активы: {', '.join(template.assets)}")
            print(f"     Индикаторов: {len(template.indicators)}")
            print(f"     Stop Loss: {template.risk_management.stop_loss_percent}%")
            print(f"     Take Profit: {template.risk_management.take_profit_percent}%")
        
        # Тест рекомендации
        print("\n🎯 Тест рекомендации стратегии...")
        conditions = await aggregation_service.get_market_conditions()
        recommended = await strategy_templates_service.recommend_template(
            conditions.__dict__ if hasattr(conditions, '__dict__') else {}
        )
        
        print(f"✓ Рекомендация: {recommended}")
        print(f"  На основе условий:")
        print(f"  • Волатильность: {conditions.overall_volatility}")
        print(f"  • Тренд: {conditions.market_trend}")
        print(f"  • Время: {conditions.time_of_day}")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


async def test_dynamic_switcher():
    """Тест 4: Динамическое переключение"""
    print_section("ТЕСТ 4: Dynamic Strategy Switcher")
    
    try:
        # Получаем статус
        status = await dynamic_switcher.get_status_report()
        
        print(f"\n✓ Статус переключателя:")
        print(f"  • Активен: {'Да' if status['is_running'] else 'Нет'}")
        print(f"  • Текущая стратегия: {status['current_strategy'] or 'Не установлена'}")
        print(f"  • Время работы: {status['uptime_hours']:.2f} часов")
        print(f"  • Всего переключений: {status['total_switches']}")
        print(f"  • Проверка через: {status['next_check_in']} секунд")
        
        print(f"\n📈 Рыночные условия:")
        mc = status['market_conditions']
        print(f"  • Волатильность: {mc['volatility']}")
        print(f"  • Тренд: {mc['trend']}")
        print(f"  • Сессия: {mc['session']}")
        print(f"  • Пик: {'Да' if mc['is_peak'] else 'Нет'}")
        
        if status['recent_switches']:
            print(f"\n🔄 Последние переключения:")
            for switch in status['recent_switches'][:3]:
                print(f"  • {switch['from']} → {switch['to']}")
                print(f"    Причина: {switch['reason']}, Уверенность: {switch['confidence']:.0%}")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


async def test_database_queries():
    """Тест 5: Оптимизированные запросы к БД"""
    print_section("ТЕСТ 5: Database Queries Optimization")
    
    try:
        # Тест получения данных с фильтрацией
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n📅 Запрос данных за период:")
        print(f"   {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        
        # Сигналы
        signals = await db.get_signals_by_date_range(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        print(f"\n✓ Сигналы за неделю: {len(signals)}")
        
        # Трейды
        trades = await db.get_trades_by_date_range(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        print(f"✓ Трейды за неделю: {len(trades)}")
        
        # Пользователи с лимитом
        users = await db.get_all_users(limit=10)
        print(f"✓ Пользователи (лимит 10): {len(users)}")
        
        # Стратегии
        strategies = await db.get_all_strategies()
        print(f"✓ Всего стратегий: {len(strategies)}")
        
        active_strategy = await db.get_active_strategy()
        if active_strategy:
            print(f"✓ Активная стратегия: {active_strategy['name']}")
        else:
            print(f"⚠️ Нет активной стратегии")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


async def run_all_tests():
    """Запуск всех тестов"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "🧪 ТЕСТИРОВАНИЕ ADMIN CORE 2.0" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    
    results = []
    
    # Тест 1: Подключение (критический)
    test1 = await test_connection()
    results.append(("Подключение к Supabase", test1))
    
    if not test1:
        print("\n❌ Критический тест не пройден! Остановка тестирования.")
        print("\n💡 Запустите диагностику: python3 diagnose_connection.py")
        return False
    
    # Тест 2: Агрегация данных
    test2 = await test_data_aggregation()
    results.append(("Data Aggregation Service", test2))
    
    # Тест 3: Шаблоны стратегий
    test3 = await test_strategy_templates()
    results.append(("Strategy Templates", test3))
    
    # Тест 4: Динамическое переключение
    test4 = await test_dynamic_switcher()
    results.append(("Dynamic Switcher", test4))

    # Тест 5: Оптимизированные запросы
    test5 = await test_database_queries()
    results.append(("Database Queries", test5))
    
    # Итоговый отчет
    print_section("ИТОГОВЫЙ ОТЧЕТ")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nРезультаты тестирования:\n")
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print(f"\n{'=' * 70}")
    print(f"  Пройдено: {passed}/{total} тестов ({passed/total*100:.0f}%)")
    print(f"{'=' * 70}\n")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Admin Core 2.0 готов к работе\n")
        return True
    else:
        print("⚠️ Некоторые тесты провалились")
        print("🔧 Проверьте логи и исправьте проблемы\n")
        return False


async def main():
    """Главная функция"""
    try:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
