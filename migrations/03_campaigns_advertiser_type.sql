-- ================================================================
-- МИГРАЦИЯ БАЗЫ ДАННЫХ: Изменение типа рекламодателя в кампаниях
-- Версия: 3.0
-- Дата: 2025-07-20
-- ================================================================

-- Включаем проверку внешних ключей
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ================================================================
-- 1. ДОБАВЛЕНИЕ НОВОГО ПОЛЯ advertiser_type
-- ================================================================

-- Добавляем поле для типа рекламодателя
ALTER TABLE campaigns ADD COLUMN advertiser_type TEXT CHECK (advertiser_type IN ('legal_entity', 'individual_entrepreneur', 'physical_person'));

-- ================================================================
-- 2. ОБНОВЛЕНИЕ СУЩЕСТВУЮЩИХ ЗАПИСЕЙ
-- ================================================================

-- Устанавливаем значение по умолчанию для существующих записей
UPDATE campaigns 
SET advertiser_type = 'legal_entity' 
WHERE advertiser_type IS NULL;

-- ================================================================
-- 3. ОБНОВЛЕНИЕ ПРЕДСТАВЛЕНИЯ
-- ================================================================

-- Пересоздаем представление для кампаний с учетом нового поля
DROP VIEW IF EXISTS v_campaigns_full;

CREATE VIEW v_campaigns_full AS
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
    c.advertiser_type,
    c.product_name,
    c.advertiser_inn,
    c.ad_content,
    c.status,
    c.created_at,
    c.updated_at,
    c.related_offer_id,
    
    -- Текстовое представление типа рекламодателя
    CASE c.advertiser_type
        WHEN 'legal_entity' THEN 'Юридическое лицо'
        WHEN 'individual_entrepreneur' THEN 'Индивидуальный предприниматель'
        WHEN 'physical_person' THEN 'Физическое лицо'
        ELSE 'Не указан'
    END as advertiser_type_display,
    
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
LEFT JOIN campaign_statistics cs ON c.id = cs.campaign_id
LEFT JOIN campaign_utm_settings uts ON c.id = uts.campaign_id;

-- ================================================================
-- 4. СОЗДАНИЕ ИНДЕКСА ДЛЯ НОВОГО ПОЛЯ
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_campaigns_advertiser_type ON campaigns(advertiser_type);

COMMIT;

-- ================================================================
-- КОНЕЦ МИГРАЦИИ
-- ================================================================

SELECT 'Миграция типа рекламодателя завершена успешно!' as result;