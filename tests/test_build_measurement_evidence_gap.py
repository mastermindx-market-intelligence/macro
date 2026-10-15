"""tests/test_build_measurement_evidence_gap.py — Evidence-Gap panel builder tests (PR-A1).

Tests:
1. build_grading_closure: correct starvation logic on synthetic fixture.
2. build_grading_closure: absent-file-safe (returns {available: False}).
3. build_trial_budgets: groupby family, latest_ts, n counts.
4. build_trial_budgets: absent-file-safe.
5. build_rule_experiments: collapses lifecycle rows; pooled_sum correct.
6. build_rule_experiments: absent-file-safe.
7. build_qledger_reliability: correct row extraction and §0.5.8 caveat present.
8. build_qledger_reliability: absent-file-safe.
9. No "validated" / "已验证" in any new function output (BC-2).
10. build_thesis_monitor_broken: BROKEN-only rows, index-paired fired criteria.
11. build_thesis_monitor_broken: absent-file-safe (returns {available: False}).
12. build_thesis_monitor_broken: non-list "monitored" or a non-object file is
    unavailable; non-list criteria/statuses and null fields degrade, never raise.
13. measurement.html.j2: eg-thesis-broken prints the BROKEN thesis, escaped.
14. measurement.html.j2: eg-thesis-broken hidden when unavailable / key absent.

House rules:
- Synthetic fixture files only — no real data writes.
- No git operations; no parquet appends.
- Pure stdlib + json; no scipy, sklearn, statsmodels.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Import the functions under test.  We patch the module-level path constants
# using monkeypatch so each test can supply its own synthetic file.
import scripts.build_measurement as bm  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1 & 2. build_grading_closure
# ---------------------------------------------------------------------------

GRADING_CLOSURE_FIXTURE = {
    "schema": "grading_closure.v1",
    "generated_at": "2026-07-06T04:38:22Z",
    "n_ledgers": 4,
    "n_closed": 1,
    "n_grader_starved": 2,
    "n_log_only": 1,
    "ledgers": [
        # CLOSED: grader wired, n_graded > 0
        {
            "key": "ledger_closed",
            "path": "data/x/closed.parquet",
            "storage": "present",
            "grader_wired": "Y:scripts/grade_x.py",
            "n_logged": 100,
            "n_graded": 95,
            "last_graded_at": "2026-07-05T10:00:00Z",
            "verdict": "CLOSED",
        },
        # TIME-STARVED: grader wired, n_graded == 0
        {
            "key": "ledger_time_starved",
            "path": "data/x/time.parquet",
            "storage": "present",
            "grader_wired": "Y:engine/y.py",
            "n_logged": 5,
            "n_graded": 0,
            "last_graded_at": None,
            "verdict": "GRADER-STARVED",
        },
        # BUILD-STARVED: grader NOT wired, n_graded == 0
        {
            "key": "ledger_build_starved",
            "path": "data/x/build.parquet",
            "storage": "present",
            "grader_wired": "N",
            "n_logged": 26,
            "n_graded": 0,
            "last_graded_at": None,
            "verdict": "LOG-ONLY",
        },
        # Another TIME-STARVED with a known maturity note
        {
            "key": "oracle_forward_ledger",
            "path": "data/oracle/forward_ledger.jsonl",
            "storage": "present",
            "grader_wired": "Y:scripts/oracle_nightly.py",
            "n_logged": 173,
            "n_graded": 0,
            "last_graded_at": None,
            "verdict": "GRADER-STARVED",
        },
    ],
}


def test_grading_closure_starvation_logic(monkeypatch, tmp_path):
    fixture_path = tmp_path / "governance" / "grading_closure.json"
    _write_json(fixture_path, GRADING_CLOSURE_FIXTURE)
    monkeypatch.setattr(bm, "GRADING_CLOSURE_PATH", fixture_path)

    result = bm.build_grading_closure()

    assert result["available"] is True
    assert result["n_ledgers"] == 4

    rows_by_key = {r["key"]: r for r in result["rows"]}

    # CLOSED ledger
    closed = rows_by_key["ledger_closed"]
    assert closed["starvation_type"] == "closed"
    assert "closed" in closed["starvation"]

    # TIME-STARVED ledger (grader wired, n_graded=0)
    time_row = rows_by_key["ledger_time_starved"]
    assert time_row["starvation_type"] == "time"
    assert "time-starved" in time_row["starvation"].lower()

    # BUILD-STARVED ledger (grader_wired == 'N')
    build_row = rows_by_key["ledger_build_starved"]
    assert build_row["starvation_type"] == "build"
    assert "needs grader" in build_row["starvation"].lower()

    # oracle_forward_ledger — TIME-STARVED with maturity note from _MATURITY_NOTES
    oracle_row = rows_by_key["oracle_forward_ledger"]
    assert oracle_row["starvation_type"] == "time"
    assert "2026-07-30" in oracle_row["starvation"]


def test_grading_closure_absent_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "GRADING_CLOSURE_PATH", tmp_path / "does_not_exist.json")
    result = bm.build_grading_closure()
    assert result["available"] is False


# ---------------------------------------------------------------------------
# 3 & 4. build_trial_budgets
# ---------------------------------------------------------------------------

TRIAL_LEDGER_ROWS = [
    {"ts": "2026-06-21T10:36:05.703638+00:00", "family": "incremental_ic:mom_12_1", "config_hash": "aaa"},
    {"ts": "2026-06-22T10:36:05.703638+00:00", "family": "incremental_ic:mom_12_1", "config_hash": "bbb"},
    {"ts": "2026-06-21T10:36:07.148583+00:00", "family": "incremental_ic:near_52w_high", "config_hash": "ccc"},
    {"ts": "2026-07-01T10:00:00+00:00", "family": "replay", "config_hash": "ddd"},
]


def test_trial_budgets_groupby(monkeypatch, tmp_path):
    fixture_path = tmp_path / "trial_ledger.jsonl"
    _write_jsonl(fixture_path, TRIAL_LEDGER_ROWS)
    monkeypatch.setattr(bm, "TRIAL_LEDGER_PATH", fixture_path)

    result = bm.build_trial_budgets()

    assert result["available"] is True
    assert result["n_total"] == 4
    assert result["n_families"] == 3

    rows_by_family = {r["family"]: r for r in result["rows"]}

    mom_row = rows_by_family["incremental_ic:mom_12_1"]
    assert mom_row["n_rows"] == 2
    # Latest ts should be the later date
    assert mom_row["latest_ts"] == "2026-06-22T10:36:05.703638+00:00"

    high_row = rows_by_family["incremental_ic:near_52w_high"]
    assert high_row["n_rows"] == 1

    replay_row = rows_by_family["replay"]
    assert replay_row["n_rows"] == 1


def test_trial_budgets_absent_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "TRIAL_LEDGER_PATH", tmp_path / "missing.jsonl")
    result = bm.build_trial_budgets()
    assert result["available"] is False


# ---------------------------------------------------------------------------
# 5 & 6. build_rule_experiments
# ---------------------------------------------------------------------------

REGISTRY_ROWS = [
    # First registration
    {
        "exp_id": "exp_alpha",
        "registered_at": "2026-07-06T05:31:35Z",
        "question": "Does waiting 5 bars reduce regret? " + "x" * 250,  # long question
        "declared_budget": 10,
        "status": "registered",
    },
    # Status update for same exp_id
    {
        "exp_id": "exp_alpha",
        "registered_at": "2026-07-06T05:31:35Z",
        "status_updated_at": "2026-07-06T06:00:00Z",
        "status": "executed",
        "run_at": "2026-07-06T05:59:00Z",
    },
    # Another experiment
    {
        "exp_id": "exp_beta",
        "registered_at": "2026-07-06T07:00:00Z",
        "question": "Short question",
        "declared_budget": 6,
        "status": "registered",
    },
]


def test_rule_experiments_collapses_lifecycle(monkeypatch, tmp_path):
    fixture_path = tmp_path / "rule_experiments" / "registry.jsonl"
    _write_jsonl(fixture_path, REGISTRY_ROWS)
    monkeypatch.setattr(bm, "RULE_EXPERIMENTS_PATH", fixture_path)

    result = bm.build_rule_experiments()

    assert result["available"] is True
    # Only 2 unique exp_ids even though 3 rows
    assert result["n_experiments"] == 2
    # Pooled SUM = 10 + 6 = 16
    assert result["pooled_declared_budget_sum"] == 16

    rows_by_id = {r["exp_id"]: r for r in result["rows"]}

    # Latest status for exp_alpha should be 'executed'
    assert rows_by_id["exp_alpha"]["status"] == "executed"
    # Question truncated at 200 chars + "…"
    q = rows_by_id["exp_alpha"]["question"]
    assert len(q) <= 201  # 200 + "…"
    assert q.endswith("…")

    # exp_beta: short question unchanged
    assert rows_by_id["exp_beta"]["question"] == "Short question"
    assert rows_by_id["exp_beta"]["declared_budget"] == 6


def test_rule_experiments_absent_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "RULE_EXPERIMENTS_PATH", tmp_path / "missing.jsonl")
    result = bm.build_rule_experiments()
    assert result["available"] is False


# ---------------------------------------------------------------------------
# 7 & 8. build_qledger_reliability
# ---------------------------------------------------------------------------

TRACK_RECORD_FIXTURE = {
    "generated_at": "2026-07-05T11:12:30Z",
    "grade_horizons": [5, 21, 63],
    "graded_min_dates": 25,
    "by_desk": {},
    "by_family": {
        "altdata": {
            "5": {
                "n_obs": 94,
                "n_dates": 5,
                "hit_rate": 0.56383,
                "excess_mean": 0.004928,
                "wilson_ci_low": 0.463027,
                "state": "ACCRUING",
            }
        },
        "radar": {
            "5": {
                "n_obs": 1014,
                "n_dates": 7,
                "hit_rate": 0.540434,
                "excess_mean": 0.008928,
                "wilson_ci_low": 0.509664,
                "state": "ACCRUING",
            }
        },
        "policy": {
            "5": {
                "n_obs": 7,
                "n_dates": 2,
                "hit_rate": None,
                "excess_mean": None,
                "wilson_ci_low": None,
                "state": "ACCRUING",
            }
        },
    },
}


def test_qledger_reliability_rows(monkeypatch, tmp_path):
    fixture_path = tmp_path / "qledger" / "track_record.json"
    _write_json(fixture_path, TRACK_RECORD_FIXTURE)
    monkeypatch.setattr(bm, "QLEDGER_TRACK_RECORD_PATH", fixture_path)

    result = bm.build_qledger_reliability()

    assert result["available"] is True
    assert result["graded_min_dates"] == 25
    assert result["max_n_dates"] == 7  # radar has n_dates=7
    assert result["n_families"] == 3
    assert len(result["rows"]) == 3

    rows_by_fam = {r["family"]: r for r in result["rows"]}

    altdata_row = rows_by_fam["altdata"]
    assert altdata_row["n_obs"] == 94
    assert altdata_row["n_dates"] == 5
    assert altdata_row["hit_rate_pct"] == "56.4%"
    assert altdata_row["wilson_ci_low_str"] == "0.4630"
    # n_dates_note present for §0.5.8
    assert "5" in altdata_row["n_dates_note"]
    assert "25" in altdata_row["n_dates_note"]

    # Policy has null hit_rate
    policy_row = rows_by_fam["policy"]
    assert policy_row["hit_rate_pct"] == "—"
    assert policy_row["wilson_ci_low_str"] == "—"


def test_qledger_reliability_caveat_present(monkeypatch, tmp_path):
    """§0.5.8: the CI caveat must disclose that n_obs is not independent of n_dates."""
    fixture_path = tmp_path / "qledger" / "track_record.json"
    _write_json(fixture_path, TRACK_RECORD_FIXTURE)
    monkeypatch.setattr(bm, "QLEDGER_TRACK_RECORD_PATH", fixture_path)

    result = bm.build_qledger_reliability()

    caveat_en = result["ci_caveat_en"]
    # The disclosure requirement is the DEPENDENCE between the raw and clustered
    # counts, not one particular synonym for it — the wording moved from
    # "overlapping" to "correlated", which pinned this assertion red while the
    # substance stayed intact (and the suite runs in no workflow, so nothing saw it).
    assert any(w in caveat_en.lower() for w in ("overlapping", "correlated", "clustered")), (
        f"caveat must name the n_obs/n_dates dependence: {caveat_en!r}"
    )
    assert "n_dates" in caveat_en
    assert "n_obs" in caveat_en

    caveat_zh = result["ci_caveat_zh"]
    assert "n_dates" in caveat_zh
    assert "n_obs" in caveat_zh


def test_qledger_reliability_absent_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "QLEDGER_TRACK_RECORD_PATH", tmp_path / "missing.json")
    result = bm.build_qledger_reliability()
    assert result["available"] is False


# ---------------------------------------------------------------------------
# 9. BC-2: no "validated" / "已验证" in any new function output
# ---------------------------------------------------------------------------

def test_no_validated_in_output(monkeypatch, tmp_path):
    """None of the new functions may produce the word 'validated' (BC-2 / CI-enforced)."""
    # Grading closure
    fixture_path = tmp_path / "governance" / "grading_closure.json"
    _write_json(fixture_path, GRADING_CLOSURE_FIXTURE)
    monkeypatch.setattr(bm, "GRADING_CLOSURE_PATH", fixture_path)
    gc = bm.build_grading_closure()
    gc_text = json.dumps(gc).lower()
    assert "validated" not in gc_text, "build_grading_closure output contains 'validated'"

    # Trial budgets
    tl_path = tmp_path / "trial_ledger.jsonl"
    _write_jsonl(tl_path, TRIAL_LEDGER_ROWS)
    monkeypatch.setattr(bm, "TRIAL_LEDGER_PATH", tl_path)
    tb = bm.build_trial_budgets()
    tb_text = json.dumps(tb).lower()
    assert "validated" not in tb_text, "build_trial_budgets output contains 'validated'"

    # Rule experiments
    re_path = tmp_path / "rule_experiments" / "registry.jsonl"
    _write_jsonl(re_path, REGISTRY_ROWS)
    monkeypatch.setattr(bm, "RULE_EXPERIMENTS_PATH", re_path)
    re_out = bm.build_rule_experiments()
    re_text = json.dumps(re_out).lower()
    assert "validated" not in re_text, "build_rule_experiments output contains 'validated'"

    # qledger reliability
    ql_path = tmp_path / "qledger" / "track_record.json"
    _write_json(ql_path, TRACK_RECORD_FIXTURE)
    monkeypatch.setattr(bm, "QLEDGER_TRACK_RECORD_PATH", ql_path)
    ql = bm.build_qledger_reliability()
    ql_text = json.dumps(ql).lower()
    assert "validated" not in ql_text, "build_qledger_reliability output contains 'validated'"


# ---------------------------------------------------------------------------
# 10-12. build_thesis_monitor_broken (Calibration Lab — name the BROKEN theses)
# ---------------------------------------------------------------------------

THESIS_MONITOR_FIXTURE = {
    "schema": "thesis_monitor.v1",
    "asof": "2026-01-01",
    "n_open": 3,
    "n_broken": 1,
    "n_weakening": 1,
    "monitored": [
        {
            "theme": "fixture_alpha",
            "source": "deterministic",
            "status": "BROKEN",
            "opened": "2025-12-01",
            "stage_at_open": "PRECIPICE",
            "kill_criteria": [
                {"kind": "k_first", "detail": "first criterion detail"},
                {"kind": "k_second", "detail": "second criterion detail"},
            ],
            "criterion_statuses": ["WEAKENING", "BROKEN"],
        },
        {
            "theme": "fixture_beta",
            "source": "deterministic",
            "status": "WEAKENING",
            "opened": "2025-12-02",
            "stage_at_open": "BROADENING",
            "kill_criteria": [{"kind": "k_first", "detail": "beta first"}],
            "criterion_statuses": ["WEAKENING"],
        },
        {
            "theme": "fixture_gamma",
            "source": "deterministic",
            "status": "INTACT",
            "opened": "2025-12-03",
            "stage_at_open": "PRECIPICE",
            "kill_criteria": [{"kind": "k_first", "detail": "gamma first"}],
            "criterion_statuses": ["INTACT"],
        },
    ],
}


def test_thesis_monitor_broken_rows_from_fixture(monkeypatch, tmp_path):
    """Only status==BROKEN rows appear; fired pairs by index with kill_criteria."""
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, THESIS_MONITOR_FIXTURE)
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)

    result = bm.build_thesis_monitor_broken()

    assert result["available"] is True
    assert result["asof"] == "2026-01-01"
    # counts are passed through from the file — never recomputed here
    assert result["n_broken"] == 1
    assert result["n_weakening"] == 1

    # file order preserved, BROKEN-only
    assert [r["theme"] for r in result["rows"]] == ["fixture_alpha"]
    alpha = result["rows"][0]
    assert alpha["opened"] == "2025-12-01"
    assert alpha["stage_at_open"] == "PRECIPICE"
    # the SECOND criterion is the BROKEN one — not the first, not both
    assert alpha["fired"] == [{"kind": "k_second", "detail": "second criterion detail"}]


def test_thesis_monitor_absent_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        bm, "THESIS_MONITOR_PATH", tmp_path / "foresight" / "thesis_monitor.json"
    )
    result = bm.build_thesis_monitor_broken()
    assert result["available"] is False


def test_thesis_monitor_non_list_monitored_is_unavailable(monkeypatch, tmp_path):
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {"asof": "2026-01-01", "monitored": {}})
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    result = bm.build_thesis_monitor_broken()
    assert result["available"] is False


def test_thesis_monitor_non_object_file_is_unavailable(monkeypatch, tmp_path):
    """A top-level list has no .get(); it must degrade, not crash run()."""
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, [{"status": "BROKEN"}])
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    result = bm.build_thesis_monitor_broken()
    assert result["available"] is False


def test_thesis_monitor_llm_only_row_shows_its_inputs(monkeypatch, tmp_path):
    """An LLM-only thesis is shaped like the producer's standalone row
    (engine/thesis_monitor.py): opened_asof, text kill_criteria, no
    criterion_statuses.  It still names when it opened and what it was
    judged on, instead of rendering as an empty row."""
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {
        "asof": "2026-01-01", "n_broken": 1, "n_weakening": 0,
        "monitored": [{
            "theme": "fixture_llm", "source": "llm", "status": "BROKEN",
            "heat_at_open": 0.196, "heat_now": 0.157, "n_surfaces_now": 1,
            "physical_now": False, "opened_asof": "2025-12-05",
            "kill_criteria": ["a text criterion", "another text criterion"],
        }],
    })
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    rows = bm.build_thesis_monitor_broken()["rows"]
    assert rows == [{
        "theme": "fixture_llm", "opened": "2025-12-05", "stage_at_open": "",
        "fired": [{"kind": "llm_inputs",
                   "detail": "heat 0.196 → 0.157 · 1 surface(s) now · physical now: no"}],
    }]
    html = _render_measurement(thesis_monitor_broken=bm.build_thesis_monitor_broken())
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "2025-12-05" in panel and "llm_inputs" in panel
    assert '<td class="eg-mono">—</td>' in panel  # no stage at open


def test_thesis_monitor_llm_row_does_not_claim_heat_decay(monkeypatch, tmp_path):
    """The producer breaks an LLM thesis on lost physical confirmation, too few
    surfaces OR a heat drop, and does not record which.  Steady heat with
    physical confirmation lost must not be labelled as heat decay."""
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {
        "asof": "2026-01-01", "n_broken": 1, "n_weakening": 0,
        "monitored": [{
            "theme": "fixture_llm_phys", "source": "llm", "status": "BROKEN",
            "heat_at_open": 0.2, "heat_now": 0.2, "n_surfaces_now": 3,
            "physical_now": False, "opened_asof": "2025-12-05",
            "kill_criteria": ["a text criterion"],
        }],
    })
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    (fired,) = bm.build_thesis_monitor_broken()["rows"][0]["fired"]
    assert fired["kind"] == "llm_inputs"
    assert "decay" not in fired["kind"]
    assert fired["detail"] == "heat 0.2 → 0.2 · 3 surface(s) now · physical now: no"


def test_thesis_monitor_llm_row_without_inputs_shows_dashes(monkeypatch, tmp_path):
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {
        "asof": "2026-01-01", "n_broken": 1, "n_weakening": 0,
        "monitored": [{"theme": "fixture_llm_bare", "source": "llm", "status": "BROKEN"}],
    })
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    (fired,) = bm.build_thesis_monitor_broken()["rows"][0]["fired"]
    assert fired["detail"] == "heat — → — · — surface(s) now · physical now: —"


def test_thesis_monitor_malformed_criteria_degrade(monkeypatch, tmp_path):
    """Non-list kill_criteria / criterion_statuses must not raise out of run()."""
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {
        "asof": "2026-01-01", "n_broken": 2, "n_weakening": 0,
        "monitored": [
            {"theme": "fixture_int_criteria", "status": "BROKEN",
             "kill_criteria": 3, "criterion_statuses": ["BROKEN"]},
            {"theme": "fixture_int_statuses", "status": "BROKEN",
             "kill_criteria": [{"kind": "k", "detail": "d"}], "criterion_statuses": 5},
        ],
    })
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    rows = bm.build_thesis_monitor_broken()["rows"]
    assert [(r["theme"], r["fired"]) for r in rows] == [
        ("fixture_int_criteria", []), ("fixture_int_statuses", []),
    ]


def test_thesis_monitor_null_fields_never_render_none(monkeypatch, tmp_path):
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {
        "asof": None, "n_broken": None, "n_weakening": None,
        "monitored": [{"theme": None, "status": "BROKEN", "stage_at_open": None,
                       "kill_criteria": [], "criterion_statuses": []}],
    })
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    result = bm.build_thesis_monitor_broken()
    assert result["rows"][0]["stage_at_open"] == ""
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "None" not in panel


# ---------------------------------------------------------------------------
# 13-14. measurement.html.j2 — eg-thesis-broken subpanel (escaped, hidden)
# ---------------------------------------------------------------------------

def _render_measurement(**over) -> str:
    """Render measurement.html.j2 with all-artifacts-absent defaults.

    Same absent-state context as tests/test_etf_board_windows_tile.py::_render;
    thesis_monitor_broken is deliberately NOT defaulted there so the "key absent"
    case can be exercised by simply not passing it.
    """
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(REPO / "templates")), autoescape=False)
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:  # noqa: BLE001 — English-only fallback, as the builder does
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)
    ctx = {
        "page_title": "Test", "engines": [], "gate_ledger": [],
        "accruing_experiments": [], "cone_recalibration": {}, "collinearity": {},
        "sync_gauge": {"available": False},
        "provenance": {"epochs": {}, "fingerprint_consistent": True},
        "build_date": "2026-01-01", "generated_at": "2026-01-01T00:00:00Z",
        "n_stamps_grand_total": 0, "truth_ledger": {"available": False},
        "accrual_clocks": [], "prediction_layer": {"available": False},
        "coverage_matrix": {"available": False, "rows": []},
        "grading_closure": {"available": False}, "trial_budgets": {"available": False},
        "rule_experiments": {"available": False},
        "qledger_reliability": {"available": False},
        "seasonality_record": {"available": False, "registered": 0, "graded": 0,
                               "next_close": None},
    }
    ctx.update(over)
    return env.get_template("measurement.html.j2").render(**ctx)


BROKEN_THESIS_CONTEXT = {
    "available": True,
    "asof": "2026-01-01",
    "n_broken": 1,
    "n_weakening": 1,
    "rows": [
        {
            "theme": "fixture_alpha",
            "opened": "2025-12-01",
            "stage_at_open": "PRECIPICE",
            "fired": [{"kind": "k_second", "detail": "<b>x</b>"}],
        },
        {
            "theme": "<script>x</script>",
            "opened": "2025-12-02",
            "stage_at_open": "BROADENING",
            "fired": [],
        },
    ],
}


def test_measurement_template_lists_broken_thesis_escaped():
    html = _render_measurement(thesis_monitor_broken=BROKEN_THESIS_CONTEXT)

    assert 'id="eg-thesis-broken"' in html
    assert "fixture_alpha" in html
    assert "k_second" in html
    # autoescape=False in the builder — producer strings must carry |e
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "<script>x</script>" not in html
    # no real producer theme may leak into a synthetic render
    assert "ai_semiconductors" not in html


def test_measurement_template_hides_broken_block_when_unavailable():
    # rows present but available=False: the guard must still hide the block
    unavailable = dict(BROKEN_THESIS_CONTEXT, available=False)
    assert "eg-thesis-broken" not in _render_measurement(
        thesis_monitor_broken=unavailable
    )
    assert "eg-thesis-broken" not in _render_measurement()
