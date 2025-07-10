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
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
offers_management_bp = Blueprint('offers_management', __name__, url_prefix='/api/offers')

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

def validate_offer_ownership(offer_id: int, user_id: int) -> bool:
    """Проверка принадлежности оффера пользователю"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_by FROM offers 
            WHERE id = ? AND created_by = ?
        """, (offer_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
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
                id, title, description, budget, category, subcategory,
                target_audience, placement_requirements, min_subscriber_count,
                max_budget_per_post, placement_duration, status, is_marked,
                selected_channels_count, expected_placement_duration,
                created_by, created_at, expires_at
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
    """Получение рекомендованных каналов для оффера"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Получаем детали оффера
        offer = get_offer_details(offer_id)
        if not offer:
            return []
        
        # Базовый запрос для получения каналов
        query = """
            SELECT 
                c.id, c.title, c.username, c.description,
                c.subscriber_count, c.category, c.language,
                c.is_verified, c.telegram_channel_link,
                u.username as owner_username,
                u.first_name as owner_first_name,
                u.last_name as owner_last_name,
                -- Проверяем, есть ли уже предложение для этого канала
                CASE 
                    WHEN op.id IS NOT NULL THEN op.status
                    ELSE 'not_sent'
                END as proposal_status,
                -- Рассчитываем совместимость
                CASE 
                    WHEN c.category = ? THEN 3
                    WHEN c.category LIKE '%' || ? || '%' THEN 2
                    ELSE 1
                END as category_match_score,
                -- Рассчитываем соответствие по подписчикам
                CASE 
                    WHEN c.subscriber_count >= ? THEN 2
                    WHEN c.subscriber_count >= (? * 0.5) THEN 1
                    ELSE 0
                END as subscriber_match_score
            FROM channels c
            LEFT JOIN users u ON c.owner_id = u.id
            LEFT JOIN offer_proposals op ON (op.channel_id = c.id AND op.offer_id = ?)
            WHERE 
                c.is_active = 1 
                AND c.is_verified = 1
                AND c.status = 'pending'
                AND c.subscriber_count > 0
                -- Исключаем каналы того же владельца
                AND c.owner_id != ?
            ORDER BY 
                (category_match_score + subscriber_match_score) DESC,
                c.subscriber_count DESC
            LIMIT 50
        """
        
        # Параметры для запроса
        category = offer.get('category', 'other')
        min_subscribers = offer.get('min_subscriber_count', 100)
        created_by = offer.get('created_by')
        
        cursor.execute(query, (
            category, category, min_subscribers, min_subscribers, 
            offer_id, created_by
        ))
        
        results = cursor.fetchall()
        conn.close()
        
        # Формируем результат
        channels = []
        for row in results:
            channel_data = dict(row)
            
            # Добавляем дополнительную информацию
            channel_data['compatibility_score'] = (
                channel_data['category_match_score'] + 
                channel_data['subscriber_match_score']
            )
            
            # Формируем ссылку на канал
            if channel_data['username']:
                channel_data['channel_link'] = f"https://t.me/{channel_data['username']}"
            else:
                channel_data['channel_link'] = channel_data['telegram_channel_link']
            
            # Оценка стоимости размещения (примерная)
            estimated_cost = min(
                channel_data['subscriber_count'] * 0.01,  # 1 копейка за подписчика
                offer.get('max_budget_per_post', offer.get('budget', 1000))
            )
            channel_data['estimated_cost'] = round(estimated_cost, 2)
            
            channels.append(channel_data)
        
        return channels
        
    except Exception as e:
        logger.error(f"Ошибка получения рекомендованных каналов: {e}")
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
def get_recommended_channels_endpoint(offer_id: int):
    """
    Получение рекомендованных каналов для оффера
    
    GET /api/offers/{offer_id}/recommended-channels
    
    Query Parameters:
    - limit: количество каналов (по умолчанию 20)
    - category: фильтр по категории
    - min_subscribers: минимальное количество подписчиков
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
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
        
        # Получаем детали оффера
        offer = get_offer_details(offer_id)
        if not offer:
            return jsonify({
                'error': 'Not Found',
                'message': 'Оффер не найден'
            }), 404
        
        # Получаем параметры фильтрации
        limit = request.args.get('limit', 20, type=int)
        category_filter = request.args.get('category')
        min_subscribers_filter = request.args.get('min_subscribers', type=int)
        
        # Получаем рекомендованные каналы
        channels = get_recommended_channels(offer_id)
        
        # Применяем дополнительные фильтры
        if category_filter:
            channels = [c for c in channels if c['category'] == category_filter]
        
        if min_subscribers_filter:
            channels = [c for c in channels if c['subscriber_count'] >= min_subscribers_filter]
        
        # Ограничиваем количество результатов
        channels = channels[:limit]
        
        # Формируем ответ
        response = {
            'success': True,
            'offer_id': offer_id,
            'offer_title': offer['title'],
            'offer_status': offer['status'],
            'total_channels': len(channels),
            'channels': channels,
            'filters': {
                'category': category_filter,
                'min_subscribers': min_subscribers_filter,
                'limit': limit
            }
        }
        
        logger.info(f"Получены рекомендованные каналы для оффера {offer_id}: {len(channels)} каналов")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения рекомендованных каналов: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@offers_management_bp.route('/<int:offer_id>/select-channels', methods=['POST'])
def select_channels_endpoint(offer_id: int):
    """
    Выбор каналов и запуск кампании
    
    POST /api/offers/{offer_id}/select-channels
    
    Request Body:
    {
        "channel_ids": [1, 2, 3],
        "message": "Текст сообщения для владельцев каналов",
        "expected_duration": 7
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
        
        # Проверяем принадлежность оффера
        if not validate_offer_ownership(offer_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Оффер не принадлежит пользователю'
            }), 403
        
        # Получаем детали оффера
        offer = get_offer_details(offer_id)
        if not offer:
            return jsonify({
                'error': 'Not Found',
                'message': 'Оффер не найден'
            }), 404
        
        # Проверяем статус оффера
        if offer['status'] not in ['draft', 'matching']:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя выбрать каналы для оффера со статусом {offer["status"]}'
            }), 400
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Отсутствует тело запроса'
            }), 400
        
        channel_ids = data.get('channel_ids', [])
        custom_message = data.get('message', '')
        expected_duration = data.get('expected_duration', 7)
        
        # Валидация данных
        if not channel_ids or not isinstance(channel_ids, list):
            return jsonify({
                'error': 'Bad Request',
                'message': 'Необходимо указать массив channel_ids'
            }), 400
        
        if len(channel_ids) > 20:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Максимум 20 каналов за раз'
            }), 400
        
        # Создаем предложения для выбранных каналов
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        created_proposals = []
        
        try:
            # Начинаем транзакцию
            conn.execute('BEGIN')
            
            for channel_id in channel_ids:
                # Проверяем, что канал существует и активен
                cursor.execute("""
                    SELECT id, title, owner_id 
                    FROM channels 
                    WHERE id = ? AND is_active = 1 AND is_verified = 1
                """, (channel_id,))
                
                channel = cursor.fetchone()
                if not channel:
                    continue
                
                # Проверяем, что предложение еще не создано
                cursor.execute("""
                    SELECT id FROM offer_proposals 
                    WHERE offer_id = ? AND channel_id = ?
                """, (offer_id, channel_id))
                
                existing_proposal = cursor.fetchone()
                if existing_proposal:
                    continue
                
                # Создаем предложение
                cursor.execute("""
                    INSERT INTO offer_proposals (
                        offer_id, channel_id, status, created_at, 
                        expires_at, notified_at
                    ) VALUES (?, ?, 'sent', CURRENT_TIMESTAMP, 
                             datetime('now', '+7 days'), CURRENT_TIMESTAMP)
                """, (offer_id, channel_id))
                
                proposal_id = cursor.lastrowid
                created_proposals.append({
                    'proposal_id': proposal_id,
                    'channel_id': channel_id,
                    'channel_title': channel['title'],
                    'channel_owner_id': channel['owner_id']
                })
            
            # Обновляем статус оффера
            cursor.execute("""
                UPDATE offers 
                SET status = 'started', 
                    selected_channels_count = ?,
                    expected_placement_duration = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (len(created_proposals), expected_duration, offer_id))
            
            # Подтверждаем транзакцию
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка создания предложений: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка создания предложений'
            }), 500
        
        finally:
            conn.close()
        

        # Отправляем уведомления владельцам каналов
        # TODO: Реализовать отправку уведомлений через Telegram Bot
        
        # Формируем ответ
        response = {
            'success': True,
            'offer_id': offer_id,
            'created_proposals': len(created_proposals),
            'proposals': created_proposals,
            'message': f'Создано {len(created_proposals)} предложений для каналов'
        }
        
        logger.info(f"Создано {len(created_proposals)} предложений для оффера {offer_id}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка выбора каналов: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

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
        user_id = get_user_id_from_request()
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
        user_id = get_user_id_from_request()
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
                o.id, o.title, o.status, o.budget, o.created_at,
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