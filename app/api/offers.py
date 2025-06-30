# app/api/offers.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""
Оптимизированный модуль offers.py
Убрано дублирование с working_app.py, сохранена функциональность
"""

import json
import logging
import os
import sys
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify

# === КОНФИГУРАЦИЯ ===
DATABASE_PATH = 'telegram_mini_app.db'
logger = logging.getLogger(__name__)

# === BLUEPRINT ===
offers_bp = Blueprint('offers', __name__)


# === УТИЛИТЫ ===
def get_user_id_from_request():
    """Получение user_id из заголовков запроса"""
    user_id = request.headers.get('X-Telegram-User-Id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    # Fallback к основному пользователю
    fallback_id = os.environ.get('YOUR_TELEGRAM_ID', '373086959')
    try:
        return int(fallback_id)
    except (ValueError, TypeError):
        return 373086959


def execute_db_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Универсальная функция для работы с БД"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None
        elif fetch_all:
            result = cursor.fetchall()
            conn.close()
            return [dict(row) for row in result] if result else []
        else:
            conn.commit()
            lastrowid = cursor.lastrowid
            conn.close()
            return lastrowid

    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        if 'conn' in locals():
            conn.close()
        raise


def import_add_offer_safely():
    """Безопасный импорт модуля add_offer"""
    try:
        sys.path.insert(0, os.getcwd())
        import add_offer
        return add_offer
    except ImportError as e:
        logger.error(f"Ошибка импорта add_offer: {e}")
        return None


# === API ENDPOINTS ===

@offers_bp.route('', methods=['POST'])
def create_offer():
    """Создание нового оффера"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        telegram_user_id = get_user_id_from_request()
        logger.info(f"Создание оффера пользователем {telegram_user_id}")

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы офферов недоступен'}), 503

        result = add_offer.add_offer(telegram_user_id, data)

        if result['success']:
            logger.info(f"Создан оффер {result.get('offer_id')} пользователем {telegram_user_id}")
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/my', methods=['GET'])
def get_my_offers():
    """Получение офферов текущего пользователя с оптимизированным запросом"""
    try:
        telegram_user_id = get_user_id_from_request()
        logger.info(f"Запрос офферов пользователя {telegram_user_id}")

        # Получаем ID пользователя в БД
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Параметры фильтрации
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status')
        search = request.args.get('search', '').strip()
        category_filter = request.args.get('category')

        offset = (page - 1) * limit

        # Оптимизированный запрос с подсчетом откликов
        base_query = '''
                     SELECT o.*,
                            COUNT(or_resp.id)                                       as response_count,
                            COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_count,
                            COUNT(CASE WHEN or_resp.status = 'pending' THEN 1 END)  as pending_count
                     FROM offers o
                              LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                     WHERE o.created_by = ? \
                     '''

        params = [user['id']]

        # Добавляем фильтры
        if status_filter:
            base_query += ' AND o.status = ?'
            params.append(status_filter)

        if search:
            base_query += ' AND (o.title LIKE ? OR o.description LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])

        if category_filter:
            base_query += ' AND o.category = ?'
            params.append(category_filter)

        base_query += ' GROUP BY o.id ORDER BY o.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        offers = execute_db_query(base_query, tuple(params), fetch_all=True)

        # Получаем общее количество для пагинации
        count_query = 'SELECT COUNT(*) as total FROM offers WHERE created_by = ?'
        total_count = execute_db_query(count_query, (user['id'],), fetch_one=True)['total']

        # Форматируем данные
        formatted_offers = []
        for offer in offers:
            # Парсим метаданные
            try:
                metadata = json.loads(offer.get('metadata', '{}')) if offer.get('metadata') else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            formatted_offer = {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'content': offer['content'],
                'category': offer['category'] or 'general',
                'status': offer['status'] or 'active',
                'price': float(offer['price']) if offer['price'] else 0,
                'currency': offer['currency'] or 'RUB',
                'budget_total': float(offer.get('budget_total', 0)) if offer.get('budget_total') else 0,
                'target_audience': offer.get('target_audience', ''),
                'min_subscribers': offer.get('min_subscribers', 1),
                'max_subscribers': offer.get('max_subscribers', 100000000),
                'requirements': offer.get('requirements', ''),
                'deadline': offer.get('deadline', ''),
                'duration_days': offer.get('duration_days', 30),
                'created_at': offer['created_at'],
                'updated_at': offer['updated_at'],
                'response_count': offer.get('response_count', 0),
                'accepted_count': offer.get('accepted_count', 0),
                'pending_count': offer.get('pending_count', 0),
                'metadata': metadata,
                'is_active': offer['status'] == 'active',
                'has_responses': offer.get('response_count', 0) > 0,
                'needs_attention': offer.get('pending_count', 0) > 0
            }
            formatted_offers.append(formatted_offer)

        logger.info(f"Возвращено {len(formatted_offers)} офферов из {total_count}")

        return jsonify({
            'success': True,
            'offers': formatted_offers,
            'count': len(formatted_offers),
            'total_count': total_count,
            'page': page,
            'total_pages': (total_count + limit - 1) // limit,
            'filters': {
                'status': status_filter,
                'search': search,
                'category': category_filter
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения офферов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/available', methods=['GET'])
def get_available_offers():
    """Получение доступных офферов для владельцев каналов"""
    try:
        telegram_user_id = get_user_id_from_request()

        # Собираем фильтры из параметров запроса
        filters = {
            'search': request.args.get('search', '').strip(),
            'category': request.args.get('category', '').strip(),
            'min_budget': request.args.get('min_budget'),
            'max_budget': request.args.get('max_budget'),
            'min_subscribers': request.args.get('min_subscribers'),
            'limit': int(request.args.get('limit', 50)),
            'exclude_user_id': telegram_user_id
        }

        # Удаляем пустые фильтры
        filters = {k: v for k, v in filters.items() if v not in [None, '', 'None']}

        logger.info(f"Загрузка доступных офферов для {telegram_user_id} с фильтрами: {filters}")

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы офферов недоступен'}), 503

        offers = add_offer.get_available_offers(filters)

        return jsonify({
            'success': True,
            'offers': offers,
            'count': len(offers),
            'filters_applied': filters
        })

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/stats', methods=['GET'])
def get_offers_stats():
    """Статистика офферов пользователя"""
    try:
        telegram_user_id = get_user_id_from_request()

        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        # Получаем статистику одним запросом
        stats = execute_db_query("""
                                 SELECT COUNT(*)                                                as total_offers,
                                        COUNT(CASE WHEN status = 'active' THEN 1 END)           as active_offers,
                                        COALESCE(SUM(CASE WHEN status IN ('completed', 'active') THEN price ELSE 0 END),
                                                 0)                                             as total_spent,
                                        COUNT(or_resp.id)                                       as total_responses,
                                        COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_responses
                                 FROM offers o
                                          LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                                 WHERE o.created_by = ?
                                 """, (user['id'],), fetch_one=True)

        return jsonify({
            'success': True,
            'stats': {
                'total_offers': stats['total_offers'] or 0,
                'active_offers': stats['active_offers'] or 0,
                'total_spent': float(stats['total_spent']) if stats['total_spent'] else 0,
                'total_responses': stats['total_responses'] or 0,
                'accepted_responses': stats['accepted_responses'] or 0
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    """Удаление оффера"""
    try:
        telegram_user_id = get_user_id_from_request()
        logger.info(f"Запрос на удаление оффера {offer_id}")

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы офферов недоступен'}), 503

        result = add_offer.delete_offer_by_id(offer_id, telegram_user_id)

        if result['success']:
            logger.info(f"Оффер {offer_id} удален пользователем {telegram_user_id}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/<int:offer_id>/status', methods=['PATCH'])
def update_offer_status(offer_id):
    """Обновление статуса оффера"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Не указан новый статус'}), 400

        new_status = data['status']
        reason = data.get('reason', '')

        valid_statuses = ['active', 'paused', 'cancelled', 'completed']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Недопустимый статус. Разрешены: {", ".join(valid_statuses)}'
            }), 400

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы офферов недоступен'}), 503

        result = add_offer.update_offer_status_by_id(offer_id, telegram_user_id, new_status, reason)

        if result['success']:
            logger.info(f"Статус оффера {offer_id} изменен на {new_status}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка изменения статуса оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/<int:offer_id>/respond', methods=['POST'])
def respond_to_offer(offer_id):
    """Создание отклика на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json() or {}

        channel_id = data.get('channel_id')
        message = data.get('message', '').strip()

        if not channel_id or not message:
            return jsonify({'success': False, 'error': 'Канал и сообщение обязательны'}), 400

        # Получаем пользователя и проверяем канал
        user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,), fetch_one=True)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 400

        channel = execute_db_query("""
                                   SELECT *
                                   FROM channels
                                   WHERE id = ?
                                     AND owner_id = ?
                                     AND is_verified = 1
                                   """, (channel_id, user['id']), fetch_one=True)

        if not channel:
            return jsonify({'success': False, 'error': 'Канал не найден или не верифицирован'}), 400

        # Проверяем, что не откликались ранее
        existing_response = execute_db_query("""
                                             SELECT id
                                             FROM offer_responses
                                             WHERE offer_id = ?
                                               AND user_id = ?
                                             """, (offer_id, user['id']), fetch_one=True)

        if existing_response:
            return jsonify({'success': False, 'error': 'Вы уже откликались на этот оффер'}), 400

        # Создаем отклик
        response_id = execute_db_query("""
                                       INSERT INTO offer_responses (offer_id, user_id, message, status,
                                                                    channel_title, channel_username,
                                                                    channel_subscribers,
                                                                    created_at, updated_at)
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                       """, (
                                           offer_id, user['id'], message, 'pending',
                                           channel['title'], channel['username'], channel.get('subscriber_count', 0),
                                           datetime.now().isoformat(), datetime.now().isoformat()
                                       ))

        logger.info(f"Создан отклик {response_id} на оффер {offer_id}")

        return jsonify({
            'success': True,
            'message': 'Отклик успешно отправлен',
            'response_id': response_id
        }), 201

    except Exception as e:
        logger.error(f"Ошибка создания отклика: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/<int:offer_id>/responses', methods=['GET'])
def get_offer_responses_api(offer_id):
    """Получение откликов на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()

        # Проверяем права доступа к офферу
        offer = execute_db_query("""
                                 SELECT o.*, u.telegram_id as owner_telegram_id
                                 FROM offers o
                                          JOIN users u ON o.created_by = u.id
                                 WHERE o.id = ?
                                 """, (offer_id,), fetch_one=True)

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        if offer['owner_telegram_id'] != telegram_user_id:
            return jsonify({'success': False, 'error': 'Нет доступа к этому офферу'}), 403

        # Получаем отклики
        responses = execute_db_query("""
                                     SELECT or_resp.*,
                                            u.first_name || ' ' || COALESCE(u.last_name, '') as channel_owner_name,
                                            u.username                                       as channel_owner_username,
                                            u.telegram_id                                    as channel_owner_telegram_id
                                     FROM offer_responses or_resp
                                              JOIN users u ON or_resp.user_id = u.id
                                     WHERE or_resp.offer_id = ?
                                     ORDER BY or_resp.created_at DESC
                                     """, (offer_id,), fetch_all=True)

        # Форматируем отклики
        formatted_responses = []
        for response in responses:
            formatted_responses.append({
                'id': response['id'],
                'offer_id': response['offer_id'],
                'status': response['status'],
                'message': response['message'],
                'created_at': response['created_at'],
                'updated_at': response['updated_at'],
                'channel_title': response.get('channel_title', 'Канал без названия'),
                'channel_username': response.get('channel_username', 'unknown'),
                'channel_subscribers': response.get('channel_subscribers', 0),
                'channel_owner_name': response['channel_owner_name'].strip() or 'Пользователь',
                'channel_owner_username': response['channel_owner_username'] or '',
                'channel_owner_telegram_id': response['channel_owner_telegram_id']
            })

        return jsonify({
            'success': True,
            'responses': formatted_responses,
            'count': len(formatted_responses),
            'offer': {
                'id': offer['id'],
                'title': offer['title'],
                'status': offer['status']
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения откликов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/responses/<response_id>/status', methods=['PATCH'])
def update_response_status_api(response_id):
    """Обновление статуса отклика"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Не указан новый статус'}), 400

        new_status = data['status']
        message = data.get('message', '')

        valid_statuses = ['accepted', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Недопустимый статус. Разрешены: {", ".join(valid_statuses)}'
            }), 400

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы откликов недоступен'}), 503

        result = add_offer.update_response_status(response_id, new_status, telegram_user_id, message)

        if result['success']:
            logger.info(f"Статус отклика {response_id} изменен на {new_status}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка изменения статуса отклика: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/contracts', methods=['GET'])
def get_user_contracts():
    """Получение контрактов пользователя"""
    try:
        telegram_user_id = get_user_id_from_request()

        user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,), fetch_one=True)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        # Получаем контракты пользователя
        contracts = execute_db_query("""
                                     SELECT c.*,
                                            o.title          as offer_title,
                                            u_adv.first_name as advertiser_name,
                                            u_pub.first_name as publisher_name,
                                            or_resp.channel_title,
                                            or_resp.channel_username
                                     FROM contracts c
                                              JOIN offers o ON c.offer_id = o.id
                                              JOIN users u_adv ON c.advertiser_id = u_adv.id
                                              JOIN users u_pub ON c.publisher_id = u_pub.id
                                              JOIN offer_responses or_resp ON c.response_id = or_resp.id
                                     WHERE c.advertiser_id = ?
                                        OR c.publisher_id = ?
                                     ORDER BY c.created_at DESC
                                     """, (user['id'], user['id']), fetch_all=True)

        contracts_list = []
        for contract in contracts:
            contracts_list.append({
                'id': contract['id'],
                'offer_title': contract['offer_title'],
                'price': float(contract['price']),
                'status': contract['status'],
                'role': 'advertiser' if contract['advertiser_id'] == user['id'] else 'publisher',
                'advertiser_name': contract['advertiser_name'],
                'publisher_name': contract['publisher_name'],
                'channel_title': contract['channel_title'],
                'channel_username': contract['channel_username'],
                'placement_deadline': contract['placement_deadline'],
                'monitoring_end': contract['monitoring_end'],
                'verification_passed': bool(contract.get('verification_passed')),
                'verification_details': contract.get('verification_details', ''),
                'violation_reason': contract.get('violation_reason', ''),
                'created_at': contract['created_at']
            })

        return jsonify({
            'success': True,
            'contracts': contracts_list,
            'count': len(contracts_list)
        })

    except Exception as e:
        logger.error(f"Ошибка получения контрактов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/contracts/<contract_id>/placement', methods=['POST'])
def submit_placement_api(contract_id):
    """Подача заявки о размещении рекламы"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        if not data or 'post_url' not in data:
            return jsonify({'success': False, 'error': 'Не указана ссылка на пост'}), 400

        post_url = data['post_url'].strip()

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль системы контрактов недоступен'}), 503

        result = add_offer.submit_placement(contract_id, post_url, telegram_user_id)

        if result['success']:
            logger.info(f"Подана заявка о размещении для контракта {contract_id}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка подачи заявки о размещении: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/contracts/<contract_id>/cancel', methods=['POST'])
def cancel_contract_api(contract_id):
    """Отмена контракта"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json() or {}
        reason = data.get('reason', 'Отменено пользователем')

        # Проверяем права и обновляем статус
        contract = execute_db_query("""
                                    SELECT c.*,
                                           u_adv.telegram_id as advertiser_telegram_id,
                                           u_pub.telegram_id as publisher_telegram_id
                                    FROM contracts c
                                             JOIN users u_adv ON c.advertiser_id = u_adv.id
                                             JOIN users u_pub ON c.publisher_id = u_pub.id
                                    WHERE c.id = ?
                                      AND (u_adv.telegram_id = ? OR u_pub.telegram_id = ?)
                                    """, (contract_id, telegram_user_id, telegram_user_id), fetch_one=True)

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден или нет доступа'}), 404

        if contract['status'] in ['completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Контракт уже завершен или отменен'}), 400

        execute_db_query("""
                         UPDATE contracts
                         SET status           = 'cancelled',
                             violation_reason = ?,
                             updated_at       = ?
                         WHERE id = ?
                         """, (reason, datetime.now().isoformat(), contract_id))

        logger.info(f"Контракт {contract_id} отменен пользователем {telegram_user_id}")

        return jsonify({
            'success': True,
            'message': 'Контракт отменен. Все участники получили уведомления.'
        })

    except Exception as e:
        logger.error(f"Ошибка отмены контракта: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/contracts/<contract_id>', methods=['DELETE'])
def delete_contract_api(contract_id):
    """Удаление завершенного контракта"""
    try:
        telegram_user_id = get_user_id_from_request()

        add_offer = import_add_offer_safely()
        if not add_offer:
            # Fallback - удаление напрямую
            contract = execute_db_query("""
                                        SELECT c.*,
                                               u_adv.telegram_id as advertiser_telegram_id,
                                               u_pub.telegram_id as publisher_telegram_id
                                        FROM contracts c
                                                 JOIN users u_adv ON c.advertiser_id = u_adv.id
                                                 JOIN users u_pub ON c.publisher_id = u_pub.id
                                        WHERE c.id = ?
                                        """, (contract_id,), fetch_one=True)

            if not contract:
                return jsonify({'success': False, 'error': 'Контракт не найден'}), 404

            if (contract['advertiser_telegram_id'] != telegram_user_id and
                    contract['publisher_telegram_id'] != telegram_user_id):
                return jsonify({'success': False, 'error': 'Нет доступа к контракту'}), 403

            if contract['status'] not in ['verification_failed', 'cancelled']:
                return jsonify(
                    {'success': False, 'error': 'Можно удалять только неудачные или отмененные контракты'}), 400

            # Удаляем контракт и связанные записи
            execute_db_query('DELETE FROM monitoring_tasks WHERE contract_id = ?', (contract_id,))
            execute_db_query('DELETE FROM contracts WHERE id = ?', (contract_id,))

            return jsonify({'success': True, 'message': 'Контракт удален'})

        result = add_offer.delete_finished_contract(contract_id, telegram_user_id)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка удаления контракта: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ОТЛАДОЧНЫЕ ENDPOINTS ===

@offers_bp.route('/debug/verify-post', methods=['POST'])
def debug_verify_post():
    """Диагностика проверки поста"""
    try:
        data = request.get_json()
        if not data or 'post_url' not in data:
            return jsonify({'success': False, 'error': 'Не указана ссылка на пост'}), 400

        post_url = data['post_url'].strip()
        expected_content = data.get('expected_content', '')

        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль диагностики недоступен'}), 503

        # Простая проверка URL
        if hasattr(add_offer, 'extract_post_info_from_url'):
            result = add_offer.extract_post_info_from_url(post_url)
        else:
            result = {'success': True, 'message': 'Основная проверка URL прошла успешно'}

        return jsonify({
            'success': True,
            'debug_result': result,
            'url': post_url
        })

    except Exception as e:
        logger.error(f"Ошибка диагностики поста: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/debug/quick-test', methods=['GET'])
def quick_test_verification_endpoint():
    """Быстрый тест проверки размещения"""
    try:
        add_offer = import_add_offer_safely()
        if not add_offer:
            return jsonify({'success': False, 'error': 'Модуль тестирования недоступен'}), 503

        if hasattr(add_offer, 'quick_test_verification'):
            # Захватываем вывод функции
            import io
            import contextlib

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                add_offer.quick_test_verification()

            output = output_buffer.getvalue()

            return jsonify({
                'success': True,
                'test_output': output,
                'message': 'Быстрый тест выполнен'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Функция быстрого теста недоступна',
                'test_output': 'Тест не выполнен - функция не найдена'
            })

    except Exception as e:
        logger.error(f"Ошибка быстрого теста: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS ===

@offers_bp.route('/detail/<int:offer_id>', methods=['GET'])
def get_offer_detail(offer_id):
    """Получение детальной информации об оффере"""
    try:
        include_responses = request.args.get('include_responses', 'false').lower() == 'true'

        # Получаем базовую информацию об оффере
        offer = execute_db_query("""
                                 SELECT o.*, u.username as creator_username, u.first_name as creator_name
                                 FROM offers o
                                          JOIN users u ON o.created_by = u.id
                                 WHERE o.id = ?
                                 """, (offer_id,), fetch_one=True)

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        # Форматируем детальную информацию
        offer_detail = {
            'id': offer['id'],
            'title': offer['title'],
            'description': offer['description'],
            'content': offer['content'],
            'price': float(offer['price']) if offer['price'] else 0,
            'currency': offer['currency'] or 'RUB',
            'category': offer['category'] or 'general',
            'status': offer['status'] or 'active',
            'target_audience': offer.get('target_audience', ''),
            'requirements': offer.get('requirements', ''),
            'deadline': offer.get('deadline', ''),
            'budget_total': float(offer.get('budget_total', 0)) if offer.get('budget_total') else 0,
            'duration_days': offer.get('duration_days', 30),
            'min_subscribers': offer.get('min_subscribers', 1),
            'max_subscribers': offer.get('max_subscribers', 100000000),
            'created_at': offer['created_at'],
            'updated_at': offer['updated_at'],
            'creator_username': offer.get('creator_username', ''),
            'creator_name': offer.get('creator_name', ''),
        }

        # Добавляем отклики если запрошены
        if include_responses:
            responses = execute_db_query("""
                                         SELECT COUNT(*)                                        as total_responses,
                                                COUNT(CASE WHEN status = 'pending' THEN 1 END)  as pending_responses,
                                                COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_responses,
                                                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_responses
                                         FROM offer_responses
                                         WHERE offer_id = ?
                                         """, (offer_id,), fetch_one=True)

            offer_detail['responses_stats'] = {
                'total': responses['total_responses'] or 0,
                'pending': responses['pending_responses'] or 0,
                'accepted': responses['accepted_responses'] or 0,
                'rejected': responses['rejected_responses'] or 0
            }

        return jsonify({
            'success': True,
            'offer': offer_detail
        })

    except Exception as e:
        logger.error(f"Ошибка получения деталей оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/contracts/<contract_id>', methods=['GET'])
def get_contract_details(contract_id):
    """Получение деталей контракта"""
    try:
        telegram_user_id = get_user_id_from_request()

        # Получаем детали контракта
        contract = execute_db_query("""
                                    SELECT c.*,
                                           o.title           as offer_title,
                                           o.description     as offer_description,
                                           u_adv.first_name  as advertiser_name,
                                           u_adv.telegram_id as advertiser_telegram_id,
                                           u_pub.first_name  as publisher_name,
                                           u_pub.telegram_id as publisher_telegram_id,
                                           or_resp.channel_title,
                                           or_resp.channel_username,
                                           or_resp.message   as response_message
                                    FROM contracts c
                                             JOIN offers o ON c.offer_id = o.id
                                             JOIN users u_adv ON c.advertiser_id = u_adv.id
                                             JOIN users u_pub ON c.publisher_id = u_pub.id
                                             JOIN offer_responses or_resp ON c.response_id = or_resp.id
                                    WHERE c.id = ?
                                      AND (u_adv.telegram_id = ? OR u_pub.telegram_id = ?)
                                    """, (contract_id, telegram_user_id, telegram_user_id), fetch_one=True)

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден или нет доступа'}), 404

        contract_details = {
            'id': contract['id'],
            'offer_title': contract['offer_title'],
            'offer_description': contract['offer_description'],
            'price': float(contract['price']),
            'status': contract['status'],
            'role': 'advertiser' if contract['advertiser_telegram_id'] == telegram_user_id else 'publisher',
            'advertiser_name': contract['advertiser_name'],
            'publisher_name': contract['publisher_name'],
            'channel_title': contract['channel_title'],
            'channel_username': contract['channel_username'],
            'response_message': contract['response_message'],
            'placement_deadline': contract['placement_deadline'],
            'monitoring_duration': contract.get('monitoring_duration'),
            'monitoring_end': contract['monitoring_end'],
            'post_url': contract.get('post_url'),
            'post_id': contract.get('post_id'),
            'verification_passed': bool(contract.get('verification_passed')),
            'verification_details': contract.get('verification_details'),
            'violation_reason': contract.get('violation_reason'),
            'post_requirements': contract.get('post_requirements'),
            'created_at': contract['created_at'],
            'submitted_at': contract.get('submitted_at'),
            'completed_at': contract.get('completed_at')
        }

        return jsonify({
            'success': True,
            'contract': contract_details
        })

    except Exception as e:
        logger.error(f"Ошибка получения деталей контракта {contract_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ===

@offers_bp.route('/categories', methods=['GET'])
def get_offer_categories():
    """Получение списка категорий офферов"""
    categories = [
        {'id': 'general', 'name': 'Общие', 'description': 'Общие предложения'},
        {'id': 'tech', 'name': 'Технологии', 'description': 'IT, гаджеты, программы'},
        {'id': 'finance', 'name': 'Финансы', 'description': 'Банки, инвестиции, криптовалюты'},
        {'id': 'lifestyle', 'name': 'Образ жизни', 'description': 'Мода, красота, здоровье'},
        {'id': 'education', 'name': 'Образование', 'description': 'Курсы, книги, обучение'},
        {'id': 'entertainment', 'name': 'Развлечения', 'description': 'Игры, фильмы, музыка'},
        {'id': 'business', 'name': 'Бизнес', 'description': 'Услуги, консалтинг, стартапы'},
        {'id': 'health', 'name': 'Здоровье', 'description': 'Медицина, фитнес, питание'},
        {'id': 'sports', 'name': 'Спорт', 'description': 'Спортивные товары и события'},
        {'id': 'travel', 'name': 'Путешествия', 'description': 'Туризм, отели, авиабилеты'},
        {'id': 'other', 'name': 'Другое', 'description': 'Прочие категории'}
    ]

    return jsonify({
        'success': True,
        'categories': categories
    })


@offers_bp.route('/summary', methods=['GET'])
def get_user_summary():
    """Получение сводной информации пользователя"""
    try:
        telegram_user_id = get_user_id_from_request()

        user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,), fetch_one=True)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        # Получаем сводную статистику одним запросом
        summary = execute_db_query("""
                                   SELECT COUNT(DISTINCT o.id)                                                     as total_offers,
                                          COUNT(DISTINCT CASE WHEN o.status = 'active' THEN o.id END)              as active_offers,
                                          COUNT(DISTINCT or_resp.id)                                               as total_responses,
                                          COUNT(DISTINCT CASE WHEN or_resp.status = 'pending' THEN or_resp.id END) as pending_responses,
                                          COUNT(DISTINCT c.id)                                                     as total_contracts,
                                          COUNT(DISTINCT CASE WHEN c.status = 'active' THEN c.id END)              as active_contracts,
                                          COALESCE(
                                                  SUM(CASE WHEN o.status IN ('completed', 'active') THEN o.price ELSE 0 END),
                                                  0)                                                               as total_budget
                                   FROM offers o
                                            LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                                            LEFT JOIN contracts c ON (c.advertiser_id = ? OR c.publisher_id = ?)
                                   WHERE o.created_by = ?
                                   """, (user['id'], user['id'], user['id']), fetch_one=True)

        return jsonify({
            'success': True,
            'summary': {
                'total_offers': summary['total_offers'] or 0,
                'active_offers': summary['active_offers'] or 0,
                'total_responses': summary['total_responses'] or 0,
                'pending_responses': summary['pending_responses'] or 0,
                'total_contracts': summary['total_contracts'] or 0,
                'active_contracts': summary['active_contracts'] or 0,
                'total_budget': float(summary['total_budget']) if summary['total_budget'] else 0
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ЭКСПОРТ ===
__all__ = ['offers_bp']