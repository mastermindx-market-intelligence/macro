"""S2 v1.1 hardening pins (X2-01..08, A7-F1/F2/F5).

Each test_h1_* pin is written to FAIL at the v1 base except where labelled
as a pure regression pin. Descriptive research only: every authority flag
stays false.
"""
from __future__ import annotations

import copy
import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from run_s2 import (  # noqa: E402
    RETIRED_TOKEN, V1_1_DIR_REL, generate_outputs, multiplicity_sentence,
    verify_seal,
)
from s2_collapse import run_collapse  # noqa: E402
from s2_outcomes import OutcomeEngine  # noqa: E402
from s2_seal import AUTHORITY_FLAGS, refuse_nonfalse_authority  # noqa: E402
from s2_selection import split_tokens  # noqa: E402
from s2_splits import purge_flag  # noqa: E402
from s2_state import compute_state  # noqa: E402
from s2_loaders import GitBlobLoader  # noqa: E402
from s2_seal import GRADE_HORIZONS, PROTOCOLS  # noqa: E402
from s2_clocklaw import session_dates  # noqa: E402
import lib.nyse_calendar as nyse_calendar  # noqa: E402
import lib.hk_calendar as hk_calendar  # noqa: E402

V1_1 = ROOT / V1_1_DIR_REL
V1 = ROOT / "research" / "single_name_intelligence" / "runs" / "s2_event_response"
REG = (ROOT / "research" / "single_name_intelligence" / "protocols"
       / "S0_PROTOCOL_REGISTER.md")
INPUT_REF = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"


def _v1_1_report() -> str:
    path = V1_1 / "REPORT.md"
    if not path.exists():
        pytest.fail("v1.1 REPORT.md missing (FAIL at base: expected)")
    return path.read_text(encoding="utf-8")


def _v1_1_seal() -> dict:
    path = V1_1 / "SEAL_AND_BUDGET.json"
    if not path.exists():
        pytest.fail("v1.1 SEAL_AND_BUDGET.json missing (FAIL at base: expected)")
    return json.loads(path.read_text(encoding="utf-8"))


def _v1_1_results() -> dict:
    out = {}
    for pid in PROTOCOLS:
        path = V1_1 / "results" / f"{pid}.json"
        if not path.exists():
            pytest.fail(f"v1.1 results/{pid}.json missing (FAIL at base: expected)")
        out[pid] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _cell_blocks(report: str) -> list[str]:
    parts = re.split(r"(?=^#{2,3} )", report, flags=re.M)
    return [p for p in parts if p.startswith("### TRAIN")
            or p.startswith("### TUNE") or p.startswith("### QUARANTINE")]


# ---------------------------------------------------------------------------
# X2-01 leak scan before outcomes  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_01_leak_scan_before_outcomes(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple] = []
    orig_scan = OutcomeEngine.info_leak_scan
    orig_excess = OutcomeEngine.episode_excess
    orig_leg = OutcomeEngine.leg_return
    orig_window = OutcomeEngine.resolve_window

    def rec_scan(self, *a, **k):
        calls.append(("scan", None, None))
        return orig_scan(self, *a, **k)

    def rec_excess(self, s_us, h):
        calls.append(("excess", s_us, h))
        return orig_excess(self, s_us, h)

    def rec_leg(self, *a, **k):
        calls.append(("leg_return", a[1] if len(a) > 1 else None, None))
        return orig_leg(self, *a, **k)

    def rec_window(self, s_us, h):
        calls.append(("resolve_window", s_us, h))
        return orig_window(self, s_us, h)

    monkeypatch.setattr(OutcomeEngine, "info_leak_scan", rec_scan)
    monkeypatch.setattr(OutcomeEngine, "episode_excess", rec_excess)
    monkeypatch.setattr(OutcomeEngine, "leg_return", rec_leg)
    monkeypatch.setattr(OutcomeEngine, "resolve_window", rec_window)

    out = tmp_path / "o"
    ledger = tmp_path / "trial_ledger.jsonl"
    generate_outputs(ROOT, INPUT_REF, out, ledger, V1)

    kinds = [c[0] for c in calls]
    assert "scan" in kinds
    first_scan = kinds.index("scan")
    window_kinds = {"excess", "leg_return", "resolve_window"}
    window_idxs = [i for i, k in enumerate(kinds) if k in window_kinds]
    if window_idxs:
        assert first_scan < min(window_idxs)

    p04_tune_dates = set()
    from s2_splits import split_label
    loader = GitBlobLoader(ROOT, INPUT_REF)
    state = compute_state(loader)
    for h in GRADE_HORIZONS:
        for ep in state["membership"]["P04"]["counted"].get(h, []):
            s = date.fromisoformat(ep.opener.s_us)
            if split_label(s) == "TUNE":
                p04_tune_dates.add(s)
    assert p04_tune_dates, "P04 TUNE membership must be non-empty"
    for kind, s_us, h in calls:
        if kind in ("excess", "resolve_window") and s_us in p04_tune_dates:
            raise AssertionError(
                f"window-return call {kind}({s_us}, {h}) for a P04 TUNE episode")

    report = (out / "REPORT.md").read_text(encoding="utf-8")
    for h in GRADE_HORIZONS:
        # each P04 TUNE horizon prints the token
        assert RETIRED_TOKEN in report


