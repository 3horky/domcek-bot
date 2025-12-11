import discord
import os
import asyncio
import traceback
import io
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from oznamy_db import init_db, get_setting
from config import HOW_TO_CHANNEL_ID, REACTION_EMOJI, COMMAND_CHANNEL_ID

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

class DomcekBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.reaction_emoji = REACTION_EMOJI
        self.auto_react_channels = set()

    async def setup_hook(self):
        self.tree.on_error = self.on_tree_error
        # Load extensions
        extensions = ['cogs.announcements', 'cogs.admin', 'cogs.channels', 'cogs.general']
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension: {ext}")
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await self.handle_error(error, interaction)

    async def on_command_error(self, ctx, error):
        await self.handle_error(error, ctx)

    async def handle_error(self, error, ctx_or_interaction):
        # Print to console
        traceback.print_exception(type(error), error, error.__traceback__)
        
        # Get admins to notify
        admin_ids = get_setting("error_notification_users", [])
        if not admin_ids:
            return

        # Format error
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        
        embed = discord.Embed(
            title="⚠️ Bot Error Occurred",
            description=f"An error occurred.",
            color=discord.Color.red()
        )
        if hasattr(ctx_or_interaction, 'command') and ctx_or_interaction.command:
             embed.description = f"An error occurred in command `{ctx_or_interaction.command.name}`."
        
        embed.add_field(name="Error", value=str(error)[:1024], inline=False)
        
        # Send DMs
        for user_id in admin_ids:
            try:
                user = await self.fetch_user(user_id)
                if user:
                    # Create a fresh file object for each send to avoid closed file issues
                    file = discord.File(io.BytesIO(tb_str.encode("utf-8")), filename="traceback.txt")
                    await user.send(embed=embed, file=file)
            except Exception as e:
                print(f"Failed to send error DM to {user_id}: {e}")

        # Notify user if interaction
        if isinstance(ctx_or_interaction, discord.Interaction):
            try:
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message("❌ An internal error occurred. The admins have been notified.", ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send("❌ An internal error occurred. The admins have been notified.", ephemeral=True)
            except Exception:
                pass

    async def on_ready(self):
        print(f"Bot prihlásený ako {self.user}")
        init_db()
        
        # Load settings from DB
        self.reaction_emoji = get_setting("reaction_emoji", REACTION_EMOJI)
        self.auto_react_channels = set(get_setting("auto_react_channels", []))
        
        # Keep alive loop
        self.loop.create_task(self.keep_alive_loop())

        try:
            print("====== on_ready() spustený ======")
            # Sync commands globally (or per guild for faster dev)
            # It's often better to have a manual sync command, but for this refactor we keep it here or rely on the admin sync command
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(e)

        # Check and send help message
        how_to_channel = self.get_channel(HOW_TO_CHANNEL_ID)
        if how_to_channel and isinstance(how_to_channel, discord.TextChannel):
            try:
                history = [msg async for msg in how_to_channel.history(limit=10)]
                if not any("Používanie bota" in msg.content for msg in history if msg.author == self.user):
                    await how_to_channel.send(
                        "📬 **Používanie bota**\n\n"
                        "**Vytvorenie kanála:**\n"
                        f"Spusti príkaz `/vytvor_channel` v kanáli <#{COMMAND_CHANNEL_ID}> a zadaj:\n"
                        "- `emoji`: napr. 🏫 alebo 📚\n"
                        "- `name`: vlastný názov\n"
                        "- `uzivatelia`: označ @mená všetkých, ktorých chceš pridať (oddelených medzerami)\n"
                        "- `rola`: voliteľná rola, ktorá má mať prístup\n\n"
                        "**Archivácia kanála:**\n"
                        "Spusti príkaz `/archivuj_channel` v tom kanáli, ktorý chceš archivovať.\n"
                        "Pridaj dôvod a dátum (napr. `2025_06`).\n"
                        "Tvoja požiadavka bude odoslaná administrátorom, ktorí ju schvália alebo zamietnu."
                    )
            except Exception as e:
                print(f"Error sending help message: {e}")

    async def keep_alive_loop(self):
        while True:
            print("Heartbeat - bot je nažive")
            await asyncio.sleep(300)

bot = DomcekBot()

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ DISCORD_TOKEN not found in environment variables.")
