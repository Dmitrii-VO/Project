#!/usr/bin/env python3
"""
Менеджер эскроу операций
Управление блокировкой и освобождением средств
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.database import execute_db_query
from app.events.event_dispatcher import event_dispatcher

logger = logging.getLogger(__name__)

class EscrowManager:
    """Менеджер эскроу операций"""
    
    def __init__(self):
        self.default_hold_period = timedelta(days=7)
    
    def create_escrow(self, user_id: int, amount: Decimal, 
                     placement_id: int, description: str = None) -> Dict[str, Any]:
        """Создание эскроу холда"""
        try:
            escrow_id = execute_db_query(
                """INSERT INTO escrow_holds 
                   (user_id, placement_id, amount, status, description, 
                    created_at, release_date)
                   VALUES (?, ?, ?, 'active', ?, ?, ?)""",
                (
                    user_id,
                    placement_id, 
                    float(amount),
                    description or f'Эскроу для размещения {placement_id}',
                    datetime.now(),
                    datetime.now() + self.default_hold_period
                )
            )
            
            return {
                'success': True,
                'escrow_id': escrow_id,
                'amount': float(amount),
                'release_date': (datetime.now() + self.default_hold_period).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания эскроу: {e}")
            return {'success': False, 'error': str(e)}
    
    def release_escrow(self, escrow_id: int, admin_id: int = None) -> Dict[str, Any]:
        """Освобождение средств из эскроу"""
        try:
            # Обновляем статус эскроу
            execute_db_query(
                """UPDATE escrow_holds 
                   SET status = 'released', released_at = ?, released_by = ?
                   WHERE id = ? AND status = 'active'""",
                (datetime.now(), admin_id, escrow_id)
            )
            
            return {'success': True, 'escrow_id': escrow_id}
            
        except Exception as e:
            logger.error(f"❌ Ошибка освобождения эскроу: {e}")
            return {'success': False, 'error': str(e)}