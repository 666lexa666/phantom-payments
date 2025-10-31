from flask import Blueprint
from .qr_code import qr_code_bp
from .qr_status import qr_status_bp

operations_bp = Blueprint("operations", __name__)

operations_bp.register_blueprint(qr_code_bp, url_prefix="/qr-code")
operations_bp.register_blueprint(qr_status_bp, url_prefix="/qr-status")
