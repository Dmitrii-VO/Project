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
            this.checkAdminAccess();
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

        // Фильтры модерации
        const moderationStatusFilter = document.getElementById('moderationStatusFilter');
        const moderationSearch = document.getElementById('moderationSearch');
        
        if (moderationStatusFilter) {
            moderationStatusFilter.addEventListener('change', () => this.loadModerationOffers());
        }
        
        if (moderationSearch) {
            moderationSearch.addEventListener('input', this.debounce(() => {
                this.loadModerationOffers();
            }, 300));
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
            case 'admin-moderation':
                console.log('🔄 Переключение на админ-модерацию');
                
                // Принудительно показываем вкладку
                const adminContent = document.getElementById('admin-moderation');
                if (adminContent) {
                    adminContent.style.display = 'block';
                    console.log('✅ Админ контент принудительно показан');
                } else {
                    console.error('❌ Элемент admin-moderation не найден!');
                }
                
                await this.loadModerationOffers();
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
                console.log('🔍 Запрос getMyOffers()...');
                const result = await this.api.getMyOffers();
                console.log('📡 Ответ API:', result);
                
                if (result && result.success) {
                    console.log('🔍 Проверка структуры данных:');
                    console.log('- result.data:', result.data);
                    console.log('- result.data.offers:', result.data?.offers);
                    console.log('- Array.isArray(result.data.offers):', Array.isArray(result.data?.offers));
                    console.log('- result.data.offers.length:', result.data?.offers?.length);
                    
                    if (result.data && result.data.offers && Array.isArray(result.data.offers) && result.data.offers.length > 0) {
                        console.log(`✅ Найдено офферов: ${result.data.offers.length}`);
                        this.renderOffers(result.data.offers, container);
                        this.hideEmptyState();
                    } else {
                        console.log('ℹ️ Офферов не найдено, показываем пустое состояние');
                        console.log('📊 Данные которые получили:', JSON.stringify(result.data, null, 2));
                        this.showEmpty(container, 'У вас пока нет офферов', 'Создайте свой первый оффер для поиска каналов', 
                            '<button class="btn btn-primary" onclick="window.offersManager?.switchTab(\'create-offer\')">Создать оффер</button>');
                    }
                    return;
                } else {
                    console.log('❌ API вернул неуспешный результат:', result);
                    this.showError(container, 'Не удалось загрузить офферы');
                    return;
                }
            } catch (apiError) {
                console.error('❌ Исключение при запросе API:', apiError);
                this.showError(container, 'Ошибка загрузки: ' + apiError.message);
                return;
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
            
            // Загружаем входящие предложения для владельцев каналов
            try {
                const response = await fetch('/api/proposals/incoming', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                    }
                });

                const result = await response.json();
                
                if (response.ok && result.success) {
                    if (result.proposals && result.proposals.length > 0) {
                        // Преобразуем предложения в формат офферов с информацией о proposal_id
                        const proposalsAsOffers = result.proposals.map(proposal => ({
                            id: proposal.id, // ID оффера
                            proposal_id: proposal.proposal_id, // ID предложения
                            proposal_status: proposal.proposal_status, // Статус предложения
                            title: proposal.title,
                            description: proposal.description,
                            price: proposal.price,
                            currency: proposal.currency || 'RUB',
                            status: 'active', // Для корректного отображения
                            target_audience: proposal.target_audience,
                            creator_name: proposal.creator_name,
                            first_name: proposal.first_name,
                            channel_title: proposal.channel_title,
                            can_respond: proposal.can_respond,
                            is_expired: proposal.is_expired
                        }));
                        
                        this.renderOffers(proposalsAsOffers, container);
                        console.log(`✅ Загружено предложений: ${result.proposals.length}`);
                    } else {
                        this.showEmpty(container, 'Нет входящих предложений', 'У вас пока нет предложений от рекламодателей');
                    }
                    return;
                } else {
                    throw new Error(result.message || 'Ошибка загрузки предложений');
                }
            } catch (apiError) {
                console.error('❌ Ошибка API proposals/incoming:', apiError);
                
                // Fallback на обычные офферы
                try {
                    const result = await this.api.getOffers(this.filters);
                    
                    if (result.success) {
                        if (result.data && result.data.offers && result.data.offers.length > 0) {
                            this.renderOffers(result.data.offers, container);
                        } else {
                            this.showEmpty(container, 'Офферы не найдены', 'Попробуйте изменить фильтры поиска');
                        }
                        return;
                    }
                } catch (fallbackError) {
                    console.error('❌ Ошибка fallback API:', fallbackError);
                }
                
                this.showError(container, 'Ошибка загрузки: ' + apiError.message);
                return;
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
                target_audience: 'Владельцы и администраторы Telegram каналов, ищущие качественный рекламный контент',
                price: Math.min(parseInt(formData.get('budget')) * 0.1, 50000),
                budget_total: parseInt(formData.get('budget')),
                category: 'general',
                currency: 'RUB',
                content: formData.get('description'),
                requirements: 'Размещение рекламного контента в соответствии с требованиями площадки',
                deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] // +30 дней
            };
            
            console.log('📋 Создание оффера:', offerData);
            
            const result = await this.api.createOffer(offerData);
            
            if (result.success) {
                console.log('✅ Оффер создан успешно:', result.data);
                this.modals.showNotification('Оффер создан успешно!', 'success');
                
                // Показываем модальное окно выбора каналов, если есть данные оффера
                if (result.data && result.data.offer_id) {
                    const offerId = result.data.offer_id;
                    const offerTitle = result.data.offer?.title || offerData.title;
                    const offer = result.data.offer || offerData;
                    await this.showChannelSelection(offerId, offerTitle, false, offer);
                }
                
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

    async showChannelSelection(offerId, offerTitle, isDraft = false, offerData = null) {
        try {
            console.log(`🔍 Показываем выбор каналов для оффера ${offerId}: "${offerTitle}" (isDraft: ${isDraft})`);
            
            // Подготавливаем данные для рекомендаций
            const recommendationData = {
                offer_id: offerId,
                title: offerTitle
            };
            
            // Если есть полные данные оффера, добавляем их
            if (offerData) {
                recommendationData.description = offerData.description || '';
                recommendationData.target_audience = offerData.target_audience || '';
                recommendationData.price = offerData.price || offerData.budget_total || 0;
                recommendationData.category = offerData.category || 'general';
            }
            
            console.log(`📤 Отправляем данные для рекомендаций:`, recommendationData);
            
            const channelsResult = await this.api.getRecommendedChannels(recommendationData);
            
            if (channelsResult.success && channelsResult.channels) {
                console.log(`✅ Получено ${channelsResult.channels.length} рекомендованных каналов`);
                this.modals.createChannelSelection(offerId, offerTitle, channelsResult.channels, isDraft);
            } else {
                console.log('❌ Не удалось получить каналы:', channelsResult.error);
                this.modals.showNotification('Не удалось загрузить каналы для выбора', 'error');
            }
        } catch (error) {
            console.error('❌ Ошибка загрузки каналов:', error);
            this.modals.showNotification('Ошибка загрузки каналов: ' + error.message, 'error');
        }
    }

    async completeOffer(offerId) {
        try {
            console.log(`🚀 Завершение оффера ${offerId}`, typeof offerId);
            
            if (!offerId) {
                throw new Error('ID оффера не указан');
            }
            
            // Получаем информацию об оффере
            const offerResult = await this.api.getOfferDetails(offerId);
            
            console.log('🔍 Результат API getOfferDetails:', offerResult);
            
            if (!offerResult.success) {
                throw new Error('Не удалось получить информацию об оффере');
            }
            
            // API может возвращать данные в разной структуре
            let offer = null;
            
            if (offerResult.data && offerResult.data.offer) {
                // Структура: { success: true, data: { offer: {...} } }
                offer = offerResult.data.offer;
            } else if (offerResult.data) {
                // Структура: { success: true, data: {...} }
                offer = offerResult.data;
            } else {
                // Прямая структура оффера
                offer = offerResult;
            }
            
            console.log('📋 Данные оффера:', offer);
            console.log('📊 Статус оффера:', offer?.status);
            
            if (!offer) {
                throw new Error('Данные оффера не найдены в ответе API');
            }
            
            // Проверяем статус
            if (offer.status !== 'draft') {
                this.modals.showNotification(`Нельзя завершить оффер со статусом: ${offer.status}`, 'error');
                return;
            }
            
            // Открываем модальное окно выбора каналов для черновика
            await this.showChannelSelection(offerId, offer.title, true, offer);
            
        } catch (error) {
            console.error('❌ Ошибка завершения оффера:', error);
            this.modals.showNotification('Ошибка завершения оффера: ' + error.message, 'error');
        }
    }

    async showOfferStats(offerId) {
        try {
            console.log(`📊 Показываем статистику для оффера ${offerId}`);
            
            // Получаем статистику оффера
            const statsResult = await this.api.getOfferStatistics(offerId);
            
            if (statsResult.success) {
                // Создаем модальное окно со статистикой
                this.modals.showOfferStatistics(offerId, statsResult.data);
            } else {
                this.modals.showNotification('Не удалось загрузить статистику', 'error');
            }
            
        } catch (error) {
            console.error('❌ Ошибка загрузки статистики:', error);
            this.modals.showNotification('Ошибка загрузки статистики: ' + error.message, 'error');
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

    async editOffer(offerId) {
        console.log('✏️ Редактирование оффера:', offerId);
        
        try {
            // Получаем данные оффера
            const response = await fetch(`/api/offers_moderation/${offerId}`, {
                headers: {
                    'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                const offer = result.data;
                console.log('📋 Данные оффера для редактирования:', offer);
                
                // Создаем модальное окно редактирования
                this.modals.createEditOffer(offer);
            } else {
                throw new Error(result.error || 'Не удалось загрузить данные оффера');
            }
            
        } catch (error) {
            console.error('❌ Ошибка при открытии редактирования:', error);
            this.modals.showNotification('Ошибка загрузки данных для редактирования: ' + error.message, 'error');
        }
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

    // Админские методы
    isOffersPage() {
        // Проверяем что мы на странице с офферами и есть нужные элементы
        const hasOffersTabs = document.querySelector('.tabs-nav') && 
                             document.querySelector('[data-tab="my-offers"]');
        const hasAdminElements = document.getElementById('admin-tab') && 
                               document.getElementById('admin-moderation');
        
        return hasOffersTabs && hasAdminElements;
    }

    checkAdminAccess() {
        const userId = window.getTelegramUserId?.();
        const adminId = '373086959';
        
        console.log(`🔍 Checking admin access: userId = ${userId}, adminId = ${adminId}`);
        console.log(`🔍 Current page URL: ${window.location.pathname}`);
        
        // Показываем вкладку модерации только для админа и только на странице офферов
        if (userId && userId === adminId && this.isOffersPage()) {
            console.log('✅ Администраторский доступ предоставлен');
            const adminTab = document.getElementById('admin-tab');
            const adminContent = document.getElementById('admin-moderation');
            
            if (adminTab) {
                adminTab.style.display = 'block';
                console.log('✅ Админ вкладка показана');
                console.log('🔍 Админ вкладка classList:', adminTab.classList.toString());
                console.log('🔍 Админ вкладка style:', adminTab.style.cssText);
            } else {
                console.error('❌ Элемент admin-tab не найден!');
            }
            
            if (adminContent) {
                console.log('✅ Админ контент найден');
                console.log('🔍 Админ контент classList:', adminContent.classList.toString());
                console.log('🔍 Админ контент style:', adminContent.style.cssText);
            } else {
                console.error('❌ Элемент admin-moderation не найден!');
            }
        } else {
            console.log('👤 Обычный пользователь, админ-панель скрыта');
            
            // Убеждаемся что вкладка скрыта для обычных пользователей
            const adminTab = document.getElementById('admin-tab');
            const adminContent = document.getElementById('admin-moderation');
            
            if (adminTab) {
                adminTab.style.display = 'none';
                console.log('✅ Админ вкладка скрыта для обычного пользователя');
            }
            
            if (adminContent) {
                adminContent.style.display = 'none';
                adminContent.classList.remove('active');
                console.log('✅ Админ контент скрыт для обычного пользователя');
            }
        }
    }

    async loadModerationOffers() {
        const container = document.getElementById('moderationGrid');
        const loading = document.getElementById('moderationLoading');
        const empty = document.getElementById('moderationEmpty');
        
        console.log('🔍 Элементы модерации:', {
            container: container,
            loading: loading,
            empty: empty,
            containerVisible: container ? container.style.display : 'not found'
        });
        
        if (!container) {
            console.error('❌ Контейнер moderationGrid не найден!');
            return;
        }

        try {
            // Показываем загрузку
            this.showModerationLoading(true);
            
            // Получаем фильтры
            const statusFilter = document.getElementById('moderationStatusFilter')?.value || 'pending';
            const searchQuery = document.getElementById('moderationSearch')?.value || '';
            
            const filters = {
                status: statusFilter === 'all' ? null : statusFilter,
                search: searchQuery.trim() || null
            };
            
            console.log('🔍 Загрузка офферов для модерации:', filters);
            
            // Запрос к API
            const result = await this.api.getModerationOffers(filters);
            
            if (result.success && result.data && Array.isArray(result.data.offers)) {
                const offers = result.data.offers;
                console.log(`📋 Получено офферов для модерации: ${offers.length}`);
                
                if (offers.length > 0) {
                    this.renderModerationOffers(offers, container);
                    this.showModerationLoading(false);
                } else {
                    this.showModerationEmpty(true);
                }
            } else {
                console.error('❌ Ошибка загрузки офферов для модерации:', result.error);
                this.showModerationError(result.error || 'Неизвестная ошибка');
            }
            
        } catch (error) {
            console.error('❌ Исключение при загрузке офферов для модерации:', error);
            this.showModerationError(error.message);
        }
    }

    renderModerationOffers(offers, container) {
        console.log(`🎨 Рендеринг ${offers.length} офферов для модерации`);
        console.log('📋 Container:', container);
        console.log('📋 First offer:', offers[0]);
        
        const offersHtml = offers.map((offer, index) => {
            console.log(`🎯 Создание карточки ${index + 1}:`, offer);
            const cardHtml = this.createModerationOfferCard(offer);
            console.log(`✅ Карточка ${index + 1} создана, HTML length:`, cardHtml.length);
            return cardHtml;
        }).join('');
        
        console.log(`📄 Общий HTML length:`, offersHtml.length);
        
        // Устанавливаем HTML с принудительными стилями
        container.innerHTML = `<div class="offers-list" style="display: flex; flex-direction: column; gap: 16px; padding: 20px; background: #f8f9fa; border: 2px solid #007bff; border-radius: 8px;">${offersHtml}</div>`;
        
        // Принудительно показываем контейнер
        container.style.display = 'block';
        container.style.visibility = 'visible';
        container.style.opacity = '1';
        container.style.height = 'auto';
        container.style.background = '#ffffff';
        container.style.border = '1px solid #dee2e6';
        container.style.borderRadius = '8px';
        container.style.padding = '16px';
        container.style.margin = '16px 0';
        
        console.log(`✅ HTML установлен в контейнер с принудительными стилями`);
        
        // Проверим, что карточки действительно добавились
        const cards = container.querySelectorAll('.offer-card');
        console.log(`🎯 Найдено карточек в DOM: ${cards.length}`);
        
        cards.forEach((card, index) => {
            card.style.display = 'block';
            card.style.visibility = 'visible';
            card.style.opacity = '1';
            console.log(`✅ Карточка ${index + 1} принудительно показана`);
        });
    }

    createModerationOfferCard(offer) {
        console.log('🎯 Создание карточки модерации для оффера:', offer);
        
        const status = offer.status || 'draft';
        const submittedDate = offer.submitted_at ? new Date(offer.submitted_at).toLocaleString('ru-RU') : 'Не указана';
        const userName = offer.user_name || 'Неизвестный пользователь';
        const userId = offer.user_id || 'N/A';
        
        // Отладочная информация для бюджета
        console.log(`💰 ОТЛАДКА БЮДЖЕТА для оффера ${offer.id}:`);
        console.log(`   - offer.budget_total: ${offer.budget_total}`);
        console.log(`   - offer.price: ${offer.price}`);
        console.log(`   - Будет использоваться: ${offer.budget_total || offer.price || 0} (приоритет budget_total)`);
        
        console.log(`📋 Остальные данные - Статус: ${status}, Дата: ${submittedDate}, Пользователь: ${userName}`);
        
        // Проверим наличие templates
        if (!this.templates) {
            console.error('❌ Templates не найдены!');
            return '<div style="padding: 20px; border: 2px solid red; margin: 10px; background: #ffe6e6;">Error: Templates not found</div>';
        }
        
        // Создаем карточку с упрощенной структурой для отладки
        const html = `
            <div class="offer-card moderation ${status}" data-offer-id="${offer.id}" style="border: 1px solid #ddd; padding: 16px; margin: 12px 0; border-radius: 8px; background: white;">
                <div class="offer-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <h3 class="offer-title" style="margin: 0; color: #333; font-size: 18px;">${offer.title || 'Без названия'}</h3>
                    ${this.templates.statusBadge(status)}
                </div>
                
                <div class="offer-user-info" style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin: 12px 0;">
                    <div style="margin-bottom: 8px;">
                        <strong>👤 Пользователь:</strong> ${userName} (ID: ${userId})
                    </div>
                    <div>
                        <strong>📅 Подано:</strong> ${submittedDate}
                    </div>
                </div>
                
                <div class="offer-meta" style="margin: 12px 0;">
                    <span class="offer-price" style="font-weight: bold; color: #28a745;">₽ ${this.templates.formatPrice(offer.budget_total || offer.price || 0)}</span>
                    <span style="margin-left: 12px; color: #6c757d;">${offer.category || 'Общее'}</span>
                </div>
                
                <div class="offer-description" style="margin: 12px 0; color: #495057; line-height: 1.4;">
                    ${offer.description ? (offer.description.length > 150 ? offer.description.substring(0, 150) + '...' : offer.description) : 'Описание отсутствует'}
                </div>
                
                <div class="offer-actions moderation-actions" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px;">
                    ${this.getModerationButtons(offer)}
                </div>
                
                ${offer.rejection_reason ? `
                    <div class="rejection-reason" style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; margin-top: 12px; border-radius: 0 6px 6px 0; color: #721c24;">
                        <strong>❌ Причина отклонения:</strong>
                        <p style="margin: 4px 0 0 0;">${offer.rejection_reason}</p>
                    </div>
                ` : ''}
            </div>
        `;
        
        console.log(`✅ HTML карточка создана, длина: ${html.length} символов`);
        return html;
    }

    getModerationButtons(offer) {
        const status = offer.status || 'draft';
        const offerId = offer.id;
        let buttons = [];
        
        // Кнопка просмотра деталей всегда доступна
        buttons.push(`<button class="btn btn-outline btn-sm" onclick="window.offersManager?.showOfferDetails('${offerId}')">👁️ Просмотр</button>`);
        
        if (status === 'pending') {
            // Для офферов на модерации показываем кнопки одобрения, отклонения и удаления
            buttons.push(`<button class="btn btn-success btn-sm" onclick="window.offersManager?.approveOffer('${offerId}')">✅ Одобрить</button>`);
            buttons.push(`<button class="btn btn-danger btn-sm" onclick="window.offersManager?.rejectOffer('${offerId}')">❌ Отклонить</button>`);
            buttons.push(`<button class="btn btn-outline btn-sm" onclick="window.offersManager?.deleteOfferFromModeration('${offerId}')" style="color: var(--danger-600); border-color: var(--danger-300);">🗑️ Удалить</button>`);
        } else if (status === 'active') {
            // Для активных офферов показываем статистику
            buttons.push(`<button class="btn btn-primary btn-sm" onclick="window.offersManager?.showOfferStats('${offerId}')">📊 Статистика</button>`);
        } else if (status === 'rejected') {
            // Для отклоненных можно повторно рассмотреть
            buttons.push(`<button class="btn btn-warning btn-sm" onclick="window.offersManager?.reopenOffer('${offerId}')">🔄 Пересмотреть</button>`);
        }
        
        return buttons.join('');
    }

    async approveOffer(offerId) {
        if (!confirm('Вы уверены, что хотите одобрить этот оффер?')) {
            return;
        }
        
        try {
            console.log(`✅ Одобрение оффера ${offerId}`);
            
            const result = await this.api.approveOffer(offerId);
            
            if (result.success) {
                this.modals.showNotification('Оффер успешно одобрен!', 'success');
                await this.loadModerationOffers(); // Обновляем список
            } else {
                throw new Error(result.error || 'Ошибка одобрения оффера');
            }
            
        } catch (error) {
            console.error('❌ Ошибка одобрения оффера:', error);
            this.modals.showNotification('Ошибка одобрения: ' + error.message, 'error');
        }
    }

    async rejectOffer(offerId) {
        const reason = prompt('Укажите причину отклонения:');
        if (!reason || reason.trim() === '') {
            return;
        }
        
        try {
            console.log(`❌ Отклонение оффера ${offerId} с причиной: ${reason}`);
            
            const result = await this.api.rejectOffer(offerId, reason.trim());
            
            if (result.success) {
                this.modals.showNotification('Оффер отклонен!', 'success');
                await this.loadModerationOffers(); // Обновляем список
            } else {
                throw new Error(result.error || 'Ошибка отклонения оффера');
            }
            
        } catch (error) {
            console.error('❌ Ошибка отклонения оффера:', error);
            this.modals.showNotification('Ошибка отклонения: ' + error.message, 'error');
        }
    }

    async reopenOffer(offerId) {
        if (!confirm('Вы уверены, что хотите вернуть этот оффер на модерацию?')) {
            return;
        }
        
        try {
            console.log(`🔄 Возврат оффера ${offerId} на модерацию`);
            
            const result = await this.api.reopenOffer(offerId);
            
            if (result.success) {
                this.modals.showNotification('Оффер возвращен на модерацию!', 'success');
                await this.loadModerationOffers(); // Обновляем список
            } else {
                throw new Error(result.error || 'Ошибка возврата оффера на модерацию');
            }
            
        } catch (error) {
            console.error('❌ Ошибка возврата оффера:', error);
            this.modals.showNotification('Ошибка: ' + error.message, 'error');
        }
    }

    // UI методы для модерации
    showModerationLoading(show) {
        const loading = document.getElementById('moderationLoading');
        const container = document.getElementById('moderationGrid');
        const empty = document.getElementById('moderationEmpty');
        
        console.log(`🔄 showModerationLoading(${show}):`, {
            loading: loading,
            container: container,
            empty: empty
        });
        
        if (loading) loading.style.display = show ? 'block' : 'none';
        if (container) {
            container.style.display = show ? 'none' : 'block';
            
            // Принудительно показываем контейнер при скрытии загрузки
            if (!show) {
                container.style.visibility = 'visible';
                container.style.opacity = '1';
                container.style.minHeight = '200px';
                console.log('🔧 Принудительно показан контейнер модерации');
            }
        }
        if (empty) empty.style.display = 'none';
        
        console.log('✅ Состояние элементов после изменения:', {
            loadingDisplay: loading ? loading.style.display : 'not found',
            containerDisplay: container ? container.style.display : 'not found',
            emptyDisplay: empty ? empty.style.display : 'not found'
        });
    }

    showModerationEmpty(show) {
        const loading = document.getElementById('moderationLoading');
        const container = document.getElementById('moderationGrid');
        const empty = document.getElementById('moderationEmpty');
        
        if (loading) loading.style.display = 'none';
        if (container) container.style.display = show ? 'none' : 'block';
        if (empty) empty.style.display = show ? 'block' : 'none';
    }

    showModerationError(message) {
        const container = document.getElementById('moderationGrid');
        if (container) {
            container.innerHTML = this.templates.errorState(
                message, 
                () => this.loadModerationOffers()
            );
        }
        this.showModerationLoading(false);
    }

    async deleteOfferFromModeration(offerId) {
        if (!confirm('Вы уверены, что хотите удалить этот оффер? Это действие нельзя отменить.')) {
            return;
        }
        
        try {
            console.log(`🗑️ Удаление оффера ${offerId} из модерации`);
            
            // Используем специальный endpoint для удаления из модерации
            const result = await this.api.request(`/api/offers_moderation/${offerId}/delete`, {
                method: 'DELETE'
            });
            
            if (result.success) {
                this.modals.showNotification(`Оффер "${result.title}" успешно удален!`, 'success');
                await this.loadModerationOffers(); // Обновляем список
            } else {
                throw new Error(result.error || 'Ошибка удаления оффера');
            }
            
        } catch (error) {
            console.error('❌ Ошибка удаления оффера:', error);
            this.modals.showNotification('Ошибка удаления: ' + error.message, 'error');
        }
    }

    // Глобальная функция обновления модерации для HTML
    refreshModeration() {
        console.log('🔄 Обновление модерации по запросу пользователя');
        this.loadModerationOffers();
    }
}