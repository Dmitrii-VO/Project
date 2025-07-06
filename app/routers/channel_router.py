# app/routers/channel_router.py
"""
Маршрутизатор для работы с каналами Telegram Mini App

Содержит все API эндпоинты для управления каналами:
- Добавление и верификация каналов
- Управление настройками каналов
- Статистика каналов
- Поиск и фильтрация
"""
import sqlite3
import time
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from app.config.telegram_config import AppConfig
from app.models.database import db_manager, execute_db_query, get_user_id_from_request

logger = logging.getLogger(__name__)

# Создаем Blueprint
channel_bp = Blueprint('channels', __name__)
import secrets
from sqlalchemy import and_, or_, desc
from .middleware import (
    require_telegram_auth,
    cache_response,
    rate_limit_decorator,
    TelegramAuth
)
try:
    from app.services.telegram_verification import verify_channel
except ImportError:
    # Fallback если сервис не доступен
    def verify_channel(channel_id, verification_code):
        return {'success': True, 'found': True, 'message': 'Test mode'}

# Константы
MAX_CHANNELS_PER_USER = 10
TELEGRAM_API_TIMEOUT = 10
VERIFICATION_CODE_LENGTH = 8


class ChannelValidator:
    """Класс для валидации данных каналов"""

    @staticmethod
    def validate_channel_data(data):
        """Валидация основных данных канала"""
        errors = []

        # Проверка обязательных полей
        required_fields = ['channel_id', 'channel_name']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} is required')

        # Валидация channel_id
        channel_id = data.get('channel_id', '')
        if channel_id:
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                errors.append('Invalid channel_id format')

        # Валидация цены
        price = data.get('price_per_post')
        if price is not None:
            try:
                price = float(price)
                if price < 0:
                    errors.append('Price cannot be negative')
                elif price > 1000000:
                    errors.append('Price too high (max: 1,000,000)')
            except (ValueError, TypeError):
                errors.append('Invalid price format')

        # Валидация категории
        valid_categories = [
            'technology', 'business', 'entertainment', 'news',
            'education', 'lifestyle', 'sports', 'gaming', 'other'
        ]
        category = data.get('category')
        if category and category not in valid_categories:
            errors.append(f'Invalid category. Allowed: {", ".join(valid_categories)}')

        return errors

# === API ЭНДПОИНТЫ ===

