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
    modal.className = 'modal-backdrop';

    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeDeleteModal()"></div>
        <div class="modal-content" style="pointer-events: auto; z-index: 9999; position: relative; background: white; border-radius: 12px; padding: 24px; max-width: 400px; width: 90%;">
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
                <button class="btn btn-danger" id="confirmDeleteBtn" style="pointer-events: auto; z-index: 9999; position: relative;">
                    🗑️ Удалить канал
                </button>
            </div>
        </div>
    `;

    // Добавляем в body
    document.body.appendChild(modal);

    // Показываем модальное окно с классом show
    modal.classList.add('show');

    // Добавляем event listener для кнопки подтверждения удаления
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        // Убираем любые существующие обработчики
        confirmBtn.onclick = null;
        
        // Добавляем обработчик клика
        confirmBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔄 Клик по кнопке подтверждения удаления');
            confirmChannelDeletionModal();
        }, { capture: true });
        
        // Добавляем обработчик для touch событий (для мобильных устройств)
        confirmBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔄 Touch по кнопке подтверждения удаления');
            confirmChannelDeletionModal();
        }, { capture: true });
        
        // Добавляем обработчик для mousedown (более низкий уровень)
        confirmBtn.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔄 Mousedown по кнопке подтверждения удаления');
            confirmChannelDeletionModal();
        }, { capture: true });
        
        console.log('✅ Event listener добавлен для кнопки подтверждения удаления');
    }

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
async function confirmChannelDeletionModal() {
    console.log('🔄 Начинаем confirmChannelDeletionModal');
    console.log(`🔍 channelToDelete: ${channelToDelete}`);
    
    if (!channelToDelete) {
        console.error('❌ Нет канала для удаления');
        return;
    }

    const confirmBtn = document.getElementById('confirmDeleteBtn');
    console.log(`🔍 confirmBtn найден: ${!!confirmBtn}`);
    
    if (!confirmBtn) {
        console.error('❌ Кнопка confirmDeleteBtn не найдена');
        return;
    }
    
    const originalText = confirmBtn.textContent;
    console.log(`🔍 originalText: ${originalText}`);

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
        console.log(`📤 Отправляем DELETE запрос на /api/channels/${channelToDelete}`);
        console.log(`🔑 Заголовки:`, headers);
        
        const response = await fetch(`/api/channels/${channelToDelete}`, {
            method: 'DELETE',
            headers: headers
        });

        console.log(`📊 Статус ответа: ${response.status}`);
        console.log(`📊 Response OK: ${response.ok}`);
        
        const data = await response.json();
        console.log(`📄 Данные ответа:`, data);

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
            console.error('❌ Ошибка удаления канала');
            console.error('📊 response.ok:', response.ok);
            console.error('📊 data.success:', data.success);
            console.error('📄 Полные данные:', data);
            
            const errorMessage = data.message || data.error || 'Неизвестная ошибка';
            console.error('❌ Сообщение об ошибке:', errorMessage);

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

// Тестовая функция для проверки удаления канала
async function testDeleteChannelModal(channelId) {
    console.log(`🧪 Тестируем удаление канала ${channelId} через модал`);
    
    // Устанавливаем channelToDelete
    channelToDelete = channelId;
    console.log(`🔍 Установлен channelToDelete: ${channelToDelete}`);
    
    // Вызываем функцию удаления
    await confirmChannelDeletionModal();
}

// Функция для тестирования всего процесса удаления канала
function testFullDeleteProcess(channelId) {
    console.log(`🧪 Тестируем полный процесс удаления канала ${channelId}`);
    
    // Сначала показываем модал подтверждения
    showDeleteConfirmation(channelId, 'Тестовый канал', 'test_channel');
    
    // Даем время на отображение модала
    setTimeout(() => {
        console.log('🔍 Проверяем наличие модального окна и кнопки');
        
        const modal = document.getElementById('deleteChannelModal');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        
        console.log(`🔍 Модал найден: ${!!modal}`);
        console.log(`🔍 Кнопка найдена: ${!!confirmBtn}`);
        console.log(`🔍 channelToDelete: ${channelToDelete}`);
        
        if (modal && confirmBtn) {
            console.log('✅ Все элементы найдены, можно тестировать удаление');
            
            // Можно сразу вызвать функцию удаления
            // confirmChannelDeletionModal();
        } else {
            console.error('❌ Не все элементы найдены');
        }
    }, 500);
}

// Функции модального окна верификации:
function showVerificationModal(channelId, channelName, channelUsername, verificationCode) {        
            console.log(`🔐 Показываем верификацию для канала ${channelId}`);
            console.log(`🔐 Код верификации: ${verificationCode}`);
            
            // Проверяем, что вызов функции корректный (с правильными параметрами)
            if (!channelId || !channelName || !verificationCode) {
                console.error('❌ Некорректные параметры для showVerificationModal:', { channelId, channelName, channelUsername, verificationCode });
                return;
            }
            
            // Проверяем, что функция вызвана пользователем, а не автоматически
            const stack = new Error().stack;
            console.log('📍 Call stack:', stack);
            
            try {
                // Используем программное создание модального окна как основной метод
                // так как это более надежно и не зависит от HTML структуры
                createVerificationModalProgrammatically(channelId, channelName, channelUsername, verificationCode);
            } catch (error) {
                console.error('❌ Ошибка создания модального окна:', error);
                // Fallback к простому alert
                showSimpleAlert(channelName, channelUsername, verificationCode);
            }
        }

// Последний резервный метод - простой alert
function showSimpleAlert(channelName, channelUsername, verificationCode) {
    const message = `🔐 Код верификации для канала "${channelName}" (@${channelUsername}):\n\n${verificationCode}\n\nСкопируйте этот код и опубликуйте в вашем канале, затем переслать нашему боту.`;
    
    alert(message);
    
    // Попытка скопировать код в буфер обмена
    try {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(verificationCode);
            console.log('✅ Код скопирован в буфер обмена');
        }
    } catch (error) {
        console.error('❌ Не удалось скопировать код:', error);
    }
}

// Функция для создания модального окна программно
function createVerificationModalProgrammatically(channelId, channelName, channelUsername, verificationCode) {
    console.log('🔧 Создаем модальное окно верификации программно...');
    console.log('🔍 Параметры:', { channelId, channelName, channelUsername, verificationCode });
    
    // Удаляем все существующие модальные окна верификации
    const existingModals = document.querySelectorAll('#verificationModal');
    existingModals.forEach(modal => {
        console.log('🗑️ Удаляем существующее модальное окно:', modal);
        modal.remove();
    });
    
    // Проверяем, что модальное окно действительно нужно показать
    if (!channelId || !channelName || !verificationCode) {
        console.error('❌ Недостаточно данных для создания модального окна верификации');
        return;
    }
    
    // Создаем новое модальное окно
    const modal = document.createElement('div');
    modal.id = 'verificationModal';
    modal.className = 'modal-backdrop';
    
    modal.innerHTML = `
        <div class="modal" style="background: white !important; border-radius: 8px !important; padding: 24px !important; max-width: 500px !important; width: 90% !important; max-height: 80vh !important; overflow-y: auto !important; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important; position: relative !important; z-index: 100000 !important; margin: 0 auto !important; flex-shrink: 0 !important; align-self: center !important; justify-self: center !important;">
            <div class="modal-header">
                <h3 class="modal-title">🔐 Подтвердите владение каналом</h3>
                <button class="modal-close" onclick="closeModal()" style="float: right; background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
            </div>
            <div class="modal-body">
                <div class="verification-info">
                    <div class="channel-info" style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                        <div class="channel-avatar" style="width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; background: #e5e7eb; border-radius: 50%; font-weight: bold; font-size: 1.2rem;">
                            ${channelName.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: #111827; font-size: 1.1rem;">${channelName}</div>
                            <div style="color: #6b7280;">@${channelUsername || 'Без username'}</div>
                        </div>
                    </div>

                    <div class="verification-code-block" style="background: #f0fdf4; border: 2px solid #10b981; border-radius: 8px; padding: 16px; margin-bottom: 16px; text-align: center;">
                        <h4 style="color: #047857; margin-bottom: 8px;">🔐 Ваш код верификации:</h4>
                        <div style="font-family: monospace; font-size: 18px; font-weight: bold; color: #047857; background: white; padding: 8px; border-radius: 4px; border: 1px solid #10b981; cursor: pointer; user-select: all;" onclick="copyToClipboard('${verificationCode}');" title="Нажмите для копирования">${verificationCode}</div>
                        <small style="color: #047857; margin-top: 8px; display: block;">Нажмите на код для копирования</small>
                    </div>
                    
                    <div class="instruction-block" style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                        <h4 style="color: #0369a1; margin-bottom: 12px;">📋 Инструкция по верификации:</h4>
                        <ol style="margin: 0; padding-left: 20px; color: #374151;">
                            <li style="margin-bottom: 8px;">Скопируйте код верификации выше</li>
                            <li style="margin-bottom: 8px;">Опубликуйте код в вашем канале <strong>@${channelUsername}</strong></li>
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
            </div>
            <div class="modal-footer" style="text-align: center; margin-top: 16px;">
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-right: 8px;">Отмена</button>
                <button class="btn btn-primary" onclick="closeModal()">Понятно</button>
            </div>
        </div>
    `;
    
    // Добавляем модальное окно в DOM
    document.body.appendChild(modal);
    console.log('🔍 Модальное окно добавлено в DOM:', modal);
    
    // Показываем модальное окно с классом show
    modal.classList.add('show');
    
    // Принудительно сбрасываем все возможные conflicting стили
    document.body.style.position = 'relative';
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    
    // Показываем модальное окно
    document.body.style.overflow = 'hidden';
    console.log('🔍 Стили применены - overflow: hidden');
    
    // Проверяем что модальное окно видно
    const computedStyle = window.getComputedStyle(modal);
    console.log('🔍 Computed styles:', {
        display: computedStyle.display,
        position: computedStyle.position,
        zIndex: computedStyle.zIndex,
        visibility: computedStyle.visibility,
        opacity: computedStyle.opacity
    });
    
    // Добавляем обработчик для закрытия по клику на backdrop
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    console.log('✅ Модальное окно верификации создано программно');
    
    // Дополнительная проверка через небольшую задержку
    setTimeout(() => {
        const modalInDom = document.getElementById('verificationModal');
        console.log('🔍 Модальное окно в DOM через 100ms:', modalInDom);
        if (modalInDom) {
            console.log('🔍 Размеры модального окна:', {
                width: modalInDom.offsetWidth,
                height: modalInDom.offsetHeight,
                top: modalInDom.offsetTop,
                left: modalInDom.offsetLeft
            });
            
            // Принудительное центрирование если модальное окно не по центру
            const innerModal = modalInDom.querySelector('.modal');
            if (innerModal) {
                console.log('🔄 Принудительное центрирование модального окна...');
                
                // Убеждаемся что модальное окно по центру
                modalInDom.style.display = 'flex';
                modalInDom.style.alignItems = 'center';
                modalInDom.style.justifyContent = 'center';
                
                // Принудительно центрируем внутренний контейнер
                innerModal.style.margin = '0 auto';
                innerModal.style.alignSelf = 'center';
                innerModal.style.justifySelf = 'center';
                
                console.log('✅ Принудительное центрирование выполнено');
            }
            
            // Если модальное окно не видно, попробуем альтернативный метод
            if (modalInDom.offsetWidth === 0 || modalInDom.offsetHeight === 0) {
                console.log('❌ Модальное окно не видно, создаем простое alert');
                createSimpleVerificationAlert(channelName, channelUsername, verificationCode);
            }
        } else {
            console.log('❌ Модальное окно не найдено, создаем простое alert');
            createSimpleVerificationAlert(channelName, channelUsername, verificationCode);
        }
    }, 100);
}

// Простой альтернативный метод показа кода верификации
function createSimpleVerificationAlert(channelName, channelUsername, verificationCode) {
    console.log('🚨 Создаем простое alert для верификации');
    
    // Удаляем все существующие модальные окна
    const existingModals = document.querySelectorAll('#verificationModal');
    existingModals.forEach(modal => modal.remove());
    
    // Создаем очень простое модальное окно
    const simpleModal = document.createElement('div');
    simpleModal.id = 'verificationModal';
    simpleModal.className = 'modal-backdrop';
    
    simpleModal.innerHTML = `
        <div style="background: white !important; padding: 30px !important; border-radius: 10px !important; max-width: 400px !important; width: 90% !important; text-align: center !important; box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important; margin: 0 auto !important; position: relative !important; max-height: 80vh !important; overflow-y: auto !important;">
            <h2 style="color: #333 !important; margin-bottom: 20px !important;">🔐 Код верификации</h2>
            <p style="color: #666 !important; margin-bottom: 15px !important;">Канал: <strong>${channelName}</strong></p>
            <p style="color: #666 !important; margin-bottom: 15px !important;">Username: <strong>@${channelUsername}</strong></p>
            <div style="background: #f0f9ff !important; border: 2px solid #0ea5e9 !important; border-radius: 8px !important; padding: 15px !important; margin: 20px 0 !important;">
                <p style="color: #0369a1 !important; margin-bottom: 10px !important; font-weight: bold !important;">Ваш код верификации:</p>
                <div style="font-family: monospace !important; font-size: 20px !important; font-weight: bold !important; color: #0369a1 !important; background: white !important; padding: 10px !important; border-radius: 5px !important; border: 1px solid #0ea5e9 !important; user-select: all !important;">${verificationCode}</div>
            </div>
            <p style="color: #666 !important; font-size: 14px !important; margin-bottom: 20px !important;">Скопируйте код и опубликуйте в вашем канале</p>
            <button onclick="copyToClipboard('${verificationCode}'); showNotification('Код скопирован!', 'success');" style="background: #0ea5e9 !important; color: white !important; border: none !important; padding: 10px 20px !important; border-radius: 5px !important; cursor: pointer !important; margin-right: 10px !important;">Скопировать код</button>
            <button onclick="closeModal()" style="background: #6b7280 !important; color: white !important; border: none !important; padding: 10px 20px !important; border-radius: 5px !important; cursor: pointer !important;">Закрыть</button>
        </div>
    `;
    
    document.body.appendChild(simpleModal);
    document.body.style.overflow = 'hidden';
    
    // Показываем модальное окно с классом show
    simpleModal.classList.add('show');
    
    // Обработчик для закрытия по клику на backdrop
    simpleModal.addEventListener('click', function(e) {
        if (e.target === simpleModal) {
            closeModal();
        }
    });
    
    console.log('✅ Простое модальное окно создано');
}

// Функция для копирования в буфер обмена
function copyToClipboard(text) {
    try {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                console.log('✅ Код скопирован в буфер обмена');
                showNotification('Код скопирован в буфер обмена!', 'success');
            }).catch(err => {
                console.error('❌ Ошибка копирования:', err);
                fallbackCopyTextToClipboard(text);
            });
        } else {
            fallbackCopyTextToClipboard(text);
        }
    } catch (error) {
        console.error('❌ Ошибка копирования:', error);
        fallbackCopyTextToClipboard(text);
    }
}

// Fallback метод копирования для старых браузеров
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            console.log('✅ Код скопирован в буфер обмена (fallback)');
            showNotification('Код скопирован в буфер обмена!', 'success');
        } else {
            console.error('❌ Не удалось скопировать код');
            showNotification('Не удалось скопировать код', 'error');
        }
    } catch (err) {
        console.error('❌ Ошибка копирования:', err);
        showNotification('Ошибка копирования', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Простая функция для показа уведомлений
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    if (type === 'success') {
        notification.style.background = '#10b981';
    } else if (type === 'error') {
        notification.style.background = '#ef4444';
    } else {
        notification.style.background = '#6366f1';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Делаем функции глобально доступными
window.showVerificationModal = showVerificationModal;
window.showDeleteConfirmation = showDeleteConfirmation;
window.createVerificationModalProgrammatically = createVerificationModalProgrammatically;
window.createSimpleVerificationAlert = createSimpleVerificationAlert;
window.showSimpleAlert = showSimpleAlert;
window.copyToClipboard = copyToClipboard;
window.showNotification = showNotification;

console.log('✅ Modal functions loaded:', {
    showVerificationModal: typeof window.showVerificationModal,
    showDeleteConfirmation: typeof window.showDeleteConfirmation
});

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
            // Используем единое модальное окно
            createVerificationModalProgrammatically(
                verificationChannelData.id,
                verificationChannelData.title || verificationChannelData.name,
                channelUsername,
                verificationCode
            );
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

// Делаем startVerification глобально доступной
window.startVerification = startVerification;
console.log('✅ startVerification function loaded:', typeof window.startVerification);

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
            modal.className = 'loading-overlay';
            modal.style.padding = '20px';
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
                notification.className = 'toast-notification success';
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
    // Используем единое модальное окно
    createVerificationModalProgrammatically(
        'temp',
        'Канал @' + channelUsername,
        channelUsername,
        verificationCode
    );
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
window.confirmChannelDeletionModal = confirmChannelDeletionModal;
window.testDeleteChannelModal = testDeleteChannelModal;
