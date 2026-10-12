from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from scripts.build_fundamental_forensics import (
    PUBLIC_SUMMARY_MAX_AGE_DAYS,
    PUBLIC_SUMMARY_RELATIVE,
    PUBLIC_SUMMARY_SCHEMA as SCHEMA_PUBLIC,
    SCHEMA,
    _write_public_summary,
    _write_state_atomic,
    compose_state,
    detector_evaluability,
    detect_quarterly,
    public_summary_projection,
    read_public_summary,
    render_shell,
)
from engine.fundamental_forensics.peer_cohort import CohortDefinition


def test_atomic_private_state_gzip_is_path_independent_and_deterministic(tmp_path: Path):
    state = {
        "schema": SCHEMA,
        "generated_at": "2026-08-01T12:00:00+00:00",
        "companies": {},
    }
    first = _write_state_atomic(tmp_path / "one" / "state.json.gz", state)
    second = _write_state_atomic(tmp_path / "two" / "state.json.gz", state)

    assert first.read_bytes() == second.read_bytes()
    assert not list(tmp_path.rglob("*.tmp"))


def _q(**overrides):
    base = {
        "ticker": "TST",
        "fiscal_year": 2025,
        "fiscal_quarter": 2,
        "period_end": "2025-06-30",
        "filed": "2025-08-01",
        "revenue": 100.0,
        "gross_profit": 40.0,
        "receivables": 20.0,
        "inventory": 20.0,
        "cfo": 15.0,
        "capex": 10.0,
        "op_income": 15.0,
        "ni": 12.0,
        "contract_liabilities": 5.0,
    }
    base.update(overrides)
    return base


def test_quarterly_detectors_emit_review_prompts_without_company_score():
    prior = pd.Series(_q())
    current = pd.Series(_q(
        fiscal_year=2026,
        period_end="2026-06-30",
        filed="2026-08-01",
        revenue=105.0,
        gross_profit=36.75,  # 35% margin vs 40%
        receivables=35.0,
        inventory=40.0,
        capex=30.0,
        op_income=16.0,
    ))
    findings = detect_quarterly(current, prior, 320193)
    ids = {item["detector"] for item in findings}

    assert ids == {
        "margin_compression_despite_revenue_growth",
        "receivables_stretch",
        "inventory_build",
        "capital_intensity_rising",
    }
    encoded = json.dumps(findings).lower()
    assert '"score"' not in encoded
    assert '"rank"' not in encoded
    assert "fraud" not in encoded
    assert all(item["display_only"] for item in findings)
    assert all(item["authority"] == "review_priority_only" for item in findings)
    assert all(item["evidence"][0]["url"].startswith("https://www.sec.gov/") for item in findings)


def test_receivables_boundary_is_strictly_greater_than_ten_points():
    prior = pd.Series(_q())
    exact = pd.Series(_q(fiscal_year=2026, period_end="2026-06-30", revenue=105.0, receivables=23.0))
    # revenue +5%; receivables +15% -> exactly +10pp, therefore clear.
    assert "receivables_stretch" not in {f["detector"] for f in detect_quarterly(exact, prior, None)}


def test_coverage_uses_detector_denominators_and_consecutive_years():
    prior = pd.Series(_q(
        revenue=0.0,
        receivables=0.0,
        inventory=0.0,
        capex=0.0,
        op_income=0.0,
    ))
    current = pd.Series(_q(fiscal_year=2026, period_end="2026-06-30"))
    nonconsecutive = pd.DataFrame([
        {"fy": 2021, "period_end": "2021-12-31", "ni": 1.0, "cfo": 1.0, "assets": 10.0},
        {"fy": 2023, "period_end": "2023-12-31", "ni": 1.0, "cfo": 1.0, "assets": 10.0},
        {"fy": 2025, "period_end": "2025-12-31", "ni": 1.0, "cfo": 1.0, "assets": 10.0},
    ])

    coverage = detector_evaluability(current, prior, nonconsecutive)

    assert coverage == {
        "margin_compression_despite_revenue_growth": False,
        "receivables_stretch": False,
        "inventory_build": False,
        "capital_intensity_rising": False,
        "accruals_trending_up": False,
    }


