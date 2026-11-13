"""MarketDesk-specific freshness regressions for the Research Vault source clock.

Hermetic: every case is built in-process from literal catalogs. No network, no
store, no fixture files, no clock reads -- ``now`` is always injected.

The defect these lock down: a single ``max(published_at)`` over the whole vault
cannot tell a healthy vault from one whose MarketDesk provider has stopped
publishing while an internal desk keeps the vault-wide max young. The prior
triage (``rd-source-clock-triage-20261022-01``) proved the masking and wrongly
concluded the old provider identity was unrecoverable; it is recoverable from
the catalog itself, because ``publish_vault.vault_id()`` stamps every MarketDesk
sidecar id with a canonical ``marketdesk-`` prefix.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from engine.research_vault import catalog as catalog_mod
from scripts import check_research_vault_source_freshness as guard

NOW = datetime(2026, 9, 5, 4, tzinfo=timezone.utc)

FRESH = "2026-09-04T18:00:00Z"   # ~10h before NOW -> inside the weekday deadline
OLD = "2026-08-25T16:47:24Z"     # weeks before NOW -> well past it

INTERNAL_ID = "mastermind-research-2026-09-04-cndt-settlement"
# Real shape observed on the live anonymous Research Desk preview: the casefolded
# blob id plus a 6-hex digest of the ORIGINAL id.
MARKETDESK_ID = "marketdesk-zarzrnqfgu6-29437b"


def _vault(items):
    return {
        "schema": "research_vault.catalog.v1",
        "generated_at": "2026-09-05T00:00:00Z",
        "count": len(items),
        "items": items,
    }


def _row(item_id, stamp):
    return {"id": item_id, "published_at": stamp}


def _internal(stamp=FRESH, item_id=INTERNAL_ID):
    return _row(item_id, stamp)


def _marketdesk(stamp=FRESH, item_id=MARKETDESK_ID):
    return _row(item_id, stamp)


def _preview(full, now=NOW):
    """Truncate exactly like app/research._catalog_preview, reusing the summary.

    The summary is produced from the COMPLETE catalog before truncation, which
    is the property the provider clock depends on.
    """
    summary = catalog_mod.public_summary(full, now=now)
    return dict(full, items=full["items"][:1], summary=summary, preview=True)


# --------------------------------------------------------------------------
# the masking case
# --------------------------------------------------------------------------
def test_internal_new_provider_old_is_never_reported_source_fresh():
    report = guard.evaluate(_vault([_internal(FRESH), _marketdesk(OLD)]), now=NOW)

    assert report["status"] == guard.MARKETDESK_STALE
    assert report["ok"] is not True
    # The vault-wide clock is genuinely fresh -- that is exactly why the global
    # max alone could not see the outage.
    assert report["latest_report_at"] == "2026-09-04T18:00:00+00:00"
    assert report["marketdesk_latest_at"] == "2026-08-25T16:47:24+00:00"
    assert report["marketdesk_report_count"] == 1


def test_provider_fresh_internal_old_is_source_fresh():
    report = guard.evaluate(_vault([_internal(OLD), _marketdesk(FRESH)]), now=NOW)

    assert report["status"] == "SOURCE_FRESH"
    assert report["ok"] is True
    assert report["marketdesk_latest_at"] == "2026-09-04T18:00:00+00:00"


# --------------------------------------------------------------------------
# missing provider -- fail closed, never borrow the global clock
# --------------------------------------------------------------------------
def test_no_provider_rows_fails_closed():
    report = guard.evaluate(_vault([_internal(FRESH)]), now=NOW)

    assert report["status"] == guard.MARKETDESK_CLOCK_MISSING
    assert report["ok"] is not True
    assert report["marketdesk_report_count"] == 0


def test_pre_slice_summary_stays_readable_and_fails_closed():
    """An old service emits no ``providers`` key: readable, typed, red -- no crash."""
    full = _vault([_internal(FRESH), _marketdesk(FRESH)])
    clock = catalog_mod.public_summary(full, now=NOW)["source_clock"]
    legacy = {key: value for key, value in clock.items() if key != "providers"}

    report = guard.evaluate(
        dict(full, preview=True, summary={"source_clock": legacy}), now=NOW
    )

    assert report["status"] == guard.MARKETDESK_CLOCK_MISSING
    # Every pre-existing key keeps its exact name, type and value, so an
    # old-schema reader is unaffected by the rollout.
    assert legacy["latest_report_published_at"] == "2026-09-04T18:00:00+00:00"
    assert legacy["report_count"] == 2
    assert legacy["schema"] == "research_vault.source_clock.v1"


# --------------------------------------------------------------------------
# malformed clocks
# --------------------------------------------------------------------------
def test_one_dirty_provider_row_does_not_replace_the_verdict():
    report = guard.evaluate(
        _vault([
            _internal(FRESH),
            _marketdesk("bad"),
            _marketdesk(FRESH, "marketdesk-ixfukwixfml-b74821"),
        ]),
        now=NOW,
    )

    assert report["status"] == "SOURCE_FRESH"
    assert report["marketdesk_report_count"] == 2
    assert report["marketdesk_invalid_published_at"] == 1
    assert report["marketdesk_latest_at"] == "2026-09-04T18:00:00+00:00"


def test_every_provider_row_malformed_is_stale_not_fresh():
    report = guard.evaluate(
        _vault([_internal(FRESH), _marketdesk("bad")]), now=NOW
    )

    assert report["status"] == guard.MARKETDESK_STALE
    assert report["marketdesk_invalid_published_at"] == 1
    assert report["marketdesk_latest_at"] is None


def test_provider_aggregate_counts_must_be_self_consistent():
    full = _vault([_internal(FRESH), _marketdesk(FRESH)])
    clock = catalog_mod.public_summary(full, now=NOW)["source_clock"]
    good = clock["providers"]["marketdesk"]

    for tamper in (
        {"report_count": -1},
        {"report_count": True},
        {"valid_clock_count": 99},
        {"invalid_clock_count": -1},
        {"id_prefix": "other-"},
        {"latest_report_published_at": "bad"},
    ):
        broken = dict(clock, providers={"marketdesk": dict(good, **tamper)})
        report = guard.evaluate(
            dict(full, preview=True, summary={"source_clock": broken}), now=NOW
        )
        assert report["status"] == guard.MARKETDESK_CLOCK_MISSING, tamper


# --------------------------------------------------------------------------
# preview / full parity
# --------------------------------------------------------------------------
@pytest.mark.parametrize("provider_stamp", [FRESH, OLD])
def test_preview_truncation_never_changes_the_provider_verdict(provider_stamp):
    full = _vault([
        _internal(FRESH),
        _marketdesk(provider_stamp),
        _row("later-internal-2", "2026-08-25T12:00:00Z"),
        _row("later-internal-3", "2026-08-25T12:00:00Z"),
        _row("later-internal-4", "2026-08-25T12:00:00Z"),
    ])
    # The preview keeps only the first item -- the provider row is truncated away.
    assert _marketdesk(provider_stamp)["id"] not in {
        item["id"] for item in _preview(full)["items"]
    }

    short = guard.evaluate(_preview(full), now=NOW)
    whole = guard.evaluate(full, now=NOW)

    assert short["status"] == whole["status"]
    for key in (
        "latest_report_at",
        "marketdesk_latest_at",
        "marketdesk_deadline_at",
        "marketdesk_report_count",
        "marketdesk_invalid_published_at",
        "count",
        "age_hours",
    ):
        assert short.get(key) == whole.get(key), key


# --------------------------------------------------------------------------
# acknowledgement semantics are preserved and NOT widened
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload,expected",
    [
        ([_internal(FRESH), _marketdesk(OLD)], guard.MARKETDESK_STALE),
        ([_internal(FRESH)], guard.MARKETDESK_CLOCK_MISSING),
        ([_internal(FRESH), _marketdesk("bad")], guard.MARKETDESK_STALE),
    ],
)
def test_generic_producer_ack_cannot_soften_a_provider_verdict(payload, expected):
    report = guard.evaluate(_vault(payload), now=NOW)

    assert report["status"] == expected
    # The existing ack is keyed to the single PRODUCER_STALE literal.
    assert guard._acknowledges_producer_stale(report, True) is False
    assert guard._acknowledges_producer_stale(report, False) is False


def test_existing_producer_stale_ack_semantics_are_unchanged():
    report = guard.evaluate(_vault([_internal(OLD), _marketdesk(OLD)]), now=NOW)

    assert report["status"] == "PRODUCER_STALE"
    assert guard._acknowledges_producer_stale(report, True) is True
    assert guard._acknowledges_producer_stale(report, False) is False


def test_global_stale_keeps_precedence_over_the_provider_verdict():
    """Global staleness implies provider staleness, so PRODUCER_STALE still wins."""
    report = guard.evaluate(_vault([_internal(OLD), _marketdesk(OLD)]), now=NOW)

    assert report["status"] == "PRODUCER_STALE"


# --------------------------------------------------------------------------
# bounded output
# --------------------------------------------------------------------------
def test_report_json_is_bounded_and_finite():
    for payload in (
        _vault([_internal(FRESH), _marketdesk(FRESH)]),
        _vault([_internal(FRESH), _marketdesk(OLD)]),
        _vault([_internal(FRESH)]),
    ):
        report = guard.evaluate(payload, now=NOW)
        text = json.dumps(report, sort_keys=True, allow_nan=False)

        assert "NaN" not in text and "Infinity" not in text
        assert json.loads(text) == report
        # The report names the provider and grades it, but never quotes a report:
        # no raw sidecar id and no institution/title text reaches the JSON.
        assert "zarzrnqfgu6" not in text
        assert INTERNAL_ID not in text


def test_hostile_max_age_cannot_produce_non_finite_provider_numbers():
    for value in (float("nan"), float("inf"), -float("inf"), 0, -1):
        report = guard.evaluate(
            _vault([_internal(FRESH), _marketdesk(FRESH)]),
            now=NOW,
            max_age_hours=value,
        )
        assert report["status"] == "CATALOG_UNAVAILABLE"
        json.dumps(report, allow_nan=False)


# --------------------------------------------------------------------------
# the catalog projection itself
# --------------------------------------------------------------------------
def test_provider_clock_is_private_safe_and_does_not_mutate_input():
    full = _vault([
        _internal(FRESH),
        _marketdesk(OLD),
        {"id": MARKETDESK_ID + "-x", "published_at": "bad", "title": "PRIVATE"},
    ])
    before = json.loads(json.dumps(full))

    clock = catalog_mod.public_summary(full, now=NOW)["source_clock"]
    provider = clock["providers"]["marketdesk"]
    blob = json.dumps(clock)

    assert provider["id_prefix"] == "marketdesk-"
    assert provider["report_count"] == 2
    assert provider["valid_clock_count"] == 1
    assert provider["invalid_clock_count"] == 1
    assert provider["latest_report_published_at"] == "2026-08-25T16:47:24+00:00"
    # Counts and a maximum only -- no report id, title or summary text.
    assert "PRIVATE" not in blob
    assert "zarzrnqfgu6" not in blob
    assert full == before


def test_id_namespace_matches_the_canonical_producer_shape():
    """The namespace is producer-derived, not an institution/title guess."""
    import re

    from engine.research_vault.catalog import MARKETDESK_ID_PREFIX

    assert MARKETDESK_ID_PREFIX == "marketdesk-"
    shape = re.compile(r"^marketdesk-[a-z0-9-]+-[0-9a-f]{6}$")
    assert shape.match(MARKETDESK_ID)
    assert shape.match("marketdesk-ixfukwixfml-b74821")
    # An internal desk id is never mistaken for a MarketDesk row.
    assert not shape.match(INTERNAL_ID)


# --------------------------------------------------------------------------
# the public read port inherits the guard without widening its vocabulary
# --------------------------------------------------------------------------
def _read_service():
    from engine.research_vault.read_service import ResearchReadService

    return ResearchReadService(
        catalog_store=lambda: None,
        corpus_connection=lambda: None,
        preview_selector=lambda catalog: (),
        clock=lambda: NOW,
    )


@pytest.mark.parametrize(
    "items,expected_degradations",
    [
        ([_internal(FRESH), _marketdesk(FRESH)], set()),
        (
            [_internal(FRESH), _marketdesk(OLD)],
            {"PRODUCER_STALE", "MARKETDESK_STALE"},
        ),
        ([_internal(FRESH)], {"PRODUCER_STALE", "MARKETDESK_CLOCK_MISSING"}),
    ],
)
def test_read_port_reports_a_stale_provider_as_producer_stale(
    items, expected_degradations
):
    source = _read_service()._source_state(_vault(items), NOW)

    # The vault IS readable, so CATALOG_UNAVAILABLE would be a lie.
    expected_state = "SOURCE_FRESH" if not expected_degradations else "PRODUCER_STALE"
    assert source["state"] == expected_state
    assert source["state"] != "CATALOG_UNAVAILABLE"
    assert expected_degradations <= set(source["known_degradation"])


def test_public_source_state_vocabulary_stays_closed():
    """Provider verdicts must NOT leak new strings into the public state enum."""
    from engine.research_vault import read_port

    assert read_port.SOURCE_STATES == frozenset({
        "SOURCE_FRESH",
        "PRODUCER_STALE",
        "CATALOG_UNAVAILABLE",
        "NO_REPORTS",
        "LATEST_REPORT_INVALID",
        "FUTURE_REPORT_CLOCK",
    })
    assert "MARKETDESK_STALE" not in read_port.SOURCE_STATES
    assert "MARKETDESK_CLOCK_MISSING" not in read_port.SOURCE_STATES
    # They are admissible degradations, which is how a consumer tells them apart.
    assert "MARKETDESK_STALE" in read_port.DEGRADATION_CODES
    assert "MARKETDESK_CLOCK_MISSING" in read_port.DEGRADATION_CODES


def test_source_state_payload_validates_against_the_port():
    from engine.research_vault import read_port

    for items in (
        [_internal(FRESH), _marketdesk(FRESH)],
        [_internal(FRESH), _marketdesk(OLD)],
        [_internal(FRESH)],
    ):
        source = _read_service()._source_state(_vault(items), NOW)
        # Round-trips the port's own validator rather than a local copy of it.
        assert read_port.source_state(
            state=source["state"],
            catalog_generated_at=source["catalog_generated_at"],
            latest_report_published_at=source["latest_report_published_at"],
            source_age_hours=source["source_age_hours"],
            report_count=source["report_count"],
            known_degradation=source["known_degradation"],
        ) == source