// app/static/js/offers.js - ИСПРАВЛЕННАЯ ВЕРСИЯ БЕЗ КОНФЛИКТОВ

console.log('📝 Загрузка offers.js - исправленная версия');

// ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
let offersManager = null;

// ===== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP =====
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// ===== ФУНКЦИЯ ПОЛУЧЕНИЯ USER ID =====
function getTelegramUserId() {
    console.log('🔍 Получение Telegram User ID...');

    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const user = window.Telegram.WebApp.initDataUnsafe.user;
        if (user && user.id) {
            console.log('✅ User ID из Telegram WebApp:', user.id);
            return user.id.toString();
        }
    }

    const fallbackId = '373086959';
    console.log('⚠️ Используем fallback User ID:', fallbackId);
    return fallbackId;
}

// ===== ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ ВКЛАДОК =====
function switchTab(tabName) {
    console.log('🔄 Переключение на вкладку:', tabName);

    document.querySelectorAll('.nav-card').forEach(card => card.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const activeCard = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeCard) {
        activeCard.classList.add('active');
    }

    const activeContent = document.getElementById(tabName);
    if (activeContent) {
        activeContent.classList.add('active');
    }

    // Загружаем данные в зависимости от вкладки
    if (tabName === 'my-offers') {
        loadMyOffers();
    } else if (tabName === 'create-offer') {
        initializeOffersManager();
    } else if (tabName === 'find-offer') {
        setTimeout(() => {
            loadAvailableOffers({});
        }, 100);
    } else if (tabName === 'contracts') {
        // Новая вкладка контрактов
        setTimeout(() => {
            loadUserContracts();
        }, 100);
    }
}

