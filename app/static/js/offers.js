// app/static/js/offers.js - ПО АНАЛОГИИ С CHANNELS

// ===== ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ ВКЛАДОК (точно как в channels-ui.js) =====
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

// ===== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP (как в channels) =====
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
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

        const response = await fetch('/api/offers/my', {
            headers: {
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

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
        showOffersError('Ошибка загрузки офферов');
    }
}

function renderOffers(offers) {
    const container = document.getElementById('offersGrid');
    const emptyState = document.getElementById('emptyOffersState');

    if (!container) return;

    // Скрываем пустое состояние
    if (emptyState) {
        emptyState.style.display = 'none';
    }

    container.innerHTML = offers.map(offer => `
        <div class="offer-card">
            <div class="offer-header">
                <div class="offer-title">${escapeHtml(offer.title || 'Без названия')}</div>
                <div class="offer-status status-${offer.status || 'pending'}">${getStatusText(offer.status)}</div>
            </div>
            
            <div class="offer-meta">
                <div class="meta-item">
                    <span>💰</span>
                    <span>${formatCurrency(offer.price || offer.budget || 0)} ${offer.currency || 'RUB'}</span>
                </div>
                <div class="meta-item">
                    <span>📅</span>
                    <span>${formatDate(offer.created_at)}</span>
                </div>
                <div class="meta-item">
                    <span>👥</span>
                    <span>Мин. ${formatNumber(offer.min_subscribers || 0)} подписчиков</span>
                </div>
                ${offer.responses_count ? `
                <div class="meta-item">
                    <span>💬</span>
                    <span>${offer.responses_count} откликов</span>
                </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function showOffersLoading() {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <div class="loading-spinner"></div>
                <div>Загрузка офферов...</div>
            </div>
        `;
    }
}

function showEmptyOffersState() {
    const container = document.getElementById('offersGrid');
    const emptyState = document.getElementById('emptyOffersState');

    if (container) {
        container.innerHTML = '';
    }

    if (emptyState) {
        emptyState.style.display = 'block';
    }
}

function showOffersError(message) {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--danger-color);">
                <div>❌ ${message}</div>
                <button class="btn btn-primary" onclick="loadMyOffers()" style="margin-top: 16px;">
                    🔄 Попробовать снова
                </button>
            </div>
        `;
    }
}

// ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (как в channels) =====
function getStatusText(status) {
    const statusMap = {
        'active': 'Активен',
        'pending': 'На модерации',
        'paused': 'Приостановлен',
        'completed': 'Завершен',
        'draft': 'Черновик'
    };
    return statusMap[status] || 'Неизвестно';
}

function formatCurrency(amount) {
    return Number(amount || 0).toLocaleString('ru-RU');
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatDate(dateString) {
    if (!dateString) return 'Не указано';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function getTelegramUserId() {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        return window.Telegram.WebApp.initDataUnsafe.user?.id || 'demo_user';
    }
    return 'demo_user';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function goBack() {
    try {
        console.log('🔙 Переход на главную страницу');
        window.location.href = '/';
    } catch (error) {
        console.error('Ошибка при переходе на главную:', error);
        window.location = '/';
    }
}

// ===== ПОИСК ПО ОФФЕРАМ (как поиск в channels) =====
function setupOffersSearch() {
    const searchInput = document.getElementById('offersSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
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

        // Обновляем progress bar
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
        if (this.currentStep < this.totalSteps) {
            this.updateStep(this.currentStep + 1);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.updateStep(this.currentStep - 1);
        }
    }

    updatePreview() {
        // Обновляем предпросмотр
        const titleInput = document.querySelector('input[name="title"]');
        const budgetInput = document.querySelector('input[name="budget"]');

        if (titleInput) {
            const previewTitle = document.getElementById('previewTitle');
            if (previewTitle) {
                previewTitle.textContent = titleInput.value || 'Не указано';
            }
        }

        if (budgetInput) {
            const previewBudget = document.getElementById('previewBudget');
            if (previewBudget) {
                const budget = budgetInput.value;
                previewBudget.textContent = budget ? `₽${Number(budget).toLocaleString()}` : 'Не указан';
            }
        }

        // Тематики
        const selectedChips = document.querySelectorAll('.chip.selected');
        const previewTopics = document.getElementById('previewTopics');
        if (previewTopics) {
            const topics = Array.from(selectedChips).map(chip => chip.textContent).join(', ');
            previewTopics.textContent = topics || 'Не выбраны';
        }

        // География
        const geographySelect = document.querySelector('select[name="geography"]');
        const previewGeography = document.getElementById('previewGeography');
        if (previewGeography && geographySelect) {
            const geographyMap = {
                'russia': 'Россия',
                'cis': 'СНГ',
                'europe': 'Европа',
                'world': 'Весь мир'
            };
            previewGeography.textContent = geographyMap[geographySelect.value] || 'Не указана';
        }
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
            const formData = this.collectFormData();

            const response = await fetch('/api/offers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': getTelegramUserId()
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                alert('✅ Оффер успешно создан!');
                // Переходим на вкладку "Мои офферы"
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

// ===== ИНИЦИАЛИЗАЦИЯ (как в channels) =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Инициализация страницы офферов');

    // Загружаем офферы по умолчанию (первая вкладка)
    loadMyOffers();

    // Настройка поиска
    setupOffersSearch();

    // Инициализация существующего функционала создания офферов
    if (typeof OffersManager !== 'undefined') {
        window.offersManager = new OffersManager();
    }

    console.log('✅ Страница офферов инициализирована');
});

// ===== ДЕЛАЕМ ФУНКЦИИ ГЛОБАЛЬНО ДОСТУПНЫМИ (как в channels) =====
window.switchTab = switchTab;
window.loadMyOffers = loadMyOffers;
window.goBack = goBack;
window.OffersManager = OffersManager;