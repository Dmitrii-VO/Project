# app/api/campaigns_management.py
"""
API для управления рекламными кампаниями
"""

from flask import Blueprint, request, jsonify, current_app
from app.models.database import db_manager
from app.services.auth_service import auth_service
import json
import datetime
from typing import Dict, Any, Optional

# Создание Blueprint
campaigns_bp = Blueprint('campaigns', __name__, url_prefix='/api/campaigns')

# === ВАЛИДАЦИЯ ===

class CampaignValidator:
    @staticmethod
    def validate_campaign_data(data: Dict[str, Any]) -> list:
        """Валидация данных кампании"""
        errors = []
        
        # Обязательные поля
        if not data.get('name', '').strip():
            errors.append('Название кампании обязательно')
        
        if not data.get('start_date'):
            errors.append('Дата начала кампании обязательна')
            
        if not data.get('end_date'):
            errors.append('Дата окончания кампании обязательна')
            
        if not data.get('ad_content', '').strip():
            errors.append('Содержание рекламного поста обязательно')
            
        # Проверка типа рекламодателя
        advertiser_type = data.get('advertiser_type', '').strip()
        if not advertiser_type:
            errors.append('Тип рекламодателя обязателен')
        elif advertiser_type not in ['legal_entity', 'individual_entrepreneur', 'physical_person']:
            errors.append('Неверный тип рекламодателя')
        
        # Проверка бюджета
        budget = data.get('budget_limit', 0)
        try:
            budget = float(budget)
            if budget < 0:
                errors.append('Бюджет не может быть отрицательным')
        except (ValueError, TypeError):
            errors.append('Неверный формат бюджета')
            
        # Проверка дат
        try:
            start_date = datetime.datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            
            if start_date > end_date:
                errors.append('Дата начала не может быть позже даты окончания')
                
            # Проверяем, что дата начала не в прошлом (для новых кампаний)
            if start_date < datetime.date.today():
                errors.append('Дата начала не может быть в прошлом')
                
        except (ValueError, TypeError):
            errors.append('Неверный формат даты')
        
        # Проверка длины полей
        name = data.get('name', '').strip()
        if name and (len(name) < 3 or len(name) > 200):
            errors.append('Название должно быть от 3 до 200 символов')
            
        ad_content = data.get('ad_content', '').strip()
        if ad_content and len(ad_content) > 4000:
            errors.append('Рекламный пост не должен превышать 4000 символов')
            
        # Проверка ИНН
        inn = data.get('advertiser_inn', '').strip()
        if inn and not inn.isdigit():
            errors.append('ИНН должен содержать только цифры')
        if inn and len(inn) not in [10, 12]:
            errors.append('ИНН должен содержать 10 или 12 цифр')
            
        return errors

# === API ENDPOINTS ===

