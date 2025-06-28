#!/usr/bin/env python3
"""
Скрипт для проверки и исправления структуры базы данных
"""

import sqlite3
import os

# Путь к базе данных
DATABASE_PATH = 'telegram_mini_app.db'

def check_and_fix_database():
    """Проверяет и исправляет структуру базы данных"""
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных {DATABASE_PATH} не найдена!")
        return
    
    print(f"🔍 Проверка базы данных: {DATABASE_PATH}")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 1. Проверяем структуру таблицы offer_responses
        print("\n📋 Проверка структуры таблицы 'offer_responses':")
        cursor.execute("PRAGMA table_info(offer_responses)")
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ Таблица 'offer_responses' не найдена!")
            return
        
        print("   Существующие поля:")
        column_names = []
        for col in columns:
            column_names.append(col[1])
            print(f"   - {col[1]} ({col[2]})")
        
        # 2. Проверяем наличие поля channel_id
        if 'channel_id' in column_names:
            print("✅ Поле 'channel_id' уже существует!")
        else:
            print("⚠️  Поле 'channel_id' отсутствует. Добавляем...")
            
            try:
                cursor.execute("ALTER TABLE offer_responses ADD COLUMN channel_id INTEGER")
                conn.commit()
                print("✅ Поле 'channel_id' успешно добавлено!")
            except sqlite3.Error as e:
                print(f"❌ Ошибка при добавлении поля: {e}")
        
        # 3. Проверяем структуру таблицы contracts
        print("\n📋 Проверка структуры таблицы 'contracts':")
        cursor.execute("PRAGMA table_info(contracts)")
        contracts_columns = cursor.fetchall()
        
        if contracts_columns:
            print("   Поля таблицы contracts:")
            for col in contracts_columns:
                print(f"   - {col[1]} ({col[2]})")
        else:
            print("❌ Таблица 'contracts' не найдена!")
        
        # 4. Показываем статистику
        print("\n📊 Статистика базы данных:")
        
        # Количество офферов
        cursor.execute("SELECT COUNT(*) FROM offers")
        offers_count = cursor.fetchone()[0]
        print(f"   Офферов: {offers_count}")
        
        # Количество откликов
        cursor.execute("SELECT COUNT(*) FROM offer_responses")
        responses_count = cursor.fetchone()[0]
        print(f"   Откликов: {responses_count}")
        
        # Количество контрактов (если таблица существует)
        try:
            cursor.execute("SELECT COUNT(*) FROM contracts")
            contracts_count = cursor.fetchone()[0]
            print(f"   Контрактов: {contracts_count}")
        except sqlite3.Error:
            print("   Контрактов: таблица не существует")
        
        # 5. Проверяем отклики без channel_id
        if 'channel_id' in column_names:
            cursor.execute("SELECT COUNT(*) FROM offer_responses WHERE channel_id IS NULL")
            null_channel_count = cursor.fetchone()[0]
            if null_channel_count > 0:
                print(f"⚠️  Найдено {null_channel_count} откликов без channel_id")
                print("   Это нормально для старых откликов.")
        
        conn.close()
        print("\n✅ Проверка завершена!")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    print("🛠️  Утилита проверки и исправления базы данных")
    print("=" * 50)
    check_and_fix_database()
