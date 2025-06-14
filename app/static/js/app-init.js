// static/js/app-init.js - Инициализация всего приложения

// === ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ===
class TelegramMiniApp {
    constructor() {
        this.initialized = false;
        this.loadingSteps = [
            'Подключение к Telegram...',
            'Аутентификация пользователя...',
            'Загрузка данных...',
            'Настройка интерфейса...'
        ];
        this.currentStep = 0;
    }

    async init() {
        try {
            console.log('🚀 Starting Telegram Mini App initialization...');

            // Показываем экран загрузки
            this.updateLoadingStep(0);

            // 1. Инициализация Telegram WebApp
            const telegramInitialized = initTelegramWebApp();
            await this.delay(500);

            // 2. Аутентификация пользователя
            this.updateLoadingStep(1);
            const user = await getTelegramUser();

            if (user) {
                console.log('✅ User authenticated:', user.first_name);
            } else {
                console.log('⚠️ No user data available');
            }

            await this.delay(500);

            // 3. Загрузка данных приложения
            this.updateLoadingStep(2);
            await this.loadAppData();
            await this.delay(500);

            // 4. Настройка интерфейса
            this.updateLoadingStep(3);
            this.setupUI();
            await this.delay(300);

            // Завершение инициализации
            this.initialized = true;
            console.log('✅ Telegram Mini App fully initialized');

            // Показываем приложение
            this.showApp();

            // Haptic feedback при успешной инициализации
            if (window.appGlobals.tg && window.appGlobals.tg.HapticFeedback) {
                window.appGlobals.tg.HapticFeedback.notificationOccurred('success');
            }

        } catch (error) {
            console.error('❌ Initialization failed:', error);
            this.showError('Ошибка инициализации приложения');
        }
    }

    updateLoadingStep(stepIndex) {
        this.currentStep = stepIndex;
        const loadingScreen = document.getElementById('loading-screen');

        if (loadingScreen && this.loadingSteps[stepIndex]) {
            const textElement = loadingScreen.querySelector('div:last-child');
            if (textElement) {
                textElement.textContent = this.loadingSteps[stepIndex];
            }
        }
    }

    async loadAppData() {
        try {
            // Загружаем статистику (если на главной странице)
            if (window.location.pathname === '/' || window.location.pathname === '/index') {
                await this.loadStats();
                await this.loadRecentActivity();
            }

            // Загружаем данные для конкретных страниц
            const path = window.location.pathname;

            if (path.includes('channels')) {
                await this.loadChannels();
            } else if (path.includes('offers')) {
                await this.loadOffers();
            } else if (path.includes('analytics')) {
                await this.loadAnalytics();
            }

        } catch (error) {
            console.error('❌ Error loading app data:', error);
            // Продолжаем работу даже если данные не загрузились
        }
    }

    setupUI() {
        // Настройка элементов интерфейса
        this.setupEventListeners();
        this.setupTelegramTheme();
        this.setupKeyboardHandling();
    }

