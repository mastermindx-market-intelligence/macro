"""Canonical package contract for US Sector Participation W1.

Import-light deterministic authority shared by the licensed-data producer,
Sector Central builder and public projection.  It acquires no market data and
assigns no forecast or trade authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

PACKAGE_SCHEMA = "sector_participation_20.v1"
GENERATION_SCHEMA = "sector_participation_20.generation.v1"
MEMBER_STATES = frozenset({"A", "B", "H", "M", "I", "U"})
PRICE_BASIS = "split_adjusted"
PUBLIC_URL = "sectordata/sector_participation_20.json"
CLIENT_ASSET = "sector_participation_20.js"


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"W1 {label} must be a nonempty string")
    return value


def _iso_date(value: Any, label: str) -> date:
    text = _required_text(value, label)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"W1 {label} must be an ISO date") from exc


def _utc_clock(value: Any, label: str) -> datetime:
    text = _required_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"W1 {label} must be an ISO UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"W1 {label} must carry an explicit UTC offset")
    return parsed


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonicalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def observation_material(package: dict) -> dict:
    """Canonical economic/analytical evidence, excluding generation clocks."""
    material = copy.deepcopy(package)
    material.pop("generation_id", None)
    material.pop("observation_id", None)
    material.pop("computed_at", None)
    material.pop("published_at", None)
    source = material.get("source")
    if isinstance(source, dict):
        source.pop("acquired_at", None)
    return canonicalize(material)


def observation_id(package: dict) -> str:
    encoded = json.dumps(
        observation_material(package), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def generation_material(package: dict) -> dict:
    """Canonical receipt for one qualification/computation of an observation."""
    reference = package.get("reference") if isinstance(package, dict) else None
    source = package.get("source") if isinstance(package, dict) else None
    return canonicalize({
        "schema": GENERATION_SCHEMA,
        "observation_id": package.get("observation_id") if isinstance(package, dict) else None,
        "roster_id": reference.get("roster_id") if isinstance(reference, dict) else None,
        "response_set_id": source.get("response_set_id") if isinstance(source, dict) else None,
        "source_acquired_at": source.get("acquired_at") if isinstance(source, dict) else None,
        "computed_at": package.get("computed_at") if isinstance(package, dict) else None,
    })


def generation_id(package: dict) -> str:
    encoded = json.dumps(
        generation_material(package), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def json_bytes(package: dict) -> bytes:
    return (json.dumps(package, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def validate_package(package: dict) -> None:
    """Fail closed on malformed or cross-generation W1 evidence."""
    if not isinstance(package, dict) or package.get("schema") != PACKAGE_SCHEMA:
        raise ValueError("invalid W1 package schema")
    if package.get("observation_id") != observation_id(package):
        raise ValueError("W1 observation digest mismatch")
    if package.get("generation_id") != generation_id(package):
        raise ValueError("W1 generation digest mismatch")

    method = package.get("method")
    expected_legend = {
        "A": "eligible_above_ma20",
        "B": "eligible_equal_or_below_ma20",
        "H": "insufficient_history",
        "M": "required_expected_session_missing",
        "I": "invalid_identity_basis_or_observation",
        "U": "source_request_unavailable_or_refused",
    }
    if (not isinstance(method, dict)
            or method.get("name") != "sector_participation_20"
            or type(method.get("window_sessions")) is not int
            or method.get("window_sessions") != 20
            or method.get("comparison") != "close > MA20"
            or method.get("coverage_basis")
            != "complete expected NYSE sessions through selected session"
            or method.get("display_floor")
            != {"min_eligible": 5, "min_coverage": 0.9}
            or method.get("state_legend") != expected_legend):
        raise ValueError("W1 method contract is malformed")
    _utc_clock(package.get("computed_at"), "computation clock")
    _utc_clock(package.get("published_at"), "publication clock")

    sessions = package.get("sessions")
    if not isinstance(sessions, list) or not sessions or any(
            not isinstance(item, str) for item in sessions):
        raise ValueError("W1 sessions must be a nonempty string list")
    try:
        parsed_sessions = [date.fromisoformat(item) for item in sessions]
    except ValueError as exc:
        raise ValueError("W1 sessions contain a non-date") from exc
    if parsed_sessions != sorted(set(parsed_sessions)):
        raise ValueError("W1 sessions must be strictly increasing and unique")

    sectors = package.get("sectors")
    members = package.get("members")
    if (not isinstance(sectors, dict) or not sectors
            or not isinstance(members, dict) or not members):
        raise ValueError("W1 sectors and members must be nonempty mappings")

    n_sessions = len(sessions)
    roster_pairs: list[tuple[str, str, str]] = []
    by_sector: dict[str, list[dict]] = {sector: [] for sector in sectors}
    source_failure_members = 0
    for symbol, member in members.items():
        if not isinstance(symbol, str) or not isinstance(member, dict):
            raise ValueError("W1 member identity is malformed")
        name = member.get("name")
        sector = member.get("sector")
        states = member.get("states")
        distances = member.get("distance_bps")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"W1 member {symbol} lacks a display identity")
        if sector not in sectors:
            raise ValueError(f"W1 member {symbol} points at an unknown sector")
        if (not isinstance(states, str) or len(states) != n_sessions
                or any(state not in MEMBER_STATES for state in states)):
            raise ValueError(f"W1 member {symbol} has invalid state alignment")
        if len(set(states)) == 1 and states[0] in {"I", "U"}:
            source_failure_members += 1
        if not isinstance(distances, list) or len(distances) != n_sessions:
            raise ValueError(f"W1 member {symbol} has invalid distance alignment")
        for state, distance in zip(states, distances):
            if state in ("A", "B"):
                if (isinstance(distance, bool)
                        or not isinstance(distance, (int, float))
                        or not math.isfinite(float(distance))):
                    raise ValueError(f"W1 member {symbol} lacks an eligible distance")
            elif distance is not None:
                raise ValueError(
                    f"W1 member {symbol} has distance on excluded state {state}")
        href = member.get("href")
        if href != "stock.html#" + quote(symbol, safe=""):
            raise ValueError(
                f"W1 member {symbol} lacks the existing research destination")
        roster_pairs.append((symbol, name, sector))
        by_sector[sector].append(member)

    reference = package.get("reference")
    roster_encoded = json.dumps(
        sorted(roster_pairs), separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    roster_id = "sha256:" + hashlib.sha256(roster_encoded).hexdigest()
    if (not isinstance(reference, dict)
            or reference.get("universe") != "S&P 500"
            or reference.get("member_count") != len(members)
            or reference.get("roster_id") != roster_id
            or reference.get("observed_at") is not None
            or not isinstance(reference.get("reconstruction"), str)
            or not reference["reconstruction"].strip()
            or not isinstance(reference.get("reconstruction_zh"), str)
            or not reference["reconstruction_zh"].strip()):
        raise ValueError("W1 reference roster identity is inconsistent")

    any_rate = False
    for sector, row in sectors.items():
        if not isinstance(row, dict):
            raise ValueError(f"W1 sector {sector} is malformed")
        for key in ("above", "eligible", "expected", "pct"):
            if not isinstance(row.get(key), list) or len(row[key]) != n_sessions:
                raise ValueError(f"W1 sector {sector} has misaligned {key}")
        excluded = row.get("excluded")
        if not isinstance(excluded, dict):
            raise ValueError(f"W1 sector {sector} lacks exclusions")
        for state in ("H", "M", "I", "U"):
            if (not isinstance(excluded.get(state), list)
                    or len(excluded[state]) != n_sessions):
                raise ValueError(
                    f"W1 sector {sector} has misaligned exclusion {state}")

        sector_members = by_sector.get(sector) or []
        for position in range(n_sessions):
            count_values = [row[key][position] for key in ("above", "eligible", "expected")]
            count_values.extend(excluded[state][position] for state in ("H", "M", "I", "U"))
            if any(type(value) is not int or value < 0 for value in count_values):
                raise ValueError(f"W1 sector {sector} contains a non-integer count")
            states = [member["states"][position] for member in sector_members]
            above = states.count("A")
            eligible = above + states.count("B")
            expected = len(states)
            if (row["above"][position] != above
                    or row["eligible"][position] != eligible
                    or row["expected"][position] != expected):
                raise ValueError(
                    f"W1 sector {sector} counts disagree with member states")
            for state in ("H", "M", "I", "U"):
                if excluded[state][position] != states.count(state):
                    raise ValueError(
                        f"W1 sector {sector} exclusion counts disagree")
            wanted_pct = (100.0 * above / eligible
                          if eligible >= 5 and eligible >= 0.9 * expected else None)
            actual_pct = row["pct"][position]
            if wanted_pct is None:
                if actual_pct is not None:
                    raise ValueError(
                        f"W1 sector {sector} published a rate below its floor")
            else:
                any_rate = True
                if (isinstance(actual_pct, bool)
                        or not isinstance(actual_pct, (int, float))
                        or not math.isfinite(float(actual_pct))
                        or abs(float(actual_pct) - wanted_pct) > 1e-9):
                    raise ValueError(
                        f"W1 sector {sector} rate disagrees with member states")
    if package.get("available") is not any_rate:
        raise ValueError("W1 availability disagrees with sector evidence")

    source = package.get("source")
    request_identity = source.get("request_identity") if isinstance(source, dict) else None
    if (not isinstance(source, dict)
            or source.get("provider") != "licensed_vendor"
            or source.get("basis") != PRICE_BASIS
            or not _is_sha256(source.get("response_set_id"))
            or not isinstance(request_identity, dict)
            or request_identity.get("resource")
            != "/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
            or request_identity.get("adjusted") is not True
            or request_identity.get("sort") != "asc"
            or request_identity.get("limit") != 50000):
        raise ValueError("W1 source identity is malformed")

    requested_start = _iso_date(source.get("requested_start"), "requested start")
    requested_end = _iso_date(source.get("requested_end"), "requested end")
    latest_expected = _iso_date(
        source.get("latest_expected_session"), "latest expected session")
    if requested_start > parsed_sessions[0] or requested_end != parsed_sessions[-1]:
        raise ValueError("W1 requested range does not contain the public evidence sessions")
    if latest_expected != requested_end:
        raise ValueError("W1 latest expected session disagrees with requested end")
    source_session_value = source.get("source_session")
    if source_session_value is not None:
        source_session = _iso_date(source_session_value, "source session")
        if source_session < requested_start or source_session > requested_end:
            raise ValueError("W1 source session is outside the qualified source range")

    requested_count = source.get("requested_member_count")
    accepted_count = source.get("accepted_member_count")
    unavailable_count = source.get("unavailable_member_count")
    if (type(requested_count) is not int or requested_count != len(members)
            or type(accepted_count) is not int
            or type(unavailable_count) is not int
            or accepted_count < 0 or unavailable_count < 0
            or accepted_count + unavailable_count != requested_count
            or unavailable_count != source_failure_members
            or accepted_count != len(members) - source_failure_members):
        raise ValueError("W1 source coverage counts are inconsistent")
    if package.get("available") and source_session_value is None:
        raise ValueError("W1 available evidence requires a source session")
    acquired_at = source.get("acquired_at")
    if accepted_count > 0:
        _utc_clock(acquired_at, "acquisition clock")
    elif acquired_at is not None:
        _utc_clock(acquired_at, "acquisition clock")


def atomic_replace_bytes(blob: bytes, target: Path) -> None:
    """Replace one file atomically after a same-directory durable temp write."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def write_validated_package(package: dict, target: Path) -> bytes:
    """Validate, serialize and atomically replace one canonical generation."""
    validate_package(package)
    blob = json_bytes(package)
    validate_package(json.loads(blob.decode("utf-8")))
    atomic_replace_bytes(blob, Path(target))
    return blob


