# app/security/audit_logger.py
"""
Аудит и логирование действий пользователей для Telegram Mini App
Трекинг безопасности и мониторинг подозрительной активности
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional, List
from flask import Flask, request, g, session
from functools import wraps
import logging
import sqlite3
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class SecurityAuditLogger:
    """
    Класс для аудита действий пользователей и безопасности
    """
    
    def __init__(self, app: Flask = None, db_path: str = None):
        self.app = app
        self.db_path = db_path or 'telegram_mini_app.db'
        self.suspicious_activity = defaultdict(list)
        self.rate_tracking = defaultdict(lambda: deque(maxlen=100))
        self.lock = threading.Lock()
        
        # Пороги для определения подозрительной активности
        self.thresholds = {
            'failed_auth_attempts': 5,      # За 15 минут
            'rapid_requests': 50,           # За минуту
            'data_breach_attempts': 3,      # За час
            'permission_escalation': 1,     # За день
            'unusual_patterns': 10          # За час
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация аудит логгера"""
        self.app = app
        app.extensions['audit_logger'] = self
        
        # Создаем таблицы для аудита
        self._create_audit_tables()
        
        # Добавляем middleware для трекинга запросов
        app.before_request(self._track_request)
        app.after_request(self._track_response)
        
        logger.info("✅ Security Audit Logger initialized")
    
    def _create_audit_tables(self):
        """Создание таблиц для аудита в базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица для логов безопасности
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    action TEXT NOT NULL,
                    resource TEXT,
                    method TEXT,
                    status_code INTEGER,
                    risk_level TEXT DEFAULT 'low',
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для подозрительной активности
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suspicious_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    ip_address TEXT,
                    activity_type TEXT NOT NULL,
                    severity TEXT DEFAULT 'medium',
                    description TEXT,
                    evidence TEXT,
                    blocked BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для трекинга сессий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    login_time TEXT,
                    last_activity TEXT,
                    logout_time TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для производительности
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON security_audit_logs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_suspicious_user_id ON suspicious_activity(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Audit tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create audit tables: {e}")
    
    def _track_request(self):
        """Трекинг входящих запросов"""
        g.request_start_time = time.time()
        g.user_id = request.headers.get('X-Telegram-User-Id')
        g.ip_address = self._get_client_ip()
        g.session_id = session.get('session_id') if 'session_id' in session else None
        
        # Трекинг частоты запросов
        if g.user_id:
            self._track_request_rate(g.user_id)
    
    def _track_response(self, response):
        """Трекинг ответов сервера"""
        try:
            request_time = time.time() - g.get('request_start_time', time.time())
            
            # Логируем подозрительные статус коды
            if response.status_code in [401, 403, 429, 500]:
                self._log_security_event(
                    action=f"HTTP_{response.status_code}",
                    resource=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    risk_level='medium' if response.status_code in [401, 403, 429] else 'high',
                    details={
                        'response_time': request_time,
                        'content_length': response.content_length,
                        'headers': dict(request.headers)
                    }
                )
            
            # Логируем медленные запросы
            if request_time > 5.0:  # Более 5 секунд
                self._log_security_event(
                    action="SLOW_REQUEST",
                    resource=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    risk_level='low',
                    details={'response_time': request_time}
                )
            
        except Exception as e:
            logger.error(f"Error in response tracking: {e}")
        
        return response
    
    def _get_client_ip(self) -> str:
        """Получение IP адреса клиента"""
        # Проверяем заголовки proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or 'unknown'
    
    def _track_request_rate(self, user_id: str):
        """Трекинг частоты запросов пользователя"""
        current_time = time.time()
        
        with self.lock:
            self.rate_tracking[user_id].append(current_time)
            
            # Проверяем превышение лимитов
            recent_requests = [t for t in self.rate_tracking[user_id] if current_time - t < 60]
            
            if len(recent_requests) > self.thresholds['rapid_requests']:
                self._flag_suspicious_activity(
                    user_id=user_id,
                    activity_type='rapid_requests',
                    severity='high',
                    description=f'User made {len(recent_requests)} requests in 1 minute',
                    evidence={'requests_count': len(recent_requests), 'time_window': 60}
                )
    
    def _log_security_event(self, action: str, resource: str = None, method: str = None,
                          status_code: int = None, risk_level: str = 'low', details: Dict = None):
        """Логирование события безопасности"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_audit_logs 
                (timestamp, user_id, session_id, ip_address, user_agent, action, 
                 resource, method, status_code, risk_level, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                g.get('user_id'),
                g.get('session_id'),
                g.get('ip_address'),
                request.headers.get('User-Agent', ''),
                action,
                resource,
                method,
                status_code,
                risk_level,
                json.dumps(details) if details else None
            ))
            
            conn.commit()
            conn.close()
            
            # Дополнительное логирование для высокорисковых событий
            if risk_level in ['high', 'critical']:
                logger.warning(f"🚨 Security Event: {action} - User: {g.get('user_id')} - IP: {g.get('ip_address')}")
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _flag_suspicious_activity(self, user_id: str, activity_type: str, severity: str,
                                description: str, evidence: Dict = None):
        """Отметка подозрительной активности"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO suspicious_activity 
                (user_id, ip_address, activity_type, severity, description, evidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                g.get('ip_address'),
                activity_type,
                severity,
                description,
                json.dumps(evidence) if evidence else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"🚨 Suspicious Activity: {activity_type} - User: {user_id} - {description}")
            
            # Уведомление администратора при критических событиях
            if severity == 'critical':
                self._notify_admin_suspicious_activity(user_id, activity_type, description)
                
        except Exception as e:
            logger.error(f"Failed to flag suspicious activity: {e}")
    
    def _notify_admin_suspicious_activity(self, user_id: str, activity_type: str, description: str):
        """Уведомление администратора о критической подозрительной активности"""
        try:
            # Отправляем уведомление администратору через Telegram
            admin_message = f"""
