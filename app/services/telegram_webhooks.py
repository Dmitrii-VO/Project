# telegram_webhooks.py - Обработка webhook'ов от Telegram
import os
import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')

# Создаем Blueprint для webhook'ов
webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')

# Импорт системы платежей
try:
    from payments_system import TelegramPayments, PaymentManager, EscrowManager
    PAYMENTS_AVAILABLE = True
except ImportError:
    logger.error("❌ Модуль платежей недоступен")
    PAYMENTS_AVAILABLE = False

# Импорт системы уведомлений
try:
    from notifications_system import NotificationManager
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    logger.error("❌ Модуль уведомлений недоступен")
    NOTIFICATIONS_AVAILABLE = False

class TelegramWebhookHandler:
    """Обработчик webhook'ов от Telegram"""
    
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.payment_manager = PaymentManager() if PAYMENTS_AVAILABLE else None
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
        """Отправка сообщения пользователю"""
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/sendMessage",
                    json=payload
                ) as response:
                    result = await response.json()
                    return result.get('ok', False)
                    
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def process_successful_payment(self, update_data: Dict) -> Dict:
        """Обработка успешного платежа"""
        try:
            message = update_data.get('message', {})
            successful_payment = message.get('successful_payment', {})
            user = message.get('from', {})
            
            if not successful_payment:
                return {'success': False, 'error': 'Нет данных о платеже'}
            
            logger.info(f"Обработка платежа от пользователя {user.get('id')}: {successful_payment}")
            
            # Обрабатываем платеж через платежную систему
            if PAYMENTS_AVAILABLE and self.payment_manager:
                telegram_payments = TelegramPayments()
                result = await telegram_payments.process_successful_payment(successful_payment)
                
                if result['success']:
                    # Отправляем уведомление об успешном платеже
                    await self.send_payment_confirmation(
                        user.get('id'),
                        result['payment_id'],
                        result['amount']
                    )
                    
                    # Создаем уведомление в системе
                    if NOTIFICATIONS_AVAILABLE:
                        NotificationManager.create_notification(
                            user_id=user.get('id'),
                            notification_type='payment_success',
                            title='💰 Платеж получен',
                            message=f'Платеж на сумму ₽{result["amount"]} успешно обработан',
                            data={'payment_id': result['payment_id'], 'amount': result['amount']}
                        )
                    
                    return result
                else:
                    # Отправляем уведомление об ошибке
                    await self.send_message(
                        user.get('id'),
                        f"❌ <b>Ошибка обработки платежа</b>\\n\\n{result.get('error', 'Неизвестная ошибка')}"
                    )
                    return result
            else:
                return {'success': False, 'error': 'Платежная система недоступна'}
                
        except Exception as e:
            logger.error(f"Ошибка обработки платежа: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_payment_confirmation(self, user_id: int, payment_id: int, amount: float):
        """Отправка подтверждения о платеже"""
        try:
            message_text = f"""
✅ <b>Платеж успешно получен!</b>

💰 <b>Сумма:</b> ₽{amount}
🆔 <b>ID платежа:</b> {payment_id}
🕐 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔒 <b>Средства помещены в эскроу</b>
Они будут переданы исполнителю после выполнения заказа.

📱 <b>Следить за статусом можно в приложении</b>
            """
            
            await self.send_message(user_id, message_text.strip())
            
        except Exception as e:
            logger.error(f"Ошибка отправки подтверждения: {e}")
    
    async def process_pre_checkout_query(self, update_data: Dict) -> Dict:
        """Обработка pre-checkout запроса"""
        try:
            pre_checkout_query = update_data.get('pre_checkout_query', {})
            query_id = pre_checkout_query.get('id')
            
            if not query_id:
                return {'success': False, 'error': 'Нет ID запроса'}
            
            # Проверяем валидность платежа
            invoice_payload = pre_checkout_query.get('invoice_payload', '{}')
            try:
                payload_data = json.loads(invoice_payload)
                offer_id = payload_data.get('offer_id')
                amount = payload_data.get('amount')
                
                # Проверяем существование оффера
                if offer_id:
                    from add_offer import get_offer_by_id
                    offer = get_offer_by_id(offer_id)
                    
                    if not offer:
                        # Отклоняем платеж
                        await self.answer_pre_checkout_query(query_id, False, "Оффер не найден")
                        return {'success': False, 'error': 'Оффер не найден'}
                    
                    if offer['payment_status'] == 'paid':
                        # Отклоняем платеж
                        await self.answer_pre_checkout_query(query_id, False, "Оффер уже оплачен")
                        return {'success': False, 'error': 'Оффер уже оплачен'}
                
                # Одобряем платеж
                await self.answer_pre_checkout_query(query_id, True)
                return {'success': True}
                
            except json.JSONDecodeError:
                # Отклоняем платеж
                await self.answer_pre_checkout_query(query_id, False, "Некорректные данные платежа")
                return {'success': False, 'error': 'Некорректные данные'}
                
        except Exception as e:
            logger.error(f"Ошибка pre-checkout: {e}")
            # В случае ошибки отклоняем платеж
            if 'query_id' in locals():
                await self.answer_pre_checkout_query(query_id, False, "Внутренняя ошибка")
            return {'success': False, 'error': str(e)}
    
    async def answer_pre_checkout_query(self, query_id: str, ok: bool, error_message: str = None):
        """Ответ на pre-checkout запрос"""
        try:
            payload = {
                'pre_checkout_query_id': query_id,
                'ok': ok
            }
            
            if not ok and error_message:
                payload['error_message'] = error_message
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/answerPreCheckoutQuery",
                    json=payload
                ) as response:
                    result = await response.json()
                    logger.info(f"Pre-checkout ответ: {result}")
                    
        except Exception as e:
            logger.error(f"Ошибка ответа на pre-checkout: {e}")

