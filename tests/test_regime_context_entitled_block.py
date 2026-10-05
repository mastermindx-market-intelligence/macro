"""Additive regime-detail block: entitled digest = base digest + block.

K1 invariant: deleting the regime-detail lines from the paid digest must
yield EXACTLY the free digest (same base sections, same text, same order).
REGIME_DETAIL never participates in the base drop loop — the entitled path
renders the block under its own budget and splices it at its existing slot.

The test deliberately populates every base section with enough payload to
exceed the base char budget once the block is added, so any drop-loop
participation by REGIME_DETAIL would surface as a missing base section in
the paid digest that the free digest still has.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.neuralweb import market_packet as mp
from engine.neuralweb import regime_context as rc

# Reuse the existing fixture style from test_regime_context.py — the regime
# sources() helper there is the proven shape that drives a populated packet.
from tests.test_regime_context import sources as _regime_sources

NOW = datetime(2026, 10, 1, 23, 0, tzinfo=timezone.utc)

# A bounded marker line that the block ALWAYS emits; lets us isolate it.
REGIME_DETAIL_MARKER = "REGIME DETAIL"


# ---------------------------------------------------------------------------
# Payload builders — self-contained; no apt-get mirror to the rich fixtures.
# ---------------------------------------------------------------------------

def _iso(dt):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _quotes():
    return {
        "asof": _iso(NOW),
        "indices": {
            "SPX": {"last": 6500.21, "chg": 0.42, "prev_close": 6472.41},
            "NDX": {"last": 23500.0, "chg": 0.61, "prev_close": 23357.0},
            "DJI": {"last": 46000.0, "chg": 0.18, "prev_close": 45917.0},
            "RUT": {"last": 2400.0, "chg": -0.05, "prev_close": 2401.2},
            "VIX": {"last": 18.21, "chg": -2.34, "prev_close": 18.65},
        },
        "session": {"region": "us", "open": True,
                    "local_time": "2026-10-01 16:00 EDT"},
    }


def _breadth():
    return {
        "schema": "live.breadth.v1", "asof": _iso(NOW),
        "delay_min": 3, "session": "post",
        "tiers": [
            {"key": "large", "univ": "S&P 500", "adv": 322, "dec": 179,
             "adv_pct": 64.27, "nh": 33, "nl": 2},
            {"key": "mid", "univ": "S&P 400", "adv": 245, "dec": 155,
             "adv_pct": 61.25},
            {"key": "small", "univ": "S&P 600", "adv": 362, "dec": 239,
             "adv_pct": 60.23},
        ],
    }


def _risk():
    return {
        "asof": _iso(NOW), "session": {"region": "us", "open": True,
                                       "local_time": "2026-10-01 16:00 EDT"},
        "stale": False, "stale_reason": "",
        "shock_active": True,
    }


def _drivers():
    # Many drivers → big drivers block → bump the base text above 3,800.
    LONG = (
        "hawkish repricing, cuts priced out, long-end bear steepening, real "
        "yields rolling over, term premium widening, breakevens sticky, "
        "breadth narrowing, megacap leadership, vol suppressed, credit "
        "spreads tight, liquidity ample, fiscal impulse negative, dollar "
        "bid, oil firm, gold bid, copper bid, semis bid, banks bid, "
        "regional rotation away from EU, EM bid into copper and semis, "
        "HY tight, IG tight, TIPS breakevens sticky, 5y5y steepening, "
        "real-rate peak confirmed, term-premium decomposition shows risk "
        "premium dominant, supply dynamics muted, dealer gamma pinned at "
        "spot, vol-of-vol low, skew negative, put-call elevated at "
        "downside strikes only, breadth-breadth ratio rolling, "
        "leadership concentration narrowing to AI hardware + semis, "
        "consumer-discretionary breadth firm, staples lagging, "
        "industrials lagging, utilities bid defensively"
    )
    return {
        "asof": "2026-10-01", "window_d": 5,
        "verdict": "clear", "verdict_zh": "明确",
        "primary_label": "Fed repricing",
        "primary_label_zh": "美联储重定价",
        "direction": LONG,
        "direction_zh": "鹰派重定价，长期端熊市陡峭化，实际收益率回落，期限溢价扩大，通胀保值债券粘性，广度收窄，超大盘领导地位，波动率受抑制，信贷利差紧缩，流动性充足，财政刺激为负，美元被买入，原油坚定，企稳，铜被买入，企稳，半导体被买入，银行被买入",
        "confidence": "medium",
        "drivers": [
            {"label": f"Driver {i}", "label_zh": f"驱动 {i}",
             "direction": LONG, "direction_zh": LONG,
             "magnitude": "moderate", "confidence": "medium"}
            for i in range(6)
        ],
    }


def _shock():
    return {"schema": "shock_deescalation.v1", "active": True,
            "since": "2026-09-28", "expires": "2026-10-05",
            "note": "Shock de-escalation window: scores capped while the tape resets."}


def _wires():
    return {"schema": "wires.v1",
            "updated_at": _iso(NOW),
            "items": [
                {"id": "a", "ts": _iso(NOW), "en": "Fed holds rates",
                 "zh": "美联储维持利率", "salience": 90, "class": "policy",
                 "source_name": "wire", "corroboration": "2 sources"},
                {"id": "b", "ts": _iso(NOW), "en": "Chipmaker guides lower",
                 "zh": "芯片制造商下调指引", "salience": 50, "class": "earnings",
                 "source_name": "wire", "corroboration": "1 source"},
            ]}


def _master_brief():
    LONG = (
        "credit conditions remain benign, NFCI well below zero, HY OAS "
        "anchored near structural tights, leveraged-loan default rate at "
        "cycle lows, distressed exchange at multi-year lows, recovery rates "
        "normal, lender appetite ample, deal calendar busy, refi wall light, "
        "M&A pipeline rebuilding, IPO market reopening with quality bias, "
        "secondary trading active, block prints rare, vol-of-vol subdued, "
        "tail hedge demand tepid, systematic trend followers long, CTAs at "
        "extremes, vol-control strategies rebalancing, risk-parity tilting "
        "to credit and equity, macro hedge funds net long, pension allocator "
        "flows constructive, retail sentiment surveys improving, "
        "household equity allocation rising, fund flows positive across "
        "equity ETFs, credit ETFs, commodity ETFs, money market funds losing"
    )
    return {
        "as_of": "2026-10-01", "state_asof": "2026-10-01",
        "regime_read": LONG,
        "summary": LONG,
        "rotation_check": LONG,
        "forward_read": LONG,
        "watch_items": [LONG, LONG, LONG, LONG],
        "forward_watch": [LONG, LONG, LONG, LONG],
        "conflicts": [LONG, LONG, LONG, LONG],
    }


def _world_state():
    return {"as_of": "2026-10-01", "narrative": "World-state prose."}


def _rates():
    return {"as_of": "2026-10-01",
            "board": {
                "rate_path_row": {"asof": "2026-10-01", "policy_rate": 3.63,
                                  "implied_path": {"m1": 3.67, "m3": 3.84,
                                                   "m12": 4.15}},
                "inflation_row": {"breakeven_10y": 2.2,
                                   "regime": "above target"},
                "risk_row": {"curve_regime_key": "bear_steepener",
                             "curve_regime_label_en": "Bear steepener",
                             "term_premium_dir": "rising"},
            }}


def _vol():
    return {"schema": "vol_regime.v1", "asof": "2026-10-01",
            "snapshot": {"available": True, "asof": "2026-10-01",
                         "regime": "normalizing", "risk_score": 0.155,
                         "vix": 18.21, "ts_slope_state": "contango",
                         "move": 76.1}}


def _crossasset():
    return {"date": "2026-10-01", "asof": "2026-10-01",
            "regime": "mixed / no clear trend",
            "correlation": "concentrated",
            "favored": ["equity_us", "equity_sm", "copper", "dollar",
                        "equity_intl"]}


def _basket_pulse():
    return {
        "schema": "basket_pulse.v1", "market": "us", "session": "rth",
        "mode": "live", "as_of_quotes": _iso(NOW),
        "as_of_utc": _iso(NOW),
        "delay_min_median": 1.0, "coverage_pct": 99.4,
        "baskets": [
            {"id": "ai_semiconductors", "live_ew_chg_pct": 2.1,
             "tape_rank": 1},
            {"id": "us_sector_energy", "live_ew_chg_pct": 1.83,
             "tape_rank": 2},
            {"id": "power_grid", "live_ew_chg_pct": 1.2, "tape_rank": 3},
            {"id": "retail", "live_ew_chg_pct": 0.4, "tape_rank": 4},
            {"id": "big_pharma", "live_ew_chg_pct": 0.0, "tape_rank": 5},
            {"id": "insurance", "live_ew_chg_pct": None, "tape_rank": None},
            {"id": "housing", "live_ew_chg_pct": -0.35, "tape_rank": 6},
            {"id": "us_sector_utilities", "live_ew_chg_pct": -0.7,
             "tape_rank": 7},
            {"id": "us_sector_staples", "live_ew_chg_pct": -0.92,
             "tape_rank": 8},
            {"id": "memory_storage", "live_ew_chg_pct": -1.42,
             "tape_rank": 9},
        ],
    }


def _watch():
    # The WATCH source path is `site/basket_pulse.json` per test fixtures; we
    # don't need a separate file — build_packet handles a missing watch
    # silently. To prove the drop-loop invariant at the boundary, we want the
    # WATCH section to render — but build_packet populates it from sources
    # internal to the engine. If absent, the section is "" and the render
    # loop skips it (no participation in budget).
    return None


def _pressure():
    return {"asof": _iso(NOW), "n_up": 6, "n_down": 14,
            "broad_selloff": False,
            "rows": [
                {"name": "Acme Co", "move": "-8.1%", "vol": "2.3x",
                 "vs": "peers -0.4%", "family": "Energy",
                 "state": "below 50dma"},
            ]}


def _desk_payload():
    # Pad DESK with multiple long reads to push base text above 3,800.
    LONG_LINE = (
        "credit conditions remain benign, NFCI well below zero, HY OAS "
        "anchored near structural tights, leveraged-loan default rate at "
        "cycle lows, distressed exchange at multi-year lows, recovery rates "
        "normal, lender appetite ample, deal calendar busy, refi wall light, "
        "M&A pipeline rebuilding, IPO market reopening with quality bias, "
        "secondary trading active, block prints rare, vol-of-vol subdued, "
        "tail hedge demand tepid, systematic trend followers long, CTAs at "
        "extremes, vol-control strategies rebalancing, risk-parity tilting "
        "to credit and equity, macro hedge funds net long, pension allocator "
        "flows constructive, retail sentiment surveys improving, "
        "household equity allocation rising, fund flows positive across "
        "equity ETFs, credit ETFs, commodity ETFs, money market funds losing"
    )
    return {
        "asof": _iso(NOW),
        "reads": [
            ("Credit", LONG_LINE),
            ("Rates", LONG_LINE),
            ("Equity flow", LONG_LINE),
            ("FX", LONG_LINE),
        ],
    }


def _watch_payload():
    LONG = (
        "if AI hardware capex guidance disappoints, semis leadership rolls over; "
        "if HY OAS widens 30bp+, credit cycle turns; if NFCI crosses 0, "
        "financial conditions tighten materially; if 10Y nominal crosses 5%, "
        "equity multiples compress; if dollar breaks higher, EM and risk-on "
        "bid fades; if oil breaks out of range, inflation regime re-rates; "
        "if real 10Y rolls meaningfully lower, growth scare confirmed; "
        "if breadth fails to broaden, leadership narrows to a knife-edge"
    )
    return {
        "asof": _iso(NOW),
        "lines": [
            ("Watch", LONG),
            ("Cross-asset", LONG),
            ("Liquidity", LONG),
            ("Vol regime", LONG),
        ],
    }


# ---------------------------------------------------------------------------
# Per-test root mint
# ---------------------------------------------------------------------------

def _write_regime_sources(root):
    """Mirror the small `_write_sources` helper from test_regime_context.py,
    used here so the regime-context read actually succeeds."""
    sources_payload = _regime_sources()
    for key, rel in rc.SOURCE_PATHS.items():
        p = root / rel
        _write(p, sources_payload[key])


def _populate_root(root: Path):
    """Write every source needed to fill every base section."""
    live = root / "site" / "live"
    _write(live / "quotes.json", _quotes())
    _write(live / "breadth.json", _breadth())
    _write(live / "risk_state.json", _risk())
    _write(live / "market_drivers.json", _drivers())
    _write(live / "shock_state.json", _shock())
    _write(live / "wires.json", _wires())
    _write(root / "site" / "master_brief.json", _master_brief())
    _write(root / "data" / "neuralweb" / "world_state.json", _world_state())
    _write(root / "data" / "rates_command" / "latest.json", _rates())
    _write(root / "site" / "vol" / "regime.json", _vol())
    _write(root / "data" / "crossasset" / "latest.json", _crossasset())
    _write(live / "basket_pulse.json", _basket_pulse())
    _write(root / "data" / "price_pressure" / "latest.json", _pressure())
    _write_regime_sources(root)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.delenv(mp._LIVE_DIR_ENV, raising=False)
    monkeypatch.setattr(mp, "_VPS_LIVE_DIR",
                         tmp_path / "__no_such_vps_dir__")
    # Force _live_dir() to fall back to the tmp live dir we wrote.
    monkeypatch.setenv("MACRO_LIVE_DIR", str(tmp_path / "site" / "live"))
    mp._CACHE.clear()
    _populate_root(tmp_path)
    yield tmp_path
    mp._CACHE.clear()


_SECTION_PREFIXES = (
    "TAPE ", "CURVE ", "FLAG ", "FLAGS ", "SHOCK ", "EVENTS ", "DRIVERS ",
    "RATES ", "VOL ", "VOLATILITY ", "BREADTH ", "LEADERS ", "REGIONAL ",
    "CROSS-ASSET ", "CROSSASSET ", "CNBOARD ", "CN BOARD ", "DESK ", "WATCH ",
    "PRESSURE ", "REGIME DETAIL ", "REGIONAL BOARDS ",
)


def _strip_block(text: str) -> str:
    """Drop the entire REGIME_DETAIL section, including its multi-line body.

    The block starts at the line beginning with REGIME_DETAIL and runs through
    the next line that begins with any known section header prefix.
    """
    lines = text.splitlines()
    out = []
    in_block = False
    for line in lines:
        if line.startswith(REGIME_DETAIL_MARKER):
            in_block = True
            continue
        if in_block:
            if any(line.startswith(p) for p in _SECTION_PREFIXES):
                in_block = False
                out.append(line)
            continue
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# (a) INVARIANT — identical packet → paid base == free base
# ---------------------------------------------------------------------------

def test_paid_base_stripped_equals_free(tmp_path):
    """Deleting the regime-detail block lines from the entitled digest must
    yield EXACTLY the non-entitled digest (same base sections, same text,
    same order)."""
    free = mp.digest(tmp_path)
    paid = mp.digest(tmp_path, include_regime_detail=True)
    assert REGIME_DETAIL_MARKER in paid, \
        "paid digest must contain the regime-detail block"
    assert REGIME_DETAIL_MARKER not in free, \
        "free digest must NOT contain the regime-detail block"
    stripped = _strip_block(paid)
    assert stripped == free, (
        f"paid base (stripped) diverges from free.\n"
        f"--- only in free ---\n"
        f"{_diff(stripped, free)}\n"
        f"--- only in paid base ---\n"
        f"{_diff(free, stripped)}"
    )


def _diff(a, b):
    a_lines = set(a.splitlines())
    b_lines = set(b.splitlines())
    only_a = sorted(a_lines - b_lines)
    only_b = sorted(b_lines - a_lines)
    return "ONLY_FREE:\n" + "\n".join(only_a) + "\nONLY_PAID_BASE:\n" + "\n".join(only_b)


def test_paid_digest_exceeds_free_digest_by_block_only(tmp_path):
    """The paid digest adds the regime-detail block and NOTHING ELSE."""
    free = mp.digest(tmp_path)
    paid = mp.digest(tmp_path, include_regime_detail=True)
    # The block accounts for every paid-only line. If the block was added as
    # an inline section, the section text would either drop something else
    # (violating additive) or duplicate something (also violating it).
    stripped_paid = _strip_block(paid)
    assert stripped_paid == free, (
        "after stripping the regime-detail block, paid and free must be "
        "IDENTICAL — the block is not strictly ADDITIVE"
    )


# ---------------------------------------------------------------------------
# (b) Length budget — block has its own budget; total ≤ base + block + separators
# ---------------------------------------------------------------------------

def test_paid_digest_within_composed_budget(tmp_path):
    """Total entitled digest ≤ base budget + block budget + 1 separator line."""
    paid = mp.digest(tmp_path, include_regime_detail=True)
    # Use the literals the engine ships, so a constant rename can't drift this.
    base_budget = mp.DEFAULT_CHAR_BUDGET
    block_budget = mp.REGIME_DETAIL_BLOCK_BUDGET  # 2000, single source
    cap = base_budget + block_budget + 2  # two newlines + section header
    assert len(paid) <= cap, (
        f"paid digest {len(paid)} chars exceeds "
        f"base({base_budget}) + block({block_budget}) + 2 = {cap}"
    )


def test_base_text_exceeds_default_when_populated(tmp_path):
    """Sanity: a populated packet drives the base text to at least 3,800
    chars — the floor the mission sets. Without this, the additive test
    can't actually surface a drop-loop bug."""
    free = mp.digest(tmp_path)
    assert len(free) >= 3800, f"base text only {len(free)} chars; pad payload"


