# payout_system.py - ФИНАЛЬНАЯ ВЕРСИЯ без ошибок логирования
import os
import json
import sqlite3
import asyncio
import aiohttp
import schedule
import time
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from enum import Enum
from threading import Thread
from flask import Blueprint, request, jsonify

# === ПРОСТОЕ ЛОГИРОВАНИЕ БЕЗ ПРОБЛЕМ С КОДИРОВКОЙ ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('payout_system.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)


# Функция для простого логирования
def log_message(level, message):
    """Простое логирование без эмодзи"""
    try:
        # Убираем эмодзи из сообщения для логирования
        clean_message = ''.join(char for char in message if ord(char) < 128)
        getattr(logger, level)(clean_message)
    except:
        pass


def print_status(message):
    """Простой вывод статуса"""
    try:
        print(message)
    except:
        # Если ошибка с кодировкой, выводим без специальных символов
        clean_message = ''.join(char for char in message if ord(char) < 128)
        print(clean_message)


# Конфигурация
DATABASE_PATH = 'telegram_mini_app.db'
BOT_TOKEN = os.environ.get('BOT_TOKEN')
TELEGRAM_PAYMENT_TOKEN = os.environ.get('TELEGRAM_PAYMENT_TOKEN')
YOUR_TELEGRAM_ID = int(os.environ.get('YOUR_TELEGRAM_ID', 373086959))

# Константы для автоматических выплат
DEFAULT_ESCROW_PERIOD = 7  # дней до автовыплаты
MIN_PAYOUT_AMOUNT = 100  # минимальная сумма для выплаты (в рублях)
MAX_RETRY_ATTEMPTS = 3  # максимальное количество попыток


class PayoutStatus(Enum):
    """Статусы выплат"""
    PENDING = 'pending'  # Ожидает обработки
    PROCESSING = 'processing'  # Обрабатывается
    COMPLETED = 'completed'  # Завершена
    FAILED = 'failed'  # Ошибка
    RETRY = 'retry'  # Повторная попытка
    CANCELLED = 'cancelled'  # Отменена


class PayoutTrigger(Enum):
    """Триггеры для выплат"""
    AUTO_TIME = 'auto_time'  # Автоматически по времени
    MANUAL_RELEASE = 'manual_release'  # Ручное освобождение
    OFFER_COMPLETED = 'offer_completed'  # Оффер завершен
    DISPUTE_RESOLVED = 'dispute_resolved'  # Спор решен


def get_db_connection():
    """Получение подключения к SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except Exception as e:
        raise Exception(f"Ошибка подключения к SQLite: {e}")


def safe_execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Безопасное выполнение SQL запросов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        result = None
        if fetch_one:
            row = cursor.fetchone()
            result = dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            result = [dict(row) for row in rows] if rows else []
        else:
            conn.commit()
            result = cursor.lastrowid

        conn.close()
        return result
    except Exception as e:
        log_message('error', f"Ошибка выполнения запроса: {e}")
        return None


class TelegramPayoutHandler:
    """Обработчик выплат через Telegram"""

    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_payment_notification(self, user_id: int, amount: float,
                                        payout_id: int, status: str) -> bool:
        """Отправка уведомления о выплате"""
        try:
            if status == PayoutStatus.COMPLETED.value:
                message = f"""
Выплата выполнена!

Сумма: {amount} рублей
ID выплаты: {payout_id}
Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Средства переведены на ваш Telegram Wallet.
                """
            elif status == PayoutStatus.FAILED.value:
                message = f"""
Ошибка выплаты

Сумма: {amount} рублей
ID выплаты: {payout_id}

Произошла ошибка при переводе средств. Мы работаем над решением проблемы.
                """
            else:
                message = f"""
Выплата обрабатывается

Сумма: {amount} рублей
ID выплаты: {payout_id}

