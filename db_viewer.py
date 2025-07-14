#!/usr/bin/env python3
"""
Скрипт для точной проверки структуры таблиц БД
Показывает все поля в таблицах для правильного составления SQL запросов
"""

import sqlite3
import os

DB_PATH = 'telegram_mini_app.db'

def get_table_structure(table_name):
    """Получить структуру конкретной таблицы"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        conn.close()
        return columns
    except Exception as e:
        print(f"❌ Ошибка получения структуры {table_name}: {e}")
        return []

def check_required_tables_for_proposals():
    """Проверить структуру таблиц нужных для proposals/incoming"""
    print("🔍 ПРОВЕРКА СТРУКТУРЫ ТАБЛИЦ ДЛЯ API /proposals/incoming")
    print("=" * 70)
    
    required_tables = ['offer_proposals', 'channels', 'offers', 'users']
    
    for table in required_tables:
        print(f"\n📋 ТАБЛИЦА: {table.upper()}")
        print("-" * 50)
        
        columns = get_table_structure(table)
        
        if not columns:
            print(f"❌ Таблица {table} не найдена!")
            continue
            
        print("Доступные поля:")
        for i, col in enumerate(columns):
            # (cid, name, type, notnull, dflt_value, pk)
            name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else "NULL"
            default = f"DEFAULT {col[4]}" if col[4] is not None else ""
            
            print(f"  {i:2d}. {name:<25} {col_type:<15} {not_null:<8} {default}")

def create_correct_sql_query():
    """Создать правильный SQL запрос на основе реальной структуры"""
    print("\n🔧 СОЗДАНИЕ ПРАВИЛЬНОГО SQL ЗАПРОСА")
    print("=" * 70)
    
    # Проверяем какие поля есть в offers
    offers_columns = get_table_structure('offers')
    offers_fields = [col[1] for col in offers_columns] if offers_columns else []
    
    # Проверяем какие поля есть в other tables
    proposals_columns = get_table_structure('offer_proposals')
    proposals_fields = [col[1] for col in proposals_columns] if proposals_columns else []
    
    channels_columns = get_table_structure('channels')
    channels_fields = [col[1] for col in channels_columns] if channels_columns else []
    
    users_columns = get_table_structure('users')
    users_fields = [col[1] for col in users_columns] if users_columns else []
    
    print("\n✅ ДОСТУПНЫЕ ПОЛЯ ПО ТАБЛИЦАМ:")
    print(f"offers: {offers_fields}")
    print(f"offer_proposals: {proposals_fields}")  
    print(f"channels: {channels_fields}")
    print(f"users: {users_fields}")
    
    # Создаем правильный запрос
    print("\n📝 ПРАВИЛЬНЫЙ SQL ЗАПРОС:")
    print("-" * 50)
    
    # Основные поля offer_proposals
    select_fields = [
        "-- Основные поля предложения",
        "op.id, op.offer_id, op.channel_id, op.status",
        "op.created_at, op.responded_at, op.expires_at",
        "op.rejection_reason, op.notified_at"
    ]
    
    # Поля offers (только существующие)
    offers_safe_fields = []
    if 'title' in offers_fields:
        offers_safe_fields.append("o.title as offer_title")
    if 'description' in offers_fields:
        offers_safe_fields.append("o.description as offer_description")
    if 'budget_total' in offers_fields:
        offers_safe_fields.append("o.budget_total as offer_budget")
    elif 'price' in offers_fields:
        offers_safe_fields.append("o.price as offer_budget")
    if 'content' in offers_fields:
        offers_safe_fields.append("o.content as offer_content")
    if 'requirements' in offers_fields:
        offers_safe_fields.append("o.requirements as placement_requirements")
    if 'duration_days' in offers_fields:
        offers_safe_fields.append("o.duration_days as placement_duration")
    if 'expected_placement_duration' in offers_fields:
        offers_safe_fields.append("o.expected_placement_duration")
    if 'category' in offers_fields:
        offers_safe_fields.append("o.category as offer_category")
    if 'target_audience' in offers_fields:
        offers_safe_fields.append("o.target_audience")
    if 'currency' in offers_fields:
        offers_safe_fields.append("o.currency")
    
    if offers_safe_fields:
        select_fields.append("-- Информация об оффере")
        select_fields.extend(offers_safe_fields)
    
    # Поля channels (только существующие)
    channels_safe_fields = []
    if 'title' in channels_fields:
        channels_safe_fields.append("c.title as channel_title")
    if 'username' in channels_fields:
        channels_safe_fields.append("c.username as channel_username")
    if 'subscriber_count' in channels_fields:
        channels_safe_fields.append("c.subscriber_count")
    if 'category' in channels_fields:
        channels_safe_fields.append("c.category as channel_category")
    
    if channels_safe_fields:
        select_fields.append("-- Информация о канале") 
        select_fields.extend(channels_safe_fields)
    
    # Поля users (только существующие)
    users_safe_fields = []
    if 'username' in users_fields:
        users_safe_fields.append("u.username as advertiser_username")
    if 'first_name' in users_fields:
        users_safe_fields.append("u.first_name as advertiser_first_name")
    if 'last_name' in users_fields:
        users_safe_fields.append("u.last_name as advertiser_last_name")
    
    if users_safe_fields:
        select_fields.append("-- Информация о создателе оффера")
        select_fields.extend(users_safe_fields)
    
    # Вычисляемые поля
    select_fields.extend([
        "-- Дополнительная информация",
        "CASE WHEN op.expires_at < datetime('now') THEN 1 ELSE 0 END as is_expired",
        "CASE WHEN op.expires_at > datetime('now') THEN CAST((julianday(op.expires_at) - julianday('now')) * 24 AS INTEGER) ELSE 0 END as hours_until_expiry"
    ])
    
    # Формируем полный запрос
    sql_query = f"""
