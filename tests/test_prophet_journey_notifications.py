"""tests/test_prophet_journey_notifications.py — B21 U2, the PURE producer
half (identity, eligibility, correction table, tier).

Hermetic by construction: the module under test has no IO seam at all, so
this suite needs no socket guard and no monkeypatching. B1 ledger fixtures
are minted through the real writer (engine/us_candidate_episode.py
``make_event``) so envelope keys, content-addressed ``pee:`` ids and
``content_sha256`` receipts are byte-true; B3 projection fixtures use the
writer's row shape (engine/prophet_candidate_state.py ``_row``). The
incumbent modules are imported by THIS suite only — the producer module
itself imports nothing from the repo (pinned below).
"""
from __future__ import annotations

import ast
import sys
import uuid
from pathlib import Path

from engine import fif_saved_research_notifications as fif
from engine import prophet_candidate_state as b3
from engine import prophet_journey_notifications as pjn
from engine.stock_identity import fingerprint
from engine.us_candidate_episode import episode_id as b1_episode_id
from engine.us_candidate_episode import make_event
from lib.tiers import normalize_tier, tier_rank

ROOT = Path(__file__).resolve().parents[1]

SECURITY_ID = "SEC:US-XNAS-XYZ"
COMPANY_ID = "ISS:US-XNAS-XYZ"
ERA = "candidate-episode-v1-2026-08-25"
B3_ERA = "candidate-state-v1-2026-09-18"
GENERATION = "peg:" + "a" * 64
SESSION = "2026-08-25"
NEXT_SESSION_END = "2026-08-26T00:00:00Z"
# The run clock for the mint-time recency gate (F28 R2): inside SESSION's
# bound, so the default fixtures mint.
NOW = "2026-08-25T12:00:00Z"
USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"

ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-08-24T20:00:00Z",
    "price": 42.1,
    "basis": "adjusted_close",
    "source_receipt": "sha256:receipt-a",
}
EPISODE = b1_episode_id(SECURITY_ID, "epoch_0", ANCHOR, 1)
OTHER_ANCHOR = {**ANCHOR, "time": "2026-08-23T20:00:00Z"}
OTHER_EPISODE = b1_episode_id(SECURITY_ID, "epoch_0", OTHER_ANCHOR, 1)

TURN_WATCH_SCHEMA = "prophet.candidate_episode_input.turn_watch/v1"

EXPECTED_PAYLOAD_KEYS = {
    "ticker", "condition_plain", "evidence_url", "subject", "fired_at",
    "category", "event_date", "requires_tier", "not_after", "fact_receipt",
    "corrects_fire_event_id", "candidate_generation_id", "market_session",
    "definition_era", "kind", "source", "schema",
}


# ---------------------------------------------------------------------------
# Fixture builders — byte-true B1 envelopes and B3 rows
# ---------------------------------------------------------------------------
def _open_payload(*, ticker: str = "XYZ", anchor=ANCHOR) -> dict:
    return {
        "security_id": SECURITY_ID,
        "company_id": COMPANY_ID,
        "ticker_at_observation": ticker,
        "identity_epoch": "epoch_0",
        "identity_epoch_state": "provisional",
        "identity_spec_schema": "stock_identity.fingerprint_spec.v1",
        "identity_spec_hash": fingerprint.spec_hash(),
        "structural_anchor": anchor,
        "intake_class": "technical_emergence",
        "opened_at": "2026-08-24T20:00:00Z",
    }


def _envelope(
    event_type: str,
    *,
    payload: dict,
    episode: str = EPISODE,
    source_event_id: str,
    source_system: str = "test_source",
    source_schema: str = "test.source/v1",
    recorded_at: str,
    correction_of: str | None = None,
    known_at: str | None = None,
) -> dict:
    # known_at defaults to recorded_at, so B1's canonical replay order
    # (known_at, source_system, source_event_id) follows the fixture clock.
    return make_event(
        event_type=event_type,
        episode_id=episode,
        source_system=source_system,
        source_schema=source_schema,
        source_event_id=source_event_id,
        occurred_at="2026-08-24T20:00:00Z",
        known_at=known_at or recorded_at,
        recorded_at=recorded_at,
        source_receipt="sha256:test-source",
        definition_era=ERA,
        correction_of=correction_of,
        payload=payload,
    )


def _open_envelope(*, ticker: str = "XYZ", episode: str = EPISODE, anchor=ANCHOR) -> dict:
    return _envelope(
        "OPENED",
        payload=_open_payload(ticker=ticker, anchor=anchor),
        episode=episode,
        source_event_id=f"turn-watch:{ticker}:2026-08-24",
        recorded_at="2026-08-24T20:30:00Z",
    )


def _transition_envelope(
    target: str, *, episode: str = EPISODE, recorded_at: str = "2026-08-25T03:00:00Z"
) -> dict:
    return _envelope(
        "STATE_TRANSITIONED",
        payload={"episode_state": target, "terminal_reason": "episode ran out"},
        episode=episode,
        source_event_id=f"episode:{episode}:{target}",
        recorded_at=recorded_at,
    )


def _corrected_envelope(
    patch: dict,
    *,
    recorded_at: str = "2026-08-25T04:00:00Z",
    correction_of: str | None = None,
) -> dict:
    # B1 places a CORRECTED only once its correction_of relation is placed;
    # the default targets the episode's OPENED relation.
    return _envelope(
        "CORRECTED",
        payload={"patch": patch},
        source_event_id=f"episode:{EPISODE}:corrected",
        recorded_at=recorded_at,
        correction_of=correction_of or _open_envelope()["event_id"],
    )


def _retracted_envelope(target_event_id: str, *, recorded_at: str = "2026-08-25T05:00:00Z") -> dict:
    return _envelope(
        "RETRACTED",
        payload={"reason": "source withdrawn"},
        source_event_id=f"episode:{EPISODE}:retracted",
        recorded_at=recorded_at,
        correction_of=target_event_id,
    )


def _superseded_envelope(successor: str = OTHER_EPISODE, *, recorded_at: str = "2026-08-25T06:00:00Z") -> dict:
    return _envelope(
        "IDENTITY_SUPERSEDED",
        payload={"successor_episode_id": successor, "reason": "identity re-anchored"},
        source_event_id=f"episode:{EPISODE}:superseded",
        recorded_at=recorded_at,
    )


def _relation_envelope(*, recorded_at: str = "2026-08-25T02:10:00Z") -> dict:
    """A TURN WATCH OBSERVED relation, the B3-indexed source of TRIGGERED."""
    return _envelope(
        "OBSERVED",
        payload={
            "security_id": SECURITY_ID,
            "company_id": COMPANY_ID,
            "ticker_at_observation": "XYZ",
            "anchor": ANCHOR,
            "occurred_at": "2026-08-24T20:00:00Z",
        },
        source_event_id="turn-watch:XYZ:2026-08-24:observed",
        source_system="turn_watch",
        source_schema=TURN_WATCH_SCHEMA,
        recorded_at=recorded_at,
    )


def _projection_row(
    *,
    episode: str = EPISODE,
    lifecycle: str = "ACTIVE",
    source_state: str = "ACTIVE",
    emergence_state: str | None = None,
    emergence_ref: str | None = None,
) -> dict:
    if emergence_state is None:
        emergence = {
            "state": "UNESTIMABLE",
            "reason": "SOURCE_NOT_SUPPLIED",
            "source_system": None,
            "source_token": None,
            "source_ref": None,
        }
    else:
        emergence = {
            "state": emergence_state,
            "reason": None,
            "source_system": "turn_watch",
            "source_token": "B1_OBSERVED",
            "source_ref": emergence_ref,
        }
    return {
        "schema": "prophet.candidate_state/v1",
        "definition_era": B3_ERA,
        "episode_id": episode,
        "security_id": SECURITY_ID,
        "company_id": COMPANY_ID,
        "identity_epoch": "epoch_0",
        "candidate_generation_id": GENERATION,
        "episode_lifecycle": {
            "state": lifecycle,
            "source_state": source_state,
            "terminal_reason": None,
            "superseded_by": None,
        },
        "emergence_state": emergence,
        "maturity_state": {
            "state": "UNESTIMABLE",
            "reason": "SOURCE_NOT_SUPPLIED",
            "source_token": None,
        },
        "entry_availability": {"state": "UNAVAILABLE_DATA", "reason": "B4_NOT_AVAILABLE"},
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate_signal": False,
            "can_change_entry_open": False,
            "can_change_execution": False,
        },
    }


