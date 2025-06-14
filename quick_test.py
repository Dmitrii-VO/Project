#!/usr/bin/env python3
"""
quick_test.py - Быстрая проверка основных функций Telegram Mini App
Этот скрипт выполняет базовые проверки за минимальное время
"""

import os
import sys
import requests
import subprocess
import time
import json
from typing import Dict, List, Tuple

class QuickTester:
    """Класс для быстрого тестирования"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.results = []
        
    def check(self, name: str, condition: bool, message: str = "") -> bool:
        """Проверка с результатом"""
        status = "✅ PASS" if condition else "❌ FAIL"
        print(f"{status} {name}: {message}")
        self.results.append((name, condition, message))
        return condition
    
    def test_files_exist(self) -> bool:
        """Проверка наличия ключевых файлов"""
        print("\n📁 Проверка файлов...")
        
        files = [
            ("working_app.py", "Главный файл приложения"),
            ("requirements.txt", "Файл зависимостей"),
            ("telegram_mini_app.db", "База данных"),
            ("app/static/css/style.css", "CSS стили"),
            ("app/templates/index.html", "Главный шаблон")
        ]
        
        all_exist = True
        for file_path, description in files:
            exists = os.path.exists(file_path)
            self.check(f"Файл {file_path}", exists, description)
            if not exists:
                all_exist = False
                
        return all_exist
    
    def test_app_startup(self) -> Tuple[bool, subprocess.Popen]:
        """Тест запуска приложения"""
        print("\n🚀 Запуск приложения...")
        
        try:
            # Запускаем приложение
            process = subprocess.Popen(
                [sys.executable, "working_app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Ждем запуска
            time.sleep(3)
            
            if process.poll() is None:
                self.check("Запуск процесса", True, f"PID: {process.pid}")
                return True, process
            else:
                stdout, stderr = process.communicate()
                self.check("Запуск процесса", False, f"Ошибка: {stderr[:100]}")
                return False, None
                
        except Exception as e:
            self.check("Запуск процесса", False, f"Исключение: {str(e)}")
            return False, None
    
    def test_http_endpoints(self) -> bool:
        """Тест HTTP эндпоинтов"""
        print("\n🌐 Проверка эндпоинтов...")
        
        endpoints = [
            ("/", "Главная страница"),
            ("/test", "Тестовый эндпоинт"),
            ("/health", "Проверка здоровья"),
            ("/api/offers", "API офферов"),
            ("/static/css/style.css", "CSS файлы")
        ]
        
        all_work = True
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                success = response.status_code < 500
                self.check(f"GET {endpoint}", success, f"Код: {response.status_code}")
                if not success:
                    all_work = False
            except requests.exceptions.RequestException as e:
                self.check(f"GET {endpoint}", False, f"Ошибка: {str(e)[:50]}")
                all_work = False
                
        return all_work
    
    def test_telegram_bot(self) -> bool:
        """Тест Telegram бота"""
        print("\n🤖 Проверка Telegram бота...")
        
        bot_token = "6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8"
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_name = data['result']['username']
                    self.check("Telegram Bot API", True, f"Бот: @{bot_name}")
                    return True
                else:
                    self.check("Telegram Bot API", False, f"API ошибка: {data}")
                    return False
            else:
                self.check("Telegram Bot API", False, f"HTTP: {response.status_code}")
                return False
                
        except Exception as e:
            self.check("Telegram Bot API", False, f"Ошибка: {str(e)}")
            return False
    
    def test_database(self) -> bool:
        """Тест базы данных"""
        print("\n🗄️ Проверка базы данных...")
        
        try:
            import sqlite3
            
            if not os.path.exists("telegram_mini_app.db"):
                self.check("Файл БД", False, "База данных не найдена")
                return False
            
            conn = sqlite3.connect("telegram_mini_app.db")
            cursor = conn.cursor()
            
            # Проверяем таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.check("Подключение к БД", True, f"Таблиц: {len(tables)}")
            
            # Проверяем основные таблицы
            expected_tables = ['users', 'channels', 'offers']
            missing = [t for t in expected_tables if t not in tables]
            
            if missing:
                self.check("Структура БД", False, f"Отсутствуют: {missing}")
                conn.close()
                return False
            else:
                self.check("Структура БД", True, "Основные таблицы найдены")
                conn.close()
                return True
                
        except Exception as e:
            self.check("База данных", False, f"Ошибка: {str(e)}")
            return False
    
    def run_quick_test(self) -> Dict:
        """Запуск быстрого теста"""
        print("⚡ БЫСТРАЯ ПРОВЕРКА TELEGRAM MINI APP")
        print("=" * 50)
        
        start_time = time.time()
        process = None
        
        try:
            # Проверяем файлы
            files_ok = self.test_files_exist()
            
            # Проверяем БД
            db_ok = self.test_database()
            
            # Проверяем Telegram бота
            bot_ok = self.test_telegram_bot()
            
            # Запускаем приложение и тестируем
            app_ok = False
            http_ok = False
            
            if files_ok:
                app_started, process = self.test_app_startup()
                if app_started:
                    app_ok = True
                    time.sleep(2)  # Даем время на полный запуск
                    http_ok = self.test_http_endpoints()
            
            # Подводим итоги
            duration = time.time() - start_time
            
            total_checks = len(self.results)
            passed_checks = sum(1 for _, success, _ in self.results if success)
            
            print("\n" + "=" * 50)
            print("📊 РЕЗУЛЬТАТЫ БЫСТРОЙ ПРОВЕРКИ")
            print("=" * 50)
            print(f"⏱️ Время выполнения: {duration:.1f}с")
            print(f"✅ Пройдено: {passed_checks}/{total_checks}")
            print(f"📈 Успешность: {passed_checks/total_checks*100:.1f}%")
            
            # Категории проверок
            categories = {
                "Файлы": files_ok,
                "База данных": db_ok, 
                "Telegram бот": bot_ok,
                "Запуск приложения": app_ok,
                "HTTP эндпоинты": http_ok
            }
            
            print("\n📋 По категориям:")
            for category, status in categories.items():
                icon = "✅" if status else "❌"
                print(f"  {icon} {category}")
            
            # Общая оценка
            overall_success = passed_checks >= total_checks * 0.8
            
            if overall_success:
                print("\n🎉 Быстрая проверка ПРОЙДЕНА!")
                print("   Приложение готово к работе")
            else:
                print("\n⚠️ Обнаружены ПРОБЛЕМЫ!")
                print("   Требуется дополнительная настройка")
            
            return {
                'success': overall_success,
                'duration': duration,
                'checks': self.results,
                'categories': categories,
                'summary': {
                    'total': total_checks,
                    'passed': passed_checks,
                    'rate': passed_checks/total_checks*100
                }
            }
            
        except KeyboardInterrupt:
            print("\n⏹️ Проверка прервана")
            return {'success': False, 'interrupted': True}
            
        finally:
            # Завершаем процесс приложения
            if process and process.poll() is None:
                print("\n🔄 Завершение приложения...")
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()

def main():
    """Главная функция"""
    tester = QuickTester()
    result = tester.run_quick_test()
    
    # Возвращаем код выхода
    return 0 if result.get('success', False) else 1

if __name__ == "__main__":
    sys.exit(main())