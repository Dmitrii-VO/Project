"""
Smart Channel Recommendations API
Интеллектуальная система рекомендаций каналов для офферов
"""

import logging
import math
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app.models.database import execute_db_query
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
smart_recommendations_bp = Blueprint('smart_recommendations', __name__)

class IntelligentChannelMatcher:
    """Интеллектуальная система подбора каналов"""
    
    def __init__(self):
        self.category_weights = {
            'tech': ['технология', 'IT', 'программирование', 'разработка', 'стартап'],
            'business': ['бизнес', 'предпринимательство', 'инвестиции', 'финансы'],
            'lifestyle': ['образ жизни', 'мотивация', 'саморазвитие', 'психология'],
            'entertainment': ['развлечения', 'юмор', 'кино', 'музыка', 'игры'],
            'education': ['образование', 'обучение', 'курсы', 'университет'],
            'health': ['здоровье', 'фитнес', 'медицина', 'спорт'],
            'travel': ['путешествия', 'туризм', 'отдых', 'страны'],
            'food': ['еда', 'кулинария', 'рецепты', 'ресторан'],
            'fashion': ['мода', 'стиль', 'красота', 'одежда'],
            'crypto': ['криптовалюта', 'блокчейн', 'биткоин', 'DeFi']
        }
    
    def find_best_matches(self, offer_data, available_channels):
        """Поиск лучших соответствий каналов для оффера"""
        matches = []
        
        for channel in available_channels:
            match_score = self.calculate_match_score(offer_data, channel)
            if match_score > 0.3:  # Минимальный порог соответствия
                channel_data = self.enrich_channel_data(channel, offer_data, match_score)
                matches.append(channel_data)
        
        # Сортируем по релевантности
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:20]  # Топ-20 каналов
    
    def calculate_match_score(self, offer_data, channel):
        """Расчет оценки соответствия канала офферу"""
        score = 0.0
        factors = {}
        
        # 1. Соответствие категории (вес 30%)
        category_score = self.calculate_category_match(offer_data.get('category'), channel)
        factors['category_match'] = category_score
        score += category_score * 0.3
        
        # 2. Соответствие бюджета (вес 25%)
        budget_score = self.calculate_budget_compatibility(offer_data.get('budget', 0), channel)
        factors['budget_compatibility'] = budget_score
        score += budget_score * 0.25
        
        # 3. Качество аудитории (вес 20%)
        audience_score = self.calculate_audience_quality(channel)
        factors['audience_quality'] = audience_score
        score += audience_score * 0.2
        
        # 4. Историческая эффективность (вес 15%)
        performance_score = self.calculate_historical_performance(channel)
        factors['historical_performance'] = performance_score
        score += performance_score * 0.15
        
        # 5. Доступность (вес 10%)
        availability_score = self.calculate_availability(channel)
        factors['availability'] = availability_score
        score += availability_score * 0.1
        
        return min(score, 1.0), factors
    
    def calculate_category_match(self, offer_category, channel):
        """Соответствие категории"""
        if not offer_category or not channel.get('description'):
            return 0.3
        
        keywords = self.category_weights.get(offer_category, [])
        if not keywords:
            return 0.3
        
        description = (channel.get('description', '') + ' ' + 
                      channel.get('title', '')).lower()
        
        matches = sum(1 for keyword in keywords if keyword.lower() in description)
        return min(matches / len(keywords), 1.0)
    
    def calculate_budget_compatibility(self, budget, channel):
        """Совместимость бюджета"""
        channel_price = channel.get('price_per_post', 0)
        if not channel_price or not budget:
            return 0.5
        
        # Идеальный диапазон: канал стоит 5-30% от бюджета
        price_ratio = channel_price / budget
        
        if 0.05 <= price_ratio <= 0.30:
            return 1.0
        elif price_ratio < 0.05:
            return 0.8  # Дешево, но нормально
        elif price_ratio <= 0.50:
            return 0.6  # Дороговато
        else:
            return 0.2  # Слишком дорого
    
    def calculate_audience_quality(self, channel):
        """Качество аудитории канала"""
        subscribers = channel.get('subscribers', 0)
        engagement_rate = channel.get('engagement_rate', 0)
        is_verified = channel.get('is_verified', False)
        
        # Базовая оценка по подписчикам
        if subscribers < 1000:
            size_score = 0.3
        elif subscribers < 5000:
            size_score = 0.5
        elif subscribers < 20000:
            size_score = 0.7
        elif subscribers < 100000:
            size_score = 0.9
        else:
            size_score = 1.0
        
        # Оценка по вовлеченности
        if engagement_rate < 1:
            engagement_score = 0.2
        elif engagement_rate < 3:
            engagement_score = 0.5
        elif engagement_rate < 5:
            engagement_score = 0.7
        elif engagement_rate < 10:
            engagement_score = 0.9
        else:
            engagement_score = 1.0
        
        # Бонус за верификацию
        verification_bonus = 0.1 if is_verified else 0
        
        return (size_score * 0.4 + engagement_score * 0.6 + verification_bonus)
    
    def calculate_historical_performance(self, channel):
        """Историческая эффективность канала"""
        try:
            # Получаем статистику размещений за последние 3 месяца
            stats = execute_db_query("""
                SELECT 
                    COUNT(*) as total_placements,
                    AVG(CASE WHEN performance_rating IS NOT NULL THEN performance_rating ELSE 3 END) as avg_rating,
                    COUNT(CASE WHEN performance_rating >= 4 THEN 1 END) as good_placements
                FROM offer_placements op
                JOIN offer_proposals opr ON op.proposal_id = opr.id
                WHERE opr.channel_id = ? 
                AND op.created_at >= DATE('now', '-3 months')
            """, (channel.get('id'),), fetch_one=True)
            
            if not stats or stats['total_placements'] == 0:
                return 0.5  # Нет истории - средняя оценка
            
            # Нормализуем рейтинг (от 1 до 5)
            rating_score = (stats['avg_rating'] - 1) / 4
            
            # Учитываем количество хороших размещений
            success_rate = stats['good_placements'] / stats['total_placements']
            
            return (rating_score * 0.7 + success_rate * 0.3)
            
        except Exception as e:
            logger.warning(f"Ошибка расчета исторической эффективности: {e}")
            return 0.5
    
    def calculate_availability(self, channel):
        """Доступность канала для размещения"""
        try:
            # Проверяем загруженность канала
            recent_placements = execute_db_query("""
                SELECT COUNT(*) as count
                FROM offer_placements op
                JOIN offer_proposals opr ON op.proposal_id = opr.id
                WHERE opr.channel_id = ? 
                AND op.created_at >= DATE('now', '-7 days')
            """, (channel.get('id'),), fetch_one=True)
            
            placements_count = recent_placements['count'] if recent_placements else 0
            
            # Чем меньше размещений на неделе, тем выше доступность
            if placements_count == 0:
                return 1.0
            elif placements_count <= 2:
                return 0.8
            elif placements_count <= 5:
                return 0.6
            else:
                return 0.3
                
        except Exception as e:
            logger.warning(f"Ошибка расчета доступности: {e}")
            return 0.7
    
    def enrich_channel_data(self, channel, offer_data, match_score_data):
        """Обогащение данных канала дополнительными метриками"""
        match_score, factors = match_score_data
        
        # Прогноз ROI
        expected_roi = self.calculate_expected_roi(channel, offer_data, match_score)
        
        # Прогноз охвата
        estimated_reach = self.calculate_estimated_reach(channel, offer_data)
        
        return {
            'id': channel['id'],
            'username': channel['username'],
            'title': channel.get('title', channel['username']),
            'subscribers': channel.get('subscribers', 0),
            'price_per_post': channel.get('price_per_post', 0),
            'engagement_rate': round(channel.get('engagement_rate', 0), 1),
            'is_verified': channel.get('is_verified', False),
            'categories': self.extract_categories(channel),
            'match_score': round(match_score, 2),
            'match_factors': factors,
            'expected_roi': round(expected_roi, 1),
            'estimated_reach': estimated_reach,
            'estimated_views': int(estimated_reach * channel.get('engagement_rate', 3) / 100),
            'recommendation_reason': self.generate_recommendation_reason(factors, match_score)
        }
    
    def calculate_expected_roi(self, channel, offer_data, match_score):
        """Расчет ожидаемого ROI"""
        # Базовый ROI зависит от соответствия и качества канала
        base_roi = 1.5 + (match_score * 2)
        
        # Корректировка по историческим данным
        try:
            avg_performance = execute_db_query("""
                SELECT AVG(performance_rating) as avg_rating
                FROM offer_placements op
                JOIN offer_proposals opr ON op.proposal_id = opr.id
                WHERE opr.channel_id = ?
                AND performance_rating IS NOT NULL
            """, (channel['id'],), fetch_one=True)
            
            if avg_performance and avg_performance['avg_rating']:
                performance_multiplier = avg_performance['avg_rating'] / 3  # Нормализуем к 1
                base_roi *= performance_multiplier
                
        except Exception:
            pass
        
        return max(base_roi, 0.5)
    
    def calculate_estimated_reach(self, channel, offer_data):
        """Расчет ожидаемого охвата"""
        subscribers = channel.get('subscribers', 0)
        
        # Охват зависит от размера канала
        if subscribers < 1000:
            reach_rate = 0.8  # Маленькие каналы имеют высокий охват
        elif subscribers < 10000:
            reach_rate = 0.6
        elif subscribers < 50000:
            reach_rate = 0.4
        else:
            reach_rate = 0.3  # Большие каналы имеют меньший относительный охват
        
        return int(subscribers * reach_rate)
    
    def extract_categories(self, channel):
        """Извлечение категорий канала"""
        description = (channel.get('description', '') + ' ' + 
                      channel.get('title', '')).lower()
        
        categories = []
        for category, keywords in self.category_weights.items():
            if any(keyword.lower() in description for keyword in keywords):
                categories.append(category)
        
        return categories[:3]  # Максимум 3 категории
    
    def generate_recommendation_reason(self, factors, match_score):
        """Генерация причины рекомендации"""
        if match_score > 0.8:
            return "Отличное соответствие по всем параметрам"
        elif factors.get('category_match', 0) > 0.7:
            return "Идеально подходит по тематике"
        elif factors.get('budget_compatibility', 0) > 0.8:
            return "Оптимальное соотношение цена/охват"
        elif factors.get('audience_quality', 0) > 0.8:
            return "Высококачественная аудитория"
        else:
            return "Хорошие показатели эффективности"

