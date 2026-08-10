from __future__ import annotations

import hashlib
import itertools
import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta

import pytest

from domcek_bot.application.publication.composer import (
    DISCORD_CONTENT_LIMIT,
    DISCORD_EMBED_DESCRIPTION_LIMIT,
    PublicationCompositionError,
    compose_publication,
    plan_discord_messages,
)
from domcek_bot.application.publication.formatting import (
    format_all_day_range,
    format_timed_range,
    google_html_to_text,
    neutralize_discord_mentions,
)
from domcek_bot.application.publication.models import (
    DraftItemKind,
    DraftWarningCode,
    EventSeriesOverrideInput,
    ExclusionReason,
    InfoAnnouncementInput,
    ManualEventInput,
    PublicationComposeSnapshot,
    PublicationDraftItem,
    ValueOrigin,
)
from domcek_bot.application.records import (
    CalendarSourceRecord,
    EventOverrideRecord,
    ExternalEventRecord,
    GuildConfigRecord,
)
from domcek_bot.domain.enums import (
    DescriptionState,
    ExternalEventStatus,
    InclusionDecision,
)

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
REFERENCE = datetime(2026, 8, 9, 10, tzinfo=UTC)
SLOT = datetime(2026, 8, 10, 18, tzinfo=UTC)
SYNCED = datetime(2026, 8, 9, 9, tzinfo=UTC)
SOURCE_A_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SOURCE_B_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


def _guild(
    *,
    publication_weekday: int = 0,
    publication_time: time = time(20),
    publish_google_descriptions: bool = False,
    everyone_mention_enabled: bool = True,
) -> GuildConfigRecord:
    return GuildConfigRecord(
        guild_id=GUILD_ID,
        publication_weekday=publication_weekday,
        publication_time=publication_time,
        timezone="Europe/Bratislava",
        publish_google_descriptions=publish_google_descriptions,
        everyone_mention_enabled=everyone_mention_enabled,
        closing_message="Potvrďte prečítanie reakciou.",
    )


def _source(source_id: uuid.UUID = SOURCE_A_ID, *, priority: int = 100) -> CalendarSourceRecord:
    return CalendarSourceRecord(
        id=source_id,
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id=f"{source_id}@example.test",
        display_name="Kalendár",
        priority=priority,
    )


def _timed_event(
    event_id: uuid.UUID,
    *,
    title: str | None = "Udalosť",
    description: str | None = None,
    starts_at: datetime = SLOT,
    ends_at: datetime | None = SLOT + timedelta(hours=1),
    source_id: uuid.UUID = SOURCE_A_ID,
    series_key: str | None = None,
    original_start_key: str | None = None,
) -> ExternalEventRecord:
    return ExternalEventRecord(
        id=event_id,
        calendar_source_id=source_id,
        source_key=f"key-{event_id}",
        provider_event_id=f"provider-{event_id}",
        source_title=title,
        source_description=description,
        is_all_day=False,
        starts_at=starts_at,
        ends_at=ends_at,
        source_timezone="Europe/Prague",
        status=ExternalEventStatus.CONFIRMED,
        last_synced_at=SYNCED,
        series_key=series_key,
        original_start_key=original_start_key,
    )


def _all_day_event(
    event_id: uuid.UUID,
    *,
    starts_on: date,
    ends_on: date,
    title: str = "Celodenná",
    source_id: uuid.UUID = SOURCE_A_ID,
) -> ExternalEventRecord:
    return ExternalEventRecord(
        id=event_id,
        calendar_source_id=source_id,
        source_key=f"key-{event_id}",
        provider_event_id=f"provider-{event_id}",
        source_title=title,
        is_all_day=True,
        starts_on=starts_on,
        ends_on=ends_on,
        source_timezone="Europe/Prague",
        status=ExternalEventStatus.CONFIRMED,
        last_synced_at=SYNCED,
    )


