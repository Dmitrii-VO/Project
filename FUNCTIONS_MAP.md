# 🗺️ Карта функций проекта

Этот файл содержит информацию о расположении всех функций в проекте для удобной навигации.

## 📂 Структура файлов

### 🎯 Frontend - JavaScript

#### `/app/static/js/channels-core.js`
**Основные функции управления каналами**

- `getTelegramUser()` - Получение данных пользователя Telegram
- `loadUserChannels()` - Загрузка каналов пользователя
- `createChannelCard(channel)` - Создание карточки канала
- `showChannelEditModal(channelId)` - Открытие модального окна редактирования канала
- `loadChannelDataForEdit(channelId)` - Загрузка данных канала для редактирования
- `saveChannelChanges(channelId)` - Сохранение изменений канала
- `closeEditModal()` - Закрытие модального окна редактирования
- `confirmChannelDeletion(channelId)` - Подтверждение удаления канала (fallback)
- `deleteChannel(channelId)` - Удаление канала (fallback)
- `testDeleteChannel(channelId)` - Тестовая функция для прямого вызова API удаления
- `testDeleteButtonClick()` - Тестовая функция для проверки клика по кнопке удаления
- `refreshChannelStatistics(channelId)` - Обновление статистики канала
- `debugChannelData()` - Отладочная функция для проверки данных каналов

**Глобальные экспорты:**
```javascript
window.loadUserChannels = loadUserChannels;
window.testDeleteChannel = testDeleteChannel;
window.testDeleteButtonClick = testDeleteButtonClick;
window.confirmChannelDeletion = confirmChannelDeletion;
window.deleteChannel = deleteChannel;
window.closeEditModal = closeEditModal;
window.saveChannelChanges = saveChannelChanges;
```

#### `/app/static/js/channels-modals.js`
**Модальные окна и их обработчики**

- `showDeleteConfirmation(channelId, channelName, channelUsername)` - Показать модальное окно подтверждения удаления
- `closeDeleteModal()` - Закрыть модальное окно удаления
- `confirmChannelDeletionModal()` - Подтверждение удаления канала (основная функция)
- `testDeleteChannelModal(channelId)` - Тестовая функция для проверки удаления через модал
- `testFullDeleteProcess(channelId)` - Тестовая функция для полного процесса удаления
- `showVerificationModal(channelId, channelName, channelUsername)` - Показать модальное окно верификации
- `startVerification()` - Запуск процесса верификации
- `startChannelVerification(channelId)` - Запуск верификации конкретного канала
- `closeVerificationModalAndRefresh()` - Закрытие модального окна верификации с обновлением

**Глобальные переменные:**
```javascript
let verificationChannelData = null;
let channelToDelete = null;
```

**Глобальные экспорты:**
```javascript
window.closeDeleteModal = closeDeleteModal;
window.confirmChannelDeletionModal = confirmChannelDeletionModal;
window.testDeleteChannelModal = testDeleteChannelModal;
window.testFullDeleteProcess = testFullDeleteProcess;
window.showDeleteConfirmation = showDeleteConfirmation;
window.startVerification = startVerification;
window.startChannelVerification = startChannelVerification;
```

#### `/app/static/js/channels-ui.js`
**Интерфейс и UI элементы**

- `showLoadingState()` - Показать состояние загрузки
- `hideLoadingState()` - Скрыть состояние загрузки
- `showEmptyState()` - Показать пустое состояние
- `hideEmptyState()` - Скрыть пустое состояние
- `showChannelStats(channelId)` - Показать статистику канала
- `showChannelSettings(channelId)` - Показать настройки канала
- `editChannel(channelId)` - Редактировать канал

#### `/app/static/js/channels-forms.js`
**Формы и их обработка**

- `initChannelForms()` - Инициализация форм каналов
- `handleChannelSubmit(event)` - Обработка отправки формы канала
- `validateChannelForm(formData)` - Валидация формы канала

#### `/app/static/js/channels-analyzer.js`
**Анализ каналов**

- `ChannelAnalyzer()` - Класс для анализа каналов
- `analyzeChannel(username)` - Анализ канала по username
- `getChannelInfo(username)` - Получение информации о канале
- `validateChannelData(data)` - Валидация данных канала

#### `/app/static/js/utils.js`
**Утилиты**

