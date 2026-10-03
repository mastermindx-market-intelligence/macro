"""Tests for the backward-compatible regionalization of engine.group_flow._setup."""
import pandas as pd
import pytest

from engine import group_flow


def test_region_aliases():
    a = group_flow._REGION_ALIASES
    assert a["us"] == "us" and a["usa"] == "us"
    assert a["china"] == "cn" and a["cn"] == "cn"
    assert a["hongkong"] == "hk" and a["hk"] == "hk"
    assert a["canada"] == "ca" and a["ca"] == "ca"


def test_setup_default_is_us():
    """No-arg _setup() stays US (backward compatible) and carries the expected contract."""
    s = group_flow._setup()
    if s is None:
        pytest.skip("no US baskets cache present")
    assert set(["mem", "closes", "rets", "idx", "bench", "region"]).issubset(s.keys())
    assert s["region"] == "us"
    assert not s["closes"].empty
    assert s["bench"].dropna().shape[0] > 0


def test_unknown_region_falls_back_to_us():
    s = group_flow._setup("atlantis")
    if s is None:
        pytest.skip("no US baskets cache present")
    assert s["region"] == "us"


@pytest.mark.parametrize("region", ["cn", "hk", "ca"])
def test_setup_regional(region):
    s = group_flow._setup(region)
    if s is None:
        pytest.skip(f"no {region} baskets cache present")
    assert s["region"] == region
    assert not s["closes"].empty
    assert s["mem"].get("baskets")
    assert s["bench"].dropna().shape[0] > 0


def test_setup_regional_refuses_without_exact_common_benchmark_session(monkeypatch):
    panel_idx = pd.bdate_range("2025-01-02", periods=5)
    benchmark_idx = pd.bdate_range("2025-02-03", periods=5)
    closes = pd.DataFrame({"AAA": range(5), "BBB": range(5), "CCC": range(5)}, index=panel_idx)
    benchmark = pd.DataFrame({"close": range(100, 105)}, index=benchmark_idx)
    membership = {"baskets": {"test": {"members": []}}, "benchmark": "TEST"}

    monkeypatch.setattr(
        group_flow,
        "_region_plane",
        lambda region: (lambda: membership, lambda: closes, "regional", "TEST"),
    )
    monkeypatch.setattr(
        group_flow.store,
        "read",
        lambda group, name: benchmark if (group, name) == ("regional", "TEST") else None,
    )

    assert group_flow._setup("cn") is None
