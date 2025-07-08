# app/services/__init__.py
"""
Модуль сервисов Telegram Mini App
Содержит всю бизнес-логику и интеграции
"""

# === ДОБАВЬТЕ ЭТО В НАЧАЛО ФАЙЛА ===

# Импорт сервиса верификации каналов
try:
    from .telegram_verification import (
        TelegramVerificationService,
        verification_service,
        verify_channel
    )

    # Добавляем в список экспорта
    VERIFICATION_SERVICES = [
        'TelegramVerificationService',
        'verification_service',
        'verify_channel'
    ]

    print("✅ Сервис верификации Telegram загружен")

except ImportError as e:
    print(f"⚠️ Не удалось загрузить сервис верификации: {e}")
    VERIFICATION_SERVICES = []

# === ОБНОВИТЕ СУЩЕСТВУЮЩИЙ __all__ ===

# Импорты для удобного доступа к сервисам
__all__ = [
              # Существующие сервисы
              'payments_system',
              'analytics_api',
              'placement_tracking',
              'ai_recommendations',
              'payout_system',
              'advanced_matching_algorithm',
              'notifications_system',
              'telegram_webhook'
          ] + VERIFICATION_SERVICES  # Добавляем новые сервисы


# === ОБНОВИТЕ ФУНКЦИЮ get_available_services ===

# Функция для проверки доступности сервисов
def get_available_services():
    """Получить список доступных сервисов"""
    available = []

    services_to_check = [
        'payments_system',
        'analytics_api',
        'placement_tracking',
        'ai_recommendations',
        'payout_system',
        'advanced_matching_algorithm',
        'notifications_system',
        'telegram_webhook',
        'telegram_verification'  # Добавляем проверку нового сервиса
    ]

    for service_name in services_to_check:
        try:
            __import__(f'app.services.{service_name}')
            available.append(service_name)
        except ImportError:
            pass

    return available


# === ОБНОВИТЕ ФУНКЦИЮ init_services ===

# Инициализация сервисов при импорте
def init_services():
    """Инициализация всех доступных сервисов"""
    available_services = get_available_services()

    if available_services:
        print(f"✅ Доступные сервисы: {', '.join(available_services)}")

        # Специальная инициализация для сервиса верификации
        if 'telegram_verification' in available_services:
            try:
                from .telegram_verification import verification_service
                if verification_service.bot_token:
                    print("✅ Сервис верификации готов к работе")
                else:
                    print("⚠️ Сервис верификации работает в тестовом режиме")
            except:
                pass
    else:
        print("⚠️ Сервисы не найдены")

    return available_services