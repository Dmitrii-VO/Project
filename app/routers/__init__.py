# app/routers/__init__.py
"""
Модуль маршрутизации для Telegram Mini App

Этот модуль содержит все маршруты и Blueprint'ы приложения.
Оптимизирован для производительности и безопасности.
"""

from flask import Flask, render_template
from .main_router import main_bp
from .api_router import api_bp
from .channel_router import channel_bp
from .offer_router import offer_bp
from .analytics_router import analytics_bp
from .payment_router import payment_bp

# Список всех Blueprint'ов для регистрации
BLUEPRINTS = [
    (main_bp, '/', 'main'),
    (api_bp, '/api', 'api'),
    (channel_bp, '/channels', 'channels'),
    (offer_bp, '/offers', 'offers'),
    (analytics_bp, '/analytics', 'analytics'),
    (payment_bp, '/payments', 'payments')
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
            app.logger.info(f"✅ Blueprint '{name}' зарегистрирован с префиксом '{url_prefix}'")
        except Exception as e:
            app.logger.error(f"❌ Ошибка регистрации Blueprint '{name}': {e}")
            raise


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
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify, request
        app.logger.error(f"Internal error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500


def setup_middleware(app: Flask) -> None:
    """Настройка middleware"""

    from .middleware import (
        security_middleware,
        telegram_auth_middleware,
        performance_middleware
    )

    # Регистрируем middleware
    app.before_request(security_middleware)
    app.before_request(telegram_auth_middleware)
    app.before_request(performance_middleware)


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