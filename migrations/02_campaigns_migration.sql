-- ================================================================
-- МИГРАЦИЯ БАЗЫ ДАННЫХ: Система рекламных кампаний
-- Версия: 2.0
-- Дата: 2025-07-20
-- ================================================================

-- Включаем проверку внешних ключей
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ================================================================
-- 1. СОЗДАНИЕ ТАБЛИЦЫ РЕКЛАМОДАТЕЛЕЙ
-- ================================================================

CREATE TABLE IF NOT EXISTS campaign_advertisers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,              -- Название рекламодателя
    inn TEXT,                               -- ИНН компании
    contact_person TEXT,                    -- Контактное лицо
    email TEXT,                             -- Email
    phone TEXT,                             -- Телефон
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- 2. СОЗДАНИЕ ОСНОВНОЙ ТАБЛИЦЫ КАМПАНИЙ
-- ================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Основная информация
    name TEXT NOT NULL,                          -- Название кампании
    budget_limit DECIMAL(12, 2) DEFAULT 0.00,   -- Лимит бюджета в рублях
    
    -- UTM и трекинг
    add_utm_tags BOOLEAN DEFAULT 0,             -- Добавлять UTM метки к ссылкам
    track_clicks BOOLEAN DEFAULT 0,             -- Отслеживать клики по каждой ссылке
    
    -- Период работы
    start_date DATE NOT NULL,                   -- Дата начала (YYYY-MM-DD)
    end_date DATE NOT NULL,                     -- Дата окончания (YYYY-MM-DD)
    
    -- Время работы
    work_weekends BOOLEAN DEFAULT 1,            -- Работать в выходные дни
    work_hours_only BOOLEAN DEFAULT 0,          -- Только рабочие часы (9-18)
    
    -- Информация о рекламодателе
    advertiser_id INTEGER,                      -- Связь с таблицей рекламодателей
    advertiser_custom TEXT,                     -- Пользовательский ввод рекламодателя
    product_name TEXT,                          -- Наименование товара/услуги
    advertiser_inn TEXT,                        -- ИНН рекламодателя
    
    -- Рекламный пост
    ad_content TEXT,                            -- Содержание рекламного поста
    
    -- Мета-информация
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed', 'cancelled')),
    created_by INTEGER NOT NULL,               -- ID пользователя-создателя
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Связь с офферами (опционально)
    related_offer_id INTEGER,
    
    -- Ограничения
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_offer_id) REFERENCES offers(id) ON DELETE SET NULL,
    FOREIGN KEY (advertiser_id) REFERENCES campaign_advertisers(id) ON DELETE SET NULL,
    
    -- Проверки
    CHECK (start_date <= end_date),
    CHECK (budget_limit >= 0),
    CHECK (LENGTH(name) >= 3 AND LENGTH(name) <= 200)
);

-- ================================================================
-- 3. СОЗДАНИЕ ТАБЛИЦЫ UTM НАСТРОЕК
-- ================================================================

CREATE TABLE IF NOT EXISTS campaign_utm_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    
    -- UTM параметры
    utm_source TEXT DEFAULT 'telegram',        -- utm_source
    utm_medium TEXT DEFAULT 'channel',         -- utm_medium  
    utm_campaign TEXT,                         -- utm_campaign (обычно название кампании)
    utm_term TEXT,                             -- utm_term
    utm_content TEXT,                          -- utm_content
    
    -- Дополнительные настройки
    custom_parameters TEXT,                    -- JSON с дополнительными параметрами
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    UNIQUE(campaign_id)  -- Одна настройка UTM на кампанию
);

-- ================================================================
-- 4. СОЗДАНИЕ ТАБЛИЦЫ СТАТИСТИКИ КАМПАНИЙ
-- ================================================================

CREATE TABLE IF NOT EXISTS campaign_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    
    -- Статистика
    total_clicks INTEGER DEFAULT 0,           -- Общее количество кликов
    total_views INTEGER DEFAULT 0,            -- Общее количество просмотров
    total_spent DECIMAL(12, 2) DEFAULT 0.00,  -- Потрачено денег
    channels_count INTEGER DEFAULT 0,         -- Количество каналов в кампании
    posts_count INTEGER DEFAULT 0,            -- Количество размещенных постов
    
    -- Временные метки
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    UNIQUE(campaign_id)  -- Одна статистика на кампанию
);

-- ================================================================
-- 5. СОЗДАНИЕ ИНДЕКСОВ ДЛЯ ОПТИМИЗАЦИИ
-- ================================================================

