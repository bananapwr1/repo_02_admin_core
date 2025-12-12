"""
Расширенная диагностика подключения к Supabase
Этот скрипт проверяет все аспекты подключения и помогает выявить проблемы
"""
import asyncio
import sys
import os
import httpx
from config import settings


async def test_network_connectivity():
    """Проверка базовой сетевой связности"""
    print("=" * 70)
    print("🌐 ПРОВЕРКА СЕТЕВОЙ СВЯЗНОСТИ")
    print("=" * 70)
    
    # Проверка интернет-соединения
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://www.google.com")
            if response.status_code == 200:
                print("✅ Интернет-соединение работает")
            else:
                print(f"⚠️ Необычный код ответа от Google: {response.status_code}")
    except Exception as e:
        print(f"❌ Нет интернет-соединения: {e}")
        return False
    
    # Проверка доступности Supabase
    if not settings.SUPABASE_URL:
        print("❌ SUPABASE_BASE_URL не установлен")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.SUPABASE_URL)
            print(f"✅ Supabase URL доступен (код: {response.status_code})")
    except Exception as e:
        print(f"❌ Supabase URL недоступен: {e}")
        return False
    
    print()
    return True


def check_environment_variables():
    """Проверка переменных окружения"""
    print("=" * 70)
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 70)
    
    issues = []
    
    # Проверка TELEGRAM_BOT_TOKEN
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        issues.append("TELEGRAM_BOT_TOKEN")
    else:
        token_preview = settings.TELEGRAM_BOT_TOKEN[:10] + "..." + settings.TELEGRAM_BOT_TOKEN[-10:]
        print(f"✅ TELEGRAM_BOT_TOKEN: {token_preview} (длина: {len(settings.TELEGRAM_BOT_TOKEN)})")
    
    # Проверка SUPABASE_URL
    if not settings.SUPABASE_URL:
        print("❌ SUPABASE_BASE_URL не установлен")
        issues.append("SUPABASE_BASE_URL")
    else:
        print(f"✅ SUPABASE_BASE_URL: {settings.SUPABASE_URL}")
        
        if not settings.SUPABASE_URL.startswith("https://"):
            print("   ⚠️ URL должен начинаться с https://")
            issues.append("SUPABASE_BASE_URL (неверный формат)")
        
        if not settings.SUPABASE_URL.endswith(".supabase.co"):
            print("   ⚠️ URL должен заканчиваться на .supabase.co")
            issues.append("SUPABASE_BASE_URL (неверный домен)")
    
    # Проверка SUPABASE_KEY
    if not settings.SUPABASE_KEY:
        print("❌ SUPABASE_SERVICE_KEY (или SUPABASE_KEY) не установлен")
        issues.append("SUPABASE_SERVICE_KEY|SUPABASE_KEY")
    else:
        key_length = len(settings.SUPABASE_KEY)
        key_preview = settings.SUPABASE_KEY[:15] + "..." + settings.SUPABASE_KEY[-15:]
        print(f"✅ SUPABASE_SERVICE_KEY: {key_preview}")
        print(f"   Длина ключа: {key_length} символов")
        
        # Анализ типа ключа
        if key_length < 100:
            print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Ключ слишком короткий ({key_length} символов)")
            print("   ⚠️ Похоже, что это НЕ Service Role Key!")
            print("   ℹ️ Service Role Key обычно 200+ символов и начинается с 'eyJ'")
            print()
            print("   📖 Как получить правильный ключ:")
            print("      1. Откройте Supabase Dashboard")
            print("      2. Выберите ваш проект")
            print("      3. Settings -> API")
            print("      4. Скопируйте 'service_role' key (НЕ 'anon' key!)")
            print("      5. Вставьте его в .env как SUPABASE_SERVICE_KEY (или SUPABASE_KEY)")
            print()
            issues.append("SUPABASE_SERVICE_KEY|SUPABASE_KEY (используется Anon Key вместо Service Role Key)")
        elif key_length >= 100 and key_length < 200:
            print("   ⚠️ Ключ короче обычного Service Role Key (обычно 200+ символов)")
            print("   Убедитесь, что это именно Service Role Key")
        else:
            print("   ✅ Длина ключа соответствует Service Role Key")
        
        if not settings.SUPABASE_KEY.startswith("eyJ"):
            print("   ⚠️ Service Role Key обычно начинается с 'eyJ'")
            issues.append("SUPABASE_SERVICE_KEY|SUPABASE_KEY (необычный формат)")
    
    # Проверка ADMIN_USER_ID
    if not settings.ADMIN_USER_ID:
        print("❌ ADMIN_USER_ID не установлен (доступ не защищён!)")
        issues.append("ADMIN_USER_ID")
    else:
        print(f"✅ ADMIN_USER_ID: {settings.ADMIN_USER_ID}")
    
    print()
    
    if issues:
        print("=" * 70)
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
        for issue in issues:
            print(f"   - {issue}")
        print("=" * 70)
        print()
        return False
    
    return True


