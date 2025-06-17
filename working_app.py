#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
Рефакторированная версия с улучшенной архитектурой и производительностью
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import requests

# Добавляем пути для импорта модулей
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(PROJECT_ROOT, 'app')

for path in [PROJECT_ROOT, APP_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем системные переменные")

# Flask импорты
from flask import Flask, jsonify, request, render_template


# === КОНФИГУРАЦИЯ ===
class AppConfig:
    """Централизованная конфигурация приложения"""

    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

    # База данных
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
    DATABASE_PATH = os.path.join(PROJECT_ROOT, 'telegram_mini_app.db')

    # Telegram
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8')
    TELEGRAM_PAYMENT_TOKEN = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
    YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))

    # Веб-хуки и безопасность
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret')
    WEBAPP_URL = os.environ.get('WEBAPP_URL', 'http://localhost:5000')

    # Функциональность
    FEATURES = {
        'telegram_integration': os.environ.get('TELEGRAM_INTEGRATION', 'True').lower() == 'true',
        'offers_system': os.environ.get('OFFERS_SYSTEM_ENABLED', 'True').lower() == 'true',
        'payments_system': os.environ.get('PAYMENTS_SYSTEM_ENABLED', 'True').lower() == 'true',
        'analytics_system': os.environ.get('ANALYTICS_SYSTEM_ENABLED', 'True').lower() == 'true',
    }

    # Настройки производительности
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = DEBUG

    @classmethod
    def validate(cls) -> bool:
        """Валидация критических настроек"""
        errors = []

        if not cls.BOT_TOKEN or cls.BOT_TOKEN == 'your-bot-token':
            errors.append("BOT_TOKEN не настроен")

        if not os.path.exists(cls.DATABASE_PATH):
            errors.append(f"База данных не найдена: {cls.DATABASE_PATH}")

        if errors:
            for error in errors:
                print(f"❌ {error}")
            return False

        return True


# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
def setup_logging() -> logging.Logger:
    """Настройка системы логирования"""
    logging.basicConfig(
        level=logging.INFO if not AppConfig.DEBUG else logging.DEBUG,
        format='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger('TelegramApp')
    logger.info("📋 Система логирования инициализирована")
    return logger


# === НАСТРОЙКА TELEGRAM WEBHOOK ===
def setup_telegram_webhook():
    """Настройка webhook для Telegram бота"""
    import requests

    bot_token = AppConfig.BOT_TOKEN
    webhook_url = f"{AppConfig.WEBAPP_URL}/api/channels/webhook"

    try:
        # Устанавливаем webhook
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        response = requests.post(url, json={
            'url': webhook_url,
            'allowed_updates': ['channel_post', 'message']
        })

        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Webhook установлен: {webhook_url}")
            else:
                logger.error(f"❌ Ошибка установки webhook: {result.get('description')}")
        else:
            logger.error(f"❌ HTTP ошибка: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Ошибка настройки webhook: {e}")

# === СОЗДАНИЕ ПРИЛОЖЕНИЯ ===
def create_app() -> Flask:
    """Фабрика приложений с улучшенной архитектурой"""

    app = Flask(__name__)
    app.config.from_object(AppConfig)

    # Настройка JSON сериализации
    app.json.ensure_ascii = False
    app.json.sort_keys = AppConfig.JSON_SORT_KEYS

    # Инициализация компонентов
    init_database(app)
    register_blueprints(app)  # Включает main_router.py с основными страницами
    register_middleware(app)
    register_error_handlers(app)
    register_system_routes(app)  # Только служебные маршруты

    return app


# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ===
def init_database(app: Flask) -> None:
    """Инициализация базы данных"""
    try:
        # Проверяем существование БД
        if not os.path.exists(AppConfig.DATABASE_PATH):
            logger.warning("⚠️ База данных не найдена, создаем новую...")
            # Здесь можно добавить создание БД

        logger.info("✅ База данных инициализирована")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


# === РЕГИСТРАЦИЯ BLUEPRINTS ===
def register_blueprints(app: Flask) -> None:
    """Регистрация всех Blueprint'ов с использованием исправленной системы"""

    blueprints_registered = 0

    try:
        # Пробуем использовать app.routers, но БЕЗ проблемного channel_router
        print("📦 Регистрация Blueprint'ов...")

        # Ручная регистрация только работающих Blueprint'ов
        blueprint_modules = [
            ('app.routers.main_router', 'main_bp', ''),  # Основные страницы без префикса
            ('app.routers.api_router', 'api_bp', '/api'),
            #('app.routers.channel_router', 'channel_bp', '/api/channels'),
            ('app.routers.offer_router', 'offer_bp', '/api/offers'),
            ('app.routers.analytics_router', 'analytics_bp', '/api/analytics'),
            ('app.routers.payment_router', 'payment_bp', '/api/payments'),
        ]

        for module_name, blueprint_name, url_prefix in blueprint_modules:
            try:
                module = __import__(module_name, fromlist=[blueprint_name])
                blueprint = getattr(module, blueprint_name)
                app.register_blueprint(blueprint, url_prefix=url_prefix)
                blueprints_registered += 1
                prefix_display = url_prefix if url_prefix else "/"
                logger.debug(f"✅ Blueprint зарегистрирован: {blueprint_name} -> {prefix_display}")

            except (ImportError, AttributeError) as e:
                logger.warning(f"⚠️ Не удалось загрузить {module_name}: {e}")

        logger.info(f"📦 Зарегистрировано Blueprint'ов: {blueprints_registered}")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка регистрации Blueprint'ов: {e}")
        raise

    # Регистрируем исправленный channels_bp из app.api.channels
    try:
        from app.api.channels import channels_bp
        app.register_blueprint(channels_bp, url_prefix='/api/channels')
        logger.info("✅ channels_bp зарегистрирован на /api/channels")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации channels_bp: {e}")
        # Не поднимаем исключение, просто логируем ошибку


# === MIDDLEWARE ===
def register_middleware(app: Flask) -> None:
    """Регистрация middleware"""

    @app.before_request
    def security_middleware():
        """Базовая безопасность"""
        # Ограничение размера запроса
        if request.content_length and request.content_length > AppConfig.MAX_CONTENT_LENGTH:
            return jsonify({'error': 'Request too large'}), 413

        # Логирование API запросов
        if request.path.startswith('/api/'):
            logger.debug(f"API: {request.method} {request.path} from {request.remote_addr}")

    @app.after_request
    def security_headers(response):
        """Добавление заголовков безопасности"""
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        })
        return response

    logger.info("🛡️ Middleware безопасности зарегистрированы")


