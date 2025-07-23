# app/performance/__init__.py
"""
Модуль оптимизации производительности для Telegram Mini App
Содержит кэширование, мониторинг и оптимизацию запросов
"""

from .caching import setup_caching, cached, cache_manager
from .monitoring import setup_performance_monitoring, monitor_performance
from .database_optimizer import DatabaseOptimizer, optimize_query, setup_database_optimization

__all__ = [
    'setup_caching',
    'cached', 
    'cache_manager',
    'setup_performance_monitoring',
    'monitor_performance',
    'DatabaseOptimizer',
    'optimize_query',
    'setup_database_optimization'
]