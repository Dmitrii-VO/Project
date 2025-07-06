// Все переменные для модальных окон:
let verificationChannelData = null;
let channelToDelete = null

// Функции модального окна удаления:
 //Показать модальное окно подтверждения удаления
function showDeleteConfirmation(channelId, channelName, channelUsername) {
    console.log(`🗑️ Показываем подтверждение удаления канала ${channelId}`);

    channelToDelete = channelId;

    // Удаляем старое модальное окно если существует
    const oldModal = document.getElementById('deleteChannelModal');
    if (oldModal) {
        oldModal.remove();
    }

    // Создаем новое модальное окно
    const modal = document.createElement('div');
    modal.id = 'deleteChannelModal';
    modal.className = 'modal';
    modal.style.display = 'flex';

    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeDeleteModal()"></div>
        <div class="modal-content">
            <div class="modal-header">
                <h3>🗑️ Удалить канал</h3>
                <button class="modal-close" onclick="closeDeleteModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="confirmation-content">
                    <div class="channel-info" id="deleteChannelInfo">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div class="channel-avatar" style="width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; background: #e5e7eb; border-radius: 50%; font-weight: bold;">
                                ${channelName.substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <div style="font-weight: 600; color: #111827;">${channelName}</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">${channelUsername || 'Без username'}</div>
                            </div>
                        </div>
                    </div>
                    <div style="background: #fef3cd; border: 1px solid #f59e0b; border-radius: var(--border-radius-sm); padding: 16px; margin: 16px 0; color: #92400e;">
                        <strong>⚠️ Внимание!</strong><br>
                        Это действие нельзя отменить. Канал будет удален из системы.
                    </div>
                    <div style="text-align: center; font-weight: 600; color: var(--text-primary); margin: 16px 0;">
                        Вы действительно хотите удалить этот канал?
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeDeleteModal()">
                    Отмена
                </button>
                <button class="btn btn-danger" id="confirmDeleteBtn" onclick="confirmChannelDeletion()">
                    🗑️ Удалить канал
                </button>
            </div>
        </div>
    `;

    // Добавляем в body
    document.body.appendChild(modal);

    // Блокируем прокрутку страницы
    document.body.style.overflow = 'hidden';

    console.log('✅ Модальное окно удаления создано заново');
}
function closeDeleteModal() {
    console.log('❌ Закрываем модальное окно удаления');
    
    // Используем универсальную функцию
    closeModal();
    
    // Дополнительная логика для этого конкретного модального окна
    channelToDelete = null;
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = '🗑️ Удалить канал';
    }
}
// Закрытие модального окна по клику на оверлей
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});
async function confirmChannelDeletion() {
    if (!channelToDelete) {
        console.error('❌ Нет канала для удаления');
        return;
    }

    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const originalText = confirmBtn.textContent;

    try {
        // Отключаем кнопку и показываем загрузку
        confirmBtn.disabled = true;
        confirmBtn.textContent = '⏳ Удаляем...';

        console.log(`🗑️ Удаляем канал ${channelToDelete}`);

        // Получаем данные Telegram пользователя
        const telegramUser = getTelegramUser();
        if (!telegramUser) {
            throw new Error('Данные пользователя Telegram недоступны');
        }

        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUser.id.toString()
        };

        if (telegramUser.username) {
            headers['X-Telegram-Username'] = telegramUser.username;
        }
       // if (telegramUser.first_name) {
        //    headers['X-Telegram-First-Name'] = telegramUser.first_name;
        //}
       // if (telegramUser.last_name) {
       //     headers['X-Telegram-Last-Name'] = telegramUser.last_name;
       // }

        // Отправляем DELETE запрос
        const response = await fetch(`/api/channels/${channelToDelete}`, {
            method: 'DELETE',
            headers: headers
        });

        const data = await response.json();

        if (response.ok && data.success) {
            console.log('✅ Канал удален:', data.message);
            closeDeleteModal();

            // Показываем уведомление об успехе
            showSuccessNotification(data.message || 'Канал успешно удален!');

            // НОВОЕ: Обновляем список каналов
            setTimeout(() => {
                loadUserChannels();
            }, 1000);

            // Удаляем карточку из DOM
            const channelCard = document.querySelector(`[data-channel-id="${channelToDelete}"]`);
            if (channelCard) {
                channelCard.style.transition = 'opacity 0.3s ease';
                channelCard.style.opacity = '0';
                setTimeout(() => {
                    channelCard.remove();

                    // Проверяем, остались ли каналы
                    const remainingChannels = document.querySelectorAll('.channel-card[data-user-channel="true"]');
                    if (remainingChannels.length === 0) {
                        showEmptyState();
                    }
                }, 300);
            }

        } else {
            // Обработка ошибок
            const errorMessage = data.message || data.error || 'Неизвестная ошибка';
            console.error('❌ Ошибка удаления канала:', errorMessage);

            showNotification('error', `❌ Ошибка: ${errorMessage}`);
        }

    } catch (error) {
        console.error('💥 Ошибка при удалении канала:', error);
        showNotification('error', '❌ Ошибка подключения к серверу');
    } finally {
        // Восстанавливаем состояние кнопки
        confirmBtn.disabled = false;
        confirmBtn.textContent = originalText;
    }
}

// Функции модального окна верификации:
function showVerificationModal(channelId, channelName, channelUsername) {        
            console.log(`🔐 Показываем верификацию для канала ${channelId}`);
            
            verificationChannelData = { id: channelId, name: channelName, username: channelUsername };

            const content = document.getElementById('verificationContent');
            content.innerHTML = `
                <div class="verification-info">
                    <div class="channel-info" style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                        <div class="channel-avatar" style="width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; background: #e5e7eb; border-radius: 50%; font-weight: bold; font-size: 1.2rem;">
                            ${channelName.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #111827; font-size: 1.1rem;">${channelName}</div>
                            <div style="color: #6b7280;">${channelUsername || 'Без username'}</div>
                        </div>
                    </div>

                    <div class="instruction-block" style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                        <h4 style="color: #0369a1; margin-bottom: 12px;">📋 Инструкция по верификации:</h4>
                        <ol style="margin: 0; padding-left: 20px; color: #374151;">
                            <li style="margin-bottom: 8px;">Нажмите кнопку "Начать верификацию"</li>
                            <li style="margin-bottom: 8px;">Получите уникальный код верификации</li>
                            <li style="margin-bottom: 8px;">Опубликуйте код в вашем канале <strong>${channelUsername}</strong></li>
                            <li style="margin-bottom: 8px;">Переслать сообщение с кодом нашему боту</li>
                            <li style="margin-bottom: 8px;">Дождитесь подтверждения верификации</li>
                        </ol>
                    </div>

                    <div class="warning-block" style="background: #fef3cd; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px;">
                        <small style="color: #92400e;">
                            💡 <strong>Совет:</strong> После публикации кода вы можете удалить сообщение из канала.
                            Главное — успеть переслать его боту!
                        </small>
                    </div>
                </div>
            `;

            document.getElementById('verificationModal').style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }

async function startVerification() {
    if (!verificationChannelData) {
        console.error('❌ Нет данных канала для верификации');
        return;
    }

    const startBtn = document.getElementById('startVerificationBtn');
    const originalText = startBtn.textContent;

    try {
        startBtn.disabled = true;
        startBtn.textContent = '⏳ Запуск верификации...';

        const telegramUser = getTelegramUser();
        if (!telegramUser) {
            throw new Error('Данные пользователя Telegram недоступны');
        }

        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUser.id.toString()
        };

        if (telegramUser.username) {
            headers['X-Telegram-Username'] = telegramUser.username;
        }

        // ИСПРАВЛЕНИЕ: Используем тот же endpoint, что и для добавления канала
        const response = await fetch('/api/channels', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                username: verificationChannelData.username?.replace('@', '') || 'unknown',
                category: 'other',
                description: 'Повторная верификация канала',
                payment_terms: 'prepayment',
                action: 'reverify', // Флаг для определения повторной верификации
                channel_id: verificationChannelData.id
            })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Ошибка сервера');
        }

        // Закрываем модальное окно верификации
        closeModal();

        // Показываем инструкции как при добавлении канала
        const verificationCode = result.verification_code || result.channel?.verification_code;
        const channelUsername = result.channel?.username || verificationChannelData.username;

        if (verificationCode) {
            // Создаем модальное окно с инструкциями (такое же как при добавлении)
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
                                Откройте ваш канал <strong>${channelUsername}</strong>
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

    }
    catch (error) {
        console.error('💥 Ошибка верификации:', error);
        showErrorNotification(error.message);
    }
    finally {
        startBtn.disabled = false;
        startBtn.textContent = originalText;
    }

}
function showVerificationCode(data) {
            const content = document.getElementById('verificationContent');
            content.innerHTML = `
                <div class="verification-code-display">
                    <div class="channel-info" style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                        <div class="channel-avatar" style="width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; background: #e5e7eb; border-radius: 50%; font-weight: bold; font-size: 1.2rem;">
                            ${verificationChannelData.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #111827; font-size: 1.1rem;">${verificationChannelData.name}</div>
                            <div style="color: #6b7280;">${verificationChannelData.username || 'Без username'}</div>
                        </div>
                    </div>

                    <div class="code-block" style="background: #1f2937; color: #10b981; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                        <h4 style="color: #10b981; margin-bottom: 15px;">🔐 Ваш код верификации:</h4>
                        <div class="verification-code" style="
                            font-family: 'Courier New', monospace;
                            font-size: 24px;
                            font-weight: bold;
                            letter-spacing: 2px;
                            cursor: pointer;
                            user-select: all;
                            padding: 10px;
                            border: 2px dashed #10b981;
                            border-radius: 4px;
                            transition: all 0.2s ease;
                        " onclick="copyVerificationCode(this, '${data.verification_code}')">
                            ${data.verification_code}
                        </div>
                        <small style="color: #9ca3af; margin-top: 10px; display: block;">
                            Нажмите на код, чтобы скопировать
                        </small>
                    </div>

                    <div class="instruction-steps" style="background: #f9fafb; border-radius: 8px; padding: 16px;">
                        <h4 style="color: #374151; margin-bottom: 12px;">📋 Следующие шаги:</h4>
                        <ol style="margin: 0; padding-left: 20px; color: #4b5563;">
                            <li style="margin-bottom: 8px;">Скопируйте код выше</li>
                            <li style="margin-bottom: 8px;">Откройте ваш канал <strong>${verificationChannelData.username}</strong></li>
                            <li style="margin-bottom: 8px;">Опубликуйте сообщение с этим кодом</li>
                            <li style="margin-bottom: 8px;">Переслать сообщение нашему боту</li>
                            <li>Дождитесь автоматического подтверждения</li>
                        </ol>
                    </div>
                </div>
            `;

            // Изменяем кнопку
            const startBtn = document.getElementById('startVerificationBtn');
            startBtn.textContent = '🔄 Проверить статус';
            startBtn.onclick = () => checkVerificationStatus();
        }
function copyVerificationCode(code, element = null) {
    navigator.clipboard.writeText(code).then(() => {
        // Если передан элемент, изменяем его стиль
        if (element && element.style) {
            const originalBg = element.style.background;
            const originalText = element.textContent;

            element.style.background = '#1b5e20';
            element.innerHTML = `${code} ✅ Скопировано!`;

            setTimeout(() => {
                element.style.background = originalBg;
                element.innerHTML = code;
            }, 2000);
        }

        // Показываем уведомление
        if (typeof showNotification === 'function') {
            showNotification('success', '📋 Код скопирован в буфер обмена!');
        } else {
            console.log('✅ Код скопирован:', code);
        }

    }).catch(() => {
        // Fallback для старых браузеров
        const textArea = document.createElement('textarea');
        textArea.value = code;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        if (element && element.style) {
            element.style.background = '#1b5e20';
            element.innerHTML = `${code} ✅`;
            setTimeout(() => {
                element.style.background = '#333';
                element.innerHTML = code;
            }, 2000);
        }

        alert('📋 Код скопирован в буфер обмена!');
    });
}
async function checkVerificationStatus() {
            if (!verificationChannelData) return;

            try {
                const telegramUser = getTelegramUser();
                const headers = {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': telegramUser.id.toString()
                };

                const response = await fetch(`/api/channels/${verificationChannelData.id}`, {
                    method: 'GET',
                    headers: headers
                });

                const data = await response.json();

                if (data.success && data.channel && (data.channel.is_verified || data.channel.status === 'verified')) {
                    // Канал верифицирован!
                    showSuccessNotification('🎉 Канал успешно верифицирован!');
                    closeModal();

                    // Обновляем список каналов
                    setTimeout(() => {
                        loadUserChannels();
                    }, 1000);
                } else {
                    showInfoNotification('⏳ Верификация еще не завершена. Убедитесь, что код опубликован и переслан боту.');
                }

            } catch (error) {
                console.error('Ошибка проверки статуса:', error);
                showErrorNotification('Ошибка проверки статуса верификации');
            }
        }

// Функции создания модальных окон:
function showVerificationSuccess(data) {
            const modal = createModal();
            modal.innerHTML = `
                <div class="verification-modal success">
                    <div class="modal-header">
                        <div class="success-icon">✅</div>
                        <h3>Канал верифицирован!</h3>
                    </div>
                    <div class="modal-body">
                        <p><strong>${data.message}</strong></p>
                        <div class="channel-info">
                            <p><strong>Канал:</strong> ${data.channel?.title || 'Неизвестный канал'}</p>
                            <p><strong>Статус:</strong> <span class="status verified">Верифицирован</span></p>
                            <p><strong>Дата верификации:</strong> ${formatDate(data.channel?.verified_at)}</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" onclick="closeModal()">
                            Отлично!
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        }
function showVerificationError(data) {
            const modal = createModal();
            const instructions = data.instructions || [];
            const verificationCode = data.verification_code;

            modal.innerHTML = `
                <div class="verification-modal error">
                    <div class="modal-header">
                        <div class="error-icon">❌</div>
                        <h3>Верификация не удалась</h3>
                    </div>
                    <div class="modal-body">
                        <p class="error-message">${data.error || 'Неизвестная ошибка'}</p>

                        ${verificationCode ? `
                            <div class="verification-code-block">
                                <h4>Код верификации:</h4>
                                <div class="code-display">
                                    <code>${verificationCode}</code>
                                    <button class="btn btn-small" onclick="copyToClipboard('${verificationCode}')">
                                        📋 Копировать
                                    </button>
                                </div>
                            </div>
                        ` : ''}

                        ${instructions.length > 0 ? `
                            <div class="instructions">
                                <h4>Инструкции:</h4>
                                <ol>
                                    ${instructions.map(instruction => `<li>${instruction}</li>`).join('')}
                                </ol>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="closeModal()">
                            Понятно
                        </button>
                        <button class="btn btn-primary" onclick="retryVerification(${data.channel?.id || 'null'})">
                            Попробовать снова
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
        }
function createModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            `;
            return modal;
        }

function retryVerification(channelId) {
    closeModal();
    if (channelId) {
        verifyChannel(channelId);
    }
}
function updateChannelStatus(channelId, status) {
            const channelCard = document.querySelector(`[data-channel-id="${channelId}"]`);
            if (channelCard) {
                const statusElement = channelCard.querySelector('.channel-status');
                if (statusElement) {
                    statusElement.className = `channel-status ${status}`;
                    statusElement.textContent = status === 'verified' ? 'Верифицирован' : 'На модерации';
                }

                // Скрываем кнопку верификации
                const verifyButton = channelCard.querySelector('.btn-warning');
                if (verifyButton && status === 'verified') {
                    verifyButton.style.display = 'none';
                }
            }
        }
function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Показываем уведомление
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #28a745;
                    color: white;
                    padding: 12px 20px;
                    border-radius: 5px;
                    z-index: 10001;
                    font-weight: bold;
                `;
                notification.textContent = 'Код скопирован!';
                document.body.appendChild(notification);

                setTimeout(() => {
                    notification.remove();
                }, 2000);
            }).catch(() => {
                // Fallback для старых браузеров
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);

                alert('Код скопирован в буфер обмена');
            });
        }

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeDeleteModal();
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDeleteModal();
    }
});
async function startChannelVerification(channelId, channelName, channelUsername) {
    console.log(`🔐 Запуск верификации канала ${channelId}: ${channelName}`);

    try {
        // Получаем данные пользователя Telegram
        const telegramUser = getTelegramUser();
        if (!telegramUser) {
            throw new Error('Данные пользователя Telegram недоступны');
        }

        // Показываем индикатор загрузки
        showNotification('info', '⏳ Запускаем верификацию...');

        // Подготавливаем заголовки для запроса
        const headers = {
            'Content-Type': 'application/json',
            'X-Telegram-User-Id': telegramUser.id.toString()
        };

        if (telegramUser.username) {
            headers['X-Telegram-Username'] = telegramUser.username;
        }

        // Отправляем запрос на сервер для генерации нового кода верификации
        const response = await fetch('/api/channels', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                username: channelUsername?.replace('@', '') || 'unknown',
                category: 'other',
                description: 'Повторная верификация канала',
                payment_terms: 'prepayment',
                action: 'reverify', // Флаг повторной верификации
                channel_id: channelId
            })
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Ошибка сервера');
        }

        // Получаем код верификации из ответа
        const verificationCode = result.verification_code || result.channel?.verification_code;
        const usernameForDisplay = result.channel?.username || channelUsername;

        if (verificationCode) {
            // Показываем модальное окно с инструкциями
            showVerificationInstructions(verificationCode, usernameForDisplay);
        } else {
            // Fallback если код не получен
            showNotification('success', '✅ Верификация запущена!');
        }

    } catch (error) {
        console.error('💥 Ошибка верификации:', error);
        showNotification('error', `❌ Ошибка: ${error.message}`);
    }
}
function showVerificationInstructions(verificationCode, channelUsername) {
    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.background = 'rgba(0,0,0,0.8)';

    modal.innerHTML = `
        <div style="
            background: white; 
            padding: 30px; 
            border-radius: 15px;
            max-width: min(500px, 95vw); 
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            max-height: 95vh; 
            overflow-y: auto;
        ">
            <!-- Заголовок -->
            <div style="font-size: 48px; margin-bottom: 20px;">📝</div>
            <h3 style="color: #333; margin-bottom: 20px; font-size: 1.5rem;">
                Подтвердите владение каналом
            </h3>

            <!-- Блок с кодом верификации -->
            <div style="
                background: #e3f2fd; 
                padding: 20px; 
                border-radius: 10px;
                margin: 20px 0; 
                border-left: 4px solid #2196f3;
            ">
                <h4 style="color: #1976d2; margin-bottom: 15px; font-size: 1.1rem;">
                    🔐 Код верификации:
                </h4>

                <div id="verificationCodeBlock" style="
                    background: #333; 
                    color: #00ff00; 
                    padding: 15px;
                    border-radius: 8px; 
                    font-family: 'Courier New', monospace;
                    font-size: 20px; 
                    font-weight: bold; 
                    letter-spacing: 2px;
                    margin: 15px 0; 
                    cursor: pointer; 
                    user-select: all;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    transition: all 0.2s ease;
                " onclick="copyVerificationCode('${verificationCode}', this)">
                    ${verificationCode}
                </div>

                <small style="color: #666; font-size: 0.85rem;">
                    💡 Нажмите на код, чтобы скопировать
                </small>
            </div>

            <!-- Пошаговая инструкция -->
            <div style="
                background: #f5f5f5; 
                padding: 20px; 
                border-radius: 10px;
                margin: 20px 0; 
                text-align: left;
            ">
                <h4 style="color: #333; margin-bottom: 15px; text-align: center; font-size: 1.1rem;">
                    📋 Пошаговая инструкция:
                </h4>

                <ol style="margin: 0; padding-left: 20px; color: #555; line-height: 1.6;">
                    <li style="margin-bottom: 10px;">
                        <strong>Скопируйте код выше</strong> (нажмите на него)
                    </li>
                    <li style="margin-bottom: 10px;">
                        Откройте ваш канал <strong>@${channelUsername}</strong>
                    </li>
                    <li style="margin-bottom: 10px;">
                        <strong>Опубликуйте сообщение</strong> с кодом: <code style="background: #eee; padding: 2px 4px; border-radius: 3px;">${verificationCode}</code>
                    </li>
                    <li style="margin-bottom: 10px;">
                        <strong>Переслать это сообщение</strong> нашему боту
                    </li>
                    <li style="margin-bottom: 10px;">
                        Дождитесь <strong>уведомления об успешной верификации</strong>
                    </li>
                </ol>
            </div>

            <!-- Полезный совет -->
            <div style="
                background: #fff3cd; 
                padding: 15px; 
                border-radius: 8px;
                margin: 15px 0; 
                border-left: 4px solid #ffc107;
            ">
                <small style="color: #856404; font-size: 0.9rem;">
                    💡 <strong>Совет:</strong> После публикации кода вы можете сразу удалить сообщение из канала.
                    Главное — успеть переслать его боту!
                </small>
            </div>

            <!-- Кнопки действий -->
            <div style="margin-top: 25px;">
                <button onclick="closeVerificationModalAndRefresh(this)" style="
                    background: #2196f3; 
                    color: white; 
                    border: none;
                    padding: 12px 30px; 
                    border-radius: 8px; 
                    font-size: 16px;
                    cursor: pointer; 
                    font-weight: 600;
                    margin-right: 10px;
                ">
                    Понятно, приступаю!
                </button>

                <button onclick="copyVerificationCode('${verificationCode}')" style="
                    background: #28a745; 
                    color: white; 
                    border: none;
                    padding: 12px 20px; 
                    border-radius: 8px; 
                    font-size: 14px;
                    cursor: pointer; 
                    font-weight: 600;
                ">
                    📋 Копировать код
                </button>
            </div>

            <!-- Ссылка на бота -->
            <div style="margin-top: 15px;">
                <a href="https://t.me/YOUR_BOT_USERNAME" target="_blank" style="
                    color: #2196f3; 
                    text-decoration: none; 
                    font-size: 14px; 
                    font-weight: 600;
                ">
                    🤖 Открыть бота для верификации
                </a>
            </div>
        </div>
    `;
    // Автоматическое закрытие через 30 секунд
    setTimeout(() => {
        if (document.body.contains(modal)) {
            closeModal(modal);
            if (typeof showNotification === 'function') {
                showNotification('info', '⏰ Окно автоматически закрыто. Не забудьте опубликовать код в канале!');
            }
        }
    }, 10000);
    // Добавляем модальное окно в DOM
    document.body.appendChild(modal);

    // Закрытие по клику на фон
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal(modal);
        }
    });
}
/**
 * Закрыть модальное окно верификации и обновить список каналов
 */
function closeVerificationModalAndRefresh(element) {
    // Закрываем модальное окно
    closeModal(element);

    // Показываем уведомление что код нужно опубликовать
    if (typeof showNotification === 'function') {
        showNotification('info', '📝 Опубликуйте код в канале и переслать его боту для завершения верификации');
    }

    // Обновляем список каналов через небольшую задержку
    if (typeof loadUserChannels === 'function') {
        setTimeout(() => {
            loadUserChannels();
        }, 1000);
    }
}

// Делаем функцию глобально доступной
window.closeVerificationModalAndRefresh = closeVerificationModalAndRefresh;
// Делаем функции глобально доступными для onclick
window.closeDeleteModal = closeDeleteModal;
window.confirmChannelDeletion = confirmChannelDeletion;
window.startVerification = startVerification;
window.showDeleteConfirmation = showDeleteConfirmation;
window.startChannelVerification = startChannelVerification;