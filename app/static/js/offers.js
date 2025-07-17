// app/static/js/offers.js - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ

// ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
let offersManager = null;

// ===== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP =====
if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// ===== HTML ШАБЛОНЫ =====
const Templates = {
    statusBadge(status, text) {
        const statusTexts = {
            active: '✅ Активен',
            draft: '📝 Черновик', 
            completed: '✅ Завершен',
            paused: '⏸️ Приостановлен'
        };
        const displayText = text || statusTexts[status] || statusTexts.active;
        return `<span class="status-badge ${status}">${displayText}</span>`;
    },

    button(text, onclick, style = 'primary', size = 'sm') {
        const classes = `btn-${style} btn-${size}`;
        return `<button class="${classes}" onclick="${onclick}">${text}</button>`;
    },

    modal(title, content, id = 'modal') {
        return `
            <div id="${id}" class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="modal-close" onclick="closeResponseModal('${id}')">&times;</button>
                    </div>
                    <div class="modal-body">${content}</div>
                </div>
            </div>
        `;
    },

    formField(label, type, id, options = {}) {
        const { required = false, placeholder = '', style = '' } = options;
        const req = required ? '<span class="required">*</span>' : '';
        const extraStyle = style ? ` style="${style}"` : '';
        
        if (type === 'select' && options.items) {
            return `
                <div class="form-field">
                    <label for="${id}">${label} ${req}</label>
                    <select id="${id}" ${required ? 'required' : ''}${extraStyle}>
                        ${options.items.map(item => `<option value="${item.value}">${item.text}</option>`).join('')}
                    </select>
                </div>
            `;
        }
        
        if (type === 'textarea') {
            return `
                <div class="form-field">
                    <label for="${id}">${label} ${req}</label>
                    <textarea id="${id}" ${required ? 'required' : ''} placeholder="${placeholder}"${extraStyle}></textarea>
                </div>
            `;
        }
        
        return `
            <div class="form-field">
                <label for="${id}">${label} ${req}</label>
                <input type="${type}" id="${id}" ${required ? 'required' : ''} placeholder="${placeholder}"${extraStyle}>
            </div>
        `;
    },

    infoCard(title, content, emoji = '📝') {
        return `<div class="info-card"><h4>${emoji} ${title}</h4>${content}</div>`;
    }
};

// ===== УТИЛИТЫ =====
const Utils = {
    formatPrice(price) {
        const numericPrice = typeof price === 'string'
            ? parseFloat(price.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0
            : (price || 0);
        return numericPrice === 0 ? '0' : numericPrice.toLocaleString('ru-RU', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    },

    formatNumber(num) {
        return num ? new Intl.NumberFormat('ru-RU').format(num) : '0';
    },

    formatDate(dateString) {
        if (!dateString) return 'Не указано';
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return 'Неверная дата';
            return date.toLocaleDateString('ru-RU', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (error) {
            return 'Ошибка даты';
        }
    },

    showLoading(container, message = 'Загрузка...') {
        if (container) {
            container.innerHTML = `<div class="loading-state"><div class="loading-spinner">⏳</div><p>${message}</p></div>`;
        }
    },

    showError(container, message, retryCallback = null) {
        if (container) {
            const retryBtn = retryCallback ? Templates.button('🔄 Попробовать снова', `${retryCallback.name}()`, 'outline') : '';
            container.innerHTML = `<div class="error-state"><div class="error-icon">❌</div><h3>Ошибка загрузки</h3><p>${message}</p>${retryBtn}</div>`;
        }
    },

    showEmpty(container, title, description, action = null) {
        if (container) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">📝</div><h3>${title}</h3><p>${description}</p>${action || ''}</div>`;
        }
    }
};

// ===== API REQUESTS =====
const ApiClient = {
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        };

        const config = { ...defaultOptions, ...options };
        if (config.headers) {
            config.headers = { ...defaultOptions.headers, ...config.headers };
        }

        const response = await fetch(url, config);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    },

    async get(url) { return this.request(url, { method: 'GET' }); },
    async post(url, data) { return this.request(url, { method: 'POST', body: JSON.stringify(data) }); },
    async patch(url, data) { return this.request(url, { method: 'PATCH', body: JSON.stringify(data) }); },
    async delete(url) { return this.request(url, { method: 'DELETE' }); },

    // Универсальная загрузка с состояниями
    async loadData(config) {
        const { 
            url, container, loadingMessage = 'Загрузка...', 
            emptyTitle = 'Нет данных', emptyDescription = '', emptyAction = '',
            renderer, retryCallback, filters = {}
        } = config;
        
        const containerEl = typeof container === 'string' ? document.getElementById(container) : container;
        if (!containerEl) return;

        try {
            Utils.showLoading(containerEl, loadingMessage);
            
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            
            const fullUrl = `${url}${params.toString() ? '?' + params.toString() : ''}`;
            const result = await this.get(fullUrl);
            
            if (result.success && result.offers?.length > 0) {
                renderer ? renderer(result.offers) : containerEl.innerHTML = JSON.stringify(result.offers);
            } else {
                Utils.showEmpty(containerEl, emptyTitle, emptyDescription, emptyAction);
            }
        } catch (error) {
            Utils.showError(containerEl, 'Ошибка загрузки: ' + error.message, retryCallback);
        }
    }
};

