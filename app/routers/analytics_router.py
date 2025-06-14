"""
Маршрутизатор аналитики для Telegram Mini App

Содержит все API эндпоинты для аналитики и статистики:
- Дашборды пользователей
- Детальная аналитика каналов и офферов
- Графики и метрики
- Отчеты и экспорт данных
"""

import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import and_, or_, desc, func, extract
from .middleware import (
    require_telegram_auth,
    cache_response,
    rate_limit_decorator
)
from ..models.channels import Channel

# Создание Blueprint для аналитики
analytics_bp = Blueprint('analytics', __name__)


class AnalyticsService:
    """Сервис для расчета аналитических данных"""

    @staticmethod
    def get_date_range(period='30d'):
        """Получение диапазона дат для анализа"""
        end_date = datetime.utcnow()

        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # custom period
            try:
                days = int(period.rstrip('d'))
                start_date = end_date - timedelta(days=days)
            except:
                start_date = end_date - timedelta(days=30)

        return start_date, end_date

    @staticmethod
    def calculate_growth_rate(current_value, previous_value):
        """Расчет темпа роста"""
        if previous_value == 0:
            return 100.0 if current_value > 0 else 0.0

        growth_rate = ((current_value - previous_value) / previous_value) * 100
        return round(growth_rate, 2)

    @staticmethod
    def get_time_series_data(query, date_field, period='30d', group_by='day'):
        """Получение данных временных рядов"""
        start_date, end_date = AnalyticsService.get_date_range(period)

        # Фильтруем по периоду
        query = query.filter(date_field >= start_date, date_field <= end_date)

        # Группируем по временным интервалам
        if group_by == 'day':
            time_unit = func.date(date_field)
        elif group_by == 'week':
            time_unit = func.date_trunc('week', date_field)
        elif group_by == 'month':
            time_unit = func.date_trunc('month', date_field)
        else:
            time_unit = func.date(date_field)

        results = query.with_entities(
            time_unit.label('date'),
            func.count().label('count')
        ).group_by(time_unit).order_by(time_unit).all()

        return [
            {
                'date': result.date.isoformat() if hasattr(result.date, 'isoformat') else str(result.date),
                'count': result.count
            } for result in results
        ]

# === ДАШБОРДЫ ===

