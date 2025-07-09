"""
Минимальный API для каналов без проблемных импортов
"""
import os
import random
import re
import time
from flask import Blueprint, current_app, request, jsonify, g
import logging
import sqlite3

from datetime import datetime
from app.config.telegram_config import AppConfig
from app.models.database import execute_db_query
from app.services.telegram_verification import TelegramVerificationService


# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
channels_bp = Blueprint('channels', __name__)

# Путь к базе данных
DATABASE_PATH = 'telegram_mini_app.db'

# Добавьте этот эндпоинт в channels.py

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

@channels_bp.route('/', methods=['GET'])
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

@channels_bp.route('/<int:channel_id>', methods=['GET'])
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

@channels_bp.route('/<int:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    try:
        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        if not telegram_user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем user_id по telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        user_id = user['id']

        # Находим канал
        cursor.execute("SELECT * FROM channels WHERE id = ? AND owner_id = ?", (channel_id, user_id))
        channel = cursor.fetchone()
        if not channel:
            conn.close()
            return jsonify({'error': 'Channel not found or access denied'}), 404

        # Проверяем активные отклики (pending responses)
        cursor.execute("SELECT COUNT(*) as cnt FROM offer_responses WHERE channel_id = ? AND status = 'pending'", (channel_id,))
        active_responses = cursor.fetchone()['cnt']

        if active_responses > 0:
            conn.close()
            return jsonify({
                'error': 'Cannot delete channel with pending responses',
                'active_responses_count': active_responses,
                'message': 'Please resolve all pending responses before deleting the channel'
            }), 400

        # Удаляем связанные отклики
        cursor.execute("DELETE FROM offer_responses WHERE channel_id = ?", (channel_id,))

        # Удаляем канал
        channel_name = channel['title']
        cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))

        conn.commit()
        conn.close()

        current_app.logger.info(
            f"Channel {channel_id} ({channel_name}) deleted by user {telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Channel \"{channel_name}\" deleted successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting channel {channel_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@channels_bp.route('/<int:channel_id>/responses', methods=['GET'])
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

@channels_bp.route('/<int:channel_id>/responses/<int:response_id>', methods=['PUT'])
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

@channels_bp.route('/categories', methods=['GET'])
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

@channels_bp.route('/stats', methods=['GET'])
def get_channels_stats():
    """
    Получение общей статистики по каналам (SQLite версия)

    Returns:
        JSON с общей статистикой
    """
    try:
        # Общая статистика каналов
        total_channels_result = execute_db_query(
            "SELECT COUNT(*) as total FROM channels WHERE is_active = 1",
            fetch_one=True
        )
        total_channels = total_channels_result['total'] if total_channels_result else 0

        verified_channels_result = execute_db_query(
            "SELECT COUNT(*) as verified FROM channels WHERE is_verified = 1 AND is_active = 1",
            fetch_one=True
        )
        verified_channels = verified_channels_result['verified'] if verified_channels_result else 0

        # Статистика по подписчикам (только для верифицированных каналов)
        subscriber_stats_result = execute_db_query("""
            SELECT 
                COALESCE(SUM(subscriber_count), 0) as total_subscribers,
                COALESCE(AVG(subscriber_count), 0) as avg_subscribers,
                COALESCE(MAX(subscriber_count), 0) as max_subscribers
            FROM channels 
            WHERE is_verified = 1 AND is_active = 1
        """, fetch_one=True)

        subscriber_stats = subscriber_stats_result or {
            'total_subscribers': 0,
            'avg_subscribers': 0,
            'max_subscribers': 0
        }

        # Топ категории (только верифицированные каналы)
        top_categories_result = execute_db_query("""
            SELECT 
                category,
                COUNT(*) as count
            FROM channels 
            WHERE is_verified = 1 AND is_active = 1
            GROUP BY category 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """, fetch_all=True)

        top_categories = top_categories_result or []

        # Дополнительная статистика по статусам
        status_stats_result = execute_db_query("""
            SELECT 
                status,
                COUNT(*) as count
            FROM channels
            WHERE is_active = 1
            GROUP BY status
        """, fetch_all=True)

        status_stats = status_stats_result or []

        # Статистика по языкам
        language_stats_result = execute_db_query("""
            SELECT 
                language,
                COUNT(*) as count
            FROM channels
            WHERE is_verified = 1 AND is_active = 1
            GROUP BY language
            ORDER BY COUNT(*) DESC
            LIMIT 3
        """, fetch_all=True)

        language_stats = language_stats_result or []

        return jsonify({
            'channels': {
                'total': total_channels,
                'verified': verified_channels,
                'verification_rate': round((verified_channels / total_channels * 100), 2) if total_channels > 0 else 0,
                'active': total_channels
            },
            'subscribers': {
                'total': int(subscriber_stats['total_subscribers']),
                'average': int(subscriber_stats['avg_subscribers']),
                'maximum': int(subscriber_stats['max_subscribers'])
            },
            'categories': {
                'top_categories': [
                    {
                        'category': cat['category'] or 'other',
                        'count': cat['count']
                    } for cat in top_categories
                ]
            },
            'status_distribution': [
                {
                    'status': stat['status'] or 'unknown',
                    'count': stat['count']
                } for stat in status_stats
            ],
            'languages': {
                'top_languages': [
                    {
                        'language': lang['language'] or 'unknown',
                        'count': lang['count']
                    } for lang in language_stats
                ]
            },
            'metadata': {
                'cache_timeout': 300,
                'generated_at': datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channels stats: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e) if current_app.debug else 'Failed to retrieve channel statistics'
        }), 500

@channels_bp.route('/analyze', methods=['POST'])
def analyze_channel():
    """Анализ канала по username для получения информации"""
    try:
        logger.info("🔍 Анализ канала")

        data = request.get_json()
        if not data:
            logger.error("❌ Нет JSON данных")
            return jsonify({'success': False, 'error': 'JSON данные обязательны'}), 400

        # Проверяем разные варианты передачи username
        username = data.get('username') or data.get('channel_username') or data.get('channel_url', '')
        if not username:
            logger.error("❌ Не найден username канала")
            return jsonify({'success': False, 'error': 'Username канала обязателен'}), 400

        # Извлекаем username из различных форматов URL
        cleaned_username = extract_username_from_url(username)
        logger.info(f"📺 Анализируем канал: @{cleaned_username}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')
        logger.info(f"👤 Пользователь: {telegram_user_id}")

        # Проверяем, не добавлен ли уже канал
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT c.id, c.title
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       WHERE (c.username = ? OR c.telegram_id = ?)
                         AND u.telegram_id = ?
                       """, (cleaned_username, cleaned_username, telegram_user_id))

        existing_channel = cursor.fetchone()
        conn.close()

        if existing_channel:
            logger.warning(f"❌ Канал @{cleaned_username} уже добавлен")
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен'
            }), 409

        # Сначала пробуем получить реальные данные из Telegram API
        real_data = {'success': False}  
        # Определяем категорию по username
        category = 'other'
        if any(word in cleaned_username.lower() for word in ['tech', 'it', 'dev', 'code']):
            category = 'technology'
        elif any(word in cleaned_username.lower() for word in ['news', 'новости']):
            category = 'news'
        elif any(word in cleaned_username.lower() for word in ['crypto', 'bitcoin', 'btc']):
            category = 'crypto'
        elif any(word in cleaned_username.lower() for word in ['game', 'игр']):
            category = 'gaming'

        # Всегда используем сгенерированные данные (JavaScript делает реальные запросы)
        logger.info(f"⚠️ Используем сгенерированные данные для @{cleaned_username}")

        if real_data.get('success'):
            logger.info(f"✅ Получены реальные данные для @{cleaned_username}")

            channel_info = {
                'success': True,
                'data': {
                    'username': cleaned_username,
                    'title': real_data.get('title', f'Канал @{cleaned_username}'),
                    'description': real_data.get('description') or f'Telegram канал @{cleaned_username}',
                    'subscriber': real_data.get('subscriber', 0),
                    'engagement_rate': round(random.uniform(1.0, 15.0), 1) if real_data.get('subscriber', 0) > 0 else 0,
                    'verified': False,  # Эту информацию сложно получить через API
                    'category': category,
                    'avatar_letter': cleaned_username[0].upper() if cleaned_username else 'C',
                    'channel_type': real_data.get('type', 'channel'),
                    'invite_link': real_data.get('invite_link') or f'https://t.me/{cleaned_username}',
                    'estimated_reach': {
                        'min_views': int(real_data.get('subscriber', 0) * 0.1),
                        'max_views': int(real_data.get('subscriber', 0) * 0.4),
                        'avg_views': int(real_data.get('subscriber', 0) * 0.25)
                    } if real_data.get('subscriber', 0) > 0 else None,
                    'data_source': 'telegram_api'
                },
                'user_permissions': {
                    'is_admin': True,
                    'can_post': True
                },
                'note': 'Данные получены из Telegram API'
            }
        else:
            logger.info(f"⚠️ Данных нет для @{cleaned_username}")
            return jsonify(channel_info)

    except Exception as e:
        logger.error(f"💥 Ошибка анализа канала: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500

@channels_bp.route('/my', methods=['GET'])
def get_my_channels():
    """
    ФУНКЦИЯ 3: Получение каналов текущего пользователя
    ИСПРАВЛЕНО: убран SQLAlchemy, исправлены имена полей
    """
    try:
        # Получаем telegram_user_id из заголовков (универсально для фронта)
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        if not telegram_user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        current_app.logger.info(f"Получение каналов для пользователя telegram_id: {telegram_user_id}")

        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем user_id по telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'success': True, 'channels': [], 'total': 0})

        user_id = user['id']

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

        channels_list = []
        for channel in channels_data:
            channel_dict = {
                'id': channel['id'],
                'channel_id': channel['telegram_id'],
                'channel_name': channel['title'] or 'Неизвестный канал',
                'title': channel['title'] or 'Неизвестный канал',
                'channel_username': channel['username'],
                'username': channel['username'],
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

@channels_bp.route('/<int:channel_id>/update-stats', methods=['PUT', 'POST'])
def update_channel_stats(channel_id):
    """Обновление статистики канала данными от фронтенда"""

    logger.info(f"📊 Обновление статистики канала {channel_id}")

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'JSON данные обязательны'}), 400

    # Получаем telegram_user_id из заголовков
    telegram_user_id = request.headers.get('X-Telegram-User-Id')
    if not telegram_user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    conn = sqlite3.connect(AppConfig.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Проверяем права на канал
    cursor.execute("""
                    SELECT c.id, c.title, c.username, c.subscriber_count
                    FROM channels c
                            JOIN users u ON c.owner_id = u.id
                    WHERE c.id = ?
                        AND u.telegram_id = ?
                    """, (channel_id, telegram_user_id))

    channel = cursor.fetchone()
    if not channel:
        conn.close()
        return jsonify({'success': False, 'error': 'Канал не найден'}), 404
    logger.info(f"✅ Канал найден: {channel['title']} (ID: {channel_id})")

@channels_bp.route('', methods=['POST'])
def add_channel():
    """Добавление нового канала с данными от фронтенда"""
    try:
        logger.info("➕ Попытка добавления нового канала")

        # ✅ ПРАВИЛЬНЫЙ ПОРЯДОК: СНАЧАЛА ПОЛУЧАЕМ data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400

        # ✅ ИНИЦИАЛИЗИРУЕМ subscriber_count ИЗ ДАННЫХ
        subscriber_count = data.get('subscriber_count', 0)

        # Проверяем разные варианты передачи данных о подписчиках
        possible_subscriber_fields = [
            'subscriber_count',     # Основное поле для БД
            'subscribers_count',    # Для совместимости 
            'raw_subscriber_count', # Из анализатора
            'member_count'          # ✅ ДОБАВИТЬ: Из Bot API
        ]

        for field in possible_subscriber_fields:
            value = data.get(field)
            if value and isinstance(value, (int, str)) and str(value).replace('K', '').replace('M', '').replace('.', '').isdigit():
                subscriber_count = value
                logger.info(f"✅ Найдены подписчики в поле '{field}': {subscriber_count}")
                break
        
        # ✅ ОБРАБОТКА СТРОКОВЫХ ЗНАЧЕНИЙ
        if isinstance(subscriber_count, str):
            try:
                if subscriber_count.upper().endswith('K'):
                    subscriber_count = int(float(subscriber_count[:-1]) * 1000)
                elif subscriber_count.upper().endswith('M'):
                    subscriber_count = int(float(subscriber_count[:-1]) * 1000000)
                else:
                    subscriber_count = int(subscriber_count)
            except (ValueError, TypeError):
                subscriber_count = 0

        # Убеждаемся что это число
        if not isinstance(subscriber_count, int):
            subscriber_count = 0

        logger.info(f"📊 Количество подписчиков для сохранения: {subscriber_count}")
        logger.info(f"🔍 DEBUG: Полученные данные = {data}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')
        logger.info(f"👤 Пользователь: {telegram_user_id}")

        username = data.get('username', '').strip()
        if not username:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        cleaned_username = extract_username_from_url(username)
        logger.info(f"📺 Добавляем канал: @{cleaned_username}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем ID пользователя
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()

        if not user:
            # Создаем пользователя если не существует
            cursor.execute("""
                           INSERT INTO users (telegram_id, username, first_name, is_active, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)
                           """, (telegram_user_id, f'user_{telegram_user_id}', 'User', True,
                                 datetime.now().isoformat(), datetime.now().isoformat()))
            user_db_id = cursor.lastrowid
            logger.info(f"✅ Создан новый пользователь с ID: {user_db_id}")
        else:
            user_db_id = user['id']
            logger.info(f"✅ Найден пользователь с ID: {user_db_id}")

        # Проверяем, не добавлен ли уже канал
        is_reverify = data.get('action') == 'reverify'

        cursor.execute("""
                       SELECT c.id, c.title, c.verification_code, c.is_verified, c.status
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       WHERE (c.username = ? OR c.username = ? OR c.telegram_id = ?)
                         AND u.telegram_id = ?
                       """, (cleaned_username, f"@{cleaned_username}", cleaned_username, telegram_user_id))

        existing_channel = cursor.fetchone()

        if existing_channel and not is_reverify:
            conn.close()
            if existing_channel['is_verified']:
                logger.info(f"✅ Канал уже верифицирован")
                return jsonify({
                    'success': True,
                    'already_exists': True,
                    'is_verified': True,
                    'message': 'Канал уже добавлен и верифицирован',
                    'channel': {
                        'id': existing_channel['id'],
                        'title': existing_channel['title'],
                        'username': cleaned_username,
                        'status': existing_channel['status']
                    }
                })
            else:
                logger.info(f"⚠️ Канал существует но не верифицирован")
                return jsonify({
                    'success': True,
                    'already_exists': True,
                    'is_verified': False,
                    'message': 'Канал уже добавлен, но требует верификации',
                    'verification_code': existing_channel['verification_code'],
                    'channel': {
                        'id': existing_channel['id'],
                        'title': existing_channel['title'],
                        'username': cleaned_username,
                        'status': existing_channel['status']
                    }
                })

        # Генерируем код верификации
        import secrets
        verification_code = f'VERIFY_{secrets.token_hex(4).upper()}'
        logger.info(f"📝 Сгенерирован код верификации: {verification_code}")

        # ✅ ПРАВИЛЬНОЕ ОПРЕДЕЛЕНИЕ telegram_id
        telegram_channel_id = data.get('telegram_id') or data.get('channel_id') or cleaned_username

        # Получаем дополнительные данные
        title = data.get('title', f'Канал @{cleaned_username}')
        description = data.get('description', '')
        category = data.get('category', 'other')

        current_time = datetime.now().isoformat()

        if existing_channel and is_reverify:
            # Обновляем существующий канал для повторной верификации
            logger.info(f"🔄 Обновляем канал для повторной верификации")
            
            cursor.execute("""
                           UPDATE channels 
                           SET verification_code = ?, 
                               status = 'pending',
                               updated_at = ?,
                               subscriber_count = ?
                           WHERE id = ?
                           """, (verification_code, current_time, subscriber_count, existing_channel['id']))
            
            channel_id = existing_channel['id']
            logger.info(f"✅ Канал {channel_id} обновлен для повторной верификации")
        else:
            # Добавляем новый канал в БД
            logger.info(f"➕ Добавляем новый канал в базу данных")
            
            cursor.execute("""
                           INSERT INTO channels (telegram_id, title, username, description, category,
                                                 subscriber_count, language, is_verified, is_active,
                                                 owner_id, created_at, updated_at, status, verification_code)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           """, (
                telegram_channel_id, title, cleaned_username, description, category,
                subscriber_count, 'ru', False, True,
                user_db_id, current_time, current_time, 'pending', verification_code
            ))

            channel_id = cursor.lastrowid
            logger.info(f"✅ Канал добавлен в БД с ID: {channel_id}")

        conn.commit()
        conn.close()

        # Возвращаем успешный ответ
        response_data = {
            'success': True,
            'message': 'Канал успешно добавлен! Теперь подтвердите владение.',
            'verification_code': verification_code,
            'channel': {
                'id': channel_id,
                'title': title,
                'username': cleaned_username,
                'subscriber_count': subscriber_count,
                'status': 'pending',
                'verification_code': verification_code
            },
            'instructions': [
                f'1. Перейдите в ваш канал @{cleaned_username}',
                f'2. Опубликуйте сообщение с кодом: {verification_code}',
                '3. Переслать это сообщение нашему боту',
                '4. Дождитесь подтверждения верификации'
            ]
        }

        logger.info(f"🎉 Канал {cleaned_username} успешно добавлен!")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Ошибка добавления канала: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500

@channels_bp.route('/<int:channel_id>/verify', methods=['PUT', 'POST'])
def verify_channel_endpoint(channel_id):
    """Верификация канала"""
    try:
        logger.info(f"🔍 Запрос верификации канала {channel_id}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем канал
        cursor.execute("""
            SELECT c.*, u.telegram_id as owner_telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ? AND u.telegram_id = ?
        """, (channel_id, telegram_user_id))

        channel = cursor.fetchone()

        if not channel:
            conn.close()
            return jsonify({'success': False, 'error': 'Канал не найден'}), 404

        if channel['is_verified']:
            conn.close()
            return jsonify({
                'success': True,
                'message': 'Канал уже верифицирован',
                'channel': dict(channel)
            })

        # Используем сервис верификации
        channel_username = channel['username']
        verification_code = channel['verification_code']

        # Добавляем @ если нужно
        if channel_username and not channel_username.startswith('@'):
            channel_username = '@' + channel_username

        logger.info(f"🔍 Проверяем {channel_username} с кодом {verification_code}")

        # Вызываем сервис верификации
        verification_result = TelegramVerificationService.verify_channel(channel_username, verification_code)

        if verification_result.get('success') and verification_result.get('found'):
            # Обновляем статус
            cursor.execute("""
                UPDATE channels 
                SET is_verified = 1, 
                    verified_at = ?,
                    status = 'verified'
                WHERE id = ?
            """, (datetime.now().isoformat(), channel_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ Канал {channel_id} верифицирован!")

            return jsonify({
                'success': True,
                'message': 'Канал успешно верифицирован!',
                'channel': {
                    'id': channel_id,
                    'title': channel['title'],
                    'is_verified': True,
                    'verified_at': datetime.now().isoformat()
                }
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Код верификации не найден в канале',
                'verification_code': verification_code,
                'instructions': [
                    f'1. Перейдите в канал @{channel["username"]}',
                    f'2. Опубликуйте сообщение с кодом: {verification_code}',
                    '3. Подождите 1-2 минуты или нажмите "Верифицировать" снова'
                ]
            }), 400

    except Exception as e:
        logger.error(f"❌ Ошибка верификации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@channels_bp.route('/debug/<int:channel_id>', methods=['GET'])
def debug_channel(channel_id):
    """Отладочная информация о канале"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Канал не найден'}), 404

        result = {
            'channel': dict(channel),
            'webhook_url': f"{os.environ.get('WEBAPP_URL', 'http://localhost:5000')}/api/channels/webhook",
            'bot_token_available': bool(os.environ.get('BOT_TOKEN')),
            'verification_service_loaded': 'verify_channel' in globals()
        }

        conn.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_username_from_url(url):
    """Извлекает username из различных форматов URL Telegram"""
    # Убираем пробелы
    url = url.strip()

    # Если это уже чистый username
    if not url.startswith('http') and not url.startswith('@'):
        return url.lstrip('@')

    # Паттерны для извлечения username
    patterns = [
        r'https?://t\.me/([a-zA-Z0-9_]+)',  # https://t.me/username
        r'https?://telegram\.me/([a-zA-Z0-9_]+)',  # https://telegram.me/username
        r'@([a-zA-Z0-9_]+)',  # @username
        r'^([a-zA-Z0-9_]+)$'  # просто username
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            logger.info(f"🔍 Извлечен username: {username} из URL: {url}")
            return username

    # Если ничего не найдено, возвращаем как есть
    logger.warning(f"⚠️ Не удалось извлечь username из: {url}")
    return url.lstrip('@')

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(AppConfig.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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

