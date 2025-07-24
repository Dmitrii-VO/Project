#!/usr/bin/env python3
"""
Автоматическая верификация каналов
Полная система проверки владельцев каналов через Telegram API
"""

import random
import string
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

from .telegram_api_client import TelegramAPIClient
from app.models.database import execute_db_query
from app.events.event_dispatcher import event_dispatcher
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

class ChannelVerifier:
    """Система верификации каналов"""
    
    def __init__(self):
        self.telegram_client = TelegramAPIClient()
        self.verification_timeout = timedelta(hours=24)
        self.max_verification_attempts = 3
    
    def start_verification(self, user_id: int, channel_username: str, 
                          channel_title: str = None) -> Dict[str, Any]:
        """Начало процесса верификации канала"""
        try:
            # Проверяем, не находится ли канал уже в процессе верификации
            existing_verification = execute_db_query(
                """SELECT * FROM channels 
                   WHERE username = ? AND verification_code IS NOT NULL 
                   AND verification_expires_at > ?""",
                (channel_username, datetime.now()),
                fetch_one=True
            )
            
            if existing_verification:
                return {
                    'success': False,
                    'error': 'Канал уже находится в процессе верификации',
                    'existing_code': existing_verification['verification_code']
                }
            
            # Получаем информацию о канале через Telegram API
            channel_info = self.telegram_client.get_channel_info(channel_username)
            
            if not channel_info['success']:
                return {
                    'success': False,
                    'error': channel_info['error']
                }
            
            # Проверяем, что пользователь является администратором канала
            admin_check = self.telegram_client.check_user_admin_status(
                channel_username, user_id
            )
            
            if not admin_check['success'] or not admin_check['is_admin']:
                return {
                    'success': False,
                    'error': 'Вы не являетесь администратором этого канала'
                }
            
            # Генерируем код верификации
            verification_code = self._generate_verification_code()
            
            # Сохраняем или обновляем канал в базе данных
            channel_id = self._save_channel_for_verification(
                user_id=user_id,
                username=channel_username,
                title=channel_info['data']['title'],
                description=channel_info['data'].get('description', ''),
                subscriber_count=channel_info['data'].get('member_count', 0),
                verification_code=verification_code
            )
            
            # Отправляем инструкции пользователю
            verification_instructions = self._get_verification_instructions(
                verification_code, channel_username
            )
            
            logger.info(f"✅ Начата верификация канала {channel_username} для пользователя {user_id}")
            
            return {
                'success': True,
                'channel_id': channel_id,
                'verification_code': verification_code,
                'instructions': verification_instructions,
                'expires_at': (datetime.now() + self.verification_timeout).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка начала верификации: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_verification(self, channel_id: int, user_id: int) -> Dict[str, Any]:
        """Проверка верификации канала"""
        try:
            # Получаем данные канала
            channel = execute_db_query(
                """SELECT * FROM channels 
                   WHERE id = ? AND owner_id = ? AND verification_code IS NOT NULL""",
                (channel_id, user_id),
                fetch_one=True
            )
            
            if not channel:
                return {'success': False, 'error': 'Канал не найден или не принадлежит вам'}
            
            # Проверяем, не истек ли срок верификации
            if datetime.fromisoformat(channel['verification_expires_at']) < datetime.now():
                return {
                    'success': False, 
                    'error': 'Срок верификации истек',
                    'expired': True
                }
            
            # Ищем пост с кодом верификации в канале
            verification_found = self.telegram_client.find_verification_post(
                channel['username'], 
                channel['verification_code']
            )
            
            if verification_found['success']:
                # Верификация прошла успешно
                self._complete_verification(channel_id)
                
                # Отправляем событие
                event_dispatcher.channel_verified(
                    channel_id=channel_id,
                    owner_id=user_id,
                    title=channel['title']
                )
                
                logger.info(f"✅ Канал {channel['username']} успешно верифицирован")
                
                return {
                    'success': True,
                    'verified': True,
                    'message': 'Канал успешно верифицирован!',
                    'post_url': verification_found.get('post_url')
                }
            else:
                return {
                    'success': True,
                    'verified': False,
                    'message': 'Пост с кодом верификации не найден',
                    'remaining_time': self._get_remaining_verification_time(channel)
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки верификации: {e}")
            return {'success': False, 'error': str(e)}
    
    def auto_verify_channels(self) -> Dict[str, Any]:
        """Автоматическая проверка всех каналов в процессе верификации"""
        try:
            # Получаем все каналы, ожидающие верификации
            pending_channels = execute_db_query(
                """SELECT * FROM channels 
                   WHERE verification_code IS NOT NULL 
                   AND verification_expires_at > ? 
                   AND is_verified = 0""",
                (datetime.now(),)
            )
            
            verified_count = 0
            expired_count = 0
            errors = []
            
            for channel in pending_channels:
                try:
                    # Проверяем наличие поста с кодом
                    verification_found = self.telegram_client.find_verification_post(
                        channel['username'], 
                        channel['verification_code']
                    )
                    
                    if verification_found['success']:
                        # Завершаем верификацию
                        self._complete_verification(channel['id'])
                        
                        # Отправляем событие
                        event_dispatcher.channel_verified(
                            channel_id=channel['id'],
                            owner_id=channel['owner_id'],
                            title=channel['title']
                        )
                        
                        verified_count += 1
                        logger.info(f"✅ Автоверификация: канал {channel['username']} верифицирован")
                        
                except Exception as e:
                    errors.append(f"Канал {channel['username']}: {str(e)}")
                    logger.error(f"❌ Ошибка автоверификации канала {channel['username']}: {e}")
            
            # Очищаем истекшие верификации
            expired_result = execute_db_query(
                """UPDATE channels 
                   SET verification_code = NULL, verification_expires_at = NULL, updated_at = ?
                   WHERE verification_expires_at <= ? AND is_verified = 0""",
                (datetime.now(), datetime.now())
            )
            
            expired_count = expired_result if isinstance(expired_result, int) else 0
            
            logger.info(f"📊 Автоверификация: {verified_count} верифицировано, {expired_count} истекло")
            
            return {
                'success': True,
                'verified_count': verified_count,
                'expired_count': expired_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоверификации: {e}")
            return {'success': False, 'error': str(e)}
    
    def revoke_verification(self, channel_id: int, admin_user_id: int, reason: str) -> Dict[str, Any]:
        """Отзыв верификации канала (для админов)"""
        try:
            # Получаем данные канала
            channel = execute_db_query(
                "SELECT * FROM channels WHERE id = ?",
                (channel_id,),
                fetch_one=True
            )
            
            if not channel:
                return {'success': False, 'error': 'Канал не найден'}
            
            # Отзываем верификацию
            execute_db_query(
                """UPDATE channels 
                   SET is_verified = 0, verification_revoked_at = ?, 
                       verification_revoked_by = ?, verification_revoke_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (datetime.now(), admin_user_id, reason, datetime.now(), channel_id)
            )
            
            # Отправляем событие
            event_dispatcher.channel_deactivated(
                channel_id=channel_id,
                owner_id=channel['owner_id'],
                title=channel['title'],
                reason=reason
            )
            
            logger.info(f"⚠️ Верификация канала {channel['username']} отозвана администратором {admin_user_id}")
            
            return {
                'success': True,
                'message': 'Верификация канала отозвана'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка отзыва верификации: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_verification_status(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение статуса верификации каналов пользователя"""
        try:
            channels = execute_db_query(
                """SELECT id, username, title, is_verified, verification_code,
                          verification_expires_at, created_at
                   FROM channels 
                   WHERE owner_id = ? 
                   ORDER BY created_at DESC""",
                (user_id,)
            )
            
            result = []
            for channel in channels:
                status_info = {
                    'channel_id': channel['id'],
                    'username': channel['username'],
                    'title': channel['title'],
                    'is_verified': bool(channel['is_verified']),
                    'created_at': channel['created_at']
                }
                
                if channel['verification_code'] and not channel['is_verified']:
                    # В процессе верификации
                    expires_at = datetime.fromisoformat(channel['verification_expires_at'])
                    if expires_at > datetime.now():
                        status_info.update({
                            'status': 'pending_verification',
                            'verification_code': channel['verification_code'],
                            'expires_at': channel['verification_expires_at'],
                            'remaining_hours': self._get_remaining_hours(expires_at)
                        })
                    else:
                        status_info['status'] = 'verification_expired'
                elif channel['is_verified']:
                    status_info['status'] = 'verified'
                else:
                    status_info['status'] = 'not_started'
                
                result.append(status_info)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса верификации: {e}")
            return []
    
    def _generate_verification_code(self) -> str:
        """Генерация уникального кода верификации"""
        return ''.join(random.choices(
            string.ascii_uppercase + string.digits, 
            k=AppConfig.VERIFICATION_CODE_LENGTH
        ))
    
    def _save_channel_for_verification(self, user_id: int, username: str, title: str, 
                                     description: str, subscriber_count: int, 
                                     verification_code: str) -> int:
        """Сохранение канала для верификации"""
        # Проверяем, существует ли канал
        existing_channel = execute_db_query(
            "SELECT id FROM channels WHERE username = ?",
            (username,),
            fetch_one=True
        )
        
        expires_at = datetime.now() + self.verification_timeout
        
        if existing_channel:
            # Обновляем существующий канал
            execute_db_query(
                """UPDATE channels 
                   SET owner_id = ?, title = ?, description = ?, subscriber_count = ?,
                       verification_code = ?, verification_expires_at = ?, updated_at = ?
                   WHERE id = ?""",
                (user_id, title, description, subscriber_count, 
                 verification_code, expires_at, datetime.now(), existing_channel['id'])
            )
            return existing_channel['id']
        else:
            # Создаем новый канал
            return execute_db_query(
                """INSERT INTO channels 
                   (owner_id, username, title, description, subscriber_count,
                    verification_code, verification_expires_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, title, description, subscriber_count,
                 verification_code, expires_at, datetime.now(), datetime.now())
            )
    
    def _complete_verification(self, channel_id: int):
        """Завершение верификации канала"""
        execute_db_query(
            """UPDATE channels 
               SET is_verified = 1, verification_code = NULL, verification_expires_at = NULL,
                   verified_at = ?, updated_at = ?
               WHERE id = ?""",
            (datetime.now(), datetime.now(), channel_id)
        )
    
    def _get_verification_instructions(self, verification_code: str, channel_username: str) -> str:
        """Получение инструкций по верификации"""
        return f"""
🔐 **Инструкции по верификации канала @{channel_username}**

Для подтверждения владения каналом выполните следующие шаги:

1️⃣ Перейдите в ваш канал @{channel_username}
2️⃣ Опубликуйте пост с кодом верификации: **{verification_code}**
3️⃣ Вернитесь в веб-приложение и нажмите "Проверить верификацию"

⏰ **Важно:** Код действителен в течение 24 часов

📝 **Пример поста:**
```
Код верификации для Telegram Mini App: {verification_code}
```

После публикации поста верификация будет завершена автоматически.
        """
    
    def _get_remaining_verification_time(self, channel: Dict[str, Any]) -> str:
        """Получение оставшегося времени верификации"""
        expires_at = datetime.fromisoformat(channel['verification_expires_at'])
        remaining = expires_at - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return "Истекло"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        return f"{hours}ч {minutes}м"
    
    def _get_remaining_hours(self, expires_at: datetime) -> int:
        """Получение оставшихся часов до истечения"""
        remaining = expires_at - datetime.now()
        return max(0, int(remaining.total_seconds() // 3600))