import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
🏆 Bine ai venit la Star Alliance Bot!

🛡 Clan 1: #GC002L02
🛡 Clan 2: #GRC9VUG8
🛡 Clan 3: #J9QVU9J8

Comenzi:
/alliance
/clan1
/clan2
/clan3
/help
"""
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/alliance\n/clan1\n/clan2\n/clan3"
    )

async def alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """🏆 STAR ALLIANCE

🛡 Clan 1
#GC002L02

🛡 Clan 2
#GRC9VUG8

🛡 Clan 3
#J9QVU9J8"""
    )

async def clan1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Clan 1\nTag: #GC002L02"
    )

async def clan2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Clan 2\nTag: #GRC9VUG8"
    )

async def clan3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 Clan 3\nTag: #J9QVU9J8"
    )

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("alliance", alliance))
app.add_handler(CommandHandler("clan1", clan1))
app.add_handler(CommandHandler("clan2", clan2))
app.add_handler(CommandHandler("clan3", clan3))

print("Star Alliance Bot este online!")

app.run_polling()

