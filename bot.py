import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")

user_keys = {}
user_selected_plan = {}

PRICES = {
    "7_days": 250,
    "30_days": 500,
    "60_days": 1000
}
PRICE_NAMES = {
    "7_days": "7",
    "30_days": "30",
    "60_days": "60"
}

def get_usdt_rate():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub")
        data = response.json()
        return data["tether"]["rub"]
    except:
        return 96.0

SUPPORT_LINK = "https://t.me/pwnmeifucan"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"

# ========== ГЛАВНОЕ МЕНЮ ==========
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("⚡ Купить подписку")],
        [KeyboardButton("🔑 Мои ключи")],
        [KeyboardButton("ℹ️ Info")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ========== КОМАНДА /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👾 Привет, <b>{user.first_name}</b>!",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ КОМАНД ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    if text == "⚡ Купить подписку":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 дней — 250₽", callback_data="price_7_days")],
            [InlineKeyboardButton("📅 30 дней — 500₽", callback_data="price_30_days")],
            [InlineKeyboardButton("📅 60 дней — 1000₽", callback_data="price_60_days")]
        ])
        await update.message.reply_text(
            "⚡️ Выберите тариф:",
            reply_markup=keyboard
        )

    elif text == "🔑 Мои ключи":
        keys = user_keys.get(user_id, [])
        if not keys:
            await update.message.reply_text("😔 Ключей нет.")
        else:
            msg = "Ваши ключи:\n" + "\n".join(keys)
            await update.message.reply_text(msg)

    elif text == "ℹ️ Info":
        info_text = (
            "<b>📋 Информация</b>\n\n"
            f'📄 <a href="{PRIVACY_LINK}">Политика конфиденциальности</a>\n'
            f'📄 <a href="{AGREEMENT_LINK}">Пользовательское соглашение</a>\n\n'
            f'🆘 <a href="{SUPPORT_LINK}">Поддержка</a>'
        )
        await update.message.reply_text(
            info_text,
            parse_mode="HTML",
            disable_web_page_preview=True,  # Убирает превью ссылок
            reply_markup=main_keyboard
        )

# ========== INLINE КНОПКИ ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)

    if data.startswith("price_"):
        plan_key = data.split("_")[1] + "_" + data.split("_")[2]
        price = PRICES.get(plan_key, 0)
        days = PRICE_NAMES.get(plan_key, "0")
        user_selected_plan[user_id] = (days, price)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Через реселлера (RUB)", url=SUPPORT_LINK)],  # Теперь просто ссылка
            [InlineKeyboardButton("💎 CryptoBot (авто)", callback_data="pay_crypto")]
        ])
        await query.edit_message_text(
            f"💳 Подписка на период {days} дней — {price}₽\n\nВыберите способ оплаты:",
            reply_markup=keyboard
        )

    elif data == "pay_crypto":
        days, price = user_selected_plan.get(user_id, ("0", 0))
        rate = get_usdt_rate()
        usdt_amount = round(price / rate, 2)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Оплатить в CryptoBot", url="https://t.me/CryptoBot")],
            [InlineKeyboardButton("✅ Я оплатил", callback_data="payment_done")]
        ])
        await query.edit_message_text(
            f"💎 {usdt_amount} USDT (~{price} ₽) · {days} дн.\n\n"
            f"Оплатите в CryptoBot и вернитесь.",
            reply_markup=keyboard
        )

    elif data == "payment_done":
        await query.edit_message_text(
            "Soon\n\n"
            "bot py pidor_19"
        )

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Бот запущен и работает!")
    app.run_polling()

if __name__ == "__main__":
    main()
