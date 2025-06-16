# app/utils/validators.py
"""
Валидаторы для Telegram Mini App
Содержит функции валидации данных, Telegram ID, каналов и других сущностей
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# === TELEGRAM ВАЛИДАТОРЫ ===

def validate_telegram_id(telegram_id: Union[str, int]) -> bool:
    """
    Валидация Telegram User ID

    Args:
        telegram_id: Telegram ID пользователя

    Returns:
        bool: True если ID валиден
    """
    try:
        # Конвертируем в int
        tid = int(telegram_id)

        # Telegram User ID должен быть положительным числом
        # и обычно находится в диапазоне от 1 до 2^32
        return 1 <= tid <= 4294967295
    except (ValueError, TypeError):
        return False


def validate_channel_id(channel_id: str) -> bool:
    """
    Валидация Telegram Channel ID

    Args:
        channel_id: ID или username канала

    Returns:
        bool: True если ID валиден
    """
    if not isinstance(channel_id, str) or not channel_id.strip():
        return False

    channel_id = channel_id.strip()

    # Проверяем формат @username
    if channel_id.startswith('@'):
        username = channel_id[1:]
        # Username должен содержать только буквы, цифры и подчеркивания
        # Длина от 5 до 32 символов
        if re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
            return True

    # Проверяем формат -100XXXXXXXXX (супергруппы и каналы)
    elif channel_id.startswith('-100'):
        try:
            # Убираем -100 и проверяем, что остальное - число
            numeric_part = channel_id[4:]
            int(numeric_part)
            return len(numeric_part) >= 6  # Минимальная длина ID
        except ValueError:
            return False

    # Проверяем формат -XXXXXXX (обычные группы)
    elif channel_id.startswith('-') and not channel_id.startswith('-100'):
        try:
            numeric_part = channel_id[1:]
            int(numeric_part)
            return len(numeric_part) >= 6
        except ValueError:
            return False

    return False


def validate_telegram_username(username: str) -> bool:
    """
    Валидация Telegram username

    Args:
        username: Имя пользователя (без @)

    Returns:
        bool: True если username валиден
    """
    if not isinstance(username, str):
        return False

    # Убираем @ если есть
    username = username.lstrip('@').strip()

    # Username должен быть от 5 до 32 символов
    # Содержать только буквы, цифры и подчеркивания
    # Не может начинаться или заканчиваться подчеркиванием
    # Не может содержать два подчеркивания подряд
    if not (5 <= len(username) <= 32):
        return False

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False

    if username.startswith('_') or username.endswith('_'):
        return False

    if '__' in username:
        return False

    return True


# === ФИНАНСОВЫЕ ВАЛИДАТОРЫ ===

def validate_price(price: Union[str, int, float]) -> bool:
    """
    Валидация цены

    Args:
        price: Цена для валидации

    Returns:
        bool: True если цена валидна
    """
    try:
        price_float = float(price)

        # Цена должна быть положительной
        if price_float <= 0:
            return False

        # Максимальная цена 10 миллионов
        if price_float > 10_000_000:
            return False

        # Проверяем количество знаков после запятой (не более 2)
        if isinstance(price, str):
            if '.' in price:
                decimal_part = price.split('.')[1]
                if len(decimal_part) > 2:
                    return False

        return True
    except (ValueError, TypeError):
        return False


def validate_budget(budget: Union[str, int, float], min_budget: float = 100.0) -> bool:
    """
    Валидация бюджета оффера

    Args:
        budget: Бюджет для валидации
        min_budget: Минимальный бюджет

    Returns:
        bool: True если бюджет валиден
    """
    try:
        budget_float = float(budget)

        # Бюджет должен быть больше минимального
        if budget_float < min_budget:
            return False

        # Максимальный бюджет 100 миллионов
        if budget_float > 100_000_000:
            return False

        return True
    except (ValueError, TypeError):
        return False


# === КОНТЕНТ ВАЛИДАТОРЫ ===

def validate_offer_title(title: str) -> bool:
    """
    Валидация названия оффера

    Args:
        title: Название оффера

    Returns:
        bool: True если название валидно
    """
    if not isinstance(title, str):
        return False

    title = title.strip()

    # Длина от 5 до 200 символов
    if not (5 <= len(title) <= 200):
        return False

    # Не должно содержать только пробелы
    if not title:
        return False

    # Проверяем на запрещенные слова/символы
    forbidden_patterns = [
        r'<script',
        r'javascript:',
        r'<iframe',
        r'onclick=',
        r'onerror='
    ]

    title_lower = title.lower()
    for pattern in forbidden_patterns:
        if re.search(pattern, title_lower):
            return False

    return True


def validate_offer_description(description: str) -> bool:
    """
    Валидация описания оффера

    Args:
        description: Описание оффера

    Returns:
        bool: True если описание валидно
    """
    if not isinstance(description, str):
        return False

    description = description.strip()

    # Длина от 20 до 5000 символов
    if not (20 <= len(description) <= 5000):
        return False

    # Не должно содержать только пробелы
    if not description:
        return False

    return True


def validate_channel_name(name: str) -> bool:
    """
    Валидация названия канала

    Args:
        name: Название канала

    Returns:
        bool: True если название валидно
    """
    if not isinstance(name, str):
        return False

    name = name.strip()

    # Длина от 1 до 255 символов
    if not (1 <= len(name) <= 255):
        return False

    return True


# === КОНТАКТНЫЕ ДАННЫЕ ===

def validate_email(email: str) -> bool:
    """
    Валидация email адреса

    Args:
        email: Email для валидации

    Returns:
        bool: True если email валиден
    """
    if not isinstance(email, str):
        return False

    email = email.strip().lower()

    # Простая проверка email регулярным выражением
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        return False

    # Длина не должна превышать 254 символа
    if len(email) > 254:
        return False

    return True


def validate_phone(phone: str) -> bool:
    """
    Валидация номера телефона

    Args:
        phone: Номер телефона

    Returns:
        bool: True если номер валиден
    """
    if not isinstance(phone, str):
        return False

    # Убираем все символы кроме цифр и +
    cleaned_phone = re.sub(r'[^\d+]', '', phone)

    # Проверяем формат международного номера
    if cleaned_phone.startswith('+'):
        # Международный формат: +1234567890 (от 7 до 15 цифр после +)
        digits = cleaned_phone[1:]
        return digits.isdigit() and 7 <= len(digits) <= 15
    else:
        # Локальный формат: только цифры (от 7 до 15 цифр)
        return cleaned_phone.isdigit() and 7 <= len(cleaned_phone) <= 15


def validate_url(url: str) -> bool:
    """
    Валидация URL

    Args:
        url: URL для валидации

    Returns:
        bool: True если URL валиден
    """
    if not isinstance(url, str):
        return False

    url = url.strip()

    try:
        result = urlparse(url)

        # URL должен иметь схему (http/https) и netloc (домен)
        if not result.scheme or not result.netloc:
            return False

        # Поддерживаем только http и https
        if result.scheme not in ['http', 'https']:
            return False

        # Домен должен содержать точку
        if '.' not in result.netloc:
            return False

        return True
    except Exception:
        return False


# === СПЕЦИАЛИЗИРОВАННЫЕ ВАЛИДАТОРЫ ===

def validate_category(category: str) -> bool:
    """
    Валидация категории оффера/канала

    Args:
        category: Категория

    Returns:
        bool: True если категория валидна
    """
    valid_categories = [
        'technology', 'business', 'entertainment', 'news',
        'education', 'lifestyle', 'sports', 'gaming',
        'finance', 'health', 'travel', 'food', 'art',
        'music', 'crypto', 'marketing', 'other'
    ]

    return isinstance(category, str) and category.lower() in valid_categories


def validate_language_code(lang_code: str) -> bool:
    """
    Валидация кода языка

    Args:
        lang_code: Код языка (ISO 639-1)

    Returns:
        bool: True если код валиден
    """
    valid_languages = [
        'ru', 'en', 'uk', 'es', 'fr', 'de', 'it',
        'pt', 'pl', 'tr', 'zh', 'ja', 'ko', 'ar'
    ]

    return isinstance(lang_code, str) and lang_code.lower() in valid_languages


def validate_json_data(json_string: str) -> bool:
    """
    Валидация JSON строки

    Args:
        json_string: JSON строка

    Returns:
        bool: True если JSON валиден
    """
    if not isinstance(json_string, str):
        return False

    try:
        json.loads(json_string)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


# === КОМБИНИРОВАННЫЕ ВАЛИДАТОРЫ ===

class TelegramDataValidator:
    """Класс для комплексной валидации Telegram данных"""

    @staticmethod
    def validate_channel_data(data: Dict[str, Any]) -> List[str]:
        """
        Валидация данных канала

        Args:
            data: Словарь с данными канала

        Returns:
            List[str]: Список ошибок валидации
        """
        errors = []

        # Проверяем обязательные поля
        required_fields = ['channel_id', 'channel_name']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Field '{field}' is required")

        # Валидируем channel_id
        if 'channel_id' in data:
            if not validate_channel_id(data['channel_id']):
                errors.append("Invalid channel_id format")

        # Валидируем название канала
        if 'channel_name' in data:
            if not validate_channel_name(data['channel_name']):
                errors.append("Invalid channel name")

        # Валидируем цену
        if 'price_per_post' in data and data['price_per_post'] is not None:
            if not validate_price(data['price_per_post']):
                errors.append("Invalid price_per_post")

        # Валидируем категорию
        if 'category' in data and data['category']:
            if not validate_category(data['category']):
                errors.append("Invalid category")

        return errors

    @staticmethod
    def validate_offer_data(data: Dict[str, Any]) -> List[str]:
        """
        Валидация данных оффера

        Args:
            data: Словарь с данными оффера

        Returns:
            List[str]: Список ошибок валидации
        """
        errors = []

        # Проверяем обязательные поля
        required_fields = ['title', 'description', 'budget']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Field '{field}' is required")

        # Валидируем название
        if 'title' in data:
            if not validate_offer_title(data['title']):
                errors.append("Invalid offer title")

        # Валидируем описание
        if 'description' in data:
            if not validate_offer_description(data['description']):
                errors.append("Invalid offer description")

        # Валидируем бюджет
        if 'budget' in data:
            if not validate_budget(data['budget']):
                errors.append("Invalid budget")

        # Валидируем категорию
        if 'category' in data and data['category']:
            if not validate_category(data['category']):
                errors.append("Invalid category")

        return errors

    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> List[str]:
        """
        Валидация данных пользователя

        Args:
            data: Словарь с данными пользователя

        Returns:
            List[str]: Список ошибок валидации
        """
        errors = []

        # Валидируем Telegram ID
        if 'telegram_id' in data:
            if not validate_telegram_id(data['telegram_id']):
                errors.append("Invalid telegram_id")

        # Валидируем username
        if 'username' in data and data['username']:
            if not validate_telegram_username(data['username']):
                errors.append("Invalid username")

        # Валидируем email
        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                errors.append("Invalid email")

        # Валидируем телефон
        if 'phone' in data and data['phone']:
            if not validate_phone(data['phone']):
                errors.append("Invalid phone number")

        return errors


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Санитизация строки

    Args:
        text: Текст для санитизации
        max_length: Максимальная длина

    Returns:
        str: Очищенный текст
    """
    if not isinstance(text, str):
        return ""

    # Удаляем потенциально опасные теги и скрипты
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'on\w+\s*=',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>'
    ]

    cleaned_text = text
    for pattern in dangerous_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL)

    # Обрезаем до максимальной длины
    if max_length and len(cleaned_text) > max_length:
        cleaned_text = cleaned_text[:max_length].rstrip()

    return cleaned_text.strip()


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Валидация расширения файла

    Args:
        filename: Имя файла
        allowed_extensions: Список разрешенных расширений

    Returns:
        bool: True если расширение разрешено
    """
    if not isinstance(filename, str) or not filename:
        return False

    # Получаем расширение файла
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''

    return file_extension in [ext.lower() for ext in allowed_extensions]


def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
    """
    Валидация размера файла

    Args:
        file_size: Размер файла в байтах
        max_size_mb: Максимальный размер в МБ

    Returns:
        bool: True если размер допустим
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return isinstance(file_size, int) and 0 < file_size <= max_size_bytes


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Валидация диапазона дат

    Args:
        start_date: Начальная дата (ISO формат)
        end_date: Конечная дата (ISO формат)

    Returns:
        bool: True если диапазон валиден
    """
    try:
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Конечная дата должна быть после начальной
        return end_dt > start_dt
    except (ValueError, AttributeError):
        return False


# === КОНСТАНТЫ ===

# Разрешенные расширения файлов
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'webm']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'txt', 'rtf']

# Максимальные размеры
MAX_IMAGE_SIZE_MB = 5
MAX_VIDEO_SIZE_MB = 50
MAX_DOCUMENT_SIZE_MB = 10

# Лимиты для текстовых полей
MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 200
MIN_DESCRIPTION_LENGTH = 20
MAX_DESCRIPTION_LENGTH = 5000


class ChannelDataValidator:
    """Алиас для TelegramDataValidator для обратной совместимости"""

    @staticmethod
    def validate_channel_data(data: Dict[str, Any]) -> List[str]:
        return TelegramDataValidator.validate_channel_data(data)


class OfferDataValidator:
    """Валидатор данных офферов"""

    @staticmethod
    def validate_offer_data(data: Dict[str, Any]) -> List[str]:
        return TelegramDataValidator.validate_offer_data(data)


class UserDataValidator:
    """Валидатор данных пользователей"""

    @staticmethod
    def validate_user_data(data: Dict[str, Any]) -> List[str]:
        return TelegramDataValidator.validate_user_data(data)


class PaymentDataValidator:
    """Валидатор платежных данных"""

    @staticmethod
    def validate_payment_data(data: Dict[str, Any]) -> List[str]:
        errors = []

        # Валидация суммы
        if 'amount' in data:
            if not validate_price(data['amount']):
                errors.append("Invalid payment amount")

        # Валидация валюты
        if 'currency' in data:
            valid_currencies = ['RUB', 'USD', 'EUR']
            if data['currency'] not in valid_currencies:
                errors.append("Invalid currency")

        return errors


class ResponseDataValidator:
    """Валидатор данных откликов"""

    @staticmethod
    def validate_response_data(data: Dict[str, Any]) -> List[str]:
        errors = []

        # Валидация сообщения
        if 'message' in data and data['message']:
            message = data['message'].strip()
            if not (10 <= len(message) <= 1000):
                errors.append("Response message must be between 10 and 1000 characters")

        return errors


# === ЭКСПОРТ ===

__all__ = [
    # Основные валидаторы
    'validate_telegram_id',
    'validate_channel_id',
    'validate_telegram_username',
    'validate_price',
    'validate_budget',
    'validate_offer_title',
    'validate_offer_description',
    'validate_channel_name',
    'validate_email',
    'validate_phone',
    'validate_url',
    'validate_category',
    'validate_language_code',
    'validate_json_data',

    # Классы валидаторов
    'TelegramDataValidator',
    'ChannelDataValidator',
    'OfferDataValidator',
    'UserDataValidator',
    'PaymentDataValidator',
    'ResponseDataValidator',

    # Вспомогательные функции
    'sanitize_string',
    'validate_file_extension',
    'validate_file_size',
    'validate_date_range',

    # Константы
    'ALLOWED_IMAGE_EXTENSIONS',
    'ALLOWED_VIDEO_EXTENSIONS',
    'ALLOWED_DOCUMENT_EXTENSIONS',
    'MAX_IMAGE_SIZE_MB',
    'MAX_VIDEO_SIZE_MB',
    'MAX_DOCUMENT_SIZE_MB',
    'MIN_TITLE_LENGTH',
    'MAX_TITLE_LENGTH',
    'MIN_DESCRIPTION_LENGTH',
    'MAX_DESCRIPTION_LENGTH'
]