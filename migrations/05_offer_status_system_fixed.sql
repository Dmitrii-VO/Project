-- Миграция: Система статусов офферов (исправленная версия)
-- Версия: 1.4
-- Дата: 2025-07-21

-- Добавляем только недостающие поля (status уже существует)
ALTER TABLE offers ADD COLUMN submitted_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN rejected_at TIMESTAMP;
ALTER TABLE offers ADD COLUMN rejection_reason TEXT;
ALTER TABLE offers ADD COLUMN user_id INTEGER; -- Для связи с пользователем

-- Обновляем существующие офферы: меняем статус с 'active' на 'draft'
UPDATE offers SET status = 'draft' WHERE status = 'active';

-- Создаем индекс для быстрого поиска по статусу
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);

-- Создаем индекс для модерации (поиск pending офферов по дате создания)
CREATE INDEX IF NOT EXISTS idx_offers_pending_created ON offers(status, created_at);

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