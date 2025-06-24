// app/static/js/offers.js
// JavaScript для работы с системой офферов

class OffersManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.init();
    }

    init() {
        console.log('🎯 Инициализация системы офферов');
        this.setupEventListeners();
        this.updateStep(this.currentStep);
        this.loadUserData();
    }

    setupEventListeners() {
        // Кнопки навигации
        document.getElementById('nextBtn')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prevBtn')?.addEventListener('click', () => this.prevStep());
        document.getElementById('submitBtn')?.addEventListener('click', () => this.submitOffer());

        // Форма валидация
        this.setupFormValidation();

        // Предпросмотр
        this.setupPreview();

        // Слайдеры
        this.setupSliders();
    }

    setupFormValidation() {
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('input', () => this.validateField(input));
            input.addEventListener('blur', () => this.validateField(input));
        });
    }

    setupPreview() {
        // Обновление предпросмотра при изменении полей
        const titleInput = document.getElementById('title');
        const budgetInput = document.getElementById('budget');
        const currencySelect = document.getElementById('currency');

        titleInput?.addEventListener('input', () => {
            document.getElementById('previewTitle').textContent = titleInput.value || '-';
        });

        const updateBudget = () => {
            const budget = budgetInput?.value || 0;
            const currency = currencySelect?.value || 'RUB';
            document.getElementById('previewBudget').textContent = 
                budget ? `${Number(budget).toLocaleString()} ${currency}` : '-';
        };

        budgetInput?.addEventListener('input', updateBudget);
        currencySelect?.addEventListener('change', updateBudget);
    }

    setupSliders() {
        // Слайдер бюджета
        const budgetSlider = document.getElementById('budgetSlider');
        const budgetInput = document.getElementById('budget');
        const budgetDisplay = document.getElementById('budgetDisplay');

        if (budgetSlider && budgetInput) {
            budgetSlider.addEventListener('input', (e) => {
                const value = e.target.value;
                budgetInput.value = value;
                budgetDisplay.textContent = Number(value).toLocaleString();
                budgetInput.dispatchEvent(new Event('input'));
            });

            budgetInput.addEventListener('input', (e) => {
                const value = Math.min(Math.max(e.target.value, 1000), 1000000);
                budgetSlider.value = value;
                budgetDisplay.textContent = Number(value).toLocaleString();
            });
        }

        // Слайдер подписчиков
        const subscribersSlider = document.getElementById('minSubscribersSlider');
        const subscribersInput = document.getElementById('minSubscribers');
        const subscribersDisplay = document.getElementById('subscribersDisplay');

        if (subscribersSlider && subscribersInput) {
            subscribersSlider.addEventListener('input', (e) => {
                const value = Math.max(1, e.target.value); // Минимум 1 подписчик
                subscribersInput.value = value;
                subscribersDisplay.textContent = Number(value).toLocaleString();
            });

            subscribersInput.addEventListener('input', (e) => {
                const value = Math.max(1, Math.min(e.target.value, 5000000));
                subscribersSlider.value = value;
                subscribersDisplay.textContent = Number(value).toLocaleString();
            });
        }
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Валидация по типу поля
        switch (field.id) {
            case 'title':
                if (!value || value.length < 5) {
                    isValid = false;
                    errorMessage = 'Название должно содержать минимум 5 символов';
                }
                break;

            case 'content':
                if (!value || value.length < 20) {
                    isValid = false;
                    errorMessage = 'Описание должно содержать минимум 20 символов';
                }
                break;

            case 'budget':
                const budget = Number(value);
                if (!budget || budget < 1000) {
                    isValid = false;
                    errorMessage = 'Минимальный бюджет: 1,000 ₽';
                }
                break;

            case 'minSubscribers':
                const subscribers = Number(value);
                if (!subscribers || subscribers < 1) {
                    isValid = false;
                    errorMessage = 'Минимальное количество подписчиков: 1';
                    field.value = 1; // Принудительно устанавливаем минимум
                }
                break;

            case 'targetAudience':
                if (!value || value.length < 10) {
                    isValid = false;
                    errorMessage = 'Опишите целевую аудиторию (минимум 10 символов)';
                }
                break;
        }

        // Показываем/скрываем ошибку
        this.showFieldError(field, isValid, errorMessage);
        return isValid;
    }

    showFieldError(field, isValid, message) {
        const errorElement = document.getElementById(`${field.id}Error`);
        
        if (errorElement) {
            if (isValid) {
                errorElement.style.display = 'none';
                field.classList.remove('error');
            } else {
                errorElement.textContent = message;
                errorElement.style.display = 'block';
                field.classList.add('error');
            }
        }

        // Добавляем CSS класс для поля с ошибкой
        if (isValid) {
            field.classList.remove('invalid');
            field.classList.add('valid');
        } else {
            field.classList.remove('valid');
            field.classList.add('invalid');
        }
    }

    validateStep(step) {
        const stepElement = document.querySelector(`[data-step="${step}"]`);
        if (!stepElement) return true;

        const inputs = stepElement.querySelectorAll('input, textarea, select');
        let stepValid = true;

        inputs.forEach(input => {
            if (!this.validateField(input)) {
                stepValid = false;
            }
        });

        return stepValid;
    }

    updateStep(step) {
        // Обновляем индикатор шагов
        document.querySelectorAll('.step').forEach((stepEl, index) => {
            const stepNumber = index + 1;
            stepEl.classList.toggle('active', stepNumber === step);
            stepEl.classList.toggle('completed', stepNumber < step);
        });

        // Показываем/скрываем шаги формы
        document.querySelectorAll('.form-step').forEach(stepEl => {
            stepEl.style.display = stepEl.dataset.step == step ? 'block' : 'none';
        });

        // Управляем кнопками
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (prevBtn) prevBtn.style.display = step === 1 ? 'none' : 'inline-flex';
        if (nextBtn) nextBtn.style.display = step === this.totalSteps ? 'none' : 'inline-flex';
        if (submitBtn) submitBtn.style.display = step === this.totalSteps ? 'inline-flex' : 'none';

        // Обновляем предпросмотр на последнем шаге
        if (step === this.totalSteps) {
            this.updatePreview();
        }

        this.currentStep = step;
    }

    nextStep() {
        if (this.validateStep(this.currentStep)) {
            if (this.currentStep < this.totalSteps) {
                this.updateStep(this.currentStep + 1);
            }
        } else {
            this.showNotification('Пожалуйста, исправьте ошибки перед продолжением', 'error');
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.updateStep(this.currentStep - 1);
        }
    }

    updatePreview() {
        // Обновляем все поля предпросмотра
        const fields = {
            'previewTitle': document.getElementById('title')?.value || '-',
            'previewBudget': (() => {
                const budget = document.getElementById('budget')?.value;
                const currency = document.getElementById('currency')?.value || 'RUB';
                return budget ? `${Number(budget).toLocaleString()} ${currency}` : '-';
            })(),
            'previewAudience': document.getElementById('targetAudience')?.value || '-',
            'previewGeography': (() => {
                const geo = document.getElementById('geography')?.value;
                return geo || 'Весь мир';
            })(),
            'previewTopics': (() => {
                const checkboxes = document.querySelectorAll('input[name="categories"]:checked');
                const topics = Array.from(checkboxes).map(cb => cb.value);
                return topics.length > 0 ? topics.join(', ') : '-';
            })()
        };

        // Устанавливаем значения
        Object.entries(fields).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    collectFormData() {
        const formData = {
            title: document.getElementById('title')?.value?.trim(),
            content: document.getElementById('content')?.value?.trim(),
            budget: Number(document.getElementById('budget')?.value) || 0,
            currency: document.getElementById('currency')?.value || 'RUB',
            targetAudience: document.getElementById('targetAudience')?.value?.trim(),
            geography: document.getElementById('geography')?.value?.trim(),
            minSubscribers: Math.max(1, Number(document.getElementById('minSubscribers')?.value) || 1),
            duration: Number(document.getElementById('duration')?.value) || 7,
            categories: Array.from(document.querySelectorAll('input[name="categories"]:checked')).map(cb => cb.value),
            requirements: document.getElementById('requirements')?.value?.trim() || '',
            contactInfo: document.getElementById('contactInfo')?.value?.trim() || ''
        };

        // Добавляем поле price как алиас для budget для совместимости
        formData.price = formData.budget;
        formData.duration_days = formData.duration;
        formData.target_audience = formData.targetAudience;

        return formData;
    }

    async submitOffer() {
        console.log('📤 Отправка оффера...');

        if (!this.validateStep(this.totalSteps)) {
            this.showNotification('Пожалуйста, проверьте все поля', 'error');
            return;
        }

        const formData = this.collectFormData();
        
        // Валидация обязательных полей
        if (!formData.title || !formData.content || !formData.budget || formData.minSubscribers < 1) {
            this.showNotification('Заполните все обязательные поля', 'error');
            return;
        }

        const submitBtn = document.getElementById('submitBtn');
        const originalText = submitBtn?.textContent;
        
        try {
            // Блокируем кнопку
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Создание...';
            }

            // Получаем данные для аутентификации
            const telegramUserId = this.getTelegramUserId();
            const telegramInitData = this.getTelegramInitData();

            const headers = {
                'Content-Type': 'application/json'
            };

            // Добавляем заголовки аутентификации
            if (telegramUserId) {
                headers['X-Telegram-User-Id'] = telegramUserId.toString();
            }

            if (telegramInitData) {
                headers['X-Telegram-Init-Data'] = telegramInitData;
            }

            console.log('Отправка с заголовками:', headers);

            const response = await fetch('/api/offers', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification('Оффер успешно создан!', 'success');

                // Redirect через 2 секунды
                setTimeout(() => {
                    window.location.href = '/offers';
                }, 2000);
            } else {
                throw new Error(result.error || `HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            console.error('Ошибка создания оффера:', error);
            this.showNotification(`Ошибка: ${error.message}`, 'error');
        } finally {
            // Восстанавливаем кнопку
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }

    getTelegramUserId() {
        // Получаем ID пользователя из Telegram WebApp
        if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
            return window.Telegram.WebApp.initDataUnsafe.user.id;
        }

        // Fallback для тестирования
        return localStorage.getItem('test_user_id') || '373086959';
    }

    getTelegramInitData() {
        // Получаем полные данные инициализации
        if (window.Telegram?.WebApp?.initData) {
            return window.Telegram.WebApp.initData;
        }
        return null;
    }

    loadUserData() {
        // Загружаем данные пользователя если доступны
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            const user = window.Telegram.WebApp.initDataUnsafe.user;

            // Предзаполняем контактную информацию
            const contactField = document.getElementById('contactInfo');
            if (contactField && !contactField.value) {
                contactField.value = `@${user.username || user.first_name}`;
            }
        }
    }

    showNotification(message, type = 'info') {
        // Используем простые уведомления вместо Telegram WebApp для совместимости
        console.log(`${type.toUpperCase()}: ${message}`);

        // Fallback уведомления
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Стили для уведомления
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            left: '20px',
            padding: '16px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '600',
            zIndex: '10000',
            transform: 'translateY(-100px)',
            transition: 'transform 0.3s ease',
            textAlign: 'center',
            fontSize: '14px'
        });

        // Цвета по типу
        const colors = {
            success: '#4facfe',
            error: '#ff6b6b',
            info: '#667eea'
        };
        notification.style.background = colors[type] || colors.info;

        document.body.appendChild(notification);

        // Анимация появления
        setTimeout(() => {
            notification.style.transform = 'translateY(0)';
        }, 100);

        // Автоудаление
        setTimeout(() => {
            notification.style.transform = 'translateY(-100px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);

        // Для отладки также показываем browser alert при ошибках
        if (type === 'error') {
            setTimeout(() => alert(message), 500);
        }
    }
}

// Класс для управления списком офферов
class OffersListManager {
    constructor() {
        this.offers = [];
        this.filters = {
            status: 'all',
            category: 'all',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };
    }

    async loadOffers() {
        try {
            const response = await fetch('/api/offers/my', {
                headers: {
                    'X-Telegram-User-Id': this.getTelegramUserId()
                }
            });

            const result = await response.json();
            
            if (result.success) {
                this.offers = result.offers || [];
                this.renderOffers();
            } else {
                console.error('Ошибка загрузки офферов:', result.error);
            }
        } catch (error) {
            console.error('Ошибка загрузки офферов:', error);
        }
    }

    renderOffers() {
        const container = document.getElementById('offersContainer');
        if (!container) return;

        if (this.offers.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📝</div>
                    <h3>Нет офферов</h3>
                    <p>Создайте свой первый оффер, чтобы начать привлекать каналы</p>
                    <a href="/offers/create" class="btn btn-primary">Создать оффер</a>
                </div>
            `;
            return;
        }

        const filteredOffers = this.filterOffers();
        
        container.innerHTML = filteredOffers.map(offer => `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3 class="offer-title">${offer.title}</h3>
                    <span class="offer-status status-${offer.status}">${this.getStatusText(offer.status)}</span>
                </div>
                
                <div class="offer-meta">
                    <span class="offer-budget">${Number(offer.price || offer.budget || 0).toLocaleString()} ${offer.currency || 'RUB'}</span>
                    <span class="offer-date">${this.formatDate(offer.created_at)}</span>
                </div>
                
                <p class="offer-description">${offer.description || offer.content?.substring(0, 100) + '...'}</p>
                
                <div class="offer-stats">
                    <span class="stat">
                        <span class="stat-icon">👥</span>
                        Откликов: ${offer.response_count || 0}
                    </span>
                    <span class="stat">
                        <span class="stat-icon">✅</span>
                        Принято: ${offer.accepted_count || 0}
                    </span>
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-secondary" onclick="offersListManager.viewOffer(${offer.id})">
                        Подробнее
                    </button>
                    ${offer.status === 'active' ? `
                        <button class="btn btn-primary" onclick="offersListManager.pauseOffer(${offer.id})">
                            Приостановить
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    filterOffers() {
        return this.offers.filter(offer => {
            if (this.filters.status !== 'all' && offer.status !== this.filters.status) {
                return false;
            }
            return true;
        });
    }

    getStatusText(status) {
        const statusTexts = {
            'active': 'Активен',
            'paused': 'Приостановлен',
            'completed': 'Завершен',
            'cancelled': 'Отменен'
        };
        return statusTexts[status] || status;
    }

    formatDate(dateString) {
        if (!dateString) return 'Неизвестно';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Неизвестно';
        }
    }

    async viewOffer(offerId) {
        window.location.href = `/offers/${offerId}`;
    }

    async pauseOffer(offerId) {
        try {
            const response = await fetch(`/api/offers/${offerId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': this.getTelegramUserId()
                },
                body: JSON.stringify({ status: 'paused' })
            });

            const result = await response.json();
            
            if (result.success) {
                await this.loadOffers(); // Перезагружаем список
            } else {
                alert('Ошибка при изменении статуса оффера');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            alert('Ошибка при изменении статуса оффера');
        }
    }

    getTelegramUserId() {
        if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
            return window.Telegram.WebApp.initDataUnsafe.user.id;
        }
        return localStorage.getItem('test_user_id') || '373086959';
    }
}

// Глобальные переменные для доступа из HTML
let offersManager;
let offersListManager;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Инициализация страницы офферов');
    
    // Определяем тип страницы и инициализируем соответствующий менеджер
    if (document.getElementById('offerForm')) {
        offersManager = new OffersManager();
    }
    
    if (document.getElementById('offersContainer')) {
        offersListManager = new OffersListManager();
        offersListManager.loadOffers();
    }

    // Настройка Telegram WebApp
    if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
});

// Экспортируем для использования в других скриптах
window.OffersManager = OffersManager;
window.OffersListManager = OffersListManager;