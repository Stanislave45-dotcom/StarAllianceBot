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

# Pauză după terminarea unei scanări
CHECK_INTERVAL = 60

# Notificări numai pentru 9001+ trofee
MIN_TROPHIES = 9000

# Fișierul în care se păstrează ultima stare
STATE_FILE = "players.json"

HEADERS = {
    "Authorization": f"Bearer {CR_API_TOKEN}"
}


# =====================================
# PROFIL ROYALEAPI
# =====================================

def get_profile_url(player_tag):
    tag_without_hash = (
        str(player_tag)
        .replace("#", "")
        .upper()
    )

    return (
        "https://royaleapi.com/player/"
        + tag_without_hash
    )


# =====================================
# TRIMITERE MESAJ TELEGRAM
# =====================================

def send_telegram(message, player_tag=None):
    telegram_url = (
        "https://api.telegram.org/bot"
        + str(BOT_TOKEN)
        + "/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    # Adaugă buton către profilul jucătorului
    if player_tag:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": "👤 Vezi profilul pe RoyaleAPI",
                        "url": get_profile_url(player_tag)
                    }
                ]
            ]
        }

    try:
        response = requests.post(
            telegram_url,
            json=payload,
            timeout=30
        )

        print(
            "Telegram:",
            response.status_code,
            response.text[:500]
        )

        if response.status_code != 200:
            print(
                "Telegram a respins notificarea:",
                response.text
            )
            return False

        return True

    except requests.RequestException as error:
        print("Eroare Telegram:", error)
        return False


# =====================================
# CITIRE TOP 100 MOLDOVA
# =====================================

def get_top_clans():
    url = (
        f"{API_BASE}/locations/"
        f"{MOLDOVA_LOCATION_ID}/rankings/clans"
        "?limit=100"
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
    encoded_tag = quote(
        clan_tag,
        safe=""
    )

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
                response.text[:300]
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

        clan_rank = clan.get(
            "rank",
            0
        )

        if not clan_tag:
            continue

        clan_data = get_clan_members(
            clan_tag
        )

        if clan_data is None:
            failed_clans += 1
            continue

        members = clan_data.get(
            "memberList",
            []
        )

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

        # Pauză mică între cererile API
        time.sleep(0.10)

    print(
        "Jucători găsiți:",
        len(current_players)
    )

    print(
        "Clanuri cu eroare:",
        failed_clans
    )

    # Dacă nu am putut citi toate clanurile,
    # anulăm comparația pentru a evita alerte false
    if failed_clans > 0:
        print(
            "Scanarea este incompletă. "
            "Comparația a fost anulată."
        )
        return None

    return current_players


# =====================================
# CITIRE STARE
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


# =====================================
# SALVARE STARE
# =====================================

def save_players(players):
    temporary_file = (
        STATE_FILE + ".tmp"
    )

    try:
        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                players,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temporary_file,
            STATE_FILE
        )

        print("Starea a fost salvată.")
        return True

    except OSError as error:
        print("Eroare salvare stare:", error)
        return False


# =====================================
# FORMATARE JUCATOR
# =====================================

def player_line(player):
    player_name = html.escape(
        str(
            player.get(
                "name",
                "Jucător necunoscut"
            )
        )
    )

    player_tag = html.escape(
        str(
            player.get(
                "tag",
                ""
            )
        )
    )

    trophies = player.get(
        "trophies",
        0
    )

    return (
        f"👤 <b>{player_name}</b>\n"
        f"🏷 {player_tag}\n"
        f"🏆 {trophies} trofee"
    )


# =====================================
# FILTRU TROFEE
# =====================================

