# app/api/offers.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ

import json
import logging
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from app.config.telegram_config import AppConfig
from app.models.database import db_manager
from flask import Blueprint, request, jsonify
import os
from app.models import execute_db_query
from app.services.auth_service import auth_service
logger = logging.getLogger(__name__)

# === BLUEPRINT ===
offers_bp = Blueprint('offers', __name__)


# === API ENDPOINTS ===

@offers_bp.route('', methods=['GET'])
def get_available_offers():
    """Получение доступных офферов для владельцев каналов"""
    try:
        # Получаем параметры фильтрации
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        
        status_filter = request.args.get('status', 'active')
        search = request.args.get('search', '')
        category_filter = request.args.get('category', '')
        
        # Получаем текущего пользователя
        telegram_id = auth_service.get_current_user_id()
        user_db_id = None
        
        if telegram_id:
            user = execute_db_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )
            if user:
                user_db_id = user['id']
        
        # Базовый запрос для получения доступных офферов
        base_query = '''
            SELECT o.*, u.username as creator_username, u.first_name as creator_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE 1=1
        '''
        
        count_query = '''
            SELECT COUNT(*) as total
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE 1=1
        '''
        
        params = []
        
        # Фильтр по статусу (по умолчанию только активные)
        # Если статус не указан явно или пустой, используем 'active'
        if not status_filter:
            status_filter = 'active'
        
        base_query += ' AND o.status = ?'
        count_query += ' AND o.status = ?'
        params.append(status_filter)
        
        # Исключаем собственные офферы пользователя
        if user_db_id:
            base_query += ' AND o.created_by != ?'
            count_query += ' AND o.created_by != ?'
            params.append(user_db_id)
        
        # Фильтр по поиску
        if search:
            base_query += ' AND (o.title LIKE ? OR o.description LIKE ?)'
            count_query += ' AND (o.title LIKE ? OR o.description LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])
        
        # Фильтр по категории
        if category_filter:
            base_query += ' AND o.category = ?'
            count_query += ' AND o.category = ?'
            params.append(category_filter)
        
        # Получаем общее количество
        total_count = execute_db_query(count_query, tuple(params), fetch_one=True)['total']
        
        # Добавляем сортировку и пагинацию
        base_query += ' ORDER BY o.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        # Получаем офферы
        offers = execute_db_query(base_query, tuple(params), fetch_all=True)
        
        # Форматируем данные
        formatted_offers = []
        for offer in offers:
            # Парсим метаданные
            try:
                metadata = json.loads(offer.get('metadata', '{}')) if offer.get('metadata') else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            
            formatted_offers.append({
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'price': offer['price'],
                'budget_total': offer['budget_total'],
                'currency': offer['currency'],
                'target_audience': offer['target_audience'],
                'requirements': offer['requirements'],
                'category': offer['category'],
                'status': offer['status'],
                'created_at': offer['created_at'],
                'expires_at': offer['expires_at'],
                'creator_username': offer['creator_username'],
                'creator_name': offer['creator_name'],
                'metadata': metadata
            })
        
        total_pages = (total_count + limit - 1) // limit
        
        logger.info(f"Найдено доступных офферов: {len(formatted_offers)} из {total_count}")
        
        return jsonify({
            'success': True,
            'offers': formatted_offers,
            'count': len(formatted_offers),
            'total_count': total_count,
            'page': page,
            'total_pages': total_pages
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@offers_bp.route('', methods=['POST'])
def create_offer():
    """Создание нового оффера"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Получаем текущего пользователя через единую систему авторизации
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        logger.info(f"Создание оффера пользователем telegram_id={telegram_id}")

        # Базовая валидация обязательных полей
        required_fields = ['title', 'description', 'price', 'target_audience']
        errors = []
        
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400

        # Получаем/создаем пользователя в БД через единую систему
        user_db_id = auth_service.ensure_user_exists(
            username=data.get('username'),
            first_name=data.get('first_name')
        )
        
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка создания пользователя'}), 500
            
        logger.info(f"Пользователь telegram_id={telegram_id} → db_id={user_db_id}")

        # Подготавливаем данные для оффера
        metadata = {
            'posting_requirements': data.get('posting_requirements', {}),
            'additional_info': data.get('additional_info', ''),
            'creator_telegram_id': telegram_id
        }

        # Определяем статус оффера (draft или active)
        initial_status = data.get('status', 'active')  # По умолчанию active, но можно передать draft
        
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
            initial_status,
            data.get('category', 'general'),
            json.dumps(metadata),
            float(data.get('budget_total', data['price'])),
            data.get('expires_at'),
            int(data.get('duration_days', 30)),
            int(data.get('min_subscribers', 0)),
            int(data.get('max_subscribers', 0))
        ))

        logger.info(f"Создан новый оффер {offer_id} пользователем {telegram_id}")
        
        # Создаем предложения для выбранных каналов
        if data.get('selected_channels'):
            channel_ids = data['selected_channels']
            for channel_id in channel_ids:
                execute_db_query('''
                    INSERT OR IGNORE INTO offer_proposals 
                    (offer_id, channel_id, status, expires_at, notified_at) 
                    VALUES (?, ?, 'sent', datetime('now', '+7 days'), CURRENT_TIMESTAMP)
                ''', (offer_id, channel_id))
            
            logger.info(f"Созданы предложения для {len(channel_ids)} каналов")
            
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

        # Получаем telegram_id через единую систему авторизации
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

        # Получаем информацию о пользователе для логирования
        user = execute_db_query(
            'SELECT id, telegram_id, username FROM users WHERE telegram_id = ?',
            (telegram_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"Пользователь с telegram_id {telegram_id} не найден в БД")
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        user_db_id = user['id']
        logger.info(f"Поиск офферов для пользователя: db_id={user_db_id}, telegram_id={user['telegram_id']}, username={user['username']}")

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
                            u.first_name as creator_name, \
                            u.telegram_id as creator_telegram_id, \
                            o.created_by as creator_db_id
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
        total_count = execute_db_query(count_query, tuple(params), fetch_one=True)['total']

        # Добавляем сортировку и пагинацию
        base_query += ' ORDER BY o.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        # Получаем офферы
        offers = execute_db_query(base_query, tuple(params), fetch_all=True)
        logger.info(f"Найдено офферов: {len(offers)} (всего в БД: {total_count}) для пользователя db_id={user_db_id}")
        
        # Отладочная информация
        if len(offers) == 0 and total_count == 0:
            logger.warning(f"Нет офферов для пользователя db_id={user_db_id}. Проверим последние офферы в БД:")
            debug_offers = execute_db_query(
                'SELECT id, title, created_by FROM offers ORDER BY created_at DESC LIMIT 5',
                fetch_all=True
            )
            for offer in debug_offers:
                logger.warning(f"  Оффер id={offer['id']}, title={offer['title']}, created_by={offer['created_by']}")

        if not offers:
            return jsonify({
                'success': True,
                'offers': [],
                'count': 0,
                'total_count': total_count,
                'page': page,
                'total_pages': 0,
                'user_id': user_db_id
            })

        # ОПТИМИЗИРОВАННЫЙ подсчет откликов одним запросом
        offer_ids = [str(offer['id']) for offer in offers]
        offer_ids_str = ','.join(offer_ids)

        # Получаем статистику откликов для всех офферов одним запросом
        response_stats = execute_db_query(f'''
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
            'user_db_id': user_db_id,
            'telegram_id': user['telegram_id'],

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
  
@offers_bp.route('/stats', methods=['GET'])
def get_offers_stats():
    """Статистика офферов пользователя"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅

        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,),
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
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅
        logger.info(f"Запрос на удаление оффера {offer_id} от пользователя {telegram_id}")

        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,),
            fetch_one=True
        )
        
        logger.info(f"Поиск пользователя с telegram_id={telegram_id}, результат: {user}")

        if not user:
            logger.error(f"Пользователь с telegram_id={telegram_id} не найден в базе")
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Получаем оффер
        offer = execute_db_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )
        
        logger.info(f"Поиск оффера с id={offer_id}, результат: {offer}")

        if not offer:
            logger.error(f"Оффер с id={offer_id} не найден в базе")
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        logger.info(f"Проверка прав: offer created_by={offer['created_by']}, user id={user['id']}")
        if offer['created_by'] != user['id']:
            logger.error(f"Пользователь {user['id']} не имеет прав на удаление оффера {offer_id} (владелец: {offer['created_by']})")
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

            logger.info(f"Оффер {offer_id} удален пользователем {telegram_id}")

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
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅
        data = request.get_json()

        new_status = data.get('status')
        reason = data.get('reason', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Статус не указан'}), 400

        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,),
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
                telegram_id = auth_service.get_current_user_id()
                if not telegram_id:
                    return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅
                data = request.get_json()

                channel_id = data.get('channel_id')
                message = data.get('message', '').strip()

                if not channel_id or not message:
                    return jsonify({'success': False, 'error': 'Канал и сообщение обязательны'}), 400

                # Получаем данные канала для создания отклика
                user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,),
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

                # Получаем информацию об оффере для уведомления
                offer = execute_db_query("""
                    SELECT o.*, u.telegram_id as owner_telegram_id, u.first_name, u.username as owner_username
                    FROM offers o
                    JOIN users u ON o.created_by = u.id
                    WHERE o.id = ?
                """, (offer_id,), fetch_one=True)

                if not offer:
                    return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

                # Проверяем, есть ли уже отклик от этого пользователя с этим каналом
                existing_response = execute_db_query("""
                    SELECT id, status, created_at
                    FROM offer_responses
                    WHERE offer_id = ? AND user_id = ? AND channel_id = ?
                """, (offer_id, user['id'], channel_id), fetch_one=True)

                if existing_response:
                    status = existing_response['status']
                    created_at = existing_response['created_at']
                    
                    # Формируем подходящее сообщение об ошибке в зависимости от статуса
                    if status == 'pending':
                        return jsonify({
                            'success': False, 
                            'error': 'Вы уже отправили отклик на этот оффер. Дождитесь ответа рекламодателя.',
                            'existing_response': {
                                'id': existing_response['id'],
                                'status': status,
                                'created_at': created_at
                            }
                        }), 409
                    elif status == 'accepted':
                        return jsonify({
                            'success': False, 
                            'error': 'Ваш отклик уже принят рекламодателем. Повторный отклик невозможен.',
                            'existing_response': {
                                'id': existing_response['id'],
                                'status': status,
                                'created_at': created_at
                            }
                        }), 409
                    elif status == 'rejected':
                        return jsonify({
                            'success': False, 
                            'error': 'Ваш отклик был отклонен рекламодателем. Повторный отклик невозможен.',
                            'existing_response': {
                                'id': existing_response['id'],
                                'status': status,
                                'created_at': created_at
                            }
                        }), 409
                    else:
                        # Для других статусов (viewed, etc.)
                        return jsonify({
                            'success': False, 
                            'error': f'Вы уже отправили отклик на этот оффер (статус: {status}). Повторный отклик невозможен.',
                            'existing_response': {
                                'id': existing_response['id'],
                                'status': status,
                                'created_at': created_at
                            }
                        }), 409

                # Дополнительная проверка: нельзя откликаться на собственный оффер
                if offer['owner_telegram_id'] == telegram_id:
                    return jsonify({
                        'success': False, 
                        'error': 'Вы не можете откликаться на собственный оффер'
                    }), 403

                # Проверяем статус оффера
                if offer['status'] != 'active':
                    return jsonify({
                        'success': False, 
                        'error': f'Оффер неактивен (статус: {offer["status"]}). Отклик невозможен.'
                    }), 400

                # Создаем отклик
                response_id = execute_db_query("""
                                               INSERT INTO offer_responses (offer_id, user_id, channel_id, message,
                                                                            status,
                                                                            channel_title, channel_username,
                                                                            channel_subscribers, created_at, updated_at)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                               """, (
                                                   offer_id, user['id'], channel['id'], message, 'pending',
                                                   channel.get('title', ''), channel.get('username', ''),
                                                   channel.get('subscriber_count', 0)
                                               ))

                # Отправляем немедленное уведомление рекламодателю
                try:
                    from app.telegram.telegram_notifications import TelegramNotificationService
                    
                    # Получаем данные отправителя отклика
                    sender = execute_db_query("""
                        SELECT first_name, last_name, username, telegram_id
                        FROM users WHERE id = ?
                    """, (user['id'],), fetch_one=True)
                    
                    # Формируем имя отправителя
                    sender_name = []
                    if sender.get('first_name'):
                        sender_name.append(sender['first_name'])
                    if sender.get('last_name'):
                        sender_name.append(sender['last_name'])
                    full_name = ' '.join(sender_name) if sender_name else sender.get('username', 'Администратор')
                    
                    # Формируем уведомление
                    notification_text = f"📬 <b>Новый отклик на ваш оффер!</b>\n\n"
                    notification_text += f"🎯 <b>Оффер:</b> {offer['title']}\n"
                    notification_text += f"📺 <b>Канал:</b> @{channel.get('username', 'канал')} ({channel.get('subscriber_count', 0):,} подписчиков)\n"
                    notification_text += f"👤 <b>Администратор:</b> {full_name}\n\n"
                    notification_text += f"💬 <b>Сообщение:</b>\n{message}\n\n"
                    notification_text += f"📱 Посмотрите детали в приложении"
                    
                    # Отправляем уведомление
                    TelegramNotificationService.send_telegram_notification(
                        offer['owner_telegram_id'],
                        notification_text,
                        {
                            'type': 'new_response',
                            'offer_id': offer_id,
                            'response_id': response_id,
                            'channel_id': channel['id']
                        }
                    )
                    
                    logger.info(f"✅ Уведомление о новом отклике отправлено рекламодателю {offer['owner_telegram_id']}")
                    
                except Exception as notification_error:
                    logger.error(f"❌ Ошибка отправки уведомления о новом отклике: {notification_error}")
                    # Не прерываем выполнение, если уведомление не отправилось

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
                telegram_id = auth_service.get_current_user_id()
                if not telegram_id:
                    return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅

                # Проверяем права доступа к офферу
                offer = execute_db_query("""
                                         SELECT o.*, u.telegram_id as owner_telegram_id
                                         FROM offers o
                                                  JOIN users u ON o.created_by = u.id
                                         WHERE o.id = ?
                                         """, (offer_id,), fetch_one=True)

                if not offer:
                    return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

                if offer['owner_telegram_id'] != telegram_id:
                    return jsonify({'success': False, 'error': 'Нет доступа к этому офферу'}), 403

                # Получаем отклики с информацией о размещениях
                responses = execute_db_query("""
                                             SELECT or_resp.*,
                                                    u.first_name || ' ' || COALESCE(u.last_name, '') as channel_owner_name,
                                                    u.username                                       as channel_owner_username,
                                                    u.telegram_id                                    as channel_owner_telegram_id,
                                                    pl.id as placement_id,
                                                    pl.status as placement_status,
                                                    pl.deadline as placement_deadline,
                                                    pl.funds_reserved,
                                                    pl.ereit_token,
                                                    pl.generated_post_text,
                                                    pl.created_at as placement_created_at
                                             FROM offer_responses or_resp
                                                      JOIN users u ON or_resp.user_id = u.id
                                                      LEFT JOIN offer_placements pl ON or_resp.id = pl.response_id
                                             WHERE or_resp.offer_id = ?
                                             ORDER BY or_resp.created_at DESC
                                             """, (offer_id,), fetch_all=True)

                # Форматируем отклики
                formatted_responses = []
                for response in responses:
                    # Добавляем информацию о размещении, если она есть
                    placement = None
                    if response.get('placement_id'):
                        placement = {
                            'id': response['placement_id'],
                            'status': response['placement_status'],
                            'deadline': response['placement_deadline'],
                            'funds_reserved': response['funds_reserved'],
                            'ereit_token': response['ereit_token'],
                            'generated_post_text': response['generated_post_text'],
                            'created_at': response['placement_created_at']
                        }
                    
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
                        'channel_owner_telegram_id': response['channel_owner_telegram_id'],
                        'placement': placement
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
    """Обновление статуса отклика с автоматическими действиями при принятии"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        # Получаем или создаем пользователя в БД
        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500
        
        data = request.get_json()
        new_status = data.get('status')
        message = data.get('message', '')

        if not new_status:
            return jsonify({'success': False, 'error': 'Статус не указан'}), 400

        # Получаем полные данные отклика с информацией о канале и пользователе
        response_data = execute_db_query('''
            SELECT or_resp.*,
                o.created_by,
                o.title as offer_title,
                o.description as offer_description,
                o.price as offer_price,
                o.budget_total,
                o.content,
                u.telegram_id as author_telegram_id,
                u.first_name as author_first_name,
                u.last_name as author_last_name,
                u.username as author_username,
                ch.title as channel_title,
                ch.username as channel_username,
                ch.subscriber_count,
                ch_owner.telegram_id as channel_owner_telegram_id,
                ch_owner.first_name as channel_owner_first_name,
                ch_owner.last_name as channel_owner_last_name,
                ch_owner.username as channel_owner_username
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            JOIN users u ON o.created_by = u.id
            JOIN channels ch ON or_resp.channel_id = ch.id
            JOIN users ch_owner ON ch.owner_id = ch_owner.id
            WHERE or_resp.id = ?
        ''', (response_id,), fetch_one=True)

        if not response_data:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        if response_data['author_telegram_id'] != telegram_id:
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

        if new_status == 'accepted':
            # === АВТОМАТИЧЕСКИЕ ДЕЙСТВИЯ ПРИ ПРИНЯТИИ ===
            
            # 1. Отклоняем остальные отклики
            execute_db_query('''
                UPDATE offer_responses
                SET status = 'rejected',
                    updated_at = ?,
                    admin_message = 'Автоматически отклонен (выбран другой канал)'
                WHERE offer_id = ?
                AND id != ? AND status = 'pending'
            ''', (datetime.now().isoformat(), response_data['offer_id'], response_id))
            
            # 2. Резервирование средств (заглушка)
            offer_price = float(response_data['budget_total'] or response_data['offer_price'] or 0)
            reserved_amount = offer_price
            
            # Функция резервирования средств (пока заглушка)
            def reserve_funds(user_id, amount):
                """Заглушка для резервирования средств"""
                logger.info(f"💰 Резервирование {amount} руб. для пользователя {user_id}")
                return True  # Всегда успешно пока что
            
            funds_reserved = reserve_funds(user_db_id, reserved_amount)
            
            # 3. Генерация eREIT токена
            import uuid
            import hashlib
            ereit_token = f"EREIT_{str(uuid.uuid4())[:8].upper()}"
            
            # 4. Генерация рекламного поста
            generated_post = generate_ad_post(response_data, ereit_token)
            
            # 5. Установка дедлайна (24 часа)
            from datetime import timedelta
            placement_deadline = datetime.now() + timedelta(hours=24)
            
            # 6. Создание записи в offer_placements
            placement_id = execute_db_query('''
                INSERT INTO offer_placements (
                    proposal_id,
                    response_id, 
                    status, 
                    deadline, 
                    placement_deadline,
                    funds_reserved,
                    reserved_at,
                    generated_post_text,
                    ereit_token,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response_id,  # proposal_id - используем response_id как временную замену
                response_id,  # response_id
                'pending_placement',
                placement_deadline.isoformat(),
                placement_deadline.isoformat(),
                reserved_amount,
                datetime.now().isoformat(),
                generated_post,
                ereit_token,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # 7. Отправка уведомления владельцу канала
            try:
                from app.telegram.telegram_notifications import TelegramNotificationService
                
                # Форматируем дату дедлайна
                deadline_str = placement_deadline.strftime("%d %B, %H:%M")
                
                # Создаем уведомление
                notification_text = f"""✅ <b>Ваше предложение принято!</b>

