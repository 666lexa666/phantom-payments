from flask import Blueprint
from .operations import operations_bp
from .pikmi import pikmi_bp
from .webhook import webhook_bp
from .test import test_bp

# Основной blueprint для всех маршрутов
api_bp = Blueprint("api", __name__)

# 🔹 Регистрируем подроуты
api_bp.register_blueprint(operations_bp, url_prefix="/operations")
api_bp.register_blueprint(pikmi_bp, url_prefix="/order")
api_bp.register_blueprint(webhook_bp, url_prefix="/webhook")
api_bp.register_blueprint(test_bp, url_prefix="/test")
