"""T08b + T08b-fix — bridge production ``event_workspace.v1`` payloads into
composer rows.

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier
PR #7870). The composer
(:func:`engine.market_ontology.semiconductor_theme_research.compose_semiconductor_research`)
keys on rows shaped like the synthetic witness fixture
(``tests/fixtures/semiconductor_theme_research/witness_hbm_packaging.json``).
Production intake (``scripts/refresh_event_workspaces.py``) emits a different
shape — ``facts`` of ``event_fact.v1`` with an ISO ``period`` end, an optional
``typed_absence`` envelope, an ``issuer`` block with a CIK-shaped
``company_id``, ``fiscal_period{year,quarter,calendar_end}``, a lifecycle
``{state, observed_at, source_available_at}`` without ``recorded_at``. This
file pins :func:`project_event_workspace` so the production intake can drive
the same composer the synthetic fixture drives, without ever authoring
authority or arithmetic.

Pinned here and nowhere else:

  * The two real-metadata payloads the ``test_semiconductor_earnings_intake_integration``
    carrier produces for TSM and ON project to rows whose ``reported[0]``
    carries ``metric='revenue'``, the closed basis, ``currency='USD'`` and
    the closed ``fiscal_period`` token — never the ISO ``period`` end.
  * The projected TSM Q1+Q2 bundle drives the composer to
    ``economics.status == 'ready'`` / ``prior_vs_actual.status == 'comparable'``
    (a refusal FAILS; there is no skip).
  * VERBATIM, NEVER PARSED: numeric strings (``"40.2"``, ``"2026"``, ``"2"``)
    and bools are refused; NaN/inf are dropped with a typed omission.
  * NEVER RAISES: unhashable basis, non-list guidance, non-dict lifecycle,
    hostile nested types — no exception for any input.
  * Closed CIK grammar (N3) and whole-payload refusal on an unparseable CIK
    (N12).
  * Two-clock law (N11): ``recorded_at`` is emitted from ``observed_at`` and
    the row SURVIVES the composer's real ``system_replay`` selection; a
    payload without ``observed_at`` projects no ``recorded_at`` and is
    dropped in replay.
  * Fresh copies (N6): mutating the projection never writes into the payload.
"""
from __future__ import annotations

import ast
import copy
import math
from pathlib import Path

import pytest

from engine.company_intelligence.issuer_profiles import ON_CIK, TSM_CIK
from engine.market_ontology.semiconductor_theme_research import (
    OwnerBundle,
    ResearchQuery,
    _Selection,
    compose_semiconductor_research,
)
from engine.market_ontology.workspace_projection import project_event_workspace

from tests.test_semiconductor_earnings_intake_integration import (
    ON_MANIFESTS,
    ON_Q2_MANIFESTS,
    ON_Q2_RESULTS_ACCESSION,
    ON_Q2_ROWS,
    ON_Q2_SYNTHETIC_EXHIBIT,
    ON_RESULTS_ACCESSION,
    ON_ROWS,
    ON_SYNTHETIC_EXHIBIT,
    TSM_MANIFESTS,
    TSM_Q1_MANIFEST,
    TSM_Q1_RESULTS_ACCESSION,
    TSM_Q1_ROW,
    TSM_Q1_SYNTHETIC_EXHIBIT,
    TSM_RESULTS_ACCESSION,
    TSM_ROWS,
    TSM_SYNTHETIC_EXHIBIT,
    _discover,
)

ROW_KEYS = ("event_id", "cik", "fiscal_period", "guidance", "reported", "lifecycle", "omissions")
MODULE_PATH = Path(__file__).resolve().parents[1] / "engine" / "market_ontology" / "workspace_projection.py"


def _fact(metric="revenue", value=12.34, **extra):
    label = metric if isinstance(metric, str) else "hostile"   # never str() a hostile metric
    fact = {"schema": "event_fact.v1", "fact_id": f"fact_{label}", "metric": metric,
            "value": value, "unit": "usd_billions", "period": "2026-06-30",
            "basis": "reported_ifrs", "currency": "USD"}
    fact.update(extra)
    return fact


