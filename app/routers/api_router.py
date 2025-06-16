# app/routers/api_router.py
"""
API маршрутизатор для Telegram Mini App

Содержит общие API эндпоинты, не относящиеся к конкретным сущностям.
Включает эндпоинты для аутентификации, статистики и системной информации.
"""

import time
from flask import Blueprint, request, jsonify, current_app, g
from .middleware import (
    require_telegram_auth, 
    cache_response, 
    rate_limit_decorator,
    get_security_stats,
    TelegramAuth
)

# Создание Blueprint для API
api_bp = Blueprint('api', __name__)

# === АУТЕНТИФИКАЦИЯ ===

@api_bp.route('/auth/status')
@cache_response(timeout=60)  # Кэшируем на 1 минуту
def auth_status():
    """
    Проверка статуса аутентификации пользователя
    
    Returns:
        JSON с информацией об аутентификации
    """
    try:
        telegram_user_id = TelegramAuth.get_current_user_id()
        
        if not telegram_user_id:
            return jsonify({
                'authenticated': False,
                'message': 'Telegram user ID not found'
            })
        
        # Проверяем существование пользователя в БД
        user_db_id = TelegramAuth.ensure_user_exists(telegram_user_id)
        
        if not user_db_id:
            return jsonify({
                'authenticated': False,
                'message': 'User registration failed'
            }), 500
        
        # Получаем дополнительную информацию о пользователе
        from ..models.user import User
        user = User.query.get(user_db_id)
        
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
                'balance': user.balance,
                'created_at': user.created_at.isoformat() if user.created_at else None
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
        if not TelegramAuth.validate_telegram_data(init_data):
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
        user_db_id = TelegramAuth.ensure_user_exists(telegram_user_id)
        
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

