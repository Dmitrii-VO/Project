#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
ФИНАЛЬНАЯ ВЕРСИЯ - убрано дублирование, сохранена функциональность
"""

import os
import sqlite3
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
from app.api.offers import offers_bp
from app.routers.main_router import main_bp
from app.api.channels import channels_bp
import requests
from flask import Flask, jsonify, request, render_template


# Загрузка переменных окружения
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем системные переменные")

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

# === СОЗДАНИЕ ПРИЛОЖЕНИЯ ===
def create_app() -> Flask:
    """Фабрика приложений"""

    app = Flask(__name__, static_folder= 'app/static', template_folder='templates')
    app.config.from_object(AppConfig)

    # Настройка JSON сериализации
    app.json.ensure_ascii = False
    app.json.sort_keys = AppConfig.JSON_SORT_KEYS

    # Инициализация компонентов
    register_blueprints(app)
    register_middleware(app)
    register_error_handlers(app)
    register_system_routes(app)

    return app

# === РЕГИСТРАЦИЯ BLUEPRINTS ===
def register_blueprints(app: Flask) -> None:
    """Регистрация Blueprint'ов"""
    app.register_blueprint(offers_bp, url_prefix='/api/offers')
    app.register_blueprint(main_bp)
    app.register_blueprint(channels_bp, url_prefix='/api/channels')


# === MIDDLEWARE ===
def register_middleware(app: Flask) -> None:
    """Регистрация middleware"""

    @app.before_request
    def security_middleware():
        if request.content_length and request.content_length > AppConfig.MAX_CONTENT_LENGTH:
            return jsonify({'error': 'Request too large'}), 413

    @app.after_request
    def security_headers(response):
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
        })
        return response


