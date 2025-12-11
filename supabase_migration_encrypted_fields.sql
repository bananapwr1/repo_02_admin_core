-- ============================================
-- Миграция: Добавление зашифрованных полей в таблицу strategies
-- ============================================
-- Этот скрипт добавляет поддержку шифрования конфиденциальных данных
-- Используется с ENCRYPTION_KEY в Admin Core

-- Добавляем новые колонки для зашифрованных данных
ALTER TABLE strategies 
ADD COLUMN IF NOT EXISTS api_keys_encrypted TEXT,
ADD COLUMN IF NOT EXISTS secret_keys_encrypted TEXT,
ADD COLUMN IF NOT EXISTS private_params_encrypted TEXT,
ADD COLUMN IF NOT EXISTS credentials_encrypted TEXT;

-- Добавляем комментарии для документации
COMMENT ON COLUMN strategies.api_keys_encrypted IS 'Зашифрованные API ключи бирж (Fernet encryption)';
COMMENT ON COLUMN strategies.secret_keys_encrypted IS 'Зашифрованные секретные ключи (Fernet encryption)';
COMMENT ON COLUMN strategies.private_params_encrypted IS 'Зашифрованные приватные параметры (Fernet encryption)';
COMMENT ON COLUMN strategies.credentials_encrypted IS 'Зашифрованные учетные данные (Fernet encryption)';

-- ============================================
-- Завершение миграции
-- ============================================
-- Миграция выполнена успешно!
-- 
-- ВАЖНО: Все конфиденциальные данные теперь должны шифроваться перед сохранением
-- Используйте StrategyManagerService для работы со стратегиями
