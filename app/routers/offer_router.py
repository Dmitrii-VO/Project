# app/routers/offer_router.py
"""
Маршрутизатор для работы с офферами Telegram Mini App

Содержит все API эндпоинты для управления рекламными офферами:
- Создание и управление офферами
- Поиск подходящих каналов
- Система откликов
- Статистика офферов
"""

import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import and_, or_, desc, func
from .middleware import (
    require_telegram_auth,
    cache_response,
    rate_limit_decorator,
    TelegramAuth
)

# Создание Blueprint для офферов
offer_bp = Blueprint('offers', __name__)

# Константы
MAX_OFFERS_PER_USER = 50
MIN_BUDGET = 100  # Минимальный бюджет в рублях
MAX_BUDGET = 1000000  # Максимальный бюджет


class OfferValidator:
    """Класс для валидации данных офферов"""

    @staticmethod
    def validate_offer_data(data):
        """Валидация основных данных оффера"""
        errors = []

        # Проверка обязательных полей
        required_fields = ['title', 'description', 'budget']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} is required')

        # Валидация заголовка
        title = data.get('title', '')
        if title:
            if len(title) < 5:
                errors.append('Title must be at least 5 characters')
            elif len(title) > 200:
                errors.append('Title must be no more than 200 characters')

        # Валидация описания
        description = data.get('description', '')
        if description:
            if len(description) < 20:
                errors.append('Description must be at least 20 characters')
            elif len(description) > 2000:
                errors.append('Description must be no more than 2000 characters')

        # Валидация бюджета
        budget = data.get('budget')
        if budget is not None:
            try:
                budget = float(budget)
                if budget < MIN_BUDGET:
                    errors.append(f'Budget must be at least {MIN_BUDGET} rubles')
                elif budget > MAX_BUDGET:
                    errors.append(f'Budget cannot exceed {MAX_BUDGET} rubles')
            except (ValueError, TypeError):
                errors.append('Invalid budget format')

        # Валидация категории
        valid_categories = [
            'technology', 'business', 'entertainment', 'news',
            'education', 'lifestyle', 'sports', 'gaming', 'other'
        ]
        category = data.get('category')
        if category and category not in valid_categories:
            errors.append(f'Invalid category. Allowed: {", ".join(valid_categories)}')

        # Валидация даты окончания
        end_date = data.get('end_date')
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if end_datetime <= datetime.utcnow():
                    errors.append('End date must be in the future')
            except ValueError:
                errors.append('Invalid end_date format. Use ISO format')

        # Валидация целевой аудитории
        target_audience = data.get('target_audience', {})
        if target_audience:
            min_subscribers = target_audience.get('min_subscribers')
            if min_subscribers is not None:
                try:
                    min_subscribers = int(min_subscribers)
                    if min_subscribers < 0:
                        errors.append('min_subscribers cannot be negative')
                except (ValueError, TypeError):
                    errors.append('Invalid min_subscribers format')

            max_price = target_audience.get('max_price')
            if max_price is not None:
                try:
                    max_price = float(max_price)
                    if max_price < 0:
                        errors.append('max_price cannot be negative')
                except (ValueError, TypeError):
                    errors.append('Invalid max_price format')

        return errors


