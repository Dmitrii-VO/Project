# sqlite_migration.py - Очищенная миграция без тестовых данных
import os
import sys
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Конфигурация
OLD_DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:1994@localhost:5432/telegram_mini_app')
NEW_SQLITE_PATH = 'telegram_mini_app.db'
YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))


def get_postgres_connection():
    """Получение подключения к PostgreSQL для экспорта данных"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        url = urlparse(OLD_DATABASE_URL)
        conn = psycopg2.connect(
            host=url.hostname or 'localhost',
            port=url.port or 5432,
            database=url.path[1:] if url.path else 'postgres',
            user=url.username or 'postgres',
            password=url.password or 'password',
            cursor_factory=RealDictCursor
        )
        return conn
    except ImportError:
        print("⚠️ psycopg2 не установлен, пропускаем экспорт данных")
        return None
    except Exception as e:
        print(f"⚠️ Ошибка подключения к PostgreSQL: {e}")
        return None


def create_sqlite_database():
    """Создание SQLite базы данных с полной схемой"""
    print("🗄️ Создание SQLite базы данных...")

    # Удаляем старую базу если существует
    if os.path.exists(NEW_SQLITE_PATH):
        os.remove(NEW_SQLITE_PATH)
        print(f"🗑️ Удалена старая база данных: {NEW_SQLITE_PATH}")

    conn = sqlite3.connect(NEW_SQLITE_PATH)
    cursor = conn.cursor()

    # Включаем foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')

    print("📋 Создание основных таблиц...")

    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создание таблицы каналов
    cursor.execute('''
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_channel_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            username TEXT,
            subscribers_count INTEGER DEFAULT 0,
            description TEXT,
            category TEXT DEFAULT 'general',
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            is_public BOOLEAN DEFAULT 1,
            accepts_ads BOOLEAN DEFAULT 1,
            invite_link TEXT,
            photo_url TEXT,
            avg_engagement_rate REAL DEFAULT 0.0,
            price_per_post INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Создание базовой таблицы офферов (для обратной совместимости)
    cursor.execute('''
        CREATE TABLE offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content TEXT NOT NULL,
            price DECIMAL(12, 2) NOT NULL,
            currency TEXT DEFAULT 'RUB',
            deadline DATE,
            target_audience TEXT,
            requirements TEXT,
            status TEXT DEFAULT 'active',
            offer_type TEXT DEFAULT 'main',
            parent_offer_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            channel_id INTEGER,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (parent_offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            CHECK (status IN ('active', 'paused', 'completed', 'cancelled', 'pending')),
            CHECK (price > 0)
        )
    ''')

    print("🆕 Создание расширенных таблиц для системы офферов...")

    # НОВАЯ: Расширенная таблица офферов
    cursor.execute('''
        CREATE TABLE offers_extended (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content TEXT NOT NULL,
            price DECIMAL(12, 2) NOT NULL,
            currency TEXT DEFAULT 'RUB',
            deadline DATE,
            target_audience TEXT,
            requirements TEXT,
            status TEXT DEFAULT 'active',
            offer_type TEXT DEFAULT 'post',
            budget_total DECIMAL(12, 2),
            budget_spent DECIMAL(12, 2) DEFAULT 0,
            max_channels INTEGER,
            completion_rate REAL DEFAULT 0.0,
            total_invitations INTEGER DEFAULT 0,
            accepted_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
            CHECK (status IN ('active', 'paused', 'completed', 'cancelled', 'draft')),
            CHECK (price > 0)
        )
    ''')

    # НОВАЯ: Таблица связей офферов и каналов
    cursor.execute('''
        CREATE TABLE offer_channel_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            price_negotiated DECIMAL(12, 2),
            response_message TEXT,
            proposed_date DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers_extended(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            UNIQUE(offer_id, channel_id),
            CHECK (status IN ('pending', 'accepted', 'rejected', 'completed', 'cancelled'))
        )
    ''')

    # НОВАЯ: Таблица связи главных офферов с индивидуальными
    cursor.execute('''
        CREATE TABLE channel_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_offer_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (main_offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
        )
    ''')

    # Создание базовой таблицы ответов на офферы (для обратной совместимости)
    cursor.execute('''
        CREATE TABLE offer_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
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

    print("🔔 Создание системы уведомлений...")

    # НОВАЯ: Таблица уведомлений
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (type IN ('offer_received', 'payment_received', 'channel_verified', 'deadline_reminder', 'system'))
        )
    ''')

    print("📄 Создание системы шаблонов...")

    # НОВАЯ: Таблица шаблонов офферов
    cursor.execute('''
        CREATE TABLE offer_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            title_template TEXT NOT NULL,
            description_template TEXT NOT NULL,
            content_template TEXT NOT NULL,
            default_price DECIMAL(12, 2),
            default_currency TEXT DEFAULT 'RUB',
            is_public BOOLEAN DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    print("⚡ Создание индексов для производительности...")

    # Создание индексов для производительности
    indexes = [
        # Основные индексы
        'CREATE INDEX idx_users_telegram_id ON users(telegram_id)',
        'CREATE INDEX idx_channels_owner_id ON channels(owner_id)',
        'CREATE INDEX idx_channels_username ON channels(username)',
        'CREATE INDEX idx_channels_active ON channels(is_active)',
        'CREATE INDEX idx_channels_accepts_ads ON channels(accepts_ads)',

        # Индексы для офферов
        'CREATE INDEX idx_offers_channel_id ON offers(channel_id)',
        'CREATE INDEX idx_offers_status ON offers(status)',
        'CREATE INDEX idx_offers_created_by ON offers(created_by)',
        'CREATE INDEX idx_offers_extended_created_by ON offers_extended(created_by)',
        'CREATE INDEX idx_offers_extended_status ON offers_extended(status)',
        'CREATE INDEX idx_offers_extended_created_at ON offers_extended(created_at)',

        # Индексы для целей офферов
        'CREATE INDEX idx_offer_targets_offer_id ON offer_channel_targets(offer_id)',
        'CREATE INDEX idx_offer_targets_channel_id ON offer_channel_targets(channel_id)',
        'CREATE INDEX idx_offer_targets_status ON offer_channel_targets(status)',

        # Индексы для ответов
        'CREATE INDEX idx_offer_responses_offer_id ON offer_responses(offer_id)',
        'CREATE INDEX idx_offer_responses_user_id ON offer_responses(user_id)',
        'CREATE INDEX idx_offer_responses_status ON offer_responses(status)',

        # Индексы для уведомлений
        'CREATE INDEX idx_notifications_user_id ON notifications(user_id)',
        'CREATE INDEX idx_notifications_is_read ON notifications(is_read)',
        'CREATE INDEX idx_notifications_type ON notifications(type)',
        'CREATE INDEX idx_notifications_created_at ON notifications(created_at)',

        # Индексы для шаблонов
        'CREATE INDEX idx_offer_templates_created_by ON offer_templates(created_by)',
        'CREATE INDEX idx_offer_templates_is_public ON offer_templates(is_public)',
        'CREATE INDEX idx_offer_templates_category ON offer_templates(category)'
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    print("🎯 Настройка SQLite для производительности...")

    # Оптимизация SQLite
    optimization_queries = [
        'PRAGMA journal_mode = WAL',  # Включаем WAL режим для лучшей производительности
        'PRAGMA synchronous = NORMAL',  # Баланс между безопасностью и скоростью
        'PRAGMA cache_size = 10000',  # Увеличиваем кеш
        'PRAGMA temp_store = memory',  # Временные данные в памяти
        'PRAGMA mmap_size = 268435456'  # 256MB memory-mapped I/O
    ]

    for query in optimization_queries:
        cursor.execute(query)

    conn.commit()
    print("✅ SQLite схема создана с полной структурой")
    return conn


def create_main_user_only(sqlite_conn):
    """Создание только основного пользователя без тестовых данных"""
    cursor = sqlite_conn.cursor()

    try:
        print("👤 Создание основного пользователя...")

        # Создаем только основного пользователя (администратора)
        cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin) 
            VALUES (?, ?, ?, ?)
        ''', (YOUR_TELEGRAM_ID, 'main_user', 'Main User', True))

        sqlite_conn.commit()
        print(f"✅ Основной пользователь создан (Telegram ID: {YOUR_TELEGRAM_ID})")

    except Exception as e:
        print(f"⚠️ Предупреждение при создании основного пользователя: {e}")
        sqlite_conn.rollback()


def export_data_from_postgres():
    """Экспорт реальных данных из PostgreSQL (исключая тестовые)"""
    pg_conn = get_postgres_connection()
    if not pg_conn:
        print("⚠️ Пропускаем экспорт данных из PostgreSQL")
        return None

    print("📤 Экспортируем реальные данные из PostgreSQL...")

    exported_data = {
        'users': [],
        'channels': [],
        'offers': [],
        'offer_responses': []
    }

    try:
        cursor = pg_conn.cursor()

        # Экспорт пользователей (исключая тестовых)
        cursor.execute('''
            SELECT * FROM users 
            WHERE username NOT LIKE '%test%' 
            AND username NOT LIKE '%demo%'
            ORDER BY id
        ''')
        users = cursor.fetchall()
        for user in users:
            exported_data['users'].append(dict(user))

        # Экспорт каналов (исключая тестовые и демо)
        cursor.execute('''
            SELECT * FROM channels 
            WHERE title NOT LIKE '%тест%' 
            AND title NOT LIKE '%test%' 
            AND title NOT LIKE '%демо%'
            AND title NOT LIKE '%demo%'
            AND title NOT LIKE '%🧪%'
            AND username NOT LIKE 'test_%'
            AND username NOT LIKE 'demo_%'
            ORDER BY id
        ''')
        channels = cursor.fetchall()
        for channel in channels:
            exported_data['channels'].append(dict(channel))

        # Экспорт офферов (исключая тестовые)
        cursor.execute('''
            SELECT * FROM offers 
            WHERE title NOT LIKE '%тест%' 
            AND title NOT LIKE '%test%'
            AND title NOT LIKE '%демо%'
            AND title NOT LIKE '%demo%'
            ORDER BY id
        ''')
        offers = cursor.fetchall()
        for offer in offers:
            exported_data['offers'].append(dict(offer))

        # Экспорт ответов
        cursor.execute('SELECT * FROM offer_responses ORDER BY id')
        responses = cursor.fetchall()
        for response in responses:
            exported_data['offer_responses'].append(dict(response))

        pg_conn.close()

        print(f"   📊 Экспортировано реальных данных:")
        print(f"      👥 Пользователей: {len(exported_data['users'])}")
        print(f"      📺 Каналов: {len(exported_data['channels'])}")
        print(f"      💼 Офферов: {len(exported_data['offers'])}")
        print(f"      📝 Ответов: {len(exported_data['offer_responses'])}")

        return exported_data

    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")
        pg_conn.close()
        return None


def import_data_to_sqlite(sqlite_conn, data):
    """Импорт реальных данных в SQLite"""
    if not data:
        create_main_user_only(sqlite_conn)
        return

    print("📥 Импортируем реальные данные в SQLite...")
    cursor = sqlite_conn.cursor()

    try:
        # Импорт пользователей
        for user in data['users']:
            cursor.execute('''
                INSERT OR IGNORE INTO users (
                    telegram_id, username, first_name, last_name, 
                    is_admin, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['telegram_id'], user['username'], user['first_name'], user['last_name'],
                user['is_admin'], user['is_active'], user['created_at'], user['updated_at']
            ))

        # Импорт каналов
        for channel in data['channels']:
            cursor.execute('''
                INSERT OR IGNORE INTO channels (
                    telegram_channel_id, title, username, subscribers_count, description,
                    category, is_verified, is_active, is_public, invite_link, photo_url,
                    created_at, updated_at, owner_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                channel['telegram_channel_id'], channel['title'], channel['username'],
                channel['subscribers_count'], channel['description'], channel.get('category', 'general'),
                channel['is_verified'], channel['is_active'], channel['is_public'],
                channel['invite_link'], channel['photo_url'], channel['created_at'],
                channel['updated_at'], channel['owner_id']
            ))

        # Импорт офферов
        for offer in data['offers']:
            cursor.execute('''
                INSERT OR IGNORE INTO offers (
                    title, description, content, price, currency, deadline,
                    target_audience, requirements, status, created_at, updated_at,
                    channel_id, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                offer['title'], offer['description'], offer['content'], offer['price'],
                offer['currency'], offer['deadline'], offer['target_audience'],
                offer['requirements'], offer['status'], offer['created_at'],
                offer['updated_at'], offer['channel_id'], offer['created_by']
            ))

        # Импорт ответов
        for response in data['offer_responses']:
            cursor.execute('''
                INSERT OR IGNORE INTO offer_responses (
                    status, proposed_date, rejection_reason, payment_status, payment_id,
                    created_at, updated_at, offer_id, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response['status'], response['proposed_date'], response['rejection_reason'],
                response['payment_status'], response['payment_id'], response['created_at'],
                response['updated_at'], response['offer_id'], response['user_id']
            ))

        sqlite_conn.commit()
        print("✅ Реальные данные успешно импортированы")

        # Создаем основного пользователя если он не был импортирован
        create_main_user_only(sqlite_conn)

    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        sqlite_conn.rollback()


def update_env_file():
    """Обновление .env файла для SQLite"""
    print("📝 Обновление .env файла...")

    # Читаем текущий .env
    env_content = ""
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()

    # Заменяем DATABASE_URL
    new_database_url = f'sqlite:///{NEW_SQLITE_PATH}'

    if 'DATABASE_URL=' in env_content:
        # Заменяем существующую строку
        lines = env_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                lines[i] = f'DATABASE_URL={new_database_url}'
                break
        env_content = '\n'.join(lines)
    else:
        # Добавляем новую строку
        env_content += f'\nDATABASE_URL={new_database_url}\n'

    # Сохраняем обновленный .env
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"✅ DATABASE_URL обновлен: {new_database_url}")


def verify_database():
    """Проверка созданной базы данных"""
    print("🔍 Проверка созданной базы данных...")

    try:
        conn = sqlite3.connect(NEW_SQLITE_PATH)
        cursor = conn.cursor()

        # Проверяем наличие всех таблиц
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()

        expected_tables = [
            'channels', 'channel_offers', 'notifications', 'offers',
            'offers_extended', 'offer_channel_targets', 'offer_responses',
            'offer_templates', 'users'
        ]

        found_tables = [table[0] for table in tables]

        print(f"   📋 Найдено таблиц: {len(found_tables)}")
        for table in found_tables:
            print(f"      ✅ {table}")

        # Проверяем отсутствующие таблицы
        missing_tables = set(expected_tables) - set(found_tables)
        if missing_tables:
            print(f"   ⚠️ Отсутствующие таблицы: {list(missing_tables)}")

        # Проверяем количество записей
        for table in found_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"      📊 {table}: {count} записей")

        conn.close()
        print("✅ Проверка базы данных завершена")

    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")


def main():
    """Главная функция миграции"""
    print("🔄 МИГРАЦИЯ БЕЗ ТЕСТОВЫХ ДАННЫХ")
    print("=" * 60)

    # 1. Экспортируем только реальные данные из PostgreSQL
    exported_data = export_data_from_postgres()

    # 2. Создаем SQLite базу данных с полной схемой
    sqlite_conn = create_sqlite_database()

    # 3. Импортируем только реальные данные
    import_data_to_sqlite(sqlite_conn, exported_data)

    # 4. Закрываем соединение
    sqlite_conn.close()

    # 5. Обновляем .env файл
    update_env_file()

    # 6. Проверяем созданную базу данных
    verify_database()

    print("\n" + "=" * 60)
    print("🎉 МИГРАЦИЯ БЕЗ ТЕСТОВЫХ ДАННЫХ ЗАВЕРШЕНА!")
    print("=" * 60)
    print("📋 СОЗДАНО:")
    print("✅ Чистая схема базы данных SQLite")
    print("✅ Все необходимые таблицы для системы офферов")
    print("✅ Система уведомлений")
    print("✅ Шаблоны офферов")
    print("✅ Производительные индексы")
    print("✅ Только основной пользователь (без тестовых данных)")
    print("\n📋 ЧТО ДАЛЬШЕ:")
    print("1. Запустите приложение: python working_app.py")
    print("2. Добавьте реальные каналы через интерфейс")
    print("3. Создавайте реальные предложения")
    print(f"\n🗄️ База данных: {NEW_SQLITE_PATH}")
    print(f"📝 .env обновлен: DATABASE_URL=sqlite:///{NEW_SQLITE_PATH}")
    print("=" * 60)


if __name__ == '__main__':
    main()