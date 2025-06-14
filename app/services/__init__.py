# app/services/__init__.py
"""
Модуль сервисов Telegram Mini App
Содержит всю бизнес-логику и интеграции
"""

# Импорты для удобного доступа к сервисам
__all__ = [
    'payments_system',
    'analytics_api',
    'placement_tracking',
    'ai_recommendations',
    'payout_system',
    'advanced_matching_algorithm',
    'notifications_system',
    'telegram_webhooks'
]


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
        'telegram_webhooks'
    ]

    for service_name in services_to_check:
        try:
            __import__(f'app.services.{service_name}')
            available.append(service_name)
        except ImportError:
            pass

    return available


# Инициализация сервисов при импорте
def init_services():
    """Инициализация всех доступных сервисов"""
    available_services = get_available_services()

    if available_services:
        print(f"✅ Доступные сервисы: {', '.join(available_services)}")
    else:
        print("⚠️ Сервисы не найдены")

    return available_services