def test_compose_state_contract_and_pit_clock(tmp_path: Path):
    q_dir = tmp_path / "data" / "edgar"
    q_dir.mkdir(parents=True)
    quarterly = pd.DataFrame([
        _q(fiscal_year=2024, period_end="2024-06-30", filed="2024-08-01"),
        _q(fiscal_year=2025, period_end="2025-06-30", filed="2025-08-01"),
        _q(
            fiscal_year=2026,
            period_end="2026-06-30",
            filed="2026-08-01",
            revenue=105.0,
            gross_profit=36.75,
            receivables=35.0,
            inventory=40.0,
            capex=30.0,
            op_income=16.0,
        ),
    ])
    quarterly.to_parquet(q_dir / "statements_quarterly.parquet", index=False)
    annual = pd.DataFrame([
        {"ticker": "TST", "fy": 2023, "period_end": "2023-12-31", "ni": 10.0, "cfo": 14.0, "assets": 100.0},
        {"ticker": "TST", "fy": 2024, "period_end": "2024-12-31", "ni": 12.0, "cfo": 13.0, "assets": 100.0},
        {"ticker": "TST", "fy": 2025, "period_end": "2025-12-31", "ni": 18.0, "cfo": 10.0, "assets": 100.0},
    ])
    annual.to_parquet(q_dir / "statements.parquet", index=False)

    state = compose_state(tmp_path, generated_at="2026-08-01T12:00:00+00:00")
    source_clock_state = compose_state(tmp_path)

    assert state["schema"] == SCHEMA
    assert state["generated_at"] == "2026-08-01T12:00:00+00:00"
    assert source_clock_state["generated_at"] == "2026-08-01T23:59:59+00:00"
    assert state["as_of"] == "2026-08-01"
    assert state["summary"]["companies"] == 1
    assert state["companies"]["TST"]["action"]["key"] == "high"
    assert len(state["companies"]["TST"]["periods"]) == 3
    encoded = json.dumps(state).lower()
    assert '"company_score"' not in encoded
    assert '"rank"' not in encoded
    assert '"fraud"' not in encoded
    assert state["source"]["basis"] == "repository quarterly and annual EDGAR panels"


def _render_into(tmp_path: Path, root: Path, *, summary=None) -> str:
    """Render the shell inside tmp_path against the real templates."""
    (tmp_path / "templates").symlink_to(root / "templates")
    if summary is not None:
        _write_public_summary(tmp_path, summary)
    return render_shell(tmp_path, state_summary=summary).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# FIF P1-b state data contract (items I1, I2, I4, I5)
# ---------------------------------------------------------------------------

GEN_AT = "2026-10-12T00:00:00+00:00"


def _write_workbench_panel(
    root: Path,
    *,
    cik: int | None = None,
    period_start_by_year: dict[int, str | None] | None = None,
) -> None:
    """Write the synthetic TST quarterly+annual panel (the contract-test shape)."""
    q_dir = root / "data" / "edgar"
    q_dir.mkdir(parents=True, exist_ok=True)

    def _row(fy: int, end: str, filed: str, **overrides):
        base = _q(fiscal_year=fy, period_end=end, filed=filed)
        base.update(overrides)
        return base

    quarterly_rows = [
        _row(2024, "2024-06-30", "2024-08-01"),
        _row(2025, "2025-06-30", "2025-08-01"),
        _row(
            2026, "2026-06-30", "2026-08-01",
            revenue=105.0, gross_profit=36.75, receivables=35.0,
            inventory=40.0, capex=30.0, op_income=16.0,
        ),
    ]
    if period_start_by_year is not None:
        for row in quarterly_rows:
            row["period_start"] = period_start_by_year.get(row["fiscal_year"])
    pd.DataFrame(quarterly_rows).to_parquet(q_dir / "statements_quarterly.parquet", index=False)
    annual = pd.DataFrame([
        {"ticker": "TST", "fy": 2023, "period_end": "2023-12-31", "ni": 10.0, "cfo": 14.0, "assets": 100.0},
        {"ticker": "TST", "fy": 2024, "period_end": "2024-12-31", "ni": 12.0, "cfo": 13.0, "assets": 100.0},
        {"ticker": "TST", "fy": 2025, "period_end": "2025-12-31", "ni": 18.0, "cfo": 10.0, "assets": 100.0},
    ])
    annual.to_parquet(q_dir / "statements.parquet", index=False)
    if cik is not None:
        pd.DataFrame({"cik": [cik]}, index=["TST"]).to_parquet(q_dir / "fundamentals.parquet")


def _write_issuer_master(root: Path, rows: list[dict]) -> None:
    target = root / "data" / "reference" / "issuer_master.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(target, index=False)


