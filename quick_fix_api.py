#!/usr/bin/env python3
"""
Быстрое исправление API для отображения офферов
"""

import os
import shutil
from datetime import datetime

def backup_and_fix_api():
    """Создаем резервную копию и исправляем API"""
    
    print("🔧 БЫСТРОЕ ИСПРАВЛЕНИЕ API")
    print("-" * 40)
    
    # Создаем резервную копию
    try:
        backup_file = f'app/api/offers_backup_fix_{datetime.now().strftime("%H%M%S")}.py'
        shutil.copy2('app/api/offers.py', backup_file)
        print(f"✅ Резервная копия: {backup_file}")
    except Exception as e:
        print(f"⚠️ Не удалось создать резервную копию: {e}")
    
    # Исправленный API код
    fixed_api = '''# app/api/offers.py - Исправленная версия для отображения офферов
from datetime import datetime

from flask import Blueprint, request, jsonify
from app.models.database import db_manager
from app.config.settings import Config
import logging
import os
import sys

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
            # Добавляем путь к корню проекта
            sys.path.insert(0, os.getcwd())
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
    """Получение моих офферов - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        logger.info("Запрос на получение моих офферов")
        
        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        logger.info(f"Определен user_id: {telegram_user_id}")
        
        if not telegram_user_id:
            return jsonify({
                'success': False, 
                'error': 'Не удалось определить пользователя',
                'debug_headers': dict(request.headers),
                'debug_env': os.environ.get('YOUR_TELEGRAM_ID')
            }), 400

        status = request.args.get('status')
        logger.info(f"Фильтр по статусу: {status}")

        try:
            # Добавляем путь к корню проекта
            sys.path.insert(0, os.getcwd())
            from add_offer import get_user_offers
            
            logger.info("Вызываем get_user_offers")
            offers = get_user_offers(telegram_user_id, status)
            logger.info(f"Получено офферов: {len(offers)}")
            
            return jsonify({
                'success': True, 
                'offers': offers, 
                'count': len(offers),
                'user_id': telegram_user_id
            })

        except ImportError as e:
            logger.error(f"Ошибка импорта get_user_offers: {e}")
            return jsonify({
                'success': False,
                'error': f'Модуль системы офферов недоступен: {str(e)}'
            }), 503
        except Exception as e:
            logger.error(f"Ошибка в get_user_offers: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Ошибка получения офферов: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Общая ошибка в get_my_offers: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500


@offers_bp.route('/detail/<int:offer_id>', methods=['GET'])
def get_offer_detail(offer_id):
    """Получение детальной информации об оффере"""
    try:
        include_responses = request.args.get('include_responses', 'false').lower() == 'true'

        try:
            sys.path.insert(0, os.getcwd())
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
            sys.path.insert(0, os.getcwd())
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
@offers_bp.route('/debug/user', methods=['GET', 'POST'])
def debug_current_user():
    """Отладочный маршрут для проверки текущего пользователя"""
    try:
        user_id = get_user_id_from_request()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'headers': dict(request.headers),
            'method': request.method,
            'args': dict(request.args),
            'env_telegram_id': os.environ.get('YOUR_TELEGRAM_ID')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@offers_bp.route('/debug/test', methods=['GET'])
def debug_test_offers():
    """Тестовый маршрут для проверки получения офферов"""
    try:
        # Прямой запрос к БД
        user_id = 373086959  # Ваш ID
        
        sys.path.insert(0, os.getcwd())
        from add_offer import get_user_offers
        
        offers = get_user_offers(user_id)
        
        return jsonify({
            'success': True,
            'test_user_id': user_id,
            'offers_count': len(offers),
            'offers': offers[:3]  # Первые 3 для проверки
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })
'''

    # Записываем исправленный файл
    try:
        with open('app/api/offers.py', 'w', encoding='utf-8') as f:
            f.write(fixed_api)
        
        print("✅ API исправлен!")
        print("✅ Добавлено подробное логирование")
        print("✅ Исправлен импорт add_offer")
        print("✅ Добавлены debug маршруты")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 БЫСТРОЕ ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С ОФФЕРАМИ")
    print("=" * 50)
    
    if backup_and_fix_api():
        print("\n🎉 ИСПРАВЛЕНИЕ ПРИМЕНЕНО!")
        print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Перезапустите сервер: Ctrl+C, затем python working_app.py")
        print("2. Обновите страницу в браузере (F5)")
        print("3. Проверьте консоль браузера")
        print("4. Для отладки: http://localhost:5000/api/offers/debug/test")
    else:
        print("\n❌ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ")

if __name__ == '__main__':
    main()