def _payload(**overrides):
    payload = {
        "event_id": "evt_test",
        "issuer": {"company_id": f"cik:{TSM_CIK}"},
        "fiscal_period": {"year": 2026, "quarter": 2, "calendar_end": "2026-06-30"},
        "facts": [_fact()],
        "guidance": [],
        "lifecycle": {"state": "published",
                      "observed_at": "2026-07-21T00:00:00Z",
                      "source_available_at": "2026-07-16T12:00:00Z"},
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# (a) Real-metadata payloads from the integration test's `_discover` helper
# ─────────────────────────────────────────────────────────────────────────────


def _projected_tsm_q1_q2(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """TSM Q1-2026 + Q2-2026 events, each as the composer row, through the
    production identity + profile (no seams; only the network is replaced)."""
    revisions, _ = _discover(
        monkeypatch, ticker="TSM", cik=TSM_CIK,
        rows=TSM_ROWS + [TSM_Q1_ROW],
        manifests={**TSM_MANIFESTS, **TSM_Q1_MANIFEST},
        bodies={TSM_RESULTS_ACCESSION: TSM_SYNTHETIC_EXHIBIT,
                TSM_Q1_RESULTS_ACCESSION: TSM_Q1_SYNTHETIC_EXHIBIT},
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


def test_tsm_real_metadata_projects_to_revenue_ifrs_usd_q1_q2(monkeypatch) -> None:
    projected = _projected_tsm_q1_q2(monkeypatch)
    assert len(projected) == 2
    by_period = _by_fp(projected)
    q1, q2 = by_period[(2026, 1)], by_period[(2026, 2)]

    assert q1["event_id"].endswith("2026q1_results")
    assert q2["event_id"].endswith("2026q2_results")
    assert q1["cik"] == "0001046179" and q2["cik"] == "0001046179"
    assert "company_node_id" not in q1 and "company_node_id" not in q2
    assert tuple(q1) == ROW_KEYS and tuple(q2) == ROW_KEYS

    q1_rev = next(row for row in q1["reported"] if row["metric"] == "revenue")
    q2_rev = next(row for row in q2["reported"] if row["metric"] == "revenue")
    assert q1_rev["currency"] == "USD" and q2_rev["currency"] == "USD"
    assert q1_rev["basis"] == "reported_ifrs" and q2_rev["basis"] == "reported_ifrs"
    assert q1_rev["fiscal_period"] == "2026Q1" and q2_rev["fiscal_period"] == "2026Q2"
    assert q1_rev["unit"] == "usd_billions" and q2_rev["unit"] == "usd_billions"
    assert isinstance(q1_rev["value"], float) and math.isfinite(q1_rev["value"])
    for row in q1["reported"] + q2["reported"]:
        assert "provenance" not in row and "source_span" not in row
    # Production lifecycle carries observed_at; the two-clock law derives recorded_at.
    for row in (q1, q2):
        assert row["lifecycle"]["recorded_at"] == row["lifecycle"]["observed_at"]
        assert row["omissions"] == []


def test_on_real_metadata_projects_to_revenue_gaap_usd_q1_q2(monkeypatch) -> None:
    revisions, _ = _discover(
        monkeypatch, ticker="ON", cik=ON_CIK,
        rows=ON_ROWS + ON_Q2_ROWS,
        manifests={**ON_MANIFESTS, **ON_Q2_MANIFESTS},
        bodies={ON_RESULTS_ACCESSION: ON_SYNTHETIC_EXHIBIT,
                ON_Q2_RESULTS_ACCESSION: ON_Q2_SYNTHETIC_EXHIBIT},
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


# ─────────────────────────────────────────────────────────────────────────────
# (b) The projected TSM Q1+Q2 rows drive the composer to `economics.ready`
# ─────────────────────────────────────────────────────────────────────────────


def _tsm_q1_q2_bundle(projected: list[dict]) -> OwnerBundle:
    """An OwnerBundle whose event_workspaces are the projected rows, with one
    bound ``ready`` packet whose derivation inputs reference BOTH event ids
    (the only shape ``_build_economics`` accepts). identity_results are
    empty: ``_build_economics`` keys on ``workspace['cik']`` directly."""
    cik = projected[0]["cik"]
    inputs = sorted({projected[0]["event_id"], projected[1]["event_id"]})
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
        revision_tuple=tuple(("event", event_id) for event_id in inputs),
        rights_revision="synthetic-rights-0",
        assertions=(),
        identity_results=(),
        event_workspaces=tuple(projected),
        financial_packets=(packet,),
        interpretation_blocks=(),
        native_refs=(),
        omissions=(),
    )


def test_projected_tsm_two_quarter_bundle_drives_economics_ready(monkeypatch) -> None:
    """A composer refusal here FAILS the test (no skip escape hatch)."""
    projected = _projected_tsm_q1_q2(monkeypatch)
    bundle = _tsm_q1_q2_bundle(projected)
    query = ResearchQuery(
        anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
        view="economics", time_mode="latest",
        source_cutoff=None, recorded_cutoff=None,
    )
    response = compose_semiconductor_research(query, bundle)
    assert response["economics"]["status"] == "ready", response["economics"]
    management = response["economics"]["management"]
    assert management is not None
    assert management["comparisons"]["prior_vs_actual"]["status"] == "comparable", management


def test_projected_tsm_rows_drive_economics_ready_under_system_replay(monkeypatch) -> None:
    """N11 end-to-end in ONE path: the REAL projected rows (production
    lifecycle → recorded_at) survive the composer's system_replay gate and
    still reach economics.ready / comparable. Cutoffs sit after the
    discovery-time observed_at (wall-clock now) and after the packet's
    recorded_at."""
    projected = _projected_tsm_q1_q2(monkeypatch)
    for row in projected:
        assert row["lifecycle"]["recorded_at"] == row["lifecycle"]["observed_at"]
    bundle = _tsm_q1_q2_bundle(projected)
    query = ResearchQuery(
        anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
        view="economics", time_mode="system_replay",
        source_cutoff="2099-12-31", recorded_cutoff="2099-12-31",
    )
    response = compose_semiconductor_research(query, bundle)
    assert response["economics"]["status"] == "ready", response["economics"]
    assert response["economics"]["management"]["comparisons"]["prior_vs_actual"]["status"] == "comparable"
    assert sorted(response["economics"]["input_refs"]) == sorted(r["event_id"] for r in projected)
    # And a recorded_cutoff BEFORE the rows' observed_at drops them: no triple.
    early = ResearchQuery(
        anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
        view="economics", time_mode="system_replay",
        source_cutoff="2099-12-31", recorded_cutoff="2026-01-01",
    )
    assert compose_semiconductor_research(early, bundle)["economics"]["status"] == "unavailable"


# ─────────────────────────────────────────────────────────────────────────────
# (c) Typed absences never produce rows
# ─────────────────────────────────────────────────────────────────────────────


def test_typed_absence_facts_never_produce_reported_rows() -> None:
    payload = _payload(facts=[
        _fact(),
        {"schema": "event_fact.v1", "fact_id": "fact_revenue_twd",
         "metric": "revenue", "typed_absence": {"reason": "missing_units"}},
    ])
    row = project_event_workspace(payload)
    assert row is not None
    assert [r["metric"] for r in row["reported"]] == ["revenue"]
    assert row["omissions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# (d) Two present facts sharing (metric, basis) → no row + omission token
# ─────────────────────────────────────────────────────────────────────────────


def test_two_present_facts_same_metric_and_basis_yield_no_row_with_omission_token() -> None:
    payload = _payload(facts=[_fact(value=12.34, fact_id="a"), _fact(value=12.35, fact_id="b")])
    row = project_event_workspace(payload)
    assert row is not None
    assert row["reported"] == []
    assert row["omissions"] == ["reported_ambiguous:revenue"]
    payload["facts"][1]["basis"] = "reported_gaap"      # different bases do not collide
    row = project_event_workspace(payload)
    assert row is not None and len(row["reported"]) == 2
    assert row["omissions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# (e) Whole-payload refusals → None, never an exception
# ─────────────────────────────────────────────────────────────────────────────


def test_non_mapping_payload_yields_none() -> None:
    for probe in (None, "not a mapping", [1, 2, 3], 42, b"bytes", {"a"}):
        assert project_event_workspace(probe) is None  # type: ignore[arg-type]


def test_missing_event_id_yields_none() -> None:
    assert project_event_workspace(_payload(event_id=None)) is None
    assert project_event_workspace(_payload(event_id="")) is None
    assert project_event_workspace(_payload(event_id=7)) is None


def test_missing_fiscal_period_yields_none() -> None:
    assert project_event_workspace(_payload(fiscal_period=None)) is None
    assert project_event_workspace(_payload(fiscal_period="not a mapping")) is None
    assert project_event_workspace(_payload(fiscal_period=[2026, 2])) is None


@pytest.mark.parametrize("quarter", [
    pytest.param("Q1", id="text"),
    pytest.param("2", id="numeric-string-refused"),
    pytest.param(2.0, id="float"),
    pytest.param(True, id="bool"),
    pytest.param(5, id="above-range"),
    pytest.param(0, id="zero"),
    pytest.param(None, id="none"),
])
def test_non_int_or_out_of_range_quarter_yields_none(quarter) -> None:
    assert project_event_workspace(_payload(fiscal_period={"year": 2026, "quarter": quarter})) is None


# ─────────────────────────────────────────────────────────────────────────────
# (f) Closed CIK grammar (N3) + whole-payload refusal on unparseable CIK (N12)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("company_id, expected", [
    pytest.param("cik:0001046179", "0001046179", id="prefixed-colon"),
    pytest.param("cik0001046179", "0001046179", id="prefixed-bare"),
    pytest.param("CIK:0001046179", "0001046179", id="prefix-upper"),
    pytest.param("0001046179", "0001046179", id="bare-ten"),
    pytest.param("1046179", "0001046179", id="bare-short-padded"),
    pytest.param("cik:1", "0000000001", id="prefixed-one-digit"),
])
def test_closed_cik_grammar_accepts_only_cik_prefixed_or_bare_digits(company_id, expected) -> None:
    row = project_event_workspace(_payload(issuer={"company_id": company_id}))
    assert row is not None and row["cik"] == expected


@pytest.mark.parametrize("company_id", [
    pytest.param("lei:5493001KJTIIGC8Y1R12", id="lei-digit-run"),
    pytest.param("0001046179  abcd", id="digits-then-prose"),
    pytest.param(" cik:0001046179", id="leading-space"),
    pytest.param("cik:0001046179 ", id="trailing-space"),
    pytest.param("cik:00010461790", id="eleven-digits"),
    pytest.param("cik:", id="prefix-only"),
    pytest.param("cik:٠٠٠١٠٤٦١٧٩", id="unicode-digits"),
    pytest.param("cik:1046179x", id="digits-then-letter"),
    pytest.param("0", id="all-zero-one-digit"),
    pytest.param("cik:0000000000", id="all-zero-ten-digits"),
    pytest.param("TSM", id="ticker"),
    pytest.param("", id="empty"),
    pytest.param(None, id="none"),
    pytest.param(1046179, id="int"),
    pytest.param(["cik:0001046179"], id="list"),
])
def test_unparseable_cik_refuses_the_whole_payload(company_id) -> None:
    assert project_event_workspace(_payload(issuer={"company_id": company_id})) is None


def test_missing_or_non_mapping_issuer_refuses_the_whole_payload() -> None:
    payload = _payload()
    del payload["issuer"]
    assert project_event_workspace(payload) is None
    assert project_event_workspace(_payload(issuer="cik:0001046179")) is None
    assert project_event_workspace(_payload(issuer={"display_name": "No id"})) is None


# ─────────────────────────────────────────────────────────────────────────────
# (g) Verbatim numerics — never parsed, never coerced (B2, N4)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value", [
    pytest.param("40.2", id="numeric-string"),
    pytest.param("1_000", id="underscore-string"),
    pytest.param("٢", id="unicode-digit-string"),
    pytest.param("1e400", id="exp-string"),
    pytest.param("twelve point three four", id="prose"),
    pytest.param(True, id="bool-true"),
    pytest.param(False, id="bool-false"),
    pytest.param(None, id="none"),
    pytest.param([12.34], id="list"),
    pytest.param({"v": 12.34}, id="dict"),
])
def test_non_numeric_value_is_not_present_and_never_raises(value) -> None:
    row = project_event_workspace(_payload(facts=[_fact(value=value)]))
    assert row is not None
    assert row["reported"] == []
    assert row["omissions"] == []          # not present: nothing to type


@pytest.mark.parametrize("value", [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="inf"),
    pytest.param(float("-inf"), id="neg-inf"),
])
def test_non_finite_value_is_dropped_with_typed_omission(value) -> None:
    row = project_event_workspace(_payload(facts=[_fact(value=value)]))
    assert row is not None
    assert row["reported"] == []
    assert row["omissions"] == ["reported_non_finite:revenue"]


