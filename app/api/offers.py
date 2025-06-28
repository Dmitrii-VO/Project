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


# ИСПРАВЛЕНИЕ: в файле app/api/offers.py
# Найти функцию get_my_offers и заменить SQL запрос

@offers_bp.route('/my', methods=['GET'])
def get_my_offers():
    """Получение моих офферов - ФИНАЛЬНАЯ ОПТИМИЗИРОВАННАЯ ВЕРСИЯ"""
    try:
        import json
        logger.info("Запрос на получение моих офферов")

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
            logger.warning(f"Пользователь с telegram_id {telegram_user_id} не найден в БД")
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        user_db_id = user['id']
        logger.info(f"ID пользователя в БД: {user_db_id}")

        # Параметры фильтрации и пагинации
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status')  # active, paused, completed, cancelled
        search = request.args.get('search', '').strip()
        category_filter = request.args.get('category')

        offset = (page - 1) * limit

        # Построение базового запроса
        base_query = '''
                     SELECT o.id, \
                            o.title, \
                            o.description, \
                            o.content, \
                            o.price, \
                            o.currency,
                            o.category, \
                            o.status, \
                            o.created_at, \
                            o.updated_at,
                            o.target_audience, \
                            o.requirements, \
                            o.deadline, \
                            o.budget_total,
                            o.duration_days, \
                            o.min_subscribers, \
                            o.max_subscribers, \
                            o.metadata,
                            u.username   as creator_username, \
                            u.first_name as creator_name
                     FROM offers o
                              JOIN users u ON o.created_by = u.id
                     WHERE o.created_by = ? \
                     '''

        count_query = '''
                      SELECT COUNT(*) as total
                      FROM offers o
                      WHERE o.created_by = ? \
                      '''

        params = [user_db_id]

        # Добавляем фильтры
        if status_filter:
            base_query += ' AND o.status = ?'
            count_query += ' AND o.status = ?'
            params.append(status_filter)

        if search:
            base_query += ' AND (o.title LIKE ? OR o.description LIKE ?)'
            count_query += ' AND (o.title LIKE ? OR o.description LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])

        if category_filter:
            base_query += ' AND o.category = ?'
            count_query += ' AND o.category = ?'
            params.append(category_filter)

        # Получаем общее количество (для пагинации)
        total_count = db_manager.execute_query(count_query, tuple(params), fetch_one=True)['total']

        # Добавляем сортировку и пагинацию
        base_query += ' ORDER BY o.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        # Получаем офферы
        offers = db_manager.execute_query(base_query, tuple(params), fetch_all=True)
        logger.info(f"Найдено офферов: {len(offers)} (всего в БД: {total_count})")

        if not offers:
            return jsonify({
                'success': True,
                'offers': [],
                'count': 0,
                'total_count': total_count,
                'page': page,
                'total_pages': 0,
                'user_id': telegram_user_id
            })

        # ОПТИМИЗИРОВАННЫЙ подсчет откликов одним запросом
        offer_ids = [str(offer['id']) for offer in offers]
        offer_ids_str = ','.join(offer_ids)

        # Получаем статистику откликов для всех офферов одним запросом
        response_stats = db_manager.execute_query(f'''
            SELECT offer_id,
                   COUNT(*) as total_count,
                   COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count,
                   COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                   COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
            FROM offer_responses 
            WHERE offer_id IN ({offer_ids_str})
            GROUP BY offer_id
        ''', fetch_all=True)

        # Создаем словарь для быстрого поиска статистики
        stats_dict = {}
        for stat in response_stats:
            stats_dict[stat['offer_id']] = {
                'total_count': stat['total_count'],
                'accepted_count': stat['accepted_count'],
                'pending_count': stat['pending_count'],
                'rejected_count': stat['rejected_count']
            }

        # Форматируем данные для фронтенда
        formatted_offers = []
        for offer in offers:
            offer_id = offer['id']

            # Получаем статистику откликов
            stats = stats_dict.get(offer_id, {
                'total_count': 0,
                'accepted_count': 0,
                'pending_count': 0,
                'rejected_count': 0
            })

            # Парсим метаданные
            try:
                metadata = json.loads(offer.get('metadata', '{}')) if offer.get('metadata') else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            # Рассчитываем дополнительные метрики
            response_count = stats['total_count']
            acceptance_rate = (stats['accepted_count'] / response_count * 100) if response_count > 0 else 0

            # Определяем эффективность оффера
            effectiveness = 'high' if acceptance_rate >= 50 else 'medium' if acceptance_rate >= 20 else 'low'

            formatted_offer = {
                # Основная информация
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'content': offer['content'],
                'category': offer['category'] or 'general',
                'status': offer['status'] or 'active',

                # Финансовые данные
                'price': float(offer['price']) if offer['price'] else 0,
                'currency': offer['currency'] or 'RUB',
                'budget_total': float(offer.get('budget_total', 0)) if offer.get('budget_total') else 0,

                # Настройки таргетинга
                'target_audience': offer.get('target_audience', ''),
                'min_subscribers': offer.get('min_subscribers', 1),
                'max_subscribers': offer.get('max_subscribers', 100000000),

                # Требования и условия
                'requirements': offer.get('requirements', ''),
                'deadline': offer.get('deadline', ''),
                'duration_days': offer.get('duration_days', 30),

                # Временные метки
                'created_at': offer['created_at'],
                'updated_at': offer['updated_at'],

                # Статистика откликов
                'response_count': response_count,
                'accepted_count': stats['accepted_count'],
                'pending_count': stats['pending_count'],
                'rejected_count': stats['rejected_count'],
                'acceptance_rate': round(acceptance_rate, 1),
                'effectiveness': effectiveness,

                # Информация о создателе
                'creator_username': offer.get('creator_username', ''),
                'creator_name': offer.get('creator_name', ''),

                # Дополнительные данные
                'metadata': metadata,

                # Вычисляемые поля
                'is_active': offer['status'] == 'active',
                'has_responses': response_count > 0,
                'needs_attention': stats['pending_count'] > 0,
                'is_successful': stats['accepted_count'] > 0
            }

            formatted_offers.append(formatted_offer)
            logger.debug(f"Оффер {offer_id} '{offer['title']}': {response_count} откликов")

        # Рассчитываем общую статистику пользователя
        total_responses = sum(stats_dict[oid]['total_count'] for oid in stats_dict)
        total_accepted = sum(stats_dict[oid]['accepted_count'] for oid in stats_dict)
        total_pending = sum(stats_dict[oid]['pending_count'] for oid in stats_dict)

        logger.info(f"Возвращаем {len(formatted_offers)} офферов. Всего откликов: {total_responses}")

        return jsonify({
            'success': True,
            'offers': formatted_offers,
            'count': len(formatted_offers),
            'total_count': total_count,
            'page': page,
            'total_pages': (total_count + limit - 1) // limit,
            'user_id': telegram_user_id,

            # Сводная статистика
            'summary': {
                'total_offers': total_count,
                'total_responses': total_responses,
                'total_accepted': total_accepted,
                'total_pending': total_pending,
                'overall_acceptance_rate': round((total_accepted / total_responses * 100) if total_responses > 0 else 0,
                                                 1)
            },

            # Фильтры для фронтенда
            'filters': {
                'status': status_filter,
                'search': search,
                'category': category_filter,
                'page': page,
                'limit': limit
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения офферов: {e}")
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
                                                  SELECT COUNT(*)                                                as total_responses,
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


@offers_bp.route('/contracts/<contract_id>', methods=['DELETE'])
def delete_contract_api(contract_id):
    """Удаление контракта (только для статуса verification_failed)"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Проверяем права доступа и статус контракта
        contract_query = '''
                         SELECT c.*,
                                o.title           as offer_title,
                                u_adv.telegram_id as advertiser_telegram_id,
                                u_pub.telegram_id as publisher_telegram_id
                         FROM contracts c
                                  JOIN offers o ON c.offer_id = o.id
                                  JOIN users u_adv ON c.advertiser_id = u_adv.id
                                  JOIN users u_pub ON c.publisher_id = u_pub.id
                         WHERE c.id = ?
                         '''

        contract = db_manager.execute_query(
            contract_query,
            (contract_id,),
            fetch_one=True
        )

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден'}), 404

        # Проверяем права доступа (только участники контракта)
        if (contract['advertiser_telegram_id'] != telegram_user_id and
                contract['publisher_telegram_id'] != telegram_user_id):
            return jsonify({'success': False, 'error': 'Нет доступа к этому контракту'}), 403

        # Проверяем статус - можно удалять только verification_failed
        if contract['status'] != 'verification_failed':
            return jsonify({
                'success': False,
                'error': f'Можно удалять только контракты со статусом "verification_failed". Текущий статус: {contract["status"]}'
            }), 400

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import delete_failed_contract

            result = delete_failed_contract(contract_id, telegram_user_id)

            if result['success']:
                logger.info(f"Контракт {contract_id} удален пользователем {telegram_user_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта delete_failed_contract: {e}")

            # Fallback - удаляем напрямую
            try:
                db_manager.execute_query(
                    'DELETE FROM contracts WHERE id = ? AND status = "verification_failed"',
                    (contract_id,)
                )

                return jsonify({
                    'success': True,
                    'message': f'Контракт "{contract["offer_title"]}" удален'
                }), 200

            except Exception as db_error:
                logger.error(f"Ошибка прямого удаления контракта: {db_error}")
                return jsonify({
                    'success': False,
                    'error': 'Ошибка удаления контракта'
                }), 500

    except Exception as e:
        logger.error(f"Ошибка удаления контракта {contract_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


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


@offers_bp.route('/<int:offer_id>/respond', methods=['POST'])
def respond_to_offer(offer_id):
    """Создание отклика на оффер с выбранным каналом"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}

        # Получаем ID выбранного канала
        channel_id = data.get('channel_id')
        if not channel_id:
            return jsonify({'success': False, 'error': 'Не выбран канал'}), 400

        # Проверяем, что канал принадлежит пользователю и верифицирован
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 400

        user_db_id = user['id']

        # Проверяем канал
        channel = db_manager.execute_query(
            '''SELECT *
               FROM channels
               WHERE id = ?
                 AND owner_id = ?
                 AND is_verified = 1''',
            (channel_id, user_db_id),
            fetch_one=True
        )

        if not channel:
            return jsonify({'success': False, 'error': 'Канал не найден или не верифицирован'}), 400

        # Проверяем, что пользователь еще не откликался на этот оффер этим каналом
        existing_response = db_manager.execute_query(
            '''SELECT id
               FROM offer_responses
               WHERE offer_id = ?
                 AND channel_id = ?''',
            (offer_id, channel_id),
            fetch_one=True
        )

        if existing_response:
            return jsonify({'success': False, 'error': 'Вы уже откликались на этот оффер данным каналом'}), 400

        message = data.get('message', '').strip()

        try:
            sys.path.insert(0, os.getcwd())

            # Используем старую структуру БД без channel_id
            # Получаем данные канала для совместимости со старой структурой
            channel_data = {
                'channel_title': channel['title'],
                'channel_username': channel['username'],
                'channel_subscribers': channel['subscriber_count'] or 0,
                'message': message
            }

            # Создаем отклик напрямую в БД без использования channel_id
            import sqlite3
            from datetime import datetime

            DATABASE_PATH = 'telegram_mini_app.db'
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Создаем отклик в старой структуре БД
            cursor.execute('''
                           INSERT INTO offer_responses (offer_id, user_id, message, status,
                                                        channel_title, channel_username, channel_subscribers,
                                                        created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ''', (
                               offer_id,
                               user_db_id,
                               message,
                               'pending',
                               channel_data['channel_title'],
                               channel_data['channel_username'],
                               channel_data['channel_subscribers'],
                               datetime.now().isoformat(),
                               datetime.now().isoformat()
                           ))

            response_id = cursor.lastrowid
            conn.commit()
            conn.close()

            result = {
                'success': True,
                'message': 'Отклик успешно отправлен',
                'response_id': response_id
            }

            if result['success']:
                logger.info(f"Создан отклик на оффер {offer_id} от канала {channel_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта create_offer_response_with_channel: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания отклика на оффер {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@offers_bp.route('/<int:offer_id>/responses', methods=['GET'])
def get_offer_responses_api(offer_id):
    """Получение откликов на оффер с подробной информацией"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        logger.info(f"Запрос откликов для оффера {offer_id} от пользователя {telegram_user_id}")

        # ИСПРАВЛЕННЫЙ запрос: Проверяем права доступа к офферу
        offer = db_manager.execute_query(
            '''SELECT o.*, u.telegram_id as owner_telegram_id
               FROM offers o
                        JOIN users u ON o.created_by = u.id
               WHERE o.id = ?''',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            logger.warning(f"Оффер {offer_id} не найден")
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        logger.info(f"Оффер найден: {offer['title']}, владелец: {offer['owner_telegram_id']}")

        if offer['owner_telegram_id'] != telegram_user_id:
            logger.warning(f"Нет доступа к офферу {offer_id}: владелец {offer['owner_telegram_id']}, запрос от {telegram_user_id}")
            return jsonify({'success': False, 'error': 'Нет доступа к этому офферу'}), 403

        # ИСПРАВЛЕННЫЙ запрос откликов: используем существующие поля из offer_responses
        responses = db_manager.execute_query(
            '''SELECT or_resp.*,
                      u.first_name || ' ' || COALESCE(u.last_name, '') as channel_owner_name,
                      u.username as channel_owner_username,
                      u.telegram_id as channel_owner_telegram_id
               FROM offer_responses or_resp
                        JOIN users u ON or_resp.user_id = u.id
               WHERE or_resp.offer_id = ?
               ORDER BY or_resp.created_at DESC''',
            (offer_id,),
            fetch_all=True
        )

        logger.info(f"Найдено откликов: {len(responses)}")

        # Форматируем данные для фронтенда
        formatted_responses = []
        for response in responses:
            formatted_response = {
                'id': response['id'],
                'offer_id': response['offer_id'],
                'user_id': response['user_id'],
                'status': response['status'],
                'message': response['message'],
                'created_at': response['created_at'],
                'updated_at': response['updated_at'],

                # Информация о канале (из полей offer_responses)
                'channel_title': response.get('channel_title', 'Канал без названия'),
                'channel_username': response.get('channel_username', 'unknown'),
                'channel_subscribers': response.get('channel_subscribers', 0),
                'channel_description': '',  # Пустое значение для совместимости
                'channel_category': '',     # Пустое значение для совместимости

                # Информация о владельце канала
                'channel_owner_name': response['channel_owner_name'].strip() if response['channel_owner_name'] else 'Пользователь',
                'channel_owner_username': response['channel_owner_username'] or '',
                'channel_owner_telegram_id': response['channel_owner_telegram_id']
            }
            formatted_responses.append(formatted_response)
            logger.debug(f"Обработан отклик {response['id']}: {formatted_response['channel_title']}")

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
        logger.error(f"Ошибка получения откликов для оффера {offer_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


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


@offers_bp.route('/responses/<int:response_id>/accept', methods=['POST'])
def accept_response(response_id):
    """Принятие отклика на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Проверяем права доступа
        response_data = db_manager.execute_query(
            '''SELECT or_resp.*, o.user_id as offer_owner_id, u.telegram_id as offer_owner_telegram_id
               FROM offer_responses or_resp
                        JOIN offers o ON or_resp.offer_id = o.id
                        JOIN users u ON o.user_id = u.id
               WHERE or_resp.id = ?''',
            (response_id,),
            fetch_one=True
        )

        if not response_data:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        if response_data['offer_owner_telegram_id'] != telegram_user_id:
            return jsonify({'success': False, 'error': 'Нет доступа к этому отклику'}), 403

        if response_data['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Отклик уже обработан'}), 400

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import accept_offer_response

            result = accept_offer_response(response_id, telegram_user_id)

            if result['success']:
                logger.info(f"Отклик {response_id} принят пользователем {telegram_user_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта accept_offer_response: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка принятия отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/responses/<int:response_id>/reject', methods=['POST'])
def reject_response(response_id):
    """Отклонение отклика на оффер"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        data = request.get_json() or {}
        reason = data.get('reason', 'Не подходящий канал')

        # Проверяем права доступа
        response_data = db_manager.execute_query(
            '''SELECT or_resp.*, o.user_id as offer_owner_id, u.telegram_id as offer_owner_telegram_id
               FROM offer_responses or_resp
                        JOIN offers o ON or_resp.offer_id = o.id
                        JOIN users u ON o.user_id = u.id
               WHERE or_resp.id = ?''',
            (response_id,),
            fetch_one=True
        )

        if not response_data:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        if response_data['offer_owner_telegram_id'] != telegram_user_id:
            return jsonify({'success': False, 'error': 'Нет доступа к этому отклику'}), 403

        if response_data['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Отклик уже обработан'}), 400

        try:
            sys.path.insert(0, os.getcwd())
            from add_offer import reject_offer_response

            result = reject_offer_response(response_id, telegram_user_id, reason)

            if result['success']:
                logger.info(f"Отклик {response_id} отклонён пользователем {telegram_user_id}")
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта reject_offer_response: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы откликов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка отклонения отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/responses/<int:response_id>', methods=['GET'])
def get_response_details(response_id):
    """Получение подробной информации об отклике"""
    try:
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Получаем детальную информацию об отклике
        response_data = db_manager.execute_query(
            '''SELECT or_resp.*,
                      o.title                                                      as offer_title,
                      o.description                                                as offer_description,
                      o.total_budget                                               as offer_budget,
                      c.title                                                      as channel_title,
                      c.username                                                   as channel_username,
                      c.subscriber_count                                           as channel_subscribers,
                      c.description                                                as channel_description,
                      c.category                                                   as channel_category,
                      c.price_per_post                                             as channel_price,
                      u_owner.first_name || ' ' || COALESCE(u_owner.last_name, '') as channel_owner_name,
                      u_owner.username                                             as channel_owner_username,
                      u_owner.telegram_id                                          as channel_owner_telegram_id,
                      u_advertiser.telegram_id                                     as offer_owner_telegram_id
               FROM offer_responses or_resp
                        JOIN offers o ON or_resp.offer_id = o.id
                        JOIN channels c ON or_resp.channel_id = c.id
                        JOIN users u_owner ON c.owner_id = u_owner.id
                        JOIN users u_advertiser ON o.user_id = u_advertiser.id
               WHERE or_resp.id = ?''',
            (response_id,),
            fetch_one=True
        )

        if not response_data:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        # Проверяем права доступа (владелец оффера или владелец канала)
        if (response_data['offer_owner_telegram_id'] != telegram_user_id and
                response_data['channel_owner_telegram_id'] != telegram_user_id):
            return jsonify({'success': False, 'error': 'Нет доступа к этому отклику'}), 403

        # Форматируем ответ
        formatted_response = {
            'id': response_data['id'],
            'offer_id': response_data['offer_id'],
            'channel_id': response_data['channel_id'],
            'status': response_data['status'],
            'message': response_data['message'],
            'created_at': response_data['created_at'],
            'updated_at': response_data['updated_at'],

            # Информация об оффере
            'offer': {
                'title': response_data['offer_title'],
                'description': response_data['offer_description'],
                'budget': response_data['offer_budget']
            },

            # Информация о канале
            'channel': {
                'title': response_data['channel_title'],
                'username': response_data['channel_username'],
                'subscribers': response_data['channel_subscribers'],
                'description': response_data['channel_description'],
                'category': response_data['channel_category'],
                'price_per_post': response_data['channel_price']
            },

            # Информация о владельце канала
            'channel_owner': {
                'name': response_data['channel_owner_name'].strip(),
                'username': response_data['channel_owner_username'],
                'telegram_id': response_data['channel_owner_telegram_id']
            }
        }

        return jsonify({
            'success': True,
            'response': formatted_response
        })

    except Exception as e:
        logger.error(f"Ошибка получения деталей отклика {response_id}: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/debug/responses-raw/<int:offer_id>', methods=['GET'])
def debug_responses_raw(offer_id):
    """Отладка: сырые данные откликов"""
    try:
        # Проверяем оффер
        offer = db_manager.execute_query(
            'SELECT id, title, created_by FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        # Получаем все отклики
        responses = db_manager.execute_query(
            'SELECT * FROM offer_responses WHERE offer_id = ?',
            (offer_id,),
            fetch_all=True
        )

        # Проверяем пользователя-владельца
        if offer:
            owner = db_manager.execute_query(
                'SELECT telegram_id FROM users WHERE id = ?',
                (offer['created_by'],),
                fetch_one=True
            )
        else:
            owner = None

        return jsonify({
            'success': True,
            'offer_id': offer_id,
            'offer_data': offer,
            'offer_owner': owner,
            'responses_count': len(responses),
            'responses_raw': responses,
            'current_user': get_user_id_from_request()
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@offers_bp.route('/debug/responses-count/<int:offer_id>', methods=['GET'])
def debug_responses_count(offer_id):
    """Отладка подсчета откликов для оффера"""
    try:
        # Прямой подсчет откликов
        direct_count = db_manager.execute_query(
            'SELECT COUNT(*) as count FROM offer_responses WHERE offer_id = ?',
            (offer_id,),
            fetch_one=True
        )

        # Подсчет через LEFT JOIN (как в get_user_offers)
        join_count = db_manager.execute_query(
            '''SELECT o.id, o.title, COUNT(DISTINCT or_resp.id) as response_count
               FROM offers o
                        LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
               WHERE o.id = ?
               GROUP BY o.id, o.title''',
            (offer_id,),
            fetch_one=True
        )

        return jsonify({
            'success': True,
            'offer_id': offer_id,
            'direct_count': direct_count['count'] if direct_count else 0,
            'join_count': join_count['response_count'] if join_count else 0,
            'join_data': join_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

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