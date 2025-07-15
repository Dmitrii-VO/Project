#!/usr/bin/env python3
"""
Универсальный скрипт настройки базы данных
Автоматически определяет нужно ли создавать базовые таблицы или только миграцию
"""

import os
import sqlite3
import sys
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class UniversalDatabaseSetup:
    """Универсальный класс для настройки БД"""
    
    def __init__(self, db_path: str = 'telegram_mini_app.db'):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.setup_version = "1.0_universal_setup"
        
        # Список основных таблиц, которые должны существовать
        self.core_tables = ['users', 'channels', 'offers', 'payments', 'channel_offers']
        
        # Список новых таблиц для системы офферов
        self.new_tables = ['offer_proposals', 'offer_placements', 'placement_checks', 'offer_statistics']
        
    def create_backup(self) -> bool:
        """Создание резервной копии базы данных"""
        try:
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, self.backup_path)
                logger.info(f"✅ Резервная копия создана: {self.backup_path}")
                return True
            else:
                logger.info(f"📄 Файл БД не существует, будет создан новый: {self.db_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания резервной копии: {e}")
            return False
    
    def analyze_database_state(self) -> Dict[str, any]:
        """Анализ текущего состояния базы данных"""
        try:
            if not os.path.exists(self.db_path):
                return {
                    'database_exists': False,
                    'core_tables_exist': False,
                    'new_tables_exist': False,
                    'missing_core_tables': self.core_tables,
                    'missing_new_tables': self.new_tables,
                    'action_needed': 'full_setup'
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существующие таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Анализируем какие таблицы есть/нет
            missing_core_tables = [table for table in self.core_tables if table not in existing_tables]
            missing_new_tables = [table for table in self.new_tables if table not in existing_tables]
            existing_core_tables = [table for table in self.core_tables if table in existing_tables]
            existing_new_tables = [table for table in self.new_tables if table in existing_tables]
            
            # Проверяем структуру существующих таблиц
            tables_need_migration = []
            if 'offers' in existing_tables:
                cursor.execute("PRAGMA table_info(offers)")
                offers_columns = [col[1] for col in cursor.fetchall()]
                new_offers_fields = ['status', 'is_marked', 'selected_channels_count', 'expected_placement_duration']
                if not all(field in offers_columns for field in new_offers_fields):
                    tables_need_migration.append('offers')
            
            if 'channels' in existing_tables:
                cursor.execute("PRAGMA table_info(channels)")
                channels_columns = [col[1] for col in cursor.fetchall()]
                new_channels_fields = ['last_parsed_at', 'parsing_enabled', 'telegram_channel_link']
                if not all(field in channels_columns for field in new_channels_fields):
                    tables_need_migration.append('channels')
            
            conn.close()
            
            # Определяем необходимое действие
            if missing_core_tables:
                action_needed = 'create_core_tables_and_migrate'
            elif missing_new_tables or tables_need_migration:
                action_needed = 'migrate_only'
            else:
                action_needed = 'no_action'
            
            result = {
                'database_exists': True,
                'core_tables_exist': len(missing_core_tables) == 0,
                'new_tables_exist': len(missing_new_tables) == 0,
                'existing_tables': existing_tables,
                'missing_core_tables': missing_core_tables,
                'missing_new_tables': missing_new_tables,
                'existing_core_tables': existing_core_tables,
                'existing_new_tables': existing_new_tables,
                'tables_need_migration': tables_need_migration,
                'action_needed': action_needed
            }
            
            logger.info(f"📊 Анализ БД: {len(existing_tables)} таблиц найдено")
            logger.info(f"📊 Основные таблицы: {len(existing_core_tables)}/{len(self.core_tables)}")
            logger.info(f"📊 Новые таблицы: {len(existing_new_tables)}/{len(self.new_tables)}")
            logger.info(f"🎯 Необходимое действие: {action_needed}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа БД: {e}")
            return {'error': str(e)}
    
    def get_core_tables_sql(self) -> str:
        """Получение SQL для создания основных таблиц"""
        return """
        -- ================================================================
        -- СОЗДАНИЕ ОСНОВНЫХ ТАБЛИЦ
        -- ================================================================
        
        -- Таблица пользователей
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Таблица каналов
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            title TEXT NOT NULL,
            username TEXT,
            description TEXT,
            subscriber_count INTEGER DEFAULT 0,
            category TEXT DEFAULT 'other',
            language TEXT DEFAULT 'ru',
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            owner_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            verification_code TEXT,
            status TEXT DEFAULT 'pending',
            verified_at DATETIME,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );
        
        -- Таблица офферов
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_offer_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            content TEXT,
            budget DECIMAL(12, 2),
            target_audience TEXT,
            placement_requirements TEXT,
            contact_info TEXT,
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            is_active BOOLEAN DEFAULT 1,
            category TEXT,
            subcategory TEXT,
            is_premium BOOLEAN DEFAULT 0,
            priority_score INTEGER DEFAULT 0,
            tags TEXT,
            media_files TEXT,
            placement_duration INTEGER,
            min_subscriber_count INTEGER,
            max_budget_per_post DECIMAL(12, 2),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        
        -- Таблица платежей
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            placement_id TEXT NOT NULL,
            amount DECIMAL(12, 2) NOT NULL,
            status TEXT DEFAULT 'pending',
            publisher_id INTEGER NOT NULL,
            advertiser_id INTEGER NOT NULL,
            payment_method TEXT DEFAULT 'internal',
            transaction_id TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME,
            completed_at DATETIME,
            FOREIGN KEY (publisher_id) REFERENCES users(id),
            FOREIGN KEY (advertiser_id) REFERENCES users(id)
        );
        
        -- Таблица связи каналов и офферов
        CREATE TABLE IF NOT EXISTS channel_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_offer_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (main_offer_id) REFERENCES offers(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        );
        
        -- ================================================================
        -- СОЗДАНИЕ ОСНОВНЫХ ИНДЕКСОВ
        -- ================================================================
        
        -- Индексы для users
        CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
        
        -- Индексы для channels
        CREATE INDEX IF NOT EXISTS idx_channels_owner_id ON channels(owner_id);
        CREATE INDEX IF NOT EXISTS idx_channels_telegram_id ON channels(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_channels_username ON channels(username);
        CREATE INDEX IF NOT EXISTS idx_channels_is_verified ON channels(is_verified);
        CREATE INDEX IF NOT EXISTS idx_channels_is_active ON channels(is_active);
        CREATE INDEX IF NOT EXISTS idx_channels_category ON channels(category);
        CREATE INDEX IF NOT EXISTS idx_channels_status ON channels(status);
        
        -- Индексы для offers
        CREATE INDEX IF NOT EXISTS idx_offers_created_by ON offers(created_by);
        CREATE INDEX IF NOT EXISTS idx_offers_is_active ON offers(is_active);
        CREATE INDEX IF NOT EXISTS idx_offers_category ON offers(category);
        CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at);
        CREATE INDEX IF NOT EXISTS idx_offers_expires_at ON offers(expires_at);
        
        -- Индексы для payments
        CREATE INDEX IF NOT EXISTS idx_payments_placement_id ON payments(placement_id);
        CREATE INDEX IF NOT EXISTS idx_payments_publisher_id ON payments(publisher_id);
        CREATE INDEX IF NOT EXISTS idx_payments_advertiser_id ON payments(advertiser_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        
        -- Индексы для channel_offers
        CREATE INDEX IF NOT EXISTS idx_channel_offers_main_offer_id ON channel_offers(main_offer_id);
        CREATE INDEX IF NOT EXISTS idx_channel_offers_channel_id ON channel_offers(channel_id);
        """
    
    def get_migration_sql(self) -> str:
        """Получение SQL для миграции (новые поля и таблицы)"""
        return """
        -- ================================================================
        -- МИГРАЦИЯ: Новая система офферов
        -- ================================================================
        
        -- Добавление новых полей в offers
        ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'draft';
        ALTER TABLE offers ADD COLUMN is_marked BOOLEAN DEFAULT 0;
        ALTER TABLE offers ADD COLUMN selected_channels_count INTEGER DEFAULT 0;
        ALTER TABLE offers ADD COLUMN expected_placement_duration INTEGER DEFAULT 7;
        
        -- Добавление новых полей в channels
        ALTER TABLE channels ADD COLUMN last_parsed_at DATETIME DEFAULT NULL;
        ALTER TABLE channels ADD COLUMN parsing_enabled BOOLEAN DEFAULT 1;
        ALTER TABLE channels ADD COLUMN telegram_channel_link TEXT DEFAULT NULL;
        
        -- Таблица предложений владельцам каналов
        CREATE TABLE IF NOT EXISTS offer_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            status TEXT DEFAULT 'sent',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            responded_at DATETIME DEFAULT NULL,
            rejection_reason TEXT DEFAULT NULL,
            expires_at DATETIME DEFAULT NULL,
            notified_at DATETIME DEFAULT NULL,
            reminder_sent_at DATETIME DEFAULT NULL,
            FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            UNIQUE(offer_id, channel_id)
        );
        
        -- Таблица размещений постов
        CREATE TABLE IF NOT EXISTS offer_placements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id INTEGER NOT NULL,
            post_url TEXT DEFAULT NULL,
            placement_start DATETIME DEFAULT NULL,
            placement_end DATETIME DEFAULT NULL,
            expected_duration INTEGER DEFAULT 7,
            status TEXT DEFAULT 'pending',
            final_views_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposal_id) REFERENCES offer_proposals(id) ON DELETE CASCADE
        );
        
        -- Таблица логов проверок размещения
        CREATE TABLE IF NOT EXISTS placement_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placement_id INTEGER NOT NULL,
            check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            post_exists BOOLEAN DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            check_status TEXT DEFAULT 'success',
            error_message TEXT DEFAULT NULL,
            response_data TEXT DEFAULT NULL,
            FOREIGN KEY (placement_id) REFERENCES offer_placements(id) ON DELETE CASCADE
        );
        
        -- Таблица агрегированной статистики по офферам
        CREATE TABLE IF NOT EXISTS offer_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            total_proposals INTEGER DEFAULT 0,
            accepted_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            expired_count INTEGER DEFAULT 0,
            cancelled_count INTEGER DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            total_views INTEGER DEFAULT 0,
            total_spent DECIMAL(12, 2) DEFAULT 0.00,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            UNIQUE(offer_id)
        );
        
        -- Индексы для offer_proposals
        CREATE INDEX IF NOT EXISTS idx_offer_proposals_offer_id ON offer_proposals(offer_id);
        CREATE INDEX IF NOT EXISTS idx_offer_proposals_channel_id ON offer_proposals(channel_id);
        CREATE INDEX IF NOT EXISTS idx_offer_proposals_status ON offer_proposals(status);
        CREATE INDEX IF NOT EXISTS idx_offer_proposals_created_at ON offer_proposals(created_at);
        CREATE INDEX IF NOT EXISTS idx_offer_proposals_expires_at ON offer_proposals(expires_at);
        
        -- Индексы для offer_placements
        CREATE INDEX IF NOT EXISTS idx_offer_placements_proposal_id ON offer_placements(proposal_id);
        CREATE INDEX IF NOT EXISTS idx_offer_placements_status ON offer_placements(status);
        CREATE INDEX IF NOT EXISTS idx_offer_placements_placement_start ON offer_placements(placement_start);
        CREATE INDEX IF NOT EXISTS idx_offer_placements_placement_end ON offer_placements(placement_end);
        
        -- Индексы для placement_checks
        CREATE INDEX IF NOT EXISTS idx_placement_checks_placement_id ON placement_checks(placement_id);
        CREATE INDEX IF NOT EXISTS idx_placement_checks_check_time ON placement_checks(check_time);
        CREATE INDEX IF NOT EXISTS idx_placement_checks_post_exists ON placement_checks(post_exists);
        
        -- Индексы для новых полей в существующих таблицах
        CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);
        CREATE INDEX IF NOT EXISTS idx_channels_parsing_enabled ON channels(parsing_enabled);
        CREATE INDEX IF NOT EXISTS idx_channels_last_parsed_at ON channels(last_parsed_at);
        
        -- Обновление существующих записей
        UPDATE offers 
        SET status = 'draft', is_marked = 0, selected_channels_count = 0,
            expected_placement_duration = 7
        WHERE status IS NULL OR status = '';
        
        UPDATE channels 
        SET parsing_enabled = 1,
            telegram_channel_link = CASE 
                WHEN username IS NOT NULL THEN 'https://t.me/' || username
                ELSE NULL 
            END
        WHERE parsing_enabled IS NULL;
        """
    
    def execute_sql_safely(self, sql: str, description: str) -> bool:
        """Безопасное выполнение SQL с обработкой ошибок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Включаем WAL режим для безопасности
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Разделяем SQL на отдельные команды и выполняем
            commands = [cmd.strip() for cmd in sql.split(';') if cmd.strip()]
            
            for i, command in enumerate(commands):
                try:
                    cursor.execute(command)
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info(f"⚠️ Поле уже существует (пропускаем): {str(e)}")
                        continue
                    elif "already exists" in str(e).lower():
                        logger.info(f"⚠️ Объект уже существует (пропускаем): {str(e)}")
                        continue
                    else:
                        raise e
                except Exception as e:
                    logger.error(f"❌ Ошибка в команде {i+1}: {command[:50]}...")
                    raise e
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ {description} выполнено успешно!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения {description}: {e}")
            return False
    
    def verify_setup(self) -> bool:
        """Проверка результатов настройки"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем основные таблицы
            for table in self.core_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    logger.error(f"❌ Основная таблица {table} не найдена")
                    return False
                logger.info(f"✅ Основная таблица {table} найдена")
            
            # Проверяем новые таблицы
            for table in self.new_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    logger.error(f"❌ Новая таблица {table} не найдена")
                    return False
                logger.info(f"✅ Новая таблица {table} найдена")
            
            # Проверяем новые поля в offers
            cursor.execute("PRAGMA table_info(offers)")
            offers_columns = [col[1] for col in cursor.fetchall()]
            new_offers_fields = ['status', 'is_marked', 'selected_channels_count', 'expected_placement_duration']
            
            for field in new_offers_fields:
                if field not in offers_columns:
                    logger.error(f"❌ Поле {field} не найдено в таблице offers")
                    return False
                logger.info(f"✅ Поле {field} добавлено в таблицу offers")
            
            # Проверяем новые поля в channels
            cursor.execute("PRAGMA table_info(channels)")
            channels_columns = [col[1] for col in cursor.fetchall()]
            new_channels_fields = ['last_parsed_at', 'parsing_enabled', 'telegram_channel_link']
            
            for field in new_channels_fields:
                if field not in channels_columns:
                    logger.error(f"❌ Поле {field} не найдено в таблице channels")
                    return False
                logger.info(f"✅ Поле {field} добавлено в таблицу channels")
            
            # Проверяем индексы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            logger.info(f"✅ Создано индексов: {len(indexes)}")
            
            # Проверяем триггеры
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
            triggers = [row[0] for row in cursor.fetchall()]
            logger.info(f"✅ Создано триггеров: {len(triggers)}")
            
            # Проверяем представления
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
            views = [row[0] for row in cursor.fetchall()]
            logger.info(f"✅ Создано представлений: {len(views)}")
            
            conn.close()
            
            logger.info("✅ Настройка БД прошла проверку!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки настройки: {e}")
            return False
    
    def rollback_changes(self) -> bool:
        """Откат изменений"""
        try:
            if os.path.exists(self.backup_path):
                shutil.copy2(self.backup_path, self.db_path)
                logger.info(f"✅ Откат выполнен. База данных восстановлена из: {self.backup_path}")
                return True
            else:
                logger.error("❌ Резервная копия не найдена. Откат невозможен.")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка отката: {e}")
            return False
    
    def save_setup_info(self) -> Dict:
        """Сохранение информации о настройке"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу migrations если не существует
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            
            # Сохраняем информацию о настройке
            cursor.execute("""
                INSERT INTO migrations (version, description) 
                VALUES (?, ?)
            """, (self.setup_version, "Universal database setup with offer system"))
            
            conn.commit()
            
            # Получаем все миграции
            cursor.execute("SELECT * FROM migrations ORDER BY executed_at DESC")
            migrations = cursor.fetchall()
            
            conn.close()
            
            return {
                'current_version': self.setup_version,
                'migrations': migrations
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения информации о настройке: {e}")
            return {'error': str(e)}

def main():
    """Основная функция"""
    print("🚀 Универсальная настройка базы данных...")
    print("=" * 60)
    
    # Проверяем аргументы
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'telegram_mini_app.db'
    
    setup = UniversalDatabaseSetup(db_path)
    
    # Шаг 1: Анализ состояния БД
    print("\n🔍 Шаг 1: Анализ состояния базы данных...")
    state = setup.analyze_database_state()
    
    if 'error' in state:
        print(f"❌ Ошибка анализа: {state['error']}")
        sys.exit(1)
    
    print(f"📊 Состояние БД: {state['action_needed']}")
    
    # Шаг 2: Создание резервной копии
    print("\n💾 Шаг 2: Создание резервной копии...")
    if not setup.create_backup():
        print("❌ Не удалось создать резервную копию")
        sys.exit(1)
    
    # Шаг 3: Выполнение необходимых действий
    print(f"\n🔄 Шаг 3: Выполнение действий ({state['action_needed']})...")
    
    success = True
    
    if state['action_needed'] in ['full_setup', 'create_core_tables_and_migrate']:
        # Создаем основные таблицы
        if not setup.execute_sql_safely(setup.get_core_tables_sql(), "создание основных таблиц"):
            success = False
    
    if success and state['action_needed'] in ['full_setup', 'create_core_tables_and_migrate', 'migrate_only']:
        # Выполняем миграцию
        if not setup.execute_sql_safely(setup.get_migration_sql(), "миграция новой системы офферов"):
            success = False
    
    if not success:
        print("❌ Настройка не выполнена, выполняем откат...")
        setup.rollback_changes()
        sys.exit(1)
    
    # Шаг 4: Проверка результатов
    print("\n✅ Шаг 4: Проверка результатов...")
    if not setup.verify_setup():
        print("❌ Проверка не пройдена")
        setup.rollback_changes()
        sys.exit(1)
    
    # Шаг 5: Сохранение информации о настройке
    print("\n📝 Шаг 5: Сохранение информации о настройке...")
    setup_info = setup.save_setup_info()
    
    print("\n" + "=" * 60)
    print("🎉 НАСТРОЙКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 60)
    print(f"📊 Версия: {setup_info.get('current_version', 'Unknown')}")
    print(f"💾 Резервная копия: {setup.backup_path}")
    print(f"🗄️  База данных: {setup.db_path}")
    print(f"🎯 Выполненное действие: {state['action_needed']}")
    
    print("\n📋 Создано:")
    print(f"• Основных таблиц: {len(setup.core_tables)}")
    print(f"• Новых таблиц: {len(setup.new_tables)}")
    print("• Индексы, триггеры и представления")
    
    print("\n📋 Следующие шаги:")
    print("1. Проверьте работу приложения")
    print("2. Если все работает - удалите резервную копию")
    print("3. Можете переходить к следующему этапу разработки")

if __name__ == "__main__":
    main()