@api_bp.route('/status')
@cache_response(timeout=30)  # Кэшируем на 30 секунд
def system_status():
    """
    Статус системы и основные метрики
    
    Returns:
        JSON с информацией о состоянии системы
    """
    try:
        # Проверяем подключение к БД
        from ..models.database import db
        db.session.execute('SELECT 1')
        database_status = 'healthy'
        
        # Получаем статистику
        from ..models.user import User
        from ..models.channels import Channel
        from ..models.offer import Offer
        
        user_count = User.query.count()
        channel_count = Channel.query.count()
        offer_count = Offer.query.count()
        
        # Статистика безопасности
        security_stats = get_security_stats()
        
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
            'security': security_stats,
            'telegram_bot_configured': bool(current_app.config.get('TELEGRAM_BOT_TOKEN'))
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
        from ..models.user import User
        
        user = User.query.get(g.current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found'
            }), 404
        
        # Получаем статистику пользователя
        from ..models.channels import Channel
        from ..models.offer import Offer
        
        channels_count = Channel.query.filter_by(owner_id=user.id).count()
        offers_count = Offer.query.filter_by(advertiser_id=user.id).count()
        
        return jsonify({
            'user': {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
                'balance': user.balance,
                'created_at': user.created_at.isoformat() if user.created_at else None
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
@rate_limit_decorator(max_requests=5, window=300)  # 5 обновлений за 5 минут
def update_user_profile():
    """
    Обновление профиля пользователя
    
    Expected JSON:
    {
        "user_type": "channel_owner" | "advertiser",
        "username": "новое_имя_пользователя"
    }
    
    Returns:
        JSON с обновленными данными пользователя
    """
    try:
        from ..models.user import User
        from ..models.database import db
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400
        
        user = User.query.get(g.current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found'
            }), 404
        
        # Обновляем разрешенные поля
        if 'user_type' in data:
            if data['user_type'] in ['channel_owner', 'advertiser']:
                user.user_type = data['user_type']
            else:
                return jsonify({
                    'error': 'Invalid user_type'
                }), 400
        
        if 'username' in data:
            # Проверяем уникальность username
            existing_user = User.query.filter(
                User.username == data['username'],
                User.id != user.id
            ).first()
            
            if existing_user:
                return jsonify({
                    'error': 'Username already taken'
                }), 400
            
            user.username = data['username']
        
        # Сохраняем изменения
        db.session.commit()
        
        current_app.logger.info(f"User {user.telegram_id} updated profile")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
                'balance': user.balance
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating user profile: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

# === ПОИСК И ФИЛЬТРАЦИЯ ===

@api_bp.route('/search')
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=60)  # 20 поисковых запросов в минуту
def global_search():
    """
    Глобальный поиск по каналам и офферам
    
    Query params:
    - q: поисковый запрос
    - type: тип поиска (channels, offers, all)
    - limit: количество результатов (по умолчанию 10)
    
    Returns:
        JSON с результатами поиска
    """
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')
        limit = min(int(request.args.get('limit', 10)), 50)  # Максимум 50 результатов
        
        if not query:
            return jsonify({
                'error': 'Search query is required'
            }), 400
        
        if len(query) < 2:
            return jsonify({
                'error': 'Search query must be at least 2 characters'
            }), 400
        
        results = {
            'query': query,
            'channels': [],
            'offers': []
        }
        
        # Поиск по каналам
        if search_type in ['channels', 'all']:
            from ..models.channels import Channel
            
            channels = Channel.query.filter(
                Channel.is_verified == True,
                Channel.channel_name.ilike(f'%{query}%')
            ).limit(limit).all()
            
            results['channels'] = [{
                'id': channel.id,
                'channel_name': channel.channel_name,
                'channel_username': channel.channel_username,
                'subscribers_count': channel.subscribers_count,
                'category': channel.category,
                'price_per_post': channel.price_per_post
            } for channel in channels]
        
        # Поиск по офферам
        if search_type in ['offers', 'all']:
            from ..models.offer import Offer
            
            offers = Offer.query.filter(
                Offer.status == 'active',
                Offer.title.ilike(f'%{query}%')
            ).limit(limit).all()
            
            results['offers'] = [{
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': offer.budget,
                'category': offer.category,
                'created_at': offer.created_at.isoformat() if offer.created_at else None
            } for offer in offers]
        
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
        from ..models.user import User
        from ..models.channels import Channel
        from ..models.offer import Offer
        from ..models.response import Response
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        user = User.query.get(g.current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User not found'
            }), 404
        
        # Базовая статистика
        stats = {
            'user_type': user.user_type,
            'balance': user.balance
        }
        
        # Статистика для владельцев каналов
        if user.user_type == 'channel_owner':
            # Количество каналов
            channels_count = Channel.query.filter_by(owner_id=user.id).count()
            verified_channels = Channel.query.filter_by(
                owner_id=user.id, 
                is_verified=True
            ).count()
            
            # Общее количество подписчиков
            total_subscribers = db.session.query(
                func.sum(Channel.subscribers_count)
            ).filter_by(owner_id=user.id).scalar() or 0
            
            # Активные отклики на каналы
            active_responses = Response.query.join(Channel).filter(
                Channel.owner_id == user.id,
                Response.status == 'pending'
            ).count()
            
            stats.update({
                'channels': {
                    'total': channels_count,
                    'verified': verified_channels,
                    'total_subscribers': total_subscribers
                },
                'responses': {
                    'active': active_responses
                }
            })
        
        # Статистика для рекламодателей
        elif user.user_type == 'advertiser':
            # Количество офферов
            offers_count = Offer.query.filter_by(advertiser_id=user.id).count()
            active_offers = Offer.query.filter_by(
                advertiser_id=user.id,
                status='active'
            ).count()
            
            # Общий бюджет офферов
            total_budget = db.session.query(
                func.sum(Offer.budget)
            ).filter_by(advertiser_id=user.id).scalar() or 0
            
            # Отклики на офферы
            responses_count = Response.query.join(Offer).filter(
                Offer.advertiser_id == user.id
            ).count()
            
            stats.update({
                'offers': {
                    'total': offers_count,
                    'active': active_offers,
                    'total_budget': total_budget
                },
                'responses': {
                    'received': responses_count
                }
            })
        
        # Активность за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        if user.user_type == 'channel_owner':
            recent_responses = Response.query.join(Channel).filter(
                Channel.owner_id == user.id,
                Response.created_at >= thirty_days_ago
            ).count()
            stats['recent_activity'] = {
                'responses_last_30_days': recent_responses
            }
        else:
            recent_offers = Offer.query.filter(
                Offer.advertiser_id == user.id,
                Offer.created_at >= thirty_days_ago
            ).count()
            stats['recent_activity'] = {
                'offers_last_30_days': recent_offers
            }
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

