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

# Экспорт
__all__ = ['main_bp']
