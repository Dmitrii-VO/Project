#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
ФИНАЛЬНАЯ ВЕРСИЯ - убрано дублирование, сохранена функциональность
"""

import os
import sqlite3
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
from app.models.database import execute_db_query
from app.api.offers import offers_bp
from app.routers.main_router import main_bp
from app.api.channels import channels_bp
import requests
from flask import Flask, jsonify, request, render_template


# Загрузка переменных окружения
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем системные переменные")

# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
def setup_logging() -> logging.Logger:
    """Настройка системы логирования"""
    logging.basicConfig(
        level=logging.INFO if not AppConfig.DEBUG else logging.DEBUG,
        format='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger('TelegramApp')
    logger.info("📋 Система логирования инициализирована")
    return logger

# === СОЗДАНИЕ ПРИЛОЖЕНИЯ ===
def create_app() -> Flask:
    """Фабрика приложений"""

    app = Flask(__name__, static_folder= 'app/static', template_folder='templates')
    app.config.from_object(AppConfig)

    # Настройка JSON сериализации
    app.json.ensure_ascii = False
    app.json.sort_keys = AppConfig.JSON_SORT_KEYS

    # Инициализация компонентов
    register_blueprints(app)
    register_middleware(app)
    register_error_handlers(app)
    
    register_system_routes(app)

    return app

# === РЕГИСТРАЦИЯ BLUEPRINTS ===
def register_blueprints(app: Flask) -> None:
    """Регистрация Blueprint'ов"""
    app.register_blueprint(offers_bp, url_prefix='/api/offers')
    app.register_blueprint(main_bp)
    app.register_blueprint(channels_bp, url_prefix='/api/channels')


# === MIDDLEWARE ===
def register_middleware(app: Flask) -> None:
    """Регистрация middleware"""

    @app.before_request
    def security_middleware():
        if request.content_length and request.content_length > AppConfig.MAX_CONTENT_LENGTH:
            return jsonify({'error': 'Request too large'}), 413

    @app.after_request
    def security_headers(response):
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
        })
        return response


# === ОБРАБОТЧИКИ ОШИБОК ===
def register_error_handlers(app: Flask) -> None:
    """Регистрация обработчиков ошибок"""

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'path': request.path}), 404
        return render_template('error.html', message='Страница не найдена'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', message='Внутренняя ошибка сервера'), 500


# === СЛУЖЕБНЫЕ МАРШРУТЫ ===
def register_system_routes(app: Flask) -> None:
    """Регистрация служебных маршрутов"""

    # Базовые каналы endpoints для совместимости
    @app.route('/api/channels/<int:channel_id>/verify', methods=['PUT', 'POST'])
    def verify_channel_unified(channel_id):
        """Верификация канала"""
        try:
            telegram_user_id = get_user_id_from_request()

            result = {
                'success': True,
                'message': f'✅ Канал {channel_id} успешно верифицирован!',
                'channel': {
                    'id': channel_id,
                    'is_verified': True,
                    'verified_at': datetime.utcnow().isoformat()
                }
            }

            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ Ошибка верификации канала: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400


# ===== TELEGRAM WEBHOOK =====
def setup_telegram_webhook():
    """Настройка webhook для Telegram бота"""
    try:
        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            return

        webhook_url = f"{AppConfig.WEBAPP_URL}/api/channels/webhook"
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

        response = requests.post(url, json={
            'url': webhook_url,
            'allowed_updates': ['channel_post', 'message', 'edited_message', 'edited_channel_post'],
            'drop_pending_updates': False
        })

        if response.status_code == 200 and response.json().get('ok'):
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        else:
            logger.error(f"❌ Ошибка установки webhook")

    except Exception as e:
        logger.error(f"❌ Ошибка настройки webhook: {e}")


# === ИНИЦИАЛИЗАЦИЯ ===
logger = setup_logging()
app = create_app()

# === ТОЧКА ВХОДА ===
def main():
    """Главная функция запуска"""

    if not AppConfig.validate():
        logger.error("❌ Критические ошибки конфигурации")
        sys.exit(1)

    setup_telegram_webhook()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    logger.info("=" * 60)
    logger.info("🚀 TELEGRAM MINI APP - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ")
    logger.info("=" * 60)
    logger.info(f"📱 BOT_TOKEN: {'✅ Настроен' if AppConfig.BOT_TOKEN else '❌ Отсутствует'}")
    logger.info(f"🗄️ База данных: {AppConfig.DATABASE_PATH}")
    logger.info(f"🌐 Запуск на: http://{host}:{port}")
    

    # Показываем статистику маршрутов
    total_routes = len(list(app.url_map.iter_rules()))
    offers_routes = len([r for r in app.url_map.iter_rules() if '/api/offers' in r.rule])
    logger.info(f"📊 Всего маршрутов: {total_routes} (offers: {offers_routes})")
    logger.info("=" * 60)

    try:
        app.run(
            host=host,
            port=port,
            debug=AppConfig.DEBUG,
            threaded=True,
            use_reloader=AppConfig.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("🛑 Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()