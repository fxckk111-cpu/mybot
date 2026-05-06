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
            # Одна кнопка — полгода за 200₽
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
            # Полгода за 200₽
            days = "180"
            price = 200
            user_selected_plan = {"days": days, "price": price}
            
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
    app.run(host="0.0.0.0", port=port, debug=False)            days = PRICE_NAMES.get(plan_key, "0")
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
