# app/services/offers/api/offer_routes.py
"""
Основные маршруты для работы с офферами
Заменяет основную функциональность из offers.py
"""

from flask import Blueprint, request, jsonify
from app.services.offers import OfferService, OfferValidator
from app.utils.response_utils import success_response, error_response
import logging

logger = logging.getLogger(__name__)

offer_routes = Blueprint('offer_routes', __name__)
offer_service = OfferService()


@offer_routes.route('/my-offers', methods=['GET'])
def get_my_offers():
    """Получение моих офферов"""
    try:
        # Получаем и валидируем фильтры
        filters = OfferValidator.validate_offer_filters(request.args.to_dict())
        
        # Получаем офферы через сервис
        result = offer_service.get_my_offers(filters)
        
        return success_response(
            data=result,
            message="Офферы успешно получены"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка получения офферов пользователя: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/available', methods=['GET'])
def get_available_offers():
    """Получение доступных офферов для владельцев каналов"""
    try:
        # Получаем и валидируем фильтры
        filters = OfferValidator.validate_offer_filters(request.args.to_dict())
        
        # Получаем офферы через сервис
        result = offer_service.get_available_offers(filters)
        
        return success_response(
            data=result,
            message="Доступные офферы получены"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения доступных офферов: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/create', methods=['POST'])
def create_offer():
    """Создание нового оффера"""
    try:
        # Получаем данные из запроса
        offer_data = request.get_json()
        if not offer_data:
            return error_response("Данные оффера не предоставлены", 400)
        
        # Создаем оффер через сервис
        result = offer_service.create_offer(offer_data)
        
        return success_response(
            data=result,
            message="Оффер успешно создан",
            status_code=201
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка создания оффера: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/smart-create', methods=['POST'])
def create_smart_offer():
    """Умное создание оффера с автоматическим подбором каналов"""
    try:
        # Получаем данные из запроса
        offer_data = request.get_json()
        if not offer_data:
            return error_response("Данные оффера не предоставлены", 400)
        
        # Создаем умный оффер через сервис
        result = offer_service.create_smart_offer(offer_data)
        
        return success_response(
            data=result,
            message="Умный оффер успешно создан",
            status_code=201
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка создания умного оффера: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/<int:offer_id>', methods=['GET'])
def get_offer_details(offer_id):
    """Получение деталей оффера"""
    try:
        result = offer_service.get_offer_details(offer_id)
        
        return success_response(
            data=result,
            message="Детали оффера получены"
        )
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        logger.error(f"Ошибка получения деталей оффера {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/<int:offer_id>/status', methods=['PUT'])
def update_offer_status(offer_id):
    """Обновление статуса оффера"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return error_response("Новый статус не указан", 400)
        
        new_status = data['status']
        reason = data.get('reason', '')
        
        result = offer_service.update_offer_status(offer_id, new_status, reason)
        
        return success_response(
            data=result,
            message=f"Статус оффера изменен на '{new_status}'"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка обновления статуса оффера {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    """Удаление оффера"""
    try:
        result = offer_service.delete_offer(offer_id)
        
        return success_response(
            data=result,
            message="Оффер успешно удален"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/<int:offer_id>/responses', methods=['GET'])
def get_offer_responses(offer_id):
    """Получение откликов на оффер"""
    try:
        result = offer_service.get_offer_responses(offer_id)
        
        return success_response(
            data=result,
            message="Отклики на оффер получены"
        )
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        logger.error(f"Ошибка получения откликов на оффер {offer_id}: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/statistics', methods=['GET'])
def get_offer_statistics():
    """Получение статистики офферов пользователя"""
    try:
        result = offer_service.get_offer_statistics()
        
        return success_response(
            data=result,
            message="Статистика офферов получена"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка получения статистики офферов: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/categories', methods=['GET'])
def get_offer_categories():
    """Получение списка категорий офферов"""
    try:
        result = offer_service.get_offer_categories()
        
        return success_response(
            data=result,
            message="Категории офферов получены"
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения категорий офферов: {e}")
        return error_response("Внутренняя ошибка сервера", 500)


@offer_routes.route('/summary', methods=['GET'])
def get_user_summary():
    """Получение сводной информации пользователя"""
    try:
        result = offer_service.get_user_summary()
        
        return success_response(
            data=result,
            message="Сводная информация получена"
        )
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Ошибка получения сводной информации: {e}")
        return error_response("Внутренняя ошибка сервера", 500)