# notifications_system.py - Система уведомлений
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional
import os

# Конфигурация
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
DATABASE_PATH = DATABASE_URL.replace('sqlite:///', '')
YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))

# Создаем Blueprint для уведомлений
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

def get_db_connection():
    """Получение подключения к SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к SQLite: {e}")

def safe_execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Безопасное выполнение SQL запросов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        result = None
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows] if rows else []
        
        if not (fetch_one or fetch_all):
            conn.commit()
        
        conn.close()
        return result
    except Exception as e:
        print(f"Ошибка выполнения запроса: {e}")
        return None

def get_current_user_id():
    """Получение ID текущего пользователя"""
    return YOUR_TELEGRAM_ID

def ensure_user_exists(user_id, username=None, first_name=None):
    """Обеспечение существования пользователя в базе"""
    user = safe_execute_query(
        'SELECT id FROM users WHERE telegram_id = ?',
        (user_id,),
        fetch_one=True
    )
    if not user:
        safe_execute_query('''
            INSERT INTO users (telegram_id, username, first_name, is_admin) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, username or f'user_{user_id}', first_name or 'User', False))
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )
    return user['id'] if user else None

class NotificationManager:
    """Менеджер уведомлений"""
    
    @staticmethod
    def create_notification(user_id: int, notification_type: str, title: str, 
                          message: str, data: Optional[Dict] = None, priority: int = 0):
        """Создание уведомления"""
        try:
            safe_execute_query('''
                INSERT INTO notifications (user_id, type, title, message, data, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, notification_type, title, message, 
                  json.dumps(data) if data else None, priority))
            
            # Отправляем push-уведомление если приоритет высокий
            if priority > 0:
                NotificationManager.send_push_notification(user_id, title, message)
                
            return True
        except Exception as e:
            print(f"Ошибка создания уведомления: {e}")
            return False
    
    @staticmethod
    def send_push_notification(user_id: int, title: str, message: str):
        """Отправка push-уведомления через Telegram Bot API"""
        try:
            # Здесь должна быть интеграция с Telegram Bot API
            # Пока просто логируем
            print(f"🔔 Push notification to {user_id}: {title} - {message}")
            return True
        except Exception as e:
            print(f"Ошибка отправки push-уведомления: {e}")
            return False
    
    @staticmethod
    def get_user_notifications(user_id: int, limit: int = 50, unread_only: bool = False):
        """Получение уведомлений пользователя"""
        query = '''
            SELECT * FROM notifications 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if unread_only:
            query += ' AND is_read = 0'
        
        query += ' ORDER BY priority DESC, created_at DESC LIMIT ?'
        params.append(limit)
        
        notifications = safe_execute_query(query, params, fetch_all=True)
        
        # Обогащаем данные
        enriched_notifications = []
        for notif in notifications:
            notif_data = dict(notif)
            notif_data['created_at_formatted'] = format_datetime(notif['created_at'])
            notif_data['data_parsed'] = json.loads(notif['data']) if notif['data'] else {}
            notif_data['time_ago'] = get_time_ago(notif['created_at'])
            notif_data['icon'] = get_notification_icon(notif['type'])
            notif_data['color'] = get_notification_color(notif['type'])
            enriched_notifications.append(notif_data)
        
        return enriched_notifications
    
    @staticmethod
    def mark_as_read(notification_ids: List[int], user_id: int):
        """Отметка уведомлений как прочитанных"""
        if not notification_ids:
            return False
        
        placeholders = ','.join(['?' for _ in notification_ids])
        params = notification_ids + [user_id]
        
        safe_execute_query(f'''
            UPDATE notifications 
            SET is_read = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders}) AND user_id = ?
        ''', params)
        
        return True
    
    @staticmethod
    def mark_all_as_read(user_id: int):
        """Отметка всех уведомлений как прочитанных"""
        safe_execute_query('''
            UPDATE notifications 
            SET is_read = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_read = 0
        ''', (user_id,))
        
        return True
    
    @staticmethod
    def get_unread_count(user_id: int):
        """Получение количества непрочитанных уведомлений"""
        result = safe_execute_query('''
            SELECT COUNT(*) as count FROM notifications 
            WHERE user_id = ? AND is_read = 0
        ''', (user_id,), fetch_one=True)
        
        return result['count'] if result else 0
    
    @staticmethod
    def delete_old_notifications(days: int = 30):
        """Удаление старых уведомлений"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        safe_execute_query('''
            DELETE FROM notifications 
            WHERE created_at < ? AND is_read = 1
        ''', (cutoff_date.isoformat(),))
        
        return True

# =============================================================================
# API ENDPOINTS
# =============================================================================

@notifications_bp.route('', methods=['GET'])
def get_notifications():
    """Получение уведомлений текущего пользователя"""
    try:
        user_id = get_current_user_id()
        user_db_id = ensure_user_exists(user_id, f'user_{user_id}', 'User')
        
        limit = request.args.get('limit', 50, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications = NotificationManager.get_user_notifications(
            user_db_id, limit, unread_only
        )
        
        unread_count = NotificationManager.get_unread_count(user_db_id)
        
        return jsonify({
            'notifications': notifications,
            'total': len(notifications),
            'unread_count': unread_count,
            'has_more': len(notifications) == limit
        })
        
    except Exception as e:
        print(f"Ошибка получения уведомлений: {e}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """Получение количества непрочитанных уведомлений"""
    try:
        user_id = get_current_user_id()
        user_db_id = ensure_user_exists(user_id, f'user_{user_id}', 'User')
        
        count = NotificationManager.get_unread_count(user_db_id)
        
        return jsonify({
            'unread_count': count,
            'has_unread': count > 0
        })
        
    except Exception as e:
        print(f"Ошибка получения количества уведомлений: {e}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/mark-read', methods=['POST'])
def mark_notifications_read():
    """Отметка уведомлений как прочитанных"""
    try:
        user_id = get_current_user_id()
        user_db_id = ensure_user_exists(user_id, f'user_{user_id}', 'User')
        
        data = request.get_json()
        notification_ids = data.get('notification_ids', [])
        mark_all = data.get('mark_all', False)
        
        if mark_all:
            NotificationManager.mark_all_as_read(user_db_id)
            message = 'Все уведомления отмечены как прочитанные'
        elif notification_ids:
            NotificationManager.mark_as_read(notification_ids, user_db_id)
            message = f'Отмечено как прочитанные: {len(notification_ids)} уведомлений'
        else:
            return jsonify({'error': 'Не указаны уведомления для отметки'}), 400
        
        new_unread_count = NotificationManager.get_unread_count(user_db_id)
        
        return jsonify({
            'success': True,
            'message': message,
            'unread_count': new_unread_count
        })
        
    except Exception as e:
        print(f"Ошибка отметки уведомлений: {e}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/create', methods=['POST'])
def create_notification():
    """Создание уведомления (для системных нужд)"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'type', 'title', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Поле {field} обязательно'}), 400
        
        success = NotificationManager.create_notification(
            data['user_id'],
            data['type'],
            data['title'],
            data['message'],
            data.get('data'),
            data.get('priority', 0)
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Уведомление создано'
            })
        else:
            return jsonify({'error': 'Ошибка создания уведомления'}), 500
            
    except Exception as e:
        print(f"Ошибка создания уведомления: {e}")
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/settings', methods=['GET', 'POST'])
def notification_settings():
    """Настройки уведомлений пользователя"""
    try:
        user_id = get_current_user_id()
        user_db_id = ensure_user_exists(user_id, f'user_{user_id}', 'User')
        
        if request.method == 'GET':
            # Получаем настройки (пока заглушка)
            settings = {
                'offer_received': True,
                'offer_accepted': True,
                'offer_rejected': True,
                'payment_received': True,
                'channel_verified': True,
                'system_notifications': True,
                'email_notifications': False,
                'push_notifications': True
            }
            
            return jsonify({
                'settings': settings
            })
        
        elif request.method == 'POST':
            # Сохраняем настройки (пока заглушка)
            data = request.get_json()
            
            # Здесь должно быть сохранение в базу данных
            
            return jsonify({
                'success': True,
                'message': 'Настройки сохранены'
            })
            
    except Exception as e:
        print(f"Ошибка настроек уведомлений: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# АВТОМАТИЧЕСКИЕ УВЕДОМЛЕНИЯ ДЛЯ СОБЫТИЙ СИСТЕМЫ
# =============================================================================

class AutoNotifications:
    """Автоматические уведомления для событий системы"""
    
    @staticmethod
    def on_offer_received(channel_owner_id: int, offer_id: int, offer_title: str, 
                         advertiser_name: str, price: float, currency: str):
        """Уведомление о получении нового оффера"""
        NotificationManager.create_notification(
            channel_owner_id,
            'offer_received',
            '💼 Новое рекламное предложение',
            f'От {advertiser_name}: "{offer_title}" за {price:,.0f} {currency}',
            {
                'offer_id': offer_id,
                'action_url': f'/offers?offer_id={offer_id}',
                'action_text': 'Посмотреть оффер'
            },
            priority=1
        )
    
    @staticmethod
    def on_offer_response(advertiser_id: int, channel_title: str, response_type: str, 
                         offer_title: str, offer_id: int):
        """Уведомление об ответе на оффер"""
        response_texts = {
            'accepted': '✅ принял',
            'rejected': '❌ отклонил',
            'negotiate': '💬 хочет обсудить'
        }
        
        response_text = response_texts.get(response_type, response_type)
        
        NotificationManager.create_notification(
            advertiser_id,
            'offer_response',
            f'📢 Ответ на ваш оффер',
            f'Канал "{channel_title}" {response_text} предложение "{offer_title}"',
            {
                'offer_id': offer_id,
                'response_type': response_type,
                'action_url': f'/offers/my-offers?offer_id={offer_id}',
                'action_text': 'Посмотреть детали'
            },
            priority=1
        )
    
    @staticmethod
    def on_payment_received(user_id: int, amount: float, currency: str, 
                           offer_title: str, transaction_id: str):
        """Уведомление о получении платежа"""
        NotificationManager.create_notification(
            user_id,
            'payment_received',
            '💰 Платеж получен',
            f'Получен платеж {amount:,.0f} {currency} за "{offer_title}"',
            {
                'amount': amount,
                'currency': currency,
                'transaction_id': transaction_id,
                'action_url': '/payments',
                'action_text': 'Посмотреть платежи'
            },
            priority=2
        )
    
    @staticmethod
    def on_channel_verified(user_id: int, channel_title: str, channel_id: int):
        """Уведомление о верификации канала"""
        NotificationManager.create_notification(
            user_id,
            'channel_verified',
            '✅ Канал верифицирован',
            f'Ваш канал "{channel_title}" прошел верификацию',
            {
                'channel_id': channel_id,
                'action_url': '/channels-enhanced',
                'action_text': 'Посмотреть каналы'
            },
            priority=1
        )
    
    @staticmethod
    def on_offer_deadline_reminder(user_id: int, offer_title: str, offer_id: int, days_left: int):
        """Напоминание о приближающемся дедлайне"""
        NotificationManager.create_notification(
            user_id,
            'deadline_reminder',
            '⏰ Напоминание о дедлайне',
            f'До окончания оффера "{offer_title}" осталось {days_left} дн.',
            {
                'offer_id': offer_id,
                'days_left': days_left,
                'action_url': f'/offers/my-offers?offer_id={offer_id}',
                'action_text': 'Проверить статус'
            },
            priority=1
        )

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def format_datetime(dt_str):
    """Форматирование даты и времени"""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return dt_str

def get_time_ago(dt_str):
    """Получение относительного времени"""
    if not dt_str:
        return 'Неизвестно'
    
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f'{diff.days} дн. назад'
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f'{hours} ч. назад'
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f'{minutes} мин. назад'
        else:
            return 'Только что'
    except:
        return 'Неизвестно'

def get_notification_icon(notification_type):
    """Получение иконки для типа уведомления"""
    icons = {
        'offer_received': '💼',
        'offer_accepted': '✅',
        'offer_rejected': '❌',
        'payment_received': '💰',
        'payment_sent': '💸',
        'channel_verified': '🔒',
        'deadline_reminder': '⏰',
        'system': '🔔'
    }
    return icons.get(notification_type, '📢')

def get_notification_color(notification_type):
    """Получение цвета для типа уведомления"""
    colors = {
        'offer_received': '#2196F3',
        'offer_accepted': '#4CAF50',
        'offer_rejected': '#F44336',
        'payment_received': '#4CAF50',
        'payment_sent': '#FF9800',
        'channel_verified': '#9C27B0',
        'deadline_reminder': '#FF5722',
        'system': '#607D8B'
    }
    return colors.get(notification_type, '#2196F3')

# Экспорт для использования в других модулях
__all__ = ['NotificationManager', 'AutoNotifications', 'notifications_bp']