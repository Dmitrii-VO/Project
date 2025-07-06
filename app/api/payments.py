from flask import Blueprint, request, jsonify
from app.services.auth_service import auth_service
from app.utils.decorators import require_telegram_auth
from app.models.database import db_manager
from app.config.telegram_config import AppConfig
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)
payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/stats', methods=['GET'])
@require_telegram_auth
def get_payment_stats():
    """Получение статистики платежей пользователя"""
    try:
        if not AppConfig.PAYMENTS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система платежей отключена'}), 503

        telegram_user_id = auth_service.get_current_user_id()

        # Статистика выплат (входящие)
        payout_stats = db_manager.execute_query('''
                                                SELECT COUNT(*)                                                   as total_count,
                                                       SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_amount,
                                                       COUNT(CASE WHEN status = 'pending' THEN 1 END)             as pending_count,
                                                       COUNT(CASE WHEN status = 'completed' THEN 1 END)           as completed_count,
                                                       COUNT(CASE WHEN status = 'failed' THEN 1 END)              as failed_count
                                                FROM payouts p
                                                         JOIN users u ON p.recipient_id = u.id
                                                WHERE u.telegram_id = ?
                                                ''', (telegram_user_id,), fetch_one=True)

        # Статистика эскроу (исходящие)
        escrow_stats = db_manager.execute_query('''
                                                SELECT COUNT(*)                                                        as total_escrows,
                                                       SUM(CASE WHEN status = 'funds_held' THEN amount ELSE 0 END)     as held_amount,
                                                       SUM(CASE WHEN status = 'funds_released' THEN amount ELSE 0 END) as released_amount,
                                                       COUNT(CASE WHEN status = 'disputed' THEN 1 END)                 as disputed_count
                                                FROM escrow_transactions et
                                                         JOIN offers o ON et.offer_id = o.id
                                                         JOIN users u ON o.created_by = u.id
                                                WHERE u.telegram_id = ?
                                                ''', (telegram_user_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'payments': payout_stats or {},
            'escrow': escrow_stats or {}
        })

    except Exception as e:
        logger.error(f"Ошибка получения статистики платежей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/create-escrow', methods=['POST'])
@require_telegram_auth
def create_escrow():
    """Создание эскроу-транзакции"""
    try:
        if not AppConfig.PAYMENTS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система платежей отключена'}), 503

        telegram_user_id = auth_service.get_current_user_id()
        data = request.get_json()

        offer_id = data.get('offer_id')
        amount = float(data.get('amount', 0))
        recipient_user_id = data.get('recipient_user_id')

        if not all([offer_id, amount > 0, recipient_user_id]):
            return jsonify({
                'success': False,
                'error': 'Необходимы: offer_id, amount, recipient_user_id'
            }), 400

        # Проверяем права на оффер
        offer = db_manager.execute_query('''
                                         SELECT o.*, u.telegram_id
                                         FROM offers o
                                                  JOIN users u ON o.created_by = u.id
                                         WHERE o.id = ?
                                           AND u.telegram_id = ?
                                         ''', (offer_id, telegram_user_id), fetch_one=True)

        if not offer:
            return jsonify({
                'success': False,
                'error': 'Оффер не найден или нет прав доступа'
            }), 404

        # Создаем эскроу
        escrow_id = db_manager.execute_query('''
                                             INSERT INTO escrow_transactions (offer_id, recipient_id, amount, status, created_at, expires_at)
                                             VALUES (?, ?, ?, 'funds_held', ?, ?)
                                             ''', (
                                                 offer_id,
                                                 recipient_user_id,
                                                 amount,
                                                 datetime.now(),
                                                 datetime.now() + timedelta(days=7)
                                             ))

        logger.info(f"Создана эскроу-транзакция {escrow_id} для оффера {offer_id}")

        return jsonify({
            'success': True,
            'escrow_id': escrow_id,
            'message': 'Эскроу-транзакция создана успешно'
        })

    except Exception as e:
        logger.error(f"Ошибка создания эскроу: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500