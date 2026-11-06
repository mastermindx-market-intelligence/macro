"""Intraday (hourly) US price accrual via Polygon / massive.com -> data/intraday/<T>.parquet.

Powers the **4H timeframe** on US single-stock charts and the 2D/3D intraday
bar-derivation hooks (engine/bar_derive.py): the collector pulls hourly bars, ships
them as site/intraday/<T>.json (scripts/build_chart_data) for the chart, and keeps the
raw store the signal-engine / Standout-grid sessions can later resample. US-only by
entitlement — the plan covers US stocks REST aggregates; non-US markets have no
intraday source, so they keep daily-derived timeframes only.

HONEST FRESHNESS — the Polygon **STANDARD** stocks plan serves **15-MINUTE-DELAYED**
aggregates. This is NOT real-time: every bar's timestamp trails the wall clock by at
least ~15 minutes. We stamp that floor on the store (a ``_meta.json`` sidecar) so every
downstream consumer/label can say "delayed" truthfully. Upgrading to a real-time/
websocket plan later -> set DELAYED_MIN = 0 (see research/LIVE_DATA_POLYGON.md).

APPEND-ONLY / KEY-DEDUPED — each run reads the existing per-ticker parquet, re-fetches
only a small recent window (with a 2-day overlap so late bar corrections are picked up),
concatenates, and de-dupes on the bar timestamp (keep='last'). So an hourly run extends
the store cheaply instead of re-pulling 180 days every time. ``--full`` forces a clean
re-fetch; ``--lookback-days`` sets the cold-start window when no prior file exists.

Curated to the deep-history US names (data/stocks/*) + sector/factor ETFs — the most-viewed,
candle-capable set — to keep the API call count and data footprint modest. Fail-safe: no
API key -> no-op; a per-ticker error is logged and skipped, never aborts the run. Mirrors
scripts/build_polygon_gex.accrue (its own persistence path, driven from scripts/collect.py).

Cannot be exercised live locally without the key (CI secret); the append/dedup + universe
+ no-key no-op paths are unit-tested in tests/test_polygon_intraday.py.

REUSING THE SAME SOURCE OWNER AT ANOTHER CADENCE (2026-11-03) — this collector is the
incumbent source owner for US intraday aggregates and can be pointed at another cadence
(e.g. 30-minute) WITHOUT becoming a second collector, timer or store:
``accrue(..., multiplier=30, timespan="minute")``. The default path is untouched — the
cadence still resolves from the existing ``polygon.intraday`` config and stays hourly.
Three guards, all firing BEFORE any vendor call: a non-default cadence REQUIRES an
explicit ``out_dir``; adjacent store metadata (``_meta.json`` "bar", per-ticker receipt
"bar_seconds") that identifies a DIFFERENT cadence is a refusal; and a non-default
cadence additionally needs the target directory to be empty or to carry metadata
identifying the REQUESTED cadence (a directory holding store files with no
cadence-identifying metadata cannot be proven compatible).

RETAINED OBSERVATIONS (opt-in, ``retain_observations=True`` / ``--retain-observations``) —
each nonempty aggregate result is retained verbatim as an immutable, content-addressed
JSON capture at ``<outdir>/observations/<TICKER>/<sha256>.json``
(``polygon.intraday_observation/v1``): the exact aggregate records the vendor returned,
the query window that produced them, and the honest post-fetch wall clock at which they
were observed. The capture is written BEFORE the receipt that advertises it, is never
overwritten, and a capture that cannot be read back byte-exact is refused rather than
advertised; a correction therefore yields a SECOND, distinct capture and the earlier one
is kept. These records are vendor-native aggregates — what the vendor returned for that
window; they do NOT assert that every constituent minute traded. Nothing here claims
admission, liveness or realtime.

The capture-extended receipt uses v2 and preserves all v1 fields (it adds
``observation_file`` / ``observation_sha256`` / ``observation_available_at``); the legacy
receipt fields are unchanged and the legacy v1 schema/shape is kept whenever
no capture was requested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from collectors.polygon_options import PolygonOptions  # noqa: E402
from engine.options_signal_episode import (  # noqa: E402
    PRICE_BASIS,
    PRICE_RECEIPT_SCHEMA,
    TIMESTAMP_BASIS,
)
from lib import config  # noqa: E402

log = logging.getLogger("polygon_intraday")
GROUP = "intraday"

# Polygon STANDARD (stocks) plan delay floor, in minutes. 15-min delayed aggregates;
# NOT real-time. Stamped onto the store's _meta.json so consumers label honestly.
# Set to 0 once a real-time/websocket entitlement is live (see LIVE_DATA_POLYGON.md).
DELAYED_MIN = 15

# Re-fetch this many days back from the last stored bar on an incremental run, so a
# late aggregate correction (Polygon revises the most recent session) is captured.
_OVERLAP_DAYS = 2

# Cadence fallbacks — the shipped default is the hourly aggregate the store already
# holds. The live values come from config.polygon.intraday (multiplier/timespan).
DEFAULT_MULTIPLIER = 1
DEFAULT_TIMESPAN = "hour"

# Retained-observation contract.
OBSERVATION_SCHEMA = "polygon.intraday_observation/v1"
CAPTURE_PRICE_RECEIPT_SCHEMA = "polygon.intraday_price_receipt/v2"
OBSERVATION_DIRNAME = "observations"

# Credential/header-shaped field names that must never reach a retained capture.
# The aggregate endpoint returns only price/volume records; anything else in a row is
# an anomaly and is refused rather than silently scrubbed (a scrubbed capture would no
# longer be the exact vendor response).
_CREDENTIAL_FIELDS = frozenset({
    "apikey", "api_key", "authorization", "headers", "request_headers",
    "x-api-key", "token", "secret", "password",
})

# "<multiplier><timespan>" as written by _write_meta (e.g. "1hour", "30minute").
_BAR_LABEL_RE = re.compile(r"^(\d+)(minute|hour|day)$")


class IntradayRefusal(ValueError):
    """A refusal that must stop the run BEFORE any vendor call.

    Raised for an unusable cadence, a non-default cadence without an explicit out_dir,
    and a target store that already holds a different cadence. It is a ValueError so a
    caller that only knows the legacy contract still catches it.
    """


class ObservationCaptureError(RuntimeError):
    """A retained capture that cannot be written, read back or trusted.

    Never advertised as qualified: the run refuses to write the receipt that would
    point at those bytes.
    """


def _utc_now() -> datetime:
    """The aware wall clock every post-fetch reading uses.

    One seam, so a caller can pin the observation clock. It is NEVER the bar timestamp,
    never the ``as_of`` argument and never an inferred bar_end+delay.
    """
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("receipt clock must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _encode_json(payload: dict) -> bytes:
    """Canonical bytes for a JSON artifact (sorted keys, no NaN/Inf, trailing newline)."""
    return (json.dumps(payload, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _atomic_write_bytes(path: Path, encoded: bytes, *, exclusive: bool = False) -> None:
    """Publish fsynced bytes by replacement, or by an exclusive link for immutable captures."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            # Publish once without a check/replace race. A concurrent existing
            # name is acceptable only when it already contains these exact bytes.
            try:
                os.link(tmp, path)
            except FileExistsError:
                if path.read_bytes() != encoded:
                    raise ObservationCaptureError("immutable capture collision")
        else:
            os.replace(tmp, path)
        _fsync_directory(path.parent)
    finally:
        if tmp.exists():
            tmp.unlink()


