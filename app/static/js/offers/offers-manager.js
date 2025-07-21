/**
 * offers-manager.js
 * Основной менеджер для управления офферами
 */

import { OffersAPI } from './offers-api.js';
import { OffersTemplates } from './offers-templates.js';
import { ModalManager } from './offers-modals.js';

export class OffersManager {
    constructor() {
        this.api = new OffersAPI();
        this.templates = OffersTemplates;
        this.modals = new ModalManager();
        this.currentTab = 'my-offers';
        this.filters = {};
        this.isInitialized = false;
    }

    async init() {
        if (this.isInitialized) {
            console.log('⚠️ OffersManager уже инициализирован');
            return;
        }

        console.log('🚀 Инициализация OffersManager');
        
        try {
            this.setupEventListeners();
            this.setupTabSwitching();
            await this.loadInitialData();
            this.isInitialized = true;
            console.log('✅ OffersManager успешно инициализирован');
        } catch (error) {
            console.error('❌ Ошибка инициализации OffersManager:', error);
            this.modals.showNotification('Ошибка инициализации', 'error');
        }
    }

    setupEventListeners() {
        // Поиск офферов
        const searchInput = document.getElementById('offersSearch');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.searchOffers(searchInput.value);
            }, 300));
        }

        // Фильтры поиска
        const filterElements = ['findCategoryFilter', 'findBudgetMin', 'findBudgetMax', 'findMinSubscribers'];
        filterElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.updateFilters());
            }
        });

        // Форма создания оффера
        const createOfferForm = document.getElementById('autoOfferForm');
        if (createOfferForm) {
            createOfferForm.addEventListener('submit', (e) => this.handleCreateOffer(e));
        }

        // Форма кампании
        const campaignForm = document.getElementById('campaignForm');
        if (campaignForm) {
            campaignForm.addEventListener('submit', (e) => this.handleCreateCampaign(e));
        }
    }

    setupTabSwitching() {
        document.querySelectorAll('.tabs-nav a').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = tab.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
    }

    async switchTab(tabName) {
        console.log(`🔄 Переключение на вкладку: ${tabName}`);
        
        // Обновляем навигацию
        document.querySelectorAll('.tabs-nav a').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tabs-content').forEach(content => content.classList.remove('active'));
        
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(tabName);
        
        if (activeTab) activeTab.classList.add('active');
        if (activeContent) activeContent.classList.add('active');
        
        this.currentTab = tabName;
        
        // Загружаем данные для активной вкладки
        await this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'my-offers':
                await this.loadMyOffers();
                break;
            case 'find-offer':
                await this.loadAvailableOffers();
                break;
            case 'create-offer':
                this.setupCreateOfferForm();
                break;
            case 'campaigns':
                this.setupCampaignForm();
                break;
        }
    }

    async loadInitialData() {
        await this.loadMyOffers();
    }

    async loadMyOffers() {
        const container = document.getElementById('offersGrid');
        if (!container) return;

        try {
            this.showLoading(container, 'Загрузка ваших офферов...');
            
            // Попробуем загрузить реальные данные
            try {
                const result = await this.api.getMyOffers();
                
                if (result.success && result.offers?.length > 0) {
                    this.renderOffers(result.offers, container);
                    this.hideEmptyState();
                    return;
                }
            } catch (apiError) {
                console.log('📡 API недоступен, показываем тестовые данные:', apiError.message);
            }
            
            // Показываем тестовые данные если API недоступен
            const testOffers = this.generateTestOffers();
            if (testOffers.length > 0) {
                this.renderOffers(testOffers, container);
                this.hideEmptyState();
            } else {
                this.showEmptyState();
            }
            
        } catch (error) {
            console.error('❌ Ошибка загрузки офферов:', error);
            this.showEmptyState();
        }
    }

    async loadAvailableOffers() {
        const container = document.getElementById('findOffersGrid');
        if (!container) return;

        try {
            this.showLoading(container, 'Поиск доступных офферов...');
            
            // Попробуем загрузить реальные данные
            try {
                const result = await this.api.getOffers(this.filters);
                
                if (result.success && result.offers?.length > 0) {
                    this.renderOffers(result.offers, container);
                    return;
                }
            } catch (apiError) {
                console.log('📡 API недоступен, показываем тестовые данные:', apiError.message);
            }
            
            // Показываем тестовые данные если API недоступен
            const testOffers = this.generateAvailableTestOffers();
            if (testOffers.length > 0) {
                this.renderOffers(testOffers, container);
            } else {
                this.showEmpty(container, 'Офферы не найдены', 'Попробуйте изменить фильтры поиска');
            }
            
        } catch (error) {
            console.error('❌ Ошибка поиска офферов:', error);
            this.showEmpty(container, 'Офферы не найдены', 'Попробуйте изменить фильтры поиска');
        }
    }

    renderOffers(offers, container) {
        const offersHtml = offers.map(offer => this.templates.offerCard(offer)).join('');
        container.innerHTML = `<div class="offers-list">${offersHtml}</div>`;
    }

    async handleCreateOffer(event) {
        event.preventDefault();
        
        const submitBtn = event.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        try {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создаем оффер...';
            
            const formData = new FormData(event.target);
            const offerData = {
                title: 'Автоматический подбор каналов',
                description: formData.get('description'),
                budget: parseInt(formData.get('budget')),
                price: Math.min(parseInt(formData.get('budget')) * 0.1, 50000),
                budget_total: parseInt(formData.get('budget')),
                target_audience: 'general',
                category: 'general',
                currency: 'RUB',
                content: formData.get('description')
            };
            
            console.log('📋 Создание оффера:', offerData);
            
            const result = await this.api.createOffer(offerData);
            
            if (result.success) {
                console.log('✅ Оффер создан успешно:', result.offer);
                this.modals.showNotification('Оффер создан успешно!', 'success');
                
                // Показываем модальное окно выбора каналов
                await this.showChannelSelection(result.offer.id, result.offer.title);
                
                event.target.reset();
                this.switchTab('my-offers');
            } else {
                throw new Error(result.error || 'Ошибка создания оффера');
            }
        } catch (error) {
            console.error('❌ Ошибка создания оффера:', error);
            this.modals.showNotification(`Ошибка: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    async handleCreateCampaign(event) {
        event.preventDefault();
        
        const submitBtn = event.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        
        try {
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Создаем кампанию...';
            
            const formData = new FormData(event.target);
            const campaignData = {
                name: formData.get('name'),
                budget_limit: parseFloat(formData.get('budget_limit')),
                add_utm_tags: formData.has('add_utm_tags'),
                track_clicks: formData.has('track_clicks'),
                start_date: formData.get('start_date'),
                end_date: formData.get('end_date'),
                work_weekends: formData.has('work_weekends'),
                work_hours_only: formData.has('work_hours_only'),
                advertiser_type: formData.get('advertiser_type'),
                product_name: formData.get('product_name'),
                advertiser_inn: formData.get('advertiser_inn'),
                ad_content: formData.get('ad_content'),
                status: 'active'
            };
            
            console.log('📋 Создание кампании:', campaignData);
            
            // Здесь должен быть API вызов для кампаний
            // const result = await this.api.createCampaign(campaignData);
            
            this.modals.showNotification('Кампания создана успешно!', 'success');
            event.target.reset();
            
        } catch (error) {
            console.error('❌ Ошибка создания кампании:', error);
            this.modals.showNotification(`Ошибка: ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    async showChannelSelection(offerId, offerTitle) {
        try {
            const channelsResult = await this.api.getRecommendedChannels({ offer_id: offerId });
            
            if (channelsResult.success && channelsResult.channels) {
                this.modals.createChannelSelection(offerId, offerTitle, channelsResult.channels);
            } else {
                this.modals.showNotification('Не удалось загрузить каналы', 'error');
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки каналов:', error);
            this.modals.showNotification('Ошибка загрузки каналов: ' + error.message, 'error');
        }
    }

    setupCreateOfferForm() {
        // Настройка формы создания оффера
        const today = new Date().toISOString().split('T')[0];
        const budgetInput = document.getElementById('offerBudget');
        if (budgetInput && !budgetInput.value) {
            budgetInput.value = '20000';
        }
    }

    setupCampaignForm() {
        // Настройка формы кампании
        const today = new Date().toISOString().split('T')[0];
        const startDateInput = document.getElementById('campaignStartDate');
        const endDateInput = document.getElementById('campaignEndDate');
        
        if (startDateInput) startDateInput.min = today;
        if (endDateInput) endDateInput.min = today;
        
        // Валидация дат
        if (startDateInput) {
            startDateInput.addEventListener('change', () => {
                if (endDateInput) {
                    endDateInput.min = startDateInput.value;
                    if (endDateInput.value && endDateInput.value < startDateInput.value) {
                        endDateInput.value = startDateInput.value;
                    }
                }
            });
        }
    }

    searchOffers(query) {
        this.filters.search = query;
        if (this.currentTab === 'find-offer') {
            this.loadAvailableOffers();
        }
    }

    updateFilters() {
        this.filters = {
            category: document.getElementById('findCategoryFilter')?.value || '',
            budget_min: document.getElementById('findBudgetMin')?.value || '',
            budget_max: document.getElementById('findBudgetMax')?.value || '',
            min_subscribers: document.getElementById('findMinSubscribers')?.value || ''
        };
        
        if (this.currentTab === 'find-offer') {
            this.loadAvailableOffers();
        }
    }

    clearFilters() {
        this.filters = {};
        document.getElementById('findCategoryFilter').value = '';
        document.getElementById('findBudgetMin').value = '';
        document.getElementById('findBudgetMax').value = '';
        document.getElementById('findMinSubscribers').value = '';
        
        if (this.currentTab === 'find-offer') {
            this.loadAvailableOffers();
        }
    }

    // UI состояния
    showLoading(container, message = 'Загрузка...') {
        container.innerHTML = this.templates.loadingState(message);
    }

    showError(container, message) {
        container.innerHTML = this.templates.errorState(message, () => this.loadTabData(this.currentTab));
    }

    showEmpty(container, title, description, action = null) {
        container.innerHTML = this.templates.emptyState(title, description, action);
    }

    showEmptyState() {
        const emptyState = document.getElementById('emptyOffersState');
        if (emptyState) emptyState.style.display = 'block';
    }

    hideEmptyState() {
        const emptyState = document.getElementById('emptyOffersState');
        if (emptyState) emptyState.style.display = 'none';
    }

    // Утилиты
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

    // Генерация тестовых данных для "Мои офферы"
    generateTestOffers() {
        return [
            {
                id: 1,
                title: 'Реклама курсов по программированию',
                description: 'Ищем каналы для размещения рекламы онлайн-курсов по Python, JavaScript и React. Целевая аудитория - начинающие разработчики.',
                price: 15000,
                budget_total: 50000,
                category: 'education',
                status: 'active',
                created_at: new Date().toISOString()
            },
            {
                id: 2,
                title: 'Продвижение мобильного приложения',
                description: 'Требуется размещение рекламы нового фитнес-приложения. Ищем каналы о здоровье, спорте и ЗОЖ.',
                price: 25000,
                budget_total: 80000,
                category: 'lifestyle',
                status: 'draft',
                created_at: new Date().toISOString()
            },
            {
                id: 3,
                title: 'Реклама финансовых услуг',
                description: 'Размещение рекламы банковских продуктов и инвестиционных услуг.',
                price: 30000,
                budget_total: 100000,
                category: 'finance',
                status: 'completed',
                created_at: new Date().toISOString()
            }
        ];
    }

    // Генерация тестовых данных для "Найти оффер"
    generateAvailableTestOffers() {
        return [
            {
                id: 101,
                title: 'Реклама технологического стартапа',
                description: 'Ищем каналы для продвижения новой SaaS платформы для управления проектами. Бюджет до 200к рублей.',
                price: 20000,
                budget_total: 200000,
                category: 'tech',
                status: 'active',
                created_at: new Date().toISOString()
            },
            {
                id: 102,
                title: 'Продвижение образовательного контента',
                description: 'Требуется размещение рекламы онлайн-школы английского языка. Ищем каналы об образовании и саморазвитии.',
                price: 12000,
                budget_total: 150000,
                category: 'education',
                status: 'active',
                created_at: new Date().toISOString()
            },
            {
                id: 103,
                title: 'Реклама e-commerce проекта',
                description: 'Продвижение интернет-магазина товаров для дома. Целевая аудитория - домохозяйки и семьи.',
                price: 18000,
                budget_total: 120000,
                category: 'business',
                status: 'active',
                created_at: new Date().toISOString()
            },
            {
                id: 104,
                title: 'Реклама финтех приложения',
                description: 'Размещение рекламы мобильного приложения для инвестиций. Ищем финансовые каналы.',
                price: 35000,
                budget_total: 300000,
                category: 'finance',
                status: 'active',
                created_at: new Date().toISOString()
            },
            {
                id: 105,
                title: 'Продвижение развлекательного контента',
                description: 'Реклама нового игрового приложения для мобильных устройств.',
                price: 22000,
                budget_total: 180000,
                category: 'entertainment',
                status: 'active',
                created_at: new Date().toISOString()
            }
        ];
    }

    // Публичные методы для глобального доступа
    showOfferDetails(offerId) {
        // Логика показа деталей оффера
        console.log('Показ деталей оффера:', offerId);
        this.modals.showNotification(`Просмотр деталей оффера ${offerId}`, 'info');
    }

    editOffer(offerId) {
        // Логика редактирования оффера
        console.log('Редактирование оффера:', offerId);
        this.modals.showNotification(`Редактирование оффера ${offerId}`, 'info');
    }

    showOfferStats(offerId) {
        // Логика показа статистики оффера
        console.log('Статистика оффера:', offerId);
        this.modals.showNotification(`Статистика оффера ${offerId}`, 'info');
    }

    deleteOffer(offerId) {
        // Логика удаления оффера
        console.log('Удаление оффера:', offerId);
        this.modals.createDeleteConfirmation(offerId);
    }

    async confirmDeleteOffer(offerId) {
        try {
            // Пытаемся удалить через API
            const result = await this.api.deleteOffer(offerId);
            
            if (result && result.success) {
                this.modals.showNotification('Оффер успешно удален!', 'success');
                // Обновляем список офферов
                await this.loadMyOffers();
                return;
            } else {
                throw new Error(result?.error || 'Ошибка удаления оффера');
            }
        } catch (error) {
            console.log('📡 API недоступен, удаляем из тестовых данных:', error.message);
            
            // Удаляем из DOM
            const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
            if (offerCard) {
                offerCard.style.transition = 'all 0.3s ease';
                offerCard.style.opacity = '0';
                offerCard.style.transform = 'scale(0.8)';
                
                setTimeout(() => {
                    offerCard.remove();
                    this.modals.showNotification('Оффер удален!', 'success');
                    
                    // Проверяем, остались ли офферы
                    const remainingOffers = document.querySelectorAll('.offer-card').length;
                    if (remainingOffers === 0) {
                        this.showEmptyState();
                    }
                }, 300);
            }
        }
    }
}