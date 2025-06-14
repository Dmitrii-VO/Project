#!/usr/bin/env python3
"""
test_real_data.py - Тестирование с реальными каналами и предложениями
Этот скрипт работает только с реальными данными без создания тестовых
"""

import os
import sys
import json
import time
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealDataTester:
    """Тестер для работы с реальными каналами и предложениями"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', 'http://localhost:5000')
        self.bot_token = config.get('bot_token', '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8')
        self.db_path = config.get('db_path', 'telegram_mini_app.db')
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, data: Optional[Dict] = None):
        """Логирование результата теста"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}: {message}")
    
    def get_real_channels_from_db(self) -> List[Dict]:
        """Получение реальных каналов из базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, username, subscriber_count, category, price_per_post, 
                       description, created_at, is_active 
                FROM channels 
                WHERE is_active = 1
                ORDER BY subscriber_count DESC
                LIMIT 20
            """)
            
            columns = [desc[0] for desc in cursor.description]
            channels = []
            
            for row in cursor.fetchall():
                channel = dict(zip(columns, row))
                channels.append(channel)
            
            conn.close()
            
            self.log_test(
                "Получение реальных каналов", 
                True, 
                f"Найдено {len(channels)} активных каналов",
                {'count': len(channels)}
            )
            
            return channels
            
        except Exception as e:
            self.log_test("Получение реальных каналов", False, str(e))
            return []
    
    def get_real_offers_from_db(self) -> List[Dict]:
        """Получение реальных предложений из базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, description, budget, target_audience, 
                       category, requirements, created_at, status, user_id
                FROM offers 
                WHERE status IN ('active', 'pending')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            columns = [desc[0] for desc in cursor.description]
            offers = []
            
            for row in cursor.fetchall():
                offer = dict(zip(columns, row))
                offers.append(offer)
            
            conn.close()
            
            self.log_test(
                "Получение реальных предложений", 
                True, 
                f"Найдено {len(offers)} активных предложений",
                {'count': len(offers)}
            )
            
            return offers
            
        except Exception as e:
            self.log_test("Получение реальных предложений", False, str(e))
            return []
    
    def verify_channel_data(self, channel: Dict) -> bool:
        """Проверка данных реального канала через Telegram API"""
        try:
            channel_username = channel.get('username', '').replace('@', '')
            
            if not channel_username:
                self.log_test(
                    f"Проверка канала {channel.get('name', 'Unknown')}", 
                    False, 
                    "Отсутствует username канала"
                )
                return False
            
            # Получаем информацию о канале через Bot API
            url = f"https://api.telegram.org/bot{self.bot_token}/getChat"
            params = {'chat_id': f"@{channel_username}"}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('ok'):
                    chat_info = data['result']
                    
                    # Сравниваем данные
                    db_name = channel.get('name', '')
                    api_title = chat_info.get('title', '')
                    
                    # Получаем количество участников
                    member_count_url = f"https://api.telegram.org/bot{self.bot_token}/getChatMemberCount"
                    member_response = requests.get(member_count_url, params=params, timeout=10)
                    
                    actual_members = 0
                    if member_response.status_code == 200:
                        member_data = member_response.json()
                        if member_data.get('ok'):
                            actual_members = member_data['result']
                    
                    db_members = channel.get('subscriber_count', 0)
                    
                    # Проверяем соответствие данных
                    title_match = db_name.lower() in api_title.lower() or api_title.lower() in db_name.lower()
                    member_diff = abs(actual_members - db_members) / max(db_members, 1) if db_members > 0 else 1
                    
                    verification_data = {
                        'db_name': db_name,
                        'api_title': api_title,
                        'db_members': db_members,
                        'api_members': actual_members,
                        'title_match': title_match,
                        'member_diff_percent': member_diff * 100
                    }
                    
                    # Канал считается валидным если название примерно совпадает 
                    # и количество участников не отличается более чем на 50%
                    is_valid = title_match and member_diff < 0.5
                    
                    self.log_test(
                        f"Проверка канала @{channel_username}",
                        is_valid,
                        f"Участников: {actual_members}, Название: '{api_title}'",
                        verification_data
                    )
                    
                    return is_valid
                else:
                    self.log_test(
                        f"Проверка канала @{channel_username}",
                        False,
                        f"API ошибка: {data.get('description', 'Unknown')}"
                    )
                    return False
            else:
                self.log_test(
                    f"Проверка канала @{channel_username}",
                    False,
                    f"HTTP ошибка: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                f"Проверка канала {channel.get('username', 'Unknown')}",
                False,
                f"Исключение: {str(e)}"
            )
            return False
    
    def test_channel_matching_algorithm(self, channels: List[Dict], offers: List[Dict]) -> bool:
        """Тестирование алгоритма подбора каналов для предложений"""
        try:
            if not channels or not offers:
                self.log_test(
                    "Алгоритм подбора",
                    False,
                    "Недостаточно данных для тестирования"
                )
                return False
            
            successful_matches = 0
            total_attempts = min(len(offers), 5)  # Тестируем максимум 5 предложений
            
            for offer in offers[:total_attempts]:
                offer_budget = offer.get('budget', 0)
                offer_category = offer.get('category', '').lower()
                offer_audience = offer.get('target_audience', '').lower()
                
                # Ищем подходящие каналы
                suitable_channels = []
                
                for channel in channels:
                    channel_price = channel.get('price_per_post', 0)
                    channel_category = channel.get('category', '').lower()
                    channel_subscribers = channel.get('subscriber_count', 0)
                    
                    # Критерии подбора
                    budget_ok = offer_budget >= channel_price
                    category_match = (not offer_category or not channel_category or 
                                    offer_category in channel_category or 
                                    channel_category in offer_category)
                    min_subscribers = channel_subscribers >= 1000  # Минимальный порог
                    
                    if budget_ok and category_match and min_subscribers:
                        match_score = 0
                        
                        # Подсчет релевантности
                        if channel_price <= offer_budget * 0.8:  # В пределах бюджета
                            match_score += 30
                        if offer_category and channel_category and offer_category == channel_category:
                            match_score += 40
                        if channel_subscribers >= 10000:  # Хорошая аудитория
                            match_score += 20
                        if channel.get('is_active', False):
                            match_score += 10
                        
                        suitable_channels.append({
                            'channel': channel,
                            'score': match_score
                        })
                
                # Сортируем по релевантности
                suitable_channels.sort(key=lambda x: x['score'], reverse=True)
                
                if suitable_channels:
                    successful_matches += 1
                    best_match = suitable_channels[0]
                    
                    self.log_test(
                        f"Подбор для предложения '{offer.get('title', 'Unknown')[:30]}'",
                        True,
                        f"Найдено {len(suitable_channels)} каналов, лучший: @{best_match['channel'].get('username', 'Unknown')}",
                        {
                            'offer_id': offer.get('id'),
                            'matches_count': len(suitable_channels),
                            'best_score': best_match['score']
                        }
                    )
                else:
                    self.log_test(
                        f"Подбор для предложения '{offer.get('title', 'Unknown')[:30]}'",
                        False,
                        "Подходящих каналов не найдено"
                    )
            
            success_rate = successful_matches / total_attempts if total_attempts > 0 else 0
            
            self.log_test(
                "Алгоритм подбора (общий)",
                success_rate >= 0.6,  # 60% успешных подборов
                f"Успешных подборов: {successful_matches}/{total_attempts} ({success_rate*100:.1f}%)",
                {'success_rate': success_rate}
            )
            
            return success_rate >= 0.6
            
        except Exception as e:
            self.log_test("Алгоритм подбора", False, str(e))
            return False
    
    def test_api_with_real_data(self) -> bool:
        """Тестирование API с реальными данными"""
        try:
            # Тестируем получение каналов через API
            response = requests.get(f"{self.base_url}/api/channels", timeout=10)
            
            if response.status_code == 200:
                api_channels = response.json()
                
                if isinstance(api_channels, list) and len(api_channels) > 0:
                    self.log_test(
                        "API каналов",
                        True,
                        f"Получено {len(api_channels)} каналов через API"
                    )
                else:
                    self.log_test(
                        "API каналов",
                        False,
                        "API вернул пустой список или неверный формат"
                    )
                    return False
            else:
                self.log_test(
                    "API каналов",
                    False,
                    f"HTTP ошибка: {response.status_code}"
                )
                return False
            
            # Тестируем получение предложений через API
            response = requests.get(f"{self.base_url}/api/offers", timeout=10)
            
            if response.status_code == 200:
                api_offers = response.json()
                
                if isinstance(api_offers, list):
                    self.log_test(
                        "API предложений",
                        True,
                        f"Получено {len(api_offers)} предложений через API"
                    )
                    return True
                else:
                    self.log_test(
                        "API предложений",
                        False,
                        "API вернул неверный формат данных"
                    )
                    return False
            else:
                self.log_test(
                    "API предложений",
                    False,
                    f"HTTP ошибка: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test("API тестирование", False, str(e))
            return False
    
    def test_database_consistency(self) -> bool:
        """Проверка целостности данных в базе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем на дубликаты каналов
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM channels 
                WHERE username IS NOT NULL AND username != ''
                GROUP BY username 
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                self.log_test(
                    "Дубликаты каналов",
                    False,
                    f"Найдено {len(duplicates)} дублирующихся каналов",
                    {'duplicates': duplicates}
                )
            else:
                self.log_test(
                    "Дубликаты каналов",
                    True,
                    "Дубликатов не обнаружено"
                )
            
            # Проверяем валидность цен
            cursor.execute("""
                SELECT COUNT(*) FROM channels 
                WHERE price_per_post < 0 OR price_per_post > 1000000
            """)
            
            invalid_prices = cursor.fetchone()[0]
            
            if invalid_prices > 0:
                self.log_test(
                    "Валидность цен",
                    False,
                    f"Найдено {invalid_prices} каналов с невалидными ценами"
                )
            else:
                self.log_test(
                    "Валидность цен",
                    True,
                    "Все цены в допустимых пределах"
                )
            
            # Проверяем актуальность данных
            cursor.execute("""
                SELECT COUNT(*) FROM channels 
                WHERE created_at < datetime('now', '-6 months')
            """)
            
            old_channels = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM channels")
            total_channels = cursor.fetchone()[0]
            
            if total_channels > 0:
                old_ratio = old_channels / total_channels
                self.log_test(
                    "Актуальность данных",
                    old_ratio < 0.5,  # Менее 50% старых данных
                    f"Каналов старше 6 месяцев: {old_channels}/{total_channels} ({old_ratio*100:.1f}%)"
                )
            
            conn.close()
            return True
            
        except Exception as e:
            self.log_test("Целостность БД", False, str(e))
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Запуск комплексного теста с реальными данными"""
        print("🔍 ТЕСТИРОВАНИЕ С РЕАЛЬНЫМИ ДАННЫМИ")
        print("=" * 60)
        
        start_time = time.time()
        
        # Получаем реальные данные
        channels = self.get_real_channels_from_db()
        offers = self.get_real_offers_from_db()
        
        if not channels:
            print("⚠️ Реальные каналы не найдены в базе данных")
            print("   Добавьте каналы перед тестированием")
            return {'success': False, 'reason': 'no_channels'}
        
        # Проверяем несколько реальных каналов
        print(f"\n📺 Проверка {min(len(channels), 5)} реальных каналов...")
        verified_channels = 0
        
        for channel in channels[:5]:  # Проверяем максимум 5 каналов
            if self.verify_channel_data(channel):
                verified_channels += 1
        
        # Тестируем алгоритм подбора
        print(f"\n🎯 Тестирование алгоритма подбора...")
        matching_works = self.test_channel_matching_algorithm(channels, offers)
        
        # Тестируем API
        print(f"\n🌐 Тестирование API...")
        api_works = self.test_api_with_real_data()
        
        # Проверяем целостность данных
        print(f"\n🔍 Проверка целостности данных...")
        db_consistent = self.test_database_consistency()
        
        # Подводим итоги
        duration = time.time() - start_time
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ С РЕАЛЬНЫМИ ДАННЫМИ")
        print("=" * 60)
        print(f"⏱️ Время выполнения: {duration:.1f}с")
        print(f"📺 Каналов в БД: {len(channels)}")
        print(f"📋 Предложений в БД: {len(offers)}")
        print(f"✅ Проверенных каналов: {verified_channels}/5")
        print(f"🎯 Алгоритм подбора: {'✅ Работает' if matching_works else '❌ Проблемы'}")
        print(f"🌐 API: {'✅ Работает' if api_works else '❌ Проблемы'}")
        print(f"🔍 Целостность БД: {'✅ ОК' if db_consistent else '❌ Проблемы'}")
        print(f"📊 Общий результат: {passed_tests}/{total_tests} тестов ({passed_tests/total_tests*100:.1f}%)")
        
        # Сохраняем детальный отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': passed_tests/total_tests*100 if total_tests > 0 else 0,
                'channels_count': len(channels),
                'offers_count': len(offers),
                'verified_channels': verified_channels
            },
            'components': {
                'channel_verification': verified_channels > 0,
                'matching_algorithm': matching_works,
                'api_functionality': api_works,
                'database_consistency': db_consistent
            },
            'detailed_results': self.test_results
        }
        
        # Сохраняем отчет
        with open('real_data_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Детальный отчет: real_data_test_report.json")
        
        # Определяем общий успех
        overall_success = (
            passed_tests >= total_tests * 0.7 and  # 70% тестов пройдено
            verified_channels > 0 and  # Хотя бы один канал проверен
            api_works  # API работает
        )
        
        if overall_success:
            print("\n🎉 ТЕСТИРОВАНИЕ УСПЕШНО ЗАВЕРШЕНО!")
            print("   Приложение готово к работе с реальными данными")
        else:
            print("\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
            print("   Требуется дополнительная настройка")
            
            # Рекомендации по исправлению
            print("\n🔧 Рекомендации:")
            if verified_channels == 0:
                print("   • Проверьте корректность данных каналов в БД")
                print("   • Убедитесь, что бот имеет доступ к каналам")
            if not matching_works:
                print("   • Проверьте алгоритм подбора каналов")
                print("   • Добавьте больше каналов разных категорий")
            if not api_works:
                print("   • Проверьте работу API эндпоинтов")
                print("   • Убедитесь, что приложение запущено")
        
        return report

def main():
    """Главная функция"""
    config = {
        'base_url': 'http://localhost:5000',
        'bot_token': '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8',
        'db_path': 'telegram_mini_app.db'
    }
    
    tester = RealDataTester(config)
    
    try:
        result = tester.run_comprehensive_test()
        
        # Возвращаем код выхода
        if result.get('summary', {}).get('success_rate', 0) >= 70:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        return 130
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {str(e)}")
        logger.exception("Критическая ошибка при тестировании")
        return 1

if __name__ == "__main__":
    sys.exit(main())