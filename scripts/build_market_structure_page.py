"""Build the Market Structure page -> site/market_structure.html.

Reads  data/market_structure/latest.json  (schema market_structure_context.v1)
and renders templates/market_structure.html.j2.

The artifact is display_only / context-only — no authority signals, no sized
inputs.  This builder is intentionally thin: the engine that writes
latest.json lives in engine/market_structure_context.py (not yet built).
For MSP Wave 2 the builder loads whatever latest.json exists, passes it to
the Jinja template as `msp`, and renders.  Absent artifact → msp=None →
template shows warm-up placeholders for every panel.

Usage:
    python -m scripts.build_market_structure          # uses repo root auto-detect
    python -m scripts.build_market_structure_page --root /path/to/repo
    python -m scripts.build_market_structure_page --fixture tests/fixtures/market_structure_latest.json
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Undefined

log = logging.getLogger("build_market_structure_page")

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Relative path inside the data dir where the engine writes the artifact.
_ARTIFACT_REL = Path("market_structure") / "latest.json"


def _load_msp(root: Path, fixture: Path | None = None) -> dict | None:
    """Load the market structure artifact.  Returns None on any failure."""
    if fixture is not None:
        path = fixture.resolve()
    else:
        try:
            sys.path.insert(0, str(root))
            from lib import config as _cfg  # noqa: PLC0415
            path = _cfg.data_dir() / _ARTIFACT_REL
        except Exception:  # noqa: BLE001
            path = root / "data" / _ARTIFACT_REL

    if not path.exists():
        log.info("market_structure artifact not found at %s — warm-up state", path)
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            log.warning("market_structure artifact is not a dict; warm-up state")
            return None
        return raw
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load market_structure artifact: %s; warm-up state", exc)
        return None


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _weekly_display(msp: dict | None) -> dict:
    """Project supplied prices into display geometry; never synthesize a band."""
    wm = (msp or {}).get("week_map")
    gamma = (msp or {}).get("gamma") or {}
    if not isinstance(wm, dict):
        return {"present": False}
    bands = []
    values = []
    for sigma in (1, 2):
        lo, hi = wm.get(f"band_{sigma}sigma_lo"), wm.get(f"band_{sigma}sigma_hi")
        valid = _finite_number(lo) and _finite_number(hi) and lo <= hi
        band = {"sigma": sigma, "available": valid, "lo": lo if valid else None, "hi": hi if valid else None}
        if valid:
            values.extend([lo, hi])
        bands.append(band)
    close = wm.get("locked_close")
    close = close if _finite_number(close) else None
    spot = gamma.get("spot") if isinstance(gamma, dict) else None
    spot_live = _finite_number(spot)
    spot = spot if spot_live else close
    flip = wm.get("gamma_flip")
    flip = flip if _finite_number(flip) else None
    values.extend(v for v in (close, spot, flip) if v is not None)
    if values:
        low, high = min(values), max(values)
        padding = max(abs(low) * .01, .5) if high == low else (high - low) * .08
        low, high = low - padding, high + padding
        def x(value: float) -> float:
            return round(18 + (value - low) / (high - low) * 564, 3)
        for band in bands:
            if band["available"]:
                band.update(x=x(band["lo"]), width=x(band["hi"]) - x(band["lo"]))
        spot_x = x(spot) if spot is not None else None
        flip_x = x(flip) if flip is not None else None
    else:
        spot_x = flip_x = None
    return {"present": True, "bands": bands, "has_band": any(b["available"] for b in bands),
            "close": close, "spot": spot, "spot_live": spot_live, "flip": flip,
            "spot_x": spot_x, "flip_x": flip_x}


def render(root: Path, fixture: Path | None = None) -> str:
    """Render market_structure.html.j2 and return the HTML string."""
    msp = _load_msp(root, fixture)

    templates_dir = root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
        undefined=Undefined,
    )

    # Wire bilingual helpers so templates that use td() / tr() don't crash.
    try:
        sys.path.insert(0, str(root))
        from engine import i18n  # noqa: PLC0415
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:  # noqa: BLE001
        pass  # template defines t() as a local macro; td() only used in footer

    env.globals["finite_number"] = _finite_number
    tpl = env.get_template("market_structure.html.j2")
    return tpl.render(msp=msp, wm_view=_weekly_display(msp))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Render market_structure.html")
    parser.add_argument("--root", default=None, help="Repo root (default: auto-detect)")
    parser.add_argument(
        "--fixture",
        default=None,
        help="Load this JSON file instead of the live artifact",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else _REPO_ROOT
    fixture = Path(args.fixture).resolve() if args.fixture else None

    out_path = root / "site" / "market_structure.html"

    try:
        html = render(root, fixture=fixture)
    except Exception as exc:  # noqa: BLE001
        log.error("render failed: %s", exc, exc_info=True)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # write_page is the ONLY write path. The raw-write fallback that used to sit
    # here caught every exception and silently shipped the page without the
    # data-base shim — its per-ticker fetches pointed at Pages instead of R2, and
    # the render lane's inject_data_base sweep healed the committed copy, so the
    # regression was invisible except in a standalone builder run. It was also
    # unreachable in practice: render() above already imports engine.i18n and
    # reads templates/ from this same root, so `lib.pages` cannot fail to import
    # where render() succeeded.
    from lib.pages import write_page  # noqa: PLC0415
    write_page(out_path, html)

    kb = len(html) // 1024
    log.info("wrote %s (%d KB)", out_path, kb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
