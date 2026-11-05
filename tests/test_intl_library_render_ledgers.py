"""INTL library forward-ledger lane gate — render-only bug repair (2026-11-04).

scripts/build_intl_library.py advances TWO data/ forward ledgers: the name-score
CALL ledger (engine/name_score_grader.append_name_calls) and the B2 conviction
accrual (engine/conviction_accrual.archive_member_conviction). Both were written on
EVERY lane that runs the build — the render / engine-render / intraday lanes and the
closing bell run the intl build too, not just the nightly collect lane. House law
(engine/risk_radar_intl_audit.ledger_lane_armed): nightly is the SOLE advancer of
data/ forward ledgers. On the other lanes the board still renders, but no forward
ledger may advance — a mid-session append is PIT-inconsistent and, being
idempotent-by-asof, would permanently displace the nightly row.

The repair gates the two ARCHIVAL WRITES behind the canonical predicate; the library
ANALYSIS / RENDER / DISPLAY path is untouched.

This suite proves the repair at the actual seam without running the (very expensive)
988-name analysis pipeline:

  GROUP 1 — the gate IS the canonical predicate, REUSED and not re-implemented: the
            script's helper answers exactly like
            engine.risk_radar_intl_audit.ledger_lane_armed over the whole env matrix
            (nightly / legacy US_LANE alias / render / engine-render / intraday /
            empty / unknown / COLLECT_LANE precedence), and its CODE must not re-read
            the lane env vars itself.

  GROUP 2 — EXECUTION of the real guarded blocks: the two writer blocks are lifted out
            of main() by AST (the exact source text that ships), executed with the
            writers stubbed, and asserted against the lane matrix:
              off-lane (render / engine-render / intraday / closing-bell / empty /
              unknown / legacy render): NEITHER writer is called;
              nightly: BOTH writers are called exactly as before the repair — same
              market / region / as-of / session_keyed arguments.
            A sensitivity check neutralises the gate in a COPY of the block and shows
            the same harness DOES observe the writer call, so the off-lane assertions
            above are not vacuous.

  GROUP 3 — the DISPLAY computation is NOT gated: the INTL displayed score
            (POTENTIAL score / band / rank_pctile) is still computed on a render
            lane — only the archival writes are gated.

  GROUP 4 — source-level pins: both writer call sites sit inside the
            _ledger_lane_armed() branch (the house idiom, mirroring
            tests/test_risk_radar_intl_profiles.py::test_cn_hk_ca_build_appenders_lane_gated),
            and the repair adds no new store / registry / receipt.

Nothing here touches the repo's data/ or site/ trees: both writers are stubbed and
the analysis pipeline never runs.

NOTE tests/conftest.py arms COLLECT_LANE=nightly autouse — every case below sets or
pops BOTH lane vars explicitly, so the assertions hold with or without that fixture.

Run: python3 -m pytest tests/test_intl_library_render_ledgers.py -q
"""
from __future__ import annotations

import ast
import logging
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import engine  # noqa: E402
from engine import risk_radar_intl_audit as rra  # noqa: E402
from scripts import build_intl_library as bil  # noqa: E402

_SCRIPT = Path(bil.__file__).resolve()
_SRC = _SCRIPT.read_text(encoding="utf-8")
_TREE = ast.parse(_SRC)
_PARENTS = {child: parent for parent in ast.walk(_TREE) for child in ast.iter_child_nodes(parent)}

_NAME_SCORE_WRITER = "name_score_grader.append_name_calls"
_ACCRUAL_WRITER = "conviction_accrual.archive_member_conviction"


# ── helpers ────────────────────────────────────────────────────────────────────
def _main_node() -> ast.FunctionDef:
    for node in _TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError(f"{_SCRIPT} has no main()")


def _segment(node: ast.AST) -> str:
    """The exact source text of a node (line range — keeps the original indentation)."""
    return "\n".join(_SRC.splitlines()[node.lineno - 1: node.end_lineno])


def _block_containing(marker: str) -> ast.AST:
    """The one try-block in main() whose source text contains `marker`."""
    cands = [n for n in ast.walk(_main_node())
             if isinstance(n, ast.Try) and marker in _segment(n)]
    assert len(cands) == 1, (
        f"expected exactly one try-block containing {marker!r} in main(), found {len(cands)}")
    return cands[0]


