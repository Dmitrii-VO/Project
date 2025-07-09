#!/usr/bin/env python3
"""
API для работы с предложениями
Endpoints для владельцев каналов
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
proposals_management_bp = Blueprint('proposals_management', __name__, url_prefix='/api/proposals')

# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================

def get_db_connection():
    """Получение соединения с базой данных"""
    try:
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None

def validate_proposal_ownership(proposal_id: int, user_id: int) -> bool:
    """Проверка принадлежности предложения владельцу канала"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT op.id 
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE op.id = ? AND c.owner_id = ?
        """, (proposal_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"Ошибка проверки владения предложением: {e}")
        return False

def get_proposal_details(proposal_id: int) -> Optional[Dict]:
    """Получение деталей предложения"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                op.id, op.offer_id, op.channel_id, op.status,
                op.created_at, op.responded_at, op.rejection_reason,
                op.expires_at, op.notified_at, op.reminder_sent_at,
                -- Информация об оффере
                o.title as offer_title, o.description as offer_description,
                o.budget as offer_budget, o.content as offer_content,
                o.placement_requirements, o.contact_info,
                o.placement_duration, o.expected_placement_duration,
                o.category as offer_category, o.target_audience,
                -- Информация о канале
                c.title as channel_title, c.username as channel_username,
                c.subscriber_count, c.category as channel_category,
                -- Информация о создателе оффера
                u.username as advertiser_username, u.first_name as advertiser_first_name,
                u.last_name as advertiser_last_name, u.telegram_id as advertiser_telegram_id
            FROM offer_proposals op
            JOIN offers o ON op.offer_id = o.id
            JOIN channels c ON op.channel_id = c.id
            JOIN users u ON o.created_by = u.id
            WHERE op.id = ?
        """, (proposal_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения деталей предложения: {e}")
        return None

def get_user_channels(user_id: int) -> List[Dict]:
    """Получение каналов пользователя"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, username, subscriber_count, category, is_verified
            FROM channels 
            WHERE owner_id = ? AND is_active = 1
            ORDER BY subscriber_count DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Ошибка получения каналов пользователя: {e}")
        return []

def update_proposal_status(proposal_id: int, new_status: str, rejection_reason: str = None) -> bool:
    """Обновление статуса предложения"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        if rejection_reason:
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = ?, responded_at = CURRENT_TIMESTAMP, rejection_reason = ?
                WHERE id = ?
            """, (new_status, rejection_reason, proposal_id))
        else:
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = ?, responded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, proposal_id))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка обновления статуса предложения: {e}")
        return False

