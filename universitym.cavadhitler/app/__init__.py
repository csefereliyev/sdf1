import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from . import db
from .config import Config
from .errors import AppError

logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.init_app(app)

    from .routes import api, pages
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(pages)

    _register_error_handlers(app)
    return app


def _wants_json():
    return request.path.startswith("/api")


def _register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({"error": error.message, "details": error.errors}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if _wants_json():
            return jsonify({"error": error.description, "details": {}}), error.code
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        logger.exception("Gözlənilməyən xəta: %s", error)
        message = "Gözlənilməyən xəta baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin."
        if _wants_json():
            return jsonify({"error": message, "details": {}}), 500
        return render_template("error.html", code=500, message=message), 500
