// static/js/telegram-webapp.js - Основная логика Telegram WebApp

// === ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP ===
function initTelegramWebApp() {
    console.log('🚀 Initializing Telegram WebApp...');

    // Проверяем доступность Telegram WebApp API
    if (window.Telegram && window.Telegram.WebApp) {
        window.appGlobals.tg = window.Telegram.WebApp;
        window.appGlobals.isInTelegram = true;

        const tg = window.appGlobals.tg;

        // Инициализация приложения
        tg.ready();

        // Расширяем на весь экран
        tg.expand();

        // Включаем закрытие при свайпе вниз
        tg.enableClosingConfirmation();

        console.log('✅ Telegram WebApp initialized');
        console.log('Platform:', tg.platform);
        console.log('Version:', tg.version);
        console.log('Theme:', tg.colorScheme);

        // Применяем тему
        applyTelegramTheme();

        // Настраиваем события
        setupTelegramEvents();

        return true;
    } else {
        console.log('⚠️ Not running in Telegram WebApp');
        window.appGlobals.isInTelegram = false;

        // Для тестирования в браузере
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            setupBrowserMock();
            return true; // Возвращаем true для mock-а
        }

        return false;
    }
}

// === ПРИМЕНЕНИЕ ТЕМЫ TELEGRAM ===
function applyTelegramTheme() {
    if (!window.appGlobals.tg) return;

    const tg = window.appGlobals.tg;
    const colorScheme = tg.colorScheme;
    const themeParams = tg.themeParams;

    console.log('🎨 Applying Telegram theme:', colorScheme);

    const root = document.documentElement;

    if (colorScheme === 'dark') {
        // Темная тема
        root.style.setProperty('--bg-primary', themeParams.bg_color || '#1a1a1a');
        root.style.setProperty('--bg-secondary', themeParams.secondary_bg_color || '#2d2d2d');
        root.style.setProperty('--text-primary', themeParams.text_color || '#ffffff');
        root.style.setProperty('--text-secondary', themeParams.hint_color || '#a0a0a0');
        root.style.setProperty('--border-color', '#404040');

        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
    } else {
        // Светлая тема
        root.style.setProperty('--bg-primary', themeParams.bg_color || '#ffffff');
        root.style.setProperty('--bg-secondary', themeParams.secondary_bg_color || '#f7fafc');
        root.style.setProperty('--text-primary', themeParams.text_color || '#2d3748');
        root.style.setProperty('--text-secondary', themeParams.hint_color || '#718096');
        root.style.setProperty('--border-color', '#e2e8f0');

        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
    }

    // Устанавливаем цвета Telegram
    if (themeParams.header_bg_color) {
        tg.setHeaderColor(themeParams.header_bg_color);
    }

    if (themeParams.bg_color) {
        tg.setBackgroundColor(themeParams.bg_color);
    }
}

// === СОБЫТИЯ TELEGRAM ===
function setupTelegramEvents() {
    if (!window.appGlobals.tg) return;

    const tg = window.appGlobals.tg;

    // Изменение темы
    tg.onEvent('themeChanged', () => {
        console.log('🎨 Theme changed');
        applyTelegramTheme();
    });

    // Изменение viewport
    tg.onEvent('viewportChanged', (eventData) => {
        console.log('📱 Viewport changed:', eventData);
        handleViewportChange(eventData);
    });

    // Главная кнопка
    tg.onEvent('mainButtonClicked', () => {
        console.log('🔵 Main button clicked');
        handleMainButtonClick();
    });

    // Кнопка "Назад"
    tg.onEvent('backButtonClicked', () => {
        console.log('⬅️ Back button clicked');
        handleBackButtonClick();
    });

    console.log('📡 Telegram events configured');
}

// === ПОЛУЧЕНИЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ ===
async function getTelegramUser() {
    if (!window.appGlobals.tg) {
        console.log('⚠️ Telegram WebApp not available');
        return null;
    }

    const tg = window.appGlobals.tg;

    // Способ 1: Из initDataUnsafe (для разработки)
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        console.log('👤 User from initDataUnsafe:', user);

        window.appGlobals.user = {
            id: user.id,
            first_name: user.first_name,
            last_name: user.last_name || '',
            username: user.username || '',
            language_code: user.language_code || 'ru',
            is_premium: user.is_premium || false
        };

        return window.appGlobals.user;
    }

    // Способ 2: Верификация через сервер (для продакшена)
    if (tg.initData) {
        try {
            const userData = await apiRequest('/api/telegram/verify', {
                method: 'POST',
                headers: {
                    'X-Telegram-Init-Data': tg.initData
                }
            });

            window.appGlobals.user = userData.user;
            return userData.user;
        } catch (error) {
            console.error('❌ User verification failed:', error);
        }
    }

    console.log('⚠️ No user data available');
    return null;
}

// === ОБРАБОТЧИКИ СОБЫТИЙ ===
function handleViewportChange(eventData) {
    if (eventData.isStateStable) {
        const viewportHeight = window.appGlobals.tg.viewportHeight;
        const viewportStableHeight = window.appGlobals.tg.viewportStableHeight;

        // Проверяем, открыта ли клавиатура
        const keyboardOpen = viewportHeight < viewportStableHeight;

        if (keyboardOpen) {
            document.body.classList.add('keyboard-open');
        } else {
            document.body.classList.remove('keyboard-open');
        }
    }
}

