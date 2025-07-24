#!/usr/bin/env python3
"""
Telegram API Client для верификации каналов
Работа с Telegram Bot API для проверки каналов и постов
"""

import re
import logging
import requests
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.config.telegram_config import AppConfig, TELEGRAM_API_TIMEOUT, TELEGRAM_API_RATE_LIMIT

logger = logging.getLogger(__name__)

class TelegramAPIClient:
    """Клиент для работы с Telegram Bot API"""
    
    def __init__(self):
        self.bot_token = AppConfig.BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.request_timeout = TELEGRAM_API_TIMEOUT
        
        # Лимиты API
        self.api_rate_limit = TELEGRAM_API_RATE_LIMIT  # requests per second
        self.last_request_time = 0
    
    def get_channel_info(self, channel_username: str) -> Dict[str, Any]:
        """Получение информации о канале"""
        try:
            # Убираем @ если есть
            username = channel_username.lstrip('@')
            
            # Получаем информацию о чате
            response = self._make_api_request('getChat', {
                'chat_id': f'@{username}'
            })
            
            if not response['success']:
                return response
            
            chat_data = response['data']
            
            # Получаем количество участников
            members_response = self._make_api_request('getChatMemberCount', {
                'chat_id': f'@{username}'
            })
            
            member_count = 0
            if members_response['success']:
                member_count = members_response['data']
            
            return {
                'success': True,
                'data': {
                    'id': chat_data['id'],
                    'title': chat_data['title'],
                    'username': chat_data.get('username'),
                    'description': chat_data.get('description', ''),
                    'member_count': member_count,
                    'type': chat_data['type'],
                    'invite_link': chat_data.get('invite_link')
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о канале {channel_username}: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_user_admin_status(self, channel_username: str, user_id: int) -> Dict[str, Any]:
        """Проверка статуса администратора пользователя в канале"""
        try:
            username = channel_username.lstrip('@')
            
            # Получаем информацию о пользователе в чате
            response = self._make_api_request('getChatMember', {
                'chat_id': f'@{username}',
                'user_id': user_id
            })
            
            if not response['success']:
                return response
            
            member_data = response['data']
            status = member_data['status']
            
            # Проверяем, является ли пользователь админом или создателем
            is_admin = status in ['creator', 'administrator']
            
            # Для администраторов проверяем права
            can_post = False
            if is_admin:
                if status == 'creator':
                    can_post = True
                elif status == 'administrator':
                    can_post = member_data.get('can_post_messages', False)
            
            return {
                'success': True,
                'is_admin': is_admin,
                'status': status,
                'can_post': can_post,
                'data': member_data
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прав администратора: {e}")
            return {'success': False, 'error': str(e)}
    
    def find_verification_post(self, channel_username: str, verification_code: str) -> Dict[str, Any]:
        """Поиск поста с кодом верификации в канале"""
        try:
            username = channel_username.lstrip('@')
            
            # Получаем последние сообщения из канала
            # Используем метод getUpdates для получения сообщений
            # В реальном API это может быть сложнее, тут упрощенная версия
            
            # Альтернативный подход - проверяем через поиск в канале
            # Для демонстрации используем упрощенную логику
            
            # В реальности здесь должен быть код для поиска постов
            # через Telegram API или веб-скрапинг
            
            # Имитируем поиск
            found = self._search_verification_code_in_channel(username, verification_code)
            
            if found:
                return {
                    'success': True,
                    'found': True,
                    'post_url': f'https://t.me/{username}/{found["message_id"]}',
                    'message_id': found['message_id'],
                    'post_date': found.get('date')
                }
            else:
                return {
                    'success': True,
                    'found': False,
                    'message': 'Пост с кодом верификации не найден'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска поста верификации: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_channel_statistics(self, channel_username: str) -> Dict[str, Any]:
        """Получение расширенной статистики канала"""
        try:
            username = channel_username.lstrip('@')
            
            # Основная информация о канале
            channel_info = self.get_channel_info(username)
            if not channel_info['success']:
                return channel_info
            
            # Дополнительная статистика (в реальности через Telegram API)
            # Здесь используем доступные методы Bot API
            
            stats = {
                'member_count': channel_info['data']['member_count'],
                'title': channel_info['data']['title'],
                'description': channel_info['data']['description'],
                'username': channel_info['data']['username'],
                'last_updated': datetime.now().isoformat()
            }
            
            # Попытка получить дополнительную информацию
            try:
                # Получаем последние сообщения для анализа активности
                recent_activity = self._analyze_channel_activity(username)
                stats.update(recent_activity)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить расширенную статистику: {e}")
            
            return {
                'success': True,
                'data': stats
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики канала: {e}")
            return {'success': False, 'error': str(e)}
    
    def validate_channel_ownership(self, channel_username: str, user_id: int, 
                                 verification_method: str = 'post') -> Dict[str, Any]:
        """Валидация владения каналом различными методами"""
        try:
            # Проверяем права администратора
            admin_check = self.check_user_admin_status(channel_username, user_id)
            if not admin_check['success']:
                return admin_check
            
            if not admin_check['is_admin']:
                return {
                    'success': False,
                    'error': 'Пользователь не является администратором канала'
                }
            
            # Дополнительные проверки в зависимости от метода
            if verification_method == 'post':
                if not admin_check.get('can_post', True):
                    return {
                        'success': False,
                        'error': 'У пользователя нет прав на публикацию сообщений'
                    }
            
            return {
                'success': True,
                'validated': True,
                'admin_status': admin_check['status'],
                'can_post': admin_check.get('can_post', True)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации владения каналом: {e}")
            return {'success': False, 'error': str(e)}
    
    def _make_api_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение запроса к Telegram Bot API с rate limiting"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.api_rate_limit
            
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
            
            self.last_request_time = time.time()
            
            # Выполняем запрос
            url = f"{self.base_url}/{method}"
            response = requests.post(
                url,
                json=params,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return {
                        'success': True,
                        'data': data['result']
                    }
                else:
                    error_msg = data.get('description', 'Unknown API error')
                    logger.error(f"❌ Telegram API error: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_code': data.get('error_code')
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка запроса к Telegram API: {e}")
            return {'success': False, 'error': f'Network error: {str(e)}'}
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка API: {e}")
            return {'success': False, 'error': str(e)}
    
    def _search_verification_code_in_channel(self, username: str, verification_code: str) -> Optional[Dict[str, Any]]:
        """Поиск кода верификации в канале (упрощенная версия)"""
        try:
            # В реальной реализации здесь должен быть код для:
            # 1. Получения последних сообщений из канала
            # 2. Поиска в них кода верификации
            # 3. Возврата информации о найденном сообщении
            
            # Для демонстрации возвращаем имитацию поиска
            # В продакшене нужно использовать Telegram API или веб-скрапинг
            
            # Имитируем успешный поиск с некоторой вероятностью
            import random
            if random.random() > 0.3:  # 70% вероятность найти код
                return {
                    'message_id': random.randint(1, 1000),
                    'date': datetime.now(),
                    'text': f'Код верификации для Telegram Mini App: {verification_code}',
                    'found': True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска кода верификации: {e}")
            return None
    
    def _analyze_channel_activity(self, username: str) -> Dict[str, Any]:
        """Анализ активности канала"""
        try:
            # В реальной реализации здесь должен быть анализ:
            # - Частоты постов
            # - Времени последнего поста
            # - Среднего количества просмотров
            # - Вовлеченности аудитории
            
            # Для демонстрации возвращаем базовые метрики
            return {
                'estimated_reach': 'Unknown',  # Охват постов
                'post_frequency': 'Unknown',   # Частота публикаций
                'last_post_date': 'Unknown',   # Дата последнего поста
                'engagement_rate': 'Unknown'   # Уровень вовлеченности
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа активности канала: {e}")
            return {}