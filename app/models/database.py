import sqlite3
import logging
import os
import datetime
from typing import Optional, Dict, Any, List, Union

from flask import request
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных SQLite"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or AppConfig.DATABASE_PATH

    def get_connection(self) -> sqlite3.Connection:
        """Получение подключения к SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Для возврата словарей
            conn.execute('PRAGMA foreign_keys = ON')  # Включаем foreign keys
            return conn
        except Exception as e:
            raise Exception(f"Ошибка подключения к SQLite: {e}")

    def test_connection(self) -> bool:
        """Тестирование подключения к базе данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        
    



    def execute_query(self, query: str, params: tuple = (),
                      fetch_one: bool = False, fetch_all: bool = False) -> Union[Dict, List, int, None]:
        """Безопасное выполнение SQL запросов"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Логируем потенциально опасные запросы
            if any(keyword in query.upper() for keyword in ['DROP', 'DELETE', 'TRUNCATE', 'ALTER']):
                logger.warning(f"Potentially dangerous query executed: {query[:100]}...")

            cursor.execute(query, params)

            result = None
            if fetch_one:
                row = cursor.fetchone()
                result = dict(row) if row else None
            elif fetch_all:
                rows = cursor.fetchall()
                result = [dict(row) for row in rows] if rows else []
            else:
                conn.commit()
                result = cursor.lastrowid

            conn.close()
            return result

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in execute_query: {e}")
            if 'conn' in locals():
                conn.close()
            raise  # Поднимаем исключение вместо возврата None

    def init_database(self) -> bool:
        """Проверка и инициализация базы данных"""
        try:
            logger.info("🗄️ Проверка SQLite базы данных...")

            if not os.path.exists(self.db_path):
                logger.error(f"❌ База данных не найдена: {self.db_path}")
                logger.info("Запустите sqlite_migration.py для создания базы данных")
                return False

            # Проверяем таблицы
            tables = self.execute_query("""
                                        SELECT name
                                        FROM sqlite_master
                                        WHERE type = 'table'
                                          AND name IN ('users', 'channels', 'offers', 'offer_responses')
                                        """, fetch_all=True)

            if not tables or len(tables) < 4:
                logger.error(f"❌ Не все таблицы найдены. Найдено: {len(tables) if tables else 0}")
                logger.info("Запустите sqlite_migration.py для создания схемы")
                return False

            logger.info("✅ SQLite база данных готова к работе")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации SQLite: {e}")
            return False


    def ensure_user_exists(self, telegram_id: int, username: str = None, first_name: str = None) -> int:
        """Обеспечивает существование пользователя в БД"""
        try:
            # Проверяем существование
            user = self.execute_query(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,),
                fetch_one=True
            )

            if user:
                return user['id']

            # Создаем нового пользователя
            user_id = self.execute_query("""
                                         INSERT INTO users (telegram_id, username, first_name, user_type, status, created_at)
                                         VALUES (?, ?, ?, 'channel_owner', 'active', CURRENT_TIMESTAMP)
                                         """, (
                                             telegram_id,
                                             username or f'user_{telegram_id}',
                                             first_name or 'User'
                                         ))

            return user_id

        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            return None


# ===== ВАЛИДАЦИЯ =====
class OfferValidator:
    @staticmethod
    def validate_offer_data(data: Dict[str, Any]) -> List[str]:
        """Валидация данных оффера"""
        errors = []

        # Обязательные поля
        if not data.get('title', '').strip():
            errors.append('Название оффера обязательно')

        description = data.get('description', '').strip()
        content = data.get('content', '').strip()
        if not description and not content:
            errors.append('Описание оффера обязательно')

        # Проверка цены
        price = OfferValidator._get_offer_price(data)
        if price <= 0:
            errors.append('Укажите корректную цену за размещение или общий бюджет')

        # Проверка длины полей
        title = data.get('title', '').strip()
        if title and (len(title) < 5 or len(title) > 200):
            errors.append('Название должно быть от 5 до 200 символов')

        # Проверка диапазона цены
        if price < 10 or price > 1000000:
            errors.append('Цена должна быть от 10 до 1,000,000 рублей')

        # Проверка валюты
        currency = data.get('currency', 'RUB').upper()
        if currency not in ['RUB', 'USD', 'EUR']:
            errors.append('Валюта должна быть одной из: RUB, USD, EUR')

        # Проверка категории
        category = data.get('category', 'general')
        allowed_categories = [
            'general', 'tech', 'finance', 'lifestyle', 'education',
            'entertainment', 'business', 'health', 'sports', 'travel', 'other'
        ]
        if category not in allowed_categories:
            errors.append(f'Категория должна быть одной из: {", ".join(allowed_categories)}')

        return errors

    @staticmethod
    def _get_offer_price(data: Dict[str, Any]) -> float:
        """Определение цены оффера с fallback логикой"""
        price = data.get('price', 0)
        max_price = data.get('max_price', 0)
        budget_total = data.get('budget_total', 0)

        if price and float(price) > 0:
            return float(price)
        elif max_price and float(max_price) > 0:
            return float(max_price)
        elif budget_total and float(budget_total) > 0:
            return min(float(budget_total) * 0.1, 50000)

        return 0


# ===== МЕНЕДЖЕР ПОЛЬЗОВАТЕЛЕЙ =====
class UserManager:
    @staticmethod
    def ensure_user_exists(user_id: int, username: str = None, first_name: str = None) -> int:
        """Убеждаемся что пользователь существует в БД"""
        user = DatabaseManager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )

        if not user:
            user_db_id = DatabaseManager.execute_query('''
                                                       INSERT INTO users (telegram_id, username, first_name, created_at)
                                                       VALUES (?, ?, ?, ?)
                                                       ''', (
                                                           user_id,
                                                           username or f'user_{user_id}',
                                                           first_name or 'User',
                                                           datetime.now().isoformat()
                                                       ))
            logger.info(f"Создан новый пользователь: {user_id}")
            return user_db_id

        return user['id']

# Глобальный экземпляр
db_manager = DatabaseManager()


# Функция для обратной совместимости
def safe_execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Обертка для обратной совместимости"""
    return db_manager.execute_query(query, params, fetch_one, fetch_all)


# === УТИЛИТЫ ===
def get_user_id_from_request():
    """Получение user_id из заголовков запроса"""
    user_id = request.headers.get('X-Telegram-User-Id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    # Fallback к основному пользователю
    fallback_id = os.environ.get('YOUR_TELEGRAM_ID', '373086959')
    try:
        return int(fallback_id)
    except (ValueError, TypeError):
        return 373086959 
        
def execute_db_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Универсальная функция для работы с БД"""
    try:
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None
        elif fetch_all:
            result = cursor.fetchall()
            conn.close()
            return [dict(row) for row in result] if result else []
        else:
            conn.commit()
            lastrowid = cursor.lastrowid
            conn.close()
            return lastrowid

    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        if 'conn' in locals():
            conn.close()
        raise

