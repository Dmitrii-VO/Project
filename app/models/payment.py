# app/models/payment.py
"""
Модель платежей для Telegram Mini App
Поддерживает депозиты, выводы, эскроу-транзакции и комиссии
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum

from .database import db_manager
from ..utils.exceptions import PaymentError, InsufficientFundsError
from ..config.settings import ESCROW_FEE_PERCENT, MIN_WITHDRAWAL_AMOUNT, MAX_WITHDRAWAL_AMOUNT


class PaymentType(Enum):
    """Типы платежей"""
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    ESCROW_HOLD = 'escrow_hold'
    ESCROW_RELEASE = 'escrow_release'
    ESCROW_REFUND = 'escrow_refund'
    COMMISSION = 'commission'
    REFERRAL = 'referral'


class PaymentStatus(Enum):
    """Статусы платежей"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'


class PaymentMethod(Enum):
    """Методы платежей"""
    TELEGRAM_PAYMENTS = 'telegram_payments'
    SBP = 'sbp'
    CARD = 'card'
    CRYPTO = 'crypto'
    BALANCE = 'balance'


class Payment:
    """Модель платежа"""

    def __init__(self, payment_data: Dict[str, Any] = None):
        if payment_data:
            self.id = payment_data.get('id')
            self.user_id = payment_data.get('user_id')
            self.amount = Decimal(str(payment_data.get('amount', 0)))
            self.currency = payment_data.get('currency', 'RUB')
            self.payment_type = payment_data.get('payment_type')
            self.payment_method = payment_data.get('payment_method')
            self.status = payment_data.get('status', PaymentStatus.PENDING.value)
            self.description = payment_data.get('description', '')
            self.external_id = payment_data.get('external_id')
            self.metadata = self._parse_metadata(payment_data.get('metadata'))
            self.commission_amount = Decimal(str(payment_data.get('commission_amount', 0)))
            self.created_at = payment_data.get('created_at')
            self.updated_at = payment_data.get('updated_at')
            self.completed_at = payment_data.get('completed_at')
            self.expires_at = payment_data.get('expires_at')
        else:
            self.id = None
            self.user_id = None
            self.amount = Decimal('0')
            self.currency = 'RUB'
            self.payment_type = None
            self.payment_method = None
            self.status = PaymentStatus.PENDING.value
            self.description = ''
            self.external_id = None
            self.metadata = {}
            self.commission_amount = Decimal('0')
            self.created_at = None
            self.updated_at = None
            self.completed_at = None
            self.expires_at = None

    def _parse_metadata(self, metadata: Any) -> Dict[str, Any]:
        """Парсинг метаданных из JSON"""
        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(metadata, dict):
            return metadata
        return {}

    def save(self) -> bool:
        """Сохранение платежа в базу данных"""
        try:
            metadata_json = json.dumps(self.metadata) if self.metadata else None

            if self.id:
                # Обновление существующего платежа
                query = """
                        UPDATE payments
                        SET user_id           = ?, \
                            amount            = ?, \
                            currency          = ?, \
                            payment_type      = ?,
                            payment_method    = ?, \
                            status            = ?, \
                            description       = ?, \
                            external_id       = ?,
                            metadata          = ?, \
                            commission_amount = ?, \
                            updated_at        = CURRENT_TIMESTAMP,
                            completed_at      = ?, \
                            expires_at        = ?
                        WHERE id = ? \
                        """
                params = (
                    self.user_id, float(self.amount), self.currency, self.payment_type,
                    self.payment_method, self.status, self.description, self.external_id,
                    metadata_json, float(self.commission_amount), self.completed_at,
                    self.expires_at, self.id
                )
            else:
                # Создание нового платежа
                query = """
                        INSERT INTO payments (user_id, amount, currency, payment_type, payment_method, \
                                              status, description, external_id, metadata, commission_amount, \
                                              created_at, expires_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?) \
                        """
                params = (
                    self.user_id, float(self.amount), self.currency, self.payment_type,
                    self.payment_method, self.status, self.description, self.external_id,
                    metadata_json, float(self.commission_amount), self.expires_at
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового платежа
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise PaymentError(f"Ошибка сохранения платежа: {str(e)}")

    @classmethod
    def get_by_id(cls, payment_id: int) -> Optional['Payment']:
        """Получение платежа по ID"""
        query = "SELECT * FROM payments WHERE id = ?"
        result = db_manager.execute_query(query, (payment_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_external_id(cls, external_id: str) -> Optional['Payment']:
        """Получение платежа по внешнему ID"""
        query = "SELECT * FROM payments WHERE external_id = ?"
        result = db_manager.execute_query(query, (external_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_user_payments(cls, user_id: int, payment_type: str = None,
                          status: str = None, limit: int = 50) -> List['Payment']:
        """Получение платежей пользователя"""
        query = "SELECT * FROM payments WHERE user_id = ?"
        params = [user_id]

        if payment_type:
            query += " AND payment_type = ?"
            params.append(payment_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)

        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def get_pending_payments(cls, payment_type: str = None) -> List['Payment']:
        """Получение всех ожидающих платежей"""
        query = "SELECT * FROM payments WHERE status = 'pending'"
        params = []

        if payment_type:
            query += " AND payment_type = ?"
            params.append(payment_type)

        query += " ORDER BY created_at ASC"

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def create_deposit(cls, user_id: int, amount: Decimal, payment_method: str,
                       external_id: str = None, description: str = "") -> 'Payment':
        """Создание депозита"""
        payment = cls()
        payment.user_id = user_id
        payment.amount = amount
        payment.payment_type = PaymentType.DEPOSIT.value
        payment.payment_method = payment_method
        payment.status = PaymentStatus.PENDING.value
        payment.description = description or f"Пополнение баланса на {amount} RUB"
        payment.external_id = external_id
        payment.expires_at = datetime.now() + timedelta(hours=1)  # Истекает через час

        payment.save()
        return payment

    @classmethod
    def create_withdrawal(cls, user_id: int, amount: Decimal, payment_method: str,
                          withdrawal_details: Dict[str, Any], description: str = "") -> 'Payment':
        """Создание вывода средств"""
        # Проверяем лимиты
        if amount < Decimal(str(MIN_WITHDRAWAL_AMOUNT)):
            raise PaymentError(f"Минимальная сумма вывода: {MIN_WITHDRAWAL_AMOUNT} RUB")

        if amount > Decimal(str(MAX_WITHDRAWAL_AMOUNT)):
            raise PaymentError(f"Максимальная сумма вывода: {MAX_WITHDRAWAL_AMOUNT} RUB")

        # Рассчитываем комиссию (например, 3%)
        commission = amount * Decimal('0.03')
        total_deduction = amount + commission

        # Проверяем баланс пользователя
        from .user import User
        user = User.get_by_id(user_id)
        if not user or user.balance < total_deduction:
            raise InsufficientFundsError("Недостаточно средств для вывода")

        payment = cls()
        payment.user_id = user_id
        payment.amount = -total_deduction  # Отрицательная сумма для списания
        payment.payment_type = PaymentType.WITHDRAWAL.value
        payment.payment_method = payment_method
        payment.status = PaymentStatus.PENDING.value
        payment.description = description or f"Вывод средств {amount} RUB"
        payment.commission_amount = commission
        payment.metadata = {
            'withdrawal_amount': float(amount),
            'commission': float(commission),
            'total_deduction': float(total_deduction),
            'withdrawal_details': withdrawal_details
        }

        payment.save()
        return payment

    @classmethod
    def create_escrow_hold(cls, advertiser_id: int, channel_owner_id: int,
                           amount: Decimal, offer_response_id: int,
                           auto_release_hours: int = 72) -> 'Payment':
        """Создание эскроу-холда"""
        # Проверяем баланс рекламодателя
        from .user import User
        advertiser = User.get_by_id(advertiser_id)
        if not advertiser or advertiser.balance < amount:
            raise InsufficientFundsError("Недостаточно средств для эскроу")

        # Рассчитываем комиссию платформы
        escrow_fee = amount * Decimal(str(ESCROW_FEE_PERCENT / 100))

        payment = cls()
        payment.user_id = advertiser_id
        payment.amount = -(amount + escrow_fee)  # Списываем с рекламодателя
        payment.payment_type = PaymentType.ESCROW_HOLD.value
        payment.payment_method = PaymentMethod.BALANCE.value
        payment.status = PaymentStatus.COMPLETED.value  # Сразу выполняем холд
        payment.description = f"Эскроу-холд для оффера {offer_response_id}"
        payment.commission_amount = escrow_fee
        payment.metadata = {
            'recipient_id': channel_owner_id,
            'offer_response_id': offer_response_id,
            'escrow_amount': float(amount),
            'escrow_fee': float(escrow_fee),
            'auto_release_at': (datetime.now() + timedelta(hours=auto_release_hours)).isoformat()
        }

        payment.save()
        return payment

    @classmethod
    def create_escrow_release(cls, escrow_payment_id: int, released_by: int = None) -> 'Payment':
        """Освобождение эскроу-средств"""
        escrow_payment = cls.get_by_id(escrow_payment_id)
        if not escrow_payment or escrow_payment.payment_type != PaymentType.ESCROW_HOLD.value:
            raise PaymentError("Эскроу-платеж не найден")

        metadata = escrow_payment.metadata
        recipient_id = metadata.get('recipient_id')
        escrow_amount = Decimal(str(metadata.get('escrow_amount', 0)))

        if not recipient_id or escrow_amount <= 0:
            raise PaymentError("Некорректные данные эскроу")

        # Создаем платеж для получателя
        payment = cls()
        payment.user_id = recipient_id
        payment.amount = escrow_amount
        payment.payment_type = PaymentType.ESCROW_RELEASE.value
        payment.payment_method = PaymentMethod.BALANCE.value
        payment.status = PaymentStatus.COMPLETED.value
        payment.description = f"Получение средств из эскроу #{escrow_payment_id}"
        payment.metadata = {
            'escrow_payment_id': escrow_payment_id,
            'released_by': released_by,
            'original_offer_response_id': metadata.get('offer_response_id')
        }

        payment.save()
        return payment

    def update_status(self, new_status: str, external_id: str = None) -> bool:
        """Обновление статуса платежа"""
        old_status = self.status
        self.status = new_status

        if external_id:
            self.external_id = external_id

        if new_status == PaymentStatus.COMPLETED.value:
            self.completed_at = datetime.now().isoformat()

        success = self.save()

        if success and old_status != new_status:
            self._process_status_change(old_status, new_status)

        return success

    def _process_status_change(self, old_status: str, new_status: str):
        """Обработка изменения статуса"""
        if new_status == PaymentStatus.COMPLETED.value:
            self._update_user_balance()

    def _update_user_balance(self):
        """Обновление баланса пользователя"""
        try:
            from .user import User
            user = User.get_by_id(self.user_id)
            if user:
                user.update_balance(float(self.amount))
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            print(f"Ошибка обновления баланса для платежа {self.id}: {e}")

    def can_be_cancelled(self) -> bool:
        """Проверка возможности отмены платежа"""
        return self.status in [PaymentStatus.PENDING.value, PaymentStatus.PROCESSING.value]

    def cancel(self, reason: str = "") -> bool:
        """Отмена платежа"""
        if not self.can_be_cancelled():
            raise PaymentError("Платеж не может быть отменен")

        self.status = PaymentStatus.CANCELLED.value
        if reason:
            self.metadata['cancellation_reason'] = reason

        return self.save()

    def is_expired(self) -> bool:
        """Проверка истечения срока платежа"""
        if not self.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now() > expires_at
        except (ValueError, AttributeError):
            return False

    @classmethod
    def get_user_balance_history(cls, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Получение истории изменений баланса"""
        query = """
            SELECT DATE(created_at) as date, 
                   SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                   COUNT(*) as transactions
            FROM payments 
            WHERE user_id = ? AND status = 'completed' 
                  AND created_at >= datetime('now', '-{} days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """.format(days)

        results = db_manager.execute_query(query, (user_id,), fetch_all=True)

        return [
            {
                'date': row['date'],
                'income': float(row['income'] or 0),
                'expenses': float(row['expenses'] or 0),
                'transactions': row['transactions']
            }
            for row in results
        ] if results else []

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_type': self.payment_type,
            'payment_method': self.payment_method,
            'status': self.status,
            'description': self.description,
            'external_id': self.external_id,
            'metadata': self.metadata,
            'commission_amount': float(self.commission_amount),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at,
            'expires_at': self.expires_at
        }


class EscrowTransaction:
    """Модель эскроу-транзакции"""

    def __init__(self, transaction_data: Dict[str, Any] = None):
        if transaction_data:
            self.id = transaction_data.get('id')
            self.offer_response_id = transaction_data.get('offer_response_id')
            self.advertiser_id = transaction_data.get('advertiser_id')
            self.channel_owner_id = transaction_data.get('channel_owner_id')
            self.amount = Decimal(str(transaction_data.get('amount', 0)))
            self.currency = transaction_data.get('currency', 'RUB')
            self.status = transaction_data.get('status', 'pending')
            self.escrow_fee = Decimal(str(transaction_data.get('escrow_fee', 0)))
            self.created_at = transaction_data.get('created_at')
            self.released_at = transaction_data.get('released_at')
            self.cancelled_at = transaction_data.get('cancelled_at')
            self.dispute_reason = transaction_data.get('dispute_reason')
            self.auto_release_at = transaction_data.get('auto_release_at')
        else:
            self.id = None
            self.offer_response_id = None
            self.advertiser_id = None
            self.channel_owner_id = None
            self.amount = Decimal('0')
            self.currency = 'RUB'
            self.status = 'pending'
            self.escrow_fee = Decimal('0')
            self.created_at = None
            self.released_at = None
            self.cancelled_at = None
            self.dispute_reason = None
            self.auto_release_at = None

    def save(self) -> bool:
        """Сохранение эскроу-транзакции"""
        try:
            if self.id:
                query = """
                        UPDATE escrow_transactions
                        SET status         = ?, \
                            released_at    = ?, \
                            cancelled_at   = ?, \
                            dispute_reason = ?
                        WHERE id = ? \
                        """
                params = (self.status, self.released_at, self.cancelled_at,
                          self.dispute_reason, self.id)
            else:
                query = """
                        INSERT INTO escrow_transactions (offer_response_id, advertiser_id, channel_owner_id, amount, \
                                                         currency, status, escrow_fee, created_at, auto_release_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?) \
                        """
                params = (
                    self.offer_response_id, self.advertiser_id, self.channel_owner_id,
                    float(self.amount), self.currency, self.status, float(self.escrow_fee),
                    self.auto_release_at
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise PaymentError(f"Ошибка сохранения эскроу-транзакции: {str(e)}")

    @classmethod
    def get_by_offer_response(cls, offer_response_id: int) -> Optional['EscrowTransaction']:
        """Получение эскроу по ID отклика"""
        query = "SELECT * FROM escrow_transactions WHERE offer_response_id = ?"
        result = db_manager.execute_query(query, (offer_response_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_active_escrows(cls) -> List['EscrowTransaction']:
        """Получение активных эскроу-транзакций"""
        query = """
                SELECT * \
                FROM escrow_transactions
                WHERE status = 'active'
                ORDER BY created_at ASC \
                """
        results = db_manager.execute_query(query, fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    def release(self, released_by: int = None) -> bool:
        """Освобождение эскроу"""
        if self.status != 'active':
            raise PaymentError("Эскроу не активен")

        # Создаем платеж для получателя
        Payment.create_escrow_release(self.id, released_by)

        # Обновляем статус эскроу
        self.status = 'released'
        self.released_at = datetime.now().isoformat()

        return self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'offer_response_id': self.offer_response_id,
            'advertiser_id': self.advertiser_id,
            'channel_owner_id': self.channel_owner_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'escrow_fee': float(self.escrow_fee),
            'created_at': self.created_at,
            'released_at': self.released_at,
            'cancelled_at': self.cancelled_at,
            'dispute_reason': self.dispute_reason,
            'auto_release_at': self.auto_release_at
        }