"""Discord interaction process: thin UI over shared application use cases."""

from __future__ import annotations

import asyncio
import math
import secrets
import signal
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import discord
import structlog
from discord import app_commands

from domcek_bot.application.alerts import AlertCategory, ConfiguredModeratorAlerts
from domcek_bot.application.auth.authorization import (
    AppRole,
    Capability,
    Principal,
    resolve_app_roles,
)
from domcek_bot.application.channels import (
    ArchiveDecisionConflict,
    ChannelManagementService,
    ChannelOperationError,
    CreatedChannel,
    DiscordChannelGateway,
    normalize_channel_emoji,
    normalize_channel_name,
)
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.publication.engine import (
    DiscordAmbiguousError,
    DiscordDefinitiveError,
    DiscordTransientError,
    PublicationEngine,
)
from domcek_bot.application.publication.formatting import neutralize_discord_mentions
from domcek_bot.application.publication.intro import IntroService
from domcek_bot.application.publication.manual import (
    InvalidPublishConfirmation,
    ManualPublicationDisabled,
    ManualPublicationPreview,
    ManualPublicationService,
)
from domcek_bot.application.publication.models import DiscordMessagePlan
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import PublicationMessageRecord
from domcek_bot.config import ProcessKind, Settings, load_settings
from domcek_bot.domain.enums import ArchiveState, PublicationState
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.gemini_intro import GeminiIntroGenerator
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from domcek_bot.logging import configure_logging

logger = structlog.get_logger(__name__)


def _safe_latency_ms(latency_seconds: float) -> int | None:
    milliseconds = latency_seconds * 1000
    if not math.isfinite(milliseconds) or milliseconds < 0:
        return None
    return round(milliseconds)


class DiscordPyPublicationGateway:
    def __init__(self, client: discord.Client) -> None:
        self._client = client

    async def send_message(self, message: PublicationMessageRecord) -> int:
        channel = self._client.get_channel(message.discord_channel_id)
        if channel is None:
            try:
                channel = await self._client.fetch_channel(message.discord_channel_id)
            except discord.HTTPException as exc:
                raise _classified_discord_error(exc) from exc
        if not isinstance(channel, discord.TextChannel):
            raise DiscordDefinitiveError("configured announcement channel is not text")
        try:
            sent = await channel.send(
                content=message.content,
                embeds=[discord.Embed.from_dict(embed) for embed in message.embeds],
                allowed_mentions=discord.AllowedMentions(
                    everyone="everyone" in message.allowed_mentions,
                    users=False,
                    roles=False,
                    replied_user=False,
                ),
                nonce=message.nonce,
            )
        except discord.HTTPException as exc:
            raise _classified_discord_error(exc) from exc
        return sent.id

    async def add_reaction(self, *, channel_id: int, message_id: int, emoji: str) -> None:
        channel = self._client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self._client.fetch_channel(channel_id)
            except discord.HTTPException as exc:
                raise _classified_discord_error(exc) from exc
        if not isinstance(channel, discord.TextChannel):
            raise DiscordDefinitiveError("reaction channel is not text")
        try:
            message = await channel.fetch_message(message_id)
            await message.add_reaction(emoji)
        except discord.HTTPException as exc:
            raise _classified_discord_error(exc) from exc


