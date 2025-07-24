#!/usr/bin/env python3
"""
Добавляет колонку balance в таблицу users
"""

import os
import sys

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_balance_column():
    """Добавляет колонку balance в таблицу users"""
    try:
        # Проверяем, есть ли уже колонка balance
        columns = execute_db_query(
            "PRAGMA table_info(users)",
            fetch_all=True
        )
        
        has_balance = any(col['name'] == 'balance' for col in columns)
        
        if has_balance:
            logger.info("✅ Колонка balance уже существует")
            return True
        
        # Добавляем колонку balance
        logger.info("Добавляем колонку balance...")
        execute_db_query(
            "ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0.0"
        )
        
        logger.info("✅ Колонка balance успешно добавлена")
        
        # Устанавливаем тестовый баланс для существующих пользователей
        execute_db_query(
            "UPDATE users SET balance = 1500.0 WHERE telegram_id = 373086959"
        )
        
        logger.info("✅ Установлен тестовый баланс 1500 руб. для пользователя 373086959")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка добавления колонки balance: {e}")
        return False

if __name__ == '__main__':
    logger.info("🔧 Добавление колонки balance...")
    
    if add_balance_column():
        logger.info("🏁 Операция завершена успешно")
    else:
        logger.error("❌ Операция завершена с ошибками")