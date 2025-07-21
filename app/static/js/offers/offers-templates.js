/**
 * offers-templates.js
 * HTML шаблоны для страницы офферов
 */

export const OffersTemplates = {
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
    },

    // Шаблоны для списка офферов
    offerCard(offer) {
        return `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3 class="offer-title">${offer.title || 'Без названия'}</h3>
                    ${this.statusBadge(offer.status)}
                </div>
                <div class="offer-meta">
                    <span class="offer-price">₽ ${this.formatPrice(offer.price || offer.budget_total || 0)}</span>
                    <span class="offer-category">${offer.category || 'Общее'}</span>
                </div>
                <div class="offer-description">
                    ${offer.description ? (offer.description.length > 100 ? offer.description.substring(0, 100) + '...' : offer.description) : 'Описание отсутствует'}
                </div>
                <div class="offer-actions">
                    ${this.button('👁️ Просмотр', `window.offersManager?.showOfferDetails?.('${offer.id}') || showOfferDetails('${offer.id}')`, 'outline', 'sm')}
                    ${this.button('✏️ Редактировать', `window.offersManager?.editOffer?.('${offer.id}') || editOffer('${offer.id}')`, 'secondary', 'sm')}
                    ${this.button('📊 Статистика', `window.offersManager?.showOfferStats?.('${offer.id}') || showOfferStats('${offer.id}')`, 'primary', 'sm')}
                </div>
            </div>
        `;
    },

    // Шаблон пустого состояния
    emptyState(title, description, actionButton = null) {
        return `
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <h3>${title}</h3>
                <p>${description}</p>
                ${actionButton || ''}
            </div>
        `;
    },

    // Шаблон состояния загрузки
    loadingState(message = 'Загрузка...') {
        return `
            <div class="loading-state">
                <div class="loading-spinner">⏳</div>
                <p>${message}</p>
            </div>
        `;
    },

    // Шаблон состояния ошибки
    errorState(message, retryCallback = null) {
        const retryBtn = retryCallback ? this.button('🔄 Попробовать снова', retryCallback, 'outline') : '';
        return `
            <div class="error-state">
                <div class="error-icon">❌</div>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                ${retryBtn}
            </div>
        `;
    },

    // Вспомогательные методы
    formatPrice(price) {
        const numericPrice = typeof price === 'string'
            ? parseFloat(price.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0
            : (price || 0);
        return numericPrice === 0 ? '0' : numericPrice.toLocaleString('ru-RU', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    }
};