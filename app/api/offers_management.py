#!/usr/bin/env python3
"""
API для управления офферами
Новая система офферов с предложениями и размещениями
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from app.models.database import execute_db_query
from app.services.auth_service import auth_service
from app.config.telegram_config import AppConfig
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
offers_management_bp = Blueprint('offers_management', __name__)

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

def validate_offer_ownership(offer_id: int, user_db_id: int) -> bool:
    """Проверка принадлежности оффера пользователю"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error(f"Ошибка подключения к БД в validate_offer_ownership")
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_by FROM offers 
            WHERE id = ?
        """, (offer_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            logger.warning(f"Оффер {offer_id} не найден")
            return False
            
        offer_owner_id = result[0]
        is_owner = offer_owner_id == user_db_id
        
        logger.debug(f"Проверка владения оффером {offer_id}: owner_id={offer_owner_id}, user_db_id={user_db_id}, is_owner={is_owner}")
        
        return is_owner
    except Exception as e:
        logger.error(f"Ошибка проверки владения оффером: {e}")
        return False

def get_offer_details(offer_id: int) -> Optional[Dict]:
    """Получение деталей оффера"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, title, description, budget_total as budget, category, 
                target_audience, requirements as placement_requirements, 
                min_subscribers as min_subscriber_count, max_price as max_budget_per_post, 
                duration_days as placement_duration, status, created_by, created_at, expires_at
            FROM offers 
            WHERE id = ?
        """, (offer_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения деталей оффера: {e}")
        return None

def get_recommended_channels(offer_id: int) -> List[Dict]:
    """Получение верифицированных каналов кроме собственных"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Получаем детали оффера
        offer = get_offer_details(offer_id)
        if not offer:
            return []
        
        # Запрос с фильтрами верификации и статуса
        query = """
            SELECT 
                c.id, c.title, c.username, c.description,
                c.subscriber_count, c.category, c.language,
                c.is_verified, 
                u.username as owner_username,
                u.first_name as owner_first_name,
                -- Расчет совместимости
                CASE 
                    WHEN c.category = ? THEN 8
                    WHEN c.subscriber_count >= 1000 THEN 7
                    ELSE 6
                END as match_score,
                'not_sent' as proposal_status
            FROM channels c
            LEFT JOIN users u ON c.owner_id = u.id
            WHERE 
                c.is_active = 1 
                AND c.is_verified = 1
             
                AND c.subscriber_count > 0
                -- Исключаем только СВОИ каналы
                AND c.owner_id != ?
            ORDER BY c.subscriber_count DESC, c.is_verified DESC
            LIMIT 50
        """
        
        # Параметры: категория оффера и ID владельца оффера
        offer_category = offer.get('category', 'general')
        offer_owner_id = offer.get('created_by')
        
        cursor.execute(query, (offer_category, offer_owner_id))
        results = cursor.fetchall()
        
        channels = []
        for row in results:
            channel_dict = dict(row)
            channels.append(channel_dict)
        
        conn.close()
        
        logger.info(f"Найдено верифицированных каналов для оффера {offer_id}: {len(channels)}")
        
        return channels
        
    except Exception as e:
        logger.error(f"Ошибка получения каналов: {e}")
        return []
    
