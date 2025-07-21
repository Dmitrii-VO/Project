# app/services/offers/api/offer_management.py
"""
Маршруты для управления офферами (административные функции)
Заменяет функциональность из offers_management.py
"""

from flask import Blueprint, request, jsonify
from app.services.offers import OfferService, OfferValidator, OfferMatcher
from app.utils.response_utils import success_response, error_response
import logging

logger = logging.getLogger(__name__)

offer_management = Blueprint('offer_management', __name__)
offer_service = OfferService()
offer_matcher = OfferMatcher()


@offer_management.route('/recommendations/<int:offer_id>', methods=['GET'])
def get_offer_recommendations(offer_id):
    """Получение рекомендованных каналов для оффера"""
    try:
        limit = int(request.args.get('limit', 20))
        
        # Получаем рекомендации через утилиту
        channels = offer_matcher.get_recommended_channels(offer_id, limit)
        
        return success_response(
            data={
                'offer_id': offer_id,
                'recommended_channels': channels,
                'count': len(channels)
            },
            message="Рекомендации получены"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка получения рекомендаций для оффера {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_management.route('/check-eligibility', methods=['POST'])
def check_channel_eligibility():
    """Проверка подходности канала для оффера"""
    try:
        data = request.get_json()
        if not data or 'offer_id' not in data or 'channel_id' not in data:
            return error_response("Требуются offer_id и channel_id", 400)
        
        offer_id = int(data['offer_id'])
        channel_id = int(data['channel_id'])
        
        # Проверяем подходность
        result = offer_matcher.check_channel_eligibility(offer_id, channel_id)
        
        return success_response(
            data=result,
            message="Проверка завершена"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка проверки подходности канала: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_management.route('/matching-channels/<int:offer_id>', methods=['GET'])
def find_matching_channels(offer_id):
    """Поиск подходящих каналов для оффера"""
    try:
        # Получаем оффер
        offer_details = offer_service.get_offer_details(offer_id)
        if not offer_details['success']:
            return error_response("Оффер не найден", 404)
        
        offer = offer_details['offer']
        
        # Получаем фильтры из параметров запроса
        filters = {
            'limit': int(request.args.get('limit', 50)),
            'min_acceptance_rate': float(request.args.get('min_acceptance_rate', 0))
        }
        
        # Ищем подходящие каналы
        channels = offer_matcher.find_matching_channels(offer, filters)
        
        return success_response(
            data={
                'offer_id': offer_id,
                'matching_channels': channels,
                'count': len(channels),
                'filters': filters
            },
            message="Подходящие каналы найдены"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка поиска подходящих каналов для оффера {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_management.route('/bulk-actions', methods=['POST'])
def bulk_actions():
    """Массовые операции с офферами"""
    try:
        data = request.get_json()
        if not data or 'action' not in data or 'offer_ids' not in data:
            return error_response("Требуются action и offer_ids", 400)
        
        action = data['action']
        offer_ids = data['offer_ids']
        
        if not isinstance(offer_ids, list) or not offer_ids:
            return error_response("offer_ids должен быть непустым списком", 400)
        
        results = []
        
        # Выполняем действие для каждого оффера
        for offer_id in offer_ids:
            try:
                if action == 'pause':
                    result = offer_service.update_offer_status(
                        offer_id, 'paused', 'Массовая операция'
                    )
                elif action == 'activate':
                    result = offer_service.update_offer_status(
                        offer_id, 'active', 'Массовая операция'
                    )
                elif action == 'cancel':
                    result = offer_service.update_offer_status(
                        offer_id, 'cancelled', 'Массовая операция'
                    )
                elif action == 'delete':
                    result = offer_service.delete_offer(offer_id)
                else:
                    results.append({
                        'offer_id': offer_id,
                        'success': False,
                        'error': f"Неизвестное действие: {action}"
                    })
                    continue
                
                results.append({
                    'offer_id': offer_id,
                    'success': result['success'],
                    'message': result.get('message', '')
                })
                
            except Exception as e:
                results.append({
                    'offer_id': offer_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Подсчитываем статистику
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        return success_response(
            data={
                'action': action,
                'results': results,
                'summary': {
                    'total': total,
                    'successful': successful,
                    'failed': total - successful
                }
            },
            message=f"Массовая операция завершена: {successful}/{total} успешно"
        )
        
    except Exception as e:
        logger.error(f"Ошибка массовой операции: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_management.route('/export', methods=['GET'])
def export_offers():
    """Экспорт офферов пользователя"""
    try:
        # Получаем все офферы пользователя
        result = offer_service.get_my_offers({'limit': 1000})
        
        if not result['success']:
            return error_response("Ошибка получения офферов", 500)
        
        from datetime import datetime
        
        # Подготавливаем данные для экспорта
        export_data = {
            'export_date': offer_service.formatter._format_datetime(str(datetime.now())),
            'total_offers': result['total_count'],
            'offers': result['offers']
        }
        
        return success_response(
            data=export_data,
            message="Данные подготовлены для экспорта"
        )
        
    except Exception as e:
        logger.error(f"Ошибка экспорта офферов: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_management.route('/analytics', methods=['GET'])
def get_offers_analytics():
    """Получение аналитики по офферам"""
    try:
        # Получаем базовую статистику
        stats_result = offer_service.get_offer_statistics()
        
        if not stats_result['success']:
            return error_response("Ошибка получения статистики", 500)
        
        # Получаем все офферы для аналитики
        offers_result = offer_service.get_my_offers({'limit': 1000})
        
        analytics = {
            'basic_stats': stats_result['stats'],
            'offers_by_status': {},
            'offers_by_category': {},
            'monthly_creation': {},
            'performance_metrics': {}
        }
        
        if offers_result['success']:
            offers = offers_result['offers']
            
            # Анализ по статусам
            for offer in offers:
                status = offer['status']
                analytics['offers_by_status'][status] = analytics['offers_by_status'].get(status, 0) + 1
            
            # Анализ по категориям
            for offer in offers:
                category = offer['category']
                analytics['offers_by_category'][category] = analytics['offers_by_category'].get(category, 0) + 1
            
            # Метрики производительности
            total_responses = sum(offer['statistics']['total_responses'] for offer in offers)
            total_accepted = sum(offer['statistics']['accepted_responses'] for offer in offers)
            
            analytics['performance_metrics'] = {
                'average_responses_per_offer': round(total_responses / len(offers), 2) if offers else 0,
                'overall_acceptance_rate': round((total_accepted / total_responses * 100), 2) if total_responses > 0 else 0,
                'most_popular_category': max(analytics['offers_by_category'].items(), key=lambda x: x[1])[0] if analytics['offers_by_category'] else None
            }
        
        return success_response(
            data=analytics,
            message="Аналитика получена"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения аналитики: {e}")
        return error_response("Внутренняя ошибка сервера", 500)