def _calendar_rows(session: str = SESSION, end: str = NEXT_SESSION_END) -> list[dict]:
    return [{"market_session": session, "next_session_end_utc": end}]


def _inputs(
    b1_rows: list[dict],
    *,
    prev_rows: list[dict] | None = None,
    curr_rows: list[dict] | None = None,
    calendar_rows: list[dict] | None = None,
    outbox_rows: list[dict] | None = None,
    b1_state: str = pjn.READ_OK,
    market_session: str | None = SESSION,
    now_utc: str | None = NOW,
    prev_state: str | None = None,
) -> pjn.JourneyInputs:
    return pjn.JourneyInputs(
        b1_events=pjn.TypedRead(b1_state, list(b1_rows)),
        projection_prev=pjn.TypedRead(
            prev_state or (pjn.READ_OK if prev_rows else pjn.READ_OK_ZERO),
            list(prev_rows or []),
        ),
        projection_curr=pjn.TypedRead(
            pjn.READ_OK if curr_rows else pjn.READ_OK_ZERO, list(curr_rows or [])
        ),
        session_calendar=pjn.TypedRead(
            pjn.READ_OK if calendar_rows is not None else pjn.READ_OK_ZERO,
            list(calendar_rows or []),
        ),
        existing_outbox=pjn.TypedRead(
            pjn.READ_OK if outbox_rows else pjn.READ_OK_ZERO, list(outbox_rows or [])
        ),
        candidate_generation_id=GENERATION,
        market_session=market_session,
        now_utc=now_utc,
    )


def _subs_rows(user_tickers: dict[str, tuple[str, ...]]) -> tuple[list[dict], list[dict]]:
    list_rows: list[dict] = []
    symbol_rows: list[dict] = []
    for index, user_id in enumerate(sorted(user_tickers)):
        list_id = f"wl-{index}"
        list_rows.append(
            {"id": list_id, "user_id": user_id, "name": pjn.DESIGNATED_LIST_NAME}
        )
        for ticker in user_tickers[user_id]:
            symbol_rows.append({"watchlist_id": list_id, "symbol": ticker})
    return list_rows, symbol_rows


def _subscriptions(user_tickers: dict[str, tuple[str, ...]]) -> dict[str, frozenset[str]]:
    list_rows, symbol_rows = _subs_rows(user_tickers)
    return pjn.build_subscriptions(list_rows, symbol_rows)


