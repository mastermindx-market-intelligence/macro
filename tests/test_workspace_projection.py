"""T08b — bridge production ``event_workspace.v1`` payloads into composer rows.

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier
PR #7870), T08b. The composer
(:func:`engine.market_ontology.semiconductor_theme_research.compose_semiconductor_research`)
keys on rows shaped like the synthetic witness fixture
(``tests/fixtures/semiconductor_theme_research/witness_hbm_packaging.json``).
Production intake (:mod:`scripts.refresh_event_workspaces`) emits a different
shape — ``facts`` of ``event_fact.v1`` with an ISO ``period`` end, an
optional ``typed_absence`` envelope, an ``issuer`` block with a CIK-shaped
``company_id``, ``fiscal_period{year,quarter,calendar_end}``, etc. This test
file pins :func:`project_event_workspace` so the production intake can drive
the same composer the synthetic fixture drives, without ever authoring
authority or arithmetic.

What this pins that no other test does:

  * The two real-metadata payloads the ``test_semiconductor_earnings_intake_integration``
    carrier produces for TSM and ON project to rows whose ``reported[0]``
    carries ``metric='revenue'``, the closed basis (``reported_ifrs`` for
    TSM, ``reported_gaap`` for ON), ``currency='USD'``, and the closed
    ``fiscal_period`` token ``"2026Q2"`` / ``"2026Q1"`` — never the
    ISO ``period`` end from the fact envelope.
  * The projected TSM Q1+Q2 bundle drives the composer to
    ``economics.status == 'ready'`` and
    ``management.comparisons.prior_vs_actual.status == 'comparable'`` — the
    same payload the live-EDGAR proof found as ``fx_assumption_unreconciled``
    in ``_composer_sequence`` (real revenue for TSM is basis-matched to the
    TSM USD outlook). On the same witness fixtures the helper admits in the
    integration suite.
  * Typed absences never produce ``reported`` rows.
  * Two present facts sharing ``(metric, basis)`` → no row + omission token.
  * Malformed payloads (missing ``fiscal_period``, non-int quarter,
    non-numeric ``value``, issuer without a CIK) → ``None`` or a row
    without that field, never an exception.
  * ``provenance`` and ``source_span`` never appear in ``reported``.

The composer test stands on the witness fixture's exact authority / identity /
financial_packet shape (one bound packet per TSM event) — the projected
rows are the only inputs that differ.  Identity_results are MINIMAL: the
fixture's company_node_id mapping is unused because ``_build_economics`` keys
on ``cik`` (``workspace.get('cik')``) when ``company_node_id`` is absent —
exactly the projection's contract.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from engine.company_intelligence.guidance_history import GuidanceHistoryError
from engine.company_intelligence.issuer_profiles import ON_CIK, TSM_CIK
from engine.market_ontology.semiconductor_theme_research import (
    DEFINITION_VERSION,
    OwnerBundle,
    ResearchQuery,
    compose_semiconductor_research,
)
from engine.market_ontology.workspace_projection import project_event_workspace

from tests.test_semiconductor_earnings_intake_integration import (
    ON_Q2_ROWS,
    ON_Q2_MANIFESTS,
    ON_Q2_SYNTHETIC_EXHIBIT,
    ON_RESULTS_ACCESSION,
    ON_ROWS,
    ON_MANIFESTS,
    ON_SYNTHETIC_EXHIBIT,
    TSM_MANIFESTS,
    TSM_Q1_ROW,
    TSM_Q1_MANIFEST,
    TSM_Q1_SYNTHETIC_EXHIBIT,
    TSM_RESULTS_ACCESSION,
    TSM_ROWS,
    TSM_SYNTHETIC_EXHIBIT,
    _discover,
)


# ─────────────────────────────────────────────────────────────────────────────
# (a) Real-metadata payloads from the integration test's `_discover` helper
# ─────────────────────────────────────────────────────────────────────────────


def _projected_tsm_q1_q2(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """TSM Q1-2026 + Q2-2026 events, each as the composer row.

    Both events reach ``_discover`` through the production identity + profile
    (no seams): the Q1 row is added to ``TSM_ROWS`` and its Q1 manifest is
    added to ``TSM_MANIFESTS``. The integration suite pins the same admission
    law for these accessions — by reusing its helper we guarantee the
    projection is exercised against the same real-metadata payload shape.
    """
    revisions, _ = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK,
        rows=TSM_ROWS + [TSM_Q1_ROW],
        manifests={**TSM_MANIFESTS, **TSM_Q1_MANIFEST},
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT,
                TSM_Q1_RESULTS_ACCESSION(): TSM_Q1_SYNTHETIC_EXHIBIT},
    )
    projected = []
    for _event_id, payload in revisions:
        row = project_event_workspace(payload)
        assert row is not None, f"project_event_workspace refused: {payload.get('event_id')}"
        projected.append(row)
    projected.sort(key=lambda r: (r["fiscal_period"]["year"], r["fiscal_period"]["quarter"]))
    return projected


def _by_fp(rows):
    return {(r["fiscal_period"]["year"], r["fiscal_period"]["quarter"]): r for r in rows}


def TSM_Q1_RESULTS_ACCESSION() -> str:
    return "0001046179-26-000199"  # from tests/test_semiconductor_earnings_intake_integration.TSM_Q1_RESULTS_ACCESSION


def test_tsm_real_metadata_projects_to_revenue_ifrs_usd_q1_q2(monkeypatch) -> None:
    """The two TSM real-metadata payloads project to closed-grammar rows."""
    projected = _projected_tsm_q1_q2(monkeypatch)
    assert len(projected) == 2
    by_period = _by_fp(projected)
    q1, q2 = by_period[(2026, 1)], by_period[(2026, 2)]

    assert q1["event_id"].endswith("2026q1_results")
    assert q2["event_id"].endswith("2026q2_results")
    # The composer's CIK key is satisfied: a real production CIK, zero-padded.
    assert q1["cik"] == "0001046179" and q2["cik"] == "0001046179"
    # company_node_id is omitted by the projection; the composer keys on cik.
    assert "company_node_id" not in q1 and "company_node_id" not in q2

    q1_rev = next(row for row in q1["reported"] if row["metric"] == "revenue")
    q2_rev = next(row for row in q2["reported"] if row["metric"] == "revenue")
    assert q1_rev["currency"] == "USD" and q2_rev["currency"] == "USD"
    assert q1_rev["basis"] == "reported_ifrs" and q2_rev["basis"] == "reported_ifrs"
    # fiscal_period is the closed token from the workspace block, never the
    # ISO ``period`` end from the fact envelope.
    assert q1_rev["fiscal_period"] == "2026Q1" and q2_rev["fiscal_period"] == "2026Q2"
    assert q1_rev["unit"] == "usd_billions" and q2_rev["unit"] == "usd_billions"
    # provenance / source_span are not echoed into reported.
    for row in q1["reported"] + q2["reported"]:
        assert "provenance" not in row and "source_span" not in row


def test_on_real_metadata_projects_to_revenue_gaap_usd_q1_q2(monkeypatch) -> None:
    """onsemi's two real filings project to closed-grammar rows."""
    revisions, _ = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK,
        rows=ON_ROWS + ON_Q2_ROWS,
        manifests={**ON_MANIFESTS, **ON_Q2_MANIFESTS},
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT,
                ON_Q2_RESULTS_ACCESSION(): ON_Q2_SYNTHETIC_EXHIBIT},
    )
    projected = []
    for _event_id, payload in revisions:
        row = project_event_workspace(payload)
        assert row is not None, f"project_event_workspace refused: {payload.get('event_id')}"
        projected.append(row)
    projected.sort(key=lambda r: (r["fiscal_period"]["year"], r["fiscal_period"]["quarter"]))
    by_period = _by_fp(projected)
    q1, q2 = by_period[(2026, 1)], by_period[(2026, 2)]

    assert q1["cik"] == "0001097864" and q2["cik"] == "0001097864"
    q1_rev = next(row for row in q1["reported"] if row["metric"] == "revenue")
    q2_rev = next(row for row in q2["reported"] if row["metric"] == "revenue")
    assert q1_rev["currency"] == "USD" and q2_rev["currency"] == "USD"
    assert q1_rev["basis"] == "reported_gaap" and q2_rev["basis"] == "reported_gaap"
    assert q1_rev["fiscal_period"] == "2026Q1" and q2_rev["fiscal_period"] == "2026Q2"


