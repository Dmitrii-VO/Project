# app/api/offers_new.py
"""
Новая модульная версия offers API
Заменяет монолитный файл app/api/offers.py

Использует сервисный слой для всей бизнес-логики
Структура:
- /api/offers/ - основные операции с офферами  
- /api/offers/management/ - административные функции
"""

from flask import Blueprint
from app.services.offers.api import offer_routes, offer_management

# Создаем основной Blueprint
offers_bp = Blueprint('offers', __name__, url_prefix='/api/offers')

# Регистрируем вложенные Blueprint'ы
offers_bp.register_blueprint(offer_routes, url_prefix='')
offers_bp.register_blueprint(offer_management, url_prefix='/management')

# Экспортируем для регистрации в основном приложении
__all__ = ['offers_bp']