def _fid(event: pjn.JourneyEvent, user_id: str) -> str:
    return pjn.fire_event_id(
        kind=event.kind,
        episode_id=event.episode_id,
        from_state=event.from_state,
        to_state=event.to_state,
        b1_event_id=event.b1_event_id,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------
def test_constants_are_pinned():
    assert pjn.SCHEMA == "prophet.b21.journey_notifications/v1"
    assert pjn.SOURCE == "macro.prophet_journey_notifications"
    assert pjn.CATEGORY == "prophet_research_journey"
    assert pjn.CHANNEL == "email"
    assert pjn.DESIGNATED_LIST_NAME == "Prophet Research"
    assert pjn.REQUIRES_TIER == "essential"
    assert pjn.EVIDENCE_BASE == "https://www.mastermind-x.com"
    assert pjn.KINDS == (
        "episode_terminal",
        "emergence_triggered",
        "corrected_material",
        "retracted",
        "superseded",
    )
    assert pjn.MATERIAL_PATCH_FIELDS == ("terminal_reason", "ticker_at_observation")
    assert pjn.SUPPRESSION_KEYS == (
        "read_unavailable", "prev_projection_unavailable", "ineligible_event",
        "unknown_side", "no_subscriber", "already_fired", "banned_term",
        "not_after_unresolvable", "stale_transition_at_mint", "no_original",
        "original_quarantined", "original_producer_suppressed",
        "original_superseded_in_run",
    )
    assert pjn.PRODUCER_SUPPRESSED_REASON == "superseded_by_prophet_correction"
    assert pjn._BANNED_TERMS == ("falsif", "refut", "证伪")
    assert pjn.READ_OK == "READ_OK"
    assert pjn.READ_OK_ZERO == "READ_OK_ZERO"
    assert pjn.READ_UNAVAILABLE == "READ_UNAVAILABLE"
    assert pjn._ALERT_ID_NAMESPACE == uuid.UUID(
        "3f6b2d8e-9a41-5c07-b2e5-6d1f8a0c4b93"
    )
    # One namespace per producer: a shared one would let synthetic ids
    # collide across categories.
    assert pjn._ALERT_ID_NAMESPACE != fif._ALERT_ID_NAMESPACE


# ---------------------------------------------------------------------------
# 2. Tier — one paid literal, ranked by the plans catalog
# ---------------------------------------------------------------------------
def test_requires_tier_is_a_ranked_paid_tier():
    rank = tier_rank()
    assert rank is not None, "plans catalog unavailable — cannot rank REQUIRES_TIER"
    canonical = normalize_tier(pjn.REQUIRES_TIER)
    assert canonical in rank
    assert rank.index(canonical) > rank.index("free")


# ---------------------------------------------------------------------------
# 3. fire_event_id — literal + round trip
# ---------------------------------------------------------------------------
def test_fire_event_id_literal_and_round_trip():
    episode = "pe:SEC:US-XNAS-XYZ:epoch_0:sa:deadbeef:1"
    cause = "pee:" + "ab" * 32
    fid = pjn.fire_event_id(
        kind="superseded",
        episode_id=episode,
        from_state="ACTIVE",
        to_state="SUPERSEDED",
        b1_event_id=cause,
        user_id=USER_A,
    )
    assert fid == f"prophet|superseded|{episode}|ACTIVE->SUPERSEDED|{cause}|{USER_A}"
    parsed = pjn.parse_fire_event_id(fid)
    assert parsed == {
        "kind": "superseded",
        "episode_id": episode,
        "from_state": "ACTIVE",
        "to_state": "SUPERSEDED",
        "b1_event_id": cause,
        "user_id": USER_A,
    }
    # every kind round-trips
    for kind in pjn.KINDS:
        text = pjn.fire_event_id(
            kind=kind, episode_id=episode, from_state="NONE",
            to_state="TRIGGERED", b1_event_id=cause, user_id=USER_B,
        )
        assert pjn.parse_fire_event_id(text)["kind"] == kind
    # malformed shapes raise, never guess
    for bad in (
        fid + "|extra",
        "prophet|superseded|" + episode + "|ACTIVE->SUPERSEDED|" + cause,
        "prophet|made_up_kind|" + episode + "|ACTIVE->SUPERSEDED|" + cause + f"|{USER_A}",
        # a colon inside from/to cannot be told apart from the episode id's
        # own colon literal — rejected outright
        "prophet|superseded|" + episode + "|ACT:IVE->SUPERSEDED|" + cause + f"|{USER_A}",
        "prophet|superseded|" + episode + "|ACTIVE->SUPER->SEDED|" + cause + f"|{USER_A}",
        "prophet|superseded|" + episode + "|ACTIVESUPERSEDED|" + cause + f"|{USER_A}",
    ):
        try:
            pjn.parse_fire_event_id(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse accepted a malformed id: {bad!r}")


# ---------------------------------------------------------------------------
# 4. synthetic_alert_id
# ---------------------------------------------------------------------------
def test_synthetic_alert_id_is_uuid5_per_user_and_stable():
    expected_a = str(
        uuid.uuid5(pjn._ALERT_ID_NAMESPACE, f"prophet_watch:{USER_A}")
    )
    assert pjn.synthetic_alert_id(USER_A) == expected_a
    assert pjn.synthetic_alert_id(USER_A) == pjn.synthetic_alert_id(USER_A)
    assert pjn.synthetic_alert_id(USER_B) != expected_a
    assert pjn.synthetic_alert_id(USER_A) != fif.synthetic_alert_id(USER_A)


# ---------------------------------------------------------------------------
# 5. Unavailable read
# ---------------------------------------------------------------------------
def test_unavailable_read_yields_no_events_and_typed_count():
    events, counts = pjn.derive_events(
        _inputs([_open_envelope()], b1_state=pjn.READ_UNAVAILABLE)
    )
    assert events == []
    assert counts == {
        key: (1 if key == "read_unavailable" else 0) for key in pjn.SUPPRESSION_KEYS
    }


# ---------------------------------------------------------------------------
# 6. episode_terminal and the replicated B3 lifecycle table
# ---------------------------------------------------------------------------
def test_state_transitioned_terminal_uses_b3_lifecycle_pair():
    # The replicated table equals B3's own constants over B3's source set.
    for source_state in sorted(b3._SOURCE_EPISODE_STATES):
        assert (
            pjn._LIFECYCLE_BY_SOURCE[source_state]
            == b3._expected_lifecycle_state(source_state, None)
        ), source_state
    assert set(pjn._LIFECYCLE_BY_SOURCE) == set(b3._SOURCE_EPISODE_STATES)

    expected = {
        "RESOLVED": "CLOSED",
        "EXPIRED": "CLOSED",
        "INVALIDATED": "INVALIDATED",
        "RETRACTED": "RETRACTED",
    }
    for target, lifecycle in expected.items():
        ledger = [_open_envelope(), _transition_envelope(target)]
        events, _ = pjn.derive_events(_inputs(ledger))
        terminals = [e for e in events if e.kind == "episode_terminal"]
        assert len(terminals) == 1, target
        event = terminals[0]
        transition = ledger[1]
        assert (event.from_state, event.to_state) == ("ACTIVE", lifecycle)
        assert event.b1_event_id == transition["event_id"]
        assert event.fact_receipt == transition["content_sha256"]
        assert event.fired_at == transition["recorded_at"]
        assert event.definition_era == transition["definition_era"]
        assert event.episode_id == EPISODE
        assert (event.company_id, event.ticker) == (COMPANY_ID, "XYZ")


# ---------------------------------------------------------------------------
# 7. emergence_triggered across generations
# ---------------------------------------------------------------------------
def test_emergence_triggered_requires_real_relation_id_across_generations():
    relation = _relation_envelope()
    ledger = [_open_envelope(), relation]
    curr = _projection_row(
        emergence_state="TRIGGERED", emergence_ref=relation["event_id"]
    )

    # prev ARMED -> curr TRIGGERED with a real relation id: the event.
    events, counts = pjn.derive_events(
        _inputs(ledger, prev_rows=[_projection_row(emergence_state="ARMED")], curr_rows=[curr])
    )
    emergences = [e for e in events if e.kind == "emergence_triggered"]
    assert len(emergences) == 1
    event = emergences[0]
    assert (event.from_state, event.to_state) == ("NONE", "TRIGGERED")
    assert event.b1_event_id == relation["event_id"]
    assert event.fired_at == relation["recorded_at"]
    assert event.fact_receipt == relation["content_sha256"]
    assert counts["unknown_side"] == 0

    # absent in prev (first generation the episode appears triggered): still one
    events, _ = pjn.derive_events(_inputs(ledger, curr_rows=[curr]))
    assert len([e for e in events if e.kind == "emergence_triggered"]) == 1

    # prev already TRIGGERED: not a change, no count
    events, counts = pjn.derive_events(
        _inputs(
            ledger,
            prev_rows=[
                _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
            ],
            curr_rows=[curr],
        )
    )
    assert [e for e in events if e.kind == "emergence_triggered"] == []
    assert counts["unknown_side"] == 0

    # prev carrying the B3 default UNESTIMABLE filler is ABSENT evidence,
    # not a prior trigger: the event still derives (the unknown_side key for
    # emergence belongs to a missing relation id, never to the prev filler)
    events, counts = pjn.derive_events(
        _inputs(
            ledger,
            prev_rows=[_projection_row(emergence_state="UNESTIMABLE")],
            curr_rows=[curr],
        )
    )
    assert len([e for e in events if e.kind == "emergence_triggered"]) == 1
    assert counts["unknown_side"] == 0

    # no relation id at the B3 source_ref site: unknown side, never an event
    events, counts = pjn.derive_events(
        _inputs(
            ledger,
            prev_rows=[_projection_row(emergence_state="ARMED")],
            curr_rows=[_projection_row(emergence_state="TRIGGERED", emergence_ref=None)],
        )
    )
    assert events == []
    assert counts["unknown_side"] == 1

    # a malformed relation id is not a real relation id either
    events, counts = pjn.derive_events(
        _inputs(
            ledger,
            prev_rows=[_projection_row(emergence_state="ARMED")],
            curr_rows=[_projection_row(emergence_state="TRIGGERED", emergence_ref="pee:not-hex")],
        )
    )
    assert events == []
    assert counts["unknown_side"] == 1


# ---------------------------------------------------------------------------
# 8. corrected_material
# ---------------------------------------------------------------------------
def test_corrected_material_only_for_shown_fields():
    transition = _transition_envelope("EXPIRED")

    def _derived(patch: dict):
        return pjn.derive_events(
            _inputs([_open_envelope(), transition, _corrected_envelope(patch)])
        )

    events, _ = _derived({"terminal_reason": "re-priced exit"})
    corrections = [e for e in events if e.kind == "corrected_material"]
    assert len(corrections) == 1
    event = corrections[0]
    assert (event.from_state, event.to_state) == ("NONE", "corrected_material")
    assert "the closing reason changed" in event.condition_plain
    # the original it corrects is resolved at plan time from the outbox
    # readback (F28 R6, test_r6_*), never carried on the derived event
    assert not hasattr(event, "corrects")
    assert "a correction to the journey you were shown" in event.condition_plain
    assert "a correction to this research journey" in event.condition_plain_unsent

    events, _ = _derived({"ticker_at_observation": "ZYX"})
    assert "the ticker on record changed" in events[-1].condition_plain

    events, _ = _derived(
        {"terminal_reason": "re-priced exit", "ticker_at_observation": "ZYX"}
    )
    assert (
        "the closing reason changed and the ticker on record changed"
        in events[-1].condition_plain
    )

    # a patch on a non-material field alone is seen but never minted
    events, counts = _derived({"opened_at": "2026-08-01T00:00:00Z"})
    assert [e for e in events if e.kind == "corrected_material"] == []
    assert counts["ineligible_event"] >= 1


# ---------------------------------------------------------------------------
# 9. retracted / superseded glance text
# ---------------------------------------------------------------------------
def test_retracted_and_superseded_kinds_keep_machine_ids_out_of_glance_text():
    opened = _open_envelope()
    successor = OTHER_EPISODE
    ledger = [
        opened,
        _retracted_envelope(opened["event_id"]),
        _superseded_envelope(successor),
    ]
    events, _ = pjn.derive_events(_inputs(ledger))
    by_kind = {event.kind: event for event in events}
    assert set(by_kind) == {"retracted", "superseded"}

    retracted = by_kind["retracted"]
    assert (retracted.from_state, retracted.to_state) == ("ACTIVE", "RETRACTED")
    assert retracted.condition_plain == (
        "XYZ: this name is no longer tracked; the earlier notice is withdrawn."
    )
    assert retracted.subject == "XYZ Prophet journey: withdrawn"

    superseded = by_kind["superseded"]
    assert (superseded.from_state, superseded.to_state) == ("ACTIVE", "SUPERSEDED")
    assert superseded.condition_plain == (
        "XYZ: this opportunity continues under a successor identity."
    )
    assert superseded.subject == "XYZ Prophet journey: successor"

    for event in (retracted, superseded):
        for text in (event.condition_plain, event.subject):
            lowered = text.lower()
            assert successor not in text
            assert EPISODE not in text
            assert "pe:" not in lowered and "pee:" not in lowered
            assert "|" not in text


# ---------------------------------------------------------------------------
# 10. Never-eligible events
# ---------------------------------------------------------------------------
def test_never_eligible_events_are_ignored():
    observed = _relation_envelope()
    ledger = [
        _open_envelope(),
        observed,
        _envelope(
            "EXPERT_EVENT_ATTACHED",
            payload={"expert_event_id": "expert-1"},
            source_event_id="expert:1",
            recorded_at="2026-08-25T02:20:00Z",
        ),
        _envelope(
            "REARM_SUPPRESSED",
            payload={"reason": "rearm window closed"},
            source_event_id="rearm:1",
            recorded_at="2026-08-25T02:30:00Z",
        ),
    ]
    events, counts = pjn.derive_events(_inputs(ledger))
    assert events == []
    # OPENED (v1 seat ruling), OBSERVED, EXPERT_EVENT_ATTACHED and
    # REARM_SUPPRESSED are each seen once and counted, never minted.
    assert counts["ineligible_event"] == 4

    # a repeated identical event (same content-addressed event_id) derives
    # ONE event and the duplicate copy costs nothing
    transition = _transition_envelope("EXPIRED")
    events, _ = pjn.derive_events(_inputs([_open_envelope(), transition, dict(transition)]))
    terminals = [e for e in events if e.kind == "episode_terminal"]
    assert len(terminals) == 1

    # a RETRACTED of an engine-internal relation is not a shown relation
    expert = ledger[2]
    events, counts = pjn.derive_events(
        _inputs(
            [
                _open_envelope(),
                expert,
                _retracted_envelope(expert["event_id"]),
            ]
        )
    )
    assert [e for e in events if e.kind == "retracted"] == []
    assert counts["ineligible_event"] >= 1


# ---------------------------------------------------------------------------
# 11. Unknown sides
# ---------------------------------------------------------------------------
def test_unestimable_or_unavailable_side_is_not_a_change():
    opened = _open_envelope()

    # F28 R1: the retracted/superseded from side is the B1 replay state, so
    # an UNAVAILABLE_DATA prev lifecycle neither suppresses nor re-keys it
    for ledger, kind, pair in (
        ([opened, _retracted_envelope(opened["event_id"])], "retracted", ("ACTIVE", "RETRACTED")),
        ([opened, _superseded_envelope()], "superseded", ("ACTIVE", "SUPERSEDED")),
    ):
        events, counts = pjn.derive_events(
            _inputs(ledger, prev_rows=[_projection_row(lifecycle="UNAVAILABLE_DATA")])
        )
        assert [(e.from_state, e.to_state) for e in events if e.kind == kind] == [pair]
        assert counts["unknown_side"] == 0

    relation = _relation_envelope()
    triggered = _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])

    # the emergence side's unknown is the RELATION ID (test 7 pins that the
    # prev UNESTIMABLE filler itself never suppresses)
    events, counts = pjn.derive_events(
        _inputs(
            [opened, relation],
            prev_rows=[_projection_row(emergence_state="ARMED")],
            curr_rows=[
                _projection_row(emergence_state="TRIGGERED", emergence_ref=None)
            ],
        )
    )
    assert [e for e in events if e.kind == "emergence_triggered"] == []
    assert counts["unknown_side"] == 1

    # a prior emergence of UNAVAILABLE_DATA is still unknown (F28 R8 relaxes
    # only the absent/UNESTIMABLE prior)
    events, counts = pjn.derive_events(
        _inputs(
            [opened, relation],
            prev_rows=[_projection_row(emergence_state="UNAVAILABLE_DATA")],
            curr_rows=[triggered],
        )
    )
    assert events == []
    assert counts["unknown_side"] == 1

    # a current lifecycle of UNAVAILABLE_DATA is an unknown side as well
    events, counts = pjn.derive_events(
        _inputs(
            [opened, relation],
            prev_rows=[_projection_row(emergence_state="ARMED")],
            curr_rows=[
                {**triggered, "episode_lifecycle": {**triggered["episode_lifecycle"], "state": "UNAVAILABLE_DATA"}}
            ],
        )
    )
    assert events == []
    assert counts["unknown_side"] == 1


