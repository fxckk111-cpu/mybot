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

# ID админов
ADMIN_IDS = ["8095717532", "522044023"]

# Ссылки
RESELLER_LINK = "https://t.me/realsapphire"
SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

CRYPTO_API_URL = "https://pay.crypt.bot/api/"
app = Flask(__name__)

users_db = {}
admin_actions = {}
next_uid = 2

# Вечные подписки для админов (загружаются в users_db при старте)
ADMIN_KEYS = {
    "522044023": gen_key() if 'gen_key' in dir() else "admin_key_0",
    "8095717532": gen_key() if 'gen_key' in dir() else "admin_key_1"
}

def gen_key():
    parts = []
    for i in range(10):
        parts.append(random.choice(string.ascii_lowercase))
        parts.append(random.choice(string.digits))
    return ''.join(parts)[:20]

def resolve_target(input_text, bot_token):
    """Определяет user_id по @username или id"""
    if input_text.startswith("@"):
        username = input_text[1:]
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        try:
            r = requests.get(url, params={"chat_id": input_text})
            data = r.json()
            if data.get("ok"):
                return data["result"]["id"], username
        except:
            pass
        return None, None
    elif input_text.isdigit():
        return int(input_text), None
    return None, None

def get_user_info(user_id, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getChat"
    try:
        r = requests.get(url, params={"chat_id": user_id})
        data = r.json()
        if data.get("ok"):
            return data["result"].get("username"), data["result"].get("first_name")
    except:
        pass
    return None, None

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
    """Инициализирует вечные подписки для админов"""
    for admin_id in ADMIN_IDS:
        if admin_id not in users_db:
            users_db[admin_id] = {
                "uid": admin_id[-4:],
                "key": ADMIN_KEYS.get(admin_id, gen_key()),
                "expire": 9999999999,
                "subscription_name": "вечная",
                "days": 9999,
                "step": "done"
            }

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

# ========== ОСНОВНОЙ ВЕБХУК ==========
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    global next_uid
    data = request.get_json()
    if not data:
        return jsonify({"ok": False}), 400

    # Инициализация админов при первом запуске
    init_admin_subscriptions()

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        is_admin = user_id in ADMIN_IDS

        if text == "/start":
            # Создаём новый uid для нового пользователя (если его нет)
            if user_id not in users_db and not is_admin:
                users_db[user_id] = {"uid": next_uid, "step": "new"}
                next_uid += 1
            send_message(chat_id, f"👾 Привет, <b>{msg['from']['first_name']}</b>!", 
                        parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))

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
            send_message(chat_id, f"👋 Привет, <b>{msg['from']['first_name']}</b>!\n😂 Что хочешь сделать?", 
                        parse_mode="HTML", reply_markup=keyboard)

        elif text == "⚡ Купить чит" and not is_admin:
            send_tariffs(chat_id)

        elif text == "🔑 Мои ключи":
            sub_info = get_user_subscription_info(user_id)
            if not sub_info:
                send_message(chat_id, "😔 Ключей нет.")
            else:
                if sub_info.get("expire", 0) >= 999999999:
                    expire_str = "никогда"
                else:
                    expire_str = datetime.fromtimestamp(sub_info["expire"]).strftime("%d.%m.%Y")
                msg_text = (
                    f"👾 <b>{sub_info['uid']}</b>\n"
                    f"🔑 <b>Ключ:</b> <code>{sub_info['key']}</code>\n"
                    f"⏳ <i>Ключ истекает: {expire_str}</i>"
                )
                if "invite_link" in sub_info and sub_info.get("invite_link"):
                    msg_text += f"\n\n🔗 <a href='{sub_info['invite_link']}'>Ссылка в группу с покупателями</a>"
                send_message(chat_id, msg_text, parse_mode="HTML")

        elif text == "ℹ️ Информация" and not is_admin:
            info = f"<b>📋 Информация</b>\n\n📄 <a href='{PRIVACY_LINK}'>Политика конфиденциальности</a>\n📄 <a href='{AGREEMENT_LINK}'>Пользовательское соглашение</a>\n\n🆘 <a href='{SUPPORT_LINK}'>Поддержка</a>"
            send_message(chat_id, info, parse_mode="HTML", disable_web_page_preview=True)

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        user_id = str(cb["from"]["id"])
        cb_data = cb["data"]
        is_admin = user_id in ADMIN_IDS

        # Назад в меню
        if cb_data == "back_to_menu":
            delete_message(chat_id, message_id)
            send_message(chat_id, f"👾 Привет, <b>{cb['from']['first_name']}</b>!", parse_mode="HTML", reply_markup=get_main_keyboard(is_admin))
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
                update_message(chat_id, message_id, "❌ Нет активного счета. Начните новую покупку.")
                return

            invoice_id = users_db[user_id]["invoice_id"]
            try:
                inv = crypto_api("getInvoices", {"invoice_ids": [invoice_id]})
                if inv["items"][0]["status"] == "paid":
                    uid = users_db[user_id].get("uid") if "uid" in users_db[user_id] else next_uid
                    if uid == next_uid:
                        next_uid += 1
                    key = gen_key()
                    expire = int((datetime.now() + timedelta(days=days)).timestamp())
                    invite_link = create_invite_link(GROUP_ID, user_id, days)
                    users_db[user_id] = {
                        "uid": uid,
                        "key": key,
                        "expire": expire,
                        "subscription_name": f"{days} дней",
                        "days": days,
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
                    update_message(chat_id, message_id, "⏳ Платёж ещё не подтверждён. Попробуйте позже.", 
                                 reply_markup={"inline_keyboard": [[{"text": "🔙 Назад", "callback_data": "back_to_plans"}]]})
            except Exception as e:
                update_message(chat_id, message_id, f"❌ Ошибка проверки: {e}")
            return jsonify({"ok": True})

        # Админ-панель
        if cb_data.startswith("admin_"):
            if not is_admin:
                return jsonify({"ok": True})
            
            action = cb_data.replace("admin_", "")
            admin_actions[user_id] = {"action": action, "step": "wait_target"}
            
            emojis = {"revoke": "😒", "transfer": "🤝", "freeze": "❄", "grant": "🎁"}
            emoji = emojis.get(action, "⚠️")
            action_names = {"revoke": "забрать", "transfer": "передать", "freeze": "заморозить", "grant": "выдать"}
            
            update_message(chat_id, message_id,
                f"{emoji} Хорошо, <b>{cb['from']['first_name']}</b>! {action_names[action]} так {action_names[action]}!\n"
                f"Напишите @username или id пользователя, которому нужно {action_names[action]}.\n"
                f"⚠️ Пожалуйста, используйте формат @username или id (пример id: 123456789)",
                parse_mode="HTML")
            return jsonify({"ok": True})

        # Подтверждение действия админа
        if cb_data.startswith("confirm_"):
            action = cb_data.replace("confirm_", "")
            
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_confirm":
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                target_username = action_data.get("target_username")
                admin_name = cb['from']['first_name']
                
                if action == "grant":
                    # Для выдачи подписки показываем выбор периода
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
                    update_message(chat_id, message_id, f"{action_data.get('emoji', '🎁')} Выберите период подписки для @{target_username or target_id}:", reply_markup=keyboard)
                    return jsonify({"ok": True})
                else:
                    # revoke, freeze, transfer
                    if action == "revoke":
                        if str(target_id) in users_db and "key" in users_db[str(target_id)]:
                            sub_name = users_db[str(target_id)].get("subscription_name", "подписка")
                            key = users_db[str(target_id)]["key"]
                            del users_db[str(target_id)]
                            kick_from_group(GROUP_ID, target_id)
                            send_message(target_id, f"😒 <b>{target_username or target_id}</b>, у тебя <b>{admin_name}</b> забрал {sub_name} и твой ключ: <code>{key}</code> больше не доступен", parse_mode="HTML")
                            send_message(chat_id, f"✅ Подписка у пользователя {target_username or target_id} отобрана")
                        else:
                            send_message(chat_id, f"❌ У пользователя {target_username or target_id} нет активной подписки")
                    
                    elif action == "freeze":
                        if str(target_id) in users_db and "key" in users_db[str(target_id)]:
                            sub_name = users_db[str(target_id)].get("subscription_name", "подписка")
                            users_db[str(target_id)]["frozen"] = True
                            users_db[str(target_id)]["old_expire"] = users_db[str(target_id)]["expire"]
                            send_message(target_id, f"❄ <b>{target_username or target_id}</b>, твоя подписка на {sub_name} была заморожена админом <b>{admin_name}</b>.", parse_mode="HTML")
                            send_message(chat_id, f"✅ Подписка пользователя {target_username or target_id} заморожена")
                        else:
                            send_message(chat_id, f"❌ У пользователя {target_username or target_id} нет активной подписки")
                    
                    elif action == "transfer":
                        # Сохраняем для следующего шага
                        admin_actions[user_id]["from_id"] = target_id
                        admin_actions[user_id]["from_username"] = target_username
                        admin_actions[user_id]["step"] = "wait_transfer_target"
                        update_message(chat_id, message_id, f"🤝 Хорошо, а теперь напишите @username или id пользователя, КОМУ передать подписку от @{target_username or target_id}:", parse_mode="HTML")
                        return jsonify({"ok": True})
                    
                    delete_message(chat_id, message_id)
                    send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(is_admin))
                    del admin_actions[user_id]
            return jsonify({"ok": True})

        # Выбор периода для выдачи
        if cb_data.startswith("period_"):
            if user_id in admin_actions and admin_actions[user_id].get("step") == "wait_period":
                days_map = {"1hour": 1/24, "1day": 1, "7days": 7, "1month": 30, "6months": 180, "12months": 365, "forever": 9999}
                period_key = cb_data.replace("period_", "")
                days = days_map.get(period_key, 30)
                
                action_data = admin_actions[user_id]
                target_id = action_data.get("target_id")
                target_username = action_data.get("target_username")
                admin_name = cb['from']['first_name']
                
                sub_name = f"{days} дней" if days < 9999 else "навсегда"
                key = gen_key()
                uid = next_uid
                next_uid += 1
                expire = int((datetime.now() + timedelta(days=days)).timestamp()) if days < 9999 else 9999999999
                invite_link = create_invite_link(GROUP_ID, target_id, days if days < 9999 else 365)
                
                users_db[str(target_id)] = {
                    "uid": uid,
                    "key": key,
                    "expire": expire,
                    "subscription_name": sub_name,
                    "days": days if days < 9999 else 9999,
                    "invite_link": invite_link,
                    "step": "done"
                }
                
                expire_str = datetime.fromtimestamp(expire).strftime("%d.%m.%Y") if days < 9999 else "никогда"
                send_message(target_id,
                    f"🎉 <b>{target_username or target_id}</b>, поздравляю! Тебе <b>{admin_name}</b> выдал подписку на {sub_name}\n\n"
                    f"👾 <b>{uid}</b>\n"
                    f"🔑 <b>Ключ:</b> <code>{key}</code>\n"
                    f"⏳ <i>Ключ истекает: {expire_str}</i>\n\n"
                    f"🔗 <a href='{invite_link}'>Ссылка в группу с покупателями</a>",
                    parse_mode="HTML")
                
                delete_message(chat_id, message_id)
                send_message(chat_id, f"✅ Подписка на {sub_name} выдана пользователю {target_username or target_id}", reply_markup=get_main_keyboard(is_admin))
                del admin_actions[user_id]
            return jsonify({"ok": True})

        # Отмена действия
        if cb_data == "cancel_action":
            if user_id in admin_actions:
                del admin_actions[user_id]
            delete_message(chat_id, message_id)
            send_message(chat_id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))
            return jsonify({"ok": True})

    # Обработка текстовых сообщений для админ-действий
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(chat_id)
        text = msg.get("text", "")
        
        if user_id in admin_actions:
            action_data = admin_actions[user_id]
            step = action_data.get("step")
            
            target_id, target_username = resolve_target(text, BOT_TOKEN)
            
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
                    f"{emoji} <b>{msg['from']['first_name']}</b>, ты точно хочешь {action_names[action]} {target_display} подписку?",
                    parse_mode="HTML", reply_markup=keyboard)
            
            elif step == "wait_transfer_target":
                # Передача подписки
                from_id = action_data.get("from_id")
                from_username = action_data.get("from_username")
                to_id = target_id
                to_username = target_username
                
                if str(from_id) in users_db and "key" in users_db[str(from_id)]:
                    user_data = users_db[str(from_id)].copy()
                    users_db[str(to_id)] = user_data
                    del users_db[str(from_id)]
                    new_link = create_invite_link(GROUP_ID, to_id, user_data.get("days", 30))
                    if new_link:
                        users_db[str(to_id)]["invite_link"] = new_link
                    
                    send_message(from_id, f"🤝 <b>{from_username or from_id}</b> твоя подписка была передана админом <b>{msg['from']['first_name']}</b>: @{to_username or to_id}", parse_mode="HTML")
                    send_message(chat_id, f"✅ Подписка передана от {from_username or from_id} к {to_username or to_id}")
                else:
                    send_message(chat_id, "❌ Не удалось передать подписку")
                
                delete_message(chat_id, None)  # Не удаляем, так как это новое сообщение
                send_message(chat_id, "✅ Готово!", reply_markup=get_main_keyboard(True))
                del admin_actions[user_id]

    return jsonify({"ok": True})

@app.route("/")
def health():
    return "Бот работает!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
