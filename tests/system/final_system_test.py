#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ ТЕСТ: Полная проверка системы размещения рекламы
Тестирование с корректной последовательностью команд
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query
from app.telegram.telegram_bot_commands import TelegramBotExtension

def final_system_test():
    """Финальный системный тест"""
    
    print("🎯 ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ РАЗМЕЩЕНИЯ РЕКЛАМЫ")
    print("=" * 60)
    print("Тестируем полный цикл: создание → отклик → размещение → подтверждение")
    print()
    
    bot_extension = TelegramBotExtension()
    test_data = {}
    
    try:
        # ===== ПОДГОТОВКА ДАННЫХ =====
        print("📋 ЭТАП 1: Подготовка тестовых данных")
        print("-" * 40)
        
        # Создаем рекламодателя
        advertiser_id = execute_db_query("""
            INSERT OR REPLACE INTO users 
            (telegram_id, username, first_name, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (111111111, 'test_advertiser', 'Test Advertiser'))
        
        # Создаем владельца канала
        owner_id = execute_db_query("""
            INSERT OR REPLACE INTO users 
            (telegram_id, username, first_name, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (222222222, 'test_owner', 'Channel Owner'))
        
        # Создаем канал
        channel_id = execute_db_query("""
            INSERT INTO channels 
            (title, username, subscriber_count, owner_id, is_verified, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
        """, ('Финальный тест канал', 'final_test_channel', 10000, owner_id))
        
        # Создаем оффер
        offer_id = execute_db_query("""
            INSERT INTO offers 
            (title, description, price, created_by, status, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, ('Финальный тест реклама', 'Тестовая реклама для проверки системы', 5000, advertiser_id, 'active'))
        
        # Создаем отклик
        response_id = execute_db_query("""
            INSERT INTO offer_responses 
            (offer_id, channel_id, user_id, message, channel_username, channel_title, 
             channel_subscribers, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (offer_id, channel_id, owner_id, 'Готов разместить рекламу', 
              'final_test_channel', 'Финальный тест канал', 10000, 'accepted'))
        
        # Создаем размещение
        placement_id = execute_db_query("""
            INSERT INTO offer_placements 
            (response_id, proposal_id, status, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (response_id, response_id, 'pending_placement'))
        
        test_data = {
            'advertiser_id': advertiser_id,
            'owner_id': owner_id,
            'owner_telegram_id': 222222222,
            'channel_id': channel_id,
            'channel_username': 'final_test_channel',
            'offer_id': offer_id,
            'response_id': response_id,
            'placement_id': placement_id
        }
        
        print(f"✅ Созданы тестовые данные:")
        print(f"   👤 Владелец канала: TG_ID={test_data['owner_telegram_id']}")
        print(f"   📺 Канал: @{test_data['channel_username']}")
        print(f"   🎯 Оффер: ID={offer_id}")
        print(f"   📤 Отклик: ID={response_id}")
        print(f"   📍 Размещение: ID={placement_id}")
        
        # ===== ТЕСТ КОМАНД БОТА =====
        print(f"\n🤖 ЭТАП 2: Тестирование команд бота")
        print("-" * 40)
        
        owner_tg_id = test_data['owner_telegram_id']
        
        # Тест 1: /my_channels
        print("1️⃣ Тестируем /my_channels:")
        channels_result = bot_extension.handle_my_channels(owner_tg_id)
        if "Финальный тест канал" in channels_result['text']:
            print("   ✅ Команда работает, канал найден")
        else:
            print("   ❌ Проблема с командой /my_channels")
            
        # Тест 2: /my_proposals  
        print("2️⃣ Тестируем /my_proposals:")
        proposals_result = bot_extension.handle_my_proposals(owner_tg_id)
        if "Финальный тест реклама" in proposals_result['text']:
            print("   ✅ Команда работает, предложение найдено")
        else:
            print("   ❌ Проблема с командой /my_proposals")
        
        # ===== ТЕСТ ПОДТВЕРЖДЕНИЯ БЕЗ ССЫЛКИ =====
        print(f"\n📤 ЭТАП 3: Подтверждение размещения БЕЗ ссылки")
        print("-" * 40)
        
        # Проверяем статус до подтверждения
        before_status = execute_db_query("""
            SELECT status FROM offer_placements WHERE id = ?
        """, (placement_id,), fetch_one=True)
        print(f"📊 Статус ДО подтверждения: {before_status['status']}")
        
        # Выполняем команду /post_published
        result = bot_extension.handle_post_published(owner_tg_id)
        print(f"🤖 Результат команды:")
        
        if "Размещение подтверждено" in result['text']:
            print("   ✅ Размещение успешно подтверждено!")
            
            # Проверяем статус после подтверждения
            after_status = execute_db_query("""
                SELECT status, placement_start FROM offer_placements WHERE id = ?
            """, (placement_id,), fetch_one=True)
            print(f"   📊 Статус ПОСЛЕ: {after_status['status']}")
            print(f"   ⏰ Время размещения: {after_status['placement_start']}")
            
            if after_status['status'] == 'active':
                print("   🎉 Статус корректно изменен на 'active'!")
            else:
                print("   ❌ Статус не изменился корректно")
                
        else:
            print(f"   ❌ Неожиданный результат: {result['text'][:100]}...")
        
        # ===== СОЗДАНИЕ ВТОРОГО РАЗМЕЩЕНИЯ ДЛЯ ТЕСТА С ССЫЛКОЙ =====
        print(f"\n🔗 ЭТАП 4: Тест подтверждения СО ССЫЛКОЙ")
        print("-" * 40)
        
        # Создаем второе размещение для теста со ссылкой
        placement_id_2 = execute_db_query("""
            INSERT INTO offer_placements 
            (response_id, proposal_id, status, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (response_id, response_id, 'pending_placement'))
        
        print(f"📍 Создано второе размещение: ID={placement_id_2}")
        
        # Тестируем команду с ссылкой
        test_url = f"https://t.me/{test_data['channel_username']}/456"
        print(f"🔗 Тестируем с URL: {test_url}")
        
        result_with_link = bot_extension.handle_post_published_with_link(
            owner_tg_id, [test_url]
        )
        
        if "Размещение подтверждено" in result_with_link['text']:
            print("   ✅ Размещение со ссылкой подтверждено!")
            
            # Проверяем обновление
            updated_placement = execute_db_query("""
                SELECT status, post_url, placement_start 
                FROM offer_placements WHERE id = ?
            """, (placement_id_2,), fetch_one=True)
            
            print(f"   📊 Статус: {updated_placement['status']}")
            print(f"   🔗 URL: {updated_placement['post_url']}")
            print(f"   ⏰ Время: {updated_placement['placement_start']}")
            
            if (updated_placement['status'] == 'active' and 
                updated_placement['post_url'] == test_url):
                print("   🎉 Размещение со ссылкой работает корректно!")
            else:
                print("   ❌ Проблема с размещением со ссылкой")
        else:
            print(f"   ❌ Ошибка: {result_with_link['text'][:100]}...")
        
        # ===== ФИНАЛЬНАЯ ПРОВЕРКА =====
        print(f"\n🔍 ЭТАП 5: Финальная проверка системы")
        print("-" * 40)
        
        # Проверяем все размещения
        all_placements = execute_db_query("""
            SELECT p.id, p.status, p.post_url, p.placement_start,
                   o.title as offer_title, r.status as response_status
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.id IN (?, ?)
        """, (placement_id, placement_id_2), fetch_all=True)
        
        print("📊 Результаты всех размещений:")
        success_count = 0
        for placement in all_placements:
            print(f"   📍 Размещение {placement['id']}:")
            print(f"      🎯 Оффер: {placement['offer_title']}")
            print(f"      📊 Статус: {placement['status']}")
            print(f"      🔗 URL: {placement['post_url'] or 'Не указан'}")
            print(f"      ⏰ Время: {placement['placement_start'] or 'Не указано'}")
            
            if placement['status'] == 'active':
                success_count += 1
                print(f"      ✅ Успешно!")
            else:
                print(f"      ❌ Проблема!")
            print()
        
        # ===== ИТОГИ =====
        print("=" * 60)
        print("🎯 ИТОГИ ФИНАЛЬНОГО ТЕСТИРОВАНИЯ")
        print("=" * 60)
        print(f"✅ Успешных размещений: {success_count}/2")
        print(f"📈 Процент успеха: {(success_count/2)*100:.0f}%")
        
        if success_count == 2:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("🚀 Команда /post_published работает корректно!")
            print("✅ Система размещения рекламы полностью функциональна!")
        else:
            print(f"\n⚠️  Есть проблемы с системой")
            print(f"🔧 Требуется дополнительная отладка")
        
        # ===== ОЧИСТКА =====
        print(f"\n🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ")
        print("-" * 40)
        
        # Удаляем в правильном порядке
        execute_db_query("DELETE FROM offer_placements WHERE id IN (?, ?)", (placement_id, placement_id_2))
        execute_db_query("DELETE FROM offer_responses WHERE id = ?", (response_id,))
        execute_db_query("DELETE FROM offers WHERE id = ?", (offer_id,))
        execute_db_query("DELETE FROM channels WHERE id = ?", (channel_id,))
        execute_db_query("DELETE FROM users WHERE id IN (?, ?)", (advertiser_id, owner_id))
        
        print("✅ Тестовые данные очищены")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_system_test()