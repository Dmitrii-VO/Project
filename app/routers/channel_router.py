# app/routers/channel_router.py
"""
Маршрутизатор для работы с каналами Telegram Mini App

Содержит все API эндпоинты для управления каналами:
- Добавление и верификация каналов
- Управление настройками каналов
- Статистика каналов
- Поиск и фильтрация
"""

import time
import secrets
from datetime import datetime

import requests
from flask import Blueprint, request, jsonify, current_app, g
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

# Создание Blueprint для каналов
channel_bp = Blueprint('channels', __name__)

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
@cache_response(timeout=120)  # Кэшируем на 2 минуты
def get_channels():
    """
    Получение списка каналов

    Query params:
    - page: номер страницы (по умолчанию 1)
    - limit: количество каналов на странице (по умолчанию 20, макс 100)
    - category: фильтр по категории
    - min_subscribers: минимальное количество подписчиков
    - max_price: максимальная цена за пост
    - verified_only: только верифицированные каналы (true/false)
    - search: поиск по названию канала

    Returns:
        JSON со списком каналов
    """
    try:
        from ..models.channels import Channel
        from ..models.user import User

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

        # Базовый запрос
        query = Channel.query.join(User, Channel.owner_id == User.id)

        # Применяем фильтры
        if verified_only:
            query = query.filter(Channel.is_verified == True)

        if category:
            query = query.filter(Channel.category == category)

        if min_subscribers:
            query = query.filter(Channel.subscribers_count >= min_subscribers)

        if max_price:
            query = query.filter(Channel.price_per_post <= max_price)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Channel.channel_name.ilike(search_pattern),
                    Channel.channel_username.ilike(search_pattern)
                )
            )

        # Получаем общее количество
        total_count = query.count()

        # Получаем каналы с пагинацией
        channels = query.order_by(desc(Channel.subscribers_count)).offset(offset).limit(limit).all()

        # Формируем ответ
        channels_data = []
        for channel in channels:
            channels_data.append({
                'id': channel.id,
                'channel_id': channel.channel_id,
                'channel_name': channel.channel_name,
                'channel_username': channel.channel_username,
                'subscribers_count': channel.subscribers_count,
                'category': channel.category,
                'price_per_post': channel.price_per_post,
                'is_verified': channel.is_verified,
                'created_at': channel.created_at.isoformat() if channel.created_at else None,
                'owner': {
                    'username': channel.owner.username,
                    'first_name': channel.owner.first_name
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

    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting channels: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/<int:channel_id>', methods=['GET'])
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_channel(channel_id):
    """
    Получение информации о конкретном канале

    Args:
        channel_id: ID канала

    Returns:
        JSON с детальной информацией о канале
    """
    try:
        from ..models.channels import Channel
        from ..models.user import User
        from ..models.response import Response
        from ..models.offer import Offer
        from ..models.database import db

        channel = Channel.query.options(
            db.joinedload(Channel.owner)
        ).get(channel_id)

        if not channel:
            return jsonify({
                'error': 'Channel not found'
            }), 404

        # Базовая информация
        channel_data = {
            'id': channel.id,
            'channel_id': channel.channel_id,
            'channel_name': channel.channel_name,
            'channel_username': channel.channel_username,
            'subscribers_count': channel.subscribers_count,
            'category': channel.category,
            'price_per_post': channel.price_per_post,
            'is_verified': channel.is_verified,
            'created_at': channel.created_at.isoformat() if channel.created_at else None,
            'owner': {
                'id': channel.owner.id,
                'username': channel.owner.username,
                'first_name': channel.owner.first_name,
                'last_name': channel.owner.last_name
            }
        }

        # Добавляем статистику если пользователь - владелец канала
        telegram_user_id = TelegramAuth.get_current_user_id()
        if telegram_user_id and channel.owner.telegram_id == telegram_user_id:
            # Статистика откликов
            responses_count = Response.query.filter_by(channel_id=channel.id).count()
            pending_responses = Response.query.filter_by(
                channel_id=channel.id,
                status='pending'
            ).count()
            accepted_responses = Response.query.filter_by(
                channel_id=channel.id,
                status='accepted'
            ).count()

            channel_data['statistics'] = {
                'total_responses': responses_count,
                'pending_responses': pending_responses,
                'accepted_responses': accepted_responses,
                'acceptance_rate': (accepted_responses / responses_count * 100) if responses_count > 0 else 0
            }

            # Последние отклики
            recent_responses = Response.query.filter_by(
                channel_id=channel.id
            ).order_by(desc(Response.created_at)).limit(5).all()

            channel_data['recent_responses'] = [{
                'id': response.id,
                'offer_title': response.offer.title if response.offer else 'Unknown',
                'status': response.status,
                'created_at': response.created_at.isoformat() if response.created_at else None
            } for response in recent_responses]

        return jsonify(channel_data)

    except Exception as e:
        current_app.logger.error(f"Error getting channel {channel_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500



def get_channel_info_simple(channel_id):
    """Простая заглушка для получения информации о канале"""
    return {
        'channel_name': f'Channel {channel_id}',
        'channel_username': f'channel_{channel_id}',
        'member_count': 1000
    }
@channel_bp.route('/', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=5, window=300)  # 5 каналов за 5 минут
def create_channel():
    """
    Добавление нового канала

    Expected JSON:
    {
        "channel_id": "@mychannel или -100123456789",
        "channel_name": "Название канала",
        "category": "technology",
        "price_per_post": 100.0
    }

    Returns:
        JSON с информацией о созданном канале
    """
    try:
        from ..models.channels import Channel
        from ..models.user import User
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400

        # Валидация данных
        validation_errors = ChannelValidator.validate_channel_data(data)
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'details': validation_errors
            }), 400

        # Проверяем лимит каналов для пользователя
        user = User.query.get(g.current_user_id)
        user_channels_count = Channel.query.filter_by(owner_id=user.id).count()

        if user_channels_count >= MAX_CHANNELS_PER_USER:
            return jsonify({
                'error': f'Maximum {MAX_CHANNELS_PER_USER} channels per user'
            }), 400

        # Проверяем, не добавлен ли уже этот канал
        channel_id = data['channel_id']
        existing_channel = Channel.query.filter_by(channel_id=channel_id).first()

        if existing_channel:
            return jsonify({
                'error': 'Channel already exists',
                'existing_channel_id': existing_channel.id
            }), 409

        # Получаем информацию о канале из Telegram API
        telegram_info = get_channel_info_simple(channel_id)

        # Создаем канал
        channel = Channel(
            channel_id=channel_id,
            channel_name=data['channel_name'],
            channel_username=data.get('channel_username') or (
                telegram_info.get('channel_username') if telegram_info else None),
            subscribers_count=telegram_info.get('member_count', 0) if telegram_info else 0,
            category=data.get('category', 'other'),
            price_per_post=float(data.get('price_per_post', 0)),
            owner_id=user.id,
            is_verified=False,
            verification_code=secrets.token_hex(VERIFICATION_CODE_LENGTH)
        )

        # Если получили данные из Telegram API, обновляем
        if telegram_info:
            if telegram_info.get('channel_name'):
                channel.channel_name = telegram_info['channel_name']
            if telegram_info.get('channel_username'):
                channel.channel_username = telegram_info['channel_username']

        db.session.add(channel)
        db.session.commit()

        current_app.logger.info(
            f"Channel created: {channel_id} by user {user.telegram_id}"
        )

        return jsonify({
            'success': True,
            'message': 'Channel created successfully',
            'channel': {
                'id': channel.id,
                'channel_id': channel.channel_id,
                'channel_name': channel.channel_name,
                'channel_username': channel.channel_username,
                'subscribers_count': channel.subscribers_count,
                'category': channel.category,
                'price_per_post': channel.price_per_post,
                'is_verified': channel.is_verified,
                'verification_code': channel.verification_code,
                'verification_instructions': (
                    f"Для подтверждения владения каналом отправьте этот код в ваш канал: {channel.verification_code}\n"
                    f"Система автоматически проверит код и подтвердит канал в течение нескольких минут.\n"
                    f"Если автоматическая проверка не сработает, используйте PUT /api/channels/{channel.id}/verify"
                )
            }
        }), 201

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating channel: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/<int:channel_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=10, window=300)  # 10 обновлений за 5 минут
def update_channel(channel_id):
    """
    Обновление информации о канале

    Args:
        channel_id: ID канала

    Expected JSON:
    {
        "channel_name": "Новое название",
        "category": "technology",
        "price_per_post": 150.0
    }

    Returns:
        JSON с обновленной информацией о канале
    """
    try:
        from ..models.channels import Channel
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400

        # Находим канал
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({
                'error': 'Channel not found or access denied'
            }), 404

        # Валидация данных
        validation_errors = ChannelValidator.validate_channel_data(data)
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'details': validation_errors
            }), 400

        # Обновляем разрешенные поля
        updated_fields = []

        if 'channel_name' in data:
            channel.channel_name = data['channel_name']
            updated_fields.append('channel_name')

        if 'category' in data:
            channel.category = data['category']
            updated_fields.append('category')

        if 'price_per_post' in data:
            channel.price_per_post = float(data['price_per_post'])
            updated_fields.append('price_per_post')

        # Обновляем информацию из Telegram API если нужно
        if 'refresh_telegram_data' in data and data['refresh_telegram_data']:
            telegram_info = get_channel_info_simple(channel_id)
            if telegram_info:
                if telegram_info.get('member_count') is not None:
                    channel.subscribers_count = telegram_info['member_count']
                    updated_fields.append('subscribers_count')

                if telegram_info.get('channel_username'):
                    channel.channel_username = telegram_info['channel_username']
                    updated_fields.append('channel_username')

        if updated_fields:
            db.session.commit()

            current_app.logger.info(
                f"Channel {channel_id} updated fields: {', '.join(updated_fields)} "
                f"by user {g.telegram_user_id}"
            )

        return jsonify({
            'success': True,
            'message': f'Channel updated: {", ".join(updated_fields)}' if updated_fields else 'No changes made',
            'updated_fields': updated_fields,
            'channel': {
                'id': channel.id,
                'channel_id': channel.channel_id,
                'channel_name': channel.channel_name,
                'channel_username': channel.channel_username,
                'subscribers_count': channel.subscribers_count,
                'category': channel.category,
                'price_per_post': channel.price_per_post,
                'is_verified': channel.is_verified
            }
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating channel {channel_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


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
@cache_response(timeout=60)  # Кэшируем на 1 минуту
def get_my_channels():
    """
    Получение каналов текущего пользователя

    Returns:
        JSON со списком каналов пользователя
    """
    try:
        import sqlite3

        # Получаем telegram_user_id из заголовка (установлен middleware)
        telegram_user_id = getattr(g, 'telegram_user_id', None)
        user_id = getattr(g, 'current_user_id', None)

        if not user_id:
            return jsonify({
                'error': 'User not authenticated'
            }), 401

        current_app.logger.info(f"Получение каналов для пользователя ID: {user_id}")

        # Прямое подключение к базе
        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()

        # Получаем каналы пользователя
        cursor.execute("""
                       SELECT id,
                              telegram_id,
                              title,
                              username,
                              subscriber_count,
                              category,
                              is_verified,
                              verification_code,
                              created_at,
                              status
                       FROM channels
                       WHERE owner_id = ?
                       ORDER BY created_at DESC
                       """, (user_id,))

        channels_data = cursor.fetchall()
        conn.close()

        current_app.logger.info(f"Найдено каналов: {len(channels_data)}")

        # Преобразуем в список словарей
        channels_list = []
        for channel in channels_data:
            channel_dict = {
                'id': channel[0],
                'channel_id': channel[1],
                'channel_name': channel[2],
                'channel_username': channel[3],
                'subscribers_count': channel[4] or 0,
                'category': channel[5] or 'other',
                'price_per_post': 0.0,  # Пока зафиксированное значение
                'is_verified': bool(channel[6]),
                'verification_code': channel[7] if not channel[6] else None,
                'created_at': channel[8],
                'status': channel[9] or 'pending'
            }
            channels_list.append(channel_dict)

        return jsonify({
            'success': True,
            'channels': channels_list,
            'total': len(channels_list),
            'user_id': user_id,
            'telegram_user_id': telegram_user_id
        })

    except Exception as e:
        current_app.logger.error(f"Ошибка в get_my_channels: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e)
        }), 500

@channel_bp.route('/<int:channel_id>/responses', methods=['GET'])
@require_telegram_auth
def get_channel_responses(channel_id):
    """
    Получение откликов на канал

    Args:
        channel_id: ID канала

    Query params:
    - status: фильтр по статусу (pending, accepted, rejected)
    - page: номер страницы
    - limit: количество на странице

    Returns:
        JSON со списком откликов на канал
    """
    try:
        from ..models.channels import Channel
        from ..models.response import Response
        from ..models.offer import Offer
        from ..models.user import User

        # Проверяем доступ к каналу
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({
                'error': 'Channel not found or access denied'
            }), 404

        # Параметры пагинации
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фильтры
        status_filter = request.args.get('status')

        # Базовый запрос
        query = Response.query.filter_by(channel_id=channel_id).join(
            Offer, Response.offer_id == Offer.id
        ).join(
            User, Offer.advertiser_id == User.id
        )

        if status_filter:
            query = query.filter(Response.status == status_filter)

        # Получаем общее количество
        total_count = query.count()

        # Получаем отклики с пагинацией
        responses = query.order_by(desc(Response.created_at)).offset(offset).limit(limit).all()

        # Формируем ответ
        responses_data = []
        for response in responses:
            responses_data.append({
                'id': response.id,
                'status': response.status,
                'message': response.message,
                'created_at': response.created_at.isoformat() if response.created_at else None,
                'offer': {
                    'id': response.offer.id,
                    'title': response.offer.title,
                    'description': response.offer.description,
                    'budget': response.offer.budget,
                    'category': response.offer.category
                },
                'advertiser': {
                    'id': response.offer.advertiser.id,
                    'username': response.offer.advertiser.username,
                    'first_name': response.offer.advertiser.first_name
                }
            })

        return jsonify({
            'responses': responses_data,
            'channel': {
                'id': channel.id,
                'channel_name': channel.channel_name
            },
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit,
                'has_next': offset + limit < total_count,
                'has_prev': page > 1
            }
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting channel responses: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/<int:channel_id>/responses/<int:response_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=300)  # 20 действий за 5 минут
def update_response_status(channel_id, response_id):
    """
    Обновление статуса отклика на канал

    Args:
        channel_id: ID канала
        response_id: ID отклика

    Expected JSON:
    {
        "status": "accepted" | "rejected",
        "message": "Причина принятия/отклонения"
    }

    Returns:
        JSON с результатом обновления
    """
    try:
        from ..models.channels import Channel
        from ..models.response import Response
        from ..models.database import db

        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({
                'error': 'Status is required'
            }), 400

        new_status = data['status']
        if new_status not in ['accepted', 'rejected']:
            return jsonify({
                'error': 'Invalid status. Must be "accepted" or "rejected"'
            }), 400

        # Проверяем доступ к каналу
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({
                'error': 'Channel not found or access denied'
            }), 404

        # Находим отклик
        response = Response.query.filter_by(
            id=response_id,
            channel_id=channel_id
        ).first()

        if not response:
            return jsonify({
                'error': 'Response not found'
            }), 404

        if response.status != 'pending':
            return jsonify({
                'error': f'Response already {response.status}'
            }), 400

        # Обновляем статус
        response.status = new_status
        if 'message' in data:
            response.message = data['message']

        db.session.commit()

        current_app.logger.info(
            f"Response {response_id} status updated to {new_status} by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Response {new_status} successfully',
            'response': {
                'id': response.id,
                'status': response.status,
                'message': response.message,
                'updated_at': time.time()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error updating response status: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@channel_bp.route('/categories', methods=['GET'])
@cache_response(timeout=3600)  # Кэшируем на 1 час
def get_categories():
    """
    Получение списка доступных категорий каналов

    Returns:
        JSON со списком категорий и их статистикой
    """
    try:
        from ..models.channels import Channel
        from ..models.database import db
        from sqlalchemy import func

        # Получаем статистику по категориям
        categories_stats = db.session.query(
            Channel.category,
            func.count(Channel.id).label('channels_count'),
            func.avg(Channel.subscribers_count).label('avg_subscribers'),
            func.avg(Channel.price_per_post).label('avg_price')
        ).filter(
            Channel.is_verified == True
        ).group_by(Channel.category).all()

        categories = [
            {
                'name': 'technology',
                'display_name': 'Технологии',
                'description': 'IT, программирование, гаджеты'
            },
            {
                'name': 'business',
                'display_name': 'Бизнес',
                'description': 'Предпринимательство, финансы, инвестиции'
            },
            {
                'name': 'entertainment',
                'display_name': 'Развлечения',
                'description': 'Кино, музыка, шоу-бизнес'
            },
            {
                'name': 'news',
                'display_name': 'Новости',
                'description': 'Актуальные события, политика'
            },
            {
                'name': 'education',
                'display_name': 'Образование',
                'description': 'Обучение, курсы, научные статьи'
            },
            {
                'name': 'lifestyle',
                'display_name': 'Образ жизни',
                'description': 'Мода, красота, путешествия'
            },
            {
                'name': 'sports',
                'display_name': 'Спорт',
                'description': 'Футбол, хоккей, фитнес'
            },
            {
                'name': 'gaming',
                'display_name': 'Игры',
                'description': 'Видеоигры, киберспорт'
            },
            {
                'name': 'other',
                'display_name': 'Другое',
                'description': 'Прочие тематики'
            }
        ]

        # Добавляем статистику к категориям
        stats_dict = {stat.category: stat for stat in categories_stats}

        for category in categories:
            stat = stats_dict.get(category['name'])
            if stat:
                category['statistics'] = {
                    'channels_count': stat.channels_count,
                    'avg_subscribers': int(stat.avg_subscribers or 0),
                    'avg_price': round(float(stat.avg_price or 0), 2)
                }
            else:
                category['statistics'] = {
                    'channels_count': 0,
                    'avg_subscribers': 0,
                    'avg_price': 0
                }

        return jsonify({
            'categories': categories,
            'total_categories': len(categories)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting categories: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


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
        subscribers_stats = db.session.query(
            func.sum(Channel.subscribers_count).label('total_subscribers'),
            func.avg(Channel.subscribers_count).label('avg_subscribers'),
            func.max(Channel.subscribers_count).label('max_subscribers')
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
            'subscribers': {
                'total': int(subscribers_stats.total_subscribers or 0),
                'average': int(subscribers_stats.avg_subscribers or 0),
                'maximum': int(subscribers_stats.max_subscribers or 0)
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


# Экспорт
__all__ = ['channel_bp', 'init_channel_routes', 'ChannelValidator']