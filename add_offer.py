# add_offer.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
import sqlite3
import json
import logging
import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'telegram_mini_app.db'


# ===== УТИЛИТЫ БАЗЫ ДАННЫХ =====
class DatabaseManager:
    @staticmethod
    def get_connection():
        """Получение подключения к SQLite"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        except Exception as e:
            raise Exception(f"Ошибка подключения к SQLite: {e}")

    @staticmethod
    def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        """Безопасное выполнение SQL запросов"""
        try:
            conn = DatabaseManager.get_connection()
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


# ===== ОСНОВНЫЕ ФУНКЦИИ ОФФЕРОВ =====
def add_offer(user_id: int, offer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Создание нового оффера"""
    try:
        logger.info(f"Создание оффера пользователем {user_id}: {offer_data}")

        # Валидация
        errors = OfferValidator.validate_offer_data(offer_data)
        if errors:
            return {'success': False, 'errors': errors}

        # Пользователь
        user_db_id = UserManager.ensure_user_exists(
            user_id,
            offer_data.get('username'),
            offer_data.get('first_name')
        )

        # Подготовка данных
        offer_params = _prepare_offer_data(offer_data, user_db_id)

        # Создание оффера
        offer_id = DatabaseManager.execute_query('''
                                                 INSERT INTO offers (created_by, title, description, content, price,
                                                                     currency,
                                                                     target_audience, requirements, deadline, status,
                                                                     category,
                                                                     metadata, budget_total, expires_at, duration_days,
                                                                     min_subscribers, max_subscribers)
                                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                 ''', offer_params)

        logger.info(f"Создан новый оффер {offer_id} пользователем {user_id}")

        # Получаем созданный оффер
        created_offer = DatabaseManager.execute_query('''
                                                      SELECT o.*, u.username, u.first_name
                                                      FROM offers o
                                                               JOIN users u ON o.created_by = u.id
                                                      WHERE o.id = ?
                                                      ''', (offer_id,), fetch_one=True)

        return {
            'success': True,
            'offer_id': offer_id,
            'offer': created_offer,
            'message': 'Оффер успешно создан'
        }

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return {
            'success': False,
            'error': f'Ошибка создания оффера: {str(e)}'
        }


def _prepare_offer_data(offer_data: Dict[str, Any], user_db_id: int) -> tuple:
    """Подготовка данных для вставки в БД"""
    title = offer_data['title'].strip()
    description = offer_data.get('description', '').strip()
    content = offer_data.get('content', '').strip()

    # Логика для description и content
    if not description and content:
        description = content[:200] + "..." if len(content) > 200 else content
    elif not description:
        description = title

    if not content:
        content = description

    # Цена с fallback логикой
    price = OfferValidator._get_offer_price(offer_data)
    currency = offer_data.get('currency', 'RUB').upper()
    category = offer_data.get('category', 'general')

    # Дополнительные параметры
    target_audience = offer_data.get('target_audience', '').strip()
    requirements = offer_data.get('requirements', '').strip()
    duration_days = int(offer_data.get('duration_days', 30))

    # Бюджет
    budget_total = float(offer_data.get('budget_total', price))
    if budget_total < price:
        budget_total = price

    # Метаданные
    metadata = _build_offer_metadata(offer_data)

    # Даты
    current_time = datetime.now()
    deadline_date = (current_time + timedelta(days=duration_days)).date()
    expires_at = current_time + timedelta(days=duration_days)

    # Подписчики
    min_subscribers = int(offer_data.get('min_subscribers', 1))
    max_subscribers = int(offer_data.get('max_subscribers', 100000000))

    return (
        user_db_id, title, description, content, price, currency,
        target_audience, requirements, deadline_date.isoformat(), 'active', category,
        json.dumps(metadata, ensure_ascii=False), budget_total, expires_at.isoformat(),
        duration_days, min_subscribers, max_subscribers
    )