🎯 <b>Оффер:</b> {response_data['offer_title']}
💰 <b>Оплата:</b> {reserved_amount:,.0f} руб.
📅 <b>Разместить до:</b> {deadline_str}

📝 <b>Рекламный пост:</b>
{generated_post}

⚡ <b>Действия:</b>
1. Скопируйте текст выше
2. Опубликуйте в канале @{response_data['channel_username']}
3. Подтвердите размещение командой /post_published

⏰ <b>У вас есть 24 часа для размещения</b>"""
                
                success = TelegramNotificationService.send_telegram_notification(
                    response_data['channel_owner_telegram_id'],
                    notification_text,
                    {
                        'type': 'offer_accepted',
                        'offer_id': response_data['offer_id'],
                        'response_id': response_id,
                        'placement_id': placement_id,
                        'ereit_token': ereit_token
                    }
                )
                
                if success:
                    logger.info(f"✅ Уведомление о принятии отправлено владельцу канала {response_data['channel_owner_telegram_id']}")
                else:
                    logger.error(f"❌ Не удалось отправить уведомление владельцу канала {response_data['channel_owner_telegram_id']}")
                    
            except Exception as notification_error:
                logger.error(f"❌ Ошибка отправки уведомления о принятии: {notification_error}")
            
            result = {
                'success': True,
                'message': f'Отклик принят! Владелец канала получил уведомление с инструкциями по размещению.',
                'placement_id': placement_id,
                'deadline': placement_deadline.isoformat(),
                'reserved_amount': reserved_amount,
                'ereit_token': ereit_token
            }
        else:
            # Для отклонения отправляем обычное уведомление
            result = {
                'success': True,
                'message': f'Отклик отклонён. Пользователь получил уведомление.'
            }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Ошибка обновления статуса отклика: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_ad_post(response_data, ereit_token):
    """Генерация рекламного поста с eREIT токеном"""
    try:
        # Базовый текст из оффера
        base_text = response_data.get('ad_text') or response_data.get('content') or response_data.get('offer_description', '')
        
        # Если нет готового текста, создаем базовый
        if not base_text:
            base_text = f"🎯 {response_data['offer_title']}\n\n📢 Новое предложение для наших подписчиков!"
        
        # Добавляем eREIT токен
        post_text = f"""{base_text}