def _snapshot(
    *,
    guild: GuildConfigRecord | None = None,
    sources: tuple[CalendarSourceRecord, ...] | None = None,
    events: tuple[ExternalEventRecord, ...] = (),
    overrides: tuple[EventOverrideRecord, ...] = (),
    series_overrides: tuple[EventSeriesOverrideInput, ...] = (),
    manual_events: tuple[ManualEventInput, ...] = (),
    info: tuple[InfoAnnouncementInput, ...] = (),
    completed: frozenset[str] = frozenset(),
) -> PublicationComposeSnapshot:
    return PublicationComposeSnapshot(
        guild=guild or _guild(),
        reference_time=REFERENCE,
        calendar_sources=sources or (_source(),),
        external_events=events,
        event_overrides=overrides,
        series_overrides=series_overrides,
        manual_events=manual_events,
        info_announcements=info,
        completed_slot_keys=completed,
        intro_text="Ahojte @everyone, tu je prehľad.",
    )


def _override(
    event_id: uuid.UUID,
    *,
    title: str | None = None,
    state: DescriptionState = DescriptionState.INHERIT,
    description: str | None = None,
    inclusion: InclusionDecision = InclusionDecision.AUTO,
) -> EventOverrideRecord:
    return EventOverrideRecord(
        external_event_id=event_id,
        public_title=title,
        description_state=state,
        public_description=description,
        inclusion_decision=inclusion,
        updated_by_user_id=USER_ID,
    )


def _series_override(
    *,
    effective_at: datetime,
    title: str | None = None,
    state: DescriptionState = DescriptionState.INHERIT,
    description: str | None = None,
) -> EventSeriesOverrideInput:
    return EventSeriesOverrideInput(
        id=uuid.uuid4(),
        calendar_source_id=SOURCE_A_ID,
        series_key="series-key",
        effective_from_key=effective_at.isoformat(),
        effective_all_day=False,
        effective_from_at=effective_at,
        effective_from_date=None,
        public_title=title,
        description_state=state,
        public_description=description,
    )


def test_next_completed_slot_is_skipped_without_changing_window_rule() -> None:
    first_key = f"{GUILD_ID}:2026-08-10T20:00:Europe/Bratislava"
    draft = compose_publication(_snapshot(completed=frozenset({first_key})))

    assert draft.scheduled_local.isoformat() == "2026-08-17T20:00:00+02:00"
    assert draft.window_starts_at == draft.scheduled_local
    assert draft.window_ends_at.isoformat() == "2026-08-31T20:00:00+02:00"


@pytest.mark.parametrize(
    ("reference", "expected_slot", "expected_end"),
    [
        (
            datetime(2026, 3, 28, 12, tzinfo=UTC),
            "2026-03-29T03:00:00+02:00",
            "2026-04-12T03:00:00+02:00",
        ),
        (
            datetime(2026, 10, 24, 12, tzinfo=UTC),
            "2026-10-25T02:30:00+02:00",
            "2026-11-08T02:30:00+01:00",
        ),
    ],
)
def test_composer_slot_and_window_are_stable_across_dst(
    reference: datetime,
    expected_slot: str,
    expected_end: str,
) -> None:
    snapshot = replace(
        _snapshot(guild=_guild(publication_weekday=6, publication_time=time(2, 30))),
        reference_time=reference,
    )

    draft = compose_publication(snapshot)

    assert draft.scheduled_local.isoformat() == expected_slot
    assert draft.window_ends_at.isoformat() == expected_end


