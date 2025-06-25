#!/usr/bin/env python3
"""
Исправление отображения цены в карточках офферов
"""

def create_price_fix():
    """Создаем исправление для отображения цены"""
    
    price_fix = '''
// ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ ЦЕНЫ - замените в функции renderOffers

// Улучшенное форматирование цены
function formatPrice(price) {
    console.log('💰 Форматируем цену:', price, 'тип:', typeof price);
    
    let numericPrice = 0;
    
    // Преобразуем в число
    if (typeof price === 'string') {
        // Убираем все нечисловые символы кроме точки и запятой
        const cleanPrice = price.replace(/[^0-9.,]/g, '').replace(',', '.');
        numericPrice = parseFloat(cleanPrice) || 0;
    } else if (typeof price === 'number') {
        numericPrice = price;
    } else {
        numericPrice = 0;
    }
    
    console.log('💰 Числовая цена:', numericPrice);
    
    // Форматируем с разделителями тысяч
    if (numericPrice === 0) {
        return '0';
    }
    
    // Русский формат с пробелами как разделители тысяч
    return numericPrice.toLocaleString('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

// Замените эту часть в функции renderOffers:
offers.forEach((offer, index) => {
    console.log(`📋 Обрабатываем оффер ${index + 1}:`, offer);
    console.log('💰 Исходная цена:', offer.price, 'тип:', typeof offer.price);
    
    // Безопасное получение данных с fallback значениями
    const title = offer.title || 'Без названия';
    const description = offer.description || offer.content || 'Нет описания';
    const price = offer.price || 0;
    const currency = offer.currency || 'RUB';
    const category = offer.category || 'Не указана';
    const status = offer.status || 'active';
    const deadline = offer.deadline || 'Не указан';
    const responseCount = offer.response_count || 0;
    const acceptedCount = offer.accepted_count || 0;
    const createdAt = offer.created_at || '';
    
    // ИСПРАВЛЕННОЕ форматирование цены
    const formattedPrice = formatPrice(price);
    console.log('💰 Отформатированная цена:', formattedPrice);
    
    // ... остальной код без изменений
'''
    
    print("💰 ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ ЦЕНЫ")
    print("-" * 50)
    print("Добавьте эту функцию и измените renderOffers:")
    print(price_fix)

def create_complete_fixed_render():
    """Создаем полностью исправленную функцию renderOffers"""
    
    fixed_render = '''
// ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ФУНКЦИЯ renderOffers

// Функция форматирования цены
function formatPrice(price) {
    console.log('💰 Форматируем цену:', price, 'тип:', typeof price);
    
    let numericPrice = 0;
    
    // Преобразуем в число
    if (typeof price === 'string') {
        const cleanPrice = price.replace(/[^0-9.,]/g, '').replace(',', '.');
        numericPrice = parseFloat(cleanPrice) || 0;
    } else if (typeof price === 'number') {
        numericPrice = price;
    } else {
        numericPrice = 0;
    }
    
    // Форматируем с разделителями тысяч
    if (numericPrice === 0) {
        return '0';
    }
    
    return numericPrice.toLocaleString('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

// Функция форматирования даты
function formatDate(dateString) {
    if (!dateString) return 'Не указана';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// Основная функция отрисовки
function renderOffers(offers) {
    console.log('🎨 Отрисовка офферов:', offers.length);
    const container = document.getElementById('offersGrid');
    
    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    if (!offers || offers.length === 0) {
        showEmptyOffersState();
        return;
    }

    let html = '';
    
    offers.forEach((offer, index) => {
        console.log(`📋 Оффер ${index + 1}:`, {
            id: offer.id,
            title: offer.title,
            price: offer.price,
            priceType: typeof offer.price,
            currency: offer.currency
        });
        
        // Безопасное получение данных
        const title = offer.title || 'Без названия';
        const description = offer.description || offer.content || 'Нет описания';
        const rawPrice = offer.price || 0;
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'Не указана';
        const status = offer.status || 'active';
        const deadline = offer.deadline || 'Не указан';
        const responseCount = offer.response_count || 0;
        const createdAt = offer.created_at || '';
        
        // ИСПРАВЛЕННОЕ форматирование цены
        const formattedPrice = formatPrice(rawPrice);
        
        // Форматирование даты
        const formattedDate = formatDate(createdAt);
        
        // Определяем статус
        const statusClass = status === 'active' ? 'status-active' : 'status-inactive';
        const statusText = {
            'active': 'Активен',
            'paused': 'Приостановлен',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        }[status] || 'Неизвестно';
        
        // Обрезаем описание
        const shortDescription = description.length > 150 ? 
            description.substring(0, 150) + '...' : description;
        
        html += `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3 class="offer-title">${title}</h3>
                    <span class="offer-status ${statusClass}">${statusText}</span>
                </div>
                
                <div class="offer-price-section">
                    <div class="offer-price">
                        <span class="price-amount">${formattedPrice}</span>
                        <span class="price-currency">${currency}</span>
                    </div>
                </div>
                
                <div class="offer-details">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">📁 Категория</span>
                            <span class="detail-value">${category}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📅 Дедлайн</span>
                            <span class="detail-value">${deadline}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📊 Откликов</span>
                            <span class="detail-value">${responseCount}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📅 Создан</span>
                            <span class="detail-value">${formattedDate}</span>
                        </div>
                    </div>
                </div>
                
                <div class="offer-description">
                    <p>${shortDescription}</p>
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-outline" onclick="editOffer(${offer.id})" title="Редактировать">
                        ✏️ Редактировать
                    </button>
                    <button class="btn btn-primary" onclick="viewOfferDetails(${offer.id})" title="Подробнее">
                        👁️ Подробнее
                    </button>
                    ${responseCount > 0 ? `
                    <button class="btn btn-success" onclick="viewResponses(${offer.id})" title="Просмотр откликов">
                        💬 Отклики (${responseCount})
                    </button>` : ''}
                </div>
                
                <div class="offer-meta">
                    <small class="text-muted">ID: ${offer.id}</small>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    console.log('✅ Офферы отрисованы');
}
'''
    
    print("\n🎨 ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ФУНКЦИЯ")
    print("-" * 50)
    print("Замените всю функцию renderOffers на эту версию:")
    print(fixed_render)

