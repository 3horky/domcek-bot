import discord
import os
import asyncio
import random
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from dotenv import load_dotenv
from oznamy_db import init_db, add_announcement, get_all_announcements, get_announcement_by_id, delete_announcement_by_id, update_announcement_by_id
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, timedelta

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# KONFIGURAČNÉ KONSTANTY
AUTHORIZED_ROLE = "Team Mod"
ADMIN_ROLE = "Admin"
CATEGORY_ID = 1231260260015149068
ARCHIVE_CATEGORY_ID = 1077174157416087602
COMMAND_CHANNEL_ID = 819184838274711582
HOW_TO_CHANNEL_ID = 1278324331683778722
MODERATOR_CHANNEL_ID = 1026422525464424519
CHANNEL_NAME_TEMPLATE = "{emoji}・{name}"
ARCHIVE_EMOJI = "✅"
OZNAMY_ROLE = "Oznamy"

EMOJI_BY_DAY = {
    "pondelok": "https://cdn3.emoji.gg/emojis/5712_monday.png",
    "utorok": "https://cdn3.emoji.gg/emojis/6201_tuesday.png",
    "streda": "https://cdn3.emoji.gg/emojis/4270_wednesday.png",
    "štvrtok": "https://cdn3.emoji.gg/emojis/6285_thursday.png",
    "piatok": "https://cdn3.emoji.gg/emojis/2064_friday.png",
    "sobota": "https://cdn3.emoji.gg/emojis/4832_saturday.png",
    "nedeľa": "https://cdn3.emoji.gg/emojis/8878_sunday.png"
}

REACTION_EMOJI = os.getenv("DEFAULT_REACTION_EMOJI", "<:3horky:1377264806905516053>")
AUTO_REACT_CHANNELS = set()
THOUGHTS_FILE = "thoughts.txt"

async def cron_clean_expired_announcements():
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
        sleep_duration = (next_run - now).total_seconds()

        print(f"[🕐] Čistenie databázy sa spustí o {sleep_duration / 3600:.2f} hodín ({next_run})")
        await asyncio.sleep(sleep_duration)

        from oznamy_db import delete_expired_announcements
        delete_expired_announcements()
        print("[✅] V databáze boli vymazané expirované oznamy.")

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

