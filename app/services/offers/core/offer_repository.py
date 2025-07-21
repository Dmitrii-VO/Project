# app/services/offers/core/offer_repository.py
"""
Репозиторий для работы с офферами в базе данных
Заменяет прямые SQL запросы на централизованные методы
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from app.models.database import execute_db_query
from app.models.offer import Offer, OfferStatus
from app.config.telegram_config import AppConfig
import logging

logger = logging.getLogger(__name__)


class OfferRepository:
    """Централизованный репозиторий для работы с офферами"""
    
    @staticmethod
    def get_user_offers(user_db_id: int, filters: Dict[str, Any] = None) -> Tuple[List[Dict], int]:
        """Получение офферов пользователя с фильтрами и пагинацией"""
        filters = filters or {}
        
        page = filters.get('page', 1)
        limit = filters.get('limit', 50)
        offset = (page - 1) * limit
        
        # Строим базовый запрос
        base_query = """
            SELECT o.id, o.title, o.description, o.content, o.price, o.currency,
                   o.category, o.status, o.created_at, o.updated_at,
                   o.target_audience, o.requirements, o.deadline, o.budget_total,
                   o.duration_days, o.min_subscribers, o.max_subscribers, o.metadata,
                   u.username as creator_username, u.first_name as creator_name,
                   u.telegram_id as creator_telegram_id, o.created_by as creator_db_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.created_by = ?
        """
        
        count_query = "SELECT COUNT(*) as total FROM offers o WHERE o.created_by = ?"
        params = [user_db_id]
        
        # Добавляем фильтры
        if filters.get('status'):
            base_query += " AND o.status = ?"
            count_query += " AND o.status = ?"
            params.append(filters['status'])
            
        if filters.get('search'):
            base_query += " AND (o.title LIKE ? OR o.description LIKE ?)"
            count_query += " AND (o.title LIKE ? OR o.description LIKE ?)"
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])
            
        if filters.get('category'):
            base_query += " AND o.category = ?"
            count_query += " AND o.category = ?"
            params.append(filters['category'])
        
        # Получаем общее количество
        total_count = execute_db_query(count_query, tuple(params), fetch_one=True)['total']
        
        # Добавляем сортировку и пагинацию
        base_query += " ORDER BY o.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Получаем офферы
        offers = execute_db_query(base_query, tuple(params), fetch_all=True)
        
        return [dict(offer) for offer in offers], total_count
    
    @staticmethod
    def get_available_offers(user_db_id: Optional[int] = None, filters: Dict[str, Any] = None) -> Tuple[List[Dict], int]:
        """Получение доступных офферов для владельцев каналов"""
        filters = filters or {}
        
        page = filters.get('page', 1) 
        limit = filters.get('limit', 10)
        offset = (page - 1) * limit
        
        base_query = """
            SELECT o.*, u.username as creator_username, u.first_name as creator_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE 1=1
        """
        
        count_query = """
            SELECT COUNT(*) as total
            FROM offers o
            JOIN users u ON o.created_by = u.id  
            WHERE 1=1
        """
        
        params = []
        
        # Фильтр по статусу (по умолчанию только активные)
        status_filter = filters.get('status', 'active')
        if status_filter:
            base_query += " AND o.status = ?"
            count_query += " AND o.status = ?"
            params.append(status_filter)
        
        # Исключаем собственные офферы
        if user_db_id:
            base_query += " AND o.created_by != ?"
            count_query += " AND o.created_by != ?"
            params.append(user_db_id)
        
        # Фильтр по поиску
        if filters.get('search'):
            base_query += " AND (o.title LIKE ? OR o.description LIKE ?)"
            count_query += " AND (o.title LIKE ? OR o.description LIKE ?)"
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])
        
        # Фильтр по категории
        if filters.get('category'):
            base_query += " AND o.category = ?"
            count_query += " AND o.category = ?"
            params.append(filters['category'])
        
        # Получаем общее количество
        total_count = execute_db_query(count_query, tuple(params), fetch_one=True)['total']
        
        # Добавляем сортировку и пагинацию
        base_query += " ORDER BY o.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Получаем офферы
        offers = execute_db_query(base_query, tuple(params), fetch_all=True)
        
        return [dict(offer) for offer in offers], total_count
    
    @staticmethod
    def get_offer_by_id(offer_id: int, user_db_id: Optional[int] = None) -> Optional[Dict]:
        """Получение оффера по ID с проверкой прав доступа"""
        query = """
            SELECT o.*, u.username as creator_username, u.first_name as creator_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """
        params = [offer_id]
        
        if user_db_id:
            query += " AND o.created_by = ?"
            params.append(user_db_id)
        
        result = execute_db_query(query, tuple(params), fetch_one=True)
        return dict(result) if result else None
    
    @staticmethod
    def create_offer(user_db_id: int, offer_data: Dict[str, Any]) -> int:
        """Создание нового оффера"""
        # Подготовка метаданных
        metadata = {
            'posting_requirements': offer_data.get('posting_requirements', {}),
            'additional_info': offer_data.get('additional_info', ''),
            'creator_telegram_id': offer_data.get('creator_telegram_id')
        }
        
        # Создаем оффер
        offer_id = execute_db_query("""
            INSERT INTO offers (created_by, title, description, content, price, currency,
                               target_audience, requirements, deadline, status, category,
                               metadata, budget_total, expires_at, duration_days,
                               min_subscribers, max_subscribers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_db_id,
            offer_data['title'],
            offer_data['description'],
            offer_data.get('content', offer_data['description']),
            float(offer_data['price']),
            offer_data.get('currency', 'RUB'),
            offer_data['target_audience'],
            offer_data.get('requirements', ''),
            offer_data.get('deadline'),
            offer_data.get('status', 'active'),
            offer_data.get('category', 'general'),
            json.dumps(metadata),
            float(offer_data.get('budget_total', offer_data['price'])),
            offer_data.get('expires_at'),
            int(offer_data.get('duration_days', 30)),
            int(offer_data.get('min_subscribers', 0)),
            int(offer_data.get('max_subscribers', 0))
        ))
        
        return offer_id
    
    @staticmethod
    def update_offer_status(offer_id: int, new_status: str, reason: str = '') -> bool:
        """Обновление статуса оффера"""
        try:
            execute_db_query("""
                UPDATE offers 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, offer_id))
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса оффера {offer_id}: {e}")
            return False
    
    @staticmethod
    def delete_offer(offer_id: int, user_db_id: int) -> bool:
        """Удаление оффера с проверкой прав"""
        try:
            # Проверяем права доступа
            offer = execute_db_query(
                'SELECT created_by FROM offers WHERE id = ?',
                (offer_id,),
                fetch_one=True
            )
            
            if not offer or offer['created_by'] != user_db_id:
                return False
            
            # Удаляем в транзакции
            conn = sqlite3.connect(AppConfig.DATABASE_PATH)
            conn.execute('BEGIN TRANSACTION')
            
            try:
                conn.execute('DELETE FROM offer_responses WHERE offer_id = ?', (offer_id,))
                conn.execute('DELETE FROM offer_proposals WHERE offer_id = ?', (offer_id,))
                conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
                return False
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Ошибка при удалении оффера {offer_id}: {e}")
            return False
    
    @staticmethod
    def get_offer_statistics(user_db_id: int) -> Dict[str, Any]:
        """Получение статистики офферов пользователя"""
        stats = execute_db_query("""
            SELECT COUNT(*) as total_offers,
                   COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers,
                   COALESCE(SUM(CASE WHEN status IN ('completed', 'active') THEN price ELSE 0 END), 0) as total_spent,
                   COUNT(or_resp.id) as total_responses,
                   COUNT(CASE WHEN or_resp.status = 'accepted' THEN 1 END) as accepted_responses
            FROM offers o
            LEFT JOIN offer_responses or_resp ON o.id = or_resp.offer_id
            WHERE o.created_by = ?
        """, (user_db_id,), fetch_one=True)
        
        return {
            'total_offers': stats['total_offers'] or 0,
            'active_offers': stats['active_offers'] or 0,
            'total_spent': float(stats['total_spent']) if stats['total_spent'] else 0,
            'total_responses': stats['total_responses'] or 0,
            'accepted_responses': stats['accepted_responses'] or 0
        }
    
    @staticmethod
    def get_offer_responses(offer_id: int, user_db_id: int) -> List[Dict]:
        """Получение откликов на оффер с проверкой прав"""
        # Проверяем права доступа к офферу
        offer = execute_db_query("""
            SELECT o.*, u.telegram_id as owner_telegram_id
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ? AND o.created_by = ?
        """, (offer_id, user_db_id), fetch_one=True)
        
        if not offer:
            return []
        
        # Получаем отклики
        responses = execute_db_query("""
            SELECT or_resp.*,
                   u.first_name || ' ' || COALESCE(u.last_name, '') as channel_owner_name,
                   u.username as channel_owner_username,
                   u.telegram_id as channel_owner_telegram_id,
                   pl.id as placement_id,
                   pl.status as placement_status,
                   pl.deadline as placement_deadline
            FROM offer_responses or_resp
            JOIN users u ON or_resp.user_id = u.id
            LEFT JOIN offer_placements pl ON or_resp.id = pl.response_id
            WHERE or_resp.offer_id = ?
            ORDER BY or_resp.created_at DESC
        """, (offer_id,), fetch_all=True)
        
        return [dict(response) for response in responses]
    
    @staticmethod 
    def get_offer_response_statistics(offer_ids: List[int]) -> Dict[int, Dict]:
        """Получение статистики откликов для нескольких офферов одним запросом"""
        if not offer_ids:
            return {}
        
        offer_ids_str = ','.join(str(oid) for oid in offer_ids)
        
        response_stats = execute_db_query(f"""
            SELECT offer_id,
                   COUNT(*) as total_count,
                   COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count,
                   COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                   COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
            FROM offer_responses 
            WHERE offer_id IN ({offer_ids_str})
            GROUP BY offer_id
        """, fetch_all=True)
        
        # Создаем словарь для быстрого поиска
        stats_dict = {}
        for stat in response_stats:
            stats_dict[stat['offer_id']] = {
                'total_count': stat['total_count'],
                'accepted_count': stat['accepted_count'],
                'pending_count': stat['pending_count'],
                'rejected_count': stat['rejected_count']
            }
        
        return stats_dict
    
    @staticmethod
    def create_offer_proposals(offer_id: int, channel_ids: List[int]) -> List[Dict]:
        """Создание предложений для выбранных каналов"""
        created_proposals = []
        
        conn = sqlite3.connect(AppConfig.DATABASE_PATH)
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN')
            
            for channel_id in channel_ids:
                # Проверяем канал
                cursor.execute("""
                    SELECT id, title, owner_id 
                    FROM channels 
                    WHERE id = ? AND is_active = 1
                """, (channel_id,))
                
                channel = cursor.fetchone()
                if not channel:
                    continue
                
                # Проверяем дубликат
                cursor.execute("""
                    SELECT id FROM offer_proposals 
                    WHERE offer_id = ? AND channel_id = ?
                """, (offer_id, channel_id))
                
                if cursor.fetchone():
                    continue
                
                # Создаем предложение
                cursor.execute("""
                    INSERT INTO offer_proposals (
                        offer_id, channel_id, status, created_at, 
                        expires_at, notified_at
                    ) VALUES (?, ?, 'sent', CURRENT_TIMESTAMP, 
                             datetime('now', '+7 days'), CURRENT_TIMESTAMP)
                """, (offer_id, channel_id))
                
                created_proposals.append({
                    'proposal_id': cursor.lastrowid,
                    'channel_id': channel_id,
                    'channel_title': channel[1],
                    'channel_owner_id': channel[2]
                })
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка создания предложений: {e}")
            raise e
        finally:
            conn.close()
        
        return created_proposals