    setupEventListeners() {
        // Обработчики для форм
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });

        // Обработчики для кнопок
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', this.handleButtonClick.bind(this));
        });
    }

    setupTelegramTheme() {
        if (window.appGlobals && window.appGlobals.tg) {
            const tg = window.appGlobals.tg;

            // Применяем цвета Telegram
            if (tg.themeParams) {
                document.documentElement.style.setProperty('--tg-bg-color', tg.themeParams.bg_color || '#ffffff');
                document.documentElement.style.setProperty('--tg-text-color', tg.themeParams.text_color || '#000000');
                document.documentElement.style.setProperty('--tg-button-color', tg.themeParams.button_color || '#0088cc');
            }
        }
    }

    setupKeyboardHandling() {
        // Обработка клавиатуры для лучшего UX в Telegram
        if (window.appGlobals && window.appGlobals.tg) {
            const tg = window.appGlobals.tg;

            // Настройка главной кнопки
            if (tg.MainButton) {
                tg.MainButton.text = 'Готово';
                tg.MainButton.show();
                tg.MainButton.onClick(this.handleMainButtonClick.bind(this));
            }

            // Настройка кнопки назад
            if (tg.BackButton) {
                tg.BackButton.show();
                tg.BackButton.onClick(this.handleBackButtonClick.bind(this));
            }
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        const form = event.target;

        try {
            showLoading('Сохранение...');

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            const response = await apiRequest(form.action || '/api/submit', {
                method: form.method || 'POST',
                body: JSON.stringify(data),
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            hideLoading();

            if (response.success) {
                showAlert('Сохранено успешно!');

                // Haptic feedback при успехе
                if (window.appGlobals.tg && window.appGlobals.tg.HapticFeedback) {
                    window.appGlobals.tg.HapticFeedback.notificationOccurred('success');
                }

                // Перенаправление после успеха
                if (response.redirect) {
                    setTimeout(() => navigateTo(response.redirect), 1000);
                }
            }

        } catch (error) {
            hideLoading();
            showAlert('Произошла ошибка при сохранении');

            if (window.appGlobals.tg && window.appGlobals.tg.HapticFeedback) {
                window.appGlobals.tg.HapticFeedback.notificationOccurred('error');
            }
        }
    }

    handleButtonClick(event) {
        const button = event.target;
        const action = button.dataset.action;

        switch (action) {
            case 'navigate':
                const url = button.dataset.url;
                if (url) navigateTo(url);
                break;
            case 'submit':
                this.submitCurrentForm();
                break;
            case 'reload':
                this.loadAppData();
                break;
            default:
                console.log('Unknown action:', action);
        }
    }

    handleMainButtonClick() {
        this.submitCurrentForm();
    }

    handleBackButtonClick() {
        if (window.history.length > 1) {
            window.history.back();
        } else if (window.appGlobals.tg) {
            window.appGlobals.tg.close();
        }
    }

    submitCurrentForm() {
        const form = document.querySelector('form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }

    async loadStats() {
        try {
            const stats = await apiRequest('/api/stats');
            this.updateStatsUI(stats);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    async loadRecentActivity() {
        try {
            const activities = await apiRequest('/api/recent-activity');
            this.updateActivityUI(activities);
        } catch (error) {
            console.error('Error loading activities:', error);
        }
    }

    async loadChannels() {
        try {
            const channels = await apiRequest('/api/channels');
            console.log('Channels loaded:', channels.length);
        } catch (error) {
            console.error('Error loading channels:', error);
        }
    }

    async loadOffers() {
        try {
            const offers = await apiRequest('/api/offers/incoming');
            console.log('Offers loaded:', offers.length);
        } catch (error) {
            console.error('Error loading offers:', error);
        }
    }

    async loadAnalytics() {
        try {
            const analytics = await apiRequest('/api/analytics');
            console.log('Analytics loaded:', analytics);
        } catch (error) {
            console.error('Error loading analytics:', error);
        }
    }

    updateStatsUI(stats) {
        // Обновляем статистику на главной странице
        const elements = {
            'statsUsers': stats.users,
            'statsChannels': stats.channels,
            'statsOffers': stats.offers,
            'statsPending': stats.pending_responses
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = formatNumber(value);
            }
        });
    }

    updateActivityUI(activities) {
        const activityList = document.getElementById('activityList');
        if (activityList && activities) {
            activityList.innerHTML = activities.map(activity => `
                <div class="activity-item">
                    <span class="activity-icon">${this.getActivityIcon(activity.type)}</span>
                    <span class="activity-text">${activity.description}</span>
                    <span class="activity-time">${formatTime(activity.created_at)}</span>
                </div>
            `).join('');
        }
    }

    getActivityIcon(type) {
        const icons = {
            'channel_added': '📢',
            'offer_created': '💼',
            'response_sent': '📩',
            'payment_received': '💰'
        };
        return icons[type] || '📋';
    }

    showApp() {
        hideLoading();

        // Анимация появления
        const appContainer = document.getElementById('app-container');
        if (appContainer) {
            appContainer.style.display = 'block';
            appContainer.style.opacity = '0';
            appContainer.style.transform = 'translateY(20px)';
            appContainer.style.transition = 'all 0.3s ease-out';

            setTimeout(() => {
                appContainer.style.opacity = '1';
                appContainer.style.transform = 'translateY(0)';
            }, 100);
        }
    }

    showError(message) {
        hideLoading();
        showAlert(message);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// === ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ===
window.handleMainButtonClick = function() {
    if (window.appInstance && window.appInstance.submitCurrentForm) {
        window.appInstance.submitCurrentForm();
    }
};

// === АВТОМАТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ ===
document.addEventListener('DOMContentLoaded', async () => {
    console.log('📄 DOM loaded, starting app initialization...');

    // Создаем глобальный экземпляр приложения
    window.appInstance = new TelegramMiniApp();

    // Инициализируем приложение
    await window.appInstance.init();
});

// Обновляем данные при возвращении на страницу
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.appInstance && window.appInstance.initialized) {
        console.log('👁️ Page became visible, refreshing data...');
        window.appInstance.loadAppData();
    }
});

console.log('⚙️ App initialization module loaded');