def test_window_includes_overlap_and_excludes_exact_end_and_cancelled() -> None:
    included = _timed_event(
        uuid.UUID("00000000-0000-4000-8000-000000000001"),
        starts_at=SLOT - timedelta(hours=1),
        ends_at=SLOT + timedelta(hours=1),
    )
    exact_end = _timed_event(
        uuid.UUID("00000000-0000-4000-8000-000000000002"),
        starts_at=SLOT + timedelta(days=14),
        ends_at=SLOT + timedelta(days=14, hours=1),
    )
    cancelled = replace(
        _timed_event(uuid.UUID("00000000-0000-4000-8000-000000000003")),
        status=ExternalEventStatus.CANCELLED,
    )
    overlapping_all_day = _all_day_event(
        uuid.UUID("00000000-0000-4000-8000-000000000004"),
        starts_on=date(2026, 8, 9),
        ends_on=date(2026, 8, 11),
    )

    draft = compose_publication(
        _snapshot(events=(exact_end, cancelled, included, overlapping_all_day))
    )

    assert {item.source_id for item in draft.public_items} == {
        str(included.id),
        str(overlapping_all_day.id),
    }


@pytest.mark.parametrize(
    ("description", "inclusion", "expected_included", "reason"),
    [
        ("Poznámka. STOP CARLO", InclusionDecision.AUTO, False, ExclusionReason.STOP_CARLO),
        ("STOP CARLO", InclusionDecision.FORCE_INCLUDE, True, None),
        (None, InclusionDecision.FORCE_EXCLUDE, False, ExclusionReason.FORCE_EXCLUDE),
    ],
)
def test_instance_inclusion_has_priority_over_stop_carlo(
    description: str | None,
    inclusion: InclusionDecision,
    expected_included: bool,
    reason: ExclusionReason | None,
) -> None:
    event = _timed_event(uuid.uuid4(), description=description)
    draft = compose_publication(
        _snapshot(events=(event,), overrides=(_override(event.id, inclusion=inclusion),))
    )

    editor_item = draft.editor_events[0]
    assert editor_item.included is expected_included
    assert editor_item.exclusion_reason is reason
    assert editor_item.inclusion_decision is inclusion
    assert editor_item.instance_override_version == 1
    assert (editor_item in draft.public_items) is expected_included


@pytest.mark.parametrize(
    (
        "instance_title",
        "series_title",
        "google_title",
        "instance_state",
        "instance_description",
        "series_state",
        "series_description",
        "google_enabled",
        "expected_title_origin",
        "expected_description_origin",
        "expected_description",
    ),
    [
        (
            "Instance",
            "Séria",
            "Google",
            DescriptionState.CUSTOM,
            "Instance popis",
            DescriptionState.CUSTOM,
            "Séria popis",
            True,
            ValueOrigin.INSTANCE,
            ValueOrigin.INSTANCE,
            "Instance popis",
        ),
        (
            "Instance",
            "Séria",
            "Google",
            DescriptionState.INTENTIONALLY_EMPTY,
            None,
            DescriptionState.CUSTOM,
            "Séria popis",
            True,
            ValueOrigin.INSTANCE,
            ValueOrigin.INSTANCE,
            None,
        ),
        (
            None,
            "Séria",
            "Google",
            DescriptionState.INHERIT,
            None,
            DescriptionState.CUSTOM,
            "Séria popis",
            True,
            ValueOrigin.SERIES,
            ValueOrigin.SERIES,
            "Séria popis",
        ),
        (
            None,
            None,
            "Google",
            DescriptionState.INHERIT,
            None,
            DescriptionState.INTENTIONALLY_EMPTY,
            None,
            True,
            ValueOrigin.GOOGLE,
            ValueOrigin.SERIES,
            None,
        ),
        (
            None,
            None,
            "Google",
            DescriptionState.INHERIT,
            None,
            DescriptionState.INHERIT,
            None,
            False,
            ValueOrigin.GOOGLE,
            ValueOrigin.NONE,
            None,
        ),
        (
            None,
            None,
            None,
            DescriptionState.INHERIT,
            None,
            DescriptionState.INHERIT,
            None,
            True,
            ValueOrigin.FALLBACK,
            ValueOrigin.GOOGLE,
            "Google verejný",
        ),
    ],
)
def test_title_and_description_priority_matrix(
    instance_title: str | None,
    series_title: str | None,
    google_title: str | None,
    instance_state: DescriptionState,
    instance_description: str | None,
    series_state: DescriptionState,
    series_description: str | None,
    google_enabled: bool,
    expected_title_origin: ValueOrigin,
    expected_description_origin: ValueOrigin,
    expected_description: str | None,
) -> None:
    event = _timed_event(
        uuid.uuid4(),
        title=google_title,
        description="<p>Google verejný</p>",
        series_key="series-key",
        original_start_key=SLOT.isoformat(),
    )
    instance = _override(
        event.id,
        title=instance_title,
        state=instance_state,
        description=instance_description,
    )
    series = _series_override(
        effective_at=SLOT - timedelta(days=1),
        title=series_title,
        state=series_state,
        description=series_description,
    )
    draft = compose_publication(
        _snapshot(
            guild=_guild(publish_google_descriptions=google_enabled),
            events=(event,),
            overrides=(instance,),
            series_overrides=(series,),
        )
    )

    item = draft.editor_events[0]
    assert item.title_origin is expected_title_origin
    assert item.description_origin is expected_description_origin
    assert item.description == expected_description
    if expected_title_origin is ValueOrigin.FALLBACK:
        assert {warning.code for warning in draft.warnings} == {DraftWarningCode.MISSING_TITLE}


