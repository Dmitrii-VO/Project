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

            // ИСПРАВЛЕНО: Кодируем кириллические символы в Base64
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

        // Очищаем существующие карточки
        const existingCards = channelsGrid.querySelectorAll('.channel-card[data-user-channel="true"]');
        existingCards.forEach(card => card.remove());

        if (data.success && data.channels && data.channels.length > 0) {
            // Скрываем пустое состояние
            const emptyState = document.getElementById('emptyState');
            if (emptyState) {
                emptyState.style.display = 'none';
            }

            // Добавляем каналы пользователя
            data.channels.forEach((channel) => {
                const channelCard = createChannelCard(channel);
                channelsGrid.appendChild(channelCard);
            });

            updateChannelsCounter(data.channels.length);
        } else {
            showEmptyState();
        }

    } catch (error) {
        console.error('💥 Ошибка загрузки каналов:', error);
        hideLoadingState();
        showErrorState(error.message);
    }
}
function createChannelCard(channel) {
            const card = document.createElement('div');
            card.className = 'channel-card';
            card.setAttribute('data-user-channel', 'true');
            card.setAttribute('data-channel-id', channel.id);

            // Определяем статус канала - используем правильные поля
            const status = (channel.is_verified || channel.status === 'verified')
                ? { class: 'status-verified', text: 'Верифицирован', emoji: '✅' }
                : { class: 'status-pending', text: 'На модерации', emoji: '⏳' };

            // Безопасное получение данных с учетом реальной структуры БД
            const title = channel.title || `Канал @${channel.username}`;
            const username = channel.username ? channel.username.replace('@', '') : 'unknown';
            const subscribersCount = formatNumber(channel.subscribers_count || channel.subscriber_count || 0); // ✅ Два варианта поля
            const description = channel.description || 'Описание не указано';
            const createdAt = formatDate(channel.created_at);
            const language = channel.language || 'ru';

            // URL фотографии канала
            const avatarUrl = channel.photo_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(title)}&background=0ea5e9&color=fff&size=64`;

            card.innerHTML = `
                <div class="channel-header">
                        <div class="channel-avatar">
                            <img src="${avatarUrl}" alt="${title}"
                            onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(title)}&background=0ea5e9&color=fff&size=64'"
                            style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover;">
                        </div>
                    <div class="channel-info">
                        <div class="channel-title-row">
                            <h3 class="channel-title">${title}</h3>
                            <span class="channel-status ${status.class}">${status.emoji} ${status.text}</span>
                        </div>
                        <div class="channel-username">@${username}</div>
                        <div class="channel-description">${description}</div>
                        <div class="channel-meta">
                            <span class="meta-item">
                                <span class="meta-icon">📅</span>
                                Добавлен: ${createdAt}
                            </span>
                            ${channel.category ? `
                                <span class="meta-item">
                                    <span class="meta-icon">🏷️</span>
                                    ${getCategoryName(channel.category)}
                                </span>
                            ` : ''}
                            <span class="meta-item">
                                <span class="meta-icon">🌍</span>
                                ${language.toUpperCase()}
                            </span>
                        </div>
                    </div>
                </div>

                <div class="channel-stats">
                    <div class="stat-item">
                        <span class="stat-value">${subscribersCount}</span>
                        <span class="stat-label">Подписчиков</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">0%</span>
                        <span class="stat-label">Вовлеченность</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">Не указана</span>
                        <span class="stat-label">Цена за пост</span>
                    </div>
                </div>

                ${channel.invite_link ? `
                    <div class="channel-link">
                        <a href="${channel.invite_link}" target="_blank" class="channel-link-btn">
                            🔗 Открыть канал
                        </a>
                    </div>
                ` : ''}

                <div class="channel-actions">
                    ${(channel.is_verified || channel.status === 'verified') ? `
                        <button class="btn btn-outline-primary btn-sm" onclick="showChannelSettings(${channel.id})">
                            ⚙️ Настройки
                        </button>
                        <button class="btn btn-outline-success btn-sm" onclick="showChannelStats(${channel.id})">
                            📊 Статистика
                        </button>
                    ` : ''}
                    ${(!channel.is_verified && channel.status !== 'verified') ? `
                        <button class="btn btn-warning btn-sm" onclick="startChannelVerification(${channel.id}, '${channel.title?.replace(/'/g, "\\'")}', '${channel.username || ""}')">
                            🔒 Верифицировать
                        </button>
                    ` : ''}
                    <button class="btn btn-danger btn-sm" onclick="showDeleteConfirmation(${channel.id}, '${title.replace(/'/g, '&apos;')}', '@${username}')">
                        🗑️ Удалить
                    </button>
                </div>
            `;

            return card;
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

    let loadingElement = document.getElementById('channelsLoading');
    if (!loadingElement) {
        loadingElement = document.createElement('div');
        loadingElement.id = 'channelsLoading';
        loadingElement.className = 'loading-state';
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

            if (!document.getElementById('emptyState')) {
                const emptyState = document.createElement('div');
                emptyState.id = 'emptyState';
                emptyState.className = 'empty-state';
                emptyState.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                        <div style="font-size: 48px; margin-bottom: 16px;">📺</div>
                        <h3>У вас пока нет каналов</h3>
                        <p>Добавьте свой первый канал, чтобы начать зарабатывать на рекламе</p>
                        <button class="btn btn-primary" onclick="switchTab('add-channel')">➕ Добавить канал</button>
                    </div>
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

// Делаем функции глобально доступными для onclick
window.verifyChannel = verifyChannel;
window.loadUserChannels = loadUserChannels;
window.showChannelStats = showChannelStats;
window.showChannelSettings = showChannelSettings;
window.editChannel = editChannel;