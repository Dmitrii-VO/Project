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


def create_app() -> Flask:
    """Фабрика приложений Flask"""

    # Создаем Flask приложение
    app = Flask(__name__)

    # Загружаем конфигурацию
    try:
        from app.config.settings import Config
        app.config.from_object(Config)

        # Проверка критических настроек
        if not Config.validate_config():
            print("❌ Критическая ошибка конфигурации!")
            sys.exit(1)

    except ImportError as e:
        print(f"❌ Ошибка импорта конфигурации: {e}")
        # Базовая конфигурация как fallback
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
        app.config['DEBUG'] = True

    # Инициализация базы данных
    try:
        from app.models.database import db_manager
        if not db_manager.init_database():
            print("❌ Ошибка инициализации базы данных")
            print("💡 Попробуйте: python sqlite_migration.py")
            sys.exit(1)
    except ImportError as e:
        print(f"⚠️ Предупреждение: Модуль базы данных недоступен: {e}")

    # Регистрация middleware
    register_middleware(app)

    # Регистрация маршрутов
    register_routes(app)

    # Обработчики ошибок
    register_error_handlers(app)

    # Инициализация дополнительных систем
    initialize_systems(app)

    return app


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
        from app.config.settings import Config
        if Config.BOT_TOKEN:
            try:
                from app.services.telegram_service import create_telegram_service
                telegram_service = create_telegram_service(Config.BOT_TOKEN)
                if telegram_service:
                    app.telegram_service = telegram_service
                    logger.info("✅ Telegram сервис инициализирован")
                else:
                    logger.error("❌ Не удалось создать Telegram сервис")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Telegram сервиса: {e}")
    except ImportError:
        logger.warning("⚠️ Конфигурация недоступна для Telegram сервиса")

    # Создаем базовые маршруты для проверки здоровья
    @app.route('/health')
    def health_check():
        from flask import jsonify
        import os

        try:
            from app.config.settings import Config
            db_path = Config.DATABASE_PATH
            bot_token = bool(Config.BOT_TOKEN)
        except:
            db_path = 'telegram_mini_app.db'
            bot_token = bool(os.environ.get('BOT_TOKEN'))

        return jsonify({
            'status': 'healthy',
            'architecture': 'modular',
            'database_exists': os.path.exists(db_path),
            'bot_token_configured': bot_token,
            'modules_loaded': True
        })

    logger.info("✅ Системы инициализированы")


# Для обратной совместимости
app = None


def get_app():
    """Получение экземпляра приложения"""
    global app
    if app is None:
        app = create_app()
    return app