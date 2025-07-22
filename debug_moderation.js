// Функция отладки модерации для запуска в консоли браузера
function debugModeration() {
    console.log('🔍 === ОТЛАДКА МОДЕРАЦИИ === 🔍');
    
    // Проверяем наличие элементов
    const moderationGrid = document.getElementById('moderationGrid');
    const moderationLoading = document.getElementById('moderationLoading');
    const moderationEmpty = document.getElementById('moderationEmpty');
    const adminTab = document.getElementById('admin-tab');
    const adminContent = document.getElementById('admin-moderation');
    
    console.log('📋 Элементы DOM:');
    console.log('  moderationGrid:', moderationGrid);
    console.log('  moderationLoading:', moderationLoading);
    console.log('  moderationEmpty:', moderationEmpty);
    console.log('  adminTab:', adminTab);
    console.log('  adminContent:', adminContent);
    
    // Проверяем видимость
    if (moderationGrid) {
        console.log('📏 Размеры moderationGrid:', {
            width: moderationGrid.offsetWidth,
            height: moderationGrid.offsetHeight,
            display: window.getComputedStyle(moderationGrid).display,
            visibility: window.getComputedStyle(moderationGrid).visibility
        });
        console.log('📄 Содержимое moderationGrid:', moderationGrid.innerHTML);
    }
    
    // Проверяем OffersManager
    console.log('🛠️ OffersManager:', window.offersManager);
    
    // Проверяем получение пользователя
    console.log('👤 User ID:', window.getTelegramUserId?.());
    
    // Тестируем API напрямую
    console.log('🌐 Тестируем API...');
    fetch('/api/offers_moderation/offers?status=pending', {
        headers: {
            'X-Telegram-User-Id': '373086959'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('📡 API ответ:', data);
        if (data.success && data.data.offers.length > 0) {
            console.log('✅ API работает, офферов:', data.data.offers.length);
            
            // Пробуем рендерить карточки вручную
            if (moderationGrid && window.offersManager) {
                console.log('🎨 Пробуем рендерить карточки...');
                window.offersManager.renderModerationOffers(data.data.offers, moderationGrid);
            }
        } else {
            console.log('❌ API не вернул офферы');
        }
    })
    .catch(error => console.error('❌ API ошибка:', error));
}

// Добавляем функцию в глобальную область
window.debugModeration = debugModeration;

console.log('✅ Функция отладки загружена. Запустите debugModeration() в консоли.');