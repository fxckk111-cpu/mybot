import logging
import requests
import json
import random
import string
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8118527645:AAEDYUiN4nNE9dCOMA3ozybMe1lvLCVr5xc"
CRYPTOBOT_TOKEN = "579104:AARyyU3ZKIVsb3hgHxYWnMYyVnQhzNASc71"  # Твой токен от @CryptoBot
RESELLER_LINK = "https://t.me/realsapphire"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
SUPPORT_LINK = "https://t.me/realsapphire"

# База ключей (в памяти, для теста)
user_keys = {}
pending_payments = {}

# Цены и названия тарифов
PRICES = {
    "7": 100,
    "30": 250,
    "60": 500
}

CRYPTO_API_URL = "https://pay.crypt.bot/api/"

# ========== ФУНКЦИИ ДЛЯ CRYPTOBOT ==========
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

def generate_key():
    """Генерирует случайный ключ формата a1b23c4d5e6f7g8h9i0"""
    parts = []
    for i in range(10):
        parts.append(random.choice(string.ascii_lowercase))
        parts.append(random.choice(string.digits))
    return ''.join(parts)[:20]

# ========== КЛАВИАТУРЫ ==========
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛒 Купить подписку")],
        [KeyboardButton("🔑 Мои ключи")],
        [KeyboardButton("ℹ️ Информация")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ========== КОМАНДА /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"💎 <b>VAMP CHEAT</b> — лучший чит для Blockpost Mobile\n"
        f"✅ Без банов\n"
        f"⚡️ Аим, Aнти-аим, ESP, Чеймсы, Скины и многое другое",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ КОМАНД ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    if text == "🛒 Купить подписку":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 дней — 100₽", callback_data="price_7")],
            [InlineKeyboardButton("📅 30 дней — 250₽", callback_data="price_30")],
            [InlineKeyboardButton("📅 60 дней — 500₽", callback_data="price_60")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
        await update.message.reply_text(
            "⌛️ Выберите тариф:",
            reply_markup=keyboard
        )

    elif text == "🔑 Мои ключи":
        keys = user_keys.get(user_id, [])
        if not keys:
            await update.message.reply_text("😔 У вас нет ключей.\n\nКупить подписку: 🛒 Купить подписку")
        else:
            msg = "🔑 <b>Ваши ключи:</b>\n\n" + "\n".join([f"<code>{k}</code>" for k in keys])
            await update.message.reply_text(msg, parse_mode="HTML")

    elif text == "ℹ️ Информация":
        info_text = (
            "<b>📋 VAMP CHEAT</b>\n\n"
            f'📄 <a href="{PRIVACY_LINK}">Политика конфиденциальности</a>\n'
            f'📄 <a href="{AGREEMENT_LINK}">Пользовательское соглашение</a>\n\n'
            f'🆘 <a href="{SUPPORT_LINK}">Поддержка</a>'
        )
        await update.message.reply_text(
            info_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard
        )

# ========== INLINE КНОПКИ ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    user_id = str(update.effective_user.id)

    if data == "cancel":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await query.message.reply_text("❌ Отменено", reply_markup=main_keyboard)
        return

    if data.startswith("price_"):
        days = data.replace("price_", "")
        price = PRICES.get(days, 0)
        context.user_data["selected_days"] = days
        context.user_data["selected_price"] = price

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Через реселлера (RUB)", url=RESELLER_LINK)],
            [InlineKeyboardButton("💎 CryptoBot (авто)", callback_data="crypto_pay")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_tariffs")]
        ])
        await query.edit_message_text(
            f"💳 <b>Подписка на {days} дней — {price} ₽</b>\n\n💰 Выберите способ оплаты:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif data == "crypto_pay":
        days = context.user_data.get("selected_days", "7")
        price = int(context.user_data.get("selected_price", 100))
        
        rate = get_usdt_rate()
        amount = round(price / rate, 2)
        
        try:
            invoice = crypto_api("createInvoice", {
                "asset": "USDT",
                "amount": str(amount),
                "description": f"VAMP CHEAT — {days} дней"
            })
            
            pending_payments[user_id] = {
                "invoice_id": invoice["invoice_id"],
                "days": days,
                "price": price
            }
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Оплатить в CryptoBot", url=invoice["bot_invoice_url"])],
                [InlineKeyboardButton("✅ Я оплатил", callback_data="check_payment")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_tariffs")]
            ])
            await query.edit_message_text(
                f"💎 <b>Счёт на оплату</b>\n\n"
                f"💰 Сумма: <b>{amount} USDT (~{price} ₽)</b>\n"
                f"📅 Период: <b>{days} дней</b>\n\n"
                f"1️⃣ Нажмите «Оплатить в CryptoBot»\n"
                f"2️⃣ Оплатите счёт\n"
                f"3️⃣ Нажмите «Я оплатил»\n\n"
                f"⚡️ После оплаты вы получите ключ активации",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}\nОбратитесь к @realsapphire")

    elif data == "check_payment":
        payment = pending_payments.get(user_id)
        if not payment:
            await query.edit_message_text("❌ Нет активного платежа. Начните новую покупку.", reply_markup=main_keyboard)
            return
        
        try:
            invoices = crypto_api("getInvoices", {"invoice_ids": [payment["invoice_id"]]})
            if invoices and invoices[0]["status"] == "paid":
                key = generate_key()
                
                if user_id not in user_keys:
                    user_keys[user_id] = []
                user_keys[user_id].append(f"{payment['days']} дней — {payment['price']}₽: {key}")
                
                del pending_payments[user_id]
                
                await query.edit_message_text(
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"🎉 <b>Ваш ключ:</b>\n"
                    f"<code>{key}</code>\n\n"
                    f"📌 Сохраните его. Для активации введите ключ в нашем лаунчере.\n\n"
                    f"🔗 Скачать чит: https://t.me/realsapphire",
                    parse_mode="HTML"
                )
                await query.message.reply_text(
                    f"🔑 <b>Ваш ключ сохранён</b>\n\n"
                    f"Вы всегда можете посмотреть его в разделе «🔑 Мои ключи»",
                    parse_mode="HTML",
                    reply_markup=main_keyboard
                )
            else:
                await query.edit_message_text(
                    "⏳ <b>Платёж ещё не подтверждён</b>\n\n"
                    "Если вы уже оплатили, подождите 1-2 минуты и нажмите «Я оплатил» снова.\n"
                    "Если проблема сохраняется — обратитесь к @realsapphire",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Проверить ещё раз", callback_data="check_payment")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_tariffs")]
                    ])
                )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка проверки: {e}\nОбратитесь к @realsapphire")

    elif data == "back_to_tariffs":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 дней — 100₽", callback_data="price_7")],
            [InlineKeyboardButton("📅 30 дней — 250₽", callback_data="price_30")],
            [InlineKeyboardButton("📅 60 дней — 500₽", callback_data="price_60")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
        await query.edit_message_text(
            "⌛️ Выберите тариф:",
            reply_markup=keyboard
        )

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ VAMP BOT запущен и работает!")
    app.run_polling()

if __name__ == "__main__":
    main()
