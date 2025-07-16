/**
 * Система уведомлений для веб-интерфейса
 * Отображает счетчики новых откликов и уведомления
 */

class NotificationSystem {
    constructor() {
        this.checkInterval = 30000; // 30 секунд
        this.notificationBadge = null;
        this.init();
    }

    init() {
        this.createNotificationBadge();
        this.startPeriodicCheck();
        this.bindEvents();
    }

    /**
     * Создает значок уведомлений в шапке
     */
    createNotificationBadge() {
        // Ищем место для значка уведомлений
        const header = document.querySelector('header, .header, .navbar');
        if (!header) return;

        // Создаем контейнер для уведомлений
        const notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container';
        notificationContainer.innerHTML = `
            <div class="notification-bell" id="notification-bell">
                <span class="bell-icon">🔔</span>
                <span class="notification-badge" id="notification-badge" style="display: none;">0</span>
            </div>
            <div class="notification-dropdown" id="notification-dropdown" style="display: none;">
                <div class="notification-header">
                    <h4>Уведомления</h4>
                    <button class="mark-all-read" id="mark-all-read">Отметить все как прочитанные</button>
                </div>
                <div class="notification-list" id="notification-list">
                    <div class="no-notifications">Нет новых уведомлений</div>
                </div>
            </div>
        `;

        // Добавляем стили
        this.addNotificationStyles();

        // Добавляем в шапку
        header.appendChild(notificationContainer);
        
        this.notificationBadge = document.getElementById('notification-badge');
        this.notificationBell = document.getElementById('notification-bell');
        this.notificationDropdown = document.getElementById('notification-dropdown');
    }

