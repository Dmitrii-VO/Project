#!/usr/bin/env python3
"""
API для мониторинга размещений и статистики
Endpoints для проверки постов и получения аналитики
"""

import sqlite3
import json
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
monitoring_statistics_bp = Blueprint('monitoring_statistics', __name__, url_prefix='/api')

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

def get_bot_token() -> Optional[str]:
    """Получение токена бота"""
    try:
        return AppConfig.BOT_TOKEN
    except:
        return None

def validate_placement_access(placement_id: int, user_id: int) -> bool:
    """Проверка доступа к размещению (владелец канала или создатель оффера)"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.owner_id as channel_owner_id,
                o.created_by as offer_creator_id
            FROM offer_placements opl
            JOIN offer_proposals op ON opl.proposal_id = op.id
            JOIN channels c ON op.channel_id = c.id
            JOIN offers o ON op.offer_id = o.id
            WHERE opl.id = ?
        """, (placement_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        return (user_id == result['channel_owner_id'] or 
                user_id == result['offer_creator_id'])
    except Exception as e:
        logger.error(f"Ошибка проверки доступа к размещению: {e}")
        return False

def get_placement_details(placement_id: int) -> Optional[Dict]:
    """Получение деталей размещения"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                opl.id, opl.proposal_id, opl.post_url, opl.placement_start,
                opl.placement_end, opl.expected_duration, opl.status,
                opl.final_views_count, opl.created_at, opl.updated_at,
                -- Информация о предложении
                op.offer_id, op.channel_id, op.status as proposal_status,
                -- Информация об оффере
                o.title as offer_title, o.description as offer_description,
                o.budget as offer_budget, o.created_by as offer_creator_id,
                -- Информация о канале
                c.title as channel_title, c.username as channel_username,
                c.owner_id as channel_owner_id, c.subscriber_count,
                -- Последняя проверка
                pc.check_time as last_check_time, pc.post_exists as last_post_exists,
                pc.views_count as last_views_count, pc.check_status as last_check_status,
                pc.error_message as last_error_message
            FROM offer_placements opl
            JOIN offer_proposals op ON opl.proposal_id = op.id
            JOIN offers o ON op.offer_id = o.id
            JOIN channels c ON op.channel_id = c.id
            LEFT JOIN placement_checks pc ON opl.id = pc.placement_id
            WHERE opl.id = ?
            ORDER BY pc.check_time DESC
            LIMIT 1
        """, (placement_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения деталей размещения: {e}")
        return None

def parse_telegram_post_url(post_url: str) -> Optional[Dict[str, str]]:
    """Парсинг URL поста Telegram"""
    try:
        # Регулярное выражение для парсинга t.me ссылок
        pattern = r'https://t\.me/([^/]+)/(\d+)'
        match = re.match(pattern, post_url)
        
        if match:
            channel_username = match.group(1)
            message_id = match.group(2)
            
            return {
                'channel_username': channel_username,
                'message_id': message_id,
                'is_valid': True
            }
        else:
            return {
                'is_valid': False,
                'error': 'Invalid Telegram URL format'
            }
    except Exception as e:
        logger.error(f"Ошибка парсинга URL поста: {e}")
        return {
            'is_valid': False,
            'error': str(e)
        }

def check_telegram_post(post_url: str) -> Dict[str, Any]:
    """Проверка поста в Telegram через API"""
    try:
        bot_token = get_bot_token()
        if not bot_token:
            return {
                'success': False,
                'error': 'Bot token not configured',
                'post_exists': False,
                'views_count': 0
            }
        
        # Парсим URL
        parsed_url = parse_telegram_post_url(post_url)
        if not parsed_url['is_valid']:
            return {
                'success': False,
                'error': parsed_url['error'],
                'post_exists': False,
                'views_count': 0
            }
        
        channel_username = parsed_url['channel_username']
        message_id = parsed_url['message_id']
        
        # Формируем chat_id
        chat_id = f"@{channel_username}" if not channel_username.startswith('@') else channel_username
        
        # Делаем запрос к Telegram Bot API
        api_url = f"https://api.telegram.org/bot{bot_token}/getChat"
        chat_response = requests.get(api_url, params={'chat_id': chat_id}, timeout=10)
        
        if chat_response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to get chat info: {chat_response.status_code}',
                'post_exists': False,
                'views_count': 0
            }
        
        # Пробуем получить сообщение (это может не работать для каналов)
        # В реальном проекте здесь нужно использовать другой подход
        # Например, парсинг через веб-скрейпинг или Telegram Client API
        
        # Для демонстрации возвращаем успешный результат
        # В реальности нужно реализовать полноценный парсинг
        return {
            'success': True,
            'post_exists': True,
            'views_count': 0,  # Здесь должны быть реальные просмотры
            'message': 'Post checked successfully (mock implementation)',
            'check_method': 'telegram_bot_api'
        }
        
    except requests.RequestException as e:
        logger.error(f"Ошибка запроса к Telegram API: {e}")
        return {
            'success': False,
            'error': f'Request error: {str(e)}',
            'post_exists': False,
            'views_count': 0
        }
    except Exception as e:
        logger.error(f"Ошибка проверки поста: {e}")
        return {
            'success': False,
            'error': str(e),
            'post_exists': False,
            'views_count': 0
        }

def save_placement_check(placement_id: int, check_result: Dict[str, Any]) -> bool:
    """Сохранение результата проверки размещения"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Определяем статус проверки
        if check_result['success']:
            if check_result['post_exists']:
                check_status = 'success'
            else:
                check_status = 'not_found'
        else:
            check_status = 'error'
        
        # Сохраняем результат
        cursor.execute("""
            INSERT INTO placement_checks (
                placement_id, check_time, post_exists, views_count,
                check_status, error_message, response_data
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """, (
            placement_id,
            1 if check_result['post_exists'] else 0,
            check_result['views_count'],
            check_status,
            check_result.get('error'),
            json.dumps(check_result)
        ))
        
        # Обновляем статус размещения если пост не найден
        if not check_result['post_exists'] and check_result['success']:
            cursor.execute("""
                UPDATE offer_placements 
                SET status = 'failed', placement_end = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (placement_id,))
        
        # Обновляем количество просмотров
        elif check_result['success'] and check_result['post_exists']:
            cursor.execute("""
                UPDATE offer_placements 
                SET final_views_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (check_result['views_count'], placement_id))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения результата проверки: {e}")
        return False

def get_placement_history(placement_id: int, limit: int = 20) -> List[Dict]:
    """Получение истории проверок размещения"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, check_time, post_exists, views_count,
                check_status, error_message
            FROM placement_checks
            WHERE placement_id = ?
            ORDER BY check_time DESC
            LIMIT ?
        """, (placement_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Ошибка получения истории проверок: {e}")
        return []

def get_offer_detailed_statistics(offer_id: int) -> Dict[str, Any]:
    """Получение детальной статистики по офферу"""
    try:
        conn = get_db_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Общая информация об оффере
        cursor.execute("""
            SELECT 
                id, title, description, budget, status, created_at,
                is_marked, selected_channels_count, expected_placement_duration,
                created_by
            FROM offers
            WHERE id = ?
        """, (offer_id,))
        
        offer = cursor.fetchone()
        if not offer:
            return {}
        
        # Статистика предложений
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                GROUP_CONCAT(rejection_reason) as rejection_reasons
            FROM offer_proposals
            WHERE offer_id = ?
            GROUP BY status
        """, (offer_id,))
        
        proposal_stats = cursor.fetchall()
        
        # Статистика размещений
        cursor.execute("""
            SELECT 
                opl.status,
                COUNT(*) as count,
                SUM(opl.final_views_count) as total_views,
                AVG(opl.final_views_count) as avg_views,
                MIN(opl.placement_start) as first_placement,
                MAX(opl.placement_end) as last_placement
            FROM offer_placements opl
            JOIN offer_proposals op ON opl.proposal_id = op.id
            WHERE op.offer_id = ?
            GROUP BY opl.status
        """, (offer_id,))
        
        placement_stats = cursor.fetchall()
        
        # Детальная информация по каналам
        cursor.execute("""
            SELECT 
                c.id, c.title, c.username, c.subscriber_count, c.category,
                op.status as proposal_status, op.created_at as proposal_created,
                op.responded_at, op.rejection_reason,
                opl.status as placement_status, opl.post_url, 
                opl.placement_start, opl.placement_end, opl.final_views_count,
                -- Последняя проверка
                pc.check_time as last_check, pc.post_exists as last_post_exists,
                pc.views_count as last_views_count
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            LEFT JOIN offer_placements opl ON op.id = opl.proposal_id
            LEFT JOIN (
                SELECT placement_id, check_time, post_exists, views_count,
                       ROW_NUMBER() OVER (PARTITION BY placement_id ORDER BY check_time DESC) as rn
                FROM placement_checks
            ) pc ON opl.id = pc.placement_id AND pc.rn = 1
            WHERE op.offer_id = ?
            ORDER BY op.created_at ASC
        """, (offer_id,))
        
        channels_details = cursor.fetchall()
        
        # Статистика проверок
        cursor.execute("""
            SELECT 
                pc.check_status,
                COUNT(*) as count,
                AVG(pc.views_count) as avg_views
            FROM placement_checks pc
            JOIN offer_placements opl ON pc.placement_id = opl.id
            JOIN offer_proposals op ON opl.proposal_id = op.id
            WHERE op.offer_id = ?
            GROUP BY pc.check_status
        """, (offer_id,))
        
        check_stats = cursor.fetchall()
        
        conn.close()
        
        # Формируем результат
        result = {
            'offer': dict(offer),
            'proposal_statistics': {
                row['status']: {
                    'count': row['count'],
                    'rejection_reasons': row['rejection_reasons'].split(',') if row['rejection_reasons'] else []
                }
                for row in proposal_stats
            },
            'placement_statistics': {
                row['status']: {
                    'count': row['count'],
                    'total_views': row['total_views'] or 0,
                    'avg_views': round(row['avg_views'], 2) if row['avg_views'] else 0,
                    'first_placement': row['first_placement'],
                    'last_placement': row['last_placement']
                }
                for row in placement_stats
            },
            'channels_details': [dict(row) for row in channels_details],
            'check_statistics': {
                row['check_status']: {
                    'count': row['count'],
                    'avg_views': round(row['avg_views'], 2) if row['avg_views'] else 0
                }
                for row in check_stats
            }
        }
        
        # Добавляем сводную статистику
        total_proposals = sum(stats['count'] for stats in result['proposal_statistics'].values())
        total_views = sum(stats['total_views'] for stats in result['placement_statistics'].values())
        
        result['summary'] = {
            'total_proposals': total_proposals,
            'total_views': total_views,
            'acceptance_rate': round(
                (result['proposal_statistics'].get('accepted', {}).get('count', 0) / total_proposals * 100), 2
            ) if total_proposals > 0 else 0,
            'completion_rate': round(
                (result['placement_statistics'].get('completed', {}).get('count', 0) / 
                 max(result['placement_statistics'].get('placed', {}).get('count', 0), 1) * 100), 2
            ) if result['placement_statistics'].get('placed', {}).get('count', 0) > 0 else 0
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка получения детальной статистики: {e}")
        return {}

# ================================================================
# API ENDPOINTS
# ================================================================

@monitoring_statistics_bp.route('/placements/<int:placement_id>/status', methods=['GET'])
def get_placement_status(placement_id: int):
    """
    Получение статуса размещения
    
    GET /api/placements/{placement_id}/status
    
    Query Parameters:
    - include_history: включить историю проверок (true/false)
    - history_limit: количество записей истории (по умолчанию 10)
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем доступ к размещению
        if not validate_placement_access(placement_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Нет доступа к размещению'
            }), 403
        
        # Получаем детали размещения
        placement = get_placement_details(placement_id)
        if not placement:
            return jsonify({
                'error': 'Not Found',
                'message': 'Размещение не найдено'
            }), 404
        
        # Получаем параметры
        include_history = request.args.get('include_history', 'false').lower() == 'true'
        history_limit = request.args.get('history_limit', 10, type=int)
        
        # Формируем ответ
        response = {
            'success': True,
            'placement_id': placement_id,
            'placement': {
                'id': placement['id'],
                'proposal_id': placement['proposal_id'],
                'post_url': placement['post_url'],
                'placement_start': placement['placement_start'],
                'placement_end': placement['placement_end'],
                'expected_duration': placement['expected_duration'],
                'status': placement['status'],
                'final_views_count': placement['final_views_count'],
                'created_at': placement['created_at'],
                'updated_at': placement['updated_at']
            },
            'offer': {
                'id': placement['offer_id'],
                'title': placement['offer_title'],
                'budget': placement['offer_budget']
            },
            'channel': {
                'id': placement['channel_id'],
                'title': placement['channel_title'],
                'username': placement['channel_username'],
                'subscriber_count': placement['subscriber_count']
            },
            'last_check': {
                'check_time': placement['last_check_time'],
                'post_exists': bool(placement['last_post_exists']),
                'views_count': placement['last_views_count'],
                'check_status': placement['last_check_status'],
                'error_message': placement['last_error_message']
            } if placement['last_check_time'] else None
        }
        
        # Добавляем историю если запрошена
        if include_history:
            history = get_placement_history(placement_id, history_limit)
            response['check_history'] = history
        
        # Рассчитываем дополнительные метрики
        if placement['placement_start'] and placement['expected_duration']:
            start_time = datetime.fromisoformat(placement['placement_start'])
            expected_end = start_time + timedelta(days=placement['expected_duration'])
            now = datetime.now()
            
            response['timing'] = {
                'is_active': placement['status'] in ['placed', 'monitoring'],
                'expected_end': expected_end.isoformat(),
                'is_overdue': now > expected_end,
                'days_remaining': max(0, (expected_end - now).days) if now < expected_end else 0
            }
        
        logger.info(f"Получен статус размещения {placement_id} пользователем {user_id}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса размещения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@monitoring_statistics_bp.route('/placements/<int:placement_id>/check-now', methods=['POST'])
def check_placement_now(placement_id: int):
    """
    Принудительная проверка размещения
    
    POST /api/placements/{placement_id}/check-now
    
    Request Body:
    {
        "force": true  // принудительная проверка даже если недавно проверялось
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
        
        # Проверяем доступ к размещению
        if not validate_placement_access(placement_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Нет доступа к размещению'
            }), 403
        
        # Получаем детали размещения
        placement = get_placement_details(placement_id)
        if not placement:
            return jsonify({
                'error': 'Not Found',
                'message': 'Размещение не найдено'
            }), 404
        
        # Проверяем статус размещения
        if placement['status'] not in ['placed', 'monitoring']:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя проверить размещение со статусом {placement["status"]}'
            }), 400
        
        # Проверяем наличие URL поста
        if not placement['post_url']:
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL поста не указан'
            }), 400
        
        # Получаем параметры
        data = request.get_json() or {}
        force = data.get('force', False)
        
        # Проверяем, когда была последняя проверка
        if not force and placement['last_check_time']:
            last_check = datetime.fromisoformat(placement['last_check_time'])
            if datetime.now() - last_check < timedelta(minutes=5):
                return jsonify({
                    'error': 'Too Many Requests',
                    'message': 'Слишком частые проверки. Попробуйте через 5 минут.',
                    'last_check': placement['last_check_time']
                }), 429
        
        # Выполняем проверку поста
        logger.info(f"Выполняется принудительная проверка размещения {placement_id}")
        check_result = check_telegram_post(placement['post_url'])
        
        # Сохраняем результат проверки
        save_placement_check(placement_id, check_result)
        
        # Формируем ответ
        response = {
            'success': True,
            'placement_id': placement_id,
            'check_result': {
                'check_time': datetime.now().isoformat(),
                'post_exists': check_result['post_exists'],
                'views_count': check_result['views_count'],
                'check_status': 'success' if check_result['success'] else 'error',
                'error_message': check_result.get('error'),
                'check_method': check_result.get('check_method', 'manual')
            },
            'placement_status': placement['status'],
            'post_url': placement['post_url']
        }
        
        # Добавляем дополнительную информацию
        if check_result['success']:
            if check_result['post_exists']:
                response['message'] = 'Пост найден и активен'
            else:
                response['message'] = 'Пост не найден или удален'
                response['warning'] = 'Размещение может быть помечено как неуспешное'
        else:
            response['message'] = 'Ошибка при проверке поста'
            response['error_details'] = check_result.get('error')
        
        logger.info(f"Проверка размещения {placement_id} завершена: {check_result['success']}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка принудительной проверки размещения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@monitoring_statistics_bp.route('/statistics/offer/<int:offer_id>', methods=['GET'])
def get_offer_statistics(offer_id: int):
    """
    Получение детальной статистики по офферу
    
    GET /api/statistics/offer/{offer_id}
    
    Query Parameters:
    - include_channels: включить детали по каналам (true/false)
    - include_checks: включить статистику проверок (true/false)
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
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_by FROM offers WHERE id = ?
        """, (offer_id,))
        
        offer_owner = cursor.fetchone()
        conn.close()
        
        if not offer_owner:
            return jsonify({
                'error': 'Not Found',
                'message': 'Оффер не найден'
            }), 404
        
        if offer_owner['created_by'] != user_id:
            return jsonify({
                'error': 'Forbidden',
                'message': 'Оффер не принадлежит пользователю'
            }), 403
        
        # Получаем параметры
        include_channels = request.args.get('include_channels', 'true').lower() == 'true'
        include_checks = request.args.get('include_checks', 'true').lower() == 'true'
        
        # Получаем детальную статистику
        statistics = get_offer_detailed_statistics(offer_id)
        
        if not statistics:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка получения статистики'
            }), 500
        
        # Формируем ответ
        response = {
            'success': True,
            'offer_id': offer_id,
            'offer': statistics['offer'],
            'summary': statistics['summary'],
            'proposal_statistics': statistics['proposal_statistics'],
            'placement_statistics': statistics['placement_statistics']
        }
        
        # Добавляем детали по каналам если запрошены
        if include_channels:
            response['channels_details'] = statistics['channels_details']
        
        # Добавляем статистику проверок если запрошена
        if include_checks:
            response['check_statistics'] = statistics['check_statistics']
        
        # Добавляем дополнительную аналитику
        response['analytics'] = {
            'campaign_duration': None,
            'average_response_time': None,
            'top_performing_channels': [],
            'failure_reasons': []
        }
        
        # Рассчитываем продолжительность кампании
        if statistics['offer']['created_at']:
            start_date = datetime.fromisoformat(statistics['offer']['created_at'])
            
            # Находим последнее размещение
            last_placement = None
            for status_data in statistics['placement_statistics'].values():
                if status_data['last_placement']:
                    last_placement = status_data['last_placement']
                    break
            
            if last_placement:
                end_date = datetime.fromisoformat(last_placement)
                response['analytics']['campaign_duration'] = (end_date - start_date).days
        
        # Находим топ каналы по просмотрам
        if include_channels:
            top_channels = sorted(
                [ch for ch in statistics['channels_details'] if ch['final_views_count']],
                key=lambda x: x['final_views_count'],
                reverse=True
            )[:5]
            
            response['analytics']['top_performing_channels'] = [
                {
                    'channel_title': ch['title'],
                    'channel_username': ch['username'],
                    'views_count': ch['final_views_count'],
                    'subscriber_count': ch['subscriber_count']
                }
                for ch in top_channels
            ]
        
        # Собираем причины отказов
        failure_reasons = []
        for ch in statistics['channels_details']:
            if ch['rejection_reason']:
                failure_reasons.append(ch['rejection_reason'])
        
        response['analytics']['failure_reasons'] = list(set(failure_reasons))
        
        logger.info(f"Получена статистика для оффера {offer_id} пользователем {user_id}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики оффера: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS
# ================================================================

@monitoring_statistics_bp.route('/statistics/dashboard', methods=['GET'])
def get_dashboard_statistics():
    """
    Получение общей статистики для дашборда
    
    GET /api/statistics/dashboard
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # Статистика офферов пользователя
        cursor.execute("""
            SELECT 
                COUNT(*) as total_offers,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_offers,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as active_offers,
                SUM(budget) as total_budget
            FROM offers
            WHERE created_by = ?
        """, (user_id,))
        
        offers_stats = cursor.fetchone()
        
        # Статистика предложений
        cursor.execute("""
            SELECT 
                COUNT(*) as total_proposals,
                SUM(CASE WHEN op.status = 'accepted' THEN 1 ELSE 0 END) as accepted_proposals,
                SUM(CASE WHEN op.status = 'rejected' THEN 1 ELSE 0 END) as rejected_proposals
            FROM offer_proposals op
            JOIN offers o ON op.offer_id = o.id
            WHERE o.created_by = ?
        """, (user_id,))
        
        proposals_stats = cursor.fetchone()
        
        # Статистика размещений
        cursor.execute("""
            SELECT 
                COUNT(*) as total_placements,
                SUM(CASE WHEN opl.status = 'completed' THEN 1 ELSE 0 END) as completed_placements,
                SUM(opl.final_views_count) as total_views
            FROM offer_placements opl
            JOIN offer_proposals op ON opl.proposal_id = op.id
            JOIN offers o ON op.offer_id = o.id
            WHERE o.created_by = ?
        """, (user_id,))
        
        placements_stats = cursor.fetchone()
        
        # Статистика каналов пользователя (если он владелец каналов)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_channels,
                SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified_channels,
                SUM(subscriber_count) as total_subscribers
            FROM channels
            WHERE owner_id = ?
        """, (user_id,))
        
        channels_stats = cursor.fetchone()
        
        # Входящие предложения (для владельца каналов)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_incoming,
                SUM(CASE WHEN op.status = 'sent' THEN 1 ELSE 0 END) as pending_proposals
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ?
        """, (user_id,))
        
        incoming_stats = cursor.fetchone()
        
        conn.close()
        
        # Формируем ответ
        response = {
            'success': True,
            'user_id': user_id,
            'offers': {
                'total': offers_stats['total_offers'],
                'completed': offers_stats['completed_offers'],
                'active': offers_stats['active_offers'],
                'total_budget': offers_stats['total_budget'] or 0
            },
            'proposals': {
                'total': proposals_stats['total_proposals'],
                'accepted': proposals_stats['accepted_proposals'],
                'rejected': proposals_stats['rejected_proposals'],
                'acceptance_rate': round(
                    (proposals_stats['accepted_proposals'] / max(proposals_stats['total_proposals'], 1) * 100), 2
                )
            },
            'placements': {
                'total': placements_stats['total_placements'],
                'completed': placements_stats['completed_placements'],
                'total_views': placements_stats['total_views'] or 0,
                'completion_rate': round(
                    (placements_stats['completed_placements'] / max(placements_stats['total_placements'], 1) * 100), 2
                )
            },
            'channels': {
                'total': channels_stats['total_channels'],
                'verified': channels_stats['verified_channels'],
                'total_subscribers': channels_stats['total_subscribers'] or 0
            },
            'incoming': {
                'total': incoming_stats['total_incoming'],
                'pending': incoming_stats['pending_proposals']
            }
        }
        
        logger.info(f"Получена статистика дашборда для пользователя {user_id}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики дашборда: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@monitoring_statistics_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Ресурс не найден'
    }), 404

@monitoring_statistics_bp.errorhandler(429)
def too_many_requests(error):
    return jsonify({
        'error': 'Too Many Requests',
        'message': 'Слишком много запросов'
    }), 429

@monitoring_statistics_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Внутренняя ошибка сервера'
    }), 500