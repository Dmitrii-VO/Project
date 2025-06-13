from flask import Blueprint, request, jsonify, session
from app.services.auth_service import auth_service
from app.services.security_service import security_service
from app.utils.decorators import require_telegram_auth
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/telegram', methods=['POST'])
def telegram_auth():
    """Авторизация пользователя через Telegram WebApp"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Получаем Telegram User ID
        telegram_user_id = None

        # Способ 1: Прямая передача user_id
        if 'telegram_user_id' in data:
            try:
                telegram_user_id = int(data['telegram_user_id'])
            except (ValueError, TypeError):
                pass

        # Способ 2: Из заголовков
        if not telegram_user_id:
            header_user_id = request.headers.get('X-Telegram-User-Id')
            if header_user_id:
                try:
                    telegram_user_id = int(header_user_id)
                except (ValueError, TypeError):
                    pass

        # Способ 3: Из initData
        if not telegram_user_id and 'initData' in data:
            telegram_user_id = auth_service.validate_telegram_data(data['initData'])

        # Способ 4: Из user объекта
        if not telegram_user_id and 'user' in data:
            user_data = data['user']
            if isinstance(user_data, dict) and 'id' in user_data:
                try:
                    telegram_user_id = int(user_data['id'])
                except (ValueError, TypeError):
                    pass

        if not telegram_user_id:
            logger.error(f"Failed to get telegram_user_id from auth request")
            return jsonify({
                'success': False,
                'error': 'Не удалось получить Telegram User ID',
                'debug_info': {
                    'has_telegram_user_id': 'telegram_user_id' in data,
                    'has_header': bool(request.headers.get('X-Telegram-User-Id')),
                    'has_initData': 'initData' in data,
                    'has_user': 'user' in data
                }
            }), 400

        # Создаем/обновляем пользователя в базе
        username = data.get('username') or f'user_{telegram_user_id}'
        first_name = data.get('first_name') or 'User'

        user_db_id = auth_service.ensure_user_exists(telegram_user_id, username, first_name)

        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Ошибка создания пользователя'
            }), 500

        # Сохраняем в сессии
        session['telegram_user_id'] = telegram_user_id

        logger.info(f"Telegram user {telegram_user_id} authenticated successfully")

        return jsonify({
            'success': True,
            'telegram_user_id': telegram_user_id,
            'user_db_id': user_db_id,
            'username': username,
            'message': 'Авторизация успешна'
        })

    except Exception as e:
        logger.error(f"Telegram auth error: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка авторизации'
        }), 500


@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """Проверка статуса авторизации"""
    try:
        telegram_user_id = auth_service.get_current_user_id()

        if not telegram_user_id:
            return jsonify({
                'success': False,
                'authenticated': False,
                'error': 'Нет Telegram User ID'
            }), 401

        # Проверяем существование пользователя в БД
        from app.models.database import db_manager
        user = db_manager.execute_query(
            'SELECT id, username, first_name FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({
                'success': False,
                'authenticated': False,
                'error': 'Пользователь не найден в БД'
            }), 401

        return jsonify({
            'success': True,
            'authenticated': True,
            'telegram_user_id': telegram_user_id,
            'user_info': {
                'id': user['id'],
                'username': user['username'],
                'first_name': user['first_name']
            }
        })

    except Exception as e:
        logger.error(f"Auth check error: {e}")
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': 'Ошибка проверки авторизации'
        }), 500