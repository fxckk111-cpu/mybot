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

# Тарифы
PRICE_PLANS = [
    {"days": 7, "price": 50},
    {"days": 30, "price": 100},
    {"days": 60, "price": 200},
    {"days": 90, "price": 300}
]

# ID админов (их UID зафиксирован)
ADMIN_UID_MAP = {
    "522044023": 0,
    "8095717532": 1
}
ADMIN_IDS = list(ADMIN_UID_MAP.keys())

# Ссылки
RESELLER_LINK = "https://t.me/realsapphire"
SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

CRYPTO_API_URL = "https://pay.crypt.bot/api/"
app = Flask(__name__)

# База данных: user_id -> {uid, key, expire, invite_link, username}
users_db = {}

# Счётчик для следующих UID (начинаем с 2, т.к. 0 и 1 заняты админами)
next_uid = 2

# Временные данные для админ-действий
admin_actions = {}

def gen_key():
    """Генерирует ключ до 20 символов (буквы+цифры)"""
    parts = []
    for i in range(10):
        parts.append(random.choice(string.ascii_lowercase))
        parts.append(random.choice(string.digits))
    return ''.join(parts)[:20]

def get_username(user_id):
    """Получает username пользователя по id (без @)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            result = data["result"]
            username = result.get("username")
            if username:
                return username
            return result.get("first_name", str(user_id))
    except:
        pass
    return str(user_id)

def resolve_target(input_text):
    """Определяет user_id по @username или id"""
    input_text = input_text.strip()
    
    # Если начинается с @ — ищем по username
    if input_text.startswith("@"):
        username = input_text[1:]
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        try:
            r = requests.get(url, params={"chat_id": input_text})
            data = r.json()
            if data.get("ok"):
                return data["result"]["id"], username
        except:
            pass
        return None, None
    
    # Если просто цифры — это id
    elif input_text.isdigit():
        return int(input_text), None
    
    return None, None

def kick_from_group(user_id):
    """Кикает пользователя из группы"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember"
    try:
        requests.post(url, json={"chat_id": GROUP_ID, "user_id": user_id})
    except:
        pass

