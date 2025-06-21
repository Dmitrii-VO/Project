// Функции для работы с пользователем и API:
function getTelegramUser() {
            // Пытаемся получить данные из Telegram WebApp
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
                const user = window.Telegram.WebApp.initDataUnsafe.user;
                if (user) {
                    return user;
                }
            }

            // Fallback: тестовый пользователь для разработки
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                return {
                    id: 373086959, // YOUR_TELEGRAM_ID из .env
                    username: 'test_user',
                    first_name: 'Test',
                    last_name: 'User'
                };
            }

            return null;
        }
async function loadUserChannels() {
    // ✅ ЗАЩИТА ОТ МНОЖЕСТВЕННЫХ ВЫЗОВОВ
    if (window.channelsLoading) {
        console.log('⚠️ Загрузка каналов уже выполняется, пропускаем...');
        return;
    }
    window.channelsLoading = true;

    try {
        console.log('🔍 Начинаем загрузку каналов пользователя...');

        // Показываем индикатор загрузки
        showLoadingState();

        // Получаем данные Telegram пользователя
        const telegramUser = getTelegramUser();
        console.log('👤 Telegram пользователь:', telegramUser);

        const headers = {
            'Content-Type': 'application/json'
        };

        // Добавляем Telegram данные в заголовки если доступны
        if (telegramUser) {
            headers['X-Telegram-User-Id'] = telegramUser.id.toString();
            console.log('🔑 Добавлен заголовок X-Telegram-User-Id:', telegramUser.id);

            if (telegramUser.username) {
                headers['X-Telegram-Username'] = telegramUser.username;
            }

            // ✅ ИСПРАВЛЕНО: Кодируем кириллические символы в Base64
            if (telegramUser.first_name) {
                try {
                    headers['X-Telegram-First-Name'] = btoa(unescape(encodeURIComponent(telegramUser.first_name)));
                } catch (e) {
                    console.warn('Ошибка кодирования first_name:', e);
                }
            }

            if (telegramUser.last_name) {
                try {
                    headers['X-Telegram-Last-Name'] = btoa(unescape(encodeURIComponent(telegramUser.last_name)));
                } catch (e) {
                    console.warn('Ошибка кодирования last_name:', e);
                }
            }
        } else {
            console.error('❌ Нет данных Telegram пользователя! Используем ID по умолчанию');
            headers['X-Telegram-User-Id'] = '373086959';
        }

        // ✅ Запрос к API
        const response = await fetch('/api/channels/my', {
            method: 'GET',
            headers: headers
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        const data = await response.json();

        // Скрываем индикатор загрузки
        hideLoadingState();

        const channelsGrid = document.getElementById('channelsGrid');
        if (!channelsGrid) {
            console.error('❌ Элемент channelsGrid не найден!');
            return;
        }

        // ✅ Очищаем существующие карточки перед добавлением новых
        const existingCards = channelsGrid.querySelectorAll('.stat-card[data-user-channel="true"], .channel-card[data-user-channel="true"]');
        existingCards.forEach(card => card.remove());

        // Скрываем элементы ошибок
        const errorElement = document.getElementById('channelsError');
        if (errorElement) {
            errorElement.style.display = 'none';
        }

        // ✅ Обработка успешного ответа
        if (data.success && data.channels && data.channels.length > 0) {
            console.log(`📊 Получено ${data.channels.length} каналов от сервера`);

            // Скрываем все состояния загрузки и пустых данных
            const emptyState = document.getElementById('emptyState');
            const loadingElement = document.getElementById('channelsLoading');

            if (emptyState) emptyState.style.display = 'none';
            if (loadingElement) loadingElement.style.display = 'none';

            // ✅ ДОБАВЛЯЕМ каналы БЕЗ ДУБЛИРОВАНИЯ
            let addedCount = 0;
            data.channels.forEach((channel, index) => {
                // Проверяем, не существует ли уже карточка с таким ID
                const existingCard = channelsGrid.querySelector(`[data-channel-id="${channel.id}"]`);
                if (!existingCard) {
                    const channelCard = createChannelCard(channel);
                    channelsGrid.appendChild(channelCard);
                    addedCount++;
                    console.log(`✅ Добавлен канал: ${channel.title || channel.username}`);
                } else {
                    console.log(`⚠️ Канал ${channel.title || channel.username} уже существует, пропускаем`);
                }
            });

            console.log(`📺 Итого добавлено карточек: ${addedCount} из ${data.channels.length}`);

            // ✅ Обновляем счетчик каналов если функция существует
            if (typeof updateChannelsCounter === 'function') {
                updateChannelsCounter(data.channels.length);
            }

        } else {
            // ✅ Нет каналов для отображения
            console.log('ℹ️ Нет каналов для отображения');
            showEmptyState();
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки каналов:', error);
        hideLoadingState();
        showErrorState(error.message);
    } finally {
        // ✅ ОБЯЗАТЕЛЬНО сбрасываем флаг загрузки в любом случае
        window.channelsLoading = false;
    }
}

// ✅ Вспомогательные функции форматирования (если их нет)

function formatNumber(number) {
    if (!number || number === 0) return '0';

    if (number >= 1000000) {
        return (number / 1000000).toFixed(1) + 'M';
    } else if (number >= 1000) {
        return (number / 1000).toFixed(1) + 'K';
    }
    return number.toString();
}

function formatPrice(price) {
    if (!price) return '0';
    return new Intl.NumberFormat('ru-RU').format(price);
}

function formatDate(dateString) {
    if (!dateString) return 'Недавно';

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    } catch (e) {
        return 'Недавно';
    }
}

// ✅ Глобальный доступ
window.loadUserChannels = loadUserChannels;
function debugChannelData() {
    console.log('🔧 Запуск отладки каналов...');

    // Проверяем API напрямую
    fetch('/api/channels/my', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': '373086959' // Ваш ID для тестирования
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('🔍 Прямой API ответ:', data);

        if (data.channels && data.channels.length > 0) {
            const firstChannel = data.channels[0];
            console.log('🔍 Первый канал детально:', {
                'Все поля': Object.keys(firstChannel),
                'subscriber_count': firstChannel.subscriber_count,
                'subscribers_count': firstChannel.subscribers_count,
                'Полный объект': firstChannel
            });
        }
    })
    .catch(error => {
        console.error('❌ Ошибка API:', error);
    });
}
function createChannelCard(channel) {

    const card = document.createElement('div');
    card.className = 'stat-card';
    card.setAttribute('data-user-channel', 'true');
    card.setAttribute('data-channel-id', channel.id);

    // Определяем статус канала
    const status = (channel.is_verified || channel.status === 'verified')
        ? { class: 'status-active', text: 'Верифицирован', emoji: '✅' }
        : { class: 'status-pending', text: 'На модерации', emoji: '⏳' };

    // ИСПРАВЛЕНО: Безопасное получение данных
    const title = channel.title || channel.channel_name || `Канал @${channel.username || channel.channel_username}`;
    const username = (channel.username || channel.channel_username || 'unknown').replace('@', '');

    // ИСПРАВЛЕНО: Правильное получение количества подписчиков
    const subscribersCount = formatNumber(
        channel.subscriber_count ||     // ✅ Правильное поле из БД
        channel.subscribers_count ||    // ✅ Для совместимости
        0
    );

    // ИСПРАВЛЕНО: Реальная статистика офферов и постов
    const offersCount = formatNumber(channel.offers_count || 0);
    const postsCount = formatNumber(channel.posts_count || 0);

    const description = channel.description || channel.channel_description || 'Описание не указано';
    const createdAt = formatDate(channel.created_at);

    // HTML карточки с реальной статистикой
    card.innerHTML = `
        <!-- Заголовок канала -->
        <div class="channel-header">
            <div class="channel-info">
                <div class="channel-title">${title}</div>
            </div>
            <div class="channel-status ${status.class}">
                ${status.text}
            </div>
        </div>

        <!-- ИСПРАВЛЕНО: Статистика с реальными данными -->
        <div class="channel-stats">
            <div class="stat-item">
                <span class="stat-number">${subscribersCount}</span>
                <div class="stat-label">Подписчиков</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">${postsCount}</span>
                <div class="stat-label">Постов</div>
            </div>
            <div class="stat-item">
                <span class="stat-number">${offersCount}</span>
                <div class="stat-label">Офферов</div>
            </div>
        </div>

        <!-- Блок цены (если есть) -->
        ${channel.price_per_post ? `
        <div class="channel-pricing">
            <div class="pricing-title">Цена за пост</div>
            <div class="pricing-value">${formatPrice(channel.price_per_post)} ₽</div>
        </div>
        ` : ''}

        <!-- Кнопки действий -->
        <div class="channel-actions">
            ${(channel.is_verified || channel.status === 'verified') ? `
                <button class="btn btn-secondary" onclick="showChannelStats(${channel.id})">
                    📊 Статистика
                </button>
                <button class="btn btn-secondary" onclick="showChannelSettings(${channel.id})">
                    ⚙️ Настройки
                </button>
            ` : `
                <button class="btn btn-primary" onclick="startChannelVerification(${channel.id}, '${title?.replace(/'/g, "\\'")}', '${username || ""}')">
                    🔐 Верифицировать
                </button>
            `}
            <button class="btn btn-danger" onclick="showDeleteConfirmation(${channel.id}, '${title.replace(/'/g, '&apos;')}', '@${username}')">
                🗑️ Удалить
            </button>
        </div>
    `;

    console.log('✅ Карточка канала создана успешно');
    return card;
}
// ДОПОЛНИТЕЛЬНО: Функция обновления статистики в реальном времени
async function refreshChannelStatistics(channelId) {
    try {
        const telegramUser = getTelegramUser();
        const headers = {
            'Content-Type': 'application/json'
        };

        if (telegramUser) {
            headers['X-Telegram-User-Id'] = telegramUser.id.toString();
        }

        const response = await fetch(`/api/channels/${channelId}`, {
            method: 'GET',
            headers: headers
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success || data.id) {
                // Обновляем карточку канала
                updateChannelCard(channelId, data);
            }
        }
    } catch (error) {
        console.error(`Ошибка обновления статистики канала ${channelId}:`, error);
    }
}
function updateChannelCard(channelId, channelData) {
    const card = document.querySelector(`[data-channel-id="${channelId}"]`);
    if (!card) return;

    // Обновляем подписчиков
    const subscribersElement = card.querySelector('.stat-item:nth-child(1) .stat-number');
    if (subscribersElement) {
        subscribersElement.textContent = formatNumber(
            channelData.subscriber_count ||
            channelData.subscribers_count ||
            0
        );
    }

    // Обновляем посты
    const postsElement = card.querySelector('.stat-item:nth-child(2) .stat-number');
    if (postsElement) {
        postsElement.textContent = formatNumber(channelData.posts_count || 0);
    }

    // Обновляем офферы
    const offersElement = card.querySelector('.stat-item:nth-child(3) .stat-number');
    if (offersElement) {
        offersElement.textContent = formatNumber(channelData.offers_count || 0);
    }
}
function verifyChannel(channelId) {
            console.log(`🔍 Верификация канала ${channelId}`);

            // Показываем индикатор загрузки
            const button = event.target;
            const originalText = button.innerHTML;
            button.innerHTML = '⏳ Проверяем...';
            button.disabled = true;

            const telegramUser = getTelegramUser();
            const headers = {
                'Content-Type': 'application/json'
            };

            if (telegramUser) {
                headers['X-Telegram-User-Id'] = telegramUser.id.toString();
                if (telegramUser.username) headers['X-Telegram-Username'] = telegramUser.username;
                if (telegramUser.first_name) headers['X-Telegram-First-Name'] = telegramUser.first_name;
                if (telegramUser.last_name) headers['X-Telegram-Last-Name'] = telegramUser.last_name;
            }

            fetch(`/api/channels/${channelId}/verify`, {
                method: 'PUT',
                headers: headers
            })
                .then(response => response.json())
                .then(data => {
                    console.log('Ответ верификации:', data);

                    if (data.success) {
                        // Успешная верификация
                        showVerificationSuccess(data);

                        // Обновляем интерфейс
                        updateChannelStatus(channelId, 'verified');

                        // Перезагружаем список каналов
                        setTimeout(() => {
                            loadUserChannels();
                        }, 1000);

                    } else {
                        // Ошибка верификации
                        showVerificationError(data);
                    }
                })
                .catch(error => {
                    console.error('Ошибка верификации:', error);
                    showVerificationError({
                        error: 'Ошибка сети при верификации канала',
                        instructions: ['Проверьте подключение к интернету и попробуйте снова']
                    });
                })
                .finally(() => {
                    // Восстанавливаем кнопку
                    button.innerHTML = originalText;
                    button.disabled = false;
                });
        }