def test_numeric_values_are_copied_verbatim_including_ints_and_huge_ints() -> None:
    row = project_event_workspace(_payload(facts=[
        _fact(metric="a", value=7), _fact(metric="b", value=12.34), _fact(metric="c", value=10 ** 400),
    ]))
    assert row is not None
    by_metric = {r["metric"]: r["value"] for r in row["reported"]}
    assert by_metric == {"a": 7, "b": 12.34, "c": 10 ** 400}
    assert type(by_metric["a"]) is int and type(by_metric["b"]) is float


@pytest.mark.parametrize("year", [
    pytest.param("2026", id="numeric-string"),
    pytest.param(2026.0, id="float"),
    pytest.param(True, id="bool"),
    pytest.param(None, id="none"),
    pytest.param(7, id="one-digit"),
    pytest.param(-5, id="negative"),
    pytest.param(999, id="below-range"),
    pytest.param(10000, id="above-range"),
    pytest.param(10 ** 20, id="huge"),
    pytest.param(10 ** 4300, id="beyond-int-str-limit"),
])
def test_non_formable_year_drops_facts_with_unkeyed_omission_and_projects_year_none(year) -> None:
    row = project_event_workspace(_payload(fiscal_period={"year": year, "quarter": 2}))
    assert row is not None
    assert row["fiscal_period"] == {"year": None, "quarter": 2}
    assert row["reported"] == []
    assert row["omissions"] == ["reported_unkeyed:fiscal_period"]