# ---------------------------------------------------------------------------
# 12. Payload key set and glance hygiene
# ---------------------------------------------------------------------------
def test_payload_key_set_and_glance_text_are_clean():
    relation = _relation_envelope()
    opened = _open_envelope()
    ledger = [
        relation,
        opened,
        _transition_envelope("EXPIRED"),
        _corrected_envelope({"terminal_reason": "re-priced exit"}),
        # B1 RETRACTED targets a relation (OPENED/OBSERVED), never a
        # STATE_TRANSITIONED event — the fixture targets the OPENED one.
        _retracted_envelope(opened["event_id"]),
        _superseded_envelope(),
    ]
    events, _ = pjn.derive_events(
        _inputs(
            ledger,
            prev_rows=[_projection_row(emergence_state="ARMED")],
            curr_rows=[
                _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
            ],
        )
    )
    assert {event.kind for event in events} == set(pjn.KINDS)
    subscriptions = _subscriptions({USER_A: ("XYZ",)})
    plan = pjn.plan_enqueue(
        events,
        subscriptions,
        inputs=_inputs(ledger, calendar_rows=_calendar_rows()),
        existing_outbox_rows=[],
    )
    # F28 R5/R6: each correction kind corrects the latest EARLIER notice of
    # the episode for the user (B1 replay order, any kind). Here every
    # original was minted earlier in THIS run, so it is born suppressed
    # (its fire id still dedupes later runs) and every kind mints one row.
    by_kind = {row["payload"]["kind"]: row for row in plan.rows}
    assert sorted(by_kind) == sorted(pjn.KINDS)
    assert len(plan.rows) == len(pjn.KINDS)
    assert plan.suppressed["no_original"] == 0
    assert plan.suppressed["original_superseded_in_run"] == 3
    assert plan.patches == []
    assert {kind: row["status"] for kind, row in by_kind.items()} == {
        "emergence_triggered": "pending",
        "episode_terminal": "suppressed",
        "corrected_material": "suppressed",
        "retracted": "suppressed",
        "superseded": "pending",
    }
    for kind in ("episode_terminal", "corrected_material", "retracted"):
        assert by_kind[kind]["last_error"] == pjn.PRODUCER_SUPPRESSED_REASON
    fid = {kind: row["fire_event_id"] for kind, row in by_kind.items()}
    assert by_kind["corrected_material"]["payload"]["corrects_fire_event_id"] == fid["episode_terminal"]
    assert by_kind["retracted"]["payload"]["corrects_fire_event_id"] == fid["corrected_material"]
    assert by_kind["superseded"]["payload"]["corrects_fire_event_id"] == fid["retracted"]
    # none of these originals ever reached the reader: non-presuming copy
    assert by_kind["corrected_material"]["payload"]["condition_plain"] == (
        "XYZ: a correction to this research journey — the closing reason changed."
    )
    assert by_kind["retracted"]["payload"]["condition_plain"] == (
        "XYZ: this name is no longer tracked."
    )
    row = by_kind["episode_terminal"]
    payload = row["payload"]
    assert set(payload) == EXPECTED_PAYLOAD_KEYS
    assert payload["category"] == pjn.CATEGORY
    assert payload["requires_tier"] == "essential"
    assert payload["kind"] == "episode_terminal"
    assert payload["source"] == pjn.SOURCE
    assert payload["schema"] == pjn.SCHEMA
    assert payload["event_date"] == payload["fired_at"][:10]
    assert payload["candidate_generation_id"] == GENERATION
    assert payload["market_session"] == SESSION
    assert payload["corrects_fire_event_id"] is None
    assert payload["evidence_url"] == (
        "https://www.mastermind-x.com/us_stocks.html#us-standouts"
    )

    # glance hygiene over every derived kind, not just the minted row
    for event in events:
        for text in (event.condition_plain, event.condition_plain_unsent, event.subject):
            assert pjn._MACHINE_ID_RE.search(text) is None
            lowered = text.lower()
            assert not any(term in lowered for term in pjn._BANNED_TERMS)
            assert "fire_event_id" not in lowered
            assert "pee:" not in lowered and "pe:" not in lowered
            assert "|" not in text
            assert EPISODE not in text
        assert len(event.subject) <= 78

    # the evidence base is a parameter, not a hidden constant
    plan_custom = pjn.plan_enqueue(
        [e for e in events if e.kind == "episode_terminal"],
        subscriptions,
        inputs=_inputs(ledger, calendar_rows=_calendar_rows()),
        existing_outbox_rows=[],
        evidence_base="https://example.test/",
    )
    assert plan_custom.rows[0]["payload"]["evidence_url"] == (
        "https://example.test/us_stocks.html#us-standouts"
    )