def create_invite_link(user_id, days=30):
    """Создаёт одноразовую ссылку в группу"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    expire_date = int((datetime.now() + timedelta(days=days)).timestamp())
    params = {
        "chat_id": GROUP_ID,
        "member_limit": 1,
        "expire_date": expire_date
    }
    try:
        r = requests.post(url, json=params)
        data = r.json()
        if data.get("ok"):
            return data["result"]["invite_link"]
    except:
        pass
    return None

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
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

def get_main_keyboard(is_admin=False):
    if is_admin:
        keyboard = [["🔑 Мои ключи"], ["👑 Админ панель"]]
    else:
        keyboard = [["⚡ Купить чит"], ["🔑 Мои ключи"], ["ℹ️ Информация"]]
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_user_subscription_info(user_id):
    """Возвращает информацию о подписке пользователя"""
    user_id_str = str(user_id)
    if user_id_str in users_db:
        return users_db[user_id_str]
    return None

def get_next_uid():
    global next_uid
    uid = next_uid
    next_uid += 1
    return uid

def init_admin_subscriptions():
    """Инициализирует вечные подписки для админов"""
    for admin_id in ADMIN_IDS:
        if admin_id not in users_db:
            key = gen_key()
            invite_link = create_invite_link(admin_id, 365)
            users_db[admin_id] = {
                "uid": ADMIN_UID_MAP[admin_id],
                "key": key,
                "expire": 9999999999,
                "subscription_name": "вечная",
                "days": 9999,
                "invite_link": invite_link,
                "username": get_username(admin_id)
            }

def send_subscription_info(chat_id, user_id):
    """Отправляет информацию о подписке пользователю"""
    sub = get_user_subscription_info(user_id)
    if not sub:
        send_message(chat_id, "😔 Ключей нет.")
        return
    
    if sub["expire"] >= 9999999999:
        expire_str = "никогда"
    else:
        expire_str = datetime.fromtimestamp(sub["expire"]).strftime("%d.%m.%Y")
    
    msg = (
        f"🆔 UID: {sub['uid']}\n"
        f"🔑 Ключ: {sub['key']}\n"
        f"⏳ Ключ истекает: {expire_str}\n"
        f"🔗 Ссылка в группу с покупателями: {sub.get('invite_link', 'Ошибка создания ссылки')}"
    )
    send_message(chat_id, msg, parse_mode=None)

def send_tariffs(chat_id, message_id=None):
    """Отправляет список тарифов"""
    keyboard = {"inline_keyboard": []}
    for plan in PRICE_PLANS:
        keyboard["inline_keyboard"].append([{"text": f"📅 {plan['days']} дней — {plan['price']}₽", "callback_data": f"plan_{plan['days']}_{plan['price']}"}])
    keyboard["inline_keyboard"].append([{"text": "🔙 Назад в меню", "callback_data": "back_to_menu"}])
    
    if message_id:
        update_message(chat_id, message_id, "⚡️ Выберите тариф:", reply_markup=keyboard)
    else:
        send_message(chat_id, "⚡️ Выберите тариф:", reply_markup=keyboard)

def send_payment_methods(chat_id, message_id, days, price):
    """Отправляет кнопки выбора способа оплаты"""
    kb = {
        "inline_keyboard": [
            [{"text": "🤝 Через реселлера", "url": RESELLER_LINK}],
            [{"text": "💎 CryptoBot", "callback_data": f"crypto_pay_{days}_{price}"}],
            [{"text": "🔙 Назад", "callback_data": "back_to_plans"}]
        ]
    }
    update_message(chat_id, message_id, f"💳 Подписка на {days} дней — {price}₽\n\nВыберите способ оплаты:", reply_markup=kb)

def grant_subscription(target_id, days, admin_name):
    """Выдаёт подписку пользователю"""
    target_id_str = str(target_id)
    username = get_username(target_id)
    
    if days >= 9999:
        sub_name = "навсегда"
        expire = 9999999999
    else:
        sub_name = f"{days} дней"
        expire = int((datetime.now() + timedelta(days=days)).timestamp())
    
    key = gen_key()
    uid = get_next_uid()
    invite_link = create_invite_link(target_id, days if days < 9999 else 365)
    
    users_db[target_id_str] = {
        "uid": uid,
        "key": key,
        "expire": expire,
        "subscription_name": sub_name,
        "days": days,
        "invite_link": invite_link,
        "username": username
    }
    
    expire_str = "никогда" if days >= 9999 else datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
    
    send_message(target_id,
        f"🎉 {username}, поздравляю! Тебе {admin_name} выдал подписку на {sub_name}\n\n"
        f"🆔 UID: {uid}\n"
        f"🔑 Ключ: {key}\n"
        f"⏳ Ключ истекает: {expire_str}\n"
        f"🔗 Ссылка в группу с покупателями: {invite_link}"
    )
    return username

def revoke_subscription(target_id, admin_name):
    """Отбирает подписку у пользователя"""
    target_id_str = str(target_id)
    if target_id_str in users_db:
        sub_name = users_db[target_id_str].get("subscription_name", "подписка")
        key = users_db[target_id_str]["key"]
        username = users_db[target_id_str].get("username", get_username(target_id))
        
        del users_db[target_id_str]
        kick_from_group(target_id)
        
        send_message(target_id, f"😒 {username}, у тебя {admin_name} забрал {sub_name} и твой ключ: {key} больше не доступен")
        return username
    return None

def freeze_subscription(target_id, admin_name):
    """Замораживает подписку пользователя"""
    target_id_str = str(target_id)
    if target_id_str in users_db:
        sub_name = users_db[target_id_str].get("subscription_name", "подписка")
        username = users_db[target_id_str].get("username", get_username(target_id))
        
        users_db[target_id_str]["frozen"] = True
        users_db[target_id_str]["old_expire"] = users_db[target_id_str]["expire"]
        
        send_message(target_id, f"❄ {username}, твоя подписка на {sub_name} была заморожена админом {admin_name}.")
        return username
    return None

def transfer_subscription(from_id, to_id, admin_name):
    """Передаёт подписку от одного пользователя другому"""
    from_id_str = str(from_id)
    to_id_str = str(to_id)
    
    if from_id_str in users_db:
        user_data = users_db[from_id_str].copy()
        username_from = user_data.get("username", get_username(from_id))
        
        # Создаём новую ссылку для нового пользователя
        days = user_data.get("days", 30)
        new_link = create_invite_link(to_id, days if days < 9999 else 365)
        user_data["invite_link"] = new_link
        user_data["username"] = get_username(to_id)
        
        users_db[to_id_str] = user_data
        del users_db[from_id_str]
        
        username_to = get_username(to_id)
        
        send_message(from_id, f"🤝 {username_from}, твоя подписка была передана админом {admin_name}: @{username_to}")
        return username_from, username_to
    return None, None

# ========== ВЕБХУК ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    global next_uid
    data = request.get_json()
    if not data:
        return jsonify({"ok": False}), 400

    init_admin_subscriptions()

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        is_admin = user_id in ADMIN_IDS

        if text == "/start":
            if user_id not in users_db and not is_admin:
                users_db[user_id] = {"step": "new"}
            send_message(chat_id, f"👾 Привет, {msg['from']['first_name']}!", 
                        reply_markup=get_main_keyboard(is_admin))

        elif text == "👑 Админ панель" and is_admin:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "😒 Забрать подписку", "callback_data": "admin_revoke"}],
                    [{"text": "🤝 Передать подписку", "callback_data": "admin_transfer"}],
                    [{"text": "❄ Заморозить подписку", "callback_data": "admin_freeze"}],
                    [{"text": "🎁 Выдать подписку", "callback_data": "admin_grant"}],
                    [{"text": "🔙 Назад в меню", "callback_data": "back_to_menu"}]
                ]
            }
            send_message(chat_id, f"👋 Привет, {msg['from']['first_name']}!\n😂 Что хочешь сделать?", reply_markup=keyboard)

        elif text == "⚡ Купить чит" and not is_admin:
            send_tariffs(chat_id)

        elif text == "🔑 Мои ключи":
            send_subscription_info(chat_id, user_id)

        elif text == "ℹ️ Информация" and not is_admin:
            info = f"📋 Информация\n\n📄 Политика конфиденциальности: {PRIVACY_LINK}\n📄 Пользовательское соглашение: {AGREEMENT_LINK}\n\n🆘 Поддержка: {SUPPORT_LINK}"
            send_message(chat_id, info)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]
        is_admin = user_id in ADMIN_IDS
        admin_name = cb["from"]["first_name"]

        # Назад в меню
        if cb_data == "back_to_menu":
            delete_message(chat_id, message_id)
            send_message(chat_id, f"👾 Привет, {cb['from']['first_name']}!", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

        # Назад к тарифам
        if cb_data == "back_to_plans":
            send_tariffs(chat_id, message_id)
            return jsonify({"ok": True})

        # Выбор тарифа
        if cb_data.startswith("plan_"):
            parts = cb_data.split("_")
            days = int(parts[1])
            price = int(parts[2])
            send_payment_methods(chat_id, message_id, days, price)
            return jsonify({"ok": True})

        # CryptoBot оплата
        if cb_data.startswith("crypto_pay_"):
            parts = cb_data.split("_")
            days = int(parts[2])
            price = int(parts[3])
            
            rate = get_usdt_rate()
            amount = round(price / rate, 2)
            
            try:
                inv = crypto_api("createInvoice", {
                    "asset": "USDT",
                    "amount": str(amount),
                    "description": f"Подписка на {days} дней"
                })
                users_db[user_id] = {
                    "invoice_id": inv["invoice_id"],
                    "days": days,
                    "price": price,
                    "step": "wait_payment"
                }
                kb = {"inline_keyboard": [
                    [{"text": "💎 Оплатить в CryptoBot", "url": inv["bot_invoice_url"]}],
                    [{"text": "✅ Я оплатил", "callback_data": f"check_payment_{days}_{price}"}],
                    [{"text": "🔙 Назад", "callback_data": "back_to_plans"}]
                ]}
                update_message(chat_id, message_id, f"💳 {amount} USDT (~{price} ₽) · {days} дн.\n\nОплатите и нажмите «Я оплатил».", reply_markup=kb)
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка: {e}")
            return jsonify({"ok": True})

        # Проверка оплаты
        if cb_data.startswith("check_payment_"):
            parts = cb_data.split("_")
            days = int(parts[2])
            price = int(parts[3])
            
            if user_id not in users_db or users_db[user_id].get("step") != "wait_payment":
                update_message(chat_id, message_id, "❌ Нет активного счета.")
                return

            invoice_id = users_db[user_id]["invoice_id"]
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [invoice_id]})
                if inv["items"][0]["status"] == "paid":
                    username = get_username(user_id)
                    key = gen_key()
                    uid = get_next_uid()
                    expire = int((datetime.now() + timedelta(days=days)).timestamp())
                    invite_link = create_invite_link(user_id, days)
                    
                    users_db[user_id] = {
                        "uid": uid,
                        "key": key,
                        "expire": expire,
                        "subscription_name": f"{days} дней",
                        "days": days,
                        "invite_link": invite_link,
                        "username": username,
                        "step": "done"
                    }
                    expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y")
                    msg = (
                        f"✅ Оплата подтверждена!\n\n"
                        f"🆔 UID: {uid}\n"
                        f"🔑 Ключ: {key}\n"
                        f"⏳ Ключ истекает: {expire_str}\n"
                        f"🔗 Ссылка в группу с покупателями: {invite_link}"
                    )
                    update_message(chat_id, message_id, msg)
                else:
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён.")
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка проверки: {e}")
            return jsonify({"ok": True})

        # Админ-панель — выбор действия
        if cb_data.startswith("admin_"):
            if not is_admin:
                return jsonify({"ok": True})
            
            action = cb_data.replace("admin_", "")
            admin_actions[user_id] = {"action": action, "step": "wait_target"}
            
            emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
            emoji = emojis.get(action, "⚠️")
            action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
            
            update_message(chat_id, message_id,
                f"{emoji} Хорошо, {cb['from']['first_name']}! {action_names[action]} так {action_names[action]}!\n"
                f"Напишите @username или id пользователя, которому нужно {action_names[action]}.\n"
                f"⚠️ Пожалуйста, используйте формат @username или id (пример id: 123456789)",
                parse_mode=None)
            return jsonify({"ok": True})

        # Подтверждение действия (кроме выдачи, там выбор периода)
        if cb_data.startswith("confirm_"):
            action = cb_data.replace("confirm_", "")
            
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_confirm":
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                target_username = action_data.get("target_username")
                
                if action == "grant":
                    # Выбор периода
                    admin_actions[user_id]["step"] = "wait_period"
                    keyboard = {"inline_keyboard": [
                        [{"text": "1 час", "callback_data": "period_1hour"}],
                        [{"text": "1 день", "callback_data": "period_1day"}],
                        [{"text": "7 дней", "callback_data": "period_7days"}],
                        [{"text": "1 месяц", "callback_data": "period_1month"}],
                        [{"text": "6 месяцев", "callback_data": "period_6months"}],
                        [{"text": "12 месяцев", "callback_data": "period_12months"}],
                        [{"text": "Навсегда", "callback_data": "period_forever"}],
                        [{"text": "🔙 Назад", "callback_data": "cancel_action"}]
                    ]}
                    update_message(chat_id, message_id, f"🎁 Выберите период подписки для @{target_username or target_id}:", reply_markup=keyboard)
                
                elif action == "revoke":
                    username = revoke_subscription(target_id, admin_name)
                    delete_message(chat_id, message_id)
                    send_message(chat_id, f"✅ Подписка у пользователя {username or target_id} отобрана", reply_markup=get_main_keyboard(is_admin))
                    del admin_actions[user_id]
                
                elif action == "freeze":
                    username = freeze_subscription(target_id, admin_name)
                    delete_message(chat_id, message_id)
                    send_message(chat_id, f"✅ Подписка пользователя {username or target_id} заморожена", reply_markup=get_main_keyboard(is_admin))
                    del admin_actions[user_id]
                
                elif action == "transfer":
                    admin_actions[user_id]["from_id"] = target_id
                    admin_actions[user_id]["from_username"] = target_username
                    admin_actions[user_id]["step"] = "wait_transfer_target"
                    update_message(chat_id, message_id, f"🤝 Хорошо, а теперь напишите @username или id пользователя, КОМУ передать подписку от @{target_username or target_id}:", parse_mode=None)
            
            return jsonify({"ok": True})

        # Выбор периода для выдачи
        if cb_data.startswith("period_"):
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_period":
                days_map = {"1hour": 1, "1day": 1, "7days": 7, "1month": 30, "6months": 180, "12months": 365, "forever": 9999}
                period_key = cb_data.replace("period_", "")
                days = days_map.get(period_key, 30)
                
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                target_username = action_data.get("target_username")
                
                grant_subscription(target_id, days, admin_name)
                
                delete_message(chat_id, message_id)
                send_message(chat_id, f"✅ Подписка выдана пользователю {target_username or target_id}", reply_markup=get_main_keyboard(is_admin))
                del admin_actions[user_id]
            
            return jsonify({"ok": True})

        # Отмена действия
        if cb_data == "cancel_action":
            if user_id in admin_actions:
                del admin_actions[user_id]
            delete_message(chat_id, message_id)
            send_message(chat_id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

    # Обработка текстовых сообщений для админ-действий (ввод username/id)
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        
        if user_id in admin_actions:
            action_data = admin_actions[user_id]
            step = action_data.get("step")
            
            target_id, target_username = resolve_target(text)
            
            if target_id is None:
                send_message(chat_id, "❌ Не удалось найти пользователя.\n⚠️ Пожалуйста, используйте формат @username или id (пример id: 123456789)")
                return jsonify({"ok": True})
            
            if step == "wait_target":
                admin_actions[user_id]["target_id"] = target_id
                admin_actions[user_id]["target_username"] = target_username
                admin_actions[user_id]["step"] = "wait_confirm"
                
                action = action_data.get("action")
                emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
                emoji = emojis.get(action, "⚠️")
                action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
                target_display = f"@{target_username}" if target_username else f"id: {target_id}"
                
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Да", "callback_data": f"confirm_{action}"}],
                        [{"text": "❌ Нет", "callback_data": "cancel_action"}]
                    ]
                }
                send_message(chat_id,
                    f"{emoji} {msg['from']['first_name']}, ты точно хочешь {action_names[action]} {target_display} подписку?",
                    reply_markup=keyboard)
            
            elif step == "wait_transfer_target":
                from_id = action_data.get("from_id")
                from_username = action_data.get("from_username")
                to_id = target_id
                to_username = target_username
                
                from_name, to_name = transfer_subscription(from_id, to_id, msg['from']['first_name'])
                
                if from_name:
                    send_message(chat_id, f"✅ Подписка передана от {from_name} к {to_name}")
                else:
                    send_message(chat_id, "❌ Не удалось передать подписку")
                
                delete_message(chat_id, None)
                send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(True))
                del admin_actions[user_id]

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "Бот работает!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
