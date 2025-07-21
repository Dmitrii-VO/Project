# app/utils/response_utils.py
"""
Утилиты для стандартизации ответов API
"""

from flask import jsonify
from typing import Any, Dict, Optional
from .helpers import create_success_response, create_error_response


def success_response(data: Any = None, message: str = "Success", status_code: int = 200):
    """
    Создание стандартного успешного ответа API
    
    Args:
        data: Данные для ответа
        message: Сообщение
        status_code: HTTP статус код
    
    Returns:
        Flask Response object
    """
    response = create_success_response(data, message)
    return jsonify(response), status_code


def error_response(message: str, status_code: int = 400, error_code: str = "GENERIC_ERROR"):
    """
    Создание стандартного ответа об ошибке
    
    Args:
        message: Сообщение об ошибке
        status_code: HTTP статус код
        error_code: Код ошибки
    
    Returns:
        Flask Response object
    """
    response = create_error_response(message, error_code)
    return jsonify(response), status_code


def validation_error_response(errors: list, message: str = "Ошибка валидации"):
    """
    Создание ответа для ошибок валидации
    
    Args:
        errors: Список ошибок валидации
        message: Общее сообщение
    
    Returns:
        Flask Response object
    """
    response = create_error_response(message, "VALIDATION_ERROR")
    response["errors"] = errors
    return jsonify(response), 400


def not_found_response(message: str = "Ресурс не найден"):
    """
    Создание ответа для 404 ошибки
    
    Args:
        message: Сообщение об ошибке
    
    Returns:
        Flask Response object
    """
    return error_response(message, 404, "NOT_FOUND")


def unauthorized_response(message: str = "Требуется авторизация"):
    """
    Создание ответа для 401 ошибки
    
    Args:
        message: Сообщение об ошибке
    
    Returns:
        Flask Response object
    """
    return error_response(message, 401, "UNAUTHORIZED")


def forbidden_response(message: str = "Доступ запрещен"):
    """
    Создание ответа для 403 ошибки
    
    Args:
        message: Сообщение об ошибке
    
    Returns:
        Flask Response object
    """
    return error_response(message, 403, "FORBIDDEN")


def internal_error_response(message: str = "Внутренняя ошибка сервера"):
    """
    Создание ответа для 500 ошибки
    
    Args:
        message: Сообщение об ошибке
    
    Returns:
        Flask Response object
    """
    return error_response(message, 500, "INTERNAL_ERROR")