def sort_announcements(announcements):
    def announcement_sort_key(a):
        typ = a.get("typ", "info")
        created_at = a.get("created_at", "")
        created_dt = datetime.fromisoformat(created_at) if created_at else datetime.min
        visible_from = parse_date(a.get("visible_from", "01.01.1970")) or datetime.min

        if typ == "event":
            event_date = parse_event_date(a.get("datetime", "")) or datetime.max
            # Upravíme dátum roka na 2000 kvôli porovnávaniu dec-jan
            try:
                event_date = event_date.replace(year=2000)
            except Exception:
                pass
            return (1, 1, event_date, created_dt)  # typ 1 = event
        else:
            return (0, 0, visible_from, created_dt)  # typ 0 = info

    def announcement_group(a):
        now = datetime.now()
        visible_from = parse_date(a.get("visible_from", "01.01.1970"))
        visible_to = parse_date(a.get("visible_to", "31.12.9999"))
        if visible_from and visible_to:
            if visible_from <= now <= visible_to:
                return 0  # Aktuálne
        return 1  # Plánované

    # Najprv rozdelíme na aktuálne a plánované
    announcements.sort(key=lambda a: (
        announcement_group(a),         # aktuálne/plánované
        a["typ"] != "info",            # info < event
        announcement_sort_key(a)       # podľa typu
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

def generate_oznam_embed(typ, title, description, datetime, link, image, day):
    embed = discord.Embed(description=description, color=discord.Color.blue())
    if typ == "event" and datetime:
        icon_url = EMOJI_BY_DAY.get(day.lower(), "") if day else ""
        embed.set_author(name=datetime, icon_url=icon_url)
    if link:
        embed.title = f"🔗 {title}"
        embed.url = link
    else:
        embed.title = title
    if typ == "info" and image:
        embed.set_thumbnail(url=image)
    return embed

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

class DeleteConfirmView(View):
    def __init__(self, announcement_id):
        super().__init__(timeout=60)
        self.announcement_id = announcement_id

    @discord.ui.button(label="✅ Potvrdiť vymazanie", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        delete_announcement_by_id(self.announcement_id)
        await interaction.response.edit_message(content=f"✅ Oznam ID `{self.announcement_id}` bol vymazaný.", view=None)

    @discord.ui.button(label="❌ Zrušiť", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content="Vymazanie zrušené.", view=None)

class EditOznamModal(Modal, title="Uprav oznam"):
    def __init__(self, bot, announcement_id, announcement):
        super().__init__()
        self.bot = bot
        self.announcement_id = announcement_id
        self.typ = announcement["typ"]
        self.title_input = TextInput(label="Názov", default=announcement["title"])
        self.description_input = TextInput(label="Popis", style=discord.TextStyle.paragraph, default=announcement["description"])
        self.visible_input = TextInput(label="Zobrazovať od - do", default=f"{announcement['visible_from']} - {announcement['visible_to']}")
        if self.typ == "event":
            self.datetime_input = TextInput(label="Dátum a čas", default=announcement.get("datetime", ""))
            self.day_input = TextInput(label="Deň", default=announcement.get("day", ""))
        else:
            self.image_input = TextInput(label="Obrázok URL", default=announcement.get("image", ""))
            self.link_input = TextInput(label="Link", default=announcement.get("link", ""))

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.visible_input)
        if self.typ == "event":
            self.add_item(self.datetime_input)
            self.add_item(self.day_input)
        else:
            self.add_item(self.image_input)
            self.add_item(self.link_input)

    async def on_submit(self, interaction: Interaction):
        data = {
            "title": self.title_input.value,
            "description": self.description_input.value,
            "visible_from": self.visible_input.value.split(" - ")[0].strip(),
            "visible_to": self.visible_input.value.split(" - ")[1].strip(),
        }
        if self.typ == "event":
            data["datetime"] = self.datetime_input.value
            data["day"] = self.day_input.value
        else:
            data["image"] = self.image_input.value
            data["link"] = self.link_input.value

        update_announcement_by_id(self.announcement_id, data)

        embed = generate_oznam_embed(
            typ=self.typ,
            title=data["title"],
            description=data["description"],
            datetime=data.get("datetime"),
            link=data.get("link"),
            image=data.get("image"),
            day=data.get("day")
        )
        await interaction.response.send_message(f"✅ Oznam bol upravený.", embed=embed)

class EventOznamModal(Modal, title="Nový event oznam"):
    def __init__(self, bot, title="", description="", datetime="", day="", visible_dates=""):
        super().__init__()
        self.bot = bot
        self.add_item(TextInput(label="Názov oznamu", default=title))
        self.add_item(TextInput(label="Popis oznamu", style=discord.TextStyle.paragraph, default=description))
        self.add_item(TextInput(label="Dátum a čas (napr. 15.06. // 18:00)", default=datetime))
        self.add_item(TextInput(label="Deň v týždni (napr. piatok)", default=day))
        default_range = visible_dates or self._default_visible_range()
        self.add_item(TextInput(label="Zobrazovať od kedy - do kedy", default=default_range))

    def _default_visible_range(self):
        start, end = get_next_friday_and_thursday()
        return f"{format_date(start)} - {format_date(end)}"

    async def on_submit(self, interaction: discord.Interaction):
        children = [c.value for c in self.children]
        title, description, datetime_str, day, visible_range = children
        embed = generate_oznam_embed("event", title, description, datetime_str, None, None, day)
        await interaction.response.send_message(embed=embed, view=OznamConfirmView(self.bot, {
            "typ": "event",
            "title": title,
            "description": description,
            "datetime": datetime_str,
            "day": day,
            "visible_dates": visible_range,
            "link": None,
            "image": None
        }), ephemeral=False)

class InfoOznamModal(Modal, title="Nový info oznam"):
    def __init__(self, bot, title="", description="", image="", link="", visible_dates=""):
        super().__init__()
        self.bot = bot
        self.add_item(TextInput(label="Názov oznamu", default=title))
        self.add_item(TextInput(label="Popis oznamu", style=discord.TextStyle.paragraph, default=description))
        self.add_item(TextInput(label="URL obrázka", default=image))
        self.add_item(TextInput(label="Link (voliteľné)", default=link))
        default_range = visible_dates or self._default_visible_range()
        self.add_item(TextInput(label="Zobrazovať od kedy - do kedy", default=default_range))

    def _default_visible_range(self):
        start, end = get_next_friday_and_thursday()
        return f"{format_date(start)} - {format_date(end)}"

    async def on_submit(self, interaction: discord.Interaction):
        children = [c.value for c in self.children]
        title, description, image, link, visible_range = children
        embed = generate_oznam_embed("info", title, description, None, link, image, None)
        await interaction.response.send_message(embed=embed, view=OznamConfirmView(self.bot, {
            "typ": "info",
            "title": title,
            "description": description,
            "image": image,
            "link": link,
            "visible_dates": visible_range,
            "datetime": None,
            "day": None
        }), ephemeral=False)


class OznamConfirmView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=300)
        self.bot = bot
        self.data = data

    @discord.ui.button(label="✅ Pridať", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        # 1. Uloženie do databázy
        add_announcement(
            typ=self.data.get("typ", ""),
            title=self.data.get("title", ""),
            description=self.data.get("description", ""),
            datetime_str=self.data.get("datetime", ""),
            day=self.data.get("day", ""),
            link=self.data.get("link", ""),
            image=self.data.get("image", ""),
            visible_from=self.data.get("visible_dates", "").split(" - ")[0],
            visible_to=self.data.get("visible_dates", "").split(" - ")[1]
        )
        await interaction.response.edit_message(content="✅ Oznam bol pridaný!", embed=None, view=None)

        # 💾 Po uložení – načítaj všetky oznamy z DB
        from oznamy_db import get_all_announcements  # Uisti sa, že táto funkcia existuje
        all_announcements = get_all_announcements()

        preview_text = format_announcement_preview(all_announcements)

        # 📬 Odošli výpis
        await interaction.followup.send(content="**📋 Aktuálne oznamy:**\n\n" + preview_text, ephemeral=False)

    @discord.ui.button(label="❌ Zrušiť", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Zrušené.", embed=None, view=None)

    @discord.ui.button(label="✏️ Upraviť", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: Button):
        typ = self.data.get("typ", "event")

        # Prepíš pôvodnú správu, aby neplietla
        await interaction.message.edit(content="📝 Vybral(a) si možnosť upraviť oznam.", embed=None, view=None)

        if typ == "event":
            await interaction.response.send_modal(EventOznamModal(
                bot=self.bot,
                title=self.data.get("title", ""),
                description=self.data.get("description", ""),
                datetime=self.data.get("datetime", ""),
                day=self.data.get("day", ""),
                visible_dates=self.data.get("visible_dates", "")
            ))
        else:
            await interaction.response.send_modal(InfoOznamModal(
                bot=self.bot,
                title=self.data.get("title", ""),
                description=self.data.get("description", ""),
                image=self.data.get("image", ""),
                link=self.data.get("link", ""),
                visible_dates=self.data.get("visible_dates", "")
            ))


@bot.tree.command(name="pridaj_oznam", description="Pridá nový oznam pomocou modálneho okna")
@app_commands.describe(typ="Zadaj typ: event alebo info")
async def pridaj_oznam(interaction: discord.Interaction, typ: str):
    if typ == "event":
        await interaction.response.send_modal(EventOznamModal(bot))
    elif typ == "info":
        await interaction.response.send_modal(InfoOznamModal(bot))
    else:
        await interaction.response.send_message("Typ musí byť `event` alebo `info`.", ephemeral=True)


async def keep_alive_loop():  # Aby Google nevypol VM pre nečinnosť
    while True:
        print("Heartbeat - bot je nažive")
        await asyncio.sleep(300)  # každých 5 minút

@bot.event
async def on_ready():
    print(f"Bot prihlásený ako {bot.user}")
    bot.loop.create_task(keep_alive_loop())
    update_status.start()
    init_db()
    bot.loop.create_task(cron_clean_expired_announcements())
    # await bot.add_cog(OznamCog(bot))

    
    try:
        print("====== on_ready() spustený ======")
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        for cmd in synced:
            print(f"- {cmd.name}: {cmd.description}")
    except Exception as e:
        print(e)

    # Odošli návod do how_to len ak tam ešte nie je
    how_to_channel = bot.get_channel(HOW_TO_CHANNEL_ID)
    if how_to_channel:
        history = [msg async for msg in how_to_channel.history(limit=10)]
        if not any("Používanie bota" in msg.content for msg in history if msg.author == bot.user):
            await how_to_channel.send(
                "📬 **Používanie bota**\n\n"
                "**Vytvorenie kanála:**\n"
                "Spusti príkaz `/vytvor_channel` v kanáli <#819184838274711582> a zadaj:\n"
                "- `emoji`: napr. 🏫 alebo 📚\n"
                "- `name`: vlastný názov\n"
                "- `uzivatelia`: označ @mená všetkých, ktorých chceš pridať (oddelených medzerami)\n"
                "- `rola`: voliteľná rola, ktorá má mať prístup\n\n"
                "**Archivácia kanála:**\n"
                "Spusti príkaz `/archivuj_channel` v tom kanáli, ktorý chceš archivovať.\n"
                "Pridaj dôvod a dátum (napr. `2025_06`).\n"
                "Tvoja požiadavka bude odoslaná administrátorom, ktorí ju schvália alebo zamietnu."
            )

@bot.tree.command(name="zoznam_oznamov", description="Zobrazí všetky oznamy v databáze")
async def zoznam_oznamov(interaction: discord.Interaction):
    all_announcements = get_all_announcements()
    formatted = format_announcement_preview(all_announcements)
    await interaction.response.send_message(formatted if formatted else "Žiadne oznamy v databáze.")

@app_commands.command(name="uprav_oznam", description="Upraví oznam podľa ID")
@app_commands.describe(announcement_id="ID oznamu, ktorý chceš upraviť")
async def uprav_oznam(interaction: Interaction, announcement_id: int):
    ann = get_announcement_by_id(announcement_id)
    if not ann:
        await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
        return
    await interaction.response.send_modal(EditOznamModal(interaction.client, announcement_id, ann))

@app_commands.command(name="vymaz_oznam", description="Vymaže oznam podľa ID")
@app_commands.describe(announcement_id="ID oznamu, ktorý chceš vymazať")
async def vymaz_oznam(interaction: Interaction, announcement_id: int):
    ann = get_announcement_by_id(announcement_id)
    if not ann:
        await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
        return
    await interaction.response.send_message(f"Naozaj chceš vymazať oznam ID `{announcement_id}`?", view=DeleteConfirmView(announcement_id))

@app_commands.command(name="preview_oznam", description="Zobrazí náhľad oznamu podľa ID")
@app_commands.describe(announcement_id="ID oznamu na zobrazenie")
async def preview_oznam(interaction: Interaction, announcement_id: int):
    ann = get_announcement_by_id(announcement_id)
    if not ann:
        await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
        return
    embed = generate_oznam_embed(
        typ=ann["typ"],
        title=ann["title"],
        description=ann["description"],
        datetime=ann.get("datetime"),
        link=ann.get("link"),
        image=ann.get("image"),
        day=ann.get("day")
    )
    await interaction.response.send_message(embed=embed)

# Pomocná funkcia: kontrola, či sme v kanáli console
def only_in_command_channel():
    async def predicate(interaction: discord.Interaction):
        return interaction.channel.id == COMMAND_CHANNEL_ID
    return app_commands.check(predicate)
    
@bot.tree.command(name="nastav_reaction_emoji", description="Nastaví emoji, ktorý bude bot pridávať ako reakciu")
@app_commands.describe(emoji="Emoji (napr. <:3horky:1377264806905516053>)")
async def nastav_reaction_emoji(interaction: discord.Interaction, emoji: str):
    global REACTION_EMOJI
    if not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE):
        await interaction.response.send_message("Len admin môže meniť emoji reakcie.", ephemeral=True)
        return
    REACTION_EMOJI = emoji
    await interaction.response.send_message(f"Emoji reakcie nastavené na {emoji}.", ephemeral=True)

@bot.tree.command(name="pridaj_autoemoji_channel", description="Pridá channel do zoznamu, kde bot automaticky reaguje")
@app_commands.describe(channel="Channely, kde sa majú pridávať automatické reakcie o prečítaní.")
async def pridaj_autoemoji_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    author = interaction.user
    if not discord.utils.get(author.roles, name=ADMIN_ROLE):
        await interaction.response.send_message("Len admin môže meniť zoznam auto-emoji kanálov.", ephemeral=True)
        return
    AUTO_REACT_CHANNELS.add(channel.id)
    await interaction.response.send_message(f"Kanál {channel.mention} bol pridaný do auto-emoji zoznamu.", ephemeral=True)

@bot.tree.command(name="odober_autoemoji_channel", description="Odoberie channel zo zoznamu auto reakcií o prečítaní")
@app_commands.describe(channel="Kanál, z ktorého sa majú automatické reakcie o prečítaní odstrániť")
async def odober_autoemoji_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    author = interaction.user
    if not discord.utils.get(author.roles, name=ADMIN_ROLE):
        await interaction.response.send_message("Len admin môže meniť zoznam auto-emoji kanálov.", ephemeral=True)
        return
    AUTO_REACT_CHANNELS.discard(channel.id)
    await interaction.response.send_message(f"Kanál {channel.mention} bol odstránený zo zoznamu.", ephemeral=True)

@bot.tree.command(name="zoznam_autoemoji_channelov", description="Zobrazí zoznam channelov s automatickými reakciami")
async def zoznam_autoemoji_channelov(interaction: discord.Interaction):
    if not AUTO_REACT_CHANNELS:
        await interaction.response.send_message("Nie je nastavený žiadny kanál na automatické reakcie.", ephemeral=True)
        return
    guild = interaction.guild
    channels = [guild.get_channel(cid) for cid in AUTO_REACT_CHANNELS if guild.get_channel(cid)]
    response = "\n".join(f"- {channel.mention}" for channel in channels)
    await interaction.response.send_message("Kanály s automatickými reakciami:\n" + response, ephemeral=True)

@tasks.loop(minutes=10)
async def update_status():
    print("🌀 update_status loop beží...")
    if not os.path.exists(THOUGHTS_FILE):
        print("❌ Súbor thoughts.txt neexistuje.")
        return
    with open(THOUGHTS_FILE, "r", encoding="utf-8") as f:
        thoughts = [line.strip() for line in f if line.strip()]
    if thoughts:
        chosen = random.choice(thoughts)
        print(f"✅ Nastavujem status: \"{chosen}\"")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'"{chosen}"'))
    else:
        print("⚠️ Súbor thoughts.txt je prázdny.")
        
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if message.guild:
        if message.channel.id in AUTO_REACT_CHANNELS:
            await message.add_reaction(REACTION_EMOJI)
        elif bot.user.mentioned_in(message):
            await message.add_reaction(REACTION_EMOJI)
    else:
        # DM odpoveď
        if os.path.exists(THOUGHTS_FILE):
            with open(THOUGHTS_FILE, "r", encoding="utf-8") as f:
                thoughts = [line.strip() for line in f if line.strip()]
            if thoughts:
                await message.channel.send(f"Ahoj {message.author.display_name}!\n\n{random.choice(thoughts)}")


