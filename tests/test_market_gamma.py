"""Tests for scripts.build_site.market_gamma_view — the market dealer-gamma vol-regime
note derived from the validated index GEX store. Pure/deterministic; the regime is
the engine direct-sign gamma_regime on the same-session cboe/gex_SPX row, not
spot vs flip."""
import numpy as np
import pandas as pd

from engine import market_gamma
from scripts.build_site import market_gamma_view


def _gex(net_gex_bn, flip, spot, spot_vs_flip_pct):
    return pd.DataFrame(
        {"net_gex_bn": [net_gex_bn], "flip_strike": [flip], "spot": [spot],
         "spot_vs_flip_pct": [spot_vs_flip_pct]},
        index=pd.to_datetime(["2026-06-13"]))


def _engine(gamma_regime, asof="2026-06-13"):
    """Same-session engine row. These fixtures keep the regime they always
    asserted; the value now has to be supplied, because view() no longer
    derives it from the flip side."""
    return pd.DataFrame(
        {"gamma_regime": [gamma_regime]},
        index=pd.to_datetime([asof]),
    )


def test_injected_engine_short_below_flip():
    v = market_gamma_view(_gex(17.7, 8100, 7394.3, -8.71), gex_spx=_engine("short"))
    assert v["regime"] == "short"                  # engine direct sign, spot below flip
    assert v["spot_vs_flip_pct"] == -8.7
    assert v["flip"] == 8100 and v["spot"] == 7394
    assert v["net_gex_bn"] == 18                    # rounded
    assert v["asof"] == "2026-06-13"
    # contract aliases co-located with the FE key, all the same value (FE uses `flip`,
    # the contract/downstream bot reads `gamma_flip` / `flip_strike`)
    assert v["gamma_flip"] == 8100 and v["flip_strike"] == 8100


def test_injected_engine_long_above_flip():
    v = market_gamma_view(_gex(25.0, 5000, 5150.0, 3.0), gex_spx=_engine("long"))
    assert v["regime"] == "long"                    # engine direct sign, spot above flip


def test_at_flip_follows_injected_engine_sign():
    # spot exactly at flip (0%). The engine row says long; view does not invent it.
    assert market_gamma_view(_gex(1.0, 5000, 5000.0, 0.0), gex_spx=_engine("long"))["regime"] == "long"


def test_engine_sign_not_net_sign():
    # net_gex POSITIVE. Regime is SHORT because the engine row says short
    # (this book's flip side), not "long" off the net-$ sign.
    assert market_gamma_view(_gex(50.0, 8100, 7400.0, -8.6), gex_spx=_engine("short"))["regime"] == "short"


def test_none_and_empty_and_nan_are_graceful():
    assert market_gamma_view(None, gex_spx=None) is None
    assert market_gamma_view(pd.DataFrame(), gex_spx=None) is None
    assert market_gamma_view(_gex(10.0, 5000, 5000.0, np.nan), gex_spx=None) is None


# 2026-06-11 and 2026-06-12 are NYSE sessions (Thursday, Friday). The session
# filter must keep these rows; a weekend date would fail-open and hide a miss.
_SESSION = "2026-06-12"
_OTHER_SESSION = "2026-06-11"


def _engine_row(gamma_regime, asof=_SESSION):
    return pd.DataFrame(
        {"gamma_regime": [gamma_regime]},
        index=pd.to_datetime([asof]),
    )


def test_regime_uses_engine_direct_sign_not_flip_side():
    """Spot below the flip (svf < 0) while the same-session engine row is long.
    Regime follows the engine direct sign, not spot_vs_flip_pct."""
    gex = _gex(17.7, 8100, 7394.3, -1.2)
    gex.index = pd.to_datetime([_SESSION])
    v = market_gamma_view(gex, gex_spx=_engine_row("long"))
    assert v["regime"] == "long"
    assert v["regime_basis"] == "engine_direct_sign"


def test_regime_mirror_engine_short_above_flip():
    """Mirror: spot above the flip while the engine row is short."""
    gex = _gex(25.0, 5000, 5150.0, 1.0)
    gex.index = pd.to_datetime([_SESSION])
    v = market_gamma_view(gex, gex_spx=_engine_row("short"))
    assert v["regime"] == "short"
    assert v["regime_basis"] == "engine_direct_sign"


