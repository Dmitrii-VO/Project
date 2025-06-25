#!/usr/bin/env python3
"""
Исправление API офферов для работы без auth_service
"""

import os
import shutil
from datetime import datetime


def backup_current_api():
    """Создаем резервную копию текущего API"""
    api_file = 'app/api/offers.py'
    backup_file = f'app/api/offers_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'

    try:
        shutil.copy2(api_file, backup_file)
        print(f"✅ Создана резервная копия: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return False


def create_fixed_api():
    """Создаем исправленную версию API"""
    fixed_api_content = '''# app/api/offers.py - Исправленная версия без auth_service
from datetime import datetime

from flask import Blueprint, request, jsonify
from app.models.database import db_manager
from app.config.settings import Config
import logging

logger = logging.getLogger(__name__)
offers_bp = Blueprint('offers', __name__)

def get_user_id_from_request():
    """Получаем user_id из запроса (альтернатива auth_service)"""
    # Пробуем получить из заголовков
    user_id = request.headers.get('X-Telegram-User-Id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    # Пробуем получить из JSON данных
    data = request.get_json() or {}
    user_id = data.get('user_id') or data.get('telegram_user_id')
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            pass

    # Fallback к основному пользователю из .env
    import os
    fallback_id = os.environ.get('YOUR_TELEGRAM_ID')
    if fallback_id:
        try:
            return int(fallback_id)
        except (ValueError, TypeError):
            pass

    return None

@offers_bp.route('', methods=['POST'])
def create_offer():
    """Создание нового оффера"""
    try:
        # Проверяем что система включена
        offers_enabled = getattr(Config, 'OFFERS_SYSTEM_ENABLED', True)
        if not offers_enabled:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Импортируем функцию создания оффера
        try:
            from add_offer import add_offer
            result = add_offer(telegram_user_id, data)

            if result['success']:
                logger.info(f"Создан новый оффер {result.get('offer_id')} пользователем {telegram_user_id}")
                return jsonify(result), 201
            else:
                return jsonify(result), 400

        except ImportError as e:
            logger.error(f"Ошибка импорта add_offer: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@offers_bp.route('/my', methods=['GET'])
def get_my_offers():
    """Получение моих офферов"""
    try:
        # Проверяем что система включена
        offers_enabled = getattr(Config, 'OFFERS_SYSTEM_ENABLED', True)
        if not offers_enabled:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        status = request.args.get('status')

        try:
            from add_offer import get_user_offers
            offers = get_user_offers(telegram_user_id, status)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})

        except ImportError as e:
            logger.error(f"Ошибка импорта get_user_offers: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500


@offers_bp.route('/detail/<int:offer_id>', methods=['GET'])
def get_offer_detail(offer_id):
    """Получение детальной информации об оффере"""
    try:
        # Проверяем что система включена
        offers_enabled = getattr(Config, 'OFFERS_SYSTEM_ENABLED', True)
        if not offers_enabled:
            return jsonify({'success': False, 'error': 'Система офферов отключена'}), 503

        include_responses = request.args.get('include_responses', 'false').lower() == 'true'

        try:
            from add_offer import get_offer_by_id
            offer = get_offer_by_id(offer_id, include_responses)

            if offer:
                return jsonify({'success': True, 'offer': offer})
            else:
                return jsonify({'success': False, 'error': 'Оффер не найден'}), 404

        except ImportError as e:
            logger.error(f"Ошибка импорта get_offer_by_id: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения оффера {offer_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения оффера'}), 500


@offers_bp.route('/stats', methods=['GET'])
def get_offers_stats():
    """Статистика офферов пользователя"""
    try:
        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({'success': False, 'error': 'Не удалось определить пользователя'}), 400

        # Получаем ID пользователя в БД
        user = db_manager.execute_query(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_user_id,),
            fetch_one=True
        )

        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'})

        user_db_id = user['id']

        # Статистика офферов
        stats_queries = {
            'total_offers': """SELECT COUNT(*) as count
                               FROM offers
                               WHERE created_by = ?""",
            'active_offers': """SELECT COUNT(*) as count
                                FROM offers
                                WHERE created_by = ? AND status = 'active' """,
            'total_spent': """SELECT COALESCE(SUM(price), 0) as total
                              FROM offers
                              WHERE created_by = ?
                                AND status IN ('completed', 'active')"""
        }

        stats = {}
        for key, query in stats_queries.items():
            result = db_manager.execute_query(query, (user_db_id,), fetch_one=True)
            if key == 'total_spent':
                stats[key] = float(result['total']) if result else 0
            else:
                stats[key] = result['count'] if result else 0

        # Статистика откликов
        response_stats = db_manager.execute_query("""
            SELECT COUNT(*) as total_responses,
                   COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_responses
            FROM offer_responses or_resp
            JOIN offers o ON or_resp.offer_id = o.id
            WHERE o.created_by = ?
        """, (user_db_id,), fetch_one=True)

        stats.update({
            'total_responses': response_stats['total_responses'] if response_stats else 0,
            'accepted_responses': response_stats['accepted_responses'] if response_stats else 0
        })

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Ошибка получения статистики офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения статистики'}), 500


@offers_bp.route('/available', methods=['GET'])
def get_available_offers():
    """Получение доступных офферов для владельцев каналов"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        min_budget = request.args.get('min_budget', type=float)
        max_budget = request.args.get('max_budget', type=float)

        filters = {
            'category': category,
            'min_budget': min_budget,
            'max_budget': max_budget,
            'limit': limit
        }

        # Убираем None значения
        filters = {k: v for k, v in filters.items() if v is not None}

        try:
            from add_offer import get_available_offers
            offers = get_available_offers(filters)
            return jsonify({'success': True, 'offers': offers, 'count': len(offers)})

        except ImportError as e:
            logger.error(f"Ошибка импорта get_available_offers: {e}")
            return jsonify({
                'success': False,
                'error': 'Модуль системы офферов недоступен'
            }), 503

    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return jsonify({'success': False, 'error': 'Ошибка получения офферов'}), 500

# Дополнительные маршруты для отладки
@offers_bp.route('/debug/user', methods=['GET'])
def debug_current_user():
    """Отладочный маршрут для проверки текущего пользователя"""
    try:
        user_id = get_user_id_from_request()

        return jsonify({
            'success': True,
            'user_id': user_id,
            'headers': dict(request.headers),
            'method': request.method
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
'''

    return fixed_api_content


def apply_fix():
    """Применяем исправление"""
    print("🔧 ИСПРАВЛЕНИЕ API ОФФЕРОВ")
    print("-" * 40)

    # Создаем резервную копию
    if not backup_current_api():
        return False

    # Записываем исправленную версию
    try:
        with open('app/api/offers.py', 'w', encoding='utf-8') as f:
            f.write(create_fixed_api())

        print("✅ API исправлен!")
        print("✅ Убрана зависимость от auth_service")
        print("✅ Добавлена альтернативная аутентификация")
        print("✅ Добавлен отладочный маршрут /api/offers/debug/user")

        return True

    except Exception as e:
        print(f"❌ Ошибка записи исправленного API: {e}")
        return False


def main():
    """Главная функция"""
    print("🔧 ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ API ОФФЕРОВ")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if apply_fix():
        print("\n🎉 ИСПРАВЛЕНИЕ ПРИМЕНЕНО!")
        print("\n📋 ЧТО ИЗМЕНИЛОСЬ:")
        print("- Убрана зависимость от auth_service")
        print("- Добавлено получение user_id из заголовков")
        print("- Fallback к YOUR_TELEGRAM_ID из .env")
        print("- Добавлен debug маршрут")

        print("\n🚀 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Перезапустите сервер: python working_app.py")
        print("2. Откройте: http://localhost:5000/offers")
        print("3. Протестируйте создание оффера")
        print("4. Проверьте debug: http://localhost:5000/api/offers/debug/user")
    else:
        print("\n❌ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ")


if __name__ == '__main__':
    main()