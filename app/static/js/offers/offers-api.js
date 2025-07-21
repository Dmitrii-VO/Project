/**
 * offers-api.js
 * API клиент для работы с офферами
 */

export class OffersAPI {
    constructor() {
        this.baseUrl = '/api';
    }

    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'  // Тестовый ID как fallback
            }
        };

        const config = { ...defaultOptions, ...options };
        if (config.headers) {
            config.headers = { ...defaultOptions.headers, ...config.headers };
        }

        const response = await fetch(url, config);
        console.log(`📡 ${config.method || 'GET'} ${url} -> HTTP ${response.status}`);
        
        if (!response.ok) {
            let errorText;
            try {
                errorText = await response.text();
            } catch {
                errorText = response.statusText;
            }
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        try {
            const data = await response.json();
            console.log('📋 Ответ:', data);
            return data;
        } catch (error) {
            throw new Error('Ответ не является валидным JSON: ' + error.message);
        }
    }

    // Базовые HTTP методы
    async get(url) { 
        return this.request(url, { method: 'GET' }); 
    }
    
    async post(url, data) { 
        return this.request(url, { method: 'POST', body: JSON.stringify(data) }); 
    }
    
    async patch(url, data) { 
        return this.request(url, { method: 'PATCH', body: JSON.stringify(data) }); 
    }
    
    async delete(url) { 
        return this.request(url, { method: 'DELETE' }); 
    }

    // Методы для работы с офферами
    async getOffers(filters = {}) {
        const params = new URLSearchParams();
        Object.keys(filters).forEach(key => {
            if (filters[key] !== null && filters[key] !== '') {
                params.append(key, filters[key]);
            }
        });
        
        const url = `${this.baseUrl}/offers/available${params.toString() ? '?' + params.toString() : ''}`;
        return this.get(url);
    }

    async getMyOffers() {
        return this.get(`${this.baseUrl}/offers/my-offers`);
    }

    async getOffer(id) {
        return this.get(`${this.baseUrl}/offers/${id}`);
    }

    async createOffer(offerData) {
        return this.post(`${this.baseUrl}/offers/create`, offerData);
    }

    async updateOffer(id, offerData) {
        return this.request(`${this.baseUrl}/offers/${id}/status`, { method: 'PUT', body: JSON.stringify(offerData) });
    }

    async deleteOffer(id) {
        return this.delete(`${this.baseUrl}/offers/${id}`);
    }

    // Методы для работы с откликами
    async getProposals(offerId) {
        return this.get(`${this.baseUrl}/offers/${offerId}/responses`);
    }

    async acceptProposal(proposalId, data = {}) {
        return this.post(`${this.baseUrl}/proposals/${proposalId}/accept`, data);
    }

    async rejectProposal(proposalId, data = {}) {
        return this.post(`${this.baseUrl}/proposals/${proposalId}/reject`, data);
    }

    // Методы для работы с каналами
    async getChannels() {
        return this.get(`${this.baseUrl}/channels`);
    }

    async getRecommendedChannels(offerData) {
        return this.post(`${this.baseUrl}/channels/recommend`, offerData);
    }

    // Универсальная загрузка с обработкой состояний
    async loadData(config) {
        const { 
            url, 
            container, 
            loadingMessage = 'Загрузка...', 
            emptyTitle = 'Нет данных', 
            emptyDescription = '', 
            emptyAction = '',
            renderer, 
            retryCallback, 
            filters = {} 
        } = config;
        
        const containerEl = typeof container === 'string' ? document.getElementById(container) : container;
        if (!containerEl) return;

        try {
            this._showLoading(containerEl, loadingMessage);
            
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== null && filters[key] !== '') {
                    params.append(key, filters[key]);
                }
            });
            
            const fullUrl = `${url}${params.toString() ? '?' + params.toString() : ''}`;
            const result = await this.get(fullUrl);
            
            if (result.success && result.offers?.length > 0) {
                if (renderer && typeof renderer === 'function') {
                    renderer(result.offers);
                } else {
                    containerEl.innerHTML = JSON.stringify(result.offers, null, 2);
                }
            } else {
                this._showEmpty(containerEl, emptyTitle, emptyDescription, emptyAction);
            }
        } catch (error) {
            this._showError(containerEl, 'Ошибка загрузки: ' + error.message, retryCallback);
        }
    }

    // Вспомогательные методы для UI состояний
    _showLoading(container, message = 'Загрузка...') {
        if (container) {
            container.innerHTML = `
                <div class="loading-state">
                    <div class="loading-spinner">⏳</div>
                    <p>${message}</p>
                </div>
            `;
        }
    }

    _showError(container, message, retryCallback = null) {
        if (container) {
            const retryBtn = retryCallback ? `<button class="btn-outline btn-sm" onclick="${retryCallback.name}()">🔄 Попробовать снова</button>` : '';
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <h3>Ошибка загрузки</h3>
                    <p>${message}</p>
                    ${retryBtn}
                </div>
            `;
        }
    }

    _showEmpty(container, title, description, action = null) {
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📝</div>
                    <h3>${title}</h3>
                    <p>${description}</p>
                    ${action || ''}
                </div>
            `;
        }
    }
}