# Создайте файл monitoring_cron.py для запуска по расписанию

#!/usr/bin/env python3
"""
Cron задача для мониторинга контрактов
Запускать каждые 6 часов: 0 */6 * * *
"""

import sys
import os
from datetime import datetime

# Добавляем пути
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def run_monitoring():
    """Запуск мониторинга контрактов"""
    try:
        from add_offer import process_monitoring_tasks
        
        print(f"[{datetime.now()}] Запуск мониторинга контрактов...")
        process_monitoring_tasks()
        print(f"[{datetime.now()}] Мониторинг завершен")
        
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка мониторинга: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_monitoring()

# Для добавления в crontab:
# 0 */6 * * * /usr/bin/python3 /path/to/your/app/monitoring_cron.py >> /var/log/monitoring.log 2>&1