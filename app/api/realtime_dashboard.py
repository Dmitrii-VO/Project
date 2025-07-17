#!/usr/bin/env python3
"""
API для обновления дашбордов в реальном времени
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# Создаем Blueprint для API дашборда
dashboard_api = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')


@dashboard_api.route('/stats/placement/<int:placement_id>', methods=['GET'])
def get_placement_stats(placement_id: int):
    """Получает статистику конкретного размещения"""
    try:
        from app.services.ereit_integration import EREITIntegration
        from app.models.database import execute_db_query
        
        # Получаем основную информацию о размещении
        placement = execute_db_query("""
            SELECT p.*, 
                   o.title as offer_title,
                   o.price,
                   r.channel_title,
                   r.channel_username,
                   r.channel_subscribers
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.id = ?
        """, (placement_id,), fetch_one=True)
        
        if not placement:
            return jsonify({'error': 'Размещение не найдено'}), 404
        
        # Получаем последнюю статистику из разных источников
        telegram_stats = execute_db_query("""
            SELECT * FROM placement_statistics 
            WHERE placement_id = ? 
            ORDER BY collected_at DESC 
            LIMIT 1
        """, (placement_id,), fetch_one=True)
        
        ereit_stats = execute_db_query("""
            SELECT * FROM ereit_statistics 
            WHERE placement_id = ? 
            ORDER BY collected_at DESC 
            LIMIT 1
        """, (placement_id,), fetch_one=True)
        
        # Формируем ответ
        response_data = {
            'placement': {
                'id': placement['id'],
                'title': placement['offer_title'],
                'status': placement['status'],
                'price': placement['price'],
                'post_url': placement['post_url'],
                'ereit_token': placement['ereit_token'],
                'placement_start': placement['placement_start'],
                'deadline': placement['deadline']
            },
            'channel': {
                'title': placement['channel_title'],
                'username': placement['channel_username'],
                'subscribers': placement['channel_subscribers']
            },
            'telegram_stats': {
                'views': telegram_stats['views_count'] if telegram_stats else 0,
                'reactions': telegram_stats['reactions_count'] if telegram_stats else 0,
                'shares': telegram_stats['shares_count'] if telegram_stats else 0,
                'comments': telegram_stats['comments_count'] if telegram_stats else 0,
                'last_updated': telegram_stats['collected_at'] if telegram_stats else None
            },
            'ereit_stats': {
                'clicks': ereit_stats['clicks'] if ereit_stats else 0,
                'unique_clicks': ereit_stats['unique_clicks'] if ereit_stats else 0,
                'ctr': ereit_stats['ctr'] if ereit_stats else 0.0,
                'conversions': ereit_stats['conversion_events'] if ereit_stats else 0,
                'last_updated': ereit_stats['collected_at'] if ereit_stats else None
            },
            'performance': calculate_performance_metrics(placement, telegram_stats, ereit_stats),
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики размещения {placement_id}: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


@dashboard_api.route('/stats/overview', methods=['GET'])
def get_overview_stats():
    """Получает общую статистику по всем размещениям"""
    try:
        from app.models.database import execute_db_query
        
        # Получаем общую статистику
        overview = execute_db_query("""
            SELECT 
                COUNT(*) as total_placements,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_placements,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_placements,
                COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_placements,
                SUM(CASE WHEN status IN ('active', 'completed') THEN funds_reserved ELSE 0 END) as total_revenue
            FROM offer_placements
            WHERE created_at >= datetime('now', '-30 days')
        """, fetch_one=True)
        
        # Статистика по периодам
        period_stats = get_period_statistics()
        
        # Топ каналы
        top_channels = execute_db_query("""
            SELECT 
                r.channel_title,
                r.channel_username,
                COUNT(*) as placements_count,
                AVG(COALESCE(ps.views_count, 0)) as avg_views,
                AVG(COALESCE(es.clicks, 0)) as avg_clicks
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            LEFT JOIN placement_statistics ps ON p.id = ps.placement_id
            LEFT JOIN ereit_statistics es ON p.id = es.placement_id
            WHERE p.status IN ('active', 'completed')
            AND p.created_at >= datetime('now', '-30 days')
            GROUP BY r.channel_id
            ORDER BY placements_count DESC, avg_views DESC
            LIMIT 10
        """, fetch_all=True)
        
        response_data = {
            'overview': {
                'total_placements': overview['total_placements'] or 0,
                'active_placements': overview['active_placements'] or 0,
                'completed_placements': overview['completed_placements'] or 0,
                'expired_placements': overview['expired_placements'] or 0,
                'total_revenue': overview['total_revenue'] or 0,
                'success_rate': round((overview['completed_placements'] or 0) / max(overview['total_placements'] or 1, 1) * 100, 2)
            },
            'period_stats': period_stats,
            'top_channels': [
                {
                    'title': channel['channel_title'],
                    'username': channel['channel_username'],
                    'placements_count': channel['placements_count'],
                    'avg_views': round(channel['avg_views'] or 0),
                    'avg_clicks': round(channel['avg_clicks'] or 0)
                }
                for channel in top_channels
            ],
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения общей статистики: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


@dashboard_api.route('/stats/period', methods=['GET'])
def get_period_stats():
    """Получает статистику за определенный период"""
    try:
        from app.models.database import execute_db_query
        
        # Получаем параметры запроса
        days = request.args.get('days', 7, type=int)
        
        # Ограничиваем период
        days = min(days, 90)  # Максимум 90 дней
        
        period_stats = execute_db_query("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as placements,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                SUM(funds_reserved) as revenue
            FROM offer_placements
            WHERE created_at >= datetime('now', '-{} days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """.format(days), fetch_all=True)
        
        response_data = {
            'period': f"{days} days",
            'stats': [
                {
                    'date': stat['date'],
                    'placements': stat['placements'],
                    'completed': stat['completed'],
                    'revenue': stat['revenue'] or 0
                }
                for stat in period_stats
            ],
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики за период: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


@dashboard_api.route('/live/active-placements', methods=['GET'])
def get_live_active_placements():
    """Получает список активных размещений в реальном времени"""
    try:
        from app.models.database import execute_db_query
        
        active_placements = execute_db_query("""
            SELECT 
                p.id,
                p.status,
                p.post_url,
                p.placement_start,
                p.deadline,
                o.title as offer_title,
                r.channel_title,
                r.channel_username,
                COALESCE(ps.views_count, 0) as current_views,
                COALESCE(es.clicks, 0) as current_clicks,
                CASE 
                    WHEN p.deadline < CURRENT_TIMESTAMP THEN 'overdue'
                    WHEN p.deadline < datetime('now', '+2 hours') THEN 'urgent'
                    ELSE 'normal'
                END as urgency
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            LEFT JOIN placement_statistics ps ON p.id = ps.placement_id 
                AND ps.id = (SELECT MAX(id) FROM placement_statistics WHERE placement_id = p.id)
            LEFT JOIN ereit_statistics es ON p.id = es.placement_id 
                AND es.id = (SELECT MAX(id) FROM ereit_statistics WHERE placement_id = p.id)
            WHERE p.status IN ('pending_placement', 'active')
            ORDER BY 
                CASE urgency 
                    WHEN 'overdue' THEN 1 
                    WHEN 'urgent' THEN 2 
                    ELSE 3 
                END,
                p.deadline ASC
        """, fetch_all=True)
        
        response_data = {
            'active_placements': [
                {
                    'id': placement['id'],
                    'status': placement['status'],
                    'title': placement['offer_title'],
                    'channel': {
                        'title': placement['channel_title'],
                        'username': placement['channel_username']
                    },
                    'post_url': placement['post_url'],
                    'placement_start': placement['placement_start'],
                    'deadline': placement['deadline'],
                    'urgency': placement['urgency'],
                    'stats': {
                        'views': placement['current_views'],
                        'clicks': placement['current_clicks']
                    }
                }
                for placement in active_placements
            ],
            'total_count': len(active_placements),
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения активных размещений: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500


def calculate_performance_metrics(placement: Dict, telegram_stats: Optional[Dict], ereit_stats: Optional[Dict]) -> Dict:
    """Вычисляет метрики эффективности размещения"""
    try:
        metrics = {}
        
        if telegram_stats:
            views = telegram_stats['views_count'] or 0
            reactions = telegram_stats['reactions_count'] or 0
            
            if views > 0:
                metrics['engagement_rate'] = round((reactions / views) * 100, 2)
        
        if ereit_stats:
            clicks = ereit_stats['clicks'] or 0
            conversions = ereit_stats['conversion_events'] or 0
            
            metrics['ctr'] = ereit_stats['ctr'] or 0.0
            
            if clicks > 0:
                metrics['conversion_rate'] = round((conversions / clicks) * 100, 2)
        
        if telegram_stats and ereit_stats:
            views = telegram_stats['views_count'] or 1
            clicks = ereit_stats['clicks'] or 0
            
            metrics['click_through_rate'] = round((clicks / views) * 100, 2)
        
        # CPM (cost per mille)
        if placement.get('price') and telegram_stats:
            views = telegram_stats['views_count'] or 1
            metrics['cpm'] = round((placement['price'] / views) * 1000, 2)
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Ошибка вычисления метрик: {e}")
        return {}


def get_period_statistics() -> List[Dict]:
    """Получает статистику по периодам (7, 30 дней)"""
    from app.models.database import execute_db_query
    
    periods = [
        ('7_days', 7),
        ('30_days', 30)
    ]
    
    result = {}
    
    for period_name, days in periods:
        stats = execute_db_query("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                AVG(COALESCE(ps.views_count, 0)) as avg_views,
                AVG(COALESCE(es.clicks, 0)) as avg_clicks
            FROM offer_placements p
            LEFT JOIN placement_statistics ps ON p.id = ps.placement_id
            LEFT JOIN ereit_statistics es ON p.id = es.placement_id
            WHERE p.created_at >= datetime('now', '-{} days')
        """.format(days), fetch_one=True)
        
        result[period_name] = {
            'total_placements': stats['total'] or 0,
            'completed_placements': stats['completed'] or 0,
            'avg_views': round(stats['avg_views'] or 0),
            'avg_clicks': round(stats['avg_clicks'] or 0),
            'success_rate': round((stats['completed'] or 0) / max(stats['total'] or 1, 1) * 100, 2)
        }
    
    return result


# Регистрируем Blueprint в главном приложении
def register_dashboard_api(app):
    """Регистрирует API дашборда в Flask приложении"""
    app.register_blueprint(dashboard_api)
    logger.info("✅ Dashboard API зарегистрирован")


if __name__ == "__main__":
    # Тестирование API
    from flask import Flask
    
    app = Flask(__name__)
    register_dashboard_api(app)
    
    print("Dashboard API endpoints:")
    for rule in app.url_map.iter_rules():
        if 'dashboard' in rule.endpoint:
            print(f"  {rule.methods} {rule.rule}")