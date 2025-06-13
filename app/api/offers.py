from flask import Blueprint, request, jsonify
from app.services.auth_service import auth_service
from app.utils.decorators import require_telegram_auth
from app.models.database import db_manager
from app.config.settings import Config
import logging

logger = logging.getLogger(__name__)
offers_bp = Blueprint('offers', __name__)


@offers_bp.route('', methods=['POST'])
@require_telegram_auth
def create_offer():
    """Создание нового оффера"""
    try:
        if not Config.OFFERS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        telegram_user_id = auth_service.get_current_user_id()

        # Импортируем функцию создания оффера
        try:
            from add_offer import add_offer
            result = add_offer(telegram_user_id, data)

            if result['success']:
                logger.info(f"Создан новый оффер {result.get('offer_id')} пользователем {telegram_user_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/my', methods=['GET'])
@require_telegram_auth
def get_my_offers():
    """Получение моих офферов"""
    try:
        if not Config.OFFERS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        telegram_user_id = auth_service.get_current_user_id()
        status = request.args.get('status')

        try:
            from add_offer import get_user_offers
            offers = get_user_offers(telegram_user_id, status)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})

        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500


@offers_bp.route('/detail/<int:offer_id>', methods=['GET'])
@require_telegram_auth
def get_offer_detail(offer_id):
    """Получение детальной информации об оффере"""
    try:
        if not Config.OFFERS_SYSTEM_ENABLED:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        include_responses = request.args.get('include_responses', 'false').lower() == 'true'

        try:
            from add_offer import get_offer_by_id
            offer = get_offer_by_id(offer_id, include_responses)

            if offer:
                return jsonify({'success': True, 'offer': offer})
            else:
                return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500


@offers_bp.route('/stats', methods=['GET'])
@require_telegram_auth
def get_offers_stats():
    """Статистика офферов пользователя"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        # Получаем ID пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        user_db_id = user['id']

        # Статистика офферов
        stats_queries = {
            'total_offers': '''SELECT COUNT(*) as count
                               FROM offers
                               WHERE created_by = ?''',
            'active_offers': '''SELECT COUNT(*) as count
                                FROM offers
                                WHERE created_by = ? AND status = 'active' ''',
            'total_spent': '''SELECT COALESCE(SUM(price), 0) as total
                              FROM offers
                              WHERE created_by = ?
                                AND status IN ('completed', 'active')'''
        }

        stats = {}
        for key, query in stats_queries.items():
            result = db_manager.execute_query(query, (user_db_id,), fetch_one=True)
            if key == 'total_spent':
                stats[key] = float(result['total']) if result else 0
            else:
                stats[key] = result['count'] if result else 0

        # Статистика откликов
        if Config.RESPONSES_SYSTEM_ENABLED:
            response_stats = db_manager.execute_query('''
                                                      SELECT COUNT(*)                                                as total_responses,
                                                             COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_responses
                                                      FROM offer_responses or_resp
                                                               JOIN offers o ON or_resp.offer_id = o.id
                                                      WHERE o.created_by = ?
                                                      ''', (user_db_id,), fetch_one=True)

            stats.update({
                'total_responses': response_stats['total_responses'] if response_stats else 0,
                'accepted_responses': response_stats['accepted_responses'] if response_stats else 0
            })
        else:
            stats.update({
                'total_responses': 0,
                'accepted_responses': 0
            })

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Ошибка получения статистики офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения статистики'}), 500