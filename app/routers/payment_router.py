# app/routers/payment_router.py
"""
Маршрутизатор платежей для Telegram Mini App

Содержит все API эндпоинты для работы с платежами:
- Пополнение баланса
- Вывод средств
- История транзакций
- Интеграция с Telegram Payments
- Эскроу система
"""

import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import and_, or_, desc, func
from app.routers.middleware import (
    require_telegram_auth,
    cache_response,
    rate_limit_decorator
)

# Создание Blueprint для платежей
payment_bp = Blueprint('payments', __name__)

# Константы
MIN_DEPOSIT = 100  # Минимальная сумма пополнения (рубли)
MAX_DEPOSIT = 100000  # Максимальная сумма пополнения
MIN_WITHDRAWAL = 500  # Минимальная сумма вывода
COMMISSION_RATE = 0.05  # Комиссия 5%
ESCROW_HOLD_HOURS = 72  # Время удержания в эскроу (часы)


class PaymentValidator:
    """Класс для валидации платежных данных"""

    @staticmethod
    def validate_amount(amount, min_amount=None, max_amount=None):
        """Валидация суммы платежа"""
        errors = []

        try:
            amount = float(amount)

            if amount <= 0:
                errors.append('Amount must be positive')

            if min_amount and amount < min_amount:
                errors.append(f'Amount must be at least {min_amount}')

            if max_amount and amount > max_amount:
                errors.append(f'Amount cannot exceed {max_amount}')

            # Проверка на разумные дробные части
            decimal_places = str(amount)[::-1].find('.')
            if decimal_places > 2:
                errors.append('Amount cannot have more than 2 decimal places')

        except (ValueError, TypeError):
            errors.append('Invalid amount format')

        return errors

    @staticmethod
    def validate_payment_method(method_data):
        """Валидация метода платежа"""
        errors = []

        if not method_data or not isinstance(method_data, dict):
            errors.append('Payment method data is required')
            return errors

        method_type = method_data.get('type')
        valid_types = ['telegram_payment', 'card', 'wallet', 'bank_transfer']

        if method_type not in valid_types:
            errors.append(f'Invalid payment method. Allowed: {", ".join(valid_types)}')

        # Специфичная валидация для каждого типа
        if method_type == 'card':
            if not method_data.get('card_number'):
                errors.append('Card number is required')
            if not method_data.get('expiry_date'):
                errors.append('Expiry date is required')

        elif method_type == 'wallet':
            if not method_data.get('wallet_address'):
                errors.append('Wallet address is required')

        elif method_type == 'bank_transfer':
            if not method_data.get('account_number'):
                errors.append('Account number is required')
            if not method_data.get('bank_code'):
                errors.append('Bank code is required')

        return errors


class TelegramPaymentService:
    """Сервис для работы с Telegram Payments"""

    @staticmethod
    def create_invoice(amount, description, payload=None):
        """Создание инвойса для Telegram Payments"""
        try:
            import requests

            bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
            payment_token = current_app.config.get('TELEGRAM_PAYMENT_TOKEN')

            if not bot_token or not payment_token:
                current_app.logger.error("Telegram payment tokens not configured")
                return None

            # Данные для создания инвойса
            invoice_data = {
                'chat_id': g.telegram_user_id,
                'title': 'Пополнение баланса',
                'description': description,
                'payload': payload or f"deposit_{g.current_user_id}_{int(time.time())}",
                'provider_token': payment_token,
                'currency': 'RUB',
                'prices': json.dumps([
                    {'label': 'Пополнение баланса', 'amount': int(amount * 100)}  # Сумма в копейках
                ]),
                'start_parameter': 'deposit',
                'protect_content': True
            }

            api_url = f"https://api.telegram.org/bot{bot_token}/sendInvoice"

            response = requests.post(api_url, json=invoice_data, timeout=10)

            if response.status_code == 200:
                result = response.json()
            if result.get('ok'):
                return result.get('result')

            current_app.logger.error(f"Failed to create Telegram invoice: {response.text}")
            return None

        except Exception as e:
            current_app.logger.error(f"Error creating Telegram invoice: {e}")
            return None


@staticmethod
def verify_payment(payment_data):
    """Верификация платежа от Telegram"""
    try:
        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return False

        # Проверяем подпись платежа
        # В реальном приложении здесь должна быть проверка webhook signature

        # Базовая проверка структуры данных
        required_fields = ['total_amount', 'currency', 'invoice_payload']

        for field in required_fields:
            if field not in payment_data:
                current_app.logger.warning(f"Missing required field in payment data: {field}")
                return False

        # Проверяем валюту
        if payment_data.get('currency') != 'RUB':
            current_app.logger.warning(f"Invalid currency: {payment_data.get('currency')}")
            return False

        return True

    except Exception as e:
        current_app.logger.error(f"Error verifying Telegram payment: {e}")
        return False


