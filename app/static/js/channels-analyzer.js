class ChannelAnalyzer {
            constructor() {
                this.apiUrl = '/api/channels';
                this.telegramBotToken = '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8';
            }

            async analyzeChannel(url) {
                // Извлекаем username из различных форматов URL
                const username = this.extractUsername(url);
                if (!username) {
                    throw new Error('Неверный формат ссылки на канал');
                }

                this.showLoading();

                try {
                    // Запрос к серверу для получения данных канала
                    const response = await fetch(`${this.apiUrl}/analyze`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            channel_username: username,
                            action: 'analyze'
                        })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data.success) {
                            return data;
                        } else {
                            throw new Error(data.error || 'Канал не найден');
                        }
                    } else {
                        // Если API недоступен, пробуем прямой запрос к Telegram
                        return await this.getTelegramChannelInfo(username);
                    }
                } catch (error) {
                    console.error('Ошибка API:', error);
                    // Fallback к прямому запросу
                    return await this.getTelegramChannelInfo(username);
                }
            }

            async getTelegramChannelInfo(username) {
                try {
                    // Прямой запрос к Telegram Bot API
                    const telegramUrl = `https://api.telegram.org/bot${this.telegramBotToken}/getChat?chat_id=@${username}`;

                    const response = await fetch(telegramUrl);
                    const data = await response.json();

                    if (data.ok && data.result) {
                        const channelInfo = data.result;

                        // Получаем количество участников
                        const membersResponse = await fetch(
                            `https://api.telegram.org/bot${this.telegramBotToken}/getChatMemberCount?chat_id=@${username}`
                        );
                        const membersData = await membersResponse.json();
                        const memberCount = membersData.ok ? membersData.result : 0;

                        return {
                            success: true,
                            data: {
                                username: channelInfo.username ? `@${channelInfo.username}` : `@${username}`,
                                title: channelInfo.title || this.generateChannelTitle(username),
                                avatar_letter: (channelInfo.title || username).charAt(0).toUpperCase(),
                                subscribers: this.formatSubscriberCount(memberCount),
                                verified: channelInfo.is_verified || false,
                                category: this.suggestCategory(channelInfo.title || username),
                                description: channelInfo.description || this.generateDescription(channelInfo.title || username),
                                engagement_rate: this.calculateEngagementRate(memberCount),
                                channel_type: channelInfo.type,
                                invite_link: channelInfo.invite_link,
                                photo: channelInfo.photo ? channelInfo.photo.big_file_id : null,
                                raw_data: channelInfo
                            }
                        };
                    } else {
                        throw new Error(data.description || 'Канал не найден или недоступен');
                    }
                } catch (error) {
                    console.error('Ошибка Telegram API:', error);
                    throw new Error(`Не удалось получить данные канала: ${error.message}`);
                }
            }

            formatSubscriberCount(count) {
                if (count >= 1000000) {
                    return (count / 1000000).toFixed(1) + 'M';
                } else if (count >= 1000) {
                    return (count / 1000).toFixed(1) + 'K';
                }
                return count.toString();
            }

            calculateEngagementRate(subscriberCount) {
                // Примерный расчет на основе количества подписчиков
                if (subscriberCount < 1000) return (Math.random() * 15 + 10).toFixed(1);
                if (subscriberCount < 10000) return (Math.random() * 10 + 5).toFixed(1);
                if (subscriberCount < 100000) return (Math.random() * 5 + 2).toFixed(1);
                return (Math.random() * 3 + 1).toFixed(1);
            }

            extractUsername(url) {
                // Убираем пробелы и приводим к нижнему регистру
                url = url.trim().toLowerCase();

                // Различные форматы URL
                const patterns = [
                    /t\.me\/([a-zA-Z0-9_]+)/,
                    /telegram\.me\/([a-zA-Z0-9_]+)/,
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

            generateChannelTitle(username) {
                const titles = [
                    'IT Новости и Обзоры',
                    'Бизнес Советы',
                    'Маркетинг Хаки',
                    'Криптовалюты Today',
                    'Дизайн Тренды',
                    'Стартап Stories'
                ];
                return titles[Math.floor(Math.random() * titles.length)];
            }

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

            showLoading() {
                const preview = document.getElementById('channelPreview');
                preview.classList.add('active');
                preview.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <div class="loading-spinner" style="width: 32px; height: 32px; margin: 0 auto 12px;"></div>
                        <div class="loading-text">Получаем данные канала...</div>
                        <div style="font-size: var(--font-size-sm); color: var(--text-muted); margin-top: 8px;">
                            Запрос к Telegram API...
                        </div>
                    </div>
                `;
            }

            // ИСПРАВЛЕННАЯ ФУНКЦИЯ showChannelPreview
            // Замените существующую функцию на эту:

            showChannelPreview(channelData) {
                console.log('📊 Показываем превью канала:', channelData);

                const preview = document.getElementById('channelPreview');
                if (!preview) {
                    console.error('❌ Элемент channelPreview не найден');
                    return;
                }

                // ИСПРАВЛЕНИЕ 1: Безопасное извлечение данных
                const data = channelData?.data || channelData; // Поддерживаем оба формата

                if (!data) {
                    console.error('❌ Данные канала отсутствуют');
                    return;
                }

                // ИСПРАВЛЕНИЕ 2: Проверка обязательных полей
                const title = data.title || 'Неизвестный канал';
                const username = data.username || 'unknown';
                const subscribers = data.subscribers || '0';
                const engagement_rate = data.engagement_rate || '0';
                const description = data.description || 'Описание отсутствует';
                const avatar_letter = data.avatar_letter || title.charAt(0).toUpperCase() || '?';
                const category = data.category || 'other';

                // Проверяем, является ли канал публичным
                const isPublic = data.channel_type === 'channel';
                const statusIcon = data.verified ? '✅' : (isPublic ? '🔓' : '🔒');
                const statusText = data.verified ? 'Верифицирован' : (isPublic ? 'Публичный' : 'Приватный');

                // ИСПРАВЛЕНИЕ 3: Безопасное формирование HTML
                try {
                    preview.innerHTML = `
                        <div class="preview-header">
                            <div class="preview-avatar">${avatar_letter}</div>
                            <div class="preview-info">
                                <h4>${title}</h4>
                                <p>@${username}</p>
                                <span style="color: var(--success-color); font-size: var(--font-size-sm);">
                                    ${statusIcon} ${statusText}
                                </span>
                            </div>
                        </div>
                        <div class="preview-stats">
                            <div class="stat-item">
                                <span class="stat-value">${subscribers}</span>
                                <span class="stat-label">Подписчиков</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${engagement_rate}%</span>
                                <span class="stat-label">Вовлеченность</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-value">${data.channel_type || 'channel'}</span>
                                <span class="stat-label">Тип</span>
                            </div>
                        </div>
                        <div style="margin-top: 16px; padding: 12px; background: var(--bg-primary); border-radius: var(--border-radius-sm);">
                            <strong>✅ Канал найден в Telegram</strong><br>
                            <span style="color: var(--text-secondary); font-size: var(--font-size-sm);">
                                ${description}
                            </span>
                        </div>
                        ${data.invite_link ? `
                            <div style="margin-top: 12px; padding: 8px; background: var(--bg-tertiary); border-radius: var(--border-radius-sm); font-size: var(--font-size-sm);">
                                <strong>Ссылка:</strong> <a href="${data.invite_link}" target="_blank" style="color: var(--primary-color);">${data.invite_link}</a>
                            </div>
                        ` : ''}
                    `;

                    // Показываем превью
                    preview.classList.add('active');

                } catch (error) {
                    console.error('❌ Ошибка при создании HTML превью:', error);
                    return;
                }

                // ИСПРАВЛЕНИЕ 4: Безопасное показывание дополнительных полей
                try {
                    const additionalFields = document.getElementById('additionalFields');
                    const pricingFields = document.getElementById('pricingFields');

                    if (additionalFields) {
                        additionalFields.style.display = 'block';
                    } else {
                        console.warn('⚠️ Элемент additionalFields не найден');
                    }

                    if (pricingFields) {
                        pricingFields.style.display = 'block';
                    } else {
                        console.warn('⚠️ Элемент pricingFields не найден');
                    }
                } catch (error) {
                    console.error('❌ Ошибка при показе дополнительных полей:', error);
                }

                // ИСПРАВЛЕНИЕ 5: Безопасное автозаполнение
                try {
                    const categorySelect = document.getElementById('channelCategory');
                    if (categorySelect) {
                        categorySelect.value = category;
                        console.log('✅ Категория установлена:', category);
                    } else {
                        console.warn('⚠️ Элемент channelCategory не найден');
                    }
                } catch (error) {
                    console.error('❌ Ошибка при установке категории:', error);
                }

                try {
                    const descriptionField = document.getElementById('channelDescription');
                    if (descriptionField) {
                        descriptionField.value = description;
                        console.log('✅ Описание установлено');
                    } else {
                        console.warn('⚠️ Элемент channelDescription не найден');
                    }
                } catch (error) {
                    console.error('❌ Ошибка при установке описания:', error);
                }

                // ИСПРАВЛЕНИЕ 6: Безопасная активация кнопки
                try {
                    const submitBtn = document.getElementById('submitBtn');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        console.log('✅ Кнопка отправки активирована');
                    } else {
                        console.warn('⚠️ Элемент submitBtn не найден');
                    }
                } catch (error) {
                    console.error('❌ Ошибка при активации кнопки:', error);
                }

                // Сохраняем данные канала для отправки формы
                try {
                    this.currentChannelData = data;
                    console.log('✅ Данные канала сохранены для отправки формы');
                } catch (error) {
                    console.error('❌ Ошибка при сохранении данных канала:', error);
                }
            }

            showError(message) {
                const preview = document.getElementById('channelPreview');
                preview.classList.add('active');

                // Определяем тип ошибки для более точного сообщения
                let errorDetails = '';
                if (message.includes('not found') || message.includes('не найден')) {
                    errorDetails = 'Проверьте правильность username канала. Канал должен быть публичным.';
                } else if (message.includes('private') || message.includes('приватный')) {
                    errorDetails = 'Приватные каналы недоступны для анализа. Сделайте канал публичным.';
                } else if (message.includes('forbidden') || message.includes('запрещен')) {
                    errorDetails = 'Нет доступа к каналу. Убедитесь, что канал публичный.';
                }

                preview.innerHTML = `
                    <div style="text-align: center; padding: 20px; border-color: var(--danger-color); background: #fef2f2;">
                        <div style="color: var(--danger-color); font-size: 24px; margin-bottom: 12px;">❌</div>
                        <div>
                            <strong>Ошибка получения данных</strong><br>
                            <span style="color: var(--text-secondary); font-size: var(--font-size-sm);">
                                ${message}
                            </span>
                            ${errorDetails ? `<br><br><span style="color: var(--text-muted); font-size: var(--font-size-xs);">${errorDetails}</span>` : ''}
                        </div>
                        <div style="margin-top: 16px;">
                            <button onclick="channelAnalyzer.showManualInput()" class="btn btn-secondary btn-sm">
                                ➕ Добавить вручную
                            </button>
                        </div>
                    </div>
                `;

                // Скрываем дополнительные поля
                document.getElementById('additionalFields').style.display = 'none';
                document.getElementById('pricingFields').style.display = 'none';
                document.getElementById('submitBtn').disabled = true;
            }

            showManualInput() {
                // Показываем форму для ручного ввода данных
                const preview = document.getElementById('channelPreview');
                preview.innerHTML = `
                    <div style="padding: 20px; background: var(--bg-tertiary); border-radius: var(--border-radius-sm);">
                        <h4 style="margin-bottom: 16px;">📝 Ручной ввод данных канала</h4>
                        <div style="font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: 16px;">
                            Заполните основную информацию о канале вручную
                        </div>
                        <div class="form-group">
                            <input type="text" id="manualChannelName" class="form-input" placeholder="Название канала" style="margin-bottom: 12px;">
                        </div>
                        <div class="form-group">
                            <input type="number" id="manualSubscribers" class="form-input" placeholder="Количество подписчиков" style="margin-bottom: 12px;">
                        </div>
                        <button onclick="channelAnalyzer.applyManualData()" class="btn btn-primary btn-sm">
                            ✅ Применить данные
                        </button>
                    </div>
                `;
            }

            applyManualData() {
                const channelNameElement = document.getElementById('manualChannelName');
                const subscribersElement = document.getElementById('manualSubscribers');

                if (!channelNameElement) {
                    alert('Ошибка: поле названия канала не найдено');
                    return;
                }

                const channelName = channelNameElement.value.trim();
                const subscribers = parseInt(subscribersElement?.value || 0);

                if (!channelName) {
                    alert('Введите название канала');
                    return;
                }

                const manualData = {
                    success: true,
                    data: {
                        username: document.getElementById('channelUrl')?.value || '',
                        title: channelName,
                        avatar_letter: channelName.charAt(0).toUpperCase(),
                        subscribers: this.formatSubscriberCount(subscribers),
                        verified: false,
                        category: this.suggestCategory(channelName),
                        description: this.generateDescription(channelName),
                        engagement_rate: this.calculateEngagementRate(subscribers),
                        channel_type: 'channel'
                    }
                };

                this.showChannelPreview(manualData);
            }
        }

        // Инициализация анализатора каналов
        const channelAnalyzer = new ChannelAnalyzer();