class DiscordPyModeratorAlertTransport:
    def __init__(self, client: discord.Client, frontend_base_url: str) -> None:
        self._client = client
        self._frontend_base_url = frontend_base_url.rstrip("/")

    async def send_alert(
        self,
        *,
        guild_id: int,
        moderator_channel_id: int | None,
        title: str,
        summary: str,
        correlation_id: str,
        run_id: uuid.UUID | None,
    ) -> None:
        del guild_id
        if moderator_channel_id is None:
            return
        channel = self._client.get_channel(moderator_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        path = f"/historia?run={run_id}#run-{run_id}" if run_id is not None else "/audit"
        await channel.send(
            (
                f"**{title}**\n{summary}\nKorelačné ID: `{correlation_id}`\n"
                f"[Otvoriť administráciu]({self._frontend_base_url}{path})"
            )[:2000],
            allowed_mentions=discord.AllowedMentions.none(),
        )


class DiscordPyChannelGateway(DiscordChannelGateway):
    def __init__(self, client: discord.Client) -> None:
        self._client = client

    async def get_text_channel(self, *, guild_id: int, channel_id: int) -> CreatedChannel:
        guild = self._client.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild is not None else None
        if not isinstance(channel, discord.TextChannel):
            raise ChannelOperationError("archive target is not a guild text channel")
        return CreatedChannel(channel.id, channel.name, channel.jump_url, channel.category_id)

    async def create_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        name: str,
        member_ids: tuple[int, ...],
        role_ids: tuple[int, ...],
        operation_marker: str,
        reason: str,
    ) -> CreatedChannel:
        guild = self._client.get_guild(guild_id)
        if guild is None:
            raise ChannelOperationError("configured guild is unavailable")
        category = guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            raise ChannelOperationError("projects category is unavailable")
        overwrites: dict[
            discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite
        ] = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        access = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=True,
        )
        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role is None or role.is_default() or role.managed:
                raise ChannelOperationError("selected Discord role cannot be assigned")
            overwrites[role] = access
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is None:
                try:
                    member = await guild.fetch_member(member_id)
                except discord.HTTPException as exc:
                    raise ChannelOperationError("selected Discord member is unavailable") from exc
            overwrites[member] = access
        try:
            channel = await guild.create_text_channel(
                name,
                category=category,
                overwrites=overwrites,
                topic=_channel_operation_topic(operation_marker),
                reason=reason,
            )
        except discord.HTTPException as exc:
            raise ChannelOperationError("Discord rejected channel creation") from exc
        return CreatedChannel(channel.id, channel.name, channel.jump_url, channel.category_id)

    async def find_created_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        operation_marker: str,
    ) -> CreatedChannel | None:
        guild = self._client.get_guild(guild_id)
        if guild is None:
            raise ChannelOperationError("configured guild is unavailable")
        expected_topic = _channel_operation_topic(operation_marker)
        matches = [
            channel
            for channel in guild.text_channels
            if channel.category_id == category_id and channel.topic == expected_topic
        ]
        if len(matches) > 1:
            raise ChannelOperationError("multiple channels have the same operation marker")
        if not matches:
            return None
        channel = matches[0]
        return CreatedChannel(channel.id, channel.name, channel.jump_url, channel.category_id)

    async def archive_text_channel(
        self,
        *,
        guild_id: int,
        channel_id: int,
        archive_category_id: int,
        archived_name: str,
        reason: str,
    ) -> CreatedChannel:
        guild = self._client.get_guild(guild_id)
        if guild is None:
            raise ChannelOperationError("configured guild is unavailable")
        channel = guild.get_channel(channel_id)
        category = guild.get_channel(archive_category_id)
        if not isinstance(channel, discord.TextChannel) or not isinstance(
            category, discord.CategoryChannel
        ):
            raise ChannelOperationError("archive channel or category is unavailable")
        try:
            archived = await channel.edit(
                name=archived_name,
                category=category,
                sync_permissions=True,
                reason=reason,
            )
        except discord.HTTPException as exc:
            raise ChannelOperationError("Discord rejected channel archive") from exc
        return CreatedChannel(archived.id, archived.name, archived.jump_url, archived.category_id)