@bot.tree.command(name="vytvor_channel", description="Vytvorí súkromný kanál")
@app_commands.describe(
    emoji="Emoji pre názov kanála",
    name="Názov kanála",
    uzivatelia="Označ používateľov (oddelených medzerou)",
    rola="Voliteľná rola, ktorá bude mať prístup"
)
@only_in_command_channel()
async def vytvor_channel(
    interaction: discord.Interaction,
    emoji: str,
    name: str,
    uzivatelia: str,
    rola: discord.Role = None
):
    author = interaction.user
    guild = interaction.guild

    if not discord.utils.get(author.roles, name=AUTHORIZED_ROLE):
        await interaction.response.send_message("Nemáš oprávnenie na vytváranie kanálov.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(
            read_messages=True,
            manage_messages=True,
            manage_channels=True,
            manage_roles=True,
            view_channel=True
        ),
    }

    mentions = uzivatelia.split()
    for mention in mentions:
        if mention.startswith("<@") and mention.endswith(">"):
            user_id = int(mention.strip("<@!>"))
            member = guild.get_member(user_id)
            if member:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True)

    if rola:
        overwrites[rola] = discord.PermissionOverwrite(read_messages=True)

    category = guild.get_channel(CATEGORY_ID)
    channel_name = CHANNEL_NAME_TEMPLATE.format(emoji=emoji, name=name)

    channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
    await interaction.response.send_message(f"Kanál {channel.mention} bol vytvorený.", ephemeral=True)