// ===== ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК =====
function switchTab(tabName) {

    // Обновляем навигацию
    document.querySelectorAll('.nav-card').forEach(card => card.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const activeCard = document.querySelector(`[data-tab="${tabName}"]`);
    const activeContent = document.getElementById(tabName);

    if (activeCard) activeCard.classList.add('active');
    if (activeContent) activeContent.classList.add('active');

    // Загружаем данные для активной вкладки
    const tabActions = {
        'my-offers': loadMyOffers,
        'create-offer': initializeOffersManager,
        'find-offer': () => setTimeout(() => loadAvailableOffers({}), 100),
    };

    if (tabActions[tabName]) {
        tabActions[tabName]();
    }
}

// ===== РЕНДЕРИНГ ОФФЕРОВ =====
const OfferRenderer = {
    renderOffers(offers) {
        const container = document.getElementById('offersGrid');

        if (!container) {
            return;
        }

        if (!offers?.length) {
            Utils.showEmpty(container, 'Пока нет офферов',
                'Создайте свой первый оффер, нажав на "Создать оффер"',
                '<button class="btn btn-primary" onclick="switchTab(\'create-offer\')">Создать оффер</button>'
            );
            return;
        }

        container.innerHTML = offers.map(offer => this.renderOfferCard(offer)).join('');
    },

    renderOfferCard(offer) {
        const {
            id, title = 'Без названия', description = 'Нет описания',
            price = 0, budget_total = 0, currency = 'RUB', category = 'general',
            status = 'active', response_count = 0, created_at = '',
            creator_username = 'Неизвестный', creator_name = '', 
            creator_telegram_id = 'N/A', creator_db_id = 'N/A'
        } = offer;

        const displayPrice = budget_total || price || 0;
        const formattedPrice = Utils.formatPrice(displayPrice);
        const formattedDate = Utils.formatDate(created_at);
        let shortDescription = description.length > 80 ? description.substring(0, 80) + '...' : description;
        
        // Для черновиков добавляем пояснение
        if (status === 'draft') {
            shortDescription = '📝 Черновик требует завершения - выберите каналы для размещения. ' + shortDescription;
        }
        const shortTitle = title.length > 25 ? title.substring(0, 25) + '...' : title;

        const actionButtons = this.getActionButtons(id, status, title, response_count);
        const creatorDisplay = creator_name ? creator_name : (creator_username || 'Неизвестный');

        return `
            <div class="offer-card-compact" data-offer-id="${id}" style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: relative;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #2d3748; font-size: 14px; font-weight: 600; flex: 1;">${shortTitle}</h3>
                    ${Templates.statusBadge(status)}
                </div>
                
                <div style="margin-bottom: 6px; font-size: 10px; color: #68d391; font-weight: 500;">
                    👤 Создатель: ${creatorDisplay}
                </div>
                
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 18px; font-weight: bold; color: #667eea;">${formattedPrice}</span>
                    <span style="font-size: 12px; color: #718096; margin-left: 4px;">${currency}</span>
                    <div style="font-size: 10px; color: #a0aec0;">общий бюджет</div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #718096;">📁</span>
                        <span style="font-weight: 500; text-align: right;">${category}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #718096;">💬</span>
                        <span style="font-weight: 500; text-align: right;">${response_count}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; grid-column: 1 / -1;">
                        <span style="color: #718096;">📅</span>
                        <span style="font-weight: 500;">${formattedDate}</span>
                    </div>
                </div>
                
                <div style="background: #f7fafc; padding: 8px; border-radius: 4px; margin-bottom: 8px; font-size: 11px; line-height: 1.3; color: #4a5568;">${shortDescription}</div>
                
                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                    ${actionButtons}
                </div>
                
                <div style="margin-top: 4px; font-size: 9px; color: #a0aec0; text-align: right;">
                    Оффер ID: ${id} | Создатель: ${creator_db_id} (TG: ${creator_telegram_id})
                </div>
            </div>
        `;
    },

    getActionButtons(id, status, title, responseCount) {
        const baseButtonStyle = 'padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 10px; flex: 1;';
        const buttonConfigs = {
            active: [
                { text: '⏸️ Пауза', color: '#ed8936', action: `pauseOffer(${id}, this)` },
                { text: '❌ Отменить', color: '#e53e3e', action: `cancelOffer(${id}, '${title.replace(/'/g, "\\'")}', this)` }
            ],
            paused: [
                { text: '▶️ Возобновить', color: '#48bb78', action: `resumeOffer(${id}, this)` },
                { text: '❌ Отменить', color: '#e53e3e', action: `cancelOffer(${id}, '${title.replace(/'/g, "\\'")}', this)` }
            ],
            cancelled: [
                { text: '🗑️ Удалить', color: '#e53e3e', action: `deleteOffer(${id}, '${title.replace(/'/g, "\\'")}', this)`, flex: '2' }
            ],
            completed: [
                { text: '🗑️ Удалить', color: '#e53e3e', action: `deleteOffer(${id}, '${title.replace(/'/g, "\\'")}', this)`, flex: '2' }
            ],
            draft: [
                { text: '🗑️ Удалить', color: '#e53e3e', action: `deleteOffer(${id}, '${title.replace(/'/g, "\\'")}', this)`, flex: '2' }
            ]
        };

        // Определяем текст кнопки в зависимости от статуса
        const detailsButtonText = status === 'draft' ? '📝 Завершить' : '👁️ Подробнее';
        
        let buttons = [
            `<button onclick="viewOfferDetails(${id})" style="${baseButtonStyle} border: 1px solid #667eea; background: #667eea; color: white;">${detailsButtonText}</button>`
        ];

        // Показываем отклики только для активных офферов
        if (responseCount > 0 && status !== 'draft') {
            buttons.push(`<button onclick="manageResponses(${id})" style="${baseButtonStyle} border: 1px solid #48bb78; background: #48bb78; color: white;">💬 ${responseCount}</button>`);
        }

        const statusButtons = buttonConfigs[status] || [];
        statusButtons.forEach(btn => {
            const flexStyle = btn.flex ? `flex: ${btn.flex};` : 'flex: 1;';
            buttons.push(`<button onclick="${btn.action}" style="${baseButtonStyle} border: 1px solid ${btn.color}; background: ${btn.color}; color: white; ${flexStyle}">${btn.text}</button>`);
        });

        return `<div style="display: flex; gap: 4px; margin-top: 8px;">${buttons.join('')}</div>`;
    }
};

// ===== ЗАГРУЗКА ОФФЕРОВ =====
async function loadMyOffers() {
    await ApiClient.loadData({
        url: '/api/offers/my',
        container: 'offersGrid', 
        loadingMessage: 'Загрузка офферов...',
        emptyTitle: 'Пока нет офферов',
        emptyDescription: 'Создайте свой первый оффер, нажав на "Создать оффер"',
        emptyAction: Templates.button('Создать оффер', 'switchTab(\'create-offer\')', 'primary', 'md'),
        renderer: OfferRenderer.renderOffers.bind(OfferRenderer),
        retryCallback: loadMyOffers
    });
}

// ===== ПОИСК ДОСТУПНЫХ ОФФЕРОВ =====
function applyFindFilters() {
    const filters = {
        search: document.getElementById('findOffersSearch')?.value.trim() || '',
        category: document.getElementById('findCategoryFilter')?.value || '',
        min_budget: parseFloat(document.getElementById('findBudgetMin')?.value) || null,
        max_budget: parseFloat(document.getElementById('findBudgetMax')?.value) || null,
        min_subscribers: parseInt(document.getElementById('findMinSubscriber')?.value) || null
    };

    Object.keys(filters).forEach(key => {
        if (filters[key] === null || filters[key] === '') {
            delete filters[key];
        }
    });

    loadAvailableOffers(filters);
}

function clearFindFilters() {
    ['findOffersSearch', 'findCategoryFilter', 'findBudgetMin', 'findBudgetMax', 'findMinSubscriber']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    loadAvailableOffers({});
}

async function loadAvailableOffers(filters = {}) {
    console.log('loadAvailableOffers вызвана с фильтрами:', filters);
    await ApiClient.loadData({
        url: '/api/offers',
        container: 'findOffersGrid',
        loadingMessage: 'Поиск офферов...',
        emptyTitle: 'Нет доступных офферов',
        emptyDescription: 'В данный момент нет офферов, доступных для размещения',
        emptyAction: Templates.button('📋 Мои офферы', 'switchTab(\'my-offers\')', 'primary', 'md'),
        renderer: renderAvailableOffers,
        filters: filters
    });
    
    const loading = document.getElementById('findOffersLoading');
    if (loading) loading.style.display = 'none';
}

async function renderAvailableOffers(offers) {
    console.log('renderAvailableOffers вызвана с данными:', offers);
    const container = document.getElementById('findOffersGrid');

    if (!container) {
        console.error('Контейнер findOffersGrid не найден');
        return;
    }

    if (!offers?.length) {
        console.log('Нет офферов для отображения');
        Utils.showEmpty(container, 'Нет доступных офферов',
            'В данный момент нет офферов, доступных для размещения',
            Templates.button('📋 Мои офферы', 'switchTab(\'my-offers\')', 'primary', 'md')
        );
        return;
    }

    // Для каждого оффера получаем информацию о существующих откликах
    const offersWithResponses = await Promise.all(offers.map(async (offer) => {
        try {
            const responseResult = await ApiClient.get(`/api/offers/${offer.id}/my-responses`);
            const existingResponses = responseResult.success ? responseResult.responses : [];
            return { ...offer, existingResponses };
        } catch (error) {
            console.warn(`Не удалось загрузить отклики для оффера ${offer.id}:`, error);
            return { ...offer, existingResponses: [] };
        }
    }));

    container.innerHTML = offersWithResponses.map(offer => {
        const {
            id, title = 'Без названия', description = 'Нет описания',
            price = 0, budget_total = 0, currency = 'RUB',
            target_audience = 'Не указано', requirements = 'Нет требований',
            category = 'general', status = 'active',
            created_at, expires_at,
            creator_username = 'Неизвестный автор', creator_name = '',
            existingResponses = []
        } = offer;

        const isExpired = expires_at && new Date(expires_at) < new Date();
        const statusClass = isExpired ? 'expired' : status;
        const timeLeft = expires_at ? getTimeUntilExpiry(expires_at) : null;
        
        const displayPrice = budget_total || price;
        const formattedPrice = Utils.formatPrice(displayPrice);
        const shortDescription = description.length > 120 ? description.substring(0, 120) + '...' : description;
        const advertiserName = creator_name ? `${creator_name}` : creator_username;
        const createdDate = Utils.formatDate(created_at);
        
        // Категории на русском
        const categoryNames = {
            'general': 'Общие',
            'tech': 'Технологии',
            'finance': 'Финансы',
            'lifestyle': 'Образ жизни',
            'education': 'Образование',
            'entertainment': 'Развлечения',
            'business': 'Бизнес'
        };
        
        const categoryName = categoryNames[category] || 'Другое';

        return `
            <div class="available-offer-card" data-offer-id="${id}" style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div class="offer-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div class="offer-title" style="flex: 1;">
                        <h3 style="margin: 0; color: #2d3748; font-size: 16px; font-weight: 600; line-height: 1.3;">${title}</h3>
                        <div class="offer-meta" style="margin-top: 4px; font-size: 12px; color: #718096;">
                            👤 ${advertiserName} • 📂 ${categoryName} • 📅 ${createdDate}
                            ${timeLeft ? ` • ⏰ ${timeLeft.text}` : ''}
                        </div>
                    </div>
                    <div class="offer-price" style="text-align: right; margin-left: 12px;">
                        <div style="font-size: 18px; font-weight: 600; color: #2b6cb0;">${formattedPrice}</div>
                        <div style="font-size: 11px; color: #718096;">${currency}</div>
                    </div>
                </div>
                
                <div class="offer-description" style="margin-bottom: 12px; color: #4a5568; font-size: 14px; line-height: 1.4;">
                    ${shortDescription}
                </div>
                
                <div class="offer-audience" style="margin-bottom: 12px; padding: 8px; background: #f7fafc; border-radius: 6px; font-size: 13px;">
                    <strong>🎯 Целевая аудитория:</strong> ${target_audience}
                </div>
                
                ${existingResponses.length > 0 ? `
                <div class="response-status" style="margin-bottom: 12px; padding: 8px; background: #e6fffa; border-left: 4px solid #38b2ac; border-radius: 4px; font-size: 13px;">
                    <strong>📝 Ваши отклики:</strong> ${existingResponses.length} шт.
                    <div style="margin-top: 4px; font-size: 12px; color: #4a5568;">
                        ${existingResponses.map(resp => `
                            <div style="margin-top: 2px;">
                                • ${resp.channel.title}: ${ResponseManager.getResponseStatusText(resp.status)}
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <div class="offer-actions" style="display: flex; gap: 8px; justify-content: flex-end;">
                    <button class="btn btn-outline" onclick="viewAvailableOfferDetails(${id})" style="padding: 6px 12px; font-size: 12px; border: 1px solid #e2e8f0; background: white; color: #4a5568; border-radius: 4px;">
                        👁️ Подробнее
                    </button>
                    ${existingResponses.length > 0 ? `
                        <button class="btn btn-secondary" onclick="respondToOffer(${id})" style="padding: 6px 12px; font-size: 12px; background: #a0aec0; color: white; border: none; border-radius: 4px;">
                            ✅ Откликнулись
                        </button>
                    ` : `
                        <button class="btn btn-primary" onclick="console.log('Кнопка откликнуться нажата, ID:', ${id}); respondToOffer(${id})" style="padding: 6px 12px; font-size: 12px; background: #4299e1; color: white; border: none; border-radius: 4px;">
                            📩 Откликнуться
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join('');
}

// Вспомогательная функция для расчета времени
function getTimeUntilExpiry(expiresAt) {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diffMs = expiry.getTime() - now.getTime();
    
    if (diffMs <= 0) return null;
    
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) {
        return {
            text: `${diffDays} дн.`,
            isUrgent: diffDays <= 1
        };
    } else if (diffHours > 0) {
        return {
            text: `${diffHours} ч.`,
            isUrgent: diffHours <= 6
        };
    } else {
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        return {
            text: `${diffMinutes} мин.`,
            isUrgent: true
        };
    }
}

// ===== СОЗДАНИЕ ОФФЕРОВ - ОПТИМИЗИРОВАННЫЙ МЕНЕДЖЕР =====
class OffersManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.isInitialized = false;
    }

    init() {
        if (this.isInitialized) {
            return;
        }

        this.setupEventListeners();
        this.updateStep(this.currentStep);
        this.isInitialized = true;
    }

    setupEventListeners() {
        const controls = {
            nextBtn: () => this.nextStep(),
            prevBtn: () => this.prevStep(),
            submitBtn: () => this.submitOffer()
        };

        Object.keys(controls).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    controls[id]();
                });
            }
        });

        this.setupChips();
        this.setupsubscriberlider();
        this.setupPreviewUpdaters();
    }

    setupChips() {
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', function() {
                this.classList.toggle('selected');
            });
        });
    }

    setupsubscriberlider() {
        const subscriberRange = document.querySelector('input[name="min_subscribers"]');
        const subscriberValue = document.getElementById('subscriberValue');

        if (subscriberRange && subscriberValue) {
            subscriberRange.addEventListener('input', function() {
                const value = parseInt(this.value);
                subscriberValue.textContent = value >= 1000000 ? '1M+' :
                                              value >= 1000 ? Math.round(value/1000) + 'K' :
                                              value.toString();
            });
        }
    }

    setupPreviewUpdaters() {
        const updateTriggers = [
            'input[name="title"]',
            'input[name="budget"]',
            'select[name="geography"]'
        ];

        updateTriggers.forEach(selector => {
            const element = document.querySelector(selector);
            if (element) {
                element.addEventListener('input', () => this.updatePreview());
                element.addEventListener('change', () => this.updatePreview());
            }
        });

        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                setTimeout(() => this.updatePreview(), 10);
            });
        });
    }

    updateStep(step) {

        document.querySelectorAll('.step').forEach((stepEl, index) => {
            const stepNumber = index + 1;
            stepEl.classList.toggle('active', stepNumber === step);
            stepEl.classList.toggle('completed', stepNumber < step);
        });

        document.querySelectorAll('.form-step').forEach(stepEl => {
            stepEl.style.display = stepEl.dataset.step == step ? 'block' : 'none';
        });

        const controls = {
            prevBtn: step > 1,
            nextBtn: step < this.totalSteps,
            submitBtn: step === this.totalSteps
        };

        Object.keys(controls).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = controls[id] ? 'inline-flex' : 'none';
            }
        });

        const progress = ((step - 1) / (this.totalSteps - 1)) * 100;
        const progressEl = document.getElementById('stepperProgress');
        if (progressEl) {
            progressEl.style.width = progress + '%';
        }

        if (step === this.totalSteps) {
            this.updatePreview();
        }

        this.currentStep = step;
    }

    nextStep() {
        if (this.currentStep < this.totalSteps) {
            this.updateStep(this.currentStep + 1);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.updateStep(this.currentStep - 1);
        }
    }

    updatePreview() {
        const previewUpdates = {
            previewTitle: () => document.querySelector('input[name="title"]')?.value || 'Не указано',
            previewBudget: () => {
                const budget = document.querySelector('input[name="budget"]')?.value;
                const maxPrice = document.querySelector('input[name="max_price"]')?.value;

                let budgetText = '';
                if (budget) budgetText += `${Utils.formatPrice(budget)} RUB общий`;
                if (maxPrice) {
                    if (budgetText) budgetText += ' | ';
                    budgetText += `${Utils.formatPrice(maxPrice)} RUB за размещение`;
                } else if (budget) {
                    const estimatedMaxPrice = Math.min(parseFloat(budget) * 0.1, 50000);
                    if (budgetText) budgetText += ' | ';
                    budgetText += `~${Utils.formatPrice(estimatedMaxPrice)} RUB за размещение`;
                }
                return budgetText || 'Не указан';
            },
            previewTopics: () => {
                const ageGroups = ['18-25 лет', '26-35 лет', '36-45 лет', '46+ лет'];
                const allSelected = Array.from(document.querySelectorAll('.chip.selected'))
                    .map(chip => chip.textContent.trim());
                const topics = allSelected.filter(text => !ageGroups.includes(text));
                return topics.length > 0 ? topics.join(', ') : 'Не выбраны';
            },
            previewAudience: () => {
                const ageGroups = ['18-25 лет', '26-35 лет', '36-45 лет', '46+ лет'];
                const allSelected = Array.from(document.querySelectorAll('.chip.selected'))
                    .map(chip => chip.textContent.trim());
                const audience = allSelected.filter(text => ageGroups.includes(text));
                return audience.length > 0 ? audience.join(', ') : 'Не указана';
            },
            previewGeography: () => {
                const geographySelect = document.querySelector('select[name="geography"]');
                const geographyText = {
                    'russia': 'Россия',
                    'cis': 'СНГ',
                    'europe': 'Европа',
                    'world': 'Весь мир'
                };
                return geographyText[geographySelect?.value] || 'Не указана';
            }
        };

        Object.keys(previewUpdates).forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = previewUpdates[elementId]();
            }
        });
    }

    async submitOffer() {
        const submitBtn = document.getElementById('submitBtn');
        const originalText = submitBtn?.textContent;

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Создание...';
            }

            const data = this.collectFormData();

            const result = await ApiClient.post('/api/offers', data);

            if (result.success) {
                showChannelSelectionModal(result.offer.id, result.offer.title);
                this.resetForm();
                switchTab('my-offers');
            } else {
                throw new Error(result.error || result.errors?.join(', ') || 'Ошибка создания оффера');
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }

    collectFormData() {
        const getFieldValue = (name, defaultValue = '') => {
            const field = document.querySelector(`[name="${name}"]`);
            return field?.value?.trim() || defaultValue;
        };

        const data = {
            title: getFieldValue('title'),
            description: getFieldValue('description'),
            content: getFieldValue('description'), // Дублируем для совместимости
            currency: 'RUB',
            category: getFieldValue('category', 'general')
        };

        // Обработка цены с fallback логикой
        const maxPrice = parseFloat(getFieldValue('max_price')) || 0;
        const budget = parseFloat(getFieldValue('budget')) || 0;

        if (maxPrice > 0) {
            data.price = maxPrice;
        } else if (budget > 0) {
            data.price = Math.min(budget * 0.1, 50000);
        } else {
            throw new Error('Укажите общий бюджет или максимальную цену за размещение');
        }

        if (budget > 0) data.budget_total = budget;

        // Дополнительные поля
        const additionalFields = ['geography', 'min_subscribers'];
        additionalFields.forEach(field => {
            const value = getFieldValue(field);
            if (value) data[field] = field === 'min_subscribers' ? parseInt(value) : value;
        });

        // Собираем выбранные чипы
        const selectedChips = Array.from(document.querySelectorAll('.chip.selected'))
            .map(chip => chip.textContent.trim());

        if (selectedChips.length > 0) {
            data.topics = selectedChips.join(', ');
            data.target_audience = selectedChips.join(', ');
        }

        return data;
    }

    resetForm() {
        document.getElementById('offerForm')?.reset();
        document.querySelectorAll('.chip.selected').forEach(chip => {
            chip.classList.remove('selected');
        });
        this.updateStep(1);
    }
}

