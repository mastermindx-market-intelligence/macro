#!/usr/bin/env python3
"""Build the Winner Health board -> site/winner_health.html (TOP ANATOMY W1).

Pure SSR, the `stage_analysis` page-builder pattern: load the committed context
artifact, render one template, write through `lib.pages.write_page`. The page
ships NO fetch, NO chart library and NO page JS of its own — the sparklines are
inline SSR SVG and every Tier-2 card is a static LENS block — so there is no
per-surface JSON to copy into `site/` and no lazy-load step.

Fail-soft source handling: missing, unreadable, malformed, undated and stale
artifacts render distinct unavailable states, never a claim that a read will
finish shortly. Producer null reasons remain diagnostics, not display copy.
`main()` returns 0 when a page was written and 1 on a render/write failure.

Design contract: research/top_anatomy/W1_SURFACE_DESIGN_SPEC.md (visual law) +
docs/DESIGN_DOCTRINE.md (content law, wins on conflict). Display tier, zero
authority.

Usage:
    python -m scripts.build_winner_health_page
    python -m scripts.build_winner_health_page --root /path/to/repo
    python -m scripts.build_winner_health_page --fixture tests/fixtures/winner_health_demo.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Literal, TypedDict

from jinja2 import Environment, FileSystemLoader, Undefined

log = logging.getLogger("build_winner_health_page")

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_CONTEXT_REL = Path("top_maturation") / "latest.json"
#: Calendar days after which the read is treated as not landed. The page's own as-of
#: stamp is the last PRICED bar, so a stale artifact would otherwise print an old
#: date beside a live-looking board.
_MAX_AGE_DAYS = 6

AvailabilityCode = Literal["available", "missing", "unreadable",
                           "invalid_artifact", "invalid_date", "stale",
                           "producer_unavailable"]


class SourceAvailability(TypedDict):
    """Page-local evidence about loading the source, not a market judgement."""

    code: AvailabilityCode
    source_asof: str | None


def _availability(code: AvailabilityCode,
                  source_day: datetime.date | None = None) -> SourceAvailability:
    return {"code": code,
            "source_asof": source_day.isoformat() if source_day is not None else None}


def _data_dir(root: Path) -> Path:
    """Resolve the data dir the way the engines do, else `<root>/data`."""
    try:
        sys.path.insert(0, str(root))
        from lib import config as _cfg  # noqa: PLC0415
        return Path(_cfg.data_dir())
    except Exception:  # noqa: BLE001
        return root / "data"


def _load_context_result(
    data_dir: Path, fixture: Path | None = None
) -> tuple[dict | None, SourceAvailability]:
    """Read once and keep source failure evidence separate from market states.

    The explicit fixture path retains its existing date-admission bypass.
    Neither free-form producer null_reason nor exception text is display data.
    """
    try:
        path = fixture.resolve() if fixture is not None else (data_dir / _CONTEXT_REL)
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # Also covers disappearance between path resolution and the actual read.
        log.info("winner health source is missing")
        return None, _availability("missing")
    except (json.JSONDecodeError, RecursionError):
        log.warning("winner health source is not usable JSON")
        return None, _availability("invalid_artifact")
    except Exception as exc:  # noqa: BLE001
        log.warning("winner health source could not be loaded (%s)", exc)
        return None, _availability("unreadable")
    if not isinstance(raw, dict):
        log.warning("winner health source is not an object")
        return None, _availability("invalid_artifact")
    source_day = _source_date(raw)
    if fixture is None:
        if source_day is None:
            return None, _availability("invalid_date")
        if (datetime.date.today() - source_day).days > _MAX_AGE_DAYS:
            return None, _availability("stale", source_day)
    if raw.get("null_state"):
        # Existing truthy malformed flags must not turn into an available board.
        # Do not infer a cause from the producer's raw exception string.
        code: AvailabilityCode = (
            "producer_unavailable" if raw["null_state"] is True else "invalid_artifact"
        )
        return raw, _availability(code, source_day)
    return raw, _availability("available", source_day)


def _load_context(data_dir: Path, fixture: Path | None = None) -> dict | None:
    """Compatibility view: return the existing admitted context or None."""
    return _load_context_result(data_dir, fixture)[0]


def _source_date(ctx: dict) -> datetime.date | None:
    """Preserve the admitted date-prefix parser, including calendar validation."""
    try:
        y, m, d = (int(x) for x in str(ctx.get("asof", ""))[:10].split("-"))
        # Numeric date parts can still describe an impossible calendar day.
        return datetime.date(y, m, d)
    except Exception:  # noqa: BLE001
        return None


def _is_stale(ctx: dict) -> bool:
    """Compatibility predicate: invalid or older than six calendar days."""
    asof = _source_date(ctx)
    return asof is None or (datetime.date.today() - asof).days > _MAX_AGE_DAYS


def render(root: Path, fixture: Path | None = None) -> str:
    """Render winner_health.html.j2 and return the HTML string."""
    context, availability = _load_context_result(_data_dir(root), fixture)
    # Failed source payloads must not leak live-looking prices, backdrop or counts.
    wh = context if availability["code"] == "available" else None

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
        undefined=Undefined,
    )
    # The included partials (_site_nav / _seo_head) call td()/tr(); a missing
    # global is a hard build crash, so they are wired with the same try/except
    # fallback the stage-analysis builder uses.
    try:
        sys.path.insert(0, str(root))
        from engine import i18n  # noqa: PLC0415
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:  # noqa: BLE001
        from markupsafe import Markup  # noqa: PLC0415

        def _td(en):  # bilingual span, ZH falls back to EN
            return Markup('<span class="l-en">{}</span>'
                          '<span class="l-zh">{}</span>').format(en, en)

        env.globals.update(td=_td, tr=lambda en: en)

    return env.get_template("winner_health.html.j2").render(
        wh=wh, wh_availability=availability
    )


def build(root: Path, fixture: Path | None = None) -> Path:
    """Render the page and write it through the ONLY sanctioned write path."""
    html = render(root, fixture=fixture)
    out_path = root / "site" / "winner_health.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # write_page injects the depth-aware data-base shim. A raw write_text ships
    # the page without it and points every shared fetch at Pages instead of R2 —
    # the regression called out in the stage-analysis builder.
    from lib.pages import write_page  # noqa: PLC0415
    write_page(out_path, html)
    log.info("wrote %s (%d KB)", out_path, len(html) // 1024)
    return out_path


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Render winner_health.html")
    ap.add_argument("--root", default=None, help="Repo root (default: auto-detect)")
    ap.add_argument("--fixture", default=None,
                    help="Load this JSON as the context instead of the live artifact")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve() if a.root else _REPO_ROOT
    fixture = Path(a.fixture).resolve() if a.fixture else None
    try:
        build(root, fixture=fixture)
    except Exception as exc:  # noqa: BLE001 — a page builder never takes the lane down
        print(f"::warning title=winner-health-page::render failed ({exc})", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
