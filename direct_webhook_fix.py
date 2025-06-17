#!/usr/bin/env python3
"""
Прямое исправление webhook кода
Заменяет неработающий код на рабочий
"""

import os
import time


def create_working_webhook():
    """Создает правильный webhook код"""

    # Правильный webhook код без ошибок импорта
    webhook_code = '''

@channels_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook для автоматической верификации каналов"""
    try:
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)
        data = request.get_json()

        if not data:
            return jsonify({'ok': True})

        logger.info(f"📨 Webhook получен: {data.get('update_id', 'N/A')}")

        # Обрабатываем сообщения в каналах
        if 'channel_post' in data:
            message = data['channel_post']
            chat = message.get('chat', {})
            chat_id = str(chat.get('id'))
            text = message.get('text', '')

            logger.info(f"📢 Сообщение из канала {chat_id}: {text[:50]}...")

            # Ищем каналы с кодами верификации
            channels = db_manager.execute_query("""
                SELECT id, username, verification_code, telegram_id
                FROM channels 
                WHERE status = 'pending_verification' 
                AND verification_code IS NOT NULL
            """, fetch_all=True)

            if channels:
                logger.info(f"🔍 Найдено {len(channels)} каналов на проверке")

                verification_found = False

                for channel in channels:
                    verification_code = channel['verification_code']
                    if verification_code and verification_code in text:
                        # Подтверждаем канал
                        db_manager.execute_query("""
                            UPDATE channels 
                            SET status = 'verified', verified_at = ?, is_verified = 1
                            WHERE id = ?
                        """, (datetime.now().isoformat(), channel['id']))

                        logger.info(f"✅ Канал {channel['username']} автоматически верифицирован с кодом {verification_code}!")
                        verification_found = True

                if verification_found:
                    logger.info("🎉 Верификация успешно завершена!")
                else:
                    logger.info("ℹ️ Код верификации не найден в сообщении")
            else:
                logger.info("ℹ️ Нет каналов ожидающих верификации")

        return jsonify({'ok': True})

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Ошибка webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'ok': True})
'''

    return webhook_code


def fix_channels_api():
    """Исправляет app/api/channels.py"""

    channels_api_path = 'app/api/channels.py'

    if not os.path.exists(channels_api_path):
        print(f"❌ Файл не найден: {channels_api_path}")
        return False

    # Читаем файл
    with open(channels_api_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Создаем резервную копию
    backup_path = f"{channels_api_path}.backup_{int(time.time())}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Удаляем весь старый webhook код
    lines = content.split('\n')
    new_lines = []
    skip_webhook = False

    for line in lines:
        if '@channels_bp.route(\'/webhook\'' in line:
            skip_webhook = True
            continue

        if skip_webhook:
            # Пропускаем строки до конца функции
            if line.strip() and not line.startswith(' ') and not line.startswith('\t') and 'def ' in line:
                skip_webhook = False
                new_lines.append(line)
            elif 'return jsonify({\'ok\': True})' in line:
                skip_webhook = False
                continue
        else:
            new_lines.append(line)

    # Добавляем новый рабочий webhook
    new_content = '\n'.join(new_lines) + create_working_webhook()

    # Записываем исправленный файл
    with open(channels_api_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✅ Файл исправлен: {channels_api_path}")
    print(f"📄 Резервная копия: {backup_path}")

    return True


def test_webhook():
    """Тестирует webhook"""
    import requests
    import time

    print("🧪 Тестирование webhook через 3 секунды...")
    time.sleep(3)

    try:
        url = "https://lesson-bed-cent-concentration.trycloudflare.com/api/channels/webhook"

        test_data = {
            "update_id": 999999999,
            "channel_post": {
                "message_id": 1,
                "chat": {
                    "id": "-1001000000001",
                    "type": "channel",
                    "title": "Test Channel"
                },
                "date": 1640995200,
                "text": "#addtest123 - код верификации"
            }
        }

        response = requests.post(url, json=test_data, timeout=10)
        print(f"Статус: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Ответ: {result}")
            if result.get('ok'):
                print("✅ Webhook работает!")
                return True

        print("⚠️ Неожиданный ответ")
        return False

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    import time

    print("=" * 50)
    print("🛠️ ПРЯМОЕ ИСПРАВЛЕНИЕ WEBHOOK")
    print("=" * 50)

    # Исправляем файл
    if fix_channels_api():
        print("✅ Файл исправлен")
        print("\n⚠️ ПЕРЕЗАПУСТИТЕ СЕРВЕР!")
        print("1. Остановите сервер (Ctrl+C)")
        print("2. Запустите: python working_app.py")
        print("3. Затем протестируйте добавление канала")

        # Опционально тестируем
        test_choice = input("\nТестировать webhook сейчас? (y/n): ")
        if test_choice.lower() == 'y':
            test_webhook()
    else:
        print("❌ Не удалось исправить файл")


if __name__ == '__main__':
    main()