async def test_supabase_api_direct():
    """Прямая проверка Supabase API с детальной диагностикой"""
    print("=" * 70)
    print("🔑 ПРЯМАЯ ПРОВЕРКА SUPABASE API")
    print("=" * 70)
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("❌ Недостаточно данных для проверки API")
        return False
    
    # Тестируем REST API напрямую
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Проверяем доступ к таблице users
    test_url = f"{settings.SUPABASE_URL}/rest/v1/users?select=telegram_id&limit=1"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📡 Запрос к: {test_url}")
            print(f"🔑 Используется ключ длиной: {len(settings.SUPABASE_KEY)} символов")
            
            response = await client.get(test_url, headers=headers)
            
            print(f"📨 Код ответа: {response.status_code}")
            print(f"📋 Заголовки ответа: {dict(response.headers)}")
            
            if response.status_code == 0:
                print("❌ HTTP 0 ОШИБКА!")
                print("   Это означает, что запрос не был успешно отправлен.")
                print("   Возможные причины:")
                print("   - Проблемы с SSL/TLS сертификатами")
                print("   - Блокировка файрволом или прокси")
                print("   - Неправильный URL")
                print("   - Сетевые проблемы на уровне ОС")
                return False
            
            if response.status_code == 200:
                print("✅ API работает! Соединение установлено успешно")
                try:
                    data = response.json()
                    print(f"📊 Получено записей: {len(data)}")
                except:
                    pass
                return True
            
            elif response.status_code == 401:
                print("❌ ОШИБКА АВТОРИЗАЦИИ (401)")
                print(f"   Ответ: {response.text}")
                print()
                print("   Это означает, что ключ API неверный или недействительный!")
                print("   Проверьте:")
                print("   1. Вы используете Service Role Key (не Anon Key)")
                print("   2. Ключ скопирован полностью, без пробелов")
                print("   3. В вашем проекте Supabase включен этот ключ")
                return False
            
            elif response.status_code == 404:
                print("❌ ТАБЛИЦА НЕ НАЙДЕНА (404)")
                print("   Таблица 'users' не существует в базе данных")
                print("   Выполните SQL скрипт из файла supabase_schema.sql")
                return False
            
            else:
                print(f"⚠️ Неожиданный код ответа: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("❌ ТАЙМАУТ: Сервер не отвечает в течение 30 секунд")
        print("   Проверьте подключение к интернету и доступность Supabase")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        print(f"   Тип ошибки: {type(e).__name__}")
        return False
    
    print()


async def test_supabase_client():
    """Проверка через официальный клиент Supabase"""
    print("=" * 70)
    print("📚 ПРОВЕРКА ЧЕРЕЗ SUPABASE CLIENT")
    print("=" * 70)
    
    try:
        from database import db
        
        # Тест получения пользователей
        users = await db.get_all_users()
        print(f"✅ Подключение через клиент работает")
        print(f"   Найдено пользователей: {len(users)}")
        
        # Тест получения стратегий
        strategies = await db.get_all_strategies()
        print(f"   Найдено стратегий: {len(strategies)}")
        
        # Тест получения токенов
        tokens = await db.get_all_tokens()
        print(f"   Найдено токенов: {len(tokens)}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения через клиент: {e}")
        print(f"   Тип ошибки: {type(e).__name__}")
        print()
        return False


def print_solution_steps():
    """Вывод шагов по решению проблем"""
    print("=" * 70)
    print("💡 РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ ПРОБЛЕМ")
    print("=" * 70)
    print()
    print("1. ПОЛУЧЕНИЕ ПРАВИЛЬНОГО КЛЮЧА:")
    print("   - Откройте https://supabase.com/dashboard")
    print("   - Выберите ваш проект")
    print("   - Перейдите в Settings -> API")
    print("   - Найдите раздел 'Project API keys'")
    print("   - Скопируйте 'service_role' key (обычно скрыт, нажмите 'Reveal')")
    print("   - Это должен быть длинный ключ (200+ символов)")
    print()
    print("2. ОБНОВЛЕНИЕ .env ФАЙЛА:")
    print("   - Откройте файл .env в корне проекта")
    print("   - Найдите строку SUPABASE_SERVICE_KEY=... (или SUPABASE_KEY=...)")
    print("   - Вставьте скопированный Service Role Key")
    print("   - Сохраните файл")
    print()
    print("3. ПРОВЕРКА ТАБЛИЦ:")
    print("   - Откройте SQL Editor в Supabase Dashboard")
    print("   - Выполните содержимое файла supabase_schema.sql")
    print("   - Это создаст все необходимые таблицы")
    print()
    print("4. ПОВТОРНЫЙ ТЕСТ:")
    print("   - Запустите: python3 diagnose_connection.py")
    print("   - Все проверки должны пройти успешно")
    print()
    print("=" * 70)


async def main():
    """Главная функция диагностики"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "🔬 ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ SUPABASE" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    all_checks_passed = True
    
    # 1. Проверка переменных окружения
    if not check_environment_variables():
        all_checks_passed = False
        print("⚠️ Сначала исправьте проблемы с переменными окружения")
        print_solution_steps()
        sys.exit(1)
    
    # 2. Проверка сети
    if not await test_network_connectivity():
        all_checks_passed = False
        print("❌ Проблемы с сетевым подключением")
        sys.exit(1)
    
    # 3. Прямая проверка API
    api_ok = await test_supabase_api_direct()
    if not api_ok:
        all_checks_passed = False
    
    # 4. Проверка через клиент
    if api_ok:
        client_ok = await test_supabase_client()
        if not client_ok:
            all_checks_passed = False
    
    # Итоговый результат
    print("\n")
    print("=" * 70)
    if all_checks_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 70)
        print()
        print("🚀 Бот готов к запуску: python bot.py")
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
        print("=" * 70)
        print()
        print_solution_steps()
        sys.exit(1)
    
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