def test_h1_x2_01_v1_1_report_has_no_voided_excesses() -> None:
    """FAILS at base (v1.1 dir absent); regression pin once v1.1 exists."""
    text_blob = ""
    for path in sorted(V1_1.rglob("*")):
        if not path.is_file():
            continue
        try:
            text_blob += path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    assert "-0.0763" not in text_blob
    assert "-0.2184" not in text_blob
    assert "-0.2051" not in text_blob
    report = _v1_1_report()
    p04 = report.split("## EVT-CAPITAL")[0]
    tune_blocks = [b for b in _cell_blocks(p04) if b.startswith("### TUNE")]
    assert len(tune_blocks) == 3
    for blk in tune_blocks:
        assert RETIRED_TOKEN in blk


# ---------------------------------------------------------------------------
# X2-02 baseline (ii) sign  (FAILS at base)
# ---------------------------------------------------------------------------

class _SyntheticLoader:
    def __init__(self, baba: pd.DataFrame, spy: pd.DataFrame) -> None:
        self._frames = {"data/yahoo/BABA.parquet": baba,
                        "data/yahoo/SPY.parquet": spy}

    def read_parquet(self, path, columns=None):
        df = self._frames[path]
        return df if columns is None else df[[c for c in columns if c in df.columns]]


def _trailing_engine(baba_d, baba_d63, spy_d, spy_d63, s_us: date) -> OutcomeEngine:
    d = s_us - timedelta(days=1)
    while not nyse_calendar.is_session(d):
        d -= timedelta(days=1)
    d63 = d
    seen = 0
    while seen < 63:
        d63 -= timedelta(days=1)
        if nyse_calendar.is_session(d63):
            seen += 1
    sessions = []
    cur = d63 - timedelta(days=5)
    end = d + timedelta(days=5)
    while cur <= end:
        if nyse_calendar.is_session(cur):
            sessions.append(cur)
        cur += timedelta(days=1)

    def close_on(sess, at_d, at_d63, other):
        if sess == d:
            return at_d
        if sess == d63:
            return at_d63
        return other

    baba = pd.DataFrame(
        [(s.isoformat(), close_on(s, baba_d, baba_d63, baba_d63),
          close_on(s, baba_d, baba_d63, baba_d63))
         for s in sessions],
        columns=["Date", "close", "close_price"])
    spy = pd.DataFrame(
        [(s.isoformat(), close_on(s, spy_d, spy_d63, spy_d63),
          close_on(s, spy_d, spy_d63, spy_d63))
         for s in sessions],
        columns=["Date", "close", "close_price"])
    return OutcomeEngine(_SyntheticLoader(baba, spy)), s_us


def test_h1_x2_02_baseline_ii_sign() -> None:
    s_us = date(2024, 6, 3)
    rising, s = _trailing_engine(120.0, 100.0, 400.0, 400.0, s_us)
    assert rising.trailing63_direction(s) == 1
    falling, s = _trailing_engine(100.0, 100.0, 480.0, 400.0, s_us)
    assert falling.trailing63_direction(s) == -1


# ---------------------------------------------------------------------------
# X2-03 seal top-level flags  (FAILS at base for v1.1 file; unit pins FAIL
# at base because refuse_nonfalse_authority did not exist)
# ---------------------------------------------------------------------------

