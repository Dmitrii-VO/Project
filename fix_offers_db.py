#!/usr/bin/env python3
"""
Скрипт для исправления таблицы offers - добавление недостающих полей
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = 'telegram_mini_app.db'

def get_current_table_structure():
    """Получаем текущую структуру таблицы offers"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(offers)")
        columns = cursor.fetchall()
        print("🔍 ТЕКУЩАЯ СТРУКТУРА ТАБЛИЦЫ 'offers':")
        print("-" * 60)
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - NOT NULL: {bool(col[3])}, DEFAULT: {col[4]}")
        print("-" * 60)
        return [col[1] for col in columns]  # Возвращаем список имен полей
        
    except Exception as e:
        print(f"❌ Ошибка получения структуры: {e}")
        return []
    finally:
        conn.close()

def add_missing_columns():
    """Добавляем недостающие поля в таблицу offers"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Список полей которые нужно добавить
    new_columns = [
        ("category", "TEXT DEFAULT 'general'"),
        ("metadata", "TEXT DEFAULT '{}'"),
        ("budget_total", "DECIMAL(12, 2) DEFAULT 0"),
        ("expires_at", "DATETIME"),
        ("duration_days", "INTEGER DEFAULT 30"),
        ("min_subscribers", "INTEGER DEFAULT 1"),
        ("max_subscribers", "INTEGER DEFAULT 100000000")
    ]
    
    try:
        # Получаем существующие поля
        existing_columns = get_current_table_structure()
        
        print("\n🔧 ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ ПОЛЕЙ:")
        print("-" * 60)
        
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE offers ADD COLUMN {column_name} {column_definition}"
                    print(f"  ➕ Добавляем поле: {column_name}")
                    cursor.execute(sql)
                    print(f"     ✅ {sql}")
                except Exception as e:
                    print(f"     ❌ Ошибка добавления {column_name}: {e}")
            else:
                print(f"  ⏭️ Поле {column_name} уже существует")
        
        conn.commit()
        print("\n✅ Все поля успешно добавлены!")
        
    except Exception as e:
        print(f"❌ Ошибка добавления полей: {e}")
        conn.rollback()
    finally:
        conn.close()

def verify_table_structure():
    """Проверяем итоговую структуру таблицы"""
    print("\n🔍 ИТОГОВАЯ СТРУКТУРА ТАБЛИЦЫ 'offers':")
    print("=" * 70)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(offers)")
        columns = cursor.fetchall()
        
        print(f"{'#':<3} {'Поле':<20} {'Тип':<20} {'NOT NULL':<10} {'DEFAULT':<15}")
        print("-" * 70)
        
        for i, col in enumerate(columns):
            not_null = "YES" if col[3] else "NO"
            default = str(col[4]) if col[4] is not None else ""
            print(f"{i:<3} {col[1]:<20} {col[2]:<20} {not_null:<10} {default:<15}")
        
        print("-" * 70)
        print(f"Всего полей: {len(columns)}")
        
        return len(columns)
        
    except Exception as e:
        print(f"❌ Ошибка проверки структуры: {e}")
        return 0
    finally:
        conn.close()

def test_insert_offer():
    """Тестируем создание оффера с новыми полями"""
    print("\n🧪 ТЕСТ СОЗДАНИЯ ОФФЕРА:")
    print("-" * 40)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Получаем ID первого пользователя
        cursor.execute("SELECT id FROM users LIMIT 1")
        user_result = cursor.fetchone()
        
        if not user_result:
            print("❌ Пользователи не найдены для тестирования")
            return False
        
        user_id = user_result[0]
        
        # Тестовые данные оффера
        test_offer = {
            'title': 'Тестовый оффер',
            'description': 'Описание тестового оффера для проверки работы системы',
            'content': 'Полное содержание тестового оффера с подробным описанием',
            'price': 1000.00,
            'currency': 'RUB',
            'category': 'test',
            'target_audience': 'Тестовая аудитория',
            'requirements': 'Требования к размещению',
            'deadline': '2025-07-25',
            'status': 'active',
            'created_by': user_id,
            'metadata': '{"test": true}',
            'duration_days': 30,
            'min_subscribers': 100,
            'max_subscribers': 10000
        }
        
        # SQL для вставки
        sql = '''
        INSERT INTO offers (
            title, description, content, price, currency, category,
            target_audience, requirements, deadline, status, created_by,
            metadata, duration_days, min_subscribers, max_subscribers
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        values = (
            test_offer['title'], test_offer['description'], test_offer['content'],
            test_offer['price'], test_offer['currency'], test_offer['category'],
            test_offer['target_audience'], test_offer['requirements'],
            test_offer['deadline'], test_offer['status'], test_offer['created_by'],
            test_offer['metadata'], test_offer['duration_days'],
            test_offer['min_subscribers'], test_offer['max_subscribers']
        )
        
        cursor.execute(sql, values)
        offer_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Тестовый оффер создан с ID: {offer_id}")
        
        # Проверяем созданный оффер
        cursor.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
        created_offer = cursor.fetchone()
        
        if created_offer:
            print("📋 Данные созданного оффера:")
            cursor.execute("PRAGMA table_info(offers)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for i, value in enumerate(created_offer):
                if i < len(columns):
                    print(f"   {columns[i]}: {value}")
            
            return True
        else:
            print("❌ Не удалось найти созданный оффер")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Главная функция"""
    print("🔧 ИСПРАВЛЕНИЕ ТАБЛИЦЫ OFFERS")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🗄️ База данных: {DATABASE_PATH}")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return
    
    # Шаг 1: Показываем текущую структуру
    current_columns = get_current_table_structure()
    
    if not current_columns:
        print("❌ Не удалось получить структуру таблицы")
        return
    
    # Шаг 2: Добавляем недостающие поля
    add_missing_columns()
    
    # Шаг 3: Проверяем итоговую структуру
    final_count = verify_table_structure()
    
    # Шаг 4: Тестируем создание оффера
    if final_count > len(current_columns):
        print(f"\n✅ УСПЕШНО! Добавлено {final_count - len(current_columns)} новых полей")
        
        # Тестируем
        if test_insert_offer():
            print("\n🎉 ВСЕ ГОТОВО! Таблица offers исправлена и протестирована")
        else:
            print("\n⚠️ Структура обновлена, но тест не прошел")
    else:
        print("\n⚠️ Новые поля не были добавлены")

if __name__ == '__main__':
    main()