def _build_offer_metadata(offer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Построение метаданных оффера"""
    return {
        'contact_info': offer_data.get('contact_info', ''),
        'preferred_channels': offer_data.get('preferred_channels', []),
        'geo_targeting': offer_data.get('geo_targeting', []),
        'topics': offer_data.get('topics', ''),
        'geography': offer_data.get('geography', ''),
        'created_via': 'web_interface',
        'original_data': {
            'max_price': offer_data.get('max_price'),
            'budget_total': offer_data.get('budget_total'),
            'price': offer_data.get('price')
        }
    }


def get_user_offers(user_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Получение офферов пользователя"""
    try:
        user = DatabaseManager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        user_db_id = user['id']

        # Запрос с подсчетом откликов
        base_query = '''
                     SELECT o.*,
                            COALESCE(response_stats.response_count, 0) as response_count,
                            COALESCE(response_stats.accepted_count, 0) as accepted_count
                     FROM offers o
                              LEFT JOIN (SELECT offer_id, \
                                                COUNT(*)                                        as response_count, \
                                                COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count \
                                         FROM offer_responses \
                                         GROUP BY offer_id) response_stats ON o.id = response_stats.offer_id
                     WHERE o.created_by = ? \
                     '''

        if status:
            query = base_query + ' AND o.status = ? ORDER BY o.created_at DESC'
            params = (user_db_id, status)
        else:
            query = base_query + ' ORDER BY o.created_at DESC'
            params = (user_db_id,)

        offers = DatabaseManager.execute_query(query, params, fetch_all=True)

        # Форматируем для фронтенда
        formatted_offers = []
        for offer in offers:
            metadata = _parse_offer_metadata(offer.get('metadata', '{}'))

            formatted_offer = {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'content': offer['content'],
                'price': float(offer['price']),
                'currency': offer['currency'],
                'category': offer['category'],
                'status': offer['status'],
                'target_audience': offer.get('target_audience', ''),
                'requirements': offer.get('requirements', ''),
                'deadline': offer.get('deadline', ''),
                'created_at': offer['created_at'],
                'updated_at': offer['updated_at'],
                'response_count': offer.get('response_count', 0),
                'accepted_count': offer.get('accepted_count', 0),
                'budget_total': float(offer.get('budget_total', 0)),
                'duration_days': offer.get('duration_days', 30),
                'min_subscribers': offer.get('min_subscribers', 1),
                'max_subscribers': offer.get('max_subscribers', 100000000),
                'metadata': metadata
            }
            formatted_offers.append(formatted_offer)

        return formatted_offers

    except Exception as e:
        logger.error(f"Ошибка получения офферов пользователя {user_id}: {e}")
        return []


def _parse_offer_metadata(metadata_str: str) -> Dict[str, Any]:
    """Безопасный парсинг метаданных"""
    try:
        return json.loads(metadata_str) if metadata_str else {}
    except:
        return {}


def get_available_offers(filters=None) -> List[Dict[str, Any]]:
    """Получение доступных офферов с фильтрацией"""
    if filters is None:
        filters = {}

    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        base_query = """
                     SELECT o.*, u.first_name, u.last_name, u.username as creator_username
                     FROM offers o
                              LEFT JOIN users u ON o.created_by = u.id
                     WHERE o.status = 'active' \
                     """

        query_params = []
        conditions = []

        # Исключаем офферы текущего пользователя
        exclude_user_id = filters.get('exclude_user_id')
        if exclude_user_id:
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (exclude_user_id,))
            user_row = cursor.fetchone()
            if user_row:
                conditions.append("o.created_by != ?")
                query_params.append(user_row['id'])

        # Применяем фильтры
        filter_mappings = {
            'category': 'o.category = ?',
            'min_budget': 'o.price >= ?',
            'max_budget': 'o.price <= ?',
            'min_subscribers': 'o.min_subscribers <= ?'
        }

        for filter_key, query_condition in filter_mappings.items():
            if filters.get(filter_key):
                conditions.append(query_condition)
                query_params.append(filters[filter_key])

        # Поиск по тексту
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            conditions.append("(o.title LIKE ? OR o.description LIKE ?)")
            query_params.extend([search_term, search_term])

        # Собираем запрос
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " ORDER BY o.created_at DESC LIMIT ?"
        query_params.append(filters.get('limit', 50))

        cursor.execute(base_query, query_params)
        rows = cursor.fetchall()

        offers = []
        for row in rows:
            creator_name = _build_creator_name(row)

            offer = {
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'content': row['content'],
                'price': float(row['price']) if row['price'] else 0,
                'currency': row['currency'] or 'RUB',
                'category': row['category'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'created_by': row['created_by'],
                'creator_name': creator_name,
                'budget_total': float(row['budget_total']) if row['budget_total'] else 0,
                'min_subscribers': row['min_subscribers'] or 0,
                'max_subscribers': row['max_subscribers'] or 0,
                'deadline': row['deadline'],
                'target_audience': row['target_audience'],
                'requirements': row['requirements']
            }
            offers.append(offer)

        conn.close()
        return offers

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return []


def _build_creator_name(row) -> str:
    """Формирование имени создателя"""
    creator_name = ""
    if row['first_name']:
        creator_name += row['first_name']
    if row['last_name']:
        creator_name += f" {row['last_name']}"
    if not creator_name and row['creator_username']:
        creator_name = f"@{row['creator_username']}"
    if not creator_name:
        creator_name = "Анонимный пользователь"
    return creator_name


# ===== УПРАВЛЕНИЕ СТАТУСАМИ =====
def update_offer_status_by_id(offer_id: int, telegram_user_id: int, new_status: str, reason: str = '') -> Dict[
    str, Any]:
    """Универсальная функция обновления статуса оффера"""
    try:
        user = DatabaseManager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return {'success': False, 'error': 'Пользователь не найден'}

        offer = DatabaseManager.execute_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return {'success': False, 'error': 'Оффер не найден'}

        if offer['created_by'] != user['id']:
            return {'success': False, 'error': 'У вас нет прав для изменения этого оффера'}

        # Проверяем допустимость перехода
        status_transitions = {
            'active': ['paused', 'cancelled', 'completed'],
            'paused': ['active', 'cancelled', 'completed'],
            'cancelled': [],
            'completed': []
        }

        current_status = offer['status']
        if new_status not in status_transitions.get(current_status, []):
            return {
                'success': False,
                'error': f'Нельзя изменить статус с "{current_status}" на "{new_status}"'
            }

        # Обновляем статус
        DatabaseManager.execute_query('''
                                      UPDATE offers
                                      SET status     = ?,
                                          updated_at = ?
                                      WHERE id = ?
                                      ''', (new_status, datetime.now().isoformat(), offer_id))

        # Уведомления в зависимости от статуса
        if new_status == 'cancelled':
            _notify_channels_about_cancellation(offer_id, offer['title'])
        elif new_status == 'completed':
            _notify_channels_about_completion(offer_id, offer['title'])

        return {
            'success': True,
            'message': f'Статус оффера "{offer["title"]}" изменен на "{new_status}"',
            'offer_id': offer_id,
            'old_status': current_status,
            'new_status': new_status
        }

    except Exception as e:
        logger.error(f"Ошибка изменения статуса оффера {offer_id}: {e}")
        return {'success': False, 'error': f'Ошибка при изменении статуса оффера: {str(e)}'}


def delete_offer_by_id(offer_id: int, telegram_user_id: int) -> Dict[str, Any]:
    """Удаление оффера с проверкой прав"""
    try:
        user = DatabaseManager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return {'success': False, 'error': 'Пользователь не найден'}

        offer = DatabaseManager.execute_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return {'success': False, 'error': 'Оффер не найден'}

        if offer['created_by'] != user['id']:
            return {'success': False, 'error': 'У вас нет прав для удаления этого оффера'}

        if offer['status'] in ['active', 'paused']:
            return {
                'success': False,
                'error': 'Нельзя удалить активный оффер. Сначала завершите или отмените его.'
            }

        # Удаляем связанные данные и оффер
        conn = DatabaseManager.get_connection()
        conn.execute('BEGIN TRANSACTION')

        try:
            conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
            conn.commit()

            return {
                'success': True,
                'message': f'Оффер "{offer["title"]}" успешно удален',
                'offer_id': offer_id
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при удалении оффера {offer_id}: {e}")
            return {'success': False, 'error': 'Ошибка при удалении оффера'}
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Общая ошибка удаления оффера {offer_id}: {e}")
        return {'success': False, 'error': 'Внутренняя ошибка при удалении оффера'}


# ===== ОТКЛИКИ НА ОФФЕРЫ =====
def update_response_status(response_id, new_status, user_id, message=""):
    """Обновление статуса отклика с автоматическим созданием контракта"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        # Получаем данные отклика
        cursor.execute('''
                       SELECT or_resp.*,
                              o.created_by,
                              o.title       as offer_title,
                              o.price       as offer_price,
                              o.budget_total,
                              u.telegram_id as author_telegram_id
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                                JOIN users u ON o.created_by = u.id
                       WHERE or_resp.id = ?
                       ''', (response_id,))

        response_row = cursor.fetchone()
        if not response_row:
            conn.close()
            return {'success': False, 'error': 'Отклик не найден'}

        if response_row['author_telegram_id'] != user_id:
            conn.close()
            return {'success': False, 'error': 'Нет прав для изменения статуса'}

        if response_row['status'] != 'pending':
            conn.close()
            return {'success': False, 'error': 'Отклик уже обработан'}

        # Обновляем статус отклика
        cursor.execute('''
                       UPDATE offer_responses
                       SET status        = ?,
                           updated_at    = ?,
                           admin_message = ?
                       WHERE id = ?
                       ''', (new_status, datetime.now().isoformat(), message, response_id))

        contract_id = None
        if new_status == 'accepted':
            # Отклоняем остальные отклики
            cursor.execute('''
                           UPDATE offer_responses
                           SET status        = 'rejected',
                               updated_at    = ?,
                               admin_message = 'Автоматически отклонен (выбран другой канал)'
                           WHERE offer_id = ?
                             AND id != ? AND status = 'pending'
                           ''', (datetime.now().isoformat(), response_row['offer_id'], response_id))

            # Создаем контракт
            contract_id = _create_contract_for_response(cursor, response_row)

        conn.commit()
        conn.close()

        # Отправляем уведомления
        try:
            _send_response_notification(response_id, new_status)
            if contract_id:
                _send_contract_notification(contract_id, 'created')
        except Exception as notification_error:
            logger.warning(f"Ошибка отправки уведомления: {notification_error}")

        result = {
            'success': True,
            'message': f'Отклик {"принят" if new_status == "accepted" else "отклонён"}. Пользователь получил уведомление.'
        }

        if contract_id:
            result['contract_id'] = contract_id
            result['contract_created'] = True

        return result

    except Exception as e:
        logger.error(f"Ошибка обновления статуса отклика: {e}")
        return {'success': False, 'error': str(e)}


def _create_contract_for_response(cursor, response_row) -> str:
    """Создание контракта для принятого отклика"""
    contract_id = hashlib.md5(f"{response_row['id']}_{time.time()}".encode()).hexdigest()[:12].upper()

    placement_deadline = datetime.now() + timedelta(hours=24)
    monitoring_duration = 7
    monitoring_end = placement_deadline + timedelta(days=monitoring_duration)
    price = response_row['offer_price'] or response_row['budget_total'] or 1000

    cursor.execute('''
                   INSERT INTO contracts (id, response_id, offer_id, advertiser_id, publisher_id,
                                          price, status, placement_deadline, monitoring_duration,
                                          monitoring_end, post_requirements, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ''', (
                       contract_id, response_row['id'], response_row['offer_id'],
                       response_row['created_by'], response_row['user_id'], price, 'active',
                       placement_deadline.isoformat(), monitoring_duration, monitoring_end.isoformat(),
                       'Согласно условиям оффера', datetime.now().isoformat(), datetime.now().isoformat()
                   ))

    return contract_id


# ===== КОНТРАКТЫ =====
def submit_placement(contract_id, post_url, user_id):
    """Подача заявки о размещении рекламы"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        # Проверяем контракт
        cursor.execute('''
                       SELECT c.*, u.telegram_id as publisher_telegram_id
                       FROM contracts c
                                JOIN users u ON c.publisher_id = u.id
                       WHERE c.id = ?
                         AND u.telegram_id = ?
                         AND c.status = 'active'
                       ''', (contract_id, user_id))

        contract = cursor.fetchone()
        if not contract:
            return {'success': False, 'error': 'Контракт не найден или недоступен'}

        # Проверяем дедлайн
        placement_deadline = datetime.fromisoformat(contract['placement_deadline'])
        if datetime.now() > placement_deadline:
            cursor.execute('UPDATE contracts SET status = ? WHERE id = ?', ('expired', contract_id))
            conn.commit()
            conn.close()
            return {'success': False, 'error': 'Срок размещения истек'}

        # Извлекаем данные из URL
        post_data = extract_post_info_from_url(post_url)
        if not post_data['success']:
            return {'success': False, 'error': post_data['error']}

        # Обновляем контракт
        cursor.execute('''
                       UPDATE contracts
                       SET post_url     = ?,
                           post_id      = ?,
                           status       = 'verification',
                           submitted_at = ?
                       WHERE id = ?
                       ''', (post_url, post_data['message_id'], datetime.now().isoformat(), contract_id))

        conn.commit()
        conn.close()

        # Запускаем проверку
        try:
            verification_result = verify_placement(contract_id)
        except Exception as verify_error:
            logger.error(f"Ошибка автоматической проверки: {verify_error}")

        # Отправляем уведомление
        try:
            _send_contract_notification(contract_id, 'placement_submitted')
        except Exception as notification_error:
            logger.warning(f"Ошибка отправки уведомления: {notification_error}")

        return {
            'success': True,
            'message': 'Заявка о размещении подана! Начинается автоматическая проверка.',
            'contract_id': contract_id
        }

    except Exception as e:
        logger.error(f"Ошибка подачи заявки о размещении: {e}")
        return {'success': False, 'error': f'Ошибка подачи заявки: {str(e)}'}


def verify_placement(contract_id):
    """Проверка размещения рекламы по контракту"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT c.*, o.description as offer_description, or_resp.channel_username
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        contract = cursor.fetchone()
        if not contract:
            conn.close()
            return {'success': False, 'error': 'Контракт не найден'}

        if not contract['post_url']:
            conn.close()
            return {'success': False, 'error': 'URL поста не указан'}

        # Извлекаем данные поста
        post_info = extract_post_info_from_url(contract['post_url'])
        if not post_info['success']:
            conn.close()
            return {'success': False, 'error': post_info['error']}

        # Проверяем пост через Telegram API
        verification_result = check_telegram_post(
            post_info['channel_username'],
            post_info['message_id'],
            contract['offer_description']
        )

        # Обновляем статус контракта
        if verification_result['success']:
            new_status = 'monitoring'
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?,
                               updated_at           = ?
                           WHERE id = ?
                           ''', (new_status, True, json.dumps(verification_result['details']),
                                 datetime.now().isoformat(), contract_id))

            message = "✅ Размещение проверено и подтверждено! Начат мониторинг."
        else:
            new_status = 'verification_failed'
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?,
                               updated_at           = ?
                           WHERE id = ?
                           ''', (new_status, False, verification_result['error'],
                                 datetime.now().isoformat(), contract_id))

            message = f"❌ Проверка не пройдена: {verification_result['error']}"

        conn.commit()
        conn.close()

        # Отправляем уведомления
        try:
            _send_contract_notification(contract_id, 'verification_result', {
                'status': new_status,
                'message': message
            })
        except Exception as notification_error:
            logger.error(f"Ошибка отправки уведомлений: {notification_error}")

        return {
            'success': True,
            'status': new_status,
            'message': message,
            'details': verification_result
        }

    except Exception as e:
        logger.error(f"Критическая ошибка проверки размещения для контракта {contract_id}: {e}")
        return {'success': False, 'error': f'Критическая ошибка: {str(e)}'}


# ===== ПРОВЕРКА TELEGRAM ПОСТОВ =====
def extract_post_info_from_url(post_url):
    """Извлечение информации о посте из Telegram URL"""
    try:
        import re

        if not post_url or not isinstance(post_url, str):
            return {'success': False, 'error': 'Некорректная ссылка'}

        patterns = [
            r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://telegram\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://t\.me/c/(\d+)/(\d+)',
            r't\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)\?.*'
        ]

        for pattern in patterns:
            match = re.search(pattern, post_url.strip())
            if match:
                channel_identifier = match.group(1)
                message_id = match.group(2)

                # Для приватных каналов добавляем префикс -100
                if channel_identifier.isdigit() and not channel_identifier.startswith('-100'):
                    channel_identifier = f'-100{channel_identifier}'

                return {
                    'success': True,
                    'channel_username': channel_identifier,
                    'message_id': message_id,
                    'url_type': 'private' if channel_identifier.isdigit() else 'public',
                    'original_url': post_url
                }

        return {
            'success': False,
            'error': 'Неверный формат URL. Ожидаемые форматы: https://t.me/channel/123'
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга URL {post_url}: {e}")
        return {'success': False, 'error': f'Ошибка парсинга URL: {str(e)}'}


def check_telegram_post(channel_username, post_id, expected_content=""):
    """Проверка поста через Telegram API с приоритетом веб-проверки"""
    try:
        # Получаем BOT_TOKEN
        try:
            from working_app import AppConfig
            bot_token = AppConfig.BOT_TOKEN
        except:
            bot_token = None

        if not bot_token:
            return {'success': False, 'error': 'BOT_TOKEN не настроен'}

        # Нормализуем username канала
        if not channel_username.startswith('@'):
            channel_username = f'@{channel_username}'

        base_url = f"https://api.telegram.org/bot{bot_token}"

        # ПРИОРИТЕТ 1: Веб-проверка
        try:
            clean_username = channel_username.lstrip('@')
            public_post_url = f"https://t.me/{clean_username}/{post_id}"

            post_response = requests.get(public_post_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if post_response.status_code == 200:
                content = post_response.text.lower()
                error_indicators = ['post not found', 'not found', 'channel is private', 'пост не найден']

                if not any(indicator in content for indicator in error_indicators):
                    content_match_percentage = 100

                    if expected_content:
                        expected_words = expected_content.lower().split()
                        keywords = [word for word in expected_words if len(word) > 3][:3]

                        if keywords:
                            found_keywords = sum(1 for keyword in keywords if keyword in content)
                            content_match_percentage = (found_keywords / len(keywords)) * 100

                            if content_match_percentage < 33:
                                content_match_percentage = 50

                    return {
                        'success': True,
                        'details': {
                            'post_found': True,
                            'method': 'web_scraping',
                            'url': public_post_url,
                            'verified_at': datetime.now().isoformat(),
                            'content_match': content_match_percentage
                        }
                    }

        except Exception as web_error:
            logger.debug(f"Веб-проверка не сработала: {web_error}")

        # ПРИОРИТЕТ 2: Telegram API проверки
        try:
            # Проверка доступа к каналу
            chat_response = requests.get(f"{base_url}/getChat", params={
                'chat_id': channel_username
            }, timeout=10)

            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                if chat_data.get('ok'):
                    # Попытка получить сообщение через forwardMessage
                    message_response = requests.get(f"{base_url}/forwardMessage", params={
                        'chat_id': channel_username,
                        'from_chat_id': channel_username,
                        'message_id': post_id,
                        'disable_notification': True
                    }, timeout=10)

                    if message_response.status_code == 200:
                        msg_data = message_response.json()
                        if msg_data.get('ok'):
                            return {
                                'success': True,
                                'details': {
                                    'post_found': True,
                                    'method': 'forward_message',
                                    'verified_at': datetime.now().isoformat(),
                                    'content_match': 100
                                }
                            }

        except Exception as api_error:
            logger.debug(f"API проверка не сработала: {api_error}")

        # Если все методы не сработали
        return {
            'success': False,
            'error': 'Не удалось подтвердить существование поста. Возможно, пост был удален.'
        }

    except Exception as e:
        logger.error(f"Критическая ошибка проверки Telegram поста: {e}")
        return {'success': False, 'error': f'Ошибка проверки: {str(e)}'}


# ===== УДАЛЕНИЕ КОНТРАКТОВ =====
def delete_finished_contract(contract_id, telegram_user_id):
    """Удаление завершенного контракта"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_pub.telegram_id as publisher_telegram_id
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        contract = cursor.fetchone()
        if not contract:
            conn.close()
            return {'success': False, 'error': 'Контракт не найден'}

        # Проверяем права доступа
        if (contract['advertiser_telegram_id'] != telegram_user_id and
                contract['publisher_telegram_id'] != telegram_user_id):
            conn.close()
            return {'success': False, 'error': 'Нет доступа к этому контракту'}

        # Проверяем статус
        deletable_statuses = ['verification_failed', 'cancelled']
        if contract['status'] not in deletable_statuses:
            conn.close()
            return {
                'success': False,
                'error': f'Можно удалять только контракты со статусами: {", ".join(deletable_statuses)}'
            }

        # Удаляем связанные записи и контракт
        cursor.execute('DELETE FROM monitoring_tasks WHERE contract_id = ?', (contract_id,))
        cursor.execute('DELETE FROM payments WHERE contract_id = ?', (contract_id,))
        cursor.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))

        conn.commit()
        conn.close()

        return {
            'success': True,
            'message': f'Контракт "{contract["offer_title"]}" удален'
        }

    except Exception as e:
        logger.error(f"Ошибка удаления контракта: {e}")
        return {'success': False, 'error': str(e)}


