// Скрипт для отладки контейнера модерации
// Запустите в консоли браузера: debugContainer()

function debugContainer() {
    console.log('🔍 === ОТЛАДКА КОНТЕЙНЕРА === 🔍');
    
    const container = document.getElementById('moderationGrid');
    
    if (!container) {
        console.error('❌ Контейнер moderationGrid не найден!');
        return;
    }
    
    console.log('📋 Контейнер найден:', container);
    
    // Проверим содержимое
    console.log('📄 innerHTML длина:', container.innerHTML.length);
    console.log('📄 Первые 500 символов:', container.innerHTML.substring(0, 500));
    
    // Проверим CSS стили
    const styles = window.getComputedStyle(container);
    console.log('🎨 CSS стили контейнера:', {
        display: styles.display,
        visibility: styles.visibility,
        opacity: styles.opacity,
        width: styles.width,
        height: styles.height,
        position: styles.position,
        overflow: styles.overflow,
        zIndex: styles.zIndex
    });
    
    // Проверим родительские элементы
    let parent = container.parentElement;
    let level = 1;
    console.log('👨‍👩‍👧‍👦 Родительские элементы:');
    while (parent && level <= 5) {
        const parentStyles = window.getComputedStyle(parent);
        console.log(`  ${level}. ${parent.tagName}#${parent.id || 'no-id'}.${parent.className}`, {
            display: parentStyles.display,
            visibility: parentStyles.visibility,
            opacity: parentStyles.opacity
        });
        parent = parent.parentElement;
        level++;
    }
    
    // Проверим дочерние элементы
    console.log('👶 Дочерние элементы:');
    const children = container.children;
    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        const childStyles = window.getComputedStyle(child);
        console.log(`  ${i + 1}. ${child.tagName}.${child.className}`, {
            display: childStyles.display,
            visibility: childStyles.visibility,
            opacity: childStyles.opacity,
            width: childStyles.width,
            height: childStyles.height
        });
        
        // Проверим содержимое offers-list
        if (child.className.includes('offers-list')) {
            console.log('📋 Содержимое offers-list:');
            const offerCards = child.querySelectorAll('.offer-card');
            console.log(`  Найдено карточек: ${offerCards.length}`);
            
            offerCards.forEach((card, index) => {
                const cardStyles = window.getComputedStyle(card);
                console.log(`    Карточка ${index + 1}:`, {
                    display: cardStyles.display,
                    visibility: cardStyles.visibility,
                    opacity: cardStyles.opacity,
                    width: cardStyles.width,
                    height: cardStyles.height,
                    backgroundColor: cardStyles.backgroundColor,
                    border: cardStyles.border
                });
            });
        }
    }
    
    // Проверим viewport
    const rect = container.getBoundingClientRect();
    console.log('📐 Позиция относительно viewport:', {
        top: rect.top,
        left: rect.left,
        bottom: rect.bottom,
        right: rect.right,
        width: rect.width,
        height: rect.height,
        visible: rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth
    });
    
    // Проверим, видна ли вкладка модерации
    const adminTab = document.getElementById('admin-moderation');
    if (adminTab) {
        const tabStyles = window.getComputedStyle(adminTab);
        console.log('🏷️ Вкладка admin-moderation:', {
            display: tabStyles.display,
            visibility: tabStyles.visibility,
            hasActiveClass: adminTab.classList.contains('active')
        });
    }
    
    console.log('✅ Отладка завершена');
}

// Функция для принудительного показа карточек
function forceShowCards() {
    const container = document.getElementById('moderationGrid');
    if (!container) {
        console.error('❌ Контейнер не найден');
        return;
    }
    
    // Принудительно устанавливаем стили
    container.style.display = 'block';
    container.style.visibility = 'visible';
    container.style.opacity = '1';
    container.style.height = 'auto';
    container.style.minHeight = '200px';
    container.style.background = '#f0f0f0';
    container.style.border = '2px solid red';
    container.style.padding = '20px';
    
    console.log('🔧 Принудительно установлены стили для контейнера');
    
    // Проверим карточки
    const cards = container.querySelectorAll('.offer-card');
    cards.forEach((card, index) => {
        card.style.display = 'block';
        card.style.visibility = 'visible';
        card.style.opacity = '1';
        card.style.margin = '10px 0';
        card.style.background = 'white';
        card.style.border = '1px solid #333';
        card.style.padding = '15px';
        console.log(`🔧 Принудительно установлены стили для карточки ${index + 1}`);
    });
}

window.debugContainer = debugContainer;
window.forceShowCards = forceShowCards;

console.log('✅ Функции отладки загружены:');
console.log('  - debugContainer() - полная отладка контейнера');
console.log('  - forceShowCards() - принудительный показ карточек');