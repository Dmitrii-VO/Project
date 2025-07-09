-- ================================================================
-- МИГРАЦИЯ БАЗЫ ДАННЫХ: Новая система офферов
-- Версия: 1.0
-- Дата: 2025-07-09
-- ================================================================

-- Включаем проверку внешних ключей
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ================================================================
-- 1. МОДИФИКАЦИЯ СУЩЕСТВУЮЩИХ ТАБЛИЦ
-- ================================================================

-- 1.1 Добавление новых полей в таблицу offers
ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'matching', 'started', 'in_progress', 'completed', 'cancelled'));
ALTER TABLE offers ADD COLUMN is_marked BOOLEAN DEFAULT 0;
ALTER TABLE offers ADD COLUMN selected_channels_count INTEGER DEFAULT 0;
ALTER TABLE offers ADD COLUMN expected_placement_duration INTEGER DEFAULT 7; -- в днях

-- 1.2 Добавление полей для парсинга в таблицу channels
ALTER TABLE channels ADD COLUMN last_parsed_at DATETIME DEFAULT NULL;
ALTER TABLE channels ADD COLUMN parsing_enabled BOOLEAN DEFAULT 1;
ALTER TABLE channels ADD COLUMN telegram_channel_link TEXT DEFAULT NULL;

-- ================================================================
-- 2. СОЗДАНИЕ НОВЫХ ТАБЛИЦ
-- ================================================================

-- 2.1 Таблица предложений владельцам каналов
CREATE TABLE IF NOT EXISTS offer_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'accepted', 'rejected', 'expired', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    responded_at DATETIME DEFAULT NULL,
    rejection_reason TEXT DEFAULT NULL,
    expires_at DATETIME DEFAULT NULL, -- автоматически через неделю
    notified_at DATETIME DEFAULT NULL, -- когда отправлено уведомление
    reminder_sent_at DATETIME DEFAULT NULL, -- когда отправлено напоминание
    
    -- Внешние ключи
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
    
    -- Уникальность: один оффер - один канал
    UNIQUE(offer_id, channel_id)
);

-- 2.2 Таблица размещений постов
CREATE TABLE IF NOT EXISTS offer_placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL,
    post_url TEXT DEFAULT NULL, -- ссылка на размещенный пост
    placement_start DATETIME DEFAULT NULL, -- когда пост был размещен
    placement_end DATETIME DEFAULT NULL, -- когда пост был удален/завершен
    expected_duration INTEGER DEFAULT 7, -- ожидаемая продолжительность в днях
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'placed', 'monitoring', 'completed', 'failed', 'expired')),
    final_views_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (proposal_id) REFERENCES offer_proposals(id) ON DELETE CASCADE
);

-- 2.3 Таблица логов проверок размещения
CREATE TABLE IF NOT EXISTS placement_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placement_id INTEGER NOT NULL,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    post_exists BOOLEAN DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    check_status TEXT DEFAULT 'success' CHECK (check_status IN ('success', 'error', 'not_found', 'access_denied')),
    error_message TEXT DEFAULT NULL,
    response_data TEXT DEFAULT NULL, -- JSON с полными данными ответа
    
    -- Внешние ключи
    FOREIGN KEY (placement_id) REFERENCES offer_placements(id) ON DELETE CASCADE
);

-- 2.4 Таблица агрегированной статистики по офферам
CREATE TABLE IF NOT EXISTS offer_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    total_proposals INTEGER DEFAULT 0,
    accepted_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    expired_count INTEGER DEFAULT 0,
    cancelled_count INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0.00,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
    
    -- Уникальность: одна статистика на оффер
    UNIQUE(offer_id)
);

-- ================================================================
-- 3. СОЗДАНИЕ ИНДЕКСОВ ДЛЯ ОПТИМИЗАЦИИ
-- ================================================================

-- 3.1 Индексы для таблицы offer_proposals
CREATE INDEX IF NOT EXISTS idx_offer_proposals_offer_id ON offer_proposals(offer_id);
CREATE INDEX IF NOT EXISTS idx_offer_proposals_channel_id ON offer_proposals(channel_id);
CREATE INDEX IF NOT EXISTS idx_offer_proposals_status ON offer_proposals(status);
CREATE INDEX IF NOT EXISTS idx_offer_proposals_created_at ON offer_proposals(created_at);
CREATE INDEX IF NOT EXISTS idx_offer_proposals_expires_at ON offer_proposals(expires_at);

-- 3.2 Индексы для таблицы offer_placements
CREATE INDEX IF NOT EXISTS idx_offer_placements_proposal_id ON offer_placements(proposal_id);
CREATE INDEX IF NOT EXISTS idx_offer_placements_status ON offer_placements(status);
CREATE INDEX IF NOT EXISTS idx_offer_placements_placement_start ON offer_placements(placement_start);
CREATE INDEX IF NOT EXISTS idx_offer_placements_placement_end ON offer_placements(placement_end);

-- 3.3 Индексы для таблицы placement_checks
CREATE INDEX IF NOT EXISTS idx_placement_checks_placement_id ON placement_checks(placement_id);
CREATE INDEX IF NOT EXISTS idx_placement_checks_check_time ON placement_checks(check_time);
CREATE INDEX IF NOT EXISTS idx_placement_checks_post_exists ON placement_checks(post_exists);

-- 3.4 Индексы для существующих таблиц
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);
CREATE INDEX IF NOT EXISTS idx_channels_parsing_enabled ON channels(parsing_enabled);
CREATE INDEX IF NOT EXISTS idx_channels_last_parsed_at ON channels(last_parsed_at);

