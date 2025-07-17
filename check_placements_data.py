#!/usr/bin/env python3
"""
Проверка данных размещений
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import execute_db_query

def check_placements_data():
    """Проверка данных размещений"""
    
    print("🔍 Проверка данных размещений")
    print("=" * 50)
    
    try:
        # 1. Посмотрим все размещения
        all_placements = execute_db_query("""
            SELECT p.id, p.status, p.created_at, p.post_url,
                   pr.status as proposal_status,
                   c.title as channel_title, c.username as channel_username,
                   u.telegram_id as owner_telegram_id
            FROM offer_placements p
            JOIN offer_proposals pr ON p.proposal_id = pr.id
            JOIN channels c ON pr.channel_id = c.id
            JOIN users u ON c.owner_id = u.id
            ORDER BY p.created_at DESC
            LIMIT 10
        """, fetch_all=True)
        
        print(f"📊 Найдено размещений: {len(all_placements)}")
        print("\nПоследние 10 размещений:")
        for placement in all_placements:
            print(f"  ID: {placement['id']}, Status: {placement['status']}, "
                  f"Proposal: {placement['proposal_status']}, "
                  f"Channel: @{placement['channel_username']}, "
                  f"Owner TG ID: {placement['owner_telegram_id']}")
        
        # 2. Найдем размещения, готовые к подтверждению
        pending_placements = execute_db_query("""
            SELECT p.id, p.status, p.created_at,
                   pr.status as proposal_status,
                   c.title as channel_title, c.username as channel_username,
                   u.telegram_id as owner_telegram_id
            FROM offer_placements p
            JOIN offer_proposals pr ON p.proposal_id = pr.id
            JOIN channels c ON pr.channel_id = c.id
            JOIN users u ON c.owner_id = u.id
            WHERE p.status IN ('pending', 'pending_placement')
            AND pr.status = 'accepted'
        """, fetch_all=True)
        
        print(f"\n📋 Размещений готовых к подтверждению: {len(pending_placements)}")
        for placement in pending_placements:
            print(f"  ID: {placement['id']}, Owner TG ID: {placement['owner_telegram_id']}, "
                  f"Channel: @{placement['channel_username']}")
        
        # 3. Посмотрим статусы предложений
        proposal_statuses = execute_db_query("""
            SELECT status, COUNT(*) as count
            FROM offer_proposals
            GROUP BY status
        """, fetch_all=True)
        
        print(f"\n📊 Статусы предложений:")
        for status in proposal_statuses:
            print(f"  {status['status']}: {status['count']}")
        
        # 4. Статусы размещений
        placement_statuses = execute_db_query("""
            SELECT status, COUNT(*) as count
            FROM offer_placements
            GROUP BY status
        """, fetch_all=True)
        
        print(f"\n📊 Статусы размещений:")
        for status in placement_statuses:
            print(f"  {status['status']}: {status['count']}")
            
        # 5. Если нет pending, давайте создадим тестовый
        if not pending_placements:
            print(f"\n🛠️ Создаем тестовое размещение для пользователя 373086959")
            
            # Найдем accepted proposal
            accepted_proposal = execute_db_query("""
                SELECT pr.id, c.owner_id, u.telegram_id
                FROM offer_proposals pr
                JOIN channels c ON pr.channel_id = c.id
                JOIN users u ON c.owner_id = u.id
                WHERE pr.status = 'accepted'
                AND u.telegram_id = 373086959
                LIMIT 1
            """, fetch_one=True)
            
            if accepted_proposal:
                # Создаем тестовое размещение
                placement_id = execute_db_query("""
                    INSERT INTO offer_placements (proposal_id, status, created_at)
                    VALUES (?, 'pending', CURRENT_TIMESTAMP)
                """, (accepted_proposal['id'],))
                
                print(f"✅ Создано тестовое размещение с ID: {placement_id}")
            else:
                print(f"❌ Не найдено принятых предложений для пользователя 373086959")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    check_placements_data()