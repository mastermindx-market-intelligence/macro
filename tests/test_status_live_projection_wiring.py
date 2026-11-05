"""/api/status must publish the live source clocks THROUGH the shared projection.

WHY (D04-A2, 2026-10): ``scripts/check_vps_live_health.py::evaluate`` fails weekday
15-19Z when ``checks.flow_pulse.source_asof`` or ``checks.intraday_quotes.source_asof``
is missing, invalid or stale. ``app/live_status_projection.py`` is the ONE mapping from
the two live payloads onto those rows; ``app.main.status()`` must route both artifacts
through it, or the dead-man and the status surface grade different clocks.

Division of labour (two jobs, one law):
  * ``tests/test_vps_live_orchestration.py`` pins producer -> projection (the real
    fastpath pulse via ``_run_fastpath``, the real board via ``build_payload``) and runs
    in ``washout-turn-organ``, which installs no fastapi.
  * THIS suite pins route -> projection against the mounted app and therefore runs in
    a fastapi job (``prelaunch-hardening``, the public-API contract lane). It must not
    be replaced by an AST read of ``app/main.py``: ``scripts/ci_scope_dependencies.py``
    records a ``__file__``-rooted join of ``app/main.py`` as a code read and drags the
    whole serving closure into the reading job's scope (macro#10004 contract-delta).

The board below is the real producer's output (``scripts/build_intraday_flow_quotes``
is stdlib-only). The pulse carries the ``flow_pulse.v1`` keys the fastpath producer
writes; the producer itself needs jinja2 and the page stack, which this job does not
install, and its composition with the projection is already pinned upstream.

Offline: TestClient against the mounted app; ``_live_artifact`` redirected to tmp_path.
Mutation falsifier: drop the ``("intraday_quotes", "intraday_quotes.json")`` tuple from
``app.main.status()`` -> ``test_status_publishes_both_source_clocks_through_the_projection``
fails on ``checks["intraday_quotes"]``.

Run:
    python -m pytest tests/test_status_live_projection_wiring.py -v
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.live_status_projection import flow_pulse_fields, intraday_quotes_fields
from scripts.build_intraday_flow_quotes import build_payload


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _epoch_ms(stamp: datetime) -> int:
    return int(stamp.timestamp() * 1000)


def _pulse(now: datetime, *, source_age_min: int = 40, bars: tuple[int, ...] = (2, 0, 3)) -> dict:
    """A ``flow_pulse.v1`` payload with the keys ``scripts/build_intraday_flow._run_fastpath`` writes."""
    tickers = [{"ticker": f"T{i}", "bars_today": n} for i, n in enumerate(bars)]
    return {
        "schema": "flow_pulse.v1",
        "as_of": now.isoformat(),
        "as_of_ms": _epoch_ms(now),
        "mode": "fastpath" if any(bars) else "no_data",
        "stale": False,
        "n_tickers": len(tickers),
        "n_universe": 5,
        "source_asof": (now - timedelta(minutes=source_age_min)).isoformat(),
        "tickers": tickers,
    }


def _board(now: datetime, *, with_clocks: bool = True) -> dict:
    """The real board builder: three leaders requested, two priced (coverage 2/3)."""
    leaders = [{"ticker": name} for name in ("AAA", "BBB", "CCC")]
    quotes = {"AAA": {"price": 10.0}, "BBB": {"price": 11.0}}
    if with_clocks:
        for quote in quotes.values():
            quote["ts"] = _epoch_ms(now - timedelta(minutes=20))
    return build_payload({"leaders": leaders}, {"quotes": quotes, "meta": {}})


def _serve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, artifacts: dict[str, dict]) -> None:
    import app.main as main

    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(main, "_live_artifact", lambda name: tmp_path / name)


def test_status_publishes_both_source_clocks_through_the_projection(client, tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    pulse, board = _pulse(now), _board(now)
    _serve(monkeypatch, tmp_path, {"flow_pulse.json": pulse, "intraday_quotes.json": board})

    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    checks = body["checks"]
    flow_pulse, intraday_quotes = checks["flow_pulse"], checks["intraday_quotes"]

    # Route == projection, field for field: the rows the dead-man reads are exactly
    # what the shared module derives from the artifacts the route served.
    expected_pulse = flow_pulse_fields(pulse)
    expected_board = intraday_quotes_fields(board)
    assert {key: flow_pulse[key] for key in expected_pulse} == expected_pulse
    assert {key: intraday_quotes[key] for key in expected_board} == expected_board

    # The values are the producers' clocks and counts, untouched.
    assert flow_pulse["source_asof"] == pulse["source_asof"]
    assert flow_pulse["n_universe"] == 5
    assert flow_pulse["with_bars"] == 2
    assert flow_pulse["mode"] == "fastpath"
    assert intraday_quotes["requested"] == 3
    assert intraday_quotes["resolved"] == 2
    assert intraday_quotes["coverage"] == pytest.approx(2 / 3, abs=1e-6)
    assert intraday_quotes["source_asof"] == board["meta"]["source_asof"]
    assert intraday_quotes["source_asof"] is not None
    assert intraday_quotes["built_at"] == board["meta"]["built_at"]

    # The generic artifact row the monitor already consumed survives on both rows.
    for row in (flow_pulse, intraday_quotes):
        assert "age_min" in row and "built" in row and "schema" in row
    assert flow_pulse["schema"] == "flow_pulse.v1"

    # Pulse before board: evaluate() reports the clocks in this order.
    keys = list(checks)
    assert keys.index("flow_pulse") < keys.index("intraday_quotes")


def test_missing_clock_is_null_not_zero_and_absent_artifact_is_not_a_clock(client, tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _serve(monkeypatch, tmp_path, {"intraday_quotes.json": _board(now, with_clocks=False)})

    checks = client.get("/api/status").json()["checks"]

    # No pulse artifact -> the row says missing and carries no clock at all; the
    # dead-man reports that absence itself. Nothing fabricates a source_asof.
    assert checks["flow_pulse"] == {"status": "missing"}

    # A board whose quotes carry no observed clock projects source_asof=None —
    # missing is not zero and not an empty string.
    intraday_quotes = checks["intraday_quotes"]
    assert intraday_quotes["resolved"] == 2
    assert intraday_quotes["source_asof"] is None
    assert "source_asof" in intraday_quotes
