import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import cast
from config import AUTHORIZED_ROLE, ADMIN_ROLE, CATEGORY_ID, ARCHIVE_CATEGORY_ID, COMMAND_CHANNEL_ID, MODERATOR_CHANNEL_ID, CHANNEL_NAME_TEMPLATE, ARCHIVE_EMOJI

# Pomocná funkcia: kontrola, či sme v kanáli console
def only_in_command_channel():
    async def predicate(interaction: discord.Interaction):
        return interaction.channel is not None and interaction.channel.id == COMMAND_CHANNEL_ID
    return app_commands.check(predicate)

class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="vytvor_channel", description="Vytvorí súkromný kanál")
    @app_commands.describe(
        emoji="Emoji pre názov kanála",
        name="Názov kanála",
        uzivatelia="Označ používateľov (oddelených medzerou)",
        rola="Voliteľná rola, ktorá bude mať prístup"
    )
    @only_in_command_channel()
    async def vytvor_channel(
        self,
        interaction: discord.Interaction,
        emoji: str,
        name: str,
        uzivatelia: str,
        rola: discord.Role | None = None
    ):
        author = interaction.user
        guild = interaction.guild
        if not guild:
            return

        if not isinstance(author, discord.Member) or not discord.utils.get(author.roles, name=AUTHORIZED_ROLE):
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
                try:
                    user_id = int(mention.strip("<@!>"))
                    member = guild.get_member(user_id)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(read_messages=True)
                except ValueError:
                    pass

        if rola:
            overwrites[rola] = discord.PermissionOverwrite(read_messages=True)

        category = guild.get_channel(CATEGORY_ID)
        if category and not isinstance(category, discord.CategoryChannel):
            category = None # Or handle error
            
        channel_name = CHANNEL_NAME_TEMPLATE.format(emoji=emoji, name=name)

        # Cast category to CategoryChannel for type checker
        cat_arg = cast(discord.CategoryChannel, category) if category else None
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=cat_arg)
        await interaction.response.send_message(f"Kanál {channel.mention} bol vytvorený.", ephemeral=True)

    @app_commands.command(name="archivuj_channel", description="Archivuje aktuálny kanál")
    @app_commands.describe(datum="Dátum archivácie vo formáte RRRR_MM alebo RRRR_MM_DD", dovod="Krátky dôvod archivácie")
    async def archivuj_channel(self, interaction: discord.Interaction, datum: str, dovod: str):
        author = interaction.user
        guild = interaction.guild
        channel = interaction.channel
        
        if not guild or not channel or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Tento príkaz možno použiť len v textovom kanáli na serveri.", ephemeral=True)
            return

        mod_channel = guild.get_channel(MODERATOR_CHANNEL_ID)
        if not mod_channel or not isinstance(mod_channel, discord.TextChannel):
            await interaction.response.send_message("Moderátorský kanál nebol nájdený.", ephemeral=True)
            return

        if not isinstance(author, discord.Member):
            return

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
            if archive_category and isinstance(archive_category, discord.CategoryChannel):
                 await channel.edit(name=new_name, category=archive_category, sync_permissions=True)
                 await interaction.response.send_message(f"Kanál bol archivovaný ako `{new_name}`.", ephemeral=True)

                 embed = discord.Embed(title="✅ Kanál archivovaný", color=0x2ecc71)
                 embed.add_field(name="Kanál", value=channel.mention, inline=False)
                 embed.add_field(name="Archivoval", value=author.mention, inline=True)
                 embed.add_field(name="Dôvod", value=dovod, inline=False)
                 await mod_channel.send(embed=embed)
            else:
                 await interaction.response.send_message("Archívna kategória nebola nájdená.", ephemeral=True)

        else:
            await interaction.response.send_message("Tvoj návrh na archiváciu bol odoslaný moderátorom.", ephemeral=True)

            embed = discord.Embed(title="⚠️ Označenie kanála na archiváciu", color=0xf39c12)
            embed.add_field(name="Kanál", value=channel.mention, inline=False)
            embed.add_field(name="Navrhovateľ", value=author.mention, inline=True)
            embed.add_field(name="Dôvod", value=dovod, inline=False)
            message = await mod_channel.send(embed=embed)
            await message.add_reaction(ARCHIVE_EMOJI)

            def check(reaction, user):
                return (
                    str(reaction.emoji) == ARCHIVE_EMOJI and
                    user != self.bot.user and
                    isinstance(user, discord.Member) and
                    discord.utils.get(user.roles, name=ADMIN_ROLE) is not None
                )

            async def wait_for_reaction():
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=86400)
                    parts = channel.name.split("・", 1)
                    base_name = parts[1] if len(parts) == 2 else channel.name
                    new_name = f"{datum}_{base_name}"
                    archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)
                    if archive_category and isinstance(archive_category, discord.CategoryChannel):
                        await channel.edit(name=new_name, category=archive_category, sync_permissions=True)
                        confirmation = discord.Embed(title="✅ Archivácia potvrdená", color=0x2ecc71)
                        confirmation.add_field(name="Kanál", value=channel.mention, inline=False)
                        confirmation.add_field(name="Archivoval", value=user.mention, inline=True)
                        confirmation.add_field(name="Dôvod", value=f"Vyhovenie žiadosti na archiváciu od {author.mention}", inline=False)
                        await mod_channel.send(embed=confirmation)
                except asyncio.TimeoutError:
                    pass

            self.bot.loop.create_task(wait_for_reaction())

async def setup(bot):
    await bot.add_cog(Channels(bot))
