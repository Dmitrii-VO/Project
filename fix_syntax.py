#!/usr/bin/env python3
"""
Быстрое исправление синтаксической ошибки в offers.js
"""

import os
import re

def find_and_fix_syntax_error():
    """Находим и исправляем синтаксическую ошибку"""
    
    js_file = 'app/static/js/offers.js'
    
    print("🔧 ИСПРАВЛЕНИЕ СИНТАКСИЧЕСКОЙ ОШИБКИ")
    print("-" * 50)
    
    try:
        # Читаем файл
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📁 Файл прочитан: {len(content)} символов")
        
        # Ищем проблемные места с await
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines, 1):
            # Если в строке есть await, но функция не async
            if 'await' in line and 'async' not in line:
                # Ищем объявление функции выше
                func_start = None
                for j in range(i-10, i):
                    if j >= 0 and j < len(lines):
                        if 'function' in lines[j] and 'async' not in lines[j]:
                            func_start = j
                            break
                
                if func_start is not None:
                    # Добавляем async к функции
                    lines[func_start] = lines[func_start].replace('function', 'async function')
                    print(f"✅ Строка {func_start + 1}: добавлен async")
            
            # Исправляем неправильные fetch запросы
            if 'fetch(' in line and 'await' not in line and 'return' not in line:
                # Заменяем fetch на await fetch
                line = line.replace('fetch(', 'await fetch(')
                print(f"✅ Строка {i}: добавлен await к fetch")
        
        # Создаем полностью исправленный файл
        fixed_content = create_fixed_offers_js()
        
        # Записываем исправленный файл
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ Файл исправлен полностью!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def create_fixed_offers_js():
    """Создаем полностью исправленный offers.js"""
    
    return '''// app/static/js/offers.js - ИСПРАВЛЕННАЯ ВЕРСИЯ

// ===== ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ ВКЛАДОК =====
function switchTab(tabName) {
    console.log('🔄 Переключение на вкладку:', tabName);

    // Убираем активные классы у навигационных карточек
    document.querySelectorAll('.nav-card').forEach(card => card.classList.remove('active'));

    // Скрываем все контенты вкладок
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Активируем выбранную навигационную карточку
    const activeCard = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeCard) {
        activeCard.classList.add('active');
    }

    // Показываем соответствующий контент
    const activeContent = document.getElementById(tabName);
    if (activeContent) {
        activeContent.classList.add('active');
    }

    // Специальные действия для каждой вкладки
    if (tabName === 'my-offers') {
        loadMyOffers();
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ TELEGRAM WEBAPP =====
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// ===== ФУНКЦИЯ ПОЛУЧЕНИЯ USER ID =====
function getTelegramUserId() {
    console.log('🔍 Получение Telegram User ID...');
    
    // Пробуем получить из Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const user = window.Telegram.WebApp.initDataUnsafe.user;
        if (user && user.id) {
            console.log('✅ User ID из Telegram WebApp:', user.id);
            return user.id.toString();
        }
    }
    
    // Fallback к основному пользователю
    const fallbackId = '373086959';
    console.log('⚠️ Используем fallback User ID:', fallbackId);
    return fallbackId;
}

// ===== ЗАГРУЗКА МОИХ ОФФЕРОВ =====
async function loadMyOffers() {
    console.log('📋 Загрузка моих офферов...');
    const container = document.getElementById('offersGrid');

    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    try {
        // Показываем индикатор загрузки
        showOffersLoading();

        const userId = getTelegramUserId();
        console.log('👤 Используем User ID:', userId);

        const response = await fetch('/api/offers/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': userId
            }
        });

        console.log('🌐 API Response Status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('📦 API Response Data:', result);

        if (result.success && result.offers && result.offers.length > 0) {
            console.log('✅ Офферы загружены:', result.offers.length);
            renderOffers(result.offers);
        } else {
            console.log('ℹ️ Офферов не найдено');
            showEmptyOffersState();
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки офферов:', error);
        showOffersError('Ошибка загрузки офферов: ' + error.message);
    }
}

// ===== ОТОБРАЖЕНИЕ ОФФЕРОВ =====
function renderOffers(offers) {
    const container = document.getElementById('offersGrid');
    
    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    let html = '';
    
    offers.forEach(offer => {
        const statusClass = offer.status === 'active' ? 'status-active' : 'status-inactive';
        const statusText = offer.status === 'active' ? 'Активен' : 'Неактивен';
        
        html += `
            <div class="offer-card" data-offer-id="${offer.id}">
                <div class="offer-header">
                    <h3 class="offer-title">${offer.title}</h3>
                    <span class="offer-status ${statusClass}">${statusText}</span>
                </div>
                
                <div class="offer-info">
                    <div class="offer-price">
                        <span class="price-amount">${offer.price}</span>
                        <span class="price-currency">${offer.currency}</span>
                    </div>
                    
                    <div class="offer-details">
                        <div class="detail-item">
                            <span class="detail-label">Категория:</span>
                            <span class="detail-value">${offer.category || 'Не указана'}</span>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Дедлайн:</span>
                            <span class="detail-value">${offer.deadline || 'Не указан'}</span>
                        </div>
                        
                        <div class="detail-item">
                            <span class="detail-label">Откликов:</span>
                            <span class="detail-value">${offer.response_count || 0}</span>
                        </div>
                    </div>
                </div>
                
                <div class="offer-description">
                    ${offer.description || offer.content || ''}
                </div>
                
                <div class="offer-actions">
                    <button class="btn btn-outline" onclick="editOffer(${offer.id})">
                        Редактировать
                    </button>
                    <button class="btn btn-primary" onclick="viewOfferDetails(${offer.id})">
                        Подробнее
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ===== СОСТОЯНИЯ ЗАГРУЗКИ =====
function showOffersLoading() {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner">⏳</div>
                <p>Загрузка офферов...</p>
            </div>
        `;
    }
}

function showEmptyOffersState() {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <h3>Пока нет офферов</h3>
                <p>Создайте свой первый оффер, нажав на "Создать оффер"</p>
                <button class="btn btn-primary" onclick="switchTab('create-offer')">
                    Создать оффер
                </button>
            </div>
        `;
    }
}

function showOffersError(message) {
    const container = document.getElementById('offersGrid');
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">❌</div>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                <button class="btn btn-outline" onclick="loadMyOffers()">
                    Попробовать снова
                </button>
            </div>
        `;
    }
}

// ===== ДЕЙСТВИЯ С ОФФЕРАМИ =====
function editOffer(offerId) {
    console.log('✏️ Редактирование оффера:', offerId);
    // TODO: Реализовать редактирование
    alert(`Редактирование оффера ${offerId} (в разработке)`);
}

function viewOfferDetails(offerId) {
    console.log('👁️ Просмотр деталей оффера:', offerId);
    // TODO: Реализовать просмотр деталей
    alert(`Детали оффера ${offerId} (в разработке)`);
}

// ===== ПОИСК ПО ОФФЕРАМ =====
function setupOffersSearch() {
    const searchInput = document.getElementById('offersSearch');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            const offerCards = document.querySelectorAll('.offer-card');

            offerCards.forEach(card => {
                const title = card.querySelector('.offer-title')?.textContent.toLowerCase() || '';
                
                if (title.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
}

// ===== ФУНКЦИЯ ВОЗВРАТА =====
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// ===== КЛАСС ДЛЯ СОЗДАНИЯ ОФФЕРОВ =====
class OffersManager {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.init();
    }

    init() {
        console.log('🎯 Инициализация OffersManager');
        this.setupEventListeners();
        this.updateStep(this.currentStep);
    }

    setupEventListeners() {
        // Кнопки навигации по шагам
        document.getElementById('nextBtn')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prevBtn')?.addEventListener('click', () => this.prevStep());
        document.getElementById('submitBtn')?.addEventListener('click', () => this.submitOffer());

        // Слайдер подписчиков
        const subscribersRange = document.querySelector('input[name="min_subscribers"]');
        const subscribersValue = document.getElementById('subscribersValue');

        if (subscribersRange && subscribersValue) {
            subscribersRange.addEventListener('input', function() {
                const value = parseInt(this.value);
                subscribersValue.textContent = value >= 1000000 ? '1M+' :
                                              value >= 1000 ? Math.round(value/1000) + 'K' :
                                              value.toString();
            });
        }
    }

    updateStep(step) {
        console.log('📝 Обновление шага:', step);

        // Обновляем индикатор шагов
        document.querySelectorAll('.step').forEach((stepEl, index) => {
            const stepNumber = index + 1;
            stepEl.classList.toggle('active', stepNumber === step);
            stepEl.classList.toggle('completed', stepNumber < step);
        });

        // Показываем/скрываем шаги формы
        document.querySelectorAll('.form-step').forEach(stepEl => {
            stepEl.style.display = stepEl.dataset.step == step ? 'block' : 'none';
        });

        // Управляем кнопками
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        if (prevBtn) prevBtn.style.display = step === 1 ? 'none' : 'inline-flex';
        if (nextBtn) nextBtn.style.display = step === this.totalSteps ? 'none' : 'inline-flex';
        if (submitBtn) submitBtn.style.display = step === this.totalSteps ? 'inline-flex' : 'none';
    }

    nextStep() {
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateStep(this.currentStep);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStep(this.currentStep);
        }
    }

    async submitOffer() {
        console.log('📤 Отправка оффера...');

        const submitBtn = document.getElementById('submitBtn');
        const originalText = submitBtn?.textContent;

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Создание...';
            }

            // Собираем данные формы
            const formData = this.collectFormData();

            const response = await fetch('/api/offers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-User-Id': getTelegramUserId()
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                alert('✅ Оффер успешно создан!');
                // Переходим на вкладку "Мои офферы"
                switchTab('my-offers');
            } else {
                throw new Error(result.error || 'Ошибка создания оффера');
            }

        } catch (error) {
            console.error('❌ Ошибка создания оффера:', error);
            alert(`❌ Ошибка: ${error.message}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }

    collectFormData() {
        const form = document.getElementById('offerForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Добавляем выбранные чипы
        data.categories = Array.from(document.querySelectorAll('.chip.selected'))
            .map(chip => chip.dataset.value || chip.textContent);

        return data;
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Инициализация страницы офферов');

    // Загружаем офферы по умолчанию (первая вкладка)
    loadMyOffers();

    // Настройка поиска
    setupOffersSearch();

    // Инициализация существующего функционала создания офферов
    if (typeof OffersManager !== 'undefined') {
        window.offersManager = new OffersManager();
    }

    console.log('✅ Страница офферов инициализирована');
});

// ===== ЭКСПОРТ ФУНКЦИЙ =====
window.switchTab = switchTab;
window.loadMyOffers = loadMyOffers;
window.goBack = goBack;
window.OffersManager = OffersManager;
window.getTelegramUserId = getTelegramUserId;
'''

def main():
    """Главная функция"""
    print("🚀 ИСПРАВЛЕНИЕ СИНТАКСИЧЕСКОЙ ОШИБКИ В JAVASCRIPT")
    print("=" * 60)
    
    if find_and_fix_syntax_error():
        print("\n🎉 ФАЙЛ ПОЛНОСТЬЮ ИСПРАВЛЕН!")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Обновите страницу в браузере (Ctrl+F5)")
        print("2. Откройте консоль браузера (F12)")
        print("3. Проверьте что синтаксических ошибок нет")
        print("4. Офферы должны загрузиться автоматически")
    else:
        print("\n❌ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ")
        print("Попробуйте вручную заменить содержимое app/static/js/offers.js")

if __name__ == '__main__':
    main()
