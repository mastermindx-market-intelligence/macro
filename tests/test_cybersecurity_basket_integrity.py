"""Canonical composition contract for the US cybersecurity monitoring basket.

The basket is the cybersecurity-focused signal/breadth universe. Diversified platform vendors may
appear in product-exposure heatmaps, but they must not silently enter this core basket.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMBERSHIP = ROOT / "data" / "baskets" / "membership.json"

CORE = {
    "CRWD",
    "PANW",
    "FTNT",
    "OKTA",
    "QLYS",
    "ZS",
    "S",
    "NET",
    "RBRK",
    "TENB",
    "CHKP",
    "SAIL",
    "VRNS",
    "NTSK",
}

ADJACENT_DIVERSIFIED = {"MSFT", "CSCO", "IBM", "GOOGL", "AMZN", "AVGO"}

NEW_MEMBER_STAMPS = {
    "CHKP": "2023-05-09",
    "VRNS": "2023-05-09",
    "SAIL": "2025-02-13",
    "NTSK": "2025-09-18",
}


def _basket() -> dict:
    doc = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    return doc["baskets"]["cybersecurity"]


def test_cybersecurity_core_is_complete_and_pure_play() -> None:
    basket = _basket()
    active = {m["ticker"] for m in basket["members"] if m.get("removed") is None}

    assert active == CORE
    assert active.isdisjoint(ADJACENT_DIVERSIFIED)
    assert basket["weighting"] == "equal"
    assert basket["etf_proxy"] == "CIBR"


def test_cybersecurity_2026_expansion_is_point_in_time_honest() -> None:
    basket = _basket()
    members = {m["ticker"]: m for m in basket["members"]}

    for ticker, added in NEW_MEMBER_STAMPS.items():
        member = members[ticker]
        assert member["added"] == added
        assert member["curated_added"] == "2026-09-23"
        assert member["removed"] is None
        assert member["rationale"].strip()

    thesis = " ".join(
        [basket.get("theme", ""), basket.get("thesis", "")]
        + [members[t]["rationale"] for t in NEW_MEMBER_STAMPS]
    ).lower()
    for capability in ("network", "identity", "data security", "sase"):
        assert capability in thesis


def test_cybersecurity_new_members_have_preferred_deep_ohlcv() -> None:
    import pandas as pd

    deep = ROOT / "data" / "baskets" / "ohlcv"
    missing = [ticker for ticker in NEW_MEMBER_STAMPS if not (deep / f"{ticker}.parquet").exists()]
    assert not missing, f"new cybersecurity members are absent from the preferred OHLCV store: {missing}"

    acceptance_session = pd.Timestamp("2026-09-23")
    required_columns = {"open", "high", "low", "close", "volume"}
    for ticker, added in NEW_MEMBER_STAMPS.items():
        frame = pd.read_parquet(deep / f"{ticker}.parquet")
        index = pd.DatetimeIndex(pd.to_datetime(frame.index))

        assert required_columns.issubset(frame.columns), (ticker, sorted(frame.columns))
        assert index.is_unique, f"{ticker} deep OHLCV has duplicate sessions"
        assert index.is_monotonic_increasing, f"{ticker} deep OHLCV is not session-sorted"
        assert index.min() <= pd.Timestamp(added), f"{ticker} starts after its PIT added date"
        assert index.max() == acceptance_session, f"{ticker} is stale or future-dated"
        assert not frame[list(required_columns)].isna().any().any(), f"{ticker} has null OHLCV"

        numeric = frame[list(required_columns)].apply(pd.to_numeric, errors="coerce")
        assert not numeric.isna().any().any(), f"{ticker} has non-numeric OHLCV"
        assert (numeric[["open", "high", "low", "close"]] > 0).all().all()
        assert (numeric["volume"] >= 0).all()
        assert (numeric["high"] >= numeric[["open", "close", "low"]].max(axis=1)).all()
        assert (numeric["low"] <= numeric[["open", "close", "high"]].min(axis=1)).all()


def test_cybersecurity_core_is_current_on_the_canonical_close_panel() -> None:
    import pandas as pd

    extras = pd.read_parquet(ROOT / "data" / "baskets" / "extras.parquet")
    required = {"CHKP", "SAIL", "VRNS", "NTSK", "OKTA", "QLYS"}
    missing = sorted(required - set(extras.columns))
    stale = {
        ticker: str(pd.to_datetime(extras[ticker].dropna().index.max()).date())
        for ticker in required & set(extras.columns)
        if pd.to_datetime(extras[ticker].dropna().index.max()) < pd.Timestamp("2026-09-23")
    }
    assert not missing, f"canonical baskets/extras panel is missing cybersecurity members: {missing}"
    assert not stale, f"canonical cybersecurity close columns are stale at the acceptance session: {stale}"


def test_generated_cybersecurity_detail_projects_the_complete_core() -> None:
    page = ROOT / "site" / "basket" / "cybersecurity.html"
    line = next(
        row for row in page.read_text(encoding="utf-8").splitlines()
        if row.startswith("const DETAIL = ")
    )
    detail = json.loads(line[len("const DETAIL = ") : -1])
    members = detail["members"]
    symbols = {member["symbol"] for member in members}
    uncovered = {member["symbol"] for member in members if not member.get("conviction")}
    observation = detail["basket"]["observation"]

    assert symbols == CORE
    assert symbols.isdisjoint(ADJACENT_DIVERSIFIED)
    assert detail["basket"]["n_members"] == 14
    assert observation["status"] == "complete"
    assert observation["coverage"] == 1.0
    assert uncovered == {"SAIL", "NTSK"}
