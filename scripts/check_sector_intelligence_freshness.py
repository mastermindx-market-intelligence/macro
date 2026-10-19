"""Fail-closed semantic freshness gate for US Sector Intelligence.

The page is a composition of several independently written artifacts. A new mtime or
successful render is not proof that those artifacts describe the same market session.
This validator binds the exact basket and action-board bytes to the rendered pair and
checks the shared date against the completed-session NYSE calendar.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import nyse_calendar  # noqa: E402
_ACTION_LANES = (
    "buy_now", "buy_soon", "on_the_run", "take_profits", "hold", "avoid",
)
_HTML_ATTRS = {
    "as_of": "data-si-as-of",
    "baskets_sha256": "data-si-baskets-sha256",
    "action_board_sha256": "data-si-action-board-sha256",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        if len(value) > 10 and value[10] in ("T", " "):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return None
    except ValueError:
        return None


def _refuse_nonfinite_json(token: str) -> None:
    # stdlib json.loads accepts Python's NaN/Infinity extensions by default;
    # browsers do not, so the release validator must be at least as strict.
    raise ValueError(f"nonstandard JSON number {token!r} is forbidden")


def _read_json(path: Path, errors: list[str]) -> tuple[dict[str, Any] | None, bytes | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        errors.append(f"{path.relative_to(path.parents[2])} is absent or unreadable: {exc}")
        return None, None
    try:
        payload = json.loads(raw, parse_constant=_refuse_nonfinite_json)
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(f"{path.name} is not valid JSON: {exc}")
        return None, raw
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return None, raw
    return payload, raw


class _SectorHeroParser(HTMLParser):
    """Read the actual served hero tag, ignoring scripts and HTML comments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heroes: list[list[tuple[str, str | None]]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag != "section":
            return
        classes = [value for name, value in attrs if name == "class"]
        if any(value and "rvx-hero" in value.split() for value in classes):
            self.heroes.append(attrs)


def _read_sector_runtime_js(
    path: Path, sector_raw: bytes | None, errors: list[str],
) -> bytes | None:
    """Pin the actual browser-consumed JS to the same exact JSON generation.

    build_sector_central writes both files from the SAME compact JSON value.
    Parsing only sectordata/sector_central.json cannot prove what the page
    actually executes; a stale JS file otherwise survives a good JSON check.
    """
    try:
        actual = path.read_bytes()
    except OSError as exc:
        errors.append(f"SECTOR INTELLIGENCE RUNTIME ASSET MISSING: {path.name}: {exc}")
        return None
    if sector_raw is not None:
        expected = b"window.SECTOR_CENTRAL=" + sector_raw + b";\n"
        if actual != expected:
            errors.append(
                "SECTOR INTELLIGENCE CLIENT-DATA SPLIT: sector_central_data.js "
                "does not match the exact sectordata/sector_central.json generation"
            )
    return actual


def _html_metadata(path: Path, errors: list[str]) -> dict[str, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"site/sector_central.html is absent or unreadable: {exc}")
        return {key: None for key in _HTML_ATTRS}

    parser = _SectorHeroParser()
    try:
        parser.feed(text)
        parser.close()
    except ValueError as exc:
        errors.append(f"site/sector_central.html has invalid markup: {exc}")
        return {key: None for key in _HTML_ATTRS}
    if len(parser.heroes) != 1:
        errors.append(
            "site/sector_central.html must have exactly one rvx-hero section "
            f"for source verification (found {len(parser.heroes)})"
        )
    # Diagnostic values may be printed, but an extra or missing hero ALWAYS
    # fails the release. No attribute from another DOM node can supply the
    # missing source clock or byte stamps.
    attrs = parser.heroes[0] if len(parser.heroes) == 1 else []
    out: dict[str, str | None] = {}
    for key, name in _HTML_ATTRS.items():
        values = [value for attr, value in attrs if attr == name]
        if len(values) != 1 or not values[0]:
            out[key] = None
            errors.append(
                f"site/sector_central.html is missing {name}"
                if not values else
                f"site/sector_central.html has ambiguous {name}"
            )
        else:
            out[key] = values[0]
    return out

def _require_date(
    label: str,
    value: object,
    errors: list[str],
    dates: dict[str, date],
) -> None:
    parsed = _parse_date(value)
    if parsed is None:
        errors.append(f"{label} carries no usable as_of ({value!r})")
        return
    dates[label] = parsed


def _check_hash(
    label: str,
    recorded: object,
    actual: str,
    errors: list[str],
) -> None:
    if recorded != actual:
        errors.append(
            f"{label} mismatch: recorded {recorded!r}, actual {actual}"
        )


def evaluate(
    root: Path,
    *,
    now: datetime | None = None,
    max_sessions_behind: int = 1,
) -> dict[str, Any]:
    """Evaluate one repo/site tree without modifying it."""
    root = Path(root)
    site = root / "site"
    errors: list[str] = []
    warnings: list[str] = []
    baskets, baskets_raw = _read_json(site / "basketdata" / "baskets.json", errors)
    action, action_raw = _read_json(site / "basketdata" / "action_board.json", errors)
    sector, sector_raw = _read_json(site / "sectordata" / "sector_central.json", errors)
    sector_js_raw = _read_sector_runtime_js(
        site / "sector_central_data.js", sector_raw, errors,
    )
    premium, _ = _read_json(site / "premiumdata" / "sector_central.json", errors)
    html = _html_metadata(site / "sector_central.html", errors)

    dates: dict[str, date] = {}
    if baskets is not None:
        _require_date("site/basketdata/baskets.json:as_of", baskets.get("as_of"), errors, dates)
        _require_date(
            "site/basketdata/baskets.json:theme_intel.as_of",
            (baskets.get("theme_intel") or {}).get("as_of")
            if isinstance(baskets.get("theme_intel"), dict) else None,
            errors,
            dates,
        )
    # Baskets embed an independent US market-breadth observation read from
    # data/breadth/breadth.parquet. Its source session must not be laundered by
    # theme_intel.as_of when the basket renderer advances independently.
    if baskets is not None:
        theme_intel = baskets.get("theme_intel")
        breadth = theme_intel.get("market_concentration") if isinstance(theme_intel, dict) else None
        if breadth is not None and breadth != {}:
            if not isinstance(breadth, dict):
                errors.append("site/basketdata/baskets.json:market_concentration must be an object")
            else:
                _require_date(
                    "site/basketdata/baskets.json:theme_intel.market_concentration.source_as_of",
                    breadth.get("source_as_of"), errors, dates,
                )
                if breadth.get("source_universe") != "sp500_current_constituents":
                    errors.append(
                        "UNVERIFIED SECTOR INTELLIGENCE BREADTH UNIVERSE: "
                        "embedded US concentration must identify its observed S&P 500 source; "
                        "it does not qualify S&P 1500 participation"
                    )
    if action is not None:
        _require_date("site/basketdata/action_board.json:as_of", action.get("as_of"), errors, dates)
        board = action.get("action_board")
        if not isinstance(board, dict):
            errors.append("site/basketdata/action_board.json:action_board must be an object")
        else:
            lane_count = sum(
                len(board.get(lane) or [])
                for lane in _ACTION_LANES
                if isinstance(board.get(lane) or [], list)
            )
            total = board.get("total")
            if not isinstance(total, int):
                total = lane_count
            if total <= 0 or lane_count <= 0:
                errors.append("Sector Intelligence action board is empty")
    if sector is not None:
        _require_date("site/sectordata/sector_central.json:as_of", sector.get("as_of"), errors, dates)
    if premium is not None:
        _require_date(
            "site/premiumdata/sector_central.json:as_of",
            premium.get("as_of"),
            errors,
            dates,
        )
    _require_date(
        "site/sector_central.html:data-si-as-of",
        html.get("as_of"),
        errors,
        dates,
    )

    actual_baskets_sha = _sha256(baskets_raw) if baskets_raw is not None else None
    actual_action_sha = _sha256(action_raw) if action_raw is not None else None
    if actual_baskets_sha is not None and action is not None:
        _check_hash(
            "site/basketdata/action_board.json:baskets_sha256",
            action.get("baskets_sha256"),
            actual_baskets_sha,
            errors,
        )
    if premium is not None and actual_baskets_sha is not None:
        _check_hash(
            "site/premiumdata/sector_central.json:baskets_sha256",
            premium.get("baskets_sha256"),
            actual_baskets_sha,
            errors,
        )
    if premium is not None and actual_action_sha is not None:
        _check_hash(
            "site/premiumdata/sector_central.json:action_board_sha256",
            premium.get("action_board_sha256"),
            actual_action_sha,
            errors,
        )
    if actual_baskets_sha is not None:
        _check_hash(
            "site/sector_central.html:data-si-baskets-sha256",
            html.get("baskets_sha256"),
            actual_baskets_sha,
            errors,
        )
    if actual_action_sha is not None:
        _check_hash(
            "site/sector_central.html:data-si-action-board-sha256",
            html.get("action_board_sha256"),
            actual_action_sha,
            errors,
        )

    common_as_of: date | None = None
    unique_dates = sorted(set(dates.values()))
    if len(unique_dates) > 1:
        detail = ", ".join(
            f"{label}={value.isoformat()}" for label, value in sorted(dates.items())
        )
        errors.append(f"SECTOR INTELLIGENCE VINTAGE SPLIT: {detail}")
    elif len(unique_dates) == 1:
        common_as_of = unique_dates[0]

    sessions_behind: int | None = None
    if common_as_of is not None:
        try:
            last_completed = nyse_calendar.expected_last_session(now)
            valid_session = nyse_calendar.is_session(common_as_of)
            # sessions_behind alone cannot validate a date: future-dated and
            # weekend observations both return zero missing completed sessions.
            if not valid_session:
                errors.append(
                    "INVALID SECTOR INTELLIGENCE MARKET SESSION: common as_of="
                    f"{common_as_of.isoformat()} is not an NYSE session"
                )
            if common_as_of > last_completed:
                errors.append(
                    "FUTURE SECTOR INTELLIGENCE: common as_of="
                    f"{common_as_of.isoformat()} exceeds last completed NYSE "
                    f"session {last_completed.isoformat()}"
                )
            if valid_session and common_as_of <= last_completed:
                sessions_behind = nyse_calendar.sessions_behind(common_as_of, now)
        except Exception as exc:  # noqa: BLE001 - calendar failure is fail closed here
            errors.append(f"NYSE calendar unavailable: {exc!r}")
        else:
            if sessions_behind is not None and sessions_behind > max_sessions_behind:
                errors.append(
                    "STALE SECTOR INTELLIGENCE: common as_of="
                    f"{common_as_of.isoformat()} is {sessions_behind} completed NYSE "
                    f"sessions behind (limit {max_sessions_behind})"
                )

    facts: dict[str, Any] = {
        "as_of": common_as_of.isoformat() if common_as_of else None,
        "sessions_behind": sessions_behind,
        "dates": {label: value.isoformat() for label, value in dates.items()},
        "baskets_sha256": actual_baskets_sha,
        "action_board_sha256": actual_action_sha,
        "sector_json_sha256": _sha256(sector_raw) if sector_raw is not None else None,
        "sector_js_sha256": _sha256(sector_js_raw) if sector_js_raw is not None else None,
    }
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "facts": facts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--max-sessions-behind", type=int, default=1)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    report = evaluate(
        args.root,
        now=datetime.now(timezone.utc),
        max_sessions_behind=max(0, args.max_sessions_behind),
    )
    if not args.quiet:
        for warning in report["warnings"]:
            print(f"::warning title=sector-intelligence-freshness::{warning}")
        for error in report["errors"]:
            print(f"::error title=sector-intelligence-freshness::{error}")
        facts = report["facts"]
        print(
            "sector intelligence freshness | as_of={} behind={} ok={}".format(
                facts.get("as_of"), facts.get("sessions_behind"), report["ok"]
            )
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
