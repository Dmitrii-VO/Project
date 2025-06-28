# add_offer_fixed.py - Исправленная система создания офферов
import sqlite3
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

import requests

try:
    from flask import request, jsonify

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    request = None
    jsonify = None

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к базе данных
DATABASE_PATH = 'telegram_mini_app.db'


def get_db_connection():
    """Получение подключения к SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к SQLite: {e}")


def safe_execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Безопасное выполнение SQL запросов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None
        elif fetch_all:
            result = cursor.fetchall()
            conn.close()
            return [dict(row) for row in result] if result else []
        else:
            conn.commit()
            lastrowid = cursor.lastrowid
            conn.close()
            return lastrowid

    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        if 'conn' in locals():
            conn.close()
        raise


def validate_offer_data(data: Dict[str, Any]) -> List[str]:
    """Валидация данных оффера - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    errors = []

    # Проверка обязательных полей
    if not data.get('title', '').strip():
        errors.append('Название оффера обязательно')

    # ИСПРАВЛЕНИЕ: Проверяем и description, и content
    description = data.get('description', '').strip()
    content = data.get('content', '').strip()

    if not description and not content:
        errors.append('Описание оффера обязательно')

    # ИСПРАВЛЕНИЕ: Более гибкая проверка цены
    price = data.get('price', 0)
    budget_total = data.get('budget_total', 0)
    max_price = data.get('max_price', 0)

    # Пытаемся найти хотя бы одно значение цены
    final_price = 0
    if price and float(price) > 0:
        final_price = float(price)
    elif max_price and float(max_price) > 0:
        final_price = float(max_price)
    elif budget_total and float(budget_total) > 0:
        # Используем 10% от общего бюджета как цену за размещение
        final_price = min(float(budget_total) * 0.1, 50000)

    if final_price <= 0:
        errors.append('Укажите цену за размещение или общий бюджет')

    # Проверка длины полей
    title = data.get('title', '').strip()
    if title and (len(title) < 5 or len(title) > 200):
        errors.append('Название должно быть от 5 до 200 символов')

    # Проверка цены
    try:
        if final_price < 10 or final_price > 1000000:
            errors.append('Цена должна быть от 10 до 1,000,000 рублей')
    except (ValueError, TypeError):
        errors.append('Некорректная цена')

    # Проверка валюты
    currency = data.get('currency', 'RUB').upper()
    allowed_currencies = ['RUB', 'USD', 'EUR']
    if currency not in allowed_currencies:
        errors.append(f'Валюта должна быть одной из: {", ".join(allowed_currencies)}')

    # Проверка категории
    category = data.get('category', 'general')
    allowed_categories = [
        'general', 'tech', 'finance', 'lifestyle', 'education',
        'entertainment', 'business', 'health', 'sports', 'travel', 'other'
    ]
    if category not in allowed_categories:
        errors.append(f'Категория должна быть одной из: {", ".join(allowed_categories)}')

    return errors


def ensure_user_exists(user_id: int, username: str = None, first_name: str = None) -> int:
    """Убеждаемся что пользователь существует в БД"""
    user = safe_execute_query(
        'SELECT id FROM users WHERE telegram_id = ?',
        (user_id,),
        fetch_one=True
    )

    if not user:
        # Создаем нового пользователя
        user_db_id = safe_execute_query('''
                                        INSERT INTO users (telegram_id, username, first_name, created_at)
                                        VALUES (?, ?, ?, ?)
                                        ''', (
                                            user_id,
                                            username or f'user_{user_id}',
                                            first_name or 'User',
                                            datetime.now().isoformat()
                                        ))

        logger.info(f"Создан новый пользователь: {user_id}")
        return user_db_id

    return user['id']