# ---------------------------------------------------------------------------
# 13. not_after
# ---------------------------------------------------------------------------
def test_not_after_from_session_calendar_and_fail_closed():
    ledger = [_open_envelope(), _transition_envelope("EXPIRED")]
    events, _ = pjn.derive_events(_inputs(ledger))
    terminal = events[-1]
    # the transition's own session is its B1 known_at UTC date (F28 R2)
    assert terminal.market_session == SESSION
    subscriptions = _subscriptions({USER_A: ("XYZ",)})

    def _plan(*, calendar_rows, market_session=SESSION):
        return pjn.plan_enqueue(
            [terminal],
            subscriptions,
            inputs=_inputs(
                ledger, calendar_rows=calendar_rows, market_session=market_session
            ),
            existing_outbox_rows=[],
        )

    plan = _plan(calendar_rows=_calendar_rows())
    assert plan.rows[0]["payload"]["not_after"] == NEXT_SESSION_END
    assert plan.rows[0]["payload"]["market_session"] == SESSION

    # fractional seconds are carried VERBATIM
    plan = _plan(
        calendar_rows=_calendar_rows(end="2026-08-26T00:00:00.123456Z")
    )
    assert plan.rows[0]["payload"]["not_after"] == "2026-08-26T00:00:00.123456Z"

    # the RUN's market_session is provenance only: not_after never reads it
    plan = _plan(calendar_rows=_calendar_rows(), market_session=None)
    assert plan.rows[0]["payload"]["not_after"] == NEXT_SESSION_END

    # no calendar row for the transition's (weekday) session, an
    # unparsable end, or two conflicting ends: no row, typed
    # not_after_unresolvable — a row never ships without its bound.
    for calendar_rows in (
        _calendar_rows(session="2026-08-24"),
        _calendar_rows(end="not-a-clock"),
        _calendar_rows() + _calendar_rows(end="2026-08-26T01:00:00Z"),
        [],
    ):
        plan = _plan(calendar_rows=calendar_rows)
        assert plan.rows == []
        assert plan.suppressed["not_after_unresolvable"] == 1
        assert plan.suppressed["stale_transition_at_mint"] == 0


# ---------------------------------------------------------------------------
# 14. Dedupe and no-leak
# ---------------------------------------------------------------------------
def test_plan_enqueue_dedupes_per_user_and_never_leaks_across_users():
    third_anchor = {**ANCHOR, "time": "2026-08-22T20:00:00Z"}
    third_episode = b1_episode_id(SECURITY_ID, "epoch_0", third_anchor, 1)
    ledger = [
        _open_envelope(ticker="XYZ"),
        _open_envelope(ticker="OTHER", episode=OTHER_EPISODE, anchor=OTHER_ANCHOR),
        _open_envelope(ticker="LONELY", episode=third_episode, anchor=third_anchor),
        _transition_envelope("EXPIRED"),  # XYZ
        _transition_envelope(
            "RESOLVED", episode=OTHER_EPISODE, recorded_at="2026-08-25T03:30:00Z"
        ),
        _envelope(
            "STATE_TRANSITIONED",
            payload={"episode_state": "INVALIDATED", "terminal_reason": "x"},
            episode=third_episode,
            source_event_id="episode:lonely",
            recorded_at="2026-08-25T03:40:00Z",
        ),
    ]
    events, _ = pjn.derive_events(_inputs(ledger))
    terminals = [e for e in events if e.kind == "episode_terminal"]
    assert {e.ticker for e in terminals} == {"XYZ", "OTHER", "LONELY"}

    subscriptions = _subscriptions({USER_A: ("XYZ",), USER_B: ("OTHER",)})
    plan = pjn.plan_enqueue(
        events,
        subscriptions,
        inputs=_inputs(ledger, calendar_rows=_calendar_rows()),
        existing_outbox_rows=[],
    )
    # one row per (event, user) inside each user's OWN partition
    assert len(plan.rows) == 2
    assert plan.users_n == 2 and plan.symbols_n == 2
    assert plan.events_n == 2
    assert plan.suppressed["no_subscriber"] == 1
    by_user = {row["user_id"]: row for row in plan.rows}
    assert set(by_user) == {USER_A, USER_B}
    assert by_user[USER_A]["payload"]["ticker"] == "XYZ"
    assert by_user[USER_B]["payload"]["ticker"] == "OTHER"
    for user_id, row in by_user.items():
        assert row["user_id"] == user_id
        assert row["fire_event_id"].endswith(user_id)
        assert row["alert_id"] == pjn.synthetic_alert_id(user_id)
        assert row["channel"] == pjn.CHANNEL
        assert row["status"] == "pending"
        assert row["attempts"] == 0
        assert row["last_error"] is None
        assert set(row) == {
            "user_id", "alert_id", "fire_event_id", "channel", "status",
            "attempts", "last_error", "payload",
        }
    # B never receives A's XYZ row and vice versa — already implied by the
    # partition above, pinned explicitly:
    assert "XYZ" not in by_user[USER_B]["payload"]["ticker"]
    assert "OTHER" not in by_user[USER_A]["payload"]["ticker"]

    # replay: every minted fid already in the outbox -> duplicates only
    replay = pjn.plan_enqueue(
        events,
        subscriptions,
        inputs=_inputs(ledger, calendar_rows=_calendar_rows()),
        existing_outbox_rows=[{"fire_event_id": row["fire_event_id"], "status": "sent", "attempts": 1, "last_error": None} for row in plan.rows],
    )
    assert replay.rows == []
    assert replay.duplicate_n == 2
    assert replay.suppressed["already_fired"] == 2


# ---------------------------------------------------------------------------
# 15. The correction original-status table (all five branches)
# ---------------------------------------------------------------------------
def test_correction_rows_follow_the_original_status_table():
    opened = _open_envelope()
    terminal_env = _transition_envelope("EXPIRED")
    correction_env = _corrected_envelope({"terminal_reason": "re-priced exit"})
    ledger = [opened, terminal_env, correction_env]
    events, _ = pjn.derive_events(_inputs(ledger))
    terminal = [e for e in events if e.kind == "episode_terminal"][0]
    correction = [e for e in events if e.kind == "corrected_material"][0]
    original_fid = _fid(terminal, USER_A)
    subscriptions = _subscriptions({USER_A: ("XYZ",)})
    presuming = "XYZ: a correction to the journey you were shown — the closing reason changed."
    unsent = "XYZ: a correction to this research journey — the closing reason changed."
    patch = pjn.PlannedPatch(
        fire_event_id=original_fid,
        status="suppressed",
        last_error="superseded_by_prophet_correction",
    )

    def _plan(outbox_rows, plan_events=None):
        return pjn.plan_enqueue(
            events if plan_events is None else plan_events,
            subscriptions,
            inputs=_inputs(ledger, calendar_rows=_calendar_rows(), outbox_rows=outbox_rows),
            existing_outbox_rows=outbox_rows,
        )

    def _original_row(status, attempts=1, last_error=None):
        return {
            "fire_event_id": original_fid,
            "status": status,
            "attempts": attempts,
            "last_error": last_error,
        }

    def _corrections(plan):
        return [r for r in plan.rows if r["payload"]["kind"] == "corrected_material"]

    # no original anywhere (readback empty, original not in this run):
    # nothing minted, typed no_original.
    absent = _plan([], plan_events=[correction])
    assert absent.rows == [] and absent.patches == []
    assert absent.suppressed["no_original"] == 1

    # original minted earlier in THIS run: born suppressed, correction row
    # in the non-presuming copy (F28 R5).
    in_run = _plan([])
    assert {r["payload"]["kind"]: r["status"] for r in in_run.rows} == {
        "episode_terminal": "suppressed",
        "corrected_material": "pending",
    }
    assert in_run.suppressed["original_superseded_in_run"] == 1
    assert in_run.suppressed["no_original"] == 0
    assert _corrections(in_run)[0]["payload"]["corrects_fire_event_id"] == original_fid
    assert _corrections(in_run)[0]["payload"]["condition_plain"] == unsent

    # unsent original: pending / deferred / failed under the retry cap —
    # the original is PATCH-suppressed AND the correction row is minted in
    # the same run, in the non-presuming copy (contract §4, F28 R5).
    for status, attempts, last_error in (
        ("pending", 0, None),
        ("deferred", 1, "quiet_hours"),
        ("failed", 2, "smtp_5xx"),
        # residual cell: failed at cap with a definitive error still cannot
        # ever send again, so the one-email guarantee holds via the patch
        ("failed", 3, "smtp_refused"),
    ):
        plan = _plan([_original_row(status, attempts, last_error)])
        assert plan.patches == [patch], (status, attempts, last_error)
        corrections = _corrections(plan)
        assert len(corrections) == 1, (status, attempts, last_error)
        assert corrections[0]["payload"]["corrects_fire_event_id"] == original_fid
        assert corrections[0]["payload"]["condition_plain"] == unsent
        assert corrections[0]["status"] == "pending"
        # the original's own pair is a duplicate: its row already exists
        assert plan.suppressed["already_fired"] == 1
        assert plan.suppressed["no_original"] == 0

    # sent original: never touched, correction row only, presuming copy
    plan = _plan([_original_row("sent", 1, None)])
    assert plan.patches == []
    corrections = _corrections(plan)
    assert len(corrections) == 1
    assert corrections[0]["payload"]["corrects_fire_event_id"] == original_fid
    assert corrections[0]["payload"]["condition_plain"] == presuming

    # suppressed by the user's own prefs: mint anyway — the drain re-decides
    # from live prefs — and never presume the reader saw the original
    plan = _plan([_original_row("suppressed", 0, "entitlement_lapsed")])
    assert plan.patches == []
    corrections = _corrections(plan)
    assert len(corrections) == 1
    assert corrections[0]["payload"]["condition_plain"] == unsent

    # suppressed by THIS producer: an earlier correction already replaced it
    # — never re-read as an opt-out, nothing minted (F28 R5)
    plan = _plan([_original_row("suppressed", 0, "superseded_by_prophet_correction")])
    assert plan.patches == []
    assert _corrections(plan) == []
    assert plan.suppressed["original_producer_suppressed"] == 1

    # quarantined original: nothing minted, typed count
    plan = _plan(
        [_original_row("failed", 3, "effect_unknown_after_smtp")]
    )
    assert plan.patches == []
    assert _corrections(plan) == []
    assert plan.suppressed["original_quarantined"] == 1


