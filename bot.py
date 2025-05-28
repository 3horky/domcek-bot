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
AUTHORIZED_ROLE = "Team Mod"        # Meno roly oprávnenej vytvárať kanály
ADMIN_ROLE = "Admin"                   # Meno roly oprávnenej archivovať
CATEGORY_ID = 1231260260015149068       # ID kategórie, kde sa vytvárajú kanály
ARCHIVE_CATEGORY_ID = 1077174157416087602  # ID archívnej kategórie
CONSOLE_CHANNEL_ID = 1278324331683778722 # ID channelu console
MODERATOR_CHANNEL_ID = 1026422525464424519
CHANNEL_NAME_TEMPLATE = "{emoji}・{name}"
ARCHIVE_NAME_TEMPLATE = "{archived_date}_{name}"
ARCHIVE_EMOJI = "✅"  # ✅ emoji pre potvrdenie archivácie

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
def only_in_console():
    async def predicate(interaction: discord.Interaction):
        return interaction.channel.id == CONSOLE_CHANNEL_ID
    return app_commands.check(predicate)

class UserSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in guild.members if not member.bot
        ][:25]

        super().__init__(
            placeholder="Vyber používateľov, ktorým sa má udeliť prístup",
            min_values=1,
            max_values=min(25, len(options)),
            options=options,
            custom_id="user_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: UserSelectView = self.view
        await view.store_users(interaction, self.values)

class RoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        options = [
            discord.SelectOption(label=role.name, value=str(role.id))
            for role in guild.roles if not role.is_default()
        ][:25]

        super().__init__(
            placeholder="Vyber roly, ktorým sa má udeliť prístup",
            min_values=0,
            max_values=min(25, len(options)),
            options=options,
            custom_id="role_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: UserSelectView = self.view
        await view.finalize_channel(interaction, self.values)

class UserSelectView(discord.ui.View):
    def __init__(self, guild, emoji, name, author):
        super().__init__(timeout=300)
        self.guild = guild
        self.emoji = emoji
        self.name = name
        self.author = author
        self.selected_users = []
        self.user_select = UserSelect(guild)
        self.role_select = RoleSelect(guild)
        self.add_item(self.user_select)
        self.add_item(self.role_select)

    async def store_users(self, interaction: discord.Interaction, user_ids):
        self.selected_users = [self.guild.get_member(int(uid)) for uid in user_ids if self.guild.get_member(int(uid))]
        await interaction.response.send_message("Používatelia vybraní. Teraz vyber roly.", ephemeral=True)

    async def finalize_channel(self, interaction: discord.Interaction, role_ids):
        selected_roles = [self.guild.get_role(int(rid)) for rid in role_ids if self.guild.get_role(int(rid))]

        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.author: discord.PermissionOverwrite(
                read_messages=True,
                manage_messages=True,
                manage_channels=True,
                manage_roles=True,
                view_channel=True
            ),
        }

        for member in self.selected_users:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)

        for role in selected_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True)

        category = self.guild.get_channel(CATEGORY_ID)
        channel_name = CHANNEL_NAME_TEMPLATE.format(emoji=self.emoji, name=self.name)

        channel = await self.guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
        await interaction.response.edit_message(content=f"Kanál {channel.mention} bol vytvorený.", view=None)

@bot.tree.command(name="vytvor_channel", description="Vytvorí súkromný kanál s výberom používateľov a rolí")
@app_commands.describe(
    emoji="Emoji pre názov kanála",
    name="Názov kanála"
)
@only_in_console()
async def vytvor_channel(
    interaction: discord.Interaction,
    emoji: str,
    name: str
):
    author = interaction.user
    guild = interaction.guild

    if not discord.utils.get(author.roles, name=AUTHORIZED_ROLE):
        await interaction.response.send_message("Nemáš oprávnenie na vytváranie kanálov.", ephemeral=True)
        return

    view = UserSelectView(guild=guild, emoji=emoji, name=name, author=author)
    await interaction.response.send_message("Vyber používateľov a roly, ktorým chceš dať prístup:", view=view, ephemeral=True)


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
