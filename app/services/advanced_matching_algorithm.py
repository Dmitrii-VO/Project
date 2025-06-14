# advanced_matching_algorithm.py - Улучшенный алгоритм подбора каналов v2.0
import re
import logging
import sqlite3
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)

class AdvancedMatchingEngine:
    """Продвинутый движок сопоставления офферов и каналов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Весовые коэффициенты для различных критериев
        self.weights = {
            'price_attractiveness': 0.25,      # Привлекательность цены
            'audience_match': 0.30,            # Соответствие аудитории
            'requirements_compliance': 0.20,   # Соответствие требованиям
            'channel_quality': 0.15,           # Качество канала
            'historical_performance': 0.10     # Историческая эффективность
        }
        
        # Тематические категории для анализа
        self.categories = {
            'tech': ['технолог', 'разработк', 'программ', 'ии', 'искусств', 'блокчейн', 'крипто', 'startup', 'стартап'],
            'business': ['бизнес', 'предприним', 'инвестиц', 'финанс', 'экономик', 'маркетинг', 'продаж'],
            'education': ['образован', 'обучен', 'курс', 'тренинг', 'универс', 'школ', 'изучен'],
            'lifestyle': ['образ жизни', 'стиль', 'мод', 'красот', 'здоров', 'фитнес', 'психолог'],
            'entertainment': ['развлечен', 'юмор', 'фильм', 'музык', 'игр', 'мем', 'шоу'],
            'travel': ['путешеств', 'туризм', 'страна', 'город', 'отдых', 'виза', 'отель'],
            'food': ['еда', 'кулинар', 'рецепт', 'ресторан', 'кафе', 'готовк', 'повар'],
            'finance': ['финанс', 'банк', 'кредит', 'займ', 'инвестиц', 'трейдинг', 'валют'],
            'real_estate': ['недвижим', 'квартир', 'дом', 'ипотек', 'аренд', 'покупк', 'строител'],
            'auto': ['авто', 'машин', 'автомобил', 'транспорт', 'мото', 'грузовик']
        }
        
    def calculate_advanced_suitability_score(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> Dict[str, Any]:
        """
        Расчет продвинутого соответствия оффера каналу
        
        Returns:
            Dict с общим баллом и детализацией по критериям
        """
        try:
            scores = {}
            
            # 1. Анализ привлекательности цены
            scores['price_attractiveness'] = self._calculate_price_score(offer, channel)
            
            # 2. Анализ соответствия аудитории
            scores['audience_match'] = self._calculate_audience_match(offer, channel)
            
            # 3. Соответствие требованиям
            scores['requirements_compliance'] = self._calculate_requirements_compliance(offer, channel)
            
            # 4. Качество канала
            scores['channel_quality'] = self._calculate_channel_quality(channel)
            
            # 5. Историческая эффективность
            scores['historical_performance'] = self._calculate_historical_performance(offer, channel)
            
            # Расчет общего балла
            total_score = sum(scores[key] * self.weights[key] for key in scores)
            
            # Дополнительные метрики
            result = {
                'total_score': round(total_score, 1),
                'detailed_scores': {k: round(v, 1) for k, v in scores.items()},
                'category_matches': self._find_category_matches(offer, channel),
                'risk_factors': self._identify_risk_factors(offer, channel),
                'optimization_tips': self._generate_optimization_tips(offer, channel, scores)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета продвинутого соответствия: {e}")
            return {
                'total_score': 50.0,
                'detailed_scores': {},
                'category_matches': [],
                'risk_factors': [],
                'optimization_tips': []
            }
    
    def _calculate_price_score(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Расчет привлекательности цены"""
        try:
            offer_price = float(offer.get('price', 0))
            channel_avg_price = float(channel.get('price_per_post', 0))
            channel_subs = int(channel.get('subscriber_count', 0))
            
            # Если у канала не указана цена, используем среднерыночную по подписчикам
            if channel_avg_price == 0:
                channel_avg_price = self._estimate_market_price(channel_subs)
            
            if channel_avg_price == 0:
                return 50.0  # Нейтральная оценка при отсутствии данных
            
            # Расчет коэффициента привлекательности цены
            price_ratio = offer_price / channel_avg_price
            
            # Оптимальный диапазон: 0.8 - 1.5 от обычной цены канала
            if 0.8 <= price_ratio <= 1.5:
                base_score = 80.0
            elif 0.5 <= price_ratio < 0.8:
                base_score = 60.0  # Низкая цена
            elif 1.5 < price_ratio <= 2.0:
                base_score = 95.0  # Высокая цена - очень привлекательно
            elif price_ratio > 2.0:
                base_score = 100.0  # Очень высокая цена
            else:
                base_score = 30.0  # Слишком низкая цена
            
            # Бонус за высокие цены (мотивация)
            if offer_price >= 10000:
                base_score += 10
            elif offer_price >= 5000:
                base_score += 5
            
            return min(100.0, base_score)
            
        except Exception as e:
            logger.error(f"Ошибка расчета ценовой привлекательности: {e}")
            return 50.0
    
    def _calculate_audience_match(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Продвинутый анализ соответствия аудитории"""
        try:
            score = 0.0
            
            # Извлекаем тексты для анализа
            offer_texts = self._extract_offer_texts(offer)
            channel_texts = self._extract_channel_texts(channel)
            
            # 1. Тематическое соответствие
            category_score = self._calculate_category_similarity(offer_texts, channel_texts)
            score += category_score * 0.4
            
            # 2. Ключевые слова
            keyword_score = self._calculate_keyword_similarity(offer_texts, channel_texts)
            score += keyword_score * 0.3
            
            # 3. Целевая аудитория
            audience_score = self._calculate_target_audience_match(offer, channel)
            score += audience_score * 0.3
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Ошибка анализа соответствия аудитории: {e}")
            return 50.0
    
    def _calculate_requirements_compliance(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Проверка соответствия требованиям оффера"""
        try:
            score = 100.0  # Начинаем со 100% и вычитаем за несоответствия
            
            requirements = offer.get('requirements', '').lower()
            if not requirements:
                return 80.0  # Нет требований = хорошо, но не идеально
            
            channel_subs = int(channel.get('subscriber_count', 0))
            
            # Проверка минимального количества подписчиков
            min_subs_patterns = [
                r'(\d+)\s*(?:тыс|k)\s*подписчик',
                r'(\d+)\s*подписчик',
                r'от\s*(\d+)',
                r'минимум\s*(\d+)'
            ]
            
            for pattern in min_subs_patterns:
                match = re.search(pattern, requirements)
                if match:
                    required_subs = int(match.group(1))
                    # Если указано в тысячах
                    if 'тыс' in match.group(0) or 'k' in match.group(0):
                        required_subs *= 1000
                    
                    if channel_subs < required_subs:
                        shortage_ratio = channel_subs / required_subs
                        score -= (1 - shortage_ratio) * 50  # Серьезный штраф
                    break
            
            # Проверка верификации
            if 'верифиц' in requirements or 'проверен' in requirements:
                if not channel.get('is_verified', False):
                    score -= 30
            
            # Проверка тематических требований
            forbidden_themes = ['18+', 'взрослы', 'эротик', 'азартн']
            for theme in forbidden_themes:
                if theme in requirements:
                    channel_desc = channel.get('description', '').lower()
                    if theme in channel_desc:
                        score -= 40
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"Ошибка проверки требований: {e}")
            return 50.0
    
    def _calculate_channel_quality(self, channel: Dict[str, Any]) -> float:
        """Оценка качества канала"""
        try:
            score = 50.0  # Базовая оценка
            
            # 1. Количество подписчиков (логарифмическая шкала)
            subs = int(channel.get('subscriber_count', 0))
            if subs > 0:
                subs_score = min(30.0, math.log10(subs) * 10)
                score += subs_score
            
            # 2. Верификация канала
            if channel.get('is_verified', False):
                score += 15
            
            # 3. Активность (если есть данные)
            if channel.get('avg_views_per_post', 0) > 0:
                views = int(channel.get('avg_views_per_post', 0))
                engagement_rate = (views / subs) * 100 if subs > 0 else 0
                
                if engagement_rate >= 10:
                    score += 20
                elif engagement_rate >= 5:
                    score += 15
                elif engagement_rate >= 2:
                    score += 10
                elif engagement_rate >= 1:
                    score += 5
            
            # 4. Полнота профиля
            profile_completeness = 0
            if channel.get('description'):
                profile_completeness += 25
            if channel.get('category'):
                profile_completeness += 25
            if channel.get('price_per_post', 0) > 0:
                profile_completeness += 25
            if channel.get('link'):
                profile_completeness += 25
            
            score += profile_completeness * 0.2  # Макс 20 баллов
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Ошибка оценки качества канала: {e}")
            return 50.0
    
    def _calculate_historical_performance(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Анализ исторической эффективности"""
        try:
            # Получаем статистику предыдущих размещений
            channel_id = channel.get('id')
            if not channel_id:
                return 60.0  # Нейтральная оценка для новых каналов
            
            # Статистика по каналу
            channel_stats = self._get_channel_historical_stats(channel_id)
            
            # Статистика по категории оффера
            offer_category = self._detect_offer_category(offer)
            category_stats = self._get_category_performance_stats(channel_id, offer_category)
            
            score = 60.0  # Базовая оценка
            
            # Анализ успешности откликов канала
            if channel_stats['total_responses'] > 0:
                success_rate = channel_stats['successful_responses'] / channel_stats['total_responses']
                score += success_rate * 30
            
            # Анализ эффективности в данной категории
            if category_stats['category_responses'] > 0:
                category_success = category_stats['category_successful'] / category_stats['category_responses']
                score += category_success * 10
            
            return min(100.0, score)
            
        except Exception as e:
            logger.error(f"Ошибка анализа исторической эффективности: {e}")
            return 60.0
    
    def _extract_offer_texts(self, offer: Dict[str, Any]) -> str:
        """Извлечение всех текстов из оффера для анализа"""
        texts = []
        
        if offer.get('title'):
            texts.append(offer['title'])
        if offer.get('description'):
            texts.append(offer['description'])
        if offer.get('target_audience'):
            texts.append(offer['target_audience'])
        if offer.get('requirements'):
            texts.append(offer['requirements'])
        
        return ' '.join(texts).lower()
    
    def _extract_channel_texts(self, channel: Dict[str, Any]) -> str:
        """Извлечение всех текстов из канала для анализа"""
        texts = []
        
        if channel.get('title'):
            texts.append(channel['title'])
        if channel.get('description'):
            texts.append(channel['description'])
        if channel.get('category'):
            texts.append(channel['category'])
        
        return ' '.join(texts).lower()
    
    def _calculate_category_similarity(self, offer_text: str, channel_text: str) -> float:
        """Расчет тематического соответствия"""
        matches = []
        
        for category, keywords in self.categories.items():
            offer_matches = sum(1 for word in keywords if word in offer_text)
            channel_matches = sum(1 for word in keywords if word in channel_text)
            
            if offer_matches > 0 and channel_matches > 0:
                # Сила совпадения = произведение количества совпадений
                match_strength = min(offer_matches, channel_matches) * 10
                matches.append((category, match_strength))
        
        if not matches:
            return 30.0  # Нет четких совпадений
        
        # Возвращаем максимальную силу совпадения
        return min(100.0, max(match[1] for match in matches))
    
    def _calculate_keyword_similarity(self, offer_text: str, channel_text: str) -> float:
        """Анализ совпадения ключевых слов"""
        # Извлекаем значимые слова (больше 3 символов)
        offer_words = set(re.findall(r'\b\w{4,}\b', offer_text))
        channel_words = set(re.findall(r'\b\w{4,}\b', channel_text))
        
        if not offer_words or not channel_words:
            return 40.0
        
        # Находим пересечения
        common_words = offer_words.intersection(channel_words)
        
        if not common_words:
            return 20.0
        
        # Рассчитываем коэффициент Жаккара
        jaccard_coefficient = len(common_words) / len(offer_words.union(channel_words))
        
        return min(100.0, jaccard_coefficient * 200)  # Масштабируем до 100
    
    def _calculate_target_audience_match(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Анализ соответствия целевой аудитории"""
        target_audience = offer.get('target_audience', '').lower()
        channel_desc = channel.get('description', '').lower()
        
        if not target_audience:
            return 50.0  # Нейтральная оценка при отсутствии информации
        
        # Анализ демографических характеристик
        age_groups = {
            'молод': ['молод', 'студент', '18-25', '20-30'],
            'средний': ['взрослы', '25-40', '30-45', 'семьи'],
            'старший': ['опытны', '40+', '45+', 'пенсион']
        }
        
        gender_groups = {
            'мужчин': ['мужчин', 'мужск', 'парн', 'отц'],
            'женщин': ['женщин', 'женск', 'девушк', 'мам', 'мамоч']
        }
        
        score = 50.0
        
        # Проверяем возрастные группы
        for group, keywords in age_groups.items():
            if any(keyword in target_audience for keyword in keywords):
                if any(keyword in channel_desc for keyword in keywords):
                    score += 20
                    break
        
        # Проверяем гендерные группы
        for group, keywords in gender_groups.items():
            if any(keyword in target_audience for keyword in keywords):
                if any(keyword in channel_desc for keyword in keywords):
                    score += 15
                    break
        
        return min(100.0, score)
    
    def _find_category_matches(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> List[str]:
        """Находит совпадающие тематические категории"""
        offer_text = self._extract_offer_texts(offer)
        channel_text = self._extract_channel_texts(channel)
        
        matches = []
        
        for category, keywords in self.categories.items():
            offer_has = any(word in offer_text for word in keywords)
            channel_has = any(word in channel_text for word in keywords)
            
            if offer_has and channel_has:
                matches.append(category)
        
        return matches
    
    def _identify_risk_factors(self, offer: Dict[str, Any], channel: Dict[str, Any]) -> List[str]:
        """Определяет факторы риска"""
        risks = []
        
        # Риск низкой цены
        price = float(offer.get('price', 0))
        channel_price = float(channel.get('price_per_post', 0))
        
        if channel_price > 0 and price < channel_price * 0.5:
            risks.append('Цена значительно ниже обычной для канала')
        
        # Риск несоответствия аудитории
        channel_subs = int(channel.get('subscriber_count', 0))
        requirements = offer.get('requirements', '').lower()
        
        min_subs_match = re.search(r'(\d+)', requirements)
        if min_subs_match and channel_subs < int(min_subs_match.group(1)):
            risks.append('Канал не соответствует минимальным требованиям по подписчикам')
        
        # Риск тематического несоответствия
        if not self._find_category_matches(offer, channel):
            risks.append('Отсутствует явное тематическое соответствие')
        
        return risks
    
    def _generate_optimization_tips(self, offer: Dict[str, Any], channel: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
        """Генерирует советы по оптимизации"""
        tips = []
        
        # Советы по цене
        if scores['price_attractiveness'] < 60:
            tips.append('Рассмотрите увеличение предлагаемой цены для повышения привлекательности')
        
        # Советы по аудитории
        if scores['audience_match'] < 60:
            tips.append('Уточните описание целевой аудитории для лучшего соответствия')
        
        # Советы по требованиям
        if scores['requirements_compliance'] < 80:
            tips.append('Канал не полностью соответствует требованиям - рассмотрите альтернативы')
        
        # Советы по качеству канала
        if scores['channel_quality'] < 70:
            tips.append('Канал имеет средние показатели качества - оцените риски')
        
        return tips
    
    def _estimate_market_price(self, subscribers: int) -> float:
        """Оценка рыночной цены на основе количества подписчиков"""
        if subscribers < 1000:
            return 500
        elif subscribers < 5000:
            return 1500
        elif subscribers < 10000:
            return 3000
        elif subscribers < 50000:
            return 8000
        elif subscribers < 100000:
            return 15000
        else:
            return 25000
    
    def _get_channel_historical_stats(self, channel_id: int) -> Dict[str, int]:
        """Получение исторической статистики канала"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика откликов
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_responses,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as successful_responses
                FROM offer_responses or_resp
                JOIN channels c ON c.owner_id = or_resp.user_id
                WHERE c.id = ?
            ''', (channel_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                'total_responses': result[0] if result else 0,
                'successful_responses': result[1] if result else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики канала {channel_id}: {e}")
            return {'total_responses': 0, 'successful_responses': 0}
    
    def _get_category_performance_stats(self, channel_id: int, category: str) -> Dict[str, int]:
        """Получение статистики по категории"""
        # Упрощенная версия - можно расширить при наличии категоризации офферов
        return {'category_responses': 0, 'category_successful': 0}
    
    def _detect_offer_category(self, offer: Dict[str, Any]) -> str:
        """Определение категории оффера"""
        offer_text = self._extract_offer_texts(offer)
        
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for word in keywords if word in offer_text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'general'


# Вспомогательные функции для интеграции с существующей системой

def get_advanced_suitable_offers_for_channel(channel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Улучшенная версия получения подходящих офферов для канала
    """
    try:
        from working_app import safe_execute_query, DATABASE_PATH
        
        # Получаем информацию о канале
        channel = safe_execute_query('''
            SELECT c.*, u.telegram_id as owner_telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ?
        ''', (channel_id,), fetch_one=True)
        
        if not channel:
            return []
        
        # Получаем все активные офферы
        offers = safe_execute_query('''
            SELECT DISTINCT o.*, u.username as advertiser_username, u.first_name as advertiser_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.status = 'active'
            AND o.deadline > ?
            AND o.created_by != (SELECT owner_id FROM channels WHERE id = ?)
            ORDER BY o.created_at DESC
            LIMIT ?
        ''', (
            datetime.now().date().isoformat(),
            channel_id,
            limit * 3  # Берем больше для лучшей фильтрации
        ), fetch_all=True)
        
        # Создаем экземпляр продвинутого алгоритма
        engine = AdvancedMatchingEngine(DATABASE_PATH)
        
        # Обогащаем офферы продвинутой оценкой
        enriched_offers = []
        for offer in offers:
            # Получаем продвинутую оценку
            advanced_score = engine.calculate_advanced_suitability_score(offer, channel)
            
            # Проверяем существующие отклики
            existing_response = safe_execute_query('''
                SELECT status, created_at FROM offer_responses
                WHERE offer_id = ? AND user_id = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (offer['id'], channel['owner_id']), fetch_one=True)
            
            # Добавляем всю информацию к офферу
            offer.update({
                'advanced_suitability': advanced_score,
                'suitability_score': advanced_score['total_score'],  # Совместимость со старой системой
                'existing_response': existing_response,
                'can_respond': existing_response is None or existing_response['status'] not in ['accepted', 'rejected']
            })
            
            enriched_offers.append(offer)
        
        # Сортируем по продвинутой оценке
        enriched_offers.sort(key=lambda x: x['advanced_suitability']['total_score'], reverse=True)
        
        # Возвращаем лучшие результаты
        return enriched_offers[:limit]
        
    except Exception as e:
        logger.error(f"Ошибка получения продвинутых рекомендаций для канала {channel_id}: {e}")
        return []


def analyze_offer_channel_compatibility(offer_id: int, channel_id: int) -> Dict[str, Any]:
    """
    Детальный анализ совместимости конкретного оффера и канала
    """
    try:
        from working_app import safe_execute_query, DATABASE_PATH
        
        # Получаем оффер
        offer = safe_execute_query('SELECT * FROM offers WHERE id = ?', (offer_id,), fetch_one=True)
        if not offer:
            return {'error': 'Оффер не найден'}
        
        # Получаем канал
        channel = safe_execute_query('SELECT * FROM channels WHERE id = ?', (channel_id,), fetch_one=True)
        if not channel:
            return {'error': 'Канал не найден'}
        
        # Создаем экземпляр анализатора
        engine = AdvancedMatchingEngine(DATABASE_PATH)
        
        # Получаем детальный анализ
        analysis = engine.calculate_advanced_suitability_score(offer, channel)
        
        return {
            'success': True,
            'compatibility_analysis': analysis,
            'offer_info': {
                'id': offer['id'],
                'title': offer['title'],
                'price': offer['price']
            },
            'channel_info': {
                'id': channel['id'],
                'title': channel['title'],
                'subscribers': channel['subscriber_count']
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка анализа совместимости оффера {offer_id} и канала {channel_id}: {e}")
        return {'error': f'Ошибка анализа: {str(e)}'}
