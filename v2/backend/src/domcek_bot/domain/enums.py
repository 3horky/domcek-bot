"""Domain states persisted as readable strings."""

from enum import StrEnum


class DescriptionState(StrEnum):
    INHERIT = "inherit"
    CUSTOM = "custom"
    INTENTIONALLY_EMPTY = "intentionally_empty"


class InclusionDecision(StrEnum):
    AUTO = "auto"
    FORCE_INCLUDE = "force_include"
    FORCE_EXCLUDE = "force_exclude"


class PublicationState(StrEnum):
    PREPARING = "preparing"
    WAITING_FOR_RELEASE = "waiting_for_release"
    PUBLISHING = "publishing"
    SUCCEEDED_AUTOMATIC = "succeeded_automatic"
    SUCCEEDED_MANUAL = "succeeded_manual"
    SKIPPED_AFTER_MANUAL = "skipped_after_manual"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    PARTIALLY_PUBLISHED = "partially_published"
    CANCELLED = "cancelled"


class PublicationMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class ArchiveState(StrEnum):
    PENDING = "pending"
    ARCHIVING = "archiving"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


class ExternalEventStatus(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class SyncStatus(StrEnum):
    NEVER = "never"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PublicationItemType(StrEnum):
    INTRO = "intro"
    INFO = "info"
    EXTERNAL_EVENT = "external_event"
    MANUAL_EVENT = "manual_event"
    OUTRO = "outro"


class PublicationMessageState(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


class PublicationIncidentState(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class IntegrationTaskState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"


class UndoState(StrEnum):
    AVAILABLE = "available"
    UNDOING = "undoing"
    UNDONE = "undone"


class AuditResult(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
