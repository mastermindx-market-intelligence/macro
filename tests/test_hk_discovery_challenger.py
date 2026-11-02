"""hk-discovery wave (WS:PROPHET-HK-CA-REVAMP) — engine/hk_discovery_challenger.py.

research/PROPHET_SHADOW_CONTRACT_V1.md §3/§4 is the binding storage/isolation
contract this challenger registers against; this file's kills are named
K-D1..K-D9 per the build commission that registered the FIRST real HK Lane-B
discovery challenger (``hk_discovery_v1``) into that substrate.

Every writer-exercising kill carries a POSITIVE CONTROL arm (the substrate
standing clause, mirrored from tests/test_board_shadow.py): asserts the
control path actually wrote/produced something, so a lane-gated no-op could
never pass every kill vacuously.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import board_shadow as bs  # noqa: E402
from engine import hk_board_rank as hbr  # noqa: E402
from engine import hk_discovery_challenger as hkdc  # noqa: E402
from engine import hk_native_intelligence as hki  # noqa: E402
from lib import config  # noqa: E402


# ---------------------------------------------------------------------------
# Shared session date
# ---------------------------------------------------------------------------
# Same wall-clock hazard as tests/test_board_shadow.py: the substrate stamps
# itself from the real clock and refuses any row whose ``session_date`` trails
# that stamp by more than ``bs.SETTLE_WINDOW_DAYS`` (K8b/F10).  A hard-coded
# session date therefore passes only until it ages out, then every registration
# these K-D kills exercise is refused and the whole ``board-shadow-substrate``
# job reds with no commit near this lane.  A literal ``2026-08-21`` did exactly
# that at 2026-08-25T00:00Z.  The ancient ``2020-01-01`` backfill-refusal arm is
# deliberately NOT derived, so the fence stays under test in both directions.
ASOF = (dt.date.today() - dt.timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    monkeypatch.setattr(config, "data_dir", lambda: data_root)
    bs.CHALLENGER_REGISTRY.clear()
    monkeypatch.delenv("CN_LANE", raising=False)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    yield data_root
    bs.CHALLENGER_REGISTRY.clear()


def _hk_on(monkeypatch) -> None:
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.delenv("COLLECT_LANE", raising=False)


def _ca_on(monkeypatch) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.delenv("CN_LANE", raising=False)


def _verdict(**kw) -> dict:
    base = {"eligible": False, "ticks": None, "above200": None,
            "weekly_bull": None, "last": {}, "fresh_bars": None}
    base.update(kw)
    return base


def _discovery_fn_ok(asof_arg: str) -> list[dict]:
    return [{
        "session_date": asof_arg, "security_ref_raw": "AAA",
        "candidate_origin": "washout_reclaim",
        "availability_status": hkdc.WAIT_CONFLUENCE,
        "availability_source": "hk_signal_gate",
    }]


# ---------------------------------------------------------------------------
# K-D1 — producer-cap kill
# ---------------------------------------------------------------------------
def test_k_d1_no_producer_cap_on_the_candidate_population():
    """Every firing name reaches build_candidates output — MORE names than
    every display cap constant (RAN_CAP/VETOED_CAP/RIPENING_CAP/LEADERS_CAP)
    combined, proving this module applies no producer cap of its own."""
    n = max(hbr.RAN_CAP, hbr.VETOED_CAP, hbr.RIPENING_CAP, hbr.LEADERS_CAP) + 25
    tickers = [f"T{i}.HK" for i in range(n)]
    evidence = {"washout_2w": {t: True for t in tickers}}
    rows = hkdc.build_candidates(evidence, ASOF)
    assert len(rows) == n, (
        f"expected all {n} firing names uncapped, got {len(rows)} — a cap "
        "was applied to the candidate population"
    )
    assert {r["security_ref_raw"] for r in rows} == set(tickers)


# ---------------------------------------------------------------------------
# K-D2 — origin-laundering kill
# ---------------------------------------------------------------------------
def test_k_d2_output_invariant_under_permuted_board_fields():
    """A bundle carrying board rank/featured/membership-shaped fields must
    not change the output when those fields are permuted — this module reads
    only its own named evidence keys."""
    evidence_a = {
        "washout_2w": {"AAA": True},
        "sig_verdict": {"AAA": _verdict(eligible=True)},
        "board_pos": {"AAA": 1},          # hostile extra — must be ignored
        "featured": {"AAA": True},        # hostile extra — must be ignored
        "membership": ["AAA"],            # hostile extra — must be ignored
    }
    evidence_b = {
        **evidence_a,
        "board_pos": {"AAA": 99},
        "featured": {"AAA": False},
        "membership": [],
    }
    rows_a = hkdc.build_candidates(evidence_a, ASOF)
    rows_b = hkdc.build_candidates(evidence_b, ASOF)
    assert rows_a == rows_b


def test_k_d2_source_fence_no_featured_board_pos_or_hk_standouts_tokens():
    source = (ROOT / "engine" / "hk_discovery_challenger.py").read_text()
    assert "featured" not in source
    assert "board_pos" not in source
    assert "hk_standouts" not in source


# ---------------------------------------------------------------------------
# K-D3 — missing != 0 kill
# ---------------------------------------------------------------------------
def test_k_d3_no_ah_twin_fires_nothing_no_fabricated_zero():
    """AAA has a resolvable A/H twin (present in ah_value); BBB is never
    mentioned anywhere (no twin) — BBB must not appear as a candidate at all,
    and must never fire ah_dislocation."""
    evidence = {"ah_value": {"AAA": {"cheap": True, "z": 1.2}}}
    rows = hkdc.build_candidates(evidence, ASOF)
    tickers = {r["security_ref_raw"] for r in rows}
    assert "AAA" in tickers
    assert "BBB" not in tickers
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert "ah_dislocation" in aaa["candidate_origin"]


def test_k_d3_ah_present_but_not_cheap_never_fires():
    """A name WITH a twin whose read is not 'cheap' fires no ah_dislocation —
    the leg is a strict boolean read, never a fabricated near-miss."""
    evidence = {"ah_value": {"AAA": {"cheap": False, "z": -0.2}}}
    rows = hkdc.build_candidates(evidence, ASOF)
    assert rows == []


# ---------------------------------------------------------------------------
# K-D4 — unknown-availability kill
# ---------------------------------------------------------------------------
def test_k_d4_no_gate_verdict_is_never_entry_open():
    evidence = {"washout_2w": {"AAA": True}, "sig_verdict": {}}
    rows = hkdc.build_candidates(evidence, ASOF)
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_status"] != hkdc.ENTRY_OPEN
    assert aaa["availability_source"] == "missing_inputs(gate_verdict)"


# All three whole-read availability flags EXPLICITLY True — the ONLY shape
# from which ENTRY_OPEN is reachable (Sol pre-settlement repair 2026-08-22:
# an omitted flag must never default to available).
_ALL_READS_AVAILABLE = {
    "plc_available": True,
    "knife_available": True,
    "extension_available": True,
}


def _entry_open_base_evidence():
    return {
        "washout_2w": {"AAA": True},
        "sig_verdict": {"AAA": _verdict(eligible=True)},
        **_ALL_READS_AVAILABLE,
    }


def _aaa_row(evidence):
    rows = hkdc.build_candidates(evidence, ASOF)
    return next(r for r in rows if r["security_ref_raw"] == "AAA")


def test_k_d4_all_reads_explicitly_available_is_entry_open():
    """POSITIVE CONTROL (Sol regression 4): with every required whole-read
    availability flag explicitly True, an eligible unblocked name reaches
    ENTRY_OPEN exactly as before."""
    aaa = _aaa_row(_entry_open_base_evidence())
    assert aaa["availability_status"] == hkdc.ENTRY_OPEN
    assert aaa["availability_source"] == "hk_signal_gate"


def test_k_d4_placement_gate_unavailable_demotes_would_be_entry_open():
    aaa = _aaa_row({**_entry_open_base_evidence(), "plc_available": False})
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "placement_gate_unavailable"


def test_k_d4_knife_read_unavailable_demotes_would_be_entry_open():
    """R4 (F4): when the falling-knife pass never stamped this render
    (knife_available=False), a name that would otherwise reach ENTRY_OPEN
    gets UNAVAILABLE_DATA/knife_read_unavailable instead — never a silent
    ENTRY_OPEN pass-through just because knife_risk happened to be empty."""
    aaa = _aaa_row({**_entry_open_base_evidence(), "knife_available": False})
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "knife_read_unavailable"


def test_k_d4_omitted_plc_available_is_never_entry_open():
    """Sol regression 1: an evidence bundle that OMITS plc_available must
    fail closed — unknown required availability never defaults to pass."""
    evidence = _entry_open_base_evidence()
    del evidence["plc_available"]
    aaa = _aaa_row(evidence)
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "placement_gate_unavailable(unstated)"


def test_k_d4_omitted_knife_available_is_never_entry_open():
    """Sol regression 2: omitting knife_available (the pre-repair
    default-true hole) must fail closed to UNAVAILABLE_DATA."""
    evidence = _entry_open_base_evidence()
    del evidence["knife_available"]
    aaa = _aaa_row(evidence)
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "knife_read_unavailable(unstated)"


def test_k_d4_omitted_extension_available_is_never_entry_open():
    """Sol regression 3: omitting extension_available must fail closed."""
    evidence = _entry_open_base_evidence()
    del evidence["extension_available"]
    aaa = _aaa_row(evidence)
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "extension_read_unavailable(unstated)"


def test_k_d4_explicit_none_availability_flag_is_never_entry_open():
    """Explicit None is as unknown as omitted — fail closed for each flag."""
    for key, source in (
        ("plc_available", "placement_gate_unavailable(unstated)"),
        ("knife_available", "knife_read_unavailable(unstated)"),
        ("extension_available", "extension_read_unavailable(unstated)"),
    ):
        aaa = _aaa_row({**_entry_open_base_evidence(), key: None})
        assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA, key
        assert aaa["availability_source"] == source


def test_k_d4_absent_flag_does_not_weaken_per_name_blockers():
    """Sol repair scope guard: a known conservative per-name blocker
    (RIGHTS_BLOCKED / WAIT_PULLBACK / RAN_DONT_CHASE) still wins even when a
    DIFFERENT read's availability flag is absent — an unknown read demotes
    only the would-be ENTRY_OPEN pass, never a known blocker."""
    evidence = _entry_open_base_evidence()
    del evidence["extension_available"]
    evidence["knife_risk"] = {"AAA": True}
    aaa = _aaa_row(evidence)
    assert aaa["availability_status"] == hkdc.WAIT_PULLBACK
    assert aaa["availability_source"] == "knife_read"


def test_k_d4_knife_read_true_still_wins_over_availability():
    """A knife_available=True map that also fires knife_risk for this ticker
    must still return WAIT_PULLBACK/knife_read — availability is a SEPARATE
    ladder rung below the actual knife/extension reads, never a substitute
    for them."""
    evidence = {
        "washout_2w": {"AAA": True},
        "sig_verdict": {"AAA": _verdict(eligible=True)},
        "knife_available": True,
        "knife_risk": {"AAA": True},
    }
    rows = hkdc.build_candidates(evidence, ASOF)
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert aaa["availability_status"] == hkdc.WAIT_PULLBACK
    assert aaa["availability_source"] == "knife_read"


def test_k_d4_extension_read_unavailable_demotes_would_be_entry_open():
    """R4 (F4): the extension-map mirror of the knife-availability test above
    — extension_signals() returns an empty map by construction whenever
    `closes` is absent, and per-name absence within that empty map must not
    be read as 'not extended' when the whole read never ran."""
    aaa = _aaa_row({**_entry_open_base_evidence(), "extension_available": False})
    assert aaa["availability_status"] == hkdc.UNAVAILABLE_DATA
    assert aaa["availability_source"] == "extension_read_unavailable"


def test_k_d4_extension_read_true_still_wins_over_availability():
    """extension_available=True with the name's own extended read True must
    still return RAN_DONT_CHASE/extension_read."""
    evidence = {
        "washout_2w": {"AAA": True},
        "sig_verdict": {"AAA": _verdict(eligible=True)},
        "extension_available": True,
        "extended": {"AAA": True},
    }
    rows = hkdc.build_candidates(evidence, ASOF)
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert aaa["availability_status"] == hkdc.RAN_DONT_CHASE
    assert aaa["availability_source"] == "extension_read"


# ---------------------------------------------------------------------------
# R2 (F2) — blocked_signal shares build_vetoed_rows's staleness bound
# ---------------------------------------------------------------------------
def test_r2_ancient_veto_does_not_fire_blocked_signal():
    """An 80-session-old veto (past VETOED_MAX_SESSIONS=63) must not fire
    blocked_signal — the same bound build_vetoed_rows applies to the display
    lane."""
    evidence = {
        "sig_verdict": {"AAA": _verdict(
            eligible=False, weekly_bull=True, fresh_bars=80,
            last={"type": "buy", "quality": "block", "reason": "counter_trend"},
        )},
        "dir_by_ticker": {"AAA": "up"},
    }
    rows = hkdc.build_candidates(evidence, ASOF)
    origins = next((r["candidate_origin"] for r in rows if r["security_ref_raw"] == "AAA"), "")
    assert "blocked_signal" not in origins


def test_r2_fresh_veto_fires_blocked_signal():
    """POSITIVE CONTROL: a fresh (10-session) veto still fires, carrying the
    slugged reason sub-token."""
    evidence = {
        "sig_verdict": {"AAA": _verdict(
            eligible=False, weekly_bull=True, fresh_bars=10,
            last={"type": "buy", "quality": "block", "reason": "counter_trend"},
        )},
        "dir_by_ticker": {"AAA": "up"},
    }
    rows = hkdc.build_candidates(evidence, ASOF)
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert "blocked_signal(counter_trend)" in aaa["candidate_origin"]


def test_r2_unknown_age_veto_still_fires_blocked_signal():
    """Unknown age (no marker date at all, and fresh_bars absent) must still
    fire — only a KNOWN-stale veto is excluded, matching
    build_vetoed_rows's own conditional (`sessions is not None and sessions >
    bound`)."""
    evidence = {
        "sig_verdict": {"AAA": _verdict(
            eligible=False, weekly_bull=True, fresh_bars=None,
            last={"type": "buy", "quality": "block", "reason": "counter_trend"},
        )},
        "dir_by_ticker": {"AAA": "up"},
    }
    rows = hkdc.build_candidates(evidence, ASOF)
    aaa = next(r for r in rows if r["security_ref_raw"] == "AAA")
    assert "blocked_signal(counter_trend)" in aaa["candidate_origin"]


# ---------------------------------------------------------------------------
# K-D5 — historical-backfill kill (via the REAL substrate refusal)
# ---------------------------------------------------------------------------
def test_k_d5_historical_backfill_refused_by_the_substrate(monkeypatch):
    _hk_on(monkeypatch)

    def _backdated(_asof_arg: str) -> list[dict]:
        return [{
            "session_date": "2020-01-01", "security_ref_raw": "AAA",
            "candidate_origin": "washout_reclaim",
            "availability_status": hkdc.WAIT_CONFLUENCE,
            "availability_source": "hk_signal_gate",
        }]

    bs.register_challenger("HK", hkdc.DEFINITION, discovery_fn=_backdated)
    result = bs.write_shadow([], market="HK", asof=ASOF)
    assert result["registry_state"] == "wrote_n_rows n=0"
    assert not bs._lane_b_path("HK").exists()

    # POSITIVE CONTROL: a same-session row lands.
    bs.CHALLENGER_REGISTRY.clear()
    bs.register_challenger("HK", hkdc.DEFINITION, discovery_fn=_discovery_fn_ok)
    result2 = bs.write_shadow([], market="HK", asof=ASOF)
    assert result2["written"] == 1
    assert bs._lane_b_path("HK").exists()


# ---------------------------------------------------------------------------
# K-D6 — market re-derivation fence
# ---------------------------------------------------------------------------
def test_k_d6_module_has_no_market_parameter_env_read_or_ca_token():
    source = (ROOT / "engine" / "hk_discovery_challenger.py").read_text()
    assert "os.environ" not in source
    assert "getenv(" not in source
    assert not re.search(r'''["']CA["']''', source), "quoted market-code literal 'CA' found"
    assert not re.search(r"canada", source, re.IGNORECASE)
    for match in re.finditer(r"def\s+\w+\(([^)]*)\)", source, re.DOTALL):
        params = [
            p.strip().split(":")[0].split("=")[0].strip().lstrip("*")
            for p in match.group(1).split(",") if p.strip()
        ]
        assert "market" not in params, f"a def carries a 'market' parameter: {match.group(0)}"


def test_k_d6_output_identical_under_a_mutated_ambient_market_env_var(monkeypatch):
    evidence = {
        "washout_2w": {"AAA": True},
        "sig_verdict": {"AAA": _verdict(eligible=True)},
    }
    before = hkdc.build_candidates(evidence, ASOF)
    monkeypatch.setenv("CN_LANE", "asia")
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("MACRO_MARKET", "CA")
    after = hkdc.build_candidates(evidence, ASOF)
    assert before == after


# ---------------------------------------------------------------------------
# K-D7 — foreign-market isolation with the REAL registration
# ---------------------------------------------------------------------------
def test_k_d7_foreign_market_isolation_with_the_real_registration(monkeypatch):
    calls_seen: list[str] = []

    def _discovery_fn(asof_arg: str) -> list[dict]:
        calls_seen.append(asof_arg)
        return _discovery_fn_ok(asof_arg)

    bs.register_challenger("HK", hkdc.DEFINITION, discovery_fn=_discovery_fn)

    _ca_on(monkeypatch)
    result_ca = bs.write_shadow([], market="CA", asof=ASOF)
    assert result_ca["registry_state"] == "no_challenger_for_market"
    assert calls_seen == [], "the HK-only discovery_fn must never be invoked during a CA pass"
    assert not bs._lane_b_path("CA").exists()
    assert not (config.data_dir() / "prophet_shadow" / "ca_discovery_receipt.json").exists()

    # POSITIVE CONTROL: the same registration fires and writes under HK.
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    _hk_on(monkeypatch)
    result_hk = bs.write_shadow([], market="HK", asof=ASOF)
    assert result_hk["written"] == 1
    assert calls_seen == [ASOF]
    assert (config.data_dir() / "prophet_shadow" / "hk_discovery_receipt.json").exists()


# ---------------------------------------------------------------------------
# K-D8 (referenced here too, canonical home is tests/test_check_surface_
# freshness.py): a sanity import check that the two modules' constants agree.
# ---------------------------------------------------------------------------
def test_definition_constant_matches_the_registration_site():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    assert "hk_discovery_challenger.DEFINITION" in source
    assert hkdc.DEFINITION == "hk_discovery_v1"


# ---------------------------------------------------------------------------
# K-D9 — publication-isolation kill
# ---------------------------------------------------------------------------
def test_k_d9_registration_runs_after_the_hk_standouts_persist():
    """Structural guarantee: the registration block must sit AFTER the
    hk_standouts.json persist in scripts/build_hk_library.py's source, so the
    evidence-bundle assembly can never race or read the payload before it is
    fully serialized. MUTATION THIS KILLS: hoisting the registration block
    above the persist call.

    R3 (build commission) strengthens this pin: the evidence-ASSEMBLY BLOCK
    itself must start strictly between the persist and the registration
    call — a token at the very TOP of the assembly block (before the mutation
    this test's ORIGINAL two-point pin could not see: hoisting only the
    assembly block, leaving register_challenger's own call site untouched,
    would have passed the old i_persist < i_registration check vacuously)."""
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    i_persist = source.index('(fdir / "hk_standouts.json").write_text(')
    i_evidence_assembly_start = source.index("HK-DISCOVERY EVIDENCE ASSEMBLY START")
    i_registration = source.index(
        'hk_discovery_challenger.DEFINITION, discovery_fn=_hk_discovery_fn'
    )
    i_shadow = source.index('board_shadow.write_shadow(calls, market="HK"')
    assert i_persist < i_evidence_assembly_start < i_registration < i_shadow


def test_k_d9_evidence_assembly_block_deep_copies_before_binding():
    """R3 (F3+F7): the assembled evidence bundle must be deep-copied ONCE
    before it is bound into the registration closure — nothing later in
    scripts/build_hk_library.py (today or after a future edit) may then
    mutate a live object the closure still holds a reference to.
    MUTATION THIS KILLS: deleting the deepcopy call."""
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    i_evidence_assembly_start = source.index("HK-DISCOVERY EVIDENCE ASSEMBLY START")
    i_registration = source.index(
        'hk_discovery_challenger.DEFINITION, discovery_fn=_hk_discovery_fn'
    )
    block = source[i_evidence_assembly_start:i_registration]
    assert "deepcopy" in block


def test_k_d1_evidence_ripening_call_is_uncapped():
    """R7 (F9): the ripening evidence leg inside build_hk_library's evidence
    block must call build_ripening_rows with cap=10**9 and ready_cap=10**9 —
    the DISPLAY call elsewhere in the same file legitimately uses the real
    RIPENING_CAP/RIPENING_READY_CAP; only the discovery-evidence call must be
    uncapped (K-D1's producer-cap law, contract §4).
    MUTATION THIS KILLS: deleting either kwarg from the discovery-evidence
    call."""
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    marker = "_hk_disc_ripening_rows = hk_board_rank.build_ripening_rows("
    i = source.index(marker)
    call_src = source[i:i + 400]
    assert "cap=10**9" in call_src
    assert "ready_cap=10**9" in call_src


def test_k_d1_evidence_assembly_never_passes_a_raw_set_for_ripening_tickers():
    """R5 (F5): the evidence-assembly source must hand build_candidates a
    SORTED list for ripening_tickers, never the raw
    `_hk_disc_ripening_tickers` set — set iteration order is not stable
    across process runs. MUTATION THIS KILLS: reverting
    '"ripening_tickers": sorted(_hk_disc_ripening_tickers)' back to the bare
    set variable."""
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    assert '"ripening_tickers": sorted(_hk_disc_ripening_tickers)' in source


# ---------------------------------------------------------------------------
# R5 (F5) — deterministic candidate emission
# ---------------------------------------------------------------------------
def test_r5_build_candidates_rejects_a_raw_set_for_ripening_tickers():
    """build_candidates()/_candidate_universe() must fail loudly, not
    silently accept, a raw set for ripening_tickers — the defensive half of
    R5's fix, independent of the build_hk_library source pin above."""
    evidence = {"ripening_tickers": {"AAA", "BBB"}}
    with pytest.raises(AssertionError):
        hkdc.build_candidates(evidence, ASOF)


def test_r5_candidate_row_order_is_deterministic_across_repeated_calls():
    """Two calls in one process, given a SORTED ripening_tickers list, must
    produce identical row order — the positive control for the fix (a raw
    set could still happen to look ordered within one process; this pins the
    list-based contract that survives across processes too)."""
    evidence = {
        "washout_2w": {f"T{i}.HK": True for i in range(30)},
        "ripening_tickers": sorted(f"R{i}.HK" for i in range(30)),
    }
    rows_a = hkdc.build_candidates(evidence, ASOF)
    rows_b = hkdc.build_candidates(evidence, ASOF)
    order_a = [r["security_ref_raw"] for r in rows_a]
    order_b = [r["security_ref_raw"] for r in rows_b]
    assert order_a == order_b
    assert len(order_a) == 60


def test_k_d9_publication_isolation_with_the_real_challenger(monkeypatch):
    """Registering the REAL hk_discovery_v1 challenger and running a full
    write_shadow pass must never touch a hk_standouts-shaped payload dict
    that is already live in scope — the exact shape scripts/
    build_hk_library.py's registration block sits inside, downstream of the
    hk_standouts.json persist (fixture-level deep-equality, contract §4/K1
    idiom)."""
    _hk_on(monkeypatch)
    out = {
        "buy": [{"ticker": "AAA", "edge_z": 1.1}],
        "watch": [{"ticker": "BBB", "edge_z": -0.2}],
        "board_definition": "hk_prophet_v2",
    }
    before = json.dumps(out, sort_keys=True, default=str)

    evidence = {
        "sig_verdict": {"AAA": _verdict(eligible=True)},
        "washout_2w": {"AAA": True},
    }

    def _discovery_fn(asof_arg: str) -> list[dict]:
        return hkdc.build_candidates(evidence, asof_arg)

    bs.register_challenger("HK", hkdc.DEFINITION, discovery_fn=_discovery_fn)
    calls = [{"ticker": "AAA", "group": "entry_open", "board_definition": "hk_prophet_v2"},
             {"ticker": "BBB", "group": "watch", "board_definition": "hk_prophet_v2"}]
    result = bs.write_shadow(calls, market="HK", asof=ASOF)
    assert result["written"] >= 1  # POSITIVE CONTROL — the substrate actually ran

    after = json.dumps(out, sort_keys=True, default=str)
    assert before == after, "the hk_standouts-shaped payload must be byte-identical"


# ---------------------------------------------------------------------------
# Regression: the shared session date must never age out of the settle window
# ---------------------------------------------------------------------------
def test_shared_session_date_can_never_age_out_of_the_settle_window():
    """Companion to the same guard in tests/test_board_shadow.py.

    Both steps of the ``board-shadow-substrate`` job share one substrate and one
    wall-clock fence, so a literal that ages out here reds the job just as surely
    as one in the K1-K20 suite -- and healing only one file leaves the job red.
    """
    today = dt.date.today().isoformat()
    age = (dt.date.today() - dt.date.fromisoformat(ASOF)).days
    assert 0 <= age <= bs.SETTLE_WINDOW_DAYS
    assert not bs._settle_violation(ASOF, today)
    assert bs._settle_violation("2020-01-01", today)


def test_no_bare_session_date_literal_reintroduces_the_time_bomb():
    """Guard the repair: only the ancient backfill arm may be a bare literal."""
    source = (ROOT / "tests/test_hk_discovery_challenger.py").read_text()
    code = "\n".join(
        line.split("#", 1)[0] for line in source.splitlines()
        if not line.lstrip().startswith("#")
    )
    literals = set(re.findall(r'"(20\d{2}-\d{2}-\d{2})"', code))
    assert literals <= {"2020-01-01"}, (
        f"bare session-date literal(s) {sorted(literals - {'2020-01-01'})} will age out of "
        "SETTLE_WINDOW_DAYS and red board-shadow-substrate on a date rollover -- use ASOF"
    )


# ---------------------------------------------------------------------------
# K-NI1..K-NI4 — HK-NATIVE-INTEL Wave 6 (H3/X1 shadow families)
# ---------------------------------------------------------------------------
def _ni_prices(n: int = 420, drift: float = 0.001) -> pd.Series:
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    steps = 1.0 + drift + np.linspace(-0.003, 0.004, n)
    return pd.Series(100.0 * np.cumprod(steps), index=idx)


def _ni_premium(n: int = 420) -> pd.Series:
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    vals = np.linspace(0.10, 0.55, n) + 0.03 * np.sin(np.arange(n) / 9)
    return pd.Series(vals, index=idx)


def _ni_pairs():
    return [{"h": "0939.HK", "a": "601939.SS"}]


def test_k_ni1_h3_x1_match_frozen_formulas_and_preserve_null_semantics():
    prem, a = _ni_premium(), _ni_prices()
    asof = str(min(prem.index[-1], a.index[-1]).date())
    rows = hki.build_family_evidence(
        ["0939.HK", "0005.HK"], asof=asof, pair_rows=_ni_pairs(),
        premium_panel=pd.DataFrame({"0939.HK": prem}),
        a_closes=pd.DataFrame({"601939.SS": a}),
    )
    got = rows["0939.HK"]
    p = prem.loc[:asof].dropna().tail(hki.OWN_WIN)
    expected_h3 = float((p < p.iloc[-1]).sum() / len(p))
    r = (a / a.shift(hki.X1_LOOKBACK) - 1.0).loc[:asof].dropna().tail(hki.OWN_WIN)
    expected_x1 = float((r.iloc[-1] - r.mean()) / r.std(ddof=1))
    assert got["h3_ah_discount_status"] == hki.ACCRUING
    assert got["x1_atwin_momentum_status"] == hki.ACCRUING
    assert got["h3_ah_discount_value"] == pytest.approx(expected_h3)
    assert got["x1_atwin_momentum_value"] == pytest.approx(expected_x1)
    assert rows["0005.HK"]["h3_ah_discount_status"] == hki.NOT_APPLICABLE
    assert rows["0005.HK"]["x1_atwin_momentum_status"] == hki.NOT_APPLICABLE

    short = _ni_prices(100)
    partial = hki.build_family_evidence(
        ["0939.HK"], asof=str(short.index[-1].date()), pair_rows=_ni_pairs(),
        premium_panel=pd.DataFrame({"0939.HK": _ni_premium(100)}),
        a_closes=pd.DataFrame({"601939.SS": short}),
    )["0939.HK"]
    assert partial["h3_ah_discount_status"] == hki.PARTIAL
    assert partial["x1_atwin_momentum_status"] == hki.PARTIAL


def test_k_ni2_future_rows_cannot_change_asof_family_values():
    prem, a = _ni_premium(), _ni_prices()
    cut = prem.index[-20]
    base = hki.build_family_evidence(
        ["0939.HK"], asof=str(cut.date()), pair_rows=_ni_pairs(),
        premium_panel=pd.DataFrame({"0939.HK": prem}),
        a_closes=pd.DataFrame({"601939.SS": a}),
    )["0939.HK"]
    prem2, a2 = prem.copy(), a.copy()
    prem2.loc[prem2.index > cut] = 100.0
    a2.loc[a2.index > cut] = a2.loc[a2.index > cut] * 10.0
    changed = hki.build_family_evidence(
        ["0939.HK"], asof=str(cut.date()), pair_rows=_ni_pairs(),
        premium_panel=pd.DataFrame({"0939.HK": prem2}),
        a_closes=pd.DataFrame({"601939.SS": a2}),
    )["0939.HK"]
    assert changed == base


def test_k_ni3_native_families_do_not_originate_or_upgrade_availability():
    native = {"0939.HK": {
        "h3_ah_discount_status": hki.ACCRUING,
        "h3_ah_discount_value": 0.91,
        "x1_atwin_momentum_status": hki.ACCRUING,
        "x1_atwin_momentum_value": 1.25,
    }}
    evidence = {
        "washout_2w": {"0939.HK": True},
        "sig_verdict": {"0939.HK": _verdict(eligible=False)},
        "native_families": native,
    }
    row = hkdc.build_candidates(evidence, ASOF)[0]
    assert row["candidate_origin"] == "washout_reclaim"
    assert row["availability_status"] == hkdc.WAIT_CONFLUENCE
    for family in hki.FAMILIES:
        assert row[f"{family}_status"] == native["0939.HK"][f"{family}_status"]
        assert row[f"{family}_value"] == native["0939.HK"][f"{family}_value"]


def test_k_ni4_registered_family_fields_persist_shadow_only(monkeypatch):
    _hk_on(monkeypatch)
    raw = {
        "session_date": ASOF,
        "security_ref_raw": "0939.HK",
        "candidate_origin": "ah_dislocation",
        "availability_status": hkdc.WAIT_CONFLUENCE,
        "availability_source": "hk_signal_gate",
        "h3_ah_discount_status": hki.ACCRUING,
        "h3_ah_discount_value": 0.88,
        "x1_atwin_momentum_status": hki.PARTIAL,
        "x1_atwin_momentum_value": None,
    }
    bs.register_challenger("HK", "hk_native_family_test", discovery_fn=lambda _asof: [raw])
    receipt = bs.write_shadow([], market="HK", asof=ASOF)
    assert receipt["written"] == 1
    stored = pd.read_parquet(bs._lane_b_path("HK"))
    row = stored.iloc[0]
    assert row["h3_ah_discount_status"] == hki.ACCRUING
    assert row["h3_ah_discount_value"] == pytest.approx(0.88)
    assert row["x1_atwin_momentum_status"] == hki.PARTIAL
    assert pd.isna(row["x1_atwin_momentum_value"])
    assert bool(row["visible_to_user"]) is False
    assert bool(row["published_authority"]) is False


def test_k_ni5_builder_wires_families_after_publication_before_registration():
    source = (ROOT / "scripts/build_hk_library.py").read_text()
    persist = source.index('(fdir / "hk_standouts.json").write_text(')
    produce = source.index("hk_native_intelligence.build_family_evidence")
    bundle = source.index('"native_families":')
    register = source.index('board_shadow.register_challenger(')
    assert persist < produce < bundle < register


def test_k_ni6_unavailable_stale_and_zero_are_not_collapsed():
    fresh, prem = _ni_prices(), _ni_premium()
    last_asof = str(fresh.index[-1].date())
    unavailable = hki.build_family_evidence(
        ["0939.HK"], asof=last_asof, pair_rows=_ni_pairs(),
        premium_panel=None, a_closes=None,
    )["0939.HK"]
    assert unavailable["h3_ah_discount_status"] == hki.UNAVAILABLE
    assert unavailable["x1_atwin_momentum_status"] == hki.UNAVAILABLE

    stale_asof = str((
        fresh.index[-1] + pd.Timedelta(days=hki.MAX_INPUT_LAG_DAYS + 5)
    ).date())
    stale = hki.build_family_evidence(
        ["0939.HK"], asof=stale_asof, pair_rows=_ni_pairs(),
        premium_panel=pd.DataFrame({"0939.HK": prem}),
        a_closes=pd.DataFrame({"601939.SS": fresh}),
    )["0939.HK"]
    assert stale["h3_ah_discount_status"] == hki.STALE
    assert stale["x1_atwin_momentum_status"] == hki.STALE
    assert stale["h3_ah_discount_value"] is not None
    assert stale["x1_atwin_momentum_value"] is not None
    assert tuple(bs.FAMILY_REGISTRY) == tuple(hki.DISCOVERY_FAMILIES)


def test_k_ni7_x1_reads_the_preregistered_per_name_a_share_plane():
    calls = []

    def reader(group, name):
        calls.append((group, name))
        if group != "china_stocks":
            raise AssertionError(f"wrong X1 source plane: {group}/{name}")
        return pd.DataFrame({"close": _ni_prices()})

    panel = hki.load_a_twin_closes(_ni_pairs(), reader)
    assert calls == [("china_stocks", "601939.SS")]
    assert panel is not None
    assert list(panel.columns) == ["601939.SS"]

    source = (ROOT / "scripts/build_hk_library.py").read_text()
    marker = source.index("HK-NATIVE-INTEL Wave 6")
    registration = source.index("board_shadow.register_challenger(", marker)
    native_block = source[marker:registration]
    assert "load_a_twin_closes" in native_block
    assert 'store.read("china_search", "closes")' not in native_block

# ---------------------------------------------------------------------------
# Wave 7 — same-population HK-native rank races (H3 / X1), zero authority
# ---------------------------------------------------------------------------
def _native_family_rows_for_rank_race():
    return {
        "AAA.HK": {
            "h3_ah_discount_status": hki.ACCRUING,
            "h3_ah_discount_value": 0.90,
            "x1_atwin_momentum_status": hki.ACCRUING,
            "x1_atwin_momentum_value": 1.40,
        },
        "BBB.HK": {
            "h3_ah_discount_status": hki.ACCRUING,
            "h3_ah_discount_value": 0.55,
            "x1_atwin_momentum_status": hki.ACCRUING,
            "x1_atwin_momentum_value": 0.20,
        },
        "STALE.HK": {
            "h3_ah_discount_status": hki.STALE,
            "h3_ah_discount_value": 0.99,
            "x1_atwin_momentum_status": hki.STALE,
            "x1_atwin_momentum_value": 3.0,
        },
        "PARTIAL.HK": {
            "h3_ah_discount_status": hki.PARTIAL,
            "h3_ah_discount_value": None,
            "x1_atwin_momentum_status": hki.PARTIAL,
            "x1_atwin_momentum_value": None,
        },
        "UNAVAILABLE.HK": {
            "h3_ah_discount_status": hki.UNAVAILABLE,
            "h3_ah_discount_value": None,
            "x1_atwin_momentum_status": hki.UNAVAILABLE,
            "x1_atwin_momentum_value": None,
        },
        "NA.HK": {
            "h3_ah_discount_status": hki.NOT_APPLICABLE,
            "h3_ah_discount_value": None,
            "x1_atwin_momentum_status": hki.NOT_APPLICABLE,
            "x1_atwin_momentum_value": None,
        },
        "OFFLIST.HK": {
            "h3_ah_discount_status": hki.ACCRUING,
            "h3_ah_discount_value": 1.0,
            "x1_atwin_momentum_status": hki.ACCRUING,
            "x1_atwin_momentum_value": 9.0,
        },
    }


@pytest.mark.parametrize(
    ("family", "definition"),
    (
        ("h3_ah_discount", "hk_h3_ah_discount_rank_v1"),
        ("x1_atwin_momentum", "hk_x1_atwin_momentum_rank_v1"),
    ),
)
def test_w7_family_ranker_scores_only_accruing_incumbent_names(family, definition):
    calls = [
        {"ticker": t}
        for t in (
            "AAA.HK", "BBB.HK", "STALE.HK", "PARTIAL.HK",
            "UNAVAILABLE.HK", "NA.HK",
        )
    ]
    rows = _native_family_rows_for_rank_race()
    out = hki.rank_family_calls(calls, rows, family)

    assert hki.RANK_DEFINITIONS[family] == definition
    assert set(out) == {str(c["ticker"]) for c in calls}
    assert "OFFLIST.HK" not in out
    assert out["AAA.HK"]["score_raw"] > out["BBB.HK"]["score_raw"]
    assert out["AAA.HK"]["score_conservative"] is None
    assert out["BBB.HK"]["score_conservative"] is None
    for ticker in ("STALE.HK", "PARTIAL.HK", "UNAVAILABLE.HK", "NA.HK"):
        assert out[ticker] == {
            "score_raw": None,
            "score_conservative": None,
        }


def test_w7_family_ranker_rejects_unregistered_family():
    with pytest.raises(ValueError):
        hki.rank_family_calls(
            [{"ticker": "AAA.HK"}],
            _native_family_rows_for_rank_race(),
            "made_up_family",
        )


def test_w7_lane_a_persists_two_separate_same_population_rank_races(
    tmp_path, monkeypatch,
):
    _hk_on(monkeypatch)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        bs,
        "_read_incumbent_positions",
        lambda _market, _asof: {
            "AAA.HK": 1, "BBB.HK": 2, "STALE.HK": 3,
        },
    )
    calls = [
        {
            "ticker": "AAA.HK",
            "group": "buy",
            "board_definition": "hk_prophet_v2",
        },
        {
            "ticker": "BBB.HK",
            "group": "buy",
            "board_definition": "hk_prophet_v2",
        },
        {
            "ticker": "STALE.HK",
            "group": "watch",
            "board_definition": "hk_prophet_v2",
        },
    ]
    families = _native_family_rows_for_rank_race()
    for family, definition in hki.RANK_DEFINITIONS.items():
        bs.register_challenger(
            "HK",
            definition,
            rank_fn=lambda incoming, fam=family: hki.rank_family_calls(
                incoming, families, fam,
            ),
        )

    receipt = bs.write_shadow(calls, market="HK", asof=ASOF)
    assert receipt["written"] == 6  # 3 incumbent names x 2 separate rank races

    stored = pd.read_parquet(bs._lane_a_path("HK"))
    assert set(stored["challenger_definition"]) == set(
        hki.RANK_DEFINITIONS.values()
    )
    for definition in hki.RANK_DEFINITIONS.values():
        sub = stored[stored["challenger_definition"] == definition]
        assert set(sub["ticker"]) == {"AAA.HK", "BBB.HK", "STALE.HK"}
        assert set(sub["population_n"]) == {3}
        assert set(sub["challenger_offlist_n"]) == {0}
        assert sub["challenger_coverage"].nunique() == 1
        assert float(sub["challenger_coverage"].iloc[0]) == pytest.approx(2 / 3)
        ranked = sub.set_index("ticker")
        assert int(ranked.loc["AAA.HK", "challenger_rank"]) == 1
        assert int(ranked.loc["BBB.HK", "challenger_rank"]) == 2
        assert pd.isna(ranked.loc["STALE.HK", "challenger_rank"])
        assert pd.isna(ranked.loc["STALE.HK", "challenger_score_raw"])
        assert sub["challenger_score_conservative"].isna().all()


def test_w7_builder_registers_rank_races_only_after_publication_before_shadow_write():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    persist = source.index('(fdir / "hk_standouts.json").write_text(')
    h3 = source.index(
        'hk_native_intelligence.RANK_DEFINITIONS["h3_ah_discount"]'
    )
    x1 = source.index(
        'hk_native_intelligence.RANK_DEFINITIONS["x1_atwin_momentum"]'
    )
    shadow = source.index('board_shadow.write_shadow(calls, market="HK"')
    assert persist < h3 < shadow
    assert persist < x1 < shadow


# --- Wave 7b: broad-coverage beta-neutral RS SCREEN rank race ---
def test_w7b_bnrs_authority_is_explicitly_screen_not_selection_alpha():
    assert hki.BNRS_STATUS == "SCREEN"
    assert hki.BNRS_AUTHORITY == "candidate_intelligence_screen"
    assert hki.BNRS_DEFINITION == "hk_beta_neutral_rs_screen_rank_v1"
    assert hki.BNRS_DEFINITION not in set(hki.RANK_DEFINITIONS.values())


def test_w7b_bnrs_ranker_scores_exact_incumbent_population_missing_stays_null():
    calls = [
        {"ticker": "LEADER.HK"},
        {"ticker": "MID.HK"},
        {"ticker": "MISSING.HK"},
        {"ticker": "NAN.HK"},
        {"ticker": "LEADER.HK"},  # duplicate owner identity: first occurrence wins
        {"ticker": None},
    ]
    screen = {
        "LEADER.HK": 2.1,
        "MID.HK": 0.25,
        "NAN.HK": float("nan"),
        "OFFLIST.HK": 9.9,
    }
    out = hki.rank_bnrs_calls(calls, screen)
    assert list(out) == ["LEADER.HK", "MID.HK", "MISSING.HK", "NAN.HK"]
    assert "OFFLIST.HK" not in out
    assert out["LEADER.HK"]["score_raw"] == pytest.approx(2.1)
    assert out["MID.HK"]["score_raw"] == pytest.approx(0.25)
    assert out["MISSING.HK"] == {"score_raw": None, "score_conservative": None}
    assert out["NAN.HK"] == {"score_raw": None, "score_conservative": None}
    assert all(v["score_conservative"] is None for v in out.values())


def test_w7b_bnrs_ranker_persists_same_population_in_existing_lane_a(tmp_path, monkeypatch):
    _hk_on(monkeypatch)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        bs,
        "_read_incumbent_positions",
        lambda _market, _asof: {"LEADER.HK": 1, "MID.HK": 2, "MISS.HK": 3},
    )
    bs.CHALLENGER_REGISTRY.clear()
    calls = [
        {"ticker": "LEADER.HK", "group": "buy", "board_definition": "hk_prophet_v2"},
        {"ticker": "MID.HK", "group": "buy", "board_definition": "hk_prophet_v2"},
        {"ticker": "MISS.HK", "group": "watch", "board_definition": "hk_prophet_v2"},
    ]
    try:
        bs.register_challenger(
            "HK", hki.BNRS_DEFINITION,
            rank_fn=lambda incoming: hki.rank_bnrs_calls(
                incoming, {"LEADER.HK": 1.8, "MID.HK": 0.4}
            ),
        )
        receipt = bs.write_shadow(calls, market="HK", asof=ASOF)
        assert receipt["written"] == 3
        stored = pd.read_parquet(bs._lane_a_path("HK"))
        assert set(stored["ticker"]) == {"LEADER.HK", "MID.HK", "MISS.HK"}
        assert set(stored["population_n"]) == {3}
        assert set(stored["challenger_offlist_n"]) == {0}
        assert float(stored["challenger_coverage"].iloc[0]) == pytest.approx(2 / 3)
        by = stored.set_index("ticker")
        assert int(by.loc["LEADER.HK", "challenger_rank"]) == 1
        assert int(by.loc["MID.HK", "challenger_rank"]) == 2
        assert pd.isna(by.loc["MISS.HK", "challenger_rank"])
    finally:
        bs.CHALLENGER_REGISTRY.clear()


def test_w7b_builder_reuses_existing_bnrs_after_publication_before_shadow_write():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    compute = source.index("bnrs = (hk_stock_signals.beta_neutral_rs(")
    persist = source.index('(fdir / "hk_standouts.json").write_text(')
    definition = source.index("hk_native_intelligence.BNRS_DEFINITION", persist)
    shadow = source.index('board_shadow.write_shadow(calls, market="HK"')
    assert compute < persist < definition < shadow
    # The shadow race reuses the already-computed screen map; it must not mint
    # another beta-neutral calculation after publication.
    assert "beta_neutral_rs(" not in source[persist:shadow]


def test_w7b_bnrs_discovery_family_is_registered_typed_and_null_safe():
    assert hki.BNRS_FAMILY == "beta_neutral_rs"
    assert hki.BNRS_FAMILY in hki.DISCOVERY_FAMILIES
    assert hki.BNRS_FAMILY in bs.FAMILY_REGISTRY
    rows = hki.with_bnrs_evidence(
        {
            "LEADER.HK": {
                "h3_ah_discount_status": hki.NOT_APPLICABLE,
                "h3_ah_discount_value": None,
                "x1_atwin_momentum_status": hki.NOT_APPLICABLE,
                "x1_atwin_momentum_value": None,
            },
            "MISS.HK": {
                "h3_ah_discount_status": hki.NOT_APPLICABLE,
                "h3_ah_discount_value": None,
                "x1_atwin_momentum_status": hki.NOT_APPLICABLE,
                "x1_atwin_momentum_value": None,
            },
        },
        ["LEADER.HK", "MISS.HK"],
        {"LEADER.HK": 1.75},
    )
    assert rows["LEADER.HK"]["beta_neutral_rs_status"] == hki.BNRS_STATUS
    assert rows["LEADER.HK"]["beta_neutral_rs_value"] == pytest.approx(1.75)
    assert rows["MISS.HK"]["beta_neutral_rs_status"] == hki.UNAVAILABLE
    assert rows["MISS.HK"]["beta_neutral_rs_value"] is None
    assert "beta_neutral_rs_status" in hki.FAMILY_FIELDS
    assert "beta_neutral_rs_value" in hki.FAMILY_FIELDS


def test_w7b_discovery_candidate_carries_bnrs_without_changing_candidate_reason():
    evidence = {
        "washout_2w": {"LEADER.HK": True},
        "sig_verdict": {"LEADER.HK": {"eligible": False}},
        "native_families": {
            "LEADER.HK": {
                "beta_neutral_rs_status": hki.BNRS_STATUS,
                "beta_neutral_rs_value": 1.25,
            }
        },
    }
    row = hkdc.build_candidates(evidence, ASOF)[0]
    assert row["candidate_origin"] == "washout_reclaim"
    assert row["availability_status"] == hkdc.WAIT_CONFLUENCE
    assert row["beta_neutral_rs_status"] == hki.BNRS_STATUS
    assert row["beta_neutral_rs_value"] == pytest.approx(1.25)


def test_w7b_lane_b_persists_bnrs_family_in_existing_store(tmp_path, monkeypatch):
    _hk_on(monkeypatch)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(bs, "_read_incumbent_positions", lambda *_a, **_k: {})
    bs.CHALLENGER_REGISTRY.clear()
    raw = [{
        "session_date": ASOF,
        "security_ref_raw": "LEADER.HK",
        "candidate_origin": "ripening",
        "availability_status": hkdc.WAIT_CONFLUENCE,
        "availability_source": "hk_signal_gate",
        "beta_neutral_rs_status": hki.BNRS_STATUS,
        "beta_neutral_rs_value": 1.4,
    }]
    try:
        bs.register_challenger("HK", "bnrs_discovery_test", discovery_fn=lambda _asof: raw)
        receipt = bs.write_shadow([], market="HK", asof=ASOF)
        assert receipt["written"] == 1
        stored = pd.read_parquet(bs._lane_b_path("HK"))
        assert stored["beta_neutral_rs_status"].iloc[0] == hki.BNRS_STATUS
        assert pd.api.types.is_numeric_dtype(stored["beta_neutral_rs_value"])
        assert float(stored["beta_neutral_rs_value"].iloc[0]) == pytest.approx(1.4)
        assert bool(stored["visible_to_user"].iloc[0]) is False
        assert bool(stored["published_authority"].iloc[0]) is False
    finally:
        bs.CHALLENGER_REGISTRY.clear()


def test_w7b_builder_attaches_bnrs_to_native_family_bundle_before_discovery():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text()
    h3 = source.index("hk_native_intelligence.build_family_evidence")
    attach = source.index("hk_native_intelligence.with_bnrs_evidence", h3)
    bundle = source.index('"native_families": _hk_native_family_rows', attach)
    register = source.index("hk_native_intelligence.BNRS_DEFINITION", bundle)
    assert h3 < attach < bundle < register


# ---------------------------------------------------------------------------
# Owner-mediated Lane-B reader for downstream display-only consumers
# ---------------------------------------------------------------------------
def _reader_receipt(data_root: Path, **overrides) -> Path:
    path = data_root / "prophet_shadow" / "hk_discovery_receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "market": "HK",
        "as_of": ASOF,
        "registry_state": "wrote_n_rows n=2",
        "written": 2,
        "definitions": ["hk_discovery_v1"],
        "challenger_failures": [],
        "stamped_at": ASOF + "T12:00:00+00:00",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _reader_store(data_root: Path, rows: list[dict]) -> Path:
    path = data_root / "prophet_shadow" / "hk_discovery.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _reader_row(date: str, ticker: str, *, definition: str = "hk_discovery_v1") -> dict:
    return {
        "session_date": date,
        "market": "HK",
        "security_ref": ticker,
        "security_ref_raw": ticker,
        "ref_collision_n": 1,
        "challenger_definition": definition,
        "candidate_origin": "washout_reclaim",
        "availability_status": hkdc.WAIT_CONFLUENCE,
        "availability_source": "hk_signal_gate",
        "visible_to_user": False,
        "published_authority": False,
        "stamped_at": ASOF + "T12:00:00+00:00",
    }


def test_discovery_reader_returns_exact_receipt_epoch_in_store_order(_isolated_registry):
    root = _isolated_registry
    _reader_receipt(root)
    _reader_store(root, [
        _reader_row(ASOF, "BBB.HK"),
        _reader_row(ASOF, "AAA.HK"),
    ])
    result = bs.read_discovery_snapshot("hk", "hk_discovery_v1")
    assert result["available"] is True
    assert result["reason"] == "ok"
    assert result["as_of"] == ASOF
    assert [row["security_ref_raw"] for row in result["records"]] == ["BBB.HK", "AAA.HK"]
    assert all(set(row) == set(bs._DISCOVERY_READER_FIELDS) for row in result["records"])


def test_discovery_reader_observed_zero_never_substitutes_older_rows(_isolated_registry):
    root = _isolated_registry
    _reader_receipt(root, registry_state="wrote_n_rows n=0", written=0)
    prior_asof = (dt.date.fromisoformat(ASOF) - dt.timedelta(days=1)).isoformat()
    _reader_store(root, [_reader_row(prior_asof, "OLD.HK")])
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result == {
        "available": True,
        "reason": "observed_zero",
        "as_of": ASOF,
        "records": [],
    }


def test_discovery_reader_rejects_store_newer_than_receipt(_isolated_registry):
    root = _isolated_registry
    _reader_receipt(root)
    future_asof = (dt.date.fromisoformat(ASOF) + dt.timedelta(days=1)).isoformat()
    _reader_store(root, [_reader_row(future_asof, "FUTURE.HK")])
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == "store_newer_than_receipt"


@pytest.mark.parametrize(
    ("receipt_overrides", "reason"),
    [
        ({"definitions": ["other"]}, "definition_not_in_receipt"),
        ({"registry_state": "error"}, "receipt_not_successful"),
        ({"challenger_failures": [{"definition": "hk_discovery_v1", "error": "x"}]}, "challenger_failed"),
        ({"as_of": ""}, "receipt_asof_missing"),
        ({"market": "CA"}, "receipt_market_mismatch"),
        ({"challenger_failures": "bad"}, "receipt_failures_malformed"),
    ],
)
def test_discovery_reader_receipt_failures_are_explicit(
    _isolated_registry, receipt_overrides, reason
):
    root = _isolated_registry
    _reader_receipt(root, **receipt_overrides)
    _reader_store(root, [_reader_row(ASOF, "AAA.HK")])
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == reason
    assert result["records"] == []


def test_discovery_reader_missing_receipt_and_store_fail_closed(_isolated_registry):
    root = _isolated_registry
    assert bs.read_discovery_snapshot("HK", "hk_discovery_v1")["reason"] == "receipt_missing"
    _reader_receipt(root, registry_state="wrote_n_rows n=0", written=0)
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == "store_missing"


def test_discovery_reader_rejects_missing_columns_and_unreadable_receipt(_isolated_registry):
    root = _isolated_registry
    receipt = _reader_receipt(root)
    path = root / "prophet_shadow" / "hk_discovery.parquet"
    pd.DataFrame([{"session_date": ASOF}]).to_parquet(path, index=False)
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == "store_missing_columns"

    receipt.write_text("{broken", encoding="utf-8")
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == "receipt_unreadable"


def test_discovery_reader_rejects_malformed_store_session(_isolated_registry):
    root = _isolated_registry
    _reader_receipt(root)
    _reader_store(root, [_reader_row("not-a-date", "AAA.HK")])
    result = bs.read_discovery_snapshot("HK", "hk_discovery_v1")
    assert result["available"] is False
    assert result["reason"] == "store_session_malformed"


# ---------------------------------------------------------------------------
# Pick Lab owner-session clock — never fabricate a denominator epoch
# ---------------------------------------------------------------------------
def test_pick_lab_producer_never_falls_back_to_wall_clock():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text(encoding="utf-8")
    start = source.index("# ---- HK PICK LAB PRODUCER BLOCK")
    end = source.index("# ----", start + 32) if "# ----" in source[start + 32:] else len(source)
    block = source[start:end]
    assert "_producer_asof = str(as_of).strip() if as_of and str(as_of).strip() else None" in block
    assert "Timestamp.utcnow().date()" not in block
    assert 'board_shadow.write_shadow(calls, market="HK", asof=str(as_of) if as_of else None)' in source


def test_pick_lab_missing_owner_session_skips_snapshot_and_velocity_sinks():
    source = (ROOT / "scripts" / "build_hk_library.py").read_text(encoding="utf-8")
    start = source.index("# -- 5. Assemble snapshot rows")
    end = source.index("# -- 8.", start) if "# -- 8." in source[start:] else source.index("except Exception", start)
    block = source[start:end]
    assert "if _producer_asof is None:" in block
    assert "_snap_rows = []" in block
    assert "owner session unavailable" in block
    assert "else:\n            _snap_rows = build_hk_core_rows(" in block
    assert "if _snap_rows:" in block
    assert "if _snap_rows and _is_asia_lane_lib:" in block
    assert "write_snapshot(" in block
    assert "build_velocity_desk_artifact(" in block