# === ОБРАБОТЧИКИ ОШИБОК ===
def register_error_handlers(app: Flask) -> None:
    """Регистрация обработчиков ошибок"""

    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad request: {error} | Path: {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Bad request',
                'message': 'Неверные данные запроса',
                'path': request.path
            }), 400
        return render_template('error.html', 
                             message='Неверные данные запроса', 
                             code=400), 400

    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"Unauthorized access: {request.path} | User-Agent: {request.headers.get('User-Agent')}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация',
                'path': request.path
            }), 401
        return render_template('error.html', 
                             message='Требуется авторизация через Telegram', 
                             code=401), 401

    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f"Forbidden access: {request.path} | Headers: {dict(request.headers)}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Недостаточно прав доступа',
                'path': request.path
            }), 403
        return render_template('error.html', 
                             message='Недостаточно прав доступа', 
                             code=403), 403

    @app.errorhandler(404)
    def not_found(error):
        logger.info(f"Not found: {request.path} | Method: {request.method}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Endpoint not found', 
                'path': request.path,
                'method': request.method
            }), 404
        return render_template('error.html', 
                             message='Страница не найдена', 
                             code=404), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning(f"Method not allowed: {request.method} {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Method not allowed',
                'message': f'Метод {request.method} не поддерживается',
                'path': request.path,
                'allowed_methods': error.valid_methods if hasattr(error, 'valid_methods') else []
            }), 405
        return render_template('error.html', 
                             message=f'Метод {request.method} не поддерживается', 
                             code=405), 405

    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.warning(f"Request too large: {request.path} | Content-Length: {request.content_length}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Request too large',
                'message': 'Размер запроса превышает максимально допустимый',
                'max_size': f"{AppConfig.MAX_CONTENT_LENGTH // (1024*1024)}MB"
            }), 413
        return render_template('error.html', 
                             message='Файл слишком большой', 
                             code=413), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        logger.warning(f"Rate limit exceeded: {request.path} | IP: {request.remote_addr}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Превышен лимит запросов',
                'retry_after': getattr(error, 'retry_after', 60)
            }), 429
        return render_template('error.html', 
                             message='Превышен лимит запросов. Попробуйте позже.', 
                             code=429), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error} | Path: {request.path} | Method: {request.method}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal server error',
                'message': 'Внутренняя ошибка сервера'
            }), 500
        return render_template('error.html', 
                             message='Внутренняя ошибка сервера', 
                             code=500), 500

    @app.errorhandler(502)
    def bad_gateway(error):
        logger.error(f"Bad gateway: {error} | Path: {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Bad gateway',
                'message': 'Сервис временно недоступен'
            }), 502
        return render_template('error.html', 
                             message='Сервис временно недоступен', 
                             code=502), 502

    @app.errorhandler(503)
    def service_unavailable(error):
        logger.error(f"Service unavailable: {error} | Path: {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Service unavailable',
                'message': 'Сервис находится на техническом обслуживании'
            }), 503
        return render_template('error.html', 
                             message='Сервис находится на техническом обслуживании', 
                             code=503), 503

    # Обработка SQLite ошибок
    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        logger.error(f"Database error: {error} | Path: {request.path} | Query context available")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Database error',
                'message': 'Ошибка базы данных'
            }), 500
        return render_template('error.html', 
                             message='Временная ошибка. Попробуйте позже.', 
                             code=500), 500

    # Обработка JSON ошибок
    @app.errorhandler(400)
    def handle_json_error(error):
        if 'application/json' in request.content_type:
            logger.warning(f"Invalid JSON: {request.path} | Error: {error}")
            return jsonify({
                'error': 'Invalid JSON',
                'message': 'Неверный формат JSON данных'
            }), 400
        return bad_request(error)

    # Обработка ошибок валидации (если используется)
    try:
        from werkzeug.exceptions import UnprocessableEntity
        
        @app.errorhandler(422)
        def validation_error(error):
            logger.warning(f"Validation error: {error} | Path: {request.path}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Validation failed',
                    'message': 'Ошибка валидации данных',
                    'details': getattr(error, 'data', {})
                }), 422
            return render_template('error.html', 
                                 message='Ошибка валидации данных', 
                                 code=422), 422
    except ImportError:
        pass

    # Обработка ошибок Telegram API (если используется)
    try:
        import telegram
        
        @app.errorhandler(telegram.error.TelegramError)
        def telegram_error(error):
            logger.error(f"Telegram API error: {error} | Path: {request.path}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Telegram API error',
                    'message': 'Ошибка Telegram API'
                }), 503
            return render_template('error.html', 
                                 message='Ошибка связи с Telegram', 
                                 code=503), 503
    except ImportError:
        pass

    # Общий обработчик для всех остальных исключений
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error(f"Unexpected error: {type(error).__name__}: {error} | Path: {request.path}")
        logger.error(f"Traceback: ", exc_info=True)
        
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Unexpected error',
                'message': 'Произошла неожиданная ошибка'
            }), 500
        return render_template('error.html', 
                             message='Произошла неожиданная ошибка', 
                             code=500), 500

    logger.info("✅ Обработчики ошибок зарегистрированы")


