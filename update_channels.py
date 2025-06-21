# Создайте файл update_channels.py для обновления данных:

import sqlite3
import requests
import time

# Ваш токен бота
BOT_TOKEN = "6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8"

def get_telegram_channel_info(username):
    """Получение информации о канале через Telegram API"""
    try:
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Получаем основную информацию
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        response = requests.get(url, params={'chat_id': f'@{username}'}, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} для @{username}")
            return None
            
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ API ошибка для @{username}: {data.get('description', 'Unknown error')}")
            return None
        
        chat_info = data['result']
        
        # Получаем количество участников
        members_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount"
        members_response = requests.get(members_url, params={'chat_id': f'@{username}'}, timeout=10)
        
        member_count = 0
        if members_response.status_code == 200:
            members_data = members_response.json()
            if members_data.get('ok'):
                member_count = members_data['result']
        
        print(f"✅ @{username}: {member_count} подписчиков")
        
        return {
            'title': chat_info.get('title', ''),
            'description': chat_info.get('description', ''),
            'member_count': member_count,
            'type': chat_info.get('type')
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения данных для @{username}: {e}")
        return None

def update_channels_subscribers():
    """Обновление количества подписчиков для всех каналов"""
    try:
        conn = sqlite3.connect('telegram_mini_app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем все каналы
        cursor.execute("SELECT id, username, title, subscriber_count FROM channels")
        channels = cursor.fetchall()
        
        print(f"🔄 Обновление данных для {len(channels)} каналов...")
        
        updated_count = 0
        
        for channel in channels:
            channel_id = channel['id']
            username = channel['username']
            current_count = channel['subscriber_count']
            
            if not username:
                print(f"⚠️ Канал {channel_id} без username, пропускаем")
                continue
            
            print(f"\n🔍 Обрабатываем канал: {channel['title']} (@{username})")
            print(f"   Текущие подписчики в БД: {current_count}")
            
            # Получаем актуальные данные
            telegram_info = get_telegram_channel_info(username)
            
            if telegram_info and telegram_info['member_count'] > 0:
                new_count = telegram_info['member_count']
                
                # Обновляем в базе
                cursor.execute("""
                    UPDATE channels 
                    SET subscriber_count = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_count, channel_id))
                
                print(f"   ✅ Обновлено: {current_count} → {new_count}")
                updated_count += 1
                
            else:
                print(f"   ❌ Не удалось получить данные")
            
            # Задержка между запросами
            time.sleep(1)
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 Обновление завершено!")
        print(f"✅ Обновлено каналов: {updated_count}")
        
    except Exception as e:
        print(f"❌ Ошибка обновления: {e}")

if __name__ == "__main__":
    print("🚀 Запуск обновления данных каналов...")
    update_channels_subscribers()
    print("\n📊 Проверка результатов:")
    
    # Импортируем и запускаем проверку
    import sys
    sys.path.append('.')
    
    try:
        from check_db import check_channels_data
        check_channels_data()
    except:
        print("❌ Не удалось запустить проверку БД")