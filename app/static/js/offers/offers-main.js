/**
 * offers-main.js
 * Главный файл для инициализации модульной системы офферов
 */

import { OffersManager } from './offers-manager.js';
import { ModalManager } from './offers-modals.js';

// Глобальные переменные
let offersManager = null;
let modalManager = null;

// Инициализация Telegram WebApp
if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
    console.log('📱 Telegram WebApp инициализирован');
}

// Основная функция инициализации
async function initializeOffers() {
    try {
        console.log('🚀 Инициализация модульной системы офферов...');
        
        // Создаем экземпляры менеджеров
        modalManager = new ModalManager();
        offersManager = new OffersManager();
        
        // Инициализируем
        await offersManager.init();
        
        // Делаем доступными глобально для совместимости
        window.offersManager = offersManager;
        window.modalManager = modalManager;
        
        // Экспортируем основные функции для обратной совместимости
        setupGlobalFunctions();
        
        console.log('✅ Модульная система офферов успешно инициализирована');
        
    } catch (error) {
        console.error('❌ Ошибка инициализации модульной системы офферов:', error);
        
        // Fallback на старую систему
        console.log('🔄 Попытка загрузить старую систему...');
        loadFallbackSystem();
    }
}

// Настройка глобальных функций для обратной совместимости
function setupGlobalFunctions() {
    // Переключение табов
    window.switchTab = (tabName) => {
        if (offersManager) {
            offersManager.switchTab(tabName);
        }
    };
    
    // Функции для работы с офферами
    window.showOfferDetails = (offerId) => {
        if (offersManager) {
            offersManager.showOfferDetails(offerId);
        }
    };
    
    window.editOffer = (offerId) => {
        if (offersManager) {
            offersManager.editOffer(offerId);
        }
    };
    
    window.showOfferStats = (offerId) => {
        if (offersManager) {
            offersManager.showOfferStats(offerId);
        }
    };
    
    window.deleteOffer = (offerId) => {
        if (offersManager) {
            offersManager.deleteOffer(offerId);
        }
    };
    
    // Функции для фильтров
    window.applyFindFilters = () => {
        if (offersManager) {
            offersManager.updateFilters();
        }
    };
    
    window.clearFindFilters = () => {
        if (offersManager) {
            offersManager.clearFilters();
        }
    };
    
    // Функции для модальных окон
    window.showChannelSelectionModal = async (offerId, offerTitle) => {
        if (offersManager) {
            await offersManager.showChannelSelection(offerId, offerTitle);
        }
    };
    
    window.closeModal = (modalId) => {
        if (modalManager) {
            modalManager.close(modalId);
        }
    };
    
    window.closeChannelModal = () => {
        if (modalManager) {
            modalManager.close('channel-selection-modal');
        }
    };
    
    // Функции для работы с предложениями
    window.acceptProposal = (proposalId, title) => {
        if (modalManager) {
            modalManager.createAcceptProposal(proposalId, title);
        }
    };
    
    window.rejectProposal = (proposalId, title) => {
        if (modalManager) {
            modalManager.createRejectProposal(proposalId, title);
        }
    };
    
    // Функции кампаний
    window.saveCampaignDraft = async () => {
        if (offersManager) {
            // Логика сохранения черновика кампании
            console.log('💾 Сохранение черновика кампании...');
        }
    };
    
    // Функция назад
    window.goBack = () => {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = '/';
        }
    };
}

// Резервная система (старый код)
function loadFallbackSystem() {
    console.log('📄 Загружаем резервную систему...');
    
    // Базовые функции переключения табов
    window.switchTab = function(tabName) {
        console.log(`🔄 Переключение на вкладку: ${tabName}`);
        
        document.querySelectorAll('.tabs-nav a').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tabs-content').forEach(content => content.classList.remove('active'));
        
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(tabName);
        
        if (activeTab) activeTab.classList.add('active');
        if (activeContent) activeContent.classList.add('active');
    };
    
    // Базовые функции фильтров
    window.applyFindFilters = function() {
        console.log('🔍 Применение фильтров поиска');
    };
    
    window.clearFindFilters = function() {
        console.log('🗑️ Очистка фильтров');
        ['findCategoryFilter', 'findBudgetMin', 'findBudgetMax', 'findMinSubscribers'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.value = '';
        });
    };
    
    // Заглушка для функций, которые требуют API
    window.showOfferDetails = function(offerId) {
        console.log('📝 Показ деталей оффера:', offerId);
        alert('Функция временно недоступна');
    };
    
    window.editOffer = function(offerId) {
        console.log('✏️ Редактирование оффера:', offerId);
        alert('Функция временно недоступна');
    };
    
    window.showOfferStats = function(offerId) {
        console.log('📊 Статистика оффера:', offerId);
        alert('Функция временно недоступна');
    };
    
    console.log('✅ Резервная система загружена');
}

// Обработчик загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM загружен, инициализируем систему офферов...');
    
    // Небольшая задержка для полной загрузки всех ресурсов
    setTimeout(() => {
        initializeOffers();
    }, 100);
});

// Обработчик ошибок модулей
window.addEventListener('error', (event) => {
    if (event.filename && event.filename.includes('offers/')) {
        console.error('❌ Ошибка в модуле офферов:', event.error);
        
        if (!window.offersManager && !window.offersBackupLoaded) {
            console.log('🔄 Переключаемся на резервную систему...');
            window.offersBackupLoaded = true;
            loadFallbackSystem();
        }
    }
});

// Экспорт для других модулей
export { initializeOffers, offersManager, modalManager };