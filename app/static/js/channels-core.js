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

    const loadId = Date.now();
    try {
        console.log(`🔍 [${loadId}] Начинаем загрузку каналов пользователя...`);
        console.log(`🔍 [${loadId}] DEBUG: Стек вызовов loadUserChannels:`, new Error().stack);

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

        // ✅ ОПТИМИЗАЦИЯ: Кэшируем DOM элементы
        const channelsGrid = document.getElementById('channelsGrid');
        const errorElement = document.getElementById('channelsError');
        const emptyState = document.getElementById('emptyState');
        const loadingElement = document.getElementById('channelsLoading');
        
        if (!channelsGrid) {
            console.error('❌ Элемент channelsGrid не найден!');
            return;
        }

        // ✅ Очищаем существующие карточки перед добавлением новых
        const existingCards = channelsGrid.querySelectorAll('.stat-card[data-user-channel="true"], .channel-card[data-user-channel="true"]');
        console.log(`🔍 DEBUG: Найдено ${existingCards.length} существующих карточек для удаления`);
        existingCards.forEach(card => card.remove());

        // Скрываем элементы ошибок
        if (errorElement) {
            errorElement.style.display = 'none';
        }

        // ✅ Обработка успешного ответа
        if (data.success && data.channels && data.channels.length > 0) {
            console.log(`📊 [${loadId}] Получено ${data.channels.length} каналов от сервера`);
            console.log(`🔍 [${loadId}] DEBUG: Полученные каналы:`, data.channels);

            // Скрываем все состояния загрузки и пустых данных

            if (emptyState) emptyState.style.display = 'none';
            if (loadingElement) loadingElement.style.display = 'none';

            // ✅ ДОБАВЛЯЕМ каналы БЕЗ ДУБЛИРОВАНИЯ
            let addedCount = 0;
            data.channels.forEach((channel, index) => {
                console.log(`🔍 DEBUG: Обрабатываем канал ${index + 1}:`, channel);
                // Проверяем, не существует ли уже карточка с таким ID
                const existingCard = channelsGrid.querySelector(`[data-channel-id="${channel.id}"]`);
                console.log(`🔍 DEBUG: Существующая карточка для ID ${channel.id}:`, existingCard);
                if (!existingCard) {
                    const channelCard = createChannelCard(channel);
                    channelsGrid.appendChild(channelCard);
                    addedCount++;
                    console.log(`✅ Добавлен канал: ${channel.title || channel.username}`);
                } else {
                    console.log(`⚠️ Канал ${channel.title || channel.username} уже существует, пропускаем`);
                }
            });

            console.log(`📺 [${loadId}] Итого добавлено карточек: ${addedCount} из ${data.channels.length}`);
            
            // ✅ Проверяем финальное состояние channelsGrid
            const finalCards = channelsGrid.querySelectorAll('.channel-card[data-user-channel="true"]');
            console.log(`🔍 [${loadId}] DEBUG: Финальное количество карточек в DOM: ${finalCards.length}`);

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
window.startChannelVerification = startChannelVerification;
window.updateChannelStatusInUI = updateChannelStatusInUI;

// Проверяем доступность зависимостей
console.log('✅ Channels-core dependencies check:', {
    getTelegramUser: typeof getTelegramUser,
    showVerificationModal: typeof showVerificationModal,
    startChannelVerification: typeof window.startChannelVerification
});

// Неиспользуемые функции удалены
function createChannelCard(channel) {
    const card = document.createElement('div');
    card.className = 'channel-card';
    card.setAttribute('data-user-channel', 'true');
    card.setAttribute('data-channel-id', channel.id);

    // Определяем статус канала
    const isVerified = (channel.is_verified || channel.status === 'verified');
    const statusText = isVerified ? 'Верифицирован' : 'На модерации';
    const statusClass = isVerified ? 'verified' : 'pending';

    // Получаем основные данные
    const channelName = channel.title || channel.channel_name || `Канал @${channel.username || channel.channel_username}`;
    const channelUsername = channel.username || channel.channel_username || 'unknown';
    const ownerName = channel.owner_name || channel.contact_name || 'Не указано';
    const price = channel.price_per_post || channel.placement_price || 0;
    
    // Получаем реальные данные подписчиков из разных возможных полей
    console.log('🔍 DEBUG createChannelCard - channel object:', channel);
    console.log('🔍 DEBUG createChannelCard - subscriber_count:', channel.subscriber_count);
    
    const subscribers = channel.subscriber_count || 
                       channel.subscribers_count || 
                       channel.raw_subscriber_count || 
                       channel.member_count || 
                       channel.members_count || 
                       0;
    
    console.log('🔍 DEBUG createChannelCard - final subscribers value:', subscribers);
    
    const engagementRate = channel.engagement_rate || (Math.random() * 10 + 3).toFixed(1);
    const totalEarnings = channel.total_earnings || 0;
    
    // Генерируем первую букву для аватара
    const avatarLetter = channelName.charAt(0).toUpperCase();

    // Форматируем количество подписчиков
    const formatSubscribers = (count) => {
        if (count >= 1000000) {
            return (count / 1000000).toFixed(1) + 'M';
        } else if (count >= 1000) {
            return (count / 1000).toFixed(1) + 'K';
        }
        return count.toString();
    };

    // Современная карточка с новым дизайном
    card.innerHTML = `
        <!-- Заголовок карточки -->
        <div class="channel-header">
            <div class="channel-avatar">${avatarLetter}</div>
            <div class="channel-info">
                <div class="channel-title">${channelName}</div>
                <div class="channel-username">@${channelUsername}</div>
            </div>
        </div>
        
        <!-- Метрики -->
        <div class="channel-metrics">
            <div class="metric-item">
                <div class="metric-value">${engagementRate}%</div>
                <div class="metric-label">Вовлеченность</div>
            </div>
        </div>
        
        <!-- Блок цены и дохода -->
        <div class="channel-price-block">
            <div class="channel-price">${price}₽</div>
            <div class="channel-earnings">
                <div class="earnings-value">${totalEarnings}₽</div>
                <div class="earnings-label">Заработано</div>
            </div>
        </div>
        
        <!-- Нижняя часть - статус и действия -->
        <div class="channel-footer">
            <div class="channel-status ${statusClass}">${statusText}</div>
            <div class="channel-actions">
                ${!isVerified ? `
                    <button class="btn btn-primary" onclick="startChannelVerification(${channel.id}, '${channelName}', '${channelUsername}')" title="Верифицировать канал">
                        🔐 Верифицировать
                    </button>
                ` : ''}
                <button class="btn btn-secondary" onclick="showDeleteConfirmation(${channel.id}, '${channelName}', '${channelUsername}')" title="Удалить канал">
                    🗑️
                </button>
            </div>
        </div>
    `;

    console.log('✅ Современная карточка канала создана');
    return card;
}

// Функция для запуска верификации канала из карточки
function startChannelVerification(channelId, channelName, channelUsername) {
    console.log(`🔐 Запуск верификации канала ${channelId}: ${channelName} (@${channelUsername})`);

    try {
        // Получаем данные пользователя Telegram
        const telegramUser = getTelegramUser();
        if (!telegramUser) {
            console.error('❌ Данные пользователя Telegram недоступны');
            alert('Ошибка: данные пользователя Telegram недоступны');
            return;
        }

        // Показываем индикатор загрузки
        const verifyButtons = document.querySelectorAll(`[onclick*="startChannelVerification(${channelId}"]`);
        verifyButtons.forEach(btn => {
            btn.disabled = true;
            btn.textContent = '⏳ Загрузка...';
        });

        // Отправляем запрос на получение нового кода верификации
        fetch('/api/channels', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': telegramUser.id.toString()
            },
            body: JSON.stringify({
                username: channelUsername.replace('@', ''),
                title: channelName,
                description: `Повторная верификация канала ${channelName}`,
                category: 'other',
                price_per_post: 0,
                owner_name: telegramUser.username || 'user',
                subscriber_count: 0,
                action: 'reverify', // Флаг для определения повторной верификации
                channel_id: channelId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.verification_code) {
                console.log('✅ Получен новый код верификации:', data.verification_code);
                
                // Показываем модальное окно верификации
                showVerificationModal(channelId, channelName, channelUsername, data.verification_code);
                
                // Обновляем статус канала в UI (визуально)
                updateChannelStatusInUI(channelId, 'pending');
                
            } else {
                console.error('❌ Ошибка получения кода верификации:', data.error);
                alert('Ошибка получения кода верификации: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('❌ Сетевая ошибка:', error);
            alert('Сетевая ошибка при получении кода верификации');
        })
        .finally(() => {
            // Восстанавливаем кнопки
            verifyButtons.forEach(btn => {
                btn.disabled = false;
                btn.textContent = '🔐 Верифицировать';
            });
        });

    } catch (error) {
        console.error('❌ Ошибка верификации:', error);
        alert('Ошибка верификации: ' + error.message);
    }
}

// Функция для обновления статуса канала в UI
function updateChannelStatusInUI(channelId, status) {
    console.log(`🔄 Обновляем статус канала ${channelId} на ${status}`);
    
    const channelCard = document.querySelector(`[data-channel-id="${channelId}"]`);
    if (channelCard) {
        const statusBadge = channelCard.querySelector('.status-badge');
        if (statusBadge) {
            // Обновляем текст и класс статуса
            if (status === 'verified') {
                statusBadge.textContent = 'Верифицирован';
                statusBadge.className = 'status-badge verified';
                
                // Удаляем кнопку верификации
                const verifyBtn = channelCard.querySelector('.verify-btn');
                if (verifyBtn) {
                    verifyBtn.remove();
                }
            } else if (status === 'pending') {
                statusBadge.textContent = 'На модерации';
                statusBadge.className = 'status-badge pending';
            }
            
            console.log(`✅ Статус канала ${channelId} обновлен в UI`);
        }
    }
}

// Функция для отображения модального окна редактирования канала
function showChannelEditModal(channelId) {
    console.log(`📝 Открытие редактирования канала ${channelId}`);
    
    // Получаем данные канала
    const channelCard = document.querySelector(`[data-channel-id="${channelId}"]`);
    if (!channelCard) {
        console.error('Канал не найден');
        return;
    }
    
    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal-overlay channel-edit-modal';
    modal.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background: rgba(0, 0, 0, 0.5) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 9999 !important;
        overflow: hidden !important;
    `;
    modal.innerHTML = `
        <div class="modal-content" style="
            background: white !important;
            border-radius: 12px !important;
            max-width: 500px !important;
            width: 90% !important;
            max-height: 80vh !important;
            overflow-y: auto !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important;
            position: relative !important;
            margin: auto !important;
        ">
            <div class="modal-header">
                <h2>Редактировать канал</h2>
                <button class="modal-close" onclick="closeEditModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="editChannelForm">
                    <div class="form-group">
                        <label for="editOwnerName">Имя владельца канала (контактное лицо)</label>
                        <input type="text" id="editOwnerName" class="form-input" placeholder="Введите имя владельца">
                    </div>
                    
                    <div class="form-group">
                        <label for="editPrice">Стоимость размещения (₽)</label>
                        <input type="number" id="editPrice" class="form-input" placeholder="0" min="0">
                    </div>
                    
                    <div class="form-group danger-zone">
                        <label>Опасная зона</label>
                        <button type="button" class="btn btn-danger" id="deleteChannelBtn" data-channel-id="${channelId}">
                            🗑️ Удалить канал
                        </button>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeEditModal()">Отмена</button>
                <button class="btn btn-primary" onclick="saveChannelChanges(${channelId})">Сохранить</button>
            </div>
        </div>
    `;
    
    // Отключаем скролл на body
    document.body.style.overflow = 'hidden';
    
    document.body.appendChild(modal);
    
    // Добавляем event listener для кнопки удаления
    const deleteBtn = modal.querySelector('#deleteChannelBtn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const channelId = this.getAttribute('data-channel-id');
            console.log(`🗑️ Клик по кнопке удаления канала ${channelId}`);
            
            // Используем подход из channels-modals.js
            if (window.showDeleteConfirmation) {
                // Получаем данные о канале из карточки
                const channelCard = document.querySelector(`[data-channel-id="${channelId}"]`);
                let channelName = 'Канал';
                let channelUsername = 'channel';
                
                if (channelCard) {
                    const nameElement = channelCard.querySelector('.channel-name');
                    if (nameElement) {
                        channelName = nameElement.textContent.trim();
                    }
                }
                
                console.log(`📋 Данные канала для удаления: ID=${channelId}, Name=${channelName}, Username=${channelUsername}`);
                
                // Закрываем текущий модал редактирования
                closeEditModal();
                // Показываем модал подтверждения удаления
                window.showDeleteConfirmation(parseInt(channelId), channelName, channelUsername);
            } else {
                // Fallback: используем стандартный confirm
                confirmChannelDeletion(parseInt(channelId));
            }
        });
        console.log('✅ Event listener добавлен для кнопки удаления');
    } else {
        console.error('❌ Кнопка удаления не найдена в модальном окне');
    }
    
    // Принудительно применяем стили после добавления в DOM
    setTimeout(() => {
        const modalElement = document.querySelector('.channel-edit-modal');
        if (modalElement) {
            modalElement.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background: rgba(0, 0, 0, 0.5) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                z-index: 9999 !important;
                overflow: hidden !important;
            `;
        }
    }, 0);
    
    // Загружаем текущие данные канала
    loadChannelDataForEdit(channelId);
}

