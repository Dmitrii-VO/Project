#!/usr/bin/env python3
"""
Telegram Mini App - Упрощенный файл запуска
Перенаправляет на working_app.py для совместимости
"""

import os
import sys


def main():
    """Главная функция запуска - перенаправление на working_app.py"""
    print("🔄 Перенаправление на working_app.py...")

    # Импортируем и запускаем working_app
    try:
        import working_app
        # working_app.py запустится автоматически при импорте
    except ImportError as e:
        print(f"❌ Ошибка импорта working_app.py: {e}")
        print("💡 Убедитесь, что файл working_app.py существует")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()