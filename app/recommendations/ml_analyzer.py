#!/usr/bin/env python3
"""
ML анализатор
Машинное обучение для анализа и предсказания эффективности
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class MLAnalyzer:
    """ML анализатор данных"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.scaler = StandardScaler()
        self.channel_clusters = None
        self.offer_clusters = None
    
    def analyze_channel_categories(self, channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ категорий каналов"""
        try:
            if not channels:
                return {'success': False, 'error': 'Нет данных для анализа'}
            
            # Извлекаем текстовые данные
            texts = []
            for channel in channels:
                text_parts = [
                    channel.get('title', ''),
                    channel.get('description', ''),
                    channel.get('category', ''),
                    ' '.join(channel.get('topics', []) if isinstance(channel.get('topics'), list) else [])
                ]
                texts.append(' '.join(filter(None, text_parts)))
            
            if not any(texts):
                return {'success': False, 'error': 'Нет текстовых данных'}
            
            # TF-IDF векторизация
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Кластеризация
            n_clusters = min(5, len(channels))  # Максимум 5 кластеров
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix.toarray())
            
            # Группировка каналов по кластерам
            clusters = {}
            for i, channel in enumerate(channels):
                cluster_id = int(cluster_labels[i])
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(channel)
            
            self.channel_clusters = kmeans
            
            return {
                'success': True,
                'data': {
                    'clusters': clusters,
                    'n_clusters': n_clusters,
                    'cluster_labels': cluster_labels.tolist()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа категорий каналов: {e}")
            return {'success': False, 'error': str(e)}
    
    def predict_channel_performance(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Предсказание производительности канала"""
        try:
            # Извлекаем числовые признаки
            features = [
                channel_data.get('subscriber_count', 0),
                channel_data.get('engagement_rate', 0.0) * 100,
                channel_data.get('post_frequency', 1),
                len(channel_data.get('description', '')),
                1 if channel_data.get('verification_status') == 'verified' else 0
            ]
            
            # Нормализация признаков
            features_array = np.array(features).reshape(1, -1)
            
            # Простая модель оценки (в реальной системе здесь была бы обученная модель)
            score = self._calculate_performance_score(features)
            
            # Классификация
            if score >= 80:
                performance_class = 'excellent'
                description = 'Отличная производительность'
            elif score >= 60:
                performance_class = 'good'
                description = 'Хорошая производительность'
            elif score >= 40:
                performance_class = 'average'
                description = 'Средняя производительность'
            else:
                performance_class = 'poor'
                description = 'Низкая производительность'
            
            return {
                'success': True,
                'data': {
                    'performance_score': round(score, 2),
                    'performance_class': performance_class,
                    'description': description,
                    'features_used': len(features),
                    'predicted_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка предсказания производительности: {e}")
            return {'success': False, 'error': str(e)}
    
    def analyze_offer_targeting(self, offer_data: Dict[str, Any], channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ таргетинга оффера"""
        try:
            if not channels:
                return {'success': False, 'error': 'Нет каналов для анализа'}
            
            # Анализируем соответствие оффера каналам
            offer_keywords = self._extract_keywords(offer_data)
            
            channel_scores = []
            for channel in channels:
                channel_keywords = self._extract_keywords(channel)
                similarity_score = self._calculate_keyword_similarity(offer_keywords, channel_keywords)
                
                # Дополнительные факторы
                audience_match = self._calculate_audience_match(offer_data, channel)
                budget_fit = self._calculate_budget_fit(offer_data, channel)
                
                total_score = (similarity_score * 0.5) + (audience_match * 0.3) + (budget_fit * 0.2)
                
                channel_scores.append({
                    'channel_id': channel.get('id'),
                    'channel_title': channel.get('title'),
                    'total_score': round(total_score, 2),
                    'similarity_score': round(similarity_score, 2),
                    'audience_match': round(audience_match, 2),
                    'budget_fit': round(budget_fit, 2)
                })
            
            # Сортируем по общему счету
            channel_scores.sort(key=lambda x: x['total_score'], reverse=True)
            
            return {
                'success': True,
                'data': {
                    'channel_scores': channel_scores,
                    'total_analyzed': len(channels),
                    'offer_keywords': offer_keywords[:10]  # Первые 10 ключевых слов
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа таргетинга: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_performance_score(self, features: List[float]) -> float:
        """Расчет оценки производительности"""
        # Простая модель scoring на основе весов
        weights = [0.3, 0.4, 0.1, 0.1, 0.1]  # веса для каждого признака
        
        # Нормализуем признаки
        normalized_features = [
            min(features[0] / 10000, 10),  # подписчики (до 100k = 10 баллов)
            min(features[1], 10),          # engagement rate (до 10%)
            min(features[2], 5),           # частота постов (до 5 в день)
            min(features[3] / 100, 5),     # длина описания (до 500 символов = 5 баллов)
            features[4] * 10               # верификация (10 баллов если есть)
        ]
        
        score = sum(w * f for w, f in zip(weights, normalized_features))
        return min(score * 10, 100)  # Масштабируем до 100
    
    def _extract_keywords(self, data: Dict[str, Any]) -> List[str]:
        """Извлечение ключевых слов из данных"""
        text_parts = [
            data.get('title', ''),
            data.get('description', ''),
            data.get('category', ''),
            data.get('audience_description', ''),
            ' '.join(data.get('topics', []) if isinstance(data.get('topics'), list) else [])
        ]
        
        text = ' '.join(filter(None, text_parts)).lower()
        # Простое извлечение слов (в реальной системе использовался бы NLP)
        words = text.split()
        # Фильтруем короткие слова и стоп-слова
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        return list(set(keywords))[:20]  # Уникальные слова, максимум 20
    
    def _calculate_keyword_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """Расчет схожести ключевых слов"""
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_audience_match(self, offer_data: Dict[str, Any], channel_data: Dict[str, Any]) -> float:
        """Расчет соответствия аудитории"""
        # Простая модель на основе размера аудитории и категории
        offer_min_audience = offer_data.get('target_audience_min', 0)
        offer_max_audience = offer_data.get('target_audience_max', float('inf'))
        channel_subscribers = channel_data.get('subscriber_count', 0)
        
        # Проверяем попадание в диапазон
        if offer_min_audience <= channel_subscribers <= offer_max_audience:
            audience_score = 1.0
        else:
            # Чем дальше от диапазона, тем меньше оценка
            if channel_subscribers < offer_min_audience:
                ratio = channel_subscribers / offer_min_audience if offer_min_audience > 0 else 0
            else:
                ratio = offer_max_audience / channel_subscribers if channel_subscribers > 0 else 0
            audience_score = max(0, ratio)
        
        return audience_score
    
    def _calculate_budget_fit(self, offer_data: Dict[str, Any], channel_data: Dict[str, Any]) -> float:
        """Расчет соответствия бюджета"""
        offer_budget = offer_data.get('budget_per_post', 0)
        channel_rate = channel_data.get('rate_per_post', 0)
        
        if channel_rate == 0:
            return 0.5  # Нет данных о стоимости
        
        if offer_budget >= channel_rate:
            return 1.0  # Бюджет покрывает стоимость
        else:
            return offer_budget / channel_rate  # Частичное покрытие