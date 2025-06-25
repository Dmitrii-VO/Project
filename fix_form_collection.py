#!/usr/bin/env python3
"""
Исправление сбора данных из формы создания оффера
"""

def analyze_form_problem():
    """Анализируем проблему со сбором данных формы"""
    print("🔍 АНАЛИЗ ПРОБЛЕМЫ С ФОРМОЙ")
    print("-" * 50)
    print("❌ ПРОБЛЕМА:")
    print("- В форме указали: бюджет 55,555")
    print("- В БД сохранилось: budget_total = 2,500")
    print("- Форма собирает не те данные или неправильно")
    
    print("\n🎯 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("1. collectFormData() берет данные из неправильных полей")
    print("2. В форме есть несколько полей с ценой")
    print("3. JavaScript переписывает значения")
    print("4. Валидация изменяет данные")

def create_form_debug():
    """Создаем отладку формы"""
    
    debug_code = '''
// ОТЛАДКА ФОРМЫ - добавьте в offers.js

function debugFormFields() {
    console.log('🔍 ОТЛАДКА ПОЛЕЙ ФОРМЫ');
    console.log('=' * 40);
    
    // Находим все поля ввода
    const allInputs = document.querySelectorAll('input, textarea, select');
    console.log('📝 Найдено полей:', allInputs.length);
    
    allInputs.forEach(input => {
        if (input.name || input.id) {
            console.log(`Поле: ${input.name || input.id} = "${input.value}" (тип: ${input.type})`);
        }
    });
    
    // Проверяем специфичные поля цены/бюджета
    const priceFields = [
        'input[name="price"]',
        'input[name="budget"]', 
        'input[name="budget_total"]',
        'input[name="total_budget"]',
        'input[name="max_price"]',
        'input[name="max_price_per_post"]',
        '#offerPrice',
        '#budget',
        '#totalBudget'
    ];
    
    console.log('\\n💰 ПОЛЯ ЦЕНЫ/БЮДЖЕТА:');
    priceFields.forEach(selector => {
        const field = document.querySelector(selector);
        if (field) {
            console.log(`${selector}: "${field.value}" (name: ${field.name})`);
        }
    });
}

// Улучшенная функция сбора данных
function improvedCollectFormData() {
    console.log('📝 УЛУЧШЕННЫЙ СБОР ДАННЫХ ФОРМЫ');
    
    const data = {};
    
    // Сначала отладим поля
    debugFormFields();
    
    // Собираем данные более точно
    const form = document.getElementById('offerForm') || document.querySelector('form');
    
    if (form) {
        const formData = new FormData(form);
        for (let [key, value] of formData.entries()) {
            data[key] = value;
            console.log(`📋 FormData - ${key}: "${value}"`);
        }
    }
    
    // Специальная обработка полей цены/бюджета
    const priceSelectors = {
        'budget_total': ['input[name="budget_total"]', 'input[name="total_budget"]', '#totalBudget', 'input[placeholder*="бюджет"]'],
        'price': ['input[name="price"]', '#offerPrice', 'input[placeholder*="цена"]'],
        'max_price_per_post': ['input[name="max_price_per_post"]', 'input[name="max_price"]']
    };
    
    for (let fieldName in priceSelectors) {
        for (let selector of priceSelectors[fieldName]) {
            const field = document.querySelector(selector);
            if (field && field.value && !data[fieldName]) {
                data[fieldName] = field.value;
                console.log(`💰 Найдено ${fieldName}: "${field.value}" (селектор: ${selector})`);
                break;
            }
        }
    }
    
    console.log('📦 Итоговые данные:', data);
    return data;
}
'''
    
    print("\n🔍 ОТЛАДОЧНЫЙ КОД ФОРМЫ")
    print("-" * 50)
    print("Добавьте этот код в offers.js:")
    print(debug_code)

def create_fixed_submit_function():
    """Создаем исправленную функцию отправки"""
    
    fixed_submit = '''
// ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТПРАВКИ - замените submitOffer в OffersManager

async submitOffer() {
    console.log('📤 Отправка оффера (исправленная версия)...');

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn?.textContent;

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создание...';
        }

        // УЛУЧШЕННЫЙ СБОР ДАННЫХ
        console.log('🔍 Начинаем сбор данных формы...');
        
        // Отладим все поля
        debugFormFields();
        
        // Собираем данные пошагово
        const data = {
            title: '',
            description: '',
            budget_total: 0,
            price: 0,
            currency: 'RUB',
            category: 'general'
        };
        
        // Название
        const titleField = document.querySelector('input[name="title"]') || 
                          document.querySelector('#offerTitle') ||
                          document.querySelector('input[placeholder*="название"]');
        if (titleField) {
            data.title = titleField.value;
            console.log('📝 Название:', data.title);
        }
        
        // Описание  
        const descField = document.querySelector('textarea[name="description"]') ||
                         document.querySelector('#offerDescription') ||
                         document.querySelector('textarea[placeholder*="описание"]');
        if (descField) {
            data.description = descField.value;
            console.log('📝 Описание:', data.description);
        }
        
        // БЮДЖЕТ - ищем все возможные поля
        const budgetSelectors = [
            'input[name="budget_total"]',
            'input[name="total_budget"]', 
            'input[name="budget"]',
            '#totalBudget',
            '#budget',
            'input[placeholder*="бюджет"]',
            'input[placeholder*="Бюджет"]'
        ];
        
        for (let selector of budgetSelectors) {
            const field = document.querySelector(selector);
            if (field && field.value && parseFloat(field.value) > 0) {
                data.budget_total = parseFloat(field.value);
                console.log(`💰 Найден бюджет: ${data.budget_total} (поле: ${selector})`);
                break;
            }
        }
        
        // ЦЕНА ЗА РАЗМЕЩЕНИЕ
        const priceSelectors = [
            'input[name="price"]',
            'input[name="max_price_per_post"]',
            '#offerPrice',
            'input[placeholder*="цена"]'
        ];
        
        for (let selector of priceSelectors) {
            const field = document.querySelector(selector);
            if (field && field.value && parseFloat(field.value) > 0) {
                data.price = parseFloat(field.value);
                console.log(`💰 Найдена цена: ${data.price} (поле: ${selector})`);
                break;
            }
        }
        
        // Если не нашли бюджет, используем цену
        if (!data.budget_total && data.price) {
            data.budget_total = data.price;
            console.log('💰 Используем цену как бюджет:', data.budget_total);
        }
        
        // Категория
        const categoryField = document.querySelector('select[name="category"]') ||
                             document.querySelector('#category');
        if (categoryField) {
            data.category = categoryField.value;
            console.log('📁 Категория:', data.category);
        }
        
        // Дополнительные поля
        const contentField = document.querySelector('textarea[name="content"]');
        if (contentField && contentField.value) {
            data.content = contentField.value;
        } else {
            data.content = data.description;
        }
        
        const audienceField = document.querySelector('input[name="target_audience"]');
        if (audienceField && audienceField.value) {
            data.target_audience = audienceField.value;
        }

        // Валидация
        if (!data.title || data.title.length < 5) {
            throw new Error('Название должно содержать минимум 5 символов');
        }
        
        if (!data.description) {
            throw new Error('Укажите описание оффера');
        }
        
        if (!data.budget_total || data.budget_total <= 0) {
            throw new Error('Укажите корректный бюджет');
        }

        console.log('🚀 ФИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ОТПРАВКИ:');
        console.log(JSON.stringify(data, null, 2));

        const response = await fetch('/api/offers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        console.log('📥 Ответ сервера:', result);

        if (response.ok && result.success) {
            alert('✅ Оффер успешно создан!');
            switchTab('my-offers');
        } else {
            throw new Error(result.error || result.errors?.join(', ') || 'Ошибка создания оффера');
        }

    } catch (error) {
        console.error('❌ Ошибка создания оффера:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }
}
'''
    
    print("\n🔧 ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТПРАВКИ")
    print("-" * 50)
    print("Замените метод submitOffer в классе OffersManager:")
    print(fixed_submit)

def create_form_inspection_button():
    """Создаем кнопку для проверки формы"""
    
    button_code = '''
// КНОПКА ПРОВЕРКИ ФОРМЫ - добавьте в offers.js

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const formDebugBtn = document.createElement('button');
        formDebugBtn.textContent = '🔍 Проверка формы';
        formDebugBtn.style.cssText = 'position: fixed; top: 160px; right: 10px; z-index: 9999; background: #6f42c1; color: white; border: none; padding: 8px; border-radius: 5px; font-size: 12px;';
        formDebugBtn.onclick = function() {
            console.log('🔍 ПРОВЕРКА ФОРМЫ СОЗДАНИЯ ОФФЕРА');
            debugFormFields();
            
            // Пробуем собрать данные
            console.log('\\n📝 Пробуем собрать данные:');
            const data = improvedCollectFormData();
            
            console.log('\\n✅ Итог проверки формы завершен');
        };
        document.body.appendChild(formDebugBtn);
    }, 1000);
});
'''
    
    print("\n🔍 КНОПКА ПРОВЕРКИ ФОРМЫ")
    print("-" * 50)
    print("Добавьте эту кнопку для диагностики:")
    print(button_code)

def main():
    """Главная функция"""
    print("🔧 ИСПРАВЛЕНИЕ СБОРА ДАННЫХ ФОРМЫ")
    print("=" * 60)
    
    analyze_form_problem()
    create_form_debug()
    create_fixed_submit_function()
    create_form_inspection_button()
    
    print("\n📋 ПЛАН ДЕЙСТВИЙ:")
    print("1. Добавьте отладочные функции в offers.js")
    print("2. Замените метод submitOffer в OffersManager")
    print("3. Добавьте кнопку проверки формы")
    print("4. Обновите страницу")
    print("5. Нажмите 'Проверка формы' перед созданием оффера")
    print("6. Проверьте консоль при создании оффера")
    
    print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("- Форма правильно соберет бюджет 55,555")
    print("- В БД сохранится budget_total = 55555")
    print("- Карточка покажет '55 555 руб (Общий бюджет)'")

if __name__ == '__main__':
    main()
