import sqlite3

DATABASE_PATH = 'telegram_mini_app.db'


def check_channels_table():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Проверяем структуру таблицы channels
        cursor.execute("PRAGMA table_info(channels)")
        columns = cursor.fetchall()

        print("📋 СТРУКТУРА ТАБЛИЦЫ CHANNELS:")
        print("-" * 60)
        for column in columns:
            print(
                f"  {column[1]:<25} {column[2]:<15} {'NOT NULL' if column[3] else 'NULL':<10} DEFAULT: {column[4] or 'None'}")

        # Проверяем все таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n📋 ВСЕ ТАБЛИЦЫ В БД:")
        print("-" * 60)
        for table in tables:
            print(f"  ✅ {table[0]}")

        conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    check_channels_table()