def add_offer(user_id: int, offer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Основная функция добавления оффера

    Args:
        user_id: Telegram ID пользователя
        offer_data: Данные оффера

    Returns:
        Dict с результатом операции
    """
    try:
        logger.info(f"Создание оффера пользователем {user_id}: {offer_data}")

        # Валидация данных
        errors = validate_offer_data(offer_data)
        if errors:
            return {
                'success': False,
                'errors': errors
            }

        # Убеждаемся что пользователь существует
        user_db_id = ensure_user_exists(
            user_id,
            offer_data.get('username'),
            offer_data.get('first_name')
        )

        # ИСПРАВЛЕНИЕ: Подготовка данных для вставки
        title = offer_data['title'].strip()
        description = offer_data.get('description', '').strip()
        content = offer_data.get('content', '').strip()

        # ИСПРАВЛЕНИЕ: Более умная логика для description и content
        if not description and content:
            description = content[:200] + "..." if len(content) > 200 else content
        elif not description:
            description = title  # Fallback к title

        # Если нет content, используем description
        if not content:
            content = description

        # ИСПРАВЛЕНИЕ: Правильная обработка цены с fallback логикой
        price = 0
        if 'price' in offer_data and offer_data['price']:
            price = float(offer_data['price'])
        elif 'max_price' in offer_data and offer_data['max_price']:
            price = float(offer_data['max_price'])
        elif 'budget_total' in offer_data and offer_data['budget_total']:
            # Используем 10% от общего бюджета как цену за размещение
            budget_total_temp = float(offer_data['budget_total'])
            price = min(budget_total_temp * 0.1, 50000)
        else:
            # Если вообще ничего нет, ошибка должна была быть поймана в валидации
            price = 1000  # Fallback значение

        currency = offer_data.get('currency', 'RUB').upper()
        category = offer_data.get('category', 'general')

        # Дополнительные параметры
        target_audience = offer_data.get('target_audience', '').strip()
        requirements = offer_data.get('requirements', '').strip()
        duration_days = int(offer_data.get('duration_days', 30))

        # ИСПРАВЛЕНИЕ: Обработка budget_total
        budget_total = float(offer_data.get('budget_total', price))
        if budget_total < price:
            budget_total = price  # Общий бюджет не может быть меньше цены за размещение

        # ИСПРАВЛЕНИЕ: Расширенные метаданные оффера
        metadata = {
            'contact_info': offer_data.get('contact_info', ''),
            'preferred_channels': offer_data.get('preferred_channels', []),
            'blacklist_channels': offer_data.get('blacklist_channels', []),
            'geo_targeting': offer_data.get('geo_targeting', []),
            'age_targeting': offer_data.get('age_targeting', ''),
            'posting_time': offer_data.get('posting_time', ''),
            'additional_requirements': offer_data.get('additional_requirements', ''),
            'topics': offer_data.get('topics', ''),  # ДОБАВЛЕНО
            'geography': offer_data.get('geography', ''),  # ДОБАВЛЕНО
            'created_via': 'web_interface',
            'category': category,
            'original_data': {  # ДОБАВЛЕНО: сохраняем оригинальные данные для отладки
                'max_price': offer_data.get('max_price'),
                'budget_total': offer_data.get('budget_total'),
                'price': offer_data.get('price')
            }
        }

        # ДОБАВЛЕНО: Отладочная информация
        logger.info(f"DEBUG: Подготовленные данные - price: {price}, budget_total: {budget_total}, currency: {currency}")
        logger.info(f"DEBUG: title: {title}, description: {description[:50]}...")

        # Расчет дат
        current_time = datetime.now()
        deadline_date = (current_time + timedelta(days=duration_days)).date()
        expires_at = current_time + timedelta(days=duration_days)

        # Параметры подписчиков
        min_subscribers = int(offer_data.get('min_subscribers', 1))
        max_subscribers = int(offer_data.get('max_subscribers', 100000000))

        # Вставка оффера в базу данных
        offer_id = safe_execute_query('''
                                      INSERT INTO offers (created_by, title, description, content, price, currency,
                                                          target_audience, requirements, deadline, status, category,
                                                          metadata, budget_total, expires_at, duration_days,
                                                          min_subscribers, max_subscribers)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                      ''', (
                                          user_db_id,
                                          title,
                                          description,
                                          content,
                                          price,
                                          currency,
                                          target_audience,
                                          requirements,
                                          deadline_date.isoformat(),
                                          'active',
                                          category,
                                          json.dumps(metadata, ensure_ascii=False),
                                          budget_total,
                                          expires_at.isoformat(),
                                          duration_days,
                                          min_subscribers,
                                          max_subscribers
                                      ))

        logger.info(f"Создан новый оффер {offer_id} пользователем {user_id}")

        # Получаем созданный оффер для возврата
        created_offer = safe_execute_query('''
                                           SELECT o.*, u.username, u.first_name
                                           FROM offers o
                                                    JOIN users u ON o.created_by = u.id
                                           WHERE o.id = ?
                                           ''', (offer_id,), fetch_one=True)

        return {
            'success': True,
            'offer_id': offer_id,
            'offer': created_offer,
            'message': 'Оффер успешно создан',
            'deadline': deadline_date.strftime('%d.%m.%Y'),
            'expires_at': expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f'Ошибка создания оффера: {str(e)}'
        }


def delete_offer_by_id(offer_id: int, telegram_user_id: int) -> Dict[str, Any]:
    """
    Удаление оффера по ID с проверкой прав доступа

    Args:
        offer_id: ID оффера для удаления
        telegram_user_id: Telegram ID пользователя

    Returns:
        Dict с результатом операции
    """
    logger.info(f"🗑️ Удаление оффера {offer_id} пользователем {telegram_user_id}")

    try:
        # Получаем ID пользователя в БД
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return {
                'success': False,
                'error': 'Пользователь не найден'
            }

        user_db_id = user['id']

        # Проверяем существование оффера и права доступа
        offer = safe_execute_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return {
                'success': False,
                'error': 'Оффер не найден'
            }

        # Проверяем права доступа
        if offer['created_by'] != user_db_id:
            return {
                'success': False,
                'error': 'У вас нет прав для удаления этого оффера'
            }

        # Проверяем статус оффера
        if offer['status'] in ['active', 'paused']:
            logger.warning(f"Попытка удаления активного оффера {offer_id}")
            return {
                'success': False,
                'error': 'Нельзя удалить активный оффер. Сначала завершите или отмените его.'
            }

        # Начинаем транзакцию для удаления связанных данных
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute('BEGIN TRANSACTION')

        try:
            # Удаляем связанные отклики
            conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
            logger.info(f"Удалены отклики для оффера {offer_id}")

            # Удаляем сам оффер
            conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
            logger.info(f"Удален оффер {offer_id}: {offer['title']}")

            conn.commit()

            return {
                'success': True,
                'message': f'Оффер "{offer["title"]}" успешно удален',
                'offer_id': offer_id
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при удалении оффера {offer_id}: {e}")
            return {
                'success': False,
                'error': 'Ошибка при удалении оффера'
            }
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Общая ошибка удаления оффера {offer_id}: {e}")
        return {
            'success': False,
            'error': 'Внутренняя ошибка при удалении оффера'
        }


def cancel_offer_by_id(offer_id: int, telegram_user_id: int, reason: str = '') -> Dict[str, Any]:
    """
    Отмена оффера по ID с проверкой прав доступа

    Args:
        offer_id: ID оффера для отмены
        telegram_user_id: Telegram ID пользователя
        reason: Причина отмены (опционально)

    Returns:
        Dict с результатом операции
    """
    logger.info(f"❌ Отмена оффера {offer_id} пользователем {telegram_user_id}")

    try:
        # Получаем ID пользователя в БД
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return {
                'success': False,
                'error': 'Пользователь не найден'
            }

        user_db_id = user['id']

        # Проверяем существование оффера и права доступа
        offer = safe_execute_query(
            'SELECT id, created_by, title, status, price FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return {
                'success': False,
                'error': 'Оффер не найден'
            }

        # Проверяем права доступа
        if offer['created_by'] != user_db_id:
            return {
                'success': False,
                'error': 'У вас нет прав для отмены этого оффера'
            }

        # Проверяем текущий статус
        now = datetime.now().isoformat()
        update_query = '''
                       UPDATE offers
                       SET status     = 'cancelled',
                           updated_at = ?
                       WHERE id = ?
                       '''

        safe_execute_query(update_query, (now, offer_id))

        # Логируем причину отмены отдельно
        if reason:
            logger.info(f"Причина отмены: {reason}")

        # Уведомляем владельцев каналов которые откликнулись
        notify_channels_about_cancellation(offer_id, offer['title'])

        logger.info(f"Оффер {offer_id} успешно отменен")

        return {
            'success': True,
            'message': f'Оффер "{offer["title"]}" отменен',
            'offer_id': offer_id,
            'new_status': 'cancelled'
        }

    except Exception as e:
        logger.error(f"Ошибка отмены оффера {offer_id}: {e}")
        return {
            'success': False,
            'error': 'Ошибка при отмене оффера'
        }


def update_offer_status_by_id(offer_id: int, telegram_user_id: int, new_status: str, reason: str = '') -> Dict[
    str, Any]:
    """
    Универсальная функция обновления статуса оффера

    Args:
        offer_id: ID оффера
        telegram_user_id: Telegram ID пользователя
        new_status: Новый статус (active, paused, cancelled, completed)
        reason: Причина изменения статуса

    Returns:
        Dict с результатом операции
    """
    logger.info(f"🔄 Изменение статуса оффера {offer_id} на {new_status}")

    logger.info(f"🔄 Изменение статуса оффера {offer_id} на {new_status} пользователем {telegram_user_id}")

    try:
        # Получаем ID пользователя в БД
        logger.info(f"Ищем пользователя с telegram_id: {telegram_user_id}")
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            logger.error(f"Пользователь {telegram_user_id} не найден в БД")
            return {'success': False, 'error': 'Пользователь не найден'}

        user_db_id = user['id']
        logger.info(f"Найден пользователь с DB ID: {user_db_id}")

        # Проверяем существование оффера и права доступа
        logger.info(f"Ищем оффер {offer_id}")
        offer = safe_execute_query(
            'SELECT id, created_by, title, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            logger.error(f"Оффер {offer_id} не найден")
            return {'success': False, 'error': 'Оффер не найден'}

        logger.info(f"Найден оффер: ID={offer['id']}, created_by={offer['created_by']}, status={offer['status']}")

        if offer['created_by'] != user_db_id:
            logger.error(
                f"Пользователь {user_db_id} не является владельцем оффера {offer_id} (владелец: {offer['created_by']})")
            return {'success': False, 'error': 'У вас нет прав для изменения этого оффера'}

        current_status = offer['status']
        logger.info(f"Текущий статус: {current_status}, новый статус: {new_status}")

        # Проверяем допустимость перехода статуса
        status_transitions = {
            'active': ['paused', 'cancelled', 'completed'],
            'paused': ['active', 'cancelled', 'completed'],
            'cancelled': [],  # Из отмененного нельзя перейти в другой статус
            'completed': []  # Из завершенного нельзя перейти в другой статус
        }

        if new_status not in status_transitions.get(current_status, []):
            logger.error(f"Недопустимый переход статуса: {current_status} -> {new_status}")
            return {
                'success': False,
                'error': f'Нельзя изменить статус с "{current_status}" на "{new_status}"'
            }

        logger.info(f"Переход статуса {current_status} -> {new_status} разрешен")

        # Обновляем статус
        now = datetime.now().isoformat()
        update_query = '''
                       UPDATE offers
                       SET status     = ?,
                           updated_at = ?
                       WHERE id = ?
                       '''

        logger.info(f"Выполняем UPDATE запрос с параметрами: status={new_status}, id={offer_id}")
        safe_execute_query(update_query, (new_status, now, offer_id))

        # Логируем причину изменения отдельно
        if reason:
            logger.info(f"Причина изменения статуса: {reason}")

        # Дополнительные действия в зависимости от статуса
        if new_status == 'cancelled':
            logger.info(f"Уведомляем об отмене оффера {offer_id}")
            notify_channels_about_cancellation(offer_id, offer['title'])
        elif new_status == 'completed':
            logger.info(f"Уведомляем о завершении оффера {offer_id}")
            notify_channels_about_completion(offer_id, offer['title'])

        logger.info(f"✅ Статус оффера {offer_id} успешно изменен с {current_status} на {new_status}")

        return {
            'success': True,
            'message': f'Статус оффера "{offer["title"]}" изменен на "{new_status}"',
            'offer_id': offer_id,
            'old_status': current_status,
            'new_status': new_status
        }

    except Exception as e:
        logger.error(f"❌ ДЕТАЛЬНАЯ ОШИБКА изменения статуса оффера {offer_id}: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'Ошибка при изменении статуса оффера: {str(e)}'
        }


def notify_channels_about_cancellation(offer_id: int, offer_title: str):
    """Уведомление владельцев каналов об отмене оффера"""
    try:
        # Получаем список каналов которые откликнулись на оффер
        responses = safe_execute_query('''
                                       SELECT DISTINCT or_resp.channel_id, ch.title as channel_title, ch.owner_id
                                       FROM offer_responses or_resp
                                                JOIN channels ch ON or_resp.channel_id = ch.id
                                       WHERE or_resp.offer_id = ?
                                         AND or_resp.status IN ('pending', 'accepted')
                                       ''', (offer_id,), fetch_all=True)

        logger.info(f"Уведомляем {len(responses)} владельцев каналов об отмене оффера {offer_id}")

        # Здесь можно добавить отправку уведомлений через Telegram API
        for response in responses:
            logger.info(f"Уведомление владельцу канала {response['channel_title']} (ID: {response['owner_id']})")

    except Exception as e:
        logger.error(f"Ошибка уведомления об отмене оффера {offer_id}: {e}")


def notify_channels_about_completion(offer_id: int, offer_title: str):
    """Уведомление об успешном завершении оффера"""
    try:
        logger.info(f"Уведомляем о завершении оффера {offer_id}: {offer_title}")
        # Здесь можно добавить логику уведомлений

    except Exception as e:
        logger.error(f"Ошибка уведомления о завершении оффера {offer_id}: {e}")


def get_user_offers(user_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Получение офферов пользователя с правильным подсчетом откликов"""
    try:
        # Получаем user_db_id
        user = safe_execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (user_id,),
            fetch_one=True
        )

        if not user:
            logger.warning(f"Пользователь {user_id} не найден")
            return []

        user_db_id = user['id']
        logger.info(f"Загружаем офферы для пользователя {user_id} (DB ID: {user_db_id})")

        # ИСПРАВЛЕННЫЙ запрос с правильным подсчетом откликов
        base_query = '''
                     SELECT o.*,
                            COALESCE(response_stats.response_count, 0) as response_count,
                            COALESCE(response_stats.accepted_count, 0) as accepted_count
                     FROM offers o
                              LEFT JOIN (SELECT offer_id, \
                                                COUNT(*)                                        as response_count, \
                                                COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count \
                                         FROM offer_responses \
                                         GROUP BY offer_id) response_stats ON o.id = response_stats.offer_id
                     WHERE o.created_by = ? \
                     '''

        if status:
            query = base_query + ' AND o.status = ? ORDER BY o.created_at DESC'
            params = (user_db_id, status)
        else:
            query = base_query + ' ORDER BY o.created_at DESC'
            params = (user_db_id,)

        offers = safe_execute_query(query, params, fetch_all=True)
        logger.info(f"Найдено офферов в БД: {len(offers)}")

        # Форматируем данные для фронтенда
        formatted_offers = []
        for offer in offers:
            # Парсим метаданные
            try:
                metadata = json.loads(offer.get('metadata', '{}'))
            except:
                metadata = {}

            response_count = offer.get('response_count', 0)
            accepted_count = offer.get('accepted_count', 0)

            formatted_offer = {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'content': offer['content'],
                'price': float(offer['price']),
                'currency': offer['currency'],
                'category': offer['category'],
                'status': offer['status'],
                'target_audience': offer.get('target_audience', ''),
                'requirements': offer.get('requirements', ''),
                'deadline': offer.get('deadline', ''),
                'created_at': offer['created_at'],
                'updated_at': offer['updated_at'],
                'response_count': response_count,  # ИСПРАВЛЕНО: правильный подсчет
                'accepted_count': accepted_count,
                'budget_total': float(offer.get('budget_total', 0)),
                'duration_days': offer.get('duration_days', 30),
                'min_subscribers': offer.get('min_subscribers', 1),
                'max_subscribers': offer.get('max_subscribers', 100000000),
                'metadata': metadata
            }
            formatted_offers.append(formatted_offer)

            # Отладочный лог
            logger.info(f"Оффер {offer['id']} '{offer['title']}': {response_count} откликов")

        logger.info(f"Возвращаем {len(formatted_offers)} офферов для пользователя {user_id}")
        return formatted_offers

    except Exception as e:
        logger.error(f"Ошибка получения офферов пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_offer_by_id(offer_id: int, include_responses: bool = False) -> Optional[Dict[str, Any]]:
    """Получение оффера по ID"""
    try:
        offer = safe_execute_query('''
                                   SELECT o.*, u.username as creator_username, u.first_name as creator_name
                                   FROM offers o
                                            JOIN users u ON o.created_by = u.id
                                   WHERE o.id = ?
                                   ''', (offer_id,), fetch_one=True)

        if not offer:
            return None

        # Парсим метаданные
        try:
            metadata = json.loads(offer.get('metadata', '{}'))
        except:
            metadata = {}

        formatted_offer = {
            'id': offer['id'],
            'title': offer['title'],
            'description': offer['description'],
            'content': offer['content'],
            'price': float(offer['price']),
            'currency': offer['currency'],
            'category': offer['category'],
            'status': offer['status'],
            'target_audience': offer.get('target_audience', ''),
            'requirements': offer.get('requirements', ''),
            'deadline': offer.get('deadline', ''),
            'created_at': offer['created_at'],
            'updated_at': offer['updated_at'],
            'creator_username': offer.get('creator_username', ''),
            'creator_name': offer.get('creator_name', ''),
            'budget_total': float(offer.get('budget_total', 0)),
            'duration_days': offer.get('duration_days', 30),
            'min_subscribers': offer.get('min_subscribers', 1),
            'max_subscribers': offer.get('max_subscribers', 100000000),
            'metadata': metadata
        }

        # Добавляем отклики если требуется
        if include_responses:
            responses = safe_execute_query('''
                                           SELECT or_resp.*,
                                                  c.title    as channel_title,
                                                  c.username as channel_username,
                                                  c.subscriber_count,
                                                  u.username as responder_username
                                           FROM offer_responses or_resp
                                                    JOIN channels c ON or_resp.channel_id = c.id
                                                    JOIN users u ON c.owner_id = u.id
                                           WHERE or_resp.offer_id = ?
                                           ORDER BY or_resp.created_at DESC
                                           ''', (offer_id,), fetch_all=True)

            formatted_offer['responses'] = responses or []

        return formatted_offer

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return None


def get_available_offers(filters=None):
    """
    Получить доступные офферы с фильтрацией

    Args:
        filters (dict): Словарь с фильтрами:
            - category: категория оффера
            - min_budget: минимальный бюджет
            - max_budget: максимальный бюджет
            - search: поиск по названию/описанию
            - min_subscribers: минимальное количество подписчиков
            - exclude_user_id: ID пользователя, чьи офферы нужно исключить
            - limit: количество записей

    Returns:
        list: Список офферов
    """
    if filters is None:
        filters = {}

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Базовый запрос - исключаем только активные офферы других пользователей
        base_query = """
                     SELECT o.*, \
                            u.first_name, \
                            u.last_name, \
                            u.username as creator_username
                     FROM offers o
                              LEFT JOIN users u ON o.created_by = u.id
                     WHERE o.status = 'active' \
                     """

        query_params = []
        conditions = []

        # ВАЖНО: Исключаем офферы текущего пользователя
        exclude_user_id = filters.get('exclude_user_id')
        if exclude_user_id:
            # Получаем ID пользователя в базе данных
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (exclude_user_id,))
            user_row = cursor.fetchone()
            if user_row:
                conditions.append("o.created_by != ?")
                query_params.append(user_row['id'])
                logger.info(f"Исключаем офферы пользователя с DB ID: {user_row['id']} (Telegram ID: {exclude_user_id})")

        # Фильтр по категории
        if filters.get('category'):
            conditions.append("o.category = ?")
            query_params.append(filters['category'])

        # Фильтр по минимальному бюджету
        if filters.get('min_budget'):
            conditions.append("o.price >= ?")
            query_params.append(filters['min_budget'])

        # Фильтр по максимальному бюджету
        if filters.get('max_budget'):
            conditions.append("o.price <= ?")
            query_params.append(filters['max_budget'])

        # Поиск по названию и описанию
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            conditions.append("(o.title LIKE ? OR o.description LIKE ?)")
            query_params.extend([search_term, search_term])

        # Фильтр по минимальному количеству подписчиков
        if filters.get('min_subscribers'):
            conditions.append("o.min_subscribers <= ?")
            query_params.append(filters['min_subscribers'])

        # Добавляем условия к запросу
        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        # Сортировка по дате создания (новые сначала)
        base_query += " ORDER BY o.created_at DESC"

        # Лимит
        limit = filters.get('limit', 50)
        base_query += " LIMIT ?"
        query_params.append(limit)

        logger.info(f"SQL запрос: {base_query}")
        logger.info(f"Параметры: {query_params}")

        cursor.execute(base_query, query_params)
        rows = cursor.fetchall()

        offers = []
        for row in rows:
            # Формируем имя создателя
            creator_name = ""
            if row['first_name']:
                creator_name += row['first_name']
            if row['last_name']:
                creator_name += f" {row['last_name']}"
            if not creator_name and row['creator_username']:
                creator_name = f"@{row['creator_username']}"
            if not creator_name:
                creator_name = "Анонимный пользователь"

            offer = {
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'content': row['content'],
                'price': float(row['price']) if row['price'] else 0,
                'currency': row['currency'] or 'RUB',
                'category': row['category'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'created_by': row['created_by'],
                'creator_name': creator_name,
                'budget_total': float(row['budget_total']) if row['budget_total'] else 0,
                'min_subscribers': row['min_subscribers'] or 0,
                'max_subscribers': row['max_subscribers'] or 0,
                'deadline': row['deadline'],
                'target_audience': row['target_audience'],
                'requirements': row['requirements']
            }
            offers.append(offer)

        conn.close()

        logger.info(f"Возвращено {len(offers)} доступных офферов")
        return offers

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        import traceback
        traceback.print_exc()
        return []


def create_offer_response(offer_id, user_id, channel_info, message=""):
    """
    Создание отклика на оффер

    Args:
        offer_id: ID оффера
        user_id: Telegram ID пользователя (владельца канала)
        channel_info: Информация о канале
        message: Сообщение от владельца канала

    Returns:
        dict: Результат операции
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Проверяем, существует ли оффер
        cursor.execute('SELECT * FROM offers WHERE id = ? AND status = "active"', (offer_id,))
        offer = cursor.fetchone()

        if not offer:
            return {'success': False, 'error': 'Оффер не найден или неактивен'}

        # Получаем или создаем пользователя в БД
        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
        user_row = cursor.fetchone()

        if not user_row:
            # Создаем пользователя если не существует
            cursor.execute('''
                           INSERT INTO users (telegram_id, first_name, created_at)
                           VALUES (?, ?, ?)
                           ''', (user_id, 'Пользователь', datetime.now().isoformat()))
            user_db_id = cursor.lastrowid
        else:
            user_db_id = user_row[0]

        # Проверяем, не откликался ли уже этот пользователь
        cursor.execute('''
                       SELECT id
                       FROM offer_responses
                       WHERE offer_id = ?
                         AND user_id = ?
                       ''', (offer_id, user_db_id))

        existing_response = cursor.fetchone()
        if existing_response:
            return {'success': False, 'error': 'Вы уже откликнулись на этот оффер'}

        # Создаем отклик
        cursor.execute('''
                       INSERT INTO offer_responses (offer_id, user_id, message, status,
                                                    channel_username, channel_title, channel_subscribers,
                                                    created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ''', (
                           offer_id, user_db_id, message, 'pending',
                           channel_info.get('username', ''),
                           channel_info.get('title', ''),
                           channel_info.get('subscribers', 0),
                           datetime.now().isoformat()
                       ))

        response_id = cursor.lastrowid

        # Обновляем количество откликов в оффере
        cursor.execute('''
                       UPDATE offers
                       SET response_count = (SELECT COUNT(*)
                                             FROM offer_responses
                                             WHERE offer_id = ?)
                       WHERE id = ?
                       ''', (offer_id, offer_id))

        conn.commit()
        conn.close()

        # Отправляем уведомление автору оффера
        send_offer_notification(offer_id, response_id, 'new_response')

        logger.info(f"Создан отклик {response_id} на оффер {offer_id} от пользователя {user_id}")

        return {
            'success': True,
            'response_id': response_id,
            'message': 'Отклик успешно отправлен! Автор оффера получил уведомление.'
        }

    except Exception as e:
        logger.error(f"Ошибка создания отклика: {e}")
        return {'success': False, 'error': f'Ошибка создания отклика: {str(e)}'}


def get_offer_responses(offer_id, user_id=None):
    """Получение откликов на оффер"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем права доступа (только автор оффера может видеть отклики)
        if user_id:
            cursor.execute('''
                           SELECT u.id
                           FROM offers o
                                    JOIN users u ON o.created_by = u.id
                           WHERE o.id = ?
                             AND u.telegram_id = ?
                           ''', (offer_id, user_id))

            if not cursor.fetchone():
                return {'success': False, 'error': 'Нет доступа к откликам'}

        # Получаем отклики
        cursor.execute('''
                       SELECT or_resp.*,
                              u.first_name,
                              u.last_name,
                              u.username as user_username
                       FROM offer_responses or_resp
                                JOIN users u ON or_resp.user_id = u.id
                       WHERE or_resp.offer_id = ?
                       ORDER BY or_resp.created_at DESC
                       ''', (offer_id,))

        rows = cursor.fetchall()

        responses = []
        for row in rows:
            # Формируем имя пользователя
            user_name = ""
            if row['first_name']:
                user_name += row['first_name']
            if row['last_name']:
                user_name += f" {row['last_name']}"
            if not user_name and row['user_username']:
                user_name = f"@{row['user_username']}"
            if not user_name:
                user_name = "Пользователь"

            response = {
                'id': row['id'],
                'offer_id': row['offer_id'],
                'user_id': row['user_id'],
                'user_name': user_name,
                'message': row['message'],
                'status': row['status'],
                'channel_username': row['channel_username'],
                'channel_title': row['channel_title'],
                'channel_subscribers': row['channel_subscribers'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            responses.append(response)

        conn.close()

        return {
            'success': True,
            'responses': responses,
            'count': len(responses)
        }

    except Exception as e:
        logger.error(f"Ошибка получения откликов: {e}")
        return {'success': False, 'error': str(e)}


def update_response_status(response_id, new_status, user_id, message=""):
    """Обновление статуса отклика (принять/отклонить) с автоматическим созданием контракта"""
    try:
        logger.info(f"📝 Обновление статуса отклика {response_id} на {new_status}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем права доступа
        cursor.execute('''
                       SELECT or_resp.*,
                              o.created_by,
                              o.title       as offer_title,
                              o.price       as offer_price,
                              o.budget_total,
                              u.telegram_id as author_telegram_id,
                              ch.title      as channel_title,
                              ch.username   as channel_username,
                              ch.owner_id   as channel_owner_id
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                                JOIN users u ON o.created_by = u.id
                                LEFT JOIN channels ch ON or_resp.channel_id = ch.id
                       WHERE or_resp.id = ?
                       ''', (response_id,))

        response_row = cursor.fetchone()
        if not response_row:
            conn.close()
            return {'success': False, 'error': 'Отклик не найден'}

        if response_row['author_telegram_id'] != user_id:
            conn.close()
            return {'success': False, 'error': 'Нет прав для изменения статуса'}

        if response_row['status'] != 'pending':
            conn.close()
            return {'success': False, 'error': 'Отклик уже обработан'}

        # Обновляем статус отклика
        cursor.execute('''
                       UPDATE offer_responses
                       SET status        = ?,
                           updated_at    = ?,
                           admin_message = ?
                       WHERE id = ?
                       ''', (new_status, datetime.now().isoformat(), message, response_id))

        # Если отклик принят, создаем контракт автоматически
        contract_id = None
        if new_status == 'accepted':
            logger.info(f"✅ Отклик принят, создаем контракт для response_id: {response_id}")

            # Отклоняем остальные отклики как 'rejected'
            cursor.execute('''
                           UPDATE offer_responses
                           SET status        = 'rejected',
                               updated_at    = ?,
                               admin_message = 'Автоматически отклонен (выбран другой канал)'
                           WHERE offer_id = ?
                             AND id != ? 
                             AND status = 'pending'
                           ''', (datetime.now().isoformat(), response_row['offer_id'], response_id))

            # ИСПРАВЛЕНО: Оставляем статус оффера как 'active' вместо 'in_progress'
            # Добавляем метаданные о том, что у оффера есть принятый отклик
            cursor.execute('''
                           UPDATE offers
                           SET updated_at = ?
                           WHERE id = ?
                           ''', (datetime.now().isoformat(), response_row['offer_id']))

            logger.info(f"✅ Оффер {response_row['offer_id']} обновлен (статус остается 'active')")

            # Генерируем уникальный ID контракта
            import hashlib
            import time
            contract_id = hashlib.md5(f"{response_id}_{time.time()}".encode()).hexdigest()[:12].upper()

            # Вычисляем дедлайны
            placement_deadline = datetime.now() + timedelta(hours=24)  # 24 часа на размещение
            monitoring_duration = 7  # 7 дней мониторинга
            monitoring_end = placement_deadline + timedelta(days=monitoring_duration)

            # Определяем цену (используем цену оффера или budget_total)
            price = response_row['offer_price'] or response_row['budget_total'] or 1000

            # Определяем publisher_id
            if not response_row['channel_owner_id']:
                # Если channel_owner_id отсутствует, пытаемся найти пользователя по user_id отклика
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (response_row['user_id'],))
                user_row = cursor.fetchone()
                publisher_id = user_row['id'] if user_row else response_row['user_id']
                logger.warning(f"⚠️ channel_owner_id отсутствует, используем user_id: {publisher_id}")
            else:
                publisher_id = response_row['channel_owner_id']

            # Создаем контракт в таблице contracts
            try:
                cursor.execute('''
                               INSERT INTO contracts (id, response_id, offer_id, advertiser_id, publisher_id,
                                                      price, status, placement_deadline, monitoring_duration,
                                                      monitoring_end, post_requirements, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               ''', (
                                   contract_id,
                                   response_id,
                                   response_row['offer_id'],
                                   response_row['created_by'],  # advertiser_id
                                   publisher_id,  # publisher_id
                                   price,
                                   'active',
                                   placement_deadline.isoformat(),
                                   monitoring_duration,
                                   monitoring_end.isoformat(),
                                   'Согласно условиям оффера',
                                   datetime.now().isoformat(),
                                   datetime.now().isoformat()
                               ))

                logger.info(f"✅ Создан контракт {contract_id} для отклика {response_id}")

            except Exception as contract_error:
                logger.error(f"❌ Ошибка создания контракта: {contract_error}")
                # Контракт не создался, но отклик уже принят - это не критично
                contract_id = None

        conn.commit()
        conn.close()

        # Отправляем уведомления
        try:
            send_response_notification(response_id, new_status)
        except Exception as notification_error:
            logger.warning(f"⚠️ Ошибка отправки уведомления об отклике: {notification_error}")

        # Если создан контракт, отправляем уведомления о контракте
        if contract_id:
            try:
                send_contract_notification(contract_id, 'created')
                logger.info(f"📧 Отправлены уведомления о создании контракта {contract_id}")
            except Exception as contract_notification_error:
                logger.warning(f"⚠️ Ошибка отправки уведомления о контракте: {contract_notification_error}")

        action_text = 'принят' if new_status == 'accepted' else 'отклонён'
        success_message = f'Отклик {action_text}. Пользователь получил уведомление.'

        if contract_id:
            success_message += f' Создан контракт {contract_id}.'

        logger.info(f"✅ Статус отклика {response_id} изменен на {new_status}")

        result = {
            'success': True,
            'message': success_message
        }

        # Добавляем информацию о контракте если он создан
        if contract_id:
            result['contract_id'] = contract_id
            result['contract_created'] = True

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса отклика: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# Заменить/дополнить функцию verify_placement() в add_offer.py

def verify_placement(contract_id):
    """
    Проверка размещения рекламы по контракту

    Args:
        contract_id: ID контракта для проверки

    Returns:
        dict: Результат проверки
    """
    try:
        logger.info(f"🔍 Проверка размещения для контракта {contract_id}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные контракта
        cursor.execute('''
                       SELECT c.*,
                              o.title       as offer_title,
                              o.description as offer_description,
                              o.post_requirements,
                              or_resp.channel_username,
                              or_resp.channel_title
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        contract = cursor.fetchone()

        if not contract:
            return {'success': False, 'error': 'Контракт не найден'}

        if not contract['post_url']:
            return {'success': False, 'error': 'URL поста не указан'}

        # Извлекаем информацию о посте из URL
        post_info = extract_post_info_from_url(contract['post_url'])
        if not post_info['success']:
            return {'success': False, 'error': post_info['error']}

        channel_username = post_info['channel_username']
        message_id = post_info['message_id']

        # Проверяем пост через Telegram API
        verification_result = check_telegram_post(
            channel_username,
            message_id,
            contract['offer_description']  # Ожидаемый контент
        )

        if verification_result['success']:
            # Пост найден и соответствует требованиям
            new_status = 'monitoring'

            # Обновляем статус контракта
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?,
                               verified_at          = ?
                           WHERE id = ?
                           ''', (
                               new_status, True, verification_result['details'],
                               datetime.now().isoformat(), contract_id
                           ))

            # Запускаем мониторинг
            schedule_monitoring(contract_id)

            message = "✅ Размещение проверено и подтверждено! Начат мониторинг."

        else:
            # Пост не найден или не соответствует
            new_status = 'verification_failed'
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?
                           WHERE id = ?
                           ''', (
                               new_status, False, verification_result['error'], contract_id
                           ))

            message = f"❌ Проверка не пройдена: {verification_result['error']}"

        conn.commit()
        conn.close()

        # Отправляем уведомления
        send_contract_notification(contract_id, 'verification_result', {
            'status': new_status,
            'message': message
        })

        logger.info(f"Проверка контракта {contract_id}: {new_status}")

        return {
            'success': True,
            'status': new_status,
            'message': message,
            'details': verification_result
        }

    except Exception as e:
        logger.error(f"Ошибка проверки размещения: {e}")
        return {'success': False, 'error': str(e)}


def extract_post_info_from_url(post_url):
    """
    Извлечение информации о посте из Telegram URL

    Args:
        post_url: URL поста (https://t.me/channel/123)

    Returns:
        dict: Информация о посте
    """
    try:
        import re

        # Паттерны для разных типов URL
        patterns = [
            r'https://t\.me/([^/]+)/(\d+)',  # https://t.me/channel/123
            r'https://t\.me/c/(\d+)/(\d+)',  # https://t.me/c/1234567890/123
        ]

        for pattern in patterns:
            match = re.match(pattern, post_url)
            if match:
                channel_identifier = match.group(1)
                message_id = match.group(2)

                return {
                    'success': True,
                    'channel_username': channel_identifier,
                    'message_id': message_id,
                    'url_type': 'public' if not channel_identifier.isdigit() else 'private'
                }

        return {'success': False, 'error': 'Неверный формат URL поста'}

    except Exception as e:
        return {'success': False, 'error': f'Ошибка парсинга URL: {str(e)}'}

def create_contract(response_id, contract_details):
    """
    Создание контракта после принятия отклика

    Args:
        response_id: ID принятого отклика
        contract_details: Детали контракта (срок размещения, требования и т.д.)

    Returns:
        dict: Результат операции
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем информацию об отклике
        cursor.execute('''
                       SELECT or_resp.*,
                              o.id         as offer_id,
                              o.title,
                              o.price,
                              o.max_price,
                              o.created_by as advertiser_id,
                              o.description,
                              o.budget_total
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                       WHERE or_resp.id = ?
                         AND or_resp.status = 'accepted'
                       ''', (response_id,))

        response_data = cursor.fetchone()
        if not response_data:
            return {'success': False, 'error': 'Принятый отклик не найден'}

        # Генерируем уникальный ID контракта
        contract_id = hashlib.md5(f"{response_id}_{time.time()}".encode()).hexdigest()[:12].upper()

        # Вычисляем дедлайны
        placement_deadline = datetime.now() + timedelta(hours=contract_details.get('placement_hours', 24))
        monitoring_duration = contract_details.get('monitoring_days', 7)
        monitoring_end = placement_deadline + timedelta(days=monitoring_duration)

        # Создаем контракт
        cursor.execute('''
                       INSERT INTO contracts (id, response_id, offer_id, advertiser_id, publisher_id,
                                              price, status,
                                              placement_deadline, monitoring_duration, monitoring_end,
                                              post_requirements, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ''', (
                           contract_id, response_id, response_data['offer_id'],
                           response_data['advertiser_id'], response_data['user_id'],
                           response_data['max_price'] or response_data['price'], 'active',
                           placement_deadline.isoformat(), monitoring_duration, monitoring_end.isoformat(),
                           contract_details.get('requirements', ''), datetime.now().isoformat()
                       ))

        conn.commit()
        conn.close()

        # Отправляем уведомления обеим сторонам
        send_contract_notification(contract_id, 'created')

        logger.info(f"Создан контракт {contract_id} для отклика {response_id}")

        return {
            'success': True,
            'contract_id': contract_id,
            'placement_deadline': placement_deadline.isoformat(),
            'message': 'Контракт создан! Участники получили уведомления с деталями.'
        }

    except Exception as e:
        logger.error(f"Ошибка создания контракта: {e}")
        return {'success': False, 'error': str(e)}


def send_contract_notification(contract_id, notification_type, extra_data=None):
    """Отправка уведомлений по контрактам"""
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем информацию о контракте
        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_adv.first_name  as advertiser_name,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_pub.first_name  as publisher_name,
                              or_resp.channel_title
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        if notification_type == 'created':
            # Уведомления о создании контракта
            advertiser_msg = f"""📋 <b>Контракт создан!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Сумма:</b> {data['price']} RUB
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

⏰ <b>Срок размещения:</b> {formatDate(data['placement_deadline'])}
🔍 <b>Срок мониторинга:</b> {data['monitoring_duration']} дней

📱 Издатель должен разместить рекламу и подать заявку в приложении."""

            publisher_msg = f"""✅ <b>Ваш отклик принят! Контракт создан.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data['price']} RUB
👤 <b>Рекламодатель:</b> {data['advertiser_name']}

⏰ <b>Разместите рекламу до:</b> {formatDate(data['placement_deadline'])}

📝 <b>Что делать дальше:</b>
1. Разместите рекламу в своем канале
2. Подайте заявку с ссылкой на пост в приложении
3. После проверки начнется мониторинг
4. Получите оплату после завершения"""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Открыть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], advertiser_msg, keyboard)
            send_telegram_message(data['publisher_telegram_id'], publisher_msg, keyboard)

        elif notification_type == 'placement_submitted':
            # Уведомление рекламодателю о подаче заявки
            message = f"""📤 <b>Заявка о размещении подана!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

🔍 Начинается автоматическая проверка размещения.
Вы получите уведомление о результате проверки."""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Посмотреть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], message, keyboard)

        elif notification_type == 'verification_result':
            # Уведомления о результате проверки
            status = extra_data.get('status') if extra_data else data['status']

            if status == 'monitoring':
                adv_msg = f"""✅ <b>Размещение подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}

🔍 Начат мониторинг размещения на {data['monitoring_duration']} дней.
Оплата будет произведена автоматически после завершения мониторинга."""

                pub_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>К оплате:</b> {data['price']} RUB

🔍 Начат мониторинг на {data['monitoring_duration']} дней.
Не удаляйте пост до завершения мониторинга!"""

            else:
                error_msg = extra_data.get('message') if extra_data else 'Размещение не соответствует требованиям'

                pub_msg = f"""❌ <b>Проверка не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Причина:</b> {error_msg}

🔄 Исправьте размещение и подайте заявку повторно."""

                adv_msg = f"""❌ <b>Проверка размещения не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Причина:</b> {error_msg}

Издатель должен исправить размещение."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'completed':
            # Уведомления о завершении контракта
            payment_id = extra_data.get('payment_id') if extra_data else 'N/A'
            amount = extra_data.get('amount') if extra_data else data['price']

            adv_msg = f"""✅ <b>Контракт завершен!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
💰 <b>Сумма:</b> {amount} RUB

✅ Мониторинг завершен успешно.
💳 Платеж #{payment_id} обрабатывается."""

            pub_msg = f"""🎉 <b>Поздравляем! Контракт выполнен.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Заработано:</b> {amount} RUB

💳 Платеж #{payment_id} поступит на ваш счет в течение 24 часов.
Спасибо за качественную работу!"""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'violation':
            # Уведомления о нарушении
            reason = extra_data.get('reason') if extra_data else 'Нарушение условий контракта'

            pub_msg = f"""⚠️ <b>Обнаружено нарушение!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Проблема:</b> {reason}

🔄 Пожалуйста, восстановите размещение или свяжитесь с поддержкой."""

            adv_msg = f"""⚠️ <b>Нарушение контракта</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Проблема:</b> {reason}

Мы уведомили издателя о необходимости исправления."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления по контракту: {e}")
def formatDate(date_str):
    """Форматирование даты для уведомлений"""
    try:
        if not date_str:
            return 'Не указано'
        dt = datetime.fromisoformat(date_str)
        return dt.strftime('%d.%m.%Y в %H:%M')
    except:
        return date_str

def submit_placement(contract_id, post_url, user_id):
    """
    Подача заявки о размещении рекламы

    Args:
        contract_id: ID контракта
        post_url: Ссылка на пост с рекламой
        user_id: Telegram ID пользователя (издателя)

    Returns:
        dict: Результат операции
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем контракт
        cursor.execute('''
                       SELECT c.*, u.telegram_id as publisher_telegram_id
                       FROM contracts c
                                JOIN users u ON c.publisher_id = u.id
                       WHERE c.id = ?
                         AND u.telegram_id = ?
                         AND c.status = 'active'
                       ''', (contract_id, user_id))

        contract = cursor.fetchone()
        if not contract:
            return {'success': False, 'error': 'Контракт не найден или недоступен'}

        # Проверяем дедлайн
        placement_deadline = datetime.fromisoformat(contract['placement_deadline'])
        if datetime.now() > placement_deadline:
            cursor.execute('UPDATE contracts SET status = ? WHERE id = ?', ('expired', contract_id))
            conn.commit()
            conn.close()
            return {'success': False, 'error': 'Срок размещения истек'}

        # Извлекаем данные из URL поста
        post_data = extract_post_data(post_url)
        if not post_data['success']:
            return {'success': False, 'error': post_data['error']}

        # Обновляем контракт
        cursor.execute('''
                       UPDATE contracts
                       SET post_url     = ?,
                           post_id      = ?,
                           post_date    = ?,
                           status       = 'verification',
                           submitted_at = ?
                       WHERE id = ?
                       ''', (
                           post_url, post_data['post_id'], post_data['post_date'],
                           datetime.now().isoformat(), contract_id
                       ))

        conn.commit()
        conn.close()

        # Запускаем автоматическую проверку
        verification_result = verify_post_placement(contract_id)

        # Отправляем уведомление рекламодателю
        send_contract_notification(contract_id, 'placement_submitted')

        logger.info(f"Подана заявка о размещении для контракта {contract_id}")

        return {
            'success': True,
            'message': 'Заявка о размещении подана! Начинается автоматическая проверка.',
            'verification_status': verification_result.get('status', 'pending')
        }

    except Exception as e:
        logger.error(f"Ошибка подачи заявки о размещении: {e}")
        return {'success': False, 'error': str(e)}


def verify_post_placement(contract_id):
    """
    Автоматическая проверка размещения поста

    Args:
        contract_id: ID контракта

    Returns:
        dict: Результат проверки
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные контракта
        cursor.execute('''
                       SELECT c.*, or_resp.channel_username, o.title as offer_title, o.description
                       FROM contracts c
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                                JOIN offers o ON c.offer_id = o.id
                       WHERE c.id = ?
                         AND c.status = 'verification'
                       ''', (contract_id,))

        contract = cursor.fetchone()
        if not contract:
            return {'success': False, 'error': 'Контракт не найден'}

        # Проверяем пост через Telegram API
        verification_result = check_telegram_post(
            contract['channel_username'],
            contract['post_id'],
            contract['description']  # Ожидаемый контент
        )

        if verification_result['success']:
            # Пост найден и соответствует требованиям
            new_status = 'monitoring'
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?,
                               monitoring_started   = ?
                           WHERE id = ?
                           ''', (
                               new_status, True, verification_result['details'],
                               datetime.now().isoformat(), contract_id
                           ))

            # Запускаем мониторинг
            schedule_monitoring(contract_id)

            message = "✅ Размещение проверено и подтверждено! Начат мониторинг."

        else:
            # Пост не найден или не соответствует
            new_status = 'verification_failed'
            cursor.execute('''
                           UPDATE contracts
                           SET status               = ?,
                               verification_passed  = ?,
                               verification_details = ?
                           WHERE id = ?
                           ''', (
                               new_status, False, verification_result['error'], contract_id
                           ))

            message = f"❌ Проверка не пройдена: {verification_result['error']}"

        conn.commit()
        conn.close()

        # Отправляем уведомления
        send_contract_notification(contract_id, 'verification_result', {
            'status': new_status,
            'message': message
        })

        logger.info(f"Проверка контракта {contract_id}: {new_status}")

        return {
            'success': True,
            'status': new_status,
            'message': message,
            'details': verification_result
        }

    except Exception as e:
        logger.error(f"Ошибка проверки размещения: {e}")
        return {'success': False, 'error': str(e)}


def check_telegram_post(channel_username, post_id, expected_content=""):
    """
    Проверка существования и содержания поста в Telegram канале

    Args:
        channel_username: Username канала
        post_id: ID поста
        expected_content: Ожидаемый контент для проверки

    Returns:
        dict: Результат проверки
    """
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            return {'success': False, 'error': 'BOT_TOKEN не настроен'}

        # Формируем URL для получения поста
        url = f"https://api.telegram.org/bot{bot_token}/getChat"

        # Сначала проверяем доступ к каналу
        response = requests.get(url, params={
            'chat_id': f"@{channel_username}"
        }, timeout=10)

        if response.status_code != 200:
            return {'success': False, 'error': 'Канал недоступен или бот не добавлен в канал'}

        # Получаем конкретный пост
        message_url = f"https://api.telegram.org/bot{bot_token}/getChat"

        # Примечание: Для полной проверки поста нужны права администратора в канале
        # Здесь упрощенная проверка через публичные методы

        # Проверяем существование поста через веб-версию (если канал публичный)
        public_post_url = f"https://t.me/{channel_username}/{post_id}"

        try:
            post_response = requests.get(public_post_url, timeout=10)
            if post_response.status_code == 200:
                post_content = post_response.text

                # Простая проверка наличия ключевых слов из описания оффера
                if expected_content:
                    keywords = expected_content.lower().split()[:5]  # Первые 5 слов
                    content_lower = post_content.lower()

                    found_keywords = [kw for kw in keywords if kw in content_lower]
                    match_percentage = len(found_keywords) / len(keywords) * 100

                    if match_percentage < 50:  # Минимум 50% совпадений
                        return {
                            'success': False,
                            'error': f'Содержание поста не соответствует описанию оффера (совпадений: {match_percentage:.1f}%)'
                        }

                return {
                    'success': True,
                    'details': {
                        'post_found': True,
                        'url': public_post_url,
                        'verified_at': datetime.now().isoformat(),
                        'content_match': match_percentage if expected_content else 100
                    }
                }
            else:
                return {'success': False, 'error': 'Пост не найден по указанной ссылке'}

        except requests.RequestException:
            return {'success': False, 'error': 'Не удалось проверить пост (канал может быть приватным)'}

    except Exception as e:
        logger.error(f"Ошибка проверки Telegram поста: {e}")
        return {'success': False, 'error': f'Ошибка проверки: {str(e)}'}


def extract_post_data(post_url):
    """
    Извлечение данных из ссылки на пост Telegram

    Args:
        post_url: Ссылка на пост вида https://t.me/channel/123

    Returns:
        dict: Извлеченные данные
    """
    try:
        import re

        # Паттерн для ссылок Telegram
        pattern = r'https://t\.me/([^/]+)/(\d+)'
        match = re.match(pattern, post_url.strip())

        if not match:
            return {'success': False, 'error': 'Неверный формат ссылки. Ожидается: https://t.me/channel/123'}

        channel = match.group(1)
        post_id = match.group(2)

        return {
            'success': True,
            'channel': channel,
            'post_id': post_id,
            'post_date': datetime.now().isoformat()
        }

    except Exception as e:
        return {'success': False, 'error': f'Ошибка обработки ссылки: {str(e)}'}


def schedule_monitoring(contract_id):
    """
    Запуск мониторинга поста на время действия контракта

    Args:
        contract_id: ID контракта
    """
    try:
        # Здесь можно интегрировать с системой задач (Celery, APScheduler)
        # Пока делаем запись в БД для последующей проверки

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
                       INSERT INTO monitoring_tasks (contract_id, task_type, status, created_at, next_check)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (
                           contract_id, 'post_monitoring', 'active',
                           datetime.now().isoformat(),
                           (datetime.now() + timedelta(hours=24)).isoformat()  # Первая проверка через 24 часа
                       ))

        conn.commit()
        conn.close()

        logger.info(f"Запущен мониторинг для контракта {contract_id}")

    except Exception as e:
        logger.error(f"Ошибка запуска мониторинга: {e}")


def process_monitoring_tasks():
    """
    Обработка задач мониторинга (запускается по расписанию)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем активные задачи мониторинга
        cursor.execute('''
                       SELECT mt.*, c.post_url, c.monitoring_end, or_resp.channel_username
                       FROM monitoring_tasks mt
                                JOIN contracts c ON mt.contract_id = c.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE mt.status = 'active'
                         AND mt.next_check <= ?
                       ''', (datetime.now().isoformat(),))

        tasks = cursor.fetchall()

        for task in tasks:
            contract_id = task['contract_id']
            monitoring_end = datetime.fromisoformat(task['monitoring_end'])

            if datetime.now() > monitoring_end:
                # Мониторинг завершен - можно проводить оплату
                finalize_contract(contract_id)

                cursor.execute('''
                               UPDATE monitoring_tasks
                               SET status       = 'completed',
                                   completed_at = ?
                               WHERE id = ?
                               ''', (datetime.now().isoformat(), task['id']))

            else:
                # Промежуточная проверка
                if task['post_url']:
                    post_data = extract_post_data(task['post_url'])
                    if post_data['success']:
                        check_result = check_telegram_post(
                            task['channel_username'],
                            post_data['post_id']
                        )

                        if not check_result['success']:
                            # Пост удален или недоступен
                            cursor.execute('''
                                           UPDATE contracts
                                           SET status           = 'violation',
                                               violation_reason = ?
                                           WHERE id = ?
                                           ''', (check_result['error'], contract_id))

                            send_contract_notification(contract_id, 'violation', {
                                'reason': check_result['error']
                            })

                # Планируем следующую проверку
                next_check = datetime.now() + timedelta(hours=24)
                cursor.execute('''
                               UPDATE monitoring_tasks
                               SET next_check = ?,
                                   last_check = ?
                               WHERE id = ?
                               ''', (next_check.isoformat(), datetime.now().isoformat(), task['id']))

        conn.commit()
        conn.close()

        logger.info(f"Обработано {len(tasks)} задач мониторинга")

    except Exception as e:
        logger.error(f"Ошибка обработки мониторинга: {e}")


def finalize_contract(contract_id):
    """
    Завершение контракта и проведение оплаты

    Args:
        contract_id: ID контракта
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные контракта
        cursor.execute('''
                       SELECT c.*,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_adv.telegram_id as advertiser_telegram_id
                       FROM contracts c
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                       WHERE c.id = ?
                         AND c.status = 'monitoring'
                       ''', (contract_id,))

        contract = cursor.fetchone()
        if not contract:
            return {'success': False, 'error': 'Контракт не найден'}

        # Обновляем статус контракта
        cursor.execute('''
                       UPDATE contracts
                       SET status       = 'completed',
                           completed_at = ?
                       WHERE id = ?
                       ''', (datetime.now().isoformat(), contract_id))

        # Создаем запись о платеже
        payment_id = hashlib.md5(f"pay_{contract_id}_{time.time()}".encode()).hexdigest()[:16].upper()

        cursor.execute('''
                       INSERT INTO payments (id, contract_id, amount, status,
                                             publisher_id, advertiser_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', (
                           payment_id, contract_id, contract['price'], 'pending',
                           contract['publisher_id'], contract['advertiser_id'],
                           datetime.now().isoformat()
                       ))

        conn.commit()
        conn.close()

        # Отправляем уведомления об успешном завершении
        send_contract_notification(contract_id, 'completed', {
            'payment_id': payment_id,
            'amount': contract['price']
        })

        logger.info(f"Контракт {contract_id} завершен, создан платеж {payment_id}")

        return {'success': True, 'payment_id': payment_id}

    except Exception as e:
        logger.error(f"Ошибка завершения контракта: {e}")
        return {'success': False, 'error': str(e)}


# ДОБАВИТЬ в add_offer.py функцию для удаления неудачных контрактов

def delete_failed_contract(contract_id, telegram_user_id):
    """
    Удаление контракта со статусом verification_failed

    Args:
        contract_id: ID контракта для удаления
        telegram_user_id: Telegram ID пользователя, инициирующего удаление

    Returns:
        dict: Результат удаления
    """
    try:
        logger.info(f"🗑️ Удаление неудачного контракта {contract_id}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные контракта
        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_adv.first_name  as advertiser_name,
                              u_pub.first_name  as publisher_name
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        contract = cursor.fetchone()

        if not contract:
            return {'success': False, 'error': 'Контракт не найден'}

        # Проверяем права доступа
        if (contract['advertiser_telegram_id'] != telegram_user_id and
                contract['publisher_telegram_id'] != telegram_user_id):
            return {'success': False, 'error': 'Нет доступа к этому контракту'}

        # Проверяем статус
        if contract['status'] != 'verification_failed':
            return {
                'success': False,
                'error': f'Можно удалять только контракты со статусом "verification_failed". Текущий статус: {contract["status"]}'
            }

        offer_title = contract['offer_title']

        # Удаляем контракт
        cursor.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))
        deleted_rows = cursor.rowcount

        if deleted_rows == 0:
            return {'success': False, 'error': 'Контракт не был удален'}

        conn.commit()
        conn.close()

        # Отправляем уведомления участникам
        user_role = 'advertiser' if contract['advertiser_telegram_id'] == telegram_user_id else 'publisher'

        # Уведомление инициатору удаления
        if user_role == 'advertiser':
            message_self = f"""🗑️ <b>Контракт удален</b>

📋 <b>Оффер:</b> {offer_title}
👤 <b>Издатель:</b> {contract['publisher_name']}

Контракт удален из-за неудачной проверки размещения."""

            message_other = f"""🗑️ <b>Контракт удален рекламодателем</b>

📋 <b>Оффер:</b> {offer_title}
👤 <b>Рекламодатель:</b> {contract['advertiser_name']}

Контракт был удален из-за неудачной проверки размещения."""

            send_telegram_message(contract['advertiser_telegram_id'], message_self)
            send_telegram_message(contract['publisher_telegram_id'], message_other)

        else:  # publisher
            message_self = f"""🗑️ <b>Контракт удален</b>

📋 <b>Оффер:</b> {offer_title}
👤 <b>Рекламодатель:</b> {contract['advertiser_name']}

Контракт удален из-за неудачной проверки размещения."""

            message_other = f"""🗑️ <b>Контракт удален издателем</b>

📋 <b>Оффер:</b> {offer_title}
👤 <b>Издатель:</b> {contract['publisher_name']}

Контракт был удален из-за неудачной проверки размещения."""

            send_telegram_message(contract['publisher_telegram_id'], message_self)
            send_telegram_message(contract['advertiser_telegram_id'], message_other)

        logger.info(f"✅ Контракт {contract_id} успешно удален")

        return {
            'success': True,
            'message': f'Контракт "{offer_title}" успешно удален'
        }

    except Exception as e:
        logger.error(f"Ошибка удаления контракта: {e}")
        return {'success': False, 'error': str(e)}
# ДОБАВИТЬ в add_offer.py функции для работы с откликами

def create_offer_response_with_channel(offer_id, channel_id, user_id, telegram_user_id, message=""):
    """
    Создание отклика на оффер с выбранным каналом - ИСПРАВЛЕННАЯ ВЕРСИЯ
    Работает с существующей структурой БД БЕЗ column channel_id в offer_responses
    """
    try:
        logger.info(f"🎯 Создание отклика на оффер {offer_id} от канала {channel_id}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем оффер
        cursor.execute('SELECT * FROM offers WHERE id = ? AND status = "active"', (offer_id,))
        offer = cursor.fetchone()

        if not offer:
            conn.close()
            return {'success': False, 'error': 'Оффер не найден или неактивен'}

        # Проверяем канал
        cursor.execute('''
                       SELECT *
                       FROM channels
                       WHERE id = ?
                         AND owner_id = ?
                         AND is_verified = 1
                       ''', (channel_id, user_id))

        channel = cursor.fetchone()

        if not channel:
            conn.close()
            return {'success': False, 'error': 'Канал не найден или не верифицирован'}

        # ✅ ИСПРАВЛЕНИЕ: Проверяем дубликаты по channel_username вместо channel_id
        cursor.execute('''
                       SELECT id
                       FROM offer_responses
                       WHERE offer_id = ?
                         AND channel_username = ?
                         AND user_id = ?
                       ''', (offer_id, channel['username'], user_id))

        if cursor.fetchone():
            conn.close()
            return {'success': False, 'error': 'Вы уже откликались на этот оффер данным каналом'}

        # ✅ ИСПРАВЛЕНИЕ: Создаем отклик БЕЗ channel_id (используем существующую структуру БД)
        cursor.execute('''
                       INSERT INTO offer_responses (offer_id, user_id, channel_id, channel_title, channel_username,
                                                    channel_subscribers, message, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                       ''', (
                           offer_id,
                           user_id,
                           channel_id,  # ✅ ДОБАВЛЯЕМ channel_id
                           channel['title'],
                           channel['username'],
                           channel['subscriber_count'] or 0,
                           message
                       ))

        response_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # Отправляем уведомление рекламодателю
        try:
            send_offer_notification(offer_id, 'new_response', {
                'response_id': response_id,
                'channel_title': channel['title'],
                'channel_username': channel['username'],
                'channel_subscribers': channel['subscriber_count'] or 0,
                'responder_name': f"Пользователь {telegram_user_id}",
                'message': message
            })
        except Exception as notification_error:
            logger.warning(f"Ошибка отправки уведомления: {notification_error}")

        logger.info(f"✅ Отклик {response_id} создан успешно")

        return {
            'success': True,
            'response_id': response_id,
            'message': 'Отклик отправлен! Рекламодатель получил уведомление.'
        }

    except Exception as e:
        logger.error(f"Ошибка создания отклика: {e}")
        return {'success': False, 'error': str(e)}

def accept_offer_response(response_id, telegram_user_id):
    """
    Принятие отклика на оффер

    Args:
        response_id: ID отклика
        telegram_user_id: Telegram ID рекламодателя

    Returns:
        dict: Результат принятия отклика
    """
    try:
        logger.info(f"✅ Принятие отклика {response_id}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные отклика
        cursor.execute('''
                       SELECT or_resp.*,
                              o.title       as offer_title,
                              c.owner_id    as channel_owner_id,
                              u.telegram_id as channel_owner_telegram_id
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                                JOIN channels c ON or_resp.channel_id = c.id
                                JOIN users u ON c.owner_id = u.id
                       WHERE or_resp.id = ?
                       ''', (response_id,))

        response_data = cursor.fetchone()

        if not response_data:
            return {'success': False, 'error': 'Отклик не найден'}

        if response_data['status'] != 'pending':
            return {'success': False, 'error': 'Отклик уже обработан'}

        # Обновляем статус отклика
        cursor.execute('''
                       UPDATE offer_responses
                       SET status     = 'accepted',
                           updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?
                       ''', (response_id,))

        # Отклоняем остальные отклики на этот оффер
        cursor.execute('''
                       UPDATE offer_responses
                       SET status     = 'auto_rejected',
                           updated_at = CURRENT_TIMESTAMP
                       WHERE offer_id = ?
                         AND id != ? AND status = 'pending'
                       ''', (response_data['offer_id'], response_id))

        # Обновляем статус оффера
        cursor.execute('''
                       UPDATE offers
                       SET status     = 'in_progress',
                           updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?
                       ''', (response_data['offer_id'],))

        conn.commit()
        conn.close()

        # Отправляем уведомления
        send_response_notification(response_id, 'accepted')

        # Создаем контракт автоматически
        contract_details = {
            'placement_hours': 24,
            'monitoring_days': 7,
            'requirements': 'Согласно условиям оффера'
        }

        create_contract(response_id, contract_details)

        logger.info(f"✅ Отклик {response_id} принят, создан контракт")

        return {
            'success': True,
            'message': 'Отклик принят! Контракт создан автоматически.'
        }

    except Exception as e:
        logger.error(f"Ошибка принятия отклика: {e}")
        return {'success': False, 'error': str(e)}


def reject_offer_response(response_id, telegram_user_id, reason="Не подходящий канал"):
    """
    Отклонение отклика на оффер

    Args:
        response_id: ID отклика
        telegram_user_id: Telegram ID рекламодателя
        reason: Причина отклонения

    Returns:
        dict: Результат отклонения отклика
    """
    try:
        logger.info(f"❌ Отклонение отклика {response_id}")

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные отклика
        cursor.execute('''
                       SELECT or_resp.*, o.title as offer_title
                       FROM offer_responses or_resp
                                JOIN offers o ON or_resp.offer_id = o.id
                       WHERE or_resp.id = ?
                       ''', (response_id,))

        response_data = cursor.fetchone()

        if not response_data:
            return {'success': False, 'error': 'Отклик не найден'}

        if response_data['status'] != 'pending':
            return {'success': False, 'error': 'Отклик уже обработан'}

        # Обновляем статус отклика
        cursor.execute('''
                       UPDATE offer_responses
                       SET status        = 'rejected',
                           admin_message = ?,
                           updated_at    = CURRENT_TIMESTAMP
                       WHERE id = ?
                       ''', (reason, response_id))

        conn.commit()
        conn.close()

        # Отправляем уведомление владельцу канала
        send_response_notification(response_id, 'rejected')

        logger.info(f"❌ Отклик {response_id} отклонён")

        return {
            'success': True,
            'message': f'Отклик отклонён. Причина: {reason}'
        }

    except Exception as e:
        logger.error(f"Ошибка отклонения отклика: {e}")
        return {'success': False, 'error': str(e)}


def send_offer_notification(offer_id, notification_type, extra_data=None):
    """Отправка уведомлений по офферам"""
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if notification_type == 'new_response':
            # Уведомление рекламодателю о новом отклике
            response_id = extra_data.get('response_id')

            cursor.execute('''
                           SELECT o.title as offer_title, o.total_budget, u.telegram_id as author_telegram_id
                           FROM offers o
                                    JOIN users u ON o.user_id = u.id
                           WHERE o.id = ?
                           ''', (offer_id,))

            offer_data = cursor.fetchone()

            if offer_data:
                message = f"""🎯 <b>Новый отклик на ваш оффер!</b>

📋 <b>Оффер:</b> {offer_data['offer_title']}
💰 <b>Бюджет:</b> {offer_data['total_budget']} RUB

📺 <b>Канал откликнулся:</b>
• <b>Название:</b> {extra_data.get('channel_title')}
• <b>Username:</b> @{extra_data.get('channel_username')}
• <b>Подписчики:</b> {extra_data.get('channel_subscribers'):,}

👤 <b>Владелец:</b> {extra_data.get('responder_name', 'Пользователь')}

{f"💬 <b>Сообщение:</b> {extra_data.get('message')}" if extra_data.get('message') else ""}

🔔 Перейдите в приложение, чтобы рассмотреть отклик."""

                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📋 Посмотреть отклики",
                                "web_app": {
                                    "url": f"{AppConfig.WEBAPP_URL}/offers?tab=my-offers&offer_id={offer_id}"
                                }
                            }
                        ]
                    ]
                }

                send_telegram_message(offer_data['author_telegram_id'], message, keyboard)

        conn.close()

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления об оффере: {e}")


def send_response_notification(response_id, status):
    """Уведомление владельцу канала об изменении статуса отклика"""
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT o.title as offer_title, o.total_budget,
                   u_owner.telegram_id as channel_owner_telegram_id,
                   or_resp.admin_message, or_resp.channel_title
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            JOIN channels c ON or_resp.channel_id = c.id
            JOIN users u_owner ON c.owner_id = u_owner.id
            WHERE or_resp.id = ?
        ''', (response_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        if status == 'accepted':
            message = f"""✅ <b>Ваш отклик принят!</b>

📋 <b>Оффер:</b> {data['offer_title']}
💰 <b>Бюджет:</b> {data['total_budget']} RUB
📺 <b>Канал:</b> {data['channel_title']}

🎉 <b>Поздравляем!</b> Рекламодатель принял ваш отклик.

📋 <b>Что дальше?</b>
Контракт создан автоматически. Проверьте детали в приложении и следуйте инструкциям для размещения рекламы."""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Открыть контракты",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts"
                            }
                        }
                    ]
                ]
            }

        elif status == 'rejected':
            message = f"""❌ <b>Отклик отклонён</b>

📋 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}

К сожалению, рекламодатель выбрал другой канал.

{f"💬 <b>Причина:</b> {data['admin_message']}" if data['admin_message'] else ""}

💪 Не расстраивайтесь! Ищите другие подходящие офферы."""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔍 Найти офферы",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers"
                            }
                        }
                    ]
                ]
            }

        send_telegram_message(data['channel_owner_telegram_id'], message, keyboard)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления об отклике: {e}")