def _display_block() -> ast.AST:
    """The loop that computes the INTL DISPLAYED score (POTENTIAL -> score/band)."""
    cands = [n for n in ast.walk(_main_node())
             if isinstance(n, ast.For) and "rank_pctile" in _segment(n)]
    assert len(cands) == 1, (
        f"expected exactly one display-score loop in main(), found {len(cands)}")
    return cands[0]


def _run(node: ast.AST, ns: dict) -> None:
    """Execute a real source fragment (as parsed from the shipping script)."""
    mod = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(mod)
    exec(compile(mod, str(_SCRIPT), "exec"), ns)  # noqa: S102 — the script's own source


def _dotted(node: ast.AST) -> str:
    """`a.b.c` for an attribute chain rooted at a Name."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_lane_gated(call: ast.AST) -> bool:
    """True when `call` sits inside an `if` whose test consults the lane gate."""
    node: ast.AST | None = call
    while node is not None:
        node = _PARENTS.get(node)
        if node is None:
            return False
        if isinstance(node, ast.If):
            for sub in ast.walk(node.test):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == "_ledger_lane_armed"):
                    return True
    return False


def _set_lane(monkeypatch, lane: str | None = None, legacy: str | None = None) -> None:
    """Pin the collect lane exactly — BOTH vars are popped first (conftest arms
    COLLECT_LANE=nightly autouse) so an off-lane case is genuinely off-lane."""
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    if lane is not None:
        monkeypatch.setenv("COLLECT_LANE", lane)
    if legacy is not None:
        monkeypatch.setenv("US_LANE", legacy)


class _StubGrader:
    """Stand-in for engine.name_score_grader — records appends, writes nothing."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def append_name_calls(self, calls, market="CN", asof=None, session_keyed=True):
        self.calls.append({"calls": list(calls), "market": market, "asof": asof,
                            "session_keyed": session_keyed})
        return len(calls)


