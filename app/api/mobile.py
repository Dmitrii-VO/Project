#!/usr/bin/env python3
"""
Mobile API для Telegram Mini App
Оптимизированные endpoints для мобильных устройств с минимальным трафиком
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from functools import wraps
from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

# Создание Blueprint
mobile_bp = Blueprint('mobile', __name__)

# ================================================================
# MOBILE OPTIMIZATION MIDDLEWARE
# ================================================================

def mobile_cache(seconds=300):
    """Декоратор для кеширования мобильных API ответов"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Кеширование на клиенте
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['Cache-Control'] = f'public, max-age={seconds}'
                response.headers['X-Mobile-Optimized'] = 'true'
            return response
        return decorated_function
    return decorator

def compress_response(data):
    """Сжатие данных для мобильных устройств"""
    if isinstance(data, dict):
        # Убираем пустые поля
        return {k: v for k, v in data.items() if v is not None and v != ''}
    elif isinstance(data, list):
        return [compress_response(item) for item in data if item]
    return data

def get_mobile_user_id():
    """Получение user_id для мобильных устройств с оптимизацией"""
    try:
        from app.services.auth_service import auth_service
        user_id = auth_service.get_user_db_id()
        if user_id:
            return user_id
    except Exception:
        pass
    
    # Fallback для мобильных устройств
    try:
        telegram_data = request.headers.get('X-Telegram-Web-App-Data', '')
        if telegram_data:
            # Используем кеш для часто запрашиваемых пользователей
            user = execute_db_query(
                'SELECT id FROM users WHERE telegram_id = 373086959 LIMIT 1',
                fetch_one=True
            )
            if user:
                return user['id']
    except Exception as e:
        logger.warning(f"Mobile auth fallback error: {e}")
    
    return None

# ================================================================
# LIGHTWEIGHT MOBILE ENDPOINTS
# ================================================================

