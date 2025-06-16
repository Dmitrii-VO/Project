#!/usr/bin/env python3
"""
Working App без аутентификации
Все разделы доступны без ограничений
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify

# Создаем приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['DEBUG'] = True

# Регистрируем Blueprint'ы
try:
    from app.routers.main_router import main_bp
    app.register_blueprint(main_bp)
    print("✅ Основные маршруты зарегистрированы")
except ImportError as e:
    print(f"⚠️ Ошибка импорта роутеров: {e}")
    
    # Fallback маршруты
    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except:
            return "<h1>Telegram Mini App</h1><p>Главная страница</p>"

    @app.route('/channels')
    def channels():
        try:
            return render_template('channels.html')
        except:
            return "<h1>Каналы</h1><p>Управление каналами</p>"

    @app.route('/offers')
    def offers():
        try:
            return render_template('offers.html')
        except:
            return "<h1>Офферы</h1><p>Создание офферов</p>"

    @app.route('/analytics')
    def analytics():
        try:
            return render_template('analytics.html')
        except:
            return "<h1>Аналитика</h1><p>Статистика и отчеты</p>"

    @app.route('/payments')
    def payments():
        try:
            return render_template('payments.html')
        except:
            return "<h1>Платежи</h1><p>Управление платежами</p>"

    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })

if __name__ == '__main__':
    print("🚀 Запуск Telegram Mini App (БЕЗ АУТЕНТИФИКАЦИИ)")
    print("📱 Все разделы доступны:")
    print("   http://localhost:5000/          - Главная")
    print("   http://localhost:5000/channels  - Каналы")
    print("   http://localhost:5000/offers    - Офферы")
    print("   http://localhost:5000/analytics - Аналитика")
    print("   http://localhost:5000/payments  - Платежи")
    print("🌐 Приложение запущено на http://localhost:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