def test_compose_state_carries_entity_id_only_from_issuer_master(tmp_path: Path):
    """I1: entity_id is JOINED from issuer_master by exact CIK, never minted."""
    import scripts.build_fundamental_forensics as bff

    # (a) an authority row matching TST's panel CIK binds that row's issuer id.
    _write_workbench_panel(tmp_path, cik=1234)
    _write_issuer_master(
        tmp_path, [{"issuer_id": "ISS:US-XNAS-TST", "cik": "0000001234", "legal_name": "Test"}]
    )
    state = compose_state(tmp_path, generated_at=GEN_AT)
    company = state["companies"]["TST"]
    assert company["entity_id"] == "ISS:US-XNAS-TST"
    assert company["entity_id_reason"] == "issuer_master_row"

    # (b) no master file at all: every company null with the unavailable reason.
    bare = tmp_path / "bare"
    _write_workbench_panel(bare, cik=1234)
    bare_state = compose_state(bare, generated_at=GEN_AT)
    assert bare_state["companies"]["TST"]["entity_id"] is None
    assert bare_state["companies"]["TST"]["entity_id_reason"] == "issuer_master_unavailable"
    assert "ISS:" not in json.dumps(bare_state["companies"]["TST"])

    # (c) a master row absent for the panel CIK: null + the absent-row reason,
    # and no issuer id substring is synthesized anywhere in the companies.
    other = tmp_path / "other"
    _write_workbench_panel(other, cik=1234)
    _write_issuer_master(other, [{"issuer_id": "ISS:US-XNYS-OTH", "cik": "0000999999"}])
    other_state = compose_state(other, generated_at=GEN_AT)
    assert other_state["companies"]["TST"]["entity_id"] is None
    assert other_state["companies"]["TST"]["entity_id_reason"] == "issuer_master_row_absent_for_cik"
    assert "ISS:" not in json.dumps(other_state["companies"])

    # ambiguous authority (two issuer ids for one CIK) stays null, not a pick.
    amb = tmp_path / "amb"
    _write_workbench_panel(amb, cik=1234)
    _write_issuer_master(amb, [
        {"issuer_id": "ISS:US-XNAS-TST", "cik": "0000001234"},
        {"issuer_id": "ISS:US-XNYS-TST", "cik": "0000001234"},
    ])
    amb_state = compose_state(amb, generated_at=GEN_AT)
    assert amb_state["companies"]["TST"]["entity_id"] is None
    assert amb_state["companies"]["TST"]["entity_id_reason"] == "issuer_master_ambiguous_for_cik"

    # no CIK in the panel: the reason names the panel, not the master.
    nocik = tmp_path / "nocik"
    _write_workbench_panel(nocik)
    _write_issuer_master(nocik, [{"issuer_id": "ISS:US-XNAS-TST", "cik": "0000001234"}])
    nocik_state = compose_state(nocik, generated_at=GEN_AT)
    assert nocik_state["companies"]["TST"]["entity_id"] is None
    assert nocik_state["companies"]["TST"]["entity_id_reason"] == "cik_absent_in_panel"

    # no ticker→issuer-id path exists anywhere in the builder source.
    assert "ISS:" not in Path(bff.__file__).read_text(encoding="utf-8")


def test_state_periods_are_query_legal_or_explicit_null(tmp_path: Path):
    """I2: {kind,start,end,label} on every period; a missing start is an explicit null."""
    _write_workbench_panel(
        tmp_path,
        period_start_by_year={2024: "2024-04-01", 2025: None, 2026: "2026-03-29"},
    )
    state = compose_state(tmp_path, generated_at=GEN_AT)
    periods = state["companies"]["TST"]["periods"]
    assert periods
    saw_start = saw_null = False
    for period in periods:
        assert period["kind"] == "duration"
        assert isinstance(period["end"], str) and period["end"]
        assert period["label"] == f"FY{period['fiscal_year']} Q{period['fiscal_quarter']}"
        assert period["start"] != ""  # never an empty placeholder
        if period["start"] is None:
            assert period["period_start_basis"] == "absent_in_projection"
            saw_null = True
        else:
            assert isinstance(period["start"], str) and len(period["start"]) == 10
            assert period["period_start_basis"] == "companyfacts_duration_start"
            saw_start = True
        # the four-key projection is exactly a lawful query period payload.
        assert {key: period[key] for key in ("kind", "start", "end", "label")} == {
            "kind": "duration",
            "start": period["start"],
            "end": period["period_end"],
            "label": f"FY{period['fiscal_year']} Q{period['fiscal_quarter']}",
        }
    assert saw_start and saw_null


