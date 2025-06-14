// app/static/js/app.js - Основной JavaScript для Telegram Mini App

class TelegramMiniApp {
    constructor() {
        this.isInitialized = false;
        this.user = null;
        this.apiBase = '/api';
        this.cache = new Map();
    }

    async init() {
        console.log('🚀 Инициализация Telegram Mini App...');

        try {
            // Проверка Telegram WebApp API
            if (window.Telegram && window.Telegram.WebApp) {
                const tg = window.Telegram.WebApp;
                tg.ready();
                tg.expand();

                this.user = tg.initDataUnsafe.user;
                console.log('👤 Telegram пользователь:', this.user);

                // Применение темы
                this.applyTelegramTheme(tg.themeParams);
            } else {
                console.log('⚠️ Telegram WebApp API недоступен - демо режим');
            }

            // Инициализация компонентов
            this.initializeComponents();
            this.setupEventListeners();

            this.isInitialized = true;
            console.log('✅ Приложение инициализировано');

        } catch (error) {
            console.error('❌ Ошибка инициализации:', error);
        }
    }

    applyTelegramTheme(themeParams) {
        if (!themeParams) return;

        const root = document.documentElement;

        // Применяем цвета темы
        if (themeParams.bg_color) {
            root.style.setProperty('--tg-theme-bg-color', themeParams.bg_color);
        }
        if (themeParams.text_color) {
            root.style.setProperty('--tg-theme-text-color', themeParams.text_color);
        }
        if (themeParams.button_color) {
            root.style.setProperty('--tg-theme-button-color', themeParams.button_color);
        }
        if (themeParams.button_text_color) {
            root.style.setProperty('--tg-theme-button-text-color', themeParams.button_text_color);
        }
    }

    initializeComponents() {
        // Инициализация компонентов страницы
        this.initButtons();
        this.initForms();
        this.initCards();
    }

    initButtons() {
        // Настройка всех кнопок
        document.querySelectorAll('button, .btn').forEach(button => {
            button.addEventListener('click', this.handleButtonClick.bind(this));
        });
    }

    initForms() {
        // Настройка форм
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });
    }

    initCards() {
        // Настройка интерактивных карточек
        document.querySelectorAll('.nav-card, .stat-card').forEach(card => {
            card.addEventListener('click', this.handleCardClick.bind(this));
        });
    }

    setupEventListeners() {
        // Глобальные обработчики событий
        window.addEventListener('app:ready', this.onAppReady.bind(this));
        window.addEventListener('resize', this.onResize.bind(this));

        // Обработка ошибок
        window.addEventListener('error', this.onError.bind(this));
    }

    handleButtonClick(event) {
        const button = event.target.closest('button, .btn');
        if (!button) return;

        // Анимация нажатия
        button.style.transform = 'scale(0.95)';
        setTimeout(() => {
            button.style.transform = '';
        }, 150);

        // Haptic feedback для Telegram
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }
    }

    handleFormSubmit(event) {
        event.preventDefault();
        const form = event.target;
        console.log('📝 Отправка формы:', form.id || 'unnamed');

        // Здесь будет логика отправки форм
        this.showAlert('Форма отправлена!');
    }

    handleCardClick(event) {
        const card = event.target.closest('.nav-card, .stat-card');
        if (!card) return;

        // Анимация карточки
        card.style.transform = 'scale(0.98)';
        setTimeout(() => {
            card.style.transform = '';
        }, 200);
    }

    onAppReady() {
        console.log('🎉 Приложение готово');
        // Дополнительная инициализация после готовности
    }

    onResize() {
        console.log('📱 Изменение размера экрана');
        // Адаптация интерфейса
    }

    onError(event) {
        console.error('❌ Ошибка приложения:', event.error);
        // Обработка ошибок
    }

    // API методы
    async apiCall(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    async loadStats() {
        try {
            const endpoints = {
                'channels-count': '/stats/channels',
                'offers-count': '/stats/offers',
                'revenue-amount': '/stats/revenue',
                'users-count': '/stats/users'
            };

            for (const [elementId, endpoint] of Object.entries(endpoints)) {
                const element = document.getElementById(elementId);
                if (!element) continue;

                try {
                    const data = await this.apiCall(endpoint);
                    this.animateCounter(element, data.count || data.value || 0);
                } catch (error) {
                    // Демо данные при ошибке API
                    const demoData = {
                        'channels-count': 73,
                        'offers-count': 156,
                        'revenue-amount': '387K ₽',
                        'users-count': 841
                    };
                    this.animateCounter(element, demoData[elementId]);
                }
            }
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
        }
    }

    animateCounter(element, finalValue) {
        const isNumber = typeof finalValue === 'number';
        const duration = 1500;
        const steps = 60;

        if (isNumber && finalValue > 0) {
            let currentValue = 0;
            const increment = finalValue / steps;
            const stepDuration = duration / steps;

            const interval = setInterval(() => {
                currentValue += increment;
                if (currentValue >= finalValue) {
                    element.textContent = Math.floor(finalValue).toLocaleString();
                    clearInterval(interval);
                } else {
                    element.textContent = Math.floor(currentValue).toLocaleString();
                }
            }, stepDuration);
        } else {
            // Для строковых значений
            setTimeout(() => {
                element.textContent = finalValue;
            }, Math.random() * 1000 + 500);
        }
    }

    // Утилиты
    showAlert(message) {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.showAlert(message);
        } else {
            alert(message);
        }
    }

    showConfirm(message, callback) {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.showConfirm(message, callback);
        } else {
            const result = confirm(message);
            callback(result);
        }
    }

    vibrate() {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
        } else if (navigator.vibrate) {
            navigator.vibrate(50);
        }
    }

    setLoading(elementId, isLoading = true) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (isLoading) {
            element.innerHTML = '<span class="loading">Загрузка...</span>';
        }
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatCurrency(amount, currency = 'RUB') {
        const symbols = {
            'RUB': '₽',
            'USD': '$',
            'EUR': '€'
        };

        return `${this.formatNumber(amount)} ${symbols[currency] || currency}`;
    }
}

// Глобальные функции для использования в HTML
window.createOffer = function() {
    console.log('🎯 Создание оффера...');
    app.showAlert('Переход к созданию оффера...');
    setTimeout(() => {
        window.location.href = '/offers';
    }, 500);
};

window.addChannel = function() {
    console.log('📺 Добавление канала...');
    app.showAlert('Переход к добавлению канала...');
    setTimeout(() => {
        window.location.href = '/channels-enhanced';
    }, 500);
};

window.viewStats = function() {
    console.log('📊 Просмотр статистики...');
    app.showAlert('Переход к аналитике...');
    setTimeout(() => {
        window.location.href = '/analytics';
    }, 500);
};

// Инициализация приложения
const app = new TelegramMiniApp();

// Запуск при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 DOM загружен, запуск приложения...');
    app.init();

    // Загрузка статистики для главной страницы
    if (document.getElementById('channels-count')) {
        setTimeout(() => {
            app.loadStats();
        }, 1000);
    }
});

// Экспорт для использования в других модулях
window.TelegramMiniApp = TelegramMiniApp;
window.app = app;