@analytics_bp.route('/dashboard', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_dashboard():
    """
    Основной дашборд пользователя

    Query params:
    - period: период анализа (7d, 30d, 90d, 1y)

    Returns:
        JSON с данными дашборда
    """
    try:
        from ..models.user import User
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.response import Response

        period = request.args.get('period', '30d')
        start_date, end_date = AnalyticsService.get_date_range(period)

        user = User.query.get(g.current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        dashboard_data = {
            'user_type': user.user_type,
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

        if user.user_type == 'channel_owner':
            dashboard_data.update(AnalyticsService.get_channel_owner_dashboard(
                user.id, start_date, end_date
            ))
        elif user.user_type == 'advertiser':
            dashboard_data.update(AnalyticsService.get_advertiser_dashboard(
                user.id, start_date, end_date
            ))

        return jsonify(dashboard_data)

    except Exception as e:
        current_app.logger.error(f"Error getting dashboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500

    @staticmethod
    def get_channel_owner_dashboard(user_id, start_date, end_date):
        """Дашборд для владельца каналов"""
        from ..models import channels
        from ..models import response
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()
        # Основные метрики
        total_channels = Channel.query.filter_by(owner_id=user_id).count()
        verified_channels = Channel.query.filter_by(
            owner_id=user_id,
            is_verified=True
        ).count()

        # Общее количество подписчиков
        total_subscribers = db.session.query(
            func.sum(Channel.subscribers_count)
        ).filter_by(owner_id=user_id).scalar() or 0

        # Отклики за период
        period_responses = Response.query.join(Channel).filter(
            Channel.owner_id == user_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).count()

        # Предыдущий период для сравнения
        prev_start = start_date - (end_date - start_date)
        prev_responses = Response.query.join(Channel).filter(
            Channel.owner_id == user_id,
            Response.created_at >= prev_start,
            Response.created_at < start_date
        ).count()

        # Принятые отклики за период
        accepted_responses = Response.query.join(Channel).filter(
            Channel.owner_id == user_id,
            Response.status == 'accepted',
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).count()

        # Потенциальный доход
        potential_revenue = db.session.query(
            func.sum(Channel.price_per_post)
        ).join(Response).filter(
            Channel.owner_id == user_id,
            Response.status == 'accepted',
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).scalar() or 0

        # Статистика по каналам
        channels_stats = db.session.query(
            Channel.id,
            Channel.channel_name,
            Channel.subscribers_count,
            Channel.price_per_post,
            func.count(Response.id).label('responses_count')
        ).outerjoin(Response).filter(
            Channel.owner_id == user_id
        ).group_by(Channel.id).order_by(
            desc(func.count(Response.id))
        ).limit(5).all()

        # Временные ряды откликов
        responses_timeline = AnalyticsService.get_time_series_data(
            Response.query.join(Channel).filter(Channel.owner_id == user_id),
            Response.created_at,
            period='30d'
        )

        return {
            'metrics': {
                'total_channels': total_channels,
                'verified_channels': verified_channels,
                'total_subscribers': int(total_subscribers),
                'period_responses': period_responses,
                'accepted_responses': accepted_responses,
                'potential_revenue': float(potential_revenue),
                'response_growth': AnalyticsService.calculate_growth_rate(
                    period_responses, prev_responses
                )
            },
            'top_channels': [
                {
                    'id': stat.id,
                    'name': stat.channel_name,
                    'subscribers': stat.subscribers_count,
                    'price': stat.price_per_post,
                    'responses': stat.responses_count
                } for stat in channels_stats
            ],
            'charts': {
                'responses_timeline': responses_timeline
            }
        }

    @staticmethod
    def get_advertiser_dashboard(user_id, start_date, end_date):
        """Дашборд для рекламодателя"""
        from ..models.offer import Offer
        from ..models.response import Response
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        # Основные метрики
        total_offers = Offer.query.filter_by(advertiser_id=user_id).count()
        active_offers = Offer.query.filter_by(
            advertiser_id=user_id,
            status='active'
        ).count()

        # Общий бюджет
        total_budget = db.session.query(
            func.sum(Offer.budget)
        ).filter_by(advertiser_id=user_id).scalar() or 0

        # Отклики за период
        period_responses = Response.query.join(Offer).filter(
            Offer.advertiser_id == user_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).count()

        # Предыдущий период
        prev_start = start_date - (end_date - start_date)
        prev_responses = Response.query.join(Offer).filter(
            Offer.advertiser_id == user_id,
            Response.created_at >= prev_start,
            Response.created_at < start_date
        ).count()

        # Принятые размещения
        accepted_placements = Response.query.join(Offer).filter(
            Offer.advertiser_id == user_id,
            Response.status == 'accepted',
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).count()

        # Потраченный бюджет (примерный расчет)
        spent_budget = db.session.query(
            func.sum(Channel.price_per_post)
        ).join(Response).join(Offer).filter(
            Offer.advertiser_id == user_id,
            Response.status == 'accepted',
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).scalar() or 0

        # Статистика по офферам
        offers_stats = db.session.query(
            Offer.id,
            Offer.title,
            Offer.budget,
            Offer.status,
            func.count(Response.id).label('responses_count')
        ).outerjoin(Response).filter(
            Offer.advertiser_id == user_id
        ).group_by(Offer.id).order_by(
            desc(func.count(Response.id))
        ).limit(5).all()

        # Временные ряды откликов
        responses_timeline = AnalyticsService.get_time_series_data(
            Response.query.join(Offer).filter(Offer.advertiser_id == user_id),
            Response.created_at,
            period='30d'
        )

        return {
            'metrics': {
                'total_offers': total_offers,
                'active_offers': active_offers,
                'total_budget': float(total_budget),
                'period_responses': period_responses,
                'accepted_placements': accepted_placements,
                'spent_budget': float(spent_budget),
                'response_growth': AnalyticsService.calculate_growth_rate(
                    period_responses, prev_responses
                )
            },
            'top_offers': [
                {
                    'id': stat.id,
                    'title': stat.title,
                    'budget': stat.budget,
                    'status': stat.status,
                    'responses': stat.responses_count
                } for stat in offers_stats
            ],
            'charts': {
                'responses_timeline': responses_timeline
            }
        }

# Добавляем методы в класс AnalyticsService
AnalyticsService.get_channel_owner_dashboard = staticmethod(AnalyticsService.get_channel_owner_dashboard)
AnalyticsService.get_advertiser_dashboard = staticmethod(AnalyticsService.get_advertiser_dashboard)

@analytics_bp.route('/channels/<int:channel_id>', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=180)  # Кэшируем на 3 минуты
def get_channel_analytics(channel_id):
    """
    Детальная аналитика канала

    Args:
        channel_id: ID канала

    Query params:
    - period: период анализа (7d, 30d, 90d, 1y)

    Returns:
        JSON с аналитикой канала
    """
    try:
        from ..models.channels import Channel
        from ..models.response import Response
        from ..models.offer import Offer
        from ..models.database import db

        # Проверяем доступ к каналу
        channel = Channel.query.filter_by(
            id=channel_id,
            owner_id=g.current_user_id
        ).first()

        if not channel:
            return jsonify({'error': 'Channel not found or access denied'}), 404

        period = request.args.get('period', '30d')
        start_date, end_date = AnalyticsService.get_date_range(period)

        # Основные метрики канала
        total_responses = Response.query.filter_by(channel_id=channel_id).count()

        period_responses = Response.query.filter(
            Response.channel_id == channel_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).count()

        # Статистика по статусам
        status_stats = db.session.query(
            Response.status,
            func.count(Response.id).label('count')
        ).filter(
            Response.channel_id == channel_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).group_by(Response.status).all()

        status_breakdown = {status: count for status, count in status_stats}

        # Потенциальный доход
        potential_revenue = period_responses * channel.price_per_post

        # Реальный доход (принятые отклики)
        actual_revenue = status_breakdown.get('accepted', 0) * channel.price_per_post

        # Топ офферы по откликам
        top_offers = db.session.query(
            Offer.id,
            Offer.title,
            Offer.budget,
            Offer.category,
            Response.status,
            Response.created_at
        ).join(Response).filter(
            Response.channel_id == channel_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).order_by(desc(Response.created_at)).limit(10).all()

        # Временные ряды откликов
        responses_timeline = AnalyticsService.get_time_series_data(
            Response.query.filter(Response.channel_id == channel_id),
            Response.created_at,
            period
        )

        # Статистика по категориям
        category_stats = db.session.query(
            Offer.category,
            func.count(Response.id).label('count')
        ).join(Response).filter(
            Response.channel_id == channel_id,
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).group_by(Offer.category).order_by(
            desc(func.count(Response.id))
        ).all()

        return jsonify({
            'channel': {
                'id': channel.id,
                'name': channel.channel_name,
                'username': channel.channel_username,
                'subscribers': channel.subscribers_count,
                'price_per_post': channel.price_per_post,
                'category': channel.category,
                'is_verified': channel.is_verified
            },
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'name': period
            },
            'metrics': {
                'total_responses': total_responses,
                'period_responses': period_responses,
                'acceptance_rate': (status_breakdown.get('accepted', 0) / period_responses * 100) if period_responses > 0 else 0,
                'potential_revenue': potential_revenue,
                'actual_revenue': actual_revenue,
                'revenue_rate': (actual_revenue / potential_revenue * 100) if potential_revenue > 0 else 0
            },
            'status_breakdown': status_breakdown,
            'top_offers': [
                {
                    'id': offer.id,
                    'title': offer.title,
                    'budget': offer.budget,
                    'category': offer.category,
                    'status': offer.status,
                    'date': offer.created_at.isoformat()
                } for offer in top_offers
            ],
            'category_stats': [
                {
                    'category': stat.category,
                    'responses': stat.count
                } for stat in category_stats
            ],
            'charts': {
                'responses_timeline': responses_timeline
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting channel analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/offers/<int:offer_id>', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=180)  # Кэшируем на 3 минуты
def get_offer_analytics(offer_id):
    """
    Детальная аналитика оффера

    Args:
        offer_id: ID оффера

    Returns:
        JSON с аналитикой оффера
    """
    try:
        from ..models.offer import Offer
        from ..models.response import Response
        from ..models.channels import Channel
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        # Проверяем доступ к офферу
        offer = Offer.query.filter_by(
            id=offer_id,
            advertiser_id=g.current_user_id
        ).first()

        if not offer:
            return jsonify({'error': 'Offer not found or access denied'}), 404

        # Основные метрики
        total_responses = Response.query.filter_by(offer_id=offer_id).count()

        # Статистика по статусам
        status_stats = db.session.query(
            Response.status,
            func.count(Response.id).label('count')
        ).filter_by(offer_id=offer_id).group_by(Response.status).all()

        status_breakdown = {status: count for status, count in status_stats}

        # Анализ откликнувшихся каналов
        channels_analysis = db.session.query(
            Channel.id,
            Channel.channel_name,
            Channel.subscribers_count,
            Channel.price_per_post,
            Channel.category,
            Response.status,
            Response.created_at
        ).join(Response).filter(
            Response.offer_id == offer_id
        ).order_by(desc(Channel.subscribers_count)).all()

        # Общий охват аудитории
        total_reach = sum(channel.subscribers_count for channel in channels_analysis)

        # Потенциальная стоимость размещений
        potential_cost = sum(
            channel.price_per_post for channel in channels_analysis
            if channel.status == 'accepted'
        )

        # Анализ по категориям каналов
        category_analysis = db.session.query(
            Channel.category,
            func.count(Response.id).label('responses'),
            func.sum(Channel.subscribers_count).label('total_reach'),
            func.avg(Channel.price_per_post).label('avg_price')
        ).join(Response).filter(
            Response.offer_id == offer_id
        ).group_by(Channel.category).all()

        # Временная линия откликов
        responses_timeline = AnalyticsService.get_time_series_data(
            Response.query.filter(Response.offer_id == offer_id),
            Response.created_at,
            period='30d'
        )

        # Конверсия по дням с момента создания
        days_since_creation = (datetime.utcnow() - offer.created_at).days if offer.created_at else 0

        return jsonify({
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'created_at': offer.created_at.isoformat() if offer.created_at else None,
                'end_date': offer.end_date.isoformat() if offer.end_date else None,
                'days_active': days_since_creation
            },
            'metrics': {
                'total_responses': total_responses,
                'acceptance_rate': (status_breakdown.get('accepted', 0) / total_responses * 100) if total_responses > 0 else 0,
                'total_reach': total_reach,
                'potential_cost': potential_cost,
                'cost_per_response': (potential_cost / status_breakdown.get('accepted', 1)) if status_breakdown.get('accepted', 0) > 0 else 0,
                'budget_utilization': (potential_cost / offer.budget * 100) if offer.budget > 0 else 0
            },
            'status_breakdown': status_breakdown,
            'responding_channels': [
                {
                    'id': channel.id,
                    'name': channel.channel_name,
                    'subscribers': channel.subscribers_count,
                    'price': channel.price_per_post,
                    'category': channel.category,
                    'status': channel.status,
                    'response_date': channel.created_at.isoformat()
                } for channel in channels_analysis
            ],
            'category_analysis': [
                {
                    'category': cat.category,
                    'responses': cat.responses,
                    'total_reach': int(cat.total_reach or 0),
                    'avg_price': round(float(cat.avg_price or 0), 2)
                } for cat in category_analysis
            ],
            'charts': {
                'responses_timeline': responses_timeline
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting offer analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/market-insights', methods=['GET'])
@cache_response(timeout=600)  # Кэшируем на 10 минут
def get_market_insights():
    """
    Аналитика рынка и инсайты

    Returns:
        JSON с аналитикой рынка
    """
    try:
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.response import Response
        from ..models.user import User
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        # Общая статистика платформы
        total_users = User.query.count()
        total_channels = Channel.query.filter_by(is_verified=True).count()
        total_offers = Offer.query.filter_by(status='active').count()
        total_responses = Response.query.count()

        # Средние цены по категориям
        category_prices = db.session.query(
            Channel.category,
            func.avg(Channel.price_per_post).label('avg_price'),
            func.count(Channel.id).label('channels_count'),
            func.avg(Channel.subscribers_count).label('avg_subscribers')
        ).filter(
            Channel.is_verified == True,
            Channel.price_per_post > 0
        ).group_by(Channel.category).order_by(desc('avg_price')).all()

        # Топ категории по активности
        top_categories = db.session.query(
            Offer.category,
            func.count(Offer.id).label('offers_count'),
            func.avg(Offer.budget).label('avg_budget'),
            func.count(Response.id).label('responses_count')
        ).outerjoin(Response).filter(
            Offer.status == 'active'
        ).group_by(Offer.category).order_by(desc('offers_count')).limit(10).all()

        # Статистика по размерам каналов
        channel_size_distribution = db.session.query(
            func.case(
                (Channel.subscribers_count < 1000, 'micro'),
                (Channel.subscribers_count < 10000, 'small'),
                (Channel.subscribers_count < 100000, 'medium'),
                (Channel.subscribers_count >= 100000, 'large')
            ).label('size_category'),
            func.count(Channel.id).label('count'),
            func.avg(Channel.price_per_post).label('avg_price')
        ).filter(Channel.is_verified == True).group_by('size_category').all()

        # Тренды последних 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        daily_activity = db.session.query(
            func.date(Response.created_at).label('date'),
            func.count(Response.id).label('responses'),
            func.count(func.distinct(Response.offer_id)).label('active_offers'),
            func.count(func.distinct(Response.channel_id)).label('active_channels')
        ).filter(
            Response.created_at >= thirty_days_ago
        ).group_by(func.date(Response.created_at)).order_by('date').all()

        # Коэффициент принятия по категориям
        acceptance_rates = db.session.query(
            Channel.category,
            func.count(Response.id).label('total_responses'),
            func.sum(func.case((Response.status == 'accepted', 1), else_=0)).label('accepted_responses')
        ).join(Response).group_by(Channel.category).all()

        acceptance_stats = []
        for stat in acceptance_rates:
            rate = (stat.accepted_responses / stat.total_responses * 100) if stat.total_responses > 0 else 0
            acceptance_stats.append({
                'category': stat.category,
                'acceptance_rate': round(rate, 2),
                'total_responses': stat.total_responses
            })

        return jsonify({
            'platform_stats': {
                'total_users': total_users,
                'total_channels': total_channels,
                'active_offers': total_offers,
                'total_responses': total_responses
            },
            'category_pricing': [
                {
                    'category': cat.category,
                    'avg_price': round(float(cat.avg_price), 2),
                    'channels_count': cat.channels_count,
                    'avg_subscribers': int(cat.avg_subscribers or 0)
                } for cat in category_prices
            ],
            'top_categories': [
                {
                    'category': cat.category,
                    'offers_count': cat.offers_count,
                    'avg_budget': round(float(cat.avg_budget or 0), 2),
                    'responses_count': cat.responses_count or 0
                } for cat in top_categories
            ],
            'channel_size_distribution': [
                {
                    'size_category': dist.size_category,
                    'count': dist.count,
                    'avg_price': round(float(dist.avg_price or 0), 2)
                } for dist in channel_size_distribution
            ],
            'acceptance_rates': sorted(acceptance_stats, key=lambda x: x['acceptance_rate'], reverse=True),
            'activity_timeline': [
                {
                    'date': activity.date.isoformat(),
                    'responses': activity.responses,
                    'active_offers': activity.active_offers,
                    'active_channels': activity.active_channels
                } for activity in daily_activity
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting market insights: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/export', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=5, window=3600)  # 5 экспортов в час
def export_analytics():
    """
    Экспорт аналитических данных

    Expected JSON:
    {
        "type": "channels" | "offers" | "responses",
        "format": "csv" | "json",
        "period": "30d",
        "filters": {...}
    }

    Returns:
        JSON с ссылкой на файл экспорта
    """
    try:
        import csv
        import json
        import uuid
        import os

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        export_type = data.get('type', 'responses')
        export_format = data.get('format', 'json')
        period = data.get('period', '30d')
        filters = data.get('filters', {})

        if export_type not in ['channels', 'offers', 'responses']:
            return jsonify({'error': 'Invalid export type'}), 400

        if export_format not in ['csv', 'json']:
            return jsonify({'error': 'Invalid export format'}), 400

        # Получаем данные для экспорта
        start_date, end_date = AnalyticsService.get_date_range(period)

        if export_type == 'channels':
            export_data = AnalyticsService.export_channels_data(
                g.current_user_id, start_date, end_date, filters
            )
        elif export_type == 'offers':
            export_data = AnalyticsService.export_offers_data(
                g.current_user_id, start_date, end_date, filters
            )
        else:  # responses
            export_data = AnalyticsService.export_responses_data(
                g.current_user_id, start_date, end_date, filters
            )

        # Генерируем имя файла
        filename = f"{export_type}_{period}_{uuid.uuid4().hex[:8]}.{export_format}"

        # Создаем директорию для экспорта
        export_dir = os.path.join(current_app.root_path, 'static', 'exports')
        os.makedirs(export_dir, exist_ok=True)

        file_path = os.path.join(export_dir, filename)

        # Сохраняем файл
        if export_format == 'json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
        else:  # csv
            if export_data:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if isinstance(export_data[0], dict):
                        writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
                        writer.writeheader()
                        writer.writerows(export_data)

        # Генерируем URL для скачивания
        download_url = f"/static/exports/{filename}"

        current_app.logger.info(
            f"Analytics export created: {filename} by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': 'Export created successfully',
            'export': {
                'filename': filename,
                'download_url': download_url,
                'type': export_type,
                'format': export_format,
                'period': period,
                'records_count': len(export_data),
                'created_at': time.time()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error creating export: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Добавляем методы экспорта в AnalyticsService
class AnalyticsExportService:
    """Сервис для экспорта аналитических данных"""

    @staticmethod
    def export_channels_data(user_id, start_date, end_date, filters):
        """Экспорт данных каналов"""
        from ..models.channels import Channel
        from ..models.response import Response

        query = Channel.query.filter_by(owner_id=user_id)

        channels = query.all()
        export_data = []

        for channel in channels:
            # Статистика откликов за период
            responses_count = Response.query.filter(
                Response.channel_id == channel.id,
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            accepted_count = Response.query.filter(
                Response.channel_id == channel.id,
                Response.status == 'accepted',
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            export_data.append({
                'channel_id': channel.channel_id,
                'channel_name': channel.channel_name,
                'subscribers_count': channel.subscribers_count,
                'price_per_post': channel.price_per_post,
                'category': channel.category,
                'is_verified': channel.is_verified,
                'responses_count': responses_count,
                'accepted_count': accepted_count,
                'acceptance_rate': (accepted_count / responses_count * 100) if responses_count > 0 else 0,
                'potential_revenue': accepted_count * channel.price_per_post,
                'created_at': channel.created_at.isoformat() if channel.created_at else None
            })

        return export_data

    @staticmethod
    def export_offers_data(user_id, start_date, end_date, filters):
        """Экспорт данных офферов"""
        from ..models.offer import Offer
        from ..models.response import Response
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        query = Offer.query.filter_by(advertiser_id=user_id)

        offers = query.all()
        export_data = []

        for offer in offers:
            # Статистика откликов
            responses_count = Response.query.filter_by(offer_id=offer.id).count()
            accepted_count = Response.query.filter(
                Response.offer_id == offer.id,
                Response.status == 'accepted'
            ).count()

            # Потенциальная стоимость
            potential_cost = db.session.query(
                func.sum(Channel.price_per_post)
            ).join(Response).filter(
                Response.offer_id == offer.id,
                Response.status == 'accepted'
            ).scalar() or 0

            export_data.append({
                'offer_id': offer.id,
                'title': offer.title,
                'budget': offer.budget,
                'category': offer.category,
                'status': offer.status,
                'responses_count': responses_count,
                'accepted_count': accepted_count,
                'acceptance_rate': (accepted_count / responses_count * 100) if responses_count > 0 else 0,
                'potential_cost': potential_cost,
                'budget_utilization': (potential_cost / offer.budget * 100) if offer.budget > 0 else 0,
                'created_at': offer.created_at.isoformat() if offer.created_at else None,
                'end_date': offer.end_date.isoformat() if offer.end_date else None
            })

        return export_data

    @staticmethod
    def export_responses_data(user_id, start_date, end_date, filters):
        """Экспорт данных откликов"""
        from ..models.response import Response
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.user import User

        user = User.query.get(user_id)

        if user.user_type == 'channel_owner':
            # Отклики на каналы пользователя
            query = Response.query.join(Channel).filter(
                Channel.owner_id == user_id,
                Response.created_at >= start_date,
                Response.created_at <= end_date
            )
        else:
            # Отклики на офферы пользователя
            query = Response.query.join(Offer).filter(
                Offer.advertiser_id == user_id,
                Response.created_at >= start_date,
                Response.created_at <= end_date
            )

        responses = query.all()
        export_data = []

        for response in responses:
            export_data.append({
                'response_id': response.id,
                'status': response.status,
                'message': response.message,
                'channel_name': response.channel.channel_name,
                'channel_subscribers': response.channel.subscribers_count,
                'channel_price': response.channel.price_per_post,
                'offer_title': response.offer.title,
                'offer_budget': response.offer.budget,
                'offer_category': response.offer.category,
                'created_at': response.created_at.isoformat() if response.created_at else None
            })

        return export_data

# Добавляем методы в AnalyticsService
AnalyticsService.export_channels_data = AnalyticsExportService.export_channels_data
AnalyticsService.export_offers_data = AnalyticsExportService.export_offers_data
AnalyticsService.export_responses_data = AnalyticsExportService.export_responses_data

@analytics_bp.route('/reports/summary', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=900)  # Кэшируем на 15 минут
def get_summary_report():
    """
    Сводный отчет для пользователя

    Query params:
    - period: период анализа (7d, 30d, 90d, 1y)

    Returns:
        JSON со сводным отчетом
    """
    try:
        from ..models.user import User
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.response import Response
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        period = request.args.get('period', '30d')
        start_date, end_date = AnalyticsService.get_date_range(period)

        user = User.query.get(g.current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        report = {
            'user': {
                'id': user.id,
                'username': user.username,
                'user_type': user.user_type,
                'balance': user.balance
            },
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'name': period
            },
            'generated_at': datetime.utcnow().isoformat()
        }

        if user.user_type == 'channel_owner':
            # Отчет для владельца каналов
            channels = Channel.query.filter_by(owner_id=user.id).all()

            total_subscribers = sum(c.subscribers_count for c in channels)
            total_potential_revenue = sum(c.price_per_post for c in channels)

            # Статистика откликов
            period_responses = Response.query.join(Channel).filter(
                Channel.owner_id == user.id,
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            accepted_responses = Response.query.join(Channel).filter(
                Channel.owner_id == user.id,
                Response.status == 'accepted',
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            actual_revenue = accepted_responses * sum(c.price_per_post for c in channels) / len(channels) if channels else 0

            report['summary'] = {
                'total_channels': len(channels),
                'verified_channels': sum(1 for c in channels if c.is_verified),
                'total_subscribers': total_subscribers,
                'period_responses': period_responses,
                'accepted_responses': accepted_responses,
                'acceptance_rate': (accepted_responses / period_responses * 100) if period_responses > 0 else 0,
                'actual_revenue': actual_revenue,
                'revenue_per_channel': actual_revenue / len(channels) if channels else 0
            }

            # Топ каналы
            channels_with_stats = []
            for channel in channels:
                channel_responses = Response.query.filter(
                    Response.channel_id == channel.id,
                    Response.created_at >= start_date,
                    Response.created_at <= end_date
                ).count()

                channels_with_stats.append({
                    'name': channel.channel_name,
                    'subscribers': channel.subscribers_count,
                    'responses': channel_responses,
                    'revenue': Response.query.filter(
                        Response.channel_id == channel.id,
                        Response.status == 'accepted',
                        Response.created_at >= start_date,
                        Response.created_at <= end_date
                    ).count() * channel.price_per_post
                })

            report['top_performers'] = sorted(
                channels_with_stats,
                key=lambda x: x['revenue'],
                reverse=True
            )[:5]

        else:
            # Отчет для рекламодателя
            offers = Offer.query.filter_by(advertiser_id=user.id).all()

            total_budget = sum(o.budget for o in offers)
            active_offers = sum(1 for o in offers if o.status == 'active')

            # Статистика откликов
            period_responses = Response.query.join(Offer).filter(
                Offer.advertiser_id == user.id,
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            accepted_placements = Response.query.join(Offer).filter(
                Offer.advertiser_id == user.id,
                Response.status == 'accepted',
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).count()

            # Потраченный бюджет
            spent_budget = db.session.query(
                func.sum(Channel.price_per_post)
            ).join(Response).join(Offer).filter(
                Offer.advertiser_id == user.id,
                Response.status == 'accepted',
                Response.created_at >= start_date,
                Response.created_at <= end_date
            ).scalar() or 0

            report['summary'] = {
                'total_offers': len(offers),
                'active_offers': active_offers,
                'total_budget': total_budget,
                'spent_budget': spent_budget,
                'budget_utilization': (spent_budget / total_budget * 100) if total_budget > 0 else 0,
                'period_responses': period_responses,
                'accepted_placements': accepted_placements,
                'placement_rate': (accepted_placements / period_responses * 100) if period_responses > 0 else 0,
                'cost_per_placement': (spent_budget / accepted_placements) if accepted_placements > 0 else 0
            }

            # Топ офферы
            offers_with_stats = []
            for offer in offers:
                offer_responses = Response.query.filter_by(offer_id=offer.id).count()
                offer_accepted = Response.query.filter(
                    Response.offer_id == offer.id,
                    Response.status == 'accepted'
                ).count()

                offers_with_stats.append({
                    'title': offer.title,
                    'budget': offer.budget,
                    'responses': offer_responses,
                    'accepted': offer_accepted,
                    'success_rate': (offer_accepted / offer_responses * 100) if offer_responses > 0 else 0
                })

            report['top_performers'] = sorted(
                offers_with_stats,
                key=lambda x: x['success_rate'],
                reverse=True
            )[:5]

        # Рекомендации
        recommendations = AnalyticsService.generate_recommendations(user, report['summary'])
        report['recommendations'] = recommendations

        return jsonify(report)

    except Exception as e:
        current_app.logger.error(f"Error generating summary report: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/trends', methods=['GET'])
@cache_response(timeout=600)  # Кэшируем на 10 минут
def get_trends():
    """
    Анализ трендов и прогнозы

    Query params:
    - category: фильтр по категории
    - period: период анализа (30d, 90d, 1y)

    Returns:
        JSON с трендами и прогнозами
    """
    try:
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.response import Response
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()

        period = request.args.get('period', '90d')
        category = request.args.get('category')

        start_date, end_date = AnalyticsService.get_date_range(period)

        # Тренд активности по дням
        activity_trend = db.session.query(
            func.date(Response.created_at).label('date'),
            func.count(Response.id).label('responses'),
            func.count(func.distinct(Response.offer_id)).label('active_offers'),
            func.count(func.distinct(Response.channel_id)).label('active_channels')
        ).filter(
            Response.created_at >= start_date,
            Response.created_at <= end_date
        ).group_by(func.date(Response.created_at)).order_by('date').all()

        # Тренд цен по категориям
        price_trends = []
        categories = ['technology', 'business', 'entertainment', 'news', 'education', 'lifestyle', 'sports', 'gaming', 'other']

        for cat in categories:
            if category and cat != category:
                continue

            # Средние цены по неделям
            weekly_prices = db.session.query(
                func.date_trunc('week', Channel.created_at).label('week'),
                func.avg(Channel.price_per_post).label('avg_price'),
                func.count(Channel.id).label('channels_count')
            ).filter(
                Channel.category == cat,
                Channel.is_verified == True,
                Channel.price_per_post > 0,
                Channel.created_at >= start_date
            ).group_by(func.date_trunc('week', Channel.created_at)).order_by('week').all()

            if weekly_prices:
                price_trends.append({
                    'category': cat,
                    'data': [
                        {
                            'week': price.week.isoformat() if hasattr(price.week, 'isoformat') else str(price.week),
                            'avg_price': round(float(price.avg_price), 2),
                            'channels_count': price.channels_count
                        } for price in weekly_prices
                    ]
                })

        # Прогноз на основе линейной регрессии (упрощенный)
        if activity_trend:
            recent_activity = [day.responses for day in activity_trend[-14:]]  # Последние 14 дней
            if len(recent_activity) >= 7:
                avg_growth = (recent_activity[-1] - recent_activity[0]) / len(recent_activity)
                predicted_next_week = max(0, recent_activity[-1] + avg_growth * 7)

                forecast = {
                    'predicted_responses_next_week': int(predicted_next_week),
                    'trend_direction': 'up' if avg_growth > 0 else 'down' if avg_growth < 0 else 'stable',
                    'confidence': min(90, max(50, 70 + abs(avg_growth) * 10))  # Простой расчет уверенности
                }
            else:
                forecast = {'message': 'Insufficient data for forecasting'}
        else:
            forecast = {'message': 'No activity data available'}

        # Сезонные паттерны (по дням недели)
        weekday_patterns = db.session.query(
            extract('dow', Response.created_at).label('weekday'),
            func.count(Response.id).label('responses'),
            func.avg(func.count(Response.id)).over().label('avg_responses')
        ).filter(
            Response.created_at >= start_date
        ).group_by(extract('dow', Response.created_at)).order_by('weekday').all()

        weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        seasonal_data = [
            {
                'weekday': weekdays[int(pattern.weekday)],
                'responses': pattern.responses,
                'above_average': pattern.responses > pattern.avg_responses
            } for pattern in weekday_patterns
        ]

        return jsonify({
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'name': period
            },
            'activity_trend': [
                {
                    'date': day.date.isoformat(),
                    'responses': day.responses,
                    'active_offers': day.active_offers,
                    'active_channels': day.active_channels
                } for day in activity_trend
            ],
            'price_trends': price_trends,
            'forecast': forecast,
            'seasonal_patterns': seasonal_data,
            'insights': AnalyticsService.generate_trend_insights(activity_trend, price_trends)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting trends: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Добавляем методы генерации рекомендаций и инсайтов
class AnalyticsInsightsService:
    """Сервис для генерации инсайтов и рекомендаций"""

    @staticmethod
    def generate_recommendations(user, summary):
        """Генерация рекомендаций на основе данных"""
        recommendations = []

        if user.user_type == 'channel_owner':
            # Рекомендации для владельцев каналов
            if summary.get('acceptance_rate', 0) < 30:
                recommendations.append({
                    'type': 'improvement',
                    'title': 'Низкий процент принятия откликов',
                    'description': 'Рассмотрите пересмотр цен или улучшение описания каналов',
                    'priority': 'high'
                })

            if summary.get('verified_channels', 0) < summary.get('total_channels', 1):
                recommendations.append({
                    'type': 'action',
                    'title': 'Верифицируйте все каналы',
                    'description': 'Верифицированные каналы получают больше откликов',
                    'priority': 'medium'
                })

            if summary.get('period_responses', 0) == 0:
                recommendations.append({
                    'type': 'marketing',
                    'title': 'Нет откликов за период',
                    'description': 'Проверьте актуальность цен и категорий ваших каналов',
                    'priority': 'high'
                })

        else:
            # Рекомендации для рекламодателей
            if summary.get('budget_utilization', 0) < 50:
                recommendations.append({
                    'type': 'optimization',
                    'title': 'Низкое использование бюджета',
                    'description': 'Рассмотрите увеличение бюджета или расширение целевой аудитории',
                    'priority': 'medium'
                })

            if summary.get('placement_rate', 0) < 20:
                recommendations.append({
                    'type': 'improvement',
                    'title': 'Низкий процент размещений',
                    'description': 'Улучшите описание офферов или пересмотрите целевые параметры',
                    'priority': 'high'
                })

            if summary.get('cost_per_placement', 0) > summary.get('total_budget', 0) / 10:
                recommendations.append({
                    'type': 'cost',
                    'title': 'Высокая стоимость размещения',
                    'description': 'Ищите каналы с лучшим соотношением цена/качество',
                    'priority': 'medium'
                })

        return recommendations

    @staticmethod
    def generate_trend_insights(activity_trend, price_trends):
        """Генерация инсайтов на основе трендов"""
        insights = []

        if activity_trend and len(activity_trend) >= 7:
            # Анализ активности
            recent_week = activity_trend[-7:]
            prev_week = activity_trend[-14:-7] if len(activity_trend) >= 14 else []

            if prev_week:
                recent_avg = sum(day.responses for day in recent_week) / len(recent_week)
                prev_avg = sum(day.responses for day in prev_week) / len(prev_week)

                if recent_avg > prev_avg * 1.1:
                    insights.append({
                        'type': 'positive',
                        'title': 'Растущая активность',
                        'description': f'Активность выросла на {((recent_avg - prev_avg) / prev_avg * 100):.1f}% за последнюю неделю'
                    })
                elif recent_avg < prev_avg * 0.9:
                    insights.append({
                        'type': 'warning',
                        'title': 'Снижение активности',
                        'description': f'Активность снизилась на {((prev_avg - recent_avg) / prev_avg * 100):.1f}% за последнюю неделю'
                    })

        # Анализ ценовых трендов
        if price_trends:
            for trend in price_trends:
                if len(trend['data']) >= 4:
                    recent_prices = [float(week['avg_price']) for week in trend['data'][-4:]]
                    if len(recent_prices) >= 2:
                        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100

                        if abs(price_change) > 10:
                            insights.append({
                                'type': 'info',
                                'title': f'Изменение цен в категории {trend["category"]}',
                                'description': f'Цены {"выросли" if price_change > 0 else "снизились"} на {abs(price_change):.1f}% за последний месяц'
                            })

        return insights

# Добавляем методы в AnalyticsService
AnalyticsService.generate_recommendations = AnalyticsInsightsService.generate_recommendations
AnalyticsService.generate_trend_insights = AnalyticsInsightsService.generate_trend_insights

# === ОБРАБОТЧИКИ ОШИБОК ===

@analytics_bp.errorhandler(404)
def analytics_not_found(error):
    """Обработчик 404 ошибок для аналитики"""
    return jsonify({
        'error': 'Analytics endpoint not found',
        'message': 'The requested analytics endpoint does not exist'
    }), 404

@analytics_bp.errorhandler(403)
def analytics_access_denied(error):
    """Обработчик 403 ошибок для аналитики"""
    return jsonify({
        'error': 'Access denied',
        'message': 'You do not have permission to access this analytics data'
    }), 403

# Инициализация Blueprint
def init_analytics_routes():
    """Инициализация маршрутов аналитики"""
    current_app.logger.info("✅ Analytics routes initialized")

# Экспорт
__all__ = ['analytics_bp', 'init_analytics_routes', 'AnalyticsService']# app/routers/analytics_router.py
