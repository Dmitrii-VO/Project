// Функции переключения табов:
// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
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
document.getElementById('addChannelForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.textContent;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = '💾 Сохранение...';

        // Собираем данные формы
        const formData = {
    username: document.getElementById('channelUrl').value.trim(),
    title: document.getElementById('channelTitle')?.value ||
           channelAnalyzer.currentChannelData?.title ||
           `Канал @${document.getElementById('channelUrl').value.trim()}`,

    description: document.getElementById('channelDescription').value ||
                channelAnalyzer.currentChannelData?.description || '',

    category: document.getElementById('channelCategory').value || 'general',

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

    // Остальные поля
    price_per_post: parseFloat(document.getElementById('pricePerPost')?.value || 0),
    payment_terms: document.getElementById('paymentTerms')?.value || 'prepaid'
};
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
            // Создаем модальное окно с инструкциями
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.background = 'rgba(0,0,0,0.8)';

modal.innerHTML = `
    <div style="
        background: white; padding: 20px; border-radius: 15px;
        max-width: min(500px, 95vw); margin: 10px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        max-height: 95vh; overflow-y: auto;
    ">
<div style="font-size: 48px; margin-bottom: 20px;">📝</div>
<h3 style="color: #333; margin-bottom: 20px;">Подтвердите владение каналом</h3>

<div style="
    background: #e3f2fd; padding: 20px; border-radius: 10px;
    margin: 20px 0; border-left: 4px solid #2196f3;
">
    <h4 style="color: #1976d2; margin-bottom: 15px;">🔐 Код верификации:</h4>

    <div style="
        background: #333; color: #00ff00; padding: 15px;
        border-radius: 8px; font-family: 'Courier New', monospace;
        font-size: 20px; font-weight: bold; letter-spacing: 2px;
        margin: 15px 0; cursor: pointer; user-select: all;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    " onclick="
        navigator.clipboard.writeText('${verificationCode}');
        this.style.background='#1b5e20';
        this.innerHTML='${verificationCode} ✅';
        setTimeout(() => {
            this.style.background='#333';
            this.innerHTML='${verificationCode}';
        }, 2000);
    ">${verificationCode}</div>

    <small style="color: #666;">Нажмите на код, чтобы скопировать</small>
</div>

<div style="
    background: #f5f5f5; padding: 20px; border-radius: 10px;
    margin: 20px 0; text-align: left;
">
    <h4 style="color: #333; margin-bottom: 15px;">📋 Инструкция:</h4>

    <ol style="margin: 0; padding-left: 20px; color: #555;">
        <li style="margin-bottom: 10px;">
            Откройте ваш канал <strong>@${channelUsername}</strong>
        </li>
        <li style="margin-bottom: 10px;">
            Опубликуйте сообщение с кодом: <strong>${verificationCode}</strong>
        </li>
        <li style="margin-bottom: 10px;">
            Переслать это сообщение нашему боту <strong>@YOUR_BOT_USERNAME</strong>
        </li>
        <li style="margin-bottom: 10px;">
            Получите уведомление об успешной верификации в боте
        </li>
    </ol>
</div>

<div style="
    background: #fff3cd; padding: 15px; border-radius: 8px;
    margin: 15px 0; border-left: 4px solid #ffc107;
">
    <small style="color: #856404;">
        💡 <strong>Совет:</strong> После публикации кода вы можете сразу удалить сообщение из канала.
        Главное успеть переслать его боту!
    </small>
</div>

<button onclick="
    document.body.removeChild(this.closest('div').parentElement);
    switchTab('channels');
" style="
    background: #2196f3; color: white; border: none;
    padding: 12px 30px; border-radius: 8px; font-size: 16px;
    cursor: pointer; margin-top: 15px; font-weight: 600;
">Понятно, перейти к каналам</button>

<div style="margin-top: 15px;">
    <a href="https://t.me/YOUR_BOT_USERNAME" target="_blank" style="
        color: #2196f3; text-decoration: none; font-size: 14px; font-weight: 600;
    ">🤖 Открыть бота для верификации</a>
</div>
</div>
`;

                    document.body.appendChild(modal);

                    } else {
                    // Fallback для случаев без кода верификации
                    alert('✅ Канал успешно добавлен и находится на модерации.');
                    }

                    // Очищаем форму
                    this.reset();
                    document.getElementById('channelPreview').classList.remove('active');
                    document.getElementById('additionalFields').style.display = 'none';
                    document.getElementById('pricingFields').style.display = 'none';

                            // Переключаемся на вкладку с каналами
                            switchTab('channels');

                        } catch (error) {
                            alert('❌ Ошибка при добавлении канала: ' + error.message);
                        } finally {
                            submitBtn.disabled = false;
                            submitBtn.textContent = originalText;
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

// Функции форматирования
function formatNumber(num) {
    if (!num || num === 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}
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