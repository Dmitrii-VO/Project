-- ================================================================
-- СКРИПТ ОТКАТА МИГРАЦИИ: Новая система офферов
-- Версия: 1.0
-- Дата: 2025-07-09
-- ВНИМАНИЕ: Этот скрипт удалит все данные из новых таблиц!
-- ================================================================

-- Включаем проверку внешних ключей
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ================================================================
-- 1. ПРОВЕРКА НАЛИЧИЯ РЕЗЕРВНОЙ КОПИИ
-- ================================================================

-- Этот скрипт должен использоваться только с резервной копией!
-- Перед запуском убедитесь, что у вас есть .backup файл

-- ================================================================
-- 2. УДАЛЕНИЕ ПРЕДСТАВЛЕНИЙ
-- ================================================================

DROP VIEW IF EXISTS v_offer_proposals_full;
DROP VIEW IF EXISTS v_offer_statistics_full;

-- ================================================================
-- 3. УДАЛЕНИЕ ТРИГГЕРОВ
-- ================================================================

DROP TRIGGER IF EXISTS set_proposal_expires_at;
DROP TRIGGER IF EXISTS update_placement_updated_at;
DROP TRIGGER IF EXISTS update_offer_statistics_on_proposal_change;

-- ================================================================
-- 4. УДАЛЕНИЕ ИНДЕКСОВ
-- ================================================================

-- Индексы для новых таблиц
DROP INDEX IF EXISTS idx_offer_proposals_offer_id;
DROP INDEX IF EXISTS idx_offer_proposals_channel_id;
DROP INDEX IF EXISTS idx_offer_proposals_status;
DROP INDEX IF EXISTS idx_offer_proposals_created_at;
DROP INDEX IF EXISTS idx_offer_proposals_expires_at;

DROP INDEX IF EXISTS idx_offer_placements_proposal_id;
DROP INDEX IF EXISTS idx_offer_placements_status;
DROP INDEX IF EXISTS idx_offer_placements_placement_start;
DROP INDEX IF EXISTS idx_offer_placements_placement_end;

DROP INDEX IF EXISTS idx_placement_checks_placement_id;
DROP INDEX IF EXISTS idx_placement_checks_check_time;
DROP INDEX IF EXISTS idx_placement_checks_post_exists;

-- Индексы для существующих таблиц
DROP INDEX IF EXISTS idx_offers_status;
DROP INDEX IF EXISTS idx_channels_parsing_enabled;
DROP INDEX IF EXISTS idx_channels_last_parsed_at;

-- ================================================================
-- 5. УДАЛЕНИЕ НОВЫХ ТАБЛИЦ
-- ================================================================

-- Удаляем в обратном порядке зависимостей
DROP TABLE IF EXISTS placement_checks;
DROP TABLE IF EXISTS offer_placements;
DROP TABLE IF EXISTS offer_statistics;
DROP TABLE IF EXISTS offer_proposals;

-- ================================================================
-- 6. УДАЛЕНИЕ НОВЫХ ПОЛЕЙ ИЗ СУЩЕСТВУЮЩИХ ТАБЛИЦ
-- ================================================================

-- SQLite не поддерживает DROP COLUMN, поэтому создаем новые таблицы

-- 6.1 Восстановление таблицы offers
CREATE TABLE offers_backup AS 
SELECT 
    id,
    main_offer_id,
    title,
    description,
    content,
    budget,
    target_audience,
    placement_requirements,
    contact_info,
    created_by,
    created_at,
    updated_at,
    expires_at,
    is_active,
    category,
    subcategory,
    is_premium,
    priority_score,
    tags,
    media_files,
    placement_duration,
    min_subscriber_count,
    max_budget_per_post
FROM offers;

DROP TABLE offers;

ALTER TABLE offers_backup RENAME TO offers;

-- 6.2 Восстановление таблицы channels
CREATE TABLE channels_backup AS 
SELECT 
    id,
    telegram_id,
    title,
    username,
    description,
    subscriber_count,
    category,
    language,
    is_verified,
    is_active,
    owner_id,
    created_at,
    updated_at,
    verification_code,
    status,
    verified_at
FROM channels;

DROP TABLE channels;

ALTER TABLE channels_backup RENAME TO channels;

-- ================================================================
-- 7. ВОССТАНОВЛЕНИЕ ИСХОДНЫХ ИНДЕКСОВ
-- ================================================================

-- Восстанавливаем основные индексы для offers
CREATE INDEX IF NOT EXISTS idx_offers_created_by ON offers(created_by);
CREATE INDEX IF NOT EXISTS idx_offers_is_active ON offers(is_active);
CREATE INDEX IF NOT EXISTS idx_offers_category ON offers(category);
CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at);

-- Восстанавливаем основные индексы для channels
CREATE INDEX IF NOT EXISTS idx_channels_owner_id ON channels(owner_id);
CREATE INDEX IF NOT EXISTS idx_channels_is_active ON channels(is_active);
CREATE INDEX IF NOT EXISTS idx_channels_is_verified ON channels(is_verified);
CREATE INDEX IF NOT EXISTS idx_channels_category ON channels(category);

-- ================================================================
-- 8. УДАЛЕНИЕ ЗАПИСИ О МИГРАЦИИ
-- ================================================================

DELETE FROM migrations WHERE version = '1.0_offer_system';

-- ================================================================
-- 9. ПРОВЕРКА РЕЗУЛЬТАТОВ ОТКАТА
-- ================================================================

-- Проверяем, что новые таблицы удалены
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые таблицы удалены'
        ELSE 'ERROR: Остались новые таблицы: ' || GROUP_CONCAT(name)
    END as new_tables_check
FROM sqlite_master 
WHERE type='table' AND name LIKE 'offer_%';

-- Проверяем структуру таблицы offers
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые поля в offers удалены'
        ELSE 'ERROR: Остались новые поля в offers'
    END as offers_fields_check
FROM pragma_table_info('offers') 
WHERE name IN ('status', 'is_marked', 'selected_channels_count', 'expected_placement_duration');

-- Проверяем структуру таблицы channels
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые поля в channels удалены'
        ELSE 'ERROR: Остались новые поля в channels'
    END as channels_fields_check
FROM pragma_table_info('channels') 
WHERE name IN ('last_parsed_at', 'parsing_enabled', 'telegram_channel_link');

-- Проверяем индексы
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые индексы удалены'
        ELSE 'ERROR: Остались новые индексы: ' || GROUP_CONCAT(name)
    END as indexes_check
FROM sqlite_master 
WHERE type='index' AND name LIKE 'idx_offer_%';

-- Проверяем триггеры
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые триггеры удалены'
        ELSE 'ERROR: Остались новые триггеры: ' || GROUP_CONCAT(name)
    END as triggers_check
FROM sqlite_master 
WHERE type='trigger' AND (
    name LIKE '%offer%' OR 
    name LIKE '%proposal%' OR 
    name LIKE '%placement%'
);

-- Проверяем представления
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: Новые представления удалены'
        ELSE 'ERROR: Остались новые представления: ' || GROUP_CONCAT(name)
    END as views_check
FROM sqlite_master 
WHERE type='view' AND name LIKE 'v_%';

COMMIT;

-- ================================================================
-- 10. ФИНАЛЬНОЕ СООБЩЕНИЕ
-- ================================================================

SELECT 'Откат миграции завершен!' as result;
SELECT 'Проверьте результаты выше и убедитесь, что все OK' as instruction;
SELECT 'Если есть ошибки - восстановите базу из резервной копии' as warning;