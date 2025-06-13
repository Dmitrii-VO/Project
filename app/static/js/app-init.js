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
        if (!activityList) return;

        if (!activities || activities.length === 0) {
            activityList.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                    <span style="font-size: 48px; display: block; margin-bottom: 16px; opacity: 0.6;">📭</span>
                    <div>Пока нет активности</div>
                </div>
            `;
            return;
        }

        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    ${this.getActivityIcon(activity.type)}
                </div>
                <div class="activity-content">
                    <div class="activity-text">${activity.text}</div>
                    <div class="activity-time">${formatTime(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');
    }

    getActivityIcon(type) {
        const icons = {
            'offer': '🎯',
            'channel': '📺',
            'payment': '💰',
            'response': '📨'
        };
        return icons[type] || '📋';
    }

    setupUI() {
        // Настройка кнопок Telegram
        this.setupTelegramButtons();

        // Настройка обработчиков форм
        this.setupFormHandlers();

        // Настройка навигации
        this.setupNavigation();
    }

    setupTelegramButtons() {
        if (!window.appGlobals.tg) return;

        const tg = window.appGlobals.tg;
        const path = window.location.pathname;

        // Настройка главной кнопки в зависимости от страницы
        if (path === '/' || path === '/index') {
            // На главной - кнопка создания оффера
            tg.MainButton.setText('Создать оффер');
            tg.MainButton.onClick(() => navigateTo('/create-offer'));
            tg.MainButton.show();
        } else if (path.includes('create-offer')) {
            // На странице создания - кнопка отправки формы
            tg.MainButton.setText('Создать оффер');
            tg.MainButton.onClick(() => this.submitCurrentForm());
            tg.MainButton.show();
        } else {
            // На других страницах скрываем главную кнопку
            tg.MainButton.hide();
        }

        // Показываем кнопку "Назад" если не на главной
        if (path !== '/' && path !== '/index') {
            tg.BackButton.show();
        } else {
            tg.BackButton.hide();
        }
    }

    setupFormHandlers() {
        // Настройка всех форм на странице
        const forms = document.querySelectorAll('form');

        forms.forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleFormSubmit(form);
            });
        });
    }

    setupNavigation() {
        // Настройка всех ссылок для навигации
        const navLinks = document.querySelectorAll('a[href^="/"], button[onclick*="navigateTo"]');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Haptic feedback при навигации
                if (window.appGlobals.tg && window.appGlobals.tg.HapticFeedback) {
                    window.appGlobals.tg.HapticFeedback.impactOccurred('light');
                }
            });
        });
    }

    async handleFormSubmit(form) {
        const formData = new FormData(form);
        const url = form.action || '/api/default';
        const method = form.method || 'POST';

        try {
            showLoading();

            const response = await apiRequest(url, {
                method: method.toUpperCase(),
                body: JSON.stringify(Object.fromEntries(formData))
            });

            hideLoading();

            if (response.status === 'success') {
                showAlert(response.message || 'Успешно сохранено!');

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

    submitCurrentForm() {
        const form = document.querySelector('form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }

    showApp() {
        hideLoading();

        // Анимация появления
        const appContainer = document.getElementById('app-container');
        if (appContainer) {
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