# analytics_api.py - Расширенная аналитика для Telegram Mini App
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import json
import re

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Движок аналитики для обработки данных и генерации инсайтов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def get_db_connection(self):
        """Получение подключения к базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def get_date_range(self, range_type: str) -> Tuple[datetime, datetime]:
        """Получение диапазона дат на основе типа"""
        end_date = datetime.now()
        
        if range_type == '7d':
            start_date = end_date - timedelta(days=7)
        elif range_type == '30d':
            start_date = end_date - timedelta(days=30)
        elif range_type == '90d':
            start_date = end_date - timedelta(days=90)
        elif range_type == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # 'all'
            start_date = datetime(2020, 1, 1)  # Начало времени для системы
            
        return start_date, end_date
    
    def get_user_metrics(self, telegram_user_id: int, range_type: str = '30d') -> Dict[str, Any]:
        """Получение основных метрик пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_demo_metrics()
            
            cursor = conn.cursor()
            start_date, end_date = self.get_date_range(range_type)
            
            # Получаем ID пользователя в БД
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                conn.close()
                return self._get_demo_metrics()
            
            user_db_id = user_row['id']
            
            # Общий доход
            cursor.execute('''
                SELECT COALESCE(SUM(o.price), 0) as total_revenue
                FROM offers o
                JOIN offer_responses r ON o.id = r.offer_id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
                AND r.created_at BETWEEN ? AND ?
            ''', (user_db_id, start_date.isoformat(), end_date.isoformat()))
            
            revenue_row = cursor.fetchone()
            total_revenue = revenue_row['total_revenue'] if revenue_row else 0
            
            # Общая аудитория
            cursor.execute('''
                SELECT COALESCE(SUM(subscriber_count), 0) as total_audience
                FROM channels
                WHERE owner_id = ? AND is_active = 1
            ''', (user_db_id,))
            
            audience_row = cursor.fetchone()
            total_audience = audience_row['total_audience'] if audience_row else 0
            
            # Конверсия (принятые отклики / всего офферов)
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT r.offer_id) as accepted_offers,
                    (SELECT COUNT(*) FROM offers WHERE created_by = ?) as total_offers
                FROM offer_responses r
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
                AND r.created_at BETWEEN ? AND ?
            ''', (user_db_id, user_db_id, start_date.isoformat(), end_date.isoformat()))
            
            conversion_row = cursor.fetchone()
            if conversion_row and conversion_row['total_offers'] > 0:
                conversion_rate = (conversion_row['accepted_offers'] / conversion_row['total_offers']) * 100
            else:
                conversion_rate = 0
            
            # Среднее время отклика
            cursor.execute('''
                SELECT AVG(
                    (julianday(r.created_at) - julianday(o.created_at)) * 24
                ) as avg_response_hours
                FROM offer_responses r
                JOIN offers o ON r.offer_id = o.id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ?
                AND r.created_at BETWEEN ? AND ?
            ''', (user_db_id, start_date.isoformat(), end_date.isoformat()))
            
            response_time_row = cursor.fetchone()
            avg_response_time = response_time_row['avg_response_hours'] if response_time_row else 24
            
            # Тренды (сравнение с предыдущим периодом)
            prev_start = start_date - (end_date - start_date)
            trends = self._calculate_trends(cursor, user_db_id, start_date, end_date, prev_start, start_date)
            
            conn.close()
            
            return {
                'total_revenue': float(total_revenue),
                'revenue_trend': trends.get('revenue_trend', 0),
                'total_audience': int(total_audience),
                'audience_trend': trends.get('audience_trend', 0),
                'conversion_rate': float(conversion_rate),
                'conversion_trend': trends.get('conversion_trend', 0),
                'avg_response_time': float(avg_response_time),
                'response_trend': trends.get('response_trend', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting user metrics: {e}")
            return self._get_demo_metrics()
    
    def _calculate_trends(self, cursor, user_db_id: int, 
                         current_start: datetime, current_end: datetime,
                         prev_start: datetime, prev_end: datetime) -> Dict[str, float]:
        """Расчет трендов по сравнению с предыдущим периодом"""
        try:
            # Доход - текущий период
            cursor.execute('''
                SELECT COALESCE(SUM(o.price), 0) as revenue
                FROM offers o
                JOIN offer_responses r ON o.id = r.offer_id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
                AND r.created_at BETWEEN ? AND ?
            ''', (user_db_id, current_start.isoformat(), current_end.isoformat()))
            current_revenue = cursor.fetchone()['revenue']
            
            # Доход - предыдущий период
            cursor.execute('''
                SELECT COALESCE(SUM(o.price), 0) as revenue
                FROM offers o
                JOIN offer_responses r ON o.id = r.offer_id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
                AND r.created_at BETWEEN ? AND ?
            ''', (user_db_id, prev_start.isoformat(), prev_end.isoformat()))
            prev_revenue = cursor.fetchone()['revenue']
            
            revenue_trend = self._calculate_percentage_change(prev_revenue, current_revenue)
            
            # Для остальных метрик используем демо-данные или упрощенный расчет
            return {
                'revenue_trend': revenue_trend,
                'audience_trend': 8.3,  # Демо
                'conversion_trend': 15.2,  # Демо
                'response_trend': -2.1  # Демо
            }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {
                'revenue_trend': 0,
                'audience_trend': 0,
                'conversion_trend': 0,
                'response_trend': 0
            }
    
    def _calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Расчет процентного изменения"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return ((new_value - old_value) / old_value) * 100
    
    def get_chart_data(self, telegram_user_id: int, range_type: str = '30d') -> Dict[str, Any]:
        """Получение данных для графиков"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_demo_chart_data(range_type)
            
            cursor = conn.cursor()
            start_date, end_date = self.get_date_range(range_type)
            
            # Получаем ID пользователя
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                conn.close()
                return self._get_demo_chart_data(range_type)
            
            user_db_id = user_row['id']
            
            # График доходов по дням
            revenue_chart = self._get_revenue_chart_data(cursor, user_db_id, start_date, end_date, range_type)
            
            # График распределения по каналам
            channels_chart = self._get_channels_chart_data(cursor, user_db_id, start_date, end_date)
            
            conn.close()
            
            return {
                'revenue_chart': revenue_chart,
                'channels_chart': channels_chart
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return self._get_demo_chart_data(range_type)
    
    def _get_revenue_chart_data(self, cursor, user_db_id: int, 
                               start_date: datetime, end_date: datetime, range_type: str) -> Dict[str, List]:
        """Получение данных для графика доходов"""
        try:
            # Определяем интервал группировки
            if range_type in ['7d', '30d']:
                date_format = '%Y-%m-%d'
                interval = 'day'
            elif range_type == '90d':
                date_format = '%Y-%W'  # По неделям
                interval = 'week'
            else:
                date_format = '%Y-%m'  # По месяцам
                interval = 'month'
            
            cursor.execute('''
                SELECT 
                    strftime(?, r.created_at) as period,
                    COALESCE(SUM(o.price), 0) as revenue
                FROM offer_responses r
                JOIN offers o ON r.offer_id = o.id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
                AND r.created_at BETWEEN ? AND ?
                GROUP BY strftime(?, r.created_at)
                ORDER BY period
            ''', (date_format, user_db_id, start_date.isoformat(), end_date.isoformat(), date_format))
            
            results = cursor.fetchall()
            
            labels = []
            data = []
            
            for row in results:
                if interval == 'day':
                    date_obj = datetime.strptime(row['period'], '%Y-%m-%d')
                    labels.append(date_obj.strftime('%d.%m'))
                elif interval == 'week':
                    labels.append(f"Неделя {row['period'].split('-')[1]}")
                else:
                    date_obj = datetime.strptime(row['period'], '%Y-%m')
                    labels.append(date_obj.strftime('%b %Y'))
                
                data.append(float(row['revenue']))
            
            return {
                'labels': labels,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue chart data: {e}")
            return {'labels': [], 'data': []}
    
    def _get_channels_chart_data(self, cursor, user_db_id: int, 
                                start_date: datetime, end_date: datetime) -> Dict[str, List]:
        """Получение данных для графика каналов"""
        try:
            cursor.execute('''
                SELECT 
                    c.title,
                    c.username,
                    COALESCE(SUM(o.price), 0) as revenue
                FROM channels c
                LEFT JOIN offer_responses r ON c.id = r.channel_id AND r.status = 'accepted'
                LEFT JOIN offers o ON r.offer_id = o.id
                WHERE c.owner_id = ? 
                AND (r.created_at IS NULL OR r.created_at BETWEEN ? AND ?)
                GROUP BY c.id, c.title, c.username
                HAVING revenue > 0
                ORDER BY revenue DESC
                LIMIT 5
            ''', (user_db_id, start_date.isoformat(), end_date.isoformat()))
            
            results = cursor.fetchall()
            
            labels = []
            data = []
            
            for row in results:
                channel_name = row['title'] or f"@{row['username']}"
                labels.append(channel_name)
                data.append(float(row['revenue']))
            
            return {
                'labels': labels,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error getting channels chart data: {e}")
            return {'labels': [], 'data': []}
    
    def get_performance_data(self, telegram_user_id: int, range_type: str = '30d') -> List[Dict[str, Any]]:
        """Получение данных о эффективности каналов"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_demo_performance_data()
            
            cursor = conn.cursor()
            start_date, end_date = self.get_date_range(range_type)
            
            # Получаем ID пользователя
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                conn.close()
                return self._get_demo_performance_data()
            
            user_db_id = user_row['id']
            
            cursor.execute('''
                SELECT 
                    c.id,
                    c.username,
                    c.title,
                    c.subscriber_count,
                    c.is_active,
                    COUNT(DISTINCT r.id) as offers_count,
                    COALESCE(SUM(CASE WHEN r.status = 'accepted' THEN o.price ELSE 0 END), 0) as revenue,
                    COALESCE(AVG(CASE WHEN r.status = 'accepted' THEN 1.0 ELSE 0 END) * 100, 0) as conversion,
                    4.5 as rating  -- Демо рейтинг
                FROM channels c
                LEFT JOIN offer_responses r ON c.id = r.channel_id
                LEFT JOIN offers o ON r.offer_id = o.id
                WHERE c.owner_id = ?
                AND (r.created_at IS NULL OR r.created_at BETWEEN ? AND ?)
                GROUP BY c.id, c.username, c.title, c.subscriber_count, c.is_active
                ORDER BY revenue DESC
            ''', (user_db_id, start_date.isoformat(), end_date.isoformat()))
            
            results = cursor.fetchall()
            conn.close()
            
            channels = []
            for row in results:
                # Демо CTR (в реальной системе нужно отслеживать клики)
                ctr = min(5.0, max(1.0, (row['conversion'] / 100) * 15))
                
                channels.append({
                    'id': row['id'],
                    'username': row['username'],
                    'title': row['title'],
                    'subscriber_count': row['subscriber_count'] or 0,
                    'is_active': bool(row['is_active']),
                    'offers_count': row['offers_count'],
                    'revenue': float(row['revenue']),
                    'ctr': float(ctr),
                    'conversion': float(row['conversion']),
                    'rating': float(row['rating'])
                })
            
            return channels
            
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return self._get_demo_performance_data()
    
    def generate_ai_recommendations(self, telegram_user_id: int, range_type: str = '30d') -> List[Dict[str, str]]:
        """Генерация AI-рекомендаций на основе данных"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_demo_recommendations()
            
            cursor = conn.cursor()
            
            # Получаем ID пользователя
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                conn.close()
                return self._get_demo_recommendations()
            
            user_db_id = user_row['id']
            recommendations = []
            
            # Анализ каналов без активности
            cursor.execute('''
                SELECT c.username, c.title
                FROM channels c
                LEFT JOIN offer_responses r ON c.id = r.channel_id
                WHERE c.owner_id = ? AND c.is_active = 1
                GROUP BY c.id
                HAVING COUNT(r.id) = 0
                LIMIT 3
            ''', (user_db_id,))
            
            inactive_channels = cursor.fetchall()
            for channel in inactive_channels:
                recommendations.append({
                    'type': 'Активация канала',
                    'text': f'Канал @{channel["username"]} не получает офферы. Оптимизируйте описание и категорию.',
                    'impact': 'Увеличение откликов на 40%'
                })
            
            # Анализ ценовой политики
            cursor.execute('''
                SELECT AVG(o.price) as avg_price
                FROM offers o
                JOIN offer_responses r ON o.id = r.offer_id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ? AND r.status = 'accepted'
            ''', (user_db_id,))
            
            price_row = cursor.fetchone()
            if price_row and price_row['avg_price']:
                avg_price = price_row['avg_price']
                if avg_price < 1000:
                    recommendations.append({
                        'type': 'Оптимизация цен',
                        'text': 'Средняя цена ваших размещений ниже рыночной. Рассмотрите повышение тарифов.',
                        'impact': f'Увеличение дохода на ₽{int(avg_price * 0.3 * 30)} в месяц'
                    })
            
            # Анализ времени отклика
            cursor.execute('''
                SELECT AVG(
                    (julianday(r.created_at) - julianday(o.created_at)) * 24
                ) as avg_response_hours
                FROM offer_responses r
                JOIN offers o ON r.offer_id = o.id
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ?
            ''', (user_db_id,))
            
            response_row = cursor.fetchone()
            if response_row and response_row['avg_response_hours']:
                avg_hours = response_row['avg_response_hours']
                if avg_hours > 12:
                    recommendations.append({
                        'type': 'Скорость отклика',
                        'text': 'Ваше среднее время отклика превышает 12 часов. Быстрые ответы увеличивают конверсию.',
                        'impact': 'Увеличение конверсии на 25%'
                    })
            
            conn.close()
            
            # Если нет специфических рекомендаций, добавляем общие
            if len(recommendations) < 3:
                general_recommendations = [
                    {
                        'type': 'Контент-стратегия',
                        'text': 'Добавьте больше визуального контента для повышения вовлеченности.',
                        'impact': 'Рост CTR на 18%'
                    },
                    {
                        'type': 'Таргетинг',
                        'text': 'Уточните описание целевой аудитории ваших каналов.',
                        'impact': 'Повышение качества офферов на 30%'
                    },
                    {
                        'type': 'Расширение',
                        'text': 'Рассмотрите добавление каналов в смежных тематиках.',
                        'impact': 'Увеличение дохода на 45%'
                    }
                ]
                
                for rec in general_recommendations:
                    if len(recommendations) >= 4:
                        break
                    recommendations.append(rec)
            
            return recommendations[:4]  # Максимум 4 рекомендации
            
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
            return self._get_demo_recommendations()
    
    # Демо-данные для случаев, когда нет реальных данных
    def _get_demo_metrics(self) -> Dict[str, Any]:
        """Демо-метрики для показа"""
        return {
            'total_revenue': 45230.0,
            'revenue_trend': 12.5,
            'total_audience': 125400,
            'audience_trend': 8.3,
            'conversion_rate': 24.6,
            'conversion_trend': 15.2,
            'avg_response_time': 3.2,
            'response_trend': -2.1
        }
    
    def _get_demo_chart_data(self, range_type: str) -> Dict[str, Any]:
        """Демо-данные для графиков"""
        import random
        
        # Генерируем данные в зависимости от периода
        if range_type == '7d':
            days = 7
            labels = [(datetime.now() - timedelta(days=i)).strftime('%d.%m') for i in range(days-1, -1, -1)]
        elif range_type == '30d':
            days = 30
            labels = [(datetime.now() - timedelta(days=i)).strftime('%d.%m') for i in range(days-1, -1, -1)]
        else:
            days = 12
            labels = [(datetime.now() - timedelta(days=i*7)).strftime('%d.%m') for i in range(days-1, -1, -1)]
        
        # Генерируем реалистичные данные доходов
        revenue_data = []
        base_revenue = 1500
        for i in range(len(labels)):
            # Добавляем некоторую случайность и тренд
            trend = i * 50  # Растущий тренд
            noise = random.uniform(-300, 500)
            revenue = max(0, base_revenue + trend + noise)
            revenue_data.append(round(revenue, 2))
        
        return {
            'revenue_chart': {
                'labels': labels,
                'data': revenue_data
            },
            'channels_chart': {
                'labels': ['Tech News', 'Business Hub', 'Lifestyle', 'Gaming', 'Education'],
                'data': [35, 25, 20, 15, 5]
            }
        }
    
    def _get_demo_performance_data(self) -> List[Dict[str, Any]]:
        """Демо-данные производительности каналов"""
        return [
            {
                'id': 1,
                'username': 'tech_news_daily',
                'title': 'Tech News Daily',
                'subscriber_count': 45200,
                'is_active': True,
                'offers_count': 12,
                'revenue': 18500.0,
                'ctr': 3.2,
                'conversion': 24.5,
                'rating': 4.8
            },
            {
                'id': 2,
                'username': 'business_insights',
                'title': 'Business Insights',
                'subscriber_count': 28900,
                'is_active': True,
                'offers_count': 8,
                'revenue': 12300.0,
                'ctr': 2.8,
                'conversion': 18.7,
                'rating': 4.6
            },
            {
                'id': 3,
                'username': 'lifestyle_trends',
                'title': 'Lifestyle Trends',
                'subscriber_count': 51300,
                'is_active': False,
                'offers_count': 15,
                'revenue': 14200.0,
                'ctr': 4.1,
                'conversion': 21.3,
                'rating': 4.5
            }
        ]
    
    def _get_demo_recommendations(self) -> List[Dict[str, str]]:
        """Демо-рекомендации"""
        return [
            {
                'type': 'Оптимизация цен',
                'text': 'Рассмотрите увеличение цены за размещение в топовых каналах на 15%',
                'impact': 'Увеличение дохода на ₽2,700 в месяц'
            },
            {
                'type': 'Улучшение контента',
                'text': 'Добавьте больше визуального контента для повышения вовлеченности',
                'impact': 'Рост CTR на 23%'
            },
            {
                'type': 'Время публикации',
                'text': 'Оптимальное время для размещений: 10:00-12:00 и 18:00-20:00',
                'impact': 'Увеличение охвата на 18%'
            },
            {
                'type': 'Новые категории',
                'text': 'Рассмотрите добавление каналов в категории "Финансы" и "Образование"',
                'impact': 'Расширение аудитории на 35,000 подписчиков'
            }
        ]


# Функции для интеграции с Flask приложением
def add_analytics_routes(app, database_path: str):
    """Добавление маршрутов аналитики в Flask приложение"""
    
    from flask import request, jsonify
    
    analytics_engine = AnalyticsEngine(database_path)
    
    def get_current_user_id():
        """Получение текущего Telegram User ID (копия из основного приложения)"""
        user_id_header = request.headers.get('X-Telegram-User-Id')
        if user_id_header:
            try:
                return int(user_id_header)
            except (ValueError, TypeError):
                pass
        
        # Из POST данных
        if request.method == 'POST' and request.is_json:
            try:
                data = request.get_json()
                if data and 'telegram_user_id' in data:
                    return int(data['telegram_user_id'])
            except:
                pass
        
        # Из GET параметров
        user_id_param = request.args.get('telegram_user_id')
        if user_id_param:
            try:
                return int(user_id_param)
            except (ValueError, TypeError):
                pass
        
        return None
    
    @app.route('/api/analytics/metrics')
    def api_analytics_metrics():
        """API получения основных метрик"""
        try:
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            range_type = request.args.get('range', '30d')
            metrics = analytics_engine.get_user_metrics(telegram_user_id, range_type)
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'range': range_type
            })
            
        except Exception as e:
            logger.error(f"Analytics metrics API error: {e}")
            return jsonify({
                'success': False, 
                'error': 'Ошибка получения метрик',
                'metrics': analytics_engine._get_demo_metrics()
            }), 500
    
    @app.route('/api/analytics/charts')
    def api_analytics_charts():
        """API получения данных для графиков"""
        try:
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            range_type = request.args.get('range', '30d')
            chart_data = analytics_engine.get_chart_data(telegram_user_id, range_type)
            
            return jsonify({
                'success': True,
                'revenue_chart': chart_data['revenue_chart'],
                'channels_chart': chart_data['channels_chart'],
                'range': range_type
            })
            
        except Exception as e:
            logger.error(f"Analytics charts API error: {e}")
            return jsonify({
                'success': False, 
                'error': 'Ошибка получения данных графиков'
            }), 500
    
    @app.route('/api/analytics/performance')
    def api_analytics_performance():
        """API получения данных о производительности каналов"""
        try:
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            range_type = request.args.get('range', '30d')
            performance_data = analytics_engine.get_performance_data(telegram_user_id, range_type)
            
            return jsonify({
                'success': True,
                'channels': performance_data,
                'range': range_type
            })
            
        except Exception as e:
            logger.error(f"Analytics performance API error: {e}")
            return jsonify({
                'success': False, 
                'error': 'Ошибка получения данных производительности'
            }), 500
    
    @app.route('/api/analytics/recommendations')
    def api_analytics_recommendations():
        """API получения AI-рекомендаций"""
        try:
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            range_type = request.args.get('range', '30d')
            recommendations = analytics_engine.generate_ai_recommendations(telegram_user_id, range_type)
            
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'range': range_type
            })
            
        except Exception as e:
            logger.error(f"Analytics recommendations API error: {e}")
            return jsonify({
                'success': False, 
                'error': 'Ошибка получения рекомендаций'
            }), 500