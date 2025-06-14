# enhanced_api_routes.py - Исправленная версия
"""
Модуль расширенных API маршрутов для Telegram Mini App
Содержит дополнительные маршруты и функциональность
"""

import logging
from flask import Flask

logger = logging.getLogger(__name__)


def add_enhanced_routes(app: Flask = None):
    """
    Добавление расширенных маршрутов к Flask приложению

    Args:
        app: Экземпляр Flask приложения (опционально)

    Returns:
        bool: True если маршруты добавлены успешно
    """
    try:
        if app is None:
            logger.warning("Flask приложение не передано в add_enhanced_routes")
            return False

        logger.info("🔗 Добавление расширенных API маршрутов...")

        # Счетчик добавленных маршрутов
        routes_added = 0

        # === БАЗОВЫЕ РАСШИРЕННЫЕ МАРШРУТЫ ===

        @app.route('/api/enhanced/status')
        def enhanced_status():
            """Расширенный статус системы"""
            from flask import jsonify
            import os

            return jsonify({
                'status': 'enhanced_active',
                'version': '2.0',
                'features': {
                    'enhanced_routes': True,
                    'api_extended': True,
                    'telegram_integration': os.environ.get('BOT_TOKEN') is not None
                },
                'message': 'Расширенные маршруты активны'
            })

        routes_added += 1

        @app.route('/api/enhanced/info')
        def enhanced_info():
            """Информация о расширенных возможностях"""
            from flask import jsonify

            return jsonify({
                'enhanced_features': [
                    'Расширенная аналитика',
                    'Продвинутое сопоставление',
                    'Система уведомлений',
                    'Автоматические выплаты'
                ],
                'api_version': '2.0',
                'documentation': '/api/enhanced/docs'
            })

        routes_added += 1

        @app.route('/api/enhanced/docs')
        def enhanced_docs():
            """Документация по расширенным API"""
            from flask import render_template_string

            docs_html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Enhanced API Documentation</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    .endpoint { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                    .method { background: #007bff; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
                    pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
                </style>
            </head>
            <body>
                <h1>🚀 Enhanced API Documentation</h1>

                <div class="endpoint">
                    <h3><span class="method">GET</span> /api/enhanced/status</h3>
                    <p>Получить расширенный статус системы</p>
                    <pre>{"status": "enhanced_active", "version": "2.0"}</pre>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span> /api/enhanced/info</h3>
                    <p>Информация о расширенных возможностях</p>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span> /api/enhanced/health</h3>
                    <p>Детальная проверка здоровья системы</p>
                </div>

                <p><a href="/">← Вернуться на главную</a></p>
            </body>
            </html>
            '''

            return render_template_string(docs_html)

        routes_added += 1

        @app.route('/api/enhanced/health')
        def enhanced_health():
            """Детальная проверка здоровья системы"""
            from flask import jsonify
            import os

            # Проверка различных компонентов
            components = {
                'database': os.path.exists('telegram_mini_app.db'),
                'config': os.path.exists('.env'),
                'bot_token': os.environ.get('BOT_TOKEN') is not None,
                'telegram_id': os.environ.get('YOUR_TELEGRAM_ID') is not None
            }

            all_healthy = all(components.values())

            return jsonify({
                'overall_status': 'healthy' if all_healthy else 'degraded',
                'components': components,
                'timestamp': str(datetime.now()),
                'version': '2.0'
            }), 200 if all_healthy else 503

        routes_added += 1

        # === ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМИ СИСТЕМАМИ ===

        try:
            # Пытаемся добавить маршруты офферов если система доступна
            from add_offer import get_user_offers

            @app.route('/api/enhanced/offers/summary')
            def offers_summary():
                """Краткая сводка по офферам"""
                from flask import jsonify, request

                try:
                    user_id = request.args.get('user_id', type=int)
                    if not user_id:
                        return jsonify({'error': 'user_id обязателен'}), 400

                    offers = get_user_offers(user_id)

                    summary = {
                        'total_offers': len(offers) if offers else 0,
                        'active_offers': len([o for o in offers if o.get('status') == 'active']) if offers else 0,
                        'user_id': user_id
                    }

                    return jsonify(summary)

                except Exception as e:
                    return jsonify({'error': str(e)}), 500

            routes_added += 1
            logger.info("✅ Маршруты офферов добавлены")

        except ImportError:
            logger.warning("⚠️ Система офферов недоступна для расширенных маршрутов")

        # === РЕЗУЛЬТАТ ===

        logger.info(f"✅ Добавлено {routes_added} расширенных маршрутов")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка добавления расширенных маршрутов: {e}")
        return False


# Для обратной совместимости
def add_enhanced_routes_fallback():
    """Заглушка для случаев когда Flask приложение недоступно"""
    logger.warning("⚠️ add_enhanced_routes вызвана без Flask приложения")
    return None


# Импорт datetime для использования в маршрутах
from datetime import datetime