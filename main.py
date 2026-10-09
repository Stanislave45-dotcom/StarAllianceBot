import html
import json
import os
import time
from datetime import datetime
from urllib.parse import quote

import requests


# =====================================
# VARIABILE RAILWAY
# =====================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CR_API_TOKEN = os.getenv("CR_API_TOKEN")


# =====================================
# CONFIGURARE
# =====================================

MOLDOVA_LOCATION_ID = 57000155
API_BASE = "https://proxy.royaleapi.dev/v1"

# Verificare la fiecare 60 de secunde
CHECK_INTERVAL = 60

# Alerte numai pentru jucători cu peste 9000
MIN_TROPHIES = 9000

STATE_FILE = "players.json"

HEADERS = {
    "Authorization": f"Bearer {CR_API_TOKEN}"
}


# =====================================
# TRIMITERE MESAJ TELEGRAM
# =====================================

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
                "parse_mode": "HTML",
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


# =====================================
# CITIRE TOP 100 MOLDOVA
# =====================================

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


# =====================================
# CITIRE MEMBRI CLAN
# =====================================

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


# =====================================
# SCANARE JUCATORI
# =====================================

def scan_players():
    clans = get_top_clans()

    if clans is None:
        return None

    current_players = {}
    failed_clans = 0

    print("Clanuri găsite:", len(clans))

    for clan in clans:
        clan_tag = clan.get("tag")
        clan_name = clan.get(
            "name",
            "Clan necunoscut"
        )
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
                "trophies": member.get(
                    "trophies",
                    0
                ),
                "role": member.get(
                    "role",
                    "member"
                ),
                "clan_tag": clan_tag,
                "clan_name": clan_name,
                "clan_rank": clan_rank
            }

        # Pauză mică între solicitări
        time.sleep(0.10)

    print("Jucători găsiți:", len(current_players))
    print("Clanuri cu eroare:", failed_clans)

    # Nu comparăm dacă scanarea este incompletă.
    # Astfel evităm notificările false.
    if failed_clans > 0:
        print(
            "Scanarea este incompletă. "
            "Comparația a fost anulată."
        )
        return None

    return current_players


# =====================================
# CITIRE SI SALVARE STARE
# =====================================

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


# =====================================
# PROFIL ROYALEAPI
# =====================================

def get_profile_url(player_tag):
    tag_without_hash = (
        player_tag
        .replace("#", "")
        .upper()
    )

    return (
        f"https://royaleapi.com/player/"
        f"{tag_without_hash}"
    )


# =====================================
# FORMATARE JUCATOR
# =====================================

def player_line(player):
    player_name = html.escape(
        str(player.get(
            "name",
            "Jucător necunoscut"
        ))
    )

    player_tag = str(
        player.get("tag", "")
    )

    safe_tag = html.escape(player_tag)
    profile_url = get_profile_url(player_tag)
    trophies = player.get("trophies", 0)

    return (
        f'👤 {profile_url}'
        f"<b>{player_name}</b></a>\n"
        f"🏷 {safe_tag}\n"
        f"🏆 {trophies} trofee"
    )


# =====================================
# FILTRU TROFEE
# =====================================

def has_enough_trophies(player):
    trophies = player.get("trophies", 0)

    # Numai peste 9000, deci 9001+
    return trophies > MIN_TROPHIES


# =====================================
# NOTIFICARE TRANSFER
# =====================================

def notify_transfer(old_player, new_player):
    if not has_enough_trophies(new_player):
        print(
            "Transfer ignorat sub prag:",
            new_player.get("name"),
            new_player.get("trophies")
        )
        return

    old_clan = html.escape(
        str(old_player.get(
            "clan_name",
            "Clan necunoscut"
        ))
    )

    new_clan = html.escape(
        str(new_player.get(
            "clan_name",
            "Clan necunoscut"
        ))
    )

    old_rank = old_player.get("clan_rank", 0)
    new_rank = new_player.get("clan_rank", 0)

    message = (
        "🔄 <b>TRANSFER DETECTAT</b>\n\n"
        f"{player_line(new_player)}\n\n"
        f"⬅️ Din: <b>{old_clan}</b> "
        f"(#{old_rank})\n"
        f"➡️ În: <b>{new_clan}</b> "
        f"(#{new_rank})"
    )

    send_telegram(message)