# ---------------------------------------------------------------------------
# Forced-small budget — base sections drop identically for paid and free
# ---------------------------------------------------------------------------

def test_forced_small_budget_drops_base_sections_identically(tmp_path):
    """When the base budget is too small for every base section, paid and
    free digests must drop IDENTICAL base sections — REGIME_DETAIL never
    participates in the base drop loop."""
    # Build packets at a budget that forces drops; then compare the base
    # contents with and without the block present.
    free = mp.digest(tmp_path, char_budget=1500)
    paid = mp.digest(tmp_path, char_budget=1500, include_regime_detail=True)
    assert REGIME_DETAIL_MARKER not in free
    # The block MUST NOT be cut by the 1500 cap. K1: block has its own
    # budget and is spliced in afterwards.
    assert REGIME_DETAIL_MARKER in paid
    # The base part (lines NOT containing the block marker) must be IDENTICAL.
    free_base = free
    paid_base = _strip_block(paid)
    assert paid_base == free_base, "forced-small budget: paid and free diverge"


# ---------------------------------------------------------------------------
# Gateway path — _grounding_digest wires both chat loops identically
# ---------------------------------------------------------------------------

def test_both_chat_loops_route_through_grounding_digest(tmp_path):
    """Both _run_brain_loop (non-streaming) and _run_brain_loop_stream
    (streaming) must funnel the digest through _grounding_digest. K1 relies
    on _grounding_digest being the ONE place entitlement is honored."""
    import ast
    from pathlib import Path as _P
    src = (_P("engine/neuralweb/brain_gateway.py")).read_text()
    tree = ast.parse(src)
    consuming = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for call in ast.walk(node):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == "_grounding_digest"):
                    consuming.append(node.name)
                    break
    assert len(consuming) >= 2, f"only {consuming} consume _grounding_digest"


