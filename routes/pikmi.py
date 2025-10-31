from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import os
import requests
import uuid
from datetime import datetime

pikmi_bp = Blueprint("pikmi", __name__)

# 🔑 Настройки Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 🔐 API-ключ для запроса к Birs
BIRS_API_KEY = os.environ.get("BIRS_API_KEY")  # Хранится в Render env vars


@pikmi_bp.route("/api/order", methods=["POST"])
def create_order():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        steam_id = data.get("steamId")
        amount = data.get("amount")
        api_login = data.get("api_login")
        api_key = data.get("api_key")

        if not all([steam_id, amount, api_login, api_key]):
            return jsonify({"error": "Missing required fields"}), 400

        # 💰 Переводим сумму в рубли
        amount_rub = amount / 100

        # ⚙️ Формируем данные для внешнего API
        payload = {
            "amount": amount_rub,
            "customer_email": "test@mail.com",
            "callback_url": "https://www.host.com/callback",
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": BIRS_API_KEY,
        }

        # 🌍 Отправляем запрос к Birs API
        response = requests.post(
            "https://admin.birs.app/v2.1/payment-test/create-link-payment",
            json=payload,
            headers=headers,
            timeout=20,
        )

        birs_data = response.json()

        # 🚨 Обрабатываем неуспешные ответы
        if not birs_data.get("success", False):
            print("❌ Ошибка при создании платежа через Birs API:")
            print(birs_data)
            return jsonify({"error": birs_data.get("message", "Unknown error")}), 400

        # ✅ Успешный ответ
        birs_payment = birs_data.get("data", {})
        payment_id = birs_payment.get("id")
        payment_url = birs_payment.get("payment_url")

        if not payment_id or not payment_url:
            return jsonify({"error": "Invalid Birs response"}), 500

        # 🧾 Подготавливаем данные для вставки в таблицу purchases
        qr_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        insert_data = {
            "id": payment_id,
            "user_id": None,
            "amount": amount_rub,
            "status": "pending",
            "steam_login": steam_id,
            "api_login": api_login,
            "payer_phone": None,
            "qr_id": qr_id,
            "qr_payload": payment_url,
            "sndpam": None,
            "refund_attempts": 0,
            "commit": None,
        }

        # 💾 Добавляем запись в Supabase
        result = supabase.table("purchases").insert(insert_data).execute()

        if result.error:
            print("❌ Ошибка при вставке в purchases:", result.error)
            return jsonify({"error": "Database insert failed"}), 500

        # 📦 Возвращаем успешный ответ
        return (
            jsonify(
                {
                    "result": {
                        "operation_id": payment_id,
                        "qr_id": qr_id,
                        "qr_link": payment_url,
                    }
                }
            ),
            200,
        )

    except requests.exceptions.RequestException as e:
        print("🌐 Ошибка соединения с Birs API:", e)
        return jsonify({"error": "Failed to connect to Birs API"}), 502

    except Exception as e:
        print("💥 Неожиданная ошибка:", e)
        return jsonify({"error": str(e)}), 500
