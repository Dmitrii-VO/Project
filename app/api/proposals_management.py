#!/usr/bin/env python3
"""
API для работы с предложениями
Endpoints для владельцев каналов
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, current_app
from app.models.database import get_user_id_from_request, execute_db_query
from app.config.telegram_config import AppConfig
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
proposals_management_bp = Blueprint('proposals_management', __name__, url_prefix='/api/proposals')

# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================

def get_db_connection():
    """Получение соединения с базой данных"""
    try:
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        return None

def validate_proposal_ownership(proposal_id: int, user_id: int) -> bool:
    """Проверка принадлежности предложения владельцу канала"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT op.id 
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            WHERE op.id = ? AND c.owner_id = ?
        """, (proposal_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"Ошибка проверки владения предложением: {e}")
        return False

def get_proposal_details(proposal_id: int) -> Optional[Dict]:
    """Получение деталей предложения"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                op.id, op.offer_id, op.channel_id, op.status,
                op.created_at, op.responded_at, op.rejection_reason,
                op.expires_at, op.notified_at, op.reminder_sent_at,
                -- Информация об оффере
                o.budget_total as offer_budget, o.content as offer_content,
                o.requirements as placement_requirements, o.category as contact_info,
                o.duration_days as placement_duration, o.expected_placement_duration,
                o.category as offer_category, o.target_audience,
                -- Информация о канале
                c.title as channel_title, c.username as channel_username,
                c.subscriber_count, c.category as channel_category,
                -- Информация о создателе оффера
                u.username as advertiser_username, u.first_name as advertiser_first_name,
                u.last_name as advertiser_last_name, u.telegram_id as advertiser_telegram_id
            FROM offer_proposals op
            JOIN offers o ON op.offer_id = o.id
            JOIN channels c ON op.channel_id = c.id
            JOIN users u ON o.created_by = u.id
            WHERE op.id = ?
        """, (proposal_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"Ошибка получения деталей предложения: {e}")
        return None

def get_user_channels(user_id: int) -> List[Dict]:
    """Получение каналов пользователя"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, username, subscriber_count, category, is_verified
            FROM channels 
            WHERE owner_id = ? AND is_active = 1
            ORDER BY subscriber_count DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Ошибка получения каналов пользователя: {e}")
        return []

def update_proposal_status(proposal_id: int, new_status: str, rejection_reason: str = None) -> bool:
    """Обновление статуса предложения"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        if rejection_reason:
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = ?, responded_at = CURRENT_TIMESTAMP, rejection_reason = ?
                WHERE id = ?
            """, (new_status, rejection_reason, proposal_id))
        else:
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = ?, responded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, proposal_id))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка обновления статуса предложения: {e}")
        return False

