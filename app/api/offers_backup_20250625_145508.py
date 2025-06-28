from datetime import datetime

from flask import Blueprint, request, jsonify
from app.services.auth_service import auth_service
from app.utils.decorators import require_telegram_auth
from app.models.database import db_manager
from app.config.settings import Config
import logging

logger = logging.getLogger(__name__)
offers_bp = Blueprint('offers', __name__)


@offers_bp.route('', methods=['POST'])
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


@offers_bp.route('/available', methods=['GET'])
def get_available_offers():
    """Получение доступных офферов для владельцев каналов"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        min_budget = request.args.get('min_budget', type=float)
        max_budget = request.args.get('max_budget', type=float)

        offset = (page - 1) * limit

        # Базовый запрос для активных офферов
        query = '''
                SELECT o.*, \
                       u.username, \
                       u.first_name,
                       COUNT(DISTINCT or_resp.id) as response_count
                FROM offers o
                         JOIN users u ON o.created_by = u.id
                         LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                WHERE o.status = 'active' \
                '''
        params = []

        # Добавляем фильтры
        if category:
            query += ' AND (o.target_audience LIKE ? OR o.requirements LIKE ?)'
            params.extend([f'%{category}%', f'%{category}%'])

        if min_budget:
            query += ' AND o.price >= ?'
            params.append(min_budget)

        if max_budget:
            query += ' AND o.price <= ?'
            params.append(max_budget)

        query += '''
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])

        offers = db_manager.execute_query(query, tuple(params), fetch_all=True)

        # Подсчитываем общее количество
        count_query = '''
                      SELECT COUNT(DISTINCT o.id)
                      FROM offers o
                      WHERE o.status = 'active' \
                      '''
        count_params = []

        if category:
            count_query += ' AND (o.target_audience LIKE ? OR o.requirements LIKE ?)'
            count_params.extend([f'%{category}%', f'%{category}%'])

        if min_budget:
            count_query += ' AND o.price >= ?'
            count_params.append(min_budget)

        if max_budget:
            count_query += ' AND o.price <= ?'
            count_params.append(max_budget)

        total_count = db_manager.execute_query(count_query, tuple(count_params), fetch_one=True)[0]

        return jsonify({
            'success': True,
            'offers': offers or [],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500


@offers_bp.route('/<int:offer_id>/respond', methods=['POST'])
@require_telegram_auth
def respond_to_offer(offer_id):
    """Откликнуться на оффер"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        telegram_user_id = auth_service.get_current_user_id()

        # Получаем ID пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        user_db_id = user['id']

        # Проверяем существование оффера
        offer = db_manager.execute_query(
            'SELECT id, title, created_by FROM offers WHERE id = ? AND status = "active"',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден или неактивен'}), 404

        # Проверяем, что пользователь не автор оффера
        if offer['created_by'] == user_db_id:
            return jsonify({'success': False, 'error': 'Нельзя откликнуться на собственный оффер'}), 400

        # Проверяем, есть ли уже отклик
        existing_response = db_manager.execute_query(
            'SELECT id FROM offer_responses WHERE offer_id = ? AND user_id = ?',
            (offer_id, user_db_id),
            fetch_one=True
        )

        if existing_response:
            return jsonify({'success': False, 'error': 'Вы уже откликнулись на этот оффер'}), 400

        # Создаем отклик
        response_message = data.get('message', '').strip()
        proposed_date = data.get('proposed_date')
        counter_price = data.get('counter_price')

        response_id = db_manager.execute_query('''
                                               INSERT INTO offer_responses (offer_id, user_id, status, response_message,
                                                                            proposed_date, counter_price, created_at)
                                               VALUES (?, ?, 'pending', ?, ?, ?, ?)
                                               ''', (
                                                   offer_id, user_db_id, response_message,
                                                   proposed_date, counter_price, datetime.now().isoformat()
                                               ))

        logger.info(f"Создан отклик {response_id} на оффер {offer_id} от пользователя {telegram_user_id}")

        return jsonify({
            'success': True,
            'response_id': response_id,
            'message': 'Отклик успешно отправлен'
        }), 201

    except Exception as e:
        logger.error(f"Ошибка создания отклика на оффер {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка отправки отклика'}), 500


@offers_bp.route('/<int:offer_id>/responses/<int:response_id>/accept', methods=['PUT'])
@require_telegram_auth
def accept_offer_response(offer_id, response_id):
    """Принять отклик на оффер"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        # Получаем ID пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        user_db_id = user['id']

        # Проверяем права на принятие отклика
        offer = db_manager.execute_query(
            'SELECT id, title, created_by FROM offers WHERE id = ? AND created_by = ?',
            (offer_id, user_db_id),
            fetch_one=True
        )

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден или у вас нет прав'}), 403

        # Проверяем существование отклика
        response = db_manager.execute_query(
            'SELECT id, status FROM offer_responses WHERE id = ? AND offer_id = ?',
            (response_id, offer_id),
            fetch_one=True
        )

        if not response:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        if response['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Отклик уже обработан'}), 400

        # Принимаем отклик
        db_manager.execute_query('''
                                 UPDATE offer_responses
                                 SET status     = 'accepted',
                                     updated_at = ?
                                 WHERE id = ?
                                 ''', (datetime.now().isoformat(), response_id))

        # Отклоняем все остальные отклики на этот оффер
        db_manager.execute_query('''
                                 UPDATE offer_responses
                                 SET status     = 'rejected',
                                     updated_at = ?
                                 WHERE offer_id = ?
                                   AND id != ? AND status = 'pending'
                                 ''', (datetime.now().isoformat(), offer_id, response_id))

        # Меняем статус оффера на завершенный
        db_manager.execute_query('''
                                 UPDATE offers
                                 SET status     = 'completed',
                                     updated_at = ?
                                 WHERE id = ?
                                 ''', (datetime.now().isoformat(), offer_id))

        logger.info(f"Принят отклик {response_id} на оффер {offer_id}")

        return jsonify({
            'success': True,
            'message': 'Отклик принят'
        })

    except Exception as e:
        logger.error(f"Ошибка принятия отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка принятия отклика'}), 500

@offers_bp.route('/test', methods=['GET'])
def test_offers_api():
    """Тестовый endpoint для проверки API офферов"""
    return jsonify({
        'success': True,
        'message': 'API офферов работает!',
        'timestamp': datetime.now().isoformat()
    })

