"""HTTP API factory."""

import logging
from hmac import compare_digest

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from light_alarm.api.routes import create_blueprint

logger = logging.getLogger(__name__)


def create_app(runtime):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.register_blueprint(create_blueprint(runtime))

    @app.before_request
    def authenticate():
        if runtime.settings.api_key:
            supplied = request.headers.get("X-API-Key", "")
            if not compare_digest(supplied.encode(), runtime.settings.api_key.encode()):
                return jsonify(status="error", message="Unauthorized."), 401

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify(status="error", message=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(status="error", message=error.description), error.code

    @app.errorhandler(Exception)
    def internal_error(error):
        logger.exception("API request failed | path=%s", request.path)
        return jsonify(status="error", message="Internal server error; see system logs."), 500

    return app
