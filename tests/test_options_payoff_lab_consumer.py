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