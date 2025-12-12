# 🏗️ Архитектура Admin Core (Repo 02)

## 📋 Обзор

Admin Core - это ядро управления торговой системой, которое отвечает за:
- Управление стратегиями
- Автономное (pattern-based) принятие решений LONG/SHORT/HOLD по условиям активной стратегии
- Логику анализа (reasoning logs) для администратора

## 🎯 Архитектурные Принципы

### 1. Разделение Ответственности

```
┌─────────────────────────────────────────────────────────────┐
│                     TRADING ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐              ┌───────────────────┐    │
│  │   UI Bot (Repo 1)│              │ Admin Core (Repo 2)│    │
│  │                  │              │                    │    │
│  │  • User Interface│              │  • Strategy Mgmt   │    │
│  │  • User Admin    │◄────────────►│  • Data Analysis   │    │
│  │  • Subscriptions │   Supabase   │  • Trading Core    │    │
│  │  • Notifications │              │  • Auto-Switching  │    │
│  └──────────────────┘              └───────────────────┘    │
│           │                                   │               │
│           │                                   │               │
│           └───────────────┬───────────────────┘               │
│                           │                                   │
│                  ┌────────▼─────────┐                        │
│                  │   Supabase DB    │                        │
│                  │                  │                        │
│                  │  • users         │                        │
│                  │  • strategies    │                        │
│                  │  • signals       │                        │
│                  │  • trades        │                        │
│                  │  • logs          │                        │
│                  └──────────────────┘                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Централизация Данных

**Единая База Данных (Supabase):**
- `users` - управление из UI Bot, просмотр из Admin Core
- `strategies` - создание и редактирование в Admin Core
- `signals` - генерация в Admin Core, отображение в UI Bot
- `trades` - исполнение и трекинг
- `logs` - централизованное логирование

### 3. Автономное Ядро (Pattern-Based Core)

Admin Core не использует внешние AI-модели. Решения принимаются строго по шаблонным условиям индикаторов активной стратегии, а каждый прогон записывает reasoning logs в Supabase (`decision_logs`).

## 🏛️ Компоненты Системы

### Core Services (Ядро)

#### 1. Data Aggregation Service (опционально / не используется в запуске по умолчанию)
**Файл:** `services/data_aggregation_service.py`

**Функции:**
- Сбор статистики по активам (день/неделя/месяц)
- Анализ рыночных условий
- Определение волатильности и трендов
- Расчет метрик производительности

**Ключевые методы:**
```python
await aggregation_service.get_asset_statistics(asset, period='daily')
await aggregation_service.get_market_conditions()
```

#### 2. Strategy Templates Service (опционально / не используется в запуске по умолчанию)
**Файл:** `services/strategy_templates_service.py`

**Функции:**
- Управление шаблонами стратегий
- 4 встроенных шаблона (Scalping, Momentum, Mean Reversion, Breakout)
- Рекомендации стратегий на основе условий
- Автонастройка параметров

**Шаблоны:**
- **Scalping** - высокочастотная торговля (5m, высокая волатильность)
- **Momentum** - следование тренду (1h, средняя волатильность)
- **Mean Reversion** - возврат к среднему (4h, низкая волатильность)
- **Breakout** - пробой уровней (1h, высокая волатильность)

#### 3. Dynamic Strategy Switcher (опционально / не используется в запуске по умолчанию)
**Файл:** `services/dynamic_strategy_switcher.py`

**Функции:**
- Автоматическое переключение стратегий
- Анализ производительности каждые 5 минут
- Адаптация к времени суток
- Реакция на изменение рыночных условий

**Триггеры переключения:**
- Плохая производительность (винрейт < 35%)
- Смена торговой сессии
- Изменение волатильности
- Запланированные проверки (каждые 8 часов)

### Database Layer

#### Supabase Connector
**Файл:** `database/supabase_connector.py`

**Улучшения:**
- ✅ Повторные попытки при сетевых ошибках
- ✅ Валидация Service Role Key
- ✅ Расширенная диагностика
- ✅ Фильтрация по датам
- ✅ Оптимизированные запросы

**Критические методы:**
```python
# Пользователи
await db.get_all_users(limit=100)
await db.get_user_by_id(telegram_id)

# Стратегии
await db.get_all_strategies()
await db.get_active_strategy()
await db.create_strategy(data)

# Данные с фильтрацией
await db.get_signals_by_date_range(start, end, asset)
await db.get_trades_by_date_range(start, end, asset)
```

## 🔄 Workflow (Типичный Цикл Работы)

### 1. Запуск Системы

```
┌─────────────────────────────────────────────────────────┐
│  1. Загрузка конфигурации (.env)                        │
│     ✓ SUPABASE_SERVICE_KEY (или SUPABASE_KEY) (200+ chars)│
│     ✓ SUPABASE_BASE_URL                                  │
│     ✓ SUPABASE_ENCRYPTION_KEY                            │
│     ✓ TELEGRAM_BOT_TOKEN                                 │
│     ✓ ADMIN_USER_ID                                      │
├─────────────────────────────────────────────────────────┤
│  2. Проверка подключения к Supabase                     │
│     ✓ Валидация ключа                                   │
│     ✓ Тестовый запрос к таблице users                   │
│     ✓ Проверка доступа                                  │
├─────────────────────────────────────────────────────────┤
│  3. Инициализация сервисов                              │
│     ✓ Strategy Manager (CRUD стратегий + шифрование)     │
│     ✓ Trading Logic Core (pattern-based)                 │
│     ✓ Reasoning logs (decision_logs)                     │
├─────────────────────────────────────────────────────────┤
│  4. Старт автоматических процессов                      │
│     ✓ Фоновый цикл Ядра (каждые N секунд)               │
│     ✓ Запись reasoning logs                             │
└─────────────────────────────────────────────────────────┘
```

### 2. Цикл Оптимизации

```
Каждые 5 минут:

