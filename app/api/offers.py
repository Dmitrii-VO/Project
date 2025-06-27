# app/api/offers.py - Исправленная версия для отображения офферов
from datetime import datetime

from flask import Blueprint, request, jsonify

from add_offer import send_telegram_message
from app.models.database import db_manager
from app.config.settings import Config
import logging
import os
import sys
import sqlite3
DATABASE_PATH = 'telegram_mini_app.db'
logger = logging.getLogger(__name__)
offers_bp = Blueprint('offers', __name__)

def get_user_id_from_request():
    """Получаем user_id из запроса (альтернатива auth_service)"""
    # Пробуем получить из заголовков
    user_id = request.headers.get('X-Telegram-User-Id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass
    
    # Пробуем получить из JSON данных
    data = request.get_json() or {}
    user_id = data.get('user_id') or data.get('telegram_user_id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass
    
    # Fallback к основному пользователю из .env
    fallback_id = os.environ.get('YOUR_TELEGRAM_ID')
    if fallback_id:
        try:
            return int(fallback_id)
        except (ValueError, TypeError):
            pass
    
    return None

@offers_bp.route('', methods=['POST'])
def create_offer():
    """Создание нового оффера"""
    try:
        # Проверяем что система включена
        offers_enabled = getattr(Config, 'OFFERS_SYSTEM_ENABLED', True)
        if not offers_enabled:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Импортируем функцию создания оффера
        try:
            # Добавляем путь к корню проекта
            sys.path.insert(0, os.getcwd())
            from add_offer import add_offer
            result = add_offer(telegram_user_id, data)

            if result['success']:
                logger.info(f"Создан новый оффер {result.get('offer_id')} пользователем {telegram_user_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта add_offer: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/my', methods=['GET'])
def get_my_offers():
    """Получение моих офферов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        logger.info("Запрос на получение моих офферов")
        
        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        logger.info(f"Определен user_id: {telegram_user_id}")
        
        if not telegram_user_id:
            return jsonify({
                'success': False, 
                'error': 'Не удалось определить пользователя',
                'debug_headers': dict(request.headers),
                'debug_env': os.environ.get('YOUR_TELEGRAM_ID')
            }), 400

        status = request.args.get('status')
        logger.info(f"Фильтр по статусу: {status}")

        try:
            # Добавляем путь к корню проекта
            sys.path.insert(0, os.getcwd())
            from add_offer import get_user_offers
            
            logger.info("Вызываем get_user_offers")
            offers = get_user_offers(telegram_user_id, status)
            logger.info(f"Получено офферов: {len(offers)}")
            
            return jsonify({
                'success': True, 
                'offers': offers, 
                'count': len(offers),
                'user_id': telegram_user_id
            })

        except ImportError as e:
            logger.error(f"Ошибка импорта get_user_offers: {e}")
            return jsonify({
                'success': False,
                'error': f'Модуль системы офферов недоступен: {str(e)}'
            }), 503
        except Exception as e:
            logger.error(f"Ошибка в get_user_offers: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Ошибка получения офферов: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Общая ошибка в get_my_offers: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500


@offers_bp.route('/detail/<int:offer_id>', methods=['GET'])
def get_offer_detail(offer_id):
    """Получение детальной информации об оффере"""
    try:
        include_responses = request.args.get('include_responses', 'false').lower() == 'true'

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import get_offer_by_id
            offer = get_offer_by_id(offer_id, include_responses)

            if offer:
                return jsonify({'success': True, 'offer': offer})
            else:
                return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        except ImportError as e:
            logger.error(f"Ошибка импорта get_offer_by_id: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500


@offers_bp.route('/stats', methods=['GET'])
def get_offers_stats():
    """Статистика офферов пользователя"""
    try:
        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

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
            'total_offers': """SELECT COUNT(*) as count
                               FROM offers
                               WHERE created_by = ?""",
            'active_offers': """SELECT COUNT(*) as count
                                FROM offers
                                WHERE created_by = ? AND status = 'active' """,
            'total_spent': """SELECT COALESCE(SUM(price), 0) as total
                              FROM offers
                              WHERE created_by = ?
                                AND status IN ('completed', 'active')"""
        }

        stats = {}
        for key, query in stats_queries.items():
            result = db_manager.execute_query(query, (user_db_id,), fetch_one=True)
            if key == 'total_spent':
                stats[key] = float(result['total']) if result else 0
            else:
                stats[key] = result['count'] if result else 0

        # Статистика откликов
        response_stats = db_manager.execute_query("""
            SELECT COUNT(*) as total_responses,
                   COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_responses
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            WHERE o.created_by = ?
        """, (user_db_id,), fetch_one=True)

        stats.update({
            'total_responses': response_stats['total_responses'] if response_stats else 0,
            'accepted_responses': response_stats['accepted_responses'] if response_stats else 0
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
    """Получение доступных офферов для владельцев каналов (исключая свои офферы)"""
    try:
        # Получаем user_id текущего пользователя
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        min_budget = request.args.get('min_budget', type=float)
        max_budget = request.args.get('max_budget', type=float)
        search = request.args.get('search', '').strip()
        min_subscribers = request.args.get('min_subscribers', type=int)

        filters = {
            'category': category,
            'min_budget': min_budget,
            'max_budget': max_budget,
            'search': search,
            'min_subscribers': min_subscribers,
            'limit': limit,
            'exclude_user_id': telegram_user_id  # Исключаем офферы текущего пользователя
        }

        # Убираем None значения
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}

        logger.info(f"Загрузка доступных офферов для пользователя {telegram_user_id} с фильтрами: {filters}")

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import get_available_offers
            offers = get_available_offers(filters)

            logger.info(f"Найдено доступных офферов: {len(offers)} (исключая офферы пользователя {telegram_user_id})")

            return jsonify({
                'success': True,
                'offers': offers,
                'count': len(offers),
                'current_user_id': telegram_user_id,
                'filters_applied': filters
            })

        except ImportError as e:
            logger.error(f"Ошибка импорта get_available_offers: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500

# Дополнительные маршруты для отладки
@offers_bp.route('/debug/user', methods=['GET', 'POST'])
def debug_current_user():
    """Отладочный маршрут для проверки текущего пользователя"""
    try:
        user_id = get_user_id_from_request()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'headers': dict(request.headers),
            'method': request.method,
            'args': dict(request.args),
            'env_telegram_id': os.environ.get('YOUR_TELEGRAM_ID')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@offers_bp.route('/debug/test', methods=['GET'])
def debug_test_offers():
    """Тестовый маршрут для проверки получения офферов"""
    try:
        # Прямой запрос к БД
        user_id = 373086959  # Ваш ID
        
        sys.path.insert(0, os.getcwd())
        from add_offer import get_user_offers
        
        offers = get_user_offers(user_id)
        
        return jsonify({
            'success': True,
            'test_user_id': user_id,
            'offers_count': len(offers),
            'offers': offers[:3]  # Первые 3 для проверки
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@offers_bp.route('/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    """Удаление оффера"""
    try:
        logger.info(f"Запрос на удаление оффера {offer_id}")

        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        try:
            # Импортируем функцию удаления
            sys.path.insert(0, os.getcwd())
            from add_offer import delete_offer_by_id

            result = delete_offer_by_id(offer_id, telegram_user_id)

            if result['success']:
                logger.info(f"Оффер {offer_id} успешно удален пользователем {telegram_user_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта delete_offer_by_id: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/<int:offer_id>/cancel', methods=['POST'])
def cancel_offer(offer_id):
    """Отмена оффера"""
    try:
        logger.info(f"Запрос на отмену оффера {offer_id}")

        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}
        cancel_reason = data.get('reason', 'Отменено пользователем')

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import cancel_offer_by_id

            result = cancel_offer_by_id(offer_id, telegram_user_id, cancel_reason)

            if result['success']:
                logger.info(f"Оффер {offer_id} успешно отменен пользователем {telegram_user_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта cancel_offer_by_id: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка отмены оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/<int:offer_id>/status', methods=['PATCH'])
def update_offer_status(offer_id):
    """Обновление статуса оффера"""
    try:
        logger.info(f"Запрос на изменение статуса оффера {offer_id}")

        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

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

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import update_offer_status_by_id

            result = update_offer_status_by_id(offer_id, telegram_user_id, new_status, reason)

            if result['success']:
                logger.info(f"Статус оффера {offer_id} изменен на {new_status}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта update_offer_status_by_id: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка изменения статуса оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


# Добавьте эти endpoints в app/api/offers.py

@offers_bp.route('/<int:offer_id>/respond', methods=['POST'])
def respond_to_offer(offer_id):
    """Создание отклика на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}

        channel_info = {
            'username': data.get('channel_username', ''),
            'title': data.get('channel_title', ''),
            'subscribers': data.get('channel_subscribers', 0)
        }

        message = data.get('message', '')

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import create_offer_response

            result = create_offer_response(offer_id, telegram_user_id, channel_info, message)

            if result['success']:
                logger.info(f"Создан отклик на оффер {offer_id} от пользователя {telegram_user_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта create_offer_response: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания отклика на оффер {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/<int:offer_id>/responses', methods=['GET'])
def get_offer_responses_api(offer_id):
    """Получение откликов на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import get_offer_responses

            result = get_offer_responses(offer_id, telegram_user_id)
            return jsonify(result)

        except ImportError as e:
            logger.error(f"Ошибка импорта get_offer_responses: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения откликов для оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/responses/<int:response_id>/status', methods=['PATCH'])
def update_response_status_api(response_id):
    """Обновление статуса отклика (принять/отклонить)"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

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

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import update_response_status

            result = update_response_status(response_id, new_status, telegram_user_id, message)

            if result['success']:
                logger.info(f"Статус отклика {response_id} изменен на {new_status}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта update_response_status: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка изменения статуса отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


# Добавьте эти endpoints в app/api/offers.py

@offers_bp.route('/responses/<int:response_id>/contract', methods=['POST'])
def create_contract_api(response_id):
    """Создание контракта после принятия отклика"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}

        contract_details = {
            'placement_hours': data.get('placement_hours', 24),  # Срок размещения в часах
            'monitoring_days': data.get('monitoring_days', 7),  # Срок мониторинга в днях
            'requirements': data.get('requirements', '')  # Требования к посту
        }

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import create_contract

            result = create_contract(response_id, contract_details)

            if result['success']:
                logger.info(f"Создан контракт для отклика {response_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта create_contract: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы контрактов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания контракта для отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/contracts/<contract_id>/placement', methods=['POST'])
def submit_placement_api(contract_id):
    """Подача заявки о размещении рекламы"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json()
        if not data or 'post_url' not in data:
            return jsonify({'success': False, 'error': 'Не указана ссылка на пост'}), 400

        post_url = data['post_url'].strip()

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import submit_placement

            result = submit_placement(contract_id, post_url, telegram_user_id)

            if result['success']:
                logger.info(f"Подана заявка о размещении для контракта {contract_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта submit_placement: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы контрактов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка подачи заявки о размещении: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/contracts', methods=['GET'])
def get_user_contracts():
    """Получение контрактов пользователя"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Получаем ID пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        user_db_id = user['id']

        # Получаем контракты пользователя (как рекламодатель и как издатель)
        contracts_query = '''
                          SELECT c.*, \
                                 o.title          as offer_title, \
                                 u_adv.first_name as advertiser_name, \
                                 u_pub.first_name as publisher_name, \
                                 or_resp.channel_title, \
                                 or_resp.channel_username
                          FROM contracts c
                                   JOIN offers o ON c.offer_id = o.id
                                   JOIN users u_adv ON c.advertiser_id = u_adv.id
                                   JOIN users u_pub ON c.publisher_id = u_pub.id
                                   JOIN offer_responses or_resp ON c.response_id = or_resp.id
                          WHERE c.advertiser_id = ? \
                             OR c.publisher_id = ?
                          ORDER BY c.created_at DESC \
                          '''

        contracts = db_manager.execute_query(contracts_query, (user_db_id, user_db_id), fetch_all=True)

        contracts_list = []
        for contract in contracts:
            contracts_list.append({
                'id': contract['id'],
                'offer_title': contract['offer_title'],
                'price': float(contract['price']),
                'status': contract['status'],
                'role': 'advertiser' if contract['advertiser_id'] == user_db_id else 'publisher',
                'advertiser_name': contract['advertiser_name'],
                'publisher_name': contract['publisher_name'],
                'channel_title': contract['channel_title'],
                'channel_username': contract['channel_username'],
                'placement_deadline': contract['placement_deadline'],
                'monitoring_end': contract['monitoring_end'],
                'post_url': contract['post_url'],
                'verification_passed': bool(contract['verification_passed']),
                'created_at': contract['created_at'],
                'completed_at': contract['completed_at']
            })

        return jsonify({
            'success': True,
            'contracts': contracts_list,
            'count': len(contracts_list)
        })

    except Exception as e:
        logger.error(f"Ошибка получения контрактов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения контрактов'}), 500


@offers_bp.route('/contracts/<contract_id>', methods=['GET'])
def get_contract_details(contract_id):
    """Получение деталей контракта"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Получаем детали контракта
        contract_query = '''
                         SELECT c.*, \
                                o.title           as offer_title, \
                                o.description     as offer_description, \
                                u_adv.first_name  as advertiser_name, \
                                u_adv.telegram_id as advertiser_telegram_id, \
                                u_pub.first_name  as publisher_name, \
                                u_pub.telegram_id as publisher_telegram_id, \
                                or_resp.channel_title, \
                                or_resp.channel_username, \
                                or_resp.message   as response_message
                         FROM contracts c
                                  JOIN offers o ON c.offer_id = o.id
                                  JOIN users u_adv ON c.advertiser_id = u_adv.id
                                  JOIN users u_pub ON c.publisher_id = u_pub.id
                                  JOIN offer_responses or_resp ON c.response_id = or_resp.id
                         WHERE c.id = ? \
                           AND (u_adv.telegram_id = ? OR u_pub.telegram_id = ?) \
                         '''

        contract = db_manager.execute_query(
            contract_query,
            (contract_id, telegram_user_id, telegram_user_id),
            fetch_one=True
        )

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
            'monitoring_duration': contract['monitoring_duration'],
            'monitoring_end': contract['monitoring_end'],
            'post_url': contract['post_url'],
            'post_id': contract['post_id'],
            'verification_passed': bool(contract['verification_passed']),
            'verification_details': contract['verification_details'],
            'violation_reason': contract['violation_reason'],
            'post_requirements': contract['post_requirements'],
            'created_at': contract['created_at'],
            'submitted_at': contract['submitted_at'],
            'completed_at': contract['completed_at']
        }

        return jsonify({
            'success': True,
            'contract': contract_details
        })

    except Exception as e:
        logger.error(f"Ошибка получения деталей контракта {contract_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения контракта'}), 500


@offers_bp.route('/contracts/<contract_id>/cancel', methods=['POST'])
def cancel_contract_api(contract_id):
    """Отмена контракта"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}
        reason = data.get('reason', 'Отменено пользователем')

        # Проверяем права доступа и текущий статус
        contract_query = '''
                         SELECT c.*, \
                                u_adv.telegram_id as advertiser_telegram_id, \
                                u_pub.telegram_id as publisher_telegram_id
                         FROM contracts c
                                  JOIN users u_adv ON c.advertiser_id = u_adv.id
                                  JOIN users u_pub ON c.publisher_id = u_pub.id
                         WHERE c.id = ? \
                           AND (u_adv.telegram_id = ? OR u_pub.telegram_id = ?) \
                         '''

        contract = db_manager.execute_query(
            contract_query,
            (contract_id, telegram_user_id, telegram_user_id),
            fetch_one=True
        )

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден или нет доступа'}), 404

        if contract['status'] in ['completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Контракт уже завершен или отменен'}), 400

        # Отменяем контракт
        db_manager.execute_query('''
                                 UPDATE contracts
                                 SET status           = 'cancelled',
                                     violation_reason = ?,
                                     updated_at       = ?
                                 WHERE id = ?
                                 ''', ('cancelled', reason, datetime.now().isoformat(), contract_id))

        # Отменяем задачи мониторинга
        db_manager.execute_query('''
                                 UPDATE monitoring_tasks
                                 SET status       = 'failed',
                                     completed_at = ?
                                 WHERE contract_id = ?
                                   AND status = 'active'
                                 ''', (datetime.now().isoformat(), contract_id))

        # Отправляем уведомления
        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import send_contract_notification
            send_contract_notification(contract_id, 'cancelled', {'reason': reason})
        except ImportError:
            pass

        logger.info(f"Контракт {contract_id} отменен пользователем {telegram_user_id}")

        return jsonify({
            'success': True,
            'message': 'Контракт отменен. Все участники получили уведомления.'
        })

    except Exception as e:
        logger.error(f"Ошибка отмены контракта {contract_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


# Добавляем функцию для отправки уведомлений в add_offer.py
def send_contract_notification(contract_id, notification_type, extra_data=None):
    """Отправка уведомлений по контрактам"""
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем информацию о контракте
        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_adv.first_name  as advertiser_name,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_pub.first_name  as publisher_name,
                              or_resp.channel_title
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        if notification_type == 'created':
            # Уведомления о создании контракта
            advertiser_msg = f"""📋 <b>Контракт создан!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Сумма:</b> {data['price']} RUB
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

⏰ <b>Срок размещения:</b> {formatDate(data['placement_deadline'])}
🔍 <b>Срок мониторинга:</b> {data['monitoring_duration']} дней

📱 Издатель должен разместить рекламу и подать заявку в приложении."""

            publisher_msg = f"""✅ <b>Ваш отклик принят! Контракт создан.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data['price']} RUB
👤 <b>Рекламодатель:</b> {data['advertiser_name']}

⏰ <b>Разместите рекламу до:</b> {formatDate(data['placement_deadline'])}

📝 <b>Что делать дальше:</b>
1. Разместите рекламу в своем канале
2. Подайте заявку с ссылкой на пост в приложении
3. После проверки начнется мониторинг
4. Получите оплату после завершения"""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Открыть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], advertiser_msg, keyboard)
            send_telegram_message(data['publisher_telegram_id'], publisher_msg, keyboard)

        elif notification_type == 'placement_submitted':
            # Уведомление рекламодателю о подаче заявки
            message = f"""📤 <b>Заявка о размещении подана!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

🔍 Начинается автоматическая проверка размещения.
Вы получите уведомление о результате проверки."""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Посмотреть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], message, keyboard)

        elif notification_type == 'verification_result':
            # Уведомления о результате проверки
            status = extra_data.get('status') if extra_data else data['status']

            if status == 'monitoring':
                adv_msg = f"""✅ <b>Размещение подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}

🔍 Начат мониторинг размещения на {data['monitoring_duration']} дней.
Оплата будет произведена автоматически после завершения мониторинга."""

                pub_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>К оплате:</b> {data['price']} RUB

🔍 Начат мониторинг на {data['monitoring_duration']} дней.
Не удаляйте пост до завершения мониторинга!"""

            else:
                error_msg = extra_data.get('message') if extra_data else 'Размещение не соответствует требованиям'

                pub_msg = f"""❌ <b>Проверка не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Причина:</b> {error_msg}

🔄 Исправьте размещение и подайте заявку повторно."""

                adv_msg = f"""❌ <b>Проверка размещения не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Причина:</b> {error_msg}

Издатель должен исправить размещение."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'completed':
            # Уведомления о завершении контракта
            payment_id = extra_data.get('payment_id') if extra_data else 'N/A'
            amount = extra_data.get('amount') if extra_data else data['price']

            adv_msg = f"""✅ <b>Контракт завершен!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
💰 <b>Сумма:</b> {amount} RUB

✅ Мониторинг завершен успешно.
💳 Платеж #{payment_id} обрабатывается."""

            pub_msg = f"""🎉 <b>Поздравляем! Контракт выполнен.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Заработано:</b> {amount} RUB

💳 Платеж #{payment_id} поступит на ваш счет в течение 24 часов.
Спасибо за качественную работу!"""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'violation':
            # Уведомления о нарушении
            reason = extra_data.get('reason') if extra_data else 'Нарушение условий контракта'

            pub_msg = f"""⚠️ <b>Обнаружено нарушение!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Проблема:</b> {reason}

🔄 Пожалуйста, восстановите размещение или свяжитесь с поддержкой."""

            adv_msg = f"""⚠️ <b>Нарушение контракта</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Проблема:</b> {reason}

Мы уведомили издателя о необходимости исправления."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления по контракту: {e}")


def formatDate(date_str):
    """Форматирование даты для уведомлений"""
    try:
        if not date_str:
            return 'Не указано'
        dt = datetime.fromisoformat(date_str)
        return dt.strftime('%d.%m.%Y в %H:%M')
    except:
        return date_str