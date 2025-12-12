# 🚀 Инструкция по развертыванию

Пошаговое руководство по развертыванию Admin Panel Bot.

## 📋 Предварительные требования

1. **Python 3.9+**
2. **Telegram Bot Token** (получить у @BotFather)
3. **Supabase Project** (зарегистрироваться на supabase.com)

## 🔧 Шаг 1: Создание Telegram бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   - Введите название бота (например, "Trading Admin Panel")
   - Введите username (должен заканчиваться на `bot`, например, `trading_admin_bot`)
4. Сохраните полученный токен

## 🗄 Шаг 2: Настройка Supabase

### 2.1 Создание проекта

1. Перейдите на [supabase.com](https://supabase.com)
2. Создайте новый проект
3. Сохраните:
   - `Project URL` (например, `https://xxxxx.supabase.co`)
   - `Service Role Key` (находится в Settings > API)

### 2.2 Создание таблиц

1. Откройте SQL Editor в Supabase Dashboard
2. Скопируйте содержимое файла `supabase_schema.sql`
3. Выполните SQL-скрипт
4. Проверьте, что все таблицы созданы

## 💻 Шаг 3: Установка на локальной машине

### 4.1 Клонирование проекта

```bash
cd /path/to/your/projects
# Если проект в git:
# git clone <repo_url>
cd workspace
```

### 4.2 Создание виртуального окружения

```bash
# Создание venv
python3 -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate
```

### 4.3 Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4.4 Настройка .env

```bash
cp .env.example .env
nano .env  # или любой текстовый редактор
```

Заполните переменные:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
SUPABASE_BASE_URL=https://your-project.supabase.co
# ВАЖНО: Используйте Service Role Key (200+ символов), не Anon Key!
# Найдите его в: Supabase Dashboard -> Settings -> API -> service_role (не anon!)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your_full_service_role_key

# Ваш Telegram ID (получите у @userinfobot)
ADMIN_USER_ID=123456789

# Ключ шифрования (Fernet)
SUPABASE_ENCRYPTION_KEY=your_fernet_key_here
```

### 4.5 Получение вашего Telegram ID

1. Откройте [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте любое сообщение
3. Скопируйте ваш ID
4. Добавьте его в `ADMIN_USER_ID` в .env

### 4.6 Запуск бота

```bash
python3 bot.py
```

Если всё настроено правильно, вы увидите:

```
INFO - 🚀 Admin Panel Bot запускается...
INFO - ✅ Конфигурация проверена
INFO - ✅ Подключение к Supabase установлено
INFO - ✅ Admin Panel Bot успешно запущен!
```

И получите сообщение в Telegram от вашего бота.

## 🌐 Шаг 5: Развертывание на сервере (опционально)

### Вариант 1: VPS/Dedicated Server

#### 5.1 Подключение к серверу

```bash
ssh user@your-server-ip
```

#### 5.2 Установка Python

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

#### 5.3 Клонирование проекта

```bash
cd /opt
sudo git clone <your-repo> admin-bot
cd admin-bot
```

#### 5.4 Установка зависимостей

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5.5 Настройка .env

```bash
sudo nano .env
# Заполните переменные
```

#### 5.6 Создание systemd service

```bash
sudo nano /etc/systemd/system/admin-bot.service
```

Содержимое:

```ini
[Unit]
Description=Trading Admin Panel Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/admin-bot
ExecStart=/opt/admin-bot/venv/bin/python /opt/admin-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 5.7 Запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl enable admin-bot
sudo systemctl start admin-bot
sudo systemctl status admin-bot
```

#### 5.8 Просмотр логов

```bash
sudo journalctl -u admin-bot -f
# или
tail -f /opt/admin-bot/admin_bot.log
```

### Вариант 2: Render.com

1. Создайте аккаунт на [render.com](https://render.com)
2. Создайте новый Web Service
3. Подключите ваш Git репозиторий
4. Настройте:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. Добавьте Environment Variables из .env
6. Deploy!

### Вариант 3: Heroku

1. Создайте аккаунт на [heroku.com](https://heroku.com)
2. Установите Heroku CLI
3. Создайте Procfile:

```
worker: python bot.py
```

4. Deploy:

```bash
heroku login
heroku create your-admin-bot
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set SUPABASE_BASE_URL=your_url
# ... остальные переменные
git push heroku main
heroku ps:scale worker=1
```

## ✅ Проверка работоспособности

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Должны увидеть главное меню
5. Попробуйте основные функции:
   - 👥 Пользователи
   - 📊 Статистика
   - 🎯 Стратегии

## 🔍 Решение проблем

### Бот не отвечает

1. Проверьте, что бот запущен:
   ```bash
   ps aux | grep bot.py
   ```

2. Проверьте логи:
   ```bash
   tail -f admin_bot.log
   ```

3. Проверьте токен в .env

### Ошибка подключения к Supabase

1. Проверьте `SUPABASE_BASE_URL` и `SUPABASE_SERVICE_KEY` (или `SUPABASE_KEY`)
2. Убедитесь, что используется Service Role Key (200+ символов), а не Anon Key!
3. Убедитесь, что таблицы созданы (запустите SQL из supabase_schema.sql)
4. Запустите диагностику: `python3 diagnose_connection.py`

### Доступ запрещен

1. Проверьте, что ваш Telegram ID в `ADMIN_USER_ID`
2. ID должен быть числом, без пробелов
3. Repo 02 предполагает одного администратора

## 🔐 Безопасность

1. **Никогда не коммитьте .env в git**
2. Используйте Service Role Key только на сервере
3. Регулярно обновляйте зависимости:
   ```bash
   pip install --upgrade -r requirements.txt
   ```
4. Следите за логами на предмет подозрительной активности
5. Используйте firewall на сервере

## 📊 Мониторинг

### Логи

- Локально: `admin_bot.log`
- Systemd: `journalctl -u admin-bot -f`
- Heroku: `heroku logs --tail`

### Статистика

- Используйте команду `/stats` в боте
- Проверяйте раздел "📊 Статистика"
- Настройте уведомления о критических событиях

## 🔄 Обновление

```bash
# Остановка бота
sudo systemctl stop admin-bot

# Обновление кода
git pull

# Обновление зависимостей
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Запуск бота
sudo systemctl start admin-bot
```

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте документацию: `README.md`
2. Просмотрите логи: `admin_bot.log`
3. Проверьте Issues в репозитории
4. Создайте новый Issue с описанием проблемы

---

**Удачного развертывания! 🚀**