@pytest.mark.parametrize("year", [1000, 2026, 9999])
def test_four_digit_years_form_the_closed_token(year) -> None:
    row = project_event_workspace(_payload(fiscal_period={"year": year, "quarter": 3}))
    assert row is not None
    assert row["fiscal_period"] == {"year": year, "quarter": 3}
    assert row["reported"][0]["fiscal_period"] == f"{year}Q3"


def test_unkeyed_omission_is_recorded_only_when_present_facts_exist() -> None:
    row = project_event_workspace(_payload(fiscal_period={"year": "2026", "quarter": 2}, facts=[]))
    assert row is not None and row["omissions"] == []
    row = project_event_workspace(_payload(
        fiscal_period={"year": "2026", "quarter": 2},
        facts=[{"metric": "revenue", "typed_absence": {"reason": "x"}}],
    ))
    assert row is not None and row["omissions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# (h) Malformed nested inputs — never raise, exact shape (B1, N10)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("basis", [
    pytest.param({"k": "v"}, id="dict-basis"),
    pytest.param(["a"], id="list-basis"),
    pytest.param(7, id="int-basis"),
])
def test_unhashable_or_non_token_basis_drops_the_fact_with_malformed_omission(basis) -> None:
    row = project_event_workspace(_payload(facts=[_fact(basis=basis)]))
    assert row is not None
    assert row["reported"] == []
    assert row["omissions"] == ["reported_malformed:revenue"]


