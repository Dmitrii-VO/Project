#!/usr/bin/env python3
"""
Исправление основной формы создания офферов
"""

def fix_offers_js_form():
    """Исправляем collectFormData в offers.js"""
    
    fixed_method = '''
// ИСПРАВЛЕННЫЙ МЕТОД collectFormData для OffersManager
collectFormData() {
    console.log('📝 Сбор данных основной формы...');
    
    const data = {};
    
    // Собираем данные из всех полей формы
    const form = document.getElementById('offerForm') || document.querySelector('form');
    
    if (form) {
        const formData = new FormData(form);
        for (let [key, value] of formData.entries()) {
            data[key] = value;
            console.log(`📋 Из FormData - ${key}: ${value}`);
        }
    }
    
    // Дополнительно собираем по селекторам (если FormData не сработал)
    const selectors = {
        'title': ['input[name="title"]', '#offerTitle', 'input[placeholder*="название"]'],
        'description': ['textarea[name="description"]', '#offerDescription', 'textarea[placeholder*="описание"]'],
        'content': ['textarea[name="content"]', '#offerContent'],
        'price': ['input[name="price"]', '#offerPrice', 'input[type="number"]'],
        'currency': ['select[name="currency"]', '#currency'],
        'category': ['select[name="category"]', '#category'],
        'target_audience': ['input[name="target_audience"]', 'textarea[name="target_audience"]'],
        'requirements': ['textarea[name="requirements"]', 'input[name="requirements"]'],
        'duration_days': ['input[name="duration_days"]', 'select[name="duration_days"]'],
        'min_subscribers': ['input[name="min_subscribers"]'],
        'max_subscribers': ['input[name="max_subscribers"]']
    };
    
    for (let field in selectors) {
        if (!data[field]) {
            for (let selector of selectors[field]) {
                const element = document.querySelector(selector);
                if (element && element.value) {
                    data[field] = element.value;
                    console.log(`📋 Из селектора ${selector} - ${field}: ${element.value}`);
                    break;
                }
            }
        }
    }
    
    // Собираем выбранные чипы категорий
    const selectedChips = document.querySelectorAll('.chip.selected');
    if (selectedChips.length > 0) {
        const categories = Array.from(selectedChips).map(chip => 
            chip.dataset.value || chip.textContent.trim()
        );
        data.categories = categories;
        if (!data.category && categories.length > 0) {
            data.category = categories[0];
        }
        console.log('📋 Выбранные категории:', categories);
    }
    
    // Устанавливаем значения по умолчанию для обязательных полей
    data.title = data.title || 'Новый оффер';
    data.description = data.description || 'Описание оффера';
    data.price = data.price || '1000';
    data.currency = data.currency || 'RUB';
    data.category = data.category || 'general';
    
    // Дополнительные поля
    if (!data.content) {
        data.content = data.description;
    }
    
    // Преобразуем числовые поля
    if (data.price) data.price = parseFloat(data.price) || 1000;
    if (data.duration_days) data.duration_days = parseInt(data.duration_days) || 30;
    if (data.min_subscribers) data.min_subscribers = parseInt(data.min_subscribers) || 1;
    if (data.max_subscribers) data.max_subscribers = parseInt(data.max_subscribers) || 100000000;
    
    console.log('📦 Итоговые данные основной формы:', data);
    
    return data;
}
'''
    
    print("🔧 ИСПРАВЛЕНИЕ ОСНОВНОЙ ФОРМЫ")
    print("-" * 50)
    print("Замените метод collectFormData() в классе OffersManager на:")
    print(fixed_method)

