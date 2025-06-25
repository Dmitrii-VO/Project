# add_offer_fixed.py - Исправленная система создания офферов
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

    if not data.get('description', '').strip() and not data.get('content', '').strip():
        errors.append('Описание оффера обязательно')

    if not data.get('price') or float(data.get('price', 0)) <= 0:
        errors.append('Цена должна быть больше 0')

    # Проверка длины полей
    title = data.get('title', '').strip()
    if len(title) < 5 or len(title) > 200:
        errors.append('Название должно быть от 5 до 200 символов')

    # Проверка цены
    try:
        price = float(data.get('price', 0))
        if price < 10 or price > 1000000:
            errors.append('Цена должна быть от 10 до 1,000,000 рублей')
    except (ValueError, TypeError):
        errors.append('Некорректная цена')

    # Проверка валюты
    currency = data.get('currency', 'RUB').upper()
    allowed_currencies = ['RUB', 'USD', 'EUR']
    if currency not in allowed_currencies:
        errors.append(f'Валюта должна быть одной из: {", ".join(allowed_currencies)}')

    # Проверка категории
    category = data.get('category', 'general')
    allowed_categories = [
        'general', 'tech', 'finance', 'lifestyle', 'education',
        'entertainment', 'business', 'health', 'sports', 'travel', 'other'
    ]
    if category not in allowed_categories:
        errors.append(f'Категория должна быть одной из: {", ".join(allowed_categories)}')

    return errors


def ensure_user_exists(user_id: int, username: str = None, first_name: str = None) -> int:
    """Убеждаемся что пользователь существует в БД"""
    user = safe_execute_query(
        'SELECT id FROM users WHERE telegram_id = ?',
        (user_id,),
        fetch_one=True
    )

    if not user:
        # Создаем нового пользователя
        user_db_id = safe_execute_query('''
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
        logger.info(f"Создание оффера пользователем {user_id}: {offer_data}")

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
        description = offer_data.get('description', '').strip()
        content = offer_data.get('content', '').strip()

        # Если нет description, создаем из content
        if not description and content:
            description = content[:200] + "..." if len(content) > 200 else content
        elif not description:
            description = title  # Fallback к title

        price = float(offer_data['price'])
        currency = offer_data.get('currency', 'RUB').upper()
        category = offer_data.get('category', 'general')

        # Дополнительные параметры
        target_audience = offer_data.get('target_audience', '').strip()
        requirements = offer_data.get('requirements', '').strip()
        duration_days = int(offer_data.get('duration_days', 30))

        # Метаданные оффера
        metadata = {
            'contact_info': offer_data.get('contact_info', ''),
            'preferred_channels': offer_data.get('preferred_channels', []),
            'blacklist_channels': offer_data.get('blacklist_channels', []),
            'geo_targeting': offer_data.get('geo_targeting', []),
            'age_targeting': offer_data.get('age_targeting', ''),
            'posting_time': offer_data.get('posting_time', ''),
            'additional_requirements': offer_data.get('additional_requirements', ''),
            'created_via': 'web_interface',
            'category': category
        }

        # Расчет дат
        current_time = datetime.now()
        deadline_date = (current_time + timedelta(days=duration_days)).date()
        expires_at = current_time + timedelta(days=duration_days)

        # Параметры подписчиков
        min_subscribers = int(offer_data.get('min_subscribers', 1))
        max_subscribers = int(offer_data.get('max_subscribers', 100000000))
        budget_total = float(offer_data.get('budget_total', price))

        # Вставка оффера в базу данных
        offer_id = safe_execute_query('''
                                      INSERT INTO offers (created_by, title, description, content, price, currency,
                                                          target_audience, requirements, deadline, status, category,
                                                          metadata, budget_total, expires_at, duration_days,
                                                          min_subscribers, max_subscribers)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                          'active',
                                          category,
                                          json.dumps(metadata, ensure_ascii=False),
                                          budget_total,
                                          expires_at.isoformat(),
                                          duration_days,
                                          min_subscribers,
                                          max_subscribers
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
            'deadline': deadline_date.strftime('%d.%m.%Y'),
            'expires_at': expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        import traceback
        traceback.print_exc()
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
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        user_db_id = user['id']

        # Формируем запрос
        if status:
            query = '''
                    SELECT o.*,
                           COUNT(DISTINCT or_resp.id)                                                as response_count,
                           COUNT(DISTINCT CASE WHEN or_resp.status = 'accepted' THEN or_resp.id END) as accepted_count
                    FROM offers o
                             LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                    WHERE o.created_by = ? \
                      AND o.status = ?
                    GROUP BY o.id
                    ORDER BY o.created_at DESC \
                    '''
            params = (user_db_id, status)
        else:
            query = '''
                    SELECT o.*,
                           COUNT(DISTINCT or_resp.id)                                                as response_count,
                           COUNT(DISTINCT CASE WHEN or_resp.status = 'accepted' THEN or_resp.id END) as accepted_count
                    FROM offers o
                             LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                    WHERE o.created_by = ?
                    GROUP BY o.id
                    ORDER BY o.created_at DESC \
                    '''
            params = (user_db_id,)

        offers = safe_execute_query(query, params, fetch_all=True)

        # Форматируем данные для фронтенда
        formatted_offers = []
        for offer in offers:
            # Парсим метаданные
            try:
                metadata = json.loads(offer.get('metadata', '{}'))
            except:
                metadata = {}

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

        logger.info(f"Получено {len(formatted_offers)} офферов для пользователя {user_id}")
        return formatted_offers

    except Exception as e:
        logger.error(f"Ошибка получения офферов пользователя {user_id}: {e}")
        return []


def get_offer_by_id(offer_id: int, include_responses: bool = False) -> Optional[Dict[str, Any]]:
    """Получение оффера по ID"""
    try:
        offer = safe_execute_query('''
                                   SELECT o.*, u.username as creator_username, u.first_name as creator_name
                                   FROM offers o
                                            JOIN users u ON o.created_by = u.id
                                   WHERE o.id = ?
                                   ''', (offer_id,), fetch_one=True)

        if not offer:
            return None

        # Парсим метаданные
        try:
            metadata = json.loads(offer.get('metadata', '{}'))
        except:
            metadata = {}

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
            'creator_username': offer.get('creator_username', ''),
            'creator_name': offer.get('creator_name', ''),
            'budget_total': float(offer.get('budget_total', 0)),
            'duration_days': offer.get('duration_days', 30),
            'min_subscribers': offer.get('min_subscribers', 1),
            'max_subscribers': offer.get('max_subscribers', 100000000),
            'metadata': metadata
        }

        # Добавляем отклики если требуется
        if include_responses:
            responses = safe_execute_query('''
                                           SELECT or_resp.*,
                                                  c.title    as channel_title,
                                                  c.username as channel_username,
                                                  c.subscriber_count,
                                                  u.username as responder_username
                                           FROM offer_responses or_resp
                                                    JOIN channels c ON or_resp.channel_id = c.id
                                                    JOIN users u ON c.owner_id = u.id
                                           WHERE or_resp.offer_id = ?
                                           ORDER BY or_resp.created_at DESC
                                           ''', (offer_id,), fetch_all=True)

            formatted_offer['responses'] = responses or []

        return formatted_offer

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return None


