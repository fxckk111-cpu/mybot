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
next_uid = 1

ADMIN_UIDS = {
    "522044023": "777777",
    "8095717532": "777778"
}
ADMIN_KEYS = {
    "522044023": "".join(random.choices(string.ascii_lowercase + string.digits, k=20)),
    "8095717532": "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
}

def save_users():
    with open("users.json", "w") as f:
        json.dump({"users": users_db, "next_uid": next_uid}, f, indent=2)

def load_users():
    global users_db, next_uid
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            data = json.load(f)
            users_db = data.get("users", {})
            next_uid = data.get("next_uid", 1)
    for admin_id in ADMIN_IDS:
        if admin_id not in users_db:
            users_db[admin_id] = {
                "uid": ADMIN_UIDS.get(admin_id, f"ADMIN_{admin_id[-4:]}"),
                "key": ADMIN_KEYS.get(admin_id, gen_key()),
                "expire": 9999999999,
                "subscription_name": "навсегда",
                "invite_link": f"https://t.me/+group_{admin_id[-6:]}",
                "days": 9999
            }
    save_users()

def gen_key():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def get_chat_info(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            info = data["result"]
            return info.get("username"), info.get("first_name")
    except:
        pass
    return None, None

def get_user_display(user_id):
    username, first_name = get_chat_info(user_id)
    return f"@{username}" if username else first_name or str(user_id)

def kick_from_group(chat_id, user_id):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember", json={"chat_id": chat_id, "user_id": user_id})

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
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

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
    params = {"chat_id": chat_id, "member_limit": 1, "expire_date": int((datetime.now() + timedelta(days=days)).timestamp())}
    r = requests.post(url, json=params)
    data = r.json()
    return data["result"]["invite_link"] if data.get("ok") else None

def get_main_keyboard(is_admin=False):
    if is_admin:
        return {"keyboard": [["🔑 Мои ключи"], ["👑 Админ панель"]], "resize_keyboard": True}
    return {"keyboard": [["⚡ Купить чит"], ["🔑 Мои ключи"], ["ℹ️ Информация"]], "resize_keyboard": True}

def check_user_premium(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        r = requests.get(url, params={"chat_id": user_id, "user_id": user_id})
        data = r.json()
        if data.get("ok"):
            status = data["result"].get("status")
            return status in ["creator", "administrator", "member"]
    except:
        pass
    return False

def send_admin_action_interface(chat_id, admin_name, action):
    emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
    emoji = emojis.get(action, "⚠️")
    action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "👤 User", "callback_data": f"select_user_{action}_normal", "request_user": {"request_id": 1, "user_is_bot": False, "user_is_premium": False}}],
            [{"text": "⭐ Premium", "callback_data": f"select_user_{action}_premium", "request_user": {"request_id": 2, "user_is_bot": False, "user_is_premium": True}}],
            [{"text": "🔙 Назад", "callback_data": "back_to_menu"}]
        ]
    }
    send_message(chat_id, f"{emoji} Хорошо, <b>{admin_name}</b>! {action_names[action]} так {action_names[action]}!\n\nВыберите пользователя:", parse_mode="HTML", reply_markup=keyboard)

