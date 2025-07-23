# app/performance/database_optimizer.py
"""
Оптимизатор базы данных для Telegram Mini App
Содержит индексы, оптимизированные запросы и исправления N+1 проблем
"""

import sqlite3
import time
from typing import List, Dict, Any, Optional, Tuple
from flask import Flask, current_app, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """
    Класс для оптимизации базы данных
    """
    
    def __init__(self, app: Flask = None, db_path: str = None):
        self.app = app
        self.db_path = db_path or 'telegram_mini_app.db'
        self.slow_query_threshold = 0.1  # 100ms
        self.query_stats = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация оптимизатора"""
        self.app = app
        self.db_path = app.config.get('DATABASE_PATH', self.db_path)
        
        # Создаем необходимые индексы
        self.create_performance_indexes()
        
        # Настраиваем оптимизации SQLite
        self.configure_sqlite_optimizations()
        
        app.extensions['db_optimizer'] = self
        logger.info("✅ Database Optimizer initialized")
    
    def create_performance_indexes(self):
        """Создание индексов для улучшения производительности"""
        indexes = [
            # Основные индексы для поиска
            ("idx_users_telegram_id", "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)"),
            ("idx_channels_owner_active", "CREATE INDEX IF NOT EXISTS idx_channels_owner_active ON channels(owner_id, is_active)"),
            ("idx_channels_category_verified", "CREATE INDEX IF NOT EXISTS idx_channels_category_verified ON channels(category, is_verified)"),
            ("idx_channels_search", "CREATE INDEX IF NOT EXISTS idx_channels_search ON channels(title, username)"),
            
            # Индексы для офферов
            ("idx_offers_creator_status", "CREATE INDEX IF NOT EXISTS idx_offers_creator_status ON offers(creator_id, status)"),
            ("idx_offers_status_created", "CREATE INDEX IF NOT EXISTS idx_offers_status_created ON offers(status, created_at)"),
            ("idx_offers_category", "CREATE INDEX IF NOT EXISTS idx_offers_category ON offers(category)"),
            
            # Индексы для предложений
            ("idx_offer_proposals_channel_status", "CREATE INDEX IF NOT EXISTS idx_offer_proposals_channel_status ON offer_proposals(channel_id, status)"),
            ("idx_offer_proposals_offer_id", "CREATE INDEX IF NOT EXISTS idx_offer_proposals_offer_id ON offer_proposals(offer_id)"),
            ("idx_offer_proposals_created", "CREATE INDEX IF NOT EXISTS idx_offer_proposals_created ON offer_proposals(created_at)"),
            
            # Индексы для логов безопасности
            ("idx_security_logs_user_time", "CREATE INDEX IF NOT EXISTS idx_security_logs_user_time ON security_audit_logs(user_id, timestamp)"),
            ("idx_security_logs_risk", "CREATE INDEX IF NOT EXISTS idx_security_logs_risk ON security_audit_logs(risk_level, timestamp)"),
            ("idx_suspicious_activity_user", "CREATE INDEX IF NOT EXISTS idx_suspicious_activity_user ON suspicious_activity(user_id, created_at)"),
            
            # Составные индексы для сложных запросов
            ("idx_channels_owner_verified_active", "CREATE INDEX IF NOT EXISTS idx_channels_owner_verified_active ON channels(owner_id, is_verified, is_active)"),
            ("idx_offers_creator_category_status", "CREATE INDEX IF NOT EXISTS idx_offers_creator_category_status ON offers(creator_id, category, status)")
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            created_indexes = []
            for name, sql in indexes:
                try:
                    cursor.execute(sql)
                    created_indexes.append(name)
                except sqlite3.Error as e:
                    logger.warning(f"Failed to create index {name}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Created {len(created_indexes)} database indexes")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
    
    def configure_sqlite_optimizations(self):
        """Настройка оптимизаций SQLite"""
        optimizations = [
            "PRAGMA journal_mode = WAL",           # Write-Ahead Logging для лучшей производительности
            "PRAGMA synchronous = NORMAL",         # Балансируем безопасность и скорость
            "PRAGMA cache_size = 10000",           # Увеличиваем размер кэша
            "PRAGMA temp_store = MEMORY",          # Временные таблицы в памяти
            "PRAGMA mmap_size = 268435456",        # 256MB memory-mapped I/O
            "PRAGMA optimize"                      # Автоматическая оптимизация
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for pragma in optimizations:
                try:
                    cursor.execute(pragma)
                except sqlite3.Error as e:
                    logger.warning(f"Failed to execute {pragma}: {e}")
            
            conn.close()
            logger.info("✅ SQLite optimizations configured")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure SQLite optimizations: {e}")
    
    def get_optimized_channels_query(self, user_id: str = None, include_stats: bool = True) -> str:
        """
        Оптимизированный запрос для получения каналов (исправляет N+1 проблему)
        """
        base_query = """
        SELECT 
            c.*,
            u.first_name as owner_name,
            u.username as owner_username
        """
        
        if include_stats:
            base_query += """,
            COALESCE(oc.offers_count, 0) as offers_count,
            COALESCE(pc.posts_count, 0) as posts_count,
            COALESCE(rc.responses_count, 0) as responses_count
            """
        
        base_query += """
        FROM channels c
        LEFT JOIN users u ON c.owner_id = u.id
        """
        
        if include_stats:
            base_query += """
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as offers_count 
                FROM offers 
                WHERE status = 'active'
                GROUP BY channel_id
            ) oc ON c.id = oc.channel_id
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as posts_count 
                FROM channel_posts 
                GROUP BY channel_id
            ) pc ON c.id = pc.channel_id
            LEFT JOIN (
                SELECT channel_id, COUNT(*) as responses_count 
                FROM offer_responses 
                GROUP BY channel_id
            ) rc ON c.id = rc.channel_id
            """
        
        if user_id:
            base_query += " WHERE c.owner_id = ?"
        
        base_query += " ORDER BY c.created_at DESC"
        
        return base_query
    
    def get_optimized_offers_query(self, user_id: str = None, status: str = None) -> str:
        """
        Оптимизированный запрос для получения офферов
        """
        query = """
        SELECT 
            o.*,
            u.first_name as creator_name,
            COUNT(DISTINCT op.id) as proposals_count,
            COUNT(DISTINCT CASE WHEN op.status = 'accepted' THEN op.id END) as accepted_proposals,
            COUNT(DISTINCT CASE WHEN op.status = 'rejected' THEN op.id END) as rejected_proposals
        FROM offers o
        LEFT JOIN users u ON o.creator_id = u.id
        LEFT JOIN offer_proposals op ON o.id = op.offer_id
        WHERE 1=1
        """
        
        if user_id:
            query += " AND o.creator_id = ?"
        
        if status:
            query += " AND o.status = ?"
        
        query += """
        GROUP BY o.id, u.first_name
        ORDER BY o.created_at DESC
        """
        
        return query
    
    def get_optimized_proposals_query(self, channel_id: str = None, user_id: str = None) -> str:
        """
        Оптимизированный запрос для получения предложений
        """
        query = """
        SELECT 
            op.*,
            o.title as offer_title,
            o.description as offer_description,  
            o.budget_total,
            o.category,
            u.first_name as advertiser_name,
            c.title as channel_title,
            c.username as channel_username
        FROM offer_proposals op
        LEFT JOIN offers o ON op.offer_id = o.id
        LEFT JOIN users u ON o.creator_id = u.id
        LEFT JOIN channels c ON op.channel_id = c.id
        WHERE 1=1
        """
        
        if channel_id:
            query += " AND op.channel_id = ?"
        
        if user_id:
            query += " AND c.owner_id = ?"
        
        query += " ORDER BY op.created_at DESC"
        
        return query
    
    def analyze_query_performance(self, query: str, params: tuple = ()) -> Dict[str, Any]:
        """
        Анализ производительности запроса
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем план выполнения запроса
            explain_query = f"EXPLAIN QUERY PLAN {query}"
            cursor.execute(explain_query, params)
            query_plan = cursor.fetchall()
            
            # Измеряем время выполнения
            start_time = time.time()
            cursor.execute(query, params)
            results = cursor.fetchall()
            execution_time = time.time() - start_time
            
            conn.close()
            
            analysis = {
                'execution_time': execution_time,
                'rows_returned': len(results),
                'query_plan': [
                    {
                        'id': row[0],
                        'parent': row[1], 
                        'detail': row[3]
                    } for row in query_plan
                ],
                'performance_rating': self._rate_query_performance(execution_time, len(results))
            }
            
            # Сохраняем статистику
            query_hash = hash(query)
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = {
                    'query': query[:100] + '...' if len(query) > 100 else query,
                    'executions': 0,
                    'total_time': 0,
                    'avg_time': 0
                }
            
            stats = self.query_stats[query_hash]
            stats['executions'] += 1
            stats['total_time'] += execution_time
            stats['avg_time'] = stats['total_time'] / stats['executions']
            
            return analysis
            
        except Exception as e:
            logger.error(f"Query analysis error: {e}")
            return {'error': str(e)}
    
    def _rate_query_performance(self, execution_time: float, rows_returned: int) -> str:
        """Оценка производительности запроса"""
        if execution_time < 0.01:
            return "excellent"
        elif execution_time < 0.05:
            return "good"
        elif execution_time < 0.1:
            return "fair"
        elif execution_time < 0.5:
            return "poor"
        else:
            return "very_poor"
    
    def get_slow_queries_report(self) -> List[Dict[str, Any]]:
        """Отчет по медленным запросам"""
        slow_queries = [
            {
                'query': stats['query'],
                'executions': stats['executions'],
                'avg_time': round(stats['avg_time'], 4),
                'total_time': round(stats['total_time'], 4)
            }
            for stats in self.query_stats.values()
            if stats['avg_time'] > self.slow_query_threshold
        ]
        
        return sorted(slow_queries, key=lambda x: x['avg_time'], reverse=True)
    
    def optimize_database_maintenance(self):
        """Выполнение операций по обслуживанию БД"""
        maintenance_queries = [
            "VACUUM",                    # Дефрагментация БД
            "REINDEX",                   # Перестроение индексов
            "ANALYZE",                   # Обновление статистики
            "PRAGMA optimize"            # Автоматическая оптимизация
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for query in maintenance_queries:
                start_time = time.time()
                cursor.execute(query)
                execution_time = time.time() - start_time
                logger.info(f"Maintenance: {query} completed in {execution_time:.3f}s")
            
            conn.close()
            logger.info("✅ Database maintenance completed")
            
        except Exception as e:
            logger.error(f"❌ Database maintenance failed: {e}")

def optimize_query(threshold_ms: int = 100):
    """
    Декоратор для мониторинга и оптимизации запросов
    
    Args:
        threshold_ms: Порог времени выполнения в миллисекундах для логирования
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Логируем медленные запросы
                if execution_time * 1000 > threshold_ms:
                    logger.warning(
                        f"Slow query in {f.__name__}: {execution_time*1000:.1f}ms "
                        f"Args: {args[:2]}{'...' if len(args) > 2 else ''}"
                    )
                
                # Сохраняем статистику
                optimizer = current_app.extensions.get('db_optimizer')
                if optimizer:
                    query_hash = hash(f.__name__)
                    if query_hash not in optimizer.query_stats:
                        optimizer.query_stats[query_hash] = {
                            'query': f.__name__,
                            'executions': 0,
                            'total_time': 0,
                            'avg_time': 0
                        }
                    
                    stats = optimizer.query_stats[query_hash]
                    stats['executions'] += 1
                    stats['total_time'] += execution_time
                    stats['avg_time'] = stats['total_time'] / stats['executions']
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Query error in {f.__name__} after {execution_time*1000:.1f}ms: {e}")
                raise
                
        return wrapper
    return decorator

def setup_database_optimization(app: Flask) -> DatabaseOptimizer:
    """Настройка оптимизации базы данных"""
    db_optimizer = DatabaseOptimizer(app)
    
    # Добавляем endpoints для мониторинга
    @app.route('/api/db/performance', methods=['GET'])
    def db_performance():
        """Статистика производительности БД (только для администратора)"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            slow_queries = db_optimizer.get_slow_queries_report()
            
            return {
                'success': True,
                'slow_queries': slow_queries,
                'total_queries_tracked': len(db_optimizer.query_stats),
                'slow_query_threshold': db_optimizer.slow_query_threshold
            }
        except Exception as e:
            logger.error(f"DB performance error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    @app.route('/api/db/maintenance', methods=['POST'])
    def db_maintenance():
        """Запуск обслуживания БД (только для администратора)"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            db_optimizer.optimize_database_maintenance()
            return {
                'success': True,
                'message': 'Database maintenance completed successfully'
            }
        except Exception as e:
            logger.error(f"DB maintenance error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    logger.info("✅ Database optimization configured")
    return db_optimizer

logger.info("✅ Database Optimizer module initialized")