# ===== УВЕДОМЛЕНИЯ =====
def _send_telegram_message(chat_id, text, keyboard=None):
    """Отправка сообщения в Telegram"""
    try:
        from working_app import AppConfig
        bot_token = AppConfig.BOT_TOKEN

        if not bot_token:
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        if keyboard:
            payload['reply_markup'] = keyboard

        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200

    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False


def _send_contract_notification(contract_id, notification_type, extra_data=None):
    """Отправка уведомлений по контрактам"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_adv.first_name  as advertiser_name,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_pub.first_name  as publisher_name,
                              or_resp.channel_title
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        # Формируем сообщения в зависимости от типа уведомления
        notification_messages = {
            'created': {
                'advertiser': f"""📋 <b>Контракт создан!</b>
🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Сумма:</b> {data['price']} RUB
📺 <b>Канал:</b> {data['channel_title']}""",
                'publisher': f"""✅ <b>Ваш отклик принят! Контракт создан.</b>
🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data['price']} RUB"""
            },
            'verification_result': {
                'common': extra_data.get('message') if extra_data else 'Результат проверки размещения'
            }
        }

        messages = notification_messages.get(notification_type, {})

        if 'advertiser' in messages:
            _send_telegram_message(data['advertiser_telegram_id'], messages['advertiser'])
        if 'publisher' in messages:
            _send_telegram_message(data['publisher_telegram_id'], messages['publisher'])
        if 'common' in messages:
            _send_telegram_message(data['advertiser_telegram_id'], messages['common'])
            _send_telegram_message(data['publisher_telegram_id'], messages['common'])

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления по контракту: {e}")


def _send_response_notification(response_id, status):
    """Уведомление об изменении статуса отклика"""
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT o.title             as offer_title,
                              u_owner.telegram_id as channel_owner_telegram_id,
                              or_resp.admin_message,
                              or_resp.channel_title
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                                JOIN users u_owner ON or_resp.user_id = u_owner.id
                       WHERE or_resp.id = ?
                       ''', (response_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        if status == 'accepted':
            message = f"""✅ <b>Ваш отклик принят!</b>