# ---------------------------------------------------------------------------
# 16. Banned terms suppress at persist
# ---------------------------------------------------------------------------
def test_banned_terms_suppress_at_persist():
    clean = pjn.JourneyEvent(
        kind="episode_terminal",
        episode_id=EPISODE,
        company_id=COMPANY_ID,
        ticker="XYZ",
        from_state="ACTIVE",
        to_state="CLOSED",
        b1_event_id="pee:" + "cd" * 32,
        fact_receipt="sha256:" + "ef" * 32,
        definition_era=ERA,
        condition_plain="XYZ: the Prophet research journey you follow has closed — it ran its course.",
        subject="XYZ Prophet journey: closed",
        fired_at="2026-08-25T03:00:00Z",
        market_session=SESSION,
    )
    banned_condition = pjn.JourneyEvent(
        **{
            **clean.__dict__,
            "condition_plain": "XYZ: this thesis was falsified by later facts.",
        }
    )
    banned_subject = pjn.JourneyEvent(
        **{
            **clean.__dict__,
            "subject": "XYZ|terminal",
        }
    )
    subscriptions = _subscriptions({USER_A: ("XYZ",)})
    inputs = _inputs([], calendar_rows=_calendar_rows())

    plan = pjn.plan_enqueue(
        [clean], subscriptions, inputs=inputs, existing_outbox_rows=[]
    )
    assert len(plan.rows) == 1

    plan = pjn.plan_enqueue(
        [banned_condition], subscriptions, inputs=inputs, existing_outbox_rows=[]
    )
    assert plan.rows == []
    assert plan.suppressed["banned_term"] == 1

    plan = pjn.plan_enqueue(
        [banned_subject], subscriptions, inputs=inputs, existing_outbox_rows=[]
    )
    assert plan.rows == []
    assert plan.suppressed["banned_term"] == 1


# ---------------------------------------------------------------------------
# 17. Purity — no repo imports, no IO, stdlib only
# ---------------------------------------------------------------------------
def test_module_is_pure_and_imports_no_repo_modules():
    source = (ROOT / "engine" / "prophet_journey_notifications.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "engine.", "app.", "lib.", "scripts.", "psycopg", "requests",
        "urllib", "os.environ", "open(",
    ):
        assert forbidden not in source, forbidden
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    imported.discard("__future__")
    assert imported, "expected at least the stdlib imports the module uses"
    for module in sorted(imported):
        assert module in sys.stdlib_module_names, module


# ---------------------------------------------------------------------------
# 18. Determinism
# ---------------------------------------------------------------------------
def test_plan_is_deterministic():
    opened = _open_envelope()
    relation = _relation_envelope()
    ledger = [
        opened,
        relation,
        _transition_envelope("EXPIRED"),
        _corrected_envelope({"terminal_reason": "re-priced exit"}),
    ]
    inputs = _inputs(
        ledger,
        prev_rows=[_projection_row(emergence_state="ARMED")],
        curr_rows=[
            _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
        ],
        calendar_rows=_calendar_rows(),
    )
    events, _ = pjn.derive_events(inputs)
    subscriptions = _subscriptions({USER_A: ("XYZ",), USER_B: ("XYZ",)})

    first = pjn.plan_enqueue(
        events, subscriptions, inputs=inputs, existing_outbox_rows=[]
    )
    second = pjn.plan_enqueue(
        list(reversed(events)),  # caller order must not matter
        {user: symbols for user, symbols in reversed(list(subscriptions.items()))},
        inputs=inputs,
        existing_outbox_rows=[],
    )
    assert second.rows == first.rows
    assert second.patches == first.patches
    assert second.suppressed == first.suppressed
    assert (second.users_n, second.symbols_n, second.events_n, second.duplicate_n) == (
        first.users_n, first.symbols_n, first.events_n, first.duplicate_n
    )
    # rows carry a total order: (ticker, fired_at, kind, user_id)
    keys = [
        (
            row["payload"]["ticker"],
            row["payload"]["fired_at"],
            row["payload"]["kind"],
            row["user_id"],
        )
        for row in first.rows
    ]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# F28 R1–R10 — the seat's repair rulings, one named test each
# ---------------------------------------------------------------------------

def _sent(rows: list[dict]) -> list[dict]:
    return [
        {
            "fire_event_id": row["fire_event_id"],
            "status": "sent",
            "attempts": 1,
            "last_error": None,
        }
        for row in rows
    ]


def _pairs(events: list, kind: str) -> list[tuple[str, str]]:
    return [(e.from_state, e.to_state) for e in events if e.kind == kind]


def test_r1_from_state_is_the_b1_replay_state_and_stable_across_runs():
    # F28 R1: from_state is the B1 replay state just before the causing
    # event, never projection_prev, so the fire id does not drift when the
    # projection advances between runs.
    opened = _open_envelope()
    ledger = [opened, _transition_envelope("EXPIRED"), _superseded_envelope()]
    subscriptions = _subscriptions({USER_A: ("XYZ",)})

    run1 = _inputs(
        ledger,
        prev_rows=[_projection_row(lifecycle="ACTIVE")],
        calendar_rows=_calendar_rows(),
    )
    run2 = _inputs(
        ledger,
        prev_rows=[_projection_row(lifecycle="SUPERSEDED", source_state="EXPIRED")],
        calendar_rows=_calendar_rows(),
    )
    events1, _ = pjn.derive_events(run1)
    events2, _ = pjn.derive_events(run2)
    assert _pairs(events1, "superseded") == [("CLOSED", "SUPERSEDED")]
    assert _pairs(events2, "superseded") == [("CLOSED", "SUPERSEDED")]
    assert [_fid(e, USER_A) for e in events1] == [_fid(e, USER_A) for e in events2]

    plan1 = pjn.plan_enqueue(events1, subscriptions, inputs=run1, existing_outbox_rows=[])
    assert sorted(r["payload"]["kind"] for r in plan1.rows) == ["episode_terminal", "superseded"]
    readback = _sent(plan1.rows)
    plan2 = pjn.plan_enqueue(
        events2, subscriptions, inputs=run2, existing_outbox_rows=readback
    )
    assert plan2.rows == [] and plan2.patches == []
    assert plan2.suppressed["already_fired"] == 2

    # a retraction after INVALIDATED keeps the replayed INVALIDATED from side
    ledger = [opened, _transition_envelope("INVALIDATED"), _retracted_envelope(opened["event_id"])]
    events, _ = pjn.derive_events(
        _inputs(ledger, prev_rows=[_projection_row(lifecycle="ACTIVE")])
    )
    assert _pairs(events, "retracted") == [("INVALIDATED", "RETRACTED")]


def test_r1_replay_uses_canonical_known_at_order():
    # B1 replays by (known_at, source_system, source_event_id), not by
    # recorded_at or input order: the transition KNOWN at 03:00 but recorded
    # at 09:00 still precedes a supersession known and recorded at 06:00.
    late_recorded_terminal = _envelope(
        "STATE_TRANSITIONED",
        payload={"episode_state": "EXPIRED", "terminal_reason": "episode ran out"},
        source_event_id=f"episode:{EPISODE}:EXPIRED",
        known_at="2026-08-25T03:00:00Z",
        recorded_at="2026-08-25T09:00:00Z",
    )
    superseded = _superseded_envelope(recorded_at="2026-08-25T06:00:00Z")
    events, _ = pjn.derive_events(
        _inputs([_open_envelope(), superseded, late_recorded_terminal])
    )
    assert _pairs(events, "episode_terminal") == [("ACTIVE", "CLOSED")]
    assert _pairs(events, "superseded") == [("CLOSED", "SUPERSEDED")]
    assert [e.kind for e in events] == ["episode_terminal", "superseded"]