def update_offer_status(offer_id: int, new_status: str) -> bool:
    """Обновление статуса оффера"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE offers 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, offer_id))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка обновления статуса оффера: {e}")
        return False

# ================================================================
# API ENDPOINTS
# ================================================================

@offers_management_bp.route('/<int:offer_id>/recommended-channels', methods=['GET'])
def get_recommended_channels_for_offer(offer_id: int):
    """
    Get recommended channels for an offer
    
    GET /api/offers/{offer_id}/recommended-channels
    
    Query Parameters:
    - limit: number of channels to return (default 20)
    - category: filter by category
    - min_subscribers: minimum number of subscribers
    """
    try:
        # Get user ID from unified auth service
        user_id = auth_service.get_user_db_id()

        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401

        # Check if user owns the offer
        if not validate_offer_ownership(offer_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Offer does not belong to user'
            }), 403

        # Get offer details
        offer = get_offer_details(offer_id)
        if not offer:
            return jsonify({
                'error': 'Not Found',
                'message': 'Offer not found'
            }), 404

        # Get filter parameters
        limit = request.args.get('limit', 20, type=int)
        category = request.args.get('category')
        min_subscribers = request.args.get('min_subscribers', type=int)

        # Get recommended channels
        channels = get_recommended_channels(offer_id)

        # Apply additional filters
        if category:
            channels = [c for c in channels if c.get('category') == category]
        
        if min_subscribers:
            channels = [c for c in channels if c.get('subscriber_count', 0) >= min_subscribers]

        # Limit number of results
        channels = channels[:limit]

        # Form response
        response = {
            'success': True,
            'offer_id': offer_id,
            'offer_title': offer.get('title'),
            'offer_status': offer.get('status'),
            'total_channels': len(channels),
            'channels': channels,
            'filters': {
                'category': category,
                'min_subscribers': min_subscribers,
                'limit': limit
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting recommended channels: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Internal server error'
        }), 500


@offers_management_bp.route('/<int:offer_id>/select-channels', methods=['POST'])
def select_channels_endpoint(offer_id: int):
    try:
        user_id = auth_service.get_user_db_id()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Получаем детали оффера
        offer = get_offer_details(offer_id)
        if not offer:
            return jsonify({'error': 'Not Found', 'message': 'Оффер не найден'}), 404
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Bad Request', 'message': 'Отсутствует тело запроса'}), 400
        
        channel_ids = data.get('channel_ids', [])
        expected_duration = data.get('expected_duration', 7)
        
        # Валидация
        if not channel_ids or len(channel_ids) > 20:
            return jsonify({'error': 'Bad Request', 'message': 'Укажите от 1 до 20 каналов'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        created_proposals = []
        
        try:
            conn.execute('BEGIN')
            
            for channel_id in channel_ids:
                # Проверяем канал
                cursor.execute("""
                    SELECT id, title, owner_id 
                    FROM channels 
                    WHERE id = ? AND is_active = 1 AND is_verified = 1
                """, (channel_id,))
                
                channel = cursor.fetchone()
                if not channel:
                    continue
                
                # Проверяем дубликат
                cursor.execute("""
                    SELECT id FROM offer_proposals 
                    WHERE offer_id = ? AND channel_id = ?
                """, (offer_id, channel_id))
                
                if cursor.fetchone():
                    continue
                
                # Создаем предложение
                cursor.execute("""
                    INSERT INTO offer_proposals (
                        offer_id, channel_id, status, created_at, 
                        expires_at, notified_at
                    ) VALUES (?, ?, 'sent', CURRENT_TIMESTAMP, 
                             datetime('now', '+7 days'), CURRENT_TIMESTAMP)
                """, (offer_id, channel_id))
                
                created_proposals.append({
                    'proposal_id': cursor.lastrowid,
                    'channel_id': channel_id,
                    'channel_title': channel['title'],
                    'channel_owner_id': channel['owner_id']
                })
            
            # Обновляем статус оффера
            cursor.execute("""
                UPDATE offers 
                SET status = 'active',
                    selected_channels_count = ?,
                    expected_placement_duration = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (len(created_proposals), expected_duration, offer_id))
            
            conn.commit()
            
            # Отправляем уведомления
            notification_results = []
            for proposal in created_proposals:
                try:
                    notification_service = current_app.telegram_notifications
                    success = notification_service.send_new_proposal_notification(proposal['proposal_id'])
                    notification_results.append({
                        'proposal_id': proposal['proposal_id'],
                        'notification_sent': success
                    })
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
                    notification_results.append({
                        'proposal_id': proposal['proposal_id'],
                        'notification_sent': False
                    })
            
            successful_notifications = sum(1 for r in notification_results if r['notification_sent'])
            
            return jsonify({
                'success': True,
                'message': f'Предложения отправлены в {len(created_proposals)} каналов',
                'created_proposals': len(created_proposals),
                'notifications_sent': successful_notifications
            }), 200
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка создания предложений: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500
        

