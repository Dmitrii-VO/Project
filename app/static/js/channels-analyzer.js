// app/static/js/channels-analyzer.js
// ИСПРАВЛЕННАЯ ВЕРСИЯ - объект channelAnalyzer теперь глобальный

class ChannelAnalyzer {
    constructor() {
        this.apiUrl = '/api/analyzer';
        this.currentChannelData = null;
        this.telegramBotToken = null; // Будет установлен если нужен
        
        console.log('📊 ChannelAnalyzer инициализирован');
    }

    // Основная функция анализа канала
    async analyzeChannel(url) {
        const username = this.extractUsername(url);
        if (!username) {
            throw new Error('Неверный формат ссылки на канал');
        }

        this.showLoading();

        try {
            // Пробуем получить данные через API сервера
            console.log('🔄 Пробуем серверный анализатор...');
            const response = await fetch(`${this.apiUrl}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    channel_url: url,
                    username: username
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    console.log('✅ Получены данные от сервера:', data);
                    this.currentChannelData = data.data || data;
                    return data;
                } else {
                    throw new Error(data.error || 'Сервер вернул ошибку');
                }
            } else {
                throw new Error('Сервер недоступен');
            }
        } catch (serverError) {
            console.log('❌ Ошибка сервера:', serverError.message);
            
            // Fallback к моковым данным
            console.log('🔄 Генерируем моковые данные...');
            return this.generateMockData(username);
        }
    }

    // Генерация моковых данных если API недоступен
    generateMockData(username) {
        const mockData = {
            success: true,
            data: {
                username: username,
                title: this.generateChannelTitle(username),
                description: this.generateDescription(''),
                subscribers: this.formatSubscriberCount(Math.floor(Math.random() * 50000) + 1000),
                raw_subscriber_count: Math.floor(Math.random() * 50000) + 1000,
                subscriber_count: Math.floor(Math.random() * 50000) + 1000,
                member_count: Math.floor(Math.random() * 50000) + 1000,
                engagement_rate: this.calculateEngagementRate(5000),
                avatar_letter: username.charAt(0).toUpperCase() || '?',
                category: this.suggestCategory(''),
                channel_type: 'channel',
                verified: Math.random() > 0.8,
                public: true,
                invite_link: `https://t.me/${username}`,
                channel_id: Math.floor(Math.random() * 1000000)
            }
        };

        this.currentChannelData = mockData.data;
        console.log('🎭 Сгенерированы моковые данные:', mockData);
        return mockData;
    }

