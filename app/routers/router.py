from flask import Blueprint, render_template, request, jsonify

main_bp = Blueprint('main', __name__)

# === ОСНОВНЫЕ МАРШРУТЫ ===
@main_bp.before_request
def security_middleware():
    """Middleware безопасности - выполняется ПЕРЕД каждым запросом"""

    # Получаем информацию о запросе
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    # 1. Блокировка заблокированных IP
    if client_ip in blocked_ips:
        log_security_event('BLOCKED_IP_ACCESS', {
            'ip': client_ip,
            'path': request.path,
            'method': request.method
        })
        return jsonify({'error': 'Access denied'}), 403

    # 2. Rate limiting
    if not rate_limit_check(f"global_{client_ip}"):
        # Добавляем в подозрительные при превышении лимита
        suspicious_ips.add(client_ip)

        log_security_event('RATE_LIMIT_EXCEEDED', {
            'ip': client_ip,
            'path': request.path,
            'user_agent': user_agent
        })

        return jsonify({'error': 'Too many requests'}), 429

    # 3. Детекция подозрительных запросов
    request_data = {
        'user_agent': user_agent,
        'ip': client_ip,
        'path': request.path,
        'method': request.method
    }

    if is_suspicious_request(request_data):
        suspicious_ips.add(client_ip)
        log_security_event('SUSPICIOUS_REQUEST', request_data)

    # 4. Валидация размера запроса
    if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
        log_security_event('LARGE_REQUEST', {
            'ip': client_ip,
            'size': request.content_length,
            'path': request.path
        })
        return jsonify({'error': 'Request too large'}), 413

    # 5. Проверка Content-Type для POST запросов
    if request.method == 'POST' and request.path.startswith('/api/'):
        content_type = request.headers.get('Content-Type', '')
        if not content_type.startswith('application/json'):
            return jsonify({'error': 'Invalid Content-Type'}), 400
    # 6 Логирование доступа к API каналов
    if request.path.startswith('/api/channels'):
        telegram_user_id = get_current_user_id()
        logger.info(f"API Channels access: {request.method} {request.path} by user {telegram_user_id}")

        # Логируем заголовки для отладки
        headers_info = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent')
        }
        logger.debug(f"Request headers: {headers_info}")
        # Логируем заголовки для отладки
        headers_info = {
            'X-Telegram-User-Id': request.headers.get('X-Telegram-User-Id'),
            'Content-Type': request.headers.get('Content-Type'),
            'User-Agent': request.headers.get('User-Agent')
        }
        logger.debug(f"Request headers: {headers_info}")

def telegram_auth_middleware():
    """Middleware для автоматической аутентификации Telegram пользователей"""

    # Применяем только к API эндпоинтам каналов
    if not request.path.startswith('/api/channels'):
        return

    # Пропускаем GET запросы к общим эндпоинтам
    if request.method == 'GET' and request.path in ['/api/channels', '/api/channels/']:
        return

    try:
        telegram_user_id = get_current_user_id()

        if telegram_user_id:
            # Убеждаемся что пользователь существует в БД
            user_db_id = ensure_user_exists(telegram_user_id)

            if not user_db_id:
                logger.warning(f"Failed to ensure user exists for Telegram ID: {telegram_user_id}")
            else:
                logger.debug(f"Telegram user {telegram_user_id} authenticated for {request.path}")

    except Exception as e:
        logger.error(f"Telegram auth middleware error: {e}")
@main_bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@main_bp.route('/channels-enhanced')
def channels_page():
    """Страница управления каналами"""
    return render_template('channels.html')

@main_bp.route('/analytics')
def analytics_page():
    """Страница аналитики"""
    return render_template('analytics.html')

@main_bp.route('/payments')
def payments_page():
    """Страница платежей"""
    return render_template('payments.html')

@main_bp.route('/offers')
def create_offer_page():
    """Страница создания оффера"""
    return render_template('offers.html')