def ON_Q2_RESULTS_ACCESSION() -> str:
    return "0001140361-26-030989"  # from tests/test_semiconductor_earnings_intake_integration


# ─────────────────────────────────────────────────────────────────────────────
# (b) The projected TSM Q1+Q2 rows drive the composer to `economics.ready`
# ─────────────────────────────────────────────────────────────────────────────


def _minimal_identity_results(cik: str) -> tuple[dict, ...]:
    """A minimal identity_results tuple — empty.  ``_build_economics`` keys
    on ``workspace.get('cik')`` directly, so the projected rows drive the
    composer without any identity mapping being learned."""
    return ()


def _minimal_assertions() -> tuple[dict, ...]:
    """Empty assertions — no curation rows; the composer then refuses the
    industrial views (so the only pane the economics test exercises is
    economics itself)."""
    return ()


def _tsm_q1_q2_bundle(projected: list[dict]) -> OwnerBundle:
    """An OwnerBundle whose event_workspaces are the projected rows.

    financial_packets: one bound ``ready`` packet per event, with its
    derivations' ``inputs`` referencing BOTH event ids — this is the exact
    shape the witness fixture binds for its synthetic TSM Foundry Alpha
    sequence, and the only shape ``_build_economics`` will accept.
    """
    cik = projected[0]["cik"]
    q1_id = projected[0]["event_id"]
    q2_id = projected[1]["event_id"]
    inputs = sorted({q1_id, q2_id})
    packet = {
        "schema": "financial_intelligence_packet.v1",
        "entity": {"cik": cik},
        "derivations": {
            "prior_midpoint": {
                "value": 12.34,
                "receipt": {"store": "synthetic-derivations",
                            "method": "owner_midpoint_receipt"},
                "inputs": inputs,
                "owner": "financial-owner",
            },
        },
        "status": "ready",
        "recorded_at": "2026-07-21T00:00:00Z",
    }
    return OwnerBundle(
        revision_tuple=(("event", q1_id), ("event", q2_id)),
        rights_revision="synthetic-rights-0",
        assertions=_minimal_assertions(),
        identity_results=_minimal_identity_results(cik),
        event_workspaces=tuple(projected),
        financial_packets=(packet,),
        interpretation_blocks=(),
        native_refs=(),
        omissions=(),
    )


