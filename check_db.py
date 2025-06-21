# Создайте файл check_db.py для проверки данных в БД:

import sqlite3

def check_channels_data():
    """Проверка данных каналов в базе"""
    try:
        conn = sqlite3.connect('telegram_mini_app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("🔍 Проверка структуры таблицы channels:")
        cursor.execute("PRAGMA table_info(channels)")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"   {col['name']}: {col['type']} (NOT NULL: {col['notnull']})")
        
        print("\n📊 Данные каналов:")
        cursor.execute("SELECT id, title, username, subscriber_count FROM channels LIMIT 5")
        channels = cursor.fetchall()
        
        if not channels:
            print("   ❌ Каналы не найдены!")
        else:
            for channel in channels:
                print(f"   ID: {channel['id']}")
                print(f"   Название: {channel['title']}")
                print(f"   Username: {channel['username']}")
                print(f"   Подписчики: {channel['subscriber_count']} (тип: {type(channel['subscriber_count'])})")
                print("   " + "-" * 40)
        
        # Проверяем все каналы на null значения
        cursor.execute("SELECT COUNT(*) FROM channels WHERE subscriber_count IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"\n🚨 Каналов с NULL subscriber_count: {null_count}")
        
        cursor.execute("SELECT COUNT(*) FROM channels WHERE subscriber_count = 0")
        zero_count = cursor.fetchone()[0]
        print(f"⚠️ Каналов с subscriber_count = 0: {zero_count}")
        
        cursor.execute("SELECT COUNT(*) FROM channels WHERE subscriber_count > 0")
        positive_count = cursor.fetchone()[0]
        print(f"✅ Каналов с subscriber_count > 0: {positive_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")

if __name__ == "__main__":
    check_channels_data()