def create_price_debug_function():
    """Создаем функцию для отладки цен"""
    
    debug_function = '''
// ОТЛАДОЧНАЯ ФУНКЦИЯ - добавьте в offers.js для диагностики

function debugPrices() {
    console.log('🔍 ОТЛАДКА ЦЕН');
    console.log('=' * 40);
    
    // Получаем данные офферов напрямую
    fetch('/api/offers/my', {
        headers: {
            'X-Telegram-User-Id': getTelegramUserId()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.offers) {
            console.log('📊 Анализ цен офферов:');
            
            data.offers.forEach((offer, index) => {
                console.log(`Оффер ${index + 1}:`);
                console.log('  ID:', offer.id);
                console.log('  Название:', offer.title);
                console.log('  Цена (исходная):', offer.price);
                console.log('  Тип цены:', typeof offer.price);
                console.log('  Валюта:', offer.currency);
                console.log('  Цена (отформатированная):', formatPrice(offer.price));
                console.log('  ---');
            });
        }
    })
    .catch(error => {
        console.error('Ошибка получения данных:', error);
    });
}

// Добавляем кнопку отладки цен
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const debugBtn = document.createElement('button');
        debugBtn.textContent = '💰 Отладка цен';
        debugBtn.style.cssText = 'position: fixed; top: 60px; right: 10px; z-index: 9999; background: #28a745; color: white; border: none; padding: 8px; border-radius: 5px; font-size: 12px;';
        debugBtn.onclick = debugPrices;
        document.body.appendChild(debugBtn);
    }, 1000);
});
'''
    
    print("\n🔍 ОТЛАДОЧНАЯ ФУНКЦИЯ")
    print("-" * 50)
    print("Добавьте эту функцию для диагностики проблем с ценой:")
    print(debug_function)

def main():
    """Главная функция"""
    print("💰 ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ ЦЕНЫ В ОФФЕРАХ")
    print("=" * 60)
    
    print("❌ ПРОБЛЕМА: Цена отображается неправильно")
    print("🎯 ПРИЧИНЫ:")
    print("- Цена приходит как строка вместо числа")
    print("- Неправильное форматирование")
    print("- Отсутствие обработки edge cases")
    
    create_price_fix()
    create_complete_fixed_render()
    create_price_debug_function()
    
    print("\n📋 ПЛАН ДЕЙСТВИЙ:")
    print("1. Добавьте функцию formatPrice()")
    print("2. Замените функцию renderOffers() полностью")
    print("3. Добавьте отладочную кнопку")
    print("4. Обновите страницу и проверьте")
    
    print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("- Корректное отображение цен с разделителями тысяч")
    print("- Правильная обработка всех типов данных")
    print("- Красивое форматирование в русском стиле")

if __name__ == '__main__':
    main()
