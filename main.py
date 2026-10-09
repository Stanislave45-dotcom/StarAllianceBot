import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CR_API_TOKEN = os.getenv("CR_API_TOKEN")

MOLDOVA_LOCATION_ID = 57000039
API_BASE = "https://proxy.royaleapi.dev/v1"

headers = {
    "Authorization": f"Bearer {CR_API_TOKEN}"
}

ranking_url = (
    f"{API_BASE}/locations/"
    f"{MOLDOVA_LOCATION_ID}/rankings/clans?limit=100"
)

response = requests.get(
    ranking_url,
    headers=headers,
    timeout=30
)

print("Clash Royale status:", response.status_code)
print(response.text[:500])

if response.status_code == 200:
    data = response.json()
    clans = data.get("items", [])

    top_10 = clans[:10]

message = "🇲🇩 TOP 10 CLANURI MOLDOVA\n\n"

for clan in top_10:
    rank = clan["rank"]
    name = clan["name"]
    members = clan["memberCount"]

    message += f"#{rank} {name} ({members}/50)\n"

else:
    message = (
        "❌ Eroare Clash Royale API\n\n"
        f"Cod eroare: {response.status_code}\n"
        "Verifică CR_API_TOKEN și IP-ul cheii."
    )

telegram_url = (
    f"https://api.telegram.org/"
    f"bot{BOT_TOKEN}/sendMessage"
)

telegram_response = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)

print("Telegram status:", telegram_response.status_code)
print(telegram_response.text)