class ChannelSetupView(discord.ui.View):
    def __init__(
        self,
        *,
        service: ChannelManagementService,
        principal: Principal,
        requested_name: str,
        emoji: str,
        request_interaction_id: int,
    ) -> None:
        super().__init__(timeout=300)
        self._service = service
        self._principal = principal
        self._requested_name = requested_name
        self._emoji = emoji
        self._request_interaction_id = request_interaction_id
        self._member_ids: tuple[int, ...] = ()
        self._role_ids: tuple[int, ...] = ()
        self._member_names: tuple[str, ...] = ()
        self._role_names: tuple[str, ...] = ()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._principal.user_id:
            return True
        await interaction.response.send_message(
            "Tento výber patrí inému používateľovi.", ephemeral=True
        )
        return False

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Ľudia s prístupom (voliteľné)",
        min_values=0,
        max_values=10,
        row=0,
    )
    async def select_users(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect[discord.ui.View]
    ) -> None:
        self._member_ids = tuple(user.id for user in select.values)
        self._member_names = tuple(user.display_name for user in select.values)
        await interaction.response.edit_message(content=self.summary, view=self)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Roly s prístupom (voliteľné)",
        min_values=0,
        max_values=10,
        row=1,
    )
    async def select_roles(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect[discord.ui.View]
    ) -> None:
        self._role_ids = tuple(role.id for role in select.values)
        self._role_names = tuple(role.name for role in select.values)
        await interaction.response.edit_message(content=self.summary, view=self)

    @discord.ui.button(label="Vytvoriť kanál", style=discord.ButtonStyle.primary, row=2)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        button.disabled = True
        await interaction.response.edit_message(content=self.summary, view=self)
        try:
            principal = await cast(CarloClient, interaction.client).principal(interaction)
            principal.require(Capability.MANAGE_CHANNELS)
            created = await self._service.create_channel(
                name=self._requested_name,
                member_ids=self._member_ids,
                role_ids=self._role_ids,
                idempotency_key=str(self._request_interaction_id),
                principal=principal,
                correlation_id=str(interaction.id),
                emoji=self._emoji,
            )
        except PermissionError:
            await interaction.followup.send(
                "Oprávnenie na vytvorenie kanála už nie je platné.", ephemeral=True
            )
            return
        except (ValueError, ChannelOperationError) as exc:
            await logger.aerror(
                "discord_channel_create_failed",
                correlation_id=str(interaction.id),
                error_type=type(exc).__name__,
            )
            await interaction.followup.send(
                "Kanál sa nepodarilo bezpečne vytvoriť. Skontrolujte výber a oprávnenia Carla.",
                ephemeral=True,
            )
            return
        await interaction.followup.send(f"Kanál {created.jump_url} bol vytvorený.", ephemeral=True)
        self.stop()

    @property
    def summary(self) -> str:
        people = ", ".join(self._member_names) or "nikto ďalší"
        roles = ", ".join(self._role_names) or "žiadne ďalšie roly"
        return (
            "**Nový projektový kanál**\n"
            f"Názov: `#{self._emoji}・{normalize_channel_name(self._requested_name)}`\n"
            f"Vlastník: **{self._principal.display_name}**\n"
            "Kategória: **projektová kategória nastavená v Carlovi**\n"
            f"Ďalší ľudia: {people}\n"
            f"Roly s prístupom: {roles}\n"
            "Vlastník, vybraní ľudia a roly dostanú prístup; ostatní členovia servera nie.\n"
            "Kanál sa vytvorí až po potvrdení."
        )


