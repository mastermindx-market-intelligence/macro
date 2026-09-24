"""FDA Drug Shortage collector — first orphan-rescue feed (Wave 5b / §3.4).

Probes the openFDA drug/shortages endpoint (https://api.fda.gov/drug/shortages.json)
to capture active and resolved drug shortages. Keyless, bounded, non-fatal on failure.

Schema observed at build-time (2026-07-02) via empirical probe:
  generic_name     str   — INN + dosage form
  status           str   — "Current" | "Resolved" | "To Be Discontinued" | absent
  availability     str   — "Available" | "Limited Availability" | "Unavailable" | absent
  initial_posting_date  str  — MM/DD/YYYY
  discontinued_date     str  — MM/DD/YYYY | absent
  update_date           str  — MM/DD/YYYY | absent

The endpoint serves 1,637 records as of 2026-07-02 at keyless rate (no API key required
for low-volume access). Paginated with skip+limit. We fetch all records and cache them
to data/fda/shortages.parquet (append-only, deduped on package_ndc+initial_posting_date).

Display-only; degrades to None / empty on any network failure; never raises into the build.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from lib import config

log = logging.getLogger(__name__)


def _legacy_parse_clock():
    return datetime.now(timezone.utc)


SHORTAGES_URL = "https://api.fda.gov/drug/shortages.json"
PAGE_SIZE = 100       # openFDA max per request
MAX_PAGES = 25        # cap: 2500 records; avoids runaway loop
PACE_S = 0.4          # polite pacing between pages
SCHEMA = "fda_shortages_observation.v1"
HISTORY_COLUMNS = [
    "first_observed_generation", "last_observed_generation",
    "absent_since_generation", "previous_status", "status_changed_generation",
    "capture_known",
]


def _shortages_path():
    p = config.data_dir() / "fda" / "shortages.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _fetch_page(skip: int, limit: int = PAGE_SIZE) -> dict:
    """Fetch one page from the openFDA shortages endpoint. Returns the raw JSON dict."""
    params = {"limit": limit, "skip": skip}
    headers = {"User-Agent": "python-requests/2.32 (macro-dashboard; contact@macro-dashboard.dev)"}
    r = requests.get(SHORTAGES_URL, params=params, headers=headers, timeout=40)
    if r.status_code in (429, 500, 502, 503, 504):
        raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
    r.raise_for_status()
    return r.json()


def _parse_record(*args) -> dict:
    rec = args[0]
    """Flatten one openFDA shortages record into a flat row."""
    openfda = rec.get("openfda") or {}
    brands = openfda.get("brand_name") or []
    substances = openfda.get("substance_name") or []
    required_text = {
        "package_ndc": rec.get("package_ndc"),
        "generic_name": rec.get("generic_name"),
        "status": rec.get("status"),
        "availability": rec.get("availability"),
        "initial_posting_date": rec.get("initial_posting_date"),
        "update_date": rec.get("update_date"),
    }
    if any(value is not None and not isinstance(value, str) for value in required_text.values()):
        raise TypeError("malformed shortage row")
    fetched_utc = args[1] if len(args) == 2 else _legacy_parse_clock()
    return {
        **{name: value or "" for name, value in required_text.items()},
        "brand_name": brands[0] if isinstance(brands, list) and brands else None,
        "substance_name": substances[0] if isinstance(substances, list) and substances else None,
        "discontinued_date": rec.get("discontinued_date") if isinstance(rec.get("discontinued_date"), str) or rec.get("discontinued_date") is None else "",
        "therapeutic_category": (rec.get("therapeutic_category") or [None])[0] if isinstance(rec.get("therapeutic_category") or [None], list) else "",
        "company_name": rec.get("company_name") if isinstance(rec.get("company_name"), str) else None,
        "related_info": rec.get("related_info") if isinstance(rec.get("related_info"), str) else None,
        "fetched_utc": fetched_utc.astimezone(timezone.utc).isoformat(),
    }


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _sidecar_path(path):
    return path.with_suffix(".observation.json")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _empty_history_frame():
    return pd.DataFrame(columns=["package_ndc", "initial_posting_date", *HISTORY_COLUMNS])


def _staged_parquet_bytes(frame):
    staged_path = f".fda-shortages-staged-{os.getpid()}.parquet"
    try:
        frame.to_parquet(staged_path, engine="pyarrow")
        with open(staged_path, "rb") as staged_file:
            return staged_file.read()
    finally:
        try:
            os.unlink(staged_path)
        except FileNotFoundError:
            pass


def _write_unselected_rows(path, rows):
    staged_bytes = _staged_parquet_bytes(_normalise_legacy(pd.DataFrame(rows)))

    def write(staged):
        staged.write_bytes(staged_bytes)

    _write_staged(path, write)


def _observation_result(capture, rows, *, qualified, failure_code):
    return {
        "qualified": qualified,
        "failure_code": failure_code,
        "rows": rows,
        "capture": capture,
    }


def collect_shortage_sweep(fetch_page, *, clock, page_size, max_pages) -> dict:
    """Collect one bounded sweep through the supplied page function.

    A stable key is `(package_ndc, initial_posting_date)`. Rows lacking either
    value are rejected as `KEY_ABSENT`; malformed values are rejected as
    `MALFORMED_ROW`. Matching counts establish a complete interval sweep, not
    snapshot isolation.
    """
    started = clock()
    raw_count = 0
    unique_count = 0
    reported_total = None
    source_generation = None
    rows_by_key = {}
    seen_pages = set()
    failure_code = None
    pages = 0

    for page_number in range(max_pages):
        try:
            data = fetch_page(pages * page_size, page_size)
        except Exception:
            failure_code = "FIRST_PAGE_OUTAGE" if pages == 0 else "PAGE_FAILED"
            break

        if not isinstance(data, dict):
            failure_code = "PAGE_FAILED" if pages else "FIRST_PAGE_OUTAGE"
            break
        meta = data.get("meta") or {}
        results_meta = meta.get("results") or {}
        total = results_meta.get("total")
        generation = meta.get("last_updated")
        if not isinstance(total, int) or isinstance(total, bool):
            failure_code = "PAGE_FAILED" if pages else "FIRST_PAGE_OUTAGE"
            break
        if reported_total is None:
            reported_total = total
            source_generation = generation
        elif total != reported_total:
            failure_code = "COUNT_DRIFT"
            break
        elif generation != source_generation:
            failure_code = "GENERATION_DRIFT"
            break

        results = data.get("results")
        if not isinstance(results, list):
            failure_code = "PAGE_FAILED" if pages else "FIRST_PAGE_OUTAGE"
            break
        page_rows = []
        page_keys = []
        for raw_row in results:
            raw_count += 1
            if not isinstance(raw_row, dict):
                failure_code = "MALFORMED_ROW"
                break
            if "openfda" in raw_row and not isinstance(raw_row.get("openfda"), dict):
                failure_code = "MALFORMED_ROW"
                break
            try:
                parsed = _parse_record(raw_row, started)
            except (TypeError, ValueError, AttributeError, KeyError, IndexError):
                failure_code = "MALFORMED_ROW"
                break
            package_ndc = parsed.get("package_ndc")
            posting_date = parsed.get("initial_posting_date")
            if package_ndc in (None, "") or posting_date in (None, ""):
                failure_code = "KEY_ABSENT"
                break
            parsed["observed_generation"] = source_generation
            key = (package_ndc, posting_date)
            page_rows.append(parsed)
            page_keys.append(key)
            if key not in rows_by_key:
                rows_by_key[key] = parsed
                unique_count += 1
        if failure_code:
            break
        page_identity = tuple(page_keys)
        if page_identity in seen_pages:
            failure_code = "REPEATED_PAGE"
            break
        seen_pages.add(page_identity)
        pages += 1
        if unique_count >= reported_total:
            break
        if pages == max_pages:
            failure_code = "CAP_BEFORE_TOTAL"
            break

    finished = clock()
    if failure_code is None and not (
        isinstance(source_generation, str) and source_generation
    ):
        failure_code = "NO_SOURCE_GENERATION"
    complete = failure_code is None and reported_total is not None and unique_count == reported_total
    capture = {
        "started_at": _iso_utc(started),
        "finished_at": _iso_utc(finished),
        "source_generation": source_generation,
        "pages": pages,
        "page_size": page_size,
        "max_pages": max_pages,
        "raw_count": raw_count,
        "unique_count": unique_count,
        "reported_total": reported_total,
        "complete": complete,
        "atomic_snapshot_proven": False,
        "acquisition_interval_s": float((finished - started).total_seconds()),
    }
    return _observation_result(
        capture, [] if failure_code else list(rows_by_key.values()),
        qualified=complete and failure_code is None, failure_code=failure_code,
    )


def _write_staged(path, write):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        write(staged)
        os.replace(staged, path)
    finally:
        if staged.exists():
            staged.unlink()


def _normalise_legacy(frame):
    normalised = frame.copy()
    for column in HISTORY_COLUMNS:
        if column not in normalised:
            normalised[column] = None
    normalised["capture_known"] = normalised.get("capture_known").map(lambda value: bool(value) if pd.notna(value) else False)
    return normalised


def format_observation_receipt(observation: dict) -> str:
    capture = (observation or {}).get("capture") or {}
    refresh = (observation or {}).get("last_refresh") or {}
    source_generation = capture.get("source_generation")
    attempted_at = refresh.get("attempted_at")
    return (
        f"fda_shortages: observation qualified={bool(refresh.get('qualified'))} "
        f"failure_code={refresh.get('failure_code') or 'none'} "
        f"source_generation={source_generation if isinstance(source_generation, str) else 'unknown'} "
        f"last_refresh={attempted_at if isinstance(attempted_at, str) else 'none'} "
        f"legacy={bool((observation or {}).get('legacy'))} "
        f"inconsistent={bool((observation or {}).get('inconsistent'))}"
    )


def _selected_state(path):
    sidecar = _sidecar_path(path)
    if not path.exists() and not sidecar.exists():
        return {
            "rows": None, "capture": None, "last_refresh": None,
            "history_coverage": {
                "earliest_qualified_generation": None,
                "legacy_rows_capture_unknown": False,
                "forward_retention_started_at": None,
            }, "legacy": False, "inconsistent": False,
        }
    if not sidecar.exists():
        inconsistent = False
        rows = _empty_history_frame()
        if path.exists():
            try:
                rows = pd.read_parquet(path)
            except Exception:
                rows = None
                inconsistent = True
        return {
            "rows": rows, "capture": None, "last_refresh": None,
            "history_coverage": {
                "earliest_qualified_generation": None,
                "legacy_rows_capture_unknown": True,
                "forward_retention_started_at": None,
            }, "legacy": True, "inconsistent": inconsistent,
        }
    try:
        receipt = json.loads(sidecar.read_text())
    except Exception:
        return {
            "rows": None, "capture": None, "last_refresh": None,
            "history_coverage": {}, "retention": {}, "legacy": False,
            "inconsistent": True,
        }
    coverage = receipt.get("history_coverage", {})
    expected = receipt.get("parquet_sha256")
    digest = _digest(path)
    inconsistent = expected is not None and digest != expected
    rows = None
    if expected is not None and path.exists() and not inconsistent:
        try:
            rows = pd.read_parquet(path)
        except Exception:
            rows = None
            inconsistent = True
    return {
        "rows": rows,
        "capture": receipt.get("selected_capture") if not inconsistent else None,
        "last_refresh": receipt.get("last_refresh"),
        "history_coverage": coverage,
        "retention": receipt.get("retention") or {},
        "legacy": False, "inconsistent": inconsistent,
    }


def _json_dumps(receipt):
    return json.dumps(receipt, sort_keys=True, indent=2)


def save_shortage_observation(result, *, path, expected_predecessor) -> dict:
    """Persist one observation with a same-checkout predecessor fence.

    This stores current rows plus absence/status-change metadata; not a history
    ledger. Atomic rename is not multi-writer fencing. The predecessor fence
    covers concurrent writers on one checkout only; cross-checkout lineage
    divergence is caught by the parquet digest, not by this fence.
    """
    sidecar = _sidecar_path(path)
    on_disk_predecessor = _digest(sidecar)
    if on_disk_predecessor != expected_predecessor:
        return {
            "promoted": False, "reason": "PREDECESSOR_MISMATCH",
            "predecessor": on_disk_predecessor,
        }

    capture = result.get("capture") or {}
    state = _selected_state(path)
    selected = state.get("capture") or {}
    unselected_rows = result.get("rows")
    if result.get("qualified") and (
        not isinstance(capture.get("source_generation"), str)
        or not capture.get("source_generation")
    ):
        result = {
            **result,
            "qualified": False,
            "failure_code": "NO_SOURCE_GENERATION",
            "rows": [],
        }
    if result.get("qualified"):
        if selected:
            if (capture.get("source_generation") or "") < (selected.get("source_generation") or ""):
                return {"promoted": False, "reason": "GENERATION_REGRESSION", "predecessor": on_disk_predecessor}
            if capture.get("started_at") < selected.get("started_at"):
                return {"promoted": False, "reason": "GENERATION_REGRESSION", "predecessor": on_disk_predecessor}

        previous = state["rows"]
        if previous is None and state["inconsistent"]:
            if not isinstance(capture.get("source_generation"), str) or not capture.get("source_generation"):
                return {"promoted": False, "reason": "NO_SOURCE_GENERATION", "predecessor": on_disk_predecessor}
            return {"promoted": False, "reason": "METADATA_WRITE_FAILED", "predecessor": on_disk_predecessor}
        if previous is None:
            previous = _empty_history_frame()
        previous = _normalise_legacy(previous)
        if previous.empty and not {"package_ndc", "initial_posting_date"}.issubset(previous.columns):
            previous = _empty_history_frame()
        previous = previous.set_index(["package_ndc", "initial_posting_date"], drop=False)
        generation = capture["source_generation"]
        new_frame = pd.DataFrame(result["rows"])
        if new_frame.empty:
            new_frame = _empty_history_frame()
        new_frame = new_frame.set_index(["package_ndc", "initial_posting_date"], drop=False)
        merged = []
        for key, old in previous.iterrows():
            if key not in new_frame.index:
                row = old.to_dict()
                if row.get("absent_since_generation") is None or pd.isna(row.get("absent_since_generation")):
                    row["absent_since_generation"] = generation
                row["last_observed_generation"] = row.get("last_observed_generation")
                row["capture_known"] = bool(row.get("capture_known"))
                merged.append(row)
        for key, raw_new in new_frame.iterrows():
            new = raw_new.to_dict()
            old = previous.loc[key] if key in previous.index else None
            old = old.iloc[0] if isinstance(old, pd.DataFrame) else old
            if old is not None:
                old = old.to_dict()
                new["first_observed_generation"] = old.get("first_observed_generation") or generation
                if old.get("status") != new.get("status"):
                    new["previous_status"] = old.get("status")
                    new["status_changed_generation"] = generation
                else:
                    new["previous_status"] = old.get("previous_status")
                    new["status_changed_generation"] = old.get("status_changed_generation")
            else:
                new["first_observed_generation"] = generation
            new["last_observed_generation"] = generation
            new["absent_since_generation"] = None
            new["capture_known"] = True
            merged.append(new)

        frame = pd.DataFrame(merged)
        for column in HISTORY_COLUMNS:
            if column not in frame:
                frame[column] = None
        frame = frame.drop_duplicates(subset=["package_ndc", "initial_posting_date"], keep="last")
        generations_seen = list((state["history_coverage"] or {}).get("generations_seen") or [])
        if previous.get("capture_known").any():
            if selected:
                generations_seen.append(selected.get("source_generation"))
        if isinstance(capture["source_generation"], str) and capture["source_generation"]:
            generations_seen.append(capture["source_generation"])
        generations_seen = list(dict.fromkeys(value for value in generations_seen if value is not None))[-120:]
        generation_rank = {value: rank for rank, value in enumerate(generations_seen)}
        absent = frame["absent_since_generation"].map(
            lambda value: generation_rank.get(value, len(generations_seen))
        )
        age = len(generations_seen) - 1 - absent
        keep = absent.isna() | (age < 90)
        dropped = int((~keep).sum())
        frame = frame.loc[keep].reset_index(drop=True)

        def write_parquet(staged):
            frame.to_parquet(staged, engine="pyarrow")

        staged_parquet = path.with_name(f".{path.name}.{os.getpid()}.staged")
        write_parquet(staged_parquet)
        parquet_digest = _digest(staged_parquet)
        if state["legacy"]:
            coverage = {
                "earliest_qualified_generation": generation,
                "legacy_rows_capture_unknown": True,
                "forward_retention_started_at": capture["finished_at"],
            }
        else:
            coverage = dict(state["history_coverage"])
            coverage["earliest_qualified_generation"] = coverage.get("earliest_qualified_generation") or generation
            coverage["forward_retention_started_at"] = coverage.get("forward_retention_started_at") or capture["finished_at"]
            coverage["generations_seen"] = generations_seen
        previous_dropped = int((state.get("retention") or {}).get("dropped_absent_rows") or 0)
        receipt = {
            "schema": SCHEMA,
            "selected_capture": capture,
            "last_refresh": {
                "attempted_at": capture["finished_at"], "qualified": True,
                "failure_code": None, "partial_rows_observed": 0,
            },
            "history_coverage": coverage,
            "retention": {"absent_generations_kept": 90, "dropped_absent_rows": previous_dropped + dropped},
            "predecessor": expected_predecessor,
            "parquet_sha256": parquet_digest,
        }
        previous_parquet = path.read_bytes() if path.exists() else None
        staged_backup = sidecar.with_name(f".{path.name}.{os.getpid()}.backup")
        staged_sidecar = sidecar.with_name(f".{sidecar.name}.{os.getpid()}.tmp")
        try:
            payload = _json_dumps(receipt)
            if previous_parquet is not None:
                staged_backup.write_bytes(previous_parquet)
            staged_sidecar.write_bytes(payload.encode("utf-8"))
        except Exception:
            return {
                "promoted": False, "reason": "METADATA_WRITE_FAILED",
                "predecessor": on_disk_predecessor,
            }

        try:
            _write_staged(
                path,
                lambda staged: staged.write_bytes(staged_parquet.read_bytes()),
            )
            os.replace(staged_sidecar, sidecar)
        except Exception:
            if previous_parquet is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(staged_backup, path)
            return {
                "promoted": False, "reason": "METADATA_WRITE_FAILED",
                "predecessor": on_disk_predecessor,
            }
        finally:
            staged_backup.unlink(missing_ok=True)
            staged_sidecar.unlink(missing_ok=True)
            staged_parquet.unlink(missing_ok=True)
        return {"promoted": True, "reason": None, "predecessor": _digest(sidecar)}

    refresh = {
        "attempted_at": capture.get("finished_at"), "qualified": False,
        "failure_code": result.get("failure_code"),
        "partial_rows_observed": len(result.get("rows") or []),
    }
    try:
        existing = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    except Exception:
        existing = {}
    if existing.get("parquet_sha256") is None and unselected_rows:
        _write_unselected_rows(path, unselected_rows)
        existing = {
            **existing,
            "parquet_sha256": _digest(path),
            "history_coverage": {
                "earliest_qualified_generation": None,
                "legacy_rows_capture_unknown": True,
                "forward_retention_started_at": None,
            },
        }
    receipt = {
        "schema": SCHEMA,
        "selected_capture": existing.get("selected_capture"),
        "last_refresh": refresh,
        "history_coverage": existing.get("history_coverage") or {},
        "retention": existing.get("retention") or {
            "absent_generations_kept": 90, "dropped_absent_rows": 0,
        },
        "predecessor": expected_predecessor,
        "parquet_sha256": existing.get("parquet_sha256"),
    }
    try:
        payload = _json_dumps(receipt)
        _write_staged(sidecar, lambda staged: staged.write_text(payload, encoding="utf-8"))
    except Exception:
        return {
            "promoted": False, "reason": "METADATA_WRITE_FAILED",
            "predecessor": on_disk_predecessor,
        }
    return {"promoted": False, "reason": result.get("failure_code"), "predecessor": _digest(sidecar)}


def read_shortage_observation(*, path) -> dict:
    """Read the selected observation and verify its parquet digest."""
    return _selected_state(path)


def _frame_attrs(frame, state, failed_refresh=False):
    if frame is None:
        return None
    frame.attrs["fda_observation"] = {
        "capture": state.get("capture"),
        "last_refresh": state.get("last_refresh"),
        "legacy": state.get("legacy", False),
        "inconsistent": state.get("inconsistent", False),
        "failed_refresh": failed_refresh,
    }
    return frame


def fetch_shortages(full_refresh: bool = False) -> pd.DataFrame | None:
    """Refresh the feed, keeping the last qualified observation on failure."""
    path = _shortages_path()
    expected_predecessor = _digest(_sidecar_path(path))
    failure_outcome = False

    def fetch_page(skip, limit):
        if skip:
            time.sleep(PACE_S)
        return _fetch_page(skip=skip, limit=limit)

    try:
        result = collect_shortage_sweep(
            fetch_page, clock=lambda: datetime.now(timezone.utc),
            page_size=PAGE_SIZE, max_pages=MAX_PAGES,
        )
        outcome = save_shortage_observation(
            result, path=path, expected_predecessor=expected_predecessor,
        )
        failure_outcome = not outcome.get("promoted", False)
    except Exception as error:
        log.warning("fda_shortages refresh did not publish: %s", error)
        failure_outcome = True
    state = read_shortage_observation(path=path)
    return _frame_attrs(state["rows"], state, failed_refresh=failure_outcome)


def load_shortages_cache() -> pd.DataFrame | None:
    """Read the selected shortage observation without network access."""
    path = _shortages_path()
    state = read_shortage_observation(path=path)
    return _frame_attrs(state["rows"], state)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")
    df = fetch_shortages()
    if df is not None:
        print(f"Fetched {len(df)} records")
        print(df[["generic_name", "status", "availability"]].head(10))
