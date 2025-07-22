"""
API endpoints for offer moderation and status management
"""
from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.config.telegram_config import AppConfig
from datetime import datetime

# Константа администратора
ADMIN_USER_ID = 373086959

offers_moderation_bp = Blueprint('offers_moderation', __name__, url_prefix='/api/offers_moderation')

# Создаем экземпляр сервиса авторизации
auth_service = AuthService()

def get_telegram_user_id():
    """Получение текущего Telegram User ID"""
    return auth_service.get_current_user_id()

def is_admin():
    """Проверка прав администратора"""
    try:
        user_id = get_telegram_user_id()
        return str(user_id) == str(ADMIN_USER_ID)
    except:
        return False

def get_db_connection():
    """Получение соединения с базой данных"""
    import sqlite3
    
    print(f"🔍 Connecting to database: {AppConfig.DATABASE_PATH}")
    
    conn = sqlite3.connect(AppConfig.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Для удобного доступа к столбцам по имени
    return conn

def send_telegram_notification(user_id, message, notification_type="general"):
    """Отправка уведомления в Telegram"""
    try:
        from app.telegram.telegram_notifications import TelegramNotificationService, NotificationData, NotificationType
        
        print(f"🔔 Отправка уведомления пользователю {user_id}: {message}")
        
        service = TelegramNotificationService()
        
        # Создаем уведомление
        notification = NotificationData(
            user_id=0,  # Будет заполнено автоматически
            telegram_id=int(user_id),
            notification_type=NotificationType.PROPOSAL_ACCEPTED if "одобрен" in message.lower() else 
                            NotificationType.PROPOSAL_REJECTED if "отклонен" in message.lower() else
                            NotificationType.NEW_PROPOSAL,
            title="Система модерации офферов",
            message=message,
            data={'user_id': user_id, 'type': notification_type},
            priority=2
        )
        
        result = service.send_notification(notification)
        print(f"✅ Результат отправки: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False

@offers_moderation_bp.route('/offers', methods=['GET'])
def get_offers_for_moderation():
    """Получение офферов для модерации (только для админа)"""
    current_user = get_telegram_user_id()
    print(f"🔍 Admin check for user: {current_user}")
    
    if not is_admin():
        print(f"❌ Access denied for user: {current_user}")
        return jsonify({'error': 'Access denied'}), 403
    
    print(f"✅ Admin access confirmed for user: {current_user}")
    
    try:
        # Получаем параметры фильтрации
        status_filter = request.args.get('status')
        search_query = request.args.get('search')
        
        print(f"📋 Moderation request - status_filter: {status_filter}, search: {search_query}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Базовый запрос с безопасными полями
        query = """
        SELECT 
            o.id, o.title, o.description, 
            COALESCE(o.budget_total, o.price, 0) as budget_total, 
            COALESCE(o.category, 'general') as category,
            o.created_at, 
            COALESCE(o.submitted_at, o.created_at) as submitted_at,
            COALESCE(o.user_id, o.created_by, 0) as user_internal_id,
            COALESCE(o.status, 'draft') as status,
            COALESCE(o.rejection_reason, '') as rejection_reason,
            COALESCE(u.telegram_id, 0) as telegram_id,
            COALESCE(u.first_name, 'Unknown') as first_name,
            COALESCE(u.last_name, '') as last_name
        FROM offers o
        LEFT JOIN users u ON (o.created_by = u.id OR o.user_id = u.id)
        WHERE 1=1
        """
        params = []
        
        # Добавляем фильтр по статусу
        if status_filter and status_filter != 'all':
            query += " AND o.status = ?"
            params.append(status_filter)
        else:
            # По умолчанию показываем офферы на модерации
            query += " AND o.status = ?"
            params.append('pending')
        
        # Добавляем поиск по названию
        if search_query:
            query += " AND (title LIKE ? OR description LIKE ?)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern])
        
        query += " ORDER BY o.created_at DESC"
        
        print(f"🔍 Executing query: {query}")
        print(f"🔍 Query params: {params}")
        
        cursor.execute(query, params)
        offers = cursor.fetchall()
        
        print(f"📊 Found {len(offers)} offers for moderation")
        
        offers_list = []
        for i, offer in enumerate(offers):
            user_name = f"{offer[11]} {offer[12]}".strip() if offer[11] != 'Unknown' else f"User {offer[10]}"
            offer_data = {
                'id': offer[0],
                'title': offer[1],
                'description': offer[2],
                'budget_total': offer[3],
                'price': offer[3],  # Для совместимости
                'category': offer[4],
                'created_at': offer[5],
                'submitted_at': offer[6],
                'user_id': offer[10],  # telegram_id пользователя
                'status': offer[8],
                'rejection_reason': offer[9],
                'user_name': user_name
            }
            offers_list.append(offer_data)
            print(f"📋 Offer {i+1}: ID={offer[0]}, Title='{offer[1]}', Status='{offer[8]}', User='{user_name}'")
        
        print(f"✅ Returning {len(offers_list)} offers to frontend")
        
        conn.close()
        return jsonify({
            'success': True,
            'data': {
                'offers': offers_list
            },
            'count': len(offers_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500


@offers_moderation_bp.route('/<int:offer_id>', methods=['GET'])
def get_offer_by_id(offer_id):
    """Получение конкретного оффера по ID"""
    try:
        print(f"🔍 Получение оффера {offer_id}")
        
        # Получаем user_id из заголовков
        user_id = request.headers.get('X-Telegram-User-Id')
        if not user_id:
            return jsonify({'error': 'User ID не передан'}), 400
        
        print(f"👤 User ID: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем информацию об оффере и проверяем права доступа
        cursor.execute("""
            SELECT o.id, o.title, o.description, o.budget_total, o.category, 
                   o.status, o.created_at, o.requirements, o.min_subscribers,
                   o.created_by, u.telegram_id as creator_telegram_id,
                   u.username as creator_username
            FROM offers o
            LEFT JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """, (offer_id,))
        
        offer = cursor.fetchone()
        conn.close()
        
        if not offer:
            return jsonify({'error': 'Оффер не найден'}), 404
        
        # Проверяем права доступа (пользователь может видеть только свои офферы, либо админ видит все)
        is_admin_user = str(user_id) == str(ADMIN_USER_ID)
        is_owner = str(offer['creator_telegram_id']) == str(user_id)
        
        if not is_admin_user and not is_owner:
            return jsonify({'error': 'Нет прав для просмотра этого оффера'}), 403
        
        offer_data = {
            'id': offer['id'],
            'title': offer['title'],
            'description': offer['description'],
            'budget_total': offer['budget_total'],
            'price': offer['budget_total'],  # alias for compatibility
            'category': offer['category'],
            'status': offer['status'],
            'created_at': offer['created_at'],
            'requirements': offer['requirements'],
            'min_subscribers': offer['min_subscribers'],
            'creator_id': offer['creator_telegram_id'],
            'creator_username': offer['creator_username']
        }
        
        print(f"📋 Оффер найден: {offer_data['title']} (статус: {offer_data['status']})")
        
        return jsonify({
            'success': True,
            'data': offer_data
        })
        
    except Exception as e:
        print(f"❌ Ошибка получения оффера: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@offers_moderation_bp.route('/<int:offer_id>/approve', methods=['POST'])
def approve_offer(offer_id):
    """Одобрение оффера администратором"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли оффер и получаем telegram_id создателя
        cursor.execute("""
            SELECT o.title, o.status, u.telegram_id, o.id
            FROM offers o
            LEFT JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """, (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        title, current_status, creator_telegram_id, _ = offer
        
        if current_status != 'pending':
            conn.close()
            return jsonify({'error': f'Cannot approve offer with status: {current_status}'}), 400
        
        # Обновляем статус на 'active'
        cursor.execute("""
            UPDATE offers 
            SET status = 'active', approved_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (offer_id,))
        
        conn.commit()
        
        # Отправляем детальное уведомление создателю оффера
        notification_message = f"""✅ <b>Оффер одобрен!</b>

🎯 <b>Название:</b> {title}
📊 <b>Статус:</b> Активен
⏰ <b>Время одобрения:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

🚀 <b>Что дальше:</b>
• Ваш оффер теперь виден всем владельцам каналов
• Вы будете получать уведомления о новых откликах
• Проверьте статистику в приложении

💡 Откройте приложение для подробной информации!"""

        send_telegram_notification(creator_telegram_id, notification_message, "offer_approved")
        
        # Получаем каналы, которым был отправлен оффер, и уведомляем их владельцев
        cursor.execute("""
            SELECT DISTINCT u.telegram_id, c.title, c.username
            FROM offer_proposals op
            LEFT JOIN channels c ON op.channel_id = c.id
            LEFT JOIN users u ON c.owner_id = u.id
            WHERE op.offer_id = ? AND u.telegram_id IS NOT NULL
        """, (offer_id,))
        channels = cursor.fetchall()
        
        # Отправляем уведомления владельцам каналов
        for channel in channels:
            channel_owner_id, channel_title, channel_username = channel
            
            channel_notification = f"""📢 <b>Новый оффер одобрен!</b>

🎯 <b>Название оффера:</b> {title}
📺 <b>Ваш канал:</b> {channel_title} ({channel_username or 'без username'})
⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

💼 <b>Что делать:</b>
• Оффер теперь активен и доступен для отклика
• Вы можете ответить на предложение в приложении
• Проверьте детали оффера и условия сотрудничества

🔔 <b>Не упустите возможность!</b>
💻 Откройте приложение для подробной информации"""

            send_telegram_notification(channel_owner_id, channel_notification, "offer_available_for_channel")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Offer approved successfully',
            'offer_id': offer_id,
            'new_status': 'active'
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@offers_moderation_bp.route('/<int:offer_id>/reject', methods=['POST'])
def reject_offer(offer_id):
    """Отклонение оффера администратором"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json() or {}
        rejection_reason = data.get('reason', 'Причина не указана')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли оффер и получаем telegram_id создателя
        cursor.execute("""
            SELECT o.title, o.status, u.telegram_id, o.id
            FROM offers o
            LEFT JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """, (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        title, current_status, creator_telegram_id, _ = offer
        
        if current_status != 'pending':
            conn.close()
            return jsonify({'error': f'Cannot reject offer with status: {current_status}'}), 400
        
        # Обновляем статус на 'rejected'
        cursor.execute("""
            UPDATE offers 
            SET status = 'rejected', 
                rejection_reason = ?,
                rejected_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (rejection_reason, offer_id))
        
        conn.commit()
        conn.close()
        
        # Отправляем детальное уведомление создателю оффера
        notification_message = f"""❌ <b>Оффер отклонен</b>

🎯 <b>Название:</b> {title}
📊 <b>Статус:</b> Отклонен
⏰ <b>Время отклонения:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

📝 <b>Причина отклонения:</b>
{rejection_reason}

🔄 <b>Что можно делать:</b>
• Отредактировать оффер с учетом замечаний
• Уточнить детали описания или бюджета
• Повторно отправить на модерацию

💡 Откройте приложение для редактирования!"""

        send_telegram_notification(creator_telegram_id, notification_message, "offer_rejected")
        
        return jsonify({
            'success': True,
            'message': 'Offer rejected successfully',
            'offer_id': offer_id,
            'new_status': 'rejected',
            'reason': rejection_reason
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@offers_moderation_bp.route('/<int:offer_id>/status', methods=['PUT'])
def update_offer_status(offer_id):
    """Обновление статуса оффера"""
    try:
        data = request.get_json() or {}
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
            
        # Валидация статусов
        valid_statuses = ['draft', 'pending', 'active', 'rejected']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Valid statuses: {valid_statuses}'}), 400
        
        user_id = get_telegram_user_id()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем права на изменение оффера
        cursor.execute("SELECT user_id, title, status FROM offers WHERE id = ?", (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        offer_user_id, title, current_status = offer
        
        # Проверяем права доступа
        if str(offer_user_id) != str(user_id) and not is_admin():
            conn.close()
            return jsonify({'error': 'Access denied'}), 403
        
        # Логика переходов статусов
        if current_status == 'draft' and new_status == 'pending':
            # Создатель отправляет черновик на модерацию
            cursor.execute("UPDATE offers SET status = 'pending', submitted_at = CURRENT_TIMESTAMP WHERE id = ?", (offer_id,))
            
            # Уведомления
            user_message = f"""📤 <b>Оффер отправлен на модерацию!</b>

🎯 <b>Название:</b> {title}
📊 <b>Статус:</b> На модерации
⏰ <b>Время отправки:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

⏳ <b>Что происходит сейчас:</b>
• Модераторы проверяют ваш оффер
• Обычно модерация занимает 1-24 часа
• Вы получите уведомление о результате

🔔 Следите за уведомлениями!"""

            admin_message = f"""📬 <b>Новый оффер на модерации</b>

🎯 <b>Название:</b> {title}
👤 <b>От пользователя:</b> {user_id}
⏰ <b>Время поступления:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

🔍 <b>Требуется:</b> Проверить и принять решение
💻 Откройте админ-панель для модерации"""

            send_telegram_notification(user_id, user_message, "offer_submitted")
            send_telegram_notification(ADMIN_USER_ID, admin_message, "admin_new_offer")
            
        elif current_status == 'rejected' and new_status == 'draft':
            # Возврат отклоненного оффера в черновики для редактирования
            cursor.execute("UPDATE offers SET status = 'draft', rejection_reason = NULL WHERE id = ?", (offer_id,))
            
        else:
            # Проверка других переходов только для админа
            if not is_admin():
                conn.close()
                return jsonify({'error': 'Invalid status transition'}), 400
            
            cursor.execute("UPDATE offers SET status = ? WHERE id = ?", (new_status, offer_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Status updated successfully',
            'offer_id': offer_id,
            'old_status': current_status,
            'new_status': new_status
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@offers_moderation_bp.route('/complete/<int:offer_id>', methods=['POST'])
def complete_offer(offer_id):
    """Завершение черновика оффера - переход к выбору каналов"""
    try:
        user_id = get_telegram_user_id()
        data = request.get_json() or {}
        selected_channels = data.get('channels', [])
        
        print(f"🚀 Complete offer {offer_id} for user {user_id} with channels: {selected_channels}")
        
        if not selected_channels:
            return jsonify({'error': 'No channels selected'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Сначала проверим, существует ли оффер вообще
        cursor.execute("SELECT id, title, status, created_by, user_id FROM offers WHERE id = ?", (offer_id,))
        offer_data = cursor.fetchone()
        
        if not offer_data:
            conn.close()
            print(f"❌ Offer {offer_id} not found")
            return jsonify({'error': 'Offer not found'}), 404
        
        print(f"📋 Offer data: {dict(offer_data)}")
        
        # Проверяем права доступа - нужно найти соответствие между internal ID и telegram ID
        offer_internal_id = offer_data['created_by'] or offer_data['user_id']
        
        if offer_internal_id:
            # Получаем telegram_id пользователя по internal ID
            cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (offer_internal_id,))
            user_record = cursor.fetchone()
            
            if user_record:
                offer_telegram_id = user_record['telegram_id']
                print(f"🔍 Offer creator telegram_id: {offer_telegram_id}, current user: {user_id}")
                
                if str(offer_telegram_id) != str(user_id):
                    conn.close()
                    print(f"❌ Access denied: offer telegram_id {offer_telegram_id} != user {user_id}")
                    return jsonify({'error': 'Access denied'}), 403
            else:
                conn.close()
                print(f"❌ User record not found for internal ID: {offer_internal_id}")
                return jsonify({'error': 'User not found'}), 404
        else:
            conn.close()
            print(f"❌ No creator ID found in offer data")
            return jsonify({'error': 'Invalid offer data'}), 400
            
        title, status = offer_data['title'], offer_data['status']
        
        if status != 'draft':
            conn.close()
            print(f"❌ Cannot complete offer with status: {status}")
            return jsonify({'error': f'Cannot complete offer with status: {status}'}), 400
        
        print(f"✅ Offer validation passed, proceeding with completion...")
        
        # Создаем предложения для выбранных каналов
        try:
            for i, channel_id in enumerate(selected_channels):
                print(f"📤 Creating proposal {i+1}/{len(selected_channels)} for channel {channel_id}")
                cursor.execute("""
                    INSERT INTO offer_proposals (offer_id, channel_id, status, created_at)
                    VALUES (?, ?, 'sent', CURRENT_TIMESTAMP)
                """, (offer_id, channel_id))
            
            print(f"✅ All {len(selected_channels)} proposals created successfully")
            
            # Обновляем статус оффера на 'pending'
            print(f"📝 Updating offer {offer_id} status to 'pending'...")
            cursor.execute("""
                UPDATE offers 
                SET status = 'pending', submitted_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (offer_id,))
            
            print(f"✅ Offer status updated to 'pending'")
            
            conn.commit()
            print(f"✅ Database changes committed successfully")
            
        except Exception as db_error:
            print(f"❌ Database operation failed: {db_error}")
            conn.rollback()
            conn.close()
            return jsonify({'error': f'Database operation failed: {str(db_error)}'}), 500
        
        conn.close()
        
        # Отправляем детальные уведомления
        user_message = f"""🚀 <b>Оффер отправлен на модерацию!</b>

🎯 <b>Название:</b> {title}
📺 <b>Выбрано каналов:</b> {len(selected_channels)}
📊 <b>Статус:</b> На модерации
⏰ <b>Время отправки:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

✅ <b>Что сделано:</b>
• Созданы предложения для {len(selected_channels)} каналов
• Оффер отправлен на модерацию
• Уведомления отправлены администраторам

⏳ <b>Ожидайте:</b> Результат модерации в течение 24 часов"""

        admin_message = f"""📬 <b>Новый оффер готов к модерации</b>

🎯 <b>Название:</b> {title}
👤 <b>Пользователь:</b> {user_id}
📺 <b>Каналов выбрано:</b> {len(selected_channels)}
⏰ <b>Время:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

🔍 <b>Действие:</b> Требуется модерация
💻 Перейдите в админ-панель"""

        send_telegram_notification(user_id, user_message, "offer_completed")
        send_telegram_notification(ADMIN_USER_ID, admin_message, "admin_new_complete_offer")
        
        return jsonify({
            'success': True,
            'message': 'Offer completed and sent for moderation',
            'offer_id': offer_id,
            'channels_count': len(selected_channels),
            'new_status': 'pending'
        })
        
    except Exception as e:
        print(f"💥 Unexpected error in complete_offer: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@offers_moderation_bp.route('/<int:offer_id>/reopen', methods=['POST'])
def reopen_offer(offer_id):
    """Возврат оффера на модерацию"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли оффер
        cursor.execute("SELECT user_id, title, status FROM offers WHERE id = ?", (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        user_id, title, current_status = offer
        
        # Возвращаем оффер на модерацию
        cursor.execute("""
            UPDATE offers 
            SET status = 'pending', 
                rejection_reason = NULL,
                submitted_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (offer_id,))
        
        conn.commit()
        conn.close()
        
        # Отправляем детальное уведомление
        user_message = f"""🔄 <b>Оффер возвращен на модерацию</b>

🎯 <b>Название:</b> {title}
📊 <b>Новый статус:</b> На модерации
⏰ <b>Время возврата:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

✅ <b>Что произошло:</b>
• Администратор вернул оффер на повторную модерацию
• Причина отклонения сброшена
• Оффер будет рассмотрен заново

⏳ <b>Ожидайте:</b> Новое решение в течение 24 часов"""

        send_telegram_notification(user_id, user_message, "offer_reopened")
        
        return jsonify({
            'success': True,
            'message': 'Offer reopened for moderation',
            'offer_id': offer_id,
            'new_status': 'pending'
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@offers_moderation_bp.route('/<int:offer_id>/delete', methods=['DELETE'])
def delete_offer_from_moderation(offer_id):
    """Удаление оффера администратором"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем информацию об оффере перед удалением
        cursor.execute("""
            SELECT o.title, o.created_by, o.user_id, o.status,
                   u.telegram_id, u.first_name, u.last_name
            FROM offers o
            LEFT JOIN users u ON (o.created_by = u.id OR o.user_id = u.id)
            WHERE o.id = ?
        """, (offer_id,))
        offer_data = cursor.fetchone()
        
        if not offer_data:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
        
        title = offer_data[0]
        user_telegram_id = offer_data[4]
        user_name = f"{offer_data[5] or ''} {offer_data[6] or ''}".strip() or 'Пользователь'
        
        # Удаляем связанные предложения
        cursor.execute("DELETE FROM offer_proposals WHERE offer_id = ?", (offer_id,))
        
        # Удаляем оффер
        cursor.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        
        conn.commit()
        conn.close()
        
        # Отправляем уведомление создателю оффера
        if user_telegram_id:
            user_message = f"""🗑️ <b>Оффер удален администратором</b>

🎯 <b>Название:</b> {title}
📊 <b>Действие:</b> Удален из системы
⏰ <b>Время удаления:</b> {datetime.now().strftime('%d.%m.%Y в %H:%M')}

ℹ️ <b>Информация:</b>
• Оффер был удален администратором из системы
• Все связанные предложения также удалены
• При необходимости можете создать новый оффер

💡 Обратитесь к поддержке при вопросах"""

            send_telegram_notification(user_telegram_id, user_message, "offer_deleted")
        
        return jsonify({
            'success': True,
            'message': 'Offer deleted successfully',
            'offer_id': offer_id,
            'title': title
        })
        
    except Exception as e:
        print(f"❌ Ошибка удаления оффера: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@offers_moderation_bp.route('/<int:offer_id>/update', methods=['PUT'])
def update_offer(offer_id):
    """Обновление данных оффера и отправка на модерацию"""
    try:
        # Получаем user_id из заголовков
        user_id = request.headers.get('X-Telegram-User-Id')
        if not user_id:
            return jsonify({'error': 'User ID не передан'}), 400
        
        # Получаем данные для обновления
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные для обновления не переданы'}), 400
        
        print(f"🔄 Обновление оффера {offer_id} пользователем {user_id}")
        print(f"📋 Данные для обновления: {data}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, что оффер существует и принадлежит пользователю
        cursor.execute("""
            SELECT o.id, o.title, o.status, o.created_by, u.telegram_id
            FROM offers o
            LEFT JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """, (offer_id,))
        
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Оффер не найден'}), 404
        
        # Проверяем права доступа
        if str(offer['telegram_id']) != str(user_id):
            conn.close()
            return jsonify({'error': 'Нет прав для редактирования этого оффера'}), 403
        
        # Проверяем, что оффер можно редактировать
        if offer['status'] not in ['draft', 'rejected']:
            conn.close()
            return jsonify({'error': f'Нельзя редактировать оффер со статусом: {offer["status"]}'}), 400
        
        old_title = offer['title']
        
        # Подготавливаем данные для обновления (обновляем только переданные поля)
        update_fields = []
        update_values = []
        
        # Всегда устанавливаем статус pending при редактировании и очищаем причину отклонения
        update_fields.append("status = 'pending'")
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_fields.append("rejection_reason = NULL")
        
        # Обновляем только те поля, которые были переданы
        if 'title' in data:
            update_fields.append("title = ?")
            update_values.append(data['title'])
            
        if 'description' in data:
            update_fields.append("description = ?")
            update_values.append(data['description'])
            
        if 'category' in data:
            update_fields.append("category = ?")
            update_values.append(data['category'])
            
        if 'budget_total' in data:
            update_fields.append("budget_total = ?")
            update_fields.append("price = ?")  # Синхронизируем price с budget_total
            update_values.append(data['budget_total'])
            update_values.append(data['budget_total'])
            
        if 'requirements' in data:
            update_fields.append("requirements = ?")
            update_values.append(data['requirements'])
            
        if 'min_subscribers' in data:
            update_fields.append("min_subscribers = ?")
            update_values.append(data['min_subscribers'])
        
        # Добавляем offer_id в конец для WHERE условия
        update_values.append(offer_id)
        
        # Формируем и выполняем запрос
        update_query = f"UPDATE offers SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(update_query, update_values)
        
        conn.commit()
        conn.close()
        
        print(f"✅ Оффер {offer_id} успешно обновлен и отправлен на модерацию")
        
        # Формируем сообщение об изменениях
        changes_list = []
        if 'budget_total' in data:
            changes_list.append(f"• Бюджет: {data['budget_total']} ₽")
        if 'description' in data:
            changes_list.append(f"• Объявление: обновлено")
        if 'title' in data:
            changes_list.append(f"• Название: {data['title']}")
        if 'category' in data:
            changes_list.append(f"• Категория: {data['category']}")
        
        changes_text = "\n".join(changes_list) if changes_list else "• Общие правки"
        
        # Отправляем уведомление пользователю
        send_telegram_notification(
            user_id, 
            f"🔄 Ваш оффер \"{data.get('title', old_title)}\" был обновлен и отправлен на повторную модерацию.\n\n"
            f"📋 Внесенные изменения:\n"
            f"{changes_text}\n\n"
            f"⏳ Администратор рассмотрит ваши изменения в ближайшее время.",
            "offer_updated"
        )
        
        # Уведомляем админа о новом оффере на модерации  
        send_telegram_notification(
            ADMIN_USER_ID,
            f"🔄 Пользователь обновил оффер и отправил на повторную модерацию:\n\n"
            f"📝 Название: {data.get('title', old_title)}\n"
            f"💰 Бюджет: {data.get('budget_total', 'не изменен')} ₽\n"
            f"👤 Пользователь: {user_id}\n"
            f"🆔 Оффер ID: {offer_id}\n\n"
            f"📝 Изменения:\n{changes_text}\n\n"
            f"⚡ Требует модерации",
            "offer_updated_admin"
        )
        
        return jsonify({
            'success': True,
            'message': 'Оффер успешно обновлен и отправлен на модерацию',
            'offer_id': offer_id,
            'title': data.get('title')
        })
        
    except Exception as e:
        print(f"❌ Ошибка обновления оффера: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500