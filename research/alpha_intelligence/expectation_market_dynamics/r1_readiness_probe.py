#!/usr/bin/env python3
"""Read-only R1 readiness probe.

Measures the Information→Price R1 gaps against git blobs. It does not write
under data/ or site/, does not assign a rights class, and does not complete R1.

Issuer resolution uses the same readers as the #8505 census:
``VendorAliasTable.resolve("store", ticker, cutoff_date)`` and
``IssuerMaster.issuer_of_security``. Those modules are stdlib-only. This file
adds no dependency beyond the stdlib, pyarrow, and pandas already installed.

Definitions that reproduce the census receipt (schema
r1-identity-coverage-census.v1):

* Universe names are the parquet index ``symbol`` of the three constituent
  blobs. The sha256 is of ``json.dumps(sorted_names, separators=(",", ":"))``.
* ``issuer_id`` on the reference spine is how many universe names resolve to a
  non-null issuer id at the cutoff date.
* ``alias_dated`` is how many of those resolved names have at least one
  ``vendor_aliases`` row (any vendor) whose ``valid_from`` is on or before the
  cutoff date. A ``valid_to`` with no ``valid_from`` is not counted as dated.
  ``undated`` is resolved names minus that dated set.
* ``cik_map`` and ``openfigi`` store universe ticker presence in the census
  receipt's ``issuer_id`` field. Neither file has an ``issuer_id`` column.
* ``ticker_sectors`` stores universe ticker presence in the receipt's
  ``undated`` field.
* ``identity_resolution`` counts distinct universe ``source_native_symbol``
  values with a non-null ``issuer_id``.
* Publication-clock and attempt-status counts are full-file counts, matching
  the census receipt. Cohort rows also report the cutoff slice separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import yaml
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.dataos.identity import IssuerMaster, VendorAliasTable  # noqa: E402

SCHEMA_VERSION = "r1-readiness-probe.v2"
EXPECTED_UNIVERSE_SHA256 = (
    "441a942e97950e2fae5c6a015f38535058b0647a540f8ee1ac2342d02bd6ddc5"
)
CUTOFF = "2026-10-03T06:31:51Z"
CUTOFF_DATE = date(2026, 10, 3)
CUTOFF_TS = pd.Timestamp(CUTOFF)

OWNER_RECEIPTS_PATH = (
    "research/alpha_intelligence/expectation_market_dynamics/"
    "R1_OWNER_RECEIPTS_2026-10-07.json"
)
OWNER_RECEIPTS_SCHEMA = "r1-owner-receipts.v1"
OWNER_WS_KEY_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]*$")
RIGHTS_LITERAL_RE = re.compile(r'"rights_class"\s*:\s*"([^"]*)"')
EXPECTED_RECEIPT_FORM = {
    "G1": "DEGRADED_LABELED_ABSENCE",
    "G2": "DEGRADED_LABELED_ABSENCE",
    "G3": "DEGRADED_LABELED_ABSENCE",
    "G4": "OWNER_REFUSAL_NO_CLASS",
    "G5": "CAPTURE_CLOCK_ONLY",
}
REQUIRED_OWNER_PATHS = {
    "G1": (
        "data/reference/",
        "data/reference/security_master.parquet",
        "data/reference/vendor_aliases.parquet",
        "data/reference/issuer_master.parquet",
        "data/symbol_directory/",
        "data/openfigi/",
    ),
    "G2": (
        "data/reference/vendor_aliases.parquet",
        "data/reference/issuer_migrations.parquet",
        "data/reference/security_migrations.parquet",
    ),
    "G3": (
        "data/reference/security_master.parquet",
        "data/reference/issuer_master.parquet",
        "data/revisions/expectation_observations.parquet",
    ),
    "G4": ("collectors/equity_revisions.py",),
    "G5": (
        "data/revisions/expectation_observations.parquet",
        "data/revisions/expectation_attempts.parquet",
        "collectors/equity_revisions.py",
    ),
}
STABLE_COUNT_KEYS = {
    "G1": ("issuer_id_resolved", "universe_names", "unresolved"),
    "G2": (
        "alias_rows_dated_le_cutoff",
        "undated_alias_rows",
        "prospective_from_undated_rows",
    ),
    "G3": (
        "spine_columns_present",
        "observation_currency_nonnull",
        "observation_fiscal_year_nonnull",
        "observation_basis_nonnull",
    ),
    "G4": ("literal", "line"),
    "G5": ("source_effective_at_nonnull", "source_published_at_nonnull"),
}

CONSTITUENTS = (
    "data/breadth/constituents.parquet",
    "data/midcap_breadth/constituents.parquet",
    "data/smallcap_breadth/constituents.parquet",
)
SPINE_PATHS = (
    "data/reference/security_master.parquet",
    "data/reference/vendor_aliases.parquet",
    "data/reference/issuer_master.parquet",
    "data/reference/issuer_migrations.parquet",
    "data/reference/security_migrations.parquet",
)
OTHER_PATHS = (
    "data/symbol_directory/cik_map/2026-09-28.parquet",
    "data/openfigi/cusip_ticker.parquet",
    "data/breadth/ticker_sectors.parquet",
    "data/theme_graph/identity_resolution.parquet",
    "data/ffiec_y9c/bhc_ticker_map.csv",
    "data/revisions/expectation_observations.parquet",
    "data/revisions/expectation_attempts.parquet",
    "collectors/equity_revisions.py",
)
GRAIN = (
    "provider",
    "provider_record_class",
    "ticker_compat",
    "metric",
    "horizon_label_raw",
    "observation_type",
)
FAILURE_STATUSES = (
    "partial",
    "null",
    "http_401",
    "http_403",
    "http_429",
    "malformed",
    "error",
)
COVERAGE_KEYS = (
    "issuer_id",
    "alias_dated",
    "currency",
    "fye",
    "basis",
    "undated",
)


class ProbeError(Exception):
    def __init__(self, command: str, detail: str) -> None:
        self.command = command
        self.detail = detail
        super().__init__(f"{command}: {detail}")


def _git(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    command = "git " + " ".join(args)
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise ProbeError(command, detail or f"exit {exc.returncode}") from exc


def git_text(args: list[str]) -> str:
    return _git(args).stdout.decode("utf-8").strip()


def git_bytes(rev: str, path: str) -> bytes:
    return _git(["show", f"{rev}:{path}"]).stdout


def blob_sha(rev: str, path: str) -> str:
    return git_text(["rev-parse", f"{rev}:{path}"])


def as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        if value != value:  # NaN
            return None
    except TypeError:
        pass
    text = str(value)
    if text in {"NaT", "nan", "None", "", "<NA>"}:
        return None
    return date.fromisoformat(text[:10])


def norm_scalar(value: object) -> str | None:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except TypeError:
        pass
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    text = str(value)
    if text in {"None", "nan", "NaT", "<NA>", ""}:
        return None
    return text


def read_frame(rev: str, path: str) -> tuple[pd.DataFrame, str, int]:
    raw = git_bytes(rev, path)
    sha = blob_sha(rev, path)
    suffix = Path(path).suffix or ".blob"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(raw)
        temporary = Path(handle.name)
    try:
        if suffix == ".csv":
            frame = pd.read_csv(temporary)
        else:
            frame = pd.read_parquet(temporary)
    finally:
        temporary.unlink(missing_ok=True)
    return frame, sha, int(len(frame))


def universe_names(frames: dict[str, pd.DataFrame]) -> list[str]:
    names: set[str] = set()
    for path in CONSTITUENTS:
        frame = frames[path]
        if frame.index.name != "symbol":
            raise ProbeError(
                f"universe index of {path}",
                f"expected index name 'symbol', got {frame.index.name!r}",
            )
        names.update(frame.index.astype(str))
    return sorted(names)


def names_sha256(names: list[str]) -> str:
    payload = json.dumps(names, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def alias_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in frame.to_dict("records"):
        records.append(
            {
                "vendor": row["vendor"],
                "vendor_symbol": row["vendor_symbol"],
                "security_id": row["security_id"],
                "valid_from": as_date(row["valid_from"]),
                "valid_to": as_date(row["valid_to"]),
            }
        )
    return records


def resolve_issuers(
    names: list[str],
    records: list[dict[str, object]],
    security_master: pd.DataFrame,
) -> tuple[set[str], set[str], list[str]]:
    table = VendorAliasTable.from_records(records)
    master = IssuerMaster.from_records(security_master.to_dict("records"))
    resolved: set[str] = set()
    for symbol in names:
        security_id = table.resolve("store", symbol, CUTOFF_DATE)
        if security_id and master.issuer_of_security(security_id):
            resolved.add(symbol)
    dated: set[str] = set()
    valid_to_only: set[str] = set()
    universe = set(names)
    for record in records:
        symbol = str(record["vendor_symbol"])
        if symbol not in universe:
            continue
        valid_from = record["valid_from"]
        valid_to = record["valid_to"]
        if isinstance(valid_from, date) and valid_from <= CUTOFF_DATE:
            dated.add(symbol)
        elif valid_from is None and isinstance(valid_to, date):
            valid_to_only.add(symbol)
    dated_resolved = dated & resolved
    return resolved, dated_resolved, sorted(valid_to_only)


def zero_coverage(**overrides: int) -> dict[str, int]:
    row = {key: 0 for key in COVERAGE_KEYS}
    row.update(overrides)
    return row


def spine_coverage(resolved: int, dated: int, undated: int) -> dict[str, int]:
    return zero_coverage(issuer_id=resolved, alias_dated=dated, undated=undated)


def distinct_in_universe(series: pd.Series, names: set[str]) -> int:
    tickers = series.dropna().astype(str)
    return int(tickers[tickers.isin(names)].nunique())


def nonnull_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].notna().sum())


def migration_tickers(frame: pd.DataFrame, names: set[str]) -> int:
    found: set[str] = set()
    for listing_key, migrated_at in zip(frame["listing_key"], frame["migrated_at"]):
        when = as_date(migrated_at)
        if when is None or when > CUTOFF_DATE:
            continue
        ticker = str(listing_key).split("-")[-1]
        if ticker in names:
            found.add(ticker)
    return len(found)


def column_absent(frames: dict[str, pd.DataFrame], names: tuple[str, ...]) -> list[str]:
    present: list[str] = []
    for path, frame in frames.items():
        for name in names:
            if name in frame.columns:
                present.append(f"{path}:{name}")
    return present


def rights_and_provider(source: str) -> dict[str, object]:
    rights: list[dict[str, object]] = []
    provider: list[dict[str, object]] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if "rights_class" in line and "UNKNOWN" in line:
            rights.append({"line": number, "text": line.strip()})
        if "_EXPECTATION_PROVIDER" in line and "yfinance" in line:
            provider.append({"line": number, "text": line.strip()})
    return {"rights": rights, "provider": provider}


def _status_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["status"].value_counts(dropna=False).to_dict()
    cleaned: dict[str, int] = {}
    for key, value in counts.items():
        label = "null" if pd.isna(key) else str(key)
        cleaned[label] = int(value)
    return cleaned


def _after_good(frame: pd.DataFrame) -> dict[str, int]:
    ordered = frame.sort_values(
        ["ticker_compat", "attempted_at_ts", "attempt_id"],
        kind="mergesort",
    )
    seen_good: set[str] = set()
    counts = {status: 0 for status in FAILURE_STATUSES}
    counts["other_non_success"] = 0
    for ticker, status, observation_count in zip(
        ordered["ticker_compat"],
        ordered["status"],
        ordered["observation_count"],
    ):
        label = "null" if pd.isna(status) else str(status)
        if label in counts and ticker in seen_good:
            counts[label] += 1
        elif label != "success" and label not in counts and ticker in seen_good:
            counts["other_non_success"] += 1
        good = (
            label == "success"
            and pd.notna(observation_count)
            and int(observation_count) > 0
        )
        if good:
            seen_good.add(str(ticker))
    return counts


def attempt_cohorts(attempts: pd.DataFrame) -> dict[str, object]:
    frame = attempts.copy()
    frame["attempted_at_ts"] = pd.to_datetime(
        frame["attempted_at"], utc=True, errors="coerce"
    )
    full = frame
    bounded = frame[frame["attempted_at_ts"] <= CUTOFF_TS]
    return {
        "logic": (
            "Attempt-status sequence only: a later attempt for the same "
            "ticker_compat whose status is partial, null, http_401, http_403, "
            "http_429, malformed, or error, after an earlier attempt with status "
            "success and observation_count > 0. Sort is ticker_compat, "
            "attempted_at, attempt_id. This is not the owner's partial-after-good "
            "witness. A ticker can be partial on every attempt and still keep an "
            "earlier good observation value. That witness is "
            "observations.missing_after_earlier_good_value."
        ),
        "full_file": {
            "rows": int(len(full)),
            "status": _status_counts(full),
            "observation_count_sum": int(full["observation_count"].fillna(0).sum()),
            "after_good": _after_good(full),
        },
        "effective_le_cutoff": {
            "rows": int(len(bounded)),
            "status": _status_counts(bounded),
            "observation_count_sum": int(bounded["observation_count"].fillna(0).sum()),
            "after_good": _after_good(bounded),
        },
        "preservation_of_prior_good_bytes": {
            "status": "UNMEASURABLE",
            "reason": (
                "One current attempts file has no parent snapshot, so it cannot "
                "show whether a later partial, null, or failure left the prior "
                "good observation bytes unchanged."
            ),
        },
    }


def observation_cohorts(observations: pd.DataFrame) -> dict[str, object]:
    frame = observations.copy()
    frame["observed_ts"] = pd.to_datetime(
        frame["system_observed_at"], utc=True, errors="coerce"
    )
    frame["period_norm"] = frame["period_end"].map(norm_scalar)
    frame["value_norm"] = frame["value"].map(norm_scalar)
    frame["unit_norm"] = frame["unit"].map(norm_scalar)
    frame["currency_norm"] = frame["currency"].map(norm_scalar)
    frame["basis_norm"] = frame["basis"].map(norm_scalar)

    supersedes = frame.loc[
        frame["correction_state"] == "supersedes",
        [
            "supersedes_observation_id",
            "period_norm",
            "value_norm",
            "unit_norm",
            "currency_norm",
            "basis_norm",
            "observed_ts",
        ],
    ].copy()
    supersedes["prior_id"] = supersedes["supersedes_observation_id"].map(norm_scalar)
    prior_cols = (
        frame[
            [
                "observation_id",
                "period_norm",
                "value_norm",
                "unit_norm",
                "currency_norm",
                "basis_norm",
            ]
        ]
        .drop_duplicates("observation_id")
        .rename(
            columns={
                "observation_id": "prior_observation_id",
                "period_norm": "prior_period",
                "value_norm": "prior_value",
                "unit_norm": "prior_unit",
                "currency_norm": "prior_currency",
                "basis_norm": "prior_basis",
            }
        )
    )
    merged = supersedes.merge(
        prior_cols, left_on="prior_id", right_on="prior_observation_id", how="left"
    )
    prior_missing = int(merged["prior_observation_id"].isna().sum())
    found = merged[merged["prior_observation_id"].notna()].copy()

    def _eq(left: pd.Series, right: pd.Series) -> pd.Series:
        return left.fillna("\0") == right.fillna("\0")

    same_period = (
        found["period_norm"].notna()
        & found["prior_period"].notna()
        & _eq(found["period_norm"], found["prior_period"])
    )
    value_differs = ~_eq(found["value_norm"], found["prior_value"])
    meta_differs = (
        ~_eq(found["unit_norm"], found["prior_unit"])
        | ~_eq(found["currency_norm"], found["prior_currency"])
        | ~_eq(found["basis_norm"], found["prior_basis"])
    )
    same_anchor_mask = same_period & value_differs
    same_anchor = int(same_anchor_mask.sum())
    same_anchor_bounded = int(
        (same_anchor_mask & (found["observed_ts"] <= CUTOFF_TS)).sum()
    )
    metadata_only = int((same_period & ~value_differs & meta_differs).sum())
    null_anchor = int((~same_period).sum())

    good_rows = frame[frame["value_norm"].notna()].sort_values(
        ["observed_ts", "observation_id"], kind="mergesort"
    )
    good_rows = good_rows.assign(
        previous_good_period=good_rows.groupby(list(GRAIN), dropna=False, sort=False)[
            "period_norm"
        ].shift(1)
    )
    rollover = good_rows[
        good_rows["previous_good_period"].notna()
        & good_rows["period_norm"].notna()
        & (good_rows["previous_good_period"] != good_rows["period_norm"])
    ]
    rollover_state = {
        str(key): int(value)
        for key, value in rollover["correction_state"].value_counts(dropna=False).items()
    }

    def label_counts(sub: pd.DataFrame) -> dict[str, int]:
        return {
            str(key): int(value)
            for key, value in sub["correction_state"].value_counts(dropna=False).items()
        }

    bounded = frame[frame["observed_ts"] <= CUTOFF_TS]
    ordered_good = frame.sort_values(
        ["observed_ts", "observation_id"], kind="mergesort"
    ).copy()
    ordered_good["is_good_value"] = ordered_good["value_norm"].notna().astype(int)
    good_group = ordered_good.groupby(list(GRAIN), dropna=False, sort=False)
    ordered_good["prior_good_values"] = (
        good_group["is_good_value"].cumsum() - ordered_good["is_good_value"]
    )
    missing_after = ordered_good[
        (ordered_good["correction_state"] == "missing")
        & (ordered_good["prior_good_values"] > 0)
    ]
    missing_after_bounded = missing_after[missing_after["observed_ts"] <= CUTOFF_TS]

    currency_nonnull = int(frame["currency"].notna().sum()) if "currency" in frame else 0
    basis_nonnull = int(frame["basis"].notna().sum()) if "basis" in frame else 0
    fiscal_year_nonnull = (
        int(frame["fiscal_year"].notna().sum()) if "fiscal_year" in frame else 0
    )
    fiscal_period_nonnull = (
        int(frame["fiscal_period"].notna().sum()) if "fiscal_period" in frame else 0
    )
    return {
        "unchanged": {
            "measurable": True,
            "logic": (
                "correction_state == 'unchanged'. The collector writes that label "
                "only when a prior good row exists on the same grain, the period "
                "ends are not a pair of different real anchors, and value, unit, "
                "currency, and basis match."
            ),
            "rows_full_file": int((frame["correction_state"] == "unchanged").sum()),
            "rows_effective_le_cutoff": int(
                (bounded["correction_state"] == "unchanged").sum()
            ),
        },
        "same_anchor_changed_value": {
            "measurable": True,
            "logic": (
                "correction_state == 'supersedes', supersedes_observation_id joins "
                "to a row in this file, both period_end values are non-null and "
                "equal, and value differs. A supersession whose anchor is null, "
                "or whose anchors differ, is counted separately and is not this "
                "cohort."
            ),
            "rows_full_file": same_anchor,
            "rows_effective_le_cutoff": same_anchor_bounded,
            "supersedes_rows": int(len(supersedes)),
            "supersedes_null_or_different_anchor": null_anchor,
            "supersedes_prior_missing": prior_missing,
            "supersedes_metadata_only_same_anchor": metadata_only,
        },
        "missing_after_earlier_good_value": {
            "measurable": True,
            "logic": (
                "On one grain, ordered by system_observed_at then observation_id, "
                "a row with correction_state 'missing' whose same grain has at "
                "least one earlier row with a non-null value. The earlier row is "
                "still in this file. This is the observation-grain form of "
                "partial/null after a good value. It does not prove that a good "
                "row absent from this file was never deleted."
            ),
            "rows_full_file": int(len(missing_after)),
            "rows_effective_le_cutoff": int(len(missing_after_bounded)),
        },
        "fiscal_rollover_not_a_revision": {
            "measurable": True,
            "logic": (
                "Keep rows with a non-null value. On one grain (provider, "
                "provider_record_class, ticker_compat, metric, horizon_label_raw, "
                "observation_type), ordered by system_observed_at then "
                "observation_id, compare each row with the previous non-null-value "
                "row. Both period_end values are non-null and differ. That is the "
                "collector's newest-prior-good-row anchor test. The owner's cohort "
                "is the later row whose correction_state is original, not "
                "supersedes. fiscal_year and fiscal_period are entirely null, so a "
                "fiscal-label rollover cannot be measured. This count is the "
                "period_end comparison only."
            ),
            "rows_full_file": int(len(rollover)),
            "rows_effective_le_cutoff": int(
                (rollover["observed_ts"] <= CUTOFF_TS).sum()
            ),
            "later_correction_state": rollover_state,
            "rows_later_state_original": int(rollover_state.get("original", 0)),
            "rows_later_state_supersedes": int(rollover_state.get("supersedes", 0)),
        },
        "correction_state_full_file": label_counts(frame),
        "correction_state_effective_le_cutoff": label_counts(bounded),
        "currency_or_basis_change": {
            "status": "UNMEASURABLE",
            "reason": (
                "currency non-null rows are "
                f"{currency_nonnull}, basis non-null rows are {basis_nonnull}, "
                f"fiscal_year non-null rows are {fiscal_year_nonnull}, and "
                f"fiscal_period non-null rows are {fiscal_period_nonnull}. "
                "A change in those fields cannot be observed. Zero is not a "
                "measurement of no change."
            ),
        },
        "event_time_order": {
            "status": "UNMEASURABLE",
            "reason": (
                "source_effective_at and source_published_at are entirely null. "
                "provider_observed_at and system_observed_at are capture clocks. "
                "Event-time order is excluded. Capture-time cohorts above use "
                "system_observed_at."
            ),
        },
    }


def gate_status(passed: bool, measurable: bool = True) -> str:
    if not measurable:
        return "UNMEASURABLE"
    return "CLOSED" if passed else "OPEN"


def owns_path(owns_paths, required: str) -> bool:
    if owns_paths is None:
        return False
    for entry in owns_paths:
        if entry == required:
            return True
        if entry.endswith("/") and required.startswith(entry):
            return True
    return False


def parse_front_matter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    end = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            end = index
            break
    if end is None:
        return {}
    body = "\n".join(lines[1:end])
    try:
        loaded = yaml.safe_load(body)
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def rights_literal_of(text: str) -> str | None:
    code = text.split("#", 1)[0]
    match = RIGHTS_LITERAL_RE.search(code)
    return match.group(1) if match else None


def evaluate_owner_receipt(
    gap_key: str,
    gap: dict[str, object],
    receipt_gap: dict[str, object] | None,
    ws_front_matter: dict[str, object] | None,
    rights_hits: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    raw = str(gap["status"])
    if receipt_gap is None or not isinstance(receipt_gap, dict):
        block = {
            "present": False,
            "owner_ws": None,
            "form_ok": False,
            "cutoff_ok": False,
            "ws_active": False,
            "uncovered_paths": [],
            "counts_match": False,
            "mismatches": ["owner receipt missing"],
        }
        if raw == "CLOSED":
            final = "CLOSED"
        elif raw == "UNMEASURABLE":
            final = "UNMEASURABLE"
        else:
            final = "OPEN"
        return {"status": final, "owner_receipt": block}

    mismatches: list[str] = []
    owner_ws = receipt_gap.get("owner_ws")
    owner_ws_valid = isinstance(owner_ws, str) and bool(OWNER_WS_KEY_RE.match(owner_ws))
    if not owner_ws_valid:
        mismatches.append("owner_ws invalid")

    expected_form = EXPECTED_RECEIPT_FORM[gap_key]
    got_form = receipt_gap.get("receipt_form")
    form_ok = got_form == expected_form
    if not form_ok:
        mismatches.append(f"receipt_form {got_form} != {expected_form}")

    cutoff_ok = receipt_gap.get("cutoff") == CUTOFF
    if not cutoff_ok:
        mismatches.append(f"cutoff {receipt_gap.get('cutoff')} != {CUTOFF}")

    ws_active = isinstance(ws_front_matter, dict) and ws_front_matter.get("status") == "active"
    if not ws_active:
        mismatches.append("workstream not active or missing")

    owns_paths_list = (
        ws_front_matter.get("owns_paths")
        if isinstance(ws_front_matter, dict)
        else None
    )
    uncovered_paths = [
        path
        for path in REQUIRED_OWNER_PATHS[gap_key]
        if not owns_path(owns_paths_list, path)
    ]
    for path in uncovered_paths:
        mismatches.append(f"uncovered {path}")

    counts_match = True
    for key in STABLE_COUNT_KEYS[gap_key]:
        receipt_val = receipt_gap.get("counts", {}).get(key)
        probe_val = gap["value"].get(key)  # type: ignore[union-attr]
        if isinstance(receipt_val, list) or isinstance(probe_val, list):
            receipt_cmp = sorted(receipt_val or [])
            probe_cmp = sorted(probe_val or [])
            if receipt_cmp != probe_cmp:
                counts_match = False
                mismatches.append(f"count {key}: receipt {receipt_val} probe {probe_val}")
        elif receipt_val != probe_val:
            counts_match = False
            mismatches.append(f"count {key}: receipt {receipt_val} probe {probe_val}")

    if gap_key == "G4":
        hits = rights_hits or []
        refusal = receipt_gap.get("refusal") or {}
        if len(hits) != 1:
            mismatches.append("g4 refusal not on the literal's line")
        elif hits[0]["line"] != refusal.get("line"):
            mismatches.append("g4 refusal line mismatch")
        else:
            marker = refusal.get("same_line_marker")
            if not isinstance(marker, str) or not marker or marker not in str(hits[0]["text"]):
                mismatches.append("g4 refusal not on the literal's line")

    block = {
        "present": True,
        "owner_ws": owner_ws if isinstance(owner_ws, str) else None,
        "form_ok": form_ok,
        "cutoff_ok": cutoff_ok,
        "ws_active": ws_active,
        "uncovered_paths": uncovered_paths,
        "counts_match": counts_match,
        "mismatches": mismatches,
    }

    if raw == "CLOSED":
        final = "CLOSED"
    elif raw == "UNMEASURABLE":
        final = "UNMEASURABLE"
    elif raw == "OPEN":
        final = "DEGRADED_ACCEPTED" if not mismatches else "OPEN"
    else:
        final = raw

    return {"status": final, "owner_receipt": block}


def compute_r1_status(
    gap_statuses: dict[str, str], headlines: list[str]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    for key, status in gap_statuses.items():
        if status not in {"CLOSED", "DEGRADED_ACCEPTED"}:
            reasons.append(f"{key} {status}")
    for headline in headlines:
        reasons.append(f"headline: {headline}")
    if reasons:
        return ("INCOMPLETE", reasons)
    if all(status == "CLOSED" for status in gap_statuses.values()):
        return ("COMPLETE", [])
    return ("COMPLETE_DEGRADED", [])


def build_receipt(rev: str) -> tuple[dict[str, object], list[str]]:
    commands = [f"git rev-parse {rev}"]
    source_revision = git_text(["rev-parse", rev])
    frames: dict[str, pd.DataFrame] = {}
    sources: list[dict[str, object]] = []
    for path in (*CONSTITUENTS, *SPINE_PATHS, *OTHER_PATHS):
        show = f"git show {rev}:{path}"
        commands.append(show)
        commands.append(f"git rev-parse {rev}:{path}")
        if path.endswith(".py"):
            text = git_bytes(rev, path).decode("utf-8")
            sha = blob_sha(rev, path)
            sources.append({"path": path, "blob": sha, "rows": None})
            frames[path] = text  # type: ignore[assignment]
            continue
        frame, sha, rows = read_frame(rev, path)
        frames[path] = frame
        sources.append({"path": path, "blob": sha, "rows": rows})

    names = universe_names(frames)
    digest = names_sha256(names)
    matched = digest == EXPECTED_UNIVERSE_SHA256
    name_set = set(names)
    records = alias_records(frames["data/reference/vendor_aliases.parquet"])
    resolved, dated, valid_to_only = resolve_issuers(
        names,
        records,
        frames["data/reference/security_master.parquet"],
    )
    resolved_n = len(resolved)
    dated_n = len(dated)
    undated_n = resolved_n - dated_n
    spine = spine_coverage(resolved_n, dated_n, undated_n)

    cik = frames["data/symbol_directory/cik_map/2026-09-28.parquet"]
    figi = frames["data/openfigi/cusip_ticker.parquet"]
    sectors = frames["data/breadth/ticker_sectors.parquet"]
    identity = frames["data/theme_graph/identity_resolution.parquet"]
    observations = frames["data/revisions/expectation_observations.parquet"]
    attempts = frames["data/revisions/expectation_attempts.parquet"]
    migrations = frames["data/reference/issuer_migrations.parquet"]

    cik_tickers = distinct_in_universe(cik["ticker"], name_set)
    figi_tickers = distinct_in_universe(figi["ticker"], name_set)
    sector_tickers = distinct_in_universe(sectors["ticker"], name_set)
    identity_hit = identity[
        identity["source_native_symbol"].astype(str).isin(name_set)
        & identity["issuer_id"].notna()
    ]
    identity_n = int(identity_hit["source_native_symbol"].astype(str).nunique())
    cik_has_issuer = "issuer_id" in cik.columns

    coverage = {
        "data/reference/security_master.parquet": spine,
        "data/reference/vendor_aliases.parquet": spine,
        "data/reference/issuer_migrations.parquet+security_migrations.parquet": spine_coverage(
            resolved_n,
            migration_tickers(migrations, name_set),
            undated_n,
        ),
        "data/symbol_directory/cik_map/2026-09-28.parquet": zero_coverage(
            issuer_id=cik_tickers
        ),
        "data/openfigi/cusip_ticker.parquet": zero_coverage(issuer_id=figi_tickers),
        "data/breadth/ticker_sectors.parquet": zero_coverage(undated=sector_tickers),
        "data/theme_graph/identity_resolution.parquet": zero_coverage(
            issuer_id=identity_n
        ),
        "data/revisions/expectation_observations.parquet": zero_coverage(
            issuer_id=nonnull_count(observations, "issuer_ref"),
            currency=nonnull_count(observations, "currency"),
            fye=nonnull_count(observations, "fiscal_year"),
            basis=nonnull_count(observations, "basis"),
        ),
    }

    clock_fields = {
        "source_effective_at_nonnull": nonnull_count(observations, "source_effective_at"),
        "source_published_at_nonnull": nonnull_count(observations, "source_published_at"),
        "provider_observed_at_nonnull": nonnull_count(observations, "provider_observed_at"),
        "system_observed_at_nonnull": nonnull_count(observations, "system_observed_at"),
        "attempted_at_nonnull": nonnull_count(attempts, "attempted_at"),
        "completed_at_nonnull": nonnull_count(attempts, "completed_at"),
    }
    literals = rights_and_provider(frames["collectors/equity_revisions.py"])
    rights_hits = literals["rights"]
    rights_literal = None
    rights_line = None
    if rights_hits:
        rights_line = int(rights_hits[0]["line"])
        rights_literal = rights_literal_of(str(rights_hits[0]["text"]))
        if rights_literal is None:
            rights_literal = (
                "UNKNOWN"
                if "UNKNOWN" in str(rights_hits[0]["text"])
                else str(rights_hits[0]["text"])
            )
    spine_field_names = (
        "currency",
        "fiscal_year_end",
        "fye",
        "fiscal_year",
        "accounting_basis",
        "basis",
    )
    spine_frames = {
        path: frames[path]
        for path in (
            "data/reference/security_master.parquet",
            "data/reference/issuer_master.parquet",
            "data/reference/vendor_aliases.parquet",
        )
    }
    present_fields = column_absent(spine_frames, spine_field_names)

    attempt_part = attempt_cohorts(attempts)
    observation_part = observation_cohorts(observations)
    full_status = attempt_part["full_file"]["status"]  # type: ignore[index]

    gaps = {
        "G1": {
            "metric": "issuer_id_resolved",
            "value": {
                "issuer_id_resolved": resolved_n,
                "universe_names": len(names),
                "unresolved": len(names) - resolved_n,
                "cik_map_universe_tickers": cik_tickers,
                "cik_map_has_issuer_id_column": cik_has_issuer,
                "cik_map_file_rows": int(len(cik)),
                "openfigi_universe_tickers": figi_tickers,
                "openfigi_file_rows": int(len(figi)),
                "identity_resolution_universe_symbols": identity_n,
            },
            "gate": "issuer_id_resolved == universe.names",
            "status": gate_status(resolved_n == len(names)),
        },
        "G2": {
            "metric": "alias_rows_dated_le_cutoff",
            "value": {
                "alias_rows_dated_le_cutoff": dated_n,
                "undated_alias_rows": undated_n,
                "prospective_from_undated_rows": 0,
                "dated_symbols": sorted(dated),
                "valid_to_without_valid_from_universe_names": valid_to_only,
            },
            "gate": (
                "undated_alias_rows == 0 and "
                "alias_rows_dated_le_cutoff == universe.names"
            ),
            "status": gate_status(undated_n == 0 and dated_n == len(names)),
        },
        "G3": {
            "metric": "currency_fye_basis_nonnull",
            "value": {
                "spine_columns_present": present_fields,
                "observation_currency_nonnull": nonnull_count(observations, "currency"),
                "observation_fiscal_year_nonnull": nonnull_count(
                    observations, "fiscal_year"
                ),
                "observation_basis_nonnull": nonnull_count(observations, "basis"),
            },
            "gate": (
                "security_master exposes currency, fiscal_year_end, and "
                "accounting_basis, each non-null for every issuer-resolved name"
            ),
            "status": gate_status(
                any(item.endswith(":currency") for item in present_fields)
                and any(
                    item.endswith(":fiscal_year_end") or item.endswith(":fye")
                    for item in present_fields
                )
                and any(
                    item.endswith(":accounting_basis") or item.endswith(":basis")
                    for item in present_fields
                )
                and nonnull_count(observations, "currency") >= resolved_n
                and nonnull_count(observations, "basis") >= resolved_n
            ),
        },
        "G4": {
            "metric": "rights_class_literal",
            "value": {
                "literal": rights_literal,
                "line": rights_line,
                "hits": rights_hits,
                "provider": literals["provider"],
            },
            "gate": (
                "collectors/equity_revisions.py rights_class literal is an "
                "owner-assigned class other than UNKNOWN, or the same line records "
                "an owner refusal"
            ),
            "status": gate_status(rights_literal not in {None, "UNKNOWN"}, rights_literal is not None),
        },
        "G5": {
            "metric": "source_publication_clock_nonnull",
            "value": {
                "source_effective_at_nonnull": clock_fields["source_effective_at_nonnull"],
                "source_published_at_nonnull": clock_fields["source_published_at_nonnull"],
                "observation_rows": int(len(observations)),
                "provider_observed_at_nonnull": clock_fields["provider_observed_at_nonnull"],
                "system_observed_at_nonnull": clock_fields["system_observed_at_nonnull"],
            },
            "gate": "source_effective_at_nonnull > 0 and source_published_at_nonnull > 0",
            "status": gate_status(
                clock_fields["source_effective_at_nonnull"] > 0
                and clock_fields["source_published_at_nonnull"] > 0
            ),
        },
    }

    receipts: dict[str, object] | None = None
    receipts_present = False
    receipts_schema: str | None = None
    receipts_blob: str | None = None
    show_receipts = f"git show {rev}:{OWNER_RECEIPTS_PATH}"
    commands.append(show_receipts)
    try:
        receipts_raw = git_bytes(rev, OWNER_RECEIPTS_PATH)
        receipts = json.loads(receipts_raw.decode("utf-8"))
        receipts_present = True
        receipts_schema = str(receipts.get("schema_version"))
        receipts_blob = blob_sha(rev, OWNER_RECEIPTS_PATH)
    except (ProbeError, ValueError, json.JSONDecodeError):
        receipts = None

    gap_statuses: dict[str, str] = {}
    for key, gap in gaps.items():
        receipt_gap = None
        ws_front_matter: dict[str, object] | None = None
        if (
            receipts is not None
            and receipts.get("schema_version") == OWNER_RECEIPTS_SCHEMA
        ):
            receipt_gap = receipts.get("gaps", {}).get(key)
            owner_ws = (
                receipt_gap.get("owner_ws")
                if isinstance(receipt_gap, dict)
                else None
            )
            if isinstance(owner_ws, str) and OWNER_WS_KEY_RE.match(owner_ws):
                ws_path = f"agentos/workstreams/WS-{owner_ws}.md"
                commands.append(f"git show {rev}:{ws_path}")
                try:
                    ws_text = git_bytes(rev, ws_path).decode("utf-8")
                    ws_front_matter = parse_front_matter(ws_text)
                except ProbeError:
                    ws_front_matter = None
        evaluated = evaluate_owner_receipt(
            key,
            gap,
            receipt_gap if isinstance(receipt_gap, dict) else None,
            ws_front_matter,
            rights_hits if key == "G4" else None,
        )
        gap["gate_status"] = gap["status"]
        gap["status"] = evaluated["status"]
        gap["owner_receipt"] = evaluated["owner_receipt"]
        gap_statuses[key] = str(evaluated["status"])

    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_revision": source_revision,
        "cutoff": CUTOFF,
        "universe": {
            "names": len(names),
            "sha256": digest,
            "matched": matched,
        },
        "sources": sources,
        "coverage": coverage,
        "publication_clock": {
            "expectation_attempts": [
                "attempt_id",
                "collection_session_id",
                "provider",
                "ticker_compat",
                "attempted_at",
                "completed_at",
                "status",
                "http_status",
                "latency_ms",
                "response_payload_hash",
                "safe_error_class",
                "safe_error_detail",
                "observation_count",
            ],
            "expectation_observations_clock_fields": clock_fields,
        },
        "gaps": gaps,
        "owner_receipts": {
            "path": OWNER_RECEIPTS_PATH,
            "present": receipts_present,
            "schema_version": receipts_schema,
            "blob": receipts_blob,
        },
        "cohorts": {
            "vocabulary": {
                "unchanged": "natural unchanged witness",
                "changed": "same-anchor changed-value",
                "partial_null_failure": "partial-null-failure after good",
                "rollover": "fiscal rollover is not a revision",
            },
            "attempts": attempt_part,
            "observations": observation_part,
            "attempt_status_full_file": full_status,
        },
        "commands": commands,
    }
    headlines: list[str] = []
    if not matched:
        headlines.append(
            "HEADLINE: universe sha256 mismatch: "
            f"got {digest} expected {EXPECTED_UNIVERSE_SHA256} "
            f"(names={len(names)})"
        )
    r1_status, r1_status_reasons = compute_r1_status(gap_statuses, headlines)
    receipt["r1_status"] = r1_status
    receipt["r1_status_reasons"] = r1_status_reasons
    return receipt, headlines


def shared_mismatches(probe: dict[str, object], census: dict[str, object]) -> list[str]:
    diffs: list[str] = []
    probe_universe = probe["universe"]
    census_universe = census["universe"]
    if probe_universe["names"] != census_universe["names"]:  # type: ignore[index]
        diffs.append(
            "universe.names: "
            f"probe {probe_universe['names']} census {census_universe['names']}"  # type: ignore[index]
        )
    if probe_universe["sha256"] != census_universe["sha256"]:  # type: ignore[index]
        diffs.append(
            "universe.sha256: "
            f"probe {probe_universe['sha256']} census {census_universe['sha256']}"  # type: ignore[index]
        )
    probe_coverage = probe["coverage"]
    census_coverage = census["coverage"]
    for path, census_row in census_coverage.items():  # type: ignore[union-attr]
        probe_row = probe_coverage.get(path)  # type: ignore[union-attr]
        if probe_row is None:
            diffs.append(f"coverage missing path {path}")
            continue
        for key, census_value in census_row.items():
            probe_value = probe_row.get(key)
            if probe_value != census_value:
                diffs.append(
                    f"coverage {path} {key}: probe {probe_value} census {census_value}"
                )
    probe_clocks = probe["publication_clock"]["expectation_observations_clock_fields"]  # type: ignore[index]
    census_clocks = census["publication_clock"]["expectation_observations_clock_fields"]  # type: ignore[index]
    for key, census_value in census_clocks.items():
        probe_value = probe_clocks.get(key)
        if probe_value != census_value:
            diffs.append(
                f"publication_clock {key}: probe {probe_value} census {census_value}"
            )
    census_sources = {
        row["path"]: row
        for row in census["sources"]  # type: ignore[index]
        if row.get("rows") is not None
    }
    probe_sources = {row["path"]: row for row in probe["sources"]}  # type: ignore[index]
    for path, census_row in census_sources.items():
        probe_row = probe_sources.get(path)
        if probe_row is None:
            diffs.append(f"sources missing {path}")
            continue
        if probe_row["rows"] != census_row["rows"]:
            diffs.append(
                f"sources {path} rows: probe {probe_row['rows']} census {census_row['rows']}"
            )
        if census_row.get("blob") and probe_row["blob"] != census_row["blob"]:
            diffs.append(
                f"sources {path} blob: probe {probe_row['blob']} census {census_row['blob']}"
            )
    return diffs


def summary_line(receipt: dict[str, object]) -> str:
    gaps = receipt["gaps"]
    g1 = gaps["G1"]["value"]  # type: ignore[index]
    g2 = gaps["G2"]["value"]  # type: ignore[index]
    g5 = gaps["G5"]["value"]  # type: ignore[index]
    status = receipt["cohorts"]["attempt_status_full_file"]  # type: ignore[index]
    attempts = receipt["cohorts"]["attempts"]["full_file"]["rows"]  # type: ignore[index]
    matched = "MATCH" if receipt["universe"]["matched"] else "MISMATCH"  # type: ignore[index]
    return (
        f"universe {g1['universe_names']} sha {matched} "
        f"issuer_id_resolved {g1['issuer_id_resolved']} "
        f"undated {g2['undated_alias_rows']} "
        f"dated {g2['alias_rows_dated_le_cutoff']} "
        f"cik_map {g1['cik_map_universe_tickers']} "
        f"openfigi {g1['openfigi_universe_tickers']} "
        f"identity_resolution {g1['identity_resolution_universe_symbols']} "
        f"source_clocks {g5['source_effective_at_nonnull']}/"
        f"{g5['source_published_at_nonnull']} "
        f"attempts {attempts} success {status.get('success', 0)} "
        f"partial {status.get('partial', 0)} null {status.get('null', 0)} "
        f"r1_status {receipt['r1_status']}"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only R1 readiness probe. Reads git blobs for --rev "
            "(default origin/main) and writes a JSON receipt. "
            "--check compares shared counts with a census JSON receipt."
        )
    )
    parser.add_argument(
        "--rev",
        default="origin/main",
        help="Git revision whose blobs are measured. Default: origin/main.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write the JSON receipt to this path instead of stdout.",
    )
    parser.add_argument(
        "--check",
        type=Path,
        help="Census JSON receipt. Exit non-zero if any shared count differs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        receipt, headlines = build_receipt(args.rev)
    except ProbeError as exc:
        print(f"HEADLINE: blob read failed: {exc.command}", file=sys.stderr)
        print(exc.detail, file=sys.stderr)
        return 2
    text = json.dumps(receipt, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    print(summary_line(receipt), file=sys.stderr)
    exit_code = 0
    for headline in headlines:
        print(headline, file=sys.stderr)
        exit_code = 2
    if args.check:
        census = json.loads(args.check.read_text(encoding="utf-8"))
        diffs = shared_mismatches(receipt, census)
        if diffs:
            print("r1-readiness-probe --check: FAIL", file=sys.stderr)
            for diff in diffs:
                print(f"MISMATCH {diff}", file=sys.stderr)
            return 1 if exit_code == 0 else exit_code
        print("r1-readiness-probe --check: OK (shared counts equal)", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
