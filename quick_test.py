#!/usr/bin/env python3
"""
Быстрый тест API офферов
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_debug_user():
    """Тест debug маршрута"""
    print("🔍 ТЕСТ DEBUG USER")
    print("-" * 30)
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/offers/debug/user',
            headers={
                'X-Telegram-User-Id': '373086959',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ User ID определен: {data.get('user_id')}")
                return True
            else:
                print(f"❌ Ошибка: {data.get('error')}")
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def test_create_offer_api():
    """Тест создания оффера через API"""
    print("\n🎯 ТЕСТ СОЗДАНИЯ ОФФЕРА")
    print("-" * 30)
    
    offer_data = {
        'title': 'API тест оффер',
        'description': 'Тестирование через Python requests',
        'content': 'Полное описание тестового оффера',
        'price': 1500,
        'currency': 'RUB',
        'category': 'tech',
        'target_audience': 'IT специалисты',
        'requirements': 'Размещение в течение недели'
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/offers',
            json=offer_data,
            headers={
                'X-Telegram-User-Id': '373086959',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get('success'):
                print(f"✅ Оффер создан с ID: {data.get('offer_id')}")
                return data.get('offer_id')
            else:
                print(f"❌ Ошибка создания: {data.get('error')}")
        
        return None
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_get_my_offers():
    """Тест получения моих офферов"""
    print("\n📋 ТЕСТ ПОЛУЧЕНИЯ ОФФЕРОВ")
    print("-" * 30)
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/offers/my',
            headers={
                'X-Telegram-User-Id': '373086959',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                offers = data.get('offers', [])
                print(f"✅ Найдено офферов: {len(offers)}")
                
                for i, offer in enumerate(offers[-3:], 1):  # Показываем последние 3
                    print(f"   {i}. ID: {offer['id']} | {offer['title']} | {offer['price']} {offer['currency']}")
                
                return len(offers)
            else:
                print(f"❌ Ошибка: {data.get('error')}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return 0

def check_server():
    """Проверяем что сервер запущен"""
    print("🔍 ПРОВЕРКА СЕРВЕРА")
    print("-" * 30)
    
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        if response.status_code == 200:
            print("✅ Сервер работает")
            return True
        else:
            print(f"⚠️ Сервер отвечает с кодом: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        print("💡 Убедитесь что запущен: python working_app.py")
        return False

def main():
    """Главная функция"""
    print("🧪 БЫСТРЫЙ ТЕСТ API ОФФЕРОВ")
    print("=" * 40)
    
    # Проверяем сервер
    if not check_server():
        return
    
    # Тестируем API
    debug_ok = test_debug_user()
    offer_id = test_create_offer_api()
    offers_count = test_get_my_offers()
    
    # Итоги
    print("\n" + "=" * 40)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 40)
    
    if debug_ok:
        print("✅ Debug API работает")
    else:
        print("❌ Debug API не работает")
    
    if offer_id:
        print("✅ Создание офферов работает")
    else:
        print("❌ Создание офферов не работает")
    
    if offers_count > 0:
        print(f"✅ Получение офферов работает ({offers_count} офферов)")
    else:
        print("❌ Получение офферов не работает")
    
    if debug_ok and offer_id and offers_count > 0:
        print("\n🎉 ВСЕ API РАБОТАЮТ!")
        print("🚀 Можно тестировать веб-интерфейс:")
        print("   http://localhost:5000/offers")
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ С API")
        print("💡 Проверьте логи сервера")

if __name__ == '__main__':
    main()
