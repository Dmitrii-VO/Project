# app/services/telegram_webhooks.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import os
import json
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')

# Создаем Blueprint для webhook'ов
webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')


@webhooks_bp.route('/payment', methods=['POST'])
def payment_webhook():
    """Webhook для обработки платежей от Telegram"""
    try:
        data = request.get_json()
        logger.info(f"Получен webhook платежа: {data}")

        # Здесь будет логика обработки платежей
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Ошибка обработки webhook платежа: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@webhooks_bp.route('/bot', methods=['POST'])
def bot_webhook():
    """Основной webhook для бота"""
    try:
        data = request.get_json()
        logger.info(f"Получен webhook бота: {data}")

        # Здесь будет логика обработки сообщений бота
        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Ошибка обработки webhook бота: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@webhooks_bp.route('/status')
def webhook_status():
    """Статус webhook системы"""
    return jsonify({
        'status': 'active',
        'bot_token_configured': bool(BOT_TOKEN),
        'webhook_secret_configured': bool(WEBHOOK_SECRET)
    })


def register_webhook_routes(app):
    """Регистрация webhook маршрутов в Flask приложении"""
    app.register_blueprint(webhooks_bp)
    logger.info("✅ Webhook маршруты зарегистрированы")
    return True


# Экспорт функций
__all__ = ['register_webhook_routes']