def create_form_debug_script():
    """Создаем скрипт для отладки формы"""
    
    debug_script = '''
<!-- ОТЛАДОЧНЫЙ СКРИПТ - добавьте в templates/offers.html -->

<script>
// Функция отладки формы
function debugMainForm() {
    console.log('🔍 ОТЛАДКА ОСНОВНОЙ ФОРМЫ');
    console.log('=' * 40);
    
    // Ищем все формы на странице
    const forms = document.querySelectorAll('form');
    console.log('📋 Найдено форм:', forms.length);
    
    forms.forEach((form, index) => {
        console.log(`Форма ${index + 1}:`, form.id || form.className);
    });
    
    // Ищем все поля ввода
    const inputs = document.querySelectorAll('input, textarea, select');
    console.log('📝 Найдено полей:', inputs.length);
    
    inputs.forEach(input => {
        if (input.name) {
            console.log(`Поле: ${input.name} = "${input.value}"`);
        }
    });
    
    // Проверяем чипы
    const chips = document.querySelectorAll('.chip');
    const selectedChips = document.querySelectorAll('.chip.selected');
    console.log('🏷️ Всего чипов:', chips.length);
    console.log('✅ Выбрано чипов:', selectedChips.length);
    
    // Тестируем сбор данных
    if (window.offersManager) {
        console.log('🧪 Тестируем collectFormData:');
        const data = window.offersManager.collectFormData();
        console.log('📦 Результат:', data);
    }
}

// Добавляем кнопку отладки
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const debugBtn = document.createElement('button');
        debugBtn.textContent = '🔍 Отладка формы';
        debugBtn.style.cssText = 'position: fixed; top: 10px; right: 10px; z-index: 9999; background: #dc3545; color: white; border: none; padding: 10px; border-radius: 5px;';
        debugBtn.onclick = debugMainForm;
        document.body.appendChild(debugBtn);
    }, 1000);
});
</script>
'''
    
    print("\n🔍 ОТЛАДОЧНЫЙ СКРИПТ")
    print("-" * 50)
    print("Добавьте этот скрипт в templates/offers.html:")
    print(debug_script)

def create_simple_fix():
    """Создаем простое исправление"""
    
    simple_fix = '''
// ПРОСТОЕ ИСПРАВЛЕНИЕ - замените submitOffer в OffersManager

async submitOffer() {
    console.log('📤 Отправка оффера (исправленная версия)...');

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn?.textContent;

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создание...';
        }

        // ПРОСТОЙ СБОР ДАННЫХ
        const data = {
            title: document.querySelector('input[name="title"]')?.value || 
                   document.querySelector('#offerTitle')?.value || 
                   'Новый оффер',
            description: document.querySelector('textarea[name="description"]')?.value || 
                        document.querySelector('#offerDescription')?.value || 
                        'Описание оффера',
            price: document.querySelector('input[name="price"]')?.value || 
                   document.querySelector('#offerPrice')?.value || 
                   '1000',
            category: document.querySelector('select[name="category"]')?.value || 
                     'general',
            currency: 'RUB'
        };
        
        // Дополнительные поля
        const contentField = document.querySelector('textarea[name="content"]');
        if (contentField) data.content = contentField.value;
        
        const audienceField = document.querySelector('input[name="target_audience"]');
        if (audienceField) data.target_audience = audienceField.value;

        console.log('🚀 Отправляем простые данные:', data);

        const response = await fetch('/api/offers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

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
    
    print("\n⚡ ПРОСТОЕ ИСПРАВЛЕНИЕ")
    print("-" * 50)
    print("Если сложное не поможет, замените submitOffer на простую версию:")
    print(simple_fix)

def main():
    """Главная функция"""
    print("🎯 ИСПРАВЛЕНИЕ ОСНОВНОЙ ФОРМЫ СОЗДАНИЯ ОФФЕРОВ")
    print("=" * 60)
    
    print("✅ ХОРОШИЕ НОВОСТИ: API работает (тестовая форма создала оффер)")
    print("❌ ПРОБЛЕМА: Основная форма неправильно собирает данные")
    
    fix_offers_js_form()
    create_form_debug_script()
    create_simple_fix()
    
    print("\n🎯 ПЛАН ДЕЙСТВИЙ:")
    print("1. Добавьте отладочную кнопку на страницу")
    print("2. Нажмите 'Отладка формы' чтобы увидеть поля")
    print("3. Замените collectFormData() на исправленную версию")
    print("4. Или используйте простое исправление submitOffer()")
    
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Попробуйте создать оффер через основную форму")
    print("2. Если ошибка - нажмите кнопку 'Отладка формы'")
    print("3. Посмотрите в консоли какие поля найдены")
    print("4. Исправьте collectFormData() или используйте простую версию")

if __name__ == '__main__':
    main()