@pytest.mark.parametrize("key", ["currency", "perimeter", "definition", "unit"])
def test_non_token_optional_field_drops_the_fact(key) -> None:
    row = project_event_workspace(_payload(facts=[_fact(**{key: {"nested": True}})]))
    assert row is not None
    assert row["reported"] == [] and row["omissions"] == ["reported_malformed:revenue"]


def test_explicit_none_tokens_are_copied_verbatim() -> None:
    row = project_event_workspace(_payload(facts=[_fact(basis=None, currency=None)]))
    assert row is not None
    [reported] = row["reported"]
    assert reported["basis"] is None and reported["currency"] is None


@pytest.mark.parametrize("facts", [
    pytest.param(None, id="none"),
    pytest.param("revenue", id="string"),
    pytest.param({"metric": "revenue", "value": 1.0}, id="mapping-not-list"),
    pytest.param([None, "x", 7, ["nested"]], id="non-mapping-items"),
    pytest.param([{"value": 1.0}], id="missing-metric"),
    pytest.param([{"metric": "", "value": 1.0}], id="empty-metric"),
    pytest.param([{"metric": 7, "value": 1.0}], id="non-string-metric"),
])
def test_malformed_facts_yield_no_rows_and_no_exception(facts) -> None:
    row = project_event_workspace(_payload(facts=facts))
    assert row is not None and row["reported"] == [] and row["omissions"] == []


@pytest.mark.parametrize("guidance", [
    pytest.param(None, id="none"),
    pytest.param("not a list", id="string"),
    pytest.param({"horizon": "2026Q3"}, id="mapping-not-list"),
])
def test_guidance_not_a_list_projects_empty(guidance) -> None:
    row = project_event_workspace(_payload(guidance=guidance))
    assert row is not None and row["guidance"] == [] and row["omissions"] == []


def test_non_mapping_guidance_items_are_dropped_with_typed_omission() -> None:
    row = project_event_workspace(_payload(guidance=["bad", 7, None, {"horizon": "2026Q3"}]))
    assert row is not None
    assert row["guidance"] == [{"horizon": "2026Q3"}]
    assert row["omissions"] == ["guidance_malformed_item"]


def _deep(levels: int) -> dict:
    root: dict = {}
    cursor = root
    for _ in range(levels):
        cursor["n"] = {}
        cursor = cursor["n"]
    return root


