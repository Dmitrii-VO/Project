#!/usr/bin/env python3
"""
Исправление недостающих колонок в базе данных
"""

import os
import sys
import logging

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_channels_table():
    """Исправляет таблицу channels, добавляя недостающие колонки"""
    logger.info("🔧 Исправление таблицы channels...")
    
    # Список недостающих колонок для таблицы channels
    missing_columns = [
        ("subscribers", "INTEGER DEFAULT 0"),
        ("description", "TEXT DEFAULT ''"),
        ("channel_type", "TEXT DEFAULT 'public'"),
        ("language", "TEXT DEFAULT 'ru'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    
    success_count = 0
    
    for column_name, column_definition in missing_columns:
        try:
            # Проверяем, существует ли колонка
            result = execute_db_query(f"PRAGMA table_info(channels)")
            existing_columns = [row['name'] for row in result] if result else []
            
            if column_name in existing_columns:
                logger.info(f"✅ Колонка channels.{column_name} уже существует")
                success_count += 1
            else:
                # Добавляем колонку
                sql = f"ALTER TABLE channels ADD COLUMN {column_name} {column_definition}"
                execute_db_query(sql)
                logger.info(f"➕ Добавлена колонка channels.{column_name}")
                success_count += 1
                
        except Exception as e:
            logger.error(f"❌ Ошибка с колонкой channels.{column_name}: {e}")
    
    return success_count == len(missing_columns)

def fix_offers_table():
    """Исправляет таблицу offers"""
    logger.info("🔧 Исправление таблицы offers...")
    
    missing_columns = [
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    
    success_count = 0
    
    for column_name, column_definition in missing_columns:
        try:
            result = execute_db_query(f"PRAGMA table_info(offers)")
            existing_columns = [row['name'] for row in result] if result else []
            
            if column_name in existing_columns:
                logger.info(f"✅ Колонка offers.{column_name} уже существует")
                success_count += 1
            else:
                sql = f"ALTER TABLE offers ADD COLUMN {column_name} {column_definition}"
                execute_db_query(sql)
                logger.info(f"➕ Добавлена колонка offers.{column_name}")
                success_count += 1
                
        except Exception as e:
            logger.error(f"❌ Ошибка с колонкой offers.{column_name}: {e}")
    
    return success_count == len(missing_columns)

def test_fixed_database():
    """Тестирует исправленную базу данных"""
    logger.info("🧪 Тестирование исправленной базы данных...")
    
    try:
        # Тест каналов с новой колонкой subscribers
        channels = execute_db_query('SELECT id, title, subscribers FROM channels LIMIT 3', fetch_all=True)
        if channels:
            logger.info(f"✅ Каналы загружены: {len(channels)}")
            for channel in channels:
                logger.info(f"   ID: {channel['id']}, Подписчики: {channel['subscribers']}")
        else:
            logger.info("ℹ️ Каналы не найдены, но запрос выполнился успешно")
        
        # Тест офферов
        offers = execute_db_query('SELECT id, title, price FROM offers LIMIT 3', fetch_all=True)
        logger.info(f"✅ Офферы: найдено {len(offers) if offers else 0}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        return False

def main():
    """Главная функция исправления"""
    logger.info("🚀 ИСПРАВЛЕНИЕ НЕДОСТАЮЩИХ КОЛОНОК")
    logger.info("="*50)
    
    try:
        # Исправляем таблицы
        channels_ok = fix_channels_table()
        offers_ok = fix_offers_table()
        
        if channels_ok and offers_ok:
            logger.info("✅ Все таблицы исправлены успешно!")
            
            # Тестируем
            if test_fixed_database():
                logger.info("🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
                logger.info("✅ База данных теперь полностью функциональна")
                return True
            else:
                logger.error("❌ Тестирование показало проблемы")
                return False
        else:
            logger.error("❌ Не все таблицы удалось исправить")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return False

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)