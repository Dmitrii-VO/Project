#!/usr/bin/env python3
"""
install_missing_deps.py - Установка недостающих зависимостей
Автоматически устанавливает все необходимые пакеты для работы приложения
"""

import subprocess
import sys
import os

def run_command(command):
    """Выполнение команды с выводом результата"""
    try:
        print(f"🔄 Выполняется: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ Успешно: {command}")
        if result.stdout:
            print(f"   Вывод: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {command}")
        print(f"   Код ошибки: {e.returncode}")
        if e.stderr:
            print(f"   Ошибка: {e.stderr.strip()}")
        return False

def check_pip():
    """Проверка наличия pip"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip доступен")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip недоступен")
        return False

def install_package(package_name):
    """Установка отдельного пакета"""
    command = f"{sys.executable} -m pip install {package_name}"
    return run_command(command)

def install_from_requirements():
    """Установка из requirements.txt"""
    if os.path.exists("requirements.txt"):
        print("📄 Найден requirements.txt, устанавливаем зависимости...")
        command = f"{sys.executable} -m pip install -r requirements.txt"
        return run_command(command)
    else:
        print("⚠️ requirements.txt не найден")
        return False

def install_critical_packages():
    """Установка критически важных пакетов"""
    critical_packages = [
        "aiohttp==3.9.1",
        "asyncio-mqtt",
        "python-telegram-bot==20.7", 
        "flask==3.0.0",
        "python-dotenv==1.0.0",
        "requests==2.32.3"
    ]
    
    print("🔧 Установка критически важных пакетов...")
    success_count = 0
    
    for package in critical_packages:
        if install_package(package):
            success_count += 1
        else:
            print(f"⚠️ Не удалось установить {package}, пропускаем...")
    
    print(f"📊 Установлено {success_count} из {len(critical_packages)} пакетов")
    return success_count > 0

def test_imports():
    """Тестирование импортов после установки"""
    test_modules = [
        ("aiohttp", "aiohttp"),
        ("flask", "Flask"),
        ("dotenv", "python-dotenv"),
        ("requests", "requests")
    ]
    
    print("🧪 Тестирование импортов...")
    
    for module_name, package_name in test_modules:
        try:
            __import__(module_name)
            print(f"✅ {package_name}: импорт успешен")
        except ImportError:
            print(f"❌ {package_name}: импорт неудачен")

def upgrade_pip():
    """Обновление pip до последней версии"""
    print("⬆️ Обновление pip...")
    command = f"{sys.executable} -m pip install --upgrade pip"
    return run_command(command)

def clear_cache():
    """Очистка кэша pip"""
    print("🧹 Очистка кэша pip...")
    command = f"{sys.executable} -m pip cache purge"
    return run_command(command)

def main():
    """Главная функция установки"""
    print("📦 УСТАНОВКА НЕДОСТАЮЩИХ ЗАВИСИМОСТЕЙ")
    print("=" * 50)
    
    # Проверка pip
    if not check_pip():
        print("❌ pip недоступен! Установите Python правильно.")
        return False
    
    # Обновление pip
    upgrade_pip()
    
    # Очистка кэша (на всякий случай)
    clear_cache()
    
    # Попытка установки из requirements.txt
    print("\n📄 Попытка установки из requirements.txt...")
    requirements_success = install_from_requirements()
    
    # Установка критических пакетов
    print("\n🔧 Установка критически важных пакетов...")
    critical_success = install_critical_packages()
    
    # Тестирование импортов
    print("\n🧪 Проверка установленных модулей...")
    test_imports()
    
    print("\n" + "=" * 50)
    
    if requirements_success or critical_success:
        print("🎉 УСТАНОВКА ЗАВЕРШЕНА!")
        print("✅ Основные зависимости установлены")
        print("\n🚀 Теперь попробуйте запустить:")
        print("  python working_app.py")
        print("\n💡 Если остались ошибки, устанавливайте пакеты по мере необходимости:")
        print("  pip install <package_name>")
        return True
    else:
        print("❌ УСТАНОВКА НЕ УДАЛАСЬ")
        print("💡 Попробуйте установить вручную:")
        print("  pip install aiohttp")
        print("  pip install python-telegram-bot")
        print("  pip install flask")
        return False

if __name__ == '__main__':
    success = main()
    
    if success:
        print("\n✨ Готово! Запускайте приложение.")
    else:
        print("\n💥 Требуется ручная установка зависимостей.")
        print("🔧 Основные команды:")
        print("  pip install aiohttp")
        print("  pip install python-telegram-bot") 
        print("  pip install flask python-dotenv requests")
