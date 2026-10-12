"""S1 v1.1 hardening pins (X1-01..X1-10, A6-F1..F3).

Committed-evidence tests read runs/s1_residual_v1_1/. Unit tests that
drive retirement / authority / A6 behaviour fail at the v1 base except
the labelled pure regression pins.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research/single_name_intelligence/residual"))

import run_s1  # noqa: E402
from s1_decomposition import beta_window_dates, spec_hash  # noqa: E402
from s1_prereg import (AUTHORITY_FLAGS, POWER_FLOOR_N,  # noqa: E402
                       assert_authority_false, prereg_digest)
from s1_report import (TCEHY_EXEMPLAR, appendix_cells,  # noqa: E402
                       criterion_met_rows, exemplar_table, family_alpha,
                       family_effective_n, family_wise_clearing,
                       parse_block_key, s0_criterion_holds)
from s1_stats import mirror_mean_ci  # noqa: E402
from s1_synth import synth_frames, write_synthetic_repo  # noqa: E402

V11 = REPO / "research/single_name_intelligence/runs/s1_residual_v1_1"
V1 = REPO / "research/single_name_intelligence/runs/s1_residual"
PREREG = "c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab"
FINDING = ("p=", "criterion met", "beats", "rejects")


def _load_json(p: Path):
    return json.loads(p.read_text("utf-8"))


def _v11_results():
    assert V11.is_dir(), f"missing v1.1 tree {V11}"
    out = {}
    for pid in ("P01", "P02", "P03"):
        doc = _load_json(V11 / "results" / f"{pid}.json")
        out[pid] = {"family": doc["family"], "blocks": doc["blocks"],
                    "block_order": list(doc["blocks"])}
    return out


def _report() -> str:
    p = V11 / "REPORT.md"
    assert p.exists(), p
    return p.read_text("utf-8")


def _block_sections(md: str) -> list[tuple[str, str]]:
    parts = re.split(r"^### ", md, flags=re.M)[1:]
    out = []
    for sec in parts:
        lines = sec.splitlines()
        key = lines[0].strip()
        out.append((key, sec))
    return out


def _lead_line(sec: str) -> str:
    for ln in sec.splitlines()[1:]:
        if ln.strip():
            return ln.strip()
    return ""


# --------------------------------------------------------------------------- #
# X1-03 P03 TUNE retirement scope
# --------------------------------------------------------------------------- #
def test_h1_x1_03_p03_hk_tune_not_retired():
    """FAILS at the base: v1 stamps TUNE RETIRED on all 12 P03 HK TUNE blocks."""
    p03 = _load_json(V11 / "results" / "P03.json")
    hk_tune, baba_tune = [], []
    for k, b in p03["blocks"].items():
        aset = b.get("analysis_set") or ""
        blob = json.dumps(b)
        if "hkd_" in k and "|TUNE|" in k:
            hk_tune.append(k)
            assert "TUNE RETIRED" not in aset, k
            assert "TUNE RETIRED" not in blob, k
            assert "VINTAGE_UNVERIFIABLE (HK series, no raw column) — disclosed, NOT retired" in aset
            assert "DESCRIPTIVE — outside the P03 cohort" in aset
        if "adr_baba" in k and "|TUNE|" in k:
            baba_tune.append(k)
            assert "TUNE RETIRED" in aset, k
    assert len(hk_tune) == 12
    assert baba_tune and all("TUNE RETIRED" in p03["blocks"][k]["analysis_set"]
                             for k in baba_tune)
    p01 = _load_json(V11 / "results" / "P01.json")
    p01_tune = [k for k in p01["blocks"] if "|TUNE" in k]
    assert p01_tune
    assert all("TUNE RETIRED" in p01["blocks"][k]["analysis_set"] for k in p01_tune)
    lane = _load_json(V11 / "LANE_MANIFEST.json")
    scopes = {r["protocol_id"]: r.get("retired_scope", r["protocol_id"])
              for r in lane["retirements"]}
    assert scopes.get("P03") == "P03-BABA"
    assert scopes.get("P01") == "P01"
    for r in lane["retirements"]:
        assert r["successor"] == f"{r['protocol_id']} v2 — not drafted; owner = seat/S0"


def test_h1_x1_03_retirement_pairs_synthetic_baba_hit():
    """FAILS at the base: v1 retired protocols, not (protocol, subject) pairs."""
    baba = {"BABA": {"detection": {"first_offending_date": "2024-06-13"}},
            "SPY": {"detection": None}, "KWEB": {"detection": None}}
    got = run_s1.retired_scope_pairs(baba)
    assert got == {("P01", "adr_baba"), ("P03", "adr_baba")}
    spy = {"BABA": {"detection": None},
           "SPY": {"detection": {"first_offending_date": "2024-03-15"}},
           "KWEB": {"detection": None}}
    spy_got = run_s1.retired_scope_pairs(spy)
    assert ("P03", "hkd_9988") not in spy_got
    assert ("P03", "hkd_0700") not in spy_got
    assert ("P02", "hkd_0700") not in spy_got
    kweb = {"BABA": {"detection": None}, "SPY": {"detection": None},
            "KWEB": {"detection": {"first_offending_date": "2024-12-17"}}}
    kweb_got = run_s1.retired_scope_pairs(kweb)
    assert kweb_got == {("P03", "adr_baba")}
    assert ("P03", "hkd_9988") not in kweb_got
    assert ("P01", "adr_baba") not in kweb_got
    _ = (V11 / "results" / "P03.json").read_text("utf-8")


# --------------------------------------------------------------------------- #
# X1-05 power floor
# --------------------------------------------------------------------------- #
def test_h1_x1_05_power_floor_abstain_leads():
    """FAILS at the base: v1 leads with p-values / S0 verdicts at honest_n < 153."""
    md = _report()
    assert POWER_FLOOR_N == 153
    m = re.search(r"below-floor cell count: (\d+)", md)
    assert m, "below-floor count missing from REPORT lead"
    printed = int(m.group(1))
    parsed = 0
    for key, sec in _block_sections(md):
        n = int(re.search(r"^3\. honest_n: (\d+)", sec, re.M).group(1))
        if n < 153:
            parsed += 1
            lead = _lead_line(sec)
            assert lead.startswith("ABSTAIN — honest_n"), (key, lead)
            for tok in FINDING:
                assert tok not in lead, (key, tok, lead)
    assert printed == parsed
    assert printed == 102


# --------------------------------------------------------------------------- #
# X1-06 family-wise haircut
# --------------------------------------------------------------------------- #
def test_h1_x1_06_family_wise_haircut_and_appendix():
    """FAILS at the base: v1 prints unadjusted p<0.05 with no family-wise haircut."""
    md = _report()
    protocols = _v11_results()
    for pid in ("P01", "P02", "P03"):
        eff = family_effective_n(protocols, pid)
        a = family_alpha(eff)
        line = f"{pid}: family-wise α = 0.05 / effective_n = {eff}"
        assert line in md, line
        clearing = family_wise_clearing(protocols, pid)
        listed = ", ".join(clearing) if clearing else "none"
        assert f"cells clearing α with honest_n >= {POWER_FLOOR_N}: {listed}" in md
        assert a == 0.05 / eff
    heading = "## Multiple-looks appendix (unadjusted, non-confirmatory)"
    assert md.count(heading) == 1
    want = appendix_cells(protocols)
    for key, pv, a, pid in want:
        assert key in md
        assert f"unadjusted p={pv}" in md
    assert any("P02|hkd_0700|h=21|TRAIN|always_long|H0_1" in k
               or k == "P02|hkd_0700|h=21|TRAIN|always_long|H0_1"
               for k, *_ in want)
    p02 = protocols["P02"]["blocks"]["P02|hkd_0700|h=21|TRAIN|always_long|H0_1"]
    p = p02["test"]["p_value"]
    assert p > 0.05 / 12
    assert abs(p - 0.010543202856568812) < 1e-12
    assert len(want) == 5


# --------------------------------------------------------------------------- #
# X1-01 coverage and regime
# --------------------------------------------------------------------------- #
def test_h1_x1_01_coverage_and_current_regime():
    """FAILS at the base: v1 never states coverage / 2026 regime limits."""
    md = _report()
    assert md.count("## Coverage and current regime") == 1
    protocols = _v11_results()
    rows = criterion_met_rows(protocols)
    for r in rows:
        needle = (f"{r['protocol']}|{r['subject']}|h={r['horizon']}|{r['split']} "
                  f"honest_n={r['honest_n']} "
                  f"{'retired' if r['retired'] else 'not-retired'}")
        assert needle in md, needle
    nonret = [r for r in rows if r["split"] == "TUNE" and not r["retired"]
              and r["honest_n"] >= POWER_FLOOR_N]
    assert nonret == []
    assert ("No S1 residual cell covering the 2024-01-01..2026-10-01 TUNE "
            "window meets the S0 criterion as confirmatory evidence; the "
            "criterion-met cells are pre-2024 TRAIN or TUNE-retired and "
            "do not cover the 2026 regime.") in md
    p03 = protocols["P03"]["blocks"]
    for k, b in p03.items():
        if "TUNE RETIRED" in (b.get("analysis_set") or ""):
            blob = json.dumps(b)
            assert "criterion met" not in blob, k
            assert "criterion met" not in k
    for key, sec in _block_sections(md):
        if "TUNE RETIRED" in sec:
            assert "criterion met" not in sec, key


# --------------------------------------------------------------------------- #
# X1-02 exemplar coverage
# --------------------------------------------------------------------------- #
def test_h1_x1_02_exemplar_table_and_tcehy():
    """FAILS at the base: v1 has no exemplar table and is silent on TCEHY."""
    md = _report()
    protocols = _v11_results()
    table = exemplar_table(protocols)
    for row in table:
        if row["exemplar"] == "TCEHY":
            assert TCEHY_EXEMPLAR in md
            assert row["text"] == TCEHY_EXEMPLAR
            continue
        bits = []
        for pid in ("P01", "P02", "P03"):
            info = row["protocols"][pid]
            bits.append(f"{pid} n={info['n']} {info['dist']}")
        line_frag = f"- {row['exemplar']}: " + "; ".join(bits)
        assert line_frag in md, line_frag
    tcehy_line = [ln for ln in md.splitlines() if ln.startswith("- TCEHY:")]
    assert len(tcehy_line) == 1
    assert "SEC:" not in tcehy_line[0]
    assert "CIK" not in tcehy_line[0]
    assert "TCEHY" in tcehy_line[0]
    assert "UNRESOLVED" in tcehy_line[0]
    assert ("The M2-over-M1 result is BABA-ADS h=5 TRAIN descriptive only and "
            "is KILL/HOLD on every 9988/0700 M2_vs_M1 cell.") in md


# --------------------------------------------------------------------------- #
# X1-04 0700 coverage hole
# --------------------------------------------------------------------------- #
def test_h1_x1_04_0700_coverage_hole():
    """FAILS at the base: v1 never prints the 0700 pre-2014 coverage hole."""
    md = _report()
    holes = {}
    for h in (5, 21, 63):
        rows = [_load_json_line(l) for l in
                (V11 / "manifests" / f"P02_hkd_0700_{h}.jsonl")
                .read_text("utf-8").splitlines() if l.strip()]
        abstain = [r for r in rows if r["split"] == "ABSTAIN_RESOLVER_NONE"]
        first = min(r["anchor_session_date"] for r in abstain)
        last = max(r["anchor_session_date"] for r in abstain)
        holes[h] = (f"COVERAGE HOLE: 0700 anchors {first}..{last} "
                    f"ABSTAIN_RESOLVER_NONE ({len(abstain)}/{len(rows)} "
                    f"h={h} units; qledger HK clock floor 2014-01-01)")
    n_0700 = 0
    for key, sec in _block_sections(md):
        if "hkd_0700" not in key:
            continue
        n_0700 += 1
        meta = parse_block_key(key)
        hits = [ln for ln in sec.splitlines() if "COVERAGE HOLE:" in ln]
        assert len(hits) == 1, (key, hits)
        assert hits[0].strip() == holes[meta["h"]], (key, hits[0], holes[meta["h"]])
    assert n_0700 > 0
    # exemplar row carries a hole line too
    assert holes[5] in md


def _load_json_line(line: str):
    return json.loads(line)


# --------------------------------------------------------------------------- #
# X1-07 committed-evidence tests open v1.1 files (this file as a whole)
# --------------------------------------------------------------------------- #
def test_h1_x1_07_committed_evidence_paths():
    """FAILS at the base: v1.1 directory does not exist."""
    for rel in ("REPORT.md", "results/P01.json", "results/P02.json",
                "results/P03.json", "SEAL_AND_BUDGET.json",
                "LANE_MANIFEST.json", "CHALLENGER_UNIVERSE.json",
                "VERSION_RECORD.json", "trial_ledger.jsonl"):
        p = V11 / rel
        assert p.exists(), p
        p.read_text("utf-8")[:20]


# --------------------------------------------------------------------------- #
# X1-08 BLOCKED-AS-EVIDENCE on every TRAIN block
# --------------------------------------------------------------------------- #
def test_h1_x1_08_train_blocked_as_evidence():
    """FAILS at the base: v1 carries the label only at page level."""
    md = _report()
    n = 0
    for key, sec in _block_sections(md):
        if "|TRAIN|" not in key:
            continue
        n += 1
        assert "BLOCKED-AS-EVIDENCE" in sec, key
    assert n > 0
    protocols = _v11_results()
    for pid in protocols:
        for key, b in protocols[pid]["blocks"].items():
            if "|TRAIN|" in key:
                assert "BLOCKED-AS-EVIDENCE" in b["analysis_set"], key


# --------------------------------------------------------------------------- #
# X1-09 challenger panel disclosure
# --------------------------------------------------------------------------- #
def test_h1_x1_09_challenger_panel_disclosure():
    """FAILS at the base: v1 REPORT has no IPCA universe coverage line."""
    md = _report()
    u = _load_json(V11 / "CHALLENGER_UNIVERSE.json")
    line = (f"IPCA challenger universe = {u['files_examined']}/"
            f"{u['admitted_count']} (files_examined/admitted); "
            "survivorship: today's file set, no point-in-time membership; "
            "FX pairs/ETFs mixed with single names (e.g. USDBRL_X); "
            "the IPCA challenger cannot support any coverage claim")
    assert md.count(line) == 1


# --------------------------------------------------------------------------- #
# X1-10 refuse-on-true
# --------------------------------------------------------------------------- #
def test_h1_x1_10_refuse_on_true(monkeypatch, tmp_path):
    """FAILS at the base: v1 does not call assert_authority_false."""
    monkeypatch.setitem(run_s1.AUTHORITY_FLAGS, "trade", True)
    rc = run_s1.main(
        ["--input-ref", "X", "--out-dir", str(tmp_path / "out"),
         "--trial-ledger-path", str(tmp_path / "t.jsonl"),
         "--repo-root", str(tmp_path)],
        store=object(),
    )
    assert rc != 0
    assert not (tmp_path / "out" / "REPORT.md").exists()
    v11_seal = _load_json(V11 / "SEAL_AND_BUDGET.json")
    tampered = dict(v11_seal)
    flags = dict(tampered["authority_flags"])
    flags["trade"] = True
    tampered["authority_flags"] = flags
    (tmp_path / "research/single_name_intelligence/runs/s1_residual").mkdir(parents=True)
    # verify_seal against a tmp copy: plant seal at default RUNS_REL
    seal_path = tmp_path / "research/single_name_intelligence/runs/s1_residual" / "SEAL_AND_BUDGET.json"
    seal_path.write_text(json.dumps(tampered), encoding="utf-8")

    class _Store:
        input_ref = tampered["input_ref"]

    with pytest.raises(Exception) as e:
        run_s1.verify_seal(_Store(), tmp_path, tampered["input_ref"])
    assert "trade" in str(e.value)
    for p in (V1 / "SEAL_AND_BUDGET.json", V11 / "SEAL_AND_BUDGET.json"):
        seal = _load_json(p)
        assert_authority_false(seal["authority_flags"])


# --------------------------------------------------------------------------- #
# A6-F1 spec_hash order (regression pin, labelled) + docstring
# --------------------------------------------------------------------------- #
def test_h1_a6_f1_spec_hash_order_significant():
    """Regression pin (labelled): permuting factors changes the hash.

    Docstring must contain "order". The docstring clause FAILS at the base;
    the permutation behaviour already held at v1.
    """
    a = spec_hash("M2", "SEC:US-XNYS-BABA", ["SPY", "KWEB"], 5)
    b = spec_hash("M2", "SEC:US-XNYS-BABA", ["KWEB", "SPY"], 5)
    assert a != b
    assert "order" in spec_hash.__doc__.lower()


# --------------------------------------------------------------------------- #
# A6-F2 mirror CI rounding docstring (regression pin, labelled)
# --------------------------------------------------------------------------- #
def test_h1_a6_f2_mirror_ci_rounding_docstring():
    """Regression pin (labelled): docstring-only; FAILS at the base."""
    doc = mirror_mean_ci.__doc__ or ""
    assert "4" in doc and "round" in doc.lower()
    assert "mean" in doc.lower()


# --------------------------------------------------------------------------- #
# A6-F3 chronological input
# --------------------------------------------------------------------------- #
def test_h1_a6_f3_beta_window_dates_strictly_increasing():
    """FAILS at the base: v1 accepted unsorted subject_dates."""
    d0 = date(2020, 1, 6)
    ordered = [d0 + timedelta(days=i) for i in range(10)]
    got = beta_window_dates(ordered, ordered[-2], window=5)
    assert got == [d for d in ordered if d <= ordered[-2]][-5:]
    unsorted = list(ordered)
    unsorted[3], unsorted[4] = unsorted[4], unsorted[3]
    with pytest.raises(ValueError, match="strictly increasing"):
        beta_window_dates(unsorted, unsorted[-1], window=5)
    # v1.1 membership/results for decomposition unchanged except X1 relabels:
    # membership_table equals v1.
    v1 = _load_json(V1 / "SEAL_AND_BUDGET.json")["membership_table"]
    v11 = _load_json(V11 / "SEAL_AND_BUDGET.json")["membership_table"]
    assert v1 == v11


# --------------------------------------------------------------------------- #
# language / authority / digest pins used by several defects
# --------------------------------------------------------------------------- #
def test_h1_x1_report_language_and_digest():
    md = _report()
    low = md.lower()
    for tok in ("validated", "news impact", "forecast support", "caused"):
        assert tok not in low, tok
    rec = _load_json(V11 / "VERSION_RECORD.json")
    assert rec["prereg_digest_v1"] == PREREG
    assert rec["prereg_digest_v1_1"] == PREREG
    assert rec["prereg_digest_unchanged"] is True
    assert rec["membership_table_unchanged"] is True
    assert rec["descriptive_only"] is True
    assert rec["authority_flags"] == AUTHORITY_FLAGS
    assert prereg_digest() == PREREG
    assert rec["configuration_added_removed_or_changed"] is False
