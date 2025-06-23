// TELEGRAM MINI APP - ОПТИМИЗИРОВАННЫЙ КЛАСС
class TelegramApp {
    constructor() {
        this.isReady = false;
        this.user = null;
        this.tg = window.Telegram?.WebApp;
    }

    // Инициализация приложения
    async init() {
        console.log('🚀 Инициализация Telegram Mini App...');

        try {
            // Инициализация Telegram WebApp
            this.initTelegramWebApp();

            // Применение темы
            this.applyTheme();

            // Настройка обработчиков
            this.setupEventListeners();

            // Скрытие экрана загрузки
            this.hideLoadingScreen();

            this.isReady = true;
            console.log('✅ Приложение готово');

        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
            this.hideLoadingScreen(); // Показать контент даже при ошибке
        }
    }

    // Инициализация Telegram WebApp
    initTelegramWebApp() {
        if (this.tg) {
            this.tg.ready();
            this.tg.expand();
            this.user = this.tg.initDataUnsafe?.user;
            console.log('👤 Telegram пользователь:', this.user);
        } else {
            console.log('⚠️ Telegram WebApp недоступен - демо режим');
        }
    }

    // Применение темы Telegram
    applyTheme() {
        if (!this.tg?.themeParams) return;

        const root = document.documentElement;
        const theme = this.tg.themeParams;

        // Применяем цвета темы
        Object.entries({
            '--tg-theme-bg-color': theme.bg_color,
            '--tg-theme-text-color': theme.text_color,
            '--tg-theme-button-color': theme.button_color,
            '--tg-theme-button-text-color': theme.button_text_color,
        }).forEach(([property, value]) => {
            if (value) root.style.setProperty(property, value);
        });
    }

    // Настройка обработчиков событий
    setupEventListeners() {
        // Обработчик кнопок
        document.addEventListener('click', this.handleClick.bind(this));

        // Обработчик форм
        document.addEventListener('submit', this.handleSubmit.bind(this));

        // Обработчик изменения размера
        window.addEventListener('resize', this.handleResize.bind(this));

        // Обработчик ошибок
        window.addEventListener('error', this.handleError.bind(this));
    }

    // Обработчик кликов
    handleClick(event) {
        const button = event.target.closest('button, .btn');
        if (!button) return;

        // Haptic feedback для Telegram
        if (this.tg?.HapticFeedback) {
            this.tg.HapticFeedback.impactOccurred('light');
        }
    }

    // Обработчик отправки форм
    handleSubmit(event) {
        // Базовая обработка - можно расширить
        console.log('📤 Отправка формы:', event.target);
    }

    // Обработчик изменения размера
    handleResize() {
        // Адаптация для мобильных устройств
        const isMobile = window.innerWidth <= 768;
        document.body.classList.toggle('mobile', isMobile);
    }

    // Обработчик ошибок
    handleError(event) {
        console.error('❌ Ошибка приложения:', event.error);
        // Показать контент даже при ошибках
        this.hideLoadingScreen();
    }

    // Скрытие экрана загрузки
    hideLoadingScreen() {
        setTimeout(() => {
            const loadingScreen = document.getElementById('loading-screen');
            const appContainer = document.getElementById('app-container');

            if (loadingScreen) loadingScreen.classList.add('hidden');
            if (appContainer) appContainer.classList.add('visible');
        }, 1000);
    }

    // Утилиты для взаимодействия с Telegram
    showAlert(message) {
        if (this.tg?.showAlert) {
            this.tg.showAlert(message);
        } else {
            alert(message);
        }
    }

    close() {
        if (this.tg?.close) {
            this.tg.close();
        } else {
            console.log('Закрытие приложения...');
        }
    }

    // Навигация
    goBack() {
        if (this.tg?.BackButton) {
            this.tg.BackButton.onClick(() => window.history.back());
        } else {
            window.history.back();
        }
    }
}

// Создание глобального экземпляра
window.TelegramApp = new TelegramApp();

// Глобальные функции для совместимости
window.showAlert = (message) => window.TelegramApp.showAlert(message);
window.closeApp = () => window.TelegramApp.close();
window.goBack = () => window.TelegramApp.goBack();