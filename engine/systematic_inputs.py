"""RESEARCH input qualification bridge — Systematic Strategies (Macro #10089).

A thin, read-only gate between a caller-supplied R2 price capture and the
systematic backtester.  It answers one question honestly: *may these bytes be
used as current data, and may they be used as economics?*  Those are different
questions with different answers, and the module keeps them apart on purpose.

This is **not** an ingestion pipeline, a price authority, a corporate-action
adjuster, a registry or a scheduler.  Every one of those already has an owner.
The parent lane (``systematic-10089-ceo-web-01``) owns acquisition; this module
only qualifies what that lane hands over, and only the inputs the caller
explicitly supplies.

Reused contracts (imported, never copied or re-declared):

* :mod:`lib.us_cash_calendar` — the shared published US cash-session calendar.
  Every gap and freshness decision routes through ``is_session`` /
  ``sessions_between``; no holiday table is hand-coded here.
* :mod:`lib.dataos.price` — :class:`AdjustmentBasis`, whose own ``unlawful_for``
  prose is the law this module cites for a raw tape.
* :mod:`lib.dataos.registry` — :class:`Registry` / :class:`DatasetContract` for
  status, basis and rights, and :func:`qualify_action_input` as the single
  qualify-first action gate.  ``_is_evidence_pointer`` is imported for the R00.02
  evidence rule so this file cannot drift a second copy of it.
* :mod:`lib.dataos.price_views` is referenced in documentation only; the
  ``PriceFrame`` adapter target is defined by PR #10093, which is **not merged**
  into this base, so no import of it happens here and no per-bar past receipt is
  fabricated.

Laws this module deliberately does not break:

* A price jump is an *inference*.  It may add a ``SUSPECTED`` reason and never a
  factor; :func:`qualify_action_input` owns that word.
* Absence of a jump is **not** evidence of absence of an action.
* A fresh manifest cannot authenticate stale local bytes, and a structurally
  ready input is not capital- or economically-eligible.
* ``historical_original_availability_proven`` stays ``False`` unless an
  existing-owner proof pointer passes the R00.02 evidence test; a bare caller
  ``true`` is downgraded, not believed.

The returned document is ``systematic_input_qualification.v1``, mode
``RESEARCH_ONLY``.  It is a diagnostic artifact, not a source ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from lib import us_cash_calendar as _cal
from lib.dataos.price import AdjustmentBasis
from lib.dataos.registry import (
    ActionInputStatus,
    DatasetContract,
    DatasetStatus,
    Registry,
    _is_evidence_pointer,
    qualify_action_input,
)

__all__ = [
    "SCHEMA", "MODE_RESEARCH_ONLY", "MODE_CURRENT", "MODE_HISTORICAL_RECONSTRUCTION",
    "CaptureError", "CaptureObject", "CaptureManifest", "QualificationInputs",
    "parse_manifest", "resolve_capture_path", "read_object_bytes",
    "qualify_systematic_inputs", "qualify_one_instrument",
]

#: The one emitted document schema.
SCHEMA = "systematic_input_qualification.v1"
#: Never anything else; this bridge has no execution mode.
MODE_RESEARCH_ONLY = "RESEARCH_ONLY"
#: Caller asked whether these bytes are *current*.
MODE_CURRENT = "current"
#: Caller explicitly asked for a historical reconstruction of the past.  It is
#: never reported as current freshness.
MODE_HISTORICAL_RECONSTRUCTION = "historical_reconstruction"
_MODES = (MODE_CURRENT, MODE_HISTORICAL_RECONSTRUCTION)

#: Allowed uses.  ``descriptive_reconstruction`` is reachable ONLY when the
#: economics actually qualified; otherwise this stays ``inspect_only``.
ALLOWED_USE_INSPECT_ONLY = "inspect_only"
ALLOWED_USE_DESCRIPTIVE = "descriptive_reconstruction"

#: Defaults a caller may override; none widens an authority.
DEFAULT_MAX_OBJECT_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
#: A close-to-close move at or beyond this fraction raises a *suspected* action
#: reason only.  It is a reason code, never a factor.
#:
#: 0.4, not 0.5: the most common real event this has to catch is a 2:1 split,
#: which is exactly a 50% move.  A threshold that only fires at >=50% therefore
#: sits ON the boundary of that event and misses any split that arrives with
#: even a little drift (a real 2:1 prints ~0.4999, not 0.5000).  0.4 brackets
#: 2:1 and 3:1 with room while staying far above ordinary daily moves.
DEFAULT_JUMP_FRACTION = 0.4

#: Raw OHLCV columns this bridge requires in a frame.
OHLC_COLUMNS = ("open", "high", "low", "close")
VOLUME_COLUMN = "volume"
#: Registry-declared source prefix an object key must carry.
SOURCE_KEY_PREFIX = "massive_stock_day/"


class CaptureError(ValueError):
    """A caller-supplied capture is structurally impossible to qualify."""


# ── Stable blocker / finding codes ─────────────────────────────────────────
# One UPPER_SNAKE code per decision rule so a downstream refusal path can
# branch on the code instead of parsing prose.

class Code:
    """Namespace of the stable codes this module emits."""

    # capture / receipt
    RECEIPT_JSON_INVALID = "RECEIPT_JSON_INVALID"
    RECEIPT_DUPLICATE_KEY = "RECEIPT_DUPLICATE_KEY"
    RECEIPT_NOT_OBJECT = "RECEIPT_NOT_OBJECT"
    RECEIPT_TIMESTAMP_NAIVE = "RECEIPT_TIMESTAMP_NAIVE"
    RECEIPT_TIMESTAMP_AFTER_AS_OF = "RECEIPT_TIMESTAMP_AFTER_AS_OF"
    RECEIPT_TIMESTAMP_MISSING = "RECEIPT_TIMESTAMP_MISSING"
    RECEIPT_SCOPE_NOT_READ_ONLY = "RECEIPT_SCOPE_NOT_READ_ONLY"
    # object integrity
    PATH_ESCAPE = "PATH_ESCAPE"
    PATH_SYMLINK = "PATH_SYMLINK"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    OBJECT_NOT_REGULAR_FILE = "OBJECT_NOT_REGULAR_FILE"
    OBJECT_TOO_LARGE = "OBJECT_TOO_LARGE"
    OBJECT_CHANGED_DURING_READ = "OBJECT_CHANGED_DURING_READ"
    OBJECT_SIZE_MISMATCH = "OBJECT_SIZE_MISMATCH"
    OBJECT_HASH_MISMATCH = "OBJECT_HASH_MISMATCH"
    OBJECT_ROWS_MISMATCH = "OBJECT_ROWS_MISMATCH"
    DUPLICATE_OBJECT_KEY = "DUPLICATE_OBJECT_KEY"
    SOURCE_KEY_PREFIX_MISMATCH = "SOURCE_KEY_PREFIX_MISMATCH"
    # frame structure
    FRAME_NOT_SUPPLIED = "FRAME_NOT_SUPPLIED"
    FRAME_EMPTY = "FRAME_EMPTY"
    FRAME_UNREADABLE = "FRAME_UNREADABLE"
    DATE_COLUMN_MISSING = "DATE_COLUMN_MISSING"
    SESSION_LABEL_UNPARSEABLE = "SESSION_LABEL_UNPARSEABLE"
    SESSION_LABEL_DUPLICATE = "SESSION_LABEL_DUPLICATE"
    SESSION_LABEL_NOT_CHRONOLOGICAL = "SESSION_LABEL_NOT_CHRONOLOGICAL"
    SESSION_LABEL_NOT_A_SESSION = "SESSION_LABEL_NOT_A_SESSION"
    SESSION_INDEX_IS_AWARE = "SESSION_INDEX_IS_AWARE"
    PRICE_COLUMN_MISSING = "PRICE_COLUMN_MISSING"
    PRICE_NON_FINITE = "PRICE_NON_FINITE"
    PRICE_NOT_POSITIVE = "PRICE_NOT_POSITIVE"
    PRICE_INEQUALITY_VIOLATION = "PRICE_INEQUALITY_VIOLATION"
    VOLUME_NULL = "VOLUME_NULL"
    VOLUME_NEGATIVE = "VOLUME_NEGATIVE"
    VOLUME_ZERO_SUSPECTED_MISSINGNESS = "VOLUME_ZERO_SUSPECTED_MISSINGNESS"
    CALENDAR_GAP = "CALENDAR_GAP"
    # freshness
    EXPECTED_SESSION_NOT_SUPPLIED = "EXPECTED_SESSION_NOT_SUPPLIED"
    LAST_SESSION_STALE = "LAST_SESSION_STALE"
    LAST_SESSION_NOT_A_SESSION = "LAST_SESSION_NOT_A_SESSION"
    LAST_SESSION_IN_FUTURE = "LAST_SESSION_IN_FUTURE"
    FRESHNESS_NOT_EVALUABLE = "FRESHNESS_NOT_EVALUABLE"
    MODE_HISTORICAL_NOT_CURRENT = "MODE_HISTORICAL_NOT_CURRENT"
    # adjustment / actions / rights
    SOURCE_NOT_PRODUCED = "SOURCE_NOT_PRODUCED"
    BASIS_NOT_DECLARED = "BASIS_NOT_DECLARED"
    BASIS_RAW_UNLAWFUL_FOR_ECONOMICS = "BASIS_RAW_UNLAWFUL_FOR_ECONOMICS"
    ACTION_EVIDENCE_MISSING = "ACTION_EVIDENCE_MISSING"
    ACTION_EVIDENCE_MALFORMED = "ACTION_EVIDENCE_MALFORMED"
    ACTION_NOT_CONFIRMED = "ACTION_NOT_CONFIRMED"
    ACTION_SOURCE_NOT_PRODUCED = "ACTION_SOURCE_NOT_PRODUCED"
    SUSPECTED_ACTION_DISCONTINUITY = "SUSPECTED_ACTION_DISCONTINUITY"
    PIT_CORPORATE_ACTIONS_NOT_DECLARED = "PIT_CORPORATE_ACTIONS_NOT_DECLARED"
    RIGHTS_UNDECLARED = "RIGHTS_UNDECLARED"
    RIGHTS_NOT_GRANTED = "RIGHTS_NOT_GRANTED"
    RIGHTS_EVIDENCE_UNLAWFUL = "RIGHTS_EVIDENCE_UNLAWFUL"
    # availability / universe
    HISTORICAL_AVAILABILITY_NOT_PROVEN = "HISTORICAL_AVAILABILITY_NOT_PROVEN"
    SYMBOL_EXCLUDED = "SYMBOL_EXCLUDED"


# ── Strict, duplicate-key-safe JSON ────────────────────────────────────────

def _reject_constant(token: str) -> Any:
    """NaN/Infinity are not JSON and are not a missing value either."""
    raise CaptureError(
        f"{Code.RECEIPT_JSON_INVALID}: non-finite JSON constant {token!r} is not admissible"
    )


def _no_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    """Duplicate keys are a caller bug, not a last-wins merge."""
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise CaptureError(f"{Code.RECEIPT_DUPLICATE_KEY}: {key!r}")
        seen.add(key)
    return dict(pairs)


def loads_strict(raw: str | bytes) -> Any:
    """``json.loads`` that refuses duplicate keys and NaN/Infinity."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:  # pragma: no cover - defensive
            raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: {exc}") from exc
    try:
        return json.loads(
            raw,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except CaptureError:
        raise
    except json.JSONDecodeError as exc:
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: {exc}") from exc


def _aware(value: Any, *, what: str) -> datetime:
    """Parse an ISO-8601 timestamp and require an explicit offset.

    A naive receipt timestamp is refused, never assumed to be UTC: the capture
    stamps ``received_at`` from the observer and a local-time reading would
    silently move an observation across the ``as_of`` fence.
    """
    if not isinstance(value, str) or not value.strip():
        raise CaptureError(f"{Code.RECEIPT_TIMESTAMP_MISSING}: {what}")
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: {what}={value!r}: {exc}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaptureError(f"{Code.RECEIPT_TIMESTAMP_NAIVE}: {what}={value!r}")
    return parsed


def _digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ── Capture manifest (the caller's receipt, parsed and bounded) ─────────────

@dataclass(frozen=True)
class CaptureObject:
    """One declared object.  Metadata only — the bytes are read separately."""

    object_key: str
    bytes: int
    sha256: str
    received_at: datetime | None
    object_last_modified: str | None = None
    rows: int | None = None
    columns: tuple[str, ...] = ()
    first_session: str | None = None
    last_session: str | None = None
    timezone: str | None = None

    @property
    def basename(self) -> str:
        """The declared key's basename — the ONLY filename this bridge trusts.

        The receipt's ``local_file`` is an observation of where the parent's
        writer happened to put bytes; it is never a path this module opens.
        """
        return self.object_key.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class CaptureManifest:
    """A parsed receipt: what the parent captured, and under what scope."""

    receipt_sha256: str | None
    scope: str | None
    historical_original_availability_proven: bool
    corporate_actions_qualified: bool
    objects: tuple[CaptureObject, ...]
    exclusions: tuple[Mapping[str, Any], ...] = ()
    owner_availability_proof: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def object_for(self, object_key: str) -> CaptureObject | None:
        for obj in self.objects:
            if obj.object_key == object_key:
                return obj
        return None


def _as_int(value: Any, *, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: {what} must be int, got {value!r}")
    return value


def _as_str(value: Any, *, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: {what} must be a non-empty string")
    return value


def parse_manifest(raw: str | bytes) -> CaptureManifest:
    """Parse a caller-supplied receipt into a :class:`CaptureManifest`.

    Raises :class:`CaptureError` on malformed or structurally impossible input.
    A duplicate key anywhere in the document (nested objects included) is a
    refusal, because a silently last-wins key is how a second claim about the
    same capture hides beside the first.
    """
    document = loads_strict(raw)
    if not isinstance(document, Mapping):
        raise CaptureError(f"{Code.RECEIPT_NOT_OBJECT}: receipt root must be an object")

    raw_objects = document.get("objects")
    if not isinstance(raw_objects, list):
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: 'objects' must be a list")

    objects: list[CaptureObject] = []
    seen_keys: set[str] = set()
    for entry in raw_objects:
        if not isinstance(entry, Mapping):
            raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: objects[] entry must be an object")
        object_key = _as_str(entry.get("object_key"), what="objects[].object_key")
        if object_key in seen_keys:
            raise CaptureError(f"{Code.DUPLICATE_OBJECT_KEY}: {object_key}")
        seen_keys.add(object_key)
        digest = _as_str(entry.get("sha256"), what=f"objects[{object_key}].sha256")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise CaptureError(
                f"{Code.RECEIPT_JSON_INVALID}: objects[{object_key}].sha256 is not a "
                f"64-char hex digest"
            )
        received = entry.get("received_at")
        columns = entry.get("columns")
        objects.append(
            CaptureObject(
                object_key=object_key,
                bytes=_as_int(entry.get("bytes"), what=f"objects[{object_key}].bytes"),
                sha256=digest.lower(),
                received_at=_aware(received, what=f"objects[{object_key}].received_at")
                if received is not None
                else None,
                object_last_modified=(
                    entry.get("object_last_modified")
                    if isinstance(entry.get("object_last_modified"), str)
                    else None
                ),
                rows=(
                    _as_int(entry["rows"], what=f"objects[{object_key}].rows")
                    if entry.get("rows") is not None
                    else None
                ),
                columns=tuple(str(c) for c in columns) if isinstance(columns, list) else (),
                first_session=(
                    entry["first_session"] if isinstance(entry.get("first_session"), str) else None
                ),
                last_session=(
                    entry["last_session"] if isinstance(entry.get("last_session"), str) else None
                ),
                timezone=entry["timezone"] if isinstance(entry.get("timezone"), str) else None,
            )
        )

    exclusions = document.get("exclusions") or []
    if not isinstance(exclusions, list):
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: 'exclusions' must be a list")

    return CaptureManifest(
        receipt_sha256=(digest.lower() if isinstance(document.get("receipt_sha256"), str) else None),
        scope=document.get("scope") if isinstance(document.get("scope"), str) else None,
        historical_original_availability_proven=bool(
            document.get("historical_original_availability_proven")
        ),
        corporate_actions_qualified=bool(document.get("corporate_actions_qualified")),
        objects=tuple(objects),
        exclusions=tuple(e for e in exclusions if isinstance(e, Mapping)),
        owner_availability_proof=(
            document["owner_availability_proof"]
            if isinstance(document.get("owner_availability_proof"), str)
            else None
        ),
        raw=document,
    )


# ── Path safety and read-only object observation ───────────────────────────

def resolve_capture_path(root: Path | str, basename: str) -> Path:
    """Resolve ``basename`` strictly *under* ``root``.

    Traversal (``..``), absolute names, and any symlink that leaves the root are
    refused.  The caller's receipt ``local_file`` never reaches this function —
    only a declared key's basename does.
    """
    if not isinstance(basename, str) or not basename.strip():
        raise CaptureError(f"{Code.PATH_ESCAPE}: empty basename")
    name = basename.strip()
    if name != Path(name).name or name in (".", "..") or "/" in name or "\\" in name:
        raise CaptureError(f"{Code.PATH_ESCAPE}: {basename!r} is not a bare basename")
    if os.path.isabs(name):
        raise CaptureError(f"{Code.PATH_ESCAPE}: {basename!r} is absolute")

    base = Path(root)
    try:
        real_root = base.resolve(strict=True)
    except (OSError, FileNotFoundError) as exc:
        raise CaptureError(f"{Code.OBJECT_NOT_FOUND}: capture root {base}: {exc}") from exc
    candidate = base / name

    # A symlink at the final component is refused outright: even a symlink that
    # stays inside the root means the bytes are not the declared object.
    if candidate.is_symlink():
        raise CaptureError(f"{Code.PATH_SYMLINK}: {name!r} is a symlink")
    try:
        real = candidate.resolve(strict=True)
    except (OSError, FileNotFoundError) as exc:
        raise CaptureError(f"{Code.OBJECT_NOT_FOUND}: {name!r}: {exc}") from exc
    if real.parent != real_root:
        raise CaptureError(f"{Code.PATH_ESCAPE}: {name!r} resolves outside the capture root")
    return real


def read_object_bytes(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    max_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
) -> bytes:
    """Read one object read-only and prove its size and digest.

    The file is stat-ed before and after the read; a size/mtime/inode/device
    change between the two observations is a refusal, because the digest would
    then describe bytes that were never a single stable file.
    """
    if expected_bytes < 0:
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: negative declared bytes")
    if expected_bytes > max_bytes:
        raise CaptureError(
            f"{Code.OBJECT_TOO_LARGE}: declared {expected_bytes} exceeds bound {max_bytes}"
        )
    if not path.is_file():
        raise CaptureError(f"{Code.OBJECT_NOT_REGULAR_FILE}: {path}")

    before = path.stat()
    if before.st_size != expected_bytes:
        raise CaptureError(
            f"{Code.OBJECT_SIZE_MISMATCH}: declared {expected_bytes}, actual {before.st_size}"
        )
    if before.st_size > max_bytes:
        raise CaptureError(f"{Code.OBJECT_TOO_LARGE}: {before.st_size} exceeds {max_bytes}")

    payload = path.read_bytes()
    after = path.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        raise CaptureError(f"{Code.OBJECT_CHANGED_DURING_READ}: {path}")

    actual = _digest_bytes(payload)
    if actual != expected_sha256.lower():
        raise CaptureError(f"{Code.OBJECT_HASH_MISMATCH}: declared {expected_sha256}, actual {actual}")
    return payload


def read_frame(payload: bytes, suffix: str) -> pd.DataFrame:
    """Decode parquet/CSV bytes.  Only these two; anything else is refused."""
    import io

    lowered = suffix.lower()
    if lowered.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(payload))
    if lowered.endswith(".csv"):
        return pd.read_csv(io.BytesIO(payload))
    raise CaptureError(f"{Code.FRAME_UNREADABLE}: unsupported object suffix {suffix!r}")


# ── Frame qualification ────────────────────────────────────────────────────

def _session_series(frame: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Return (naive date series, structural codes) from the frame's date labels.

    The labels are *session labels*, not UTC arrival instants: a naive ``Date``
    index is the exchange's session, and an aware index is refused outright
    rather than coerced (``SESSION_INDEX_IS_AWARE``) because a tz-aware daily
    label means somebody attached a receipt clock to a session and the two can
    no longer be told apart.
    """
    codes: list[str] = []
    index = frame.index
    if isinstance(index, pd.DatetimeIndex) and index.tz is not None:
        codes.append(Code.SESSION_INDEX_IS_AWARE)
        index = index.tz_convert("UTC").tz_localize(None)

    if "date" in frame.columns:
        raw = frame["date"]
    else:
        name = index.name if isinstance(index.name, str) else None
        if name in (None, "", "Date", "timestamp"):
            raw = pd.Series(index, index=range(len(frame)))
        elif name.lower() in ("date", "session", "trade_date"):
            raw = pd.Series(index, index=range(len(frame)))
        else:
            codes.append(Code.DATE_COLUMN_MISSING)
            raw = pd.Series([None] * len(frame), index=range(len(frame)))

    parsed = pd.to_datetime(raw, errors="coerce")
    if parsed.isna().any():
        codes.append(Code.SESSION_LABEL_UNPARSEABLE)
    try:
        as_dates = parsed.dt.date
    except AttributeError:  # pragma: no cover - defensive
        codes.append(Code.SESSION_LABEL_UNPARSEABLE)
        return pd.Series([None] * len(frame), index=range(len(frame))), codes
    return as_dates, codes


def _check_price_block(frame: pd.DataFrame, *, volume_requires_positive: bool
                       ) -> tuple[list[str], dict[str, Any]]:
    """Finite, positive, correctly-ordered OHLC and non-negative volume."""
    codes: list[str] = []
    stats: dict[str, Any] = {}

    missing = [c for c in (*OHLC_COLUMNS, VOLUME_COLUMN) if c not in frame.columns]
    if missing:
        codes.append(Code.PRICE_COLUMN_MISSING)
        stats["missing_columns"] = missing
        return codes, stats
    stats["missing_columns"] = []

    for name in OHLC_COLUMNS:
        values = pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype="float64", na_value=None)
        finite = [i for i, v in enumerate(values) if v is not None and v == v and abs(v) != float("inf")]
        non_finite = [i for i, v in enumerate(values) if v is None or v != v or abs(v) == float("inf")]
        if non_finite:
            codes.append(Code.PRICE_NON_FINITE)
            stats.setdefault("non_finite_rows", {})[name] = len(non_finite)
        non_positive = [i for i in finite if values[i] <= 0.0]
        if non_positive:
            codes.append(Code.PRICE_NOT_POSITIVE)
            stats.setdefault("non_positive_rows", {})[name] = len(non_positive)

    low = pd.to_numeric(frame["low"], errors="coerce")
    high = pd.to_numeric(frame["high"], errors="coerce")
    open_ = pd.to_numeric(frame["open"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    bad = (low > high) | (low > open_) | (low > close) | (high < open_) | (high < close)
    if bool(bad.fillna(False).any()):
        codes.append(Code.PRICE_INEQUALITY_VIOLATION)
        stats["inequality_rows"] = int(bad.fillna(False).sum())

    volume = pd.to_numeric(frame[VOLUME_COLUMN], errors="coerce")
    null_volume = int(volume.isna().sum())
    if null_volume:
        codes.append(Code.VOLUME_NULL)
    negatives = int((volume.dropna() < 0).sum())
    if negatives:
        codes.append(Code.VOLUME_NEGATIVE)
    zeros = int((volume.dropna() == 0).sum())
    # Always published, so a consumer can tell "measured zero zeros" from
    # "not measured" — and so a null is never read as a 0 by omission.
    stats["zero_volume_sessions"] = zeros
    stats["null_volume_rows"] = null_volume
    stats["negative_volume_rows"] = negatives
    if zeros:
        # The registry records that native parsing normalises missing source
        # volume to zero, so a zero is *suspected erased missingness*, not a
        # quiet zero-volume session.  A dependent capacity check refuses it.
        if volume_requires_positive:
            codes.append(Code.VOLUME_ZERO_SUSPECTED_MISSINGNESS)
    return codes, stats


def _suspected_jumps(close: pd.Series, sessions: pd.Series, *, fraction: float) -> list[dict[str, Any]]:
    """Large close-to-close moves, reported as SUSPECTED reasons only.

    This never applies a factor and never upgrades to CONFIRMED.  It exists so
    the *suspicion* is recorded where the raw tape was read; the word itself
    belongs to :func:`qualify_action_input`, which is what the caller is told to
    run against ``origin="price_discontinuity"``.
    """
    values = pd.to_numeric(close, errors="coerce").to_numpy(dtype="float64", na_value=None)
    out: list[dict[str, Any]] = []
    for i in range(1, len(values)):
        prev, curr = values[i - 1], values[i]
        if prev is None or curr is None or prev != prev or curr != curr:
            continue
        if prev <= 0 or curr <= 0:
            continue
        change = abs(curr / prev - 1.0)
        if change >= fraction:
            out.append(
                {
                    "session": sessions.iloc[i].isoformat(),
                    "previous_session": sessions.iloc[i - 1].isoformat(),
                    "change_fraction": round(float(change), 6),
                    "origin": "price_discontinuity",
                    "action_status": ActionInputStatus.SUSPECTED.value,
                    "factor_applied": False,
                }
            )
    return out


def _qualify_frame(
    *,
    symbol: str,
    frame: pd.DataFrame,
    volume_requires_positive: bool,
    jump_fraction: float,
) -> dict[str, Any]:
    """Structural findings for one instrument.  Pure; no I/O, no registry."""
    codes: list[str] = []
    findings: dict[str, Any] = {"symbol": symbol}

    if frame is None or len(frame) == 0:
        return {
            "symbol": symbol,
            "blockers": [Code.FRAME_EMPTY],
            "action_blockers": [],
            "structural_ready": False,
            "findings": findings,
        }

    sessions, session_codes = _session_series(frame)
    codes.extend(session_codes)

    parsed = [d for d in sessions.tolist() if isinstance(d, date)]
    findings["rows"] = int(len(frame))
    findings["first_session"] = parsed[0].isoformat() if parsed else None
    findings["last_session"] = parsed[-1].isoformat() if parsed else None

    if parsed:
        seen = set()
        duplicates = [d for d in parsed if d in seen or seen.add(d)]
        if duplicates:
            codes.append(Code.SESSION_LABEL_DUPLICATE)
            findings["duplicate_session_labels"] = sorted({d.isoformat() for d in duplicates})
        if any(parsed[i] >= parsed[i + 1] for i in range(len(parsed) - 1)):
            codes.append(Code.SESSION_LABEL_NOT_CHRONOLOGICAL)
        non_sessions = sorted({d.isoformat() for d in parsed if not _cal.is_session(d)})
        if non_sessions:
            codes.append(Code.SESSION_LABEL_NOT_A_SESSION)
            findings["labels_that_are_not_sessions"] = non_sessions

        # Calendar gap evidence: the shared published calendar decides which
        # full dates are sessions, so a missing session is *detected*, never
        # compressed away by comparing counts.
        first, last = parsed[0], parsed[-1]
        if last >= first:
            expected = _cal.sessions_between(first, last)
            present = set(parsed)
            missing_dates = [d for d in expected if d not in present]
            findings["expected_sessions_in_range"] = len(expected)
            findings["present_sessions_in_range"] = len([d for d in expected if d in present])
            if missing_dates:
                codes.append(Code.CALENDAR_GAP)
                findings["missing_sessions"] = [d.isoformat() for d in missing_dates]

    price_codes, price_stats = _check_price_block(frame, volume_requires_positive=volume_requires_positive)
    codes.extend(price_codes)
    findings["price"] = price_stats

    if Code.PRICE_COLUMN_MISSING not in codes and Code.SESSION_LABEL_UNPARSEABLE not in codes:
        findings["suspected_actions"] = _suspected_jumps(
            frame["close"], sessions, fraction=jump_fraction
        )
    else:
        findings["suspected_actions"] = []

    blockers = sorted(set(codes))
    suspected = findings.get("suspected_actions") or []
    return {
        "symbol": symbol,
        "blockers": blockers,
        # A suspected action is NOT a structural defect: the file is still
        # complete and well-formed.  It is reported separately so a consumer
        # cannot read a clean `blockers` list as "no action happened".
        "action_blockers": [Code.SUSPECTED_ACTION_DISCONTINUITY] if suspected else [],
        "structural_ready": not blockers,
        "findings": findings,
    }


def qualify_one_instrument(
    *,
    symbol: str,
    frame: pd.DataFrame,
    volume_requires_positive: bool = False,
    jump_fraction: float = DEFAULT_JUMP_FRACTION,
) -> dict[str, Any]:
    """Public single-instrument structural qualification (used by the CLI/tests)."""
    return _qualify_frame(
        symbol=symbol,
        frame=frame,
        volume_requires_positive=volume_requires_positive,
        jump_fraction=jump_fraction,
    )


# ── Source / rights / action qualification ─────────────────────────────────

def _rights_findings(contract: DatasetContract) -> tuple[list[str], dict[str, Any]]:
    """Read the three INDEPENDENT rights off the registered contract.

    A right that is not declared is not a denial and not a grant — it is
    ``unverified``, and dependent use is refused (R00.02: a readable label
    grants nothing).
    """
    from lib.dataos.registry import RIGHTS_KEYS

    codes: list[str] = []
    rights: dict[str, Any] = {}
    evidence = contract.rights.get("evidence") or {}
    for key in RIGHTS_KEYS:
        value = contract.rights.get(key)
        rights[key] = value if isinstance(value, str) else None
        if value == "granted":
            pointer = evidence.get(key) if isinstance(evidence, Mapping) else None
            if not _is_evidence_pointer(pointer):
                codes.append(Code.RIGHTS_EVIDENCE_UNLAWFUL)
                rights[f"{key}_evidence"] = pointer
        elif value == "not_granted":
            codes.append(Code.RIGHTS_NOT_GRANTED)
        else:
            codes.append(Code.RIGHTS_UNDECLARED)
    # Dependent (economic) use needs purchase_access AND internal_computation.
    # The two are never inferred from one another; redistribution is reported
    # but not required for internal research.  A ``granted`` right whose
    # evidence pointer is unlawful blocks economics even though it says granted.
    economics_blocking: list[str] = []
    for key in ("purchase_access", "internal_computation"):
        if rights.get(key) != "granted":
            economics_blocking.append(
                Code.RIGHTS_NOT_GRANTED
                if rights.get(key) == "not_granted"
                else Code.RIGHTS_UNDECLARED
            )
    if Code.RIGHTS_EVIDENCE_UNLAWFUL in codes:
        economics_blocking.append(Code.RIGHTS_EVIDENCE_UNLAWFUL)
    return sorted(set(codes)), {
        "rights": rights,
        "economics_blocking": sorted(set(economics_blocking)),
    }


def _action_evidence_verdict(
    evidence: Mapping[str, Any] | None, *, registry: Registry, action_dataset_id: str
) -> tuple[ActionInputStatus | None, str | None, list[str]]:
    """Run the EXISTING qualify-first gate. Never a local re-implementation.

    Returns ``(status, reason, codes)``; ``(None, None, codes)`` when no usable
    evidence was supplied.  The caller cannot smuggle a status in: the verdict
    is computed here from the observation and the live registry.
    """
    if evidence is None:
        return None, None, [Code.ACTION_EVIDENCE_MISSING]
    if not isinstance(evidence, Mapping):
        return None, None, [Code.ACTION_EVIDENCE_MALFORMED]
    payload = dict(evidence)
    if not payload.get("dataset_id"):
        payload["dataset_id"] = action_dataset_id
    try:
        verdict = qualify_action_input(payload, registry=registry)
    except (TypeError, ValueError):
        # A structurally impossible observation has no honest status; the caller
        # is told the evidence is malformed rather than handed a soft verdict.
        return None, None, [Code.ACTION_EVIDENCE_MALFORMED]
    codes: list[str] = []
    if verdict.status is not ActionInputStatus.CONFIRMED:
        codes.append(Code.ACTION_NOT_CONFIRMED)
        if verdict.reason == "SOURCE_NOT_PRODUCED":
            codes.append(Code.ACTION_SOURCE_NOT_PRODUCED)
    return verdict.status, verdict.reason, codes


def _discontinuity_observation(action_dataset_id: str) -> dict[str, Any]:
    """The observation shape that, by construction, can only ever be SUSPECTED.

    A price jump is passed through the same gate as any other candidate so the
    SUSPECTED verdict and its reason code come from the existing law, not from
    this file's own vocabulary.
    """
    return {
        "dataset_id": action_dataset_id,
        "endpoint": None,
        "field_convention": None,
        "receipt": None,
        "origin": "price_discontinuity",
        "response": None,
        "rights_limited": False,
    }


# ── The qualification document ─────────────────────────────────────────────

@dataclass(frozen=True)
class QualificationInputs:
    """Everything the pure function is allowed to see."""

    manifest: CaptureManifest
    frames: Mapping[str, pd.DataFrame]
    declared_universe: tuple[str, ...]
    as_of: datetime
    expected_session: date | None
    price_contract: DatasetContract
    action_dataset_id: str
    action_evidence: Mapping[str, Any] | None = None
    economic_evidence: Mapping[str, Any] | None = None
    registry: Registry | None = None
    mode: str = MODE_CURRENT
    volume_requires_positive: bool = False
    jump_fraction: float = DEFAULT_JUMP_FRACTION


def qualify_systematic_inputs(inputs: QualificationInputs) -> dict[str, Any]:
    """Qualify a supplied capture. Pure: no I/O, no network, no writes.

    ``current_data_ready`` and ``economic_inputs_ready`` are computed and
    reported separately and are deliberately NOT collapsed.  With the raw
    sample the honest answer is "structurally fresh for the symbols that are
    complete, incomplete for the rest, and economically blocked for all" —
    unknown is not free execution.
    """
    if inputs.mode not in _MODES:
        raise CaptureError(f"{Code.RECEIPT_JSON_INVALID}: unknown mode {inputs.mode!r}")
    if inputs.as_of.tzinfo is None or inputs.as_of.utcoffset() is None:
        raise CaptureError(f"{Code.RECEIPT_TIMESTAMP_NAIVE}: as_of must be offset-aware")

    manifest = inputs.manifest
    source_codes: list[str] = []
    source_facts: dict[str, Any] = {}

    # ── capture-level fencing ──────────────────────────────────────────────
    if manifest.scope is not None and "read_only" not in manifest.scope:
        source_codes.append(Code.RECEIPT_SCOPE_NOT_READ_ONLY)

    # historical_original_availability_proven: a bare caller ``true`` is not
    # believed.  Only an existing-owner proof pointer that passes the R00.02
    # evidence test may set it.
    availability_proven = False
    if manifest.historical_original_availability_proven:
        if manifest.owner_availability_proof and _is_evidence_pointer(
            manifest.owner_availability_proof
        ):
            availability_proven = True
            source_facts["historical_original_availability_proof"] = (
                manifest.owner_availability_proof
            )
        else:
            source_codes.append(Code.HISTORICAL_AVAILABILITY_NOT_PROVEN)
    else:
        source_codes.append(Code.HISTORICAL_AVAILABILITY_NOT_PROVEN)

    # ── source identity, basis, rights ────────────────────────────────────
    contract = inputs.price_contract
    source_facts["dataset_id"] = contract.dataset_id
    source_facts["status"] = (
        contract.status.value if isinstance(contract.status, DatasetStatus) else str(contract.status)
    )
    source_facts["basis"] = contract.basis or None
    source_facts["adjustment"] = contract.adjustment or None
    source_facts["point_in_time_corporate_actions"] = contract.point_in_time_corporate_actions
    if contract.status is not DatasetStatus.PRODUCED:
        source_codes.append(Code.SOURCE_NOT_PRODUCED)
    if contract.basis not in {b.value for b in AdjustmentBasis}:
        source_codes.append(Code.BASIS_NOT_DECLARED)
    basis_member: AdjustmentBasis | None = None
    try:
        basis_member = AdjustmentBasis(contract.basis)
    except ValueError:
        basis_member = None
    if basis_member is not None:
        source_facts["basis_lawful_for"] = list(basis_member.lawful_for)
        source_facts["basis_unlawful_for"] = list(basis_member.unlawful_for)

    rights_codes, rights_facts = _rights_findings(contract)
    source_codes.extend(rights_codes)

    # ── corporate actions ──────────────────────────────────────────────────
    action_codes: list[str] = []
    action_facts: dict[str, Any] = {
        "action_dataset_id": inputs.action_dataset_id,
        "manifest_corporate_actions_qualified": manifest.corporate_actions_qualified,
        "factor_applied": False,
        "confirmed_event_source": None,
    }
    economic_basis: str | None = None
    if inputs.registry is None:
        raise CaptureError(
            "registry is required: an action observation can never be CONFIRMED against "
            "a source nobody registered (qualify_action_input has no registry-free shape)"
        )
    status, reason, codes = _action_evidence_verdict(
        inputs.action_evidence, registry=inputs.registry, action_dataset_id=inputs.action_dataset_id
    )
    action_codes.extend(codes)
    action_facts["evidence_verdict"] = status.value if status else None
    action_facts["evidence_reason"] = reason
    if status is ActionInputStatus.CONFIRMED:
        action_facts["confirmed_event_source"] = inputs.action_dataset_id

    if inputs.economic_evidence is not None:
        declared = inputs.economic_evidence.get("adjustment_basis")
        if isinstance(declared, str) and declared.strip():
            economic_basis = declared.strip()

    # The raw-basis law, quoted from the enum's own prose rather than re-declared.
    raw_unlawful = (
        basis_member is not None
        and basis_member is AdjustmentBasis.RAW
        and basis_member.unlawful_for
    )
    if raw_unlawful:
        source_codes.append(Code.BASIS_RAW_UNLAWFUL_FOR_ECONOMICS)
    if economic_basis == AdjustmentBasis.RAW.value:
        source_codes.append(Code.BASIS_RAW_UNLAWFUL_FOR_ECONOMICS)
    if contract.point_in_time_corporate_actions is not True:
        action_codes.append(Code.PIT_CORPORATE_ACTIONS_NOT_DECLARED)

    # A price jump is never an economic unlock and never a factor.  Run it
    # through the same gate so the reason code is the existing one.
    if status is None and inputs.action_evidence is None:
        suspected = qualify_action_input(
            _discontinuity_observation(inputs.action_dataset_id), registry=inputs.registry
        )
        action_facts["price_path_verdict"] = suspected.status.value
        action_facts["price_path_reason"] = suspected.reason

    # ── per-instrument ─────────────────────────────────────────────────────
    exclusions_by_symbol: dict[str, str] = {}
    for exclusion in manifest.exclusions:
        key = exclusion.get("object_key") or exclusion.get("symbol")
        if isinstance(key, str):
            exclusions_by_symbol[key.rsplit("/", 1)[-1].rsplit(".", 1)[0].upper()] = str(
                exclusion.get("reason") or "excluded by capture manifest"
            )

    instruments: list[dict[str, Any]] = []
    for symbol in inputs.declared_universe:
        frame = inputs.frames.get(symbol)
        declared_object = next(
            (o for o in manifest.objects
             if o.basename.rsplit(".", 1)[0].upper() == symbol.upper()),
            None,
        )
        if declared_object is None:
            record = {
                "symbol": symbol,
                "blockers": [Code.FRAME_NOT_SUPPLIED],
                "action_blockers": [],
                "structural_ready": False,
                "findings": {"symbol": symbol, "declared_object": None},
                "source": {"key_prefix_matches": False},
            }
        else:
            record = _qualify_frame(
                symbol=symbol,
                frame=frame,
                volume_requires_positive=inputs.volume_requires_positive,
                jump_fraction=inputs.jump_fraction,
            )
            record["source"] = {
                "object_key": declared_object.object_key,
                "key_prefix_matches": declared_object.object_key.startswith(SOURCE_KEY_PREFIX),
                "bytes": declared_object.bytes,
                "sha256": declared_object.sha256,
                "received_at": (
                    declared_object.received_at.isoformat()
                    if declared_object.received_at
                    else None
                ),
                "manifest_rows": declared_object.rows,
                "manifest_first_session": declared_object.first_session,
                "manifest_last_session": declared_object.last_session,
            }
            if not declared_object.object_key.startswith(SOURCE_KEY_PREFIX):
                record["blockers"] = sorted(
                    set(record["blockers"]) | {Code.SOURCE_KEY_PREFIX_MISMATCH}
                )
                record["structural_ready"] = False
            # The declared row count is checked against the decoded frame, so a
            # receipt cannot claim a file it did not describe.
            if declared_object.rows is not None and frame is not None:
                actual_rows = int(len(frame))
                record["source"]["actual_rows"] = actual_rows
                if actual_rows != declared_object.rows:
                    record["blockers"] = sorted(
                        set(record["blockers"]) | {Code.OBJECT_ROWS_MISMATCH}
                    )
                    record["structural_ready"] = False
            # received_at must not be in the future relative to the injected as_of.
            if declared_object.received_at is None:
                record["blockers"] = sorted(
                    set(record["blockers"]) | {Code.RECEIPT_TIMESTAMP_MISSING}
                )
                record["structural_ready"] = False
            elif declared_object.received_at > inputs.as_of:
                record["blockers"] = sorted(
                    set(record["blockers"]) | {Code.RECEIPT_TIMESTAMP_AFTER_AS_OF}
                )
                record["structural_ready"] = False
            # The manifest's own last_session is a CLAIM; the frame is the fact.
            actual_last = record["findings"].get("last_session")
            claimed_last = declared_object.last_session
            record["freshness"] = {
                "actual_last_session": actual_last,
                "manifest_last_session": claimed_last,
                "manifest_claim_matches_actual": (
                    claimed_last is not None and claimed_last == actual_last
                ),
                "expected_completed_session": (
                    inputs.expected_session.isoformat() if inputs.expected_session else None
                ),
            }
            if inputs.expected_session is None:
                record["freshness"]["status"] = Code.FRESHNESS_NOT_EVALUABLE
                record["freshness"]["blockers"] = [Code.EXPECTED_SESSION_NOT_SUPPLIED]
            elif actual_last is None:
                record["freshness"]["status"] = Code.LAST_SESSION_NOT_A_SESSION
                record["freshness"]["blockers"] = [Code.FRESHNESS_NOT_EVALUABLE]
            else:
                last_date = date.fromisoformat(actual_last)
                if last_date > inputs.expected_session:
                    record["freshness"]["blockers"] = [Code.LAST_SESSION_IN_FUTURE]
                elif last_date < inputs.expected_session:
                    record["freshness"]["blockers"] = [Code.LAST_SESSION_STALE]
                else:
                    record["freshness"]["blockers"] = []
                record["freshness"]["status"] = (
                    "fresh" if not record["freshness"]["blockers"] else "not_fresh"
                )
            if record["freshness"]["blockers"]:
                record["blockers"] = sorted(
                    set(record["blockers"]) | set(record["freshness"]["blockers"])
                )
                record["structural_ready"] = False
            if actual_last is not None and not _cal.is_session(date.fromisoformat(actual_last)):
                record["blockers"] = sorted(
                    set(record["blockers"]) | {Code.LAST_SESSION_NOT_A_SESSION}
                )
                record["structural_ready"] = False

        if symbol.upper() in exclusions_by_symbol:
            # Retained, never dropped: an excluded instrument stays in the
            # declared universe with an explicit blocked state.
            record["excluded"] = True
            record["exclusion_reason"] = exclusions_by_symbol[symbol.upper()]
            record["blockers"] = sorted(set(record.get("blockers", [])) | {Code.SYMBOL_EXCLUDED})
            record["structural_ready"] = False
        else:
            record["excluded"] = False
        instruments.append(record)

    # ── rollup ─────────────────────────────────────────────────────────────
    excluded_symbols = sorted(r["symbol"] for r in instruments if r.get("excluded"))
    present_symbols = [r for r in instruments if not r.get("excluded")]
    all_structural = all(r["structural_ready"] for r in present_symbols) and bool(present_symbols)

    mode_blocks: list[str] = []
    if inputs.mode == MODE_HISTORICAL_RECONSTRUCTION:
        mode_blocks.append(Code.MODE_HISTORICAL_NOT_CURRENT)

    freshness_evaluated = inputs.expected_session is not None
    source_blocks_economics = [
        c for c in source_codes if c != Code.HISTORICAL_AVAILABILITY_NOT_PROVEN
    ]
    rights_economics_blocking = rights_facts["economics_blocking"]

    economics_blockers = sorted(
        set(source_blocks_economics)
        | set(rights_economics_blocking)
        | set(action_codes)
    )
    economic_inputs_ready = not economics_blockers and all_structural
    current_data_ready = (
        all_structural
        and not mode_blocks
        and freshness_evaluated
        and not (source_codes and Code.RECEIPT_SCOPE_NOT_READ_ONLY in source_codes)
    )

    allowed_use = (
        ALLOWED_USE_DESCRIPTIVE
        if economic_inputs_ready and inputs.mode == MODE_HISTORICAL_RECONSTRUCTION
        else ALLOWED_USE_INSPECT_ONLY
    )

    document = {
        "schema": SCHEMA,
        "mode": MODE_RESEARCH_ONLY,
        "as_of": inputs.as_of.isoformat(),
        "requested_mode": inputs.mode,
        "expected_completed_session": (
            inputs.expected_session.isoformat() if inputs.expected_session else None
        ),
        "current_data_ready": bool(current_data_ready),
        "economic_inputs_ready": bool(economic_inputs_ready),
        "allowed_use": allowed_use,
        "capital_eligible": False,
        "live_orders_enabled": False,
        "historical_original_availability_proven": availability_proven,
        "capture": {
            "receipt_sha256": manifest.receipt_sha256,
            "scope": manifest.scope,
            "object_count": len(manifest.objects),
            "declared_universe": list(inputs.declared_universe),
            "excluded_symbols": excluded_symbols,
        },
        "source": {
            **source_facts,
            "blockers": sorted(set(source_codes)),
            "rights": rights_facts["rights"],
        },
        "actions": {
            **action_facts,
            "economic_adjustment_basis": economic_basis,
            "blockers": sorted(set(action_codes)),
        },
        "economics_blockers": economics_blockers,
        "mode_blockers": sorted(set(mode_blocks)),
        "instruments": instruments,
        "reconstruction_note": (
            "A whole-file receipt time is a CURRENT observation of every historical row "
            "in the file. It is not proof of what was knowable at any past decision "
            "point, and no per-bar past receipt is asserted here."
        ),
        "limitations": [
            "structural readiness is not capital or economic eligibility",
            "raw tape is unqualified for return math until an action-qualified view exists",
            "this document records evidence and readiness; it grants no signal authority",
        ],
    }
    return document