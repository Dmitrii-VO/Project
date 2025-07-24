#!/usr/bin/env python3
"""
Процессор выплат
Обработка выплат владельцам каналов
"""

import logging
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal

from app.models.database import execute_db_query
from app.events.event_dispatcher import event_dispatcher

logger = logging.getLogger(__name__)

class PayoutProcessor:
    """Процессор выплат"""
    
    def __init__(self):
        self.min_payout_amount = Decimal('100')
    
    def process_payout(self, user_id: int, amount: Decimal, 
                      payout_method: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка выплаты"""
        try:
            if amount < self.min_payout_amount:
                return {
                    'success': False, 
                    'error': f'Минимальная сумма выплаты {self.min_payout_amount} руб.'
                }
            
            payout_id = execute_db_query(
                """INSERT INTO payouts 
                   (user_id, amount, payout_method, details, status, created_at)
                   VALUES (?, ?, ?, ?, 'pending', ?)""",
                (user_id, float(amount), payout_method, str(details), datetime.now())
            )
            
            return {
                'success': True,
                'payout_id': payout_id,
                'amount': float(amount),
                'status': 'pending'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выплаты: {e}")
            return {'success': False, 'error': str(e)}