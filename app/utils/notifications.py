import sqlite3
import logging
from datetime import datetime
import os
import sys
from add_offer import send_telegram_message
# Добавляем путь для импорта
sys.path.insert(0, os.getcwd())

logger = logging.getLogger(__name__)
DATABASE_PATH = 'telegram_mini_app.db'


def send_contract_notification(contract_id, notification_type, extra_data=None):
    """Отправка уведомлений по контрактам"""
    try:
        from working_app import AppConfig

        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем информацию о контракте
        cursor.execute('''
                       SELECT c.*,
                              o.title           as offer_title,
                              u_adv.telegram_id as advertiser_telegram_id,
                              u_adv.first_name  as advertiser_name,
                              u_pub.telegram_id as publisher_telegram_id,
                              u_pub.first_name  as publisher_name,
                              or_resp.channel_title
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN users u_adv ON c.advertiser_id = u_adv.id
                                JOIN users u_pub ON c.publisher_id = u_pub.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       WHERE c.id = ?
                       ''', (contract_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        if notification_type == 'created':
            # Уведомления о создании контракта
            advertiser_msg = f"""📋 <b>Контракт создан!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Сумма:</b> {data['price']} RUB
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

⏰ <b>Срок размещения:</b> {formatDate(data['placement_deadline'])}
🔍 <b>Срок мониторинга:</b> {data['monitoring_duration']} дней

📱 Издатель должен разместить рекламу и подать заявку в приложении."""

            publisher_msg = f"""✅ <b>Ваш отклик принят! Контракт создан.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data['price']} RUB
👤 <b>Рекламодатель:</b> {data['advertiser_name']}

⏰ <b>Разместите рекламу до:</b> {formatDate(data['placement_deadline'])}

📝 <b>Что делать дальше:</b>
1. Разместите рекламу в своем канале
2. Подайте заявку с ссылкой на пост в приложении
3. После проверки начнется мониторинг
4. Получите оплату после завершения"""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Открыть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], advertiser_msg, keyboard)
            send_telegram_message(data['publisher_telegram_id'], publisher_msg, keyboard)

        elif notification_type == 'placement_submitted':
            # Уведомление рекламодателю о подаче заявки
            message = f"""📤 <b>Заявка о размещении подана!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

🔍 Начинается автоматическая проверка размещения.
Вы получите уведомление о результате проверки."""

            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📋 Посмотреть контракт",
                            "web_app": {
                                "url": f"{AppConfig.WEBAPP_URL}/offers?tab=contracts&contract_id={contract_id}"
                            }
                        }
                    ]
                ]
            }

            send_telegram_message(data['advertiser_telegram_id'], message, keyboard)

        elif notification_type == 'verification_result':
            # Уведомления о результате проверки
            status = extra_data.get('status') if extra_data else data['status']

            if status == 'monitoring':
                adv_msg = f"""✅ <b>Размещение подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}

🔍 Начат мониторинг размещения на {data['monitoring_duration']} дней.
Оплата будет произведена автоматически после завершения мониторинга."""

                pub_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>К оплате:</b> {data['price']} RUB

🔍 Начат мониторинг на {data['monitoring_duration']} дней.
Не удаляйте пост до завершения мониторинга!"""

            else:
                error_msg = extra_data.get('message') if extra_data else 'Размещение не соответствует требованиям'

                pub_msg = f"""❌ <b>Проверка не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Причина:</b> {error_msg}

🔄 Исправьте размещение и подайте заявку повторно."""

                adv_msg = f"""❌ <b>Проверка размещения не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Причина:</b> {error_msg}

Издатель должен исправить размещение."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'completed':
            # Уведомления о завершении контракта
            payment_id = extra_data.get('payment_id') if extra_data else 'N/A'
            amount = extra_data.get('amount') if extra_data else data['price']

            adv_msg = f"""✅ <b>Контракт завершен!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
💰 <b>Сумма:</b> {amount} RUB

✅ Мониторинг завершен успешно.
💳 Платеж #{payment_id} обрабатывается."""

            pub_msg = f"""🎉 <b>Поздравляем! Контракт выполнен.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Заработано:</b> {amount} RUB

💳 Платеж #{payment_id} поступит на ваш счет в течение 24 часов.
Спасибо за качественную работу!"""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'violation':
            # Уведомления о нарушении
            reason = extra_data.get('reason') if extra_data else 'Нарушение условий контракта'

            pub_msg = f"""⚠️ <b>Обнаружено нарушение!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Проблема:</b> {reason}

🔄 Пожалуйста, восстановите размещение или свяжитесь с поддержкой."""

            adv_msg = f"""⚠️ <b>Нарушение контракта</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Проблема:</b> {reason}

Мы уведомили издателя о необходимости исправления."""

            send_telegram_message(data['advertiser_telegram_id'], adv_msg)
            send_telegram_message(data['publisher_telegram_id'], pub_msg)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления по контракту: {e}")

def formatDate(date_str):
    """Форматирование даты для уведомлений"""
    try:
        if not date_str:
            return 'Не указано'
        dt = datetime.fromisoformat(date_str)
        return dt.strftime('%d.%m.%Y в %H:%M')
    except:
        return date_str