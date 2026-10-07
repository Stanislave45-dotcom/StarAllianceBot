from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 Bine ai venit la Star Alliance Bot!\n\n"
        "Clan 1: #GC002L02\n"
        "Clan 2: #GRC9VUG8\n"
        "Clan 3: #J9QVU9J8"
    )

async def alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 STAR ALLIANCE\n\n"
        "🛡 Clan 1: #GC002L02\n"
        "🛡 Clan 2: #GRC9VUG8\n"
        "🛡 Clan 3: #J9QVU9J8"
    )

app = Application.builder().token("8961688347:AAE2T3Rg_QK5kKEMEPShObq4hzytg-1sOp4").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("alliance", alliance))

app.run_polling()