def _atomic_write_json(path: Path, payload: dict) -> None:
    _atomic_write_bytes(path, _encode_json(payload))


def _bar_seconds(multiplier: int, timespan: str) -> int:
    unit = {
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }.get(timespan.lower())
    if unit is None or type(multiplier) is not int or multiplier <= 0:
        raise ValueError(f"unsupported Polygon aggregate cadence: {multiplier}{timespan}")
    return multiplier * unit


def _normalise_timespan(timespan: str) -> str:
    return str(timespan).strip().lower()


def _resolve_cadence(icfg: dict, *, multiplier: int | None, timespan: str | None) -> tuple[int, str, int]:
    """(multiplier, timespan, bar_seconds) for this run.

    The explicit override wins; otherwise the cadence resolves from the EXISTING
    ``polygon.intraday`` config, so the default run keeps its shipped cadence. An
    unusable cadence is refused here, before any vendor call.
    """
    cfg_mult = int(icfg.get("multiplier", DEFAULT_MULTIPLIER))
    cfg_span = _normalise_timespan(icfg.get("timespan", DEFAULT_TIMESPAN))
    mult = cfg_mult if multiplier is None else multiplier
    span = cfg_span if timespan is None else _normalise_timespan(timespan)
    if type(mult) is not int or mult <= 0:
        raise IntradayRefusal(f"unsupported Polygon aggregate cadence: {mult!r}{span}")
    try:
        seconds = _bar_seconds(mult, span)
    except ValueError as exc:
        raise IntradayRefusal(str(exc)) from exc
    return mult, span, seconds


