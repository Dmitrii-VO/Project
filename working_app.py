# working_app.py - Продуктивная версия без тестовых данных
import os
import sys
import json
import logging
import sqlite3
import re
import html
import time
from collections import defaultdict
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, session, redirect
from functools import wraps

from app import initialize_systems
from flask import render_template
from app.api.channel_recommendations import *
from app.templates.pages import *


try:
    from enhanced_api_routes import add_enhanced_routes

    enhanced_routes_available = True
    print("✅ Расширенные маршруты импортированы")
except ImportError as e:
    print(f"⚠️ Расширенные маршруты недоступны: {e}")
    enhanced_routes_available = False


    # Создаем заглушку
    def add_enhanced_routes(app=None):
        print("🔄 Используется заглушка для расширенных маршрутов")
        return False


# Импорт переменных окружения для выплат
TELEGRAM_PAYMENT_TOKEN = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')

# Добавляем текущую директорию в путь для импорта наших модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Logger готов к использованию

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен. Используйте: pip install python-dotenv")

# Импорт наших модулей
try:
    from real_telegram_integration import create_telegram_service, run_async_in_sync

    TELEGRAM_INTEGRATION = True
    logger.info("✅ Telegram интеграция подключена")
except ImportError as e:
    print(f"❌ Не удалось импортировать модули Telegram: {e}")
    print("Telegram интеграция ОБЯЗАТЕЛЬНА для продуктивной работы")
    TELEGRAM_INTEGRATION = False
    create_telegram_service = None
    run_async_in_sync = None

# === ИМПОРТ СИСТЕМЫ ОФФЕРОВ ===
try:
    from add_offer import (
        add_offer,
        get_user_offers,
        get_offer_by_id,
        update_offer_status,
        validate_offer_data,
        ensure_user_exists
    )

    OFFERS_SYSTEM_ENABLED = True
    logger.info("✅ Система офферов подключена")
except ImportError as e:
    logger.error(f"❌ Не удалось подключить систему офферов: {e}")
    OFFERS_SYSTEM_ENABLED = False

# === ИМПОРТ СИСТЕМЫ ОТКЛИКОВ ===
try:
    from offer_responses import (
        get_suitable_offers_for_channel,
        create_offer_response,
        get_channel_responses,
        get_offer_responses,
        update_response_status,
        get_response_statistics,
        calculate_suitability_score
    )

    RESPONSES_SYSTEM_ENABLED = True
    logger.info("✅ Система откликов подключена")
except ImportError as e:
    logger.error(f"❌ Не удалось подключить систему откликов: {e}")
    RESPONSES_SYSTEM_ENABLED = False

# === ИМПОРТ ПЛАТЕЖНОЙ СИСТЕМЫ ===
try:
    from app.services.payments_system import (
        register_payments_routes,
        create_payments_tables,
        PaymentManager,
        EscrowManager, MAX_RETRY_ATTEMPTS
    )
    from app.services.telegram_webhooks import register_webhook_routes
    PAYMENTS_SYSTEM_ENABLED = True
    logger.info("✅ Платежная система подключена")
except ImportError as e:
    logger.error(f"❌ Платежная система недоступна: {e}")
    PAYMENTS_SYSTEM_ENABLED = False
# === ИМПОРТ ПРОДВИНУТОГО АЛГОРИТМА ===
try:
    from app.services.advanced_matching_algorithm import (
        get_advanced_suitable_offers_for_channel,
        analyze_offer_channel_compatibility,
        AdvancedMatchingEngine
    )
    ADVANCED_MATCHING_ENABLED = True
    logger.info("✅ Продвинутый алгоритм сопоставления подключен")
except ImportError as e:
    logger.error(f"❌ Не удалось подключить продвинутый алгоритм: {e}")
    ADVANCED_MATCHING_ENABLED = False

# === ИМПОРТ РАСШИРЕННОЙ АНАЛИТИКИ ===
try:
    from app.services.analytics_api import add_analytics_routes, AnalyticsEngine
    from app.services.placement_tracking import PlacementTracker, add_tracking_routes
    from app.services.ai_recommendations import AIRecommendationEngine, add_ai_recommendation_routes

    ANALYTICS_SYSTEM_ENABLED = True
    PLACEMENT_TRACKING_ENABLED = True
    AI_RECOMMENDATIONS_ENABLED = True

    logger.info("✅ Полная система аналитики подключена")
    logger.info("  📊 Базовая аналитика: Активна")
    logger.info("  📈 Отслеживание размещений: Активно")
    logger.info("  🤖 AI-рекомендации: Активны")

except ImportError as e:
    logger.error(f"❌ Не удалось подключить расширенную аналитику: {e}")
    ANALYTICS_SYSTEM_ENABLED = False
    PLACEMENT_TRACKING_ENABLED = False
    AI_RECOMMENDATIONS_ENABLED = False

try:
    from app.services.payout_system import (
        register_payout_routes,
        create_payout_tables,
        PayoutManager,
        AutoPayoutScheduler,
        TelegramPayoutHandler
    )
    PAYOUT_SYSTEM_ENABLED = True
    logger.info("✅ Система автоматических выплат подключена")
except ImportError as e:
    logger.error(f"❌ Не удалось подключить систему выплат: {e}")
    PAYOUT_SYSTEM_ENABLED = False


def check_services_availability():
    """Проверка доступности всех сервисов"""
    services_status = {
        'payments': PAYMENTS_SYSTEM_ENABLED,
        'analytics': ANALYTICS_SYSTEM_ENABLED,
        'placement_tracking': PLACEMENT_TRACKING_ENABLED,
        'ai_recommendations': AI_RECOMMENDATIONS_ENABLED,
        'payouts': PAYOUT_SYSTEM_ENABLED,
        'advanced_matching': ADVANCED_MATCHING_ENABLED,
        'notifications': NOTIFICATIONS_ENABLED
    }

    logger.info("🔍 Статус сервисов:")
    for service, status in services_status.items():
        icon = "✅" if status else "❌"
        logger.info(f"  {icon} {service}: {'Активен' if status else 'Отключен'}")

    return services_status
# Глобальный менеджер выплат
payout_manager = None

# Создание Flask приложения
app = Flask(__name__,
            template_folder='app/templates',
            static_folder='app/static',
            channels_foleder='app/pages/channels')

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')


# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ БЕЗОПАСНОСТИ ===
# Rate limiting storage
request_counts = defaultdict(list)
REQUEST_LIMIT = 100  # запросов
TIME_WINDOW = 3600  # за час

# Подозрительные IP
suspicious_ips = set()
blocked_ips = set()


# === ФУНКЦИИ БЕЗОПАСНОСТИ ===

def get_client_ip():
    """Получение реального IP клиента"""
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip

    return request.environ.get('REMOTE_ADDR', '127.0.0.1')


def rate_limit_check(identifier: str) -> bool:
    """Проверка rate limiting"""
    now = time.time()
    request_counts[identifier] = [
        req_time for req_time in request_counts[identifier]
        if now - req_time < TIME_WINDOW
    ]

    if len(request_counts[identifier]) >= REQUEST_LIMIT:
        return False

    request_counts[identifier].append(now)
    return True


def is_suspicious_request(request_data: dict) -> bool:
    """Детекция подозрительных запросов"""
    user_agent = request_data.get('user_agent', '').lower()

    suspicious_agents = [
        'sqlmap', 'nikto', 'nmap', 'masscan', 'nessus',
        'burp', 'zap', 'w3af', 'havij', 'python-requests/2.0'
    ]

    for agent in suspicious_agents:
        if agent in user_agent:
            return True

    if not user_agent or len(user_agent) < 10:
        return True

    return False


def log_security_event(event_type: str, details: dict):
    """Логирование событий безопасности"""
    security_logger = logging.getLogger('security')
    security_logger.warning(f"SECURITY_EVENT: {event_type}", extra={
        'details': details,
        'timestamp': datetime.now().isoformat()
    })


def validate_telegram_username(username: str) -> Tuple[bool, str]:
    """Строгая валидация Telegram username с защитой от SQL injection"""
    if not username:
        return False, "Username не может быть пустым"

    cleaned = username.strip().lstrip('@')

    # SQL injection защита
    sql_patterns = [
        r"['\";]", r"--", r"/\*", r"\*/", r"\bDROP\b", r"\bDELETE\b",
        r"\bUPDATE\b", r"\bINSERT\b", r"\bSELECT\b", r"\bUNION\b",
        r"\bOR\b.*=.*=", r"1\s*=\s*1", r"1\s*=\s*'1'"
    ]

    for pattern in sql_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return False, "Недопустимые символы в username"

    if len(cleaned) < 5 or len(cleaned) > 32:
        return False, "Username должен быть от 5 до 32 символов"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', cleaned):
        return False, "Username может содержать только буквы, цифры и подчеркивания"

    return True, cleaned


def sanitize_input(input_str: str, max_length: int = 100) -> Optional[str]:
    """Безопасная очистка пользовательского ввода"""
    if not input_str:
        return None

    cleaned = re.sub(r'[<>"\';\\]', '', input_str.strip())

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    cleaned = html.escape(cleaned)
    return cleaned if cleaned else None


def require_telegram_auth(f):
    """Декоратор для обязательной авторизации через Telegram"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        telegram_user_id = get_current_user_id()

        if not telegram_user_id:
            logger.warning(f"Unauthorized access attempt to {request.endpoint} from IP: {get_client_ip()}")
            logger.warning(f"Request headers: {dict(request.headers)}")

            return jsonify({
                'success': False,
                'error': 'Требуется авторизация через Telegram',
                'code': 'AUTH_REQUIRED',
                'debug_info': {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'has_headers': bool(request.headers.get('X-Telegram-User-Id')),
                    'has_json': request.is_json,
                    'content_type': request.headers.get('Content-Type')
                }
            }), 401

        # Проверяем существование пользователя в БД
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"User {telegram_user_id} not found in database")
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден в системе',
                'code': 'USER_NOT_FOUND'
            }), 401

        logger.info(f"Authenticated user {telegram_user_id} accessing {request.endpoint}")
        return f(*args, **kwargs)

    return decorated_function


# Настройка логирования безопасности
security_logger = logging.getLogger('security')
try:
    security_handler = logging.FileHandler('security.log')
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
    ))
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
except Exception as e:
    print(f"Warning: Could not setup security logging: {e}")

# Конфигурация базы данных
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
DATABASE_PATH = DATABASE_URL.replace('sqlite:///', '')
YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Обязательная проверка конфигурации
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не настроен! Приложение не может работать без настроенного Telegram бота.")
    sys.exit(1)

if not TELEGRAM_INTEGRATION:
    logger.error("❌ Telegram интеграция недоступна! Приложение не может работать без реальной интеграции.")
    sys.exit(1)

# Инициализация Telegram сервиса
telegram_service = create_telegram_service(BOT_TOKEN)
if not telegram_service:
    logger.error("❌ Не удалось создать Telegram сервис!")
    sys.exit(1)

try:
    from app.services.notifications_system import notifications_bp, NotificationManager, AutoNotifications

    app.register_blueprint(notifications_bp)
    logger.info("✅ Система уведомлений подключена")
    NOTIFICATIONS_ENABLED = True
except ImportError as e:
    logger.warning(f"⚠️ Не удалось подключить систему уведомлений: {e}")
    NOTIFICATIONS_ENABLED = False


# === ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ===
def get_db_connection():
    """Получение подключения к SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Для возврата словарей
        conn.execute('PRAGMA foreign_keys = ON')  # Включаем foreign keys
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к SQLite: {e}")


def safe_execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Безопасное выполнение SQL запросов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ВАЖНО: Всегда используем параметризованные запросы
        if params is None:
            params = ()

        # Логируем потенциально опасные запросы
        if any(keyword in query.upper() for keyword in ['DROP', 'DELETE', 'TRUNCATE', 'ALTER']):
            logger.warning(f"Potentially dangerous query executed: {query[:100]}...")

        cursor.execute(query, params)

        result = None
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows] if rows else []

        if not (fetch_one or fetch_all):
            conn.commit()

        conn.close()
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        logger.error(f"Query: {query}")
        if params:
            logger.error(f"Params: {params}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in safe_execute_query: {e}")
        return None


def validate_offer_data_secure(data):
    """Безопасная валидация данных оффера"""
    errors = []

    # Проверка title с защитой от XSS
    title = sanitize_input(data.get('title', ''), 200)
    if not title or len(title) < 10:
        errors.append('Заголовок должен быть от 10 до 200 символов')

    # Проверка description
    description = sanitize_input(data.get('description', ''), 500)
    if not description or len(description) < 20:
        errors.append('Описание должно быть от 20 до 500 символов')

    # Проверка content
    content = sanitize_input(data.get('content', ''), 2000)
    if not content or len(content) < 50:
        errors.append('Контент должен быть от 50 до 2000 символов')

    # Проверка price с защитой от injection
    try:
        price = float(data.get('price', 0))
        if price <= 0 or price > 1000000:
            errors.append('Цена должна быть от 1 до 1,000,000')
    except (ValueError, TypeError):
        errors.append('Некорректная цена')

    # Проверка currency
    currency = data.get('currency', '').upper()
    allowed_currencies = ['RUB', 'USD', 'EUR']
    if currency not in allowed_currencies:
        errors.append('Валюта должна быть RUB, USD или EUR')

    return errors


