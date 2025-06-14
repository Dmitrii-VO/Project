# app/__init__.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import os
import sys
import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаем глобальный объект приложения
app = None


def create_app() -> Flask:
    """Фабрика приложений Flask"""
    global app

    # Создаем Flask приложение
    app = Flask(__name__)

    # Загружаем конфигурацию
    try:
        from app.config.settings import Config
        app.config.from_object(Config)
    except ImportError as e:
        print(f"❌ Ошибка импорта конфигурации: {e}")
        # Базовая конфигурация как fallback
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
        app.config['DEBUG'] = True

    return app

def initialize_systems():
    """Инициализация систем"""
    print("Системы инициализированы")
    return True


def register_middleware(app: Flask):
    """Регистрация middleware"""
    try:
        from app.services.security_service import security_service
        from flask import request, jsonify

        @app.before_request
        def security_middleware():
            """Middleware безопасности"""
            client_ip = security_service.get_client_ip()

            # Блокировка заблокированных IP
            if client_ip in security_service.blocked_ips:
                security_service.log_security_event('BLOCKED_IP_ACCESS', {
                    'ip': client_ip,
                    'path': request.path,
                    'method': request.method
                })
                return jsonify({'error': 'Access denied'}), 403

            # Rate limiting
            if not security_service.rate_limit_check(f"global_{client_ip}"):
                security_service.suspicious_ips.add(client_ip)
                security_service.log_security_event('RATE_LIMIT_EXCEEDED', {
                    'ip': client_ip,
                    'path': request.path
                })
                return jsonify({'error': 'Too many requests'}), 429

            # Проверка размера запроса
            if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
                return jsonify({'error': 'Request too large'}), 413

        @app.after_request
        def security_headers_middleware(response):
            """Добавление заголовков безопасности"""
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

            # CSP
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://telegram.org; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.telegram.org; "
                "frame-ancestors 'none'"
            )
            response.headers['Content-Security-Policy'] = csp

            return response

    except ImportError as e:
        print(f"⚠️ Предупреждение: Сервис безопасности недоступен: {e}")


def register_routes(app: Flask):
    """Регистрация всех маршрутов"""
    logger = logging.getLogger(__name__)

    # Основные маршруты
    try:
        from app.api.main_routes import main_bp
        app.register_blueprint(main_bp)
        logger.info("✅ Основные маршруты зарегистрированы")
    except ImportError as e:
        logger.warning(f"⚠️ Основные маршруты недоступны: {e}")

        # Создаем базовые маршруты как fallback
        @app.route('/')
        def index():
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Telegram Mini App</title></head>
            <body>
                <h1>🚀 Telegram Mini App</h1>
                <p>Модульная архитектура запущена!</p>
                <ul>
                    <li><a href="/test">Test API</a></li>
                    <li><a href="/health">Health Check</a></li>
                </ul>
            </body>
            </html>
            '''

        @app.route('/test')
        def test():
            from flask import jsonify
            return jsonify({
                'status': 'OK',
                'message': 'Модульная архитектура работает!',
                'architecture': 'modular'
            })

    # API маршруты
    api_modules = [
        ('app.api.auth', 'auth_bp', '/api/auth'),
        ('app.api.channels', 'channels_bp', '/api/channels'),
        ('app.api.offers', 'offers_bp', '/api/offers'),
        ('app.api.payments', 'payments_bp', '/api/payments'),
        ('app.api.analytics', 'analytics_bp', '/api/analytics')
    ]

    for module_name, blueprint_name, url_prefix in api_modules:
        try:
            module = __import__(module_name, fromlist=[blueprint_name])
            blueprint = getattr(module, blueprint_name)
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            logger.info(f"✅ {module_name} зарегистрирован")
        except ImportError as e:
            logger.warning(f"⚠️ {module_name} недоступен: {e}")
        except AttributeError as e:
            logger.warning(f"⚠️ Blueprint {blueprint_name} не найден в {module_name}: {e}")


def register_error_handlers(app: Flask):
    """Регистрация обработчиков ошибок"""
    from flask import jsonify, request, render_template_string

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint не найден'}), 404

        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Страница не найдена</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error-container { max-width: 600px; margin: 0 auto; }
                .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>🚫 Страница не найдена</h1>
                <p>Запрошенная страница: <code>{{ request.path }}</code></p>
                <p>Возможно, ссылка устарела или содержит ошибку.</p>
                <a href="/" class="btn">← Вернуться на главную</a>
            </div>
        </body>
        </html>
        '''), 404

    @app.errorhandler(500)
    def internal_error(error):
        logging.getLogger(__name__).error(f"500 Error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

    @app.errorhandler(429)
    def rate_limit_handler(error):
        return jsonify({'error': 'Превышен лимит запросов', 'retry_after': 3600}), 429


def initialize_systems(app: Flask):
    """Инициализация дополнительных систем"""
    logger = logging.getLogger(__name__)

    # Инициализация Telegram сервиса
    try:
        if config_available and Config.BOT_TOKEN:
            if telegram_service_class_available and TelegramService:
                # Используем класс TelegramService если доступен
                telegram_service = TelegramService(Config.BOT_TOKEN)
                app.telegram_service = telegram_service
                logger.info("✅ TelegramService инициализирован")
            elif TELEGRAM_INTEGRATION and create_telegram_service:
                # Fallback на функцию create_telegram_service
                telegram_service = create_telegram_service(Config.BOT_TOKEN)
                app.telegram_service = telegram_service
                logger.info("✅ Telegram интеграция инициализирована (fallback)")
            else:
                logger.warning("⚠️ Telegram сервисы недоступны")
                app.telegram_service = None
        else:
            logger.error("❌ BOT_TOKEN не настроен")
            app.telegram_service = None
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Telegram: {e}")
        app.telegram_service = None

    # Создаем базовые маршруты для проверки здоровья
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'architecture': 'modular',
            'database_exists': os.path.exists(DATABASE_PATH),
            'bot_token_configured': bool(BOT_TOKEN),
            'modules_loaded': True
        })

    logger.info("✅ Системы инициализированы")

def get_app():
    """Получение экземпляра приложения"""
    global app
    if app is None:
        app = create_app()
    return app

__all__ = ['create_app', 'get_app', 'app']