🚨 КРИТИЧЕСКАЯ АКТИВНОСТЬ ОБНАРУЖЕНА

👤 Пользователь: {user_id}
🔍 Тип: {activity_type}
📝 Описание: {description}
🕒 Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
🌐 IP: {g.get('ip_address')}

⚡ Требуется немедленная проверка!
            """
            
            # Здесь можно добавить отправку уведомления администратору
            # Используя существующую систему уведомлений проекта
            logger.critical(f"ADMIN NOTIFICATION: {admin_message}")
            
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    def log_user_action(self, action: str, details: Dict = None, risk_level: str = 'low'):
        """Публичный метод для логирования действий пользователя"""
        self._log_security_event(
            action=action,
            resource=request.path if request else None,
            method=request.method if request else None,
            risk_level=risk_level,
            details=details
        )
    
    def log_auth_attempt(self, user_id: str, success: bool, details: Dict = None):
        """Логирование попыток аутентификации"""
        action = "AUTH_SUCCESS" if success else "AUTH_FAILURE"
        risk_level = 'low' if success else 'medium'
        
        self._log_security_event(
            action=action,
            risk_level=risk_level,
            details={
                'success': success,
                'user_id': user_id,
                **(details or {})
            }
        )
        
        # Трекинг неудачных попыток аутентификации
        if not success:
            self._track_failed_auth(user_id)
    
    def _track_failed_auth(self, user_id: str):
        """Трекинг неудачных попыток аутентификации"""
        current_time = time.time()
        
        with self.lock:
            if user_id not in self.suspicious_activity:
                self.suspicious_activity[user_id] = []
            
            # Добавляем текущую неудачную попытку
            self.suspicious_activity[user_id].append(current_time)
            
            # Удаляем старые записи (старше 15 минут)
            cutoff_time = current_time - 900  # 15 минут
            self.suspicious_activity[user_id] = [
                t for t in self.suspicious_activity[user_id] if t > cutoff_time
            ]
            
            # Проверяем превышение порога
            if len(self.suspicious_activity[user_id]) >= self.thresholds['failed_auth_attempts']:
                self._flag_suspicious_activity(
                    user_id=user_id,
                    activity_type='multiple_failed_auth',
                    severity='high',
                    description=f'Multiple failed authentication attempts: {len(self.suspicious_activity[user_id])}',
                    evidence={'attempts': len(self.suspicious_activity[user_id]), 'time_window': 900}
                )
    
    def get_user_activity_summary(self, user_id: str, hours: int = 24) -> Dict:
        """Получение сводки активности пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Активность за последние часы
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT action, COUNT(*) as count, risk_level
                FROM security_audit_logs 
                WHERE user_id = ? AND timestamp > ?
                GROUP BY action, risk_level
                ORDER BY count DESC
            ''', (user_id, cutoff_time.isoformat()))
            
            activity = cursor.fetchall()
            
            # Подозрительная активность
            cursor.execute('''
                SELECT activity_type, severity, COUNT(*) as count
                FROM suspicious_activity 
                WHERE user_id = ? AND created_at > ?
                GROUP BY activity_type, severity
            ''', (user_id, cutoff_time.isoformat()))
            
            suspicious = cursor.fetchall()
            
            conn.close()
            
            return {
                'user_id': user_id,
                'time_period_hours': hours,
                'activity': [
                    {'action': row[0], 'count': row[1], 'risk_level': row[2]}
                    for row in activity
                ],
                'suspicious_activity': [
                    {'type': row[0], 'severity': row[1], 'count': row[2]}
                    for row in suspicious
                ],
                'total_requests': sum(row[1] for row in activity),
                'high_risk_events': sum(row[1] for row in activity if row[2] in ['high', 'critical'])
            }
            
        except Exception as e:
            logger.error(f"Failed to get user activity summary: {e}")
            return {'error': str(e)}
    
    def get_security_dashboard_data(self) -> Dict:
        """Получение данных для дашборда безопасности"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Статистика за последние 24 часа
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Общая статистика
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN risk_level = 'high' THEN 1 END) as high_risk,
                    COUNT(CASE WHEN risk_level = 'critical' THEN 1 END) as critical_risk,
                    COUNT(DISTINCT user_id) as unique_users
                FROM security_audit_logs 
                WHERE timestamp > ?
            ''', (cutoff_time.isoformat(),))
            
            stats = cursor.fetchone()
            
            # Топ подозрительных активностей
            cursor.execute('''
                SELECT activity_type, COUNT(*) as count
                FROM suspicious_activity 
                WHERE created_at > ?
                GROUP BY activity_type
                ORDER BY count DESC
                LIMIT 10
            ''', (cutoff_time.isoformat(),))
            
            top_suspicious = cursor.fetchall()
            
            # Топ IP адресов
            cursor.execute('''
                SELECT ip_address, COUNT(*) as count
                FROM security_audit_logs 
                WHERE timestamp > ?
                GROUP BY ip_address
                ORDER BY count DESC
                LIMIT 10
            ''', (cutoff_time.isoformat(),))
            
            top_ips = cursor.fetchall()
            
            conn.close()
            
            return {
                'summary': {
                    'total_events': stats[0],
                    'high_risk_events': stats[1],
                    'critical_events': stats[2],
                    'unique_users': stats[3]
                },
                'top_suspicious_activities': [
                    {'type': row[0], 'count': row[1]} for row in top_suspicious
                ],
                'top_ip_addresses': [
                    {'ip': row[0], 'requests': row[1]} for row in top_ips
                ],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {'error': str(e)}


def audit_log(action: str, risk_level: str = 'low', details: Dict = None):
    """
    Декоратор для автоматического аудита функций
    
    Args:
        action: Название действия для логирования
        risk_level: Уровень риска ('low', 'medium', 'high', 'critical')
        details: Дополнительные детали
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Получаем audit logger из приложения
                from flask import current_app
                audit_logger = current_app.extensions.get('audit_logger')
                
                if audit_logger:
                    # Логируем начало операции
                    audit_logger.log_user_action(
                        action=f"{action}_START",
                        risk_level='low',
                        details={
                            'function': f.__name__,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                            **(details or {})
                        }
                    )
                
                # Выполняем функцию
                result = f(*args, **kwargs)
                
                if audit_logger:
                    # Логируем успешное завершение
                    audit_logger.log_user_action(
                        action=f"{action}_SUCCESS",
                        risk_level=risk_level,
                        details={
                            'function': f.__name__,
                            'success': True,
                            **(details or {})
                        }
                    )
                
                return result
                
            except Exception as e:
                if audit_logger:
                    # Логируем ошибку
                    audit_logger.log_user_action(
                        action=f"{action}_ERROR",
                        risk_level='high',
                        details={
                            'function': f.__name__,
                            'error': str(e),
                            'success': False,
                            **(details or {})
                        }
                    )
                raise
        
        return decorated_function
    return decorator


logger.info("✅ Security Audit Logger module initialized")