def get_available_offers(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Получение доступных офферов для владельцев каналов"""
    try:
        filters = filters or {}

        # Базовый запрос для активных офферов
        query = '''
                SELECT o.*, \
                       u.username                 as creator_username, \
                       u.first_name               as creator_name,
                       COUNT(DISTINCT or_resp.id) as response_count
                FROM offers o
                         JOIN users u ON o.created_by = u.id
                         LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                WHERE o.status = 'active' \
                '''
        params = []

        # Добавляем фильтры
        if filters.get('category'):
            query += ' AND o.category = ?'
            params.append(filters['category'])

        if filters.get('min_budget'):
            query += ' AND o.price >= ?'
            params.append(float(filters['min_budget']))

        if filters.get('max_budget'):
            query += ' AND o.price <= ?'
            params.append(float(filters['max_budget']))

        # Группировка и сортировка
        query += '''
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT ?
        '''
        limit = int(filters.get('limit', 50))
        params.append(limit)

        offers = safe_execute_query(query, tuple(params), fetch_all=True)

        # Форматируем для фронтенда
        formatted_offers = []
        for offer in offers:
            try:
                metadata = json.loads(offer.get('metadata', '{}'))
            except:
                metadata = {}

            formatted_offer = {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'price': float(offer['price']),
                'currency': offer['currency'],
                'category': offer['category'],
                'target_audience': offer.get('target_audience', ''),
                'requirements': offer.get('requirements', ''),
                'deadline': offer.get('deadline', ''),
                'created_at': offer['created_at'],
                'creator_username': offer.get('creator_username', ''),
                'creator_name': offer.get('creator_name', ''),
                'response_count': offer.get('response_count', 0),
                'min_subscribers': offer.get('min_subscribers', 1),
                'max_subscribers': offer.get('max_subscribers', 100000000),
                'metadata': metadata
            }
            formatted_offers.append(formatted_offer)

        return formatted_offers

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return []


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
            logger.error(f"Ошибка получения оффера: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500

    @app.route('/api/offers/available', methods=['GET'])
    def api_get_available_offers():
        """API для получения доступных офферов"""
        try:
            filters = {
                'category': request.args.get('category'),
                'min_budget': request.args.get('min_budget', type=float),
                'max_budget': request.args.get('max_budget', type=float),
                'limit': request.args.get('limit', 50, type=int)
            }

            # Убираем None значения
            filters = {k: v for k, v in filters.items() if v is not None}

            offers = get_available_offers(filters)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})

        except Exception as e:
            logger.error(f"Ошибка получения доступных офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500

    print("✅ Маршруты офферов зарегистрированы")


# Экспорт функций для использования в других модулях
__all__ = [
    'add_offer', 'get_user_offers', 'get_offer_by_id',
    'get_available_offers', 'register_offer_routes'
]

if __name__ == '__main__':
    # Тестирование функций
    print("🧪 Тестирование модуля add_offer")

    # Тест создания оффера
    test_data = {
        'title': 'Тестовый оффер из модуля',
        'description': 'Описание тестового оффера',
        'content': 'Полное содержание тестового оффера',
        'price': 1500,
        'currency': 'RUB',
        'category': 'tech',
        'target_audience': 'IT специалисты',
        'requirements': 'Размещение в течение недели',
        'duration_days': 14
    }

    result = add_offer(373086959, test_data)
    print(f"Результат создания: {result}")

    if result['success']:
        # Тест получения офферов
        offers = get_user_offers(373086959)
        print(f"Найдено офферов: {len(offers)}")

        # Тест получения по ID
        if offers:
            offer_detail = get_offer_by_id(offers[0]['id'], True)
            print(f"Детали оффера: {offer_detail is not None}")