def test_h1_x2_03_seal_top_level_flags(monkeypatch) -> None:
    seal = _v1_1_seal()
    top = seal["authority_flags"]
    assert seal["outcome_free"] is True
    for k in ("rank_authority", "gate_authority", "size_authority",
              "signal_authority", "escalation_authority", "trade_authority"):
        assert top[k] is False
        assert seal["labels"]["authority_flags"][k] is False

    tainted_top = copy.deepcopy(seal)
    tainted_top["authority_flags"]["trade_authority"] = True
    with pytest.raises((ValueError, SystemExit)):
        refuse_nonfalse_authority(tainted_top)

    tainted_labels = copy.deepcopy(seal)
    tainted_labels["labels"]["authority_flags"]["trade_authority"] = True
    with pytest.raises((ValueError, SystemExit)):
        refuse_nonfalse_authority(tainted_labels)

    # v1 seal still verifies (absent top-level key falls back to labels)
    loader = GitBlobLoader(ROOT, INPUT_REF)
    state = compute_state(loader)
    verify_seal(V1, state)

    monkeypatch.setitem(AUTHORITY_FLAGS, "trade_authority", True)
    with pytest.raises((ValueError, SystemExit)):
        refuse_nonfalse_authority(seal)


# ---------------------------------------------------------------------------
# X2-04 graded-only membership digest  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_04_graded_only_membership_digest() -> None:
    seal = _v1_1_seal()
    v1 = json.loads((V1 / "SEAL_AND_BUDGET.json").read_text(encoding="utf-8"))
    v1_mem = {(r["protocol_id"], int(r["horizon"]), r["split"]):
              r["membership_sha256"] for r in v1["membership_table"]}
    report = _v1_1_report()
    for row in seal["membership_table"]:
        key = (row["protocol_id"], int(row["horizon"]), row["split"])
        assert row["membership_sha256"] == v1_mem[key]
        if (row["protocol_id"] == "P04" and row["split"] == "TUNE"
                and int(row["horizon"]) in (5, 21, 63)):
            assert row["count"] == 2
            assert row["graded_membership_count"] == 1
            assert row["census_only_count"] == 1
            # honest-N in the REPORT for that cell equals graded_membership_count
            needle = f"| P04 | TUNE | {row['horizon']} | {row['graded_membership_count']} |"
            assert needle in report


# ---------------------------------------------------------------------------
# X2-05 register fold  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_05_register_fold() -> None:
    text = REG.read_text(encoding="utf-8")
    # vocabulary row no longer says "No row holds it today" for RETIRED-CONTAMINATED
    vocab = None
    for line in text.splitlines():
        if line.startswith("| **RETIRED-CONTAMINATED**"):
            vocab = line
            break
    assert vocab is not None
    assert "No row holds it today" not in vocab
    assert "P01 v1" in vocab and "P03 v1" in vocab and "P04 v1" in vocab
    for pid in ("P01", "P03", "P04"):
        assert f"| {pid} |" in text
    assert text.count("RETIRED-CONTAMINATED (v1 TUNE information_leak, SL §8 → §7); prior status:") == 3
    assert text.count("— (none registered); owner = seat/S0") == 3
    lane = json.loads((V1_1 / "LANE_MANIFEST.json").read_text(encoding="utf-8"))
    p04 = [r for r in lane["info_leak"] if r.get("protocol_id") == "P04"][0]
    assert p04["successor"] == "— (none registered); owner = seat/S0"


# ---------------------------------------------------------------------------
# X2-06 multiplicity sentence  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_06_multiplicity_sentence() -> None:
    results = _v1_1_results()
    sentence = multiplicity_sentence(results)
    report = _v1_1_report()
    assert report.count(sentence) == 1
    n_cells = sum(
        1 for pid in results
        for split in ("TRAIN", "TUNE", "QUARANTINE")
        for _h in ("h5", "h21", "h63"))
    n_test = sum(1 for pid in results if "TEST" in results[pid]["splits"])
    assert str(n_cells) in sentence
    assert str(n_test) in sentence
    assert "no p-value family exists" in sentence
    assert "multiplicity adjustment is therefore not estimable" in sentence


# ---------------------------------------------------------------------------
# X2-07 renderer nits  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_07_renderer_nits() -> None:
    report = _v1_1_report()
    sections = re.split(r"(?=^## EVT-)", report, flags=re.M)
    family_sections = [s for s in sections if s.startswith("## EVT-")]
    assert len(family_sections) == 3
    iii = "baseline (iii) direction of the all-events pooled TRAIN prior"
    for section in family_sections:
        for blk in _cell_blocks(section):
            if not blk.startswith("### TUNE"):
                continue
            assert blk.count(iii) == 1
        if section.startswith("## EVT-CAPITAL") or section.startswith("## EVT-REGULATORY"):
            assert "REG P04" not in section


