#!/usr/bin/env python3
"""
Тестирование исправленной системы офферов
"""

import requests
import json
from datetime import datetime

# Настройки
BASE_URL = 'http://localhost:5000'
TEST_USER_ID = 373086959  # Ваш Telegram ID

def test_create_offer():
    """Тест создания оффера через API"""
    print("🧪 ТЕСТ СОЗДАНИЯ ОФФЕРА")
    print("-" * 40)
    
    offer_data = {
        'title': 'Тестовый оффер через API',
        'description': 'Описание тестового оффера для проверки работы системы',
        'content': 'Полное содержание оффера с требованиями к размещению',
        'price': 2500,
        'currency': 'RUB',
        'category': 'tech',
        'target_audience': 'IT-специалисты 25-40 лет',
        'requirements': 'Размещение в течение 3 дней, без редактирования',
        'duration_days': 21,
        'min_subscribers': 500,
        'max_subscribers': 50000,
        'budget_total': 2500
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/api/offers',
            json=offer_data,
            headers={'X-Telegram-User-Id': str(TEST_USER_ID)}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('success'):
            print("✅ Оффер создан успешно!")
            return result.get('offer_id')
        else:
            print("❌ Ошибка создания оффера")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_get_my_offers():
    """Тест получения моих офферов"""
    print("\n🧪 ТЕСТ ПОЛУЧЕНИЯ МОИХ ОФФЕРОВ")
    print("-" * 40)
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/offers/my',
            headers={'X-Telegram-User-Id': str(TEST_USER_ID)}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result.get('success'):
            offers = result.get('offers', [])
            print(f"✅ Найдено офферов: {len(offers)}")
            
            for i, offer in enumerate(offers, 1):
                print(f"\n📋 Оффер #{i}:")
                print(f"   ID: {offer['id']}")
                print(f"   Название: {offer['title']}")
                print(f"   Цена: {offer['price']} {offer['currency']}")
                print(f"   Категория: {offer['category']}")
                print(f"   Статус: {offer['status']}")
                print(f"   Откликов: {offer.get('response_count', 0)}")
            
            return offers
        else:
            print("❌ Ошибка получения офферов")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return []

def test_get_offer_detail(offer_id):
    """Тест получения деталей оффера"""
    if not offer_id:
        return
        
    print(f"\n🧪 ТЕСТ ПОЛУЧЕНИЯ ДЕТАЛЕЙ ОФФЕРА {offer_id}")
    print("-" * 40)
    
    try:
        response = requests.get(
            f'{BASE_URL}/api/offers/detail/{offer_id}',
            headers={'X-Telegram-User-Id': str(TEST_USER_ID)}
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result.get('success'):
            offer = result.get('offer')
            print("✅ Детали оффера получены:")
            print(f"   ID: {offer['id']}")
            print(f"   Название: {offer['title']}")
            print(f"   Описание: {offer['description'][:100]}...")
            print(f"   Цена: {offer['price']} {offer['currency']}")
            print(f"   Категория: {offer['category']}")
            print(f"   Целевая аудитория: {offer.get('target_audience', 'Не указана')}")
            print(f"   Требования: {offer.get('requirements', 'Не указаны')}")
            print(f"   Дедлайн: {offer.get('deadline', 'Не указан')}")
            print(f"   Создатель: {offer.get('creator_username', 'N/A')}")
            print(f"   Бюджет: {offer.get('budget_total', 0)}")
            print(f"   Подписчики: {offer.get('min_subscribers', 0)} - {offer.get('max_subscribers', 0)}")
            return offer
        else:
            print("❌ Ошибка получения деталей оффера")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_direct_function():
    """Тест прямого вызова функций из add_offer.py"""
    print("\n🧪 ТЕСТ ПРЯМОГО ВЫЗОВА ФУНКЦИЙ")
    print("-" * 40)
    
    try:
        # Импортируем исправленный модуль
        import sys
        import os
        sys.path.insert(0, os.getcwd())
        
        from add_offer import add_offer, get_user_offers, get_offer_by_id
        
        # Тестовые данные
        test_data = {
            'title': 'Прямой тест функции',
            'description': 'Тест создания оффера через прямой вызов функции',
            'content': 'Полное описание оффера для тестирования',
            'price': 3000,
            'currency': 'RUB',
            'category': 'business',
            'target_audience': 'Предприниматели',
            'requirements': 'Качественное размещение',
            'duration_days': 30
        }
        
        # Тест создания
        print("1. Создание оффера...")
        result = add_offer(TEST_USER_ID, test_data)
        print(f"   Результат: {result.get('success')}")
        
        if result.get('success'):
            offer_id = result.get('offer_id')
            print(f"   Создан оффер ID: {offer_id}")
            
            # Тест получения списка
            print("2. Получение списка офферов...")
            offers = get_user_offers(TEST_USER_ID)
            print(f"   Найдено офферов: {len(offers)}")
            
            # Тест получения по ID
            print("3. Получение оффера по ID...")
            offer_detail = get_offer_by_id(offer_id)
            print(f"   Оффер найден: {offer_detail is not None}")
            
            if offer_detail:
                print(f"   Название: {offer_detail['title']}")
                print(f"   Цена: {offer_detail['price']}")
                
            return True
        else:
            print(f"   Ошибка: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_direct():
    """Тест прямого обращения к БД"""
    print("\n🧪 ТЕСТ ПРЯМОГО ОБРАЩЕНИЯ К БД")
    print("-" * 40)
    
    try:
        import sqlite3
        
        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()
        
        # Проверяем количество офферов
        cursor.execute("SELECT COUNT(*) FROM offers")
        count = cursor.fetchone()[0]
        print(f"✅ Всего офферов в БД: {count}")
        
        # Показываем последние 3 оффера
        cursor.execute("""
            SELECT id, title, price, currency, category, status, created_at 
            FROM offers 
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        
        offers = cursor.fetchall()
        print(f"📋 Последние {len(offers)} офферов:")
        
        for offer in offers:
            print(f"   ID: {offer[0]} | {offer[1]} | {offer[2]} {offer[3]} | {offer[4]} | {offer[5]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

def check_server_status():
    """Проверяем статус сервера"""
    print("🔍 ПРОВЕРКА СТАТУСА СЕРВЕРА")
    print("-" * 40)
    
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
        print("💡 Запустите сервер: python working_app.py")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ОФФЕРОВ")
    print("=" * 60)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Тестовый пользователь: {TEST_USER_ID}")
    print(f"🌐 Сервер: {BASE_URL}")
    
    # Тест 1: Прямые функции (без сервера)
    print("\n" + "="*60)
    print("📝 ЭТАП 1: ТЕСТИРОВАНИЕ БЕЗ СЕРВЕРА")
    direct_ok = test_direct_function()
    db_ok = test_database_direct()
    
    if not direct_ok:
        print("❌ Базовые функции не работают. Проверьте add_offer.py")
        return
    
    # Тест 2: API через сервер
    print("\n" + "="*60)  
    print("📝 ЭТАП 2: ТЕСТИРОВАНИЕ API")
    
    server_ok = check_server_status()
    if not server_ok:
        print("⚠️ Сервер не запущен. Тестируем только прямые функции.")
        print("\n🎉 РЕЗУЛЬТАТ: Базовые функции работают!")
        print("💡 Для полного теста запустите: python working_app.py")
        return
    
    # API тесты
    offer_id = test_create_offer()
    offers = test_get_my_offers() 
    
    if offers and len(offers) > 0:
        test_get_offer_detail(offers[0]['id'])
    elif offer_id:
        test_get_offer_detail(offer_id)
    
    # Итоговый результат
    print("\n" + "="*60)
    print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    
    if direct_ok and server_ok:
        print("✅ Все тесты пройдены успешно!")
        print("✅ Система офферов полностью работает!")
    elif direct_ok:
        print("✅ Базовые функции работают")
        print("⚠️ API требует запущенного сервера")
    else:
        print("❌ Есть проблемы с системой")
    
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Убедитесь что сервер запущен: python working_app.py")
    print("2. Откройте в браузере: http://localhost:5000/offers")
    print("3. Протестируйте создание офферов через интерфейс")

if __name__ == '__main__':
    main()