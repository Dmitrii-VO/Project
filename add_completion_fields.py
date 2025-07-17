#!/usr/bin/env python3
"""
Добавляет недостающие поля для системы завершения размещений
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query

def add_completion_fields():
    """Добавляет недостающие поля для завершения размещений"""
    print("🔄 Добавление полей для системы завершения размещений...")
    
    try:
        # 1. Добавляем поля в offer_placements
        print("📝 Обновление таблицы offer_placements...")
        
        completion_fields = [
            "ALTER TABLE offer_placements ADD COLUMN final_stats TEXT",
            "ALTER TABLE offer_placements ADD COLUMN final_payout REAL DEFAULT 0"
        ]
        
        for field_sql in completion_fields:
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
        
        channel_completion_fields = [
            "ALTER TABLE channels ADD COLUMN completed_placements INTEGER DEFAULT 0",
            "ALTER TABLE channels ADD COLUMN total_earned REAL DEFAULT 0"
        ]
        
        for field_sql in channel_completion_fields:
            try:
                execute_db_query(field_sql)
                print(f"✅ Добавлено поле: {field_sql.split('ADD COLUMN')[1].split()[0]}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️ Поле уже существует: {field_sql.split('ADD COLUMN')[1].split()[0]}")
                else:
                    print(f"❌ Ошибка добавления поля: {e}")
        
        # 3. Создаем таблицу placement_reports
        print("📝 Создание таблицы placement_reports...")
        
        execute_db_query("""
            CREATE TABLE IF NOT EXISTS placement_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placement_id INTEGER NOT NULL,
                report_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (placement_id) REFERENCES offer_placements(id)
            )
        """)
        print("✅ Таблица placement_reports создана")
        
        # 4. Создаем индексы
        print("📝 Создание индексов...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_placement_reports_placement_id ON placement_reports(placement_id)",
            "CREATE INDEX IF NOT EXISTS idx_placement_reports_created_at ON placement_reports(created_at)"
        ]
        
        for index_sql in indexes:
            try:
                execute_db_query(index_sql)
                index_name = index_sql.split("INDEX IF NOT EXISTS")[1].split()[0]
                print(f"✅ Создан индекс: {index_name}")
            except Exception as e:
                print(f"❌ Ошибка создания индекса: {e}")
        
        print("🎉 Все поля для завершения размещений добавлены успешно!")
        
        # 5. Проверяем структуру таблиц
        print("\n📊 Проверка структуры таблиц:")
        
        # Проверяем offer_placements
        placement_columns = execute_db_query("PRAGMA table_info(offer_placements)", fetch_all=True)
        print(f"✅ offer_placements: {len(placement_columns)} колонок")
        
        # Проверяем channels
        channel_columns = execute_db_query("PRAGMA table_info(channels)", fetch_all=True)
        print(f"✅ channels: {len(channel_columns)} колонок")
        
        # Проверяем placement_reports
        reports_columns = execute_db_query("PRAGMA table_info(placement_reports)", fetch_all=True)
        print(f"✅ placement_reports: {len(reports_columns)} колонок")
        
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False


if __name__ == "__main__":
    success = add_completion_fields()
    if success:
        print("\n✅ Миграция завершена успешно!")
    else:
        print("\n❌ Миграция завершена с ошибками!")
        sys.exit(1)