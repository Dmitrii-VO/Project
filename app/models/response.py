# app/models/response.py
"""
Модель откликов на офферы для Telegram Mini App
Связывает каналы и офферы, обеспечивает процесс переговоров
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from .database import db_manager
from ..utils.exceptions import ResponseError, ValidationError, OfferError
from ..config.settings import AUTO_ACCEPT_TIMEOUT_HOURS, MAX_COUNTER_OFFERS


class ResponseStatus(Enum):
    """Статусы откликов"""
    PENDING = 'pending'
    INTERESTED = 'interested'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    COUNTER_OFFERED = 'counter_offered'
    POSTED = 'posted'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class ResponseType(Enum):
    """Типы откликов"""
    DIRECT = 'direct'  # Прямой отклик по цене канала
    NEGOTIATION = 'negotiation'  # Отклик с переговорами
    COUNTER_OFFER = 'counter_offer'  # Встречное предложение
    AUTO_MATCHED = 'auto_matched'  # Автоматическое сопоставление


class Response:
    """Модель отклика на оффер"""

    def __init__(self, response_data: Dict[str, Any] = None):
        if response_data:
            self.id = response_data.get('id')
            self.offer_id = response_data.get('offer_id')
            self.channel_id = response_data.get('channel_id')
            self.channel_owner_id = response_data.get('channel_owner_id')
            self.status = response_data.get('status', ResponseStatus.PENDING.value)
            self.response_type = response_data.get('response_type', ResponseType.DIRECT.value)
            self.proposed_price = Decimal(str(response_data.get('proposed_price', 0)))
            self.final_price = Decimal(str(response_data.get('final_price', 0)))
            self.message = response_data.get('message', '')
            self.proposed_terms = response_data.get('proposed_terms', '')
            self.proposed_posting_time = response_data.get('proposed_posting_time')
            self.negotiation_data = self._parse_negotiation_data(response_data.get('negotiation_data'))
            self.rejection_reason = response_data.get('rejection_reason')
            self.posted_at = response_data.get('posted_at')
            self.post_url = response_data.get('post_url')
            self.post_content = response_data.get('post_content')
            self.performance_metrics = self._parse_performance_metrics(response_data.get('performance_metrics'))
            self.expires_at = response_data.get('expires_at')
            self.created_at = response_data.get('created_at')
            self.updated_at = response_data.get('updated_at')
            self.completed_at = response_data.get('completed_at')
        else:
            self.id = None
            self.offer_id = None
            self.channel_id = None
            self.channel_owner_id = None
            self.status = ResponseStatus.PENDING.value
            self.response_type = ResponseType.DIRECT.value
            self.proposed_price = Decimal('0')
            self.final_price = Decimal('0')
            self.message = ''
            self.proposed_terms = ''
            self.proposed_posting_time = None
            self.negotiation_data = {}
            self.rejection_reason = None
            self.posted_at = None
            self.post_url = None
            self.post_content = None
            self.performance_metrics = {}
            self.expires_at = None
            self.created_at = None
            self.updated_at = None
            self.completed_at = None

    def _parse_negotiation_data(self, negotiation_data: Any) -> Dict[str, Any]:
        """Парсинг данных переговоров из JSON"""
        if isinstance(negotiation_data, str):
            try:
                return json.loads(negotiation_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(negotiation_data, dict):
            return negotiation_data
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
            negotiation_data_json = json.dumps(self.negotiation_data) if self.negotiation_data else None
            performance_metrics_json = json.dumps(self.performance_metrics) if self.performance_metrics else None

            if self.id:
                # Обновление существующего отклика
                query = """
                        UPDATE offer_responses
                        SET status                = ?, \
                            response_type         = ?, \
                            proposed_price        = ?, \
                            final_price           = ?,
                            message               = ?, \
                            proposed_terms        = ?, \
                            proposed_posting_time = ?,
                            negotiation_data      = ?, \
                            rejection_reason      = ?, \
                            posted_at             = ?,
                            post_url              = ?, \
                            post_content          = ?, \
                            performance_metrics   = ?,
                            expires_at            = ?, \
                            updated_at            = CURRENT_TIMESTAMP, \
                            completed_at          = ?
                        WHERE id = ? \
                        """
                params = (
                    self.status, self.response_type, float(self.proposed_price), float(self.final_price),
                    self.message, self.proposed_terms, self.proposed_posting_time,
                    negotiation_data_json, self.rejection_reason, self.posted_at,
                    self.post_url, self.post_content, performance_metrics_json,
                    self.expires_at, self.completed_at, self.id
                )
            else:
                # Создание нового отклика
                query = """
                        INSERT INTO offer_responses (offer_id, channel_id, channel_owner_id, status, response_type, \
                                                     proposed_price, final_price, message, proposed_terms, \
                                                     proposed_posting_time, negotiation_data, expires_at, created_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) \
                        """
                params = (
                    self.offer_id, self.channel_id, self.channel_owner_id,
                    self.status, self.response_type, float(self.proposed_price),
                    float(self.final_price), self.message, self.proposed_terms,
                    self.proposed_posting_time, negotiation_data_json, self.expires_at
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового отклика
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise ResponseError(f"Ошибка сохранения отклика: {str(e)}")

    @classmethod
    def get_by_id(cls, response_id: int) -> Optional['Response']:
        """Получение отклика по ID"""
        query = "SELECT * FROM offer_responses WHERE id = ?"
        result = db_manager.execute_query(query, (response_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_offer_id(cls, offer_id: int, status: str = None) -> List['Response']:
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
    def get_by_channel_id(cls, channel_id: int, status: str = None, limit: int = 50) -> List['Response']:
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
    def get_user_responses(cls, user_id: int, user_type: str, status: str = None, limit: int = 50) -> List['Response']:
        """Получение откликов пользователя (владельца каналов или рекламодателя)"""
        if user_type == 'channel_owner':
            # Отклики на каналы пользователя
            query = """
                    SELECT or1.* \
                    FROM offer_responses or1 \
                             JOIN channels c ON or1.channel_id = c.id
                    WHERE c.owner_id = ? \
                    """
            params = [user_id]
        elif user_type == 'advertiser':
            # Отклики на офферы пользователя
            query = """
                    SELECT or1.* \
                    FROM offer_responses or1 \
                             JOIN offers o ON or1.offer_id = o.id
                    WHERE o.advertiser_id = ? \
                    """
            params = [user_id]
        else:
            return []

        if status:
            query += " AND or1.status = ?"
            params.append(status)

        query += " ORDER BY or1.created_at DESC LIMIT ?"
        params.append(limit)

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def create_response(cls, offer_id: int, channel_id: int, channel_owner_id: int,
                        response_data: Dict[str, Any]) -> 'Response':
        """Создание отклика на оффер"""
        # Проверяем, что оффер активен
        from .offer import Offer
        offer = Offer.get_by_id(offer_id)
        if not offer or offer.status != 'active':
            raise OfferError("Оффер не активен или не найден")

        # Проверяем, что канал не откликался ранее
        existing_response = cls._get_existing_response(offer_id, channel_id)
        if existing_response:
            raise ResponseError("Канал уже откликнулся на этот оффер")

        # Проверяем канал
        from .channels import Channel
        channel = Channel.get_by_id(channel_id)
        if not channel or not channel.is_verified:
            raise ResponseError("Канал не найден или не верифицирован")

        # Валидируем данные отклика
        cls._validate_response_data(response_data)

        # Создаем отклик
        response = cls()
        response.offer_id = offer_id
        response.channel_id = channel_id
        response.channel_owner_id = channel_owner_id
        response.status = response_data.get('status', ResponseStatus.INTERESTED.value)
        response.response_type = response_data.get('response_type', ResponseType.DIRECT.value)
        response.proposed_price = Decimal(str(response_data.get('proposed_price', channel.price_per_post)))
        response.message = response_data.get('message', '')
        response.proposed_terms = response_data.get('proposed_terms', '')
        response.proposed_posting_time = response_data.get('proposed_posting_time')

        # Устанавливаем срок действия (по умолчанию 48 часов)
        response.expires_at = (datetime.now() + timedelta(hours=48)).isoformat()

        # Проверяем цену относительно лимитов оффера
        if offer.max_price_per_post > 0 and response.proposed_price > offer.max_price_per_post:
            # Если цена превышает лимит, создаем встречное предложение
            response.status = ResponseStatus.COUNTER_OFFERED.value
            response.response_type = ResponseType.COUNTER_OFFER.value
            response.negotiation_data = {
                'original_price': float(channel.price_per_post),
                'offer_max_price': float(offer.max_price_per_post),
                'counter_reason': 'price_exceeds_limit'
            }

        response.save()

        # Уведомляем рекламодателя
        response._notify_advertiser()

        # Логируем создание отклика
        response._log_response_event('created')

        return response

    @classmethod
    def _get_existing_response(cls, offer_id: int, channel_id: int) -> Optional['Response']:
        """Проверка существующего отклика"""
        query = "SELECT * FROM offer_responses WHERE offer_id = ? AND channel_id = ?"
        result = db_manager.execute_query(query, (offer_id, channel_id), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @staticmethod
    def _validate_response_data(data: Dict[str, Any]):
        """Валидация данных отклика"""
        errors = []

        # Проверка цены
        proposed_price = data.get('proposed_price')
        if proposed_price is not None:
            try:
                price = float(proposed_price)
                if price <= 0:
                    errors.append("Цена должна быть положительной")
                elif price > 1000000:
                    errors.append("Цена слишком высокая (максимум 1,000,000 RUB)")
            except (ValueError, TypeError):
                errors.append("Некорректный формат цены")

        # Проверка сообщения
        message = data.get('message', '')
        if len(message) > 1000:
            errors.append("Сообщение не должно превышать 1000 символов")

        # Проверка условий
        terms = data.get('proposed_terms', '')
        if len(terms) > 500:
            errors.append("Условия не должны превышать 500 символов")

        # Проверка времени размещения
        posting_time = data.get('proposed_posting_time')
        if posting_time:
            try:
                posting_datetime = datetime.fromisoformat(posting_time.replace('Z', '+00:00'))
                if posting_datetime < datetime.now():
                    errors.append("Время размещения не может быть в прошлом")
            except (ValueError, AttributeError):
                errors.append("Некорректный формат времени размещения")

        if errors:
            raise ValidationError('; '.join(errors))

    def accept_by_advertiser(self, advertiser_id: int) -> bool:
        """Принятие отклика рекламодателем"""
        if self.status not in [ResponseStatus.PENDING.value, ResponseStatus.INTERESTED.value,
                               ResponseStatus.COUNTER_OFFERED.value]:
            raise ResponseError("Можно принять только ожидающие отклики")

        # Проверяем права
        from .offer import Offer
        offer = Offer.get_by_id(self.offer_id)
        if not offer or offer.advertiser_id != advertiser_id:
            raise ResponseError("Нет прав для принятия этого отклика")

        # Проверяем бюджет
        if offer.budget < self.proposed_price:
            raise ResponseError("Недостаточно бюджета для принятия отклика")

        old_status = self.status
        self.status = ResponseStatus.ACCEPTED.value
        self.final_price = self.proposed_price

        success = self.save()

        if success:
            # Создаем эскроу-транзакцию
            self._create_escrow_transaction()

            # Уведомляем владельца канала
            self._notify_channel_owner('accepted')

            # Обновляем бюджет оффера
            offer.budget -= self.final_price
            offer.save()

            # Логируем событие
            self._log_response_event('accepted_by_advertiser', {'old_status': old_status})

        return success

    def reject_by_advertiser(self, advertiser_id: int, reason: str = "") -> bool:
        """Отклонение отклика рекламодателем"""
        if self.status not in [ResponseStatus.PENDING.value, ResponseStatus.INTERESTED.value,
                               ResponseStatus.COUNTER_OFFERED.value]:
            raise ResponseError("Можно отклонить только ожидающие отклики")

        # Проверяем права
        from .offer import Offer
        offer = Offer.get_by_id(self.offer_id)
        if not offer or offer.advertiser_id != advertiser_id:
            raise ResponseError("Нет прав для отклонения этого отклика")

        old_status = self.status
        self.status = ResponseStatus.REJECTED.value
        self.rejection_reason = reason

        success = self.save()

        if success:
            # Уведомляем владельца канала
            self._notify_channel_owner('rejected')

            # Логируем событие
            self._log_response_event('rejected_by_advertiser', {
                'old_status': old_status,
                'reason': reason
            })

        return success

    def create_counter_offer(self, new_price: float, message: str = "", terms: str = "") -> bool:
        """Создание встречного предложения"""
        if self.status != ResponseStatus.PENDING.value:
            raise ResponseError("Встречное предложение можно создать только для ожидающих откликов")

        # Проверяем лимит встречных предложений
        negotiation_history = self.negotiation_data.get('history', [])
        if len(negotiation_history) >= MAX_COUNTER_OFFERS:
            raise ResponseError(f"Превышен лимит встречных предложений ({MAX_COUNTER_OFFERS})")

        # Добавляем в историю переговоров
        counter_offer = {
            'price': new_price,
            'message': message,
            'terms': terms,
            'created_at': datetime.now().isoformat(),
            'type': 'counter_offer'
        }

        if 'history' not in self.negotiation_data:
            self.negotiation_data['history'] = []

        self.negotiation_data['history'].append(counter_offer)
        self.negotiation_data['counter_offers_count'] = len(self.negotiation_data['history'])

        # Обновляем статус и цену
        self.status = ResponseStatus.COUNTER_OFFERED.value
        self.response_type = ResponseType.COUNTER_OFFER.value
        self.proposed_price = Decimal(str(new_price))
        self.message = message
        self.proposed_terms = terms

        success = self.save()

        if success:
            # Уведомляем рекламодателя
            self._notify_advertiser_counter_offer()

            # Логируем событие
            self._log_response_event('counter_offer_created', {
                'new_price': new_price,
                'counter_offers_count': self.negotiation_data['counter_offers_count']
            })

        return success

    def mark_as_posted(self, post_data: Dict[str, Any]) -> bool:
        """Отметка о размещении поста"""
        if self.status != ResponseStatus.ACCEPTED.value:
            raise ResponseError("Можно отметить размещение только для принятых откликов")

        self.status = ResponseStatus.POSTED.value
        self.posted_at = datetime.now().isoformat()
        self.post_url = post_data.get('post_url', '')
        self.post_content = post_data.get('post_content', '')

        # Добавляем начальные метрики
        initial_metrics = post_data.get('initial_metrics', {})
        if initial_metrics:
            self.performance_metrics.update(initial_metrics)

        success = self.save()

        if success:
            # Освобождаем эскроу
            self._release_escrow()

            # Уведомляем рекламодателя
            self._notify_advertiser_posting()

            # Логируем событие
            self._log_response_event('posted', {
                'post_url': self.post_url,
                'posted_at': self.posted_at
            })

        return success

    def update_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Обновление метрик производительности"""
        if self.status not in [ResponseStatus.POSTED.value, ResponseStatus.COMPLETED.value]:
            raise ResponseError("Метрики можно обновлять только для размещенных постов")

        # Обновляем метрики с историей
        timestamp = datetime.now().isoformat()

        # Сохраняем историю изменений метрик
        if 'history' not in self.performance_metrics:
            self.performance_metrics['history'] = []

        self.performance_metrics['history'].append({
            'timestamp': timestamp,
            'metrics': metrics
        })

        # Обновляем текущие метрики
        self.performance_metrics.update({
            **metrics,
            'last_updated': timestamp
        })

        # Оставляем только последние 50 записей истории
        self.performance_metrics['history'] = self.performance_metrics['history'][-50:]

        return self.save()

    def complete(self, completion_data: Dict[str, Any] = None) -> bool:
        """Завершение отклика"""
        if self.status != ResponseStatus.POSTED.value:
            raise ResponseError("Можно завершить только размещенные отклики")

        self.status = ResponseStatus.COMPLETED.value
        self.completed_at = datetime.now().isoformat()

        if completion_data:
            # Добавляем финальные данные
            self.performance_metrics.update({
                'completion_data': completion_data,
                'completed_at': self.completed_at
            })

        success = self.save()

        if success:
            # Логируем завершение
            self._log_response_event('completed', completion_data or {})

            # Уведомляем участников
            self._notify_completion()

        return success

    def cancel(self, cancelled_by: str, reason: str = "") -> bool:
        """Отмена отклика"""
        if self.status in [ResponseStatus.COMPLETED.value, ResponseStatus.CANCELLED.value]:
            raise ResponseError("Нельзя отменить завершенный или уже отмененный отклик")

        old_status = self.status
        self.status = ResponseStatus.CANCELLED.value
        self.rejection_reason = f"Отменен ({cancelled_by}): {reason}"

        success = self.save()

        if success:
            # Возвращаем средства из эскроу если необходимо
            if old_status == ResponseStatus.ACCEPTED.value:
                self._refund_escrow()

            # Логируем отмену
            self._log_response_event('cancelled', {
                'cancelled_by': cancelled_by,
                'reason': reason,
                'old_status': old_status
            })

            # Уведомляем участников
            self._notify_cancellation(cancelled_by, reason)

        return success

    def is_expired(self) -> bool:
        """Проверка истечения срока отклика"""
        if not self.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now() > expires_at
        except (ValueError, AttributeError):
            return False

    def extend_expiry(self, hours: int) -> bool:
        """Продление срока действия отклика"""
        if self.status not in [ResponseStatus.PENDING.value, ResponseStatus.INTERESTED.value,
                               ResponseStatus.COUNTER_OFFERED.value]:
            raise ResponseError("Можно продлить только активные отклики")

        if self.expires_at:
            try:
                current_expiry = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
                new_expiry = current_expiry + timedelta(hours=hours)
            except (ValueError, AttributeError):
                new_expiry = datetime.now() + timedelta(hours=hours)
        else:
            new_expiry = datetime.now() + timedelta(hours=hours)

        self.expires_at = new_expiry.isoformat()
        return self.save()

    def get_analytics(self) -> Dict[str, Any]:
        """Получение аналитики по отклику"""
        try:
            analytics = {
                'response_info': {
                    'id': self.id,
                    'status': self.status,
                    'response_type': self.response_type,
                    'proposed_price': float(self.proposed_price),
                    'final_price': float(self.final_price),
                    'created_at': self.created_at,
                    'posted_at': self.posted_at,
                    'completed_at': self.completed_at
                },
                'negotiation': {
                    'counter_offers_count': self.negotiation_data.get('counter_offers_count', 0),
                    'has_negotiations': bool(self.negotiation_data.get('history')),
                    'negotiation_duration': self._calculate_negotiation_duration()
                },
                'performance': {
                    'has_metrics': bool(self.performance_metrics),
                    'latest_metrics': self._get_latest_metrics(),
                    'metrics_history_count': len(self.performance_metrics.get('history', []))
                },
                'timeline': self._build_timeline()
            }

            # Добавляем ROI если есть метрики
            if self.performance_metrics and self.final_price > 0:
                analytics['roi'] = self._calculate_roi()

            return analytics

        except Exception as e:
            return {'error': str(e)}

    def _calculate_negotiation_duration(self) -> Optional[float]:
        """Расчет длительности переговоров в часах"""
        if not self.negotiation_data.get('history'):
            return None

        try:
            first_event = self.negotiation_data['history'][0]
            last_event = self.negotiation_data['history'][-1]

            start_time = datetime.fromisoformat(first_event['created_at'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(last_event['created_at'].replace('Z', '+00:00'))

            duration = (end_time - start_time).total_seconds() / 3600
            return round(duration, 2)

        except (ValueError, KeyError, AttributeError):
            return None

    def _get_latest_metrics(self) -> Dict[str, Any]:
        """Получение последних метрик"""
        if not self.performance_metrics:
            return {}

        # Возвращаем метрики без истории
        latest = self.performance_metrics.copy()
        latest.pop('history', None)
        return latest

    def _calculate_roi(self) -> Dict[str, Any]:
        """Расчет ROI на основе метрик"""
        try:
            metrics = self.performance_metrics
            cost = float(self.final_price)

            # Базовые метрики
            views = metrics.get('views', 0)
            clicks = metrics.get('clicks', 0)
            conversions = metrics.get('conversions', 0)

            roi_data = {
                'cost_per_view': round(cost / views, 4) if views > 0 else 0,
                'cost_per_click': round(cost / clicks, 2) if clicks > 0 else 0,
                'cost_per_conversion': round(cost / conversions, 2) if conversions > 0 else 0,
                'ctr': round(clicks / views * 100, 2) if views > 0 else 0,
                'conversion_rate': round(conversions / clicks * 100, 2) if clicks > 0 else 0
            }

            # Если есть данные о доходе
            revenue = metrics.get('revenue', 0)
            if revenue > 0:
                roi_data['roi'] = round((revenue - cost) / cost * 100, 2)
                roi_data['roas'] = round(revenue / cost, 2)

            return roi_data

        except (ValueError, TypeError, ZeroDivisionError):
            return {}

    def _build_timeline(self) -> List[Dict[str, Any]]:
        """Построение временной линии событий"""
        timeline = []

        # Событие создания
        if self.created_at:
            timeline.append({
                'event': 'created',
                'timestamp': self.created_at,
                'description': 'Отклик создан',
                'data': {
                    'proposed_price': float(self.proposed_price),
                    'message': self.message[:100] + '...' if len(self.message) > 100 else self.message
                }
            })

        # События переговоров
        if self.negotiation_data.get('history'):
            for event in self.negotiation_data['history']:
                timeline.append({
                    'event': 'negotiation',
                    'timestamp': event['created_at'],
                    'description': f"Встречное предложение: {event['price']} ₽",
                    'data': event
                })

        # Событие принятия
        if self.status in [ResponseStatus.ACCEPTED.value, ResponseStatus.POSTED.value, ResponseStatus.COMPLETED.value]:
            timeline.append({
                'event': 'accepted',
                'timestamp': self.updated_at or self.created_at,
                'description': 'Отклик принят',
                'data': {'final_price': float(self.final_price)}
            })

        # Событие размещения
        if self.posted_at:
            timeline.append({
                'event': 'posted',
                'timestamp': self.posted_at,
                'description': 'Пост размещен',
                'data': {
                    'post_url': self.post_url,
                    'post_content': self.post_content[:100] + '...' if self.post_content and len(
                        self.post_content) > 100 else self.post_content
                }
            })

        # Событие завершения
        if self.completed_at:
            timeline.append({
                'event': 'completed',
                'timestamp': self.completed_at,
                'description': 'Отклик завершен',
                'data': {'status': 'completed'}
            })

        # Сортируем по времени
        timeline.sort(key=lambda x: x['timestamp'])
        return timeline

    def _create_escrow_transaction(self):
        """Создание эскроу-транзакции при принятии отклика"""
        try:
            from .payment import Payment

            Payment.create_escrow_hold(
                advertiser_id=self._get_advertiser_id(),
                channel_owner_id=self.channel_owner_id,
                amount=self.final_price,
                offer_response_id=self.id,
                auto_release_hours=72
            )

        except Exception as e:
            print(f"Ошибка создания эскроу для отклика {self.id}: {e}")

    def _release_escrow(self):
        """Освобождение эскроу при размещении поста"""
        try:
            from .payment import EscrowTransaction

            escrow = EscrowTransaction.get_by_offer_response(self.id)
            if escrow:
                escrow.release(released_by=self.channel_owner_id)

        except Exception as e:
            print(f"Ошибка освобождения эскроу для отклика {self.id}: {e}")

    def _refund_escrow(self):
        """Возврат эскроу при отмене"""
        try:
            from .payment import EscrowTransaction

            escrow = EscrowTransaction.get_by_offer_response(self.id)
            if escrow and escrow.status == 'active':
                # Отменяем эскроу и возвращаем средства рекламодателю
                escrow.status = 'cancelled'
                escrow.cancelled_at = datetime.now().isoformat()
                escrow.save()

                # Возвращаем средства на баланс рекламодателя
                from .user import User
                advertiser = User.get_by_id(self._get_advertiser_id())
                if advertiser:
                    advertiser.update_balance(float(self.final_price), f"Возврат за отмененный отклик #{self.id}")

        except Exception as e:
            print(f"Ошибка возврата эскроу для отклика {self.id}: {e}")

    def _get_advertiser_id(self) -> int:
        """Получение ID рекламодателя"""
        from .offer import Offer
        offer = Offer.get_by_id(self.offer_id)
        return offer.advertiser_id if offer else None

    def _notify_advertiser(self):
        """Уведомление рекламодателя о новом отклике"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            advertiser_id = self._get_advertiser_id()
            if advertiser_id:
                advertiser = User.get_by_id(advertiser_id)
                if advertiser:
                    # Получаем информацию о канале
                    from .channels import Channel
                    channel = Channel.get_by_id(self.channel_id)
                    channel_name = channel.channel_name if channel else f"Канал #{self.channel_id}"

                    message = f"📩 Новый отклик на ваш оффер!\n"
                    message += f"📺 Канал: {channel_name}\n"
                    message += f"💰 Предложенная цена: {self.proposed_price} ₽\n"

                    if self.message:
                        message += f"💬 Сообщение: {self.message[:100]}..."

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'new_response',
                            'response_id': self.id,
                            'offer_id': self.offer_id,
                            'channel_id': self.channel_id
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
                    message = f"✅ Ваш отклик принят!\n💰 Сумма: {self.final_price} ₽"
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
                        'response_id': self.id,
                        'action': action
                    }
                )

        except Exception as e:
            print(f"Ошибка уведомления владельца канала: {e}")

    def _notify_advertiser_counter_offer(self):
        """Уведомление рекламодателя о встречном предложении"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            advertiser_id = self._get_advertiser_id()
            if advertiser_id:
                advertiser = User.get_by_id(advertiser_id)
                if advertiser:
                    message = f"💱 Встречное предложение\n"
                    message += f"💰 Новая цена: {self.proposed_price} ₽\n"

                    if self.message:
                        message += f"💬 Сообщение: {self.message}"

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'counter_offer',
                            'response_id': self.id,
                            'new_price': float(self.proposed_price)
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления о встречном предложении: {e}")

    def _notify_advertiser_posting(self):
        """Уведомление рекламодателя о размещении поста"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            advertiser_id = self._get_advertiser_id()
            if advertiser_id:
                advertiser = User.get_by_id(advertiser_id)
                if advertiser:
                    message = f"📢 Пост размещен!\n"
                    message += f"💰 Сумма: {self.final_price} ₽\n"

                    if self.post_url:
                        message += f"🔗 Ссылка: {self.post_url}"

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'post_published',
                            'response_id': self.id,
                            'post_url': self.post_url
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления о размещении: {e}")

    def _notify_completion(self):
        """Уведомление о завершении отклика"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            # Уведомляем владельца канала
            owner = User.get_by_id(self.channel_owner_id)
            if owner:
                message = f"🎉 Отклик завершен!\n💰 Получено: {self.final_price} ₽"

                NotificationService.send_telegram_notification(
                    owner.telegram_id,
                    message,
                    {
                        'type': 'response_completed',
                        'response_id': self.id
                    }
                )

            # Уведомляем рекламодателя
            advertiser_id = self._get_advertiser_id()
            if advertiser_id:
                advertiser = User.get_by_id(advertiser_id)
                if advertiser:
                    message = f"✅ Размещение завершено!\n📊 Посмотрите статистику в аналитике"

                    NotificationService.send_telegram_notification(
                        advertiser.telegram_id,
                        message,
                        {
                            'type': 'campaign_completed',
                            'response_id': self.id
                        }
                    )

        except Exception as e:
            print(f"Ошибка уведомления о завершении: {e}")

    def _notify_cancellation(self, cancelled_by: str, reason: str):
        """Уведомление об отмене отклика"""
        try:
            from .user import User
            from ..services.notification_service import NotificationService

            message = f"❌ Отклик отменен\n📝 Причина: {reason}"

            # Уведомляем обе стороны
            participants = [
                (self.channel_owner_id, 'response_cancelled'),
                (self._get_advertiser_id(), 'response_cancelled')
            ]

            for user_id, notification_type in participants:
                if user_id:
                    user = User.get_by_id(user_id)
                    if user:
                        NotificationService.send_telegram_notification(
                            user.telegram_id,
                            message,
                            {
                                'type': notification_type,
                                'response_id': self.id,
                                'cancelled_by': cancelled_by
                            }
                        )

        except Exception as e:
            print(f"Ошибка уведомления об отмене: {e}")

    def _log_response_event(self, event_type: str, event_data: Dict[str, Any] = None):
        """Логирование событий отклика"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'response_id': self.id,
                'data': event_data or {}
            }

            # Добавляем в лог переговоров
            if 'events_log' not in self.negotiation_data:
                self.negotiation_data['events_log'] = []

            self.negotiation_data['events_log'].append(log_entry)

            # Оставляем только последние 100 событий
            self.negotiation_data['events_log'] = self.negotiation_data['events_log'][-100:]

        except Exception as e:
            print(f"Ошибка логирования события отклика: {e}")

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = {
            'id': self.id,
            'offer_id': self.offer_id,
            'channel_id': self.channel_id,
            'channel_owner_id': self.channel_owner_id,
            'status': self.status,
            'response_type': self.response_type,
            'proposed_price': float(self.proposed_price),
            'final_price': float(self.final_price),
            'message': self.message,
            'proposed_terms': self.proposed_terms,
            'proposed_posting_time': self.proposed_posting_time,
            'posted_at': self.posted_at,
            'post_url': self.post_url,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at
        }

        if include_sensitive:
            result.update({
                'negotiation_data': self.negotiation_data,
                'performance_metrics': self.performance_metrics,
                'rejection_reason': self.rejection_reason,
                'post_content': self.post_content
            })

        return result


class ResponseAnalytics:
    """Класс для аналитики откликов"""

    @staticmethod
    def get_platform_response_stats() -> Dict[str, Any]:
        """Получение общей статистики откликов на платформе"""
        try:
            # Общее количество откликов
            total_responses = db_manager.execute_query(
                "SELECT COUNT(*) FROM offer_responses",
                fetch_one=True
            )[0]

            # Статистика по статусам
            status_stats = db_manager.execute_query(
                """
                SELECT status, COUNT(*) as count
                FROM offer_responses
                GROUP BY status
                """,
                fetch_all=True
            )

            # Средняя цена откликов
            avg_price_stats = db_manager.execute_query(
                """
                SELECT AVG(proposed_price) as avg_proposed,
                       AVG(final_price)    as avg_final,
                       MAX(final_price)    as max_price,
                       MIN(proposed_price) as min_price
                FROM offer_responses
                WHERE final_price > 0
                """,
                fetch_one=True
            )

            # Статистика по времени отклика
            response_time_stats = db_manager.execute_query(
                """
                SELECT AVG(
                               CASE
                                   WHEN or1.created_at > o.created_at
                                       THEN (julianday(or1.created_at) - julianday(o.created_at)) * 24
                                   ELSE NULL
                                   END
                       ) as avg_response_time_hours
                FROM offer_responses or1
                         JOIN offers o ON or1.offer_id = o.id
                WHERE or1.created_at > o.created_at
                """,
                fetch_one=True
            )

            # Конверсия по месяцам
            monthly_conversion = db_manager.execute_query(
                """
                SELECT strftime('%Y-%m', created_at) as month,
                    COUNT(*) as total_responses,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_responses
                FROM offer_responses
                WHERE created_at >= datetime('now', '-12 months')
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY month DESC
                """,
                fetch_all=True
            )

            return {
                'total_responses': total_responses,
                'status_distribution': [
                    {'status': row[0], 'count': row[1]}
                    for row in status_stats
                ],
                'pricing': {
                    'avg_proposed_price': round(float(avg_price_stats[0] or 0), 2),
                    'avg_final_price': round(float(avg_price_stats[1] or 0), 2),
                    'max_price': float(avg_price_stats[2] or 0),
                    'min_price': float(avg_price_stats[3] or 0)
                },
                'timing': {
                    'avg_response_time_hours': round(float(response_time_stats[0] or 0), 2)
                },
                'monthly_trends': [
                    {
                        'month': row[0],
                        'total_responses': row[1],
                        'accepted_responses': row[2],
                        'conversion_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                    }
                    for row in monthly_conversion
                ]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_user_response_performance(user_id: int, user_type: str, days: int = 30) -> Dict[str, Any]:
        """Получение статистики откликов пользователя"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            if user_type == 'channel_owner':
                # Статистика для владельца каналов
                response_stats = db_manager.execute_query(
                    """
                    SELECT COUNT(*)                                                 as total_responses,
                           SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                           SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END)   as posted,
                           AVG(or1.final_price)                                     as avg_earnings,
                           SUM(or1.final_price)                                     as total_earnings
                    FROM offer_responses or1
                             JOIN channels c ON or1.channel_id = c.id
                    WHERE c.owner_id = ?
                      AND or1.created_at >= ?
                    """,
                    (user_id, cutoff_date),
                    fetch_one=True
                )

            else:  # advertiser
                # Статистика для рекламодателя
                response_stats = db_manager.execute_query(
                    """
                    SELECT COUNT(*)                                                 as total_responses,
                           SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                           SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END)   as posted,
                           AVG(or1.final_price)                                     as avg_cost,
                           SUM(or1.final_price)                                     as total_cost
                    FROM offer_responses or1
                             JOIN offers o ON or1.offer_id = o.id
                    WHERE o.advertiser_id = ?
                      AND or1.created_at >= ?
                    """,
                    (user_id, cutoff_date),
                    fetch_one=True
                )

            total = response_stats[0]
            accepted = response_stats[1]
            posted = response_stats[2]
            avg_amount = float(response_stats[3] or 0)
            total_amount = float(response_stats[4] or 0)

            return {
                'period_days': days,
                'total_responses': total,
                'accepted_responses': accepted,
                'posted_responses': posted,
                'acceptance_rate': (accepted / total * 100) if total > 0 else 0,
                'completion_rate': (posted / accepted * 100) if accepted > 0 else 0,
                'avg_amount': round(avg_amount, 2),
                'total_amount': round(total_amount, 2),
                'user_type': user_type
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_negotiation_analytics(response_id: int) -> Dict[str, Any]:
        """Получение аналитики переговоров по отклику"""
        try:
            response = Response.get_by_id(response_id)
            if not response:
                return {'error': 'Response not found'}

            negotiation_data = response.negotiation_data

            analytics = {
                'response_id': response_id,
                'has_negotiations': bool(negotiation_data.get('history')),
                'counter_offers_count': negotiation_data.get('counter_offers_count', 0),
                'negotiation_duration': response._calculate_negotiation_duration(),
                'price_changes': [],
                'negotiation_success': response.status == ResponseStatus.ACCEPTED.value
            }

            # Анализ изменений цены
            if negotiation_data.get('history'):
                prices = [float(response.proposed_price)]

                for event in negotiation_data['history']:
                    if event.get('price'):
                        prices.append(float(event['price']))

                analytics['price_changes'] = [
                    {
                        'step': i + 1,
                        'price': price,
                        'change': round(price - prices[0], 2) if i > 0 else 0,
                        'change_percent': round((price - prices[0]) / prices[0] * 100, 2) if prices[
                                                                                                 0] > 0 and i > 0 else 0
                    }
                    for i, price in enumerate(prices)
                ]

                analytics['final_price_change'] = {
                    'absolute': round(prices[-1] - prices[0], 2),
                    'percent': round((prices[-1] - prices[0]) / prices[0] * 100, 2) if prices[0] > 0 else 0
                }

            return analytics

        except Exception as e:
            return {'error': str(e)}


class ResponseMaintenanceService:
    """Сервис обслуживания откликов"""

    @staticmethod
    def expire_old_responses() -> Dict[str, int]:
        """Обработка истекших откликов"""
        try:
            current_time = datetime.now().isoformat()

            # Находим истекшие отклики
            expired_responses = db_manager.execute_query(
                """
                SELECT id
                FROM offer_responses
                WHERE status IN ('pending', 'interested', 'counter_offered')
                  AND expires_at <= ?
                """,
                (current_time,),
                fetch_all=True
            )

            expired_count = 0
            for (response_id,) in expired_responses:
                response = Response.get_by_id(response_id)
                if response:
                    response.status = ResponseStatus.CANCELLED.value
                    response.rejection_reason = "Истек срок действия"
                    response.save()
                    expired_count += 1

            return {
                'expired_responses': expired_count,
                'processed_at': current_time
            }

        except Exception as e:
            return {'error': str(e), 'expired_responses': 0}

    @staticmethod
    def auto_complete_posted_responses(days_since_posting: int = 7) -> Dict[str, int]:
        """Автоматическое завершение размещенных откликов"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_since_posting)).isoformat()

            # Находим давно размещенные отклики
            old_posted = db_manager.execute_query(
                """
                SELECT id
                FROM offer_responses
                WHERE status = 'posted'
                  AND posted_at <= ?
                """,
                (cutoff_date,),
                fetch_all=True
            )

            completed_count = 0
            for (response_id,) in old_posted:
                response = Response.get_by_id(response_id)
                if response:
                    response.complete(
                        {'auto_completed': True, 'reason': f'Auto-completed after {days_since_posting} days'})
                    completed_count += 1

            return {
                'auto_completed_responses': completed_count,
                'cutoff_days': days_since_posting,
                'processed_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'auto_completed_responses': 0}

    @staticmethod
    def cleanup_old_negotiations(days_old: int = 90) -> Dict[str, int]:
        """Очистка старых данных переговоров"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            # Находим старые завершенные отклики
            old_responses = db_manager.execute_query(
                """
                SELECT id
                FROM offer_responses
                WHERE status IN ('completed', 'cancelled', 'rejected')
                  AND updated_at <= ?
                """,
                (cutoff_date,),
                fetch_all=True
            )

            cleaned_count = 0
            for (response_id,) in old_responses:
                response = Response.get_by_id(response_id)
                if response:
                    # Очищаем детальные данные переговоров, оставляя только сводку
                    if response.negotiation_data:
                        summary = {
                            'counter_offers_count': response.negotiation_data.get('counter_offers_count', 0),
                            'negotiation_duration': response._calculate_negotiation_duration(),
                            'cleaned_at': datetime.now().isoformat()
                        }
                        response.negotiation_data = summary
                        response.save()
                        cleaned_count += 1

            return {
                'cleaned_responses': cleaned_count,
                'cutoff_days': days_old,
                'processed_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'cleaned_responses': 0}


# Экспорт основных классов и функций
__all__ = [
    'Response', 'ResponseAnalytics', 'ResponseMaintenanceService',
    'ResponseStatus', 'ResponseType'
]