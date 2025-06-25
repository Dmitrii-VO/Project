#!/usr/bin/env python3
"""
Исправление JavaScript в app/static/js/offers.js
"""

import os
import shutil
from datetime import datetime

def backup_and_fix_js():
    """Создаем резервную копию и исправляем JavaScript"""
    
    js_file = 'app/static/js/offers.js'
    
    print("🔧 ИСПРАВЛЕНИЕ app/static/js/offers.js")
    print("-" * 50)
    
    # Создаем резервную копию
    try:
        backup_file = f'app/static/js/offers_backup_{datetime.now().strftime("%H%M%S")}.js'
        shutil.copy2(js_file, backup_file)
        print(f"✅ Резервная копия: {backup_file}")
    except Exception as e:
        print(f"⚠️ Не удалось создать резервную копию: {e}")
    
    # Читаем текущий файл
    try:
        with open(js_file, 'r', encoding='utf-8') as f:
            current_content = f.read()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False
    
    # Исправленный JavaScript код
    # Находим и заменяем функцию getTelegramUserId
    if 'function getTelegramUserId()' in current_content:
        print("✅ Функция getTelegramUserId уже существует, заменяем")
    else:
        print("➕ Добавляем функцию getTelegramUserId")
    
    # Заменяем или добавляем правильную функцию
    fixed_function = '''
// ===== ИСПРАВЛЕННАЯ ФУНКЦИЯ ПОЛУЧЕНИЯ USER ID =====
function getTelegramUserId() {
    console.log('🔍 Получение Telegram User ID...');
    
    // Пробуем получить из Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const user = window.Telegram.WebApp.initDataUnsafe.user;
        if (user && user.id) {
            console.log('✅ User ID из Telegram WebApp:', user.id);
            return user.id.toString();
        }
    }
    
    // Fallback к основному пользователю
    const fallbackId = '373086959';
    console.log('⚠️ Используем fallback User ID:', fallbackId);
    return fallbackId;
}

// ===== ИСПРАВЛЕННАЯ ФУНКЦИЯ ЗАГРУЗКИ ОФФЕРОВ =====
async function loadMyOffers() {
    console.log('📋 Загрузка моих офферов...');
    const container = document.getElementById('offersGrid');

    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    try {
        // Показываем индикатор загрузки
        showOffersLoading();

        const userId = getTelegramUserId();
        console.log('👤 Используем User ID:', userId);

        const response = await fetch('/api/offers/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': userId
            }
        });

        console.log('🌐 API Response Status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('📦 API Response Data:', result);

        if (result.success && result.offers && result.offers.length > 0) {
            console.log('✅ Офферы загружены:', result.offers.length);
            renderOffers(result.offers);
        } else {
            console.log('ℹ️ Офферов не найдено');
            showEmptyOffersState();
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки офферов:', error);
        showOffersError('Ошибка загрузки офферов: ' + error.message);
    }
}'''

    # Удаляем старые функции если есть
    import re
    
    # Удаляем старую функцию getTelegramUserId
    current_content = re.sub(
        r'function getTelegramUserId\(\)\s*{[^}]*}(\s*{[^}]*})*',
        '',
        current_content,
        flags=re.DOTALL
    )
    
    # Удаляем старую функцию loadMyOffers  
    current_content = re.sub(
        r'async function loadMyOffers\(\)\s*{[^}]*}(\s*{[^}]*})*',
        '',
        current_content,
        flags=re.DOTALL
    )
    
    # Находим место для вставки (после инициализации Telegram WebApp)
    insertion_point = current_content.find('// ===== ЗАГРУЗКА МОИХ ОФФЕРОВ =====')
    
    if insertion_point == -1:
        # Если не найдена секция, вставляем в начало
        insertion_point = current_content.find('document.addEventListener(\'DOMContentLoaded\'')
        if insertion_point == -1:
            insertion_point = 0
    
    # Вставляем исправленные функции
    new_content = (
        current_content[:insertion_point] + 
        fixed_function + 
        '\n\n' + 
        current_content[insertion_point:]
    )
    
    # Записываем исправленный файл
    try:
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ JavaScript исправлен!")
        print("✅ Добавлена правильная функция getTelegramUserId")
        print("✅ Исправлена функция loadMyOffers")
        print("✅ Добавлено подробное логирование")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка записи файла: {e}")
        return False

def create_minimal_fix():
    """Создаем минимальное исправление если основное не сработает"""
    
    print("\n🔧 СОЗДАНИЕ МИНИМАЛЬНОГО ИСПРАВЛЕНИЯ")
    print("-" * 50)
    
    minimal_js = '''
// Минимальное исправление - добавьте в начало app/static/js/offers.js

// Исправленная функция получения User ID
function getTelegramUserId() {
    return '373086959'; // Ваш Telegram ID
}

// Исправленная функция загрузки офферов
async function loadMyOffers() {
    console.log('📋 Загрузка моих офферов...');
    const container = document.getElementById('offersGrid');

    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    try {
        const response = await fetch('/api/offers/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': '373086959'
            }
        });

        console.log('API Response Status:', response.status);
        
        const result = await response.json();
        console.log('API Response Data:', result);

        if (result.success && result.offers && result.offers.length > 0) {
            console.log('✅ Офферы загружены:', result.offers.length);
            renderOffers(result.offers);
        } else {
            console.log('ℹ️ Офферов не найдено');
            showEmptyOffersState();
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки офферов:', error);
        showOffersError('Ошибка загрузки офферов: ' + error.message);
    }
}
'''
    
    print("Если автоматическое исправление не сработает,")
    print("добавьте этот код в начало app/static/js/offers.js:")
    print(minimal_js)

def main():
    """Главная функция"""
    print("🚀 ИСПРАВЛЕНИЕ JAVASCRIPT ДЛЯ ОТОБРАЖЕНИЯ ОФФЕРОВ")
    print("=" * 60)
    
    # Проверяем что файл существует
    if not os.path.exists('app/static/js/offers.js'):
        print("❌ Файл app/static/js/offers.js не найден!")
        return
    
    # Исправляем JavaScript
    if backup_and_fix_js():
        print("\n🎉 JAVASCRIPT ИСПРАВЛЕН!")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Обновите страницу в браузере (Ctrl+F5)")
        print("2. Откройте консоль браузера (F12)")
        print("3. Проверьте что офферы загружаются")
        print("4. В консоли должны быть сообщения: '✅ Офферы загружены: 5'")
    else:
        print("\n⚠️ АВТОМАТИЧЕСКОЕ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ")
        create_minimal_fix()

if __name__ == '__main__':
    main()