// ===== УПРАВЛЕНИЕ ОТКЛИКАМИ =====
const ResponseManager = {
    async acceptOffer(offerId) {
        try {
            const channelsResult = await ApiClient.get('/api/channels/my');

            if (!channelsResult.success) {
                throw new Error(channelsResult.error || 'Ошибка загрузки каналов');
            }

            const verifiedChannels = (channelsResult.channels || []).filter(channel =>
                channel.is_verified === true || channel.is_verified === 1 || channel.status === 'verified'
            );

            if (verifiedChannels.length === 0) {
                alert('У вас нет верифицированных каналов. Сначала добавьте и верифицируйте канал в разделе "Мои каналы".');
                return;
            }

            const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
            const titleElement = offerCard?.querySelector('h3');
            const offer = {
                id: offerId,
                title: titleElement?.textContent?.trim() || 'Оффер'
            };

            this.showResponseModal(offerId, offer, verifiedChannels);
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);
        }
    },

    async showResponseModal(offerId, offer, verifiedChannels) {
        // Проверяем существующие отклики пользователя на этот оффер
        let existingResponses = [];
        try {
            const responseResult = await ApiClient.get(`/api/offers/${offerId}/my-responses`);
            if (responseResult.success) {
                existingResponses = responseResult.responses || [];
            }
        } catch (error) {
            console.warn('Не удалось загрузить существующие отклики:', error);
        }

        const channelOptions = verifiedChannels.map(channel => {
            // Проверяем, есть ли уже отклик с этим каналом
            const existingResponse = existingResponses.find(r => r.channel_id === channel.id);
            const statusText = existingResponse ? this.getResponseStatusText(existingResponse.status) : '';
            
            return {
                value: channel.id,
                text: `${channel.title} (@${channel.username}) - ${Utils.formatNumber(channel.subscriber_count)} подписчиков${statusText}`,
                disabled: existingResponse ? true : false,
                existingResponse: existingResponse
            };
        });

        // Создаем опции для select с учетом статуса откликов
        const selectOptions = channelOptions.map(option => {
            const disabledAttr = option.disabled ? 'disabled' : '';
            const selectedAttr = '';
            return `<option value="${option.value}" ${disabledAttr} ${selectedAttr}>${option.text}</option>`;
        }).join('');

        // Показываем предупреждение о существующих откликах
        let existingResponsesWarning = '';
        if (existingResponses.length > 0) {
            existingResponsesWarning = `
                <div class="alert alert-info" style="margin-bottom: 20px;">
                    <span>💡</span>
                    <div>
                        <strong>Информация:</strong> У вас уже есть ${existingResponses.length} отклик(ов) на этот оффер.
                        Каналы с существующими откликами отмечены и недоступны для повторного отклика.
                    </div>
                </div>
            `;
        }

        const formContent = `
            ${Templates.infoCard(offer.title, '', '🎯')}
            ${existingResponsesWarning}
            <form id="responseForm">
                <div class="form-field">
                    <label for="selectedChannel">Выберите канал <span class="required">*</span></label>
                    <select id="selectedChannel" required>
                        <option value="">Выберите канал...</option>
                        ${selectOptions}
                    </select>
                </div>
                ${Templates.formField('Сообщение рекламодателю', 'textarea', 'responseMessage', { 
                    required: true, 
                    placeholder: 'Расскажите, почему ваш канал подходит для этого оффера...',
                    style: 'min-height:120px;'
                })}
                <div class="button-group">
                    ${Templates.button('Отмена', 'closeResponseModal(\'responseModal\')', 'outline', 'md')}
                    <button type="submit" class="btn-primary btn-md">Отправить отклик</button>
                </div>
            </form>
        `;

        const modal = document.createElement('div');
        const modalHTML = Templates.modal('📝 Отклик на оффер', formContent, 'responseModal');
        modal.innerHTML = modalHTML;
        const modalElement = modal.firstElementChild;
        
        // Добавляем класс 'active' для показа модального окна
        if (modalElement) {
            modalElement.classList.add('active');
        }
        
        document.body.appendChild(modalElement);

        // Ждем, пока элемент появится в DOM, затем добавляем обработчики
        setTimeout(() => {
            const form = document.getElementById('responseForm');
            if (form) {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    await this.submitResponse(offerId, modalElement);
                });
            }
            
            // Добавляем обработчик для кнопки закрытия
            const closeButton = modalElement.querySelector('.modal-close');
            if (closeButton) {
                console.log('Добавляем обработчик для кнопки закрытия');
                closeButton.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Кнопка закрытия нажата через addEventListener');
                    closeResponseModal('responseModal');
                });
            }
        }, 100);
    },

    getResponseStatusText(status) {
        const statusMap = {
            'pending': ' [⏳ Ожидает ответа]',
            'accepted': ' [✅ Принят]',
            'rejected': ' [❌ Отклонен]',
            'viewed': ' [👀 Просмотрен]'
        };
        return statusMap[status] || ` [${status}]`;
    },

    async submitResponse(offerId, modal) {
        const selectedChannelId = document.getElementById('selectedChannel').value;
        const message = document.getElementById('responseMessage').value.trim();

        if (!selectedChannelId || !message) {
            alert('Заполните все обязательные поля');
            return;
        }

        try {
            const result = await ApiClient.post(`/api/offers/${offerId}/respond`, {
                channel_id: parseInt(selectedChannelId),
                message: message
            });

            if (result.success) {
                alert('✅ ' + result.message);
                modal.remove();

                const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
                const respondButton = offerCard?.querySelector('button[onclick*="respondToOffer"]');
                if (respondButton) {
                    respondButton.style.background = '#a0aec0';
                    respondButton.textContent = '✅ Отклик отправлен';
                    respondButton.disabled = true;
                    respondButton.onclick = null;
                }
            } else {
                throw new Error(result.error || 'Ошибка отправки отклика');
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);
        }
    },

    async manageResponses(offerId) {

        try {
            const result = await ApiClient.get(`/api/offers/${offerId}/responses`);

            if (!result.success) {
                throw new Error(result.error || 'Ошибка загрузки откликов');
            }

            const offer = { id: offerId, title: result.offer?.title || `Оффер #${offerId}` };
            this.showResponsesModal(offer, result.responses || []);
        } catch (error) {
            alert(`❌ Ошибка загрузки откликов: ${error.message}`);
        }
    },

    showResponsesModal(offer, responses) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.background = 'rgba(0,0,0,0.8)';

    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; padding: 24px; max-width: 800px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="margin: 0; color: #2d3748; font-size: 20px;">💬 Отклики на оффер "${offer.title}"</h3>
                <button onclick="closeModal()" class="modal-close">&times;</button>
            </div>
            
            <div style="background: #f7fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 4px 0; color: #2d3748;">📊 Статистика</h4>
                <p style="margin: 0; color: #718096; font-size: 14px;">Всего откликов: <strong>${responses.length}</strong></p>
            </div>

            <div>${responses.length > 0 ? this.renderResponsesList(responses) : this.renderEmptyResponses()}</div>
        </div>
    `;

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
            document.body.style.overflow = 'auto';
        }
    });
},

    renderResponsesList(responses) {
        return responses.map(response => {
            const channelTitle = response.channel_title || 'Канал без названия';
            const channelUsername = response.channel_username || 'username';
            const channelsubscriber = response.channel_subscriber || 0;
            const message = response.message || '';
            const status = response.status || 'pending';
            const placement = response.placement || null;

            return `
                <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div style="flex: 1;">
                            <h5 style="margin: 0 0 4px 0; color: #2d3748; font-size: 16px;">📺 ${channelTitle}</h5>
                            <div style="font-size: 14px; color: #718096;">@${channelUsername} • 👥 ${Utils.formatNumber(channelsubscriber)} подписчиков</div>
                        </div>
                        <div style="padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; background: ${this.getStatusColor(status)}; color: #2d3748;">${this.getStatusText(status)}</div>
                    </div>

                    ${message ? `
                        <div style="background: #f7fafc; padding: 12px; border-radius: 6px; margin: 12px 0; border-left: 4px solid #4299e1;">
                            <div style="font-size: 12px; color: #4299e1; font-weight: 600; margin-bottom: 4px;">💬 СООБЩЕНИЕ:</div>
                            <div style="font-size: 14px; color: #2d3748;">${message}</div>
                        </div>
                    ` : ''}

                    ${placement ? this.renderPlacementInfo(placement) : ''}

                    <div style="display: flex; gap: 8px; margin-top: 12px;">
                        ${status === 'pending' ? `
                            <button onclick="ResponseManager.respondToResponse('${response.id}', 'accepted')" style="padding: 6px 12px; background: #48bb78; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">✅ Принять</button>
                            <button onclick="ResponseManager.showRejectModal('${response.id}')" style="padding: 6px 12px; background: #f56565; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">❌ Отклонить</button>
                        ` : ''}
                        ${status === 'accepted' && placement && placement.status === 'pending_placement' ? `
                            <button onclick="ResponseManager.cancelPlacement('${placement.id}')" style="padding: 6px 12px; background: #ed8936; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">🚫 Отменить размещение</button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    },

    renderPlacementInfo(placement) {
        if (!placement) return '';

        const deadline = new Date(placement.deadline);
        const now = new Date();
        const isExpired = deadline < now;
        const timeLeft = this.getTimeLeft(deadline);

        return `
            <div style="background: #e6fffa; padding: 12px; border-radius: 6px; margin: 12px 0; border-left: 4px solid #38b2ac;">
                <div style="font-size: 12px; color: #38b2ac; font-weight: 600; margin-bottom: 8px;">📅 РАЗМЕЩЕНИЕ</div>
                <div style="font-size: 14px; color: #2d3748; margin-bottom: 4px;">
                    💰 Зарезервировано: <strong>${placement.funds_reserved || 0} руб.</strong>
                </div>
                <div style="font-size: 14px; color: #2d3748; margin-bottom: 4px;">
                    📅 Дедлайн: <strong>${deadline.toLocaleString('ru-RU')}</strong>
                </div>
                <div style="font-size: 14px; color: ${isExpired ? '#e53e3e' : '#38b2ac'}; font-weight: 600;" data-deadline="${placement.deadline}">
                    ⏰ ${isExpired ? 'Срок истёк' : timeLeft}
                </div>
                ${placement.ereit_token ? `
                    <div style="font-size: 12px; color: #718096; margin-top: 4px;">
                        🔗 Токен: <code>${placement.ereit_token}</code>
                    </div>
                ` : ''}
            </div>
        `;
    },

    getTimeLeft(deadline) {
        const now = new Date();
        const diff = deadline - now;
        
        if (diff <= 0) return 'Срок истёк';
        
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        
        if (hours > 0) {
            return `Осталось: ${hours}ч ${minutes}мин`;
        } else {
            return `Осталось: ${minutes}мин`;
        }
    },

    async cancelPlacement(placementId) {
        if (!confirm('Вы уверены, что хотите отменить размещение? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const result = await ApiClient.patch(`/api/offers/placements/${placementId}/cancel`, {
                reason: 'Отменено рекламодателем'
            });

            if (result.success) {
                alert('✅ Размещение отменено');
                // Обновляем список откликов
                location.reload();
            } else {
                throw new Error(result.error || 'Ошибка отмены размещения');
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);
        }
    },

    showRejectModal(responseId) {
        const reasons = [
            'Не подходит аудитория канала',
            'Слишком высокая цена',
            'Канал не соответствует требованиям',
            'Другая причина'
        ];

        const reasonOptions = reasons.map(reason => 
            `<label style="display: block; margin: 8px 0; cursor: pointer;">
                <input type="radio" name="rejectReason" value="${reason}" style="margin-right: 8px;">
                ${reason}
            </label>`
        ).join('');

        const modalContent = `
            <div style="background: white; border-radius: 12px; padding: 24px; max-width: 500px; width: 100%; position: relative;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #2d3748; font-size: 18px;">❌ Отклонение предложения</h3>
                    <button onclick="closeModal('rejectModal')" class="modal-close" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #718096;">&times;</button>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <p style="color: #4a5568; margin-bottom: 16px;">Укажите причину отклонения предложения:</p>
                    
                    <form id="rejectForm">
                        <div style="margin-bottom: 16px;">
                            ${reasonOptions}
                        </div>
                        
                        <div id="customReasonBlock" style="display: none; margin-top: 12px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
                                Опишите причину:
                            </label>
                            <textarea 
                                id="customReasonText" 
                                placeholder="Введите причину отклонения..."
                                style="width: 100%; min-height: 80px; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; resize: vertical;"
                            ></textarea>
                        </div>
                        
                        <div style="display: flex; gap: 12px; margin-top: 20px;">
                            <button type="button" onclick="closeModal('rejectModal')" style="flex: 1; padding: 10px; background: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer;">
                                Отмена
                            </button>
                            <button type="submit" style="flex: 1; padding: 10px; background: #f56565; color: white; border: none; border-radius: 6px; cursor: pointer;">
                                Отклонить
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        const modal = document.createElement('div');
        modal.id = 'rejectModal';
        modal.className = 'modal';
        modal.className = 'modal-backdrop';
        modal.innerHTML = modalContent;
        
        document.body.appendChild(modal);

        // Обработчик изменения радио-кнопок
        const radioInputs = modal.querySelectorAll('input[name="rejectReason"]');
        const customReasonBlock = modal.querySelector('#customReasonBlock');
        
        radioInputs.forEach(input => {
            input.addEventListener('change', function() {
                if (this.value === 'Другая причина') {
                    customReasonBlock.style.display = 'block';
                } else {
                    customReasonBlock.style.display = 'none';
                }
            });
        });

        // Обработчик отправки формы
        modal.querySelector('#rejectForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const selectedReason = modal.querySelector('input[name="rejectReason"]:checked');
            if (!selectedReason) {
                alert('Выберите причину отклонения');
                return;
            }

            let reason = selectedReason.value;
            if (reason === 'Другая причина') {
                const customText = modal.querySelector('#customReasonText').value.trim();
                if (!customText) {
                    alert('Введите причину отклонения');
                    return;
                }
                reason = customText;
            }

            await ResponseManager.respondToResponse(responseId, 'rejected', reason);
            closeModal('rejectModal');
        });
    },

    renderEmptyResponses() {
        return `
            <div style="text-align: center; padding: 40px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                <h4 style="margin: 0 0 8px 0; color: #2d3748;">Пока нет откликов</h4>
                <p style="margin: 0; color: #718096;">Отклики начнут поступать в ближайшее время.</p>
            </div>
        `;
    },

    getStatusText(status) {
        const texts = {
            'pending': 'На рассмотрении',
            'accepted': 'Принят',
            'rejected': 'Отклонён',
            'pending_placement': 'Ожидает размещения',
            'placed': 'Размещено',
            'expired': 'Срок истёк'
        };
        return texts[status] || status;
    },

    getStatusColor(status) {
        const colors = {
            'pending': '#feb2b2',
            'accepted': '#9ae6b4',
            'rejected': '#fed7d7',
            'pending_placement': '#fef5e7',
            'placed': '#c6f6d5',
            'expired': '#fed7d7'
        };
        return colors[status] || '#e2e8f0';
    },

    async respondToResponse(responseId, action, reason = '') {

        try {
            let message = reason || '';
            if (action === 'rejected' && !message) {
                message = prompt('Причина отклонения (необязательно):') || '';
            }

            const result = await ApiClient.patch(`/api/offers/responses/${responseId}/status`, {
                status: action,
                message: message
            });

            if (result.success) {
                const actionText = action === 'accepted' ? 'принят' : 'отклонён';
                alert(`✅ Отклик ${actionText}`);


                // Закрываем модальное окно и обновляем список
                document.querySelector('div[style*="position: fixed"]')?.remove();
                document.body.style.overflow = 'auto';
                setTimeout(() => loadMyOffers(), 500);
            } else {
                throw new Error(result.error || 'Ошибка обработки отклика');
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);
        }
    }
};


