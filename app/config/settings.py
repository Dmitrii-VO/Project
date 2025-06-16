# app/config/settings.py


"""
Конфигурация для Telegram Mini App рекламной платформы
Содержит все настройки приложения, включая константы для моделей
"""

import os
from typing import Optional

# === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ДЛЯ ИМПОРТА В МОДЕЛИ ===

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


class Config:
    """Базовая конфигурация приложения"""

    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'

    # === БАЗА ДАННЫХ ===
    DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
    DATABASE_PATH: str = DATABASE_URL.replace('sqlite:///', '')

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
    WEBAPP_URL: Optional[str] = os.environ.get('WEBAPP_URL')

    # === ПЛАТЕЖНАЯ СИСТЕМА ===
    TELEGRAM_PAYMENT_TOKEN: Optional[str] = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
    WEBHOOK_SECRET: str = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')

    # === БЕЗОПАСНОСТЬ ===
    REQUEST_LIMIT: int = 100
    TIME_WINDOW: int = 3600

    # === ФУНКЦИОНАЛЬНОСТЬ СИСТЕМЫ ===
    TELEGRAM_INTEGRATION: bool = True
    OFFERS_SYSTEM_ENABLED: bool = True
    RESPONSES_SYSTEM_ENABLED: bool = True
    PAYMENTS_SYSTEM_ENABLED: bool = True
    ANALYTICS_SYSTEM_ENABLED: bool = True
    PLACEMENT_TRACKING_ENABLED: bool = True
    AI_RECOMMENDATIONS_ENABLED: bool = True
    ADVANCED_MATCHING_ENABLED: bool = True
    NOTIFICATIONS_ENABLED: bool = True
    PAYOUT_SYSTEM_ENABLED: bool = True

    @classmethod
    def validate_config(cls) -> bool:
        """Проверка критических настроек"""
        if not BOT_TOKEN:  # Используем глобальную константу
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не настроен!")
            return False

        if not os.path.exists(cls.DATABASE_PATH):
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: База данных не найдена: {cls.DATABASE_PATH}")
            return False

        return True


# === ДОПОЛНИТЕЛЬНЫЕ КОНСТАНТЫ ===

# === ДОПОЛНИТЕЛЬНЫЕ КОНСТАНТЫ ===

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
CACHE_TTL_SECONDS: int = int(os.environ.get('CACHE_TTL_SECONDS', '3600'))
STATISTICS_CACHE_TTL: int = int(os.environ.get('STATISTICS_CACHE_TTL', '1800'))
CHANNEL_INFO_CACHE_TTL: int = int(os.environ.get('CHANNEL_INFO_CACHE_TTL', '7200'))

# Константы для безопасности
SESSION_TIMEOUT_HOURS: int = int(os.environ.get('SESSION_TIMEOUT_HOURS', '24'))
PASSWORD_MIN_LENGTH: int = int(os.environ.get('PASSWORD_MIN_LENGTH', '8'))
MAX_LOGIN_ATTEMPTS: int = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
ACCOUNT_LOCKOUT_MINUTES: int = int(os.environ.get('ACCOUNT_LOCKOUT_MINUTES', '30'))

# Константы для мониторинга и логов
LOG_RETENTION_DAYS: int = int(os.environ.get('LOG_RETENTION_DAYS', '30'))
ERROR_LOG_MAX_SIZE_MB: int = int(os.environ.get('ERROR_LOG_MAX_SIZE_MB', '100'))
PERFORMANCE_LOG_ENABLED: bool = os.environ.get('PERFORMANCE_LOG_ENABLED', 'False').lower() == 'true'

# Константы для интеграций
WEBHOOK_TIMEOUT_SECONDS: int = int(os.environ.get('WEBHOOK_TIMEOUT_SECONDS', '30'))
EXTERNAL_API_TIMEOUT_SECONDS: int = int(os.environ.get('EXTERNAL_API_TIMEOUT_SECONDS', '10'))
RETRY_DELAYS_SECONDS: list = [1, 2, 4, 8, 16]  # Экспоненциальная задержка
# Алиас для совместимости с моделями
TELEGRAM_API_TIMEOUT: int = EXTERNAL_API_TIMEOUT_SECONDS

# Деловые константы
COMMISSION_RATE_PERCENT: float = float(os.environ.get('COMMISSION_RATE_PERCENT', '5.0'))
PREMIUM_COMMISSION_RATE_PERCENT: float = float(os.environ.get('PREMIUM_COMMISSION_RATE_PERCENT', '3.0'))
REFERRAL_BONUS_PERCENT: float = float(os.environ.get('REFERRAL_BONUS_PERCENT', '10.0'))

# Ограничения платформы
MAX_CHANNELS_PER_USER: int = int(os.environ.get('MAX_CHANNELS_PER_USER', '10'))
MAX_ACTIVE_OFFERS_PER_USER: int = int(os.environ.get('MAX_ACTIVE_OFFERS_PER_USER', '50'))
MAX_RESPONSES_PER_OFFER: int = int(os.environ.get('MAX_RESPONSES_PER_OFFER', '100'))