function handleMainButtonClick() {
    // Переопределяется в каждой странице
    console.log('Main button clicked - no handler defined');

    // Пытаемся найти и выполнить глобальный обработчик
    if (window.handleMainButtonClick && typeof window.handleMainButtonClick === 'function') {
        window.handleMainButtonClick();
    }
}

function handleBackButtonClick() {
    // Простая навигация назад
    if (window.history.length > 1) {
        window.history.back();
    } else if (window.appGlobals.tg) {
        window.appGlobals.tg.close();
    }
}

// === MOCK ДЛЯ БРАУЗЕРА ===
function setupBrowserMock() {
    console.log('🔧 Setting up browser mock for development');

    window.Telegram = {
        WebApp: {
            initDataUnsafe: {
                user: {
                    id: 373086959,
                    first_name: 'Test User',
                    last_name: 'Developer',
                    username: 'testuser',
                    language_code: 'ru',
                    is_premium: false
                }
            },
            initData: '',
            platform: 'web',
            version: '6.0',
            colorScheme: 'light',
            themeParams: {
                bg_color: '#ffffff',
                text_color: '#000000',
                header_bg_color: '#667eea',
                secondary_bg_color: '#f7fafc',
                hint_color: '#718096'
            },
            viewportHeight: window.innerHeight,
            viewportStableHeight: window.innerHeight,
            ready: () => console.log('Mock: ready'),
            expand: () => console.log('Mock: expand'),
            close: () => console.log('Mock: close'),
            enableClosingConfirmation: () => console.log('Mock: enableClosingConfirmation'),
            setHeaderColor: (color) => console.log('Mock: setHeaderColor', color),
            setBackgroundColor: (color) => console.log('Mock: setBackgroundColor', color),
            showAlert: (message, callback) => {
                alert(message);
                if (callback) callback();
            },
            showConfirm: (message, callback) => {
                const result = confirm(message);
                callback(result);
            },
            onEvent: (event, callback) => {
                console.log('Mock: onEvent', event);

                // Эмулируем некоторые события для тестирования
                if (event === 'themeChanged') {
                    window.mockThemeCallback = callback;
                } else if (event === 'viewportChanged') {
                    window.mockViewportCallback = callback;
                } else if (event === 'mainButtonClicked') {
                    window.mockMainButtonCallback = callback;
                } else if (event === 'backButtonClicked') {
                    window.mockBackButtonCallback = callback;
                }
            },
            MainButton: {
                text: 'Готово',
                isVisible: false,
                setText: function(text) {
                    console.log('Mock MainButton setText:', text);
                    this.text = text;
                },
                show: function() {
                    console.log('Mock MainButton show');
                    this.isVisible = true;
                },
                hide: function() {
                    console.log('Mock MainButton hide');
                    this.isVisible = false;
                },
                onClick: function(callback) {
                    console.log('Mock MainButton onClick set');
                    this.callback = callback;
                },
                click: function() {
                    if (this.callback) this.callback();
                }
            },
            BackButton: {
                isVisible: false,
                show: function() {
                    console.log('Mock BackButton show');
                    this.isVisible = true;
                },
                hide: function() {
                    console.log('Mock BackButton hide');
                    this.isVisible = false;
                },
                onClick: function(callback) {
                    console.log('Mock BackButton onClick set');
                    this.callback = callback;
                },
                click: function() {
                    if (this.callback) this.callback();
                }
            },
            HapticFeedback: {
                impactOccurred: (style) => console.log('Mock haptic impact:', style),
                notificationOccurred: (type) => console.log('Mock notification haptic:', type)
            }
        }
    };

    // Устанавливаем глобальные переменные для mock
    window.appGlobals.tg = window.Telegram.WebApp;
    window.appGlobals.isInTelegram = true; // Для тестирования считаем что в Telegram

    console.log('✅ Browser mock setup complete');
}

// === УТИЛИТЫ ДЛЯ РАЗРАБОТКИ ===
function testTelegramFunctions() {
    console.log('🧪 Testing Telegram functions...');

    if (window.appGlobals.tg) {
        // Тест главной кнопки
        window.appGlobals.tg.MainButton.setText('Тест');
        window.appGlobals.tg.MainButton.show();

        // Тест haptic feedback
        if (window.appGlobals.tg.HapticFeedback) {
            window.appGlobals.tg.HapticFeedback.impactOccurred('light');
        }

        console.log('✅ Test complete');
    } else {
        console.log('❌ Telegram WebApp not available for testing');
    }
}

// Экспортируем функции для глобального использования
window.initTelegramWebApp = initTelegramWebApp;
window.getTelegramUser = getTelegramUser;
window.applyTelegramTheme = applyTelegramTheme;
window.setupTelegramEvents = setupTelegramEvents;
window.testTelegramFunctions = testTelegramFunctions;

console.log('📱 Telegram WebApp module loaded');