def test_state_findings_carry_explicit_occurrence_absence(tmp_path: Path):
    """I4: occurrence_id/source_span are explicit JSON nulls with a basis, never fabricated."""
    _write_workbench_panel(tmp_path)
    state = compose_state(tmp_path, generated_at=GEN_AT)
    encoded = json.dumps(state["companies"]["TST"])
    findings = state["companies"]["TST"]["findings"]
    assert findings, "the panel fixture must trigger at least one finding"
    for finding in findings:
        assert finding["occurrence_id"] is None
        assert finding["source_span"] is None
        assert finding["occurrence_basis"] == "panel_projection_not_occurrence_bound"
    assert '"source_span": [' not in encoded
    assert '"occurrence_id": "null"' not in encoded  # never the string "null"


def test_state_payload_peer_cohort_envelope(tmp_path: Path, monkeypatch):
    """I5: the payload envelope, the imported policy echo, and the byte budget."""
    import base64
    import random

    import scripts.build_fundamental_forensics as bff

    _write_workbench_panel(tmp_path)
    state = compose_state(tmp_path, generated_at=GEN_AT)
    payload = state["payload"]
    assert payload["schema"] == "fundamental_forensics_state_payload.v1"
    # this root carries no coverage contract: a typed absence, never a silent null
    assert payload["peer_cohort"] is None
    assert payload["peer_cohort_reason"] == "production_dataset_absent"
    lowered = json.dumps(state).lower()
    assert '"rank"' not in lowered
    assert '"fraud"' not in lowered

    # injected table: to_dict() passes through key-for-key plus the policy echo
    probe = CohortDefinition(cohort_id="", anchor_issuer_id="", members=(), metric_ids=())
    assert (probe.alignment_mode, probe.period_tolerance_days, probe.min_n) == ("exclude", 45, 3)
    injected = {
        "contract_id": "synthetic_v1",
        "policy": {
            "alignment_mode": probe.alignment_mode,
            "period_tolerance_days": probe.period_tolerance_days,
            "min_n": probe.min_n,
        },
        "tables": [{
            "cohort_id": "synthetic_v1:ISS:US-XNAS-TST",
            "members_n": 1,
            "members": [],
            "emissions": [{
                "metric_id": "revenue",
                "emission_state": "ranked",
                "eligible_n": 1,
                "rows": [{"issuer_id": "ISS:US-XNAS-TST", "metric_id": "revenue",
                          "value": "101", "period_end": "2026-06-30",
                          "period_label": "2026-06-30", "shifted": False}],
                "ranks": {"ISS:US-XNAS-TST": 1},
                "percentiles": {"ISS:US-XNAS-TST": "0.0000"},
                "mean": "101",
            }],
            "exclusions": [],
            "authority": {"class": "context_only", "display_only": True},
            "anchor_issuer_id": "ISS:US-XNAS-TST",
        }],
        "member_exclusions": [],
    }
    monkeypatch.setattr(bff, "_compose_peer_cohort", lambda root, index: (injected, None))
    carried = compose_state(tmp_path, generated_at=GEN_AT)
    assert carried["payload"]["peer_cohort"] == injected
    assert carried["payload"]["peer_cohort_reason"] is None
    assert '"ranks"' in json.dumps(carried["payload"])
    # the carried state remains a lawful transport document end to end
    _write_state_atomic(tmp_path / "state.json.gz", carried)
    lowered = json.dumps(carried).lower()
    assert '"rank"' not in lowered
    assert '"fraud"' not in lowered

    # an over-budget payload is dropped whole with the typed reason — never truncated
    noise = base64.b64encode(random.Random(0).randbytes(96 * 1024)).decode("ascii")
    oversized = dict(injected)
    oversized["tables"] = [{"rows": [{"value": noise}]}]
    monkeypatch.setattr(bff, "_compose_peer_cohort", lambda root, index: (oversized, None))
    monkeypatch.setattr(bff, "MAX_COMPRESSED_BYTES", 2048)
    dropped = compose_state(tmp_path, generated_at=GEN_AT)
    assert dropped["payload"]["peer_cohort"] is None
    assert dropped["payload"]["peer_cohort_reason"] == "state_byte_budget_exceeded"
    assert noise not in json.dumps(dropped)

    monkeypatch.setattr(bff, "MAX_COMPRESSED_BYTES", 5 * 1024 * 1024)
    monkeypatch.setattr(bff, "MAX_DECOMPRESSED_BYTES", 512)
    dropped_raw = compose_state(tmp_path, generated_at=GEN_AT)
    assert dropped_raw["payload"]["peer_cohort"] is None
    assert dropped_raw["payload"]["peer_cohort_reason"] == "state_byte_budget_exceeded"


