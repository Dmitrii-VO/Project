# app/api/offers.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ

import json
import logging
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from app.models.database import db_manager
from flask import Blueprint, request, jsonify
import os
from app.models import get_user_id_from_request, execute_db_query
from dotenv import load_dotenv
DATABASE_PATH = os.getenv('DATABASE_PATH')
logger = logging.getLogger(__name__)

# === BLUEPRINT ===
offers_bp = Blueprint('offers', __name__)

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

        # Базовая валидация обязательных полей
        required_fields = ['title', 'description', 'price', 'target_audience']
        errors = []
        
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        # Получаем/создаем пользователя в БД
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            # Создаем нового пользователя
            user_db_id = execute_db_query(
                '''INSERT INTO users (telegram_id, username, first_name, user_type, status, created_at)
                   VALUES (?, ?, ?, 'advertiser', 'active', CURRENT_TIMESTAMP)''',
                (telegram_user_id, data.get('username', f'user_{telegram_user_id}'), data.get('first_name', 'User'))
            )
        else:
            user_db_id = user['id']

        # Подготавливаем данные для оффера
        metadata = {
            'posting_requirements': data.get('posting_requirements', {}),
            'additional_info': data.get('additional_info', ''),
            'creator_telegram_id': telegram_user_id
        }

        # Создаем оффер
        offer_id = execute_db_query('''
            INSERT INTO offers (created_by, title, description, content, price, currency,
                               target_audience, requirements, deadline, status, category,
                               metadata, budget_total, expires_at, duration_days,
                               min_subscribers, max_subscribers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_db_id,
            data['title'],
            data['description'], 
            data.get('content', data['description']),
            float(data['price']),
            data.get('currency', 'RUB'),
            data['target_audience'],
            data.get('requirements', ''),
            data.get('deadline'),
            'active',
            data.get('category', 'general'),
            json.dumps(metadata),
            float(data.get('budget_total', data['price'])),
            data.get('expires_at'),
            int(data.get('duration_days', 30)),
            int(data.get('min_subscribers', 0)),
            int(data.get('max_subscribers', 0))
        ))

        logger.info(f"Создан новый оффер {offer_id} пользователем {telegram_user_id}")

        # Получаем созданный оффер
        created_offer = execute_db_query('''
            SELECT o.*, u.username, u.first_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        ''', (offer_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'offer_id': offer_id,
            'offer': created_offer,
            'message': 'Оффер успешно создан'
        }), 201

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

        # Строим запрос
        base_query = """
            SELECT o.*, u.first_name, u.last_name, u.username as creator_username
            FROM offers o
            LEFT JOIN users u ON o.created_by = u.id
            WHERE o.status = 'active'
        """

        query_params = []
        conditions = []

        # Исключаем офферы текущего пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )
        
        if user:
            conditions.append("o.created_by != ?")
            query_params.append(user['id'])

        # Применяем фильтры
        if filters.get('category'):
            conditions.append('o.category = ?')
            query_params.append(filters['category'])

        if filters.get('min_budget'):
            conditions.append('o.price >= ?')
            query_params.append(float(filters['min_budget']))

        if filters.get('max_budget'):
            conditions.append('o.price <= ?')
            query_params.append(float(filters['max_budget']))

        if filters.get('min_subscribers'):
            conditions.append('o.min_subscribers <= ?')
            query_params.append(int(filters['min_subscribers']))

        # Поиск по тексту
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            conditions.append("(o.title LIKE ? OR o.description LIKE ?)")
            query_params.extend([search_term, search_term])

        # Собираем запрос
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " ORDER BY o.created_at DESC LIMIT ?"
        query_params.append(filters.get('limit', 50))

        # Выполняем запрос
        rows = execute_db_query(base_query, tuple(query_params), fetch_all=True)

        offers = []
        for row in rows:
            # Формируем имя создателя
            creator_name = ''
            if row.get('first_name') and row.get('last_name'):
                creator_name = f"{row['first_name']} {row['last_name']}"
            elif row.get('first_name'):
                creator_name = row['first_name']
            elif row.get('creator_username'):
                creator_name = f"@{row['creator_username']}"
            else:
                creator_name = "Аноним"

            offer = {
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'content': row['content'],
                'price': float(row['price']) if row['price'] else 0,
                'currency': row['currency'] or 'RUB',
                'category': row['category'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'created_by': row['created_by'],
                'creator_name': creator_name,
                'budget_total': float(row['budget_total']) if row['budget_total'] else 0,
                'min_subscribers': row['min_subscribers'] or 0,
                'max_subscribers': row['max_subscribers'] or 0,
                'deadline': row['deadline'],
                'target_audience': row['target_audience'],
                'requirements': row['requirements']
            }
            offers.append(offer)

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

        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Получаем оффер
        offer = execute_db_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        if offer['created_by'] != user['id']:
            return jsonify({'success': False, 'error': 'У вас нет прав для удаления этого оффера'}), 403

        if offer['status'] in ['active', 'paused']:
            return jsonify({
                'success': False,
                'error': 'Нельзя удалить активный оффер. Сначала завершите или отмените его.'
            }), 400

        # Удаляем связанные данные и оффер в транзакции
        import sqlite3
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute('BEGIN TRANSACTION')

        try:
            conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
            conn.commit()

            logger.info(f"Оффер {offer_id} удален пользователем {telegram_user_id}")

            return jsonify({
                'success': True,
                'message': f'Оффер "{offer["title"]}" успешно удален',
                'offer_id': offer_id
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при удалении оффера {offer_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении оффера'}), 500
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@offers_bp.route('/<int:offer_id>/status', methods=['PATCH'])
def update_offer_status(offer_id):
    """Обновление статуса оффера"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        new_status = data.get('status')
        reason = data.get('reason', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Статус не указан'}), 400

        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Получаем оффер
        offer = execute_db_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        if offer['created_by'] != user['id']:
            return jsonify({'success': False, 'error': 'У вас нет прав для изменения этого оффера'}), 403

        # Проверяем допустимость перехода
        status_transitions = {
            'active': ['paused', 'cancelled', 'completed'],
            'paused': ['active', 'cancelled', 'completed'],
            'cancelled': [],
            'completed': []
        }

        current_status = offer['status']
        if new_status not in status_transitions.get(current_status, []):
            return jsonify({
                'success': False,
                'error': f'Нельзя изменить статус с "{current_status}" на "{new_status}"'
            }), 400

        # Обновляем статус
        execute_db_query('''
                        UPDATE offers
                        SET status     = ?,
                            updated_at = ?
                        WHERE id = ?
                        ''', (new_status, datetime.now().isoformat(), offer_id))

        return jsonify({
            'success': True,
            'message': f'Статус оффера "{offer["title"]}" изменен на "{new_status}"',
            'offer_id': offer_id,
            'old_status': current_status,
            'new_status': new_status
        })

    except Exception as e:
        logger.error(f"❌ Ошибка изменения статуса оффера: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@offers_bp.route('/<int:offer_id>/respond', methods=['POST'])
def respond_to_offer(offer_id):
            """Отклик на оффер"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                channel_id = data.get('channel_id')
                message = data.get('message', '').strip()

                if not channel_id or not message:
                    return jsonify({'success': False, 'error': 'Канал и сообщение обязательны'}), 400

                # Получаем данные канала для создания отклика
                user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,),
                                        fetch_one=True)
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

                # Создаем отклик
                # Создаем отклик
                response_id = execute_db_query("""
                                               INSERT INTO offer_responses (offer_id, user_id, channel_id, message,
                                                                            status,
                                                                            channel_title, channel_username,
                                                                            channel_subscriber, created_at, updated_at)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                               """, (
                                                   offer_id, user['id'], channel['id'], message, 'pending',
                                                   channel.get('title', ''), channel.get('username', ''),
                                                   channel.get('subscriber_count', 0)
                                               ))

                return jsonify({
                    'success': True,
                    'message': 'Отклик успешно отправлен! Ожидайте ответа от рекламодателя.',
                    'response_id': response_id
                })

            except Exception as e:
                logger.error(f"❌ Ошибка отклика на оффер: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

@offers_bp.route('/<int:offer_id>/responses', methods=['GET'])
def get_offer_responses(offer_id):
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
                        'channel_subscriber': response.get('channel_subscriber', 0),
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
                logger.error(f"❌ Ошибка получения откликов: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

@offers_bp.route('/responses/<response_id>/status', methods=['PATCH'])
def update_response_status_route(response_id):
    """Обновление статуса отклика с автоматическим созданием контракта"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        new_status = data.get('status')
        message = data.get('message', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Статус не указан'}), 400

        # Получаем данные отклика
        response_data = execute_db_query('''
            SELECT or_resp.*,
                o.created_by,
                o.title as offer_title,
                o.price as offer_price,
                o.budget_total,
                u.telegram_id as author_telegram_id
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            JOIN users u ON o.created_by = u.id
            WHERE or_resp.id = ?
        ''', (response_id,), fetch_one=True)

        if not response_data:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        if response_data['author_telegram_id'] != telegram_user_id:
            return jsonify({'success': False, 'error': 'Нет прав для изменения статуса'}), 403

        if response_data['status'] != 'pending':
            return jsonify({'success': False, 'error': 'Отклик уже обработан'}), 400

        # Обновляем статус отклика
        execute_db_query('''
            UPDATE offer_responses
            SET status = ?,
                updated_at = ?,
                admin_message = ?
            WHERE id = ?
        ''', (new_status, datetime.now().isoformat(), message, response_id))

        contract_id = None
        if new_status == 'accepted':
            # Отклоняем остальные отклики
            execute_db_query('''
                UPDATE offer_responses
                SET status = 'rejected',
                    updated_at = ?,
                    admin_message = 'Автоматически отклонен (выбран другой канал)'
                WHERE offer_id = ?
                AND id != ? AND status = 'pending'
            ''', (datetime.now().isoformat(), response_data['offer_id'], response_id))

            # Генерируем уникальный ID контракта
            
            contract_uuid = str(uuid.uuid4())

            # Создаем контракт
            execute_db_query('''
                INSERT INTO contracts (id, offer_id, response_id, advertiser_id, publisher_id,
                                    status, price, placement_deadline, monitoring_end, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, 
                        datetime('now', '+7 days'), datetime('now', '+14 days'), CURRENT_TIMESTAMP)
            ''', (contract_uuid, response_data['offer_id'], response_id, response_data['created_by'], 
                response_data['user_id'], response_data.get('offer_price', 0)))
            
            contract_id = contract_uuid

        result = {
            'success': True,
            'message': f'Отклик {"принят" if new_status == "accepted" else "отклонён"}. Пользователь получил уведомление.'
        }

        if contract_id:
            result['contract_id'] = contract_id
            result['contract_created'] = True

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка обновления статуса отклика: {e}")
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


@offers_bp.route('/contracts/<contract_id>/placement', methods=['POST'])
def submit_placement_api(contract_id):
    """Подача заявки о размещении рекламы"""
    try:
        telegram_user_id = get_user_id_from_request()
        data = request.get_json()

        if not data or 'post_url' not in data:
            return jsonify({'success': False, 'error': 'Не указана ссылка на пост'}), 400

        post_url = data['post_url'].strip()

        # Проверяем контракт
        contract = execute_db_query('''
            SELECT c.*, u.telegram_id as publisher_telegram_id
            FROM contracts c
            JOIN users u ON c.publisher_id = u.id
            WHERE c.id = ?
              AND u.telegram_id = ?
              AND c.status = 'active'
        ''', (contract_id, telegram_user_id), fetch_one=True)

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден или недоступен'}), 404

        # Проверяем дедлайн
        placement_deadline = datetime.fromisoformat(contract['placement_deadline'])
        if datetime.now() > placement_deadline:
            execute_db_query('UPDATE contracts SET status = ? WHERE id = ?', ('expired', contract_id))
            return jsonify({'success': False, 'error': 'Срок размещения истек'}), 400

        # Простое извлечение message_id из URL (упрощенная версия)
        message_id = None
        if 't.me/' in post_url and '/' in post_url.split('t.me/')[-1]:
            try:
                message_id = post_url.split('/')[-1]
                if not message_id.isdigit():
                    message_id = None
            except:
                pass

        if not message_id:
            return jsonify({'success': False, 'error': 'Некорректная ссылка на пост'}), 400

        # Обновляем контракт
        execute_db_query('''
            UPDATE contracts
            SET post_url = ?,
                post_id = ?,
                status = 'verification',
                submitted_at = ?
            WHERE id = ?
        ''', (post_url, message_id, datetime.now().isoformat(), contract_id))

        logger.info(f"Подана заявка о размещении для контракта {contract_id}")

        return jsonify({
            'success': True,
            'message': 'Заявка о размещении подана! Начинается автоматическая проверка.',
            'contract_id': contract_id
        })

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

        # Получаем данные контракта
        contract = execute_db_query('''
            SELECT c.*,
                   o.title as offer_title,
                   u_adv.telegram_id as advertiser_telegram_id,
                   u_pub.telegram_id as publisher_telegram_id
            FROM contracts c
            JOIN offers o ON c.offer_id = o.id
            JOIN users u_adv ON c.advertiser_id = u_adv.id
            JOIN users u_pub ON c.publisher_id = u_pub.id
            WHERE c.id = ?
        ''', (contract_id,), fetch_one=True)

        if not contract:
            return jsonify({'success': False, 'error': 'Контракт не найден'}), 404

        # Проверяем права доступа
        if (contract['advertiser_telegram_id'] != telegram_user_id and
                contract['publisher_telegram_id'] != telegram_user_id):
            return jsonify({'success': False, 'error': 'Нет доступа к этому контракту'}), 403

        # Проверяем статус
        deletable_statuses = ['verification_failed', 'cancelled']
        if contract['status'] not in deletable_statuses:
            return jsonify({
                'success': False,
                'error': f'Можно удалять только контракты со статусами: {", ".join(deletable_statuses)}'
            }), 400

        # Удаляем связанные записи и контракт в транзакции
        import sqlite3
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute('BEGIN TRANSACTION')

        try:
            conn.execute('DELETE FROM monitoring_tasks WHERE contract_id = ?', (contract_id,))
            conn.execute('DELETE FROM payments WHERE contract_id = ?', (contract_id,))
            conn.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))
            
            conn.commit()

            return jsonify({
                'success': True,
                'message': f'Контракт "{contract["offer_title"]}" удален'
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при удалении контракта: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении контракта'}), 500
        finally:
            conn.close()

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

        # Извлечение информации о посте из Telegram URL
        import re

        if not post_url or not isinstance(post_url, str):
            return jsonify({'success': False, 'error': 'Некорректная ссылка'}), 400

        patterns = [
            r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://telegram\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://t\.me/c/(\d+)/(\d+)',
            r't\.me/([a-zA-Z0-9_]+)/(\d+)',
            r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)\?.*'
        ]

        result = None
        for pattern in patterns:
            match = re.search(pattern, post_url.strip())
            if match:
                channel_identifier = match.group(1)
                message_id = match.group(2)

                # Для приватных каналов добавляем префикс -100
                if channel_identifier.isdigit() and not channel_identifier.startswith('-100'):
                    channel_identifier = f'-100{channel_identifier}'

                result = {
                    'success': True,
                    'channel_username': channel_identifier,
                    'message_id': message_id,
                    'url_type': 'private' if channel_identifier.isdigit() else 'public',
                    'original_url': post_url
                }
                break

        if not result:
            result = {
                'success': False,
                'error': 'Неверный формат URL. Ожидаемые форматы: https://t.me/channel/123'
            }

        return jsonify({
            'success': True,
            'debug_result': result,
            'url': post_url
        })

    except Exception as e:
        logger.error(f"Ошибка диагностики поста: {e}")
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