class EscrowService:
    """Сервис эскроу для безопасных сделок"""

    @staticmethod
    def create_escrow(payer_id, recipient_id, amount, description, related_response_id=None):
        """Создание эскроу транзакции"""
        try:
            from ..models.payment import Payment
            from ..models.user import User
            from ..models.database import db

            # Проверяем баланс плательщика
            payer = User.query.get(payer_id)
            if not payer or payer.balance < amount:
                return None, "Insufficient balance"

            # Создаем эскроу транзакцию
            escrow_payment = Payment(
                user_id=payer_id,
                amount=-amount,  # Списание с баланса
                payment_type='escrow_hold',
                status='pending',
                description=description,
                payment_method={'type': 'escrow'},
                metadata={
                    'recipient_id': recipient_id,
                    'related_response_id': related_response_id,
                    'release_time': (datetime.utcnow() + timedelta(hours=ESCROW_HOLD_HOURS)).isoformat()
                }
            )

            # Обновляем баланс плательщика
            payer.balance -= amount

            db.session.add(escrow_payment)
            db.session.commit()

            current_app.logger.info(
                f"Escrow created: {amount} RUB from user {payer_id} to {recipient_id}"
            )

            return escrow_payment, "Escrow created successfully"

        except Exception as e:
            current_app.logger.error(f"Error creating escrow: {e}")
            db.session.rollback()
            return None, "Failed to create escrow"

    @staticmethod
    def release_escrow(escrow_payment_id, release_to_recipient=True):
        """Освобождение средств из эскроу"""
        try:
            from ..models.payment import Payment
            from ..models.user import User
            from ..models.database import db

            escrow_payment = Payment.query.get(escrow_payment_id)

            if not escrow_payment or escrow_payment.payment_type != 'escrow_hold':
                return False, "Escrow payment not found"

            if escrow_payment.status != 'pending':
                return False, "Escrow already processed"

            amount = abs(escrow_payment.amount)
            metadata = escrow_payment.metadata or {}

            if release_to_recipient:
                # Переводим средства получателю
                recipient_id = metadata.get('recipient_id')
                if recipient_id:
                    recipient = User.query.get(recipient_id)
                    if recipient:
                        recipient.balance += amount

                        # Создаем запись о поступлении средств
                        recipient_payment = Payment(
                            user_id=recipient_id,
                            amount=amount,
                            payment_type='escrow_release',
                            status='completed',
                            description=f"Escrow release: {escrow_payment.description}",
                            payment_method={'type': 'escrow'},
                            metadata={'escrow_payment_id': escrow_payment_id}
                        )

                        db.session.add(recipient_payment)

                escrow_payment.status = 'completed'
                escrow_payment.metadata = {**metadata, 'released_to': 'recipient'}

            else:
                # Возвращаем средства плательщику
                payer = User.query.get(escrow_payment.user_id)
                if payer:
                    payer.balance += amount

                escrow_payment.status = 'cancelled'
                escrow_payment.metadata = {**metadata, 'released_to': 'payer'}

            db.session.commit()

            current_app.logger.info(
                f"Escrow released: {escrow_payment_id}, amount: {amount}, "
                f"to: {'recipient' if release_to_recipient else 'payer'}"
            )

            return True, "Escrow released successfully"

        except Exception as e:
            current_app.logger.error(f"Error releasing escrow: {e}")
            db.session.rollback()
            return False, "Failed to release escrow"


# === API ЭНДПОИНТЫ ===

