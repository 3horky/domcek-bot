import discord
import os
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, time, timedelta
from google import genai
from oznamy_db import add_announcement, get_all_announcements, get_announcement_by_id, delete_announcement_by_id, update_announcement_by_id, delete_expired_announcements, get_setting
from config import MONTH_COLORS, OZNAMY_CHANNEL_ID
from utils import get_next_saturday_at_10, format_announcement_preview, generate_announcement_embeds_for_date, generate_oznam_embed, get_next_friday_and_thursday, format_date

class ConfirmPostNowView(View):
    def __init__(self, bot, cog):
        super().__init__(timeout=60)
        self.bot = bot
        self.cog = cog

    @discord.ui.button(label="✅ Uverejniť oznamy", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Uverejňujem oznamy...", view=None)
        
        success, msg = await self.cog.publish_announcements()
        
        if success:
            await interaction.followup.send("✅ Oznamy boli uverejnené.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ {msg}", ephemeral=True)

    @discord.ui.button(label="❌ Zrušiť", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Zverejnenie oznamov zrušené.", view=None)

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

class EditOznamModal(Modal):
    def __init__(self, bot, announcement_id, announcement):
        super().__init__(title="Uprav oznam")
        self.bot = bot
        self.announcement_id = announcement_id
        self.typ = announcement["typ"]
        
        self.title_input = TextInput(label="Názov", default=announcement["title"])
        self.description_input = TextInput(label="Popis", style=discord.TextStyle.paragraph, default=announcement["description"])
        self.visible_input = TextInput(label="Zobrazovať od - do", default=f"{announcement['visible_from']} - {announcement['visible_to']}")
        
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.visible_input)
        
        if self.typ == "event":
            self.datetime_input = TextInput(label="Dátum a čas", default=announcement.get("datetime", ""))
            self.day_input = TextInput(label="Deň", default=announcement.get("day", ""))
            self.add_item(self.datetime_input)
            self.add_item(self.day_input)
        else:
            self.image_input = TextInput(label="Obrázok URL", default=announcement.get("image", ""))
            self.link_input = TextInput(label="Link", default=announcement.get("link", ""))
            self.add_item(self.image_input)
            self.add_item(self.link_input)

    async def on_submit(self, interaction: Interaction):
        data = {
            "typ": self.typ,
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

        light_color, dark_color = MONTH_COLORS.get(datetime.now().month, (0xDDDDDD, 0x999999))
        embed_color = light_color if self.typ == "info" else dark_color

        embed = generate_oznam_embed(
            typ=self.typ,
            title=data["title"],
            description=data["description"],
            datetime_str=data.get("datetime"),
            link=data.get("link"),
            image=data.get("image"),
            day=data.get("day"),
            oznam_color=embed_color
        )
        await interaction.response.send_message(f"✅ Oznam bol upravený.", embed=embed)

class EventOznamModal(Modal):
    def __init__(self, bot, title="", description="", datetime="", day="", visible_dates=""):
        super().__init__(title="Nový event oznam")
        self.bot = bot
        
        self.title_input = TextInput(label="Názov oznamu", default=title)
        self.description_input = TextInput(label="Popis oznamu", style=discord.TextStyle.paragraph, default=description)
        self.datetime_input = TextInput(label="Dátum a čas (napr. 15.06. // 18:00)", default=datetime)
        self.day_input = TextInput(label="Deň v týždni (napr. piatok)", default=day)
        
        default_range = visible_dates or self._default_visible_range()
        self.visible_input = TextInput(label="Zobrazovať od kedy - do kedy", default=default_range)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.datetime_input)
        self.add_item(self.day_input)
        self.add_item(self.visible_input)

    def _default_visible_range(self):
        start, end = get_next_friday_and_thursday()
        return f"{format_date(start)} - {format_date(end)}"

    async def on_submit(self, interaction: discord.Interaction):
        title = self.title_input.value
        description = self.description_input.value
        datetime_str = self.datetime_input.value
        day = self.day_input.value
        visible_range = self.visible_input.value

        light_color, dark_color = MONTH_COLORS.get(datetime.now().month, (0xDDDDDD, 0x999999))
        
        embed = generate_oznam_embed("event", title, description, datetime_str, None, None, day, dark_color)
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

class InfoOznamModal(Modal):
    def __init__(self, bot, title="", description="", image="", link="", visible_dates=""):
        super().__init__(title="Nový info oznam")
        self.bot = bot
        
        self.title_input = TextInput(label="Názov oznamu", default=title)
        self.description_input = TextInput(label="Popis oznamu", style=discord.TextStyle.paragraph, default=description)
        self.image_input = TextInput(label="URL obrázka", default=image)
        self.link_input = TextInput(label="Link (voliteľné)", default=link, required=False)
        
        default_range = visible_dates or self._default_visible_range()
        self.visible_input = TextInput(label="Zobrazovať od kedy - do kedy", default=default_range)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.image_input)
        self.add_item(self.link_input)
        self.add_item(self.visible_input)

    def _default_visible_range(self):
        start, end = get_next_friday_and_thursday()
        return f"{format_date(start)} - {format_date(end)}"

    async def on_submit(self, interaction: discord.Interaction):
        title = self.title_input.value
        description = self.description_input.value
        image = self.image_input.value
        link = self.link_input.value
        visible_range = self.visible_input.value

        light_color, dark_color = MONTH_COLORS.get(datetime.now().month, (0xDDDDDD, 0x999999))
        
        embed = generate_oznam_embed("info", title, description, None, link, image, None, light_color)
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
        if interaction.message:
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

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clean_expired_announcements_task.start()
        self.schedule_loop.start()

    async def cog_unload(self):
        self.clean_expired_announcements_task.cancel()
        self.schedule_loop.cancel()

    @tasks.loop(time=time(hour=1, minute=0))
    async def clean_expired_announcements_task(self):
        print("[🕐] Spúšťam čistenie databázy...")
        delete_expired_announcements()
        print("[✅] V databáze boli vymazané expirované oznamy.")

    @tasks.loop(minutes=1)
    async def schedule_loop(self):
        await self.bot.wait_until_ready()
        
        # Check if schedule is active
        if not get_setting("schedule_active", False):
            return

        now = datetime.now()
        schedule = get_setting("publish_schedule", {"day": "Not set", "time": "Not set"})
        
        if schedule["day"] == "Not set" or schedule["time"] == "Not set":
            return

        # --- Publishing Logic ---
        # Check if today is the day and time matches
        # Assuming schedule["day"] is English day name (e.g. "Friday")
        if now.strftime("%A") == schedule["day"] and now.strftime("%H:%M") == schedule["time"]:
            print(f"[📅] Auto-publishing announcements (Schedule: {schedule['day']} {schedule['time']})")
            await self.publish_announcements()

        # --- Reminder Logic ---
        # Reminder is sent the day BEFORE at 20:00
        # Calculate day before
        days_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        target_day_int = days_map.get(schedule["day"])
        if target_day_int is not None:
            reminder_day_int = (target_day_int - 1) % 7
            
            if now.weekday() == reminder_day_int and now.strftime("%H:%M") == "20:00":
                print(f"[🔔] Sending announcement reminder (Target: {schedule['day']})")
                await self.send_reminder(schedule["time"])

    async def publish_announcements(self):
        """Publishes announcements to the configured channel. Returns (success, message)."""
        today = datetime.now()
        embeds = generate_announcement_embeds_for_date(today)

        if not embeds:
            return False, "Dnes nemáme žiadne oznamy na zverejnenie."

        light_color, _ = MONTH_COLORS.get(today.month, (0xDDDDDD, 0x999999))
        
        reaction_emoji_str = getattr(self.bot, "reaction_emoji", "✅")
        try:
            emoji = discord.PartialEmoji.from_str(reaction_emoji_str)
        except:
            emoji = reaction_emoji_str
        
        closing_embed = discord.Embed(
            title=f"Ak si si prečítal(a) oznamy, nezabudni dať  {reaction_emoji_str}",
            color=light_color
        )

        channel = self.bot.get_channel(OZNAMY_CHANNEL_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            return False, "Kanál #oznamy neexistuje alebo nie je textový kanál."

        try:
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents="Napíš 3-5 vetový pozdrav a úvod k správe plnej informácii a aktuálnych oznamov. Prihováraš sa 200 mladým ľuďom. Ak by ti to bolo treba kvôli správnej formulácii, si mužského rodu. Namiesto 'všetci' a ekvivalentov oslovuj @everyone. Po oslovení urob nový riadok. Na každý ďalší takýto prompt odpovedz originálnou správou. Môžeš používať emoji. Ak sa v správe odkazuješ k aktuálnemu obdobiu (sviatky, mesiace, výročia, dni), ubezpeč sa, že to zodpovedá aktuálnemu dátumu."
            )
            header = (response.text or "") + "\n⇣"
        except Exception as e:
            print(f"Gemini Error: {e}")
            header = "Ahojte @everyone! 👇\n⇣"

        try:
            message = await channel.send(content=header, embeds=embeds + [closing_embed])
            try:
                await message.add_reaction(emoji)
            except:
                pass
            return True, "Oznamy boli uverejnené."
        except Exception as e:
            return False, f"Chyba pri odosielaní: {e}"

    async def send_reminder(self, publish_time):
        """Sends a reminder DM to configured admins."""
        # Get announcements for TOMORROW (since reminder is day before)
        # Actually, generate_announcement_embeds_for_date filters by visibility.
        # If we run this "day before", we should check if they will be visible TOMORROW.
        # But usually visibility is set broadly. Let's just check what would be published tomorrow.
        tomorrow = datetime.now() + timedelta(days=1)
        embeds = generate_announcement_embeds_for_date(tomorrow)
        
        if not embeds:
            return # No announcements to remind about

        admin_ids = get_setting("error_notification_users", [])
        if not admin_ids:
            return

        msg = f"🔔 **PRIPOMIENKA:** Zajtra o {publish_time} zverejním oznamy.\n\n**Náhľad:**"
        
        for uid in admin_ids:
            user = self.bot.get_user(uid)
            if user:
                try:
                    await user.send(content=msg, embeds=embeds)
                except:
                    pass

    @app_commands.command(name="pridaj_oznam", description="Pridá nový oznam pomocou modálneho okna")
    @app_commands.describe(typ="Zadaj typ: event alebo info")
    async def pridaj_oznam(self, interaction: discord.Interaction, typ: str):
        if typ == "event":
            await interaction.response.send_modal(EventOznamModal(self.bot))
        elif typ == "info":
            await interaction.response.send_modal(InfoOznamModal(self.bot))
        else:
            await interaction.response.send_message("Typ musí byť `event` alebo `info`.", ephemeral=True)

    @app_commands.command(name="zoznam_oznamov", description="Zobrazí všetky oznamy v databáze")
    async def zoznam_oznamov(self, interaction: discord.Interaction):
        all_announcements = get_all_announcements()
        formatted = format_announcement_preview(all_announcements)
        await interaction.response.send_message(formatted if formatted else "Žiadne oznamy v databáze.")

    @app_commands.command(name="uprav_oznam", description="Upraví oznam podľa ID")
    @app_commands.describe(announcement_id="ID oznamu, ktorý chceš upraviť")
    async def uprav_oznam(self, interaction: Interaction, announcement_id: int):
        ann = get_announcement_by_id(announcement_id)
        if not ann:
            await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
            return
        await interaction.response.send_modal(EditOznamModal(self.bot, announcement_id, ann))

    @app_commands.command(name="vymaz_oznam", description="Vymaže oznam podľa ID")
    @app_commands.describe(announcement_id="ID oznamu, ktorý chceš vymazať")
    async def vymaz_oznam(self, interaction: Interaction, announcement_id: int):
        ann = get_announcement_by_id(announcement_id)
        if not ann:
            await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
            return
        await interaction.response.send_message(f"Naozaj chceš vymazať oznam ID `{announcement_id}`?", view=DeleteConfirmView(announcement_id))

    @app_commands.command(name="preview_oznam", description="Zobrazí náhľad oznamu podľa ID")
    @app_commands.describe(announcement_id="ID oznamu na zobrazenie")
    async def preview_oznam(self, interaction: Interaction, announcement_id: int):
        ann = get_announcement_by_id(announcement_id)
        if not ann:
            await interaction.response.send_message(f"⚠️ Oznam ID `{announcement_id}` neexistuje.", ephemeral=True)
            return

        light_color, dark_color = MONTH_COLORS.get(datetime.now().month, (0xDDDDDD, 0x999999))
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vygeneruj_oznamy", description="Vygeneruje oznamy pre zadaný deň alebo najbližší sobotu.")
    @app_commands.describe(
        datum="Dátum v tvare DD.MM alebo DD.MM.YYYY. Ak nie je zadaný, použije sa najbližšia sobota."
    )
    async def vygeneruj_oznamy(self, interaction: discord.Interaction, datum: str | None = None):
        if datum is None:
            target_datetime = get_next_saturday_at_10()
            intro_message = f"Zobrazujem oznamy k dátumu najbližšieho zverejnenia: **{target_datetime.strftime('%d.%m.%Y %H:%M')}**"
        else:
            try:
                if len(datum) <= 5:
                    datum += f".{datetime.now().year}"
                target_datetime = datetime.strptime(datum, "%d.%m.%Y")
                intro_message = f"Zobrazujem oznamy k **{target_datetime.strftime('%d.%m.%Y')}**"
            except ValueError:
                await interaction.response.send_message("Neplatný formát dátumu. Použite DD.MM alebo DD.MM.YYYY.", ephemeral=True)
                return

        embeds = generate_announcement_embeds_for_date(target_datetime)

        if not embeds:
            await interaction.response.send_message(f"{intro_message}\n\n❤\ufe0f Žiadne oznamy nie sú k dispozícii pre tento deň.")
            return

        # Hlavička v textovej správe
        message = f"{intro_message}\n\n⇣"
        await interaction.response.send_message(content=message, embeds=embeds)

    @app_commands.command(name="uverejni_oznamy_teraz", description="Uverejní oznamy k dnešnému dňu do kanála #oznamy")
    async def uverejni_oznamy_teraz(self, interaction: discord.Interaction):
        today = datetime.now().strftime("%d.%m.%Y")
        message = (
            f"⚠️ Tento krok uverejní všetky aktívne oznamy k dnešnému dňu (**{today}**) "
            f"do kanála <#{OZNAMY_CHANNEL_ID}>.\n"
            "Naozaj ich chceš teraz zverejniť?"
        )
        await interaction.response.send_message(content=message, view=ConfirmPostNowView(self.bot, self), ephemeral=False)

async def setup(bot):
    await bot.add_cog(Announcements(bot))