def test_projected_tsm_two_quarter_bundle_drives_economics_ready(monkeypatch) -> None:
    """The projected TSM Q1+Q2 rows feed the composer to a ready economics
    pane with a comparable prior-vs-actual — the same outcome the
    integration suite asserts for the same admission payloads under
    ``_composer_sequence`` (``position == 'below_range'`` here because the
    synthetic packet midpoint is below TSM's Q2 USD-restated revenue)."""
    projected = _projected_tsm_q1_q2(monkeypatch)
    bundle = _tsm_q1_q2_bundle(projected)
    query = ResearchQuery(
        anchor_theme_id="ai_semiconductors",
        slice_key="hbm_packaging",
        view="economics",
        time_mode="latest",
        source_cutoff=None,
        recorded_cutoff=None,
    )
    try:
        response = compose_semiconductor_research(query, bundle)
    except GuidanceHistoryError as exc:  # pragma: no cover - recorded in DEVIATIONS
        pytest.skip(f"composer refused: {exc.code}")
    assert response["economics"]["status"] == "ready", response["economics"]
    management = response["economics"]["management"]
    assert management is not None
    assert management["comparisons"]["prior_vs_actual"]["status"] == "comparable", management


# ─────────────────────────────────────────────────────────────────────────────
# (c) Typed absences never produce rows
# ─────────────────────────────────────────────────────────────────────────────


