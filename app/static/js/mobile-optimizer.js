/**
 * Mobile Optimizer для Telegram Mini App
 * Оптимизации для мобильных устройств и WebApp
 */

class MobileOptimizer {
    constructor() {
        this.isMobile = this.detectMobile();
        this.isTelegram = this.detectTelegram();
        this.cache = new Map();
        this.requestQueue = [];
        this.isOnline = navigator.onLine;
        
        this.init();
        console.log('📱 Mobile Optimizer инициализирован', {
            isMobile: this.isMobile,
            isTelegram: this.isTelegram,
            isOnline: this.isOnline
        });
    }
    
    init() {
        // Настройка событий
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processOfflineQueue();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
        
        // Оптимизация для мобильных устройств
        if (this.isMobile) {
            this.optimizeForMobile();
        }
        
        // Настройки для Telegram WebApp
        if (this.isTelegram) {
            this.setupTelegramOptimizations();
        }
    }
    
    detectMobile() {
        const userAgent = navigator.userAgent.toLowerCase();
        const mobileKeywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet'];
        return mobileKeywords.some(keyword => userAgent.includes(keyword)) || 
               window.innerWidth <= 768;
    }
    
    detectTelegram() {
        return window.Telegram && window.Telegram.WebApp;
    }
    
    optimizeForMobile() {
        // Уменьшаем количество одновременных запросов
        this.maxConcurrentRequests = 2;
        
        // Увеличиваем время кеширования
        this.cacheTimeout = 10 * 60 * 1000; // 10 минут
        
        // Включаем агрессивное кеширование
        this.enableAggressiveCaching = true;
        
        // Оптимизация прокрутки
        this.optimizeScrolling();
        
        // Оптимизация изображений
        this.optimizeImages();
        
        console.log('📱 Мобильные оптимизации применены');
    }
    
    setupTelegramOptimizations() {
        const tg = window.Telegram.WebApp;
        
        // Расширяем WebApp на весь экран
        tg.expand();
        
        // Настраиваем тему
        this.setupTelegramTheme(tg);
        
        // Настраиваем кнопки
        this.setupTelegramButtons(tg);
        
        // Включаем haptic feedback
        this.enableHapticFeedback = true;
        
        console.log('📱 Telegram WebApp оптимизации применены');
    }
    
    setupTelegramTheme(tg) {
        // Применяем цвета темы Telegram
        const root = document.documentElement;
        
        if (tg.themeParams) {
            root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
            root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
            root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#708499');
            root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#5288c1');
            root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#5288c1');
            root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
        }
    }
    
    setupTelegramButtons(tg) {
        // Кнопка "Назад"
        tg.BackButton.onClick(() => {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                tg.close();
            }
        });
        
        // Главная кнопка (если нужна)
        tg.MainButton.setText('Действие');
        tg.MainButton.hide(); // Скрываем по умолчанию
        
