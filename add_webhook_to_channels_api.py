#!/usr/bin/env python3
"""
Добавление webhook endpoint в app/api/channels.py
Этот скрипт добавляет функцию автоматической верификации
"""

import os
import re

def add_webhook_to_channels_api():
    """Добавляет webhook endpoint в файл app/api/channels.py"""
    
    channels_api_path = 'app/api/channels.py'
    
    if not os.path.exists(channels_api_path):
        print(f"❌ Файл не найден: {channels_api_path}")
        return False
    
    # Читаем существующий файл
    with open(channels_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем, не добавлен ли уже webhook
    if '/webhook' in content and 'telegram_webhook' in content:
        print("ℹ️ Webhook endpoint уже существует в файле")
        return True
    
    # Webhook код для добавления
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
            
            verification_found = False
            
            for channel in channels:
                verification_code = channel['verification_code']
                if verification_code and verification_code in text:
                    # Подтверждаем канал
                    success = db_manager.execute_query("""
                        UPDATE channels 
                        SET status = 'verified', verified_at = ?, is_verified = 1
                        WHERE id = ?
                    """, (datetime.now().isoformat(), channel['id']))
                    
                    if success:
                        logger.info(f"✅ Канал {channel['username']} автоматически верифицирован с кодом {verification_code}!")
                        verification_found = True
                    else:
                        logger.error(f"❌ Ошибка обновления канала {channel['id']}")
            
            if verification_found:
                logger.info("🎉 Верификация успешно завершена!")
        
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'ok': True})  # Всегда возвращаем ok для Telegram
'''

    # Находим место для вставки (перед последним комментарием или в конце)
    insert_position = len(content)
    
    # Ищем место после последней функции
    if 'def ' in content:
        # Находим последнюю функцию
        last_func_match = None
        for match in re.finditer(r'\ndef [^:]+:', content):
            last_func_match = match
        
        if last_func_match:
            # Находим конец последней функции
            start_pos = last_func_match.start()
            remaining_content = content[start_pos:]
            
            # Ищем следующую функцию или конец файла
            next_func = re.search(r'\n\ndef ', remaining_content)
            if next_func:
                insert_position = start_pos + next_func.start()
            else:
                # Если нет следующей функции, вставляем в конец
                insert_position = len(content)
    
    # Вставляем webhook код
    new_content = content[:insert_position] + webhook_code + content[insert_position:]
    
    # Создаем резервную копию
    backup_path = f"{channels_api_path}.backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Записываем обновленный файл
    with open(channels_api_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Webhook endpoint добавлен в {channels_api_path}")
    print(f"📄 Резервная копия: {backup_path}")
    
    return True

def update_channels_api_imports():
    """Обновляет импорты в начале файла"""
    
    channels_api_path = 'app/api/channels.py'
    
    if not os.path.exists(channels_api_path):
        return False
    
    with open(channels_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем нужные импорты
    imports_to_add = []
    
    if 'from datetime import datetime' not in content:
        imports_to_add.append('from datetime import datetime')
    
    if 'import logging' not in content:
        imports_to_add.append('import logging')
    
    if imports_to_add:
        # Находим место для вставки импортов (после существующих импортов)
        import_lines = []
        lines = content.split('\n')
        
        insert_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                insert_line = i + 1
        
        # Вставляем новые импорты
        for imp in imports_to_add:
            lines.insert(insert_line, imp)
            insert_line += 1
        
        # Записываем обновленный файл
        new_content = '\n'.join(lines)
        with open(channels_api_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Обновлены импорты: {', '.join(imports_to_add)}")
    
    return True

def test_webhook_endpoint():
    """Тестирует добавленный endpoint"""
    print("\n🧪 Тестирование webhook endpoint...")
    
    import requests
    
    try:
        url = "https://lesson-bed-cent-concentration.trycloudflare.com/api/channels/webhook"
        
        test_data = {
            "update_id": 123456789,
            "channel_post": {
                "message_id": 1,
                "chat": {
                    "id": "-1001000000999",
                    "type": "channel",
                    "title": "Тестовый канал"
                },
                "date": 1640995200,
                "text": "#addtest123 - код верификации"
            }
        }
        
        response = requests.post(url, json=test_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook endpoint работает!")
                return True
            else:
                print(f"⚠️ Неожиданный ответ: {result}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
    
    return False

def main():
    """Главная функция"""
    print("=" * 60)
    print("🔧 ДОБАВЛЕНИЕ WEBHOOK В API КАНАЛОВ")
    print("=" * 60)
    
    # 1. Обновляем импорты
    if update_channels_api_imports():
        print("✅ Импорты обновлены")
    
    # 2. Добавляем webhook endpoint
    if add_webhook_to_channels_api():
        print("✅ Webhook endpoint добавлен")
        
        # 3. Тестируем endpoint
        print("\n⏳ Ожидание 3 секунды для перезагрузки сервера...")
        import time
        time.sleep(3)
        
        test_webhook_endpoint()
        
        print("\n🎉 Настройка завершена!")
        print("📋 Следующие шаги:")
        print("1. Перезапустите сервер: python working_app.py")
        print("2. Настройте webhook: python setup_webhook.py")
        print("3. Протестируйте добавление канала")
        
    else:
        print("❌ Не удалось добавить webhook endpoint")

if __name__ == '__main__':
    main()
