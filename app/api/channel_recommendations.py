# channel_recommendations.py - Система автоматических рекомендаций каналов
import re
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from working_app import safe_execute_query

logger = logging.getLogger(__name__)

# Тематические категории и ключевые слова
CATEGORY_KEYWORDS = {
    'technology': ['технолог', 'IT', 'программирован', 'софт', 'разработк', 'код', 'веб', 'приложен', 'стартап', 'диджитал'],
    'crypto': ['криптовалют', 'биткоин', 'блокчейн', 'NFT', 'DeFi', 'майнинг', 'трейдинг', 'токен'],
    'business': ['бизнес', 'предпринимательств', 'стартап', 'инвестиц', 'финанс', 'маркетинг', 'продаж'],
    'gaming': ['игр', 'геймер', 'киберспорт', 'стрим', 'gaming', 'консол', 'мобильн'],
    'education': ['образован', 'курс', 'учеб', 'школ', 'университет', 'обучен', 'навык'],
    'entertainment': ['развлечен', 'юмор', 'мем', 'фильм', 'сериал', 'музык', 'видео'],
    'lifestyle': ['образ жизни', 'мотивац', 'саморазвит', 'психолог', 'здоровь', 'спорт'],
    'news': ['новости', 'события', 'политик', 'экономик', 'аналитик', 'обзор'],
    'ecommerce': ['интернет-магазин', 'товар', 'скидк', 'распродаж', 'покупк', 'продукт']
}

# Ценовые сегменты
PRICE_SEGMENTS = {
    'budget': (0, 2000),
    'medium': (2000, 10000), 
    'premium': (10000, 50000),
    'enterprise': (50000, float('inf'))
}
def get_channel_recommendations():
    """Получение рекомендаций каналов"""
    return []

def analyze_offer_content(title: str, description: str, target_audience: str = "") -> Dict[str, Any]:
    """
    Анализ контента оффера для определения тематики и целевой аудитории
    
    Args:
        title: Заголовок оффера
        description: Описание оффера
        target_audience: Целевая аудитория
        
    Returns:
        Dict с результатами анализа
    """
    try:
        # Объединяем весь текст для анализа
        full_text = f"{title} {description} {target_audience}".lower()
        
        # Определяем категории по ключевым словам
        detected_categories = []
        category_scores = {}
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in full_text:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                category_scores[category] = score
                detected_categories.append({
                    'category': category,
                    'score': score,
                    'keywords': matched_keywords
                })
        
        # Сортируем категории по релевантности
        detected_categories.sort(key=lambda x: x['score'], reverse=True)
        
        # Анализ целевой аудитории
        audience_analysis = analyze_target_audience(full_text)
        
        # Анализ срочности и временных рамок
        urgency_analysis = analyze_urgency(full_text)
        
        return {
            'categories': detected_categories[:3],  # Топ-3 категории
            'primary_category': detected_categories[0]['category'] if detected_categories else 'general',
            'audience': audience_analysis,
            'urgency': urgency_analysis,
            'keywords': extract_important_keywords(full_text)
        }
        
    except Exception as e:
        logger.error(f"Ошибка анализа контента оффера: {e}")
        return {
            'categories': [],
            'primary_category': 'general',
            'audience': {},
            'urgency': 'normal',
            'keywords': []
        }

def analyze_target_audience(text: str) -> Dict[str, Any]:
    """Анализ целевой аудитории из текста"""
    audience_indicators = {
        'age_18_25': ['студент', 'молодежь', 'школьник', 'подросток'],
        'age_25_35': ['молодой специалист', 'карьер', 'профессионал'],
        'age_35_45': ['опытный', 'руководител', 'менеджер', 'семейн'],
        'age_45_plus': ['зрелый', 'опытный', 'пенсионер', 'старш'],
        'gender_male': ['мужчин', 'мужской', 'отц', 'парн'],
        'gender_female': ['женщин', 'женский', 'мам', 'девушк'],
        'income_high': ['премиум', 'люкс', 'элитн', 'дорог', 'VIP'],
        'income_medium': ['средний класс', 'доступн', 'оптимальн'],
        'income_low': ['бюджетн', 'эконом', 'дешев', 'скидк']
    }
    
    detected_segments = {}
    for segment, keywords in audience_indicators.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            detected_segments[segment] = score
    
    return detected_segments

