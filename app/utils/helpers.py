#!/usr/bin/env python3
"""
Вспомогательные функции для Telegram Mini App
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """Безопасная загрузка JSON"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(data: Any) -> str:
    """Безопасное сохранение в JSON"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return "{}"


def truncate_string(s: str, max_length: int = 100) -> str:
    """Обрезка строки до указанной длины"""
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла"""
    import re
    return re.sub(r'[^\w\-_\.]', '_', filename)


def get_file_size_mb(file_path: str) -> float:
    """Получение размера файла в MB"""
    import os
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0.0


def is_valid_url(url: str) -> bool:
    """Проверка валидности URL"""
    import re
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return pattern.match(url) is not None


def generate_unique_id() -> str:
    """Генерация уникального ID"""
    import uuid
    return str(uuid.uuid4())


def hash_string(s: str) -> str:
    """Хеширование строки"""
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()


def format_number(num: int) -> str:
    """Форматирование числа с разделителями"""
    return f"{num:,}".replace(',', ' ')


def calculate_percentage(part: int, total: int) -> float:
    """Вычисление процента"""
    if total == 0:
        return 0.0
    return (part / total) * 100


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Слияние словарей"""
    result = dict1.copy()
    result.update(dict2)
    return result


def get_nested_value(data: Dict, keys: str, default: Any = None) -> Any:
    """Получение вложенного значения из словаря"""
    try:
        for key in keys.split('.'):
            data = data[key]
        return data
    except (KeyError, TypeError):
        return default


def clean_text(text: str) -> str:
    """Очистка текста"""
    import re
    # Удаляем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text.strip())
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    return text


def is_valid_email(email: str) -> bool:
    """Проверка валидности email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_current_timestamp() -> int:
    """Получение текущего timestamp"""
    return int(datetime.now().timestamp())


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def validate_json_structure(data: Dict, required_keys: list) -> bool:
    """Валидация структуры JSON"""
    for key in required_keys:
        if key not in data:
            return False
    return True


def escape_html(text: str) -> str:
    """Экранирование HTML"""
    import html
    return html.escape(text)


def create_error_response(error_message: str, error_code: str = "GENERIC_ERROR") -> Dict:
    """Создание стандартного ответа об ошибке"""
    return {
        "success": False,
        "error": error_message,
        "error_code": error_code,
        "timestamp": get_current_timestamp()
    }


def create_success_response(data: Any = None, message: str = "Success") -> Dict:
    """Создание стандартного успешного ответа"""
    response = {
        "success": True,
        "message": message,
        "timestamp": get_current_timestamp()
    }
    
    if data is not None:
        response["data"] = data
    
    return response


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Декоратор для повторного выполнения функции при исключении"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


def log_function_call(func):
    """Декоратор для логирования вызовов функций"""
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"Function {func.__name__} returned: {result}")
        return result
    return wrapper


def measure_execution_time(func):
    """Декоратор для измерения времени выполнения"""
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper


def format_currency(amount: float, currency: str = "RUB") -> str:
    """
    Форматирование суммы в валюте
    
    Args:
        amount: Сумма для форматирования
        currency: Код валюты (RUB, USD, EUR)
    
    Returns:
        str: Отформатированная строка с суммой
    
    Examples:
        >>> format_currency(1000.50, "RUB")
        "1 000.50 ₽"
        >>> format_currency(99.99, "USD")
        "$99.99"
        >>> format_currency(1234.56, "EUR")
        "€1,234.56"
    """
    try:
        amount = float(amount)
        
        if currency == "RUB":
            # Русский рубль - с пробелами в качестве разделителей тысяч
            if amount == int(amount):
                return f"{int(amount):,} ₽".replace(',', ' ')
            else:
                return f"{amount:,.2f} ₽".replace(',', ' ')
        
        elif currency == "USD":
            # Американский доллар
            return f"${amount:,.2f}"
        
        elif currency == "EUR":
            # Евро
            return f"€{amount:,.2f}"
        
        else:
            # Неизвестная валюта
            return f"{amount:,.2f} {currency}"
    
    except (ValueError, TypeError):
        return f"0 {currency}"


def generate_token(length: int = 32) -> str:
    """
    Генерация случайного токена
    
    Args:
        length: Длина токена
    
    Returns:
        str: Случайный токен
    """
    import secrets
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """
    Хеширование пароля
    
    Args:
        password: Пароль для хеширования
    
    Returns:
        str: Хеш пароля
    """
    import hashlib
    import secrets
    
    # Генерируем соль
    salt = secrets.token_hex(16)
    
    # Хешируем пароль с солью
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    
    # Возвращаем соль + хеш
    return salt + pwd_hash.hex()


def verify_password(password: str, hashed: str) -> bool:
    """
    Проверка пароля
    
    Args:
        password: Пароль для проверки
        hashed: Хешированный пароль
    
    Returns:
        bool: True если пароль верный
    """
    import hashlib
    
    try:
        # Извлекаем соль (первые 32 символа)
        salt = hashed[:32]
        stored_hash = hashed[32:]
        
        # Хешируем пароль с той же солью
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        
        return pwd_hash.hex() == stored_hash
    
    except Exception:
        return False


def sanitize_html(text: str) -> str:
    """
    Очистка HTML тегов
    
    Args:
        text: Текст для очистки
    
    Returns:
        str: Очищенный текст
    """
    import re
    
    if not isinstance(text, str):
        return ""
    
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Очищаем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста до указанной длины
    
    Args:
        text: Текст для обрезки
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
    
    Returns:
        str: Обрезанный текст
    """
    if not isinstance(text, str):
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def slug_from_text(text: str) -> str:
    """
    Создание slug из текста
    
    Args:
        text: Текст для преобразования
    
    Returns:
        str: Slug строка
    """
    import re
    
    if not isinstance(text, str):
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Удаляем специальные символы
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Заменяем пробелы на дефисы
    text = re.sub(r'\s+', '-', text)
    
    # Удаляем лишние дефисы
    text = re.sub(r'-+', '-', text)
    
    return text.strip('-')


def parse_telegram_data(init_data: str) -> dict:
    """
    Парсинг данных от Telegram WebApp
    
    Args:
        init_data: Данные инициализации от Telegram
    
    Returns:
        dict: Распарсенные данные
    """
    import urllib.parse
    
    try:
        # Парсим URL-параметры
        parsed = urllib.parse.parse_qs(init_data)
        
        result = {}
        
        # Извлекаем данные пользователя
        if 'user' in parsed:
            user_data = safe_json_loads(parsed['user'][0])
            if user_data:
                result['user'] = user_data
        
        # Извлекаем другие параметры
        for key in ['auth_date', 'hash', 'query_id', 'start_param']:
            if key in parsed:
                result[key] = parsed[key][0]
        
        return result
    
    except Exception:
        return {}


# Экспорт основных функций
__all__ = [
    'format_datetime',
    'safe_json_loads',
    'safe_json_dumps',
    'truncate_string',
    'sanitize_filename',
    'get_file_size_mb',
    'is_valid_url',
    'generate_unique_id',
    'hash_string',
    'format_number',
    'calculate_percentage',
    'merge_dicts',
    'get_nested_value',
    'clean_text',
    'is_valid_email',
    'get_current_timestamp',
    'format_file_size',
    'validate_json_structure',
    'escape_html',
    'create_error_response',
    'create_success_response',
    'retry_on_exception',
    'log_function_call',
    'measure_execution_time',
    'format_currency',
    'generate_token',
    'hash_password',
    'verify_password',
    'sanitize_html',
    'truncate_text',
    'slug_from_text',
    'parse_telegram_data'
]