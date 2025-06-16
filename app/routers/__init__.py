# app/routers/__init__.py
"""
Модуль маршрутизации для Telegram Mini App

ИСПРАВЛЕННАЯ ВЕРСИЯ с правильными URL префиксами
"""

from flask import Flask, render_template
from .main_router import main_bp
from .api_router import api_bp
from .channel_router import channel_bp
from .offer_router import offer_bp
from .analytics_router import analytics_bp
from .payment_router import payment_bp

# ИСПРАВЛЕННЫЙ список Blueprint'ов с правильными префиксами
BLUEPRINTS = [
    (main_bp, '', 'main'),  # Основные страницы: /, /channels, /offers, /analytics, /payments
    (api_bp, '/api', 'api'),  # Общие API endpoints
    (channel_bp, '/api/channels', 'channels_api'),  # API для каналов
    (offer_bp, '/api/offers', 'offers_api'),  # API для офферов
    (analytics_bp, '/api/analytics', 'analytics_api'),  # API для аналитики
    (payment_bp, '/api/payments', 'payments_api'),  # API для платежей
]


def register_blueprints(app: Flask) -> None:
    """
    Регистрирует все Blueprint'ы в приложении Flask

    Args:
        app: Экземпляр Flask приложения
    """

    for blueprint, url_prefix, name in BLUEPRINTS:
        try:
            app.register_blueprint(
                blueprint,
                url_prefix=url_prefix,
                name=name
            )
            prefix_display = url_prefix if url_prefix else "/"
            app.logger.info(f"✅ Blueprint '{name}' зарегистрирован с префиксом '{prefix_display}'")
        except Exception as e:
            app.logger.error(f"❌ Ошибка регистрации Blueprint '{name}': {e}")
            # Не поднимаем исключение, продолжаем регистрацию других Blueprint'ов
            continue


def init_routers(app: Flask) -> None:
    """
    Инициализирует систему маршрутизации

    Args:
        app: Экземпляр Flask приложения
    """

    # Регистрируем все Blueprint'ы
    register_blueprints(app)

    # Настраиваем обработчики ошибок
    setup_error_handlers(app)

    # Настраиваем middleware
    setup_middleware(app)

    app.logger.info("🚀 Система маршрутизации инициализирована")


def setup_error_handlers(app: Flask) -> None:
    """Настройка обработчиков ошибок"""

    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'API endpoint not found'}), 404
        try:
            return render_template('error.html', message='Страница не найдена'), 404
        except:
            return '<h1>404 - Страница не найдена</h1>', 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify, request
        app.logger.error(f"Internal error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        try:
            return render_template('error.html', message='Внутренняя ошибка сервера'), 500
        except:
            return '<h1>500 - Внутренняя ошибка сервера</h1>', 500


def setup_middleware(app: Flask) -> None:
    """Настройка middleware"""

    try:
        from .middleware import (
            security_middleware,
            telegram_auth_middleware,
            performance_middleware
        )

        # Регистрируем middleware
        app.before_request(security_middleware)
        app.before_request(telegram_auth_middleware)
        app.before_request(performance_middleware)

        app.logger.info("✅ Middleware зарегистрированы")
    except ImportError as e:
        app.logger.warning(f"⚠️ Не удалось загрузить middleware: {e}")


__all__ = [
    'register_blueprints',
    'init_routers',
    'main_bp',
    'api_bp',
    'channel_bp',
    'offer_bp',
    'analytics_bp',
    'payment_bp'
]