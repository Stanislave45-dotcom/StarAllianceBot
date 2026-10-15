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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()
CR_API_TOKEN = os.getenv("CR_API_TOKEN", "").strip()


# =====================================
# CONFIGURARE
# =====================================

MOLDOVA_LOCATION_ID = 57000155
API_BASE = "https://proxy.royaleapi.dev/v1"

# Pauză între scanări
CHECK_INTERVAL = 60

# Notificări doar pentru 9001+
MIN_TROPHIES = 9000

# Câte scanări consecutive trebuie să lipsească
# un jucător înainte de verificarea ieșirii
LEAVE_CONFIRMATIONS_REQUIRED = 2

STATE_FILE = "players.json"
PENDING_FILE = "pending_leaves.json"

HEADERS = {
    "Authorization": f"Bearer {CR_API_TOKEN}",
    "Accept": "application/json"
}


# =====================================
# PROFIL ROYALEAPI
# =====================================

def get_profile_url(player_tag):
    clean_tag = (
        str(player_tag)
        .replace("#", "")
        .upper()
    )

    return (
        "https://royaleapi.com/player/"
        + clean_tag
    )


# =====================================
# TELEGRAM
# =====================================

def send_telegram(message, player_tag=None):
    telegram_url = (
        "https://api.telegram.org/bot"
        + BOT_TOKEN
        + "/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    if player_tag:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": (
                            "👤 Vezi profilul pe RoyaleAPI"
                        ),
                        "url": get_profile_url(
                            player_tag
                        )
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
                "Telegram a respins mesajul:",
                response.text
            )
            return False

        return True

    except requests.RequestException as error:
        print(
            "Eroare Telegram:",
            repr(error)
        )
        return False


# =====================================
# CITIRE TOP 100 MOLDOVA
# =====================================

def get_top_clans():
    url = (
        f"{API_BASE}/locations/"
        f"{MOLDOVA_LOCATION_ID}/rankings/clans"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "limit": 100
            },
            timeout=30
        )

        print(
            "Clasament Moldova:",
            response.status_code
        )

        if response.status_code != 200:
            print(
                response.text[:500]
            )
            return None

        data = response.json()

        clans = data.get(
            "items",
            []
        )

        print(
            "Clanuri în Top Moldova:",
            len(clans)
        )

        return clans

    except requests.RequestException as error:
        print(
            "Eroare clasament:",
            repr(error)
        )
        return None


# =====================================
# CITIRE CLAN
# =====================================

def get_clan_data(clan_tag):
    encoded_tag = quote(
        str(clan_tag),
        safe=""
    )

    url = (
        f"{API_BASE}/clans/"
        f"{encoded_tag}"
    )

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
            "Eroare citire clan:",
            clan_tag,
            repr(error)
        )
        return None


# =====================================
# JUCĂTOR EXISTĂ ÎN CLAN?
# =====================================

def player_is_still_in_clan(
    clan_tag,
    player_tag
):
    clan_data = get_clan_data(
        clan_tag
    )

    if clan_data is None:
        # None = nu putem confirma
        return None

    members = clan_data.get(
        "memberList",
        []
    )

    for member in members:
        if (
            member.get("tag")
            == player_tag
        ):
            return True

    return False


# =====================================
# SCANARE TOP 100
# =====================================

