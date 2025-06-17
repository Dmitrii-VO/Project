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


def get_real_telegram_data(username):
    """Попытка получить реальные данные канала через Telegram API"""
    try:
        import requests

        # Используем публичную информацию (ограниченную)
        # Для полных данных нужно, чтобы бот был админом канала

        bot_token = "6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8"

        # Пробуем получить информацию о чате
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        response = requests.get(url, params={'chat_id': f'@{username}'}, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                chat_info = data.get('result', {})

                # Пробуем получить количество участников
                members_url = f"https://api.telegram.org/bot{bot_token}/getChatMemberCount"
                members_response = requests.get(members_url, params={'chat_id': f'@{username}'}, timeout=10)

                member_count = 0
                if members_response.status_code == 200:
                    members_data = members_response.json()
                    if members_data.get('ok'):
                        member_count = members_data.get('result', 0)

                return {
                    'success': True,
                    'title': chat_info.get('title', f'Канал @{username}'),
                    'description': chat_info.get('description', ''),
                    'username': chat_info.get('username', username),
                    'subscribers': member_count,
                    'type': chat_info.get('type', 'channel'),
                    'invite_link': chat_info.get('invite_link'),
                    'photo': chat_info.get('photo')
                }

        logger.warning(f"⚠️ Не удалось получить данные из Telegram API для @{username}")
        return {'success': False, 'error': 'API недоступен'}

    except Exception as e:
        logger.error(f"❌ Ошибка Telegram API: {e}")
        return {'success': False, 'error': str(e)}


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
    """Получение каналов текущего пользователя"""
    try:
        # Получаем telegram_user_id из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '373086959')
        logger.info(f"👤 Получение каналов для пользователя {telegram_user_id}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем каналы пользователя
        cursor.execute("""
                       SELECT c.id,
                              c.telegram_id,
                              c.title,
                              c.username,
                              c.subscriber_count,
                              c.description,
                              c.category,
                              c.language,
                              c.is_verified,
                              c.is_active,
                              c.owner_id,
                              c.created_at,
                              c.updated_at,
                              c.verification_code,
                              c.status,
                              c.verified_at,
                              u.username as owner_username
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       WHERE u.telegram_id = ?
                       ORDER BY c.created_at DESC
                       """, (telegram_user_id,))

        channels = cursor.fetchall()
        conn.close()

        # Преобразуем в список словарей
        # Преобразуем в список словарей с ПРАВИЛЬНЫМИ полями
        channels_list = []
        for channel in channels:
            channel_dict = {
                'id': channel['id'],
                'telegram_id': channel['telegram_id'],
                'title': channel['title'],
                'username': channel['username'],
                'subscribers_count': channel['subscriber_count'] or 0,  # ✅ Правильное поле
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
                'price_per_post': 0
            }
            channels_list.append(channel_dict)

        logger.info(f"✅ Найдено каналов: {len(channels_list)}")

        return jsonify({
            'success': True,
            'channels': channels_list,
            'total': len(channels_list)
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения каналов: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        real_data = get_real_telegram_data(cleaned_username)

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

        if real_data.get('success'):
            logger.info(f"✅ Получены реальные данные для @{cleaned_username}")

            channel_info = {
                'success': True,
                'data': {
                    'username': cleaned_username,
                    'title': real_data.get('title', f'Канал @{cleaned_username}'),
                    'description': real_data.get('description') or f'Telegram канал @{cleaned_username}',
                    'subscribers': real_data.get('subscribers', 0),
                    'engagement_rate': round(random.uniform(1.0, 15.0), 1) if real_data.get('subscribers', 0) > 0 else 0,
                    'verified': False,  # Эту информацию сложно получить через API
                    'category': category,
                    'avatar_letter': cleaned_username[0].upper() if cleaned_username else 'C',
                    'channel_type': real_data.get('type', 'channel'),
                    'invite_link': real_data.get('invite_link') or f'https://t.me/{cleaned_username}',
                    'estimated_reach': {
                        'min_views': int(real_data.get('subscribers', 0) * 0.1),
                        'max_views': int(real_data.get('subscribers', 0) * 0.4),
                        'avg_views': int(real_data.get('subscribers', 0) * 0.25)
                    } if real_data.get('subscribers', 0) > 0 else None,
                    'data_source': 'telegram_api'
                },
                'user_permissions': {
                    'is_admin': True,
                    'can_post': True
                },
                'note': 'Данные получены из Telegram API'
            }
        else:
            logger.info(f"⚠️ Используем сгенерированные данные для @{cleaned_username}")

            # Возвращаем улучшенную информацию о канале
            # В реальном приложении здесь был бы запрос к Telegram API

            # Генерируем более реалистичные данные
            # Случайное количество подписчиков (от 500 до 50000)
            subscribers = random.randint(500, 50000)

            # Случайный процент вовлеченности (от 1% до 15%)
            engagement = round(random.uniform(1.0, 15.0), 1)

            channel_info = {
                'success': True,
                'data': {
                    'username': cleaned_username,
                    'title': f'Канал @{cleaned_username}',
                    'description': f'Telegram канал @{cleaned_username}. Реальные данные будут получены после подключения к Telegram API.',
                    'subscribers': subscribers,
                    'engagement_rate': engagement,
                    'verified': random.choice([True, False]),  # Случайно верифицирован или нет
                    'category': category,
                    'avatar_letter': cleaned_username[0].upper() if cleaned_username else 'C',
                    'channel_type': 'channel',
                    'invite_link': f'https://t.me/{cleaned_username}',
                    'estimated_reach': {
                        'min_views': int(subscribers * 0.1),
                        'max_views': int(subscribers * 0.4),
                        'avg_views': int(subscribers * 0.25)
                    },
                    'posting_frequency': f'{random.randint(1, 5)} постов в день',
                    'last_post': f'{random.randint(1, 24)} часов назад',
                    'data_source': 'generated'
                },
                'user_permissions': {
                    'is_admin': True,
                    'can_post': True
                },
                'note': 'Данные сгенерированы для демонстрации. Для получения реальных данных необходимо подключение к Telegram API.'
            }

        logger.info(f"✅ Анализ канала @{cleaned_username} завершен")
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
    """Добавление нового канала"""
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
        cursor.execute("""
            SELECT c.id, c.title
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.username = ?
            AND u.telegram_id = ?
        """, (f'@{cleaned_username}', telegram_user_id))

        existing_channel = cursor.fetchone()

        if existing_channel:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Канал @{cleaned_username} уже добавлен'
            }), 409

        # Генерируем код верификации
        import secrets
        verification_code = secrets.token_hex(8)

        # Добавляем канал в БД
        cursor.execute("""
                       INSERT INTO channels (telegram_id, title, username, description, category,
                                             subscriber_count, language, is_verified, is_active,
                                             owner_id, created_at, updated_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       """, (
                           cleaned_username,  # telegram_id (используем username)
                           data.get('title', f'Канал @{cleaned_username}'),  # title
                           cleaned_username,  # username
                           data.get('description', 'Описание канала'),  # description
                           data.get('category', 'general'),  # category
                           data.get('subscribers_count', 0),  # subscriber_count
                           'ru',  # language
                           False,  # is_verified
                           True,  # is_active
                           user_db_id,  # owner_id
                           datetime.now().isoformat(),  # created_at
                           datetime.now().isoformat(),  # updated_at
                           'pending'  # status
                       ))

        channel_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"✅ Канал добавлен с ID: {channel_id}")

        return jsonify({
            'success': True,
            'message': f'Канал @{cleaned_username} добавлен',
            'channel': {
                'id': channel_id,
                'username': cleaned_username,
                'verification_code': verification_code
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
        logger.info("📨 Получен webhook от Telegram")

        data = request.get_json()
        if not data:
            logger.warning("❌ Пустой webhook")
            return jsonify({'ok': True})

        logger.info(f"📨 Webhook данные: {data.get('update_id', 'N/A')}")

        # Обрабатываем сообщения в каналах для автоверификации
        if 'channel_post' in data:
            message = data['channel_post']
            chat = message.get('chat', {})
            chat_id = str(chat.get('id'))
            text = message.get('text', '')

            logger.info(f"📢 Сообщение из канала {chat_id}: {text[:50]}...")

            # Ищем каналы с кодами верификации
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, verification_code, telegram_id
                FROM channels 
                WHERE status = 'pending_verification' 
                AND verification_code IS NOT NULL
            """)

            channels = cursor.fetchall()

            if channels:
                logger.info(f"🔍 Найдено {len(channels)} каналов на проверке")

                for channel in channels:
                    verification_code = channel['verification_code']
                    if verification_code and verification_code in text:
                        # Подтверждаем канал
                        cursor.execute("""
                            UPDATE channels 
                            SET status = 'verified', verified_at = ?, is_verified = 1
                            WHERE id = ?
                        """, (datetime.now().isoformat(), channel['id']))

                        conn.commit()
                        logger.info(f"✅ Канал {channel['id']} верифицирован!")
                        break

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
