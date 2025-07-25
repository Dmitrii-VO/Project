/**
 * Smart Offer Creation Wizard
 * Упрощенная система создания офферов в одну форму
 */

class SmartOfferWizard {
    constructor() {
        this.api = new OffersAPI();
        this.currentStep = 1;
        this.offerData = {};
        this.selectedChannels = [];
        this.budgetCalculator = new BudgetCalculator();
        this.channelRecommendations = [];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadCategories();
        this.initBudgetCalculator();
    }

    setupEventListeners() {
        // Основная форма
        document.getElementById('smartOfferForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });

        // Умный расчет бюджета
        document.getElementById('offerBudget')?.addEventListener('input', (e) => {
            this.calculateReachPreview(parseFloat(e.target.value));
        });

        // Выбор категории - загружаем рекомендации каналов
        document.getElementById('offerCategory')?.addEventListener('change', (e) => {
            this.loadChannelRecommendations(e.target.value);
        });

        // Переключение между табами
        document.querySelectorAll('.wizard-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(parseInt(e.target.dataset.tab));
            });
        });
    }

    /**
     * Умный калькулятор охвата по бюджету
     */
    calculateReachPreview(budget) {
        if (!budget || budget <= 0) {
            this.updateReachPreview(0, 0);
            return;
        }

        const category = document.getElementById('offerCategory')?.value;
        const avgCPM = this.getAverageCPM(category);
        const estimatedReach = Math.floor(budget / avgCPM * 1000);
        const estimatedViews = Math.floor(estimatedReach * 0.15); // 15% engagement rate

        this.updateReachPreview(estimatedReach, estimatedViews);
        this.updateBudgetRecommendations(budget, category);
    }

    updateReachPreview(reach, views) {
        const reachElement = document.getElementById('estimatedReach');
        const viewsElement = document.getElementById('estimatedViews');
        
        if (reachElement) reachElement.textContent = this.formatNumber(reach);
        if (viewsElement) viewsElement.textContent = this.formatNumber(views);
    }

    /**
     * Получение средней стоимости CPM по категории
     */
    getAverageCPM(category) {
        const cpmData = {
            'tech': 250,
            'business': 300,
            'lifestyle': 180,
            'entertainment': 150,
            'education': 200,
            'health': 280,
            'travel': 220,
            'food': 170,
            'fashion': 190,
            'sports': 160,
            'gaming': 140,
            'crypto': 400,
            'default': 200
        };
        
        return cpmData[category] || cpmData['default'];
    }

    /**
     * Загрузка умных рекомендаций каналов
     */
    async loadChannelRecommendations(category) {
        if (!category) return;

        try {
            const budget = parseFloat(document.getElementById('offerBudget')?.value) || 0;
            const response = await fetch('/api/offers/smart-recommendations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: category,
                    budget: budget,
                    factors: ['engagement', 'price_efficiency', 'audience_match']
                })
            });

            if (response.ok) {
                this.channelRecommendations = await response.json();
                this.renderChannelRecommendations();
            }
        } catch (error) {
            console.error('Ошибка загрузки рекомендаций:', error);
        }
    }

    /**
     * Отображение рекомендованных каналов с умными метриками
     */
    renderChannelRecommendations() {
        const container = document.getElementById('channelRecommendations');
        if (!container || !this.channelRecommendations.data) return;

        const html = this.channelRecommendations.data.map(channel => `
            <div class="channel-recommendation" data-channel-id="${channel.id}">
                <div class="channel-info">
                    <div class="channel-header">
                        <h4>@${channel.username}</h4>
                        <div class="match-score">
                            <span class="score-value">${Math.round(channel.match_score * 100)}%</span>
                            <span class="score-label">совпадение</span>
                        </div>
                    </div>
                    
                    <div class="channel-metrics">
                        <div class="metric">
                            <span class="metric-value">${this.formatNumber(channel.subscribers)}</span>
                            <span class="metric-label">подписчиков</span>
                        </div>
                        <div class="metric">
                            <span class="metric-value">${channel.engagement_rate}%</span>
                            <span class="metric-label">вовлеченность</span>
                        </div>
                        <div class="metric">
                            <span class="metric-value">₽${this.formatNumber(channel.price_per_post)}</span>
                            <span class="metric-label">за пост</span>
                        </div>
                        <div class="metric expected-roi">
                            <span class="metric-value">${channel.expected_roi}x</span>
                            <span class="metric-label">прогноз ROI</span>
                        </div>
                    </div>
                    
                    <div class="channel-tags">
                        ${channel.categories.map(cat => `<span class="tag">${cat}</span>`).join('')}
                    </div>
                </div>
                
                <div class="channel-actions">
                    <label class="channel-select">
                        <input type="checkbox" name="selectedChannels" value="${channel.id}">
                        <span class="checkmark"></span>
                        <span class="select-label">Выбрать</span>
                    </label>
                    <button type="button" class="btn-preview" onclick="previewChannel(${channel.id})">
                        Превью
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
        this.setupChannelSelection();
    }

    /**
     * Настройка выбора каналов с автоматическим пересчетом
     */
    setupChannelSelection() {
        document.querySelectorAll('input[name="selectedChannels"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectedChannels();
                this.recalculateTotals();
            });
        });
    }

    updateSelectedChannels() {
        const checkedBoxes = document.querySelectorAll('input[name="selectedChannels"]:checked');
        this.selectedChannels = Array.from(checkedBoxes).map(cb => ({
            id: parseInt(cb.value),
            data: this.channelRecommendations.data.find(c => c.id === parseInt(cb.value))
        }));
    }

    /**
     * Пересчет общей стоимости и охвата
     */
    recalculateTotals() {
        const totals = this.selectedChannels.reduce((acc, channel) => {
            const channelData = channel.data;
            acc.cost += channelData.price_per_post;
            acc.reach += channelData.subscribers;
            acc.expectedViews += Math.floor(channelData.subscribers * channelData.engagement_rate / 100);
            return acc;
        }, { cost: 0, reach: 0, expectedViews: 0 });

        this.updateTotalsSummary(totals);
        this.validateBudget(totals.cost);
    }

    updateTotalsSummary(totals) {
        document.getElementById('totalCost').textContent = `₽${this.formatNumber(totals.cost)}`;
        document.getElementById('totalReach').textContent = this.formatNumber(totals.reach);
        document.getElementById('totalViews').textContent = this.formatNumber(totals.expectedViews);
        
        // Обновляем прогресс бар бюджета
        const budget = parseFloat(document.getElementById('offerBudget')?.value) || 0;
        const budgetUsage = budget > 0 ? (totals.cost / budget) * 100 : 0;
        document.getElementById('budgetProgress').style.width = `${Math.min(budgetUsage, 100)}%`;
    }

    validateBudget(totalCost) {
        const budget = parseFloat(document.getElementById('offerBudget')?.value) || 0;
        const budgetWarning = document.getElementById('budgetWarning');
        
        if (totalCost > budget) {
            budgetWarning.style.display = 'block';
            budgetWarning.textContent = `Превышение бюджета на ₽${this.formatNumber(totalCost - budget)}`;
            budgetWarning.className = 'budget-warning error';
        } else if (totalCost < budget * 0.7) {
            budgetWarning.style.display = 'block';
            budgetWarning.textContent = `Неиспользованный бюджет: ₽${this.formatNumber(budget - totalCost)}`;
            budgetWarning.className = 'budget-warning info';
        } else {
            budgetWarning.style.display = 'none';
        }
    }

    /**
     * Отправка умной формы оффера
     */
    async handleFormSubmit() {
        try {
            const formData = this.collectFormData();
            
            // Валидация
            const validation = this.validateOfferData(formData);
            if (!validation.isValid) {
                this.showValidationErrors(validation.errors);
                return;
            }

            // Показываем прелоадер
            this.showSubmissionProgress();

            // Создаем оффер с выбранными каналами
            const offerResponse = await this.api.createSmartOffer(formData);
            
            if (offerResponse.success) {
                this.showSuccessMessage(offerResponse.data);
                this.resetForm();
                
                // Перенаправляем на страницу с офферами
                setTimeout(() => {
                    window.location.href = '/offers?tab=my-offers';
                }, 2000);
            } else {
                this.showErrorMessage(offerResponse.error);
            }

        } catch (error) {
            console.error('Ошибка создания оффера:', error);
            this.showErrorMessage('Произошла ошибка при создании оффера');
        } finally {
            this.hideSubmissionProgress();
        }
    }

    collectFormData() {
        return {
            title: document.getElementById('offerTitle')?.value.trim(),
            description: document.getElementById('offerDescription')?.value.trim(),
            category: document.getElementById('offerCategory')?.value,
            budget: parseFloat(document.getElementById('offerBudget')?.value) || 0,
            requirements: document.getElementById('offerRequirements')?.value.trim(),
            deadline: document.getElementById('offerDeadline')?.value,
            selected_channels: this.selectedChannels.map(c => c.id),
            channel_requirements: this.collectChannelRequirements(),
            auto_approve: document.getElementById('autoApprove')?.checked || false
        };
    }

    collectChannelRequirements() {
        return this.selectedChannels.map(channel => ({
            channel_id: channel.id,
            custom_price: document.getElementById(`customPrice_${channel.id}`)?.value || null,
            posting_time: document.getElementById(`postingTime_${channel.id}`)?.value || null,
            special_requirements: document.getElementById(`requirements_${channel.id}`)?.value || null
        }));
    }

    validateOfferData(data) {
        const errors = [];

        if (!data.title || data.title.length < 10) {
            errors.push('Название должно содержать минимум 10 символов');
        }

        if (!data.description || data.description.length < 50) {
            errors.push('Описание должно содержать минимум 50 символов');
        }

        if (!data.category) {
            errors.push('Выберите категорию оффера');
        }

        if (data.budget < 1000) {
            errors.push('Минимальный бюджет: 1,000₽');
        }

        if (data.selected_channels.length === 0) {
            errors.push('Выберите хотя бы один канал');
        }

        const totalCost = this.selectedChannels.reduce((sum, ch) => sum + ch.data.price_per_post, 0);
        if (totalCost > data.budget) {
            errors.push(`Стоимость размещения (₽${this.formatNumber(totalCost)}) превышает бюджет`);
        }

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    showValidationErrors(errors) {
        const errorContainer = document.getElementById('validationErrors');
        errorContainer.innerHTML = `
            <div class="validation-errors">
                <h4>Исправьте ошибки:</h4>
                <ul>
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            </div>
        `;
        errorContainer.style.display = 'block';
        
        // Прокручиваем к ошибкам
        errorContainer.scrollIntoView({ behavior: 'smooth' });
    }

    showSubmissionProgress() {
        const submitBtn = document.getElementById('submitOfferBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <span class="spinner"></span>
                Создаем оффер...
            `;
        }
    }

    hideSubmissionProgress() {
        const submitBtn = document.getElementById('submitOfferBtn');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Создать оффер';
        }
    }

    showSuccessMessage(offerData) {
        const message = `
            <div class="success-message">
                <div class="success-icon">✅</div>
                <h3>Оффер успешно создан!</h3>
                <p>ID оффера: <strong>#${offerData.id}</strong></p>
                <p>Отправлено предложений: <strong>${offerData.proposals_sent}</strong></p>
                <p>Статус: <strong>${this.getStatusText(offerData.status)}</strong></p>
            </div>
        `;
        
        document.getElementById('submissionResult').innerHTML = message;
    }

    showErrorMessage(error) {
        const message = `
            <div class="error-message">
                <div class="error-icon">❌</div>
                <h3>Ошибка создания оффера</h3>
                <p>${error}</p>
                <button onclick="location.reload()" class="btn-retry">Попробовать снова</button>
            </div>
        `;
        
        document.getElementById('submissionResult').innerHTML = message;
    }

    getStatusText(status) {
        const statusMap = {
            'draft': 'Черновик',
            'pending': 'На модерации',
            'active': 'Активный',
            'rejected': 'Отклонен'
        };
        return statusMap[status] || status;
    }

    formatNumber(num) {
        return new Intl.NumberFormat('ru-RU').format(num);
    }

    resetForm() {
        document.getElementById('smartOfferForm')?.reset();
        this.selectedChannels = [];
        this.channelRecommendations = [];
        document.getElementById('channelRecommendations').innerHTML = '';
        document.getElementById('validationErrors').style.display = 'none';
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/offers/categories');
            if (response.ok) {
                const categories = await response.json();
                this.populateCategories(categories.data);
            }
        } catch (error) {
            console.error('Ошибка загрузки категорий:', error);
        }
    }

    populateCategories(categories) {
        const select = document.getElementById('offerCategory');
        if (!select) return;

        select.innerHTML = '<option value="">Выберите категорию</option>';
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            select.appendChild(option);
        });
    }

    initBudgetCalculator() {
        this.budgetCalculator = new BudgetCalculator();
    }
}

