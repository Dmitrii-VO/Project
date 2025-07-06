"""
Минимальный API для каналов без проблемных импортов
"""
from flask import Blueprint, request, jsonify
import logging
import sqlite3
import os
import re
import random
from datetime import datetime
from app.services.telegram_verification import verify_channel

# Настройка логирования
logger = logging.getLogger(__name__)

# Создание Blueprint
channels_bp = Blueprint('channels', __name__)

# Путь к базе данных
DATABASE_PATH = 'telegram_mini_app.db'


def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def extract_username_from_url(url):
    """Извлекает username из различных форматов URL Telegram"""
    # Убираем пробелы
    url = url.strip()

    # Если это уже чистый username
    if not url.startswith('http') and not url.startswith('@'):
        return url.lstrip('@')

    # Паттерны для извлечения username
    patterns = [
        r'https?://t\.me/([a-zA-Z0-9_]+)',  # https://t.me/username
        r'https?://telegram\.me/([a-zA-Z0-9_]+)',  # https://telegram.me/username
        r'@([a-zA-Z0-9_]+)',  # @username
        r'^([a-zA-Z0-9_]+)$'  # просто username
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            username = match.group(1)
            logger.info(f"🔍 Извлечен username: {username} из URL: {url}")
            return username

    # Если ничего не найдено, возвращаем как есть
    logger.warning(f"⚠️ Не удалось извлечь username из: {url}")
    return url.lstrip('@')


@channels_bp.route('/my', methods=['GET'])
def get_my_channels():
    """Получение каналов пользователя"""
    try:
        telegram_user_id = request.headers.get('X-Telegram-User-Id')

        if not telegram_user_id:
            return jsonify({
                'success': False,
                'error': 'X-Telegram-User-Id header is required'
            }), 400

        logger.info(f"🔍 Получение каналов для Telegram ID: {telegram_user_id}")

        # Подключение к базе данных
        conn = sqlite3.connect('telegram_mini_app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ИСПРАВЛЕНО: Получаем каналы с подробной информацией
        cursor.execute("""
                       SELECT c.*,
                              u.username as owner_username
                       FROM channels c
                                LEFT JOIN users u ON c.owner_id = u.id
                       WHERE u.telegram_id = ?
                       ORDER BY c.created_at DESC
                       """, (telegram_user_id,))

        channels = cursor.fetchall()
        conn.close()

        logger.info(f"📊 Найдено каналов в БД: {len(channels)}")

        # ИСПРАВЛЕНО: Преобразуем в список словарей с правильными полями
        channels_list = []
        for channel in channels:
            # Получаем реальное количество подписчиков из БД
            subscriber_count = channel['subscriber_count']

            # Отладочная информация
            logger.info(f"📈 Канал {channel['title']}: subscriber_count в БД = {subscriber_count}")

            channel_dict = {
                'id': channel['id'],
                'telegram_id': channel['telegram_id'],
                'title': channel['title'],
                'username': channel['username'],

                # ИСПРАВЛЕНО: Правильное получение подписчиков
                'subscriber_count': subscriber_count or 0,  # ✅ Из БД
                'description': channel['description'] or '',
                'category': channel['category'] or 'general',
                'language': channel['language'] or 'ru',
                'is_verified': bool(channel['is_verified']),
                'is_active': bool(channel['is_active']),
                'created_at': channel['created_at'],
                'updated_at': channel['updated_at'],
                'verification_code': channel['verification_code'],
                'status': channel['status'],
                'verified_at': channel['verified_at'],
                'owner_username': channel['owner_username'],

                # Дополнительные поля для совместимости с фронтендом
                'channel_name': channel['title'],
                'channel_username': channel['username'],

                # Поля которых нет в БД - добавляем значения по умолчанию
                'is_public': True,
                'accepts_ads': True,
                'invite_link': f'https://t.me/{channel["username"].lstrip("@")}' if channel['username'] else None,
                'photo_url': None,
                'avg_engagement_rate': 0.0,
                'price_per_post': 0,

                # Добавляем статистику
                'offers_count': get_channel_offers_count(channel['id']),
                'posts_count': get_channel_posts_count(channel['id'])
            }
            channels_list.append(channel_dict)

        logger.info(f"✅ Возвращаем {len(channels_list)} каналов")

        return jsonify({
            'success': True,
            'channels': channels_list,
            'total': len(channels_list)
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения каналов: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ДОБАВЛЯЕМ вспомогательные функции:
def get_channel_offers_count(channel_id: int) -> int:
    """Получение количества офферов для канала"""
    try:
        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()

        # Проверяем таблицу responses
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
        if cursor.fetchone():
            cursor.execute("""
                           SELECT COUNT(DISTINCT r.offer_id)
                           FROM responses r
                           WHERE r.channel_id = ?
                           """, (channel_id,))
            result = cursor.fetchone()
            count = result[0] if result else 0
        else:
            count = 0

        conn.close()
        return count

    except Exception as e:
        logger.error(f"Error getting offers count for channel {channel_id}: {e}")
        return 0


def get_channel_posts_count(channel_id: int) -> int:
    """Получение количества постов канала"""
    try:
        from datetime import datetime

        conn = sqlite3.connect('telegram_mini_app.db')
        cursor = conn.cursor()

        # Проверяем таблицу posts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM posts WHERE channel_id = ?", (channel_id,))
            result = cursor.fetchone()
            count = result[0] if result else 0
        else:
            # Примерный подсчет по дате создания канала
            cursor.execute("SELECT created_at FROM channels WHERE id = ?", (channel_id,))
            result = cursor.fetchone()

            if result and result[0]:
                try:
                    created_at = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                    days_active = (datetime.now() - created_at).days
                    count = max(0, days_active // 7)  # Примерно 1 пост в неделю
                except:
                    count = 0
            else:
                count = 0

        conn.close()
        return count

    except Exception as e:
        logger.error(f"Error getting posts count for channel {channel_id}: {e}")
        return 0


@channels_bp.route('/analyze', methods=['POST'])
def analyze_channel():
    """Анализ канала по username для получения информации"""
    try:
        logger.info("🔍 Анализ канала")

        data = request.get_json()
        if not data:
            logger.error("❌ Нет JSON данных")
            return jsonify({'success': False, 'error': 'JSON данные обязательны'}), 400

        # Проверяем разные варианты передачи username
        username = data.get('username') or data.get('channel_username') or data.get('channel_url', '')
        if not username:
            logger.error("❌ Не найден username канала")
            return jsonify({'success': False, 'error': 'Username канала обязателен'}), 400

        # Извлекаем username из различных форматов URL
        cleaned_username = extract_username_from_url(username)
        logger.info(f"📺 Анализируем канал: @{cleaned_username}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')
        logger.info(f"👤 Пользователь: {telegram_user_id}")

        # Проверяем, не добавлен ли уже канал
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT c.id, c.title
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       WHERE (c.username = ? OR c.telegram_id = ?)
                         AND u.telegram_id = ?
                       """, (cleaned_username, cleaned_username, telegram_user_id))

        existing_channel = cursor.fetchone()
        conn.close()

        if existing_channel:
            logger.warning(f"❌ Канал @{cleaned_username} уже добавлен")
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен'
            }), 409

        # Сначала пробуем получить реальные данные из Telegram API
        real_data = {'success': False}  
        # Определяем категорию по username
        category = 'other'
        if any(word in cleaned_username.lower() for word in ['tech', 'it', 'dev', 'code']):
            category = 'technology'
        elif any(word in cleaned_username.lower() for word in ['news', 'новости']):
            category = 'news'
        elif any(word in cleaned_username.lower() for word in ['crypto', 'bitcoin', 'btc']):
            category = 'crypto'
        elif any(word in cleaned_username.lower() for word in ['game', 'игр']):
            category = 'gaming'

        # Всегда используем сгенерированные данные (JavaScript делает реальные запросы)
        logger.info(f"⚠️ Используем сгенерированные данные для @{cleaned_username}")

        if real_data.get('success'):
            logger.info(f"✅ Получены реальные данные для @{cleaned_username}")

            channel_info = {
                'success': True,
                'data': {
                    'username': cleaned_username,
                    'title': real_data.get('title', f'Канал @{cleaned_username}'),
                    'description': real_data.get('description') or f'Telegram канал @{cleaned_username}',
                    'subscriber': real_data.get('subscriber', 0),
                    'engagement_rate': round(random.uniform(1.0, 15.0), 1) if real_data.get('subscriber', 0) > 0 else 0,
                    'verified': False,  # Эту информацию сложно получить через API
                    'category': category,
                    'avatar_letter': cleaned_username[0].upper() if cleaned_username else 'C',
                    'channel_type': real_data.get('type', 'channel'),
                    'invite_link': real_data.get('invite_link') or f'https://t.me/{cleaned_username}',
                    'estimated_reach': {
                        'min_views': int(real_data.get('subscriber', 0) * 0.1),
                        'max_views': int(real_data.get('subscriber', 0) * 0.4),
                        'avg_views': int(real_data.get('subscriber', 0) * 0.25)
                    } if real_data.get('subscriber', 0) > 0 else None,
                    'data_source': 'telegram_api'
                },
                'user_permissions': {
                    'is_admin': True,
                    'can_post': True
                },
                'note': 'Данные получены из Telegram API'
            }
        else:
            logger.info(f"⚠️ Данных нет для @{cleaned_username}")
            return jsonify(channel_info)

    except Exception as e:
        logger.error(f"💥 Ошибка анализа канала: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500


@channels_bp.route('', methods=['POST'])
def add_channel():
    """Добавление нового канала с данными от фронтенда"""
    try:
        logger.info("➕ Попытка добавления нового канала")

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')
        logger.info(f"👤 Пользователь: {telegram_user_id}")

        username = data.get('username', '').strip()
        if not username:
            return jsonify({'success': False, 'error': 'Username обязателен'}), 400

        cleaned_username = extract_username_from_url(username)
        logger.info(f"📺 Добавляем канал: @{cleaned_username}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем ID пользователя
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_user_id,))
        user = cursor.fetchone()

        if not user:
            # Создаем пользователя если не существует
            cursor.execute("""
                           INSERT INTO users (telegram_id, username, first_name, is_active, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)
                           """, (telegram_user_id, f'user_{telegram_user_id}', 'User', True,
                                 datetime.now().isoformat(), datetime.now().isoformat()))
            user_db_id = cursor.lastrowid
            logger.info(f"✅ Создан новый пользователь с ID: {user_db_id}")
        else:
            user_db_id = user['id']
            logger.info(f"✅ Найден пользователь с ID: {user_db_id}")

        # Проверяем, не добавлен ли уже канал
        is_reverify = data.get('action') == 'reverify'

        cursor.execute("""
                       SELECT c.id, c.title, c.verification_code, c.is_verified, c.status
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       WHERE (c.username = ? OR c.username = ? OR c.telegram_id = ?)
                         AND u.telegram_id = ?
                       """, (cleaned_username, f'@{cleaned_username}', cleaned_username, telegram_user_id))

        existing_channel = cursor.fetchone()

        # Если канал существует и это НЕ повторная верификация - ошибка
        if existing_channel and not is_reverify:
            logger.warning(f"❌ Канал @{cleaned_username} уже добавлен (ID: {existing_channel['id']})")
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен'
            }), 409

        # Если это повторная верификация существующего канала
        if existing_channel and is_reverify:
            logger.info(f"🔄 Повторная верификация канала @{cleaned_username}")

            # Генерируем новый код верификации
            import secrets
            new_verification_code = f'VERIFY_{secrets.token_hex(4).upper()}'

            # Обновляем код верификации в существующем канале
            cursor.execute("""
                           UPDATE channels
                           SET verification_code = ?,
                               status            = 'pending',
                               is_verified       = FALSE,
                               updated_at        = ?
                           WHERE id = ?
                           """, (new_verification_code, datetime.now().isoformat(), existing_channel['id']))

            conn.commit()
            conn.close()

            logger.info(f"✅ Новый код верификации для канала {existing_channel['id']}: {new_verification_code}")

            return jsonify({
                'success': True,
                'message': 'Новый код верификации сгенерирован',
                'verification_code': new_verification_code,
                'channel': {
                    'id': existing_channel['id'],
                    'username': cleaned_username,
                    'title': existing_channel['title'],
                    'verification_code': new_verification_code,
                    'status': 'pending'
                }
            })

        # Парсим число подписчиков если это строка (например "12.5K")
        if isinstance(subscriber_count, str):
            try:
                # Обрабатываем форматы типа "12.5K", "1.2M"
                if subscriber_count.upper().endswith('K'):
                    subscriber_count = int(float(subscriber_count[:-1]) * 1000)
                elif subscriber_count.upper().endswith('M'):
                    subscriber_count = int(float(subscriber_count[:-1]) * 1000000)
                else:
                    subscriber_count = int(subscriber_count)
            except (ValueError, TypeError):
                subscriber_count = 0

        # Убеждаемся что это число
        if not isinstance(subscriber_count, int):
            subscriber_count = 0

        logger.info(f"📊 Количество подписчиков от фронтенда: {subscriber_count}")
        logger.info(f"🔍 DEBUG: Полученные данные = {data}")
        logger.info(f"🔍 DEBUG: channel_data = {data.get('channel_data', 'НЕТ')}")

        # Генерируем код верификации
        import secrets
        verification_code = f'VERIFY_{secrets.token_hex(4).upper()}'
        logger.info(f"📝 Сгенерирован код верификации: {verification_code}")

        # ✅ СОХРАНЯЕМ КАНАЛ С ДАННЫМИ ОТ ФРОНТЕНДА
        subscriber_count = 0

        # Проверяем разные варианты передачи данных о подписчиках
        possible_subscriber_fields = ['subscriber_count'
        ]

        for field in possible_subscriber_fields:
            value = data.get(field)
            if value and isinstance(value, (int, str)) and str(value).isdigit():
                subscriber_count = int(value)
                logger.info(f"✅ Найдены подписчики в поле '{field}': {subscriber_count}")
                break

        logger.info(f"📊 Итоговое количество подписчиков для сохранения: {subscriber_count}")

        # ✅ ИСПРАВЛЕНО: Правильное определение telegram_id
        telegram_channel_id = data.get('telegram_id') or data.get('channel_id') or cleaned_username

        # Добавляем канал в БД
        cursor.execute("""
                       INSERT INTO channels (telegram_id, title, username, description, category,
                                             subscriber_count, language, is_verified, is_active,
                                             owner_id, created_at, updated_at, status, verification_code)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       """, (
                           telegram_channel_id,  # ✅ ИСПРАВЛЕНО
                           data.get('title', f'Канал @{cleaned_username}'),
                           cleaned_username,
                           data.get('description', 'Описание канала'),
                           data.get('category', 'general'),
                           subscriber_count,  # ✅ ИСПРАВЛЕНО: используем вычисленное значение
                           'ru',
                           False,
                           True,
                           user_db_id,
                           datetime.now().isoformat(),
                           datetime.now().isoformat(),
                           'pending',
                           verification_code
                       ))

        channel_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"✅ Канал добавлен с ID: {channel_id}, подписчиков: {subscriber_count}")

        return jsonify({
            'success': True,
            'message': f'Канал @{cleaned_username} добавлен',
            'channel': {
                'id': channel_id,
                'username': cleaned_username,
                'verification_code': verification_code,
                'subscriber_count': subscriber_count  # Возвращаем для подтверждения
            }
        }), 201

    except Exception as e:
        logger.error(f"💥 Ошибка добавления канала: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500


@channels_bp.route('/<int:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """Удаление канала"""
    try:
        logger.info(f"🗑️ Попытка удаления канала {channel_id}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        logger.info(f"👤 Telegram User ID: {telegram_user_id}")

        if not telegram_user_id:
            logger.warning("❌ Не указан Telegram User ID")
            return jsonify({
                'success': False,
                'error': 'Не указан Telegram User ID'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем права на удаление
        logger.info(f"🔍 Проверяем права на канал {channel_id}")
        cursor.execute("""
            SELECT c.id, c.title, c.username 
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ? AND u.telegram_id = ?
        """, (channel_id, telegram_user_id))

        channel = cursor.fetchone()

        if not channel:
            logger.warning(f"❌ Канал {channel_id} не найден для пользователя {telegram_user_id}")

            # Проверяем, существует ли канал вообще
            cursor.execute("SELECT id, title FROM channels WHERE id = ?", (channel_id,))
            any_channel = cursor.fetchone()

            conn.close()

            if any_channel:
                return jsonify({
                    'success': False,
                    'error': 'У вас нет прав на удаление этого канала'
                }), 403
            else:
                return jsonify({
                    'success': False,
                    'error': 'Канал не найден'
                }), 404

        channel_title = channel['title'] if channel['title'] else f'ID {channel_id}'
        logger.info(f"✅ Канал найден: {channel_title}")

        # Удаляем связанные данные
        logger.info(f"🔄 Удаление связанных данных")

        # 1. Удаляем ответы на офферы (если таблица существует)
        try:
            cursor.execute("""
                DELETE FROM offer_responses 
                WHERE offer_id IN (
                    SELECT id FROM offers WHERE channel_id = ?
                )
            """, (channel_id,))
            logger.info(f"✅ Удалены ответы на офферы: {cursor.rowcount}")
        except sqlite3.Error as e:
            logger.debug(f"Ошибка удаления ответов: {e}")

        # 2. Удаляем офферы (если таблица существует)
        try:
            cursor.execute("DELETE FROM offers WHERE channel_id = ?", (channel_id,))
            logger.info(f"✅ Удалены офферы: {cursor.rowcount}")
        except sqlite3.Error as e:
            logger.debug(f"Ошибка удаления офферов: {e}")

        # 3. Удаляем уведомления (если таблица существует)
        try:
            cursor.execute("""
                DELETE FROM notifications 
                WHERE data LIKE '%"channel_id":' || ? || '%'
            """, (channel_id,))
            logger.info(f"✅ Удалены уведомления: {cursor.rowcount}")
        except sqlite3.Error as e:
            logger.debug(f"Ошибка удаления уведомлений: {e}")

        # 4. Удаляем сам канал
        logger.info(f"🗑️ Удаляем канал {channel_id}")
        cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        deleted_count = cursor.rowcount

        # Подтверждаем изменения
        conn.commit()
        conn.close()

        logger.info(f"🎯 Удалено строк: {deleted_count}")

        if deleted_count > 0:
            logger.info(f"✅ Канал {channel_id} ({channel_title}) успешно удален")
            return jsonify({
                'success': True,
                'message': f'Канал "{channel_title}" успешно удален'
            })
        else:
            logger.error(f"❌ Канал {channel_id} не был удален")
            return jsonify({
                'success': False,
                'error': 'Канал не был удален'
            }), 500

    except Exception as e:
        logger.error(f"💥 Критическая ошибка удаления канала {channel_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500


@channels_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook для получения обновлений от Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': True})

        # Проверка пересланных сообщений для верификации
        if 'message' in data:
            message = data['message']

            # Обработка команды /start
            if 'text' in message and message['text'] == '/start':
                from_user_id = str(message['from']['id'])

                try:
                    import requests
                    bot_token = os.environ.get('BOT_TOKEN', '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8')
                    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                    welcome_message = """👋 <b>Добро пожаловать!</b>

                    Я помогу вам верифицировать ваши Telegram каналы.

                    <b>Как это работает:</b>
                    1️⃣ Добавьте канал в Mini App
                    2️⃣ Получите код верификации
                    3️⃣ Опубликуйте код в вашем канале
                    4️⃣ Переслать сообщение с кодом мне

                    После успешной верификации вы получите уведомление прямо здесь!"""

                    # Создаем клавиатуру для приветствия
                    welcome_keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚀 Открыть Mini App",
                                    "web_app": {
                                        "url": f"{os.environ.get('WEBAPP_URL', 'https://your-domain.com')}"
                                    }
                                }
                            ]
                        ]
                    }

                    requests.post(send_url, json={
                        'chat_id': from_user_id,
                        'text': welcome_message,
                        'parse_mode': 'HTML',
                        'reply_markup': welcome_keyboard
                    }, timeout=5)
                except:
                    pass

            # Проверка пересланных сообщений
            elif 'forward_from_chat' in message:
                forward_chat = message['forward_from_chat']

                # Проверяем, что это канал
                if forward_chat.get('type') == 'channel':
                    chat_id = str(forward_chat.get('id'))
                    chat_username = forward_chat.get('username', '').lower()
                    from_user_id = str(message['from']['id'])

                    # Получаем текст пересланного сообщения
                    forward_text = message.get('text', '')

                    logger.info(f"📩 Пересланное сообщение из @{chat_username}: {forward_text[:50]}...")

                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Ищем канал с кодом верификации в пересланном тексте
                    cursor.execute("""
                        SELECT c.id, c.title, c.verification_code, c.username
                        FROM channels c
                        JOIN users u ON c.owner_id = u.id
                        WHERE u.telegram_id = ?
                        AND c.is_verified = 0
                        AND c.verification_code IS NOT NULL
                    """, (from_user_id,))

                    channels = cursor.fetchall()

                    # Проверяем каждый канал пользователя
                    for channel in channels:
                        # Проверяем, есть ли код верификации в тексте
                        if channel['verification_code'] in forward_text:
                            # И совпадает ли username канала
                            if (channel['username'].lower() == chat_username or
                                    channel['username'].lower() == f'@{chat_username}' or
                                    channel['telegram_id'] == chat_id):

                                # Верифицируем канал
                                cursor.execute("""
                                    UPDATE channels
                                    SET is_verified = 1,
                                        verified_at = ?,
                                        status = 'verified',
                                        telegram_id = ?
                                    WHERE id = ?
                                """, (datetime.now().isoformat(), chat_id, channel['id']))

                                conn.commit()
                                logger.info(f"✅ Канал '{channel['title']}' верифицирован!")

                                # Отправляем уведомление ПОЛЬЗОВАТЕЛЮ В БОТ
                                try:
                                    import requests
                                    bot_token = os.environ.get('BOT_TOKEN', '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8')
                                    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                                    success_message = f"""✅ <b>Канал успешно верифицирован!</b>

                                    📺 <b>Канал:</b> {channel['title']}
                                    🔗 <b>Username:</b> @{channel['username']}
                                    📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

                                    Теперь вы можете:
                                    - Получать предложения от рекламодателей
                                    - Устанавливать цены за размещение
                                    - Просматривать статистику канала

                                    Перейдите в <a href="https://t.me/miniappsmatchbot/start?startapp=channels">Mini App</a> для управления каналом."""

                                    # НА:
                                    # Получаем данные пользователя
                                    cursor.execute("""
                                                   SELECT first_name, last_name, username
                                                   FROM users
                                                   WHERE telegram_id = ?
                                                   """, (from_user_id,))
                                    user_data = cursor.fetchone()

                                    # Форматируем имя пользователя
                                    if user_data:
                                        user_name_parts = []
                                        if user_data['first_name']:
                                            user_name_parts.append(user_data['first_name'])
                                        if user_data['last_name']:
                                            user_name_parts.append(user_data['last_name'])
                                        full_name = ' '.join(user_name_parts) if user_name_parts else user_data[
                                                                                                          'username'] or 'Пользователь'
                                    else:
                                        full_name = 'Пользователь'

                                    # Форматируем дату добавления канала
                                    try:
                                        # Парсим дату создания канала
                                        created_at = datetime.fromisoformat(
                                            channel['created_at'].replace('Z', '+00:00'))
                                        formatted_date = created_at.strftime('%d.%m.%Y в %H:%M')
                                    except:
                                        formatted_date = 'Недавно'


                                    success_message = f"""✅ <b>Канал успешно верифицирован!</b>

                                    📺 <b>Канал:</b> {channel['title']}
                                    👤 <b>Пользователь:</b> {full_name}
                                    📅 <b>Дата добавления:</b> {formatted_date}

                                    🎉 <b>Поздравляем!</b> Ваш канал верифицирован!

                                    Теперь вы можете:
                                    - Получать предложения от рекламодателей
                                    - Устанавливать цены за размещение
                                    - Просматривать статистику канала
                                    - Управлять настройками"""

                                    # Создаем клавиатуру с кнопкой Mini App
                                    keyboard = {
                                        "inline_keyboard": [
                                            [
                                                {
                                                    "text": "🚀 Открыть Mini App",
                                                    "web_app": {
                                                        "url": f"{os.environ.get('WEBAPP_URL', 'https://your-domain.com')}/channels"
                                                    }
                                                }
                                            ]
                                        ]
                                    }

                                    requests.post(send_url, json={
                                        'chat_id': from_user_id,
                                        'text': success_message,
                                        'parse_mode': 'HTML',
                                        'reply_markup': keyboard
                                    }, timeout=5)
                                except Exception as e:
                                    logger.error(f"Ошибка отправки уведомления: {e}")

                                conn.close()
                                return jsonify({'ok': True})

                    # Если код не найден, отправляем подсказку
                    try:
                        import requests
                        bot_token = os.environ.get('BOT_TOKEN', '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8')
                        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                        requests.post(send_url, json={
                            'chat_id': from_user_id,
                            'text': '❌ Код верификации не найден в пересланном сообщении.\n\nУбедитесь, что вы переслали сообщение с кодом верификации из вашего канала.',
                            'parse_mode': 'HTML'
                        }, timeout=5)
                    except:
                        pass

                    conn.close()

        return jsonify({'ok': True})

    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return jsonify({'ok': True})


@channels_bp.route('/test', methods=['GET'])
def test_channels_api():
    """Тестовый эндпоинт для проверки работы API"""
    try:
        # Проверяем подключение к БД
        if not os.path.exists(DATABASE_PATH):
            return jsonify({
                'success': False,
                'error': f'База данных не найдена: {DATABASE_PATH}'
            }), 500

        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем количество каналов
        cursor.execute("SELECT COUNT(*) as count FROM channels")
        channels_count = cursor.fetchone()['count']

        # Проверяем количество пользователей
        cursor.execute("SELECT COUNT(*) as count FROM users")
        users_count = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            'success': True,
            'message': 'Channels API работает!',
            'stats': {
                'channels': channels_count,
                'users': users_count
            }
        })

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@channels_bp.route('/<int:channel_id>/verify', methods=['PUT', 'POST'])
def verify_channel_endpoint(channel_id):
    """Верификация канала"""
    try:
        logger.info(f"🔍 Запрос верификации канала {channel_id}")

        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем канал
        cursor.execute("""
            SELECT c.*, u.telegram_id as owner_telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.id = ? AND u.telegram_id = ?
        """, (channel_id, telegram_user_id))

        channel = cursor.fetchone()

        if not channel:
            conn.close()
            return jsonify({'success': False, 'error': 'Канал не найден'}), 404

        if channel['is_verified']:
            conn.close()
            return jsonify({
                'success': True,
                'message': 'Канал уже верифицирован',
                'channel': dict(channel)
            })

        # Используем сервис верификации
        channel_username = channel['username']
        verification_code = channel['verification_code']

        # Добавляем @ если нужно
        if channel_username and not channel_username.startswith('@'):
            channel_username = '@' + channel_username

        logger.info(f"🔍 Проверяем {channel_username} с кодом {verification_code}")

        # Вызываем сервис верификации
        verification_result = verify_channel(channel_username, verification_code)

        if verification_result.get('success') and verification_result.get('found'):
            # Обновляем статус
            cursor.execute("""
                UPDATE channels 
                SET is_verified = 1, 
                    verified_at = ?,
                    status = 'verified'
                WHERE id = ?
            """, (datetime.now().isoformat(), channel_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ Канал {channel_id} верифицирован!")

            return jsonify({
                'success': True,
                'message': 'Канал успешно верифицирован!',
                'channel': {
                    'id': channel_id,
                    'title': channel['title'],
                    'is_verified': True,
                    'verified_at': datetime.now().isoformat()
                }
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Код верификации не найден в канале',
                'verification_code': verification_code,
                'instructions': [
                    f'1. Перейдите в канал @{channel["username"]}',
                    f'2. Опубликуйте сообщение с кодом: {verification_code}',
                    '3. Подождите 1-2 минуты или нажмите "Верифицировать" снова'
                ]
            }), 400

    except Exception as e:
        logger.error(f"❌ Ошибка верификации: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@channels_bp.route('/debug/<int:channel_id>', methods=['GET'])
def debug_channel(channel_id):
    """Отладочная информация о канале"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Канал не найден'}), 404

        result = {
            'channel': dict(channel),
            'webhook_url': f"{os.environ.get('WEBAPP_URL', 'http://localhost:5000')}/api/channels/webhook",
            'bot_token_available': bool(os.environ.get('BOT_TOKEN')),
            'verification_service_loaded': 'verify_channel' in globals()
        }

        conn.close()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Добавьте этот эндпоинт в channels.py

@channels_bp.route('/<int:channel_id>/update-stats', methods=['PUT', 'POST'])
def update_channel_stats(channel_id):
    """Обновление статистики канала данными от фронтенда"""

    logger.info(f"📊 Обновление статистики канала {channel_id}")

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'JSON данные обязательны'}), 400

    # Получаем telegram_user_id из заголовков
    telegram_user_id = request.headers.get('X-Telegram-User-Id')
    if not telegram_user_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем права на канал
    cursor.execute("""
                    SELECT c.id, c.title, c.username, c.subscriber_count
                    FROM channels c
                            JOIN users u ON c.owner_id = u.id
                    WHERE c.id = ?
                        AND u.telegram_id = ?
                    """, (channel_id, telegram_user_id))

    channel = cursor.fetchone()
    if not channel:
        conn.close()
        return jsonify({'success': False, 'error': 'Канал не найден'}), 404
    logger.info(f"✅ Канал найден: {channel['title']} (ID: {channel_id})")


