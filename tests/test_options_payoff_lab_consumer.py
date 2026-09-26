"""Tests for the F03-W2-5b index-ETF payoff lab consumer (options.html.j2).

Hermetic by construction: every fixture payload is built IN-MEMORY from the
producer's documented contract (engine/options_payoff_lab.py SCHEMA
"mastermind.options_payoff_lab/v1"); no real network, no store read, no
file-system access.  The producer is the W2-5a store-host builder at
PR #7759 (DRAFT, seat-gated); this test file pins the CONSUMER contract
so the seat can ratify both halves from one review.

What these tests pin (each maps to a law the surface must not drift off):
  · absent payload renders NO `oew-lab` markup and the page is byte-equal to
    a render that never received the argument (zero other behaviour change)
  · SPY / QQQ / IWM cards carry the fold; SPX and DIA do not
  · when no root has a BUILT structure, the whole fold is absent
  · verdict truth table — four payloads, four plain-word verdicts, exact EN/ZH
  · bracket positions are within 0–100 and monotone floor<flip<ceiling when
    walls are ordered
  · copy law: summary ≤ 14 words, no banned token from B5 in the fold's
    visible text, every data-tip-en ≤ 80 words
  · asof_note appears only when ledger_asof ≠ card asof
  · engine-render.yml text pins: the R2 restore step follows the skew restore
    step, the brun line follows the skew emit line inside cl_gex(), every
    step's run < 20,500 chars
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.build_options_command import (  # noqa: E402
    INDEX_KEYS,
    build_context,
    build_payoff_lab,
    render,
)
from tests.test_build_options_command import (  # noqa: E402
    BANNED_VOCABULARY,
    BANNED_ON_TIER_2,
    _banned_vocabulary_hits,
    _pin_completed_session,
    _stores,
    _visible_text,
    _tip_text,
)

# B5 banned-on-the-face tokens.  Engine/options_payoff.py vocabulary lives on
# the consumer-facing fold's Tier-2 receipt tip ONLY, never on the face — and
# the slugs (atm_straddle, rr25, put_spread_95_90, call_spread_105_110) stay
# out of user copy on every tier per their Tier-2 carve-out below.
# Word-boundary matches avoid accidental hits on "ThetaData" / "mid prices"
# / etc.; we sweep on the visible text AFTER _visible_text strips scripts
# and styles and tags.
#
# Note: `mid` is in B5's banned list, but the spec's literal footer copy is
# "End-of-day mid prices, {expiry_en} expiry · ThetaData" (B3 §3) — the
# plain-word phrase is required, and the token is therefore expected in
# context.  The test exempts that one footer occurrence and asserts the rest
# of the fold never carries the bare jargon form.
_FOLD_BANNED_FACE = [
    r"\bdelta\b", r"\bvega\b", r"\btheta\b",
    r"\bgreeks?\b", r"\brisk reversal\b", r"\bATM\b",
    r"\b25d\b", r"\batm_straddle\b", r"\brr25\b",
    r"\bput_spread_95_90\b", r"\bcall_spread_105_110\b",
    r"\bdisplay-tier\b",
]
_FOLD_BANNED_FACE_RE = re.compile("|".join(_FOLD_BANNED_FACE), re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture payload builders — the producer contract, frozen
# (engine/options_payoff_lab.py SCHEMA "mastermind.options_payoff_lab/v1").
# Each helper returns a complete payload with the requested shape; tests
# compose them with overrides to drive every code path.
# ─────────────────────────────────────────────────────────────────────────────
def _structure(name: str, *, breakevens, cost_per_contract, max_gain, max_loss,
               null: bool = False, null_reason: str | None = None) -> dict:
    """One structure record — the SHAPE engine/options_payoff_lab.py writes.

    `cost_per_contract` is the per-contract figure (StructureSummary.cost =
    sum(qty * multiplier * entry_price)).  The page displays per-share
    (= cost_per_contract / 100 for the standard ETF multiplier); the test
    exercises the consumer's per-share division directly.
    """
    summary = {
        "cost": None if null else cost_per_contract,
        "max_gain": None if null else max_gain,
        "max_loss": None if null else max_loss,
        "breakevens": [] if null else list(breakevens),
        "horizon_days": 21,
        "horizon_expiry": "2026-09-25",
        "liquidity": "ok",
        "prerequisites_met": not null,
        "states": (),
        "assumptions": {},
    }
    payoff = {
        "max_gain": None if null else max_gain,
        "max_loss": None if null else max_loss,
        "cost": None if null else cost_per_contract,
        "cost_per_unit": None if null else cost_per_contract / 100.0,
        "breakevens": [] if null else list(breakevens),
        "spots": [], "pnl": [], "pnl_per_unit": [],
        "assumptions": {},
        "states": (),
    }
    states: list[dict] = []
    if null:
        states.append({
            "code": "QUOTE_MISSING",
            "scope": "structure",
            "reason": null_reason or "one leg had no quote",
            "receipt": {"root": "TEST", "name": name},
        })
    return {
        "name": name,
        "selection_rule": [],
        "summary": summary,
        "expiry_payoff": payoff,
        "scenario_grids": {},
        "greeks_drift": {},
        "assumptions": {},
        "evidence_recipe": {},
        "states": states,
    }


def _root(name: str, *, spot: float, expiration: str, tenor_days: float,
          structures: list[dict], empty_state: dict | None = None) -> dict:
    return {
        "root": name,
        "spot": spot,
        "expiration": expiration,
        "tenor_days": tenor_days,
        "structures": structures,
        "states": [] if empty_state is None else [empty_state],
    }


def _full_root_spy() -> dict:
    """SPY: all four structures BUILT, breakevens inside walls (verdict 'inside')."""
    return _root(
        "SPY", spot=645.0, expiration="2026-09-25", tenor_days=21 / 365.0,
        structures=[
            _structure("atm_straddle", breakevens=(630.0, 660.0),
                      cost_per_contract=1590.0, max_gain=12000.0, max_loss=-1590.0),
            _structure("rr25", breakevens=(620.0, 670.0),
                      cost_per_contract=-150.0, max_gain=10000.0, max_loss=-5000.0),
            _structure("put_spread_95_90", breakevens=(645.0,),
                      cost_per_contract=320.0, max_gain=3500.0, max_loss=-320.0),
            _structure("call_spread_105_110", breakevens=(650.0,),
                      cost_per_contract=410.0, max_gain=4400.0, max_loss=-410.0),
        ],
    )


def _straddle_null_qqq() -> dict:
    """QQQ: straddle is NULL (the producer's QUOTE_MISSING fired on one leg);
    other three structures are BUILT."""
    return _root(
        "QQQ", spot=580.0, expiration="2026-09-25", tenor_days=21 / 365.0,
        structures=[
            _structure("atm_straddle", breakevens=(), cost_per_contract=0,
                      max_gain=None, max_loss=None, null=True),
            _structure("rr25", breakevens=(560.0, 600.0),
                      cost_per_contract=-80.0, max_gain=8000.0, max_loss=-4000.0),
            _structure("put_spread_95_90", breakevens=(580.0,),
                      cost_per_contract=275.0, max_gain=3000.0, max_loss=-275.0),
            _structure("call_spread_105_110", breakevens=(585.0,),
                      cost_per_contract=355.0, max_gain=3500.0, max_loss=-355.0),
        ],
    )


def _payload(*, roots: list[dict], ledger_asof: str | None = "2026-09-24",
             card_asof: str = "2026-09-24", accrual_state: str = "ledger_only") -> dict:
    return {
        "schema": "mastermind.options_payoff_lab/v1",
        "asof": card_asof,
        "generated_utc": "2026-09-25T02:28:00Z",
        "source": "thetadata",
        "roots": list(roots),
        "counts": {
            "roots_priced": len([r for r in roots if r["structures"]]),
            "structures_built": sum(
                1 for r in roots for s in r["structures"]
                if (s.get("expiry_payoff") or {}).get("max_gain") is not None
            ),
            "structures_null": sum(
                1 for r in roots for s in r["structures"]
                if (s.get("expiry_payoff") or {}).get("max_gain") is None
            ),
        },
        "states": [],
        "ledger_asof": ledger_asof,
        "accrual_state": accrual_state,
        "n": sum(
            1 for r in roots for s in r["structures"]
            if (s.get("expiry_payoff") or {}).get("max_gain") is not None
        ),
    }


def _workspace_fold(page: str, sym: str) -> str:
    """Slice the rendered HTML to just the fold container under one index card."""
    # Anchor on the index card opening, then capture the trailing <details>
    # oew-lab container (one card = at most one fold, before the card's
    # closing </div>).  When the card has no fold, return the card-only slice
    # so callers can assert `class="oew-lab…"` absence on it.
    needle = f'class="oew-ic-sym mono">{sym}</span>'
    if needle not in page:
        return ""
    start = page.rfind('<div class="oew-ic">', 0, page.index(needle))
    next_card = page.find('<div class="oew-ic">', start + 1)
    card_end = next_card if next_card >= 0 else page.find("<!-- /oew -->", start)
    if card_end < 0:
        card_end = len(page)
    fold_start = page.find('<details class="oew-aib-detail oew-lab"', start, card_end)
    if fold_start < 0:
        return page[start:card_end]
    fold_end = page.find("</details>", fold_start, card_end)
    if fold_end < 0:
        fold_end = card_end
    return page[fold_start:fold_end + len("</details>")]


# ─────────────────────────────────────────────────────────────────────────────
# Tests — pinned by the F03-W2-5b frozen spec
# ─────────────────────────────────────────────────────────────────────────────
def test_payoff_lab_none_renders_no_fold():
    """payoff_lab=None → rendered options.html contains no `oew-lab` MARKUP and
    equals the render that never received the argument.  CSS rule names
    (`.oew-lab-track` etc.) ship in the inline <style> block regardless —
    the markup gate is `class="oew-lab…"`."""
    base = render(REPO, _stores())
    same = render(REPO, _stores(), payoff_lab=None)
    assert 'class="oew-lab' not in base
    assert base == same


def test_absent_payload_renders_no_fold():
    """accrual_state: 'absent' → no fold markup, byte-equal to the no-arg render."""
    absent = _payload(roots=[_full_root_spy()], accrual_state="absent")
    base = render(REPO, _stores())
    rendered = render(REPO, _stores(), payoff_lab=absent)
    assert 'class="oew-lab' not in rendered
    assert rendered == base


def test_full_payload_renders_fold_on_spy_with_track_and_four_rows():
    """SPY built (all four) + QQQ null straddle + IWM missing → SPY card has
    the fold with 4 rows and a track; QQQ's summary is the fallback wording;
    QQQ's null row carries oew-lab-null; IWM and SPX have NO fold."""
    spy = _full_root_spy()
    qqq = _straddle_null_qqq()
    payload = _payload(roots=[spy, qqq])  # IWM is omitted (no chain today)
    stores = _stores()
    page = render(REPO, stores, payoff_lab=payload)

    # SPY fold
    ws_spy = _workspace_fold(page, "SPY")
    assert '<details class="oew-aib-detail oew-lab"' in ws_spy
    assert ws_spy.count('<div class="oew-lab-row') == 4
    assert 'class="oew-lab-track"' in ws_spy
    assert 'class="oew-lab-verdict"' in ws_spy

    # QQQ fold: summary is fallback because the straddle is NULL
    ws_qqq = _workspace_fold(page, "QQQ")
    assert '<details class="oew-aib-detail oew-lab"' in ws_qqq
    assert "What a structure pays" in _visible_text(ws_qqq)
    assert "结构的盈亏" in _visible_text(ws_qqq)
    # The NULL straddle row carries the oew-lab-null span class (composed
    # with the "v" base — `class="v oew-lab-null"`).
    assert 'oew-lab-null' in ws_qqq
    assert 'class="oew-lab-row is-null"' in ws_qqq

    # IWM card — no fold (IWM not in payload)
    ws_iwm = _workspace_fold(page, "IWM")
    assert '<details class="oew-aib-detail oew-lab"' not in ws_iwm

    # SPX card — no chain in the lab; SPX never appears as a fold-bearing sym
    ws_spx = _workspace_fold(page, "SPX")
    assert '<details class="oew-aib-detail oew-lab"' not in ws_spx


def test_verdict_truth_table_exact_strings():
    """Four payloads, one per verdict; assert the exact EN and ZH strings the
    closed vocabulary in build_payoff_lab's bracket returns."""
    stores = _stores()
    cases = [
        # (label, spot, put_wall, gamma_flip, call_wall, breakevens, en, zh)
        ("inside", 645.0, 620.0, 645.0, 670.0, (630.0, 660.0),
         "Priced move stays inside the walls", "定价波幅在墙位之内"),
        ("ceiling", 645.0, 620.0, 645.0, 655.0, (630.0, 660.0),
         "Priced move reaches the ceiling", "定价波幅触及上方墙"),
        ("floor", 645.0, 635.0, 660.0, 670.0, (630.0, 660.0),
         "Priced move reaches the floor", "定价波幅触及下方墙"),
        ("both", 645.0, 635.0, 660.0, 655.0, (630.0, 660.0),
         "Priced move clears both walls", "定价波幅越过上下墙位"),
    ]
    for label, spot, put_wall, flip, call_wall, bes, want_en, want_zh in cases:
        root = _root(
            "SPY", spot=spot, expiration="2026-09-25", tenor_days=21 / 365.0,
            structures=[
                _structure("atm_straddle", breakevens=bes,
                          cost_per_contract=1500.0, max_gain=10000.0, max_loss=-1500.0),
            ],
        )
        out_payload = _payload(roots=[root])
        # Override the SPY gex summary walls for this verdict
        stores_local = {
            **stores,
            "gex": {**stores["gex"], "SPY": {
                **stores["gex"]["SPY"],
                "summary": {
                    **stores["gex"]["SPY"]["summary"],
                    "spot": spot, "put_wall": put_wall,
                    "gamma_flip": flip, "call_wall": call_wall,
                },
            }},
        }
        ctx = build_context(REPO, stores_local, payoff_lab=out_payload)
        lab = ctx["payoff_lab"]["SPY"]
        assert lab["bracket"]["verdict_en"] == want_en, f"verdict_en for {label}"
        assert lab["bracket"]["verdict_zh"] == want_zh, f"verdict_zh for {label}"


def test_bracket_positions_within_range_and_monotone():
    """When walls are ordered, floor_pct < flip_pct < ceiling_pct AND every
    pct position is in [0, 100]."""
    stores = _stores()
    payload = _payload(roots=[_full_root_spy()])
    ctx = build_context(REPO, stores, payoff_lab=payload)
    bracket = ctx["payoff_lab"]["SPY"]["bracket"]
    assert bracket is not None
    for key in ("floor_pct", "flip_pct", "ceiling_pct", "spot_pct", "lo_pct", "hi_pct"):
        assert 0.0 <= bracket[key] <= 100.0, f"{key}={bracket[key]} not in [0,100]"
    assert bracket["floor_pct"] < bracket["flip_pct"] < bracket["ceiling_pct"]


def test_copy_law_summary_under_14_words_no_banned_token():
    """The summary on the face is ≤ 14 words AND the fold's visible text has
    no token from B5.  Every data-tip-en ≤ 80 words."""
    payload = _payload(roots=[_full_root_spy()])
    page = render(REPO, _stores(), payoff_lab=payload)
    ws_spy = _workspace_fold(page, "SPY")

    # Summary ≤ 14 words — extract ONLY the <summary>…</summary> element,
    # then read its EN-side text (l-en).  The fold's <summary> carries the
    # priced-move sentence directly; the card header is OUTSIDE the fold.
    summary_match = re.search(r"<summary>(.*?)</summary>", ws_spy, re.S)
    assert summary_match, "expected a <summary> element inside the fold"
    summary_html = summary_match.group(1)
    summary_en = re.search(r'<span class="l-en">(.*?)</span>', summary_html)
    assert summary_en, "summary must carry an EN span"
    summary_words = [w for w in re.split(r"\s+", summary_en.group(1).strip()) if w]
    assert len(summary_words) <= 14, summary_words

    # B5 banned tokens never appear in the visible fold text (word-boundary regex)
    visible = _visible_text(ws_spy)
    fold_banned_hits = _FOLD_BANNED_FACE_RE.findall(visible)
    assert not fold_banned_hits, f"B5 banned token in fold face: {fold_banned_hits}"
    # Belt-and-braces: the static BANNED_VOCABULARY is the workspace's set.
    # 'mid' is on the BANNED list and the spec's footer copy is
    # "End-of-day mid prices, … · ThetaData" — one expected occurrence.
    static_hits = _banned_vocabulary_hits(visible)
    allowed_static = {"mid": 1}  # the spec's footer phrase
    unexpected = {k: v for k, v in static_hits.items() if allowed_static.get(k, 0) != v}
    assert unexpected == {}, f"workspace banned vocabulary (unexpected): {unexpected}"

    # Every data-tip-en ≤ 80 words (Tier-2 rule)
    tips = re.findall(r'data-tip-en\s*=\s*"([^"]*)"', ws_spy)
    assert tips, "expected data-tip-en attributes in the fold"
    for t in tips:
        word_count = len([w for w in t.split() if w])
        assert word_count <= 80, f"data-tip-en exceeds 80 words: {word_count} words"


def test_asof_note_only_when_ledger_asof_differs_from_card_asof():
    """The fold's asof_note appears ONLY when ledger_asof ≠ card asof."""
    stores = _stores()
    # Same asof → no asof_note
    same = _payload(roots=[_full_root_spy()],
                    ledger_asof="2026-09-24", card_asof="2026-09-24")
    ctx_same = build_context(REPO, stores, payoff_lab=same)
    assert ctx_same["payoff_lab"]["SPY"]["asof_note_en"] == ""
    assert ctx_same["payoff_lab"]["SPY"]["asof_note_zh"] == ""
    # Different asof → asof_note populated
    diff = _payload(roots=[_full_root_spy()],
                    ledger_asof="2026-09-23", card_asof="2026-09-24")
    ctx_diff = build_context(REPO, stores, payoff_lab=diff)
    assert "2026-09-23" in ctx_diff["payoff_lab"]["SPY"]["asof_note_en"]
    assert "2026-09-23" in ctx_diff["payoff_lab"]["SPY"]["asof_note_zh"]
    page = render(REPO, stores, payoff_lab=diff)
    assert "Structures as of 2026-09-23" in _visible_text(_workspace_fold(page, "SPY"))


# ─────────────────────────────────────────────────────────────────────────────
# RED-first tests for round-3 behavioural fixes
# ─────────────────────────────────────────────────────────────────────────────
def test_risk_words_are_per_share_not_per_contract():
    """Round-3 fix #1 (MAJOR 1): the producer's `expiry_payoff.max_loss` /
    `max_gain` are PER-CONTRACT (engine/options_payoff.py StructureSummary.cost =
    sum(qty * multiplier * entry_price), multiplier=100 for ETF standard
    contracts).  The consumer must divide by 100 BEFORE formatting the risk
    line, so a producer figure of -1200.0 (per-contract loss) renders as
    `$12.00 a share` (per-share), NOT `1,200 a share` or `$1,200.00 a share`.

    The fixture deliberately uses a loss figure that does NOT equal the cost
    so the "the cost" shortcut does not mask the per-share division — we
    are testing the division, not the shortcut.

    On the previous head (2d881478b8) the helper formatted the per-contract
    raw value with `:,.0f`, so -1200.0 rendered as `1,200` — this test fails
    there and passes on the new head (9731865033)."""
    from scripts.build_options_command import _payoff_lab_row_text

    record = {
        "name": "rr25",
        "summary": {
            "cost": -150.0,  # per-contract (credit)
            "max_gain": 10000.0,  # per-contract
            "max_loss": -1200.0,  # per-contract (NOT equal to abs(cost)=150)
            "breakevens": [620.0, 670.0],
            "horizon_days": 21,
            "horizon_expiry": "2026-09-25",
            "liquidity": "ok",
            "prerequisites_met": True,
            "states": (),
            "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": 10000.0,
            "max_loss": -1200.0,
            "cost": -150.0,
            "cost_per_unit": -1.5,
            "breakevens": [620.0, 670.0],
            "spots": [], "pnl": [], "pnl_per_unit": [],
            "assumptions": {},
            "states": (),
        },
        "states": [],
    }
    row = _payoff_lab_row_text(record, spot=645.0)

    # The risk line must use per-share numbers ($12.00, $100.00), not per-contract
    # ($1,200.00, $10,000.00).  The previous head emitted `1,200` / `10,000`
    # for these values — the regression this test pins.
    assert "1,200" not in row["risk_en"], (
        f"risk_en still uses per-contract value 1,200: {row['risk_en']!r}"
    )
    assert "10,000" not in row["risk_en"], (
        f"risk_en still uses per-contract value 10,000: {row['risk_en']!r}"
    )
    assert "12.00 a share" in row["risk_en"], (
        f"risk_en must carry per-share '$12.00 a share': {row['risk_en']!r}"
    )
    assert "100.00 a share" in row["risk_en"], (
        f"risk_en must carry per-share '$100.00 a share': {row['risk_en']!r}"
    )

    # Same on the ZH side — per-share (每股 $X.XX), not per-contract.
    assert "1,200" not in row["risk_zh"], (
        f"risk_zh still uses per-contract value 1,200: {row['risk_zh']!r}"
    )
    assert "10,000" not in row["risk_zh"], (
        f"risk_zh still uses per-contract value 10,000: {row['risk_zh']!r}"
    )
    assert "每股 $12.00" in row["risk_zh"], (
        f"risk_zh must carry per-share '每股 $12.00': {row['risk_zh']!r}"
    )
    assert "每股 $100.00" in row["risk_zh"], (
        f"risk_zh must carry per-share '每股 $100.00': {row['risk_zh']!r}"
    )


def test_risk_zh_parity_keeps_zh_words_not_en_words():
    """Round-3 fix #2 (MAJOR 2 ZH parity): when `loss_word` resolves to
    'the cost' / `成本金额` or 'no cap' / `无上限`, the ZH risk line must carry
    the ZH word, not the EN word.  On the previous head (2d881478b8) the
    code discarded the ZH half of `_payoff_lab_risk_word` (used `loss_en, _`)
    and stitched `loss_word` (an EN string) into both `risk_en` and `risk_zh`,
    so ZH read e.g. `最多损失：the cost · 最多盈利：no cap`.

    This test pins that ZH reads `最多损失：成本金额` / `最多盈利：无上限` for
    the loss-equals-cost and UNBOUNDED-gain cases — failing on the previous
    head where the EN words bled into ZH."""
    from scripts.build_options_command import _payoff_lab_row_text

    # Case 1: loss == cost ⇒ loss_word = 'the cost' / '成本金额'.
    rec_cost = {
        "name": "atm_straddle",
        "summary": {
            "cost": 1590.0, "max_gain": 12000.0, "max_loss": -1590.0,
            "breakevens": [630.0, 660.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-25", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": 12000.0, "max_loss": -1590.0, "cost": 1590.0,
            "cost_per_unit": 15.9, "breakevens": [630.0, 660.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    row_cost = _payoff_lab_row_text(rec_cost, spot=645.0)
    assert "成本金额" in row_cost["risk_zh"], (
        f"risk_zh must use ZH word '成本金额' (not EN 'the cost'): {row_cost['risk_zh']!r}"
    )
    assert "the cost" not in row_cost["risk_zh"], (
        f"risk_zh leaked EN 'the cost': {row_cost['risk_zh']!r}"
    )

    # Case 2: UNBOUNDED gain ⇒ gain_word = 'no cap' / '无上限'.
    rec_unb = {
        "name": "atm_straddle",
        "summary": {
            "cost": 1590.0, "max_gain": "UNBOUNDED", "max_loss": -1590.0,
            "breakevens": [630.0, 660.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-25", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": "UNBOUNDED", "max_loss": -1590.0, "cost": 1590.0,
            "cost_per_unit": 15.9, "breakevens": [630.0, 660.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    row_unb = _payoff_lab_row_text(rec_unb, spot=645.0)
    assert "无上限" in row_unb["risk_zh"], (
        f"risk_zh must use ZH word '无上限' (not EN 'no cap'): {row_unb['risk_zh']!r}"
    )
    assert "no cap" not in row_unb["risk_zh"], (
        f"risk_zh leaked EN 'no cap': {row_unb['risk_zh']!r}"
    )
    assert "no cap" in row_unb["risk_en"], (
        f"risk_en must carry 'no cap' (the EN half of UNBOUNDED): {row_unb['risk_en']!r}"
    )


def test_null_zh_never_copies_en_prose():
    """Round-3 fix #2 (MAJOR 2 ZH parity on null rows): when the producer
    ships an EN-only `null_reason` (≤ 10 plain words), the consumer uses
    that prose for `null_en` but keeps `null_zh` on its own closed-vocab
    string — NEVER copies the EN prose into ZH.  On the previous head
    (2d881478b8) the code did `out['null_zh'] = prose` for the override
    path, exposing English in the Chinese locale.

    This test pins that ZH stays on the closed-vocab string even when the
    producer's EN prose would otherwise win."""
    from scripts.build_options_command import _payoff_lab_row_text

    record = {
        "name": "atm_straddle",
        "summary": {
            "cost": None, "max_gain": None, "max_loss": None,
            "breakevens": [], "horizon_days": 21, "horizon_expiry": "2026-09-25",
            "liquidity": "thin", "prerequisites_met": False, "states": (),
            "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": None, "max_loss": None, "cost": None,
            "cost_per_unit": None, "breakevens": [],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [{
            "code": "QUOTE_MISSING",
            "scope": "structure",
            "reason": "left leg had no bid today",
            "receipt": {"root": "TEST", "name": "atm_straddle"},
        }],
    }
    row = _payoff_lab_row_text(record, spot=645.0)
    # EN picks up the producer's prose (≤ 10 plain words).
    assert row["null_en"] == "left leg had no bid today"
    # ZH must stay on the closed-vocab ZH string — never copy EN prose.
    assert row["null_zh"] != "left leg had no bid today", (
        f"null_zh leaked EN producer prose: {row['null_zh']!r}"
    )
    assert "今日未定价" in row["null_zh"], (
        f"null_zh must stay on closed-vocab ZH string: {row['null_zh']!r}"
    )


def test_css_oew_lab_has_no_border_radius_50():
    """Round-3 fix #3 (BLOCKER 2 CSS): the design-system gate forbids
    `border-radius:50%` in this packet's `.oew-lab*` rules — the spec
    names the dot geometry as a rectangle, and the dot is the brightest
    thing in the fold, so the round shape would carry glow semantics the
    law forbids.  On the previous head (2d881478b8) `.oew-lab-spot` and
    `.oew-lab-be` carried `border-radius:50%`; on the new head they do not.

    A-F03-W3-2 (payoff-fold catalyst chip) is part of the same
    `.oew-lab*` selector family; the chip itself uses
    `border-radius:var(--r-pill)` (the same pill-shaped radius the page
    already uses for `.oew-aib-lede-chip`, `.st-ready`, and the rest of
    the chip vocabulary) — never a literal `border-radius:50%`.  The
    chip has NO `::before` pseudo (no leading dot — same shape family
    as `.oew-aib-lede-chip`, which is dot-less).

    This test pins the absence as a literal grep on the rendered template."""
    text = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")

    # Pin: NO `.oew-lab*` rule carries `border-radius:50%`.  Selector
    # captures both `.oew-lab-cat` and `.oew-lab-cat::before` (the latter
    # would be the only exemption, since we want a `::before` dot to be
    # allowed — but the new head has no `::before` and no `50%`, so
    # nothing should match).
    pattern = re.compile(
        r"(\.oew-lab[a-z0-9_-]*(?:::[a-z-]+)?)[^{}]*\{[^{}]*border-radius:\s*50%",
        flags=re.S,
    )
    bad = list(pattern.findall(text))
    assert not bad, f".oew-lab rule(s) still carry border-radius:50%: {bad}"


def test_css_oew_lab_has_no_hex_color_literals():
    """Round-3 fix #3 (BLOCKER 2 CSS): the design-system gate forbids raw
    hex literals in this packet's CSS — page tokens only.  On the previous
    head (2d881478b8) a CSS comment carried the literal `#4c55a8` (the
    light-mode accent), which the checker flagged even though it was
    only a comment.  The new head removed the literal entirely (the
    light-mode accent is set by the page's existing
    `html[data-theme='light'] .oew` block above).

    This test pins the absence of any hex literal anywhere in the
    `.oew-lab*` rules."""
    text = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")

    # Capture every `.oew-lab…` selector block and assert no hex literal.
    blocks = re.findall(r"(\.oew-lab[a-z0-9_-]*[^{}]*\{[^{}]*\})",
                        text, flags=re.S)
    assert blocks, "expected at least one .oew-lab* rule block"
    hex_re = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    bad = [(b[:60], hex_re.findall(b)) for b in blocks if hex_re.search(b)]
    assert not bad, f".oew-lab* rule(s) still carry hex literals: {bad}"


def test_css_breakeven_dot_ring_uses_outline_not_box_shadow():
    """Round-3 fix #3 (BLOCKER 2 CSS): the breakeven dot's tile-coloured
    ring uses `outline:` rather than `box-shadow:` — `box-shadow:` would
    trigger the design-system's glow/shadow guard.  The light-mode override
    flips ring off via `outline:none` (was `box-shadow:none`).

    This test pins both the dark-mode rule and the light-mode override."""
    text = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")

    # Dark-mode: the `.oew-lab-be` rule carries `outline:` (not `box-shadow:`)
    # for the tile-coloured ring.
    m = re.search(r"\.oew-lab-be\s*\{([^{}]*)\}", text, flags=re.S)
    assert m, "expected .oew-lab-be rule block"
    be_block = m.group(1)
    assert "outline:" in be_block, (
        f".oew-lab-be must use `outline:` for the tile ring: {be_block!r}"
    )
    assert "box-shadow:" not in be_block, (
        f".oew-lab-be must NOT use `box-shadow:` (design-system glow guard): {be_block!r}"
    )

    # Light-mode override: flips ring off via `outline:none`.
    m_light = re.search(
        r"html\[data-theme=.light.\]\s*\.oew-lab-be\s*\{([^{}]*)\}", text, flags=re.S
    )
    assert m_light, "expected html[data-theme=light] .oew-lab-be override"
    light_block = m_light.group(1)
    assert "outline:none" in light_block, (
        f"light-mode override must set `outline:none`: {light_block!r}"
    )


def test_engine_render_yml_text_pins():
    """engine-render.yml: the R2 restore step follows the skew restore step;
    the brun line follows the skew emit line inside cl_gex(); every step's
    run < 20,500 chars (GitHub's 21,000-char limit)."""
    import yaml
    cfg_path = REPO / ".github" / "workflows" / "engine-render.yml"
    text = cfg_path.read_text(encoding="utf-8")

    # 1. The new restore step exists AFTER the skew restore step.
    skew_step_idx = text.find("- name: restore options_skew ledger from R2")
    assert skew_step_idx >= 0, "skew restore step missing"
    payoff_step_idx = text.find("- name: restore options_payoff_lab from R2")
    assert payoff_step_idx >= 0, "payoff lab restore step missing"
    assert payoff_step_idx > skew_step_idx, "payoff lab step must follow skew restore step"
    assert "options_payoff_lab" in text[payoff_step_idx:payoff_step_idx + 800]

    # 2. The brun line follows the skew emit brun INSIDE cl_gex().
    cl_gex_idx = text.find("cl_gex()")
    assert cl_gex_idx >= 0, "cl_gex() band not found"
    cl_gex_end = text.find("}", cl_gex_idx)
    band = text[cl_gex_idx:cl_gex_end]
    skew_emit_idx = band.find("scripts.build_options_skew --emit")
    payoff_emit_idx = band.find("scripts.build_options_payoff_lab --emit")
    assert skew_emit_idx >= 0, "skew emit brun not found inside cl_gex()"
    assert payoff_emit_idx >= 0, "payoff lab emit brun not found inside cl_gex()"
    assert payoff_emit_idx > skew_emit_idx, "payoff lab brun must follow skew emit"

    # 3. Every step's run < 20,500 chars.
    parsed = yaml.safe_load(text)
    max_run = max(
        len(s.get("run", ""))
        for j in parsed["jobs"].values()
        for s in j.get("steps", []) if isinstance(s, dict)
    )
    assert max_run < 20_500, f"step run length {max_run} exceeds 20,500"


# ─────────────────────────────────────────────────────────────────────────────
# RED-first tests for round-4 seat rulings (PR #7763 round 4/N)
# ─────────────────────────────────────────────────────────────────────────────
def test_built_when_only_max_loss_is_non_null():
    """Round-4 fix (MAJOR 1): a structure whose producer contract carries
    ONLY `expiry_payoff.max_loss` (max_gain == None — e.g. a debit-only spread
    whose profit is theoretically unbounded) is still BUILT per the producer's
    own `_structure_is_built`. The consumer's row-level `built` flag must
    match, so the fold renders the row instead of dropping it to NULL.

    On the previous head the row-level check was already correct (it read
    `max_gain OR max_loss`), but the ROOT-level `any_built` short-circuit in
    `build_payoff_lab` only looked at max_gain — so a root whose every
    structure carried only max_loss was silently skipped and the WHOLE fold
    disappeared. This test exercises the root-level path: a SPY root with one
    debit-only structure (max_loss=-500.0, max_gain=None) still renders the
    fold for SPY.
    """
    spy = _root(
        "SPY", spot=773.50, expiration="2026-09-26", tenor_days=21,
        structures=[
            # Debit-only: max_loss set, max_gain None. Per the producer's
            # _structure_is_built this is BUILT — max_loss is non-null.
            {
                "name": "put_spread_95_90",
                "selection_rule": [],
                "summary": {
                    "cost": 320.0, "max_gain": None, "max_loss": -500.0,
                    "breakevens": [770.0], "horizon_days": 21,
                    "horizon_expiry": "2026-09-26", "liquidity": "ok",
                    "prerequisites_met": True, "states": (), "assumptions": {},
                    "structure": {"legs": [
                        {"right": "P", "qty": 1, "strike": 735.0},
                        {"right": "P", "qty": -1, "strike": 700.0},
                    ]},
                },
                "expiry_payoff": {
                    "max_gain": None, "max_loss": -500.0, "cost": 320.0,
                    "cost_per_unit": 3.2, "breakevens": [770.0],
                    "spots": [], "pnl": [], "pnl_per_unit": [],
                    "assumptions": {}, "states": (),
                },
                "scenario_grids": {}, "greeks_drift": {}, "assumptions": {},
                "evidence_recipe": {}, "states": [],
            },
        ],
    )
    payload = _payload(roots=[spy])
    out = build_payoff_lab(payload, _stores())
    assert "SPY" in out, (
        "root-level any_built must fire when max_loss is non-null even if "
        "max_gain is None — the producer's contract counts it as BUILT"
    )
    rows = out["SPY"]["rows"]
    put_spread_row = next(r for r in rows if r.get("name_en") == "Downside hedge")
    assert put_spread_row["built"] is True, (
        "row-level built must be True when max_loss is non-null"
    )
    # And the risk line must render — not the NULL fallback.
    assert put_spread_row["risk_en"], "risk_en must render for debit-only BUILT"
    assert put_spread_row["risk_zh"], "risk_zh must render for debit-only BUILT"


def test_zh_debit_cost_carries_pct_parity():
    """Round-4 fix (MAJOR 2): ZH debit cost line mirrors EN meaning end-to-end.
    The EN line is `costs $X.XX a share · Y.Y% of the index`; the ZH line
    must carry the same two facts — `成本 $X.XX/股 · 占指数 Y.Y%`. On the
    previous head (9731865033) the ZH line dropped the `% of the index`
    half, breaking parity. This test pins ZH to carry both."""
    from scripts.build_options_command import _payoff_lab_row_text

    record = {
        "name": "atm_straddle",
        "summary": {
            "cost": 1590.0, "max_gain": 12000.0, "max_loss": -1590.0,
            "breakevens": [630.0, 660.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-25", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": 12000.0, "max_loss": -1590.0, "cost": 1590.0,
            "cost_per_unit": 15.9, "breakevens": [630.0, 660.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    row = _payoff_lab_row_text(record, spot=645.0)
    # EN baseline (pinned already by copy tests).
    assert "costs $15.90 a share" in row["cost_en"], row["cost_en"]
    assert "% of the index" in row["cost_en"], row["cost_en"]
    # ZH must carry the per-share AND the pct, mirroring the EN structure.
    assert "成本 $15.90/股" in row["cost_zh"], (
        f"cost_zh must carry the per-share figure: {row['cost_zh']!r}"
    )
    assert "占指数" in row["cost_zh"], (
        f"cost_zh must carry the as-%-of-index (parity with EN): {row['cost_zh']!r}"
    )
    assert "%" in row["cost_zh"], (
        f"cost_zh must carry a percent sign: {row['cost_zh']!r}"
    )
    # And the EN-side pct value must appear in the ZH line (same number).
    assert "2.5%" in row["cost_zh"], (
        f"cost_zh must carry the same pct value (2.5% of index at spot 645): {row['cost_zh']!r}"
    )


def test_zh_credit_uses_shou_ru_not_huo_de():
    """Round-4 fix (MAJOR 2): ZH credit (negative cost_per_share) uses `收入`
    (income), not `获得` (obtain) — `获得` is also a valid Chinese verb but
    `收入` is the financial-vocabulary word for credit / income and is what
    the EN `brings in` translates to in this domain."""
    from scripts.build_options_command import _payoff_lab_row_text

    record = {
        "name": "rr25",
        "summary": {
            "cost": -150.0, "max_gain": 10000.0, "max_loss": -5000.0,
            "breakevens": [620.0, 670.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-25", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
            # legs missing here — the rr25 strike-copy helper will fall back
            # to the standard max_loss/max_gain copy, which is fine; we are
            # only asserting the credit cost word on this fixture.
        },
        "expiry_payoff": {
            "max_gain": 10000.0, "max_loss": -5000.0, "cost": -150.0,
            "cost_per_unit": -1.5, "breakevens": [620.0, 670.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    row = _payoff_lab_row_text(record, spot=645.0)
    assert "收入 $1.50/股" in row["cost_zh"], (
        f"cost_zh credit must use 收入: {row['cost_zh']!r}"
    )
    assert "获得" not in row["cost_zh"], (
        f"cost_zh credit must NOT use 获得 (use 收入 instead): {row['cost_zh']!r}"
    )


def test_rr25_risk_uses_strikes_not_spot_to_zero_loss():
    """Round-4 SEAT ADDITION: for an rr25 structure the producer's
    `expiry_payoff.max_loss` is the short put's spot-to-zero bound — a
    per-contract figure like SPY −75387.0 that would render as `$753.87 a
    share` after the per-share division and mislead the reader. The fold's
    rr25 row MUST use strike-based risk copy instead, pulling the short put
    strike and long call strike from `summary.structure.legs`.

    This test exercises the real receipt numbers (SPY spot 773.50,
    straddle max_loss −2291.5 → `$22.92 a share`, rr25 max_loss
    −75387.0 → strike copy with NO `$753.87` anywhere on the row)."""
    from scripts.build_options_command import _payoff_lab_row_text

    # Real receipt values from the W2-5a store-host receipt (2026-09-21).
    rr25_record = {
        "name": "rr25",
        "summary": {
            "cost": -250.0, "max_gain": None, "max_loss": -75387.0,
            "breakevens": [770.0, 780.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-26", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
            # The legs the rr25 structure carries (per engine/options_payoff_lab
            # .py::_catalog_specs): C at call_strike qty +1, P at put_strike
            # qty -1. Put strike 745, call strike 800 — illustrative.
            "structure": {"legs": [
                {"right": "C", "qty": 1, "strike": 800.0,
                 "expiration": "2026-09-26"},
                {"right": "P", "qty": -1, "strike": 745.0,
                 "expiration": "2026-09-26"},
            ]},
        },
        "expiry_payoff": {
            "max_gain": None, "max_loss": -75387.0, "cost": -250.0,
            "cost_per_unit": -2.5, "breakevens": [770.0, 780.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    row = _payoff_lab_row_text(rr25_record, spot=773.50)

    # 1. The risk line MUST be strike-based, not the standard max_loss copy.
    assert "loses like the index" in row["risk_en"], (
        f"rr25 risk_en must use strike-based copy: {row['risk_en']!r}"
    )
    assert "gains like the index" in row["risk_en"], (
        f"rr25 risk_en must use strike-based copy: {row['risk_en']!r}"
    )
    assert "低于" in row["risk_zh"] and "与指数同跌" in row["risk_zh"], (
        f"rr25 risk_zh must use strike-based copy: {row['risk_zh']!r}"
    )
    assert "高于" in row["risk_zh"] and "与指数同涨" in row["risk_zh"], (
        f"rr25 risk_zh must use strike-based copy: {row['risk_zh']!r}"
    )

    # 2. The strikes (745, 800) MUST appear on the line.
    assert "745" in row["risk_en"], (
        f"rr25 risk_en must carry the put strike 745: {row['risk_en']!r}"
    )
    assert "800" in row["risk_en"], (
        f"rr25 risk_en must carry the call strike 800: {row['risk_en']!r}"
    )

    # 3. The misleading spot-to-zero figure MUST NOT appear anywhere.
    assert "$753.87" not in row["risk_en"], (
        f"rr25 risk_en must not carry '$753.87 a share' "
        f"(spot-to-zero would mislead): {row['risk_en']!r}"
    )
    assert "$753.87" not in row["risk_zh"], (
        f"rr25 risk_zh must not carry '$753.87' "
        f"(spot-to-zero would mislead): {row['risk_zh']!r}"
    )
    # The raw per-contract figure 75387.0 must not leak into either line.
    assert "75,387" not in row["risk_en"], (
        f"rr25 risk_en must not carry the raw per-contract figure: {row['risk_en']!r}"
    )
    assert "75,387" not in row["risk_zh"], (
        f"rr25 risk_zh must not carry the raw per-contract figure: {row['risk_zh']!r}"
    )

    # 4. The standard copy must NOT appear on an rr25 row.
    assert "most you can lose" not in row["risk_en"], (
        f"rr25 risk_en must NOT use the standard max_loss copy: {row['risk_en']!r}"
    )
    assert "最多损失" not in row["risk_zh"], (
        f"rr25 risk_zh must NOT use the standard max_loss copy: {row['risk_zh']!r}"
    )

    # 5. Companion assertion — for the straddle on the SAME receipt (spot
    # 773.50, max_loss −2292.0), the per-share division lands on $22.92 and
    # the standard copy renders. We deliberately set `cost ≠ |max_loss|` so
    # the "the cost" shortcut doesn't fire and the per-share figure renders.
    # This pins that the strike-based copy only fires for rr25 and the
    # straddle still uses the standard per-share copy.
    straddle_record = {
        "name": "atm_straddle",
        "summary": {
            "cost": 1800.0, "max_gain": None, "max_loss": -2292.0,
            "breakevens": [750.0, 795.0], "horizon_days": 21,
            "horizon_expiry": "2026-09-26", "liquidity": "ok",
            "prerequisites_met": True, "states": (), "assumptions": {},
        },
        "expiry_payoff": {
            "max_gain": None, "max_loss": -2292.0, "cost": 1800.0,
            "cost_per_unit": 18.0, "breakevens": [750.0, 795.0],
            "spots": [], "pnl": [], "pnl_per_unit": [], "assumptions": {}, "states": (),
        },
        "states": [],
    }
    straddle_row = _payoff_lab_row_text(straddle_record, spot=773.50)
    assert "$22.92 a share" in straddle_row["risk_en"], (
        f"straddle risk_en must carry per-share '$22.92 a share': "
        f"{straddle_row['risk_en']!r}"
    )
    assert "loses like the index" not in straddle_row["risk_en"], (
        f"straddle risk_en must NOT use strike-based copy: "
        f"{straddle_row['risk_en']!r}"
    )


def test_tenor_days_passes_int_through_and_none_on_non_int():
    """Round-4 fix (MINOR 2): the contract is `tenor_days: int`. The consumer
    passes an int through unchanged; a non-int (None, partial float, str)
    becomes None — the fold never prints tenor, so a None here is silent.

    This test exercises the row-level envelope at `build_payoff_lab`: when
    `tenor_days` is an int it lands as int on the envelope; when it is a
    partial float (21 / 365.0) it lands as None."""
    full_int = _root(
        "SPY", spot=773.50, expiration="2026-09-26", tenor_days=21,
        structures=[
            _structure("atm_straddle", breakevens=(750.0, 795.0),
                      cost_per_contract=2291.5, max_gain=None, max_loss=-2291.5),
        ],
    )
    out_int = build_payoff_lab(_payload(roots=[full_int]), _stores())
    assert out_int["SPY"]["tenor_days"] == 21, (
        f"tenor_days=21 (int) must pass through as int: {out_int['SPY']['tenor_days']!r}"
    )

    full_float = _root(
        "SPY", spot=773.50, expiration="2026-09-26", tenor_days=21 / 365.0,
        structures=[
            _structure("atm_straddle", breakevens=(750.0, 795.0),
                      cost_per_contract=2291.5, max_gain=None, max_loss=-2291.5),
        ],
    )
    out_float = build_payoff_lab(_payload(roots=[full_float]), _stores())
    assert out_float["SPY"]["tenor_days"] is None, (
        f"tenor_days=21/365.0 (partial float) must become None: "
        f"{out_float['SPY']['tenor_days']!r}"
    )

    full_none = _root(
        "SPY", spot=773.50, expiration="2026-09-26", tenor_days=None,
        structures=[
            _structure("atm_straddle", breakevens=(750.0, 795.0),
                      cost_per_contract=2291.5, max_gain=None, max_loss=-2291.5),
        ],
    )
    out_none = build_payoff_lab(_payload(roots=[full_none]), _stores())
    assert out_none["SPY"]["tenor_days"] is None, (
        f"tenor_days=None must stay None: {out_none['SPY']['tenor_days']!r}"
    )


def test_css_oew_lab_track_height_is_4px():
    """Round-4 fix (MAJOR 3): the fold's track is a 4px hairline rail — the
    previous head had it at 14px. The marks (walls, flip, spot, breakeven)
    overhang the rail by design (ink-weight ticks rising from a hairline)."""
    text = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")
    m = re.search(r"\.oew-lab-track\s*\{([^{}]*)\}", text, flags=re.S)
    assert m, "expected .oew-lab-track rule block"
    block = m.group(1)
    # The 4px token must be present on the track rule.
    assert re.search(r"height:\s*4px", block), (
        f".oew-lab-track must carry height:4px: {block!r}"
    )
    # And the 14px value (the previous-head regression) must not.
    assert "height:14px" not in block, (
        f".oew-lab-track must NOT carry height:14px: {block!r}"
    )


def test_css_oew_lab_row_v_has_mono_class_in_markup():
    """Round-4 fix (MAJOR 3): the fold's row values carry the page's mono
    treatment — `class="v mono"` on the per-row value spans inside the fold.
    A regression to `class="v"` alone would leave them on the page's
    proportional face."""
    text = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")
    # The fold row value spans carry class="v mono" — pin the exact form.
    assert re.search(r'class="v mono">\{\{\s*t\(r\.(cost_en|cost_zh)', text), (
        "fold cost row value must carry class=\"v mono\""
    )
    assert re.search(r'class="v mono">\{\{\s*t\(r\.(pays_en|pays_zh)', text), (
        "fold pays row value must carry class=\"v mono\""
    )
    assert re.search(r'class="v mono">\{\{\s*t\(r\.(risk_en|risk_zh)', text), (
        "fold risk row value must carry class=\"v mono\""
    )


# ═════════════════════════════════════════════════════════════════════════════
# A-F03-W3-2 — payoff-fold catalyst chip (SPY / QQQ / IWM index cards)
#
# The chip answers exactly one question: "does a Federal Reserve rate
# decision land before this expiry?".  It is context only — never rank,
# never score, never size.  Every test below pins one leg of the spec's
# tri-state law, the loader's fail-soft contract, or the render fixture
# (8 chips across the matrix is the W2-5b evidence path; this packet
# reuses it for the 2-chip / 3-card fixture the chip lives on).
# ═════════════════════════════════════════════════════════════════════════════

import json  # noqa: E402  (W3-2 only — pinned here so the upstream import block stays canonical)


def _catalyst_links(asof: str = "2026-09-23", horizon_end: str = "2026-11-25",
                    fomc_dates: list[str] | None = None,
                    schema: str = "mastermind.options_catalyst_links/v1",
                    macro_calendar: dict | None | str = "build") -> dict:
    """Build the catalyst-links envelope the chip helper reads.

    `macro_calendar` accepts three shapes for testing the loader / chip:
      · "build"    → build a real macro_calendar dict from asof/horizon_end/fomc_dates;
      · dict       → use as-is (lets the loader tests pass an off-shape dict);
      · None       → omit `macro_calendar` entirely (loader returns None).
    """
    payload: dict = {
        "schema": schema,
        "spec_version": "v1",
        "session_date": asof,
        "asof": asof,
        "horizon_days": 63,
        "source": {"events": "r2:live_flow/events/2026-09-23.jsonl",
                   "earnings": "engine.earnings_blackout",
                   "macro": "engine.event_calendar",
                   "identity": "stock_identity.plane:stocks"},
        "counts": {"events": 1, "dropped_malformed": 0, "known_symbols": 1,
                   "candidates_earnings": 1, "candidates_macro": len(fomc_dates or []),
                   "by_state": {}},
        "authority": {"rank": False, "size": False, "gate": False,
                      "score": False, "origin": False},
        "is_context_only": True,
        "states": ["ok"],
        "links_path": "2026-09-23.jsonl",
    }
    if macro_calendar == "build":
        payload["macro_calendar"] = {
            "asof": asof,
            "horizon_end": horizon_end,
            "source": "engine.event_calendar",
            "fomc": [{"date": d, "label": "Fed rate decision"} for d in (fomc_dates or [])],
        }
    elif isinstance(macro_calendar, dict):
        payload["macro_calendar"] = macro_calendar
    return payload


def test_payoff_lab_catalyst_before_expiry_one_date_exact_strings():
    """One FOMC date inside the window → state='before-expiry', chip names
    the FIRST such date.  Exact-string assertion (ruling D.2) so a drift
    in either chip or tip cannot pass this test."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2026-10-28",
        card_asof="2026-09-23",
        calendar=_catalyst_links(asof="2026-09-23", horizon_end="2026-11-25",
                                 fomc_dates=["2026-10-28"])["macro_calendar"],
    )
    assert out is not None
    assert out["state"] == "before-expiry"
    assert out["chip_en"] == "Fed decision Oct 28 lands before this expiry"
    assert out["chip_zh"] == "美联储10月28日议息在到期前"
    # Exact tip copy (ruling D.2).  Calendar asof formats as a date word,
    # never the raw ISO string — ZH lands as a single Chinese sentence.
    assert out["tip_en"] == (
        "The Federal Reserve's rate decision on Oct 28 falls inside the "
        "Oct 28 expiry these structures use. Prices here were set at this "
        "close; a scheduled decision inside the window is context, not a "
        "signal. Calendar as of Sep 23."
    )
    assert out["tip_zh"] == (
        "美联储10月28日的利率决定落在这些结构所用的10月28日到期日之前。"
        "此处价格以本次收盘计算；窗口内的既定议息只是背景信息，不是信号。"
        "日历截至9月23日。"
    )
    assert out["calendar_asof"] == "2026-09-23"


def test_payoff_lab_catalyst_before_expiry_two_dates_tip_lists_both():
    """Two FOMC dates inside the window → state='before-expiry', chip still
    names the FIRST, tip includes BOTH dates and the 'and so does …' clause.
    Exact-string assertion so a drift in either chip or tip cannot pass."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2026-12-15",
        card_asof="2026-09-23",
        calendar=_catalyst_links(asof="2026-09-23", horizon_end="2026-12-31",
                                 fomc_dates=["2026-10-28", "2026-12-09"])["macro_calendar"],
    )
    assert out is not None
    assert out["state"] == "before-expiry"
    assert out["chip_en"] == "Fed decision Oct 28 lands before this expiry"
    assert out["chip_zh"] == "美联储10月28日议息在到期前"
    assert out["tip_en"] == (
        "The Federal Reserve's rate decision on Oct 28 falls inside the "
        "Dec 15 expiry these structures use, and so does Dec 9. "
        "Prices here were set at this close; a scheduled decision inside "
        "the window is context, not a signal. Calendar as of Sep 23."
    )
    assert out["tip_zh"] == (
        "美联储10月28日的利率决定落在这些结构所用的12月15日到期日之前，12月9日亦然。"
        "此处价格以本次收盘计算；窗口内的既定议息只是背景信息，不是信号。"
        "日历截至9月23日。"
    )


def test_payoff_lab_catalyst_before_expiry_sorts_unsorted_fomc_input():
    """A-F03-W3-2 (MINOR 1 RED-first): the helper sorts the filtered FOMC
    dates itself.  A hand-written unsorted `fomc` list must still pick the
    SOONEST date for the chip — without the sort the loop would emit the
    dates in calendar order and `fomc_dates[0]` could name Dec 9 instead
    of Oct 28.  Without the sort fix, the chip says 'Dec 9' and the test
    fails."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2026-12-15",
        card_asof="2026-09-23",
        # Deliberately unsorted: Dec 9 before Oct 28.  Producer output is
        # always sorted, but the consumer must remain correct on a hand-
        # written fixture (the calendar is an additive key — overcorrection
        # would invalidate the helper on any future contributor that does
        # not sort).
        calendar=_catalyst_links(asof="2026-09-23", horizon_end="2026-12-31",
                                 fomc_dates=["2026-12-09", "2026-10-28"])["macro_calendar"],
    )
    assert out is not None
    assert out["state"] == "before-expiry"
    # Chip names the SOONEST date in the window — Oct 28 — not the first
    # entry the loop happened to see.
    assert out["chip_en"] == "Fed decision Oct 28 lands before this expiry"
    assert out["chip_zh"] == "美联储10月28日议息在到期前"
    # Tail lists the other date in correct order — Oct 28 first, Dec 9 next.
    assert "and so does Dec 9" in out["tip_en"]
    assert "12月9日亦然" in out["tip_zh"]


def test_payoff_lab_catalyst_three_dates_verb_agreement_fixes():
    """Three-or-more dates flip the EN verb from singular 'does' to plural
    'do' (MINOR 2 verdict).  At a 63-day window a hand-injected test
    fixture can carry three dates; the helper must stay correct."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2027-01-27",
        card_asof="2026-09-23",
        calendar=_catalyst_links(
            asof="2026-09-23", horizon_end="2027-02-23",
            fomc_dates=["2026-10-28", "2026-12-09", "2027-01-27"],
        )["macro_calendar"],
    )
    assert out is not None
    assert out["state"] == "before-expiry"
    # Verb flip: 'do' (plural of "Fed decisions") replaces 'does' (singular).
    assert "and so do Dec 9, Jan 27" in out["tip_en"], (
        f"verb agreement broken at ≥3 dates: {out['tip_en']!r}"
    )
    # ZH stays on the 12月9日、1月27日亦然 form (no verb).
    assert "12月9日、1月27日亦然" in out["tip_zh"]


def test_payoff_lab_catalyst_clear_when_no_fomc_in_window():
    """Calendar covers the expiry, no FOMC inside the window → state='clear',
    chip + tip are exact strings (ruling D.2)."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2026-10-09",
        card_asof="2026-09-23",
        # FOMC dates exist, but neither is inside (2026-09-23, 2026-10-09].
        calendar=_catalyst_links(asof="2026-09-23", horizon_end="2026-11-25",
                                 fomc_dates=["2026-10-28", "2026-12-09"])["macro_calendar"],
    )
    assert out is not None
    assert out["state"] == "clear"
    assert out["chip_en"] == "No Fed decision before this expiry"
    assert out["chip_zh"] == "到期前无美联储议息"
    assert out["tip_en"] == (
        "No Federal Reserve rate decision is scheduled between this close "
        "and the Oct 9 expiry. Calendar as of Sep 23."
    )
    assert out["tip_zh"] == (
        "本次收盘至10月9日到期之间没有既定的美联储利率决定。"
        "日历截至9月23日。"
    )
    assert out["calendar_asof"] == "2026-09-23"


def test_payoff_lab_catalyst_none_when_expiration_beyond_horizon_end():
    """Expiration outside the calendar's horizon → None (chip ABSENT).
    Comparing a date the calendar cannot see is a guess, not a fact."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2027-06-15",
        card_asof="2026-09-23",
        calendar=_catalyst_links(asof="2026-09-23", horizon_end="2026-11-25",
                                 fomc_dates=[])["macro_calendar"],
    )
    assert out is None


def test_payoff_lab_catalyst_none_when_calendar_older_than_7_days():
    """Calendar asof more than 7 calendar days older than card_asof → None
    (a rotten calendar is not a calendar)."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="2026-10-28",
        card_asof="2026-09-23",
        # Calendar asof is 2026-09-01 — 22 days older than 2026-09-23 → rotten.
        calendar=_catalyst_links(asof="2026-09-01", horizon_end="2026-11-03",
                                 fomc_dates=["2026-10-28"])["macro_calendar"],
    )
    assert out is None
    # Boundary: exactly 7 days old is acceptable.
    boundary = _payoff_lab_catalyst(
        expiration="2026-10-28",
        card_asof="2026-09-23",
        # 2026-09-16 is exactly 7 calendar days older than 2026-09-23 → acceptable.
        calendar=_catalyst_links(asof="2026-09-16", horizon_end="2026-11-18",
                                 fomc_dates=["2026-10-28"])["macro_calendar"],
    )
    assert boundary is not None
    assert boundary["state"] == "before-expiry"


def test_payoff_lab_catalyst_none_for_missing_calendar():
    """calendar=None → None (chip ABSENT — unknown is not 'none')."""
    from scripts.build_options_command import _payoff_lab_catalyst

    assert _payoff_lab_catalyst("2026-10-28", "2026-09-23", None) is None


def test_payoff_lab_catalyst_none_for_non_iso_expiration():
    """Non-ISO expiration → None."""
    from scripts.build_options_command import _payoff_lab_catalyst

    out = _payoff_lab_catalyst(
        expiration="not-a-date",
        card_asof="2026-09-23",
        calendar=_catalyst_links(fomc_dates=["2026-10-28"])["macro_calendar"],
    )
    assert out is None


def test_load_catalyst_links_returns_none_when_file_missing(tmp_path):
    """load_catalyst_links() returns None when the artifact is absent —
    the chip stays absent on every card and the page is byte-equal to the
    no-catalyst render."""
    from scripts.build_options_command import load_catalyst_links
    assert load_catalyst_links(tmp_path) is None


def test_load_catalyst_links_returns_none_on_wrong_schema(tmp_path):
    """Wrong schema on the envelope → None.  The producer is the only
    legitimate writer; any other schema is a contract break."""
    from scripts.build_options_command import load_catalyst_links

    art = tmp_path / "site" / "options_catalyst_links"
    art.mkdir(parents=True)
    (art / "latest.json").write_text(json.dumps({
        "schema": "something.else/v1",
        "macro_calendar": {"fomc": []},
    }))
    assert load_catalyst_links(tmp_path) is None


def test_load_catalyst_links_returns_none_when_macro_calendar_missing(tmp_path):
    """No `macro_calendar` key → None.  The chip stays absent until the
    next nightly populates the new key."""
    from scripts.build_options_command import load_catalyst_links

    art = tmp_path / "site" / "options_catalyst_links"
    art.mkdir(parents=True)
    (art / "latest.json").write_text(json.dumps({
        "schema": "mastermind.options_catalyst_links/v1",
    }))
    assert load_catalyst_links(tmp_path) is None


def test_load_catalyst_links_returns_none_when_fomc_not_a_list(tmp_path):
    """`macro_calendar.fomc` not a list → None (off-shape payload)."""
    from scripts.build_options_command import load_catalyst_links

    art = tmp_path / "site" / "options_catalyst_links"
    art.mkdir(parents=True)
    (art / "latest.json").write_text(json.dumps({
        "schema": "mastermind.options_catalyst_links/v1",
        "macro_calendar": {"asof": "2026-09-23", "horizon_end": "2026-11-25",
                           "source": "engine.event_calendar",
                           "fomc": "not-a-list"},
    }))
    assert load_catalyst_links(tmp_path) is None


def test_load_catalyst_links_returns_payload_when_shape_is_valid(tmp_path):
    """All shape guards pass → returns the parsed payload (the chip
    helper then reads `payload['macro_calendar']`)."""
    from scripts.build_options_command import load_catalyst_links
    import scripts.build_options_command as boc

    art = tmp_path / "site" / "options_catalyst_links"
    art.mkdir(parents=True)
    payload = _catalyst_links(fomc_dates=["2026-10-28", "2026-12-09"])
    (art / "latest.json").write_text(json.dumps(payload))
    out = load_catalyst_links(tmp_path)
    assert isinstance(out, dict)
    assert out["schema"] == "mastermind.options_catalyst_links/v1"
    assert [e["date"] for e in out["macro_calendar"]["fomc"]] == ["2026-10-28", "2026-12-09"]
    # Reference kept stable — no globals touched.
    assert boc._CATALYST_LINKS_SCHEMA == "mastermind.options_catalyst_links/v1"


def test_render_with_calendar_yields_two_chips_for_three_cards():
    """Render fixture (ruling D.2): SPY before-expiry, QQQ clear, IWM absent
    (no chain in fold) → exactly 2 `data-payoff-catalyst-chip` elements on
    ONE page.  The two real outcomes both render: `is-before-expiry` on SPY,
    `is-clear` on QQQ.  Per-root expiration split (SPY 2026-09-25, QQQ
    2026-09-24, card_asof 2026-09-24, FOMC 2026-09-25).  SPY's window
    (2026-09-24, 2026-09-25] contains the FOMC date → before-expiry; QQQ's
    window (2026-09-24, 2026-09-24] is empty → clear."""
    from scripts.build_options_command import build_context

    spy = _full_root_spy()      # expiration = "2026-09-25"
    # QQQ's expiration lands on card_asof itself, so the strict-greater
    # window `(card_asof < d <= expiration)` is empty and the chip is
    # `clear` regardless of which FOMC date the calendar carries.
    qqq_same_day = _root(
        "QQQ", spot=580.0, expiration="2026-09-24", tenor_days=0.0,
        structures=[
            _structure("atm_straddle", breakevens=(565.0, 595.0),
                      cost_per_contract=1850.0, max_gain=10000.0, max_loss=-1850.0),
            _structure("rr25", breakevens=(560.0, 600.0),
                      cost_per_contract=-80.0, max_gain=8000.0, max_loss=-4000.0),
            _structure("put_spread_95_90", breakevens=(580.0,),
                      cost_per_contract=275.0, max_gain=3000.0, max_loss=-275.0),
            _structure("call_spread_105_110", breakevens=(585.0,),
                      cost_per_contract=355.0, max_gain=3500.0, max_loss=-355.0),
        ],
    )
    payload = _payload(roots=[spy, qqq_same_day])  # IWM deliberately omitted
    catalyst_links = _catalyst_links(
        asof="2026-09-24", horizon_end="2026-11-30",
        fomc_dates=["2026-09-25"],
    )

    ctx = build_context(REPO, _stores(), payoff_lab=payload,
                        catalyst_links=catalyst_links)
    lab = ctx["payoff_lab"]
    assert "SPY" in lab and lab["SPY"]["catalyst"] is not None
    assert lab["SPY"]["catalyst"]["state"] == "before-expiry"
    assert "QQQ" in lab and lab["QQQ"]["catalyst"] is not None
    assert lab["QQQ"]["catalyst"]["state"] == "clear"
    assert "IWM" not in lab, "IWM is absent from the fixture — chip has no card"

    page = render(REPO, _stores(), payoff_lab=payload,
                  catalyst_links=catalyst_links)
    chip_count = page.count("data-payoff-catalyst-chip")
    assert chip_count == 2, (
        f"expected exactly 2 chip elements on one page (SPY + QQQ, IWM absent), got {chip_count}"
    )
    assert "is-before-expiry" in page, "SPY chip must carry is-before-expiry class"
    assert "is-clear" in page, "QQQ chip must carry is-clear class"


def test_render_with_calendar_exercises_both_chip_states():
    """Cross-state render fixture on ONE page (MAJOR 2): SPY before-expiry +
    QQQ clear on the SAME render.  Per-fold class-token coverage that both
    CSS art directions actually fire (`is-before-expiry` on SPY's fold,
    `is-clear` on QQQ's fold).  Per-root expiration split: SPY 2026-09-25
    covers the FOMC date, QQQ 2026-09-24 yields an empty window."""
    from scripts.build_options_command import build_context

    spy = _full_root_spy()      # expiration = "2026-09-25"
    qqq_same_day = _root(
        "QQQ", spot=580.0, expiration="2026-09-24", tenor_days=0.0,
        structures=[
            _structure("atm_straddle", breakevens=(565.0, 595.0),
                      cost_per_contract=1850.0, max_gain=10000.0, max_loss=-1850.0),
            _structure("rr25", breakevens=(560.0, 600.0),
                      cost_per_contract=-80.0, max_gain=8000.0, max_loss=-4000.0),
            _structure("put_spread_95_90", breakevens=(580.0,),
                      cost_per_contract=275.0, max_gain=3000.0, max_loss=-275.0),
            _structure("call_spread_105_110", breakevens=(585.0,),
                      cost_per_contract=355.0, max_gain=3500.0, max_loss=-355.0),
        ],
    )
    payload = _payload(roots=[spy, qqq_same_day])
    catalyst_links = _catalyst_links(
        asof="2026-09-24", horizon_end="2026-11-30",
        fomc_dates=["2026-09-25"],
    )

    page = render(REPO, _stores(), payoff_lab=payload,
                  catalyst_links=catalyst_links)
    fold_spy = _workspace_fold(page, "SPY")
    fold_qqq = _workspace_fold(page, "QQQ")
    # SPY's fold carries the before-expiry chip; QQQ's fold carries clear.
    assert 'data-payoff-catalyst-chip' in fold_spy
    assert 'is-before-expiry' in fold_spy
    assert 'data-payoff-catalyst-chip' in fold_qqq
    assert 'is-clear' in fold_qqq
    # Cross-state guard: SPY's fold never carries the clear class token,
    # and QQQ's fold never carries the before-expiry class token.
    assert 'is-clear' not in fold_spy
    assert 'is-before-expiry' not in fold_qqq


def test_render_chips_carry_no_banned_tokens_in_visible_text():
    """The chip text + tip text MUST NOT carry the bare machine words
    `FOMC`, `fomc`, `macro_calendar` (the dict name) or `before-expiry`
    (the class token is allowed in markup, but the WORD must not appear in
    visible text — neither chip nor tip should say "before-expiry")."""
    from scripts.build_options_command import build_context

    spy = _full_root_spy()
    qqq = _straddle_null_qqq()
    payload = _payload(roots=[spy, qqq])
    catalyst_links = _catalyst_links(asof="2026-09-24", horizon_end="2026-11-30",
                                     fomc_dates=["2026-09-25", "2026-10-28"])

    page = render(REPO, _stores(), payoff_lab=payload, catalyst_links=catalyst_links)
    visible = _visible_text(page)
    for banned in ("FOMC", "fomc", "macro_calendar", "before-expiry"):
        assert banned not in visible, (
            f"chip-rendered HTML carries banned token {banned!r} in visible text"
        )
    # The CLASS TOKEN `is-before-expiry` IS allowed — pin that explicitly.
    assert "is-before-expiry" in page, (
        "the chip's class token is allowed in markup; if it's missing, the "
        "template probably branched on the wrong condition"
    )


def test_render_fold_other_elements_unchanged_when_calendar_present():
    """When a calendar is threaded in, the fold's other elements are
    byte-identical to the no-calendar render — only the chip is added."""
    spy = _full_root_spy()
    qqq = _straddle_null_qqq()
    payload = _payload(roots=[spy, qqq])
    catalyst_links = _catalyst_links(asof="2026-09-24", horizon_end="2026-11-30",
                                     fomc_dates=["2026-09-25", "2026-10-28"])

    base = render(REPO, _stores(), payoff_lab=payload)
    with_cal = render(REPO, _stores(), payoff_lab=payload, catalyst_links=catalyst_links)

    # The fold's row count, verdict, bracket, and asof_note are all
    # unchanged — strip the new chip element and compare.
    chip_pattern = re.compile(
        r'<p[^>]*data-payoff-catalyst-chip[^>]*>.*?</p>',
        flags=re.S,
    )
    base_no_chip = chip_pattern.sub("", base)
    with_cal_no_chip = chip_pattern.sub("", with_cal)
    assert base_no_chip == with_cal_no_chip, (
        "fold elements changed when the chip was threaded in; "
        "the chip is the ONLY additive element on this surface"
    )


def test_load_stores_body_does_not_read_the_chip_store():
    """F03-W3-2 ADDITIVE: the chip's store is read via a NEW function
    (`load_catalyst_links`), NOT through the pinned workspace loader.
    The pinned workspace-scope suite's `WORKSPACE_STORES` set stays
    untouched — this test pins that the chip store's name never appears
    inside the pinned loader's body (the real cross-source byte-equal
    check is the WORKSPACE_STORES map at
    tests/test_render_options_workspace_scope.py:335, not this string
    presence test)."""
    cmd_src = (REPO / "scripts" / "build_options_command.py").read_text(encoding="utf-8")
    # Extract the body of load_stores — the same extractor as the
    # workspace-scope test, with the chip store absent.
    body = cmd_src.split("def load_stores(", 1)[1].split("\n\n", 1)[0]
    forbidden_strings = [
        "options_catalyst_links",  # never inside load_stores
    ]
    for token in forbidden_strings:
        assert token not in body, (
            f"the pinned workspace loader must NOT read the chip store "
            f"(use load_catalyst_links); found {token!r} inside its body"
        )


def test_payoff_lab_fold_payoff_lab_consumer_pin_count():
    """Acceptance-grep table: the F03-W3-2 surface area is pinned by:
      · 2 new functions (`load_catalyst_links`, `_payoff_lab_catalyst`)
      · 1 template marker (`data-payoff-catalyst-chip`)
      · >= 6 CSS rule occurrences (`.oew-lab-cat` selector + 2 light overrides)
    """
    import inspect

    cmd_src = (REPO / "scripts" / "build_options_command.py").read_text(encoding="utf-8")
    tpl_src = (REPO / "templates" / "options.html.j2").read_text(encoding="utf-8")

    assert "def load_catalyst_links(" in cmd_src
    assert "def _payoff_lab_catalyst(" in cmd_src
    assert tpl_src.count("data-payoff-catalyst-chip") == 1
    assert tpl_src.count(".oew-lab-cat") >= 6
    assert tpl_src.count('html[data-theme="light"] .oew-lab-cat') == 2
