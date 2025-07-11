import sqlite3

conn = sqlite3.connect('telegram_mini_app.db')
cursor = conn.cursor()

# Добавляем недостающие колонки в offers
cursor.execute('ALTER TABLE offers ADD COLUMN selected_channels_count INTEGER DEFAULT 0;')
cursor.execute('ALTER TABLE offers ADD COLUMN expected_placement_duration INTEGER DEFAULT 7;')

# Пересоздаем offer_proposals с правильными колонками
cursor.execute('DROP TABLE IF EXISTS offer_proposals;')
cursor.execute('''
CREATE TABLE offer_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    status TEXT DEFAULT 'sent',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME DEFAULT NULL,
    notified_at DATETIME DEFAULT NULL,
    FOREIGN KEY (offer_id) REFERENCES offers(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);
''')

conn.commit()
conn.close()
print("✅ Все колонки добавлены!")