def send_telegram_message(chat_id, text, keyboard=None):
    """Отправка сообщения в Telegram с клавиатурой"""
    try:
        import requests
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        if keyboard:
            payload['reply_markup'] = keyboard

        response = requests.post(url, json=payload, timeout=10)

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False


# Flask маршруты для интеграции с основным приложением
def register_offer_routes(app):
    """Регистрация маршрутов для работы с офферами в Flask приложении"""

    if not FLASK_AVAILABLE:
        print("⚠️ Flask недоступен, маршруты офферов не зарегистрированы")
        return

    @app.route('/api/offers', methods=['POST'])
    def api_create_offer():
        """API для создания нового оффера"""
        try:
            data = request.get_json()
            print(f"DEBUG: Получены данные от клиента: {data}")
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400

            # Получаем user_id из заголовков или данных
            user_id = data.get('user_id') or request.headers.get('X-Telegram-User-Id')
            if not user_id:
                return jsonify({'success': False, 'error': 'User ID обязателен'}), 400

            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Некорректный User ID'}), 400

            # Создаем оффер
            result = add_offer(user_id, data)
            print(f"DEBUG: Результат add_offer: {result}")
            print(f"DEBUG: Результат add_offer: {result}")
            if result['success']:
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
            return jsonify({'success': True, 'offers': offers})
        except Exception as e:
            logger.error(f"Ошибка получения офферов: {e}")
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
            logger.error(f"Ошибка получения оффера: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500

    @app.route('/api/offers/available', methods=['GET'])
    def api_get_available_offers():
        """API для получения доступных офферов"""
        try:
            filters = {
                'category': request.args.get('category'),
                'min_budget': request.args.get('min_budget', type=float),
                'max_budget': request.args.get('max_budget', type=float),
                'limit': request.args.get('limit', 50, type=int)
            }

            # Убираем None значения
            filters = {k: v for k, v in filters.items() if v is not None}

            offers = get_available_offers(filters)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})

        except Exception as e:
            logger.error(f"Ошибка получения доступных офферов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500

    print("✅ Маршруты офферов зарегистрированы")


# Экспорт функций для использования в других модулях
__all__ = [
    'add_offer', 'get_user_offers', 'get_offer_by_id',
    'get_available_offers', 'cancel_offer_by_id',
    'update_offer_status_by_id', 'register_offer_routes'
]

if __name__ == '__main__':
    # Тестирование функций
    print("🧪 Тестирование модуля add_offer")

    # Тест создания оффера
    test_data = {
        'title': 'Тестовый оффер из модуля',
        'description': 'Описание тестового оффера',
        'content': 'Полное содержание тестового оффера',
        'price': 1500,
        'currency': 'RUB',
        'category': 'tech',
        'target_audience': 'IT специалисты',
        'requirements': 'Размещение в течение недели',
        'duration_days': 14
    }

    result = add_offer(373086959, test_data)
    print(f"Результат создания: {result}")

    if result['success']:
        # Тест получения офферов
        offers = get_user_offers(373086959)
        print(f"Найдено офферов: {len(offers)}")

        # Тест получения по ID
        if offers:
            offer_detail = get_offer_by_id(offers[0]['id'], True)
            print(f"Детали оффера: {offer_detail is not None}")