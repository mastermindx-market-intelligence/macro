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
    surfaces OR a heat drop; a row that carries no broken_reasons record does not
    say which.  Steady heat with physical confirmation lost must not be labelled as heat decay."""
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


# ---------------------------------------------------------------------------
# W17-B-C3 Spec 2: grading-closure "Last graded" column (display-only of
# row.last_graded_at, already copied at scripts/build_measurement.py:1258).
# ---------------------------------------------------------------------------

GRADING_CLOSURE_LAST_GRADED_CONTEXT = {
    "available": True,
    "generated_at": "2026-10-17T00:00:00Z",
    "n_ledgers": 2,
    "n_closed": 1,
    "n_grader_starved": 1,
    "n_log_only": 0,
    "rows": [
        {
            "key": "qledger_claims",
            "path": "data/qledger/claims.jsonl",
            "n_logged": 246813,
            "n_graded": 208167,
            "grader_wired": "True",
            "verdict": "CLOSED",
            "starvation": "closed",
            "starvation_type": "closed",
            "last_graded_at": "2026-10-16T11:32:33.971947+00:00",
        },
        {
            "key": "stub_forward_log",
            "path": "data/governance/stub_forward.jsonl",
            "n_logged": 5,
            "n_graded": 0,
            "grader_wired": "False",
            "verdict": "TIME-STARVED",
            "starvation": "accruing (time-starved)",
            "starvation_type": "time",
            "last_graded_at": None,
        },
    ],
}


def _grading_closure_table(html: str) -> str:
    start = html.index('id="eg-grading-closure"')
    return html[start:html.index("</table>", start)]


def test_grading_closure_last_graded_at_renders():
    html = _render_measurement(
        grading_closure=GRADING_CLOSURE_LAST_GRADED_CONTEXT)
    table = _grading_closure_table(html)
    assert "Last graded" in table            # EN header
    assert "\u6700\u8fd1\u8bc4\u5206" in table  # ZH header 最近评分
    assert "2026-10-16" in table             # date prefix only
    assert "2026-10-16T11:32:33" not in table  # never the raw timestamp
    body = table[table.index("<tbody>"):table.index("</tbody>")]
    row_cells = body.split("<tr>")[1:]
    assert len(row_cells) == 2
    assert "None" not in table and "null" not in table
    assert "2026-10-16" in row_cells[0]      # date lands on the stamped row
    assert "\u2014" in row_cells[1]          # em dash on the null row
    assert "None" not in row_cells[1]


# ---------------------------------------------------------------------------
# W17-B-C3 Spec 5: cone-recalibration "Half-width (days)" stat. Display-only
# of headline.recal_halfwidth_days; skipped entirely when the key is missing.
# ---------------------------------------------------------------------------

CONE_RECAL_HALFWIDTH_CONTEXT = {
    "engines": {
        "sector_cycles": {
            "headline": {
                "recal_multiplier": 8.191,
                "empirical": 0.188,
                "recal_halfwidth_days": 1484.237,
            },
            "forward_only": {"recal_multiplier": 7.657},
            "overdue_fraction": 0.346,
            "epoch": {"basis_version": "price_v1", "zz_version": "zz14_v0"},
        }
    }
}


def test_cone_recal_halfwidth_days_renders():
    html = _render_measurement(
        cone_recalibration=CONE_RECAL_HALFWIDTH_CONTEXT)
    assert "1484.2" in html
    assert "1484.237" not in html  # rounded to one decimal
    assert "Half-width (days)" in html
    assert "\u534a\u5bbd\uff08\u5929\uff09" in html  # ZH 半宽（天）
    assert "8.191" in html  # existing headline stat still renders


def test_cone_recal_halfwidth_stat_skipped_when_key_missing():
    ctx = json.loads(json.dumps(CONE_RECAL_HALFWIDTH_CONTEXT))
    del ctx["engines"]["sector_cycles"]["headline"]["recal_halfwidth_days"]
    html = _render_measurement(cone_recalibration=ctx)
    assert "8.191" in html                    # the card still renders
    assert "Half-width (days)" not in html    # the stat is skipped
    assert "\u534a\u5bbd\uff08\u5929\uff09" not in html
    assert "1484.2" not in html


# ---------------------------------------------------------------------------
# 15. LLM overlay pass-through on BROKEN rows (W17 spec 3) + the INTACT
#     "Still tracked" sibling table (W17 spec 4)
# ---------------------------------------------------------------------------

def _thesis_fixture(monkeypatch, tmp_path, monitored):
    fixture_path = tmp_path / "foresight" / "thesis_monitor.json"
    _write_json(fixture_path, {"schema": "thesis_monitor.v1",
                               "asof": "2026-10-18", "n_open": 11,
                               "n_broken": 1, "n_weakening": 0,
                               "monitored": monitored})
    monkeypatch.setattr(bm, "THESIS_MONITOR_PATH", fixture_path)
    return bm.build_thesis_monitor_broken()


def test_broken_row_llm_overlay_from_committed_shape(monkeypatch, tmp_path):
    """The folded overlay keys ride the BROKEN row; the panel renders them."""
    result = _thesis_fixture(monkeypatch, tmp_path, [{
        "theme": "data_center_power", "source": "deterministic",
        "status": "BROKEN", "opened": "2026-08-02",
        "stage_at_open": "BROADENING (text)",
        "kill_criteria": [{"kind": "cycle_tripwire", "detail": "dd"}],
        "criterion_statuses": ["BROKEN"],
        "llm_status": "INTACT", "llm_heat_at_open": 0.467,
        "llm_heat_now": 0.467,
    }])
    (row,) = result["rows"]
    assert row["llm_status"] == "INTACT"
    assert row["llm_heat_at_open"] == 0.467
    assert row["llm_heat_now"] == 0.467
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "0.467" in panel
    assert "still tracked" in panel
    # the producer never records WHICH LLM condition fired — no cause label
    assert "heat decay" not in panel


def test_overlay_words_null_heat_and_missing_heat_guard(monkeypatch, tmp_path):
    """BROKEN maps to its own EN/ZH word, a null heat renders a dash (never
    "None"), and a row carrying llm_status without both heats gets no clause."""
    base = {"source": "deterministic", "status": "BROKEN",
            "opened": "2026-08-02", "stage_at_open": "BROADENING (text)",
            "kill_criteria": [{"kind": "cycle_tripwire", "detail": "dd"}],
            "criterion_statuses": ["BROKEN"]}
    result = _thesis_fixture(monkeypatch, tmp_path, [
        dict(base, theme="grid_storage", llm_status="BROKEN",
             llm_heat_at_open=0.512, llm_heat_now=None),
        dict(base, theme="optical_links", llm_status="WEAKENING"),
    ])
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "overlay broken · heat" in panel
    assert "叠加 已失效" in panel
    assert "None" not in panel
    assert "0.512 → —" in panel
    assert "overlay weakening" not in panel and "叠加 走弱" not in panel


def test_intact_rows_from_committed_shape(monkeypatch, tmp_path):
    """INTACT rows land in intact_rows (file order); rows stays BROKEN-only."""
    result = _thesis_fixture(monkeypatch, tmp_path, [
        {"theme": "grid_electrification", "source": "deterministic",
         "status": "INTACT", "opened": "2026-07-04",
         "stage_at_open": "BROADENING (text)"},
        {"theme": "nuclear_power", "source": "deterministic",
         "status": "INTACT", "opened": "2026-07-04",
         "stage_at_open": "BROADENING (text)", "llm_status": "BROKEN",
         "llm_heat_at_open": 0.213, "llm_heat_now": 0.169},
        {"theme": "space_satellite", "source": "deterministic",
         "status": "INTACT", "opened": "2026-10-06",
         "stage_at_open": "BROADENING (text)"},
        {"theme": "rare_earth_critical_min", "source": "deterministic",
         "status": "BROKEN", "opened": "2026-06-01",
         "stage_at_open": "PRECIPICE",
         "kill_criteria": [{"kind": "k_b", "detail": "b"}],
         "criterion_statuses": ["BROKEN"]},
    ])
    assert [r["theme"] for r in result["intact_rows"]] == [
        "grid_electrification", "nuclear_power", "space_satellite"]
    assert [r["theme"] for r in result["rows"]] == ["rare_earth_critical_min"]
    grid = result["intact_rows"][0]
    assert grid["opened"] == "2026-07-04"
    assert grid["stage_at_open"] == "BROADENING (text)"
    html = _render_measurement(thesis_monitor_broken=result)
    assert "eg-thesis-intact" in html
    assert "Still tracked" in html
    assert "grid_electrification" in html
    assert "2026-07-04" in html


def test_still_tracked_header_hidden_when_intact_rows_empty():
    """An empty intact_rows list must render no Still tracked header."""
    ctx = dict(BROKEN_THESIS_CONTEXT, intact_rows=[])
    html = _render_measurement(thesis_monitor_broken=ctx)
    assert "eg-thesis-broken" in html
    assert "Still tracked" not in html
    assert "仍在跟踪" not in html


# ---------------------------------------------------------------------------
# 16. W20-L1 — the producer records WHICH AI kill condition fired
#     (broken_reasons / llm_broken_reasons); the reader relays it.
# ---------------------------------------------------------------------------

def test_w20l1_llm_row_names_recorded_reason(monkeypatch, tmp_path):
    """An LLM row carrying broken_reasons names that condition, not its inputs."""
    result = _thesis_fixture(monkeypatch, tmp_path, [{
        "theme": "fixture_med", "source": "llm", "status": "BROKEN",
        "heat_at_open": 0.196, "heat_now": 0.137, "n_surfaces_now": 1,
        "physical_now": False, "opened_asof": "2026-09-30",
        "kill_criteria": ["t"], "broken_reasons": ["below_quorum"],
    }])
    (row,) = result["rows"]
    assert row["fired"] == [{"kind": "below_quorum", "detail": "1 surface(s) now"}]
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "below_quorum — 1 surface(s) now" in panel
    assert "llm_inputs" not in panel
    assert "heat 0.196" not in panel


def test_w20l1_llm_row_all_reasons_keep_producer_order(monkeypatch, tmp_path):
    """Every recorded reason becomes its own fired entry, in list order."""
    result = _thesis_fixture(monkeypatch, tmp_path, [{
        "theme": "fixture_all", "source": "llm", "status": "BROKEN",
        "heat_at_open": 0.5, "heat_now": 0.2, "n_surfaces_now": 1,
        "physical_now": False, "opened_asof": "2026-09-30",
        "kill_criteria": ["t"],
        "broken_reasons": ["physical_lost", "below_quorum", "heat_drop"],
    }])
    (row,) = result["rows"]
    assert row["fired"] == [
        {"kind": "physical_lost", "detail": "physical now: no"},
        {"kind": "below_quorum", "detail": "1 surface(s) now"},
        {"kind": "heat_drop", "detail": "heat 0.5 → 0.2"},
    ]


def test_w20l1_reason_list_degrades_to_inputs(monkeypatch, tmp_path):
    """Empty/string/garbage/unknown broken_reasons degrade without re-judging."""
    inputs = "heat 0.196 → 0.137 · 1 surface(s) now · physical now: no"
    fields = {"source": "llm", "status": "BROKEN", "heat_at_open": 0.196,
              "heat_now": 0.137, "n_surfaces_now": 1, "physical_now": False,
              "opened_asof": "2026-09-30", "kill_criteria": ["t"]}
    result = _thesis_fixture(monkeypatch, tmp_path, [
        dict(fields, theme="r1", broken_reasons=[]),
        dict(fields, theme="r2", broken_reasons="below_quorum"),
        dict(fields, theme="r3", broken_reasons=[None, 7, "", "below_quorum"]),
        dict(fields, theme="r4", broken_reasons=["new_rule"]),
    ])
    rows = result["rows"]
    assert rows[0]["fired"] == [{"kind": "llm_inputs", "detail": inputs}]
    assert rows[1]["fired"] == [{"kind": "llm_inputs", "detail": inputs}]
    assert rows[2]["fired"] == [{"kind": "below_quorum", "detail": "1 surface(s) now"}]
    assert rows[3]["fired"] == [{"kind": "new_rule", "detail": inputs}]


def test_w20l1_overlay_reasons_pass_through_and_render(monkeypatch, tmp_path):
    """llm_broken_reasons rides the deterministic row only when written (as a
    list) and the overlay clause names the fired codes, escaped."""
    base = {"source": "deterministic", "status": "BROKEN",
            "opened": "2026-08-02", "stage_at_open": "BROADENING (text)",
            "kill_criteria": [{"kind": "cycle_tripwire", "detail": "dd"}],
            "criterion_statuses": ["BROKEN"]}
    result = _thesis_fixture(monkeypatch, tmp_path, [
        dict(base, theme="w20l1_o1", llm_status="BROKEN",
             llm_heat_at_open=0.213, llm_heat_now=0.169,
             llm_broken_reasons=["below_quorum"]),
        dict(base, theme="w20l1_o2", llm_status="BROKEN",
             llm_heat_at_open=0.213, llm_heat_now=0.169, llm_broken_reasons="x"),
        dict(base, theme="w20l1_o3", llm_status="INTACT",
             llm_heat_at_open=0.4, llm_heat_now=0.4, llm_broken_reasons=[]),
        dict(base, theme="w20l1_o4", llm_status="BROKEN",
             llm_heat_at_open=0.3, llm_heat_now=0.3,
             llm_broken_reasons=["<b>r</b>"]),
        dict(base, theme="w20l1_o5", llm_status="BROKEN",
             llm_heat_at_open=0.1),
    ])
    assert [r["llm_broken_reasons"] for r in result["rows"][:4]] == [
        ["below_quorum"], [], [], ["<b>r</b>"]]
    assert "llm_broken_reasons" not in result["rows"][4]
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-broken"', 1)[1].split("eg-footnote", 1)[0]
    assert "0.213 → 0.169 · fired: below_quorum" in panel
    assert "· 触发：below_quorum" in panel
    assert panel.count("fired:") == 2  # o1 and o4 only
    # strengthening for m14: o5 lacks llm_heat_now, so only o1..o4 render a
    # clause; a guard missing the 'llm_heat_now' in row check would add o5.
    assert panel.count("overlay ") == 4
    assert "&lt;b&gt;r&lt;/b&gt;" in panel
    assert "<b>r</b>" not in panel


def test_w20l1_intact_row_carries_overlay(monkeypatch, tmp_path):
    """The AI overlay rides INTACT rows too, so disagreement stays visible."""
    result = _thesis_fixture(monkeypatch, tmp_path, [
        {"theme": "grid_electrification", "source": "deterministic",
         "status": "INTACT", "opened": "2026-07-04",
         "stage_at_open": "BROADENING (text)"},
        {"theme": "nuclear_power", "source": "deterministic",
         "status": "INTACT", "opened": "2026-07-04",
         "stage_at_open": "BROADENING (text)", "llm_status": "BROKEN",
         "llm_heat_at_open": 0.213, "llm_heat_now": 0.169,
         "llm_broken_reasons": ["below_quorum"]},
    ])
    keys = ("llm_status", "llm_heat_at_open", "llm_heat_now", "llm_broken_reasons")
    nuclear = result["intact_rows"][1]
    assert nuclear["llm_status"] == "BROKEN"
    assert nuclear["llm_heat_at_open"] == 0.213
    assert nuclear["llm_heat_now"] == 0.169
    assert nuclear["llm_broken_reasons"] == ["below_quorum"]
    assert not any(k in result["intact_rows"][0] for k in keys)
    html = _render_measurement(thesis_monitor_broken=result)
    panel = html.split('id="eg-thesis-intact"', 1)[1].split("</table>", 1)[0]
    assert "AI overlay" in panel and "AI 叠加" in panel
    assert "overlay broken · heat" in panel
    assert "0.213 → 0.169 · fired: below_quorum" in panel
    assert "叠加 已失效" in panel
    (grid_seg,) = [s for s in panel.split("<tr>") if "grid_electrification" in s]
    assert "—" in grid_seg
    assert "overlay" not in grid_seg


def test_w20l1_footnote_and_docstring_name_reasons():
    """The footnote and the reader docstring name the recorded reason codes."""
    html = _render_measurement(thesis_monitor_broken=BROKEN_THESIS_CONTEXT)
    note = html.split('id="eg-thesis-broken"', 1)[1]
    note = note.split("eg-footnote", 1)[1].split("</div>", 1)[0]
    assert "not which one fired" not in note
    assert "不指明具体触发哪一项" not in note
    en, zh = note.split('class="l-zh"')
    for token in ("physical_lost", "below_quorum", "heat_drop", "llm_inputs"):
        assert token in en
        assert token in zh
    doc = bm.build_thesis_monitor_broken.__doc__
    assert "broken_reasons" in doc
    assert "does not\n    record which" not in doc