class OfferMatchingService:
    """Сервис для поиска подходящих каналов для офферов"""

    @staticmethod
    def find_matching_channels(offer_id, limit=20):
        """Поиск каналов, подходящих для оффера"""
        try:
            from ..models.offer import Offer
            from ..models.channels import Channel
            from ..models.response import Response
            from ..models.database import db

            offer = Offer.query.get(offer_id)
            if not offer:
                return []

            # Базовый запрос - только верифицированные каналы
            query = Channel.query.filter(Channel.is_verified == True)

            # Фильтр по категории
            if offer.category and offer.category != 'other':
                query = query.filter(Channel.category == offer.category)

            # Фильтр по целевой аудитории
            if offer.target_audience:
                target = offer.target_audience

                # Минимальное количество подписчиков
                if target.get('min_subscribers'):
                    query = query.filter(
                        Channel.subscribers_count >= target['min_subscribers']
                    )

                # Максимальная цена за пост
                if target.get('max_price'):
                    query = query.filter(
                        Channel.price_per_post <= target['max_price']
                    )

                # Категории каналов
                if target.get('categories'):
                    query = query.filter(
                        Channel.category.in_(target['categories'])
                    )

            # Исключаем каналы, которые уже откликнулись
            responded_channels = db.session.query(Response.channel_id).filter_by(
                offer_id=offer_id
            ).subquery()

            query = query.filter(
                ~Channel.id.in_(responded_channels)
            )

            # Исключаем каналы владельца оффера
            query = query.filter(Channel.owner_id != offer.advertiser_id)

            # Сортируем по количеству подписчиков и цене
            channels = query.order_by(
                desc(Channel.subscribers_count),
                Channel.price_per_post
            ).limit(limit).all()

            # Добавляем рейтинг соответствия
            scored_channels = []
            for channel in channels:
                score = OfferMatchingService.calculate_match_score(offer, channel)
                scored_channels.append({
                    'channel': channel,
                    'match_score': score
                })

            # Сортируем по рейтингу
            scored_channels.sort(key=lambda x: x['match_score'], reverse=True)

            return scored_channels[:limit]

        except Exception as e:
            current_app.logger.error(f"Error finding matching channels: {e}")
            return []

    @staticmethod
    def calculate_match_score(offer, channel):
        """Расчет рейтинга соответствия канала офферу"""
        score = 0

        # Соответствие категории (40 баллов)
        if offer.category == channel.category:
            score += 40
        elif offer.category == 'other':
            score += 20

        # Соответствие бюджета и цены (30 баллов)
        if channel.price_per_post > 0:
            if offer.budget >= channel.price_per_post:
                price_ratio = min(offer.budget / channel.price_per_post, 10)
                score += min(price_ratio * 3, 30)
        else:
            score += 15  # Бесплатные размещения

        # Количество подписчиков (20 баллов)
        if channel.subscribers_count > 0:
            # Логарифмическая шкала для подписчиков
            import math
            subscribers_score = min(math.log10(channel.subscribers_count) * 5, 20)
            score += subscribers_score

        # Верификация канала (10 баллов)
        if channel.is_verified:
            score += 10

        return round(score, 2)


# === API ЭНДПОИНТЫ ===

