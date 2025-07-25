#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
ФИНАЛЬНАЯ ВЕРСИЯ - убрано дублирование, сохранена функциональность
"""

import os
import sqlite3
import sys
import logging
from datetime import datetime
from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig
from app.api.offers import offers_bp
from app.api.offers_moderation import offers_moderation_bp
from app.routers.main_router import main_bp
from app.api.channels import channels_bp
from app.api.analytics import analytics_bp
from app.api.payments import payments_bp
import requests
from flask import Flask, jsonify, request, render_template
from app.api.channel_analyzer import analyzer_bp
# Удалено - функциональность интегрирована в новый offers API
from app.api.proposals_management import proposals_management_bp
from app.api.monitoring_statistics import monitoring_statistics_bp
from app.api.campaigns_management import campaigns_bp
from app.api.mobile import mobile_bp
from app.api.users import users_bp
from app.api.smart_recommendations import smart_recommendations_bp
from app.telegram.telegram_bot_commands import TelegramBotExtension
from app.telegram.telegram_channel_parser import TelegramChannelParser
from app.telegram.telegram_notifications import TelegramNotificationService
from app.security import (
    setup_csrf_protection, 
    setup_rate_limiting, 
    setup_security_headers,
    SecurityAuditLogger
)
from app.performance import (
    setup_caching,
    setup_performance_monitoring,
    DatabaseOptimizer
)

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

    app = Flask(__name__,
                static_folder='app/static',
                template_folder='templates')
    app.config.from_object(AppConfig)
    # Настройка JSON сериализации
    app.json.ensure_ascii = False
    app.json.sort_keys = AppConfig.JSON_SORT_KEYS

    # Инициализация компонентов
    register_blueprints(app)
    register_security(app)
    register_performance(app)
    register_middleware(app)
    register_error_handlers(app)
    register_system_routes(app)

    logger.info("✅ Компоненты приложения инициализированы")
    if AppConfig.TELEGRAM_INTEGRATION and AppConfig.BOT_TOKEN:
        try:
            app.telegram_notifications = TelegramNotificationService()
            app.telegram_parser = TelegramChannelParser()
            app.telegram_bot = TelegramBotExtension()   
            logger.info("✅ Telegram сервисы инициализированы")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Telegram: {e}") 
    else:
        logger.warning("⚠️ Telegram интеграция отключена или BOT_TOKEN не задан")
    return app


# === РЕГИСТРАЦИЯ BLUEPRINTS ===
def register_blueprints(app: Flask) -> None:
    """Регистрация Blueprint'ов"""
    app.register_blueprint(offers_bp, url_prefix='/api/offers')
    app.register_blueprint(offers_moderation_bp)  # Модерация офферов
    app.register_blueprint(main_bp)
    app.register_blueprint(channels_bp, url_prefix='/api/channels')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(analyzer_bp, url_prefix='/api/analyzer')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    # Удалено - функциональность интегрирована в новый offers API
    app.register_blueprint(proposals_management_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(mobile_bp, url_prefix='/api/mobile')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(smart_recommendations_bp, url_prefix='/api/offers')
    app.register_blueprint(monitoring_statistics_bp,
                           url_prefix='/api/monitoring_statistics')


# === БЕЗОПАСНОСТЬ ===
def register_security(app: Flask) -> None:
    """Регистрация модулей безопасности"""
    try:
        # 1. CSRF Protection - защита от межсайтовых запросов
        csrf = setup_csrf_protection(app)
        logger.info("✅ CSRF Protection настроена")
        
        # 2. Rate Limiting - ограничение частоты запросов
        rate_limiter = setup_rate_limiting(app)
        logger.info("✅ Rate Limiting настроен")
        
        # 3. Security Headers - заголовки безопасности
        security_headers = setup_security_headers(app)
        logger.info("✅ Security Headers настроены")
        
        # 4. Audit Logger - аудит действий пользователей
        audit_logger = SecurityAuditLogger(app, db_path=AppConfig.DATABASE_PATH)
        logger.info("✅ Security Audit Logger настроен")
        
        # Добавляем эндпоинты безопасности
        @app.route('/api/security/dashboard', methods=['GET'])
        def security_dashboard():
            """Дашборд безопасности (только для администратора)"""
            user_id = request.headers.get('X-Telegram-User-Id')
            
            # Проверяем права администратора
            if user_id != '373086959':  # ID администратора
                return jsonify({
                    'error': 'Access Denied',
                    'message': 'Administrator access required'
                }), 403
            
            try:
                dashboard_data = audit_logger.get_security_dashboard_data()
                return jsonify({
                    'success': True,
                    'data': dashboard_data
                })
            except Exception as e:
                logger.error(f"Security dashboard error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to load security dashboard'
                }), 500
        
        @app.route('/api/security/user-activity/<user_id>', methods=['GET'])
        def user_activity_summary(user_id):
            """Сводка активности пользователя (только для администратора)"""
            requester_id = request.headers.get('X-Telegram-User-Id')
            
            # Проверяем права (администратор или сам пользователь)
            if requester_id != '373086959' and requester_id != user_id:
                return jsonify({
                    'error': 'Access Denied',
                    'message': 'Insufficient permissions'
                }), 403
            
            try:
                hours = int(request.args.get('hours', 24))
                activity_data = audit_logger.get_user_activity_summary(user_id, hours)
                return jsonify({
                    'success': True,
                    'data': activity_data
                })
            except Exception as e:
                logger.error(f"User activity summary error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to load user activity'
                }), 500
        
        logger.info("✅ Модули безопасности зарегистрированы")
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки безопасности: {e}")
        # Не останавливаем приложение, но логируем критическую ошибку
        logger.critical("🚨 ПРИЛОЖЕНИЕ ЗАПУЩЕНО БЕЗ ПОЛНОЙ ЗАЩИТЫ БЕЗОПАСНОСТИ!")


