#!/usr/bin/env python3
"""
create_app_structure.py - Создание структуры директорий приложения
Запустите этот скрипт для создания всех необходимых директорий и файлов
"""

import os
import sys

def create_directory_structure():
    """Создание полной структуры директорий"""
    
    # Основные директории
    directories = [
        'app',
        'app/config',
        'app/models',
        'app/services',
        'app/api',
        'app/templates',
        'app/templates/components',
        'app/templates/pages',
        'app/templates/pages/offers',
        'app/templates/pages/channels',
        'app/templates/pages/analytics',
        'app/templates/pages/payments',
        'app/static',
        'app/static/css',
        'app/static/js',
        'app/static/js/components',
        'app/static/js/utils',
        'app/static/images',
        'app/static/images/icons',
        'app/static/images/logos',
        'app/utils',
        'migrations',
        'migrations/versions',
        'tests',
        'tests/test_api',
        'tests/test_services',
        'tests/test_models',
        'scripts',
        'docs',
        'logs'
    ]
    
    created_dirs = []
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                created_dirs.append(directory)
                print(f"✅ Создана директория: {directory}")
            except Exception as e:
                print(f"❌ Ошибка создания {directory}: {e}")
        else:
            print(f"📁 Директория уже существует: {directory}")
    
    return created_dirs

def create_init_files():
    """Создание __init__.py файлов"""
    
    init_files = {
        'app/__init__.py': '''# app/__init__.py
"""
Главный модуль приложения Telegram Mini App
"""

import os
import sys
import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app() -> Flask:
    """Фабрика приложений Flask"""
    app = Flask(__name__)
    
    # Базовая конфигурация
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    return app

# Для обратной совместимости
app = None

def get_app():
    """Получение экземпляра приложения"""
    global app
    if app is None:
        app = create_app()
    return app
''',
        
        'app/config/__init__.py': '''# app/config/__init__.py
"""Модуль конфигурации приложения"""

try:
    from .settings import Config
    __all__ = ['Config']
except ImportError:
    __all__ = []
''',
        
        'app/models/__init__.py': '''# app/models/__init__.py
"""Модуль моделей данных"""

__all__ = []
''',
        
        'app/services/__init__.py': '''# app/services/__init__.py
"""Модуль сервисов и бизнес-логики"""

__all__ = []
''',
        
        'app/api/__init__.py': '''# app/api/__init__.py
"""API модуль для Telegram Mini App"""

__all__ = []

def get_available_blueprints():
    """Получить список доступных Blueprint'ов"""
    return []
''',
        
        'app/utils/__init__.py': '''# app/utils/__init__.py
"""Модуль утилит и вспомогательных функций"""

__all__ = []
''',
        
        'migrations/__init__.py': '''# migrations/__init__.py
"""Модуль миграций базы данных"""

__all__ = []
''',
        
        'tests/__init__.py': '''# tests/__init__.py
"""Модуль тестов"""

__all__ = []
''',
    }
    
    created_files = []
    
    for file_path, content in init_files.items():
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created_files.append(file_path)
                print(f"✅ Создан файл: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка создания {file_path}: {e}")
        else:
            print(f"📄 Файл уже существует: {file_path}")
    
    return created_files

def create_basic_templates():
    """Создание базовых шаблонов"""
    
    templates = {
        'app/templates/base.html': '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Telegram Mini App{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div id="app">
        {% block content %}{% endblock %}
    </div>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
''',
        
        'app/templates/index.html': '''{% extends "base.html" %}

{% block title %}Главная - Telegram Mini App{% endblock %}

{% block content %}
<div class="container">
    <h1>🚀 Telegram Mini App</h1>
    <p>Добро пожаловать в систему рекламных размещений!</p>
    
    <div class="navigation">
        <a href="/offers" class="btn">📢 Офферы</a>
        <a href="/channels" class="btn">📺 Каналы</a>
        <a href="/analytics" class="btn">📊 Аналитика</a>
    </div>
</div>
{% endblock %}
''',
    }
    
    created_templates = []
    
    for file_path, content in templates.items():
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created_templates.append(file_path)
                print(f"✅ Создан шаблон: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка создания {file_path}: {e}")
    
    return created_templates

def create_basic_static_files():
    """Создание базовых статических файлов"""
    
    static_files = {
        'app/static/css/style.css': '''/* Базовые стили для Telegram Mini App */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: var(--tg-theme-bg-color, #ffffff);
    color: var(--tg-theme-text-color, #000000);
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}

.btn {
    display: inline-block;
    padding: 12px 24px;
    margin: 8px;
    background-color: var(--tg-theme-button-color, #007bff);
    color: var(--tg-theme-button-text-color, #ffffff);
    text-decoration: none;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-size: 16px;
}

.btn:hover {
    opacity: 0.8;
}

.navigation {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 20px;
}

h1 {
    text-align: center;
    margin-bottom: 20px;
}
''',
        
        'app/static/js/app.js': '''// Основной JavaScript для Telegram Mini App

// Инициализация Telegram WebApp
window.Telegram = window.Telegram || {};
window.Telegram.WebApp = window.Telegram.WebApp || {
    ready: function() { console.log('Telegram WebApp ready'); },
    expand: function() { console.log('Telegram WebApp expand'); },
    close: function() { console.log('Telegram WebApp close'); }
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Telegram Mini App загружен');
    
    // Инициализация Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
    
    // Основная логика приложения
    initializeApp();
});

function initializeApp() {
    console.log('Инициализация приложения...');
    
    // Здесь будет основная логика
    setupEventListeners();
}

function setupEventListeners() {
    // Настройка обработчиков событий
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Кнопка нажата:', e.target.textContent);
        });
    });
}
''',
    }
    
    created_static = []
    
    for file_path, content in static_files.items():
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                created_static.append(file_path)
                print(f"✅ Создан статический файл: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка создания {file_path}: {e}")
    
    return created_static

def main():
    """Главная функция создания структуры"""
    print("🏗️ СОЗДАНИЕ СТРУКТУРЫ ПРИЛОЖЕНИЯ")
    print("=" * 50)
    
    # Создание директорий
    print("\n📁 Создание директорий...")
    created_dirs = create_directory_structure()
    
    # Создание __init__.py файлов
    print("\n📄 Создание __init__.py файлов...")
    created_inits = create_init_files()
    
    # Создание базовых шаблонов
    print("\n🎨 Создание базовых шаблонов...")
    created_templates = create_basic_templates()
    
    # Создание статических файлов
    print("\n🎯 Создание статических файлов...")
    created_static = create_basic_static_files()
    
    print("\n" + "=" * 50)
    print("✅ СТРУКТУРА ПРИЛОЖЕНИЯ СОЗДАНА!")
    print("=" * 50)
    
    total_created = len(created_dirs) + len(created_inits) + len(created_templates) + len(created_static)
    
    print(f"📊 Создано объектов: {total_created}")
    print(f"   📁 Директории: {len(created_dirs)}")
    print(f"   📄 __init__.py: {len(created_inits)}")
    print(f"   🎨 Шаблоны: {len(created_templates)}")
    print(f"   🎯 Статические файлы: {len(created_static)}")
    
    print("\n🎉 Теперь можно запускать приложение!")
    print("💡 Следующие шаги:")
    print("   1. Создайте файлы конфигурации (уже сделано)")
    print("   2. Запустите: python working_app.py")
    print("   3. Откройте: http://localhost:5000")

if __name__ == '__main__':
    main()