🔗 Подробности и участие: [ссылка с eREIT токеном]

💎 Код отслеживания: {ereit_token}
📊 Эксклюзивно для подписчиков @{response_data['channel_username']}"""
        
        return post_text
        
    except Exception as e:
        logger.error(f"Ошибка генерации рекламного поста: {e}")
        return f"🎯 {response_data.get('offer_title', 'Рекламное предложение')}\n\n💎 Код: {ereit_token}"

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

@offers_bp.route('/<int:offer_id>/my-responses', methods=['GET'])
def get_my_responses_for_offer(offer_id):
    """Получение откликов текущего пользователя на конкретный оффер"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

        # Получаем user_db_id
        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500

        # Проверяем, что оффер существует
        offer = execute_db_query("""
            SELECT id, title, status FROM offers WHERE id = ?
        """, (offer_id,), fetch_one=True)

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        # Получаем все отклики пользователя на этот оффер
        responses = execute_db_query("""
            SELECT 
                or_resp.id,
                or_resp.offer_id,
                or_resp.channel_id,
                or_resp.message,
                or_resp.status,
                or_resp.created_at,
                or_resp.updated_at,
                c.title as channel_title,
                c.username as channel_username,
                c.subscriber_count
            FROM offer_responses or_resp
            JOIN channels c ON or_resp.channel_id = c.id
            WHERE or_resp.offer_id = ? AND or_resp.user_id = ?
            ORDER BY or_resp.created_at DESC
        """, (offer_id, user_db_id), fetch_all=True)

        # Форматируем результат
        formatted_responses = []
        for response in responses:
            formatted_responses.append({
                'id': response['id'],
                'offer_id': response['offer_id'],
                'channel_id': response['channel_id'],
                'message': response['message'],
                'status': response['status'],
                'created_at': response['created_at'],
                'updated_at': response['updated_at'],
                'channel': {
                    'title': response['channel_title'],
                    'username': response['channel_username'],
                    'subscriber_count': response['subscriber_count']
                }
            })

        return jsonify({
            'success': True,
            'responses': formatted_responses,
            'offer': {
                'id': offer['id'],
                'title': offer['title'],
                'status': offer['status']
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения откликов пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@offers_bp.route('/placements/<int:placement_id>/cancel', methods=['PATCH'])
def cancel_placement(placement_id):
    """Отмена размещения рекламодателем"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500
        
        data = request.get_json()
        reason = data.get('reason', 'Отменено рекламодателем')
        
        # Получаем информацию о размещении
        placement = execute_db_query("""
            SELECT pl.*, or_resp.offer_id, o.created_by, o.title as offer_title,
                   ch.title as channel_title, ch.username as channel_username,
                   ch_owner.telegram_id as channel_owner_telegram_id
            FROM offer_placements pl
            JOIN offer_responses or_resp ON pl.response_id = or_resp.id
            JOIN offers o ON or_resp.offer_id = o.id
            JOIN channels ch ON or_resp.channel_id = ch.id
            JOIN users ch_owner ON ch.owner_id = ch_owner.id
            WHERE pl.id = ?
        """, (placement_id,), fetch_one=True)
        
        if not placement:
            return jsonify({'success': False, 'error': 'Размещение не найдено'}), 404
        
        # Проверяем права доступа
        if placement['created_by'] != user_db_id:
            return jsonify({'success': False, 'error': 'Нет прав для отмены размещения'}), 403
        
        # Проверяем, что размещение можно отменить
        if placement['status'] not in ['pending_placement']:
            return jsonify({'success': False, 'error': 'Размещение нельзя отменить в текущем статусе'}), 400
        
        # Отменяем размещение
        execute_db_query("""
            UPDATE offer_placements
            SET status = 'cancelled',
                cancellation_reason = ?,
                cancelled_at = ?,
                cancelled_by = ?,
                updated_at = ?
            WHERE id = ?
        """, (reason, datetime.now().isoformat(), user_db_id, datetime.now().isoformat(), placement_id))
        
        # Обновляем статус отклика
        execute_db_query("""
            UPDATE offer_responses
            SET status = 'cancelled',
                updated_at = ?,
                admin_message = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), f'Размещение отменено: {reason}', placement['response_id']))
        
        # Отправляем уведомление владельцу канала
        try:
            from app.telegram.telegram_notifications import TelegramNotificationService
            
            notification_text = f"""🚫 <b>Размещение отменено</b>

🎯 <b>Оффер:</b> {placement['offer_title']}
📺 <b>Канал:</b> @{placement['channel_username']}
💰 <b>Сумма:</b> {placement['funds_reserved']} руб.

📝 <b>Причина:</b> {reason}

💡 Средства не были списаны с вашего баланса."""
            
            TelegramNotificationService.send_telegram_notification(
                placement['channel_owner_telegram_id'],
                notification_text,
                {
                    'type': 'placement_cancelled',
                    'placement_id': placement_id,
                    'offer_id': placement['offer_id']
                }
            )
            
            logger.info(f"✅ Уведомление об отмене размещения отправлено владельцу канала {placement['channel_owner_telegram_id']}")
            
        except Exception as notification_error:
            logger.error(f"❌ Ошибка отправки уведомления об отмене: {notification_error}")
        
        return jsonify({
            'success': True,
            'message': 'Размещение успешно отменено',
            'placement_id': placement_id
        })
        
    except Exception as e:
        logger.error(f"Ошибка отмены размещения: {e}")
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
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401  # ✅

        user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,), fetch_one=True)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        # Получаем сводную статистику одним запросом
        summary = execute_db_query("""
                                   SELECT COUNT(DISTINCT o.id)                                                     as total_offers,
                                          COUNT(DISTINCT CASE WHEN o.status = 'active' THEN o.id END)              as active_offers,
                                          COUNT(DISTINCT or_resp.id)                                               as total_responses,
                                          COUNT(DISTINCT CASE WHEN or_resp.status = 'pending' THEN or_resp.id END) as pending_responses,
                                          COALESCE(
                                                  SUM(CASE WHEN o.status IN ('completed', 'active') THEN o.price ELSE 0 END),
                                                  0)                                                               as total_budget
                                   FROM offers o
                                            LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                                   WHERE o.created_by = ?
                                   """, (user['id'],), fetch_one=True)

        return jsonify({
            'success': True,
            'summary': {
                'total_offers': summary['total_offers'] or 0,
                'active_offers': summary['active_offers'] or 0,
                'total_responses': summary['total_responses'] or 0,
                'pending_responses': summary['pending_responses'] or 0,
                'total_budget': float(summary['total_budget']) if summary['total_budget'] else 0
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения сводки: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@offers_bp.route('/<int:offer_id>', methods=['GET'])
def get_offer_details(offer_id):
    """Получение деталей конкретного оффера"""
    try:
        # Проверяем авторизацию
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        user_db_id = user['id']
        
        # Получаем оффер
        offer = execute_db_query(
            'SELECT * FROM offers WHERE id = ? AND created_by = ?',
            (offer_id, user_db_id),
            fetch_one=True
        )
        
        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404
        
        # Преобразуем в словарь для JSON
        offer_data = dict(offer)
        
        # Парсим metadata если есть
        if offer_data.get('metadata'):
            try:
                offer_data['metadata'] = json.loads(offer_data['metadata'])
            except:
                offer_data['metadata'] = {}
        
        return jsonify({
            'success': True,
            'offer': offer_data
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей оффера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/<int:offer_id>', methods=['PATCH'])
def update_offer_status_endpoint(offer_id):
    """Обновление статуса оффера"""
    try:
        # Проверяем авторизацию
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        # Получаем или создаем пользователя в БД
        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500
        
        # Проверяем, что оффер существует и принадлежит пользователю
        offer = execute_db_query(
            'SELECT * FROM offers WHERE id = ? AND created_by = ?',
            (offer_id, user_db_id),
            fetch_one=True
        )
        
        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404
        
        # Получаем новый статус из запроса
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Необходимо указать статус'}), 400
        
        new_status = data['status']
        if new_status not in ['draft', 'active', 'paused', 'completed']:
            return jsonify({'success': False, 'error': 'Недопустимый статус'}), 400
        
        # Обновляем статус
        execute_db_query(
            'UPDATE offers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_status, offer_id)
        )
        
        logger.info(f"Обновлен статус оффера {offer_id} на {new_status}")
        
        return jsonify({
            'success': True,
            'message': f'Статус оффера изменен на {new_status}',
            'offer_id': offer_id,
            'status': new_status
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка обновления статуса оффера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/<int:offer_id>/complete-draft', methods=['POST'])
def complete_draft_offer(offer_id):
    """Завершение создания оффера из черновика"""
    try:
        # Проверяем авторизацию
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        # Получаем пользователя
        user = execute_db_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        user_db_id = user['id']
        
        # Проверяем, что оффер существует и принадлежит пользователю
        offer = execute_db_query(
            'SELECT * FROM offers WHERE id = ? AND created_by = ?',
            (offer_id, user_db_id),
            fetch_one=True
        )
        
        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден'}), 404
        
        # Проверяем, что оффер в статусе draft
        if offer['status'] != 'draft':
            return jsonify({'success': False, 'error': 'Оффер уже завершен'}), 400
        
        # Получаем выбранные каналы из запроса
        data = request.get_json()
        if not data or 'channel_ids' not in data:
            return jsonify({'success': False, 'error': 'Необходимо выбрать каналы'}), 400
        
        channel_ids = data['channel_ids']
        if not channel_ids or not isinstance(channel_ids, list):
            return jsonify({'success': False, 'error': 'Необходимо выбрать хотя бы один канал'}), 400
        
        # Обновляем статус оффера на active
        execute_db_query(
            'UPDATE offers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('active', offer_id)
        )
        
        # Создаем предложения для выбранных каналов (копируем логику из основного создания)
        created_proposals = []
        for channel_id in channel_ids:
            # Проверяем, что канал существует
            channel = execute_db_query(
                'SELECT id, title FROM channels WHERE id = ? AND is_active = 1',
                (channel_id,),
                fetch_one=True
            )
            
            if channel:
                # Создаем предложение
                proposal_id = execute_db_query('''
                    INSERT INTO offer_proposals (offer_id, channel_id, status, created_at)
                    VALUES (?, ?, 'sent', CURRENT_TIMESTAMP)
                ''', (offer_id, channel_id))
                
                created_proposals.append({
                    'id': proposal_id,
                    'channel_id': channel_id,
                    'channel_title': channel['title']
                })
        
        logger.info(f"Завершен черновик оффера {offer_id}, создано {len(created_proposals)} предложений")
        
        return jsonify({
            'success': True,
            'message': f'Оффер завершен и отправлен в {len(created_proposals)} каналов',
            'offer_id': offer_id,
            'proposals_created': len(created_proposals)
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка завершения черновика: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/responses/notifications', methods=['GET'])
def get_response_notifications():
    """Получение количества новых откликов для уведомлений"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

        # Получаем user_db_id
        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500

        # Получаем количество новых откликов (за последние 24 часа)
        new_responses = execute_db_query("""
            SELECT COUNT(*) as count
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            WHERE o.created_by = ? 
            AND or_resp.status = 'pending'
            AND or_resp.created_at > datetime('now', '-1 day')
        """, (user_db_id,), fetch_one=True)

        # Получаем общее количество непрочитанных откликов
        total_unread = execute_db_query("""
            SELECT COUNT(*) as count
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            WHERE o.created_by = ? 
            AND or_resp.status = 'pending'
        """, (user_db_id,), fetch_one=True)

        # Получаем количество офферов с новыми откликами
        offers_with_responses = execute_db_query("""
            SELECT COUNT(DISTINCT o.id) as count
            FROM offers o
            JOIN offer_responses or_resp ON o.id = or_resp.offer_id
            WHERE o.created_by = ? 
            AND or_resp.status = 'pending'
            AND or_resp.created_at > datetime('now', '-1 day')
        """, (user_db_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'notifications': {
                'new_responses_24h': new_responses['count'] or 0,
                'total_unread': total_unread['count'] or 0,
                'offers_with_new_responses': offers_with_responses['count'] or 0,
                'has_new_responses': (new_responses['count'] or 0) > 0
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения уведомлений об откликах: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/responses/<int:response_id>/mark-read', methods=['POST'])
def mark_response_as_read(response_id):
    """Отметить отклик как прочитанный"""
    try:
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

        user_db_id = auth_service.ensure_user_exists()
        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка получения пользователя'}), 500

        # Проверяем права доступа к отклику
        response = execute_db_query("""
            SELECT or_resp.*, o.created_by
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            WHERE or_resp.id = ? AND o.created_by = ?
        """, (response_id, user_db_id), fetch_one=True)

        if not response:
            return jsonify({'success': False, 'error': 'Отклик не найден'}), 404

        # Обновляем статус на просмотренный (если это был pending)
        if response['status'] == 'pending':
            execute_db_query("""
                UPDATE offer_responses 
                SET status = 'viewed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (response_id,))

        return jsonify({
            'success': True,
            'message': 'Отклик отмечен как прочитанный'
        })

    except Exception as e:
        logger.error(f"Ошибка отметки отклика как прочитанного: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


# === ЭКСПОРТ ===
__all__ = ['offers_bp']