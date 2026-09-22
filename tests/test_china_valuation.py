from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from collectors import china_valuation as cv


class _Response:
    def __init__(self, body: list[list[object]]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "Result": [{
                "DisplayData": {
                    "resultData": {
                        "tplData": {
                            "result": {"chartInfo": [{"body": self._body}]}
                        }
                    }
                }
            }]
        }


def test_band_sets_an_explicit_transport_timeout(monkeypatch) -> None:
    seen: dict[str, object] = {}
    body = [[f"2026-01-{(i % 28) + 1:02d}", i + 1] for i in range(60)]

    def fake_get(url: str, *, params: dict, timeout: float):
        seen.update(url=url, params=params, timeout=timeout)
        return _Response(body)

    monkeypatch.setattr(cv.requests, "get", fake_get)
    result = cv._band("600519", "市盈率(TTM)", timeout=1.25)

    assert seen["url"] == cv.BAIDU_VALUATION_URL
    assert seen["timeout"] == 1.25
    assert seen["params"]["code"] == "600519"
    assert result == {"v": 60.0, "pctile": 100.0, "lo": 1.0, "hi": 60.0, "n": 60}


def test_band_turns_transport_timeout_into_missing_optional_context(monkeypatch) -> None:
    def fail_get(*args, **kwargs):
        raise requests.Timeout("provider stalled")

    monkeypatch.setattr(cv.requests, "get", fail_get)
    assert cv._band("600519", "市盈率(TTM)", timeout=0.1) is None


def test_refresh_stops_at_wall_clock_budget(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cv, "OUT", tmp_path / "china_valuation" / "percentiles.parquet")
    monkeypatch.setattr(cv, "_universe", lambda limit: ["A.SS", "B.SS", "C.SS"])
    calls: list[tuple[str, float]] = []

    def fake_fetch(ticker: str, *, timeout: float):
        calls.append((ticker, timeout))
        return None

    ticks = iter([100.0, 100.0, 104.0])
    monkeypatch.setattr(cv, "fetch_one", fake_fetch)
    monkeypatch.setattr(cv.time, "monotonic", lambda: next(ticks))

    assert cv.refresh(max_new=3, max_runtime_seconds=3.0) == 0
    assert calls == [("A.SS", 1.0)]
