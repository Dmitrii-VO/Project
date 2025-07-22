-- Миграция: Система статусов офферов
-- Версия: 1.4
-- Дата: 2025-07-21

-- Добавляем новые поля в таблицу offers
ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'pending', 'active', 'rejected'));
ALTER TABLE offers ADD COLUMN submitted_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN rejected_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN rejection_reason TEXT;

-- Обновляем существующие офферы
UPDATE offers SET status = 'draft' WHERE status IS NULL;

-- Создаем индекс для быстрого поиска по статусу
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);

-- Создаем индекс для модерации (поиск pending офферов по дате создания)
CREATE INDEX IF NOT EXISTS idx_offers_pending_created ON offers(status, created_at) WHERE status = 'pending';

-- Создаем таблицу для логирования изменений статусов
CREATE TABLE IF NOT EXISTS offer_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by INTEGER NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
);

-- Индекс для логов
CREATE INDEX IF NOT EXISTS idx_status_log_offer ON offer_status_log(offer_id, changed_at);