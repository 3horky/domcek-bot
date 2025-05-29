import discord
import os
import asyncio
import random
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from oznamy_db import init_db
from discord.ui import View, Button, Modal, TextInput

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

def generate_oznam_embed(typ, title, description, datetime=None, day=None, link=None, image=None):
    embed = discord.Embed(description=description)

    if typ == "event" and datetime and day:
        embed.set_author(name=datetime, icon_url=EMOJI_BY_DAY.get(day.lower(), ""))
        embed.title = title
        embed.color = discord.Color.blue()

    elif typ == "info" and image:
        embed.set_thumbnail(url=image)
        embed.title = f"🔗 {title}" if link else title
        if link:
            embed.url = link
        embed.color = discord.Color.green()

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

class EventOznamModal(Modal, title="Nový event oznam"):
    def __init__(self, bot, title_default="", description_default="", datetime_default="", day_default=""):
        super().__init__()
        self.bot = bot

        self.title = TextInput(label="Názov", default=title_default)
        self.description = TextInput(label="Popis", style=discord.TextStyle.paragraph, default=description_default)
        self.datetime = TextInput(label="Dátum a čas", placeholder="15.06. // 18:00", default=datetime_default)
        self.day = TextInput(label="Deň v týždni", placeholder="napr. piatok", default=day_default)

        self.add_item(self.title)
        self.add_item(self.description)
        self.add_item(self.datetime)
        self.add_item(self.day)

    async def on_submit(self, interaction: discord.Interaction):
        embed = generate_oznam_embed(
            typ="event",
            title=self.title.value,
            description=self.description.value,
            datetime=self.datetime.value,
            day=self.day.value,
            link=None,
            image=None
        )
        view = OznamConfirmView(self.bot, data={
            "typ": "event",
            "title": self.title.value,
            "description": self.description.value,
            "datetime": self.datetime.value,
            "day": self.day.value,
            "link": None,
            "image": None
        })
        await interaction.response.send_message(embed=embed, ephemeral=True)

class InfoOznamModal(Modal, title="Nový info oznam"):
    def __init__(self, bot, title_default="", description_default="", image_default="", link_default=""):
        super().__init__()
        self.bot = bot

        self.title = TextInput(label="Názov", default=title_default)
        self.description = TextInput(label="Popis", style=discord.TextStyle.paragraph, default=description_default)
        self.image = TextInput(label="URL obrázka", default=image_default)
        self.link = TextInput(label="Link (voliteľný)", required=False, default=link_default)

        self.add_item(self.title)
        self.add_item(self.description)
        self.add_item(self.image)
        self.add_item(self.link)

    async def on_submit(self, interaction: discord.Interaction):
        embed = generate_oznam_embed(
            typ="info",
            title=self.title.value,
            description=self.description.value,
            datetime=None,
            day=None,
            link=self.link.value or None,
            image=self.image.value
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class OznamConfirmView(View):
    def __init__(self, bot, data):
        super().__init__(timeout=300)
        self.bot = bot
        self.data = data

    @discord.ui.button(label="✅ Pridať", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Oznam bol uložený ✅", embed=None, view=None)

    @discord.ui.button(label="❌ Zrušiť", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Zrušené.", embed=None, view=None)

    @discord.ui.button(label="✏️ Upraviť", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: Button):
        typ = self.data.get("typ", "event")

        if typ == "event":
            await interaction.response.send_modal(EventOznamModal(
                bot=self.bot,
                title_default=self.data.get("title", ""),
                description_default=self.data.get("description", ""),
                datetime_default=self.data.get("datetime", ""),
                day_default=self.data.get("day", "")
            ))
        else:
            await interaction.response.send_modal(InfoOznamModal(
                bot=self.bot,
                title_default=self.data.get("title", ""),
                description_default=self.data.get("description", ""),
                image_default=self.data.get("image", ""),
                link_default=self.data.get("link", "")
            ))

class OznamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pridaj_oznam", description="Pridá nový oznam (event alebo info)")
    @app_commands.describe(typ="Typ oznamu: event alebo info")
    async def pridaj_oznam(self, interaction: discord.Interaction, typ: str):
        if typ.lower() not in ["event", "info"]:
            await interaction.response.send_message("Typ musí byť `event` alebo `info`.", ephemeral=True)
            return

        if typ.lower() == "event":
            await interaction.response.send_modal(EventOznamModal(self.bot))
        else:
            await interaction.response.send_modal(InfoOznamModal(self.bot))

    def generate_oznam_embed(self, typ, title, description, datetime, link, image):
        embed = discord.Embed(description=description)
        if typ.lower() == "event" and datetime:
            embed.set_author(name=datetime, icon_url=self.get_day_icon(datetime))
        if link:
            embed.title = f"🔗 {title}"
            embed.url = link
        else:
            embed.title = title
        if typ.lower() == "general" and image:
            embed.set_thumbnail(url=image)
        return embed

    def get_day_icon(self, datetime_str):
        for key, url in EMOJI_BY_DAY.items():
            if key in datetime_str.lower():
                return url
        return ""

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
    await bot.add_cog(OznamCog(bot))

    
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
