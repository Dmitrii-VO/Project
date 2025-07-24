#!/usr/bin/env python3
"""
Системный мониторинг
Мониторинг состояния и производительности системы
"""

import logging
import psutil
import os
from typing import Dict, Any
from datetime import datetime, timedelta

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Системный монитор"""
    
    def __init__(self):
        pass
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Получение системной статистики"""
        try:
            # CPU статистика
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Память
            memory = psutil.virtual_memory()
            
            # Диск
            disk = psutil.disk_usage('/')
            
            # Процессы
            process_count = len(psutil.pids())
            
            return {
                'success': True,
                'data': {
                    'cpu': {
                        'usage_percent': cpu_percent,
                        'cpu_count': cpu_count
                    },
                    'memory': {
                        'total': memory.total,
                        'available': memory.available,
                        'used': memory.used,
                        'usage_percent': memory.percent
                    },
                    'disk': {
                        'total': disk.total,
                        'used': disk.used,
                        'free': disk.free,
                        'usage_percent': (disk.used / disk.total) * 100
                    },
                    'processes': {
                        'count': process_count
                    },
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения системной статистики: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Получение статистики базы данных"""
        try:
            # Статистика таблиц
            tables_stats = {
                'users': self._get_table_count('users'),
                'channels': self._get_table_count('channels'),
                'offers': self._get_table_count('offers'),
                'offer_placements': self._get_table_count('offer_placements')
            }
            
            # Размер базы данных
            db_path = 'telegram_mini_app.db'
            db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            
            return {
                'success': True,
                'data': {
                    'tables': tables_stats,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики БД: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_table_count(self, table_name: str) -> int:
        """Получение количества записей в таблице"""
        try:
            result = execute_db_query(
                f"SELECT COUNT(*) as count FROM {table_name}",
                fetch_one=True
            )
            return result['count'] if result else 0
        except:
            return 0
    
    def get_application_health(self) -> Dict[str, Any]:
        """Проверка состояния приложения"""
        try:
            health_checks = {
                'database': self._check_database_health(),
                'disk_space': self._check_disk_space(),
                'memory': self._check_memory_usage()
            }
            
            # Общий статус
            overall_status = 'healthy' if all(
                check['status'] == 'ok' for check in health_checks.values()
            ) else 'warning'
            
            return {
                'success': True,
                'data': {
                    'overall_status': overall_status,
                    'checks': health_checks,
                    'checked_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки здоровья: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Проверка состояния базы данных"""
        try:
            # Простой запрос для проверки соединения
            execute_db_query("SELECT 1", fetch_one=True)
            return {'status': 'ok', 'message': 'База данных доступна'}
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка БД: {e}'}
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Проверка дискового пространства"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 90:
                status = 'critical'
                message = f'Критически мало места: {usage_percent:.1f}%'
            elif usage_percent > 80:
                status = 'warning'
                message = f'Мало места на диске: {usage_percent:.1f}%'
            else:
                status = 'ok'
                message = f'Место на диске: {usage_percent:.1f}%'
                
            return {'status': status, 'message': message}
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка проверки диска: {e}'}
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Проверка использования памяти"""
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                status = 'critical'
                message = f'Критически мало памяти: {memory.percent:.1f}%'
            elif memory.percent > 80:
                status = 'warning'
                message = f'Высокое использование памяти: {memory.percent:.1f}%'
            else:
                status = 'ok'
                message = f'Использование памяти: {memory.percent:.1f}%'
                
            return {'status': status, 'message': message}
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка проверки памяти: {e}'}