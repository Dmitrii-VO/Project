import time
import re
import html
import logging
from collections import defaultdict
from typing import Tuple, Optional, Dict, Any
from flask import request
from datetime import datetime
from app.config.settings import Config

logger = logging.getLogger(__name__)


class SecurityService:
    """Сервис безопасности приложения"""

    def __init__(self):
        # Rate limiting storage
        self.request_counts = defaultdict(list)
        self.suspicious_ips = set()
        self.blocked_ips = set()

        # Настройка логирования безопасности
        self.setup_security_logging()

    def setup_security_logging(self):
        """Настройка логирования безопасности"""
        try:
            security_logger = logging.getLogger('security')
            security_handler = logging.FileHandler('security.log')
            security_handler.setFormatter(logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
            ))
            security_logger.addHandler(security_handler)
            security_logger.setLevel(logging.WARNING)
        except Exception as e:
            logger.warning(f"Could not setup security logging: {e}")

    def get_client_ip(self) -> str:
        """Получение реального IP клиента"""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        return request.environ.get('REMOTE_ADDR', '127.0.0.1')

    def rate_limit_check(self, identifier: str) -> bool:
        """Проверка rate limiting"""
        now = time.time()
        self.request_counts[identifier] = [
            req_time for req_time in self.request_counts[identifier]
            if now - req_time < Config.TIME_WINDOW
        ]

        if len(self.request_counts[identifier]) >= Config.REQUEST_LIMIT:
            return False

        self.request_counts[identifier].append(now)
        return True

    def is_suspicious_request(self, request_data: Dict[str, Any]) -> bool:
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

    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Логирование событий безопасности"""
        security_logger = logging.getLogger('security')
        security_logger.warning(f"SECURITY_EVENT: {event_type}", extra={
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def validate_telegram_username(self, username: str) -> Tuple[bool, str]:
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

    def sanitize_input(self, input_str: str, max_length: int = 100) -> Optional[str]:
        """Безопасная очистка пользовательского ввода"""
        if not input_str:
            return None

        cleaned = re.sub(r'[<>"\';\\]', '', input_str.strip())

        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]

        cleaned = html.escape(cleaned)
        return cleaned if cleaned else None

    def validate_offer_data(self, data: Dict[str, Any]) -> list:
        """Безопасная валидация данных оффера"""
        errors = []

        # Проверка title с защитой от XSS
        title = self.sanitize_input(data.get('title', ''), 200)
        if not title or len(title) < 10:
            errors.append('Заголовок должен быть от 10 до 200 символов')

        # Проверка description
        description = self.sanitize_input(data.get('description', ''), 500)
        if not description or len(description) < 20:
            errors.append('Описание должно быть от 20 до 500 символов')

        # Проверка content
        content = self.sanitize_input(data.get('content', ''), 2000)
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


# Глобальный экземпляр
security_service = SecurityService()