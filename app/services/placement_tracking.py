# placement_tracking.py - Система отслеживания эффективности рекламных размещений
import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

@dataclass
class PlacementMetrics:
    """Метрики рекламного размещения"""
    placement_id: str
    offer_id: int
    channel_id: int
    views: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    cost: float = 0.0
    ctr: float = 0.0  # Click Through Rate
    conversion_rate: float = 0.0
    roi: float = 0.0  # Return on Investment
    created_at: datetime = None
    updated_at: datetime = None

class PlacementTracker:
    """Система отслеживания эффективности размещений"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ensure_tracking_tables()
    
    def get_db_connection(self):
        """Получение подключения к базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def ensure_tracking_tables(self):
        """Создание таблиц для отслеживания размещений"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Таблица рекламных размещений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ad_placements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id TEXT UNIQUE NOT NULL,
                    offer_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    response_id INTEGER,
                    status TEXT DEFAULT 'active',
                    post_url TEXT,
                    scheduled_at TIMESTAMP,
                    published_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (offer_id) REFERENCES offers (id),
                    FOREIGN KEY (channel_id) REFERENCES channels (id),
                    FOREIGN KEY (response_id) REFERENCES offer_responses (id)
                )
            ''')
            
            # Таблица метрик размещений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS placement_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id TEXT NOT NULL,
                    metric_date DATE NOT NULL,
                    views INTEGER DEFAULT 0,
                    clicks INTEGER DEFAULT 0,
                    conversions INTEGER DEFAULT 0,
                    revenue DECIMAL(10,2) DEFAULT 0.00,
                    cost DECIMAL(10,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (placement_id) REFERENCES ad_placements (placement_id),
                    UNIQUE(placement_id, metric_date)
                )
            ''')
            
            # Таблица событий отслеживания (клики, просмотры, конверсии)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracking_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id TEXT NOT NULL,
                    event_type TEXT NOT NULL, -- 'view', 'click', 'conversion'
                    user_agent TEXT,
                    ip_address TEXT,
                    referrer TEXT,
                    conversion_value DECIMAL(10,2),
                    event_data TEXT, -- JSON с дополнительными данными
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (placement_id) REFERENCES ad_placements (placement_id)
                )
            ''')
            
            # Таблица целей и KPI
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS placement_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id TEXT NOT NULL,
                    goal_type TEXT NOT NULL, -- 'clicks', 'conversions', 'revenue', 'roi'
                    target_value DECIMAL(10,2) NOT NULL,
                    current_value DECIMAL(10,2) DEFAULT 0.00,
                    is_achieved BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (placement_id) REFERENCES ad_placements (placement_id)
                )
            ''')
            
            # Индексы для оптимизации
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_placement_metrics_date ON placement_metrics(metric_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracking_events_type ON tracking_events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracking_events_placement ON tracking_events(placement_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Таблицы отслеживания размещений созданы/проверены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания таблиц отслеживания: {e}")
            return False
    
    def create_placement(self, offer_id: int, channel_id: int, response_id: int = None, 
                        scheduled_at: datetime = None, expires_at: datetime = None) -> str:
        """Создание нового размещения"""
        try:
            placement_id = str(uuid.uuid4())
            
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            # Получаем информацию об оффере и канале
            cursor.execute('''
                SELECT o.price, c.title
                FROM offers o, channels c
                WHERE o.id = ? AND c.id = ?
            ''', (offer_id, channel_id))
            
            offer_channel = cursor.fetchone()
            if not offer_channel:
                conn.close()
                return None
            
            cost = float(offer_channel['price'])
            
            # Создаем размещение
            cursor.execute('''
                INSERT INTO ad_placements (
                    placement_id, offer_id, channel_id, response_id,
                    scheduled_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (placement_id, offer_id, channel_id, response_id, 
                  scheduled_at, expires_at))
            
            # Создаем начальную запись метрик
            today = datetime.now().date()
            cursor.execute('''
                INSERT OR REPLACE INTO placement_metrics (
                    placement_id, metric_date, cost
                ) VALUES (?, ?, ?)
            ''', (placement_id, today, cost))
            
            # Создаем цели по умолчанию
            default_goals = [
                ('clicks', 100),  # 100 кликов
                ('conversions', 5),  # 5 конверсий
                ('roi', 150)  # 150% ROI
            ]
            
            for goal_type, target_value in default_goals:
                cursor.execute('''
                    INSERT INTO placement_goals (placement_id, goal_type, target_value)
                    VALUES (?, ?, ?)
                ''', (placement_id, goal_type, target_value))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Создано размещение {placement_id} для оффера {offer_id} в канале {channel_id}")
            return placement_id
            
        except Exception as e:
            logger.error(f"Ошибка создания размещения: {e}")
            return None
    
    def track_event(self, placement_id: str, event_type: str, 
                   user_agent: str = None, ip_address: str = None,
                   referrer: str = None, conversion_value: float = None,
                   event_data: dict = None) -> bool:
        """Отслеживание события (просмотр, клик, конверсия)"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Проверяем существование размещения
            cursor.execute('SELECT id FROM ad_placements WHERE placement_id = ?', (placement_id,))
            if not cursor.fetchone():
                conn.close()
                logger.warning(f"Размещение {placement_id} не найдено")
                return False
            
            # Записываем событие
            cursor.execute('''
                INSERT INTO tracking_events (
                    placement_id, event_type, user_agent, ip_address,
                    referrer, conversion_value, event_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (placement_id, event_type, user_agent, ip_address,
                  referrer, conversion_value, json.dumps(event_data) if event_data else None))
            
            # Обновляем метрики
            today = datetime.now().date()
            
            if event_type == 'view':
                cursor.execute('''
                    INSERT OR REPLACE INTO placement_metrics (
                        placement_id, metric_date, views,
                        clicks, conversions, revenue, cost
                    ) VALUES (
                        ?, ?, 
                        COALESCE((SELECT views FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0) + 1,
                        COALESCE((SELECT clicks FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT conversions FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT revenue FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT cost FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0)
                    )
                ''', (placement_id, today, placement_id, today, placement_id, today, 
                      placement_id, today, placement_id, today, placement_id, today))
            
            elif event_type == 'click':
                cursor.execute('''
                    INSERT OR REPLACE INTO placement_metrics (
                        placement_id, metric_date, views, clicks,
                        conversions, revenue, cost
                    ) VALUES (
                        ?, ?,
                        COALESCE((SELECT views FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT clicks FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0) + 1,
                        COALESCE((SELECT conversions FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT revenue FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT cost FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0)
                    )
                ''', (placement_id, today, placement_id, today, placement_id, today,
                      placement_id, today, placement_id, today, placement_id, today))
            
            elif event_type == 'conversion':
                revenue_add = conversion_value or 0
                cursor.execute('''
                    INSERT OR REPLACE INTO placement_metrics (
                        placement_id, metric_date, views, clicks, conversions,
                        revenue, cost
                    ) VALUES (
                        ?, ?,
                        COALESCE((SELECT views FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT clicks FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0),
                        COALESCE((SELECT conversions FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0) + 1,
                        COALESCE((SELECT revenue FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0) + ?,
                        COALESCE((SELECT cost FROM placement_metrics WHERE placement_id = ? AND metric_date = ?), 0)
                    )
                ''', (placement_id, today, placement_id, today, placement_id, today,
                      placement_id, today, placement_id, today, revenue_add, placement_id, today))
            
            # Обновляем цели
            self._update_goals(cursor, placement_id)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Записано событие {event_type} для размещения {placement_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отслеживания события: {e}")
            return False
    
    def _update_goals(self, cursor, placement_id: str):
        """Обновление статуса целей"""
        try:
            # Получаем текущие метрики
            cursor.execute('''
                SELECT 
                    SUM(views) as total_views,
                    SUM(clicks) as total_clicks,
                    SUM(conversions) as total_conversions,
                    SUM(revenue) as total_revenue,
                    SUM(cost) as total_cost
                FROM placement_metrics
                WHERE placement_id = ?
            ''', (placement_id,))
            
            metrics = cursor.fetchone()
            if not metrics:
                return
            
            total_clicks = metrics['total_clicks'] or 0
            total_conversions = metrics['total_conversions'] or 0
            total_revenue = metrics['total_revenue'] or 0
            total_cost = metrics['total_cost'] or 0
            
            roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            
            # Обновляем цели
            goal_values = {
                'clicks': total_clicks,
                'conversions': total_conversions,
                'revenue': total_revenue,
                'roi': roi
            }
            
            for goal_type, current_value in goal_values.items():
                cursor.execute('''
                    UPDATE placement_goals
                    SET current_value = ?,
                        is_achieved = CASE WHEN current_value >= target_value THEN 1 ELSE 0 END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE placement_id = ? AND goal_type = ?
                ''', (current_value, placement_id, goal_type))
            
        except Exception as e:
            logger.error(f"Ошибка обновления целей: {e}")
    
    def get_placement_metrics(self, placement_id: str) -> PlacementMetrics:
        """Получение метрик размещения"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            # Получаем основную информацию о размещении
            cursor.execute('''
                SELECT ap.*, o.price as offer_price
                FROM ad_placements ap
                JOIN offers o ON ap.offer_id = o.id
                WHERE ap.placement_id = ?
            ''', (placement_id,))
            
            placement = cursor.fetchone()
            if not placement:
                conn.close()
                return None
            
            # Получаем агрегированные метрики
            cursor.execute('''
                SELECT 
                    SUM(views) as total_views,
                    SUM(clicks) as total_clicks,
                    SUM(conversions) as total_conversions,
                    SUM(revenue) as total_revenue,
                    SUM(cost) as total_cost
                FROM placement_metrics
                WHERE placement_id = ?
            ''', (placement_id,))
            
            metrics = cursor.fetchone()
            conn.close()
            
            if not metrics:
                return PlacementMetrics(
                    placement_id=placement_id,
                    offer_id=placement['offer_id'],
                    channel_id=placement['channel_id'],
                    cost=float(placement['offer_price']),
                    created_at=datetime.fromisoformat(placement['created_at'])
                )
            
            total_views = metrics['total_views'] or 0
            total_clicks = metrics['total_clicks'] or 0
            total_conversions = metrics['total_conversions'] or 0
            total_revenue = metrics['total_revenue'] or 0
            total_cost = metrics['total_cost'] or 0
            
            # Рассчитываем производные метрики
            ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
            conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
            roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            
            return PlacementMetrics(
                placement_id=placement_id,
                offer_id=placement['offer_id'],
                channel_id=placement['channel_id'],
                views=total_views,
                clicks=total_clicks,
                conversions=total_conversions,
                revenue=float(total_revenue),
                cost=float(total_cost),
                ctr=round(ctr, 2),
                conversion_rate=round(conversion_rate, 2),
                roi=round(roi, 2),
                created_at=datetime.fromisoformat(placement['created_at'])
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик размещения: {e}")
            return None
    
    def get_user_placements(self, telegram_user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение размещений пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Получаем размещения пользователя
            cursor.execute('''
                SELECT 
                    ap.*,
                    o.title as offer_title,
                    o.price as offer_price,
                    c.title as channel_title,
                    c.username as channel_username,
                    COALESCE(SUM(pm.views), 0) as total_views,
                    COALESCE(SUM(pm.clicks), 0) as total_clicks,
                    COALESCE(SUM(pm.conversions), 0) as total_conversions,
                    COALESCE(SUM(pm.revenue), 0) as total_revenue,
                    COALESCE(SUM(pm.cost), 0) as total_cost
                FROM ad_placements ap
                JOIN offers o ON ap.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                JOIN channels c ON ap.channel_id = c.id
                LEFT JOIN placement_metrics pm ON ap.placement_id = pm.placement_id
                WHERE u.telegram_id = ?
                GROUP BY ap.id
                ORDER BY ap.created_at DESC
                LIMIT ?
            ''', (telegram_user_id, limit))
            
            placements = cursor.fetchall()
            conn.close()
            
            result = []
            for p in placements:
                total_views = p['total_views'] or 0
                total_clicks = p['total_clicks'] or 0
                total_conversions = p['total_conversions'] or 0
                total_revenue = p['total_revenue'] or 0
                total_cost = p['total_cost'] or 0
                
                ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
                conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
                roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
                
                result.append({
                    'placement_id': p['placement_id'],
                    'offer_title': p['offer_title'],
                    'channel_title': p['channel_title'],
                    'channel_username': p['channel_username'],
                    'status': p['status'],
                    'views': total_views,
                    'clicks': total_clicks,
                    'conversions': total_conversions,
                    'revenue': float(total_revenue),
                    'cost': float(total_cost),
                    'ctr': round(ctr, 2),
                    'conversion_rate': round(conversion_rate, 2),
                    'roi': round(roi, 2),
                    'created_at': p['created_at'],
                    'published_at': p['published_at']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения размещений пользователя: {e}")
            return []
    
    def get_performance_summary(self, telegram_user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение сводки по эффективности за период"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT ap.placement_id) as total_placements,
                    COALESCE(SUM(pm.views), 0) as total_views,
                    COALESCE(SUM(pm.clicks), 0) as total_clicks,
                    COALESCE(SUM(pm.conversions), 0) as total_conversions,
                    COALESCE(SUM(pm.revenue), 0) as total_revenue,
                    COALESCE(SUM(pm.cost), 0) as total_cost
                FROM ad_placements ap
                JOIN offers o ON ap.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                LEFT JOIN placement_metrics pm ON ap.placement_id = pm.placement_id
                WHERE u.telegram_id = ?
                AND pm.metric_date >= ?
            ''', (telegram_user_id, start_date))
            
            summary = cursor.fetchone()
            conn.close()
            
            if not summary:
                return {}
            
            total_views = summary['total_views'] or 0
            total_clicks = summary['total_clicks'] or 0
            total_conversions = summary['total_conversions'] or 0
            total_revenue = summary['total_revenue'] or 0
            total_cost = summary['total_cost'] or 0
            
            avg_ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
            avg_conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
            total_roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            
            return {
                'period_days': days,
                'total_placements': summary['total_placements'],
                'total_views': total_views,
                'total_clicks': total_clicks,
                'total_conversions': total_conversions,
                'total_revenue': float(total_revenue),
                'total_cost': float(total_cost),
                'avg_ctr': round(avg_ctr, 2),
                'avg_conversion_rate': round(avg_conversion_rate, 2),
                'total_roi': round(total_roi, 2),
                'avg_cost_per_click': round(total_cost / total_clicks, 2) if total_clicks > 0 else 0,
                'avg_revenue_per_conversion': round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки эффективности: {e}")
            return {}

# Функции для интеграции с основным приложением
def add_tracking_routes(app, db_path: str):
    """Добавление маршрутов отслеживания в Flask приложение"""
    
    from flask import request, jsonify, redirect
    
    tracker = PlacementTracker(db_path)
    
    @app.route('/track/<placement_id>/<event_type>')
    def track_placement_event(placement_id, event_type):
        """Эндпоинт для отслеживания событий размещений"""
        try:
            # Получаем данные о запросе
            user_agent = request.headers.get('User-Agent', '')
            ip_address = request.environ.get('REMOTE_ADDR', '')
            referrer = request.headers.get('Referer', '')
            
            # Дополнительные параметры
            conversion_value = request.args.get('value', type=float)
            
            # Отслеживаем событие
            success = tracker.track_event(
                placement_id=placement_id,
                event_type=event_type,
                user_agent=user_agent,
                ip_address=ip_address,
                referrer=referrer,
                conversion_value=conversion_value
            )
            
            if success:
                # Для кликов - редиректим на целевую страницу
                if event_type == 'click':
                    target_url = request.args.get('url')
                    if target_url:
                        return redirect(target_url)
                
                # Для просмотров - возвращаем прозрачный пиксель
                elif event_type == 'view':
                    response = app.response_class(
                        response='',
                        status=204,
                        headers={'Content-Type': 'image/gif'}
                    )
                    return response
                
                return jsonify({'status': 'ok'})
            else:
                return jsonify({'status': 'error'}), 400
                
        except Exception as e:
            logger.error(f"Tracking error: {e}")
            return jsonify({'status': 'error'}), 500
    
    @app.route('/api/placements/metrics/<placement_id>')
    def api_placement_metrics(placement_id):
        """API получения метрик размещения"""
        try:
            metrics = tracker.get_placement_metrics(placement_id)
            if metrics:
                return jsonify({
                    'success': True,
                    'metrics': {
                        'placement_id': metrics.placement_id,
                        'views': metrics.views,
                        'clicks': metrics.clicks,
                        'conversions': metrics.conversions,
                        'revenue': metrics.revenue,
                        'cost': metrics.cost,
                        'ctr': metrics.ctr,
                        'conversion_rate': metrics.conversion_rate,
                        'roi': metrics.roi
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Размещение не найдено'}), 404
                
        except Exception as e:
            logger.error(f"Placement metrics API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/placements/my')
    def api_my_placements():
        """API получения моих размещений"""
        try:
            from working_app import get_current_user_id  # Импорт из основного файла
            
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            limit = min(int(request.args.get('limit', 50)), 100)
            placements = tracker.get_user_placements(telegram_user_id, limit)
            
            return jsonify({
                'success': True,
                'placements': placements,
                'total': len(placements)
            })
            
        except Exception as e:
            logger.error(f"My placements API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/placements/summary')
    def api_placement_summary():
        """API получения сводки по эффективности"""
        try:
            from working_app import get_current_user_id
            
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            days = min(int(request.args.get('days', 30)), 365)
            summary = tracker.get_performance_summary(telegram_user_id, days)
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Placement summary API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

# Пример использования
def create_demo_placement(db_path: str):
    """Создание демо-размещения для тестирования"""
    tracker = PlacementTracker(db_path)
    
    # Создаем размещение
    placement_id = tracker.create_placement(
        offer_id=1, 
        channel_id=1,
        expires_at=datetime.now() + timedelta(days=7)
    )
    
    if placement_id:
        # Симулируем события
        import random
        import time
        
        # Просмотры
        for _ in range(random.randint(100, 500)):
            tracker.track_event(placement_id, 'view')
            time.sleep(0.01)  # Небольшая задержка
        
        # Клики
        for _ in range(random.randint(5, 25)):
            tracker.track_event(placement_id, 'click')
            time.sleep(0.01)
        
        # Конверсии
        for _ in range(random.randint(1, 5)):
            tracker.track_event(placement_id, 'conversion', conversion_value=random.uniform(100, 1000))
            time.sleep(0.01)
        
        logger.info(f"Создано демо-размещение {placement_id} с тестовыми данными")
        return placement_id
    
    return None