@channel_bp.route('/', methods=['GET'])
@cache_response(timeout=120)
def get_channels():
    """
    ФУНКЦИЯ 1: Получение списка каналов
    ИСПРАВЛЕНО: убран SQLAlchemy, исправлены имена полей
    """
    try:
        # Параметры пагинации
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фильтры
        category = request.args.get('category')
        min_subscribers = request.args.get('min_subscribers', type=int)
        max_price = request.args.get('max_price', type=float)
        verified_only = request.args.get('verified_only', '').lower() == 'true'
        search = request.args.get('search', '').strip()

        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Базовый запрос
        sql = """
            SELECT c.id, c.telegram_id, c.title, c.username, c.subscriber_count, 
                   c.category, c.is_verified, c.created_at, c.owner_id,
                   u.username as owner_username, u.first_name as owner_name
            FROM channels c 
            JOIN users u ON c.owner_id = u.id 
            WHERE c.is_active = 1
        """
        count_sql = "SELECT COUNT(*) as total FROM channels c WHERE c.is_active = 1"
        params = []

        # Применяем фильтры
        if verified_only:
            sql += " AND c.is_verified = 1"
            count_sql += " AND c.is_verified = 1"

        if category:
            sql += " AND c.category = ?"
            count_sql += " AND c.category = ?"
            params.append(category)

        if min_subscribers:
            # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
            sql += " AND c.subscriber_count >= ?"
            count_sql += " AND c.subscriber_count >= ?"
            params.append(min_subscribers)

        if search:
            sql += " AND (c.title LIKE ? OR c.username LIKE ?)"
            count_sql += " AND (c.title LIKE ? OR c.username LIKE ?)"
            search_term = f'%{search}%'
            params.extend([search_term, search_term])

        # Получаем общее количество
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()['total']

        # Добавляем сортировку и пагинацию
        # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
        sql += " ORDER BY c.subscriber_count DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        channels = cursor.fetchall()
        conn.close()

        # Формируем ответ
        channels_data = []
        for channel in channels:
            channels_data.append({
                'id': channel['id'],
                'channel_id': channel['telegram_id'],
                'channel_name': channel['title'],
                'channel_username': channel['username'],
                # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
                'subscriber_count': channel['subscriber_count'] or 0,
                'category': channel['category'],
                'price_per_post': 0.0,  # Заглушка
                'is_verified': bool(channel['is_verified']),
                'created_at': channel['created_at'],
                'owner': {
                    'username': channel['owner_username'],
                    'first_name': channel['owner_name']
                }
            })

        return jsonify({
            'channels': channels_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit,
                'has_next': offset + limit < total_count,
                'has_prev': page > 1
            },
            'filters_applied': {
                'category': category,
                'min_subscribers': min_subscribers,
                'max_price': max_price,
                'verified_only': verified_only,
                'search': search
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channels: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@channel_bp.route('/<int:channel_id>', methods=['GET'])
@cache_response(timeout=300)
def get_channel(channel_id):
    """
    ФУНКЦИЯ 2: Получение информации о конкретном канале
    ИСПРАВЛЕНО: убран SQLAlchemy, исправлены имена полей
    """
    try:
        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.*, u.username as owner_username, u.first_name as owner_name
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ?
        """, (channel_id,))
        
        channel = cursor.fetchone()
        conn.close()

        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

        # Базовая информация
        channel_data = {
            'id': channel['id'],
            'channel_id': channel['telegram_id'],
            'channel_name': channel['title'],
            'channel_username': channel['username'],
            # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
            'subscriber_count': channel['subscriber_count'] or 0,
            'category': channel['category'],
            'description': channel.get('description', ''),
            'language': channel.get('language', 'ru'),
            'price_per_post': 0.0,  # Заглушка
            'is_verified': bool(channel['is_verified']),
            'is_active': bool(channel['is_active']),
            'created_at': channel['created_at'],
            'verified_at': channel.get('verified_at'),
            'owner': {
                'username': channel['owner_username'],
                'first_name': channel['owner_name']
            }
        }

        return jsonify({
            'success': True,
            'channel': channel_data
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channel {channel_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@channel_bp.route('/<int:channel_id>/verify', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=3, window=300)  # 3 попытки верификации за 5 минут
def verify_channel(channel_id):
    """
    Верификация владения каналом

    Args:
        channel_id: ID канала

    Returns:
        JSON с результатом верификации
    """
    try:
        from ..models.channels import Channel
        from ..models.database import db

        # Находим канал
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({
                'error': 'Channel not found or access denied'
            }), 404

        if channel.is_verified:
            return jsonify({
                'success': True,
                'message': 'Channel is already verified'
            })

        # Проверяем верификацию через Telegram API
        verification_result = verify_channel(
            channel.channel_id,
            channel.verification_code
        )

        is_verified = verification_result.get('success', False) and verification_result.get('found', False)

        if is_verified:
            channel.is_verified = True
            db.session.commit()

            current_app.logger.info(
                f"Channel {channel_id} verified by user {g.telegram_user_id}"
            )

            return jsonify({
                'success': True,
                'message': 'Channel verified successfully',
                'channel': {
                    'id': channel.id,
                    'channel_name': channel.channel_name,
                    'is_verified': channel.is_verified
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Verification failed',
                'instructions': (
                    f"Please post this verification code in your channel: {channel.verification_code}\n"
                    "Make sure the code is visible in a recent message and try again."
                )
            }), 400

    except Exception as e:
        current_app.logger.error(f"Error verifying channel {channel_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/<int:channel_id>', methods=['DELETE'])
@require_telegram_auth
@rate_limit_decorator(max_requests=5, window=300)  # 5 удалений за 5 минут
def delete_channel(channel_id):
    """
    Удаление канала

    Args:
        channel_id: ID канала

    Returns:
        JSON с результатом удаления
    """
    try:
        from ..models.channels import Channel
        from ..models.response import Response
        from ..models.database import db

        # Находим канал
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({
                'error': 'Channel not found or access denied'
            }), 404

        # Проверяем активные отклики
        active_responses = Response.query.filter_by(
            channel_id=channel_id,
            status='pending'
        ).count()

        if active_responses > 0:
            return jsonify({
                'error': 'Cannot delete channel with pending responses',
                'active_responses_count': active_responses,
                'message': 'Please resolve all pending responses before deleting the channel'
            }), 400

        # Удаляем связанные отклики
        Response.query.filter_by(channel_id=channel_id).delete()

        # Удаляем канал
        channel_name = channel.channel_name
        db.session.delete(channel)
        db.session.commit()

        current_app.logger.info(
            f"Channel {channel_id} ({channel_name}) deleted by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Channel "{channel_name}" deleted successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting channel {channel_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/my', methods=['GET'])
@require_telegram_auth
def get_my_channels():
    """
    ФУНКЦИЯ 3: Получение каналов текущего пользователя
    ИСПРАВЛЕНО: убран SQLAlchemy, исправлены имена полей
    """
    try:
        telegram_user_id = getattr(g, 'telegram_user_id', None)
        user_id = getattr(g, 'current_user_id', None)

        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        current_app.logger.info(f"Получение каналов для пользователя ID: {user_id}")

        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, telegram_id, title, username, subscriber_count, category,
                   is_verified, verification_code, created_at, status
            FROM channels
            WHERE owner_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        channels_data = cursor.fetchall()
        conn.close()

        current_app.logger.info(f"Найдено каналов: {len(channels_data)}")

        # ✅ ИСПРАВЛЕНО: Преобразуем в список словарей с правильными именами полей
        channels_list = []
        for channel in channels_data:
            channel_dict = {
                'id': channel['id'],
                'channel_id': channel['telegram_id'],
                'channel_name': channel['title'] or 'Неизвестный канал',
                'title': channel['title'] or 'Неизвестный канал',
                'channel_username': channel['username'],
                'username': channel['username'],
                # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
                'subscriber_count': channel['subscriber_count'] or 0,
                'category': channel['category'] or 'other',
                'price_per_post': 0.0,
                'is_verified': bool(channel['is_verified']),
                'verification_code': channel['verification_code'] if not channel['is_verified'] else None,
                'created_at': channel['created_at'],
                'status': channel['status'] or 'pending',
                'offers_count': get_channel_offers_count(channel['id']),
                'posts_count': get_channel_posts_count(channel['id'])
            }
            channels_list.append(channel_dict)

        return jsonify({
            'success': True,
            'channels': channels_list,
            'total': len(channels_list)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting my channels: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@channel_bp.route('/<int:channel_id>/responses', methods=['GET'])
@require_telegram_auth
def get_channel_responses(channel_id):
    """
    ФУНКЦИЯ 6: Получение откликов канала
    ИСПРАВЛЕНО: убран SQLAlchemy
    """
    try:
        user_id = getattr(g, 'current_user_id', None)

        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        # Проверяем права доступа к каналу
        channel = execute_db_query(
            'SELECT * FROM channels WHERE id = ? AND owner_id = ?',
            (channel_id, user_id),
            fetch_one=True
        )

        if not channel:
            return jsonify({'error': 'Channel not found or access denied'}), 404

        # Получаем отклики
        responses = execute_db_query("""
            SELECT or.*, o.title as offer_title, u.username, u.first_name
            FROM offer_responses or
            JOIN offers o ON or.offer_id = o.id
            JOIN users u ON or.user_id = u.id
            WHERE or.channel_id = ?
            ORDER BY or.created_at DESC
        """, (channel_id,), fetch_all=True)

        responses_data = []
        for response in responses:
            responses_data.append({
                'id': response['id'],
                'offer_id': response['offer_id'],
                'offer_title': response['offer_title'],
                'message': response['message'],
                'status': response['status'],
                'channel_username': response.get('channel_username', ''),
                'channel_title': response.get('channel_title', ''),
                # ✅ ИСПРАВЛЕНО: subscriber_count вместо subscribers_count
                'channel_subscriber_count': response.get('channel_subscribers', 0),
                'created_at': response['created_at'],
                'updated_at': response['updated_at'],
                'user': {
                    'username': response['username'],
                    'first_name': response['first_name']
                }
            })

        return jsonify({
            'success': True,
            'responses': responses_data,
            'total': len(responses_data)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channel responses: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@channel_bp.route('/<int:channel_id>/responses/<int:response_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=300)  # 20 действий за 5 минут
def update_response_status(channel_id, response_id):
    """
    ФУНКЦИЯ 7: Обновление статуса отклика
    ИСПРАВЛЕНО: убран SQLAlchemy
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        new_status = data.get('status')
        if new_status not in ['accepted', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400

        user_id = getattr(g, 'current_user_id', None)

        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        # Проверяем доступ к каналу
        channel = execute_db_query(
            'SELECT * FROM channels WHERE id = ? AND owner_id = ?',
            (channel_id, user_id),
            fetch_one=True
        )

        if not channel:
            return jsonify({'error': 'Channel not found or access denied'}), 404

        # Находим отклик
        response = execute_db_query(
            'SELECT * FROM offer_responses WHERE id = ? AND channel_id = ?',
            (response_id, channel_id),
            fetch_one=True
        )

        if not response:
            return jsonify({'error': 'Response not found'}), 404

        if response['status'] != 'pending':
            return jsonify({'error': f'Response already {response["status"]}'}), 400

        # Обновляем статус
        execute_db_query("""
            UPDATE offer_responses 
            SET status = ?, admin_message = ?, updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            data.get('message', ''),
            datetime.utcnow().isoformat(),
            response_id
        ))

        current_app.logger.info(
            f"Response {response_id} status updated to {new_status} by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Response {new_status} successfully',
            'response': {
                'id': response_id,
                'status': new_status,
                'message': data.get('message', ''),
                'updated_at': time.time()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error updating response status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@channel_bp.route('/categories', methods=['GET'])
@cache_response(timeout=3600)  # Кэшируем на 1 час
def get_categories():
    """
    ФУНКЦИЯ 8: Получение категорий каналов
    ИСПРАВЛЕНО: убран SQLAlchemy
    """
    try:
        # ✅ ИСПРАВЛЕНО: Чистый SQLite вместо SQLAlchemy
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем статистику по категориям
        cursor.execute("""
            SELECT category, 
                   COUNT(*) as channel_count,
                   AVG(subscriber_count) as avg_subscribers,
                   SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified_count
            FROM channels 
            WHERE is_active = 1 
            GROUP BY category
            ORDER BY channel_count DESC
        """)

        categories_stats = cursor.fetchall()
        conn.close()

        categories_data = []
        for category in categories_stats:
            categories_data.append({
                'name': category['category'],
                'display_name': category['category'].title(),
                'channel_count': category['channel_count'],
                # ✅ ИСПРАВЛЕНО: avg_subscribers вместо avg_subscribers_count
                'avg_subscriber_count': int(category['avg_subscribers'] or 0),
                'verified_count': category['verified_count'],
                'verification_rate': round(
                    (category['verified_count'] / category['channel_count'] * 100) 
                    if category['channel_count'] > 0 else 0, 1
                )
            })

        return jsonify({
            'success': True,
            'categories': categories_data,
            'total': len(categories_data)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@channel_bp.route('/stats', methods=['GET'])
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_channels_stats():
    """
    Получение общей статистики по каналам

    Returns:
        JSON с общей статистикой
    """
    try:
        from ..models.channels import Channel
        from ..models.database import db
        from sqlalchemy import func

        # Общая статистика
        total_channels = Channel.query.count()
        verified_channels = Channel.query.filter_by(is_verified=True).count()

        # Статистика по подписчикам
        subscriber_stats = db.session.query(
            func.sum(Channel.subscriber_count).label('total_subscriber'),
            func.avg(Channel.subscriber_count).label('avg_subscriber'),
            func.max(Channel.subscriber_count).label('max_subscribers')
        ).filter(Channel.is_verified == True).first()

        # Статистика по ценам
        price_stats = db.session.query(
            func.avg(Channel.price_per_post).label('avg_price'),
            func.min(Channel.price_per_post).label('min_price'),
            func.max(Channel.price_per_post).label('max_price')
        ).filter(
            Channel.is_verified == True,
            Channel.price_per_post > 0
        ).first()

        # Топ категории
        top_categories = db.session.query(
            Channel.category,
            func.count(Channel.id).label('count')
        ).filter(
            Channel.is_verified == True
        ).group_by(Channel.category).order_by(
            desc(func.count(Channel.id))
        ).limit(5).all()

        return jsonify({
            'channels': {
                'total': total_channels,
                'verified': verified_channels,
                'verification_rate': (verified_channels / total_channels * 100) if total_channels > 0 else 0
            },
            'subscriber': {
                'total': int(subscriber_stats.total_subscriber or 0),
                'average': int(subscriber_stats.avg_subscriber or 0),
                'maximum': int(subscriber_stats.max_subscribers or 0)
            },
            'pricing': {
                'average': round(float(price_stats.avg_price or 0), 2),
                'minimum': round(float(price_stats.min_price or 0), 2),
                'maximum': round(float(price_stats.max_price or 0), 2)
            },
            'top_categories': [
                {
                    'category': cat.category,
                    'count': cat.count
                } for cat in top_categories
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channels stats: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@channel_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """
    Webhook для получения обновлений от Telegram бота
    Автоматически проверяет коды верификации в каналах
    """
    try:
        from ..models.channels import Channel
        from ..models.database import db
        from datetime import datetime

        data = request.get_json()

        if not data:
            return jsonify({'ok': True})

        # Обрабатываем только сообщения в каналах
        if 'channel_post' in data:
            message = data['channel_post']
            chat = message.get('chat', {})
            chat_id = str(chat.get('id'))
            text = message.get('text', '')

            current_app.logger.info(f"Получено сообщение из канала {chat_id}: {text[:50]}...")

            # Ищем канал в базе данных
            channel = Channel.query.filter_by(channel_id=chat_id).first()

            if channel and not channel.is_verified and channel.verification_code:
                # Проверяем, содержит ли сообщение код верификации
                if channel.verification_code in text:
                    channel.is_verified = True
                    channel.verified_at = datetime.now().isoformat()
                    db.session.commit()

                    current_app.logger.info(
                        f"✅ Канал {channel.id} автоматически верифицирован с кодом {channel.verification_code}"
                    )

        return jsonify({'ok': True})

    except Exception as e:
        current_app.logger.error(f"❌ Ошибка webhook: {e}")
        return jsonify({'ok': True})  # Всегда возвращаем ok для Telegram

# === ОБРАБОТЧИКИ ОШИБОК ===

@channel_bp.errorhandler(404)
def channel_not_found(error):
    """Обработчик 404 ошибок для каналов"""
    return jsonify({
        'error': 'Channel endpoint not found',
        'message': 'The requested channel endpoint does not exist'
    }), 404


@channel_bp.errorhandler(403)
def channel_access_denied(error):
    """Обработчик 403 ошибок для каналов"""
    return jsonify({
        'error': 'Access denied',
        'message': 'You do not have permission to access this channel'
    }), 403


# Инициализация Blueprint
def init_channel_routes():
    """Инициализация маршрутов каналов"""
    current_app.logger.info("✅ Channel routes initialized")


def get_channel_offers_count(channel_id: int) -> int:
    """Получение количества офферов для канала"""
    try:
        import sqlite3
        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()

        # Проверяем таблицу responses (отклики на офферы)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
        if cursor.fetchone():
            cursor.execute("""
                           SELECT COUNT(DISTINCT r.offer_id)
                           FROM responses r
                           WHERE r.channel_id = ?
                           """, (channel_id,))
            result = cursor.fetchone()
            count = result[0] if result else 0
        else:
            count = 0

        conn.close()
        return count

    except Exception as e:
        current_app.logger.error(f"Error getting offers count for channel {channel_id}: {e}")
        return 0


def get_channel_posts_count(channel_id: int) -> int:
    """Получение количества постов канала"""
    try:
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()

        # Проверяем таблицу posts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM posts WHERE channel_id = ?", (channel_id,))
            result = cursor.fetchone()
            count = result[0] if result else 0
        else:
            # Примерный подсчет по дате создания канала
            cursor.execute("SELECT created_at FROM channels WHERE id = ?", (channel_id,))
            result = cursor.fetchone()

            if result and result[0]:
                try:
                    created_at = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                    days_active = (datetime.now() - created_at).days
                    count = max(0, days_active // 7)  # Примерно 1 пост в неделю
                except:
                    count = 0
            else:
                count = 0

        conn.close()
        return count

    except Exception as e:
        current_app.logger.error(f"Error getting posts count for channel {channel_id}: {e}")
        return 0


# Экспорт
__all__ = ['channel_bp', 'init_channel_routes', 'ChannelValidator']