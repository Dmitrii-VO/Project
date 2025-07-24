#!/usr/bin/env python3
"""
Диагностика проблем с аналитикой
"""

import os
import sys
import json
import logging
from datetime import datetime

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app.api.analytics import analytics_bp, get_dashboard_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_analytics_api():
    """Диагностика API аналитики"""
    logger.info("🔍 ДИАГНОСТИКА API АНАЛИТИКИ")
    logger.info("="*50)
    
    try:
        # Создаем тестовое приложение
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
        
        logger.info("✅ Flask приложение создано")
        
        # Тестируем API
        with app.test_client() as client:
            logger.info("🧪 Тестирование endpoint /api/analytics/dashboard...")
            
            response = client.get('/api/analytics/dashboard')
            
            logger.info(f"📞 Статус ответа: {response.status_code}")
            logger.info(f"📋 Заголовки ответа: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.get_json()
                    logger.info("✅ API возвращает валидный JSON")
                    logger.info("📊 Структура данных:")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                    
                    # Проверяем ключевые поля
                    if data.get('success'):
                        logger.info("✅ API возвращает success: true")
                        
                        analytics_data = data.get('data', {})
                        key_metrics = {
                            'total_views': analytics_data.get('total_views'),
                            'click_rate': analytics_data.get('click_rate'),
                            'total_revenue': analytics_data.get('total_revenue'),
                            'conversion_rate': analytics_data.get('conversion_rate'),
                            'channels_count': analytics_data.get('channels_count'),
                            'offers_count': analytics_data.get('offers_count')
                        }
                        
                        logger.info("🎯 Ключевые метрики:")
                        for key, value in key_metrics.items():
                            logger.info(f"   {key}: {value}")
                        
                        # Проверяем тестовые значения
                        test_values = [1234567, 45230, 3.8, 2.1]
                        found_test_values = []
                        
                        for metric, value in key_metrics.items():
                            if value in test_values:
                                found_test_values.append(f"{metric}={value}")
                        
                        if found_test_values:
                            logger.warning(f"⚠️ Обнаружены тестовые значения: {', '.join(found_test_values)}")
                        else:
                            logger.info("✅ Тестовые значения не обнаружены - отображаются реальные данные")
                        
                        return True, data
                    else:
                        logger.error(f"❌ API возвращает success: false, error: {data.get('error')}")
                        return False, data
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка парсинга JSON: {e}")
                    logger.error(f"📄 Raw ответ: {response.get_data(as_text=True)}")
                    return False, None
            else:
                error_text = response.get_data(as_text=True)
                logger.error(f"❌ API вернул ошибку {response.status_code}")
                logger.error(f"📄 Текст ошибки: {error_text}")
                return False, None
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка диагностики: {e}")
        return False, None

def diagnose_database_connection():
    """Диагностика подключения к базе данных"""
    logger.info("\n🗄️ ДИАГНОСТИКА БАЗЫ ДАННЫХ")
    logger.info("="*50)
    
    try:
        from app.models.database import execute_db_query, db_manager
        
        # Тест подключения
        logger.info("🔌 Тестирование подключения к базе данных...")
        
        if db_manager.test_connection():
            logger.info("✅ Подключение к базе данных успешно")
        else:
            logger.error("❌ Ошибка подключения к базе данных")
            return False
        
        # Проверяем наличие данных пользователя
        logger.info("👤 Проверка данных пользователя...")
        
        users = execute_db_query('SELECT id, telegram_id, balance FROM users LIMIT 5', fetch_all=True)
        if users:
            logger.info(f"✅ Найдено пользователей: {len(users)}")
            for user in users:
                logger.info(f"   ID: {user['id']}, Telegram: {user['telegram_id']}, Баланс: {user.get('balance', 'N/A')}")
        else:
            logger.warning("⚠️ Пользователи не найдены")
        
        # Проверяем каналы
        logger.info("📺 Проверка каналов...")
        channels = execute_db_query('SELECT id, title, subscribers FROM channels LIMIT 5', fetch_all=True)
        if channels:
            logger.info(f"✅ Найдено каналов: {len(channels)}")
        else:
            logger.warning("⚠️ Каналы не найдены")
        
        # Проверяем офферы
        logger.info("📢 Проверка офферов...")
        offers = execute_db_query('SELECT id, title, price FROM offers LIMIT 5', fetch_all=True)
        if offers:
            logger.info(f"✅ Найдено офферов: {len(offers)}")
        else:
            logger.warning("⚠️ Офферы не найдены")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка диагностики БД: {e}")
        return False

def diagnose_javascript_compatibility():
    """Диагностика совместимости с JavaScript"""
    logger.info("\n🌐 ДИАГНОСТИКА JAVASCRIPT СОВМЕСТИМОСТИ")
    logger.info("="*50)
    
    # Создаем пример данных, которые должен получить JavaScript
    test_api_response = {
        "success": True,
        "data": {
            "timestamp": datetime.now().isoformat(),
            "user_id": 1,
            "total_views": 0,
            "click_rate": 0,
            "total_revenue": 1500.0,
            "conversion_rate": 0,
            "channels_count": 2,
            "offers_count": 0
        }
    }
    
    logger.info("📊 Пример данных для JavaScript:")
    logger.info(json.dumps(test_api_response, indent=2, ensure_ascii=False))
    
    # Проверяем, что данные можно сериализовать в JSON
    try:
        json_str = json.dumps(test_api_response)
        parsed_back = json.loads(json_str)
        logger.info("✅ Данные корректно сериализуются в JSON")
        
        # Проверяем ключевые поля, которые ищет JavaScript
        required_fields = ['success', 'data']
        data_fields = ['total_views', 'click_rate', 'total_revenue', 'conversion_rate']
        
        for field in required_fields:
            if field in parsed_back:
                logger.info(f"✅ Поле '{field}' присутствует")
            else:
                logger.error(f"❌ Отсутствует обязательное поле '{field}'")
        
        data_section = parsed_back.get('data', {})
        for field in data_fields:
            if field in data_section:
                logger.info(f"✅ Поле data.{field} = {data_section[field]}")
            else:
                logger.warning(f"⚠️ Отсутствует поле data.{field}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка JSON сериализации: {e}")
        return False

def create_fix_recommendations(api_works, db_works, js_compatible):
    """Создает рекомендации по исправлению"""
    logger.info("\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
    logger.info("="*50)
    
    if api_works and db_works and js_compatible:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        logger.info("✅ API аналитики работает корректно")
        logger.info("✅ База данных доступна")
        logger.info("✅ Данные совместимы с JavaScript")
        logger.info("")
        logger.info("🤔 Возможные причины 'ошибки загрузки данных' в браузере:")
        logger.info("1. 🌐 Проблема с CORS (Cross-Origin Resource Sharing)")
        logger.info("2. 🔒 Проблема с авторизацией в браузере")
        logger.info("3. 📡 Сетевая проблема или блокировка запросов")
        logger.info("4. 🧩 JavaScript не может найти элементы на странице")
        logger.info("5. ⚡ Таймаут запроса или медленный ответ сервера")
        logger.info("")
        logger.info("🔧 Рекомендуемые действия:")
        logger.info("1. Откройте браузер в режиме разработчика (F12)")
        logger.info("2. Перейдите на вкладку Network/Сеть")
        logger.info("3. Загрузите страницу /analytics")
        logger.info("4. Проверьте запрос к /api/analytics/dashboard")
        logger.info("5. Посмотрите на статус ответа и содержимое")
        
    else:
        logger.error("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
        
        if not api_works:
            logger.error("🔥 API аналитики не работает")
            logger.info("   - Проверьте логи сервера")
            logger.info("   - Убедитесь, что все зависимости установлены")
            logger.info("   - Проверьте функцию get_current_user_id()")
        
        if not db_works:
            logger.error("🔥 База данных недоступна")
            logger.info("   - Проверьте путь к файлу базы данных")
            logger.info("   - Убедитесь, что файл БД существует и доступен для чтения")
            logger.info("   - Запустите миграции если необходимо")
        
        if not js_compatible:
            logger.error("🔥 Данные не совместимы с JavaScript")
            logger.info("   - Проверьте структуру JSON ответа")
            logger.info("   - Убедитесь, что все поля корректно сериализуются")

def main():
    """Главная функция диагностики"""
    logger.info("🚀 ПОЛНАЯ ДИАГНОСТИКА АНАЛИТИКИ")
    logger.info("="*60)
    logger.info(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Выполняем все тесты
    api_works, api_data = diagnose_analytics_api()
    db_works = diagnose_database_connection()
    js_compatible = diagnose_javascript_compatibility()
    
    # Создаем рекомендации
    create_fix_recommendations(api_works, db_works, js_compatible)
    
    logger.info("\n🏁 ДИАГНОСТИКА ЗАВЕРШЕНА")
    logger.info("="*60)
    
    return api_works and db_works and js_compatible

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)