def test_latest_effective_series_rule_uses_original_occurrence_after_move() -> None:
    event = _timed_event(
        uuid.uuid4(),
        starts_at=SLOT + timedelta(days=5),
        ends_at=SLOT + timedelta(days=5, hours=1),
        series_key="series-key",
        original_start_key=(SLOT + timedelta(days=2)).isoformat(),
    )
    too_new = _series_override(effective_at=SLOT + timedelta(days=3), title="Budúce pravidlo")
    applicable = _series_override(effective_at=SLOT + timedelta(days=1), title="Platné pravidlo")

    draft = compose_publication(_snapshot(events=(event,), series_overrides=(too_new, applicable)))

    assert draft.public_items[0].title == "Platné pravidlo"
    assert draft.public_items[0].title_origin is ValueOrigin.SERIES
    assert draft.public_items[0].series_public_title == "Platné pravidlo"
    assert draft.public_items[0].series_override_version == 0


def test_all_day_series_rule_uses_original_occurrence_date() -> None:
    event = replace(
        _all_day_event(
            uuid.uuid4(),
            starts_on=date(2026, 8, 15),
            ends_on=date(2026, 8, 16),
        ),
        series_key="series-key",
        original_start_key="2026-08-12",
    )
    applicable = EventSeriesOverrideInput(
        id=uuid.uuid4(),
        calendar_source_id=SOURCE_A_ID,
        series_key="series-key",
        effective_from_key="2026-08-11",
        effective_all_day=True,
        effective_from_at=None,
        effective_from_date=date(2026, 8, 11),
        public_title="Celodenné pravidlo",
        description_state=DescriptionState.INHERIT,
        public_description=None,
    )
    too_new = replace(
        applicable,
        id=uuid.uuid4(),
        effective_from_key="2026-08-13",
        effective_from_date=date(2026, 8, 13),
        public_title="Príliš nové pravidlo",
    )

    draft = compose_publication(_snapshot(events=(event,), series_overrides=(too_new, applicable)))

    assert draft.public_items[0].title == "Celodenné pravidlo"


def test_manual_all_day_overlap_uses_same_half_open_window() -> None:
    overlapping = ManualEventInput(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        title="Manuálna viacdňová",
        is_all_day=True,
        starts_on=date(2026, 8, 9),
        ends_on=date(2026, 8, 11),
    )
    exact_end = replace(
        overlapping,
        id=uuid.uuid4(),
        title="Mimo okna",
        starts_on=date(2026, 8, 24),
        ends_on=date(2026, 8, 25),
    )

    draft = compose_publication(_snapshot(manual_events=(exact_end, overlapping)))

    assert [item.source_id for item in draft.public_items] == [str(overlapping.id)]
    assert draft.public_items[0].display_time == ("09.08. \N{EN DASH} 10.08. // celodenná")


