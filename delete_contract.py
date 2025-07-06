#!/usr/bin/env python3
# delete_contract.py - Удаление проблемного контракта

import sqlite3
import os
from datetime import datetime

# Путь к базе данных
DB_PATH = 'telegram_mini_app.db'

def delete_problematic_contract():
    """Удаление контракта с ID 'null'"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("🔍 Поиск проблемного контракта...")
        
        # Ищем контракт с ID NULL
        cursor.execute("SELECT * FROM contracts WHERE id IS NULL")
        problematic_contract = cursor.fetchone()
        
        if problematic_contract:
            print("🎯 НАЙДЕН проблемный контракт с NULL ID:")
            print(f"   ID: {problematic_contract[0]} (NULL)")
            print(f"   Response ID: {problematic_contract[1]}")
            print(f"   Offer ID: {problematic_contract[2]}")
            print(f"   Status: {problematic_contract[5]}")
            print(f"   Создан: {problematic_contract[7]}")
            
            # Подтверждение удаления
            confirm = input("\n❓ Удалить этот контракт с NULL ID? (y/N): ").lower().strip()
            
            if confirm in ['y', 'yes', 'да']:
                # Удаляем контракт
                cursor.execute("DELETE FROM contracts WHERE id IS NULL")
                deleted_contracts = cursor.rowcount
                print(f"✅ Удалено контрактов: {deleted_contracts}")
                
                # Проверяем связанные записи в payments
                cursor.execute("SELECT COUNT(*) FROM payments WHERE contract_id IS NULL")
                payments_count = cursor.fetchone()[0]
                
                if payments_count > 0:
                    print(f"⚠️  Найдено {payments_count} связанных записей в payments")
                    delete_payments = input("❓ Удалить связанные платежи? (y/N): ").lower().strip()
                    
                    if delete_payments in ['y', 'yes', 'да']:
                        cursor.execute("DELETE FROM payments WHERE contract_id IS NULL")
                        print(f"✅ Удалено {payments_count} связанных платежей")
                
                # Проверяем связанные записи в monitoring_tasks
                cursor.execute("SELECT COUNT(*) FROM monitoring_tasks WHERE contract_id IS NULL")
                monitoring_count = cursor.fetchone()[0]
                
                if monitoring_count > 0:
                    print(f"⚠️  Найдено {monitoring_count} связанных задач мониторинга")
                    delete_monitoring = input("❓ Удалить связанные задачи мониторинга? (y/N): ").lower().strip()
                    
                    if delete_monitoring in ['y', 'yes', 'да']:
                        cursor.execute("DELETE FROM monitoring_tasks WHERE contract_id IS NULL")
                        print(f"✅ Удалено {monitoring_count} задач мониторинга")
                
                # Применяем изменения
                conn.commit()
                
                print("\n🎉 ПРОБЛЕМНЫЙ КОНТРАКТ УСПЕШНО УДАЛЕН!")
                
                # Показываем статистику после удаления
                cursor.execute("SELECT COUNT(*) FROM contracts")
                total_contracts = cursor.fetchone()[0]
                print(f"📊 Осталось контрактов в базе: {total_contracts}")
                
            else:
                print("❌ Удаление отменено")
                return False
                
        else:
            print("✅ Контракт с NULL ID не найден в базе данных")
            
            # Показываем все контракты
            cursor.execute("SELECT id, status, created_at FROM contracts ORDER BY created_at DESC LIMIT 10")
            contracts = cursor.fetchall()
            
            if contracts:
                print("\n📋 Последние 10 контрактов:")
                for contract in contracts:
                    print(f"   ID: {contract[0]}, Status: {contract[1]}, Created: {contract[2]}")
            else:
                print("📋 В базе данных нет контрактов")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при работе с базой данных: {e}")
        return False

def show_contracts_stats():
    """Показать статистику контрактов"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n📊 === СТАТИСТИКА КОНТРАКТОВ ===")
        
        # Общее количество
        cursor.execute("SELECT COUNT(*) FROM contracts")
        total = cursor.fetchone()[0]
        print(f"Всего контрактов: {total}")
        
        # По статусам
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM contracts 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        """)
        statuses = cursor.fetchall()
        
        print("По статусам:")
        for status, count in statuses:
            print(f"  {status}: {count}")
        
        # Проблемные контракты
        cursor.execute("SELECT COUNT(*) FROM contracts WHERE id IS NULL OR id = '' OR id = 'null'")
        problematic = cursor.fetchone()[0]
        
        if problematic > 0:
            print(f"⚠️  Проблемных контрактов (NULL ID): {problematic}")
            
            # Показываем детали проблемных контрактов
            cursor.execute("SELECT id, status, created_at FROM contracts WHERE id IS NULL OR id = '' OR id = 'null'")
            problematic_contracts = cursor.fetchall()
            
            for contract in problematic_contracts:
                print(f"     ID: {contract[0]}, Status: {contract[1]}, Created: {contract[2]}")
        else:
            print("✅ Проблемных контрактов не найдено")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

if __name__ == "__main__":
    print("🗑️  === УДАЛЕНИЕ ПРОБЛЕМНОГО КОНТРАКТА ===")
    print(f"База данных: {DB_PATH}")
    print()
    
    # Показываем статистику до удаления
    show_contracts_stats()
    
    # Удаляем проблемный контракт
    success = delete_problematic_contract()
    
    if success:
        print()
        # Показываем статистику после удаления
        show_contracts_stats()
    
    print("\n✅ Готово!")