# === СЛУЖЕБНЫЕ МАРШРУТЫ ===
def register_system_routes(app: Flask) -> None:
    """Регистрация служебных маршрутов"""

    # === МАРШРУТЫ ЗДОРОВЬЯ СИСТЕМЫ ===
    
    @app.route('/health')
    @app.route('/api/health')
    def health_check():
        """Проверка состояния системы"""
        try:
            # Проверяем БД
            db_status = 'healthy'
            try:
                execute_db_query("SELECT 1", fetch_one=True)
            except Exception as e:
                db_status = f'unhealthy: {str(e)}'
                logger.error(f"Database health check failed: {e}")

            # Проверяем файловую систему
            fs_status = 'healthy' if os.path.exists(AppConfig.DATABASE_PATH) else 'database_missing'

            status = {
                'status': 'healthy' if db_status == 'healthy' else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'telegram_webapp': True,
                'services': {
                    'database': db_status,
                    'filesystem': fs_status,
                    'bot_configured': bool(AppConfig.BOT_TOKEN)
                }
            }

            status_code = 200 if status['status'] == 'healthy' else 503
            return jsonify(status), status_code

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503

    # === МАРШРУТЫ КОНФИГУРАЦИИ ===

    @app.route('/api/config')
    def get_app_config():
        """Получение публичной конфигурации приложения"""
        try:
            config = {
                'app_name': 'Telegram Mini App',
                'version': '1.0.0',
                'api_version': 'v1',
                'features': {
                    'channels': True,
                    'offers': True,
                    'analytics': True,
                    'payments': True,
                    'notifications': True
                },
                'limits': {
                    'max_channels_per_user': 10,
                    'max_offers_per_user': 50,
                    'max_file_size': AppConfig.MAX_CONTENT_LENGTH,
                    'supported_file_types': ['jpg', 'jpeg', 'png', 'gif', 'mp4']
                },
                'telegram': {
                    'webapp_url': AppConfig.WEBAPP_URL,
                    'bot_configured': bool(AppConfig.BOT_TOKEN)
                }
            }

            return jsonify({
                'success': True,
                'config': config,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Config fetch failed: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # === МАРШРУТЫ СТАТИСТИКИ ===

    @app.route('/api/stats/global')
    def get_global_stats():
        """Получение глобальной статистики системы"""
        try:
            stats = {
                'channels': 0,
                'users': 0,
                'offers': 0,
                'revenue': 0
            }

            # Безопасный подсчет с обработкой ошибок
            try:
                result = execute_db_query("SELECT COUNT(*) as count FROM channels WHERE is_active = 1", fetch_one=True)
                stats['channels'] = result['count'] if result else 0
            except:
                pass

            try:
                result = execute_db_query("SELECT COUNT(*) as count FROM users WHERE is_active = 1", fetch_one=True)
                stats['users'] = result['count'] if result else 0
            except:
                pass

            try:
                result = execute_db_query("SELECT COUNT(*) as count FROM offers WHERE status = 'active'", fetch_one=True)
                stats['offers'] = result['count'] if result else 0
            except:
                pass

            try:
                result = execute_db_query("SELECT COALESCE(SUM(price), 0) as total FROM offers WHERE status = 'active'", fetch_one=True)
                stats['revenue'] = float(result['total']) if result and result['total'] else 0
            except:
                pass

            return jsonify({
                'success': True,
                'stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Global stats failed: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # === WEBHOOK МАРШРУТЫ ===

    @app.route('/webhook/telegram', methods=['POST'])
    def telegram_webhook():
        """
        ЕДИНЫЙ WEBHOOK для всех типов Telegram обновлений
        Маршрутизирует обновления по типам в соответствующие обработчики
        """
        try:
            update = request.get_json()
            
            if not update:
                return jsonify({'ok': True})

            logger.info(f"🔔 Получено Telegram обновление: {update.get('update_id', 'unknown')}")
            
            # === ОБРАБОТКА ПЛАТЕЖЕЙ ===
            if 'pre_checkout_query' in update or ('message' in update and 'successful_payment' in update.get('message', {})):
                logger.info("💳 Обрабатываем платежное обновление")
                return handle_payment_webhook(update)
            
            # === ОБРАБОТКА СООБЩЕНИЙ В КАНАЛАХ (верификация) ===
            if 'channel_post' in update:
                logger.info("📢 Обрабатываем сообщение в канале")
                return handle_channel_verification(update)
            
            # === ОБРАБОТКА ЛИЧНЫХ СООБЩЕНИЙ БОТУ ===
            if 'message' in update:
                message = update['message']
                
                # Команда /start
                if message.get('text') == '/start':
                    logger.info("🚀 Обрабатываем команду /start")
                    return handle_start_command(update)
                
                # Пересланные сообщения для верификации
                if 'forward_from_chat' in message:
                    logger.info("📤 Обрабатываем пересланное сообщение")
                    return handle_forwarded_message(update)
            
            # === ОБРАБОТКА CALLBACK QUERY ===
            if 'callback_query' in update:
                logger.info("🔘 Обрабатываем callback query")
                return handle_callback_query(update)
            
            # Если тип обновления не определен - просто возвращаем OK
            logger.info(f"❓ Неопределенный тип обновления: {list(update.keys())}")
            return jsonify({'ok': True})

        except Exception as e:
            logger.error(f"❌ Ошибка webhook: {e}")
            return jsonify({'ok': True})  # Всегда возвращаем ok для Telegram

    def handle_payment_webhook(update):
        """Обработка платежных обновлений"""
        try:
            from app.routers.payment_router import process_payment_update
            return process_payment_update(update)
        except ImportError:
            logger.warning("⚠️ Payment router не найден")
            return jsonify({'ok': True})

    def handle_channel_verification(update):
        """Обработка верификации каналов через channel_post"""
        try:
            message = update['channel_post']
            chat = message.get('chat', {})
            chat_id = str(chat.get('id'))
            text = message.get('text', '')

            logger.info(f"📢 Сообщение из канала {chat_id}: {text[:50]}...")

            # Проверяем коды верификации
            result = execute_db_query(
                "SELECT * FROM channels WHERE telegram_id = ? AND is_verified = 0 AND verification_code IS NOT NULL",
                (chat_id,),
                fetch_all=True
            )

            for channel in result:
                if channel['verification_code'] in text:
                    # Верифицируем канал
                    execute_db_query(
                        "UPDATE channels SET is_verified = 1, verified_at = ? WHERE id = ?",
                        (datetime.utcnow().isoformat(), channel['id'])
                    )
                    logger.info(f"✅ Канал {channel['id']} автоматически верифицирован")

            return jsonify({'ok': True})

        except Exception as e:
            logger.error(f"❌ Ошибка верификации канала: {e}")
            return jsonify({'ok': True})

    def handle_start_command(update):
        """Обработка команды /start"""
        try:
            import requests
            
            message = update['message']
            from_user_id = str(message['from']['id'])
            
            bot_token = AppConfig.BOT_TOKEN
            if not bot_token:
                return jsonify({'ok': True})
            
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            welcome_message = """👋 <b>Добро пожаловать!</b>

    Я помогу вам верифицировать ваши Telegram каналы.

    <b>Как это работает:</b>
    1️⃣ Добавьте канал в Mini App
    2️⃣ Получите код верификации  
    3️⃣ Опубликуйте код в вашем канале
    4️⃣ Переслать сообщение с кодом мне

    После успешной верификации вы получите уведомление прямо здесь!"""

            requests.post(send_url, json={
                'chat_id': from_user_id,
                'text': welcome_message,
                'parse_mode': 'HTML'
            }, timeout=5)
            
            return jsonify({'ok': True})

        except Exception as e:
            logger.error(f"❌ Ошибка /start: {e}")
            return jsonify({'ok': True})

    def handle_forwarded_message(update):
        """Обработка пересланных сообщений для верификации с расширенным логом"""
        try:
            message = update.get('message', {})
            forwarded_chat = message.get('forward_from_chat', {})
            text = message.get('text', '')

            logger.info("📨 Получено пересланное сообщение:")
            logger.info(f"  🔹 Текст: {text}")
            logger.info(f"  🔹 forward_from_chat: {forwarded_chat}")

            chat_id = str(forwarded_chat.get('id', ''))
            username = forwarded_chat.get('username', '')

            result = None

            if chat_id:
                logger.info(f"🔍 Пытаемся найти канал по telegram_id = {chat_id}")
                result = execute_db_query(
                    "SELECT * FROM channels WHERE telegram_id = ? AND is_verified = 0",
                    (chat_id,),
                    fetch_one=True
                )

            if not result and username:
                logger.info(f"🔍 Пытаемся найти канал по username = {username}")
                result = execute_db_query(
                    "SELECT * FROM channels WHERE username = ? AND is_verified = 0",
                    (username,),
                    fetch_one=True
                )

            if not result:
                logger.warning("❌ Канал не найден в базе по ID или username")
            elif result['verification_code'] not in text:
                logger.warning(f"❌ Код верификации не найден в тексте. Ожидали: {result['verification_code']}")
            else:
                execute_db_query(
                    "UPDATE channels SET is_verified = 1, verified_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), result['id'])
                )
                logger.info(f"✅ Канал {result['id']} успешно верифицирован через пересылку")

            return jsonify({'ok': True})

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке пересланного сообщения: {e}", exc_info=True)
            return jsonify({'ok': True})



    def handle_callback_query(update):
        """Обработка inline кнопок"""
        try:
            # Здесь можно добавить обработку inline кнопок
            return jsonify({'ok': True})
        except Exception as e:
            logger.error(f"❌ Ошибка callback: {e}")
            return jsonify({'ok': True})


    # === СЛУЖЕБНЫЕ МАРШРУТЫ ===

    @app.route('/api/system/info')
    def system_info():
        """Информация о системе"""
        try:
            import platform
            import sys

            info = {
                'python_version': sys.version,
                'platform': platform.platform(),
                'architecture': platform.architecture(),
                'hostname': platform.node(),
                'app_config': {
                    'debug': AppConfig.DEBUG,
                    'database_path': AppConfig.DATABASE_PATH,
                    'webapp_url': AppConfig.WEBAPP_URL
                }
            }

            return jsonify({
                'success': True,
                'system_info': info,
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"System info failed: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/test/connection')
    def test_connection():
        """Тест соединения и базовой функциональности"""
        try:
            # Тестируем различные компоненты
            tests = {
                'database': False,
                'filesystem': False,
                'config': False
            }

            # Тест БД
            try:
                execute_db_query("SELECT 1", fetch_one=True)
                tests['database'] = True
            except:
                pass

            # Тест файловой системы
            try:
                tests['filesystem'] = os.path.exists(AppConfig.DATABASE_PATH)
            except:
                pass

            # Тест конфигурации
            try:
                tests['config'] = bool(AppConfig.BOT_TOKEN)
            except:
                pass

            success = all(tests.values())

            return jsonify({
                'success': success,
                'tests': tests,
                'message': 'All tests passed' if success else 'Some tests failed',
                'timestamp': datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # === СЛУЖЕБНЫЕ СТРАНИЦЫ ===

    @app.route('/robots.txt')
    def robots_txt():
        """Robots.txt для поисковых систем"""
        return """User-agent: *
Disallow: /api/
Disallow: /admin/
Allow: /
""", 200, {'Content-Type': 'text/plain'}

    @app.route('/favicon.ico')
    def favicon():
        """Favicon redirect"""
        return '', 204

    logger.info("✅ Служебные маршруты зарегистрированы")




# === ИНИЦИАЛИЗАЦИЯ ===
logger = setup_logging()
app = create_app()

# === ТОЧКА ВХОДА ===
def main():
    """Главная функция запуска"""

    if not AppConfig.validate():
        logger.error("❌ Критические ошибки конфигурации")
        sys.exit(1)
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    logger.info("=" * 60)
    logger.info("🚀 TELEGRAM MINI APP - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ")
    logger.info("=" * 60)
    logger.info(f"📱 BOT_TOKEN: {'✅ Настроен' if AppConfig.BOT_TOKEN else '❌ Отсутствует'}")
    logger.info(f"🗄️ База данных: {AppConfig.DATABASE_PATH}")
    logger.info(f"🌐 Запуск на: http://{host}:{port}")

    # Показываем статистику маршрутов
    total_routes = len(list(app.url_map.iter_rules()))
    offers_routes = len([r for r in app.url_map.iter_rules() if '/api/offers' in r.rule])
    logger.info(f"📊 Всего маршрутов: {total_routes} (offers: {offers_routes})")
    logger.info("=" * 60)
    logger.info(f"📡 WEBAPP_URL = {AppConfig.WEBAPP_URL}")

    # === Установка Webhook для Telegram ===
    try:
        bot_token = AppConfig.BOT_TOKEN
        webhook_url = f"{AppConfig.WEBAPP_URL}/webhook/telegram"

        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            params={'url': webhook_url},
            timeout=10
        )

        if response.status_code == 200 and response.json().get("ok"):
            logger.info(f"✅ Webhook успешно установлен: {webhook_url}")
        else:
            logger.error(f"❌ Не удалось установить webhook: {response.text}")
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")

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