def test_public_summary_projection_emits_only_the_two_free_counts():
    """A count names nobody; anything that could name somebody must not survive."""
    projected = public_summary_projection({
        "companies": 1240,
        "findings": 3417,
        "high": 88,
        "latest_filing": "2026-08-05",
        "detector_coverage": {"accrual": 12},
        "top_symbol": "SMCI",
        "companies_list": ["AAPL", "SMCI"],
    })
    assert projected == {"companies": 1240, "findings": 3417}


def test_anonymous_preview_omits_the_count_fact_when_no_summary_exists(tmp_path: Path):
    """A fresh clone, a CI checkout and the first build all lack the projection."""
    html = _render_into(tmp_path, Path(__file__).resolve().parents[1])
    assert 'class="ff-gate-facts"' in html
    assert "Last pass" not in html
    assert "companies read" not in html
    # The absent fact must be omitted whole, never printed as a zero.
    assert "0 companies read" not in html


def test_anonymous_preview_prints_counts_supplied_by_the_build(tmp_path: Path):
    html = _render_into(tmp_path, Path(__file__).resolve().parents[1], summary={"companies": 1240, "findings": 3417})
    assert "1,240 companies read, 3,417 changes ranked for a look" in html
    assert "读取 1,240 家公司，排出 3,417 项值得一看的变化" in html


def test_build_site_compat_hook_prints_the_same_counts_as_the_forensics_build(tmp_path: Path):
    """render_from_state() re-renders this shell moments after the nightly
    forensics build (daily.yml: forensics, then build_site) and again on every
    render.yml lane that never composes state. A count carried only in-process
    would be erased there within seconds and would never exist on a render-lane
    rebuild, so the fact has to survive a render that is handed no summary."""
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "templates").symlink_to(root / "templates")
    _write_public_summary(tmp_path, {"companies": 1240, "findings": 3417, "top_symbol": "SMCI"})

    html = render_shell(tmp_path).read_text(encoding="utf-8")  # no state_summary — the compat-hook path

    assert "1,240 companies read, 3,417 changes ranked for a look" in html
    assert "SMCI" not in html


def test_unreadable_or_foreign_public_summary_degrades_to_no_fact(tmp_path: Path):
    path = tmp_path / PUBLIC_SUMMARY_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    unusable = (
        "{ not json",
        json.dumps({"companies": 5, "findings": 5}),           # no schema
        json.dumps({"schema": "other/v9"}),                     # foreign schema
        json.dumps({"schema": SCHEMA_PUBLIC, "companies": 5, "findings": 5}),  # unstamped
    )
    for payload in unusable:
        path.write_text(payload, encoding="utf-8")
        assert read_public_summary(tmp_path) == {}
    assert read_public_summary(tmp_path / "nowhere") == {}


def test_public_summary_stops_being_published_once_it_outlives_its_build(tmp_path: Path):
    """daily.yml's run_py annotates a failed builder but does NOT exit non-zero,
    so a broken forensics build leaves the nightly green while build_site keeps
    re-rendering this page from the last good file. Without a bound the counts
    would freeze and stay published forever — the exact stale-stat defect the
    preview shipped without totals to avoid."""
    built = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _write_public_summary(tmp_path, {"companies": 1240, "findings": 3417}, generated_at=built.isoformat())

    fresh = built + timedelta(days=PUBLIC_SUMMARY_MAX_AGE_DAYS)
    assert read_public_summary(tmp_path, now=fresh) == {"companies": 1240, "findings": 3417}

    stale = built + timedelta(days=PUBLIC_SUMMARY_MAX_AGE_DAYS + 1)
    assert read_public_summary(tmp_path, now=stale) == {}

    # ...and the page omits the fact whole rather than printing frozen counts.
    (tmp_path / "templates").symlink_to(Path(__file__).resolve().parents[1] / "templates")
    import scripts.build_fundamental_forensics as bff
    real_read = bff.read_public_summary
    try:
        bff.read_public_summary = lambda root, **kw: real_read(root, now=stale)
        html = bff.render_shell(tmp_path).read_text(encoding="utf-8")
    finally:
        bff.read_public_summary = real_read
    assert "companies read" not in html
    assert "1,240" not in html
