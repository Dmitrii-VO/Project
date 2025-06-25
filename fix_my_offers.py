#!/usr/bin/env python3
"""
Исправление проблемы с API получения моих офферов
"""

def test_my_offers_api():
    """Тестируем API получения офферов"""
    import requests
    
    print("🔍 ДИАГНОСТИКА API /api/offers/my")
    print("-" * 40)
    
    try:
        # Тестируем с правильными заголовками
        response = requests.get(
            'http://localhost:5000/api/offers/my',
            headers={
                'X-Telegram-User-Id': '373086959',
                'Content-Type': 'application/json'
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("❌ API возвращает ошибку!")
            return False
        
        data = response.json()
        if data.get('success'):
            print(f"✅ API работает, найдено офферов: {len(data.get('offers', []))}")
            return True
        else:
            print(f"❌ API вернул ошибку: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def check_server_logs():
    """Проверяем что происходит на сервере"""
    print("\n📋 ПРОВЕРКА СЕРВЕРА")
    print("-" * 40)
    
    try:
        # Проверяем что сервер отвечает
        import requests
        response = requests.get('http://localhost:5000/health')
        if response.status_code == 200:
            print("✅ Сервер работает")
        else:
            print(f"⚠️ Сервер отвечает с кодом: {response.status_code}")
            
        # Проверяем debug API
        debug_response = requests.get(
            'http://localhost:5000/api/offers/debug/user',
            headers={'X-Telegram-User-Id': '373086959'}
        )
        
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            print(f"✅ Debug API работает, user_id: {debug_data.get('user_id')}")
        else:
            print(f"❌ Debug API не работает: {debug_response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки сервера: {e}")

def fix_offers_js():
    """Исправляем JavaScript для корректного запроса"""
    
    js_fix = '''
// Исправление для app/static/js/offers.js
// Добавьте эту функцию для правильного получения user_id

function getTelegramUserId() {
    // Пробуем получить из Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const user = window.Telegram.WebApp.initDataUnsafe.user;
        if (user && user.id) {
            return user.id.toString();
        }
    }
    
    // Fallback к основному пользователю
    return '373086959';
}

// Исправленная функция загрузки офферов
async function loadMyOffers() {
    console.log('📋 Загрузка моих офферов...');
    const container = document.getElementById('offersGrid');

    if (!container) {
        console.error('❌ Контейнер offersGrid не найден');
        return;
    }

    try {
        showOffersLoading();

        const response = await fetch('/api/offers/my', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-User-Id': getTelegramUserId()
            }
        });

        console.log('API Response Status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('API Response Data:', result);

        if (result.success && result.offers && result.offers.length > 0) {
            console.log('✅ Офферы загружены:', result.offers.length);
            renderOffers(result.offers);
        } else {
            console.log('ℹ️ Офферов не найдено');
            showEmptyOffersState();
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки офферов:', error);
        showOffersError('Ошибка загрузки офферов: ' + error.message);
    }
}
'''
    
    print("\n🔧 ИСПРАВЛЕНИЕ JAVASCRIPT")
    print("-" * 40)
    print("Добавьте этот код в app/static/js/offers.js:")
    print(js_fix)

def create_temp_fix():
    """Создаем временное исправление API"""
    print("\n🛠️ СОЗДАНИЕ ВРЕМЕННОГО ИСПРАВЛЕНИЯ")
    print("-" * 40)
    
    temp_api_code = '''
# Временное исправление для app/api/offers.py
# Замените функцию get_my_offers на эту версию:

@offers_bp.route('/my', methods=['GET'])
def get_my_offers():
    """Получение моих офферов - исправленная версия"""
    try:
        # Получаем user_id
        telegram_user_id = get_user_id_from_request()
        if not telegram_user_id:
            return jsonify({
                'success': False, 
                'error': 'Не удалось определить пользователя',
                'debug_headers': dict(request.headers)
            }), 400

        status = request.args.get('status')

        # Импортируем функцию напрямую
        try:
            import sys
            import os
            sys.path.insert(0, os.getcwd())
            from add_offer import get_user_offers
            
            offers = get_user_offers(telegram_user_id, status)
            
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
            return jsonify({
                'success': False,
                'error': f'Ошибка получения офферов: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Общая ошибка в get_my_offers: {e}")
        return jsonify({
            'success': False, 
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500
'''
    
    print("Замените функцию get_my_offers в app/api/offers.py на:")
    print(temp_api_code)

def main():
    """Главная функция диагностики"""
    print("🔧 ДИАГНОСТИКА ПРОБЛЕМЫ С ОТОБРАЖЕНИЕМ ОФФЕРОВ")
    print("=" * 60)
    
    # Тестируем API
    api_works = test_my_offers_api()
    
    # Проверяем сервер
    check_server_logs()
    
    if not api_works:
        print("\n❌ ПРОБЛЕМА В API!")
        print("Нужно исправить код сервера.")
        create_temp_fix()
    
    # Показываем исправление JS
    fix_offers_js()
    
    print("\n🎯 ПЛАН ИСПРАВЛЕНИЯ:")
    print("1. Исправьте функцию get_my_offers в app/api/offers.py")
    print("2. Перезапустите сервер: python working_app.py")
    print("3. Обновите страницу в браузере")
    print("4. Проверьте консоль браузера на ошибки")

if __name__ == '__main__':
    main()
