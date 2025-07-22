"""
API endpoints for offer moderation and status management
"""
from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.config.telegram_config import AppConfig

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

def send_telegram_notification(user_id, message):
    """Отправка уведомления в Telegram"""
    try:
        from app.telegram.telegram_notifications import send_notification
        send_notification(user_id, message)
        return True
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

@offers_moderation_bp.route('/<int:offer_id>/approve', methods=['POST'])
def approve_offer(offer_id):
    """Одобрение оффера администратором"""
    if not is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли оффер и его текущий статус
        cursor.execute("SELECT user_id, title, status FROM offers WHERE id = ?", (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        user_id, title, current_status = offer
        
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
        conn.close()
        
        # Отправляем уведомление создателю оффера
        notification_message = f"✅ Ваш оффер '{title}' одобрен и теперь активен!"
        send_telegram_notification(user_id, notification_message)
        
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
        
        # Проверяем, существует ли оффер и его текущий статус
        cursor.execute("SELECT user_id, title, status FROM offers WHERE id = ?", (offer_id,))
        offer = cursor.fetchone()
        
        if not offer:
            conn.close()
            return jsonify({'error': 'Offer not found'}), 404
            
        user_id, title, current_status = offer
        
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
        
        # Отправляем уведомление создателю оффера
        notification_message = f"❌ Ваш оффер '{title}' отклонен.\nПричина: {rejection_reason}\n\nВы можете отредактировать оффер и отправить его повторно."
        send_telegram_notification(user_id, notification_message)
        
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
            send_telegram_notification(user_id, f"📤 Ваш оффер '{title}' отправлен на модерацию.")
            send_telegram_notification(ADMIN_USER_ID, f"📬 Новый оффер на модерации: '{title}' от пользователя {user_id}")
            
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
        
        # Отправляем уведомления
        send_telegram_notification(user_id, f"📤 Ваш оффер '{title}' отправлен на модерацию с {len(selected_channels)} выбранными каналами.")
        send_telegram_notification(ADMIN_USER_ID, f"📬 Новый оффер на модерации: '{title}' от пользователя {user_id}")
        
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
        
        # Отправляем уведомления
        send_telegram_notification(user_id, f"🔄 Ваш оффер '{title}' возвращен на модерацию.")
        
        return jsonify({
            'success': True,
            'message': 'Offer reopened for moderation',
            'offer_id': offer_id,
            'new_status': 'pending'
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500