import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("1. buy a subscription", callback_data="buy")],
        [InlineKeyboardButton("2. my keys", callback_data="my_keys")],
        [InlineKeyboardButton("3. information", callback_data="info")]
    ]
    await update.message.reply_text(f"hello, {user.first_name}!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "buy":
        keyboard = [
            [InlineKeyboardButton("week - 200₽", callback_data="price_week")],
            [InlineKeyboardButton("month - 500₽", callback_data="price_month")],
            [InlineKeyboardButton("half a year - 1000₽", callback_data="price_half_year")]
        ]
        await query.edit_message_text("choose a pricing plan:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "price_week":
        context.user_data["plan"] = "week"
        context.user_data["price"] = 200
        await show_payment(query, "week", 200)
    elif data == "price_month":
        context.user_data["plan"] = "month"
        context.user_data["price"] = 500
        await show_payment(query, "month", 500)
    elif data == "price_half_year":
        context.user_data["plan"] = "half_year"
        context.user_data["price"] = 1000
        await show_payment(query, "half a year", 1000)

    elif data == "pay_rub":
        plan = context.user_data.get("plan", "")
        price = context.user_data.get("price", 0)
        await query.edit_message_text(f"subscribe to «{plan}» — {price}₽\n\nОплата по ссылке: https://t.me/m/1wZevkoDYWQ1\n\nПосле оплаты напишите @pwnmeifucan для получения ключа.")

    elif data == "pay_crypto":
        plan = context.user_data.get("plan", "")
        price = context.user_data.get("price", 0)
        await query.edit_message_text(f"subscribe to «{plan}» — {price}₽\n\nОплатите через @CryptoBot\nПосле оплаты напишите @pwnmeifucan с чеком.")

    elif data == "my_keys":
        await query.edit_message_text("there are no keys :(")

    elif data == "info":
        keyboard = [
            [InlineKeyboardButton("privacy policy", url="https://telegra.ph/Politika-konfidencialnosti-04-01-26")],
            [InlineKeyboardButton("user agreement", url="https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19")],
            [InlineKeyboardButton("support", url="https://t.me/pwnmeifucan")]
        ]
        await query.edit_message_text("information", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_payment(query, plan, price):
    keyboard = [
        [InlineKeyboardButton("RUB", callback_data="pay_rub")],
        [InlineKeyboardButton("CryptoBot", callback_data="pay_crypto")]
    ]
    await query.edit_message_text(f"subscribe to «{plan}» — {price}₽\n\nchoose a payment method:", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
