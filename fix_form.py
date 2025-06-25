#!/usr/bin/env python3
"""
Исправление отправки формы создания офферов
"""

def create_debug_form_submission():
    """Создаем отладочную версию отправки формы"""
    
    debug_js = '''
// ОТЛАДОЧНАЯ ВЕРСИЯ ОТПРАВКИ ФОРМЫ - добавьте в offers.js

// Улучшенная функция сбора данных формы
collectFormData() {
    console.log('📝 Сбор данных формы...');
    
    // Получаем все поля формы
    const form = document.getElementById('offerForm') || document.querySelector('form');
    
    if (!form) {
        console.error('❌ Форма не найдена!');
        return {};
    }
    
    const data = {};
    
    // Собираем данные из input полей
    const inputs = form.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        if (input.name && input.value) {
            data[input.name] = input.value;
            console.log(`📋 ${input.name}: ${input.value}`);
        }
    });
    
    // Обязательные поля с fallback значениями
    if (!data.title) {
        data.title = document.querySelector('input[name="title"]')?.value || 
                    document.querySelector('#offerTitle')?.value ||
                    'Новый оффер';
    }
    
    if (!data.description) {
        data.description = document.querySelector('textarea[name="description"]')?.value || 
                          document.querySelector('#offerDescription')?.value ||
                          'Описание оффера';
    }
    
    if (!data.price) {
        data.price = document.querySelector('input[name="price"]')?.value || 
                    document.querySelector('#offerPrice')?.value ||
                    '1000';
    }
    
    // Дополнительные поля
    data.currency = data.currency || 'RUB';
    data.category = data.category || 'general';
    data.content = data.content || data.description;
    
    console.log('📦 Собранные данные:', data);
    return data;
}

// Улучшенная функция отправки оффера
async submitOffer() {
    console.log('📤 Отправка оффера...');

    const submitBtn = document.getElementById('submitBtn') || 
                     document.querySelector('.btn-primary[type="submit"]') ||
                     document.querySelector('button[onclick*="submit"]');
    
    const originalText = submitBtn?.textContent;

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создание...';
        }

        // Собираем данные формы
        const formData = this.collectFormData();
        
        // Валидируем обязательные поля
        if (!formData.title || formData.title.length < 5) {
            throw new Error('Название должно содержать минимум 5 символов');
        }
        
        if (!formData.price || parseFloat(formData.price) <= 0) {
            throw new Error('Укажите корректную цену');
        }

        console.log('🚀 Отправляем данные:', formData);

        const response = await fetch('/api/offers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify(formData)
        });

        console.log('📡 Статус ответа:', response.status);
        
        const result = await response.json();
        console.log('📥 Ответ сервера:', result);

        if (response.ok && result.success) {
            console.log('✅ Оффер создан успешно!');
            alert('✅ Оффер успешно создан!');
            
            // Очищаем форму
            this.clearForm();
            
            // Переходим на вкладку "Мои офферы"
            switchTab('my-offers');
        } else {
            const errorMsg = result.error || result.errors?.join(', ') || 'Неизвестная ошибка';
            throw new Error(errorMsg);
        }

    } catch (error) {
        console.error('❌ Ошибка создания оффера:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText || 'Создать оффер';
        }
    }
}

// Функция очистки формы
clearForm() {
    const form = document.getElementById('offerForm') || document.querySelector('form');
    if (form) {
        form.reset();
        console.log('🧹 Форма очищена');
    }
}
'''
    
    print("🔧 ОТЛАДОЧНАЯ ВЕРСИЯ ОТПРАВКИ ФОРМЫ")
    print("-" * 50)
    print("Замените методы collectFormData() и submitOffer() в OffersManager на:")
    print(debug_js)

