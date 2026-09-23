"""Share the existing US-produced cross-market view with International.

build_site is the sole producer; build_intl consumes the same rendered fragment.
This never calculates a score or changes a measurement timestamp. A standalone
International build retains the committed snapshot instead of recomputing US data.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

SCHEMA = "global-regime-fragment.v1"
RELATIVE_PATH = Path("macrodata/global_regime_fragment.json")
UNAVAILABLE_HTML = '''<section class="panel" id="ud-hero" data-source-status="unavailable"
  aria-labelledby="ud-hero-h"><h2 id="ud-hero-h"><span class="l-en">Global markets</span>
  <span class="l-zh">全球市场</span></h2><p><span class="l-en">The cross-market snapshot
  is unavailable. No regime score is being inferred.</span><span class="l-zh">跨市场快照暂不可用，
  不据此推算状态评分。</span></p></section>'''

_HERO_STYLE_NEEDLE = ".ud-hero — Unified Macro Dashboard hero"
_NEXT_STYLE_NEEDLE = "UD-B2-W1 — Vol-weather sub-row"


def internationalize_hero_styles(theme_css: str) -> str:
    """Derive Intl-only hero CSS from the governed Macro component block.

    The shared theme stays byte-stable. International receives a presentation
    bridge inside its snapshot, so unrelated pages/receipts never need a global
    stylesheet rebind merely because this component is mounted on intl.html.
    """
    if not isinstance(theme_css, str):
        raise TypeError("theme_css must be text")
    hero_name = theme_css.find(_HERO_STYLE_NEEDLE)
    next_name = theme_css.find(_NEXT_STYLE_NEEDLE, hero_name + 1)
    if hero_name < 0 or next_name < 0:
        raise ValueError("governed hero style block not found")
    start = theme_css.rfind("/*", 0, hero_name)
    end = theme_css.rfind("/*", 0, next_name)
    if start < 0 or end <= start:
        raise ValueError("governed hero style boundaries not found")
    block = theme_css[start:end]
    if "body.page-macro" not in block:
        raise ValueError("governed hero style block lost Macro scope")
    if "body.page-intl" in block:
        raise ValueError("shared theme already contains International hero overrides")
    return block.replace("body.page-macro", "body.page-intl").strip()


def write_global_regime_fragment(site: Path, html: str, *, source_asof=None) -> Path:
    """Atomically publish a fragment rendered from the existing Macro view model."""
    if not isinstance(html, str) or html.count('id="ud-hero"') != 1:
        raise ValueError("expected exactly one rendered global-regime component")
    if 'data-regime-scope="us-reference"' not in html:
        raise ValueError("international fragment must identify its US reference")
    path = Path(site) / RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA, "source_asof": source_asof,
               "sha256": hashlib.sha256(html.encode()).hexdigest(), "html": html}
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                prefix=".global-regime-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def read_global_regime_fragment(site: Path) -> str:
    """Read the trusted build artifact; never fabricate data on absence/corruption."""
    try:
        payload = json.loads((Path(site) / RELATIVE_PATH).read_text(encoding="utf-8"))
        html = payload["html"]
        if (payload.get("schema") != SCHEMA or not isinstance(html, str)
                or html.count('id="ud-hero"') != 1
                or 'data-regime-scope="us-reference"' not in html
                or hashlib.sha256(html.encode()).hexdigest() != payload.get("sha256")):
            raise ValueError("invalid global-regime fragment")
        return html
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        logging.getLogger(__name__).warning("Global-regime fragment unavailable: %s", error)
        return UNAVAILABLE_HTML
