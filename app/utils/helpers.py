# app/utils/helpers.py
"""
Вспомогательные функции для Telegram Mini App
Содержит утилиты для форматирования, обработки данных и общих операций
"""

import re
import json
import hashlib
import secrets
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from decimal import Decimal

logger = logging.getLogger(__name__)


# === ФОРМАТИРОВАНИЕ ===

def format_currency(amount: Union[int, float, Decimal, str], currency: str = "RUB") -> str:
    """
    Форматирование валютных сумм

    Args:
        amount: Сумма для форматирования
        currency: Код валюты

    Returns:
        str: Отформатированная строка с валютой
    """
    try:
        # Конвертируем в float
        if isinstance(amount, Decimal):
            amount_num = float(amount)
        else:
            amount_num = float(amount)

        # Форматируем в зависимости от валюты
        if currency == "RUB":
            if amount_num >= 1000:
                return f"{amount_num:,.0f} ₽"
            else:
                return f"{amount_num:.2f} ₽"
        elif currency == "USD":
            return f"${amount_num:,.2f}"
        elif currency == "EUR":
            return f"€{amount_num:,.2f}"
        elif currency == "BTC":
            return f"₿{amount_num:.8f}"
        elif currency == "ETH":
            return f"Ξ{amount_num:.6f}"
        else:
            return f"{amount_num:,.2f} {currency}"

    except (ValueError, TypeError, AttributeError):
        return f"0.00 {currency}"


def format_datetime(dt: Union[str, datetime], format_type: str = "full") -> str:
    """
    Форматирование даты и времени

    Args:
        dt: Дата/время для форматирования
        format_type: Тип форматирования (full, date, time, relative)

    Returns:
        str: Отформатированная строка
    """
    try:
        # Парсим дату если это строка
        if isinstance(dt, str):
            # Поддерживаем разные форматы
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                try:
                    dt = datetime.strptime(dt.replace('Z', ''), fmt)
                    break
                except ValueError:
                    continue
            else:
                # Если не удалось распарсить, используем ISO формат
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

        if not isinstance(dt, datetime):
            return "Неизвестная дата"

        # Форматируем в зависимости от типа
        if format_type == "full":
            return dt.strftime("%d.%m.%Y %H:%M")
        elif format_type == "date":
            return dt.strftime("%d.%m.%Y")
        elif format_type == "time":
            return dt.strftime("%H:%M")
        elif format_type == "relative":
            return format_time_ago(dt)
        elif format_type == "iso":
            return dt.isoformat()
        else:
            return dt.strftime("%d.%m.%Y %H:%M")

    except (ValueError, AttributeError):
        return "Неизвестная дата"


def format_time_ago(dt: Union[str, datetime]) -> str:
    """
    Форматирование времени в относительном формате ('N минут назад')

    Args:
        dt: Дата/время

    Returns:
        str: Относительное время
    """
    try:
        # Парсим дату если нужно
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

        now = datetime.now()
        if dt.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)

        diff = now - dt

        # Определяем период
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} {'год' if years == 1 else 'лет'} назад"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} {'месяц' if months == 1 else 'месяцев'} назад"
        elif diff.days > 0:
            return f"{diff.days} {'день' if diff.days == 1 else 'дней'} назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} {'час' if hours == 1 else 'часов'} назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} {'минуту' if minutes == 1 else 'минут'} назад"
        else:
            return "только что"

    except (ValueError, AttributeError):
        return "неизвестно"


def format_number(number: Union[int, float], format_type: str = "default") -> str:
    """
    Форматирование чисел

    Args:
        number: Число для форматирования
        format_type: Тип форматирования (default, compact, percentage)

    Returns:
        str: Отформатированное число
    """
    try:
        num = float(number)

        if format_type == "compact":
            # Компактный формат (1.2K, 3.4M)
            if abs(num) >= 1_000_000_000:
                return f"{num / 1_000_000_000:.1f}B"
            elif abs(num) >= 1_000_000:
                return f"{num / 1_000_000:.1f}M"
            elif abs(num) >= 1_000:
                return f"{num / 1_000:.1f}K"
            else:
                return f"{num:.0f}"
        elif format_type == "percentage":
            return f"{num:.1f}%"
        else:
            # Обычный формат с разделителями
            if num == int(num):
                return f"{int(num):,}".replace(',', ' ')
            else:
                return f"{num:,.2f}".replace(',', ' ')

    except (ValueError, TypeError):
        return "0"


# === БЕЗОПАСНОСТЬ ===