# === ОБРАБОТЧИКИ ОШИБОК ===
def register_error_handlers(app: Flask) -> None:
    """Регистрация обработчиков ошибок"""

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Endpoint not found',
                'path': request.path,
                'method': request.method
            }), 404
        return render_template('error.html', message='Страница не найдена'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', message='Внутренняя ошибка сервера'), 500

    @app.errorhandler(413)
    def request_too_large(error):
        return jsonify({'error': 'Request entity too large'}), 413

    logger.info("🚨 Обработчики ошибок зарегистрированы")


# === СЛУЖЕБНЫЕ МАРШРУТЫ ===
def register_system_routes(app: Flask) -> None:
    """Регистрация служебных системных маршрутов (не основных страниц)"""

    @app.route('/api/channels/<int:channel_id>/verify', methods=['PUT'])
    def verify_channel_endpoint(channel_id):
        """Endpoint для верификации каналов"""
        from flask import jsonify, request

        try:
            logger.info(f"🔍 Верификация канала {channel_id}")

            # Получаем данные пользователя из заголовков
            telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')
            telegram_username = request.headers.get('X-Telegram-Username', 'unknown')

            logger.info(f"👤 Пользователь: {telegram_username} ({telegram_user_id})")

            # Имитируем успешную верификацию
            result = {
                'success': True,
                'message': f'✅ Канал {channel_id} успешно верифицирован!',
                'channel': {
                    'id': channel_id,
                    'channel_name': f'Channel {channel_id}',
                    'is_verified': True,
                    'verified_by': telegram_username,
                    'verified_at': datetime.utcnow().isoformat()
                }
            }

            logger.info(f"✅ Канал {channel_id} верифицирован")
            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ Ошибка верификации канала {channel_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

    # Дополнительные endpoints для каналов
    @app.route('/api/channels', methods=['GET'])
    def get_channels_endpoint():
        """Получить список каналов"""
        from flask import jsonify, request

        try:
            telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')
            logger.info(f"📋 Запрос каналов от {telegram_user_id}")

            # Возвращаем тестовые данные
            channels = [
                {
                    'id': 10,
                    'title': 'Мой канал',
                    'username': 'my_channel',
                    'subscriber_count': 1200,
                    'is_verified': False,
                    'category': 'technology',
                    'status': 'pending'
                }
            ]

            return jsonify({
                'success': True,
                'channels': channels
            })

        except Exception as e:
            logger.error(f"❌ Ошибка получения каналов: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

    @app.route('/api/channels', methods=['POST'])
    def create_channel_endpoint():
        """Создать новый канал"""
        from flask import jsonify, request
        import random
        import string

        try:
            data = request.get_json() or {}
            telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')

            # Генерируем код верификации
            verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            channel = {
                'id': random.randint(100, 999),
                'title': data.get('title', 'Новый канал'),
                'username': data.get('channel_url', '').replace('@', '').replace('https://t.me/', ''),
                'subscriber_count': data.get('subscriber_count', 0),
                'is_verified': False,
                'verification_code': verification_code,
                'status': 'pending'
            }

            logger.info(f"📺 Создан канал {channel['id']} для {telegram_user_id}")

            return jsonify({
                'success': True,
                'message': 'Канал добавлен успешно',
                'channel': channel,
                'verification_code': verification_code
            }), 201

        except Exception as e:
            logger.error(f"❌ Ошибка создания канала: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

    logger.info("🔧 Endpoints для каналов добавлены")


# === СТАТИСТИКА И МОНИТОРИНГ ===
class AppStats:
    """Класс для сбора статистики приложения"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0

    def increment_requests(self):
        self.request_count += 1

    def increment_errors(self):
        self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        uptime = datetime.utcnow() - self.start_time
        return {
            'uptime_seconds': int(uptime.total_seconds()),
            'requests_total': self.request_count,
            'errors_total': self.error_count,
            'start_time': self.start_time.isoformat()
        }


# === TELEGRAM API СЕРВИС ===
class TelegramVerificationService:
    """Сервис для верификации каналов через Telegram Bot API"""

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def get_channel_messages(self, channel_id, limit=50):
        """Получить последние сообщения из канала"""
        try:
            # Используем getUpdates для получения сообщений
            url = f"{self.base_url}/getUpdates"
            params = {
                'limit': limit,
                'timeout': 10
            }

            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])

            logger.error(f"Ошибка получения сообщений: {response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Исключение при получении сообщений: {e}")
            return []

    def check_verification_code_in_channel(self, channel_id, verification_code):
        """Проверить наличие кода верификации в канале"""
        try:
            logger.info(f"🔍 Проверка кода {verification_code} в канале {channel_id}")

            # Получаем последние обновления
            updates = self.get_channel_messages(channel_id)

            # Ищем код в сообщениях канала
            for update in updates:
                # Проверяем channel_post (сообщения в каналах)
                if 'channel_post' in update:
                    message = update['channel_post']
                    chat = message.get('chat', {})
                    text = message.get('text', '')

                    # Проверяем ID канала
                    if str(chat.get('id')) == str(channel_id) or str(chat.get('username', '')).lower() == str(
                            channel_id).lower().replace('@', ''):
                        if verification_code in text:
                            logger.info(f"✅ Код {verification_code} найден в канале {channel_id}")
                            return True

                # Также проверяем обычные сообщения (для групп)
                if 'message' in update:
                    message = update['message']
                    chat = message.get('chat', {})
                    text = message.get('text', '')

                    if str(chat.get('id')) == str(channel_id):
                        if verification_code in text:
                            logger.info(f"✅ Код {verification_code} найден в чате {channel_id}")
                            return True

            logger.warning(f"❌ Код {verification_code} НЕ найден в канале {channel_id}")
            return False

        except Exception as e:
            logger.error(f"Ошибка проверки кода: {e}")
            return False

    def get_channel_info(self, channel_id):
        """Получить информацию о канале"""
        try:
            url = f"{self.base_url}/getChat"
            params = {'chat_id': channel_id}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', {})

            return None

        except Exception as e:
            logger.error(f"Ошибка получения информации о канале: {e}")
            return None


# === БАЗА ДАННЫХ ДЛЯ КАНАЛОВ ===
class ChannelDatabase:
    """Простая база данных для каналов (в памяти)"""

    def __init__(self):
        self.channels = {}  # {channel_id: channel_data}
        self.next_id = 1

    def create_channel(self, user_id, channel_data):
        """Создать новый канал"""
        import random
        import string

        # Генерируем уникальный код верификации
        verification_code = 'VERIFY_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        channel = {
            'id': self.next_id,
            'user_id': user_id,
            'title': channel_data.get('title', 'Новый канал'),
            'username': channel_data.get('username', ''),
            'telegram_id': channel_data.get('telegram_id', ''),
            'category': channel_data.get('category', 'other'),
            'subscriber_count': channel_data.get('subscriber_count', 0),
            'verification_code': verification_code,
            'is_verified': False,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'verified_at': None
        }

        self.channels[self.next_id] = channel
        self.next_id += 1

        return channel

    def get_channel(self, channel_id):
        """Получить канал по ID"""
        return self.channels.get(channel_id)

    def update_channel(self, channel_id, updates):
        """Обновить канал"""
        if channel_id in self.channels:
            self.channels[channel_id].update(updates)
            return self.channels[channel_id]
        return None

    def get_user_channels(self, user_id):
        """Получить каналы пользователя"""
        return [channel for channel in self.channels.values() if channel['user_id'] == user_id]




# === ИНИЦИАЛИЗАЦИЯ ===
logger = setup_logging()
app = create_app()
stats = AppStats()

# Регистрация служебных маршрутов (основные маршруты в app/routers/main_router.py)
#register_system_routes(app)

# Сохранение времени старта
app.start_time = stats.start_time.isoformat()

# === ГЛОБАЛЬНЫЕ ОБЪЕКТЫ ===
# Инициализируем сервисы
telegram_service = None
channel_db = ChannelDatabase()


def init_telegram_service():
    """Инициализация Telegram сервиса"""
    global telegram_service
    bot_token = os.environ.get('BOT_TOKEN')
    if bot_token:
        telegram_service = TelegramVerificationService(bot_token)
        logger.info("✅ Telegram сервис инициализирован")
    else:
        logger.warning("⚠️ BOT_TOKEN не найден")


# === ENDPOINT'Ы ДЛЯ КАНАЛОВ ===
@app.route('/api/channels/<int:channel_id>/verify', methods=['PUT'])
def verify_channel_real(channel_id):
    """Реальная верификация канала через проверку кода"""
    try:
        logger.info(f"🔍 Начинаем верификацию канала {channel_id}")

        # Получаем данные пользователя
        telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')
        telegram_username = request.headers.get('X-Telegram-Username', 'unknown')

        # Получаем канал из базы
        channel = channel_db.get_channel(channel_id)
        if not channel:
            return jsonify({
                'success': False,
                'error': 'Канал не найден'
            }), 404

        # Проверяем, что канал принадлежит пользователю
        if str(channel['user_id']) != str(telegram_user_id):
            return jsonify({
                'success': False,
                'error': 'Нет доступа к каналу'
            }), 403

        # Проверяем, не верифицирован ли уже
        if channel['is_verified']:
            return jsonify({
                'success': True,
                'message': 'Канал уже верифицирован',
                'channel': channel
            })

        # Проверяем наличие Telegram сервиса
        if not telegram_service:
            # Заглушка для тестирования без API
            logger.warning("⚠️ Telegram API недоступен, используем заглушку")
            # Обновляем статус канала
            updates = {
                'is_verified': True,
                'status': 'verified',
                'verified_at': datetime.now().isoformat()
            }
            updated_channel = channel_db.update_channel(channel_id, updates)

            return jsonify({
                'success': True,
                'message': f'✅ Канал "{channel["title"]}" успешно верифицирован!',
                'channel': updated_channel
            })

        # Реальная проверка через Telegram API
        verification_code = channel['verification_code']
        channel_telegram_id = channel.get('telegram_id') or channel.get('username')

        if not channel_telegram_id:
            return jsonify({
                'success': False,
                'error': 'Не указан ID или username канала'
            }), 400

        # Проверяем код в канале
        is_code_found = telegram_service.check_verification_code_in_channel(
            channel_telegram_id,
            verification_code
        )

        if is_code_found:
            # Код найден - верифицируем канал
            updates = {
                'is_verified': True,
                'status': 'verified',
                'verified_at': datetime.now().isoformat()
            }
            updated_channel = channel_db.update_channel(channel_id, updates)

            logger.info(f"✅ Канал {channel_id} успешно верифицирован")

            return jsonify({
                'success': True,
                'message': f'✅ Канал "{channel["title"]}" успешно верифицирован!',
                'channel': updated_channel
            })
        else:
            # Код не найден
            return jsonify({
                'success': False,
                'error': f'❌ Код верификации "{verification_code}" не найден в канале',
                'instructions': [
                    f'1. Откройте ваш канал @{channel.get("username", "your_channel")}',
                    f'2. Опубликуйте сообщение с кодом: {verification_code}',
                    f'3. Подождите несколько минут',
                    f'4. Нажмите кнопку "Верифицировать" снова'
                ],
                'verification_code': verification_code
            })

    except Exception as e:
        logger.error(f"❌ Ошибка верификации канала {channel_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels', methods=['GET'])
def get_channels_real():
    """Получить каналы пользователя"""
    try:
        telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')

        # Получаем каналы пользователя
        user_channels = channel_db.get_user_channels(telegram_user_id)

        return jsonify({
            'success': True,
            'channels': user_channels,
            'total': len(user_channels)
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения каналов: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels', methods=['POST'])
def create_channel_real():
    """Создать новый канал"""
    try:
        data = request.get_json() or {}
        telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')

        # Создаем канал
        channel = channel_db.create_channel(telegram_user_id, {
            'title': data.get('title', 'Новый канал'),
            'username': data.get('channel_url', '').replace('@', '').replace('https://t.me/', ''),
            'telegram_id': data.get('telegram_id', ''),
            'category': data.get('category', 'other'),
            'subscriber_count': data.get('subscriber_count', 0)
        })

        logger.info(f"📺 Создан канал {channel['id']} для пользователя {telegram_user_id}")

        return jsonify({
            'success': True,
            'message': 'Канал успешно добавлен',
            'channel': channel,
            'verification_instructions': [
                f'Для верификации канала выполните следующие шаги:',
                f'1. Перейдите в ваш канал @{channel["username"]}',
                f'2. Опубликуйте сообщение с кодом: {channel["verification_code"]}',
                f'3. Нажмите кнопку "Верифицировать" в интерфейсе'
            ]
        }), 201

    except Exception as e:
        logger.error(f"❌ Ошибка создания канала: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Инициализируем Telegram сервис при запуске
init_telegram_service()

logger.info("🔧 Система верификации каналов инициализирована")
# === ТОЧКА ВХОДА ===
def main():
    """Главная функция запуска"""

    # Валидация конфигурации
    if not AppConfig.validate():
        logger.error("❌ Критические ошибки конфигурации")
        sys.exit(1)

    setup_telegram_webhook()

    # Настройки запуска
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    logger.info("=" * 60)
    logger.info("🚀 TELEGRAM MINI APP v2.0")
    logger.info("=" * 60)
    logger.info(f"📱 BOT_TOKEN: {'✅ Настроен' if AppConfig.BOT_TOKEN else '❌ Отсутствует'}")
    logger.info(f"🗄️ База данных: {AppConfig.DATABASE_PATH}")
    logger.info(f"🌐 Запуск на: http://{host}:{port}")
    logger.info(f"🔧 Режим разработки: {AppConfig.DEBUG}")
    logger.info(f"⚙️ Функции: {sum(AppConfig.FEATURES.values())}/{len(AppConfig.FEATURES)} включены")
    logger.info("=" * 60)

    try:
        app.run(
            host=host,
            port=port,
            debug=AppConfig.DEBUG,
            threaded=True,
            use_reloader=AppConfig.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("🛑 Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()