function requestVerification(channelId) {
            return verifyChannel(channelId);
        }
async function startChannelVerification(channelId, channelName, channelUsername) {
    console.log(`🔐 Запуск верификации канала ${channelId}`);

    try {
        const telegramUser = getTelegramUser();
        if (!telegramUser) {
            throw new Error('Данные пользователя Telegram недоступны');
        }

        // Показываем индикатор загрузки
        showNotification('info', '⏳ Запускаем верификацию...');

        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUser.id.toString()
        };

        if (telegramUser.username) {
            headers['X-Telegram-Username'] = telegramUser.username;
        }

        // Используем тот же endpoint, что и для добавления канала
        const response = await fetch('/api/channels', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                username: channelUsername?.replace('@', '') || 'unknown',
                category: 'other',
                description: 'Повторная верификация канала',
                payment_terms: 'prepayment',
                action: 'reverify', // Флаг для определения повторной верификации
                channel_id: channelId
            })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Ошибка сервера');
        }

        // Показываем инструкции точно как при добавлении канала
        const verificationCode = result.verification_code || result.channel?.verification_code;
        const usernameForDisplay = result.channel?.username || channelUsername;

        if (verificationCode) {
            // Создаем модальное окно с инструкциями (ТОЧНО такое же как при добавлении)
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.8); z-index: 10000;
                display: flex; align-items: center; justify-content: center;
            `;

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
                                Откройте ваш канал <strong>@${usernameForDisplay}</strong>
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
                        loadUserChannels();
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
            showSuccessNotification('✅ Верификация запущена!');
        }

    } catch (error) {
        console.error('💥 Ошибка верификации:', error);
        showErrorNotification(`❌ Ошибка: ${error.message}`);
    }
}

// И все вспомогательные функции состояния:
function showLoadingState() {
    const channelsGrid = document.getElementById('channelsGrid');
    if (!channelsGrid) return;

    // СНАЧАЛА СКРЫВАЕМ ВСЕ СОСТОЯНИЯ
    const emptyState = document.getElementById('emptyState');
    const errorElement = document.getElementById('channelsError');

    if (emptyState) emptyState.style.display = 'none';
    if (errorElement) errorElement.style.display = 'none';

    // УБИРАЕМ СУЩЕСТВУЮЩИЕ КАРТОЧКИ ПЕРЕД ПОКАЗОМ ЗАГРУЗКИ
    const existingCards = channelsGrid.querySelectorAll('.stat-card[data-user-channel="true"], .channel-card[data-user-channel="true"]');
    existingCards.forEach(card => card.remove());

    let loadingElement = document.getElementById('channelsLoading');
    if (!loadingElement) {
        loadingElement = document.createElement('div');
        loadingElement.id = 'channelsLoading';
        loadingElement.className = 'loading-state';
        loadingElement.style.gridColumn = '1 / -1';
        loadingElement.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <div class="loading-spinner"></div>
                <div class="loading-text">Загрузка каналов...</div>
            </div>
        `;
        channelsGrid.appendChild(loadingElement);
    }
    loadingElement.style.display = 'block';
}
function hideLoadingState() {
    const loadingElement = document.getElementById('channelsLoading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}
function showEmptyState() {
    const channelsGrid = document.getElementById('channelsGrid');
    if (!channelsGrid) return;

    if (!document.getElementById('emptyState')) {
        const emptyState = document.createElement('div');
        emptyState.id = 'emptyState';
        emptyState.className = 'empty-state';
        emptyState.style.gridColumn = '1 / -1';  // ← ДОБАВЛЕНО для занятия всей ширины
        emptyState.innerHTML = `
            <div class="stat-icon">📺</div>
            <h3>Нет добавленных каналов</h3>
            <p>Добавьте свой первый канал для начала работы с рекламодателями</p>
            <button class="btn btn-primary" onclick="switchTab('add-channel')">
                ➕ Добавить канал
            </button>
        `;
        channelsGrid.appendChild(emptyState);
    }

    document.getElementById('emptyState').style.display = 'block';
}
function showErrorState(errorMessage) {
    const channelsGrid = document.getElementById('channelsGrid');
    if (!channelsGrid) return;

    let errorElement = document.getElementById('channelsError');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.id = 'channelsError';
        errorElement.className = 'error-state';
        channelsGrid.appendChild(errorElement);
    }

    errorElement.innerHTML = `
        <div style="text-align: center; padding: 40px; background: #fef2f2; border-radius: var(--border-radius); border: 2px solid var(--danger-color);">
            <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
            <h3 style="color: var(--danger-color);">Ошибка загрузки каналов</h3>
            <p style="color: var(--text-secondary); margin: 16px 0;">
                ${errorMessage}
            </p>
            <button class="btn btn-primary" onclick="loadUserChannels()">
                🔄 Попробовать снова
            </button>
        </div>
    `;
    errorElement.style.display = 'block';
}
function showChannelStats(channelId) {
    showInfoNotification('Статистика канала (в разработке)');
}
function showChannelSettings(channelId) {
    showInfoNotification('⚙️ Настройки канала скоро будут доступны');
}
function editChannel(channelId) {
            alert('Редактирование канала (в разработке)');
        }
function goBack() {
    try {
        console.log('🔙 Переход на главную страницу');

        // ВСЕГДА переходим на главную страницу, даже в Telegram WebApp
        window.location.href = '/';

    } catch (error) {
        console.error('Ошибка при переходе на главную:', error);
        // Дополнительная попытка
        try {
            window.location.replace('/');
        } catch (e) {
            // Крайний случай - перезагрузка с главной
            window.location = '/';
        }
    }
}
// Добавьте эти функции в channels-core.js или создайте отдельный файл

async function updateChannelWithTelegramData(channelId, username) {
    try {
        console.log(`🔄 Обновляем данные канала ${channelId} (@${username})`);

        // Получаем свежие данные от Telegram API
        const telegramData = await channelAnalyzer.getTelegramChannelInfo(username);

        if (!telegramData.success) {
            throw new Error('Не удалось получить данные от Telegram API');
        }

        console.log('📊 Полученные данные от Telegram:', telegramData);

        // Отправляем обновление на сервер
        const response = await fetch(`/api/channels/${channelId}/update-stats`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            },
            body: JSON.stringify({
                telegram_data: telegramData,
                raw_subscriber_count: telegramData.data.raw_subscriber_count,
                title: telegramData.data.title,
                description: telegramData.data.description
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`✅ Канал ${channelId} обновлен:`, result);
            return result;
        } else {
            throw new Error(result.error || 'Ошибка обновления');
        }

    } catch (error) {
        console.error(`❌ Ошибка обновления канала ${channelId}:`, error);
        throw error;
    }
}

async function updateAllChannelsWithZeroSubscribers() {
    try {
        console.log('🔄 Начинаем обновление каналов с 0 подписчиков...');

        // Получаем текущий список каналов
        const response = await fetch('/api/channels/my', {
            headers: {
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error('Не удалось получить список каналов');
        }

        // Находим каналы с 0 подписчиков
        const channelsToUpdate = data.channels.filter(channel =>
            channel.subscriber_count === 0 || channel.subscribers_count === 0
        );

        console.log(`📊 Найдено ${channelsToUpdate.length} каналов для обновления`);

        // Обновляем каждый канал
        const results = [];
        for (const channel of channelsToUpdate) {
            try {
                console.log(`🔄 Обновляем канал: ${channel.title} (@${channel.username})`);

                const result = await updateChannelWithTelegramData(
                    channel.id,
                    channel.username.replace('@', '')
                );

                results.push({
                    channel_id: channel.id,
                    success: true,
                    old_count: channel.subscriber_count,
                    new_count: result.channel.subscriber_count
                });

                // Небольшая пауза между запросами
                await new Promise(resolve => setTimeout(resolve, 1000));

            } catch (error) {
                console.error(`❌ Ошибка обновления ${channel.title}:`, error);
                results.push({
                    channel_id: channel.id,
                    success: false,
                    error: error.message
                });
            }
        }

        console.log('✅ Обновление завершено:', results);

        // Перезагружаем страницу для отображения обновленных данных
        if (results.some(r => r.success)) {
            console.log('🔄 Перезагружаем список каналов...');
            await loadUserChannels();
        }

        return results;

    } catch (error) {
        console.error('❌ Ошибка массового обновления:', error);
        throw error;
    }
}

// Функция для быстрого исправления конкретного канала
async function fixChannelData(channelId) {
    try {
        // Находим канал в текущем списке
        const channelCard = document.querySelector(`[data-channel-id="${channelId}"]`);
        if (!channelCard) {
            throw new Error('Канал не найден на странице');
        }

        // Извлекаем username из карточки
        const usernameElement = channelCard.querySelector('.channel-username');
        if (!usernameElement) {
            throw new Error('Username не найден в карточке');
        }

        const username = usernameElement.textContent.replace('@', '').trim();

        console.log(`🛠️ Исправляем данные канала ${channelId} (@${username})`);

        const result = await updateChannelWithTelegramData(channelId, username);

        // Обновляем карточку на странице
        const subscribersElement = channelCard.querySelector('.subscribers-count');
        if (subscribersElement && result.channel.subscriber_count > 0) {
            subscribersElement.textContent = formatSubscriberCount(result.channel.subscriber_count);
        }

        console.log(`✅ Канал ${channelId} исправлен!`);
        return result;

    } catch (error) {
        console.error(`❌ Ошибка исправления канала ${channelId}:`, error);
        alert(`Ошибка исправления: ${error.message}`);
        throw error;
    }
}

// Экспортируем функции для использования в консоли
window.updateChannelWithTelegramData = updateChannelWithTelegramData;
window.updateAllChannelsWithZeroSubscribers = updateAllChannelsWithZeroSubscribers;
window.fixChannelData = fixChannelData;

// Делаем функции глобально доступными для onclick
window.verifyChannel = verifyChannel;
window.loadUserChannels = loadUserChannels;
window.showChannelStats = showChannelStats;
window.showChannelSettings = showChannelSettings;
window.editChannel = editChannel;
window.refreshChannelStatistics = refreshChannelStatistics;
window.updateChannelCard = updateChannelCard;
window.debugChannelData = debugChannelData;