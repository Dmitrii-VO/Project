/**
 * analytics.js - JavaScript для страницы аналитики
 * Telegram Mini App - Статистика и аналитика
 * 
 * Функции:
 * - Загрузка данных из API
 * - Обновление статистических карточек
 * - Создание графиков с Chart.js
 * - Обработка ошибок и состояний загрузки
 */

class AnalyticsManager {
    constructor() {
        this.isLoading = false;
        this.charts = {};
        this.data = {};
        this.currentSection = 'overview';
        
        console.log('📊 Analytics Manager инициализирован');
    }

    // === ИНИЦИАЛИЗАЦИЯ ===
    async init() {
        try {
            console.log('🚀 Инициализация аналитики...');
            
            // Показываем состояние загрузки
            this.showLoadingState();
            
            // Загружаем данные с API
            await this.loadAnalyticsData();
            
            // Обновляем UI
            this.updateStatCards();
            
            // Инициализируем графики
            this.initializeCharts();
            
            // Настраиваем навигацию
            this.setupNavigation();
            
            console.log('✅ Аналитика успешно инициализирована');
            
        } catch (error) {
            console.error('❌ Ошибка инициализации аналитики:', error);
            this.showErrorState(error.message);
        }
    }

    // === ЗАГРУЗКА ДАННЫХ ===
    async loadAnalyticsData() {
        try {
            this.isLoading = true;
            
            console.log('📡 Загрузка данных из API...');
            
            const response = await fetch('/api/statistics/dashboard', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Web-App-Data': window.Telegram?.WebApp?.initData || ''
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Ошибка загрузки данных');
            }

            this.data = result.data || {};
            console.log('📊 Данные успешно загружены:', this.data);
            
            return this.data;
            
        } catch (error) {
            console.error('❌ Ошибка загрузки данных:', error);
            
            // Используем тестовые данные в случае ошибки
            this.data = this.generateTestData();
            console.log('🧪 Используются тестовые данные');
            
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    // === ОБНОВЛЕНИЕ КАРТОЧЕК СТАТИСТИКИ ===
    updateStatCards() {
        const stats = this.data;
        
        // Универсальные элементы для всех страниц
        const elements = {
            'total-views': this.formatNumber(stats.total_views || 0),
            'click-rate': this.formatPercentage(stats.click_rate || 0),
            'total-revenue': this.formatCurrency(stats.total_revenue || 0),
            'conversion-rate': this.formatPercentage(stats.conversion_rate || 0),
            'total-offers': this.formatNumber(stats.total_offers || 0),
            'total-proposals': this.formatNumber(stats.total_proposals || 0),
            'acceptance-rate': this.formatPercentage(stats.acceptance_rate || 0),
            'channels-count': this.formatNumber(stats.channels_count || 0),
            'offers-count': this.formatNumber(stats.offers_count || 0),
            'revenue-amount': this.formatCurrency(stats.revenue_amount || 0),
            'users-count': this.formatNumber(stats.users_count || 0),
            'avg-cpm': this.formatCurrency(stats.avg_cpm || 0),
            'total-spent': this.formatCurrency(stats.total_spent || 0),
            'month-spent': this.formatCurrency(stats.month_spent || 0),
            'avg-check': this.formatCurrency(stats.avg_check || 0)
        };

        // Обновляем все найденные элементы
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = value;
                element.classList.remove('loading');
                console.log(`📈 Обновлен элемент ${id}: ${value}`);
            }
        });
    }

    // === ИНИЦИАЛИЗАЦИЯ ГРАФИКОВ ===
    initializeCharts() {
        console.log('📈 Инициализация графиков...');
        
        // График просмотров по дням
        this.createViewsChart();
        
        // График статусов предложений
        this.createProposalsChart();
        
        // График расходов
        this.createSpendingChart();
        
        // График эффективности
        this.createEfficiencyChart();
        
        console.log('✅ Графики инициализированы');
    }

    // === СОЗДАНИЕ ГРАФИКА ПРОСМОТРОВ ===
    createViewsChart() {
        const canvas = document.getElementById('viewsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.data.views_by_day || this.generateViewsData();

        this.charts.views = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Просмотры',
                    data: data.values,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // === СОЗДАНИЕ ГРАФИКА ПРЕДЛОЖЕНИЙ ===
    createProposalsChart() {
        const canvas = document.getElementById('proposalsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.data.proposals_stats || {
            accepted: 45,
            rejected: 25,
            pending: 30
        };

        this.charts.proposals = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Принято', 'Отклонено', 'Ожидают'],
                datasets: [{
                    data: [data.accepted, data.rejected, data.pending],
                    backgroundColor: [
                        '#10B981', // Зеленый для принятых
                        '#EF4444', // Красный для отклоненных
                        '#F59E0B'  // Желтый для ожидающих
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // === СОЗДАНИЕ ГРАФИКА РАСХОДОВ ===
    createSpendingChart() {
        const canvas = document.getElementById('spendingChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.data.spending_by_day || this.generateSpendingData();

        this.charts.spending = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Расходы',
                    data: data.values,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgb(102, 126, 234)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // === СОЗДАНИЕ ГРАФИКА ЭФФЕКТИВНОСТИ ===
    createEfficiencyChart() {
        const canvas = document.getElementById('efficiencyChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.data.efficiency_stats || {
            cpm: 75,
            ctr: 65,
            conversion: 45,
            roi: 85,
            reach: 70
        };

        this.charts.efficiency = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['CPM', 'CTR', 'Конверсия', 'ROI', 'Охват'],
                datasets: [{
                    label: 'Эффективность',
                    data: [data.cpm, data.ctr, data.conversion, data.roi, data.reach],
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    pointBackgroundColor: 'rgb(102, 126, 234)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(102, 126, 234)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    // === НАВИГАЦИЯ ПО РАЗДЕЛАМ ===
    setupNavigation() {
        const navCards = document.querySelectorAll('.nav-card');
        
        navCards.forEach(card => {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                
                const section = card.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
                if (section) {
                    this.showSection(section);
                }
            });
        });
    }

    showSection(section) {
        this.currentSection = section;
        
        // Обновляем активную карточку
        document.querySelectorAll('.nav-card').forEach(card => {
            card.classList.remove('active');
        });
        
        const activeCard = document.querySelector(`[onclick*="${section}"]`);
        if (activeCard) {
            activeCard.classList.add('active');
        }
        
        // Здесь можно добавить логику показа/скрытия разделов
        console.log(`📄 Переключен раздел: ${section}`);
    }

    // === СОСТОЯНИЯ ЗАГРУЗКИ ===
    showLoadingState() {
        document.querySelectorAll('.loading').forEach(element => {
            element.textContent = 'Загрузка...';
        });
    }

    showErrorState(message) {
        document.querySelectorAll('.loading').forEach(element => {
            element.textContent = 'Ошибка';
            element.style.color = '#EF4444';
        });
        
        console.error('❌ Ошибка аналитики:', message);
        
        // Показываем уведомление пользователю
        this.showNotification('Ошибка загрузки данных', 'error');
    }

    // === УТИЛИТЫ ===
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0
        }).format(amount);
    }

    formatPercentage(value) {
        return value.toFixed(1) + '%';
    }

    // === ТЕСТОВЫЕ ДАННЫЕ ===
    generateTestData() {
        return {
            total_views: 12450,
            click_rate: 3.2,
            total_revenue: 45600,
            conversion_rate: 2.1,
            total_offers: 25,
            total_proposals: 156,
            acceptance_rate: 68.5,
            channels_count: 45,
            offers_count: 89,
            revenue_amount: 234500,
            users_count: 1250,
            avg_cpm: 45.50,
            total_spent: 23400,
            month_spent: 15600,
            avg_check: 2340
        };
    }

    generateViewsData() {
        const labels = [];
        const values = [];
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('ru-RU', { 
                month: 'short', 
                day: 'numeric' 
            }));
            values.push(Math.floor(Math.random() * 1000) + 500);
        }
        
        return { labels, values };
    }

    generateSpendingData() {
        const labels = [];
        const values = [];
        
        for (let i = 29; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('ru-RU', { 
                day: 'numeric' 
            }));
            values.push(Math.floor(Math.random() * 5000) + 1000);
        }
        
        return { labels, values };
    }

    showNotification(message, type = 'info') {
        // Простое уведомление в консоли
        console.log(`📢 ${type.toUpperCase()}: ${message}`);
        
        // Здесь можно добавить красивые toast-уведомления
        if (window.Telegram?.WebApp?.showAlert) {
            window.Telegram.WebApp.showAlert(message);
        }
    }

    // === ОБНОВЛЕНИЕ ДАННЫХ ===
    async refresh() {
        console.log('🔄 Обновление аналитики...');
        await this.loadAnalyticsData();
        this.updateStatCards();
        this.updateCharts();
    }

    updateCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.update) {
                chart.update();
            }
        });
    }
}

// === ГЛОБАЛЬНЫЕ ФУНКЦИИ ===
window.showSection = function(section) {
    if (window.analyticsManager) {
        window.analyticsManager.showSection(section);
    }
};

window.changeChartPeriod = function(chart, period) {
    console.log(`📊 Изменение периода графика ${chart}: ${period}`);
    // Здесь можно добавить логику изменения периода
};

window.goBack = function() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
};

// === ИНИЦИАЛИЗАЦИЯ ===
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Инициализация страницы аналитики...');
    
    try {
        window.analyticsManager = new AnalyticsManager();
        await window.analyticsManager.init();
        
        console.log('✅ Страница аналитики готова');
        
    } catch (error) {
        console.error('❌ Критическая ошибка инициализации:', error);
    }
});

// === TELEGRAM WEB APP ИНТЕГРАЦИЯ ===
if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    console.log('📱 Telegram Web App готов');
}
