// Функции переключения табов:
// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const tabBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (tabBtn) {
        tabBtn.classList.add('active');
    }
    const tabContent = document.getElementById(tabName);
    if (tabContent) {
        tabContent.classList.add('active');
    }
}

// Инициализация Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// Обработчики для переключения табов
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        switchTab(tabName);
    });
});

// Обработка формы добавления канала
document.addEventListener('DOMContentLoaded', function() {
    const addChannelForm = document.getElementById('addChannelForm');
    if (addChannelForm) {
        addChannelForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    // Защита от повторных отправок
    if (window.channelSubmitting) {
        console.log('⚠️ Форма уже отправляется, пропускаем...');
        return;
    }
    window.channelSubmitting = true;

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '💾 Сохранение...';

        // Собираем данные формы
        console.log('🔍 DEBUG: channelAnalyzer.currentChannelData =', channelAnalyzer.currentChannelData);
        
        // Проверяем наличие основного поля
        const channelUrlElement = document.getElementById('channelUrl');
        if (!channelUrlElement) {
            throw new Error('Поле URL канала не найдено');
        }
        
        const channelUrl = document.getElementById('channelUrl')?.value?.trim() || '';
        const channelPrice = document.getElementById('channelPrice')?.value || '';
        const channelContact = document.getElementById('channelContact')?.value || '';
        
        const formData = {
    username: channelUrl,
    title: channelAnalyzer.currentChannelData?.title || `Канал @${channelUrl}`,
    description: channelAnalyzer.currentChannelData?.description || '',
    category: 'general',

    // ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Передаем данные подписчиков из ВСЕХ источников
    subscriber_count: channelAnalyzer.currentChannelData?.raw_subscriber_count ||
                     channelAnalyzer.currentChannelData?.subscriber_count ||
                     channelAnalyzer.currentChannelData?.member_count || 0,

    subscribers_count: channelAnalyzer.currentChannelData?.raw_subscriber_count ||
                      channelAnalyzer.currentChannelData?.subscriber_count ||
                      channelAnalyzer.currentChannelData?.member_count || 0,

    // Дополнительные поля для совместимости
    raw_subscriber_count: channelAnalyzer.currentChannelData?.raw_subscriber_count || 0,
    member_count: channelAnalyzer.currentChannelData?.member_count || 0,

    // Telegram данные если есть
    telegram_id: channelAnalyzer.currentChannelData?.telegram_id ||
                channelAnalyzer.currentChannelData?.channel_id,

    // Остальные поля из формы
    price_per_post: parseFloat(channelPrice || '0'),
    contact_info: channelContact,
    payment_terms: 'prepaid'
};
        
        console.log('🔍 DEBUG: formData =', formData);
        
        // Проверяем обязательные поля
        if (!channelUrl) {
            throw new Error('Укажите ссылку на канал');
        }
        if (!channelPrice) {
            throw new Error('Укажите стоимость размещения');
        }
        if (!channelContact) {
            throw new Error('Укажите контакт для связи');
        }
        
        // Проверяем что данные не пустые
        if (formData.subscriber_count === 0 && channelAnalyzer.currentChannelData?.raw_subscriber_count) {
            console.warn('⚠️ ВНИМАНИЕ: subscriber_count = 0, но raw_subscriber_count =',
                         channelAnalyzer.currentChannelData.raw_subscriber_count);
        }
        console.groupEnd();
        // Отправляем данные
        const response = await fetch('/api/channels', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': window.Telegram?.WebApp?.initDataUnsafe?.user?.id || '373086959'
            },
            body: JSON.stringify(formData)
        });
        // Отправляем данные на сервер


        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Ошибка сервера');
        }

        // Показываем инструкции по автоматической верификации
        const verificationCode = result.verification_code || result.channel?.verification_code;
        const channelUsername = result.channel?.username || formData.channelUrl;

        if (verificationCode) {
            // Используем единое модальное окно из channels-modals.js
            if (typeof createVerificationModalProgrammatically === 'function') {
                createVerificationModalProgrammatically(
                    result.channel?.id || 'temp',
                    result.channel?.title || formData.title,
                    channelUsername,
                    verificationCode
                );
            } else {
                // Fallback если функция не доступна
                alert(`✅ Канал успешно добавлен! Код верификации: ${verificationCode}`);
            }
        } else {
            // Fallback для случаев без кода верификации
            alert('✅ Канал успешно добавлен и находится на модерации.');
        }

                    // Очищаем форму
                    this.reset();
                    const channelPreview = document.getElementById('channelPreview');
                    if (channelPreview) {
                        channelPreview.classList.remove('active');
                    }
                    const additionalFields = document.getElementById('additionalFields');
                    if (additionalFields) {
                        additionalFields.style.display = 'none';
                    }
                    const pricingFields = document.getElementById('pricingFields');
                    if (pricingFields) {
                        pricingFields.style.display = 'none';
                    }

                            // Переключаемся на вкладку с каналами
                            switchTab('channels');

                        } catch (error) {
                            alert('❌ Ошибка при добавлении канала: ' + error.message);
                        } finally {
                            submitBtn.disabled = false;
                            submitBtn.textContent = originalText;
                            window.channelSubmitting = false; // Сбрасываем флаг
                        }
                    });
    }
});

