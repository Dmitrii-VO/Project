import os
import sys
from dotenv import load_dotenv


# Добавляем пути для импорта модулей
def find_project_root():
    """Автоматически находит корень проекта"""
    current = os.path.dirname(os.path.abspath(__file__))
    
    # Поднимаемся вверх, пока не найдем признаки корня проекта
    while current != os.path.dirname(current):  # Пока не дошли до корня диска
        markers = ['telegram_mini_app.db', 'requirements.txt', '.env', '.git']
        if any(os.path.exists(os.path.join(current, marker)) for marker in markers):
            return current
        current = os.path.dirname(current)
    
    # Если не нашли, возвращаем текущую папку
    return os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = find_project_root()
APP_PATH = os.path.join(PROJECT_ROOT, 'app')

for path in [PROJECT_ROOT, APP_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)

# === КОНФИГУРАЦИЯ ===
class AppConfig:
    """Централизованная конфигурация приложения"""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_PATH = os.path.join(PROJECT_ROOT, 'telegram_mini_app.db')
    WEBAPP_URL = os.environ.get('WEBAPP_URL', 'http://localhost:5000')

    # Настройки производительности
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = DEBUG

    @classmethod
    def validate(cls) -> bool:
        """Валидация критических настроек"""
        errors = []

        if not cls.BOT_TOKEN or cls.BOT_TOKEN == 'your-bot-token':
            errors.append("BOT_TOKEN не настроен")

        if not os.path.exists(cls.DATABASE_PATH):
            errors.append(f"База данных не найдена: {cls.DATABASE_PATH}")

        if errors:
            for error in errors:
                print(f"❌ {error}")
            return False

        return True