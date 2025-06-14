# app/api/__init__.py
"""
API модуль для Telegram Mini App
Содержит все API маршруты разделенные по функциональности
"""

from flask import Blueprint

# Для удобства импорта Blueprint'ов
__all__ = ['main_bp', 'auth_bp', 'channels_bp', 'offers_bp', 'payments_bp', 'analytics_bp', 'channel_recommendations_bp']


def get_available_blueprints():
    """Получить список доступных Blueprint'ов"""
    blueprints = []

    try:
        from .main_routes import main_bp
        blueprints.append(('main_routes', main_bp, None))
    except ImportError:
        pass

    try:
        from .auth import auth_bp
        blueprints.append(('auth', auth_bp, '/api/auth'))
    except ImportError:
        pass

    try:
        from .channels import channels_bp
        blueprints.append(('channels', channels_bp, '/api/channels'))
    except ImportError:
        pass

    try:
        from .offers import offers_bp
        blueprints.append(('offers', offers_bp, '/api/offers'))
    except ImportError:
        pass

    try:
        from .payments import payments_bp
        blueprints.append(('payments', payments_bp, '/api/payments'))
    except ImportError:
        pass

    try:
        from .analytics import analytics_bp
        blueprints.append(('analytics', analytics_bp, '/api/analytics'))
    except ImportError:
        pass

    try:
        from .analytics import analytics_bp
        blueprints.append(('channel_recommendations', analytics_bp, '/api/channel_recommendations'))
    except ImportError:
        pass

    return blueprints