def test_regime_unavailable_when_engine_row_missing():
    gex = _gex(17.7, 8100, 7394.3, -1.2)
    gex.index = pd.to_datetime([_SESSION])
    v = market_gamma_view(gex, gex_spx=None)
    assert v is not None
    assert v["regime"] is None
    assert v["regime_basis"] == "unavailable"


def test_regime_unavailable_on_session_date_mismatch():
    gex = _gex(17.7, 8100, 7394.3, -1.2)
    gex.index = pd.to_datetime([_SESSION])
    v = market_gamma_view(gex, gex_spx=_engine_row("long", asof=_OTHER_SESSION))
    assert v is not None
    assert v["regime"] is None
    assert v["regime_basis"] == "unavailable"


def test_regime_unavailable_when_engine_value_is_null():
    gex = _gex(17.7, 8100, 7394.3, -1.2)
    gex.index = pd.to_datetime([_SESSION])
    for raw in (None, np.nan):
        v = market_gamma_view(gex, gex_spx=_engine_row(raw))
        assert v is not None
        assert v["regime"] is None
        assert v["regime_basis"] == "unavailable"


def test_regime_unchanged_when_engine_agrees_with_flip_side():
    """Control: engine sign and flip side agree. Pre-existing keys keep the
    values the flip-side deriver published; only regime_basis is added."""
    gex = _gex(17.7, 8100, 7394.3, -1.2)
    gex.index = pd.to_datetime([_SESSION])
    v = market_gamma_view(gex, gex_spx=_engine_row("short"))
    assert v["regime"] == "short"
    assert v["regime_basis"] == "engine_direct_sign"
    assert v["spot_vs_flip_pct"] == -1.2
    assert v["net_gex_bn"] == 18
    assert v["flip"] == 8100
    assert v["gamma_flip"] == 8100
    assert v["flip_strike"] == 8100
    assert v["spot"] == 7394
    assert v["asof"] == _SESSION
    assert set(v) == {
        "regime", "regime_basis", "spot_vs_flip_pct", "net_gex_bn",
        "flip", "gamma_flip", "flip_strike", "spot", "asof",
    }


# M01 repair 1: production one-argument view() path

def test_default_path_reads_gex_spx_and_uses_engine_sign(monkeypatch):
    """One-argument view() reads cboe/gex_SPX and uses that sign.

    Spot is below the flip (spot_vs_flip_pct -9.63). The retired flip-side
    rule would call this short; the engine row says long.
    """
    calls = []

    def _read(group, name):
        calls.append((group, name))
        if (group, name) == ("cboe", "gex_SPX"):
            return pd.DataFrame(
                {"gamma_regime": ["long"]},
                index=pd.to_datetime(["2026-06-13"]),
            )
        return None

    monkeypatch.setattr(market_gamma.store, "read", _read)
    v = market_gamma.view(_gex(6.8, 8300, 7500.58, -9.63))
    assert v["regime"] == "long"
    assert v["regime_basis"] == "engine_direct_sign"
    assert ("cboe", "gex_SPX") in calls


def test_default_path_absent_gex_spx_yields_no_regime(monkeypatch):
    """A missing cboe/gex_SPX row leaves regime unset. Flip, spot and net GEX stay."""
    def _read(group, name):
        if (group, name) == ("cboe", "gex_SPX"):
            return None
        return None

    monkeypatch.setattr(market_gamma.store, "read", _read)
    v = market_gamma.view(_gex(6.8, 8300, 7500.58, -9.63))
    assert v["regime"] is None
    assert v["regime_basis"] == "unavailable"
    assert v["gamma_flip"] is not None
    assert v["spot"] is not None
    assert v["net_gex_bn"] is not None


def test_default_path_raising_gex_spx_read_is_unavailable(monkeypatch):
    """A raising cboe/gex_SPX read must not escape view(); regime stays unavailable."""
    def _read(group, name):
        if (group, name) == ("cboe", "gex_SPX"):
            raise RuntimeError("store down")
        return None

    monkeypatch.setattr(market_gamma.store, "read", _read)
    v = market_gamma.view(_gex(6.8, 8300, 7500.58, -9.63))
    assert v["regime"] is None
    assert v["regime_basis"] == "unavailable"
    assert v["gamma_flip"] is not None
    assert v["spot"] is not None
    assert v["net_gex_bn"] is not None