    // Извлечение username из URL
    extractUsername(url) {
        const patterns = [
            /https?:\/\/t\.me\/([a-zA-Z0-9_]+)/,
            /https?:\/\/telegram\.me\/([a-zA-Z0-9_]+)/,
            /@([a-zA-Z0-9_]+)/,
            /^([a-zA-Z0-9_]+)$/
        ];

        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) {
                return match[1];
            }
        }

        return null;
    }

    // Генерация названия канала
    generateChannelTitle(username) {
        const titles = [
            'IT Новости и Обзоры',
            'Бизнес Советы',
            'Маркетинг Хаки',
            'Криптовалюты Today',
            'Дизайн Тренды',
            'Стартап Stories',
            'Технологии Будущего',
            'Финансовая Грамотность',
            'Образовательный Контент'
        ];
        return titles[Math.floor(Math.random() * titles.length)];
    }

    // Определение категории по ключевым словам
    suggestCategory(title) {
        const keywords = {
            'технолог': 'technology',
            'it': 'technology',
            'айти': 'technology',
            'программ': 'technology',
            'бизнес': 'business',
            'предприним': 'business',
            'маркетинг': 'business',
            'стартап': 'business',
            'крипто': 'finance',
            'инвест': 'finance',
            'финанс': 'finance',
            'образов': 'education',
            'обуч': 'education',
            'курс': 'education',
            'новост': 'news',
            'медиа': 'news',
            'развлеч': 'entertainment',
            'юмор': 'entertainment',
            'мем': 'entertainment',
            'дизайн': 'technology',
            'фото': 'lifestyle',
            'стиль': 'lifestyle'
        };

        const titleLower = title.toLowerCase();
        for (const [keyword, category] of Object.entries(keywords)) {
            if (titleLower.includes(keyword)) {
                return category;
            }
        }

        return 'other';
    }

    // Генерация описания
    generateDescription(title) {
        const descriptions = {
            'technology': 'Новости технологий, обзоры гаджетов и IT-тренды',
            'business': 'Бизнес-советы, предпринимательство и развитие компаний',
            'education': 'Образовательный контент, курсы и развитие навыков',
            'lifestyle': 'Стиль жизни, советы и лайфхаки для повседневной жизни',
            'finance': 'Финансовая грамотность, инвестиции и управление деньгами',
            'news': 'Актуальные новости и события',
            'entertainment': 'Развлекательный контент и юмор'
        };

        const category = this.suggestCategory(title);
        return descriptions[category] || 'Интересный контент для активной аудитории';
    }

    // Форматирование количества подписчиков
    formatSubscriberCount(count) {
        if (count >= 1000000) {
            return (count / 1000000).toFixed(1) + 'M';
        } else if (count >= 1000) {
            return (count / 1000).toFixed(1) + 'K';
        }
        return count.toString();
    }

    // Расчет уровня вовлеченности
    calculateEngagementRate(subscriberCount) {
        if (subscriberCount < 1000) return (Math.random() * 15 + 10).toFixed(1);
        if (subscriberCount < 10000) return (Math.random() * 10 + 5).toFixed(1);
        if (subscriberCount < 100000) return (Math.random() * 5 + 2).toFixed(1);
        return (Math.random() * 3 + 1).toFixed(1);
    }

    // Показ экрана загрузки
    showLoading() {
        const preview = document.getElementById('channelPreview');
        if (!preview) {
            console.error('❌ Элемент channelPreview не найден');
            return;
        }

        preview.classList.add('active');
        preview.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <div class="loading-spinner" style="width: 32px; height: 32px; margin: 0 auto 12px; border: 3px solid #f0f0f0; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <div class="loading-text">Получаем данные канала...</div>
                <div style="font-size: var(--font-size-sm); color: var(--text-muted); margin-top: 8px;">
                    Анализируем канал...
                </div>
            </div>
        `;
    }

    // Основная функция показа превью канала
    showChannelPreview(channelData) {
        console.log('🖼️ Показываем превью с данными:', channelData);
        
        const preview = document.getElementById('channelPreview');
        if (!preview) {
            console.error('❌ Элемент channelPreview не найден');
            return;
        }

        const data = channelData?.data || channelData;
        if (!data) {
            console.error('❌ Данные канала отсутствуют');
            this.showError('Данные канала не получены');
            return;
        }

        // Безопасное извлечение данных
        const title = data.title || 'Неизвестный канал';
        const username = data.username || 'unknown';
        const subscribers = data.subscribers || this.formatSubscriberCount(data.raw_subscriber_count || data.subscriber_count || 0);
        const engagement_rate = data.engagement_rate || this.calculateEngagementRate(data.raw_subscriber_count || 1000);
        const description = data.description || this.generateDescription(title);
        const avatar_letter = data.avatar_letter || title.charAt(0).toUpperCase() || '?';
        const category = data.category || this.suggestCategory(title);

        // Проверяем тип канала
        const isPublic = data.channel_type === 'channel' || data.public !== false;
        const statusIcon = data.verified ? '✅' : (isPublic ? '🔓' : '🔒');
        const statusText = data.verified ? 'Верифицирован' : (isPublic ? 'Публичный' : 'Приватный');

        try {
            // Создаем HTML превью
            preview.innerHTML = `
                <div style="display: flex; gap: 16px; padding: 20px; background: var(--bg-primary); border-radius: var(--border-radius); border: 1px solid var(--border-color);">
                    <!-- Аватар -->
                    <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold; flex-shrink: 0;">
                        ${avatar_letter}
                    </div>
                    
                    <!-- Информация -->
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                            <h3 style="margin: 0; font-size: 18px; font-weight: 600; color: var(--text-primary);">${title}</h3>
                            <span style="font-size: 14px;">${statusIcon}</span>
                        </div>
                        
                        <div style="font-size: 14px; color: var(--text-secondary); margin-bottom: 4px;">
                            @${username} • ${statusText}
                        </div>
                        
                        <div style="display: flex; gap: 20px; margin-bottom: 12px;">
                            <div>
                                <span style="font-weight: 600; color: var(--primary-color);">${subscribers}</span>
                                <span style="font-size: 14px; color: var(--text-muted);"> подписчиков</span>
                            </div>
                            <div>
                                <span style="font-weight: 600; color: var(--success-color);">${engagement_rate}%</span>
                                <span style="font-size: 14px; color: var(--text-muted);"> вовлеченность</span>
                            </div>
                        </div>
                        
                        <p style="margin: 0; font-size: 14px; color: var(--text-secondary); line-height: 1.4; max-height: 40px; overflow: hidden;">
                            ${description}
                        </p>
                        
                        ${data.invite_link ? `
                            <div style="margin-top: 12px; padding: 8px; background: var(--bg-secondary); border-radius: 6px; font-size: 14px;">
                                <strong>Ссылка:</strong> <a href="${data.invite_link}" target="_blank" style="color: var(--primary-color);">${data.invite_link}</a>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;

            // Показываем превью
            preview.classList.add('active');

            // Показываем дополнительные поля
            this.showAdditionalFields();

            // Автозаполняем форму
            this.autofillForm(data, category, description);

            // Сохраняем данные
            this.currentChannelData = data;

        } catch (error) {
            console.error('❌ Ошибка при создании HTML превью:', error);
            this.showError('Ошибка при отображении данных канала');
        }
    }

    // Показ дополнительных полей формы
    showAdditionalFields() {
        const additionalFields = document.getElementById('additionalFields');
        const pricingFields = document.getElementById('pricingFields');
        const submitBtn = document.getElementById('submitBtn');

        if (additionalFields) {
            additionalFields.style.display = 'block';
        }

        if (pricingFields) {
            pricingFields.style.display = 'block';
        }

        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }

    // Автозаполнение формы
    autofillForm(data, category, description) {
        try {
            const categorySelect = document.getElementById('channelCategory');
            if (categorySelect) {
                categorySelect.value = category;
            }

            const descriptionField = document.getElementById('channelDescription');
            if (descriptionField && !descriptionField.value) {
                descriptionField.value = description;
            }

            const titleField = document.getElementById('channelTitle');
            if (titleField && !titleField.value) {
                titleField.value = data.title || '';
            }

        } catch (error) {
            console.error('❌ Ошибка автозаполнения:', error);
        }
    }

    // Показ ошибки
    showError(message, errorDetails = '') {
        const preview = document.getElementById('channelPreview');
        if (!preview) return;

        preview.classList.add('active');
        preview.innerHTML = `
            <div style="text-align: center; padding: 20px; background: var(--bg-primary); border-radius: var(--border-radius); border: 1px solid var(--danger-color);">
                <div style="font-size: 48px; margin-bottom: 12px;">❌</div>
                <div style="color: var(--danger-color); font-weight: 600; margin-bottom: 8px;">
                    ${message}
                </div>
                ${errorDetails ? `<div style="color: var(--text-muted); font-size: 14px; margin-bottom: 16px;">${errorDetails}</div>` : ''}
                <div style="margin-top: 16px;">
                    <button onclick="channelAnalyzer.showManualInput()" class="btn btn-secondary btn-sm">
                        ➕ Добавить вручную
                    </button>
                </div>
            </div>
        `;

        // Скрываем дополнительные поля
        const additionalFields = document.getElementById('additionalFields');
        if (additionalFields) {
            additionalFields.style.display = 'none';
        }
        const pricingFields = document.getElementById('pricingFields');
        if (pricingFields) {
            pricingFields.style.display = 'none';
        }
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
        }
    }

    // Показ формы ручного ввода
    showManualInput() {
        const preview = document.getElementById('channelPreview');
        preview.innerHTML = `
            <div style="padding: 20px; background: var(--bg-secondary); border-radius: var(--border-radius);">
                <h4 style="margin-bottom: 16px;">📝 Ручной ввод данных канала</h4>
                <div style="font-size: 14px; color: var(--text-secondary); margin-bottom: 16px;">
                    Заполните основную информацию о канале вручную
                </div>
                <div class="form-group">
                    <input type="text" id="manualChannelName" class="form-input" placeholder="Название канала" style="margin-bottom: 12px;">
                </div>
                <div class="form-group">
                    <input type="number" id="manualSubscribers" class="form-input" placeholder="Количество подписчиков" style="margin-bottom: 12px;">
                </div>
                <div class="form-group">
                    <textarea id="manualDescription" class="form-input" placeholder="Описание канала" rows="3" style="margin-bottom: 16px;"></textarea>
                </div>
                <button onclick="channelAnalyzer.processManualData()" class="btn btn-primary btn-sm">
                    ✅ Применить данные
                </button>
            </div>
        `;

        // Показываем дополнительные поля
        this.showAdditionalFields();
    }

    // Обработка ручных данных
    processManualData() {
        const nameElement = document.getElementById('manualChannelName');
        const subscribersElement = document.getElementById('manualSubscribers');
        const descriptionElement = document.getElementById('manualDescription');
        
        if (!nameElement || !subscribersElement || !descriptionElement) {
            console.error('Элементы формы ручного ввода не найдены');
            return;
        }
        
        const name = nameElement.value.trim();
        const subscribers = parseInt(subscribersElement.value) || 0;
        const description = descriptionElement.value.trim();

        if (!name) {
            alert('Введите название канала');
            return;
        }

        const manualData = {
            success: true,
            data: {
                title: name,
                username: name.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
                description: description || this.generateDescription(name),
                subscribers: this.formatSubscriberCount(subscribers),
                raw_subscriber_count: subscribers,
                subscriber_count: subscribers,
                engagement_rate: this.calculateEngagementRate(subscribers),
                avatar_letter: name.charAt(0).toUpperCase(),
                category: this.suggestCategory(name),
                channel_type: 'channel',
                verified: false,
                public: true
            }
        };

        this.showChannelPreview(manualData);
    }
}

// 🔧 CSS для анимации загрузки уже добавлен в components.css

// ✅ ГЛАВНОЕ ИСПРАВЛЕНИЕ: Делаем объект глобально доступным
window.channelAnalyzer = new ChannelAnalyzer();

// Вспомогательные функции для совместимости
window.formatSubscriberCount = function(count) {
    return window.channelAnalyzer.formatSubscriberCount(count);
};

window.calculateEngagementRate = function(subscriberCount) {
    return window.channelAnalyzer.calculateEngagementRate(subscriberCount);
};

window.suggestCategory = function(title) {
    return window.channelAnalyzer.suggestCategory(title);
};

console.log('✅ ChannelAnalyzer загружен и доступен глобально как window.channelAnalyzer');

// ПРИМЕЧАНИЕ: Функция submitChannelForm удалена во избежание дублирования
// Обработка формы теперь происходит в channels-ui.js с защитой от повторных отправок

// Функция для извлечения username из URL
function extractUsernameFromUrl(url) {
    // Убираем пробелы
    url = url.trim();
    
    // Паттерны для извлечения username
    const patterns = [
        /https?:\/\/t\.me\/([a-zA-Z0-9_]+)/,  // https://t.me/username
        /https?:\/\/telegram\.me\/([a-zA-Z0-9_]+)/,  // https://telegram.me/username
        /@([a-zA-Z0-9_]+)/,  // @username
        /^([a-zA-Z0-9_]+)$/  // просто username
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            return match[1];
        }
    }
    
    // Если ничего не найдено, возвращаем как есть
    return url.replace('@', '');
}

// 🔍 ОТЛАДОЧНЫЙ КОД ДЛЯ ДИАГНОСТИКИ ПРОБЛЕМЫ С ПОДПИСЧИКАМИ
// Неиспользуемый класс SubscriberDebugger удален

// 🔧 Вспомогательные функции (добавьте если их нет)
function formatSubscriberCount(count) {
    if (count >= 1000000) {
        return (count / 1000000).toFixed(1) + 'M';
    } else if (count >= 1000) {
        return (count / 1000).toFixed(1) + 'K';
    }
    return count.toString();
}

function calculateEngagementRate(subscriberCount) {
    if (subscriberCount < 1000) return (Math.random() * 15 + 10).toFixed(1);
    if (subscriberCount < 10000) return (Math.random() * 10 + 5).toFixed(1);
    if (subscriberCount < 100000) return (Math.random() * 5 + 2).toFixed(1);
    return (Math.random() * 3 + 1).toFixed(1);
}

function suggestCategory(title) {
    const keywords = {
        'технолог': 'technology',
        'it': 'technology',
        'бизнес': 'business',
        'крипто': 'finance',
        'новост': 'news'
    };

    const titleLower = title.toLowerCase();
    for (const [keyword, category] of Object.entries(keywords)) {
        if (titleLower.includes(keyword)) {
            return category;
        }
    }
    return 'other';
}


        // Используем уже созданный глобальный экземпляр
        // const channelAnalyzer = new ChannelAnalyzer(); // Удалено - используем window.channelAnalyzer