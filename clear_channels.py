#!/usr/bin/env python3
"""
Скрипт для очистки таблицы каналов
Удаляет все каналы из базы данных для тестирования новой системы модерации
"""

import os
import sqlite3
from datetime import datetime

DATABASE_PATH = 'telegram_mini_app.db'


def clear_channels_table():
    """Очистка таблицы каналов"""

    print("🗑️ ОЧИСТКА ТАБЛИЦЫ КАНАЛОВ")
    print("=" * 50)

    # Проверяем существование базы данных
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return False

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Включаем foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')

        # Проверяем количество каналов до удаления
        cursor.execute("SELECT COUNT(*) FROM channels")
        channels_before = cursor.fetchone()[0]

        print(f"📊 Каналов в базе до очистки: {channels_before}")

        if channels_before == 0:
            print("✅ Таблица каналов уже пуста")
            conn.close()
            return True

        # Получаем информацию о каналах для логирования
        cursor.execute("""
                       SELECT id, telegram_id, title, is_verified
                       FROM channels
                       ORDER BY created_at
                       """)
        channels_info = cursor.fetchall()

        print("\n📋 КАНАЛЫ ДЛЯ УДАЛЕНИЯ:")
        print("-" * 50)
        for channel in channels_info:
            status = "✅ Верифицирован" if channel[3] else "⏳ Не верифицирован"
            telegram_id = channel[1] if channel[1] else "Нет ID"
            title = channel[2] if channel[2] else "Без названия"
            print(f"  ID: {channel[0]:<3} | {telegram_id:<15} | {title:<20} | {status}")

        # Запрашиваем подтверждение
        print(f"\n⚠️ ВНИМАНИЕ: Будет удалено {channels_before} каналов!")
        print("Это действие необратимо.")

        confirm = input("\nПродолжить? (y/N): ").lower().strip()

        if confirm not in ['y', 'yes', 'да']:
            print("❌ Операция отменена")
            conn.close()
            return False

        # Удаляем связанные данные (если есть)
        print("\n🔄 Удаление связанных данных...")

        # Удаляем связи каналов с офферами (проверяем существование таблицы)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channel_offers'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM channel_offers WHERE channel_id IN (SELECT id FROM channels)")
            deleted_channel_offers = cursor.rowcount
            print(f"  🗑️ Удалено связей с офферами: {deleted_channel_offers}")
        else:
            print("  ℹ️ Таблица channel_offers не найдена")
            deleted_channel_offers = 0

        # Удаляем ответы на офферы связанные с каналами
        cursor.execute("""
                       DELETE
                       FROM offer_responses
                       WHERE offer_id IN (SELECT id
                                          FROM offers
                                          WHERE channel_id IN (SELECT id FROM channels))
                       """)
        deleted_responses = cursor.rowcount
        print(f"  🗑️ Удалено ответов на офферы: {deleted_responses}")

        # Удаляем офферы связанные с каналами
        cursor.execute("DELETE FROM offers WHERE channel_id IN (SELECT id FROM channels)")
        deleted_offers = cursor.rowcount
        print(f"  🗑️ Удалено офферов: {deleted_offers}")

        # Удаляем уведомления связанные с каналами (если есть)
        try:
            cursor.execute("""
                           DELETE
                           FROM notifications
                           WHERE data LIKE '%channel_id%'
                             AND json_extract(data, '$.channel_id') IN (SELECT id FROM channels)
                           """)
            deleted_notifications = cursor.rowcount
            print(f"  🗑️ Удалено уведомлений: {deleted_notifications}")
        except:
            print("  ℹ️ Таблица уведомлений не найдена или не содержит связанных данных")

        # Удаляем все каналы
        print("\n🗑️ Удаление каналов...")
        cursor.execute("DELETE FROM channels")
        deleted_channels = cursor.rowcount

        # Сбрасываем автоинкремент
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='channels'")

        # Подтверждаем изменения
        conn.commit()

        # Проверяем результат
        cursor.execute("SELECT COUNT(*) FROM channels")
        channels_after = cursor.fetchone()[0]

        print(f"\n✅ ОПЕРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 50)
        print(f"📊 Каналов удалено: {deleted_channels}")
        print(f"📊 Каналов осталось: {channels_after}")
        print(f"📊 Связанных офферов удалено: {deleted_offers}")
        print(f"📊 Ответов на офферы удалено: {deleted_responses}")
        print(f"📊 Связей с офферами удалено: {deleted_channel_offers}")

        if channels_after == 0:
            print("✅ Таблица каналов успешно очищена")
            print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
            print("1. Перезапустите приложение: python working_app.py")
            print("2. Добавьте новые каналы через интерфейс")
            print("3. Протестируйте новую систему автоматической модерации")
        else:
            print(f"⚠️ Остались каналы: {channels_after}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        if 'conn' in locals():
            conn.close()
        return False


def verify_cleanup():
    """Проверка результатов очистки"""
    print("\n🔍 ПРОВЕРКА РЕЗУЛЬТАТОВ")
    print("=" * 50)

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Проверяем таблицы
        tables_to_check = [
            ('channels', 'Каналы'),
            ('offers', 'Офферы'),
            ('offer_responses', 'Ответы на офферы'),
            ('channel_offers', 'Связи каналов с офферами'),
            ('notifications', 'Уведомления'),
            ('users', 'Пользователи')
        ]

        for table_name, table_desc in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"📊 {table_desc:<25}: {count} записей")
            except sqlite3.Error:
                print(f"⚠️ {table_desc:<25}: таблица не найдена")

        conn.close()

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")


def main():
    """Главная функция"""
    print("🔄 СКРИПТ ОЧИСТКИ КАНАЛОВ")
    print("Версия для тестирования новой системы автоматической модерации")
    print("=" * 70)

    # Очищаем таблицу каналов
    success = clear_channels_table()

    if success:
        # Проверяем результаты
        verify_cleanup()

        print(f"\n🎉 ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 70)
        print("✅ База данных готова для тестирования новой системы модерации")
        print("✅ Все каналы удалены")
        print("✅ Связанные данные очищены")
        print("\n📝 РЕКОМЕНДАЦИИ:")
        print("• Перезапустите приложение для применения изменений")
        print("• Добавьте тестовые каналы через интерфейс")
        print("• Проверьте работу автоматической верификации")

    else:
        print(f"\n❌ ОШИБКА ОЧИСТКИ")
        print("=" * 70)
        print("Проверьте сообщения об ошибках выше")
        print("Убедитесь, что база данных не используется другими процессами")


if __name__ == '__main__':
    main()