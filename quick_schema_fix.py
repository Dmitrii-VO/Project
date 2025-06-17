#!/usr/bin/env python3
"""
Быстрое исправление схемы базы данных для автоматической модерации
"""

import sqlite3
import os

DATABASE_PATH = 'telegram_mini_app.db'

def fix_channels_table():
    """Добавляет недостающие столбцы в таблицу channels"""
    print("🔧 Исправление схемы таблицы channels...")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Проверяем текущую структуру
        cursor.execute("PRAGMA table_info(channels)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Текущие столбцы: {columns}")
        
        changes = []
        
        # Добавляем verification_code
        if 'verification_code' not in columns:
            cursor.execute('ALTER TABLE channels ADD COLUMN verification_code TEXT')
            changes.append('verification_code')
            print("✅ Добавлен: verification_code")
        
        # Добавляем status
        if 'status' not in columns:
            cursor.execute("ALTER TABLE channels ADD COLUMN status TEXT DEFAULT 'pending'")
            changes.append('status')
            print("✅ Добавлен: status")
        
        # Добавляем verified_at
        if 'verified_at' not in columns:
            cursor.execute('ALTER TABLE channels ADD COLUMN verified_at DATETIME')
            changes.append('verified_at')
            print("✅ Добавлен: verified_at")
        
        if changes:
            # Обновляем существующие записи
            cursor.execute("""
                UPDATE channels 
                SET status = CASE 
                    WHEN is_verified = 1 THEN 'verified'
                    ELSE 'pending_verification'
                END
                WHERE status IS NULL
            """)
            
            conn.commit()
            print(f"✅ Изменения сохранены: {', '.join(changes)}")
        else:
            print("ℹ️ Все столбцы уже существуют")
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(channels)")
        updated_columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Обновленные столбцы: {updated_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_insert():
    """Тестирует вставку данных с новыми полями"""
    print("\n🧪 Тестирование вставки...")
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Пробуем вставить тестовую запись
        test_data = (
            'test_channel_id',
            'test_username', 
            'Тестовый канал',
            'Описание теста',
            1,  # owner_id
            'test',
            '2025-06-17T15:30:00',
            '#addtest456',
            'pending_verification'
        )
        
        cursor.execute("""
            INSERT INTO channels (
                telegram_id, username, title, description, owner_id,
                category, created_at, verification_code, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_data)
        
        conn.commit()
        print("✅ Тестовая вставка прошла успешно")
        
        # Удаляем тестовую запись
        cursor.execute("DELETE FROM channels WHERE telegram_id = 'test_channel_id'")
        conn.commit()
        print("✅ Тестовая запись удалена")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def main():
    print("=" * 50)
    print("🛠️ БЫСТРОЕ ИСПРАВЛЕНИЕ СХЕМЫ БД")
    print("=" * 50)
    
    if fix_channels_table():
        if test_insert():
            print("\n🎉 Схема успешно исправлена!")
            print("📋 Теперь можно добавлять каналы с автоматической модерацией")
        else:
            print("\n⚠️ Схема исправлена, но есть проблемы с тестированием")
    else:
        print("\n❌ Не удалось исправить схему")

if __name__ == '__main__':
    main()
