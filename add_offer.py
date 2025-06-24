# add_offer.py - Система создания офферов (продуктивная версия)
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

try:
    from flask import request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # Заглушки для случая, когда Flask недоступен
    request = None
    jsonify = None

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к базе данных
DATABASE_PATH = 'telegram_mini_app.db'

def get_db_connection():
    """Получение подключения к SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к SQLite: {e}")

def safe_execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Безопасное выполнение SQL запросов"""
    try:
        conn = get_db_connection()
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

def validate_offer_data(data: Dict[str, Any]) -> List[str]:
    """Валидация данных оффера"""
    errors = []

    # Проверка обязательных полей
    if not data.get('title', '').strip():
        errors.append('Название оффера обязательно')

    if not data.get('content', '').strip():
        errors.append('Описание оффера обязательно')

    if not data.get('price') or float(data.get('price', 0)) <= 0:
        errors.append('Цена должна быть больше 0')

    # Проверка длины полей
    title = data.get('title', '').strip()
    if len(title) < 10 or len(title) > 200:
        errors.append('Название должно быть от 10 до 200 символов')

    content = data.get('content', '').strip()
    if len(content) < 50 or len(content) > 2000:
        errors.append('Описание должно быть от 50 до 2000 символов')

    # Проверка цены
    try:
        price = float(data.get('price', 0))
        if price < 100 or price > 1000000:
            errors.append('Цена должна быть от 100 до 1,000,000')
    except (ValueError, TypeError):
        errors.append('Некорректная цена')

    # Проверка валюты
    currency = data.get('currency', '').upper()
    if currency not in ['RUB', 'USD', 'EUR']:
        errors.append('Валюта должна быть RUB, USD или EUR')

    # Проверка категории
    category = data.get('category', '').strip()
    allowed_categories = [
        'marketing', 'tech', 'education', 'entertainment',
        'business', 'crypto', 'gaming', 'lifestyle', 'other'
    ]
    if category not in allowed_categories:
        errors.append('Некорректная категория')

    return errors

def ensure_user_exists(user_id: int, username: str = None, first_name: str = None) -> int:
    """Обеспечение существования пользователя в базе"""
    user = safe_execute_query(
        'SELECT id FROM users WHERE telegram_id = ?',
        (user_id,),
        fetch_one=True
    )

    if not user:
        # Создаем нового пользователя
        user_db_id = safe_execute_query('''
            INSERT INTO users (telegram_id, username, first_name, is_admin, created_at) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            username or f'user_{user_id}',
            first_name or 'User',
            False,
            datetime.now().isoformat()
        ))

        logger.info(f"Создан новый пользователь: {user_id}")
        return user_db_id

    return user['id']

def add_offer(user_id: int, offer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Основная функция добавления оффера

    Args:
        user_id: Telegram ID пользователя
        offer_data: Данные оффера

    Returns:
        Dict с результатом операции
    """
    try:
        # Валидация данных
        errors = validate_offer_data(offer_data)
        if errors:
            return {
                'success': False,
                'errors': errors
            }

        # Убеждаемся что пользователь существует
        user_db_id = ensure_user_exists(
            user_id,
            offer_data.get('username'),
            offer_data.get('first_name')
        )

        # Подготовка данных для вставки
        title = offer_data['title'].strip()
        content = offer_data['content'].strip()
        price = float(offer_data['price'])
        currency = offer_data['currency'].upper()
        category = offer_data['category'].strip()

        # Дополнительные параметры
        target_audience = offer_data.get('target_audience', '').strip()
        requirements = offer_data.get('requirements', '').strip()
        duration_days = int(offer_data.get('duration_days', 30))

        # Метаданные оффера
        metadata = {
            'contact_info': offer_data.get('contact_info', ''),
            'preferred_channels': offer_data.get('preferred_channels', []),
            'blacklist_channels': offer_data.get('blacklist_channels', []),
            'min_subscribers': offer_data.get('min_subscribers', 1),
            'max_subscribers': offer_data.get('max_subscribers', 100000000),
            'geo_targeting': offer_data.get('geo_targeting', []),
            'age_targeting': offer_data.get('age_targeting', ''),
            'posting_time': offer_data.get('posting_time', ''),
            'additional_requirements': offer_data.get('additional_requirements', '')
        }

        # Правильный расчет даты истечения
        current_time = datetime.now()
        expires_at = current_time + timedelta(days=duration_days)

        # Вставка оффера в базу данных
        metadata['category'] = category

        # Создаем description из первых 200 символов content
        description = content[:200] + "..." if len(content) > 200 else content

        # Рассчитываем deadline вместо expires_at
        deadline_date = (current_time + timedelta(days=duration_days)).date()

        offer_id = safe_execute_query('''
            INSERT INTO offers (
                created_by, title, description, content, price, currency,
                target_audience, requirements, deadline, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_db_id,
            title,
            description,
            content,
            price,
            currency,
            target_audience,
            requirements,
            deadline_date.isoformat(),
            'active'
        ))

        logger.info(f"Создан новый оффер {offer_id} пользователем {user_id}")

        # Получаем созданный оффер для возврата
        created_offer = safe_execute_query('''
            SELECT o.*, u.username, u.first_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        ''', (offer_id,), fetch_one=True)

        return {
            'success': True,
            'offer_id': offer_id,
            'offer': created_offer,
            'message': 'Оффер успешно создан',
            'deadline': deadline_date.strftime('%d.%m.%Y')
        }

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return {
            'success': False,
            'error': f'Ошибка создания оффера: {str(e)}'
        }

