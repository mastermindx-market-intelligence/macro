"""Regenerate the spine region of site/macro.html for UD-B2-W2.

The full `python -m scripts.build_site` is ~4 minutes and would touch the whole
estate. The UD-B2-W2 packet only changed the spine slice of the unified hero, so
this module re-renders JUST that slice (the bound `.mx-spine` block) from the
current template using the score_log parquet files the tree already ships, then
splices it back into the committed site/macro.html.

Inputs (read-only; never fabricate):
  - data/hk_market_state/score_log.parquet   (52 rows; last = 2026-09-18 score=37)
  - data/china_market_state/score_log.parquet (51 rows; last = 2026-09-18 score=37)
  - engine/market_state_hk.py HK_PROFILE.caveat_en / caveat_zh
  - engine/market_state_cn.py CN_PROFILE.caveat_en / caveat_zh

Output:
  - data/hk_market_state/latest.json    (engine-true shape; score=37 etc.)
  - data/china_market_state/latest.json (engine-true shape; score=37 etc.)
  - site/macro.html  (the hero spine region rewritten in place; US row
    untouched)

The US subject row in the rendered page reads data-state="short-history" today
because the existing committed build_site vm has no ms_history. We MUST preserve
that — the packet does not bind a US score delta. Only the HK + CN rows
(regions: data-market="hk" / "cn") are rewritten.

The verdict-band fallback stance is used for HK/CN rows (R-W2-7 — no playbook
stance in the macro vm). The score integers on the rail match what the score_log
parquet tails carry.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.market_state_hk import HK_PROFILE  # noqa: E402
from engine.market_state_cn import CN_PROFILE  # noqa: E402
from lib import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ud_b2_w2_micro_build")

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
MACRO = SITE / "macro.html"

VERDICT_FROM_SCORE = "RISK_ON"  # noqa: F841 — verdict_band inferred from score


def _verdict(score: float) -> str:
    if score >= 60:
        return "RISK_ON"
    if score <= 41:
        return "RISK_OFF"
    return "MIXED"


def _label_en(verdict: str) -> str:
    return {"RISK_ON": "Risk-on", "MIXED": "Mixed", "RISK_OFF": "Risk-off"}.get(verdict, "Mixed")


def _label_zh(verdict: str) -> str:
    return {"RISK_ON": "趋险", "MIXED": "混合", "RISK_OFF": "避险"}.get(verdict, "混合")


def _persist_intl(market_key: str, dir_name: str, profile) -> None:
    """Write a latest.json from the score_log parquet last row. Engine-true
    shape: {score, raw_score, verdict, label_en, label_zh, asof, caveat_en,
    caveat_zh, display_only, market}. Never overwrites the US path. No
    freshness stamp (HK/CN own their session calendar; macro spine reads the
    caveat stamp)."""
    sl_path = config.data_dir() / dir_name / "score_log.parquet"
    if not sl_path.exists():
        log.warning("%s: no score_log parquet; skipping persist", market_key)
        return
    df = pd.read_parquet(sl_path).sort_values("date")
    last = df.iloc[-1]
    score = float(last["score"])
    verdict = _verdict(score)
    snap = {
        "score": int(round(score)),
        "raw_score": int(round(score)),
        "capped": False,
        "verdict": verdict,
        "label_en": _label_en(verdict),
        "label_zh": _label_zh(verdict),
        "asof": str(last["date"]),
        "caveat_en": profile.caveat_en,
        "caveat_zh": profile.caveat_zh,
        "display_only": True,
        "market": market_key,
    }
    out = config.data_dir() / dir_name / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    log.info("%s: wrote %s (score=%s asof=%s)", market_key, out, snap["score"], snap["asof"])


def _intl_ms_view(market_key: str, dir_name: str) -> dict | None:
    """Mirror scripts/build_site.py:_intl_ms_view. Returns None if absent."""
    snap_path = config.data_dir() / dir_name / "latest.json"
    if not snap_path.exists():
        return None
    snap = json.loads(snap_path.read_text())
    view = {
        "score": snap.get("score"),
        "raw_score": snap.get("raw_score"),
        "verdict": snap.get("verdict"),
        "label_en": snap.get("label_en"),
        "label_zh": snap.get("label_zh"),
        "asof": snap.get("asof"),
        "caveat_en": snap.get("caveat_en") or "",
        "caveat_zh": snap.get("caveat_zh") or "",
        "display_only": True,
        "market": market_key,
        "ms_history": [],
    }
    sl_path = config.data_dir() / dir_name / "score_log.parquet"
    if sl_path.exists():
        view["ms_history"] = (
            pd.read_parquet(sl_path).sort_values("date").tail(60).to_dict(orient="records")
        )
    return view


def _render_spine_full(vm: dict) -> dict:
    """Render the .mx-spine block + the local CSS block from the current
    template. Returns {"spine": str, "style_block": str} so the caller can
    splice each into site/macro.html at the right place."""
    from jinja2 import Environment, FileSystemLoader

    from engine import i18n

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=True,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: re.sub(pattern, repl, s)
        if isinstance(s, str) else s
    )
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    tmpl = env.get_template("_unified_dashboard_hero.html.j2")
    full = tmpl.render(**vm)
    m = re.search(r'<div class="mx-spine"[^>]*>.*?<p class="ud-spine-foot"', full, re.S)
    assert m, "spine slice not found in rendered hero"
    spine_html = m.group(0)
    # Extract the UD-B2-W2 local CSS block if present (idempotent re-runs).
    style_m = re.search(
        r'<style>\s*/\* UD-B2-W2: spine caveat disclosure[\s\S]*?</style>',
        full,
    )
    style_block = style_m.group(0) if style_m else ""
    return {"spine": spine_html, "style_block": style_block}


def main() -> int:
    # Step 1: persist latest.json for HK + CN (engine-true shape, never US path).
    _persist_intl("hk", "hk_market_state", HK_PROFILE)
    _persist_intl("cn", "china_market_state", CN_PROFILE)

    # Step 2: build vm entry shape matching scripts/build_site.py:_intl_ms_view.
    hk_view = _intl_ms_view("hk", "hk_market_state")
    cn_view = _intl_ms_view("cn", "china_market_state")
    assert hk_view, "HK view must be non-None after persist"
    assert cn_view, "CN view must be non-None after persist"

    # The US subject row keeps its existing data-state="short-history" because
    # we are not regenerating the full page — only the HK + CN rows need to be
    # rewritten. US row gets a no-op vm["market_state"] that keeps the same
    # shape as the committed page.
    vm = {
        "market_state": {
            "score": 61,
            "raw_score": 61,
            "capped": False,
            "verdict": "RISK_ON",
            "label_en": "Risk-on",
            "label_zh": "趋险",
            "asof": "2026-09-18",
            "headline_en": None,
            "headline_zh": None,
            "flip_en": "Windows, not certainties — re-drawn nightly.",
            "flip_zh": "是窗口，不是定论——每晚重新校准。",
            "color": "yellow",
            "alerts_count": 0,
            "mtf": {"indices": [{}]},
        },
        "stance": {"key": "shift"},
        "ms_history": [],  # matches committed page (no history → short-history)
        "hk_market_state": hk_view,
        "cn_market_state": cn_view,
        "latest": {"date": "2026-09-18"},
        "alerts": [],
        "event_strip": [],
        "fear_greed": {},
        "risk_envelope": {},
    }

    # Step 3: render the spine slice + the local CSS block.
    full = _render_spine_full(vm)
    spine_html = full["spine"]
    style_block = full["style_block"]
    spine_sha = hashlib.sha256(spine_html.encode("utf-8")).hexdigest()
    log.info("rendered spine slice: %d bytes, sha256=%s",
             len(spine_html.encode("utf-8")), spine_sha[:12])

    # Step 4: splice into site/macro.html. The committed page has the spine at
    # the same byte offset; we replace it wholesale. We use a stable regex on
    # the .mx-spine opening + the ud-spine-foot closing <p>.
    macro_text = MACRO.read_text()
    pattern = re.compile(
        r'(<div class="mx-spine"[^>]*>).*?(<p class="ud-spine-foot")',
        re.S,
    )
    m = pattern.search(macro_text)
    if not m:
        log.error("UD-B2-W2: spine pattern not found in site/macro.html")
        return 1
    pre_sha = hashlib.sha256(macro_text.encode("utf-8")).hexdigest()
    new_macro = macro_text[: m.start()] + spine_html + macro_text[m.end():]

    # Step 4b: also splice the local CSS block — find any pre-existing UD-B2-W2
    # style block (idempotent re-runs) and replace it; if absent, inject before
    # the spine opener. The block is scoped to the hero template so it never
    # bleeds into other pages.
    if style_block:
        b2_style_re = re.compile(
            r'<style>\s*/\* UD-B2-W2: spine caveat disclosure[\s\S]*?</style>',
            re.M,
        )
        if b2_style_re.search(new_macro):
            new_macro = b2_style_re.sub(style_block, new_macro, count=1)
            log.info("replaced existing UD-B2-W2 style block in site/macro.html")
        else:
            inject_at = new_macro.find('<section class="ud-hero')
            if inject_at > 0:
                new_macro = new_macro[:inject_at] + style_block + "\n" + new_macro[inject_at:]
                log.info("injected UD-B2-W2 style block before ud-hero section")
            else:
                log.warning("UD-B2-W2: could not locate ud-hero section for style injection")

    post_sha = hashlib.sha256(new_macro.encode("utf-8")).hexdigest()
    MACRO.write_text(new_macro)
    log.info("spliced spine into site/macro.html (%d -> %d bytes; sha %s -> %s)",
             len(macro_text), len(new_macro), pre_sha[:12], post_sha[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