    /**
     * Добавляет CSS стили для уведомлений
     */
    addNotificationStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: relative;
                display: inline-block;
                margin-left: 20px;
            }

            .notification-bell {
                position: relative;
                cursor: pointer;
                padding: 8px;
                border-radius: 50%;
                transition: background-color 0.3s;
            }

            .notification-bell:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }

            .bell-icon {
                font-size: 20px;
                display: inline-block;
            }

            .notification-badge {
                position: absolute;
                top: 0;
                right: 0;
                background-color: #ff4444;
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                font-size: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                min-width: 20px;
                padding: 0 4px;
                box-sizing: border-box;
            }

            .notification-dropdown {
                position: absolute;
                top: 100%;
                right: 0;
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                width: 320px;
                max-height: 400px;
                overflow-y: auto;
                z-index: 1000;
                margin-top: 8px;
            }

            .notification-header {
                padding: 15px 20px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .notification-header h4 {
                margin: 0;
                font-size: 16px;
                color: #333;
            }

            .mark-all-read {
                background: none;
                border: none;
                color: #007bff;
                cursor: pointer;
                font-size: 12px;
                text-decoration: underline;
            }

            .notification-list {
                max-height: 300px;
                overflow-y: auto;
            }

            .notification-item {
                padding: 15px 20px;
                border-bottom: 1px solid #f0f0f0;
                cursor: pointer;
                transition: background-color 0.2s;
            }

            .notification-item:hover {
                background-color: #f8f9fa;
            }

            .notification-item.unread {
                background-color: #e3f2fd;
            }

            .notification-item.unread::before {
                content: '';
                position: absolute;
                left: 8px;
                top: 50%;
                transform: translateY(-50%);
                width: 8px;
                height: 8px;
                background-color: #007bff;
                border-radius: 50%;
            }

            .notification-text {
                font-size: 14px;
                color: #333;
                margin-bottom: 5px;
            }

            .notification-time {
                font-size: 12px;
                color: #666;
            }

            .no-notifications {
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 14px;
            }

            .notification-highlight {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding-left: 16px;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Привязывает события
     */
    bindEvents() {
        // Клик по колокольчику
        if (this.notificationBell) {
            this.notificationBell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotificationDropdown();
            });
        }

        // Закрытие dropdown при клике вне его
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.notification-container')) {
                this.hideNotificationDropdown();
            }
        });

        // Кнопка "Отметить все как прочитанные"
        const markAllReadBtn = document.getElementById('mark-all-read');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
    }

    /**
     * Запускает периодическую проверку уведомлений
     */
    startPeriodicCheck() {
        this.checkNotifications();
        setInterval(() => {
            this.checkNotifications();
        }, this.checkInterval);
    }

    /**
     * Проверяет новые уведомления
     */
    async checkNotifications() {
        try {
            const response = await fetch('/api/offers/responses/notifications', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('telegram_auth_token')}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateNotificationBadge(data.notifications);
                }
            }
        } catch (error) {
            console.error('Ошибка проверки уведомлений:', error);
        }
    }

    /**
     * Обновляет значок уведомлений
     */
    updateNotificationBadge(notifications) {
        if (!this.notificationBadge) return;

        const count = notifications.new_responses_24h || 0;
        
        if (count > 0) {
            this.notificationBadge.textContent = count > 99 ? '99+' : count;
            this.notificationBadge.style.display = 'flex';
            
            // Добавляем анимацию
            this.notificationBadge.style.animation = 'pulse 2s infinite';
        } else {
            this.notificationBadge.style.display = 'none';
        }

        // Обновляем title для accessibility
        if (this.notificationBell) {
            this.notificationBell.title = count > 0 ? `${count} новых откликов` : 'Нет новых откликов';
        }
    }

    /**
     * Показывает/скрывает dropdown уведомлений
     */
    toggleNotificationDropdown() {
        if (!this.notificationDropdown) return;

        const isVisible = this.notificationDropdown.style.display === 'block';
        
        if (isVisible) {
            this.hideNotificationDropdown();
        } else {
            this.showNotificationDropdown();
        }
    }

    /**
     * Показывает dropdown уведомлений
     */
    showNotificationDropdown() {
        if (!this.notificationDropdown) return;

        this.notificationDropdown.style.display = 'block';
        this.loadNotificationList();
    }

    /**
     * Скрывает dropdown уведомлений
     */
    hideNotificationDropdown() {
        if (!this.notificationDropdown) return;
        this.notificationDropdown.style.display = 'none';
    }

    /**
     * Загружает список уведомлений
     */
    async loadNotificationList() {
        const notificationList = document.getElementById('notification-list');
        if (!notificationList) return;

        try {
            // Показываем загрузку
            notificationList.innerHTML = '<div class="loading">Загрузка...</div>';

            const response = await fetch('/api/offers/my', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('telegram_auth_token')}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.renderNotificationList(data.offers);
                }
            }
        } catch (error) {
            console.error('Ошибка загрузки уведомлений:', error);
            notificationList.innerHTML = '<div class="error">Ошибка загрузки</div>';
        }
    }

    /**
     * Рендерит список уведомлений
     */
    renderNotificationList(offers) {
        const notificationList = document.getElementById('notification-list');
        if (!notificationList) return;

        // Фильтруем офферы с новыми откликами
        const offersWithNewResponses = offers.filter(offer => 
            offer.pending_count > 0 || offer.needs_attention
        );

        if (offersWithNewResponses.length === 0) {
            notificationList.innerHTML = '<div class="no-notifications">Нет новых уведомлений</div>';
            return;
        }

        const notifications = offersWithNewResponses.map(offer => {
            const timeAgo = this.formatTimeAgo(offer.updated_at);
            const responseText = offer.pending_count === 1 ? 'отклик' : 'откликов';
            
            return `
                <div class="notification-item unread" data-offer-id="${offer.id}">
                    <div class="notification-text">
                        <strong>${offer.pending_count} новых ${responseText}</strong> на оффер "${offer.title}"
                    </div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
            `;
        }).join('');

        notificationList.innerHTML = notifications;

        // Привязываем клики
        notificationList.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const offerId = e.currentTarget.getAttribute('data-offer-id');
                this.handleNotificationClick(offerId);
            });
        });
    }

    /**
     * Обрабатывает клик по уведомлению
     */
    handleNotificationClick(offerId) {
        // Перенаправляем на страницу оффера
        window.location.href = `/offer/${offerId}`;
        this.hideNotificationDropdown();
    }

    /**
     * Отмечает все уведомления как прочитанные
     */
    async markAllAsRead() {
        try {
            // Здесь будет API вызов для отметки всех как прочитанных
            console.log('Отмечаем все как прочитанные');
            
            // Обновляем UI
            this.updateNotificationBadge({ new_responses_24h: 0 });
            this.hideNotificationDropdown();
            
            // Показываем уведомление
            this.showToast('Все уведомления отмечены как прочитанные');
        } catch (error) {
            console.error('Ошибка отметки уведомлений:', error);
        }
    }

    /**
     * Форматирует время "назад"
     */
    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (minutes < 60) {
            return `${minutes} мин назад`;
        } else if (hours < 24) {
            return `${hours} ч назад`;
        } else {
            return `${days} д назад`;
        }
    }

    /**
     * Показывает всплывающее уведомление
     */
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * Подсвечивает новые элементы в списке
     */
    highlightNewResponses() {
        const responseItems = document.querySelectorAll('.response-item');
        responseItems.forEach(item => {
            if (item.dataset.isNew === 'true') {
                item.classList.add('notification-highlight');
            }
        });
    }
}

// Добавляем CSS анимацию
const animationStyle = document.createElement('style');
animationStyle.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(animationStyle);

// Инициализируем систему уведомлений когда DOM готов
document.addEventListener('DOMContentLoaded', () => {
    window.notificationSystem = new NotificationSystem();
});

// Экспорт для использования в других модулях
window.NotificationSystem = NotificationSystem;