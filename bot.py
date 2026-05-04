import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("BOT_TOKEN")

# База ключей (в памяти, для теста)
user_keys = {}

# Цены и названия тарифов
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

# Ссылки
RUB_LINK = "https://t.me/m/1wZevkoDYWQ1"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
SUPPORT_LINK = "https://t.me/pwnmeifucan"

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("1. buy a subscription", callback_data="buy")],
        [InlineKeyboardButton("2. my keys", callback_data="my_keys")],
        [InlineKeyboardButton("3. information", callback_data="info")]
    ]
    await update.message.reply_text(
        f"hello, {user.first_name}!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ===== 1. BUY =====
    if data == "buy":
        keyboard = [
            [InlineKeyboardButton("week - 200₽", callback_data="price_week")],
            [InlineKeyboardButton("month - 500₽", callback_data="price_month")],
            [InlineKeyboardButton("half a year - 1000₽", callback_data="price_half_year")]
        ]
        await query.edit_message_text(
            "choose a pricing plan:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== ВЫБОР ТАРИФА =====
    elif data.startswith("price_"):
        plan = data.split("_")[1]
        price = PRICES.get(plan, 0)
        plan_name = PRICE_NAMES.get(plan, plan)
        
        # Сохраняем выбранный план во временные данные
        context.user_data["selected_plan"] = plan
        context.user_data["selected_price"] = price
        context.user_data["selected_plan_name"] = plan_name
        
        keyboard = [
            [InlineKeyboardButton("RUB", callback_data="pay_rub")],
            [InlineKeyboardButton("CryptoBot", callback_data="pay_crypto")]
        ]
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\nchoose a payment method:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== RUB =====
    elif data == "pay_rub":
        plan_name = context.user_data.get("selected_plan_name", "")
        price = context.user_data.get("selected_price", 0)
        # Здесь можно добавить логику выдачи ключа после оплаты
        # Для теста выдадим ключ вручную
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\n"
            f"Оплата по ссылке: {RUB_LINK}\n"
            f"После оплаты напишите @pwnmeifucan для получения ключа."
        )

    # ===== CRYPTOBOT =====
    elif data == "pay_crypto":
        plan_name = context.user_data.get("selected_plan_name", "")
        price = context.user_data.get("selected_price", 0)
        await query.edit_message_text(
            f"subscribe to «{plan_name}» — {price}₽\n\n"
            f"Оплатите через @CryptoBot\n"
            f"После оплаты напишите @pwnmeifucan с чеком."
        )

    # ===== 2. MY KEYS =====
    elif data == "my_keys":
        user_id = str(update.effective_user.id)
        keys = user_keys.get(user_id, [])
        if not keys:
            await query.edit_message_text("there are no keys :(")
        else:
            msg = "Ваши ключи:\n" + "\n".join(keys)
            await query.edit_message_text(msg)

    # ===== 3. INFORMATION =====
    elif data == "info":
        # Формируем текст с кликабельными ссылками
        info_text = (
            "information\n\n"
            f'<a href="{PRIVACY_LINK}">privacy policy</a>\n'
            f'<a href="{AGREEMENT_LINK}">user agreement</a>\n'
            f'<a href="{SUPPORT_LINK}">support</a>'
        )
        await query.edit_message_text(
            info_text,
            parse_mode="HTML"
        )

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен и работает!")
    app.run_polling()

if __name__ == "__main__":
    main()
