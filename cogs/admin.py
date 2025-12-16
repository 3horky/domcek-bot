import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput, UserSelect, ChannelSelect
from config import ADMIN_ROLE
from oznamy_db import get_setting, set_setting
from utils import get_bot_version

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="carlo_admin", description="Otvorí administračný panel")
    async def carlo_admin(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not discord.utils.get(interaction.user.roles, name=ADMIN_ROLE):
            await interaction.response.send_message("Nemáš oprávnenie.", ephemeral=True)
            return
        
        embed = get_main_embed(self.bot)
        await interaction.response.send_message(embed=embed, view=MainAdminView(self.bot), ephemeral=True)

    @commands.command()
    @commands.has_role(ADMIN_ROLE)
    async def sync(self, ctx):
        """Synchronizuje slash príkazy"""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")

def get_main_embed(bot):
    embed = discord.Embed(title="⚙️ Carlo Admin Dashboard", color=discord.Color.blue())
    
    # Error Notifications
    error_users = get_setting("error_notification_users", [])
    embed.add_field(name="🔔 Upozornenia na chyby", value=f"{len(error_users)} nastavených používateľov", inline=True)
    
    # Auto-React
    react_channels = get_setting("auto_react_channels", [])
    embed.add_field(name="💬 Kanály pre auto-reakcie", value=f"{len(react_channels)} nastavených kanálov", inline=True)
    
    # General
    emoji = get_setting("reaction_emoji", "✅")
    schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
    schedule_active = get_setting("schedule_active", False)
    status_icon = "🟢" if schedule_active else "🔴"
    status_text = "Aktívny" if schedule_active else "Pozastavený"
    
    embed.add_field(name="Všeobecné nastavenia", value=f"Emoji: {emoji}\nRozvrh: {schedule.get('day')} o {schedule.get('time')}\nStav: {status_icon} {status_text}", inline=False)
    
    embed.set_footer(text=f"Verzia: {get_bot_version()}")
    return embed

class MainAdminView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🔔 Upozornenia na chyby", style=discord.ButtonStyle.primary, row=0)
    async def error_notifs(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="🔔 Nastavenia upozornení na chyby", color=discord.Color.red())
        current_users = get_setting("error_notification_users", [])
        
        user_list = []
        for uid in current_users:
            user = self.bot.get_user(uid)
            user_list.append(f"• {user.mention if user else f'Neznámy ({uid})'}")
            
        embed.description = "\n".join(user_list) if user_list else "Žiadni nastavení používatelia."
        
        await interaction.response.edit_message(embed=embed, view=ErrorConfigView(self.bot))

    @discord.ui.button(label="💬 Kanály pre auto-reakcie", style=discord.ButtonStyle.primary, row=0)
    async def auto_react(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="💬 Kanály pre auto-reakcie", color=discord.Color.green())
        current_channels = get_setting("auto_react_channels", [])
        
        channel_list = []
        for cid in current_channels:
            channel = self.bot.get_channel(cid)
            channel_list.append(f"• {channel.mention if channel else f'Neznámy ({cid})'}")
            
        embed.description = "\n".join(channel_list) if channel_list else "Žiadne nastavené kanály."
        
        await interaction.response.edit_message(embed=embed, view=AutoReactConfigView(self.bot))

    @discord.ui.button(label="⚙️ Všeobecné nastavenia", style=discord.ButtonStyle.secondary, row=1)
    async def general_config(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        emoji = get_setting("reaction_emoji", "✅")
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule_active = get_setting("schedule_active", False)
        status_icon = "🟢" if schedule_active else "🔴"
        status_text = "Aktívny" if schedule_active else "Pozastavený"
        
        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

class ErrorConfigView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.current_users = get_setting("error_notification_users", [])
        
        self.add_item(AddUserSelect(bot))
        
        if self.current_users:
            self.add_item(RemoveUserSelect(bot, self.current_users))

    @discord.ui.button(label="🔙 Späť", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=get_main_embed(self.bot), view=MainAdminView(self.bot))

class AddUserSelect(UserSelect):
    def __init__(self, bot):
        super().__init__(placeholder="Pridať používateľa...", min_values=1, max_values=5, row=0)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_users = get_setting("error_notification_users", [])
        new_users = []
        
        for user in self.values:
            if user.id not in current_users:
                current_users.append(user.id)
                new_users.append(user)
        
        set_setting("error_notification_users", current_users)
        
        for user in new_users:
            try:
                await user.send("Odteraz budeš dostávať upozornenia na chyby bota. Ak si myslíš, že je to chyba, kontaktuj administrátora.")
            except:
                pass
        
        # Refresh view
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            user_list = []
            for uid in current_users:
                user = self.bot.get_user(uid)
                user_list.append(f"• {user.mention if user else f'Neznámy ({uid})'}")
            embed.description = "\n".join(user_list) if user_list else "Žiadni nastavení používatelia."
            
            await interaction.response.edit_message(embed=embed, view=ErrorConfigView(self.bot))
        else:
            await interaction.response.edit_message(content="✅ Používatelia pridaní.", view=ErrorConfigView(self.bot))

class RemoveUserSelect(Select):
    def __init__(self, bot, current_users):
        options = []
        for uid in current_users:
            user = bot.get_user(uid)
            label = user.name if user else f"Unknown User ({uid})"
            options.append(discord.SelectOption(label=label, value=str(uid)))
        super().__init__(placeholder="Odobrať používateľa...", options=options[:25], row=1)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_users = get_setting("error_notification_users", [])
        for val in self.values:
            uid = int(val)
            if uid in current_users:
                current_users.remove(uid)
        
        set_setting("error_notification_users", current_users)
        
        # Refresh view
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            user_list = []
            for uid in current_users:
                user = self.bot.get_user(uid)
                user_list.append(f"• {user.mention if user else f'Neznámy ({uid})'}")
            embed.description = "\n".join(user_list) if user_list else "Žiadni nastavení používatelia."

            await interaction.response.edit_message(embed=embed, view=ErrorConfigView(self.bot))
        else:
            await interaction.response.edit_message(content="✅ Používatelia odobratí.", view=ErrorConfigView(self.bot))

class AutoReactConfigView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.current_channels = get_setting("auto_react_channels", [])
        
        self.add_item(AddChannelSelect(bot))
        
        if self.current_channels:
            self.add_item(RemoveChannelSelect(bot, self.current_channels))

    @discord.ui.button(label="🔙 Späť", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=get_main_embed(self.bot), view=MainAdminView(self.bot))

class AddChannelSelect(ChannelSelect):
    def __init__(self, bot):
        super().__init__(placeholder="Pridať kanál...", channel_types=[discord.ChannelType.text], min_values=1, max_values=5, row=0)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_channels = get_setting("auto_react_channels", [])
        
        for channel in self.values:
            if channel.id not in current_channels:
                current_channels.append(channel.id)
        
        set_setting("auto_react_channels", current_channels)
        self.bot.auto_react_channels = set(current_channels)
        
        # Refresh view
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            channel_list = []
            for cid in current_channels:
                channel = self.bot.get_channel(cid)
                channel_list.append(f"• {channel.mention if channel else f'Neznámy ({cid})'}")
            embed.description = "\n".join(channel_list) if channel_list else "Žiadne nastavené kanály."

            await interaction.response.edit_message(embed=embed, view=AutoReactConfigView(self.bot))
        else:
            await interaction.response.edit_message(content="✅ Kanály pridané.", view=AutoReactConfigView(self.bot))

class RemoveChannelSelect(Select):
    def __init__(self, bot, current_channels):
        options = []
        for cid in current_channels:
            channel = bot.get_channel(cid)
            label = channel.name if channel else f"Unknown Channel ({cid})"
            options.append(discord.SelectOption(label=label, value=str(cid)))
        super().__init__(placeholder="Odobrať kanál...", options=options[:25], row=1)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_channels = get_setting("auto_react_channels", [])
        for val in self.values:
            cid = int(val)
            if cid in current_channels:
                current_channels.remove(cid)
        
        set_setting("auto_react_channels", current_channels)
        self.bot.auto_react_channels = set(current_channels)
        
        # Refresh view
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            channel_list = []
            for cid in current_channels:
                channel = self.bot.get_channel(cid)
                channel_list.append(f"• {channel.mention if channel else f'Neznámy ({cid})'}")
            embed.description = "\n".join(channel_list) if channel_list else "Žiadne nastavené kanály."

            await interaction.response.edit_message(embed=embed, view=AutoReactConfigView(self.bot))
        else:
            await interaction.response.edit_message(content="✅ Kanály odobraté.", view=AutoReactConfigView(self.bot))

class GeneralConfigView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        # Update button label based on current state
        schedule_active = get_setting("schedule_active", False)
        self.toggle_schedule.label = "⏸️ Pozastaviť rozvrh" if schedule_active else "▶️ Aktivovať rozvrh"
        self.toggle_schedule.style = discord.ButtonStyle.danger if schedule_active else discord.ButtonStyle.success

    @discord.ui.button(label="Zmeniť Emoji", style=discord.ButtonStyle.primary, row=0)
    async def change_emoji(self, interaction: discord.Interaction, button: Button):
        # Try to ensure we have the latest emojis for this guild
        if interaction.guild:
            try:
                await interaction.guild.fetch_emojis()
            except:
                pass
        
        embed = discord.Embed(title="Vyber zdroj emoji", description="Vyber **vlastný emoji** zo zoznamu nižšie.\nPre štandardné emoji (napr. ✅), použi tlačidlo 'Zadať manuálne'.", color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=EmojiPickerView(self.bot, interaction.guild))

    @discord.ui.button(label="Nastaviť Rozvrh", style=discord.ButtonStyle.primary, row=0)
    async def set_schedule(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="Nastavenie rozvrhu", description="Vyber deň v týždni a nastav čas publikovania.", color=discord.Color.gold())
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        embed.add_field(name="Aktuálne nastavenie", value=f"{schedule.get('day')} o {schedule.get('time')}")
        
        await interaction.response.edit_message(embed=embed, view=ScheduleConfigView(self.bot))

    @discord.ui.button(label="▶️ Aktivovať rozvrh", style=discord.ButtonStyle.success, row=1)
    async def toggle_schedule(self, interaction: discord.Interaction, button: Button):
        current_state = get_setting("schedule_active", False)
        new_state = not current_state
        set_setting("schedule_active", new_state)
        
        # Refresh view
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        emoji = get_setting("reaction_emoji", "✅")
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        status_icon = "🟢" if new_state else "🔴"
        status_text = "Aktívny" if new_state else "Pozastavený"
        
        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

    @discord.ui.button(label="🔙 Späť", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=get_main_embed(self.bot), view=MainAdminView(self.bot))

class EmojiPickerView(View):
    def __init__(self, bot, guild):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild = guild
        
        # Use bot.emojis to get all emojis the bot can see
        emojis = list(bot.emojis)
        print(f"DEBUG: Found {len(emojis)} emojis in cache.")
        
        if emojis:
            # We can only show 25 options in a select menu.
            # Prioritize emojis from the current guild if possible
            guild_emojis = [e for e in emojis if e.guild_id == guild.id] if guild else []
            other_emojis = [e for e in emojis if e not in guild_emojis]
            
            display_emojis = (guild_emojis + other_emojis)[:25]
            
            self.add_item(GuildEmojiSelect(bot, display_emojis))
        else:
            # Add a disabled placeholder if no emojis found
            self.add_item(Select(placeholder="Nenašli sa žiadne vlastné emoji (Bot nie je na žiadnom serveri s emoji)", disabled=True, options=[discord.SelectOption(label="None", value="none")]))
        
    @discord.ui.button(label="Zadať manuálne / Unicode", style=discord.ButtonStyle.primary, row=1)
    async def manual_input(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ChangeEmojiModal(self.bot))

    @discord.ui.button(label="🔙 Späť", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        emoji = get_setting("reaction_emoji", "✅")
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule_active = get_setting("schedule_active", False)
        status_icon = "🟢" if schedule_active else "🔴"
        status_text = "Aktívny" if schedule_active else "Pozastavený"

        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

class GuildEmojiSelect(Select):
    def __init__(self, bot, emojis):
        options = []
        for emoji in emojis:
            # Ensure label is within limits (100 chars)
            label = emoji.name[:100] if emoji.name else "Unnamed Emoji"
            options.append(discord.SelectOption(label=label, value=str(emoji), emoji=emoji))
        
        super().__init__(placeholder="Vyber emoji...", options=options, row=0)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        emoji = self.values[0]
        set_setting("reaction_emoji", emoji)
        self.bot.reaction_emoji = emoji
        
        # Return to General Config
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule_active = get_setting("schedule_active", False)
        status_icon = "🟢" if schedule_active else "🔴"
        status_text = "Aktívny" if schedule_active else "Pozastavený"

        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

class ChangeEmojiModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Zmeniť Reaction Emoji")
        self.bot = bot
        self.emoji_input = TextInput(label="Nový Emoji", placeholder="Vlož emoji sem (napr. ✅ alebo vlastný)", min_length=1)
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction: discord.Interaction):
        emoji = self.emoji_input.value.strip()
        set_setting("reaction_emoji", emoji)
        self.bot.reaction_emoji = emoji
        
        # Refresh view
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule_active = get_setting("schedule_active", False)
        status_icon = "🟢" if schedule_active else "🔴"
        status_text = "Aktívny" if schedule_active else "Pozastavený"

        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

class ScheduleConfigView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(DaySelect(bot))

    @discord.ui.button(label="Nastaviť čas", style=discord.ButtonStyle.primary, row=1)
    async def set_time(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SetTimeModal(self.bot))

    @discord.ui.button(label="🔙 Späť", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="⚙️ Všeobecné nastavenia", color=discord.Color.gold())
        emoji = get_setting("reaction_emoji", "✅")
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule_active = get_setting("schedule_active", False)
        status_icon = "🟢" if schedule_active else "🔴"
        status_text = "Aktívny" if schedule_active else "Pozastavený"

        embed.add_field(name="Aktuálny Emoji", value=emoji, inline=True)
        embed.add_field(name="Aktuálny rozvrh", value=f"{schedule.get('day')} o {schedule.get('time')}", inline=True)
        embed.add_field(name="Stav rozvrhu", value=f"{status_icon} {status_text}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=GeneralConfigView(self.bot))

class DaySelect(Select):
    def __init__(self, bot):
        options = [
            discord.SelectOption(label="Pondelok", value="Monday"),
            discord.SelectOption(label="Utorok", value="Tuesday"),
            discord.SelectOption(label="Streda", value="Wednesday"),
            discord.SelectOption(label="Štvrtok", value="Thursday"),
            discord.SelectOption(label="Piatok", value="Friday"),
            discord.SelectOption(label="Sobota", value="Saturday"),
            discord.SelectOption(label="Nedeľa", value="Sunday"),
        ]
        super().__init__(placeholder="Vyber deň v týždni...", options=options, row=0)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        day = self.values[0]
        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule["day"] = day
        set_setting("publish_schedule", schedule)
        
        # Refresh view
        if interaction.message:
            embed = interaction.message.embeds[0]
            embed.set_field_at(0, name="Aktuálne nastavenie", value=f"{schedule.get('day')} o {schedule.get('time')}")
            await interaction.response.edit_message(embed=embed, view=ScheduleConfigView(self.bot))

class SetTimeModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Nastaviť čas publikovania")
        self.bot = bot
        self.time_input = TextInput(label="Čas (HH:MM)", placeholder="napr. 18:00", min_length=5, max_length=5)
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        time_val = self.time_input.value
        # Basic validation
        try:
            import time
            time.strptime(time_val, '%H:%M')
        except ValueError:
             await interaction.response.send_message("❌ Neplatný formát času. Použi HH:MM (napr. 18:00).", ephemeral=True)
             return

        schedule = get_setting("publish_schedule", {"day": "Nenastavené", "time": "Nenastavené"})
        schedule["time"] = time_val
        set_setting("publish_schedule", schedule)
        
        # Refresh view
        embed = discord.Embed(title="Nastavenie rozvrhu", description="Vyber deň v týždni a nastav čas publikovania.", color=discord.Color.gold())
        embed.add_field(name="Aktuálne nastavenie", value=f"{schedule.get('day')} o {schedule.get('time')}")
        
        await interaction.response.edit_message(embed=embed, view=ScheduleConfigView(self.bot))

async def setup(bot):
    await bot.add_cog(Admin(bot))
