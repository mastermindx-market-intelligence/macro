"""Non-finite producer numbers must drop the field, not the nomination pass."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.entry_radar.contracts import Nomination, NominationError, ProducerRead
from engine.entry_radar.nomination_bus import NominationBus
from engine.entry_radar.producers.base import finite_or_none
from engine.entry_radar.producers import read_flow_pulse, read_us_standouts
from engine.entry_radar.spool import NominationSpool
from engine.entry_radar.universe import load_config

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
YESTERDAY = NOW - timedelta(days=1)
ASOF = "2026-08-14T02:10:00Z"


def _cfg():
    return load_config(ROOT)


def _nomination(**kw) -> Nomination:
    base = dict(
        ticker="ZZTOP",
        source_id="basketdata:linked_outsiders",
        source_family="special_situation",
        reason_code="filing.linked_counterparty",
        reason_text="ZZTOP named as a counterparty in a material 8-K",
        observed_at=NOW,
        source_asof=YESTERDAY,
        source_rank=3,
        source_value=1.0,
        source_horizon="event",
        ttl_until=NOW + timedelta(hours=36),
        evidence_ref="linked_outsiders.json#semis/ZZTOP",
        data_quality="ok",
    )
    base.update(kw)
    return Nomination(**base)


def _standouts_doc():
    return {
        "as_of": ASOF,
        "rank_by": "eq",
        "buy": [
            {
                "ticker": "NVDA",
                "name": "NVIDIA",
                "alpha": 2.31,
                "state": "go",
                "label": "Buy",
                "score_rank": 1,
            }
        ],
        "watch": [],
        "leaders": [],
        "laggards": [],
    }


def _reject_nonstandard_constants(_value: str) -> None:
    raise ValueError("non-standard json constant")


def test_finite_or_none():
    assert finite_or_none(None) is None
    assert finite_or_none(True) is None
    assert finite_or_none("x") is None
    assert finite_or_none(float("nan")) is None
    assert finite_or_none(float("inf")) is None
    assert finite_or_none(float("-inf")) is None
    assert finite_or_none(3) == 3.0
    assert finite_or_none("2.5") == 2.5
    import numpy as np

    assert finite_or_none(np.float64(1.5)) == 1.5


def test_nomination_refuses_non_finite_source_value():
    for bad in (float("nan"), float("inf"), "not-a-number"):
        with pytest.raises(NominationError, match="source_value"):
            _nomination(source_value=bad)


def test_nomination_refuses_non_finite_float_rank():
    with pytest.raises(NominationError, match="source_rank"):
        _nomination(source_rank=float("nan"))


def test_board_row_with_nan_value_keeps_the_nomination(tmp_path):
    doc = _standouts_doc()
    doc["buy"][0]["alpha"] = float("nan")
    path = tmp_path / "us_standouts.json"
    path.write_text(json.dumps(doc, allow_nan=True), encoding="utf-8")

    baseline = _standouts_doc()
    baseline["buy"][0]["alpha"] = 2.31
    base_path = tmp_path / "baseline.json"
    base_path.write_text(json.dumps(baseline), encoding="utf-8")

    nan_read = read_us_standouts(path, now=NOW, cfg=_cfg())
    ok_read = read_us_standouts(base_path, now=NOW, cfg=_cfg())
    assert len(nan_read.nominations) == len(ok_read.nominations) == 1
    assert nan_read.nominations[0].source_value is None
    assert ok_read.nominations[0].source_value == 2.31


def test_flow_pulse_row_with_nan_rvol_keeps_the_nomination(tmp_path):
    path = tmp_path / "flow_pulse.json"
    path.write_text(
        json.dumps(
            {
                "schema": "flow_pulse.v1",
                "as_of": "2026-08-14T14:00:00Z",
                "stale": False,
                "tickers": [{"ticker": "ZZTOP", "rvol_tod": float("nan")}],
            },
            allow_nan=True,
        ),
        encoding="utf-8",
    )
    got = read_flow_pulse(path, now=NOW, cfg=_cfg())
    assert len(got.read.nominations) == 1
    assert got.read.nominations[0].source_value is None


def test_spool_accepts_a_pass_that_had_a_nan_row(tmp_path):
    doc = _standouts_doc()
    doc["buy"][0]["alpha"] = float("nan")
    path = tmp_path / "us_standouts.json"
    path.write_text(json.dumps(doc, allow_nan=True), encoding="utf-8")
    read = read_us_standouts(path, now=NOW, cfg=_cfg())

    spool = NominationSpool(local_dir=tmp_path, prefix="t")
    bus = NominationBus(spool=spool)
    assert bus.ingest_read(read, now=NOW) == 1
    assert bus.spool_keys
    blob = (tmp_path / bus.spool_keys[0]).read_text(encoding="utf-8")
    json.loads(blob, parse_constant=_reject_nonstandard_constants)
    payload = json.loads(blob)
    assert payload["n_nominations"] == 1
