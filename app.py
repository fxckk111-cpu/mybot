import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import random
import string

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8118527645:AAEDYUiN4nNE9dCOMA3ozybMe1lvLCVr5xc"
RESELLER_LINK = "https://t.me/realsapphire"
PRIVACY_LINK = "https://telegra.ph/Politika-konfidencialnosti-04-01-26"
AGREEMENT_LINK = "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19"
SUPPORT_LINK = "https://t.me/realsapphire"

# База ключей
user_keys = {}

def generate_key():
	parts = []
	for i in range(10):
		parts.append(random.choice(string.ascii_lowercase))
		parts.append(random.choice(string.digits))
	return ''.join(parts)[:20]

# ========== ГЛАВНОЕ МЕНЮ ==========
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
	user_id = str(update.effective_user.id)

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
		keys = user_keys.get(user_id, [])
		if not keys:
			await update.message.reply_text("😔 Ключей нет.")
		else:
			msg = "🔑 <b>Ваши ключи:</b>\n\n" + "\n".join([f"<code>{k}</code>" for k in keys])
			await update.message.reply_text(msg, parse_mode="HTML")

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
		await query.message.reply_text("❌ Отменено", reply_markup=main_keyboard)
		return

	if data.startswith("price_"):
		_, days, price = data.split("_")
		context.user_data["selected_days"] = days
		context.user_data["selected_price"] = price

		keyboard = InlineKeyboardMarkup([
			[InlineKeyboardButton("🤝 Через реселлера (RUB)", url=RESELLER_LINK)],
			[InlineKeyboardButton("🔙 Назад", callback_data="back_to_tariffs")]
		])
		await query.edit_message_text(
			f"💳 <b>Подписка на {days} дней — {price} ₽</b>\n\n💰 Выберите способ оплаты:",
			parse_mode="HTML",
			reply_markup=keyboard
		)

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

# ========== АДМИНСКАЯ КОМАНДА ДЛЯ ВЫДАЧИ КЛЮЧЕЙ ==========
async def givekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = str(update.effective_user.id)
	
	# Только один админ — ты
	if user_id != "8915153014":
		await update.message.reply_text("❌ У вас нет прав для этой команды.")
		return
	
	try:
		args = context.args
		if len(args) < 2:
			await update.message.reply_text(
				"❌ Использование: /givekey @username дни\n"
				"Пример: /givekey @realsapphire 30"
			)
			return
		
		username = args[0]
		days = args[1]
		
		if username.startswith("@"):
			username = username[1:]
		
		try:
			chat = await context.bot.get_chat(f"@{username}")
			target_id = str(chat.id)
		except:
			await update.message.reply_text(f"❌ Не удалось найти пользователя @{username}")
			return
		
		key = generate_key()
		
		if target_id not in user_keys:
			user_keys[target_id] = []
		user_keys[target_id].append(f"{days} дней — {key}")
		
		await context.bot.send_message(
			chat_id=target_id,
			text=f"🎉 <b>Вам выдан ключ!</b>\n\n"
				 f"🔑 <code>{key}</code>\n"
				 f"📅 Период: {days} дней\n\n"
				 f"Ключ сохранён. Вы можете посмотреть его в разделе «🔑 Мои ключи».",
			parse_mode="HTML"
		)
		
		await update.message.reply_text(f"✅ Ключ выдан пользователю @{username} на {days} дней")
		
	except Exception as e:
		await update.message.reply_text(f"❌ Ошибка: {e}")

# ========== ЗАПУСК ==========
def main():
	app = Application.builder().token(BOT_TOKEN).build()
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler("givekey", givekey))
	app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
	app.add_handler(CallbackQueryHandler(button_handler))
	print("✅ VAMP BOT запущен и работает!")
	app.run_polling()

if __name__ == "__main__":
	main()