def get_user_offers(user_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Получение офферов пользователя"""
    try:
        # Получаем user_db_id
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )

        if not user:
            return []

        user_db_id = user['id']

        # Формируем запрос
        if status:
            query = '''
                SELECT o.*, 
                       COUNT(DISTINCT or_resp.id) as response_count,
                       COUNT(DISTINCT CASE WHEN or_resp.status = 'accepted' THEN or_resp.id END) as accepted_count
                FROM offers o
                LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                WHERE o.created_by = ? AND o.status = ?
                GROUP BY o.id
                ORDER BY o.created_at DESC
            '''
            params = (user_db_id, status)
        else:
            query = '''
                SELECT o.*, 
                       COUNT(DISTINCT or_resp.id) as response_count,
                       COUNT(DISTINCT CASE WHEN or_resp.status = 'accepted' THEN or_resp.id END) as accepted_count
                FROM offers o
                LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                WHERE o.created_by = ?
                GROUP BY o.id
                ORDER BY o.created_at DESC
            '''
            params = (user_db_id,)

        offers = safe_execute_query(query, params, fetch_all=True)

        # Обогащаем данными
        for offer in offers:
            if offer.get('metadata'):
                try:
                    offer['metadata'] = json.loads(offer['metadata'])
                    # Извлекаем category из metadata для совместимости
                    if 'category' in offer['metadata']:
                        offer['category'] = offer['metadata']['category']
                    else:
                        offer['category'] = 'other'
                except:
                    offer['metadata'] = {}
                    offer['category'] = 'other'
            else:
                offer['category'] = 'other'

            # Добавляем форматированные даты
            if offer.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(offer['created_at'])
                    offer['created_at_formatted'] = created_at.strftime('%d.%m.%Y %H:%M')
                except:
                    offer['created_at_formatted'] = 'Неизвестно'

            if offer.get('deadline'):
                try:
                    deadline_date = datetime.fromisoformat(offer['deadline']).date()
                    offer['deadline_formatted'] = deadline_date.strftime('%d.%m.%Y')
                    offer['is_expired'] = deadline_date < datetime.now().date()

                    if not offer['is_expired']:
                        days_left = (deadline_date - datetime.now().date()).days
                        offer['days_left'] = max(0, days_left)
                    else:
                        offer['days_left'] = 0
                except:
                    offer['deadline_formatted'] = 'Неизвестно'
                    offer['is_expired'] = False
                    offer['days_left'] = 0

        return offers

    except Exception as e:
        logger.error(f"Ошибка получения офферов пользователя: {e}")
        return []

def update_offer_status(offer_id: int, status: str, user_id: int = None) -> bool:
    """Обновление статуса оффера"""
    try:
        allowed_statuses = ['active', 'paused', 'completed', 'cancelled']
        if status not in allowed_statuses:
            return False

        if user_id:
            # Проверяем права на изменение
            user = safe_execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (user_id,),
                fetch_one=True
            )

            if not user:
                return False

            # Проверяем принадлежность оффера
            query = '''
                UPDATE offers 
                SET status = ?, updated_at = ?
                WHERE id = ? AND created_by = ?
            '''
            params = (status, datetime.now().isoformat(), offer_id, user['id'])
        else:
            query = '''
                UPDATE offers 
                SET status = ?, updated_at = ?
                WHERE id = ?
            '''
            params = (status, datetime.now().isoformat(), offer_id)

        safe_execute_query(query, params)
        logger.info(f"Статус оффера {offer_id} изменен на {status}")
        return True

    except Exception as e:
        logger.error(f"Ошибка обновления статуса оффера: {e}")
        return False

def get_offer_by_id(offer_id: int, include_responses: bool = False) -> Optional[Dict[str, Any]]:
    """Получение оффера по ID"""
    try:
        # Основные данные оффера
        offer = safe_execute_query('''
            SELECT o.*, u.username, u.first_name, u.telegram_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        ''', (offer_id,), fetch_one=True)

        if not offer:
            return None

        # Парсим метаданные
        if offer.get('metadata'):
            try:
                offer['metadata'] = json.loads(offer['metadata'])
                # Извлекаем category из metadata
                if 'category' in offer['metadata']:
                    offer['category'] = offer['metadata']['category']
                else:
                    offer['category'] = 'other'
            except:
                offer['metadata'] = {}
                offer['category'] = 'other'
        else:
            offer['category'] = 'other'

        # Форматируем даты
        if offer.get('created_at'):
            try:
                created_at = datetime.fromisoformat(offer['created_at'])
                offer['created_at_formatted'] = created_at.strftime('%d.%m.%Y %H:%M')
            except:
                offer['created_at_formatted'] = 'Неизвестно'

        if offer.get('deadline'):
            try:
                deadline_date = datetime.fromisoformat(offer['deadline']).date()
                offer['deadline_formatted'] = deadline_date.strftime('%d.%m.%Y')
                offer['is_expired'] = deadline_date < datetime.now().date()

                if not offer['is_expired']:
                    days_left = (deadline_date - datetime.now().date()).days
                    offer['days_left'] = max(0, days_left)
                else:
                    offer['days_left'] = 0
            except:
                offer['deadline_formatted'] = 'Неизвестно'
                offer['is_expired'] = False
                offer['days_left'] = 0

        # Если нужны ответы на оффер
        if include_responses:
            responses = safe_execute_query('''
                SELECT or_resp.*, c.title as channel_title, c.username as channel_username,
                       c.subscriber_count, u.username as responder_username
                FROM offer_responses or_resp
                JOIN channels c ON or_resp.channel_id = c.id
                JOIN users u ON c.owner_id = u.id
                WHERE or_resp.offer_id = ?
                ORDER BY or_resp.created_at DESC
            ''', (offer_id,), fetch_all=True)

            offer['responses'] = responses or []

        return offer

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return None

# Flask маршруты для интеграции с основным приложением
def register_offer_routes(app):
    """Регистрация маршрутов для работы с офферами в Flask приложении"""

    if not FLASK_AVAILABLE:
        print("⚠️ Flask недоступен, маршруты офферов не зарегистрированы")
        return

    @app.route('/api/offers', methods=['POST'])
    def api_create_offer():
        """API для создания нового оффера"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400

            # Получаем user_id из заголовков или данных
            user_id = data.get('user_id') or request.headers.get('X-Telegram-User-Id')
            if not user_id:
                return jsonify({'success': False, 'error': 'User ID обязателен'}), 400

            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Некорректный User ID'}), 400

            # Создаем оффер
            result = add_offer(user_id, data)

            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Ошибка API создания оффера: {e}")
            return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

    @app.route('/api/offers/<int:user_id>', methods=['GET'])
    def api_get_user_offers(user_id):
        """API для получения офферов пользователя"""
        try:
            status = request.args.get('status')
            offers = get_user_offers(user_id, status)
            return jsonify({'success': True, 'offers': offers})
        except Exception as e:
            logger.error(f"Ошибка получения офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500

    @app.route('/api/offers/detail/<int:offer_id>', methods=['GET'])
    def api_get_offer_detail(offer_id):
        """API для получения детальной информации об оффере"""
        try:
            include_responses = request.args.get('include_responses', 'false').lower() == 'true'
            offer = get_offer_by_id(offer_id, include_responses)

            if offer:
                return jsonify({'success': True, 'offer': offer})
            else:
                return jsonify({'success': False, 'error': 'Оффер не найден'}), 404
        except Exception as e:
            logger.error(f"Ошибка получения оффера {offer_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500

    @app.route('/api/offers/<int:offer_id>/status', methods=['PUT'])
    def api_update_offer_status(offer_id):
        """API для обновления статуса оффера"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return jsonify({'success': False, 'error': 'Статус обязателен'}), 400

            user_id = data.get('user_id') or request.headers.get('X-Telegram-User-Id')
            if user_id:
                user_id = int(user_id)

            success = update_offer_status(offer_id, data['status'], user_id)

            if success:
                return jsonify({'success': True, 'message': 'Статус обновлен'})
            else:
                return jsonify({'success': False, 'error': 'Не удалось обновить статус'}), 400

        except Exception as e:
            logger.error(f"Ошибка обновления статуса оффера: {e}")
            return jsonify({'success': False, 'error': 'Ошибка обновления статуса'}), 500