// ===== УПРАВЛЕНИЕ СТАТУСАМИ ОФФЕРОВ =====
const OfferStatusManager = {
    async updateStatus(offerId, newStatus, reason = '', buttonElement = null, loadingText = 'Обновление...') {
        const originalText = buttonElement?.textContent;

        try {
            if (buttonElement) {
                buttonElement.disabled = true;
                buttonElement.textContent = `⏳ ${loadingText}`;
                buttonElement.style.opacity = '0.6';
            }

            const result = await ApiClient.patch(`/api/offers/${offerId}/status`, {
                status: newStatus,
                reason: reason
            });

            if (result.success) {
                alert(`✅ ${result.message}`);
                this.updateOfferCardStatus(offerId, newStatus);
            } else {
                throw new Error(result.error || `Ошибка изменения статуса на ${newStatus}`);
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);

            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.textContent = originalText;
                buttonElement.style.opacity = '1';
            }
        }
    },

    updateOfferCardStatus(offerId, newStatus) {
        const offerCard = document.querySelector(`[data-offer-id="${offerId}"]`);
        if (!offerCard) return;

        const statusBadge = offerCard.querySelector('.offer-header span');
        if (statusBadge) {
            const statusConfig = {
                'active': { bg: '#d4edda', color: '#155724', text: 'Активен' },
                'paused': { bg: '#fff3cd', color: '#856404', text: 'Приостановлен' },
                'completed': { bg: '#d1ecf1', color: '#0c5460', text: 'Завершен' },
                'cancelled': { bg: '#f8d7da', color: '#721c24', text: 'Отменен' }
            };

            const config = statusConfig[newStatus] || statusConfig.active;
            statusBadge.textContent = config.text;
            statusBadge.style.background = config.bg;
            statusBadge.style.color = config.color;
        }

        setTimeout(() => loadMyOffers(), 1000);
    },

    async deleteOffer(offerId, offerTitle, buttonElement) {
        if (!confirm(`Вы уверены, что хотите удалить оффер "${offerTitle}"?\n\nЭто действие нельзя отменить.`)) {
            return;
        }

        const originalText = buttonElement?.textContent;

        try {
            if (buttonElement) {
                buttonElement.disabled = true;
                buttonElement.textContent = '⏳ Удаление...';
                buttonElement.style.opacity = '0.6';
            }

            const result = await ApiClient.delete(`/api/offers/${offerId}`);

            if (result.success) {
                showNotification('success', `✅ ${result.message || 'Оффер успешно удален'}`);

                const offerCard = buttonElement?.closest('.offer-card-compact');
                if (offerCard) {
                    // Добавляем анимацию исчезновения
                    offerCard.style.transition = 'all 0.4s ease';
                    offerCard.style.transform = 'scale(0.95)';
                    offerCard.style.opacity = '0';
                    offerCard.style.marginBottom = '0';
                    offerCard.style.height = '0';
                    offerCard.style.padding = '0';
                    offerCard.style.overflow = 'hidden';

                    setTimeout(() => {
                        offerCard.remove();
                        
                        // Проверяем, остались ли офферы
                        const remainingOffers = document.querySelectorAll('.offer-card-compact');
                        if (remainingOffers.length === 0) {
                            const offersGrid = document.getElementById('offersGrid');
                            if (offersGrid) {
                                Utils.showEmpty(offersGrid, 'Пока нет офферов',
                                    'Создайте свой первый оффер, нажав на "Создать оффер"',
                                    '<button class="btn btn-primary" onclick="switchTab(\'create-offer\')">Создать оффер</button>'
                                );
                            }
                        }
                    }, 400);
                }
            } else {
                throw new Error(result.error || 'Ошибка удаления оффера');
            }
        } catch (error) {
            alert(`❌ Ошибка: ${error.message}`);

            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.textContent = originalText;
                buttonElement.style.opacity = '1';
            }
        }
    }
};

