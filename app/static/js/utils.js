// УТИЛИТЫ ДЛЯ TELEGRAM MINI APP

// Утилиты для API запросов
const API = {
    // Базовый запрос
    async request(url, options = {}) {
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
            console.error('API Error:', error);
            throw error;
        }
    },

    // GET запрос
    get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },

    // POST запрос
    post(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // PUT запрос
    put(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // DELETE запрос
    delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
};

// Утилиты для UI
const UI = {
    // Показать уведомление
    showNotification(message, type = 'info') {
        if (window.TelegramApp) {
            window.TelegramApp.showAlert(message);
        } else {
            alert(message);
        }
    },

    // Показать лоадер
    showLoader(element) {
        if (element) {
            element.innerHTML = '<div class="loading-spinner"></div>';
        }
    },

    // Скрыть лоадер
    hideLoader(element, content = '') {
        if (element) {
            element.innerHTML = content;
        }
    },

    // Форматирование чисел
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },

    // Форматирование валюты
    formatCurrency(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB'
        }).format(amount);
    },

    // Дебаунс функция
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Троттлинг функция
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Утилиты для локального хранения (замена localStorage для Telegram)
const Storage = {
    data: new Map(),

    set(key, value) {
        this.data.set(key, JSON.stringify(value));
    },

    get(key) {
        const value = this.data.get(key);
        return value ? JSON.parse(value) : null;
    },

    remove(key) {
        this.data.delete(key);
    },

    clear() {
        this.data.clear();
    }
};

// Утилиты для валидации форм
const Validation = {
    // Проверка email
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    // Проверка URL
    isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    },

    // Проверка Telegram username
    isValidTelegramUsername(username) {
        const re = /^[a-zA-Z0-9_]{5,32}$/;
        return re.test(username.replace('@', ''));
    },

    // Проверка на пустоту
    isEmpty(value) {
        return !value || value.trim() === '';
    },

    // Проверка минимальной длины
    minLength(value, min) {
        return value && value.length >= min;
    },

    // Проверка максимальной длины
    maxLength(value, max) {
        return value && value.length <= max;
    },

    // Проверка числа
    isNumber(value) {
        return !isNaN(value) && !isNaN(parseFloat(value));
    },

    // Проверка положительного числа
    isPositiveNumber(value) {
        return this.isNumber(value) && parseFloat(value) > 0;
    }
};

// Утилиты для работы с DOM
const DOM = {
    // Найти элемент
    $(selector) {
        return document.querySelector(selector);
    },

    // Найти все элементы
    $(selector) {
        return document.querySelectorAll(selector);
    },

    // Добавить класс
    addClass(element, className) {
        if (element) element.classList.add(className);
    },

    // Удалить класс
    removeClass(element, className) {
        if (element) element.classList.remove(className);
    },

    // Переключить класс
    toggleClass(element, className) {
        if (element) element.classList.toggle(className);
    },

    // Проверить наличие класса
    hasClass(element, className) {
        return element ? element.classList.contains(className) : false;
    },

    // Создать элемент
    createElement(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            element.setAttribute(key, value);
        });

        if (content) {
            element.innerHTML = content;
        }

        return element;
    },

    // Удалить элемент
    removeElement(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }
};

// Глобальный экспорт утилит
window.API = API;
window.UI = UI;
window.Storage = Storage;
window.Validation = Validation;
window.DOM = DOM;