#!/usr/bin/env python3
"""
Диагностический скрипт для анализа структуры Telegram Mini App
и выявления проблем с функцией requestVerification
"""

import os
import re
from pathlib import Path

class TelegramAppDiagnostic:
    def __init__(self, project_path="."):
        self.project_path = Path(project_path)
        self.issues = []
        self.files_analyzed = []
        
    def analyze_project_structure(self):
        """Анализирует структуру проекта"""
        print("🔍 АНАЛИЗ СТРУКТУРЫ ПРОЕКТА")
        print("=" * 50)
        
        # Ожидаемые файлы для Telegram Mini App
        expected_files = [
            "app.py",
            "main.py", 
            "run.py",
            "requirements.txt",
            "config.py",
            "database.py",
            "models.py"
        ]
        
        expected_dirs = [
            "templates",
            "static",
            "static/js",
            "static/css"
        ]
        
        print("📁 Структура директорий:")
        for root, dirs, files in os.walk(self.project_path):
            level = root.replace(str(self.project_path), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
                
        print("\n✅ Найденные ключевые файлы:")
        for file in expected_files:
            file_path = self.project_path / file
            if file_path.exists():
                print(f"  ✓ {file}")
            else:
                print(f"  ✗ {file} - ОТСУТСТВУЕТ")
                self.issues.append(f"Отсутствует файл: {file}")
                
        print("\n📂 Найденные директории:")
        for dir_name in expected_dirs:
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                print(f"  ✓ {dir_name}/")
            else:
                print(f"  ✗ {dir_name}/ - ОТСУТСТВУЕТ")
                self.issues.append(f"Отсутствует директория: {dir_name}")
    
    def find_verification_function(self):
        """Ищет определение функции requestVerification"""
        print("\n🔍 ПОИСК ФУНКЦИИ requestVerification")
        print("=" * 50)
        
        js_files = []
        html_files = []
        
        # Поиск JS и HTML файлов
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.js'):
                    js_files.append(Path(root) / file)
                elif file.endswith('.html'):
                    html_files.append(Path(root) / file)
        
        print(f"📄 Найдено JS файлов: {len(js_files)}")
        print(f"📄 Найдено HTML файлов: {len(html_files)}")
        
        # Анализ JS файлов
        verification_found = False
        for js_file in js_files:
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'requestVerification' in content:
                        print(f"\n✅ Функция найдена в: {js_file}")
                        # Показываем контекст функции
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'requestVerification' in line:
                                start = max(0, i-3)
                                end = min(len(lines), i+10)
                                print(f"📝 Контекст (строки {start+1}-{end}):")
                                for j in range(start, end):
                                    prefix = ">>> " if j == i else "    "
                                    print(f"{prefix}{j+1:3}: {lines[j]}")
                                print()
                        verification_found = True
                    self.files_analyzed.append(str(js_file))
            except Exception as e:
                print(f"❌ Ошибка чтения {js_file}: {e}")
        
        # Анализ HTML файлов на предмет вызовов функции
        verification_calls = []
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'requestVerification' in content:
                        verification_calls.append(html_file)
                        # Найдем строки с вызовами
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'requestVerification' in line:
                                print(f"\n📞 Вызов найден в {html_file}, строка {i+1}:")
                                print(f"    {line.strip()}")
                    self.files_analyzed.append(str(html_file))
            except Exception as e:
                print(f"❌ Ошибка чтения {html_file}: {e}")
        
        if not verification_found:
            print("\n❌ ПРОБЛЕМА: Функция requestVerification НЕ НАЙДЕНА в JS файлах!")
            self.issues.append("Функция requestVerification не определена")
            
        if verification_calls and not verification_found:
            print(f"\n⚠️  КОНФЛИКТ: Функция вызывается в {len(verification_calls)} файлах, но не определена!")
            
        return verification_found, verification_calls
    
    def check_telegram_web_app_integration(self):
        """Проверяет интеграцию с Telegram WebApp API"""
        print("\n🔍 ПРОВЕРКА TELEGRAM WEBAPP API")
        print("=" * 50)
        
        telegram_script_found = False
        webapp_ready_found = False
        
        for html_file in Path(self.project_path).rglob("*.html"):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Проверка подключения Telegram WebApp скрипта
                    if 'telegram-web-app.js' in content:
                        telegram_script_found = True
                        print(f"✅ Telegram WebApp скрипт найден в: {html_file}")
                    
                    # Проверка инициализации WebApp
                    if 'Telegram.WebApp' in content:
                        webapp_ready_found = True
                        print(f"✅ Telegram WebApp API используется в: {html_file}")
                        
            except Exception as e:
                print(f"❌ Ошибка чтения {html_file}: {e}")
        
        if not telegram_script_found:
            print("❌ ПРОБЛЕМА: Не найден скрипт telegram-web-app.js")
            self.issues.append("Отсутствует подключение telegram-web-app.js")
            
        if not webapp_ready_found:
            print("❌ ПРОБЛЕМА: Не найдено использование Telegram.WebApp API")
            self.issues.append("Не используется Telegram.WebApp API")
    
    def check_flask_routes(self):
        """Проверяет Flask маршруты"""
        print("\n🔍 ПРОВЕРКА FLASK МАРШРУТОВ")
        print("=" * 50)
        
        python_files = list(Path(self.project_path).rglob("*.py"))
        routes_found = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Поиск маршрутов
                    route_pattern = r'@app\.route\(["\']([^"\']+)["\']'
                    routes = re.findall(route_pattern, content)
                    
                    if routes:
                        print(f"\n📍 Маршруты в {py_file}:")
                        for route in routes:
                            print(f"  • {route}")
                            routes_found.append(route)
                            
            except Exception as e:
                print(f"❌ Ошибка чтения {py_file}: {e}")
        
        # Проверка наличия ключевых маршрутов
        expected_routes = ['/channels', '/verify', '/api/verify']
        missing_routes = []
        
        for expected in expected_routes:
            found = any(expected in route for route in routes_found)
            if not found:
                missing_routes.append(expected)
        
        if missing_routes:
            print(f"\n⚠️  Возможно отсутствуют маршруты: {missing_routes}")
    
    def generate_report(self):
        """Генерирует итоговый отчет"""
        print("\n" + "="*60)
        print("📋 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("="*60)
        
        if self.issues:
            print("\n❌ НАЙДЕННЫЕ ПРОБЛЕМЫ:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ Критических проблем не найдено")
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"  • Проанализировано файлов: {len(self.files_analyzed)}")
        print(f"  • Найдено проблем: {len(self.issues)}")
        
        print(f"\n🔧 СЛЕДУЮЩИЕ ШАГИ:")
        print("  1. Устраните найденные проблемы")
        print("  2. Создайте недостающие файлы")
        print("  3. Определите функцию requestVerification")
        print("  4. Проверьте подключение к Telegram WebApp API")

def main():
    """Основная функция диагностики"""
    print("🚀 ДИАГНОСТИКА TELEGRAM MINI APP")
    print("=" * 60)
    
    # Запрос пути к проекту
    project_path = input("Введите путь к проекту (Enter для текущей директории): ").strip()
    if not project_path:
        project_path = "."
    
    diagnostic = TelegramAppDiagnostic(project_path)
    
    try:
        # Выполнение диагностики
        diagnostic.analyze_project_structure()
        diagnostic.find_verification_function()
        diagnostic.check_telegram_web_app_integration()
        diagnostic.check_flask_routes()
        diagnostic.generate_report()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка диагностики: {e}")

if __name__ == "__main__":
    main()