@smart_recommendations_bp.route('/smart-recommendations', methods=['POST'])
def get_smart_recommendations():
    """Получение умных рекомендаций каналов"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400
        
        # Получаем ID текущего пользователя
        try:
            user_id = AuthService.get_current_user_id()
        except:
            # Fallback для тестирования
            user_id = 1
        
        # Получаем доступные каналы (исключаем каналы пользователя)
        available_channels = execute_db_query("""
            SELECT 
                c.*,
                COALESCE(c.subscribers, 0) as subscribers,
                COALESCE(c.price_per_post, 0) as price_per_post,
                COALESCE(
                    (SELECT AVG(engagement_rate) 
                     FROM channel_statistics cs 
                     WHERE cs.channel_id = c.id 
                     AND cs.date >= DATE('now', '-30 days')), 
                    3.0
                ) as engagement_rate
            FROM channels c
            WHERE c.is_active = 1 
            AND c.is_verified = 1
            AND c.owner_id != ?
            AND c.price_per_post > 0
            ORDER BY c.subscribers DESC
            LIMIT 50
        """, (user_id,), fetch_all=True)
        
        if not available_channels:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Нет доступных каналов'
            })
        
        # Создаем matcher и находим лучшие соответствия
        matcher = IntelligentChannelMatcher()
        recommendations = matcher.find_best_matches(data, available_channels)
        
        # Добавляем дополнительную информацию
        result = {
            'success': True,
            'data': recommendations,
            'meta': {
                'total_analyzed': len(available_channels),
                'recommendations_count': len(recommendations),
                'average_match_score': round(
                    sum(r['match_score'] for r in recommendations) / len(recommendations), 2
                ) if recommendations else 0,
                'budget_utilization': calculate_budget_utilization(recommendations, data.get('budget', 0))
            }
        }
        
        logger.info(f"Сгенерировано {len(recommendations)} рекомендаций для пользователя {user_id}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Ошибка генерации рекомендаций: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка генерации рекомендаций'
        }), 500

def calculate_budget_utilization(recommendations, budget):
    """Расчет использования бюджета рекомендациями"""
    if not budget or not recommendations:
        return {}
    
    # Топ-5 самых релевантных каналов
    top_channels = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)[:5]
    total_cost = sum(ch['price_per_post'] for ch in top_channels)
    
    return {
        'top_5_cost': total_cost,
        'budget_coverage': round((total_cost / budget) * 100, 1) if budget > 0 else 0,
        'remaining_budget': max(budget - total_cost, 0),
        'recommended_selection': len([ch for ch in top_channels if ch['price_per_post'] <= budget * 0.3])
    }

@smart_recommendations_bp.route('/categories', methods=['GET'])
def get_offer_categories():
    """Получение списка категорий офферов"""
    categories = [
        {'id': 'tech', 'name': '💻 Технологии', 'description': 'IT, программирование, стартапы'},
        {'id': 'business', 'name': '💼 Бизнес', 'description': 'Предпринимательство, финансы, инвестиции'},
        {'id': 'lifestyle', 'name': '🌟 Образ жизни', 'description': 'Мотивация, саморазвитие, психология'},
        {'id': 'entertainment', 'name': '🎬 Развлечения', 'description': 'Юмор, кино, музыка, игры'},
        {'id': 'education', 'name': '📚 Образование', 'description': 'Обучение, курсы, университеты'},
        {'id': 'health', 'name': '💪 Здоровье', 'description': 'Фитнес, медицина, спорт'},
        {'id': 'travel', 'name': '✈️ Путешествия', 'description': 'Туризм, отдых, страны'},
        {'id': 'food', 'name': '🍕 Еда', 'description': 'Кулинария, рецепты, рестораны'},
        {'id': 'fashion', 'name': '👗 Мода', 'description': 'Стиль, красота, одежда'},
        {'id': 'crypto', 'name': '₿ Криптовалюты', 'description': 'Блокчейн, биткоин, DeFi'}
    ]
    
    return jsonify({
        'success': True,
        'data': categories
    })

@smart_recommendations_bp.route('/market-data', methods=['GET'])
def get_market_data():
    """Получение рыночных данных для калькулятора"""
    try:
        # Средние цены по категориям
        market_data = execute_db_query("""
            SELECT 
                category,
                AVG(price_per_post) as avg_price,
                COUNT(*) as channels_count,
                AVG(subscribers) as avg_subscribers
            FROM channels 
            WHERE is_active = 1 AND price_per_post > 0
            GROUP BY category
        """, fetch_all=True)
        
        # Общая статистика
        total_stats = execute_db_query("""
            SELECT 
                COUNT(*) as total_channels,
                AVG(price_per_post) as avg_price,
                AVG(subscribers) as avg_subscribers,
                SUM(subscribers) as total_reach
            FROM channels 
            WHERE is_active = 1 AND price_per_post > 0
        """, fetch_one=True)
        
        return jsonify({
            'success': True,
            'data': {
                'categories': [dict(row) for row in market_data] if market_data else [],
                'total_stats': dict(total_stats) if total_stats else {},
                'updated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения рыночных данных: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения рыночных данных'
        }), 500