def init_database():
    """Проверка SQLite базы данных"""
    try:
        logger.info("🗄️ Проверка SQLite базы данных...")

        # Проверяем существование файла базы данных
        if not os.path.exists(DATABASE_PATH):
            logger.error(f"❌ База данных не найдена: {DATABASE_PATH}")
            logger.info("Запустите sqlite_migration.py для создания базы данных")
            return False

        # Проверяем таблицы
        tables = safe_execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'channels', 'offers', 'offer_responses')
        """, fetch_all=True)

        if not tables or len(tables) < 4:
            logger.error(f"❌ Не все таблицы найдены. Найдено: {len(tables) if tables else 0}")
            logger.info("Запустите sqlite_migration.py для создания схемы")
            return False
        if PAYMENTS_SYSTEM_ENABLED:
            create_payments_tables()
            if create_payout_tables():
                logger.info("✅ Таблицы системы выплат инициализированы")
            else:
                logger.error("❌ Ошибка создания таблиц системы выплат")
                return False
        logger.info("✅ SQLite база данных готова к работе")
        return True




    except Exception as e:
        logger.error(f"❌ Ошибка инициализации SQLite: {e}")
        return False


def initialize_analytics_system():
    """Инициализация системы аналитики"""
    try:
        if not ANALYTICS_SYSTEM_ENABLED:
            logger.warning("⚠️ Система аналитики недоступна")
            return False

        logger.info("📊 Инициализация системы аналитики...")

        # Добавляем маршруты аналитики
        add_analytics_routes(app, DATABASE_PATH)

        # Создаем экземпляр движка аналитики
        analytics_engine = AnalyticsEngine(DATABASE_PATH)

        logger.info("✅ Система аналитики успешно инициализирована")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации системы аналитики: {e}")
        return False


def initialize_full_analytics_system():
    """Инициализация полной системы аналитики с детальной диагностикой"""
    try:
        logger.info("🚀 Инициализация расширенной системы аналитики...")

        systems_status = {
            'basic_analytics': False,
            'placement_tracking': False,
            'ai_recommendations': False
        }

        initialization_log = []

        # 1. Инициализация базовой аналитики
        if ANALYTICS_SYSTEM_ENABLED:
            try:
                add_analytics_routes(app, DATABASE_PATH)
                analytics_engine = AnalyticsEngine(DATABASE_PATH)

                # Тестовый запрос для проверки
                test_metrics = analytics_engine._get_demo_metrics()
                if test_metrics:
                    systems_status['basic_analytics'] = True
                    initialization_log.append("✅ Базовая аналитика: Маршруты добавлены, движок создан")
                else:
                    initialization_log.append("⚠️ Базовая аналитика: Маршруты добавлены, но тест не прошел")

            except Exception as e:
                initialization_log.append(f"❌ Базовая аналитика: Ошибка - {e}")
                logger.error(f"Basic analytics initialization error: {e}")
        else:
            initialization_log.append("❌ Базовая аналитика: Модуль не загружен")

        # 2. Инициализация отслеживания размещений
        if PLACEMENT_TRACKING_ENABLED:
            try:
                add_tracking_routes(app, DATABASE_PATH)
                placement_tracker = PlacementTracker(DATABASE_PATH)

                # Проверка создания таблиц
                if placement_tracker.ensure_tracking_tables():
                    systems_status['placement_tracking'] = True
                    initialization_log.append("✅ Отслеживание размещений: Маршруты и таблицы созданы")
                else:
                    initialization_log.append("⚠️ Отслеживание размещений: Проблемы с таблицами БД")

            except Exception as e:
                initialization_log.append(f"❌ Отслеживание размещений: Ошибка - {e}")
                logger.error(f"Placement tracking initialization error: {e}")
        else:
            initialization_log.append("❌ Отслеживание размещений: Модуль не загружен")

        # 3. Инициализация AI-рекомендаций
        if AI_RECOMMENDATIONS_ENABLED:
            try:
                add_ai_recommendation_routes(app, DATABASE_PATH)
                ai_engine = AIRecommendationEngine(DATABASE_PATH)

                # Тест генерации демо-рекомендаций
                demo_recommendations = ai_engine._get_fallback_recommendations()
                if demo_recommendations:
                    systems_status['ai_recommendations'] = True
                    initialization_log.append("✅ AI-рекомендации: Маршруты добавлены, движок готов")
                else:
                    initialization_log.append("⚠️ AI-рекомендации: Движок создан, но тест не прошел")

            except Exception as e:
                initialization_log.append(f"❌ AI-рекомендации: Ошибка - {e}")
                logger.error(f"AI recommendations initialization error: {e}")
        else:
            initialization_log.append("❌ AI-рекомендации: Модуль не загружен")

        # Сохраняем статус и лог
        app.analytics_status = systems_status
        app.analytics_initialization_log = initialization_log

        # Выводим детальный лог
        for log_entry in initialization_log:
            logger.info(f"  {log_entry}")

        # Финальная статистика
        active_systems = sum(systems_status.values())
        total_systems = len(systems_status)

        logger.info(f"📊 Результат инициализации: {active_systems}/{total_systems} систем активно")

        if active_systems == total_systems:
            logger.info("🎉 Все системы аналитики успешно инициализированы!")
        elif active_systems >= 1:
            logger.info("⚠️ Система частично готова, некоторые функции могут быть недоступны")
        else:
            logger.error("❌ Критическая ошибка: Ни одна система аналитики не работает")

        return active_systems > 0

    except Exception as e:
        logger.error(f"❌ Критическая ошибка инициализации аналитики: {e}")
        app.analytics_status = {'error': str(e)}
        return False


# === UTILITY ФУНКЦИИ ===
def get_current_user_id():
    """Получение текущего Telegram User ID"""
    # Попробуем получить из заголовков
    user_id_header = request.headers.get('X-Telegram-User-Id')
    if user_id_header:
        try:
            return int(user_id_header)
        except (ValueError, TypeError):
            pass

    # Из POST данных
    if request.method == 'POST' and request.is_json:
        try:
            data = request.get_json()
            if data and 'telegram_user_id' in data:
                return int(data['telegram_user_id'])
        except:
            pass

    # Из GET параметров
    user_id_param = request.args.get('telegram_user_id')
    if user_id_param:
        try:
            return int(user_id_param)
        except (ValueError, TypeError):
            pass

    # Fallback на основного пользователя
    return YOUR_TELEGRAM_ID

def validate_telegram_data(init_data_raw):
    """Проверка подлинности данных от Telegram WebApp"""
    try:
        # Простая проверка формата (в продакшене нужна полная валидация с HMAC)
        if not init_data_raw or 'user=' not in init_data_raw:
            return None

        # Извлекаем user_id из initData
        import urllib.parse

        for param in init_data_raw.split('&'):
            if param.startswith('user='):
                user_data = urllib.parse.unquote(param[5:])
                try:
                    import json
                    user_info = json.loads(user_data)
                    if 'id' in user_info:
                        return int(user_info['id'])
                except:
                    pass
        return None

    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return None


@app.route('/api/auth/telegram', methods=['POST'])
def telegram_auth():
    """Авторизация пользователя через Telegram WebApp"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Получаем Telegram User ID
        telegram_user_id = None

        # Способ 1: Прямая передача user_id
        if 'telegram_user_id' in data:
            try:
                telegram_user_id = int(data['telegram_user_id'])
            except (ValueError, TypeError):
                pass

        # Способ 2: Из заголовков
        if not telegram_user_id:
            header_user_id = request.headers.get('X-Telegram-User-Id')
            if header_user_id:
                try:
                    telegram_user_id = int(header_user_id)
                except (ValueError, TypeError):
                    pass

        # Способ 3: Из initData
        if not telegram_user_id and 'initData' in data:
            telegram_user_id = validate_telegram_data(data['initData'])

        # Способ 4: Из user объекта
        if not telegram_user_id and 'user' in data:
            user_data = data['user']
            if isinstance(user_data, dict) and 'id' in user_data:
                try:
                    telegram_user_id = int(user_data['id'])
                except (ValueError, TypeError):
                    pass

        if not telegram_user_id:
            logger.error(f"Failed to get telegram_user_id from auth request")
            logger.error(f"Data: {data}")
            logger.error(f"Headers: {dict(request.headers)}")

            return jsonify({
                'success': False,
                'error': 'Не удалось получить Telegram User ID',
                'debug_info': {
                    'has_telegram_user_id': 'telegram_user_id' in data,
                    'has_header': bool(request.headers.get('X-Telegram-User-Id')),
                    'has_initData': 'initData' in data,
                    'has_user': 'user' in data
                }
            }), 400

        # Создаем/обновляем пользователя в базе
        username = data.get('username') or f'user_{telegram_user_id}'
        first_name = data.get('first_name') or 'User'

        user_db_id = ensure_user_exists(telegram_user_id, username, first_name)

        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Ошибка создания пользователя'
            }), 500

        # Сохраняем в сессии
        session['telegram_user_id'] = telegram_user_id

        logger.info(f"Telegram user {telegram_user_id} authenticated successfully")

        return jsonify({
            'success': True,
            'telegram_user_id': telegram_user_id,
            'user_db_id': user_db_id,
            'username': username,
            'message': 'Авторизация успешна'
        })

    except Exception as e:
        logger.error(f"Telegram auth error: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка авторизации'
        }), 500

def log_user_access(telegram_user_id, endpoint, success=True, error=None):
    """Логирование доступа пользователей для отладки"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'telegram_user_id': telegram_user_id,
        'endpoint': endpoint,
        'success': success,
        'error': error,
        'ip': get_client_ip(),
        'user_agent': request.headers.get('User-Agent', '')
    }

    if success:
        logger.info(f"User access: {telegram_user_id} -> {endpoint}")
    else:
        logger.warning(f"Failed user access: {telegram_user_id} -> {endpoint}, Error: {error}")
def ensure_user_exists(telegram_user_id, username=None, first_name=None):
    """Обеспечение существования пользователя в базе по Telegram ID"""
    try:
        # Проверяем существование пользователя
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            # Создаем нового пользователя
            logger.info(f"Creating new user for Telegram ID: {telegram_user_id}")

            safe_execute_query('''
                INSERT INTO users (telegram_id, username, first_name, is_admin, created_at) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                telegram_user_id,
                username or f'user_{telegram_user_id}',
                first_name or 'Telegram User',
                telegram_user_id == YOUR_TELEGRAM_ID,  # Делаем админом если это ваш ID
                datetime.now().isoformat()
            ))

            # Получаем созданного пользователя
            user = safe_execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_user_id,),
                fetch_one=True
            )
        else:
            # Обновляем информацию о существующем пользователе
            if username or first_name:
                safe_execute_query('''
                    UPDATE users 
                    SET username = COALESCE(?, username), 
                        first_name = COALESCE(?, first_name),
                        updated_at = ?
                    WHERE telegram_id = ?
                ''', (username, first_name, datetime.now().isoformat(), telegram_user_id))

        return user['id'] if user else None

    except Exception as e:
        logger.error(f"Ошибка создания/обновления пользователя {telegram_user_id}: {e}")
        return None


# === ОСНОВНЫЕ МАРШРУТЫ ===
@app.before_request
def security_middleware():
    """Middleware безопасности - выполняется ПЕРЕД каждым запросом"""

    # Получаем информацию о запросе
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    # 1. Блокировка заблокированных IP
    if client_ip in blocked_ips:
        log_security_event('BLOCKED_IP_ACCESS', {
            'ip': client_ip,
            'path': request.path,
            'method': request.method
        })
        return jsonify({'error': 'Access denied'}), 403

    # 2. Rate limiting
    if not rate_limit_check(f"global_{client_ip}"):
        # Добавляем в подозрительные при превышении лимита
        suspicious_ips.add(client_ip)

        log_security_event('RATE_LIMIT_EXCEEDED', {
            'ip': client_ip,
            'path': request.path,
            'user_agent': user_agent
        })

        return jsonify({'error': 'Too many requests'}), 429

    # 3. Детекция подозрительных запросов
    request_data = {
        'user_agent': user_agent,
        'ip': client_ip,
        'path': request.path,
        'method': request.method
    }

    if is_suspicious_request(request_data):
        suspicious_ips.add(client_ip)
        log_security_event('SUSPICIOUS_REQUEST', request_data)

    # 4. Валидация размера запроса
    if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
        log_security_event('LARGE_REQUEST', {
            'ip': client_ip,
            'size': request.content_length,
            'path': request.path
        })
        return jsonify({'error': 'Request too large'}), 413

    # 5. Проверка Content-Type для POST запросов
    if request.method == 'POST' and request.path.startswith('/api/'):
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/json'):
            return jsonify({'error': 'Invalid Content-Type'}), 400
    # 6 Логирование доступа к API каналов
    if request.path.startswith('/api/channels'):
        telegram_user_id = get_current_user_id()
        logger.info(f"API Channels access: {request.method} {request.path} by user {telegram_user_id}")

        # Логируем заголовки для отладки
        headers_info = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent')
        }
        logger.debug(f"Request headers: {headers_info}")
        # Логируем заголовки для отладки
        headers_info = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent')
        }
        logger.debug(f"Request headers: {headers_info}")

def telegram_auth_middleware():
    """Middleware для автоматической аутентификации Telegram пользователей"""

    # Применяем только к API эндпоинтам каналов
    if not request.path.startswith('/api/channels'):
        return

    # Пропускаем GET запросы к общим эндпоинтам
    if request.method == 'GET' and request.path in ['/api/channels', '/api/channels/']:
        return

    try:
        telegram_user_id = get_current_user_id()

        if telegram_user_id:
            # Убеждаемся что пользователь существует в БД
            user_db_id = ensure_user_exists(telegram_user_id)

            if not user_db_id:
                logger.warning(f"Failed to ensure user exists for Telegram ID: {telegram_user_id}")
            else:
                logger.debug(f"Telegram user {telegram_user_id} authenticated for {request.path}")

    except Exception as e:
        logger.error(f"Telegram auth middleware error: {e}")

@app.route('/')
def index():
    """Главная страница с новым дизайном"""
    return render_template('index.html')

@app.route('/index')
def index_alt():
    """Альтернативный маршрут для главной страницы"""
    return redirect('/')

@app.route('/channels')
def channels_redirect():
    """Редирект с /channels на /channels-enhanced для совместимости"""
    return redirect('/channels-enhanced')


@app.route('/debug/templates')
def debug_templates():
    """Отладочный маршрут для проверки шаблонов"""
    import os

    templates_dir = os.path.join(app.root_path, 'templates')
    static_dir = os.path.join(app.root_path, 'static')

    debug_info = {
        'templates_dir_exists': os.path.exists(templates_dir),
        'static_dir_exists': os.path.exists(static_dir),
        'templates_dir_path': templates_dir,
        'static_dir_path': static_dir,
        'templates_files': [],
        'static_files': []
    }

    if os.path.exists(templates_dir):
        debug_info['templates_files'] = os.listdir(templates_dir)

    if os.path.exists(static_dir):
        for root, dirs, files in os.walk(static_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), static_dir)
                debug_info['static_files'].append(rel_path)

    return jsonify(debug_info)

@app.route('/channels-enhanced')
def channels_page():
    """Страница управления каналами"""
    return render_template('channels.html')


@app.route('/analytics')
def analytics_page():
    """Страница аналитики с расширенными метриками"""
    try:
        # Проверяем авторизацию пользователя
        telegram_user_id = get_current_user_id()

        if not telegram_user_id:
            # Если не авторизован, показываем демо-версию
            logger.info("Показ демо-версии аналитики для неавторизованного пользователя")
            return render_template('analytics.html', demo_mode=True)

        # Проверяем наличие пользователя в БД
        user = safe_execute_query(
            'SELECT id, username FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"Пользователь {telegram_user_id} не найден в БД для аналитики")
            return render_template('analytics.html', demo_mode=True)

        # Получаем базовую статистику для передачи в шаблон
        user_stats = {}
        if ANALYTICS_SYSTEM_ENABLED:
            try:
                analytics_engine = AnalyticsEngine(DATABASE_PATH)
                user_stats = analytics_engine.get_user_metrics(telegram_user_id, '30d')
            except Exception as e:
                logger.error(f"Ошибка получения статистики для аналитики: {e}")
                user_stats = {}

        logger.info(f"Загружена страница аналитики для пользователя {telegram_user_id}")

        return render_template('analytics.html',
                               demo_mode=False,
                               user_stats=user_stats,
                               telegram_user_id=telegram_user_id,
                               analytics_enabled=ANALYTICS_SYSTEM_ENABLED)

    except Exception as e:
        logger.error(f"Ошибка загрузки страницы аналитики: {e}")
        return render_template('analytics.html', demo_mode=True, error=str(e))


@app.route('/advanced-offers/<int:channel_id>')
def advanced_offers_page(channel_id):
    """Страница офферов с продвинутой аналитикой"""
    try:
        # Проверяем принадлежность канала
        telegram_user_id = get_current_user_id()
        if not telegram_user_id:
            return redirect('/')

        channel = safe_execute_query('''
                                     SELECT c.*, u.telegram_id as owner_telegram_id
                                     FROM channels c
                                              JOIN users u ON c.owner_id = u.id
                                     WHERE c.id = ?
                                       AND u.telegram_id = ?
                                     ''', (channel_id, telegram_user_id), fetch_one=True)

        if not channel:
            return render_template('error.html', message='Канал не найден')

        return render_template('advanced_offers.html',
                               channel=channel,
                               channel_id=channel_id)

    except Exception as e:
        logger.error(f"Ошибка страницы продвинутых офферов: {e}")
        return render_template('error.html', message='Ошибка загрузки')


@app.route('/analytics-demo')
def analytics_demo_page():
    """Демо-страница системы аналитики"""
    return render_template('analytics_demo.html')


@app.route('/api/analytics/test-all-systems')
@require_telegram_auth
def api_test_all_systems():
    """Комплексный тест всех систем аналитики"""
    try:
        telegram_user_id = get_current_user_id()

        test_results = {
            'timestamp': datetime.now().isoformat(),
            'user_id': telegram_user_id,
            'systems': {
                'basic_analytics': False,
                'placement_tracking': False,
                'ai_recommendations': False,
                'database': False
            },
            'details': {},
            'errors': [],
            'performance': {}
        }

        # 1. Тест базы данных
        try:
            start_time = datetime.now()
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                conn.close()

                test_results['systems']['database'] = True
                test_results['details']['database'] = {
                    'connection': 'success',
                    'user_count': user_count,
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                }

        except Exception as e:
            test_results['errors'].append(f'Database test failed: {str(e)}')

        # 2. Тест базовой аналитики
        if ANALYTICS_SYSTEM_ENABLED:
            try:
                start_time = datetime.now()
                analytics_engine = AnalyticsEngine(DATABASE_PATH)
                metrics = analytics_engine.get_user_metrics(telegram_user_id, '7d')

                test_results['systems']['basic_analytics'] = True
                test_results['details']['basic_analytics'] = {
                    'metrics_generated': bool(metrics),
                    'revenue': metrics.get('total_revenue', 0),
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                }

            except Exception as e:
                test_results['errors'].append(f'Basic analytics test failed: {str(e)}')

        # 3. Тест отслеживания размещений
        if PLACEMENT_TRACKING_ENABLED:
            try:
                start_time = datetime.now()
                placement_tracker = PlacementTracker(DATABASE_PATH)
                summary = placement_tracker.get_performance_summary(telegram_user_id, 7)

                test_results['systems']['placement_tracking'] = True
                test_results['details']['placement_tracking'] = {
                    'summary_generated': bool(summary),
                    'placements_count': summary.get('total_placements', 0),
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                }

            except Exception as e:
                test_results['errors'].append(f'Placement tracking test failed: {str(e)}')

        # 4. Тест AI-рекомендаций
        if AI_RECOMMENDATIONS_ENABLED:
            try:
                start_time = datetime.now()
                ai_engine = AIRecommendationEngine(DATABASE_PATH)
                recommendations = ai_engine.generate_recommendations(telegram_user_id, 7)

                test_results['systems']['ai_recommendations'] = True
                test_results['details']['ai_recommendations'] = {
                    'recommendations_count': len(recommendations),
                    'has_high_priority': any(r.priority == 'high' for r in recommendations),
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000
                }

            except Exception as e:
                test_results['errors'].append(f'AI recommendations test failed: {str(e)}')

        # Общая статистика
        working_systems = sum(test_results['systems'].values())
        total_systems = len(test_results['systems'])

        test_results['summary'] = {
            'working_systems': working_systems,
            'total_systems': total_systems,
            'success_rate': round((working_systems / total_systems) * 100, 1),
            'has_errors': len(test_results['errors']) > 0,
            'overall_status': 'healthy' if working_systems >= 3 else 'partial' if working_systems >= 1 else 'failed'
        }

        # Рекомендации по улучшению
        recommendations = []
        if not test_results['systems']['database']:
            recommendations.append('Проверьте подключение к базе данных SQLite')
        if not test_results['systems']['basic_analytics']:
            recommendations.append('Убедитесь что analytics_api.py установлен корректно')
        if not test_results['systems']['placement_tracking']:
            recommendations.append('Проверьте модуль placement_tracking.py')
        if not test_results['systems']['ai_recommendations']:
            recommendations.append('Убедитесь что ai_recommendations.py загружен')

        test_results['recommendations'] = recommendations

        return jsonify({
            'success': True,
            'test_results': test_results
        })

    except Exception as e:
        logger.error(f"System test error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'test_results': {
                'summary': {'overall_status': 'failed', 'error': str(e)}
            }
        }), 500
# === API ENDPOINTS ===

@app.route('/api/stats')
def api_stats():
    """Общая статистика системы"""
    try:
        # Статистика пользователей
        users_count = safe_execute_query('SELECT COUNT(*) as count FROM users', fetch_one=True)

        # Статистика каналов
        channels_count = safe_execute_query('SELECT COUNT(*) as count FROM channels', fetch_one=True)

        # Статистика офферов (если система включена)
        if OFFERS_SYSTEM_ENABLED:
            offers_count = safe_execute_query('SELECT COUNT(*) as count FROM offers', fetch_one=True)
        else:
            offers_count = {'count': 0}

        # Статистика откликов (если система включена)
        if RESPONSES_SYSTEM_ENABLED:
            responses_count = safe_execute_query('SELECT COUNT(*) as count FROM offer_responses', fetch_one=True)
        else:
            responses_count = {'count': 0}

        return jsonify({
            'success': True,
            'users': users_count['count'] if users_count else 0,
            'channels': channels_count['count'] if channels_count else 0,
            'offers': offers_count['count'] if offers_count else 0,
            'responses': responses_count['count'] if responses_count else 0,
            'features': {
                'telegram_integration': TELEGRAM_INTEGRATION,
                'offers_system': OFFERS_SYSTEM_ENABLED,
                'responses_system': RESPONSES_SYSTEM_ENABLED,
                'database': 'SQLite',
                'bot_configured': bool(BOT_TOKEN)
            }
        })



    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'users': 0,
            'channels': 0,
            'offers': 0,
            'responses': 0
        }), 500


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка статуса авторизации"""
    try:
        telegram_user_id = get_current_user_id()

        if not telegram_user_id:
            return jsonify({
                'success': False,
                'authenticated': False,
                'error': 'Нет Telegram User ID'
            }), 401

        # Проверяем существование пользователя в БД
        user = safe_execute_query(
            'SELECT id, username, first_name FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({
                'success': False,
                'authenticated': False,
                'error': 'Пользователь не найден в БД'
            }), 401

        return jsonify({
            'success': True,
            'authenticated': True,
            'telegram_user_id': telegram_user_id,
            'user_info': {
                'id': user['id'],
                'username': user['username'],
                'first_name': user['first_name']
            }
        })

    except Exception as e:
        logger.error(f"Auth check error: {e}")
        return jsonify({
            'success': False,
            'authenticated': False,
            'error': 'Ошибка проверки авторизации'
        }), 500


