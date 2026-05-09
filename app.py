import os
import json
import requests
import random
import string
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

BOT_TOKEN = "8687695414:AAFX_eG3x05gQXahtMogvAh2JYfQuiwyWCM"
CRYPTOBOT_TOKEN = "579104:AARyyU3ZKIVsb3hgHxYWnMYyVnQhzNASc71"
GROUP_ID = -1003992937868

PRICE_PLANS = [
    {"days": 7, "price": 50},
    {"days": 30, "price": 100},
    {"days": 60, "price": 200},
    {"days": 90, "price": 300}
]

ADMIN_IDS = ["8095717532", "522044023"]
RESELLER_LINK = "https://t.me/realsapphire"
SUPPORT_LINK = "https://t.me/realsapphire"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

CRYPTO_API_URL = "https://pay.crypt.bot/api/"
app = Flask(__name__)

users_db = {}
admin_actions = {}
next_uid = 2

def gen_key():
    parts = []
    for i in range(10):
        parts.append(random.choice(string.ascii_lowercase))
        parts.append(random.choice(string.digits))
    return ''.join(parts)[:20]

def get_user_info(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            return data["result"].get("username"), data["result"].get("first_name")
    except:
        pass
    return None, f"user_{user_id}"

def get_chat_member_status(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        r = requests.post(url, json={"chat_id": user_id, "user_id": user_id})
        data = r.json()
        if data.get("ok"):
            return data["result"].get("status")
    except:
        pass
    return None

def is_premium_user(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            return data["result"].get("is_premium", False)
    except:
        pass
    return False

def kick_from_group(chat_id, user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember"
    try:
        requests.post(url, json={"chat_id": chat_id, "user_id": user_id})
    except:
        pass

def send_message(chat_id, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    if disable_web_page_preview is not None:
        data["disable_web_page_preview"] = disable_web_page_preview
    requests.post(url, json=data)

def update_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, json=data)

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    requests.post(url, json={"chat_id": chat_id, "message_id": message_id})

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

def create_invite_link(chat_id, user_id, days=30):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    params = {
        "chat_id": chat_id,
        "member_limit": 1,
        "expire_date": int((datetime.now() + timedelta(days=days)).timestamp())
    }
    r = requests.post(url, json=params)
    data = r.json()
    if data.get("ok"):
        return data["result"]["invite_link"]
    return None

def get_main_keyboard(is_admin=False):
    if is_admin:
        keyboard = [["🔑 Мои ключи"], ["👑 Админ панель"]]
    else:
        keyboard = [["⚡ Купить чит"], ["🔑 Мои ключи"], ["ℹ️ Информация"]]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_user_subscription_info(user_id):
    user_id_str = str(user_id)
    if user_id_str in users_db:
        return users_db[user_id_str]
    return None

def init_admin_subscriptions():
    for admin_id in ADMIN_IDS:
        if admin_id not in users_db:
            users_db[admin_id] = {
                "uid": admin_id[-4:],
                "key": gen_key(),
                "expire": 9999999999,
                "subscription_name": "вечная",
                "days": 9999,
                "step": "done"
            }

init_admin_subscriptions()

def send_tariffs(chat_id, message_id=None):
    keyboard = {"inline_keyboard": []}
    for plan in PRICE_PLANS:
        keyboard["inline_keyboard"].append([{"text": f"📅 {plan['days']} дней — {plan['price']}₽", "callback_data": f"plan_{plan['days']}_{plan['price']}"}])
    keyboard["inline_keyboard"].append([{"text": "🔙 Назад в меню", "callback_data": "back_to_menu"}])
    if message_id:
        update_message(chat_id, message_id, "⚡️ Выберите тариф:", reply_markup=keyboard)
    else:
        send_message(chat_id, "⚡️ Выберите тариф:", reply_markup=keyboard)

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    global next_uid
    data = request.get_json()
    if not data:
        return jsonify({"ok": False}), 400

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        is_admin = user_id in ADMIN_IDS

        if msg.get("text") == "/start":
            if user_id not in users_db and not is_admin:
                users_db[user_id] = {"uid": next_uid, "step": "new"}
                next_uid += 1
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))

        elif msg.get("text") == "👑 Админ панель" and is_admin:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "😒 Забрать подписку", "callback_data": "admin_revoke"}],
                    [{"text": "🤝 Передать подписку", "callback_data": "admin_transfer"}],
                    [{"text": "❄ Заморозить подписку", "callback_data": "admin_freeze"}],
                    [{"text": "🎁 Выдать подписку", "callback_data": "admin_grant"}],
                    [{"text": "🔙 Назад в меню", "callback_data": "back_to_menu"}]
                ]
            }
            send_message(chat_id, f"👋 Привет, <b>{msg['from']['first_name']}</b>!\n😂 Что хочешь сделать?", parse_mode="HTML", reply_markup=keyboard)

        elif msg.get("text") == "⚡ Купить чит" and not is_admin:
            send_tariffs(chat_id)

        elif msg.get("text") == "🔑 Мои ключи":
            sub = get_user_subscription_info(user_id)
            if not sub:
                send_message(chat_id, "😔 Ключей нет.")
                return
            expire_str = "никогда" if sub["expire"] >= 999999999 else datetime.fromtimestamp(sub["expire"]).strftime("%d.%m.%Y")
            text = f"🆔 UID: {sub['uid']}\n🔑 Ключ: {sub['key']}\n⏳ Ключ истекает: {expire_str}"
            if "invite_link" in sub and sub["invite_link"]:
                text += f"\n\n🔗 Ссылка в группу с покупателями: {sub['invite_link']}"
            send_message(chat_id, text)

        elif msg.get("text") == "ℹ️ Информация" and not is_admin:
            info = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, info, parse_mode="HTML", disable_web_page_preview=True)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        is_admin = user_id in ADMIN_IDS

        if cb["data"] == "back_to_menu":
            delete_message(chat_id, message_id)
            send_message(chat_id, f"👾 Привет, <b>{cb['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

        if cb["data"] == "back_to_plans":
            send_tariffs(chat_id, message_id)
            return jsonify({"ok": True})

        if cb["data"].startswith("plan_"):
            _, days, price = cb["data"].split("_")
            days, price = int(days), int(price)
            kb = {"inline_keyboard": [[{"text": "🤝 Через реселлера", "url": RESELLER_LINK}], [{"text": "💎 CryptoBot", "callback_data": f"crypto_{days}_{price}"}], [{"text": "🔙 Назад", "callback_data": "back_to_plans"}]]}
            update_message(chat_id, message_id, f"💳 Подписка на {days} дней — {price}₽\n\nВыберите способ оплаты:", reply_markup=kb)
            return jsonify({"ok": True})

        if cb["data"].startswith("crypto_"):
            _, days, price = cb["data"].split("_")
            days, price = int(days), int(price)
            rate = get_usdt_rate()
            amount = round(price / rate, 2)
            try:
                inv = crypto_api("createInvoice", {"asset": "USDT", "amount": str(amount), "description": f"Подписка на {days} дней"})
                users_db[user_id] = {"invoice_id": inv["invoice_id"], "days": days, "price": price, "step": "wait_payment"}
                kb = {"inline_keyboard": [[{"text": "💎 Оплатить", "url": inv["bot_invoice_url"]}], [{"text": "✅ Я оплатил", "callback_data": f"check_{days}_{price}"}], [{"text": "🔙 Назад", "callback_data": "back_to_plans"}]]}
                update_message(chat_id, message_id, f"💳 {amount} USDT (~{price} ₽) · {days} дн.\n\nОплатите и нажмите «Я оплатил».", reply_markup=kb)
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка: {e}")
            return jsonify({"ok": True})

        if cb["data"].startswith("check_"):
            _, days, price = cb["data"].split("_")
            days, price = int(days), int(price)
            if user_id not in users_db or users_db[user_id].get("step") != "wait_payment":
                update_message(chat_id, message_id, "❌ Нет активного счета. Начните новую покупку.")
                return
            inv_id = users_db[user_id]["invoice_id"]
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [inv_id]})
                if inv["items"][0]["status"] == "paid":
                    uid = users_db[user_id].get("uid") if "uid" in users_db[user_id] else next_uid
                    if uid == next_uid:
                        next_uid += 1
                    key = gen_key()
                    expire = int((datetime.now() + timedelta(days=days)).timestamp())
                    link = create_invite_link(GROUP_ID, user_id, days)
                    users_db[user_id] = {"uid": uid, "key": key, "expire": expire, "subscription_name": f"{days} дней", "days": days, "invite_link": link, "step": "done"}
                    expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
                    msg = f"✅ Оплата подтверждена!\n\n🆔 UID: {uid}\n🔑 Ключ: {key}\n⏳ Ключ истекает: {expire_str}\n\n🔗 Ссылка в группу с покупателями: {link}"
                    update_message(chat_id, message_id, msg)
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён.", reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "back_to_plans"}]]})
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка: {e}")
            return jsonify({"ok": True})

        if is_admin and cb["data"].startswith("admin_"):
            action = cb["data"].replace("admin_", "")
            admin_actions[user_id] = {"action": action, "step": "wait_target"}
            kb = {"inline_keyboard": [[{"text": "👤 User", "callback_data": "select_user_normal"}], [{"text": "⭐ Premium", "callback_data": "select_user_premium"}], [{"text": "🔙 Назад", "callback_data": "back_to_menu"}]]}
            update_message(chat_id, message_id, "Выберите пользователя:", reply_markup=kb)
            return jsonify({"ok": True})

        if cb["data"] == "select_user_normal" and is_admin:
            admin_actions[user_id]["mode"] = "normal"
            send_message(chat_id, "👉 Отправьте контакт пользователя (через «Поделиться контактом»), либо отправьте его @username.")
            return jsonify({"ok": True})

        if cb["data"] == "select_user_premium" and is_admin:
            admin_actions[user_id]["mode"] = "premium"
            send_message(chat_id, "👉 Отправьте контакт пользователя с премиум‑подпиской.")
            return jsonify({"ok": True})

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_target":
            target_input = text.strip()
            target_id = None
            if target_input.startswith("@"):
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
                try:
                    r = requests.get(url, params={"chat_id": target_input})
                    data = r.json()
                    if data.get("ok"):
                        target_id = data["result"]["id"]
                except:
                    pass
            if target_id is None and target_input.isdigit():
                target_id = int(target_input)
            if target_id is None:
                send_message(chat_id, "❌ Не удалось найти пользователя. Попробуйте ещё раз.")
                return jsonify({"ok": True})

            action_data = admin_actions[user_id]
            action = action_data["action"]
            admin_actions[user_id]["target_id"] = target_id
            admin_actions[user_id]["target_username"], _ = get_user_info(target_id)
            admin_actions[user_id]["step"] = "wait_confirm"
            _, admin_name = get_user_info(user_id)
            target_display = f"@{admin_actions[user_id]['target_username']}" if admin_actions[user_id]['target_username'] else f"id: {target_id}"
            emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
            emoji = emojis.get(action, "⚠️")
            texts = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
            text = texts.get(action, "действие")
            kb = {"inline_keyboard": [[{"text": "✅ Да", "callback_data": f"confirm_{action}"}], [{"text": "❌ Нет", "callback_data": "cancel_action"}]]}
            send_message(chat_id, f"{emoji} <b>{admin_name}</b>, ты точно хочешь {text} {target_display} подписку?", parse_mode="HTML", reply_markup=kb)
            return jsonify({"ok": True})

    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user_id = str(cb["from"]["id"])
        is_admin = user_id in ADMIN_IDS
        if is_admin and cb["data"].startswith("confirm_"):
            action = cb["data"].replace("confirm_", "")
            if user_id not in admin_actions:
                return jsonify({"ok": True})
            adata = admin_actions[user_id]
            target_id = adata.get("target_id")
            target_username, _ = get_user_info(target_id)
            _, admin_name = get_user_info(user_id)
            days = adata.get("days", 30)

            if action == "revoke":
                if str(target_id) in users_db:
                    sub = users_db[str(target_id)]
                    send_message(target_id, f"😒 {target_username}, у тебя {admin_name} забрал твою подписку «{sub.get('subscription_name', 'подписка')}», и твой ключ: {sub['key']} больше не доступен")
                    del users_db[str(target_id)]
                    kick_from_group(GROUP_ID, target_id)
                    send_message(chat_id, f"✅ Подписка у {target_username} отобрана")
                else:
                    send_message(chat_id, f"❌ У {target_username} нет активной подписки")
            elif action == "freeze":
                if str(target_id) in users_db:
                    sub = users_db[str(target_id)]
                    sub["frozen"] = True
                    sub["old_expire"] = sub["expire"]
                    send_message(target_id, f"❄ {target_username}, твоя подписка на {sub.get('subscription_name', 'подписка')} была заморожена админом {admin_name}.")
                    send_message(chat_id, f"✅ Подписка {target_username} заморожена")
                else:
                    send_message(chat_id, f"❌ У {target_username} нет подписки")
            elif action == "grant":
                kb = {"inline_keyboard": [[{"text": "1 час", "callback_data": "period_1hour"}], [{"text": "1 день", "callback_data": "period_1day"}], [{"text": "7 дней", "callback_data": "period_7days"}], [{"text": "1 месяц", "callback_data": "period_1month"}], [{"text": "6 месяцев", "callback_data": "period_6months"}], [{"text": "12 месяцев", "callback_data": "period_12months"}], [{"text": "Навсегда", "callback_data": "period_forever"}], [{"text": "🔙 Назад", "callback_data": "cancel_action"}]]}
                update_message(chat_id, cb["message"]["message_id"], f"🎁 Выберите период подписки для {target_username or target_id}:", reply_markup=kb)
                admin_actions[user_id]["step"] = "wait_period"
                return jsonify({"ok": True})
            elif action == "transfer":
                if str(target_id) in users_db:
                    admin_actions[user_id]["from_id"] = target_id
                    admin_actions[user_id]["from_username"] = target_username
                    admin_actions[user_id]["step"] = "wait_transfer"
                    send_message(chat_id, "🤝 Теперь отправьте контакт пользователя, КОМУ передать подписку.")
                    return jsonify({"ok": True})
                else:
                    send_message(chat_id, "❌ У этого пользователя нет активной подписки")
            delete_message(chat_id, cb["message"]["message_id"])
            send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(is_admin))
            del admin_actions[user_id]
            return jsonify({"ok": True})

        if is_admin and cb["data"].startswith("period_"):
            if user_id not in admin_actions:
                return jsonify({"ok": True})
            adata = admin_actions[user_id]
            target_id = adata.get("target_id")
            target_username, _ = get_user_info(target_id)
            _, admin_name = get_user_info(user_id)
            days_map = {"1hour": 1/24, "1day": 1, "7days": 7, "1month": 30, "6months": 180, "12months": 365, "forever": 9999}
            days = days_map.get(cb["data"].replace("period_", ""), 30)
            sub_name = f"{days} дней" if days < 9999 else "навсегда"
            key = gen_key()
            uid = next_uid
            next_uid += 1
            expire = int((datetime.now() + timedelta(days=days)).timestamp()) if days < 9999 else 9999999999
            link = create_invite_link(GROUP_ID, target_id, days if days < 9999 else 365)
            users_db[str(target_id)] = {"uid": uid, "key": key, "expire": expire, "subscription_name": sub_name, "days": (days if days < 9999 else 9999), "invite_link": link, "step": "done"}
            expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y") if days < 9999 else "никогда"
            send_message(target_id, f"🎉 {target_username}, поздравляю! Тебе {admin_name} выдал подписку на {sub_name}\n\n🆔 UID: {uid}\n🔑 Ключ: {key}\n⏳ Ключ истекает: {expire_str}\n\n🔗 Ссылка в группу с покупателями: {link}")
            delete_message(chat_id, cb["message"]["message_id"])
            send_message(chat_id, f"✅ Подписка на {sub_name} выдана {target_username}", reply_markup=get_main_keyboard(is_admin))
            del admin_actions[user_id]
            return jsonify({"ok": True})

        if is_admin and cb["data"] == "cancel_action":
            if user_id in admin_actions:
                del admin_actions[user_id]
            delete_message(chat_id, cb["message"]["message_id"])
            send_message(chat_id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

    if "message" in data and "contact" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        if user_id in admin_actions and admin_actions[user_id].get("step") in ("wait_target", "wait_transfer"):
            contact = msg["contact"]
            target_id = contact["user_id"]
            target_username, _ = get_user_info(target_id)
            mode = admin_actions[user_id].get("mode")
            if mode == "premium" and not is_premium_user(target_id):
                send_message(chat_id, "❌ Этот пользователь не имеет премиум‑подписки. Попробуйте другого.")
                return jsonify({"ok": True})
            step = admin_actions[user_id].get("step")
            if step == "wait_target":
                admin_actions[user_id]["target_id"] = target_id
                admin_actions[user_id]["target_username"] = target_username
                admin_actions[user_id]["step"] = "wait_confirm"
                action = admin_actions[user_id]["action"]
                _, admin_name = get_user_info(user_id)
                texts = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
                target_display = f"@{target_username}" if target_username else f"id: {target_id}"
                kb = {"inline_keyboard": [[{"text": "✅ Да", "callback_data": f"confirm_{action}"}], [{"text": "❌ Нет", "callback_data": "cancel_action"}]]}
                send_message(chat_id, f"👉 {admin_name}, ты точно хочешь {texts.get(action, 'действие')} {target_display} подписку?", parse_mode="HTML", reply_markup=kb)
            elif step == "wait_transfer":
                from_id = admin_actions[user_id].get("from_id")
                from_username = admin_actions[user_id].get("from_username")
                if str(from_id) in users_db:
                    data = users_db[str(from_id)].copy()
                    users_db[str(target_id)] = data
                    del users_db[str(from_id)]
                    new_link = create_invite_link(GROUP_ID, target_id, data.get("days", 30))
                    if new_link:
                        users_db[str(target_id)]["invite_link"] = new_link
                    _, admin_name = get_user_info(user_id)
                    send_message(from_id, f"🤝 {from_username}, твоя подписка была передана админом {admin_name}: @{target_username or target_id}")
                    send_message(chat_id, f"✅ Подписка передана от {from_username} к {target_username or target_id}")
                else:
                    send_message(chat_id, "❌ Не удалось передать подписку")
                send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(True))
                del admin_actions[user_id]
            return jsonify({"ok": True})

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