def create_minimal_test_form():
    """Создаем минимальную тестовую форму"""
    
    test_html = '''
<!-- ТЕСТОВАЯ ФОРМА - добавьте в templates/offers.html -->

<div class="test-form-section" style="margin: 20px; padding: 20px; border: 2px solid #007bff;">
    <h3>🧪 Быстрый тест создания оффера</h3>
    
    <form id="quickTestForm">
        <div style="margin-bottom: 15px;">
            <label>Название:</label>
            <input type="text" name="title" value="Тестовый оффер" required style="width: 100%; padding: 8px;">
        </div>
        
        <div style="margin-bottom: 15px;">
            <label>Описание:</label>
            <textarea name="description" required style="width: 100%; padding: 8px;">Описание тестового оффера</textarea>
        </div>
        
        <div style="margin-bottom: 15px;">
            <label>Цена:</label>
            <input type="number" name="price" value="1500" required style="width: 100%; padding: 8px;">
        </div>
        
        <div style="margin-bottom: 15px;">
            <label>Категория:</label>
            <select name="category" style="width: 100%; padding: 8px;">
                <option value="general">Общее</option>
                <option value="tech">Технологии</option>
                <option value="business">Бизнес</option>
            </select>
        </div>
        
        <button type="button" onclick="testQuickForm()" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px;">
            🚀 Быстрый тест
        </button>
    </form>
</div>

<script>
async function testQuickForm() {
    console.log('🧪 Быстрый тест создания оффера');
    
    const form = document.getElementById('quickTestForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    console.log('📦 Данные для отправки:', data);
    
    try {
        const response = await fetch('/api/offers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': '373086959'
            },
            body: JSON.stringify(data)
        });
        
        console.log('📡 Статус:', response.status);
        const result = await response.json();
        console.log('📥 Ответ:', result);
        
        if (result.success) {
            alert('✅ Тест успешен! Оффер создан.');
            loadMyOffers(); // Обновляем список
        } else {
            alert('❌ Ошибка: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('❌ Ошибка теста:', error);
        alert('❌ Ошибка: ' + error.message);
    }
}
</script>
'''
    
    print("\n🧪 ТЕСТОВАЯ ФОРМА")
    print("-" * 50)
    print("Добавьте эту тестовую форму в templates/offers.html для быстрой проверки:")
    print(test_html)

def create_api_debug_endpoint():
    """Создаем отладочный endpoint для API"""
    
    debug_api = '''
# Добавьте в app/api/offers.py для отладки

@offers_bp.route('/debug/form', methods=['POST'])
def debug_form_submission():
    """Отладочный endpoint для проверки данных формы"""
    try:
        data = request.get_json()
        user_id = get_user_id_from_request()
        
        return jsonify({
            'success': True,
            'received_data': data,
            'user_id': user_id,
            'headers': dict(request.headers),
            'data_type': type(data).__name__,
            'data_keys': list(data.keys()) if data else []
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'request_data': request.get_data(as_text=True)
        })
'''
    
    print("\n🔍 ОТЛАДОЧНЫЙ API ENDPOINT")
    print("-" * 50)
    print("Добавьте этот endpoint в app/api/offers.py:")
    print(debug_api)

def main():
    """Главная функция"""
    print("🔧 ИСПРАВЛЕНИЕ СОЗДАНИЯ ОФФЕРОВ")
    print("=" * 60)
    
    print("ПРОБЛЕМА: 400 Bad Request при создании оффера")
    print("ПРИЧИНА: Некорректные данные формы или отсутствие обязательных полей")
    
    # Предлагаем решения
    create_debug_form_submission()
    create_minimal_test_form()
    create_api_debug_endpoint()
    
    print("\n🎯 ПЛАН ДЕЙСТВИЙ:")
    print("1. Добавьте тестовую форму в templates/offers.html")
    print("2. Протестируйте создание через простую форму")
    print("3. Если работает - исправьте основную форму")
    print("4. Добавьте отладочный endpoint для диагностики")
    
    print("\n🔍 ДЛЯ ДИАГНОСТИКИ:")
    print("1. Откройте консоль браузера при отправке формы")
    print("2. Проверьте какие данные отправляются")
    print("3. Проверьте ответ сервера с ошибкой")

if __name__ == '__main__':
    main()
