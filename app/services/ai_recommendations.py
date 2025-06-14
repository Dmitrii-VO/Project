# ai_recommendations.py - Продвинутая система AI-рекомендаций для оптимизации
import os
import sqlite3
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

@dataclass
class Recommendation:
    """Структура рекомендации"""
    id: str
    type: str  # 'pricing', 'content', 'timing', 'targeting', 'expansion'
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    impact_description: str
    estimated_impact: Dict[str, float]  # Ожидаемые изменения метрик
    action_items: List[str]  # Конкретные шаги для выполнения
    confidence: float  # Уверенность в рекомендации (0-100%)
    data_source: str  # Источник данных для рекомендации
    created_at: datetime

class AIRecommendationEngine:
    """Движок AI-рекомендаций для оптимизации рекламных кампаний"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.recommendation_rules = self._load_recommendation_rules()
    
    def get_db_connection(self):
        """Получение подключения к базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def _load_recommendation_rules(self) -> Dict[str, Any]:
        """Загрузка правил для генерации рекомендаций"""
        return {
            'pricing': {
                'low_roi_threshold': 50,  # ROI менее 50%
                'high_roi_threshold': 200,  # ROI более 200%
                'market_price_deviation': 0.3  # Отклонение от рыночной цены на 30%
            },
            'content': {
                'low_ctr_threshold': 1.0,  # CTR менее 1%
                'low_engagement_threshold': 0.5,  # Вовлеченность менее 0.5%
                'content_length_optimal': (50, 200)  # Оптимальная длина контента
            },
            'timing': {
                'response_time_threshold': 12,  # Время отклика более 12 часов
                'optimal_posting_hours': [(9, 12), (18, 21)],  # Оптимальные часы для постинга
                'peak_days': [1, 2, 3, 4]  # Пн-Чт - пиковые дни
            },
            'targeting': {
                'low_conversion_threshold': 2.0,  # Конверсия менее 2%
                'audience_overlap_threshold': 0.7,  # Пересечение аудиторий более 70%
                'category_performance_threshold': 0.8  # Производительность категории
            },
            'expansion': {
                'channel_count_threshold': 3,  # Менее 3 каналов
                'category_diversification': 0.6,  # Диверсификация по категориям
                'growth_opportunity_threshold': 1000  # Потенциал роста аудитории
            }
        }
    
    def generate_recommendations(self, telegram_user_id: int, days: int = 30) -> List[Recommendation]:
        """Генерация персональных рекомендаций для пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_fallback_recommendations()
            
            # Получаем данные пользователя
            user_data = self._get_user_analytics_data(conn, telegram_user_id, days)
            
            recommendations = []
            
            # Анализируем ценообразование
            pricing_recs = self._analyze_pricing(conn, telegram_user_id, user_data)
            recommendations.extend(pricing_recs)
            
            # Анализируем контент
            content_recs = self._analyze_content_performance(conn, telegram_user_id, user_data)
            recommendations.extend(content_recs)
            
            # Анализируем тайминг
            timing_recs = self._analyze_timing_optimization(conn, telegram_user_id, user_data)
            recommendations.extend(timing_recs)
            
            # Анализируем таргетинг
            targeting_recs = self._analyze_targeting_efficiency(conn, telegram_user_id, user_data)
            recommendations.extend(targeting_recs)
            
            # Анализируем возможности расширения
            expansion_recs = self._analyze_expansion_opportunities(conn, telegram_user_id, user_data)
            recommendations.extend(expansion_recs)
            
            conn.close()
            
            # Сортируем по приоритету и уверенности
            recommendations.sort(key=lambda x: (
                {'high': 3, 'medium': 2, 'low': 1}[x.priority],
                x.confidence
            ), reverse=True)
            
            return recommendations[:6]  # Возвращаем топ-6 рекомендаций
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._get_fallback_recommendations()
    
    def _get_user_analytics_data(self, conn, telegram_user_id: int, days: int) -> Dict[str, Any]:
        """Получение аналитических данных пользователя"""
        cursor = conn.cursor()
        
        # Получаем ID пользователя в БД
        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return {}
        
        user_db_id = user_row['id']
        start_date = datetime.now() - timedelta(days=days)
        
        # Основные метрики
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT c.id) as channel_count,
                COUNT(DISTINCT o.id) as offer_count,
                COUNT(DISTINCT r.id) as response_count,
                COALESCE(AVG(o.price), 0) as avg_price,
                COALESCE(SUM(CASE WHEN r.status = 'accepted' THEN o.price ELSE 0 END), 0) as total_revenue,
                COALESCE(AVG(c.subscriber_count), 0) as avg_subscribers
            FROM users u
            LEFT JOIN channels c ON u.id = c.owner_id
            LEFT JOIN offers o ON u.id = o.created_by
            LEFT JOIN offer_responses r ON o.id = r.offer_id
            WHERE u.id = ? AND o.created_at >= ?
        ''', (user_db_id, start_date.isoformat()))
        
        metrics = cursor.fetchone()
        
        # Анализ категорий каналов
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM channels
            WHERE owner_id = ? AND is_active = 1
            GROUP BY category
        ''', (user_db_id,))
        
        categories = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Анализ времени откликов
        cursor.execute('''
            SELECT AVG(
                (julianday(r.created_at) - julianday(o.created_at)) * 24
            ) as avg_response_hours
            FROM offer_responses r
            JOIN offers o ON r.offer_id = o.id
            JOIN channels c ON r.channel_id = c.id
            WHERE c.owner_id = ? AND r.created_at >= ?
        ''', (user_db_id, start_date.isoformat()))
        
        response_time_row = cursor.fetchone()
        avg_response_hours = response_time_row['avg_response_hours'] if response_time_row else 24
        
        return {
            'user_db_id': user_db_id,
            'channel_count': metrics['channel_count'] or 0,
            'offer_count': metrics['offer_count'] or 0,
            'response_count': metrics['response_count'] or 0,
            'avg_price': float(metrics['avg_price']) if metrics['avg_price'] else 0,
            'total_revenue': float(metrics['total_revenue']) if metrics['total_revenue'] else 0,
            'avg_subscribers': int(metrics['avg_subscribers']) if metrics['avg_subscribers'] else 0,
            'categories': categories,
            'avg_response_hours': float(avg_response_hours) if avg_response_hours else 24,
            'conversion_rate': (metrics['response_count'] / metrics['offer_count'] * 100) if metrics['offer_count'] > 0 else 0
        }
    
    def _analyze_pricing(self, conn, telegram_user_id: int, user_data: Dict) -> List[Recommendation]:
        """Анализ ценообразования"""
        recommendations = []
        cursor = conn.cursor()
        
        try:
            # Анализ ROI
            if user_data.get('total_revenue', 0) > 0:
                # Примерный расчет ROI (в реальности нужны данные о затратах)
                estimated_costs = user_data['total_revenue'] * 0.3  # Предполагаем 30% затрат
                roi = ((user_data['total_revenue'] - estimated_costs) / estimated_costs) * 100
                
                if roi < self.recommendation_rules['pricing']['low_roi_threshold']:
                    recommendations.append(Recommendation(
                        id='pricing_low_roi',
                        type='pricing',
                        priority='high',
                        title='Низкий ROI рекламных размещений',
                        description=f'Ваш ROI составляет {roi:.1f}%, что ниже рекомендуемых {self.recommendation_rules["pricing"]["low_roi_threshold"]}%',
                        impact_description='Увеличение дохода на 25-40%',
                        estimated_impact={'revenue': 25, 'roi': 30},
                        action_items=[
                            'Пересмотрите ценообразование для топовых каналов',
                            'Проанализируйте конкурентов в вашей нише',
                            'Добавьте премиум-опции размещения',
                            'Оптимизируйте таргетинг для повышения конверсии'
                        ],
                        confidence=85.0,
                        data_source='Анализ ROI за последние 30 дней',
                        created_at=datetime.now()
                    ))
            
            # Анализ средней цены по сравнению с рынком
            cursor.execute('''
                SELECT AVG(price) as market_avg_price
                FROM offers o
                JOIN users u ON o.created_by = u.id
                WHERE u.telegram_id != ? AND o.created_at >= ?
            ''', (telegram_user_id, (datetime.now() - timedelta(days=30)).isoformat()))
            
            market_data = cursor.fetchone()
            if market_data and market_data['market_avg_price']:
                market_avg = float(market_data['market_avg_price'])
                user_avg = user_data.get('avg_price', 0)
                
                if user_avg > 0:
                    price_ratio = user_avg / market_avg
                    
                    if price_ratio < (1 - self.recommendation_rules['pricing']['market_price_deviation']):
                        recommendations.append(Recommendation(
                            id='pricing_below_market',
                            type='pricing',
                            priority='medium',
                            title='Цены ниже рыночных',
                            description=f'Ваши цены на {(1-price_ratio)*100:.1f}% ниже среднерыночных',
                            impact_description=f'Увеличение дохода на ₽{int((market_avg - user_avg) * user_data.get("offer_count", 1) * 30)} в месяц',
                            estimated_impact={'revenue': (1/price_ratio - 1) * 100, 'price': (market_avg - user_avg) / user_avg * 100},
                            action_items=[
                                f'Увеличьте базовые тарифы до ₽{market_avg:.0f}',
                                'Добавьте дополнительные услуги (срочность, гарантии)',
                                'Создайте пакетные предложения',
                                'Обоснуйте стоимость качеством аудитории'
                            ],
                            confidence=75.0,
                            data_source='Сравнение с рыночными ценами',
                            created_at=datetime.now()
                        ))
            
        except Exception as e:
            logger.error(f"Pricing analysis error: {e}")
        
        return recommendations
    
    def _analyze_content_performance(self, conn, telegram_user_id: int, user_data: Dict) -> List[Recommendation]:
        """Анализ эффективности контента"""
        recommendations = []
        cursor = conn.cursor()
        
        try:
            # Анализ длины описаний офферов
            cursor.execute('''
                SELECT 
                    AVG(LENGTH(description)) as avg_desc_length,
                    AVG(LENGTH(content)) as avg_content_length,
                    COUNT(*) as total_offers
                FROM offers o
                JOIN users u ON o.created_by = u.id
                WHERE u.telegram_id = ?
            ''', (telegram_user_id,))
            
            content_data = cursor.fetchone()
            
            if content_data and content_data['total_offers'] > 0:
                avg_desc_length = content_data['avg_desc_length'] or 0
                avg_content_length = content_data['avg_content_length'] or 0
                
                optimal_min, optimal_max = self.recommendation_rules['content']['content_length_optimal']
                
                if avg_content_length < optimal_min or avg_content_length > optimal_max:
                    status = 'короткий' if avg_content_length < optimal_min else 'длинный'
                    recommendations.append(Recommendation(
                        id='content_length_optimization',
                        type='content',
                        priority='medium',
                        title=f'Оптимизация длины контента',
                        description=f'Ваш контент в среднем {status} ({avg_content_length:.0f} символов)',
                        impact_description='Увеличение CTR на 15-25%',
                        estimated_impact={'ctr': 20, 'engagement': 15},
                        action_items=[
                            f'Стремитесь к длине {optimal_min}-{optimal_max} символов',
                            'Используйте структурированный текст с заголовками',
                            'Добавляйте призывы к действию',
                            'Включайте эмодзи для визуального разнообразия'
                        ],
                        confidence=70.0,
                        data_source='Анализ длины контента',
                        created_at=datetime.now()
                    ))
            
            # Анализ использования ключевых слов
            cursor.execute('''
                SELECT title, description, content
                FROM offers o
                JOIN users u ON o.created_by = u.id
                WHERE u.telegram_id = ?
                ORDER BY o.created_at DESC
                LIMIT 10
            ''', (telegram_user_id,))
            
            recent_offers = cursor.fetchall()
            
            if recent_offers:
                # Простой анализ ключевых слов
                all_text = ' '.join([
                    (offer['title'] or '') + ' ' + (offer['description'] or '') + ' ' + (offer['content'] or '')
                    for offer in recent_offers
                ])
                
                # Подсчет упоминаний продающих слов
                selling_words = ['скидка', 'акция', 'выгода', 'эксклюзив', 'бесплатно', 'новинка', 'лимитированный']
                urgency_words = ['срочно', 'сегодня', 'ограниченное время', 'только сейчас']
                
                selling_count = sum(all_text.lower().count(word) for word in selling_words)
                urgency_count = sum(all_text.lower().count(word) for word in urgency_words)
                
                if selling_count < 2 or urgency_count < 1:
                    recommendations.append(Recommendation(
                        id='content_keywords_optimization',
                        type='content',
                        priority='medium',
                        title='Недостаточно продающих элементов',
                        description='В ваших офферах мало триггеров действия и создания срочности',
                        impact_description='Увеличение конверсии на 20-30%',
                        estimated_impact={'conversion': 25, 'response_rate': 20},
                        action_items=[
                            'Добавляйте слова, создающие срочность',
                            'Используйте конкретные выгоды и преимущества',
                            'Включайте социальные доказательства',
                            'Добавляйте гарантии и обещания'
                        ],
                        confidence=65.0,
                        data_source='Анализ ключевых слов в контенте',
                        created_at=datetime.now()
                    ))
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
        
        return recommendations
    
    def _analyze_timing_optimization(self, conn, telegram_user_id: int, user_data: Dict) -> List[Recommendation]:
        """Анализ оптимизации тайминга"""
        recommendations = []
        
        try:
            # Анализ времени отклика
            avg_response_hours = user_data.get('avg_response_hours', 24)
            threshold = self.recommendation_rules['timing']['response_time_threshold']
            
            if avg_response_hours > threshold:
                recommendations.append(Recommendation(
                    id='timing_response_speed',
                    type='timing',
                    priority='high',
                    title='Медленный отклик на офферы',
                    description=f'Ваше среднее время отклика составляет {avg_response_hours:.1f} часов',
                    impact_description='Увеличение конверсии на 25-35%',
                    estimated_impact={'conversion': 30, 'response_rate': 25},
                    action_items=[
                        'Настройте push-уведомления для новых офферов',
                        'Создайте шаблоны ответов для быстрой реакции',
                        'Проверяйте офферы минимум 3 раза в день',
                        'Рассмотрите автоматические отклики'
                    ],
                    confidence=90.0,
                    data_source='Анализ времени откликов',
                    created_at=datetime.now()
                ))
            
            # Анализ активности по дням недели
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    strftime('%w', r.created_at) as day_of_week,
                    COUNT(*) as response_count
                FROM offer_responses r
                JOIN channels c ON r.channel_id = c.id
                JOIN users u ON c.owner_id = u.id
                WHERE u.telegram_id = ?
                GROUP BY strftime('%w', r.created_at)
            ''', (telegram_user_id,))
            
            day_activity = {int(row['day_of_week']): row['response_count'] for row in cursor.fetchall()}
            
            if day_activity:
                # Анализ распределения активности
                weekday_activity = sum(day_activity.get(i, 0) for i in range(1, 6))  # Пн-Пт
                weekend_activity = sum(day_activity.get(i, 0) for i in [0, 6])  # Сб-Вс
                
                total_activity = weekday_activity + weekend_activity
                if total_activity > 0:
                    weekday_ratio = weekday_activity / total_activity
                    
                    if weekday_ratio < 0.7:  # Менее 70% активности в будни
                        recommendations.append(Recommendation(
                            id='timing_weekday_focus',
                            type='timing',
                            priority='medium',
                            title='Недостаточная активность в будни',
                            description=f'Только {weekday_ratio*100:.1f}% активности приходится на рабочие дни',
                            impact_description='Увеличение количества качественных офферов на 40%',
                            estimated_impact={'offer_quality': 40, 'response_rate': 20},
                            action_items=[
                                'Увеличьте активность в понедельник-четверг',
                                'Размещайте офферы в рабочие часы (9:00-18:00)',
                                'Настройте напоминания для проверки новых предложений',
                                'Фокусируйтесь на B2B сегменте в будни'
                            ],
                            confidence=75.0,
                            data_source='Анализ активности по дням недели',
                            created_at=datetime.now()
                        ))
            
        except Exception as e:
            logger.error(f"Timing analysis error: {e}")
        
        return recommendations
    
    def _analyze_targeting_efficiency(self, conn, telegram_user_id: int, user_data: Dict) -> List[Recommendation]:
        """Анализ эффективности таргетинга"""
        recommendations = []
        cursor = conn.cursor()
        
        try:
            # Анализ конверсии по категориям
            cursor.execute('''
                SELECT 
                    c.category,
                    COUNT(DISTINCT r.id) as responses,
                    COUNT(DISTINCT o.id) as offers,
                    CASE WHEN COUNT(DISTINCT o.id) > 0 
                         THEN CAST(COUNT(DISTINCT r.id) AS FLOAT) / COUNT(DISTINCT o.id) * 100
                         ELSE 0 END as conversion_rate
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                LEFT JOIN offer_responses r ON c.id = r.channel_id
                LEFT JOIN offers o ON r.offer_id = o.id
                WHERE u.telegram_id = ? AND c.category IS NOT NULL
                GROUP BY c.category
                HAVING COUNT(DISTINCT o.id) > 0
            ''', (telegram_user_id,))
            
            category_performance = cursor.fetchall()
            
            if category_performance:
                best_category = max(category_performance, key=lambda x: x['conversion_rate'])
                worst_category = min(category_performance, key=lambda x: x['conversion_rate'])
                
                if best_category['conversion_rate'] > worst_category['conversion_rate'] * 2:
                    recommendations.append(Recommendation(
                        id='targeting_category_focus',
                        type='targeting',
                        priority='high',
                        title='Неэффективное распределение по категориям',
                        description=f'Категория "{best_category["category"]}" показывает в 2+ раза лучшие результаты',
                        impact_description=f'Увеличение общей конверсии на {(best_category["conversion_rate"] - worst_category["conversion_rate"]):.1f}%',
                        estimated_impact={'conversion': (best_category["conversion_rate"] - worst_category["conversion_rate"]), 'revenue': 30},
                        action_items=[
                            f'Сфокусируйтесь на категории "{best_category["category"]}"',
                            f'Рассмотрите закрытие или оптимизацию категории "{worst_category["category"]}"',
                            'Изучите успешные паттерны лучшей категории',
                            'Перераспределите усилия в пользу эффективных направлений'
                        ],
                        confidence=80.0,
                        data_source='Сравнительный анализ категорий',
                        created_at=datetime.now()
                    ))
            
            # Анализ размера аудитории каналов
            cursor.execute('''
                SELECT 
                    AVG(subscriber_count) as avg_subscribers,
                    MIN(subscriber_count) as min_subscribers,
                    MAX(subscriber_count) as max_subscribers,
                    COUNT(*) as channel_count
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE u.telegram_id = ? AND c.is_active = 1
            ''', (telegram_user_id,))
            
            audience_data = cursor.fetchone()
            
            if audience_data and audience_data['channel_count'] > 1:
                if audience_data['max_subscribers'] > audience_data['min_subscribers'] * 10:
                    recommendations.append(Recommendation(
                        id='targeting_audience_balance',
                        type='targeting',
                        priority='medium',
                        title='Несбалансированность аудитории каналов',
                        description='Большой разброс в размерах аудитории ваших каналов',
                        impact_description='Более стабильный доход и предсказуемость результатов',
                        estimated_impact={'stability': 40, 'predictability': 35},
                        action_items=[
                            'Развивайте мелкие каналы до среднего размера',
                            'Создайте каналы среднего размера (10K-50K подписчиков)',
                            'Диверсифицируйте портфель каналов',
                            'Установите минимальные требования к размеру аудитории'
                        ],
                        confidence=70.0,
                        data_source='Анализ распределения аудитории',
                        created_at=datetime.now()
                    ))
            
        except Exception as e:
            logger.error(f"Targeting analysis error: {e}")
        
        return recommendations
    
    def _analyze_expansion_opportunities(self, conn, telegram_user_id: int, user_data: Dict) -> List[Recommendation]:
        """Анализ возможностей расширения"""
        recommendations = []
        cursor = conn.cursor()
        
        try:
            channel_count = user_data.get('channel_count', 0)
            
            # Рекомендация по количеству каналов
            if channel_count < self.recommendation_rules['expansion']['channel_count_threshold']:
                potential_revenue = 15000 * (3 - channel_count)  # Примерный доход с канала
                
                recommendations.append(Recommendation(
                    id='expansion_channel_count',
                    type='expansion',
                    priority='high',
                    title='Недостаточно каналов для масштабирования',
                    description=f'У вас только {channel_count} каналов. Рекомендуется минимум 3-5 для стабильного дохода',
                    impact_description=f'Потенциальное увеличение дохода на ₽{potential_revenue:,.0f} в месяц',
                    estimated_impact={'revenue': potential_revenue/1000, 'stability': 50},
                    action_items=[
                        'Создайте 2-3 дополнительных канала в смежных тематиках',
                        'Рассмотрите покупку готовых каналов',
                        'Изучите наиболее прибыльные ниши',
                        'Начните с одного канала и масштабируйте успешную модель'
                    ],
                    confidence=85.0,
                    data_source='Анализ портфеля каналов',
                    created_at=datetime.now()
                ))
            
            # Анализ диверсификации по категориям
            categories = user_data.get('categories', {})
            if len(categories) <= 1 and channel_count > 1:
                recommendations.append(Recommendation(
                    id='expansion_diversification',
                    type='expansion',
                    priority='medium',
                    title='Низкая диверсификация по тематикам',
                    description='Все ваши каналы сконцентрированы в одной категории',
                    impact_description='Снижение рисков на 40% и увеличение охвата аудитории',
                    estimated_impact={'risk_reduction': 40, 'audience_growth': 25},
                    action_items=[
                        'Добавьте каналы в смежных тематиках',
                        'Изучите спрос в категориях "Финансы", "Образование", "Технологии"',
                        'Протестируйте новые ниши с минимальными вложениями',
                        'Создайте каналы для разных демографических групп'
                    ],
                    confidence=75.0,
                    data_source='Анализ тематического разнообразия',
                    created_at=datetime.now()
                ))
            
            # Анализ потенциала роста аудитории
            cursor.execute('''
                SELECT SUM(subscriber_count) as total_audience
                FROM channels c
                JOIN users u ON c.owner_id = u.id
                WHERE u.telegram_id = ? AND c.is_active = 1
            ''', (telegram_user_id,))
            
            audience_data = cursor.fetchone()
            total_audience = audience_data['total_audience'] if audience_data else 0
            
            if total_audience < self.recommendation_rules['expansion']['growth_opportunity_threshold']:
                growth_potential = 50000 - total_audience
                
                recommendations.append(Recommendation(
                    id='expansion_audience_growth',
                    type='expansion',
                    priority='medium',
                    title='Потенциал роста аудитории',
                    description=f'Ваша общая аудитория составляет {total_audience:,} подписчиков',
                    impact_description=f'Потенциал роста до {growth_potential:,} дополнительных подписчиков',
                    estimated_impact={'audience_growth': growth_potential/1000, 'revenue': growth_potential/100},
                    action_items=[
                        'Инвестируйте в продвижение существующих каналов',
                        'Запустите cross-promotion между каналами',
                        'Создайте вирусный контент для органического роста',
                        'Рассмотрите партнерства с другими каналами'
                    ],
                    confidence=70.0,
                    data_source='Анализ потенциала роста',
                    created_at=datetime.now()
                ))
            
        except Exception as e:
            logger.error(f"Expansion analysis error: {e}")
        
        return recommendations
    
    def _get_fallback_recommendations(self) -> List[Recommendation]:
        """Fallback рекомендации при отсутствии данных"""
        return [
            Recommendation(
                id='general_start',
                type='expansion',
                priority='high',
                title='Начните с основ',
                description='Добавьте первый канал и создайте качественное описание',
                impact_description='Создание базы для будущего дохода',
                estimated_impact={'setup': 100},
                action_items=[
                    'Добавьте ваш первый Telegram канал',
                    'Заполните подробное описание и категорию',
                    'Установите конкурентные цены',
                    'Активно ищите первые офферы'
                ],
                confidence=100.0,
                data_source='Базовые рекомендации',
                created_at=datetime.now()
            ),
            Recommendation(
                id='general_optimization',
                type='content',
                priority='medium',
                title='Оптимизируйте контент',
                description='Качественный контент - основа успешных размещений',
                impact_description='Увеличение привлекательности для рекламодателей',
                estimated_impact={'attractiveness': 50},
                action_items=[
                    'Используйте качественные изображения',
                    'Пишите понятные и информативные описания',
                    'Добавляйте статистику и достижения',
                    'Регулярно обновляйте информацию о канале'
                ],
                confidence=90.0,
                data_source='Общие рекомендации',
                created_at=datetime.now()
            )
        ]

def add_ai_recommendation_routes(app, db_path: str):
    """Добавление API маршрутов для AI-рекомендаций"""
    
    from flask import request, jsonify
    
    ai_engine = AIRecommendationEngine(db_path)
    
    @app.route('/api/ai/recommendations')
    def api_ai_recommendations():
        """API получения AI-рекомендаций"""
        try:
            # Импортируем функцию получения пользователя
            from working_app import get_current_user_id
            
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            days = min(int(request.args.get('days', 30)), 90)
            recommendations = ai_engine.generate_recommendations(telegram_user_id, days)
            
            # Конвертируем в JSON-совместимый формат
            recommendations_data = []
            for rec in recommendations:
                recommendations_data.append({
                    'id': rec.id,
                    'type': rec.type,
                    'priority': rec.priority,
                    'title': rec.title,
                    'description': rec.description,
                    'impact_description': rec.impact_description,
                    'estimated_impact': rec.estimated_impact,
                    'action_items': rec.action_items,
                    'confidence': rec.confidence,
                    'data_source': rec.data_source,
                    'created_at': rec.created_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'recommendations': recommendations_data,
                'total': len(recommendations_data),
                'analysis_period_days': days
            })
            
        except Exception as e:
            logger.error(f"AI recommendations API error: {e}")
            return jsonify({
                'success': False,
                'error': 'Ошибка генерации рекомендаций',
                'recommendations': []
            }), 500
    
    @app.route('/api/ai/insights')
    def api_ai_insights():
        """API получения AI-инсайтов"""
        try:
            from working_app import get_current_user_id
            
            telegram_user_id = get_current_user_id()
            if not telegram_user_id:
                return jsonify({'success': False, 'error': 'Не авторизован'}), 401
            
            # Получаем краткие инсайты
            conn = ai_engine.get_db_connection()
            if not conn:
                return jsonify({'success': False, 'error': 'Ошибка БД'}), 500
            
            user_data = ai_engine._get_user_analytics_data(conn, telegram_user_id, 30)
            conn.close()
            
            insights = {
                'performance_score': min(100, max(0, 
                    (user_data.get('conversion_rate', 0) * 2) + 
                    (user_data.get('channel_count', 0) * 10) +
                    (50 if user_data.get('avg_response_hours', 24) < 12 else 20)
                )),
                'top_strength': ai_engine._identify_top_strength(user_data),
                'main_opportunity': ai_engine._identify_main_opportunity(user_data),
                'quick_wins': ai_engine._get_quick_wins(user_data)
            }
            
            return jsonify({
                'success': True,
                'insights': insights
            })
            
        except Exception as e:
            logger.error(f"AI insights API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Добавляем вспомогательные методы в класс AIRecommendationEngine
    def _identify_top_strength(self, user_data: Dict) -> str:
        """Определение главной силы пользователя"""
        if user_data.get('avg_response_hours', 24) < 6:
            return 'Быстрые отклики на офферы'
        elif user_data.get('channel_count', 0) >= 5:
            return 'Диверсифицированный портфель каналов'
        elif user_data.get('conversion_rate', 0) > 20:
            return 'Высокая конверсия размещений'
        else:
            return 'Стабильное развитие'
    
    def _identify_main_opportunity(self, user_data: Dict) -> str:
        """Определение главной возможности"""
        if user_data.get('channel_count', 0) < 3:
            return 'Масштабирование количества каналов'
        elif user_data.get('avg_response_hours', 24) > 12:
            return 'Ускорение реакции на офферы'
        elif len(user_data.get('categories', {})) <= 1:
            return 'Диверсификация по тематикам'
        else:
            return 'Оптимизация ценообразования'
    
    def _get_quick_wins(self, user_data: Dict) -> List[str]:
        """Получение быстрых побед"""
        wins = []
        
        if user_data.get('avg_response_hours', 24) > 6:
            wins.append('Настройте уведомления для быстрых откликов')
        
        if user_data.get('channel_count', 0) < 5:
            wins.append('Добавьте еще 1-2 канала в смежных тематиках')
        
        if user_data.get('avg_price', 0) < 1000:
            wins.append('Поднимите цены на 15-20%')
        
        return wins[:3]  # Максимум 3 быстрые победы
    
    # Привязываем методы к классу
    ai_engine._identify_top_strength = lambda user_data: _identify_top_strength(ai_engine, user_data)
    ai_engine._identify_main_opportunity = lambda user_data: _identify_main_opportunity(ai_engine, user_data)
    ai_engine._get_quick_wins = lambda user_data: _get_quick_wins(ai_engine, user_data)