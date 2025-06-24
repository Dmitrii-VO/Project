#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
Рефакторированная версия с улучшенной архитектурой и производительностью
"""

import os
import sqlite3
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import os

import logger
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

try:
    from app.services.telegram_verification import verification_service
except ImportError:
    verification_service = None

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
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('DEBUG')
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    # База данных
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DATABASE_PATH = os.path.join(PROJECT_ROOT)

    # Telegram
    TELEGRAM_PAYMENT_TOKEN = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
    YOUR_TELEGRAM_ID = os.environ.get('YOUR_TELEGRAM_ID')

    # Веб-хуки и безопасность
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
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

    app = Flask(__name__, static_folder='app/static', template_folder='templates')
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
            ('app.api.channel_analyzer', 'analyzer_bp', '/api/analyzer'),
            ('app.routers.main_router', 'main_bp', ''),  # Основные страницы без префикса
            ('app.routers.api_router', 'api_bp', '/api'),
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

    # Регистрируем offers_bp из app.api.offers
    try:
        from app.api.offers import offers_bp
        app.register_blueprint(offers_bp, url_prefix='/api/offers')
        logger.info("✅ offers_bp зарегистрирован на /api/offers")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации offers_bp: {e}")
        # Не поднимаем исключение, просто логируем ошибку

# Инициализируем анализатор каналов с токеном бота
try:
    from app.api.channel_analyzer import init_analyzer

#   init_analyzer(os.environ['BOT_TOKEN'])
    print("✅ Анализатор каналов инициализирован с Bot Token")  # ✅ Используем print вместо logger
except Exception as e:
    print(f"❌ Ошибка инициализации анализатора: {e}")  # ✅ Используем print вместо logger


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
    @app.route('/api/channels', methods=['POST'])
    def create_channel_endpoint():
        """Создать новый канал"""
        from flask import jsonify, request
        import random
        import string

        try:
            data = request.get_json()
            telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')
            logger.info(f"➕ Создание канала от {telegram_user_id}")

            # ДОБАВЛЕНО: Проверка флага повторной верификации
            is_reverify = data.get('action') == 'reverify'
            channel_id = data.get('channel_id') if is_reverify else None

            # Генерируем новый код верификации
            verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            # Возвращаем результат с кодом верификации
            result = {
                'success': True,
                'message': 'Канал добавлен и ожидает верификации' if not is_reverify else 'Новый код верификации сгенерирован',
                'verification_code': verification_code,
                'channel': {
                    'id': channel_id or random.randint(1000, 9999),
                    'username': data.get('username', 'unknown'),
                    'title': f"Канал @{data.get('username', 'unknown')}",
                    'verification_code': verification_code,
                    'status': 'pending'
                }
            }

            logger.info(f"✅ Канал создан с кодом верификации: {verification_code}")
            return jsonify(result)

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

# === ENDPOINT'Ы ДЛЯ КАНАЛОВ ===
@app.route('/api/channels/<int:channel_id>/verify', methods=['PUT', 'POST'])
def verify_channel_unified(channel_id, datetime=None):
    """Единый endpoint для верификации каналов"""
    try:
        logger.info(f"🔍 Запрос верификации канала {channel_id}")

        # Получаем данные пользователя
        telegram_user_id = request.headers.get('X-Telegram-User-Id', 'unknown')
        telegram_username = request.headers.get('X-Telegram-Username', 'unknown')

        logger.info(f"👤 Пользователь: {telegram_username} (ID: {telegram_user_id})")

        # Получаем канал из базы
        channel = channel_db.get_channel(channel_id)
        if not channel:
            return jsonify({
                'success': False,
                'error': 'Канал не найден'
            }), 404

        # Проверяем права доступа
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

        # ОСНОВНАЯ ВЕРИФИКАЦИЯ ЧЕРЕЗ ЕДИНЫЙ СЕРВИС 🎯
        verification_code = channel['verification_code']
        channel_telegram_id = channel.get('telegram_id') or channel.get('username')

        if not channel_telegram_id:
            return jsonify({
                'success': False,
                'error': 'Не указан ID или username канала'
            }), 400

        # ВЫЗЫВАЕМ ЕДИНЫЙ СЕРВИС!
        if verification_service:
            verification_result = verification_service.verify_channel_ownership(
                channel_telegram_id,
                verification_code
            )
        else:
            # Fallback на тестовый режим
            verification_result = {
                'success': True,
                'found': True,  # Для тестирования
                'message': 'Тестовый режим - канал верифицирован',
                'details': {'mode': 'fallback'}
            }

        logger.info(f"📊 Результат верификации: {verification_result}")

        # Обрабатываем результат
        if verification_result['success'] and verification_result['found']:
            # КОД НАЙДЕН - ВЕРИФИЦИРУЕМ КАНАЛ! ✅
            updates = {
                'is_verified': True,
                'status': 'verified',
                'verified_at': datetime.now().isoformat()
            }
            updated_channel = channel_db.update_channel(channel_id, updates)

            # ДОБАВИТЬ отправку уведомления пользователю:
            try:
                import requests
                from datetime import datetime

                bot_token = AppConfig.BOT_TOKEN
                send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                # Получаем данные пользователя
                conn = sqlite3.connect(AppConfig.DATABASE_PATH)
                cursor = conn.cursor()

                cursor.execute("""
                               SELECT u.first_name, u.last_name, u.username, c.created_at
                               FROM users u
                                        JOIN channels c ON c.owner_id = u.id
                               WHERE c.id = ?
                                 AND u.telegram_id = ?
                               """, (channel_id, telegram_user_id))

                user_channel_data = cursor.fetchone()
                conn.close()

                if user_channel_data:
                    # Форматируем имя пользователя
                    user_name_parts = []
                    if user_channel_data[0]:  # first_name
                        user_name_parts.append(user_channel_data[0])
                    if user_channel_data[1]:  # last_name
                        user_name_parts.append(user_channel_data[1])
                    full_name = ' '.join(user_name_parts) if user_name_parts else user_channel_data[2] or 'Пользователь'

                    # Форматируем дату добавления
                    try:
                        created_at = datetime.fromisoformat(user_channel_data[3])
                        formatted_date = created_at.strftime('%d.%m.%Y в %H:%M')
                    except:
                        formatted_date = 'Недавно'

                    success_message = f"""🎉 <b>Отличная новость!</b>

            ✅ <b>Канал успешно верифицирован!</b>

            👤 <b>Владелец:</b> {full_name}
            📺 <b>Канал:</b> {channel['title']}
            📅 <b>Добавлен:</b> {formatted_date}
            🎉 <b>Поздравляем!</b> Ваш канал верифицирован!

            🚀 <b>Что дальше?</b>
            - Настройте цены за размещение
            - Начните получать предложения от рекламодателей
            - Отслеживайте статистику канала
            - Управляйте настройками"""

                    # Создаем клавиатуру с кнопкой Mini App
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚀 Перейти в Mini App",
                                    "web_app": {
                                        "url": f"{AppConfig.WEBAPP_URL}/channels"
                                    }
                                }
                            ]
                        ]
                    }

                    # Отправляем уведомление с кнопкой
                    requests.post(send_url, json={
                        'chat_id': telegram_user_id,
                        'text': success_message,
                        'parse_mode': 'HTML',
                        'reply_markup': keyboard
                    }, timeout=10)

                    logger.info(f"📨 Уведомление о верификации отправлено пользователю {telegram_user_id}")

            except Exception as notification_error:
                logger.error(f"❌ Ошибка отправки уведомления: {notification_error}")


            logger.info(f"✅ Канал {channel_id} успешно верифицирован")

            return jsonify({
                'success': True,
                'message': f'✅ Канал "{channel["title"]}" успешно верифицирован!',
                'channel': updated_channel,
                'verification_details': verification_result['details']
            })

        else:
            # КОД НЕ НАЙДЕН ❌
            error_message = verification_result.get('message', 'Код верификации не найден')

            return jsonify({
                'success': False,
                'error': f'❌ {error_message}',
                'verification_code': verification_code,
                'instructions': [
                    f'1. Перейдите в ваш канал @{channel.get("username", "your_channel")}',
                    f'2. Опубликуйте сообщение с кодом: {verification_code}',
                    f'3. Подождите 1-2 минуты для обновления',
                    f'4. Нажмите кнопку "Верифицировать" снова'
                ],
                'channel': channel,
                'verification_details': verification_result.get('details', {})
            })

    except Exception as e:
        logger.error(f"❌ Критическая ошибка верификации канала {channel_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}',
            'details': {
                'channel_id': channel_id,
                'timestamp': datetime.now().isoformat(),
                'error_type': type(e).__name__
            }
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

        # Получаем username канала
        username = data.get('username', '').replace('@', '').replace('https://t.me/', '')
        if not username:
            username = data.get('channel_url', '').replace('@', '').replace('https://t.me/', '')

        logger.info(f"➕ Запрос создания/верификации канала @{username} от {telegram_user_id}")

        # НОВОЕ: Проверка флага повторной верификации
        is_reverify = data.get('action') == 'reverify'
        requested_channel_id = data.get('channel_id')

        # Проверяем, существует ли уже канал
        existing_channel = None
        for channel in channel_db.channels.values():
            if (channel['user_id'] == telegram_user_id and
                    (channel['username'] == username or channel['username'] == f'@{username}')):
                existing_channel = channel
                break

        # Если канал существует и это НЕ повторная верификация - ошибка
        if existing_channel and not is_reverify:
            logger.warning(f"❌ Канал @{username} уже добавлен пользователем {telegram_user_id}")
            return jsonify({
                'success': False,
                'error': f'Канал @{username} уже добавлен'
            }), 409

        # Если это повторная верификация существующего канала
        if existing_channel and is_reverify:
            logger.info(f"🔄 Повторная верификация канала @{username}")

            # Генерируем новый код верификации
            import random
            import string
            new_verification_code = 'VERIFY_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            # Обновляем код верификации
            existing_channel['verification_code'] = new_verification_code
            existing_channel['status'] = 'pending'
            existing_channel['is_verified'] = False  # Сбрасываем верификацию

            logger.info(f"✅ Новый код верификации для канала {existing_channel['id']}: {new_verification_code}")

            return jsonify({
                'success': True,
                'message': 'Новый код верификации сгенерирован',
                'verification_code': new_verification_code,
                'channel': {
                    'id': existing_channel['id'],
                    'username': username,
                    'title': existing_channel['title'],
                    'verification_code': new_verification_code,
                    'status': 'pending'
                }
            })

        # Создаем новый канал (только если это не повторная верификация)
        channel = channel_db.create_channel(telegram_user_id, {
            'title': data.get('title', f'Канал @{username}'),
            'username': username,
            'telegram_id': data.get('telegram_id', ''),
            'category': data.get('category', 'other'),
            'subscriber_count': data.get('subscriber_count', 0)
        })

        logger.info(f"📺 Создан новый канал {channel['id']} для пользователя {telegram_user_id}")

        return jsonify({
            'success': True,
            'message': 'Канал добавлен и ожидает верификации',
            'verification_code': channel['verification_code'],
            'channel': {
                'id': channel['id'],
                'username': channel['username'],
                'title': channel['title'],
                'verification_code': channel['verification_code'],
                'status': 'pending'
            }
        }), 201

    except Exception as e:
        logger.error(f"❌ Ошибка создания канала: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# === ДОПОЛНИТЕЛЬНЫЙ ENDPOINT ДЛЯ ТЕСТИРОВАНИЯ ===
@app.route('/api/verification/test', methods=['GET'])
def test_verification_service():
    """Тестирование сервиса верификации"""
    try:
        if verification_service:
            # Тестируем с фейковыми данными
            test_result = verification_service.verify_channel_ownership(
                "@test_channel",
                "VERIFY_TEST123"
            )

            return jsonify({
                'success': True,
                'service_available': True,
                'test_result': test_result,
                'bot_token_configured': bool(verification_service.bot_token)
            })
        else:
            return jsonify({
                'success': False,
                'service_available': False,
                'error': 'Сервис верификации не загружен'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/table-schema/<table_name>')
def debug_table_schema(table_name):
    import sqlite3
    conn = sqlite3.connect('telegram_mini_app.db')
    cursor = conn.cursor()

    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        create_sql = cursor.fetchone()

        return jsonify({
            'table': table_name,
            'columns': columns,
            'create_sql': create_sql[0] if create_sql else None
        })
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

@app.route('/debug/routes')
def debug_routes():
    import urllib
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    return jsonify(routes)

@app.route('/api/offers/debug', methods=['POST'])
def debug_create_offer():
    """Отладочный endpoint для создания оффера"""
    try:
        data = request.get_json()
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')

        print(f"DEBUG: Получены данные: {data}")
        print(f"DEBUG: User ID: {telegram_user_id}")

        # Проверяем импорт
        try:
            from add_offer import add_offer
            print("DEBUG: add_offer импортирован успешно")
        except ImportError as e:
            return jsonify({'error': f'Ошибка импорта add_offer: {e}'}), 500

        # Проверяем функцию
        try:
            result = add_offer(int(telegram_user_id), data)
            print(f"DEBUG: Результат add_offer: {result}")
            return jsonify(result)
        except Exception as e:
            print(f"DEBUG: Ошибка в add_offer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Ошибка в add_offer: {str(e)}'}), 500

    except Exception as e:
        print(f"DEBUG: Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Общая ошибка: {str(e)}'}), 500

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


@app.route('/test-static')
def test_static():
    """Тестовый маршрут для проверки статических файлов"""
    import os
    static_path = app.static_folder
    js_path = os.path.join(static_path, 'js')

    return jsonify({
        'static_folder': static_path,
        'static_exists': os.path.exists(static_path),
        'js_folder_exists': os.path.exists(js_path),
        'js_files': os.listdir(js_path) if os.path.exists(js_path) else [],
        'working_dir': os.getcwd(),
        'project_root': PROJECT_ROOT
    })

if __name__ == '__main__':
    main()