#!/usr/bin/env python3
"""
Telegram Payments Integration
Полная интеграция с Telegram Payments API для обработки платежей
"""

import json
import hmac
import hashlib
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from app.config.telegram_config import AppConfig
from app.models.database import execute_db_query
from app.events.event_dispatcher import event_dispatcher

logger = logging.getLogger(__name__)

class TelegramPaymentProcessor:
    """Обработчик платежей через Telegram Payments API"""
    
    def __init__(self):
        self.bot_token = AppConfig.BOT_TOKEN
        self.payment_token = AppConfig.TELEGRAM_PAYMENT_TOKEN
        self.webhook_secret = AppConfig.WEBHOOK_SECRET
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Поддерживаемые валюты
        self.supported_currencies = {
            'RUB': {'min_amount': 100, 'max_amount': 100000},
            'USD': {'min_amount': 1, 'max_amount': 1000},
            'EUR': {'min_amount': 1, 'max_amount': 1000}
        }
        
        # Комиссии платежных систем
        self.payment_fees = {
            'telegram_payments': 0.029,  # 2.9%
            'bank_card': 0.035,          # 3.5%
            'yoomoney': 0.025,           # 2.5%
            'sberbank': 0.02             # 2%
        }
    
    def create_invoice(self, user_id: int, amount: Decimal, currency: str = 'RUB',
                      title: str = None, description: str = None, 
                      payload: str = None, offer_id: int = None) -> Dict[str, Any]:
        """Создание инвойса для пополнения баланса"""
        try:
            # Валидация суммы
            if not self._validate_amount(amount, currency):
                raise ValueError(f"Недопустимая сумма {amount} {currency}")
            
            # Подготовка данных
            invoice_data = {
                'chat_id': user_id,
                'title': title or 'Пополнение баланса',
                'description': description or f'Пополнение баланса на {amount} {currency}',
                'payload': payload or f'topup_{user_id}_{int(datetime.now().timestamp())}',
                'provider_token': self.payment_token,
                'currency': currency,
                'prices': [{'label': 'Пополнение', 'amount': int(amount * 100)}],  # В копейках
                'start_parameter': f'invoice_{user_id}',
                'photo_url': 'https://your-domain.com/static/img/payment_logo.png',
                'photo_size': 512,
                'photo_width': 512,
                'photo_height': 512,
                'need_name': False,
                'need_phone_number': False,
                'need_email': False,
                'need_shipping_address': False,
                'send_phone_number_to_provider': False,
                'send_email_to_provider': False,
                'is_flexible': False
            }
            
            # Отправка запроса в Telegram API
            response = requests.post(
                f"{self.base_url}/sendInvoice",
                json=invoice_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    # Сохраняем инвойс в базу данных
                    invoice_id = self._save_invoice(
                        user_id=user_id,
                        amount=amount,
                        currency=currency,
                        payload=invoice_data['payload'],
                        offer_id=offer_id,
                        telegram_message_id=result['result']['message_id']
                    )
                    
                    # Отправляем событие
                    event_dispatcher.payment_created(
                        payment_id=invoice_id,
                        user_id=user_id,
                        amount=float(amount),
                        payment_type='deposit',
                        status='pending',
                        provider='telegram_payments'
                    )
                    
                    logger.info(f"✅ Создан инвойс {invoice_id} для пользователя {user_id}")
                    
                    return {
                        'success': True,
                        'invoice_id': invoice_id,
                        'telegram_message_id': result['result']['message_id'],
                        'payload': invoice_data['payload']
                    }
                else:
                    logger.error(f"❌ Telegram API ошибка: {result}")
                    return {'success': False, 'error': result.get('description', 'Unknown error')}
            else:
                logger.error(f"❌ HTTP ошибка: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания инвойса: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_successful_payment(self, pre_checkout_query: Dict[str, Any]) -> bool:
        """Обработка успешного платежа (pre-checkout)"""
        try:
            query_id = pre_checkout_query['id']
            payload = pre_checkout_query['invoice_payload']
            
            # Валидация payload
            if not self._validate_payload(payload):
                self._answer_pre_checkout_query(query_id, False, "Недействительный платеж")
                return False
            
            # Подтверждаем платеж
            self._answer_pre_checkout_query(query_id, True)
            
            logger.info(f"✅ Pre-checkout подтвержден для payload {payload}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка pre-checkout: {e}")
            return False
    
    def finalize_payment(self, successful_payment: Dict[str, Any], user_id: int) -> bool:
        """Финализация успешного платежа"""
        try:
            payload = successful_payment['invoice_payload']
            telegram_payment_charge_id = successful_payment['telegram_payment_charge_id']
            provider_payment_charge_id = successful_payment['provider_payment_charge_id']
            total_amount = Decimal(successful_payment['total_amount']) / 100  # Из копеек
            currency = successful_payment['currency']
            
            # Находим инвойс в базе данных
            invoice = execute_db_query(
                "SELECT * FROM payments WHERE payload = ? AND status = 'pending'",
                (payload,),
                fetch_one=True
            )
            
            if not invoice:
                logger.error(f"❌ Инвойс не найден для payload {payload}")
                return False
            
            # Обновляем статус платежа
            execute_db_query(
                """UPDATE payments SET 
                   status = 'completed',
                   provider_payment_id = ?,
                   telegram_payment_id = ?,
                   processed_at = ?,
                   updated_at = ?
                   WHERE id = ?""",
                (
                    provider_payment_charge_id,
                    telegram_payment_charge_id,
                    datetime.now(),
                    datetime.now(),
                    invoice['id']
                )
            )
            
            # Обновляем баланс пользователя
            self._update_user_balance(user_id, total_amount, 'deposit')
            
            # Отправляем события
            event_dispatcher.payment_processed(
                payment_id=invoice['id'],
                user_id=user_id,
                amount=float(total_amount),
                payment_type='deposit',
                status='completed'
            )
            
            event_dispatcher.user_balance_changed(
                user_id=user_id,
                telegram_id=user_id,  # В данном случае совпадают
                old_balance=0,  # Получим из БД отдельно если нужно
                new_balance=float(total_amount),  # Новый баланс получим из БД
                change_type='deposit',
                description=f'Пополнение через Telegram Payments'
            )
            
            logger.info(f"✅ Платеж {invoice['id']} успешно обработан")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка финализации платежа: {e}")
            return False
    
    def create_withdrawal_request(self, user_id: int, amount: Decimal, 
                                payment_method: str, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Создание запроса на вывод средств"""
        try:
            # Проверяем баланс пользователя
            user_balance = self._get_user_balance(user_id)
            if user_balance < amount:
                return {'success': False, 'error': 'Недостаточно средств'}
            
            # Проверяем минимальную сумму вывода
            if amount < AppConfig.MIN_BALANCE_WITHDRAWAL:
                return {
                    'success': False, 
                    'error': f'Минимальная сумма вывода {AppConfig.MIN_BALANCE_WITHDRAWAL} руб.'
                }
            
            # Создаем запрос на вывод
            withdrawal_id = execute_db_query(
                """INSERT INTO payments 
                   (user_id, amount, currency, payment_type, status, provider, 
                    description, payment_details, created_at, updated_at)
                   VALUES (?, ?, 'RUB', 'withdrawal', 'pending', ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    float(amount),
                    payment_method,
                    f'Вывод средств через {payment_method}',
                    json.dumps(payment_details),
                    datetime.now(),
                    datetime.now()
                )
            )
            
            # Блокируем средства на балансе
            self._update_user_balance(user_id, -amount, 'withdrawal_hold')
            
            # Отправляем событие
            event_dispatcher.payment_created(
                payment_id=withdrawal_id,
                user_id=user_id,
                amount=float(amount),
                payment_type='withdrawal',
                status='pending'
            )
            
            logger.info(f"✅ Создан запрос на вывод {withdrawal_id} для пользователя {user_id}")
            
            return {
                'success': True,
                'withdrawal_id': withdrawal_id,
                'amount': float(amount),
                'status': 'pending'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания запроса на вывод: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_withdrawal(self, withdrawal_id: int, admin_user_id: int) -> Dict[str, Any]:
        """Обработка запроса на вывод средств (для админов)"""
        try:
            # Получаем данные о выводе
            withdrawal = execute_db_query(
                "SELECT * FROM payments WHERE id = ? AND payment_type = 'withdrawal'",
                (withdrawal_id,),
                fetch_one=True
            )
            
            if not withdrawal:
                return {'success': False, 'error': 'Запрос на вывод не найден'}
            
            if withdrawal['status'] != 'pending':
                return {'success': False, 'error': 'Запрос уже обработан'}
            
            # Здесь должна быть интеграция с реальной платежной системой
            # Для демонстрации просто меняем статус
            
            execute_db_query(
                """UPDATE payments SET 
                   status = 'completed',
                   processed_at = ?,
                   updated_at = ?,
                   admin_notes = ?
                   WHERE id = ?""",
                (
                    datetime.now(),
                    datetime.now(),
                    f'Обработано администратором {admin_user_id}',
                    withdrawal_id
                )
            )
            
            # Отправляем события
            event_dispatcher.payment_processed(
                payment_id=withdrawal_id,
                user_id=withdrawal['user_id'],
                amount=withdrawal['amount'],
                payment_type='withdrawal',
                status='completed'
            )
            
            logger.info(f"✅ Вывод {withdrawal_id} обработан администратором {admin_user_id}")
            
            return {
                'success': True,
                'withdrawal_id': withdrawal_id,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки вывода: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение истории платежей пользователя"""
        try:
            payments = execute_db_query(
                """SELECT id, amount, currency, payment_type, status, provider,
                          description, created_at, processed_at
                   FROM payments 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (user_id, limit)
            )
            
            return [dict(payment) for payment in payments]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории платежей: {e}")
            return []
    
    def _validate_amount(self, amount: Decimal, currency: str) -> bool:
        """Валидация суммы платежа"""
        if currency not in self.supported_currencies:
            return False
        
        limits = self.supported_currencies[currency]
        return limits['min_amount'] <= amount <= limits['max_amount']
    
    def _validate_payload(self, payload: str) -> bool:
        """Валидация payload платежа"""
        try:
            # Проверяем формат payload
            if not payload.startswith('topup_'):
                return False
            
            parts = payload.split('_')
            if len(parts) != 3:
                return False
            
            user_id = int(parts[1])
            timestamp = int(parts[2])
            
            # Проверяем, что payload не старше 1 часа
            if datetime.now().timestamp() - timestamp > 3600:
                return False
            
            return True
            
        except (ValueError, IndexError):
            return False
    
    def _answer_pre_checkout_query(self, query_id: str, ok: bool, error_message: str = None):
        """Ответ на pre-checkout query"""
        try:
            data = {'pre_checkout_query_id': query_id, 'ok': ok}
            if not ok and error_message:
                data['error_message'] = error_message
            
            requests.post(
                f"{self.base_url}/answerPreCheckoutQuery",
                json=data,
                timeout=10
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка ответа на pre-checkout: {e}")
    
    def _save_invoice(self, user_id: int, amount: Decimal, currency: str, 
                     payload: str, offer_id: int = None, telegram_message_id: int = None) -> int:
        """Сохранение инвойса в базу данных"""
        return execute_db_query(
            """INSERT INTO payments 
               (user_id, offer_id, amount, currency, payment_type, status, provider,
                description, payload, telegram_message_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'deposit', 'pending', 'telegram_payments', ?, ?, ?, ?, ?)""",
            (
                user_id,
                offer_id,
                float(amount),
                currency,
                f'Пополнение баланса на {amount} {currency}',
                payload,
                telegram_message_id,
                datetime.now(),
                datetime.now()
            )
        )
    
    def _get_user_balance(self, user_id: int) -> Decimal:
        """Получение баланса пользователя"""
        user = execute_db_query(
            "SELECT balance FROM users WHERE telegram_id = ?",
            (user_id,),
            fetch_one=True
        )
        return Decimal(str(user['balance'])) if user else Decimal('0')
    
    def _update_user_balance(self, user_id: int, amount: Decimal, operation_type: str):
        """Обновление баланса пользователя"""
        if operation_type == 'deposit':
            execute_db_query(
                "UPDATE users SET balance = balance + ?, updated_at = ? WHERE telegram_id = ?",
                (float(amount), datetime.now(), user_id)
            )
        elif operation_type == 'withdrawal_hold':
            execute_db_query(
                "UPDATE users SET balance = balance - ?, updated_at = ? WHERE telegram_id = ?",
                (float(abs(amount)), datetime.now(), user_id)
            )
    
    def calculate_fee(self, amount: Decimal, provider: str = 'telegram_payments') -> Decimal:
        """Расчет комиссии платежной системы"""
        fee_rate = self.payment_fees.get(provider, 0.029)
        return amount * Decimal(str(fee_rate))