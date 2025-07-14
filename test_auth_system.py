#!/usr/bin/env python3
"""
Тестирование новой единой системы авторизации
"""
import os
import sys
import sqlite3
import requests
import json

# Добавляем путь к проекту
sys.path.append('/mnt/d/Project')

def test_auth_system():
    """Тестирование работы авторизации"""
    
    print("🔍 Тестирование единой системы авторизации")
    print("=" * 60)
    
    # Тест 1: Базовая работа с базой данных
    print("\n1. Тест базы данных:")
    try:
        conn = sqlite3.connect('/mnt/d/Project/telegram_mini_app.db')
        cursor = conn.cursor()
        
        # Проверяем наличие пользователя с telegram_id = 1
        cursor.execute('SELECT id, telegram_id, username FROM users WHERE telegram_id = 1')
        user = cursor.fetchone()
        if user:
            print(f"   ✅ Пользователь найден: db_id={user[0]}, telegram_id={user[1]}, username={user[2]}")
        else:
            print("   ❌ Пользователь с telegram_id=1 не найден")
            
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
    
    # Тест 2: Проверка оффера
    print("\n2. Тест оффера:")
    try:
        conn = sqlite3.connect('/mnt/d/Project/telegram_mini_app.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, created_by FROM offers WHERE id = 4')
        offer = cursor.fetchone()
        if offer:
            print(f"   ✅ Оффер найден: id={offer[0]}, title={offer[1]}, created_by={offer[2]}")
        else:
            print("   ❌ Оффер с id=4 не найден")
            
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
    
    # Тест 3: Проверка каналов
    print("\n3. Тест каналов:")
    try:
        conn = sqlite3.connect('/mnt/d/Project/telegram_mini_app.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, owner_id FROM channels WHERE is_verified = 1')
        channels = cursor.fetchall()
        print(f"   ✅ Найдено верифицированных каналов: {len(channels)}")
        for ch in channels:
            print(f"      - ID: {ch[0]}, Title: {ch[1]}, Owner: {ch[2]}")
            
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")
    
    # Тест 4: Симуляция HTTP запроса
    print("\n4. Тест HTTP запроса:")
    try:
        # Создаем простой тестовый запрос
        url = 'http://localhost:5000/api/offers_management/4/recommended-channels'
        headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': '1'  # telegram_id пользователя
        }
        
        print(f"   🔍 URL: {url}")
        print(f"   📋 Headers: {headers}")
        
        # Если сервер запущен, попробуем запрос
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   📡 Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Успешный ответ: {data.get('total_channels', 0)} каналов")
            else:
                print(f"   ❌ Ошибка: {response.text}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Сервер не запущен, пропускаем HTTP тест")
            
    except Exception as e:
        print(f"   ❌ Ошибка HTTP: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Тестирование завершено")

if __name__ == '__main__':
    test_auth_system()