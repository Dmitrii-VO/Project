#!/usr/bin/env python3
"""
simple_init_db.py - Простая инициализация SQLite базы данных
Создает базовую схему без сложной миграции
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем переменные окружения по умолчанию")
    # Определяем заглушку для load_dotenv
    load_dotenv = lambda: None

# Конфигурация
DATABASE_PATH = 'telegram_mini_app.db'
YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))

def create_basic_database():
    """Создание базовой SQLite базы данных с минимальной схемой"""
    print("🗄️ Создание базовой SQLite базы данных...")
    
    # Удаляем старую базу если существует
    if os.path.exists(DATABASE_PATH):
        backup_name = f"{DATABASE_PATH}.backup.{int(datetime.now().timestamp())}"
        os.rename(DATABASE_PATH, backup_name)
        print(f"📦 Создан бэкап: {backup_name}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    print("📋 Создание основных таблиц...")
    
    # 1. Таблица пользователей
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            role TEXT DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Таблица users создана")
    
    # 2. Таблица каналов
    cursor.execute('''
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            title TEXT NOT NULL,
            username TEXT,
            description TEXT,
            subscriber_count INTEGER DEFAULT 0,
            category TEXT,
            language TEXT DEFAULT 'ru',
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            owner_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    print("✅ Таблица channels создана")
    
    # 3. Таблица офферов
    cursor.execute('''
        CREATE TABLE offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content TEXT,
            price DECIMAL(10, 2) NOT NULL,
            currency TEXT DEFAULT 'RUB',
            deadline DATE,
            target_audience TEXT,
            requirements TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            channel_id INTEGER,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (status IN ('active', 'paused', 'completed', 'cancelled'))
        )
    ''')
    print("✅ Таблица offers создана")
    
    # 4. Таблица откликов на офферы
    cursor.execute('''
        CREATE TABLE offer_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'pending',
            proposed_date DATE,
            rejection_reason TEXT,
            response_message TEXT,
            counter_price DECIMAL(12, 2),
            payment_status TEXT DEFAULT 'pending',
            payment_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            offer_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(offer_id, user_id),
            CHECK (status IN ('pending', 'accepted', 'rejected', 'completed', 'cancelled')),
            CHECK (payment_status IN ('pending', 'processing', 'paid', 'failed', 'refunded'))
        )
    ''')
    print("✅ Таблица offer_responses создана")
    
    # 5. Таблица уведомлений (опционально)
    cursor.execute('''
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            priority INTEGER DEFAULT 0,
            is_read BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    print("✅ Таблица notifications создана")
    
    print("📊 Создание индексов для производительности...")
    
    # Индексы для производительности
    indexes = [
        "CREATE INDEX idx_users_telegram_id ON users(telegram_id)",
        "CREATE INDEX idx_channels_owner_id ON channels(owner_id)",
        "CREATE INDEX idx_channels_telegram_id ON channels(telegram_id)",
        "CREATE INDEX idx_offers_created_by ON offers(created_by)",
        "CREATE INDEX idx_offers_channel_id ON offers(channel_id)",
        "CREATE INDEX idx_offers_status ON offers(status)",
        "CREATE INDEX idx_offer_responses_offer_id ON offer_responses(offer_id)",
        "CREATE INDEX idx_offer_responses_user_id ON offer_responses(user_id)",
        "CREATE INDEX idx_notifications_user_id ON notifications(user_id)",
        "CREATE INDEX idx_notifications_is_read ON notifications(is_read)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    print("✅ Индексы созданы")
    
    # Создание основного пользователя
    print("👤 Создание основного пользователя...")
    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, role, created_at)
        VALUES (?, 'main_user', 'Main User', 'admin', ?)
    ''', (YOUR_TELEGRAM_ID, datetime.now()))
    
    if cursor.rowcount > 0:
        print(f"✅ Создан основной пользователь с ID: {YOUR_TELEGRAM_ID}")
    else:
        print(f"ℹ️ Пользователь с ID {YOUR_TELEGRAM_ID} уже существует")
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    print("✅ База данных успешно создана!")
    return True

def verify_database():
    """Проверка созданной базы данных"""
    print("🔍 Проверка базы данных...")
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        expected_tables = ['users', 'channels', 'offers', 'offer_responses', 'notifications']
        found_tables = [table[0] for table in tables]
        
        print(f"📋 Найдено таблиц: {len(found_tables)}")
        for table in found_tables:
            print(f"   ✅ {table}")
        
        # Проверяем отсутствующие таблицы
        missing_tables = set(expected_tables) - set(found_tables)
        if missing_tables:
            print(f"⚠️ Отсутствующие таблицы: {list(missing_tables)}")
            return False
        
        # Проверяем количество записей
        for table in found_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   📊 {table}: {count} записей")
        
        conn.close()
        print("✅ Проверка базы данных прошла успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
        return False

def update_env_file():
    """Обновление .env файла"""
    print("📝 Проверка .env файла...")
    
    database_url = f'sqlite:///{DATABASE_PATH}'
    
    # Читаем существующий .env
    env_content = ""
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # Проверяем DATABASE_URL
    if 'DATABASE_URL=' in env_content:
        # Обновляем существующую строку
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                if database_url not in line:
                    lines[i] = f'DATABASE_URL={database_url}'
                    print(f"✅ DATABASE_URL обновлен: {database_url}")
                else:
                    print(f"ℹ️ DATABASE_URL уже корректный: {database_url}")
                break
        env_content = '\n'.join(lines)
    else:
        # Добавляем новую строку
        env_content += f'\nDATABASE_URL={database_url}\n'
        print(f"✅ DATABASE_URL добавлен: {database_url}")
    
    # Сохраняем .env
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)

def main():
    """Главная функция инициализации"""
    print("🚀 ПРОСТАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    try:
        # 1. Создание базы данных
        if create_basic_database():
            print("\n✅ База данных создана успешно")
        else:
            print("\n❌ Ошибка создания базы данных")
            return False
        
        # 2. Проверка базы данных
        if verify_database():
            print("\n✅ Проверка прошла успешно")
        else:
            print("\n❌ Ошибка при проверке")
            return False
        
        # 3. Обновление .env файла
        update_env_file()
        
        print("\n" + "=" * 50)
        print("🎉 ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 50)
        print(f"🗄️ База данных: {DATABASE_PATH}")
        print(f"👤 Основной пользователь: {YOUR_TELEGRAM_ID}")
        print("\n📋 ЧТО ДАЛЬШЕ:")
        print("1. Запустите приложение: python working_app.py")
        print("2. Откройте браузер: http://localhost:5000")
        print("3. Добавьте реальные каналы через интерфейс")
        print("4. Создавайте реальные предложения")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("\n💡 Попробуйте:")
        print("1. Проверить права доступа к директории")
        print("2. Убедиться, что SQLite установлен")
        print("3. Запустить от имени администратора")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