@payment_bp.route('/balance', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=60)  # Кэшируем на 1 минуту
def get_balance():
    """
    Получение баланса пользователя

    Returns:
        JSON с информацией о балансе
    """
    try:
        from ..models.user import User
        from ..models.payment import Payment
        from ..models.database import db

        user = User.query.get(g.current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Получаем последние транзакции
        recent_transactions = Payment.query.filter_by(
            user_id=user.id
        ).order_by(desc(Payment.created_at)).limit(5).all()

        # Статистика за месяц
        month_ago = datetime.utcnow() - timedelta(days=30)
        monthly_income = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.user_id == user.id,
            Payment.amount > 0,
            Payment.status == 'completed',
            Payment.created_at >= month_ago
        ).scalar() or 0

        monthly_expenses = db.session.query(
            func.sum(Payment.amount)
        ).filter(
            Payment.user_id == user.id,
            Payment.amount < 0,
            Payment.status == 'completed',
            Payment.created_at >= month_ago
        ).scalar() or 0

        return jsonify({
            'balance': {
                'current': user.balance,
                'currency': 'RUB',
                'formatted': f"{user.balance:,.2f} ₽"
            },
            'monthly_stats': {
                'income': abs(monthly_income),
                'expenses': abs(monthly_expenses),
                'net': monthly_income + monthly_expenses  # monthly_expenses уже отрицательные
            },
            'recent_transactions': [
                {
                    'id': transaction.id,
                    'amount': transaction.amount,
                    'type': transaction.payment_type,
                    'status': transaction.status,
                    'description': transaction.description,
                    'created_at': transaction.created_at.isoformat() if transaction.created_at else None
                } for transaction in recent_transactions
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting balance: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/deposit', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=10, window=3600)  # 10 пополнений в час
def create_deposit():
    """
    Создание запроса на пополнение баланса

    Expected JSON:
    {
        "amount": 1000.0,
        "payment_method": {
            "type": "telegram_payment"
        },
        "description": "Пополнение баланса"
    }

    Returns:
        JSON с информацией о платеже
    """
    try:
        from ..models.payment import Payment
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        amount = data.get('amount')
        payment_method = data.get('payment_method', {})
        description = data.get('description', 'Пополнение баланса')

        # Валидация суммы
        amount_errors = PaymentValidator.validate_amount(amount, MIN_DEPOSIT, MAX_DEPOSIT)
        if amount_errors:
            return jsonify({
                'error': 'Invalid amount',
                'details': amount_errors
            }), 400

        # Валидация метода платежа
        method_errors = PaymentValidator.validate_payment_method(payment_method)
        if method_errors:
            return jsonify({
                'error': 'Invalid payment method',
                'details': method_errors
            }), 400

        amount = float(amount)

        # Создаем запись о платеже
        payment = Payment(
            user_id=g.current_user_id,
            amount=amount,
            payment_type='deposit',
            status='pending',
            description=description,
            payment_method=payment_method
        )

        db.session.add(payment)
        db.session.commit()

        # Обрабатываем в зависимости от метода платежа
        if payment_method.get('type') == 'telegram_payment':
            # Создаем Telegram инвойс
            invoice = TelegramPaymentService.create_invoice(
                amount=amount,
                description=description,
                payload=f"deposit_{payment.id}"
            )

            if invoice:
                payment.metadata = {'telegram_invoice': invoice}
                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': 'Invoice created successfully',
                    'payment': {
                        'id': payment.id,
                        'amount': payment.amount,
                        'status': payment.status,
                        'payment_url': f"https://t.me/invoice/{invoice.get('message_id', '')}"
                    },
                    'telegram_invoice': invoice
                }), 201
            else:
                payment.status = 'failed'
                payment.metadata = {'error': 'Failed to create Telegram invoice'}
                db.session.commit()

                return jsonify({
                    'error': 'Failed to create payment invoice'
                }), 500

        else:
            # Для других методов платежа
            return jsonify({
                'success': True,
                'message': 'Payment request created',
                'payment': {
                    'id': payment.id,
                    'amount': payment.amount,
                    'status': payment.status,
                    'next_step': 'Contact support for manual processing'
                }
            }), 201

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating deposit: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/withdraw', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=5, window=3600)  # 5 выводов в час
def create_withdrawal():
    """
    Создание запроса на вывод средств

    Expected JSON:
    {
        "amount": 500.0,
        "payment_method": {
            "type": "card",
            "card_number": "1234567812345678",
            "card_holder": "Ivan Petrov"
        },
        "description": "Вывод средств"
    }

    Returns:
        JSON с информацией о выводе
    """
    try:
        from ..models.payment import Payment
        from ..models.user import User
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        amount = data.get('amount')
        payment_method = data.get('payment_method', {})
        description = data.get('description', 'Вывод средств')

        # Валидация суммы
        amount_errors = PaymentValidator.validate_amount(amount, MIN_WITHDRAWAL)
        if amount_errors:
            return jsonify({
                'error': 'Invalid amount',
                'details': amount_errors
            }), 400

        # Валидация метода платежа
        method_errors = PaymentValidator.validate_payment_method(payment_method)
        if method_errors:
            return jsonify({
                'error': 'Invalid payment method',
                'details': method_errors
            }), 400

        amount = float(amount)

        # Рассчитываем комиссию
        commission = amount * COMMISSION_RATE
        total_deduction = amount + commission

        # Проверяем баланс
        user = User.query.get(g.current_user_id)
        if user.balance < total_deduction:
            return jsonify({
                'error': 'Insufficient balance',
                'available': user.balance,
                'required': total_deduction,
                'commission': commission
            }), 400

        # Создаем запись о выводе
        withdrawal = Payment(
            user_id=g.current_user_id,
            amount=-total_deduction,  # Отрицательная сумма для списания
            payment_type='withdrawal',
            status='pending',
            description=description,
            payment_method=payment_method,
            metadata={
                'withdrawal_amount': amount,
                'commission': commission,
                'total_deduction': total_deduction
            }
        )

        # Резервируем средства (списываем с баланса)
        user.balance -= total_deduction

        db.session.add(withdrawal)
        db.session.commit()

        current_app.logger.info(
            f"Withdrawal created: {amount} RUB (+ {commission} commission) "
            f"by user {g.telegram_user_id}"
        )

        return jsonify({
            'success': True,
            'message': 'Withdrawal request created successfully',
            'withdrawal': {
                'id': withdrawal.id,
                'amount': amount,
                'commission': commission,
                'total_deduction': total_deduction,
                'status': withdrawal.status,
                'processing_time': '1-3 business days'
            }
        }), 201

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating withdrawal: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/webhook/telegram', methods=['POST'])
@rate_limit_decorator(max_requests=100, window=60)  # 100 webhook'ов в минуту
def telegram_payment_webhook():
    """
    Webhook для обработки платежей от Telegram

    Returns:
        JSON с результатом обработки
    """
    try:
        from ..models.payment import Payment
        from ..models.user import User
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Проверяем тип обновления
        if 'pre_checkout_query' in data:
            # Предварительная проверка платежа
            pre_checkout = data['pre_checkout_query']

            # Базовая валидация
            if not TelegramPaymentService.verify_payment(pre_checkout):
                return jsonify({'ok': False, 'error_message': 'Payment verification failed'})

            # Отвечаем положительно
            return jsonify({'ok': True})

        elif 'message' in data and 'successful_payment' in data['message']:
            # Успешный платеж
            successful_payment = data['message']['successful_payment']

            # Извлекаем ID платежа из payload
            payload = successful_payment.get('invoice_payload', '')
            if not payload.startswith('deposit_'):
                current_app.logger.warning(f"Invalid payment payload: {payload}")
                return jsonify({'error': 'Invalid payload'}), 400

            try:
                payment_id = int(payload.split('_')[1])
            except (IndexError, ValueError):
                current_app.logger.warning(f"Cannot extract payment ID from payload: {payload}")
                return jsonify({'error': 'Invalid payload format'}), 400

            # Находим платеж в базе
            payment = Payment.query.get(payment_id)
            if not payment:
                current_app.logger.warning(f"Payment not found: {payment_id}")
                return jsonify({'error': 'Payment not found'}), 404

            if payment.status != 'pending':
                current_app.logger.warning(f"Payment already processed: {payment_id}")
                return jsonify({'error': 'Payment already processed'}), 400

            # Проверяем сумму
            telegram_amount = successful_payment.get('total_amount', 0) / 100  # Конвертируем из копеек
            if abs(telegram_amount - payment.amount) > 0.01:  # Допускаем погрешность в 1 копейку
                current_app.logger.error(
                    f"Amount mismatch: expected {payment.amount}, got {telegram_amount}"
                )
                return jsonify({'error': 'Amount mismatch'}), 400

            # Обновляем платеж и баланс пользователя
            user = User.query.get(payment.user_id)
            if user:
                user.balance += payment.amount
                payment.status = 'completed'
                payment.metadata = {
                    **(payment.metadata or {}),
                    'telegram_payment': successful_payment,
                    'processed_at': datetime.utcnow().isoformat()
                }

                db.session.commit()

                current_app.logger.info(
                    f"Payment processed successfully: {payment_id}, "
                    f"amount: {payment.amount}, user: {user.telegram_id}"
                )

                return jsonify({'success': True, 'message': 'Payment processed'})
            else:
                current_app.logger.error(f"User not found for payment: {payment_id}")
                return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'Webhook received'})

    except Exception as e:
        current_app.logger.error(f"Error processing Telegram webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/transactions', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=120)  # Кэшируем на 2 минуты
def get_transactions():
    """
    Получение истории транзакций пользователя

    Query params:
    - page: номер страницы (по умолчанию 1)
    - limit: количество на странице (по умолчанию 20, макс 100)
    - type: фильтр по типу (deposit, withdrawal, escrow_hold, escrow_release)
    - status: фильтр по статусу (pending, completed, failed, cancelled)
    - period: период (7d, 30d, 90d, 1y)

    Returns:
        JSON с историей транзакций
    """
    try:
        from ..models.payment import Payment
        from ..models.database import db

        # Параметры пагинации
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фильтры
        payment_type = request.args.get('type')
        status = request.args.get('status')
        period = request.args.get('period')

        # Базовый запрос
        query = Payment.query.filter_by(user_id=g.current_user_id)

        # Применяем фильтры
        if payment_type:
            query = query.filter(Payment.payment_type == payment_type)

        if status:
            query = query.filter(Payment.status == status)

        if period:
            from ..routers.analytics_router import AnalyticsService
            start_date, end_date = AnalyticsService.get_date_range(period)
            query = query.filter(
                Payment.created_at >= start_date,
                Payment.created_at <= end_date
            )

        # Получаем общее количество
        total_count = query.count()

        # Получаем транзакции с пагинацией
        transactions = query.order_by(desc(Payment.created_at)).offset(offset).limit(limit).all()

        # Формируем ответ
        transactions_data = []
        for transaction in transactions:
            transaction_data = {
                'id': transaction.id,
                'amount': transaction.amount,
                'payment_type': transaction.payment_type,
                'status': transaction.status,
                'description': transaction.description,
                'payment_method': transaction.payment_method,
                'created_at': transaction.created_at.isoformat() if transaction.created_at else None
            }

            # Добавляем специфичную информацию для разных типов
            if transaction.payment_type == 'withdrawal' and transaction.metadata:
                metadata = transaction.metadata
                transaction_data['withdrawal_details'] = {
                    'withdrawal_amount': metadata.get('withdrawal_amount'),
                    'commission': metadata.get('commission'),
                    'total_deduction': metadata.get('total_deduction')
                }

            elif transaction.payment_type in ['escrow_hold', 'escrow_release'] and transaction.metadata:
                metadata = transaction.metadata
                transaction_data['escrow_details'] = {
                    'recipient_id': metadata.get('recipient_id'),
                    'related_response_id': metadata.get('related_response_id'),
                    'release_time': metadata.get('release_time'),
                    'released_to': metadata.get('released_to')
                }

            transactions_data.append(transaction_data)

        # Статистика по типам транзакций
        type_stats = db.session.query(
            Payment.payment_type,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('total_amount')
        ).filter_by(user_id=g.current_user_id).group_by(Payment.payment_type).all()

        return jsonify({
            'transactions': transactions_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit,
                'has_next': offset + limit < total_count,
                'has_prev': page > 1
            },
            'statistics': {
                'by_type': [
                    {
                        'type': stat.payment_type,
                        'count': stat.count,
                        'total_amount': float(stat.total_amount or 0)
                    } for stat in type_stats
                ]
            }
        })

    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter value',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error getting transactions: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/escrow', methods=['POST'])
