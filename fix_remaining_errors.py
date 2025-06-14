#!/usr/bin/env python3
"""
fix_remaining_errors.py - Исправление оставшихся ошибок
1. Добавление модуля schedule в requirements.txt
2. Исправление переменной config_available
"""

import os
import shutil
from datetime import datetime

def create_backup(file_path):
    """Создание резервной копии"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"📦 Резервная копия: {backup_path}")
    return backup_path

def fix_requirements():
    """Добавление модуля schedule в requirements.txt"""
    print("📝 Исправление requirements.txt...")
    
    file_path = "requirements.txt"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} не найден")
        return False
    
    create_backup(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие schedule
        if 'schedule==' not in content and 'schedule' not in content:
            print("✅ Добавляем модуль schedule...")
            content += "\n# Планировщик задач для автоматических выплат\nschedule==1.2.0\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Модуль schedule добавлен в requirements.txt")
            return True
        else:
            print("ℹ️ Модуль schedule уже есть в requirements.txt")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def fix_config_available():
    """Исправление переменной config_available в working_app.py"""
    print("🔧 Исправление config_available...")
    
    file_path = "working_app.py"
    if not os.path.exists(file_path):
        print(f"❌ {file_path} не найден")
        return False
    
    create_backup(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем и исправляем проблему с config_available
        if "name 'config_available' is not defined" in content or 'config_available' in content:
            print("✅ Исправляем config_available...")
            
            # Ищем блок импорта конфигурации и добавляем определение переменной
            patterns_to_fix = [
                # Случай 1: импорт без определения переменной
                (
                    r'try:\s*\n\s*from app\.config\.settings import Config\s*\n',
                    '''try:
    from app.config.settings import Config
    config_available = True
'''
                ),
                # Случай 2: использование config_available без определения
                (
                    r'if config_available and Config\.BOT_TOKEN:',
                    '''# Проверяем доступность конфигурации
try:
    config_available = True if 'Config' in locals() or 'Config' in globals() else False
except:
    config_available = False

if config_available and hasattr(Config, 'BOT_TOKEN') and Config.BOT_TOKEN:'''
                )
            ]
            
            for pattern, replacement in patterns_to_fix:
                import re
                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                if new_content != content:
                    content = new_content
                    print(f"✅ Применен паттерн исправления")
                    break
            
            # Дополнительное исправление - добавляем определение в начало если не найдено
            if 'config_available = ' not in content:
                # Ищем место после импорта Config
                config_import_pos = content.find('from app.config.settings import Config')
                if config_import_pos != -1:
                    # Найдем конец строки
                    end_line = content.find('\n', config_import_pos)
                    if end_line != -1:
                        # Вставляем определение переменной
                        insert_text = '\n    config_available = True'
                        content = content[:end_line] + insert_text + content[end_line:]
                        print("✅ Добавлено определение config_available")
            
            # Альтернативное исправление - добавляем безопасную проверку
            safe_check = '''
# Безопасная проверка конфигурации
try:
    config_available = 'Config' in locals() or 'Config' in globals()
    if config_available:
        config_available = hasattr(Config, 'BOT_TOKEN')
except:
    config_available = False
'''
            
            # Вставляем перед использованием config_available
            if 'config_available and Config.BOT_TOKEN' in content:
                pos = content.find('config_available and Config.BOT_TOKEN')
                content = content[:pos] + safe_check + '\n' + content[pos:]
                print("✅ Добавлена безопасная проверка config_available")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def install_schedule():
    """Установка модуля schedule"""
    print("📦 Установка модуля schedule...")
    
    try:
        import subprocess
        result = subprocess.run(['pip', 'install', 'schedule==1.2.0'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Модуль schedule установлен")
            return True
        else:
            print(f"❌ Ошибка установки: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка установки: {e}")
        return False

def main():
    """Главная функция"""
    print("🔧 ИСПРАВЛЕНИЕ ОСТАВШИХСЯ ОШИБОК")
    print("=" * 50)
    
    success_count = 0
    
    # 1. Исправляем requirements.txt
    print("\n1️⃣ Исправление requirements.txt")
    if fix_requirements():
        success_count += 1
        print("✅ requirements.txt исправлен")
    else:
        print("❌ Не удалось исправить requirements.txt")
    
    # 2. Устанавливаем schedule
    print("\n2️⃣ Установка модуля schedule")
    if install_schedule():
        success_count += 1
        print("✅ Модуль schedule установлен")
    else:
        print("❌ Не удалось установить schedule")
        print("💡 Попробуйте вручную: pip install schedule==1.2.0")
    
    # 3. Исправляем config_available
    print("\n3️⃣ Исправление config_available")
    if fix_config_available():
        success_count += 1
        print("✅ config_available исправлен")
    else:
        print("❌ Не удалось исправить config_available")
    
    print("\n" + "=" * 50)
    print(f"📊 РЕЗУЛЬТАТ: {success_count}/3 исправлений применено")
    print("=" * 50)
    
    if success_count >= 2:
        print("🎉 Большинство ошибок исправлено!")
        print("\n🚀 Попробуйте перезапустить приложение:")
        print("   python working_app.py")
        print("\n💡 Если остались ошибки:")
        print("   - Перезапустите терминал")
        print("   - Проверьте установку зависимостей")
        return True
    else:
        print("⚠️ Не все ошибки удалось исправить")
        print("💡 Попробуйте ручные исправления")
        return False

if __name__ == '__main__':
    success = main()
    print("\n" + "="*50)
    if success:
        print("✨ Готово! Перезапустите приложение.")
    else:
        print("💭 Нужны дополнительные исправления.")
