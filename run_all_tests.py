#!/usr/bin/env python3
"""
run_all_tests.py - Главный скрипт для запуска всех тестов Telegram Mini App
Этот скрипт координирует выполнение всех видов тестирования поэтапно
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from typing import Dict, List, Any
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('master_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MasterTester:
    """Главный координатор тестирования"""
    
    def __init__(self):
        self.start_time = time.time()
        self.test_results = {}
        self.overall_success = True
        
        # Конфигурация
        self.config = {
            'base_url': 'http://localhost:5000',
            'bot_token': '6712109516:AAHL23ltolowG5kYTfkTKDadg2Io1Rd0WT8',
            'db_path': 'telegram_mini_app.db'
        }
        
    def print_header(self, title: str, char: str = "="):
        """Печать заголовка"""
        print(f"\n{char * 60}")
        print(f"{title.center(60)}")
        print(f"{char * 60}")
    
    def run_script(self, script_name: str, description: str, timeout: int = 300) -> Dict[str, Any]:
        """Запуск отдельного скрипта тестирования"""
        print(f"\n🔄 {description}")
        print(f"   Скрипт: {script_name}")
        
        if not os.path.exists(script_name):
            result = {
                'success': False,
                'error': f'Скрипт {script_name} не найден',
                'duration': 0
            }
            print(f"❌ Скрипт не найден: {script_name}")
            return result
        
        start_time = time.time()
        
        try:
            # Запускаем скрипт
            process = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            result = {
                'success': process.returncode == 0,
                'return_code': process.returncode,
                'duration': duration,
                'stdout': process.stdout,
                'stderr': process.stderr
            }
            
            if result['success']:
                print(f"✅ {description} - УСПЕШНО ({duration:.1f}с)")
            else:
                print(f"❌ {description} - ОШИБКА ({duration:.1f}с)")
                if process.stderr:
                    print(f"   Ошибка: {process.stderr[:200]}...")
                self.overall_success = False
            
            return result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            result = {
                'success': False,
                'error': f'Timeout after {timeout}s',
                'duration': duration
            }
            print(f"⏰ {description} - ТАЙМАУТ ({timeout}с)")
            self.overall_success = False
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = {
                'success': False,
                'error': str(e),
                'duration': duration
            }
            print(f"💥 {description} - ИСКЛЮЧЕНИЕ: {str(e)}")
            self.overall_success = False
            return result
    
    def check_prerequisites(self) -> bool:
        """Проверка предварительных условий"""
        self.print_header("ПРОВЕРКА ПРЕДВАРИТЕЛЬНЫХ УСЛОВИЙ")
        
        checks = []
        
        # Проверяем Python версию
        python_version = sys.version_info
        python_ok = python_version >= (3, 8)
        checks.append(('Python версия', python_ok, f'{python_version.major}.{python_version.minor}'))
        
        # Проверяем наличие ключевых файлов
        required_files = [
            'working_app.py',
            'requirements.txt', 
            'telegram_mini_app.db'
        ]
        
        for file_path in required_files:
            exists = os.path.exists(file_path)
            checks.append((f'Файл {file_path}', exists, 'найден' if exists else 'отсутствует'))
        
        # Проверяем наличие директорий
        required_dirs = [
            'app',
            'app/static',
            'app/templates'
        ]
        
        for dir_path in required_dirs:
            exists = os.path.isdir(dir_path)
            checks.append((f'Директория {dir_path}', exists, 'найдена' if exists else 'отсутствует'))
        
        # Проверяем зависимости
        try:
            import flask
            import requests
            checks.append(('Flask', True, flask.__version__))
            checks.append(('Requests', True, requests.__version__))
        except ImportError as e:
            checks.append(('Зависимости', False, str(e)))
        
        # Выводим результаты проверок
        all_ok = True
        for check_name, success, details in checks:
            status = "✅" if success else "❌"
            print(f"{status} {check_name}: {details}")
            if not success:
                all_ok = False
        
        if not all_ok:
            print("\n⚠️ Обнаружены проблемы с предварительными условиями!")
            print("   Исправьте их перед запуском тестов")
            return False
        
        print("\n✅ Все предварительные условия выполнены")
        return True
    
    def run_quick_test(self) -> bool:
        """Быстрое тестирование основных функций"""
        self.print_header("БЫСТРОЕ ТЕСТИРОВАНИЕ")
        
        result = self.run_script('quick_test.py', 'Быстрая проверка основных функций', timeout=120)
        self.test_results['quick_test'] = result
        
        return result['success']
    
    def run_comprehensive_test(self) -> bool:
        """Комплексное тестирование"""
        self.print_header("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ")
        
        result = self.run_script('test_application.py', 'Полное тестирование всех компонентов', timeout=600)
        self.test_results['comprehensive_test'] = result
        
        return result['success']
    
    def run_real_data_test(self) -> bool:
        """Тестирование с реальными данными"""
        self.print_header("ТЕСТИРОВАНИЕ С РЕАЛЬНЫМИ ДАННЫМИ")
        
        result = self.run_script('test_real_data.py', 'Тестирование реальных каналов и предложений', timeout=300)
        self.test_results['real_data_test'] = result
        
        return result['success']
    
    def run_performance_monitoring(self, duration_minutes: int = 5) -> bool:
        """Мониторинг производительности"""
        self.print_header("МОНИТОРИНГ ПРОИЗВОДИТЕЛЬНОСТИ")
        
        # Создаем временный скрипт для мониторинга с параметрами
        monitor_script = f"""