// ===== ФУНКЦИИ ЗАГРУЗКИ И ОТОБРАЖЕНИЯ ОФФЕРОВ =====
function formatPrice(price) {
    let numericPrice = 0;

    if (typeof price === 'string') {
        const cleanPrice = price.replace(/[^0-9.,]/g, '').replace(',', '.');
        numericPrice = parseFloat(cleanPrice) || 0;
    } else if (typeof price === 'number') {
        numericPrice = price;
    }

    if (numericPrice === 0) return '0';

    return numericPrice.toLocaleString('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

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
    offers.forEach((offer) => {
        const title = offer.title || 'Без названия';
        const description = offer.description || offer.content || 'Нет описания';

        // Показываем общий бюджет для "Мои офферы"
        const displayPrice = offer.budget_total || offer.price || 0;
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'general';
        const status = offer.status || 'active';
        const responseCount = offer.response_count || offer.responses_count || offer.total_responses || 0;  // ИСПРАВЛЕНО: правильное поле
        const createdAt = offer.created_at || '';

        const formattedPrice = formatPrice(displayPrice);
        const formattedDate = formatDate(createdAt);

        const statusText = {
            'active': 'Активен',
            'paused': 'Приостановлен',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        }[status] || 'Неизвестно';

        // Сокращаем описание
        const shortDescription = description.length > 80 ?
            description.substring(0, 80) + '...' : description;

        // Сокращаем название если слишком длинное
        const shortTitle = title.length > 25 ?
            title.substring(0, 25) + '...' : title;

        html += `
            <div class="offer-card-compact" data-offer-id="${offer.id}" style="
                background: white; 
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                padding: 12px; 
                margin-bottom: 12px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                position: relative;
            ">
                <!-- Заголовок и статус -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #2d3748; font-size: 14px; font-weight: 600; flex: 1;">${shortTitle}</h3>
                    <span style="
                        padding: 2px 8px; 
                        border-radius: 12px; 
                        font-size: 10px; 
                        font-weight: 500; 
                        background: ${status === 'active' ? '#d4edda' : status === 'paused' ? '#fff3cd' : status === 'completed' ? '#d1ecf1' : '#f8d7da'}; 
                        color: ${status === 'active' ? '#155724' : status === 'paused' ? '#856404' : status === 'completed' ? '#0c5460' : '#721c24'};
                        white-space: nowrap;
                        margin-left: 8px;
                    ">${statusText}</span>
                </div>
                
                <!-- Общий бюджет крупно -->
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 18px; font-weight: bold; color: #667eea;">${formattedPrice}</span>
                    <span style="font-size: 12px; color: #718096; margin-left: 4px;">${currency}</span>
                    <div style="font-size: 10px; color: #a0aec0;">общий бюджет</div>
                </div>
                
                <!-- Краткая информация в 2 колонки -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #718096;">📁</span>
                        <span style="font-weight: 500; text-align: right;">${category}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #718096;">💬</span>
                        <span style="font-weight: 500; text-align: right;">${responseCount}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; grid-column: 1 / -1;">
                        <span style="color: #718096;">📅</span>
                        <span style="font-weight: 500;">${formattedDate}</span>
                    </div>
                </div>
                
                <!-- Краткое описание -->
                <div style="
                    background: #f7fafc; 
                    padding: 8px; 
                    border-radius: 4px; 
                    margin-bottom: 8px;
                    font-size: 11px;
                    line-height: 1.3;
                    color: #4a5568;
                ">${shortDescription}</div>
                
                <!-- Компактные кнопки -->
                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                    <!-- Кнопка "Подробнее" всегда показывается -->
                    <button onclick="viewOfferDetails(${offer.id})" style="
                        padding: 4px 8px; 
                        border: 1px solid #667eea; 
                        background: #667eea; 
                        color: white; 
                        border-radius: 4px; 
                        cursor: pointer; 
                        font-size: 10px;
                        flex: 1;
                    ">👁️ Подробнее</button>
                    
                    <!-- ИСПРАВЛЕНО: Кнопка "Отклики" если есть отклики -->
                    ${responseCount > 0 ? `
                    <button onclick="manageResponses(${offer.id})" style="
                        padding: 4px 8px; 
                        border: 1px solid #48bb78; 
                        background: #48bb78; 
                        color: white; 
                        border-radius: 4px; 
                        cursor: pointer; 
                        font-size: 10px;
                        flex: 1;
                    ">💬 ${responseCount}</button>` : ''}
                    
                    <!-- Кнопки управления в зависимости от статуса -->
                    ${status === 'active' ? `
                        <button onclick="pauseOffer(${offer.id}, this)" style="
                            padding: 4px 8px; 
                            border: 1px solid #ed8936; 
                            background: #ed8936; 
                            color: white; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 10px;
                            flex: 1;
                        ">⏸️ Пауза</button>
                        <button onclick="cancelOffer(${offer.id}, '${title.replace(/'/g, "\\'")}', this)" style="
                            padding: 4px 8px; 
                            border: 1px solid #e53e3e; 
                            background: #e53e3e; 
                            color: white; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 10px;
                            flex: 1;
                        ">❌ Отменить</button>
                    ` : ''}
                    
                    ${status === 'paused' ? `
                        <button onclick="resumeOffer(${offer.id}, this)" style="
                            padding: 4px 8px; 
                            border: 1px solid #48bb78; 
                            background: #48bb78; 
                            color: white; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 10px;
                            flex: 1;
                        ">▶️ Возобновить</button>
                        <button onclick="cancelOffer(${offer.id}, '${title.replace(/'/g, "\\'")}', this)" style="
                            padding: 4px 8px; 
                            border: 1px solid #e53e3e; 
                            background: #e53e3e; 
                            color: white; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 10px;
                            flex: 1;
                        ">❌ Отменить</button>
                    ` : ''}
                    
                    ${status === 'cancelled' || status === 'completed' ? `
                        <button onclick="deleteOffer(${offer.id}, '${title.replace(/'/g, "\\'")}', this)" style="
                            padding: 4px 8px; 
                            border: 1px solid #e53e3e; 
                            background: #e53e3e; 
                            color: white; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 10px;
                            flex: 2;
                        ">🗑️ Удалить</button>
                    ` : ''}
                </div>
                
                <!-- ID внизу мелким шрифтом -->
                <div style="margin-top: 4px; font-size: 9px; color: #a0aec0; text-align: right;">
                    ID: ${offer.id}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    console.log('✅ Компактные офферы отрисованы с правильными счетчиками откликов');
}

async function updateResponseStatus(responseId, newStatus) {
    console.log(`📝 Изменение статуса отклика ${responseId} на ${newStatus}`);

    let message = '';
    let contractDetails = {};

    if (newStatus === 'accepted') {
        // При принятии отклика сразу создаем контракт
        const contractModal = createContractDetailsModal(responseId);
        document.body.appendChild(contractModal);
        return; // Выходим, дальше обработка в модальном окне
    } else if (newStatus === 'rejected') {
        message = prompt('Причина отклонения (необязательно):');
        if (message === null) return; // Пользователь отменил
    }

    try {
        const response = await fetch(`/api/offers/responses/${responseId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                status: newStatus,
                message: message || ''
            })
        });

        const result = await response.json();

        if (result.success) {
            renderContracts(result.contracts);
        } else {
            throw new Error(result.error || 'Ошибка загрузки контрактов');
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки контрактов:', error);
        showContractsError('Ошибка загрузки контрактов: ' + error.message);
    }
}

async function loadMyOffers() {
    console.log('📋 Загрузка моих офферов...');
    const container = document.getElementById('offersGrid');

    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    try {
        showOffersLoading();

        const userId = getTelegramUserId();
        const response = await fetch('/api/offers/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': userId
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

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

// ===== КЛАСС ДЛЯ СОЗДАНИЯ ОФФЕРОВ - ИСПРАВЛЕННАЯ ВЕРСИЯ =====
class OffersManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.isInitialized = false;
    }

    init() {
        if (this.isInitialized) {
            console.log('⚠️ OffersManager уже инициализирован');
            return;
        }

        console.log('🎯 Инициализация OffersManager');
        this.setupEventListeners();
        this.updateStep(this.currentStep);
        this.isInitialized = true;
    }

    setupEventListeners() {
        console.log('🔗 Настройка обработчиков событий...');

        // Проверяем наличие кнопок и привязываем обработчики
        const nextBtn = document.getElementById('nextBtn');
        const prevBtn = document.getElementById('prevBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (nextBtn) {
            console.log('✅ Кнопка "Далее" найдена, привязываем обработчик');
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔄 Клик по кнопке "Далее"');
                this.nextStep();
            });
        } else {
            console.error('❌ Кнопка "Далее" не найдена!');
        }

        if (prevBtn) {
            console.log('✅ Кнопка "Назад" найдена, привязываем обработчик');
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔄 Клик по кнопке "Назад"');
                this.prevStep();
            });
        }

        if (submitBtn) {
            console.log('✅ Кнопка "Создать" найдена, привязываем обработчик');
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🔄 Клик по кнопке "Создать"');
                this.submitOffer();
            });
        }

        // Настройка чипов
        this.setupChips();

        // Настройка слайдера подписчиков
        this.setupSubscribersSlider();
        // Добавьте это в конец функции setupEventListeners()

        // Обновление предпросмотра при изменении полей
        const titleInput = document.querySelector('input[name="title"]');
        const budgetInput = document.querySelector('input[name="budget"]');
        const geographySelect = document.querySelector('select[name="geography"]');

        if (titleInput) {
            titleInput.addEventListener('input', () => this.updatePreview());
        }
        if (budgetInput) {
            budgetInput.addEventListener('input', () => this.updatePreview());
        }
        if (geographySelect) {
            geographySelect.addEventListener('change', () => this.updatePreview());
        }

        // Обновление при клике по чипам
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                setTimeout(() => this.updatePreview(), 10); // Небольшая задержка для обновления класса
            });
        });
    }

    setupChips() {
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', function() {
                this.classList.toggle('selected');
            });
        });
    }

    setupSubscribersSlider() {
        const subscribersRange = document.querySelector('input[name="min_subscribers"]');
        const subscribersValue = document.getElementById('subscribersValue');

        if (subscribersRange && subscribersValue) {
            subscribersRange.addEventListener('input', function() {
                const value = parseInt(this.value);
                subscribersValue.textContent = value >= 1000000 ? '1M+' :
                                              value >= 1 ? Math.round(value/1000) + 'K' :
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

        // Обновляем прогресс-бар
        const stepperProgress = document.getElementById('stepperProgress');
        if (stepperProgress) {
            const progress = ((step - 1) / (this.totalSteps - 1)) * 100;
            stepperProgress.style.width = progress + '%';
        }

        // Обновляем предпросмотр на последнем шаге
        if (step === this.totalSteps) {
            this.updatePreview();
        }

        this.currentStep = step;
    }

    nextStep() {
        console.log('➡️ Переход к следующему шагу');
        if (this.currentStep < this.totalSteps) {
            this.updateStep(this.currentStep + 1);
        }
    }

    prevStep() {
        console.log('⬅️ Переход к предыдущему шагу');
        if (this.currentStep > 1) {
            this.updateStep(this.currentStep - 1);
        }
    }

    updatePreview() {
    console.log('🔍 Обновление предпросмотра');

    // 1. НАЗВАНИЕ
    const titleInput = document.querySelector('input[name="title"]');
    const previewTitle = document.getElementById('previewTitle');
    if (previewTitle) {
        previewTitle.textContent = titleInput?.value || 'Не указано';
    }

    // 2. БЮДЖЕТ - показать и общий бюджет, и максимальную цену за размещение
    const budgetInput = document.querySelector('input[name="budget"]');
    const maxPriceInput = document.querySelector('input[name="max_price"]');
    const previewBudget = document.getElementById('previewBudget');
    if (previewBudget) {
        const budget = budgetInput?.value;
        const maxPrice = maxPriceInput?.value;

        let budgetText = '';
        if (budget) {
            budgetText += `${formatPrice(budget)} RUB общий`;
        }
        if (maxPrice) {
            if (budgetText) budgetText += ' | ';
            budgetText += `${formatPrice(maxPrice)} RUB за размещение`;
        } else if (budget) {
            // Если максимальная цена не указана, показываем расчетную
            const estimatedMaxPrice = Math.min(parseFloat(budget) * 0.1, 50000);
            if (budgetText) budgetText += ' | ';
            budgetText += `~${formatPrice(estimatedMaxPrice)} RUB за размещение`;
        }

        previewBudget.textContent = budgetText || 'Не указан';
    }

    // 3. ТЕМАТИКИ (ТОЛЬКО тематики каналов, БЕЗ возрастных групп)
    const allSelectedChips = Array.from(document.querySelectorAll('.chip.selected'))
        .map(chip => chip.textContent.trim());

    // Список возрастных групп для исключения
    const ageGroups = ['18-25 лет', '26-35 лет', '36-45 лет', '46+ лет'];

    // Фильтруем ТОЛЬКО тематики каналов
    const selectedTopics = allSelectedChips.filter(text => {
        return !ageGroups.includes(text);
    });

    const previewTopics = document.getElementById('previewTopics');
    if (previewTopics) {
        previewTopics.textContent = selectedTopics.length > 0 ? selectedTopics.join(', ') : 'Не выбраны';
    }

    // 4. ЦЕЛЕВАЯ АУДИТОРИЯ (ТОЛЬКО возрастные группы)
    const selectedAudience = allSelectedChips.filter(text => {
        return ageGroups.includes(text);
    });

    const previewAudience = document.getElementById('previewAudience');
    if (previewAudience) {
        previewAudience.textContent = selectedAudience.length > 0 ? selectedAudience.join(', ') : 'Не указана';
    }

    // 5. ГЕОГРАФИЯ
    const geographySelect = document.querySelector('select[name="geography"]');
    const previewGeography = document.getElementById('previewGeography');
    if (previewGeography) {
        const geographyValue = geographySelect?.value;
        const geographyText = {
            'russia': 'Россия',
            'cis': 'СНГ',
            'europe': 'Европа',
            'world': 'Весь мир'
        }[geographyValue] || 'Не указана';

        previewGeography.textContent = geographyText;
    }

    console.log('✅ Предпросмотр обновлен', {
        allSelected: allSelectedChips,
        topics: selectedTopics,
        audience: selectedAudience,
        geography: geographySelect?.value
    });
}

    // В функции submitOffer() класса OffersManager добавьте сохранение max_price:

    async submitOffer() {
    console.log('📤 Отправка оффера...');

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn?.textContent;

    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создание...';
        }

        // Собираем данные формы
        const data = {
            title: '',
            description: '',
            budget_total: 0,
            price: 0,
            max_price: 0,  // ДОБАВИЛИ поле max_price
            currency: 'RUB',
            category: 'general'
        };

        // Название
        const titleField = document.querySelector('input[name="title"]');
        if (titleField && titleField.value) {
            data.title = titleField.value.trim();
        } else {
            throw new Error('Укажите название оффера');
        }

        // Описание
        const descField = document.querySelector('textarea[name="description"]');
        if (descField && descField.value) {
            data.description = descField.value.trim();
        } else {
            throw new Error('Укажите описание оффера');
        }

        // Общий бюджет
        const budgetField = document.querySelector('input[name="budget"]');
        if (budgetField && budgetField.value) {
            const budgetValue = parseFloat(budgetField.value);
            if (budgetValue > 0) {
                data.budget_total = budgetValue;
            } else {
                throw new Error('Укажите корректный общий бюджет');
            }
        } else {
            throw new Error('Укажите общий бюджет');
        }

        // ИСПРАВЛЕНИЕ: Максимальная цена за размещение
        const maxPriceField = document.querySelector('input[name="max_price"]');
        if (maxPriceField && maxPriceField.value) {
            const maxPriceValue = parseFloat(maxPriceField.value);
            if (maxPriceValue > 0) {
                data.max_price = maxPriceValue;
                data.price = maxPriceValue; // Также сохраняем в price для совместимости
            } else {
                throw new Error('Укажите корректную максимальную цену за размещение');
            }
        } else {
            // Если максимальная цена не указана, используем 10% от общего бюджета
            data.max_price = Math.min(data.budget_total * 0.1, 50000);
            data.price = data.max_price;
        }

        // Категория
        const categoryField = document.querySelector('select[name="category"]');
        if (categoryField && categoryField.value) {
            data.category = categoryField.value;
        }

        data.content = data.description;

        console.log('🚀 Отправляемые данные:', data);

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

            // Очищаем форму
            document.getElementById('offerForm').reset();
            document.querySelectorAll('.chip.selected').forEach(chip => {
                chip.classList.remove('selected');
            });

            // Возвращаемся к первому шагу
            this.updateStep(1);

            // Переходим к списку офферов
            switchTab('my-offers');
        } else {
            throw new Error(result.error || 'Ошибка создания оффера');
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
}

// ===== ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ OFFERS MANAGER =====
function initializeOffersManager() {
    console.log('🎯 Инициализация менеджера офферов...');

    // Создаем экземпляр только если его еще нет
    if (!offersManager) {
        offersManager = new OffersManager();
    }

    // Небольшая задержка для уверенности что DOM готов
    setTimeout(() => {
        offersManager.init();
    }, 100);
}

// ===== ПОИСК ПО ОФФЕРАМ =====
function setupOffersSearch() {
    const searchInput = document.getElementById('offersSearch');

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const offerCards = document.querySelectorAll('.offer-card');

            offerCards.forEach(card => {
                const title = card.querySelector('h3')?.textContent.toLowerCase() || '';
                card.style.display = title.includes(searchTerm) ? 'block' : 'none';
            });
        });
    }
}

// ===== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ =====
function editOffer(offerId) {
    alert(`Редактирование оффера ${offerId} (в разработке)`);
}

function viewOfferDetails(offerId) {
    alert(`Детали оффера ${offerId} (в разработке)`);
}

function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// ===== ФУНКЦИЯ УДАЛЕНИЯ ОФФЕРА =====
async function deleteOffer(offerId, offerTitle, buttonElement) {
    console.log('🗑️ Запрос на удаление оффера:', offerId);

    // Показываем подтверждение
    const confirmMessage = `Вы уверены, что хотите удалить оффер "${offerTitle}"?\n\nЭто действие нельзя отменить.`;

    if (!confirm(confirmMessage)) {
        console.log('❌ Удаление отменено пользователем');
        return;
    }

    const originalText = buttonElement?.textContent;

    try {
        // Блокируем кнопку
        if (buttonElement) {
            buttonElement.disabled = true;
            buttonElement.textContent = '⏳ Удаление...';
            buttonElement.style.opacity = '0.6';
        }

        console.log('🌐 Отправляем запрос на удаление...');

        const response = await fetch(`/api/offers/${offerId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();
        console.log('📥 Ответ сервера:', result);

        if (response.ok && result.success) {
            console.log('✅ Оффер успешно удален');

            // Показываем сообщение об успехе
            alert(`✅ ${result.message || 'Оффер успешно удален'}`);

            // Убираем карточку из интерфейса с анимацией
            const offerCard = buttonElement?.closest('.offer-card');
            if (offerCard) {
                offerCard.style.transition = 'all 0.3s ease';
                offerCard.style.transform = 'scale(0.9)';
                offerCard.style.opacity = '0';

                setTimeout(() => {
                    offerCard.remove();

                    // Проверяем, остались ли офферы
                    const remainingOffers = document.querySelectorAll('.offer-card');
                    if (remainingOffers.length === 0) {
                        showEmptyOffersState();
                    }
                }, 300);
            }

        } else {
            throw new Error(result.error || 'Ошибка удаления оффера');
        }

    } catch (error) {
        console.error('❌ Ошибка удаления оффера:', error);
        alert(`❌ Ошибка: ${error.message}`);

        // Восстанавливаем кнопку
        if (buttonElement) {
            buttonElement.disabled = false;
            buttonElement.textContent = originalText;
            buttonElement.style.opacity = '1';
        }
    }
}

// ===== МАССОВОЕ УДАЛЕНИЕ ОФФЕРОВ =====
async function deleteMultipleOffers() {
    console.log('🗑️ Массовое удаление офферов');

    const selectedOffers = document.querySelectorAll('.offer-card input[type="checkbox"]:checked');

    if (selectedOffers.length === 0) {
        alert('Выберите офферы для удаления');
        return;
    }

    const confirmMessage = `Вы уверены, что хотите удалить ${selectedOffers.length} оффер(ов)?\n\nЭто действие нельзя отменить.`;

    if (!confirm(confirmMessage)) {
        return;
    }

    let deletedCount = 0;
    let errorCount = 0;

    for (const checkbox of selectedOffers) {
        const offerCard = checkbox.closest('.offer-card');
        const offerId = offerCard?.dataset.offerId;

        if (offerId) {
            try {
                const response = await fetch(`/api/offers/${offerId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Telegram-User-Id': getTelegramUserId()
                    }
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    deletedCount++;
                    offerCard.remove();
                } else {
                    errorCount++;
                    console.error(`Ошибка удаления оффера ${offerId}:`, result.error);
                }

            } catch (error) {
                errorCount++;
                console.error(`Ошибка удаления оффера ${offerId}:`, error);
            }
        }
    }

    // Показываем результат
    if (deletedCount > 0) {
        alert(`✅ Удалено офферов: ${deletedCount}${errorCount > 0 ? `\n❌ Ошибок: ${errorCount}` : ''}`);
    } else {
        alert('❌ Не удалось удалить ни одного оффера');
    }

    // Проверяем, остались ли офферы
    const remainingOffers = document.querySelectorAll('.offer-card');
    if (remainingOffers.length === 0) {
        showEmptyOffersState();
    }
}

// ===== ФУНКЦИИ УПРАВЛЕНИЯ СТАТУСОМ ОФФЕРА =====

async function cancelOffer(offerId, offerTitle, buttonElement) {
    console.log('❌ Запрос на отмену оффера:', offerId);

    // Только подтверждение без запроса причины
    const confirmMessage = `Вы уверены, что хотите отменить оффер "${offerTitle}"?\n\nПосле отмены вы сможете его удалить.`;

    if (!confirm(confirmMessage)) {
        console.log('❌ Отмена отменена пользователем');
        return;
    }

    await updateOfferStatus(offerId, 'cancelled', 'Отменено пользователем', buttonElement, 'Отмена...');
}

async function pauseOffer(offerId, buttonElement) {
    console.log('⏸️ Приостановка оффера:', offerId);

    // Приостанавливаем без запроса причины
    await updateOfferStatus(offerId, 'paused', 'Приостановлено пользователем', buttonElement, 'Приостановка...');
}

async function resumeOffer(offerId, buttonElement) {
    console.log('▶️ Возобновление оффера:', offerId);

    await updateOfferStatus(offerId, 'active', 'Возобновлено пользователем', buttonElement, 'Возобновление...');
}

async function completeOffer(offerId, buttonElement) {
    console.log('✅ Завершение оффера:', offerId);

    if (!confirm('Завершить оффер? После завершения его нельзя будет возобновить.')) {
        return;
    }

    await updateOfferStatus(offerId, 'completed', 'Завершено пользователем', buttonElement, 'Завершение...');
}

// ===== ФУНКЦИИ ПОИСКА ОФФЕРОВ =====
function applyFindFilters() {
    console.log('🔍 Применение фильтров поиска...');

    const filters = {
        search: document.getElementById('findOffersSearch')?.value.trim() || '',
        category: document.getElementById('findCategoryFilter')?.value || '',
        // ВАЖНО: Фильтруем по цене за размещение (price), а не по общему бюджету
        min_budget: parseFloat(document.getElementById('findBudgetMin')?.value) || null,
        max_budget: parseFloat(document.getElementById('findBudgetMax')?.value) || null,
        min_subscribers: parseInt(document.getElementById('findMinSubscribers')?.value) || null
    };

    // Убираем пустые значения
    Object.keys(filters).forEach(key => {
        if (filters[key] === null || filters[key] === '') {
            delete filters[key];
        }
    });

    console.log('🎯 Фильтры по цене за размещение:', filters);
    loadAvailableOffers(filters);
}

function clearFindFilters() {
    console.log('🗑️ Очистка фильтров...');

    document.getElementById('findOffersSearch').value = '';
    document.getElementById('findCategoryFilter').value = '';
    document.getElementById('findBudgetMin').value = '';
    document.getElementById('findBudgetMax').value = '';
    document.getElementById('findMinSubscribers').value = '';

    // Загружаем все офферы без фильтров
    loadAvailableOffers({});
}

async function loadAvailableOffers(filters = {}) {
    console.log('📥 Загрузка доступных офферов с фильтрами:', filters);

    const container = document.getElementById('findOffersGrid');
    const loading = document.getElementById('findOffersLoading');

    if (!container || !loading) {
        console.error('❌ Контейнеры для поиска не найдены');
        return;
    }

    // Показываем загрузку
    loading.style.display = 'block';
    container.innerHTML = '';

    try {
        // Формируем URL с параметрами
        const params = new URLSearchParams();
        Object.keys(filters).forEach(key => {
            if (filters[key] !== null && filters[key] !== '') {
                params.append(key, filters[key]);
            }
        });

        const url = `/api/offers/available${params.toString() ? '?' + params.toString() : ''}`;
        console.log('🌐 URL запроса:', url);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Загружено доступных офферов:', result.offers?.length || 0);
            renderAvailableOffers(result.offers || []);
        } else {
            throw new Error(result.error || 'Ошибка загрузки офферов');
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки доступных офферов:', error);
        showFindOffersError('Ошибка загрузки офферов: ' + error.message);
    } finally {
        loading.style.display = 'none';
    }
}

function renderAvailableOffers(offers) {
    console.log('🎨 Отрисовка доступных офферов:', offers.length);
    const container = document.getElementById('findOffersGrid');

    if (!container) {
        console.error('❌ Контейнер findOffersGrid не найден');
        return;
    }

    if (!offers || offers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="font-size: 48px; margin-bottom: 16px;">🎯</div>
                <h3>Нет доступных офферов</h3>
                <p>В данный момент нет офферов от других пользователей, соответствующих вашим критериям поиска</p>
                <button class="btn btn-primary" onclick="clearFindFilters()">
                    🗑️ Очистить фильтры
                </button>
            </div>
        `;
        return;
    }

    let html = '';
    offers.forEach((offer) => {
        const title = offer.title || 'Без названия';
        const description = offer.description || offer.content || 'Нет описания';

        // ИСПРАВЛЕНИЕ: Показываем максимальную цену за размещение
        const maxPricePerPlacement = offer.max_price || offer.price || 0;
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'Не указана';
        const minSubscribers = offer.min_subscribers || 0;
        const maxSubscribers = offer.max_subscribers || 'Без ограничений';
        const createdAt = formatDate(offer.created_at);
        const creatorName = offer.creator_name || 'Неизвестный автор';

        const formattedMaxPrice = formatPrice(maxPricePerPlacement);
        const shortDescription = description.length > 200 ?
            description.substring(0, 200) + '...' : description;

        // Форматируем подписчиков
        const subscribersText = maxSubscribers !== 'Без ограничений' && maxSubscribers > 0
            ? `${formatNumber(minSubscribers)}-${formatNumber(maxSubscribers)}`
            : `${formatNumber(minSubscribers)}+`;

        html += `
            <div class="offer-card" data-offer-id="${offer.id}" style="cursor: pointer; margin-bottom: 20px;" onclick="showOfferDetails(${offer.id})">
                <div class="offer-header">
                    <h3 style="margin: 0; color: #333; font-size: 18px; font-weight: 600; flex: 1;">${title}</h3>
                    <span style="padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; background: #d4edda; color: #155724; margin-left: 12px;">
                        Активен
                    </span>
                </div>

                <!-- Автор оффера -->
                <div style="margin-bottom: 12px; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #667eea;">
                    <div style="font-size: 12px; color: #666;">👤 Автор оффера:</div>
                    <div style="font-size: 14px; font-weight: 600; color: #333;">${creatorName}</div>
                </div>

                <!-- МАКСИМАЛЬНАЯ ЦЕНА ЗА РАЗМЕЩЕНИЕ - выделяем крупно и ярко -->
                <div style="margin: 12px 0; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; text-align: center;">
                    <div style="color: white; font-size: 24px; font-weight: bold;">${formattedMaxPrice} ${currency}</div>
                    <div style="color: rgba(255,255,255,0.9); font-size: 12px; margin-top: 4px;">💰 Оплата за размещение</div>
                </div>

                <div style="margin: 12px 0; color: #666; font-size: 14px; line-height: 1.5;">
                    ${shortDescription}
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee;">
                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <div style="font-size: 12px; color: #888;">
                            📂 <strong style="color: #333;">${category}</strong>
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            👥 <strong style="color: #333;">${subscribersText}</strong>
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            📅 <strong style="color: #333;">${createdAt}</strong>
                        </div>
                        <!-- УБРАЛИ отображение общего бюджета -->
                    </div>

                    <button class="btn btn-primary" style="padding: 12px 20px; font-size: 14px; margin-left: 12px; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);" onclick="event.stopPropagation(); acceptOffer(${offer.id})">
                        ✅ Откликнуться
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function showFindOffersError(message) {
    const container = document.getElementById('findOffersGrid');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon" style="font-size: 48px; margin-bottom: 16px;">❌</div>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                <button class="btn btn-outline" onclick="loadAvailableOffers()">
                    🔄 Попробовать снова
                </button>
            </div>
        `;
    }
}

// ===== ФУНКЦИИ РАБОТЫ С ОТКЛИКАМИ =====

async function acceptOffer(offerId) {
    console.log('✅ Отклик на оффер:', offerId);

    try {
        // Получаем данные оффера из DOM
        const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
        if (!offerCard) {
            throw new Error('Оффер не найден на странице');
        }

        // Парсим данные из карточки оффера
        const titleElement = offerCard.querySelector('h4');
        const budgetElement = offerCard.querySelector('strong[style*="color: #333"]');

        const offer = {
            id: offerId,
            title: titleElement ? titleElement.textContent.trim() : 'Оффер',
            total_budget: budgetElement ? budgetElement.textContent : 'Не указан'
        };

        console.log('📋 Данные оффера из DOM:', offer);

        // Получаем все каналы пользователя
        const channelsResponse = await fetch('/api/channels/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const channelsResult = await channelsResponse.json();

        if (!channelsResult.success) {
            throw new Error(channelsResult.error || 'Ошибка загрузки каналов');
        }

        // Фильтруем только верифицированные каналы
        const allChannels = channelsResult.channels || [];
        const verifiedChannels = allChannels.filter(channel =>
            channel.is_verified === true || channel.is_verified === 1 || channel.status === 'verified'
        );

        console.log('📋 Все каналы:', allChannels.length);
        console.log('✅ Верифицированные каналы:', verifiedChannels.length);

        if (verifiedChannels.length === 0) {
            alert('У вас нет верифицированных каналов. Сначала добавьте и верифицируйте канал в разделе "Мои каналы".');
            return;
        }

        // Показываем модальное окно с данными оффера и каналов
        const modal = createResponseModal(offerId, offer, verifiedChannels);
        document.body.appendChild(modal);

    } catch (error) {
        console.error('❌ Ошибка при отклике на оффер:', error);
        alert(`❌ Ошибка: ${error.message}`);
    }
}

function createResponseModal(offerId, offer, verifiedChannels) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
    <div style="
        background: white;
        border-radius: 12px;
        padding: 24px;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="margin: 0; color: #2d3748; font-size: 20px;">📝 Отклик на оффер</h3>
            <button onclick="closeResponseModal()" style="
                background: none; border: none; font-size: 24px; 
                cursor: pointer; color: #666;
            ">&times;</button>
        </div>
        
        <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
            <h4 style="margin: 0 0 8px 0; color: #2d3748;">🎯 ${offer.title}</h4>
            <p style="margin: 0; color: #718096; font-size: 14px;">
                💰 Бюджет: ${offer.total_budget || 'Не указан'} RUB
            </p>
        </div>
        
        <form id="responseForm">
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
                    Выберите канал <span style="color: #e53e3e;">*</span>
                </label>
                <select id="selectedChannel" required style="
                    width: 100%; padding: 12px; border: 2px solid #e2e8f0;
                    border-radius: 6px; font-size: 14px; background: white;
                ">
                    ${verifiedChannels.map(channel => `
                        <option value="${channel.id}">
                            ${channel.title} (@${channel.username}) - ${channel.subscriber_count || 0} подписчиков
                        </option>
                    `).join('')}
                </select>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
                    Сообщение рекламодателю <span style="color: #e53e3e;">*</span>
                </label>
                <textarea id="responseMessage" required placeholder="Расскажите, почему ваш канал подходит для этого оффера..." style="
                    width: 100%; min-height: 120px; padding: 12px;
                    border: 2px solid #e2e8f0; border-radius: 6px;
                    font-size: 14px; resize: vertical; font-family: inherit;
                "></textarea>
            </div>
            
            <div style="display: flex; gap: 12px;">
                <button type="button" onclick="closeResponseModal()" style="
                    flex: 1; padding: 12px; border: 2px solid #e2e8f0;
                    background: white; color: #4a5568; border-radius: 6px;
                    font-size: 16px; font-weight: 600; cursor: pointer;
                ">🔹 Отмена</button>
                
                <button type="submit" style="
                    flex: 1; padding: 12px; border: none;
                    background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                    color: white; border-radius: 6px; font-size: 16px;
                    font-weight: 600; cursor: pointer;
                ">🔹 Отправить отклик</button>
            </div>
        </form>
    </div>
`;

    // Обработчик формы
    const form = modal.querySelector('#responseForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        submitOfferResponse(offerId);
    });

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeResponseModal();
        }
    });

    return modal;
}

async function submitOfferResponse(offerId) {
    const selectedChannelId = document.getElementById('selectedChannel').value;
    const message = document.getElementById('responseMessage').value.trim();

    // 🔍 ОТЛАДКА: проверяем что получили
    console.log('🔍 Отладка данных формы:');
    console.log('selectedChannelId:', selectedChannelId, 'тип:', typeof selectedChannelId);
    console.log('message:', message);

    // Проверяем элемент селектора
    const selectElement = document.getElementById('selectedChannel');
    console.log('Элемент селектора:', selectElement);
    console.log('Опции селектора:', selectElement ? selectElement.options.length : 'НЕТ ЭЛЕМЕНТА');

    if (selectElement && selectElement.options.length > 0) {
        for (let i = 0; i < selectElement.options.length; i++) {
            console.log(`Опция ${i}:`, selectElement.options[i].value, '-', selectElement.options[i].text);
        }
    }

    if (!selectedChannelId || selectedChannelId === '' || selectedChannelId === 'null') {
        alert('Выберите канал из списка');
        console.error('❌ Канал не выбран. selectedChannelId:', selectedChannelId);
        return;
    }

    if (!message) {
        alert('Введите сообщение для рекламодателя');
        return;
    }

    const submitBtn = document.querySelector('#responseForm button[type="submit"]');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Отправка...';

        const payload = {
            channel_id: parseInt(selectedChannelId),
            message: message
        };

        console.log('📤 Отправляем payload:', payload);

        const response = await fetch(`/api/offers/${offerId}/respond`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify(payload)
        });

        console.log('📥 Ответ сервера:', response.status, response.statusText);

        const result = await response.json();
        console.log('📋 Результат:', result);

        if (result.success) {
            alert('✅ ' + result.message);
            closeResponseModal();

            // Обновляем кнопку в карточке
            const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
            if (offerCard) {
                const respondButton = offerCard.querySelector('button[onclick*="acceptOffer"]');
                if (respondButton) {
                    respondButton.style.background = '#a0aec0';
                    respondButton.textContent = '✅ Отклик отправлен';
                    respondButton.disabled = true;
                    respondButton.onclick = null;
                }
            }
        } else {
            throw new Error(result.error || 'Ошибка отправки отклика');
        }

    } catch (error) {
        console.error('❌ Ошибка отправки отклика:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}


// ===== ФУНКЦИИ УПРАВЛЕНИЯ ОТКЛИКАМИ (для авторов офферов) =====

async function manageResponses(offerId) {
    console.log('💬 Управление откликами для оффера:', offerId);

    try {
        const url = `/api/offers/${offerId}/responses`;
        console.log('🌐 Запрос URL:', url);
        console.log('🔑 User ID:', getTelegramUserId());

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        console.log('📋 Статус ответа:', response.status, response.statusText);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Ошибка HTTP:', errorText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('📋 Полный результат API:', result);
        console.log('📊 Количество откликов:', result.responses ? result.responses.length : 'undefined');

        if (!result.success) {
            console.error('❌ API вернул success: false, error:', result.error);
            throw new Error(result.error || 'API вернул success: false');
        }

        if (!result.responses) {
            console.warn('⚠️ Поле responses отсутствует в ответе API');
            console.log('🔍 Доступные поля:', Object.keys(result));
        }

        // Создаем объект offer для совместимости
        const offer = {
            id: offerId,
            title: result.offer?.title || `Оффер #${offerId}`
        };

        console.log('📊 Отклики для модального окна:', result.responses);

        // Проверяем каждый отклик
        if (result.responses && result.responses.length > 0) {
            result.responses.forEach((response, index) => {
                console.log(`📝 Отклик ${index + 1}:`, {
                    id: response.id,
                    channel_title: response.channel_title,
                    channel_username: response.channel_username,
                    status: response.status,
                    message: response.message ? response.message.substring(0, 50) + '...' : 'Нет сообщения'
                });
            });
        }

        showResponsesModal(offer, result.responses || []);

    } catch (error) {
        console.error('❌ Полная ошибка загрузки откликов:', error);
        console.error('❌ Stack trace:', error.stack);
        alert(`❌ Ошибка загрузки откликов: ${error.message}`);
    }
}

function showResponsesModal(offer, responses) {
    console.log('📋 showResponsesModal вызвана');
    console.log('📊 Оффер:', offer);
    console.log('📋 Отклики (тип):', typeof responses);
    console.log('📋 Отклики (Array.isArray):', Array.isArray(responses));
    console.log('📊 Количество откликов:', responses ? responses.length : 'undefined/null');

    if (responses && responses.length > 0) {
        console.log('📝 Первый отклик для примера:', responses[0]);
    }

    // Удаляем существующее модальное окно если есть
    const existingModal = document.getElementById('responsesModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.id = 'responsesModal';
    modal.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background: rgba(0,0,0,0.8) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 9999 !important;
        padding: 20px !important;
    `;

    const modalContent = `
        <div style="
            background: white !important;
            border-radius: 12px !important;
            padding: 24px !important;
            max-width: 800px !important;
            width: 100% !important;
            max-height: 90vh !important;
            overflow-y: auto !important;
            position: relative !important;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #2d3748; font-size: 20px;">
                    💬 Отклики на оффер "${offer.title || offer.id}"
                </h3>
                <button onclick="closeResponsesModal()" style="
                    background: none; border: none; font-size: 24px; 
                    cursor: pointer; color: #666; padding: 5px;
                ">&times;</button>
            </div>
            
            <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0 0 4px 0; color: #2d3748;">📊 Статистика</h4>
                        <p style="margin: 0; color: #718096; font-size: 14px;">
                            Всего откликов: <strong>${responses ? responses.length : 0}</strong>
                        </p>
                    </div>
                </div>
            </div>

            <div id="responsesList">
                ${responses && responses.length > 0 ? renderSimpleResponsesList(responses) : renderEmptyResponses()}
            </div>
        </div>
    `;

    modal.innerHTML = modalContent;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    console.log('✅ Модальное окно добавлено в DOM');

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeResponsesModal();
        }
    });
}

function renderSimpleResponsesList(responses) {
    console.log('🎨 Рендерим список откликов:', responses.length);

    if (!Array.isArray(responses)) {
        console.error('❌ responses не является массивом:', typeof responses);
        return '<div>Ошибка: неверный формат данных откликов</div>';
    }

    if (responses.length === 0) {
        console.log('ℹ️ Массив откликов пустой');
        return renderEmptyResponses();
    }

    return responses.map((response, index) => {
        console.log(`🎨 Рендерим отклик ${index + 1}:`, {
            id: response.id,
            channel_title: response.channel_title,
            status: response.status
        });

        // Безопасное получение значений с fallback
        const channelTitle = response.channel_title || 'Канал без названия';
        const channelUsername = response.channel_username || 'username';
        const channelSubscribers = response.channel_subscribers || 0;
        const message = response.message || '';
        const status = response.status || 'pending';

        return `
            <div style="
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                padding: 16px; 
                margin-bottom: 12px;
                background: white;
            ">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div style="flex: 1;">
                        <h5 style="margin: 0 0 4px 0; color: #2d3748; font-size: 16px;">
                            📺 ${channelTitle}
                        </h5>
                        <div style="font-size: 14px; color: #718096;">
                            @${channelUsername} • 
                            👥 ${formatNumber(channelSubscribers)} подписчиков
                        </div>
                    </div>
                    <div style="
                        padding: 4px 12px; 
                        border-radius: 20px;
                        font-size: 12px; 
                        font-weight: 600;
                        background: #fed7d7; 
                        color: #c53030;
                    ">
                        ${getStatusText(status)}
                    </div>
                </div>

                ${message ? `
                    <div style="
                        background: #f7fafc; 
                        padding: 12px; 
                        border-radius: 6px; 
                        margin: 12px 0;
                        border-left: 4px solid #4299e1;
                    ">
                        <div style="font-size: 12px; color: #4299e1; font-weight: 600; margin-bottom: 4px;">
                            💬 СООБЩЕНИЕ:
                        </div>
                        <div style="font-size: 14px; color: #2d3748;">
                            ${message}
                        </div>
                    </div>
                ` : ''}

                <div style="display: flex; gap: 8px; margin-top: 12px;">
                    ${status === 'pending' ? `
                        <button onclick="respondToResponse('${response.id}', 'accepted')" style="
                            padding: 6px 12px; 
                            background: #48bb78; 
                            color: white;
                            border: none; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 12px;
                        ">✅ Принять</button>
                        <button onclick="respondToResponse('${response.id}', 'rejected')" style="
                            padding: 6px 12px; 
                            background: #f56565; 
                            color: white;
                            border: none; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-size: 12px;
                        ">❌ Отклонить</button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function renderEmptyResponses() {
    return `
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
            <h4 style="margin: 0 0 8px 0; color: #2d3748;">Пока нет откликов</h4>
            <p style="margin: 0; color: #718096;">
                Отклики начнут поступать в ближайшее время.
            </p>
        </div>
    `;
}

function closeResponsesModal() {
    const modal = document.getElementById('responsesModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = 'auto';
        console.log('✅ Модальное окно закрыто');
    }
}









function renderResponsesList(responses) {
    return responses.map(response => `
        <div class="response-card" style="
            border: 2px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;
            background: white; transition: all 0.2s;
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div style="flex: 1;">
                    <h5 style="margin: 0 0 4px 0; color: #2d3748; font-size: 16px;">
                        📺 ${response.channel_title || 'Канал без названия'}
                    </h5>
                    <div style="display: flex; gap: 16px; font-size: 14px; color: #718096;">
                        <span>👤 ${response.channel_owner_name || 'Владелец'}</span>
                        <span>@${response.channel_username || 'username'}</span>
                        <span>👥 ${formatNumber(response.channel_subscribers || 0)} подписчиков</span>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="
                        display: inline-block; padding: 4px 12px; border-radius: 20px;
                        font-size: 12px; font-weight: 600; text-transform: uppercase;
                        ${getStatusStyle(response.status)}
                    ">
                        ${getStatusText(response.status)}
                    </div>
                    <div style="font-size: 12px; color: #718096; margin-top: 4px;">
                        ${formatDate(response.created_at)}
                    </div>
                </div>
            </div>

            ${response.message ? `
                <div style="
                    background: #f7fafc; padding: 12px; border-radius: 6px; margin: 12px 0;
                    border-left: 4px solid #4299e1;
                ">
                    <div style="font-size: 12px; color: #4299e1; font-weight: 600; margin-bottom: 4px;">
                        💬 СООБЩЕНИЕ ОТ ВЛАДЕЛЬЦА КАНАЛА:
                    </div>
                    <div style="font-size: 14px; color: #2d3748; line-height: 1.4;">
                        ${response.message}
                    </div>
                </div>
            ` : ''}

            ${response.channel_description ? `
                <div style="font-size: 14px; color: #718096; margin: 8px 0;">
                    <strong>Описание канала:</strong> ${response.channel_description}
                </div>
            ` : ''}

            <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end;">
                ${response.status === 'pending' ? `
                    <button onclick="respondToResponse('${response.id}', 'accepted')" style="
                        padding: 8px 16px; background: #48bb78; color: white;
                        border: none; border-radius: 6px; cursor: pointer; font-size: 14px;
                    ">✅ Принять</button>
                    <button onclick="respondToResponse('${response.id}', 'rejected')" style="
                        padding: 8px 16px; background: #f56565; color: white;
                        border: none; border-radius: 6px; cursor: pointer; font-size: 14px;
                    ">❌ Отклонить</button>
                ` : ''}
                
                <button onclick="showResponseDetails('${response.id}')" style="
                    padding: 8px 16px; background: #4299e1; color: white;
                    border: none; border-radius: 6px; cursor: pointer; font-size: 14px;
                ">👁️ Подробнее</button>
                
                ${response.channel_username ? `
                    <a href="https://t.me/${response.channel_username}" target="_blank" style="
                        padding: 8px 16px; background: #805ad5; color: white;
                        border: none; border-radius: 6px; cursor: pointer; font-size: 14px;
                        text-decoration: none; display: inline-block;
                    ">📱 Открыть канал</a>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function getResponsesStatusSummary(responses) {
    const statusCounts = responses.reduce((acc, response) => {
        acc[response.status] = (acc[response.status] || 0) + 1;
        return acc;
    }, {});

    const statusLabels = {
        'pending': '⏳ На рассмотрении',
        'accepted': '✅ Принятые',
        'rejected': '❌ Отклонённые',
        'interested': '👀 Заинтересованные'
    };

    return Object.entries(statusCounts)
        .map(([status, count]) => `${statusLabels[status] || status}: ${count}`)
        .join('<br>');
}

function getStatusStyle(status) {
    const styles = {
        'pending': 'background: #fed7d7; color: #c53030;',
        'accepted': 'background: #c6f6d5; color: #2f855a;',
        'rejected': 'background: #fed7d7; color: #c53030;',
        'interested': 'background: #bee3f8; color: #2b6cb0;'
    };
    return styles[status] || 'background: #e2e8f0; color: #4a5568;';
}


function getStatusText(status) {
    const texts = {
        'pending': 'На рассмотрении',
        'accepted': 'Принят',
        'rejected': 'Отклонён',
        'interested': 'Заинтересован'
    };
    return texts[status] || status;
}

async function respondToResponse(responseId, action) {
    try {
        const response = await fetch(`/api/offers/responses/${responseId}/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `✅ Отклик ${action === 'accepted' ? 'принят' : 'отклонён'}`);

            // Обновляем модальное окно
            closeResponsesModal();
            // Здесь можно перезагрузить модальное окно или обновить конкретный элемент

        } else {
            throw new Error(result.error || 'Ошибка обработки отклика');
        }

    } catch (error) {
        console.error('❌ Ошибка обработки отклика:', error);
        alert(`❌ Ошибка: ${error.message}`);
    }
}

function formatDate(dateString) {
    if (!dateString) return 'Недавно';

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return 'Недавно';
    }
}

function renderContracts(contracts) {
    console.log('🎨 Отрисовка контрактов:', contracts.length);

    // Создаем контейнер для контрактов если его нет
    let container = document.getElementById('contractsGrid');
    if (!container) {
        container = document.createElement('div');
        container.id = 'contractsGrid';
        container.style.cssText = 'margin-top: 20px;';

        // Добавляем после существующих элементов
        const offersContainer = document.querySelector('.container');
        if (offersContainer) {
            offersContainer.appendChild(container);
        }
    }

    if (!contracts || contracts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="font-size: 48px; margin-bottom: 16px;">📋</div>
                <h3>Нет активных контрактов</h3>
                <p>Когда вы примете отклик или откликнетесь на оффер, контракты появятся здесь</p>
            </div>
        `;
        return;
    }

    let html = '';
    contracts.forEach(contract => {
        const statusColors = {
            'active': '#ed8936',
            'verification': '#3182ce',
            'monitoring': '#38a169',
            'completed': '#48bb78',
            'cancelled': '#e53e3e',
            'expired': '#a0aec0',
            'violation': '#e53e3e',
            'verification_failed': '#e53e3e'
        };

        const statusTexts = {
            'active': 'Ожидает размещения',
            'verification': 'Проверка размещения',
            'monitoring': 'Мониторинг',
            'completed': 'Завершен',
            'cancelled': 'Отменен',
            'expired': 'Просрочен',
            'violation': 'Нарушение',
            'verification_failed': 'Проверка не пройдена'
        };

        const statusColor = statusColors[contract.status] || '#718096';
        const statusText = statusTexts[contract.status] || contract.status;
        const isPublisher = contract.role === 'publisher';

        html += `
            <div class="contract-card" data-contract-id="${contract.id}" style="
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                cursor: pointer;
            " onclick="showContractDetails('${contract.id}')">
                
                <!-- Заголовок и статус -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #2d3748; font-size: 16px; font-weight: 600; flex: 1;">
                        ${contract.offer_title}
                    </h3>
                    <span style="
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 500;
                        background: ${statusColor}20;
                        color: ${statusColor};
                        margin-left: 12px;
                    ">${statusText}</span>
                </div>
                
                <!-- Роль и участники -->
                <div style="margin-bottom: 12px; padding: 8px 12px; background: ${isPublisher ? '#f0fff4' : '#ebf8ff'}; border-radius: 6px;">
                    <div style="font-size: 12px; color: #666;">
                        ${isPublisher ? '📺 Вы - издатель' : '📢 Вы - рекламодатель'}
                    </div>
                    <div style="font-size: 14px; font-weight: 600; color: #333;">
                        ${isPublisher ? `Канал: ${contract.channel_title}` : `Издатель: ${contract.publisher_name}`}
                    </div>
                </div>
                
                <!-- Основная информация -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; font-size: 14px;">
                    <div>
                        <span style="color: #718096;">💰 Сумма:</span>
                        <span style="font-weight: 600; color: #2d3748;">${formatPrice(contract.price)} RUB</span>
                    </div>
                    <div>
                        <span style="color: #718096;">📅 Создан:</span>
                        <span style="font-weight: 600; color: #2d3748;">${formatDate(contract.created_at)}</span>
                    </div>
                </div>
                
                <!-- Дедлайны -->
                ${contract.status === 'active' ? `
                    <div style="background: #fffaf0; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #c05621;">⏰ Разместить до:</div>
                        <div style="font-size: 14px; font-weight: 600; color: #c05621;">
                            ${formatDate(contract.placement_deadline)}
                        </div>
                    </div>
                ` : ''}
                
                ${contract.status === 'monitoring' ? `
                    <div style="background: #f0fff4; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #276749;">🔍 Мониторинг до:</div>
                        <div style="font-size: 14px; font-weight: 600; color: #276749;">
                            ${formatDate(contract.monitoring_end)}
                        </div>
                    </div>
                ` : ''}

                ${contract.status === 'verification_failed' ? `
                    <div style="background: #fed7d7; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px;">
                        <div style="font-size: 12px; color: #c53030;">❌ Причина:</div>
                        <div style="font-size: 14px; font-weight: 600; color: #c53030;">
                            ${contract.verification_details || 'Размещение не соответствует требованиям'}
                        </div>
                    </div>
                ` : ''}
                
                <!-- Кнопки действий -->
                <div style="display: flex; gap: 8px; margin-top: 12px;">
                    <button onclick="event.stopPropagation(); showContractDetails('${contract.id}')" style="
                        flex: 1;
                        padding: 8px 12px;
                        border: 1px solid #667eea;
                        background: #667eea;
                        color: white;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: 600;
                        cursor: pointer;
                    ">📋 Детали</button>
                    
                    ${contract.status === 'active' && isPublisher ? `
                        <button onclick="event.stopPropagation(); showPlacementForm('${contract.id}')" style="
                            flex: 1;
                            padding: 8px 12px;
                            border: 1px solid #48bb78;
                            background: #48bb78;
                            color: white;
                            border-radius: 6px;
                            font-size: 12px;
                            font-weight: 600;
                            cursor: pointer;
                        ">📤 Подать заявку</button>
                    ` : ''}
                    
                    ${contract.status === 'active' && isPublisher ? `
                        <button onclick="event.stopPropagation(); showContractInstructions(${JSON.stringify(contract).replace(/"/g, '&quot;')})" style="
                            padding: 8px 12px;
                            border: 1px solid #3182ce;
                            background: #3182ce;
                            color: white;
                            border-radius: 6px;
                            font-size: 12px;
                            font-weight: 600;
                            cursor: pointer;
                        ">📋 Как размещать</button>
                    ` : ''}
                    
                    ${['active', 'verification'].includes(contract.status) ? `
                        <button onclick="event.stopPropagation(); cancelContract('${contract.id}')" style="
                            padding: 8px 12px;
                            border: 1px solid #e53e3e;
                            background: #e53e3e;
                            color: white;
                            border-radius: 6px;
                            font-size: 12px;
                            font-weight: 600;
                            cursor: pointer;
                        ">❌ Отменить</button>
                    ` : ''}

                    ${contract.status === 'verification_failed' ? `
                        <button onclick="event.stopPropagation(); deleteFailedContract('${contract.id}', '${contract.offer_title.replace(/'/g, "\\'")}', this)" style="
                            padding: 8px 12px;
                            border: 1px solid #e53e3e;
                            background: #e53e3e;
                            color: white;
                            border-radius: 6px;
                            font-size: 12px;
                            font-weight: 600;
                            cursor: pointer;
                        ">🗑️ Удалить</button>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Функция удаления неудачных контрактов
async function deleteFailedContract(contractId, offerTitle, buttonElement) {
    console.log('🗑️ Запрос на удаление неудачного контракта:', contractId);

    // Показываем подтверждение
    const confirmMessage = `Удалить контракт "${offerTitle}"?\n\nКонтракт не прошел проверку размещения и может быть удален.\nЭто действие нельзя отменить.`;

    if (!confirm(confirmMessage)) {
        console.log('❌ Удаление отменено пользователем');
        return;
    }

    const originalText = buttonElement?.textContent;

    try {
        // Блокируем кнопку
        if (buttonElement) {
            buttonElement.disabled = true;
            buttonElement.textContent = '⏳ Удаление...';
            buttonElement.style.opacity = '0.6';
        }

        console.log('🌐 Отправляем запрос на удаление контракта...');

        const response = await fetch(`/api/offers/contracts/${contractId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();
        console.log('📥 Ответ сервера:', result);

        if (result.success) {
            console.log('✅ Контракт успешно удален');

            // Показываем уведомление
            if (typeof showNotification === 'function') {
                showNotification('success', `✅ ${result.message}`);
            } else {
                alert(`✅ ${result.message}`);
            }

            // Перезагружаем список контрактов
            if (typeof loadUserContracts === 'function') {
                loadUserContracts();
            } else {
                // Убираем элемент из DOM если функция недоступна
                const contractCard = buttonElement.closest('.contract-card, [data-contract-id]');
                if (contractCard) {
                    contractCard.style.transition = 'opacity 0.3s ease';
                    contractCard.style.opacity = '0';
                    setTimeout(() => contractCard.remove(), 300);
                }
            }

        } else {
            throw new Error(result.error || 'Ошибка удаления контракта');
        }

    } catch (error) {
        console.error('❌ Ошибка удаления контракта:', error);

        // Восстанавливаем кнопку
        if (buttonElement) {
            buttonElement.disabled = false;
            buttonElement.textContent = originalText;
            buttonElement.style.opacity = '1';
        }

        // Показываем ошибку
        if (typeof showNotification === 'function') {
            showNotification('error', `❌ Ошибка: ${error.message}`);
        } else {
            alert(`❌ Ошибка удаления: ${error.message}`);
        }
    }
}

function showContractsError(message) {
    const container = document.getElementById('contractsGrid');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon" style="font-size: 48px; margin-bottom: 16px;">❌</div>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                <button class="btn btn-outline" onclick="loadUserContracts()">
                    🔄 Попробовать снова
                </button>
            </div>
        `;
    }
}

async function showContractDetails(contractId) {
    console.log('📋 Показ деталей контракта:', contractId);

    try {
        const response = await fetch(`/api/offers/contracts/${contractId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success) {
            showContractDetailsModal(result.contract);
        } else {
            throw new Error(result.error || 'Ошибка загрузки деталей контракта');
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки деталей контракта:', error);
        alert(`❌ Ошибка: ${error.message}`);
    }
}

function showContractDetailsModal(contract) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    const statusColors = {
        'active': '#ed8936',
        'verification': '#3182ce',
        'monitoring': '#38a169',
        'completed': '#48bb78',
        'cancelled': '#e53e3e',
        'expired': '#a0aec0',
        'violation': '#e53e3e'
    };

    const statusTexts = {
        'active': 'Ожидает размещения',
        'verification': 'Проверка размещения',
        'monitoring': 'Мониторинг',
        'completed': 'Завершен',
        'cancelled': 'Отменен',
        'expired': 'Просрочен',
        'violation': 'Нарушение'
    };

    const statusColor = statusColors[contract.status] || '#718096';
    const statusText = statusTexts[contract.status] || contract.status;
    const isPublisher = contract.role === 'publisher';

    modal.innerHTML = `
        <div style="
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #2d3748; font-size: 20px;">📋 Контракт ${contract.id}</h3>
                <button onclick="closeContractDetailsModal()" style="
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #718096;
                ">×</button>
            </div>
            
            <!-- Статус -->
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 600;
                    background: ${statusColor}20;
                    color: ${statusColor};
                ">${statusText}</span>
            </div>
            
            <!-- Основная информация -->
            <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 12px 0; color: #2d3748;">📝 Основная информация</h4>
                <div style="display: grid; gap: 8px;">
                    <div><strong>Оффер:</strong> ${contract.offer_title}</div>
                    <div><strong>Сумма:</strong> ${formatPrice(contract.price)} RUB</div>
                    <div><strong>Ваша роль:</strong> ${isPublisher ? 'Издатель (владелец канала)' : 'Рекламодатель'}</div>
                    <div><strong>Рекламодатель:</strong> ${contract.advertiser_name}</div>
                    <div><strong>Издатель:</strong> ${contract.publisher_name}</div>
                    <div><strong>Канал:</strong> ${contract.channel_title} (@${contract.channel_username})</div>
                </div>
            </div>
            
            <!-- Временные рамки -->
            <div style="background: #ebf8ff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 12px 0; color: #2b6cb0;">⏰ Временные рамки</h4>
                <div style="display: grid; gap: 8px; color: #2b6cb0;">
                    <div><strong>Срок размещения:</strong> ${formatDate(contract.placement_deadline)}</div>
                    <div><strong>Срок мониторинга:</strong> ${contract.monitoring_duration} дней</div>
                    <div><strong>Мониторинг до:</strong> ${formatDate(contract.monitoring_end)}</div>
                    <div><strong>Создан:</strong> ${formatDate(contract.created_at)}</div>
                    ${contract.completed_at ? `<div><strong>Завершен:</strong> ${formatDate(contract.completed_at)}</div>` : ''}
                </div>
            </div>
            
            <!-- Требования -->
            ${contract.post_requirements ? `
                <div style="background: #fff5f5; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #c53030;">📋 Требования к посту</h4>
                    <div style="color: #c53030;">${contract.post_requirements}</div>
                </div>
            ` : ''}
            
            <!-- Размещение -->
            ${contract.post_url ? `
                <div style="background: #f0fff4; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #276749;">🔗 Размещение</h4>
                    <div style="color: #276749;">
                        <div><strong>Ссылка на пост:</strong> <a href="${contract.post_url}" target="_blank" style="color: #276749;">${contract.post_url}</a></div>
                        ${contract.submitted_at ? `<div><strong>Подано:</strong> ${formatDate(contract.submitted_at)}</div>` : ''}
                        ${contract.verification_passed !== null ? `
                            <div><strong>Проверка:</strong> ${contract.verification_passed ? '✅ Пройдена' : '❌ Не пройдена'}</div>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
            
            <!-- Нарушения -->
            ${contract.violation_reason ? `
                <div style="background: #fed7d7; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #c53030;">⚠️ Нарушение</h4>
                    <div style="color: #c53030;">${contract.violation_reason}</div>
                </div>
            ` : ''}
            
            <!-- Сообщение из отклика -->
            ${contract.response_message ? `
                <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 12px 0; color: #4a5568;">💬 Сообщение из отклика</h4>
                    <div style="color: #4a5568; font-style: italic;">"${contract.response_message}"</div>
                </div>
            ` : ''}
            
            <!-- Действия -->
            <div style="display: flex; gap: 12px; margin-top: 20px;">
                ${contract.status === 'active' && isPublisher ? `
                    <button onclick="closeContractDetailsModal(); showPlacementForm('${contract.id}')" style="
                        flex: 1;
                        padding: 12px;
                        border: none;
                        background: #48bb78;
                        color: white;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">📤 Подать заявку о размещении</button>
                ` : ''}
                
                ${['active', 'verification'].includes(contract.status) ? `
                    <button onclick="closeContractDetailsModal(); cancelContract('${contract.id}')" style="
                        padding: 12px 20px;
                        border: 1px solid #e53e3e;
                        background: white;
                        color: #e53e3e;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">❌ Отменить контракт</button>
                ` : ''}
                
                <button onclick="closeContractDetailsModal()" style="
                    padding: 12px 20px;
                    border: 1px solid #e2e8f0;
                    background: white;
                    color: #4a5568;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                ">Закрыть</button>
            </div>
        </div>
    `;

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeContractDetailsModal();
        }
    });

    document.body.appendChild(modal);
}

function closeContractDetailsModal() {
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
    }
}

function showPlacementForm(contractId) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
        ">
            <h3 style="margin: 0 0 16px 0; color: #2d3748; font-size: 20px;">📤 Подача заявки о размещении</h3>
            
            <div style="background: #ebf8ff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 8px 0; color: #2b6cb0;">📋 Инструкция:</h4>
                <ol style="margin: 0; padding-left: 16px; color: #2b6cb0;">
                    <li>Разместите рекламу в своем канале</li>
                    <li>Скопируйте ссылку на пост</li>
                    <li>Вставьте ссылку в поле ниже</li>
                    <li>Нажмите "Подать заявку"</li>
                </ol>
            </div>
            
            <form id="placementForm">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Ссылка на пост с рекламой <span style="color: #e53e3e;">*</span>
                    </label>
                    <input type="url" id="postUrl" required style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    " placeholder="https://t.me/yourchannel/123">
                    <small style="color: #718096;">Пример: https://t.me/yourchannel/123</small>
                </div>
                
                <div style="display: flex; gap: 12px;">
                    <button type="button" onclick="closePlacementForm()" style="
                        flex: 1;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        background: white;
                        color: #4a5568;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">Отмена</button>
                    
                    <button type="submit" style="
                        flex: 1;
                        padding: 12px;
                        border: none;
                        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                        color: white;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">📤 Подать заявку</button>
                </div>
            </form>
        </div>
    `;

    // Обработчик формы
    const form = modal.querySelector('#placementForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        submitPlacement(contractId);
    });

    document.body.appendChild(modal);
}

async function submitPlacement(contractId) {
    const postUrl = document.getElementById('postUrl').value.trim();

    if (!postUrl) {
        alert('Укажите ссылку на пост');
        return;
    }

    const submitBtn = document.querySelector('#placementForm button[type="submit"]');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Подача заявки...';

        const response = await fetch(`/api/offers/contracts/${contractId}/placement`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                post_url: postUrl
            })
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ ' + result.message);
            closePlacementForm();
            loadUserContracts(); // Обновляем список контрактов
        } else {
            throw new Error(result.error || 'Ошибка подачи заявки');
        }

    } catch (error) {
        console.error('❌ Ошибка подачи заявки:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function closePlacementForm() {
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
    }
}

async function cancelContract(contractId) {
    if (!confirm('Вы уверены, что хотите отменить контракт?\n\nЭто действие нельзя отменить.')) {
        return;
    }

    const reason = prompt('Причина отмены (необязательно):') || 'Отменено пользователем';

    try {
        const response = await fetch(`/api/offers/contracts/${contractId}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                reason: reason
            })
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ ' + result.message);
            loadUserContracts(); // Обновляем список контрактов
        } else {
            throw new Error(result.error || 'Ошибка отмены контракта');
        }

    } catch (error) {
        console.error('❌ Ошибка отмены контракта:', error);
        alert(`❌ Ошибка: ${error.message}`);
    }
}

