# app/models/database.py
# ИСПРАВЛЕНО: БД + работа с пользователями, ленивый импорт auth_service

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
    def ensure_user_exists(telegram_id: int, username: str = None, first_name: str = None) -> Optional[int]:
        """
        Обеспечение существования пользователя в базе по Telegram ID
        ПЕРЕНЕСЕНО из auth_service.py
        """
        try:
            # Проверяем существование пользователя
            user = db_manager.execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )

            if not user:
                # ✅ ИСПРАВЛЕНО: создаем без несуществующих полей user_type, status
                logger.info(f"Creating new user for Telegram ID: {telegram_id}")

                user_db_id = db_manager.execute_query('''
                    INSERT INTO users (telegram_id, username, first_name, is_admin, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    telegram_id,
                    username or f'user_{telegram_id}',
                    first_name or 'Telegram User',
                    telegram_id == AppConfig.YOUR_TELEGRAM_ID,  # Админ если это YOUR_TELEGRAM_ID
                    datetime.datetime.now().isoformat(),
                    datetime.datetime.now().isoformat()
                ))

                return user_db_id
            else:
                # Обновляем информацию о существующем пользователе
                if username or first_name:
                    db_manager.execute_query('''
                        UPDATE users
                        SET username = COALESCE(?, username),
                            first_name = COALESCE(?, first_name),
                            updated_at = ?
                        WHERE telegram_id = ?
                    ''', (username, first_name, datetime.datetime.now().isoformat(), telegram_id))

                return user['id']

        except Exception as e:
            logger.error(f"Ошибка создания/обновления пользователя {telegram_id}: {e}")
            return None

    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
        """Получение пользователя по Telegram ID"""
        try:
            return db_manager.execute_query(
                'SELECT * FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {telegram_id}: {e}")
            return None

    @staticmethod
    def create_user_from_legacy(user_id: int, username: str = None, first_name: str = None) -> int:
        """Создание пользователя (legacy метод для обратной совместимости)"""
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )

        if not user:
            user_db_id = db_manager.execute_query('''
                INSERT INTO users (telegram_id, username, first_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                username or f'user_{user_id}',
                first_name or 'User',
                datetime.datetime.now().isoformat(),
                datetime.datetime.now().isoformat()
            ))
            logger.info(f"Создан новый пользователь: {user_id}")
            return user_db_id

        return user['id']


# Глобальный экземпляр
db_manager = DatabaseManager()


# === УТИЛИТЫ ===
def get_user_id_from_request():
    """
    Получение user_db_id из запроса
    
    ИСПРАВЛЕНО: ленивый импорт AuthService для избежания циклических импортов
    """
    try:
        # ✅ ЛЕНИВЫЙ ИМПОРТ - импортируем ЭКЗЕМПЛЯР auth_service, а не класс
        from app.services.auth_service import auth_service
        
        # Получаем telegram_id через экземпляр сервиса авторизации
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            logger.warning("⚠️ Database: auth_service.get_current_user_id() вернул None")
            return None
        
        # Конвертируем telegram_id в user_db_id
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ищем пользователя по telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            user_db_id = user['id']
            logger.debug(f"🔍 Database: telegram_id {telegram_id} → user_db_id {user_db_id}")
            return user_db_id
        else:
            logger.warning(f"⚠️ Database: Пользователь с telegram_id {telegram_id} не найден в БД")
            return None
        
    except Exception as e:
        logger.error(f"❌ Database: Ошибка в get_user_id_from_request(): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


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


# Функция для обратной совместимости
def safe_execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Обертка для обратной совместимости"""
    return db_manager.execute_query(query, params, fetch_one, fetch_all)