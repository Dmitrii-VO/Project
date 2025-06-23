// DASHBOARD LOGIC - ОПТИМИЗИРОВАННЫЙ
class Dashboard {
    constructor() {
        this.isLoading = false;
        this.statsCache = null;
        this.updateInterval = null;
    }

    // Инициализация dashboard
    async init() {
        console.log('📊 Инициализация Dashboard...');

        try {
            await this.loadStats();
            this.startAutoUpdate();
        } catch (error) {
            console.error('❌ Ошибка инициализации Dashboard:', error);
            this.showFallbackData();
        }
    }

    // Загрузка статистики
    async loadStats() {
        if (this.isLoading) return;

        this.isLoading = true;

        try {
            // Загрузка данных с API
            const data = await API.get('/api/stats/global');

            if (data && data.success) {
                this.statsCache = data.stats;
                this.updateStatsDisplay(data.stats);
            } else {
                throw new Error('Неверный формат ответа API');
            }

        } catch (error) {
            console.error('❌ Ошибка загрузки статистики:', error);
            this.showFallbackData();
        } finally {
            this.isLoading = false;
        }
    }

    // Обновление отображения статистики
    updateStatsDisplay(stats) {
        const updates = [
            { id: 'channels-count', value: stats.channels || 0 },
            { id: 'offers-count', value: stats.offers || 0 },
            { id: 'revenue-amount', value: stats.revenue || 0, currency: true },
            { id: 'users-count', value: stats.users || 0 }
        ];

        updates.forEach((update, index) => {
            setTimeout(() => {
                this.animateCounter(update.id, update.value, update.currency);
            }, index * 150); // Последовательная анимация
        });
    }

    // Анимация счетчика
    animateCounter(elementId, targetValue, isCurrency = false) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const startValue = 0;
        const duration = 1500;
        const startTime = performance.now();

        const updateCounter = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Easing function для плавности
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.floor(startValue + (targetValue - startValue) * easeOutQuart);

            // Форматирование значения
            element.textContent = this.formatValue(currentValue, isCurrency);

            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = this.formatValue(targetValue, isCurrency);
            }
        };

        requestAnimationFrame(updateCounter);
    }

    // Форматирование значений
    formatValue(value, isCurrency = false) {
        if (isCurrency) {
            return new Intl.NumberFormat('ru-RU', {
                style: 'currency',
                currency: 'RUB',
                minimumFractionDigits: 0
            }).format(value);
        }

        // Компактное отображение больших чисел
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }

        return new Intl.NumberFormat('ru-RU').format(value);
    }

    // Показ резервных данных при ошибке
    showFallbackData() {
        const fallbackStats = {
            channels: 0,
            offers: 0,
            revenue: 0,
            users: 0
        };

        this.updateStatsDisplay(fallbackStats);

        // Показать сообщение об ошибке
        if (window.UI) {
            window.UI.showNotification('Не удалось загрузить актуальную статистику');
        }
    }

    // Автообновление данных
    startAutoUpdate() {
        // Обновляем каждые 5 минут
        this.updateInterval = setInterval(() => {
            if (!document.hidden) {
                this.loadStats();
            }
        }, 5 * 60 * 1000);
    }

    // Остановка автообновления
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    // Принудительное обновление
    refresh() {
        this.loadStats();
    }

    // Очистка ресурсов
    destroy() {
        this.stopAutoUpdate();
        this.statsCache = null;
    }
}

// Создание глобального экземпляра
window.Dashboard = new Dashboard();

// Очистка при уходе со страницы
window.addEventListener('beforeunload', () => {
    if (window.Dashboard) {
        window.Dashboard.destroy();
    }
});

// Обновление при возвращении на страницу
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.Dashboard && !window.Dashboard.isLoading) {
        window.Dashboard.refresh();
    }
});