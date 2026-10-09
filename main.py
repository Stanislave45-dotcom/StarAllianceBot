import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "ID_CANAL"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": "✅ StarAllianceBot este online!"
    }
)
