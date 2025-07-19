#!/usr/bin/env python3
"""
Общие фикстуры и настройки для pytest
tests/conftest.py
"""

import sys
import os
import pytest
import logging

# Настройка путей для импорта
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | TEST | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


@pytest.fixture
def test_user():
    """Фикстура тестового пользователя"""
    return {
        'telegram_id': 9999999,
        'username': 'test_user',
        'first_name': 'Test User'
    }


@pytest.fixture
def test_admin_user():
    """Фикстура тестового администратора"""
    return {
        'telegram_id': 9999998,
        'username': 'test_admin',
        'first_name': 'Test Admin',
        'is_admin': True
    }


@pytest.fixture
def api_headers(test_user):
    """Стандартные заголовки для API тестов"""
    return {
        'Content-Type': 'application/json',
        'X-Telegram-User-Id': str(test_user['telegram_id'])
    }


@pytest.fixture
def cleanup_test_data():
    """Фикстура очистки тестовых данных"""
    # Очистка перед тестом
    _cleanup_database()
    
    yield
    
    # Очистка после теста
    _cleanup_database()


def _cleanup_database():
    """Очистка тестовых данных из БД"""
    try:
        from app.models.database import execute_db_query
        
        test_telegram_ids = [9999999, 9999998, 9999997, 9999996, 9999995]
        
        for telegram_id in test_telegram_ids:
            # Удаляем связанные данные
            execute_db_query("DELETE FROM offer_responses WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)", (telegram_id,))
            execute_db_query("DELETE FROM offers WHERE created_by IN (SELECT id FROM users WHERE telegram_id = ?)", (telegram_id,))
            execute_db_query("DELETE FROM channels WHERE owner_id IN (SELECT id FROM users WHERE telegram_id = ?)", (telegram_id,))
            execute_db_query("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
            
        logger.debug("✅ Тестовые данные очищены")
        
    except Exception as e:
        logger.warning(f"⚠️ Предупреждение при очистке тестов: {e}")


# Настройки pytest
def pytest_configure(config):
    """Конфигурация pytest"""
    # Добавляем маркеры
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests") 
    config.addinivalue_line("markers", "system: system tests")
    config.addinivalue_line("markers", "slow: slow running tests")


def pytest_collection_modifyitems(config, items):
    """Модификация собранных тестов"""
    for item in items:
        # Автоматически добавляем маркеры на основе пути
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "system" in str(item.fspath):
            item.add_marker(pytest.mark.system)