/**
 * Калькулятор бюджета и охвата
 */
class BudgetCalculator {
    constructor() {
        this.marketData = null;
        this.loadMarketData();
    }

    async loadMarketData() {
        try {
            const response = await fetch('/api/offers/market-data');
            if (response.ok) {
                this.marketData = await response.json();
            }
        } catch (error) {
            console.warn('Не удалось загрузить рыночные данные:', error);
        }
    }

    calculateOptimalBudget(category, targetReach) {
        const avgCPM = this.getAverageCPM(category);
        return Math.ceil(targetReach / 1000 * avgCPM);
    }

    suggestBudgetRange(category) {
        const baseCPM = this.getAverageCPM(category);
        return {
            min: baseCPM * 10, // 10k reach
            recommended: baseCPM * 50, // 50k reach
            max: baseCPM * 200 // 200k reach
        };
    }

    getAverageCPM(category) {
        // Базовые данные CPM по категориям (можно загружать с сервера)
        const cpmData = {
            'tech': 250,
            'business': 300,
            'lifestyle': 180,
            'entertainment': 150,
            'education': 200,
            'health': 280,
            'travel': 220,
            'food': 170,
            'fashion': 190,
            'sports': 160,
            'gaming': 140,
            'crypto': 400
        };
        
        return cpmData[category] || 200;
    }
}

// Глобальные функции для HTML
window.previewChannel = function(channelId) {
    // Показать превью канала в модальном окне
    console.log('Preview channel:', channelId);
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('smartOfferForm')) {
        window.smartOfferWizard = new SmartOfferWizard();
    }
});

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SmartOfferWizard, BudgetCalculator };
}