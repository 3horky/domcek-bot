import discord
import os
import asyncio

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

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
COMMAND_CHANNEL_ID = 819184838274711582  # zadaj ID channelu kde sa používajú príkazy
HOW_TO_CHANNEL_ID = 1278324331683778722  # pôvodný console channel, teraz how_to
MODERATOR_CHANNEL_ID = 1026422525464424519
CHANNEL_NAME_TEMPLATE = "{emoji}・{name}"
ARCHIVE_NAME_TEMPLATE = "{archived_date}_{name}"
ARCHIVE_EMOJI = "✅"

async def keep_alive_loop():  # Aby Google nevypol VM pre nečinnosť
    while True:
        print("Heartbeat - bot je nažive")
        await asyncio.sleep(300)  # každých 5 minút

@bot.event
async def on_ready():
    print(f"Bot prihlásený ako {bot.user}")
    bot.loop.create_task(keep_alive_loop())

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# Pomocná funkcia: kontrola, či sme v kanáli console
def only_in_command_channel():
    async def predicate(interaction: discord.Interaction):
        return interaction.channel.id == COMMAND_CHANNEL_ID
    return app_commands.check(predicate)

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
