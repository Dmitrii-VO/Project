# app/services/offers/core/offer_validator.py
"""
Валидатор для офферов
Централизует всю логику валидации
"""

from typing import Dict, List, Any
from app.models.offer import OfferStatus
from app.models.database import execute_db_query
import logging

logger = logging.getLogger(__name__)


class OfferValidator:
    """Валидатор для офферов"""
    
    @staticmethod
    def validate_offer_data(data: Dict[str, Any]) -> List[str]:
        """Валидация данных оффера"""
        errors = []
        
        # Проверка обязательных полей
        required_fields = ['title', 'description', 'price', 'target_audience']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        # Валидация заголовка
        title = data.get('title', '')
        if len(title) < 5:
            errors.append("Заголовок должен содержать минимум 5 символов")
        elif len(title) > 200:
            errors.append("Заголовок не должен превышать 200 символов")
        
        # Валидация описания
        description = data.get('description', '')
        if len(description) < 10:
            errors.append("Описание должно содержать минимум 10 символов")
        elif len(description) > 2000:
            errors.append("Описание не должно превышать 2000 символов")
        
        # Валидация цены
        try:
            price = float(data.get('price', 0))
            if price <= 0:
                errors.append("Цена должна быть больше 0")
            elif price > 10000000:
                errors.append("Цена не должна превышать 10,000,000 рублей")
        except (ValueError, TypeError):
            errors.append("Некорректный формат цены")
        
        # Валидация бюджета
        if data.get('budget_total'):
            try:
                budget = float(data.get('budget_total', 0))
                price = float(data.get('price', 0))
                if budget < price:
                    errors.append("Общий бюджет не может быть меньше цены за пост")
            except (ValueError, TypeError):
                errors.append("Некорректный формат бюджета")
        
        # Валидация категории
        valid_categories = [
            'general', 'tech', 'finance', 'lifestyle', 'education',
            'entertainment', 'business', 'health', 'sports', 'travel', 'other'
        ]
        category = data.get('category')
        if category and category not in valid_categories:
            errors.append(f"Недопустимая категория. Доступные: {', '.join(valid_categories)}")
        
        # Валидация целевой аудитории
        target_audience = data.get('target_audience', '')
        if isinstance(target_audience, str) and len(target_audience) < 10:
            errors.append("Описание целевой аудитории должно содержать минимум 10 символов")
        
        # Валидация подписчиков
        if data.get('min_subscribers'):
            try:
                min_subs = int(data.get('min_subscribers', 0))
                if min_subs < 0:
                    errors.append("Минимальное количество подписчиков не может быть отрицательным")
            except (ValueError, TypeError):
                errors.append("Некорректный формат минимального количества подписчиков")
        
        if data.get('max_subscribers'):
            try:
                max_subs = int(data.get('max_subscribers', 0))
                min_subs = int(data.get('min_subscribers', 0))
                if max_subs < min_subs:
                    errors.append("Максимальное количество подписчиков не может быть меньше минимального")
            except (ValueError, TypeError):
                errors.append("Некорректный формат максимального количества подписчиков")
        
        # Валидация длительности
        if data.get('duration_days'):
            try:
                duration = int(data.get('duration_days', 30))
                if duration < 1:
                    errors.append("Длительность должна быть минимум 1 день")
                elif duration > 365:
                    errors.append("Длительность не должна превышать 365 дней")
            except (ValueError, TypeError):
                errors.append("Некорректный формат длительности")
        
        return errors
    
    @staticmethod
    def validate_status_transition(offer_id: int, new_status: str) -> bool:
        """Валидация перехода статуса оффера"""
        try:
            # Получаем текущий статус
            offer = execute_db_query(
                "SELECT status FROM offers WHERE id = ?",
                (offer_id,),
                fetch_one=True
            )
            
            if not offer:
                return False
            
            current_status = offer['status']
            
            # Определяем допустимые переходы
            allowed_transitions = {
                'draft': ['active', 'cancelled'],
                'active': ['paused', 'completed', 'cancelled'],
                'paused': ['active', 'completed', 'cancelled'],
                'completed': [],  # Завершенные офферы нельзя изменять
                'cancelled': [],  # Отмененные офферы нельзя изменять
                'expired': []     # Истекшие офферы нельзя изменять
            }
            
            return new_status in allowed_transitions.get(current_status, [])
            
        except Exception as e:
            logger.error(f"Ошибка валидации перехода статуса: {e}")
            return False
    
    @staticmethod
    def validate_offer_ownership(offer_id: int, user_db_id: int) -> bool:
        """Проверка принадлежности оффера пользователю"""
        try:
            offer = execute_db_query(
                "SELECT created_by FROM offers WHERE id = ?",
                (offer_id,),
                fetch_one=True
            )
            
            return offer and offer['created_by'] == user_db_id
            
        except Exception as e:
            logger.error(f"Ошибка проверки владения оффером: {e}")
            return False
    
    @staticmethod
    def validate_selected_channels(channel_ids: List[int]) -> List[str]:
        """Валидация выбранных каналов"""
        errors = []
        
        if not channel_ids:
            errors.append("Необходимо выбрать хотя бы один канал")
            return errors
        
        if len(channel_ids) > 50:
            errors.append("Нельзя выбрать больше 50 каналов")
        
        # Проверяем существование каналов
        try:
            channel_ids_str = ','.join(str(cid) for cid in channel_ids)
            existing_channels = execute_db_query(f"""
                SELECT id FROM channels 
                WHERE id IN ({channel_ids_str}) AND is_active = 1
            """, fetch_all=True)
            
            existing_ids = {ch['id'] for ch in existing_channels}
            missing_ids = set(channel_ids) - existing_ids
            
            if missing_ids:
                errors.append(f"Каналы не найдены или неактивны: {', '.join(map(str, missing_ids))}")
                
        except Exception as e:
            logger.error(f"Ошибка валидации каналов: {e}")
            errors.append("Ошибка проверки каналов")
        
        return errors
    
    @staticmethod
    def validate_offer_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация и очистка фильтров для офферов"""
        cleaned_filters = {}
        
        # Валидация пагинации
        page = filters.get('page', 1)
        try:
            page = max(1, int(page))
            cleaned_filters['page'] = page
        except (ValueError, TypeError):
            cleaned_filters['page'] = 1
        
        limit = filters.get('limit', 50)
        try:
            limit = max(1, min(100, int(limit)))  # От 1 до 100
            cleaned_filters['limit'] = limit
        except (ValueError, TypeError):
            cleaned_filters['limit'] = 50
        
        # Валидация статуса
        status = filters.get('status')
        valid_statuses = ['active', 'draft', 'paused', 'completed', 'cancelled', 'expired']
        if status and status in valid_statuses:
            cleaned_filters['status'] = status
        
        # Валидация категории
        category = filters.get('category')
        valid_categories = [
            'general', 'tech', 'finance', 'lifestyle', 'education',
            'entertainment', 'business', 'health', 'sports', 'travel', 'other'
        ]
        if category and category in valid_categories:
            cleaned_filters['category'] = category
        
        # Валидация поиска
        search = filters.get('search', '').strip()
        if search and len(search) >= 2:  # Минимум 2 символа для поиска
            cleaned_filters['search'] = search[:100]  # Максимум 100 символов
        
        return cleaned_filters
    
    @staticmethod
    def validate_response_data(data: Dict[str, Any]) -> List[str]:
        """Валидация данных отклика на оффер"""
        errors = []
        
        # Проверка сообщения
        message = data.get('message', '').strip()
        if not message:
            errors.append("Сообщение обязательно")
        elif len(message) < 10:
            errors.append("Сообщение должно содержать минимум 10 символов")
        elif len(message) > 1000:
            errors.append("Сообщение не должно превышать 1000 символов")
        
        # Проверка канала (если указан)
        channel_id = data.get('channel_id')
        if channel_id:
            try:
                channel_id = int(channel_id)
                if channel_id <= 0:
                    errors.append("Некорректный ID канала")
            except (ValueError, TypeError):
                errors.append("Некорректный формат ID канала")
        
        return errors
    
    @staticmethod
    def validate_smart_offer_data(data: Dict[str, Any]) -> List[str]:
        """Валидация данных для умного создания оффера"""
        errors = []
        
        # Проверка обязательных полей для умного оффера
        required_fields = ['title', 'description', 'category', 'budget']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Поле '{field}' обязательно для заполнения")
        
        # Валидация заголовка
        title = data.get('title', '').strip()
        if len(title) < 10:
            errors.append("Название должно содержать минимум 10 символов")
        elif len(title) > 100:
            errors.append("Название не должно превышать 100 символов")
        
        # Валидация описания
        description = data.get('description', '').strip()
        if len(description) < 50:
            errors.append("Описание должно содержать минимум 50 символов")
        elif len(description) > 1000:
            errors.append("Описание не должно превышать 1000 символов")
        
        # Валидация бюджета
        try:
            budget = float(data.get('budget', 0))
            if budget < 1000:
                errors.append("Минимальный бюджет: 1,000₽")
            elif budget > 10000000:
                errors.append("Бюджет не должен превышать 10,000,000₽")
        except (ValueError, TypeError):
            errors.append("Некорректный формат бюджета")
        
        # Валидация категории
        category = data.get('category')
        valid_categories = [
            'tech', 'business', 'lifestyle', 'entertainment', 'education',
            'health', 'travel', 'food', 'fashion', 'crypto'
        ]
        if category not in valid_categories:
            errors.append(f"Недопустимая категория. Доступные: {', '.join(valid_categories)}")
        
        # Валидация выбранных каналов
        selected_channels = data.get('selected_channels', [])
        if not selected_channels:
            errors.append("Необходимо выбрать хотя бы один канал")
        elif len(selected_channels) > 20:
            errors.append("Нельзя выбрать больше 20 каналов за раз")
        
        # Валидация требований к каналам
        channel_requirements = data.get('channel_requirements', [])
        for req in channel_requirements:
            if not isinstance(req, dict):
                errors.append("Некорректный формат требований к каналу")
                continue
                
            channel_id = req.get('channel_id')
            if channel_id and channel_id not in selected_channels:
                errors.append(f"Требования указаны для невыбранного канала {channel_id}")
                
            # Валидация кастомной цены
            custom_price = req.get('custom_price')
            if custom_price:
                try:
                    price = float(custom_price)
                    if price <= 0:
                        errors.append(f"Кастомная цена для канала {channel_id} должна быть больше 0")
                except (ValueError, TypeError):
                    errors.append(f"Некорректная кастомная цена для канала {channel_id}")
        
        # Валидация даты дедлайна
        deadline = data.get('deadline')
        if deadline:
            try:
                from datetime import datetime
                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                if deadline_date <= datetime.now():
                    errors.append("Дата размещения должна быть в будущем")
            except (ValueError, TypeError):
                errors.append("Некорректный формат даты размещения")
        
        return errors