"""Exact-date native ON RRP measurement for the reviewed market consumer.

One retained observation earns one fact. No history expansion, unit aliases,
inferred counterparty/rate facts, producer, rights grant or writer admission.
The existing Treasury consumer's bounded parquet validation is reused unchanged.
"""
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

from engine.press import treasury_context as retained

ARTIFACT = 'data/fred/RRPONTSYD.parquet'
FACT_ID = 'overnight_rrp_amount'
SPEC = retained.Series(FACT_ID, 'RRPONTSYD', 'on_rrp',
                       'overnight reverse repurchase agreements',
                       'billions of US dollars')


def reviewed_fact(*, fact_id: str, path: Path, digest: str,
                  observation_date: str | None, root: Path) -> dict:
    """Read one hash-bound, exact observation; never substitute the latest row."""
    import pandas as pd
    from engine.press import desk_planner as planner

    if fact_id != FACT_ID:
        raise ValueError('unknown RRP fact id')
    if (not isinstance(observation_date, str)
            or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', observation_date)):
        raise ValueError('RRP context requires an explicit ISO observation date')
    date.fromisoformat(observation_date)
    retained._no_symlink_component(root, ARTIFACT)
    raw = retained._read_bound(path, digest)
    try:
        frame = pd.read_parquet(io.BytesIO(raw))
    except Exception as exc:
        raise ValueError('RRP artifact is malformed') from exc
    values, index = retained._column(frame, SPEC)
    positions = (index == pd.Timestamp(observation_date)).nonzero()[0]
    if len(positions) != 1:
        raise ValueError('RRP series has no exact row for the requested observation date')
    value = values[int(positions[0])]
    if value < 0:
        raise ValueError('RRP operation amount must not be negative')
    reading = format(value, 'f')
    text = (f'Retained FRED series RRPONTSYD reports overnight reverse-repo usage '
            f'of {reading} billion US dollars for observation date {observation_date}.')
    fact = planner._fact(FACT_ID, text, ref=f'artifact:{ARTIFACT}',
                         tier='first_party', values=[reading],
                         source_name='Federal Reserve Bank of New York via FRED (RRPONTSYD)',
                         dated=observation_date)
    # first_party identifies our extraction, not ownership of the underlying data.
    fact.update(source_series=SPEC.series, source_artifact=ARTIFACT,
                observation_date=observation_date, unit=SPEC.unit,
                source_url='https://fred.stlouisfed.org/series/RRPONTSYD',
                source_provenance={
                    'schema': 'press.retained_rrp_provenance.v1',
                    'observation': {'state': 'present', 'date': observation_date, 'precision': 'day'},
                    'publication_time': {'state': 'unavailable', 'value': None,
                                         'reason': 'not_recorded_in_retained_series'},
                    'first_known_time': {'state': 'unavailable', 'value': None,
                                         'reason': 'no_per_observation_ingestion_receipt'},
                    'vintage': {'state': 'unavailable', 'value': None,
                                'reason': 'retained_snapshot_not_a_point_in_time_vintage'},
                    'rights_admission': 'not_granted_by_extraction',
                })
    return fact
