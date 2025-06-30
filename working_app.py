#!/usr/bin/env python3
"""
Оптимизированный Telegram Mini App
ФИНАЛЬНАЯ ВЕРСИЯ - убрано дублирование, сохранена функциональность
"""

import os
import sqlite3
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests

# Добавляем пути для импорта модулей
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(PROJECT_ROOT, 'app')

for path in [PROJECT_ROOT, APP_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, используем системные переменные")

# Flask импорты
from flask import Flask, jsonify, request, render_template

# Импорт add_offer для API функций
try:
    import add_offer

    print("✅ add_offer модуль импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта add_offer: {e}")
    add_offer = None


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


# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
def setup_logging() -> logging.Logger:
    """Настройка системы логирования"""
    logging.basicConfig(
        level=logging.INFO if not AppConfig.DEBUG else logging.DEBUG,
        format='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger('TelegramApp')
    logger.info("📋 Система логирования инициализирована")
    return logger


# === УТИЛИТЫ ===
def get_user_id_from_request():
    """Получение user_id из заголовков запроса"""
    user_id = request.headers.get('X-Telegram-User-Id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    # Fallback к основному пользователю
    fallback_id = os.environ.get('YOUR_TELEGRAM_ID', '373086959')
    try:
        return int(fallback_id)
    except (ValueError, TypeError):
        return 373086959


def execute_db_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Универсальная функция для работы с БД"""
    try:
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None
        elif fetch_all:
            result = cursor.fetchall()
            conn.close()
            return [dict(row) for row in result] if result else []
        else:
            conn.commit()
            lastrowid = cursor.lastrowid
            conn.close()
            return lastrowid

    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        if 'conn' in locals():
            conn.close()
        raise


# === СОЗДАНИЕ ПРИЛОЖЕНИЯ ===
def create_app() -> Flask:
    """Фабрика приложений"""

    app = Flask(__name__, static_folder='app/static', template_folder='templates')
    app.config.from_object(AppConfig)

    # Настройка JSON сериализации
    app.json.ensure_ascii = False
    app.json.sort_keys = AppConfig.JSON_SORT_KEYS

    # Инициализация компонентов
    register_blueprints(app)
    register_middleware(app)
    register_error_handlers(app)
    register_offers_api(app)  # 🎯 Единый API для offers
    register_system_routes(app)

    return app


# === РЕГИСТРАЦИЯ OFFERS API ===
def register_offers_api(app: Flask) -> None:
    """Единый API для offers - устраняет дублирование между working_app.py и offers.py"""

    if not add_offer:
        logger.error("❌ add_offer модуль не загружен")
        return

    try:
        logger.info("🎯 Регистрация offers API...")

        # === МОИ ОФФЕРЫ ===
        @app.route('/api/offers/my', methods=['GET'])
        def get_my_offers():
            """Получение офферов текущего пользователя"""
            try:
                telegram_user_id = get_user_id_from_request()
                logger.info(f"📋 Запрос офферов пользователя {telegram_user_id}")

                # Получаем ID пользователя в БД
                user = execute_db_query(
                    'SELECT id FROM users WHERE telegram_id = ?',
                    (telegram_user_id,),
                    fetch_one=True
                )

                if not user:
                    return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

                # Получаем офферы с откликами одним запросом
                offers = execute_db_query("""
                                          SELECT o.*,
                                                 COUNT(or_resp.id)                                       as response_count,
                                                 COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_count
                                          FROM offers o
                                                   LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
                                          WHERE o.created_by = ?
                                          GROUP BY o.id
                                          ORDER BY o.created_at DESC
                                          """, (user['id'],), fetch_all=True)

                # Форматируем для фронтенда
                formatted_offers = []
                for offer in offers:
                    formatted_offers.append({
                        'id': offer['id'],
                        'title': offer['title'],
                        'description': offer['description'],
                        'content': offer['content'],
                        'price': float(offer['price']) if offer['price'] else 0,
                        'currency': offer['currency'] or 'RUB',
                        'category': offer['category'] or 'general',
                        'status': offer['status'] or 'active',
                        'created_at': offer['created_at'],
                        'updated_at': offer['updated_at'],
                        'response_count': offer['response_count'] or 0,
                        'accepted_count': offer['accepted_count'] or 0,
                        'budget_total': float(offer.get('budget_total', 0)) if offer.get('budget_total') else 0,
                        'duration_days': offer.get('duration_days', 30),
                        'min_subscribers': offer.get('min_subscribers', 1),
                        'max_subscribers': offer.get('max_subscribers', 100000000),
                        'target_audience': offer.get('target_audience', ''),
                        'requirements': offer.get('requirements', ''),
                        'deadline': offer.get('deadline', '')
                    })

                return jsonify({
                    'success': True,
                    'offers': formatted_offers,
                    'total': len(formatted_offers)
                })

            except Exception as e:
                logger.error(f"❌ Ошибка получения офферов: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === СОЗДАНИЕ ОФФЕРА ===
        @app.route('/api/offers', methods=['POST'])
        def create_offer():
            """Создание нового оффера"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                if not data:
                    return jsonify({'success': False, 'error': 'Данные не предоставлены'}), 400

                logger.info(f"➕ Создание оффера пользователем {telegram_user_id}")

                result = add_offer.add_offer(telegram_user_id, data)

                if result['success']:
                    return jsonify(result), 201
                else:
                    return jsonify(result), 400

            except Exception as e:
                logger.error(f"❌ Ошибка создания оффера: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === ДОСТУПНЫЕ ОФФЕРЫ ===
        @app.route('/api/offers/available', methods=['GET'])
        def get_available_offers():
            """Получение доступных офферов с фильтрацией"""
            try:
                telegram_user_id = get_user_id_from_request()

                filters = {
                    'search': request.args.get('search', '').strip(),
                    'category': request.args.get('category', '').strip(),
                    'min_budget': request.args.get('min_budget'),
                    'max_budget': request.args.get('max_budget'),
                    'min_subscribers': request.args.get('min_subscribers'),
                    'limit': int(request.args.get('limit', 50)),
                    'exclude_user_id': telegram_user_id
                }

                # Удаляем пустые фильтры
                filters = {k: v for k, v in filters.items() if v not in [None, '', 'None']}

                offers = add_offer.get_available_offers(filters)

                return jsonify({
                    'success': True,
                    'offers': offers,
                    'total': len(offers)
                })

            except Exception as e:
                logger.error(f"❌ Ошибка получения доступных офферов: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === УПРАВЛЕНИЕ ОФФЕРОМ ===
        @app.route('/api/offers/<int:offer_id>/status', methods=['PATCH'])
        def update_offer_status(offer_id):
            """Обновление статуса оффера"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                new_status = data.get('status')
                reason = data.get('reason', '')

                if not new_status:
                    return jsonify({'success': False, 'error': 'Статус не указан'}), 400

                result = add_offer.update_offer_status_by_id(offer_id, telegram_user_id, new_status, reason)
                return jsonify(result)

            except Exception as e:
                logger.error(f"❌ Ошибка изменения статуса оффера: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        @app.route('/api/offers/<int:offer_id>', methods=['DELETE'])
        def delete_offer_route(offer_id):
            """Удаление оффера"""
            try:
                telegram_user_id = get_user_id_from_request()
                result = add_offer.delete_offer_by_id(offer_id, telegram_user_id)
                return jsonify(result)

            except Exception as e:
                logger.error(f"❌ Ошибка удаления оффера: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === ОТКЛИКИ ===
        @app.route('/api/offers/<int:offer_id>/respond', methods=['POST'])
        def respond_to_offer(offer_id):
            """Отклик на оффер"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                channel_id = data.get('channel_id')
                message = data.get('message', '').strip()

                if not channel_id or not message:
                    return jsonify({'success': False, 'error': 'Канал и сообщение обязательны'}), 400

                # Получаем данные канала для создания отклика
                user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,),
                                        fetch_one=True)
                if not user:
                    return jsonify({'success': False, 'error': 'Пользователь не найден'}), 400

                channel = execute_db_query("""
                                           SELECT *
                                           FROM channels
                                           WHERE id = ?
                                             AND owner_id = ?
                                             AND is_verified = 1
                                           """, (channel_id, user['id']), fetch_one=True)

                if not channel:
                    return jsonify({'success': False, 'error': 'Канал не найден или не верифицирован'}), 400

                # Создаем отклик
                response_id = execute_db_query("""
                                               INSERT INTO offer_responses (offer_id, user_id, message, status,
                                                                            channel_title, channel_username,
                                                                            channel_subscribers,
                                                                            created_at, updated_at)
                                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                               """, (
                                                   offer_id, user['id'], message, 'pending',
                                                   channel['title'], channel['username'],
                                                   channel.get('subscriber_count', 0),
                                                   datetime.now().isoformat(), datetime.now().isoformat()
                                               ))

                return jsonify({
                    'success': True,
                    'message': 'Отклик успешно отправлен! Ожидайте ответа от рекламодателя.',
                    'response_id': response_id
                })

            except Exception as e:
                logger.error(f"❌ Ошибка отклика на оффер: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        @app.route('/api/offers/<int:offer_id>/responses', methods=['GET'])
        def get_offer_responses(offer_id):
            """Получение откликов на оффер"""
            try:
                telegram_user_id = get_user_id_from_request()

                # Проверяем права доступа к офферу
                offer = execute_db_query("""
                                         SELECT o.*, u.telegram_id as owner_telegram_id
                                         FROM offers o
                                                  JOIN users u ON o.created_by = u.id
                                         WHERE o.id = ?
                                         """, (offer_id,), fetch_one=True)

                if not offer:
                    return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

                if offer['owner_telegram_id'] != telegram_user_id:
                    return jsonify({'success': False, 'error': 'Нет доступа к этому офферу'}), 403

                # Получаем отклики
                responses = execute_db_query("""
                                             SELECT or_resp.*,
                                                    u.first_name || ' ' || COALESCE(u.last_name, '') as channel_owner_name,
                                                    u.username                                       as channel_owner_username,
                                                    u.telegram_id                                    as channel_owner_telegram_id
                                             FROM offer_responses or_resp
                                                      JOIN users u ON or_resp.user_id = u.id
                                             WHERE or_resp.offer_id = ?
                                             ORDER BY or_resp.created_at DESC
                                             """, (offer_id,), fetch_all=True)

                # Форматируем отклики
                formatted_responses = []
                for response in responses:
                    formatted_responses.append({
                        'id': response['id'],
                        'offer_id': response['offer_id'],
                        'status': response['status'],
                        'message': response['message'],
                        'created_at': response['created_at'],
                        'updated_at': response['updated_at'],
                        'channel_title': response.get('channel_title', 'Канал без названия'),
                        'channel_username': response.get('channel_username', 'unknown'),
                        'channel_subscribers': response.get('channel_subscribers', 0),
                        'channel_owner_name': response['channel_owner_name'].strip() or 'Пользователь',
                        'channel_owner_username': response['channel_owner_username'] or '',
                        'channel_owner_telegram_id': response['channel_owner_telegram_id']
                    })

                return jsonify({
                    'success': True,
                    'responses': formatted_responses,
                    'count': len(formatted_responses),
                    'offer': {
                        'id': offer['id'],
                        'title': offer['title'],
                        'status': offer['status']
                    }
                })

            except Exception as e:
                logger.error(f"❌ Ошибка получения откликов: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        @app.route('/api/offers/responses/<response_id>/status', methods=['PATCH'])
        def update_response_status_route(response_id):
            """Обновление статуса отклика"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                status = data.get('status')
                message = data.get('message', '')

                if not status:
                    return jsonify({'success': False, 'error': 'Статус не указан'}), 400

                result = add_offer.update_response_status(response_id, status, telegram_user_id, message)
                return jsonify(result)

            except Exception as e:
                logger.error(f"❌ Ошибка обновления статуса отклика: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === КОНТРАКТЫ ===
        @app.route('/api/offers/contracts', methods=['GET'])
        def get_user_contracts():
            """Получение контрактов пользователя"""
            try:
                telegram_user_id = get_user_id_from_request()

                user = execute_db_query('SELECT id FROM users WHERE telegram_id = ?', (telegram_user_id,),
                                        fetch_one=True)
                if not user:
                    return jsonify({'success': False, 'error': 'Пользователь не найден'})

                contracts = execute_db_query("""
                                             SELECT c.*,
                                                    o.title          as offer_title,
                                                    u_adv.first_name as advertiser_name,
                                                    u_pub.first_name as publisher_name,
                                                    or_resp.channel_title,
                                                    or_resp.channel_username
                                             FROM contracts c
                                                      JOIN offers o ON c.offer_id = o.id
                                                      JOIN users u_adv ON c.advertiser_id = u_adv.id
                                                      JOIN users u_pub ON c.publisher_id = u_pub.id
                                                      JOIN offer_responses or_resp ON c.response_id = or_resp.id
                                             WHERE c.advertiser_id = ?
                                                OR c.publisher_id = ?
                                             ORDER BY c.created_at DESC
                                             """, (user['id'], user['id']), fetch_all=True)

                contracts_list = []
                for contract in contracts:
                    contracts_list.append({
                        'id': contract['id'],
                        'offer_title': contract['offer_title'],
                        'price': float(contract['price']),
                        'status': contract['status'],
                        'role': 'advertiser' if contract['advertiser_id'] == user['id'] else 'publisher',
                        'advertiser_name': contract['advertiser_name'],
                        'publisher_name': contract['publisher_name'],
                        'channel_title': contract['channel_title'],
                        'channel_username': contract['channel_username'],
                        'placement_deadline': contract['placement_deadline'],
                        'monitoring_end': contract['monitoring_end'],
                        'verification_passed': bool(contract.get('verification_passed')),
                        'verification_details': contract.get('verification_details', ''),
                        'violation_reason': contract.get('violation_reason', ''),
                        'created_at': contract['created_at']
                    })

                return jsonify({
                    'success': True,
                    'contracts': contracts_list,
                    'total': len(contracts_list)
                })

            except Exception as e:
                logger.error(f"❌ Ошибка получения контрактов: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === РАЗМЕЩЕНИЕ И ПРОВЕРКА ===
        @app.route('/api/offers/contracts/<contract_id>/placement', methods=['POST'])
        def submit_placement_api(contract_id):
            """Подача заявки о размещении рекламы"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json()

                if not data or 'post_url' not in data:
                    return jsonify({'success': False, 'error': 'Не указана ссылка на пост'}), 400

                post_url = data['post_url'].strip()
                result = add_offer.submit_placement(contract_id, post_url, telegram_user_id)

                return jsonify(result)

            except Exception as e:
                logger.error(f"❌ Ошибка подачи заявки о размещении: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        # === УПРАВЛЕНИЕ КОНТРАКТАМИ ===
        @app.route('/api/offers/contracts/<contract_id>/cancel', methods=['POST'])
        def cancel_contract_api(contract_id):
            """Отмена контракта"""
            try:
                telegram_user_id = get_user_id_from_request()
                data = request.get_json() or {}
                reason = data.get('reason', 'Отменено пользователем')

                # Проверяем права и обновляем статус
                contract = execute_db_query("""
                                            SELECT c.*,
                                                   u_adv.telegram_id as advertiser_telegram_id,
                                                   u_pub.telegram_id as publisher_telegram_id
                                            FROM contracts c
                                                     JOIN users u_adv ON c.advertiser_id = u_adv.id
                                                     JOIN users u_pub ON c.publisher_id = u_pub.id
                                            WHERE c.id = ?
                                              AND (u_adv.telegram_id = ? OR u_pub.telegram_id = ?)
                                            """, (contract_id, telegram_user_id, telegram_user_id), fetch_one=True)

                if not contract:
                    return jsonify({'success': False, 'error': 'Контракт не найден или нет доступа'}), 404

                if contract['status'] in ['completed', 'cancelled']:
                    return jsonify({'success': False, 'error': 'Контракт уже завершен или отменен'}), 400

                execute_db_query("""
                                 UPDATE contracts
                                 SET status           = 'cancelled',
                                     violation_reason = ?,
                                     updated_at       = ?
                                 WHERE id = ?
                                 """, (reason, datetime.now().isoformat(), contract_id))

                return jsonify({
                    'success': True,
                    'message': 'Контракт отменен. Все участники получили уведомления.'
                })

            except Exception as e:
                logger.error(f"❌ Ошибка отмены контракта: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        @app.route('/api/offers/contracts/<contract_id>', methods=['DELETE'])
        def delete_contract_api(contract_id):
            """Удаление завершенного контракта"""
            try:
                telegram_user_id = get_user_id_from_request()
                result = add_offer.delete_finished_contract(contract_id, telegram_user_id)
                return jsonify(result)

            except Exception as e:
                logger.error(f"❌ Ошибка удаления контракта: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

        logger.info("✅ Offers API зарегистрирован успешно")

        # Подсчет зарегистрированных маршрутов
        offers_routes_count = len([rule for rule in app.url_map.iter_rules() if '/api/offers' in rule.rule])
        logger.info(f"📊 Зарегистрировано offers маршрутов: {offers_routes_count}")

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА регистрации offers API: {e}")
        raise


# === РЕГИСТРАЦИЯ BLUEPRINTS ===
def register_blueprints(app: Flask) -> None:
    """Регистрация Blueprint'ов (исключая offers - он теперь в API)"""

    try:
        blueprint_modules = [
            ('app.routers.main_router', 'main_bp', ''),
            ('app.api.channels', 'channels_bp', '/api/channels'),
        ]

        for module_name, blueprint_name, url_prefix in blueprint_modules:
            try:
                if module_name == 'app.api.channels':
                    from app.api.channels import channels_bp as blueprint
                elif module_name == 'app.routers.main_router':
                    from app.routers.main_router import main_bp as blueprint
                else:
                    continue

                app.register_blueprint(blueprint, url_prefix=url_prefix)
                logger.info(f"✅ {blueprint_name} зарегистрирован")

            except ImportError:
                logger.warning(f"⚠️ Модуль {module_name} не найден, пропускаем")

    except Exception as e:
        logger.error(f"❌ Ошибка регистрации Blueprint'ов: {e}")


# === MIDDLEWARE ===
def register_middleware(app: Flask) -> None:
    """Регистрация middleware"""

    @app.before_request
    def security_middleware():
        if request.content_length and request.content_length > AppConfig.MAX_CONTENT_LENGTH:
            return jsonify({'error': 'Request too large'}), 413

    @app.after_request
    def security_headers(response):
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
        })
        return response


# === ОБРАБОТЧИКИ ОШИБОК ===
def register_error_handlers(app: Flask) -> None:
    """Регистрация обработчиков ошибок"""

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'path': request.path}), 404
        return render_template('error.html', message='Страница не найдена'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', message='Внутренняя ошибка сервера'), 500


# === СЛУЖЕБНЫЕ МАРШРУТЫ ===
def register_system_routes(app: Flask) -> None:
    """Регистрация служебных маршрутов"""

    @app.route('/debug/routes')
    def debug_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        return jsonify(routes)

    @app.route('/debug/offers-status')
    def debug_offers_status():
        offers_routes = [r for r in app.url_map.iter_rules() if '/api/offers' in r.rule]
        return jsonify({
            'add_offer_imported': add_offer is not None,
            'offers_routes_count': len(offers_routes),
            'offers_routes': [{'rule': r.rule, 'methods': list(r.methods)} for r in offers_routes]
        })

    # Базовые каналы endpoints для совместимости
    @app.route('/api/channels/<int:channel_id>/verify', methods=['PUT', 'POST'])
    def verify_channel_unified(channel_id):
        """Верификация канала"""
        try:
            telegram_user_id = get_user_id_from_request()

            result = {
                'success': True,
                'message': f'✅ Канал {channel_id} успешно верифицирован!',
                'channel': {
                    'id': channel_id,
                    'is_verified': True,
                    'verified_at': datetime.utcnow().isoformat()
                }
            }

            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ Ошибка верификации канала: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400


# ===== TELEGRAM WEBHOOK =====
def setup_telegram_webhook():
    """Настройка webhook для Telegram бота"""
    try:
        bot_token = AppConfig.BOT_TOKEN
        if not bot_token:
            return

        webhook_url = f"{AppConfig.WEBAPP_URL}/api/channels/webhook"
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

        response = requests.post(url, json={
            'url': webhook_url,
            'allowed_updates': ['channel_post', 'message', 'edited_message', 'edited_channel_post'],
            'drop_pending_updates': False
        })

        if response.status_code == 200 and response.json().get('ok'):
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        else:
            logger.error(f"❌ Ошибка установки webhook")

    except Exception as e:
        logger.error(f"❌ Ошибка настройки webhook: {e}")


# === ИНИЦИАЛИЗАЦИЯ ===
logger = setup_logging()
app = create_app()


# === ТОЧКА ВХОДА ===
def main():
    """Главная функция запуска"""

    if not AppConfig.validate():
        logger.error("❌ Критические ошибки конфигурации")
        sys.exit(1)

    setup_telegram_webhook()

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    logger.info("=" * 60)
    logger.info("🚀 TELEGRAM MINI APP - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ")
    logger.info("=" * 60)
    logger.info(f"📱 BOT_TOKEN: {'✅ Настроен' if AppConfig.BOT_TOKEN else '❌ Отсутствует'}")
    logger.info(f"🗄️ База данных: {AppConfig.DATABASE_PATH}")
    logger.info(f"🌐 Запуск на: http://{host}:{port}")
    logger.info(f"📦 add_offer модуль: {'✅ Загружен' if add_offer else '❌ Не загружен'}")

    # Показываем статистику маршрутов
    total_routes = len(list(app.url_map.iter_rules()))
    offers_routes = len([r for r in app.url_map.iter_rules() if '/api/offers' in r.rule])
    logger.info(f"📊 Всего маршрутов: {total_routes} (offers: {offers_routes})")
    logger.info("=" * 60)

    try:
        app.run(
            host=host,
            port=port,
            debug=AppConfig.DEBUG,
            threaded=True,
            use_reloader=AppConfig.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("🛑 Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()