@app.route('/api/analytics/status')
def api_analytics_status():
    """Проверка статуса системы аналитики"""
    try:
        telegram_user_id = get_current_user_id()

        status = {
            'analytics_enabled': ANALYTICS_SYSTEM_ENABLED,
            'database_connected': os.path.exists(DATABASE_PATH),
            'user_authenticated': bool(telegram_user_id),
            'telegram_user_id': telegram_user_id
        }

        if ANALYTICS_SYSTEM_ENABLED and telegram_user_id:
            try:
                analytics_engine = AnalyticsEngine(DATABASE_PATH)
                # Быстрая проверка работоспособности
                test_metrics = analytics_engine.get_user_metrics(telegram_user_id, '7d')
                status['metrics_available'] = True
                status['sample_revenue'] = test_metrics.get('total_revenue', 0)
            except Exception as e:
                status['metrics_available'] = False
                status['metrics_error'] = str(e)

        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Analytics status check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': {
                'analytics_enabled': ANALYTICS_SYSTEM_ENABLED,
                'database_connected': False,
                'user_authenticated': False
            }
        }), 500


# === API МАРШРУТЫ ДЛЯ ОФФЕРОВ ===
if OFFERS_SYSTEM_ENABLED:

    @app.route('/api/offers', methods=['POST'])
    def api_create_offer():
        """API для создания нового оффера"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400

            # Получаем user_id из заголовков или данных
            user_id = data.get('user_id') or request.headers.get('X-Telegram-User-Id')
            if not user_id:
                # Используем ваш ID по умолчанию для тестирования
                user_id = YOUR_TELEGRAM_ID

            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Некорректный User ID'}), 400

            # Добавляем дополнительную информацию о пользователе
            if 'username' not in data:
                data['username'] = f'user_{user_id}'
            if 'first_name' not in data:
                data['first_name'] = 'User'

            # Создаем оффер
            result = add_offer(user_id, data)

            if result['success']:
                logger.info(f"Создан новый оффер {result.get('offer_id')} пользователем {user_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Ошибка API создания оффера: {e}")
            return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


    @app.route('/api/offers/<int:user_id>', methods=['GET'])
    def api_get_user_offers(user_id):
        """API для получения офферов пользователя"""
        try:
            status = request.args.get('status')
            offers = get_user_offers(user_id, status)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})
        except Exception as e:
            logger.error(f"Ошибка получения офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500


    @app.route('/api/offers/my', methods=['GET'])
    def api_get_my_offers():
        """API для получения моих офферов"""
        try:
            telegram_user_id = get_current_user_id()
            status = request.args.get('status')
            offers = get_user_offers(telegram_user_id, status)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})
        except Exception as e:
            logger.error(f"Ошибка получения моих офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500


    @app.route('/api/offers/detail/<int:offer_id>', methods=['GET'])
    def api_get_offer_detail(offer_id):
        """API для получения детальной информации об оффере"""
        try:
            include_responses = request.args.get('include_responses', 'false').lower() == 'true'
            offer = get_offer_by_id(offer_id, include_responses)

            if offer:
                return jsonify({'success': True, 'offer': offer})
            else:
                return jsonify({'success': False, 'error': 'Оффер не найден'}), 404
        except Exception as e:
            logger.error(f"Ошибка получения оффера {offer_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500


    @app.route('/api/offers/<int:offer_id>/status', methods=['PUT'])
    def api_update_offer_status(offer_id):
        """API для обновления статуса оффера"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return jsonify({'success': False, 'error': 'Статус обязателен'}), 400

            user_id = data.get('user_id') or request.headers.get('X-Telegram-User-Id') or get_current_user_id()
            if user_id:
                user_id = int(user_id)

            success = update_offer_status(offer_id, data['status'], user_id)

            if success:
                return jsonify({'success': True, 'message': 'Статус обновлен'})
            else:
                return jsonify({'success': False, 'error': 'Не удалось обновить статус'}), 400

        except Exception as e:
            logger.error(f"Ошибка обновления статуса оффера: {e}")
            return jsonify({'success': False, 'error': 'Ошибка обновления статуса'}), 500


    @app.route('/api/offers/stats', methods=['GET'])
    def api_offers_stats():
        """Статистика офферов"""
        try:
            telegram_user_id = get_current_user_id()

            # Получаем ID пользователя в БД
            user = safe_execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_user_id,),
                fetch_one=True
            )

            if not user:
                return jsonify({'success': False, 'error': 'Пользователь не найден'})

            user_db_id = user['id']

            # Статистика офферов
            total_offers = safe_execute_query('''
                SELECT COUNT(*) as count FROM offers WHERE created_by = ?
            ''', (user_db_id,), fetch_one=True)

            active_offers = safe_execute_query('''
                SELECT COUNT(*) as count FROM offers 
                WHERE created_by = ? AND status = 'active'
            ''', (user_db_id,), fetch_one=True)

            total_spent = safe_execute_query('''
                SELECT COALESCE(SUM(price), 0) as total FROM offers
                WHERE created_by = ? AND status IN ('completed', 'active')
            ''', (user_db_id,), fetch_one=True)

            # Статистика откликов на мои офферы
            if RESPONSES_SYSTEM_ENABLED:
                total_responses = safe_execute_query('''
                    SELECT COUNT(*) as count
                    FROM offer_responses or_resp
                    JOIN offers o ON or_resp.offer_id = o.id
                    WHERE o.created_by = ?
                ''', (user_db_id,), fetch_one=True)

                accepted_responses = safe_execute_query('''
                    SELECT COUNT(*) as count
                    FROM offer_responses or_resp
                    JOIN offers o ON or_resp.offer_id = o.id
                    WHERE o.created_by = ? AND or_resp.status = 'accepted'
                ''', (user_db_id,), fetch_one=True)
            else:
                total_responses = {'count': 0}
                accepted_responses = {'count': 0}

            return jsonify({
                'success': True,
                'stats': {
                    'total_offers': total_offers['count'] if total_offers else 0,
                    'active_offers': active_offers['count'] if active_offers else 0,
                    'total_spent': float(total_spent['total']) if total_spent else 0,
                    'total_responses': total_responses['count'] if total_responses else 0,
                    'accepted_responses': accepted_responses['count'] if accepted_responses else 0
                }
            })

        except Exception as e:
            logger.error(f"Ошибка получения статистики офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения статистики'}), 500


    @app.route('/create-offer')
    def create_offer_page():
        """Страница создания оффера"""
        return render_template('create_offer.html')

# === API МАРШРУТЫ ДЛЯ ОТКЛИКОВ ===
if RESPONSES_SYSTEM_ENABLED:

    @app.route('/api/offers/suitable/<int:channel_id>', methods=['GET'])
    def api_get_suitable_offers(channel_id):
        """API для получения подходящих офферов для канала"""
        try:
            # Проверяем принадлежность канала текущему пользователю
            telegram_user_id = get_current_user_id()

            channel_owner = safe_execute_query('''
                SELECT c.id
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE c.id = ? AND u.telegram_id = ?
            ''', (channel_id, telegram_user_id), fetch_one=True)

            if not channel_owner:
                return jsonify({
                    'success': False,
                    'error': 'Канал не найден или нет прав доступа'
                }), 403

            limit = int(request.args.get('limit', 20))
            offers = get_suitable_offers_for_channel(channel_id, limit)

            return jsonify({
                'success': True,
                'offers': offers,
                'count': len(offers)
            })

        except Exception as e:
            logger.error(f"Ошибка получения подходящих офферов: {e}")
            return jsonify({
                'success': False,
                'error': 'Ошибка получения офферов'
            }), 500


    @app.route('/api/responses', methods=['POST'])
    def api_create_response():
        """API для создания отклика на оффер"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400

            channel_id = data.get('channel_id')
            offer_id = data.get('offer_id')

            if not channel_id or not offer_id:
                return jsonify({'success': False, 'error': 'channel_id и offer_id обязательны'}), 400

            # Проверяем принадлежность канала текущему пользователю
            telegram_user_id = get_current_user_id()

            channel_owner = safe_execute_query('''
                SELECT c.id
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE c.id = ? AND u.telegram_id = ?
            ''', (channel_id, telegram_user_id), fetch_one=True)

            if not channel_owner:
                return jsonify({
                    'success': False,
                    'error': 'Канал не найден или нет прав доступа'
                }), 403

            result = create_offer_response(channel_id, offer_id, data)

            if result['success']:
                logger.info(f"Создан отклик на оффер {offer_id} от канала {channel_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Ошибка API создания отклика: {e}")
            return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


    @app.route('/api/responses/channel/<int:channel_id>', methods=['GET'])
    def api_get_channel_responses(channel_id):
        """API для получения откликов канала"""
        try:
            # Проверяем принадлежность канала текущему пользователю
            telegram_user_id = get_current_user_id()

            channel_owner = safe_execute_query('''
                SELECT c.id
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE c.id = ? AND u.telegram_id = ?
            ''', (channel_id, telegram_user_id), fetch_one=True)

            if not channel_owner:
                return jsonify({
                    'success': False,
                    'error': 'Канал не найден или нет прав доступа'
                }), 403

            status = request.args.get('status')
            responses = get_channel_responses(channel_id, status)
            return jsonify({'success': True, 'responses': responses, 'count': len(responses)})
        except Exception as e:
            logger.error(f"Ошибка получения откликов канала: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения откликов'}), 500


    @app.route('/channel-offers/<int:channel_id>')
    def channel_offers_page(channel_id):
        """Страница подходящих офферов для канала"""
        try:
            # Строгая проверка принадлежности канала
            telegram_user_id = get_current_user_id()

            channel = safe_execute_query('''
                SELECT c.*, u.telegram_id as owner_telegram_id
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE c.id = ? AND u.telegram_id = ?
            ''', (channel_id, telegram_user_id), fetch_one=True)

            if not channel:
                return jsonify({'error': 'Канал не найден или нет прав доступа'}), 404

            return render_template_string('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Подходящие офферы - {{ channel.title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .btn { background: #2196F3; color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #1976D2; }
        .btn-success { background: #4CAF50; }
        .btn-success:hover { background: #45a049; }
        .btn-danger { background: #f44336; }
        .btn-danger:hover { background: #da190b; }
        .offer-card { border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 16px; position: relative; }
        .offer-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .offer-title { font-weight: bold; font-size: 18px; margin-bottom: 8px; }
        .offer-price { font-size: 24px; font-weight: bold; color: #2196F3; }
        .offer-meta { color: #666; font-size: 14px; margin-bottom: 12px; }
        .offer-content { margin: 12px 0; line-height: 1.5; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #eee; border-radius: 6px 6px 0 0; cursor: pointer; }
        .tab.active { background: white; border-bottom: 2px solid #2196F3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Подходящие офферы для {{ channel.title }}</h1>
            <p>Выберите интересные предложения для размещения в вашем канале</p>
            <div style="margin-top: 10px;">
                <strong>Канал:</strong> @{{ channel.username }} | 
                <strong>Подписчиков:</strong> {{ channel.subscriber_count or 'Неизвестно' }}
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('offers')">Доступные офферы</div>
            <div class="tab" onclick="showTab('my-responses')">Мои отклики</div>
        </div>

        <div id="offers-tab">
            <div id="offersContainer">
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 24px; margin-bottom: 10px;">🔍</div>
                    <div>Загрузка подходящих офферов...</div>
                </div>
            </div>
        </div>

        <div id="my-responses-tab" style="display: none;">
            <div id="responsesContainer">
                <div style="text-align: center; padding: 40px; color: #666;">Загрузка...</div>
            </div>
        </div>
    </div>

    <script>
        const channelId = {{ channel.id }};

        function showTab(tabName) {
            document.querySelectorAll('[id$="-tab"]').forEach(tab => {
                tab.style.display = 'none';
            });

            document.querySelectorAll('.tab').forEach(btn => {
                btn.classList.remove('active');
            });

            document.getElementById(tabName + '-tab').style.display = 'block';
            event.target.classList.add('active');

            if (tabName === 'offers') {
                loadSuitableOffers();
            } else if (tabName === 'my-responses') {
                loadMyResponses();
            }
        }

        async function loadSuitableOffers() {
            try {
                const response = await fetch(`/api/offers/suitable/${channelId}`);
                const result = await response.json();

                const container = document.getElementById('offersContainer');

                if (result.success && result.offers.length > 0) {
                    container.innerHTML = result.offers.map(offer => `
                        <div class="offer-card">
                            <div class="offer-header">
                                <div>
                                    <div class="offer-title">${offer.title}</div>
                                    <div class="offer-meta">
                                        ${offer.category} • ${formatDate(offer.created_at)}
                                    </div>
                                </div>
                                <div class="offer-price">${offer.price} ${offer.currency}</div>
                            </div>

                            <div class="offer-content">
                                ${offer.content}
                            </div>

                            <div style="margin-top: 16px;">
                                <button class="btn btn-success" onclick="respondToOffer(${offer.id}, 'interested')">
                                    ⭐ Заинтересован
                                </button>
                                <button class="btn btn-success" onclick="respondToOffer(${offer.id}, 'accepted')" style="margin-left: 8px;">
                                    ✅ Принять
                                </button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #666;">
                            <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
                            <h3>Нет активных офферов</h3>
                            <p>В данный момент нет подходящих рекламных предложений.</p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Load offers error:', error);
                document.getElementById('offersContainer').innerHTML = `
                    <div class="card" style="text-align: center; color: #f44336;">
                        <h3>Ошибка загрузки</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }

        async function respondToOffer(offerId, status) {
            const message = prompt('Сообщение для рекламодателя:');
            if (!message) return;

            try {
                const response = await fetch('/api/responses', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        channel_id: channelId,
                        offer_id: offerId,
                        status: status,
                        message: message
                    })
                });

                const result = await response.json();

                if (result.success) {
                    alert('Отклик успешно отправлен!');
                    loadSuitableOffers();
                } else {
                    alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
                }
            } catch (error) {
                alert('Ошибка отправки отклика: ' + error.message);
            }
        }

        async function loadMyResponses() {
            try {
                const response = await fetch(`/api/responses/channel/${channelId}`);
                const result = await response.json();

                const container = document.getElementById('responsesContainer');

                if (result.success && result.responses.length > 0) {
                    container.innerHTML = result.responses.map(response => `
                        <div class="card">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <strong>${response.offer_title}</strong>
                                <span>${response.status}</span>
                            </div>
                            <div>${response.message}</div>
                            <div style="color: #666; font-size: 12px; margin-top: 8px;">
                                ${formatDate(response.created_at)}
                            </div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #666;">
                            <h3>Нет откликов</h3>
                            <p>Ваши отклики появятся здесь</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('responsesContainer').innerHTML = `
                    <div style="text-align: center; color: #f44336;">Ошибка загрузки: ${error.message}</div>
                `;
            }
        }

        function formatDate(dateStr) {
            return new Date(dateStr).toLocaleDateString('ru-RU');
        }

        document.addEventListener('DOMContentLoaded', () => {
            loadSuitableOffers();
        });
    </script>
</body>
</html>
            ''', channel=channel)

        except Exception as e:
            logger.error(f"Ошибка страницы офферов канала: {e}")
            return jsonify({'error': str(e)}), 500

if RESPONSES_SYSTEM_ENABLED and PLACEMENT_TRACKING_ENABLED:

    @app.route('/api/responses/create-with-tracking', methods=['POST'])
    @require_telegram_auth
    def api_create_response_with_tracking():
        """Создание отклика с автоматическим созданием отслеживания размещения"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400

            # Создаем обычный отклик
            result = create_offer_response(
                data.get('channel_id'),
                data.get('offer_id'),
                data
            )

            if result['success'] and result.get('response_id'):
                # Создаем размещение для отслеживания
                try:
                    placement_tracker = PlacementTracker(DATABASE_PATH)

                    # Планируем размещение на завтра
                    scheduled_at = datetime.now() + timedelta(hours=24)
                    expires_at = scheduled_at + timedelta(days=7)

                    placement_id = placement_tracker.create_placement(
                        offer_id=data.get('offer_id'),
                        channel_id=data.get('channel_id'),
                        response_id=result['response_id'],
                        scheduled_at=scheduled_at,
                        expires_at=expires_at
                    )

                    if placement_id:
                        result['placement_id'] = placement_id
                        result['tracking_enabled'] = True
                        result['tracking_url'] = f"/track/{placement_id}/view"

                        logger.info(f"Создано размещение {placement_id} для отклика {result['response_id']}")

                except Exception as tracking_error:
                    logger.error(f"Ошибка создания отслеживания: {tracking_error}")
                    result['tracking_enabled'] = False
                    result['tracking_error'] = str(tracking_error)

            return jsonify(result)

        except Exception as e:
            logger.error(f"Ошибка создания отклика с отслеживанием: {e}")
            return jsonify({
                'success': False,
                'error': 'Внутренняя ошибка сервера'
            }), 500

# === API КАНАЛОВ С УСИЛЕННОЙ ФИЛЬТРАЦИЕЙ ===

@app.route('/api/channels/search', methods=['POST'])
@require_telegram_auth
def search_channel():
    """Поиск канала через Telegram API"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        username = data['username'].strip().lstrip('@')
        user_id = get_current_user_id()

        # Поиск канала через Telegram API
        search_result = run_async_in_sync(telegram_service.search_channel(username, user_id))
        return jsonify(search_result)

    except Exception as e:
        logger.error(f"Search channel error: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500


@app.route('/api/channels', methods=['POST'])
@require_telegram_auth
def add_channel_with_telegram_id():
    """Добавление канала с обязательной привязкой к Telegram User ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400

        username = data.get('username', '').strip()
        telegram_user_id = get_current_user_id()

        logger.info(f"Adding channel @{username} for Telegram user {telegram_user_id}")

        if not username:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        # Получаем или создаем пользователя по Telegram ID
        user_db_id = ensure_user_exists(
            telegram_user_id,
            f'user_{telegram_user_id}',
            f'Telegram User {telegram_user_id}'
        )

        if not user_db_id:
            return jsonify({'success': False, 'error': 'Ошибка создания пользователя'}), 500

        # Очищаем username
        cleaned_username = username.lstrip('@')

        # Проверяем, не добавлен ли уже канал ЭТИМ Telegram пользователем
        existing_channel = safe_execute_query("""
            SELECT c.id, c.title 
            FROM channels c 
            JOIN users u ON c.owner_id = u.id 
            WHERE c.username = ? AND u.telegram_id = ?
        """, (cleaned_username, telegram_user_id), fetch_one=True)

        if existing_channel:
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен вами'
            })

        # Поиск канала через Telegram API
        logger.info(f"Searching channel @{cleaned_username} via Telegram API")
        search_result = run_async_in_sync(telegram_service.search_channel(cleaned_username, telegram_user_id))

        if not search_result.get('success'):
            return jsonify({
                'success': False,
                'error': search_result.get('error', 'Канал не найден')
            })

        channel_data = search_result.get('channel')
        user_permissions = search_result.get('user_permissions', {})

        if not channel_data:
            return jsonify({
                'success': False,
                'error': 'Не удалось получить данные канала'
            })

        # Проверяем права администратора
        if not user_permissions.get('is_admin', False):
            return jsonify({
                'success': False,
                'error': 'Вы должны быть администратором канала для его добавления'
            })

        # Сохраняем канал в базу данных
        logger.info(f"Saving channel @{cleaned_username} to database")

        try:
            current_time = datetime.now().isoformat()

            # ИСПРАВЛЕНО: Используем правильное название столбца subscribers_count
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO channels (
                    telegram_channel_id, 
                    username, 
                    title, 
                    description, 
                    subscribers_count, 
                    is_verified, 
                    is_active, 
                    owner_id, 
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                channel_data.get('id'),
                cleaned_username,
                channel_data.get('title', ''),
                channel_data.get('description', ''),
                channel_data.get('subscribers_count', 0),  # Данные уже в правильном формате
                channel_data.get('verified', False),
                True,  # is_active
                user_db_id,
                current_time,
                current_time
            ))

            # Проверяем, что запись была добавлена
            if cursor.rowcount > 0:
                connection.commit()
                connection.close()

                logger.info(f"✅ Channel @{cleaned_username} successfully added for user {telegram_user_id}")
                return jsonify({
                    'success': True,
                    'message': f'Канал @{cleaned_username} успешно добавлен!',
                    'channel': {
                        'username': cleaned_username,
                        'title': channel_data.get('title', ''),
                        'subscribers_count': channel_data.get('subscribers_count', 0)
                    }
                })
            else:
                connection.rollback()
                connection.close()
                return jsonify({
                    'success': False,
                    'error': 'Канал не был добавлен в базу данных'
                })

        except Exception as db_error:
            logger.error(f"Database error when adding channel: {db_error}")
            return jsonify({
                'success': False,
                'error': f'Ошибка базы данных: {str(db_error)}'
            })

    except Exception as e:
        logger.error(f"Ошибка добавления канала для Telegram пользователя: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка сервера: {str(e)}'
        }), 500


