import os
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.getenv("BOT_TOKEN")

SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

user_keys = {}

app = Flask(__name__)

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
            keyboard = {
                "keyboard": [["⚡ Купить подписку"], ["🔑 Мои ключи"], ["ℹ️ Info"]],
                "resize_keyboard": True
            }
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=keyboard)
        
        elif text == "⚡ Купить подписку":
            keyboard = {"inline_keyboard": [
                [{"text": "📅 Полгода — 200₽", "callback_data": "price_half_year"}]
            ]}
            send_message(chat_id, "⚡️ Выберите тариф:", reply_markup=keyboard)
        
        elif text == "🔑 Мои ключи":
            keys = user_keys.get(user_id, [])
            if not keys:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                send_message(chat_id, "Ваши ключи:\n" + "\n".join(keys))
        
        elif text == "ℹ️ Info":
            info_text = (
                "<b>📋 Информация</b>\n\n"
                f'📄 <a href="{PRIVACY_LINK}">Политика конфиденциальности</a>\n'
                f'📄 <a href="{AGREEMENT_LINK}">Пользовательское соглашение</a>\n\n'
                f'🆘 <a href="{SUPPORT_LINK}">Поддержка</a>'
            )
            send_message(chat_id, info_text, parse_mode="HTML", disable_web_page_preview=True)
    
    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]
        
        if cb_data == "price_half_year":
            days = "180"
            price = 200
            
            keyboard = {"inline_keyboard": [
                [{"text": "🤝 Связаться с реселлером", "url": SUPPORT_LINK}]
            ]}
            update_message(chat_id, message_id, f"💳 Подписка на период {days} дней — {price}₽\n\nНажмите на кнопку ниже, чтобы связаться с продавцом и оплатить:", reply_markup=keyboard)
    
    return jsonify({"ok": True})

@app.route("/")
def health():
    return "Бот работает!", 200

def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    webhook_url = f"https://mybot-frxc.onrender.com/webhook/{TOKEN}"
    r = requests.post(url, json={"url": webhook_url})
    print("Webhook set:", r.json())

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
