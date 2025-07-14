# app/services/auth_service.py
# ЕДИНАЯ СИСТЕМА АВТОРИЗАЦИИ - АДЕКВАТНАЯ ВЕРСИЯ

import os
import json
import logging
from typing import Optional
from urllib.parse import unquote
from flask import request, session
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)


class AuthService:
    """Единая система авторизации через Telegram"""
    
    def __init__(self):
        self._request_cache = {}
    
    def get_current_user_id(self) -> Optional[int]:
        """
        Получение текущего Telegram User ID - ЕДИНАЯ ТОЧКА ВХОДА
        
        Кэширует результат в рамках одного запроса для оптимизации.
        Возвращает telegram_id (int) или None.
        """
        
        # Кэширование в рамках запроса
        cache_key = f"{id(request)}_{request.method}_{request.path}"
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]
        
        user_id = self._get_user_id_from_sources()
        self._request_cache[cache_key] = user_id
        
        if user_id:
            logger.debug(f"✅ Авторизация успешна: telegram_id={user_id}")
        else:
            logger.debug(f"❌ Авторизация не найдена для {request.method} {request.path}")
            
        return user_id
    
    def _get_user_id_from_sources(self) -> Optional[int]:
        """Получение User ID из различных источников по приоритету"""
        
        # 1. Из заголовков (основной способ для API)
        user_id = self._get_user_id_from_headers()
        if user_id:
            return user_id

        # 2. Из POST данных (для форм)
        user_id = self._get_user_id_from_post()
        if user_id:
            return user_id

        # 3. Из GET параметров (для ссылок)
        user_id = self._get_user_id_from_get()
        if user_id:
            return user_id

        # 4. Из сессии (для web-интерфейса)
        user_id = self._get_user_id_from_session()
        if user_id:
            return user_id

        # 5. Режим разработки (только для отладки)
        if self._is_development_mode():
            user_id = self._get_development_user_id()
            if user_id:
                logger.warning(f"🧪 РЕЖИМ РАЗРАБОТКИ: используется User ID {user_id}")
                return user_id

        # 6. Логируем отсутствие авторизации
        self._log_missing_auth()
        return None
    
    def _get_user_id_from_headers(self) -> Optional[int]:
        """Получение User ID из заголовков HTTP"""
        headers_to_check = [
            'X-Telegram-User-Id',
            'X-User-Id',
            'Authorization-User-Id',
            'telegram-user-id',
            'x-telegram-user-id',
            'x-user-id'
        ]
        
        for header in headers_to_check:
            value = request.headers.get(header)
            if value:
                try:
                    user_id = int(value)
                    logger.debug(f"🔍 User ID найден в заголовке {header}: {user_id}")
                    return user_id
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный формат User ID в заголовке {header}: {value}")
        return None
    
    def _get_user_id_from_post(self) -> Optional[int]:
        """Получение User ID из POST данных"""
        if request.method != 'POST':
            return None
            
        try:
            if request.is_json:
                data = request.get_json() or {}
                # Проверяем разные варианты названий полей
                for field in ['telegram_id', 'user_id', 'id']:
                    if field in data:
                        user_id = int(data[field])
                        logger.debug(f"🔍 User ID найден в POST.{field}: {user_id}")
                        return user_id
                        
                # Вложенные объекты
                if 'user' in data and isinstance(data['user'], dict):
                    if 'id' in data['user']:
                        user_id = int(data['user']['id'])
                        logger.debug(f"🔍 User ID найден в POST.user.id: {user_id}")
                        return user_id
                        
            elif request.form:
                # Данные из form-data
                for field in ['telegram_id', 'user_id', 'id']:
                    if field in request.form:
                        user_id = int(request.form[field])
                        logger.debug(f"🔍 User ID найден в FORM.{field}: {user_id}")
                        return user_id
                        
        except Exception as e:
            logger.warning(f"⚠️ Ошибка парсинга User ID из POST: {e}")
        return None
    
    def _get_user_id_from_get(self) -> Optional[int]:
        """Получение User ID из GET параметров"""
        params_to_check = ['telegram_id', 'user_id', 'id']
        
        for param in params_to_check:
            value = request.args.get(param)
            if value:
                try:
                    user_id = int(value)
                    logger.debug(f"🔍 User ID найден в GET.{param}: {user_id}")
                    return user_id
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный формат User ID в GET.{param}: {value}")
        return None
    
    def _get_user_id_from_session(self) -> Optional[int]:
        """Получение User ID из сессии"""
        session_keys = ['telegram_id', 'user_id', 'id']
        
        for key in session_keys:
            value = session.get(key)
            if value:
                try:
                    user_id = int(value)
                    logger.debug(f"🔍 User ID найден в сессии.{key}: {user_id}")
                    return user_id
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Неверный формат User ID в сессии.{key}: {value}")
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

    def get_user_db_id(self) -> Optional[int]:
        """Получение ID пользователя в базе данных"""
        telegram_id = self.get_current_user_id()
        if not telegram_id:
            return None
            
        try:
            # Ленивый импорт для избежания циклических зависимостей
            from app.models.database import execute_db_query
            
            user = execute_db_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )
            
            if user:
                return user['id']
            else:
                logger.warning(f"⚠️ Пользователь с telegram_id {telegram_id} не найден в БД")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения user_db_id: {e}")
            return None
    
    def ensure_user_exists(self, username: str = None, first_name: str = None) -> Optional[int]:
        """Создание пользователя в БД если не существует"""
        telegram_id = self.get_current_user_id()
        if not telegram_id:
            return None
            
        try:
            from app.models.database import execute_db_query
            from datetime import datetime
            
            # Проверяем существование
            user = execute_db_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )
            
            if not user:
                # Создаем нового пользователя
                user_id = execute_db_query(
                    '''INSERT INTO users (telegram_id, username, first_name, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (
                        telegram_id,
                        username or f'user_{telegram_id}',
                        first_name or 'Telegram User',
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                logger.info(f"✅ Создан новый пользователь: telegram_id={telegram_id}, db_id={user_id}")
                return user_id
            else:
                # Обновляем существующего
                if username or first_name:
                    execute_db_query(
                        '''UPDATE users SET username = COALESCE(?, username), 
                                           first_name = COALESCE(?, first_name),
                                           updated_at = ?
                           WHERE telegram_id = ?''',
                        (username, first_name, datetime.now().isoformat(), telegram_id)
                    )
                return user['id']
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания/обновления пользователя: {e}")
            return None
    
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
        if not AppConfig.DEBUG:
            return  # Не логируем в продакшене
            
        logger.debug("🔍 ОТЛАДКА АВТОРИЗАЦИИ:")
        logger.debug(f"   📍 Путь: {request.path}")
        logger.debug(f"   📋 Метод: {request.method}")
        logger.debug(f"   🌐 IP: {request.remote_addr}")
        
        # Проверяем заголовки
        auth_headers = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'X-User-Id': request.headers.get('X-User-Id'),
            'Authorization': request.headers.get('Authorization', '')[:20] + '...' if request.headers.get('Authorization') else None,
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent', '')[:50] + '...'
        }
        logger.debug(f"   📨 Заголовки: {auth_headers}")
        
        # Проверяем POST данные
        if request.method == 'POST':
            try:
                if request.is_json:
                    data = request.get_json() or {}
                    has_telegram_data = bool(
                        data.get('telegram_id') or 
                        data.get('user_id') or
                        data.get('user', {}).get('id') or 
                        data.get('initData')
                    )
                    logger.debug(f"   📤 Есть ID в POST JSON: {has_telegram_data}")
                elif request.form:
                    has_form_data = bool(
                        request.form.get('telegram_id') or
                        request.form.get('user_id')
                    )
                    logger.debug(f"   📤 Есть ID в POST form: {has_form_data}")
            except:
                logger.debug(f"   📤 Ошибка парсинга POST данных")
        
        # Проверяем GET параметры
        has_get_user_id = bool(request.args.get('telegram_id') or request.args.get('user_id'))
        logger.debug(f"   📥 Есть ID в GET: {has_get_user_id}")
        
        # Проверяем сессию
        has_session_user_id = bool(session.get('telegram_id') or session.get('user_id'))
        logger.debug(f"   🍪 Есть ID в сессии: {has_session_user_id}")

    def _get_current_timestamp(self) -> str:
        """Получение текущего времени в ISO формате"""
        from datetime import datetime
        return datetime.now().isoformat()

# Глобальный экземпляр - единая точка доступа
auth_service = AuthService()

# Функции для обратной совместимости
def get_current_user_id() -> Optional[int]:
    """Получение текущего telegram_id пользователя"""
    return auth_service.get_current_user_id()

def get_user_db_id() -> Optional[int]:
    """Получение ID пользователя в базе данных"""
    return auth_service.get_user_db_id()

def ensure_user_exists(username: str = None, first_name: str = None) -> Optional[int]:
    """Создание пользователя в БД если не существует"""
    return auth_service.ensure_user_exists(username, first_name)