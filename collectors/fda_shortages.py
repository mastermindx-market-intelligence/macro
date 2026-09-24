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

SHORTAGES_URL = "https://api.fda.gov/drug/shortages.json"
PAGE_SIZE = 100       # openFDA max per request
MAX_PAGES = 25        # cap: 2500 records; avoids runaway loop
PACE_S = 0.4          # polite pacing between pages
SCHEMA = "fda_shortages_observation.v1"
HISTORY_COLUMNS = [
    "first_observed_generation", "last_observed_generation",
    "absent_since_generation", "previous_status", "status_changed_generation",
    "capture_known",
]          # polite pacing between pages


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


def _parse_record(rec: dict) -> dict:
    """Flatten one openFDA shortages record into a flat row."""
    openfda = rec.get("openfda") or {}
    brands = openfda.get("brand_name") or []
    substances = openfda.get("substance_name") or []
    return {
        "package_ndc": rec.get("package_ndc") or "",
        "generic_name": rec.get("generic_name") or "",
        "brand_name": brands[0] if brands else None,
        "substance_name": substances[0] if substances else None,
        "status": rec.get("status") or "",
        "availability": rec.get("availability") or "",
        "initial_posting_date": rec.get("initial_posting_date") or "",
        "update_date": rec.get("update_date") or "",
        "discontinued_date": rec.get("discontinued_date") or None,
        "therapeutic_category": (rec.get("therapeutic_category") or [None])[0],
        "company_name": rec.get("company_name") or None,
        "related_info": rec.get("related_info") or None,
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
    }


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _sidecar_path(path):
    return path.with_suffix(".observation.json")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _empty_history_frame():
    return pd.DataFrame(columns=["package_ndc", "initial_posting_date", *HISTORY_COLUMNS])


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
            parsed = _parse_record(raw_row)
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
        frame = pd.read_parquet(path) if path.exists() else _empty_history_frame()
        return {
            "rows": frame, "capture": None, "last_refresh": None,
            "history_coverage": {
                "earliest_qualified_generation": None,
                "legacy_rows_capture_unknown": True,
                "forward_retention_started_at": None,
            }, "legacy": True, "inconsistent": False,
        }
    receipt = json.loads(sidecar.read_text())
    coverage = receipt.get("history_coverage", {})
    state = {
        "rows": pd.read_parquet(path) if path.exists() else None,
        "capture": receipt.get("selected_capture"),
        "last_refresh": receipt.get("last_refresh"),
        "history_coverage": coverage, "legacy": False,
        "inconsistent": False,
    }
    expected = receipt.get("parquet_sha256")
    if expected is None or not path.exists() or _digest(path) != expected:
        state.update(rows=None, capture=None, inconsistent=True)
    return state


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
    if result.get("qualified"):
        if selected:
            if (capture.get("source_generation") or "") < (selected.get("source_generation") or ""):
                return {"promoted": False, "reason": "GENERATION_REGRESSION", "predecessor": on_disk_predecessor}
            if capture.get("started_at") < selected.get("started_at"):
                return {"promoted": False, "reason": "GENERATION_REGRESSION", "predecessor": on_disk_predecessor}

        previous = state["rows"]
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
        qualified_generations = []
        if previous.get("capture_known").any():
            if selected:
                qualified_generations.append(selected.get("source_generation"))
            previous_absent = previous["absent_since_generation"].dropna().tolist()
            previous_present = previous["last_observed_generation"].dropna().tolist()
            qualified_generations.extend(previous_absent)
            qualified_generations.extend(previous_present)
        if capture["source_generation"] not in qualified_generations:
            qualified_generations.append(capture["source_generation"])
        known = sorted(set(value for value in qualified_generations if value is not None))
        generation_rank = {value: rank for rank, value in enumerate(known)}
        absent = frame["absent_since_generation"].map(lambda value: generation_rank.get(value, 0))
        floor_rank = max(0, len(known) - 1 - 90)
        keep = absent.isna() | (absent >= floor_rank)
        dropped = int((~keep).sum())
        frame = frame.loc[keep].reset_index(drop=True)

        def write_parquet(staged):
            frame.to_parquet(staged, engine="pyarrow")
        _write_staged(path, write_parquet)
        parquet_digest = _digest(path)
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
        receipt = {
            "schema": SCHEMA,
            "selected_capture": capture,
            "last_refresh": {
                "attempted_at": capture["finished_at"], "qualified": True,
                "failure_code": None, "partial_rows_observed": 0,
            },
            "history_coverage": coverage,
            "retention": {"absent_generations_kept": 90, "dropped_absent_rows": dropped},
            "predecessor": expected_predecessor,
            "parquet_sha256": parquet_digest,
        }
        try:
            payload = _json_dumps(receipt)
        except Exception:
            return {
                "promoted": False, "reason": "METADATA_WRITE_FAILED",
                "predecessor": on_disk_predecessor,
            }
        try:
            _write_staged(sidecar, lambda staged: staged.write_text(payload, encoding="utf-8"))
        except Exception:
            return {
                "promoted": False, "reason": "METADATA_WRITE_FAILED",
                "predecessor": on_disk_predecessor,
            }
        return {"promoted": True, "reason": None, "predecessor": _digest(sidecar)}

    refresh = {
        "attempted_at": capture.get("finished_at"), "qualified": False,
        "failure_code": result.get("failure_code"),
        "partial_rows_observed": len(result.get("rows") or []),
    }
    if state["legacy"]:
        coverage = {
            "earliest_qualified_generation": None,
            "legacy_rows_capture_unknown": True,
            "forward_retention_started_at": None,
        }
    else:
        coverage = dict(state["history_coverage"])
    receipt = {
        "schema": SCHEMA,
        "selected_capture": state.get("capture"),
        "last_refresh": refresh,
        "history_coverage": coverage,
        "retention": {
            "absent_generations_kept": 90,
            "dropped_absent_rows": (state.get("history_coverage") or {}).get("retention", {}).get("dropped_absent_rows", 0),
        },
        "predecessor": expected_predecessor,
        "parquet_sha256": _digest(path) if path.exists() else None,
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

    result = collect_shortage_sweep(
        fetch_page, clock=lambda: datetime.now(timezone.utc),
        page_size=PAGE_SIZE, max_pages=MAX_PAGES,
    )
    try:
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