SELECT 
    {','.join([f'    {field}' for field in select_fields if not field.startswith('--')])}
FROM offer_proposals op
JOIN channels c ON op.channel_id = c.id
JOIN offers o ON op.offer_id = o.id
JOIN users u ON o.created_by = u.id
WHERE c.owner_id = ?
ORDER BY 
    CASE op.status
        WHEN 'sent' THEN 1
        WHEN 'accepted' THEN 2
        WHEN 'rejected' THEN 3
        WHEN 'expired' THEN 4
        ELSE 5
    END,
    op.created_at DESC
LIMIT ? OFFSET ?
"""
    
    print(sql_query)
    return sql_query

def test_sql_query():
    """Тестировать созданный SQL запрос"""
    print("\n🧪 ТЕСТИРОВАНИЕ SQL ЗАПРОСА")
    print("=" * 70)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Простой тест запроса
        test_query = create_correct_sql_query()
        
        # Заменяем параметры на тестовые значения
        test_query_with_params = test_query.replace('?', '1', 1).replace('?', '10', 1).replace('?', '0', 1)
        
        cursor.execute(test_query_with_params)
        results = cursor.fetchall()
        
        print(f"✅ Запрос выполнен успешно!")
        print(f"📊 Найдено записей: {len(results)}")
        
        if results and len(results) > 0:
            print("\n📋 Пример первой записи:")
            # Получаем названия колонок
            cursor.execute("SELECT * FROM offer_proposals LIMIT 0")
            col_names = [description[0] for description in cursor.description]
            
            for i, value in enumerate(results[0]):
                if i < len(col_names):
                    print(f"  {col_names[i]}: {value}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def main():
    """Основная функция"""
    print("🔍 АНАЛИЗ СТРУКТУРЫ БД ДЛЯ PROPOSALS/INCOMING API")
    print("=" * 70)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return
    
    print(f"✅ База данных найдена: {DB_PATH}")
    
    # 1. Проверяем структуру всех нужных таблиц
    check_required_tables_for_proposals()
    
    # 2. Создаем правильный SQL запрос
    create_correct_sql_query()
    
    # 3. Тестируем запрос
    test_sql_query()
    
    print("\n🎯 РЕЗУЛЬТАТ:")
    print("- Проверена структура всех таблиц")
    print("- Создан SQL запрос только с существующими полями")
    print("- Протестирован запрос на реальных данных")
    print("\nТеперь можно обновить код в proposals_management.py!")

if __name__ == "__main__":
    main()