def test_grounding_digest_paid_free_invariant_for_both_loops(tmp_path):
    """Drive _grounding_digest (the single funnel for both chat loops) and
    prove the paid/free base invariant at the actual gateway entry point."""
    from engine.neuralweb import brain_gateway as gw
    free = gw._grounding_digest(tmp_path)
    paid = gw._grounding_digest(tmp_path, include_regime_detail=True)
    assert REGIME_DETAIL_MARKER in paid
    assert REGIME_DETAIL_MARKER not in free
    assert _strip_block(paid) == free


def test_grounding_digest_cache_partitions_paid_and_free(tmp_path):
    """The digest cache must split by entitlement so a paid digest never
    bleeds into a free one (and vice versa) when the underlying sources
    haven't moved."""
    from engine.neuralweb import brain_gateway as gw
    paid_a = gw._grounding_digest(tmp_path, include_regime_detail=True)
    free_a = gw._grounding_digest(tmp_path)
    paid_b = gw._grounding_digest(tmp_path, include_regime_detail=True)
    free_b = gw._grounding_digest(tmp_path)
    assert REGIME_DETAIL_MARKER in paid_a and REGIME_DETAIL_MARKER in paid_b
    assert REGIME_DETAIL_MARKER not in free_a
    assert REGIME_DETAIL_MARKER not in free_b
    assert paid_a == paid_b and free_a == free_b