# ---------------------------------------------------------------------------
# X2-08 honest-N lead table  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_x2_08_honest_n_lead_table() -> None:
    report = _v1_1_report()
    lead = report.split("## Abstention ladder")[0]
    lead_rows = [ln for ln in lead.splitlines()
                 if re.match(r"\| P0[456] \| (TRAIN|TUNE|QUARANTINE) \|", ln)]
    assert len(lead_rows) == 27
    for blk in _cell_blocks(report):
        assert "effective_n" not in blk


# ---------------------------------------------------------------------------
# A7-F1 conservative purge  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_a7_f1_purge_unknown_coverage() -> None:
    assert purge_flag("TRAIN", None) is True
    assert purge_flag("TUNE", None) is True
    assert purge_flag("QUARANTINE", None) is True


# ---------------------------------------------------------------------------
# A7-F2 no empty tokens  (FAILS at base for "" and "a<br/>")
# ---------------------------------------------------------------------------

def test_h1_a7_f2_no_empty_tokens() -> None:
    assert split_tokens("") == []
    assert split_tokens("a<br/>") == ["a"]
    assert split_tokens(None) == []
    assert split_tokens("<br/>".join(split_tokens(None))) == split_tokens(None)


# ---------------------------------------------------------------------------
# A7-F5 deterministic exclusion order  (FAILS at base)
# ---------------------------------------------------------------------------

def test_h1_a7_f5_deterministic_exclusion_order() -> None:
    loader = GitBlobLoader(ROOT, INPUT_REF)
    state = compute_state(loader)
    us = session_dates(nyse_calendar)
    hk = session_dates(hk_calendar)
    rows = [{
        "id": r["id"],
        "issuer_key": r["issuer_key"],
        "family": r["family"],
        "category": r.get("category"),
        "title": r.get("title", ""),
        "t_avail_utc": r["t_avail_utc"],
        "t_avail_quality": r["t_avail_quality"],
        "s_us": r["s_us"],
        "s_hk": r["s_hk"],
        "evidence_pointer": f"{r['source']}#id={r['id']}",
        "disposition": r["disposition"],
        "listed_exclusion_reason": r["listed_exclusion_reason"],
    } for r in state["census_rows"]]
    programmes = state["programmes"]
    event_exclusions = state["event_exclusions"]
    base = run_collapse(rows, programmes, us, hk, GRADE_HORIZONS,
                        event_exclusions=event_exclusions)

    def dump(out: dict) -> str:
        payload = {
            "events": [(e.issuer_key, e.family, e.t_avail_utc, e.evidence_pointer,
                        tuple(e.member_ids), e.programme)
                       for e in out["events"]],
            "exclusions": [(e.step, e.issuer_key, e.id, e.reason)
                           for e in out["exclusions"]],
            "counts": out["counts"],
            "per_h": {
                str(h): [(ep.opener.evidence_pointer, ep.horizon,
                          tuple(a.evidence_pointer for a in ep.absorbed))
                         for ep in out["per_h"][h]["episodes"]]
                for h in GRADE_HORIZONS
            },
        }
        return json.dumps(payload, sort_keys=True, default=str)

    want = dump(base)
    rng = random.Random(20261012)
    for i in range(50):
        perm = list(rows)
        rng.shuffle(perm)
        got = run_collapse(perm, programmes, us, hk, GRADE_HORIZONS,
                           event_exclusions=event_exclusions)
        assert dump(got) == want, f"shuffle {i} changed collapse output"


# ---------------------------------------------------------------------------
# Language / authority regression pins (pure regression pins)
# ---------------------------------------------------------------------------

def test_h1_v1_1_report_banned_tokens_regression() -> None:
    """Pure regression pin: v1.1 REPORT language law."""
    report = _v1_1_report()
    low = report.lower()
    for tok in ("validated", "news impact", "forecast support"):
        assert tok not in low
    assert "p_value" not in low
    # X2-06 requires the words "p-value family" once; no numeric p-value is printed.
    assert low.count("p-value") == 1
    assert "no p-value family exists" in low
    vr = json.loads((V1_1 / "VERSION_RECORD.json").read_text(encoding="utf-8"))
    assert vr["descriptive_only"] is True
    assert all(v is False for v in vr["authority_flags"].values())
