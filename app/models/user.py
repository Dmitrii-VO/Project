# app/models/user.py


"""
Модель пользователей для Telegram Mini App
Поддерживает рекламодателей и владельцев каналов, управление балансом и аналитику
"""

import json
import hashlib
import hmac
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from .database import db_manager
from ..utils.exceptions import UserError, ValidationError, AuthenticationError
from ..config.settings import (TELEGRAM_BOT_TOKEN, MIN_WITHDRAWAL_AMOUNT,
                               REFERRAL_BONUS_AMOUNT, DEFAULT_USER_TYPE)

class UserType(Enum):
    """Типы пользователей"""
    CHANNEL_OWNER = 'channel_owner'
    ADVERTISER = 'advertiser'
    BOTH = 'both'  # Пользователь может быть и рекламодателем, и владельцем каналов


class UserStatus(Enum):
    """Статусы пользователей"""
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    BANNED = 'banned'
    PENDING_VERIFICATION = 'pending_verification'


class User:
    """Модель пользователя"""

    def __init__(self, user_data: Dict[str, Any] = None):
        if user_data:
            self.id = user_data.get('id')
            self.telegram_id = str(user_data.get('telegram_id', ''))
            self.username = user_data.get('username')
            self.first_name = user_data.get('first_name')
            self.last_name = user_data.get('last_name')
            self.language_code = user_data.get('language_code', 'ru')
            self.user_type = user_data.get('user_type', UserType.CHANNEL_OWNER.value)
            self.status = user_data.get('status', UserStatus.ACTIVE.value)
            self.balance = Decimal(str(user_data.get('balance', 0)))
            self.total_earned = Decimal(str(user_data.get('total_earned', 0)))
            self.total_spent = Decimal(str(user_data.get('total_spent', 0)))
            self.referrer_id = user_data.get('referrer_id')
            self.referral_code = user_data.get('referral_code')
            self.settings = self._parse_settings(user_data.get('settings'))
            self.profile_data = self._parse_profile_data(user_data.get('profile_data'))
            self.last_activity = user_data.get('last_activity')
            self.created_at = user_data.get('created_at')
            self.updated_at = user_data.get('updated_at')
        else:
            self.id = None
            self.telegram_id = ''
            self.username = None
            self.first_name = None
            self.last_name = None
            self.language_code = 'ru'
            self.user_type = UserType.CHANNEL_OWNER.value
            self.status = UserStatus.ACTIVE.value
            self.balance = Decimal('0')
            self.total_earned = Decimal('0')
            self.total_spent = Decimal('0')
            self.referrer_id = None
            self.referral_code = None
            self.settings = {}
            self.profile_data = {}
            self.last_activity = None
            self.created_at = None
            self.updated_at = None

    def _parse_settings(self, settings: Any) -> Dict[str, Any]:
        """Парсинг настроек пользователя из JSON"""
        if isinstance(settings, str):
            try:
                return json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(settings, dict):
            return settings
        return {}

    def _parse_profile_data(self, profile_data: Any) -> Dict[str, Any]:
        """Парсинг данных профиля из JSON"""
        if isinstance(profile_data, str):
            try:
                return json.loads(profile_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(profile_data, dict):
            return profile_data
        return {}

    def save(self) -> bool:
        """Сохранение пользователя в базу данных"""
        try:
            settings_json = json.dumps(self.settings) if self.settings else None
            profile_data_json = json.dumps(self.profile_data) if self.profile_data else None

            if self.id:
                # Обновление существующего пользователя
                query = """
                        UPDATE users
                        SET username      = ?, \
                            first_name    = ?, \
                            last_name     = ?, \
                            language_code = ?,
                            user_type     = ?, \
                            status        = ?, \
                            balance       = ?, \
                            total_earned  = ?,
                            total_spent   = ?, \
                            settings      = ?, \
                            profile_data  = ?,
                            last_activity = ?, \
                            updated_at    = CURRENT_TIMESTAMP
                        WHERE id = ? \
                        """
                params = (
                    self.username, self.first_name, self.last_name, self.language_code,
                    self.user_type, self.status, float(self.balance), float(self.total_earned),
                    float(self.total_spent), settings_json, profile_data_json,
                    self.last_activity, self.id
                )
            else:
                # Создание нового пользователя
                query = """
                        INSERT INTO users (telegram_id, username, first_name, last_name, language_code, \
                                           user_type, status, balance, total_earned, total_spent, \
                                           referrer_id, referral_code, settings, profile_data, \
                                           created_at, last_activity) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) \
                        """
                params = (
                    self.telegram_id, self.username, self.first_name, self.last_name,
                    self.language_code, self.user_type, self.status, float(self.balance),
                    float(self.total_earned), float(self.total_spent), self.referrer_id,
                    self.referral_code, settings_json, profile_data_json
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового пользователя
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise UserError(f"Ошибка сохранения пользователя: {str(e)}")

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        """Получение пользователя по ID"""
        query = "SELECT * FROM users WHERE id = ?"
        result = db_manager.execute_query(query, (user_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_telegram_id(cls, telegram_id: str) -> Optional['User']:
        """Получение пользователя по Telegram ID"""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        result = db_manager.execute_query(query, (str(telegram_id),), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_referral_code(cls, referral_code: str) -> Optional['User']:
        """Получение пользователя по реферальному коду"""
        query = "SELECT * FROM users WHERE referral_code = ?"
        result = db_manager.execute_query(query, (referral_code,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def create_from_telegram(cls, telegram_data: Dict[str, Any], referral_code: str = None) -> 'User':
        """Создание пользователя из данных Telegram"""
        # Валидируем данные Telegram
        if not cls._validate_telegram_data(telegram_data):
            raise AuthenticationError("Недействительные данные Telegram")

        # Проверяем, что пользователь не существует
        existing_user = cls.get_by_telegram_id(telegram_data['id'])
        if existing_user:
            return existing_user

        # Обрабатываем реферальную систему
        referrer_id = None
        if referral_code:
            referrer = cls.get_by_referral_code(referral_code)
            if referrer:
                referrer_id = referrer.id

        # Создаем пользователя
        user = cls()
        user.telegram_id = str(telegram_data['id'])
        user.username = telegram_data.get('username')
        user.first_name = telegram_data.get('first_name')
        user.last_name = telegram_data.get('last_name')
        user.language_code = telegram_data.get('language_code', 'ru')
        user.user_type = DEFAULT_USER_TYPE
        user.status = UserStatus.ACTIVE.value
        user.referrer_id = referrer_id
        user.referral_code = cls._generate_referral_code()

        # Дефолтные настройки
        user.settings = {
            'notifications_enabled': True,
            'email_notifications': False,
            'language': user.language_code,
            'timezone': 'UTC',
            'auto_accept_offers': False,
            'min_offer_price': 0
        }

        # Сохраняем профильные данные из Telegram
        user.profile_data = {
            'telegram_username': telegram_data.get('username'),
            'is_premium': telegram_data.get('is_premium', False),
            'photo_url': telegram_data.get('photo_url'),
            'registration_source': 'telegram_miniapp'
        }

        user.save()

        # Обрабатываем реферальный бонус
        if referrer_id:
            user._process_referral_bonus(referrer_id)

        return user

    @staticmethod
    def _validate_telegram_data(telegram_data: Dict[str, Any]) -> bool:
        """Валидация данных от Telegram WebApp"""
        try:
            # Проверяем обязательные поля
            if not telegram_data.get('id'):
                return False

            # Если есть hash, проверяем подпись
            if 'hash' in telegram_data:
                return User._verify_telegram_hash(telegram_data)

            return True

        except Exception:
            return False

    @staticmethod
    def _verify_telegram_hash(telegram_data: Dict[str, Any]) -> bool:
        """Проверка подписи данных Telegram WebApp"""
        try:
            if not TELEGRAM_BOT_TOKEN:
                return False

            received_hash = telegram_data.pop('hash', '')

            # Создаем строку для проверки
            data_check_string = '\n'.join([
                f"{k}={v}" for k, v in sorted(telegram_data.items())
                if k != 'hash'
            ])

            # Создаем секретный ключ
            secret_key = hmac.new(
                "WebAppData".encode(),
                TELEGRAM_BOT_TOKEN.encode(),
                hashlib.sha256
            ).digest()

            # Вычисляем hash
            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(received_hash, calculated_hash)

        except Exception:
            return False

    @staticmethod
    def _generate_referral_code() -> str:
        """Генерация реферального кода"""
        import secrets
        return f"REF_{secrets.token_hex(4).upper()}"

    def update_balance(self, amount: float, description: str = "") -> bool:
        """Обновление баланса пользователя"""
        try:
            amount_decimal = Decimal(str(amount))
            new_balance = self.balance + amount_decimal

            if new_balance < 0:
                raise UserError("Недостаточно средств")

            old_balance = self.balance
            self.balance = new_balance

            # Обновляем статистику
            if amount_decimal > 0:
                self.total_earned += amount_decimal
            else:
                self.total_spent += abs(amount_decimal)

            success = self.save()

            if success:
                # Логируем изменение баланса
                self._log_balance_change(old_balance, new_balance, amount_decimal, description)

            return success

        except Exception as e:
            raise UserError(f"Ошибка обновления баланса: {str(e)}")

    def _log_balance_change(self, old_balance: Decimal, new_balance: Decimal,
                            amount: Decimal, description: str):
        """Логирование изменений баланса"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'old_balance': float(old_balance),
                'new_balance': float(new_balance),
                'amount': float(amount),
                'description': description
            }

            # Добавляем в историю баланса в настройках
            if 'balance_history' not in self.settings:
                self.settings['balance_history'] = []

            self.settings['balance_history'].append(log_entry)

            # Оставляем только последние 100 записей
            self.settings['balance_history'] = self.settings['balance_history'][-100:]

        except Exception as e:
            print(f"Ошибка логирования изменения баланса: {e}")

    def can_withdraw(self, amount: float) -> Tuple[bool, str]:
        """Проверка возможности вывода средств"""
        amount_decimal = Decimal(str(amount))

        # Проверяем минимальную сумму
        if amount_decimal < MIN_WITHDRAWAL_AMOUNT:
            return False, f"Минимальная сумма вывода: {MIN_WITHDRAWAL_AMOUNT} RUB"

        # Проверяем баланс
        if self.balance < amount_decimal:
            return False, "Недостаточно средств"

        # Проверяем статус пользователя
        if self.status != UserStatus.ACTIVE.value:
            return False, "Аккаунт заблокирован или приостановлен"

        # Проверяем ограничения по выводу
        daily_limit = self.settings.get('daily_withdrawal_limit', 100000)
        if amount > daily_limit:
            return False, f"Превышен дневной лимит вывода: {daily_limit} RUB"

        return True, "OK"

    def get_channels(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Получение каналов пользователя"""
        try:
            from .channels import Channel

            channels = Channel.get_user_channels(self.id, include_deleted=include_inactive)
            return [channel.to_dict() for channel in channels]

        except Exception as e:
            print(f"Ошибка получения каналов пользователя {self.id}: {e}")
            return []

    def get_offers(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение офферов пользователя"""
        try:
            from .offer import Offer

            offers = Offer.get_advertiser_offers(self.id, status, limit)
            return [offer.to_dict() for offer in offers]

        except Exception as e:
            print(f"Ошибка получения офферов пользователя {self.id}: {e}")
            return []

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            stats = {
                'period_days': days,
                'user_type': self.user_type,
                'balance': float(self.balance),
                'total_earned': float(self.total_earned),
                'total_spent': float(self.total_spent),
                'profit': float(self.total_earned - self.total_spent)
            }

            if self.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                # Статистика для владельца каналов
                channel_stats = self._get_channel_owner_stats(cutoff_date)
                stats.update(channel_stats)

            if self.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                # Статистика для рекламодателя
                advertiser_stats = self._get_advertiser_stats(cutoff_date)
                stats.update(advertiser_stats)

            return stats

        except Exception as e:
            return {'error': str(e)}

    def _get_channel_owner_stats(self, cutoff_date: str) -> Dict[str, Any]:
        """Статистика для владельца каналов"""
        try:
            # Количество каналов
            channels_count = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_active = 1",
                (self.id,),
                fetch_one=True
            )[0]

            # Верифицированные каналы
            verified_channels = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_verified = 1",
                (self.id,),
                fetch_one=True
            )[0]

            # Общее количество подписчиков
            total_subscribers = db_manager.execute_query(
                "SELECT SUM(subscribers_count) FROM channels WHERE owner_id = ? AND is_active = 1",
                (self.id,),
                fetch_one=True
            )[0] or 0

            # Отклики за период
            responses_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                               as total_responses,
                       SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END)   as accepted,
                       SUM(CASE WHEN status = 'posted' THEN price ELSE 0 END) as earned
                FROM offer_responses or1
                         JOIN channels c ON or1.channel_id = c.id
                WHERE c.owner_id = ?
                  AND or1.created_at >= ?
                """,
                (self.id, cutoff_date),
                fetch_one=True
            )

            return {
                'channels': {
                    'total': channels_count,
                    'verified': verified_channels,
                    'verification_rate': (verified_channels / channels_count * 100) if channels_count > 0 else 0,
                    'total_subscribers': int(total_subscribers)
                },
                'responses': {
                    'total': responses_stats[0],
                    'accepted': responses_stats[1],
                    'acceptance_rate': (responses_stats[1] / responses_stats[0] * 100) if responses_stats[0] > 0 else 0,
                    'period_earnings': float(responses_stats[2] or 0)
                }
            }

        except Exception as e:
            return {'channels': {}, 'responses': {}, 'error': str(e)}

    def _get_advertiser_stats(self, cutoff_date: str) -> Dict[str, Any]:
        """Статистика для рекламодателя"""
        try:
            # Статистика офферов
            offers_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                              as total_offers,
                       SUM(budget)                                           as total_budget,
                       SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)    as active_offers,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_offers
                FROM offers
                WHERE advertiser_id = ?
                  AND created_at >= ?
                """,
                (self.id, cutoff_date),
                fetch_one=True
            )

            # Статистика откликов на офферы
            responses_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                                 as total_responses,
                       SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                       AVG(or1.price)                                           as avg_price,
                       SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END)   as posted
                FROM offer_responses or1
                         JOIN offers o ON or1.offer_id = o.id
                WHERE o.advertiser_id = ?
                  AND or1.created_at >= ?
                """,
                (self.id, cutoff_date),
                fetch_one=True
            )

            return {
                'offers': {
                    'total': offers_stats[0],
                    'active': offers_stats[2],
                    'completed': offers_stats[3],
                    'completion_rate': (offers_stats[3] / offers_stats[0] * 100) if offers_stats[0] > 0 else 0,
                    'total_budget': float(offers_stats[1] or 0)
                },
                'campaigns': {
                    'responses_received': responses_stats[0],
                    'responses_accepted': responses_stats[1],
                    'avg_response_price': round(float(responses_stats[2] or 0), 2),
                    'posts_published': responses_stats[3],
                    'success_rate': (responses_stats[3] / responses_stats[0] * 100) if responses_stats[0] > 0 else 0
                }
            }

        except Exception as e:
            return {'offers': {}, 'campaigns': {}, 'error': str(e)}

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Обновление настроек пользователя"""
        try:
            # Список разрешенных настроек
            allowed_settings = [
                'notifications_enabled', 'email_notifications', 'language',
                'timezone', 'auto_accept_offers', 'min_offer_price',
                'daily_withdrawal_limit', 'preferred_payment_method',
                'marketing_notifications', 'sound_notifications'
            ]

            for key, value in new_settings.items():
                if key in allowed_settings:
                    self.settings[key] = value

            return self.save()

        except Exception as e:
            raise UserError(f"Ошибка обновления настроек: {str(e)}")

    def update_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Обновление профильных данных"""
        try:
            # Обновляем основные поля
            if 'first_name' in profile_data:
                self.first_name = profile_data['first_name']

            if 'last_name' in profile_data:
                self.last_name = profile_data['last_name']

            if 'language_code' in profile_data:
                self.language_code = profile_data['language_code']

            # Обновляем дополнительные данные профиля
            allowed_profile_fields = [
                'company_name', 'website', 'description', 'contact_email',
                'phone_number', 'country', 'city', 'avatar_url'
            ]

            for key, value in profile_data.items():
                if key in allowed_profile_fields:
                    self.profile_data[key] = value

            return self.save()

        except Exception as e:
            raise UserError(f"Ошибка обновления профиля: {str(e)}")

    def switch_user_type(self, new_type: str) -> bool:
        """Смена типа пользователя"""
        if new_type not in [ut.value for ut in UserType]:
            raise ValidationError("Недопустимый тип пользователя")

        self.user_type = new_type
        return self.save()

    def suspend(self, reason: str = "") -> bool:
        """Приостановка аккаунта"""
        self.status = UserStatus.SUSPENDED.value
        if reason:
            self.profile_data['suspension_reason'] = reason
            self.profile_data['suspended_at'] = datetime.now().isoformat()

        return self.save()

    def ban(self, reason: str = "") -> bool:
        """Блокировка аккаунта"""
        self.status = UserStatus.BANNED.value
        if reason:
            self.profile_data['ban_reason'] = reason
            self.profile_data['banned_at'] = datetime.now().isoformat()

        return self.save()

    def reactivate(self) -> bool:
        """Реактивация аккаунта"""
        self.status = UserStatus.ACTIVE.value

        # Удаляем информацию о блокировке/приостановке
        fields_to_remove = ['suspension_reason', 'suspended_at', 'ban_reason', 'banned_at']
        for field in fields_to_remove:
            self.profile_data.pop(field, None)

        return self.save()

    def update_activity(self) -> bool:
        """Обновление времени последней активности"""
        self.last_activity = datetime.now().isoformat()
        return self.save()

    def get_referrals(self, limit: int = 100) -> List['User']:
        """Получение списка рефералов"""
        query = "SELECT * FROM users WHERE referrer_id = ? ORDER BY created_at DESC LIMIT ?"
        results = db_manager.execute_query(query, (self.id, limit), fetch_all=True)

        return [User(dict(row)) for row in results] if results else []

    def get_referral_earnings(self) -> Dict[str, Any]:
        """Получение статистики по рефералам"""
        try:
            referrals = self.get_referrals()
            total_referrals = len(referrals)

            # Подсчитываем общие доходы от рефералов
            total_referral_earnings = sum(
                ref.total_spent * Decimal('0.05')  # 5% комиссия
                for ref in referrals
            )

            # Активные рефералы (с активностью за последние 30 дней)
            cutoff_date = datetime.now() - timedelta(days=30)
            active_referrals = 0

            for ref in referrals:
                if ref.last_activity:
                    try:
                        last_activity = datetime.fromisoformat(ref.last_activity.replace('Z', '+00:00'))
                        if last_activity >= cutoff_date:
                            active_referrals += 1
                    except (ValueError, AttributeError):
                        pass

            return {
                'total_referrals': total_referrals,
                'active_referrals': active_referrals,
                'total_earnings': float(total_referral_earnings),
                'referral_code': self.referral_code,
                'conversion_rate': (active_referrals / total_referrals * 100) if total_referrals > 0 else 0
            }

        except Exception as e:
            return {
                'total_referrals': 0,
                'active_referrals': 0,
                'total_earnings': 0,
                'referral_code': self.referral_code,
                'error': str(e)
            }

    def _process_referral_bonus(self, referrer_id: int):
        """Обработка реферального бонуса"""
        try:
            referrer = User.get_by_id(referrer_id)
            if referrer and REFERRAL_BONUS_AMOUNT > 0:
                # Начисляем бонус рефереру
                referrer.update_balance(
                    REFERRAL_BONUS_AMOUNT,
                    f"Реферальный бонус за приглашение пользователя {self.telegram_id}"
                )

                # Можем также начислить бонус новому пользователю
                welcome_bonus = REFERRAL_BONUS_AMOUNT * 0.5  # 50% от реферального бонуса
                if welcome_bonus > 0:
                    self.update_balance(welcome_bonus, "Приветственный бонус")

        except Exception as e:
            print(f"Ошибка обработки реферального бонуса: {e}")

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language_code': self.language_code,
            'user_type': self.user_type,
            'status': self.status,
            'balance': float(self.balance) if self.balance is not None else 0.0,
            'total_earned': float(self.total_earned) if self.total_earned is not None else 0.0,
            'total_spent': float(self.total_spent) if self.total_spent is not None else 0.0,
            'referral_code': self.referral_code,
            'profile_data': self.profile_data if self.profile_data is not None else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }

        if include_sensitive:
            result.update({
                'settings': self.settings if self.settings is not None else {},
                'referrer_id': self.referrer_id,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            })

        return result


class UserAnalytics:
    """Класс для аналитики пользователей"""

    @staticmethod
    def get_platform_user_stats() -> Dict[str, Any]:
        """Получение общей статистики пользователей платформы"""
        try:
            # Общее количество пользователей
            total_users = db_manager.execute_query(
                "SELECT COUNT(*) FROM users",
                fetch_one=True
            )[0]

            # Активные пользователи (с активностью за последние 30 дней)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            active_users = db_manager.execute_query(
                "SELECT COUNT(*) FROM users WHERE last_activity >= ?",
                (thirty_days_ago,),
                fetch_one=True
            )[0]

            # Распределение по типам пользователей
            user_types = db_manager.execute_query(
                """
                SELECT user_type, COUNT(*) as count
                FROM users
                GROUP BY user_type
                """,
                fetch_all=True
            )

            # Статистика регистраций
            registration_stats = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, COUNT (*) as registrations
                FROM users
                WHERE created_at >= date ('now', '-30 days')
                GROUP BY DATE (created_at)
                ORDER BY date DESC
                """,
                fetch_all=True
            )

            # Статистика балансов
            balance_stats = db_manager.execute_query(
                """
                SELECT SUM(balance)                            as total_balance,
                       AVG(balance)                            as avg_balance,
                       MAX(balance)                            as max_balance,
                       COUNT(CASE WHEN balance > 0 THEN 1 END) as users_with_balance
                FROM users
                """,
                fetch_one=True
            )

            # Топ пользователи по доходам
            top_earners = db_manager.execute_query(
                """
                SELECT username, first_name, user_type, total_earned
                FROM users
                WHERE total_earned > 0
                ORDER BY total_earned DESC LIMIT 10
                """,
                fetch_all=True
            )

            return {
                'users': {
                    'total': total_users,
                    'active_30d': active_users,
                    'activity_rate': (active_users / total_users * 100) if total_users > 0 else 0
                },
                'user_types': [
                    {'type': row[0], 'count': row[1]}
                    for row in user_types
                ] if user_types else [],
                'registrations': [
                    {'date': row[0], 'count': row[1]}
                    for row in registration_stats
                ] if registration_stats else [],
                'balance': {
                    'total': float(balance_stats[0] or 0),
                    'average': round(float(balance_stats[1] or 0), 2),
                    'maximum': float(balance_stats[2] or 0),
                    'users_with_balance': balance_stats[3]
                },
                'top_earners': [
                    {
                        'username': row[0] or 'Анонимный',
                        'name': row[1] or '',
                        'type': row[2],
                        'earnings': float(row[3])
                    }
                    for row in top_earners
                ] if top_earners else []
            }

        except Exception as e:
            raise UserError(f"Ошибка получения статистики пользователей: {str(e)}")

    @staticmethod
    def get_user_engagement_metrics(days: int = 30) -> Dict[str, Any]:
        """Получение метрик вовлеченности пользователей"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Пользователи с активностью
            activity_stats = db_manager.execute_query(
                """
                SELECT COUNT(CASE WHEN last_activity >= ? THEN 1 END)                       as active_users,
                       COUNT(CASE WHEN last_activity >= date ('now', '-7 days') THEN 1 END) as weekly_active,
                       COUNT(CASE WHEN last_activity >= date ('now', '-1 day') THEN 1 END)  as daily_active,
                       COUNT(*)                                                             as total_users
                FROM users
                """,
                (cutoff_date,),
                fetch_one=True
            )

            # Транзакционная активность
            transaction_stats = db_manager.execute_query(
                """
                SELECT COUNT(DISTINCT user_id) as users_with_transactions,
                       COUNT(*)                as total_transactions,
                       AVG(amount)             as avg_transaction_amount
                FROM payments
                WHERE created_at >= ?
                """,
                (cutoff_date,),
                fetch_one=True
            )

            # Создание контента (офферы и каналы)
            content_stats = db_manager.execute_query(
                """
                SELECT (SELECT COUNT(DISTINCT advertiser_id) FROM offers WHERE created_at >= ?) as active_advertisers,
                       (SELECT COUNT(DISTINCT owner_id) FROM channels WHERE created_at >= ?)    as new_channel_owners,
                       (SELECT COUNT(*) FROM offers WHERE created_at >= ?)                      as new_offers,
                       (SELECT COUNT(*) FROM channels WHERE created_at >= ?)                    as new_channels
                """,
                (cutoff_date, cutoff_date, cutoff_date, cutoff_date),
                fetch_one=True
            )

            return {
                'period_days': days,
                'activity': {
                    'monthly_active_users': activity_stats[0],
                    'weekly_active_users': activity_stats[1],
                    'daily_active_users': activity_stats[2],
                    'total_users': activity_stats[3],
                    'monthly_retention': (activity_stats[0] / activity_stats[3] * 100) if activity_stats[3] > 0 else 0
                },
                'transactions': {
                    'active_users': transaction_stats[0],
                    'total_transactions': transaction_stats[1],
                    'avg_amount': round(float(transaction_stats[2] or 0), 2),
                    'transaction_rate': (transaction_stats[0] / activity_stats[3] * 100) if activity_stats[3] > 0 else 0
                },
                'content_creation': {
                    'active_advertisers': content_stats[0],
                    'new_channel_owners': content_stats[1],
                    'new_offers': content_stats[2],
                    'new_channels': content_stats[3]
                }
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_retention_cohorts(months: int = 6) -> Dict[str, Any]:
        """Анализ когорт пользователей по месяцам регистрации"""
        try:
            cohorts = []

            for month_offset in range(months):
                # Определяем месяц когорты
                cohort_month = datetime.now() - timedelta(days=30 * month_offset)
                cohort_start = cohort_month.replace(day=1)
                next_month = (cohort_start + timedelta(days=32)).replace(day=1)

                # Пользователи, зарегистрированные в этом месяце
                cohort_users = db_manager.execute_query(
                    """
                    SELECT id, created_at
                    FROM users
                    WHERE created_at >= ?
                      AND created_at < ?
                    """,
                    (cohort_start.isoformat(), next_month.isoformat()),
                    fetch_all=True
                )

                if not cohort_users:
                    continue

                cohort_size = len(cohort_users)
                user_ids = [str(user[0]) for user in cohort_users]

                # Считаем активность по неделям
                weekly_retention = []
                for week in range(min(4, int((datetime.now() - cohort_start).days / 7))):
                    week_start = cohort_start + timedelta(weeks=week)
                    week_end = week_start + timedelta(weeks=1)

                    active_users = db_manager.execute_query(
                        f"""
                        SELECT COUNT(*) FROM users 
                        WHERE id IN ({','.join(['?'] * len(user_ids))})
                        AND last_activity >= ? AND last_activity < ?
                        """,
                        (*user_ids, week_start.isoformat(), week_end.isoformat()),
                        fetch_one=True
                    )[0]

                    retention_rate = (active_users / cohort_size * 100) if cohort_size > 0 else 0
                    weekly_retention.append({
                        'week': week + 1,
                        'active_users': active_users,
                        'retention_rate': round(retention_rate, 1)
                    })

                cohorts.append({
                    'cohort_month': cohort_start.strftime('%Y-%m'),
                    'cohort_size': cohort_size,
                    'weekly_retention': weekly_retention
                })

            return {
                'cohorts': cohorts,
                'analysis_period_months': months,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'cohorts': []}


class UserNotificationService:
    """Сервис уведомлений пользователей"""

    @staticmethod
    def send_welcome_notification(user: User) -> bool:
        """Отправка приветственного уведомления"""
        try:
            from ..services.notification_service import NotificationService

            welcome_message = f"""
🎉 Добро пожаловать в платформу рекламы!

Привет, {user.first_name or user.username or 'пользователь'}!

Вы успешно зарегистрировались. Теперь вы можете:
• Добавлять свои каналы для монетизации
• Создавать рекламные предложения
• Зарабатывать на размещении рекламы

🎁 Ваш реферальный код: {user.referral_code}
Приглашайте друзей и получайте бонусы!

Начните с добавления вашего первого канала 👇
            """

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                welcome_message,
                {
                    'type': 'welcome',
                    'user_id': user.id,
                    'referral_code': user.referral_code
                }
            )

        except Exception as e:
            print(f"Ошибка отправки приветственного уведомления: {e}")
            return False

    @staticmethod
    def send_balance_notification(user: User, amount: float, transaction_type: str) -> bool:
        """Уведомление об изменении баланса"""
        try:
            from ..services.notification_service import NotificationService

            if transaction_type == 'deposit':
                emoji = "💰"
                action = "пополнен"
            elif transaction_type == 'withdrawal':
                emoji = "💸"
                action = "списан"
            elif transaction_type == 'earning':
                emoji = "🎉"
                action = "начислен доход"
            else:
                emoji = "💳"
                action = "изменен"

            message = f"""
{emoji} Баланс {action}

Сумма: {abs(amount):,.2f} ₽
Текущий баланс: {user.balance:,.2f} ₽

Все операции можно отслеживать в разделе "Платежи".
            """

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                message,
                {
                    'type': 'balance_change',
                    'user_id': user.id,
                    'amount': amount,
                    'transaction_type': transaction_type
                }
            )

        except Exception as e:
            print(f"Ошибка отправки уведомления о балансе: {e}")
            return False

    @staticmethod
    def send_milestone_notification(user: User, milestone_type: str, value: Any) -> bool:
        """Уведомление о достижениях пользователя"""
        try:
            from ..services.notification_service import NotificationService

            milestone_messages = {
                'first_channel': f"🎊 Поздравляем! Вы добавили свой первый канал: {value}",
                'first_offer': f"🚀 Отлично! Вы создали свой первый оффер: {value}",
                'first_earning': f"💎 Ваш первый заработок: {value} ₽! Так держать!",
                'channels_milestone': f"📺 У вас уже {value} каналов! Впечатляющий рост!",
                'earnings_milestone': f"💰 Поздравляем! Общий доход достиг {value} ₽!",
                'referral_milestone': f"👥 Отлично! У вас уже {value} рефералов!"
            }

            message = milestone_messages.get(
                milestone_type,
                f"🎉 Поздравляем с достижением: {milestone_type}"
            )

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                message,
                {
                    'type': 'milestone',
                    'user_id': user.id,
                    'milestone_type': milestone_type,
                    'value': value
                }
            )

        except Exception as e:
            print(f"Ошибка отправки уведомления о достижении: {e}")
            return False


class UserRecommendationService:
    """Сервис рекомендаций для пользователей"""

    @staticmethod
    def get_personalized_recommendations(user: User) -> List[Dict[str, Any]]:
        """Получение персонализированных рекомендаций"""
        try:
            recommendations = []

            # Рекомендации для новых пользователей
            if not user.last_activity or (
                    datetime.now() - datetime.fromisoformat(user.last_activity.replace('Z', '+00:00'))).days < 7:
                recommendations.extend(UserRecommendationService._get_new_user_recommendations(user))

            # Рекомендации для владельцев каналов
            if user.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                recommendations.extend(UserRecommendationService._get_channel_owner_recommendations(user))

            # Рекомендации для рекламодателей
            if user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                recommendations.extend(UserRecommendationService._get_advertiser_recommendations(user))

            # Общие рекомендации по улучшению
            recommendations.extend(UserRecommendationService._get_improvement_recommendations(user))

            # Сортируем по приоритету и возвращаем топ-5
            recommendations.sort(key=lambda x: x['priority'], reverse=True)
            return recommendations[:5]

        except Exception as e:
            return [{'type': 'error', 'title': 'Ошибка рекомендаций', 'description': str(e), 'priority': 0}]

    @staticmethod
    def _get_new_user_recommendations(user: User) -> List[Dict[str, Any]]:
        """Рекомендации для новых пользователей"""
        recommendations = []

        # Проверяем, есть ли каналы
        channels_count = len(user.get_channels())
        if channels_count == 0:
            recommendations.append({
                'type': 'add_first_channel',
                'title': 'Добавьте ваш первый канал',
                'description': 'Начните зарабатывать, добавив свой Telegram канал',
                'priority': 100,
                'action_url': '/channels',
                'icon': '📺'
            })

        # Проверяем баланс
        if user.balance == 0 and user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
            recommendations.append({
                'type': 'add_balance',
                'title': 'Пополните баланс',
                'description': 'Добавьте средства для создания рекламных предложений',
                'priority': 90,
                'action_url': '/payments',
                'icon': '💰'
            })

        # Рекомендация по настройке профиля
        if not user.profile_data.get('description'):
            recommendations.append({
                'type': 'complete_profile',
                'title': 'Заполните профиль',
                'description': 'Добавьте описание и контактную информацию',
                'priority': 80,
                'action_url': '/profile',
                'icon': '👤'
            })

        return recommendations

    @staticmethod
    def _get_channel_owner_recommendations(user: User) -> List[Dict[str, Any]]:
        """Рекомендации для владельцев каналов"""
        recommendations = []
        channels = user.get_channels()

        # Проверяем верификацию каналов
        unverified_channels = [ch for ch in channels if not ch['is_verified']]
        if unverified_channels:
            recommendations.append({
                'type': 'verify_channels',
                'title': 'Верифицируйте каналы',
                'description': f'{len(unverified_channels)} каналов не верифицированы',
                'priority': 95,
                'action_url': '/channels',
                'icon': '✅'
            })

        # Проверяем цены за размещение
        channels_without_price = [ch for ch in channels if ch['price_per_post'] == 0]
        if channels_without_price:
            recommendations.append({
                'type': 'set_prices',
                'title': 'Установите цены',
                'description': f'{len(channels_without_price)} каналов без цен за размещение',
                'priority': 85,
                'action_url': '/channels',
                'icon': '💸'
            })

        # Рекомендация по улучшению описания каналов
        if len(channels) > 0:
            avg_subscribers = sum(ch['subscribers_count'] for ch in channels) / len(channels)
            if avg_subscribers > 10000:
                recommendations.append({
                    'type': 'premium_features',
                    'title': 'Используйте премиум функции',
                    'description': 'Ваши каналы подходят для премиум размещений',
                    'priority': 75,
                    'action_url': '/premium',
                    'icon': '💎'
                })

        return recommendations

    @staticmethod
    def _get_advertiser_recommendations(user: User) -> List[Dict[str, Any]]:
        """Рекомендации для рекламодателей"""
        recommendations = []
        offers = user.get_offers(limit=10)

        # Рекомендация создать первый оффер
        if len(offers) == 0:
            recommendations.append({
                'type': 'create_first_offer',
                'title': 'Создайте первый оффер',
                'description': 'Начните рекламную кампанию с создания оффера',
                'priority': 95,
                'action_url': '/offers',
                'icon': '🎯'
            })

        # Анализ производительности офферов
        active_offers = [offer for offer in offers if offer['status'] == 'active']
        if len(active_offers) == 0 and len(offers) > 0:
            recommendations.append({
                'type': 'reactivate_offers',
                'title': 'Активируйте офферы',
                'description': 'У вас нет активных рекламных предложений',
                'priority': 90,
                'action_url': '/offers',
                'icon': '🚀'
            })

        # Рекомендация по бюджету
        if user.balance < 5000 and len(offers) > 0:
            recommendations.append({
                'type': 'increase_budget',
                'title': 'Увеличьте бюджет',
                'description': 'Низкий баланс может ограничить эффективность кампаний',
                'priority': 80,
                'action_url': '/payments',
                'icon': '💳'
            })

        return recommendations

    @staticmethod
    def _get_improvement_recommendations(user: User) -> List[Dict[str, Any]]:
        """Общие рекомендации по улучшению"""
        recommendations = []

        # Рекомендация по рефералам
        referral_stats = user.get_referral_earnings()
        if referral_stats['total_referrals'] < 3:
            recommendations.append({
                'type': 'invite_referrals',
                'title': 'Пригласите друзей',
                'description': f'Код: {user.referral_code}. Получайте 5% с их оборота',
                'priority': 70,
                'action_url': '/referrals',
                'icon': '👥'
            })

        # Рекомендация по аналитике
        if user.total_earned > 0:
            recommendations.append({
                'type': 'check_analytics',
                'title': 'Изучите аналитику',
                'description': 'Анализируйте эффективность для роста доходов',
                'priority': 65,
                'action_url': '/analytics',
                'icon': '📊'
            })

        return recommendations


# Утилитарные функции для работы с пользователями
class UserUtils:
    """Утилитарные функции для работы с пользователями"""

    @staticmethod
    def generate_user_avatar_url(user: User) -> str:
        """Генерация URL аватара пользователя"""
        # Если есть фото из Telegram
        if user.profile_data.get('photo_url'):
            return user.profile_data['photo_url']

        # Генерируем аватар на основе инициалов
        initials = ""
        if user.first_name:
            initials += user.first_name[0].upper()
        if user.last_name:
            initials += user.last_name[0].upper()

        if not initials and user.username:
            initials = user.username[0].upper()

        if not initials:
            initials = "U"

        # Можно использовать сервис генерации аватаров
        return f"https://ui-avatars.com/api/?name={initials}&background=random&color=fff&size=128"

    @staticmethod
    def format_user_display_name(user: User) -> str:
        """Форматирование отображаемого имени пользователя"""
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        elif user.username:
            return f"@{user.username}"
        else:
            return f"Пользователь {user.telegram_id[-4:]}"

    @staticmethod
    def calculate_user_rating(user: User) -> Dict[str, Any]:
        """Расчет рейтинга пользователя"""
        try:
            rating_score = 0
            factors = []

            # Факторы для владельцев каналов
            if user.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                channels = user.get_channels()
                verified_channels = [ch for ch in channels if ch['is_verified']]

                # Бонус за верифицированные каналы
                if verified_channels:
                    channel_bonus = len(verified_channels) * 10
                    rating_score += channel_bonus
                    factors.append(f"+{channel_bonus} за {len(verified_channels)} верифицированных каналов")

                # Бонус за общее количество подписчиков
                total_subscribers = sum(ch['subscribers_count'] for ch in channels)
                if total_subscribers > 0:
                    subscriber_bonus = min(total_subscribers // 1000, 50)  # Макс 50 баллов
                    rating_score += subscriber_bonus
                    factors.append(f"+{subscriber_bonus} за {total_subscribers:,} подписчиков")

            # Факторы для рекламодателей
            if user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                # Бонус за общие расходы
                if user.total_spent > 0:
                    spend_bonus = min(int(user.total_spent // 1000), 100)  # Макс 100 баллов
                    rating_score += spend_bonus
                    factors.append(f"+{spend_bonus} за траты {user.total_spent:,.0f} ₽")

                # Бонус за успешные кампании
                offers = user.get_offers()
                completed_offers = [offer for offer in offers if offer['status'] == 'completed']
                if completed_offers:
                    campaign_bonus = len(completed_offers) * 5
                    rating_score += campaign_bonus
                    factors.append(f"+{campaign_bonus} за {len(completed_offers)} завершенных кампаний")

            # Общие факторы
            # Бонус за активность
            if user.last_activity:
                try:
                    last_activity = datetime.fromisoformat(user.last_activity.replace('Z', '+00:00'))
                    days_inactive = (datetime.now() - last_activity).days

                    if days_inactive <= 7:
                        activity_bonus = 20
                        factors.append(f"+{activity_bonus} за активность")
                        rating_score += activity_bonus
                    elif days_inactive <= 30:
                        activity_bonus = 10
                        factors.append(f"+{activity_bonus} за недавнюю активность")
                        rating_score += activity_bonus
                except (ValueError, AttributeError):
                    pass

            # Бонус за рефералов
            referral_stats = user.get_referral_earnings()
            if referral_stats['total_referrals'] > 0:
                referral_bonus = min(referral_stats['total_referrals'] * 3, 30)
                rating_score += referral_bonus
                factors.append(f"+{referral_bonus} за {referral_stats['total_referrals']} рефералов")

            # Определяем уровень рейтинга
            if rating_score >= 200:
                level = "Платиновый"
                level_color = "#E5E4E2"
            elif rating_score >= 100:
                level = "Золотой"
                level_color = "#FFD700"
            elif rating_score >= 50:
                level = "Серебряный"
                level_color = "#C0C0C0"
            elif rating_score >= 20:
                level = "Бронзовый"
                level_color = "#CD7F32"
            else:
                level = "Новичок"
                level_color = "#90EE90"

            return {
                'score': rating_score,
                'level': level,
                'level_color': level_color,
                'factors': factors,
                'next_level_threshold': UserUtils._get_next_level_threshold(rating_score),
                'progress_to_next': UserUtils._calculate_progress_to_next_level(rating_score)
            }

        except Exception as e:
            return {
                'score': 0,
                'level': 'Не определен',
                'level_color': '#808080',
                'factors': [],
                'error': str(e)
            }

    @staticmethod
    def _get_next_level_threshold(current_score: int) -> int:
        """Получение порога для следующего уровня"""
        thresholds = [20, 50, 100, 200]

        for threshold in thresholds:
            if current_score < threshold:
                return threshold

        return thresholds[-1]  # Максимальный уровень

    @staticmethod
    def _calculate_progress_to_next_level(current_score: int) -> float:
        """Расчет прогресса до следующего уровня в процентах"""
        next_threshold = UserUtils._get_next_level_threshold(current_score)

        if current_score >= 200:  # Максимальный уровень
            return 100.0

        # Определяем предыдущий порог
        thresholds = [0, 20, 50, 100, 200]
        prev_threshold = 0

        for i, threshold in enumerate(thresholds):
            if next_threshold == threshold and i > 0:
                prev_threshold = thresholds[i - 1]
                break

        if next_threshold == prev_threshold:
            return 100.0

        progress = (current_score - prev_threshold) / (next_threshold - prev_threshold) * 100
        return round(min(max(progress, 0), 100), 1)

    @staticmethod
    def get_user_achievements(user: User) -> List[Dict[str, Any]]:
        """Получение достижений пользователя"""
        achievements = []

        try:
            # Достижения за регистрацию
            if user.created_at:
                achievements.append({
                    'id': 'registered',
                    'title': 'Добро пожаловать!',
                    'description': 'Успешная регистрация в платформе',
                    'icon': '🎉',
                    'earned_at': user.created_at,
                    'category': 'основные'
                })

            # Достижения для владельцев каналов
            if user.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                channels = user.get_channels()

                if len(channels) >= 1:
                    achievements.append({
                        'id': 'first_channel',
                        'title': 'Первый канал',
                        'description': 'Добавлен первый канал',
                        'icon': '📺',
                        'category': 'каналы'
                    })

                if len(channels) >= 5:
                    achievements.append({
                        'id': 'channel_collector',
                        'title': 'Коллекционер каналов',
                        'description': 'Добавлено 5 каналов',
                        'icon': '📚',
                        'category': 'каналы'
                    })

                verified_channels = [ch for ch in channels if ch['is_verified']]
                if len(verified_channels) >= 1:
                    achievements.append({
                        'id': 'verified_owner',
                        'title': 'Верифицированный владелец',
                        'description': 'Первый канал верифицирован',
                        'icon': '✅',
                        'category': 'каналы'
                    })

                total_subscribers = sum(ch['subscribers_count'] for ch in channels)
                if total_subscribers >= 10000:
                    achievements.append({
                        'id': 'big_audience',
                        'title': 'Большая аудитория',
                        'description': '10K+ подписчиков суммарно',
                        'icon': '👥',
                        'category': 'каналы'
                    })

                if total_subscribers >= 100000:
                    achievements.append({
                        'id': 'massive_reach',
                        'title': 'Массовый охват',
                        'description': '100K+ подписчиков суммарно',
                        'icon': '🎯',
                        'category': 'каналы'
                    })

            # Достижения для рекламодателей
            if user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                offers = user.get_offers()

                if len(offers) >= 1:
                    achievements.append({
                        'id': 'first_campaign',
                        'title': 'Первая кампания',
                        'description': 'Создан первый оффер',
                        'icon': '🚀',
                        'category': 'реклама'
                    })

                completed_offers = [offer for offer in offers if offer['status'] == 'completed']
                if len(completed_offers) >= 5:
                    achievements.append({
                        'id': 'campaign_master',
                        'title': 'Мастер кампаний',
                        'description': '5 завершенных кампаний',
                        'icon': '🏆',
                        'category': 'реклама'
                    })

                if user.total_spent >= 10000:
                    achievements.append({
                        'id': 'big_spender',
                        'title': 'Крупный рекламодатель',
                        'description': 'Потрачено 10K+ рублей',
                        'icon': '💰',
                        'category': 'реклама'
                    })

            # Финансовые достижения
            if user.total_earned >= 1000:
                achievements.append({
                    'id': 'first_earning',
                    'title': 'Первый заработок',
                    'description': 'Заработано 1K+ рублей',
                    'icon': '💎',
                    'category': 'финансы'
                })

            if user.total_earned >= 10000:
                achievements.append({
                    'id': 'good_earner',
                    'title': 'Хороший заработок',
                    'description': 'Заработано 10K+ рублей',
                    'icon': '💸',
                    'category': 'финансы'
                })

            if user.total_earned >= 100000:
                achievements.append({
                    'id': 'top_earner',
                    'title': 'Топ заработок',
                    'description': 'Заработано 100K+ рублей',
                    'icon': '🤑',
                    'category': 'финансы'
                })

            # Социальные достижения
            referral_stats = user.get_referral_earnings()
            if referral_stats['total_referrals'] >= 3:
                achievements.append({
                    'id': 'influencer',
                    'title': 'Влиятельная личность',
                    'description': 'Привлечено 3+ рефералов',
                    'icon': '🌟',
                    'category': 'социальные'
                })

            if referral_stats['total_referrals'] >= 10:
                achievements.append({
                    'id': 'super_influencer',
                    'title': 'Супер влиятельная личность',
                    'description': 'Привлечено 10+ рефералов',
                    'icon': '⭐',
                    'category': 'социальные'
                })

            # Достижения активности
            if user.last_activity:
                try:
                    registration_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                    days_since_registration = (datetime.now() - registration_date).days

                    if days_since_registration >= 30:
                        achievements.append({
                            'id': 'monthly_user',
                            'title': 'Месяц с нами',
                            'description': '30 дней в платформе',
                            'icon': '📅',
                            'category': 'активность'
                        })

                    if days_since_registration >= 365:
                        achievements.append({
                            'id': 'yearly_user',
                            'title': 'Год с нами',
                            'description': '365 дней в платформе',
                            'icon': '🎂',
                            'category': 'активность'
                        })
                except (ValueError, AttributeError):
                    pass

            return achievements

        except Exception as e:
            return [{
                'id': 'error',
                'title': 'Ошибка получения достижений',
                'description': str(e),
                'icon': '❌',
                'category': 'система'
            }]

    @staticmethod
    def suggest_next_actions(user: User) -> List[Dict[str, Any]]:
        """Предложение следующих действий для пользователя"""
        try:
            actions = []

            # Для новых пользователей
            if not user.last_activity or (
                    datetime.now() - datetime.fromisoformat(user.last_activity.replace('Z', '+00:00'))).days < 7:
                if len(user.get_channels()) == 0:
                    actions.append({
                        'title': 'Добавьте первый канал',
                        'description': 'Начните монетизацию, добавив свой канал',
                        'priority': 'high',
                        'url': '/channels',
                        'icon': '📺'
                    })

                if user.balance == 0 and user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                    actions.append({
                        'title': 'Пополните баланс',
                        'description': 'Добавьте средства для создания офферов',
                        'priority': 'medium',
                        'url': '/payments',
                        'icon': '💰'
                    })

            # Для владельцев каналов
            if user.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                channels = user.get_channels()
                unverified = [ch for ch in channels if not ch['is_verified']]

                if unverified:
                    actions.append({
                        'title': 'Верифицируйте каналы',
                        'description': f'{len(unverified)} каналов ожидают верификации',
                        'priority': 'high',
                        'url': '/channels',
                        'icon': '✅'
                    })

                no_price = [ch for ch in channels if ch['price_per_post'] == 0]
                if no_price:
                    actions.append({
                        'title': 'Установите цены',
                        'description': f'{len(no_price)} каналов без цен',
                        'priority': 'medium',
                        'url': '/channels',
                        'icon': '💸'
                    })

            # Для рекламодателей
            if user.user_type in [UserType.ADVERTISER.value, UserType.BOTH.value]:
                offers = user.get_offers()

                if len(offers) == 0:
                    actions.append({
                        'title': 'Создайте первый оффер',
                        'description': 'Запустите рекламную кампанию',
                        'priority': 'high',
                        'url': '/offers',
                        'icon': '🎯'
                    })

                active_offers = [offer for offer in offers if offer['status'] == 'active']
                if len(active_offers) == 0 and len(offers) > 0:
                    actions.append({
                        'title': 'Активируйте офферы',
                        'description': 'У вас нет активных предложений',
                        'priority': 'medium',
                        'url': '/offers',
                        'icon': '🚀'
                    })

            # Общие действия
            referral_stats = user.get_referral_earnings()
            if referral_stats['total_referrals'] < 3:
                actions.append({
                    'title': 'Пригласите друзей',
                    'description': 'Получайте 5% с оборота рефералов',
                    'priority': 'low',
                    'url': '/referrals',
                    'icon': '👥'
                })

            if user.total_earned > 0:
                actions.append({
                    'title': 'Изучите аналитику',
                    'description': 'Анализируйте свою эффективность',
                    'priority': 'low',
                    'url': '/analytics',
                    'icon': '📊'
                })

            return actions[:5]  # Возвращаем топ-5 действий

        except Exception as e:
            return [{
                'title': 'Ошибка рекомендаций',
                'description': str(e),
                'priority': 'low',
                'url': '/',
                'icon': '❌'
            }]


class UserSecurityService:
    """Сервис безопасности пользователей"""

    @staticmethod
    def check_suspicious_activity(user: User) -> Dict[str, Any]:
        """Проверка подозрительной активности"""
        try:
            warnings = []
            risk_score = 0

            # Проверка частоты транзакций
            recent_payments = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM payments
                WHERE user_id = ?
                  AND created_at >= datetime('now', '-1 hour')
                """,
                (user.id,),
                fetch_one=True
            )[0]

            if recent_payments > 10:
                warnings.append("Высокая частота транзакций")
                risk_score += 30

            # Проверка крупных сумм
            large_transactions = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM payments
                WHERE user_id = ?
                  AND ABS(amount) > 50000
                  AND created_at >= datetime('now', '-24 hours')
                """,
                (user.id,),
                fetch_one=True
            )[0]

            if large_transactions > 0:
                warnings.append("Крупные транзакции за последние 24 часа")
                risk_score += 20

            # Проверка новых каналов с большим количеством подписчиков
            if user.user_type in [UserType.CHANNEL_OWNER.value, UserType.BOTH.value]:
                recent_big_channels = db_manager.execute_query(
                    """
                    SELECT COUNT(*)
                    FROM channels
                    WHERE owner_id = ?
                      AND subscribers_count > 100000
                      AND created_at >= datetime('now', '-7 days')
                    """,
                    (user.id,),
                    fetch_one=True
                )[0]

                if recent_big_channels > 0:
                    warnings.append("Добавлены каналы с большой аудиторией")
                    risk_score += 15

            # Определение уровня риска
            if risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'warnings': warnings,
                'requires_verification': risk_score >= 40,
                'recommended_actions': UserSecurityService._get_security_recommendations(risk_level)
            }

        except Exception as e:
            return {
                'risk_level': 'unknown',
                'risk_score': 0,
                'warnings': [f'Ошибка проверки: {str(e)}'],
                'requires_verification': False,
                'recommended_actions': []
            }

    @staticmethod
    def _get_security_recommendations(risk_level: str) -> List[str]:
        """Получение рекомендаций по безопасности"""
        if risk_level == "high":
            return [
                "Временно ограничить крупные транзакции",
                "Требовать дополнительную верификацию",
                "Уведомить службу безопасности",
                "Запросить подтверждение операций"
            ]
        elif risk_level == "medium":
            return [
                "Мониторить активность пользователя",
                "Установить лимиты на транзакции",
                "Отправить уведомление пользователю"
            ]
        else:
            return [
                "Продолжить обычный мониторинг",
                "Периодически проверять активность"
            ]

    @staticmethod
    def log_security_event(user: User, event_type: str, details: Dict[str, Any]) -> bool:
        """Логирование событий безопасности"""
        try:
            # Добавляем событие в лог безопасности пользователя
            if 'security_log' not in user.settings:
                user.settings['security_log'] = []

            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'details': details,
                'user_agent': details.get('user_agent', 'unknown'),
                'ip_address': details.get('ip_address', 'unknown')
            }

            user.settings['security_log'].append(event)

            # Оставляем только последние 100 событий
            user.settings['security_log'] = user.settings['security_log'][-100:]

            return user.save()

        except Exception as e:
            print(f"Ошибка логирования события безопасности: {e}")
            return False