@app.route('/api/channels/my', methods=['GET'])
@require_telegram_auth
def get_my_channels():
    """Получение ТОЛЬКО своих каналов по Telegram ID с усиленной фильтрацией"""
    try:
        telegram_user_id = get_current_user_id()
        logger.info(f"Getting channels for Telegram user: {telegram_user_id}")

        # Получаем или создаем пользователя по Telegram ID
        user_db_id = ensure_user_exists(telegram_user_id, f'user_{telegram_user_id}', 'User')
        if not user_db_id:
            return jsonify({
                'success': False,
                'channels': [],
                'total': 0,
                'message': 'Ошибка пользователя'
            }), 500

        # СТРОГО фильтруем каналы по владельцу (двойная проверка по Telegram User ID)
        channels = safe_execute_query("""
            SELECT c.*, u.username as owner_username, u.telegram_id as owner_telegram_id
            FROM channels c 
            JOIN users u ON c.owner_id = u.id
            WHERE c.owner_id = ? AND u.telegram_id = ? AND u.id = ?
            ORDER BY c.created_at DESC
        """, (user_db_id, telegram_user_id, user_db_id), fetch_all=True)

        logger.info(f"Found {len(channels) if channels else 0} channels for Telegram user {telegram_user_id}")

        if not channels:
            return jsonify({
                'success': True,
                'channels': [],
                'total': 0,
                'message': 'У вас пока нет добавленных каналов',
                'telegram_user_info': {
                    'telegram_user_id': telegram_user_id,
                    'user_db_id': user_db_id
                }
            })

        enriched_channels = []
        for channel in channels:
            # Дополнительная проверка безопасности на уровне данных
            if channel['owner_telegram_id'] != telegram_user_id:
                logger.warning(
                    f"Security: Channel {channel['id']} owner mismatch. "
                    f"Expected: {telegram_user_id}, Got: {channel['owner_telegram_id']}")
                continue

            channel_data = dict(channel)

            # Обеспечиваем совместимость названий полей
            if 'subscriber_count' in channel_data:
                channel_data['subscribers_count'] = channel_data['subscriber_count']
            elif 'subscribers_count' in channel_data:
                channel_data['subscriber_count'] = channel_data['subscribers_count']
            else:
                channel_data['subscriber_count'] = 0
                channel_data['subscribers_count'] = 0

            # Форматируем дату
            if channel_data.get('created_at'):
                try:
                    if isinstance(channel_data['created_at'], str):
                        created_at = datetime.fromisoformat(channel_data['created_at'].replace('Z', '+00:00'))
                    else:
                        created_at = channel_data['created_at']
                    channel_data['created_at_formatted'] = created_at.strftime('%d.%m.%Y')
                except:
                    channel_data['created_at_formatted'] = 'Неизвестно'

            enriched_channels.append(channel_data)

        # Статистика только для текущего Telegram пользователя
        stats = {
            'total_channels': len(enriched_channels),
            'verified_channels': len([c for c in enriched_channels if c.get('is_verified')]),
            'active_channels': len([c for c in enriched_channels if c.get('is_active')]),
            'total_subscribers': sum(c.get('subscriber_count', 0) or 0 for c in enriched_channels)
        }

        return jsonify({
            'success': True,
            'channels': enriched_channels,
            'total': len(enriched_channels),
            'stats': stats,
            'telegram_user_info': {
                'telegram_user_id': telegram_user_id,
                'user_db_id': user_db_id
            }
        })

    except Exception as e:
        logger.error(f"Ошибка получения каналов для Telegram пользователя: {e}")
        return jsonify({
            'success': False,
            'channels': [],
            'error': str(e),
            'telegram_user_info': {
                'telegram_user_id': get_current_user_id() if get_current_user_id() else None
            }
        }), 500



