#!/usr/bin/env python3
"""
Скрипт для проверки созданных контрактов
"""

import sqlite3
from datetime import datetime

DATABASE_PATH = 'telegram_mini_app.db'


def check_contracts():
    """Проверяет созданные контракты"""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем таблицу contracts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contracts'")
        if not cursor.fetchone():
            print("❌ Таблица 'contracts' не найдена!")
            return

        # Получаем все контракты
        cursor.execute('''
                       SELECT c.*,
                              o.title        as offer_title,
                              or_resp.status as response_status
                       FROM contracts c
                                JOIN offers o ON c.offer_id = o.id
                                JOIN offer_responses or_resp ON c.response_id = or_resp.id
                       ORDER BY c.created_at DESC
                       ''')

        contracts = cursor.fetchall()

        print(f"📋 Найдено контрактов: {len(contracts)}")
        print("-" * 80)

        for contract in contracts:
            print(f"🆔 ID: {contract['id']}")
            print(f"📝 Оффер: {contract['offer_title']}")
            print(f"💰 Цена: {contract['price']} RUB")
            print(f"📊 Статус контракта: {contract['status']}")
            print(f"📊 Статус отклика: {contract['response_status']}")
            print(f"⏰ Создан: {contract['created_at']}")
            print(f"📅 Дедлайн размещения: {contract['placement_deadline']}")
            print("-" * 40)

        # Статистика по статусам
        cursor.execute('''
                       SELECT status, COUNT(*) as count
                       FROM contracts
                       GROUP BY status
                       ''')

        status_stats = cursor.fetchall()

        print(f"📊 Статистика контрактов:")
        for stat in status_stats:
            print(f"   {stat['status']}: {stat['count']}")

        # Проверяем связи
        cursor.execute('''
                       SELECT (SELECT COUNT(*) FROM contracts)                                 as total_contracts,
                              (SELECT COUNT(*) FROM offer_responses WHERE status = 'accepted') as accepted_responses,
                              (SELECT COUNT(*) FROM offers WHERE status = 'in_progress')       as in_progress_offers
                       ''')

        stats = cursor.fetchone()

        print(f"\n🔗 Проверка связей:")
        print(f"   Контрактов: {stats['total_contracts']}")
        print(f"   Принятых откликов: {stats['accepted_responses']}")
        print(f"   Офферов в работе: {stats['in_progress_offers']}")

        if stats['total_contracts'] == stats['accepted_responses']:
            print("✅ Каждому принятому отклику соответствует контракт")
        else:
            print("⚠️  Несоответствие количества контрактов и принятых откликов")

        conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    check_contracts()