@offers_management_bp.route('/<int:offer_id>/mark-as-advertising', methods=['POST'])
def mark_as_advertising_endpoint(offer_id: int):
    """
    Маркировка рекламы
    
    POST /api/offers/{offer_id}/mark-as-advertising
    
    Request Body:
    {
        "marked": true
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = auth_service.get_user_db_id()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность оффера
        if not validate_offer_ownership(offer_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Оффер не принадлежит пользователю'
            }), 403
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Отсутствует тело запроса'
            }), 400
        
        is_marked = data.get('marked', True)
        
        # Обновляем маркировку
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE offers 
            SET is_marked = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if is_marked else 0, offer_id))
        
        conn.commit()
        conn.close()
        
        if cursor.rowcount == 0:
            return jsonify({
                'error': 'Not Found',
                'message': 'Оффер не найден'
            }), 404
        
        # Формируем ответ
        response = {
            'success': True,
            'offer_id': offer_id,
            'is_marked': is_marked,
            'message': 'Маркировка рекламы ' + ('установлена' if is_marked else 'снята')
        }
        
        logger.info(f"Маркировка рекламы для оффера {offer_id}: {is_marked}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка маркировки рекламы: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@offers_management_bp.route('/<int:offer_id>/statistics', methods=['GET'])
def get_offer_statistics_endpoint(offer_id: int):
    """
    Получение статистики по офферу
    
    GET /api/offers/{offer_id}/statistics
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = auth_service.get_user_db_id()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность оффера
        if not validate_offer_ownership(offer_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Оффер не принадлежит пользователю'
            }), 403
        
        # Получаем статистику
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # Получаем общую статистику
        cursor.execute("""
            SELECT 
                o.id, o.title, o.status, o.budget_total, o.created_at,
                o.is_marked, o.selected_channels_count,
                os.total_proposals, os.accepted_count, os.rejected_count,
                os.expired_count, os.cancelled_count, os.completed_count,
                os.failed_count, os.total_views, os.total_spent
            FROM offers o
            LEFT JOIN offer_statistics os ON o.id = os.offer_id
            WHERE o.id = ?
        """, (offer_id,))
        
        offer_stats = cursor.fetchone()
        
        if not offer_stats:
            conn.close()
            return jsonify({
                'error': 'Not Found',
                'message': 'Оффер не найден'
            }), 404
        
        # Получаем детализированную статистику по предложениям
        cursor.execute("""
            SELECT 
                op.id, op.status, op.created_at, op.responded_at,
                op.rejection_reason, op.expires_at,
                c.title as channel_title, c.username as channel_username,
                c.subscriber_count, c.category,
                opl.post_url, opl.placement_start, opl.placement_end,
                opl.final_views_count, opl.status as placement_status
            FROM offer_proposals op
            LEFT JOIN channels c ON op.channel_id = c.id
            LEFT JOIN offer_placements opl ON op.id = opl.proposal_id
            WHERE op.offer_id = ?
            ORDER BY op.created_at DESC
        """, (offer_id,))
        
        proposals = cursor.fetchall()
        conn.close()
        
        # Формируем детализированную статистику
        proposals_list = []
        for proposal in proposals:
            proposal_data = dict(proposal)
            proposals_list.append(proposal_data)
        
        # Рассчитываем дополнительные метрики
        total_proposals = offer_stats['total_proposals'] or 0
        accepted_count = offer_stats['accepted_count'] or 0
        rejected_count = offer_stats['rejected_count'] or 0
        
        acceptance_rate = (accepted_count / total_proposals * 100) if total_proposals > 0 else 0
        rejection_rate = (rejected_count / total_proposals * 100) if total_proposals > 0 else 0
        
        # Формируем ответ
        response = {
            'success': True,
            'offer_id': offer_id,
            'offer_title': offer_stats['title'],
            'offer_status': offer_stats['status'],
            'offer_budget': offer_stats['budget'],
            'is_marked': bool(offer_stats['is_marked']),
            'created_at': offer_stats['created_at'],
            'summary': {
                'total_proposals': total_proposals,
                'accepted_count': accepted_count,
                'rejected_count': rejected_count,
                'expired_count': offer_stats['expired_count'] or 0,
                'cancelled_count': offer_stats['cancelled_count'] or 0,
                'completed_count': offer_stats['completed_count'] or 0,
                'failed_count': offer_stats['failed_count'] or 0,
                'total_views': offer_stats['total_views'] or 0,
                'total_spent': offer_stats['total_spent'] or 0,
                'acceptance_rate': round(acceptance_rate, 2),
                'rejection_rate': round(rejection_rate, 2)
            },
            'proposals': proposals_list
        }
        
        logger.info(f"Получена статистика для оффера {offer_id}: {total_proposals} предложений")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@offers_management_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Ресурс не найден'
    }), 404

@offers_management_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Внутренняя ошибка сервера'
    }), 500