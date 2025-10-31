from flask import Blueprint
from routes.api.operations.qr_code import qr_code_bp
from routes.api.operations.qr_status import qr_status_bp

operations_bp = Blueprint("operations", __name__)

# Статические префиксы для вложенных blueprints
operations_bp.register_blueprint(qr_code_bp, url_prefix="/qr-code")
operations_bp.register_blueprint(qr_status_bp, url_prefix="/qr-status")
