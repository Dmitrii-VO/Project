# app/routers/__init__.py
"""
Модуль маршрутизации для Telegram Mini App

ИСПРАВЛЕННАЯ ВЕРСИЯ с правильными URL префиксами
"""

from flask import Flask, render_template
from .main_router import main_bp
from .api_router import api_bp

