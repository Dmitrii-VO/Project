# offer_responses.py - Система откликов на офферы (продуктивная версия)
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

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


def get_suitable_offers_for_channel(channel_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получение подходящих офферов для канала

    Args:
        channel_id: ID канала в базе данных
        limit: Максимальное количество офферов

    Returns:
        List офферов, подходящих для канала
    """
    try:
        # Получаем информацию о канале
        channel = safe_execute_query('''
            SELECT c.*, u.telegram_id as owner_telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ?
        ''', (channel_id,), fetch_one=True)

        if not channel:
            return []

        # Получаем офферы, исключая уже отвеченные
        query = '''
            SELECT DISTINCT o.*, u.username as advertiser_username, u.first_name as advertiser_name,
                   u.telegram_id as advertiser_telegram_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.status = 'active'
            AND o.deadline > ?
            AND o.id NOT IN (
                SELECT offer_id FROM offer_responses 
                WHERE channel_id = ? AND status IN ('accepted', 'rejected')
            )
            AND o.created_by != (
                SELECT owner_id FROM channels WHERE id = ?
            )
            ORDER BY o.created_at DESC
            LIMIT ?
        '''

        offers = safe_execute_query(query, (
            datetime.now().date().isoformat(),
            channel_id,
            channel_id,
            limit
        ), fetch_all=True)

        # Обогащаем офферы дополнительной информацией
        for offer in offers:
            # Проверяем соответствие требованиям
            offer['suitability_score'] = calculate_suitability_score(offer, channel)
            offer['meets_requirements'] = check_channel_requirements(offer, channel)

            # Добавляем информацию о том, отвечал ли канал на этот оффер
            existing_response = safe_execute_query('''
                SELECT status, created_at FROM offer_responses
                WHERE offer_id = ? AND channel_id = ?
            ''', (offer['id'], channel_id), fetch_one=True)

            offer['existing_response'] = existing_response

        # Сортируем по соответствию
        offers.sort(key=lambda x: x['suitability_score'], reverse=True)

        return offers

    except Exception as e:
        logger.error(f"Ошибка получения подходящих офферов для канала {channel_id}: {e}")
        return []


def calculate_suitability_score(offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
    """Расчет соответствия оффера каналу (0-100)"""
    score = 50.0  # Базовый балл

    try:
        # Проверка количества подписчиков
        channel_subs = channel.get('subscriber_count', 0)

        # Проверка цены (выше цена - больше привлекательность)
        price = float(offer.get('price', 0))
        if price >= 5000:
            score += 15
        elif price >= 1000:
            score += 10
        elif price >= 500:
            score += 5

        # Проверка активности канала
        if channel.get('is_verified'):
            score += 10

        # Проверка целевой аудитории
        target_audience = offer.get('target_audience', '').lower()
        channel_desc = channel.get('description', '').lower()

        if target_audience and channel_desc:
            # Простое совпадение ключевых слов
            common_words = ['криптовалют', 'технолог', 'игр', 'развлечен', 'бизнес', 'образован']
            for word in common_words:
                if word in target_audience and word in channel_desc:
                    score += 5
                    break

        # Проверка требований
        requirements = offer.get('requirements', '').lower()
        if requirements:
            # Извлекаем минимальное количество подписчиков из требований
            import re
            min_subs_match = re.search(r'(\d+).*подписчик', requirements)
            if min_subs_match:
                min_subs = int(min_subs_match.group(1))
                if channel_subs >= min_subs:
                    score += 20
                else:
                    score -= 30

        # Ограничиваем диапазон 0-100
        score = max(0, min(100, score))

    except Exception as e:
        logger.error(f"Ошибка расчета соответствия: {e}")
        score = 50.0

    return round(score, 1)


def check_channel_requirements(offer: Dict[str, Any], channel: Dict[str, Any]) -> Dict[str, Any]:
    """Проверка соответствия канала требованиям оффера"""
    requirements = {
        'subscriber_count': True,
        'verification_status': True,
        'content_match': True
    }

    try:
        # Проверка требований из текстового поля
        requirements_text = offer.get('requirements', '').lower()
        channel_subs = channel.get('subscriber_count', 0)

        if requirements_text:
            # Извлекаем минимальное количество подписчиков
            import re
            min_subs_match = re.search(r'(\d+).*подписчик', requirements_text)
            if min_subs_match:
                min_subs = int(min_subs_match.group(1))
                requirements['subscriber_count'] = channel_subs >= min_subs

        # Проверка верификации если требуется
        if 'верифиц' in requirements_text or 'проверен' in requirements_text:
            requirements['verification_status'] = channel.get('is_verified', False)

        # Проверка тематического соответствия
        target_audience = offer.get('target_audience', '').lower()
        channel_desc = channel.get('description', '').lower()

        if target_audience and channel_desc:
            # Простая проверка совпадения ключевых слов
            common_words = ['криптовалют', 'технолог', 'игр', 'развлечен', 'бизнес', 'образован']
            content_match = any(word in target_audience and word in channel_desc for word in common_words)
            requirements['content_match'] = content_match

    except Exception as e:
        logger.error(f"Ошибка проверки требований: {e}")

    return requirements


def create_offer_response(channel_id: int, offer_id: int, response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Создание отклика на оффер

    Args:
        channel_id: ID канала
        offer_id: ID оффера
        response_data: Данные отклика

    Returns:
        Dict с результатом операции
    """
    try:
        # Валидация данных
        errors = validate_response_data(response_data)
        if errors:
            return {
                'success': False,
                'errors': errors
            }

        # Проверяем существование канала и оффера
        channel = safe_execute_query(
            'SELECT id, owner_id FROM channels WHERE id = ?',
            (channel_id,),
            fetch_one=True
        )

        if not channel:
            return {'success': False, 'error': 'Канал не найден'}

        offer = safe_execute_query(
            'SELECT id, created_by, status FROM offers WHERE id = ?',
            (offer_id,),
            fetch_one=True
        )

        if not offer:
            return {'success': False, 'error': 'Оффер не найден'}

        if offer['status'] != 'active':
            return {'success': False, 'error': 'Оффер неактивен'}

        # Проверяем, не отвечал ли уже канал на этот оффер
        existing_response = safe_execute_query('''
            SELECT id FROM offer_responses 
            WHERE channel_id = ? AND offer_id = ?
        ''', (channel_id, offer_id), fetch_one=True)

        if existing_response:
            return {'success': False, 'error': 'Вы уже отвечали на этот оффер'}

        # Подготовка данных
        status = response_data['status']  # 'interested', 'accepted', 'rejected'
        message = response_data.get('message', '').strip()
        counter_price = response_data.get('proposed_price')
        response_message = response_data.get('proposed_terms', '').strip()

        # Создание отклика в соответствии со схемой БД
        response_id = safe_execute_query('''
            INSERT INTO offer_responses (
                offer_id, user_id, status, response_message, counter_price,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            offer_id,
            channel['owner_id'],  # user_id владельца канала
            status,
            f"{message}\n\nУсловия: {response_message}".strip(),
            counter_price,
            datetime.now().isoformat()
        ))

        logger.info(f"Создан отклик {response_id} на оффер {offer_id} от канала {channel_id}")

        # Получаем созданный отклик для возврата
        created_response = safe_execute_query('''
            SELECT or_resp.*, o.title as offer_title, c.title as channel_title
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            LEFT JOIN channels c ON c.owner_id = or_resp.user_id AND c.id = ?
            WHERE or_resp.id = ?
        ''', (channel_id, response_id), fetch_one=True)

        # Отправляем уведомление рекламодателю (если система уведомлений доступна)
        try:
            send_response_notification(offer['created_by'], created_response)
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление: {e}")

        return {
            'success': True,
            'response_id': response_id,
            'response': created_response,
            'message': 'Отклик успешно отправлен'
        }

    except Exception as e:
        logger.error(f"Ошибка создания отклика: {e}")
        return {
            'success': False,
            'error': f'Ошибка создания отклика: {str(e)}'
        }


def validate_response_data(data: Dict[str, Any]) -> List[str]:
    """Валидация данных отклика"""
    errors = []

    # Проверка статуса
    status = data.get('status', '').strip()
    allowed_statuses = ['interested', 'accepted', 'rejected']
    if status not in allowed_statuses:
        errors.append('Некорректный статус отклика')

    # Проверка сообщения для заинтересованности и принятия
    message = data.get('message', '').strip()
    if status in ['interested', 'accepted'] and len(message) < 10:
        errors.append('Сообщение должно содержать минимум 10 символов')

    if message and len(message) > 1000:
        errors.append('Сообщение не должно превышать 1000 символов')

    # Проверка предложенной цены
    proposed_price = data.get('proposed_price')
    if proposed_price is not None:
        try:
            price = float(proposed_price)
            if price <= 0 or price > 1000000:
                errors.append('Предложенная цена должна быть от 1 до 1,000,000')
        except (ValueError, TypeError):
            errors.append('Некорректная предложенная цена')

    # Проверка условий
    proposed_terms = data.get('proposed_terms', '').strip()
    if proposed_terms and len(proposed_terms) > 500:
        errors.append('Условия не должны превышать 500 символов')

    return errors


def get_channel_responses(channel_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Получение откликов канала"""
    try:
        # Получаем ID владельца канала
        channel = safe_execute_query(
            'SELECT owner_id FROM channels WHERE id = ?',
            (channel_id,),
            fetch_one=True
        )

        if not channel:
            return []

        if status:
            query = '''
                SELECT or_resp.*, o.title as offer_title, o.price as offer_price,
                       o.currency as offer_currency, o.content as offer_content,
                       u.username as advertiser_username, u.first_name as advertiser_name
                FROM offer_responses or_resp
                JOIN offers o ON or_resp.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                WHERE or_resp.user_id = ? AND or_resp.status = ?
                ORDER BY or_resp.created_at DESC
            '''
            params = (channel['owner_id'], status)
        else:
            query = '''
                SELECT or_resp.*, o.title as offer_title, o.price as offer_price,
                       o.currency as offer_currency, o.content as offer_content,
                       u.username as advertiser_username, u.first_name as advertiser_name
                FROM offer_responses or_resp
                JOIN offers o ON or_resp.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                WHERE or_resp.user_id = ?
                ORDER BY or_resp.created_at DESC
            '''
            params = (channel['owner_id'],)

        responses = safe_execute_query(query, params, fetch_all=True)

        return responses

    except Exception as e:
        logger.error(f"Ошибка получения откликов канала: {e}")
        return []


def get_offer_responses(offer_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Получение откликов на оффер"""
    try:
        if status:
            query = '''
                SELECT or_resp.*, c.title as channel_title, c.username as channel_username,
                       c.subscriber_count, u.username as channel_owner_username
                FROM offer_responses or_resp
                JOIN users u ON or_resp.user_id = u.id
                LEFT JOIN channels c ON c.owner_id = or_resp.user_id
                WHERE or_resp.offer_id = ? AND or_resp.status = ?
                ORDER BY or_resp.created_at DESC
            '''
            params = (offer_id, status)
        else:
            query = '''
                SELECT or_resp.*, c.title as channel_title, c.username as channel_username,
                       c.subscriber_count, u.username as channel_owner_username
                FROM offer_responses or_resp
                JOIN users u ON or_resp.user_id = u.id
                LEFT JOIN channels c ON c.owner_id = or_resp.user_id
                WHERE or_resp.offer_id = ?
                ORDER BY or_resp.created_at DESC
            '''
            params = (offer_id,)

        responses = safe_execute_query(query, params, fetch_all=True)

        return responses

    except Exception as e:
        logger.error(f"Ошибка получения откликов на оффер: {e}")
        return []


def update_response_status(response_id: int, new_status: str, user_id: int = None) -> bool:
    """Обновление статуса отклика"""
    try:
        allowed_statuses = ['interested', 'accepted', 'rejected', 'completed', 'cancelled']
        if new_status not in allowed_statuses:
            return False

        if user_id:
            # Проверяем права пользователя - может изменять только свои отклики
            user = safe_execute_query(
                'SELECT id FROM users WHERE telegram_id = ?',
                (user_id,),
                fetch_one=True
            )

            if not user:
                return False

            response = safe_execute_query('''
                SELECT id FROM offer_responses
                WHERE id = ? AND user_id = ?
            ''', (response_id, user['id']), fetch_one=True)

            if not response:
                return False

        # Обновляем статус
        safe_execute_query('''
            UPDATE offer_responses 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (new_status, datetime.now().isoformat(), response_id))

        logger.info(f"Статус отклика {response_id} изменен на {new_status}")
        return True

    except Exception as e:
        logger.error(f"Ошибка обновления статуса отклика: {e}")
        return False


def send_response_notification(advertiser_user_id: int, response_data: Dict[str, Any]):
    """Отправка уведомления рекламодателю о новом отклике"""
    try:
        # Здесь будет интеграция с системой уведомлений
        # Пока просто логируем
        logger.info(
            f"Уведомление рекламодателю {advertiser_user_id}: новый отклик на оффер '{response_data.get('offer_title')}'")

        # TODO: Интеграция с Telegram Bot API для отправки уведомлений

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")


def get_response_statistics(channel_id: int = None, offer_id: int = None) -> Dict[str, Any]:
    """Получение статистики откликов"""
    try:
        stats = {}

        if channel_id:
            # Получаем ID владельца канала
            channel = safe_execute_query(
                'SELECT owner_id FROM channels WHERE id = ?',
                (channel_id,),
                fetch_one=True
            )

            if not channel:
                return {}

            # Статистика для канала
            total_responses = safe_execute_query('''
                SELECT COUNT(*) as count FROM offer_responses WHERE user_id = ?
            ''', (channel['owner_id'],), fetch_one=True)

            accepted_responses = safe_execute_query('''
                SELECT COUNT(*) as count FROM offer_responses 
                WHERE user_id = ? AND status = 'accepted'
            ''', (channel['owner_id'],), fetch_one=True)

            potential_earnings = safe_execute_query('''
                SELECT COALESCE(SUM(COALESCE(or_resp.counter_price, o.price)), 0) as total
                FROM offer_responses or_resp
                JOIN offers o ON or_resp.offer_id = o.id
                WHERE or_resp.user_id = ? AND or_resp.status = 'accepted'
            ''', (channel['owner_id'],), fetch_one=True)

            stats = {
                'total_responses': total_responses['count'] if total_responses else 0,
                'accepted_responses': accepted_responses['count'] if accepted_responses else 0,
                'potential_earnings': float(potential_earnings['total']) if potential_earnings else 0,
                'acceptance_rate': 0
            }

            if stats['total_responses'] > 0:
                stats['acceptance_rate'] = round((stats['accepted_responses'] / stats['total_responses']) * 100, 1)

        elif offer_id:
            # Статистика для оффера
            total_responses = safe_execute_query('''
                SELECT COUNT(*) as count FROM offer_responses WHERE offer_id = ?
            ''', (offer_id,), fetch_one=True)

            interested_responses = safe_execute_query('''
                SELECT COUNT(*) as count FROM offer_responses 
                WHERE offer_id = ? AND status = 'interested'
            ''', (offer_id,), fetch_one=True)

            accepted_responses = safe_execute_query('''
                SELECT COUNT(*) as count FROM offer_responses 
                WHERE offer_id = ? AND status = 'accepted'
            ''', (offer_id,), fetch_one=True)

            stats = {
                'total_responses': total_responses['count'] if total_responses else 0,
                'interested_responses': interested_responses['count'] if interested_responses else 0,
                'accepted_responses': accepted_responses['count'] if accepted_responses else 0,
                'response_rate': 0
            }

        return stats

    except Exception as e:
        logger.error(f"Ошибка получения статистики откликов: {e}")
        return {}


def get_all_available_offers_for_channel(channel_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Получение ВСЕХ доступных офферов для канала (без строгой фильтрации)

    Args:
        channel_id: ID канала в базе данных
        limit: Максимальное количество офферов

    Returns:
        List всех доступных офферов для канала
    """
    try:
        # Получаем информацию о канале
        channel = safe_execute_query('''
            SELECT c.*, u.telegram_id as owner_telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ?
        ''', (channel_id,), fetch_one=True)

        if not channel:
            return []

        # Получаем ВСЕ активные офферы, исключая только офферы самого владельца канала
        query = '''
            SELECT DISTINCT o.*, u.username as advertiser_username, u.first_name as advertiser_name,
                   u.telegram_id as advertiser_telegram_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.status = 'active'
            AND o.deadline > ?
            AND o.created_by != (
                SELECT owner_id FROM channels WHERE id = ?
            )
            ORDER BY o.created_at DESC
            LIMIT ?
        '''

        offers = safe_execute_query(query, (
            datetime.now().date().isoformat(),
            channel_id,
            limit
        ), fetch_all=True)

        # Обогащаем офферы дополнительной информацией
        for offer in offers:
            # Вычисляем соответствие (но не фильтруем по нему)
            offer['suitability_score'] = calculate_suitability_score(offer, channel)
            offer['meets_requirements'] = check_channel_requirements(offer, channel)

            # Проверяем, есть ли уже отклик от этого канала
            existing_response = safe_execute_query('''
                SELECT status, created_at, response_message FROM offer_responses
                WHERE offer_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (offer['id'], channel['owner_id']), fetch_one=True)

            offer['existing_response'] = existing_response

            # Добавляем статус "можно откликнуться"
            offer['can_respond'] = existing_response is None or existing_response['status'] not in ['accepted',
                                                                                                    'rejected']

        # Сортируем по релевантности: сначала новые, потом по соответствию
        offers.sort(key=lambda x: (
            x['existing_response'] is None,  # Сначала те, на которые не отвечали
            x['suitability_score'],  # Потом по соответствию
            x['created_at']  # Потом по дате создания
        ), reverse=True)

        return offers

    except Exception as e:
        logger.error(f"Ошибка получения всех доступных офферов для канала {channel_id}: {e}")
        return []


def get_offers_statistics() -> Dict[str, Any]:
    """Получение общей статистики по офферам"""
    try:
        stats = {}

        # Общее количество активных офферов
        active_offers = safe_execute_query('''
            SELECT COUNT(*) as count FROM offers WHERE status = 'active' AND deadline > ?
        ''', (datetime.now().date().isoformat(),), fetch_one=True)
        stats['active_offers'] = active_offers['count'] if active_offers else 0

        # Общий бюджет активных офферов
        total_budget = safe_execute_query('''
            SELECT SUM(price) as total FROM offers WHERE status = 'active' AND deadline > ?
        ''', (datetime.now().date().isoformat(),), fetch_one=True)
        stats['total_budget'] = total_budget['total'] if total_budget and total_budget['total'] else 0

        # Средняя цена оффера
        avg_price = safe_execute_query('''
            SELECT AVG(price) as avg FROM offers WHERE status = 'active' AND deadline > ?
        ''', (datetime.now().date().isoformat(),), fetch_one=True)
        stats['average_price'] = avg_price['avg'] if avg_price and avg_price['avg'] else 0

        # Общее количество откликов
        total_responses = safe_execute_query('''
            SELECT COUNT(*) as count FROM offer_responses
        ''', fetch_one=True)
        stats['total_responses'] = total_responses['count'] if total_responses else 0

        return stats

    except Exception as e:
        logger.error(f"Ошибка получения статистики офферов: {e}")
        return {}