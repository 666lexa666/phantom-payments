from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import os

qr_status_bp = Blueprint("qr_status", __name__)

# 🔑 Инициализация Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@qr_status_bp.route("/", methods=["GET"])
def get_qr_status(opId):
    try:
        # Получаем API-данные из заголовков
        api_key = request.headers.get("X-Api-Key")
        api_login = request.headers.get("X-Api-Login")

        if not api_key and not api_login:
            return jsonify({"error": "Missing API credentials"}), 400

        # Если есть только ключ — ищем логин
        if not api_login and api_key:
            client_by_key = (
                supabase.table("api_clients")
                .select("api_login, test")
                .eq("api_key", api_key)
                .maybe_single()
                .execute()
                .data
            )

            if not client_by_key:
                return jsonify({"error": "Invalid API key"}), 401

            api_login = client_by_key["api_login"]

        # Проверяем наличие opId
        if not opId:
            return jsonify({"error": "Missing opId"}), 400

        # Проверяем API-клиента
        client_resp = (
            supabase.table("api_clients")
            .select("api_login, api_key, test")
            .eq("api_login", api_login)
            .eq("api_key", api_key)
            .maybe_single()
            .execute()
        )

        client = client_resp.data
        if not client:
            return jsonify({"error": "Forbidden: invalid API credentials"}), 403

        # 🔹 Определяем таблицу по режиму
        table_name = "purchases_test" if client.get("test") else "purchases"

        # 🔍 Ищем запись по opId и api_login
        purchase_resp = (
            supabase.table(table_name)
            .select("status, commit")
            .eq("api_login", api_login)
            .eq("id", opId)
            .maybe_single()
            .execute()
        )

        purchase = purchase_resp.data
        if not purchase:
            return jsonify({"error": "Purchase not found"}), 404

        # ✅ Определяем operation_status_code
        status = purchase.get("status", "").lower() if purchase.get("status") else ""
        commit_info = purchase.get("commit")

        operation_status_code = 1  # По умолчанию "в процессе"
        info = None

        if status == "success":
            operation_status_code = 5
        elif status == "refund":
            operation_status_code = 3
            info = commit_info

        return jsonify({"results": {"operation_status_code": operation_status_code, "info": info}}), 200

    except Exception as e:
        print("❌ Ошибка проверки статуса:", e)
        return jsonify({"error": str(e)}), 500