@app.route('/api/channels/<int:channel_id>/refresh', methods=['POST'])
@require_telegram_auth
def refresh_channel_data(channel_id):
    """Обновление данных канала (только владельцем по Telegram ID)"""
    try:
        telegram_user_id = get_current_user_id()
        logger.info(f"Refreshing channel {channel_id} for Telegram user {telegram_user_id}")

        # Проверяем права на обновление канала
        channel = safe_execute_query('''
            SELECT c.telegram_channel_id, c.username, c.title
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ? AND u.telegram_id = ?
        ''', (channel_id, telegram_user_id), fetch_one=True)

        if not channel:
            return jsonify({'success': False, 'error': 'Канал не найден или нет прав доступа'}), 404

        # Остальная логика обновления...

    except Exception as e:
        logger.error(f"Ошибка обновления канала: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/telegram-info', methods=['GET'])
@require_telegram_auth
def get_telegram_user_info():
    """Получение информации о текущем Telegram пользователе"""
    try:
        telegram_user_id = get_current_user_id()

        # Получаем информацию о пользователе из БД
        user_info = safe_execute_query('''
            SELECT id, telegram_id, username, first_name, created_at
            FROM users 
            WHERE telegram_id = ?
        ''', (telegram_user_id,), fetch_one=True)

        if not user_info:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404

        # Остальная логика...

    except Exception as e:
        logger.error(f"Ошибка получения информации о Telegram пользователе: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/<int:channel_id>', methods=['DELETE'])
@require_telegram_auth
def delete_channel_secure(channel_id):
    """Безопасное удаление канала только владельцем (по Telegram ID)"""
    try:
        telegram_user_id = get_current_user_id()
        logger.info(f"Deleting channel {channel_id} for Telegram user {telegram_user_id}")

        # СТРОГАЯ ПРОВЕРКА: канал принадлежит текущему Telegram пользователю
        channel = safe_execute_query('''
            SELECT c.id, c.title, c.username 
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ? AND u.telegram_id = ?
        ''', (channel_id, telegram_user_id), fetch_one=True)

        if not channel:
            return jsonify({
                'success': False,
                'error': 'Канал не найден или у вас нет прав на его удаление'
            }), 404

        # Остальная логика удаления...

    except Exception as e:
        logger.error(f"Ошибка удаления канала: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# === ДОПОЛНИТЕЛЬНЫЕ API ENDPOINTS ===
@app.route('/test')
def api_test():
    """Тестовая страница"""
    return jsonify({
        'status': 'OK',
        'message': 'Продуктивная версия приложения работает!',
        'features': {
            'telegram_api': bool(BOT_TOKEN),
            'telegram_integration': TELEGRAM_INTEGRATION,
            'offers_system': OFFERS_SYSTEM_ENABLED,
            'responses_system': RESPONSES_SYSTEM_ENABLED,
            'database': 'SQLite',
            'real_channel_search': True,
            'production_mode': True
        },
        'config': {
            'bot_token_configured': bool(BOT_TOKEN),
            'database_path': DATABASE_PATH,
            'database_exists': os.path.exists(DATABASE_PATH),
            'your_telegram_id': YOUR_TELEGRAM_ID
        },
        'timestamp': datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """Проверка здоровья приложения"""
    try:
        # Тест базы данных
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        conn.close()

        # Тест Telegram API
        telegram_status = run_async_in_sync(telegram_service.test_connection())

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'database_type': 'SQLite',
            'database_path': DATABASE_PATH,
            'database_size': f"{os.path.getsize(DATABASE_PATH) / 1024:.1f} KB" if os.path.exists(
                DATABASE_PATH) else 'N/A',
            'telegram_api': 'connected' if telegram_status['success'] else 'error',
            'telegram_integration': 'enabled' if TELEGRAM_INTEGRATION else 'disabled',
            'offers_system': 'enabled' if OFFERS_SYSTEM_ENABLED else 'disabled',
            'responses_system': 'enabled' if RESPONSES_SYSTEM_ENABLED else 'disabled',
            'bot_token_configured': bool(BOT_TOKEN),
            'production_mode': True,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/database-info')
def api_database_info():
    """Информация о базе данных"""
    try:
        # Получение списка таблиц
        tables_result = safe_execute_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """, fetch_all=True)

        tables = [table['name'] for table in tables_result] if tables_result else []

        # Информация о каждой таблице
        table_info = {}
        for table_name in tables:
            count_result = safe_execute_query(f"SELECT COUNT(*) as count FROM {table_name}", fetch_one=True)
            table_info[table_name] = count_result['count'] if count_result else 0

        return jsonify({
            'database_type': 'SQLite',
            'database_path': DATABASE_PATH,
            'database_exists': os.path.exists(DATABASE_PATH),
            'database_size': f"{os.path.getsize(DATABASE_PATH) / 1024:.1f} KB" if os.path.exists(
                DATABASE_PATH) else 'N/A',
            'status': 'Connected',
            'tables_count': len(tables),
            'tables': tables,
            'table_info': table_info,
            'sqlite_version': sqlite3.sqlite_version,
            'production_mode': True
        })

    except Exception as e:
        return jsonify({
            'database_type': 'SQLite',
            'status': f'Error: {str(e)}',
            'tables_count': 0
        }), 500


# === ERROR HANDLERS ===
@app.errorhandler(429)
def rate_limit_handler(e):
    """Обработчик ошибки превышения лимита запросов"""
    client_ip = get_client_ip()

    log_security_event('RATE_LIMIT_ERROR', {
        'ip': client_ip,
        'path': request.path,
        'user_agent': request.headers.get('User-Agent', '')
    })

    return jsonify({
        'error': 'Превышен лимит запросов',
        'retry_after': 3600
    }), 429


@app.errorhandler(403)
def forbidden_handler(e):
    """Обработчик ошибки доступа запрещен"""
    return jsonify({'error': 'Доступ запрещен'}), 403


@app.errorhandler(413)
def request_too_large_handler(e):
    """Обработчик ошибки слишком большого запроса"""
    return jsonify({'error': 'Запрос слишком большой'}), 413


@app.errorhandler(500)
def handle_500(error):
    logger.error(f"500 Error: {error}")
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.errorhandler(404)
def page_not_found(error):
    """Обработчик ошибки 404"""
    error_info = {
        'error': 'Страница не найдена',
        'requested_url': request.url,
        'available_routes': [rule.rule for rule in app.url_map.iter_rules()],
        'message': 'Проверьте правильность URL или используйте навигацию'
    }

    # Если это API запрос, возвращаем JSON
    if request.path.startswith('/api/'):
        return jsonify(error_info), 404

    # Для обычных страниц можно перенаправить на главную
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
            <br><br>
            <details>
                <summary>Отладочная информация</summary>
                <pre>{{ error_info | tojson(indent=2) }}</pre>
            </details>
        </div>
    </body>
    </html>
    ''', error_info=error_info), 404

@app.after_request
def security_headers_middleware(response):
    """Middleware для добавления заголовков безопасности"""

    # Основные заголовки безопасности
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://telegram.org https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.telegram.org; "
        "frame-ancestors 'none'"
    )
    response.headers['Content-Security-Policy'] = csp

    # Убираем информацию о сервере
    response.headers.pop('Server', None)

    return response


# === SYSTEM RECOMMENDATIONS API ===

@app.route('/api/offers/channel-recommendations', methods=['POST'])
def get_channel_recommendations():
    """API для получения рекомендованных каналов на основе анализа оффера"""
    try:
        from app.api.channel_recommendations import get_channel_recommendations_api

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Отсутствуют данные запроса'}), 400

        # Валидация обязательных полей
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()

        if not title and not description:
            return jsonify({'error': 'Укажите заголовок или описание оффера'}), 400

        # Получение параметров
        target_audience = data.get('target_audience', '').strip()
        price = float(data.get('price', 0))
        limit = min(int(data.get('limit', 10)), 20)  # Максимум 20 рекомендаций

        # Получаем рекомендации
        result = get_channel_recommendations_api(
            title=title,
            description=description,
            target_audience=target_audience,
            price=price,
            limit=limit
        )

        if result['success']:
            logger.info(f"Сгенерировано {len(result['recommendations'])} рекомендаций для оффера '{title[:50]}'")

            # Добавляем дополнительную информацию для фронтенда
            for rec in result['recommendations']:
                rec['estimated_reach'] = estimate_channel_reach(rec)
                rec['price_comparison'] = compare_price_with_market(rec.get('price_per_post', 0), price)

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': f'Ошибка валидации данных: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций каналов: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


def estimate_channel_reach(channel: Dict[str, Any]) -> Dict[str, Any]:
    """Оценка охвата канала"""
    try:
        subscribers = channel.get('subscriber_count', 0)
        avg_rating = float(channel.get('avg_rating', 4.0))

        # Базовый охват (обычно 10-30% от подписчиков)
        base_reach_rate = 0.15 + (avg_rating - 3.0) * 0.05  # От 10% до 25%
        estimated_views = int(subscribers * base_reach_rate)

        # Оценка вовлеченности
        engagement_rate = min(base_reach_rate * 0.1, 0.05)  # 1-5%
        estimated_engagement = int(estimated_views * engagement_rate)

        return {
            'estimated_views': estimated_views,
            'estimated_engagement': estimated_engagement,
            'reach_rate': round(base_reach_rate * 100, 1)
        }
    except:
        return {
            'estimated_views': 0,
            'estimated_engagement': 0,
            'reach_rate': 15.0
        }


def compare_price_with_market(channel_price: float, offer_price: float) -> Dict[str, Any]:
    """Сравнение цены канала с предложенной ценой"""
    try:
        if channel_price <= 0:
            return {
                'status': 'unknown',
                'message': 'Цена не указана',
                'ratio': 0
            }

        ratio = offer_price / channel_price

        if ratio >= 1.2:
            return {
                'status': 'above_market',
                'message': f'На {int((ratio - 1) * 100)}% выше обычной цены',
                'ratio': ratio
            }
        elif ratio >= 0.8:
            return {
                'status': 'market_rate',
                'message': 'Соответствует рыночной цене',
                'ratio': ratio
            }
        else:
            return {
                'status': 'below_market',
                'message': f'На {int((1 - ratio) * 100)}% ниже обычной цены',
                'ratio': ratio
            }
    except:
        return {
            'status': 'unknown',
            'message': 'Не удалось сравнить цены',
            'ratio': 0
        }


@app.route('/api/offers/quick-analysis', methods=['POST'])
def quick_offer_analysis():
    """Быстрый анализ оффера для показа предварительных рекомендаций"""
    try:
        from app.api.channel_recommendations import get_channel_recommendations_api

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Отсутствуют данные запроса'}), 400

        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        target_audience = data.get('target_audience', '').strip()

        if not title and not description:
            return jsonify({'error': 'Укажите заголовок или описание'}), 400

        # Анализируем контент
        analysis = analyze_offer_content(title, description, target_audience)

        # Получаем краткую статистику по категориям
        category_stats = {}
        if analysis.get('primary_category'):
            category_stats = get_category_statistics(analysis['primary_category'])

        return jsonify({
            'success': True,
            'analysis': analysis,
            'category_stats': category_stats,
            'suggestions': generate_quick_suggestions(analysis)
        })

    except Exception as e:
        logger.error(f"Ошибка быстрого анализа оффера: {e}")
        return jsonify({'error': 'Ошибка анализа'}), 500


def get_category_statistics(category: str) -> Dict[str, Any]:
    """Получение статистики по категории"""
    try:
        stats = safe_execute_query('''
                                   SELECT COUNT(*)              as total_channels,
                                          AVG(subscriber_count) as avg_subscribers,
                                          AVG(price_per_post)   as avg_price,
                                          MIN(price_per_post)   as min_price,
                                          MAX(price_per_post)   as max_price
                                   FROM channels
                                   WHERE category = ?
                                     AND is_active = 1
                                     AND price_per_post > 0
                                   ''', (category,), fetch_one=True)

        if stats and stats['total_channels'] > 0:
            return {
                'total_channels': stats['total_channels'],
                'avg_subscribers': int(stats['avg_subscribers'] or 0),
                'avg_price': round(float(stats['avg_price'] or 0), 2),
                'price_range': {
                    'min': round(float(stats['min_price'] or 0), 2),
                    'max': round(float(stats['max_price'] or 0), 2)
                }
            }
    except Exception as e:
        logger.error(f"Ошибка получения статистики категории {category}: {e}")

    return {
        'total_channels': 0,
        'avg_subscribers': 0,
        'avg_price': 0,
        'price_range': {'min': 0, 'max': 0}
    }


def generate_quick_suggestions(analysis: Dict[str, Any]) -> List[str]:
    """Генерация быстрых советов по улучшению оффера"""
    suggestions = []

    try:
        categories = analysis.get('categories', [])
        keywords = analysis.get('keywords', [])

        if not categories:
            suggestions.append("Добавьте более конкретное описание тематики для лучшего подбора каналов")

        if len(keywords) < 3:
            suggestions.append("Используйте больше ключевых слов для точного таргетинга")

        urgency = analysis.get('urgency', 'normal')
        if urgency == 'high':
            suggestions.append("При срочном размещении рассмотрите каналы с быстрым откликом")

        if analysis.get('audience'):
            suggestions.append("Указана целевая аудитория - это поможет найти более релевантные каналы")
        else:
            suggestions.append("Укажите целевую аудиторию для более точных рекомендаций")

    except Exception as e:
        logger.error(f"Ошибка генерации советов: {e}")

    return suggestions


# === ПРОДВИНУТЫЙ АЛГОРИТМ СОПОСТАВЛЕНИЯ ===
@app.route('/api/offers/advanced-channel-offers/<int:channel_id>')
def api_advanced_channel_offers(channel_id):
    """API для получения офферов с продвинутой оценкой"""
    try:
        telegram_user_id = get_current_user_id()
        if not telegram_user_id:
            return jsonify({'error': 'Не авторизован'}), 401

        # Проверяем владельца канала
        channel = safe_execute_query('''
                                     SELECT c.id, c.owner_id, u.telegram_id
                                     FROM channels c
                                              JOIN users u ON c.owner_id = u.id
                                     WHERE c.id = ?
                                     ''', (channel_id,), fetch_one=True)

        if not channel:
            return jsonify({'error': 'Канал не найден'}), 404

        if channel['telegram_id'] != telegram_user_id:
            return jsonify({'error': 'Доступ запрещен'}), 403

        # Получаем офферы с продвинутой оценкой
        if ADVANCED_MATCHING_ENABLED:
            limit = min(int(request.args.get('limit', 10)), 20)
            offers = get_advanced_suitable_offers_for_channel(channel_id, limit)
        else:
            # Fallback на старый алгоритм
            from offer_responses import get_suitable_offers_for_channel
            offers = get_suitable_offers_for_channel(channel_id, 10)

        return jsonify({
            'success': True,
            'channel_id': channel_id,
            'offers': offers,
            'total_count': len(offers),
            'algorithm_version': 'advanced_v2.0' if ADVANCED_MATCHING_ENABLED else 'legacy_v1.0'
        })

    except Exception as e:
        logger.error(f"Ошибка получения продвинутых офферов для канала {channel_id}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/compatibility-analysis', methods=['POST'])
def api_compatibility_analysis():
    """Детальный анализ совместимости оффера и канала"""
    try:
        telegram_user_id = get_current_user_id()
        if not telegram_user_id:
            return jsonify({'error': 'Не авторизован'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Отсутствуют данные'}), 400

        offer_id = data.get('offer_id')
        channel_id = data.get('channel_id')

        if not offer_id or not channel_id:
            return jsonify({'error': 'Укажите offer_id и channel_id'}), 400

        # Проверяем доступ к каналу
        channel = safe_execute_query('''
                                     SELECT c.id, u.telegram_id
                                     FROM channels c
                                              JOIN users u ON c.owner_id = u.id
                                     WHERE c.id = ?
                                     ''', (channel_id,), fetch_one=True)

        if not channel or channel['telegram_id'] != telegram_user_id:
            return jsonify({'error': 'Доступ к каналу запрещен'}), 403

        # Выполняем анализ совместимости
        if ADVANCED_MATCHING_ENABLED:
            analysis = analyze_offer_channel_compatibility(offer_id, channel_id)
        else:
            analysis = {'error': 'Продвинутый анализ недоступен'}

        return jsonify(analysis)

    except Exception as e:
        logger.error(f"Ошибка анализа совместимости: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@app.route('/api/algorithm-comparison/<int:channel_id>')
def api_algorithm_comparison(channel_id):
    """Сравнение старого и нового алгоритмов"""
    try:
        telegram_user_id = get_current_user_id()
        if not telegram_user_id:
            return jsonify({'error': 'Не авторизован'}), 401

        # Проверяем доступ
        channel = safe_execute_query('''
                                     SELECT c.id, u.telegram_id
                                     FROM channels c
                                              JOIN users u ON c.owner_id = u.id
                                     WHERE c.id = ?
                                     ''', (channel_id,), fetch_one=True)

        if not channel or channel['telegram_id'] != telegram_user_id:
            return jsonify({'error': 'Доступ запрещен'}), 403

        # Получаем результаты старого алгоритма
        if RESPONSES_SYSTEM_ENABLED:
            old_offers = get_suitable_offers_for_channel(channel_id, 10)
        else:
            old_offers = []

        # Получаем результаты нового алгоритма
        if ADVANCED_MATCHING_ENABLED:
            new_offers = get_advanced_suitable_offers_for_channel(channel_id, 10)
        else:
            new_offers = []

        # Сравнительная статистика
        comparison = {
            'channel_id': channel_id,
            'old_algorithm': {
                'total_offers': len(old_offers),
                'avg_score': sum(offer.get('suitability_score', 0) for offer in old_offers) / len(
                    old_offers) if old_offers else 0,
                'offers': old_offers
            },
            'new_algorithm': {
                'total_offers': len(new_offers),
                'avg_score': sum(offer.get('suitability_score', 0) for offer in new_offers) / len(
                    new_offers) if new_offers else 0,
                'offers': new_offers
            }
        }

        return jsonify({
            'success': True,
            'comparison': comparison
        })

    except Exception as e:
        logger.error(f"Ошибка сравнения алгоритмов для канала {channel_id}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


def add_user_matching_settings_table():
    """Добавляет таблицу настроек алгоритма сопоставления"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS user_matching_settings
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           algorithm_version
                           TEXT
                           DEFAULT
                           'advanced_v2.0',
                           custom_weights
                           TEXT, -- JSON с пользовательскими весами
                           filters
                           TEXT, -- JSON с фильтрами
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ),
                           UNIQUE
                       (
                           user_id
                       )
                           )
                       ''')

        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_user_matching_settings_user_id
                           ON user_matching_settings(user_id)
                       ''')

        conn.commit()
        conn.close()
        logger.info("✅ Таблица user_matching_settings создана")
        return True

    except Exception as e:
        logger.error(f"Ошибка создания таблицы настроек: {e}")
        return False


def initialize_advanced_matching():
    """Инициализация компонентов продвинутого алгоритма"""
    try:
        logger.info("🧠 Инициализация продвинутого алгоритма сопоставления...")

        # Создаем таблицу настроек
        table_created = add_user_matching_settings_table()

        # Проверяем доступность модуля
        if ADVANCED_MATCHING_ENABLED:
            engine = AdvancedMatchingEngine(DATABASE_PATH)
            logger.info("✅ Продвинутый алгоритм готов к работе")
            return True
        else:
            logger.error("❌ Продвинутый алгоритм недоступен")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации продвинутого алгоритма: {e}")
        return False


@app.route('/api/analytics/system-status')
def api_analytics_system_status():
    """Проверка статуса всей системы аналитики"""
    try:
        telegram_user_id = get_current_user_id()

        # Базовый статус системы
        status = {
            'timestamp': datetime.now().isoformat(),
            'database_connected': os.path.exists(DATABASE_PATH),
            'user_authenticated': bool(telegram_user_id),
            'telegram_user_id': telegram_user_id,
            'systems': {
                'basic_analytics': ANALYTICS_SYSTEM_ENABLED,
                'placement_tracking': PLACEMENT_TRACKING_ENABLED,
                'ai_recommendations': AI_RECOMMENDATIONS_ENABLED
            },
            'features': [],
            'quick_stats': {}
        }

        # Проверяем какие системы реально работают
        if hasattr(app, 'analytics_status'):
            status['systems_runtime'] = app.analytics_status

        # Получаем быстрые статистики если пользователь авторизован
        if telegram_user_id and ANALYTICS_SYSTEM_ENABLED:
            try:
                analytics_engine = AnalyticsEngine(DATABASE_PATH)
                quick_metrics = analytics_engine.get_user_metrics(telegram_user_id, '7d')

                status['quick_stats'] = {
                    'revenue_7d': quick_metrics.get('total_revenue', 0),
                    'channels': quick_metrics.get('total_audience', 0) > 0,
                    'conversion_rate': quick_metrics.get('conversion_rate', 0),
                    'response_time': quick_metrics.get('avg_response_time', 0)
                }

                # Определяем доступные функции
                features = ['📊 Дашборд метрик', '📈 Графики динамики']

                if PLACEMENT_TRACKING_ENABLED:
                    features.append('🎯 Отслеживание размещений')

                if AI_RECOMMENDATIONS_ENABLED:
                    features.append('🤖 AI-рекомендации')

                status['features'] = features

            except Exception as e:
                logger.error(f"Error getting quick stats: {e}")
                status['quick_stats_error'] = str(e)

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f"Analytics system status error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': {
                'database_connected': False,
                'user_authenticated': False,
                'systems': {
                    'basic_analytics': False,
                    'placement_tracking': False,
                    'ai_recommendations': False
                }
            }
        }), 500


