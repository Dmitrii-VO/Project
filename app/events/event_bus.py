#!/usr/bin/env python3
"""
Event Bus для Telegram Mini App
Центральная система обработки событий
"""

import asyncio
import logging
import json
from typing import Callable, Dict, List, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading
import queue
import time

from .event_types import BaseEvent, EventType

logger = logging.getLogger(__name__)

class EventHandler:
    """Обработчик событий"""
    
    def __init__(self, callback: Callable, event_types: List[EventType], 
                 priority: int = 0, async_handler: bool = False):
        self.callback = callback
        self.event_types = event_types
        self.priority = priority
        self.async_handler = async_handler
        self.handler_id = id(self)
        
    def can_handle(self, event_type: EventType) -> bool:
        """Проверка, может ли обработчик обработать событие"""
        return event_type in self.event_types
    
    def handle(self, event: BaseEvent) -> Any:
        """Обработка события"""
        try:
            if self.async_handler:
                return asyncio.create_task(self.callback(event))
            else:
                return self.callback(event)
        except Exception as e:
            logger.error(f"Ошибка в обработчике {self.handler_id}: {e}")
            raise

class EventBus:
    """Шина событий"""
    
    def __init__(self, max_workers: int = 10, queue_size: int = 1000):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_queue = queue.Queue(maxsize=queue_size)
        self._processing = False
        self._worker_thread = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self._stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_registered': 0
        }
        
        # Middleware функции
        self._before_publish_middleware: List[Callable] = []
        self._after_publish_middleware: List[Callable] = []
        self._before_handle_middleware: List[Callable] = []
        self._after_handle_middleware: List[Callable] = []
        
        # Персистентность событий
        self._persistent_storage: Optional[Callable] = None
        self._failed_events: List[BaseEvent] = []
        
    def start(self):
        """Запуск обработки событий"""
        if not self._processing:
            self._processing = True
            self._worker_thread = threading.Thread(target=self._process_events, daemon=True)
            self._worker_thread.start()
            logger.info("EventBus запущен")
    
    def stop(self):
        """Остановка обработки событий"""
        if self._processing:
            self._processing = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5)
            self._executor.shutdown(wait=True)
            logger.info("EventBus остановлен")
    
    def register_handler(self, event_types: Union[EventType, List[EventType]], 
                        callback: Callable, priority: int = 0, 
                        async_handler: bool = False) -> str:
        """Регистрация обработчика событий"""
        if isinstance(event_types, EventType):
            event_types = [event_types]
        
        handler = EventHandler(callback, event_types, priority, async_handler)
        
        with self._lock:
            for event_type in event_types:
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                self._handlers[event_type].append(handler)
                # Сортируем по приоритету (больший приоритет = раньше обработка)
                self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
            
            self._stats['handlers_registered'] += 1
        
        logger.info(f"Зарегистрирован обработчик {handler.handler_id} для {event_types}")
        return str(handler.handler_id)
    
    def register_global_handler(self, callback: Callable, priority: int = 0, 
                               async_handler: bool = False) -> str:
        """Регистрация глобального обработчика для всех событий"""
        handler = EventHandler(callback, list(EventType), priority, async_handler)
        
        with self._lock:
            self._global_handlers.append(handler)
            self._global_handlers.sort(key=lambda h: h.priority, reverse=True)
            self._stats['handlers_registered'] += 1
        
        logger.info(f"Зарегистрирован глобальный обработчик {handler.handler_id}")
        return str(handler.handler_id)
    
    def unregister_handler(self, handler_id: str):
        """Отмена регистрации обработчика"""
        handler_id_int = int(handler_id)
        
        with self._lock:
            # Удаляем из конкретных типов событий
            for event_type in list(self._handlers.keys()):
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] 
                    if h.handler_id != handler_id_int
                ]
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
            
            # Удаляем из глобальных обработчиков
            self._global_handlers = [
                h for h in self._global_handlers 
                if h.handler_id != handler_id_int
            ]
        
        logger.info(f"Обработчик {handler_id} удален")
    
    def publish(self, event: BaseEvent, sync: bool = False) -> bool:
        """Публикация события"""
        try:
            # Применяем middleware перед публикацией
            for middleware in self._before_publish_middleware:
                event = middleware(event) or event
            
            self._stats['events_published'] += 1
            
            # Сохраняем событие если настроено персистентное хранилище
            if self._persistent_storage:
                self._persistent_storage(event)
            
            if sync:
                # Синхронная обработка
                self._handle_event(event)
            else:
                # Асинхронная обработка через очередь
                if not self._event_queue.full():
                    self._event_queue.put(event)
                else:
                    logger.warning("Очередь событий переполнена, событие отброшено")
                    return False
            
            # Применяем middleware после публикации
            for middleware in self._after_publish_middleware:
                middleware(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка публикации события {event.event_type}: {e}")
            self._stats['events_failed'] += 1
            return False
    
    def _process_events(self):
        """Основной цикл обработки событий"""
        while self._processing:
            try:
                # Получаем событие из очереди с таймаутом
                event = self._event_queue.get(timeout=1.0)
                
                # Обрабатываем событие в пуле потоков
                future = self._executor.submit(self._handle_event, event)
                
                # Не блокируем основной поток
                self._event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в цикле обработки событий: {e}")
    
    def _handle_event(self, event: BaseEvent):
        """Обработка конкретного события"""
        try:
            # Применяем middleware перед обработкой
            for middleware in self._before_handle_middleware:
                event = middleware(event) or event
            
            handlers_executed = 0
            
            # Получаем обработчики для конкретного типа события
            event_handlers = self._handlers.get(event.event_type, [])
            
            # Добавляем глобальные обработчики
            all_handlers = event_handlers + self._global_handlers
            
            # Сортируем по приоритету
            all_handlers.sort(key=lambda h: h.priority, reverse=True)
            
            # Выполняем обработчики
            for handler in all_handlers:
                try:
                    if handler.can_handle(event.event_type):
                        handler.handle(event)
                        handlers_executed += 1
                except Exception as e:
                    logger.error(f"Ошибка в обработчике {handler.handler_id}: {e}")
                    self._stats['events_failed'] += 1
            
            if handlers_executed > 0:
                self._stats['events_processed'] += 1
                logger.debug(f"Событие {event.event_type} обработано {handlers_executed} обработчиками")
            else:
                logger.debug(f"Нет обработчиков для события {event.event_type}")
            
            # Применяем middleware после обработки
            for middleware in self._after_handle_middleware:
                middleware(event)
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке события: {e}")
            self._failed_events.append(event)
            self._stats['events_failed'] += 1
    
    def add_middleware(self, middleware_type: str, callback: Callable):
        """Добавление middleware"""
        middleware_map = {
            'before_publish': self._before_publish_middleware,
            'after_publish': self._after_publish_middleware,
            'before_handle': self._before_handle_middleware,
            'after_handle': self._after_handle_middleware
        }
        
        if middleware_type in middleware_map:
            middleware_map[middleware_type].append(callback)
            logger.info(f"Добавлен {middleware_type} middleware")
        else:
            raise ValueError(f"Неизвестный тип middleware: {middleware_type}")
    
    def set_persistent_storage(self, storage_callback: Callable):
        """Настройка персистентного хранилища событий"""
        self._persistent_storage = storage_callback
        logger.info("Настроено персистентное хранилище событий")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            **self._stats,
            'queue_size': self._event_queue.qsize(),
            'failed_events_count': len(self._failed_events),
            'active_handlers': sum(len(handlers) for handlers in self._handlers.values()) + len(self._global_handlers),
            'is_processing': self._processing
        }
    
    def get_failed_events(self) -> List[BaseEvent]:
        """Получение неудачных событий"""
        return self._failed_events.copy()
    
    def clear_failed_events(self):
        """Очистка неудачных событий"""
        self._failed_events.clear()
        logger.info("Очищены неудачные события")
    
    def retry_failed_events(self):
        """Повторная обработка неудачных событий"""
        if not self._failed_events:
            return
        
        failed_events = self._failed_events.copy()
        self._failed_events.clear()
        
        for event in failed_events:
            self.publish(event)
        
        logger.info(f"Повторно отправлено {len(failed_events)} неудачных событий")

