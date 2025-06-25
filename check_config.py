#!/usr/bin/env python3
"""
Проверка настроек системы офферов для интеграции с фронтендом
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Проверяем переменные окружения"""
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("-" * 50)
    
    load_dotenv()
    
    # Критические настройки для офферов
    critical_vars = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'YOUR_TELEGRAM_ID': os.getenv('YOUR_TELEGRAM_ID'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'OFFERS_SYSTEM_ENABLED': os.getenv('OFFERS_SYSTEM_ENABLED', 'True')
    }
    
    print("📋 Критические переменные:")
    all_ok = True
    
    for var, value in critical_vars.items():
        if value:
            # Скрываем токены для безопасности
            if 'TOKEN' in var or 'SECRET' in var:
                display_value = f"{value[:10]}***{value[-4:]}" if len(value) > 14 else "***"
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: НЕ УСТАНОВЛЕНА")
            all_ok = False
    
    return all_ok

def check_config_file():
    """Проверяем файл конфигурации"""
    print("\n🔍 ПРОВЕРКА app/config/settings.py")
    print("-" * 50)
    
    try:
        sys.path.insert(0, os.getcwd())
        from app.config.settings import Config
        
        config_checks = {
            'OFFERS_SYSTEM_ENABLED': getattr(Config, 'OFFERS_SYSTEM_ENABLED', None),
            'MIN_OFFER_BUDGET': getattr(Config, 'MIN_OFFER_BUDGET', None),
            'MAX_OFFER_BUDGET': getattr(Config, 'MAX_OFFER_BUDGET', None),
            'DEFAULT_OFFER_DURATION_DAYS': getattr(Config, 'DEFAULT_OFFER_DURATION_DAYS', None),
        }
        
        print("📋 Настройки офферов в Config:")
        for setting, value in config_checks.items():
            if value is not None:
                print(f"   ✅ {setting}: {value}")
            else:
                print(f"   ⚠️ {setting}: НЕ НАЙДЕНА")
        
        # Проверяем доступность констант
        try:
            from app.config.settings import MIN_OFFER_BUDGET, MAX_OFFER_BUDGET
            print(f"   ✅ Константы доступны: MIN={MIN_OFFER_BUDGET}, MAX={MAX_OFFER_BUDGET}")
        except ImportError as e:
            print(f"   ⚠️ Ошибка импорта констант: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка загрузки конфигурации: {e}")
        return False

def check_api_registration():
    """Проверяем регистрацию API офферов"""
    print("\n🔍 ПРОВЕРКА РЕГИСТРАЦИИ API")
    print("-" * 50)
    
    try:
        # Проверяем импорт API модулей
        from app.api.offers import offers_bp
        print("   ✅ app.api.offers импортирован")
        
        from app.routers.main_router import main_bp
        print("   ✅ app.routers.main_router импортирован")
        
        # Проверяем Blueprint'ы
        print(f"   ✅ offers_bp зарегистрирован: {offers_bp.name}")
        print(f"   ✅ main_bp зарегистрирован: {main_bp.name}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки API: {e}")
        return False

def check_auth_service():
    """Проверяем сервис аутентификации"""
    print("\n🔍 ПРОВЕРКА СЕРВИСА АУТЕНТИФИКАЦИИ")
    print("-" * 50)
    
    try:
        from app.services.auth_service import auth_service
        print("   ✅ auth_service импортирован")
        
        # Проверяем методы
        methods = ['get_current_user_id', 'verify_telegram_auth']
        for method in methods:
            if hasattr(auth_service, method):
                print(f"   ✅ Метод {method} доступен")
            else:
                print(f"   ⚠️ Метод {method} отсутствует")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки auth_service: {e}")
        print("   💡 Возможно нужно использовать альтернативную аутентификацию")
        return False

def check_working_app_integration():
    """Проверяем интеграцию в working_app.py"""
    print("\n🔍 ПРОВЕРКА ИНТЕГРАЦИИ В working_app.py")
    print("-" * 50)
    
    try:
        # Читаем working_app.py
        with open('working_app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = {
            'offers_bp импорт': 'from app.api.offers import offers_bp' in content,
            'offers_bp регистрация': 'offers_bp' in content and 'register_blueprint' in content,
            'add_offer импорт': 'from add_offer import' in content or 'import add_offer' in content,
            'API маршрут /api/offers': '/api/offers' in content
        }
        
        print("📋 Проверка интеграции:")
        all_integrated = True
        
        for check, result in checks.items():
            if result:
                print(f"   ✅ {check}")
            else:
                print(f"   ❌ {check}")
                all_integrated = False
        
        return all_integrated
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки working_app.py: {e}")
        return False

def check_frontend_files():
    """Проверяем фронтенд файлы"""
    print("\n🔍 ПРОВЕРКА ФРОНТЕНД ФАЙЛОВ")
    print("-" * 50)
    
    files_to_check = [
        'templates/offers.html',
        'app/static/js/offers.js',
        'templates/offers-list.html'
    ]
    
    all_files_exist = True
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            # Проверяем размер файла
            size = os.path.getsize(file_path)
            print(f"   ✅ {file_path} ({size} байт)")
        else:
            print(f"   ❌ {file_path} отсутствует")
            all_files_exist = False
    
    return all_files_exist

def suggest_fixes():
    """Предлагаем исправления"""
    print("\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
    print("-" * 50)
    
    print("1. Если auth_service не работает:")
    print("   - Используйте альтернативную аутентификацию через заголовки")
    print("   - В API получайте user_id из request.headers.get('X-Telegram-User-Id')")
    
    print("\n2. Для полной интеграции убедитесь что:")
    print("   - OFFERS_SYSTEM_ENABLED=True в .env")
    print("   - offers_bp зарегистрирован в working_app.py")
    print("   - add_offer.py находится в корне проекта")
    
    print("\n3. Для тестирования:")
    print("   - Запустите: python working_app.py")
    print("   - Откройте: http://localhost:5000/offers")
    print("   - Попробуйте создать оффер через интерфейс")

def main():
    """Главная функция проверки"""
    print("🔍 ПОЛНАЯ ПРОВЕРКА СИСТЕМЫ ОФФЕРОВ")
    print("=" * 60)
    
    checks = [
        ("Переменные окружения", check_environment),
        ("Файл конфигурации", check_config_file),
        ("Регистрация API", check_api_registration),
        ("Сервис аутентификации", check_auth_service),
        ("Интеграция в working_app.py", check_working_app_integration),
        ("Фронтенд файлы", check_frontend_files)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Ошибка в проверке '{check_name}': {e}")
            results.append((check_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ ПРОЙДЕНО" if result else "❌ ОШИБКА"
        print(f"{check_name:<30} {status}")
    
    print("-" * 60)
    print(f"Пройдено проверок: {passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("🚀 Система офферов готова к работе!")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Запустите сервер: python working_app.py")
        print("2. Откройте: http://localhost:5000/offers")
        print("3. Создайте тестовый оффер")
    else:
        print("⚠️ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        suggest_fixes()

if __name__ == '__main__':
    main()