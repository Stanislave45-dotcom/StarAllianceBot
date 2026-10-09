import json
import os
import time
from datetime import datetime
from urllib.parse import quote

import requests


# =========================
# VARIABILE RAILWAY
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CR_API_TOKEN = os.getenv("CR_API_TOKEN")


# =========================
# CONFIGURARE
# =========================

MOLDOVA_LOCATION_ID = 57000155
API_BASE = "https://proxy.royaleapi.dev/v1"

CHECK_INTERVAL = 300  # 300 secunde = 5 minute
STATE_FILE = "players.json"

HEADERS = {
    "Authorization": f"Bearer {CR_API_TOKEN}"
}


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    try:
        response = requests.post(
            telegram_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            },
            timeout=30
        )

        print(
            "Telegram:",
            response.status_code,
            response.text[:300]
        )

    except requests.RequestException as error:
        print("Eroare Telegram:", error)


# =========================
# CITIRE TOP 100 MOLDOVA
# =========================

def get_top_clans():
    url = (
        f"{API_BASE}/locations/"
        f"{MOLDOVA_LOCATION_ID}/rankings/clans"
        f"?limit=100"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        print(
            "Clasament Moldova:",
            response.status_code
        )

        if response.status_code != 200:
            print(response.text[:500])
            return None

        data = response.json()
        return data.get("items", [])

    except requests.RequestException as error:
        print("Eroare clasament:", error)
        return None


# =========================
# CITIRE MEMBRI CLAN
# =========================

def get_clan_members(clan_tag):
    encoded_tag = quote(clan_tag, safe="")

    url = f"{API_BASE}/clans/{encoded_tag}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            print(
                "Eroare clan:",
                clan_tag,
                response.status_code,
                response.text[:200]
            )
            return None

        return response.json()

    except requests.RequestException as error:
        print(
            "Eroare membri clan:",
            clan_tag,
            error
        )
        return None


# =========================
# SCANARE JUCATORI
# =========================

def scan_players():
    clans = get_top_clans()

    if clans is None:
        return None

    current_players = {}
    failed_clans = 0

    print("Clanuri găsite:", len(clans))

    for clan in clans:
        clan_tag = clan.get("tag")
        clan_name = clan.get("name", "Clan necunoscut")
        clan_rank = clan.get("rank", 0)

        if not clan_tag:
            continue

        clan_data = get_clan_members(clan_tag)

        if clan_data is None:
            failed_clans += 1
            continue

        members = clan_data.get("memberList", [])

        for member in members:
            player_tag = member.get("tag")

            if not player_tag:
                continue

            current_players[player_tag] = {
                "name": member.get(
                    "name",
                    "Jucător necunoscut"
                ),
                "tag": player_tag,
                "trophies": member.get("trophies", 0),
                "role": member.get(
                    "role",
                    "member"
                ),
                "clan_tag": clan_tag,
                "clan_name": clan_name,
                "clan_rank": clan_rank
            }

        time.sleep(0.15)

    print("Jucători găsiți:", len(current_players))
    print("Clanuri cu eroare:", failed_clans)

    # Evită notificările false dacă unele clanuri
    # nu au putut fi citite.
    if failed_clans > 0:
        print(
            "Scanarea este incompletă. "
            "Comparația a fost anulată."
        )
        return None

    return current_players


# =========================
# SALVARE SI CITIRE STARE
# =========================

def load_previous_players():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return None

        return data

    except (
        json.JSONDecodeError,
        OSError
    ) as error:
        print("Eroare citire stare:", error)
        return None


def save_players(players):
    try:
        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                players,
                file,
                ensure_ascii=False,
                indent=2
            )

        print("Starea a fost salvată.")

    except OSError as error:
        print("Eroare salvare stare:", error)


# =========================
# FORMATARE NOTIFICARI
# =========================

def player_line(player):
    return (
        f"👤 {player['name']}\n"
        f"🏷 {player['tag']}\n"
        f"🏆 {player.get('trophies', 0)} trofee"
    )


def notify_transfer(old_player, new_player):
    message = (
        "🔄 TRANSFER DETECTAT\n\n"
        f"{player_line(new_player)}\n\n"
        f"⬅️ Din: {old_player['clan_name']}\n"
        f"➡️ În: {new_player['clan_name']}\n\n"
        f"🇲🇩 Poziția noului clan: "
        f"#{new_player.get('clan_rank', 0)}"
    )

    send_telegram(message)


def notify_join(player):
    message = (
        "✅ JUCĂTOR INTRAT\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 Clan: {player['clan_name']}\n"
        f"🇲🇩 Poziția clanului: "
        f"#{player.get('clan_rank', 0)}"
    )

    send_telegram(message)


def notify_leave(player):
    message = (
        "🚪 JUCĂTOR IEȘIT\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 A ieșit din: {player['clan_name']}\n"
        f"🇲🇩 Poziția clanului: "
        f"#{player.get('clan_rank', 0)}"
    )

    send_telegram(message)


# =========================
# COMPARARE
# =========================

def compare_players(previous, current):
    previous_tags = set(previous.keys())
    current_tags = set(current.keys())

    common_tags = previous_tags & current_tags

    transfer_tags = set()

    # Transferuri între clanurile monitorizate
    for player_tag in common_tags:
        old_player = previous[player_tag]
        new_player = current[player_tag]

        if (
            old_player.get("clan_tag")
            != new_player.get("clan_tag")
        ):
            transfer_tags.add(player_tag)
            notify_transfer(
                old_player,
                new_player
            )
            time.sleep(0.5)

    # Jucători noi în Top 100
    joined_tags = current_tags - previous_tags

    for player_tag in joined_tags:
        notify_join(current[player_tag])
        time.sleep(0.5)

    # Jucători dispăruți din Top 100
    left_tags = previous_tags - current_tags

    for player_tag in left_tags:
        notify_leave(previous[player_tag])
        time.sleep(0.5)

    print("Transferuri:", len(transfer_tags))
    print("Intrări:", len(joined_tags))
    print("Ieșiri:", len(left_tags))


# =========================
# VERIFICARE PRINCIPALA
# =========================

def run_check():
    print("\n=========================")
    print(
        "Verificare:",
        datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    )
    print("=========================")

    current_players = scan_players()

    if current_players is None:
        print("Verificarea a fost anulată.")
        return

    previous_players = load_previous_players()

    # Prima pornire: doar salvăm lista.
    if previous_players is None or len(previous_players) == 0:
        save_players(current_players)

        send_telegram(
            "✅ Monitorizarea a fost inițializată!\n\n"
            f"🇲🇩 Clanuri urmărite: 100\n"
            f"👥 Jucători salvați: "
            f"{len(current_players)}\n\n"
            "Prima scanare nu generează notificări."
        )

        return

    compare_players(
        previous_players,
        current_players
    )

    save_players(current_players)


# =========================
# PORNIRE BOT
# =========================

def validate_variables():
    missing = []

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not CHAT_ID:
        missing.append("CHAT_ID")

    if not CR_API_TOKEN:
        missing.append("CR_API_TOKEN")

    if missing:
        print(
            "Lipsesc variabilele:",
            ", ".join(missing)
        )
        return False

    return True


if __name__ == "__main__":
    if not validate_variables():
        raise SystemExit(1)

    print("StarAllianceBot a pornit.")

    while True:
        try:
            run_check()

        except Exception as error:
            print(
                "Eroare neașteptată:",
                repr(error)
            )

        print(
            f"Următoarea verificare în "
            f"{CHECK_INTERVAL} secunde."
        )

        time.sleep(CHECK_INTERVAL)
