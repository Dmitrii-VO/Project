# Тесты проекта

Эта папка содержит все тестовые файлы проекта, организованные по категориям.

## Структура тестов:

### 📁 Организация по папкам:

#### `/unit/` - Юнит-тесты отдельных компонентов
- `test_notification.py` - Тест системы уведомлений
- `test_offer_notification.py` - Тест уведомлений офферов
- `test_direct_notification.py` - Тест прямых уведомлений

#### `/integration/` - Интеграционные тесты API
- `test_delete_api.py` - Тест API удаления каналов
- `test_delete_direct.py` - Тест прямого удаления
- `test_get_channel.py` - Тест получения канала
- `test_analytics/` - Тесты аналитики

#### `/system/` - Системные E2E тесты
- `test_placement_completion.py` - Тест завершения размещения
- `test_post_published_command.py` - Тест команды /post_published
- `final_system_test.py` - Финальный тест системы размещения
- `full_system_test.py` - Полный E2E тест всего процесса

#### `/legacy/` - Унаследованные тесты
- `test_fixed_command.py` - Устаревший тест команд

#### `/utils/` - Утилиты тестирования и диагностики
- `check_placements_data.py` - Проверка данных размещений
- `debug_db_structure.py` - Отладка структуры БД

#### Корневые тесты (требуют категоризации):
- `test_complete_system.py` - Полное тестирование всей системы
- `test_acceptance_flow.py` - Тест процесса принятия предложений (ЭТАП 2)
- `test_ereit.py` - Тестирование eREIT интеграции
- `test_notifications.py` - Основной тест системы уведомлений
- `test_rejection_flow.py` - Тест процесса отклонения предложений

## Запуск тестов:

```bash
# Все тесты (если используется pytest)
python -m pytest tests/

# По категориям
python -m pytest tests/unit/          # Юнит-тесты
python -m pytest tests/integration/   # Интеграционные тесты
python -m pytest tests/system/        # Системные тесты

# Отдельные тесты (прямой запуск)
python tests/unit/test_notification.py
python tests/system/test_placement_completion.py
python tests/integration/test_delete_api.py

# Корневые тесты (временно)
python tests/test_acceptance_flow.py
python tests/test_complete_system.py
```

## Правила для тестов:

1. ✅ Все тестовые файлы должны находиться в папке `tests/`
2. ✅ Имена файлов должны начинаться с `test_`
3. ✅ Каждый тест должен быть самодостаточным
4. ✅ Тесты должны очищать за собой тестовые данные
5. ✅ Использовать уникальные telegram_id для избежания конфликтов

## Примечания:

- Все тесты используют локальную базу данных `telegram_mini_app.db`
- API тесты предполагают запущенный сервер на `http://localhost:5000`
- При необходимости тесты создают временных пользователей и данные