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
            # ('app.routers.channel_router', 'channel_bp', '/api/channels'),  # УБИРАЕМ ПРОБЛЕМНЫЙ
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

    @app.route('/health')
    def health_check():
        """Проверка здоровья приложения"""
        try:
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '2.0.0',
                'features': AppConfig.FEATURES,
                'uptime': getattr(app, 'start_time', 'unknown')
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

    @app.route('/system/config')
    def system_config():
        """Системная конфигурация (безопасная)"""
        return jsonify({
            'app_name': 'Telegram Mini App',
            'version': '2.0.0',
            'features': AppConfig.FEATURES,
            'telegram_webapp': True,
            'debug': AppConfig.DEBUG
        })

    @app.route('/system/stats')
    def system_stats():
        """Системная статистика"""
        try:
            return jsonify(stats.get_stats())
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return jsonify({'error': 'Stats unavailable'}), 500


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


# === ИНИЦИАЛИЗАЦИЯ ===
logger = setup_logging()
app = create_app()
stats = AppStats()

# Регистрация служебных маршрутов (основные маршруты в app/routers/main_router.py)
#register_system_routes(app)

# Сохранение времени старта
app.start_time = stats.start_time.isoformat()


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