# ---------------------------------------------------------------------------
# Authority preserved — schema, dimensions, six statuses untouched
# ---------------------------------------------------------------------------

def test_authority_flags_and_schema_preserved(tmp_path):
    """Defensive: K1 changes nothing about the regime-context schema, the
    six statuses, or the fact that paid context is opt-in by entitlement."""
    from engine.neuralweb import brain_gateway as gw
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(gw, "_resolve_tier",
                             lambda *a, **k: {"tier": "essential",
                                              "status": "active",
                                              "features": ["site_full"]})
        # Insured visitor with paying tier must be admitted
        assert gw._regime_context_allowed("u", tmp_path) is True
        # Free visitor must NOT be admitted
        monkeypatch.setattr(gw, "_resolve_tier",
                             lambda *a, **k: {"tier": "free",
                                              "status": "active",
                                              "features": ["site_full"]})
        assert gw._regime_context_allowed("u", tmp_path) is False
    finally:
        monkeypatch.undo()
    # The packet-level schema is unchanged
    packet = mp.build_packet(tmp_path, now=NOW, include_regime_detail=True)
    assert packet["regime_detail"]["schema"] == rc.SCHEMA


# ---------------------------------------------------------------------------
# Round 5 — the entitlement keyword reaches _grounding_digest ONLY when granted
# ---------------------------------------------------------------------------

