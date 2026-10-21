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
) -> dict:
    return make_event(
        event_type=event_type,
        episode_id=episode,
        source_system=source_system,
        source_schema=source_schema,
        source_event_id=source_event_id,
        occurred_at="2026-08-24T20:00:00Z",
        known_at="2026-08-24T20:00:00Z",
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


def _corrected_envelope(patch: dict, *, recorded_at: str = "2026-08-25T04:00:00Z") -> dict:
    return _envelope(
        "CORRECTED",
        payload={"patch": patch},
        source_event_id=f"episode:{EPISODE}:corrected",
        recorded_at=recorded_at,
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
) -> pjn.JourneyInputs:
    return pjn.JourneyInputs(
        b1_events=pjn.TypedRead(b1_state, list(b1_rows)),
        projection_prev=pjn.TypedRead(
            pjn.READ_OK if prev_rows else pjn.READ_OK_ZERO, list(prev_rows or [])
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
        "read_unavailable", "ineligible_event", "unknown_side", "no_subscriber",
        "already_fired", "banned_term", "session_end_unknown", "no_original",
        "original_quarantined",
    )
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
    # the correction corrects the episode_terminal notice derived before it
    assert event.corrects == ("episode_terminal", "ACTIVE", "CLOSED", transition["event_id"])

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

    # prev lifecycle UNAVAILABLE_DATA: the from side is unknown, so the
    # retraction pair cannot be stated
    events, counts = pjn.derive_events(
        _inputs(
            [opened, _retracted_envelope(opened["event_id"])],
            prev_rows=[_projection_row(lifecycle="UNAVAILABLE_DATA")],
        )
    )
    assert [e for e in events if e.kind == "retracted"] == []
    assert counts["unknown_side"] == 1

    # same for a superseded pair off an unknown from side
    events, counts = pjn.derive_events(
        _inputs(
            [opened, _superseded_envelope()],
            prev_rows=[_projection_row(lifecycle="UNAVAILABLE_DATA")],
        )
    )
    assert [e for e in events if e.kind == "superseded"] == []
    assert counts["unknown_side"] == 1

    # and the emergence side's unknown is the RELATION ID (test 7 pins that
    # the prev UNESTIMABLE filler itself never suppresses)
    relation = _relation_envelope()
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
    # the three correction kinds find no original row here (no_original);
    # episode_terminal and emergence_triggered — the non-correction kinds —
    # are exactly the rows this run mints.
    minted_kinds = sorted(row["payload"]["kind"] for row in plan.rows)
    assert minted_kinds == ["emergence_triggered", "episode_terminal"]
    assert plan.suppressed["no_original"] == 3
    row = next(
        r for r in plan.rows if r["payload"]["kind"] == "episode_terminal"
    )
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
        for text in (event.condition_plain, event.subject):
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

    # fractional seconds are carried VERBATIM
    plan = _plan(
        calendar_rows=_calendar_rows(end="2026-08-26T00:00:00.123456Z")
    )
    assert plan.rows[0]["payload"]["not_after"] == "2026-08-26T00:00:00.123456Z"

    # no run session, no calendar row for it, or an unparsable end: no row,
    # typed session_end_unknown — a row never ships without its bound.
    for calendar_rows, market_session in (
        (_calendar_rows(), None),
        (_calendar_rows(session="2026-08-24"), SESSION),
        (_calendar_rows(end="not-a-clock"), SESSION),
    ):
        plan = _plan(calendar_rows=calendar_rows, market_session=market_session)
        assert plan.rows == []
        assert plan.suppressed["session_end_unknown"] == 1


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
        assert set(row) == {
            "user_id", "alert_id", "fire_event_id", "channel", "status",
            "attempts", "payload",
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
    correction = [e for e in events if e.kind == "corrected_material"][0]
    assert correction.corrects is not None
    original_fid = pjn.fire_event_id(
        kind=correction.corrects[0],
        episode_id=EPISODE,
        from_state=correction.corrects[1],
        to_state=correction.corrects[2],
        b1_event_id=correction.corrects[3],
        user_id=USER_A,
    )
    subscriptions = _subscriptions({USER_A: ("XYZ",)})

    def _plan(outbox_rows):
        return pjn.plan_enqueue(
            events,
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

    # absent original: the terminal notice mints normally (nothing exists
    # yet), the correction finds no original row and is counted no_original.
    absent = _plan([])
    assert len(absent.rows) == 1
    assert absent.rows[0]["payload"]["kind"] == "episode_terminal"
    assert absent.suppressed["no_original"] == 1
    assert absent.patches == []

    # unsent original: pending / deferred / failed under the retry cap —
    # the original is PATCH-suppressed and NO correction row is minted (its
    # own pair counts duplicate: the row already exists).
    for status, attempts, last_error in (
        ("pending", 0, None),
        ("deferred", 1, "quiet_hours"),
        ("failed", 2, "smtp_5xx"),
        # residual cell: failed at cap with a definitive error still cannot
        # ever send again, so the one-email guarantee holds via the patch
        ("failed", 3, "smtp_refused"),
    ):
        plan = _plan([_original_row(status, attempts, last_error)])
        assert plan.patches == [
            pjn.PlannedPatch(
                fire_event_id=original_fid,
                status="suppressed",
                last_error="superseded_by_prophet_correction",
            )
        ], (status, attempts, last_error)
        assert [r for r in plan.rows if r["payload"]["kind"] == "corrected_material"] == []
        assert plan.suppressed["no_original"] == 0

    # sent original: never touched, correction row only
    plan = _plan([_original_row("sent", 1, None)])
    assert plan.patches == []
    corrections = [r for r in plan.rows if r["payload"]["kind"] == "corrected_material"]
    assert len(corrections) == 1
    assert corrections[0]["payload"]["corrects_fire_event_id"] == original_fid

    # suppressed original: mint anyway — the drain re-decides from live prefs
    plan = _plan([_original_row("suppressed", 0, "entitlement_lapsed")])
    assert plan.patches == []
    assert len([r for r in plan.rows if r["payload"]["kind"] == "corrected_material"]) == 1

    # quarantined original: nothing minted, typed count
    plan = _plan(
        [_original_row("failed", 3, "effect_unknown_after_smtp")]
    )
    assert plan.patches == []
    assert [r for r in plan.rows if r["payload"]["kind"] == "corrected_material"] == []
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
