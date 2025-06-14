import os
from typing import Optional

class Config:
    """Базовая конфигурация приложения"""



    # Основные настройки
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # База данных
    DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite:///telegram_mini_app.db')
    DATABASE_PATH: str = DATABASE_URL.replace('sqlite:///', '')

    # ДОБАВИТЬ ЭТИ СТРОКИ для Flask-SQLAlchemy:
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Telegram
    BOT_TOKEN: Optional[str] = os.environ.get('BOT_TOKEN')
    YOUR_TELEGRAM_ID: int = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))
    WEBAPP_URL: Optional[str] = os.environ.get('WEBAPP_URL')
    
    # Платежи
    TELEGRAM_PAYMENT_TOKEN: Optional[str] = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
    WEBHOOK_SECRET: str = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-here')


    
    # Безопасность
    REQUEST_LIMIT: int = 100
    TIME_WINDOW: int = 3600
    
    # Функции (обновляются при импорте модулей)
    TELEGRAM_INTEGRATION: bool = True
    OFFERS_SYSTEM_ENABLED: bool = True
    RESPONSES_SYSTEM_ENABLED: bool = True
    PAYMENTS_SYSTEM_ENABLED: bool = True
    ANALYTICS_SYSTEM_ENABLED: bool = True
    PLACEMENT_TRACKING_ENABLED: bool = True
    AI_RECOMMENDATIONS_ENABLED: bool = True
    ADVANCED_MATCHING_ENABLED: bool = True
    NOTIFICATIONS_ENABLED: bool = True
    PAYOUT_SYSTEM_ENABLED: bool = True
    
    @classmethod
    def validate_config(cls) -> bool:
        """Проверка критических настроек"""
        if not cls.BOT_TOKEN:
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не настроен!")
            return False
        
        if not os.path.exists(cls.DATABASE_PATH):
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: База данных не найдена: {cls.DATABASE_PATH}")
            return False
            
        return True
