# app/routers/main_router.py
"""
Главный маршрутизатор для основных страниц Telegram Mini App
Без аутентификации - все страницы доступны
"""

import time
from flask import Blueprint, render_template, jsonify, current_app, request

# Создание Blueprint
main_bp = Blueprint('main', __name__)

# === ОСНОВНЫЕ СТРАНИЦЫ ===

@main_bp.route('/')
def index():
    """Главная страница приложения"""
    try:
        return render_template('index.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering index page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/channels')
def channels_page():
    """Страница управления каналами"""
    try:
        return render_template('channels.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering channels page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    try:
        return render_template('analytics.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering analytics page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/payments')
def payments_page():
    """Страница платежей"""
    try:
        return render_template('payments.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering payments page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/offers')
def offers_page():
    """Страница создания офферов"""
    try:
        return render_template('offers.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering offers page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# === СЛУЖЕБНЫЕ ЭНДПОИНТЫ ===

@main_bp.route('/health')
def health_check():
    """Проверка состояния приложения"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'version': '1.0.0',
            'telegram_webapp': True
        })
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@main_bp.route('/test')
def test_endpoint():
    """Тестовый эндпоинт для проверки работоспособности"""
    return jsonify({
        'message': 'Telegram Mini App работает!',
        'timestamp': time.time(),
        'user_agent': request.headers.get('User-Agent'),
        'features': {
            'channels': True,
            'offers': True,
            'analytics': True,
            'payments': True
        }
    })


@main_bp.route('/test-offers')
def test_offers_page():
    """Тестовая страница для проверки API офферов"""
    try:
        return render_template('test-offers.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering test offers page: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/offers/available')
def available_offers_page():
    """Страница доступных офферов"""
    try:
        return render_template('offers-list.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering available offers page: {e}")
        return jsonify({'error': 'Internal server error'}), 500



# === API СТАТИСТИКИ ===
# тут считаю количество на главной странице
@main_bp.route('/api/stats/global')
def global_stats():
    """API для получения общей статистики системы"""
    try:
        from ..models.database import db_manager

        # Инициализируем статистику нулями
        stats = {
            'channels': 0,
            'users': 0,
            'offers': 0,
            'revenue': 0
        }

        # Безопасный подсчет каналов
        try:
            result = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM channels WHERE is_active = 1",
                fetch_one=True
            )
            if result:
                stats['channels'] = int(result['count'])
        except Exception as e:
            current_app.logger.warning(f"Channels count error: {e}")
            # Пробуем без фильтра
            try:
                result = db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM channels",
                    fetch_one=True
                )
                if result:
                    stats['channels'] = int(result['count'])
            except:
                pass

        # Безопасный подсчет пользователей
        try:
            result = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM users",
                fetch_one=True
            )
            if result:
                stats['users'] = int(result['count'])
        except Exception as e:
            current_app.logger.warning(f"Users count error: {e}")

        # Безопасный подсчет офферов - пробуем разные варианты
        try:
            # Сначала пробуем основную таблицу offers
            result = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM offers",
                fetch_one=True
            )
            if result:
                stats['offers'] = int(result['count'])
        except Exception as e:
            current_app.logger.warning(f"Offers count error: {e}")
            # Пробуем offers_extended
            try:
                result = db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM offers_extended",
                    fetch_one=True
                )
                if result:
                    stats['offers'] = int(result['count'])
            except:
                pass

        # Безопасный подсчет оборота
        try:
            # Пробуем через completed offers
            result = db_manager.execute_query(
                "SELECT COALESCE(SUM(price), 0) as total FROM offers WHERE status = 'completed'",
                fetch_one=True
            )
            if result and result['total']:
                stats['revenue'] = int(result['total'])
        except Exception as e:
            current_app.logger.warning(f"Revenue calculation error: {e}")
            # Пробуем offers_extended
            try:
                result = db_manager.execute_query(
                    "SELECT COALESCE(SUM(price), 0) as total FROM offers_extended WHERE status = 'completed'",
                    fetch_one=True
                )
                if result and result['total']:
                    stats['revenue'] = int(result['total'])
            except:
                pass

        current_app.logger.info(f"Global stats calculated: {stats}")

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        current_app.logger.error(f"Critical error getting global stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load statistics',
            'stats': {
                'channels': 0,
                'users': 0,
                'offers': 0,
                'revenue': 0
            }
        }), 500

# Экспорт
__all__ = ['main_bp']
