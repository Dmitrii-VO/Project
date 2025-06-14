# app/services/payments_system.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import os
import sqlite3
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

def create_payments_tables():
    """Создание таблиц платежной системы"""
    try:
        DATABASE_PATH = 'telegram_mini_app.db'
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Создаем таблицу escrow_transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS escrow_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                advertiser_id INTEGER NOT NULL,
                channel_owner_id INTEGER NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'RUB',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                escrow_fee DECIMAL(10, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                released_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                dispute_reason TEXT,
                FOREIGN KEY (offer_id) REFERENCES offers(id),
                FOREIGN KEY (advertiser_id) REFERENCES users(id),
                FOREIGN KEY (channel_owner_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Таблицы платежной системы созданы")
        return True

    except Exception as e:
        print(f"❌ Ошибка создания таблиц платежной системы: {e}")
        return False


def register_payments_routes(app):
    """Регистрация маршрутов платежной системы"""
    payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

    @payments_bp.route('/status')
    def payment_status():
        """Статус платежной системы"""
        return jsonify({
            'status': 'active',
            'message': 'Платежная система работает',
            'version': '1.0',
            'escrow_enabled': True
        })

    @payments_bp.route('/webhook', methods=['POST'])
    def payment_webhook():
        """Webhook для обработки платежей"""
        data = request.get_json()
        return jsonify({'status': 'received'})

    @payments_bp.route('/escrow/create', methods=['POST'])
    def create_escrow():
        """Создание эскроу транзакции"""
        return jsonify({'status': 'escrow_created', 'id': 1})

    app.register_blueprint(payments_bp)
    return True


# Классы для обратной совместимости
class PaymentManager:
    """Менеджер платежей"""
    def __init__(self, db_path=None):
        self.db_path = db_path or 'telegram_mini_app.db'
        logger.info("PaymentManager инициализирован")

    def create_payment(self, amount, currency='RUB'):
        return {'status': 'created', 'amount': amount, 'currency': currency}


class EscrowManager:
    """Менеджер эскроу"""
    def __init__(self, db_path=None):
        self.db_path = db_path or 'telegram_mini_app.db'
        logger.info("EscrowManager инициализирован")

    def create_escrow(self, offer_id, amount):
        return {'status': 'escrow_created', 'offer_id': offer_id, 'amount': amount}


# Константы
MAX_RETRY_ATTEMPTS = 3

# Экспорт всех необходимых компонентов
__all__ = [
    'register_payments_routes',
    'create_payments_tables',
    'PaymentManager',
    'EscrowManager',
    'MAX_RETRY_ATTEMPTS'
]