def test_free_turns_call_grounding_digest_in_the_legacy_two_argument_shape(tmp_path):
    """A free/anonymous turn must call `_grounding_digest(root, lang=...)`
    exactly as before the paid block existed, so every pre-existing stub of
    the two-argument shape (tests/test_brain_gateway.py monkeypatches
    `lambda root, lang="en": ""`) keeps working; the keyword is passed only
    on an entitled turn."""
    import ast
    from pathlib import Path as _P
    from engine.neuralweb import brain_gateway as gw
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(gw, "_regime_context_allowed", lambda user_id, root: False)
        assert gw._regime_detail_kwargs("u", tmp_path) == {}
        monkeypatch.setattr(gw, "_regime_context_allowed", lambda user_id, root: True)
        assert gw._regime_detail_kwargs("u", tmp_path) == {"include_regime_detail": True}
        # The legacy stub shape survives a free turn end to end.
        monkeypatch.setattr(gw, "_regime_context_allowed", lambda user_id, root: False)
        monkeypatch.setattr(gw, "_grounding_digest", lambda root, lang="en": "LEGACY")
        assert gw._grounding_digest(
            tmp_path, lang="en", **gw._regime_detail_kwargs("u", tmp_path)) == "LEGACY"
    finally:
        monkeypatch.undo()
    # No gateway call site may spell the keyword literally: a literal keyword
    # reaches a legacy stub even on a free turn and raises TypeError.
    src = _P("engine/neuralweb/brain_gateway.py").read_text()
    routed = 0
    for call in ast.walk(ast.parse(src)):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "_grounding_digest"):
            assert not any(kw.arg == "include_regime_detail" for kw in call.keywords), (
                f"literal include_regime_detail keyword at line {call.lineno}")
            if any(kw.arg is None and isinstance(kw.value, ast.Call)
                   and isinstance(kw.value.func, ast.Name)
                   and kw.value.func.id == "_regime_detail_kwargs"
                   for kw in call.keywords):
                routed += 1
    assert routed >= 2, f"only {routed} chat-loop call(s) route entitlement through _regime_detail_kwargs"
