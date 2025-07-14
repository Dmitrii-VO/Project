#!/usr/bin/env python3
"""
Тестируем логику рекомендаций каналов
"""
import sqlite3

conn = sqlite3.connect("/mnt/d/Project/telegram_mini_app.db")
cursor = conn.cursor()

offer_id = 4

cursor.execute("SELECT id, title, category, created_by FROM offers WHERE id = ?", (offer_id,))
offer = cursor.fetchone()

print("Оффер ID:", offer[0])
print("Создан пользователем:", offer[3])

cursor.execute("SELECT id, title, owner_id FROM channels WHERE is_verified = 1")
all_channels = cursor.fetchall()
print("Все верифицированные каналы:")
for ch in all_channels:
    print("  Channel", ch[0], ":", ch[1], "(owner:", ch[2], ")")

print("Фильтруем каналы где owner_id не равен", offer[3])
filtered = []
for ch in all_channels:
    if ch[2] != offer[3]:
        filtered.append(ch)
        
print("Найдено рекомендуемых каналов:", len(filtered))
for channel in filtered:
    print("  ID:", channel[0], ", Title:", channel[1], ", Owner:", channel[2])

conn.close()