- `getTelegramUserId()` - Получение ID пользователя Telegram
- `cacheTelegramUserId()` - Кэширование ID пользователя
- `clearTelegramUserIdCache()` - Очистка кэша ID пользователя
- `closeModal()` - Закрытие модального окна
- `initModalHandlers()` - Инициализация обработчиков модальных окон

### 🎯 Backend - Python

#### `/app/api/channels.py`
**API для работы с каналами**

- `get_channels()` - GET `/api/channels/` - Получение списка каналов
- `get_channel(channel_id)` - GET `/api/channels/<id>` - Получение канала по ID
- `delete_channel(channel_id)` - DELETE `/api/channels/<id>` - Удаление канала
- `update_channel(channel_id)` - PUT `/api/channels/<id>` - Обновление канала
- `get_channel_responses(channel_id)` - GET `/api/channels/<id>/responses` - Получение откликов канала
- `update_response_status(channel_id, response_id)` - PUT `/api/channels/<id>/responses/<id>` - Обновление статуса отклика
- `get_categories()` - GET `/api/channels/categories` - Получение категорий каналов
- `get_channels_stats()` - GET `/api/channels/stats` - Получение статистики каналов
- `analyze_channel()` - POST `/api/channels/analyze` - Анализ канала
- `get_my_channels()` - GET `/api/channels/my` - Получение каналов пользователя
- `update_channel_stats(channel_id)` - PUT/POST `/api/channels/<id>/update-stats` - Обновление статистики канала
- `add_channel()` - POST `/api/channels/` - Добавление нового канала
- `debug_channel(channel_id)` - GET `/api/channels/debug/<id>` - Отладочная информация о канале

**Вспомогательные функции:**
- `extract_username_from_url(url)` - Извлечение username из URL
- `get_db_connection()` - Получение соединения с базой данных
- `get_channel_offers_count(channel_id)` - Получение количества офферов канала
- `get_channel_posts_count(channel_id)` - Получение количества постов канала

#### `/app/api/offers.py`
**API для работы с офферами**

- `get_offers()` - GET `/api/offers/` - Получение списка офферов
- `create_offer()` - POST `/api/offers/` - Создание нового оффера
- `get_offer(offer_id)` - GET `/api/offers/<id>` - Получение оффера по ID
- `update_offer(offer_id)` - PUT `/api/offers/<id>` - Обновление оффера
- `delete_offer(offer_id)` - DELETE `/api/offers/<id>` - Удаление оффера

#### `/app/api/analytics.py`
**API для аналитики**

- `get_analytics_data()` - GET `/api/analytics/` - Получение данных аналитики
- `get_channel_analytics(channel_id)` - GET `/api/analytics/channels/<id>` - Аналитика канала
- `get_user_analytics()` - GET `/api/analytics/users/` - Аналитика пользователей

## 🔧 Функции удаления каналов

### Основной процесс удаления:

1. **Клик по кнопке редактирования** → `showChannelEditModal(channelId)` в `channels-core.js:273`
2. **Клик по кнопке удаления в модале** → Event listener в `channels-core.js:351`
3. **Открытие модала подтверждения** → `showDeleteConfirmation(channelId, channelName, channelUsername)` в `channels-modals.js:6`
4. **Клик по кнопке подтверждения** → Event listener в `channels-modals.js:74`
5. **Выполнение удаления** → `confirmChannelDeletionModal()` в `channels-modals.js:108`
6. **API запрос** → DELETE `/api/channels/<id>` в `channels.py:246`

### Тестовые функции:

- `testDeleteChannel(channelId)` - Прямой вызов API удаления
- `testDeleteChannelModal(channelId)` - Тест удаления через модал
- `testFullDeleteProcess(channelId)` - Полный тест процесса удаления

## 🏗️ Архитектура проекта

### Frontend архитектура:
- **channels-core.js** - Основная логика управления каналами
- **channels-modals.js** - Модальные окна и их обработчики  
- **channels-ui.js** - UI компоненты и интерфейс
- **channels-forms.js** - Обработка форм
- **channels-analyzer.js** - Анализ каналов
- **utils.js** - Общие утилиты

### Backend архитектура:
- **channels.py** - API для каналов
- **offers.py** - API для офферов
- **analytics.py** - API для аналитики
- **working_app.py** - Основное приложение Flask