-- ================================================================
-- 4. СОЗДАНИЕ ТРИГГЕРОВ ДЛЯ АВТОМАТИЗАЦИИ
-- ================================================================

-- 4.1 Триггер для автоматического обновления expires_at в offer_proposals
CREATE TRIGGER IF NOT EXISTS set_proposal_expires_at
    AFTER INSERT ON offer_proposals
    FOR EACH ROW
    WHEN NEW.expires_at IS NULL
BEGIN
    UPDATE offer_proposals 
    SET expires_at = datetime(NEW.created_at, '+7 days')
    WHERE id = NEW.id;
END;

-- 4.2 Триггер для обновления updated_at в offer_placements
CREATE TRIGGER IF NOT EXISTS update_placement_updated_at
    AFTER UPDATE ON offer_placements
    FOR EACH ROW
BEGIN
    UPDATE offer_placements 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- 4.3 Триггер для обновления статистики при изменении предложений
CREATE TRIGGER IF NOT EXISTS update_offer_statistics_on_proposal_change
    AFTER UPDATE OF status ON offer_proposals
    FOR EACH ROW
BEGIN
    INSERT OR REPLACE INTO offer_statistics (
        offer_id, 
        total_proposals, 
        accepted_count, 
        rejected_count, 
        expired_count, 
        cancelled_count,
        last_updated
    )
    SELECT 
        NEW.offer_id,
        COUNT(*) as total_proposals,
        SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
        SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_count,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count,
        CURRENT_TIMESTAMP
    FROM offer_proposals 
    WHERE offer_id = NEW.offer_id;
END;

-- ================================================================
-- 5. НАСТРОЙКА ЗНАЧЕНИЙ ПО УМОЛЧАНИЮ ДЛЯ СУЩЕСТВУЮЩИХ ЗАПИСЕЙ
-- ================================================================

-- 5.1 Обновление существующих офферов
UPDATE offers 
SET status = 'draft', 
    is_marked = 0, 
    selected_channels_count = 0,
    expected_placement_duration = 7
WHERE status IS NULL OR status = '';

-- 5.2 Обновление существующих каналов
UPDATE channels 
SET parsing_enabled = 1,
    telegram_channel_link = CASE 
        WHEN username IS NOT NULL THEN 'https://t.me/' || username
        ELSE NULL 
    END
WHERE parsing_enabled IS NULL;

-- ================================================================
-- 6. СОЗДАНИЕ ПРЕДСТАВЛЕНИЙ ДЛЯ УДОБСТВА
-- ================================================================

-- 6.1 Представление для полной информации о предложениях
CREATE VIEW IF NOT EXISTS v_offer_proposals_full AS
SELECT 
    op.id,
    op.offer_id,
    op.channel_id,
    op.status,
    op.created_at,
    op.responded_at,
    op.rejection_reason,
    op.expires_at,
    
    -- Информация об оффере
    o.title as offer_title,
    o.description as offer_description,
    o.budget as offer_budget,
    o.status as offer_status,
    
    -- Информация о канале
    c.title as channel_title,
    c.username as channel_username,
    c.subscriber_count,
    c.category as channel_category,
    c.owner_id as channel_owner_id,
    
    -- Информация о размещении
    opl.id as placement_id,
    opl.post_url,
    opl.placement_start,
    opl.placement_end,
    opl.status as placement_status,
    opl.final_views_count
    
FROM offer_proposals op
LEFT JOIN offers o ON op.offer_id = o.id
LEFT JOIN channels c ON op.channel_id = c.id
LEFT JOIN offer_placements opl ON op.id = opl.proposal_id;

-- 6.2 Представление для статистики офферов
CREATE VIEW IF NOT EXISTS v_offer_statistics_full AS
SELECT 
    o.id as offer_id,
    o.title as offer_title,
    o.status as offer_status,
    o.budget as offer_budget,
    o.created_at as offer_created_at,
    
    -- Статистика из таблицы
    COALESCE(os.total_proposals, 0) as total_proposals,
    COALESCE(os.accepted_count, 0) as accepted_count,
    COALESCE(os.rejected_count, 0) as rejected_count,
    COALESCE(os.expired_count, 0) as expired_count,
    COALESCE(os.cancelled_count, 0) as cancelled_count,
    COALESCE(os.completed_count, 0) as completed_count,
    COALESCE(os.failed_count, 0) as failed_count,
    COALESCE(os.total_views, 0) as total_views,
    COALESCE(os.total_spent, 0.00) as total_spent,
    
    -- Расчетные поля
    CASE 
        WHEN os.total_proposals > 0 THEN 
            ROUND((os.accepted_count * 100.0 / os.total_proposals), 2)
        ELSE 0 
    END as acceptance_rate,
    
    CASE 
        WHEN os.accepted_count > 0 THEN 
            ROUND((os.completed_count * 100.0 / os.accepted_count), 2)
        ELSE 0 
    END as completion_rate
    
FROM offers o
LEFT JOIN offer_statistics os ON o.id = os.offer_id;

-- ================================================================
-- 7. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ
-- ================================================================

-- Проверим, что все таблицы созданы корректно
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'offer_%';
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';
SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%offer%';
SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v_%';

COMMIT;

-- ================================================================
-- КОНЕЦ МИГРАЦИИ
-- ================================================================

-- Сообщение об успешном завершении
SELECT 'Миграция базы данных завершена успешно!' as result;