// ===== ГЛОБАЛЬНЫЕ ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ =====
function initializeOffersManager() {
    if (!offersManager) {
        offersManager = new OffersManager();
    }
    setTimeout(() => offersManager.init(), 100);
}

// Статусы офферов
async function cancelOffer(offerId, offerTitle, buttonElement) {
    if (!confirm(`Вы уверены, что хотите отменить оффер "${offerTitle}"?`)) return;
    await OfferStatusManager.updateStatus(offerId, 'cancelled', 'Отменено пользователем', buttonElement, 'Отмена...');
}

async function pauseOffer(offerId, buttonElement) {
    await OfferStatusManager.updateStatus(offerId, 'paused', 'Приостановлено пользователем', buttonElement, 'Приостановка...');
}

async function resumeOffer(offerId, buttonElement) {
    await OfferStatusManager.updateStatus(offerId, 'active', 'Возобновлено пользователем', buttonElement, 'Возобновление...');
}

async function deleteOffer(offerId, offerTitle, buttonElement) {
    await OfferStatusManager.deleteOffer(offerId, offerTitle, buttonElement);
}

// Отклики и детали
async function acceptOffer(offerId) {
    await ResponseManager.acceptOffer(offerId);
}

async function manageResponses(offerId) {
    await ResponseManager.manageResponses(offerId);
}