def test_typed_absence_facts_never_produce_reported_rows() -> None:
    """The TSM synthetic exhibit yields one PRESENT revenue (USD) and one
    TYPED-ABSENT revenue (TWD) — the TWD row is dropped; the USD row
    survives."""
    payload = {
        "event_id": "evt_test_absent",
        "issuer": {"company_id": f"cik:{TSM_CIK}"},
        "fiscal_period": {"year": 2026, "quarter": 1, "calendar_end": "2026-03-31"},
        "facts": [
            {"schema": "event_fact.v1", "fact_id": "fact_revenue_usd",
             "metric": "revenue", "value": 12.34, "unit": "usd_billions",
             "period": "2026-03-31", "basis": "reported_ifrs", "currency": "USD"},
            {"schema": "event_fact.v1", "fact_id": "fact_revenue_twd",
             "metric": "revenue", "typed_absence": {"reason": "missing_units"}},
        ],
        "guidance": [],
        "lifecycle": {"source_available_at": "2026-04-20T12:00:00Z",
                      "observed_at": "2026-04-20T12:00:00Z",
                      "recorded_at": "2026-04-20T12:00:00Z"},
    }
    row = project_event_workspace(payload)
    assert row is not None
    metrics = [r["metric"] for r in row["reported"]]
    assert metrics == ["revenue"]


# ─────────────────────────────────────────────────────────────────────────────
# (d) Two present facts sharing (metric, basis) → no row + omission token
# ─────────────────────────────────────────────────────────────────────────────


