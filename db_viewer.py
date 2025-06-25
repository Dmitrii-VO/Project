#!/usr/bin/env python3
"""
Скрипт для просмотра структуры и содержимого базы данных Telegram Mini App
Поддерживает SQLite и PostgreSQL
"""

import os
import sys
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем системные переменные")

# Конфигурация
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
SQLITE_PATH = 'telegram_mini_app.db'


def get_database_type():
    """Определяем тип базы данных"""
    if DATABASE_URL.startswith('sqlite'):
        return 'sqlite'
    elif DATABASE_URL.startswith('postgresql'):
        return 'postgresql'
    else:
        return 'unknown'


def get_sqlite_connection():
    """Подключение к SQLite"""
    try:
        # Пробуем разные пути к БД
        possible_paths = [
            SQLITE_PATH,
            'telegram_mini_app.db',
            os.path.join(os.getcwd(), 'telegram_mini_app.db'),
            DATABASE_URL.replace('sqlite:///', ''),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"📁 Найдена база данных: {path}")
                conn = sqlite3.connect(path)
                conn.row_factory = sqlite3.Row  # Для именованных столбцов
                return conn, path
        
        print(f"❌ База данных SQLite не найдена в путях: {possible_paths}")
        return None, None
        
    except Exception as e:
        print(f"❌ Ошибка подключения к SQLite: {e}")
        return None, None


def get_postgresql_connection():
    """Подключение к PostgreSQL"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        url = urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            host=url.hostname or 'localhost',
            port=url.port or 5432,
            database=url.path[1:] if url.path else 'postgres',
            user=url.username or 'postgres',
            password=url.password or 'password',
            cursor_factory=RealDictCursor
        )
        return conn, DATABASE_URL
        
    except ImportError:
        print("❌ psycopg2 не установлен для работы с PostgreSQL")
        return None, None
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return None, None


def get_database_connection():
    """Получаем подключение к базе данных"""
    db_type = get_database_type()
    
    print(f"🗄️ Тип базы данных: {db_type}")
    print(f"🔗 URL подключения: {DATABASE_URL}")
    
    if db_type == 'sqlite':
        return get_sqlite_connection()
    elif db_type == 'postgresql':
        return get_postgresql_connection()
    else:
        print(f"❌ Неподдерживаемый тип БД: {db_type}")
        return None, None


def get_tables_list(conn, db_type):
    """Получаем список таблиц"""
    cursor = conn.cursor()
    
    try:
        if db_type == 'sqlite':
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
        else:  # PostgreSQL
            cursor.execute("""
                SELECT tablename as name FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
        
        tables = [row[0] if isinstance(row, tuple) else row['name'] for row in cursor.fetchall()]
        return tables
        
    except Exception as e:
        print(f"❌ Ошибка получения списка таблиц: {e}")
        return []


def get_table_schema(conn, table_name, db_type):
    """Получаем схему таблицы"""
    cursor = conn.cursor()
    
    try:
        if db_type == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema = []
            for col in columns:
                schema.append({
                    'column': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'primary_key': bool(col[5])
                })
        else:  # PostgreSQL
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = cursor.fetchall()
            schema = []
            for col in columns:
                schema.append({
                    'column': col[0],
                    'type': col[1],
                    'not_null': col[2] == 'NO',
                    'default': col[3],
                    'primary_key': False  # Нужен отдельный запрос для PK
                })
        
        return schema
        
    except Exception as e:
        print(f"❌ Ошибка получения схемы таблицы {table_name}: {e}")
        return []


def get_table_count(conn, table_name):
    """Получаем количество записей в таблице"""
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        return count
        
    except Exception as e:
        print(f"❌ Ошибка подсчета записей в {table_name}: {e}")
        return 0


def get_table_sample(conn, table_name, limit=5):
    """Получаем примеры записей из таблицы"""
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cursor.fetchall()
        
        # Преобразуем в список словарей
        if rows:
            if hasattr(rows[0], 'keys'):  # sqlite3.Row или psycopg2.RealDictRow
                return [dict(row) for row in rows]
            else:  # обычные кортежи
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        
        return []
        
    except Exception as e:
        print(f"❌ Ошибка получения примеров из {table_name}: {e}")
        return []


