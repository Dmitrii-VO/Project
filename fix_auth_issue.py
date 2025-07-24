#!/usr/bin/env python3
"""
Скрипт для исправления проблем аутентификации
Создает тестового пользователя если его нет
"""

import os
import sys

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_create_test_user():
    """Проверяет наличие пользователей и создает тестового если нужно"""
    try:
        # Проверяем количество пользователей
        user_count = execute_db_query(
            "SELECT COUNT(*) as count FROM users",
            fetch_one=True
        )
        
        count = user_count['count'] if user_count else 0
        logger.info(f"Количество пользователей в базе: {count}")
        
        if count == 0:
            logger.info("Создаем тестового пользователя...")
            
            # Создаем тестового пользователя
            user_id = execute_db_query("""
                INSERT INTO users (
                    telegram_id, username, first_name, last_name, 
                    is_active, balance, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                1,  # telegram_id
                'testuser',  # username
                'Test',  # first_name  
                'User',  # last_name
                1,  # is_active
                0  # balance
            ))
            
            logger.info(f"Создан тестовый пользователь с ID: {user_id}")
            
        else:
            # Показываем информацию о существующих пользователях
            users = execute_db_query(
                "SELECT id, telegram_id, username, balance FROM users LIMIT 5",
                fetch_all=True
            )
            
            logger.info("Существующие пользователи:")
            for user in users:
                logger.info(f"  ID: {user['id']}, Telegram ID: {user['telegram_id']}, Username: {user.get('username', 'N/A')}, Balance: {user.get('balance', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при работе с пользователями: {e}")
        return False

def check_table_structure():
    """Проверяет структуру таблиц"""
    try:
        # Проверяем структуру таблицы users
        columns = execute_db_query(
            "PRAGMA table_info(users)",
            fetch_all=True
        )
        
        logger.info("Структура таблицы users:")
        for col in columns:
            logger.info(f"  {col['name']} ({col['type']})")
            
        return True
        
    except Exception as e:
        logger.error(f"Ошибка проверки структуры таблиц: {e}")
        return False

def test_api_endpoints():
    """Тестирует API endpoints"""
    try:
        from app.api.analytics import get_current_user_id
        from app.api.payments import get_current_user_for_payments
        
        logger.info("Тестирование функций аутентификации:")
        
        # Тест analytics
        analytics_user_id = get_current_user_id()
        logger.info(f"Analytics user ID: {analytics_user_id}")
        
        # Тест payments  
        payments_user_id = get_current_user_for_payments()
        logger.info(f"Payments user ID: {payments_user_id}")
        
        return analytics_user_id is not None and payments_user_id is not None
        
    except Exception as e:
        logger.error(f"Ошибка тестирования API: {e}")
        return False

if __name__ == '__main__':
    logger.info("🔧 Исправление проблем аутентификации...")
    
    # Проверяем структуру таблиц
    logger.info("1. Проверка структуры таблиц...")
    check_table_structure()
    
    # Создаем тестового пользователя если нужно
    logger.info("2. Проверка и создание тестового пользователя...")
    check_and_create_test_user()
    
    # Тестируем API функции
    logger.info("3. Тестирование API функций...")
    if test_api_endpoints():
        logger.info("✅ Все функции аутентификации работают корректно")
    else:
        logger.warning("⚠️ Обнаружены проблемы с аутентификацией")
    
    logger.info("🏁 Исправление завершено")