def _store_cadence_markers(outdir: Path) -> list[tuple[str, int]]:
    """Adjacent store metadata that POSITIVELY identifies a cadence, as (source, seconds).

    ``_meta.json`` carries "bar" ("1hour"), each per-ticker receipt carries
    "bar_seconds". Unreadable/unidentifiable metadata is reported and ignored — it
    identifies no cadence, so it cannot identify a different one.
    """
    markers: list[tuple[str, int]] = []
    meta = outdir / "_meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text())
        except Exception as e:  # noqa: BLE001 — unreadable metadata identifies nothing
            log.warning("polygon intraday: unreadable %s (%s) — cadence not identified",
                        meta.name, e)
        else:
            label = str((data or {}).get("bar") or "")
            match = _BAR_LABEL_RE.match(label)
            if match:
                markers.append((meta.name, _bar_seconds(int(match.group(1)), match.group(2))))
            else:
                log.warning("polygon intraday: %s does not identify a cadence (bar=%r)",
                            meta.name, label)
    for receipt_path in sorted(outdir.glob("*.parquet.receipt.json")):
        try:
            data = json.loads(receipt_path.read_text())
        except Exception as e:  # noqa: BLE001 — unreadable metadata identifies nothing
            log.warning("polygon intraday: unreadable %s (%s) — cadence not identified",
                        receipt_path.name, e)
            continue
        seconds = (data or {}).get("bar_seconds")
        if type(seconds) is int:
            markers.append((receipt_path.name, seconds))
        else:
            log.warning("polygon intraday: %s does not identify a cadence", receipt_path.name)
    return markers


def _assert_cadence_compatible(outdir: Path, *, bar_seconds: int, bar_label: str,
                               require_provable: bool) -> None:
    """Refuse to write into a store that holds (or may hold) a DIFFERENT cadence.

    ``require_provable`` is set for a non-default cadence: the target directory must
    then be empty, or carry metadata identifying the REQUESTED cadence — a 30-minute
    run must never land inside an hourly store.
    """
    markers = _store_cadence_markers(outdir)
    for source, seconds in markers:
        if seconds != bar_seconds:
            raise IntradayRefusal(
                f"refusing to write {bar_label} bars into {outdir}: {source} identifies a "
                f"{seconds}s cadence, and a different cadence would corrupt that store"
            )
    if require_provable and not markers:
        stored = sorted(p.name for p in outdir.glob("*.parquet"))
        if stored:
            raise IntradayRefusal(
                f"refusing to write {bar_label} bars into {outdir}: the directory already "
                f"holds {len(stored)} store file(s) with no cadence-identifying metadata, "
                f"so the existing cadence cannot be proven compatible"
            )


def _assert_receipt_contract(outdir: Path, *, retain_observations: bool) -> None:
    """An opt-in capture store cannot silently migrate or downgrade existing receipts."""
    expected = CAPTURE_PRICE_RECEIPT_SCHEMA if retain_observations else PRICE_RECEIPT_SCHEMA
    for path in sorted(outdir.glob("*.parquet.receipt.json")):
        try:
            receipt = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise IntradayRefusal(f"cannot establish receipt contract for {path.name}") from exc
        if not isinstance(receipt, dict) or receipt.get("schema") != expected:
            raise IntradayRefusal(
                f"receipt contract mismatch in {path.name}; expected {expected}; "
                "store migration or downgrade is not authorized by this invocation")
    if retain_observations:
        for path in outdir.glob("*.parquet"):
            if not path.with_suffix(".parquet.receipt.json").is_file():
                raise IntradayRefusal(f"cannot establish retained-observation contract for {path.name}")
    elif (outdir / OBSERVATION_DIRNAME).exists():
        raise IntradayRefusal("retained observations exist; a no-retention run would weaken this store's contract")


