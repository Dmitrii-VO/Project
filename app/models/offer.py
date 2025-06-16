# app/models/offer.py
"""
Модель офферов (рекламных предложений) для Telegram Mini App
Поддерживает создание офферов, систему сопоставления и управление откликами
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from .database import db_manager
from ..utils.exceptions import OfferError, ValidationError, InsufficientFundsError
from ..config.settings import MIN_OFFER_BUDGET, MAX_OFFER_DURATION_DAYS


class OfferStatus(Enum):
    """Статусы офферов"""
    DRAFT = 'draft'
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class OfferType(Enum):
    """Типы офферов"""
    SINGLE_POST = 'single_post'
    MULTIPLE_POSTS = 'multiple_posts'
    STORY = 'story'
    PINNED_POST = 'pinned_post'
    INTEGRATION = 'integration'
    REVIEW = 'review'


class ContentType(Enum):
    """Типы контента"""
    TEXT = 'text'
    IMAGE = 'image'
    VIDEO = 'video'
    LINK = 'link'
    POLL = 'poll'
    MIXED = 'mixed'


class Offer:
    """Модель оффера (рекламного предложения)"""

    def __init__(self, offer_data: Dict[str, Any] = None):
        if offer_data:
            self.id = offer_data.get('id')
            self.title = offer_data.get('title')
            self.description = offer_data.get('description')
            self.content = offer_data.get('content', '')
            self.ad_text = offer_data.get('ad_text', '')
            self.media_urls = self._parse_media_urls(offer_data.get('media_urls'))
            self.content_type = offer_data.get('content_type', ContentType.TEXT.value)
            self.offer_type = offer_data.get('offer_type', OfferType.SINGLE_POST.value)
            self.budget = Decimal(str(offer_data.get('budget', 0)))
            self.max_price_per_post = Decimal(str(offer_data.get('max_price_per_post', 0)))
            self.category = offer_data.get('category')
            self.subcategory = offer_data.get('subcategory')
            self.target_audience = self._parse_target_audience(offer_data.get('target_audience'))
            self.targeting_criteria = self._parse_targeting_criteria(offer_data.get('targeting_criteria'))
            self.posting_requirements = self._parse_posting_requirements(offer_data.get('posting_requirements'))
            self.status = offer_data.get('status', OfferStatus.DRAFT.value)
            self.advertiser_id = offer_data.get('advertiser_id')
            self.analytics_goals = self._parse_analytics_goals(offer_data.get('analytics_goals'))
            self.expires_at = offer_data.get('expires_at')
            self.created_at = offer_data.get('created_at')
            self.updated_at = offer_data.get('updated_at')
            self.published_at = offer_data.get('published_at')
            self.completed_at = offer_data.get('completed_at')
        else:
            self.id = None
            self.title = None
            self.description = None
            self.content = ''
            self.ad_text = ''
            self.media_urls = []
            self.content_type = ContentType.TEXT.value
            self.offer_type = OfferType.SINGLE_POST.value
            self.budget = Decimal('0')
            self.max_price_per_post = Decimal('0')
            self.category = None
            self.subcategory = None
            self.target_audience = {}
            self.targeting_criteria = {}
            self.posting_requirements = {}
            self.status = OfferStatus.DRAFT.value
            self.advertiser_id = None
            self.analytics_goals = {}
            self.expires_at = None
            self.created_at = None
            self.updated_at = None
            self.published_at = None
            self.completed_at = None

    def _parse_media_urls(self, media_urls: Any) -> List[str]:
        """Парсинг медиа URL из JSON"""
        if isinstance(media_urls, str):
            try:
                return json.loads(media_urls)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(media_urls, list):
            return media_urls
        return []

    def _parse_target_audience(self, target_audience: Any) -> Dict[str, Any]:
        """Парсинг целевой аудитории из JSON"""
        if isinstance(target_audience, str):
            try:
                return json.loads(target_audience)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(target_audience, dict):
            return target_audience
        return {}

    def _parse_targeting_criteria(self, targeting_criteria: Any) -> Dict[str, Any]:
        """Парсинг критериев таргетинга из JSON"""
        if isinstance(targeting_criteria, str):
            try:
                return json.loads(targeting_criteria)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(targeting_criteria, dict):
            return targeting_criteria
        return {}

    def _parse_posting_requirements(self, posting_requirements: Any) -> Dict[str, Any]:
        """Парсинг требований к размещению из JSON"""
        if isinstance(posting_requirements, str):
            try:
                return json.loads(posting_requirements)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(posting_requirements, dict):
            return posting_requirements
        return {}

    def _parse_analytics_goals(self, analytics_goals: Any) -> Dict[str, Any]:
        """Парсинг целей аналитики из JSON"""
        if isinstance(analytics_goals, str):
            try:
                return json.loads(analytics_goals)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(analytics_goals, dict):
            return analytics_goals
        return {}

    def save(self) -> bool:
        """Сохранение оффера в базу данных"""
        try:
            media_urls_json = json.dumps(self.media_urls) if self.media_urls else None
            target_audience_json = json.dumps(self.target_audience) if self.target_audience else None
            targeting_criteria_json = json.dumps(self.targeting_criteria) if self.targeting_criteria else None
            posting_requirements_json = json.dumps(self.posting_requirements) if self.posting_requirements else None
            analytics_goals_json = json.dumps(self.analytics_goals) if self.analytics_goals else None

            if self.id:
                # Обновление существующего оффера
                query = """
                        UPDATE offers
                        SET title                = ?, \
                            description          = ?, \
                            content              = ?, \
                            ad_text              = ?,
                            media_urls           = ?, \
                            content_type         = ?, \
                            offer_type           = ?,
                            budget               = ?, \
                            max_price_per_post   = ?, \
                            category             = ?, \
                            subcategory          = ?,
                            target_audience      = ?, \
                            targeting_criteria   = ?, \
                            posting_requirements = ?,
                            status               = ?, \
                            analytics_goals      = ?, \
                            expires_at           = ?,
                            updated_at           = CURRENT_TIMESTAMP, \
                            published_at         = ?, \
                            completed_at         = ?
                        WHERE id = ? \
                        """
                params = (
                    self.title, self.description, self.content, self.ad_text,
                    media_urls_json, self.content_type, self.offer_type,
                    float(self.budget), float(self.max_price_per_post),
                    self.category, self.subcategory, target_audience_json,
                    targeting_criteria_json, posting_requirements_json,
                    self.status, analytics_goals_json, self.expires_at,
                    self.published_at, self.completed_at, self.id
                )
            else:
                # Создание нового оффера
                query = """
                        INSERT INTO offers (title, description, content, ad_text, media_urls, \
                                            content_type, offer_type, budget, max_price_per_post, \
                                            category, subcategory, target_audience, targeting_criteria, \
                                            posting_requirements, status, advertiser_id, analytics_goals, \
                                            expires_at, created_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) \
                        """
                params = (
                    self.title, self.description, self.content, self.ad_text,
                    media_urls_json, self.content_type, self.offer_type,
                    float(self.budget), float(self.max_price_per_post),
                    self.category, self.subcategory, target_audience_json,
                    targeting_criteria_json, posting_requirements_json,
                    self.status, self.advertiser_id, analytics_goals_json,
                    self.expires_at
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового оффера
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise OfferError(f"Ошибка сохранения оффера: {str(e)}")

    @classmethod
    def get_by_id(cls, offer_id: int) -> Optional['Offer']:
        """Получение оффера по ID"""
        query = "SELECT * FROM offers WHERE id = ?"
        result = db_manager.execute_query(query, (offer_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_advertiser_offers(cls, advertiser_id: int, status: str = None,
                              limit: int = 50) -> List['Offer']:
        """Получение офферов рекламодателя"""
        query = "SELECT * FROM offers WHERE advertiser_id = ?"
        params = [advertiser_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def get_active_offers(cls, category: str = None, limit: int = 100) -> List['Offer']:
        """Получение активных офферов"""
        query = "SELECT * FROM offers WHERE status = 'active' AND expires_at > CURRENT_TIMESTAMP"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def search_offers(cls, filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> Tuple[List['Offer'], int]:
        """Поиск офферов с фильтрами"""
        base_query = "SELECT * FROM offers WHERE status IN ('active', 'paused')"
        count_query = "SELECT COUNT(*) FROM offers WHERE status IN ('active', 'paused')"

        params = []
        conditions = []

        # Фильтр по категории
        if filters.get('category'):
            conditions.append("category = ?")
            params.append(filters['category'])

        # Фильтр по бюджету
        if filters.get('min_budget'):
            conditions.append("budget >= ?")
            params.append(filters['min_budget'])

        if filters.get('max_budget'):
            conditions.append("budget <= ?")
            params.append(filters['max_budget'])

        # Фильтр по типу оффера
        if filters.get('offer_type'):
            conditions.append("offer_type = ?")
            params.append(filters['offer_type'])

        # Поиск по тексту
        if filters.get('search'):
            conditions.append("(title LIKE ? OR description LIKE ?)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])

        # Фильтр по рекламодателю
        if filters.get('advertiser_id'):
            conditions.append("advertiser_id = ?")
            params.append(filters['advertiser_id'])

        # Добавляем условия к запросам
        if conditions:
            condition_str = " AND " + " AND ".join(conditions)
            base_query += condition_str
            count_query += condition_str

        # Получаем общее количество
        total_count = db_manager.execute_query(count_query, tuple(params), fetch_one=True)[0]

        # Добавляем сортировку и пагинацию
        base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Получаем офферы
        results = db_manager.execute_query(base_query, tuple(params), fetch_all=True)
        offers = [cls(dict(row)) for row in results] if results else []

        return offers, total_count

    @classmethod
    def create_offer(cls, advertiser_id: int, offer_data: Dict[str, Any]) -> 'Offer':
        """Создание нового оффера"""
        # Валидируем данные оффера
        cls._validate_offer_data(offer_data)

        # Проверяем баланс рекламодателя
        from .user import User
        advertiser = User.get_by_id(advertiser_id)
        if not advertiser:
            raise OfferError("Рекламодатель не найден")

        budget = Decimal(str(offer_data.get('budget', 0)))
        if advertiser.balance < budget:
            raise InsufficientFundsError("Недостаточно средств для создания оффера")

        # Создаем оффер
        offer = cls()
        offer.advertiser_id = advertiser_id
        offer.title = offer_data.get('title')
        offer.description = offer_data.get('description')
        offer.content = offer_data.get('content', '')
        offer.ad_text = offer_data.get('ad_text', '')
        offer.media_urls = offer_data.get('media_urls', [])
        offer.content_type = offer_data.get('content_type', ContentType.TEXT.value)
        offer.offer_type = offer_data.get('offer_type', OfferType.SINGLE_POST.value)
        offer.budget = budget
        offer.max_price_per_post = Decimal(str(offer_data.get('max_price_per_post', 0)))
        offer.category = offer_data.get('category')
        offer.subcategory = offer_data.get('subcategory')
        offer.target_audience = offer_data.get('target_audience', {})
        offer.targeting_criteria = offer_data.get('targeting_criteria', {})
        offer.posting_requirements = offer_data.get('posting_requirements', {})
        offer.analytics_goals = offer_data.get('analytics_goals', {})
        offer.status = OfferStatus.DRAFT.value

        # Устанавливаем срок действия (по умолчанию 30 дней)
        duration_days = offer_data.get('duration_days', 30)
        if duration_days > MAX_OFFER_DURATION_DAYS:
            duration_days = MAX_OFFER_DURATION_DAYS

        offer.expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()

        offer.save()
        return offer

    @staticmethod
    def _validate_offer_data(data: Dict[str, Any]):
        """Валидация данных оффера"""
        errors = []

        # Проверка обязательных полей
        required_fields = ['title', 'description', 'budget', 'category']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} is required')

        # Валидация бюджета
        budget = data.get('budget')
        if budget is not None:
            try:
                budget = float(budget)
                if budget < MIN_OFFER_BUDGET:
                    errors.append(f'Budget must be at least {MIN_OFFER_BUDGET} RUB')
                elif budget > 10000000:  # 10 млн максимум
                    errors.append('Budget too high (max: 10,000,000 RUB)')
            except (ValueError, TypeError):
                errors.append('Invalid budget format')

        # Валидация максимальной цены за пост
        max_price = data.get('max_price_per_post')
        if max_price is not None:
            try:
                max_price = float(max_price)
                if max_price < 0:
                    errors.append('Max price per post cannot be negative')
                elif max_price > 1000000:
                    errors.append('Max price per post too high (max: 1,000,000 RUB)')
            except (ValueError, TypeError):
                errors.append('Invalid max_price_per_post format')

        # Валидация типов
        valid_content_types = [ct.value for ct in ContentType]
        if data.get('content_type') and data['content_type'] not in valid_content_types:
            errors.append(f'Invalid content_type. Must be one of: {", ".join(valid_content_types)}')

        valid_offer_types = [ot.value for ot in OfferType]
        if data.get('offer_type') and data['offer_type'] not in valid_offer_types:
            errors.append(f'Invalid offer_type. Must be one of: {", ".join(valid_offer_types)}')

        # Валидация целевой аудитории
        target_audience = data.get('target_audience', {})
        if isinstance(target_audience, dict):
            min_subscribers = target_audience.get('min_subscribers')
            if min_subscribers is not None:
                try:
                    min_subscribers = int(min_subscribers)
                    if min_subscribers < 0:
                        errors.append('min_subscribers cannot be negative')
                except (ValueError, TypeError):
                    errors.append('Invalid min_subscribers format')

        if errors:
            raise ValidationError('; '.join(errors))

    def publish(self) -> bool:
        """Публикация оффера"""
        if self.status != OfferStatus.DRAFT.value:
            raise OfferError("Только черновики можно публиковать")

        # Проверяем баланс рекламодателя
        from .user import User
        advertiser = User.get_by_id(self.advertiser_id)
        if not advertiser or advertiser.balance < self.budget:
            raise InsufficientFundsError("Недостаточно средств для публикации оффера")

        self.status = OfferStatus.ACTIVE.value
        self.published_at = datetime.now().isoformat()

        if self.save():
            # Запускаем поиск подходящих каналов и отправку уведомлений
            self._trigger_channel_matching()
            return True

        return False

    def pause(self) -> bool:
        """Приостановка оффера"""
        if self.status != OfferStatus.ACTIVE.value:
            raise OfferError("Можно приостановить только активные офферы")

        self.status = OfferStatus.PAUSED.value
        return self.save()

    def resume(self) -> bool:
        """Возобновление оффера"""
        if self.status != OfferStatus.PAUSED.value:
            raise OfferError("Можно возобновить только приостановленные офферы")

        # Проверяем срок действия
        if self.is_expired():
            raise OfferError("Нельзя возобновить истекший оффер")

        self.status = OfferStatus.ACTIVE.value
        return self.save()

    def cancel(self, reason: str = "") -> bool:
        """Отмена оффера"""
        if self.status in [OfferStatus.COMPLETED.value, OfferStatus.CANCELLED.value]:
            raise OfferError("Нельзя отменить завершенный или уже отмененный оффер")

        self.status = OfferStatus.CANCELLED.value
        if reason:
            if 'cancellation_reason' not in self.analytics_goals:
                self.analytics_goals['cancellation_reason'] = reason

        # Возвращаем неиспользованный бюджет
        self._refund_unused_budget()

        return self.save()

    def complete(self) -> bool:
        """Завершение оффера"""
        if self.status not in [OfferStatus.ACTIVE.value, OfferStatus.PAUSED.value]:
            raise OfferError("Можно завершить только активные или приостановленные офферы")

        self.status = OfferStatus.COMPLETED.value
        self.completed_at = datetime.now().isoformat()

        # Возвращаем неиспользованный бюджет
        self._refund_unused_budget()

        return self.save()

    def is_expired(self) -> bool:
        """Проверка истечения срока оффера"""
        if not self.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now() > expires_at
        except (ValueError, AttributeError):
            return False

    def get_responses(self, status: str = None) -> List['OfferResponse']:
        """Получение откликов на оффер"""
        from .response import OfferResponse
        return OfferResponse.get_by_offer_id(self.id, status)

    def get_matching_channels(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получение подходящих каналов для оффера"""
        from .channels import ChannelMatcher

        criteria = {
            'category': self.category,
            'subcategory': self.subcategory,
            'budget': float(self.budget),
            'max_price': float(self.max_price_per_post) if self.max_price_per_post > 0 else None,
            **self.target_audience
        }

        return ChannelMatcher.find_matching_channels(criteria, limit)

    def get_analytics(self) -> Dict[str, Any]:
        """Получение аналитики по офферу"""
        responses = self.get_responses()

        total_responses = len(responses)
        accepted_responses = len([r for r in responses if r.status == 'accepted'])
        rejected_responses = len([r for r in responses if r.status == 'rejected'])
        pending_responses = len([r for r in responses if r.status == 'pending'])

        total_spent = sum(float(r.price) for r in responses if r.status == 'accepted')
        remaining_budget = float(self.budget) - total_spent

        return {
            'responses': {
                'total': total_responses,
                'accepted': accepted_responses,
                'rejected': rejected_responses,
                'pending': pending_responses,
                'acceptance_rate': (accepted_responses / total_responses * 100) if total_responses > 0 else 0
            },
            'budget': {
                'total': float(self.budget),
                'spent': total_spent,
                'remaining': remaining_budget,
                'utilization': (total_spent / float(self.budget) * 100) if self.budget > 0 else 0
            },
            'channels': {
                'applied': len(set(r.channel_id for r in responses)),
                'accepted': len(set(r.channel_id for r in responses if r.status == 'accepted'))
            },
            'estimated_reach': self._calculate_estimated_reach()
        }

    def _calculate_estimated_reach(self) -> Dict[str, Any]:
        """Расчет ожидаемого охвата"""
        accepted_responses = [r for r in self.get_responses() if r.status == 'accepted']

        total_subscribers = 0
        estimated_views = 0
        estimated_engagement = 0

        for response in accepted_responses:
            from .channels import Channel
            channel = Channel.get_by_id(response.channel_id)
            if channel:
                total_subscribers += channel.subscribers_count
                # Примерный коэффициент охвата 15-25%
                reach_coefficient = 0.2
                views = int(channel.subscribers_count * reach_coefficient)
                estimated_views += views
                estimated_engagement += int(views * 0.05)  # 5% вовлеченность

        return {
            'total_subscribers': total_subscribers,
            'estimated_views': estimated_views,
            'estimated_engagement': estimated_engagement,
            'channels_count': len(accepted_responses)
        }

    def _trigger_channel_matching(self):
        """Запуск процесса поиска подходящих каналов и отправки уведомлений"""
        try:
            from .channels import ChannelNotificationService

            # Получаем подходящие каналы
            matching_channels = self.get_matching_channels(limit=50)

            if matching_channels:
                # Отправляем уведомления владельцам каналов
                ChannelNotificationService.notify_matching_channels(self.id, matching_channels)

        except Exception as e:
            print(f"Ошибка при поиске каналов для оффера {self.id}: {e}")

    def _refund_unused_budget(self):
        """Возврат неиспользованного бюджета"""
        try:
            from .user import User
            from .payment import Payment

            analytics = self.get_analytics()
            unused_budget = analytics['budget']['remaining']

            if unused_budget > 0:
                # Возвращаем деньги на баланс рекламодателя
                advertiser = User.get_by_id(self.advertiser_id)
                if advertiser:
                    advertiser.update_balance(unused_budget)

                    # Создаем запись о возврате
                    Payment.create_deposit(
                        self.advertiser_id,
                        Decimal(str(unused_budget)),
                        'balance',
                        description=f"Возврат неиспользованного бюджета оффера #{self.id}"
                    )

        except Exception as e:
            print(f"Ошибка возврата бюджета для оффера {self.id}: {e}")

    def update_budget(self, new_budget: float) -> bool:
        """Обновление бюджета оффера"""
        if self.status not in [OfferStatus.DRAFT.value, OfferStatus.ACTIVE.value, OfferStatus.PAUSED.value]:
            raise OfferError("Нельзя изменить бюджет завершенного или отмененного оффера")

        new_budget_decimal = Decimal(str(new_budget))

        if new_budget_decimal < MIN_OFFER_BUDGET:
            raise ValidationError(f"Бюджет должен быть не менее {MIN_OFFER_BUDGET} RUB")

        # Проверяем, что новый бюджет покрывает уже потраченные средства
        analytics = self.get_analytics()
        spent = analytics['budget']['spent']

        if new_budget < spent:
            raise ValidationError("Новый бюджет не может быть меньше уже потраченных средств")

        # Проверяем баланс рекламодателя для увеличения бюджета
        if new_budget_decimal > self.budget:
            from .user import User
            advertiser = User.get_by_id(self.advertiser_id)
            budget_increase = new_budget_decimal - self.budget

            if not advertiser or advertiser.balance < budget_increase:
                raise InsufficientFundsError("Недостаточно средств для увеличения бюджета")

        self.budget = new_budget_decimal
        return self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'ad_text': self.ad_text,
            'media_urls': self.media_urls,
            'content_type': self.content_type,
            'offer_type': self.offer_type,
            'budget': float(self.budget),
            'max_price_per_post': float(self.max_price_per_post),
            'category': self.category,
            'subcategory': self.subcategory,
            'target_audience': self.target_audience,
            'targeting_criteria': self.targeting_criteria,
            'posting_requirements': self.posting_requirements,
            'status': self.status,
            'advertiser_id': self.advertiser_id,
            'analytics_goals': self.analytics_goals,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'published_at': self.published_at,
            'completed_at': self.completed_at
        }