@bot.event
async def setup_hook():
    how_to_channel = bot.get_channel(HOW_TO_CHANNEL_ID)
    if how_to_channel:
        await how_to_channel.send(
            "\U0001F4AC **Používanie bota**\n"
            "\n**Vytvorenie kanála:**\n"
            "Spusti príkaz `/vytvor_channel` v kanáli <#819184838274711582> a zadaj: \n"
            "- `emoji`: napr. \U0001F3EB alebo \U0001F4DA alebo ktorékoľvek iné, ktoré sa ti páči. \n"
            "- `name`: vlastný názov (na našom serveri namiesto medzier používame '_') \n"
            "- `uzivatelia`: označ @mená všetkých, ktorých chceš pridať (oddelených medzerami) \n"
            "- `rola`: voliteľná rola, ktorá má mať prístup\n"
            "\n**Archivácia kanála:**\n"
            "Spusti príkaz `/archivuj_channel` v tom kanáli, ktorý chceš archivovať.\n"
            "Pridaj dôvod a dátum (napr. `2025_06`).\n"
            "Tvoja požiadavka bude odoslaná administrátorom, ktorí ju schvália alebo zamietnu."
        )

@bot.tree.command(name="archivuj_channel", description="Archivuje aktuálny kanál")
@app_commands.describe(datum="Dátum archivácie vo formáte RRRR_MM alebo RRRR_MM_DD", dovod="Krátky dôvod archivácie")
async def archivuj_channel(interaction: discord.Interaction, datum: str, dovod: str):
    author = interaction.user
    guild = interaction.guild
    channel = interaction.channel
    mod_channel = guild.get_channel(MODERATOR_CHANNEL_ID)

    is_admin = discord.utils.get(author.roles, name=ADMIN_ROLE)
    is_team_mod = discord.utils.get(author.roles, name=AUTHORIZED_ROLE)

    if not is_admin and not is_team_mod:
        await interaction.response.send_message("Nemáš oprávnenie na archiváciu alebo označenie.", ephemeral=True)
        return

    if is_admin:
        parts = channel.name.split("・", 1)
        base_name = parts[1] if len(parts) == 2 else channel.name
        new_name = f"{datum}_{base_name}"

        archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)
        await channel.edit(name=new_name, category=archive_category, sync_permissions=True)
        await interaction.response.send_message(f"Kanál bol archivovaný ako `{new_name}`.", ephemeral=True)

        embed = discord.Embed(title="✅ Kanál archivovaný", color=0x2ecc71)
        embed.add_field(name="Kanál", value=channel.mention, inline=False)
        embed.add_field(name="Archivoval", value=author.mention, inline=True)
        embed.add_field(name="Dôvod", value=dovod, inline=False)
        await mod_channel.send(embed=embed)

    else:
        await interaction.response.send_message("Tvoj návrh na archiváciu bol odoslaný moderátorom.", ephemeral=True)

        embed = discord.Embed(title="⚠️ Označenie kanála na archiváciu", color=0xf39c12)
        embed.add_field(name="Kanál", value=channel.mention, inline=False)
        embed.add_field(name="Navrhovateľ", value=author.mention, inline=True)
        embed.add_field(name="Dôvod", value=dovod, inline=False)
        message = await mod_channel.send(embed=embed)
        await message.add_reaction(ARCHIVE_EMOJI)

        async def check(reaction, user):
            return (
                str(reaction.emoji) == ARCHIVE_EMOJI and
                user != bot.user and
                discord.utils.get(user.roles, name=ADMIN_ROLE)
            )

        async def wait_for_reaction():
            try:
                reaction, user = await bot.wait_for("reaction_add", check=check, timeout=86400)
                parts = channel.name.split("・", 1)
                base_name = parts[1] if len(parts) == 2 else channel.name
                new_name = f"{datum}_{base_name}"
                archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)
                await channel.edit(name=new_name, category=archive_category, sync_permissions=True)
                confirmation = discord.Embed(title="✅ Archivácia potvrdená", color=0x2ecc71)
                confirmation.add_field(name="Kanál", value=channel.mention, inline=False)
                confirmation.add_field(name="Archivoval", value=user.mention, inline=True)
                confirmation.add_field(name="Dôvod", value=f"Vyhovenie žiadosti na archiváciu od {author.mention}", inline=False)
                await mod_channel.send(embed=confirmation)
            except asyncio.TimeoutError:
                pass

        bot.loop.create_task(wait_for_reaction())


bot.run(os.getenv("DISCORD_TOKEN"))