def test_uncopyable_guidance_items_are_dropped_not_raised() -> None:
    def gen():
        yield 1

    row = project_event_workspace(_payload(guidance=[
        {"g": gen()},                      # unpicklable member → TypeError inside deepcopy
        _deep(5000),                       # pathological nesting → RecursionError inside deepcopy
        {"horizon": "2026Q3"},
    ]))
    assert row is not None
    assert row["guidance"] == [{"horizon": "2026Q3"}]
    assert row["omissions"] == ["guidance_malformed_item"]


@pytest.mark.parametrize("value", [
    pytest.param("mutated", id="prose"),
    pytest.param("2026-13-45", id="impossible-date"),
    pytest.param("2026-07-21T25:00:00Z", id="impossible-instant"),
    pytest.param("", id="empty"),
    pytest.param(1721000000, id="epoch-int"),
    pytest.param(["2026-07-21"], id="list"),
])
def test_lifecycle_value_outside_the_clock_grammar_is_dropped_with_typed_omission(value) -> None:
    row = project_event_workspace(_payload(lifecycle={
        "observed_at": value, "source_available_at": "2026-07-16T12:00:00Z",
    }))
    assert row is not None
    assert row["lifecycle"] == {"source_available_at": "2026-07-16T12:00:00Z"}
    assert row["omissions"] == ["lifecycle_malformed:observed_at"]
    row = project_event_workspace(_payload(lifecycle={"source_available_at": value}))
    assert row is not None
    assert row["lifecycle"] == {}
    assert row["omissions"] == ["lifecycle_malformed:source_available_at"]


def test_explicit_none_lifecycle_value_is_a_typed_absence_not_malformed() -> None:
    """Production's _lifecycle_payload emits None for an unknown clock; a typed
    absence is dropped silently, never recorded as malformed."""
    row = project_event_workspace(_payload(lifecycle={"observed_at": None, "source_available_at": None,
                                                      "state": "published"}))
    assert row is not None and row["lifecycle"] == {} and row["omissions"] == []


def test_hostile_str_subclass_in_lifecycle_never_raises() -> None:
    class HostileStr(str):
        def __contains__(self, item):
            raise RuntimeError("hostile __contains__")

    row = project_event_workspace(_payload(lifecycle={"observed_at": HostileStr("2026-07-21")}))
    assert row is not None and row["lifecycle"] == {}
    assert row["omissions"] == ["lifecycle_malformed:observed_at"]


def test_uncopyable_lifecycle_value_is_dropped_not_raised() -> None:
    def gen():
        yield 1

    row = project_event_workspace(_payload(lifecycle={"observed_at": gen(), "source_available_at": "unknown"}))
    assert row is not None
    assert row["lifecycle"] == {"source_available_at": "unknown"}
    assert row["omissions"] == ["lifecycle_malformed:observed_at"]


@pytest.mark.parametrize("value", [
    pytest.param("2026-07-21", id="date-only"),
    pytest.param("2026-07-21T09:15:00Z", id="instant-z"),
    pytest.param("2026-07-21T09:15:00+00:00", id="instant-offset"),
    pytest.param("2026-07-21T09:15:00.250000Z", id="instant-micros"),
])
def test_clock_strings_in_the_composer_grammar_are_copied_verbatim_and_promoted(value) -> None:
    row = project_event_workspace(_payload(lifecycle={"observed_at": value, "source_available_at": value}))
    assert row is not None
    assert row["lifecycle"] == {"source_available_at": value, "observed_at": value, "recorded_at": value}
    assert row["omissions"] == []
    assert [w["event_id"] for w in _replay_selection([row], recorded_cutoff="2099-12-31")] == ["evt_test"]


def test_typed_unknown_source_availability_is_copied_verbatim_for_the_composer() -> None:
    row = project_event_workspace(_payload(lifecycle={"source_available_at": "unknown",
                                                      "observed_at": "2026-07-21T09:15:00Z"}))
    assert row is not None
    assert row["lifecycle"]["source_available_at"] == "unknown"
    assert row["omissions"] == []
    # observed_at never accepts the typed literal: it is a system clock reading.
    row = project_event_workspace(_payload(lifecycle={"observed_at": "unknown"}))
    assert row is not None and row["lifecycle"] == {} and row["omissions"] == ["lifecycle_malformed:observed_at"]


@pytest.mark.parametrize("lifecycle", [
    pytest.param(None, id="none"),
    pytest.param("published", id="string"),
    pytest.param(["observed_at"], id="list"),
])
def test_lifecycle_not_a_dict_projects_empty(lifecycle) -> None:
    row = project_event_workspace(_payload(lifecycle=lifecycle))
    assert row is not None and row["lifecycle"] == {}