// Поиск по каналам
const searchInput = document.querySelector('#channelSearch');
if (searchInput) {
    searchInput.addEventListener('input', function() {
    const searchTerm = this.value.toLowerCase();
    const channelCards = document.querySelectorAll('.channel-card');

    channelCards.forEach(card => {
        const title = card.querySelector('.channel-title')?.textContent.toLowerCase() || '';
        const username = card.querySelector('.channel-username')?.textContent.toLowerCase() || '';

        if (title.includes(searchTerm) || username.includes(searchTerm)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('📺 Страница каналов загружена');
});

// Используем функцию formatNumber из channels-core.js
function formatPrice(price) {
    if (!price || price === 0) return 'Не указана';
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(price);
}
function formatDate(dateString) {
    if (!dateString) return 'Не указана';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (error) {
        return 'Некорректная дата';
    }
}
function getCategoryName(category) {
    const categories = {
        'technology': 'Технологии',
        'business': 'Бизнес',
        'entertainment': 'Развлечения',
        'news': 'Новости',
        'education': 'Образование',
        'lifestyle': 'Стиль жизни',
        'sports': 'Спорт',
        'gaming': 'Игры',
        'crypto': 'Криптовалюты',
        'travel': 'Путешествия',
        'food': 'Еда',
        'fitness': 'Фитнес',
        'art': 'Искусство',
        'music': 'Музыка',
        'general': 'Общее',
        'other': 'Другое'
    };
    return categories[category] || category;
}
function updateChannelsCounter(count) {
    const tabButton = document.querySelector('.tab-btn[data-tab="channels"]');
    if (tabButton) {
        const originalText = tabButton.textContent.split('(')[0].trim();
        tabButton.textContent = count > 0 ? `${originalText} (${count})` : originalText;
    }
}

// Функции уведомлений:
function showNotification(type, message) {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification-popup ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
function showSuccessNotification(message) {
            showNotification('success', message);
        }
function showErrorNotification(message) {
            showNotification('error', message);
        }
function showInfoNotification(message) {
            showNotification('info', message);
        }

// Отладочные функции:
function debugChannelPreview() {
    console.log('🔍 Проверка элементов для превью канала:');

    const elements = [
        'channelPreview',
        'additionalFields',
        'pricingFields',
        'channelCategory',
        'channelDescription',
        'submitBtn'
    ];

    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            console.log(`✅ ${id}: найден`);
        } else {
            console.log(`❌ ${id}: НЕ найден`);
        }
    });
}
function testChannelPreview() {
    const testData = {
        data: {
            title: 'Тестовый канал',
            username: 'test_channel',
            subscribers: '1.2K',
            engagement_rate: '5.5',
            description: 'Это тестовое описание канала',
            avatar_letter: 'T',
            category: 'technology',
            channel_type: 'channel',
            verified: false
        }
    };

    if (window.channelAnalyzer && window.channelAnalyzer.showChannelPreview) {
        window.channelAnalyzer.showChannelPreview(testData);
    } else {
        console.error('❌ channelAnalyzer не найден');
    }
}

console.log('🔧 Исправленная функция showChannelPreview загружена');
console.log('💡 Для отладки используйте: debugChannelPreview() или testChannelPreview()');

// Закрытие модального окна по ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});

// Вместо onclick в HTML, добавьте обработчики
document.addEventListener('DOMContentLoaded', function() {
    // Обработчики для табов
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Обработчик кнопки "Добавить канал"
    document.querySelectorAll('.btn[onclick*="switchTab"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab('add-channel');
        });
    });
});

// Делаем функции глобально доступными
window.switchTab = switchTab;
window.showNotification = showNotification;