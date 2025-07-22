// Финальный тест для выявления проблемы с отображением
// Запустите в консоли: runFinalTest()

function runFinalTest() {
    console.log('🚀 === ФИНАЛЬНЫЙ ТЕСТ АДМИН-ПАНЕЛИ === 🚀');
    
    // 1. Проверяем вкладку админ-модерации
    const adminTab = document.getElementById('admin-moderation');
    console.log('🏷️ Вкладка admin-moderation:', adminTab);
    
    if (adminTab) {
        const tabStyles = window.getComputedStyle(adminTab);
        console.log('🎨 Стили вкладки:', {
            display: tabStyles.display,
            visibility: tabStyles.visibility,
            opacity: tabStyles.opacity,
            position: tabStyles.position,
            zIndex: tabStyles.zIndex,
            height: tabStyles.height,
            hasActiveClass: adminTab.classList.contains('active')
        });
        
        // Принудительно активируем вкладку
        adminTab.style.display = 'block';
        adminTab.style.visibility = 'visible';
        adminTab.style.opacity = '1';
        adminTab.classList.add('active');
        console.log('✅ Вкладка принудительно активирована');
    }
    
    // 2. Проверяем контейнер модерации
    const container = document.getElementById('moderationGrid');
    console.log('📦 Контейнер moderationGrid:', container);
    
    if (container) {
        console.log('📄 Содержимое контейнера (первые 200 символов):', container.innerHTML.substring(0, 200));
        
        const containerStyles = window.getComputedStyle(container);
        console.log('🎨 Стили контейнера:', {
            display: containerStyles.display,
            visibility: containerStyles.visibility,
            opacity: containerStyles.opacity,
            width: containerStyles.width,
            height: containerStyles.height,
            overflow: containerStyles.overflow
        });
        
        const rect = container.getBoundingClientRect();
        console.log('📐 Позиция контейнера:', {
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            isVisible: rect.height > 0 && rect.width > 0
        });
    }
    
    // 3. Проверяем карточки
    const cards = document.querySelectorAll('#moderationGrid .offer-card');
    console.log(`🎴 Найдено карточек: ${cards.length}`);
    
    cards.forEach((card, index) => {
        const cardStyles = window.getComputedStyle(card);
        const cardRect = card.getBoundingClientRect();
        
        console.log(`🎴 Карточка ${index + 1}:`, {
            display: cardStyles.display,
            visibility: cardStyles.visibility,
            opacity: cardStyles.opacity,
            width: cardRect.width,
            height: cardRect.height,
            background: cardStyles.backgroundColor,
            border: cardStyles.border,
            isVisible: cardRect.height > 0 && cardRect.width > 0
        });
        
        // Принудительно показываем карточку
        card.style.display = 'block !important';
        card.style.visibility = 'visible !important';
        card.style.opacity = '1 !important';
        card.style.background = '#ffffff !important';
        card.style.border = '2px solid #ff0000 !important';
        card.style.padding = '20px !important';
        card.style.margin = '10px 0 !important';
        card.style.minHeight = '100px !important';
    });
    
    // 4. Проверяем scroll положение
    console.log('📜 Scroll позиция:', {
        pageYOffset: window.pageYOffset,
        scrollTop: document.documentElement.scrollTop,
        containerTopFromViewport: container ? container.getBoundingClientRect().top : 'N/A'
    });
    
    // 5. Создаем тестовую карточку для сравнения
    const testDiv = document.createElement('div');
    testDiv.innerHTML = `
        <div style="background: yellow; border: 3px solid red; padding: 20px; margin: 20px; font-size: 18px; font-weight: bold;">
            🧪 ТЕСТОВАЯ КАРТОЧКА - ЕСЛИ ВЫ ВИДИТЕ ЭТО, ТО ПРОБЛЕМА НЕ В CSS
        </div>
    `;
    
    if (container) {
        container.appendChild(testDiv);
        console.log('✅ Тестовая карточка добавлена в контейнер');
    }
    
    // 6. Проверяем все родительские элементы контейнера
    if (container) {
        let parent = container.parentElement;
        let level = 1;
        console.log('👨‍👩‍👧‍👦 Проверка родительских элементов:');
        
        while (parent && level <= 5) {
            const parentStyles = window.getComputedStyle(parent);
            console.log(`  Уровень ${level}: ${parent.tagName}#${parent.id || 'no-id'}`, {
                display: parentStyles.display,
                visibility: parentStyles.visibility,
                opacity: parentStyles.opacity,
                overflow: parentStyles.overflow,
                height: parentStyles.height,
                maxHeight: parentStyles.maxHeight
            });
            
            parent = parent.parentElement;
            level++;
        }
    }
    
    console.log('🏁 Финальный тест завершен');
}

// Функция для принудительного скрола к контейнеру
function scrollToContainer() {
    const container = document.getElementById('moderationGrid');
    if (container) {
        container.scrollIntoView({ behavior: 'smooth', block: 'center' });
        console.log('📜 Скрол к контейнеру выполнен');
    }
}

window.runFinalTest = runFinalTest;
window.scrollToContainer = scrollToContainer;

console.log('✅ Финальные функции отладки готовы:');
console.log('  - runFinalTest() - полная диагностика');
console.log('  - scrollToContainer() - скрол к контейнеру');