def scan_players():
    clans = get_top_clans()

    if clans is None:
        return None

    # Dacă API-ul întoarce prea puține clanuri,
    # nu considerăm scanarea sigură.
    if len(clans) < 90:
        print(
            "ATENȚIE: doar",
            len(clans),
            "clanuri primite."
        )
        print(
            "Scanarea este considerată nesigură."
        )
        return None

    current_players = {}

    current_clans = {}

    failed_clans = []

    for clan in clans:
        clan_tag = clan.get("tag")

        if not clan_tag:
            continue

        clan_name = clan.get(
            "name",
            "Clan necunoscut"
        )

        clan_rank = clan.get(
            "rank",
            0
        )

        current_clans[clan_tag] = {
            "tag": clan_tag,
            "name": clan_name,
            "rank": clan_rank
        }

        clan_data = get_clan_data(
            clan_tag
        )

        if clan_data is None:
            failed_clans.append(
                clan_tag
            )
            continue

        members = clan_data.get(
            "memberList",
            []
        )

        # Protecție suplimentară:
        # dacă API-ul dă o listă evident goală,
        # nu o tratăm drept 50 de ieșiri.
        if (
            clan_data.get(
                "members",
                len(members)
            ) > 0
            and len(members) == 0
        ):
            print(
                "Listă membri suspectă:",
                clan_tag
            )

            failed_clans.append(
                clan_tag
            )
            continue

        for member in members:
            player_tag = member.get(
                "tag"
            )

            if not player_tag:
                continue

            current_players[
                player_tag
            ] = {
                "name": member.get(
                    "name",
                    "Jucător necunoscut"
                ),
                "tag": player_tag,
                "trophies": int(
                    member.get(
                        "trophies",
                        0
                    )
                    or 0
                ),
                "role": member.get(
                    "role",
                    "member"
                ),
                "clan_tag": clan_tag,
                "clan_name": clan_name,
                "clan_rank": clan_rank
            }

        time.sleep(0.10)

    print(
        "Jucători găsiți:",
        len(current_players)
    )

    print(
        "Clanuri cu eroare:",
        len(failed_clans)
    )

    if failed_clans:
        print(
            "Scanarea este incompletă."
        )
        print(
            "Starea NU va fi comparată "
            "sau suprascrisă."
        )

        return None

    return {
        "players": current_players,
        "clans": current_clans
    }


# =====================================
# CITIRE JSON
# =====================================

def load_json(
    file_name,
    default_value
):
    if not os.path.exists(
        file_name
    ):
        return default_value

    try:
        with open(
            file_name,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )

        return data

    except (
        OSError,
        json.JSONDecodeError
    ) as error:
        print(
            "Eroare citire",
            file_name,
            repr(error)
        )

        return default_value


# =====================================
# SALVARE JSON
# =====================================

def save_json(
    file_name,
    data
):
    temporary_file = (
        file_name + ".tmp"
    )

    try:
        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temporary_file,
            file_name
        )

        return True

    except OSError as error:
        print(
            "Eroare salvare",
            file_name,
            repr(error)
        )

        return False


# =====================================
# STAREA JUCĂTORILOR
# =====================================

