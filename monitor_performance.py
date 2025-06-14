#!/usr/bin/env python3
"""
monitor_performance.py - Мониторинг производительности Telegram Mini App
Непрерывный мониторинг работы приложения в реальном времени
"""

import os
import sys
import time
import json
import psutil
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import sqlite3

class PerformanceMonitor:
    """Монитор производительности приложения"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', 'http://localhost:5000')
        self.monitoring = False
        self.metrics = {
            'requests': [],
            'system': [],
            'database': [],
            'errors': []
        }
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('performance.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Получение системных метрик"""
        try:
            # CPU и память
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Сетевые подключения
            connections = len(psutil.net_connections())
            
            # Процессы Python
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network_connections': connections,
                'python_processes': len(python_processes),
                'python_memory': sum(p.get('memory_percent', 0) for p in python_processes)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения системных метрик: {e}")
            return {}
    
    def test_endpoint_performance(self, endpoint: str, method: str = 'GET') -> Dict[str, Any]:
        """Тестирование производительности эндпоинта"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json={}, timeout=30)
            else:
                return {'error': f'Unsupported method: {method}'}
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time': response_time,
                'content_length': len(response.content),
                'success': 200 <= response.status_code < 400
            }
            
        except requests.exceptions.Timeout:
            return {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'error': 'timeout',
                'success': False
            }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'error': str(e),
                'success': False
            }
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """Получение метрик базы данных"""
        try:
            db_path = self.config.get('db_path', 'telegram_mini_app.db')
            
            if not os.path.exists(db_path):
                return {'error': 'Database not found'}
            
            # Размер файла БД
            db_size = os.path.getsize(db_path)
            
            # Подключаемся к БД
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Количество записей в таблицах
            tables_info = {}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table_name, in tables:
                if table_name != 'sqlite_sequence':
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    tables_info[table_name] = count
            
            # Проверяем время выполнения простого запроса
            start_time = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            query_time = time.time() - start_time
            
            conn.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'database_size_bytes': db_size,
                'tables': tables_info,
                'simple_query_time': query_time,
                'total_records': sum(tables_info.values())
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def monitor_cycle(self):
        """Один цикл мониторинга"""
        # Системные метрики
        system_metrics = self.get_system_metrics()
        if system_metrics:
            self.metrics['system'].append(system_metrics)
        
        # Метрики БД
        db_metrics = self.get_database_metrics()
        if db_metrics:
            self.metrics['database'].append(db_metrics)
        
        # Тестируем ключевые эндпоинты
        endpoints = [
            ('/', 'GET'),
            ('/test', 'GET'),
            ('/api/offers', 'GET'),
            ('/api/channels', 'GET')
        ]
        
        for endpoint, method in endpoints:
            metrics = self.test_endpoint_performance(endpoint, method)
            self.metrics['requests'].append(metrics)
            
            # Логируем проблемы
            if not metrics.get('success', False):
                error_info = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'endpoint_error',
                    'endpoint': endpoint,
                    'details': metrics
                }
                self.metrics['errors'].append(error_info)
                self.logger.warning(f"Проблема с {endpoint}: {metrics.get('error', 'Unknown')}")
    
    def analyze_metrics(self) -> Dict[str, Any]:
        """Анализ собранных метрик"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_duration': 0,
            'system_health': {},
            'performance_summary': {},
            'issues_detected': []
        }
        
        # Анализ системных метрик
        if self.metrics['system']:
            recent_system = self.metrics['system'][-10:]  # Последние 10 измерений
            
            avg_cpu = sum(m.get('cpu_percent', 0) for m in recent_system) / len(recent_system)
            avg_memory = sum(m.get('memory', {}).get('percent', 0) for m in recent_system) / len(recent_system)
            
            analysis['system_health'] = {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_percent': avg_memory,
                'cpu_status': 'high' if avg_cpu > 80 else 'normal' if avg_cpu > 50 else 'low',
                'memory_status': 'high' if avg_memory > 80 else 'normal' if avg_memory > 50 else 'low'
            }
            
            # Проблемы с ресурсами
            if avg_cpu > 80:
                analysis['issues_detected'].append({
                    'type': 'high_cpu',
                    'severity': 'warning',
                    'message': f'Высокая загрузка CPU: {avg_cpu:.1f}%'
                })
            
            if avg_memory > 80:
                analysis['issues_detected'].append({
                    'type': 'high_memory',
                    'severity': 'warning', 
                    'message': f'Высокое использование памяти: {avg_memory:.1f}%'
                })
        
        # Анализ производительности эндпоинтов
        if self.metrics['requests']:
            recent_requests = [r for r in self.metrics['requests'] 
                             if r.get('timestamp') and 
                             datetime.fromisoformat(r['timestamp']) > datetime.now() - timedelta(minutes=10)]
            
            if recent_requests:
                successful_requests = [r for r in recent_requests if r.get('success', False)]
                success_rate = len(successful_requests) / len(recent_requests) * 100
                
                if successful_requests:
                    response_times = [r.get('response_time', 0) for r in successful_requests 
                                    if r.get('response_time')]
                    
                    if response_times:
                        avg_response_time = sum(response_times) / len(response_times)
                        max_response_time = max(response_times)
                        
                        analysis['performance_summary'] = {
                            'success_rate': success_rate,
                            'avg_response_time': avg_response_time,
                            'max_response_time': max_response_time,
                            'total_requests': len(recent_requests),
                            'successful_requests': len(successful_requests)
                        }
                        
                        # Проблемы с производительностью
                        if success_rate < 90:
                            analysis['issues_detected'].append({
                                'type': 'low_success_rate',
                                'severity': 'error',
                                'message': f'Низкая успешность запросов: {success_rate:.1f}%'
                            })
                        
                        if avg_response_time > 5:
                            analysis['issues_detected'].append({
                                'type': 'slow_response',
                                'severity': 'warning',
                                'message': f'Медленные ответы: {avg_response_time:.2f}с'
                            })
        
        # Анализ ошибок
        recent_errors = [e for e in self.metrics['errors']
                        if e.get('timestamp') and 
                        datetime.fromisoformat(e['timestamp']) > datetime.now() - timedelta(minutes=10)]
        
        if len(recent_errors) > 5:
            analysis['issues_detected'].append({
                'type': 'frequent_errors',
                'severity': 'error',
                'message': f'Частые ошибки: {len(recent_errors)} за последние 10 минут'
            })
        
        return analysis
    
    def start_monitoring(self, duration_minutes: int = 10, interval_seconds: int = 30):
        """Запуск мониторинга"""
        print(f"🔍 Запуск мониторинга на {duration_minutes} минут")
        print(f"   Интервал проверок: {interval_seconds} секунд")
        print("=" * 50)
        
        self.monitoring = True
        start_time = time.time()
        cycles_completed = 0
        
        try:
            while self.monitoring and time.time() - start_time < duration_minutes * 60:
                cycle_start = time.time()
                
                print(f"🔄 Цикл мониторинга #{cycles_completed + 1}")
                self.monitor_cycle()
                cycles_completed += 1
                
                # Анализируем метрики каждые 5 циклов
                if cycles_completed % 5 == 0:
                    analysis = self.analyze_metrics()
                    
                    print(f"\n📊 Промежуточный анализ:")
                    if analysis['system_health']:
                        print(f"   CPU: {analysis['system_health']['avg_cpu_percent']:.1f}% "
                              f"({analysis['system_health']['cpu_status']})")
                        print(f"   Память: {analysis['system_health']['avg_memory_percent']:.1f}% "
                              f"({analysis['system_health']['memory_status']})")
                    
                    if analysis['performance_summary']:
                        perf = analysis['performance_summary']
                        print(f"   Успешность: {perf['success_rate']:.1f}%")
                        print(f"   Время ответа: {perf['avg_response_time']:.2f}с")
                    
                    if analysis['issues_detected']:
                        print(f"   ⚠️ Проблем обнаружено: {len(analysis['issues_detected'])}")
                        for issue in analysis['issues_detected'][-3:]:  # Последние 3
                            print(f"     • {issue['message']}")
                    else:
                        print(f"   ✅ Проблем не обнаружено")
                
                # Ждем до следующего цикла
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n⏹️ Мониторинг прерван пользователем")
        
        # Финальный анализ
        print("\n" + "=" * 50)
        print("📈 ИТОГОВЫЙ АНАЛИЗ МОНИТОРИНГА")
        print("=" * 50)
        
        final_analysis = self.analyze_metrics()
        
        total_duration = time.time() - start_time
        print(f"⏱️ Время мониторинга: {total_duration/60:.1f} минут")
        print(f"🔄 Выполнено циклов: {cycles_completed}")
        
        # Системное состояние
        if final_analysis['system_health']:
            sh = final_analysis['system_health']
            print(f"\n🖥️ Система:")
            print(f"   CPU: {sh['avg_cpu_percent']:.1f}% ({sh['cpu_status']})")
            print(f"   Память: {sh['avg_memory_percent']:.1f}% ({sh['memory_status']})")
        
        # Производительность
        if final_analysis['performance_summary']:
            ps = final_analysis['performance_summary']
            print(f"\n⚡ Производительность:")
            print(f"   Успешность запросов: {ps['success_rate']:.1f}%")
            print(f"   Среднее время ответа: {ps['avg_response_time']:.2f}с")
            print(f"   Максимальное время ответа: {ps['max_response_time']:.2f}с")
            print(f"   Всего запросов: {ps['total_requests']}")
        
        # Проблемы
        issues = final_analysis['issues_detected']
        if issues:
            print(f"\n⚠️ Обнаруженные проблемы ({len(issues)}):")
            for issue in issues:
                severity_icon = "🚨" if issue['severity'] == 'error' else "⚠️"
                print(f"   {severity_icon} {issue['message']}")
        else:
            print(f"\n✅ Критических проблем не обнаружено")
        
        # Сохраняем полный отчет
        report = {
            'monitoring_summary': {
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'duration_minutes': total_duration / 60,
                'cycles_completed': cycles_completed,
                'total_requests_monitored': len(self.metrics['requests'])
            },
            'final_analysis': final_analysis,
            'raw_metrics': {
                'system': self.metrics['system'][-20:],  # Последние 20 записей
                'requests': self.metrics['requests'][-50:],  # Последние 50 запросов
                'database': self.metrics['database'][-10:],  # Последние 10 проверок БД
                'errors': self.metrics['errors'][-20:]  # Последние 20 ошибок
            }
        }
        
        with open('performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Полный отчет сохранен: performance_report.json")
        
        return final_analysis

def main():
    """Главная функция"""
    config = {
        'base_url': 'http://localhost:5000',
        'db_path': 'telegram_mini_app.db'
    }
    
    monitor = PerformanceMonitor(config)
    
    # Параметры мониторинга
    duration = 10  # минут
    interval = 30  # секунд
    
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("⚠️ Неверный формат времени, используется 10 минут")
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
        except ValueError:
            print("⚠️ Неверный формат интервала, используется 30 секунд")
    
    try:
        analysis = monitor.start_monitoring(duration, interval)
        
        # Возвращаем код выхода на основе обнаруженных проблем
        critical_issues = [i for i in analysis.get('issues_detected', []) 
                          if i.get('severity') == 'error']
        
        if critical_issues:
            print(f"\n❌ Обнаружены критические проблемы: {len(critical_issues)}")
            return 1
        else:
            print(f"\n✅ Мониторинг завершен успешно")
            return 0
            
    except Exception as e:
        print(f"\n💥 Ошибка мониторинга: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())