-- Индексы для campaigns
CREATE INDEX IF NOT EXISTS idx_campaigns_created_by ON campaigns(created_by);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_start_date ON campaigns(start_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_end_date ON campaigns(end_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_advertiser_id ON campaigns(advertiser_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_related_offer_id ON campaigns(related_offer_id);

-- Индексы для campaign_advertisers
CREATE INDEX IF NOT EXISTS idx_campaign_advertisers_status ON campaign_advertisers(status);
CREATE INDEX IF NOT EXISTS idx_campaign_advertisers_inn ON campaign_advertisers(inn);

-- Индексы для campaign_utm_settings
CREATE INDEX IF NOT EXISTS idx_campaign_utm_campaign_id ON campaign_utm_settings(campaign_id);

-- Индексы для campaign_statistics
CREATE INDEX IF NOT EXISTS idx_campaign_statistics_campaign_id ON campaign_statistics(campaign_id);

-- ================================================================
-- 6. СОЗДАНИЕ ТРИГГЕРОВ ДЛЯ АВТОМАТИЗАЦИИ
-- ================================================================

-- Триггер для обновления updated_at в campaigns
CREATE TRIGGER IF NOT EXISTS update_campaigns_updated_at
    AFTER UPDATE ON campaigns
    FOR EACH ROW
BEGIN
    UPDATE campaigns 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Триггер для обновления updated_at в campaign_advertisers
CREATE TRIGGER IF NOT EXISTS update_campaign_advertisers_updated_at
    AFTER UPDATE ON campaign_advertisers
    FOR EACH ROW
BEGIN
    UPDATE campaign_advertisers 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Триггер для обновления updated_at в campaign_utm_settings
CREATE TRIGGER IF NOT EXISTS update_campaign_utm_updated_at
    AFTER UPDATE ON campaign_utm_settings
    FOR EACH ROW
BEGIN
    UPDATE campaign_utm_settings 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Триггер для создания UTM настроек по умолчанию
CREATE TRIGGER IF NOT EXISTS create_default_utm_settings
    AFTER INSERT ON campaigns
    FOR EACH ROW
    WHEN NEW.add_utm_tags = 1
BEGIN
    INSERT INTO campaign_utm_settings (
        campaign_id, 
        utm_campaign,
        utm_source,
        utm_medium
    ) VALUES (
        NEW.id,
        NEW.name,
        'telegram',
        'channel'
    );
END;

-- Триггер для создания статистики по умолчанию
CREATE TRIGGER IF NOT EXISTS create_default_campaign_statistics
    AFTER INSERT ON campaigns
    FOR EACH ROW
BEGIN
    INSERT INTO campaign_statistics (campaign_id) VALUES (NEW.id);
END;

-- ================================================================
-- 7. ЗАПОЛНЕНИЕ ТЕСТОВЫХ ДАННЫХ
-- ================================================================

-- Добавляем несколько тестовых рекламодателей
INSERT OR IGNORE INTO campaign_advertisers (name, inn, contact_person, email) VALUES 
('ООО "Технологии будущего"', '7707083893', 'Иванов Иван Иванович', 'ivanov@techfuture.ru'),
('ИП Петров А.В.', '123456789012', 'Петров Алексей Владимирович', 'petrov@example.com'),
('ООО "Финансовые решения"', '7707123456', 'Сидорова Мария Петровна', 'sidorova@finsolve.ru'),
('Агентство "Креатив Медиа"', '7707987654', 'Козлов Дмитрий Сергеевич', 'kozlov@creative-media.ru');

-- ================================================================
-- 8. СОЗДАНИЕ ПРЕДСТАВЛЕНИЙ ДЛЯ УДОБСТВА
-- ================================================================

-- Представление для полной информации о кампаниях
CREATE VIEW IF NOT EXISTS v_campaigns_full AS
SELECT 
    c.id,
    c.name,
    c.budget_limit,
    c.add_utm_tags,
    c.track_clicks,
    c.start_date,
    c.end_date,
    c.work_weekends,
    c.work_hours_only,
    c.product_name,
    c.advertiser_inn,
    c.ad_content,
    c.status,
    c.created_at,
    c.updated_at,
    c.related_offer_id,
    
    -- Информация о рекламодателе
    COALESCE(ca.name, c.advertiser_custom) as advertiser_name,
    ca.contact_person as advertiser_contact,
    ca.email as advertiser_email,
    
    -- Статистика
    cs.total_clicks,
    cs.total_views,
    cs.total_spent,
    cs.channels_count,
    cs.posts_count,
    
    -- UTM настройки
    uts.utm_source,
    uts.utm_medium,
    uts.utm_campaign,
    uts.utm_term,
    uts.utm_content,
    
    -- Расчетные поля
    CASE 
        WHEN DATE('now') < c.start_date THEN 'scheduled'
        WHEN DATE('now') > c.end_date THEN 'expired'
        ELSE c.status 
    END as effective_status,
    
    julianday(c.end_date) - julianday(c.start_date) + 1 as duration_days,
    
    CASE 
        WHEN cs.total_clicks > 0 AND cs.total_spent > 0 THEN 
            ROUND(cs.total_spent / cs.total_clicks, 2)
        ELSE 0 
    END as cost_per_click

FROM campaigns c
LEFT JOIN campaign_advertisers ca ON c.advertiser_id = ca.id
LEFT JOIN campaign_statistics cs ON c.id = cs.campaign_id
LEFT JOIN campaign_utm_settings uts ON c.id = uts.campaign_id;

-- ================================================================
-- 9. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ
-- ================================================================

-- Проверяем, что все таблицы созданы корректно
SELECT 'Таблицы кампаний:' as info;
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'campaign%';

SELECT 'Индексы кампаний:' as info;
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%campaign%';

SELECT 'Триггеры кампаний:' as info;
SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%campaign%';

SELECT 'Представления кампаний:' as info;
SELECT name FROM sqlite_master WHERE type='view' AND name LIKE '%campaign%';

COMMIT;

-- ================================================================
-- КОНЕЦ МИГРАЦИИ
-- ================================================================

SELECT 'Миграция системы рекламных кампаний завершена успешно!' as result;