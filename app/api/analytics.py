#!/usr/bin/env python3
"""
API для аналитики и статистики
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

# Создание Blueprint
analytics_bp = Blueprint('analytics', __name__)

# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================

def get_current_user_id():
    """Получение telegram_id текущего пользователя"""
    try:
        # Получаем данные из Telegram Web App
        telegram_web_app_data = request.headers.get('X-Telegram-Web-App-Data', '')
        
        if telegram_web_app_data:
            # Простой парсинг telegram_id из строки
            for part in telegram_web_app_data.split('&'):
                if part.startswith('user='):
                    import json
                    import urllib.parse
                    user_data = json.loads(urllib.parse.unquote(part[5:]))
                    return user_data.get('id')
        
        # Если не удалось получить из заголовков, пробуем из параметров
        if hasattr(request, 'args') and 'telegram_id' in request.args:
            return int(request.args['telegram_id'])
            
        return None
        
    except Exception as e:
        logger.error(f"Ошибка получения telegram_id: {e}")
        return None

def get_user_by_telegram_id(telegram_id: int):
    """Получение пользователя по telegram_id"""
    return execute_db_query(
        'SELECT * FROM users WHERE telegram_id = ?',
        (telegram_id,),
        fetch_one=True
    )

def get_user_metrics(user_id: int) -> dict:
    """Получение основных метрик пользователя"""
    try:
        # Статистика каналов
        channels_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_channels,
                COALESCE(SUM(subscriber_count), 0) as total_subscribers,
                COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_channels
            FROM channels 
            WHERE owner_id = ? AND is_active = 1
        """, (user_id,), fetch_one=True)
        
        # Статистика офферов  
        offers_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_offers,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_offers,
                COALESCE(SUM(price), 0) as total_budget
            FROM offers 
            WHERE created_by = ?
        """, (user_id,), fetch_one=True)
        
        # Статистика предложений (как владелец канала)
        proposals_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_proposals,
                COUNT(CASE WHEN op.status = 'accepted' THEN 1 END) as accepted,
                COUNT(CASE WHEN op.status = 'rejected' THEN 1 END) as rejected
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE c.owner_id = ?
        """, (user_id,), fetch_one=True)
        
        # Базовые расчеты
        total_views = 0  # TODO: добавить реальные данные из placement_statistics
        total_clicks = 0  # TODO: добавить реальные данные из ereit_statistics
        ctr = (total_clicks / max(total_views, 1)) * 100 if total_views > 0 else 0
        total_revenue = 0  # TODO: добавить реальные данные из payments
        
        return {
            'total_views': total_views,
            'click_rate': round(ctr, 2),
            'total_revenue': total_revenue,
            'conversion_rate': 0,  # TODO: рассчитать реальную конверсию
            'channels_count': channels_stats['total_channels'] or 0,
            'subscribers_count': channels_stats['total_subscribers'] or 0,
            'offers_count': offers_stats['total_offers'] or 0,
            'proposals_count': proposals_stats['total_proposals'] or 0,
            'verified_channels': channels_stats['verified_channels'] or 0,
            'active_offers': offers_stats['active_offers'] or 0,
            'acceptance_rate': round((proposals_stats['accepted'] / max(proposals_stats['total_proposals'], 1)) * 100, 2) if proposals_stats['total_proposals'] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения метрик: {e}")
        return {
            'total_views': 0,
            'click_rate': 0,
            'total_revenue': 0,
            'conversion_rate': 0,
            'channels_count': 0,
            'subscribers_count': 0,
            'offers_count': 0,
            'proposals_count': 0,
            'verified_channels': 0,
            'active_offers': 0,
            'acceptance_rate': 0
        }

def get_chart_data(user_id: int) -> dict:
    """Данные для графиков"""
    try:
        # TODO: Добавить реальные данные из БД
        # Пока возвращаем тестовые данные для демонстрации
        
        return {
            'views_by_day': {
                'labels': ['1 дек', '2 дек', '3 дек', '4 дек', '5 дек', '6 дек', '7 дек'],
                'values': [120, 150, 180, 140, 200, 250, 190]
            },
            'proposals_stats': {
                'accepted': 15,
                'rejected': 8,
                'pending': 12
            },
            'spending_by_day': {
                'labels': ['1', '2', '3', '4', '5', '6', '7'],
                'values': [1500, 2200, 1800, 2400, 2100, 2800, 2300]
            },
            'efficiency_stats': {
                'cpm': 75,
                'ctr': 65,
                'conversion': 45,
                'roi': 85,
                'reach': 70
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения данных графиков: {e}")
        return {}

# ================================================================
# API ENDPOINTS
# ================================================================

@analytics_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """Основной endpoint для аналитики дашборда"""
    try:
        # Получаем telegram_id
        telegram_id = get_current_user_id()
        if not telegram_id:
            return jsonify({
                'success': False, 
                'error': 'Требуется авторизация'
            }), 401
        
        # Получаем пользователя из БД
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404
        
        user_id = user['id']
        
        # Собираем все данные
        metrics = get_user_metrics(user_id)
        charts = get_chart_data(user_id)
        
        # Формируем ответ
        dashboard_data = {
            'success': True,
            'data': {
                'timestamp': datetime.now().isoformat(),
                'user_id': telegram_id,
                **metrics,  # Разворачиваем метрики в корень data
                **charts   # Добавляем данные графиков
            }
        }
        
        logger.info(f"Аналитика загружена для пользователя {telegram_id}")
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Ошибка получения аналитики: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500

@analytics_bp.route('/status', methods=['GET'])
def get_analytics_status():
    """Проверка статуса системы аналитики"""
    try:
        telegram_id = get_current_user_id()
        
        # Проверка БД
        db_status = 'healthy'
        try:
            execute_db_query("SELECT 1", fetch_one=True)
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        status = {
            'analytics_enabled': True,
            'database_connected': db_status == 'healthy',
            'user_authenticated': bool(telegram_id),
            'telegram_id': telegram_id,
            'version': '1.0.0'
        }

        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Analytics status check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': {
                'analytics_enabled': False,
                'database_connected': False,
                'user_authenticated': False
            }
        }), 500

@analytics_bp.route('/generate-test-data', methods=['POST'])
def generate_test_data():
    """Генерация тестовых данных для аналитики (только для разработки)"""
    try:
        if not AppConfig.DEBUG:
            return jsonify({'error': 'Доступно только в режиме разработки'}), 403
            
        telegram_id = get_current_user_id()
        if not telegram_id:
            return jsonify({'error': 'Требуется авторизация'}), 401
            
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
            
        user_id = user['id']
        
        # Добавляем тестовые данные
        try:
            # Тестовые размещения (если таблица существует)
            execute_db_query("""
                INSERT OR IGNORE INTO placement_statistics 
                (placement_id, views_count, clicks_count, collected_at)
                VALUES (1, 1247, 89, datetime('now'))
            """)
            
            logger.info(f"Тестовые данные созданы для пользователя {telegram_id}")
        except Exception as e:
            logger.warning(f"Не удалось создать тестовые данные: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Тестовые данные созданы'
        })
        
    except Exception as e:
        logger.error(f"Ошибка создания тестовых данных: {e}")
        return jsonify({'error': str(e)}), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@analytics_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint не найден'
    }), 404

@analytics_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Внутренняя ошибка сервера'
    }), 500