def test_optional_tokens_are_absent_when_missing_and_present_when_provided() -> None:
    payload = _payload(
        issuer={"company_id": "cik0001046179"},
        facts=[{"schema": "event_fact.v1", "fact_id": "fact_revenue",
                "metric": "revenue", "value": 12.34, "unit": "usd_billions",
                "period": "2026-03-31", "basis": "reported_ifrs", "currency": "USD"}],
        lifecycle={"source_available_at": "2026-04-20T12:00:00Z"},
    )
    row = project_event_workspace(payload)
    assert row is not None
    assert row["cik"] == "0001046179"
    assert "perimeter" not in row["reported"][0] and "definition" not in row["reported"][0]
    assert "basis" in row["reported"][0] and "currency" in row["reported"][0]
    assert row["lifecycle"] == {"source_available_at": "2026-04-20T12:00:00Z"}
    assert "recorded_at" not in row["lifecycle"] and "observed_at" not in row["lifecycle"]


def test_provenance_and_source_span_never_leak_into_reported() -> None:
    payload = _payload(facts=[_fact(
        provenance="verbatim prose about where the figure was read",
        source_span={"document_id": "syn-doc", "char_start": 100, "char_end": 200, "literal": "12.34"},
        perimeter="as_reported", definition="revenue_net_of_returns",
    )])
    row = project_event_workspace(payload)
    assert row is not None
    [reported] = row["reported"]
    assert "provenance" not in reported and "source_span" not in reported
    assert reported["basis"] == "reported_ifrs" and reported["currency"] == "USD"
    assert reported["perimeter"] == "as_reported"
    assert reported["definition"] == "revenue_net_of_returns"
    assert reported["fiscal_period"] == "2026Q2"


def test_row_carries_exactly_the_seven_keys() -> None:
    row = project_event_workspace(_payload())
    assert row is not None and tuple(row) == ROW_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# (i) Fresh copies (N6)
# ─────────────────────────────────────────────────────────────────────────────


def test_projection_returns_fresh_copies_that_do_not_alias_the_payload() -> None:
    guidance_item = {"schema": "guidance_item.v1", "horizon": "2026Q3", "range": {"low": 1, "high": 2}}
    payload = _payload(guidance=[guidance_item], facts=[_fact(definition="x")])
    before = copy.deepcopy(payload)
    row = project_event_workspace(payload)
    assert row is not None
    row["guidance"][0]["range"]["low"] = 999
    row["guidance"].append({"injected": True})
    row["reported"][0]["definition"] = "mutated"
    row["reported"][0]["unit"] = "mutated"
    row["lifecycle"]["observed_at"] = "mutated"
    row["omissions"].append("mutated")
    assert payload == before
    assert row["guidance"][0] is not guidance_item


# ─────────────────────────────────────────────────────────────────────────────
# (j) Two-clock law (N11): recorded_at from observed_at; replay survival
# ─────────────────────────────────────────────────────────────────────────────

_PRODUCTION_LIFECYCLE = {
    "state": "published",
    "observed_at": "2026-07-21T09:15:00Z",
    "source_available_at": "2026-07-16T12:00:00Z",
}


def _replay_selection(rows, *, recorded_cutoff: str, source_cutoff: str = "2026-07-31") -> list[dict]:
    bundle = OwnerBundle(
        revision_tuple=(("event", "evt_test"),),
        rights_revision="synthetic-rights-0",
        assertions=(), identity_results=(),
        event_workspaces=tuple(rows),
        financial_packets=(), interpretation_blocks=(), native_refs=(), omissions=(),
    )
    query = ResearchQuery(
        anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
        view="economics", time_mode="system_replay",
        source_cutoff=source_cutoff, recorded_cutoff=recorded_cutoff,
    )
    return _Selection(query, bundle).event_workspaces()


def test_production_lifecycle_projects_recorded_at_equal_to_observed_at() -> None:
    row = project_event_workspace(_payload(lifecycle=dict(_PRODUCTION_LIFECYCLE)))
    assert row is not None
    assert row["lifecycle"] == {
        "source_available_at": "2026-07-16T12:00:00Z",
        "observed_at": "2026-07-21T09:15:00Z",
        "recorded_at": "2026-07-21T09:15:00Z",
    }