class ArchiveDecisionButton(discord.ui.Button["ArchiveDecisionView"]):
    def __init__(self, *, request_id: str, approve: bool) -> None:
        self._approve = approve
        super().__init__(
            label="Schváliť" if approve else "Zamietnuť",
            style=(discord.ButtonStyle.success if approve else discord.ButtonStyle.secondary),
            custom_id=f"carlo:archive:{'approve' if approve else 'reject'}:{request_id}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            return
        await self.view.decide(interaction, approve=self._approve)


class ArchiveDecisionView(discord.ui.View):
    def __init__(
        self,
        *,
        service: ChannelManagementService,
        request_id: str,
    ) -> None:
        super().__init__(timeout=None)
        self._service = service
        self._request_id = request_id
        self.add_item(ArchiveDecisionButton(request_id=request_id, approve=True))
        self.add_item(ArchiveDecisionButton(request_id=request_id, approve=False))

    async def decide(self, interaction: discord.Interaction, *, approve: bool) -> None:
        client = cast(CarloClient, interaction.client)
        try:
            principal = await client.principal(interaction)
            result = await self._service.decide_archive(
                uuid.UUID(self._request_id),
                approve=approve,
                principal=principal,
                correlation_id=str(interaction.id),
            )
        except PermissionError:
            await interaction.response.send_message(
                "Archiváciu môže schváliť alebo zamietnuť iba Admin.", ephemeral=True
            )
            return
        except (ArchiveDecisionConflict, LookupError):
            await interaction.response.send_message(
                "O tejto žiadosti už bolo rozhodnuté alebo vypršala.", ephemeral=True
            )
            return
        except Exception as exc:
            await _interaction_failure(
                interaction, exc, "Archiváciu sa nepodarilo bezpečne dokončiť."
            )
            return
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(
            content=(
                f"Žiadosť bola **{'schválená a vykonaná' if approve else 'zamietnutá'}** "
                f"používateľom {interaction.user.mention}."
            ),
            view=self,
        )
        await logger.ainfo(
            "discord_archive_decided",
            request_id=self._request_id,
            state=result.state.value,
            correlation_id=str(interaction.id),
        )
        self.stop()


class DirectArchiveView(discord.ui.View):
    def __init__(
        self,
        *,
        service: ChannelManagementService,
        request_id: str,
        principal: Principal,
    ) -> None:
        super().__init__(timeout=300)
        self._service = service
        self._request_id = request_id
        self._principal = principal
        self._resolved = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._principal.user_id:
            return True
        await interaction.response.send_message(
            "Toto potvrdenie patrí inému používateľovi.", ephemeral=True
        )
        return False

    @discord.ui.button(label="Archivovať kanál", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        button.disabled = True
        await interaction.response.edit_message(view=self)
        try:
            principal = await cast(CarloClient, interaction.client).principal(interaction)
            principal.require(Capability.APPROVE_ARCHIVE)
            await self._service.decide_archive(
                uuid.UUID(self._request_id),
                approve=True,
                principal=principal,
                correlation_id=str(interaction.id),
            )
        except PermissionError:
            await interaction.followup.send("Admin oprávnenie už nie je platné.", ephemeral=True)
            return
        except Exception as exc:
            await _interaction_failure(interaction, exc, "Kanál sa nepodarilo bezpečne archivovať.")
            return
        await interaction.followup.send("Kanál bol archivovaný.", ephemeral=True)
        self._resolved = True
        self.stop()

    @discord.ui.button(label="Zrušiť", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        del button
        try:
            principal = await cast(CarloClient, interaction.client).principal(interaction)
            principal.require(Capability.APPROVE_ARCHIVE)
            await self._service.decide_archive(
                uuid.UUID(self._request_id),
                approve=False,
                principal=principal,
                correlation_id=str(interaction.id),
            )
        except PermissionError:
            await interaction.response.send_message(
                "Admin oprávnenie už nie je platné.", ephemeral=True
            )
            return
        except Exception as exc:
            await _interaction_failure(
                interaction, exc, "Archiváciu sa nepodarilo bezpečne zrušiť."
            )
            return
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(content="Archivácia bola zrušená.", view=self)
        self._resolved = True
        self.stop()

    async def on_timeout(self) -> None:
        if self._resolved:
            return
        await logger.ainfo(
            "discord_direct_archive_confirmation_expired",
            request_id=self._request_id,
        )


class PublishConfirmationView(discord.ui.View):
    def __init__(
        self,
        *,
        service: ManualPublicationService,
        principal: Principal,
        preview: ManualPublicationPreview,
    ) -> None:
        super().__init__(timeout=300)
        self._service = service
        self._principal = principal
        self._preview = preview

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._principal.user_id:
            return True
        await interaction.response.send_message(
            "Toto potvrdenie patrí inému používateľovi.", ephemeral=True
        )
        return False

    @discord.ui.button(label="Zverejniť oznamy", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        button.disabled = True
        await interaction.response.edit_message(view=self)
        try:
            principal = await cast(CarloClient, interaction.client).principal(interaction)
            principal.require(Capability.MANUAL_PUBLISH)
            _, result = await self._service.confirm(
                self._preview.confirmation_token,
                principal=principal,
                correlation_id=str(interaction.id),
            )
        except PermissionError:
            await interaction.followup.send(
                "Oprávnenie na ručné publikovanie už nie je platné.", ephemeral=True
            )
            return
        except InvalidPublishConfirmation:
            await interaction.followup.send(
                "Potvrdenie vypršalo alebo sa termín zmenil. Spustite príkaz znova.",
                ephemeral=True,
            )
            return
        except Exception as exc:
            await logger.aerror(
                "discord_manual_publication_failed",
                correlation_id=str(interaction.id),
                error_type=type(exc).__name__,
            )
            await interaction.followup.send(
                "Publikovanie sa nepodarilo bezpečne dokončiť. Carlo upozornil moderátorov.",
                ephemeral=True,
            )
            return
        if result.state in {
            PublicationState.SUCCEEDED_AUTOMATIC,
            PublicationState.SUCCEEDED_MANUAL,
        }:
            message = (
                f"Publikovanie skončilo stavom **{result.state.value}**. "
                f"Termín `{self._preview.slot_key}` už scheduler nezopakuje."
            )
        else:
            message = (
                f"Publikovanie skončilo stavom **{result.state.value}** a termín zatiaľ "
                "nie je úspešne uzavretý. Skontrolujte Históriu publikácií."
            )
        await interaction.followup.send(message, ephemeral=True)
        self.stop()


class CarloClient(discord.Client):
    def __init__(
        self,
        *,
        settings: Settings,
        database: Database,
        unit_of_work: SqlAlchemyUnitOfWork,
        intents: discord.Intents,
    ) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.settings = settings
        self.database = database
        self.unit_of_work = unit_of_work
        self.thoughts = _load_thoughts(settings.bot_thoughts_file)
        self.intro_generator: GeminiIntroGenerator | None = None
        intro_key = settings.optional_intro_generator_key()
        if intro_key is not None:
            self.intro_generator = GeminiIntroGenerator(
                api_key=intro_key,
                model=settings.intro_generator_model,
                timeout_seconds=settings.intro_generator_timeout_seconds,
            )
        draft_service = PublicationDraftService(unit_of_work)
        alert_transport = DiscordPyModeratorAlertTransport(self, settings.frontend_base_url)
        publication_alerts = ConfiguredModeratorAlerts(
            unit_of_work, alert_transport, AlertCategory.PUBLICATION
        )
        channel_alerts = ConfiguredModeratorAlerts(
            unit_of_work, alert_transport, AlertCategory.CHANNEL
        )
        engine = PublicationEngine(
            unit_of_work,
            draft_service,
            IntroService(self.intro_generator),
            DiscordPyPublicationGateway(self),
            alerts=publication_alerts,
            seen_emoji=settings.publication_seen_emoji,
            max_safe_retries=settings.publication_retry_attempts,
        )
        self.manual_publications = ManualPublicationService(
            draft_service,
            engine,
            secret=settings.session_secret_value(),
            publication_enabled=settings.manual_publication_enabled,
        )
        self.channel_management = ChannelManagementService(
            unit_of_work, DiscordPyChannelGateway(self), channel_alerts
        )
        self.runtime_operations = RuntimeOperationsService(unit_of_work)
        self.runtime_instance_id = uuid.uuid4()
        self.runtime_started_at = datetime.now(UTC)
        self._status_task: asyncio.Task[None] | None = None
        self._archives_recovered = False

    async def setup_hook(self) -> None:
        guild_id = self.settings.discord_guild_id
        if guild_id is None:
            raise RuntimeError("validated bot settings have no guild ID")
        guild = discord.Object(id=guild_id)
        self.tree.add_command(preview_command, guild=guild)
        self.tree.add_command(publish_command, guild=guild)
        self.tree.add_command(channel_command, guild=guild)
        self.tree.add_command(archive_command, guild=guild)
        for request in await self.channel_management.list_pending(guild_id):
            if (
                request.state is ArchiveState.PENDING
                and request.discord_approval_message_id is not None
            ):
                self.add_view(
                    ArchiveDecisionView(
                        service=self.channel_management,
                        request_id=str(request.id),
                    ),
                    message_id=request.discord_approval_message_id,
                )
        if self.settings.discord_sync_guild_commands:
            synced = await self.tree.sync(guild=guild)
            await logger.ainfo(
                "discord_guild_commands_synced", guild_id=guild_id, command_count=len(synced)
            )
        self._status_task = asyncio.create_task(self._status_loop())

    async def on_ready(self) -> None:
        await self._record_runtime_state("connected")
        if not self._archives_recovered:
            guild_id = self.settings.discord_guild_id
            if guild_id is not None:
                recovered = await self.channel_management.recover_archives(
                    guild_id,
                    correlation_id=f"bot-startup-{self.runtime_instance_id}",
                )
                self._archives_recovered = True
                await logger.ainfo("archive_recovery_completed", recovered=len(recovered))
        await logger.ainfo(
            "discord_ready",
            bot_user_id=self.user.id if self.user else None,
            guild_ids=[guild.id for guild in self.guilds],
        )

    async def on_resumed(self) -> None:
        await self._record_runtime_state("connected")

    async def on_disconnect(self) -> None:
        await self._record_runtime_state("disconnected")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if (
            self.settings.discord_dm_response_enabled
            and isinstance(message.channel, discord.DMChannel)
            and self.thoughts
        ):
            await message.channel.send(
                f"Ahoj {message.author.display_name}!\n\n{secrets.choice(self.thoughts)}",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if message.guild is None or self.user is None:
            return
        try:
            async with self.unit_of_work.transaction() as repositories:
                reaction_config = await repositories.reaction_configs.get(message.guild.id)
            if reaction_config is None:
                return
            emojis: set[str | discord.PartialEmoji] = set()
            if (
                reaction_config.auto_reaction_enabled
                and message.channel.id in reaction_config.auto_reaction_channel_ids
            ):
                emoji = _discord_reaction_emoji(
                    reaction_config.auto_reaction_emoji_id,
                    reaction_config.auto_reaction_emoji_unicode,
                )
                if emoji is not None:
                    emojis.add(emoji)
            if reaction_config.mention_reaction_enabled and self.user in message.mentions:
                emoji = _discord_reaction_emoji(
                    reaction_config.mention_reaction_emoji_id,
                    reaction_config.mention_reaction_emoji_unicode,
                )
                if emoji is not None:
                    emojis.add(emoji)
            for emoji in emojis:
                await message.add_reaction(emoji)
        except Exception as exc:
            await logger.awarning(
                "discord_automatic_reaction_failed",
                guild_id=message.guild.id,
                channel_id=message.channel.id,
                message_id=message.id,
                error_type=type(exc).__name__,
            )

    async def close(self) -> None:
        await self._record_runtime_state("stopped")
        if self._status_task is not None:
            self._status_task.cancel()
        if self.intro_generator is not None:
            await self.intro_generator.close()
        await super().close()

    async def principal(self, interaction: discord.Interaction) -> Principal:
        if interaction.guild_id is None or interaction.guild_id != self.settings.discord_guild_id:
            raise PermissionError("interaction is outside the configured guild")
        if not isinstance(interaction.user, discord.Member):
            raise PermissionError("guild member data is unavailable")
        async with self.unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(interaction.guild_id)
        if config is None:
            raise PermissionError("guild configuration is unavailable")
        role_ids = frozenset(role.id for role in interaction.user.roles)
        roles = resolve_app_roles(role_ids, config)
        if not roles:
            raise PermissionError("member has no Carlo role")
        return Principal(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            username=interaction.user.name,
            display_name=interaction.user.display_name,
            avatar_url=str(interaction.user.display_avatar.url),
            discord_role_ids=role_ids,
            app_roles=roles,
        )

    async def _status_loop(self) -> None:
        await self.wait_until_ready()
        next_presence_change = datetime.min.replace(tzinfo=UTC)
        while not self.is_closed():
            now = datetime.now(UTC)
            await self._record_runtime_state(
                "connected" if self.is_ready() else "disconnected",
                observed_at=now,
            )
            if self.thoughts and now >= next_presence_change:
                await self.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.listening,
                        name=secrets.choice(self.thoughts),
                    )
                )
                next_presence_change = now + timedelta(minutes=10)
            await asyncio.sleep(30)

    async def _record_runtime_state(
        self, state: str, *, observed_at: datetime | None = None
    ) -> None:
        guild_id = self.settings.discord_guild_id
        if guild_id is None:
            return
        try:
            details = {"guild_count": len(self.guilds)}
            latency_ms = _safe_latency_ms(self.latency)
            if latency_ms is not None:
                details["latency_ms"] = latency_ms
            await self.runtime_operations.heartbeat(
                guild_id=guild_id,
                process_name="bot",
                instance_id=self.runtime_instance_id,
                state=state,
                started_at=self.runtime_started_at,
                observed_at=observed_at,
                details=details,
            )
        except Exception as exc:
            await logger.awarning("discord_runtime_heartbeat_failed", error_type=type(exc).__name__)


@app_commands.command(name="nahlad", description="Zobrazí najbližšie oznamy bez publikovania")
@app_commands.guild_only()
@app_commands.default_permissions(view_channel=True)
async def preview_command(interaction: discord.Interaction) -> None:
    client = cast(CarloClient, interaction.client)
    await interaction.response.defer(ephemeral=True)
    try:
        principal = await client.principal(interaction)
        preview = await client.manual_publications.preview(
            principal=principal, for_publication=False
        )
    except PermissionError:
        await interaction.followup.send("Na tento príkaz nemáte oprávnenie.", ephemeral=True)
        return
    except Exception as exc:
        await _interaction_failure(interaction, exc, "Náhľad sa nepodarilo pripraviť.")
        return
    await _send_preview(interaction, preview, view=None)


@app_commands.command(
    name="publikovat", description="Pripraví potvrdenie ručného publikovania oznamov"
)
@app_commands.guild_only()
@app_commands.default_permissions(view_channel=True)
async def publish_command(interaction: discord.Interaction) -> None:
    client = cast(CarloClient, interaction.client)
    await interaction.response.defer(ephemeral=True)
    try:
        principal = await client.principal(interaction)
        preview = await client.manual_publications.preview(principal=principal)
    except ManualPublicationDisabled:
        await interaction.followup.send(
            "Ručné odoslanie je v aktuálnom bezpečnostnom režime vypnuté. "
            "Náhľad bez publikovania je dostupný cez `/nahlad`.",
            ephemeral=True,
        )
        return
    except PermissionError:
        await interaction.followup.send(
            "Ručne môže publikovať iba Admin alebo SDB / FMA.", ephemeral=True
        )
        return
    except Exception as exc:
        await _interaction_failure(interaction, exc, "Publikovanie sa nepodarilo pripraviť.")
        return
    view = PublishConfirmationView(
        service=client.manual_publications,
        principal=principal,
        preview=preview,
    )
    await _send_preview(interaction, preview, view=view)


@app_commands.command(name="kanal", description="Pripraví nový súkromný projektový kanál")
@app_commands.guild_only()
@app_commands.default_permissions(view_channel=True)
@app_commands.describe(nazov="Názov nového kanála", emoji="Emoji na začiatku názvu")
async def channel_command(interaction: discord.Interaction, nazov: str, emoji: str = "🏠") -> None:
    client = cast(CarloClient, interaction.client)
    try:
        principal = await client.principal(interaction)
        principal.require(Capability.MANAGE_CHANNELS)
        normalized = normalize_channel_name(nazov)
        normalized_emoji = normalize_channel_emoji(emoji)
    except (PermissionError, ValueError):
        await interaction.response.send_message(
            "Kanál nemôžete vytvoriť alebo jeho názov nie je platný.", ephemeral=True
        )
        return
    view = ChannelSetupView(
        service=client.channel_management,
        principal=principal,
        requested_name=normalized,
        emoji=normalized_emoji,
        request_interaction_id=interaction.id,
    )
    await interaction.response.send_message(
        content=view.summary,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
        ephemeral=True,
    )


@app_commands.command(name="archivovat", description="Požiada o archiváciu aktuálneho kanála")
@app_commands.guild_only()
@app_commands.default_permissions(view_channel=True)
@app_commands.describe(dovod="Prečo sa má kanál archivovať")
async def archive_command(interaction: discord.Interaction, dovod: str) -> None:
    client = cast(CarloClient, interaction.client)
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(
            "Tento príkaz použite priamo v textovom kanáli.", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    try:
        principal = await client.principal(interaction)
        request = await client.channel_management.request_archive(
            channel_id=interaction.channel.id,
            reason=dovod,
            principal=principal,
            correlation_id=str(interaction.id),
        )
    except PermissionError:
        await interaction.followup.send(
            "Na vytvorenie žiadosti o archiváciu nemáte oprávnenie.", ephemeral=True
        )
        return
    except (ValueError, ChannelOperationError) as exc:
        await _interaction_failure(interaction, exc, "Žiadosť o archiváciu sa nepodarilo vytvoriť.")
        return
    if request.discord_approval_message_id is not None:
        await interaction.followup.send(
            "Pre tento kanál už existuje čakajúca žiadosť o archiváciu.", ephemeral=True
        )
        return
    if AppRole.ADMIN in principal.app_roles:
        direct_view = DirectArchiveView(
            service=client.channel_management,
            request_id=str(request.id),
            principal=principal,
        )
        await interaction.followup.send(
            "**Potvrďte archiváciu aktuálneho kanála.**\n"
            "Individuálne oprávnenia nahradia oprávnenia archívnej kategórie.",
            view=direct_view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return
    async with client.unit_of_work.transaction() as repositories:
        config = await repositories.guild_configs.get(principal.guild_id)
    moderator_channel = (
        client.get_channel(config.moderator_channel_id)
        if config is not None and config.moderator_channel_id is not None
        else None
    )
    if not isinstance(moderator_channel, discord.TextChannel):
        await interaction.followup.send(
            "Chýba nakonfigurovaný textový kanál moderátorov.", ephemeral=True
        )
        return
    approval_view = ArchiveDecisionView(
        service=client.channel_management,
        request_id=str(request.id),
    )
    try:
        approval = await moderator_channel.send(
            content=(
                "**Žiadosť o archiváciu kanála**\n"
                f"Kanál: {interaction.channel.mention}\n"
                f"Požiadal: {interaction.user.mention}\n"
                f"Dôvod: {request.reason}\n"
                f"Platnosť: <t:{int(request.expires_at.timestamp())}:R>"
            ),
            view=approval_view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await client.channel_management.attach_approval_message(request.id, approval.id)
    except Exception as exc:
        await _interaction_failure(
            interaction, exc, "Žiadosť vznikla, ale nepodarilo sa poslať schvaľovaciu kartu."
        )
        return
    await interaction.followup.send("Žiadosť bola odoslaná Adminom na schválenie.", ephemeral=True)


async def _send_preview(
    interaction: discord.Interaction,
    preview: ManualPublicationPreview,
    *,
    view: discord.ui.View | None,
) -> None:
    plans = preview.draft.messages
    heading = (
        "**Náhľad \N{EN DASH} nič sa ešte nezverejnilo**\n"
        f"Termín: <t:{int(preview.scheduled_for.timestamp())}:F> · "
        f"{preview.announcement_count} položiek · {preview.message_count} správ"
    )
    first = plans[0]
    if view is None:
        send = (
            interaction.followup.send
            if interaction.response.is_done()
            else interaction.response.send_message
        )
        await send(
            content=f"{heading}\n\n{_preview_content(first)}",
            embeds=_preview_embeds(first),
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=True,
        )
    else:
        send = (
            interaction.followup.send
            if interaction.response.is_done()
            else interaction.response.send_message
        )
        await send(
            content=f"{heading}\n\n{_preview_content(first)}",
            embeds=_preview_embeds(first),
            allowed_mentions=discord.AllowedMentions.none(),
            view=view,
            ephemeral=True,
        )
    for plan in plans[1:]:
        await interaction.followup.send(
            content=_preview_content(plan) or "",
            embeds=_preview_embeds(plan),
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=True,
        )


def _preview_content(plan: DiscordMessagePlan) -> str | None:
    return neutralize_discord_mentions(plan.content)


def _preview_embeds(plan: DiscordMessagePlan) -> list[discord.Embed]:
    return [
        discord.Embed.from_dict(
            {
                "title": embed.title,
                "color": embed.color,
                **({"description": embed.description} if embed.description else {}),
                **({"url": embed.link_url} if embed.link_url else {}),
                **(
                    {
                        "author": {
                            "name": embed.author_name,
                            **(
                                {"icon_url": embed.author_icon_url} if embed.author_icon_url else {}
                            ),
                        }
                    }
                    if embed.author_name
                    else {}
                ),
                **({"thumbnail": {"url": embed.thumbnail_url}} if embed.thumbnail_url else {}),
            }
        )
        for embed in plan.embeds
    ]


async def _interaction_failure(
    interaction: discord.Interaction, exc: Exception, message: str
) -> None:
    await logger.aerror(
        "discord_interaction_failed",
        correlation_id=str(interaction.id),
        error_type=type(exc).__name__,
    )
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def _classified_discord_error(exc: discord.HTTPException) -> Exception:
    if exc.status == 429:
        return DiscordTransientError("Discord rate limit", retry_after=1.0)
    if exc.status >= 500:
        return DiscordAmbiguousError(f"Discord server error ({exc.status})")
    return DiscordDefinitiveError(f"Discord rejected operation ({exc.status})")


def _load_thoughts(path: Path) -> tuple[str, ...]:
    try:
        return tuple(
            line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    except OSError:
        return ()


def _channel_operation_topic(marker: str) -> str:
    return f"Carlo operation: {marker}"[:1024]


def _discord_reaction_emoji(
    emoji_id: int | None, unicode_value: str | None
) -> str | discord.PartialEmoji | None:
    if emoji_id is not None:
        return discord.PartialEmoji(name="_", id=emoji_id)
    return unicode_value


async def serve() -> None:
    settings = load_settings(ProcessKind.BOT)
    configure_logging(settings, ProcessKind.BOT.value)
    database = Database(settings)
    await database.ping()
    unit_of_work = SqlAlchemyUnitOfWork(database)

    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.dm_messages = True
    client = CarloClient(
        settings=settings,
        database=database,
        unit_of_work=unit_of_work,
        intents=intents,
    )
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(shutdown_signal, lambda: asyncio.create_task(client.close()))
        except NotImplementedError:  # pragma: no cover - Windows event loop
            pass

    try:
        await logger.ainfo("discord_starting", configured_guild_id=settings.discord_guild_id)
        await client.start(settings.discord_token_value())
    finally:
        await client.close()
        await database.close()
        await logger.ainfo("discord_stopped")


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()
