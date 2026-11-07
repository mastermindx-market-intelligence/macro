"""Read-only current owner context for the recovered Leadership Lab.

This module does not create leader states, theme states, identities, scores,
probabilities, entry permissions, or historical replays. It projects a small
whitelist from incumbent owners without touching recovered ordering/authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
import re

from engine.leadership_lab.measurement import finite_number, session_date


_CONTEXT_AUTHORITY = {
    "rank": False,
    "entry": False,
    "size": False,
    "execution": False,
    "trade": False,
}
_RERATING_CHIPS = (
    "revision_positive",
    "revision_breadth_60",
    "multiple_compressed",
    "earnings_within_14d",
)
_RS_WINDOWS = ("1W", "1M", "3M", "6M", "1Y")
_EPISODE_GENERATION_RE = re.compile(r"peg:[0-9a-f]{64}")


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _iso_date(value: object) -> str | None:
    try:
        return session_date(value)
    except (TypeError, ValueError):
        return None


def _iso_datetime(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return value


def _day(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) == 10:
        return _iso_date(value)
    parsed = _iso_datetime(value)
    return parsed[:10] if parsed else None


def _strict_bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _safe_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    values = {_text(item) for item in value}
    return sorted(item for item in values if item is not None)


def _unique_rows(rows: object, key: str) -> tuple[dict[str, Mapping], set[str]]:
    unique: dict[str, Mapping] = {}
    ambiguous: set[str] = set()
    if not isinstance(rows, list):
        return unique, ambiguous
    for row in rows:
        if not isinstance(row, Mapping) or (identity := _text(row.get(key))) is None:
            continue
        if identity in unique or identity in ambiguous:
            unique.pop(identity, None)
            ambiguous.add(identity)
        else:
            unique[identity] = row
    return unique, ambiguous


def _theme_authority_ok(payload: Mapping) -> bool:
    auth = payload.get("authority")
    return (
        isinstance(auth, Mapping)
        and auth.get("is_context_only") is True
        and auth.get("display_only") is True
        and auth.get("not_a_signal") is True
        and auth.get("may_rank") is False
        and auth.get("may_gate") is False
        and auth.get("may_size") is False
        and auth.get("may_escalate") is False
        and all(value is False for key, value in auth.items()
                if isinstance(key, str) and key.startswith("may_"))
    )


def _radar_status(payload: object) -> tuple[bool, dict]:
    if not isinstance(payload, Mapping) or payload.get("schema") != "leader_radar.v2":
        return False, {"status": "UNAVAILABLE", "reason": "INVALID_OR_MISSING_RADAR"}
    as_of = _iso_date(payload.get("as_of"))
    built_at = _iso_datetime(payload.get("built_at"))
    if as_of is None or built_at is None or not isinstance(payload.get("rows"), list):
        return False, {"status": "UNAVAILABLE", "reason": "INVALID_OR_MISSING_RADAR"}

    freshness_in = payload.get("freshness")
    freshness = {}
    if isinstance(freshness_in, Mapping):
        for key in (
            "price_through", "breadth_through", "rs_series_through",
            "regime_as_of", "revisions_asof", "state_history_through", "built_at",
        ):
            value = freshness_in.get(key)
            if isinstance(value, str) or value is None:
                freshness[key] = value

    return True, {
        "status": "AVAILABLE",
        "schema": "leader_radar.v2",
        "as_of": as_of,
        "built_at": built_at,
        "freshness": freshness,
        "history_since": _iso_date(payload.get("history_since")),
        "history_gaps": _safe_string_list(payload.get("history_gaps")),
    }


def _radar_row(row: object) -> dict:
    if not isinstance(row, Mapping):
        return {"status": "UNAVAILABLE", "reason": "NO_RADAR_ROW"}
    tracked = row.get("tracked_sessions")
    if isinstance(tracked, bool) or not isinstance(tracked, int) or tracked < 0:
        tracked = None
    entry_out = None
    entry = row.get("entry_read")
    if isinstance(entry, Mapping):
        entry_out = {
            "key": _text(entry.get("key")),
            "caveats": _safe_string_list(entry.get("caveats")),
            "basis": _safe_string_list(entry.get("basis")),
            "extension_pct_50d": finite_number(entry.get("extension_pct_50d")),
        }
    return {
        "status": "AVAILABLE",
        "state": _text(row.get("state")),
        "tracked_sessions": tracked,
        "entry_read": entry_out,
        "breakaway_watch_state": _text(row.get("breakaway_watch_state")),
    }


def _rerating_row(row: object) -> dict:
    if not isinstance(row, Mapping):
        return {"status": "UNAVAILABLE", "reason": "NO_RERATING_WATCH_ROW"}
    chips_in = row.get("chips")
    chips = {
        key: _strict_bool_or_none(chips_in.get(key)) if isinstance(chips_in, Mapping) else None
        for key in _RERATING_CHIPS
    }
    return {
        "status": "AVAILABLE",
        "state": _text(row.get("state")),
        "chips": chips,
        "interpretation": "descriptive owner context; not probability, rank, or entry permission",
    }


def _subsector(row: object) -> dict | None:
    if not isinstance(row, Mapping):
        return None
    key = _text(row.get("key"))
    if key is None:
        return None
    rs_in = row.get("rs")
    rs = {
        window: finite_number(rs_in.get(window)) if isinstance(rs_in, Mapping) else None
        for window in _RS_WINDOWS
    }
    return {"key": key, "quadrant": _text(row.get("quadrant")), "rs": rs}


def _theme_projection(row: Mapping) -> dict | None:
    theme_id = _text(row.get("theme_id"))
    if theme_id is None:
        return None
    foresight = row.get("foresight")
    rotation = row.get("subsector_rotation")
    subsectors = []
    if isinstance(rotation, Mapping):
        for item in rotation.get("subsectors") or []:
            projected = _subsector(item)
            if projected is not None:
                subsectors.append(projected)
    subsectors.sort(key=lambda item: item["key"])
    return {
        "theme_id": theme_id,
        "name_en": _text(row.get("name_en")) or theme_id,
        "name_zh": _text(row.get("name_zh")) or _text(row.get("name_en")) or theme_id,
        "foresight_stage": _text(foresight.get("stage")) if isinstance(foresight, Mapping) else None,
        "rotation_quadrant": _text(rotation.get("rollup_quadrant")) if isinstance(rotation, Mapping) else None,
        "subsectors": subsectors,
        "subsector_keys": _safe_string_list(row.get("subsector_keys")),
    }


def _known_after_recovery(
    source_session: str, *, radar_meta: Mapping,
    theme_as_of: str | None, theme_generated_at: str | None,
) -> bool:
    dates: list[str] = []
    for value in (radar_meta.get("as_of"), radar_meta.get("built_at"),
                  theme_as_of, theme_generated_at):
        day = _day(value) if isinstance(value, str) else None
        if day is not None:
            dates.append(day)
    freshness = radar_meta.get("freshness")
    if isinstance(freshness, Mapping):
        for value in freshness.values():
            day = _day(value) if isinstance(value, str) else None
            if day is not None:
                dates.append(day)
    return any(day > source_session for day in dates)


def _episode_projection(row: Mapping) -> dict | None:
    if row.get("schema") != "prophet.candidate_episode/v1":
        return None
    ticker = _text(row.get("ticker_at_observation"))
    episode_id = _text(row.get("episode_id"))
    company_id = _text(row.get("company_id"))
    security_id = _text(row.get("security_id"))
    identity_epoch = _text(row.get("identity_epoch"))
    identity_epoch_state = _text(row.get("identity_epoch_state"))
    episode_state = _text(row.get("episode_state"))
    opened_session = _iso_date(row.get("opened_session"))
    opened_at = _iso_datetime(row.get("opened_at"))
    last_observed_at = _iso_datetime(row.get("last_observed_at"))
    observation_count = row.get("observation_count")
    intake_classes = _safe_string_list(row.get("intake_classes"))
    if (
        ticker is None or episode_id is None or company_id is None or security_id is None
        or identity_epoch is None or identity_epoch_state is None or episode_state is None
        or opened_session is None or opened_at is None or last_observed_at is None
        or isinstance(observation_count, bool) or not isinstance(observation_count, int)
        or observation_count < 0
    ):
        return None
    return {
        "status": "AVAILABLE",
        "episode_id": episode_id,
        "company_id": company_id,
        "security_id": security_id,
        "identity_epoch": identity_epoch,
        "identity_epoch_state": identity_epoch_state,
        "episode_state": episode_state,
        "opened_session": opened_session,
        "opened_at": opened_at,
        "last_observed_at": last_observed_at,
        "observation_count": observation_count,
        "intake_classes": intake_classes,
    }


def _episode_owner(
    episode_book: Mapping | None, episode_generation_id: str | None,
) -> tuple[dict, dict[str, dict], set[str]]:
    unavailable = {
        "status": "UNAVAILABLE",
        "reason": "EPISODE_OWNER_NOT_CONNECTED",
        "generation_id": episode_generation_id,
    }
    if (
        not isinstance(episode_book, Mapping)
        or episode_book.get("schema") != "prophet.all_candidates/v1"
        or not isinstance(episode_book.get("episodes"), list)
        or not isinstance(episode_generation_id, str)
        or _EPISODE_GENERATION_RE.fullmatch(episode_generation_id) is None
    ):
        unavailable["reason"] = "INVALID_OR_MISSING_EPISODE_OWNER"
        return unavailable, {}, set()

    by_ticker: dict[str, dict] = {}
    duplicates: set[str] = set()
    for raw in episode_book.get("episodes") or []:
        if not isinstance(raw, Mapping):
            continue
        projection = _episode_projection(raw)
        if projection is None:
            continue
        ticker = _text(raw.get("ticker_at_observation"))
        if ticker in by_ticker:
            duplicates.add(ticker)
            by_ticker.pop(ticker, None)
            continue
        if ticker not in duplicates:
            by_ticker[ticker] = projection

    coverage = episode_book.get("coverage")
    safe_coverage = {}
    if isinstance(coverage, Mapping):
        for key in ("active", "episodes", "suppressed_inputs"):
            value = coverage.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                safe_coverage[key] = value
    return {
        "status": "AVAILABLE",
        "schema": "prophet.all_candidates/v1",
        "generation_id": episode_generation_id,
        "definition_era": _text(episode_book.get("definition_era")),
        "coverage": safe_coverage,
        "identity_scope": "CURRENT_EPISODE_IDS_ONLY_NOT_HISTORICAL",
    }, by_ticker, duplicates


def compose_current_context(
    recovery: Mapping, radar: Mapping | None, theme_state: Mapping | None, *,
    context_ref: str, episode_book: Mapping | None = None,
    episode_generation_id: str | None = None,
) -> dict:
    """Attach strictly contextual current owner reads to a recovery projection."""
    if (not isinstance(recovery, Mapping)
            or recovery.get("schema") != "mastermind.leadership_lab.recovery.v1"):
        raise ValueError("leadership recovery projection required")
    if not isinstance(context_ref, str) or not re.fullmatch(r"[0-9a-f]{40}", context_ref):
        raise ValueError("context_ref must be an exact lowercase Git commit SHA")
    source_session = _iso_date(recovery.get("source_session"))
    if source_session is None:
        raise ValueError("recovery source_session must be a valid session date")

    result = deepcopy(dict(recovery))
    rows = result.get("rows")
    shortlist = result.get("shortlist")
    if not isinstance(rows, list) or not isinstance(shortlist, list):
        raise ValueError("recovery rows and shortlist required")

    radar_ok, radar_meta = _radar_status(radar)
    radar_by_ticker: dict[str, Mapping] = {}
    rerating_by_ticker: dict[str, Mapping] = {}
    ambiguous_radar: set[str] = set()
    ambiguous_rerating: set[str] = set()
    if radar_ok and isinstance(radar, Mapping):
        radar_by_ticker, ambiguous_radar = _unique_rows(radar.get("rows"), "ticker")
        rerating_by_ticker, ambiguous_rerating = _unique_rows(radar.get("rerating_watch"), "ticker")

    theme_status = {
        "status": "UNAVAILABLE",
        "reason": "INVALID_OR_MISSING_THEME_STATE",
        "as_of": None,
        "generated_at": None,
    }
    theme_by_basket: dict[str, list[dict]] = {}
    theme_as_of = None
    theme_generated = None
    limitations = ["CURRENT_CONTEXT_NOT_HISTORICAL_REPLAY"]

    if isinstance(theme_state, Mapping) and theme_state.get("schema") == "neuralweb.theme_state.v1":
        theme_as_of = _iso_date(theme_state.get("as_of"))
        theme_generated = _iso_datetime(theme_state.get("generated_at"))
        if not _theme_authority_ok(theme_state):
            theme_status = {
                "status": "REFUSED_AUTHORITY_DRIFT",
                "reason": "THEME_STATE_AUTHORITY_DRIFT",
                "as_of": theme_as_of,
                "generated_at": theme_generated,
            }
            limitations.append("THEME_STATE_AUTHORITY_DRIFT")
        elif theme_as_of is None or theme_generated is None or not isinstance(theme_state.get("themes"), list):
            theme_status = {
                "status": "UNAVAILABLE",
                "reason": "INVALID_OR_MISSING_THEME_STATE",
                "as_of": theme_as_of,
                "generated_at": theme_generated,
            }
        else:
            theme_status = {
                "status": "AVAILABLE",
                "schema": "neuralweb.theme_state.v1",
                "as_of": theme_as_of,
                "generated_at": theme_generated,
                "authority": "CONTEXT_ONLY",
            }
            unique_themes, ambiguous_themes = _unique_rows(theme_state.get("themes"), "theme_id")
            if ambiguous_themes:
                limitations.append("AMBIGUOUS_THEME_IDS")
            for item in unique_themes.values():
                projected = _theme_projection(item)
                if projected is None:
                    continue
                for basket_id in _safe_string_list(item.get("basket_ids")):
                    theme_by_basket.setdefault(basket_id, []).append(projected)
            for values in theme_by_basket.values():
                values.sort(key=lambda item: item["theme_id"])

    episode_meta, episode_by_ticker, episode_duplicates = _episode_owner(
        episode_book, episode_generation_id)
    if episode_meta["status"] == "AVAILABLE":
        limitations.append("HISTORICAL_IDENTITY_NOT_QUALIFIED")
        global_identity = "CURRENT_EPISODE_IDS_FOR_MATCHED_ROWS_ONLY_NOT_HISTORICAL"
    else:
        limitations.append("IDENTITY_NOT_CONNECTED")
        global_identity = "NOT_CONNECTED_CURRENT_ONLY_OWNER_NOT_YET_BOUND"

    if not radar_ok:
        limitations.append("RADAR_CONTEXT_UNAVAILABLE")
    if _known_after_recovery(
        source_session, radar_meta=radar_meta,
        theme_as_of=theme_as_of, theme_generated_at=theme_generated,
    ):
        limitations.append("CONTEXT_KNOWN_AFTER_RECOVERY_SESSION")

    global_context = {
        "schema": "mastermind.leadership_lab.current_context.v1",
        "context_ref": context_ref,
        "mode": "CURRENT_OWNER_CONTEXT_ONLY",
        "historical_replay_qualified": False,
        "identity_qualification": global_identity,
        "radar": radar_meta,
        "theme_state": theme_status,
        "episode_book": episode_meta,
        "limitations": sorted(set(limitations)),
        "authority": dict(_CONTEXT_AUTHORITY),
    }

    def enrich(row: object) -> dict:
        if not isinstance(row, Mapping):
            raise ValueError("recovery row must be a mapping")
        out = deepcopy(dict(row))
        ticker = _text(out.get("ticker"))
        if ticker is None:
            raise ValueError("recovery row ticker required")
        memberships = out.get("themes")
        basket_ids = sorted({
            _text(item.get("id"))
            for item in memberships
            if isinstance(item, Mapping) and _text(item.get("id")) is not None
        }) if isinstance(memberships, list) else []
        themes: dict[str, dict] = {}
        if theme_status["status"] == "AVAILABLE":
            for basket_id in basket_ids:
                for theme in theme_by_basket.get(basket_id, ()):
                    themes.setdefault(theme["theme_id"], deepcopy(theme))
        if ticker in episode_duplicates:
            episode = {
                "status": "UNAVAILABLE",
                "reason": "AMBIGUOUS_MULTIPLE_CURRENT_EPISODES",
            }
        elif ticker in episode_by_ticker:
            episode = deepcopy(episode_by_ticker[ticker])
        else:
            episode = {"status": "UNAVAILABLE", "reason": "NO_CURRENT_EPISODE"}
        row_identity = (
            "CURRENT_EPISODE_NATIVE_IDS_NOT_HISTORICAL"
            if episode["status"] == "AVAILABLE"
            else "NOT_CONNECTED_CURRENT_ONLY_OWNER_NOT_YET_BOUND"
        )
        out["current_context"] = {
            "status": "AVAILABLE" if radar_ok or themes or episode["status"] == "AVAILABLE" else "PARTIAL",
            "radar": _radar_row(radar_by_ticker.get(ticker)) if radar_ok
                     else {"status": "UNAVAILABLE", "reason": "RADAR_SOURCE_UNAVAILABLE"},
            "rerating": _rerating_row(rerating_by_ticker.get(ticker)) if radar_ok
                        else {"status": "UNAVAILABLE", "reason": "RADAR_SOURCE_UNAVAILABLE"},
            "episode": episode,
            "themes": [themes[key] for key in sorted(themes)],
            "theme_membership_count": len(themes),
            "independent_confirmation_count": None,
            "identity_qualification": row_identity,
            "historical_replay_qualified": False,
            "forecast_probability": None,
            "authority": dict(_CONTEXT_AUTHORITY),
        }
        if ticker in ambiguous_radar:
            out["current_context"]["radar"] = {
                "status": "UNAVAILABLE", "reason": "AMBIGUOUS_RADAR_ROWS"}
        if ticker in ambiguous_rerating:
            out["current_context"]["rerating"] = {
                "status": "UNAVAILABLE", "reason": "AMBIGUOUS_RERATING_ROWS"}
        return out

    result["rows"] = [enrich(row) for row in rows]
    result["shortlist"] = [enrich(row) for row in shortlist]
    result["current_context"] = global_context
    return result