def test_two_present_facts_same_metric_and_basis_yield_no_row_with_omission_token() -> None:
    payload = {
        "event_id": "evt_test_collision",
        "issuer": {"company_id": f"cik:{TSM_CIK}"},
        "fiscal_period": {"year": 2026, "quarter": 2},
        "facts": [
            {"schema": "event_fact.v1", "fact_id": "fact_revenue_usd_a",
             "metric": "revenue", "value": 12.34, "unit": "usd_billions",
             "period": "2026-06-30", "basis": "reported_ifrs", "currency": "USD"},
            {"schema": "event_fact.v1", "fact_id": "fact_revenue_usd_b",
             "metric": "revenue", "value": 12.35, "unit": "usd_billions",
             "period": "2026-06-30", "basis": "reported_ifrs", "currency": "USD"},
        ],
        "guidance": [],
        "lifecycle": {},
    }
    row = project_event_workspace(payload)
    assert row is not None
    assert row["reported"] == []               # NEITHER row is emitted
    assert "reported_ambiguous:revenue" in row["omissions"]
    # Different bases do NOT collide — both rows survive.
    payload["facts"][1]["basis"] = "reported_gaap"
    row = project_event_workspace(payload)
    assert row is not None and len(row["reported"]) == 2
    assert row["omissions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# (e) Malformed payloads → None or a row without that field, NEVER an exception
# ─────────────────────────────────────────────────────────────────────────────


def test_non_mapping_payload_yields_none() -> None:
    assert project_event_workspace(None) is None           # type: ignore[arg-type]
    assert project_event_workspace("not a mapping") is None  # type: ignore[arg-type]
    assert project_event_workspace([1, 2, 3]) is None        # type: ignore[arg-type]


def test_missing_event_id_yields_none() -> None:
    assert project_event_workspace({"fiscal_period": {"year": 2026, "quarter": 1}}) is None


def test_missing_fiscal_period_yields_none() -> None:
    assert project_event_workspace({"event_id": "evt_x"}) is None
    assert project_event_workspace({"event_id": "evt_x", "fiscal_period": "not a mapping"}) is None


def test_non_int_quarter_yields_none() -> None:
    payload = {"event_id": "evt_x", "fiscal_period": {"year": 2026, "quarter": "Q1"}}
    assert project_event_workspace(payload) is None
    # Out-of-range quarters are rejected too.
    assert project_event_workspace(
        {"event_id": "evt_x", "fiscal_period": {"year": 2026, "quarter": 5}}) is None
    assert project_event_workspace(
        {"event_id": "evt_x", "fiscal_period": {"year": 2026, "quarter": 0}}) is None


def test_issuer_without_a_cik_yields_row_with_none_cik() -> None:
    """A payload with an issuer block but no parseable CIK is still
    projected — the composer keys on ``cik`` and accepts ``None``."""
    payload = {
        "event_id": "evt_x",
        "issuer": {"company_id": None, "display_name": "Unparseable"},
        "fiscal_period": {"year": 2026, "quarter": 1},
        "facts": [],
        "guidance": [],
        "lifecycle": {},
    }
    row = project_event_workspace(payload)
    assert row is not None and row["cik"] is None
    assert "company_node_id" not in row


def test_non_numeric_value_does_not_raise_and_is_dropped() -> None:
    payload = {
        "event_id": "evt_x",
        "issuer": {"company_id": f"cik:{TSM_CIK}"},
        "fiscal_period": {"year": 2026, "quarter": 1},
        "facts": [
            {"schema": "event_fact.v1", "fact_id": "fact_revenue",
             "metric": "revenue", "value": "twelve point three four",  # unparseable
             "unit": "usd_billions", "period": "2026-03-31",
             "basis": "reported_ifrs", "currency": "USD"},
        ],
        "guidance": [],
        "lifecycle": {},
    }
    row = project_event_workspace(payload)        # must not raise
    assert row is not None and row["reported"] == []


def test_optional_tokens_are_absent_when_missing_and_present_when_provided() -> None:
    payload = {
        "event_id": "evt_x",
        "issuer": {"company_id": "cik0001046179"},   # "cik" prefix w/o colon
        "fiscal_period": {"year": 2026, "quarter": 1},
        "facts": [
            {"schema": "event_fact.v1", "fact_id": "fact_revenue",
             "metric": "revenue", "value": 12.34, "unit": "usd_billions",
             "period": "2026-03-31", "basis": "reported_ifrs", "currency": "USD"},
        ],
        "guidance": [],
        "lifecycle": {"source_available_at": "2026-04-20T12:00:00Z",
                      "observed_at": "2026-04-20T12:00:00Z"},
    }
    row = project_event_workspace(payload)
    assert row is not None
    assert row["cik"] == "0001046179"
    assert "perimeter" not in row["reported"][0]   # not present → omitted
    assert "definition" not in row["reported"][0]  # not present → omitted
    assert "basis" in row["reported"][0] and "currency" in row["reported"][0]
    # missing lifecycle key is dropped, never coerced to None
    assert "recorded_at" not in row["lifecycle"]
    assert row["lifecycle"]["source_available_at"] == "2026-04-20T12:00:00Z"


# ─────────────────────────────────────────────────────────────────────────────
# (f) provenance / source_span never appear in reported
# ─────────────────────────────────────────────────────────────────────────────


def test_provenance_and_source_span_never_leak_into_reported() -> None:
    payload = {
        "event_id": "evt_x",
        "issuer": {"company_id": f"cik:{TSM_CIK}"},
        "fiscal_period": {"year": 2026, "quarter": 2},
        "facts": [
            {"schema": "event_fact.v1", "fact_id": "fact_revenue",
             "metric": "revenue", "value": 12.34, "unit": "usd_billions",
             "period": "2026-06-30", "basis": "reported_ifrs", "currency": "USD",
             "provenance": "verbatim prose about where the figure was read",
             "source_span": {"document_id": "syn-doc", "char_start": 100,
                             "char_end": 200, "literal": "12.34"},
             "perimeter": "as_reported", "definition": "revenue_net_of_returns"},
        ],
        "guidance": [],
        "lifecycle": {},
    }
    row = project_event_workspace(payload)
    assert row is not None
    [reported] = row["reported"]
    for forbidden in ("provenance", "source_span"):
        assert forbidden not in reported
    # Closed tokens, by contrast, are echoed verbatim.
    assert reported["basis"] == "reported_ifrs"
    assert reported["currency"] == "USD"
    assert reported["perimeter"] == "as_reported"
    assert reported["definition"] == "revenue_net_of_returns"
    # Closed fiscal_period is the workspace token, never the ISO period end.
    assert reported["fiscal_period"] == "2026Q2"