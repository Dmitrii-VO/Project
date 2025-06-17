#!/usr/bin/env python3
"""
Скрипт проверки структуры базы данных (исправленный)
"""

import sqlite3
import os

DATABASE_PATH = 'telegram_mini_app.db'


def check_database():
    """Проверка структуры базы данных"""

    print("🔍 ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("=" * 50)

    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return False

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Проверяем конкретно каналы и пользователей
        print(f"\n🔍 ДЕТАЛИ ТАБЛИЦЫ CHANNELS:")
        print("-" * 30)

        cursor.execute("SELECT * FROM channels LIMIT 5")
        channels = cursor.fetchall()

        if channels:
            print("Каналы в БД:")
            for ch in channels:
                # Исправленное обращение к sqlite3.Row
                print(f"  ID: {ch['id']}, Title: {ch['title'] or 'N/A'}, Owner: {ch['owner_id'] or 'N/A'}")
                print(f"       Username: @{ch['username'] or 'N/A'}, Verified: {ch['is_verified']}")
        else:
            print("Каналов не найдено")

        print(f"\n👥 ДЕТАЛИ ТАБЛИЦЫ USERS:")
        print("-" * 30)

        cursor.execute("SELECT * FROM users LIMIT 5")
        users = cursor.fetchall()

        if users:
            print("Пользователи в БД:")
            for user in users:
                print(f"  ID: {user['id']}, Telegram ID: {user['telegram_id']}")
                print(f"       Username: {user['username'] or 'N/A'}, Name: {user['first_name'] or 'N/A'}")
        else:
            print("Пользователей не найдено")

        # Проверяем связь каналов и пользователей
        print(f"\n🔗 ПРОВЕРКА СВЯЗЕЙ:")
        print("-" * 30)

        cursor.execute('''
                       SELECT c.id as channel_id, c.title, u.telegram_id, u.username as user_username
                       FROM channels c
                                JOIN users u ON c.owner_id = u.id
                       ''')

        relations = cursor.fetchall()
        if relations:
            print("Связи каналов с пользователями:")
            for rel in relations:
                print(
                    f"  Канал {rel['channel_id']} ({rel['title']}) -> Пользователь {rel['telegram_id']} (@{rel['user_username'] or 'N/A'})")
        else:
            print("Связей не найдено")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    check_database()