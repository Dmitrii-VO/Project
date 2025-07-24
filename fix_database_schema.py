#!/usr/bin/env python3
"""
Исправление схемы базы данных для полной совместимости
Добавляет все недостающие колонки в таблицы
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query, db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список всех недостающих колонок для исправления
MISSING_COLUMNS = [
    # Таблица offers - основные недостающие колонки
    ("offers", "ad_text", "TEXT DEFAULT ''"),
    ("offers", "media_urls", "TEXT DEFAULT '[]'"),
    ("offers", "content_type", "TEXT DEFAULT 'text'"),
    ("offers", "offer_type", "TEXT DEFAULT 'single_post'"),
    ("offers", "budget", "DECIMAL(10,2) DEFAULT 0"),
    ("offers", "max_price_per_post", "DECIMAL(10,2) DEFAULT 0"),
    ("offers", "subcategory", "TEXT DEFAULT ''"),
    ("offers", "target_audience", "TEXT DEFAULT '{}'"),
    ("offers", "targeting_criteria", "TEXT DEFAULT '{}'"),
    ("offers", "posting_requirements", "TEXT DEFAULT '{}'"),
    ("offers", "advertiser_id", "INTEGER"),
    ("offers", "analytics_goals", "TEXT DEFAULT '{}'"),
    
    # Таблица users - дополнительные поля
    ("users", "is_verified", "BOOLEAN DEFAULT 0"),
    ("users", "verification_status", "TEXT DEFAULT 'pending'"),
    ("users", "role", "TEXT DEFAULT 'user'"),
    ("users", "last_login", "TIMESTAMP"),
    ("users", "preferences", "TEXT DEFAULT '{}'"),
    ("users", "notification_settings", "TEXT DEFAULT '{}'"),
    
    # Таблица channels - расширенные поля
    ("channels", "verification_code", "TEXT"),
    ("channels", "verification_status", "TEXT DEFAULT 'pending'"),
    ("channels", "verified_at", "TIMESTAMP"),
    ("channels", "auto_stats_enabled", "BOOLEAN DEFAULT 1"),
    ("channels", "last_stats_update", "TIMESTAMP"),
    ("channels", "channel_stats", "TEXT DEFAULT '{}'"),
    ("channels", "channel_category", "TEXT DEFAULT 'general'"),
    ("channels", "target_audience", "TEXT DEFAULT '{}'"),
    ("channels", "pricing_info", "TEXT DEFAULT '{}'"),
    
    # Таблица offer_placements - статистика и мониторинг
    ("offer_placements", "views_count", "INTEGER DEFAULT 0"),
    ("offer_placements", "clicks_count", "INTEGER DEFAULT 0"),
    ("offer_placements", "conversion_count", "INTEGER DEFAULT 0"),
    ("offer_placements", "revenue_generated", "DECIMAL(10,2) DEFAULT 0"),
    ("offer_placements", "cpm", "DECIMAL(10,2) DEFAULT 0"),
    ("offer_placements", "ctr", "DECIMAL(5,2) DEFAULT 0"),
    ("offer_placements", "engagement_rate", "DECIMAL(5,2) DEFAULT 0"),
    ("offer_placements", "completion_rate", "DECIMAL(5,2) DEFAULT 0"),
    ("offer_placements", "performance_metrics", "TEXT DEFAULT '{}'"),
    ("offer_placements", "monitoring_status", "TEXT DEFAULT 'active'"),
    ("offer_placements", "last_monitored", "TIMESTAMP"),
    ("offer_placements", "payment_status", "TEXT DEFAULT 'pending'"),
    ("offer_placements", "payment_amount", "DECIMAL(10,2) DEFAULT 0"),
    ("offer_placements", "commission_rate", "DECIMAL(5,2) DEFAULT 0"),
]

def check_column_exists(table_name, column_name):
    """Проверяет существует ли колонка в таблице"""
    try:
        result = execute_db_query(f"PRAGMA table_info({table_name})")
        if result:
            existing_columns = [row['name'] for row in result]
            return column_name in existing_columns
        return False
    except Exception as e:
        logger.warning(f"Ошибка проверки колонки {table_name}.{column_name}: {e}")
        return False

def add_missing_column(table_name, column_name, column_definition):
    """Добавляет недостающую колонку в таблицу"""
    try:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        logger.info(f"  Добавляем колонку: {table_name}.{column_name}")
        execute_db_query(sql)
        return True
    except Exception as e:
        logger.error(f"  ❌ Ошибка добавления {table_name}.{column_name}: {e}")
        return False

def create_migration_history_table():
    """Создает таблицу для отслеживания миграций"""
    try:
        sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            status TEXT DEFAULT 'completed'
        )
        """
        execute_db_query(sql)
        logger.info("✅ Таблица migration_history создана")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка создания migration_history: {e}")
        return False

