#!/usr/bin/env python3
"""
Добавляет недостающие поля для системы мониторинга
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig

def add_monitoring_fields():
    """Добавляет недостающие поля для мониторинга"""
    print("🔄 Добавление полей для системы мониторинга...")
    
    try:
        # 1. Добавляем поля в offer_placements
        print("📝 Обновление таблицы offer_placements...")
        
        monitoring_fields = [
            "ALTER TABLE offer_placements ADD COLUMN warning_sent INTEGER DEFAULT 0",
            "ALTER TABLE offer_placements ADD COLUMN early_deletion_penalty REAL DEFAULT 0",
            "ALTER TABLE offer_placements ADD COLUMN actual_end_time TIMESTAMP",
            "ALTER TABLE offer_placements ADD COLUMN penalty_reason TEXT",
            "ALTER TABLE offer_placements ADD COLUMN refund_processed INTEGER DEFAULT 0",
            "ALTER TABLE offer_placements ADD COLUMN refund_amount REAL DEFAULT 0",
            "ALTER TABLE offer_placements ADD COLUMN refund_at TIMESTAMP"
        ]
        
        for field_sql in monitoring_fields:
            try:
                execute_db_query(field_sql)
                print(f"✅ Добавлено поле: {field_sql.split('ADD COLUMN')[1].split()[0]}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️ Поле уже существует: {field_sql.split('ADD COLUMN')[1].split()[0]}")
                else:
                    print(f"❌ Ошибка добавления поля: {e}")
        
        # 2. Добавляем поля в channels
        print("📝 Обновление таблицы channels...")
        
        channel_fields = [
            "ALTER TABLE channels ADD COLUMN failed_placements INTEGER DEFAULT 0",
            "ALTER TABLE channels ADD COLUMN early_deletions INTEGER DEFAULT 0",
            "ALTER TABLE channels ADD COLUMN reliability_rating REAL DEFAULT 100"
        ]
        
        for field_sql in channel_fields:
            try:
                execute_db_query(field_sql)
                print(f"✅ Добавлено поле: {field_sql.split('ADD COLUMN')[1].split()[0]}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️ Поле уже существует: {field_sql.split('ADD COLUMN')[1].split()[0]}")
                else:
                    print(f"❌ Ошибка добавления поля: {e}")
        
        # 3. Создаем таблицу ereit_statistics
        print("📝 Создание таблицы ereit_statistics...")
        
        execute_db_query("""
            CREATE TABLE IF NOT EXISTS ereit_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placement_id INTEGER NOT NULL,
                ereit_token TEXT NOT NULL,
                clicks INTEGER DEFAULT 0,
                unique_clicks INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                button_clicks INTEGER DEFAULT 0,
                link_clicks INTEGER DEFAULT 0,
                phone_clicks INTEGER DEFAULT 0,
                email_clicks INTEGER DEFAULT 0,
                social_clicks INTEGER DEFAULT 0,
                conversion_events INTEGER DEFAULT 0,
                first_click_at TIMESTAMP,
                last_click_at TIMESTAMP,
                collected_at TIMESTAMP,
                source TEXT DEFAULT 'ereit_api',
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (placement_id) REFERENCES offer_placements(id)
            )
        """)
        print("✅ Таблица ereit_statistics создана")
        
        # 4. Создаем индексы для производительности
        print("📝 Создание индексов...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ereit_stats_placement_id ON ereit_statistics(placement_id)",
            "CREATE INDEX IF NOT EXISTS idx_ereit_stats_token ON ereit_statistics(ereit_token)",
            "CREATE INDEX IF NOT EXISTS idx_ereit_stats_collected_at ON ereit_statistics(collected_at)",
            "CREATE INDEX IF NOT EXISTS idx_placements_status ON offer_placements(status)",
            "CREATE INDEX IF NOT EXISTS idx_placements_deadline ON offer_placements(deadline)",
            "CREATE INDEX IF NOT EXISTS idx_placements_warning_sent ON offer_placements(warning_sent)"
        ]
        
        for index_sql in indexes:
            try:
                execute_db_query(index_sql)
                index_name = index_sql.split("INDEX IF NOT EXISTS")[1].split()[0]
                print(f"✅ Создан индекс: {index_name}")
            except Exception as e:
                print(f"❌ Ошибка создания индекса: {e}")
        
        print("🎉 Все поля для мониторинга добавлены успешно!")
        
        # 5. Проверяем структуру таблиц
        print("\n📊 Проверка структуры таблиц:")
        
        # Проверяем offer_placements
        placement_columns = execute_db_query("PRAGMA table_info(offer_placements)", fetch_all=True)
        print(f"✅ offer_placements: {len(placement_columns)} колонок")
        
        # Проверяем channels
        channel_columns = execute_db_query("PRAGMA table_info(channels)", fetch_all=True)
        print(f"✅ channels: {len(channel_columns)} колонок")
        
        # Проверяем ereit_statistics
        ereit_columns = execute_db_query("PRAGMA table_info(ereit_statistics)", fetch_all=True)
        print(f"✅ ereit_statistics: {len(ereit_columns)} колонок")
        
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


if __name__ == "__main__":
    success = add_monitoring_fields()
    if success:
        print("\n✅ Миграция завершена успешно!")
    else:
        print("\n❌ Миграция завершена с ошибками!")
        sys.exit(1)