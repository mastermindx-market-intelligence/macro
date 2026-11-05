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
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
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


def _day(value: object) -> date | None:
    """Read a declared ISO date, never a build-clock substitute."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _lock_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    direct = _day(value)
    if direct is not None:
        return direct
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _utc_now(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)


def _snapshot_display(msp: dict | None, now: datetime | None = None) -> dict:
    """Keep the gamma observation clock independent of artifact and build clocks."""
    now = _utc_now(now)
    gamma = (msp or {}).get("gamma")
    gamma = gamma if isinstance(gamma, dict) else {}
    coverage = gamma.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    observed = _day(coverage.get("last_obs")) or _day(gamma.get("asof"))
    missing = set()
    for field in ("missing_recent", "missing_in_regime"):
        rows = coverage.get(field)
        if isinstance(rows, list):
            missing.update(str(day) for value in rows if (day := _day(value)) is not None)
    state, expected, valid_until = "unknown", None, None
    if observed is not None:
        try:
            from lib import nyse_calendar
            expected = nyse_calendar.expected_last_session(now)
            state = "stale" if observed < expected else "dated" if observed <= now.astimezone(ZoneInfo("America/New_York")).date() else "future"
            following = nyse_calendar.sessions_between(expected + timedelta(days=1), expected + timedelta(days=14))
            if following:
                valid_until = datetime.combine(following[0], time(17), tzinfo=ZoneInfo("America/New_York")).isoformat()
        except (ImportError, ValueError, OverflowError):
            state = "unknown"
    return {
        "spot": gamma.get("spot") if _finite_number(gamma.get("spot")) else None,
        "flip": gamma.get("gamma_flip") if _finite_number(gamma.get("gamma_flip")) else None,
        "regime": gamma.get("regime") if gamma.get("regime") in ("long", "short") else None,
        "observed": observed.isoformat() if observed else None,
        "state": state, "expected": expected.isoformat() if expected else None,
        "valid_until": valid_until, "missing_count": len(missing), "missing_dates": sorted(missing),
        "coverage_incomplete": coverage.get("complete") is False or bool(missing),
    }


def _weekly_clock(wm: dict, now: datetime | None = None) -> dict:
    """Qualify the supplied trading week using the existing NYSE calendar."""
    now = _utc_now(now)
    start, end, locked = _day(wm.get("week_start")), _day(wm.get("week_end")), _lock_day(wm.get("locked_at"))
    result = {"phase": "unknown", "starts_at": None, "expires_at": None,
              "week_start": str(start) if start else None, "week_end": str(end) if end else None,
              "locked_day": str(locked) if locked else None}
    if not (start and end and locked and locked < start <= end and (end-start).days <= 6):
        return result
    try:
        from lib import nyse_calendar
        sessions = nyse_calendar.sessions_between(start, end)
        if not sessions:
            return result
        et = ZoneInfo("America/New_York")
        begins = datetime.combine(sessions[0], time(), tzinfo=et)
        # Use the shared calendar's conservative 17:00 ET completion convention.
        expires = datetime.combine(sessions[-1], time(17), tzinfo=et)
        if locked != nyse_calendar.last_session_on_or_before(start - timedelta(days=1)) or locked > nyse_calendar.expected_last_session(now):
            return result
        phase = "expired" if now >= expires else "upcoming" if now < begins else "current"
        result.update(phase=phase, starts_at=begins.isoformat(), expires_at=expires.isoformat())
    except (ImportError, ValueError, OverflowError):
        pass
    return result


def _weekly_display(msp: dict | None, now: datetime | None = None) -> dict:
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
    spot_supplied = _finite_number(spot)
    spot = spot if spot_supplied else close
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
            "close": close, "spot": spot, "spot_supplied": spot_supplied, "flip": flip,
            "spot_x": spot_x, "flip_x": flip_x, **_weekly_clock(wm, now)}


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
    now = datetime.now(timezone.utc)
    return tpl.render(msp=msp, wm_view=_weekly_display(msp, now), snapshot_view=_snapshot_display(msp, now))


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
