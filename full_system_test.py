#!/usr/bin/env python3
"""
Полный тест системы: от создания оффера до подтверждения размещения
End-to-End тестирование всего процесса
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query
from app.telegram.telegram_bot_commands import TelegramBotExtension

class FullSystemTester:
    def __init__(self):
        self.test_data = {}
        self.bot_extension = TelegramBotExtension()
        print("🧪 ПОЛНЫЙ ТЕСТ СИСТЕМЫ РАЗМЕЩЕНИЯ РЕКЛАМЫ")
        print("=" * 60)
        
    def step_1_create_advertiser(self):
        """Шаг 1: Создание рекламодателя"""
        print("\n📝 ШАГ 1: Создание рекламодателя")
        print("-" * 30)
        
        try:
            # Создаем тестового рекламодателя
            advertiser_data = {
                'telegram_id': 999888777,
                'username': 'test_advertiser',
                'first_name': 'Test Advertiser',
                'last_name': 'User'
            }
            
            advertiser_id = execute_db_query("""
                INSERT OR REPLACE INTO users 
                (telegram_id, username, first_name, last_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                advertiser_data['telegram_id'],
                advertiser_data['username'], 
                advertiser_data['first_name'],
                advertiser_data['last_name']
            ))
            
            self.test_data['advertiser_id'] = advertiser_id
            self.test_data['advertiser_telegram_id'] = advertiser_data['telegram_id']
            
            print(f"✅ Рекламодатель создан: ID={advertiser_id}, TG_ID={advertiser_data['telegram_id']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания рекламодателя: {e}")
            return False
    
    def step_2_create_channel_owner(self):
        """Шаг 2: Создание владельца канала"""
        print("\n📺 ШАГ 2: Создание владельца канала")
        print("-" * 30)
        
        try:
            # Создаем владельца канала
            owner_data = {
                'telegram_id': 888777666,
                'username': 'test_channel_owner',
                'first_name': 'Channel Owner',
                'last_name': 'Test'
            }
            
            owner_id = execute_db_query("""
                INSERT OR REPLACE INTO users 
                (telegram_id, username, first_name, last_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                owner_data['telegram_id'],
                owner_data['username'],
                owner_data['first_name'], 
                owner_data['last_name']
            ))
            
            self.test_data['owner_id'] = owner_id
            self.test_data['owner_telegram_id'] = owner_data['telegram_id']
            
            print(f"✅ Владелец канала создан: ID={owner_id}, TG_ID={owner_data['telegram_id']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания владельца канала: {e}")
            return False
    
    def step_3_create_channel(self):
        """Шаг 3: Создание канала"""
        print("\n📢 ШАГ 3: Создание и верификация канала")
        print("-" * 30)
        
        try:
            # Создаем канал
            channel_data = {
                'title': 'Тестовый канал для рекламы',
                'username': 'test_ad_channel_demo',
                'description': 'Канал для тестирования системы размещения рекламы',
                'subscriber_count': 5000,
                'category': 'technology',
                'owner_id': self.test_data['owner_id']
            }
            
            channel_id = execute_db_query("""
                INSERT INTO channels 
                (title, username, description, subscriber_count, category, owner_id, 
                 is_verified, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                channel_data['title'],
                channel_data['username'],
                channel_data['description'],
                channel_data['subscriber_count'],
                channel_data['category'],
                channel_data['owner_id']
            ))
            
            self.test_data['channel_id'] = channel_id
            self.test_data['channel_username'] = channel_data['username']
            
            print(f"✅ Канал создан: ID={channel_id}, @{channel_data['username']}")
            print(f"   📊 Подписчиков: {channel_data['subscriber_count']}")
            print(f"   ✅ Статус: Верифицирован и активен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания канала: {e}")
            return False
    
    def step_4_create_offer(self):
        """Шаг 4: Создание оффера"""
        print("\n🎯 ШАГ 4: Создание оффера")
        print("-" * 30)
        
        try:
            offer_data = {
                'title': 'Реклама нового IT продукта',
                'description': 'Ищем каналы для размещения рекламы инновационного IT решения',
                'content': 'Текст рекламного поста будет предоставлен после согласования',
                'budget_total': 10000,
                'price': 2000,
                'category': 'technology',
                'target_audience': 'IT специалисты, разработчики',
                'created_by': self.test_data['advertiser_id'],
                'status': 'active'
            }
            
            offer_id = execute_db_query("""
                INSERT INTO offers 
                (title, description, content, budget_total, price, category, 
                 target_audience, created_by, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                offer_data['title'],
                offer_data['description'],
                offer_data['content'],
                offer_data['budget_total'],
                offer_data['price'],
                offer_data['category'],
                offer_data['target_audience'],
                offer_data['created_by'],
                offer_data['status']
            ))
            
            self.test_data['offer_id'] = offer_id
            
            print(f"✅ Оффер создан: ID={offer_id}")
            print(f"   📋 Название: {offer_data['title']}")
            print(f"   💰 Бюджет: {offer_data['budget_total']} руб.")
            print(f"   💳 Цена за размещение: {offer_data['price']} руб.")
            print(f"   🎯 Категория: {offer_data['category']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания оффера: {e}")
            return False
    
    def step_5_create_response(self):
        """Шаг 5: Создание отклика на оффер"""
        print("\n📤 ШАГ 5: Создание отклика владельца канала")
        print("-" * 30)
        
        try:
            response_data = {
                'offer_id': self.test_data['offer_id'],
                'channel_id': self.test_data['channel_id'],
                'user_id': self.test_data['owner_id'],
                'message': 'Готов разместить рекламу в моем канале. Условия устраивают.',
                'channel_username': self.test_data['channel_username'],
                'channel_title': 'Тестовый канал для рекламы',
                'channel_subscribers': 5000,
                'status': 'pending'
            }
            
            response_id = execute_db_query("""
                INSERT INTO offer_responses 
                (offer_id, channel_id, user_id, message, channel_username, channel_title, 
                 channel_subscribers, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                response_data['offer_id'],
                response_data['channel_id'],
                response_data['user_id'],
                response_data['message'],
                response_data['channel_username'],
                response_data['channel_title'],
                response_data['channel_subscribers'],
                response_data['status']
            ))
            
            self.test_data['response_id'] = response_id
            
            print(f"✅ Отклик создан: ID={response_id}")
            print(f"   📺 Канал: @{self.test_data['channel_username']}")
            print(f"   👥 Подписчиков: {response_data['channel_subscribers']}")
            print(f"   📋 Статус: {response_data['status']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания отклика: {e}")
            return False
    
    def step_6_accept_response(self):
        """Шаг 6: Принятие отклика рекламодателем"""
        print("\n✅ ШАГ 6: Принятие отклика рекламодателем")
        print("-" * 30)
        
        try:
            # Обновляем статус отклика на accepted
            execute_db_query("""
                UPDATE offer_responses 
                SET status = 'accepted', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (self.test_data['response_id'],))
            
            print(f"✅ Отклик принят: ID={self.test_data['response_id']}")
            print(f"   📝 Статус изменен на: accepted")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка принятия отклика: {e}")
            return False
    
    def step_7_create_placement(self):
        """Шаг 7: Создание размещения"""
        print("\n📍 ШАГ 7: Создание записи размещения")
        print("-" * 30)
        
        try:
            placement_data = {
                'response_id': self.test_data['response_id'],
                'proposal_id': self.test_data['response_id'],  # В текущей системе они совпадают
                'status': 'pending_placement'
            }
            
            placement_id = execute_db_query("""
                INSERT INTO offer_placements 
                (response_id, proposal_id, status, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                placement_data['response_id'],
                placement_data['proposal_id'],
                placement_data['status']
            ))
            
            self.test_data['placement_id'] = placement_id
            
            print(f"✅ Размещение создано: ID={placement_id}")
            print(f"   📝 Статус: {placement_data['status']}")
            print(f"   🔗 Response ID: {placement_data['response_id']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания размещения: {e}")
            return False
    
    def step_8_test_bot_commands(self):
        """Шаг 8: Тестирование команд бота"""
        print("\n🤖 ШАГ 8: Тестирование команд Telegram бота")
        print("-" * 30)
        
        try:
            owner_telegram_id = self.test_data['owner_telegram_id']
            
            # Тест команды /my_channels
            print("📢 Тестируем /my_channels...")
            channels_result = self.bot_extension.handle_my_channels(owner_telegram_id)
            if "Ваши каналы" in channels_result['text']:
                print("   ✅ /my_channels работает корректно")
            else:
                print("   ❌ /my_channels: проблема с отображением каналов")
            
            # Тест команды /my_proposals  
            print("📋 Тестируем /my_proposals...")
            proposals_result = self.bot_extension.handle_my_proposals(owner_telegram_id)
            if "предложения" in proposals_result['text'].lower():
                print("   ✅ /my_proposals работает корректно")
            else:
                print("   ❌ /my_proposals: проблема с отображением предложений")
            
            # Тест команды /post_published (до размещения)
            print("📤 Тестируем /post_published (до размещения)...")
            post_result = self.bot_extension.handle_post_published(owner_telegram_id)
            if "Размещение подтверждено" in post_result['text']:
                print("   ✅ /post_published: найдено размещение для подтверждения!")
                self.test_data['post_confirmed'] = True
            else:
                print("   ℹ️ /post_published: нет размещений для подтверждения (ожидаемо)")
                self.test_data['post_confirmed'] = False
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка тестирования команд бота: {e}")
            return False
    
    def step_9_confirm_placement(self):
        """Шаг 9: Подтверждение размещения"""
        print("\n📤 ШАГ 9: Подтверждение размещения владельцем канала")
        print("-" * 30)
        
        try:
            owner_telegram_id = self.test_data['owner_telegram_id']
            test_post_url = f"https://t.me/{self.test_data['channel_username']}/123"
            
            # Тестируем команду /post_published с ссылкой
            print(f"🔗 Подтверждаем размещение с ссылкой: {test_post_url}")
            
            result = self.bot_extension.handle_post_published_with_link(
                owner_telegram_id, [test_post_url]
            )
            
            if "Размещение подтверждено" in result['text']:
                print("   ✅ Размещение успешно подтверждено!")
                print("   📤 Рекламодатель уведомлен")
                print("   📊 Отслеживание активировано")
                
                # Проверяем обновление в БД
                updated_placement = execute_db_query("""
                    SELECT status, post_url, placement_start 
                    FROM offer_placements 
                    WHERE id = ?
                """, (self.test_data['placement_id'],), fetch_one=True)
                
                if updated_placement:
                    print(f"   📝 Статус в БД: {updated_placement['status']}")
                    print(f"   🔗 URL поста: {updated_placement['post_url']}")
                    print(f"   ⏰ Время размещения: {updated_placement['placement_start']}")
                
                return True
            else:
                print(f"   ❌ Ошибка подтверждения: {result['text'][:100]}...")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка подтверждения размещения: {e}")
            return False
    
    def step_10_verify_final_state(self):
        """Шаг 10: Проверка финального состояния"""
        print("\n🔍 ШАГ 10: Проверка финального состояния системы")
        print("-" * 30)
        
        try:
            # Проверяем статусы в БД
            placement_status = execute_db_query("""
                SELECT p.status, p.post_url, p.placement_start,
                       r.status as response_status, o.status as offer_status
                FROM offer_placements p
                JOIN offer_responses r ON p.response_id = r.id  
                JOIN offers o ON r.offer_id = o.id
                WHERE p.id = ?
            """, (self.test_data['placement_id'],), fetch_one=True)
            
            if placement_status:
                print("📊 Финальное состояние:")
                print(f"   🎯 Оффер: {placement_status['offer_status']}")
                print(f"   📤 Отклик: {placement_status['response_status']}")
                print(f"   📍 Размещение: {placement_status['status']}")
                print(f"   🔗 URL поста: {placement_status['post_url'] or 'Не указан'}")
                print(f"   ⏰ Время размещения: {placement_status['placement_start'] or 'Не указано'}")
                
                # Проверяем, что процесс завершен успешно
                if (placement_status['offer_status'] in ['active', 'started', 'in_progress'] and
                    placement_status['response_status'] == 'accepted' and 
                    placement_status['status'] == 'active'):
                    print("\n🎉 УСПЕХ! Полный цикл размещения рекламы завершен корректно!")
                    return True
                else:
                    print("\n⚠️ Есть несоответствия в статусах")
                    return False
            else:
                print("❌ Не удалось получить финальное состояние")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка проверки финального состояния: {e}")
            return False
    
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        print("\n🧹 ОЧИСТКА: Удаление тестовых данных")
        print("-" * 30)
        
        try:
            # Удаляем в правильном порядке (учитывая foreign keys)
            if 'placement_id' in self.test_data:
                execute_db_query("DELETE FROM offer_placements WHERE id = ?", 
                                (self.test_data['placement_id'],))
                print("   ✅ Размещение удалено")
            
            if 'response_id' in self.test_data:
                execute_db_query("DELETE FROM offer_responses WHERE id = ?", 
                                (self.test_data['response_id'],))
                print("   ✅ Отклик удален")
            
            if 'offer_id' in self.test_data:
                execute_db_query("DELETE FROM offers WHERE id = ?", 
                                (self.test_data['offer_id'],))
                print("   ✅ Оффер удален")
            
            if 'channel_id' in self.test_data:
                execute_db_query("DELETE FROM channels WHERE id = ?", 
                                (self.test_data['channel_id'],))
                print("   ✅ Канал удален")
            
            if 'advertiser_id' in self.test_data:
                execute_db_query("DELETE FROM users WHERE id = ?", 
                                (self.test_data['advertiser_id'],))
                print("   ✅ Рекламодатель удален")
            
            if 'owner_id' in self.test_data:
                execute_db_query("DELETE FROM users WHERE id = ?", 
                                (self.test_data['owner_id'],))
                print("   ✅ Владелец канала удален")
            
            print("🧹 Очистка завершена")
            
        except Exception as e:
            print(f"❌ Ошибка очистки: {e}")
    
    def run_full_test(self):
        """Запуск полного теста"""
        start_time = datetime.now()
        success_steps = 0
        total_steps = 10
        
        steps = [
            self.step_1_create_advertiser,
            self.step_2_create_channel_owner, 
            self.step_3_create_channel,
            self.step_4_create_offer,
            self.step_5_create_response,
            self.step_6_accept_response,
            self.step_7_create_placement,
            self.step_8_test_bot_commands,
            self.step_9_confirm_placement,
            self.step_10_verify_final_state
        ]
        
        for step in steps:
            if step():
                success_steps += 1
            else:
                print(f"\n❌ ТЕСТ ОСТАНОВЛЕН НА ШАГЕ: {step.__name__}")
                break
            
            time.sleep(0.5)  # Небольшая пауза между шагами
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ПОЛНОГО ТЕСТИРОВАНИЯ")
        print("=" * 60)
        print(f"⏱️  Время выполнения: {duration.total_seconds():.2f} секунд")
        print(f"✅ Успешных шагов: {success_steps}/{total_steps}")
        print(f"📈 Процент успеха: {(success_steps/total_steps)*100:.1f}%")
        
        if success_steps == total_steps:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("🚀 Система размещения рекламы работает корректно!")
        else:
            print(f"\n⚠️  Тест не завершен полностью")
            print(f"🔧 Требуется исправление на шаге {success_steps + 1}")
        
        # Предлагаем очистку  
        print("\n🧹 Тестовые данные:")
        print("💾 Данные сохранены для анализа")
        print("🔍 Созданные объекты:")
        for key, value in self.test_data.items():
            print(f"   {key}: {value}")
        print("\n⚠️  Для очистки запустите cleanup_test_data() вручную")

def main():
    """Главная функция"""
    tester = FullSystemTester()
    tester.run_full_test()

if __name__ == "__main__":
    main()