# Создаем обработчик
webhook_handler = TelegramWebhookHandler()

@webhooks_bp.route('/telegram', methods=['POST'])
def handle_telegram_webhook():
    """Основной webhook для обработки обновлений от Telegram"""
    try:
        # Проверяем заголовки безопасности (опционально)
        secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret_token != WEBHOOK_SECRET:
            logger.warning(f"Получен webhook с неверным секретом: {secret_token}")
            # Можно раскомментировать для строгой проверки
            # return jsonify({'status': 'error', 'message': 'Invalid secret token'}), 401
        
        # Получаем данные
        update_data = request.get_json()
        if not update_data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        logger.info(f"Получен webhook: {json.dumps(update_data, indent=2)}")
        
        # Обработка различных типов обновлений
        if 'message' in update_data:
            message = update_data['message']
            
            # Обработка успешного платежа
            if 'successful_payment' in message:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    webhook_handler.process_successful_payment(update_data)
                )
                loop.close()
                
                if result['success']:
                    logger.info(f"✅ Платеж успешно обработан: {result}")
                    return jsonify({'status': 'ok', 'message': 'Payment processed'})
                else:
                    logger.error(f"❌ Ошибка обработки платежа: {result}")
                    return jsonify({'status': 'error', 'message': result.get('error')}), 400
        
        # Обработка pre-checkout запроса
        elif 'pre_checkout_query' in update_data:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                webhook_handler.process_pre_checkout_query(update_data)
            )
            loop.close()
            
            if result['success']:
                logger.info("✅ Pre-checkout запрос обработан")
                return jsonify({'status': 'ok', 'message': 'Pre-checkout processed'})
            else:
                logger.error(f"❌ Ошибка pre-checkout: {result}")
                return jsonify({'status': 'error', 'message': result.get('error')}), 400
        
        # Для других типов обновлений просто возвращаем OK
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@webhooks_bp.route('/test-payment', methods=['POST'])
def test_payment_webhook():
    """Тестирование webhook платежей"""
    try:
        # Только для разработки!
        if os.environ.get('FLASK_ENV') != 'development':
            return jsonify({'error': 'Not available in production'}), 403
        
        data = request.get_json()
        logger.info(f"Тестовый webhook платежа: {data}")
        
        # Имитируем успешный платеж
        test_payment_data = {
            'message': {
                'successful_payment': {
                    'currency': 'RUB',
                    'total_amount': data.get('amount', 100) * 100,  # В копейках
                    'invoice_payload': json.dumps({
                        'offer_id': data.get('offer_id', 1),
                        'amount': data.get('amount', 100),
                        'timestamp': datetime.now().isoformat()
                    }),
                    'telegram_payment_charge_id': f'test_{datetime.now().timestamp()}',
                    'telegram_payment_id': f'test_payment_{datetime.now().timestamp()}',
                    'provider_payment_charge_id': f'provider_{datetime.now().timestamp()}'
                },
                'from': {
                    'id': data.get('user_id', YOUR_TELEGRAM_ID),
                    'username': 'test_user'
                }
            }
        }
        
        # Обрабатываем тестовый платеж
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            webhook_handler.process_successful_payment(test_payment_data)
        )
        loop.close()
        
        return jsonify({'status': 'ok', 'result': result})
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестового webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@webhooks_bp.route('/set-webhook', methods=['POST'])
def set_telegram_webhook():
    """Установка webhook URL в Telegram"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return jsonify({'error': 'webhook_url required'}), 400
        
        # Устанавливаем webhook
        async def setup_webhook():
            payload = {
                'url': webhook_url,
                'secret_token': WEBHOOK_SECRET,
                'allowed_updates': ['message', 'pre_checkout_query'],
                'drop_pending_updates': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    json=payload
                ) as response:
                    result = await response.json()
                    return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(setup_webhook())
        loop.close()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return jsonify({'success': True, 'result': result})
        else:
            logger.error(f"❌ Ошибка установки webhook: {result}")
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@webhooks_bp.route('/webhook-info', methods=['GET'])
def get_webhook_info():
    """Получение информации о текущем webhook"""
    try:
        async def get_info():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
                ) as response:
                    result = await response.json()
                    return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_info())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def register_webhook_routes(app):
    """Регистрация webhook маршрутов в Flask приложении"""
    app.register_blueprint(webhooks_bp)
    logger.info("✅ Webhook маршруты зарегистрированы")

# Настройка автоматической установки webhook при запуске (только для продакшена)
async def auto_setup_webhook():
    """Автоматическая настройка webhook при запуске"""
    try:
        webapp_url = os.environ.get('WEBAPP_URL')
        if not webapp_url:
            logger.warning("⚠️ WEBAPP_URL не настроен, пропускаем автоустановку webhook")
            return
        
        webhook_url = f"{webapp_url.rstrip('/')}/webhook/telegram"
        
        payload = {
            'url': webhook_url,
            'secret_token': WEBHOOK_SECRET,
            'allowed_updates': ['message', 'pre_checkout_query'],
            'drop_pending_updates': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                json=payload
            ) as response:
                result = await response.json()
                
                if result.get('ok'):
                    logger.info(f"✅ Webhook автоматически установлен: {webhook_url}")
                else:
                    logger.error(f"❌ Ошибка автоустановки webhook: {result}")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка автоустановки webhook: {e}")

# Импортируем переменные из основного приложения
try:
    from working_app import YOUR_TELEGRAM_ID
except ImportError:
    YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))

if __name__ == '__main__':
    # Тестирование webhook обработчика
    import asyncio
    
    print("🧪 Тестирование webhook обработчика...")
    
    # Тест автоустановки webhook
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(auto_setup_webhook())
    loop.close()