@campaigns_bp.route('', methods=['POST'])
def create_campaign():
    """Создание новой кампании"""
    try:
        # Получаем user_db_id из авторизации
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Отсутствуют данные'
            }), 400
        
        # Валидация данных
        errors = CampaignValidator.validate_campaign_data(data)
        if errors:
            return jsonify({
                'success': False,
                'error': 'Ошибки валидации',
                'errors': errors
            }), 400
        
        # Подготавливаем данные для вставки
        campaign_data = {
            'name': data['name'].strip(),
            'budget_limit': float(data.get('budget_limit', 0)),
            'add_utm_tags': bool(data.get('add_utm_tags', False)),
            'track_clicks': bool(data.get('track_clicks', False)),
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'work_weekends': bool(data.get('work_weekends', True)),
            'work_hours_only': bool(data.get('work_hours_only', False)),
            'advertiser_type': data.get('advertiser_type', '').strip(),
            'product_name': data.get('product_name', '').strip(),
            'advertiser_inn': data.get('advertiser_inn', '').strip(),
            'ad_content': data['ad_content'].strip(),
            'status': data.get('status', 'draft'),
            'created_by': user_db_id,
            'related_offer_id': data.get('related_offer_id') if data.get('related_offer_id') else None
        }
        
        # Создаем кампанию
        campaign_id = db_manager.execute_query('''
            INSERT INTO campaigns (
                name, budget_limit, add_utm_tags, track_clicks, 
                start_date, end_date, work_weekends, work_hours_only,
                advertiser_custom, product_name, advertiser_inn,
                ad_content, status, created_by, related_offer_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            campaign_data['name'],
            campaign_data['budget_limit'],
            campaign_data['add_utm_tags'],
            campaign_data['track_clicks'],
            campaign_data['start_date'],
            campaign_data['end_date'],
            campaign_data['work_weekends'],
            campaign_data['work_hours_only'],
            campaign_data['advertiser_type'],
            campaign_data['product_name'],
            campaign_data['advertiser_inn'],
            campaign_data['ad_content'],
            campaign_data['status'],
            campaign_data['created_by'],
            campaign_data['related_offer_id'],
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat()
        ))
        
        if not campaign_id:
            raise Exception('Ошибка создания кампании в базе данных')
        
        # Получаем созданную кампанию
        campaign = db_manager.execute_query('''
            SELECT * FROM v_campaigns_full WHERE id = ?
        ''', (campaign_id,), fetch_one=True)
        
        current_app.logger.info(f"✅ Кампания создана: ID {campaign_id}, пользователь {user_db_id}")
        
        return jsonify({
            'success': True,
            'message': 'Кампания создана успешно',
            'campaign': dict(campaign) if campaign else {'id': campaign_id}
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка создания кампании: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка создания кампании: {str(e)}'
        }), 500

@campaigns_bp.route('', methods=['GET'])
def get_campaigns():
    """Получение списка кампаний пользователя"""
    try:
        # Получаем user_db_id из авторизации
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401
        
        # Параметры фильтрации
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Базовый запрос
        query = 'SELECT * FROM v_campaigns_full WHERE created_by = ?'
        params = [user_db_id]
        
        # Добавляем фильтр по статусу
        if status:
            query += ' AND status = ?'
            params.append(status)
            
        # Сортировка и пагинация
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        campaigns = db_manager.execute_query(query, tuple(params), fetch_all=True)
        
        # Получаем общее количество
        count_query = 'SELECT COUNT(*) as total FROM campaigns WHERE created_by = ?'
        count_params = [user_db_id]
        
        if status:
            count_query += ' AND status = ?'
            count_params.append(status)
            
        total_result = db_manager.execute_query(count_query, tuple(count_params), fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        return jsonify({
            'success': True,
            'campaigns': campaigns or [],
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка получения кампаний: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка получения кампаний: {str(e)}'
        }), 500

@campaigns_bp.route('/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id: int):
    """Получение кампании по ID"""
    try:
        # Получаем user_db_id из авторизации
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401
        
        # Получаем кампанию
        campaign = db_manager.execute_query('''
            SELECT * FROM v_campaigns_full 
            WHERE id = ? AND created_by = ?
        ''', (campaign_id, user_db_id), fetch_one=True)
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Кампания не найдена'
            }), 404
        
        return jsonify({
            'success': True,
            'campaign': dict(campaign)
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка получения кампании {campaign_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка получения кампании: {str(e)}'
        }), 500

@campaigns_bp.route('/advertisers', methods=['GET'])
def get_advertisers():
    """Получение списка рекламодателей"""
    try:
        advertisers = db_manager.execute_query('''
            SELECT id, name, inn, contact_person 
            FROM campaign_advertisers 
            WHERE status = 'active'
            ORDER BY name
        ''', fetch_all=True)
        
        return jsonify({
            'success': True,
            'advertisers': advertisers or []
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка получения рекламодателей: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка получения рекламодателей: {str(e)}'
        }), 500

@campaigns_bp.route('/advertisers', methods=['POST'])
def create_advertiser():
    """Создание нового рекламодателя"""
    try:
        # Получаем user_db_id из авторизации
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401
        
        data = request.get_json()
        if not data or not data.get('name', '').strip():
            return jsonify({
                'success': False,
                'error': 'Название рекламодателя обязательно'
            }), 400
        
        # Проверяем уникальность названия
        existing = db_manager.execute_query('''
            SELECT id FROM campaign_advertisers WHERE name = ?
        ''', (data['name'].strip(),), fetch_one=True)
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Рекламодатель с таким названием уже существует'
            }), 400
        
        # Создаем рекламодателя
        advertiser_id = db_manager.execute_query('''
            INSERT INTO campaign_advertisers (name, inn, contact_person, email, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'].strip(),
            data.get('inn', '').strip(),
            data.get('contact_person', '').strip(),
            data.get('email', '').strip(),
            data.get('phone', '').strip()
        ))
        
        # Получаем созданного рекламодателя
        advertiser = db_manager.execute_query('''
            SELECT * FROM campaign_advertisers WHERE id = ?
        ''', (advertiser_id,), fetch_one=True)
        
        current_app.logger.info(f"✅ Рекламодатель создан: ID {advertiser_id}")
        
        return jsonify({
            'success': True,
            'message': 'Рекламодатель создан успешно',
            'advertiser': dict(advertiser) if advertiser else {'id': advertiser_id}
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка создания рекламодателя: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка создания рекламодателя: {str(e)}'
        }), 500

@campaigns_bp.route('/<int:campaign_id>/status', methods=['PATCH'])
def update_campaign_status(campaign_id: int):
    """Обновление статуса кампании"""
    try:
        # Получаем user_db_id из авторизации
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            return jsonify({
                'success': False,
                'error': 'Необходима авторизация'
            }), 401
        
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['draft', 'active', 'paused', 'completed', 'cancelled']:
            return jsonify({
                'success': False,
                'error': 'Неверный статус кампании'
            }), 400
        
        # Обновляем статус
        rows_affected = db_manager.execute_query('''
            UPDATE campaigns 
            SET status = ?, updated_at = ?
            WHERE id = ? AND created_by = ?
        ''', (new_status, datetime.datetime.now().isoformat(), campaign_id, user_db_id))
        
        if not rows_affected:
            return jsonify({
                'success': False,
                'error': 'Кампания не найдена'
            }), 404
        
        current_app.logger.info(f"✅ Статус кампании {campaign_id} изменен на {new_status}")
        
        return jsonify({
            'success': True,
            'message': f'Статус кампании изменен на {new_status}'
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Ошибка обновления статуса кампании {campaign_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка обновления статуса: {str(e)}'
        }), 500

# Экспорт Blueprint
__all__ = ['campaigns_bp']