def has_enough_trophies(player):
    try:
        trophies = int(
            player.get(
                "trophies",
                0
            )
        )

    except (TypeError, ValueError):
        trophies = 0

    # "Peste 9000" înseamnă minimum 9001
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
        return False

    old_clan = html.escape(
        str(
            old_player.get(
                "clan_name",
                "Clan necunoscut"
            )
        )
    )

    new_clan = html.escape(
        str(
            new_player.get(
                "clan_name",
                "Clan necunoscut"
            )
        )
    )

    old_rank = old_player.get(
        "clan_rank",
        0
    )

    new_rank = new_player.get(
        "clan_rank",
        0
    )

    message = (
        "🔄 <b>TRANSFER DETECTAT</b>\n\n"
        f"{player_line(new_player)}\n\n"
        f"⬅️ Din: <b>{old_clan}</b> "
        f"(#{old_rank})\n"
        f"➡️ În: <b>{new_clan}</b> "
        f"(#{new_rank})"
    )

    return send_telegram(
        message,
        new_player.get("tag")
    )


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
        return False

    clan_name = html.escape(
        str(
            player.get(
                "clan_name",
                "Clan necunoscut"
            )
        )
    )

    clan_rank = player.get(
        "clan_rank",
        0
    )

    message = (
        "✅ <b>JUCĂTOR INTRAT</b>\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 Clan: <b>{clan_name}</b>\n"
        f"🇲🇩 Poziția clanului: "
        f"<b>#{clan_rank}</b>"
    )

    return send_telegram(
        message,
        player.get("tag")
    )


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
        return False

    clan_name = html.escape(
        str(
            player.get(
                "clan_name",
                "Clan necunoscut"
            )
        )
    )

    clan_rank = player.get(
        "clan_rank",
        0
    )

    message = (
        "🚪 <b>JUCĂTOR IEȘIT</b>\n\n"
        f"{player_line(player)}\n\n"
        f"🏰 A ieșit din: "
        f"<b>{clan_name}</b>\n"
        f"🇲🇩 Poziția clanului: "
        f"<b>#{clan_rank}</b>"
    )

    return send_telegram(
        message,
        player.get("tag")
    )


# =====================================
# COMPARARE JUCATORI
# =====================================

def compare_players(previous, current):
    previous_tags = set(
        previous.keys()
    )

    current_tags = set(
        current.keys()
    )

    common_tags = (
        previous_tags
        & current_tags
    )

    joined_tags = (
        current_tags
        - previous_tags
    )

    left_tags = (
        previous_tags
        - current_tags
    )

    transfer_count = 0
    join_count = 0
    leave_count = 0

    sent_transfer_count = 0
    sent_join_count = 0
    sent_leave_count = 0

    # Transferuri între clanuri monitorizate
    for player_tag in sorted(common_tags):
        old_player = previous[player_tag]
        new_player = current[player_tag]

        if (
            old_player.get("clan_tag")
            != new_player.get("clan_tag")
        ):
            transfer_count += 1

            if notify_transfer(
                old_player,
                new_player
            ):
                sent_transfer_count += 1

            time.sleep(0.30)

    # Intrări
    for player_tag in sorted(joined_tags):
        join_count += 1

        if notify_join(
            current[player_tag]
        ):
            sent_join_count += 1

        time.sleep(0.30)

    # Ieșiri
    for player_tag in sorted(left_tags):
        leave_count += 1

        if notify_leave(
            previous[player_tag]
        ):
            sent_leave_count += 1

        time.sleep(0.30)

    print(
        "Transferuri detectate:",
        transfer_count
    )

    print(
        "Intrări detectate:",
        join_count
    )

    print(
        "Ieșiri detectate:",
        leave_count
    )

    print(
        "Notificări transfer trimise:",
        sent_transfer_count
    )

    print(
        "Notificări intrare trimise:",
        sent_join_count
    )

    print(
        "Notificări ieșire trimise:",
        sent_leave_count
    )


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

    previous_players = (
        load_previous_players()
    )

    # Prima scanare salvează lista,
    # fără notificări despre jucători
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
            f"⏱ Pauză între scanări: "
            f"<b>{CHECK_INTERVAL} secunde</b>\n\n"
            "Prima scanare nu generează "
            "notificări despre jucători."
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
        "Pauză între scanări:",
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
            "Următoarea verificare începe în "
            f"{CHECK_INTERVAL} secunde."
        )

        time.sleep(CHECK_INTERVAL)
