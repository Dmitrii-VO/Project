from flask import Blueprint, request, jsonify
from app.services.auth_service import auth_service
from app.services.security_service import security_service
from app.utils.decorators import require_telegram_auth
from app.models.database import db_manager
from app.config.settings import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
channels_bp = Blueprint('channels', __name__)


@channels_bp.route('/search', methods=['POST'])
@require_telegram_auth
def search_channel():
    """Поиск канала через Telegram API"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        username = data['username'].strip().lstrip('@')
        user_id = auth_service.get_current_user_id()

        # Здесь должен быть вызов Telegram API
        # Пока возвращаем заглушку
        return jsonify({
            'success': True,
            'channel': {
                'id': f'fake_id_{username}',
                'username': username,
                'title': f'Канал @{username}',
                'description': 'Описание канала',
                'subscribers_count': 1000,
                'verified': False
            },
            'user_permissions': {
                'is_admin': True
            }
        })

    except Exception as e:
        logger.error(f"Search channel error: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500


@channels_bp.route('', methods=['POST'])
@require_telegram_auth
def add_channel():
    """Добавление канала"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400

        username = data.get('username', '').strip()
        telegram_user_id = auth_service.get_current_user_id()

        if not username:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        # Получаем или создаем пользователя
        user_db_id = db_manager.ensure_user_exists(telegram_user_id)

        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка создания пользователя'}), 500

        cleaned_username = username.lstrip('@')

        # Проверяем, не добавлен ли уже канал
        existing_channel = db_manager.execute_query("""
                                                    SELECT c.id, c.title
                                                    FROM channels c
                                                             JOIN users u ON c.owner_id = u.id
                                                    WHERE c.username = ?
                                                      AND u.telegram_id = ?
                                                    """, (cleaned_username, telegram_user_id), fetch_one=True)

        if existing_channel:
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен вами'
            })

        # Добавляем канал в базу
        current_time = datetime.now().isoformat()

        channel_id = db_manager.execute_query("""
                                              INSERT INTO channels (telegram_id, username, title, description, owner_id,
                                                                    category, created_at)
                                              VALUES (?, ?, ?, ?, ?, ?, ?)
                                              """, (
                                                  f'fake_id_{cleaned_username}',
                                                  cleaned_username,
                                                  data.get('title', f'Канал @{cleaned_username}'),
                                                  data.get('description', ''),
                                                  user_db_id,
                                                  data.get('category', 'general'),
                                                  datetime.now().isoformat()
                                              ))

        if channel_id:
            logger.info(f"Канал {cleaned_username} добавлен пользователем {telegram_user_id}")

        if channel_id:
            logger.info(f"✅ Channel @{cleaned_username} successfully added for user {telegram_user_id}")
            return jsonify({
                'success': True,
                'message': f'Канал @{cleaned_username} успешно добавлен!',
                'channel': {
                    'id': channel_id,
                    'username': cleaned_username,
                    'title': f'Канал @{cleaned_username}',
                    'subscribers_count': 1000
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Канал не был добавлен в базу данных'
            })

    except Exception as e:
        logger.error(f"Ошибка добавления канала: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка сервера: {str(e)}'
        }), 500


@channels_bp.route('/my', methods=['GET'])
@require_telegram_auth
def get_my_channels():
    """Получение моих каналов"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        user_db_id = db_manager.ensure_user_exists(telegram_user_id)
        if not user_db_id:
            return jsonify({
                'success': False,
                'channels': [],
                'total': 0,
                'message': 'Ошибка пользователя'
            }), 500

        # Получаем каналы пользователя
        channels = db_manager.execute_query("""
                                            SELECT c.*, u.username as owner_username, u.telegram_id as owner_telegram_id
                                            FROM channels c
                                                     JOIN users u ON c.owner_id = u.id
                                            WHERE c.owner_id = ?
                                              AND u.telegram_id = ?
                                            ORDER BY c.created_at DESC
                                            """, (user_db_id, telegram_user_id), fetch_all=True)

        if not channels:
            return jsonify({
                'success': True,
                'channels': [],
                'total': 0,
                'message': 'У вас пока нет добавленных каналов'
            })

        # Обогащаем данные каналов
        enriched_channels = []
        for channel in channels:
            channel_data = dict(channel)

            # Обеспечиваем совместимость полей
            if 'subscriber_count' not in channel_data:
                channel_data['subscriber_count'] = channel_data.get('subscribers_count', 0)

            # Форматируем дату
            if channel_data.get('created_at'):
                try:
                    created_at = datetime.fromisoformat(channel_data['created_at'].replace('Z', '+00:00'))
                    channel_data['created_at_formatted'] = created_at.strftime('%d.%m.%Y')
                except:
                    channel_data['created_at_formatted'] = 'Неизвестно'

            enriched_channels.append(channel_data)

        # Статистика
        stats = {
            'total_channels': len(enriched_channels),
            'verified_channels': len([c for c in enriched_channels if c.get('is_verified')]),
            'active_channels': len([c for c in enriched_channels if c.get('is_active')]),
            'total_subscribers': sum(c.get('subscriber_count', 0) or 0 for c in enriched_channels)
        }

        return jsonify({
            'success': True,
            'channels': enriched_channels,
            'total': len(enriched_channels),
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Ошибка получения каналов: {e}")
        return jsonify({
            'success': False,
            'channels': [],
            'error': str(e)
        }), 500


@channels_bp.route('/<int:channel_id>', methods=['DELETE'])
@require_telegram_auth
def delete_channel(channel_id):
    """Удаление канала"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        # Проверяем права на удаление
        channel = db_manager.execute_query('''
                                           SELECT c.id, c.title, c.username
                                           FROM channels c
                                                    JOIN users u ON c.owner_id = u.id
                                           WHERE c.id = ?
                                             AND u.telegram_id = ?
                                           ''', (channel_id, telegram_user_id), fetch_one=True)

        if not channel:
            return jsonify({
                'success': False,
                'error': 'Канал не найден или у вас нет прав на его удаление'
            }), 404

        # Удаляем канал
        result = db_manager.execute_query('''
                                          DELETE
                                          FROM channels
                                          WHERE id = ?
                                          ''', (channel_id,))

        if result is not None:
            logger.info(f"Канал {channel_id} удален пользователем {telegram_user_id}")
            return jsonify({
                'success': True,
                'message': f'Канал @{channel["username"]} удален'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ошибка удаления канала'
            }), 500

    except Exception as e:
        logger.error(f"Ошибка удаления канала: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500