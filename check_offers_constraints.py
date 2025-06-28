#!/usr/bin/env python3
"""
Скрипт для проверки CHECK constraint в таблице offers
"""

import sqlite3

DATABASE_PATH = 'telegram_mini_app.db'

def check_offers_constraints():
    """Проверяет и показывает структуру таблицы offers"""
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Получаем SQL создания таблицы offers
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='offers'
        """)
        
        result = cursor.fetchone()
        if result:
            print("📋 SQL создания таблицы offers:")
            print("-" * 60)
            print(result[0])
            print("-" * 60)
            
            # Проверяем есть ли CHECK constraint
            if 'CHECK' in result[0]:
                print("⚠️  Найден CHECK constraint для статусов!")
                if "status IN" in result[0]:
                    # Извлекаем разрешенные статусы
                    import re
                    match = re.search(r"status IN \((.*?)\)", result[0])
                    if match:
                        allowed_statuses = match.group(1)
                        print(f"   Разрешенные статусы: {allowed_statuses}")
            else:
                print("✅ CHECK constraint для статусов не найден")
        
        # Проверяем текущие статусы в таблице
        cursor.execute("SELECT DISTINCT status FROM offers")
        statuses = cursor.fetchall()
        
        print(f"\n📊 Текущие статусы офферов в базе:")
        for status in statuses:
            cursor.execute("SELECT COUNT(*) FROM offers WHERE status = ?", (status[0],))
            count = cursor.fetchone()[0]
            print(f"   {status[0]}: {count} записей")
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(offers)")
        columns = cursor.fetchall()
        
        print(f"\n📋 Поля таблицы offers:")
        for col in columns:
            print(f"   {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'} {f'DEFAULT {col[4]}' if col[4] else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_offers_constraints()
