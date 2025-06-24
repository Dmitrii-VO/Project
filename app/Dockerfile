# Dockerfile - Исправленная конфигурация для контейнеризации приложения
FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="your-email@example.com"
LABEL description="Telegram Mini App for Advertising Platform"
LABEL version="1.0"

# Установка рабочей директории
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    gcc \
    g++ \
    make \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создание пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копирование requirements.txt для кэширования слоя
COPY requirements.txt /app/

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . /app/

# Создание необходимых директорий
RUN mkdir -p /app/logs /app/uploads /app/static /app/templates

# Создание базы данных SQLite (если не существует)
RUN touch /app/telegram_mini_app.db

# Настройка прав доступа
RUN chown -R appuser:appuser /app && \
    chmod +x /app/working_app.py && \

USER appuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=working_app.py
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:///telegram_mini_app.db

# Открытие порта
EXPOSE 5000

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/test || exit 1

# Команда запуска (исправлено на существующий файл)
CMD ["python", "working_app.py"]