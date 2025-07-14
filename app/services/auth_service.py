# app/services/auth_service.py
# ИСПРАВЛЕНО: только авторизация Telegram, БЕЗ работы с БД

import os
import json
import logging
from typing import Optional
from urllib.parse import unquote
from flask import request, session
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис аутентификации через Telegram"""

    def get_current_user_id(self) -> Optional[int]:
        """
        Получение текущего Telegram User ID
        
        ТОЛЬКО авторизация - НЕ работает с БД!
        Возвращает telegram_id или None.
        """
        
        # 1. Попробуем получить из заголовков
        user_id_header = request.headers.get('X-Telegram-User-Id')
        if user_id_header:
            try:
                user_id = int(user_id_header)
                logger.debug(f"🔍 User ID найден в заголовке: {user_id}")
                return user_id
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Неверный формат User ID в заголовке: {user_id_header}")

        # 2. Из POST данных
        if request.method == 'POST' and request.is_json:
            try:
                data = request.get_json()
                if data and 'telegram_id' in data:
                    user_id = int(data['telegram_id'])
                    logger.debug(f"🔍 User ID найден в POST данных: {user_id}")
                    return user_id
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга User ID из POST: {e}")

        # 3. Из GET параметров
        user_id_param = request.args.get('telegram_id')
        if user_id_param:
            try:
                user_id = int(user_id_param)
                logger.debug(f"🔍 User ID найден в GET параметрах: {user_id}")
                return user_id
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Неверный формат User ID в GET параметре: {user_id_param}")

        # 4. Из сессии (если есть)
        session_user_id = session.get('telegram_id')
        if session_user_id:
            try:
                user_id = int(session_user_id)
                logger.debug(f"🔍 User ID найден в сессии: {user_id}")
                return user_id
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Неверный формат User ID в сессии: {session_user_id}")

        # 5. РЕЖИМ РАЗРАБОТКИ - только для локальной разработки
        if self._is_development_mode():
            fallback_user_id = self._get_development_user_id()
            if fallback_user_id:
                logger.warning(f"🧪 РЕЖИМ РАЗРАБОТКИ: используется User ID {fallback_user_id}")
                logger.warning("🧪 В PRODUCTION этого быть не должно!")
                return fallback_user_id

        # 6. ЛОГИРУЕМ отсутствие авторизации
        self._log_missing_auth()
        
        # 7. ВОЗВРАЩАЕМ None - НЕТ fallback на админа!
        return None

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

    def log_user_access(self, telegram_id: int, endpoint: str, success: bool = True, error: str = None):
        """Логирование доступа пользователей для отладки"""
        log_entry = {
            'timestamp': self._get_current_timestamp(),
            'telegram_id': telegram_id,
            'endpoint': endpoint,
            'success': success,
            'error': error,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }

        if success:
            logger.info(f"User access: {telegram_id} -> {endpoint}")
        else:
            logger.warning(f"Failed user access: {telegram_id} -> {endpoint}, Error: {error}")

    def _is_development_mode(self) -> bool:
        """Проверка режима разработки"""
        return (
            AppConfig.DEBUG and 
            os.environ.get('DEBUG_AUTH', 'false').lower() == 'true'
        )

    def _get_development_user_id(self) -> Optional[int]:
        """Получение User ID для режима разработки"""
        # Можно указать в переменной окружения для тестирования
        debug_user_id = os.environ.get('DEBUG_USER_ID')
        if debug_user_id:
            try:
                return int(debug_user_id)
            except:
                pass
        
        # Или использовать админа только в debug режиме
        return AppConfig.YOUR_TELEGRAM_ID

    def _log_missing_auth(self) -> None:
        """Детальное логирование отсутствующей авторизации"""
        logger.info("🔍 ОТЛАДКА АВТОРИЗАЦИИ:")
        logger.info(f"   📍 Путь: {request.path}")
        logger.info(f"   📋 Метод: {request.method}")
        logger.info(f"   🌐 IP: {request.remote_addr}")
        
        # Проверяем заголовки
        auth_headers = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'X-Telegram-Username': request.headers.get('X-Telegram-Username'),
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent', '')[:50] + '...'
        }
        logger.info(f"   📨 Заголовки авторизации: {auth_headers}")
        
        # Проверяем POST данные
        if request.method == 'POST' and request.is_json:
            try:
                data = request.get_json() or {}
                has_telegram_data = bool(
                    data.get('telegram_id') or 
                    data.get('user', {}).get('id') or 
                    data.get('initData')
                )
                logger.info(f"   📤 Есть Telegram данные в POST: {has_telegram_data}")
            except:
                logger.info(f"   📤 Ошибка парсинга POST данных")
        
        # Проверяем GET параметры
        has_get_user_id = bool(request.args.get('telegram_id'))
        logger.info(f"   📥 Есть telegram_id в GET: {has_get_user_id}")
        
        # Проверяем сессию
        has_session_user_id = bool(session.get('telegram_id'))
        logger.info(f"   🍪 Есть telegram_id в сессии: {has_session_user_id}")

    def _get_current_timestamp(self) -> str:
        """Получение текущего времени в ISO формате"""
        from datetime import datetime
        return datetime.now().isoformat()

# Глобальный экземпляр
auth_service = AuthService()