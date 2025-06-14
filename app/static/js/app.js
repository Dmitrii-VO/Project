// Основной JavaScript для Telegram Mini App

// Инициализация Telegram WebApp
window.Telegram = window.Telegram || {};
window.Telegram.WebApp = window.Telegram.WebApp || {
    ready: function() { console.log('Telegram WebApp ready'); },
    expand: function() { console.log('Telegram WebApp expand'); },
    close: function() { console.log('Telegram WebApp close'); }
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Telegram Mini App загружен');
    
    // Инициализация Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
    
    // Основная логика приложения
    initializeApp();
});

function initializeApp() {
    console.log('Инициализация приложения...');
    
    // Здесь будет основная логика
    setupEventListeners();
}

function setupEventListeners() {
    // Настройка обработчиков событий
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Кнопка нажата:', e.target.textContent);
        });
    });
}
