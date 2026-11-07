"""Retained FRED/Treasury series as an opt-in reviewed Press context.

Narrow by construction.  Six closed parquet series, each read from bytes the
caller has already hash-bound in its reviewed context row.  This module is a
measurement extractor, not a producer, feed, provider, rights record or
publication path.  It reads the exact requested observation date and refuses
everything else: no latest row, no truncated timestamp, no filled or
carry-forward value, and no derived series whose stored identity does not hold
on the values actually selected.

The retained bytes are FRED/Treasury series carried into our own measurement
set.  ``tier='first_party'`` on a fact built here means WE extracted the
measurement from retained bytes; ``source_name`` names the retained series the
measurement came from.  Nothing here states a release clock, a first-known
date, a prediction, a causal link or an independent corroboration, and nothing
here grants rights to publish.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

# The closed series set.  A path outside this map is not a Treasury context
# source, whatever the retained file happens to contain.
@dataclass(frozen=True)
class Series:
    fact_id: str
    series: str
    column: str
    label: str
    unit: str


SERIES: dict[str, Series] = {
    'data/fred/DGS2.parquet': Series(
        'treasury_dgs2', 'DGS2', 'us2y',
        '2-year Treasury constant maturity yield', 'percent'),
    'data/fred/DGS10.parquet': Series(
        'treasury_dgs10', 'DGS10', 'us10y',
        '10-year Treasury constant maturity yield', 'percent'),
    'data/fred/DGS30.parquet': Series(
        'treasury_dgs30', 'DGS30', 'us30y',
        '30-year Treasury constant maturity yield', 'percent'),
    'data/fred/DFII10.parquet': Series(
        'treasury_dfii10', 'DFII10', 'us10y_real',
        '10-year Treasury constant maturity inflation-indexed real yield', 'percent'),
    'data/fred/T10YIE.parquet': Series(
        'treasury_t10yie', 'T10YIE', 'breakeven_10y',
        '10-year breakeven inflation rate', 'percent'),
    'data/fred/T10Y2Y.parquet': Series(
        'treasury_t10y2y', 'T10Y2Y', 'spread_2s10s',
        '10-year minus 2-year Treasury constant maturity yield spread',
        'percentage points'),
}

# A derived series is admissible only beside the two retained series it is
# derived from, and only when their stored values reproduce it exactly.
DERIVED: dict[str, tuple[str, str]] = {
    'treasury_t10y2y': ('treasury_dgs10', 'treasury_dgs2'),
    'treasury_t10yie': ('treasury_dgs10', 'treasury_dfii10'),
}

_LIMIT = 8_000_000
_SHA256 = re.compile(r'[0-9a-f]{64}')
_ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


def _read_bound(path: Path, digest: str, limit: int = _LIMIT) -> bytes:
    """Read the exact bounded bytes and check the caller's digest first.

    The hash is taken over the bytes that are about to be parsed, so a
    substituted file cannot reach the extractor behind a pinned digest.
    """
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError('treasury evidence requires a full SHA256')
    if path.is_symlink() or not path.is_file():
        raise ValueError('treasury evidence must be a bounded regular file')
    if path.stat().st_size > limit:
        raise ValueError('treasury evidence must be a bounded regular file')
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError('treasury evidence must be a bounded regular file')
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('treasury evidence hash mismatch')
    return raw


def _no_symlink_component(root: Path, rel: str) -> None:
    """A retained series may not be reached through a symlinked parent."""
    current = root
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('treasury evidence must not traverse a symlink')


def _decimal(value: object) -> Decimal:
    """One finite, non-boolean, numeric reading as an exact decimal."""
    if isinstance(value, bool):
        raise ValueError('treasury values must be numeric')
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('treasury values must be finite')
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('treasury values must be finite')
        return Decimal(str(value))
    raise ValueError('treasury values must be numeric')


def _column(frame: object, spec: Series) -> tuple[list[Decimal], object]:
    """Validate the retained table shape and return its values and index."""
    import pandas as pd

    if not isinstance(frame, pd.DataFrame) or len(frame.columns) != 1:
        raise ValueError('treasury artifact schema mismatch')
    column = frame.columns[0]
    if not isinstance(column, str) or column != spec.column:
        raise ValueError('treasury artifact schema mismatch')
    index = frame.index
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError('treasury index must be a datetime index')
    if index.tz is not None:
        raise ValueError('treasury index must not carry a timezone')
    if index.has_duplicates:
        raise ValueError('treasury index has duplicate dates')
    if not index.is_monotonic_increasing:
        raise ValueError('treasury index is not sorted')
    if not bool((index == index.normalize()).all()):
        raise ValueError('treasury index must be midnight-aligned')
    return [_decimal(value) for value in frame[column].tolist()], index


def read_value(rel: str, *, path: Path, digest: str, observation_date: str) -> Decimal:
    """The stored value of one retained series on one exact observation date."""
    import pandas as pd

    spec = SERIES[rel]
    if not isinstance(observation_date, str) or not _ISO_DATE.fullmatch(observation_date):
        raise ValueError('treasury observation date must be an ISO calendar date')
    try:
        date.fromisoformat(observation_date)
    except ValueError as exc:
        raise ValueError('treasury observation date must be an ISO calendar date') from exc
    raw = _read_bound(path, digest)
    try:
        frame = pd.read_parquet(io.BytesIO(raw))
    except Exception as exc:
        raise ValueError('treasury artifact is malformed') from exc
    values, index = _column(frame, spec)
    moment = pd.Timestamp(observation_date)
    positions = (index == moment).nonzero()[0]
    if len(positions) != 1:
        raise ValueError('treasury series has no exact row for the requested observation date')
    return values[int(positions[0])]


def reviewed_fact(rel: str, *, fact_id: str, path: Path, digest: str,
                  observation_date: str | None, root: Path) -> tuple[dict, Decimal]:
    """The reviewed fact and the stored value for one retained series."""
    spec = SERIES[rel]
    if fact_id != spec.fact_id:
        raise ValueError('unknown treasury fact id')
    if observation_date is None:
        raise ValueError('treasury context requires an explicit observation date')
    _no_symlink_component(root, rel)
    value = read_value(rel, path=path, digest=digest, observation_date=observation_date)
    return build_fact(rel, fact_id=fact_id, value=value,
                       observation_date=observation_date), value


def build_fact(rel: str, *, fact_id: str, value: Decimal, observation_date: str) -> dict:
    """The reviewed fact for one retained series on the requested date."""
    from engine.press import desk_planner as planner

    spec = SERIES[rel]
    if fact_id != spec.fact_id:
        raise ValueError('unknown treasury fact id')
    reading = format(value, 'f')
    text = (f'Retained FRED series {spec.series} ({spec.label}) reads {reading} '
            f'{spec.unit} for observation date {observation_date}.')
    fact = planner._fact(
        spec.fact_id, text, ref=f'artifact:{rel}', tier='first_party',
        values=[reading], source_name=f'FRED series {spec.series} ({spec.label})',
        dated=observation_date)
    # The series, the artifact and the observation date are the whole
    # provenance of this reading.  There is no release clock and no first-known
    # date to record, because the retained bytes carry neither.
    fact['source_series'] = spec.series
    fact['source_artifact'] = rel
    fact['observation_date'] = observation_date
    fact['unit'] = spec.unit
    fact['source_provenance'] = {
        'schema': 'press.retained_treasury_provenance.v1',
        'observation': {'state': 'present', 'date': observation_date, 'precision': 'day'},
        'publication_time': {'state': 'unavailable', 'value': None,
                             'reason': 'not_recorded_in_retained_series'},
        'first_known_time': {'state': 'unavailable', 'value': None,
                             'reason': 'no_per_observation_ingestion_receipt'},
        'vintage': {'state': 'unavailable', 'value': None,
                    'reason': 'retained_snapshot_not_a_point_in_time_vintage'},
        'rights_admission': 'not_granted_by_extraction',
    }
    derived = DERIVED.get(spec.fact_id)
    if derived is not None:
        # A derived series is the same measurement expressed another way, not
        # a second source standing behind it.
        fact['derived_from'] = list(derived)
    return fact


def verify_identity(selected: dict[str, Decimal]) -> None:
    """Refuse a derived series whose stored identity does not hold.

    ``selected`` maps the fact id of every selected Treasury series to the
    value read for the requested observation date.
    """
    for derived_id, (left_id, right_id) in DERIVED.items():
        if derived_id not in selected:
            continue
        missing = [fact_id for fact_id in (left_id, right_id) if fact_id not in selected]
        if missing:
            raise ValueError('derived treasury series requires its selected dependencies')
        if selected[left_id] - selected[right_id] != selected[derived_id]:
            raise ValueError('derived treasury series does not match its stored identity')
