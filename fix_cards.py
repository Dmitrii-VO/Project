#!/usr/bin/env python3
"""
Исправление отображения данных в карточках офферов
"""

def fix_render_offers_function():
    """Исправляем функцию renderOffers"""
    
    fixed_function = '''
// ИСПРАВЛЕННАЯ ФУНКЦИЯ renderOffers - замените в offers.js

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
        console.log(`📋 Обрабатываем оффер ${index + 1}:`, offer);
        
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
        const targetAudience = offer.target_audience || 'Не указана';
        const requirements = offer.requirements || 'Не указаны';
        
        // Форматируем цену
        const formattedPrice = typeof price === 'number' ? 
            price.toLocaleString('ru-RU') : 
            parseFloat(price).toLocaleString('ru-RU');
        
        // Форматируем дату создания
        let formattedDate = '';
        if (createdAt) {
            try {
                const date = new Date(createdAt);
                formattedDate = date.toLocaleDateString('ru-RU');
            } catch (e) {
                formattedDate = createdAt;
            }
        }
        
        // Определяем статус и его стиль
        const statusClass = status === 'active' ? 'status-active' : 'status-inactive';
        const statusText = status === 'active' ? 'Активен' : 
                          status === 'paused' ? 'Приостановлен' :
                          status === 'completed' ? 'Завершен' :
                          status === 'cancelled' ? 'Отменен' : 'Неизвестно';
        
        // Обрезаем длинное описание
        const shortDescription = description.length > 150 ? 
            description.substring(0, 150) + '...' : description;
        
        html += `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3 class="offer-title" title="${title}">${title}</h3>
                    <span class="offer-status ${statusClass}">${statusText}</span>
                </div>
                
                <div class="offer-info">
                    <div class="offer-price">
                        <span class="price-amount">${formattedPrice}</span>
                        <span class="price-currency">${currency}</span>
                    </div>
                </div>
                
                <div class="offer-details">
                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">📁 Категория:</span>
                            <span class="detail-value">${category}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📅 Дедлайн:</span>
                            <span class="detail-value">${deadline}</span>
                        </div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">📊 Откликов:</span>
                            <span class="detail-value">${responseCount}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">✅ Принято:</span>
                            <span class="detail-value">${acceptedCount}</span>
                        </div>
                    </div>
                    
                    ${targetAudience !== 'Не указана' ? `
                    <div class="detail-row">
                        <div class="detail-item full-width">
                            <span class="detail-label">🎯 Аудитория:</span>
                            <span class="detail-value">${targetAudience}</span>
                        </div>
                    </div>` : ''}
                    
                    ${requirements !== 'Не указаны' ? `
                    <div class="detail-row">
                        <div class="detail-item full-width">
                            <span class="detail-label">📋 Требования:</span>
                            <span class="detail-value">${requirements}</span>
                        </div>
                    </div>` : ''}
                </div>
                
                <div class="offer-description">
                    <p>${shortDescription}</p>
                </div>
                
                <div class="offer-meta">
                    <span class="creation-date">Создан: ${formattedDate}</span>
                    <span class="offer-id">ID: ${offer.id}</span>
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-outline" onclick="editOffer(${offer.id})" title="Редактировать оффер">
                        ✏️ Редактировать
                    </button>
                    <button class="btn btn-secondary" onclick="viewOfferDetails(${offer.id})" title="Подробная информация">
                        👁️ Подробнее
                    </button>
                    <button class="btn btn-primary" onclick="manageResponses(${offer.id})" title="Управление откликами">
                        💬 Отклики (${responseCount})
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    console.log('✅ Офферы отрисованы');
}
'''
    
    print("🎨 ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ КАРТОЧЕК")
    print("-" * 50)
    print("Замените функцию renderOffers() в offers.js на:")
    print(fixed_function)

def create_improved_css():
    """Создаем улучшенные стили для карточек"""
    
    css_styles = '''
/* УЛУЧШЕННЫЕ СТИЛИ ДЛЯ КАРТОЧЕК - добавьте в CSS */

.offer-card {
    background: #ffffff;
    border: 1px solid #e1e5e9;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.offer-card:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
}

.offer-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 15px;
}

.offer-title {
    font-size: 18px;
    font-weight: 600;
    color: #2c3e50;
    margin: 0;
    flex: 1;
    margin-right: 15px;
    line-height: 1.3;
}

.offer-status {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
}

.status-active {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.status-inactive {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.offer-info {
    margin-bottom: 15px;
}

.offer-price {
    display: flex;
    align-items: baseline;
    gap: 5px;
}

.price-amount {
    font-size: 24px;
    font-weight: 700;
    color: #007bff;
}

.price-currency {
    font-size: 16px;
    color: #6c757d;
    font-weight: 500;
}

.offer-details {
    margin-bottom: 15px;
}

.detail-row {
    display: flex;
    gap: 20px;
    margin-bottom: 8px;
}

.detail-item {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.detail-item.full-width {
    flex: 1 1 100%;
}

.detail-label {
    font-size: 13px;
    color: #6c757d;
    font-weight: 500;
}

.detail-value {
    font-size: 13px;
    color: #2c3e50;
    font-weight: 600;
    text-align: right;
}

.offer-description {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 15px;
}

.offer-description p {
    margin: 0;
    font-size: 14px;
    line-height: 1.4;
    color: #495057;
}

.offer-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    font-size: 12px;
    color: #6c757d;
}

.offer-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.btn {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    border: 1px solid;
    cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.btn-outline {
    background: #ffffff;
    color: #6c757d;
    border-color: #dee2e6;
}

.btn-outline:hover {
    background: #e9ecef;
    color: #495057;
}

.btn-secondary {
    background: #6c757d;
    color: #ffffff;
    border-color: #6c757d;
}

.btn-secondary:hover {
    background: #5a6268;
    border-color: #545b62;
}

.btn-primary {
    background: #007bff;
    color: #ffffff;
    border-color: #007bff;
}

.btn-primary:hover {
    background: #0056b3;
    border-color: #004085;
}

/* Адаптивность */
@media (max-width: 768px) {
    .detail-row {
        flex-direction: column;
        gap: 5px;
    }
    
    .detail-item {
        justify-content: flex-start;
        gap: 10px;
    }
    
    .detail-value {
        text-align: left;
    }
    
    .offer-actions {
        flex-direction: column;
    }
    
    .btn {
        justify-content: center;
    }
}
'''
    
    print("\n🎨 УЛУЧШЕННЫЕ СТИЛИ")
    print("-" * 50)
    print("Добавьте эти стили в CSS файл:")
    print(css_styles)