load_users()

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
        text = msg.get("text", "")
        is_admin = user_id in ADMIN_IDS

        if text == "/start":
            if user_id not in users_db and not is_admin:
                users_db[user_id] = {"uid": next_uid, "step": "new"}
                next_uid += 1
                save_users()
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))

        elif text == "👑 Админ панель" and is_admin:
            keyboard = {"inline_keyboard": [[{"text": "😒 Забрать подписку", "callback_data": "admin_revoke"}], [{"text": "🤝 Передать подписку", "callback_data": "admin_transfer"}], [{"text": "❄ Заморозить подписку", "callback_data": "admin_freeze"}], [{"text": "🎁 Выдать подписку", "callback_data": "admin_grant"}], [{"text": "🔙 Назад", "callback_data": "back_to_menu"}]]}
            send_message(chat_id, f"👋 Привет, <b>{msg['from']['first_name']}</b>!\n😂 Что хочешь сделать?", parse_mode="HTML", reply_markup=keyboard)

        elif text == "🔑 Мои ключи":
            sub = users_db.get(user_id)
            if not sub or "key" not in sub:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                expire_str = "никогда" if sub["expire"] >= 999999999 else datetime.fromtimestamp(sub["expire"]).strftime("%d.%m.%Y")
                msg_text = f"🆔 UID: <b>{sub['uid']}</b>\n🔑 Ключ: <code>{sub['key']}</code>\n⏳ Ключ истекает: <i>{expire_str}</i>"
                if sub.get("invite_link"):
                    msg_text += f"\n\n🔗 Ссылка в группу с покупателями: {sub['invite_link']}"
                send_message(chat_id, msg_text, parse_mode="HTML")

        elif text == "ℹ️ Информация" and not is_admin:
            send_message(chat_id, f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>", parse_mode="HTML", disable_web_page_preview=True)

        elif text == "⚡ Купить чит" and not is_admin:
            keyboard = {"inline_keyboard": [[{"text": f"📅 {p['days']} дней — {p['price']}₽", "callback_data": f"plan_{p['days']}_{p['price']}"}] for p in PRICE_PLANS] + [[{"text": "🔙 Назад", "callback_data": "back_to_menu"}]]}
            send_message(chat_id, "⚡️ Выберите тариф:", reply_markup=keyboard)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]

        if cb_data == "back_to_menu":
            delete_message(chat_id, message_id)
            send_message(chat_id, f"👾 Привет, <b>{cb['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=get_main_keyboard(user_id in ADMIN_IDS))
            return jsonify({"ok": True})

        if cb_data.startswith("plan_"):
            parts = cb_data.split("_")
            days, price = int(parts[1]), int(parts[2])
            kb = {"inline_keyboard": [[{"text": "🤝 Через реселлера", "url": RESELLER_LINK}], [{"text": "💎 CryptoBot", "callback_data": f"crypto_{days}_{price}"}], [{"text": "🔙 Назад", "callback_data": "back_to_menu"}]]}
            update_message(chat_id, message_id, f"💳 Подписка на {days} дней — {price}₽\n\nВыберите способ оплаты:", reply_markup=kb)
            return jsonify({"ok": True})

        if cb_data.startswith("crypto_"):
            parts = cb_data.split("_")
            days, price = int(parts[1]), int(parts[2])
            amount = round(price / get_usdt_rate(), 2)
            try:
                inv = crypto_api("createInvoice", {"asset": "USDT", "amount": str(amount), "description": f"Подписка на {days} дней"})
                users_db[user_id] = {"invoice_id": inv["invoice_id"], "days": days, "price": price, "step": "wait_payment"}
                save_users()
                kb = {"inline_keyboard": [[{"text": "💎 Оплатить в CryptoBot", "url": inv["bot_invoice_url"]}], [{"text": "✅ Я оплатил", "callback_data": f"check_{days}_{price}"}], [{"text": "🔙 Назад", "callback_data": "back_to_menu"}]]}
                update_message(chat_id, message_id, f"💳 {amount} USDT (~{price} ₽) · {days} дн.\n\nОплатите и нажмите «Я оплатил».", reply_markup=kb)
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка: {e}")
            return jsonify({"ok": True})

        if cb_data.startswith("check_"):
            parts = cb_data.split("_")
            days, price = int(parts[1]), int(parts[2])
            if user_id not in users_db or users_db[user_id].get("step") != "wait_payment":
                update_message(chat_id, message_id, "❌ Нет активного счета.")
                return
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [users_db[user_id]["invoice_id"]]})
                if inv["items"][0]["status"] == "paid":
                    uid = users_db[user_id].get("uid", next_uid)
                    if uid == next_uid:
                        next_uid += 1
                    key = gen_key()
                    expire = int((datetime.now() + timedelta(days=days)).timestamp())
                    invite_link = create_invite_link(GROUP_ID, user_id, days)
                    users_db[user_id] = {"uid": uid, "key": key, "expire": expire, "subscription_name": f"{days} дней", "days": days, "invite_link": invite_link, "step": "done"}
                    save_users()
                    expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
                    update_message(chat_id, message_id, f"✅ Оплата подтверждена!\n\n🆔 UID: <b>{uid}</b>\n🔑 Ключ: <code>{key}</code>\n⏳ Ключ истекает: <i>{expire_str}</i>\n\n🔗 Ссылка в группу с покупателями: {invite_link}", parse_mode="HTML")
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён. Попробуйте позже.")
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка: {e}")
            return jsonify({"ok": True})

        if cb_data.startswith("admin_"):
            if user_id not in ADMIN_IDS:
                return jsonify({"ok": True})
            action = cb_data.replace("admin_", "")
            admin_actions[user_id] = {"action": action, "step": "wait_user"}
            send_admin_action_interface(chat_id, cb['from']['first_name'], action)
            return jsonify({"ok": True})

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        
        if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_user":
            action_data = admin_actions[user_id]
            action = action_data.get("action")
            
            if text.startswith("@"):
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": text})
                data_r = r.json()
                if data_r.get("ok"):
                    target_id = str(data_r["result"]["id"])
                    target_display = get_user_display(target_id)
                    
                    delete_message(chat_id, msg["message_id"])
                    emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
                    emoji = emojis.get(action, "⚠️")
                    action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
                    
                    if action == "grant":
                        admin_actions[user_id]["target_id"] = target_id
                        admin_actions[user_id]["step"] = "wait_period"
                        keyboard = {"inline_keyboard": [[{"text": "1 час", "callback_data": "period_1hour"}], [{"text": "1 день", "callback_data": "period_1day"}], [{"text": "7 дней", "callback_data": "period_7days"}], [{"text": "1 месяц", "callback_data": "period_1month"}], [{"text": "6 месяцев", "callback_data": "period_6months"}], [{"text": "12 месяцев", "callback_data": "period_12months"}], [{"text": "Навсегда", "callback_data": "period_forever"}], [{"text": "🔙 Отмена", "callback_data": "cancel_action"}]]}
                        send_message(chat_id, f"{emoji} Выберите период подписки для {target_display}:", reply_markup=keyboard)
                    elif action == "transfer":
                        admin_actions[user_id]["from_id"] = target_id
                        admin_actions[user_id]["step"] = "wait_transfer_target"
                        send_message(chat_id, f"{emoji} Теперь напишите @username пользователя, КОМУ передать подписку от {target_display}:")
                    else:
                        admin_actions[user_id]["target_id"] = target_id
                        keyboard = {"inline_keyboard": [[{"text": "✅ Да", "callback_data": f"confirm_{action}"}], [{"text": "❌ Нет", "callback_data": "cancel_action"}]]}
                        send_message(chat_id, f"{emoji} <b>{msg['from']['first_name']}</b>, ты точно хочешь {action_names[action]} подписку у {target_display}?", parse_mode="HTML", reply_markup=keyboard)
            else:
                send_message(chat_id, "❌ Используйте @username пользователя.")
            return jsonify({"ok": True})

        if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_transfer_target":
            action_data = admin_actions[user_id]
            from_id = action_data.get("from_id")
            
            if text.startswith("@"):
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": text})
                data_r = r.json()
                if data_r.get("ok"):
                    to_id = str(data_r["result"]["id"])
                    from_display = get_user_display(from_id)
                    to_display = get_user_display(to_id)
                    
                    if from_id in users_db and "key" in users_db[from_id]:
                        user_data = users_db[from_id].copy()
                        users_db[to_id] = user_data
                        del users_db[from_id]
                        new_link = create_invite_link(GROUP_ID, to_id, user_data.get("days", 30))
                        if new_link:
                            users_db[to_id]["invite_link"] = new_link
                        save_users()
                        send_message(from_id, f"🤝 {from_display}, твоя подписка была передана админом {msg['from']['first_name']}: {to_display}", parse_mode="HTML")
                        send_message(chat_id, f"✅ Подписка передана от {from_display} к {to_display}")
                    else:
                        send_message(chat_id, "❌ Не удалось передать подписку")
                    del admin_actions[user_id]
                    send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(True))
            else:
                send_message(chat_id, "❌ Используйте @username пользователя.")
            return jsonify({"ok": True})

    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]

        if cb_data.startswith("select_user_"):
            parts = cb_data.split("_")
            action = parts[2]
            premium_type = parts[3]
            
            admin_actions[user_id] = {"action": action, "step": "wait_user"}
            send_admin_action_interface(chat_id, cb['from']['first_name'], action)
            return jsonify({"ok": True})

        if cb_data.startswith("confirm_"):
            action = cb_data.replace("confirm_", "")
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_confirm":
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                admin_name = cb['from']['first_name']
                target_display = get_user_display(target_id)

                if action == "revoke":
                    if target_id in users_db and "key" in users_db[target_id]:
                        sub_name = users_db[target_id].get("subscription_name", "подписка")
                        key = users_db[target_id]["key"]
                        del users_db[target_id]
                        save_users()
                        kick_from_group(GROUP_ID, target_id)
                        send_message(target_id, f"😒 {target_display}, у тебя {admin_name} забрал твою подписку «{sub_name}», и твой ключ: <code>{key}</code> больше не доступен", parse_mode="HTML")
                        send_message(chat_id, f"✅ Подписка у {target_display} отобрана")
                    else:
                        send_message(chat_id, f"❌ У {target_display} нет активной подписки")
                elif action == "freeze":
                    if target_id in users_db and "key" in users_db[target_id]:
                        sub_name = users_db[target_id].get("subscription_name", "подписка")
                        users_db[target_id]["frozen"] = True
                        users_db[target_id]["old_expire"] = users_db[target_id]["expire"]
                        save_users()
                        send_message(target_id, f"❄ {target_display}, твоя подписка «{sub_name}» была заморожена админом {admin_name}.", parse_mode="HTML")
                        send_message(chat_id, f"✅ Подписка {target_display} заморожена")
                    else:
                        send_message(chat_id, f"❌ У {target_display} нет активной подписки")
                
                delete_message(chat_id, message_id)
                send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(True))
                del admin_actions[user_id]
            return jsonify({"ok": True})

        if cb_data.startswith("period_"):
            period_key = cb_data.replace("period_", "")
            days_map = {"1hour": 1/24, "1day": 1, "7days": 7, "1month": 30, "6months": 180, "12months": 365, "forever": 9999}
            days = days_map.get(period_key, 30)
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_period":
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                admin_name = cb['from']['first_name']
                target_display = get_user_display(target_id)
                
                sub_name = f"{days} дней" if days < 9999 else "навсегда"
                key = gen_key()
                uid = next_uid
                next_uid += 1
                expire = int((datetime.now() + timedelta(days=days)).timestamp()) if days < 9999 else 9999999999
                invite_link = create_invite_link(GROUP_ID, target_id, days if days < 9999 else 365)
                users_db[target_id] = {"uid": uid, "key": key, "expire": expire, "subscription_name": sub_name, "days": days, "invite_link": invite_link, "step": "done"}
                save_users()
                expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y") if days < 9999 else "никогда"
                send_message(target_id, f"🎉 {target_display}, поздравляю! Тебе {admin_name} выдал подписку на {sub_name}\n\n🆔 UID: <b>{uid}</b>\n🔑 Ключ: <code>{key}</code>\n⏳ Ключ истекает: <i>{expire_str}</i>\n\n🔗 Ссылка в группу с покупателями: {invite_link}", parse_mode="HTML")
                delete_message(chat_id, message_id)
                send_message(chat_id, f"✅ Подписка на {sub_name} выдана пользователю {target_display}", reply_markup=get_main_keyboard(True))
                del admin_actions[user_id]
            return jsonify({"ok": True})

        if cb_data == "cancel_action":
            if user_id in admin_actions:
                del admin_actions[user_id]
            delete_message(chat_id, message_id)
            send_message(chat_id, "❌ Действие отменено", reply_markup=get_main_keyboard(user_id in ADMIN_IDS))
            return jsonify({"ok": True})

    if "message" in data and "users_shared" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_shared = msg.get("users_shared", {})
        users_list = user_shared.get("users", [])
        
        if users_list:
            selected_user_id = str(users_list[0]["user_id"])
            action_data = admin_actions.get(str(chat_id), {})
            action = action_data.get("action", "")
            
            if action:
                target_display = get_user_display(selected_user_id)
                emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
                emoji = emojis.get(action, "⚠️")
                action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
                
                if action == "grant":
                    admin_actions[str(chat_id)]["target_id"] = selected_user_id
                    admin_actions[str(chat_id)]["step"] = "wait_period"
                    keyboard = {"inline_keyboard": [[{"text": "1 час", "callback_data": "period_1hour"}], [{"text": "1 день", "callback_data": "period_1day"}], [{"text": "7 дней", "callback_data": "period_7days"}], [{"text": "1 месяц", "callback_data": "period_1month"}], [{"text": "6 месяцев", "callback_data": "period_6months"}], [{"text": "12 месяцев", "callback_data": "period_12months"}], [{"text": "Навсегда", "callback_data": "period_forever"}], [{"text": "🔙 Отмена", "callback_data": "cancel_action"}]]}
                    send_message(chat_id, f"{emoji} Выберите период подписки для {target_display}:", reply_markup=keyboard)
                elif action == "transfer":
                    admin_actions[str(chat_id)]["from_id"] = selected_user_id
                    admin_actions[str(chat_id)]["step"] = "wait_transfer_target"
                    send_message(chat_id, f"{emoji} Теперь выберите пользователя, КОМУ передать подписку от {target_display}:", reply_markup={"inline_keyboard": [[{"text": "👤 Выбрать пользователя", "request_user": {"request_id": 3, "user_is_bot": False}}]]})
                else:
                    admin_actions[str(chat_id)]["target_id"] = selected_user_id
                    keyboard = {"inline_keyboard": [[{"text": "✅ Да", "callback_data": f"confirm_{action}"}], [{"text": "❌ Нет", "callback_data": "cancel_action"}]]}
                    send_message(chat_id, f"{emoji} <b>{msg['from']['first_name']}</b>, ты точно хочешь {action_names[action]} подписку у {target_display}?", parse_mode="HTML", reply_markup=keyboard)

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