def _assert_no_credentials(records: list) -> None:
    """Refuse a response that carries credential/header material.

    The aggregate endpoint returns only price/volume records. A credential-shaped field
    is an anomaly: the capture is refused rather than written with the secret removed,
    because a scrubbed capture would no longer be the exact vendor response.
    """
    for row in records:
        if not isinstance(row, dict):
            continue
        for key in row:
            if str(key).strip().lower() in _CREDENTIAL_FIELDS:
                raise ObservationCaptureError(
                    f"vendor aggregate record carries credential-shaped field {key!r}; "
                    f"refusing to retain it"
                )


def _retain_observation(
    outdir: Path,
    *,
    ticker: str,
    multiplier: int,
    timespan: str,
    query_from: str,
    query_to: str,
    records: list,
) -> dict:
    """Retain the EXACT aggregate records of one successful vendor response.

    Content-addressed and immutable: ``<outdir>/observations/<TICKER>/<sha256>.json``,
    where ``<sha256>`` is the digest of the exact file bytes. Bytes already present at
    that path are COMPARED, never overwritten when they differ. The observation clock
    is the aware wall clock read AFTER the response returned — never the bar timestamp,
    never ``as_of``, never an inferred bar_end+delay.
    """
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,31}", ticker):
        raise ObservationCaptureError("invalid US symbol for capture path")
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ObservationCaptureError("aggregate results must be a list of records")
    observed_at = _utc_now()
    if observed_at.tzinfo is None:
        raise ObservationCaptureError("observation clock must be timezone-aware")
    _assert_no_credentials(records)
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "ticker": ticker,
        "multiplier": multiplier,
        "timespan": timespan,
        "adjusted": True,
        "price_basis": PRICE_BASIS,
        "timestamp_basis": TIMESTAMP_BASIS,
        "vendor_delay_minutes": DELAYED_MIN,
        "query_from": query_from,
        "query_to": query_to,
        "source_observed_at": _iso_utc(observed_at),
        "results": records,
    }
    encoded = _encode_json(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    relative = f"{OBSERVATION_DIRNAME}/{ticker}/{digest}.json"
    path = outdir / OBSERVATION_DIRNAME / ticker / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as e:
            raise ObservationCaptureError(
                f"cannot read the existing capture {relative}: {e}") from e
        if existing != encoded:
            raise ObservationCaptureError(
                f"capture {relative} already exists with different bytes — refusing to "
                f"overwrite a content-addressed capture"
            )
        # Identical bytes: the capture is immutable, so the existing file stays.
    else:
        _atomic_write_bytes(path, encoded, exclusive=True)
        try:
            written = path.read_bytes()
        except OSError as e:
            raise ObservationCaptureError(
                f"capture {relative} is not readable after the write: {e}") from e
        if written != encoded or hashlib.sha256(written).hexdigest() != digest:
            raise ObservationCaptureError(
                f"capture {relative} did not read back as the retained bytes")
    available_at = _utc_now()
    if available_at.tzinfo is None:
        raise ObservationCaptureError("observation availability clock must be timezone-aware")
    if available_at < observed_at:
        raise ObservationCaptureError("observation availability clock regressed")
    return {
        "observation_file": relative,
        "observation_sha256": digest,
        "observation_available_at": _iso_utc(available_at),
        "observation_path": path,
    }


def _verify_observation(outdir: Path, observation: dict) -> None:
    """The retained capture must be present and byte-exact before it can be advertised."""
    path = outdir / observation["observation_file"]
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ObservationCaptureError(
            f"retained capture {observation['observation_file']} is missing or unreadable: {e}") from e
    if hashlib.sha256(raw).hexdigest() != observation["observation_sha256"]:
        raise ObservationCaptureError(
            f"retained capture {observation['observation_file']} does not match its recorded digest")


def _write_price_receipt(
    outdir: Path,
    *,
    ticker: str,
    frame: pd.DataFrame,
    bar_seconds: int,
    now_fn=None,
    observation: dict | None = None,
) -> Path:
    """Bind a post-fsync source clock and digest to one exact parquet version."""
    source = (outdir / f"{ticker}.parquet").resolve()
    raw = source.read_bytes()
    available = (now_fn or _utc_now)()
    if available.tzinfo is None:
        raise ValueError("price receipt clock must be timezone-aware")
    index = pd.to_datetime(frame.index, utc=True)
    if frame.empty or index.hasnans:
        raise ValueError(f"cannot receipt an empty/invalid price frame for {ticker}")
    receipt = {
        "schema": PRICE_RECEIPT_SCHEMA,
        "ticker": ticker,
        # Portable exact locator: resolved relative to this adjacent receipt.
        "source_file": source.name,
        "source_file_sha256": hashlib.sha256(raw).hexdigest(),
        "source_available_at": _iso_utc(available),
        "bar_seconds": bar_seconds,
        "vendor_delay_minutes": DELAYED_MIN,
        "adjusted": True,
        "price_basis": PRICE_BASIS,
        "timestamp_basis": TIMESTAMP_BASIS,
        "row_count": len(frame),
        "first_time": _iso_utc(index.min().to_pydatetime()),
        "last_time": _iso_utc(index.max().to_pydatetime()),
    }
    if observation is not None:
        # The capture must be present and byte-exact BEFORE the receipt advertises it:
        # a receipt must never point at bytes that are missing or altered.
        _verify_observation(outdir, observation)
        observed_available = datetime.fromisoformat(observation["observation_available_at"].replace("Z", "+00:00"))
        if available < observed_available:
            raise ObservationCaptureError("price receipt clock precedes capture availability")
        receipt["schema"] = CAPTURE_PRICE_RECEIPT_SCHEMA
        receipt["observation_file"] = observation["observation_file"]
        receipt["observation_sha256"] = observation["observation_sha256"]
        receipt["observation_available_at"] = observation["observation_available_at"]
    path = outdir / f"{ticker}.parquet.receipt.json"
    _atomic_write_json(path, receipt)
    return path


def _universe() -> list[str]:
    """Deep-history US single names (data/stocks/*.parquet) + sector/factor ETFs from
    config.yahoo. These are exactly the candle-capable, most-viewed US tickers the daily
    chart already draws as candlesticks — the natural set to also offer intraday on."""
    names: set[str] = set()
    d = config.data_dir() / "stocks"
    if d.exists():
        for p in d.glob("*.parquet"):
            names.add(p.stem)
    ycfg = (config.load().get("yahoo") or {}).get("tickers") or {}
    # sectors/factors = the ETF set; extras = the big index ETFs (SPY/QQQ/IWM) plus the
    # searchable off-index US roster (ADRs, recent IPOs) — all have stock-library pages.
    for grp in ("sectors", "factors", "extras"):
        for t in (ycfg.get(grp) or []):
            if not str(t).startswith("^"):
                names.add(str(t))
    return sorted(names)


def _poly_sym(ticker: str) -> str:
    """Polygon encodes US class shares with a dot (BRK.B); our store uses a dash (BRK-B)."""
    return ticker.replace("-", ".")


def _read_existing(path) -> pd.DataFrame | None:
    """Prior per-ticker store, or None. Tolerant: a corrupt/legacy file -> None (the run
    falls back to a full lookback fetch rather than aborting)."""
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        if df.empty:
            return None
        # legacy files may lack a tz-aware index name; normalise so concat/dedup is safe
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "ts"
        return df[~df.index.duplicated(keep="last")].sort_index()
    except Exception:  # noqa: BLE001 — never let one bad file abort the accrual
        return None


def _write_meta(outdir, *, bar: str, universe_n: int, now: datetime) -> None:
    """Sidecar that travels with the store so every consumer (and a human) sees the
    honest delay without parsing a parquet. pandas drops DataFrame.attrs on the parquet
    round-trip, so this JSON is the durable label."""
    try:
        (outdir / "_meta.json").write_text(json.dumps({
            "store": "polygon_intraday",
            "bar": bar,
            "delayed_min": DELAYED_MIN,
            "source": "polygon_standard",
            "realtime": DELAYED_MIN == 0,
            "adjusted": True,
            "price_basis": PRICE_BASIS,
            "timestamp_basis": TIMESTAMP_BASIS,
            "note": ("15-MINUTE DELAYED (Polygon Standard plan) — NOT real-time"
                     if DELAYED_MIN else "real-time feed"),
            "universe": universe_n,
            "updated": now.isoformat(),
        }, indent=2))
    except Exception as e:  # noqa: BLE001
        log.warning("polygon intraday: could not write _meta.json: %s", e)


def accrue(as_of=None, *, lookback_days: int | None = None, full: bool = False,
           only: list[str] | None = None, limit: int | None = None,
           out_dir: Path | None = None,
           multiplier: int | None = None, timespan: str | None = None,
           retain_observations: bool = False) -> dict:
    """Extend data/intraday/<T>.parquet with fresh Polygon bars.

    ``lookback_days`` overrides the cold-start window (when no prior file exists); on an
    incremental run the window is computed from the last stored bar. ``full`` ignores
    existing files (clean re-fetch). ``only`` is the explicit requested universe rather
    than an intersection with the chart-oriented default universe — an EXPLICIT EMPTY
    ``only`` means zero symbols, never the default full universe.

    ``multiplier``/``timespan`` override the aggregate cadence; each defaults to the
    existing ``polygon.intraday`` config, so the default run stays hourly. A cadence
    that differs from the configured default requires an explicit ``out_dir`` and is
    refused when the target store holds a different cadence — before any vendor call.

    ``retain_observations`` also retains the exact aggregate records of each nonempty
    aggregate result as immutable content-addressed captures and binds them in the
    versioned receipt. It requires an explicit compatible out_dir; existing v1/v2
    destinations cannot be migrated or downgraded by this invocation. The default
    run retains nothing and writes the legacy receipt shape.
    """
    icfg = (config.load().get("polygon") or {}).get("intraday") or {}
    mult, span, bar_seconds = _resolve_cadence(icfg, multiplier=multiplier, timespan=timespan)
    cfg_mult = int(icfg.get("multiplier", DEFAULT_MULTIPLIER))
    cfg_span = _normalise_timespan(icfg.get("timespan", DEFAULT_TIMESPAN))
    default_cadence = (mult == cfg_mult and span == cfg_span)

    # The VPS uses an external ephemeral store so intraday accrual never mutates
    # canonical repo data. Mac/CI callers keep the historical default.
    default_dir = config.data_dir() / GROUP
    outdir = Path(out_dir) if out_dir is not None else default_dir
    if not default_cadence and out_dir is None:
        raise IntradayRefusal(
            f"a non-default aggregate cadence ({mult}{span}) requires an explicit out_dir; "
            f"the default store {default_dir} holds the {cfg_mult}{cfg_span} bars")
    if retain_observations and out_dir is None:
        raise IntradayRefusal("retaining observations requires an explicit compatible out_dir")
    _assert_cadence_compatible(outdir, bar_seconds=bar_seconds, bar_label=f"{mult}{span}",
                               require_provable=not default_cadence)
    _assert_receipt_contract(outdir, retain_observations=retain_observations)

    client = PolygonOptions()   # reuses the entitled stocks REST client (auth + http_get)
    if not client.enabled():
        log.warning("polygon intraday: no API key (POLYGON_API_KEY/MASSIVE_API_KEY) — skipped")
        return {"status": "skipped", "rows": 0}

    lookback = int(lookback_days if lookback_days is not None else icfg.get("lookback_days", 180))
    sleep_s = float(icfg.get("sleep", 0.06))

    now = as_of or datetime.now(timezone.utc)
    to = now.date()
    outdir.mkdir(parents=True, exist_ok=True)

    if only is not None:
        # An EXPLICIT empty list means zero symbols — never the default full universe.
        universe = sorted({
            str(symbol).strip().upper()
            for symbol in only
            if str(symbol).strip()
        })
    else:
        universe = _universe()
    if limit:
        universe = universe[:limit]

    written = 0
    appended = 0
    observations_retained = 0
    for t in universe:
        path = outdir / f"{t}.parquet"
        existing = None if full else _read_existing(path)
        # incremental window: from just before the last stored bar (overlap to catch
        # corrections); cold-start: the full lookback.
        if existing is not None:
            frm = (existing.index.max() - pd.Timedelta(days=_OVERLAP_DAYS)).date()
        else:
            frm = to - timedelta(days=lookback)
        try:
            res = client._get(
                f"/v2/aggs/ticker/{_poly_sym(t)}/range/{mult}/{span}/{frm.isoformat()}/{to.isoformat()}",
                {"adjusted": "true", "sort": "asc", "limit": 50000})
            if res:                                   # empty (weekend/after-hours) -> keep file as-is
                observation = None
                if retain_observations:
                    # Retain the EXACT vendor response BEFORE any derived artifact is
                    # written, so the receipt can only ever advertise bytes that exist.
                    observation = _retain_observation(
                        outdir,
                        ticker=t,
                        multiplier=mult,
                        timespan=span,
                        query_from=frm.isoformat(),
                        query_to=to.isoformat(),
                        records=res,
                    )
                new = pd.DataFrame({
                    "open":   [r.get("o") for r in res],
                    "high":   [r.get("h") for r in res],
                    "low":    [r.get("l") for r in res],
                    "close":  [r.get("c") for r in res],
                    "volume": [r.get("v") for r in res],
                }, index=pd.to_datetime([r["t"] for r in res], unit="ms", utc=True))
                new.index.name = "ts"
                df = pd.concat([existing, new]) if existing is not None else new
                # KEY-DEDUP on the bar timestamp, last write wins (idempotent re-run safe).
                df = df[~df.index.duplicated(keep="last")].sort_index()
                before = 0 if existing is None else len(existing)
                # atomic write: tmp + replace so a crash mid-write can't truncate the store
                # (a corrupt file would force an expensive cold re-fetch). .tmp is not matched
                # by the *.parquet glob, so a stray temp never pollutes the universe.
                tmp = outdir / f"{t}.parquet.tmp"
                df.to_parquet(tmp)
                with tmp.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(tmp, path)
                _fsync_directory(outdir)
                _write_price_receipt(
                    outdir,
                    ticker=t,
                    frame=df,
                    bar_seconds=bar_seconds,
                    observation=observation,
                )
                written += 1
                appended += max(0, len(df) - before)
                if observation is not None:
                    observations_retained += 1
        except Exception as e:  # noqa: BLE001 — degrade per-ticker, never abort the accrual
            log.warning("polygon intraday %s failed: %s", t, e)
        finally:
            time.sleep(sleep_s)                       # pace EVERY iteration (incl. empty/error)

    if written:
        _write_meta(outdir, bar=f"{mult}{span}", universe_n=len(universe), now=now)
    log.info("polygon intraday: wrote %d/%d US tickers (+%d bars; %d%s; delayed_min=%d)",
             written, len(universe), appended, mult, span, DELAYED_MIN)
    result = {"status": "ok" if written else "stale", "rows": written,
              "appended": appended, "delayed_min": DELAYED_MIN}
    if retain_observations:
        result["observations_retained"] = observations_retained
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(
        description="Polygon STANDARD (15-min DELAYED) US aggregate bars -> "
                    "data/intraday/<T>.parquet (append-only, key-deduped). The cadence "
                    "resolves from config; another cadence needs --out-dir.")
    ap.add_argument("--lookback-days", type=int, default=None,
                    help="cold-start window when no prior file exists (default config 180); "
                         "an existing file is extended incrementally regardless")
    ap.add_argument("--full", action="store_true",
                    help="ignore existing files — clean full re-fetch + overwrite")
    ap.add_argument("--limit", type=int, default=None, help="cap the universe (debug)")
    ap.add_argument("--symbols", default=None,
                    help="comma-separated tickers to restrict to (debug); an explicit empty "
                         "value means zero symbols, never the full universe")
    ap.add_argument(
        "--out-dir",
        default=None,
        help="override data/intraday output directory (VPS uses /var/lib/macro-live/data/intraday)",
    )
    ap.add_argument("--multiplier", type=int, default=None,
                    help="aggregate multiplier (default: config polygon.intraday.multiplier); "
                         "a cadence other than the configured default requires --out-dir")
    ap.add_argument("--timespan", default=None,
                    help="aggregate timespan — minute|hour|day (default: config "
                         "polygon.intraday.timespan); a cadence other than the configured "
                         "default requires --out-dir")
    ap.add_argument("--retain-observations", action="store_true",
                    help="retain the exact vendor aggregate records of each nonempty "
                         "result as immutable captures (requires an explicit compatible --out-dir) under "
                         "<out-dir>/observations/<TICKER>/<sha256>.json and bind them in "
                         "the receipt")
    args = ap.parse_args()
    only = [s.strip() for s in args.symbols.split(",")] if args.symbols is not None else None
    try:
        print(
            accrue(
                lookback_days=args.lookback_days,
                full=args.full,
                only=only,
                limit=args.limit,
                out_dir=Path(args.out_dir) if args.out_dir else None,
                multiplier=args.multiplier,
                timespan=args.timespan,
                retain_observations=args.retain_observations,
            )
        )
    except IntradayRefusal as exc:
        print(f"polygon intraday refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
