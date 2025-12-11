import os
from dotenv import load_dotenv

load_dotenv()

# KONFIGURAČNÉ KONSTANTY
# Načítanie z .env s fallbackom na produkčné hodnoty (pre spätnú kompatibilitu)
AUTHORIZED_ROLE = os.getenv("AUTHORIZED_ROLE", "Team Mod")
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "Admin")
OZNAMY_ROLE = os.getenv("OZNAMY_ROLE", "Oznamy")

# ID kanálov a kategórií (musia byť int)
def get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (ValueError, TypeError):
        return default

CATEGORY_ID = get_int_env("CATEGORY_ID", 1231260260015149068)
ARCHIVE_CATEGORY_ID = get_int_env("ARCHIVE_CATEGORY_ID", 1077174157416087602)
COMMAND_CHANNEL_ID = get_int_env("COMMAND_CHANNEL_ID", 819184838274711582)
HOW_TO_CHANNEL_ID = get_int_env("HOW_TO_CHANNEL_ID", 1278324331683778722)
OZNAMY_CHANNEL_ID = get_int_env("OZNAMY_CHANNEL_ID", 1043629695150850048)
MODERATOR_CHANNEL_ID = get_int_env("MODERATOR_CHANNEL_ID", 1026422525464424519)

CHANNEL_NAME_TEMPLATE = "{emoji}・{name}"
ARCHIVE_EMOJI = "✅"
THOUGHTS_FILE = "thoughts.txt"

# Farby pre každý mesiac (jemná pre INFO, sýta pre EVENT)
MONTH_COLORS = {
    1: (0xD6EAF8, 0x21618C),   # Január – ľadová modrá, tmavomodrá
    2: (0xCCD1D1, 0x2E4053),   # Február – šedá, zimná modrošedá
    3: (0xEAD1DC, 0x8E44AD),   # Marec – pôstna fialová
    4: (0xFCF3CF, 0xF4D03F),   # Apríl – jarná svetložltá
    5: (0xD5F5E3, 0x27AE60),   # Máj – zelená, rozkvitnutá príroda
    6: (0xFDEBD0, 0xE67E22),   # Jún – letná oranžová
    7: (0xFADBD8, 0xC0392B),   # Júl – horúca červenooranžová
    8: (0xF9E79F, 0xD68910),   # August – dozrievajúca, pomarančová
    9: (0xFCF3CF, 0xB7950B),   # September – babie leto
    10: (0xF6DDCC, 0xCA6F1E),  # Október – jesenné lístie
    11: (0xD5DBDB, 0x566573),  # November – sychravá šedá
    12: (0xFBEEE6, 0xB03A2E),  # December – vianočná, teplá červenozlatá
}

EMOJI_BY_DAY = {
    "pondelok": "https://cdn3.emoji.gg/emojis/5712_monday.png",
    "utorok": "https://cdn3.emoji.gg/emojis/6201_tuesday.png",
    "streda": "https://cdn3.emoji.gg/emojis/4270_wednesday.png",
    "štvrtok": "https://cdn3.emoji.gg/emojis/6285_thursday.png",
    "piatok": "https://cdn3.emoji.gg/emojis/2064_friday.png",
    "sobota": "https://cdn3.emoji.gg/emojis/4832_saturday.png",
    "nedeľa": "https://cdn3.emoji.gg/emojis/8878_sunday.png"
}

DEFAULT_REACTION_EMOJI = os.getenv("DEFAULT_REACTION_EMOJI", "<:3horky:1377264806905516053>")
REACTION_EMOJI = DEFAULT_REACTION_EMOJI
