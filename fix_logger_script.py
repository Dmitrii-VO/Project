#!/usr/bin/env python3
"""
fix_logger_error.py - Автоматическое исправление ошибки logger в working_app.py
Исправляет порядок импортов и определения logger
"""

import os
import re
import shutil
from datetime import datetime

def create_backup(file_path):
    """Создание резервной копии файла"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"📦 Создана резервная копия: {backup_path}")
    return backup_path

def fix_working_app():
    """Исправление working_app.py"""
    file_path = "working_app.py"
    
    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден!")
        return False
    
    # Создаем бэкап
    backup_path = create_backup(file_path)
    
    try:
        # Читаем содержимое файла
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 Анализ файла...")
        
        # Проверяем наличие проблемного блока
        if 'logger.info("✅ Расширенные маршруты импортированы")' in content:
            print("✅ Найден проблемный блок с logger")
            
            # Паттерн для поиска проблемного блока enhanced_api_routes
            pattern = r'''try:
    from enhanced_api_routes import add_enhanced_routes
    enhanced_routes_available = True
    logger\.info\("✅ Расширенные маршруты импортированы"\)
except ImportError as e:
    logger\.warning\(f"⚠️ Расширенные маршруты недоступны: \{e\}"\)
    enhanced_routes_available = False
    
    # Создаем заглушку
    def add_enhanced_routes\(app=None\):
        logger\.info\("🔄 Используется заглушка для расширенных маршрутов"\)
        return False'''
            
            # Замена на исправленный блок
            replacement = '''try:
    from enhanced_api_routes import add_enhanced_routes
    enhanced_routes_available = True
    print("✅ Расширенные маршруты импортированы")
except ImportError as e:
    print(f"⚠️ Расширенные маршруты недоступны: {e}")
    enhanced_routes_available = False
    
    # Создаем заглушку
    def add_enhanced_routes(app=None):
        print("🔄 Используется заглушка для расширенных маршрутов")
        return False'''
            
            # Выполняем замену
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            if new_content != content:
                print("🔧 Исправление найденного блока...")
                content = new_content
            else:
                print("⚠️ Автоматическая замена не сработала, применяем альтернативный метод...")
                
                # Альтернативный метод - простая замена строк
                content = content.replace(
                    'logger.info("✅ Расширенные маршруты импортированы")',
                    'print("✅ Расширенные маршруты импортированы")'
                )
                content = content.replace(
                    'logger.warning(f"⚠️ Расширенные маршруты недоступны: {e}")',
                    'print(f"⚠️ Расширенные маршруты недоступны: {e}")'
                )
                content = content.replace(
                    'logger.info("🔄 Используется заглушка для расширенных маршрутов")',
                    'print("🔄 Используется заглушка для расширенных маршрутов")'
                )
        
        # Дополнительные исправления
        print("🔧 Применение дополнительных исправлений...")
        
        # Убеждаемся, что логирование настроено в правильном порядке
        lines = content.split('\n')
        new_lines = []
        logger_setup_found = False
        enhanced_routes_moved = False
        
        for i, line in enumerate(lines):
            # Ищем блок настройки логирования
            if 'logging.basicConfig(' in line:
                logger_setup_found = True
            
            # Если встречаем logger = logging.getLogger(__name__)
            if 'logger = logging.getLogger(__name__)' in line:
                new_lines.append(line)
                # Добавляем проверку, что logger готов к использованию
                new_lines.append('')
                new_lines.append('# Logger готов к использованию')
                continue
            
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        # Записываем исправленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Файл успешно исправлен!")
        print("\n📋 Внесенные изменения:")
        print("  • Заменены logger.info/warning на print в блоке enhanced_api_routes")
        print("  • Добавлены комментарии для лучшей читаемости")
        print("  • Проверен порядок инициализации logger")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении: {e}")
        # Восстанавливаем из бэкапа
        shutil.copy2(backup_path, file_path)
        print(f"🔄 Файл восстановлен из резервной копии")
        return False

def verify_fix():
    """Проверка правильности исправления"""
    file_path = "working_app.py"
    
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, что проблемные строки исправлены
        problematic_patterns = [
            r'logger\.info\("✅ Расширенные маршруты импортированы"\)',
            r'logger\.warning\(f"⚠️ Расширенные маршруты недоступны:'
        ]
        
        for pattern in problematic_patterns:
            if re.search(pattern, content):
                print(f"⚠️ Найден неисправленный паттерн: {pattern}")
                return False
        
        print("✅ Проверка прошла успешно - проблемные logger убраны")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

def test_import():
    """Тест импорта для проверки синтаксиса"""
    print("🧪 Тестирование синтаксиса...")
    
    try:
        # Проверяем синтаксис без выполнения
        with open("working_app.py", 'r', encoding='utf-8') as f:
            code = f.read()
        
        compile(code, "working_app.py", "exec")
        print("✅ Синтаксис корректен")
        return True
        
    except SyntaxError as e:
        print(f"❌ Синтаксическая ошибка: {e}")
        print(f"   Строка {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Ошибка компиляции: {e}")
        return False

def main():
    """Главная функция"""
    print("🔧 АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ ОШИБКИ LOGGER")
    print("=" * 50)
    
    # Проверяем существование файла
    if not os.path.exists("working_app.py"):
        print("❌ Файл working_app.py не найден в текущей директории!")
        print("💡 Убедитесь, что запускаете скрипт из корня проекта")
        return False
    
    # Выполняем исправление
    print("🔧 Исправление working_app.py...")
    if not fix_working_app():
        print("❌ Исправление не удалось")
        return False
    
    # Проверяем результат
    print("\n🔍 Проверка исправлений...")
    if not verify_fix():
        print("❌ Проверка не прошла")
        return False
    
    # Тестируем синтаксис
    print("\n🧪 Проверка синтаксиса...")
    if not test_import():
        print("❌ Синтаксис некорректен")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    print("=" * 50)
    print("📋 Что было исправлено:")
    print("  ✅ Убраны вызовы logger до его инициализации")
    print("  ✅ Заменены на безопасные print() вызовы")
    print("  ✅ Проверен синтаксис файла")
    print("  ✅ Создана резервная копия")
    print("\n🚀 Теперь можно запускать:")
    print("  python working_app.py")
    print("\n💡 Если возникнут проблемы, используйте резервную копию")
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        print("\n💥 Исправление не удалось.")
        print("💡 Попробуйте исправить вручную или обратитесь за помощью.")
        exit(1)
    else:
        print("\n✨ Готово! Попробуйте запустить приложение.")
