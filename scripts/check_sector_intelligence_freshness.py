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
import re
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
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _read_json(path: Path, errors: list[str]) -> tuple[dict[str, Any] | None, bytes | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        errors.append(f"{path.relative_to(path.parents[2])} is absent or unreadable: {exc}")
        return None, None
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(f"{path.name} is not valid JSON: {exc}")
        return None, raw
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return None, raw
    return payload, raw


def _html_metadata(path: Path, errors: list[str]) -> dict[str, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"site/sector_central.html is absent or unreadable: {exc}")
        return {key: None for key in _HTML_ATTRS}
    out: dict[str, str | None] = {}
    for key, attr in _HTML_ATTRS.items():
        match = re.search(rf'\b{re.escape(attr)}="([^"]+)"', text)
        out[key] = match.group(1) if match else None
        if match is None:
            errors.append(f"site/sector_central.html is missing {attr}")
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
    sector, _ = _read_json(site / "sectordata" / "sector_central.json", errors)
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
            sessions_behind = nyse_calendar.sessions_behind(common_as_of, now)
        except Exception as exc:  # noqa: BLE001 - calendar failure is fail closed here
            errors.append(f"NYSE calendar unavailable: {exc!r}")
        else:
            if sessions_behind > max_sessions_behind:
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
