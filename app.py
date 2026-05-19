import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8687695414:AAFX_eG3x05gQXahtMogvAh2JYfQuiwyWCM"
RESELLER_LINK = "https://t.me/realsapphire"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
SUPPORT_LINK = "https://t.me/realsapphire"

# ========== ГЛАВНОЕ МЕНЮ (Reply Keyboard) ==========
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
        f"👋 Привет, <b>{user.first_name}</b>!",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ КОМАНД ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🛒 Купить подписку":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 дней — 100₽", callback_data="price_7_100")],
            [InlineKeyboardButton("📅 30 дней — 250₽", callback_data="price_30_250")],
            [InlineKeyboardButton("📅 60 дней — 500₽", callback_data="price_60_500")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
        await update.message.reply_text(
            "⌛️ Выберите тариф:",
            reply_markup=keyboard
        )

    elif text == "🔑 Мои ключи":
        await update.message.reply_text("😔 Ключей нет.")

    elif text == "ℹ️ Информация":
        info_text = (
            "<b>📋 Информация</b>\n\n"
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

    if data == "cancel":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await query.message.reply_text("❌ Отменено")
        return

    if data.startswith("price_"):
        _, days, price = data.split("_")
        context.user_data["selected_days"] = days
        context.user_data["selected_price"] = price

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Через реселлера (RUB)", url=RESELLER_LINK)],
            [InlineKeyboardButton("💎 CryptoBot", callback_data="crypto_pay")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_tariffs")]
        ])
        await query.edit_message_text(
            f"👾 <b>Подписка на {days} дней — {price} ₽</b>\n\n💰 Выберите способ оплаты:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    elif data == "crypto_pay":
        days = context.user_data.get("selected_days")
        price = context.user_data.get("selected_price")
        await query.edit_message_text(
            f"💎 Оплата через CryptoBot\n\n💳 {days} дней — {price} ₽\n\nСейчас здесь будет ссылка на оплату. Скоро добавим.",
            parse_mode="HTML"
        )
        # TODO: позже добавим создание инвойса через CryptoBot

    elif data == "back_to_tariffs":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 дней — 100₽", callback_data="price_7_100")],
            [InlineKeyboardButton("📅 30 дней — 250₽", callback_data="price_30_250")],
            [InlineKeyboardButton("📅 60 дней — 500₽", callback_data="price_60_500")],
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