// Функции для работы с доступными офферами
async function viewAvailableOfferDetails(offerId) {
    try {
        const result = await ApiClient.get(`/api/offers/${offerId}`);
        if (result.success) {
            const offer = result.offer;
            alert(`Детали оффера "${offer.title}"\n\nОписание: ${offer.description}\nЦена: ${offer.budget_total || offer.price} ${offer.currency}\nЦелевая аудитория: ${offer.target_audience}\nТребования: ${offer.requirements || 'Нет требований'}`);
        } else {
            alert('Ошибка получения деталей оффера');
        }
    } catch (error) {
        alert('Ошибка получения деталей оффера');
    }
}

async function respondToOffer(offerId) {
    await ResponseManager.acceptOffer(offerId);
}

async function viewOfferDetails(offerId) {
    try {
        // Получаем детали оффера
        const result = await ApiClient.get(`/api/offers/${offerId}`);
        
        if (!result.success) {
            throw new Error(result.error || 'Ошибка получения деталей оффера');
        }
        
        const offer = result.offer;
        
        // Если оффер - черновик, показываем модальное окно выбора каналов
        if (offer.status === 'draft') {
            showChannelSelectionModalForDraft(offerId, offer.title);
        } else {
            // Для активных офферов показываем обычные детали
            showOfferDetailsModal(offer);
        }
        
    } catch (error) {
        alert(`❌ Ошибка: ${error.message}`);
    }
}


function setupOffersSearch() {
    const searchInput = document.getElementById('offersSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            document.querySelectorAll('.offer-card-compact').forEach(card => {
                const title = card.querySelector('h3')?.textContent.toLowerCase() || '';
                card.style.display = title.includes(searchTerm) ? 'block' : 'none';
            });
        });
    }
}
// ===== МОДАЛЬНОЕ ОКНО ВЫБОРА КАНАЛОВ =====

// Проверка и доработка функции показа модального окна выбора каналов для оффера

async function showChannelSelectionModal(offerId, offerTitle) {

    try {
        // Получаем Telegram User ID (глобальная функция должна быть определена)
        const telegramUserId = getTelegramUserId?.();

        if (!telegramUserId) {
            showNotification('error', '❌ Не удалось получить ID пользователя Telegram. Попробуйте перезагрузить страницу.');
            return;
        }

        // Показываем индикатор загрузки
        showLoadingOverlay?.('Подбираем каналы...');

        // Запрос к API на получение рекомендуемых каналов
        const response = await fetch(`/api/offers_management/${offerId}/recommended-channels?limit=20`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': telegramUserId
            }
        });


        // Обработка ошибок HTTP
        if (!response.ok) {
            const errorText = await response.text();
            hideLoadingOverlay?.();
            showNotification('error', `❌ Ошибка загрузки каналов: HTTP ${response.status}: ${errorText}`);
            // Показываем fallback уведомление
            setTimeout(() => {
                showNotification('info', '✅ Оффер создан! Выбор каналов доступен в разделе "Мои офферы"');
            }, 2000);
            return;
        }

        // Парсим ответ
        const data = await response.json();

        hideLoadingOverlay?.();

        // Проверяем структуру ответа
        if (data && data.success && Array.isArray(data.channels) && data.channels.length > 0) {
            createChannelModal(offerId, offerTitle, data.channels);
        } else if (data && data.success && Array.isArray(data.channels) && data.channels.length === 0) {
            // Нет каналов, но запрос успешен
            showNotification('info', '📺 Рекомендуемые каналы не найдены. Вы можете выбрать каналы позже в разделе "Мои офферы"');
        } else if (data && data.error) {
            // Сервер вернул ошибку
            showNotification('error', `❌ Ошибка: ${data.error}`);
            setTimeout(() => {
                showNotification('info', '✅ Оффер создан! Выбор каналов доступен в разделе "Мои офферы"');
            }, 2000);
        } else {
            // Неожиданный ответ
            showNotification('error', '❌ Не удалось получить список каналов. Попробуйте позже.');
            setTimeout(() => {
                showNotification('info', '✅ Оффер создан! Выбор каналов доступен в разделе "Мои офферы"');
            }, 2000);
        }

    } catch (error) {
        hideLoadingOverlay?.();
        showNotification('error', `❌ Ошибка загрузки каналов: ${error.message}`);
        setTimeout(() => {
            showNotification('info', '✅ Оффер создан! Выбор каналов доступен в разделе "Мои офферы"');
        }, 2000);
    }
}