# =====================================
# NOTIFICARE INTRARE
# =====================================

def notify_join(player):
    if not has_enough_trophies(player):
        print(
            "Intrare ignorată sub prag:",
            player.get("name"),
            player.get("trophies")
        )
        return

    clan_name = html.escape(
        str(player.get(
            "clan_name",
            "Clan necunoscut"
        ))
    )

    clan_rank = player.get("clan_rank", 0)

    message = (
        "✅ <b>JUCĂTOR INTRAT</b>\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 Clan: <b>{clan_name}</b>\n"
        f"🇲🇩 Poziția clanului: "
        f"<b>#{clan_rank}</b>"
    )

    send_telegram(message)


# =====================================
# NOTIFICARE IESIRE
# =====================================

def notify_leave(player):
    if not has_enough_trophies(player):
        print(
            "Ieșire ignorată sub prag:",
            player.get("name"),
            player.get("trophies")
        )
        return

    clan_name = html.escape(
        str(player.get(
            "clan_name",
            "Clan necunoscut"
        ))
    )

    clan_rank = player.get("clan_rank", 0)

    message = (
        "🚪 <b>JUCĂTOR IEȘIT</b>\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 A ieșit din: "
        f"<b>{clan_name}</b>\n"
        f"🇲🇩 Poziția clanului: "
        f"<b>#{clan_rank}</b>"
    )

    send_telegram(message)


# =====================================
# COMPARARE JUCATORI
# =====================================

def compare_players(previous, current):
    previous_tags = set(previous.keys())
    current_tags = set(current.keys())

    common_tags = previous_tags & current_tags

    transfer_count = 0
    join_count = 0
    leave_count = 0

    # Transferuri între clanurile din Top 100
    for player_tag in common_tags:
        old_player = previous[player_tag]
        new_player = current[player_tag]

        if (
            old_player.get("clan_tag")
            != new_player.get("clan_tag")
        ):
            transfer_count += 1

            notify_transfer(
                old_player,
                new_player
            )

            time.sleep(0.5)

    # Jucători nou apăruți în Top 100
    joined_tags = current_tags - previous_tags

    for player_tag in joined_tags:
        join_count += 1

        notify_join(
            current[player_tag]
        )

        time.sleep(0.5)

    # Jucători dispăruți din Top 100
    left_tags = previous_tags - current_tags

    for player_tag in left_tags:
        leave_count += 1

        notify_leave(
            previous[player_tag]
        )

        time.sleep(0.5)

    print("Transferuri detectate:", transfer_count)
    print("Intrări detectate:", join_count)
    print("Ieșiri detectate:", leave_count)


# =====================================
# VERIFICARE PRINCIPALA
# =====================================

def run_check():
    print("\n=========================")
    print(
        "Verificare:",
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        )
    )
    print("=========================")

    current_players = scan_players()

    if current_players is None:
        print("Verificarea a fost anulată.")
        return

    previous_players = load_previous_players()

    # Prima pornire salvează lista fără notificări.
    if (
        previous_players is None
        or len(previous_players) == 0
    ):
        save_players(current_players)

        send_telegram(
            "✅ <b>Monitorizarea a fost "
            "inițializată!</b>\n\n"
            "🇲🇩 Clanuri urmărite: "
            "<b>100</b>\n"
            f"👥 Jucători salvați: "
            f"<b>{len(current_players)}</b>\n"
            f"🏆 Prag notificări: "
            f"<b>peste {MIN_TROPHIES} trofee</b>\n"
            "⏱ Verificare: "
            "<b>la fiecare minut</b>\n\n"
            "Prima scanare nu generează "
            "notificări."
        )

        return

    compare_players(
        previous_players,
        current_players
    )

    save_players(current_players)


# =====================================
# VERIFICARE VARIABILE
# =====================================

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


# =====================================
# PORNIRE BOT
# =====================================

if __name__ == "__main__":
    if not validate_variables():
        raise SystemExit(1)

    print("StarAllianceBot a pornit.")
    print(
        "Prag notificări:",
        MIN_TROPHIES
    )
    print(
        "Interval verificare:",
        CHECK_INTERVAL,
        "secunde"
    )

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
