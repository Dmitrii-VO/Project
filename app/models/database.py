import sqlite3
import logging
import os
from typing import Optional, Dict, Any, List, Union
from app.config.settings import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных SQLite"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH

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
# Глобальный экземпляр
db_manager = DatabaseManager()


# Функция для обратной совместимости
def safe_execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Обертка для обратной совместимости"""
    return db_manager.execute_query(query, params, fetch_one, fetch_all)