from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import os

webhook_bp = Blueprint("webhook", __name__)

# 🔑 Настройки Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@webhook_bp.route("/", methods=["POST"])
def handle_webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        payment_id = data.get("id")
        status = data.get("status")

        if not payment_id or not status:
            return jsonify({"error": "Missing required fields (id, status)"}), 400

        # 🧩 Приводим статус к нижнему регистру для надёжности
        normalized_status = status.strip().lower()

        if normalized_status == "settlement":
            new_status = "success"
        elif normalized_status in ["failed", "expired"]:
            new_status = "cancelled"
        else:
            return jsonify({"error": f"Unknown status value: {status}"}), 400

        # 💾 Обновляем запись в Supabase
        update_result = (
            supabase.table("purchases")
            .update({"status": new_status})
            .eq("id", payment_id)
            .execute()
        )

        # Проверяем, была ли запись найдена
        if not update_result.data:
            return jsonify({"error": "Purchase not found"}), 404

        print(f"✅ Webhook: updated {payment_id} → {new_status}")

        return jsonify({"success": True, "id": payment_id, "new_status": new_status}), 200

    except Exception as e:
        print("💥 Ошибка обработки webhook:", e)
        return jsonify({"error": str(e)}), 500
