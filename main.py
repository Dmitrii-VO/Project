#!/usr/bin/env python3
"""
Telegram Mini App - Основной файл запуска
Модульная архитектура для платформы рекламы в Telegram каналах
"""

import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config.settings import Config


def main():
    """Главная функция запуска приложения"""
    print("\n" + "=" * 60)
    print("🚀 TELEGRAM MINI APP - МОДУЛЬНАЯ АРХИТЕКТУРА")
    print("=" * 60)

    # Создание Flask приложения
    app = create_app()

    # Информация о конфигурации
    print_startup_info()

    # Инициализация дополнительных систем
    initialize_additional_systems(app)

    print("\n🌐 Приложение доступно:")
    print("  • Главная: http://localhost:5000")
    print("  • Каналы: http://localhost:5000/channels-enhanced")
    print("  • Офферы: http://localhost:5000/offers")
    print("  • Платежи: http://localhost:5000/payments")
    print("  • Аналитика: http://localhost:5000/analytics")
    print("  • API Test: http://localhost:5000/test")
    print("  • Health Check: http://localhost:5000/health")

    print("\n🔒 БЕЗОПАСНОСТЬ:")
    print("  • Модульная архитектура")
    print("  • Централизованная конфигурация")
    print("  • Улучшенное логирование")
    print("  • Rate limiting активен")

    print("\n🛑 Для остановки нажмите Ctrl+C")

    try:
        # Запуск Flask приложения
        app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
    except KeyboardInterrupt:
        print("\n👋 Приложение остановлено")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        sys.exit(1)


def print_startup_info():
    """Вывод информации о запуске"""
    print(f"📱 Bot Token: {'✅ Настроен' if Config.BOT_TOKEN else '❌ НЕ НАСТРОЕН!'}")
    print(f"🗄️ Database: SQLite ({Config.DATABASE_PATH})")
    print(f"👤 Your Telegram ID: {Config.YOUR_TELEGRAM_ID}")
    print(f"🔗 Telegram Integration: {'✅ Активна' if Config.TELEGRAM_INTEGRATION else '❌ Отключена'}")
    print(f"🎯 Offers System: {'✅ Активна' if Config.OFFERS_SYSTEM_ENABLED else '❌ Отключена'}")
    print(f"💬 Responses System: {'✅ Активна' if Config.RESPONSES_SYSTEM_ENABLED else '❌ Отключена'}")
    print(f"💳 Payment System: {'✅ Активна' if Config.PAYMENTS_SYSTEM_ENABLED else '❌ Отключена'}")
    print(f"📊 Analytics System: {'✅ Активна' if Config.ANALYTICS_SYSTEM_ENABLED else '❌ Отключена'}")


def initialize_additional_systems(app):
    """Инициализация дополнительных систем"""
    # Здесь можно добавить инициализацию:
    # - Системы уведомлений
    # - Планировщика задач
    # - Системы аналитики
    # - Системы выплат
    pass


if __name__ == '__main__':
    main()