def test_derive_events_is_input_order_invariant():
    opened = _open_envelope()
    relation = _relation_envelope()
    ledger = [
        opened,
        relation,
        _transition_envelope("EXPIRED"),
        _corrected_envelope({"terminal_reason": "re-priced exit"}),
        _retracted_envelope(opened["event_id"]),
        _superseded_envelope(),
    ]
    triggered = _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
    kwargs = dict(
        prev_rows=[_projection_row(emergence_state="ARMED")], curr_rows=[triggered]
    )
    baseline = pjn.derive_events(_inputs(ledger, **kwargs))
    assert len(baseline[0]) == 5
    for permuted in (
        list(reversed(ledger)),
        [ledger[i] for i in (3, 5, 0, 4, 1, 2)],
        ledger + [ledger[2]],  # a repeated identical event is placed once
    ):
        assert pjn.derive_events(_inputs(permuted, **kwargs)) == baseline


def test_r2_not_after_anchors_on_the_transition_session_and_stale_never_mints():
    ledger = [_open_envelope(), _transition_envelope("EXPIRED")]
    subscriptions = _subscriptions({USER_A: ("XYZ",)})

    def _plan(ledger, *, calendar_rows, now_utc, market_session=SESSION):
        inputs = _inputs(
            ledger,
            calendar_rows=calendar_rows,
            now_utc=now_utc,
            market_session=market_session,
        )
        events, _ = pjn.derive_events(inputs)
        return pjn.plan_enqueue(events, subscriptions, inputs=inputs, existing_outbox_rows=[])

    # a six-month-old transition replayed by a run in 2027: its own bound
    # (the session after 2026-08-25) has long passed — never minted
    later = ("2027-03-01", "2027-03-02T21:00:00Z")
    plan = _plan(
        ledger,
        calendar_rows=_calendar_rows() + _calendar_rows(*later),
        now_utc="2027-03-01T22:00:00Z",
        market_session=later[0],
    )
    assert plan.rows == []
    assert plan.suppressed["stale_transition_at_mint"] == 1
    # ... and with only the run's own calendar row it is unresolvable — the
    # run's session never lends the old fact a fresh bound
    plan = _plan(
        ledger,
        calendar_rows=_calendar_rows(*later),
        now_utc="2027-03-01T22:00:00Z",
        market_session=later[0],
    )
    assert plan.rows == []
    assert plan.suppressed["not_after_unresolvable"] == 1

    # the bound is exclusive: now == not_after is stale, one second before mints
    plan = _plan(ledger, calendar_rows=_calendar_rows(), now_utc=NEXT_SESSION_END)
    assert plan.rows == [] and plan.suppressed["stale_transition_at_mint"] == 1
    plan = _plan(ledger, calendar_rows=_calendar_rows(), now_utc="2026-08-25T23:59:59Z")
    assert len(plan.rows) == 1
    # a run without a clock cannot prove freshness: fail closed
    plan = _plan(ledger, calendar_rows=_calendar_rows(), now_utc=None)
    assert plan.rows == [] and plan.suppressed["stale_transition_at_mint"] == 1

    # a transition known on a Saturday has no calendar row of its own: the
    # neighbouring Friday row is never borrowed (seat ruling, F28 follow-up),
    # so the fact is typed unresolvable rather than minted against a session
    # that did not observe it
    saturday = [_open_envelope(), _transition_envelope("EXPIRED", recorded_at="2026-08-29T15:00:00Z")]
    plan = _plan(
        saturday,
        calendar_rows=_calendar_rows("2026-08-28", "2026-08-31T20:00:00Z"),
        now_utc="2026-08-30T12:00:00Z",
    )
    assert plan.rows == []
    assert plan.suppressed["not_after_unresolvable"] == 1
    # a weekday with no row (holiday or calendar gap) never borrows one
    wednesday = [_open_envelope(), _transition_envelope("EXPIRED", recorded_at="2026-08-26T15:00:00Z")]
    plan = _plan(
        wednesday, calendar_rows=_calendar_rows(), now_utc="2026-08-26T16:00:00Z"
    )
    assert plan.rows == []
    assert plan.suppressed["not_after_unresolvable"] == 1


def test_r3_machine_id_guard_matches_the_id_form():
    # F28 R3: the guard matches B1's id FORM (pe:/pee:<hex>), so a ticker
    # that merely contains "PE" — HPE — still mints.
    anchor = {**ANCHOR, "time": "2026-08-21T20:00:00Z"}
    episode = b1_episode_id("SEC:US-XNYS-HPE", "epoch_0", anchor, 1)
    ledger = [
        _open_envelope(ticker="HPE", episode=episode, anchor=anchor),
        _transition_envelope("INVALIDATED", episode=episode),
    ]
    inputs = _inputs(ledger, calendar_rows=_calendar_rows())
    events, _ = pjn.derive_events(inputs)
    plan = pjn.plan_enqueue(
        events, _subscriptions({USER_A: ("HPE",)}), inputs=inputs, existing_outbox_rows=[]
    )
    assert len(plan.rows) == 1
    assert plan.suppressed["banned_term"] == 0
    assert plan.rows[0]["payload"]["condition_plain"].startswith("HPE: ")

    for clean in ("HPE: the journey closed.", "TAPE: x", "PE: x", "a recipe: fine"):
        assert pjn._glance_is_clean(clean), clean
    for dirty in (EPISODE, f"XYZ {EPISODE}", "pee:ab", "peg:ab", "x fire_event_id", "a|b"):
        assert not pjn._glance_is_clean(dirty), dirty


def test_r4_non_terminal_state_transitioned_mints_nothing():
    opened = _open_envelope()

    def _transition(payload: dict, sid: str) -> dict:
        return _envelope(
            "STATE_TRANSITIONED",
            payload=payload,
            source_event_id=f"episode:{EPISODE}:{sid}",
            recorded_at="2026-08-25T03:00:00Z",
        )

    for payload in (
        {"episode_state": "ACTIVE", "terminal_reason": "x"},
        {"terminal_reason": "x"},
        {"episode_state": "BOGUS", "terminal_reason": "x"},
        {"episode_state": "INVALIDATED"},
        {"episode_state": "INVALIDATED", "terminal_reason": "  "},
    ):
        events, counts = pjn.derive_events(
            _inputs([opened, _transition(payload, "t")])
        )
        assert events == [], payload
        assert counts["ineligible_event"] == 2, payload  # OPENED + the transition

    # a second terminal on an already-terminal episode changes nothing
    events, counts = pjn.derive_events(
        _inputs([opened, _transition_envelope("EXPIRED"), _transition_envelope("INVALIDATED", recorded_at="2026-08-25T04:00:00Z")])
    )
    assert _pairs(events, "episode_terminal") == [("ACTIVE", "CLOSED")]
    assert counts["ineligible_event"] == 2

    # emergence on a journey that is no longer ACTIVE is not a notice
    relation = _relation_envelope()
    triggered = _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
    base_events, base_counts = pjn.derive_events(
        _inputs([opened, relation], prev_rows=[_projection_row(emergence_state="ARMED")], curr_rows=[triggered])
    )
    assert [e.kind for e in base_events] == ["emergence_triggered"]
    for lifecycle in ("CLOSED", "INVALIDATED", "RETRACTED", "SUPERSEDED"):
        closed = {**triggered, "episode_lifecycle": {**triggered["episode_lifecycle"], "state": lifecycle}}
        events, counts = pjn.derive_events(
            _inputs([opened, relation], prev_rows=[_projection_row(emergence_state="ARMED")], curr_rows=[closed])
        )
        assert events == [], lifecycle
        assert counts["ineligible_event"] == base_counts["ineligible_event"] + 1
        assert counts["unknown_side"] == 0


