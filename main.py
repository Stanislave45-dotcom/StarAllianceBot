import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CR_API_TOKEN = os.getenv("CR_API_TOKEN")

headers = {
    "Authorization": f"Bearer {CR_API_TOKEN}"
}

response = requests.get(
    "https://proxy.royaleapi.dev/v1/locations",
    headers=headers,
    timeout=30
)

message = "Moldova nu a fost găsită."

if response.status_code == 200:
    data = response.json()

    for location in data.get("items", []):
        if "mold" in location["name"].lower():
            message = (
                f"🇲🇩 Moldova găsită\n\n"
                f"Nume: {location['name']}\n"
                f"ID: {location['id']}\n"
                f"Țară: {location['countryCode']}"
            )
            break

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)
