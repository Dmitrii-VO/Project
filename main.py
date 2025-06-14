#!/usr/bin/env python3
"""
Telegram Mini App - Главный файл запуска
"""

import os
import sys


def main():
    """Главная функция запуска"""
    print("🚀 Запуск Telegram Mini App...")

    # Проверяем существование working_app.py
    if not os.path.exists('working_app.py'):
        print("❌ Файл working_app.py не найден!")
        sys.exit(1)

    # Запускаем working_app.py
    try:
        import working_app
        print("✅ working_app.py запущен успешно")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()