function createChannelModal(offerId, offerTitle, channels, isDraft = false) {
    const modal = document.createElement('div');
    modal.id = 'channelModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    
    const buttonText = isDraft ? 'Завершить создание' : 'Отправить';
    const onClickFunction = isDraft ? `completeDraftAndSendProposals(${offerId})` : `sendProposals(${offerId})`;
    const skipButton = isDraft ? '' : `<button class="btn btn-secondary" onclick="saveOfferAsDraft(${offerId}); closeChannelModal()">Пропустить</button>`;
    
    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeChannelModal()"></div>
        <div class="modal-content large-modal">
            <div class="modal-header">
                <h2>${isDraft ? '📝 Завершить создание оффера' : '🎯 Выберите каналы'}</h2>
                <button class="modal-close" onclick="closeChannelModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="offer-info">
                    <h3>${offerTitle}</h3>
                    <p>Найдено: <strong>${channels.length}</strong> каналов</p>
                </div>
                <div class="channels-list">
                    ${channels.map(ch => `
                        <div class="channel-card nav-card" data-channel-id="${ch.id}" onclick="toggleChannel(this)">
                            <div class="channel-checkbox"></div>
                            <div class="nav-icon">${ch.title.substring(0,2).toUpperCase()}</div>
                            <div class="nav-content">
                                <h3>${ch.title}</h3>
                                <p>@${ch.username || 'no_username'} • ${formatSubs(ch.subscriber_count)} подписчиков</p>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="modal-footer">
                <span id="selectedCount">Выбрано: 0</span>
                <div class="modal-actions">
                    ${skipButton}
                    <button class="btn btn-primary" id="sendBtn" onclick="${onClickFunction}" disabled>${buttonText}</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function toggleChannel(card) {
    const isSelected = card.classList.contains('selected');
    if (isSelected) {
        card.classList.remove('selected');
        card.style.border = '2px solid #e2e8f0';
        card.style.background = 'white';
        const checkbox = card.querySelector('.channel-checkbox');
        if (checkbox) {
            checkbox.innerHTML = '';
        }
    } else {
        card.classList.add('selected');
        card.style.border = '2px solid #4299e1';
        card.style.background = '#ebf8ff';
        const checkbox = card.querySelector('.channel-checkbox');
        if (checkbox) {
            checkbox.innerHTML = '✓';
        }
    }
    updateCount();
}

function updateCount() {
    const count = document.querySelectorAll('.channel-card.selected').length;
    document.getElementById('selectedCount').textContent = `Выбрано: ${count}`;
    
    // Обновляем кнопку отправки (работает для обычных офферов и черновиков)
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.disabled = count === 0;
    }
}

async function sendProposals(offerId) {
    const channelIds = Array.from(document.querySelectorAll('.channel-card.selected'))
        .map(card => parseInt(card.dataset.channelId));
    
    try {
        const telegramUserId = getTelegramUserId();
        
        if (!telegramUserId) {
            showNotification('error', 'Ошибка: не удалось получить Telegram User ID');
            return;
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUserId,
            'X-User-Id': telegramUserId,
            'telegram-user-id': telegramUserId
        };
        
        const response = await fetch(`/api/offers_management/${offerId}/select-channels`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({channel_ids: channelIds, message: 'Приглашение к участию'})
        });
        
        const result = await response.json();
        if (response.ok && result.success) {
            closeChannelModal();
            showNotification('success', `✅ Отправлено в ${channelIds.length} каналов!`);
            // Обновляем список офферов для черновиков
            setTimeout(() => loadMyOffers(), 1000);
        } else {
            const errorMessage = result.message || result.error || 'Неизвестная ошибка';
            showNotification('error', `Ошибка: ${errorMessage}`);
        }
    } catch (error) {
        showNotification('error', `Ошибка: ${error.message}`);
    }
}

async function completeDraftAndSendProposals(offerId) {
    const channelIds = Array.from(document.querySelectorAll('.channel-card.selected'))
        .map(card => parseInt(card.dataset.channelId));
    
    if (channelIds.length === 0) {
        showNotification('warning', '⚠️ Выберите хотя бы один канал');
        return;
    }
    
    try {
        const telegramUserId = getTelegramUserId();
        
        if (!telegramUserId) {
            showNotification('error', '❌ Не удалось получить ID пользователя Telegram');
            return;
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUserId,
            'X-User-Id': telegramUserId,
            'telegram-user-id': telegramUserId
        };
        
        // Сначала завершаем черновик (обновляем статус на active)
        const completeResponse = await fetch(`/api/offers/${offerId}/complete-draft`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                channel_ids: channelIds
            })
        });
        
        const completeResult = await completeResponse.json();
        
        if (completeResponse.ok && completeResult.success) {
            // Затем отправляем предложения в каналы
            const proposalsResponse = await fetch(`/api/offers_management/${offerId}/select-channels`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({channel_ids: channelIds, message: 'Приглашение к участию'})
            });
            
            const proposalsResult = await proposalsResponse.json();
            
            if (proposalsResponse.ok && proposalsResult.success) {
                closeChannelModal();
                showNotification('success', `✅ Оффер завершен и отправлен в ${channelIds.length} каналов!`);
                // Обновляем список офферов
                setTimeout(() => loadMyOffers(), 1000);
            } else {
                const errorMessage = proposalsResult.message || proposalsResult.error || 'Ошибка отправки предложений';
                showNotification('error', `❌ Ошибка отправки: ${errorMessage}`);
            }
        } else {
            const errorMessage = completeResult.message || completeResult.error || 'Ошибка завершения черновика';
            showNotification('error', `❌ Ошибка завершения: ${errorMessage}`);
        }
    } catch (error) {
        showNotification('error', `❌ Ошибка: ${error.message}`);
    }
}

function closeChannelModal() {
    const modal = document.getElementById('channelModal');
    if (modal) modal.remove();
}

async function saveOfferAsDraft(offerId) {
    try {
        // Обновляем статус оффера на draft
        const response = await fetch(`/api/offers/${offerId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId(),
                'X-User-Id': getTelegramUserId(),
                'telegram-user-id': getTelegramUserId()
            },
            body: JSON.stringify({ status: 'draft' })
        });

        if (response.ok) {
            showNotification('info', '📝 Оффер сохранен как черновик. Завершите его в разделе "Мои офферы"');
        } else {
            showNotification('error', '❌ Ошибка сохранения черновика');
        }
    } catch (error) {
        showNotification('error', '❌ Ошибка сохранения черновика');
    }
}

async function showChannelSelectionModalForDraft(offerId, offerTitle) {

    try {
        const telegramUserId = getTelegramUserId();
        
        if (!telegramUserId) {
            showNotification('error', '❌ Не удалось получить ID пользователя Telegram');
            return;
        }

        // Показываем индикатор загрузки
        showLoadingOverlay?.('Подбираем каналы...');

        // Запрос к API на получение рекомендуемых каналов
        const response = await fetch(`/api/offers_management/${offerId}/recommended-channels?limit=20`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': telegramUserId,
                'X-User-Id': telegramUserId,
                'telegram-user-id': telegramUserId
            }
        });


        if (!response.ok) {
            const errorText = await response.text();
            hideLoadingOverlay?.();
            showNotification('error', `❌ Ошибка загрузки каналов: HTTP ${response.status}: ${errorText}`);
            return;
        }

        const data = await response.json();

        hideLoadingOverlay?.();

        if (data && data.success && Array.isArray(data.channels) && data.channels.length > 0) {
            createChannelModal(offerId, offerTitle, data.channels, true);
        } else {
            showNotification('info', '📺 Рекомендуемые каналы не найдены');
        }

    } catch (error) {
        hideLoadingOverlay?.();
        showNotification('error', `❌ Ошибка: ${error.message}`);
    }
}

function showOfferDetailsModal(offer) {
    // Простая заглушка для показа деталей активного оффера
    alert(`Детали оффера "${offer.title}"\n\nСтатус: ${offer.status}\nЦена: ${offer.price} ${offer.currency}\nОписание: ${offer.description}`);
}


function formatSubs(count) {
    if (count >= 1000000) return (count/1000000).toFixed(1) + 'M';
    if (count >= 1000) return (count/1000).toFixed(1) + 'K';
    return count.toString();
}

function showLoadingOverlay(text) {
    const div = document.createElement('div');
    div.id = 'loading';
    div.className = 'loading-overlay';
    div.innerHTML = `<div>${text}<div style="margin-top:10px;border:3px solid #fff;border-top:3px solid transparent;border-radius:50%;width:30px;height:30px;animation:spin 1s linear infinite;"></div></div>`;
    document.body.appendChild(div);
}

function hideLoadingOverlay() {
    const el = document.getElementById('loading');
    if (el) el.remove();
}

function acceptProposal(proposalId, title) {
    showAcceptModal(proposalId, title);
}

