from functools import wraps
from flask import jsonify, request
from app.services.auth_service import auth_service
from app.models.database import db_manager
import logging

logger = logging.getLogger(__name__)


def require_telegram_auth(f):
    """Декоратор для обязательной авторизации через Telegram"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.services.security_service import security_service

        telegram_user_id = auth_service.get_current_user_id()

        if not telegram_user_id:
            logger.warning(
                f"Unauthorized access attempt to {request.endpoint} from IP: {security_service.get_client_ip()}")
            logger.warning(f"Request headers: {dict(request.headers)}")

            return jsonify({
                'success': False,
                'error': 'Требуется авторизация через Telegram',
                'code': 'AUTH_REQUIRED',
                'debug_info': {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'has_headers': bool(request.headers.get('X-Telegram-User-Id')),
                    'has_json': request.is_json,
                    'content_type': request.headers.get('Content-Type')
                }
            }), 401

        # Проверяем существование пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"User {telegram_user_id} not found in database")
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден в системе',
                'code': 'USER_NOT_FOUND'
            }), 401

        logger.info(f"Authenticated user {telegram_user_id} accessing {request.endpoint}")
        return f(*args, **kwargs)

    return decorated_function