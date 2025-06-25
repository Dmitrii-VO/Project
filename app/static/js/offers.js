// app/static/js/offers.js - ИСПРАВЛЕННАЯ ВЕРСИЯ

// ===== ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ ВКЛАДОК =====
function switchTab(tabName) {
    console.log('🔄 Переключение на вкладку:', tabName);

    // Убираем активные классы у навигационных карточек
    document.querySelectorAll('.nav-card').forEach(card => card.classList.remove('active'));

    // Скрываем все контенты вкладок
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Активируем выбранную навигационную карточку
    const activeCard = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeCard) {
        activeCard.classList.add('active');
    }

    // Показываем соответствующий контент
    const activeContent = document.getElementById(tabName);
    if (activeContent) {
        activeContent.classList.add('active');
    }

    // Специальные действия для каждой вкладки
    if (tabName === 'my-offers') {
        loadMyOffers();
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP =====
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// ФУНКЦИЯ ОПРЕДЕЛЕНИЯ ПРАВИЛЬНОЙ ЦЕНЫ
function getOfferPriceInfo(offer) {
    console.log('💰 Анализ цены для оффера', offer.id, ':', {
        price: offer.price,
        budget_total: offer.budget_total,
        max_price_per_post: offer.max_price_per_post
    });

    let displayPrice = 0;
    let priceType = '';

    // Приоритет: budget_total > price > max_price_per_post
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

    console.log(`💰 Результат для оффера ${offer.id}: ${displayPrice} (${priceType})`);

    return {
        amount: displayPrice,
        type: priceType,
        formatted: formatPrice(displayPrice)
    };
}
// ФУНКЦИЯ ФОРМАТИРОВАНИЯ ЦЕНЫ
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

// ФУНКЦИЯ ФОРМАТИРОВАНИЯ ДАТЫ
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

// ИСПРАВЛЕННАЯ ФУНКЦИЯ renderOffers
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
            priceType: typeof offer.price
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
        const formattedDate = formatDate(createdAt);

        console.log(`💰 Цена для оффера ${offer.id}: ${rawPrice} -> ${formattedPrice}`);

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
                
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <span style="font-size: 28px; font-weight: bold; color: #007bff;">${formattedPrice}</span>
                        <span style="font-size: 16px; color: #666; font-weight: 500;">${currency}</span>
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
                    ID: ${offer.id}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    console.log('✅ Офферы отрисованы с правильными ценами');
}

// Дополнительные функции
function editOffer(offerId) {
    alert(`Редактирование оффера ${offerId} (в разработке)`);
}

function viewOfferDetails(offerId) {
    alert(`Детали оффера ${offerId} (в разработке)`);
}

function manageResponses(offerId) {
    alert(`Управление откликами для оффера ${offerId} (в разработке)`);
}

// ===== ФУНКЦИЯ ПОЛУЧЕНИЯ USER ID =====
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

// ===== ЗАГРУЗКА МОИХ ОФФЕРОВ =====
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
}

// ===== СОСТОЯНИЯ ЗАГРУЗКИ =====
function showOffersLoading() {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner">⏳</div>
                <p>Загрузка офферов...</p>
            </div>
        `;
    }
}

function showEmptyOffersState() {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <h3>Пока нет офферов</h3>
                <p>Создайте свой первый оффер, нажав на "Создать оффер"</p>
                <button class="btn btn-primary" onclick="switchTab('create-offer')">
                    Создать оффер
                </button>
            </div>
        `;
    }
}