def test_force_included_stop_carlo_event_publishes_only_public_google_text() -> None:
    event = _timed_event(
        uuid.uuid4(),
        description="<p>Verejný text.</p><p>STOP CARLO</p>",
    )
    override = _override(event.id, inclusion=InclusionDecision.FORCE_INCLUDE)

    draft = compose_publication(
        _snapshot(
            guild=_guild(publish_google_descriptions=True),
            events=(event,),
            overrides=(override,),
        )
    )

    assert draft.public_items[0].description == "Verejný text."
    assert draft.editor_events[0].source_description == "Verejný text."
    assert "stop carlo" not in (draft.public_items[0].description or "").casefold()


def test_info_validity_manual_event_and_url_warnings() -> None:
    valid_info = InfoAnnouncementInput(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        title="INFO @everyone",
        description="Platné",
        valid_from=date(2026, 8, 1),
        valid_until=date(2026, 8, 10),
        link_url="javascript:alert(1)",
        image_url="https://example.test/image.png",
    )
    expired_info = replace(
        valid_info,
        id=uuid.uuid4(),
        valid_until=date(2026, 8, 9),
    )
    manual = ManualEventInput(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        title="Manuálna <@123>",
        description="Popis @here",
        is_all_day=False,
        starts_at=SLOT + timedelta(hours=2),
        ends_at=SLOT + timedelta(hours=3),
    )

    draft = compose_publication(_snapshot(info=(expired_info, valid_info), manual_events=(manual,)))

    assert [item.kind for item in draft.public_items] == [
        DraftItemKind.INFO,
        DraftItemKind.MANUAL_EVENT,
    ]
    assert draft.public_items[0].link_url is None
    assert "@\u200beveryone" in draft.public_items[0].title
    assert "<@\u200b123>" in draft.public_items[1].title
    assert "@\u200bhere" in (draft.public_items[1].description or "")
    assert {warning.code for warning in draft.warnings} == {DraftWarningCode.INVALID_LINK_URL}
    assert [embed.color for embed in draft.messages[0].embeds] == [0xF9E79F, 0xD68910]


def test_sorting_is_deterministic_with_info_all_day_sources_and_manual() -> None:
    same_time = SLOT + timedelta(days=1)
    source_a = _source(SOURCE_A_ID, priority=200)
    source_b = _source(SOURCE_B_ID, priority=100)
    external_a = _timed_event(
        uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        title="Zulu",
        starts_at=same_time,
        ends_at=same_time + timedelta(hours=1),
        source_id=SOURCE_A_ID,
    )
    external_b = _timed_event(
        uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        title="Alfa",
        starts_at=same_time,
        ends_at=same_time + timedelta(hours=1),
        source_id=SOURCE_B_ID,
    )
    all_day = _all_day_event(
        uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        starts_on=date(2026, 8, 11),
        ends_on=date(2026, 8, 12),
    )
    inputs = (external_a, external_b, all_day)
    serialized: set[str] = set()
    orders: set[tuple[str, ...]] = set()
    for permutation in itertools.permutations(inputs):
        draft = compose_publication(_snapshot(sources=(source_a, source_b), events=permutation))
        serialized.add(draft.canonical_json())
        orders.add(tuple(item.source_id for item in draft.public_items))

    assert len(serialized) == 1
    assert orders == {(str(all_day.id), str(external_b.id), str(external_a.id))}


def test_slovak_formatting_and_google_html_are_centralized() -> None:
    assert format_timed_range(SLOT, SLOT + timedelta(hours=1), "Europe/Bratislava") == (
        "10.08. // 20:00\N{EN DASH}21:00"
    )
    assert format_all_day_range(date(2026, 8, 10), date(2026, 8, 13)) == (
        "10.08. \N{EN DASH} 12.08. // celodenná"
    )
    assert google_html_to_text("<p>Prvý<br>Druhý</p>") == "Prvý\nDruhý"
    assert neutralize_discord_mentions("@everyone <@123> <@&456> @here") == (
        "@\u200beveryone <@\u200b123> <@\u200b&456> @\u200bhere"
    )


