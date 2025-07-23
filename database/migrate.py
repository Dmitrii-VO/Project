#!/usr/bin/env python3
"""
PostgreSQL Migration Tool для Telegram Mini App
Перенос данных из SQLite в PostgreSQL с сохранением целостности
"""

import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Добавляем путь для импорта конфигурации
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.telegram_config import AppConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Класс для миграции данных из SQLite в PostgreSQL"""
    
    def __init__(self):
        self.sqlite_path = AppConfig.DATABASE_PATH
        self.postgres_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://telegram_user:secure_password_2025@localhost:5432/telegram_mini_app'
        )
        
        # Маппинг таблиц и их столбцов
        self.table_mappings = {
            'users': {
                'columns': [
                    'id', 'telegram_id', 'username', 'first_name', 'last_name',
                    'phone_number', 'balance', 'is_admin', 'is_active', 
                    'language_code', 'timezone', 'created_at', 'updated_at', 'last_login'
                ],
                'id_column': 'id'
            },
            'channels': {
                'columns': [
                    'id', 'owner_id', 'title', 'username', 'description', 'category',
                    'subscriber_count', 'price_per_post', 'is_verified', 'is_active', 
                    'verification_code', 'verification_expires_at', 'last_stats_update',
                    'created_at', 'updated_at'
                ],
                'id_column': 'id'
            },
            'offers': {
                'columns': [
                    'id', 'created_by', 'advertiser_id', 'title', 'description', 
                    'target_audience', 'budget_total', 'price', 'currency', 'status',
                    'category', 'placement_type', 'start_date', 'end_date',
                    'created_at', 'updated_at', 'expires_at'
                ],
                'id_column': 'id'
            },
            'offer_responses': {
                'source_table': 'offer_proposals',  # Переименованная таблица
                'columns': [
                    'id', 'offer_id', 'channel_id', 'user_id', 'status', 
                    'response_message', 'proposed_price', 'counter_offers_count',
                    'created_at', 'updated_at', 'responded_at', 'expires_at'
                ],
                'id_column': 'id'
            },
            'offer_placements': {
                'columns': [
                    'id', 'response_id', 'status', 'post_url', 
                    'placement_start', 'placement_end', 'views_count', 'clicks_count',
                    'engagement_rate', 'created_at', 'updated_at'
                ],
                'id_column': 'id'
            },
            'payments': {
                'columns': [
                    'id', 'user_id', 'offer_id', 'placement_id', 'amount', 'currency',
                    'payment_type', 'status', 'provider', 'provider_payment_id',
                    'description', 'created_at', 'updated_at', 'processed_at'
                ],
                'id_column': 'id'
            },
            'analytics_events': {
                'columns': [
                    'id', 'user_id', 'channel_id', 'offer_id', 'event_type',
                    'event_data', 'session_id', 'ip_address', 'user_agent', 'created_at'
                ],
                'id_column': 'id'
            },
            'notifications': {
                'columns': [
                    'id', 'user_id', 'title', 'message', 'notification_type',
                    'is_read', 'data', 'created_at', 'read_at'
                ],
                'id_column': 'id'
            }
        }
    
    def connect_sqlite(self) -> sqlite3.Connection:
        """Подключение к SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            logger.info(f"✅ Подключение к SQLite: {self.sqlite_path}")
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к SQLite: {e}")
            raise
    
    def connect_postgres(self) -> psycopg2.extensions.connection:
        """Подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            conn.autocommit = False
            logger.info(f"✅ Подключение к PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def run_sql_file(self, pg_conn: psycopg2.extensions.connection, sql_file: str):
        """Выполнение SQL файла"""
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            cursor = pg_conn.cursor()
            cursor.execute(sql_content)
            pg_conn.commit()
            logger.info(f"✅ Выполнен SQL файл: {sql_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения SQL файла {sql_file}: {e}")
            pg_conn.rollback()
            raise
    
    def check_table_exists(self, sqlite_conn: sqlite3.Connection, table_name: str) -> bool:
        """Проверка существования таблицы в SQLite"""
        cursor = sqlite_conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return cursor.fetchone() is not None
    
    def get_table_data(self, sqlite_conn: sqlite3.Connection, table_name: str, columns: List[str]) -> List[Dict]:
        """Получение данных из таблицы SQLite"""
        try:
            cursor = sqlite_conn.cursor()
            
            # Проверяем какие столбцы существуют
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Берем только существующие столбцы
            valid_columns = [col for col in columns if col in existing_columns]
            
            if not valid_columns:
                logger.warning(f"⚠️ Нет валидных столбцов для таблицы {table_name}")
                return []
            
            columns_str = ', '.join(valid_columns)
            cursor.execute(f"SELECT {columns_str} FROM {table_name}")
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                item = {}
                for i, col in enumerate(valid_columns):
                    value = row[i]
                    
                    # Обработка JSON полей
                    if col in ['event_data', 'data', 'details'] and isinstance(value, str):
                        try:
                            item[col] = json.loads(value)
                        except:
                            item[col] = value
                    else:
                        item[col] = value
                
                result.append(item)
            
            logger.info(f"📊 Получено {len(result)} записей из таблицы {table_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных из {table_name}: {e}")
            return []
    
    def insert_data_to_postgres(self, pg_conn: psycopg2.extensions.connection, 
                               table_name: str, data: List[Dict], columns: List[str]):
        """Вставка данных в PostgreSQL"""
        if not data:
            logger.info(f"⏭️ Нет данных для вставки в {table_name}")
            return
        
        try:
            cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Подготавливаем данные для вставки
            values_list = []
            for item in data:
                values = []
                for col in columns:
                    value = item.get(col)
                    
                    # Специальная обработка для JSONB полей
                    if col in ['event_data', 'data', 'details'] and value is not None:
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                    
                    values.append(value)
                
                values_list.append(values)
            
            # Формируем запрос
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            query = f"""
                INSERT INTO {table_name} ({columns_str}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # Выполняем batch insert
            cursor.executemany(query, values_list)
            pg_conn.commit()
            
            logger.info(f"✅ Вставлено {cursor.rowcount} записей в {table_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка вставки данных в {table_name}: {e}")
            pg_conn.rollback()
            raise
    
    def migrate_table(self, sqlite_conn: sqlite3.Connection, 
                     pg_conn: psycopg2.extensions.connection, 
                     target_table: str, mapping: Dict):
        """Миграция одной таблицы"""
        logger.info(f"🔄 Начинаем миграцию таблицы {target_table}")
        
        # Определяем исходную таблицу
        source_table = mapping.get('source_table', target_table)
        
        # Проверяем существование исходной таблицы
        if not self.check_table_exists(sqlite_conn, source_table):
            logger.warning(f"⚠️ Таблица {source_table} не найдена в SQLite")
            return
        
        # Получаем данные
        data = self.get_table_data(sqlite_conn, source_table, mapping['columns'])
        
        # Вставляем данные
        if data:
            self.insert_data_to_postgres(pg_conn, target_table, data, mapping['columns'])
        
        logger.info(f"✅ Миграция таблицы {target_table} завершена")
    
    def update_sequences(self, pg_conn: psycopg2.extensions.connection):
        """Обновление последовательностей PostgreSQL"""
        try:
            cursor = pg_conn.cursor()
            
            # Получаем все таблицы с SERIAL столбцами
            cursor.execute("""
                SELECT schemaname, tablename, columnname, sequencename
                FROM pg_sequences 
                WHERE schemaname = 'public'
            """)
            
            sequences = cursor.fetchall()
            
            for schema, table, column, sequence in sequences:
                cursor.execute(f"""
                    SELECT setval('{sequence}', 
                           COALESCE((SELECT MAX({column}) FROM {table}), 1))
                """)
                
                logger.info(f"✅ Обновлена последовательность {sequence}")
            
            pg_conn.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления последовательностей: {e}")
            pg_conn.rollback()
    
    def verify_migration(self, sqlite_conn: sqlite3.Connection, 
                        pg_conn: psycopg2.extensions.connection):
        """Проверка корректности миграции"""
        logger.info("🔍 Проверка корректности миграции")
        
        cursor_pg = pg_conn.cursor()
        cursor_sqlite = sqlite_conn.cursor()
        
        errors = []
        
        for table_name, mapping in self.table_mappings.items():
            source_table = mapping.get('source_table', table_name)
            
            # Проверяем количество записей
            if self.check_table_exists(sqlite_conn, source_table):
                cursor_sqlite.execute(f"SELECT COUNT(*) FROM {source_table}")
                sqlite_count = cursor_sqlite.fetchone()[0]
                
                cursor_pg.execute(f"SELECT COUNT(*) FROM {table_name}")
                pg_count = cursor_pg.fetchone()[0]
                
                if sqlite_count != pg_count:
                    error_msg = f"❌ {table_name}: SQLite={sqlite_count}, PostgreSQL={pg_count}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                else:
                    logger.info(f"✅ {table_name}: {pg_count} записей")
        
        if errors:
            logger.error("❌ Обнаружены ошибки миграции:")
            for error in errors:
                logger.error(f"  {error}")
            return False
        else:
            logger.info("✅ Миграция прошла успешно!")
            return True
    
    def run_migration(self):
        """Запуск полной миграции"""
        logger.info("🚀 Начинаем миграцию данных из SQLite в PostgreSQL")
        
        # Проверяем существование SQLite файла
        if not os.path.exists(self.sqlite_path):
            logger.error(f"❌ SQLite файл не найден: {self.sqlite_path}")
            return False
        
        try:
            # Подключения к базам данных
            sqlite_conn = self.connect_sqlite()
            pg_conn = self.connect_postgres()
            
            # Выполняем миграционные скрипты
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            
            migration_files = [
                '001_initial_schema.sql',
                '002_performance_optimizations.sql'
            ]
            
            for migration_file in migration_files:
                file_path = os.path.join(migrations_dir, migration_file)
                if os.path.exists(file_path):
                    self.run_sql_file(pg_conn, file_path)
                else:
                    logger.warning(f"⚠️ Миграционный файл не найден: {file_path}")
            
            # Мигрируем данные по таблицам
            for table_name, mapping in self.table_mappings.items():
                self.migrate_table(sqlite_conn, pg_conn, table_name, mapping)
            
            # Обновляем последовательности
            self.update_sequences(pg_conn)
            
            # Проверяем корректность миграции
            success = self.verify_migration(sqlite_conn, pg_conn)
            
            # Закрываем соединения
            sqlite_conn.close()
            pg_conn.close()
            
            if success:
                logger.info("🎉 Миграция завершена успешно!")
                
                # Создаем backup SQLite файла
                backup_path = f"{self.sqlite_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.sqlite_path, backup_path)
                logger.info(f"💾 SQLite файл сохранен как backup: {backup_path}")
                
                return True
            else:
                logger.error("❌ Миграция завершена с ошибками")
                return False
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка миграции: {e}")
            return False

def main():
    """Главная функция"""
    migrator = DatabaseMigrator()
    
    # Спрашиваем подтверждение
    print("⚠️  ВНИМАНИЕ: Будет выполнена миграция данных из SQLite в PostgreSQL")
    print(f"📁 SQLite: {migrator.sqlite_path}")
    print(f"🐘 PostgreSQL: {migrator.postgres_url}")
    print()
    
    confirm = input("Продолжить миграцию? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y', 'да', 'д']:
        success = migrator.run_migration()
        sys.exit(0 if success else 1)
    else:
        print("❌ Миграция отменена")
        sys.exit(0)

if __name__ == "__main__":
    main()