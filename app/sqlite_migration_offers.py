# sqlite_migration_offers.py - Миграция для системы рекламных предложений
import os
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'telegram_mini_app.db'

def run_offers_migration():
    """Запуск миграции для системы предложений"""
    try:
        print("🔄 Запуск миграции для системы рекламных предложений...")
        
        if not os.path.exists(DATABASE_PATH):
            print(f"❌ База данных не найдена: {DATABASE_PATH}")
            print("Сначала запустите sqlite_migration.py для создания основных таблиц")
            return False

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Проверяем существующие таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('offers', 'offer_responses')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Найденные таблицы: {existing_tables}")

        # 1. Обновляем таблицу channels для поддержки рекламы
        print("🔧 Обновляем таблицу channels...")
        
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(channels)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        columns_to_add = [
            ('accepts_ads', 'BOOLEAN DEFAULT 1'),
            ('price_per_post', 'INTEGER DEFAULT NULL'),
            ('avg_engagement_rate', 'REAL DEFAULT NULL'),
            ('last_post_date', 'DATE DEFAULT NULL')
        ]
        
        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE channels ADD COLUMN {column_name} {column_def}')
                    print(f"  ✅ Добавлена колонка {column_name}")
                except sqlite3.Error as e:
                    print(f"  ⚠️ Ошибка добавления колонки {column_name}: {e}")

        # 2. Создаем таблицу channel_offers
        print("🔧 Создаем таблицу channel_offers...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                main_offer_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (main_offer_id) REFERENCES offers(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
                UNIQUE(main_offer_id, channel_id)
            )
        ''')
        print("  ✅ Таблица channel_offers создана")

        # 3. Обновляем таблицу offers
        print("🔧 Обновляем таблицу offers...")
        
        # Проверяем существующие колонки в offers
        cursor.execute("PRAGMA table_info(offers)")
        offers_columns = [column[1] for column in cursor.fetchall()]
        
        offers_columns_to_add = [
            ('offer_type', 'VARCHAR(20) DEFAULT "main"'),
            ('parent_offer_id', 'INTEGER DEFAULT NULL'),
            ('estimated_reach', 'INTEGER DEFAULT NULL'),
            ('total_cost', 'DECIMAL(10,2) DEFAULT NULL')
        ]
        
        for column_name, column_def in offers_columns_to_add:
            if column_name not in offers_columns:
                try:
                    cursor.execute(f'ALTER TABLE offers ADD COLUMN {column_name} {column_def}')
                    print(f"  ✅ Добавлена колонка {column_name} в offers")
                except sqlite3.Error as e:
                    print(f"  ⚠️ Ошибка добавления колонки {column_name}: {e}")

        # 4. Создаем таблицу offer_statistics
        print("🔧 Создаем таблицу offer_statistics...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offer_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                views_count INTEGER DEFAULT 0,
                responses_count INTEGER DEFAULT 0,
                accepted_count INTEGER DEFAULT 0,
                rejected_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
            )
        ''')
        print("  ✅ Таблица offer_statistics создана")

        # 5. Создаем таблицу notifications
        print("🔧 Создаем таблицу notifications...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                data TEXT DEFAULT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        print("  ✅ Таблица notifications создана")

        # 6. Создаем таблицу offer_history
        print("🔧 Создаем таблицу offer_history...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                action VARCHAR(50) NOT NULL,
                old_data TEXT DEFAULT NULL,
                new_data TEXT DEFAULT NULL,
                changed_by INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
                FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        print("  ✅ Таблица offer_history создана")

        # 7. Создаем индексы
        print("🔧 Создаем индексы...")
        indexes = [
            ('idx_channel_offers_main_offer', 'channel_offers', 'main_offer_id'),
            ('idx_channel_offers_channel', 'channel_offers', 'channel_id'),
            ('idx_offers_type', 'offers', 'offer_type'),
            ('idx_offers_status_created', 'offers', 'status, created_at'),
            ('idx_notifications_user_unread', 'notifications', 'user_id, is_read'),
            ('idx_offer_responses_status', 'offer_responses', 'status')
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})')
                print(f"  ✅ Индекс {index_name} создан")
            except sqlite3.Error as e:
                print(f"  ⚠️ Ошибка создания индекса {index_name}: {e}")

        # 8. Обновляем существующие данные
        print("🔧 Обновляем существующие данные...")
        cursor.execute('UPDATE channels SET accepts_ads = 1 WHERE accepts_ads IS NULL')
        
        # 9. Создаем демо каналы если таблица пустая
        print("🔧 Проверяем демо данные...")
        cursor.execute('SELECT COUNT(*) FROM channels')
        channels_count = cursor.fetchone()[0]
        
        if channels_count == 0:
            print("📝 Создаем демо каналы...")
            demo_channels = [
                ('-1001000000001', 'IT Новости', 'it_news_demo', 2500, 'Последние новости из мира технологий', 'technology', 1, 2000, 4.2),
                ('-1001000000002', 'Криптовалюты', 'crypto_demo', 1800, 'Новости криптовалют и блокчейна', 'finance', 1, 1500, 3.8),
                ('-1001000000003', 'Дизайн и UX', 'design_demo', 3200, 'Дизайн интерфейсов и пользовательский опыт', 'design', 1, 2500, 4.5),
                ('-1001000000004', 'Стартапы', 'startups_demo', 1200, 'Новости стартапов и предпринимательства', 'business', 0, 1000, 3.2),
                ('-1001000000005', 'Python разработка', 'python_demo', 4100, 'Всё о программировании на Python', 'technology', 1, 3000, 4.7)
            ]
            
            # Создаем пользователя-владельца если его нет
            cursor.execute('SELECT COUNT(*) FROM users')
            users_count = cursor.fetchone()[0]
            
            if users_count == 0:
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, is_admin) 
                    VALUES (?, ?, ?, ?)
                ''', (373086959, 'demo_owner', 'Demo User', True))
                user_id = cursor.lastrowid
            else:
                cursor.execute('SELECT id FROM users LIMIT 1')
                user_id = cursor.fetchone()[0]
            
            for channel_data in demo_channels:
                cursor.execute('''
                    INSERT INTO channels (
                        telegram_channel_id, title, username, subscribers_count, description, 
                        category, is_verified, is_active, accepts_ads, price_per_post, 
                        avg_engagement_rate, owner_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (*channel_data, user_id))
            
            print(f"  ✅ Создано {len(demo_channels)} демо каналов")

        # 10. Создаем триггеры
        print("🔧 Создаем триггеры...")
        
        # Триггер для статистики предложений
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_offer_statistics
                AFTER INSERT ON offer_responses
                FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO offer_statistics (
                    offer_id, 
                    responses_count, 
                    accepted_count, 
                    rejected_count,
                    last_updated
                )
                VALUES (
                    NEW.offer_id,
                    (SELECT COUNT(*) FROM offer_responses WHERE offer_id = NEW.offer_id),
                    (SELECT COUNT(*) FROM offer_responses WHERE offer_id = NEW.offer_id AND status = 'accepted'),
                    (SELECT COUNT(*) FROM offer_responses WHERE offer_id = NEW.offer_id AND status = 'rejected'),
                    CURRENT_TIMESTAMP
                );
            END
        ''')
        
        # Триггер для уведомлений о новых предложениях
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS create_offer_notification
                AFTER INSERT ON offers
                FOR EACH ROW
                WHEN NEW.offer_type = 'channel'
            BEGIN
                INSERT INTO notifications (user_id, type, title, message, data)
                SELECT 
                    c.owner_id,
                    'new_offer',
                    'Новое рекламное предложение',
                    'Вы получили новое предложение для канала "' || c.title || '"',
                    '{"offer_id": ' || NEW.id || ', "channel_id": ' || NEW.channel_id || '}'
                FROM channels c
                WHERE c.id = NEW.channel_id;
            END
        ''')
        
        # Триггер для уведомлений об ответах
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS create_response_notification
                AFTER INSERT ON offer_responses
                FOR EACH ROW
            BEGIN
                INSERT INTO notifications (user_id, type, title, message, data)
                SELECT 
                    o.created_by,
                    'offer_response',
                    CASE NEW.status 
                        WHEN 'accepted' THEN 'Предложение принято!'
                        WHEN 'rejected' THEN 'Предложение отклонено'
                        ELSE 'Новый ответ на предложение'
                    END,
                    'Получен ответ на ваше предложение "' || o.title || '"',
                    '{"offer_id": ' || o.id || ', "response_id": ' || NEW.id || ', "status": "' || NEW.status || '"}'
                FROM offers o
                WHERE o.id = NEW.offer_id;
            END
        ''')
        
        print("  ✅ Триггеры созданы")

        # Сохраняем изменения
        conn.commit()
        
        # Проверяем финальное состояние
        print("\n📊 Финальная проверка таблиц...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        all_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Таблицы в базе данных: {all_tables}")
        
        # Проверяем количество записей
        for table in ['users', 'channels', 'offers', 'offer_responses', 'channel_offers']:
            if table in all_tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"📊 {table}: {count} записей")
        
        conn.close()
        
        print("\n✅ Миграция системы предложений завершена успешно!")
        print("🚀 Теперь можно запускать working_app.py с поддержкой офферов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False

if __name__ == '__main__':
    success = run_offers_migration()
    if success:
        print("\n🎉 Миграция выполнена успешно!")
        print("Следующие шаги:")
        print("1. Запустите working_app.py")
        print("2. Перейдите на /create-offer для создания предложений")
        print("3. Используйте /offers/my-offers для просмотра")
    else:
        print("\n💥 Миграция не удалась. Проверьте ошибки выше.")
