# app/routers/main_router.py
"""
Главный маршрутизатор для основных страниц Telegram Mini App

Содержит только основные страницы и служебные эндпоинты.
Вся логика middleware вынесена в отдельный модуль.
"""

import time
from flask import Blueprint, render_template, jsonify, current_app
from .middleware import (
    require_telegram_auth,
    cache_response,
    TelegramAuth
)

# Импорт объекта базы данных
try:
    from ..models.database import db
except ImportError:
    try:
        from app import db
    except ImportError:
        from flask_sqlalchemy import SQLAlchemy

        db = SQLAlchemy()

# Создание Blueprint
main_bp = Blueprint('main', __name__)


# === ОСНОВНЫЕ СТРАНИЦЫ ===

@main_bp.route('/')
@cache_response(timeout=600)  # Кэшируем главную страницу на 10 минут
def index():
    """Главная страница приложения"""
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        return render_template('index.html', user_id=telegram_user_id)
    except Exception as e:
        current_app.logger.error(f"Error rendering index page: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/channels')
def channels_page():
    """Страница управления каналами"""
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        if not telegram_user_id:
            return render_template('auth_required.html'), 401

        return render_template('channels.html', user_id=telegram_user_id)
    except Exception as e:
        current_app.logger.error(f"Error rendering channels page: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        return render_template('analytics.html', user_id=telegram_user_id)
    except Exception as e:
        current_app.logger.error(f"Error rendering analytics page: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/payments')
def payments_page():
    """Страница платежей"""
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        if not telegram_user_id:
            return render_template('auth_required.html'), 401

        return render_template('payments.html', user_id=telegram_user_id)
    except Exception as e:
        current_app.logger.error(f"Error rendering payments page: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/offers')
def offers_page():
    """Страница создания офферов"""
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        if not telegram_user_id:
            return render_template('auth_required.html'), 401

        return render_template('offers.html', user_id=telegram_user_id)
    except Exception as e:
        current_app.logger.error(f"Error rendering offers page: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# === СЛУЖЕБНЫЕ ЭНДПОИНТЫ ===

@main_bp.route('/health')
def health_check():
    """Проверка состояния приложения"""
    try:
        # Проверяем подключение к БД
        db.session.execute('SELECT 1')

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
        'telegram_user_id': TelegramAuth.get_current_user_id(),
        'features': {
            'channels': True,
            'offers': True,
            'analytics': True,
            'payments': True
        }
    })


@main_bp.route('/app-info')
@cache_response(timeout=3600)  # Кэшируем на 1 час
def app_info():
    """Информация о приложении"""
    return jsonify({
        'app_name': 'Telegram Mini App',
        'version': '1.0.0',
        'description': 'Платформа для размещения рекламы в Telegram каналах',
        'features': [
            'Управление каналами',
            'Создание рекламных офферов',
            'Система откликов',
            'Детальная аналитика',
            'Безопасные платежи',
            'Эскроу система'
        ],
        'api_version': 'v1',
        'documentation': '/api/docs'
    })


# === СТРАНИЦЫ ОШИБОК ===

@main_bp.route('/404')
def page_not_found():
    """Кастомная страница 404"""
    return render_template('errors/404.html'), 404


@main_bp.route('/500')
def internal_error():
    """Кастомная страница 500"""
    return render_template('errors/500.html'), 500


@main_bp.route('/auth-required')
def auth_required():
    """Страница требования аутентификации"""
    return render_template('auth_required.html'), 401


# Инициализация Blueprint
def init_main_routes():
    """Инициализация основных маршрутов"""
    current_app.logger.info("✅ Main routes initialized")


# Экспорт
__all__ = ['main_bp', 'init_main_routes']