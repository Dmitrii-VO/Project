#!/usr/bin/env python3
"""
Тестирование исправлений для отображения офферов
"""
import os
import sys
import sqlite3
import requests
import json

# Добавляем путь к проекту
sys.path.append('/mnt/d/Project')

def test_offers_display_fix():
    """Тестирование исправлений для отображения офферов"""
    
    print("🔍 Тестирование исправлений для отображения офферов")
    print("=" * 60)
    
    # Тест 1: Проверка связи пользователей и офферов
    print("\n1. Проверка связи пользователей и офферов:")
    try:
        conn = sqlite3.connect('/mnt/d/Project/telegram_mini_app.db')
        cursor = conn.cursor()
        
        # Проверяем пользователя с telegram_id = 373086959
        cursor.execute('SELECT id, telegram_id, username FROM users WHERE telegram_id = 373086959')
        user = cursor.fetchone()
        if user:
            print(f"   ✅ Пользователь: db_id={user[0]}, telegram_id={user[1]}, username={user[2]}")
            
            # Проверяем его офферы
            cursor.execute('SELECT id, title, created_by FROM offers WHERE created_by = ? ORDER BY created_at DESC', (user[0],))
            offers = cursor.fetchall()
            print(f"   ✅ Офферы пользователя db_id={user[0]}: {len(offers)} шт.")
            for offer in offers:
                print(f"      - ID: {offer[0]}, Title: {offer[1]}, Created by: {offer[2]}")
        else:
            print("   ❌ Пользователь с telegram_id=373086959 не найден")
            
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
    
    # Тест 2: Проверка последних офферов
    print("\n2. Проверка последних офферов:")
    try:
        conn = sqlite3.connect('/mnt/d/Project/telegram_mini_app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.id, o.title, o.created_by, u.telegram_id, u.username
            FROM offers o
            JOIN users u ON o.created_by = u.id
            ORDER BY o.created_at DESC
            LIMIT 5
        ''')
        offers = cursor.fetchall()
        print(f"   ✅ Последние офферы:")
        for offer in offers:
            print(f"      - Offer ID: {offer[0]}, Title: {offer[1]}, Created by db_id: {offer[2]}, telegram_id: {offer[3]}, username: {offer[4]}")
            
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
    
    # Тест 3: Симуляция API запроса "Мои офферы"
    print("\n3. Тест API 'Мои офферы':")
    try:
        url = 'http://localhost:5000/api/offers/my'
        headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': '373086959'  # Реальный telegram_id
        }
        
        print(f"   🔍 URL: {url}")
        print(f"   📋 Headers: {headers}")
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   📡 Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Успешный ответ: {data.get('count', 0)} офферов из {data.get('total_count', 0)} всего")
                if 'telegram_id' in data:
                    print(f"   📋 Telegram ID в ответе: {data['telegram_id']}")
                if 'user_db_id' in data:
                    print(f"   📋 User DB ID в ответе: {data['user_db_id']}")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Сервер не запущен, пропускаем HTTP тест")
            
    except Exception as e:
        print(f"   ❌ Ошибка HTTP: {e}")
    
    # Тест 4: Симуляция API запроса рекомендаций
    print("\n4. Тест API рекомендаций каналов:")
    try:
        url = 'http://localhost:5000/api/offers_management/5/recommended-channels'
        headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': '373086959'  # Реальный telegram_id
        }
        
        print(f"   🔍 URL: {url}")
        print(f"   📋 Headers: {headers}")
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   📡 Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Успешный ответ: {data.get('total_channels', 0)} каналов")
            elif response.status_code == 403:
                print(f"   ❌ 403 Forbidden: {response.text}")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Сервер не запущен, пропускаем HTTP тест")
            
    except Exception as e:
        print(f"   ❌ Ошибка HTTP: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Тестирование завершено")

if __name__ == '__main__':
    test_offers_display_fix()