import discord
import os
import random
from discord.ext import commands, tasks
from config import THOUGHTS_FILE, REACTION_EMOJI

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_status.start()

    async def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(minutes=10)
    async def update_status(self):
        await self.bot.wait_until_ready()
        print("🌀 update_status loop beží...")
        if not os.path.exists(THOUGHTS_FILE):
            print("❌ Súbor thoughts.txt neexistuje.")
            return
        with open(THOUGHTS_FILE, "r", encoding="utf-8") as f:
            thoughts = [line.strip() for line in f if line.strip()]
        if thoughts:
            chosen = random.choice(thoughts)
            print(f"✅ Nastavujem status: \"{chosen}\"")
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'"{chosen}"'))
        else:
            print("⚠️ Súbor thoughts.txt je prázdny.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Auto-reaction logic
        # Check if auto_react_channels exists on bot, if not initialize it
        if not hasattr(self.bot, "auto_react_channels"):
            self.bot.auto_react_channels = set()

        # Get reaction emoji from bot instance or default
        reaction_emoji_str = getattr(self.bot, "reaction_emoji", REACTION_EMOJI)
        
        try:
            emoji = discord.PartialEmoji.from_str(reaction_emoji_str)
        except:
            emoji = reaction_emoji_str

        if message.guild:
            if message.channel.id in self.bot.auto_react_channels:
                try:
                    await message.add_reaction(emoji)
                except:
                    pass
            elif self.bot.user and self.bot.user in message.mentions:
                try:
                    await message.add_reaction(emoji)
                except:
                    pass
        else:
            # DM odpoveď
            if os.path.exists(THOUGHTS_FILE):
                with open(THOUGHTS_FILE, "r", encoding="utf-8") as f:
                    thoughts = [line.strip() for line in f if line.strip()]
                if thoughts:
                    await message.channel.send(f"Ahoj {message.author.display_name}!\n\n{random.choice(thoughts)}")

async def setup(bot):
    await bot.add_cog(General(bot))