def test_projected_production_row_survives_the_composers_system_replay_selection() -> None:
    row = project_event_workspace(_payload(lifecycle=dict(_PRODUCTION_LIFECYCLE)))
    assert row is not None
    assert [w["event_id"] for w in _replay_selection([row], recorded_cutoff="2026-07-21T09:15:00Z")] == ["evt_test"]
    assert [w["event_id"] for w in _replay_selection([row], recorded_cutoff="2026-07-22")] == ["evt_test"]
    # A recorded_cutoff BEFORE observed_at excludes the row: the gate reads the system clock.
    assert _replay_selection([row], recorded_cutoff="2026-07-21T09:14:59Z") == []


@pytest.mark.parametrize("lifecycle", [
    pytest.param({"state": "published", "source_available_at": "2026-07-16T12:00:00Z"}, id="no-observed_at"),
    pytest.param({"observed_at": "", "source_available_at": "2026-07-16T12:00:00Z"}, id="empty-observed_at"),
    pytest.param({"observed_at": None, "source_available_at": "2026-07-16T12:00:00Z"}, id="none-observed_at"),
    pytest.param({"observed_at": 1721000000, "source_available_at": "2026-07-16T12:00:00Z"}, id="int-observed_at"),
])
def test_payload_without_observed_at_projects_no_recorded_at_and_is_dropped_in_replay(lifecycle) -> None:
    row = project_event_workspace(_payload(lifecycle=lifecycle))
    assert row is not None
    assert "recorded_at" not in row["lifecycle"]
    assert _replay_selection([row], recorded_cutoff="2026-12-31") == []


def test_payload_supplied_recorded_at_is_never_copied() -> None:
    """recorded_at is the system clock derived from observed_at — a payload
    cannot forge it, and it is never taken from generated_at or a manifest."""
    row = project_event_workspace(_payload(lifecycle={
        "observed_at": "2026-07-21T09:15:00Z",
        "recorded_at": "2020-01-01T00:00:00Z",
        "generated_at": "2026-07-16T12:00:00Z",
    }))
    assert row is not None
    assert row["lifecycle"] == {"observed_at": "2026-07-21T09:15:00Z",
                                "recorded_at": "2026-07-21T09:15:00Z"}
    row = project_event_workspace(_payload(lifecycle={
        "recorded_at": "2020-01-01T00:00:00Z", "generated_at": "2026-07-16T12:00:00Z",
    }))
    assert row is not None and row["lifecycle"] == {}


# ─────────────────────────────────────────────────────────────────────────────
# (k) Never raises — hostile grid over every slot
# ─────────────────────────────────────────────────────────────────────────────

def _gen():
    yield 1


_HOSTILE = [None, "", "x", "40.2", 0, 1, -1, 2.5, True, False, float("nan"), float("inf"),
            [], ["a"], {}, {"k": "v"}, {"k": {"n": ["deep"]}}, b"bytes", 10 ** 400, 10 ** 4300,
            object(), _gen(), {"g": _gen()}, "2026-13-45", "mutated"]


def test_never_raises_for_any_slot_value() -> None:
    slots = ("event_id", "issuer", "fiscal_period", "facts", "guidance", "lifecycle")
    for slot in slots:
        for hostile in _HOSTILE:
            project_event_workspace(_payload(**{slot: hostile}))
    for hostile in _HOSTILE:
        project_event_workspace(_payload(issuer={"company_id": hostile}))
        project_event_workspace(_payload(fiscal_period={"year": hostile, "quarter": 2}))
        project_event_workspace(_payload(fiscal_period={"year": 2026, "quarter": hostile}))
        project_event_workspace(_payload(facts=[hostile]))
        project_event_workspace(_payload(guidance=[hostile]))
        for key in ("metric", "value", "unit", "basis", "currency", "perimeter", "definition"):
            project_event_workspace(_payload(facts=[_fact(**{key: hostile})]))
        for key in ("observed_at", "source_available_at", "recorded_at", "state"):
            project_event_workspace(_payload(lifecycle={key: hostile}))
    project_event_workspace(_payload(guidance=[_deep(5000)], facts=[_deep(5000)], lifecycle=_deep(5000)))


# ─────────────────────────────────────────────────────────────────────────────
# (l) Module closure — parsers only, no clock read, no conversion of payload values
# ─────────────────────────────────────────────────────────────────────────────


def test_module_never_reads_the_clock_and_applies_no_numeric_conversion() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            assert name not in {"now", "today", "utcnow", "time", "open", "float", "int",
                                "str", "round", "abs", "eval", "exec"}, name
    assert roots == {"__future__", "copy", "math", "datetime", "typing"}, sorted(roots)
