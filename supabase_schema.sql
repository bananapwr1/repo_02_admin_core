-- SQL Schema для Supabase
-- Создание всех необходимых таблиц для Admin Panel Bot

-- ============================================
-- Таблица пользователей
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    is_blocked BOOLEAN DEFAULT FALSE,
    subscription_type TEXT DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_type);
CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked);

-- ============================================
-- Таблица стратегий
-- ============================================
CREATE TABLE IF NOT EXISTS strategies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    assets_to_monitor JSONB DEFAULT '[]'::jsonb,
    timeframe TEXT DEFAULT '1h',
    indicators JSONB DEFAULT '{}'::jsonb,
    entry_rules JSONB DEFAULT '{}'::jsonb,
    exit_rules JSONB DEFAULT '{}'::jsonb,
    risk_management JSONB DEFAULT '{}'::jsonb,
    
    -- Зашифрованные поля для конфиденциальных данных
    -- Эти поля содержат зашифрованные JSON-данные (используется Fernet encryption)
    api_keys_encrypted TEXT,           -- Зашифрованные API ключи бирж
    secret_keys_encrypted TEXT,        -- Зашифрованные секретные ключи
    private_params_encrypted TEXT,     -- Зашифрованные приватные параметры
    credentials_encrypted TEXT,        -- Зашифрованные учетные данные
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_ai BOOLEAN DEFAULT FALSE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_strategies_created_at ON strategies(created_at DESC);

-- ============================================
-- Таблица токенов приглашения
-- ============================================
CREATE TABLE IF NOT EXISTS invite_tokens (
    token TEXT PRIMARY KEY,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    subscription_type TEXT DEFAULT 'trial',
    is_active BOOLEAN DEFAULT TRUE,
    created_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_tokens_active ON invite_tokens(is_active);
CREATE INDEX IF NOT EXISTS idx_tokens_created_by ON invite_tokens(created_by);

-- ============================================
-- Таблица системных логов
-- ============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL PRIMARY KEY,
    level TEXT DEFAULT 'INFO',
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);

-- ============================================
-- Таблица логов решений AI
-- ============================================
CREATE TABLE IF NOT EXISTS decision_logs (
    id BIGSERIAL PRIMARY KEY,
    asset TEXT NOT NULL,
    signal_type TEXT,
    reasoning TEXT,
    confidence DOUBLE PRECISION,
    indicators_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_decision_logs_asset ON decision_logs(asset);
CREATE INDEX IF NOT EXISTS idx_decision_logs_created_at ON decision_logs(created_at DESC);

-- ============================================
-- Таблица сигналов
-- ============================================
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    asset TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    price DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    timeframe INTEGER,
    strategy_id BIGINT REFERENCES strategies(id),
    sent_to_users INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_signals_asset ON signals(asset);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy_id);

-- ============================================
-- Таблица трейдов
-- ============================================
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    signal_id BIGINT REFERENCES signals(id),
    asset TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    entry_price DOUBLE PRECISION,
    exit_price DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    profit_loss DOUBLE PRECISION,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);

-- ============================================
-- Таблица настроек бота
-- ============================================
CREATE TABLE IF NOT EXISTS bot_settings (
    id BIGSERIAL PRIMARY KEY,
    name TEXT DEFAULT 'Trading Admin Panel',
    welcome_message TEXT DEFAULT 'Добро пожаловать!',
    contact_info TEXT,
    maintenance_mode BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Вставляем дефолтные настройки (если таблица пустая)
INSERT INTO bot_settings (name, welcome_message)
SELECT 'Trading Admin Panel', 'Добро пожаловать в админ-панель!'
WHERE NOT EXISTS (SELECT 1 FROM bot_settings);

-- ============================================
-- Таблица внутренних секретов/настроек Ядра (зашифрованные значения)
-- ============================================
CREATE TABLE IF NOT EXISTS core_settings (
    id BIGSERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value_encrypted TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_core_settings_key ON core_settings(key);

-- ============================================
-- Функция автоматического обновления updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автоматического обновления
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_strategies_updated_at ON strategies;
CREATE TRIGGER update_strategies_updated_at
    BEFORE UPDATE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bot_settings_updated_at ON bot_settings;
CREATE TRIGGER update_bot_settings_updated_at
    BEFORE UPDATE ON bot_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_core_settings_updated_at ON core_settings;
CREATE TRIGGER update_core_settings_updated_at
    BEFORE UPDATE ON core_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Row Level Security (RLS) - Опционально
-- ============================================
-- Раскомментируйте, если хотите использовать RLS

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE invite_tokens ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE decision_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE bot_settings ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Вспомогательные функции
-- ============================================

-- Функция для очистки старых логов (старше 30 дней)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '30 days';
    DELETE FROM decision_logs WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Функция для получения статистики
CREATE OR REPLACE FUNCTION get_statistics()
RETURNS TABLE (
    total_users BIGINT,
    active_users BIGINT,
    blocked_users BIGINT,
    total_strategies BIGINT,
    active_strategies BIGINT,
    total_signals BIGINT,
    total_trades BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_users,
        COUNT(*) FILTER (WHERE NOT is_blocked) AS active_users,
        COUNT(*) FILTER (WHERE is_blocked) AS blocked_users,
        (SELECT COUNT(*) FROM strategies) AS total_strategies,
        (SELECT COUNT(*) FROM strategies WHERE is_active = TRUE) AS active_strategies,
        (SELECT COUNT(*) FROM signals) AS total_signals,
        (SELECT COUNT(*) FROM trades) AS total_trades
    FROM users;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Комментарии к таблицам
-- ============================================
COMMENT ON TABLE users IS 'Пользователи торговой системы';
COMMENT ON TABLE strategies IS 'Торговые стратегии';
COMMENT ON TABLE invite_tokens IS 'Токены приглашения';
COMMENT ON TABLE system_logs IS 'Системные логи';
COMMENT ON TABLE decision_logs IS 'Логи решений AI';
COMMENT ON TABLE signals IS 'Торговые сигналы';
COMMENT ON TABLE trades IS 'Выполненные трейды';
COMMENT ON TABLE bot_settings IS 'Настройки бота';

-- ============================================
-- Завершение
-- ============================================
-- Схема создана успешно!
