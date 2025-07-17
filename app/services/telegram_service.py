import asyncio
import logging
import requests
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class TelegramService:
    """Сервис интеграции с Telegram API"""

    def __init__(self, bot_token: str = None):
        from app.config.telegram_config import AppConfig
        self.bot_token = bot_token or AppConfig.BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def search_channel(self, username: str, user_id: int) -> Dict[str, Any]:
        """Поиск канала через Telegram API"""
        try:
            # Заглушка для Telegram API
            # В реальности здесь должен быть HTTP запрос к Telegram API

            await asyncio.sleep(0.1)  # Имитация сетевого запроса

            return {
                'success': True,
                'channel': {
                    'id': f'fake_channel_id_{username}',
                    'username': username,
                    'title': f'Канал @{username}',
                    'description': f'Описание канала @{username}',
                    'subscribers_count': 1000,
                    'verified': False
                },
                'user_permissions': {
                    'is_admin': True,
                    'can_post': True
                }
            }

        except Exception as e:
            logger.error(f"Error searching channel {username}: {e}")
            return {
                'success': False,
                'error': f'Ошибка поиска канала: {str(e)}'
            }

    async def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML') -> Dict[str, Any]:
        """Отправка сообщения в Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Сообщение отправлено пользователю {chat_id}")
                    return {
                        'success': True,
                        'message_id': result.get('result', {}).get('message_id')
                    }
                else:
                    logger.error(f"❌ Ошибка Telegram API: {result.get('description')}")
                    return {
                        'success': False,
                        'error': result.get('description', 'Unknown error')
                    }
            else:
                logger.error(f"❌ HTTP ошибка: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Тест подключения к Telegram API"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    bot_info = result.get('result', {})
                    logger.info(f"✅ Telegram API доступен. Бот: {bot_info.get('username')}")
                    return {
                        'success': True,
                        'message': 'Telegram API доступен',
                        'bot_info': bot_info
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('description', 'Unknown error')
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }

        except Exception as e:
            logger.error(f"Telegram API test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def create_telegram_service(bot_token: str) -> Optional[TelegramService]:
    """Создание сервиса Telegram"""
    if not bot_token:
        logger.error("Bot token not provided")
        return None

    return TelegramService(bot_token)


def run_async_in_sync(coro):
    """Запуск асинхронной функции в синхронном контексте"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)