# Глобальный экземпляр Event Bus
event_bus = EventBus()

# Декораторы для удобной регистрации обработчиков
def event_handler(event_types: Union[EventType, List[EventType]], 
                 priority: int = 0, async_handler: bool = False):
    """Декоратор для регистрации обработчика событий"""
    def decorator(func):
        event_bus.register_handler(event_types, func, priority, async_handler)
        return func
    return decorator

def global_event_handler(priority: int = 0, async_handler: bool = False):
    """Декоратор для регистрации глобального обработчика"""
    def decorator(func):
        event_bus.register_global_handler(func, priority, async_handler)
        return func
    return decorator

# Middleware для логирования
def logging_middleware(event: BaseEvent) -> BaseEvent:
    """Middleware для логирования всех событий"""
    logger.info(f"📧 Событие: {event.event_type.value} | ID: {event.event_id} | User: {event.user_id}")
    return event

# Middleware для персистентности в базе данных
def database_persistence_middleware(event: BaseEvent):
    """Сохранение событий в базу данных"""
    try:
        from app.models.database import execute_db_query
        
        execute_db_query(
            """INSERT INTO analytics_events 
               (user_id, event_type, event_data, session_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                event.user_id,
                event.event_type.value,
                json.dumps(event.to_dict()),
                event.session_id,
                event.timestamp
            )
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения события в БД: {e}")

# Инициализация middleware по умолчанию
event_bus.add_middleware('before_handle', logging_middleware)
event_bus.set_persistent_storage(database_persistence_middleware)