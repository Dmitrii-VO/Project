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

    if (tabName === 'my-offers') {
        loadMyOffers();
    } else if (tabName === 'create-offer') {
        // Инициализируем OffersManager только при переходе на вкладку создания
        initializeOffersManager();
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
        const rawPrice = offer.price || 0;
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'Не указана';
        const status = offer.status || 'active';
        const responseCount = offer.response_count || 0;
        const createdAt = offer.created_at || '';

        const formattedPrice = formatPrice(rawPrice);
        const formattedDate = formatDate(createdAt);

        const statusText = {
            'active': 'Активен',
            'paused': 'Приостановлен',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        }[status] || 'Неизвестно';

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
                    ${status === 'active' || status === 'paused' ? `
                    <button onclick="cancelOffer(${offer.id}, '${title.replace(/'/g, "\\'")}', this)" style="padding: 8px 16px; border: 1px solid #ffc107; background: #ffc107; color: #212529; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        ❌ Отменить
                    </button>` : ''}
                    ${status === 'paused' ? `
                    <button onclick="resumeOffer(${offer.id}, this)" style="padding: 8px 16px; border: 1px solid #28a745; background: #28a745; color: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        ▶️ Возобновить
                    </button>` : ''}
                    ${status === 'active' ? `
                    <button onclick="pauseOffer(${offer.id}, this)" style="padding: 8px 16px; border: 1px solid #6c757d; background: #6c757d; color: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        ⏸️ Приостановить
                    </button>` : ''}
                    ${status === 'completed' || status === 'cancelled' ? `
                    <button onclick="deleteOffer(${offer.id}, '${title.replace(/'/g, "\\'")}', this)" style="padding: 8px 16px; border: 1px solid #dc3545; background: #dc3545; color: white; border-radius: 6px; cursor: pointer; font-size: 13px;">
                        🗑️ Удалить
                    </button>` : ''}
                </div>
                
                <div style="margin-top: 10px; font-size: 12px; color: #666;">
                    ID: ${offer.id}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    console.log('✅ Офферы отрисованы');
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

    // 2. БЮДЖЕТ
    const budgetInput = document.querySelector('input[name="budget"]');
    const previewBudget = document.getElementById('previewBudget');
    if (previewBudget) {
        const budget = budgetInput?.value;
        previewBudget.textContent = budget ? formatPrice(budget) + ' RUB' : 'Не указан';
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

            // Бюджет
            const budgetField = document.querySelector('input[name="budget"]');
            if (budgetField && budgetField.value) {
                const budgetValue = parseFloat(budgetField.value);
                if (budgetValue > 0) {
                    data.budget_total = budgetValue;
                    data.price = Math.min(budgetValue, 10000);
                } else {
                    throw new Error('Укажите корректный бюджет');
                }
            } else {
                throw new Error('Укажите бюджет');
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

    console.log('🎯 Фильтры:', filters);
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
        const price = formatPrice(offer.price || 0);
        const currency = offer.currency || 'RUB';
        const category = offer.category || 'Не указана';
        const minSubscribers = offer.min_subscribers || 0;
        const maxSubscribers = offer.max_subscribers || 'Без ограничений';
        const createdAt = formatDate(offer.created_at);
        const creatorName = offer.creator_name || 'Неизвестный автор';

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
                
                <div style="margin: 12px 0; color: #666; font-size: 14px; line-height: 1.5;">
                    ${shortDescription}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee;">
                    <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                        <div style="font-size: 12px; color: #888;">
                            💰 <strong style="color: #333;">${price} ${currency}</strong>
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            📂 <strong style="color: #333;">${category}</strong>
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            👥 <strong style="color: #333;">${subscribersText}</strong>
                        </div>
                        <div style="font-size: 12px; color: #888;">
                            📅 <strong style="color: #333;">${createdAt}</strong>
                        </div>
                    </div>
                    
                    <button class="btn btn-primary" style="padding: 8px 16px; font-size: 12px; margin-left: 12px;" onclick="event.stopPropagation(); acceptOffer(${offer.id})">
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

function showOfferDetails(offerId) {
    console.log('📋 Показ деталей оффера:', offerId);
    // TODO: Можно добавить модальное окно или переход на страницу деталей
    alert(`Детали оффера #${offerId}\n\nЗдесь будет подробная информация об оффере.`);
}

function acceptOffer(offerId) {
    console.log('✅ Принятие оффера:', offerId);

    if (confirm('Вы хотите принять этот оффер?')) {
        // TODO: Реализовать API для принятия оффера
        alert(`Оффер #${offerId} принят!\n\nФункционал в разработке.`);
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

// ===== ЭКСПОРТ ФУНКЦИЙ =====
window.switchTab = switchTab;
window.loadMyOffers = loadMyOffers;
window.goBack = goBack;
window.OffersManager = OffersManager;
window.getTelegramUserId = getTelegramUserId;
window.editOffer = editOffer;
window.viewOfferDetails = viewOfferDetails;

console.log('✅ offers.js загружен успешно');