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
            console.log('🌐 URL запроса:', '/api/analytics/dashboard');
            
            const response = await fetch('/api/analytics/dashboard', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Web-App-Data': window.Telegram?.WebApp?.initData || ''
                }
            });

            console.log('📞 Ответ сервера:', {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok,
                headers: Object.fromEntries(response.headers.entries())
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Ошибка HTTP:', errorText);
                throw new Error(`HTTP ${response.status}: ${response.statusText}\nТекст ошибки: ${errorText}`);
            }

            const result = await response.json();
            console.log('📊 Полученные данные от API:', result);
            
            if (!result.success) {
                console.error('❌ API вернул ошибку:', result);
                throw new Error(result.error || result.message || 'Неизвестная ошибка сервера');
            }

            this.data = result;
            console.log('✅ Данные успешно сохранены в this.data:', this.data);
            
            return this.data;
            
        } catch (error) {
            console.error('❌ Критическая ошибка загрузки данных:', error);
            console.error('📋 Детали ошибки:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
            
            // Пытаемся загрузить через альтернативные источники
            console.log('🔄 Попытка использовать fallback данные...');
            try {
                await this.loadFallbackData();
                console.log('✅ Fallback данные загружены успешно');
            } catch (fallbackError) {
                console.error('❌ Ошибка загрузки fallback данных:', fallbackError);
                // Используем пустые данные вместо тестовых
                this.data = this.generateEmptyData();
                console.log('📊 Используются пустые/нулевые данные - нет информации для отображения');
                console.log('🎯 Структура пустых данных:', this.data);
            }
        } finally {
            this.isLoading = false;
        }
    }

    // === ОБНОВЛЕНИЕ КАРТОЧЕК СТАТИСТИКИ ===
    updateStatCards() {
        const stats = this.data.data || this.data;
        
        console.log('🔄 Обновление карточек статистики...');
        console.log('📊 Данные для обновления:', stats);
        
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

        console.log('🎯 Значения для обновления:', elements);

        // Обновляем все найденные элементы
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                // Удаляем loading-skeleton если есть
                const loadingSkeleton = element.querySelector('.loading-skeleton');
                if (loadingSkeleton) {
                    loadingSkeleton.remove();
                }
                
                element.innerHTML = value;
                element.classList.remove('loading');
                console.log(`✅ Обновлен элемент ${id}: ${value}`);
            } else {
                console.warn(`⚠️ Элемент с ID '${id}' не найден`);
            }
        });
        
        console.log('🏁 Обновление карточек завершено');
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
        
        // Загружаем данные для конкретной вкладки
        console.log(`📄 Переключен раздел: ${section}`);
        this.loadTabData(section);
    }

    // === ЗАГРУЗКА ДАННЫХ ПО ВКЛАДКАМ ===
    async loadTabData(section) {
        console.log(`🔄 Загрузка данных для вкладки: ${section}`);
        
        switch(section) {
            case 'channels':
                await this.loadChannelsData();
                break;
            case 'offers':
                await this.loadOffersData();
                break;
            case 'revenue':
                await this.loadRevenueData();
                break;
            case 'overview':
                // Данные уже загружены в init()
                break;
            default:
                console.warn(`⚠️ Неизвестная вкладка: ${section}`);
        }
    }

    // === ЗАГРУЗКА ДАННЫХ КАНАЛОВ ===
    async loadChannelsData() {
        try {
            console.log('📺 Загрузка данных каналов...');
            
            const response = await fetch('/api/analytics/channels', {
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
                throw new Error(result.error || 'Ошибка загрузки данных каналов');
            }

            this.updateChannelsDisplay(result.data);
            console.log('✅ Данные каналов загружены:', result.data);

        } catch (error) {
            console.error('❌ Ошибка загрузки каналов:', error);
            this.showChannelsError(error.message);
        }
    }

    updateChannelsDisplay(data) {
        // Обновляем сводные метрики
        document.getElementById('channels-total-count').innerHTML = data.total_channels || 0;
        document.getElementById('channels-verified-count').innerHTML = data.verified_channels || 0;
        document.getElementById('channels-total-subscribers').innerHTML = this.formatNumber(data.total_subscribers || 0);
        document.getElementById('channels-total-earned').innerHTML = this.formatCurrency(data.total_earned || 0);

        // Показываем контент
        document.getElementById('channels-loading').style.display = 'none';
        document.getElementById('channels-error').style.display = 'none';
        document.getElementById('channels-content').style.display = 'block';

        const tableBody = document.getElementById('channels-table-body');
        
        if (!data.channels || data.channels.length === 0) {
            document.getElementById('channels-empty').style.display = 'block';
            document.querySelector('#channels-content .table-container').style.display = 'none';
            return;
        }

        // Заполняем таблицу каналов
        tableBody.innerHTML = data.channels.map(channel => `
            <tr>
                <td>
                    <div class="channel-info">
                        <div class="channel-title">
                            ${channel.title}
                            ${channel.is_verified ? '<span class="verified-badge">✅</span>' : ''}
                        </div>
                        <div class="channel-username">@${channel.username || 'username'}</div>
                    </div>
                </td>
                <td class="number">${this.formatNumber(channel.subscribers)}</td>
                <td>
                    <span class="status-badge status-${channel.verification_status}">
                        ${this.getStatusText(channel.verification_status)}
                    </span>
                </td>
                <td class="number">${channel.total_proposals}</td>
                <td class="number">
                    ${channel.accepted_proposals}
                    <span class="percentage">(${channel.acceptance_rate}%)</span>
                </td>
                <td class="number">${channel.ctr}%</td>
                <td class="number">${this.formatCurrency(channel.total_earned)}</td>
            </tr>
        `).join('');
    }

    showChannelsError(message) {
        document.getElementById('channels-loading').style.display = 'none';
        document.getElementById('channels-error').style.display = 'block';
        document.getElementById('channels-content').style.display = 'none';
    }

    // === ЗАГРУЗКА ДАННЫХ ОФФЕРОВ ===
    async loadOffersData() {
        try {
            console.log('📢 Загрузка данных офферов...');
            
            const response = await fetch('/api/analytics/offers', {
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
                throw new Error(result.error || 'Ошибка загрузки данных офферов');
            }

            this.updateOffersDisplay(result.data);
            console.log('✅ Данные офферов загружены:', result.data);

        } catch (error) {
            console.error('❌ Ошибка загрузки офферов:', error);
            this.showOffersError(error.message);
        }
    }

    updateOffersDisplay(data) {
        // Обновляем сводные метрики
        document.getElementById('offers-total-count').innerHTML = data.total_offers || 0;
        document.getElementById('offers-active-count').innerHTML = data.active_offers || 0;
        document.getElementById('offers-total-spent').innerHTML = this.formatCurrency(data.total_spent || 0);
        document.getElementById('offers-avg-ctr').innerHTML = (data.avg_ctr || 0) + '%';

        // Показываем контент
        document.getElementById('offers-loading').style.display = 'none';
        document.getElementById('offers-error').style.display = 'none';
        document.getElementById('offers-content').style.display = 'block';

        const tableBody = document.getElementById('offers-table-body');
        
        if (!data.offers || data.offers.length === 0) {
            document.getElementById('offers-empty').style.display = 'block';
            document.querySelector('#offers-content .table-container').style.display = 'none';
            return;
        }

        // Заполняем таблицу офферов
        tableBody.innerHTML = data.offers.map(offer => `
            <tr>
                <td>
                    <div class="offer-info">
                        <div class="offer-title">${offer.title}</div>
                        <div class="offer-type">${offer.offer_type}</div>
                    </div>
                </td>
                <td>${this.getCategoryText(offer.category)}</td>
                <td class="number">${this.formatCurrency(offer.price)}</td>
                <td>
                    <span class="status-badge status-${offer.status}">
                        ${this.getStatusText(offer.status)}
                    </span>
                </td>
                <td class="number">
                    ${offer.total_responses}
                    <span class="percentage">(${offer.acceptance_rate}%)</span>
                </td>
                <td class="number">${offer.ctr}%</td>
                <td class="number ${offer.roi >= 0 ? 'positive' : 'negative'}">${offer.roi}%</td>
                <td class="number">${this.formatCurrency(offer.total_spent)}</td>
            </tr>
        `).join('');
    }

    showOffersError(message) {
        document.getElementById('offers-loading').style.display = 'none';
        document.getElementById('offers-error').style.display = 'block';
        document.getElementById('offers-content').style.display = 'none';
    }

    // === ЗАГРУЗКА ФИНАНСОВЫХ ДАННЫХ ===
    async loadRevenueData() {
        try {
            console.log('💰 Загрузка финансовых данных...');
            
            const response = await fetch('/api/analytics/revenue', {
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
                throw new Error(result.error || 'Ошибка загрузки финансовых данных');
            }

            this.updateRevenueDisplay(result.data);
            this.createRevenueChart(result.data);
            console.log('✅ Финансовые данные загружены:', result.data);

        } catch (error) {
            console.error('❌ Ошибка загрузки финансовых данных:', error);
            this.showRevenueError(error.message);
        }
    }

    updateRevenueDisplay(data) {
        // Обновляем сводные метрики
        document.getElementById('revenue-current-balance').innerHTML = this.formatCurrency(data.current_balance || 0);
        document.getElementById('revenue-total-earned').innerHTML = this.formatCurrency(data.total_earned || 0);
        document.getElementById('revenue-total-spent').innerHTML = this.formatCurrency(data.total_spent || 0);
        document.getElementById('revenue-net-profit').innerHTML = this.formatCurrency(data.net_profit || 0);

        // Обновляем прогнозы
        document.getElementById('revenue-monthly-projection').innerHTML = this.formatCurrency(data.monthly_projection || 0);
        
        const dailyAverage = data.total_earned / Math.max(data.daily_revenue?.length || 1, 1);
        document.getElementById('revenue-daily-average').innerHTML = this.formatCurrency(dailyAverage);
        
        const trend = data.net_profit >= 0 ? '📈 Растет' : '📉 Падает';
        document.getElementById('revenue-trend').innerHTML = trend;

        // Показываем контент
        document.getElementById('revenue-loading').style.display = 'none';
        document.getElementById('revenue-error').style.display = 'none';
        document.getElementById('revenue-content').style.display = 'block';

        // Заполняем категории доходов
        const categoriesContainer = document.getElementById('revenue-categories');
        
        if (!data.revenue_by_category || data.revenue_by_category.length === 0) {
            document.getElementById('revenue-empty').style.display = 'block';
            return;
        }

        categoriesContainer.innerHTML = data.revenue_by_category.map(category => `
            <div class="category-item">
                <div class="category-info">
                    <div class="category-name">${this.getCategoryText(category.category)}</div>
                    <div class="category-placements">${category.placements} размещений</div>
                </div>
                <div class="category-revenue">${this.formatCurrency(category.revenue)}</div>
            </div>
        `).join('');
    }

    createRevenueChart(data) {
        const canvas = document.getElementById('revenueChart');
        if (!canvas || !data.daily_revenue) return;

        document.getElementById('revenue-chart-loading').style.display = 'none';

        const ctx = canvas.getContext('2d');
        
        const labels = data.daily_revenue.map(day => {
            const date = new Date(day.date);
            return date.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' });
        });
        
        const revenueData = data.daily_revenue.map(day => day.revenue);
        const expensesData = data.daily_expenses?.map(day => day.expenses) || [];

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Доходы',
                    data: revenueData,
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Расходы',
                    data: expensesData,
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
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
                        display: true,
                        position: 'top'
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

    showRevenueError(message) {
        document.getElementById('revenue-loading').style.display = 'none';
        document.getElementById('revenue-error').style.display = 'block';
        document.getElementById('revenue-content').style.display = 'none';
    }

    // === УТИЛИТЫ ===
    getStatusText(status) {
        const statusMap = {
            'pending': 'Ожидает',
            'verified': 'Верифицирован',
            'rejected': 'Отклонен',
            'active': 'Активный',
            'draft': 'Черновик',
            'completed': 'Завершен',
            'paused': 'Приостановлен'
        };
        return statusMap[status] || status;
    }

    getCategoryText(category) {
        const categoryMap = {
            'general': 'Общее',
            'tech': 'Технологии',
            'finance': 'Финансы',
            'lifestyle': 'Образ жизни',
            'education': 'Образование',
            'entertainment': 'Развлечения',
            'business': 'Бизнес',
            'health': 'Здоровье',
            'sports': 'Спорт',
            'travel': 'Путешествия'
        };
        return categoryMap[category] || category;
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
            element.classList.add('error-color');
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

    // === ЗАГРУЗКА FALLBACK ДАННЫХ ===
    async loadFallbackData() {
        console.log('🔄 Попытка загрузки через альтернативные источники...');
        
        // Пытаемся получить базовую информацию о пользователе
        try {
            const userResponse = await fetch('/api/users/current', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Web-App-Data': window.Telegram?.WebApp?.initData || ''
                }
            });

            if (userResponse.ok) {
                const userData = await userResponse.json();
                if (userData.success && userData.data) {
                    this.data = this.processUserData(userData.data);
                    console.log('✅ Базовые данные загружены через /api/users/current');
                    return;
                }
            }
        } catch (e) {
            console.warn('⚠️ Fallback через /api/users/current не удался:', e);
        }

        throw new Error('Все способы загрузки данных не удались');
    }

    processUserData(userData) {
        return {
            data: {
                total_views: 0,
                click_rate: 0,
                total_revenue: userData.balance || 0,
                conversion_rate: 0,
                channels_count: 0,
                offers_count: 0,
                acceptance_rate: 0,
                views_by_day: { labels: ['Нет данных'], values: [0] },
                proposals_stats: { accepted: 0, rejected: 0, pending: 0 },
                spending_by_day: { labels: ['Нет данных'], values: [0] },
                efficiency_stats: { cpm: 0, ctr: 0, conversion: 0, roi: 0, reach: 0 }
            }
        };
    }

    // === ПУСТЫЕ ДАННЫЕ ===
    generateEmptyData() {
        return {
            data: {
                total_views: 0,
                click_rate: 0,
                total_revenue: 0,
                conversion_rate: 0,
                total_offers: 0,
                total_proposals: 0,
                acceptance_rate: 0,
                channels_count: 0,
                offers_count: 0,
                revenue_amount: 0,
                users_count: 0,
                avg_cpm: 0,
                total_spent: 0,
                month_spent: 0,
                avg_check: 0,
                views_by_day: { labels: ['Нет данных'], values: [0] },
                proposals_stats: { accepted: 0, rejected: 0, pending: 0 },
                spending_by_day: { labels: ['Нет данных'], values: [0] },
                efficiency_stats: { cpm: 0, ctr: 0, conversion: 0, roi: 0, reach: 0 }
            }
        };
    }

    // === ТЕСТОВЫЕ ДАННЫЕ (для отладки) ===
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

window.loadChannelsData = function() {
    if (window.analyticsManager) {
        window.analyticsManager.loadChannelsData();
    }
};

window.loadOffersData = function() {
    if (window.analyticsManager) {
        window.analyticsManager.loadOffersData();
    }
};

window.loadRevenueData = function() {
    if (window.analyticsManager) {
        window.analyticsManager.loadRevenueData();
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
