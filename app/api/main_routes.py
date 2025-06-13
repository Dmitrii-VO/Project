from flask import Blueprint, render_template, jsonify, request
from app.services.auth_service import auth_service
from app.models.database import db_manager
from app.config.settings import Config
import os
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@main_bp.route('/channels-enhanced')
def channels_page():
    """Страница управления каналами"""
    return render_template('channels.html')


@main_bp.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        if not telegram_user_id:
            return render_template('analytics.html', demo_mode=True)

        user = db_manager.execute_query(
            'SELECT id, username FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return render_template('analytics.html', demo_mode=True)

        return render_template('analytics.html',
                               demo_mode=False,
                               telegram_user_id=telegram_user_id,
                               analytics_enabled=Config.ANALYTICS_SYSTEM_ENABLED)

    except Exception as e:
        logger.error(f"Ошибка загрузки страницы аналитики: {e}")
        return render_template('analytics.html', demo_mode=True, error=str(e))


@main_bp.route('/payments')
def payments_page():
    """Страница платежей"""
    return render_template('payments.html')


@main_bp.route('/test')
def api_test():
    """Тестовая страница"""
    return jsonify({
        'status': 'OK',
        'message': 'Модульная архитектура работает!',
        'features': {
            'telegram_api': bool(Config.BOT_TOKEN),
            'telegram_integration': Config.TELEGRAM_INTEGRATION,
            'offers_system': Config.OFFERS_SYSTEM_ENABLED,
            'responses_system': Config.RESPONSES_SYSTEM_ENABLED,
            'payments_system': Config.PAYMENTS_SYSTEM_ENABLED,
            'analytics_system': Config.ANALYTICS_SYSTEM_ENABLED,
            'database': 'SQLite',
            'modular_architecture': True
        },
        'config': {
            'bot_token_configured': bool(Config.BOT_TOKEN),
            'database_path': Config.DATABASE_PATH,
            'database_exists': os.path.exists(Config.DATABASE_PATH),
            'your_telegram_id': Config.YOUR_TELEGRAM_ID
        }
    })


@main_bp.route('/health')
def health_check():
    """Проверка здоровья приложения"""
    try:
        # Тест базы данных
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        conn.close()

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'database_type': 'SQLite',
            'database_path': Config.DATABASE_PATH,
            'database_size': f"{os.path.getsize(Config.DATABASE_PATH) / 1024:.1f} KB" if os.path.exists(
                Config.DATABASE_PATH) else 'N/A',
            'modular_architecture': True,
            'systems': {
                'telegram_integration': Config.TELEGRAM_INTEGRATION,
                'offers_system': Config.OFFERS_SYSTEM_ENABLED,
                'responses_system': Config.RESPONSES_SYSTEM_ENABLED,
                'payments_system': Config.PAYMENTS_SYSTEM_ENABLED,
                'analytics_system': Config.ANALYTICS_SYSTEM_ENABLED
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500


@main_bp.route('/api/stats')
def api_stats():
    """Общая статистика системы"""
    try:
        # Статистика пользователей
        users_count = db_manager.execute_query('SELECT COUNT(*) as count FROM users', fetch_one=True)

        # Статистика каналов
        channels_count = db_manager.execute_query('SELECT COUNT(*) as count FROM channels', fetch_one=True)

        # Статистика офферов
        offers_count = db_manager.execute_query('SELECT COUNT(*) as count FROM offers',
                                                fetch_one=True) if Config.OFFERS_SYSTEM_ENABLED else {'count': 0}

        # Статистика откликов
        responses_count = db_manager.execute_query('SELECT COUNT(*) as count FROM offer_responses',
                                                   fetch_one=True) if Config.RESPONSES_SYSTEM_ENABLED else {'count': 0}

        return jsonify({
            'success': True,
            'users': users_count['count'] if users_count else 0,
            'channels': channels_count['count'] if channels_count else 0,
            'offers': offers_count['count'] if offers_count else 0,
            'responses': responses_count['count'] if responses_count else 0,
            'features': {
                'modular_architecture': True,
                'telegram_integration': Config.TELEGRAM_INTEGRATION,
                'offers_system': Config.OFFERS_SYSTEM_ENABLED,
                'responses_system': Config.RESPONSES_SYSTEM_ENABLED,
                'payments_system': Config.PAYMENTS_SYSTEM_ENABLED,
                'database': 'SQLite',
                'bot_configured': bool(Config.BOT_TOKEN)
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'users': 0,
            'channels': 0,
            'offers': 0,
            'responses': 0
        }), 500