def analyze_urgency(text: str) -> str:
    """Определение срочности оффера"""
    urgency_keywords = {
        'high': ['срочно', 'быстро', 'немедленно', 'сегодня', 'завтра'],
        'medium': ['скоро', 'в ближайшее время', 'на этой неделе'],
        'low': ['когда удобно', 'без спешки', 'в свободное время']
    }
    
    for level, keywords in urgency_keywords.items():
        if any(keyword in text for keyword in keywords):
            return level
    
    return 'normal'

def extract_important_keywords(text: str) -> List[str]:
    """Извлечение важных ключевых слов из текста"""
    # Удаляем стоп-слова и извлекаем значимые слова
    stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'из', 'к', 'от', 'до', 'при', 'об', 'о', 'за', 'под', 'над'}
    
    # Простое извлечение слов (можно улучшить с помощью NLP библиотек)
    words = re.findall(r'\b[а-яё]{3,}\b', text)
    keywords = [word for word in words if word not in stop_words]
    
    # Возвращаем уникальные слова, отсортированные по частоте
    from collections import Counter
    word_counts = Counter(keywords)
    return [word for word, count in word_counts.most_common(10)]

def get_recommended_channels(offer_analysis: Dict[str, Any], price: float, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получение рекомендованных каналов на основе анализа оффера
    
    Args:
        offer_analysis: Результат анализа оффера
        price: Цена размещения
        limit: Максимальное количество рекомендаций
        
    Returns:
        Список рекомендованных каналов с баллами соответствия
    """
    try:
        primary_category = offer_analysis.get('primary_category', 'general')
        categories = [cat['category'] for cat in offer_analysis.get('categories', [])]
        
        # Базовый запрос для получения активных каналов
        base_query = '''
            SELECT c.*, 
                   COALESCE(AVG(r.rating), 4.0) as avg_rating,
                   COUNT(DISTINCT r.id) as total_reviews,
                   COUNT(DISTINCT recent_offers.id) as recent_offers_count
            FROM channels c
            LEFT JOIN channel_reviews r ON c.id = r.channel_id
            LEFT JOIN offers recent_offers ON c.id = recent_offers.channel_id 
                AND recent_offers.created_at >= date('now', '-30 days')
            WHERE c.is_active = 1 
                AND c.is_deleted = 0
                AND c.subscriber_count > 100
        '''
        
        # Фильтрация по категории если есть
        if primary_category != 'general':
            base_query += f" AND (c.category = '{primary_category}'"
            if categories:
                category_conditions = " OR ".join([f"c.category = '{cat}'" for cat in categories[:2]])
                base_query += f" OR {category_conditions}"
            base_query += ")"
        
        base_query += '''
            GROUP BY c.id
            ORDER BY avg_rating DESC, c.subscriber_count DESC
            LIMIT ?
        '''
        
        channels = safe_execute_query(base_query, (limit * 2,), fetch_all=True)
        
        if not channels:
            # Если нет каналов в категории, получаем общие рекомендации
            channels = safe_execute_query('''
                SELECT c.*, 
                       COALESCE(AVG(r.rating), 4.0) as avg_rating,
                       COUNT(DISTINCT r.id) as total_reviews
                FROM channels c
                LEFT JOIN channel_reviews r ON c.id = r.channel_id
                WHERE c.is_active = 1 AND c.is_deleted = 0
                GROUP BY c.id
                ORDER BY c.subscriber_count DESC, avg_rating DESC
                LIMIT ?
            ''', (limit,), fetch_all=True)
        
        # Рассчитываем баллы соответствия для каждого канала
        recommendations = []
        for channel in channels:
            score = calculate_recommendation_score(channel, offer_analysis, price)
            
            if score > 30:  # Минимальный порог соответствия
                channel_data = dict(channel)
                channel_data['recommendation_score'] = score
                channel_data['recommendation_reasons'] = get_recommendation_reasons(channel, offer_analysis, score)
                recommendations.append(channel_data)
        
        # Сортируем по баллу соответствия и возвращаем топ
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:limit]
        
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций: {e}")
        return []

def calculate_recommendation_score(channel: Dict[str, Any], offer_analysis: Dict[str, Any], price: float) -> float:
    """Расчет балла соответствия канала офферу"""
    score = 50.0  # Базовый балл
    
    try:
        # Соответствие категории (30 баллов максимум)
        primary_category = offer_analysis.get('primary_category', 'general')
        channel_category = channel.get('category', 'general')
        
        if channel_category == primary_category:
            score += 30
        elif any(cat['category'] == channel_category for cat in offer_analysis.get('categories', [])):
            score += 20
        
        # Качество канала (25 баллов максимум)
        avg_rating = float(channel.get('avg_rating', 4.0))
        score += (avg_rating - 3.0) * 12.5  # 4.0 рейтинг = +12.5, 5.0 = +25
        
        # Активность канала (15 баллов максимум)
        recent_offers = channel.get('recent_offers_count', 0)
        if recent_offers > 5:
            score += 15
        elif recent_offers > 2:
            score += 10
        elif recent_offers > 0:
            score += 5
        
        # Размер аудитории (15 баллов максимум)
        subscriber = channel.get('subscriber_count', 0)
        if subscriber > 50000:
            score += 15
        elif subscriber > 10000:
            score += 12
        elif subscriber > 5000:
            score += 8
        elif subscriber > 1000:
            score += 5
        
        # Соответствие цене (15 баллов максимум)
        channel_price = channel.get('price_per_post', 0)
        if channel_price > 0:
            price_ratio = price / channel_price
            if 0.8 <= price_ratio <= 1.2:  # Цена в пределах ±20%
                score += 15
            elif 0.6 <= price_ratio <= 1.5:  # Цена в пределах ±50%
                score += 10
            elif 0.4 <= price_ratio <= 2.0:  # Цена в пределах ±100%
                score += 5
        
        # Верификация канала (бонус)
        if channel.get('is_verified'):
            score += 5
        
        # Ограничиваем диапазон
        score = max(0, min(100, score))
        
    except Exception as e:
        logger.error(f"Ошибка расчета балла рекомендации: {e}")
        score = 50.0
    
    return round(score, 1)

def get_recommendation_reasons(channel: Dict[str, Any], offer_analysis: Dict[str, Any], score: float) -> List[str]:
    """Получение причин рекомендации канала"""
    reasons = []
    
    try:
        # Соответствие категории
        primary_category = offer_analysis.get('primary_category', 'general')
        if channel.get('category') == primary_category:
            reasons.append(f"Точное соответствие тематике: {primary_category}")
        
        # Высокий рейтинг
        avg_rating = float(channel.get('avg_rating', 4.0))
        if avg_rating >= 4.5:
            reasons.append(f"Высокий рейтинг: {avg_rating:.1f}/5.0")
        
        # Большая аудитория
        subscriber = channel.get('subscriber_count', 0)
        if subscriber > 50000:
            reasons.append(f"Большая аудитория: {subscriber:,} подписчиков")
        elif subscriber > 10000:
            reasons.append(f"Стабильная аудитория: {subscriber:,} подписчиков")
        
        # Активность
        recent_offers = channel.get('recent_offers_count', 0)
        if recent_offers > 5:
            reasons.append("Активно работает с рекламодателями")
        
        # Верификация
        if channel.get('is_verified'):
            reasons.append("Верифицированный канал")
        
        # Общий балл
        if score >= 80:
            reasons.append("Идеальное соответствие вашему оферу")
        elif score >= 65:
            reasons.append("Отличное соответствие требованиям")
        
    except Exception as e:
        logger.error(f"Ошибка получения причин рекомендации: {e}")
    
    return reasons[:3]  # Максимум 3 причины

def get_channel_recommendations_api(title: str, description: str, target_audience: str = "", price: float = 0, limit: int = 10) -> Dict[str, Any]:
    """
    API функция для получения рекомендаций каналов
    
    Args:
        title: Заголовок оффера
        description: Описание оффера  
        target_audience: Целевая аудитория
        price: Бюджет на размещение
        limit: Количество рекомендаций
        
    Returns:
        Dict с рекомендациями и метаданными
    """
    try:
        # Анализируем оффер
        offer_analysis = analyze_offer_content(title, description, target_audience)
        
        # Получаем рекомендации
        recommendations = get_recommended_channels(offer_analysis, price, limit)
        
        # Подготавливаем метаданные
        metadata = {
            'detected_categories': offer_analysis.get('categories', []),
            'primary_category': offer_analysis.get('primary_category', 'general'),
            'total_recommendations': len(recommendations),
            'analysis_keywords': offer_analysis.get('keywords', [])
        }
        
        return {
            'success': True,
            'recommendations': recommendations,
            'metadata': metadata,
            'offer_analysis': offer_analysis
        }
        
    except Exception as e:
        logger.error(f"Ошибка API рекомендаций: {e}")
        return {
            'success': False,
            'error': str(e),
            'recommendations': [],
            'metadata': {}
        }
