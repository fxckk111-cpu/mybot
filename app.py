import os
import json
import requests
import random
import string
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8687695414:AAFX_eG3x05gQXahtMogvAh2JYfQuiwyWCM"
CRYPTOBOT_TOKEN = "579104:AARyyU3ZKIVsb3hgHxYWnMYyVnQhzNASc71"
GROUP_ID = -1003992937868

PRICE_RUB = 200
DAYS_VALID = 30

# ID админов (кто может заходить в админ-панель)
ADMIN_IDS = ["8095717532", "522044023"]

SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

# ========== ДАЛЬШЕ КОД ==========
CRYPTO_API_URL = "https://pay.crypt.bot/api/"
app = Flask(__name__)

# База пользователей
users_db = {}

# Временные данные для админ-действий
admin_actions = {}

def gen_uid():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def gen_key():
    parts = []
    for i in range(10):
        parts.append(random.choice(string.ascii_lowercase))
        parts.append(random.choice(string.digits))
    return ''.join(parts)[:20]

def get_user_info(user_id):
    """Получает username и first_name пользователя по ID"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            return data["result"].get("username"), data["result"].get("first_name")
    except:
        pass
    return None, None

def kick_from_group(chat_id, user_id):
    """Кикает пользователя из группы"""
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

def create_invite_link(chat_id, user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    params = {
        "chat_id": chat_id,
        "member_limit": 1,
        "expire_date": int((datetime.now() + timedelta(days=DAYS_VALID)).timestamp())
    }
    r = requests.post(url, json=params)
    data = r.json()
    if data.get("ok"):
        return data["result"]["invite_link"]
    return None

def get_main_keyboard(is_admin=False):
    keyboard = [["⚡ Купить чит"], ["🔑 Мои ключи"], ["ℹ️ Info"]]
    if is_admin:
        keyboard.append(["👑 Админ панель"])
    return {"keyboard": keyboard, "resize_keyboard": True}

# ========== АДМИН-ПАНЕЛЬ ==========
def send_admin_panel(chat_id, first_name):
    keyboard = {
        "inline_keyboard": [
            [{"text": "😒 Забрать подписку", "callback_data": "admin_revoke"}],
            [{"text": "🤝 Передать подписку", "callback_data": "admin_transfer"}],
            [{"text": "❄ Заморозить подписку", "callback_data": "admin_freeze"}],
            [{"text": "🎁 Выдать подписку", "callback_data": "admin_grant"}]
        ]
    }
    send_message(chat_id, f"👋 Привет, <b>{first_name}</b>!\n😂 Что хочешь сделать?", parse_mode="HTML", reply_markup=keyboard)

def process_admin_action(chat_id, admin_name, action, target_id, target_username, extra_data=None):
    """Обрабатывает действия админа с пользователем"""
    emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
    emoji = emojis.get(action, "⚠️")
    action_names = {"revoke": "забрал", "transfer": "передал", "freeze": "заморозил", "grant": "выдал"}
    
    target_id_str = str(target_id)
    
    if action == "revoke":
        if target_id_str in users_db and "key" in users_db[target_id_str]:
            sub_name = users_db[target_id_str].get("subscription_name", "подписка")
            key = users_db[target_id_str]["key"]
            # Удаляем подписку
            del users_db[target_id_str]
            # Кикаем из группы
            kick_from_group(GROUP_ID, target_id)
            # Уведомляем пользователя
            send_message(target_id, f"{emoji} <b>{target_username or target_id_str}</b>, у тебя <b>{admin_name}</b> {action_names[action]} {sub_name} и твой ключ: <code>{key}</code> больше не доступен", parse_mode="HTML")
            send_message(chat_id, f"✅ Подписка у пользователя {target_username or target_id_str} отобрана")
        else:
            send_message(chat_id, f"❌ У пользователя {target_username or target_id_str} нет активной подписки")
    
    elif action == "freeze":
        if target_id_str in users_db and "key" in users_db[target_id_str]:
            sub_name = users_db[target_id_str].get("subscription_name", "подписка")
            users_db[target_id_str]["frozen"] = True
            users_db[target_id_str]["old_expire"] = users_db[target_id_str]["expire"]
            send_message(target_id, f"{emoji} <b>{target_username or target_id_str}</b>, твоя подписка на {sub_name} была заморожена админом <b>{admin_name}</b>.", parse_mode="HTML")
            send_message(chat_id, f"✅ Подписка пользователя {target_username or target_id_str} заморожена")
        else:
            send_message(chat_id, f"❌ У пользователя {target_username or target_id_str} нет активной подписки")
    
    elif action == "transfer":
        # transfer требует двух пользователей: от кого и кому
        # В extra_data должен быть словарь с "from_id" и "to_id"
        from_id = extra_data.get("from_id")
        to_id = extra_data.get("to_id")
        if from_id and to_id and str(from_id) in users_db:
            user_data = users_db[str(from_id)].copy()
            # Передаём подписку
            users_db[str(to_id)] = user_data
            del users_db[str(from_id)]
            # Создаём новую ссылку для нового пользователя
            new_link = create_invite_link(GROUP_ID, to_id)
            if new_link:
                users_db[str(to_id)]["invite_link"] = new_link
            # Уведомления
            send_message(from_id, f"⚠️ <b>{target_username or from_id}</b> твоя подписка была передана админом <b>{admin_name}</b>: @{extra_data.get('to_username', to_id)}", parse_mode="HTML")
            send_message(chat_id, f"✅ Подписка передана от {extra_data.get('from_username', from_id)} к {extra_data.get('to_username', to_id)}")
        else:
            send_message(chat_id, "❌ Не удалось передать подписку")
    
    elif action == "grant":
        days = extra_data.get("days", 30)
        sub_name = f"{days} дней"
        key = gen_key()
        uid = gen_uid()
        expire = int((datetime.now() + timedelta(days=days)).timestamp())
        invite_link = create_invite_link(GROUP_ID, target_id)
        users_db[target_id_str] = {
            "uid": uid,
            "key": key,
            "expire": expire,
            "subscription_name": sub_name,
            "invite_link": invite_link,
            "step": "done"
        }
        expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
        # Уведомляем пользователя
        send_message(target_id, 
            f"🎉 <b>{target_username or target_id_str}</b>, поздравляю! Тебе <b>{admin_name}</b> выдал подписку на {sub_name}\n\n"
            f"👾 <b>{uid}</b>\n"
            f"🔑 <b>Ключ:</b> <code>{key}</code>\n"
            f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
            f"🔗 <a href='{invite_link}'>Ссылка в группу с покупателями</a>", 
            parse_mode="HTML")
        send_message(chat_id, f"✅ Подписка на {sub_name} выдана пользователю {target_username or target_id_str}")

# ========== ОСНОВНОЙ ВЕБХУК ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
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
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", 
                        parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))

        elif text == "👑 Админ панель" and is_admin:
            send_admin_panel(chat_id, msg['from']['first_name'])

        elif text == "⚡ Купить чит":
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
                send_message(chat_id, f"❌ Ошибка: {e}\nОбратитесь к @pwnmeifucan")

        elif text == "🔑 Мои ключи":
            if user_id not in users_db or "key" not in users_db[user_id]:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                u_data = users_db[user_id]
                expire_str = datetime.fromtimestamp(u_data["expire"]).strftime("%d.%m.%Y")
                msg_text = (
                    f"👾 <b>{u_data['uid']}</b>\n"
                    f"🔑 <b>Ключ:</b> <code>{u_data['key']}</code>\n"
                    f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
                    f"🔗 <a href='{u_data['invite_link']}'>Ссылка в группу с покупателями</a>"
                )
                send_message(chat_id, msg_text, parse_mode="HTML")

        elif text == "ℹ️ Info":
            info = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, info, parse_mode="HTML", disable_web_page_preview=True)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]
        is_admin = user_id in ADMIN_IDS

        # Обработка админ-панели
        if cb_data.startswith("admin_"):
            if not is_admin:
                return jsonify({"ok": True})
            
            action = cb_data.replace("admin_", "")
            admin_actions[user_id] = {"action": action, "step": "wait_target"}
            target_type = "юзернейм или id"
            
            emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
            emoji = emojis.get(action, "⚠️")
            action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
            
            update_message(chat_id, message_id, 
                f"{emoji} Хорошо, <b>{cb['from']['first_name']}</b>! {action_names[action]} так {action_names[action]}!\n"
                f"Напиши @username или id пользователя, кому {action_names[action]}",
                parse_mode="HTML")
            return jsonify({"ok": True})

        # Обработка подтверждения действия
        elif cb_data.startswith("confirm_"):
            parts = cb_data.split("_")
            action = parts[1]
            target_id = parts[2] if len(parts) > 2 else None
            
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_confirm":
                action_data = admin_actions[user_id]
                target_id_str = action_data.get("target_id")
                target_username = action_data.get("target_username")
                
                # Получаем имя админа
                admin_name = cb['from']['first_name']
                
                if target_id_str:
                    process_admin_action(chat_id, admin_name, action, target_id_str, target_username, action_data.get("extra"))
                
                delete_message(chat_id, message_id)
                send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(is_admin))
                del admin_actions[user_id]
            
            return jsonify({"ok": True})

        elif cb_data.startswith("cancel_"):
            if user_id in admin_actions:
                del admin_actions[user_id]
            delete_message(chat_id, message_id)
            send_message(chat_id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

        # Обработка выбора периода для выдачи подписки
        elif cb_data.startswith("period_"):
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_period":
                days_map = {"1hour": 1/24, "1day": 1, "7days": 7, "1month": 30, "6months": 180, "12months": 365, "forever": 9999}
                period_key = cb_data.replace("period_", "")
                days = days_map.get(period_key, 30)
                
                action_data = admin_actions[user_id]
                target_id_str = action_data.get("target_id")
                target_username = action_data.get("target_username")
                admin_name = cb['from']['first_name']
                action = action_data.get("action")
                
                # Выдаём подписку
                process_admin_action(chat_id, admin_name, action, target_id_str, target_username, {"days": days})
                
                delete_message(chat_id, message_id)
                send_message(chat_id, "✅ Подписка выдана!", reply_markup=get_main_keyboard(is_admin))
                del admin_actions[user_id]
            
            return jsonify({"ok": True})

        # Обычная проверка оплаты
        elif cb_data == "check_payment":
            if user_id not in users_db or users_db[user_id].get("step") != "wait_payment":
                update_message(chat_id, message_id, "❌ Нет активного счета. Начните новую покупку.")
                return

            invoice_id = users_db[user_id]["invoice_id"]
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [invoice_id]})
                if inv["items"][0]["status"] == "paid":
                    uid = gen_uid()
                    key = gen_key()
                    expire = int((datetime.now() + timedelta(days=DAYS_VALID)).timestamp())
                    invite_link = create_invite_link(GROUP_ID, user_id)
                    users_db[user_id] = {
                        "uid": uid,
                        "key": key,
                        "expire": expire,
                        "subscription_name": f"{DAYS_VALID} дней",
                        "invite_link": invite_link,
                        "step": "done"
                    }
                    expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
                    msg = (
                        f"✅ Оплата подтверждена!\n\n"
                        f"👾 <b>{uid}</b>\n"
                        f"🔑 <b>Ключ:</b> <code>{key}</code>\n"
                        f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
                        f"🔗 <a href='{invite_link}'>Ссылка в группу с покупателями</a>"
                    )
                    update_message(chat_id, message_id, msg, parse_mode="HTML")
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён. Попробуйте позже.")
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка проверки: {e}")

    # Обработка текстовых сообщений для админ-действий
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        
        if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_target":
            action_data = admin_actions[user_id]
            action = action_data.get("action")
            
            # Парсим ввод: может быть @username или число (id)
            target_username = None
            target_id = None
            
            if text.startswith("@"):
                target_username = text[1:]
                # Получаем id по username
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
                r = requests.get(url, params={"chat_id": text})
                data_resp = r.json()
                if data_resp.get("ok"):
                    target_id = data_resp["result"]["id"]
                else:
                    send_message(chat_id, "❌ Не удалось найти пользователя с таким username")
                    return jsonify({"ok": True})
            elif text.isdigit():
                target_id = int(text)
            else:
                send_message(chat_id, "❌ Введите корректный @username или id")
                return jsonify({"ok": True})
            
            admin_actions[user_id]["target_id"] = target_id
            admin_actions[user_id]["target_username"] = target_username
            admin_actions[user_id]["step"] = "wait_confirm"
            
            emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
            emoji = emojis.get(action, "⚠️")
            action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
            target_display = f"@{target_username}" if target_username else f"id: {target_id}"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "✅ Да", "callback_data": f"confirm_{action}_{target_id}"}],
                    [{"text": "❌ Нет", "callback_data": f"cancel_{action}"}]
                ]
            }
            send_message(chat_id, 
                f"{emoji} <b>{msg['from']['first_name']}</b>, ты точно хочешь {action_names[action]} {target_display} подписку?",
                parse_mode="HTML", reply_markup=keyboard)

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "Бот работает!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