# Константы для разработки и тестирования
TESTING_MODE: bool = os.environ.get('TESTING_MODE', 'False').lower() == 'true'
MOCK_TELEGRAM_API: bool = os.environ.get('MOCK_TELEGRAM_API', 'False').lower() == 'true'
SEED_TEST_DATA: bool = os.environ.get('SEED_TEST_DATA', 'False').lower() == 'true'


# === КАТЕГОРИИ КАНАЛОВ ===
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


# === СТАТУСЫ СИСТЕМЫ ===
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


# === КОНФИГУРАЦИЯ ОКРУЖЕНИЙ ===
class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    TESTING_MODE = True
    SEED_TEST_DATA = True
    MOCK_TELEGRAM_API = True


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    TESTING_MODE = False
    SEED_TEST_DATA = False
    MOCK_TELEGRAM_API = False
    PERFORMANCE_LOG_ENABLED = True


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    MOCK_TELEGRAM_API = True
    SEED_TEST_DATA = True


# === АВТОМАТИЧЕСКИЙ ВЫБОР КОНФИГУРАЦИИ ===
def get_config_by_environment() -> Config:
    """Автоматический выбор конфигурации по переменной окружения"""
    env = os.environ.get('FLASK_ENV', 'development').lower()

    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()


# Экспорт констант для удобства импорта
__all__ = [
    'Config',
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
    'get_config_by_environment',
    'ChannelCategories',
    'OfferStatuses',
    'ResponseStatuses',
    'PaymentStatuses',
    'UserTypes',

    # Константы для моделей
    'AUTO_ACCEPT_TIMEOUT_HOURS',
    'MAX_COUNTER_OFFERS',
    'MIN_OFFER_BUDGET',
    'MAX_OFFER_BUDGET',
    'DEFAULT_OFFER_DURATION_DAYS',
    'MAX_OFFER_DURATION_DAYS',
    'MIN_SUBSCRIBERS_COUNT',
    'MAX_PRICE_PER_POST',
    'VERIFICATION_CODE_LENGTH',
    'CHANNEL_STATS_UPDATE_INTERVAL_HOURS',
    'MIN_BALANCE_WITHDRAWAL',
    'MAX_DAILY_WITHDRAWAL',
    'DEFAULT_DAILY_WITHDRAWAL_LIMIT',
    'MIN_PAYMENT_AMOUNT',
    'MAX_PAYMENT_AMOUNT',
    'PAYMENT_PROCESSING_FEE_PERCENT',
    'ESCROW_HOLD_DAYS',

    # Алиасы для совместимости
    'TELEGRAM_BOT_TOKEN',
    'MIN_WITHDRAWAL_AMOUNT',
    'REFERRAL_BONUS_AMOUNT',
    'DEFAULT_USER_TYPE',
    'ESCROW_FEE_PERCENT',
    'MAX_WITHDRAWAL_AMOUNT',

    # Константы для приложения
    'DEFAULT_RATE_LIMIT_PER_HOUR',
    'API_RATE_LIMIT_PER_MINUTE',
    'TELEGRAM_API_RATE_LIMIT',
    'ANALYTICS_RETENTION_DAYS',
    'REPORTS_CACHE_TTL_MINUTES',
    'NOTIFICATION_BATCH_SIZE',
    'NOTIFICATION_RETRY_ATTEMPTS',
    'MAX_OFFER_TITLE_LENGTH',
    'MAX_OFFER_DESCRIPTION_LENGTH',
    'MAX_CHANNEL_DESCRIPTION_LENGTH',
    'MAX_RESPONSE_MESSAGE_LENGTH',
    'MAX_UPLOAD_SIZE_MB',
    'ALLOWED_IMAGE_EXTENSIONS',
    'ALLOWED_VIDEO_EXTENSIONS',
    'MATCHING_SCORE_THRESHOLD',
    'AUTO_MATCH_ENABLED',
    'MAX_AUTO_MATCHES_PER_OFFER',
    'DEFAULT_TIMEZONE',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE',
    'CACHE_TTL_SECONDS',
    'STATISTICS_CACHE_TTL',
    'CHANNEL_INFO_CACHE_TTL',
    'SESSION_TIMEOUT_HOURS',
    'PASSWORD_MIN_LENGTH',
    'MAX_LOGIN_ATTEMPTS',
    'ACCOUNT_LOCKOUT_MINUTES',
    'LOG_RETENTION_DAYS',
    'ERROR_LOG_MAX_SIZE_MB',
    'PERFORMANCE_LOG_ENABLED',
    'WEBHOOK_TIMEOUT_SECONDS',
    'EXTERNAL_API_TIMEOUT_SECONDS',
    'RETRY_DELAYS_SECONDS',
    'COMMISSION_RATE_PERCENT',
    'PREMIUM_COMMISSION_RATE_PERCENT',
    'REFERRAL_BONUS_PERCENT',
    'MAX_CHANNELS_PER_USER',
    'MAX_ACTIVE_OFFERS_PER_USER',
    'MAX_RESPONSES_PER_OFFER',
    'TESTING_MODE',
    'MOCK_TELEGRAM_API',
    'SEED_TEST_DATA'
]