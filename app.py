import os
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")

# Базовый URL для API (тестовая сеть)
CRYPTO_API_URL = "https://testnet-pay.crypt.bot/api/"

SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

user_keys = {}
user_selected_plan = {}
user_invoices = {}

PRICES = {"7_days": 250, "30_days": 500, "60_days": 1000}
PRICE_NAMES = {"7_days": "7", "30_days": "30", "60_days": "60"}

app = Flask(__name__)

def crypto_api(method, params=None):
    """Вызов API CryptoBot"""
    url = CRYPTO_API_URL + method
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    response = requests.post(url, headers=headers, json=params or {})
    data = response.json()
    if not data.get("ok"):
        raise Exception(f"API error: {data}")
    return data["result"]

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
            info = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, info, parse_mode="HTML")
    
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
            user_selected_plan[user_id] = {"days": days, "price": price}
            
            keyboard = {"inline_keyboard": [
                [{"text": "🤝 Через реселлера (RUB)", "url": SUPPORT_LINK}],
                [{"text": "💎 CryptoBot (авто)", "callback_data": "pay_crypto"}]
            ]}
            update_message(chat_id, message_id, f"💳 Подписка на период {days} дней — {price}₽\n\nВыберите способ оплаты:", reply_markup=keyboard)
        
        elif cb_data == "pay_crypto":
            days = user_selected_plan[user_id]["days"]
            price = user_selected_plan[user_id]["price"]
            
            # Получаем курс USDT
            rate = get_usdt_rate()
            amount = round(price / rate, 3)
            
            try:
                # Создаём инвойс через API CryptoBot
                result = crypto_api("createInvoice", {
                    "asset": "USDT",
                    "amount": str(amount),
                    "description": f"Подписка на {days} дней"
                })
                
                invoice_id = result["invoice_id"]
                pay_url = result["bot_invoice_url"]
                
                user_invoices[user_id] = {
                    "invoice_id": invoice_id,
                    "days": days,
                    "price": price,
                    "amount": amount
                }
                
                keyboard = {"inline_keyboard": [
                    [{"text": "💎 Оплатить в CryptoBot", "url": pay_url}],
                    [{"text": "✅ Я оплатил", "callback_data": "check_payment"}]
                ]}
                update_message(chat_id, message_id, f"💎 {amount} USDT (~{price} ₽) · {days} дн.\n\nОплатите в CryptoBot и вернитесь.", reply_markup=keyboard)
            
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка создания счета: {str(e)}\nОбратитесь к @pwnmeifucan")
        
        elif cb_data == "check_payment":
            if user_id not in user_invoices:
                update_message(chat_id, message_id, "❌ Нет активного счета. Начните новую покупку.")
                return
            
            invoice_id = user_invoices[user_id]["invoice_id"]
            days = user_invoices[user_id]["days"]
            price = user_invoices[user_id]["price"]
            
            try:
                # Проверяем статус инвойса
                result = crypto_api("getInvoices", {"invoice_ids": [invoice_id]})
                invoices = result.get("items", [])
                
                if invoices and invoices[0].get("status") == "paid":
                    # Генерируем ключ
                    import hashlib
                    key_seed = f"{user_id}_{days}_{invoice_id}"
                    new_key = hashlib.sha256(key_seed.encode()).hexdigest()[:16].upper()
                    
                    if user_id not in user_keys:
                        user_keys[user_id] = []
                    user_keys[user_id].append(f"{days} дней — {price}₽: {new_key}")
                    
                    # Очищаем данные
                    del user_invoices[user_id]
                    del user_selected_plan[user_id]
                    
                    update_message(chat_id, message_id, f"✅ Оплата подтверждена!\n\n🎉 Ваш ключ: <code>{new_key}</code>\n\nСохраните его.", parse_mode="HTML")
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён.\n\nЕсли вы оплатили, подождите 1-2 минуты и нажмите «Я оплатил» снова.")
            
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка проверки: {str(e)}\nОбратитесь к @pwnmeifucan")
    
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
