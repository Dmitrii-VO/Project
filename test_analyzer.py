#!/usr/bin/env python3
"""
Тестовый скрипт для проверки анализатора каналов
Проверяет работу /api/analyzer/analyze
"""

import requests
import json
import time
from datetime import datetime

# Конфигурация
BASE_URL = "http://127.0.0.1:5000"  # Измените на ваш URL
ANALYZER_URL = f"{BASE_URL}/api/analyzer"

def test_analyzer_endpoint():
    """Тестирование основного эндпоинта анализатора"""
    print("🧪 ТЕСТИРОВАНИЕ АНАЛИЗАТОРА КАНАЛОВ")
    print("=" * 60)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL сервера: {BASE_URL}")
    print(f"🔗 Эндпоинт: {ANALYZER_URL}")
    print()
    
    # Тестовые каналы для проверки
    test_channels = [
        # Реальные публичные каналы (должны работать)
        "https://t.me/durov",           # Официальный канал Дурова
        "https://t.me/telegram",        # Официальный канал Telegram
        "t.me/vc",                     # VC.ru
        "@habr_com",                   # Хабр
        
        # Проблемный канал из вашей базы
        "zxzxczcczc",                  # Тот самый канал с 0 подписчиков
        
        # Неправильные ссылки (должны вернуть ошибку)
        "invalid_link",
        "https://invalid.com/test"
    ]
    
    results = []
    
    for i, channel_url in enumerate(test_channels, 1):
        print(f"\n📺 ТЕСТ {i}/{len(test_channels)}: {channel_url}")
        print("-" * 40)
        
        try:
            # Отправляем запрос к анализатору
            start_time = time.time()
            
            response = requests.post(
                f"{ANALYZER_URL}/analyze",
                json={"channel_url": channel_url},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            print(f"⏱️  Время ответа: {response_time}ms")
            print(f"📊 Статус код: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ УСПЕХ!")
                
                if data.get('success'):
                    channel_data = data.get('data', {})
                    print(f"📺 Название: {channel_data.get('title', 'Не найдено')}")
                    print(f"👤 Username: {channel_data.get('username', 'Не найден')}")
                    print(f"👥 Подписчики: {channel_data.get('raw_subscriber_count', 0)}")
                    print(f"📊 Форматированные: {channel_data.get('subscribers', 'Не найдено')}")
                    print(f"🏷️  Категория: {channel_data.get('category', 'Не определена')}")
                    print(f"📡 Источник данных: {data.get('data_source', 'Неизвестно')}")
                    
                    results.append({
                        'channel': channel_url,
                        'success': True,
                        'subscribers': channel_data.get('raw_subscriber_count', 0),
                        'source': data.get('data_source'),
                        'response_time': response_time
                    })
                else:
                    print(f"❌ Ошибка: {data.get('error', 'Неизвестная ошибка')}")
                    results.append({
                        'channel': channel_url,
                        'success': False,
                        'error': data.get('error'),
                        'response_time': response_time
                    })
            else:
                print(f"❌ HTTP Ошибка: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📄 Ответ: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📄 Текст ответа: {response.text[:200]}...")
                
                results.append({
                    'channel': channel_url,
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'response_time': response_time
                })
                
        except requests.exceptions.Timeout:
            print("⏰ TIMEOUT - сервер не отвечает больше 30 секунд")
            results.append({
                'channel': channel_url,
                'success': False,
                'error': 'Timeout',
                'response_time': '>30000'
            })
            
        except requests.exceptions.ConnectionError:
            print("🚫 CONNECTION ERROR - сервер недоступен")
            results.append({
                'channel': channel_url,
                'success': False,
                'error': 'Connection Error',
                'response_time': 0
            })
            
        except Exception as e:
            print(f"💥 НЕОЖИДАННАЯ ОШИБКА: {e}")
            results.append({
                'channel': channel_url,
                'success': False,
                'error': str(e),
                'response_time': 0
            })
    
    # Сводка результатов
    print("\n" + "=" * 60)
    print("📊 СВОДКА РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ Успешных: {len(successful)}/{len(results)}")
    print(f"❌ Неудачных: {len(failed)}/{len(results)}")
    
    if successful:
        print("\n🎉 УСПЕШНЫЕ ТЕСТЫ:")
        for result in successful:
            print(f"  ✅ {result['channel']} -> {result['subscribers']} подписчиков ({result['source']}) [{result['response_time']}ms]")
    
    if failed:
        print("\n💥 НЕУДАЧНЫЕ ТЕСТЫ:")
        for result in failed:
            print(f"  ❌ {result['channel']} -> {result['error']} [{result['response_time']}ms]")
    
    return results

def test_analyzer_stats():
    """Тестирование статистики анализатора"""
    print(f"\n🔍 ПРОВЕРКА СТАТИСТИКИ АНАЛИЗАТОРА")
    print("-" * 40)
    
    try:
        response = requests.get(f"{ANALYZER_URL}/stats", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('stats', {})
                print("✅ Статистика получена:")
                print(f"  📦 Размер кэша: {stats.get('cache_size', 0)}")
                print(f"  ⏰ TTL кэша: {stats.get('cache_ttl_seconds', 0)} секунд")
                print(f"  🤖 Bot Token настроен: {stats.get('bot_token_configured', False)}")
                return True
            else:
                print(f"❌ Ошибка в ответе: {data.get('error')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    
    return False

def test_server_availability():
    """Проверка доступности сервера"""
    print("🌐 ПРОВЕРКА ДОСТУПНОСТИ СЕРВЕРА")
    print("-" * 40)
    
    try:
        # Проверяем главную страницу
        response = requests.get(BASE_URL, timeout=10)
        print(f"📊 Главная страница: {response.status_code}")
        
        # Проверяем API конфигурации
        response = requests.get(f"{BASE_URL}/api/config", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("✅ API работает")
            print(f"  📱 Название: {config.get('config', {}).get('app_name', 'Неизвестно')}")
            print(f"  🔢 Версия: {config.get('config', {}).get('version', 'Неизвестно')}")
            bot_configured = config.get('config', {}).get('telegram', {}).get('bot_configured', False)
            print(f"  🤖 Bot настроен: {bot_configured}")
            return True
        else:
            print(f"❌ API недоступен: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Сервер недоступен: {e}")
    
    return False

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ АНАЛИЗАТОРА КАНАЛОВ")
    print("=" * 60)
    
    # 1. Проверяем доступность сервера
    if not test_server_availability():
        print("\n🚫 СЕРВЕР НЕДОСТУПЕН! Убедитесь что приложение запущено на", BASE_URL)
        exit(1)
    
    # 2. Проверяем статистику анализатора
    test_analyzer_stats()
    
    # 3. Тестируем основной функционал
    results = test_analyzer_endpoint()
    
    print(f"\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Определяем общий результат
    success_rate = len([r for r in results if r['success']]) / len(results) * 100
    
    if success_rate >= 70:
        print(f"🎉 РЕЗУЛЬТАТ: ХОРОШО ({success_rate:.1f}% успешных тестов)")
    elif success_rate >= 30:
        print(f"⚠️  РЕЗУЛЬТАТ: УДОВЛЕТВОРИТЕЛЬНО ({success_rate:.1f}% успешных тестов)")
    else:
        print(f"❌ РЕЗУЛЬТАТ: ПЛОХО ({success_rate:.1f}% успешных тестов)")
