# === ЕДИНЫЙ СЕРВИС ВЕРИФИКАЦИИ КАНАЛОВ ===
# Создайте новый файл: app/services/telegram_verification.py

import os
import requests
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class TelegramVerificationService:
    """
    Единый сервис для верификации каналов Telegram
    Вся логика проверки кода верификации находится только здесь!
    """

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get('BOT_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.timeout = 10

        if not self.bot_token:
            logger.warning("⚠️ BOT_TOKEN не настроен - верификация будет работать в тестовом режиме")

    def verify_channel_ownership(self, channel_id: str, verification_code: str) -> Dict[str, Any]:
        """
        ЕДИНСТВЕННОЕ МЕСТО проверки кода верификации!

        Args:
            channel_id: ID или username канала (@channel или -1001234567890)
            verification_code: Код для поиска (например: VERIFY_ABC12345)

        Returns:
            Dict с результатом верификации:
            {
                'success': bool,
                'found': bool,
                'message': str,
                'details': dict
            }
        """

        try:
            logger.info(f"🔍 Верификация канала {channel_id} с кодом {verification_code}")

            # Если нет токена - тестовый режим
            if not self.bot_token:
                return self._test_mode_verification(channel_id, verification_code)

            # Получаем сообщения из канала
            messages_result = self._get_channel_messages()

            if not messages_result['success']:
                return {
                    'success': False,
                    'found': False,
                    'message': f'Ошибка получения сообщений: {messages_result["error"]}',
                    'details': {'error_type': 'api_error'}
                }

            # Ищем код в сообщениях
            search_result = self._search_verification_code(
                messages_result['messages'],
                channel_id,
                verification_code
            )

            if search_result['found']:
                logger.info(f"✅ Код {verification_code} найден в канале {channel_id}")
                return {
                    'success': True,
                    'found': True,
                    'message': f'Код верификации найден в канале',
                    'details': {
                        'message_id': search_result['message_id'],
                        'message_text': search_result['message_text'][:100] + '...',
                        'found_at': datetime.now().isoformat()
                    }
                }
            else:
                logger.warning(f"❌ Код {verification_code} НЕ найден в канале {channel_id}")
                return {
                    'success': True,
                    'found': False,
                    'message': f'Код верификации не найден в канале',
                    'details': {
                        'messages_checked': search_result['messages_checked'],
                        'last_check': datetime.now().isoformat()
                    }
                }

        except Exception as e:
            logger.error(f"❌ Критическая ошибка верификации: {e}")
            return {
                'success': False,
                'found': False,
                'message': f'Критическая ошибка: {str(e)}',
                'details': {'exception': str(e)}
            }

    def _get_channel_messages(self, limit: int = 100) -> Dict[str, Any]:
        """Получение сообщений через Telegram Bot API"""
        try:
            # Для каналов нужно использовать getUpdates с offset
            url = f"{self.base_url}/getUpdates"
            params = {
                'limit': limit,
                'timeout': 0,  # Не ждем новых сообщений
                'allowed_updates': ['channel_post']  # Только посты из каналов
            }

            response = requests.get(url, params=params, timeout=self.timeout + 5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    updates = data.get('result', [])
                    logger.info(f"📥 Получено {len(updates)} обновлений от Telegram API")
                    return {
                        'success': True,
                        'messages': updates,
                        'count': len(updates)
                    }

            logger.error(f"❌ Ошибка Telegram API: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'HTTP {response.status_code}: {response.text}',
                'messages': []
            }

        except requests.RequestException as e:
            logger.error(f"❌ Сетевая ошибка при запросе к Telegram API: {e}")
            return {
                'success': False,
                'error': f'Сетевая ошибка: {str(e)}',
                'messages': []
            }

    def _search_verification_code(self, updates: List[Dict], channel_id: str, verification_code: str) -> Dict[str, Any]:
        """
        ГЛАВНАЯ ФУНКЦИЯ ПОИСКА КОДА!
        Здесь происходит вся магия проверки
        """

        messages_checked = 0

        for update in updates:
            # Проверяем сообщения в каналах (channel_post)
            if 'channel_post' in update:
                message = update['channel_post']
                chat = message.get('chat', {})
                text = message.get('text', '')

                messages_checked += 1

                # Проверяем, что это нужный канал
                if self._is_target_channel(chat, channel_id):
                    # ВОТ ОНА - ГЛАВНАЯ ПРОВЕРКА! 🎯
                    if verification_code in text:
                        return {
                            'found': True,
                            'message_id': message.get('message_id'),
                            'message_text': text,
                            'chat_id': chat.get('id'),
                            'chat_username': chat.get('username')
                        }

                    logger.debug(f"📝 Проверено сообщение {message.get('message_id')}: код не найден")

            # Проверяем обычные сообщения (для групп)
            elif 'message' in update:
                message = update['message']
                chat = message.get('chat', {})
                text = message.get('text', '')

                messages_checked += 1

                if self._is_target_channel(chat, channel_id):
                    # ВОТ ОНА - ВТОРАЯ ПРОВЕРКА! 🎯
                    if verification_code in text:
                        return {
                            'found': True,
                            'message_id': message.get('message_id'),
                            'message_text': text,
                            'chat_id': chat.get('id'),
                            'chat_username': chat.get('username')
                        }

        return {
            'found': False,
            'messages_checked': messages_checked
        }

    def _is_target_channel(self, chat: Dict, target_channel_id: str) -> bool:
        """Проверка, что это нужный канал"""

        chat_id = str(chat.get('id', ''))
        chat_username = chat.get('username', '').lower()

        # Нормализуем target_channel_id
        target_id = str(target_channel_id).replace('@', '').lower()

        # Проверяем по ID
        if chat_id == target_id:
            return True

        # Проверяем по username
        if chat_username and chat_username == target_id:
            return True

        return False

    def _test_mode_verification(self, channel_id: str, verification_code: str) -> Dict[str, Any]:
        """Тестовый режим для отладки без реального API"""

        import random

        logger.info(f"🧪 ТЕСТОВЫЙ РЕЖИМ: верификация {channel_id} с кодом {verification_code}")

        # Симулируем 80% успеха
        success = random.random() < 0.8

        if success:
            return {
                'success': True,
                'found': True,
                'message': f'✅ [ТЕСТ] Код найден в канале {channel_id}',
                'details': {
                    'mode': 'test',
                    'simulated': True,
                    'message_text': f'Тестовое сообщение с кодом {verification_code}'
                }
            }
        else:
            return {
                'success': True,
                'found': False,
                'message': f'❌ [ТЕСТ] Код не найден в канале {channel_id}',
                'details': {
                    'mode': 'test',
                    'simulated': True,
                    'suggestion': f'Опубликуйте код {verification_code} в канале'
                }
            }

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о канале"""

        if not self.bot_token:
            return None

        try:
            url = f"{self.base_url}/getChat"
            params = {'chat_id': channel_id}

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', {})

            return None

        except Exception as e:
            logger.error(f"Ошибка получения информации о канале: {e}")
            return None


# === ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ===
# Создаем единственный экземпляр сервиса
verification_service = TelegramVerificationService()


# === ПРОСТАЯ ФУНКЦИЯ ДЛЯ ИСПОЛЬЗОВАНИЯ ===
def verify_channel(channel_id: str, verification_code: str) -> Dict[str, Any]:
    """
    Простая функция для верификации канала
    Использует единый сервис внутри
    """
    return verification_service.verify_channel_ownership(channel_id, verification_code)


# === ЭКСПОРТ ===
__all__ = [
    'TelegramVerificationService',
    'verification_service',
    'verify_channel'
]