class _StubAccrual:
    """Stand-in for engine.conviction_accrual — records archives, writes nothing."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def archive_member_conviction(self, region, profiles, *, asof=None, archive_dir=None):
        self.calls.append({"region": region, "profiles": profiles, "asof": asof})
        return True


@pytest.fixture
def stub_writers(monkeypatch):
    """Replace both writers with recording stubs, engine-wide, so a guarded block
    that re-imports them still cannot touch a real ledger."""
    grader, accrual = _StubGrader(), _StubAccrual()
    monkeypatch.setattr(engine, "name_score_grader", grader, raising=False)
    monkeypatch.setattr(engine, "conviction_accrual", accrual, raising=False)
    return grader, accrual


def _gate() -> bool:
    """The script's OWN lane gate when it has one; the canonical predicate
    otherwise — so this harness still OBSERVES an unguarded writer in a script
    that has not been repaired yet (the block under test simply never asks)."""
    helper = getattr(bil, "_ledger_lane_armed", None)
    return helper() if callable(helper) else rra.ledger_lane_armed()


def _name_score_ns(grader: _StubGrader) -> dict:
    """Namespace for the name-score append block."""
    return {
        "log": logging.getLogger("intl_library_render_ledgers"),
        "name_score_grader": grader,
        "_ledger_lane_armed": _gate,
        "_icalls": [{"ticker": "AAA", "score": 71.0, "tier": "buy", "fuel": 0.5,
                     "trigger": "breakout", "level": 12.3}],
        "_intl_session_asof": bil._intl_session_asof,
        "alpha": None,
        "to_write": [("AAA", {"asof": "2026-11-04"})],
    }


def _accrual_ns(accrual: _StubAccrual) -> dict:
    """Namespace for the B2 accrual block."""
    return {
        "log": logging.getLogger("intl_library_render_ledgers"),
        "conviction_accrual": accrual,
        "_ledger_lane_armed": _gate,
        "_session_asof": "2026-11-04",
        "profiles": {"AAA": {"potential": {"score": 71.0}}},
    }


# ── GROUP 1 — the gate IS the canonical predicate ──────────────────────────────
_LANE_MATRIX = [
    ({"COLLECT_LANE": "nightly"}, True),
    ({"COLLECT_LANE": "NIGHTLY"}, True),
    ({"US_LANE": "nightly"}, True),
    ({"COLLECT_LANE": "render"}, False),
    ({"COLLECT_LANE": "engine-render"}, False),
    ({"COLLECT_LANE": "intraday"}, False),
    ({"COLLECT_LANE": "closing-bell"}, False),
    ({"COLLECT_LANE": "unknown"}, False),
    ({"COLLECT_LANE": ""}, False),
    ({"US_LANE": "render"}, False),
    ({"US_LANE": "unknown"}, False),
    ({}, False),
    # COLLECT_LANE is read first and wins over the legacy alias
    ({"COLLECT_LANE": "render", "US_LANE": "nightly"}, False),
]


@pytest.mark.parametrize("env,expected", _LANE_MATRIX)
def test_gate_helper_matches_the_canonical_predicate(monkeypatch, env, expected):
    """The script's helper must answer exactly like
    engine.risk_radar_intl_audit.ledger_lane_armed (reused, not re-implemented)."""
    _set_lane(monkeypatch, lane=env.get("COLLECT_LANE"), legacy=env.get("US_LANE"))
    assert rra.ledger_lane_armed() is expected, f"canonical predicate moved for {env}"
    assert bil._ledger_lane_armed() is expected, (
        f"intl library gate disagrees with the canonical predicate for {env}")


def test_gate_helper_delegates_without_reimplementing_the_lane_rule():
    """The lane rule lives in the canonical home only — the helper must not read
    the lane env vars itself."""
    helper = next((n for n in _TREE.body
                   if isinstance(n, ast.FunctionDef) and n.name == "_ledger_lane_armed"), None)
    assert helper is not None, "scripts/build_intl_library.py must expose _ledger_lane_armed()"
    code = "\n".join(
        _segment(n) for n in helper.body
        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)))
    assert "risk_radar_intl_audit" in code, (
        "the gate must be delegated to engine.risk_radar_intl_audit.ledger_lane_armed")
    assert "ledger_lane_armed" in code
    for forbidden in ("COLLECT_LANE", "US_LANE", "environ"):
        assert forbidden not in code, (
            f"the lane rule must not be re-implemented here ({forbidden!r} in "
            "_ledger_lane_armed)")


# ── GROUP 2 — the guarded blocks, executed ─────────────────────────────────────
_OFF_LANE = [
    {"COLLECT_LANE": "render"},
    {"COLLECT_LANE": "engine-render"},
    {"COLLECT_LANE": "intraday"},
    {"COLLECT_LANE": "closing-bell"},
    {"COLLECT_LANE": "unknown"},
    {"COLLECT_LANE": ""},
    {"US_LANE": "render"},
    {},
]


@pytest.mark.parametrize("env", _OFF_LANE)
def test_off_lane_advances_neither_forward_ledger(monkeypatch, stub_writers, env):
    """Render / engine-render / intraday / closing-bell / empty / unknown lanes
    must call NEITHER archival writer — the board still renders, but no forward
    ledger advances."""
    grader, accrual = stub_writers
    _set_lane(monkeypatch, lane=env.get("COLLECT_LANE"), legacy=env.get("US_LANE"))
    _run(_block_containing("append_name_calls"), _name_score_ns(grader))
    _run(_block_containing("archive_member_conviction"), _accrual_ns(accrual))
    assert grader.calls == [], (
        f"off-lane {env} advanced the name-score call ledger: {grader.calls}")
    assert accrual.calls == [], (
        f"off-lane {env} advanced the B2 conviction accrual ledger: {accrual.calls}")


def test_nightly_preserves_the_existing_append_behaviour(monkeypatch, stub_writers):
    """Nightly is the ONLY lane that advances the ledgers, and it advances them
    exactly as before the repair (same market / region / as-of / session_keyed)."""
    grader, accrual = stub_writers
    _set_lane(monkeypatch, lane="nightly")

    ns = _name_score_ns(grader)
    _run(_block_containing("append_name_calls"), ns)
    assert len(grader.calls) == 1, f"nightly must append the name-score calls once: {grader.calls}"
    call = grader.calls[0]
    assert call["market"] == "INTL"
    assert call["asof"] == "2026-11-04"
    assert call["session_keyed"] is True
    assert call["calls"] == ns["_icalls"]

    ans = _accrual_ns(accrual)
    _run(_block_containing("archive_member_conviction"), ans)
    assert len(accrual.calls) == 1, f"nightly must archive the B2 accrual once: {accrual.calls}"
    arch = accrual.calls[0]
    assert arch["region"] == "intl"
    assert arch["asof"] == "2026-11-04"
    assert arch["profiles"] is ans["profiles"]


def test_the_execution_harness_sees_an_unguarded_writer(monkeypatch, stub_writers):
    """Sensitivity proof: with the lane gate neutralised in a COPY of the block
    (the pre-repair shape), the same harness DOES observe the writer call — so the
    off-lane assertions above are not vacuous."""
    grader, accrual = stub_writers
    _set_lane(monkeypatch, lane="render")
    block = _block_containing("append_name_calls")
    src = _segment(block)
    mutated = src.replace("_ledger_lane_armed()", "True")
    assert mutated != src, "the name-score block no longer consults the lane gate"
    _run(ast.parse(textwrap.dedent(mutated)).body[0], _name_score_ns(grader))
    assert len(grader.calls) == 1, (
        "an ungated writer must be observable by this harness — the off-lane "
        "assertions would otherwise pass for the wrong reason")


# ── GROUP 3 — display computation is NOT gated ─────────────────────────────────
def test_display_score_is_computed_off_lane(monkeypatch, stub_writers):
    """The INTL DISPLAYED score (POTENTIAL score / band / rank_pctile) is display
    work: it is computed on every lane, gated or not."""
    grader, accrual = stub_writers
    _set_lane(monkeypatch, lane="render")
    rec = {
        "conviction": {
            "score": 61.0, "band": "neutral", "band_en": "neutral", "band_zh": "中性",
            "notes": [{"kind": "rank", "text": "percentile note"},
                      {"kind": "anticipation", "text": "cone note"}],
            "potential": {"score": 71.0, "band": "buy", "band_en": "buy", "band_zh": "买入",
                          "call": {"ticker": "AAA"}},
        },
        "tech": {"price": 12.3},
    }
    ns = {"to_write": [("AAA", rec)], "_icalls": []}
    _run(_display_block(), ns)
    conv = rec["conviction"]
    assert conv["score"] == 71.0, "the displayed score must still be the POTENTIAL score"
    assert conv["rank_pctile"] == 61.0, "the comp-z percentile must still be kept"
    assert conv["band"] == "buy" and conv["band_en"] == "buy" and conv["band_zh"] == "买入"
    assert [n["kind"] for n in conv["notes"]] == ["anticipation"], (
        "the rank note is dropped from the displayed notes (unchanged behaviour)")
    assert ns["_icalls"] == [{"ticker": "AAA", "level": 12.3}], (
        "the POTENTIAL call list must still be collected off-lane")
    # display work writes nothing: the archival writers stay untouched
    assert grader.calls == [] and accrual.calls == []


# ── GROUP 4 — source-level pins ───────────────────────────────────────────────
def test_both_forward_ledger_writers_sit_inside_the_lane_gate():
    """House law: nightly is the SOLE advancer of data/ forward ledgers — both
    writer call sites must sit inside the _ledger_lane_armed() branch."""
    seen: dict[str, list[ast.AST]] = {}
    for node in ast.walk(_main_node()):
        if isinstance(node, ast.Call):
            dotted = _dotted(node.func)
            if dotted in (_NAME_SCORE_WRITER, _ACCRUAL_WRITER):
                seen.setdefault(dotted, []).append(node)
    assert set(seen) == {_NAME_SCORE_WRITER, _ACCRUAL_WRITER}, (
        f"expected both forward-ledger writer call sites in main(), found {sorted(seen)}")
    for dotted, calls in seen.items():
        assert len(calls) == 1, f"{dotted} must have exactly one call site, found {len(calls)}"
        assert _is_lane_gated(calls[0]), (
            f"{dotted} must sit INSIDE the _ledger_lane_armed() branch — a forward "
            "ledger may only advance on the nightly lane")


def test_repair_adds_no_store_registry_or_receipt():
    """The repair is a gate, not a new writer: the library still only READS the
    store, and no second copy of the lane rule is introduced."""
    assert "store.write" not in _SRC, "the intl library must not write the store directly"
    assert "store.append" not in _SRC
    helpers = [n for n in _TREE.body
               if isinstance(n, ast.FunctionDef) and n.name == "_ledger_lane_armed"]
    assert len(helpers) == 1, "exactly one lane-gate helper — no second copy of the lane rule"
    canonical = [n for n in ast.walk(helpers[0])
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "ledger_lane_armed"]
    assert len(canonical) == 1, "the helper must delegate to the canonical predicate once"
    gate_calls = [n for n in ast.walk(_main_node())
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                  and n.func.id == "_ledger_lane_armed"]
    assert len(gate_calls) == 2, (
        "the gate must guard exactly the two forward-ledger writers, found "
        f"{len(gate_calls)}")