@require_telegram_auth
@rate_limit_decorator(max_requests=20, window=3600)  # 20 эскроу в час
def create_escrow():
    """
    Создание эскроу транзакции

    Expected JSON:
    {
        "recipient_id": 123,
        "amount": 500.0,
        "description": "Оплата за размещение рекламы",
        "response_id": 456
    }

    Returns:
        JSON с информацией об эскроу
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        recipient_id = data.get('recipient_id')
        amount = data.get('amount')
        description = data.get('description', 'Эскроу платеж')
        response_id = data.get('response_id')

        if not recipient_id:
            return jsonify({'error': 'Recipient ID is required'}), 400

        # Валидация суммы
        amount_errors = PaymentValidator.validate_amount(amount)
        if amount_errors:
            return jsonify({
                'error': 'Invalid amount',
                'details': amount_errors
            }), 400

        amount = float(amount)

        # Проверяем, что получатель существует
        from ..models.user import User
        recipient = User.query.get(recipient_id)
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404

        # Создаем эскроу
        escrow_payment, message = EscrowService.create_escrow(
            payer_id=g.current_user_id,
            recipient_id=recipient_id,
            amount=amount,
            description=description,
            related_response_id=response_id
        )

        if not escrow_payment:
            return jsonify({'error': message}), 400

        return jsonify({
            'success': True,
            'message': message,
            'escrow': {
                'id': escrow_payment.id,
                'amount': amount,
                'status': escrow_payment.status,
                'description': description,
                'recipient': {
                    'id': recipient.id,
                    'username': recipient.username,
                    'first_name': recipient.first_name
                },
                'hold_until': escrow_payment.metadata.get('release_time'),
                'created_at': escrow_payment.created_at.isoformat() if escrow_payment.created_at else None
            }
        }), 201

    except ValueError as e:
        return jsonify({
            'error': 'Invalid data format',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating escrow: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/escrow/<int:escrow_id>/release', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=30, window=3600)  # 30 действий в час
def release_escrow(escrow_id):
    """
    Освобождение средств из эскроу

    Args:
        escrow_id: ID эскроу транзакции

    Expected JSON:
    {
        "action": "release" | "cancel",
        "reason": "Работа выполнена успешно"
    }

    Returns:
        JSON с результатом операции
    """
    try:
        from ..models.payment import Payment
        from ..models.database import db

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        action = data.get('action')
        reason = data.get('reason', '')

        if action not in ['release', 'cancel']:
            return jsonify({'error': 'Invalid action. Must be "release" or "cancel"'}), 400

        # Находим эскроу транзакцию
        escrow_payment = Payment.query.get(escrow_id)

        if not escrow_payment:
            return jsonify({'error': 'Escrow not found'}), 404

        if escrow_payment.payment_type != 'escrow_hold':
            return jsonify({'error': 'Not an escrow transaction'}), 400

        # Проверяем права доступа
        metadata = escrow_payment.metadata or {}
        recipient_id = metadata.get('recipient_id')

        # Только плательщик или получатель могут управлять эскроу
        if escrow_payment.user_id != g.current_user_id and recipient_id != g.current_user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Логика освобождения средств
        release_to_recipient = action == 'release'

        # Если плательщик хочет отменить - средства возвращаются ему
        # Если получатель хочет отменить - средства возвращаются плательщику
        # Если любой из них хочет подтвердить - средства идут получателю
        if escrow_payment.user_id == g.current_user_id and action == 'cancel':
            release_to_recipient = False  # Плательщик отменяет - возврат ему
        elif recipient_id == g.current_user_id and action == 'cancel':
            release_to_recipient = False  # Получатель отменяет - возврат плательщику

        # Освобождаем эскроу
        success, message = EscrowService.release_escrow(escrow_id, release_to_recipient)

        if not success:
            return jsonify({'error': message}), 400

        # Обновляем причину в метаданных
        if reason:
            escrow_payment.metadata = {
                **(escrow_payment.metadata or {}),
                'release_reason': reason,
                'released_by': g.current_user_id
            }
            db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'escrow': {
                'id': escrow_payment.id,
                'status': escrow_payment.status,
                'amount': abs(escrow_payment.amount),
                'released_to': 'recipient' if release_to_recipient else 'payer',
                'reason': reason
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error releasing escrow: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/stats', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=300)  # Кэшируем на 5 минут
def get_payment_stats():
    """
    Получение статистики платежей пользователя

    Query params:
    - period: период анализа (7d, 30d, 90d, 1y)

    Returns:
        JSON со статистикой платежей
    """
    try:
        from ..models.payment import Payment
        from ..models.database import db

        period = request.args.get('period', '30d')

        # Получаем диапазон дат
        from ..routers.analytics_router import AnalyticsService
        start_date, end_date = AnalyticsService.get_date_range(period)

        # Базовая статистика за период
        period_transactions = Payment.query.filter(
            Payment.user_id == g.current_user_id,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        )

        # Группировка по типам
        type_stats = db.session.query(
            Payment.payment_type,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('total_amount'),
            func.avg(Payment.amount).label('avg_amount')
        ).filter(
            Payment.user_id == g.current_user_id,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).group_by(Payment.payment_type).all()

        # Группировка по статусам
        status_stats = db.session.query(
            Payment.status,
            func.count(Payment.id).label('count'),
            func.sum(Payment.amount).label('total_amount')
        ).filter(
            Payment.user_id == g.current_user_id,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).group_by(Payment.status).all()

        # Временные ряды (по дням)
        daily_stats = db.session.query(
            func.date(Payment.created_at).label('date'),
            func.count(Payment.id).label('transactions'),
            func.sum(func.case((Payment.amount > 0, Payment.amount), else_=0)).label('income'),
            func.sum(func.case((Payment.amount < 0, Payment.amount), else_=0)).label('expenses')
        ).filter(
            Payment.user_id == g.current_user_id,
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).group_by(func.date(Payment.created_at)).order_by('date').all()

        # Общие суммы
        total_income = sum(stat.total_amount for stat in type_stats if stat.total_amount and stat.total_amount > 0) or 0
        total_expenses = abs(
            sum(stat.total_amount for stat in type_stats if stat.total_amount and stat.total_amount < 0)) or 0

        return jsonify({
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'name': period
            },
            'summary': {
                'total_transactions': sum(stat.count for stat in type_stats),
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_amount': total_income - total_expenses
            },
            'by_type': [
                {
                    'type': stat.payment_type,
                    'count': stat.count,
                    'total_amount': float(stat.total_amount or 0),
                    'avg_amount': round(float(stat.avg_amount or 0), 2)
                } for stat in type_stats
            ],
            'by_status': [
                {
                    'status': stat.status,
                    'count': stat.count,
                    'total_amount': float(stat.total_amount or 0)
                } for stat in status_stats
            ],
            'daily_timeline': [
                {
                    'date': day.date.isoformat(),
                    'transactions': day.transactions,
                    'income': float(day.income or 0),
                    'expenses': abs(float(day.expenses or 0))
                } for day in daily_stats
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting payment stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/methods', methods=['GET'])
@require_telegram_auth
@cache_response(timeout=600)  # Кэшируем на 10 минут
def get_payment_methods():
    """
    Получение доступных методов платежа

    Returns:
        JSON с методами платежа
    """
    try:
        # Получаем конфигурацию платежных методов
        telegram_payments_enabled = bool(current_app.config.get('TELEGRAM_PAYMENT_TOKEN'))

        methods = {
            'deposit_methods': [
                {
                    'type': 'telegram_payment',
                    'name': 'Telegram Payments',
                    'description': 'Оплата через Telegram (карты, кошельки)',
                    'enabled': telegram_payments_enabled,
                    'min_amount': MIN_DEPOSIT,
                    'max_amount': MAX_DEPOSIT,
                    'commission': 0,
                    'processing_time': 'Мгновенно'
                }
            ],
            'withdrawal_methods': [
                {
                    'type': 'card',
                    'name': 'Банковская карта',
                    'description': 'Вывод на банковскую карту',
                    'enabled': True,
                    'min_amount': MIN_WITHDRAWAL,
                    'max_amount': 50000,
                    'commission_rate': COMMISSION_RATE,
                    'processing_time': '1-3 рабочих дня'
                },
                {
                    'type': 'wallet',
                    'name': 'Электронный кошелек',
                    'description': 'Вывод на электронный кошелек',
                    'enabled': True,
                    'min_amount': MIN_WITHDRAWAL,
                    'max_amount': 30000,
                    'commission_rate': COMMISSION_RATE,
                    'processing_time': '1-2 рабочих дня'
                },
                {
                    'type': 'bank_transfer',
                    'name': 'Банковский перевод',
                    'description': 'Перевод на банковский счет',
                    'enabled': True,
                    'min_amount': MIN_WITHDRAWAL,
                    'max_amount': 100000,
                    'commission_rate': COMMISSION_RATE,
                    'processing_time': '2-5 рабочих дней'
                }
            ]
        }

        return jsonify({
            'methods': methods,
            'limits': {
                'min_deposit': MIN_DEPOSIT,
                'max_deposit': MAX_DEPOSIT,
                'min_withdrawal': MIN_WITHDRAWAL,
                'commission_rate': COMMISSION_RATE,
                'escrow_hold_hours': ESCROW_HOLD_HOURS
            },
            'currencies': ['RUB'],
            'features': {
                'escrow_enabled': True,
                'telegram_payments': telegram_payments_enabled,
                'auto_withdrawal': False  # Ручная обработка выводов
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting payment methods: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@payment_bp.route('/pending', methods=['GET'])
@require_telegram_auth
def get_pending_payments():
    """
    Получение ожидающих платежей и эскроу

    Returns:
        JSON с ожидающими операциями
    """
    try:
        from ..models.payment import Payment

        # Ожидающие депозиты
        pending_deposits = Payment.query.filter(
            Payment.user_id == g.current_user_id,
            Payment.payment_type == 'deposit',
            Payment.status == 'pending'
        ).order_by(desc(Payment.created_at)).all()

        # Ожидающие выводы
        pending_withdrawals = Payment.query.filter(
            Payment.user_id == g.current_user_id,
            Payment.payment_type == 'withdrawal',
            Payment.status == 'pending'
        ).order_by(desc(Payment.created_at)).all()

        # Активные эскроу (исходящие)
        outgoing_escrow = Payment.query.filter(
            Payment.user_id == g.current_user_id,
            Payment.payment_type == 'escrow_hold',
            Payment.status == 'pending'
        ).order_by(desc(Payment.created_at)).all()

        # Входящие эскроу (где текущий пользователь - получатель)
        incoming_escrow = Payment.query.filter(
            Payment.payment_type == 'escrow_hold',
            Payment.status == 'pending'
        ).all()

        # Фильтруем входящие эскроу по получателю
        user_incoming_escrow = []
        for escrow in incoming_escrow:
            metadata = escrow.metadata or {}
            if metadata.get('recipient_id') == g.current_user_id:
                user_incoming_escrow.append(escrow)

        # Форматируем данные
        def format_payment(payment):
            data = {
                'id': payment.id,
                'amount': payment.amount,
                'status': payment.status,
                'description': payment.description,
                'created_at': payment.created_at.isoformat() if payment.created_at else None
            }

            if payment.payment_type == 'escrow_hold' and payment.metadata:
                metadata = payment.metadata
                data['escrow_details'] = {
                    'recipient_id': metadata.get('recipient_id'),
                    'release_time': metadata.get('release_time'),
                    'related_response_id': metadata.get('related_response_id')
                }

            return data

        return jsonify({
            'pending_deposits': [format_payment(p) for p in pending_deposits],
            'pending_withdrawals': [format_payment(p) for p in pending_withdrawals],
            'outgoing_escrow': [format_payment(p) for p in outgoing_escrow],
            'incoming_escrow': [format_payment(p) for p in user_incoming_escrow],
            'summary': {
                'total_pending': len(pending_deposits) + len(pending_withdrawals) + len(outgoing_escrow) + len(
                    user_incoming_escrow),
                'pending_deposits_count': len(pending_deposits),
                'pending_withdrawals_count': len(pending_withdrawals),
                'outgoing_escrow_count': len(outgoing_escrow),
                'incoming_escrow_count': len(user_incoming_escrow)
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting pending payments: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# === АДМИНИСТРАТИВНЫЕ ЭНДПОИНТЫ ===

@payment_bp.route('/admin/process-withdrawal/<int:withdrawal_id>', methods=['PUT'])
@require_telegram_auth
@rate_limit_decorator(max_requests=50, window=3600)  # Для админов
def process_withdrawal(withdrawal_id):
    """
    Обработка вывода средств (административный эндпоинт)

    Args:
        withdrawal_id: ID заявки на вывод

    Expected JSON:
    {
        "action": "approve" | "reject",
        "comment": "Комментарий администратора"
    }

    Returns:
        JSON с результатом обработки
    """
    try:
        from ..models.payment import Payment
        from ..models.user import User
        from ..models.database import db

        # Проверяем админские права (упрощенная проверка)
        admin_user = User.query.get(g.current_user_id)
        if not admin_user or admin_user.user_type != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        action = data.get('action')
        comment = data.get('comment', '')

        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400

        # Находим заявку на вывод
        withdrawal = Payment.query.get(withdrawal_id)

        if not withdrawal:
            return jsonify({'error': 'Withdrawal not found'}), 404

        if withdrawal.payment_type != 'withdrawal':
            return jsonify({'error': 'Not a withdrawal'}), 400

        if withdrawal.status != 'pending':
            return jsonify({'error': 'Withdrawal already processed'}), 400

        if action == 'approve':
            # Одобряем вывод
            withdrawal.status = 'completed'
            withdrawal.metadata = {
                **(withdrawal.metadata or {}),
                'processed_by': admin_user.id,
                'processed_at': datetime.utcnow().isoformat(),
                'admin_comment': comment
            }

        else:  # reject
            # Отклоняем вывод и возвращаем средства
            user = User.query.get(withdrawal.user_id)
            if user:
                # Возвращаем списанные средства
                returned_amount = abs(withdrawal.amount)
                user.balance += returned_amount

            withdrawal.status = 'rejected'
            withdrawal.metadata = {
                **(withdrawal.metadata or {}),
                'processed_by': admin_user.id,
                'processed_at': datetime.utcnow().isoformat(),
                'admin_comment': comment,
                'returned_amount': returned_amount
            }

        db.session.commit()

        current_app.logger.info(
            f"Withdrawal {withdrawal_id} {action}ed by admin {admin_user.telegram_id}"
        )

        return jsonify({
            'success': True,
            'message': f'Withdrawal {action}ed successfully',
            'withdrawal': {
                'id': withdrawal.id,
                'status': withdrawal.status,
                'processed_by': admin_user.username,
                'comment': comment
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error processing withdrawal: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# === ОБРАБОТЧИКИ ОШИБОК ===

@payment_bp.errorhandler(404)
def payment_not_found(error):
    """Обработчик 404 ошибок для платежей"""
    return jsonify({
        'error': 'Payment endpoint not found',
        'message': 'The requested payment endpoint does not exist'
    }), 404


@payment_bp.errorhandler(403)
def payment_access_denied(error):
    """Обработчик 403 ошибок для платежей"""
    return jsonify({
        'error': 'Access denied',
        'message': 'You do not have permission to access this payment resource'
    }), 403


@payment_bp.errorhandler(429)
def payment_rate_limit_exceeded(error):
    """Обработчик превышения rate limit для платежей"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many payment requests. Please try again later.'
    }), 429


