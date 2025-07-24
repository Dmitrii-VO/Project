#!/usr/bin/env python3
"""
Админ-панель для управления Telegram Mini App
Полная система администрирования с метриками и управлением
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template_string

from app.models.database import execute_db_query
from app.services.auth_service import get_current_user_id
from app.events.event_dispatcher import event_dispatcher
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

class AdminDashboard:
    """Главная админ-панель"""
    
    def __init__(self):
        self.admin_blueprint = Blueprint('admin', __name__, url_prefix='/admin')
        self._setup_routes()
    
    def _setup_routes(self):
        """Настройка маршрутов админ-панели"""
        
        @self.admin_blueprint.before_request
        def check_admin_access():
            """Проверка прав администратора"""
            user_id = get_current_user_id()
            if not user_id:
                return jsonify({'error': 'Требуется авторизация'}), 401
            
            # Проверяем, является ли пользователь администратором
            if not self._is_admin(user_id):
                return jsonify({'error': 'Доступ запрещен'}), 403
        
        @self.admin_blueprint.route('/')
        def dashboard():
            """Главная страница админ-панели"""
            return self._render_dashboard()
        
        @self.admin_blueprint.route('/api/stats')
        def get_stats():
            """API для получения общей статистики"""
            return jsonify(self.get_system_stats())
        
        @self.admin_blueprint.route('/api/users')
        def get_users():
            """API для получения списка пользователей"""
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            search = request.args.get('search', '')
            
            return jsonify(self.get_users_list(page, limit, search))
        
        @self.admin_blueprint.route('/api/users/<int:user_id>/ban', methods=['POST'])
        def ban_user(user_id):
            """API для блокировки пользователя"""
            data = request.get_json()
            reason = data.get('reason', 'Нарушение правил')
            
            return jsonify(self.ban_user(user_id, reason))
        
        @self.admin_blueprint.route('/api/channels')
        def get_channels():
            """API для получения списка каналов"""
            status = request.args.get('status', 'all')
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            return jsonify(self.get_channels_list(status, page, limit))
        
        @self.admin_blueprint.route('/api/channels/<int:channel_id>/verify', methods=['POST'])
        def verify_channel(channel_id):
            """API для верификации канала"""
            return jsonify(self.verify_channel_manually(channel_id))
        
        @self.admin_blueprint.route('/api/offers')
        def get_offers():
            """API для получения списка офферов"""
            status = request.args.get('status', 'all')
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            return jsonify(self.get_offers_list(status, page, limit))
        
        @self.admin_blueprint.route('/api/payments')
        def get_payments():
            """API для получения списка платежей"""
            status = request.args.get('status', 'all')
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            return jsonify(self.get_payments_list(status, page, limit))
        
        @self.admin_blueprint.route('/api/payments/<int:payment_id>/approve', methods=['POST'])
        def approve_payment(payment_id):
            """API для одобрения выплаты"""
            admin_id = get_current_user_id()
            return jsonify(self.approve_withdrawal(payment_id, admin_id))
        
        @self.admin_blueprint.route('/api/system/maintenance', methods=['POST'])
        def toggle_maintenance():
            """API для включения/выключения режима обслуживания"""
            data = request.get_json()
            enabled = data.get('enabled', False)
            message = data.get('message', 'Проводятся технические работы')
            
            return jsonify(self.set_maintenance_mode(enabled, message))
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Получение общей статистики системы"""
        try:
            # Статистика пользователей
            user_stats = execute_db_query(
                """SELECT 
                   COUNT(*) as total_users,
                   COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as new_users_week,
                   COUNT(CASE WHEN last_login >= datetime('now', '-1 day') THEN 1 END) as active_users_day,
                   COUNT(CASE WHEN is_admin = 1 THEN 1 END) as admin_count
                   FROM users""",
                fetch_one=True
            )
            
            # Статистика каналов
            channel_stats = execute_db_query(
                """SELECT 
                   COUNT(*) as total_channels,
                   COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_channels,
                   COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as new_channels_week,
                   AVG(subscriber_count) as avg_subscribers
                   FROM channels""",
                fetch_one=True
            )
            
            # Статистика офферов
            offer_stats = execute_db_query(
                """SELECT 
                   COUNT(*) as total_offers,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
                   COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as new_offers_week,
                   AVG(COALESCE(budget_total, price)) as avg_budget
                   FROM offers""",
                fetch_one=True
            )
            
            # Статистика платежей
            payment_stats = execute_db_query(
                """SELECT 
                   COUNT(*) as total_payments,
                   COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
                   SUM(CASE WHEN payment_type = 'deposit' AND status = 'completed' THEN amount ELSE 0 END) as total_deposits,
                   SUM(CASE WHEN payment_type = 'withdrawal' AND status = 'completed' THEN amount ELSE 0 END) as total_withdrawals
                   FROM payments""",
                fetch_one=True
            )
            
            # Статистика размещений
            placement_stats = execute_db_query(
                """SELECT 
                   COUNT(*) as total_placements,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_placements,
                   AVG(views_count) as avg_views,
                   AVG(engagement_rate) as avg_engagement
                   FROM offer_placements""",
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'users': dict(user_stats) if user_stats else {},
                    'channels': dict(channel_stats) if channel_stats else {},
                    'offers': dict(offer_stats) if offer_stats else {},
                    'payments': dict(payment_stats) if payment_stats else {},
                    'placements': dict(placement_stats) if placement_stats else {},
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_users_list(self, page: int = 1, limit: int = 50, search: str = '') -> Dict[str, Any]:
        """Получение списка пользователей с пагинацией"""
        try:
            offset = (page - 1) * limit
            
            # Подготавливаем условие поиска
            search_condition = ""
            search_params = []
            
            if search:
                search_condition = """
                    WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ? 
                    OR CAST(telegram_id as TEXT) LIKE ?
                """
                search_term = f"%{search}%"
                search_params = [search_term, search_term, search_term, search_term]
            
            # Получаем пользователей
            users = execute_db_query(
                f"""SELECT id, telegram_id, username, first_name, last_name, 
                           balance, is_admin, is_active, created_at, last_login
                    FROM users 
                    {search_condition}
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?""",
                search_params + [limit, offset]
            )
            
            # Получаем общее количество
            total_count = execute_db_query(
                f"SELECT COUNT(*) as count FROM users {search_condition}",
                search_params,
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'users': [dict(user) for user in users],
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count['count'] if total_count else 0,
                        'pages': ((total_count['count'] if total_count else 0) + limit - 1) // limit
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка пользователей: {e}")
            return {'success': False, 'error': str(e)}
    
    def ban_user(self, user_id: int, reason: str) -> Dict[str, Any]:
        """Блокировка пользователя"""
        try:
            admin_id = get_current_user_id()
            
            # Блокируем пользователя
            execute_db_query(
                """UPDATE users 
                   SET is_active = 0, ban_reason = ?, banned_at = ?, banned_by = ?, updated_at = ?
                   WHERE id = ?""",
                (reason, datetime.now(), admin_id, datetime.now(), user_id)
            )
            
            # Отправляем событие
            event_dispatcher.security_suspicious_activity(
                user_id=user_id,
                action='user_banned',
                risk_level='high',
                details={'reason': reason, 'banned_by': admin_id}
            )
            
            logger.info(f"👮 Пользователь {user_id} заблокирован администратором {admin_id}")
            
            return {
                'success': True,
                'message': 'Пользователь заблокирован'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка блокировки пользователя: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_channels_list(self, status: str = 'all', page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Получение списка каналов"""
        try:
            offset = (page - 1) * limit
            
            # Подготавливаем условие фильтрации
            status_condition = ""
            status_params = []
            
            if status == 'verified':
                status_condition = "WHERE is_verified = 1"
            elif status == 'pending':
                status_condition = "WHERE is_verified = 0 AND verification_code IS NOT NULL"
            elif status == 'unverified':
                status_condition = "WHERE is_verified = 0 AND verification_code IS NULL"
            
            # Получаем каналы
            channels = execute_db_query(
                f"""SELECT c.id, c.username, c.title, c.subscriber_count, c.is_verified, 
                           c.is_active, c.created_at, c.verification_code,
                           u.first_name as owner_name, u.telegram_id as owner_telegram_id
                    FROM channels c
                    JOIN users u ON c.owner_id = u.id
                    {status_condition}
                    ORDER BY c.created_at DESC 
                    LIMIT ? OFFSET ?""",
                status_params + [limit, offset]
            )
            
            # Получаем общее количество
            total_count = execute_db_query(
                f"SELECT COUNT(*) as count FROM channels c {status_condition}",
                status_params,
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'channels': [dict(channel) for channel in channels],
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count['count'] if total_count else 0,
                        'pages': ((total_count['count'] if total_count else 0) + limit - 1) // limit
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка каналов: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_channel_manually(self, channel_id: int) -> Dict[str, Any]:
        """Ручная верификация канала администратором"""
        try:
            admin_id = get_current_user_id()
            
            # Получаем данные канала
            channel = execute_db_query(
                "SELECT * FROM channels WHERE id = ?",
                (channel_id,),
                fetch_one=True
            )
            
            if not channel:
                return {'success': False, 'error': 'Канал не найден'}
            
            # Верифицируем канал
            execute_db_query(
                """UPDATE channels 
                   SET is_verified = 1, verification_code = NULL, verification_expires_at = NULL,
                       verified_at = ?, admin_verified_by = ?, updated_at = ?
                   WHERE id = ?""",
                (datetime.now(), admin_id, datetime.now(), channel_id)
            )
            
            # Отправляем событие
            event_dispatcher.channel_verified(
                channel_id=channel_id,
                owner_id=channel['owner_id'],
                title=channel['title']
            )
            
            logger.info(f"✅ Канал {channel_id} верифицирован администратором {admin_id}")
            
            return {
                'success': True,
                'message': 'Канал верифицирован'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка верификации канала: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_offers_list(self, status: str = 'all', page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Получение списка офферов"""
        try:
            offset = (page - 1) * limit
            
            # Подготавливаем условие фильтрации
            status_condition = ""
            status_params = []
            
            if status != 'all':
                status_condition = "WHERE o.status = ?"
                status_params = [status]
            
            # Получаем офферы
            offers = execute_db_query(
                f"""SELECT o.id, o.title, o.status, COALESCE(o.budget_total, o.price) as budget,
                           o.created_at, o.expires_at,
                           u.first_name as creator_name, u.telegram_id as creator_telegram_id,
                           COUNT(r.id) as responses_count
                    FROM offers o
                    JOIN users u ON o.created_by = u.id
                    LEFT JOIN offer_responses r ON o.id = r.offer_id
                    {status_condition}
                    GROUP BY o.id
                    ORDER BY o.created_at DESC 
                    LIMIT ? OFFSET ?""",
                status_params + [limit, offset]
            )
            
            return {
                'success': True,
                'data': {
                    'offers': [dict(offer) for offer in offers]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка офферов: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_payments_list(self, status: str = 'all', page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Получение списка платежей"""
        try:
            offset = (page - 1) * limit
            
            # Подготавливаем условие фильтрации
            status_condition = ""
            status_params = []
            
            if status != 'all':
                status_condition = "WHERE p.status = ?"
                status_params = [status]
            
            # Получаем платежи
            payments = execute_db_query(
                f"""SELECT p.id, p.amount, p.currency, p.payment_type, p.status, p.provider,
                           p.description, p.created_at, p.processed_at,
                           u.first_name as user_name, u.telegram_id as user_telegram_id
                    FROM payments p
                    JOIN users u ON p.user_id = u.id
                    {status_condition}
                    ORDER BY p.created_at DESC 
                    LIMIT ? OFFSET ?""",
                status_params + [limit, offset]
            )
            
            return {
                'success': True,
                'data': {
                    'payments': [dict(payment) for payment in payments]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка платежей: {e}")
            return {'success': False, 'error': str(e)}
    
    def approve_withdrawal(self, payment_id: int, admin_id: int) -> Dict[str, Any]:
        """Одобрение заявки на вывод средств"""
        try:
            from app.payments.telegram_payments import TelegramPaymentProcessor
            
            processor = TelegramPaymentProcessor()
            result = processor.process_withdrawal(payment_id, admin_id)
            
            if result['success']:
                logger.info(f"💰 Выплата {payment_id} одобрена администратором {admin_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка одобрения выплаты: {e}")
            return {'success': False, 'error': str(e)}
    
    def set_maintenance_mode(self, enabled: bool, message: str = '') -> Dict[str, Any]:
        """Включение/выключение режима обслуживания"""
        try:
            # Сохраняем настройки в конфигурации системы
            execute_db_query(
                """INSERT OR REPLACE INTO system_config (key, value, updated_at)
                   VALUES ('maintenance_mode', ?, ?)""",
                (str(enabled).lower(), datetime.now())
            )
            
            if message:
                execute_db_query(
                    """INSERT OR REPLACE INTO system_config (key, value, updated_at)
                       VALUES ('maintenance_message', ?, ?)""",
                    (message, datetime.now())
                )
            
            # Отправляем системное событие
            event_dispatcher.system_maintenance(
                enabled=enabled,
                message=message,
                admin_id=get_current_user_id()
            )
            
            action = "включен" if enabled else "выключен"
            logger.info(f"🔧 Режим обслуживания {action}")
            
            return {
                'success': True,
                'maintenance_enabled': enabled,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка изменения режима обслуживания: {e}")
            return {'success': False, 'error': str(e)}
    
    def _is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        try:
            user = execute_db_query(
                "SELECT is_admin FROM users WHERE telegram_id = ?",
                (user_id,),
                fetch_one=True
            )
            return bool(user and user['is_admin'])
        except:
            return False
    
    def _render_dashboard(self) -> str:
        """Рендеринг HTML страницы админ-панели"""
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Админ-панель - Telegram Mini App</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; }
                .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
                .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
                .section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .section h2 { margin-top: 0; }
                .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
                .btn-primary { background: #007bff; color: white; }
                .btn-success { background: #28a745; color: white; }
                .btn-danger { background: #dc3545; color: white; }
                .table { width: 100%; border-collapse: collapse; }
                .table th, .table td { padding: 8px; border-bottom: 1px solid #ddd; text-align: left; }
                .table th { background: #f8f9fa; }
                .loading { text-align: center; padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Админ-панель Telegram Mini App</h1>
                    <p>Система управления и мониторинга</p>
                </div>
                
                <div class="stats-grid" id="stats-grid">
                    <div class="loading">Загрузка статистики...</div>
                </div>
                
                <div class="section">
                    <h2>Быстрые действия</h2>
                    <button class="btn btn-primary" onclick="refreshStats()">Обновить статистику</button>
                    <button class="btn btn-success" onclick="exportData()">Экспорт данных</button>
                    <button class="btn btn-danger" onclick="toggleMaintenance()">Режим обслуживания</button>
                </div>
                
                <div class="section">
                    <h2>Последние пользователи</h2>
                    <div id="recent-users">Загрузка...</div>
                </div>
                
                <div class="section">
                    <h2>Ожидающие проверки</h2>
                    <div id="pending-items">Загрузка...</div>
                </div>
            </div>
            
            <script>
                // Загрузка статистики при загрузке страницы
                document.addEventListener('DOMContentLoaded', function() {
                    loadStats();
                    loadRecentUsers();
                    loadPendingItems();
                });
                
                function loadStats() {
                    fetch('/admin/api/stats')
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                renderStats(data.data);
                            }
                        })
                        .catch(error => console.error('Error:', error));
                }
                
                function renderStats(stats) {
                    const grid = document.getElementById('stats-grid');
                    grid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${stats.users.total_users || 0}</div>
                            <div class="stat-label">Всего пользователей</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.channels.verified_channels || 0}</div>
                            <div class="stat-label">Верифицированных каналов</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.offers.active_offers || 0}</div>
                            <div class="stat-label">Активных офферов</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.payments.pending_payments || 0}</div>
                            <div class="stat-label">Ожидающих выплат</div>
                        </div>
                    `;
                }
                
                function loadRecentUsers() {
                    fetch('/admin/api/users?limit=10')
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                renderRecentUsers(data.data.users);
                            }
                        });
                }
                
                function renderRecentUsers(users) {
                    const container = document.getElementById('recent-users');
                    const html = users.map(user => `
                        <div style="padding: 10px; border-bottom: 1px solid #eee;">
                            <strong>${user.first_name || 'Пользователь'}</strong> (@${user.username || user.telegram_id})
                            <span style="float: right;">${new Date(user.created_at).toLocaleDateString()}</span>
                        </div>
                    `).join('');
                    container.innerHTML = html || 'Нет данных';
                }
                
                function loadPendingItems() {
                    // Загрузка элементов, ожидающих проверки
                    const container = document.getElementById('pending-items');
                    container.innerHTML = 'Реализация загрузки ожидающих элементов...';
                }
                
                function refreshStats() {
                    loadStats();
                    alert('Статистика обновлена');
                }
                
                function exportData() {
                    alert('Функция экспорта данных в разработке');
                }
                
                function toggleMaintenance() {
                    if (confirm('Изменить режим обслуживания?')) {
                        alert('Функция режима обслуживания в разработке');
                    }
                }
            </script>
        </body>
        </html>
        """)