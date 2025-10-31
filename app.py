from flask import Flask, jsonify
from routes import api_bp
import os

def create_app():
    app = Flask(__name__)

    # 🔹 Регистрируем все API-маршруты
    app.register_blueprint(api_bp, url_prefix="/api")

    # 🔹 Базовый маршрут для проверки работы сервера
    @app.route("/")
    def index():
        return jsonify({"message": "🚀 API server is running"}), 200

    # 🔹 Обработка 404
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    # 🔹 Обработка 500
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app

# 🔧 Создаём глобальный объект для Gunicorn
app = create_app()

if __name__ == "__main__":
    # 🔧 Порт берём из переменных окружения (удобно для Render)
    port = int(os.environ.get("PORT", 5000))

    # 🔥 Запуск сервера
    app.run(host="0.0.0.0", port=port, debug=True)
