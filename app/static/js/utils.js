// static/js/utils.js - Вспомогательные функции

// === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
window.appGlobals = {
    tg: null,
    user: null,
    isInTelegram: false,
    initialized: false
};

// === УТИЛИТЫ API ===
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };

    const config = { ...defaultOptions, ...options };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}

// === УТИЛИТЫ UI ===
function showLoading() {
    const loadingScreen = document.getElementById('loading-screen');
    if (loadingScreen) {
        loadingScreen.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingScreen = document.getElementById('loading-screen');
    const appContainer = document.getElementById('app-container');

    if (loadingScreen) {
        loadingScreen.style.display = 'none';
    }
    if (appContainer) {
        appContainer.style.display = 'block';
    }
}

function showAlert(message, type = 'info') {
    if (window.appGlobals.isInTelegram && window.appGlobals.tg) {
        window.appGlobals.tg.showAlert(message);
    } else {
        alert(message);
    }
}

function showConfirm(message, callback) {
    if (window.appGlobals.isInTelegram && window.appGlobals.tg) {
        window.appGlobals.tg.showConfirm(message, callback);
    } else {
        const result = confirm(message);
        callback(result);
    }
}

// === НАВИГАЦИЯ ===
function navigateTo(url) {
    try {
        if (window.appGlobals.isInTelegram && window.appGlobals.tg) {
            // В Telegram просто меняем URL
            window.location.href = url;
        } else {
            // В браузере обычная навигация
            window.location.href = url;
        }
    } catch (error) {
        console.error('Navigation error:', error);
        window.location.href = url;
    }
}

// === ФОРМАТИРОВАНИЕ ===
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

function formatCurrency(amount) {
    return `₽${formatNumber(amount)}`;
}

function formatTime(timestamp) {
    if (!timestamp) return 'Недавно';

    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Только что';
        if (minutes < 60) return `${minutes} мин назад`;
        if (hours < 24) return `${hours} ч назад`;
        if (days < 7) return `${days} дн назад`;

        return date.toLocaleDateString('ru-RU');
    } catch (error) {
        return 'Недавно';
    }
}

console.log('✅ Utils loaded');