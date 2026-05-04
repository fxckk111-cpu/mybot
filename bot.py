import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os

TOKEN = os.getenv("BOT_TOKEN")

user_keys = {}
user_selected_plan = {}

PRICES = {
    "week": 200,
    "month": 500,
    "half_year": 1000
}
PRICE_NAMES = {
    "week": "week",
    "month": "month",
    "half_year": "half a year"
}

RUB_LINK = "https://t.me/m/1wZevkoDYWQ1"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
SUPPORT_LINK = "https://t.me/pwnmeifucan"

# ========== ГЛАВНОЕ МЕНЮ (Reply Keyboard) ==========
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("1. buy a subscription")],
        [KeyboardButton("2. my keys")],
        [KeyboardButton("3. information")]
    ],
    resize_keyboard=True,  # Подгон размер кнопок
    one_time_keyboard=False  # Кнопки остаются после нажатия
)

# ========== КОМАНДА /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"hello, {user.first_name}!",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ КОМАНД ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)

    if text == "1. buy a subscription":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("week - 200₽", callback_data="price_week")],
            [InlineKeyboardButton("month - 500₽", callback_data="price_month")],
            [InlineKeyboardButton("half a year - 1000₽", callback_data="price_half_year")]
        ])
        await update.message.reply_text(
            "choose a pricing plan:",
            reply_markup=keyboard
        )

    elif text == "2. my keys":
        keys = user_keys.get(user_id, [])
        if not keys:
            await update.message.reply_text("there are no keys :(")
        else:
            msg = "Ваши ключи:\n" + "\n".join(keys)
            await update.message.reply_text(msg)

    elif text == "3. information":
        info_text = (
            "information\n\n"
            f'<a href="{PRIVACY_LINK}">privacy policy</a>\n'
            f'<a href="{AGREEMENT_LINK}">user agreement</a>\n'
            f'<a href="{SUPPORT_LINK}">support</a>'
        )
        await update.message.reply_text(
            info_text,
            parse_mode="HTML",
            reply_markup=main_keyboard
        )

# ========== INLINE КНОПКИ (для выбора тарифа и оплаты) ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)

    if data.startswith("price_"):
        plan = data.split("_")[1]
        price = PRICES.get(plan, 0)
        plan_name = PRICE_NAMES.get(plan, plan)
        user_selected_plan[user_id] = (plan_name, price)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("RUB", callback_data="pay_rub")],
            [InlineKeyboardButton("CryptoBot", callback_data="pay_crypto")]
        ])
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\nchoose a payment method:",
            reply_markup=keyboard
        )

    elif data == "pay_rub":
        plan_name, price = user_selected_plan.get(user_id, ("", 0))
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\n"
            f"Оплата по ссылке: {RUB_LINK}\n"
            f"После оплаты напишите @pwnmeifucan для получения ключа."
        )

    elif data == "pay_crypto":
        plan_name, price = user_selected_plan.get(user_id, ("", 0))
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\n"
            f"Оплатите через @CryptoBot\n"
            f"После оплаты напишите @pwnmeifucan с чеком."
        )

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен с клавиатурой!")
    app.run_polling()

if __name__ == "__main__":
    main()