function createContractDetailsModal(responseId) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1001;
    `;

    modal.innerHTML = `
        <div style="
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        ">
            <h3 style="margin: 0 0 16px 0; color: #2d3748; font-size: 20px;">📋 Создание контракта</h3>
            <p style="color: #718096; margin-bottom: 20px;">Настройте условия выполнения размещения:</p>
            
            <form id="contractForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Срок размещения (часов)
                    </label>
                    <input type="number" id="placementHours" value="24" min="1" max="168" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    ">
                    <small style="color: #718096;">Время на размещение рекламы в канале</small>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Срок мониторинга (дней)
                    </label>
                    <input type="number" id="monitoringDays" value="7" min="1" max="30" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    ">
                    <small style="color: #718096;">Время жизни поста для получения оплаты</small>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Требования к посту
                    </label>
                    <textarea id="postRequirements" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                        min-height: 80px;
                        resize: vertical;
                    " placeholder="Укажите особые требования к оформлению, тексту или времени публикации..."></textarea>
                </div>
                
                <div style="background: #ebf8ff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 8px 0; color: #2b6cb0;">📋 Процесс выполнения:</h4>
                    <ol style="margin: 0; padding-left: 16px; color: #2b6cb0;">
                        <li>Издатель размещает рекламу в канале</li>
                        <li>Подает заявку с ссылкой на пост</li>
                        <li>Автоматическая проверка размещения</li>
                        <li>Мониторинг в течение указанного срока</li>
                        <li>Автоматическая оплата при успешном завершении</li>
                    </ol>
                </div>
                
                <div style="display: flex; gap: 12px;">
                    <button type="button" onclick="closeContractModal()" style="
                        flex: 1;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        background: white;
                        color: #4a5568;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">Отмена</button>
                    
                    <button type="submit" style="
                        flex: 1;
                        padding: 12px;
                        border: none;
                        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                        color: white;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: 600;
                        cursor: pointer;
                    ">✅ Создать контракт</button>
                </div>
            </form>
        </div>
    `;

    // Обработчик формы
    const form = modal.querySelector('#contractForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        submitContract(responseId);
    });

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeContractModal();
        }
    });

    return modal;
}

async function submitContract(responseId) {
    const placementHours = parseInt(document.getElementById('placementHours').value) || 24;
    const monitoringDays = parseInt(document.getElementById('monitoringDays').value) || 7;
    const requirements = document.getElementById('postRequirements').value.trim();

    const submitBtn = document.querySelector('#contractForm button[type="submit"]');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Создание контракта...';

        // Сначала принимаем отклик
        const responseUpdate = await fetch(`/api/offers/responses/${responseId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                status: 'accepted',
                message: 'Отклик принят, создан контракт'
            })
        });

        const responseResult = await responseUpdate.json();
        if (!responseResult.success) {
            throw new Error(responseResult.error || 'Ошибка принятия отклика');
        }

        // Затем создаем контракт
        const contractResponse = await fetch(`/api/offers/responses/${responseId}/contract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                placement_hours: placementHours,
                monitoring_days: monitoringDays,
                requirements: requirements
            })
        });

        const contractResult = await contractResponse.json();

        if (contractResult.success) {
            alert('✅ Контракт создан!\n\nОба участника получили уведомления с деталями выполнения.');
            closeContractModal();
            closeResponsesModal();
        } else {
            throw new Error(contractResult.error || 'Ошибка создания контракта');
        }

    } catch (error) {
        console.error('❌ Ошибка создания контракта:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function closeContractModal() {
    const modal = document.querySelector('div[style*="z-index: 1001"]');
    if (modal) {
        modal.remove();
    }
}

// ===== ИНТЕРФЕЙС КОНТРАКТОВ ДЛЯ ИЗДАТЕЛЕЙ =====

function showContractsTab() {
    // Добавим новую вкладку "Контракты" в навигацию
    loadUserContracts();
}

async function loadUserContracts() {
    console.log('📋 Загрузка контрактов пользователя...');

    // Показываем состояние загрузки
    showContractsLoading();

    try {
        const response = await fetch('/api/offers/contracts', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Контракты загружены:', result.contracts?.length || 0);

            // Обновляем статистику
            updateContractsStats(result.contracts || []);

            // Отрисовываем контракты
            renderContracts(result.contracts || []);
        } else {
            throw new Error(result.error || 'Ошибка загрузки контрактов');
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки контрактов:', error);
        showContractsError('Ошибка загрузки контрактов: ' + error.message);
    } finally {
        hideContractsLoading();
    }
}

function showContractsLoading() {
    const loading = document.getElementById('contractsLoading');
    const grid = document.getElementById('contractsGrid');

    if (loading) {
        loading.style.display = 'block';
    }
    if (grid) {
        grid.innerHTML = '';
    }
}

function hideContractsLoading() {
    const loading = document.getElementById('contractsLoading');
    if (loading) {
        loading.style.display = 'none';
    }
}

function updateContractsStats(contracts) {
    // Подсчитываем статистику
    const activeCount = contracts.filter(c => ['active', 'verification', 'monitoring'].includes(c.status)).length;
    const completedCount = contracts.filter(c => c.status === 'completed').length;
    const totalEarnings = contracts
        .filter(c => c.status === 'completed' && c.role === 'publisher')
        .reduce((sum, c) => sum + (c.price || 0), 0);

    // Обновляем элементы статистики
    const activeElement = document.getElementById('activeContractsCount');
    const completedElement = document.getElementById('completedContractsCount');
    const earningsElement = document.getElementById('totalEarningsAmount');

    if (activeElement) {
        activeElement.textContent = activeCount;
    }
    if (completedElement) {
        completedElement.textContent = completedCount;
    }
    if (earningsElement) {
        earningsElement.textContent = formatPrice(totalEarnings) + ' ₽';
    }
}

// Добавить в app/static/js/offers.js функцию для показа инструкций

function showContractInstructions(contract) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.8); display: flex; align-items: center;
        justify-content: center; z-index: 1001; padding: 20px;
    `;

    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 500px; width: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #333;">📋 Как подтвердить размещение</h3>
                <button onclick="this.closest('div[style*=\"z-index\"]').remove()" 
                        style="background: none; border: none; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="margin-bottom: 20px;">
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <h4 style="margin: 0 0 12px 0; color: #495057;">🎯 Контракт: ${contract.offer_title}</h4>
                    <p style="margin: 0; color: #6c757d;">💰 Сумма: ${contract.price} RUB</p>
                    <p style="margin: 4px 0 0 0; color: #6c757d;">📺 Канал: ${contract.channel_title}</p>
                </div>
                
                <h4 style="color: #333; margin-bottom: 12px;">Пошаговая инструкция:</h4>
                <ol style="padding-left: 20px; line-height: 1.6; color: #555;">
                    <li style="margin-bottom: 8px;"><strong>Разместите рекламу</strong> в своём канале согласно требованиям оффера</li>
                    <li style="margin-bottom: 8px;"><strong>Перейдите к нашему боту:</strong> 
                        <a href="https://t.me/bot_username" target="_blank" style="color: #007bff;">@your_bot_username</a>
                    </li>
                    <li style="margin-bottom: 8px;"><strong>Переслать пост с рекламой</strong> боту (нажмите "Forward" на сообщении)</li>
                    <li><strong>Дождитесь автоматического подтверждения</strong> - обычно это занимает несколько секунд</li>
                </ol>
                
                <div style="background: #e3f2fd; padding: 12px; border-radius: 6px; margin-top: 16px;">
                    <p style="margin: 0; font-size: 14px; color: #1565c0;">
                        💡 <strong>Важно:</strong> Бот автоматически найдёт ваш контракт и проверит размещение. 
                        После успешной проверки начнётся мониторинг на ${contract.monitoring_duration || 7} дней.
                    </p>
                </div>
            </div>
            
            <div style="display: flex; gap: 12px; justify-content: flex-end;">
                <button onclick="this.closest('div[style*=\"z-index\"]').remove()" 
                        style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer;">
                    Закрыть
                </button>
                <button onclick="window.open('https://t.me/your_bot_username', '_blank')" 
                        style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    🤖 Открыть бота
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Добавить кнопку "Как подтвердить размещение" в интерфейс контрактов
function addContractInstructionsButton(contractElement, contract) {
    if (contract.status === 'active' && contract.role === 'publisher') {
        const instructionsBtn = document.createElement('button');
        instructionsBtn.innerHTML = '📋 Как подтвердить размещение';
        instructionsBtn.style.cssText = `
            background: #17a2b8; color: white; border: none; 
            padding: 8px 16px; border-radius: 6px; cursor: pointer;
            margin-top: 8px; font-size: 14px;
        `;
        instructionsBtn.onclick = () => showContractInstructions(contract);

        contractElement.querySelector('.contract-actions')?.appendChild(instructionsBtn);
    }
}

// Модифицировать функцию renderContracts для добавления кнопок инструкций
// Найти в существующем коде место создания элементов контракта и добавить:
// addContractInstructionsButton(contractElement, contract);

// ===== ОБНОВЛЕНИЕ СУЩЕСТВУЮЩИХ ФУНКЦИЙ =====

// Обновляем функцию showOfferDetails для показа откликов
function showOfferDetails(offerId) {
    console.log('📋 Показ деталей оффера:', offerId);

    // Создаем детальное модальное окно
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #2d3748; font-size: 20px;">📋 Детали оффера</h3>
                <button onclick="closeOfferDetailsModal()" style="
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #718096;
                ">×</button>
            </div>
            
            <div style="text-align: center; padding: 40px; color: #718096;">
                <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                <p>Загрузка деталей оффера...</p>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Здесь можно добавить загрузку деталей оффера через API
    setTimeout(() => {
        modal.querySelector('div[style*="text-align: center"]').innerHTML = `
            <h4>Оффер #${offerId}</h4>
            <p>Подробная информация об оффере будет здесь</p>
            <button onclick="closeOfferDetailsModal()" style="
                padding: 8px 16px;
                border: none;
                background: #667eea;
                color: white;
                border-radius: 6px;
                cursor: pointer;
            ">Закрыть</button>
        `;
    }, 1000);
}

function closeOfferDetailsModal() {
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
    }
}

