from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import os
import uuid
from datetime import datetime

test_bp = Blueprint("test", __name__)

# 🔑 Настройки Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ✅ Проверка, что сервер работает
@test_bp.route("/", methods=["GET"])
def root_check():
    return "Server is running", 200


# 🧪 Тестовый эндпоинт (api/test)
@test_bp.route("/api/test", methods=["POST"])
def test_order():
    try:
        data = request.get_json()
        print("📥 Incoming request body:", data)

        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        steam_id = data.get("steamId")
        amount = data.get("amount")
        api_login = data.get("api_login")
        api_key = data.get("api_key")

        # Проверка обязательных полей
        if not all([steam_id, amount, api_login, api_key]):
            return jsonify({"error": "Missing required fields"}), 400

        # 🔹 Если ping → вернуть pong
        if steam_id == "ping":
            print("Ping received, returning pong")
            return jsonify({"pong": True}), 200

        # 💰 Делим сумму на 100
        amount_rub = float(amount) / 100

        # 🧾 Генерация уникальных идентификаторов
        operation_id = str(uuid.uuid4())
        qr_id = str(uuid.uuid4())
        qr_payload = f"https://fake-qr.com/{qr_id}"
        now = datetime.utcnow().isoformat()

        # 💾 Вставляем тестовую запись
        insert_data = {
            "id": operation_id,
            "amount": amount_rub,
            "api_login": api_login,
            "qr_payload": qr_payload,
            "qr_id": qr_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "commit": None,
        }

        result = supabase.table("purchases_test").insert(insert_data).execute()

        if result.error:
            print("❌ Supabase insert error:", result.error)
            return jsonify({"error": "Database error"}), 500

        response_payload = {
            "result": {
                "operation_id": operation_id,
                "qr_id": qr_id,
                "qr_payload": qr_payload,
            }
        }

        print("📤 Response payload:", response_payload)
        return jsonify(response_payload), 201

    except Exception as e:
        print("💥 Server error:", e)
        return jsonify({"error": "Internal server error"}), 500