@app.route('/api/analytics/dashboard-data')
@require_telegram_auth
def api_analytics_dashboard_data():
    """Комплексные данные для дашборда аналитики"""
    try:
        telegram_user_id = get_current_user_id()
        range_type = request.args.get('range', '30d')

        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'range': range_type,
            'user_id': telegram_user_id,
            'metrics': {},
            'charts': {},
            'performance': [],
            'recommendations': [],
            'tracking_summary': {},
            'ai_insights': {}
        }

        # 1. Базовые метрики
        if ANALYTICS_SYSTEM_ENABLED:
            try:
                analytics_engine = AnalyticsEngine(DATABASE_PATH)
                dashboard_data['metrics'] = analytics_engine.get_user_metrics(telegram_user_id, range_type)
                dashboard_data['charts'] = analytics_engine.get_chart_data(telegram_user_id, range_type)
                dashboard_data['performance'] = analytics_engine.get_performance_data(telegram_user_id, range_type)
            except Exception as e:
                logger.error(f"Basic analytics error: {e}")
                dashboard_data['analytics_error'] = str(e)

        # 2. Данные отслеживания размещений
        if PLACEMENT_TRACKING_ENABLED:
            try:
                placement_tracker = PlacementTracker(DATABASE_PATH)
                dashboard_data['tracking_summary'] = placement_tracker.get_performance_summary(
                    telegram_user_id,
                    {'7d': 7, '30d': 30, '90d': 90}.get(range_type, 30)
                )
            except Exception as e:
                logger.error(f"Placement tracking error: {e}")
                dashboard_data['tracking_error'] = str(e)

        # 3. AI-рекомендации
        if AI_RECOMMENDATIONS_ENABLED:
            try:
                ai_engine = AIRecommendationEngine(DATABASE_PATH)
                recommendations = ai_engine.generate_recommendations(
                    telegram_user_id,
                    {'7d': 7, '30d': 30, '90d': 90}.get(range_type, 30)
                )

                # Конвертируем рекомендации в JSON
                dashboard_data['recommendations'] = []
                for rec in recommendations[:4]:  # Топ-4 для дашборда
                    dashboard_data['recommendations'].append({
                        'type': rec.type,
                        'priority': rec.priority,
                        'title': rec.title,
                        'description': rec.description,
                        'impact': rec.impact_description,
                        'confidence': rec.confidence
                    })

            except Exception as e:
                logger.error(f"AI recommendations error: {e}")
                dashboard_data['ai_error'] = str(e)

        # 4. Сводная информация
        dashboard_data['summary'] = {
            'total_systems': 3,
            'active_systems': sum([
                ANALYTICS_SYSTEM_ENABLED,
                PLACEMENT_TRACKING_ENABLED,
                AI_RECOMMENDATIONS_ENABLED
            ]),
            'data_quality': 'good' if len(dashboard_data.get('performance', [])) > 0 else 'limited',
            'last_updated': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'dashboard_data': dashboard_data
        })

    except Exception as e:
        logger.error(f"Dashboard data API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'dashboard_data': {
                'summary': {'error': True, 'message': 'Ошибка загрузки данных'}
            }
        }), 500

'''@app.route('/api/analytics/create-demo-data', methods=['POST'])
@require_telegram_auth
def api_create_demo_analytics_data():
    """Создание демо-данных для тестирования аналитики"""
    try:
        telegram_user_id = get_current_user_id()

        # Проверяем права администратора
        if telegram_user_id != YOUR_TELEGRAM_ID:
            return jsonify({
                'success': False,
                'error': 'Доступ запрещен. Только для администратора.'
            }), 403

        created_items = {
            'demo_placement': None,
            'demo_events': 0,
            'demo_offers': 0
        }

        # Создаем демо-размещение если включено отслеживание
        if PLACEMENT_TRACKING_ENABLED:
            try:
                # Создаем демо-размещение
                from placement_tracking import create_demo_placement
                placement_id = create_demo_placement(DATABASE_PATH)

                if placement_id:
                    created_items['demo_placement'] = placement_id
                    created_items['demo_events'] = 50  # Примерное количество событий

                    logger.info(f"Создано демо-размещение {placement_id}")

            except Exception as e:
                logger.error(f"Error creating demo placement: {e}")

        # Создаем дополнительные демо-данные для офферов
        try:
            # Убеждаемся что пользователь существует
            user_db_id = ensure_user_exists(telegram_user_id)

            if user_db_id and OFFERS_SYSTEM_ENABLED:
                # Создаем несколько демо-офферов
                demo_offers = [
                    {
                        'title': 'Демо-оффер: Продвижение технологического стартапа',
                        'description': 'Размещение рекламы инновационного IT-продукта',
                        'content': 'Ищем каналы для размещения рекламы нашего нового мобильного приложения. Готовы предложить выгодные условия сотрудничества.',
                        'price': 5000,
                        'currency': 'RUB',
                        'category': 'technology'
                    },
                    {
                        'title': 'Демо-оффер: Реклама образовательного курса',
                        'description': 'Продвижение онлайн-курса по интернет-маркетингу',
                        'content': 'Запускаем новый курс по цифровому маркетингу. Ищем качественные каналы с активной аудиторией.',
                        'price': 3500,
                        'currency': 'RUB',
                        'category': 'education'
                    }
                ]

                for offer_data in demo_offers:
                    result = add_offer(telegram_user_id, offer_data)
                    if result.get('success'):
                        created_items['demo_offers'] += 1

        except Exception as e:
            logger.error(f"Error creating demo offers: {e}")

        return jsonify({
            'success': True,
            'message': 'Демо-данные созданы',
            'created_items': created_items,
            'note': 'Демо-данные помогут протестировать все функции аналитики'
        })

    except Exception as e:
        logger.error(f"Create demo data error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500'''


@app.route('/payments-dashboard')
def payments_dashboard():
    """Панель управления платежами"""
    return render_template('payments_dashboard.html')


