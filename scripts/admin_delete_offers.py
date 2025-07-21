#!/usr/bin/env python3
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
        print("-" * 80)
        print(f"{'ID':2} | {'Название':40} | {'Статус':8} | {'Username':15} | {'Telegram ID':12}")
        print("-" * 80)
        
        for offer in offers:
            print(f"{offer['id']:2} | {offer['title'][:40]:40} | {offer['status']:8} | {offer['username'] or 'N/A':15} | {offer['telegram_id']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def delete_all_test_offers():
    """Удаление всех тестовых офферов"""
    try:
        # Ищем тестовые офферы
        test_offers = execute_db_query("""
            SELECT id, title FROM offers 
            WHERE title LIKE '%тест%' OR title LIKE '%Тест%' OR title LIKE '%TEST%' OR title LIKE '%test%'
        """, fetch_all=True)
        
        if not test_offers:
            print("✅ Тестовые офферы не найдены")
            return True
        
        print(f"🧪 Найдено тестовых офферов: {len(test_offers)}")
        for offer in test_offers:
            print(f"   ID: {offer['id']}, Название: {offer['title'][:50]}...")
        
        confirm = input("❓ Удалить ВСЕ тестовые офферы? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Отменено")
            return False
        
        # Удаляем каждый тестовый оффер
        deleted_count = 0
        for offer in test_offers:
            if admin_delete_offer_silent(offer['id']):
                deleted_count += 1
                print(f"✅ Удален оффер {offer['id']}")
            else:
                print(f"❌ Не удалось удалить оффер {offer['id']}")
        
        print(f"🎯 Удалено {deleted_count}/{len(test_offers)} тестовых офферов")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def admin_delete_offer_silent(offer_id):
    """Тихое удаление оффера без подтверждения"""
    try:
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        conn.execute('BEGIN TRANSACTION')
        
        try:
            conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offer_proposals WHERE offer_id = ?', (offer_id,))
            conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
            
    except Exception:
        return False

if __name__ == "__main__":
    print("🔧 АДМИНИСТРАТИВНАЯ УТИЛИТА УДАЛЕНИЯ ОФФЕРОВ")
    print("=" * 50)
    
    if len(sys.argv) == 2:
        if sys.argv[1] == "list":
            list_all_offers()
        elif sys.argv[1] == "clean-test":
            delete_all_test_offers()
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
        print("  python3 admin_delete_offers.py clean-test    # Удалить все тестовые офферы")