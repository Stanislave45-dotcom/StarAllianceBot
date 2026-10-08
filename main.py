import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CR_API_KEY = os.getenv("CLASH_ROYALE_API_KEY")
headers = {
    "Authorization": f"Bearer {CR_API_KEY}"
}
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

🛡 StarAlliance MD
#GC002L02

🛡 StarAcademy MD
#GRC9VUG8

🛡 StarAlliance AX
#J9QVU9J8"""
    )

async def clan1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 StarAllianc MD\nTag: #GC002L02"
    )

async def clan2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 StarAcademy MD\nTag: #GRC9VUG8"
    )

async def clan3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 StarAlliance AX\nTag: #J9QVU9J8"
    )
async def clan1(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tag = "%23GC002L02"

    response = requests.get(
        f"https://api.clashroyale.com/v1/clans/{tag}",
        headers=headers
    )

if response.status_code != 200:
    await update.message.reply_text(
        f"❌ API Error\n"
        f"Status: {response.status_code}\n"
        f"Răspuns: {response.text}"
    )
    return

    clan = response.json()

    text = (
        f"🏆 {clan['name']}\n\n"
        f"👥 Membri: {clan['members']}/50\n"
        f"🏅 Trofee: {clan['clanScore']}\n"
        f"📈 Necesar: {clan['requiredTrophies']}"
    )

    await update.message.reply_text(text)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("alliance", alliance))
app.add_handler(CommandHandler("clan1", clan1))
app.add_handler(CommandHandler("clan2", clan2))
app.add_handler(CommandHandler("clan3", clan3))
app.add_handler(CommandHandler("clan1", clan1))

print("Star Alliance Bot este online!")

app.run_polling()