def generate_token(length: int = 32) -> str:
    """
    Генерация безопасного токена

    Args:
        length: Длина токена

    Returns:
        str: Случайный токен
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """
    Хэширование пароля

    Args:
        password: Пароль для хэширования
        salt: Соль (если не указана, генерируется автоматически)

    Returns:
        tuple: (hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # Используем PBKDF2 для хэширования
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return password_hash.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Проверка пароля

    Args:
        password: Введенный пароль
        password_hash: Хэш пароля
        salt: Соль

    Returns:
        bool: True если пароль верный
    """
    try:
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return computed_hash.hex() == password_hash
    except Exception:
        return False


# === ОБРАБОТКА ТЕКСТА ===

def sanitize_html(text: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Санитизация HTML контента

    Args:
        text: Текст для санитизации
        allowed_tags: Разрешенные HTML теги

    Returns:
        str: Очищенный текст
    """
    if not isinstance(text, str):
        return ""

    if allowed_tags is None:
        # Удаляем все HTML теги
        text = re.sub(r'<[^>]+>', '', text)
    else:
        # Удаляем только запрещенные теги
        dangerous_tags = [
            'script', 'iframe', 'object', 'embed', 'form',
            'input', 'button', 'style', 'link', 'meta'
        ]

        for tag in dangerous_tags:
            if tag not in allowed_tags:
                text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(f'<{tag}[^>]*/?>', '', text, flags=re.IGNORECASE)

    # Удаляем опасные атрибуты
    text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)

    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста с добавлением суффикса

    Args:
        text: Текст для обрезки
        max_length: Максимальная длина
        suffix: Суффикс для добавления

    Returns:
        str: Обрезанный текст
    """
    if not isinstance(text, str):
        return ""

    if len(text) <= max_length:
        return text

    # Обрезаем по словам если возможно
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.7:  # Если последний пробел не слишком далеко
        truncated = truncated[:last_space]

    return truncated + suffix


def slug_from_text(text: str, max_length: int = 50) -> str:
    """
    Создание URL-friendly slug из текста

    Args:
        text: Исходный текст
        max_length: Максимальная длина slug

    Returns:
        str: URL slug
    """
    if not isinstance(text, str):
        return ""

    # Транслитерация русских букв
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }

    # Приводим к нижнему регистру
    text = text.lower()

    # Транслитерируем
    result = ""
    for char in text:
        if char in translit_map:
            result += translit_map[char]
        elif char.isalnum():
            result += char
        elif char in ' -_':
            result += '-'

    # Очищаем и нормализуем
    result = re.sub(r'-+', '-', result)  # Убираем множественные дефисы
    result = result.strip('-')  # Убираем дефисы в начале и конце

    return result[:max_length]


# === ВЫЧИСЛЕНИЯ ===

def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """
    Вычисление процента

    Args:
        part: Часть
        total: Общее количество

    Returns:
        float: Процент
    """
    try:
        if total == 0:
            return 0.0
        return round((float(part) / float(total)) * 100, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def calculate_growth_rate(current: Union[int, float], previous: Union[int, float]) -> float:
    """
    Вычисление темпа роста

    Args:
        current: Текущее значение
        previous: Предыдущее значение

    Returns:
        float: Темп роста в процентах
    """
    try:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((float(current) - float(previous)) / float(previous)) * 100, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def calculate_average(numbers: List[Union[int, float]]) -> float:
    """
    Вычисление среднего значения

    Args:
        numbers: Список чисел

    Returns:
        float: Среднее значение
    """
    try:
        valid_numbers = [float(n) for n in numbers if isinstance(n, (int, float))]
        if not valid_numbers:
            return 0.0
        return round(sum(valid_numbers) / len(valid_numbers), 2)
    except (ValueError, TypeError):
        return 0.0


# === TELEGRAM ДАННЫЕ ===

def parse_telegram_data(init_data: str) -> Dict[str, Any]:
    """
    Парсинг initData от Telegram WebApp

    Args:
        init_data: Строка initData

    Returns:
        Dict: Распарсенные данные
    """
    try:
        # Разбираем query string
        params = {}
        for param in init_data.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[unquote(key)] = unquote(value)

        # Парсим user данные если есть
        if 'user' in params:
            try:
                params['user'] = json.loads(params['user'])
            except json.JSONDecodeError:
                pass

        return params
    except Exception:
        return {}


def format_telegram_username(username: str) -> str:
    """
    Форматирование Telegram username

    Args:
        username: Username пользователя

    Returns:
        str: Отформатированный username
    """
    if not isinstance(username, str):
        return ""

    username = username.strip()

    # Добавляем @ если нет
    if username and not username.startswith('@'):
        username = '@' + username

    return username


def extract_channel_id(channel_link: str) -> Optional[str]:
    """
    Извлечение ID канала из ссылки

    Args:
        channel_link: Ссылка на канал

    Returns:
        Optional[str]: ID канала или None
    """
    if not isinstance(channel_link, str):
        return None

    channel_link = channel_link.strip()

    # Паттерны для разных форматов ссылок
    patterns = [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',
        r'@([a-zA-Z0-9_]+)',
        r'(-100\d+)',
        r'(-\d+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, channel_link)
        if match:
            channel_id = match.group(1)
            # Добавляем @ для username
            if not channel_id.startswith(('-', '@')):
                channel_id = '@' + channel_id
            return channel_id

    return None


# === ЭКСПОРТ ===

__all__ = [
    # Форматирование
    'format_currency',
    'format_datetime',
    'format_number',
    'format_time_ago',

    # Безопасность
    'generate_token',
    'hash_password',
    'verify_password',

    # Обработка текста
    'sanitize_html',
    'truncate_text',
    'slug_from_text',

    # Вычисления
    'calculate_percentage',
    'calculate_growth_rate',
    'calculate_average',

    # Telegram данные
    'parse_telegram_data',
    'format_telegram_username',
    'extract_channel_id'
]