class OfferResponse:
    """Модель отклика на оффер"""

    def __init__(self, response_data: Dict[str, Any] = None):
        if response_data:
            self.id = response_data.get('id')
            self.offer_id = response_data.get('offer_id')
            self.channel_id = response_data.get('channel_id')
            self.channel_owner_id = response_data.get('channel_owner_id')
            self.status = response_data.get('status', 'pending')
            self.price = Decimal(str(response_data.get('price', 0)))
            self.proposed_posting_time = response_data.get('proposed_posting_time')
            self.message = response_data.get('message', '')
            self.counter_offer = self._parse_counter_offer(response_data.get('counter_offer'))
            self.rejection_reason = response_data.get('rejection_reason')
            self.posted_at = response_data.get('posted_at')
            self.post_url = response_data.get('post_url')
            self.performance_metrics = self._parse_performance_metrics(response_data.get('performance_metrics'))
            self.created_at = response_data.get('created_at')
            self.updated_at = response_data.get('updated_at')
        else:
            self.id = None
            self.offer_id = None
            self.channel_id = None
            self.channel_owner_id = None
            self.status = 'pending'
            self.price = Decimal('0')
            self.proposed_posting_time = None
            self.message = ''
            self.counter_offer = {}
            self.rejection_reason = None
            self.posted_at = None
            self.post_url = None
            self.performance_metrics = {}
            self.created_at = None
            self.updated_at = None

    def _parse_counter_offer(self, counter_offer: Any) -> Dict[str, Any]:
        """Парсинг встречного предложения из JSON"""
        if isinstance(counter_offer, str):
            try:
                return json.loads(counter_offer)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(counter_offer, dict):
            return counter_offer
        return {}

    def _parse_performance_metrics(self, performance_metrics: Any) -> Dict[str, Any]:
        """Парсинг метрик производительности из JSON"""
        if isinstance(performance_metrics, str):
            try:
                return json.loads(performance_metrics)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(performance_metrics, dict):
            return performance_metrics
        return {}

    def save(self) -> bool:
        """Сохранение отклика в базу данных"""
        try:
            counter_offer_json = json.dumps(self.counter_offer) if self.counter_offer else None
            performance_metrics_json = json.dumps(self.performance_metrics) if self.performance_metrics else None

            if self.id:
                # Обновление существующего отклика
                query = """
                        UPDATE offer_responses
                        SET status                = ?, \
                            price                 = ?, \
                            proposed_posting_time = ?, \
                            message               = ?,
                            counter_offer         = ?, \
                            rejection_reason      = ?, \
                            posted_at             = ?,
                            post_url              = ?, \
                            performance_metrics   = ?, \
                            updated_at            = CURRENT_TIMESTAMP
                        WHERE id = ? \
                        """
                params = (
                    self.status, float(self.price), self.proposed_posting_time,
                    self.message, counter_offer_json, self.rejection_reason,
                    self.posted_at, self.post_url, performance_metrics_json, self.id
                )
            else:
                # Создание нового отклика
                query = """
                        INSERT INTO offer_responses (offer_id, channel_id, channel_owner_id, status, price, \
                                                     proposed_posting_time, message, counter_offer, created_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) \
                        """
                params = (
                    self.offer_id, self.channel_id, self.channel_owner_id,
                    self.status, float(self.price), self.proposed_posting_time,
                    self.message, counter_offer_json
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового отклика
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise OfferError(f"Ошибка сохранения отклика: {str(e)}")

    @classmethod
    def get_by_id(cls, response_id: int) -> Optional['OfferResponse']:
        """Получение отклика по ID"""
        query = "SELECT * FROM offer_responses WHERE id = ?"
        result = db_manager.execute_query(query, (response_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_offer_id(cls, offer_id: int, status: str = None) -> List['OfferResponse']:
        """Получение откликов по ID оффера"""
        query = "SELECT * FROM offer_responses WHERE offer_id = ?"
        params = [offer_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def get_channel_responses(cls, channel_id: int, status: str = None, limit: int = 50) -> List['OfferResponse']:
        """Получение откликов канала"""
        query = "SELECT * FROM offer_responses WHERE channel_id = ?"
        params = [channel_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def create_response(cls, offer_id: int, channel_id: int, channel_owner_id: int,
                        price: float, message: str = "", proposed_posting_time: str = None) -> 'OfferResponse':
        """Создание отклика на оффер"""
        # Проверяем, что оффер активен
        offer = Offer.get_by_id(offer_id)
        if not offer or offer.status != OfferStatus.ACTIVE.value:
            raise OfferError("Оффер не активен или не найден")

        # Проверяем, что канал не откликался ранее
        existing_response = cls._get_existing_response(offer_id, channel_id)
        if existing_response:
            raise OfferError("Канал уже откликнулся на этот оффер")

        # Проверяем цену
        if offer.max_price_per_post > 0 and Decimal(str(price)) > offer.max_price_per_post:
            raise ValidationError(f"Цена превышает максимальную ({offer.max_price_per_post} RUB)")

        # Создаем отклик
        response = cls()
        response.offer_id = offer_id
        response.channel_id = channel_id
        response.channel_owner_id = channel_owner_id
        response.price = Decimal(str(price))
        response.message = message
        response.proposed_posting_time = proposed_posting_time
        response.status = 'pending'

        response.save()

        # Уведомляем рекламодателя о новом отклике
        response._notify_advertiser()

        return response

    @classmethod
    def _get_existing_response(cls, offer_id: int, channel_id: int) -> Optional['OfferResponse']:
        """Проверка существующего отклика"""
        query = "SELECT * FROM offer_responses WHERE offer_id = ? AND channel_id = ?"
        result = db_manager.execute_query(query, (offer_id, channel_id), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    def accept(self, advertiser_id: int) -> bool:
        """Принятие отклика рекламодателем"""
        if self.status != 'pending':
            raise OfferError("Можно принять только ожидающие отклики")

        # Проверяем, что рекламодатель является владельцем оффера
        offer = Offer.get_by_id(self.offer_id)
        if not offer or offer.advertiser_id != advertiser_id:
            raise OfferError("Нет прав для принятия этого отклика")

        # Проверяем бюджет
        if offer.budget < self.price:
            raise InsufficientFundsError("Недостаточно бюджета для принятия отклика")

        self.status = 'accepted'
        success = self.save()

        if success:
            # Создаем эскроу-транзакцию
            self._create_escrow_transaction()

            # Уведомляем владельца канала
            self._notify_channel_owner('accepted')

            # Обновляем бюджет оффера
            offer.budget -= self.price
            offer.save()

        return success

    def reject(self, advertiser_id: int, reason: str = "") -> bool:
        """Отклонение отклика рекламодателем"""
        if self.status != 'pending':
            raise OfferError("Можно отклонить только ожидающие отклики")

        # Проверяем права
        offer = Offer.get_by_id(self.offer_id)
        if not offer or offer.advertiser_id != advertiser_id:
            raise OfferError("Нет прав для отклонения этого отклика")

        self.status = 'rejected'
        self.rejection_reason = reason
        success = self.save()

        if success:
            # Уведомляем владельца канала
            self._notify_channel_owner('rejected')

        return success

    def mark_as_posted(self, post_url: str = "", performance_data: Dict[str, Any] = None) -> bool:
        """Отметка о размещении поста"""
        if self.status != 'accepted':
            raise OfferError("Можно отметить размещение только для принятых откликов")

        self.status = 'posted'
        self.posted_at = datetime.now().isoformat()
        self.post_url = post_url

        if performance_data:
            self.performance_metrics.update(performance_data)

        success = self.save()

        if success:
            # Освобождаем эскроу
            self._release_escrow()

            # Уведомляем рекламодателя о размещении
            self._notify_advertiser_posting()

        return success

    def create_counter_offer(self, new_price: float, message: str = "") -> bool:
        """Создание встречного предложения"""
        if self.status != 'pending':
            raise OfferError("Встречное предложение можно создать только для ожидающих откликов")

        self.counter_offer = {
            'price': new_price,
            'message': message,
            'created_at': datetime.now().isoformat()
        }

        success = self.save()

        if success:
            # Уведомляем рекламодателя о встречном предложении
            self._notify_advertiser_counter_offer()

        return success

    def update_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Обновление метрик производительности"""
        if self.status != 'posted':
            raise OfferError("Метрики можно обновлять только для размещенных постов")

        # Обновляем метрики
        self.performance_metrics.update({
            **metrics,
            'last_updated': datetime.now().isoformat()
        })

        return self.save()

    def _create_escrow_transaction(self):
        """Создание эскроу-транзакции при принятии отклика"""
        try:
            from .payment import Payment

            Payment.create_escrow_hold(
                advertiser_id=Offer.get_by_id(self.offer_id).advertiser_id,
                channel_owner_id=self.channel_owner_id,
                amount=self.price,
                offer_response_id=self.id,
                auto_release_hours=72  # Автоматическое освобождение через 72 часа
            )

        except Exception as e:
            print(f"Ошибка создания эскроу для отклика {self.id}: {e}")

    def _release_escrow(self):
        """Освобождение эскроу при размещении поста"""
        try:
            from .payment import EscrowTransaction

            # Находим эскроу-транзакцию
            escrow = EscrowTransaction.get_by_offer_response(self.id)
            if escrow:
                escrow.release(released_by=self.channel_owner_id)

        except Exception as e:
            print(f"Ошибка освобождения эскроу для отклика {self.id}: {e}")

    def _notify_advertiser(self):
        """Уведомление рекламодателя о новом отклике"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            offer = Offer.get_by_id(self.offer_id)
            if offer:
                advertiser = User.get_by_id(offer.advertiser_id)
                if advertiser:
                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        f"📩 Новый отклик на ваш оффер '{offer.title}'\n"
                        f"💰 Предложенная цена: {self.price} ₽\n"
                        f"💬 Сообщение: {self.message[:100]}...",
                        {
                            'type': 'new_response',
                            'offer_id': self.offer_id,
                            'response_id': self.id
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления рекламодателя: {e}")

    def _notify_channel_owner(self, action: str):
        """Уведомление владельца канала о действии с откликом"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            owner = User.get_by_id(self.channel_owner_id)
            if owner:
                if action == 'accepted':
                    message = f"✅ Ваш отклик принят!\n💰 Сумма: {self.price} ₽"
                elif action == 'rejected':
                    message = f"❌ Ваш отклик отклонен"
                    if self.rejection_reason:
                        message += f"\n📝 Причина: {self.rejection_reason}"
                else:
                    message = f"📋 Статус отклика изменен: {action}"

                NotificationService.send_telegram_notification(
                    owner.telegram_id,
                    message,
                    {
                        'type': 'response_status_change',
                        'offer_id': self.offer_id,
                        'response_id': self.id,
                        'action': action
                    }
                )

        except Exception as e:
            print(f"Ошибка уведомления владельца канала: {e}")

    def _notify_advertiser_posting(self):
        """Уведомление рекламодателя о размещении поста"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            offer = Offer.get_by_id(self.offer_id)
            if offer:
                advertiser = User.get_by_id(offer.advertiser_id)
                if advertiser:
                    message = f"📢 Пост размещен!\n🎯 Оффер: {offer.title}"
                    if self.post_url:
                        message += f"\n🔗 Ссылка: {self.post_url}"

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'post_published',
                            'offer_id': self.offer_id,
                            'response_id': self.id,
                            'post_url': self.post_url
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления о размещении: {e}")

    def _notify_advertiser_counter_offer(self):
        """Уведомление рекламодателя о встречном предложении"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            offer = Offer.get_by_id(self.offer_id)
            if offer:
                advertiser = User.get_by_id(offer.advertiser_id)
                if advertiser:
                    counter_price = self.counter_offer.get('price', 0)
                    counter_message = self.counter_offer.get('message', '')

                    message = f"💱 Встречное предложение\n"
                    message += f"🎯 Оффер: {offer.title}\n"
                    message += f"💰 Новая цена: {counter_price} ₽"
                    if counter_message:
                        message += f"\n💬 Сообщение: {counter_message}"

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'counter_offer',
                            'offer_id': self.offer_id,
                            'response_id': self.id,
                            'counter_price': counter_price
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления о встречном предложении: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'offer_id': self.offer_id,
            'channel_id': self.channel_id,
            'channel_owner_id': self.channel_owner_id,
            'status': self.status,
            'price': float(self.price),
            'proposed_posting_time': self.proposed_posting_time,
            'message': self.message,
            'counter_offer': self.counter_offer,
            'rejection_reason': self.rejection_reason,
            'posted_at': self.posted_at,
            'post_url': self.post_url,
            'performance_metrics': self.performance_metrics,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class OfferAnalytics:
    """Класс для аналитики офферов"""

    @staticmethod
    def get_platform_offer_stats() -> Dict[str, Any]:
        """Получение общей статистики офферов на платформе"""
        try:
            # Общее количество офферов
            total_offers = db_manager.execute_query(
                "SELECT COUNT(*) FROM offers",
                fetch_one=True
            )[0]

            # Активные офферы
            active_offers = db_manager.execute_query(
                "SELECT COUNT(*) FROM offers WHERE status = 'active'",
                fetch_one=True
            )[0]

            # Завершенные офферы
            completed_offers = db_manager.execute_query(
                "SELECT COUNT(*) FROM offers WHERE status = 'completed'",
                fetch_one=True
            )[0]

            # Статистика бюджетов
            budget_stats = db_manager.execute_query(
                """
                SELECT SUM(budget) as total_budget,
                       AVG(budget) as avg_budget,
                       MAX(budget) as max_budget,
                       MIN(budget) as min_budget
                FROM offers
                WHERE status IN ('active', 'completed')
                """,
                fetch_one=True
            )

            # Статистика откликов
            response_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                             as total_responses,
                       SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                       SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                       SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)  as pending
                FROM offer_responses
                """,
                fetch_one=True
            )

            # Топ категории
            top_categories = db_manager.execute_query(
                """
                SELECT category, COUNT(*) as count, AVG(budget) as avg_budget
                FROM offers
                WHERE status IN ('active', 'completed') AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                    LIMIT 5
                """,
                fetch_all=True
            )

            return {
                'offers': {
                    'total': total_offers,
                    'active': active_offers,
                    'completed': completed_offers,
                    'completion_rate': (completed_offers / total_offers * 100) if total_offers > 0 else 0
                },
                'budget': {
                    'total': float(budget_stats[0] or 0),
                    'average': round(float(budget_stats[1] or 0), 2),
                    'maximum': float(budget_stats[2] or 0),
                    'minimum': float(budget_stats[3] or 0)
                },
                'responses': {
                    'total': response_stats[0],
                    'accepted': response_stats[1],
                    'rejected': response_stats[2],
                    'pending': response_stats[3],
                    'acceptance_rate': (response_stats[1] / response_stats[0] * 100) if response_stats[0] > 0 else 0
                },
                'top_categories': [
                    {
                        'category': row[0],
                        'count': row[1],
                        'avg_budget': round(float(row[2] or 0), 2)
                    }
                    for row in top_categories
                ] if top_categories else []
            }

        except Exception as e:
            raise OfferError(f"Ошибка получения статистики офферов: {str(e)}")

    @staticmethod
    def get_advertiser_performance(advertiser_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение статистики производительности рекламодателя"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Статистика офферов рекламодателя
            offer_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                              as total_offers,
                       SUM(budget)                                           as total_budget,
                       AVG(budget)                                           as avg_budget,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_offers
                FROM offers
                WHERE advertiser_id = ?
                  AND created_at >= ?
                """,
                (advertiser_id, cutoff_date),
                fetch_one=True
            )

            # Статистика откликов
            response_stats = db_manager.execute_query(
                """
                SELECT COUNT(or1.id)                                            as total_responses,
                       SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted_responses,
                       AVG(or1.price)                                           as avg_response_price
                FROM offer_responses or1
                         JOIN offers o ON or1.offer_id = o.id
                WHERE o.advertiser_id = ?
                  AND or1.created_at >= ?
                """,
                (advertiser_id, cutoff_date),
                fetch_one=True
            )

            return {
                'period_days': days,
                'offers': {
                    'total': offer_stats[0],
                    'completed': offer_stats[3],
                    'completion_rate': (offer_stats[3] / offer_stats[0] * 100) if offer_stats[0] > 0 else 0
                },
                'budget': {
                    'total_allocated': float(offer_stats[1] or 0),
                    'average_per_offer': round(float(offer_stats[2] or 0), 2)
                },
                'responses': {
                    'total_received': response_stats[0],
                    'accepted': response_stats[1],
                    'acceptance_rate': (response_stats[1] / response_stats[0] * 100) if response_stats[0] > 0 else 0,
                    'avg_price': round(float(response_stats[2] or 0), 2)
                }
            }

        except Exception as e:
            raise OfferError(f"Ошибка получения статистики рекламодателя: {str(e)}")


class OfferRecommendationEngine:
    """Движок рекомендаций для офферов"""

    @staticmethod
    def get_budget_recommendations(category: str, target_audience: Dict[str, Any]) -> Dict[str, Any]:
        """Получение рекомендаций по бюджету"""
        try:
            # Статистика по категории
            category_stats = db_manager.execute_query(
                """
                SELECT AVG(budget)             as avg_budget,
                       AVG(max_price_per_post) as avg_price_per_post,
                       COUNT(*)                as offers_count
                FROM offers
                WHERE category = ?
                  AND status IN ('active', 'completed')
                """,
                (category,),
                fetch_one=True
            )

            # Статистика откликов в категории
            response_stats = db_manager.execute_query(
                """
                SELECT AVG(or1.price) as avg_response_price
                FROM offer_responses or1
                         JOIN offers o ON or1.offer_id = o.id
                WHERE o.category = ?
                  AND or1.status = 'accepted'
                """,
                (category,),
                fetch_one=True
            )

            avg_budget = float(category_stats[0] or 0)
            avg_price_per_post = float(category_stats[1] or 0)
            avg_response_price = float(response_stats[0] or 0)

            # Корректировка по целевой аудитории
            audience_multiplier = 1.0
            min_subscribers = target_audience.get('min_subscribers', 0)

            if min_subscribers > 100000:
                audience_multiplier = 1.5
            elif min_subscribers > 50000:
                audience_multiplier = 1.3
            elif min_subscribers > 10000:
                audience_multiplier = 1.1

            recommended_budget = max(avg_budget * audience_multiplier, MIN_OFFER_BUDGET)
            recommended_max_price = max(avg_price_per_post * audience_multiplier, avg_response_price)

            return {
                'recommended_budget': round(recommended_budget, 2),
                'budget_range': {
                    'min': round(recommended_budget * 0.7, 2),
                    'max': round(recommended_budget * 1.5, 2)
                },
                'recommended_max_price_per_post': round(recommended_max_price, 2),
                'price_range': {
                    'min': round(recommended_max_price * 0.6, 2),
                    'max': round(recommended_max_price * 1.4, 2)
                },
                'market_data': {
                    'category_avg_budget': round(avg_budget, 2),
                    'category_avg_price': round(avg_price_per_post, 2),
                    'actual_avg_response_price': round(avg_response_price, 2),
                    'offers_in_category': category_stats[2]
                }
            }

        except Exception as e:
            return {
                'recommended_budget': MIN_OFFER_BUDGET,
                'budget_range': {'min': MIN_OFFER_BUDGET, 'max': MIN_OFFER_BUDGET * 5},
                'recommended_max_price_per_post': MIN_OFFER_BUDGET / 2,
                'price_range': {'min': MIN_OFFER_BUDGET / 4, 'max': MIN_OFFER_BUDGET},
                'error': str(e)
            }



    @staticmethod
    def get_timing_recommendations(category: str) -> Dict[str, Any]:
        """Получение рекомендаций по времени размещения"""
        try:
            # Анализ времени создания успешных офферов
            timing_stats = db_manager.execute_query(
                """
                SELECT strftime('%w', created_at) as day_of_week,
                       strftime('%H', created_at) as hour_of_day,
                       COUNT(*) as count,
                    AVG(
                        (SELECT COUNT(*) FROM offer_responses 
                         WHERE offer_id = offers.id AND status = 'accepted')
                    ) as avg_accepted_responses
                FROM offers
                WHERE category = ? AND status IN ('completed', 'active')
                GROUP BY day_of_week, hour_of_day
                HAVING count >= 3
                ORDER BY avg_accepted_responses DESC, count DESC
                    LIMIT 10
                """,
                (category,),
                fetch_all=True
            )

            # Преобразуем дни недели и часы в читаемый формат
            days_of_week = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

            best_times = []
            for row in timing_stats[:5]:  # Топ 5 лучших времен
                day_num = int(row[0])
                hour = int(row[1])
                day_name = days_of_week[day_num]

                best_times.append({
                    'day': day_name,
                    'hour': f"{hour:02d}:00",
                    'success_rate': round(float(row[3]), 2),
                    'offers_count': row[2]
                })

            # Общие рекомендации
            general_recommendations = [
                "Вторник-четверг обычно показывают лучшие результаты",
                "Оптимальное время: 10:00-12:00 и 14:00-16:00",
                "Избегайте выходных и поздних вечерних часов",
                "Учитывайте часовой пояс вашей целевой аудитории"
            ]

            return {
                'best_times': best_times,
                'general_recommendations': general_recommendations,
                'category': category,
                'data_points': len(timing_stats)
            }

        except Exception as e:
            return {
                'best_times': [],
                'general_recommendations': [
                    "Рекомендуем публиковать офферы в рабочие дни",
                    "Оптимальное время: 10:00-16:00",
                    "Учитывайте активность вашей целевой аудитории"
                ],
                'error': str(e)
            }

    @staticmethod
    def suggest_improvements(offer_id: int) -> List[Dict[str, Any]]:
        """Предложения по улучшению оффера"""
        try:
            offer = Offer.get_by_id(offer_id)
            if not offer:
                return []

            suggestions = []
            responses = offer.get_responses()
            analytics = offer.get_analytics()

            # Анализ откликов
            total_responses = len(responses)
            acceptance_rate = analytics['responses']['acceptance_rate']

            if total_responses == 0:
                suggestions.append({
                    'type': 'no_responses',
                    'priority': 'high',
                    'title': 'Нет откликов',
                    'description': 'Ваш оффер не получил ни одного отклика',
                    'recommendations': [
                        'Увеличьте максимальную цену за пост',
                        'Расширьте критерии целевой аудитории',
                        'Улучшите описание оффера',
                        'Проверьте актуальность категории'
                    ]
                })

            elif acceptance_rate < 20:
                suggestions.append({
                    'type': 'low_acceptance',
                    'priority': 'medium',
                    'title': 'Низкий процент принятия откликов',
                    'description': f'Только {acceptance_rate:.1f}% откликов принято',
                    'recommendations': [
                        'Пересмотрите ценовые ожидания',
                        'Улучшите условия сотрудничества',
                        'Добавьте больше деталей в описание'
                    ]
                })

            # Анализ бюджета
            budget_utilization = analytics['budget']['utilization']
            if budget_utilization < 50 and offer.status == OfferStatus.ACTIVE.value:
                suggestions.append({
                    'type': 'low_budget_usage',
                    'priority': 'low',
                    'title': 'Низкое использование бюджета',
                    'description': f'Использовано только {budget_utilization:.1f}% бюджета',
                    'recommendations': [
                        'Рассмотрите увеличение бюджета',
                        'Расширьте критерии поиска каналов',
                        'Снизьте требования к каналам'
                    ]
                })

            # Анализ цен в откликах
            if responses:
                response_prices = [float(r.price) for r in responses]
                avg_response_price = sum(response_prices) / len(response_prices)

                if offer.max_price_per_post > 0 and avg_response_price > float(offer.max_price_per_post) * 1.2:
                    suggestions.append({
                        'type': 'price_mismatch',
                        'priority': 'medium',
                        'title': 'Несоответствие цен',
                        'description': f'Средняя цена в откликах ({avg_response_price:.0f} ₽) значительно выше вашего лимита',
                        'recommendations': [
                            f'Увеличьте максимальную цену до {avg_response_price * 1.1:.0f} ₽',
                            'Пересмотрите реалистичность ценовых ожиданий',
                            'Учтите рыночные цены в вашей категории'
                        ]
                    })

            # Анализ срока действия
            if offer.expires_at:
                try:
                    expires_at = datetime.fromisoformat(offer.expires_at.replace('Z', '+00:00'))
                    days_left = (expires_at - datetime.now()).days

                    if days_left < 3 and offer.status == OfferStatus.ACTIVE.value:
                        suggestions.append({
                            'type': 'expiring_soon',
                            'priority': 'high',
                            'title': 'Оффер скоро истекает',
                            'description': f'Осталось {days_left} дн. до истечения',
                            'recommendations': [
                                'Продлите срок действия оффера',
                                'Примите больше откликов',
                                'Ускорьте процесс принятия решений'
                            ]
                        })
                except (ValueError, AttributeError):
                    pass

            return suggestions

        except Exception as e:
            return [{
                'type': 'error',
                'priority': 'low',
                'title': 'Ошибка анализа',
                'description': f'Не удалось проанализировать оффер: {str(e)}',
                'recommendations': ['Обратитесь в службу поддержки']
            }]


# Утилитарные функции для работы с офферами
class OfferUtils:
    """Утилитарные функции для работы с офферами"""

    @staticmethod
    def calculate_estimated_reach(offer: Offer) -> Dict[str, Any]:
        """Расчет ожидаемого охвата оффера"""
        try:
            # Получаем подходящие каналы
            matching_channels = offer.get_matching_channels(limit=100)

            total_subscribers = 0
            estimated_views = 0
            estimated_channels = min(len(matching_channels), 10)  # Предполагаем, что примут ~10 каналов

            # Берем топ каналов по скору совпадения
            top_channels = sorted(matching_channels, key=lambda x: x['match_score'], reverse=True)[:estimated_channels]

            for channel_match in top_channels:
                channel = channel_match['channel']
                subscribers = channel.get('subscribers_count', 0)
                total_subscribers += subscribers

                # Коэффициент охвата зависит от категории
                reach_coefficient = OfferUtils._get_reach_coefficient(channel.get('category', 'other'))
                estimated_views += int(subscribers * reach_coefficient)

            estimated_engagement = int(estimated_views * 0.05)  # 5% вовлеченность
            estimated_cost = sum(channel_match['channel'].get('price_per_post', 0) for channel_match in top_channels)

            return {
                'estimated_channels': estimated_channels,
                'total_subscribers': total_subscribers,
                'estimated_views': estimated_views,
                'estimated_engagement': estimated_engagement,
                'estimated_cost': estimated_cost,
                'cost_per_view': round(estimated_cost / estimated_views, 4) if estimated_views > 0 else 0,
                'cost_per_engagement': round(estimated_cost / estimated_engagement,
                                             2) if estimated_engagement > 0 else 0
            }

        except Exception as e:
            return {
                'estimated_channels': 0,
                'total_subscribers': 0,
                'estimated_views': 0,
                'estimated_engagement': 0,
                'estimated_cost': 0,
                'error': str(e)
            }

    @staticmethod
    def _get_reach_coefficient(category: str) -> float:
        """Получение коэффициента охвата по категории"""
        coefficients = {
            'technology': 0.15,
            'business': 0.12,
            'entertainment': 0.25,
            'news': 0.20,
            'education': 0.18,
            'lifestyle': 0.22,
            'sports': 0.20,
            'gaming': 0.30,
            'crypto': 0.25,
            'travel': 0.18,
            'food': 0.20,
            'fitness': 0.22,
            'art': 0.16,
            'music': 0.24,
            'other': 0.15
        }
        return coefficients.get(category, 0.15)

    @staticmethod
    def validate_offer_requirements(offer_data: Dict[str, Any]) -> List[str]:
        """Валидация требований к размещению"""
        warnings = []

        # Проверка требований к размещению
        posting_requirements = offer_data.get('posting_requirements', {})

        # Слишком строгие требования
        if posting_requirements.get('exact_time_required') and posting_requirements.get('no_edits_allowed'):
            warnings.append("Слишком строгие требования могут снизить количество откликов")

        # Проверка целевой аудитории
        target_audience = offer_data.get('target_audience', {})
        min_subscribers = target_audience.get('min_subscribers', 0)
        max_price = target_audience.get('max_price', 0)

        if min_subscribers > 100000 and max_price < 5000:
            warnings.append("Цена может быть низкой для каналов с таким количеством подписчиков")

        # Проверка медиа
        media_urls = offer_data.get('media_urls', [])
        content_type = offer_data.get('content_type', 'text')

        if content_type in ['image', 'video'] and not media_urls:
            warnings.append("Не приложены медиафайлы для визуального контента")

        # Проверка текста
        ad_text = offer_data.get('ad_text', '')
        if len(ad_text) > 1000:
            warnings.append("Слишком длинный рекламный текст может снизить эффективность")
        elif len(ad_text) < 50:
            warnings.append("Слишком короткий рекламный текст может быть недостаточно информативным")

        return warnings

    @staticmethod
    def suggest_categories(title: str, description: str) -> List[Dict[str, Any]]:
        """Предложение категорий на основе текста"""
        try:
            from .channels import ChannelCategory

            text = f"{title} {description}".lower()

            category_keywords = {
                ChannelCategory.TECHNOLOGY.value: ['технологии', 'it', 'программирование', 'софт', 'приложение', 'сайт',
                                                   'код'],
                ChannelCategory.BUSINESS.value: ['бизнес', 'стартап', 'предпринимательство', 'продажи', 'маркетинг',
                                                 'реклама'],
                ChannelCategory.EDUCATION.value: ['курсы', 'обучение', 'образование', 'школа', 'университет', 'знания'],
                ChannelCategory.ENTERTAINMENT.value: ['развлечения', 'фильмы', 'игры', 'музыка', 'шоу', 'юмор'],
                ChannelCategory.LIFESTYLE.value: ['стиль жизни', 'мода', 'красота', 'здоровье', 'фитнес',
                                                  'путешествия'],
                ChannelCategory.CRYPTO.value: ['криптовалюта', 'bitcoin', 'блокчейн', 'майнинг', 'defi', 'nft'],
                ChannelCategory.NEWS.value: ['новости', 'события', 'политика', 'мир', 'происшествия'],
                ChannelCategory.SPORTS.value: ['спорт', 'футбол', 'хоккей', 'теннис', 'фитнес', 'тренировки']
            }

            category_scores = []
            for category, keywords in category_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text)
                if score > 0:
                    category_scores.append({
                        'category': category,
                        'score': score,
                        'confidence': min(score * 20, 100)  # Процент уверенности
                    })

            # Сортируем по убыванию скора
            category_scores.sort(key=lambda x: x['score'], reverse=True)

            return category_scores[:3]  # Топ 3 предложения

        except Exception as e:
            return [{'category': 'other', 'score': 0, 'confidence': 0}]

    @staticmethod
    def format_offer_for_channel_owner(offer: Offer, channel_match: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирование оффера для показа владельцу канала"""
        try:
            # Базовая информация об оффере
            formatted_offer = {
                'id': offer.id,
                'title': offer.title,
                'description': offer.description[:200] + "..." if len(offer.description) > 200 else offer.description,
                'category': offer.category,
                'budget': float(offer.budget),
                'max_price_per_post': float(offer.max_price_per_post),
                'content_type': offer.content_type,
                'offer_type': offer.offer_type,
                'expires_at': offer.expires_at
            }

            # Информация о совпадении
            if channel_match:
                formatted_offer['match_info'] = {
                    'score': channel_match.get('match_score', 0),
                    'reasons': channel_match.get('match_reasons', []),
                    'estimated_reach': channel_match.get('estimated_reach', {})
                }

            # Требования к размещению
            if offer.posting_requirements:
                requirements = []

                if offer.posting_requirements.get('exact_time_required'):
                    requirements.append("Точное время размещения")

                if offer.posting_requirements.get('no_edits_allowed'):
                    requirements.append("Без редактирования")

                if offer.posting_requirements.get('pin_required'):
                    requirements.append("Закрепление поста")

                formatted_offer['requirements'] = requirements

            # Информация о рекламодателе (ограниченная)
            from .user import User
            advertiser = User.get_by_id(offer.advertiser_id)
            if advertiser:
                formatted_offer['advertiser'] = {
                    'username': advertiser.username,
                    'rating': getattr(advertiser, 'rating', 'Новый'),
                    'completed_campaigns': len(Offer.get_advertiser_offers(offer.advertiser_id, 'completed'))
                }

            return formatted_offer

        except Exception as e:
            # В случае ошибки возвращаем базовую информацию
            return {
                'id': offer.id,
                'title': offer.title,
                'description': offer.description,
                'budget': float(offer.budget),
                'error': str(e)
            }


# Функции для автоматизации и обслуживания
class OfferMaintenanceService:
    """Сервис обслуживания офферов"""

    @staticmethod
    def expire_old_offers() -> Dict[str, int]:
        """Обработка истекших офферов"""
        try:
            current_time = datetime.now().isoformat()

            # Находим истекшие офферы
            expired_offers = db_manager.execute_query(
                """
                SELECT id
                FROM offers
                WHERE status = 'active'
                  AND expires_at <= ?
                """,
                (current_time,),
                fetch_all=True
            )

            expired_count = 0
            for (offer_id,) in expired_offers:
                offer = Offer.get_by_id(offer_id)
                if offer:
                    offer.status = OfferStatus.EXPIRED.value
                    offer.save()

                    # Возвращаем неиспользованный бюджет
                    offer._refund_unused_budget()
                    expired_count += 1

            return {
                'expired_offers': expired_count,
                'processed_at': current_time
            }

        except Exception as e:
            return {'error': str(e), 'expired_offers': 0}

    @staticmethod
    def auto_release_escrow() -> Dict[str, int]:
        """Автоматическое освобождение эскроу"""
        try:
            from .payment import EscrowTransaction

            # Находим эскроу для автоматического освобождения
            current_time = datetime.now()

            active_escrows = EscrowTransaction.get_active_escrows()
            released_count = 0

            for escrow in active_escrows:
                if escrow.auto_release_at:
                    try:
                        release_time = datetime.fromisoformat(escrow.auto_release_at.replace('Z', '+00:00'))
                        if current_time >= release_time:
                            escrow.release()
                            released_count += 1
                    except (ValueError, AttributeError):
                        continue

            return {
                'released_escrows': released_count,
                'processed_at': current_time.isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'released_escrows': 0}

    @staticmethod
    def cleanup_draft_offers(days_old: int = 7) -> Dict[str, int]:
        """Очистка старых черновиков офферов"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            # Находим старые черновики
            old_drafts = db_manager.execute_query(
                """
                SELECT id
                FROM offers
                WHERE status = 'draft'
                  AND created_at <= ?
                """,
                (cutoff_date,),
                fetch_all=True
            )

            # Удаляем старые черновики
            deleted_count = 0
            for (offer_id,) in old_drafts:
                try:
                    db_manager.execute_query(
                        "DELETE FROM offers WHERE id = ?",
                        (offer_id,)
                    )
                    deleted_count += 1
                except Exception:
                    continue

            return {
                'deleted_drafts': deleted_count,
                'cutoff_days': days_old,
                'processed_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'deleted_drafts': 0}


# Экспорт основных классов и функций
__all__ = [
    'Offer', 'OfferResponse', 'OfferAnalytics', 'OfferRecommendationEngine',
    'OfferUtils', 'OfferMaintenanceService', 'OfferStatus', 'OfferType', 'ContentType'
]
