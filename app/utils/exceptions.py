# app/utils/exceptions.py
"""
Кастомные исключения для Telegram Mini App рекламной платформы
Содержит иерархию исключений для различных компонентов системы
"""

import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramMiniAppError(Exception):
    """
    Базовое исключение для всех ошибок Telegram Mini App
    """

    def __init__(
            self,
            message: str,
            code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            user_message: Optional[str] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.now()

        super().__init__(self.message)

        # Логирование ошибки
        logger.error(f"[{self.code}] {self.message}", extra={
            'error_code': self.code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для API ответов"""
        return {
            'error': True,
            'code': self.code,
            'message': self.user_message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# === АВТОРИЗАЦИЯ И АУТЕНТИФИКАЦИЯ ===

class AuthenticationError(TelegramMiniAppError):
    """Ошибки аутентификации пользователей"""

    def __init__(self, message: str = "Ошибка аутентификации", **kwargs):
        super().__init__(
            message=message,
            user_message="Не удалось подтвердить личность. Попробуйте войти заново.",
            **kwargs
        )


class InvalidTelegramDataError(AuthenticationError):
    """Некорректные данные от Telegram WebApp"""

    def __init__(self, field: str = None, **kwargs):
        message = f"Некорректные данные Telegram: {field}" if field else "Некорректные данные Telegram"
        super().__init__(
            message=message,
            user_message="Ошибка данных от Telegram. Перезапустите приложение.",
            **kwargs
        )


class TokenExpiredError(AuthenticationError):
    """Истекший токен авторизации"""

    def __init__(self, **kwargs):
        super().__init__(
            message="Токен авторизации истек",
            user_message="Сессия истекла. Необходимо войти заново.",
            **kwargs
        )


class AccessDeniedError(AuthenticationError):
    """Отказ в доступе"""

    def __init__(self, resource: str = None, **kwargs):
        message = f"Доступ запрещен к ресурсу: {resource}" if resource else "Доступ запрещен"
        super().__init__(
            message=message,
            user_message="У вас нет прав для выполнения этого действия.",
            **kwargs
        )


# === ВАЛИДАЦИЯ ДАННЫХ ===

class ValidationError(TelegramMiniAppError):
    """Ошибки валидации входных данных"""

    def __init__(
            self,
            message: str = "Ошибка валидации данных",
            field: Optional[str] = None,
            value: Optional[str] = None,
            validation_errors: Optional[List[str]] = None,
            **kwargs
    ):
        self.field = field
        self.value = value
        self.validation_errors = validation_errors or []

        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value:
            details['value'] = str(value)[:100]  # Ограничиваем длину для безопасности
        if validation_errors:
            details['validation_errors'] = validation_errors

        super().__init__(
            message=message,
            details=details,
            user_message="Пожалуйста, проверьте введенные данные.",
            **kwargs
        )


class RequiredFieldError(ValidationError):
    """Отсутствует обязательное поле"""

    def __init__(self, field: str, **kwargs):
        super().__init__(
            message=f"Отсутствует обязательное поле: {field}",
            field=field,
            user_message=f"Поле '{field}' обязательно для заполнения.",
            **kwargs
        )


class InvalidFormatError(ValidationError):
    """Неверный формат данных"""

    def __init__(self, field: str, expected_format: str, **kwargs):
        super().__init__(
            message=f"Неверный формат поля {field}, ожидается: {expected_format}",
            field=field,
            user_message=f"Неверный формат поля '{field}'. Ожидается: {expected_format}",
            **kwargs
        )


# === ПОЛЬЗОВАТЕЛИ ===

class UserError(TelegramMiniAppError):
    """Ошибки, связанные с пользователями"""
    pass


class UserNotFoundError(UserError):
    """Пользователь не найден"""

    def __init__(self, user_id: Union[int, str] = None, **kwargs):
        message = f"Пользователь не найден: {user_id}" if user_id else "Пользователь не найден"
        super().__init__(
            message=message,
            user_message="Пользователь не найден в системе.",
            details={'user_id': user_id} if user_id else {},
            **kwargs
        )


class UserAlreadyExistsError(UserError):
    """Пользователь уже существует"""

    def __init__(self, user_id: Union[int, str] = None, **kwargs):
        message = f"Пользователь уже существует: {user_id}" if user_id else "Пользователь уже существует"
        super().__init__(
            message=message,
            user_message="Пользователь уже зарегистрирован в системе.",
            details={'user_id': user_id} if user_id else {},
            **kwargs
        )


class InsufficientPermissionsError(UserError):
    """Недостаточно прав доступа"""

    def __init__(self, required_permission: str = None, **kwargs):
        message = f"Недостаточно прав: {required_permission}" if required_permission else "Недостаточно прав"
        super().__init__(
            message=message,
            user_message="У вас недостаточно прав для выполнения этого действия.",
            details={'required_permission': required_permission} if required_permission else {},
            **kwargs
        )


# === КАНАЛЫ ===

class ChannelError(TelegramMiniAppError):
    """Ошибки, связанные с каналами"""
    pass


class ChannelNotFoundError(ChannelError):
    """Канал не найден"""

    def __init__(self, channel_id: Union[int, str] = None, **kwargs):
        message = f"Канал не найден: {channel_id}" if channel_id else "Канал не найден"
        super().__init__(
            message=message,
            user_message="Канал не найден или недоступен.",
            details={'channel_id': channel_id} if channel_id else {},
            **kwargs
        )


class ChannelAccessDeniedError(ChannelError):
    """Нет доступа к каналу"""

    def __init__(self, channel_id: Union[int, str] = None, **kwargs):
        message = f"Нет доступа к каналу: {channel_id}" if channel_id else "Нет доступа к каналу"
        super().__init__(
            message=message,
            user_message="У вас нет прав для управления этим каналом.",
            details={'channel_id': channel_id} if channel_id else {},
            **kwargs
        )


class ChannelVerificationError(ChannelError):
    """Ошибка верификации канала"""

    def __init__(self, reason: str = None, **kwargs):
        message = f"Ошибка верификации канала: {reason}" if reason else "Ошибка верификации канала"
        super().__init__(
            message=message,
            user_message="Не удалось подтвердить права на канал. Проверьте, что бот добавлен как администратор.",
            details={'reason': reason} if reason else {},
            **kwargs
        )


# === ОФФЕРЫ ===

class OfferError(TelegramMiniAppError):
    """Ошибки, связанные с офферами"""
    pass


class OfferNotFoundError(OfferError):
    """Оффер не найден"""

    def __init__(self, offer_id: Union[int, str] = None, **kwargs):
        message = f"Оффер не найден: {offer_id}" if offer_id else "Оффер не найден"
        super().__init__(
            message=message,
            user_message="Рекламное предложение не найдено.",
            details={'offer_id': offer_id} if offer_id else {},
            **kwargs
        )


class OfferExpiredError(OfferError):
    """Оффер истек"""

    def __init__(self, offer_id: Union[int, str] = None, expired_date: str = None, **kwargs):
        message = f"Оффер истек: {offer_id}" if offer_id else "Оффер истек"
        super().__init__(
            message=message,
            user_message="Срок действия предложения истек.",
            details={
                'offer_id': offer_id,
                'expired_date': expired_date
            } if offer_id else {},
            **kwargs
        )


class InsufficientBudgetError(OfferError):
    """Недостаточно бюджета для оффера"""

    def __init__(self, required_amount: float = None, available_amount: float = None, **kwargs):
        super().__init__(
            message=f"Недостаточно бюджета: требуется {required_amount}, доступно {available_amount}",
            user_message="Недостаточно средств для размещения рекламы.",
            details={
                'required_amount': required_amount,
                'available_amount': available_amount
            },
            **kwargs
        )


# === ОТКЛИКИ ===

class ResponseError(TelegramMiniAppError):
    """Ошибки, связанные с откликами"""
    pass


class ResponseNotFoundError(ResponseError):
    """Отклик не найден"""

    def __init__(self, response_id: Union[int, str] = None, **kwargs):
        message = f"Отклик не найден: {response_id}" if response_id else "Отклик не найден"
        super().__init__(
            message=message,
            user_message="Отклик не найден.",
            details={'response_id': response_id} if response_id else {},
            **kwargs
        )


class DuplicateResponseError(ResponseError):
    """Дублирующийся отклик"""

    def __init__(self, offer_id: Union[int, str] = None, **kwargs):
        super().__init__(
            message=f"Отклик уже существует для оффера: {offer_id}",
            user_message="Вы уже откликнулись на это предложение.",
            details={'offer_id': offer_id} if offer_id else {},
            **kwargs
        )


# === ПЛАТЕЖИ ===

class PaymentError(TelegramMiniAppError):
    """Ошибки платежной системы"""
    pass


class InsufficientFundsError(PaymentError):
    """Недостаточно средств"""

    def __init__(self, required_amount: float = None, available_amount: float = None, **kwargs):
        super().__init__(
            message=f"Недостаточно средств: требуется {required_amount}, доступно {available_amount}",
            user_message="Недостаточно средств на счете.",
            details={
                'required_amount': required_amount,
                'available_amount': available_amount
            },
            **kwargs
        )


class PaymentProcessingError(PaymentError):
    """Ошибка обработки платежа"""

    def __init__(self, transaction_id: str = None, provider_error: str = None, **kwargs):
        super().__init__(
            message=f"Ошибка обработки платежа: {provider_error or 'неизвестная ошибка'}",
            user_message="Не удалось обработать платеж. Попробуйте позже.",
            details={
                'transaction_id': transaction_id,
                'provider_error': provider_error
            },
            **kwargs
        )


class PaymentNotFoundError(PaymentError):
    """Платеж не найден"""

    def __init__(self, payment_id: Union[int, str] = None, **kwargs):
        message = f"Платеж не найден: {payment_id}" if payment_id else "Платеж не найден"
        super().__init__(
            message=message,
            user_message="Платеж не найден в системе.",
            details={'payment_id': payment_id} if payment_id else {},
            **kwargs
        )


# === АНАЛИТИКА ===

class AnalyticsError(TelegramMiniAppError):
    """Ошибки аналитической системы"""
    pass


class DataNotAvailableError(AnalyticsError):
    """Данные недоступны"""

    def __init__(self, data_type: str = None, period: str = None, **kwargs):
        message = f"Данные недоступны: {data_type} за {period}" if data_type and period else "Данные недоступны"
        super().__init__(
            message=message,
            user_message="Запрашиваемые данные временно недоступны.",
            details={
                'data_type': data_type,
                'period': period
            },
            **kwargs
        )


class ReportGenerationError(AnalyticsError):
    """Ошибка генерации отчета"""

    def __init__(self, report_type: str = None, **kwargs):
        message = f"Ошибка генерации отчета: {report_type}" if report_type else "Ошибка генерации отчета"
        super().__init__(
            message=message,
            user_message="Не удалось сгенерировать отчет. Попробуйте позже.",
            details={'report_type': report_type} if report_type else {},
            **kwargs
        )


# === TELEGRAM API ===

class TelegramAPIError(TelegramMiniAppError):
    """Ошибки взаимодействия с Telegram API"""

    def __init__(self, api_method: str = None, api_error: str = None, status_code: int = None, **kwargs):
        message = f"Ошибка Telegram API [{api_method}]: {api_error}" if api_method and api_error else "Ошибка Telegram API"
        super().__init__(
            message=message,
            user_message="Ошибка связи с Telegram. Попробуйте позже.",
            details={
                'api_method': api_method,
                'api_error': api_error,
                'status_code': status_code
            },
            **kwargs
        )


class BotTokenError(TelegramAPIError):
    """Ошибка токена бота"""

    def __init__(self, **kwargs):
        super().__init__(
            message="Некорректный токен бота",
            user_message="Ошибка конфигурации. Обратитесь к администратору.",
            **kwargs
        )


class WebhookError(TelegramAPIError):
    """Ошибка webhook'а"""

    def __init__(self, webhook_url: str = None, **kwargs):
        super().__init__(
            message=f"Ошибка webhook: {webhook_url}",
            user_message="Ошибка обработки webhook.",
            details={'webhook_url': webhook_url} if webhook_url else {},
            **kwargs
        )


# === СИСТЕМНЫЕ ОШИБКИ ===

class RateLimitError(TelegramMiniAppError):
    """Превышен лимит запросов"""

    def __init__(self, limit: int = None, reset_time: int = None, **kwargs):
        super().__init__(
            message=f"Превышен лимит запросов: {limit}",
            user_message=f"Слишком много запросов. Попробуйте через {'несколько минут' if not reset_time else f'{reset_time} секунд'}.",
            details={
                'limit': limit,
                'reset_time': reset_time
            },
            **kwargs
        )


class ConfigurationError(TelegramMiniAppError):
    """Ошибки конфигурации"""

    def __init__(self, config_key: str = None, **kwargs):
        message = f"Ошибка конфигурации: {config_key}" if config_key else "Ошибка конфигурации"
        super().__init__(
            message=message,
            user_message="Ошибка настроек приложения. Обратитесь к администратору.",
            details={'config_key': config_key} if config_key else {},
            **kwargs
        )


class DatabaseError(TelegramMiniAppError):
    """Ошибки базы данных"""

    def __init__(self, operation: str = None, table: str = None, **kwargs):
        message = f"Ошибка БД [{operation}] в таблице {table}" if operation and table else "Ошибка базы данных"
        super().__init__(
            message=message,
            user_message="Временная ошибка сервера. Попробуйте позже.",
            details={
                'operation': operation,
                'table': table
            },
            **kwargs
        )


class ExternalServiceError(TelegramMiniAppError):
    """Ошибки внешних сервисов"""

    def __init__(self, service_name: str = None, service_error: str = None, **kwargs):
        message = f"Ошибка сервиса {service_name}: {service_error}" if service_name else "Ошибка внешнего сервиса"
        super().__init__(
            message=message,
            user_message="Ошибка внешнего сервиса. Попробуйте позже.",
            details={
                'service_name': service_name,
                'service_error': service_error
            },
            **kwargs
        )


# === УТИЛИТЫ ДЛЯ РАБОТЫ С ИСКЛЮЧЕНИЯМИ ===

def handle_exception(func):
    """
    Декоратор для обработки исключений в API эндпоинтах
    """
    from functools import wraps
    from flask import jsonify

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TelegramMiniAppError as e:
            logger.error(f"Handled app error in {func.__name__}: {e}")
            return jsonify(e.to_dict()), 400
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {e}")
            return jsonify(e.to_dict()), 400
        except Exception as e:
            logger.error(f"Unhandled error in {func.__name__}: {e}")
            error = TelegramMiniAppError(
                message=f"Внутренняя ошибка в {func.__name__}: {str(e)}",
                user_message="Внутренняя ошибка сервера. Попробуйте позже."
            )
            return jsonify(error.to_dict()), 500

    return wrapper


def get_error_response(error: Exception, status_code: int = 500) -> tuple:
    """
    Создание стандартного ответа об ошибке
    """
    from flask import jsonify

    if isinstance(error, TelegramMiniAppError):
        return jsonify(error.to_dict()), status_code

    # Для неизвестных ошибок создаем базовое исключение
    app_error = TelegramMiniAppError(
        message=str(error),
        user_message="Произошла ошибка. Попробуйте позже."
    )
    return jsonify(app_error.to_dict()), status_code


# === СПИСОК ВСЕХ ИСКЛЮЧЕНИЙ ДЛЯ ЭКСПОРТА ===

__all__ = [
    # Базовые
    'TelegramMiniAppError',

    # Авторизация
    'AuthenticationError',
    'InvalidTelegramDataError',
    'TokenExpiredError',
    'AccessDeniedError',

    # Валидация
    'ValidationError',
    'RequiredFieldError',
    'InvalidFormatError',

    # Пользователи
    'UserError',
    'UserNotFoundError',
    'UserAlreadyExistsError',
    'InsufficientPermissionsError',

    # Каналы
    'ChannelError',
    'ChannelNotFoundError',
    'ChannelAccessDeniedError',
    'ChannelVerificationError',

    # Офферы
    'OfferError',
    'OfferNotFoundError',
    'OfferExpiredError',
    'InsufficientBudgetError',

    # Отклики
    'ResponseError',
    'ResponseNotFoundError',
    'DuplicateResponseError',

    # Платежи
    'PaymentError',
    'InsufficientFundsError',
    'PaymentProcessingError',
    'PaymentNotFoundError',

    # Аналитика
    'AnalyticsError',
    'DataNotAvailableError',
    'ReportGenerationError',

    # Telegram API
    'TelegramAPIError',
    'BotTokenError',
    'WebhookError',

    # Системные
    'RateLimitError',
    'ConfigurationError',
    'DatabaseError',
    'ExternalServiceError',

    # Утилиты
    'handle_exception',
    'get_error_response'
]