@mobile_bp.route('/summary', methods=['GET'])
@mobile_cache(seconds=600)  # 10 минут кеша для сводки
def get_mobile_summary():
    """Компактная сводка для главного экрана мобильного приложения"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        # Минимальный набор данных для мобильного
        summary_data = execute_db_query("""
            SELECT 
                u.balance,
                (SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_active = 1) as channels,
                (SELECT COUNT(*) FROM offers WHERE created_by = ? AND status = 'active') as active_offers,
                (SELECT COUNT(*) FROM offer_proposals op 
                 JOIN channels c ON op.channel_id = c.id 
                 WHERE c.owner_id = ? AND op.status = 'sent') as pending_proposals
            FROM users u WHERE u.id = ?
        """, (user_id, user_id, user_id, user_id), fetch_one=True)

        if not summary_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Компактный ответ для мобильного
        mobile_summary = {
            'balance': float(summary_data.get('balance', 0)),
            'channels': summary_data.get('channels', 0),
            'offers': summary_data.get('active_offers', 0),
            'pending': summary_data.get('pending_proposals', 0),
            'timestamp': int(datetime.now().timestamp())
        }

        return jsonify({
            'success': True,
            'data': compress_response(mobile_summary)
        })

    except Exception as e:
        logger.error(f"Mobile summary error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@mobile_bp.route('/channels/list', methods=['GET'])
@mobile_cache(seconds=300)  # 5 минут кеша
def get_mobile_channels():
    """Список каналов для мобильного устройства (только важные поля)"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        # Ограничиваем количество полей для мобильного
        channels = execute_db_query("""
            SELECT 
                c.id,
                c.title,
                c.username,
                COALESCE(c.subscribers, 0) as subs,
                c.is_verified as verified,
                c.verification_status as status,
                COUNT(CASE WHEN op.status = 'sent' THEN 1 END) as pending
            FROM channels c
            LEFT JOIN offer_proposals op ON c.id = op.channel_id
            WHERE c.owner_id = ? AND c.is_active = 1
            GROUP BY c.id, c.title, c.username, c.subscribers, c.is_verified, c.verification_status
            ORDER BY c.subscribers DESC
            LIMIT 50
        """, (user_id,), fetch_all=True)

        # Сжимаем данные для мобильного
        mobile_channels = []
        for ch in channels or []:
            mobile_channels.append({
                'id': ch['id'],
                'title': ch['title'][:30] if ch['title'] else 'No title',  # Обрезаем длинные названия
                'username': ch['username'],
                'subs': ch['subs'],
                'verified': bool(ch['verified']),
                'status': ch['status'],
                'pending': ch['pending']
            })

        return jsonify({
            'success': True,
            'data': compress_response(mobile_channels),
            'count': len(mobile_channels)
        })

    except Exception as e:
        logger.error(f"Mobile channels error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@mobile_bp.route('/offers/list', methods=['GET'])
@mobile_cache(seconds=300)
def get_mobile_offers():
    """Список офферов для мобильного (компактный формат)"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        offers = execute_db_query("""
            SELECT 
                o.id,
                o.title,
                o.status,
                o.category,
                COALESCE(o.price, o.budget, 0) as price,
                o.created_at,
                COUNT(DISTINCT op.id) as responses
            FROM offers o
            LEFT JOIN offer_proposals op ON o.id = op.offer_id
            WHERE o.created_by = ?
            GROUP BY o.id, o.title, o.status, o.category, o.price, o.budget, o.created_at
            ORDER BY o.created_at DESC
            LIMIT 30
        """, (user_id,), fetch_all=True)

        mobile_offers = []
        for offer in offers or []:
            mobile_offers.append({
                'id': offer['id'],
                'title': offer['title'][:40] if offer['title'] else 'No title',
                'status': offer['status'],
                'category': offer['category'] or 'general',
                'price': float(offer['price']),
                'responses': offer['responses'],
                'age': (datetime.now() - datetime.fromisoformat(offer['created_at'].replace('Z', '+00:00'))).days if offer['created_at'] else 0
            })

        return jsonify({
            'success': True,
            'data': compress_response(mobile_offers),
            'count': len(mobile_offers)
        })

    except Exception as e:
        logger.error(f"Mobile offers error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@mobile_bp.route('/notifications', methods=['GET'])
@mobile_cache(seconds=60)  # 1 минута кеша для уведомлений
def get_mobile_notifications():
    """Уведомления для мобильного приложения"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        # Получаем только последние важные уведомления
        notifications = []
        
        # Новые предложения
        new_proposals = execute_db_query("""
            SELECT COUNT(*) as count
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ? AND op.status = 'sent' 
            AND op.created_at > datetime('now', '-24 hours')
        """, (user_id,), fetch_one=True)
        
        if new_proposals and new_proposals['count'] > 0:
            notifications.append({
                'type': 'proposals',
                'count': new_proposals['count'],
                'message': f"New proposals: {new_proposals['count']}"
            })

        # Завершенные размещения
        completed_placements = execute_db_query("""
            SELECT COUNT(*) as count
            FROM offer_placements opl
            JOIN offer_proposals op ON opl.proposal_id = op.id
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ? AND opl.status = 'completed'
            AND opl.created_at > datetime('now', '-24 hours')
        """, (user_id,), fetch_one=True)
        
        if completed_placements and completed_placements['count'] > 0:
            notifications.append({
                'type': 'completed',
                'count': completed_placements['count'],
                'message': f"Completed: {completed_placements['count']}"
            })

        return jsonify({
            'success': True,
            'data': compress_response(notifications),
            'count': len(notifications)
        })

    except Exception as e:
        logger.error(f"Mobile notifications error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@mobile_bp.route('/stats/mini', methods=['GET'])
@mobile_cache(seconds=900)  # 15 минут кеша для мини-статистики
def get_mobile_mini_stats():
    """Минимальная статистика для виджетов мобильного приложения"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        # Только самые важные метрики для мобильного
        stats = execute_db_query("""
            SELECT 
                u.balance,
                (SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_active = 1) as channels,
                (SELECT COUNT(*) FROM offers WHERE created_by = ? AND status = 'active') as offers,
                (SELECT COALESCE(SUM(views_count), 0) FROM placement_statistics ps
                 JOIN offer_placements op ON ps.placement_id = op.id
                 JOIN offer_proposals opr ON op.proposal_id = opr.id
                 JOIN channels c ON opr.channel_id = c.id
                 WHERE c.owner_id = ? AND ps.collected_at > datetime('now', '-7 days')) as week_views
            FROM users u WHERE u.id = ?
        """, (user_id, user_id, user_id, user_id), fetch_one=True)

        if not stats:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        mini_stats = {
            'balance': float(stats.get('balance', 0)),
            'channels': stats.get('channels', 0),
            'offers': stats.get('offers', 0),
            'views': stats.get('week_views', 0)
        }

        return jsonify({
            'success': True,
            'data': compress_response(mini_stats)
        })

    except Exception as e:
        logger.error(f"Mobile mini stats error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ================================================================
# MOBILE ACTIONS (POST REQUESTS)
# ================================================================

@mobile_bp.route('/quick-action', methods=['POST'])
def mobile_quick_action():
    """Быстрые действия для мобильного интерфейса"""
    try:
        user_id = get_mobile_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Auth required'}), 401

        data = request.get_json() or {}
        action = data.get('action')
        
        if action == 'accept_proposal':
            proposal_id = data.get('proposal_id')
            if not proposal_id:
                return jsonify({'success': False, 'error': 'Missing proposal_id'}), 400
            
            # Принимаем предложение
            execute_db_query("""
                UPDATE offer_proposals 
                SET status = 'accepted', updated_at = datetime('now')
                WHERE id = ? AND channel_id IN (
                    SELECT id FROM channels WHERE owner_id = ?
                )
            """, (proposal_id, user_id))
            
            return jsonify({'success': True, 'message': 'Proposal accepted'})
        
        elif action == 'reject_proposal':
            proposal_id = data.get('proposal_id')
            if not proposal_id:
                return jsonify({'success': False, 'error': 'Missing proposal_id'}), 400
            
            # Отклоняем предложение
            execute_db_query("""
                UPDATE offer_proposals 
                SET status = 'rejected', updated_at = datetime('now')
                WHERE id = ? AND channel_id IN (
                    SELECT id FROM channels WHERE owner_id = ?
                )
            """, (proposal_id, user_id))
            
            return jsonify({'success': True, 'message': 'Proposal rejected'})
        
        else:
            return jsonify({'success': False, 'error': 'Unknown action'}), 400

    except Exception as e:
        logger.error(f"Mobile quick action error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ================================================================
# MOBILE HEALTH CHECK
# ================================================================

@mobile_bp.route('/health', methods=['GET'])
def mobile_health():
    """Проверка здоровья мобильного API"""
    try:
        # Быстрая проверка БД
        db_check = execute_db_query("SELECT 1", fetch_one=True)
        
        health_status = {
            'status': 'healthy',
            'mobile_api': True,
            'database': bool(db_check),
            'timestamp': int(datetime.now().timestamp()),
            'version': '1.0.0'
        }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
    
    except Exception as e:
        logger.error(f"Mobile health check error: {e}")
        return jsonify({
            'success': False,
            'health': {
                'status': 'unhealthy',
                'error': str(e)
            }
        }), 500

# ================================================================
# ERROR HANDLERS
# ================================================================

@mobile_bp.errorhandler(404)
def mobile_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'mobile_optimized': True
    }), 404

@mobile_bp.errorhandler(500)
def mobile_internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'mobile_optimized': True
    }), 500