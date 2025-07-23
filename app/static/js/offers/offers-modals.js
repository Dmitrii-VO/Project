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
        console.log('🔍 Создание модального окна с каналами:', channels.length);
        console.log('🔍 Первый канал:', channels[0]);
        
        const channelsHtml = channels.map((channel, index) => {
            this.currentChannelNumber = index + 1;
            const cardHtml = this.createChannelCard(channel);
            console.log(`🔍 Карточка ${index + 1} создана, HTML содержит channel-card-compact:`, cardHtml.includes('channel-card-compact'));
            return cardHtml;
        }).join('');
        
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
                    <label for="accept-comment">Комментарий (необязательно)</label>
                    <textarea id="accept-comment" class="form-input" placeholder="Дополнительные условия или комментарии" rows="3"></textarea>
                </div>
                
                <div class="form-field">
                    <label for="accept-deadline">Дата размещения (необязательно)</label>
                    <input type="date" id="accept-deadline" class="form-input" min="${new Date().toISOString().split('T')[0]}">
                    <div class="form-help">Если не указано, размещение ожидается в течение 24 часов</div>
                </div>
                
                <div class="form-actions">
                    <button class="btn btn-secondary" onclick="window.modalManager.close('accept-proposal-modal')">
                        Отмена
                    </button>
                    <button class="btn btn-primary" onclick="window.modalManager.submitAcceptProposal('${proposalId}')">
                        ✅ Принять предложение
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

    // Модальное окно редактирования оффера
    createEditOffer(offer) {
        const content = `
            <div class="edit-offer">
                <form id="edit-offer-form" onsubmit="return false;" onclick="event.stopPropagation();">
                    <div class="form-field">
                        <label for="edit-budget">Бюджет (₽) <span class="required">*</span></label>
                        <input type="number" id="edit-budget" class="form-input" value="${offer.budget_total || offer.price || ''}" placeholder="100000" min="100" required onclick="event.stopPropagation();">
                    </div>
                    
                    <div class="form-field">
                        <label for="edit-description">Объявление <span class="required">*</span></label>
                        <textarea id="edit-description" class="form-input" rows="4" placeholder="Подробное описание задачи и требований" required onclick="event.stopPropagation();">${offer.description || ''}</textarea>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="event.stopPropagation(); window.modalManager?.close?.('edit-offer-modal');">
                            Отмена
                        </button>
                        <button type="button" class="btn btn-primary" onclick="event.stopPropagation(); window.modalManager?.saveOfferEdit?.('${offer.id}');">
                            💾 Сохранить и отправить на модерацию
                        </button>
                    </div>
                </form>
            </div>
        `;

        const modal = this.create('edit-offer-modal', '✏️ Редактирование оффера', content, { size: 'medium' });
        console.log('✏️ Создано модальное окно редактирования для оффера:', offer.id);
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
        // Создаем или находим контейнер для уведомлений
        let container = document.getElementById('notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications-container';
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        // Добавляем в контейнер
        container.appendChild(notification);
        
        // Показываем с анимацией
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Функция скрытия
        const hideNotification = () => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
                // Удаляем контейнер если он пустой
                if (container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        };
        
        // Автоматическое скрытие
        setTimeout(hideNotification, duration);
        
        // Закрытие по клику
        notification.querySelector('.notification-close').onclick = hideNotification;
        
        // Ограничиваем количество уведомлений
        const notifications = container.querySelectorAll('.notification');
        if (notifications.length > 3) {
            const oldest = notifications[0];
            oldest.classList.remove('show');
            setTimeout(() => {
                if (oldest.parentNode) {
                    oldest.remove();
                }
            }, 300);
        }
    }

    // Вспомогательные методы
    createChannelCard(channel) {
        const username = channel.username || channel.channel_username || '';
        const displayUsername = username.startsWith('@') ? username : (username ? `@${username}` : '');
        const price = channel.price_per_post || channel.price || 0;
        // Используем реальные данные цены за 24ч из базы данных
        const price24h = channel.price_per_24h || channel.price_24h || price || 0;
        const subscribers = channel.subscriber_count || 0;
        const engagement = channel.engagement_rate || this.calculateEngagement(subscribers);
        const views = channel.avg_views || Math.round(subscribers * 0.3);
        const ads7days = channel.ads_count_7d || 0;
        const description = channel.description || channel.channel_description || '';
        const truncatedDesc = description.length > 60 ? description.substring(0, 60) + '...' : description;
        
        return `
            <div class="channel-card-compact" data-channel-id="${channel.id}">
                <div class="channel-header">
                    <div class="channel-number">${this.currentChannelNumber || 1}.</div>
                    <div class="channel-info">
                        <h4 class="channel-title">${channel.title || channel.channel_name || 'Канал'}</h4>
                        <p class="channel-description">${truncatedDesc}</p>
                        ${displayUsername ? `<span class="channel-username">${displayUsername}</span>` : ''}
                    </div>
                </div>

                <div class="channel-stats">
                    <div class="stats-grid">
                        <!-- Первая строка: Подписчики + Вовлеченность -->
                        <div class="stat-item">
                            <span class="stat-label">Подписчики</span>
                            <span class="stat-value">👥 ${this.formatNumber(subscribers)}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Вовлеченность (ER)</span>
                            <span class="stat-value">📊 ${engagement}%</span>
                        </div>
                        <!-- Вторая строка: Просмотры + Реклама -->
                        <div class="stat-item">
                            <span class="stat-label">Просмотры</span>
                            <span class="stat-value">👁 ${this.formatNumber(views)}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Реклама за 7 дней</span>
                            <span class="stat-value">📢 ${ads7days}</span>
                        </div>
                    </div>
                </div>

                <div class="channel-pricing">
                    <div class="price-item">
                        <span class="price-label">Цена за просмотр:</span>
                        <span class="price-value">${price > 0 && views > 0 ? (price / views * 1000).toFixed(2) : '0.50'}Р</span>
                    </div>
                    <div class="price-item">
                        <span class="price-label">Цена за 24ч:</span>
                        <span class="price-value">${price24h > 0 ? this.formatPrice(price24h) : this.formatPrice(price)}Р</span>
                    </div>
                </div>

                <div class="channel-actions">
                    <button type="button" class="btn-details" onclick="window.modalManager.showChannelDetails('${channel.id}')">
                        Подробнее
                    </button>
                    <button type="button" class="btn-add" onclick="window.modalManager.toggleChannelSelection(this, '${channel.id}')">
                        Добавить
                    </button>
                </div>

                <!-- Скрытая детальная информация -->
                <div class="channel-details" id="details-${channel.id}" style="display: none;">
                    <div class="demographics">
                        <h5>Гендер</h5>
                        <div class="gender-stats">
                            <span>М:${channel.male_percent || '65'}%</span>
                            <span>Ж:${channel.female_percent || '35'}%</span>
                        </div>
                    </div>
                    <div class="age-groups">
                        <h5>Возрастные группы</h5>
                        <div class="age-stats">
                            <span>18-24: ${channel.age_18_24 || '5'}%</span>
                            <span>25-30: ${channel.age_25_30 || '20'}%</span>
                            <span>35-30: ${channel.age_35_44 || '25'}%</span>
                            <span>45-25: ${channel.age_45_54 || '25'}%</span>
                            <span>55-15: ${channel.age_55_64 || '15'}%</span>
                            <span>65-5: ${channel.age_65_plus || '5'}%</span>
                        </div>
                    </div>
                    <div class="income-level">
                        <h5>Уровень дохода</h5>
                        <div class="income-stats">
                            <span>↓50%</span>
                            <span>↑30%</span>
                            <span>↑20%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Показать/скрыть детальную информацию о канале
    showChannelDetails(channelId) {
        const detailsElement = document.getElementById(`details-${channelId}`);
        const button = document.querySelector(`[onclick="window.modalManager.showChannelDetails('${channelId}')"]`);
        
        if (detailsElement && button) {
            if (detailsElement.style.display === 'none' || detailsElement.style.display === '') {
                detailsElement.style.display = 'block';
                button.textContent = 'Скрыть';
                button.classList.add('active');
            } else {
                detailsElement.style.display = 'none';
                button.textContent = 'Подробнее';
                button.classList.remove('active');
            }
        }
    }

    // Переключение выбора канала (теперь работает с кнопкой "Добавить")
    toggleChannelSelection(button, channelId) {
        const channelCard = button.closest('.channel-card-compact');
        
        if (channelCard.classList.contains('selected')) {
            // Убираем выбор
            channelCard.classList.remove('selected');
            button.textContent = 'Добавить';
            button.classList.remove('selected');
        } else {
            // Добавляем выбор
            channelCard.classList.add('selected');
            button.textContent = '✓ Добавлен';
            button.classList.add('selected');
        }
        
        this.updateSelectedCount();
    }

    // Вспомогательные методы
    calculateEngagement(subscribers) {
        // Простая формула для расчета ER на основе подписчиков
        if (subscribers < 1000) return '45';
        if (subscribers < 10000) return '32';
        if (subscribers < 100000) return '25';
        return '16';
    }

    updateSelectedCount() {
        const selected = document.querySelectorAll('.channel-card-compact.selected').length;
        const counter = document.getElementById('selected-count');
        if (counter) counter.textContent = selected;
    }

    sortChannels(sortBy) {
        // Логика сортировки каналов
        console.log('Сортировка каналов по:', sortBy);
    }

    // Обработчики действий
    async confirmChannelSelection(offerId, isDraft) {
        const selectedChannels = Array.from(document.querySelectorAll('.channel-card-compact.selected'))
            .map(card => card.dataset.channelId);
        
        if (selectedChannels.length === 0) {
            this.showNotification('Выберите хотя бы один канал', 'warning');
            return;
        }

        try {
            console.log(`📤 Завершение оффера ${offerId} с ${selectedChannels.length} выбранными каналами`);
            
            // Используем API для завершения оффера
            const response = await fetch(`/api/offers_moderation/complete/${offerId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                },
                body: JSON.stringify({
                    channels: selectedChannels
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(
                    `✅ Оффер отправлен на модерацию с ${result.channels_count} каналами!`, 
                    'success'
                );
                this.close('channel-selection-modal');
                
                // Обновляем список офферов если есть менеджер
                if (window.offersManager && window.offersManager.loadMyOffers) {
                    setTimeout(() => {
                        window.offersManager.loadMyOffers();
                    }, 1000);
                }
            } else {
                throw new Error(result.error || 'Неизвестная ошибка');
            }
            
        } catch (error) {
            console.error('❌ Ошибка завершения оффера:', error);
            this.showNotification('Ошибка отправки предложений: ' + error.message, 'error');
        }
    }

    async submitAcceptProposal(proposalId) {
        const comment = document.getElementById('accept-comment').value;
        const deadline = document.getElementById('accept-deadline').value;

        try {
            console.log('✅ Принятие предложения:', proposalId);
            
            // Формируем данные для отправки
            const data = {
                message: comment || '',
                scheduled_date: deadline ? `${deadline}T12:00:00` : null
            };

            // Отправляем запрос на API
            const response = await fetch(`/api/proposals/${proposalId}/accept`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('✅ Предложение принято!', 'success');
                this.close('accept-proposal-modal');
                
                // Обновляем список офферов
                if (window.offersManager?.loadAvailableOffers) {
                    setTimeout(() => window.offersManager.loadAvailableOffers(), 500);
                }
            } else {
                throw new Error(result.message || 'Ошибка принятия предложения');
            }
        } catch (error) {
            console.error('❌ Ошибка принятия предложения:', error);
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
            console.log('❌ Отклонение предложения:', proposalId);
            
            // Формируем данные для отправки
            const data = {
                reason: comment || 'Не указано',
                reason_category: reason,
                custom_reason: comment || ''
            };

            // Отправляем запрос на API
            const response = await fetch(`/api/proposals/${proposalId}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('❌ Предложение отклонено', 'success');
                this.close('reject-proposal-modal');
                
                // Обновляем список офферов
                if (window.offersManager?.loadAvailableOffers) {
                    setTimeout(() => window.offersManager.loadAvailableOffers(), 500);
                }
            } else {
                throw new Error(result.message || 'Ошибка отклонения предложения');
            }
        } catch (error) {
            console.error('❌ Ошибка отклонения предложения:', error);
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

    async saveOfferEdit(offerId) {
        console.log('💾 Сохранение изменений оффера:', offerId);
        
        try {
            // Получаем данные из упрощенной формы
            const budget = document.getElementById('edit-budget').value.trim();
            const description = document.getElementById('edit-description').value.trim();
            
            // Валидация
            if (!description) {
                this.showNotification('Введите текст объявления', 'warning');
                return;
            }
            
            if (!budget || parseFloat(budget) < 100) {
                this.showNotification('Укажите корректный бюджет (от 100 руб.)', 'warning');
                return;
            }
            
            // Подготавливаем данные для отправки (сохраняем остальные поля неизменными)
            const formData = {
                budget_total: parseFloat(budget),
                description: description
            };
            
            console.log('📋 Отправляем данные:', formData);
            
            // Отправляем запрос на обновление оффера
            const response = await fetch(`/api/offers_moderation/${offerId}/update`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': window.getTelegramUserId?.() || '373086959'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('✅ Оффер успешно обновлен и отправлен на модерацию!', 'success');
                this.close('edit-offer-modal');
                
                // Принудительно обновляем списки офферов и модерации
                if (window.offersManager) {
                    console.log('🔄 Принудительное обновление списков после редактирования');
                    
                    // Немедленно обновляем без задержки
                    if (window.offersManager.loadMyOffers) {
                        window.offersManager.loadMyOffers();
                    }
                    
                    // Обновляем также список модерации для админа
                    if (window.offersManager.loadModerationOffers) {
                        window.offersManager.loadModerationOffers();
                    }
                    
                    // Дополнительное обновление через секунду на случай задержек сервера
                    setTimeout(() => {
                        console.log('🔄 Повторное обновление списков (через 1 сек)');
                        if (window.offersManager.loadMyOffers) {
                            window.offersManager.loadMyOffers();
                        }
                        if (window.offersManager.loadModerationOffers) {
                            window.offersManager.loadModerationOffers();
                        }
                    }, 1000);
                }
            } else {
                throw new Error(result.error || 'Неизвестная ошибка');
            }
            
        } catch (error) {
            console.error('❌ Ошибка сохранения изменений:', error);
            this.showNotification('Ошибка сохранения: ' + error.message, 'error');
        }
    }

    // Глобальные обработчики событий
    setupGlobalHandlers() {
        // Закрытие по клику вне модального окна (только если клик именно по overlay, а не по его содержимому)
        document.addEventListener('click', (event) => {
            if (event.target.classList.contains('modal-overlay') && event.target === event.currentTarget) {
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

// Экспорт по умолчанию
export default ModalManager;