# === УВЕДОМЛЕНИЯ ===

@api_bp.route('/notifications')
@require_telegram_auth
@cache_response(timeout=60)  # Кэшируем на 1 минуту
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
        limit = min(int(request.args.get('limit', 20)), 100)
        unread_only = request.args.get('unread_only', '').lower() == 'true'
        
        # Пока используем простую систему уведомлений
        # В будущем можно создать отдельную модель Notification
        
        notifications = []
        
        # Уведомления для владельцев каналов
        if hasattr(g, 'current_user_id'):
            from ..models.user import User
            user = User.query.get(g.current_user_id)
            
            if user and user.user_type == 'channel_owner':
                # Новые отклики на каналы
                from ..models.response import Response
                from ..models.channels import Channel
                
                new_responses = Response.query.join(Channel).filter(
                    Channel.owner_id == user.id,
                    Response.status == 'pending'
                ).order_by(Response.created_at.desc()).limit(limit).all()
                
                for response in new_responses:
                    notifications.append({
                        'id': f"response_{response.id}",
                        'type': 'new_response',
                        'title': 'Новый отклик на ваш канал',
                        'message': f'Получен отклик на канал {response.channel.channel_name}',
                        'timestamp': response.created_at.isoformat() if response.created_at else None,
                        'unread': True,
                        'data': {
                            'response_id': response.id,
                            'channel_id': response.channel_id,
                            'offer_id': response.offer_id
                        }
                    })
            
            elif user and user.user_type == 'advertiser':
                # Уведомления для рекламодателей
                from ..models.response import Response
                from ..models.offer import Offer
                
                responses_to_offers = Response.query.join(Offer).filter(
                    Offer.advertiser_id == user.id,
                    Response.status == 'pending'
                ).order_by(Response.created_at.desc()).limit(limit).all()
                
                for response in responses_to_offers:
                    notifications.append({
                        'id': f"offer_response_{response.id}",
                        'type': 'offer_response',
                        'title': 'Отклик на ваш оффер',
                        'message': f'Канал {response.channel.channel_name} откликнулся на ваш оффер',
                        'timestamp': response.created_at.isoformat() if response.created_at else None,
                        'unread': True,
                        'data': {
                            'response_id': response.id,
                            'channel_id': response.channel_id,
                            'offer_id': response.offer_id
                        }
                    })
        
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

# === ОБРАБОТЧИКИ ОШИБОК ===

@api_bp.errorhandler(404)
def api_not_found(error):
    """Обработчик 404 ошибок для API"""
    return jsonify({
        'error': 'API endpoint not found',
        'message': 'The requested API endpoint does not exist'
    }), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
    """Обработчик 405 ошибок для API"""
    return jsonify({
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }), 405

@api_bp.errorhandler(429)
def rate_limit_exceeded(error):
    """Обработчик превышения rate limit"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.'
    }), 429

# Инициализация Blueprint
def init_api_routes():
    """Инициализация API маршрутов"""
    current_app.logger.info("✅ API routes initialized")

# Экспорт
__all__ = ['api_bp', 'init_api_routes']