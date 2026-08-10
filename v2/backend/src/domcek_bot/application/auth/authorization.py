"""Central role-to-capability authorization policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from domcek_bot.application.records import GuildConfigRecord


class AppRole(StrEnum):
    TEAM_MOD = "team_mod"
    PUBLISHER = "publisher"
    ADMIN = "admin"


class Capability(StrEnum):
    VIEW_ADMIN = "view_admin"
    EDIT_CONTENT = "edit_content"
    FORCE_INCLUSION = "force_inclusion"
    MANUAL_PUBLISH = "manual_publish"
    RECONCILE_PUBLICATION = "reconcile_publication"
    MANAGE_CHANNELS = "manage_channels"
    APPROVE_ARCHIVE = "approve_archive"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_ROLES = "manage_roles"
    VIEW_FULL_AUDIT = "view_full_audit"


ROLE_CAPABILITIES: dict[AppRole, frozenset[Capability]] = {
    AppRole.TEAM_MOD: frozenset(
        {Capability.VIEW_ADMIN, Capability.EDIT_CONTENT, Capability.MANAGE_CHANNELS}
    ),
    AppRole.PUBLISHER: frozenset({Capability.VIEW_ADMIN, Capability.MANUAL_PUBLISH}),
    AppRole.ADMIN: frozenset(Capability),
}


class AuthorizationDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    guild_id: int
    user_id: int
    username: str
    display_name: str
    avatar_url: str | None
    discord_role_ids: frozenset[int]
    app_roles: frozenset[AppRole]

    @property
    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            capability for role in self.app_roles for capability in ROLE_CAPABILITIES[role]
        )

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise AuthorizationDenied(f"missing capability: {capability.value}")


def resolve_app_roles(
    discord_role_ids: frozenset[int], config: GuildConfigRecord
) -> frozenset[AppRole]:
    mapping = (
        (config.team_mod_role_id, AppRole.TEAM_MOD),
        (config.publisher_role_id, AppRole.PUBLISHER),
        (config.admin_role_id, AppRole.ADMIN),
    )
    return frozenset(role for role_id, role in mapping if role_id in discord_role_ids)
