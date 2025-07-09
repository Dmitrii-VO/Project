// app/static/js/offers_management.js
// Управление офферами - модальные окна и интерфейс

class OffersManagement {
    constructor() {
        this.currentOffer = null;
        this.selectedChannels = new Set();
        this.recommendedChannels = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadOffers();
        console.log('📊 Offers Management initialized');
    }

    setupEventListeners() {
        // Кнопки действий
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-recommended-channels')) {
                this.showRecommendedChannels(e.target.dataset.offerId);
            }
            if (e.target.matches('.btn-offer-details')) {
                this.showOfferDetails(e.target.dataset.offerId);
            }
            if (e.target.matches('.btn-mark-advertising')) {
                this.markAsAdvertising(e.target.dataset.offerId);
            }
            if (e.target.matches('.btn-launch-campaign')) {
                this.launchCampaign();
            }
            if (e.target.matches('.channel-select-checkbox')) {
                this.toggleChannelSelection(e.target);
            }
        });

        // Закрытие модальных окон
        document.addEventListener('click', (e) => {
            if (e.target.matches('.modal-overlay')) {
                this.closeModal();
            }
        });

        // ESC для закрытия модальных окон
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    async loadOffers() {
        try {
            const response = await fetch('/api/offers');
            const data = await response.json();
            
            if (data.success) {
                this.renderOffers(data.offers);
            } else {
                this.showError('Ошибка загрузки офферов');
            }
        } catch (error) {
            console.error('Error loading offers:', error);
            this.showError('Ошибка загрузки офферов');
        }
    }

    renderOffers(offers) {
        const container = document.getElementById('offers-container');
        if (!container) return;

        if (offers.length === 0) {
            container.innerHTML = this.getEmptyStateHTML();
            return;
        }

        container.innerHTML = offers.map(offer => this.getOfferCardHTML(offer)).join('');
    }

    getEmptyStateHTML() {
        return `
            <div class="empty-state">
                <span class="stat-icon">🎯</span>
                <h3>Нет офферов</h3>
                <p>Создайте первый оффер, чтобы начать рекламную кампанию</p>
                <button class="btn btn-primary" onclick="createNewOffer()">
                    <span>➕</span> Создать оффер
                </button>
            </div>
        `;
    }

    getOfferCardHTML(offer) {
        const statusClass = this.getStatusClass(offer.status);
        const statusText = this.getStatusText(offer.status);
        
        return `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3>${offer.title}</h3>
                    <span class="offer-status ${statusClass}">${statusText}</span>
                </div>
                
                <div class="offer-content">
                    <p class="offer-description">${offer.description || 'Описание отсутствует'}</p>
                    
                    <div class="offer-stats">
                        <div class="stat-item">
                            <span class="stat-label">💰 Бюджет:</span>
                            <span class="stat-value">${offer.budget || 0} ₽</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">📊 Предложений:</span>
                            <span class="stat-value">${offer.proposals_count || 0}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">✅ Принято:</span>
                            <span class="stat-value">${offer.accepted_count || 0}</span>
                        </div>
                    </div>
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-secondary btn-offer-details" 
                            data-offer-id="${offer.id}">
                        <span>📋</span> Подробнее
                    </button>
                    
                    ${this.getOfferActionsHTML(offer)}
                </div>
                
                <div class="offer-meta">
                    <div class="offer-meta-left">
                        <span class="meta-item">
                            <span>📅</span> ${this.formatDate(offer.created_at)}
                        </span>
                        ${offer.is_marked ? '<span class="meta-item marked">🏷️ Промаркировано</span>' : ''}
                    </div>
                </div>
            </div>
        `;
    }

    getOfferActionsHTML(offer) {
        switch (offer.status) {
            case 'draft':
            case 'matching':
                return `
                    <button class="btn btn-primary btn-recommended-channels" 
                            data-offer-id="${offer.id}">
                        <span>🎯</span> Рекомендованные каналы
                    </button>
                    <button class="btn btn-secondary btn-mark-advertising" 
                            data-offer-id="${offer.id}">
                        <span>🏷️</span> Маркировать
                    </button>
                `;
            case 'started':
            case 'in_progress':
                return `
                    <button class="btn btn-primary" 
                            onclick="window.location.href='/offers/${offer.id}/statistics'">
                        <span>📊</span> Статистика
                    </button>
                `;
            case 'completed':
                return `
                    <button class="btn btn-success" 
                            onclick="window.location.href='/offers/${offer.id}/statistics'">
                        <span>✅</span> Результаты
                    </button>
                `;
            default:
                return '';
        }
    }

    async showRecommendedChannels(offerId) {
        try {
            this.currentOffer = offerId;
            this.selectedChannels.clear();
            
            // Показываем модальное окно с лоадером
            this.showModal(this.getLoadingModalHTML('Загрузка рекомендованных каналов...'));
            
            const response = await fetch(`/api/offers/${offerId}/recommended-channels`);
            const data = await response.json();
            
            if (data.success) {
                this.recommendedChannels = data.channels;
                this.showModal(this.getRecommendedChannelsModalHTML(data));
            } else {
                this.showError('Ошибка загрузки рекомендованных каналов');
                this.closeModal();
            }
        } catch (error) {
            console.error('Error loading recommended channels:', error);
            this.showError('Ошибка загрузки рекомендованных каналов');
            this.closeModal();
        }
    }

    getRecommendedChannelsModalHTML(data) {
        return `
            <div class="modal-content large-modal">
                <div class="modal-header">
                    <h2>🎯 Рекомендованные каналы</h2>
                    <button class="modal-close" onclick="offersManagement.closeModal()">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="offer-info">
                        <h3>${data.offer_title}</h3>
                        <p>Статус: <span class="offer-status ${this.getStatusClass(data.offer_status)}">${this.getStatusText(data.offer_status)}</span></p>
                        <p>Найдено каналов: <strong>${data.total_channels}</strong></p>
                    </div>
                    
                    <div class="channels-filters">
                        <div class="filter-group">
                            <label>Категория:</label>
                            <select class="form-select" onchange="offersManagement.filterChannels()">
                                <option value="">Все категории</option>
                                <option value="tech">Технологии</option>
                                <option value="business">Бизнес</option>
                                <option value="entertainment">Развлечения</option>
                                <option value="education">Образование</option>
                                <option value="other">Другое</option>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label>Мин. подписчиков:</label>
                            <input type="number" class="form-input" placeholder="1000" 
                                   onchange="offersManagement.filterChannels()">
                        </div>
                    </div>
                    
                    <div class="channels-list">
                        ${data.channels.map(channel => this.getChannelCardHTML(channel)).join('')}
                    </div>
                </div>
                
                <div class="modal-footer">
                    <div class="selected-info">
                        <span id="selected-count">0</span> каналов выбрано
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-secondary" onclick="offersManagement.closeModal()">
                            Отмена
                        </button>
                        <button class="btn btn-primary btn-launch-campaign" disabled>
                            <span>🚀</span> Запустить кампанию
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getChannelCardHTML(channel) {
        const isSelected = this.selectedChannels.has(channel.id);
        const compatibilityStars = '★'.repeat(Math.min(channel.compatibility_score, 5));
        
        return `
            <div class="channel-card ${isSelected ? 'selected' : ''}" data-channel-id="${channel.id}">
                <div class="channel-header">
                    <label class="channel-select">
                        <input type="checkbox" class="channel-select-checkbox" 
                               data-channel-id="${channel.id}" ${isSelected ? 'checked' : ''}>
                        <span class="channel-title">${channel.title}</span>
                        ${channel.is_verified ? '<span class="verified-badge">✅</span>' : ''}
                    </label>
                    <span class="compatibility-score" title="Совместимость">
                        ${compatibilityStars} ${channel.compatibility_score}/5
                    </span>
                </div>
                
                <div class="channel-info">
                    <div class="channel-stats">
                        <span class="stat-item">👥 ${this.formatNumber(channel.subscriber_count)}</span>
                        <span class="stat-item">📊 ${channel.category}</span>
                        <span class="stat-item">💰 ~${channel.estimated_cost} ₽</span>
                    </div>
                    
                    ${channel.username ? `<div class="channel-link">
                        <a href="https://t.me/${channel.username}" target="_blank">
                            🔗 @${channel.username}
                        </a>
                    </div>` : ''}
                    
                    ${channel.description ? `<div class="channel-description">
                        ${channel.description.substring(0, 150)}${channel.description.length > 150 ? '...' : ''}
                    </div>` : ''}
                </div>
                
                <div class="channel-status">
                    <span class="proposal-status ${this.getProposalStatusClass(channel.proposal_status)}">
                        ${this.getProposalStatusText(channel.proposal_status)}
                    </span>
                </div>
            </div>
        `;
    }

    toggleChannelSelection(checkbox) {
        const channelId = parseInt(checkbox.dataset.channelId);
        const channelCard = checkbox.closest('.channel-card');
        
        if (checkbox.checked) {
            this.selectedChannels.add(channelId);
            channelCard.classList.add('selected');
        } else {
            this.selectedChannels.delete(channelId);
            channelCard.classList.remove('selected');
        }
        
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        const countElement = document.getElementById('selected-count');
        if (countElement) {
            countElement.textContent = this.selectedChannels.size;
        }
        
        const launchButton = document.querySelector('.btn-launch-campaign');
        if (launchButton) {
            launchButton.disabled = this.selectedChannels.size === 0;
        }
    }

    async launchCampaign() {
        if (this.selectedChannels.size === 0) {
            this.showError('Выберите хотя бы один канал');
            return;
        }

        try {
            const launchButton = document.querySelector('.btn-launch-campaign');
            const originalText = launchButton.innerHTML;
            launchButton.innerHTML = '<span class="loading-spinner"></span> Запуск...';
            launchButton.disabled = true;

            const response = await fetch(`/api/offers/${this.currentOffer}/select-channels`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    channel_ids: Array.from(this.selectedChannels),
                    expected_duration: 7
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess(`Кампания запущена! Отправлено ${data.created_proposals} предложений.`);
                this.closeModal();
                this.loadOffers(); // Обновляем список офферов
            } else {
                this.showError('Ошибка запуска кампании');
            }
        } catch (error) {
            console.error('Error launching campaign:', error);
            this.showError('Ошибка запуска кампании');
        }
    }

    async markAsAdvertising(offerId) {
        try {
            const response = await fetch(`/api/offers/${offerId}/mark-as-advertising`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ marked: true })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Оффер помечен как реклама');
                this.loadOffers(); // Обновляем список
            } else {
                this.showError('Ошибка маркировки');
            }
        } catch (error) {
            console.error('Error marking as advertising:', error);
            this.showError('Ошибка маркировки');
        }
    }

    async showOfferDetails(offerId) {
        try {
            const response = await fetch(`/api/offers/${offerId}/statistics`);
            const data = await response.json();

            if (data.success) {
                this.showModal(this.getOfferDetailsModalHTML(data));
            } else {
                this.showError('Ошибка загрузки деталей оффера');
            }
        } catch (error) {
            console.error('Error loading offer details:', error);
            this.showError('Ошибка загрузки деталей оффера');
        }
    }

    getOfferDetailsModalHTML(data) {
        return `
            <div class="modal-content large-modal">
                <div class="modal-header">
                    <h2>📊 ${data.offer_title}</h2>
                    <button class="modal-close" onclick="offersManagement.closeModal()">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="offer-details-tabs">
                        <div class="tab-nav">
                            <button class="tab-btn active" data-tab="overview">Обзор</button>
                            <button class="tab-btn" data-tab="proposals">Предложения</button>
                            <button class="tab-btn" data-tab="analytics">Аналитика</button>
                        </div>
                        
                        <div class="tab-content active" data-tab="overview">
                            ${this.getOfferOverviewHTML(data)}
                        </div>
                        
                        <div class="tab-content" data-tab="proposals">
                            ${this.getOfferProposalsHTML(data)}
                        </div>
                        
                        <div class="tab-content" data-tab="analytics">
                            ${this.getOfferAnalyticsHTML(data)}
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="offersManagement.closeModal()">
                        Закрыть
                    </button>
                </div>
            </div>
        `;
    }

    getOfferOverviewHTML(data) {
        return `
            <div class="offer-overview">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">📤</div>
                        <div class="stat-content">
                            <div class="stat-number">${data.summary.total_proposals}</div>
                            <div class="stat-label">Всего предложений</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-content">
                            <div class="stat-number">${data.summary.accepted_count}</div>
                            <div class="stat-label">Принято</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">❌</div>
                        <div class="stat-content">
                            <div class="stat-number">${data.summary.rejected_count}</div>
                            <div class="stat-label">Отклонено</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">👁</div>
                        <div class="stat-content">
                            <div class="stat-number">${this.formatNumber(data.summary.total_views)}</div>
                            <div class="stat-label">Просмотры</div>
                        </div>
                    </div>
                </div>
                
                <div class="offer-progress">
                    <div class="progress-item">
                        <div class="progress-label">Коэффициент принятия</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.summary.acceptance_rate}%"></div>
                        </div>
                        <div class="progress-value">${data.summary.acceptance_rate}%</div>
                    </div>
                    
                    <div class="progress-item">
                        <div class="progress-label">Коэффициент отклонения</div>
                        <div class="progress-bar">
                            <div class="progress-fill danger" style="width: ${data.summary.rejection_rate}%"></div>
                        </div>
                        <div class="progress-value">${data.summary.rejection_rate}%</div>
                    </div>
                </div>
            </div>
        `;
    }

    getOfferProposalsHTML(data) {
        return `
            <div class="proposals-list">
                ${data.proposals.map(proposal => `
                    <div class="proposal-card">
                        <div class="proposal-header">
                            <h4>${proposal.channel_title}</h4>
                            <span class="proposal-status ${this.getProposalStatusClass(proposal.status)}">
                                ${this.getProposalStatusText(proposal.status)}
                            </span>
                        </div>
                        
                        <div class="proposal-content">
                            <div class="proposal-stats">
                                <span class="stat-item">👥 ${this.formatNumber(proposal.subscriber_count)}</span>
                                <span class="stat-item">📊 ${proposal.category}</span>
                                ${proposal.final_views_count ? `<span class="stat-item">👁 ${this.formatNumber(proposal.final_views_count)}</span>` : ''}
                            </div>
                            
                            ${proposal.rejection_reason ? `
                                <div class="rejection-reason">
                                    <strong>Причина отклонения:</strong> ${proposal.rejection_reason}
                                </div>
                            ` : ''}
                            
                            ${proposal.post_url ? `
                                <div class="post-link">
                                    <a href="${proposal.post_url}" target="_blank">🔗 Посмотреть пост</a>
                                </div>
                            ` : ''}
                        </div>
                        
                        <div class="proposal-meta">
                            <span class="meta-item">📅 ${this.formatDate(proposal.created_at)}</span>
                            ${proposal.responded_at ? `<span class="meta-item">✅ ${this.formatDate(proposal.responded_at)}</span>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    getOfferAnalyticsHTML(data) {
        return `
            <div class="analytics-content">
                <div class="analytics-section">
                    <h3>📊 Общая статистика</h3>
                    <div class="analytics-grid">
                        <div class="analytics-item">
                            <div class="analytics-label">Общий бюджет</div>
                            <div class="analytics-value">${data.offer_budget} ₽</div>
                        </div>
                        <div class="analytics-item">
                            <div class="analytics-label">Потрачено</div>
                            <div class="analytics-value">${data.summary.total_spent} ₽</div>
                        </div>
                        <div class="analytics-item">
                            <div class="analytics-label">Среднее CPM</div>
                            <div class="analytics-value">${this.calculateCPM(data.summary.total_spent, data.summary.total_views)} ₽</div>
                        </div>
                    </div>
                </div>
                
                <div class="analytics-section">
                    <h3>🎯 Эффективность каналов</h3>
                    <div class="top-channels">
                        ${data.proposals
                            .filter(p => p.final_views_count > 0)
                            .sort((a, b) => b.final_views_count - a.final_views_count)
                            .slice(0, 5)
                            .map(proposal => `
                                <div class="top-channel-item">
                                    <div class="channel-info">
                                        <strong>${proposal.channel_title}</strong>
                                        <span>👥 ${this.formatNumber(proposal.subscriber_count)}</span>
                                    </div>
                                    <div class="channel-performance">
                                        <span class="views">👁 ${this.formatNumber(proposal.final_views_count)}</span>
                                    </div>
                                </div>
                            `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    // Utility methods
    showModal(content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        // Анимация появления
        setTimeout(() => modal.classList.add('active'), 10);
    }

    closeModal() {
        const modal = document.querySelector('.modal-overlay');
        if (modal) {
            modal.classList.remove('active');
            setTimeout(() => modal.remove(), 300);
        }
    }

    getLoadingModalHTML(message) {
        return `
            <div class="modal-content">
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <p>${message}</p>
                </div>
            </div>
        `;
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
            <span class="notification-message">${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    getStatusClass(status) {
        const classes = {
            'draft': 'status-draft',
            'matching': 'status-matching',
            'started': 'status-started',
            'in_progress': 'status-active',
            'completed': 'status-completed',
            'cancelled': 'status-cancelled'
        };
        return classes[status] || 'status-unknown';
    }

    getStatusText(status) {
        const texts = {
            'draft': 'Черновик',
            'matching': 'Подбор каналов',
            'started': 'Запущен',
            'in_progress': 'В процессе',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        };
        return texts[status] || 'Неизвестно';
    }

    getProposalStatusClass(status) {
        const classes = {
            'not_sent': 'status-not-sent',
            'sent': 'status-sent',
            'accepted': 'status-accepted',
            'rejected': 'status-rejected',
            'expired': 'status-expired'
        };
        return classes[status] || 'status-unknown';
    }

    getProposalStatusText(status) {
        const texts = {
            'not_sent': 'Новый',
            'sent': 'Отправлено',
            'accepted': 'Принято',
            'rejected': 'Отклонено',
            'expired': 'Истекло'
        };
        return texts[status] || 'Неизвестно';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return Math.floor(num / 100000) / 10 + 'M';
        }
        if (num >= 1000) {
            return Math.floor(num / 100) / 10 + 'K';
        }
        return num.toString();
    }

    calculateCPM(spent, views) {
        if (views === 0) return 0;
        return Math.round((spent / views) * 1000 * 100) / 100;
    }
}

// Инициализация
let offersManagement;
document.addEventListener('DOMContentLoaded', () => {
    offersManagement = new OffersManagement();
});

// Вспомогательные функции
function goBack() {
    window.history.back();
}

function createNewOffer() {
    window.location.href = '/offers/create';
}

function switchTab(tabName) {
    // Обновляем навигацию
    document.querySelectorAll('.nav-card').forEach(card => {
        card.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Показываем соответствующий контент
    // Здесь можно добавить логику переключения вкладок
}

// Экспорт для использования в других модулях
window.OffersManagement = OffersManagement;