def test_r5_producer_suppressed_original_is_never_reread_as_opt_out():
    opened = _open_envelope()
    subscriptions = _subscriptions({USER_A: ("XYZ",)})
    ledger = [opened, _transition_envelope("EXPIRED"), _retracted_envelope(opened["event_id"])]
    inputs = _inputs(ledger, calendar_rows=_calendar_rows())
    events, _ = pjn.derive_events(inputs)
    terminal_fid = _fid([e for e in events if e.kind == "episode_terminal"][0], USER_A)
    retracted_fid = _fid([e for e in events if e.kind == "retracted"][0], USER_A)

    def _plan(readback, plan_events=None, plan_inputs=None):
        return pjn.plan_enqueue(
            events if plan_events is None else plan_events,
            subscriptions,
            inputs=plan_inputs or inputs,
            existing_outbox_rows=readback,
        )

    producer_suppressed = {
        "fire_event_id": terminal_fid,
        "status": "suppressed",
        "attempts": 0,
        "last_error": pjn.PRODUCER_SUPPRESSED_REASON,
    }

    # run 1: the original is still pending — PATCH it AND mint the
    # retraction in the same run (contract §4), non-presuming copy
    plan = _plan([{"fire_event_id": terminal_fid, "status": "pending", "attempts": 0, "last_error": None}])
    assert plan.patches == [
        pjn.PlannedPatch(terminal_fid, "suppressed", pjn.PRODUCER_SUPPRESSED_REASON)
    ]
    assert [r["fire_event_id"] for r in plan.rows] == [retracted_fid]
    assert plan.rows[0]["payload"]["condition_plain"] == "XYZ: this name is no longer tracked."
    assert plan.rows[0]["payload"]["corrects_fire_event_id"] == terminal_fid

    # the original suppressed by THIS producer is never re-read as the
    # user's opt-out: nothing minted, typed count
    plan = _plan([producer_suppressed])
    assert plan.rows == [] and plan.patches == []
    assert plan.suppressed["original_producer_suppressed"] == 1

    # run 2 after run 1 committed atomically: duplicates only
    plan = _plan(
        [
            producer_suppressed,
            {"fire_event_id": retracted_fid, "status": "pending", "attempts": 0, "last_error": None},
        ]
    )
    assert plan.rows == [] and plan.patches == []
    assert plan.suppressed["already_fired"] == 2
    assert plan.suppressed["original_producer_suppressed"] == 0

    # a chain: the latest prior notice is the earlier correction, which is
    # the one patched and corrected — never the producer-suppressed terminal
    chain = [
        opened,
        _transition_envelope("EXPIRED"),
        _corrected_envelope({"terminal_reason": "re-priced exit"}),
        _retracted_envelope(opened["event_id"]),
    ]
    chain_inputs = _inputs(chain, calendar_rows=_calendar_rows())
    chain_events, _ = pjn.derive_events(chain_inputs)
    corrected_fid = _fid([e for e in chain_events if e.kind == "corrected_material"][0], USER_A)
    plan = _plan(
        [
            producer_suppressed,
            {"fire_event_id": corrected_fid, "status": "pending", "attempts": 0, "last_error": None},
        ],
        plan_events=chain_events,
        plan_inputs=chain_inputs,
    )
    assert plan.patches == [
        pjn.PlannedPatch(corrected_fid, "suppressed", pjn.PRODUCER_SUPPRESSED_REASON)
    ]
    assert [r["payload"]["kind"] for r in plan.rows] == ["retracted"]
    assert plan.rows[0]["payload"]["corrects_fire_event_id"] == corrected_fid
    assert plan.suppressed["original_producer_suppressed"] == 0


def test_r6_original_resolved_from_readback_any_kind_including_emergence():
    # F28 R6: the original is the latest earlier notice of the episode for
    # the user in the outbox readback, of ANY kind — here an emergence.
    opened = _open_envelope()
    relation = _relation_envelope()
    triggered = _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
    run_a = _inputs(
        [opened, relation],
        prev_rows=[_projection_row(emergence_state="ARMED")],
        curr_rows=[triggered],
        calendar_rows=_calendar_rows(),
    )
    events_a, _ = pjn.derive_events(run_a)
    plan_a = pjn.plan_enqueue(
        events_a, _subscriptions({USER_A: ("XYZ",)}), inputs=run_a, existing_outbox_rows=[]
    )
    assert [r["payload"]["kind"] for r in plan_a.rows] == ["emergence_triggered"]
    emergence_fid = plan_a.rows[0]["fire_event_id"]

    readback = _sent(plan_a.rows)
    run_b = _inputs(
        [opened, relation, _superseded_envelope()],
        prev_rows=[triggered],
        curr_rows=[triggered],
        calendar_rows=_calendar_rows(),
        outbox_rows=readback,
    )
    events_b, _ = pjn.derive_events(run_b)
    assert [e.kind for e in events_b] == ["superseded"]
    assert not hasattr(events_b[0], "corrects")
    plan_b = pjn.plan_enqueue(
        events_b,
        _subscriptions({USER_A: ("XYZ",), USER_B: ("XYZ",)}),
        inputs=run_b,
        existing_outbox_rows=readback,
    )
    assert [r["user_id"] for r in plan_b.rows] == [USER_A]
    assert plan_b.rows[0]["payload"]["corrects_fire_event_id"] == emergence_fid
    assert plan_b.rows[0]["payload"]["condition_plain"] == (
        "XYZ: this opportunity continues under a successor identity."
    )
    # USER_B was never shown anything about this journey: no original
    assert plan_b.suppressed["no_original"] == 1


def test_r7_relation_level_retraction_copy():
    relation = _relation_envelope()
    events, _ = pjn.derive_events(
        _inputs([_open_envelope(), relation, _retracted_envelope(relation["event_id"])])
    )
    retracted = [e for e in events if e.kind == "retracted"]
    assert len(retracted) == 1
    event = retracted[0]
    assert (event.from_state, event.to_state) == ("ACTIVE", "RETRACTED")
    expected = "XYZ: an earlier observation was withdrawn; the name remains tracked."
    assert event.condition_plain == expected
    assert event.condition_plain_unsent == expected
    assert "no longer tracked" not in event.condition_plain
    assert event.subject == "XYZ Prophet journey: observation withdrawn"


def test_r8_absent_or_unestimable_prior_emergence_counts_as_not_triggered():
    opened = _open_envelope()
    relation = _relation_envelope()
    triggered = _projection_row(emergence_state="TRIGGERED", emergence_ref=relation["event_id"])
    for prev_rows in (
        [],  # no prior generation row at all
        [_projection_row(episode=OTHER_EPISODE, emergence_state="TRIGGERED")],
        [_projection_row()],  # B3's UNESTIMABLE / SOURCE_NOT_SUPPLIED default
    ):
        events, counts = pjn.derive_events(
            _inputs([opened, relation], prev_rows=prev_rows, curr_rows=[triggered])
        )
        assert [(e.kind, e.b1_event_id) for e in events] == [
            ("emergence_triggered", relation["event_id"])
        ], prev_rows
        assert counts["unknown_side"] == 0
    # UNAVAILABLE_DATA stays an unknown side
    events, counts = pjn.derive_events(
        _inputs(
            [opened, relation],
            prev_rows=[_projection_row(emergence_state="UNAVAILABLE_DATA")],
            curr_rows=[triggered],
        )
    )
    assert events == [] and counts["unknown_side"] == 1


def test_r9_prev_projection_unavailable_derives_nothing():
    opened = _open_envelope()
    events, counts = pjn.derive_events(
        _inputs(
            [opened, _transition_envelope("EXPIRED"), _retracted_envelope(opened["event_id"])],
            prev_state=pjn.READ_UNAVAILABLE,
        )
    )
    assert events == []
    assert counts == {
        key: (1 if key == "prev_projection_unavailable" else 0)
        for key in pjn.SUPPRESSION_KEYS
    }


def test_r10_corrected_ticker_routes_to_the_new_ticker():
    ledger = [
        _open_envelope(),
        _corrected_envelope({"ticker_at_observation": "ZYX"}, recorded_at="2026-08-25T02:00:00Z"),
        _transition_envelope("EXPIRED"),
    ]
    inputs = _inputs(ledger, calendar_rows=_calendar_rows())
    events, _ = pjn.derive_events(inputs)
    assert {e.ticker for e in events} == {"ZYX"}
    assert all(e.company_id == COMPANY_ID for e in events)
    plan = pjn.plan_enqueue(
        events,
        _subscriptions({USER_A: ("XYZ",), USER_B: ("ZYX",)}),
        inputs=inputs,
        existing_outbox_rows=[],
    )
    assert [r["user_id"] for r in plan.rows] == [USER_B]
    row = plan.rows[0]
    assert row["payload"]["kind"] == "episode_terminal"
    assert row["payload"]["ticker"] == "ZYX"
    assert row["payload"]["condition_plain"].startswith("ZYX: ")
    # the correction itself precedes every notice to USER_B: no original
    assert plan.suppressed["no_original"] == 1