def print_table_info(conn, table_name, db_type):
    """Выводим детальную информацию о таблице"""
    print(f"\n" + "="*60)
    print(f"📋 ТАБЛИЦА: {table_name.upper()}")
    print("="*60)
    
    # Количество записей
    count = get_table_count(conn, table_name)
    print(f"📊 Количество записей: {count}")
    
    # Схема таблицы
    schema = get_table_schema(conn, table_name, db_type)
    if schema:
        print(f"\n📋 СТРУКТУРА ТАБЛИЦЫ '{table_name}':")
        print("-" * 80)
        print(f"{'#':<3} {'Название поля':<25} {'Тип':<15} {'NOT NULL':<10} {'Значение по умолчанию':<20}")
        print("-" * 80)
        
        for i, col in enumerate(schema):
            pk_mark = " (PK)" if col['primary_key'] else ""
            not_null = "YES" if col['not_null'] else "NO"
            default = str(col['default']) if col['default'] is not None else ""
            
            print(f"{i:<3} {col['column']:<25} {col['type']:<15} {not_null:<10} {default:<20}")
        
        print("-" * 80)
        print(f"Всего полей: {len(schema)}")
    
    # Примеры данных
    if count > 0:
        print(f"\n📄 ПРИМЕРЫ ДАННЫХ (первые 5 записей):")
        print("-" * 80)
        
        samples = get_table_sample(conn, table_name)
        for i, row in enumerate(samples, 1):
            print(f"\n📝 Запись #{i}:")
            for key, value in row.items():
                # Обрезаем длинные значения
                display_value = str(value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                print(f"   {key}: {display_value}")
    else:
        print(f"\n📄 Таблица пуста")


def analyze_offers_system(conn, tables, db_type):
    """Анализируем систему офферов"""
    print(f"\n" + "="*60)
    print(f"🎯 АНАЛИЗ СИСТЕМЫ ОФФЕРОВ")
    print("="*60)
    
    # Ищем таблицы связанные с офферами
    offer_tables = [t for t in tables if 'offer' in t.lower()]
    
    if offer_tables:
        print(f"✅ Найдены таблицы офферов: {offer_tables}")
        for table in offer_tables:
            count = get_table_count(conn, table)
            print(f"   📊 {table}: {count} записей")
    else:
        print(f"❌ Таблицы офферов не найдены!")
        print(f"📋 Доступные таблицы: {tables}")
    
    # Проверяем наличие пользователей
    if 'users' in tables:
        user_count = get_table_count(conn, 'users')
        print(f"👥 Пользователей в системе: {user_count}")
        
        if user_count > 0:
            print(f"👤 Примеры пользователей:")
            users = get_table_sample(conn, 'users', 3)
            for user in users:
                print(f"   ID: {user.get('id')} | Telegram: {user.get('telegram_id')} | Username: {user.get('username', 'N/A')}")
    
    # Проверяем каналы
    if 'channels' in tables:
        channel_count = get_table_count(conn, 'channels')
        print(f"📺 Каналов в системе: {channel_count}")


def main():
    """Главная функция"""
    print("🗄️ ПРОСМОТР БАЗЫ ДАННЫХ TELEGRAM MINI APP")
    print("="*60)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Подключаемся к БД
    conn, db_path = get_database_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных")
        return
    
    db_type = get_database_type()
    print(f"✅ Подключение установлено: {db_path}")
    
    try:
        # Получаем список таблиц
        tables = get_tables_list(conn, db_type)
        
        if not tables:
            print("❌ Таблицы не найдены!")
            return
        
        print(f"\n📋 НАЙДЕННЫЕ ТАБЛИЦЫ ({len(tables)}):")
        for i, table in enumerate(tables, 1):
            count = get_table_count(conn, table)
            print(f"   {i:2d}. {table} ({count} записей)")
        
        # Анализируем систему офферов
        analyze_offers_system(conn, tables, db_type)
        
        # Интерактивный режим
        print(f"\n" + "="*60)
        print("🔍 ИНТЕРАКТИВНЫЙ РЕЖИМ")
        print("="*60)
        print("Введите номер таблицы для просмотра или команду:")
        print("   - число (1-{}): показать таблицу".format(len(tables)))
        print("   - 'all': показать все таблицы")
        print("   - 'offers': анализ системы офферов") 
        print("   - 'exit': выход")
        
        while True:
            try:
                user_input = input(f"\n> ").strip().lower()
                
                if user_input == 'exit':
                    break
                elif user_input == 'all':
                    for table in tables:
                        print_table_info(conn, table, db_type)
                elif user_input == 'offers':
                    analyze_offers_system(conn, tables, db_type)
                elif user_input.isdigit():
                    table_num = int(user_input)
                    if 1 <= table_num <= len(tables):
                        table_name = tables[table_num - 1]
                        print_table_info(conn, table_name, db_type)
                    else:
                        print(f"❌ Номер должен быть от 1 до {len(tables)}")
                else:
                    print("❌ Неизвестная команда")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")
    
    finally:
        conn.close()
        print(f"\n👋 Подключение к базе данных закрыто")


if __name__ == '__main__':
    main()