#!/usr/bin/env python3
"""
Исследование проблемы с удалением тестовых офферов
Проверяем права доступа и предлагаем решения
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from working_app import create_app
from app.models.database import execute_db_query
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_offers_and_users():
    """Анализ всех офферов и их владельцев"""
    logger.info("=== Анализ офферов и пользователей ===")
    
    try:
        # Получаем все офферы с информацией о создателях
        offers = execute_db_query("""
            SELECT o.id, o.title, o.status, o.created_at, 
                   o.created_by, u.telegram_id, u.username, u.first_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            ORDER BY o.created_at DESC
        """, fetch_all=True)
        
        logger.info(f"📊 Всего офферов в БД: {len(offers)}")
        
        for offer in offers:
            logger.info(f"🎯 Оффер ID: {offer['id']}")
            logger.info(f"   📝 Название: {offer['title'][:50]}...")
            logger.info(f"   👤 Создатель: {offer['username'] or 'Без username'} (telegram_id: {offer['telegram_id']})")
            logger.info(f"   📅 Создан: {offer['created_at']}")
            logger.info(f"   🏷️ Статус: {offer['status']}")
            logger.info("-" * 40)
        
        return offers
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения офферов: {e}")
        return []

def test_delete_permissions():
    """Тестирование прав на удаление для разных пользователей"""
    logger.info("=== Тестирование прав на удаление ===")
    
    # Получаем всех пользователей
    try:
        users = execute_db_query("""
            SELECT id, telegram_id, username, first_name 
            FROM users
        """, fetch_all=True)
        
        offers = execute_db_query("""
            SELECT id, title, created_by 
            FROM offers 
            ORDER BY id
        """, fetch_all=True)
        
        logger.info(f"👥 Пользователи ({len(users)}):")
        for user in users:
            logger.info(f"   ID: {user['id']}, Telegram: {user['telegram_id']}, Username: {user.get('username', 'N/A')}")
        
        logger.info(f"🎯 Офферы ({len(offers)}):")
        for offer in offers:
            logger.info(f"   ID: {offer['id']}, Создатель: {offer['created_by']}, Название: {offer['title'][:30]}...")
        
        return users, offers
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных: {e}")
        return [], []

def try_delete_with_different_users(offer_id, users):
    """Пробуем удалить оффер от имени разных пользователей"""
    logger.info(f"=== Тестирование удаления оффера {offer_id} ===")
    
    app = create_app()
    
    for user in users:
        telegram_id = user['telegram_id']
        username = user.get('username', 'unknown')
        
        logger.info(f"🧪 Пробуем удалить от имени: {username} (telegram_id: {telegram_id})")
        
        with app.test_client() as client:
            headers = {
                'X-Telegram-User-Id': str(telegram_id),
                'Content-Type': 'application/json'
            }
            
            response = client.delete(f'/api/offers/{offer_id}', headers=headers)
            
            logger.info(f"   📊 HTTP статус: {response.status_code}")
            
            try:
                data = response.get_json()
                if data:
                    if response.status_code == 200:
                        logger.info(f"   ✅ Успешно удален: {data.get('message', 'N/A')}")
                        return True, telegram_id
                    else:
                        logger.info(f"   ❌ Ошибка: {data.get('error', 'N/A')}")
                else:
                    logger.info(f"   ❌ Нет JSON ответа")
            except Exception as e:
                logger.info(f"   ❌ Ошибка парсинга: {e}")
    
    return False, None

def create_admin_delete_utility():
    """Создание утилиты для административного удаления"""
    logger.info("=== Создание админской утилиты удаления ===")
    
    utility_code = '''#!/usr/bin/env python3
"""
Административная утилита для удаления офферов
ИСПОЛЬЗУЙТЕ ОСТОРОЖНО!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.database import execute_db_query
import sqlite3
from app.config.telegram_config import AppConfig

def admin_delete_offer(offer_id):
    """Админское удаление оффера без проверки прав"""
    try:
        # Получаем информацию об оффере
        offer = execute_db_query(
            "SELECT id, title, created_by FROM offers WHERE id = ?",
            (offer_id,),
            fetch_one=True
        )
        
        if not offer:
            print(f"❌ Оффер с ID {offer_id} не найден")
            return False
        
        print(f"🎯 Найден оффер: {offer['title'][:50]}...")
        print(f"👤 Создатель ID: {offer['created_by']}")
        
        confirm = input("❓ Вы уверены, что хотите удалить этот оффер? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Отменено")
            return False
        
        # Удаляем в транзакции
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.execute('BEGIN TRANSACTION')
        
        try:
            # Удаляем связанные данные
            conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offer_proposals WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
            
            conn.commit()
            print(f"✅ Оффер {offer_id} успешно удален")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка удаления: {e}")
            return False
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def list_all_offers():
    """Список всех офферов"""
    try:
        offers = execute_db_query("""
            SELECT o.id, o.title, o.status, o.created_at,
                   u.username, u.telegram_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            ORDER BY o.id
        """, fetch_all=True)
        
        print(f"📊 Всего офферов: {len(offers)}")
        for offer in offers:
            print(f"ID: {offer['id']:2} | {offer['title'][:40]:40} | {offer['status']:8} | {offer['username'] or 'N/A':15} | {offer['telegram_id']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🔧 АДМИНИСТРАТИВНАЯ УТИЛИТА УДАЛЕНИЯ ОФФЕРОВ")
    print("=" * 50)
    
    if len(sys.argv) == 2:
        if sys.argv[1] == "list":
            list_all_offers()
        else:
            try:
                offer_id = int(sys.argv[1])
                admin_delete_offer(offer_id)
            except ValueError:
                print("❌ Некорректный ID оффера")
    else:
        print("Использование:")
        print("  python3 admin_delete_offers.py list          # Список всех офферов")
        print("  python3 admin_delete_offers.py <offer_id>    # Удалить оффер по ID")
'''
    
    # Сохраняем утилиту
    with open('/mnt/d/Project/scripts/admin_delete_offers.py', 'w', encoding='utf-8') as f:
        f.write(utility_code)
    
    logger.info("✅ Утилита создана: scripts/admin_delete_offers.py")
    logger.info("📋 Использование:")
    logger.info("   python3 scripts/admin_delete_offers.py list")
    logger.info("   python3 scripts/admin_delete_offers.py <offer_id>")

def run_investigation():
    """Запуск полного исследования"""
    logger.info("🔍 Начинаем исследование проблемы с удалением офферов")
    
    # Анализ данных
    logger.info("-" * 60)
    offers = analyze_offers_and_users()
    
    logger.info("-" * 60)
    users, db_offers = test_delete_permissions()
    
    if offers and users:
        # Пробуем удалить первый оффер
        if db_offers:
            first_offer_id = db_offers[0]['id']
            logger.info("-" * 60)
            success, user_id = try_delete_with_different_users(first_offer_id, users[:2])  # Тестируем с 2 пользователями
            
            if not success:
                logger.warning("⚠️ Не удалось удалить оффер через обычный API")
                logger.info("💡 Создаем административную утилиту...")
                
                logger.info("-" * 60)
                create_admin_delete_utility()
    
    # Итоговые рекомендации
    logger.info("-" * 60)
    logger.info("📋 РЕКОМЕНДАЦИИ:")
    logger.info("1. Используйте административную утилиту для очистки тестовых данных")
    logger.info("2. Убедитесь, что у вас есть telegram_id владельца оффера")
    logger.info("3. Проверьте права доступа через API с правильной авторизацией")
    
    return True

if __name__ == "__main__":
    run_investigation()