📋 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
📋 Контракт создан автоматически. Проверьте детали в приложении."""

        elif status == 'rejected':
            reason_text = f"\n💬 <b>Причина:</b> {data['admin_message']}" if data['admin_message'] else ""
            message = f"""❌ <b>Отклик отклонён</b>
📋 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}{reason_text}
💪 Не расстраивайтесь! Ищите другие подходящие офферы."""

        _send_telegram_message(data['channel_owner_telegram_id'], message)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления об отклике: {e}")


def _notify_channels_about_cancellation(offer_id: int, offer_title: str):
    """Уведомление владельцев каналов об отмене оффера"""
    try:
        responses = DatabaseManager.execute_query('''
                                                  SELECT DISTINCT u.telegram_id, or_resp.channel_title
                                                  FROM offer_responses or_resp
                                                           JOIN users u ON or_resp.user_id = u.id
                                                  WHERE or_resp.offer_id = ?
                                                    AND or_resp.status IN ('pending', 'accepted')
                                                  ''', (offer_id,), fetch_all=True)

        for response in responses:
            message = f"""📢 <b>Оффер отменен</b>
🎯 <b>Оффер:</b> {offer_title}
📺 <b>Ваш канал:</b> {response['channel_title']}
😔 К сожалению, рекламодатель отменил данный оффер."""

            _send_telegram_message(response['telegram_id'], message)

    except Exception as e:
        logger.error(f"Ошибка уведомления об отмене оффера {offer_id}: {e}")


def _notify_channels_about_completion(offer_id: int, offer_title: str):
    """Уведомление о завершении оффера"""
    logger.info(f"Уведомляем о завершении оффера {offer_id}: {offer_title}")


# ===== ТЕСТОВЫЕ ФУНКЦИИ =====
def quick_test_verification():
    """Быстрый тест проверки размещения"""
    print("🚀 БЫСТРЫЙ ТЕСТ ПРОВЕРКИ РАЗМЕЩЕНИЯ")
    print("=" * 50)

    test_url = "https://t.me/vjissda/25"

    print("1️⃣ Тест извлечения данных из URL...")
    try:
        post_info = extract_post_info_from_url(test_url)
        print(f"✅ extract_post_info_from_url: {post_info}")
    except Exception as e:
        print(f"❌ Ошибка extract_post_info_from_url: {e}")
        return

    print("\n2️⃣ Тест проверки поста...")
    if post_info['success']:
        try:
            verification = check_telegram_post(
                post_info['channel_username'],
                post_info['message_id'],
                "тестовое описание"
            )
            print(f"✅ check_telegram_post: {verification}")
        except Exception as e:
            print(f"❌ Ошибка check_telegram_post: {e}")

    print("\n🏁 ТЕСТ ЗАВЕРШЕН")


# ===== ЭКСПОРТ ФУНКЦИЙ =====
__all__ = [
    'add_offer', 'get_user_offers', 'get_available_offers',
    'update_offer_status_by_id', 'delete_offer_by_id',
    'update_response_status', 'submit_placement', 'verify_placement',
    'delete_finished_contract', 'quick_test_verification'
]

if __name__ == '__main__':
    print("🧪 Тестирование модуля add_offer")

    test_data = {
        'title': 'Тестовый оффер - оптимизированная версия',
        'description': 'Описание тестового оффера из оптимизированного модуля',
        'content': 'Полное содержание тестового оффера',
        'price': 1500,
        'currency': 'RUB',
        'category': 'tech'
    }

    result = add_offer(373086959, test_data)
    print(f"Результат создания: {result}")

    if result['success']:
        offers = get_user_offers(373086959)
        print(f"Найдено офферов: {len(offers)}")