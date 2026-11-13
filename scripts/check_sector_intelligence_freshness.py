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
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import market_session  # noqa: E402
# Shared by the build gate and the external served-generation observer.
ARTIFACT_PATHS = (
    "basketdata/baskets.json",
    "basketdata/action_board.json",
    "sectordata/sector_central.json",
    "premiumdata/sector_central.json",
    "sector_central.html",
)

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


def _read_json(
    path: Path, errors: list[str], read_bytes: Callable[[Path], bytes],
) -> tuple[dict[str, Any] | None, bytes | None]:
    try:
        raw = read_bytes(path)
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


def _html_metadata(
    path: Path, errors: list[str], read_bytes: Callable[[Path], bytes],
) -> dict[str, str | None]:
    try:
        text = read_bytes(path).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"site/sector_central.html is absent or unreadable: {exc}")
        return {key: None for key in _HTML_ATTRS}
    # Non-greedy so text between two comments survives; an unclosed
    # ``<!--`` hides the rest of the page from a browser, so it does here too.
    text = re.sub(r"<!--.*?(?:-->|\Z)", "", text, flags=re.S)
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



def check_action_board(action: dict[str, Any]) -> list[str]:
    """Shared semantic shape check; both publication surfaces use the same lanes."""
    board = action.get("action_board")
    if not isinstance(board, dict):
        return ["site/basketdata/action_board.json:action_board must be an object"]
    lane_count = sum(
        len(board.get(lane) or [])
        for lane in _ACTION_LANES
        if isinstance(board.get(lane) or [], list)
    )
    total = board.get("total")
    if not isinstance(total, int):
        total = lane_count
    if total <= 0 or lane_count <= 0:
        return ["Sector Intelligence action board is empty"]
    return []


def check_basket_dependency(action: dict[str, Any], baskets_raw: bytes) -> list[str]:
    """The board must name the exact captured baskets bytes, including revisions."""
    errors: list[str] = []
    _check_hash("site/basketdata/action_board.json:baskets_sha256",
                action.get("baskets_sha256"), _sha256(baskets_raw), errors)
    return errors


def evaluate_session_age(
    as_of: date, *, now: datetime | None = None, max_sessions_behind: int = 1,
) -> dict[str, Any]:
    """Shared source-session policy over the published US calendar and one clock.

    This helper does not read artifacts or decide whether a generation is coherent.
    It raises on unavailable or unverified calendar coverage. The legacy evaluator preserves its error
    vocabulary; native consumers can distinguish invalid, developing and old data.
    The existing default budget remains one completed session.
    """
    observed_at = datetime.now(timezone.utc) if now is None else now
    today = market_session.market_local_date("US", observed_at)
    if not market_session.calendar_verified("US", today.year):
        raise ValueError("published US calendar is unverified")
    expected = market_session.expected_session("US", observed_at)
    # An exact lag across missing annual notices must not be called verified.
    first_year = min(as_of.year, expected.year, today.year)
    last_year = max(as_of.year, expected.year, today.year)
    if not all(market_session.calendar_verified("US", year)
               for year in range(first_year, last_year + 1)):
        raise ValueError("published US calendar coverage is incomplete")
    latest = today if market_session.is_session_date("US", today) else expected
    behind = market_session.missed_sessions("US", as_of, expected)
    return {
        "as_of": as_of,
        "sessions_behind": behind,
        "latest_possible_session": latest,
        "expected_session": expected,
        "calendar_verified": True,
        "is_session": market_session.is_session_date("US", as_of),
        "future": as_of > latest,
        "developing": as_of > expected,
        "age_breach": behind > max_sessions_behind,
    }


def evaluate(
    root: Path,
    *,
    now: datetime | None = None,
    max_sessions_behind: int = 1,
    site_dir: Path | None = None,
    read_bytes: Callable[[Path], bytes] | None = None,
) -> dict[str, Any]:
    """Evaluate one generation without modifying it.

    The CLI reads root/site. The external sentinel supplies the actual served
    root and a stable in-memory byte snapshot; neither path invokes a builder.
    """
    root = Path(root)
    site = Path(site_dir) if site_dir is not None else root / "site"
    read_bytes = Path.read_bytes if read_bytes is None else read_bytes
    errors: list[str] = []
    warnings: list[str] = []
    baskets, baskets_raw = _read_json(site / "basketdata" / "baskets.json", errors, read_bytes)
    action, action_raw = _read_json(site / "basketdata" / "action_board.json", errors, read_bytes)
    sector, _ = _read_json(site / "sectordata" / "sector_central.json", errors, read_bytes)
    premium, _ = _read_json(site / "premiumdata" / "sector_central.json", errors, read_bytes)
    html = _html_metadata(site / "sector_central.html", errors, read_bytes)

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
        errors.extend(check_action_board(action))
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
        errors.extend(check_basket_dependency(action, baskets_raw))
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
    calendar_unavailable = False
    if common_as_of is not None:
        try:
            age = evaluate_session_age(common_as_of, now=now,
                                       max_sessions_behind=max_sessions_behind)
            sessions_behind = age["sessions_behind"]
            latest_possible_session = age["latest_possible_session"]
        except Exception as exc:  # noqa: BLE001 - calendar failure is fail closed here
            calendar_unavailable = True
            errors.append(f"NYSE calendar unavailable: {exc!r}")
        else:
            if common_as_of > latest_possible_session:
                errors.append(
                    f"Sector Intelligence as_of={common_as_of.isoformat()} is ahead of "
                    f"the current NYSE session {latest_possible_session.isoformat()}"
                )
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
    # A failed observation is not proof of old data. Keep the build gate
    # fail-closed while allowing the external sentinel's existing blindness
    # escalation to distinguish unreadable/unsupported generations from a
    # stable generation whose date or integrity is demonstrably wrong.
    unavailable = (
        calendar_unavailable
        or any(doc is None for doc in (baskets, action, sector, premium))
        or len(dates) != 6
        or any(value is None for value in html.values())
        or not isinstance((action or {}).get("action_board"), dict)
    )
    # A conclusive old-source watermark must not be hidden by another missing
    # field (the observed 2026-11-05 production bundle has both conditions).
    age_breach = sessions_behind is not None and sessions_behind > max_sessions_behind
    status = "stale" if age_breach else (
        "indeterminate" if unavailable else ("stale" if errors else "ok")
    )
    reason = (
        "data_out_of_date" if age_breach
        else "freshness_unavailable" if unavailable
        else "publication_inconsistent" if errors
        else "current"
    )
    return {
        "ok": not errors,
        "status": status,
        "reason": reason,
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