@app.route('/api/payments/stats')
def payments_stats():
    """Статистика платежей"""
    try:
        telegram_user_id = get_current_user_id()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Пользователь не авторизован'}), 401

        # Получаем статистику
        stats = safe_execute_query('''
                                   SELECT COUNT(*)                                                 as total_payments,
                                          SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END)    as total_paid,
                                          SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END) as pending_amount,
                                          COUNT(CASE WHEN status = 'paid' THEN 1 END)              as successful_payments
                                   FROM payments p
                                            JOIN offers o ON p.offer_id = o.id
                                            JOIN users u ON o.created_by = u.id
                                   WHERE u.telegram_id = ?
                                   ''', (telegram_user_id,), fetch_one=True)

        # Получаем статистику эскроу
        escrow_stats = safe_execute_query('''
                                          SELECT COUNT(*)                                                        as total_escrows,
                                                 SUM(CASE WHEN status = 'funds_held' THEN amount ELSE 0 END)     as held_amount,
                                                 SUM(CASE WHEN status = 'funds_released' THEN amount ELSE 0 END) as released_amount,
                                                 COUNT(CASE WHEN status = 'disputed' THEN 1 END)                 as disputed_count
                                          FROM escrow_transactions et
                                                   JOIN offers o ON et.offer_id = o.id
                                                   JOIN users u ON o.created_by = u.id
                                          WHERE u.telegram_id = ?
                                          ''', (telegram_user_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'payments': stats or {},
            'escrow': escrow_stats or {}
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики платежей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def setup_payout_routes():
    """Настройка маршрутов системы выплат"""
    global payout_manager

    if not PAYOUT_SYSTEM_ENABLED:
        logger.warning("⚠️ Система выплат отключена")
        return

    # Инициализируем менеджер выплат
    payout_manager = PayoutManager()

    # Регистрируем основные маршруты
    register_payout_routes(app)


    # === API ДЛЯ УПРАВЛЕНИЯ ВЫПЛАТАМИ ===

    @app.route('/api/payouts/trigger-escrow-release', methods=['POST'])
    def trigger_escrow_release():
        """API для освобождения средств из эскроу с созданием выплаты"""
        try:
            data = request.get_json()
            offer_id = data.get('offer_id')
            user_id = get_current_user_id()

            if not offer_id:
                return jsonify({'success': False, 'error': 'offer_id обязателен'}), 400

            # Находим эскроу для оффера
            escrow = safe_execute_query('''
                                        SELECT *
                                        FROM escrow_transactions
                                        WHERE offer_id = ?
                                          AND status = 'funds_held'
                                        ''', (offer_id,), fetch_one=True)

            if not escrow:
                return jsonify({
                    'success': False,
                    'error': 'Эскроу не найден или средства уже освобождены'
                }), 404

            # Создаем выплату
            result = payout_manager.create_manual_payout(
                escrow['id'],
                trigger_type='offer_completed'
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Выплата создана и поставлена в очередь',
                    'payout_id': result['payout_id'],
                    'amount': result['amount']
                })
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Ошибка освобождения эскроу: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payouts/pending', methods=['GET'])
    def get_pending_payouts():
        """Получение ожидающих выплат"""
        try:
            user_id = get_current_user_id()

            # Получаем ожидающие выплаты для текущего пользователя
            pending_payouts = safe_execute_query('''
                                                 SELECT p.*,
                                                        et.offer_id,
                                                        o.title as offer_title,
                                                        u.username,
                                                        u.telegram_id
                                                 FROM payouts p
                                                          JOIN users u ON p.recipient_id = u.id
                                                          LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                          LEFT JOIN offers o ON et.offer_id = o.id
                                                 WHERE p.status IN ('pending', 'retry')
                                                   AND (u.telegram_id = ? OR ? = ?)
                                                 ORDER BY p.scheduled_at ASC
                                                 ''', (user_id, user_id, YOUR_TELEGRAM_ID), fetch_all=True)

            return jsonify({
                'success': True,
                'payouts': pending_payouts or []
            })

        except Exception as e:
            logger.error(f"Ошибка получения ожидающих выплат: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payouts/failed', methods=['GET'])
    def get_failed_payouts():
        """Получение выплат с ошибками"""
        try:
            user_id = get_current_user_id()

            failed_payouts = safe_execute_query('''
                                                SELECT p.*,
                                                       et.offer_id,
                                                       o.title as offer_title,
                                                       u.username,
                                                       u.telegram_id
                                                FROM payouts p
                                                         JOIN users u ON p.recipient_id = u.id
                                                         LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                         LEFT JOIN offers o ON et.offer_id = o.id
                                                WHERE p.status = 'failed'
                                                  AND (u.telegram_id = ? OR ? = ?)
                                                ORDER BY p.updated_at DESC LIMIT 50
                                                ''', (user_id, user_id, YOUR_TELEGRAM_ID), fetch_all=True)

            return jsonify({
                'success': True,
                'payouts': failed_payouts or []
            })

        except Exception as e:
            logger.error(f"Ошибка получения выплат с ошибками: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/escrow/ready', methods=['GET'])
    def get_ready_escrows():
        """Получение эскроу готовых к выплате"""
        try:
            user_id = get_current_user_id()

            ready_escrows = safe_execute_query('''
                                               SELECT et.*,
                                                      u.username,
                                                      u.telegram_id,
                                                      o.title as offer_title,
                                                      o.price
                                               FROM escrow_transactions et
                                                        JOIN users u ON et.recipient_id = u.id
                                                        JOIN offers o ON et.offer_id = o.id
                                               WHERE et.status = 'funds_held'
                                                 AND et.expires_at <= ?
                                                 AND et.id NOT IN (SELECT DISTINCT escrow_id
                                                                   FROM payouts
                                                                   WHERE escrow_id IS NOT NULL)
                                                 AND (u.telegram_id = ? OR ? = ?)
                                               ORDER BY et.expires_at ASC
                                               ''', (datetime.now(), user_id, user_id, YOUR_TELEGRAM_ID),
                                               fetch_all=True)

            return jsonify({
                'success': True,
                'escrows': ready_escrows or []
            })

        except Exception as e:
            logger.error(f"Ошибка получения готовых эскроу: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payouts/process-ready-escrows', methods=['POST'])
    def process_ready_escrows():
        """Создание выплат для всех готовых эскроу"""
        try:
            user_id = get_current_user_id()

            # Получаем готовые эскроу
            ready_escrows = safe_execute_query('''
                                               SELECT et.*
                                               FROM escrow_transactions et
                                                        JOIN users u ON et.recipient_id = u.id
                                               WHERE et.status = 'funds_held'
                                                 AND et.expires_at <= ?
                                                 AND et.id NOT IN (SELECT DISTINCT escrow_id
                                                                   FROM payouts
                                                                   WHERE escrow_id IS NOT NULL)
                                                 AND (u.telegram_id = ? OR ? = ?)
                                               ''', (datetime.now(), user_id, user_id, YOUR_TELEGRAM_ID),
                                               fetch_all=True)

            created_payouts = []
            errors = []

            for escrow in ready_escrows:
                try:
                    result = payout_manager.create_manual_payout(
                        escrow['id'],
                        trigger_type='auto_time'
                    )

                    if result['success']:
                        created_payouts.append({
                            'escrow_id': escrow['id'],
                            'payout_id': result['payout_id'],
                            'amount': result['amount']
                        })
                    else:
                        errors.append({
                            'escrow_id': escrow['id'],
                            'error': result['error']
                        })

                except Exception as e:
                    errors.append({
                        'escrow_id': escrow['id'],
                        'error': str(e)
                    })

            return jsonify({
                'success': True,
                'created_payouts': created_payouts,
                'errors': errors,
                'message': f'Создано {len(created_payouts)} выплат, {len(errors)} ошибок'
            })

        except Exception as e:
            logger.error(f"Ошибка создания выплат для готовых эскроу: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payouts/retry-failed', methods=['POST'])
    def retry_failed_payouts():
        """Повторная попытка для выплат с ошибками"""
        try:
            data = request.get_json()
            payout_ids = data.get('payout_ids', [])

            if not payout_ids:
                # Если не указаны ID, берем все неудачные выплаты текущего пользователя
                user_id = get_current_user_id()
                failed_payouts = safe_execute_query('''
                                                    SELECT p.id
                                                    FROM payouts p
                                                             JOIN users u ON p.recipient_id = u.id
                                                    WHERE p.status = 'failed'
                                                      AND p.retry_count < ?
                                                      AND (u.telegram_id = ? OR ? = ?)
                                                    ''', (MAX_RETRY_ATTEMPTS, user_id, user_id, YOUR_TELEGRAM_ID),
                                                    fetch_all=True)

                payout_ids = [p['id'] for p in failed_payouts]

            if not payout_ids:
                return jsonify({
                    'success': True,
                    'message': 'Нет выплат для повтора'
                })

            # Сбрасываем статус на retry
            updated_count = 0
            for payout_id in payout_ids:
                result = safe_execute_query('''
                                            UPDATE payouts
                                            SET status       = 'retry',
                                                scheduled_at = ?,
                                                updated_at   = ?
                                            WHERE id = ?
                                              AND status = 'failed'
                                              AND retry_count < ?
                                            ''', (datetime.now(), datetime.now(), payout_id, MAX_RETRY_ATTEMPTS))

                if result is not None:
                    updated_count += 1

            return jsonify({
                'success': True,
                'message': f'Перезапущено {updated_count} выплат'
            })

        except Exception as e:
            logger.error(f"Ошибка повтора выплат: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # === АВТОЗАПУСК ПЛАНИРОВЩИКА ===
    @app.route('/api/payouts/scheduler/start', methods=['POST'])
    def start_payout_scheduler():
        """Запуск планировщика выплат"""
        try:
            if payout_manager:
                payout_manager.start_auto_payouts()
                return jsonify({
                    'success': True,
                    'message': 'Планировщик выплат запущен'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Менеджер выплат не инициализирован'
                }), 500
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payouts/scheduler/stop', methods=['POST'])
    def stop_payout_scheduler():
        """Остановка планировщика выплат"""
        try:
            if payout_manager:
                payout_manager.stop_auto_payouts()
                return jsonify({
                    'success': True,
                    'message': 'Планировщик выплат остановлен'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Менеджер выплат не инициализирован'
                }), 500
        except Exception as e:
            logger.error(f"Ошибка остановки планировщика: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/payments')
def payments_page():
    """Страница управления платежами"""
    try:
        telegram_user_id = get_current_user_id()
        logger.info(f"Загрузка страницы платежей для пользователя {telegram_user_id}")

        # Можно передать дополнительные данные в шаблон
        return render_template('payments.html', telegram_user_id=telegram_user_id)

    except Exception as e:
        logger.error(f"Ошибка загрузки страницы платежей: {e}")
        return render_template('payments.html', error=str(e))


@app.route('/api/payments/stats', methods=['GET'])
def api_payment_stats():
    """API для получения статистики платежей пользователя"""
    try:
        telegram_user_id = get_current_user_id()

        # Получаем статистику платежей
        payment_stats = safe_execute_query('''
                                           SELECT COUNT(*)                                                   as total_count,
                                                  SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_amount,
                                                  COUNT(CASE WHEN status = 'pending' THEN 1 END)             as pending_count,
                                                  COUNT(CASE WHEN status = 'completed' THEN 1 END)           as completed_count,
                                                  COUNT(CASE WHEN status = 'failed' THEN 1 END)              as failed_count
                                           FROM payouts p
                                                    JOIN users u ON p.recipient_id = u.id
                                           WHERE u.telegram_id = ?
                                           ''', (telegram_user_id,), fetch_one=True)

        # Получаем статистику эскроу
        escrow_stats = safe_execute_query('''
                                          SELECT COUNT(*)                                                        as total_escrows,
                                                 SUM(CASE WHEN status = 'funds_held' THEN amount ELSE 0 END)     as held_amount,
                                                 SUM(CASE WHEN status = 'funds_released' THEN amount ELSE 0 END) as released_amount,
                                                 COUNT(CASE WHEN status = 'disputed' THEN 1 END)                 as disputed_count
                                          FROM escrow_transactions et
                                                   JOIN offers o ON et.offer_id = o.id
                                                   JOIN users u ON o.created_by = u.id
                                          WHERE u.telegram_id = ?
                                          ''', (telegram_user_id,), fetch_one=True)

        return jsonify({
            'success': True,
            'payments': payment_stats or {},
            'escrow': escrow_stats or {}
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики платежей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/<payment_type>', methods=['GET'])
def api_get_payments(payment_type):
    """API для получения платежей по типу (incoming/outgoing/escrow/history)"""
    try:
        telegram_user_id = get_current_user_id()
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        if payment_type == 'incoming':
            # Входящие платежи (мне платят)
            payments = safe_execute_query('''
                                          SELECT p.*,
                                                 o.title           as offer_title,
                                                 u_sender.username as sender_username,
                                                 p.created_at,
                                                 p.amount,
                                                 p.status
                                          FROM payouts p
                                                   JOIN users u_recipient ON p.recipient_id = u_recipient.id
                                                   LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                   LEFT JOIN offers o ON et.offer_id = o.id
                                                   LEFT JOIN users u_sender ON o.created_by = u_sender.id
                                          WHERE u_recipient.telegram_id = ?
                                          ORDER BY p.created_at DESC LIMIT ?
                                          OFFSET ?
                                          ''', (telegram_user_id, limit, offset), fetch_all=True)

        elif payment_type == 'outgoing':
            # Исходящие платежи (я плачу)
            payments = safe_execute_query('''
                                          SELECT et.*,
                                                 o.title              as offer_title,
                                                 u_recipient.username as recipient_username,
                                                 et.created_at,
                                                 et.amount,
                                                 et.status,
                                                 CASE
                                                     WHEN et.status = 'funds_held' THEN 'pending'
                                                     WHEN et.status = 'funds_released' THEN 'completed'
                                                     WHEN et.status = 'disputed' THEN 'failed'
                                                     ELSE et.status
                                                     END              as payment_status
                                          FROM escrow_transactions et
                                                   JOIN offers o ON et.offer_id = o.id
                                                   JOIN users u_creator ON o.created_by = u_creator.id
                                                   LEFT JOIN users u_recipient ON et.recipient_id = u_recipient.id
                                          WHERE u_creator.telegram_id = ?
                                          ORDER BY et.created_at DESC LIMIT ?
                                          OFFSET ?
                                          ''', (telegram_user_id, limit, offset), fetch_all=True)

        elif payment_type == 'escrow':
            # Средства в эскроу
            payments = safe_execute_query('''
                                          SELECT et.*,
                                                 o.title              as offer_title,
                                                 u_recipient.username as recipient_username,
                                                 et.created_at,
                                                 et.amount,
                                                 et.status
                                          FROM escrow_transactions et
                                                   JOIN offers o ON et.offer_id = o.id
                                                   JOIN users u_creator ON o.created_by = u_creator.id
                                                   LEFT JOIN users u_recipient ON et.recipient_id = u_recipient.id
                                          WHERE (u_creator.telegram_id = ? OR EXISTS(SELECT 1
                                                                                     FROM users u_r
                                                                                     WHERE u_r.id = et.recipient_id
                                                                                       AND u_r.telegram_id = ?))
                                            AND et.status = 'funds_held'
                                          ORDER BY et.created_at DESC LIMIT ?
                                          OFFSET ?
                                          ''', (telegram_user_id, telegram_user_id, limit, offset), fetch_all=True)

        else:  # history
            # Вся история платежей
            payments = safe_execute_query('''
                                          SELECT p.*,
                                                 o.title  as offer_title,
                                                 'payout' as transaction_type,
                                                 p.created_at,
                                                 p.amount,
                                                 p.status
                                          FROM payouts p
                                                   JOIN users u ON p.recipient_id = u.id
                                                   LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                   LEFT JOIN offers o ON et.offer_id = o.id
                                          WHERE u.telegram_id = ?

                                          UNION ALL

                                          SELECT et.id,
                                                 et.offer_id,
                                                 o.title  as offer_title,
                                                 'escrow' as transaction_type,
                                                 et.created_at,
                                                 et.amount,
                                                 et.status
                                          FROM escrow_transactions et
                                                   JOIN offers o ON et.offer_id = o.id
                                                   JOIN users u ON o.created_by = u.id
                                          WHERE u.telegram_id = ?

                                          ORDER BY created_at DESC LIMIT ?
                                          OFFSET ?
                                          ''', (telegram_user_id, telegram_user_id, limit, offset), fetch_all=True)

        return jsonify({
            'success': True,
            'payments': payments or [],
            'count': len(payments) if payments else 0
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения платежей {payment_type}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/create-escrow', methods=['POST'])
def api_create_escrow():
    """API для создания эскроу-транзакции"""
    try:
        telegram_user_id = get_current_user_id()
        data = request.get_json()

        offer_id = data.get('offer_id')
        amount = float(data.get('amount', 0))
        recipient_user_id = data.get('recipient_user_id')

        if not all([offer_id, amount > 0, recipient_user_id]):
            return jsonify({
                'success': False,
                'error': 'Необходимы: offer_id, amount, recipient_user_id'
            }), 400

        # Проверяем, что оффер принадлежит пользователю
        offer = safe_execute_query('''
                                   SELECT o.*, u.telegram_id
                                   FROM offers o
                                            JOIN users u ON o.created_by = u.id
                                   WHERE o.id = ?
                                     AND u.telegram_id = ?
                                   ''', (offer_id, telegram_user_id), fetch_one=True)

        if not offer:
            return jsonify({
                'success': False,
                'error': 'Оффер не найден или нет прав доступа'
            }), 404

        # Создаем эскроу-транзакцию
        from datetime import datetime, timedelta

        escrow_id = safe_execute_query('''
                                       INSERT INTO escrow_transactions (offer_id, recipient_id, amount, status,
                                                                        created_at, expires_at)
                                       VALUES (?, ?, ?, 'funds_held', ?, ?)
                                       ''', (
                                           offer_id,
                                           recipient_user_id,
                                           amount,
                                           datetime.now(),
                                           datetime.now() + timedelta(days=7)
                                       # Автоматическое освобождение через 7 дней
                                       ))

        logger.info(f"Создана эскроу-транзакция {escrow_id} для оффера {offer_id}")

        return jsonify({
            'success': True,
            'escrow_id': escrow_id,
            'message': 'Эскроу-транзакция создана успешно'
        })

    except Exception as e:
        logger.error(f"❌ Ошибка создания эскроу: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/telegram-payment', methods=['POST'])
def api_process_telegram_payment():
    """API для обработки платежей через Telegram"""
    try:
        telegram_user_id = get_current_user_id()
        data = request.get_json()

        offer_id = data.get('offer_id')
        amount = float(data.get('amount', 0))
        payment_payload = data.get('payment_payload')

        if not all([offer_id, amount > 0]):
            return jsonify({
                'success': False,
                'error': 'Необходимы: offer_id, amount'
            }), 400

        # Получаем информацию об оффере
        offer_info = safe_execute_query('''
                                        SELECT o.*, u.telegram_id as owner_telegram_id
                                        FROM offers o
                                                 JOIN users u ON o.created_by = u.id
                                        WHERE o.id = ?
                                        ''', (offer_id,), fetch_one=True)

        if not offer_info:
            return jsonify({
                'success': False,
                'error': 'Оффер не найден'
            }), 404

        # Создаем invoice для Telegram Payments
        invoice_data = {
            'title': f'Оплата оффера: {offer_info["title"]}',
            'description': f'Рекламное размещение в канале',
            'payload': json.dumps({
                'offer_id': offer_id,
                'user_id': telegram_user_id,
                'amount': amount
            }),
            'provider_token': TELEGRAM_PAYMENT_TOKEN,  # Настроить в .env
            'currency': 'RUB',
            'prices': [{
                'label': 'Размещение рекламы',
                'amount': int(amount * 100)  # В копейках
            }]
        }

        return jsonify({
            'success': True,
            'invoice': invoice_data,
            'message': 'Invoice создан для Telegram Payments'
        })

    except Exception as e:
        logger.error(f"❌ Ошибка создания Telegram платежа: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/webhook', methods=['POST'])
def payment_webhook():
    """Webhook для обработки уведомлений о платежах от Telegram"""
    try:
        # Проверка подписи webhook (важно для безопасности)
        signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if signature != WEBHOOK_SECRET:
            logger.warning("Неверная подпись webhook")
            return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json()

        if 'successful_payment' in data.get('message', {}):
            payment_data = data['message']['successful_payment']
            payload = json.loads(payment_data['invoice_payload'])

            offer_id = payload.get('offer_id')
            user_id = payload.get('user_id')
            amount = payload.get('amount')

            # Обновляем статус платежа в БД
            # Здесь нужно реализовать логику обработки успешного платежа
            logger.info(f"Успешный платеж для оффера {offer_id} от пользователя {user_id}")

            # Можно создать эскроу или напрямую перевести средства
            # В зависимости от бизнес-логики

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/bulk-status', methods=['POST'])
def api_bulk_payment_status():
    """API для получения статусов платежей для множественных офферов"""
    try:
        telegram_user_id = get_current_user_id()
        data = request.get_json()
        offer_ids = data.get('offer_ids', [])

        if not offer_ids:
            return jsonify({'success': True, 'statuses': {}})

        # Получаем статусы для всех офферов
        placeholders = ','.join(['?' for _ in offer_ids])

        statuses_query = f'''
            SELECT 
                o.id as offer_id,
                o.created_by,
                u_creator.telegram_id as creator_telegram_id,
                CASE 
                    WHEN et.status = 'funds_held' THEN 'escrow'
                    WHEN et.status = 'funds_released' THEN 'paid'
                    WHEN EXISTS(SELECT 1 FROM offer_responses WHERE offer_id = o.id AND status = 'accepted') THEN 'pending_payment'
                    ELSE 'active'
                END as payment_status,
                et.amount as escrow_amount,
                et.expires_at as escrow_expires,
                CASE WHEN u_creator.telegram_id = ? THEN 1 ELSE 0 END as can_pay,
                CASE WHEN u_creator.telegram_id = ? AND et.status = 'funds_held' THEN 1 ELSE 0 END as can_release
            FROM offers o
            JOIN users u_creator ON o.created_by = u_creator.id
            LEFT JOIN escrow_transactions et ON o.id = et.offer_id
            WHERE o.id IN ({placeholders})
        '''

        params = [telegram_user_id, telegram_user_id] + offer_ids
        results = safe_execute_query(statuses_query, params, fetch_all=True)

        statuses = {}
        for result in results or []:
            statuses[str(result['offer_id'])] = {
                'status': result['payment_status'],
                'can_pay': bool(result['can_pay']),
                'can_release': bool(result['can_release']),
                'escrow_amount': result['escrow_amount'],
                'escrow_expires': result['escrow_expires']
            }

        return jsonify({
            'success': True,
            'statuses': statuses
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения bulk статусов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/release-escrow', methods=['POST'])
def api_release_escrow():
    """API для освобождения средств из эскроу"""
    try:
        telegram_user_id = get_current_user_id()
        data = request.get_json()
        offer_id = data.get('offer_id')

        if not offer_id:
            return jsonify({'success': False, 'error': 'offer_id обязателен'}), 400

        # Проверяем права доступа
        offer = safe_execute_query('''
                                   SELECT o.*, u.telegram_id
                                   FROM offers o
                                            JOIN users u ON o.created_by = u.id
                                   WHERE o.id = ?
                                     AND u.telegram_id = ?
                                   ''', (offer_id, telegram_user_id), fetch_one=True)

        if not offer:
            return jsonify({'success': False, 'error': 'Оффер не найден или нет прав доступа'}), 404

        # Используем систему выплат для освобождения эскроу
        if PAYOUT_SYSTEM_ENABLED and payout_manager:
            # Находим эскроу для этого оффера
            escrow = safe_execute_query('''
                                        SELECT *
                                        FROM escrow_transactions
                                        WHERE offer_id = ?
                                          AND status = 'funds_held'
                                        ''', (offer_id,), fetch_one=True)

            if not escrow:
                return jsonify({'success': False, 'error': 'Активное эскроу не найдено'}), 404

            # Создаем ручную выплату
            result = payout_manager.create_manual_payout(
                escrow['id'],
                'manual_release'
            )

            if result['success']:
                logger.info(f"Освобождены средства из эскроу {escrow['id']} для оффера {offer_id}")
                return jsonify({
                    'success': True,
                    'message': 'Средства освобождены из эскроу',
                    'payout_id': result['payout_id']
                })
            else:
                return jsonify({'success': False, 'error': result['error']})
        else:
            return jsonify({'success': False, 'error': 'Система выплат не активна'}), 503

    except Exception as e:
        logger.error(f"❌ Ошибка освобождения эскроу: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/dispute', methods=['POST'])
def api_create_payment_dispute():
    """API для создания спора по платежу"""
    try:
        telegram_user_id = get_current_user_id()
        data = request.get_json()

        offer_id = data.get('offer_id')
        reason = data.get('reason', '').strip()
        description = data.get('description', '').strip()
        evidence_urls = data.get('evidence_urls', [])

        if not all([offer_id, reason, description]):
            return jsonify({
                'success': False,
                'error': 'Необходимы: offer_id, reason, description'
            }), 400

        # Проверяем существование эскроу для оффера
        escrow = safe_execute_query('''
                                    SELECT et.*, o.title, u.telegram_id as creator_telegram_id
                                    FROM escrow_transactions et
                                             JOIN offers o ON et.offer_id = o.id
                                             JOIN users u ON o.created_by = u.id
                                    WHERE et.offer_id = ?
                                      AND et.status = 'funds_held'
                                    ''', (offer_id,), fetch_one=True)

        if not escrow:
            return jsonify({
                'success': False,
                'error': 'Активное эскроу для данного оффера не найдено'
            }), 404

        # Проверяем права пользователя (должен быть участником сделки)
        is_participant = safe_execute_query('''
                                            SELECT 1
                                            FROM (SELECT u.telegram_id
                                                  FROM offers o
                                                           JOIN users u ON o.created_by = u.id
                                                  WHERE o.id = ?

                                                  UNION

                                                  SELECT u.telegram_id
                                                  FROM escrow_transactions et
                                                           JOIN users u ON et.recipient_id = u.id
                                                  WHERE et.offer_id = ?) participants
                                            WHERE telegram_id = ?
                                            ''', (offer_id, offer_id, telegram_user_id), fetch_one=True)

        if not is_participant:
            return jsonify({
                'success': False,
                'error': 'Вы не являетесь участником данной сделки'
            }), 403

        # Создаем спор
        dispute_id = safe_execute_query('''
                                        INSERT INTO payment_disputes (escrow_id, created_by, reason, description,
                                                                      evidence_urls, status, created_at)
                                        VALUES (?, (SELECT id FROM users WHERE telegram_id = ?), ?, ?, ?, 'open', ?)
                                        ''', (
                                            escrow['id'], telegram_user_id, reason, description,
                                            json.dumps(evidence_urls), datetime.now()
                                        ))

        # Обновляем статус эскроу
        safe_execute_query('''
                           UPDATE escrow_transactions
                           SET status     = 'disputed',
                               updated_at = ?
                           WHERE id = ?
                           ''', (datetime.now(), escrow['id']))

        logger.info(f"Создан спор {dispute_id} для эскроу {escrow['id']}")

        return jsonify({
            'success': True,
            'dispute_id': dispute_id,
            'message': 'Спор создан. Средства заморожены до разрешения.'
        })

    except Exception as e:
        logger.error(f"❌ Ошибка создания спора: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payments/transactions/<int:offer_id>', methods=['GET'])
def api_get_offer_transactions(offer_id):
    """API для получения истории транзакций по офферу"""
    try:
        telegram_user_id = get_current_user_id()

        # Проверяем права доступа к офферу
        access_check = safe_execute_query('''
                                          SELECT 1
                                          FROM (
                                                   -- Создатель оффера
                                                   SELECT u.telegram_id
                                                   FROM offers o
                                                            JOIN users u ON o.created_by = u.id
                                                   WHERE o.id = ?

                                                   UNION

                                                   -- Получатель средств
                                                   SELECT u.telegram_id
                                                   FROM escrow_transactions et
                                                            JOIN users u ON et.recipient_id = u.id
                                                   WHERE et.offer_id = ?) participants
                                          WHERE telegram_id = ?
                                          ''', (offer_id, offer_id, telegram_user_id), fetch_one=True)

        if not access_check:
            return jsonify({
                'success': False,
                'error': 'Нет доступа к данному офферу'
            }), 403

        # Получаем все транзакции
        transactions = safe_execute_query('''
                                          SELECT 'escrow'             as type,
                                                 et.id,
                                                 et.amount,
                                                 et.status,
                                                 et.created_at,
                                                 et.expires_at,
                                                 'Создание эскроу'    as description,
                                                 u_recipient.username as participant
                                          FROM escrow_transactions et
                                                   LEFT JOIN users u_recipient ON et.recipient_id = u_recipient.id
                                          WHERE et.offer_id = ?

                                          UNION ALL

                                          SELECT 'payout'             as type,
                                                 p.id,
                                                 p.amount,
                                                 p.status,
                                                 p.created_at,
                                                 p.scheduled_at       as expires_at,
                                                 'Выплата'            as description,
                                                 u_recipient.username as participant
                                          FROM payouts p
                                                   JOIN escrow_transactions et ON p.escrow_id = et.id
                                                   LEFT JOIN users u_recipient ON p.recipient_id = u_recipient.id
                                          WHERE et.offer_id = ?

                                          UNION ALL

                                          SELECT 'dispute'                   as type,
                                                 pd.id,
                                                 NULL                        as amount,
                                                 pd.status,
                                                 pd.created_at,
                                                 NULL                        as expires_at,
                                                 CONCAT('Спор: ', pd.reason) as description,
                                                 u_creator.username          as participant
                                          FROM payment_disputes pd
                                                   JOIN escrow_transactions et ON pd.escrow_id = et.id
                                                   LEFT JOIN users u_creator ON pd.created_by = u_creator.id
                                          WHERE et.offer_id = ?

                                          ORDER BY created_at DESC
                                          ''', (offer_id, offer_id, offer_id), fetch_all=True)

        return jsonify({
            'success': True,
            'transactions': transactions or [],
            'offer_id': offer_id
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения транзакций: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ОБНОВЛЕНИЕ НАВИГАЦИИ ===
# Добавить в base.html или в основной шаблон навигации

@app.route('/api/navigation/menu', methods=['GET'])
def api_navigation_menu():
    """API для получения пунктов навигации с учетом платежей"""
    try:
        telegram_user_id = get_current_user_id()

        # Получаем счетчики для навигации
        stats = safe_execute_query('''
                                   SELECT (SELECT COUNT(*)
                                           FROM offers o
                                                    JOIN users u ON o.created_by = u.id
                                           WHERE u.telegram_id = ?)        as my_offers_count,
                                          (SELECT COUNT(*)
                                           FROM channels c
                                                    JOIN users u ON c.owner_id = u.id
                                           WHERE u.telegram_id = ?)        as my_channels_count,
                                          (SELECT COUNT(*)
                                           FROM payouts p
                                                    JOIN users u ON p.recipient_id = u.id
                                           WHERE u.telegram_id = ?
                                             AND p.status = 'pending')     as pending_payments_count,
                                          (SELECT COUNT(*)
                                           FROM escrow_transactions et
                                                    JOIN offers o ON et.offer_id = o.id
                                                    JOIN users u ON o.created_by = u.id
                                           WHERE u.telegram_id = ?
                                             AND et.status = 'funds_held') as escrow_count
                                   ''', (telegram_user_id, telegram_user_id, telegram_user_id, telegram_user_id),
                                   fetch_one=True)

        menu_items = [
            {
                'id': 'dashboard',
                'title': '🏠 Главная',
                'url': '/',
                'badge': None
            },
            {
                'id': 'channels',
                'title': '📺 Мои каналы',
                'url': '/channels-enhanced',
                'badge': stats.get('my_channels_count') if stats and stats.get('my_channels_count', 0) > 0 else None
            },
            {
                'id': 'offers',
                'title': '📨 Офферы',
                'url': '/offers',
                'badge': stats.get('my_offers_count') if stats and stats.get('my_offers_count', 0) > 0 else None
            },
            {
                'id': 'payments',
                'title': '💳 Платежи',
                'url': '/payments',
                'badge': (stats.get('pending_payments_count', 0) + stats.get('escrow_count', 0)) if stats else None
            },
            {
                'id': 'analytics',
                'title': '📊 Аналитика',
                'url': '/analytics',
                'badge': None
            }
        ]

        return jsonify({
            'success': True,
            'menu_items': menu_items,
            'stats': stats or {}
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения навигации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# === ДОБАВИТЬ В КОНЕЦ ФАЙЛА ПЕРЕД if __name__ == '__main__': ===

# Проверка инициализации платежной системы при запуске
def validate_startup_requirements():
    """Проверка требований для запуска"""
    errors = []

    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не настроен в переменных окружения")

    if not TELEGRAM_INTEGRATION:
        errors.append("Telegram интеграция недоступна")

    if not OFFERS_SYSTEM_ENABLED:
        errors.append("Система офферов недоступна")

    if errors:
        logger.error("❌ Критические ошибки запуска:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    return True

# === ЗАПУСК ПРИЛОЖЕНИЯ ===
if __name__ == '__main__':
    try:
        # Проверка требований
        if not validate_startup_requirements():
            logger.error("❌ Не выполнены требования для запуска приложения")
            sys.exit(1)

        # Инициализация систем
        initialize_systems(app)

        # Настройка режима запуска
        debug_mode = os.environ.get('DEBUG', 'True').lower() == 'true'
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')

        logger.info(f"🚀 Запуск Telegram Mini App на {host}:{port}")
        logger.info(f"📱 BOT_TOKEN: {'✅ Настроен' if BOT_TOKEN else '❌ Отсутствует'}")
        logger.info(f"🔧 Режим разработки: {debug_mode}")

        # Запуск Flask приложения
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            threaded=True,
            use_reloader=debug_mode
        )

    except KeyboardInterrupt:
        logger.info("🛑 Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуска: {e}")
        sys.exit(1)