def record_migration(version, description):
    """Записывает информацию о выполненной миграции"""
    try:
        sql = """
        INSERT OR REPLACE INTO migration_history (version, description, applied_at)
        VALUES (?, ?, ?)
        """
        execute_db_query(sql, (version, description, datetime.now()))
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка записи миграции: {e}")
        return False

def verify_database_structure():
    """Проверяет структуру основных таблиц"""
    logger.info("🔍 Проверка структуры базы данных...")
    
    # Основные таблицы, которые должны существовать
    required_tables = ['users', 'channels', 'offers', 'offer_placements']
    
    for table in required_tables:
        try:
            result = execute_db_query(f"SELECT COUNT(*) as count FROM {table}")
            if result:
                count = result[0]['count']
                logger.info(f"  ✅ Таблица {table}: {count} записей")
            else:
                logger.warning(f"  ⚠️ Таблица {table} пуста или недоступна")
        except Exception as e:
            logger.error(f"  ❌ Ошибка проверки таблицы {table}: {e}")

def fix_database_schema():
    """Основная функция исправления схемы базы данных"""
    logger.info("🚀 Начинаем исправление схемы базы данных...")
    
    # Проверяем структуру БД
    verify_database_structure()
    
    # Создаем таблицу миграций
    create_migration_history_table()
    
    # Счетчики для отчета
    total_columns = len(MISSING_COLUMNS)
    added_columns = 0
    skipped_columns = 0
    failed_columns = 0
    
    logger.info(f"📊 Проверяем {total_columns} потенциально недостающих колонок...")
    
    # Обрабатываем каждую недостающую колонку
    for table_name, column_name, column_definition in MISSING_COLUMNS:
        logger.info(f"🔍 Проверяем {table_name}.{column_name}...")
        
        if check_column_exists(table_name, column_name):
            logger.info(f"  ✅ Колонка {column_name} уже существует")
            skipped_columns += 1
        else:
            logger.info(f"  ➕ Добавляем недостающую колонку {column_name}")
            if add_missing_column(table_name, column_name, column_definition):
                added_columns += 1
            else:
                failed_columns += 1
    
    # Записываем информацию о миграции
    migration_version = f"schema_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    migration_description = f"Исправление схемы БД: добавлено {added_columns} колонок"
    record_migration(migration_version, migration_description)
    
    # Финальный отчет
    logger.info("\n" + "="*60)
    logger.info("📊 ОТЧЕТ ОБ ИСПРАВЛЕНИИ СХЕМЫ БАЗЫ ДАННЫХ")
    logger.info("="*60)
    logger.info(f"✅ Колонок добавлено: {added_columns}")
    logger.info(f"⏭️ Колонок пропущено (уже существуют): {skipped_columns}")
    logger.info(f"❌ Ошибок при добавлении: {failed_columns}")
    logger.info(f"📈 Всего обработано: {total_columns}")
    
    if failed_columns == 0:
        logger.info("🎉 ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО!")
        logger.info("✅ База данных теперь полностью совместима")
        return True
    else:
        logger.warning(f"⚠️ Обнаружены проблемы с {failed_columns} колонками")
        return False

def test_fixed_schema():
    """Тестирует исправленную схему"""
    logger.info("\n🧪 Тестирование исправленной схемы...")
    
    # Тест 1: Проверяем ключевые колонки offers
    try:
        result = execute_db_query("SELECT ad_text, media_urls, content_type FROM offers LIMIT 1")
        logger.info("✅ Тест offers.ad_text - успешно")
    except Exception as e:
        logger.error(f"❌ Тест offers.ad_text - ошибка: {e}")
    
    # Тест 2: Проверяем расширенные поля users
    try:
        result = execute_db_query("SELECT is_verified, role, balance FROM users LIMIT 1")
        logger.info("✅ Тест users расширенные поля - успешно")
    except Exception as e:
        logger.error(f"❌ Тест users расширенные поля - ошибка: {e}")
    
    # Тест 3: Проверяем поля каналов
    try:
        result = execute_db_query("SELECT verification_status, channel_stats FROM channels LIMIT 1")
        logger.info("✅ Тест channels расширенные поля - успешно")
    except Exception as e:
        logger.error(f"❌ Тест channels расширенные поля - ошибка: {e}")
    
    # Тест 4: Проверяем статистику размещений
    try:
        result = execute_db_query("SELECT views_count, clicks_count, revenue_generated FROM offer_placements LIMIT 1")
        logger.info("✅ Тест offer_placements статистика - успешно")
    except Exception as e:
        logger.error(f"❌ Тест offer_placements статистика - ошибка: {e}")

if __name__ == '__main__':
    logger.info("🔧 ИСПРАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ")
    logger.info("="*50)
    
    try:
        success = fix_database_schema()
        
        if success:
            test_fixed_schema()
            logger.info("\n🏁 Исправление схемы завершено успешно!")
        else:
            logger.error("\n❌ В процессе исправления схемы возникли ошибки")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)