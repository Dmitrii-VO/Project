import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import unquote
from flask import request, session
from app.config.telegram_config import AppConfig
from app.models.database import db_manager
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис аутентификации через Telegram"""

    def get_current_user_id(self) -> Optional[int]:
        """Получение текущего Telegram User ID"""
        # Попробуем получить из заголовков
        user_id_header = request.headers.get('X-Telegram-User-Id')
        if user_id_header:
            try:
                return int(user_id_header)
            except (ValueError, TypeError):
                pass

        # Из POST данных
        if request.method == 'POST' and request.is_json:
            try:
                data = request.get_json()
                if data and 'telegram_user_id' in data:
                    return int(data['telegram_user_id'])
            except:
                pass

        # Из GET параметров
        user_id_param = request.args.get('telegram_user_id')
        if user_id_param:
            try:
                return int(user_id_param)
            except (ValueError, TypeError):
                pass

        # Fallback на основного пользователя
        return AppConfig.YOUR_TELEGRAM_ID

    def validate_telegram_data(self, init_data_raw: str) -> Optional[int]:
        """Проверка подлинности данных от Telegram WebApp"""
        try:
            # Простая проверка формата (в продакшене нужна полная валидация с HMAC)
            if not init_data_raw or 'user=' not in init_data_raw:
                return None

            # Извлекаем user_id из initData
            for param in init_data_raw.split('&'):
                if param.startswith('user='):
                    user_data = unquote(param[5:])
                    try:
                        user_info = json.loads(user_data)
                        if 'id' in user_info:
                            return int(user_info['id'])
                    except:
                        pass
            return None

        except Exception as e:
            logger.error(f"Error validating Telegram data: {e}")
            return None

    def ensure_user_exists(self, telegram_user_id: int, username: str = None, first_name: str = None) -> Optional[int]:
        """Обеспечение существования пользователя в базе по Telegram ID"""
        try:
            # Проверяем существование пользователя
            user = db_manager.execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_user_id,),
                fetch_one=True
            )

            if not user:
                # Создаем нового пользователя
                logger.info(f"Creating new user for Telegram ID: {telegram_user_id}")

                db_manager.execute_query('''
                                         INSERT INTO users (telegram_id, username, first_name, is_admin, created_at)
                                         VALUES (?, ?, ?, ?, ?)
                                         ''', (
                                             telegram_user_id,
                                             username or f'user_{telegram_user_id}',
                                             first_name or 'Telegram User',
                                             telegram_user_id == AppConfig.YOUR_TELEGRAM_ID,
                                             datetime.now().isoformat()
                                         ))

                # Получаем созданного пользователя
                user = db_manager.execute_query(
                    'SELECT id FROM users WHERE telegram_id = ?',
                    (telegram_user_id,),
                    fetch_one=True
                )
            else:
                # Обновляем информацию о существующем пользователе
                if username or first_name:
                    db_manager.execute_query('''
                                             UPDATE users
                                             SET username   = COALESCE(?, username),
                                                 first_name = COALESCE(?, first_name),
                                                 updated_at = ?
                                             WHERE telegram_id = ?
                                             ''', (username, first_name, datetime.now().isoformat(), telegram_user_id))

            return user['id'] if user else None

        except Exception as e:
            logger.error(f"Ошибка создания/обновления пользователя {telegram_user_id}: {e}")
            return None

    def log_user_access(self, telegram_user_id: int, endpoint: str, success: bool = True, error: str = None):
        """Логирование доступа пользователей для отладки"""
        from app.services.security_service import security_service

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'telegram_user_id': telegram_user_id,
            'endpoint': endpoint,
            'success': success,
            'error': error,
            'ip': security_service.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')
        }

        if success:
            logger.info(f"User access: {telegram_user_id} -> {endpoint}")
        else:
            logger.warning(f"Failed user access: {telegram_user_id} -> {endpoint}, Error: {error}")


# Глобальный экземпляр
auth_service = AuthService()