// Функция для загрузки данных канала в форму редактирования
async function loadChannelDataForEdit(channelId) {
    try {
        const telegramUser = getTelegramUser();
        const response = await fetch(`/api/channels/${channelId}`, {
            headers: {
                'X-Telegram-User-Id': telegramUser.id.toString(),
                'X-Telegram-User-Data': JSON.stringify(telegramUser)
            }
        });
        
        if (response.ok) {
            const channel = await response.json();
            
            // Заполняем форму
            const editOwnerName = document.getElementById('editOwnerName');
            if (editOwnerName) {
                editOwnerName.value = channel.owner_name || channel.contact_name || '';
            }
            const editPrice = document.getElementById('editPrice');
            if (editPrice) {
                editPrice.value = channel.price_per_post || channel.placement_price || 0;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки данных канала:', error);
    }
}

// Функция для сохранения изменений канала
async function saveChannelChanges(channelId) {
    const editOwnerName = document.getElementById('editOwnerName');
    const editPrice = document.getElementById('editPrice');
    
    if (!editOwnerName || !editPrice) {
        console.error('Элементы формы редактирования не найдены');
        return;
    }
    
    const ownerName = editOwnerName.value;
    const price = editPrice.value;
    
    if (!ownerName.trim()) {
        alert('Пожалуйста, укажите имя владельца канала');
        return;
    }
    
    try {
        const telegramUser = getTelegramUser();
        const response = await fetch(`/api/channels/${channelId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': telegramUser.id.toString(),
                'X-Telegram-User-Data': JSON.stringify(telegramUser)
            },
            body: JSON.stringify({
                owner_name: ownerName,
                price_per_post: parseFloat(price) || 0
            })
        });
        
        if (response.ok) {
            console.log('✅ Канал обновлен успешно');
            closeEditModal();
            loadUserChannels(); // Перезагружаем список каналов
        } else {
            const error = await response.json();
            alert(`Ошибка сохранения: ${error.message || 'Неизвестная ошибка'}`);
        }
    } catch (error) {
        console.error('Ошибка сохранения изменений:', error);
        alert('Ошибка сохранения изменений');
    }
}

// Функция для закрытия модального окна редактирования
function closeEditModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
    }
    // Восстанавливаем скролл на body
    document.body.style.overflow = '';
}

// Функция для подтверждения удаления канала
function confirmChannelDeletion(channelId) {
    console.log(`🗑️ Вызван confirmChannelDeletion для канала ${channelId}`);
    console.log(`🔍 Тип channelId: ${typeof channelId}, значение: ${channelId}`);
    
    if (confirm('Вы уверены, что хотите удалить этот канал? Это действие нельзя отменить.')) {
        console.log(`✅ Пользователь подтвердил удаление канала ${channelId}`);
        deleteChannel(channelId);
    } else {
        console.log(`❌ Пользователь отменил удаление канала ${channelId}`);
    }
}

// Функция для удаления канала
async function deleteChannel(channelId) {
    console.log(`🗑️ Начинаем удаление канала ${channelId}`);
    
    try {
        const telegramUser = getTelegramUser();
        console.log('👤 Telegram User:', telegramUser);
        
        if (!telegramUser || !telegramUser.id) {
            alert('Ошибка авторизации. Пожалуйста, перезагрузите страницу.');
            return;
        }
        
        console.log(`📤 Отправляем DELETE запрос на /api/channels/${channelId}`);
        
        const response = await fetch(`/api/channels/${channelId}`, {
            method: 'DELETE',
            headers: {
                'X-Telegram-User-Id': telegramUser.id.toString(),
                'X-Telegram-User-Data': JSON.stringify(telegramUser)
            }
        });
        
        console.log(`📊 Статус ответа: ${response.status}`);
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Канал удален успешно:', result);
            alert('Канал успешно удален');
            closeEditModal();
            loadUserChannels(); // Перезагружаем список каналов
        } else {
            const error = await response.json();
            console.error('❌ Ошибка от сервера:', error);
            alert(`Ошибка удаления: ${error.message || 'Неизвестная ошибка'}`);
        }
    } catch (error) {
        console.error('❌ Исключение при удалении канала:', error);
        alert('Ошибка удаления канала: ' + error.message);
    }
}

// Тестовые функции удалены
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
            // Используем единое модальное окно из channels-modals.js
            if (typeof createVerificationModalProgrammatically === 'function') {
                createVerificationModalProgrammatically(
                    channelId,
                    channelName,
                    usernameForDisplay,
                    verificationCode
                );
            } else {
                // Fallback если функция не доступна
                alert(`✅ Код верификации: ${verificationCode}`);
            }

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

    const emptyState = document.getElementById('emptyState');
    if (emptyState) {
        emptyState.style.display = 'block';
    }
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
// Тестовые функции удалены
window.confirmChannelDeletion = confirmChannelDeletion;
window.deleteChannel = deleteChannel;
window.closeEditModal = closeEditModal;
window.saveChannelChanges = saveChannelChanges;
window.refreshChannelStatistics = refreshChannelStatistics;
window.updateChannelCard = updateChannelCard;
window.debugChannelData = debugChannelData;