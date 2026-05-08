import os
import json
import requests
import random
import string
import time
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

# Ссылки (твои)
SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

# База пользователей (в памяти)
users_db = {}

# Настройка подписки
PRICE_RUB = 200
DAYS_VALID = 30

CRYPTO_API_URL = "https://pay.crypt.bot/api/"

app = Flask(__name__)

def gen_uid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def gen_key():
    pattern = []
    for i in range(10):
        pattern.append(random.choice(string.ascii_lowercase))
        pattern.append(random.choice(string.digits))
    return ''.join(pattern)[:20]

def crypto_api(method, params=None):
    url = CRYPTO_API_URL + method
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    resp = requests.post(url, headers=headers, json=params or {})
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"API error: {data}")
    return data["result"]

def get_usdt_rate():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        return r.json()["tether"]["rub"]
    except:
        return 96.0

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, json=data)

def update_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, json=data)

def create_invite_link(chat_id, user_id):
    url = f"https://api.telegram.org/bot{TOKEN}/createChatInviteLink"
    params = {
        "chat_id": chat_id,
        "member_limit": 1,  # только для этого пользователя
        "expire_date": int((datetime.now() + timedelta(days=DAYS_VALID)).timestamp())
    }
    r = requests.post(url, json=params)
    data = r.json()
    if data.get("ok"):
        return data["result"]["invite_link"]
    return None

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False}), 400

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")

        if text == "/start":
            kb = {
                "keyboard": [["⚡ Купить чит"], ["🔑 Мои ключи"], ["ℹ️ Info"]],
                "resize_keyboard": True
            }
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=kb)

        elif text == "⚡ Купить чит":
            # Создаём счёт в CryptoBot
            try:
                rate = get_usdt_rate()
                amount = round(PRICE_RUB / rate, 2)
                inv = crypto_api("createInvoice", {
                    "asset": "USDT",
                    "amount": str(amount),
                    "description": f"Подписка на {DAYS_VALID} дней"
                })
                users_db[user_id] = {
                    "invoice_id": inv["invoice_id"],
                    "step": "wait_payment"
                }
                kb = {"inline_keyboard": [
                    [{"text": "💎 Оплатить в CryptoBot", "url": inv["bot_invoice_url"]}],
                    [{"text": "✅ Я оплатил", "callback_data": "check_payment"}]
                ]}
                send_message(chat_id, f"💳 {amount} USDT (~{PRICE_RUB} ₽) · {DAYS_VALID} дн.\n\nОплатите и нажмите «Я оплатил».", reply_markup=kb)
            except Exception as e:
                send_message(chat_id, f"Ошибка: {e}. Обратитесь к @pwnmeifucan")

        elif text == "🔑 Мои ключи":
            if user_id not in users_db or "key" not in users_db[user_id]:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                data = users_db[user_id]
                expire_str = datetime.fromtimestamp(data["expire"]).strftime("%d.%m.%Y")
                msg = (
                    f"👾 <b>{data['uid']}</b>\n"
                    f"🔑 <b>Ключ:</b> <code>{data['key']}</code>\n"
                    f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
                    f"🔗 <a href='{data['invite_link']}'>Ссылка в группу с покупателями</a>"
                )
                send_message(chat_id, msg, parse_mode="HTML")

        elif text == "ℹ️ Info":
            info = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика</a>\n📄 <a href='{AGREEMENT_LINK}'>Соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, info, parse_mode="HTML", disable_web_page_preview=True)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]

        if cb_data == "check_payment":
            if user_id not in users_db or users_db[user_id].get("step") != "wait_payment":
                update_message(chat_id, message_id, "Нет активного счета. Начните новую покупку.")
                return

            invoice_id = users_db[user_id]["invoice_id"]
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [invoice_id]})
                if inv["items"][0]["status"] == "paid":
                    uid = gen_uid()
                    key = gen_key()
                    expire = int((datetime.now() + timedelta(days=DAYS_VALID)).timestamp())

                    # Создаём ссылку в группу (замени GROUP_ID на ID твоей группы)
                    GROUP_ID = -1001234567890  # 👈 СЮДА ВСТАВЬ ID ТВОЕЙ ГРУППЫ
                    invite_link = create_invite_link(GROUP_ID, user_id)

                    users_db[user_id] = {
                        "uid": uid,
                        "key": key,
                        "expire": expire,
                        "invite_link": invite_link,
                        "step": "done"
                    }

                    expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
                    msg = (
                        f"✅ Оплата подтверждена!\n\n"
                        f"👾 <b>{cb['from']['first_name']}</b>\n"
                        f"🔑 <b>Ключ:</b> <code>{key}</code>\n"
                        f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
                        f"🔗 <a href='{invite_link}'>Ссылка в группу с покупателями</a>"
                    )
                    update_message(chat_id, message_id, msg, parse_mode="HTML")
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён. Попробуйте позже.")
            except Exception as e:
                update_message(chat_id, message_id, f"Ошибка проверки: {e}")

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "OK", 200

def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    webhook_url = f"https://mybot-frxc.onrender.com/webhook/{TOKEN}"
    requests.post(url, json={"url": webhook_url})

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
