/**
 * offers-modals.js
 * Управление модальными окнами для страницы офферов
 */

export class ModalManager {
    constructor() {
        this.activeModals = new Set();
        this.setupGlobalHandlers();
    }

    // Создание модального окна
    create(id, title, content, options = {}) {
        const { size = 'medium', closable = true, backdrop = true } = options;

        // Удаляем существующее модальное окно
        this.close(id);

        const modal = document.createElement('div');
        modal.id = id;
        modal.className = `modal-overlay modal-${size}`;
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    ${closable ? `<button class="modal-close" onclick="window.modalManager.close('${id}')">&times;</button>` : ''}
                </div>
                <div class="modal-body">${content}</div>
            </div>
        `;

        document.body.appendChild(modal);
        this.activeModals.add(id);

        // Показываем с анимацией
        setTimeout(() => modal.classList.add('active'), 10);

        return modal;
    }

    // Закрытие модального окна
    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            setTimeout(() => {
                modal.remove();
                this.activeModals.delete(modalId);
            }, 300);
        }
    }

    // Закрытие всех модальных окон
    closeAll() {
        this.activeModals.forEach(id => this.close(id));
    }

    // Модальное окно выбора каналов
    createChannelSelection(offerId, offerTitle, channels, isDraft = false) {
        const channelsHtml = channels.map(channel => this.createChannelCard(channel)).join('');
        
        const content = `
            <div class="channel-selection">
                <div class="channel-selection-header">
                    <p>Выберите каналы для размещения оффера: <strong>${offerTitle}</strong></p>
                    <div class="channel-selection-stats">
                        <span id="selected-count">0</span> каналов выбрано
                    </div>
                </div>
                
                <div class="channel-filters">
                    <select id="channel-sort" onchange="window.modalManager.sortChannels(this.value)">
                        <option value="subscribers">По подписчикам</option>
                        <option value="price">По цене</option>
                        <option value="engagement">По вовлеченности</option>
                    </select>
                </div>
                
                <div class="channels-grid" id="channels-grid">
                    ${channelsHtml}
                </div>
                
                <div class="channel-selection-actions">
                    <button class="btn btn-secondary" onclick="window.modalManager.close('channel-selection-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-primary" onclick="window.modalManager.confirmChannelSelection('${offerId}', ${isDraft})">
                        ${isDraft ? 'Завершить и отправить' : 'Отправить предложения'}
                    </button>
                </div>
            </div>
        `;

        return this.create('channel-selection-modal', '📺 Выбор каналов', content, { size: 'large' });
    }

    // Модальное окно принятия предложения
    createAcceptProposal(proposalId, offerTitle) {
        const content = `
            <div class="proposal-action">
                <p>Вы собираетесь принять предложение для оффера: <strong>${offerTitle}</strong></p>
                
                <div class="form-field">
                    <label for="accept-price">Цена размещения (₽)</label>
                    <input type="number" id="accept-price" class="form-input" placeholder="Укажите цену" min="0" required>
                </div>
                
                <div class="form-field">
                    <label for="accept-comment">Комментарий (необязательно)</label>
                    <textarea id="accept-comment" class="form-input" placeholder="Дополнительные условия или комментарии"></textarea>
                </div>
                
                <div class="form-field">
                    <label for="accept-deadline">Срок выполнения</label>
                    <input type="date" id="accept-deadline" class="form-input" min="${new Date().toISOString().split('T')[0]}">
                </div>
                
                <div class="form-actions">
                    <button class="btn btn-secondary" onclick="window.modalManager.close('accept-proposal-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-primary" onclick="window.modalManager.submitAcceptProposal('${proposalId}')">
                        Принять предложение
                    </button>
                </div>
            </div>
        `;

        return this.create('accept-proposal-modal', '✅ Принять предложение', content);
    }

    // Модальное окно отклонения предложения
    createRejectProposal(proposalId, offerTitle) {
        const content = `
            <div class="proposal-action">
                <p>Вы собираетесь отклонить предложение для оффера: <strong>${offerTitle}</strong></p>
                
                <div class="form-field">
                    <label for="reject-reason">Причина отклонения</label>
                    <select id="reject-reason" class="form-input" required>
                        <option value="">Выберите причину</option>
                        <option value="price">Не устраивает цена</option>
                        <option value="timing">Не подходящее время</option>
                        <option value="content">Не подходящий контент</option>
                        <option value="audience">Не целевая аудитория</option>
                        <option value="other">Другая причина</option>
                    </select>
                </div>
                
                <div class="form-field">
                    <label for="reject-comment">Комментарий (необязательно)</label>
                    <textarea id="reject-comment" class="form-input" placeholder="Дополнительные пояснения"></textarea>
                </div>
                
                <div class="form-actions">
                    <button class="btn btn-secondary" onclick="window.modalManager.close('reject-proposal-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-danger" onclick="window.modalManager.submitRejectProposal('${proposalId}')">
                        Отклонить предложение
                    </button>
                </div>
            </div>
        `;

        return this.create('reject-proposal-modal', '❌ Отклонить предложение', content);
    }

    // Модальное окно подтверждения удаления
    createDeleteConfirmation(offerId) {
        const content = `
            <div class="delete-confirmation">
                <div class="confirmation-icon">⚠️</div>
                <h3>Подтверждение удаления</h3>
                <p>Вы действительно хотите удалить этот оффер?</p>
                <p class="warning-text">Это действие нельзя будет отменить.</p>
                
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="window.modalManager?.close?.('delete-confirmation-modal')">
                        Отмена
                    </button>
                    <button type="button" class="btn btn-danger" onclick="window.modalManager?.confirmDelete?.('${offerId}')" style="background: #ef4444; color: white; border: 1px solid #ef4444;">
                        🗑️ Да, удалить
                    </button>
                </div>
            </div>
        `;

        const modal = this.create('delete-confirmation-modal', '🗑️ Удаление оффера', content);
        console.log('🗑️ Создано модальное окно подтверждения удаления для оффера:', offerId);
        return modal;
    }

    // Модальное окно деталей оффера
    createOfferDetails(offer) {
        const content = `
            <div class="offer-details">
                <div class="offer-meta">
                    <div class="meta-item">
                        <span class="meta-label">Статус:</span>
                        <span class="status-badge ${offer.status}">${this.getStatusText(offer.status)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Цена:</span>
                        <span class="meta-value">₽ ${this.formatPrice(offer.price)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Категория:</span>
                        <span class="meta-value">${offer.category || 'Общее'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Создан:</span>
                        <span class="meta-value">${this.formatDate(offer.created_at)}</span>
                    </div>
                </div>
                
                <div class="offer-description">
                    <h4>Описание</h4>
                    <p>${offer.description || 'Описание отсутствует'}</p>
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-primary" onclick="window.modalManager.editOffer('${offer.id}')">
                        ✏️ Редактировать
                    </button>
                    <button class="btn btn-secondary" onclick="window.modalManager.showOfferStats('${offer.id}')">
                        📊 Статистика
                    </button>
                </div>
            </div>
        `;

        return this.create('offer-details-modal', `📝 ${offer.title || 'Детали оффера'}`, content);
    }

    // Уведомления
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Автоматическое скрытие
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
        
        // Закрытие по клику
        notification.querySelector('.notification-close').onclick = () => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        };
    }

    // Вспомогательные методы
    createChannelCard(channel) {
        return `
            <div class="channel-card" data-channel-id="${channel.id}">
                <div class="channel-header">
                    <h4>${channel.title}</h4>
                    <input type="checkbox" class="channel-checkbox" onchange="window.modalManager.toggleChannelSelection(this, '${channel.id}')">
                </div>
                <div class="channel-meta">
                    <span>👥 ${this.formatNumber(channel.subscriber_count)} подписчиков</span>
                    <span>💰 ₽ ${this.formatPrice(channel.price)}</span>
                </div>
            </div>
        `;
    }

    toggleChannelSelection(checkbox, channelId) {
        // Логика выбора каналов
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        const selected = document.querySelectorAll('.channel-checkbox:checked').length;
        const counter = document.getElementById('selected-count');
        if (counter) counter.textContent = selected;
    }

    sortChannels(sortBy) {
        // Логика сортировки каналов
        console.log('Сортировка каналов по:', sortBy);
    }

    // Обработчики действий
    async confirmChannelSelection(offerId, isDraft) {
        const selectedChannels = Array.from(document.querySelectorAll('.channel-checkbox:checked'))
            .map(cb => cb.closest('.channel-card').dataset.channelId);
        
        if (selectedChannels.length === 0) {
            this.showNotification('Выберите хотя бы один канал', 'warning');
            return;
        }

        try {
            // Здесь должна быть логика отправки предложений
            this.showNotification('Предложения отправлены успешно!', 'success');
            this.close('channel-selection-modal');
        } catch (error) {
            this.showNotification('Ошибка отправки предложений: ' + error.message, 'error');
        }
    }

    async submitAcceptProposal(proposalId) {
        const price = document.getElementById('accept-price').value;
        const comment = document.getElementById('accept-comment').value;
        const deadline = document.getElementById('accept-deadline').value;

        if (!price) {
            this.showNotification('Укажите цену размещения', 'warning');
            return;
        }

        try {
            // Здесь должна быть логика принятия предложения
            this.showNotification('Предложение принято!', 'success');
            this.close('accept-proposal-modal');
        } catch (error) {
            this.showNotification('Ошибка: ' + error.message, 'error');
        }
    }

    async submitRejectProposal(proposalId) {
        const reason = document.getElementById('reject-reason').value;
        const comment = document.getElementById('reject-comment').value;

        if (!reason) {
            this.showNotification('Выберите причину отклонения', 'warning');
            return;
        }

        try {
            // Здесь должна быть логика отклонения предложения
            this.showNotification('Предложение отклонено', 'success');
            this.close('reject-proposal-modal');
        } catch (error) {
            this.showNotification('Ошибка: ' + error.message, 'error');
        }
    }

    async confirmDelete(offerId) {
        console.log('🗑️ Подтверждение удаления оффера:', offerId);
        
        try {
            // Закрываем модальное окно подтверждения
            this.close('delete-confirmation-modal');
            
            // Вызываем метод удаления из OffersManager
            if (window.offersManager) {
                console.log('✅ Вызываем confirmDeleteOffer для оффера:', offerId);
                await window.offersManager.confirmDeleteOffer(offerId);
            } else {
                console.error('❌ Менеджер офферов недоступен');
                this.showNotification('Ошибка: менеджер офферов недоступен', 'error');
            }
        } catch (error) {
            console.error('❌ Ошибка удаления:', error);
            this.showNotification('Ошибка удаления: ' + error.message, 'error');
        }
    }

    // Глобальные обработчики событий
    setupGlobalHandlers() {
        // Закрытие по клику вне модального окна
        document.addEventListener('click', (event) => {
            if (event.target.classList.contains('modal-overlay')) {
                const modalId = event.target.id;
                if (modalId) this.close(modalId);
            }
        });

        // Закрытие по Escape
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeAll();
            }
        });
    }

    // Утилиты форматирования
    formatPrice(price) {
        const numericPrice = typeof price === 'string'
            ? parseFloat(price.replace(/[^0-9.,]/g, '').replace(',', '.')) || 0
            : (price || 0);
        return numericPrice === 0 ? '0' : numericPrice.toLocaleString('ru-RU');
    }

    formatNumber(num) {
        return num ? new Intl.NumberFormat('ru-RU').format(num) : '0';
    }

    formatDate(dateString) {
        if (!dateString) return 'Не указано';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (error) {
            return 'Ошибка даты';
        }
    }

    getStatusText(status) {
        const statusTexts = {
            active: '✅ Активен',
            draft: '📝 Черновик', 
            completed: '✅ Завершен',
            paused: '⏸️ Приостановлен'
        };
        return statusTexts[status] || statusTexts.active;
    }
}