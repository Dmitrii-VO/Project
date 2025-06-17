#!/usr/bin/env python3
"""
Скрипт для проверки структуры таблицы channels
"""

import os
import sqlite3

DATABASE_PATH = 'telegram_mini_app.db'

def check_channels_table_structure():
    """Проверка структуры таблицы channels"""
    
    print("🔍 ПРОВЕРКА СТРУКТУРЫ ТАБЛИЦЫ CHANNELS")
    print("=" * 50)
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='channels'
        """)
        
        if not cursor.fetchone():
            print("❌ Таблица 'channels' не найдена!")
            return False
        
        # Получаем структуру таблицы
        cursor.execute("PRAGMA table_info(channels)")
        columns = cursor.fetchall()
        
        print("📋 СТРУКТУРА ТАБЛИЦЫ 'channels':")
        print("-" * 50)
        print(f"{'#':<3} {'Название поля':<25} {'Тип':<15} {'NOT NULL':<10} {'Значение по умолчанию'}")
        print("-" * 50)
        
        for col in columns:
            cid, name, data_type, not_null, default_value, pk = col
            not_null_str = "YES" if not_null else "NO"
            default_str = str(default_value) if default_value else ""
            print(f"{cid:<3} {name:<25} {data_type:<15} {not_null_str:<10} {default_str}")
        
        print("-" * 50)
        print(f"Всего полей: {len(columns)}")
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM channels")
        count = cursor.fetchone()[0]
        print(f"Записей в таблице: {count}")
        
        # Показываем несколько примеров записей если есть
        if count > 0:
            print(f"\n📄 ПРИМЕРЫ ЗАПИСЕЙ (первые 3):")
            cursor.execute("SELECT * FROM channels LIMIT 3")
            records = cursor.fetchall()
            
            for i, record in enumerate(records, 1):
                print(f"\nЗапись {i}:")
                for j, (col_info, value) in enumerate(zip(columns, record)):
                    col_name = col_info[1]
                    print(f"  {col_name}: {value}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == '__main__':
    check_channels_table_structure()