# === ПРОИЗВОДИТЕЛЬНОСТЬ ===
def register_performance(app: Flask) -> None:
    """Регистрация модулей производительности"""
    try:
        # 1. Кэширование - Redis с fallback на память
        cache_manager = setup_caching(app)
        logger.info("✅ Кэширование настроено")
        
        # 2. Оптимизация базы данных - индексы и оптимизированные запросы
        db_optimizer = DatabaseOptimizer(app, db_path=AppConfig.DATABASE_PATH)
        logger.info("✅ Оптимизация БД настроена")
        
        # 3. Мониторинг производительности - метрики API и БД
        performance_monitor = setup_performance_monitoring(app)
        logger.info("✅ Мониторинг производительности настроен")
        
        # Добавляем сводный endpoint производительности
        @app.route('/api/performance/dashboard', methods=['GET'])
        def performance_dashboard():
            """Дашборд производительности (только для администратора)"""
            user_id = request.headers.get('X-Telegram-User-Id')
            
            # Проверяем права администратора
            if user_id != '373086959':
                return jsonify({
                    'error': 'Access Denied',
                    'message': 'Administrator access required'
                }), 403
            
            try:
                # Собираем данные от всех модулей
                dashboard_data = {
                    'cache_stats': cache_manager.get_stats(),
                    'performance_metrics': performance_monitor.get_current_metrics(),
                    'slow_queries': db_optimizer.get_slow_queries_report()[:10],
                    'system_info': {
                        'cache_backend': 'redis' if cache_manager.redis_client else 'memory',
                        'db_optimization': 'enabled',
                        'monitoring': 'active'
                    }
                }
                
                return jsonify({
                    'success': True,
                    'data': dashboard_data,
                    'generated_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Performance dashboard error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to load performance dashboard'
                }), 500
        
        @app.route('/api/performance/optimize', methods=['POST'])
        def optimize_performance():
            """Запуск оптимизации производительности (администратор)"""
            user_id = request.headers.get('X-Telegram-User-Id')
            
            if user_id != '373086959':
                return jsonify({
                    'error': 'Access Denied',
                    'message': 'Administrator access required'
                }), 403
            
            try:
                # Запускаем обслуживание БД
                db_optimizer.optimize_database_maintenance()
                
                # Очищаем старые данные из кэша
                cache_manager.invalidate_pattern("*old*")
                
                # Сбрасываем метрики производительности
                performance_monitor.reset_current_period()
                
                return jsonify({
                    'success': True,
                    'message': 'Performance optimization completed',
                    'actions': [
                        'Database maintenance executed',
                        'Cache cleaned up',
                        'Performance metrics reset'
                    ]
                })
            except Exception as e:
                logger.error(f"Performance optimization error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to optimize performance'
                }), 500
        
        logger.info("✅ Модули производительности зарегистрированы")
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки производительности: {e}")
        # Не останавливаем приложение, но логируем критическую ошибку
        logger.critical("🚨 ПРИЛОЖЕНИЕ ЗАПУЩЕНО БЕЗ ПОЛНОЙ ОПТИМИЗАЦИИ ПРОИЗВОДИТЕЛЬНОСТИ!")


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
        # Проверяем, является ли это JSON ошибкой
        if request.content_type and 'application/json' in request.content_type:
            logger.warning(f"Invalid JSON: {request.path} | Error: {error}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Invalid JSON',
                    'message': 'Неверный формат JSON данных'
                }), 400
        
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
    def webhook():
        """Обработчик webhook от Telegram"""
        try:
            update = request.get_json()
            
            if not update:
                logger.warning("🚫 Пустой webhook")
                return jsonify({'ok': True})
            
            logger.info(f"📨 Получен webhook: {update.get('update_id', 'unknown')}")
            
            # === ОБРАБОТКА СООБЕНИЙ ===
            if 'message' in update:
                message = update['message']
                telegram_id = message.get('from', {}).get('id')
                text = message.get('text', '')
                
                if not telegram_id:
                    return jsonify({'ok': True})
                
                # === КОМАНДА /start ===
                if text == '/start':
                    return handle_start_command(update)    
                            
                # Пересланные сообщения для верификации
                if 'forward_from_chat' in message:
                    logger.info("📤 Обрабатываем пересланное сообщение")
                    return handle_forwarded_message(update)     
                           
                # === ОБРАБОТКА КОМАНД ===
                if text.startswith('/'):
                    return handle_command(telegram_id, text)
                                

            
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

    def handle_command(telegram_id: int, text: str) -> dict:
        """Новый роутер команд"""
        try:
            # Извлекаем команду и параметры
            parts = text.strip().split()
            command = parts[0][1:]  # Убираем первый символ "/"
            args = parts[1:] if len(parts) > 1 else []
            
            logger.info(f"🎯 Обрабатываем команду: /{command} от пользователя {telegram_id}")
            if args:
                logger.info(f"📝 Параметры команды: {args}")
            
            # Проверяем, что telegram_bot инициализирован
            if not hasattr(app, 'telegram_bot'):
                logger.error("❌ telegram_bot не инициализирован")
                return jsonify({'ok': True})
            
            # Обрабатываем команду через TelegramBotExtension
            if command == 'post_published' and args:
                # Для команды post_published передаем ссылку на пост
                response_data = app.telegram_bot.process_command_with_args(command, telegram_id, args)
            else:
                # Стандартная обработка команд
                response_data = app.telegram_bot.process_command(command, telegram_id)
            
            # Отправляем ответ пользователю
            success = app.telegram_bot.send_telegram_message(telegram_id, response_data)
            
            if success:
                logger.info(f"✅ Команда /{command} успешно обработана")
            else:
                logger.error(f"❌ Ошибка отправки ответа на команду /{command}")
            
            return jsonify({'ok': True})
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды {text}: {e}")
            
            # Отправляем сообщение об ошибке пользователю
            try:
                error_response = {
                    'text': "❌ Произошла ошибка при обработке команды. Попробуйте позже.",
                    'parse_mode': 'HTML'
                }
                app.telegram_bot.send_telegram_message(telegram_id, error_response)
            except:
                pass
            
            return jsonify({'ok': True})


    def handle_start_command(update):
        try:
            # Извлекаем данные из Telegram
            if isinstance(update, dict):
                telegram_id = update.get('message', {}).get('from', {}).get('id')
                first_name = update.get('message', {}).get('from', {}).get('first_name', 'Пользователь')
                last_name = update.get('message', {}).get('from', {}).get('last_name')  # ← Добавлена фамилия
                username = update.get('message', {}).get('from', {}).get('username')
            else:
                telegram_id = update.effective_user.id
                first_name = update.effective_user.first_name or 'Пользователь'
                last_name = update.effective_user.last_name  # ← Добавлена фамилия
                username = update.effective_user.username
            
            # Получаем пользователя
            user = execute_db_query(
                'SELECT * FROM users WHERE telegram_id = ?',
                (telegram_id,),
                fetch_one=True
            )
            
            if not user:
                # Создаем нового пользователя
                execute_db_query(
                    'INSERT INTO users (telegram_id, first_name, last_name, username) VALUES (?, ?, ?, ?)',
                    (telegram_id, first_name, last_name, username)
                )
                user = execute_db_query(
                    'SELECT * FROM users WHERE telegram_id = ?',
                    (telegram_id,),
                    fetch_one=True
                )
            else:
                # ОБНОВЛЯЕМ существующего пользователя данными из Telegram
                execute_db_query(
                    'UPDATE users SET first_name = ?, last_name = ?, username = ? WHERE telegram_id = ?',
                    (first_name, last_name, username, telegram_id)
                )
                # Получаем обновленного пользователя
                user = execute_db_query(
                    'SELECT * FROM users WHERE telegram_id = ?',
                    (telegram_id,),
                    fetch_one=True
                )
            
            # Теперь user содержит актуальные данные (включая фамилию)
            TelegramNotificationService.send_welcome_notification(user)
            
            return {'ok': True}
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print(f"❌ Update: {update}")
            return {'ok': False}
        
    @app.route('/api/telegram/set_commands', methods=['POST'])
    def set_telegram_commands():
        """Установка команд в меню Telegram бота"""
        try:
            if not hasattr(app, 'telegram_bot') or not app.telegram_bot.bot_token:
                return jsonify({'error': 'BOT_TOKEN не настроен'}), 400
            
            # Получаем список команд
            commands = app.telegram_bot.get_commands_list()
            
            # Формируем команды для Telegram API
            telegram_commands = [
                {"command": cmd["command"], "description": cmd["description"]}
                for cmd in commands
            ]
            
            # Добавляем базовые команды
            telegram_commands.insert(0, {"command": "start", "description": "🚀 Запуск бота"})
            
            # Отправляем в Telegram API
            url = f"https://api.telegram.org/bot{app.telegram_bot.bot_token}/setMyCommands"
            data = {"commands": telegram_commands}
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200 and response.json().get('ok'):
                logger.info(f"✅ Команды установлены в Telegram: {len(telegram_commands)} шт.")
                return jsonify({
                    'success': True,
                    'message': f'Установлено {len(telegram_commands)} команд',
                    'commands': telegram_commands
                })
            else:
                logger.error(f"❌ Ошибка установки команд: {response.text}")
                return jsonify({'error': 'Ошибка установки команд в Telegram'}), 500
                
        except Exception as e:
            logger.error(f"❌ Ошибка установки команд: {e}")
            return jsonify({'error': str(e)}), 500   
             
    def handle_forwarded_message(update):
        """Обработка пересланных сообщений для верификации каналов"""
        try:
           
            message = update['message']
            text = message.get('text', '')
            forward_from_chat = message.get('forward_from_chat', {})
            
            if not forward_from_chat:
                return jsonify({'ok': True})
            
            channel_id = str(forward_from_chat.get('id', ''))
            channel_username = forward_from_chat.get('username', '')
            
            logger.info(f"📨 Получено пересланное сообщение:")
            logger.info(f"  🔹 Текст: {text}")
            logger.info(f"  🔹 forward_from_chat: {forward_from_chat}")
            
            # Ищем канал по telegram_id
            logger.info(f"🔍 Пытаемся найти канал по telegram_id = {channel_id}")
            result = execute_db_query(
                "SELECT * FROM channels WHERE telegram_id = ? AND is_verified = 0 AND verification_code IS NOT NULL",
                (channel_id,),
                fetch_one=True
            )
            
            # Если не найден по ID, ищем по username
            if not result and channel_username:
                logger.info(f"🔍 Пытаемся найти канал по username = {channel_username}")
                result = execute_db_query(
                    "SELECT * FROM channels WHERE username = ? AND is_verified = 0 AND verification_code IS NOT NULL",
                    (channel_username,),
                    fetch_one=True
                )
            
            if result and result['verification_code'] in text:
                # Верифицируем канал
                execute_db_query(
                    "UPDATE channels SET is_verified = 1, verified_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), result['id'])
                )
                
                logger.info(f"✅ Канал {result['id']} успешно верифицирован через пересылку")
                
                # ✅ ДОБАВЛЯЕМ ОТПРАВКУ УВЕДОМЛЕНИЯ
                try:
                    # Получаем данные владельца канала
                    owner = execute_db_query(
                        "SELECT * FROM users WHERE id = ?",
                        (result['owner_id'],),
                        fetch_one=True
                    )
                    
                    if owner:
                        logger.info(f"📨 Отправляем уведомление владельцу канала {result['id']}")
                        
                        # Отправляем уведомление о верификации
                        notification_result = TelegramNotificationService.send_channel_notification(
                            user=owner,
                            channel=result,
                            notification_type='verified'
                        )
                        
                        if notification_result:
                            logger.info(f"✅ Уведомление о верификации отправлено владельцу канала {result['id']}")
                        else:
                            logger.error(f"❌ Не удалось отправить уведомление владельцу канала {result['id']}")
                    else:
                        logger.warning(f"⚠️ Владелец канала {result['id']} не найден в БД")
                        
                except Exception as notification_error:
                    logger.error(f"❌ Ошибка отправки уведомления о верификации: {notification_error}")
            
            return jsonify({'ok': True})
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки пересланного сообщения: {e}")
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

    # === Запуск планировщика мониторинга ===
    try:
        if not AppConfig.DEBUG:  # Только в продакшене
            from app.tasks.monitoring_scheduler import start_monitoring
            start_monitoring()
            logger.info("✅ Планировщик мониторинга запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")

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
        
        # Останавливаем планировщик
        try:
            from app.tasks.monitoring_scheduler import stop_monitoring
            stop_monitoring()
            logger.info("🛑 Планировщик мониторинга остановлен")
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()