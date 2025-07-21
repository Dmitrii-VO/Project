#!/usr/bin/env python3
"""
API для аналитики и статистики
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

# Создание Blueprint
analytics_bp = Blueprint('analytics', __name__)

# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================

def get_current_user_id():
    """Получение user_db_id текущего пользователя через auth_service"""
    try:
        from app.services.auth_service import auth_service
        return auth_service.get_user_db_id()
    except Exception as e:
        logger.error(f"Ошибка получения user_db_id: {e}")
        return None

def get_user_by_telegram_id(telegram_id: int):
    """Получение пользователя по telegram_id"""
    return execute_db_query(
        'SELECT * FROM users WHERE telegram_id = ?',
        (telegram_id,),
        fetch_one=True
    )

def get_user_metrics(user_id: int) -> dict:
    """Получение основных метрик пользователя"""
    try:
        # Статистика каналов
        channels_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_channels,
                COALESCE(SUM(subscriber_count), 0) as total_subscribers,
                COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_channels
            FROM channels 
            WHERE owner_id = ? AND is_active = 1
        """, (user_id,), fetch_one=True)
        
        # Статистика офферов  
        offers_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_offers,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_offers,
                COALESCE(SUM(CASE WHEN price > 0 THEN price ELSE budget_total END), 0) as total_budget
            FROM offers 
            WHERE created_by = ?
        """, (user_id,), fetch_one=True)
        
        # Статистика предложений (как владелец канала)
        proposals_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_proposals,
                COUNT(CASE WHEN op.status = 'accepted' THEN 1 END) as accepted,
                COUNT(CASE WHEN op.status = 'rejected' THEN 1 END) as rejected,
                COUNT(CASE WHEN op.status = 'sent' THEN 1 END) as pending
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ?
        """, (user_id,), fetch_one=True)
        
        # Статистика откликов (как создатель оффера)
        responses_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_responses,
                COUNT(CASE WHEN or_table.status = 'accepted' THEN 1 END) as accepted_responses,
                COUNT(CASE WHEN or_table.status = 'rejected' THEN 1 END) as rejected_responses
            FROM offer_responses or_table
            JOIN offers o ON or_table.offer_id = o.id
            WHERE o.created_by = ?
        """, (user_id,), fetch_one=True)
        
        # Статистика размещений
        placement_stats = execute_db_query("""
            SELECT 
                COALESCE(SUM(ps.views_count), 0) as total_views,
                COALESCE(SUM(ps.clicks_count), 0) as total_clicks
            FROM placement_statistics ps
            JOIN offer_placements op ON ps.placement_id = op.id
            JOIN offer_proposals opr ON op.proposal_id = opr.id
            JOIN channels c ON opr.channel_id = c.id
            WHERE c.owner_id = ?
        """, (user_id,), fetch_one=True)
        
        # Статистика кампаний
        campaigns_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_campaigns,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_campaigns,
                COALESCE(SUM(budget_limit), 0) as total_campaign_budget
            FROM campaigns 
            WHERE created_by = ?
        """, (user_id,), fetch_one=True)
        
        # Расчеты
        total_views = placement_stats['total_views'] or 0
        total_clicks = placement_stats['total_clicks'] or 0
        ctr = (total_clicks / max(total_views, 1)) * 100 if total_views > 0 else 0
        
        # Доходы (из завершенных офферов)
        total_revenue = execute_db_query("""
            SELECT COALESCE(SUM(CASE WHEN price > 0 THEN price ELSE budget_total END), 0) as revenue
            FROM offers 
            WHERE created_by = ? AND status = 'completed'
        """, (user_id,), fetch_one=True)['revenue'] or 0
        
        # Конверсия (завершенные размещения / общее количество предложений)
        completion_rate = 0
        if proposals_stats['total_proposals'] > 0:
            completed_placements = execute_db_query("""
                SELECT COUNT(*) as completed
                FROM offer_placements op
                JOIN offer_proposals opr ON op.proposal_id = opr.id
                JOIN channels c ON opr.channel_id = c.id
                WHERE c.owner_id = ? AND op.status = 'completed'
            """, (user_id,), fetch_one=True)['completed'] or 0
            completion_rate = (completed_placements / proposals_stats['total_proposals']) * 100
        
        return {
            'total_views': total_views,
            'click_rate': round(ctr, 2),
            'total_revenue': total_revenue,
            'conversion_rate': round(completion_rate, 2),
            'channels_count': channels_stats['total_channels'] or 0,
            'subscribers_count': channels_stats['total_subscribers'] or 0,
            'offers_count': offers_stats['total_offers'] or 0,
            'campaigns_count': campaigns_stats['total_campaigns'] or 0,
            'proposals_count': proposals_stats['total_proposals'] or 0,
            'responses_count': responses_stats['total_responses'] or 0,
            'verified_channels': channels_stats['verified_channels'] or 0,
            'active_offers': offers_stats['active_offers'] or 0,
            'active_campaigns': campaigns_stats['active_campaigns'] or 0,
            'acceptance_rate': round((proposals_stats['accepted'] / max(proposals_stats['total_proposals'], 1)) * 100, 2) if proposals_stats['total_proposals'] > 0 else 0,
            'response_rate': round((responses_stats['accepted_responses'] / max(responses_stats['total_responses'], 1)) * 100, 2) if responses_stats['total_responses'] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения метрик: {e}")
        return {
            'total_views': 0,
            'click_rate': 0,
            'total_revenue': 0,
            'conversion_rate': 0,
            'channels_count': 0,
            'subscribers_count': 0,
            'offers_count': 0,
            'campaigns_count': 0,
            'proposals_count': 0,
            'responses_count': 0,
            'verified_channels': 0,
            'active_offers': 0,
            'active_campaigns': 0,
            'acceptance_rate': 0,
            'response_rate': 0
        }

def get_chart_data(user_id: int) -> dict:
    """Данные для графиков"""
    try:
        # Данные просмотров по дням (последние 30 дней)
        views_data = execute_db_query("""
            SELECT 
                DATE(ps.collected_at) as day,
                SUM(ps.views_count) as views
            FROM placement_statistics ps
            JOIN offer_placements op ON ps.placement_id = op.id
            JOIN offer_proposals opr ON op.proposal_id = opr.id
            JOIN channels c ON opr.channel_id = c.id
            WHERE c.owner_id = ? 
                AND ps.collected_at >= DATE('now', '-30 days')
            GROUP BY DATE(ps.collected_at)
            ORDER BY day DESC
            LIMIT 7
        """, (user_id,), fetch_all=True)
        
        # Статистика предложений
        proposals_data = execute_db_query("""
            SELECT 
                op.status,
                COUNT(*) as count
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ?
            GROUP BY op.status
        """, (user_id,), fetch_all=True)
        
        # Расходы по дням (из кампаний)
        spending_data = execute_db_query("""
            SELECT 
                DATE(created_at) as day,
                SUM(budget_limit) as spending
            FROM campaigns
            WHERE created_by = ?
                AND created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY day DESC
        """, (user_id,), fetch_all=True)
        
        # Статистика по типам офферов
        offers_by_category = execute_db_query("""
            SELECT 
                COALESCE(category, 'general') as category,
                COUNT(*) as count
            FROM offers
            WHERE created_by = ?
            GROUP BY category
            ORDER BY count DESC
            LIMIT 5
        """, (user_id,), fetch_all=True)
        
        # Форматируем данные для графиков
        views_chart = {
            'labels': [row['day'] for row in reversed(views_data)] if views_data else ['Нет данных'],
            'values': [row['views'] for row in reversed(views_data)] if views_data else [0]
        }
        
        # Статистика предложений для круговой диаграммы
        proposals_dict = {}
        for row in proposals_data:
            proposals_dict[row['status']] = row['count']
        
        proposals_chart = {
            'accepted': proposals_dict.get('accepted', 0),
            'rejected': proposals_dict.get('rejected', 0),
            'pending': proposals_dict.get('sent', 0) + proposals_dict.get('expired', 0)
        }
        
        # Расходы по дням
        spending_chart = {
            'labels': [row['day'] for row in reversed(spending_data)] if spending_data else ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
            'values': [float(row['spending']) for row in reversed(spending_data)] if spending_data else [0, 0, 0, 0, 0, 0, 0]
        }
        
        # Эффективность (расчетные показатели)
        metrics = get_user_metrics(user_id)
        efficiency_chart = {
            'cpm': min(metrics['click_rate'] * 10, 100),  # Примерный CPM
            'ctr': metrics['click_rate'],
            'conversion': metrics['conversion_rate'],
            'roi': min(metrics['acceptance_rate'], 100),
            'reach': min(metrics['subscribers_count'] / 1000, 100) if metrics['subscribers_count'] > 0 else 0
        }
        
        return {
            'views_by_day': views_chart,
            'proposals_stats': proposals_chart,
            'spending_by_day': spending_chart,
            'efficiency_stats': efficiency_chart,
            'offers_by_category': {
                'labels': [row['category'] for row in offers_by_category],
                'values': [row['count'] for row in offers_by_category]
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения данных графиков: {e}")
        # Возвращаем базовую структуру с пустыми данными
        return {
            'views_by_day': {
                'labels': ['Нет данных'],
                'values': [0]
            },
            'proposals_stats': {
                'accepted': 0,
                'rejected': 0,
                'pending': 0
            },
            'spending_by_day': {
                'labels': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
                'values': [0, 0, 0, 0, 0, 0, 0]
            },
            'efficiency_stats': {
                'cpm': 0,
                'ctr': 0,
                'conversion': 0,
                'roi': 0,
                'reach': 0
            },
            'offers_by_category': {
                'labels': [],
                'values': []
            }
        }

# ================================================================
# API ENDPOINTS
# ================================================================

@analytics_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """Основной endpoint для аналитики дашборда"""
    try:
        # Получаем user_db_id
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                'success': False, 
                'error': 'Требуется авторизация'
            }), 401
        
        # Собираем все данные
        metrics = get_user_metrics(user_id)
        charts = get_chart_data(user_id)
        
        # Формируем ответ
        dashboard_data = {
            'success': True,
            'data': {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                **metrics,  # Разворачиваем метрики в корень data
                **charts   # Добавляем данные графиков
            }
        }
        
        logger.info(f"Аналитика загружена для пользователя {user_id}")
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Ошибка получения аналитики: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500

@analytics_bp.route('/status', methods=['GET'])
def get_analytics_status():
    """Проверка статуса системы аналитики"""
    try:
        telegram_id = get_current_user_id()
        
        # Проверка БД
        db_status = 'healthy'
        try:
            execute_db_query("SELECT 1", fetch_one=True)
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        status = {
            'analytics_enabled': True,
            'database_connected': db_status == 'healthy',
            'user_authenticated': bool(telegram_id),
            'telegram_id': telegram_id,
            'version': '1.0.0'
        }

        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Analytics status check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': {
                'analytics_enabled': False,
                'database_connected': False,
                'user_authenticated': False
            }
        }), 500

@analytics_bp.route('/generate-test-data', methods=['POST'])
def generate_test_data():
    """Генерация тестовых данных для аналитики (только для разработки)"""
    try:
        if not AppConfig.DEBUG:
            return jsonify({'error': 'Доступно только в режиме разработки'}), 403
            
        telegram_id = get_current_user_id()
        if not telegram_id:
            return jsonify({'error': 'Требуется авторизация'}), 401
            
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
            
        user_id = user['id']
        
        # Добавляем тестовые данные
        try:
            # Тестовые размещения (если таблица существует)
            execute_db_query("""
                INSERT OR IGNORE INTO placement_statistics 
                (placement_id, views_count, clicks_count, collected_at)
                VALUES (1, 1247, 89, datetime('now'))
            """)
            
            logger.info(f"Тестовые данные созданы для пользователя {telegram_id}")
        except Exception as e:
            logger.warning(f"Не удалось создать тестовые данные: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Тестовые данные созданы'
        })
        
    except Exception as e:
        logger.error(f"Ошибка создания тестовых данных: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@analytics_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint не найден'
    }), 404

@analytics_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Внутренняя ошибка сервера'
    }), 500