def load_previous_players():
    data = load_json(
        STATE_FILE,
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return {}

    return data


def save_players(players):
    result = save_json(
        STATE_FILE,
        players
    )

    if result:
        print(
            "Starea jucătorilor a fost salvată."
        )

    return result


# =====================================
# IEȘIRI ÎN AȘTEPTARE
# =====================================

def load_pending_leaves():
    data = load_json(
        PENDING_FILE,
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return {}

    return data


def save_pending_leaves(
    pending
):
    return save_json(
        PENDING_FILE,
        pending
    )


# =====================================
# FORMATARE
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

    trophies = int(
        player.get(
            "trophies",
            0
        )
        or 0
    )

    return (
        f"👤 <b>{player_name}</b>\n"
        f"🏷 {player_tag}\n"
        f"🏆 {trophies} trofee"
    )


# =====================================
# FILTRU TROFEE
# =====================================

def has_enough_trophies(
    player
):
    try:
        trophies = int(
            player.get(
                "trophies",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):
        trophies = 0

    return (
        trophies > MIN_TROPHIES
    )


# =====================================
# NOTIFICARE TRANSFER
# =====================================

def notify_transfer(
    old_player,
    new_player
):
    if not has_enough_trophies(
        new_player
    ):
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
    if not has_enough_trophies(
        player
    ):
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
# NOTIFICARE IEȘIRE
# =====================================

def notify_leave(player):
    if not has_enough_trophies(
        player
    ):
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
# COMPARARE SIGURĂ
# =====================================

def compare_players(
    previous,
    current,
    current_clans
):
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

    disappeared_tags = (
        previous_tags
        - current_tags
    )

    pending = (
        load_pending_leaves()
    )

    transfer_count = 0
    join_count = 0
    suspect_count = 0
    confirmed_leave_count = 0

    sent_transfer_count = 0
    sent_join_count = 0
    sent_leave_count = 0

    transferred_tags = set()


    # =================================
    # TRANSFERURI
    # =================================

    for player_tag in sorted(
        common_tags
    ):
        old_player = (
            previous[player_tag]
        )

        new_player = (
            current[player_tag]
        )

        old_clan_tag = (
            old_player.get(
                "clan_tag"
            )
        )

        new_clan_tag = (
            new_player.get(
                "clan_tag"
            )
        )

        if (
            old_clan_tag
            != new_clan_tag
        ):
            transfer_count += 1

            transferred_tags.add(
                player_tag
            )

            # Nu mai este ieșire pending
            pending.pop(
                player_tag,
                None
            )

            if notify_transfer(
                old_player,
                new_player
            ):
                sent_transfer_count += 1

            time.sleep(0.30)


    # =================================
    # JUCĂTORI REAPĂRUȚI
    # =================================

    for player_tag in current_tags:
        if player_tag in pending:
            print(
                "Jucător reapărut, "
                "ieșirea suspectă anulată:",
                player_tag
            )

            pending.pop(
                player_tag,
                None
            )


    # =================================
    # INTRĂRI
    # =================================

    for player_tag in sorted(
        joined_tags
    ):
        player = current[
            player_tag
        ]

        join_count += 1

        if notify_join(player):
            sent_join_count += 1

        time.sleep(0.30)


    # =================================
    # DISPARIȚII / POSIBILE IEȘIRI
    # =================================

    for player_tag in sorted(
        disappeared_tags
    ):
        old_player = previous[
            player_tag
        ]

        old_clan_tag = (
            old_player.get(
                "clan_tag"
            )
        )

        old_clan_name = (
            old_player.get(
                "clan_name",
                "Clan necunoscut"
            )
        )


        # -----------------------------
        # CLANUL A IEȘIT DIN TOP 100
        # -----------------------------

        if (
            old_clan_tag
            not in current_clans
        ):
            print(
                "Fără alertă:",
                old_player.get("name"),
                "- clanul",
                old_clan_name,
                "nu mai este în Top 100."
            )

            pending.pop(
                player_tag,
                None
            )

            continue


        # -----------------------------
        # PRIMA DISPARIȚIE
        # -----------------------------

        if player_tag not in pending:
            pending[
                player_tag
            ] = {
                "count": 1,
                "player": old_player,
                "first_missing": (
                    datetime.now()
                    .isoformat()
                )
            }

            suspect_count += 1

            print(
                "Ieșire suspectă, "
                "fără notificare:",
                old_player.get("name"),
                player_tag,
                "din",
                old_clan_name
            )

            continue


        # -----------------------------
        # DISPARIȚIE REPETATĂ
        # -----------------------------

        pending_entry = pending[
            player_tag
        ]

        pending_entry["count"] = (
            int(
                pending_entry.get(
                    "count",
                    1
                )
            )
            + 1
        )

        pending[
            player_tag
        ] = pending_entry

        confirmations = int(
            pending_entry.get(
                "count",
                1
            )
        )

        print(
            "Confirmări lipsă:",
            old_player.get("name"),
            confirmations,
            "/",
            LEAVE_CONFIRMATIONS_REQUIRED
        )

        if (
            confirmations
            < LEAVE_CONFIRMATIONS_REQUIRED
        ):
            continue


        # -----------------------------
        # VERIFICARE DIRECTĂ
        # -----------------------------

        print(
            "Verificare directă înainte "
            "de notificarea de ieșire:",
            old_player.get("name"),
            old_clan_name
        )

        still_member = (
            player_is_still_in_clan(
                old_clan_tag,
                player_tag
            )
        )


        # Nu am putut verifica API-ul
        if still_member is None:
            print(
                "Confirmarea a eșuat. "
                "Nu trimitem notificare:",
                player_tag
            )

            continue


        # Jucătorul este încă în clan
        if still_member is True:
            print(
                "ALERTĂ FALSĂ EVITATĂ:",
                old_player.get("name"),
                "este încă în",
                old_clan_name
            )

            pending.pop(
                player_tag,
                None
            )

            continue


        # Jucătorul chiar nu mai este membru
        confirmed_leave_count += 1

        print(
            "IEȘIRE CONFIRMATĂ:",
            old_player.get("name"),
            "din",
            old_clan_name
        )

        if notify_leave(
            old_player
        ):
            sent_leave_count += 1

        pending.pop(
            player_tag,
            None
        )

        time.sleep(0.30)


    save_pending_leaves(
        pending
    )


    # =================================
    # LOG
    # =================================

    print(
        "Transferuri detectate:",
        transfer_count
    )

    print(
        "Intrări detectate:",
        join_count
    )

    print(
        "Ieșiri suspecte noi:",
        suspect_count
    )

    print(
        "Ieșiri confirmate:",
        confirmed_leave_count
    )

    print(
        "În așteptare confirmare:",
        len(pending)
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
# VERIFICARE PRINCIPALĂ
# =====================================

def run_check():
    print(
        "\n========================="
    )

    print(
        "Verificare:",
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        )
    )

    print(
        "========================="
    )

    scan_result = (
        scan_players()
    )

    if scan_result is None:
        print(
            "Verificarea a fost anulată."
        )
        return

    current_players = (
        scan_result["players"]
    )

    current_clans = (
        scan_result["clans"]
    )

    previous_players = (
        load_previous_players()
    )


    # =================================
    # PRIMA PORNIRE
    # =================================

    if not previous_players:
        save_players(
            current_players
        )

        save_pending_leaves(
            {}
        )

        send_telegram(
            "✅ <b>Monitorizarea a fost "
            "inițializată!</b>\n\n"
            "🇲🇩 Clanuri urmărite: "
            f"<b>{len(current_clans)}</b>\n"
            "👥 Jucători salvați: "
            f"<b>{len(current_players)}</b>\n"
            "🏆 Prag notificări: "
            f"<b>peste {MIN_TROPHIES} "
            "trofee</b>\n"
            "🛡 Protecție alerte false: "
            "<b>ACTIVĂ</b>\n"
            "⏱ Pauză între scanări: "
            f"<b>{CHECK_INTERVAL} secunde</b>\n\n"
            "Prima scanare nu generează "
            "notificări despre jucători."
        )

        return


    # =================================
    # COMPARARE
    # =================================

    compare_players(
        previous_players,
        current_players,
        current_clans
    )


    # =================================
    # IMPORTANT:
    # CONSTRUIM STAREA URMĂTOARE
    # =================================

    next_state = dict(
        current_players
    )

    pending = (
        load_pending_leaves()
    )

    # Jucătorii care sunt încă în verificare
    # trebuie păstrați în starea precedentă,
    # altfel la scanarea următoare ar putea
    # fi interpretați ca intrări noi.
    for (
        player_tag,
        pending_entry
    ) in pending.items():

        if (
            player_tag
            not in next_state
        ):
            player_data = (
                pending_entry.get(
                    "player"
                )
            )

            if player_data:
                next_state[
                    player_tag
                ] = player_data


    save_players(
        next_state
    )


# =====================================
# VERIFICARE VARIABILE
# =====================================

def validate_variables():
    missing = []

    if not BOT_TOKEN:
        missing.append(
            "BOT_TOKEN"
        )

    if not CHAT_ID:
        missing.append(
            "CHAT_ID"
        )

    if not CR_API_TOKEN:
        missing.append(
            "CR_API_TOKEN"
        )

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

    print(
        "StarAllianceBot a pornit."
    )

    print(
        "Prag notificări:",
        MIN_TROPHIES
    )

    print(
        "Interval:",
        CHECK_INTERVAL,
        "secunde"
    )

    print(
        "Confirmări pentru ieșire:",
        LEAVE_CONFIRMATIONS_REQUIRED
    )

    print(
        "Protecție anti-false-alert: ACTIVĂ"
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

        time.sleep(
            CHECK_INTERVAL
        )
