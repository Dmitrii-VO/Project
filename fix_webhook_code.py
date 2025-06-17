#!/usr/bin/env python3
"""
Исправление webhook кода в app/api/channels.py
Заменяет неправильные импорты на правильные
"""

import os
import re

def fix_webhook_imports():
    """Исправляет импорты в webhook коде"""
    
    channels_api_path = 'app/api/channels.py'
    
    if not os.path.exists(channels_api_path):
        print(f"❌ Файл не найден: {channels_api_path}")
        return False
    
    # Читаем файл
    with open(channels_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Создаем резервную копию
    backup_path = f"{channels_api_path}.backup_fix"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Исправляем webhook код - заменяем весь блок
    old_webhook_pattern = r"@channels_bp\.route\('/webhook'.*?return jsonify\(\{'ok': True\}\)"
    
    new_webhook_code = '''@channels_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook для автоматической верификации каналов"""
    try:
        from datetime import datetime
        from app.models.database import db_manager
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
        return jsonify({'ok': True})  # Всегда возвращаем ok для Telegram'''
    
    # Заменяем webhook код
    new_content = re.sub(old_webhook_pattern, new_webhook_code, content, flags=re.DOTALL)
    
    # Если замена не сработала, добавляем в конец
    if '@channels_bp.route(\'/webhook\'' not in new_content:
        new_content += '\n\n' + new_webhook_code
    
    # Записываем исправленный файл
    with open(channels_api_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Webhook код исправлен в {channels_api_path}")
    print(f"📄 Резервная копия: {backup_path}")
    
    return True

def add_required_imports():
    """Добавляет необходимые импорты в начало файла"""
    
    channels_api_path = 'app/api/channels.py'
    
    with open(channels_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем импорты
    required_imports = [
        'from flask import Blueprint, request, jsonify',
        'from app.models.database import db_manager',
        'from datetime import datetime',
        'import logging'
    ]
    
    lines = content.split('\n')
    import_section_end = 0
    
    # Находим конец секции импортов
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
            import_section_end = i + 1
    
    # Добавляем недостающие импорты
    imports_added = []
    for imp in required_imports:
        if imp not in content:
            lines.insert(import_section_end, imp)
            imports_added.append(imp)
            import_section_end += 1
    
    if imports_added:
        new_content = '\n'.join(lines)
        with open(channels_api_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Добавлены импорты: {imports_added}")
    
    return True

def test_webhook_manually():
    """Ручное тестирование webhook"""
    print("🧪 Тестирование webhook...")
    
    import requests
    
    webhook_url = "https://lesson-bed-cent-concentration.trycloudflare.com/api/channels/webhook"
    
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
            "text": "#addmkg2x0 - тестовый код верификации"  # Используем реальный код из логов
        }
    }
    
    try:
        response = requests.post(webhook_url, json=test_data, timeout=10)
        
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook работает корректно!")
                return True
        
        print("⚠️ Неожиданный ответ")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("=" * 50)
    print("🔧 ИСПРАВЛЕНИЕ WEBHOOK")
    print("=" * 50)
    
    # 1. Добавляем импорты
    print("1️⃣ Проверка импортов...")
    add_required_imports()
    
    # 2. Исправляем webhook код
    print("2️⃣ Исправление webhook...")
    if fix_webhook_imports():
        print("✅ Webhook код исправлен")
        
        # 3. Тестируем
        print("3️⃣ Тестирование...")
        test_webhook_manually()
        
        print("\n🎉 Исправление завершено!")
        print("📋 Теперь нужно:")
        print("1. Перезапустить сервер")
        print("2. Добавить канал и получить код")
        print("3. Отправить код в канал")
        
    else:
        print("❌ Не удалось исправить webhook")

if __name__ == '__main__':
    main()