// Обновляем функцию switchTab для загрузки офферов при переходе на вкладку поиска
const originalSwitchTab = window.switchTab;
window.switchTab = function(tabName) {
    originalSwitchTab(tabName);

    if (tabName === 'find-offer') {
        // Загружаем доступные офферы при первом переходе на вкладку
        setTimeout(() => {
            loadAvailableOffers({});
        }, 100);
    }
};

// Настройка поиска в реальном времени для вкладки поиска
document.addEventListener('DOMContentLoaded', function() {
    const findSearchInput = document.getElementById('findOffersSearch');
    if (findSearchInput) {
        findSearchInput.addEventListener('input', function() {
            // Debounce для поиска
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                applyFindFilters();
            }, 500);
        });
    }
});

// Универсальная функция обновления статуса
async function updateOfferStatus(offerId, newStatus, reason, buttonElement, loadingText) {
    const originalText = buttonElement?.textContent;

    try {
        // Блокируем кнопку
        if (buttonElement) {
            buttonElement.disabled = true;
            buttonElement.textContent = `⏳ ${loadingText}`;
            buttonElement.style.opacity = '0.6';
        }

        console.log(`🔄 Изменение статуса оффера ${offerId} на ${newStatus}`);

        const response = await fetch(`/api/offers/${offerId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                status: newStatus,
                reason: reason || ''
            })
        });

        const result = await response.json();
        console.log('📥 Ответ сервера:', result);

        if (response.ok && result.success) {
            console.log(`✅ Статус успешно изменен на ${newStatus}`);

            // Показываем сообщение об успехе
            alert(`✅ ${result.message}`);

            // Обновляем интерфейс
            updateOfferCardStatus(offerId, newStatus);

        } else {
            throw new Error(result.error || `Ошибка изменения статуса на ${newStatus}`);
        }

    } catch (error) {
        console.error('❌ Ошибка изменения статуса:', error);
        alert(`❌ Ошибка: ${error.message}`);

        // Восстанавливаем кнопку
        if (buttonElement) {
            buttonElement.disabled = false;
            buttonElement.textContent = originalText;
            buttonElement.style.opacity = '1';
        }
    }
}

// Обновление статуса карточки без перезагрузки
function updateOfferCardStatus(offerId, newStatus) {
    const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
    if (!offerCard) return;

    // Обновляем статус-бейдж
    const statusBadge = offerCard.querySelector('.offer-header span');
    if (statusBadge) {
        const statusTexts = {
            'active': 'Активен',
            'paused': 'Приостановлен',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        };

        const statusColors = {
            'active': { bg: '#d4edda', color: '#155724' },
            'paused': { bg: '#fff3cd', color: '#856404' },
            'completed': { bg: '#d1ecf1', color: '#0c5460' },
            'cancelled': { bg: '#f8d7da', color: '#721c24' }
        };

        statusBadge.textContent = statusTexts[newStatus] || newStatus;
        const colors = statusColors[newStatus] || statusColors['active'];
        statusBadge.style.background = colors.bg;
        statusBadge.style.color = colors.color;
    }

    // Перезагружаем всю страницу для обновления кнопок
    setTimeout(() => {
        loadMyOffers();
    }, 1000);
}

async function showResponseModal(offer) {
    console.log('📝 Показываем форму отклика для оффера:', offer.id);

    try {
        // Сначала загружаем верифицированные каналы пользователя
        const channelsResponse = await fetch('/api/channels/my?verified=true', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const channelsResult = await channelsResponse.json();

        if (!channelsResult.success || !channelsResult.channels || channelsResult.channels.length === 0) {
            // Нет верифицированных каналов
            showNoChannelsModal();
            return;
        }

        const verifiedChannels = channelsResult.channels;

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.id = 'responseModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;

        modal.innerHTML = `
            <div style="
                background: white;
                border-radius: 12px;
                padding: 24px;
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #2d3748; font-size: 20px;">📝 Отклик на оффер</h3>
                    <button onclick="closeResponseModal()" style="
                        background: none; border: none; font-size: 24px; 
                        cursor: pointer; color: #666;
                    ">&times;</button>
                </div>
                
                <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 8px 0; color: #2d3748;">🎯 ${offer.title}</h4>
                    <p style="margin: 0; color: #718096; font-size: 14px;">
                        💰 Бюджет: ${offer.total_budget || 'Не указан'} RUB
                    </p>
                </div>
                
                <form id="responseForm">
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
                            Выберите канал <span style="color: #e53e3e;">*</span>
                        </label>
                        <select id="selectedChannel" required style="
                            width: 100%;
                            padding: 12px;
                            border: 2px solid #e2e8f0;
                            border-radius: 6px;
                            font-size: 16px;
                            background: white;
                        ">
                            <option value="">-- Выберите канал --</option>
                            ${verifiedChannels.map(channel => `
                                <option value="${channel.id}" data-channel='${JSON.stringify(channel)}'>
                                    ${channel.title} (@${channel.username}) - ${formatNumber(channel.subscriber_count)} подписчиков
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <div id="channelPreview" style="display: none; margin-bottom: 20px; padding: 16px; background: #e6fffa; border-radius: 8px; border-left: 4px solid #38b2ac;">
                        <h5 style="margin: 0 0 8px 0; color: #2c7a7b;">📺 Выбранный канал:</h5>
                        <div id="channelDetails"></div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
                            Сообщение рекламодателю
                        </label>
                        <textarea id="responseMessage" style="
                            width: 100%;
                            min-height: 100px;
                            padding: 12px;
                            border: 2px solid #e2e8f0;
                            border-radius: 6px;
                            font-size: 16px;
                            resize: vertical;
                            font-family: inherit;
                        " placeholder="Расскажите о своём канале, предложите варианты размещения..."></textarea>
                        <div style="font-size: 12px; color: #718096; margin-top: 4px;">
                            Опишите преимущества вашего канала и условия размещения
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 12px; justify-content: flex-end;">
                        <button type="button" onclick="closeResponseModal()" style="
                            padding: 12px 24px;
                            border: 2px solid #e2e8f0;
                            background: white;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 16px;
                        ">Отмена</button>
                        <button type="submit" id="submitResponseBtn" style="
                            padding: 12px 24px;
                            background: #3182ce;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 600;
                        ">Отправить отклик</button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';

        // Обработчик выбора канала
        document.getElementById('selectedChannel').addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const preview = document.getElementById('channelPreview');
            const details = document.getElementById('channelDetails');

            if (selectedOption.value) {
                const channelData = JSON.parse(selectedOption.getAttribute('data-channel'));

                details.innerHTML = `
                    <div style="font-size: 14px; color: #2c7a7b;">
                        <strong>${channelData.title}</strong><br>
                        Username: @${channelData.username}<br>
                        Подписчики: ${formatNumber(channelData.subscriber_count)}<br>
                        Категория: ${channelData.category || 'Не указана'}<br>
                        ${channelData.description ? `Описание: ${channelData.description}` : ''}
                    </div>
                `;
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
            }
        });

        // Обработчик формы
        document.getElementById('responseForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            await submitResponse(offer.id);
        });

    } catch (error) {
        console.error('❌ Ошибка загрузки каналов:', error);
        alert('Ошибка загрузки каналов. Попробуйте позже.');
    }
}

function showNoChannelsModal() {
    const modal = document.createElement('div');
    modal.id = 'responseModal';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); display: flex; align-items: center;
        justify-content: center; z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 400px; width: 90%; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">📺</div>
            <h3 style="margin: 0 0 16px 0; color: #2d3748;">Нет верифицированных каналов</h3>
            <p style="margin: 0 0 20px 0; color: #718096;">
                Для отклика на офферы нужно добавить и верифицировать хотя бы один канал.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button onclick="closeResponseModal()" style="
                    padding: 10px 20px; border: 2px solid #e2e8f0; background: white;
                    border-radius: 6px; cursor: pointer;
                ">Закрыть</button>
                <button onclick="window.location.href='/channels'" style="
                    padding: 10px 20px; background: #3182ce; color: white;
                    border: none; border-radius: 6px; cursor: pointer; font-weight: 600;
                ">Добавить канал</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

async function submitResponse(offerId) {
    const submitBtn = document.getElementById('submitResponseBtn');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Отправка...';

        const selectedChannelElement = document.getElementById('selectedChannel');
        const selectedOption = selectedChannelElement.options[selectedChannelElement.selectedIndex];

        if (!selectedOption.value) {
            throw new Error('Выберите канал');
        }

        const channelData = JSON.parse(selectedOption.getAttribute('data-channel'));
        const message = document.getElementById('responseMessage').value.trim();

        const response = await fetch(`/api/offers/${offerId}/respond`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                channel_id: channelData.id,
                channel_title: channelData.title,
                channel_username: channelData.username,
                channel_subscribers: channelData.subscriber_count,
                message: message
            })
        });

        const result = await response.json();

        if (result.success) {
            closeResponseModal();
            showNotification('success', '✅ Отклик отправлен! Рекламодатель получил уведомление.');

            // Обновляем список офферов если находимся на соответствующей странице
            if (typeof loadOffers === 'function') {
                loadOffers();
            }
        } else {
            throw new Error(result.error || 'Ошибка отправки отклика');
        }

    } catch (error) {
        console.error('❌ Ошибка отправки отклика:', error);
        alert(`❌ Ошибка: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function closeResponseModal() {
    const modal = document.getElementById('responseModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = 'auto';
    }
}

function formatNumber(num) {
    if (!num) return '0';
    return new Intl.NumberFormat('ru-RU').format(num);
}


// Добавляем функции в глобальную область видимости
window.cancelOffer = cancelOffer;
window.pauseOffer = pauseOffer;
window.resumeOffer = resumeOffer;
window.completeOffer = completeOffer;
window.updateOfferStatus = updateOfferStatus;

// Добавляем функции в глобальную область видимости
window.deleteOffer = deleteOffer;
window.deleteMultipleOffers = deleteMultipleOffers;
// ===== ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Инициализация страницы офферов');

    // Загружаем офферы по умолчанию
    loadMyOffers();

    // Настройка поиска
    setupOffersSearch();

    console.log('✅ Страница офферов инициализирована');
});
// Добавляем функции в глобальную область видимости
window.closeContractModal = closeContractModal;
window.showContractsTab = showContractsTab;
window.loadUserContracts = loadUserContracts;
window.showContractDetails = showContractDetails;
window.closeContractDetailsModal = closeContractDetailsModal;
window.showPlacementForm = showPlacementForm;
window.closePlacementForm = closePlacementForm;
window.cancelContract = cancelContract;
// ===== ЭКСПОРТ ФУНКЦИЙ =====
window.switchTab = switchTab;
window.loadMyOffers = loadMyOffers;
window.goBack = goBack;
window.OffersManager = OffersManager;
window.getTelegramUserId = getTelegramUserId;
window.editOffer = editOffer;
window.viewOfferDetails = viewOfferDetails;
// Добавляем функции в глобальную область видимости
window.acceptOffer = acceptOffer;
window.manageResponses = manageResponses;
window.showOfferDetails = showOfferDetails;
window.closeResponseModal = closeResponseModal;
window.closeResponsesModal = closeResponsesModal;
window.closeOfferDetailsModal = closeOfferDetailsModal;
window.updateResponseStatus = updateResponseStatus;
console.log('✅ offers.js загружен успешно');