"""Run the existing research-only LP estimator on an explicitly supplied CSV.

This is an ingestion harness, not a new registry or a published implication card.
The caller supplies ordered observations and their declared availability clocks.
The CSV contract is period,y,shock,known_at (one row per observation; horizons
count supplied observations, not calendar or verified trading sessions). Values
are used unchanged. Source-supplied clocks do not certify provider availability,
rights, causal identification or scientific quality.

The full input digest and estimator settings are logged through the existing
TrialLedger BEFORE estimation. Every explored configuration must use the same
honest family; this single-run harness cannot discover undisclosed prior searches.
BY adjusts the horizon panel; the ledger's reported search count does not itself
adjust the panel's p-values. Scientific qualification remains a separate task.

Example (requires an explicitly selected existing ledger; never runs a demo):
  python scripts/run_local_projections.py --input owner-panel.csv \\
    --cutoff 2026-10-19T00:00:00Z --family owner-study \\
    --ledger /approved/path/trial_ledger.jsonl

Only stdout receives a result. This harness never updates the experiment result
stores, research cards, qledger, signals, sizing or execution routes.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import engine.local_projections as lp
from engine.trial_ledger import TrialLedger

_MAX_BYTES = 8 * 1024 * 1024
_MAX_ROWS = 50000
_HEADER = ["period", "y", "shock", "known_at"]
_UTC = _dt.timezone.utc
_PERIOD_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

_KNOWN_AT_RE = re.compile(
    r"\A(?P<yr>\d{4})-(?P<mo>\d{2})-(?P<da>\d{2})"
    r"[Tt ]"
    r"(?P<hr>\d{2}):(?P<mi>\d{2})"
    r"(?::(?P<sec>\d{2})(?:\.(?P<frac>\d{1,6}))?)?"
    r"(?P<tz>Z|z|[+-]\d{2}:\d{2}|[+-]\d{4}|[+-]\d{2})\Z", re.ASCII
)

class PanelInputError(ValueError):
    """Raised for any structurally or semantically invalid panel input."""

def _reject(row, detail):
    prefix = f"row {row}: " if row else ""
    return PanelInputError(f"panel input rejected: {prefix}{detail}")

def _finite_float(text, name, row):
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise _reject(row, f"{name} must be a finite number, got {text!r}") from None
    if not math.isfinite(value):
        raise _reject(row, f"{name} must be a finite number, got {text!r}")
    return value

def _known_at_utc(text, row):
    match = _KNOWN_AT_RE.match(text)
    if match is None:
        raise _reject(
            row,
            "known_at must be ISO-8601 with an explicit timezone "
            f"(Z or numeric offset), got {text!r}",
        )
    offset_text = match.group("tz")
    if offset_text in ("Z", "z"):
        tzinfo = _UTC
    else:
        sign = -1 if offset_text[0] == "-" else 1
        digits = offset_text[1:].replace(":", "")
        hours = int(digits[0:2])
        minutes = int(digits[2:4]) if len(digits) >= 4 else 0
        if hours > 23 or minutes > 59:
            raise _reject(row, f"known_at timezone offset out of range: {offset_text!r}")
        tzinfo = _dt.timezone(sign * _dt.timedelta(hours=hours, minutes=minutes))
    fraction = match.group("frac")
    microsecond = int(fraction.ljust(6, "0")) if fraction else 0
    try:
        return _dt.datetime(
            int(match.group("yr")),
            int(match.group("mo")),
            int(match.group("da")),
            int(match.group("hr")),
            int(match.group("mi")),
            int(match.group("sec") or 0),
            microsecond,
            tzinfo=tzinfo,
        ).astimezone(_UTC)
    except (ValueError, OverflowError) as exc:
        raise _reject(row, f"known_at is not a valid instant: {text!r} ({exc})") from None

def parse_panel(raw: bytes, cutoff: _dt.datetime) -> dict:
    """Parse raw CSV panel bytes into aligned columns, or raise PanelInputError.

    Checks (all local and pure — no I/O, no mutation of ``raw``/``cutoff``,
    no row filtering, no imputation, no defaults):

    * ``raw``: non-empty UTF-8 CSV bytes, <= 8 MiB, no NUL byte, well-formed
      quoting. Header must be exactly ``period,y,shock,known_at`` (unique,
      ordered). CRLF and a single trailing newline are fine; blank or
      incomplete rows are not. At most 50000 data rows.
    * ``period``: canonical ``YYYY-MM-DD`` valid calendar dates, strictly
      increasing (duplicates/out-of-order rejected; spacing is observation
      sequence only, never calendar/trading-date proof).
    * ``y``/``shock``: finite floats (NaN/inf/empty rejected).
    * ``known_at``: ISO-8601 instant with explicit timezone (``Z`` or numeric
      offset), normalized to UTC.
    * ``cutoff``: timezone-aware datetime, normalized to UTC. Every row must
      satisfy period-midnight-UTC <= known_at <= cutoff.

    Returns ``{"period": [str...], "y": [float...], "shock": [float...],
    "known_at": [str isoformat UTC...], "cutoff": str isoformat UTC,
    "input_sha256": hex digest of the exact raw bytes}`` in original row
    order. All cells are source-supplied declarations; nothing here verifies
    availability, rights, or causal identification.
    """
    if not isinstance(cutoff, _dt.datetime):
        raise _reject(0, f"cutoff must be a datetime.datetime, got {type(cutoff).__name__}")
    try:
        if cutoff.utcoffset() is None:
            raise _reject(0, "cutoff must be timezone-aware; a naive cutoff is an unknown clock")
        cutoff_utc = cutoff.astimezone(_UTC)
    except (ValueError, OverflowError) as exc:
        raise _reject(0, f"cutoff cannot be normalized to UTC: {exc}") from None

    if type(raw) is not bytes:
        raise _reject(0, f"raw must be bytes, got {type(raw).__name__}")
    if not raw:
        raise _reject(0, "raw input is empty")
    if len(raw) > _MAX_BYTES:
        raise _reject(0, f"raw input is {len(raw)} bytes, over the {_MAX_BYTES}-byte (8 MiB) limit")
    input_sha256 = hashlib.sha256(raw).hexdigest()

    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _reject(0, f"raw input is not valid UTF-8: {exc}") from None
    if "\x00" in text:
        raise _reject(0, "raw input contains a NUL byte")

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
    except csv.Error as exc:
        raise _reject(0, f"malformed CSV in header row: {exc}") from None
    if header is None:
        raise _reject(0, "input is missing its header row")
    if not header:
        raise _reject(0, "header row is blank")
    if header != _HEADER:
        counts = {}
        for name in header:
            counts[name] = counts.get(name, 0) + 1
        duplicates = sorted(n for n, c in counts.items() if c > 1)
        missing = [n for n in _HEADER if n not in counts]
        extra = sorted(n for n in counts if n not in _HEADER)
        parts = []
        if duplicates:
            parts.append("duplicate column(s): " + ", ".join(duplicates))
        if missing:
            parts.append("missing column(s): " + ", ".join(missing))
        if extra:
            parts.append("unknown column(s): " + ", ".join(extra))
        if not parts:
            parts.append("columns must be exactly '" + ",".join(_HEADER) + "' in this order")
        raise _reject(0, "bad header row (" + "; ".join(parts) + ")")

    periods, ys, shocks, known_ats = [], [], [], []
    prev_period = None
    try:
        for row in reader:
            line = reader.line_num
            if not row:
                raise _reject(line, "blank row (empty lines are not allowed)")
            if len(row) != 4:
                raise _reject(
                    line, f"expected 4 fields period,y,shock,known_at; got {len(row)}: {row!r}"
                )
            if len(periods) >= _MAX_ROWS:
                raise _reject(line, f"more than {_MAX_ROWS} data rows; limit is {_MAX_ROWS}")

            period_text, y_text, shock_text, known_text = row

            if not _PERIOD_RE.match(period_text):
                raise _reject(line, f"period must be canonical YYYY-MM-DD, got {period_text!r}")
            try:
                period_date = _dt.date(
                    int(period_text[0:4]), int(period_text[5:7]), int(period_text[8:10])
                )
            except ValueError:
                raise _reject(
                    line, f"period is not a valid calendar date: {period_text!r}"
                ) from None
            if prev_period is not None and period_date <= prev_period:
                raise _reject(
                    line,
                    f"period {period_text} does not strictly increase after "
                    f"{prev_period.isoformat()}; duplicate or out-of-order periods are "
                    "rejected, and gaps are never imputed",
                )
            prev_period = period_date

            y_value = _finite_float(y_text, "y", line)
            shock_value = _finite_float(shock_text, "shock", line)

            known_utc = _known_at_utc(known_text, line)
            period_start = _dt.datetime(
                period_date.year, period_date.month, period_date.day, tzinfo=_UTC
            )
            if known_utc < period_start:
                raise _reject(
                    line,
                    f"known_at {known_utc.isoformat()} precedes midnight UTC of period "
                    f"{period_text}",
                )
            if known_utc > cutoff_utc:
                raise _reject(
                    line,
                    f"known_at {known_utc.isoformat()} is after the cutoff "
                    f"{cutoff_utc.isoformat()}; future or unknown clocks are rejected",
                )

            periods.append(period_text)
            ys.append(y_value)
            shocks.append(shock_value)
            known_ats.append(known_utc.isoformat())
    except csv.Error as exc:
        raise _reject(reader.line_num, f"malformed CSV (strict quoting): {exc}") from None

    if not periods:
        raise _reject(0, "input has a header but zero data rows")

    return {
        "period": periods,
        "y": ys,
        "shock": shocks,
        "known_at": known_ats,
        "cutoff": cutoff_utc.isoformat(),
        "input_sha256": input_sha256,
    }


def run_panel(raw: bytes, *, cutoff: datetime, family: str, ledger: TrialLedger,
              horizons: int = lp.HORIZONS, lags: int = lp.LAGS,
              embargo: int = lp.EMBARGO, min_obs: int = lp.MIN_OBS_PER_H) -> dict:
    """Register one complete configuration, then call the existing estimator.

    This function can append only to the caller's existing ledger. A storage
    failure propagates; estimation never runs after a failed registration.
    """
    panel = parse_panel(raw, cutoff)
    if (type(family) is not str or not family or family.strip() != family
            or len(family) > 128 or any(ord(c) < 32 for c in family)):
        raise PanelInputError("family must be an explicit non-empty name of at most 128 characters")
    for name, value, low, high in (("horizons", horizons, 0, 60), ("lags", lags, 1, 60),
                                    ("embargo", embargo, 1, 60), ("min_obs", min_obs, 3, 50000)):
        if type(value) is not int or not low <= value <= high:
            raise PanelInputError(f"{name} must be an integer in [{low}, {high}]")
    config = {
        "harness": "mastermind.local_projection_run/v1",
        "estimator_schema": lp.SCHEMA,
        "estimator_sha256": hashlib.sha256(Path(lp.__file__).read_bytes()).hexdigest(),
        "input_sha256": panel["input_sha256"], "cutoff": panel["cutoff"],
        "period_start": panel["period"][0], "period_end": panel["period"][-1],
        "n_rows": len(panel["y"]), "horizons": horizons, "lags": lags,
        "embargo": embargo, "min_obs": min_obs, "fdr_alpha": lp.FDR_ALPHA,
        "transform": "none; supplied y and shock values, ordered observation rows",
    }
    if not ledger.path.is_file():
        raise PanelInputError("ledger must name an existing approved trial ledger")
    with ledger.owner_transaction():
        if ledger.load_error or ledger.corrupt_lines:
            raise PanelInputError("existing trial ledger is unreadable or contains corrupt rows")
        added = ledger.log_trial(config, family=family, info_cutoff=panel["cutoff"],
                                 source="scripts/run_local_projections.py",
                                 note="Registered complete supplied CSV configuration before LP estimation; research only.")
        registered_sha256 = hashlib.sha256(ledger.raw_readback()).hexdigest()
    # A successful owner-transaction exit precedes estimation/consumer output.
    result = lp.impulse_response(panel["y"], panel["shock"], horizons=horizons,
                                 lags=lags, embargo=embargo, min_obs=min_obs,
                                 ledger=ledger, family=family)
    return {
        "schema": "mastermind.local_projection_run/v1",
        "input": {key: panel[key] for key in ("input_sha256", "cutoff", "period", "known_at")},
        "registration": {"family": family, "new_trial_logged": added,
                         "effective_n": ledger.effective_n(family), "config": config,
                         "ledger_snapshot_sha256": registered_sha256},
        "result": result,
        "limitations": "Availability clocks are source-supplied declarations, not independently verified. "
                       "Horizon units are supplied observation rows. No causal identification, data rights "
                       "or scientific acceptance is established. All searched configurations must use "
                       "the same honest family. BY corrects horizons; recorded search N is disclosure, "
                       "not an additional p-value adjustment.",
        "authority": {"research_only": True, "causal": False, "signal": False,
                      "sizing": False, "execution": False, "publication": False},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True, help="Explicit source CSV; never synthetic demo generation")
    parser.add_argument("--cutoff", required=True, help="ISO8601 information cutoff with explicit timezone")
    parser.add_argument("--family", required=True, help="Existing honest search family used for every explored configuration")
    parser.add_argument("--ledger", type=Path, required=True, help="Explicit existing TrialLedger file; no default store")
    parser.add_argument("--horizons", type=int, default=lp.HORIZONS)
    parser.add_argument("--lags", type=int, default=lp.LAGS)
    parser.add_argument("--embargo", type=int, default=lp.EMBARGO)
    args = parser.parse_args(argv)
    try:
        if not args.ledger.is_file():
            raise PanelInputError("--ledger must name an existing approved trial ledger")
        if args.input.resolve() == args.ledger.resolve():
            raise PanelInputError("input and trial ledger must be different files")
        with args.input.open("rb") as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        cutoff = datetime.fromisoformat(args.cutoff.replace("Z", "+00:00"))
        envelope = run_panel(raw, cutoff=cutoff, family=args.family, ledger=TrialLedger(args.ledger),
                             horizons=args.horizons, lags=args.lags, embargo=args.embargo)
        output = json.dumps(envelope, ensure_ascii=False, allow_nan=False)
    except (ValueError, OSError) as exc:
        print(f"Local-projection run refused: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
