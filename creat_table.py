#!/usr/bin/env python3
"""
Скрипт пересоздания таблицы offer_proposals
"""

import os
import sqlite3

DATABASE_PATH = os.getenv('DATABASE_PATH', 'telegram_mini_app.db')

def recreate_offer_proposals_table():
    """Удаление и создание таблицы offer_proposals заново"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("Удаление старой таблицы offer_proposals...")
        cursor.execute("DROP TABLE IF EXISTS offer_proposals")
        
        print("Удаление индексов...")
        cursor.execute("DROP INDEX IF EXISTS idx_offer_proposals_offer_id")
        cursor.execute("DROP INDEX IF EXISTS idx_offer_proposals_channel_id")
        cursor.execute("DROP INDEX IF EXISTS idx_offer_proposals_status")
        cursor.execute("DROP INDEX IF EXISTS idx_offer_proposals_created_at")
        cursor.execute("DROP INDEX IF EXISTS idx_offer_proposals_expires_at")
        
        print("Создание новой таблицы offer_proposals...")
        
        cursor.execute("""
            CREATE TABLE offer_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'accepted', 'rejected', 'expired', 'cancelled')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME DEFAULT NULL,
                rejection_reason TEXT DEFAULT NULL,
                expires_at DATETIME DEFAULT (datetime('now', '+7 days')),
                notified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reminder_sent_at DATETIME DEFAULT NULL,
                response_message TEXT DEFAULT NULL,
                proposed_price DECIMAL(12, 2) DEFAULT NULL,
                
                FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
                
                UNIQUE(offer_id, channel_id)
            )
        """)
        
        print("Создание индексов...")
        cursor.execute("CREATE INDEX idx_offer_proposals_offer_id ON offer_proposals(offer_id)")
        cursor.execute("CREATE INDEX idx_offer_proposals_channel_id ON offer_proposals(channel_id)")
        cursor.execute("CREATE INDEX idx_offer_proposals_status ON offer_proposals(status)")
        cursor.execute("CREATE INDEX idx_offer_proposals_created_at ON offer_proposals(created_at)")
        cursor.execute("CREATE INDEX idx_offer_proposals_expires_at ON offer_proposals(expires_at)")
        
        conn.commit()
        conn.close()
        
        print("✅ Таблица offer_proposals пересоздана успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    recreate_offer_proposals_table()