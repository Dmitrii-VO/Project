#!/usr/bin/env python3
"""
Исправление логики отображения цены в офферах
"""

def analyze_price_issue():
    """Анализируем проблему с ценой"""
    print("🔍 АНАЛИЗ ПРОБЛЕМЫ С ЦЕНОЙ")
    print("-" * 50)
    print("❌ ПРОБЛЕМА:")
    print("- В форме указывается общий бюджет: 55,555")
    print("- В карточке отображается цена за размещение: 2,500")
    print("- Неправильное поле используется для отображения")
    
    print("\n🎯 ПРИЧИНЫ:")
    print("1. Форма сохраняет общий бюджет в поле 'budget_total'")
    print("2. Карточка отображает поле 'price' (цена за размещение)")
    print("3. Нужно определить какое поле показывать")

def create_price_debug():
    """Создаем отладку для проверки полей цены"""
    
    debug_code = '''
// ОТЛАДКА ПОЛЕЙ ЦЕНЫ - добавьте в offers.js

function debugOfferPriceFields(offer) {
    console.log('🔍 ОТЛАДКА ПОЛЕЙ ЦЕНЫ для оффера', offer.id);
    console.log('===================================');
    console.log('price:', offer.price, typeof offer.price);
    console.log('budget_total:', offer.budget_total, typeof offer.budget_total);
    console.log('max_price_per_post:', offer.max_price_per_post, typeof offer.max_price_per_post);
    console.log('currency:', offer.currency);
    console.log('===================================');
    
    return {
        mainPrice: offer.budget_total || offer.price || 0,
        pricePerPost: offer.price || offer.max_price_per_post || 0,
        budgetTotal: offer.budget_total || 0
    };
}

// Измените в функции renderOffers:
offers.forEach((offer, index) => {
    // ОТЛАДКА ПОЛЕЙ ЦЕНЫ
    const priceData = debugOfferPriceFields(offer);
    
    // Определяем какую цену показывать
    const displayPrice = priceData.budgetTotal > 0 ? priceData.budgetTotal : priceData.pricePerPost;
    const priceLabel = priceData.budgetTotal > 0 ? 'Общий бюджет' : 'Цена за размещение';
    
    console.log(`💰 Отображаем для оффера ${offer.id}: ${displayPrice} (${priceLabel})`);
    
    // ... остальной код
});
'''
    
    print("\n🔍 ОТЛАДОЧНЫЙ КОД")
    print("-" * 50)
    print("Добавьте этот код для диагностики:")
    print(debug_code)

def create_fixed_price_display():
    """Создаем исправленное отображение цены"""
    
    fixed_code = '''
// ИСПРАВЛЕННОЕ ОТОБРАЖЕНИЕ ЦЕНЫ - замените в renderOffers

function getOfferPriceInfo(offer) {
    console.log('💰 Анализ цены для оффера', offer.id, ':', {
        price: offer.price,
        budget_total: offer.budget_total,
        max_price_per_post: offer.max_price_per_post
    });
    
    // Приоритет отображения:
    // 1. budget_total (общий бюджет) - если указан и больше 0
    // 2. price (основная цена)
    // 3. max_price_per_post (максимальная цена за пост)
    
    let displayPrice = 0;
    let priceType = '';
    
    if (offer.budget_total && parseFloat(offer.budget_total) > 0) {
        displayPrice = offer.budget_total;
        priceType = 'Общий бюджет';
    } else if (offer.price && parseFloat(offer.price) > 0) {
        displayPrice = offer.price;
        priceType = 'Цена за размещение';
    } else if (offer.max_price_per_post && parseFloat(offer.max_price_per_post) > 0) {
        displayPrice = offer.max_price_per_post;
        priceType = 'Макс. цена за пост';
    } else {
        displayPrice = 0;
        priceType = 'Цена не указана';
    }
    
    console.log(`💰 Результат для оффера ${offer.id}: ${displayPrice} (${priceType})`);
    
    return {
        amount: displayPrice,
        type: priceType,
        formatted: formatPrice(displayPrice)
    };
}

// В функции renderOffers замените блок с ценой:
offers.forEach((offer, index) => {
    // ... остальной код ...
    
    // ИСПРАВЛЕННОЕ получение цены
    const priceInfo = getOfferPriceInfo(offer);
    const currency = offer.currency || 'RUB';
    
    // ... в HTML блоке замените секцию цены:
    <div style="margin-bottom: 15px;">
        <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 5px;">
            <span style="font-size: 28px; font-weight: bold; color: #007bff;">${priceInfo.formatted}</span>
            <span style="font-size: 16px; color: #666; font-weight: 500;">${currency}</span>
        </div>
        <div style="font-size: 12px; color: #666; font-style: italic;">
            ${priceInfo.type}
        </div>
    </div>
    
    // ... остальной HTML ...
});
'''
    
    print("\n💰 ИСПРАВЛЕННАЯ ЛОГИКА ЦЕНЫ")
    print("-" * 50)
    print("Замените логику определения цены:")
    print(fixed_code)

