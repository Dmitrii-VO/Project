#!/usr/bin/env python3
"""
Унифицированная конфигурация для Telegram Mini App
Объединяет все настройки приложения в один файл
"""

import os
import sys
from typing import Optional

# Автоматический поиск и добавление путей
def find_project_root():
    """Автоматически находит корень проекта"""
    current = os.path.dirname(os.path.abspath(__file__))
    
    # Поднимаемся вверх, пока не найдем признаки корня проекта
    while current != os.path.dirname(current):  # Пока не дошли до корня диска
        markers = ['telegram_mini_app.db', 'requirements.txt', '.env', '.git']
        if any(os.path.exists(os.path.join(current, marker)) for marker in markers):
            return current
        current = os.path.dirname(current)
    
    # Если не нашли, возвращаем текущую папку
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = find_project_root()
APP_PATH = os.path.join(PROJECT_ROOT, 'app')

for path in [PROJECT_ROOT, APP_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ДЛЯ СОВМЕСТИМОСТИ ===

# Telegram настройки
BOT_TOKEN: Optional[str] = os.environ.get('BOT_TOKEN')
TELEGRAM_BOT_TOKEN: Optional[str] = BOT_TOKEN  # Алиас для совместимости

# Константы для откликов (Response model)
AUTO_ACCEPT_TIMEOUT_HOURS: int = int(os.environ.get('AUTO_ACCEPT_TIMEOUT_HOURS', '24'))
MAX_COUNTER_OFFERS: int = int(os.environ.get('MAX_COUNTER_OFFERS', '3'))

# Константы для офферов (Offer model)
MIN_OFFER_BUDGET: float = float(os.environ.get('MIN_OFFER_BUDGET', '100.0'))
MAX_OFFER_BUDGET: float = float(os.environ.get('MAX_OFFER_BUDGET', '1000000.0'))
DEFAULT_OFFER_DURATION_DAYS: int = int(os.environ.get('DEFAULT_OFFER_DURATION_DAYS', '7'))
MAX_OFFER_DURATION_DAYS: int = int(os.environ.get('MAX_OFFER_DURATION_DAYS', '30'))

# Константы для каналов (Channel model)
MIN_SUBSCRIBERS_COUNT: int = int(os.environ.get('MIN_SUBSCRIBERS_COUNT', '100'))
MAX_PRICE_PER_POST: float = float(os.environ.get('MAX_PRICE_PER_POST', '100000.0'))
VERIFICATION_CODE_LENGTH: int = int(os.environ.get('VERIFICATION_CODE_LENGTH', '6'))
CHANNEL_STATS_UPDATE_INTERVAL_HOURS: int = int(os.environ.get('CHANNEL_STATS_UPDATE_INTERVAL_HOURS', '24'))
MAX_CHANNELS_PER_USER: int = int(os.environ.get('MAX_CHANNELS_PER_USER', '10'))
TELEGRAM_API_TIMEOUT: int = int(os.environ.get('TELEGRAM_API_TIMEOUT', '30'))

# Константы для пользователей (User model)
MIN_BALANCE_WITHDRAWAL: float = float(os.environ.get('MIN_BALANCE_WITHDRAWAL', '50.0'))
MIN_WITHDRAWAL_AMOUNT: float = MIN_BALANCE_WITHDRAWAL  # Алиас для совместимости
MAX_DAILY_WITHDRAWAL: float = float(os.environ.get('MAX_DAILY_WITHDRAWAL', '10000.0'))
DEFAULT_DAILY_WITHDRAWAL_LIMIT: float = float(os.environ.get('DEFAULT_DAILY_WITHDRAWAL_LIMIT', '1000.0'))
REFERRAL_BONUS_AMOUNT: float = float(os.environ.get('REFERRAL_BONUS_AMOUNT', '100.0'))

# Константы для платежей (Payment model)
MIN_PAYMENT_AMOUNT: float = float(os.environ.get('MIN_PAYMENT_AMOUNT', '10.0'))
MAX_PAYMENT_AMOUNT: float = float(os.environ.get('MAX_PAYMENT_AMOUNT', '50000.0'))
PAYMENT_PROCESSING_FEE_PERCENT: float = float(os.environ.get('PAYMENT_PROCESSING_FEE_PERCENT', '2.5'))
ESCROW_HOLD_DAYS: int = int(os.environ.get('ESCROW_HOLD_DAYS', '7'))
ESCROW_FEE_PERCENT: float = float(os.environ.get('ESCROW_FEE_PERCENT', '1.0'))
MAX_WITHDRAWAL_AMOUNT: float = MAX_DAILY_WITHDRAWAL  # Алиас для совместимости

# Константы для rate limiting
DEFAULT_RATE_LIMIT_PER_HOUR: int = int(os.environ.get('DEFAULT_RATE_LIMIT_PER_HOUR', '100'))
API_RATE_LIMIT_PER_MINUTE: int = int(os.environ.get('API_RATE_LIMIT_PER_MINUTE', '60'))
TELEGRAM_API_RATE_LIMIT: int = int(os.environ.get('TELEGRAM_API_RATE_LIMIT', '30'))

# Константы для аналитики
ANALYTICS_RETENTION_DAYS: int = int(os.environ.get('ANALYTICS_RETENTION_DAYS', '365'))
REPORTS_CACHE_TTL_MINUTES: int = int(os.environ.get('REPORTS_CACHE_TTL_MINUTES', '30'))

# Константы для уведомлений
NOTIFICATION_BATCH_SIZE: int = int(os.environ.get('NOTIFICATION_BATCH_SIZE', '100'))
NOTIFICATION_RETRY_ATTEMPTS: int = int(os.environ.get('NOTIFICATION_RETRY_ATTEMPTS', '3'))

# Константы для валидации контента
MAX_OFFER_TITLE_LENGTH: int = int(os.environ.get('MAX_OFFER_TITLE_LENGTH', '100'))
MAX_OFFER_DESCRIPTION_LENGTH: int = int(os.environ.get('MAX_OFFER_DESCRIPTION_LENGTH', '2000'))
MAX_CHANNEL_DESCRIPTION_LENGTH: int = int(os.environ.get('MAX_CHANNEL_DESCRIPTION_LENGTH', '500'))
MAX_RESPONSE_MESSAGE_LENGTH: int = int(os.environ.get('MAX_RESPONSE_MESSAGE_LENGTH', '1000'))

# Константы для файлов и медиа
MAX_UPLOAD_SIZE_MB: int = int(os.environ.get('MAX_UPLOAD_SIZE_MB', '10'))
ALLOWED_IMAGE_EXTENSIONS: list = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_VIDEO_EXTENSIONS: list = ['mp4', 'mov', 'avi', 'webm']

# Константы для сопоставления (matching)
MATCHING_SCORE_THRESHOLD: float = float(os.environ.get('MATCHING_SCORE_THRESHOLD', '0.7'))
AUTO_MATCH_ENABLED: bool = os.environ.get('AUTO_MATCH_ENABLED', 'True').lower() == 'true'
MAX_AUTO_MATCHES_PER_OFFER: int = int(os.environ.get('MAX_AUTO_MATCHES_PER_OFFER', '20'))

# Временные зоны и локализация
DEFAULT_TIMEZONE: str = os.environ.get('DEFAULT_TIMEZONE', 'UTC')
SUPPORTED_LANGUAGES: list = ['ru', 'en', 'uk']
DEFAULT_LANGUAGE: str = os.environ.get('DEFAULT_LANGUAGE', 'ru')

# Константы для кэширования
CACHE_TTL_SECONDS: int = int(os.environ.get('CACHE_TTL_SECONDS', '300'))
REDIS_TTL_HOURS: int = int(os.environ.get('REDIS_TTL_HOURS', '24'))

# Константы для безопасности
REQUEST_LIMIT: int = int(os.environ.get('REQUEST_LIMIT', '100'))
TIME_WINDOW: int = int(os.environ.get('TIME_WINDOW', '3600'))

# === КЛАССЫ СТАТУСОВ ===

class ChannelCategories:
    """Категории каналов"""
    TECH = 'tech'
    BUSINESS = 'business'
    ENTERTAINMENT = 'entertainment'
    NEWS = 'news'
    EDUCATION = 'education'
    LIFESTYLE = 'lifestyle'
    GAMING = 'gaming'
    CRYPTO = 'crypto'
    HEALTH = 'health'
    TRAVEL = 'travel'
    FOOD = 'food'
    SPORTS = 'sports'
    MUSIC = 'music'
    ART = 'art'
    SCIENCE = 'science'
    POLITICS = 'politics'
    FINANCE = 'finance'
    AUTOMOTIVE = 'automotive'
    REAL_ESTATE = 'real_estate'
    OTHER = 'other'

    @classmethod
    def get_all_categories(cls) -> list:
        """Получить все категории"""
        return [
            cls.TECH, cls.BUSINESS, cls.ENTERTAINMENT, cls.NEWS,
            cls.EDUCATION, cls.LIFESTYLE, cls.GAMING, cls.CRYPTO,
            cls.HEALTH, cls.TRAVEL, cls.FOOD, cls.SPORTS,
            cls.MUSIC, cls.ART, cls.SCIENCE, cls.POLITICS,
            cls.FINANCE, cls.AUTOMOTIVE, cls.REAL_ESTATE, cls.OTHER
        ]

    @classmethod
    def get_category_names(cls) -> dict:
        """Получить названия категорий на русском"""
        return {
            cls.TECH: 'Технологии',
            cls.BUSINESS: 'Бизнес',
            cls.ENTERTAINMENT: 'Развлечения',
            cls.NEWS: 'Новости',
            cls.EDUCATION: 'Образование',
            cls.LIFESTYLE: 'Стиль жизни',
            cls.GAMING: 'Игры',
            cls.CRYPTO: 'Криптовалюты',
            cls.HEALTH: 'Здоровье',
            cls.TRAVEL: 'Путешествия',
            cls.FOOD: 'Еда',
            cls.SPORTS: 'Спорт',
            cls.MUSIC: 'Музыка',
            cls.ART: 'Искусство',
            cls.SCIENCE: 'Наука',
            cls.POLITICS: 'Политика',
            cls.FINANCE: 'Финансы',
            cls.AUTOMOTIVE: 'Автомобили',
            cls.REAL_ESTATE: 'Недвижимость',
            cls.OTHER: 'Другое'
        }


class OfferStatuses:
    """Статусы офферов"""
    DRAFT = 'draft'
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class ResponseStatuses:
    """Статусы откликов"""
    PENDING = 'pending'
    INTERESTED = 'interested'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    COUNTER_OFFERED = 'counter_offered'
    POSTED = 'posted'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class PaymentStatuses:
    """Статусы платежей"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'


class UserTypes:
    """Типы пользователей"""
    ADVERTISER = 'advertiser'
    CHANNEL_OWNER = 'channel_owner'
    BOTH = 'both'
    ADMIN = 'admin'

    @classmethod
    def get_all_types(cls) -> list:
        """Получить все типы пользователей"""
        return [cls.ADVERTISER, cls.CHANNEL_OWNER, cls.BOTH, cls.ADMIN]

    @classmethod
    def get_type_names(cls) -> dict:
        """Получить названия типов на русском"""
        return {
            cls.ADVERTISER: 'Рекламодатель',
            cls.CHANNEL_OWNER: 'Владелец канала',
            cls.BOTH: 'Рекламодатель и владелец',
            cls.ADMIN: 'Администратор'
        }


# Константа по умолчанию для типа пользователя
DEFAULT_USER_TYPE: str = UserTypes.ADVERTISER


# === ОСНОВНОЙ КЛАСС КОНФИГУРАЦИИ ===

class AppConfig:
    """Централизованная конфигурация приложения"""

    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'True').lower() == 'true'

    # === БАЗА ДАННЫХ ===
    DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
    DATABASE_PATH: str = os.path.join(PROJECT_ROOT, 'telegram_mini_app.db')

    # Flask-SQLAlchemy настройки
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # === TELEGRAM НАСТРОЙКИ ===
    BOT_TOKEN: Optional[str] = BOT_TOKEN
    YOUR_TELEGRAM_ID: int = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))
    WEBAPP_URL: Optional[str] = os.environ.get('WEBAPP_URL', 'http://localhost:5000')

    # === ПЛАТЕЖНАЯ СИСТЕМА ===
    TELEGRAM_PAYMENT_TOKEN: Optional[str] = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
    WEBHOOK_SECRET: str = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')

    # === НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ===
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = DEBUG

    # === ФУНКЦИОНАЛЬНОСТЬ СИСТЕМЫ ===
    TELEGRAM_INTEGRATION: bool = os.environ.get('TELEGRAM_INTEGRATION', 'True').lower() == 'true'
    OFFERS_SYSTEM_ENABLED: bool = os.environ.get('OFFERS_SYSTEM_ENABLED', 'True').lower() == 'true'
    RESPONSES_SYSTEM_ENABLED: bool = os.environ.get('RESPONSES_SYSTEM_ENABLED', 'True').lower() == 'true'
    PAYMENTS_SYSTEM_ENABLED: bool = os.environ.get('PAYMENTS_SYSTEM_ENABLED', 'True').lower() == 'true'
    ANALYTICS_SYSTEM_ENABLED: bool = os.environ.get('ANALYTICS_SYSTEM_ENABLED', 'True').lower() == 'true'
    PLACEMENT_TRACKING_ENABLED: bool = os.environ.get('PLACEMENT_TRACKING_ENABLED', 'True').lower() == 'true'
    AI_RECOMMENDATIONS_ENABLED: bool = os.environ.get('AI_RECOMMENDATIONS_ENABLED', 'True').lower() == 'true'
    ADVANCED_MATCHING_ENABLED: bool = os.environ.get('ADVANCED_MATCHING_ENABLED', 'True').lower() == 'true'
    NOTIFICATIONS_ENABLED: bool = os.environ.get('NOTIFICATIONS_ENABLED', 'True').lower() == 'true'
    PAYOUT_SYSTEM_ENABLED: bool = os.environ.get('PAYOUT_SYSTEM_ENABLED', 'True').lower() == 'true'

    # === ВЫПЛАТЫ И ЛИМИТЫ ===
    DEFAULT_ESCROW_PERIOD: int = int(os.environ.get('DEFAULT_ESCROW_PERIOD', '7'))
    MIN_PAYOUT_AMOUNT: int = int(os.environ.get('MIN_PAYOUT_AMOUNT', '100'))
    MAX_RETRY_ATTEMPTS: int = int(os.environ.get('MAX_RETRY_ATTEMPTS', '3'))

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

    @classmethod
    def validate_config(cls) -> bool:
        """Проверка критических настроек (алиас для совместимости)"""
        return cls.validate()


# === КОНФИГУРАЦИИ ДЛЯ РАЗНЫХ ОКРУЖЕНИЙ ===

class DevelopmentConfig(AppConfig):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING_MODE = True
    SEED_TEST_DATA = True
    MOCK_TELEGRAM_API = True


class ProductionConfig(AppConfig):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING_MODE = False
    SEED_TEST_DATA = False
    MOCK_TELEGRAM_API = False
    PERFORMANCE_LOG_ENABLED = True


class TestingConfig(AppConfig):
    """Конфигурация для тестирования"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    MOCK_TELEGRAM_API = True
    SEED_TEST_DATA = True


# === АВТОМАТИЧЕСКИЙ ВЫБОР КОНФИГУРАЦИИ ===

def get_config_by_environment() -> AppConfig:
    """Автоматический выбор конфигурации по переменной окружения"""
    env = os.environ.get('FLASK_ENV', 'development').lower()

    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()


# === АЛИАСЫ ДЛЯ СОВМЕСТИМОСТИ ===

# Для обратной совместимости создаем алиас Config
Config = AppConfig

# Экспорт констант для удобства импорта
__all__ = [
    'AppConfig',
    'Config',  # Алиас для совместимости
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
    'get_config_by_environment',
    'ChannelCategories',
    'OfferStatuses',
    'ResponseStatuses',
    'PaymentStatuses',
    'UserTypes',
    'DEFAULT_USER_TYPE',
    # Экспорт констант
    'BOT_TOKEN',
    'TELEGRAM_BOT_TOKEN',
    'AUTO_ACCEPT_TIMEOUT_HOURS',
    'MAX_COUNTER_OFFERS',
    'MIN_OFFER_BUDGET',
    'MAX_OFFER_BUDGET',
    'MIN_SUBSCRIBERS_COUNT',
    'MAX_PRICE_PER_POST',
    'VERIFICATION_CODE_LENGTH',
    'MAX_CHANNELS_PER_USER',
    'TELEGRAM_API_TIMEOUT',
    'REQUEST_LIMIT',
    'TIME_WINDOW'
]