Ваша выплата поставлена в очередь на обработку.
                """

            payload = {
                'chat_id': user_id,
                'text': message.strip(),
                'parse_mode': 'HTML'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{self.base_url}/sendMessage",
                        json=payload
                ) as response:
                    result = await response.json()
                    return result.get('ok', False)

        except Exception as e:
            log_message('error', f"Ошибка отправки уведомления о выплате: {e}")
            return False

    async def process_telegram_wallet_payout(self, user_id: int, amount: float) -> Dict:
        """Обработка выплаты через Telegram Wallet (имитация)"""
        try:
            # В реальной реализации здесь был бы вызов Telegram Payments API
            # Пока что имитируем успешную выплату

            await asyncio.sleep(1)  # Имитация обработки

            # В 10% случаев имитируем ошибку для тестирования
            import random
            if random.random() < 0.1:
                return {
                    'success': False,
                    'error': 'Временная ошибка платежной системы',
                    'retry_after': 300  # Повторить через 5 минут
                }

            transaction_id = f"tg_wallet_{int(datetime.now().timestamp())}_{user_id}"

            return {
                'success': True,
                'transaction_id': transaction_id,
                'amount': amount,
                'currency': 'RUB',
                'processed_at': datetime.now().isoformat()
            }

        except Exception as e:
            log_message('error', f"Ошибка выплаты в Telegram Wallet: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class AutoPayoutScheduler:
    """Планировщик автоматических выплат"""

    def __init__(self):
        self.payout_handler = TelegramPayoutHandler()
        self.is_running = False
        self.scheduler_thread = None

    def start_scheduler(self):
        """Запуск планировщика"""
        if self.is_running:
            log_message('warning', "Планировщик уже запущен")
            return

        self.is_running = True

        # Настраиваем расписание
        schedule.every(5).minutes.do(self.process_pending_payouts)  # Каждые 5 минут
        schedule.every(1).hours.do(self.process_expired_escrows)  # Каждый час
        schedule.every().day.at("09:00").do(self.daily_payout_summary)  # Ежедневная сводка

        # Запускаем в отдельном потоке
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

        log_message('info', "Планировщик автоматических выплат запущен")

    def stop_scheduler(self):
        """Остановка планировщика"""
        self.is_running = False
        schedule.clear()
        log_message('info', "Планировщик автоматических выплат остановлен")

    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Проверяем каждые 30 секунд
            except Exception as e:
                log_message('error', f"Ошибка в планировщике: {e}")
                time.sleep(60)  # При ошибке ждем минуту

    def process_pending_payouts(self):
        """Обработка ожидающих выплат"""
        try:
            log_message('info', "Обработка ожидающих выплат...")

            # Получаем выплаты в статусе pending или retry
            pending_payouts = safe_execute_query('''
                                                 SELECT p.*, u.telegram_id, u.username
                                                 FROM payouts p
                                                          JOIN users u ON p.recipient_id = u.id
                                                 WHERE p.status IN ('pending', 'retry')
                                                   AND p.scheduled_at <= ?
                                                 ORDER BY p.created_at ASC LIMIT 10
                                                 ''', (datetime.now(),), fetch_all=True)

            if not pending_payouts:
                log_message('info', "Нет ожидающих выплат")
                return

            log_message('info', f"Найдено {len(pending_payouts)} выплат для обработки")

            for payout in pending_payouts:
                asyncio.run(self._process_single_payout(payout))

        except Exception as e:
            log_message('error', f"Ошибка обработки ожидающих выплат: {e}")

    async def _process_single_payout(self, payout: Dict):
        """Обработка одной выплаты"""
        try:
            payout_id = payout['id']
            user_id = payout['telegram_id']
            amount = float(payout['amount'])

            log_message('info', f"Обрабатываем выплату {payout_id} для пользователя {user_id} на сумму {amount} рублей")

            # Обновляем статус на "обрабатывается"
            safe_execute_query('''
                               UPDATE payouts
                               SET status                = ?,
                                   processing_started_at = ?
                               WHERE id = ?
                               ''', (PayoutStatus.PROCESSING.value, datetime.now(), payout_id))

            # Обрабатываем выплату
            result = await self.payout_handler.process_telegram_wallet_payout(user_id, amount)

            if result['success']:
                # Успешная выплата
                safe_execute_query('''
                                   UPDATE payouts
                                   SET status         = ?,
                                       completed_at   = ?,
                                       transaction_id = ?
                                   WHERE id = ?
                                   ''', (
                                       PayoutStatus.COMPLETED.value,
                                       datetime.now(),
                                       result['transaction_id'],
                                       payout_id
                                   ))

                # Отправляем уведомление
                await self.payout_handler.send_payment_notification(
                    user_id, amount, payout_id, PayoutStatus.COMPLETED.value
                )

                log_message('info', f"Выплата {payout_id} успешно выполнена")

                # Создаем уведомление в системе
                try:
                    from notifications_system import NotificationManager
                    NotificationManager.create_notification(
                        user_id=user_id,
                        notification_type='payout_completed',
                        title='Выплата выполнена',
                        message=f'Выплата на сумму {amount} рублей успешно переведена',
                        data={'payout_id': payout_id, 'amount': amount}
                    )
                except ImportError:
                    pass

            else:
                # Ошибка выплаты
                retry_count = payout.get('retry_count', 0) + 1

                if retry_count <= MAX_RETRY_ATTEMPTS:
                    # Планируем повторную попытку
                    retry_after = result.get('retry_after', 300)  # По умолчанию через 5 минут
                    scheduled_at = datetime.now() + timedelta(seconds=retry_after)

                    safe_execute_query('''
                                       UPDATE payouts
                                       SET status       = ?,
                                           retry_count  = ?,
                                           scheduled_at = ?,
                                           last_error   = ?,
                                           updated_at   = ?
                                       WHERE id = ?
                                       ''', (
                                           PayoutStatus.RETRY.value, retry_count, scheduled_at,
                                           result['error'], datetime.now(), payout_id
                                       ))

                    log_message('warning',
                                f"Выплата {payout_id} не удалась, попытка {retry_count}/{MAX_RETRY_ATTEMPTS}")

                else:
                    # Превышено количество попыток
                    safe_execute_query('''
                                       UPDATE payouts
                                       SET status     = ?,
                                           last_error = ?,
                                           updated_at = ?
                                       WHERE id = ?
                                       ''', (
                                           PayoutStatus.FAILED.value,
                                           result['error'],
                                           datetime.now(),
                                           payout_id
                                       ))

                    # Отправляем уведомление об ошибке
                    await self.payout_handler.send_payment_notification(
                        user_id, amount, payout_id, PayoutStatus.FAILED.value
                    )

                    log_message('error', f"Выплата {payout_id} окончательно не удалась")

        except Exception as e:
            log_message('error', f"Ошибка обработки выплаты {payout['id']}: {e}")

            # Помечаем как ошибку
            safe_execute_query('''
                               UPDATE payouts
                               SET status     = ?,
                                   last_error = ?,
                                   updated_at = ?
                               WHERE id = ?
                               ''', (PayoutStatus.FAILED.value, str(e), datetime.now(), payout['id']))

    def process_expired_escrows(self):
        """Обработка просроченных эскроу для автоматических выплат"""
        try:
            log_message('info', "Проверка просроченных эскроу...")

            # Находим эскроу, которые истекли и готовы для автовыплаты
            expired_escrows = safe_execute_query('''
                                                 SELECT et.*, u.telegram_id, u.username
                                                 FROM escrow_transactions et
                                                          JOIN users u ON et.recipient_id = u.id
                                                 WHERE et.status = 'funds_held'
                                                   AND et.expires_at <= ?
                                                   AND et.id NOT IN (SELECT DISTINCT escrow_id
                                                                     FROM payouts
                                                                     WHERE escrow_id IS NOT NULL)
                                                 ORDER BY et.expires_at ASC LIMIT 20
                                                 ''', (datetime.now(),), fetch_all=True)

            if not expired_escrows:
                log_message('info', "Нет просроченных эскроу для автовыплаты")
                return

            log_message('info', f"Найдено {len(expired_escrows)} просроченных эскроу")

            for escrow in expired_escrows:
                self._create_automatic_payout(escrow)

        except Exception as e:
            log_message('error', f"Ошибка обработки просроченных эскроу: {e}")

    def _create_automatic_payout(self, escrow: Dict):
        """Создание автоматической выплаты из эскроу"""
        try:
            escrow_id = escrow['id']
            recipient_id = escrow['recipient_id']
            amount = float(escrow['amount'])

            # Создаем запись о выплате
            payout_id = safe_execute_query('''
                                           INSERT INTO payouts (escrow_id, recipient_id, amount, status, trigger_type,
                                                                created_at, scheduled_at)
                                           VALUES (?, ?, ?, ?, ?, ?, ?)
                                           ''', (
                                               escrow_id, recipient_id, amount, PayoutStatus.PENDING.value,
                                               PayoutTrigger.AUTO_TIME.value, datetime.now(), datetime.now()
                                           ))

            # Обновляем статус эскроу
            safe_execute_query('''
                               UPDATE escrow_transactions
                               SET status      = 'funds_released',
                                   released_at = ?
                               WHERE id = ?
                               ''', (datetime.now(), escrow_id))

            log_message('info', f"Создана автоматическая выплата {payout_id} из эскроу {escrow_id}")

        except Exception as e:
            log_message('error', f"Ошибка создания автоматической выплаты: {e}")

    def daily_payout_summary(self):
        """Ежедневная сводка по выплатам"""
        try:
            log_message('info', "Создание ежедневной сводки по выплатам...")

            today = datetime.now().date()

            # Статистика за сегодня
            stats = safe_execute_query('''
                                       SELECT COUNT(*)                                                   as total_payouts,
                                              SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as completed_amount,
                                              COUNT(CASE WHEN status = 'completed' THEN 1 END)           as completed_count,
                                              COUNT(CASE WHEN status = 'failed' THEN 1 END)              as failed_count,
                                              COUNT(CASE WHEN status = 'pending' THEN 1 END)             as pending_count
                                       FROM payouts
                                       WHERE DATE (created_at) = ?
                                       ''', (today,), fetch_one=True)

            if stats and stats['total_payouts'] > 0:
                summary = f"""