function rejectProposal(proposalId, title) {
    showRejectModal(proposalId, title);
}
// ===== МОДАЛЬНОЕ ОКНО ПРИНЯТИЯ ПРЕДЛОЖЕНИЯ =====
function showAcceptModal(proposalId, offerTitle) {
    const modal = createModal('accept-proposal-modal', 'Принять предложение');
    
    // Получаем завтрашнюю дату как минимальную
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minDate = tomorrow.toISOString().split('T')[0];
    
    // Получаем дату через неделю как рекомендуемую
    const weekLater = new Date();
    weekLater.setDate(weekLater.getDate() + 7);
    const recommendedDate = weekLater.toISOString().split('T')[0];
    
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>✅ Принять предложение</h3>
                    <button class="modal-close" onclick="closeModal('accept-proposal-modal')">&times;</button>
                </div>
                
                <div class="modal-body">
                    <div class="proposal-info">
                        <h4>📢 ${offerTitle}</h4>
                        <p class="text-muted">Укажите детали размещения</p>
                    </div>
                    
                    <form id="acceptProposalForm">
                        <div class="form-group">
                            <label for="scheduledDate">📅 Дата размещения *</label>
                            <input type="date" 
                                   id="scheduledDate" 
                                   class="form-control" 
                                   min="${minDate}"
                                   value="${recommendedDate}"
                                   required>
                            <small class="form-help">Минимум завтра</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="scheduledTime">🕐 Время размещения *</label>
                            <input type="time" 
                                   id="scheduledTime" 
                                   class="form-control" 
                                   value="12:00"
                                   required>
                            <small class="form-help">Оптимальное время: 12:00-18:00</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="proposedPrice">💰 Ваша цена (необязательно)</label>
                            <div class="input-group">
                                <input type="number" 
                                       id="proposedPrice" 
                                       class="form-control" 
                                       min="0" 
                                       step="0.01" 
                                       placeholder="Оставьте пустым для цены из оффера">
                                <span class="input-group-text">₽</span>
                            </div>
                            <small class="form-help">Можете предложить свою цену</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="responseNotes">💬 Комментарий (необязательно)</label>
                            <textarea id="responseNotes" 
                                      class="form-control" 
                                      rows="3" 
                                      maxlength="500"
                                      placeholder="Дополнительные условия или пожелания..."></textarea>
                            <small class="form-help">Максимум 500 символов</small>
                        </div>
                    </form>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal('accept-proposal-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-success" onclick="submitAcceptProposal(${proposalId})">
                        ✅ Принять предложение
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
    
    // Фокус на дату
    setTimeout(() => document.getElementById('scheduledDate').focus(), 100);
}

// ===== МОДАЛЬНОЕ ОКНО ОТКЛОНЕНИЯ ПРЕДЛОЖЕНИЯ =====
function showRejectModal(proposalId, offerTitle) {
    const modal = createModal('reject-proposal-modal', 'Отклонить предложение');
    
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>❌ Отклонить предложение</h3>
                    <button class="modal-close" onclick="closeModal('reject-proposal-modal')">&times;</button>
                </div>
                
                <div class="modal-body">
                    <div class="proposal-info">
                        <h4>📢 ${offerTitle}</h4>
                        <p class="text-muted">Укажите причину отклонения</p>
                    </div>
                    
                    <form id="rejectProposalForm">
                        <div class="form-group">
                            <label for="rejectionReason">❌ Причина отклонения *</label>
                            <select id="rejectionReason" class="form-control" required>
                                <option value="">Выберите причину...</option>
                                <option value="Не устраивает цена">💰 Не устраивает цена</option>
                                <option value="Не подходит тематика">🎯 Не подходит тематика</option>
                                <option value="Слишком короткий срок">⏰ Слишком короткий срок</option>
                                <option value="Канал сейчас неактивен">📴 Канал сейчас неактивен</option>
                                <option value="Не подходит формат контента">📝 Не подходит формат контента</option>
                                <option value="Занят другими кампаниями">📋 Занят другими кампаниями</option>
                                <option value="Другое">❓ Другое</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="rejectionComment">💬 Дополнительный комментарий</label>
                            <textarea id="rejectionComment" 
                                      class="form-control" 
                                      rows="3" 
                                      maxlength="500"
                                      placeholder="Подробности или предложения по улучшению оффера..."></textarea>
                            <small class="form-help">Поможет рекламодателю улучшить будущие предложения</small>
                        </div>
                        
                        <div class="rejection-warning">
                            <div class="warning-icon">⚠️</div>
                            <div class="warning-text">
                                После отклонения предложение нельзя будет принять. 
                                Рекламодатель получит уведомление с указанной причиной.
                            </div>
                        </div>
                    </form>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal('reject-proposal-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-danger" onclick="submitRejectProposal(${proposalId})">
                        ❌ Отклонить предложение
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
    
    // Фокус на причину
    setTimeout(() => document.getElementById('rejectionReason').focus(), 100);
}

// ===== ОБРАБОТКА ОТПРАВКИ ФОРМ =====

async function submitAcceptProposal(proposalId) {
    try {
        const form = document.getElementById('acceptProposalForm');
        const submitBtn = document.querySelector('.btn-success');
        
        // Валидация формы
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Получаем данные формы
        const formData = {
            scheduled_date: document.getElementById('scheduledDate').value,
            scheduled_time: document.getElementById('scheduledTime').value,
            proposed_price: document.getElementById('proposedPrice').value || null,
            response_notes: document.getElementById('responseNotes').value.trim() || null
        };
        
        // Валидация даты
        const selectedDate = new Date(formData.scheduled_date);
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        if (selectedDate < tomorrow) {
            showError('Дата размещения должна быть не ранее завтрашнего дня');
            return;
        }
        
        // Отключаем кнопку и показываем загрузку
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Принимаем...';
        
        // Отправляем запрос
        const response = await fetch(`/api/proposals/${proposalId}/accept`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('accept-proposal-modal');
            showSuccess('✅ Предложение принято! Уведомление отправлено рекламодателю.');
            
            // Обновляем список предложений
            if (typeof loadAvailableOffers === 'function') {
                loadAvailableOffers();
            }
        } else {
            throw new Error(result.message || 'Ошибка принятия предложения');
        }
        
    } catch (error) {
        showError('Ошибка: ' + error.message);
    } finally {
        // Восстанавливаем кнопку
        const submitBtn = document.querySelector('.btn-success');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '✅ Принять предложение';
        }
    }
}

async function submitRejectProposal(proposalId) {
    try {
        const form = document.getElementById('rejectProposalForm');
        const submitBtn = document.querySelector('.btn-danger');
        
        // Валидация формы
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Получаем данные формы
        const rejectionReason = document.getElementById('rejectionReason').value;
        const rejectionComment = document.getElementById('rejectionComment').value.trim();
        
        // Формируем полную причину
        let fullReason = rejectionReason;
        if (rejectionComment) {
            fullReason += `. ${rejectionComment}`;
        }
        
        // Отключаем кнопку и показываем загрузку
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Отклоняем...';
        
        // Отправляем запрос
        const response = await fetch(`/api/proposals/${proposalId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reason: fullReason
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('reject-proposal-modal');
            showSuccess('❌ Предложение отклонено. Уведомление отправлено рекламодателю.');
            
            // Обновляем список предложений
            if (typeof loadAvailableOffers === 'function') {
                loadAvailableOffers();
            }
        } else {
            throw new Error(result.message || 'Ошибка отклонения предложения');
        }
        
    } catch (error) {
        showError('Ошибка: ' + error.message);
    } finally {
        // Восстанавливаем кнопку
        const submitBtn = document.querySelector('.btn-danger');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '❌ Отклонить предложение';
        }
    }
}

// ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ МОДАЛЬНЫХ ОКОН =====

function createModal(id, title) {
    // Удаляем существующее модальное окно
    const existingModal = document.getElementById(id);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Создаем новое модальное окно
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'modal';
    
    return modal;
}

function closeResponseModal(modalId) {
    console.log('closeResponseModal вызвана с modalId:', modalId);
    const modal = document.getElementById(modalId);
    console.log('Найденный modal элемент:', modal);
    if (modal) {
        console.log('Закрываем модальное окно...');
        // Убираем класс active для запуска CSS анимации закрытия
        modal.classList.remove('active');
        // Удаляем элемент после завершения анимации
        setTimeout(() => {
            console.log('Удаляем модальное окно из DOM');
            modal.remove();
        }, 300);
    } else {
        console.error('Модальное окно не найдено по ID:', modalId);
    }
}

// Закрытие модального окна по клику вне его
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.classList.remove('active');
        setTimeout(() => event.target.remove(), 300);
    }
});

// Закрытие модального окна по Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal-overlay.active');
        modals.forEach(modal => {
            modal.classList.remove('active');
            setTimeout(() => modal.remove(), 300);
        });
    }
});

// ===== ФУНКЦИИ УВЕДОМЛЕНИЙ =====

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    // Создаем уведомление
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-message">${message}</div>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Добавляем на страницу
    document.body.appendChild(notification);
    
    // Показываем с анимацией
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
    
    // Закрытие по клику
    notification.querySelector('.notification-close').onclick = () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    };
}

// Экспорт
window.showChannelSelectionModal = showChannelSelectionModal;
window.closeChannelModal = closeChannelModal;
window.toggleChannel = toggleChannel;
window.sendProposals = sendProposals;
window.saveOfferAsDraft = saveOfferAsDraft;
window.showChannelSelectionModalForDraft = showChannelSelectionModalForDraft;
window.updateCount = updateCount;
// ===== ИНИЦИАЛИЗАЦИЯ =====

// ===== ГЛОБАЛЬНЫЙ ДОСТУП К ФУНКЦИЯМ =====
window.ResponseManager = ResponseManager;
window.manageResponses = (offerId) => ResponseManager.manageResponses(offerId);
window.acceptOffer = (offerId) => ResponseManager.acceptOffer(offerId);

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    loadMyOffers();
    setupOffersSearch();
    startTimerUpdates(); // Запускаем обновление таймеров
});

// Функция для обновления таймеров
function startTimerUpdates() {
    setInterval(() => {
        const timers = document.querySelectorAll('[data-deadline]');
        timers.forEach(timer => {
            const deadline = new Date(timer.getAttribute('data-deadline'));
            const timeLeft = ResponseManager.getTimeLeft(deadline);
            timer.textContent = timeLeft;
            
            // Если срок истёк, обновляем цвет
            if (timeLeft === 'Срок истёк') {
                timer.style.color = '#e53e3e';
            }
        });
    }, 60000); // Обновляем каждую минуту
}

