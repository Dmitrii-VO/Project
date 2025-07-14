# app/routers/api_router.py
"""
API маршрутизатор для Telegram Mini App

Содержит общие API эндпоинты, не относящиеся к конкретным сущностям.
Включает эндпоинты для аутентификации, статистики и системной информации.
"""

import time
from flask import Blueprint, request, jsonify, current_app, g
from app.services.auth_service import AuthService
from .middleware import (
    require_telegram_auth, 
    cache_response, 
    rate_limit_decorator,
    get_security_stats
)

# Создание Blueprint для API
api_bp = Blueprint('api', __name__)

# === АУТЕНТИФИКАЦИЯ ===
@api_bp.route('/auth/status')
@cache_response(timeout=60)
def auth_status():
    """
    Проверка статуса аутентификации пользователя
    
    Returns:
        JSON с информацией об аутентификации
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        
        telegram_user_id = AuthService.get_current_user_id()
        
        if not telegram_user_id:
            return jsonify({
                'authenticated': False,
                'message': 'Telegram user ID not found'
            })
        
        # Проверяем существование пользователя в БД
        user_db_id = AuthService.ensure_user_exists(telegram_user_id)
        
        if not user_db_id:
            return jsonify({
                'authenticated': False,
                'message': 'User registration failed'
            }), 500
        
        # Получаем информацию о пользователе через SQLite
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_db_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({
                'authenticated': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user['id'],
                'telegram_id': user['telegram_id'],
                'username': user.get('username', ''),
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'is_admin': bool(user.get('is_admin', False)),
                'created_at': user.get('created_at')
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking auth status: {e}")
        return jsonify({
            'authenticated': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/auth/login', methods=['POST'])
@rate_limit_decorator(max_requests=10, window=300)  # 10 попыток за 5 минут
def telegram_login():
    """
    Аутентификация пользователя через Telegram WebApp
    
    Expected JSON:
    {
        "init_data": "строка с данными от Telegram WebApp"
    }
    
    Returns:
        JSON с результатом аутентификации
    """
    try:
        data = request.get_json()
        
        if not data or 'init_data' not in data:
            return jsonify({
                'success': False,
                'error': 'init_data is required'
            }), 400
        
        init_data = data['init_data']
        
        # Валидируем данные от Telegram
        if not AuthService.validate_telegram_data(init_data):
            return jsonify({
                'success': False,
                'error': 'Invalid Telegram data'
            }), 401
        
        # Извлекаем user_id из init_data (упрощенная версия)
        import urllib.parse
        parsed_data = urllib.parse.parse_qs(init_data)
        
        # В реальном приложении нужно парсить user JSON
        # Пока используем заголовки
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        
        if not telegram_user_id:
            return jsonify({
                'success': False,
                'error': 'Telegram user ID not found'
            }), 400
        
        # Создаем или обновляем пользователя
        user_db_id = AuthService.ensure_user_exists(telegram_user_id)
        
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'User registration failed'
            }), 500
        
        # Сохраняем в сессии (для резервного способа аутентификации)
        from flask import session
        session['telegram_user_id'] = telegram_user_id
        session['user_db_id'] = user_db_id
        
        current_app.logger.info(f"User {telegram_user_id} logged in successfully")
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user_id': user_db_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error during login: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/auth/logout', methods=['POST'])
@require_telegram_auth
def logout():
    """
    Выход пользователя из системы
    
    Returns:
        JSON с результатом выхода
    """
    try:
        from flask import session
        
        # Очищаем сессию
        session.pop('telegram_user_id', None)
        session.pop('user_db_id', None)
        
        current_app.logger.info(f"User {g.telegram_user_id} logged out")
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error during logout: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# === СИСТЕМНАЯ ИНФОРМАЦИЯ ===

@cache_response(timeout=30)  # Кэшируем на 30 секунд
@api_bp.route('/status')
def system_status():
    """
    Статус системы и основные метрики
    
    Returns:
        JSON с информацией о состоянии системы
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        import time
        
        # Проверяем подключение к БД
        try:
            conn = sqlite3.connect(AppConfig.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            database_status = 'healthy'
        except Exception as e:
            database_status = f'unhealthy: {str(e)}'
            return jsonify({
                'status': 'unhealthy',
                'error': 'Database connection failed',
                'timestamp': time.time()
            }), 500
        
        # Получаем статистику
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM channels")
        channel_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM offers")
        offer_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'version': '1.0.0',
            'database': {
                'status': database_status,
                'connections': 'available'
            },
            'statistics': {
                'users': user_count,
                'channels': channel_count,
                'offers': offer_count
            },
            'telegram_bot_configured': bool(AppConfig.BOT_TOKEN)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system status: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500


@api_bp.route('/config')
@require_telegram_auth
@cache_response(timeout=300)  # Кэшируем на 5 минут
def app_config():
    """
    Конфигурация приложения для фронтенда
    
    Returns:
        JSON с публичными настройками приложения
    """
    try:
        config = {
            'app_name': 'Telegram Mini App',
            'version': '1.0.0',
            'api_version': 'v1',
            'features': {
                'channels': True,
                'offers': True,
                'analytics': True,
                'payments': bool(current_app.config.get('PAYMENT_PROVIDER_TOKEN')),
                'notifications': True
            },
            'limits': {
                'max_channels_per_user': 10,
                'max_offers_per_user': 50,
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'supported_file_types': ['jpg', 'jpeg', 'png', 'gif', 'mp4']
            },
            'telegram': {
                'bot_username': current_app.config.get('TELEGRAM_BOT_USERNAME'),
                'webapp_url': current_app.config.get('WEBAPP_URL')
            }
        }
        
        return jsonify(config)
        
    except Exception as e:
        current_app.logger.error(f"Error getting app config: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

# === ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ ===
@api_bp.route('/user/profile')
@require_telegram_auth
def get_user_profile():
    """
    Получение профиля текущего пользователя
    
    Returns:
        JSON с данными профиля пользователя
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        from app.models.database import get_user_id_from_request
        
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        user_db_id = user['id']
        
        # Получаем статистику каналов
        cursor.execute("SELECT COUNT(*) as count FROM channels WHERE owner_id = ?", (user_db_id,))
        channels_count = cursor.fetchone()['count']
        
        # Получаем статистику офферов
        cursor.execute("SELECT COUNT(*) as count FROM offers WHERE created_by = ?", (user_db_id,))
        offers_count = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'user': {
                'id': user['id'],
                'telegram_id': user['telegram_id'],
                'username': user.get('username', ''),
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'is_admin': bool(user.get('is_admin', False)),
                'created_at': user.get('created_at')
            },
            'statistics': {
                'channels_count': channels_count,
                'offers_count': offers_count
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user profile: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@api_bp.route('/user/profile', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=5, window=300)
def update_user_profile():
    """
    Обновление профиля пользователя
    
    Expected JSON:
    {
        "username": "новое_имя_пользователя"
    }
    
    Returns:
        JSON с обновленными данными пользователя
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        from app.models.database import get_user_id_from_request
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        user_db_id = user['id']
        
        # Обновляем разрешенные поля
        if 'username' in data:
            new_username = data['username']
            
            # Проверяем уникальность username
            cursor.execute("""
                SELECT id FROM users 
                WHERE username = ? AND id != ?
            """, (new_username, user_db_id))
            
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Username already taken'}), 400
            
            # Обновляем username
            cursor.execute("""
                UPDATE users 
                SET username = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (new_username, user_db_id))
        
        # Сохраняем изменения
        conn.commit()
        
        # Получаем обновленные данные
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_db_id,))
        updated_user = cursor.fetchone()
        conn.close()
        
        current_app.logger.info(f"User {telegram_user_id} updated profile")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': updated_user['id'],
                'telegram_id': updated_user['telegram_id'],
                'username': updated_user.get('username', ''),
                'first_name': updated_user.get('first_name', ''),
                'last_name': updated_user.get('last_name', ''),
                'is_admin': bool(updated_user.get('is_admin', False))
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
# === ПОИСК И ФИЛЬТРАЦИЯ ===

@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=60)  # 20 поисковых запросов в минуту
@api_bp.route('/search', methods=['GET'])
def global_search():
    """
    Глобальный поиск по системе
    
    Query params:
    - query: поисковый запрос (обязательный)
    - type: тип поиска (channels, offers, all)
    - limit: максимальное количество результатов (по умолчанию 20)
    
    Returns:
        JSON с результатами поиска
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        
        query = request.args.get('query', '').strip()
        search_type = request.args.get('type', 'all').lower()
        limit = min(int(request.args.get('limit', 20)), 50)
        
        if not query or len(query) < 2:
            return jsonify({
                'error': 'Query too short',
                'message': 'Search query must be at least 2 characters'
            }), 400
        
        results = {
            'query': query,
            'channels': [],
            'offers': []
        }
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Поиск по каналам
        if search_type in ['channels', 'all']:
            cursor.execute("""
                SELECT id, title, username, subscriber_count, category
                FROM channels 
                WHERE is_verified = 1 
                AND (title LIKE ? OR username LIKE ?)
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))
            
            channels = cursor.fetchall()
            results['channels'] = [{
                'id': channel['id'],
                'channel_name': channel['title'],
                'channel_username': channel['username'],
                'subscriber_count': channel['subscriber_count'],
                'category': channel['category']
            } for channel in channels]
        
        # Поиск по офферам
        if search_type in ['offers', 'all']:
            cursor.execute("""
                SELECT id, title, description, price, category, created_at
                FROM offers 
                WHERE status = 'active' 
                AND title LIKE ?
                LIMIT ?
            """, (f'%{query}%', limit))
            
            offers = cursor.fetchall()
            results['offers'] = [{
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'price': offer['price'],
                'category': offer['category'],
                'created_at': offer['created_at']
            } for offer in offers]
        
        conn.close()
        return jsonify(results)
        
    except ValueError:
        return jsonify({
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error in global search: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500



# === СТАТИСТИКА И АНАЛИТИКА ===

@api_bp.route('/stats/dashboard')
@require_telegram_auth
@cache_response(timeout=300)  # Кэшируем на 5 минут
def dashboard_stats():
    """
    Статистика для дашборда пользователя
    
    Returns:
        JSON с основными метриками пользователя
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        from app.models.database import get_user_id_from_request
        from datetime import datetime, timedelta
        
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        user_db_id = user['id']
        
        # Статистика каналов пользователя
        cursor.execute("""
            SELECT COUNT(*) as total_channels,
                   COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_channels,
                   COALESCE(SUM(subscriber_count), 0) as total_subscribers
            FROM channels 
            WHERE owner_id = ?
        """, (user_db_id,))
        
        channel_stats = cursor.fetchone()
        
        # Статистика офферов пользователя
        cursor.execute("""
            SELECT COUNT(*) as total_offers,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
                   COALESCE(SUM(price), 0) as total_budget
            FROM offers 
            WHERE created_by = ?
        """, (user_db_id,))
        
        offer_stats = cursor.fetchone()
        
        # Статистика откликов
        cursor.execute("""
            SELECT COUNT(*) as total_responses,
                   COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_responses
            FROM offer_responses 
            WHERE user_id = ?
        """, (user_db_id,))
        
        response_stats = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'user_id': telegram_user_id,
            'channels': {
                'total': channel_stats['total_channels'],
                'verified': channel_stats['verified_channels'],
                'total_subscribers': channel_stats['total_subscribers']
            },
            'offers': {
                'total': offer_stats['total_offers'],
                'active': offer_stats['active_offers'],
                'total_budget': float(offer_stats['total_budget'])
            },
            'responses': {
                'total': response_stats['total_responses'],
                'accepted': response_stats['accepted_responses'],
                'acceptance_rate': (response_stats['accepted_responses'] / response_stats['total_responses'] * 100) if response_stats['total_responses'] > 0 else 0
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
# === УВЕДОМЛЕНИЯ ===
@api_bp.route('/notifications')
@require_telegram_auth
@cache_response(timeout=60)
def get_notifications():
    """
    Получение уведомлений для пользователя
    
    Query params:
    - limit: количество уведомлений (по умолчанию 20)
    - unread_only: только непрочитанные (true/false)
    
    Returns:
        JSON с уведомлениями пользователя
    """
    try:
        import sqlite3
        from app.config.telegram_config import AppConfig
        from app.models.database import get_user_id_from_request
        
        limit = min(int(request.args.get('limit', 20)), 100)
        unread_only = request.args.get('unread_only', '').lower() == 'true'
        
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем пользователя
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        user_db_id = user['id']
        notifications = []
        
        # Уведомления для владельцев каналов - новые отклики
        cursor.execute("""
            SELECT r.id, r.offer_id, r.created_at, r.status,
                   c.title as channel_name, c.id as channel_id
            FROM offer_responses r
            JOIN channels c ON r.channel_id = c.id  
            WHERE c.owner_id = ? AND r.status = 'pending'
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (user_db_id, limit))
        
        responses = cursor.fetchall()
        
        for response in responses:
            notifications.append({
                'id': f"response_{response['id']}",
                'type': 'new_response',
                'title': 'Новый отклик на ваш канал',
                'message': f'Получен отклик на канал {response["channel_name"]}',
                'timestamp': response['created_at'],
                'unread': True,
                'data': {
                    'response_id': response['id'],
                    'channel_id': response['channel_id'],
                    'offer_id': response['offer_id']
                }
            })
        
        # Уведомления для рекламодателей - отклики на офферы
        cursor.execute("""
            SELECT r.id, r.offer_id, r.channel_id, r.created_at,
                   c.title as channel_name, o.title as offer_title
            FROM offer_responses r
            JOIN channels c ON r.channel_id = c.id
            JOIN offers o ON r.offer_id = o.id
            WHERE o.created_by = ? AND r.status = 'pending'
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (user_db_id, limit))
        
        offer_responses = cursor.fetchall()
        
        for response in offer_responses:
            notifications.append({
                'id': f"offer_response_{response['id']}",
                'type': 'offer_response', 
                'title': 'Отклик на ваш оффер',
                'message': f'Канал {response["channel_name"]} откликнулся на ваш оффер "{response["offer_title"]}"',
                'timestamp': response['created_at'],
                'unread': True,
                'data': {
                    'response_id': response['id'],
                    'channel_id': response['channel_id'],
                    'offer_id': response['offer_id']
                }
            })
        
        conn.close()
        
        # Сортируем по времени
        notifications.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        return jsonify({
            'notifications': notifications[:limit],
            'total_count': len(notifications),
            'unread_count': len([n for n in notifications if n['unread']])
        })
        
    except ValueError:
        return jsonify({
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
# === СЛУЖЕБНЫЕ ЭНДПОИНТЫ ===

@api_bp.route('/upload', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=10, window=300)  # 10 загрузок за 5 минут
def upload_file():
    """
    Загрузка файлов (изображения для офферов, аватары каналов и т.д.)
    
    Form data:
    - file: файл для загрузки
    - type: тип файла (avatar, offer_image, etc.)
    
    Returns:
        JSON с информацией о загруженном файле
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        file_type = request.form.get('type', 'general')
        
        if file.filename == '':
            return jsonify({
                'error': 'No file selected'
            }), 400
        
        # Проверяем размер файла
        file.seek(0, 2)  # Перемещаемся в конец файла
        file_size = file.tell()
        file.seek(0)  # Возвращаемся в начало
        
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return jsonify({
                'error': f'File too large. Maximum size: {max_size} bytes'
            }), 400
        
        # Проверяем расширение файла
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'webp'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'error': f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'
            }), 400
        
        # Генерируем безопасное имя файла
        import uuid
        import os
        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Создаем директорию для загрузок если её нет
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', file_type)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Сохраняем файл
        file_path = os.path.join(upload_dir, safe_filename)
        file.save(file_path)
        
        # Генерируем URL для доступа к файлу
        file_url = f"/static/uploads/{file_type}/{safe_filename}"
        
        current_app.logger.info(
            f"File uploaded by user {g.telegram_user_id}: {safe_filename} ({file_size} bytes)"
        )
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': {
                'filename': safe_filename,
                'original_filename': file.filename,
                'size': file_size,
                'type': file_type,
                'url': file_url,
                'extension': file_extension
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@api_bp.route('/validate', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=60)  # 20 валидаций в минуту
def validate_data():
    """
    Валидация данных (каналы, URL и т.д.)
    
    Expected JSON:
    {
        "type": "channel_url" | "telegram_channel" | "url",
        "value": "значение для валидации"
    }
    
    Returns:
        JSON с результатом валидации
    """
    try:
        data = request.get_json()
        
        if not data or 'type' not in data or 'value' not in data:
            return jsonify({
                'error': 'Type and value are required'
            }), 400
        
        validation_type = data['type']
        value = data['value']
        
        result = {
            'valid': False,
            'message': '',
            'data': {}
        }
        
        if validation_type == 'channel_url':
            # Валидация URL канала Telegram
            import re
            
            telegram_channel_pattern = r'^https://t\.me/([a-zA-Z0-9_]+)'
            match = re.match(telegram_channel_pattern, value)
            
            if match:
                channel_username = match.group(1)
                result.update({
                    'valid': True,
                    'message': 'Valid Telegram channel URL',
                    'data': {
                        'channel_username': channel_username,
                        'url': value
                    }
                })
            else:
                result['message'] = 'Invalid Telegram channel URL format'
        
        elif validation_type == 'telegram_channel':
            # Валидация username канала
            import re
            
            if re.match(r'^[a-zA-Z0-9_]{5,32}$', value):
                result.update({
                    'valid': True,
                    'message': 'Valid Telegram channel username',
                    'data': {
                        'channel_username': value
                    }
                })
            else:
                result['message'] = 'Username must be 5-32 characters and contain only letters, numbers, and underscores'
        
        elif validation_type == 'url':
            # Валидация обычного URL
            import re
            
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if re.match(url_pattern, value):
                result.update({
                    'valid': True,
                    'message': 'Valid URL',
                    'data': {
                        'url': value
                    }
                })
            else:
                result['message'] = 'Invalid URL format'
        
        else:
            return jsonify({
                'error': f'Unknown validation type: {validation_type}'
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error validating data: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500


# Инициализация Blueprint
def init_api_routes():
    """Инициализация API маршрутов"""
    current_app.logger.info("✅ API routes initialized")

# Экспорт
__all__ = ['api_bp', 'init_api_routes']