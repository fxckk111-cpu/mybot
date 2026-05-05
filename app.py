import os
import json
import requests
from flask import Flask, request, jsonify
from threading import Thread

TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

app = Flask(__name__)

# In-memory база
user_keys = {}
user_selected_plan = {}
PRICES = {"7_days": 250, "30_days": 500, "60_days": 1000}
PRICE_NAMES = {"7_days": "7", "30_days": "30", "60_days": "60"}

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, json=data).json()

def update_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, json=data).json()

def get_usdt_rate():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        return r.json()["tether"]["rub"]
    except:
        return 96.0

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"ok": False}), 400
    
    # Обработка сообщений
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        
        if text == "/start":
            keyboard = {
                "keyboard": [["⚡ Купить подписку"], ["🔑 Мои ключи"], ["ℹ️ Info"]],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=keyboard)
        
        elif text == "⚡ Купить подписку":
            keyboard = {"inline_keyboard": [
                [{"text": "📅 7 дней — 250₽", "callback_data": "price_7_days"}],
                [{"text": "📅 30 дней — 500₽", "callback_data": "price_30_days"}],
                [{"text": "📅 60 дней — 1000₽", "callback_data": "price_60_days"}]
            ]}
            send_message(chat_id, "⚡️ Выберите тариф:", reply_markup=keyboard)
        
        elif text == "🔑 Мои ключи":
            keys = user_keys.get(user_id, [])
            if not keys:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                send_message(chat_id, "Ваши ключи:\n" + "\n".join(keys))
        
        elif text == "ℹ️ Info":
            text = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, text, parse_mode="HTML")
    
    # Обработка нажатий на кнопки
    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]
        
        if cb_data.startswith("price_"):
            parts = cb_data.split("_")
            plan_key = parts[1] + "_" + parts[2]
            price = PRICES.get(plan_key, 0)
            days = PRICE_NAMES.get(plan_key, "0")
            user_selected_plan[user_id] = (days, price)
            
            keyboard = {"inline_keyboard": [
                [{"text": "🤝 Через реселлера (RUB)", "url": SUPPORT_LINK}],
                [{"text": "💎 CryptoBot (авто)", "callback_data": "pay_crypto"}]
            ]}
            update_message(chat_id, message_id, f"💳 Подписка на период {days} дней — {price}₽\n\nВыберите способ оплаты:", reply_markup=keyboard)
        
        elif cb_data == "pay_crypto":
            days, price = user_selected_plan.get(user_id, ("0", 0))
            rate = get_usdt_rate()
            usdt_amount = round(price / rate, 2)
            keyboard = {"inline_keyboard": [
                [{"text": "💎 Оплатить в CryptoBot", "url": "https://t.me/CryptoBot"}],
                [{"text": "✅ Я оплатил", "callback_data": "payment_done"}]
            ]}
            update_message(chat_id, message_id, f"💎 {usdt_amount} USDT (~{price} ₽) · {days} дн.\n\nОплатите в CryptoBot и вернитесь.", reply_markup=keyboard)
        
        elif cb_data == "payment_done":
            update_message(chat_id, message_id, "Ожидаем подтверждение...")
    
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