# Автоматическое освобождение эскроу (фоновая задача)
def auto_release_expired_escrow():
    """
    Автоматическое освобождение просроченных эскроу
    Эта функция должна вызываться периодически (например, через cron)
    """
    try:
        from ..models.payment import Payment

        # Находим просроченные эскроу
        current_time = datetime.utcnow()

        expired_escrow = Payment.query.filter(
            Payment.payment_type == 'escrow_hold',
            Payment.status == 'pending'
        ).all()

        for escrow in expired_escrow:
            metadata = escrow.metadata or {}
            release_time_str = metadata.get('release_time')

            if release_time_str:
                try:
                    release_time = datetime.fromisoformat(release_time_str.replace('Z', '+00:00'))

                    if current_time >= release_time:
                        # Автоматически освобождаем в пользу получателя
                        success, message = EscrowService.release_escrow(escrow.id, True)

                        if success:
                            current_app.logger.info(
                                f"Auto-released expired escrow: {escrow.id}"
                            )
                        else:
                            current_app.logger.error(
                                f"Failed to auto-release escrow {escrow.id}: {message}"
                            )

                except ValueError as e:
                    current_app.logger.error(f"Invalid release time format: {e}")

    except Exception as e:
        current_app.logger.error(f"Error in auto escrow release: {e}")


# Инициализация Blueprint
def init_payment_routes():
    """Инициализация маршрутов платежей"""
    current_app.logger.info("✅ Payment routes initialized")


# Экспорт
__all__ = [
    'payment_bp',
    'init_payment_routes',
    'PaymentValidator',
    'TelegramPaymentService',
    'EscrowService',
    'auto_release_expired_escrow'
]