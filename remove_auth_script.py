#!/usr/bin/env python3
"""
Диагностика маршрутов Telegram Mini App
Проверяет, какие маршруты зарегистрированы и доступны
"""

import os
import sys

# Добавляем пути
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(PROJECT_ROOT, 'app')

for path in [PROJECT_ROOT, APP_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)


def check_routes():
    """Проверка всех маршрутов"""

    print("🔍 ДИАГНОСТИКА МАРШРУТОВ TELEGRAM MINI APP")
    print("=" * 60)

    try:
        # Создаем тестовое приложение
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True

        # Пытаемся зарегистрировать Blueprint'ы
        print("📦 Регистрация Blueprint'ов...")

        blueprints_info = []

        # 1. main_router.py
        try:
            from app.routers.main_router import main_bp
            app.register_blueprint(main_bp, url_prefix='')
            blueprints_info.append(('main_bp', '', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('main_bp', '', f'❌ Ошибка: {e}'))

        # 2. api_router.py
        try:
            from app.routers.api_router import api_bp
            app.register_blueprint(api_bp, url_prefix='/api')
            blueprints_info.append(('api_bp', '/api', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('api_bp', '/api', f'❌ Ошибка: {e}'))

        # 3. channel_router.py
        try:
            from app.routers.channel_router import channel_bp
            app.register_blueprint(channel_bp, url_prefix='/api/channels')
            blueprints_info.append(('channel_bp', '/api/channels', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('channel_bp', '/api/channels', f'❌ Ошибка: {e}'))

        # 4. offer_router.py
        try:
            from app.routers.offer_router import offer_bp
            app.register_blueprint(offer_bp, url_prefix='/api/offers')
            blueprints_info.append(('offer_bp', '/api/offers', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('offer_bp', '/api/offers', f'❌ Ошибка: {e}'))

        # 5. analytics_router.py
        try:
            from app.routers.analytics_router import analytics_bp
            app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
            blueprints_info.append(('analytics_bp', '/api/analytics', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('analytics_bp', '/api/analytics', f'❌ Ошибка: {e}'))

        # 6. payment_router.py
        try:
            from app.routers.payment_router import payment_bp
            app.register_blueprint(payment_bp, url_prefix='/api/payments')
            blueprints_info.append(('payment_bp', '/api/payments', '✅ Успешно'))
        except Exception as e:
            blueprints_info.append(('payment_bp', '/api/payments', f'❌ Ошибка: {e}'))

        # Выводим результаты
        print("\n📋 РЕЗУЛЬТАТЫ РЕГИСТРАЦИИ BLUEPRINT'ОВ:")
        print("-" * 60)
        for name, prefix, status in blueprints_info:
            prefix_display = prefix if prefix else "/"
            print(f"{name:<20} {prefix_display:<15} {status}")

        # Проверяем зарегистрированные маршруты
        print(f"\n🗺️ ЗАРЕГИСТРИРОВАННЫЕ МАРШРУТЫ:")
        print("-" * 60)

        with app.app_context():
            for rule in app.url_map.iter_rules():
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                endpoint = rule.endpoint
                url = rule.rule
                print(f"{url:<25} {methods:<15} {endpoint}")

        # Тестируем основные страницы
        print(f"\n🧪 ТЕСТИРОВАНИЕ ОСНОВНЫХ СТРАНИЦ (БЕЗ АУТЕНТИФИКАЦИИ):")
        print("-" * 70)

        with app.test_client() as client:
            test_routes = [
                ('/', 'Главная страница'),
                ('/channels', 'Каналы'),
                ('/offers', 'Офферы'),
                ('/analytics', 'Аналитика'),
                ('/payments', 'Платежи'),
            ]

            for route, description in test_routes:
                try:
                    response = client.get(route)

                    if response.status_code == 200:
                        status = "✅ Работает"
                    elif response.status_code == 404:
                        status = "❌ Не найден"
                    elif response.status_code == 500:
                        status = "⚠️ Ошибка сервера"
                    else:
                        status = f"⚠️ Код {response.status_code}"

                    # Проверяем содержимое ответа
                    if response.status_code == 200:
                        content = response.get_data(as_text=True)
                        if 'auth_required' in content.lower():
                            status += " (требует авторизацию)"
                        elif 'error' in content.lower():
                            status += " (содержит ошибки)"

                    print(f"{route:<15} {description:<20} {status}")

                except Exception as e:
                    print(f"{route:<15} {description:<20} ❌ Исключение: {str(e)[:30]}...")

            # Отдельно тестируем health check
            print(f"\n🏥 HEALTH CHECK:")
            print("-" * 70)
            try:
                response = client.get('/health')
                if response.status_code == 200:
                    data = response.get_json()
                    status = data.get('status', 'unknown') if data else 'no_data'
                    print(f"/health          Health Check         ✅ Работает (статус: {status})")
                else:
                    print(f"/health          Health Check         ⚠️ Код {response.status_code}")
            except Exception as e:
                print(f"/health          Health Check         ❌ Ошибка: {str(e)[:30]}...")

        # Проверяем API эндпоинты
        print(f"\n🔌 ТЕСТИРОВАНИЕ API ЭНДПОИНТОВ:")
        print("-" * 60)

        with app.test_client() as client:
            api_routes = [
                ('/api/health', 'API Health'),
                ('/api/channels/', 'Список каналов'),
                ('/api/offers/', 'Список офферов'),
                ('/api/analytics/dashboard', 'Дашборд аналитики'),
                ('/api/payments/stats', 'Статистика платежей'),
            ]

            for route, description in api_routes:
                try:
                    response = client.get(route)
                    status = "✅ Работает" if response.status_code < 500 else f"⚠️ Код {response.status_code}"
                    print(f"{route:<25} {description:<20} {status}")
                except Exception as e:
                    print(f"{route:<25} {description:<20} ❌ Ошибка: {str(e)[:30]}...")

        print("\n" + "=" * 60)
        print("✅ Диагностика завершена!")

        # Подсчитываем статистику
        successful_blueprints = sum(1 for _, _, status in blueprints_info if '✅' in status)
        total_blueprints = len(blueprints_info)

        print(f"📊 Blueprint'ы: {successful_blueprints}/{total_blueprints} успешно зарегистрированы")
        print(f"🗺️ Всего маршрутов: {len(list(app.url_map.iter_rules()))}")

        if successful_blueprints < total_blueprints:
            print("\n⚠️ РЕКОМЕНДАЦИИ:")
            print("1. Проверьте зависимости в requirements.txt")
            print("2. Убедитесь, что все файлы модулей существуют")
            print("3. Проверьте импорты в файлах роутеров")
            print("4. Запустите: python install_missing_deps.py")

        return successful_blueprints == total_blueprints

    except Exception as e:
        print(f"❌ Критическая ошибка диагностики: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = check_routes()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Диагностика прервана пользователем")
        sys.exit(1)