def _draft_item(position: int, *, description: str = "Krátky popis") -> PublicationDraftItem:
    return PublicationDraftItem(
        kind=DraftItemKind.MANUAL_EVENT,
        source_id=str(uuid.UUID(int=position + 1)),
        title=f"Udalosť {position:02d}",
        description=description,
        title_origin=ValueOrigin.MANUAL,
        description_origin=ValueOrigin.MANUAL,
        included=True,
        exclusion_reason=None,
        display_time="10.08. // 20:00\N{EN DASH}21:00",
        day_name="pondelok",
        day_emoji="https://example.test/monday.png",
        is_all_day=False,
        starts_at=SLOT + timedelta(minutes=position),
    )


def test_message_plan_respects_limits_everyone_nonce_and_seen_target() -> None:
    messages = plan_discord_messages(
        guild_id=GUILD_ID,
        slot_key="slot",
        intro_text="Úvod",
        outro_text="Záver",
        everyone_enabled=True,
        items=tuple(_draft_item(index) for index in range(21)),
    )

    assert [len(message.embeds) for message in messages] == [10, 10, 1]
    assert sum((message.content or "").count("@everyone") for message in messages) == 1
    assert messages[0].allowed_mentions == ("everyone",)
    assert all(message.allowed_mentions == () for message in messages[1:])
    assert all(len(message.nonce) == 25 for message in messages)
    assert len({message.part_key for message in messages}) == len(messages)
    assert [message.seen_target for message in messages] == [False, False, True]
    assert all(len(message.embeds) <= 10 for message in messages)
    assert all(message.embed_character_count <= 6000 for message in messages)
    assert all(len(message.content or "") <= DISCORD_CONTENT_LIMIT for message in messages)


def test_composer_enforces_everyone_even_for_legacy_disabled_record() -> None:
    draft = compose_publication(_snapshot(guild=_guild(everyone_mention_enabled=False)))

    assert sum((message.content or "").count("@everyone") for message in draft.messages) == 1
    assert draft.messages[0].allowed_mentions == ("everyone",)


def test_message_plan_splits_on_total_characters_and_rejects_item_limit() -> None:
    split = plan_discord_messages(
        guild_id=GUILD_ID,
        slot_key="slot",
        intro_text="Úvod",
        outro_text=None,
        everyone_enabled=True,
        items=tuple(_draft_item(index, description="x" * 3000) for index in range(2)),
    )
    assert [len(message.embeds) for message in split] == [1, 1]

    with pytest.raises(PublicationCompositionError, match="description exceeds"):
        plan_discord_messages(
            guild_id=GUILD_ID,
            slot_key="slot",
            intro_text="Úvod",
            outro_text=None,
            everyone_enabled=True,
            items=(_draft_item(1, description="x" * (DISCORD_EMBED_DESCRIPTION_LIMIT + 1)),),
        )

    with pytest.raises(PublicationCompositionError, match="intro exceeds"):
        plan_discord_messages(
            guild_id=GUILD_ID,
            slot_key="slot",
            intro_text="x" * DISCORD_CONTENT_LIMIT,
            outro_text=None,
            everyone_enabled=True,
            items=(),
        )


def test_fixed_fixture_has_stable_canonical_snapshot() -> None:
    event = _timed_event(
        uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        title="Stabilná udalosť",
        description="<p>Google text</p>",
    )
    snapshot = _snapshot(
        guild=_guild(publish_google_descriptions=True),
        events=(event,),
    )

    first = compose_publication(snapshot).canonical_json()
    second = compose_publication(snapshot).canonical_json()

    assert first == second
    assert hashlib.sha256(first.encode()).hexdigest() == (
        "9f43c8dc6aba1a975130be0ee42323fbed932a7ca721420baf600c8d46e0bf06"
    )
