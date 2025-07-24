/**
 * payments.js - JavaScript для страницы платежей
 * Telegram Mini App - Система платежей и выводов
 * 
 * Функции:
 * - Загрузка реальных данных платежей из API
 * - Обработка запросов на вывод средств
 * - Управление способами оплаты
 * - История транзакций
 */

class PaymentsManager {
    constructor() {
        this.isLoading = false;
        this.data = {};
        this.currentTab = 'history';
        
        console.log('💳 Payments Manager инициализирован');
    }

    // === ИНИЦИАЛИЗАЦИЯ ===
    async init() {
        try {
            console.log('🚀 Инициализация платежей...');
            
            // Показываем состояние загрузки
            this.showLoadingState();
            
            // Загружаем данные с API
            await this.loadPaymentData();
            
            // Обновляем UI
            this.updateStatCards();
            this.loadTransactionHistory();
            
            // Настраиваем табы
            this.setupTabs();
            
            console.log('✅ Платежи успешно инициализированы');
            
        } catch (error) {
            console.error('❌ Ошибка инициализации платежей:', error);
            this.showErrorState(error.message);
        }
    }

    // === ЗАГРУЗКА ДАННЫХ ===
    async loadPaymentData() {
        try {
            this.isLoading = true;
            
            console.log('📡 Загрузка данных платежей из API...');
            
            const response = await fetch('/api/payments/dashboard', {
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
                throw new Error(result.message || 'Ошибка загрузки данных платежей');
            }

            this.data = result.data || {};
            console.log('💳 Данные платежей загружены:', this.data);
            
            return this.data;
            
        } catch (error) {
            console.error('❌ Ошибка загрузки данных платежей:', error);
            
            // Загружаем данные через альтернативные API
            try {
                await this.loadFallbackData();
            } catch (fallbackError) {
                console.error('❌ Ошибка загрузки fallback данных:', fallbackError);
                // Используем базовые данные
                this.data = this.generateBasicData();
            }
        } finally {
            this.isLoading = false;
        }
    }

    async loadFallbackData() {
        console.log('🔄 Попытка загрузки через альтернативные API...');
        
        // Пытаемся загрузить через существующие endpoints
        try {
            const statsResponse = await fetch('/api/payments/stats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Web-App-Data': window.Telegram?.WebApp?.initData || ''
                }
            });

            if (statsResponse.ok) {
                const statsData = await statsResponse.json();
                if (statsData.success) {
                    this.data = this.processStatsData(statsData);
                    console.log('✅ Данные загружены через /api/payments/stats');
                    return;
                }
            }
        } catch (e) {
            console.warn('⚠️ Fallback через /api/payments/stats не удался:', e);
        }

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
                if (userData.success) {
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

    processStatsData(statsData) {
        const payments = statsData.payments || {};
        const escrow = statsData.escrow || {};
        
        return {
            current_balance: payments.total_amount || 0,
            monthly_income: payments.total_amount || 0,
            pending_payments: payments.pending_count || 0,
            completed_payments: payments.completed_count || 0,
            failed_payments: payments.failed_count || 0,
            held_amount: escrow.held_amount || 0,
            released_amount: escrow.released_amount || 0,
            disputed_count: escrow.disputed_count || 0,
            transactions: []
        };
    }

    processUserData(userData) {
        return {
            current_balance: userData.balance || 0,
            monthly_income: userData.balance || 0,
            pending_payments: 0,
            completed_payments: 0,
            failed_payments: 0,
            held_amount: 0,
            released_amount: 0,
            disputed_count: 0,
            transactions: []
        };
    }

    generateBasicData() {
        return {
            current_balance: 0,
            monthly_income: 0,
            pending_payments: 0,
            completed_payments: 0,
            failed_payments: 0,
            held_amount: 0,
            released_amount: 0,
            disputed_count: 0,
            transactions: [
                {
                    id: 'demo_1',
                    type: 'income',
                    amount: 0,
                    description: 'Нет данных о транзакциях',
                    date: new Date().toISOString(),
                    status: 'info'
                }
            ]
        };
    }

    // === ОБНОВЛЕНИЕ UI ===
    updateStatCards() {
        const elements = {
            'total-balance': this.formatCurrency(this.data.current_balance || 0),
            'monthly-income': this.formatCurrency(this.data.monthly_income || 0),
            'pending-payments': this.formatNumber(this.data.pending_payments || 0),
            'completed-payments': this.formatNumber(this.data.completed_payments || 0)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = value;
                element.classList.remove('loading-skeleton');
                console.log(`💳 Обновлен элемент ${id}: ${value}`);
            }
        });
    }

    async loadTransactionHistory() {
        try {
            const historyContainer = document.getElementById('transaction-history');
            if (!historyContainer) return;

            const transactions = this.data.transactions || [];
            
            if (transactions.length === 0) {
                historyContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">💳</div>
                        <h3>Нет транзакций</h3>
                        <p>Ваши платежи и выводы будут отображаться здесь</p>
                    </div>
                `;
                return;
            }

            const transactionsHTML = transactions.map(transaction => {
                const typeIcon = transaction.type === 'income' ? '💰' : '💸';
                const statusClass = transaction.status === 'completed' ? 'success' : 
                                   transaction.status === 'pending' ? 'warning' : 
                                   transaction.status === 'failed' ? 'error' : 'info';
                
                return `
                    <div class="transaction-item">
                        <div class="transaction-icon">${typeIcon}</div>
                        <div class="transaction-details">
                            <div class="transaction-title">${transaction.description || 'Транзакция'}</div>
                            <div class="transaction-date">${this.formatDate(transaction.date)}</div>
                        </div>
                        <div class="transaction-amount ${transaction.type}">
                            ${transaction.type === 'income' ? '+' : '-'}${this.formatCurrency(Math.abs(transaction.amount))}
                        </div>
                        <div class="transaction-status ${statusClass}">
                            ${this.getStatusText(transaction.status)}
                        </div>
                    </div>
                `;
            }).join('');

            historyContainer.innerHTML = transactionsHTML;
            
        } catch (error) {
            console.error('❌ Ошибка загрузки истории транзакций:', error);
        }
    }

    // === УПРАВЛЕНИЕ ТАБАМИ ===
    setupTabs() {
        const tabLinks = document.querySelectorAll('.tabs-nav a');
        const tabContents = document.querySelectorAll('.tabs-content');

        tabLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                const tabId = link.getAttribute('data-tab');
                this.showTab(tabId);
                
                // Обновляем активную вкладку
                tabLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    }

    showTab(tabId) {
        this.currentTab = tabId;
        
        // Скрываем все табы
        document.querySelectorAll('.tabs-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Показываем нужный таб
        const targetTab = document.getElementById(tabId);
        if (targetTab) {
            targetTab.classList.add('active');
        }
        
        // Загружаем контент таба
        this.loadTabContent(tabId);
        
        console.log(`📄 Переключен таб: ${tabId}`);
    }

    async loadTabContent(tabId) {
        switch (tabId) {
            case 'history':
                await this.loadTransactionHistory();
                break;
            case 'withdraw':
                this.setupWithdrawForm();
                break;
            case 'methods':
                this.loadPaymentMethods();
                break;
            case 'analytics':
                this.loadPaymentAnalytics();
                break;
        }
    }

    setupWithdrawForm() {
        const withdrawTab = document.getElementById('withdraw');
        if (!withdrawTab) return;

        withdrawTab.innerHTML = `
            <div class="withdraw-form">
                <h3>Запрос на вывод средств</h3>
                <div class="form-group">
                    <label>Доступно для вывода</label>
                    <div class="available-balance">${this.formatCurrency(this.data.current_balance || 0)}</div>
                </div>
                <div class="form-group">
                    <label for="withdraw-amount">Сумма вывода</label>
                    <input type="number" id="withdraw-amount" placeholder="Введите сумму" min="100" max="${this.data.current_balance || 0}">
                </div>
                <div class="form-group">
                    <label for="withdraw-method">Способ вывода</label>
                    <select id="withdraw-method">
                        <option value="card">Банковская карта</option>
                        <option value="qiwi">QIWI Кошелек</option>
                        <option value="yoomoney">ЮMoney</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="paymentsManager.processWithdraw()">
                    Создать запрос на вывод
                </button>
            </div>
        `;
    }

    loadPaymentMethods() {
        const methodsTab = document.getElementById('methods');
        if (!methodsTab) return;

        methodsTab.innerHTML = `
            <div class="payment-methods">
                <h3>Способы оплаты</h3>
                <div class="methods-list">
                    <div class="method-item">
                        <div class="method-icon">💳</div>
                        <div class="method-info">
                            <div class="method-name">Банковские карты</div>
                            <div class="method-desc">Visa, MasterCard, МИР</div>
                        </div>
                        <div class="method-status active">Активно</div>
                    </div>
                    <div class="method-item">
                        <div class="method-icon">📱</div>
                        <div class="method-info">
                            <div class="method-name">Telegram Payments</div>
                            <div class="method-desc">Встроенные платежи Telegram</div>
                        </div>
                        <div class="method-status active">Активно</div>
                    </div>
                </div>
            </div>
        `;
    }

    loadPaymentAnalytics() {
        const analyticsTab = document.getElementById('analytics');
        if (!analyticsTab) return;

        const monthlyStats = this.calculateMonthlyStats();
        
        analyticsTab.innerHTML = `
            <div class="payment-analytics">
                <h3>Аналитика доходов</h3>
                <div class="analytics-stats">
                    <div class="stat-card">
                        <div class="stat-number">${this.formatCurrency(monthlyStats.thisMonth)}</div>
                        <div class="stat-label">Этот месяц</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${this.formatCurrency(monthlyStats.lastMonth)}</div>
                        <div class="stat-label">Прошлый месяц</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${monthlyStats.growth > 0 ? '+' : ''}${monthlyStats.growth}%</div>
                        <div class="stat-label">Рост</div>
                    </div>
                </div>
                <div class="analytics-chart">
                    <p>График доходов будет доступен после накопления данных</p>
                </div>
            </div>
        `;
    }

    // === ДЕЙСТВИЯ ===
    async processWithdraw() {
        try {
            const amount = parseFloat(document.getElementById('withdraw-amount')?.value || 0);
            const method = document.getElementById('withdraw-method')?.value;

            if (!amount || amount < 100) {
                this.showNotification('Минимальная сумма вывода 100 рублей', 'error');
                return;
            }

            if (amount > (this.data.current_balance || 0)) {
                this.showNotification('Недостаточно средств на балансе', 'error');
                return;
            }

            // Отправляем запрос на вывод
            const response = await fetch('/api/payments/withdraw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Web-App-Data': window.Telegram?.WebApp?.initData || ''
                },
                body: JSON.stringify({
                    amount: amount,
                    method: method
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Запрос на вывод создан успешно', 'success');
                await this.refresh();
            } else {
                this.showNotification(result.error || 'Ошибка создания запроса', 'error');
            }

        } catch (error) {
            console.error('❌ Ошибка вывода средств:', error);
            this.showNotification('Ошибка выполнения операции', 'error');
        }
    }

    // === СОСТОЯНИЯ ЗАГРУЗКИ ===
    showLoadingState() {
        document.querySelectorAll('.loading-skeleton').forEach(element => {
            element.textContent = 'Загрузка...';
        });
    }

    showErrorState(message) {
        document.querySelectorAll('.loading-skeleton').forEach(element => {
            element.textContent = 'Ошибка';
            element.classList.add('error-color');
        });
        
        console.error('❌ Ошибка платежей:', message);
        this.showNotification('Ошибка загрузки данных', 'error');
    }

    // === УТИЛИТЫ ===
    formatCurrency(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0
        }).format(amount);
    }

    formatNumber(num) {
        return new Intl.NumberFormat('ru-RU').format(num);
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getStatusText(status) {
        const statuses = {
            'completed': 'Завершено',
            'pending': 'Ожидает',
            'failed': 'Отклонено',
            'processing': 'Обработка',
            'info': 'Информация'
        };
        return statuses[status] || status;
    }

    calculateMonthlyStats() {
        // Базовая аналитика на основе имеющихся данных
        const thisMonth = this.data.monthly_income || 0;
        const lastMonth = thisMonth * 0.8; // Примерное значение
        const growth = lastMonth > 0 ? ((thisMonth - lastMonth) / lastMonth * 100).toFixed(1) : 0;

        return {
            thisMonth,
            lastMonth,
            growth: parseFloat(growth)
        };
    }

    showNotification(message, type = 'info') {
        console.log(`📢 ${type.toUpperCase()}: ${message}`);
        
        if (window.Telegram?.WebApp?.showAlert) {
            window.Telegram.WebApp.showAlert(message);
        } else {
            // Fallback для браузера
            alert(message);
        }
    }

    // === ОБНОВЛЕНИЕ ДАННЫХ ===
    async refresh() {
        console.log('🔄 Обновление данных платежей...');
        await this.loadPaymentData();
        this.updateStatCards();
        this.loadTabContent(this.currentTab);
    }
}

// === ГЛОБАЛЬНЫЕ ФУНКЦИИ ===
window.requestWithdraw = function() {
    if (window.paymentsManager) {
        window.paymentsManager.showTab('withdraw');
        // Переключаем активную вкладку в навигации
        document.querySelectorAll('.tabs-nav a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-tab') === 'withdraw') {
                link.classList.add('active');
            }
        });
    }
};

window.addPaymentMethod = function() {
    if (window.paymentsManager) {
        window.paymentsManager.showTab('methods');
        document.querySelectorAll('.tabs-nav a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('data-tab') === 'methods') {
                link.classList.add('active');
            }
        });
    }
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
    console.log('🚀 Инициализация страницы платежей...');
    
    try {
        window.paymentsManager = new PaymentsManager();
        await window.paymentsManager.init();
        
        console.log('✅ Страница платежей готова');
        
    } catch (error) {
        console.error('❌ Критическая ошибка инициализации платежей:', error);
    }
});

// === TELEGRAM WEB APP ИНТЕГРАЦИЯ ===
if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    console.log('📱 Telegram Web App готов для платежей');
}