def read_public_pointer(
    *, source_path: Path, site: Path | None = None,
    current_expected_session: str, logger: Any | None = None,
) -> dict:
    """Validate/project exact package bytes and return the lightweight UI pointer."""
    source_path = Path(source_path)
    if not source_path.exists():
        return {"status": "missing", "available": False,
                "note": "not yet published"}
    try:
        blob = source_path.read_bytes()
        package = json.loads(blob.decode("utf-8"))
        validate_package(package)
        if site is not None:
            atomic_replace_bytes(blob, Path(site) / PUBLIC_URL)
        source = package["source"]
        source_session = source.get("source_session")
        latest_expected = source.get("latest_expected_session")
        stale = bool(
            (source_session and latest_expected and source_session < latest_expected)
            or (latest_expected and current_expected_session
                and latest_expected < current_expected_session)
        )
        available = bool(package.get("available"))
        status = ("stale" if stale else "ready") if available else "withheld"
        pointer = {
            "status": status,
            "available": available,
            "generation_id": package["generation_id"],
            "observation_id": package["observation_id"],
            "source_session": source_session,
            "latest_expected_session": latest_expected,
            "current_expected_session": current_expected_session,
            "published_at": package.get("published_at"),
            "computed_at": package.get("computed_at"),
            "basis": source.get("basis"),
            "roster_id": (package.get("reference") or {}).get("roster_id"),
            "stale": stale,
        }
        if status in {"ready", "stale"}:
            pointer["url"] = PUBLIC_URL
        return pointer
    except Exception as exc:  # noqa: BLE001 — caller remains fail-soft
        if logger is not None:
            logger.warning(
                "sector_central: W1 participation package refused: %s", exc)
        return {"status": "invalid", "available": False,
                "note": "invalid package"}


def copy_client_asset(*, template_root: Path, site: Path) -> bool:
    """Project the one W1 browser asset through the existing page build."""
    source = Path(template_root) / CLIENT_ASSET
    if not source.exists():
        return False
    Path(site).mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, Path(site) / CLIENT_ASSET)
    return True
