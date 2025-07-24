#!/usr/bin/env python3
"""
Калькулятор комиссий
Расчет комиссий и сборов системы
"""

import logging
from typing import Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)

class CommissionCalculator:
    """Калькулятор комиссий"""
    
    def __init__(self):
        self.commission_rates = {
            'placement': 0.05,      # 5% с размещений
            'withdrawal': 0.02,     # 2% с выводов
            'payment_processing': 0.029  # 2.9% за обработку платежей
        }
    
    def calculate_placement_commission(self, amount: Decimal) -> Dict[str, Any]:
        """Расчет комиссии с размещения"""
        try:
            commission = amount * Decimal(str(self.commission_rates['placement']))
            net_amount = amount - commission
            
            return {
                'gross_amount': float(amount),
                'commission': float(commission),
                'net_amount': float(net_amount),
                'commission_rate': self.commission_rates['placement']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета комиссии: {e}")
            return {'gross_amount': 0, 'commission': 0, 'net_amount': 0}
    
    def calculate_withdrawal_fee(self, amount: Decimal) -> Dict[str, Any]:
        """Расчет комиссии за вывод"""
        try:
            fee = amount * Decimal(str(self.commission_rates['withdrawal']))
            net_amount = amount - fee
            
            return {
                'requested_amount': float(amount),
                'withdrawal_fee': float(fee),
                'net_amount': float(net_amount),
                'fee_rate': self.commission_rates['withdrawal']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета комиссии за вывод: {e}")
            return {'requested_amount': 0, 'withdrawal_fee': 0, 'net_amount': 0}