def create_placement_record(proposal_id: int, expected_duration: int = 7) -> Optional[int]:
    """Создание записи о размещении"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offer_placements (
                proposal_id, expected_duration, status, created_at
            ) VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (proposal_id, expected_duration))
        
        placement_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return placement_id
    except Exception as e:
        logger.error(f"Ошибка создания записи о размещении: {e}")
        return None

def send_notification_to_advertiser(proposal_id: int, action: str, data: any) -> bool:
    """
    УЛУЧШЕННАЯ функция отправки уведомлений рекламодателю
    
    Args:
        proposal_id: ID предложения
        action: accepted/rejected/placement_submitted
        data: dict или str с дополнительными данными
    """
    try:
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            logger.error(f"Не найдено предложение {proposal_id} для уведомления")
            return False
        
        notification_text = ""
        notification_title = ""
        
        if action == 'accepted':
            notification_title = "✅ Предложение принято!"
            notification_text = f"📢 <b>Канал:</b> {proposal.get('channel_title', 'Неизвестный канал')}\n"
            notification_text += f"💰 <b>Оффер:</b> {proposal.get('offer_title', 'Неизвестный оффер')}\n"
            
            # Добавляем информацию о дате размещения
            if isinstance(data, dict) and data.get('scheduled_date'):
                try:
                    scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00'))
                    formatted_date = scheduled_date.strftime("%d.%m.%Y в %H:%M")
                    notification_text += f"📅 <b>Планируемое размещение:</b> {formatted_date}\n"
                except:
                    notification_text += f"📅 <b>Планируемое размещение:</b> {data['scheduled_date']}\n"
            else:
                notification_text += f"📅 <b>Размещение:</b> в течение 24 часов\n"
            
            if isinstance(data, dict) and data.get('message'):
                notification_text += f"💬 <b>Сообщение:</b> {data['message']}\n"
            
            notification_text += f"\n🎯 Ожидайте уведомления о размещении!"
        
        elif action == 'rejected':
            notification_title = "❌ Предложение отклонено"
            notification_text = f"📢 <b>Канал:</b> {proposal.get('channel_title', 'Неизвестный канал')}\n"
            notification_text += f"💰 <b>Оффер:</b> {proposal.get('offer_title', 'Неизвестный оффер')}\n"
            
            if isinstance(data, dict):
                # Добавляем категорию причины
                reason_category = data.get('reason_category', 'other')
                category_names = {
                    'price': '💰 Цена',
                    'topic': '📋 Тематика', 
                    'timing': '⏰ Сроки',
                    'technical': '⚙️ Технические требования',
                    'content': '📝 Контент',
                    'other': '📌 Другое'
                }
                notification_text += f"🔍 <b>Причина:</b> {category_names.get(reason_category, 'Другое')}\n"
                
                # Добавляем текстовую причину
                if data.get('reason'):
                    notification_text += f"📝 <b>Детали:</b> {data['reason']}\n"
                
                # Добавляем предложенную цену
                if data.get('suggested_price'):
                    notification_text += f"💡 <b>Предложенная цена:</b> {data['suggested_price']} руб.\n"
                
                # Добавляем дополнительные детали
                if data.get('custom_reason'):
                    notification_text += f"📋 <b>Дополнительно:</b> {data['custom_reason']}\n"
            else:
                notification_text += f"📝 <b>Причина:</b> {data}\n"
            
            notification_text += f"\n💡 Вы можете создать новый оффер с учетом замечаний"
        
        elif action == 'placement_submitted':
            notification_title = "📤 Пост размещен!"
            notification_text = f"📢 <b>Канал:</b> {proposal.get('channel_title', 'Неизвестный канал')}\n"
            notification_text += f"💰 <b>Оффер:</b> {proposal.get('offer_title', 'Неизвестный оффер')}\n"
            notification_text += f"🔗 <b>Ссылка:</b> {data}\n"
            notification_text += f"\n⏱️ Начался мониторинг размещения"
        
        else:
            logger.warning(f"Неизвестный тип уведомления: {action}")
            return False
        
        # Сохраняем уведомление в базе данных
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notification_logs (
                        user_id, telegram_id, notification_type, title, message, 
                        status, created_at, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proposal.get('advertiser_user_id', 1),  # fallback
                    proposal.get('advertiser_telegram_id', 0),  # fallback
                    f'proposal_{action}',
                    notification_title,
                    notification_text,
                    'pending',
                    datetime.now().isoformat(),
                    json.dumps({
                        'proposal_id': proposal_id,
                        'action': action,
                        'data': data
                    })
                ))
                conn.commit()
                logger.info(f"Уведомление сохранено для пользователя {proposal.get('advertiser_telegram_id', 'unknown')}")
            except Exception as e:
                logger.error(f"Ошибка сохранения уведомления: {e}")
            finally:
                conn.close()
        
        # TODO: Здесь добавить реальную отправку через Telegram Bot API
        # Пока что логируем
        logger.info(f"📧 Уведомление рекламодателю (ID: {proposal.get('advertiser_telegram_id', 'unknown')})")
        logger.info(f"📧 Заголовок: {notification_title}")
        logger.info(f"📧 Текст: {notification_text}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления рекламодателю: {e}")
        return False

# ================================================================
# API ENDPOINTS
# ================================================================

@proposals_management_bp.route('/incoming', methods=['GET'])
def get_incoming_proposals():
    """
    Получение входящих предложений для владельца канала
    
    GET /api/proposals/incoming
    
    Query Parameters:
    - status: фильтр по статусу (sent, accepted, rejected, expired)
    - channel_id: фильтр по каналу
    - limit: количество результатов (по умолчанию 50)
    - offset: смещение для пагинации (по умолчанию 0)
    """
    try:
        # 1. Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # 2. Получаем параметры фильтрации
        status_filter = request.args.get('status')
        channel_id_filter = request.args.get('channel_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 3. Ограничиваем лимит на количество результатов
        limit = min(limit, 100)
        
        # 4. Получаем каналы пользователя
        user_channels = get_user_channels(user_id)
        if not user_channels:
            return jsonify({
                'success': True,
                'total_proposals': 0,
                'proposals': [],
                'user_channels': []
            }), 200
        
        # 5. Формируем запрос
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # 6. Базовый запрос
        where_conditions = ["c.owner_id = ?"]
        params = [user_id]
        
        # 7. Добавляем фильтры
   #    if status_filter:
   #         where_conditions.append("op.status = ?")
   #         params.append(status_filter)
        
        if channel_id_filter:
            where_conditions.append("op.channel_id = ?")
            params.append(channel_id_filter)
        
        # 8. Формируем WHERE-условие
        where_clause = " AND ".join(where_conditions)
        
        # 9. Получаем общее количество
        count_query = f"""
            SELECT COUNT(*) as total
            FROM offer_proposals op
            JOIN channels c ON op.channel_id = c.id
            JOIN offers o ON op.offer_id = o.id
            WHERE {where_clause}
        """
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # 10. Получаем данные с пагинацией
        main_query = f"""
            SELECT 
                op.id as proposal_id, op.status as proposal_status,
                op.created_at as proposal_created_at, op.expires_at,
                o.id, o.title, o.description, 
                COALESCE(o.budget_total, o.price, 0) as price,
                o.currency, o.target_audience,
                o.min_subscribers, o.max_subscribers,
                u.username as creator_name, u.first_name,
                c.title as channel_title, c.username as channel_username,
                c.subscriber_count,
                (op.expires_at < CURRENT_TIMESTAMP) as is_expired
            FROM offer_proposals op
            JOIN offers o ON op.offer_id = o.id
            JOIN channels c ON op.channel_id = c.id
            JOIN users u ON o.created_by = u.id
            WHERE {where_clause}
            ORDER BY op.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(main_query, params + [limit, offset])
        proposals = cursor.fetchall()
        conn.close()
        
        # 11. Формируем результат
        proposals_list = []
        for proposal in proposals:
            proposal_data = dict(proposal)
            
            # Добавляем дополнительную информацию
            proposal_data['is_expired'] = bool(proposal_data['is_expired'])
            proposal_data['can_respond'] = (
                proposal_data['proposal_status'] == 'sent' and 
                not proposal_data['is_expired']
            )
            
            # Рассчитываем предполагаемый доход
            if (
                proposal_data['price'] is not None and 
                proposal_data['subscriber_count'] is not None
            ):
                estimated_payment = min(
                    proposal_data['price'],
                    proposal_data['subscriber_count'] * 0.01
                )
                proposal_data['estimated_payment'] = round(estimated_payment, 2)
            else:
                proposal_data['estimated_payment'] = 0

            
            proposals_list.append(proposal_data)


        # 12. Формируем ответ
        response = {
            'success': True,
            'total_proposals': total_count,
            'proposals': proposals_list,
            'user_channels': user_channels,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'status': status_filter,
                'channel_id': channel_id_filter
            }
        }
        
        logger.info(f"Получены входящие предложения для пользователя {user_id}: {len(proposals_list)} из {total_count}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения входящих предложений: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/accept', methods=['POST'])
def accept_proposal(proposal_id: int):
    """
    Принятие предложения с возможностью указания даты размещения
    
    POST /api/proposals/{proposal_id}/accept
    
    Request Body:
    {
        "message": "Дополнительное сообщение (опционально)",
        "scheduled_date": "2025-07-15T14:30:00",  # НОВОЕ ПОЛЕ
        "timezone": "Europe/Moscow"  # НОВОЕ ПОЛЕ (опционально)
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden', 
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем данные из запроса
        data = request.get_json() or {}
        message = data.get('message', '')
        scheduled_date = data.get('scheduled_date')  # НОВОЕ ПОЛЕ
        timezone = data.get('timezone', 'Europe/Moscow')  # НОВОЕ ПОЛЕ
        
        # Валидация даты размещения
        placement_datetime = None
        if scheduled_date:
            try:
                from datetime import datetime
                
                # Парсим дату
                if isinstance(scheduled_date, str):
                    # Поддерживаем разные форматы даты
                    try:
                        placement_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                    except:
                        placement_datetime = datetime.strptime(scheduled_date, '%Y-%m-%dT%H:%M:%S')
                
                # Проверяем что дата в будущем
                if placement_datetime and placement_datetime <= datetime.now():
                    return jsonify({
                        'error': 'Bad Request',
                        'message': 'Дата размещения должна быть в будущем'
                    }), 400
                
                # Проверяем что дата не слишком далеко (например, не больше 30 дней)
                max_future_date = datetime.now() + timedelta(days=30)
                if placement_datetime and placement_datetime > max_future_date:
                    return jsonify({
                        'error': 'Bad Request',
                        'message': 'Дата размещения не может быть больше чем через 30 дней'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Ошибка парсинга даты: {e}")
                return jsonify({
                    'error': 'Bad Request',
                    'message': 'Неверный формат даты. Используйте формат: 2025-07-15T14:30:00'
                }), 400
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'sent':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Предложение уже обработано (статус: {proposal["status"]})'
            }), 400
        
        # Формируем сообщение с датой
        full_message = message
        if placement_datetime:
            full_message += f"\n📅 Планируемое размещение: {placement_datetime.strftime('%d.%m.%Y в %H:%M')}"
        
        # Обновляем статус в базе данных
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Обновляем offer_proposals (используем существующие поля)
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = 'accepted',
                    responded_at = ?,
                    response_message = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                full_message,
                proposal_id
            ))
            
            # Также обновляем offer_channel_targets если существует (используем proposed_date)
            cursor.execute("""
                UPDATE offer_channel_targets 
                SET status = 'accepted',
                    response_message = ?,
                    proposed_date = ?,
                    updated_at = ?
                WHERE offer_id = ? AND channel_id = ?
            """, (
                full_message,
                placement_datetime.date() if placement_datetime else None,
                datetime.now().isoformat(),
                proposal['offer_id'],
                proposal['channel_id']
            ))
            
            conn.commit()
            
            # Генерируем placement_id для отслеживания размещения
            placement_id = f"PLACEMENT_{proposal_id}_{int(datetime.now().timestamp())}"
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка обновления базы данных: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка сохранения данных'
            }), 500
        finally:
            conn.close()
        
        # Отправляем уведомление рекламодателю
        notification_data = {
            'scheduled_date': placement_datetime.isoformat() if placement_datetime else None,
            'message': message,
            'timezone': timezone
        }
        send_notification_to_advertiser(proposal_id, 'accepted', notification_data)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'placement_id': placement_id,
            'offer_title': proposal.get('offer_title', 'Неизвестный оффер'),
            'channel_title': proposal.get('channel_title', 'Неизвестный канал'),
            'scheduled_date': placement_datetime.isoformat() if placement_datetime else None,
            'message': 'Предложение принято',
            'next_steps': []
        }
        
        # Формируем следующие шаги
        if placement_datetime:
            response['next_steps'] = [
                f'Разместите пост {placement_datetime.strftime("%d.%m.%Y в %H:%M")}',
                'Подтвердите размещение через API с ссылкой на пост',
                'Система автоматически проверит размещение'
            ]
        else:
            response['next_steps'] = [
                'Разместите пост в течение 24 часов',
                'Подтвердите размещение через API с ссылкой на пост',
                'Ожидайте автоматической проверки'
            ]
        
        logger.info(f"Предложение {proposal_id} принято пользователем {user_id} на {placement_datetime}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка принятия предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/reject', methods=['POST'])
def reject_proposal(proposal_id: int):
    """
    Отклонение предложения с детальными причинами
    
    POST /api/proposals/{proposal_id}/reject
    
    Request Body:
    {
        "reason": "Текстовая причина отклонения (обязательно)",
        "reason_category": "price",  # НОВОЕ ПОЛЕ: price/topic/timing/other/technical
        "custom_reason": "Детальное объяснение",  # НОВОЕ ПОЛЕ (опционально)
        "suggested_price": 1500.00  # НОВОЕ ПОЛЕ (опционально) - предложить другую цену
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем данные из запроса
        data = request.get_json() or {}
        reason = data.get('reason', '').strip()
        reason_category = data.get('reason_category', 'other')  # НОВОЕ ПОЛЕ
        custom_reason = data.get('custom_reason', '').strip()  # НОВОЕ ПОЛЕ
        suggested_price = data.get('suggested_price')  # НОВОЕ ПОЛЕ
        
        # Валидация данных
        if not reason:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Необходимо указать причину отклонения'
            }), 400
        
        # Валидация категории причины
        valid_categories = ['price', 'topic', 'timing', 'technical', 'content', 'other']
        if reason_category not in valid_categories:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Неверная категория причины. Доступные: {", ".join(valid_categories)}'
            }), 400
        
        # Валидация предложенной цены
        if suggested_price is not None:
            try:
                suggested_price = float(suggested_price)
                if suggested_price <= 0:
                    return jsonify({
                        'error': 'Bad Request',
                        'message': 'Предложенная цена должна быть больше 0'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': 'Bad Request',
                    'message': 'Неверный формат предложенной цены'
                }), 400
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'sent':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Предложение уже обработано (статус: {proposal["status"]})'
            }), 400
        
        # Формируем полное сообщение с причиной (используем существующие поля БД)
        category_names = {
            'price': '💰 Цена',
            'topic': '📋 Тематика', 
            'timing': '⏰ Сроки',
            'technical': '⚙️ Технические требования',
            'content': '📝 Контент',
            'other': '📌 Другое'
        }
        
        full_reason_message = f"{category_names.get(reason_category, 'Другое')}: {reason}"
        
        if custom_reason:
            full_reason_message += f"\n\nДетали: {custom_reason}"
        if suggested_price:
            full_reason_message += f"\n\nПредложенная цена: {suggested_price} руб."
        
        # Обновляем статус в базе данных (используем существующие поля)
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        try:
            cursor = conn.cursor()
            
            # Обновляем offer_proposals (используем существующие поля)
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = 'rejected',
                    responded_at = ?,
                    rejection_reason = ?,
                    response_message = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                full_reason_message,  # В rejection_reason
                reason,  # Краткая причина в response_message
                proposal_id
            ))
            
            # Также обновляем offer_channel_targets если существует
            cursor.execute("""
                UPDATE offer_channel_targets 
                SET status = 'rejected',
                    response_message = ?,
                    updated_at = ?
                WHERE offer_id = ? AND channel_id = ?
            """, (
                full_reason_message,
                datetime.now().isoformat(),
                proposal['offer_id'],
                proposal['channel_id']
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка обновления базы данных при отклонении: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка сохранения данных'
            }), 500
        finally:
            conn.close()
        
        # Отправляем уведомление рекламодателю
        notification_data = {
            'reason': reason,
            'reason_category': reason_category,
            'custom_reason': custom_reason,
            'suggested_price': suggested_price
        }
        send_notification_to_advertiser(proposal_id, 'rejected', notification_data)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'offer_title': proposal.get('offer_title', 'Неизвестный оффер'),
            'channel_title': proposal.get('channel_title', 'Неизвестный канал'),
            'reason_category': reason_category,
            'message': 'Предложение отклонено',
            'suggestions': []
        }
        
        # Добавляем предложения по улучшению
        if reason_category == 'price':
            response['suggestions'] = [
                'Рассмотрите увеличение бюджета',
                'Попробуйте найти каналы с меньшей аудиторией',
                'Измените условия сотрудничества'
            ]
        elif reason_category == 'topic':
            response['suggestions'] = [
                'Уточните тематику оффера',
                'Найдите каналы соответствующей тематики',
                'Адаптируйте контент под аудиторию канала'
            ]
        elif reason_category == 'timing':
            response['suggestions'] = [
                'Предложите более гибкие сроки размещения',
                'Уточните оптимальное время для размещения',
                'Рассмотрите отложенное размещение'
            ]
        
        logger.info(f"Предложение {proposal_id} отклонено пользователем {user_id}. Причина: {reason_category}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка отклонения предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

@proposals_management_bp.route('/<int:proposal_id>/submit-placement', methods=['POST'])
def submit_placement(proposal_id: int):
    """
    Подтверждение размещения поста
    
    POST /api/proposals/{proposal_id}/submit-placement
    
    Request Body:
    {
        "post_url": "https://t.me/channel_username/123",
        "placement_notes": "Дополнительные заметки (опционально)"
    }
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Проверяем статус предложения
        if proposal['status'] != 'accepted':
            return jsonify({
                'error': 'Bad Request',
                'message': f'Нельзя подтвердить размещение для предложения со статусом {proposal["status"]}'
            }), 400
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Отсутствует тело запроса'
            }), 400
        
        post_url = data.get('post_url', '').strip()
        placement_notes = data.get('placement_notes', '').strip()
        
        # Валидация URL поста
        if not post_url:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Необходимо указать URL поста'
            }), 400
        
        if not post_url.startswith('https://t.me/'):
            return jsonify({
                'error': 'Bad Request',
                'message': 'URL поста должен начинаться с https://t.me/'
            }), 400
        
        # Обновляем запись о размещении
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        try:
            # Получаем ID размещения
            cursor.execute("""
                SELECT id FROM offer_placements 
                WHERE proposal_id = ? AND status = 'pending'
            """, (proposal_id,))
            
            placement = cursor.fetchone()
            if not placement:
                conn.close()
                return jsonify({
                    'error': 'Not Found',
                    'message': 'Запись о размещении не найдена'
                }), 404
            
            placement_id = placement['id']
            
            # Обновляем запись о размещении
            cursor.execute("""
                UPDATE offer_placements 
                SET post_url = ?, placement_start = CURRENT_TIMESTAMP,
                    status = 'placed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (post_url, placement_id))
            
            # Создаем первую запись проверки
            cursor.execute("""
                INSERT INTO placement_checks (
                    placement_id, check_time, post_exists, 
                    views_count, check_status, response_data
                ) VALUES (?, CURRENT_TIMESTAMP, 1, 0, 'success', ?)
            """, (placement_id, json.dumps({
                'post_url': post_url,
                'placement_notes': placement_notes,
                'submitted_by': user_id,
                'submitted_at': datetime.now().isoformat()
            })))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка обновления размещения: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка обновления размещения'
            }), 500
        
        finally:
            conn.close()
        
        # Отправляем уведомление рекламодателю
        send_notification_to_advertiser(proposal_id, 'placement_submitted', post_url)
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal_id': proposal_id,
            'placement_id': placement_id,
            'post_url': post_url,
            'offer_title': proposal['offer_title'],
            'channel_title': proposal['channel_title'],
            'message': 'Размещение подтверждено',
            'next_steps': [
                'Пост будет автоматически проверен в течение часа',
                'Система будет отслеживать пост до завершения кампании',
                'Вы получите уведомление о завершении'
            ]
        }
        
        logger.info(f"Размещение подтверждено для предложения {proposal_id}: {post_url}")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения размещения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS
# ================================================================

@proposals_management_bp.route('/<int:proposal_id>/details', methods=['GET'])
def get_proposal_details_endpoint(proposal_id: int):
    """
    Получение детальной информации о предложении
    
    GET /api/proposals/{proposal_id}/details
    """
    try:
        # Получаем ID пользователя из запроса
        user_id = get_user_id_from_request()
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Требуется авторизация'
            }), 401
        
        # Проверяем принадлежность предложения
        if not validate_proposal_ownership(proposal_id, user_id):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Предложение не принадлежит пользователю'
            }), 403
        
        # Получаем детали предложения
        proposal = get_proposal_details(proposal_id)
        if not proposal:
            return jsonify({
                'error': 'Not Found',
                'message': 'Предложение не найдено'
            }), 404
        
        # Получаем информацию о размещении
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'Ошибка подключения к базе данных'
            }), 500
        
        cursor = conn.cursor()
        
        # Получаем данные о размещении
        cursor.execute("""
            SELECT 
                id, post_url, placement_start, placement_end,
                expected_duration, status, final_views_count,
                created_at, updated_at
            FROM offer_placements
            WHERE proposal_id = ?
        """, (proposal_id,))
        
        placement = cursor.fetchone()
        
        # Получаем историю проверок
        if placement:
            cursor.execute("""
                SELECT 
                    check_time, post_exists, views_count, 
                    check_status, error_message
                FROM placement_checks
                WHERE placement_id = ?
                ORDER BY check_time DESC
                LIMIT 10
            """, (placement['id'],))
            
            checks = cursor.fetchall()
        else:
            checks = []
        
        conn.close()
        
        # Формируем ответ
        response = {
            'success': True,
            'proposal': dict(proposal),
            'placement': dict(placement) if placement else None,
            'recent_checks': [dict(check) for check in checks]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей предложения: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Внутренняя ошибка сервера'
        }), 500

# ================================================================
# ОБРАБОТЧИКИ ОШИБОК
# ================================================================

@proposals_management_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'Ресурс не найден'
    }), 404

@proposals_management_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Внутренняя ошибка сервера'
    }), 500