## 🐛 Отладка

### Тестовые функции в консоли браузера:
```javascript
// Тест удаления канала
testDeleteChannel(channelId)

// Тест модального окна удаления
testDeleteChannelModal(channelId)

// Тест полного процесса удаления
testFullDeleteProcess(channelId)

// Тест клика по кнопке
testDeleteButtonClick()

// Проверка состояния
console.log('channelToDelete:', channelToDelete)
console.log('confirmDeleteBtn:', document.getElementById('confirmDeleteBtn'))
```

### Логи для отладки:
- `🔍` - Отладочная информация
- `✅` - Успешные операции
- `❌` - Ошибки
- `📊` - Статистика и данные
- `🔄` - Процессы и операции
- `🗑️` - Удаление
- `📝` - Редактирование

---

## 🔄 Недавние изменения

### 2025-07-19: Интеграция с Telegram API для получения реальных данных

#### ✅ Проблема решена: Теперь показываются актуальные данные каналов из Telegram API

#### Frontend изменения (`/app/static/js/offers.js`):
- **Добавлены функции для работы с реальными данными:**
  - `calculateEngagement(subscribers)` - расчет вовлеченности на основе размера аудитории
  - `getDemographicsForCategory(category)` - демография на основе категории канала

- **Обновлена функция `createChannelCard(channel, index)`:**
  - Убраны генераторы случайных тестовых данных
  - Всегда использует реальные данные: `channel.subscriber_count`, `channel.price_per_post`
  - Цены берутся из БД (указаны владельцами каналов)

#### Backend изменения (`/app/api/offers_management.py`):
- **Обновлена функция `get_recommended_channels(offer_id)`:**
  - Удалены fallback тестовые данные
  - Добавлены поля `price_per_post`, `owner_id` в SQL запрос
  - Добавлены вычисляемые поля (`engagement_rate`, `avg_views`, `ads_count`)
  - ✅ Восстановлена правильная фильтрация: показываются только чужие каналы (`AND c.owner_id != ?`)

#### Интеграция с Telegram API:
- **Функция `_get_real_channel_data()`** в `telegram_notifications.py`
- Получение актуального количества подписчиков через `getChatMemberCount`
- Обновление названий каналов через `getChat`
- Автоматическое обновление данных в БД

#### Актуальные данные каналов (из Telegram API):
- **@werwfvsd**: 3 подписчика, цена 3,500₽ (указана владельцем)
- **@vjissda**: 2 подписчика, цена 7,137₽ (указана владельцем)
- **@zxzxczcczc**: 1 подписчик, цена 8,500₽ (указана владельцем)

## 🔄 Изменения от 2025-07-19: Новая система предложений

### ✅ Проблема решена: Изменена система откликов на офферы

**Старая система:**
- Пользователи сами выбирали офферы и откликались на них
- Нужно было выбирать канал для отклика

**Новая система:**
- **Создатель оффера** выбирает каналы и отправляет предложения (`offer_proposals`)
- **Владелец канала** получает уведомления и отвечает на предложения

#### Frontend изменения:
- **Новая страница `/proposals`** - для управления предложениями владельцами каналов
  - Входящие предложения
  - Принятые предложения
  - Отклоненные предложения
  - Модальное окно ответа с сообщением рекламодателю

#### Backend изменения:
- **API endpoints в `proposals_management.py`:**
  - `GET /api/proposals/incoming` - получение входящих предложений
  - `POST /api/proposals/{id}/accept` - принятие предложения
  - `POST /api/proposals/{id}/reject` - отклонение предложения
  - `GET /api/proposals/{id}/details` - детали предложения

#### Обновления интерфейса:
- **Главная страница**: добавлена карточка "Предложения" 📬
- **offers-list.html**: кнопки "Откликнуться" заменены на "Предложения"
- **Модальные окна**: обновлены для нового процесса

#### Структура базы данных:
- Используется таблица `offer_proposals` с полями:
  - `status`: 'sent', 'accepted', 'rejected', 'expired', 'cancelled'
  - `response_message`: сообщение от владельца канала
  - `rejection_reason`: причина отклонения

**Последнее обновление:** 2025-07-19
**Версия:** 1.2