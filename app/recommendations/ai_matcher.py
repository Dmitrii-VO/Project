#!/usr/bin/env python3
"""
AI-основанная система матчинга каналов и офферов
Интеллектуальные рекомендации на основе машинного обучения
"""

import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from app.models.database import execute_db_query
from app.config.telegram_config import AppConfig

logger = logging.getLogger(__name__)

class AIChannelMatcher:
    """AI система для матчинга каналов и офферов"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=['и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'о'],
            ngram_range=(1, 2)
        )
        self.scaler = StandardScaler()
        
        # Веса для различных факторов матчинга
        self.weights = {
            'category_match': 0.3,      # Совпадение категории
            'budget_compatibility': 0.25, # Соответствие бюджета
            'audience_overlap': 0.2,    # Пересечение аудитории
            'performance_score': 0.15,  # Показатели канала
            'engagement_rate': 0.1      # Уровень вовлеченности
        }
        
        # Кэш для оптимизации
        self._channel_features_cache = {}
        self._offer_features_cache = {}
    
    def find_matching_channels(self, offer_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск подходящих каналов для оффера с AI-рекомендациями"""
        try:
            # Получаем данные оффера
            offer = execute_db_query(
                """SELECT o.*, u.telegram_id as advertiser_telegram_id
                   FROM offers o
                   JOIN users u ON o.created_by = u.id
                   WHERE o.id = ?""",
                (offer_id,),
                fetch_one=True
            )
            
            if not offer:
                return []
            
            # Получаем доступные каналы
            channels = execute_db_query(
                """SELECT c.*, u.telegram_id as owner_telegram_id,
                          AVG(p.engagement_rate) as avg_engagement,
                          AVG(p.views_count) as avg_views,
                          COUNT(p.id) as placement_count
                   FROM channels c
                   JOIN users u ON c.owner_id = u.id
                   LEFT JOIN offer_responses r ON c.id = r.channel_id
                   LEFT JOIN offer_placements p ON r.id = p.response_id
                   WHERE c.is_verified = 1 AND c.is_active = 1
                   AND c.price_per_post <= ?
                   AND NOT EXISTS (
                       SELECT 1 FROM offer_responses res 
                       WHERE res.offer_id = ? AND res.channel_id = c.id
                   )
                   GROUP BY c.id
                   ORDER BY c.subscriber_count DESC""",
                (offer.get('budget_total', offer.get('price', 999999)), offer_id)
            )
            
            if not channels:
                return []
            
            # Вычисляем scores для каждого канала
            scored_channels = []
            offer_features = self._extract_offer_features(offer)
            
            for channel in channels:
                try:
                    channel_features = self._extract_channel_features(dict(channel))
                    compatibility_score = self._calculate_compatibility_score(
                        offer_features, channel_features
                    )
                    
                    channel_data = dict(channel)
                    channel_data['compatibility_score'] = compatibility_score
                    channel_data['match_reasons'] = self._generate_match_reasons(
                        offer_features, channel_features
                    )
                    
                    scored_channels.append(channel_data)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки канала {channel['id']}: {e}")
                    continue
            
            # Сортируем по score и возвращаем топ
            scored_channels.sort(key=lambda x: x['compatibility_score'], reverse=True)
            
            return scored_channels[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI матчинга для оффера {offer_id}: {e}")
            return []
    
    def find_matching_offers(self, channel_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск подходящих офферов для канала"""
        try:
            # Получаем данные канала
            channel = execute_db_query(
                """SELECT c.*, u.telegram_id as owner_telegram_id
                   FROM channels c
                   JOIN users u ON c.owner_id = u.id
                   WHERE c.id = ?""",
                (channel_id,),
                fetch_one=True
            )
            
            if not channel:
                return []
            
            # Получаем доступные офферы
            offers = execute_db_query(
                """SELECT o.*, u.telegram_id as advertiser_telegram_id,
                          COUNT(r.id) as response_count
                   FROM offers o
                   JOIN users u ON o.created_by = u.id
                   LEFT JOIN offer_responses r ON o.id = r.offer_id
                   WHERE o.status IN ('active', 'matching')
                   AND COALESCE(o.budget_total, o.price) >= ?
                   AND NOT EXISTS (
                       SELECT 1 FROM offer_responses res 
                       WHERE res.offer_id = o.id AND res.channel_id = ?
                   )
                   GROUP BY o.id
                   ORDER BY o.created_at DESC""",
                (channel.get('price_per_post', 0), channel_id)
            )
            
            if not offers:
                return []
            
            # Вычисляем scores для каждого оффера
            scored_offers = []
            channel_features = self._extract_channel_features(dict(channel))
            
            for offer in offers:
                try:
                    offer_features = self._extract_offer_features(dict(offer))
                    compatibility_score = self._calculate_compatibility_score(
                        offer_features, channel_features
                    )
                    
                    offer_data = dict(offer)
                    offer_data['compatibility_score'] = compatibility_score
                    offer_data['match_reasons'] = self._generate_match_reasons(
                        offer_features, channel_features
                    )
                    
                    scored_offers.append(offer_data)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки оффера {offer['id']}: {e}")
                    continue
            
            # Сортируем по score
            scored_offers.sort(key=lambda x: x['compatibility_score'], reverse=True)
            
            return scored_offers[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка AI матчинга для канала {channel_id}: {e}")
            return []
    
    def get_personalized_recommendations(self, user_id: int, recommendation_type: str, 
                                       limit: int = 10) -> List[Dict[str, Any]]:
        """Персонализированные рекомендации для пользователя"""
        try:
            # Получаем профиль пользователя
            user_profile = self._build_user_profile(user_id)
            
            if recommendation_type == 'channels_for_advertiser':
                return self._recommend_channels_for_advertiser(user_profile, limit)
            elif recommendation_type == 'offers_for_channel_owner':
                return self._recommend_offers_for_channel_owner(user_profile, limit)
            elif recommendation_type == 'trending_offers':
                return self._get_trending_offers(limit)
            elif recommendation_type == 'similar_channels':
                return self._get_similar_channels(user_profile, limit)
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка персональных рекомендаций: {e}")
            return []
    
    def _extract_offer_features(self, offer: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение признаков из оффера"""
        try:
            # Базовые признаки
            features = {
                'category': offer.get('category', 'other'),
                'budget': offer.get('budget_total', offer.get('price', 0)),
                'title': offer.get('title', ''),
                'description': offer.get('description', ''),
                'target_audience': offer.get('target_audience', ''),
                'created_days_ago': self._days_since_creation(offer.get('created_at')),
                'placement_type': offer.get('placement_type', 'post')
            }
            
            # Текстовые признаки
            text_content = f"{features['title']} {features['description']} {features['target_audience']}"
            features['text_content'] = text_content.lower().strip()
            
            # Бюджетная категория
            budget = features['budget']
            if budget <= 1000:
                features['budget_category'] = 'low'
            elif budget <= 5000:
                features['budget_category'] = 'medium'
            else:
                features['budget_category'] = 'high'
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения признаков оффера: {e}")
            return {}
    
    def _extract_channel_features(self, channel: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение признаков из канала"""
        try:
            # Базовые признаки
            features = {
                'category': channel.get('category', 'other'),
                'subscriber_count': channel.get('subscriber_count', 0),
                'price_per_post': channel.get('price_per_post', 0),
                'title': channel.get('title', ''),
                'description': channel.get('description', ''),
                'avg_engagement': channel.get('avg_engagement', 0) or 0,
                'avg_views': channel.get('avg_views', 0) or 0,
                'placement_count': channel.get('placement_count', 0) or 0,
                'verification_days_ago': self._days_since_verification(channel.get('verified_at')),
                'is_premium': channel.get('subscriber_count', 0) > 10000
            }
            
            # Текстовые признаки
            text_content = f"{features['title']} {features['description']}"
            features['text_content'] = text_content.lower().strip()
            
            # Категория размера
            subscribers = features['subscriber_count']
            if subscribers <= 1000:
                features['size_category'] = 'small'
            elif subscribers <= 10000:
                features['size_category'] = 'medium'
            else:
                features['size_category'] = 'large'
            
            # Рейтинг производительности
            features['performance_score'] = self._calculate_performance_score(features)
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения признаков канала: {e}")
            return {}
    
    def _calculate_compatibility_score(self, offer_features: Dict[str, Any], 
                                     channel_features: Dict[str, Any]) -> float:
        """Расчет совместимости оффера и канала на основе ML"""
        try:
            score_components = {}
            
            # 1. Совпадение категории
            category_score = 1.0 if offer_features.get('category') == channel_features.get('category') else 0.3
            score_components['category_match'] = category_score
            
            # 2. Совместимость бюджета
            offer_budget = offer_features.get('budget', 0)
            channel_price = channel_features.get('price_per_post', 0)
            
            if channel_price == 0:
                budget_score = 0.5
            else:
                ratio = offer_budget / channel_price
                if 0.8 <= ratio <= 1.5:
                    budget_score = 1.0
                elif 0.5 <= ratio <= 2.0:
                    budget_score = 0.7
                else:
                    budget_score = 0.3
            
            score_components['budget_compatibility'] = budget_score
            
            # 3. Семантическое сходство текстов
            offer_text = offer_features.get('text_content', '')
            channel_text = channel_features.get('text_content', '')
            
            if offer_text and channel_text:
                text_similarity = self._calculate_text_similarity(offer_text, channel_text)
            else:
                text_similarity = 0.0
                
            score_components['audience_overlap'] = text_similarity
            
            # 4. Производительность канала
            performance_score = min(channel_features.get('performance_score', 0), 1.0)
            score_components['performance_score'] = performance_score
            
            # 5. Уровень вовлеченности
            engagement = channel_features.get('avg_engagement', 0)
            engagement_score = min(engagement / 10.0, 1.0)  # Нормализуем к 1.0
            score_components['engagement_rate'] = engagement_score
            
            # Итоговый weighted score
            total_score = sum(
                score_components[component] * self.weights[component]
                for component in self.weights.keys()
                if component in score_components
            )
            
            return min(max(total_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета совместимости: {e}")
            return 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Расчет семантического сходства текстов"""
        try:
            if not text1 or not text2:
                return 0.0
            
            # Используем TF-IDF векторизацию
            texts = [text1, text2]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Вычисляем косинусное сходство
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return float(similarity_matrix[0, 1])
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета текстового сходства: {e}")
            return 0.0
    
    def _calculate_performance_score(self, channel_features: Dict[str, Any]) -> float:
        """Расчет рейтинга производительности канала"""
        try:
            score = 0.0
            
            # Базовый score от количества подписчиков
            subscribers = channel_features.get('subscriber_count', 0)
            if subscribers > 0:
                score += min(np.log10(subscribers) / 6.0, 0.4)  # Максимум 0.4
            
            # Score от engagement rate
            engagement = channel_features.get('avg_engagement', 0)
            if engagement > 0:
                score += min(engagement / 20.0, 0.3)  # Максимум 0.3
            
            # Score от количества размещений
            placements = channel_features.get('placement_count', 0)
            if placements > 0:
                score += min(placements / 50.0, 0.2)  # Максимум 0.2
            
            # Score от среднего количества просмотров
            avg_views = channel_features.get('avg_views', 0)
            if avg_views > 0:
                score += min(avg_views / 10000.0, 0.1)  # Максимум 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета производительности: {e}")
            return 0.0
    
    def _generate_match_reasons(self, offer_features: Dict[str, Any], 
                              channel_features: Dict[str, Any]) -> List[str]:
        """Генерация причин совместимости для объяснения рекомендации"""
        reasons = []
        
        try:
            # Проверяем совпадение категории
            if offer_features.get('category') == channel_features.get('category'):
                reasons.append("Совпадение тематики")
            
            # Проверяем совместимость бюджета
            offer_budget = offer_features.get('budget', 0)
            channel_price = channel_features.get('price_per_post', 0)
            
            if channel_price > 0:
                ratio = offer_budget / channel_price
                if 0.8 <= ratio <= 1.2:
                    reasons.append("Идеальное соответствие бюджета")
                elif 0.5 <= ratio <= 2.0:
                    reasons.append("Подходящий бюджет")
            
            # Проверяем размер аудитории
            subscribers = channel_features.get('subscriber_count', 0)
            if subscribers > 10000:
                reasons.append("Большая аудитория")
            elif subscribers > 1000:
                reasons.append("Активная аудитория")
            
            # Проверяем вовлеченность
            engagement = channel_features.get('avg_engagement', 0)
            if engagement > 5:
                reasons.append("Высокая вовлеченность")
            elif engagement > 2:
                reasons.append("Хорошая вовлеченность")
            
            # Проверяем опыт размещений
            placements = channel_features.get('placement_count', 0)
            if placements > 10:
                reasons.append("Опытный в рекламе")
            elif placements > 0:
                reasons.append("Есть опыт размещений")
            
            return reasons[:3]  # Возвращаем максимум 3 причины
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации причин: {e}")
            return ["Рекомендовано AI"]
    
    def _build_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Построение профиля пользователя для персонализации"""
        try:
            # Получаем базовую информацию о пользователе
            user = execute_db_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
                fetch_one=True
            )
            
            if not user:
                return {}
            
            # Получаем историю активности
            user_channels = execute_db_query(
                "SELECT category, COUNT(*) as count FROM channels WHERE owner_id = ? GROUP BY category",
                (user_id,)
            )
            
            user_offers = execute_db_query(
                "SELECT category, COUNT(*) as count FROM offers WHERE created_by = ? GROUP BY category",
                (user_id,)
            )
            
            # Строим профиль
            profile = {
                'user_id': user_id,
                'telegram_id': user['telegram_id'],
                'preferred_categories': [],
                'avg_budget': 0,
                'activity_level': 'low',
                'role': 'mixed'  # advertiser, channel_owner, mixed
            }
            
            # Определяем предпочитаемые категории
            if user_channels:
                channel_categories = {row['category']: row['count'] for row in user_channels}
                profile['preferred_categories'].extend(channel_categories.keys())
                profile['role'] = 'channel_owner' if not user_offers else 'mixed'
            
            if user_offers:
                offer_categories = {row['category']: row['count'] for row in user_offers}
                profile['preferred_categories'].extend(offer_categories.keys())
                profile['role'] = 'advertiser' if not user_channels else 'mixed'
            
            # Убираем дубликаты
            profile['preferred_categories'] = list(set(profile['preferred_categories']))
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Ошибка построения профиля пользователя: {e}")
            return {}
    
    def _recommend_channels_for_advertiser(self, user_profile: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Рекомендации каналов для рекламодателя"""
        try:
            # Получаем топ каналы в предпочитаемых категориях
            preferred_categories = user_profile.get('preferred_categories', [])
            
            if preferred_categories:
                category_filter = "AND c.category IN ({})".format(
                    ','.join(['?' for _ in preferred_categories])
                )
                params = preferred_categories + [limit]
            else:
                category_filter = ""
                params = [limit]
            
            channels = execute_db_query(
                f"""SELECT c.*, u.telegram_id as owner_telegram_id,
                           AVG(p.engagement_rate) as avg_engagement,
                           COUNT(p.id) as placement_count
                    FROM channels c
                    JOIN users u ON c.owner_id = u.id
                    LEFT JOIN offer_responses r ON c.id = r.channel_id
                    LEFT JOIN offer_placements p ON r.id = p.response_id
                    WHERE c.is_verified = 1 AND c.is_active = 1
                    {category_filter}
                    GROUP BY c.id
                    ORDER BY c.subscriber_count DESC, avg_engagement DESC
                    LIMIT ?""",
                params
            )
            
            return [dict(channel) for channel in channels]
            
        except Exception as e:
            logger.error(f"❌ Ошибка рекомендаций каналов: {e}")
            return []
    
    def _recommend_offers_for_channel_owner(self, user_profile: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Рекомендации офферов для владельца канала"""
        try:
            preferred_categories = user_profile.get('preferred_categories', [])
            
            if preferred_categories:
                category_filter = "AND o.category IN ({})".format(
                    ','.join(['?' for _ in preferred_categories])
                )
                params = preferred_categories + [limit]
            else:
                category_filter = ""
                params = [limit]
            
            offers = execute_db_query(
                f"""SELECT o.*, u.telegram_id as advertiser_telegram_id,
                           COUNT(r.id) as response_count
                    FROM offers o
                    JOIN users u ON o.created_by = u.id
                    LEFT JOIN offer_responses r ON o.id = r.offer_id
                    WHERE o.status IN ('active', 'matching')
                    {category_filter}
                    GROUP BY o.id
                    ORDER BY COALESCE(o.budget_total, o.price) DESC, o.created_at DESC
                    LIMIT ?""",
                params
            )
            
            return [dict(offer) for offer in offers]
            
        except Exception as e:
            logger.error(f"❌ Ошибка рекомендаций офферов: {e}")
            return []
    
    def _get_trending_offers(self, limit: int) -> List[Dict[str, Any]]:
        """Получение трендовых офферов"""
        try:
            offers = execute_db_query(
                """SELECT o.*, u.telegram_id as advertiser_telegram_id,
                          COUNT(r.id) as response_count,
                          AVG(r.proposed_price) as avg_proposed_price
                   FROM offers o
                   JOIN users u ON o.created_by = u.id
                   LEFT JOIN offer_responses r ON o.id = r.offer_id
                   WHERE o.status IN ('active', 'matching')
                   AND o.created_at >= datetime('now', '-7 days')
                   GROUP BY o.id
                   HAVING response_count > 0
                   ORDER BY response_count DESC, o.created_at DESC
                   LIMIT ?""",
                (limit,)
            )
            
            return [dict(offer) for offer in offers]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения трендовых офферов: {e}")
            return []
    
    def _get_similar_channels(self, user_profile: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Получение похожих каналов"""
        try:
            # В реальной реализации здесь должен быть более сложный алгоритм
            # основанный на collaborative filtering
            
            preferred_categories = user_profile.get('preferred_categories', [])
            
            if not preferred_categories:
                return []
            
            channels = execute_db_query(
                """SELECT c.*, u.telegram_id as owner_telegram_id
                   FROM channels c
                   JOIN users u ON c.owner_id = u.id
                   WHERE c.is_verified = 1 AND c.is_active = 1
                   AND c.category IN ({})
                   ORDER BY c.subscriber_count DESC
                   LIMIT ?""".format(','.join(['?' for _ in preferred_categories])),
                preferred_categories + [limit]
            )
            
            return [dict(channel) for channel in channels]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения похожих каналов: {e}")
            return []
    
    def _days_since_creation(self, created_at: str) -> int:
        """Количество дней с момента создания"""
        try:
            if not created_at:
                return 0
            created_date = datetime.fromisoformat(created_at)
            return (datetime.now() - created_date).days
        except:
            return 0
    
    def _days_since_verification(self, verified_at: str) -> int:
        """Количество дней с момента верификации"""
        try:
            if not verified_at:
                return 999  # Не верифицирован
            verified_date = datetime.fromisoformat(verified_at)
            return (datetime.now() - verified_date).days
        except:
            return 999