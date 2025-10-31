from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import httpx
import random
import datetime
import os

qr_code_bp = Blueprint("qr_code", __name__)

# 🔑 Инициализация Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 🔢 Генерация 8-значного ID
def generate_numeric_id():
    return random.randint(10000000, 99999999)

# 📤 Отправка запроса на Steam backend
async def send_to_steam_backend(login, amount, api_login, api_key, backend_url):
    request_data = {
        "steamId": login,
        "amount": amount,
        "api_login": api_login,
        "api_key": api_key,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            backend_url,
            headers={"Content-Type": "application/json"},
            json=request_data,
        )

        if res.status_code >= 400:
            raise Exception(f"Backend error: {res.status_code} {res.text}")

        return res.json()

# 🔑 Получение свободного steam_login
async def get_available_login():
    logins_resp = supabase.table("available_logins").select("login").eq("used", False).execute()
    logins = logins_resp.data

    if not logins:
        raise Exception("No available logins left")

    while logins:
        chosen = random.choice(logins)["login"]

        exists = supabase.table("clients").select("steam_login").eq("steam_login", chosen).maybe_single().execute().data
        if not exists:
            mark = supabase.table("available_logins").update({"used": True}).eq("login", chosen).execute()
            if mark.error:
                raise Exception(mark.error.message)
            return chosen

        logins = [l for l in logins if l["login"] != chosen]

    raise Exception("No available logins left after checking clients")

# 🧠 Основная логика
@qr_code_bp.route("/qr-code", methods=["POST"])
async def qr_code():
    try:
        api_key = request.headers.get("X-Api-Key")
        api_login = request.headers.get("X-Api-Login")

        if not api_key and not api_login:
            return jsonify({"error": "Missing API credentials"}), 400

        # Если есть только ключ — ищем логин
        if not api_login and api_key:
            client_by_key = supabase.table("api_clients").select("api_login, second_server_url").eq("api_key", api_key).maybe_single().execute().data
            if not client_by_key:
                return jsonify({"error": "Invalid API key"}), 401
            api_login = client_by_key["api_login"]

        # Проверяем клиента
        client = supabase.table("api_clients").select("id, api_login, api_key, second_server_url").eq("api_login", api_login).eq("api_key", api_key).maybe_single().execute().data
        if not client:
            return jsonify({"error": "Invalid API credentials"}), 401

        SECOND_SERVER_URL = client["second_server_url"]

        body = request.get_json()
        if not body:
            return jsonify({"error": "Missing JSON body"}), 400

        sum_value = body.get("sum")
        client_id = body.get("client_id")

        if not isinstance(sum_value, (int, float)) or sum_value <= 0:
            return jsonify({"error": "Invalid sum: must be positive number"}), 400

        if not client_id:
            return jsonify({"error": "Missing client_id in request body"}), 400

        amount = sum_value
        now = datetime.datetime.utcnow().isoformat()

        # Проверяем клиента
        existing_client = supabase.table("clients").select("*").eq("client_id", client_id).maybe_single().execute().data

        # =============== 1️⃣ Клиент существует ===============
        if existing_client:
            new_total = (existing_client.get("total_amount", 0) or 0) + amount / 100
            new_period = (existing_client.get("period_amount", 0) or 0) + amount / 100

            if new_period > 10000 or new_total > 100000:
                exceeded_type = "день" if new_period > 10000 else "месяц"
                remaining = (
                    10000 - existing_client.get("period_amount", 0)
                    if new_period > 10000
                    else 100000 - existing_client.get("total_amount", 0)
                )
                return jsonify({
                    "status": "cancelled",
                    "info": f"Превышен лимит суммы операций за {exceeded_type}. Остаточный лимит {max(0, remaining)} рублей."
                }), 200

            # обновляем клиента
            supabase.table("clients").update({
                "total_amount": new_total,
                "period_amount": new_period,
                "updated_at": now
            }).eq("client_id", client_id).execute()

            steam_login = existing_client["steam_login"]

            backend_data = await send_to_steam_backend(steam_login, amount, api_login, api_key, SECOND_SERVER_URL)
            result = backend_data["result"]

            return jsonify({
                "results": {
                    "operation_id": result["operation_id"],
                    "qr_id": result["qr_id"],
                    "qr_link": result["qr_payload"]
                }
            }), 200

        # =============== 2️⃣ Клиента нет — создаём ===============
        chosen_login = await get_available_login()
        new_id = generate_numeric_id()

        supabase.table("clients").insert({
            "id": new_id,
            "client_id": client_id,
            "api_login": api_login,
            "created_at": now,
            "updated_at": now,
            "total_amount": amount / 100,
            "period_amount": amount / 100,
            "steam_login": chosen_login,
        }).execute()

        backend_data = await send_to_steam_backend(chosen_login, amount, api_login, api_key, SECOND_SERVER_URL)
        result = backend_data["result"]

        return jsonify({
            "results": {
                "operation_id": result["operation_id"],
                "qr_id": result["qr_id"],
                "qr_link": result["qr_payload"]
            }
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