def create_placement_record(proposal_id: int, expected_duration: int = 7) -> Optional[int]:
    """Создание записи о размещении"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offer_placements (
                proposal_id, expected_duration, status, created_at
            ) VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (proposal_id, expected_duration))
        
        placement_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return placement_id
    except Exception as e:
        logger.error(f"Ошибка создания записи о размещении: {e}")
        return None

def send_notification_to_advertiser(proposal_id: int, action: str, message: str = None):
    """Отправка уведомления рекламодателю"""
    try:
        # Получаем информацию о предложении
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return False
        
        # Формируем сообщение
        if action == 'accepted':
            notification_text = f"✅ Ваше предложение принято!\n\n"
            notification_text += f"📢 Канал: {proposal['channel_title']}\n"
            notification_text += f"💰 Оффер: {proposal['offer_title']}\n"
            notification_text += f"📅 Ожидайте размещения в течение 24 часов"
        
        elif action == 'rejected':
            notification_text = f"❌ Ваше предложение отклонено\n\n"
            notification_text += f"📢 Канал: {proposal['channel_title']}\n"
            notification_text += f"💰 Оффер: {proposal['offer_title']}\n"
            if message:
                notification_text += f"📝 Причина: {message}"
        
        elif action == 'placement_submitted':
            notification_text = f"📤 Пост размещен!\n\n"
            notification_text += f"📢 Канал: {proposal['channel_title']}\n"
            notification_text += f"💰 Оффер: {proposal['offer_title']}\n"
            notification_text += f"🔗 Ссылка: {message}"
        
        else:
            return False
        
        # TODO: Реализовать отправку уведомления через Telegram Bot
        # Пока что просто логируем
        logger.info(f"Уведомление рекламодателю (ID: {proposal['advertiser_telegram_id']}): {notification_text}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления рекламодателю: {e}")
        return False

# ================================================================
# API ENDPOINTS
# ================================================================

@proposals_management_bp.route('/incoming', methods=['GET'])
def get_incoming_proposals():
    """
    Получение входящих предложений для владельца канала
    
    GET /api/proposals/incoming
    
    Query Parameters:
    - status: фильтр по статусу (sent, accepted, rejected, expired)
    - channel_id: фильтр по каналу
    - limit: количество результатов (по умолчанию 50)
    - offset: смещение для пагинации (по умолчанию 0)
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Получаем параметры фильтрации
        status_filter = request.args.get('status')
        channel_id_filter = request.args.get('channel_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Ограничиваем лимит
        limit = min(limit, 100)
        
        # Получаем каналы пользователя
        user_channels = get_user_channels(user_id)
        if not user_channels:
            return jsonify({
                'success': True,
                'total_proposals': 0,
                'proposals': [],
                'user_channels': []
            }), 200
        
        # Формируем запрос
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # Базовый запрос
        where_conditions = ["c.owner_id = ?"]
        params = [user_id]
        
        # Добавляем фильтры
        if status_filter:
            where_conditions.append("op.status = ?")
            params.append(status_filter)
        
        if channel_id_filter:
            where_conditions.append("op.channel_id = ?")
            params.append(channel_id_filter)
        
        where_clause = " AND ".join(where_conditions)
        
        # Получаем общее количество
        count_query = f"""
            SELECT COUNT(*) as total
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            JOIN offers o ON op.offer_id = o.id
            WHERE {where_clause}
        """
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Получаем данные с пагинацией
        main_query = f"""
            SELECT 
                op.id, op.offer_id, op.channel_id, op.status,
                op.created_at, op.responded_at, op.expires_at,
                op.rejection_reason, op.notified_at,
                -- Информация об оффере
                o.title as offer_title, o.description as offer_description,
                o.budget as offer_budget, o.content as offer_content,
                o.placement_requirements, o.contact_info,
                o.placement_duration, o.expected_placement_duration,
                o.category as offer_category, o.target_audience,
                -- Информация о канале
                c.title as channel_title, c.username as channel_username,
                c.subscriber_count, c.category as channel_category,
                -- Информация о создателе оффера
                u.username as advertiser_username, u.first_name as advertiser_first_name,
                u.last_name as advertiser_last_name,
                -- Информация о размещении
                opl.id as placement_id, opl.post_url, opl.status as placement_status,
                opl.placement_start, opl.placement_end, opl.final_views_count,
                -- Дополнительная информация
                CASE 
                    WHEN op.expires_at < datetime('now') THEN 1
                    ELSE 0
                END as is_expired,
                CASE 
                    WHEN op.expires_at > datetime('now') THEN 
                        CAST((julianday(op.expires_at) - julianday('now')) * 24 AS INTEGER)
                    ELSE 0
                END as hours_until_expiry
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            JOIN offers o ON op.offer_id = o.id
            JOIN users u ON o.created_by = u.id
            LEFT JOIN offer_placements opl ON op.id = opl.proposal_id
            WHERE {where_clause}
            ORDER BY 
                CASE op.status
                    WHEN 'sent' THEN 1
                    WHEN 'accepted' THEN 2
                    WHEN 'rejected' THEN 3
                    WHEN 'expired' THEN 4
                    ELSE 5
                END,
                op.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(main_query, params + [limit, offset])
        proposals = cursor.fetchall()
        conn.close()
        
        # Формируем результат
        proposals_list = []
        for proposal in proposals:
            proposal_data = dict(proposal)
            
            # Добавляем дополнительную информацию
            proposal_data['is_expired'] = bool(proposal_data['is_expired'])
            proposal_data['can_respond'] = (
                proposal_data['status'] == 'sent' and 
                not proposal_data['is_expired']
            )
            
            # Рассчитываем предполагаемый доход
            if proposal_data['offer_budget'] and proposal_data['subscriber_count']:
                estimated_payment = min(
                    proposal_data['offer_budget'],
                    proposal_data['subscriber_count'] * 0.01  # 1 копейка за подписчика
                )
                proposal_data['estimated_payment'] = round(estimated_payment, 2)
            else:
                proposal_data['estimated_payment'] = 0
            
            proposals_list.append(proposal_data)
        
        # Формируем ответ
        response = {
            'success': True,
            'total_proposals': total_count,
            'proposals': proposals_list,
            'user_channels': user_channels,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'status': status_filter,
                'channel_id': channel_id_filter
            }
        }
        
        logger.info(f"Получены входящие предложения для пользователя {user_id}: {len(proposals_list)} из {total_count}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения входящих предложений: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/accept', methods=['POST'])
def accept_proposal(proposal_id: int):
    """
    Принятие предложения
    
    POST /api/proposals/{proposal_id}/accept
    
    Request Body:
    {
        "message": "Дополнительное сообщение (опционально)"
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'sent':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя принять предложение со статусом {proposal["status"]}'
            }), 400
        
        # Проверяем срок действия
        if proposal['expires_at'] and proposal['expires_at'] < datetime.now().isoformat():
            return jsonify({
                'error': 'Bad Request',
                'message': 'Срок действия предложения истек'
            }), 400
        
        # Получаем данные из запроса
        data = request.get_json() or {}
        message = data.get('message', '')
        
        # Обновляем статус предложения
        if not update_proposal_status(proposal_id, 'accepted'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка обновления статуса предложения'
            }), 500
        
        # Создаем запись о размещении
        placement_id = create_placement_record(
            proposal_id, 
            proposal['expected_placement_duration']
        )
        
        if not placement_id:
            # Откатываем изменения
            update_proposal_status(proposal_id, 'sent')
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка создания записи о размещении'
            }), 500
        
        # Отправляем уведомление рекламодателю
        send_notification_to_advertiser(proposal_id, 'accepted', message)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'placement_id': placement_id,
            'offer_title': proposal['offer_title'],
            'channel_title': proposal['channel_title'],
            'message': 'Предложение принято',
            'next_steps': [
                'Разместите пост в течение 24 часов',
                'Подтвердите размещение через API',
                'Ожидайте автоматической проверки'
            ]
        }
        
        logger.info(f"Предложение {proposal_id} принято пользователем {user_id}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка принятия предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/reject', methods=['POST'])
def reject_proposal(proposal_id: int):
    """
    Отклонение предложения
    
    POST /api/proposals/{proposal_id}/reject
    
    Request Body:
    {
        "reason": "Причина отклонения (обязательно)"
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'sent':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя отклонить предложение со статусом {proposal["status"]}'
            }), 400
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Отсутствует тело запроса'
            }), 400
        
        reason = data.get('reason', '').strip()
        if not reason:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Необходимо указать причину отклонения'
            }), 400
        
        if len(reason) > 500:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Причина отклонения не может быть длиннее 500 символов'
            }), 400
        
        # Обновляем статус предложения
        if not update_proposal_status(proposal_id, 'rejected', reason):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка обновления статуса предложения'
            }), 500
        
        # Отправляем уведомление рекламодателю
        send_notification_to_advertiser(proposal_id, 'rejected', reason)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'offer_title': proposal['offer_title'],
            'channel_title': proposal['channel_title'],
            'rejection_reason': reason,
            'message': 'Предложение отклонено'
        }
        
        logger.info(f"Предложение {proposal_id} отклонено пользователем {user_id}: {reason}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка отклонения предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/submit-placement', methods=['POST'])
def submit_placement(proposal_id: int):
    """
    Подтверждение размещения поста
    
    POST /api/proposals/{proposal_id}/submit-placement
    
    Request Body:
    {
        "post_url": "https://t.me/channel_username/123",
        "placement_notes": "Дополнительные заметки (опционально)"
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'accepted':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя подтвердить размещение для предложения со статусом {proposal["status"]}'
            }), 400
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Отсутствует тело запроса'
            }), 400
        
        post_url = data.get('post_url', '').strip()
        placement_notes = data.get('placement_notes', '').strip()
        
        # Валидация URL поста
        if not post_url:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Необходимо указать URL поста'
            }), 400
        
        if not post_url.startswith('https://t.me/'):
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL поста должен начинаться с https://t.me/'
            }), 400
        
        # Обновляем запись о размещении
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        try:
            # Получаем ID размещения
            cursor.execute("""
                SELECT id FROM offer_placements 
                WHERE proposal_id = ? AND status = 'pending'
            """, (proposal_id,))
            
            placement = cursor.fetchone()
            if not placement:
                conn.close()
                return jsonify({
                    'error': 'Not Found',
                    'message': 'Запись о размещении не найдена'
                }), 404
            
            placement_id = placement['id']
            
            # Обновляем запись о размещении
            cursor.execute("""
                UPDATE offer_placements 
                SET post_url = ?, placement_start = CURRENT_TIMESTAMP,
                    status = 'placed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (post_url, placement_id))
            
            # Создаем первую запись проверки
            cursor.execute("""
                INSERT INTO placement_checks (
                    placement_id, check_time, post_exists, 
                    views_count, check_status, response_data
                ) VALUES (?, CURRENT_TIMESTAMP, 1, 0, 'success', ?)
            """, (placement_id, json.dumps({
                'post_url': post_url,
                'placement_notes': placement_notes,
                'submitted_by': user_id,
                'submitted_at': datetime.now().isoformat()
            })))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка обновления размещения: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка обновления размещения'
            }), 500
        
        finally:
            conn.close()
        
        # Отправляем уведомление рекламодателю
        send_notification_to_advertiser(proposal_id, 'placement_submitted', post_url)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'placement_id': placement_id,
            'post_url': post_url,
            'offer_title': proposal['offer_title'],
            'channel_title': proposal['channel_title'],
            'message': 'Размещение подтверждено',
            'next_steps': [
                'Пост будет автоматически проверен в течение часа',
                'Система будет отслеживать пост до завершения кампании',
                'Вы получите уведомление о завершении'
            ]
        }
        
        logger.info(f"Размещение подтверждено для предложения {proposal_id}: {post_url}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения размещения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS
# ================================================================

@proposals_management_bp.route('/<int:proposal_id>/details', methods=['GET'])
def get_proposal_details_endpoint(proposal_id: int):
    """
    Получение детальной информации о предложении
    
    GET /api/proposals/{proposal_id}/details
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Получаем информацию о размещении
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # Получаем данные о размещении
        cursor.execute("""
            SELECT 
                id, post_url, placement_start, placement_end,
                expected_duration, status, final_views_count,
                created_at, updated_at
            FROM offer_placements
            WHERE proposal_id = ?
        """, (proposal_id,))
        
        placement = cursor.fetchone()
        
        # Получаем историю проверок
        if placement:
            cursor.execute("""
                SELECT 
                    check_time, post_exists, views_count, 
                    check_status, error_message
                FROM placement_checks
                WHERE placement_id = ?
                ORDER BY check_time DESC
                LIMIT 10
            """, (placement['id'],))
            
            checks = cursor.fetchall()
        else:
            checks = []
        
        conn.close()
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal': dict(proposal),
            'placement': dict(placement) if placement else None,
            'recent_checks': [dict(check) for check in checks]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@proposals_management_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Ресурс не найден'
    }), 404

@proposals_management_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Внутренняя ошибка сервера'
    }), 500