def create_complete_fixed_render():
    """Создаем полностью исправленную функцию renderOffers"""
    
    complete_code = '''
// ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ renderOffers с правильной логикой цены

function getOfferPriceInfo(offer) {
    let displayPrice = 0;
    let priceType = '';
    
    if (offer.budget_total && parseFloat(offer.budget_total) > 0) {
        displayPrice = offer.budget_total;
        priceType = 'Общий бюджет';
    } else if (offer.price && parseFloat(offer.price) > 0) {
        displayPrice = offer.price;
        priceType = 'Цена за размещение';
    } else {
        displayPrice = 0;
        priceType = 'Цена не указана';
    }
    
    return {
        amount: displayPrice,
        type: priceType,
        formatted: formatPrice(displayPrice)
    };
}

function renderOffers(offers) {
    console.log('🎨 Отрисовка офферов с исправленной ценой:', offers.length);
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
        console.log(`📋 Оффер ${index + 1} (ID: ${offer.id}):`);
        console.log('  Исходные данные цены:', {
            price: offer.price,
            budget_total: offer.budget_total,
            max_price_per_post: offer.max_price_per_post
        });
        
        // Безопасное получение данных
        const title = offer.title || 'Без названия';
        const description = offer.description || offer.content || 'Нет описания';
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'Не указана';
        const status = offer.status || 'active';
        const deadline = offer.deadline || 'Не указан';
        const responseCount = offer.response_count || 0;
        const createdAt = offer.created_at || '';
        
        // ИСПРАВЛЕННОЕ получение цены
        const priceInfo = getOfferPriceInfo(offer);
        const formattedDate = formatDate(createdAt);
        
        console.log(`💰 Отображаемая цена для оффера ${offer.id}: ${priceInfo.formatted} (${priceInfo.type})`);
        
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
            <div class="offer-card" data-offer-id="${offer.id}" style="background: white; border: 1px solid #ddd; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div class="offer-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #333; font-size: 18px; font-weight: 600;">${title}</h3>
                    <span style="padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; background: ${status === 'active' ? '#d4edda' : '#f8d7da'}; color: ${status === 'active' ? '#155724' : '#721c24'};">${statusText}</span>
                </div>
                
                <div style="margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 5px;">
                        <span style="font-size: 28px; font-weight: bold; color: #007bff;">${priceInfo.formatted}</span>
                        <span style="font-size: 16px; color: #666; font-weight: 500;">${currency}</span>
                    </div>
                    <div style="font-size: 12px; color: #666; font-style: italic;">
                        ${priceInfo.type}
                    </div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #666;">📁 Категория:</span>
                            <span style="font-weight: 600;">${category}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #666;">📅 Дедлайн:</span>
                            <span style="font-weight: 600;">${deadline}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #666;">📊 Откликов:</span>
                            <span style="font-weight: 600;">${responseCount}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #666;">📅 Создан:</span>
                            <span style="font-weight: 600;">${formattedDate}</span>
                        </div>
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                    <p style="margin: 0; font-size: 14px; line-height: 1.4; color: #495057;">${shortDescription}</p>
                </div>
                
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="editOffer(${offer.id})" style="padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        ✏️ Редактировать
                    </button>
                    <button onclick="viewOfferDetails(${offer.id})" style="padding: 8px 16px; border: 1px solid #007bff; background: #007bff; color: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        👁️ Подробнее
                    </button>
                    ${responseCount > 0 ? `
                    <button onclick="manageResponses(${offer.id})" style="padding: 8px 16px; border: 1px solid #28a745; background: #28a745; color: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        💬 Отклики (${responseCount})
                    </button>` : ''}
                </div>
                
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    ID: ${offer.id} | 
                    ${offer.budget_total && parseFloat(offer.budget_total) > 0 ? 
                        `Бюджет: ${formatPrice(offer.budget_total)} ${currency}` : 
                        `Цена за пост: ${formatPrice(offer.price || 0)} ${currency}`}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    console.log('✅ Офферы отрисованы с правильной логикой цены');
}
'''
    
    print("\n🎨 ПОЛНАЯ ИСПРАВЛЕННАЯ ФУНКЦИЯ")
    print("-" * 50)
    print("Замените всю функцию renderOffers:")
    print(complete_code)

def main():
    """Главная функция"""
    print("💰 ИСПРАВЛЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ")
    print("=" * 60)
    
    analyze_price_issue()
    create_price_debug()
    create_fixed_price_display()
    create_complete_fixed_render()
    
    print("\n📋 ПЛАН ДЕЙСТВИЙ:")
    print("1. Добавьте функцию getOfferPriceInfo()")
    print("2. Замените функцию renderOffers полностью")
    print("3. Обновите страницу и проверьте")
    print("4. Проверьте консоль - должны быть логи цен")
    
    print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("- Оффер с budget_total=55555 покажет 55,555 руб (Общий бюджет)")
    print("- Оффер с price=2500 покажет 2,500 руб (Цена за размещение)")
    print("- Правильные подписи под ценами")

if __name__ == '__main__':
    main()
