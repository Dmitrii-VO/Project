# Auto-generated __init__.py
# app/models/__init__.py
"""
Модуль моделей данных для Telegram Mini App
Объединяет все модели и предоставляет удобный интерфейс для импорта
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Список всех доступных моделей
__all__ = []

# Импорт базовых компонентов
try:
    from .database import db_manager, DatabaseManager

    __all__.extend(['db_manager', 'DatabaseManager'])
    logger.info("✅ Database manager импортирован")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта database: {e}")

# Импорт модели пользователей
try:
    from .user import (
        User, UserAnalytics, UserNotificationService,
        UserRecommendationService, UserUtils, UserSecurityService,
        UserType, UserStatus
    )

    __all__.extend([
        'User', 'UserAnalytics', 'UserNotificationService',
        'UserRecommendationService', 'UserUtils', 'UserSecurityService',
        'UserType', 'UserStatus'
    ])
    logger.info("✅ User models импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта user models: {e}")

# Импорт модели каналов
try:
    from .channels import (
        Channel, ChannelStatistics, ChannelMatcher,
        ChannelNotificationService, ChannelContentAnalyzer,
        TelegramChannelService, ChannelStatus, ChannelCategory
    )

    __all__.extend([
        'Channel', 'ChannelStatistics', 'ChannelMatcher',
        'ChannelNotificationService', 'ChannelContentAnalyzer',
        'TelegramChannelService', 'ChannelStatus', 'ChannelCategory'
    ])
    logger.info("✅ Channel models импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта channel models: {e}")

# Импорт модели офферов
try:
    from .offer import (
        Offer, OfferAnalytics, OfferRecommendationEngine,
        OfferUtils, OfferMaintenanceService, OfferStatus,
        OfferType, ContentType
    )

    __all__.extend([
        'Offer', 'OfferAnalytics', 'OfferRecommendationEngine',
        'OfferUtils', 'OfferMaintenanceService', 'OfferStatus',
        'OfferType', 'ContentType'
    ])
    logger.info("✅ Offer models импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта offer models: {e}")

# Импорт модели откликов
try:
    from .response import (
        Response, ResponseAnalytics, ResponseMaintenanceService,
        ResponseStatus, ResponseType
    )

    __all__.extend([
        'Response', 'ResponseAnalytics', 'ResponseMaintenanceService',
        'ResponseStatus', 'ResponseType'
    ])
    logger.info("✅ Response models импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта response models: {e}")

# Импорт модели платежей
try:
    from .payment import (
        Payment, EscrowTransaction, PaymentType,
        PaymentStatus, PaymentMethod
    )

    __all__.extend([
        'Payment', 'EscrowTransaction', 'PaymentType',
        'PaymentStatus', 'PaymentMethod'
    ])
    logger.info("✅ Payment models импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта payment models: {e}")


class ModelsRegistry:
    """Реестр всех моделей с метаинформацией"""

    _models = {}
    _initialized = False

    @classmethod
    def register_models(cls):
        """Регистрация всех доступных моделей"""
        if cls._initialized:
            return cls._models

        # Регистрация основных моделей
        models_info = {
            'User': {
                'class': User if 'User' in globals() else None,
                'description': 'Модель пользователей системы',
                'table': 'users',
                'relationships': ['channels', 'offers', 'payments'],
                'key_methods': ['get_by_telegram_id', 'create_from_telegram', 'get_statistics']
            },
            'Channel': {
                'class': Channel if 'Channel' in globals() else None,
                'description': 'Модель Telegram каналов',
                'table': 'channels',
                'relationships': ['owner', 'responses'],
                'key_methods': ['get_by_channel_id', 'verify_ownership', 'update_stats']
            },
            'Offer': {
                'class': Offer if 'Offer' in globals() else None,
                'description': 'Модель рекламных предложений',
                'table': 'offers',
                'relationships': ['advertiser', 'responses'],
                'key_methods': ['create_offer', 'publish', 'get_matching_channels']
            },
            'Response': {
                'class': Response if 'Response' in globals() else None,
                'description': 'Модель откликов на офферы',
                'table': 'offer_responses',
                'relationships': ['offer', 'channel', 'channel_owner'],
                'key_methods': ['create_response', 'accept_by_advertiser', 'mark_as_posted']
            },
            'Payment': {
                'class': Payment if 'Payment' in globals() else None,
                'description': 'Модель платежей и транзакций',
                'table': 'payments',
                'relationships': ['user'],
                'key_methods': ['create_deposit', 'create_withdrawal', 'create_escrow_hold']
            }
        }

        # Фильтруем только доступные модели
        cls._models = {
            name: info for name, info in models_info.items()
            if info['class'] is not None
        }

        cls._initialized = True
        return cls._models

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """Получение информации о модели"""
        models = cls.register_models()
        return models.get(model_name)

    @classmethod
    def get_all_models(cls) -> Dict[str, Any]:
        """Получение всех зарегистрированных моделей"""
        return cls.register_models()

    @classmethod
    def get_model_relationships(cls) -> Dict[str, List[str]]:
        """Получение связей между моделями"""
        models = cls.register_models()
        return {
            name: info.get('relationships', [])
            for name, info in models.items()
        }


def initialize_models() -> Dict[str, bool]:
    """Инициализация всех моделей и проверка их доступности"""
    results = {}

    # Проверяем базу данных
    try:
        if db_manager.init_database():
            results['database'] = True
            logger.info("✅ База данных инициализирована")
        else:
            results['database'] = False
            logger.error("❌ Ошибка инициализации базы данных")
    except Exception as e:
        results['database'] = False
        logger.error(f"❌ Критическая ошибка БД: {e}")

    # Регистрируем модели
    try:
        models = ModelsRegistry.register_models()
        results['models_registered'] = len(models)
        logger.info(f"✅ Зарегистрировано моделей: {len(models)}")

        # Проверяем каждую модель
        for model_name, model_info in models.items():
            try:
                model_class = model_info['class']
                if hasattr(model_class, '__table_name__') or hasattr(model_class, 'get_by_id'):
                    results[f'model_{model_name.lower()}'] = True
                else:
                    results[f'model_{model_name.lower()}'] = False
                    logger.warning(f"⚠️ Модель {model_name} может быть неполной")
            except Exception as e:
                results[f'model_{model_name.lower()}'] = False
                logger.error(f"❌ Ошибка проверки модели {model_name}: {e}")

    except Exception as e:
        results['models_registered'] = 0
        logger.error(f"❌ Ошибка регистрации моделей: {e}")

    return results


def get_model_status() -> Dict[str, Any]:
    """Получение статуса всех моделей"""
    try:
        models = ModelsRegistry.get_all_models()

        status = {
            'total_models': len(models),
            'available_models': list(models.keys()),
            'database_status': 'connected' if db_manager else 'disconnected',
            'models_info': {}
        }

        # Детальная информация о каждой модели
        for model_name, model_info in models.items():
            try:
                model_class = model_info['class']
                status['models_info'][model_name] = {
                    'available': True,
                    'description': model_info.get('description', ''),
                    'table': model_info.get('table', ''),
                    'methods_count': len([
                        method for method in dir(model_class)
                        if not method.startswith('_')
                    ]),
                    'key_methods': model_info.get('key_methods', [])
                }
            except Exception as e:
                status['models_info'][model_name] = {
                    'available': False,
                    'error': str(e)
                }

        return status

    except Exception as e:
        return {
            'total_models': 0,
            'available_models': [],
            'database_status': 'error',
            'error': str(e)
        }


def create_sample_data() -> Dict[str, Any]:
    """Создание демонстрационных данных для тестирования"""
    results = {'created': [], 'errors': []}

    try:
        # Создаем тестового пользователя
        if 'User' in globals():
            test_user_data = {
                'telegram_id': '123456789',
                'username': 'test_user',
                'first_name': 'Test',
                'last_name': 'User',
                'user_type': 'both'
            }

            # Проверяем, не существует ли уже
            existing_user = User.get_by_telegram_id('123456789')
            if not existing_user:
                user = User.create_from_telegram(test_user_data)
                results['created'].append(f'Test user created with ID: {user.id}')
            else:
                results['created'].append('Test user already exists')

        # Добавляем другие демо-данные по необходимости

    except Exception as e:
        results['errors'].append(f'Error creating sample data: {str(e)}')

    return results


def validate_model_integrity() -> Dict[str, Any]:
    """Проверка целостности моделей и их связей"""
    results = {
        'valid': True,
        'issues': [],
        'warnings': [],
        'model_checks': {}
    }

    try:
        models = ModelsRegistry.get_all_models()

        for model_name, model_info in models.items():
            model_class = model_info['class']
            checks = {
                'has_save_method': hasattr(model_class, 'save'),
                'has_get_by_id': hasattr(model_class, 'get_by_id'),
                'has_to_dict': hasattr(model_class, 'to_dict'),
                'proper_init': hasattr(model_class, '__init__')
            }

            results['model_checks'][model_name] = checks

            # Проверяем критические методы
            if not checks['has_save_method']:
                results['issues'].append(f'{model_name}: отсутствует метод save()')
                results['valid'] = False

            if not checks['has_get_by_id']:
                results['warnings'].append(f'{model_name}: отсутствует метод get_by_id()')

    except Exception as e:
        results['valid'] = False
        results['issues'].append(f'Критическая ошибка валидации: {str(e)}')

    return results


# Функции для удобного доступа к моделям
def get_user_model():
    """Получение модели пользователя"""
    return User if 'User' in globals() else None


def get_channel_model():
    """Получение модели канала"""
    return Channel if 'Channel' in globals() else None


def get_offer_model():
    """Получение модели оффера"""
    return Offer if 'Offer' in globals() else None


def get_response_model():
    """Получение модели отклика"""
    return Response if 'Response' in globals() else None


def get_payment_model():
    """Получение модели платежа"""
    return Payment if 'Payment' in globals() else None


# Автоматическая инициализация при импорте модуля
try:
    _initialization_results = initialize_models()

    # Логируем результаты инициализации
    if _initialization_results.get('database'):
        logger.info("🎉 Модели успешно инициализированы")
    else:
        logger.warning("⚠️ Инициализация моделей завершена с предупреждениями")

    # Регистрируем модели в реестре
    ModelsRegistry.register_models()

except Exception as e:
    logger.error(f"❌ Критическая ошибка инициализации моделей: {e}")

# Добавляем утилитарные функции в __all__
__all__.extend([
    'ModelsRegistry', 'initialize_models', 'get_model_status',
    'create_sample_data', 'validate_model_integrity',
    'get_user_model', 'get_channel_model', 'get_offer_model',
    'get_response_model', 'get_payment_model'
])

# Метаинформация о модуле
__version__ = '1.0.0'
__author__ = 'Telegram Mini App Team'
__description__ = 'Модели данных для системы сопоставления каналов и офферов'

# Документация для разработчиков
__doc__ = """
Модуль models содержит все модели данных для Telegram Mini App:

Основные модели:
- User: Пользователи системы (рекламодатели и владельцы каналов)
- Channel: Telegram каналы с верификацией и статистикой
- Offer: Рекламные предложения с системой сопоставления
- Response: Отклики на офферы с переговорами и эскроу
- Payment: Платежи, транзакции и эскроу-операции

Использование:
    from app.models import User, Channel, Offer

    # Создание пользователя
    user = User.create_from_telegram(telegram_data)

    # Поиск каналов
    channels = Channel.search_channels(filters)

    # Создание оффера
    offer = Offer.create_offer(user_id, offer_data)

Утилиты:
- ModelsRegistry: Реестр всех моделей
- initialize_models(): Инициализация системы
- get_model_status(): Проверка статуса моделей
"""