1. Сбор данных
   └─► Агрегация статистики по активам
   └─► Анализ рыночных условий
   └─► Оценка производительности

2. Анализ
   └─► Проверка винрейта
   └─► Расчет Sharpe Ratio
   └─► Определение просадки

3. Принятие решения
   └─► Нужна ли оптимизация?
   └─► Нужно ли переключение?
   └─► Какие параметры изменить?

4. Действие
   └─► Применение оптимизации
   └─► Переключение стратегии
   └─► Логирование в БД
```

### 3. Динамическое Переключение

```
Условия переключения:

┌─────────────────┬──────────────────┬─────────────────┐
│  Время суток    │  Волатильность   │  Стратегия      │
├─────────────────┼──────────────────┼─────────────────┤
│  Азия (0-8 UTC) │  Низкая          │  Mean Reversion │
│  Overlap (8-12) │  Высокая         │  Scalping       │
│  Европа (12-16) │  Средняя         │  Momentum       │
│  Overlap (16-20)│  Высокая         │  Scalping       │
│  США (20-24)    │  Средняя         │  Momentum       │
└─────────────────┴──────────────────┴─────────────────┘

Дополнительные факторы:
• Производительность < 35% винрейт → переключение
• Просадка > 20% → снижение рисков + переключение
• Тренд изменился → смена типа стратегии
```

## 🔐 Безопасность

### Service Role Key
- ✅ Используется для полного доступа к БД
- ✅ Хранится в переменных окружения (.env)
- ✅ Не коммитится в Git
- ✅ Валидируется при запуске

### Доступ к API
- Только администратор (ADMIN_USER_ID)
- Middleware проверка в Telegram Bot
- Ограничение операций по ролям

## 📊 Таблицы Supabase

### Основные Таблицы

#### users
```sql
- telegram_id (PK)
- username, first_name, last_name
- subscription_type, subscription_expires_at
- is_blocked
- created_at, updated_at
```

#### strategies
```sql
- id (PK)
- name, description
- is_active (только одна активная!)
- assets_to_monitor (JSONB)
- timeframe
- indicators (JSONB)
- entry_rules, exit_rules (JSONB)
- risk_management (JSONB)
- created_at, updated_at
```

#### signals
```sql
- id (PK)
- asset, signal_type (buy/sell)
- price, amount
- strategy_id (FK)
- created_at
```

#### trades
```sql
- id (PK)
- user_id (FK), signal_id (FK)
- asset, trade_type
- entry_price, exit_price
- profit_loss
- status (open/closed)
- created_at, closed_at
```

## 🚀 Оптимизации

### База Данных
- ✅ Индексы на часто используемых полях
- ✅ Лимиты на выборки данных
- ✅ Фильтрация по датам
- ✅ Кэширование агрегированных данных (5 мин TTL)

### Производительность
- ✅ Асинхронные операции (asyncio)
- ✅ Batch-запросы (gather)
- ✅ Повторные попытки при ошибках
- ✅ Graceful degradation (продолжение работы при частичных ошибках)

### Масштабируемость
- ✅ Singleton паттерн для сервисов
- ✅ Независимые модули
- ✅ Легкое добавление новых стратегий
- ✅ Простая настройка параметров

## 📈 Метрики Успеха

### Производительность Стратегий
- Win Rate > 50%
- Sharpe Ratio > 0.5
- Max Drawdown < 20%
- Positive Net Profit

### Эффективность Системы
- Uptime > 99%
- Response Time < 1s
- Автопереключений за день: 2-5
- Оптимизаций за день: 10-20

## 🛠️ Инструменты Разработчика

### Диагностика
```bash
python3 diagnose_connection.py  # Полная диагностика системы
python3 test_connection.py      # Быстрая проверка подключения
```

### Тестирование
```bash
python -m pytest tests/        # Запуск тестов (если есть)
```

### Логирование
```bash
tail -f admin_bot.log          # Мониторинг логов в реальном времени
```

## 🎓 Лучшие Практики

### 1. Всегда используйте Service Role Key
❌ Неправильно: Anon Key (короткий, публичный)
✅ Правильно: Service Role Key (длинный, полный доступ)

### 2. Не храните ключи в коде
❌ Неправильно: `SUPABASE_KEY = "eyJ..."`
✅ Правильно: `SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")`

### 3. Используйте лимиты в запросах
❌ Неправильно: `select("*").execute()`
✅ Правильно: `select("*").limit(100).execute()`

### 4. Обрабатывайте ошибки
```python
try:
    result = await db.get_users()
except Exception as e:
    logger.error(f"Error: {e}")
    return []  # Graceful fallback
```

## 📚 Дополнительные Ресурсы

- [Supabase Documentation](https://supabase.com/docs)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Aiogram Framework](https://docs.aiogram.dev/)

---

**Версия:** 2.0  
**Дата обновления:** Декабрь 2025  
**Статус:** Production Ready
