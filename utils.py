import discord
import requests
import urllib.parse
from datetime import datetime, timedelta
from config import MONTH_COLORS, EMOJI_BY_DAY
from oznamy_db import get_all_announcements

def get_next_saturday_at_10():
    now = datetime.now()
    days_until_saturday = (5 - now.weekday()) % 7  # sobota = 5
    next_saturday = now + timedelta(days=days_until_saturday)
    target = next_saturday.replace(hour=10, minute=0, second=0, microsecond=0)
    
    if target < now:
        target += timedelta(days=7)
    return target

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except ValueError:
        return None

def parse_event_date(event_str):
    try:
        # Ignorujeme čas, berieme len deň a mesiac
        day_month = event_str.strip().split("//")[0].strip()
        return datetime.strptime(day_month, "%d.%m.")
    except Exception:
        return None

def is_december(date):
    return date.month == 12

def is_january(date):
    return date.month == 1

def parse_date_flexible(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except Exception:
        return None

def parse_event_date_flexible(event_str):
    try:
        date_part = event_str.strip().split("//")[0].strip()
        return datetime.strptime(date_part, "%d.%m.")
    except Exception:
        return None

def announcement_sort_key(a):
    typ = a.get("typ", "info")
    created_at = a.get("created_at", "")
    created_dt = datetime.fromisoformat(created_at) if created_at else datetime.min
    visible_from = parse_date_flexible(a.get("visible_from", "01.01.1970")) or datetime.min

    if typ == "event":
        event_date = parse_event_date_flexible(a.get("datetime", "")) or datetime.max
        try:
            event_date = event_date.replace(year=2000)  # jednotné porovnanie pre dec/jan
        except Exception:
            pass
        return (1, 1, event_date, created_dt)
    else:
        return (0, 0, visible_from, created_dt)

def sort_announcements(announcements, publish_date=None):
    def announcement_group(a):
        now = datetime.now() if publish_date is None else publish_date
        visible_from = parse_date_flexible(a.get("visible_from", "01.01.1970"))
        visible_to = parse_date_flexible(a.get("visible_to", "31.12.9999"))
        if visible_from and visible_to:
            if visible_from <= now <= visible_to:
                return 0  # Aktuálne
        return 1  # Plánované

    if publish_date:
        # Vyfiltruj len aktuálne k danému dátumu
        announcements = [
            a for a in announcements
            if announcement_group(a) == 0
        ]
        # Zoradenie: INFO pred EVENT, potom podľa sort key
        announcements.sort(key=lambda a: (
            a["typ"] != "info",          # INFO skôr ako EVENT
            announcement_sort_key(a)     # ďalšie triedenie
        ))
    else:
        # Klasické delenie na aktuálne / plánované
        announcements.sort(key=lambda a: (
            announcement_group(a),
            a["typ"] != "info",
            announcement_sort_key(a)
        ))

    return announcements

def format_announcement_preview(announcements):
    """Formátuje zoradený zoznam oznamov po pridaní do prehľadného výpisu."""
    now = datetime.now()
    announcements = sort_announcements(announcements)  # Zoradíme podľa požiadaviek
    lines = []

    for ann in announcements:
        typ = ann.get("typ", "").upper()
        title = ann.get("title", "Neznámy")
        description = ann.get("description", "")
        visible_from_str = ann.get("visible_from", "")
        visible_to_str = ann.get("visible_to", "")
        ann_id = ann.get("id", "???")

        try:
            visible_from = datetime.strptime(visible_from_str, "%d.%m.%Y")
            visible_to = datetime.strptime(visible_to_str, "%d.%m.%Y")
        except Exception:
            visible_from = visible_to = None

        if visible_from and visible_to:
            if visible_from <= now <= visible_to:
                emoji = "🟩"  # aktuálne zobrazovaný
            elif now < visible_from:
                emoji = "🟦"  # plánovaný
            else:
                emoji = "⬜"  # expirovaný
        else:
            emoji = "⬜"  # neplatný dátum

        # Skráť popis (prvých 5-6 slov)
        short_desc = " ".join(description.split()[:6]) + ("..." if len(description.split()) > 6 else "")

        # Výpis
        lines.append(
            f"{emoji} **[{typ}] {title}** (ID: `{ann_id}`)\n"
            f"_{short_desc}_\n"
            f"📅 {visible_from_str} – {visible_to_str}\n"
        )

    return "\n".join(lines)

def get_next_friday_and_thursday():
    today = datetime.today()
    friday_offset = (4 - today.weekday()) % 7  # 4 = Friday
    next_friday = today + timedelta(days=friday_offset)
    next_thursday = next_friday + timedelta(days=6)
    return next_friday, next_thursday

def format_date(date):
    return f"{date.day}.{date.month}.{date.year}"

def generate_oznam_embed(typ, title, description, datetime_str, link, image, day, oznam_color):
    embed = discord.Embed(description=description, color=oznam_color)
    if typ == "event" and datetime_str:
        icon_url = EMOJI_BY_DAY.get(day.lower(), "") if day else ""
        embed.set_author(name=datetime_str, icon_url=icon_url)
    if link:
        embed.title = f"🔗 {title}"
        embed.url = link
    else:
        embed.title = title
    if typ == "info" and image:
        encoded_url = urllib.parse.quote(image, safe='')
        embed.set_thumbnail(url=f"http://217.154.124.73:8080/thumbnail?url={encoded_url}")
    return embed

# Formátovanie jedinečných embedov ako oznamov
def generate_announcement_embeds_for_date(target_date: datetime):
    all_announcements = get_all_announcements()
    embeds = []

    for ann in sort_announcements(all_announcements, publish_date=target_date):
        try:
            visible_from = datetime.strptime(ann["visible_from"], "%d.%m.%Y")
            visible_to = datetime.strptime(ann["visible_to"], "%d.%m.%Y")
        except Exception:
            continue

        if not (visible_from <= target_date <= visible_to):
            continue

        light_color, dark_color = MONTH_COLORS.get(target_date.month, (0xDDDDDD, 0x999999))
        embed_color = light_color if ann["typ"] == "info" else dark_color

        embed = generate_oznam_embed(
            typ=ann["typ"],
            title=ann["title"],
            description=ann["description"],
            datetime_str=ann.get("datetime"),
            link=ann.get("link"),
            image=ann.get("image"),
            day=ann.get("day"),
            oznam_color=embed_color
        )
        embeds.append(embed)

    return embeds

def get_day_icon(datetime_str):
    emoji_map = {
        "pondelok": "https://cdn3.emoji.gg/emojis/5712_monday.png",
        "utorok": "https://cdn3.emoji.gg/emojis/6201_tuesday.png",
        "streda": "https://cdn3.emoji.gg/emojis/4270_wednesday.png",
        "štvrtok": "https://cdn3.emoji.gg/emojis/6285_thursday.png",
        "piatok": "https://cdn3.emoji.gg/emojis/2064_friday.png",
        "sobota": "https://cdn3.emoji.gg/emojis/4832_saturday.png",
        "nedeľa": "https://cdn3.emoji.gg/emojis/8878_sunday.png"
    }
    for key in emoji_map:
        if key in datetime_str.lower():
            return emoji_map[key]
    return ""