        // Настройки кнопки
        tg.MainButton.onClick(() => {
            this.triggerHapticFeedback('impact', 'medium');
        });
    }
    
    optimizeScrolling() {
        // Плавная прокрутка
        document.documentElement.style.scrollBehavior = 'smooth';
        
        // Предотвращение bounce эффекта на iOS
        document.body.style.overscrollBehavior = 'none';
        
        // Оптимизация прокрутки для мобильных
        let ticking = false;
        
        const optimizeScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    // Здесь можем добавить логику для ленивой загрузки
                    this.handleLazyLoading();
                    ticking = false;
                });
                ticking = true;
            }
        };
        
        window.addEventListener('scroll', optimizeScroll, { passive: true });
    }
    
    optimizeImages() {
        // Ленивая загрузка изображений
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback для старых браузеров
            images.forEach(img => {
                img.src = img.dataset.src;
                img.classList.remove('lazy');
            });
        }
    }
    
    handleLazyLoading() {
        // Логика для ленивой загрузки контента
        const lazyElements = document.querySelectorAll('.lazy-load:not(.loaded)');
        
        lazyElements.forEach(element => {
            const rect = element.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // Загружаем контент, когда элемент появляется в области видимости
            if (rect.top < windowHeight + 200) { // 200px буфер
                this.loadLazyContent(element);
            }
        });
    }
    
    loadLazyContent(element) {
        element.classList.add('loaded');
        
        // Можем загрузить дополнительные данные здесь
        const dataUrl = element.dataset.url;
        if (dataUrl) {
            this.optimizedFetch(dataUrl)
                .then(data => {
                    // Обрабатываем загруженные данные
                    this.renderLazyContent(element, data);
                })
                .catch(error => {
                    console.warn('Ошибка ленивой загрузки:', error);
                });
        }
    }
    
    renderLazyContent(element, data) {
        // Рендеринг контента для ленивой загрузки
        if (data && data.success) {
            const content = data.content || '';
            element.innerHTML = content;
            element.classList.add('content-loaded');
        }
    }
    
    // ===== ОПТИМИЗИРОВАННЫЕ ЗАПРОСЫ =====
    
    async optimizedFetch(url, options = {}) {
        // Проверяем кеш
        const cacheKey = this.generateCacheKey(url, options);
        const cachedData = this.getFromCache(cacheKey);
        
        if (cachedData) {
            console.log('📦 Данные из кеша:', url);
            return cachedData;
        }
        
        // Если офлайн, добавляем в очередь
        if (!this.isOnline) {
            return new Promise((resolve, reject) => {
                this.requestQueue.push({ url, options, resolve, reject });
            });
        }
        
        try {
            // Добавляем мобильные заголовки
            const mobileOptions = this.addMobileHeaders(options);
            
            // Выполняем запрос
            const response = await fetch(url, mobileOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Кешируем успешный ответ
            this.saveToCache(cacheKey, data);
            
            return data;
            
        } catch (error) {
            console.error('Ошибка optimizedFetch:', error);
            
            // Пытаемся вернуть старые данные из кеша
            const staleData = this.getFromCache(cacheKey, true);
            if (staleData) {
                console.log('📦 Возвращаем устаревшие данные из кеша');
                return staleData;
            }
            
            throw error;
        }
    }
    
    addMobileHeaders(options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'X-Mobile-Request': 'true',
            ...options.headers
        };
        
        // Добавляем информацию об устройстве
        if (this.isMobile) {
            headers['X-Device-Type'] = 'mobile';
        }
        
        if (this.isTelegram) {
            headers['X-Telegram-WebApp'] = 'true';
            headers['X-Telegram-Web-App-Data'] = window.Telegram.WebApp.initData || '';
        }
        
        // Добавляем информацию о сети
        if (navigator.connection) {
            headers['X-Network-Type'] = navigator.connection.effectiveType || 'unknown';
        }
        
        return {
            ...options,
            headers
        };
    }
    
    generateCacheKey(url, options) {
        const keyData = {
            url: url,
            method: options.method || 'GET',
            body: options.body || null
        };
        
        return btoa(JSON.stringify(keyData)).substring(0, 32);
    }
    
    getFromCache(key, allowStale = false) {
        const item = this.cache.get(key);
        
        if (!item) {
            return null;
        }
        
        const now = Date.now();
        const age = now - item.timestamp;
        
        // Проверяем срок годности
        if (!allowStale && age > this.cacheTimeout) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }
    
    saveToCache(key, data) {
        // Ограничиваем размер кеша
        if (this.cache.size > 100) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
    }
    
    clearCache() {
        this.cache.clear();
        console.log('🗑️ Кеш очищен');
    }
    
    processOfflineQueue() {
        console.log('🌐 Обрабатываем офлайн очередь:', this.requestQueue.length);
        
        while (this.requestQueue.length > 0) {
            const request = this.requestQueue.shift();
            
            this.optimizedFetch(request.url, request.options)
                .then(request.resolve)
                .catch(request.reject);
        }
    }
    
    // ===== УТИЛИТЫ =====
    
    triggerHapticFeedback(type = 'impact', style = 'medium') {
        if (this.enableHapticFeedback && this.isTelegram) {
            try {
                window.Telegram.WebApp.HapticFeedback.impactOccurred(style);
            } catch (error) {
                console.warn('Haptic feedback недоступен:', error);
            }
        }
    }
    
    showAlert(message, callback) {
        if (this.isTelegram) {
            window.Telegram.WebApp.showAlert(message, callback);
        } else {
            alert(message);
            if (callback) callback();
        }
    }
    
    showConfirm(message, callback) {
        if (this.isTelegram) {
            window.Telegram.WebApp.showConfirm(message, callback);
        } else {
            const result = confirm(message);
            if (callback) callback(result);
        }
    }
    
    openTelegramLink(url) {
        if (this.isTelegram) {
            window.Telegram.WebApp.openTelegramLink(url);
        } else {
            window.open(url, '_blank');
        }
    }
    
    openLink(url) {
        if (this.isTelegram) {
            window.Telegram.WebApp.openLink(url);
        } else {
            window.open(url, '_blank');
        }
    }
    
    getViewportSize() {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            isMobile: this.isMobile
        };
    }
    
    // ===== ПРОИЗВОДИТЕЛЬНОСТЬ =====
    
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
    }
    
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
    
    // ===== СТАТИСТИКА =====
    
    getPerformanceMetrics() {
        const metrics = {
            cacheSize: this.cache.size,
            queueSize: this.requestQueue.length,
            isOnline: this.isOnline,
            isMobile: this.isMobile,
            isTelegram: this.isTelegram
        };
        
        // Добавляем метрики производительности браузера
        if (performance && performance.memory) {
            metrics.memory = {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
            };
        }
        
        return metrics;
    }
}

// ===== ГЛОБАЛЬНЫЕ ФУНКЦИИ =====

window.createMobileOptimizer = () => {
    if (!window.mobileOptimizer) {
        window.mobileOptimizer = new MobileOptimizer();
    }
    return window.mobileOptimizer;
};

// Автоматическая инициализация
document.addEventListener('DOMContentLoaded', () => {
    window.createMobileOptimizer();
});

// Экспорт для модулей
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileOptimizer;
}