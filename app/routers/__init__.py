# app/routers/__init__.py
"""
Модуль маршрутизации для Telegram Mini App

ИСПРАВЛЕННАЯ ВЕРСИЯ с правильными URL префиксами
"""

from flask import Flask, render_template
from .main_router import main_bp
from .api_router import api_bp
from .channel_router import channel_bp

from .analytics_router import analytics_bp
from .payment_router import payment_bp
