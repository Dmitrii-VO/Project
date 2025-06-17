from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({
            "error": e.name,
            "message": e.description,
            "code": e.code
        }), e.code

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        app.logger.exception("Unhandled Exception")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "code": 500
        }), 500