function showOffersError(message) {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">❌</div>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                <button class="btn btn-outline" onclick="loadMyOffers()">
                    Попробовать снова
                </button>
            </div>
        `;
    }
}

// ===== ПОИСК ПО ОФФЕРАМ =====
function setupOffersSearch() {
    const searchInput = document.getElementById('offersSearch');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const offerCards = document.querySelectorAll('.offer-card');

            offerCards.forEach(card => {
                const title = card.querySelector('.offer-title')?.textContent.toLowerCase() || '';
                
                if (title.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
}

// ===== ФУНКЦИЯ ВОЗВРАТА =====
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// ===== КЛАСС ДЛЯ СОЗДАНИЯ ОФФЕРОВ =====
class OffersManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.init();
    }

    init() {
        console.log('🎯 Инициализация OffersManager');
        this.setupEventListeners();
        this.updateStep(this.currentStep);
    }

    setupEventListeners() {
        // Кнопки навигации по шагам
        document.getElementById('nextBtn')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prevBtn')?.addEventListener('click', () => this.prevStep());
        document.getElementById('submitBtn')?.addEventListener('click', () => this.submitOffer());

        // Слайдер подписчиков
        const subscribersRange = document.querySelector('input[name="min_subscribers"]');
        const subscribersValue = document.getElementById('subscribersValue');

        if (subscribersRange && subscribersValue) {
            subscribersRange.addEventListener('input', function() {
                const value = parseInt(this.value);
                subscribersValue.textContent = value >= 1000000 ? '1M+' :
                                              value >= 1000 ? Math.round(value/1000) + 'K' :
                                              value.toString();
            });
        }
    }

    updateStep(step) {
        console.log('📝 Обновление шага:', step);

        // Обновляем индикатор шагов
        document.querySelectorAll('.step').forEach((stepEl, index) => {
            const stepNumber = index + 1;
            stepEl.classList.toggle('active', stepNumber === step);
            stepEl.classList.toggle('completed', stepNumber < step);
        });

        // Показываем/скрываем шаги формы
        document.querySelectorAll('.form-step').forEach(stepEl => {
            stepEl.style.display = stepEl.dataset.step == step ? 'block' : 'none';
        });

        // Управляем кнопками
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (prevBtn) prevBtn.style.display = step === 1 ? 'none' : 'inline-flex';
        if (nextBtn) nextBtn.style.display = step === this.totalSteps ? 'none' : 'inline-flex';
        if (submitBtn) submitBtn.style.display = step === this.totalSteps ? 'inline-flex' : 'none';
    }

    nextStep() {
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateStep(this.currentStep);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStep(this.currentStep);
        }
    }

    async submitOffer() {
    console.log('📤 Отправка оффера (исправленная версия)...');

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn?.textContent;

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создание...';
        }

        console.log('🔍 Собираем данные формы...');

        // Собираем данные из правильных полей
        const data = {
            title: '',
            description: '',
            budget_total: 0,
            price: 0,
            currency: 'RUB',
            category: 'general'
        };

        // Название
        const titleField = document.querySelector('input[name="title"]');
        if (titleField && titleField.value) {
            data.title = titleField.value.trim();
        } else {
            data.title = 'Новый оффер';
        }

        // Описание
        const descField = document.querySelector('textarea[name="description"]') ||
                         document.querySelector('input[name="description"]');
        if (descField && descField.value) {
            data.description = descField.value.trim();
        } else {
            data.description = 'Описание оффера';
        }

        // ГЛАВНОЕ ИСПРАВЛЕНИЕ: Поле price содержит общий бюджет!
        const priceField = document.querySelector('input[name="price"]');
        if (priceField && priceField.value) {
            const inputValue = parseFloat(priceField.value);
            console.log(`💰 Найдено в поле price: ${inputValue}`);

            // Определяем что это - бюджет или цена за пост
            // Если значение большое (>10000), считаем это общим бюджетом
            if (inputValue >= 10000) {
                data.budget_total = inputValue;
                data.price = Math.min(inputValue, 10000); // Устанавливаем разумную цену за пост
                console.log(`💰 Интерпретируем как общий бюджет: ${data.budget_total}`);
            } else {
                data.price = inputValue;
                data.budget_total = inputValue;
                console.log(`💰 Интерпретируем как цену за пост: ${data.price}`);
            }
        }

        // Дополнительно проверяем поле budget
        const budgetField = document.querySelector('input[name="budget"]');
        if (budgetField && budgetField.value) {
            const budgetValue = parseFloat(budgetField.value);
            if (budgetValue > 0) {
                data.budget_total = budgetValue;
                console.log(`💰 Найден отдельный бюджет: ${data.budget_total}`);
            }
        }

        // Категория
        const categoryField = document.querySelector('select[name="category"]');
        if (categoryField && categoryField.value) {
            data.category = categoryField.value;
        }

        // Дополнительные поля
        data.content = data.description;

        const audienceField = document.querySelector('input[name="target_audience"]');
        if (audienceField && audienceField.value) {
            data.target_audience = audienceField.value.trim();
        }

        // Валидация
        if (!data.title || data.title.length < 3) {
            throw new Error('Название должно содержать минимум 3 символа');
        }

        if (!data.description || data.description.length < 5) {
            throw new Error('Описание должно содержать минимум 5 символов');
        }

        if (!data.budget_total || data.budget_total <= 0) {
            throw new Error('Укажите корректный бюджет');
        }

        console.log('🚀 ОТПРАВЛЯЕМ ДАННЫЕ:');
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

            // Очищаем форму
            if (priceField) priceField.value = '';
            if (titleField) titleField.value = '';
            if (descField) descField.value = '';

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

    collectFormData() {
        const form = document.getElementById('offerForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Добавляем выбранные чипы
        data.categories = Array.from(document.querySelectorAll('.chip.selected'))
            .map(chip => chip.dataset.value || chip.textContent);

        return data;
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Инициализация страницы офферов');

    // Загружаем офферы по умолчанию (первая вкладка)
    loadMyOffers();

    // Настройка поиска
    setupOffersSearch();

    // Инициализация существующего функционала создания офферов
    // ПЕРЕОПРЕДЕЛЕНИЕ submitOffer в конце offers.js - тоже замените
if (typeof OffersManager !== 'undefined') {
    OffersManager.prototype.submitOffer = async function() {
        console.log('📤 Отправка оффера (переопределенная версия)...');

        const submitBtn = document.getElementById('submitBtn');
        const originalText = submitBtn?.textContent;

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Создание...';
            }

            // ПРАВИЛЬНЫЙ сбор данных из поля price
            const priceField = document.querySelector('input[name="price"]');
            const titleField = document.querySelector('input[name="title"]');
            const descField = document.querySelector('textarea[name="description"]') ||
                             document.querySelector('input[name="description"]');

            const inputValue = priceField ? parseFloat(priceField.value) : 0;

            const data = {
                title: titleField?.value || 'Новый оффер',
                description: descField?.value || 'Описание оффера',
                budget_total: inputValue, // Используем введенное значение как общий бюджет
                price: Math.min(inputValue, 10000), // Разумная цена за пост
                currency: 'RUB',
                category: 'general'
            };

            data.content = data.description;

            console.log('🚀 Отправляем данные (переопределенная версия):', data);

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
    };
}

    console.log('✅ Страница офферов инициализирована');
});

// ===== ЭКСПОРТ ФУНКЦИЙ =====
window.switchTab = switchTab;
window.loadMyOffers = loadMyOffers;
window.goBack = goBack;
window.OffersManager = OffersManager;
window.getTelegramUserId = getTelegramUserId;


// ИСПРАВЛЕНИЕ ОСНОВНОЙ ФОРМЫ - добавьте в конец offers.js

// ОТЛАДКА ЦЕН - добавьте в конец offers.js
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const debugBtn = document.createElement('button');
        debugBtn.textContent = '💰 Отладка цен';
        debugBtn.style.cssText = 'position: fixed; top: 60px; right: 10px; z-index: 9999; background: #28a745; color: white; border: none; padding: 8px; border-radius: 5px; font-size: 12px;';
        debugBtn.onclick = function() {
            console.log('🔍 ОТЛАДКА ЦЕН ОФФЕРОВ');
            fetch('/api/offers/my', {
                headers: { 'X-Telegram-User-Id': getTelegramUserId() }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.offers) {
                    data.offers.forEach((offer, index) => {
                        console.log(`Оффер ${index + 1}:`);
                        console.log('  ID:', offer.id);
                        console.log('  Цена (исходная):', offer.price, typeof offer.price);
                        console.log('  Цена (форматированная):', formatPrice(offer.price));
                        console.log('  ---');
                    });
                }
            });
        };
        document.body.appendChild(debugBtn);
    }, 1000);
});

// КНОПКА ДИАГНОСТИКИ ЦЕН - добавьте в конец offers.js
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const priceDebugBtn = document.createElement('button');
        priceDebugBtn.textContent = '🔍 Анализ цен';
        priceDebugBtn.style.cssText = 'position: fixed; top: 110px; right: 10px; z-index: 9999; background: #dc3545; color: white; border: none; padding: 8px; border-radius: 5px; font-size: 12px;';
        priceDebugBtn.onclick = function() {
            console.log('🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ЦЕН ОФФЕРОВ');
            console.log('=' * 50);

            fetch('/api/offers/my', {
                headers: { 'X-Telegram-User-Id': getTelegramUserId() }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.offers) {
                    data.offers.forEach((offer, index) => {
                        console.log(`\n📋 Оффер ${index + 1} (ID: ${offer.id}):`);
                        console.log('  Название:', offer.title);
                        console.log('  price:', offer.price, typeof offer.price);
                        console.log('  budget_total:', offer.budget_total, typeof offer.budget_total);
                        console.log('  max_price_per_post:', offer.max_price_per_post, typeof offer.max_price_per_post);

                        const priceInfo = getOfferPriceInfo(offer);
                        console.log('  → Отображается:', priceInfo.formatted, `(${priceInfo.type})`);
                        console.log('  ---');
                    });
                }
            });
        };
        document.body.appendChild(priceDebugBtn);
    }, 1000);
});

// ОТЛАДКА ПОЛЕЙ ФОРМЫ - добавьте в offers.js
function debugFormFields() {
    console.log('🔍 ОТЛАДКА ПОЛЕЙ ФОРМЫ');
    console.log('========================');

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

    console.log('\n💰 ПОЛЯ ЦЕНЫ/БЮДЖЕТА:');
    priceFields.forEach(selector => {
        const field = document.querySelector(selector);
        if (field) {
            console.log(`${selector}: "${field.value}" (name: ${field.name})`);
        }
    });

    return true;
}

// КНОПКА ПРОВЕРКИ ФОРМЫ
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const formDebugBtn = document.createElement('button');
        formDebugBtn.textContent = '🔍 Проверка формы';
        formDebugBtn.style.cssText = 'position: fixed; top: 160px; right: 10px; z-index: 9999; background: #6f42c1; color: white; border: none; padding: 8px; border-radius: 5px; font-size: 12px;';
        formDebugBtn.onclick = function() {
            console.log('🔍 ПРОВЕРКА ФОРМЫ СОЗДАНИЯ ОФФЕРА');
            debugFormFields();
        };
        document.body.appendChild(formDebugBtn);
    }, 1000);
});