import sys
sys.path.append('.')
from monitor_performance import main
if __name__ == "__main__":
    sys.argv = ['monitor_performance.py', '{duration_minutes}', '15']
    sys.exit(main())
"""
        
        with open('temp_monitor.py', 'w') as f:
            f.write(monitor_script)
        
        try:
            result = self.run_script('temp_monitor.py', f'Мониторинг производительности ({duration_minutes} мин)', 
                                   timeout=duration_minutes * 60 + 60)
            self.test_results['performance_monitoring'] = result
            
            return result['success']
        finally:
            # Удаляем временный файл
            if os.path.exists('temp_monitor.py'):
                os.remove('temp_monitor.py')
    
    def generate_master_report(self) -> Dict[str, Any]:
        """Генерация итогового отчета"""
        total_duration = time.time() - self.start_time
        
        # Подсчитываем статистику
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get('success', False))
        
        # Собираем информацию о найденных проблемах
        issues = []
        recommendations = []
        
        for test_name, result in self.test_results.items():
            if not result.get('success', False):
                issues.append({
                    'test': test_name,
                    'error': result.get('error', 'Unknown error'),
                    'stderr': result.get('stderr', '')[:500] if result.get('stderr') else None
                })
        
        # Генерируем рекомендации
        if 'quick_test' in self.test_results and not self.test_results['quick_test']['success']:
            recommendations.append("Исправьте базовые проблемы перед переходом к сложным тестам")
        
        if any('database' in str(issue).lower() for issue in issues):
            recommendations.append("Проверьте настройки и структуру базы данных")
        
        if any('api' in str(issue).lower() or 'http' in str(issue).lower() for issue in issues):
            recommendations.append("Убедитесь, что приложение запущено и API эндпоинты доступны")
        
        if any('telegram' in str(issue).lower() or 'bot' in str(issue).lower() for issue in issues):
            recommendations.append("Проверьте корректность токена бота и доступ к Telegram API")
        
        # Определяем общее состояние
        if successful_tests == total_tests:
            overall_status = "excellent"
            status_message = "Все тесты пройдены успешно!"
        elif successful_tests >= total_tests * 0.8:
            overall_status = "good"
            status_message = "Большинство тестов пройдено, есть незначительные проблемы"
        elif successful_tests >= total_tests * 0.5:
            overall_status = "warning"
            status_message = "Половина тестов провалена, требуется внимание"
        else:
            overall_status = "critical"
            status_message = "Критические проблемы, требуется серьезное вмешательство"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'overall_status': overall_status,
                'status_message': status_message,
                'total_duration_minutes': total_duration / 60,
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': total_tests - successful_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'issues_found': issues,
            'recommendations': recommendations,
            'config_used': self.config
        }
        
        return report
    
    def run_all_tests(self, quick_only: bool = False, skip_monitoring: bool = False) -> bool:
        """Запуск всех тестов"""
        self.print_header("🧪 MASTER TESTING SUITE - TELEGRAM MINI APP", "=")
        
        print(f"⏰ Начало тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Конфигурация:")
        print(f"   • URL приложения: {self.config['base_url']}")
        print(f"   • База данных: {self.config['db_path']}")
        print(f"   • Быстрый режим: {'Да' if quick_only else 'Нет'}")
        print(f"   • Пропустить мониторинг: {'Да' if skip_monitoring else 'Нет'}")
        
        # Этап 1: Предварительные проверки
        if not self.check_prerequisites():
            print("\n❌ Тестирование прервано из-за проблем с предварительными условиями")
            return False
        
        # Этап 2: Быстрое тестирование
        quick_success = self.run_quick_test()
        
        if quick_only:
            print("\n📋 Быстрое тестирование завершено")
        else:
            # Этап 3: Комплексное тестирование (только если быстрое прошло успешно)
            if quick_success:
                comprehensive_success = self.run_comprehensive_test()
                
                # Этап 4: Тестирование с реальными данными
                real_data_success = self.run_real_data_test()
                
                # Этап 5: Мониторинг производительности (опционально)
                if not skip_monitoring:
                    performance_success = self.run_performance_monitoring(duration_minutes=3)
            else:
                print("\n⚠️ Быстрое тестирование провалено, пропускаем остальные тесты")
                print("   Исправьте базовые проблемы и запустите снова")
        
        # Генерируем итоговый отчет
        self.print_header("📊 ИТОГОВЫЙ ОТЧЕТ")
        
        report = self.generate_master_report()
        
        # Выводим краткую сводку
        summary = report['summary']
        print(f"⏱️ Общее время: {summary['total_duration_minutes']:.1f} минут")
        print(f"📊 Результат: {summary['successful_tests']}/{summary['total_tests']} тестов ({summary['success_rate']:.1f}%)")
        print(f"🎯 Статус: {summary['status_message']}")
        
        # Показываем проблемы
        if report['issues_found']:
            print(f"\n⚠️ Обнаруженные проблемы ({len(report['issues_found'])}):")
            for i, issue in enumerate(report['issues_found'][:5], 1):  # Показываем первые 5
                print(f"   {i}. {issue['test']}: {issue['error']}")
            
            if len(report['issues_found']) > 5:
                print(f"   ... и еще {len(report['issues_found']) - 5} проблем")
        
        # Показываем рекомендации
        if report['recommendations']:
            print(f"\n💡 Рекомендации:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Сохраняем полный отчет
        with open('master_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Детальный отчет сохранен: master_test_report.json")
        print(f"📋 Логи сохранены: master_test.log")
        
        # Финальное сообщение
        if summary['overall_status'] == 'excellent':
            print("\n🎉 ПРЕВОСХОДНО! Все тесты пройдены!")
            print("   Telegram Mini App готов к продакшену")
        elif summary['overall_status'] == 'good':
            print("\n✅ ХОРОШО! Основные функции работают")
            print("   Есть незначительные проблемы для исправления")
        elif summary['overall_status'] == 'warning':
            print("\n⚠️ ВНИМАНИЕ! Обнаружены серьезные проблемы")
            print("   Требуется дополнительная работа")
        else:
            print("\n🚨 КРИТИЧНО! Множественные проблемы")
            print("   Приложение не готово к использованию")
        
        return self.overall_success

def main():
    """Главная функция с обработкой аргументов"""
    parser = argparse.ArgumentParser(description='Master Testing Suite для Telegram Mini App')
    parser.add_argument('--quick', action='store_true', help='Только быстрое тестирование')
    parser.add_argument('--skip-monitoring', action='store_true', help='Пропустить мониторинг производительности')
    parser.add_argument('--config', help='Путь к файлу конфигурации JSON')
    
    args = parser.parse_args()
    
    # Создаем мастер-тестер
    tester = MasterTester()
    
    # Загружаем конфигурацию если указана
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
                tester.config.update(config)
            print(f"📝 Загружена конфигурация: {args.config}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации: {e}")
    
    try:
        # Запускаем тестирование
        success = tester.run_all_tests(
            quick_only=args.quick,
            skip_monitoring=args.skip_monitoring
        )
        
        # Возвращаем код выхода
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        return 130
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {str(e)}")
        logger.exception("Критическая ошибка мастер-тестера")
        return 1

if __name__ == "__main__":
    sys.exit(main())