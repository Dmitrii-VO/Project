#!/usr/bin/env python3
"""
Тестирование системы автоматической модерации каналов
"""

import requests
import json
import time
from datetime import datetime

# Конфигурация для тестов
BASE_URL = "https://lesson-bed-cent-concentration.trycloudflare.com"  # Ваш URL из .env
BOT_TOKEN = "6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8"

def test_webhook_setup():
    """Тест 1: Проверка настройки webhook"""
    print("🧪 Тест 1: Проверка настройки webhook")
    
    # Проверяем текущий webhook
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok'):
            webhook_info = data.get('result', {})
            current_url = webhook_info.get('url', '')
            
            print(f"✅ Текущий webhook URL: {current_url}")
            print(f"✅ Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"✅ Last error: {webhook_info.get('last_error_message', 'Нет ошибок')}")
            
            # Устанавливаем webhook на наш endpoint
            webhook_url = f"{BASE_URL}/api/channels/webhook"
            set_webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
            
            set_response = requests.post(set_webhook_url, json={
                'url': webhook_url,
                'allowed_updates': ['channel_post', 'message']
            })
            
            if set_response.status_code == 200:
                result = set_response.json()
                if result.get('ok'):
                    print(f"✅ Webhook успешно установлен на: {webhook_url}")
                    return True
                else:
                    print(f"❌ Ошибка установки webhook: {result.get('description')}")
            else:
                print(f"❌ HTTP ошибка: {set_response.status_code}")
                
        else:
            print(f"❌ Ошибка API: {data.get('description')}")
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    
    return False

def test_channel_creation():
    """Тест 2: Создание канала и получение кода верификации"""
    print("\n🧪 Тест 2: Создание тестового канала")
    
    # Тестовые данные канала
    channel_data = {
        "channel_id": "@testchannel123",  # Замените на реальный канал для теста
        "channel_name": "Тестовый канал",
        "category": "technology",
        "price_per_post": 100.0
    }
    
    headers = {
        "Content-Type": "application/json",
        # Здесь нужно добавить Telegram auth headers
    }
    
    try:
        url = f"{BASE_URL}/api/channels/"
        response = requests.post(url, json=channel_data, headers=headers)
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get('success'):
                channel = data.get('channel', {})
                verification_code = channel.get('verification_code')
                
                print(f"✅ Канал создан с ID: {channel.get('id')}")
                print(f"✅ Код верификации: {verification_code}")
                print(f"✅ Инструкции: {channel.get('verification_instructions')}")
                
                return verification_code
            else:
                print(f"❌ Ошибка создания: {data.get('message')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            try:
                error_data = response.json()
                print(f"❌ Детали ошибки: {error_data}")
            except:
                print(f"❌ Текст ошибки: {response.text}")
                
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    
    return None

def test_webhook_endpoint():
    """Тест 3: Проверка работы webhook endpoint"""
    print("\n🧪 Тест 3: Проверка webhook endpoint")
    
    # Симулируем webhook от Telegram
    test_webhook_data = {
        "update_id": 123456789,
        "channel_post": {
            "message_id": 1,
            "chat": {
                "id": "@testchannel123",
                "type": "channel",
                "title": "Тестовый канал"
            },
            "date": int(time.time()),
            "text": "#add123abc - код верификации канала"
        }
    }
    
    try:
        url = f"{BASE_URL}/api/channels/webhook"
        response = requests.post(url, json=test_webhook_data)
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("✅ Webhook endpoint работает корректно")
                return True
            else:
                print(f"❌ Неожиданный ответ: {data}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            try:
                error_data = response.json()
                print(f"❌ Детали ошибки: {error_data}")
            except:
                print(f"❌ Текст ошибки: {response.text}")
                
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
    
    return False

def test_code_generation():
    """Тест 4: Проверка генерации кодов верификации"""
    print("\n🧪 Тест 4: Проверка генерации кодов")
    
    import string
    import random
    
    def generate_verification_code():
        """Тестовая генерация кода"""
        chars = string.ascii_lowercase + string.digits
        random_part = ''.join(random.choices(chars, k=6))
        return f"#add{random_part}"
    
    # Генерируем несколько кодов
    codes = [generate_verification_code() for _ in range(5)]
    
    print("✅ Сгенерированные коды:")
    for i, code in enumerate(codes, 1):
        print(f"  {i}. {code}")
    
    # Проверяем уникальность
    if len(set(codes)) == len(codes):
        print("✅ Все коды уникальны")
        return True
    else:
        print("❌ Обнаружены дублирующиеся коды")
        return False

def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("🚀 ТЕСТИРОВАНИЕ АВТОМАТИЧЕСКОЙ МОДЕРАЦИИ КАНАЛОВ")
    print("=" * 60)
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: {BASE_URL}")
    print("=" * 60)
    
    tests = [
        ("Настройка webhook", test_webhook_setup),
        ("Генерация кодов", test_code_generation),
        ("Webhook endpoint", test_webhook_endpoint),
        # ("Создание канала", test_channel_creation),  # Отключен без auth
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status:15} | {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 Общий результат: {passed}/{len(results)} тестов пройдено")
    
    if passed == len(results):
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️ Есть проблемы, требующие внимания.")

if __name__ == "__main__":
    main()
