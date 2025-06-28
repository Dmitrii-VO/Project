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
        const responseCount = offer.response_count || 0;
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
                
                <!-- Компактные кнопки - ИСПРАВЛЕННАЯ ЛОГИКА -->
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
                    
                    <!-- Кнопка "Отклики" если есть отклики -->
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
                        <!-- Для активных: Приостановить и Отменить -->
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
                        <!-- Для приостановленных: Возобновить и Отменить -->
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
                        <!-- Для завершенных/отмененных: Удалить -->
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
    console.log('✅ Компактные офферы отрисованы');
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

// Функция для форматирования чисел (например, 1000 -> 1K)
function formatNumber(num) {
    if (!num || num === 0) return '0';

    if (num >= 1000000) {
        return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    }
    return num.toString();
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

// Добавьте эти функции в offers.js

// ===== ФУНКЦИИ РАБОТЫ С ОТКЛИКАМИ =====

async function acceptOffer(offerId) {
    console.log('✅ Отклик на оффер:', offerId);

    // Показываем модальное окно для ввода информации о канале
    const modal = createResponseModal(offerId);
    document.body.appendChild(modal);
}

function createResponseModal(offerId) {
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
            <h3 style="margin: 0 0 16px 0; color: #2d3748; font-size: 20px;">📝 Отклик на оффер</h3>
            
            <form id="responseForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Название канала <span style="color: #e53e3e;">*</span>
                    </label>
                    <input type="text" id="channelTitle" required style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    " placeholder="Например: IT новости">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Username канала
                    </label>
                    <input type="text" id="channelUsername" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    " placeholder="@mychannel">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Количество подписчиков
                    </label>
                    <input type="number" id="channelSubscribers" min="0" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                    " placeholder="1000">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #2d3748;">
                        Сообщение рекламодателю
                    </label>
                    <textarea id="responseMessage" style="
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e2e8f0;
                        border-radius: 6px;
                        font-size: 16px;
                        min-height: 80px;
                        resize: vertical;
                    " placeholder="Расскажите о своем канале, предложите варианты размещения..."></textarea>
                </div>
                
                <div style="display: flex; gap: 12px;">
                    <button type="button" onclick="closeResponseModal()" style="
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
                    ">✅ Отправить отклик</button>
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
    const channelTitle = document.getElementById('channelTitle').value.trim();
    const channelUsername = document.getElementById('channelUsername').value.trim();
    const channelSubscribers = parseInt(document.getElementById('channelSubscribers').value) || 0;
    const message = document.getElementById('responseMessage').value.trim();

    if (!channelTitle) {
        alert('Укажите название канала');
        return;
    }

    const submitBtn = document.querySelector('#responseForm button[type="submit"]');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Отправка...';

        const response = await fetch(`/api/offers/${offerId}/respond`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                channel_title: channelTitle,
                channel_username: channelUsername.replace('@', ''),
                channel_subscribers: channelSubscribers,
                message: message
            })
        });

        const result = await response.json();

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

function closeResponseModal() {
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
    }
}

// ===== ФУНКЦИИ УПРАВЛЕНИЯ ОТКЛИКАМИ (для авторов офферов) =====

async function manageResponses(offerId) {
    console.log('💬 Управление откликами для оффера:', offerId);

    try {
        const response = await fetch(`/api/offers/${offerId}/responses`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success) {
            showResponsesModal(offerId, result.responses);
        } else {
            throw new Error(result.error || 'Ошибка загрузки откликов');
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки откликов:', error);
        alert(`❌ Ошибка: ${error.message}`);
    }
}

function showResponsesModal(offerId, responses) {
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

    let responsesHtml = '';

    if (responses.length === 0) {
        responsesHtml = `
            <div style="text-align: center; padding: 40px; color: #718096;">
                <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                <h3>Пока нет откликов</h3>
                <p>Когда владельцы каналов откликнутся на ваш оффер, они появятся здесь</p>
            </div>
        `;
    } else {
        responses.forEach(response => {
            const statusColor = {
                'pending': '#ed8936',
                'accepted': '#48bb78',
                'rejected': '#e53e3e'
            }[response.status] || '#718096';

            const statusText = {
                'pending': 'На рассмотрении',
                'accepted': 'Принят',
                'rejected': 'Отклонен'
            }[response.status] || response.status;

            const createdDate = formatDate(response.created_at);

            responsesHtml += `
                <div style="
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                    background: white;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="margin: 0; color: #2d3748; font-size: 16px;">${response.user_name}</h4>
                        <span style="
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: 500;
                            background: ${statusColor}20;
                            color: ${statusColor};
                        ">${statusText}</span>
                    </div>
                    
                    <div style="margin-bottom: 12px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px;">
                            <div><strong>Канал:</strong> ${response.channel_title}</div>
                            <div><strong>Username:</strong> @${response.channel_username}</div>
                            <div><strong>Подписчики:</strong> ${formatNumber(response.channel_subscribers)}</div>
                            <div><strong>Дата:</strong> ${createdDate}</div>
                        </div>
                    </div>
                    
                    ${response.message ? `
                        <div style="
                            background: #f7fafc;
                            padding: 12px;
                            border-radius: 6px;
                            margin-bottom: 12px;
                            font-size: 14px;
                            line-height: 1.4;
                        ">
                            <strong>Сообщение:</strong><br>
                            ${response.message}
                        </div>
                    ` : ''}
                    
                    ${response.status === 'pending' ? `
                        <div style="display: flex; gap: 8px;">
                            <button onclick="updateResponseStatus(${response.id}, 'accepted')" style="
                                flex: 1;
                                padding: 8px 12px;
                                border: none;
                                background: #48bb78;
                                color: white;
                                border-radius: 6px;
                                font-size: 14px;
                                font-weight: 600;
                                cursor: pointer;
                            ">✅ Принять</button>
                            
                            <button onclick="updateResponseStatus(${response.id}, 'rejected')" style="
                                flex: 1;
                                padding: 8px 12px;
                                border: none;
                                background: #e53e3e;
                                color: white;
                                border-radius: 6px;
                                font-size: 14px;
                                font-weight: 600;
                                cursor: pointer;
                            ">❌ Отклонить</button>
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

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
                <h3 style="margin: 0; color: #2d3748; font-size: 20px;">💬 Отклики на оффер</h3>
                <button onclick="closeResponsesModal()" style="
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #718096;
                ">×</button>
            </div>
            
            <div style="margin-bottom: 16px; padding: 12px; background: #ebf8ff; border-radius: 8px; font-size: 14px;">
                📊 <strong>Всего откликов:</strong> ${responses.length}
            </div>
            
            ${responsesHtml}
        </div>
    `;

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeResponsesModal();
        }
    });

    document.body.appendChild(modal);
}

function closeResponsesModal() {
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
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
                        ">❌</button>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
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

    try {
        const response = await fetch('/api/offers/contracts', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const result = await response.json();

        if (result.success && result.contracts) {
            renderUserContracts(result.contracts); // предполагаемая функция отрисовки
        } else {
            console.warn('⚠️ Контракты не найдены или ошибка в ответе:', result);
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки контрактов:', error);
    }
}



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