@offer_bp.route('/', methods=['GET'])
@cache_response(timeout=120)  # Кэшируем на 2 минуты
def get_offers():
    """
    Получение списка офферов

    Query params:
    - page: номер страницы (по умолчанию 1)
    - limit: количество офферов на странице (по умолчанию 20, макс 100)
    - category: фильтр по категории
    - min_budget: минимальный бюджет
    - max_budget: максимальный бюджет
    - status: статус оффера (active, paused, completed, expired)
    - search: поиск по заголовку и описанию
    - my_offers: только офферы текущего пользователя (true/false)

    Returns:
        JSON со списком офферов
    """
    try:
        from ..models.offer import Offer
        from ..models.user import User
        from ..models.response import Response

        # Параметры пагинации
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фильтры
        category = request.args.get('category')
        min_budget = request.args.get('min_budget', type=float)
        max_budget = request.args.get('max_budget', type=float)
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        my_offers = request.args.get('my_offers', '').lower() == 'true'

        # Базовый запрос
        query = Offer.query.join(User, Offer.advertiser_id == User.id)

        # Фильтр по пользователю
        if my_offers:
            telegram_user_id = TelegramAuth.get_current_user_id()
            if telegram_user_id:
                user = User.query.filter_by(telegram_id=telegram_user_id).first()
                if user:
                    query = query.filter(Offer.advertiser_id == user.id)
                else:
                    # Если пользователь не найден, возвращаем пустой результат
                    return jsonify({
                        'offers': [],
                        'pagination': {'page': 1, 'limit': limit, 'total': 0, 'pages': 0}
                    })
        else:
            # Для публичного списка показываем только активные офферы
            query = query.filter(Offer.status == 'active')

        # Применяем фильтры
        if category:
            query = query.filter(Offer.category == category)

        if min_budget:
            query = query.filter(Offer.budget >= min_budget)

        if max_budget:
            query = query.filter(Offer.budget <= max_budget)

        if status:
            query = query.filter(Offer.status == status)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Offer.title.ilike(search_pattern),
                    Offer.description.ilike(search_pattern)
                )
            )

        # Получаем общее количество
        total_count = query.count()

        # Получаем офферы с пагинацией
        offers = query.order_by(desc(Offer.created_at)).offset(offset).limit(limit).all()

        # Формируем ответ
        offers_data = []
        for offer in offers:
            # Подсчитываем отклики для каждого оффера
            responses_count = Response.query.filter_by(offer_id=offer.id).count()

            offer_data = {
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'created_at': offer.created_at.isoformat() if offer.created_at else None,
                'end_date': offer.end_date.isoformat() if offer.end_date else None,
                'target_audience': offer.target_audience,
                'responses_count': responses_count,
                'advertiser': {
                    'username': offer.advertiser.username,
                    'first_name': offer.advertiser.first_name
                }
            }

            # Добавляем дополнительную информацию для владельца
            if hasattr(g, 'current_user_id') and offer.advertiser_id == g.current_user_id:
                pending_responses = Response.query.filter_by(
                    offer_id=offer.id,
                    status='pending'
                ).count()
                accepted_responses = Response.query.filter_by(
                    offer_id=offer.id,
                    status='accepted'
                ).count()

                offer_data['detailed_stats'] = {
                    'pending_responses': pending_responses,
                    'accepted_responses': accepted_responses
                }

            offers_data.append(offer_data)

        return jsonify({
            'offers': offers_data,
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
                'min_budget': min_budget,
                'max_budget': max_budget,
                'status': status,
                'search': search,
                'my_offers': my_offers
            }
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting offers: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>', methods=['GET'])
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_offer(offer_id):
    """
    Получение информации о конкретном оффере

    Args:
        offer_id: ID оффера

    Returns:
        JSON с детальной информацией об оффере
    """
    try:
        from ..models.offer import Offer
        from ..models.user import User
        from ..models.response import Response
        from ..models.channels import Channel
        from ..models.database import db

        offer = Offer.query.options(
            db.joinedload(Offer.advertiser)
        ).get(offer_id)

        if not offer:
            return jsonify({
                'error': 'Offer not found'
            }), 404

        # Базовая информация
        offer_data = {
            'id': offer.id,
            'title': offer.title,
            'description': offer.description,
            'budget': offer.budget,
            'category': offer.category,
            'status': offer.status,
            'created_at': offer.created_at.isoformat() if offer.created_at else None,
            'end_date': offer.end_date.isoformat() if offer.end_date else None,
            'target_audience': offer.target_audience,
            'advertiser': {
                'id': offer.advertiser.id,
                'username': offer.advertiser.username,
                'first_name': offer.advertiser.first_name,
                'last_name': offer.advertiser.last_name
            }
        }

        # Добавляем детальную информацию для владельца оффера
        telegram_user_id = TelegramAuth.get_current_user_id()
        if telegram_user_id and offer.advertiser.telegram_id == telegram_user_id:
            # Статистика откликов
            responses_stats = db.session.query(
                Response.status,
                func.count(Response.id).label('count')
            ).filter_by(offer_id=offer.id).group_by(Response.status).all()

            stats = {status: count for status, count in responses_stats}

            offer_data['statistics'] = {
                'total_responses': sum(stats.values()),
                'pending_responses': stats.get('pending', 0),
                'accepted_responses': stats.get('accepted', 0),
                'rejected_responses': stats.get('rejected', 0)
            }

            # Последние отклики
            recent_responses = Response.query.filter_by(
                offer_id=offer.id
            ).join(Channel).order_by(desc(Response.created_at)).limit(5).all()

            offer_data['recent_responses'] = [{
                'id': response.id,
                'channel_name': response.channel.channel_name if response.channel else 'Unknown',
                'channel_subscribers': response.channel.subscribers_count if response.channel else 0,
                'status': response.status,
                'created_at': response.created_at.isoformat() if response.created_at else None
            } for response in recent_responses]

            # Рекомендованные каналы
            matching_channels = OfferMatchingService.find_matching_channels(offer.id, limit=10)

            offer_data['recommended_channels'] = [{
                'id': match['channel'].id,
                'channel_name': match['channel'].channel_name,
                'channel_username': match['channel'].channel_username,
                'subscribers_count': match['channel'].subscribers_count,
                'price_per_post': match['channel'].price_per_post,
                'category': match['channel'].category,
                'match_score': match['match_score']
            } for match in matching_channels]

        return jsonify(offer_data)

    except Exception as e:
        current_app.logger.error(f"Error getting offer {offer_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=10, window=3600)  # 10 офферов в час
def create_offer():
    """
    Создание нового оффера

    Expected JSON:
    {
        "title": "Заголовок оффера",
        "description": "Описание рекламного размещения",
        "budget": 5000.0,
        "category": "technology",
        "end_date": "2024-12-31T23:59:59Z",
        "target_audience": {
            "min_subscribers": 1000,
            "max_price": 100,
            "categories": ["technology", "business"]
        }
    }

    Returns:
        JSON с информацией о созданном оффере
    """
    try:
        from ..models.offer import Offer
        from ..models.user import User
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400

        # Валидация данных
        validation_errors = OfferValidator.validate_offer_data(data)
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'details': validation_errors
            }), 400

        # Проверяем лимит офферов для пользователя
        user = User.query.get(g.current_user_id)
        user_offers_count = Offer.query.filter_by(advertiser_id=user.id).count()

        if user_offers_count >= MAX_OFFERS_PER_USER:
            return jsonify({
                'error': f'Maximum {MAX_OFFERS_PER_USER} offers per user'
            }), 400

        # Парсим дату окончания
        end_date = None
        if data.get('end_date'):
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'error': 'Invalid end_date format'
                }), 400

        # Создаем оффер
        offer = Offer(
            title=data['title'],
            description=data['description'],
            budget=float(data['budget']),
            category=data.get('category', 'other'),
            end_date=end_date,
            target_audience=data.get('target_audience', {}),
            advertiser_id=user.id,
            status='active'
        )

        db.session.add(offer)
        db.session.commit()

        current_app.logger.info(
            f"Offer created: {offer.id} by user {user.telegram_id}"
        )

        # Ищем подходящие каналы
        matching_channels = OfferMatchingService.find_matching_channels(offer.id, limit=5)

        return jsonify({
            'success': True,
            'message': 'Offer created successfully',
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'end_date': offer.end_date.isoformat() if offer.end_date else None,
                'target_audience': offer.target_audience,
                'created_at': offer.created_at.isoformat() if offer.created_at else None
            },
            'matching_channels_count': len(matching_channels),
            'recommended_channels': [{
                'id': match['channel'].id,
                'channel_name': match['channel'].channel_name,
                'match_score': match['match_score']
            } for match in matching_channels[:3]]  # Топ 3 рекомендации
        }), 201

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating offer: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=3600)  # 20 обновлений в час
def update_offer(offer_id):
    """
    Обновление оффера

    Args:
        offer_id: ID оффера

    Expected JSON:
    {
        "title": "Новый заголовок",
        "description": "Новое описание",
        "budget": 7000.0,
        "category": "business",
        "status": "paused",
        "target_audience": {...}
    }

    Returns:
        JSON с обновленной информацией об оффере
    """
    try:
        from ..models.offer import Offer
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400

        # Находим оффер
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({
                'error': 'Offer not found or access denied'
            }), 404

        # Проверяем, можно ли редактировать оффер
        if offer.status == 'completed':
            return jsonify({
                'error': 'Cannot edit completed offer'
            }), 400

        # Валидация данных
        validation_errors = OfferValidator.validate_offer_data(data)
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'details': validation_errors
            }), 400

        # Обновляем разрешенные поля
        updated_fields = []

        if 'title' in data:
            offer.title = data['title']
            updated_fields.append('title')

        if 'description' in data:
            offer.description = data['description']
            updated_fields.append('description')

        if 'budget' in data:
            offer.budget = float(data['budget'])
            updated_fields.append('budget')

        if 'category' in data:
            offer.category = data['category']
            updated_fields.append('category')

        if 'status' in data:
            valid_statuses = ['active', 'paused', 'completed']
            if data['status'] in valid_statuses:
                offer.status = data['status']
                updated_fields.append('status')

        if 'end_date' in data:
            if data['end_date']:
                try:
                    offer.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
                    updated_fields.append('end_date')
                except ValueError:
                    return jsonify({
                        'error': 'Invalid end_date format'
                    }), 400
            else:
                offer.end_date = None
                updated_fields.append('end_date')

        if 'target_audience' in data:
            offer.target_audience = data['target_audience']
            updated_fields.append('target_audience')

        if updated_fields:
            db.session.commit()

            current_app.logger.info(
                f"Offer {offer_id} updated fields: {', '.join(updated_fields)} "
                f"by user {g.telegram_user_id}"
            )

        return jsonify({
            'success': True,
            'message': f'Offer updated: {", ".join(updated_fields)}' if updated_fields else 'No changes made',
            'updated_fields': updated_fields,
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'end_date': offer.end_date.isoformat() if offer.end_date else None,
                'target_audience': offer.target_audience
            }
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error updating offer {offer_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>', methods=['DELETE'])
@require_telegram_auth
@rate_limit_decorator(max_requests=10, window=3600)  # 10 удалений в час
def delete_offer(offer_id):
    """
    Удаление оффера

    Args:
        offer_id: ID оффера

    Returns:
        JSON с результатом удаления
    """
    try:
        from ..models.offer import Offer
        from ..models.response import Response
        from ..models.database import db

        # Находим оффер
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({
                'error': 'Offer not found or access denied'
            }), 404

        # Проверяем активные отклики
        accepted_responses = Response.query.filter_by(
            offer_id=offer_id,
            status='accepted'
        ).count()

        if accepted_responses > 0:
            return jsonify({
                'error': 'Cannot delete offer with accepted responses',
                'accepted_responses_count': accepted_responses,
                'message': 'Please complete all accepted placements before deleting the offer'
            }), 400

        # Удаляем связанные отклики
        Response.query.filter_by(offer_id=offer_id).delete()

        # Удаляем оффер
        offer_title = offer.title
        db.session.delete(offer)
        db.session.commit()

        current_app.logger.info(
            f"Offer {offer_id} ({offer_title}) deleted by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Offer "{offer_title}" deleted successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting offer {offer_id}: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>/responses', methods=['GET'])
@require_telegram_auth
def get_offer_responses(offer_id):
    """
    Получение откликов на оффер

    Args:
        offer_id: ID оффера

    Query params:
    - status: фильтр по статусу (pending, accepted, rejected)
    - page: номер страницы
    - limit: количество на странице

    Returns:
        JSON со списком откликов на оффер
    """
    try:
        from ..models.offer import Offer
        from ..models.response import Response
        from ..models.channels import Channel
        from ..models.user import User

        # Проверяем доступ к офферу
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({
                'error': 'Offer not found or access denied'
            }), 404

        # Параметры пагинации
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фильтры
        status_filter = request.args.get('status')

        # Базовый запрос
        query = Response.query.filter_by(offer_id=offer_id).join(
            Channel, Response.channel_id == Channel.id
        ).join(
            User, Channel.owner_id == User.id
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
                'channel': {
                    'id': response.channel.id,
                    'channel_name': response.channel.channel_name,
                    'channel_username': response.channel.channel_username,
                    'subscribers_count': response.channel.subscribers_count,
                    'price_per_post': response.channel.price_per_post,
                    'category': response.channel.category,
                    'is_verified': response.channel.is_verified
                },
                'channel_owner': {
                    'id': response.channel.owner.id,
                    'username': response.channel.owner.username,
                    'first_name': response.channel.owner.first_name
                }
            })

        return jsonify({
            'responses': responses_data,
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'budget': offer.budget
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
        current_app.logger.error(f"Error getting offer responses: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>/responses/<int:response_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=30, window=300)  # 30 действий за 5 минут
def update_offer_response_status(offer_id, response_id):
    """
    Обновление статуса отклика на оффер

    Args:
        offer_id: ID оффера
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
        from ..models.offer import Offer
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

        # Проверяем доступ к офферу
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({
                'error': 'Offer not found or access denied'
            }), 404

        # Находим отклик
        response = Response.query.filter_by(
            id=response_id,
            offer_id=offer_id
        ).first()

        if not response:
            return jsonify({
                'error': 'Response not found'
            }), 404

        if response.status != 'pending':
            return jsonify({
                'error': f'Response already {response.status}'
            }), 400

        # Проверяем бюджет при принятии отклика
        if new_status == 'accepted':
            channel_price = response.channel.price_per_post
            if channel_price > offer.budget:
                return jsonify({
                    'error': 'Insufficient budget for this channel',
                    'required': channel_price,
                    'available': offer.budget
                }), 400

        # Обновляем статус
        response.status = new_status
        if 'message' in data:
            response.message = data['message']

        db.session.commit()

        current_app.logger.info(
            f"Offer response {response_id} status updated to {new_status} by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Response {new_status} successfully',
            'response': {
                'id': response.id,
                'status': response.status,
                'message': response.message,
                'channel_name': response.channel.channel_name,
                'updated_at': time.time()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error updating offer response status: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/<int:offer_id>/matching-channels', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_matching_channels(offer_id):
    """
    Получение каналов, подходящих для оффера

    Args:
        offer_id: ID оффера

    Query params:
    - limit: количество каналов (по умолчанию 20, макс 50)

    Returns:
        JSON со списком подходящих каналов
    """
    try:
        from ..models.offer import Offer

        # Проверяем доступ к офферу
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({
                'error': 'Offer not found or access denied'
            }), 404

        limit = min(int(request.args.get('limit', 20)), 50)

        # Находим подходящие каналы
        matching_channels = OfferMatchingService.find_matching_channels(offer_id, limit)

        # Формируем ответ
        channels_data = []
        for match in matching_channels:
            channel = match['channel']
            channels_data.append({
                'id': channel.id,
                'channel_name': channel.channel_name,
                'channel_username': channel.channel_username,
                'subscribers_count': channel.subscribers_count,
                'price_per_post': channel.price_per_post,
                'category': channel.category,
                'is_verified': channel.is_verified,
                'match_score': match['match_score'],
                'match_reasons': [
                    f"Category match: {channel.category}" if offer.category == channel.category else None,
                    f"Budget compatible: {channel.price_per_post} ≤ {offer.budget}" if channel.price_per_post <= offer.budget else None,
                    f"Verified channel" if channel.is_verified else None,
                    f"Large audience: {channel.subscribers_count:,} subscribers" if channel.subscribers_count > 10000 else None
                ],
                'owner': {
                    'username': channel.owner.username,
                    'first_name': channel.owner.first_name
                }
            })

            # Очищаем None значения из match_reasons
            channels_data[-1]['match_reasons'] = [
                reason for reason in channels_data[-1]['match_reasons'] if reason
            ]

        return jsonify({
            'matching_channels': channels_data,
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'budget': offer.budget,
                'category': offer.category
            },
            'total_found': len(matching_channels),
            'search_criteria': offer.target_audience or {}
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting matching channels: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/my', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=60)  # Кэшируем на 1 минуту
def get_my_offers():
    """
    Получение офферов текущего пользователя

    Returns:
        JSON со списком офферов пользователя
    """
    try:
        from ..models.offer import Offer
        from ..models.response import Response
        from ..models.database import db
        from sqlalchemy import func

        # Получаем офферы пользователя
        offers = Offer.query.filter_by(advertiser_id=g.current_user_id).order_by(
            desc(Offer.created_at)
        ).all()

        offers_data = []
        for offer in offers:
            # Статистика откликов для каждого оффера
            responses_stats = db.session.query(
                Response.status,
                func.count(Response.id).label('count')
            ).filter_by(offer_id=offer.id).group_by(Response.status).all()

            stats = {status: count for status, count in responses_stats}

            offers_data.append({
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'created_at': offer.created_at.isoformat() if offer.created_at else None,
                'end_date': offer.end_date.isoformat() if offer.end_date else None,
                'target_audience': offer.target_audience,
                'statistics': {
                    'total_responses': sum(stats.values()),
                    'pending_responses': stats.get('pending', 0),
                    'accepted_responses': stats.get('accepted', 0),
                    'rejected_responses': stats.get('rejected', 0)
                }
            })

        # Общая статистика
        total_budget = sum(offer['budget'] for offer in offers_data)
        active_offers = sum(1 for offer in offers_data if offer['status'] == 'active')
        total_responses = sum(offer['statistics']['total_responses'] for offer in offers_data)

        return jsonify({
            'offers': offers_data,
            'summary': {
                'total_offers': len(offers_data),
                'active_offers': active_offers,
                'total_budget': total_budget,
                'total_responses': total_responses,
                'average_budget': total_budget / len(offers_data) if offers_data else 0
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting user offers: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


@offer_bp.route('/stats', methods=['GET'])
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_offers_stats():
    """
    Получение общей статистики по офферам

    Returns:
        JSON с общей статистикой
    """
    try:
        from ..models.offer import Offer
        from ..models.database import db
        from sqlalchemy import func

        # Общая статистика
        total_offers = Offer.query.count()
        active_offers = Offer.query.filter_by(status='active').count()

        # Статистика по бюджетам
        budget_stats = db.session.query(
            func.sum(Offer.budget).label('total_budget'),
            func.avg(Offer.budget).label('avg_budget'),
            func.min(Offer.budget).label('min_budget'),
            func.max(Offer.budget).label('max_budget')
        ).filter(Offer.status.in_(['active', 'paused'])).first()

        # Топ категории
        top_categories = db.session.query(
            Offer.category,
            func.count(Offer.id).label('count'),
            func.avg(Offer.budget).label('avg_budget')
        ).filter(
            Offer.status == 'active'
        ).group_by(Offer.category).order_by(
            desc(func.count(Offer.id))
        ).limit(5).all()

        # Статистика по датам (последние 30 дней)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_offers = Offer.query.filter(
            Offer.created_at >= thirty_days_ago
        ).count()

        return jsonify({
            'offers': {
                'total': total_offers,
                'active': active_offers,
                'recent_30_days': recent_offers
            },
            'budgets': {
                'total': float(budget_stats.total_budget or 0),
                'average': round(float(budget_stats.avg_budget or 0), 2),
                'minimum': float(budget_stats.min_budget or 0),
                'maximum': float(budget_stats.max_budget or 0)
            },
            'top_categories': [
                {
                    'category': cat.category,
                    'count': cat.count,
                    'avg_budget': round(float(cat.avg_budget), 2)
                } for cat in top_categories
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting offers stats: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


# === ОБРАБОТЧИКИ ОШИБОК ===

@offer_bp.errorhandler(404)
def offer_not_found(error):
    """Обработчик 404 ошибок для офферов"""
    return jsonify({
        'error': 'Offer endpoint not found',
        'message': 'The requested offer endpoint does not exist'
    }), 404


@offer_bp.errorhandler(403)
def offer_access_denied(error):
    """Обработчик 403 ошибок для офферов"""
    return jsonify({
        'error': 'Access denied',
        'message': 'You do not have permission to access this offer'
    }), 403


# Инициализация Blueprint
def init_offer_routes():
    """Инициализация маршрутов офферов"""
    current_app.logger.info("✅ Offer routes initialized")


# Экспорт
__all__ = ['offer_bp', 'init_offer_routes', 'OfferValidator', 'OfferMatchingService']