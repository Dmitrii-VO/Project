from flask import Blueprint, request, jsonify
from app.services.auth_service import auth_service
from app.utils.decorators import require_telegram_auth
from app.models.database import db_manager
from app.config.telegram_config import AppConfig
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/status', methods=['GET'])
def get_analytics_status():
    """Проверка статуса системы аналитики"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        status = {
            'analytics_enabled': AppConfig.ANALYTICS_SYSTEM_ENABLED,
            'database_connected': True,  # Если дошли до сюда, значит БД работает
            'user_authenticated': bool(telegram_user_id),
            'telegram_user_id': telegram_user_id,
            'placement_tracking': AppConfig.PLACEMENT_TRACKING_ENABLED,
            'ai_recommendations': AppConfig.AI_RECOMMENDATIONS_ENABLED
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


@analytics_bp.route('/dashboard-data', methods=['GET'])
@require_telegram_auth
def get_dashboard_data():
    """Получение данных для дашборда аналитики"""
    try:
        if not AppConfig.ANALYTICS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система аналитики отключена'}), 503

        telegram_user_id = auth_service.get_current_user_id()
        range_type = request.args.get('range', '30d')

        # Получаем базовые метрики
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        user_db_id = user['id']

        # Базовая статистика
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'range': range_type,
            'user_id': telegram_user_id,
            'metrics': {},
            'charts': {},
            'performance': []
        }

        # Получаем метрики каналов
        channels_metrics = db_manager.execute_query('''
                                                    SELECT COUNT(*)               as total_channels,
                                                           SUM(subscriber_count) as total_subscriber,
                                                           AVG(subscriber_count) as avg_subscriber
                                                    FROM channels c
                                                             JOIN users u ON c.owner_id = u.id
                                                    WHERE u.telegram_id = ?
                                                    ''', (telegram_user_id,), fetch_one=True)

        # Получаем метрики офферов
        offers_metrics = db_manager.execute_query('''
                                                  SELECT COUNT(*)                                                               as total_offers,
                                                         COUNT(CASE WHEN status = 'active' THEN 1 END)                          as active_offers,
                                                         SUM(CASE WHEN status IN ('completed', 'active') THEN price ELSE 0 END) as total_spent
                                                  FROM offers o
                                                           JOIN users u ON o.created_by = u.id
                                                  WHERE u.telegram_id = ?
                                                  ''', (telegram_user_id,), fetch_one=True)

        dashboard_data['metrics'] = {
            'channels': channels_metrics or {},
            'offers': offers_metrics or {},
            'revenue': 0,  # Пока заглушка
            'conversion_rate': 0  # Пока заглушка
        }

        # Заглушка для графиков
        dashboard_data['charts'] = {
            'revenue_chart': [
                {'date': '2024-01-01', 'revenue': 1000},
                {'date': '2024-01-02', 'revenue': 1500},
                {'date': '2024-01-03', 'revenue': 1200}
            ],
            'channels_growth': [
                {'date': '2024-01-01', 'channels': 5},
                {'date': '2024-01-02', 'channels': 7},
                {'date': '2024-01-03', 'channels': 8}
            ]
        }

        return jsonify({
            'success': True,
            'dashboard_data': dashboard_data
        })

    except Exception as e:
        logger.error(f"Dashboard data API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500