def create_additional_functions():
    """Создаем дополнительные функции для работы с офферами"""
    
    functions = '''
// ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ - добавьте в offers.js

function manageResponses(offerId) {
    console.log('💬 Управление откликами для оффера:', offerId);
    
    // Временная заглушка
    alert(`Управление откликами для оффера ${offerId}\\n(Функция в разработке)`);
    
    // TODO: Реализовать открытие модального окна с откликами
}

function editOffer(offerId) {
    console.log('✏️ Редактирование оффера:', offerId);
    
    // Временная заглушка
    alert(`Редактирование оффера ${offerId}\\n(Функция в разработке)`);
    
    // TODO: Реализовать форму редактирования
}

function viewOfferDetails(offerId) {
    console.log('👁️ Просмотр деталей оффера:', offerId);
    
    // Получаем детальную информацию об оффере
    fetch(`/api/offers/detail/${offerId}`, {
        headers: {
            'X-Telegram-User-Id': getTelegramUserId()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.offer) {
            showOfferDetailsModal(data.offer);
        } else {
            alert('Ошибка получения деталей оффера');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка получения деталей оффера');
    });
}

function showOfferDetailsModal(offer) {
    const modal = `
        <div class="modal-overlay" onclick="closeModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${offer.title}</h3>
                    <button onclick="closeModal()" class="close-btn">×</button>
                </div>
                <div class="modal-body">
                    <div class="detail-section">
                        <h4>📊 Основная информация</h4>
                        <p><strong>Цена:</strong> ${offer.price} ${offer.currency}</p>
                        <p><strong>Категория:</strong> ${offer.category}</p>
                        <p><strong>Статус:</strong> ${offer.status}</p>
                        <p><strong>Дедлайн:</strong> ${offer.deadline}</p>
                    </div>
                    
                    <div class="detail-section">
                        <h4>📝 Описание</h4>
                        <p>${offer.description}</p>
                    </div>
                    
                    ${offer.target_audience ? `
                    <div class="detail-section">
                        <h4>🎯 Целевая аудитория</h4>
                        <p>${offer.target_audience}</p>
                    </div>` : ''}
                    
                    ${offer.requirements ? `
                    <div class="detail-section">
                        <h4>📋 Требования</h4>
                        <p>${offer.requirements}</p>
                    </div>` : ''}
                    
                    <div class="detail-section">
                        <h4>📊 Статистика</h4>
                        <p><strong>Бюджет:</strong> ${offer.budget_total || offer.price} ${offer.currency}</p>
                        <p><strong>Подписчики:</strong> ${offer.min_subscribers} - ${offer.max_subscribers}</p>
                        <p><strong>Создан:</strong> ${offer.created_at}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modal);
}

function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
    }
}

// Глобальные функции
window.manageResponses = manageResponses;
window.editOffer = editOffer;
window.viewOfferDetails = viewOfferDetails;
window.closeModal = closeModal;
'''
    
    print("\n🔧 ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ")
    print("-" * 50)
    print("Добавьте эти функции в offers.js:")
    print(functions)

def main():
    """Главная функция"""
    print("🎨 ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ КАРТОЧЕК ОФФЕРОВ")
    print("=" * 60)
    
    print("✅ ПРОБЛЕМА: Офферы отображаются, но данные неправильные")
    print("🎯 РЕШЕНИЕ: Исправляем функцию renderOffers и добавляем стили")
    
    fix_render_offers_function()
    create_improved_css()
    create_additional_functions()
    
    print("\n📋 ПЛАН ДЕЙСТВИЙ:")
    print("1. Замените функцию renderOffers() в offers.js")
    print("2. Добавьте улучшенные CSS стили")
    print("3. Добавьте дополнительные функции")
    print("4. Обновите страницу и проверьте результат")
    
    print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("- Корректное отображение всех данных оффера")
    print("- Красивые карточки с правильной информацией")
    print("- Рабочие кнопки действий")
    print("- Модальное окно с деталями оффера")

if __name__ == '__main__':
    main()