Сводка по выплатам за {today.strftime('%d.%m.%Y')}:
Выполнено: {stats['completed_count']} ({stats['completed_amount']} рублей)
Ошибок: {stats['failed_count']}
Ожидает: {stats['pending_count']}
Всего: {stats['total_payouts']}
                """

                log_message('info', summary)

        except Exception as e:
            log_message('error', f"Ошибка создания ежедневной сводки: {e}")


class PayoutManager:
    """Основной менеджер выплат"""

    def __init__(self):
        self.scheduler = AutoPayoutScheduler()
        self.payout_handler = TelegramPayoutHandler()

    def start_auto_payouts(self):
        """Запуск автоматических выплат"""
        self.scheduler.start_scheduler()

    def stop_auto_payouts(self):
        """Остановка автоматических выплат"""
        self.scheduler.stop_scheduler()

    def create_manual_payout(self, escrow_id: int, trigger_type: str = 'manual_release') -> Dict:
        """Создание ручной выплаты"""
        try:
            # Получаем данные эскроу
            escrow = safe_execute_query('''
                                        SELECT *
                                        FROM escrow_transactions
                                        WHERE id = ?
                                        ''', (escrow_id,), fetch_one=True)

            if not escrow:
                return {'success': False, 'error': 'Эскроу не найден'}

            if escrow['status'] != 'funds_held':
                return {'success': False, 'error': 'Эскроу не в статусе удержания средств'}

            # Проверяем, нет ли уже выплаты для этого эскроу
            existing_payout = safe_execute_query('''
                                                 SELECT id
                                                 FROM payouts
                                                 WHERE escrow_id = ?
                                                 ''', (escrow_id,), fetch_one=True)

            if existing_payout:
                return {'success': False, 'error': 'Выплата для этого эскроу уже существует'}

            # Создаем выплату
            payout_id = safe_execute_query('''
                                           INSERT INTO payouts (escrow_id, recipient_id, amount, status, trigger_type,
                                                                created_at, scheduled_at)
                                           VALUES (?, ?, ?, ?, ?, ?, ?)
                                           ''', (
                                               escrow_id, escrow['recipient_id'], escrow['amount'],
                                               PayoutStatus.PENDING.value, trigger_type,
                                               datetime.now(), datetime.now()
                                           ))

            # Обновляем эскроу
            safe_execute_query('''
                               UPDATE escrow_transactions
                               SET status      = 'funds_released',
                                   released_at = ?
                               WHERE id = ?
                               ''', (datetime.now(), escrow_id))

            return {
                'success': True,
                'payout_id': payout_id,
                'amount': escrow['amount']
            }

        except Exception as e:
            log_message('error', f"Ошибка создания ручной выплаты: {e}")
            return {'success': False, 'error': str(e)}

    def get_payout_status(self, payout_id: int) -> Optional[Dict]:
        """Получение статуса выплаты"""
        try:
            payout = safe_execute_query('''
                                        SELECT p.*,
                                               u.username,
                                               u.telegram_id,
                                               et.offer_id,
                                               o.title as offer_title
                                        FROM payouts p
                                                 JOIN users u ON p.recipient_id = u.id
                                                 LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                 LEFT JOIN offers o ON et.offer_id = o.id
                                        WHERE p.id = ?
                                        ''', (payout_id,), fetch_one=True)

            return payout

        except Exception as e:
            log_message('error', f"Ошибка получения статуса выплаты: {e}")
            return None

    def get_user_payouts(self, user_telegram_id: int, limit: int = 50) -> List[Dict]:
        """Получение выплат пользователя"""
        try:
            payouts = safe_execute_query('''
                                         SELECT p.*, et.offer_id, o.title as offer_title
                                         FROM payouts p
                                                  JOIN users u ON p.recipient_id = u.id
                                                  LEFT JOIN escrow_transactions et ON p.escrow_id = et.id
                                                  LEFT JOIN offers o ON et.offer_id = o.id
                                         WHERE u.telegram_id = ?
                                         ORDER BY p.created_at DESC LIMIT ?
                                         ''', (user_telegram_id, limit), fetch_all=True)

            return payouts or []

        except Exception as e:
            log_message('error', f"Ошибка получения выплат пользователя: {e}")
            return []

    def get_payout_statistics(self, days: int = 30) -> Dict:
        """Получение статистики выплат"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            stats = safe_execute_query('''
                                       SELECT COUNT(*)                                                   as total_payouts,
                                              SUM(amount)                                                as total_amount,
                                              SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as completed_amount,
                                              COUNT(CASE WHEN status = 'completed' THEN 1 END)           as completed_count,
                                              COUNT(CASE WHEN status = 'failed' THEN 1 END)              as failed_count,
                                              COUNT(CASE WHEN status = 'pending' THEN 1 END)             as pending_count,
                                              AVG(CASE
                                                      WHEN status = 'completed' AND completed_at IS NOT NULL
                                                          THEN (julianday(completed_at) - julianday(created_at)) * 24 * 60
                                                      ELSE NULL END)                                     as avg_processing_time_minutes
                                       FROM payouts
                                       WHERE created_at >= ?
                                       ''', (start_date,), fetch_one=True)

            return stats or {}

        except Exception as e:
            log_message('error', f"Ошибка получения статистики: {e}")
            return {}


# Flask Blueprint для API выплат
payouts_bp = Blueprint('payouts', __name__, url_prefix='/api/payouts')

# Глобальный экземпляр менеджера
payout_manager = PayoutManager()


@payouts_bp.route('/create', methods=['POST'])
def create_manual_payout_api():
    """API для создания ручной выплаты"""
    try:
        data = request.get_json()
        escrow_id = data.get('escrow_id')

        if not escrow_id:
            return jsonify({'success': False, 'error': 'escrow_id обязателен'}), 400

        result = payout_manager.create_manual_payout(escrow_id)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        log_message('error', f"Ошибка API создания выплаты: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payouts_bp.route('/status/<int:payout_id>', methods=['GET'])
def get_payout_status_api(payout_id):
    """API для получения статуса выплаты"""
    try:
        payout = payout_manager.get_payout_status(payout_id)

        if payout:
            return jsonify({'success': True, 'payout': payout})
        else:
            return jsonify({'success': False, 'error': 'Выплата не найдена'}), 404

    except Exception as e:
        log_message('error', f"Ошибка получения статуса выплаты: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payouts_bp.route('/user/<int:telegram_user_id>', methods=['GET'])
def get_user_payouts_api(telegram_user_id):
    """API для получения выплат пользователя"""
    try:
        limit = request.args.get('limit', 50, type=int)
        payouts = payout_manager.get_user_payouts(telegram_user_id, limit)

        return jsonify({'success': True, 'payouts': payouts})

    except Exception as e:
        log_message('error', f"Ошибка получения выплат пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payouts_bp.route('/stats', methods=['GET'])
def get_payout_stats_api():
    """API для получения статистики выплат"""
    try:
        days = request.args.get('days', 30, type=int)
        stats = payout_manager.get_payout_statistics(days)

        return jsonify({'success': True, 'stats': stats})

    except Exception as e:
        log_message('error', f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payouts_bp.route('/control/start', methods=['POST'])
def start_auto_payouts_api():
    """API для запуска автоматических выплат"""
    try:
        payout_manager.start_auto_payouts()
        return jsonify({'success': True, 'message': 'Автоматические выплаты запущены'})
    except Exception as e:
        log_message('error', f"Ошибка запуска автоматических выплат: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@payouts_bp.route('/control/stop', methods=['POST'])
def stop_auto_payouts_api():
    """API для остановки автоматических выплат"""
    try:
        payout_manager.stop_auto_payouts()
        return jsonify({'success': True, 'message': 'Автоматические выплаты остановлены'})
    except Exception as e:
        log_message('error', f"Ошибка остановки автоматических выплат: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def create_payout_tables():
    """Создание дополнительных таблиц для системы выплат"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Обновляем таблицу payouts с дополнительными полями
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS payouts_extended
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           escrow_id
                           INTEGER,
                           recipient_id
                           INTEGER
                           NOT
                           NULL,
                           amount
                           DECIMAL
                       (
                           10,
                           2
                       ) NOT NULL,
                           currency VARCHAR
                       (
                           3
                       ) DEFAULT 'RUB',
                           status VARCHAR
                       (
                           20
                       ) NOT NULL DEFAULT 'pending',
                           trigger_type VARCHAR
                       (
                           30
                       ) NOT NULL DEFAULT 'manual_release',
                           transaction_id VARCHAR
                       (
                           255
                       ),
                           retry_count INTEGER DEFAULT 0,
                           last_error TEXT,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           scheduled_at TIMESTAMP,
                           processing_started_at TIMESTAMP,
                           completed_at TIMESTAMP,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           FOREIGN KEY
                       (
                           escrow_id
                       ) REFERENCES escrow_transactions
                       (
                           id
                       ),
                           FOREIGN KEY
                       (
                           recipient_id
                       ) REFERENCES users
                       (
                           id
                       )
                           )
                       ''')

        # Если старая таблица payouts существует, мигрируем данные
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payouts'")
        if cursor.fetchone():
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO payouts_extended 
                (id, escrow_id, recipient_id, amount, status, transaction_id, created_at, completed_at)
                           SELECT id,
                                  escrow_id,
                                  recipient_id,
                                  amount,
                                  status,
                                  transaction_id,
                                  created_at,
                                  completed_at
                           FROM payouts
                           ''')

            # Переименовываем таблицы
            cursor.execute('DROP TABLE IF EXISTS payouts_old')
            cursor.execute('ALTER TABLE payouts RENAME TO payouts_old')
            cursor.execute('ALTER TABLE payouts_extended RENAME TO payouts')

        # Создаем таблицу логов выплат
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS payout_logs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           payout_id
                           INTEGER
                           NOT
                           NULL,
                           status_from
                           VARCHAR
                       (
                           20
                       ),
                           status_to VARCHAR
                       (
                           20
                       ),
                           message TEXT,
                           error_details TEXT,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           FOREIGN KEY
                       (
                           payout_id
                       ) REFERENCES payouts
                       (
                           id
                       )
                           )
                       ''')

        # Индексы для оптимизации
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_recipient_id ON payouts(recipient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_status ON payouts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payouts_scheduled_at ON payouts(scheduled_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payout_logs_payout_id ON payout_logs(payout_id)')

        conn.commit()
        conn.close()

        log_message('info', "Таблицы системы выплат созданы/обновлены успешно")
        print_status("Таблицы системы выплат созданы успешно")
        return True

    except Exception as e:
        log_message('error', f"Ошибка создания таблиц системы выплат: {e}")
        print_status(f"Ошибка создания таблиц: {e}")
        return False


def register_payout_routes(app):
    """Регистрация маршрутов системы выплат в Flask приложении"""
    app.register_blueprint(payouts_bp)
    log_message('info', "Маршруты системы выплат зарегистрированы")


# Инициализация при импорте
if __name__ != '__main__':
    create_payout_tables()