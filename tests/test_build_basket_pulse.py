"""Unit tests for scripts/build_basket_pulse.py — FTR W2b/c.

Tests use entirely synthetic quotes + membership fixtures; no network calls,
no data/ reads (except cum_2d which uses a monkeypatched parquet).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import build_basket_pulse as bp


# ── shared helpers ─────────────────────────────────────────────────────────────

def _now_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _make_quote(chg: float, age_min: float = 1.0, prev: float = 100.0,
                now: datetime | None = None, delay_min: float | None = None) -> dict:
    """Synthesise a Worker-contract quote dict.

    delay_min: explicit data-provider delay (mirrors the delayMin field that the
    real quotes worker writes). If None, defaults to age_min so that the synthetic
    quote's apparent staleness matches the intended test scenario.
    build_basket_pulse uses source age with delayMin as a nonnegative floor.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ts_ms = int(now.timestamp() * 1000) - int(age_min * 60_000)
    price = prev * (1 + chg / 100)
    return {
        "price": round(price, 4),
        "ts": ts_ms,
        "source": "test",
        "basis": "regular",
        "prevClose": prev,
        "changePct": round(chg, 4),
        "currency": "USD",
        "delayMin": delay_min if delay_min is not None else age_min,
    }


def _make_quotes(tickers_chg: dict[str, float], now: datetime, age_min: float = 1.0) -> dict:
    """Build a quotes dict from {ticker: changePct}."""
    return {tk: _make_quote(chg, age_min=age_min, now=now)
            for tk, chg in tickers_chg.items()}


def _make_membership(baskets: dict[str, list[str]]) -> dict:
    """Build a minimal baskets dict from {id: [ticker, ...]}."""
    out = {}
    for bid, tickers in baskets.items():
        out[bid] = {
            "name": bid,
            "members": [{"ticker": t, "removed": None} for t in tickers],
        }
    return out


# ── session flag tests ─────────────────────────────────────────────────────────

class TestSessionFlag:
    """_et_session returns the correct session label."""

    def _utc(self, hour: int, minute: int = 0) -> datetime:
        """A Wednesday (trading day) in ET summer (UTC-4)."""
        # 2026-07-08 is a Wednesday
        return datetime(2026, 7, 8, hour, minute, tzinfo=timezone.utc)

    def test_premarket(self):
        # 11:00 UTC = 07:00 ET — premarket
        assert bp._et_session(self._utc(11, 0)) == "pre"

    def test_rth_open(self):
        # 13:30 UTC = 09:30 ET — RTH open
        assert bp._et_session(self._utc(13, 30)) == "rth"

    def test_rth_mid(self):
        # 17:00 UTC = 13:00 ET — mid-day RTH
        assert bp._et_session(self._utc(17, 0)) == "rth"

    def test_post_close(self):
        # 21:00 UTC = 17:00 ET — after-hours (post)
        # Note: 20:00 ET + is "closed"; 16:00–20:00 ET is "post"
        # 20:00 UTC = 16:00 ET = RTH close exact → post starts
        assert bp._et_session(self._utc(20, 1)) == "post"

    def test_closed_before_premarket(self):
        # 07:00 UTC = 03:00 ET — closed (before 04:00 ET premarket open)
        assert bp._et_session(self._utc(7, 0)) == "closed"

    def test_closed_after_afterhours(self):
        # 01:00 UTC = 21:00 ET prior day — closed
        assert bp._et_session(self._utc(1, 0)) == "closed"

    def test_weekend_is_closed(self):
        # 2026-07-11 is a Saturday
        sat = datetime(2026, 7, 11, 15, 0, tzinfo=timezone.utc)
        assert bp._et_session(sat) == "closed"


# ── EW computation tests ───────────────────────────────────────────────────────

class TestEwChg:
    """Equal-weight average computation + coverage rules."""

    def test_ew_math_basic(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = _make_quotes({"A": 2.0, "B": 4.0, "C": 6.0}, now)
        ew, n_q, n_m, stale = bp._ew_chg(["A", "B", "C"], qs, _now_ms(now))
        assert ew == pytest.approx(4.0, abs=0.01)
        assert n_q == 3 and n_m == 3 and stale is False

    def test_coverage_below_30pct_returns_null(self):
        """A basket with 16 members but only 4 quoted (25%) → null EW."""
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        tickers = [f"T{i:02d}" for i in range(16)]
        # Only 4 quoted
        qs = _make_quotes({t: 1.0 for t in tickers[:4]}, now)
        ew, n_q, n_m, _ = bp._ew_chg(tickers, qs, _now_ms(now))
        assert ew is None, "coverage 4/16=25% < 30% must return None"
        assert n_q == 4 and n_m == 16

    def test_stale_quotes_excluded_from_ew(self):
        """Quotes older than stale_min are excluded from the EW average."""
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        # 3 fresh quotes at +4%, 2 stale at +100% — stale should be excluded
        fresh = _make_quotes({"A": 4.0, "B": 4.0, "C": 4.0}, now, age_min=1.0)
        stale = _make_quotes({"D": 100.0, "E": 100.0}, now, age_min=25.0)
        qs = {**fresh, **stale}
        tickers = ["A", "B", "C", "D", "E"]
        ew, n_q, n_m, any_stale = bp._ew_chg(tickers, qs, _now_ms(now), stale_min=20)
        # EW uses only fresh quotes [4.0, 4.0, 4.0]
        assert ew == pytest.approx(4.0, abs=0.01)
        assert any_stale is True
        assert n_q == 5   # both stale and fresh are counted in n_quoted

    def test_no_quotes_returns_null(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        ew, n_q, n_m, _ = bp._ew_chg(["X", "Y", "Z"], {}, _now_ms(now))
        assert ew is None
        assert n_q == 0 and n_m == 3

    def test_coverage_exactly_at_30pct_threshold(self):
        """Exactly 30% coverage = at the boundary → should return a value."""
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        # 3 out of 10 = 30%
        tickers = [f"T{i}" for i in range(10)]
        qs = _make_quotes({t: 2.0 for t in tickers[:3]}, now)
        ew, _, _, _ = bp._ew_chg(tickers, qs, _now_ms(now))
        # Exactly 0.30 is not < 0.30 so it should compute
        assert ew is not None


# ── tape rank tests ────────────────────────────────────────────────────────────

class TestTapeRanks:
    """Cross-sectional rank: 1=weakest, N=strongest."""

    def test_rank_ordering(self):
        data = [
            {"id": "A", "live_ew_chg_pct": -1.0},
            {"id": "B", "live_ew_chg_pct": 0.5},
            {"id": "C", "live_ew_chg_pct": 2.0},
        ]
        ranks = bp._tape_ranks(data)
        assert ranks["A"] == 1  # weakest
        assert ranks["B"] == 2
        assert ranks["C"] == 3  # strongest

    def test_null_live_ew_gets_none_rank(self):
        data = [
            {"id": "A", "live_ew_chg_pct": 1.0},
            {"id": "B", "live_ew_chg_pct": None},
        ]
        ranks = bp._tape_ranks(data)
        assert ranks["A"] == 1
        assert ranks["B"] is None

    def test_all_null_returns_none_ranks(self):
        data = [
            {"id": "X", "live_ew_chg_pct": None},
            {"id": "Y", "live_ew_chg_pct": None},
        ]
        ranks = bp._tape_ranks(data)
        assert all(v is None for v in ranks.values())


# ── shock-day relative bid gating tests ───────────────────────────────────────

class TestShockDayRelativeBid:
    """FT-R3: populated ONLY when oil_shock/geopolitical primary AND index down."""

    def _baskets_data(self, chg: float = 1.0) -> list[dict]:
        return [{"id": "test_basket", "live_ew_chg_pct": chg}]

    def test_populated_when_oil_shock_and_index_down(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {
            "SPY": _make_quote(-1.5, now=now),
            "XLK": _make_quote(2.0, now=now),
        }
        md = {"primary": "oil_shock", "family": "inflation"}
        result = bp._shock_day_relative_bid(md, self._baskets_data(1.0), qs, _now_ms(now))
        assert result is not None
        assert result["active_driver"] == "oil_shock"
        assert result["index_chg_pct"] < 0
        assert result["t1_fade_note"] == bp._T1_FADE_NOTE
        # NO beneficiary/casualty/direction fields (FT-R3)
        assert "beneficiary" not in result
        assert "casualty" not in result
        assert "direction" not in result

    def test_not_populated_when_index_up(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {"SPY": _make_quote(+0.5, now=now)}
        md = {"primary": "oil_shock", "family": "inflation"}
        result = bp._shock_day_relative_bid(md, self._baskets_data(), qs, _now_ms(now))
        assert result is None

    def test_not_populated_when_wrong_driver(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {"SPY": _make_quote(-1.0, now=now)}
        md = {"primary": "ai_semis", "family": "equity-leadership"}
        result = bp._shock_day_relative_bid(md, self._baskets_data(), qs, _now_ms(now))
        assert result is None

    def test_not_populated_when_no_market_drivers(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {"SPY": _make_quote(-1.0, now=now)}
        result = bp._shock_day_relative_bid(None, self._baskets_data(), qs, _now_ms(now))
        assert result is None

    def test_populated_when_geopolitical_family(self):
        """Geopolitical family (future driver) also gates the shock readout."""
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {"SPY": _make_quote(-2.0, now=now)}
        md = {"primary": "geopolitical_risk", "family": "geopolitical"}
        result = bp._shock_day_relative_bid(md, self._baskets_data(1.5), qs, _now_ms(now))
        assert result is not None
        assert result["active_driver"] == "geopolitical_risk"

    def test_rows_descriptive_only_no_ranking_field(self):
        """Rows carry id + live_ew_chg_pct; no beneficiary ranking."""
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {"SPY": _make_quote(-1.0, now=now)}
        md = {"primary": "oil_shock", "family": "inflation"}
        bdata = [
            {"id": "energy_complex", "live_ew_chg_pct": 2.5},
            {"id": "defensives", "live_ew_chg_pct": -0.3},
        ]
        result = bp._shock_day_relative_bid(md, bdata, qs, _now_ms(now))
        assert result is not None
        for row in result["rows"]:
            assert set(row.keys()) == {"id", "live_ew_chg_pct"}


# ── offense/defense spread tests ──────────────────────────────────────────────

class TestOdSpread:
    """od_spread_print = EW(defense) - EW(offense); None when any missing/stale."""

    def test_spread_math(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {
            "XLP": _make_quote(1.0, now=now),
            "XLU": _make_quote(2.0, now=now),
            "XLV": _make_quote(3.0, now=now),
            "SMH": _make_quote(-1.0, now=now),
            "XLK": _make_quote(1.0, now=now),
        }
        spread = bp._od_spread(qs, _now_ms(now))
        # defense avg = (1+2+3)/3 = 2.0; offense avg = (-1+1)/2 = 0.0; spread = 2.0
        assert spread == pytest.approx(2.0, abs=0.01)

    def test_returns_none_when_etf_missing(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {
            "XLP": _make_quote(1.0, now=now),
            # XLU and XLV missing
            "SMH": _make_quote(1.0, now=now),
            "XLK": _make_quote(1.0, now=now),
        }
        assert bp._od_spread(qs, _now_ms(now)) is None

    def test_returns_none_when_etf_stale(self):
        now = datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
        qs = {
            "XLP": _make_quote(1.0, age_min=25.0, now=now),  # stale
            "XLU": _make_quote(1.0, now=now),
            "XLV": _make_quote(1.0, now=now),
            "SMH": _make_quote(1.0, now=now),
            "XLK": _make_quote(1.0, now=now),
        }
        assert bp._od_spread(qs, _now_ms(now), stale_min=20) is None


# ── full build integration tests ───────────────────────────────────────────────

class TestBuild:
    """Integration tests using synthetic fixtures (no data/ reads for memberships)."""

    def _synthetic_membership(self, tmp_path: Path) -> Path:
        m = {
            "version": "test",
            "baskets": _make_membership({
                "basket_a": ["AA", "AB", "AC"],
                "basket_b": ["BA", "BB", "BC", "BD", "BD2", "BD3", "BD4"],
            }),
        }
        p = tmp_path / "membership.json"
        p.write_text(json.dumps(m))
        return p

    def test_build_emits_required_schema_keys(self, tmp_path, monkeypatch):
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # 10:00 ET = RTH
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, now=now),
            "AB": _make_quote(2.0, now=now),
            "AC": _make_quote(3.0, now=now),
            "BA": _make_quote(-1.0, now=now),
            "BB": _make_quote(-2.0, now=now),
            "BC": _make_quote(-3.0, now=now),
            "BD": _make_quote(0.5, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        # monkeypatch cum_2d to avoid reading parquet
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path,
            membership_path=mem_path,
            now=now,
        )

        assert result["schema"] == "basket_pulse.v1"
        assert result["session"] == "rth"
        assert "as_of_utc" in result
        assert "built" in result
        assert isinstance(result["coverage_pct"], float)
        assert isinstance(result["baskets"], list)
        assert len(result["baskets"]) == 2

    def test_basket_ew_and_rank_computed(self, tmp_path, monkeypatch):
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(3.0, now=now),
            "AB": _make_quote(3.0, now=now),
            "AC": _make_quote(3.0, now=now),
            "BA": _make_quote(-1.0, now=now),
            "BB": _make_quote(-1.0, now=now),
            "BC": _make_quote(-1.0, now=now),
            "BD": _make_quote(-1.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        baskets = {b["id"]: b for b in result["baskets"]}

        # basket_a: EW = 3.0; basket_b: EW = -1.0
        assert baskets["basket_a"]["live_ew_chg_pct"] == pytest.approx(3.0, abs=0.01)
        assert baskets["basket_b"]["live_ew_chg_pct"] == pytest.approx(-1.0, abs=0.01)

        # basket_b is weaker → rank 1; basket_a is stronger → rank 2
        assert baskets["basket_b"]["tape_rank"] == 1
        assert baskets["basket_a"]["tape_rank"] == 2

    def test_low_coverage_basket_has_null_ew(self, tmp_path, monkeypatch):
        """A basket with only 1 out of 10 members quoted (<30%) → null EW."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        tickers_10 = [f"M{i:02d}" for i in range(10)]
        qs = {"quotes": {tickers_10[0]: _make_quote(5.0, now=now)}}  # only 1 quoted
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps(qs))

        mem = {"version": "t", "baskets": _make_membership({"big_basket": tickers_10})}
        mem_path = tmp_path / "membership.json"
        mem_path.write_text(json.dumps(mem))
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        b = result["baskets"][0]
        assert b["live_ew_chg_pct"] is None, "coverage 1/10=10% should return null"
        assert b["tape_rank"] is None

    def test_premarket_session_flag(self, tmp_path, monkeypatch):
        """11:00 UTC = 07:00 ET → session = 'pre'."""
        now = datetime(2026, 7, 8, 11, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        assert result["session"] == "pre"

    def test_shock_day_relative_bid_gated(self, tmp_path, monkeypatch, tmp_path_factory):
        """shock_day_relative_bid populated when oil_shock + SPY down."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, now=now),
            "AB": _make_quote(1.0, now=now),
            "AC": _make_quote(1.0, now=now),
            "SPY": _make_quote(-1.5, now=now),
        }}))
        drivers = {"primary": "oil_shock", "family": "inflation", "verdict": "clear"}
        drivers_path = tmp_path / "market_drivers.json"
        drivers_path.write_text(json.dumps(drivers))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path,
            membership_path=mem_path,
            drivers_path=drivers_path,
            now=now,
        )
        sdr = result["shock_day_relative_bid"]
        assert sdr is not None
        assert sdr["active_driver"] == "oil_shock"
        assert sdr["index_chg_pct"] < 0
        assert sdr["t1_fade_note"] == bp._T1_FADE_NOTE
        # FT-R3: no direction/beneficiary/casualty
        assert "beneficiary" not in sdr
        assert "direction" not in sdr

    def test_shock_day_not_populated_when_index_flat(self, tmp_path, monkeypatch):
        """shock_day_relative_bid = null when SPY not down."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, now=now),
            "AB": _make_quote(1.0, now=now),
            "AC": _make_quote(1.0, now=now),
            "SPY": _make_quote(+0.3, now=now),  # UP
        }}))
        drivers_path = tmp_path / "market_drivers.json"
        drivers_path.write_text(json.dumps({"primary": "oil_shock", "family": "inflation"}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path,
            membership_path=mem_path,
            drivers_path=drivers_path,
            now=now,
        )
        assert result["shock_day_relative_bid"] is None

    def test_empty_quotes_produces_valid_output(self, tmp_path, monkeypatch):
        """No quotes → coverage 0%, all live_ew_chg_pct null, still a valid JSON."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        # JSON serializable (allow_nan=False contract)
        raw = json.dumps(result, allow_nan=False)
        assert "NaN" not in raw
        for b in result["baskets"]:
            assert b["live_ew_chg_pct"] is None

    def test_output_is_nan_safe(self, tmp_path, monkeypatch):
        """Output must be serializable with allow_nan=False."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        # Must not raise
        json.dumps(result, allow_nan=False)

    def test_build_emits_new_schema_fields(self, tmp_path, monkeypatch):
        """TS-R1: build result includes mode, delay_min_median, as_of_quotes."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # RTH
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, now=now),
            "AB": _make_quote(1.0, now=now),
            "AC": _make_quote(1.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        assert "mode" in result
        assert "delay_min_median" in result
        assert "as_of_quotes" in result


# ── graded-mode tests (TS-R1) ──────────────────────────────────────────────────

class TestGradedModes:
    """TS-R1: live, delayed, last_rth, eod modes.

    Fixtures use the real pathology: 238-min delays, post-session.
    """

    def _synthetic_membership(self, tmp_path: Path) -> Path:
        m = {
            "version": "test",
            "baskets": _make_membership({
                "basket_a": ["AA", "AB", "AC"],
                "basket_b": ["BA", "BB"],
            }),
        }
        p = tmp_path / "membership.json"
        p.write_text(json.dumps(m))
        return p

    # RTH, fresh quotes → live mode
    def test_live_mode_rth_fresh_quotes(self, tmp_path, monkeypatch):
        """Fresh quotes during RTH → mode=live, values computed."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # 10:00 ET RTH
        qs_path = tmp_path / "quotes.json"
        # All quotes fresh (delayMin=1 via default age_min=1)
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(2.0, now=now),
            "AB": _make_quote(2.0, now=now),
            "AC": _make_quote(2.0, now=now),
            "BA": _make_quote(-1.0, now=now),
            "BB": _make_quote(-1.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        assert result["mode"] == bp.MODE_LIVE
        assert result["session"] == "rth"
        baskets = {b["id"]: b for b in result["baskets"]}
        assert baskets["basket_a"]["live_ew_chg_pct"] == pytest.approx(2.0, abs=0.01)
        assert baskets["basket_b"]["live_ew_chg_pct"] == pytest.approx(-1.0, abs=0.01)
        assert result["delay_min_median"] is not None

    # RTH, delayed quotes (238-min delay, real-world Polygon pathology) → delayed mode
    def test_delayed_mode_rth_238min_delay(self, tmp_path, monkeypatch):
        """Delayed quotes during RTH (238-min data-provider delay) → mode=delayed,
        values computed anyway (honest-delay law), delay_min_median populated."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # 10:00 ET RTH
        qs_path = tmp_path / "quotes.json"
        # Simulate 238-min Polygon free-tier delay
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(3.0, age_min=238.0, now=now),
            "AB": _make_quote(3.0, age_min=238.0, now=now),
            "AC": _make_quote(3.0, age_min=238.0, now=now),
            "BA": _make_quote(-2.0, age_min=238.0, now=now),
            "BB": _make_quote(-2.0, age_min=238.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        assert result["mode"] == bp.MODE_DELAYED, (
            "Quotes with 238-min delay must yield mode=delayed, not null")
        # Values MUST be computed (honest-delay law: delayed value beats null)
        baskets = {b["id"]: b for b in result["baskets"]}
        assert baskets["basket_a"]["live_ew_chg_pct"] is not None, (
            "Delayed mode must compute EW from delayed quotes, not null")
        assert baskets["basket_a"]["live_ew_chg_pct"] == pytest.approx(3.0, abs=0.01)
        assert baskets["basket_b"]["live_ew_chg_pct"] == pytest.approx(-2.0, abs=0.01)
        assert result["delay_min_median"] == pytest.approx(238.0, abs=1.0)

    # Post-session + no quotes + no lastgood → eod mode
    def test_eod_mode_post_session_no_quotes_no_sidecar(self, tmp_path, monkeypatch):
        """Post-session, no quotes, no lastgood sidecar → mode=eod.
        eod_basket_chg called; no crash on missing parquet."""
        # 21:00 UTC = 17:00 ET → closed
        now = datetime(2026, 7, 8, 21, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)
        # No parquet files → eod_basket_chg returns None gracefully
        monkeypatch.setattr(bp, "_eod_basket_chg", lambda bid, mems: (None, None))

        result = bp.build(
            quotes_path=qs_path, membership_path=mem_path, now=now,
            out_dir=tmp_path,  # no sidecar present → eod
        )
        assert result["mode"] == bp.MODE_EOD
        json.dumps(result, allow_nan=False)  # NaN-safe contract

    # Post-session + valid sidecar → last_rth mode
    def test_last_rth_mode_with_sidecar(self, tmp_path, monkeypatch):
        """Post-session with a lastgood sidecar → mode=last_rth, original values served."""
        # Create a fake lastgood sidecar
        lastgood = {
            "schema": "basket_pulse.v1",
            "as_of_utc": "2026-07-08T20:00:00+00:00",
            "as_of_quotes": "2026-07-08T20:00:00+00:00",
            "built": "2026-07-08 20:00:00 UTC",
            "session": "rth",
            "mode": bp.MODE_DELAYED,
            "delay_min_median": 238.0,
            "coverage_pct": 99.5,
            "quotes_source": None,
            "n_quotes_total": 5,
            "stale_min": 20,
            "baskets": [
                {"id": "basket_a", "n_members": 3, "n_quoted": 3,
                 "live_ew_chg_pct": 2.5, "cum_2d_pct": None, "tape_rank": 2,
                 "stale": True, "delay_min": 238.0},
                {"id": "basket_b", "n_members": 2, "n_quoted": 2,
                 "live_ew_chg_pct": -1.0, "cum_2d_pct": None, "tape_rank": 1,
                 "stale": True, "delay_min": 238.0},
            ],
            "od_spread_print": None,
            "shock_day_relative_bid": None,
            "complexes": [],
        }
        sidecar_path = tmp_path / bp.LASTGOOD_FILENAME
        sidecar_path.write_text(json.dumps(lastgood))

        # Now build in post-session
        now = datetime(2026, 7, 8, 21, 0, tzinfo=timezone.utc)  # 17:00 ET post
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path, membership_path=mem_path, now=now,
            out_dir=tmp_path,
        )
        assert result["mode"] == bp.MODE_LAST_RTH
        # Values from sidecar are preserved
        baskets = {b["id"]: b for b in result["baskets"]}
        assert baskets["basket_a"]["live_ew_chg_pct"] == pytest.approx(2.5, abs=0.01)
        assert result["session"] == "post"  # current session
        assert result["delay_min_median"] == pytest.approx(238.0, abs=1.0)
        json.dumps(result, allow_nan=False)

    # Lastgood sidecar is saved on live/delayed compute
    def test_lastgood_sidecar_saved_on_live_compute(self, tmp_path, monkeypatch):
        """Successful live build writes basket_pulse_lastgood.json."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # RTH
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, now=now),
            "AB": _make_quote(1.0, now=now),
            "AC": _make_quote(1.0, now=now),
            "BA": _make_quote(-1.0, now=now),
            "BB": _make_quote(-1.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path, membership_path=mem_path, now=now,
            out_dir=tmp_path,
        )
        sidecar = tmp_path / bp.LASTGOOD_FILENAME
        assert sidecar.exists(), "lastgood sidecar must be written on live build"
        saved = json.loads(sidecar.read_text())
        assert saved["mode"] in (bp.MODE_LIVE, bp.MODE_DELAYED)
        assert saved["coverage_pct"] > 0

    # Mode=delayed: per-basket delay_min field is populated
    def test_delayed_mode_per_basket_delay_min(self, tmp_path, monkeypatch):
        """In delayed mode, each basket row has a delay_min field."""
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "AA": _make_quote(1.0, age_min=193.0, now=now),
            "AB": _make_quote(1.0, age_min=193.0, now=now),
            "AC": _make_quote(1.0, age_min=193.0, now=now),
            "BA": _make_quote(-1.0, age_min=155.0, now=now),
            "BB": _make_quote(-1.0, age_min=155.0, now=now),
        }}))
        mem_path = self._synthetic_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path, now=now)
        assert result["mode"] == bp.MODE_DELAYED
        for b in result["baskets"]:
            assert b.get("delay_min") is not None, (
                f"basket {b['id']} missing delay_min in delayed mode")

    # NaN-safe output for all modes
    def test_all_modes_nan_safe(self, tmp_path, monkeypatch):
        """All build paths produce allow_nan=False safe JSON."""
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)
        monkeypatch.setattr(bp, "_eod_basket_chg", lambda bid, mems: (None, None))
        mem_path = self._synthetic_membership(tmp_path)

        for label, qs_content, dt, extra in [
            ("live", json.dumps({"quotes": {
                "AA": _make_quote(1.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
                "AB": _make_quote(1.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
                "AC": _make_quote(1.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
            }}), datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc), {}),
            ("delayed", json.dumps({"quotes": {
                "AA": _make_quote(1.0, age_min=238.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
                "AB": _make_quote(1.0, age_min=238.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
                "AC": _make_quote(1.0, age_min=238.0, now=datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)),
            }}), datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc), {}),
            ("eod", '{"quotes":{}}', datetime(2026, 7, 8, 21, 0, tzinfo=timezone.utc),
             {"out_dir": tmp_path}),
        ]:
            qs_path = tmp_path / f"quotes_{label}.json"
            qs_path.write_text(qs_content)
            result = bp.build(
                quotes_path=qs_path, membership_path=mem_path, now=dt, **extra)
            try:
                json.dumps(result, allow_nan=False)
            except Exception as e:
                raise AssertionError(f"mode={label}: NaN in output: {e}") from e


class TestSidecarDurability:
    """TS-U0 blocker fix: sidecar must be in the fastpath staging set, and the
    age guard must gate stale sidecars before serving last_rth."""

    def _synthetic_membership(self, tmp_path: Path) -> Path:
        m = {
            "version": "test",
            "baskets": _make_membership({
                "basket_a": ["AA", "AB", "AC"],
                "basket_b": ["BA", "BB"],
            }),
        }
        p = tmp_path / "membership.json"
        p.write_text(json.dumps(m))
        return p

    def test_lastgood_path_in_fastpath_staging(self):
        """The sidecar filename must appear in the intraday-fastpath.yml staging block.

        This is a durability guard: if the workflow doesn't force-stage the sidecar
        it is wiped by actions/checkout at the next tick and last_rth never fires.
        """
        import re
        wf = Path(__file__).parent.parent / ".github" / "workflows" / "intraday-fastpath.yml"
        if not wf.exists():
            pytest.skip("intraday-fastpath.yml not present in this checkout")
        content = wf.read_text()
        assert bp.LASTGOOD_FILENAME in content, (
            f"{bp.LASTGOOD_FILENAME} must be force-staged in {wf.name}; "
            "otherwise the sidecar is wiped by checkout and last_rth can never fire."
        )

    def test_stale_sidecar_falls_through_to_eod(self, tmp_path, monkeypatch):
        """A sidecar older than the last completed NYSE session must NOT be served as
        last_rth — it should fall through to eod to avoid implying stale numbers
        are 'LAST SESSION'."""
        # Sidecar dated 2026-07-01 (many days ago, always older than last session)
        old_date = "2026-07-01T20:00:00+00:00"
        lastgood = {
            "schema": "basket_pulse.v1",
            "as_of_utc": old_date,
            "as_of_quotes": old_date,
            "built": "2026-07-01 20:00:00 UTC",
            "session": "rth",
            "mode": bp.MODE_DELAYED,
            "delay_min_median": 238.0,
            "coverage_pct": 99.5,
            "quotes_source": None,
            "n_quotes_total": 5,
            "stale_min": 20,
            "baskets": [
                {"id": "basket_a", "n_members": 3, "n_quoted": 3,
                 "live_ew_chg_pct": 2.5, "cum_2d_pct": None, "tape_rank": 2,
                 "stale": True, "delay_min": 238.0},
            ],
            "od_spread_print": None,
            "shock_day_relative_bid": None,
            "complexes": [],
        }
        sidecar_path = tmp_path / bp.LASTGOOD_FILENAME
        sidecar_path.write_text(json.dumps(lastgood))

        # Post-session on 2026-07-09 (sidecar is 8 days old — well beyond any holiday gap)
        now = datetime(2026, 7, 9, 21, 0, tzinfo=timezone.utc)  # 17:00 ET
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)

        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)
        monkeypatch.setattr(bp, "_eod_basket_chg", lambda bid, mems: (None, None))

        result = bp.build(
            quotes_path=qs_path, membership_path=mem_path, now=now,
            out_dir=tmp_path,
        )
        # Stale sidecar must be rejected; result must be eod, NOT last_rth
        assert result["mode"] == bp.MODE_EOD, (
            f"expected mode=eod when sidecar is multi-day stale, got {result['mode']!r}"
        )

    def test_fresh_sidecar_serves_last_rth(self, tmp_path, monkeypatch):
        """A same-day sidecar is served as last_rth (age guard passes)."""
        # Sidecar dated same day as the post-close tick (2026-07-09)
        fresh_date = "2026-07-09T18:00:00+00:00"
        lastgood = {
            "schema": "basket_pulse.v1",
            "as_of_utc": fresh_date,
            "as_of_quotes": fresh_date,
            "built": "2026-07-09 18:00:00 UTC",
            "session": "rth",
            "mode": bp.MODE_DELAYED,
            "delay_min_median": 238.0,
            "coverage_pct": 99.5,
            "quotes_source": None,
            "n_quotes_total": 5,
            "stale_min": 20,
            "baskets": [
                {"id": "basket_a", "n_members": 3, "n_quoted": 3,
                 "live_ew_chg_pct": 2.5, "cum_2d_pct": None, "tape_rank": 2,
                 "stale": True, "delay_min": 238.0},
            ],
            "od_spread_print": None,
            "shock_day_relative_bid": None,
            "complexes": [],
        }
        sidecar_path = tmp_path / bp.LASTGOOD_FILENAME
        sidecar_path.write_text(json.dumps(lastgood))

        # Post-session on 2026-07-09 (after 17:00 ET = 21:00 UTC)
        now = datetime(2026, 7, 9, 21, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._synthetic_membership(tmp_path)

        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(
            quotes_path=qs_path, membership_path=mem_path, now=now,
            out_dir=tmp_path,
        )
        assert result["mode"] == bp.MODE_LAST_RTH, (
            f"expected mode=last_rth for fresh same-day sidecar, got {result['mode']!r}"
        )
        assert result["baskets"][0]["live_ew_chg_pct"] == pytest.approx(2.5, abs=0.01)


class TestHKMarket:
    """GAP-3 HK extension: per-market session detection, separate artifact/sidecar
    names, US-organ gating, and the levels-based EOD fallback."""

    def _hk_membership(self, tmp_path: Path) -> Path:
        mem = {"baskets": {
            "hk_a": {"members": [
                {"ticker": "0700.HK", "removed": None},
                {"ticker": "9988.HK", "removed": None},
                {"ticker": "3690.HK", "removed": None},
            ]},
            "hk_b": {"members": [
                {"ticker": "1398.HK", "removed": None},
                {"ticker": "0939.HK", "removed": None},
            ]},
        }}
        p = tmp_path / "membership_hk.json"
        p.write_text(json.dumps(mem))
        return p

    # ── session detection ────────────────────────────────────────────────────

    @pytest.mark.parametrize("utc_hm,expected", [
        ((0, 30), "closed"),   # 08:30 HKT — before pre-auction
        ((1, 0), "pre"),       # 09:00 HKT — pre-opening auction
        ((1, 29), "pre"),      # 09:29 HKT
        ((1, 45), "rth"),      # 09:45 HKT
        ((4, 30), "rth"),      # 12:30 HKT — lunch folds into rth (delayed-mode honesty)
        ((7, 59), "rth"),      # 15:59 HKT
        ((8, 10), "post"),     # 16:10 HKT — closing auction / settle window
        ((8, 35), "closed"),   # 16:35 HKT
    ])
    def test_hk_session_windows(self, utc_hm, expected):
        h, m = utc_hm
        now = datetime(2026, 7, 8, h, m, tzinfo=timezone.utc)  # Wednesday, HKEX session day
        assert bp._hk_session(now) == expected

    def test_hk_session_closed_on_weekend_and_holiday(self):
        # Saturday
        assert bp._hk_session(datetime(2026, 7, 11, 3, 0, tzinfo=timezone.utc)) == "closed"
        # HKSAR Establishment Day (2026-07-01, a Wednesday) — HK holiday, NYSE open
        assert bp._hk_session(datetime(2026, 7, 1, 3, 0, tzinfo=timezone.utc)) == "closed"

    def test_market_session_dispatch(self):
        # 14:00 UTC on a Wednesday: US rth, HK closed (22:00 HKT)
        now = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)
        assert bp._market_session(now, "us") == "rth"
        assert bp._market_session(now, "hk") == "closed"

    # ── live compute ─────────────────────────────────────────────────────────

    def test_hk_live_mode_and_us_organ_gating(self, tmp_path, monkeypatch):
        now = datetime(2026, 7, 8, 2, 0, tzinfo=timezone.utc)  # 10:00 HKT = HK RTH
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "0700.HK": _make_quote(2.0, now=now),
            "9988.HK": _make_quote(1.0, now=now),
            "3690.HK": _make_quote(3.0, now=now),
            "1398.HK": _make_quote(-1.0, now=now),
            "0939.HK": _make_quote(-2.0, now=now),
            # US ETFs present in the shared snapshot must NOT produce an od spread for hk
            "XLP": _make_quote(0.5, now=now), "XLU": _make_quote(0.5, now=now),
            "XLV": _make_quote(0.5, now=now), "SMH": _make_quote(-0.5, now=now),
            "XLK": _make_quote(-0.5, now=now), "SPY": _make_quote(-1.0, now=now),
        }}))
        mem_path = self._hk_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path,
                          now=now, out_dir=tmp_path, market="hk")

        assert result["market"] == "hk"
        assert result["session"] == "rth"
        assert result["mode"] == bp.MODE_LIVE
        by_id = {b["id"]: b for b in result["baskets"]}
        assert by_id["hk_a"]["live_ew_chg_pct"] == pytest.approx(2.0, abs=0.01)
        assert by_id["hk_b"]["live_ew_chg_pct"] == pytest.approx(-1.5, abs=0.01)
        # US organs stay dark for hk
        assert result["od_spread_print"] is None
        assert result["shock_day_relative_bid"] is None
        assert result["complexes"] == []

    def test_hk_sidecar_uses_market_name(self, tmp_path, monkeypatch):
        now = datetime(2026, 7, 8, 2, 0, tzinfo=timezone.utc)
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text(json.dumps({"quotes": {
            "0700.HK": _make_quote(2.0, now=now),
            "9988.HK": _make_quote(1.0, now=now),
            "3690.HK": _make_quote(3.0, now=now),
            "1398.HK": _make_quote(-1.0, now=now),
            "0939.HK": _make_quote(-2.0, now=now),
        }}))
        mem_path = self._hk_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        bp.build(quotes_path=qs_path, membership_path=mem_path,
                 now=now, out_dir=tmp_path, market="hk")

        assert (tmp_path / bp.MARKETS["hk"]["lastgood_name"]).exists()
        assert not (tmp_path / bp.LASTGOOD_FILENAME).exists(), (
            "hk build must never write the US sidecar name"
        )

    # ── EOD fallback ─────────────────────────────────────────────────────────

    def test_hk_eod_fallback_reads_levels(self, tmp_path, monkeypatch):
        now = datetime(2026, 7, 11, 3, 0, tzinfo=timezone.utc)  # Saturday — closed
        qs_path = tmp_path / "quotes.json"
        qs_path.write_text('{"quotes":{}}')
        mem_path = self._hk_membership(tmp_path)
        monkeypatch.setattr(bp, "_cum_2d", lambda bid, chg, market="us": None)

        levels_called: list[str] = []

        def fake_levels(bid, market):
            assert market == "hk"
            levels_called.append(bid)
            return (1.5, "2026-07-10") if bid == "hk_a" else (None, None)

        def fail_ohlcv(bid, members):  # pragma: no cover — must not be reached
            raise AssertionError("hk eod must use the levels path, not member OHLCV")

        monkeypatch.setattr(bp, "_eod_basket_chg_levels", fake_levels)
        monkeypatch.setattr(bp, "_eod_basket_chg", fail_ohlcv)

        result = bp.build(quotes_path=qs_path, membership_path=mem_path,
                          now=now, out_dir=tmp_path, market="hk")

        assert result["mode"] == bp.MODE_EOD
        assert result["market"] == "hk"
        assert sorted(levels_called) == ["hk_a", "hk_b"]
        by_id = {b["id"]: b for b in result["baskets"]}
        assert by_id["hk_a"]["live_ew_chg_pct"] == pytest.approx(1.5, abs=0.01)
        assert by_id["hk_a"]["bar_date"] == "2026-07-10"
        assert by_id["hk_b"]["live_ew_chg_pct"] is None  # honest null (levels absent)

    @staticmethod
    def _write_levels(tmp_path, anchors):
        """Two frozen rows for hk_a; `anchors` is the `hk_a__anchor` column (None = pre-v2)."""
        import pandas as pd

        levels_dir = tmp_path / "basket_levels"
        levels_dir.mkdir(parents=True, exist_ok=True)
        idx = pd.to_datetime(["2026-07-09", "2026-07-10"])
        cols = {"hk_a__level_price": [100.0, 102.0]}
        if anchors is not None:
            cols["hk_a__anchor"] = anchors
        pd.DataFrame(cols, index=idx).to_parquet(levels_dir / "hk.parquet")

    def test_eod_levels_real_parquet_shape(self, tmp_path, monkeypatch):
        """_eod_basket_chg_levels against a real (synthetic) parquet file."""
        # chained: the newer row's anchor already covers the older row's date, so the
        # two levels sit on ONE base and their ratio is a real 1d return.
        self._write_levels(tmp_path, [None, "2026-07-09"])

        from lib import config
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

        chg, bar_date = bp._eod_basket_chg_levels("hk_a", "hk")
        assert chg == pytest.approx(2.0, abs=0.001)
        assert bar_date == "2026-07-10"
        # absent column → honest null
        assert bp._eod_basket_chg_levels("hk_missing", "hk") == (None, None)

    def test_eod_levels_legacy_store_is_honest_null(self, tmp_path, monkeypatch):
        """A pre-v2 store (no anchor column) must NOT be divided into a 1d return.

        Each legacy row was frozen on its own night's rolling-window base, so the
        ratio carries the EW return of the day that dropped out of the window front —
        an error the size of the number itself. Null, not a plausible-looking print.
        """
        self._write_levels(tmp_path, None)

        from lib import config
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

        assert bp._eod_basket_chg_levels("hk_a", "hk") == (None, None)

    def test_eod_levels_chain_break_is_honest_null(self, tmp_path, monkeypatch):
        """A chain that RESTARTED on the newer row is not divisible either."""
        self._write_levels(tmp_path, ["2026-07-09", "2026-07-10"])

        from lib import config
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

        assert bp._eod_basket_chg_levels("hk_a", "hk") == (None, None)

    def test_cum_2d_requires_a_spanning_chain(self, tmp_path, monkeypatch):
        """_cum_2d reads the same two rows and needs the same chain gate."""
        from lib import config
        monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

        self._write_levels(tmp_path, [None, "2026-07-09"])       # chained
        assert bp._cum_2d("hk_a", 0.5, market="hk") == pytest.approx(2.5, abs=0.001)

        self._write_levels(tmp_path, None)                        # legacy → null
        assert bp._cum_2d("hk_a", 0.5, market="hk") is None

        self._write_levels(tmp_path, ["2026-07-09", "2026-07-10"])  # break → null
        assert bp._cum_2d("hk_a", 0.5, market="hk") is None


# Intraday rotation clock recovery: an old quote cannot stay fresh on rebuild.
class TestObservedSourceClock:
    NOW = datetime(2026, 10, 13, 16, 0, tzinfo=timezone.utc)

    def test_saved_delay_is_not_a_permanent_age(self):
        quote = _make_quote(2.0, age_min=60, delay_min=1, now=self.NOW)
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) == 60
        assert bp._is_stale(quote, _now_ms(self.NOW)) is True

    def test_provider_delay_remains_a_floor(self):
        quote = _make_quote(2.0, age_min=1, delay_min=15, now=self.NOW)
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) == 15

    @pytest.mark.parametrize('stamp', [None, True, False, '', 'invalid', -1, 0, 10**400, float('nan'), float('inf')])
    def test_missing_or_malformed_source_clock_is_unknown(self, stamp):
        quote = {'ts': stamp, 'delayMin': 1, 'changePct': 3}
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) is None
        assert bp._is_stale(quote, _now_ms(self.NOW)) is True

    def test_future_source_clock_is_not_negative_delay(self):
        quote = {'ts': _now_ms(self.NOW) + 1, 'delayMin': 1, 'changePct': 3}
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) is None

    def test_synthetic_source_clock_cannot_support_freshness(self):
        quote = _make_quote(2, now=self.NOW)
        quote['tsSynthetic'] = True
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) is None

    @pytest.mark.parametrize('delay', [True, False, -1, float('nan'), float('inf'), 'invalid'])
    def test_invalid_delay_never_overrides_real_source_age(self, delay):
        quote = _make_quote(2, age_min=60, now=self.NOW)
        quote['delayMin'] = delay
        assert bp._quote_delay_min(quote, _now_ms(self.NOW)) == 60

    def test_unknown_clock_not_smuggled_into_delayed_average(self):
        quotes = {'A': _make_quote(2, age_min=60, now=self.NOW),
                  'B': {'changePct': 100, 'delayMin': 1, 'ts': None}}
        value, quoted, members, stale = bp._ew_chg(
            ['A', 'B'], quotes, _now_ms(self.NOW), include_delayed=True)
        assert value == 2
        assert (quoted, members, stale) == (2, 2, True)

    @pytest.mark.parametrize('change', [True, float('nan'), float('inf'), 'invalid'])
    def test_invalid_change_cannot_poison_output(self, change):
        quotes = {'A': _make_quote(0, now=self.NOW)}
        quotes['A']['changePct'] = change
        value, _, _, _ = bp._ew_chg(['A'], quotes, _now_ms(self.NOW), include_delayed=True)
        assert value is None

    def _build_from_quotes(self, tmp_path, monkeypatch, quotes, now=None):
        monkeypatch.delenv('LIVE_QUOTES_PATH', raising=False)
        monkeypatch.setattr(bp, '_cum_2d', lambda *args, **kwargs: None)
        monkeypatch.setattr(bp, '_load_market_drivers', lambda *args, **kwargs: None)
        monkeypatch.setattr(bp, '_attach_day_flow', lambda *args, **kwargs: None)
        membership = tmp_path / 'clock-membership.json'
        membership.write_text(json.dumps({'baskets': _make_membership({'clock_group': ['A', 'B', 'C']})}))
        quote_path = tmp_path / 'clock-quotes.json'
        quote_path.write_text(json.dumps({'quotes': quotes}))
        return bp.build(quotes_path=quote_path, membership_path=membership,
                        now=now or self.NOW, out_dir=tmp_path)

    def test_real_builder_degrades_aged_snapshot_and_serializes_source_range(self, tmp_path, monkeypatch):
        quotes = {'A': _make_quote(2, age_min=60, delay_min=1, now=self.NOW),
                  'B': _make_quote(4, age_min=70, delay_min=1, now=self.NOW),
                  'C': {'changePct': 99, 'ts': None, 'delayMin': 1},
                  'UNRELATED': _make_quote(8, age_min=1, now=self.NOW)}
        result = self._build_from_quotes(tmp_path, monkeypatch, quotes)
        row = result['baskets'][0]
        assert result['mode'] == 'delayed'
        assert result['delay_min_median'] == 65
        assert row['live_ew_chg_pct'] == 3
        assert row['n_priced'] == 2
        assert row['source_asof'] == '2026-10-13T15:00:00+00:00'
        assert row['source_oldest_at'] == '2026-10-13T14:50:00+00:00'
        assert row['source_time_span_seconds'] == 600
        assert result['source_asof'] == row['source_asof']
        assert result['source_oldest_at'] == row['source_oldest_at']
        assert result['as_of_quotes'] == result['source_asof']
        assert result['as_of_utc'] == self.NOW.isoformat()
        assert result['coverage_pct'] == pytest.approx(66.7)
        json.dumps(result, allow_nan=False)
        retained = json.loads((tmp_path / bp.LASTGOOD_FILENAME).read_text())
        assert retained['source_asof'] == result['source_asof']

    def test_build_source_clock_follows_contributors_not_every_quoted_member(self, tmp_path, monkeypatch):
        quotes = {'A': _make_quote(2, age_min=1, now=self.NOW),
                  'B': _make_quote(4, age_min=2, now=self.NOW),
                  'C': _make_quote(99, age_min=60, now=self.NOW)}
        result = self._build_from_quotes(tmp_path, monkeypatch, quotes)
        row = result['baskets'][0]
        assert result['mode'] == 'live'
        assert row['live_ew_chg_pct'] == 3
        assert row['n_quoted'] == 3
        assert row['n_priced'] == 2
        assert row['source_oldest_at'] == '2026-10-13T15:58:00+00:00'
        assert result['coverage_pct'] == pytest.approx(66.7)

    def test_closed_session_reuse_preserves_original_source_clocks(self, tmp_path, monkeypatch):
        quotes = _make_quotes({'A': 2, 'B': 4, 'C': 6}, self.NOW)
        first = self._build_from_quotes(tmp_path, monkeypatch, quotes)
        closed = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)
        second = self._build_from_quotes(tmp_path, monkeypatch, quotes, now=closed)
        assert second['mode'] == 'last_rth'
        assert second['source_asof'] == first['source_asof']
        assert second['as_of_quotes'] == first['as_of_quotes']
        assert second['served_utc'] == closed.isoformat()


class TestMatchedIntradayComparison:
    """Same-owner snapshot comparisons: no new collector, ledger, rank or alert."""
    FIRST = datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc)
    SECOND = datetime(2026, 10, 13, 15, 30, tzinfo=timezone.utc)

    def build(self, tmp_path, monkeypatch, prices, now, groups=None, alter=None):
        monkeypatch.delenv('LIVE_QUOTES_PATH', raising=False)
        monkeypatch.setattr(bp, '_cum_2d', lambda *args, **kwargs: None)
        monkeypatch.setattr(bp, '_load_market_drivers', lambda *args, **kwargs: None)
        monkeypatch.setattr(bp, '_attach_day_flow', lambda *args, **kwargs: None)
        quotes = {t: _make_quote((price/100-1)*100, now=now) for t, price in prices.items()}
        if alter:
            alter(quotes)
        qpath = tmp_path / 'comparison-quotes.json'
        qpath.write_text(json.dumps({'quotes': quotes}))
        mpath = tmp_path / 'comparison-members.json'
        mpath.write_text(json.dumps({'baskets': _make_membership(groups or {
            'ai_semiconductors': ['A'], 'us_sector_health': ['B']})}))
        result = bp.build(quotes_path=qpath, membership_path=mpath, now=now, out_dir=tmp_path)
        return result, {r['id']: r for r in result['baskets']}

    def test_daily_flat_can_contain_opposing_intraday_leadership(self, tmp_path, monkeypatch):
        first, first_rows = self.build(tmp_path, monkeypatch, {'A':102, 'B':99, 'SPY':100}, self.FIRST)
        assert first_rows['ai_semiconductors']['intraday_comparison']['status'] == 'baseline_missing'
        second, rows = self.build(tmp_path, monkeypatch, {'A':100, 'B':100, 'SPY':100}, self.SECOND)
        for row in rows.values():
            assert row['live_ew_chg_pct'] == 0
            assert row['intraday_comparison']['status'] == 'observed'
            assert row['intraday_comparison']['elapsed_minutes'] == 30
            assert row['intraday_comparison']['coverage_pct'] == 100
        assert rows['ai_semiconductors']['intraday_comparison']['relative_change_pct'] == pytest.approx(-1.960784, abs=1e-6)
        assert rows['us_sector_health']['intraday_comparison']['relative_change_pct'] == pytest.approx(1.010101, abs=1e-6)
        assert 'observation_baseline' not in second
        retained = json.loads((tmp_path / bp.LASTGOOD_FILENAME).read_text())
        assert retained['observation_baseline']['session_date'] == '2026-10-13'
        assert set(retained['observation_baseline']['quotes']) == {'A','B','SPY'}
        json.dumps(second, allow_nan=False)

    def test_coverage_swap_is_not_a_rotation(self, tmp_path, monkeypatch):
        groups = {'pair':['A','B']}
        self.build(tmp_path, monkeypatch, {'A':104,'SPY':100}, self.FIRST, groups)
        _, rows = self.build(tmp_path, monkeypatch, {'B':96,'SPY':100}, self.SECOND, groups)
        result = rows['pair']['intraday_comparison']
        assert result['status'] == 'insufficient_matched_coverage'
        assert result['matched_members'] == 0
        assert 'relative_change_pct' not in result

    def test_same_quote_is_not_a_new_observation(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        _, rows = self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        assert rows['ai_semiconductors']['intraday_comparison']['status'] == 'baseline_nonadvancing'

    def test_source_only_refresh_does_not_replay_an_interval(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        def unchanged(qs):
            for q in qs.values(): q['ts'] = _now_ms(self.FIRST)-60000
        _, rows = self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.SECOND, alter=unchanged)
        assert rows['ai_semiconductors']['intraday_comparison']['status'] == 'benchmark_nonadvancing'

    def test_no_overnight_splice(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        tomorrow = datetime(2026,10,14,15,30,tzinfo=timezone.utc)
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, tomorrow)
        assert rows['ai_semiconductors']['intraday_comparison']['status'] == 'session_boundary'

    def test_membership_change_has_its_own_null_reason(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST, {'pair':['A']})
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, self.SECOND, {'pair':['A','B']})
        assert rows['pair']['intraday_comparison']['status'] == 'membership_changed'

    @pytest.mark.parametrize('field,value', [('source','other'),('basis','minute'),('prevClose',99)])
    def test_source_or_reference_basis_change_is_not_return(self, tmp_path, monkeypatch, field, value):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        def alter(qs): qs['A'][field] = value
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, self.SECOND, alter=alter)
        c = rows['ai_semiconductors']['intraday_comparison']
        assert c['status'] == 'insufficient_matched_coverage'
        assert c['excluded']['basis_or_anchor_changed'] == 1

    def test_unsynchronized_member_is_not_evidence_for_spy_interval(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        def skew(qs): qs['A']['ts'] -= 5*60000
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, self.SECOND, alter=skew)
        c = rows['ai_semiconductors']['intraday_comparison']
        assert c['status'] == 'insufficient_matched_coverage'
        assert c['excluded']['source_clock_skew'] == 1

    def test_relative_winner_can_still_be_falling(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, self.FIRST)
        _, rows = self.build(tmp_path, monkeypatch, {'A':98,'B':97,'SPY':97}, self.SECOND)
        c = rows['ai_semiconductors']['intraday_comparison']
        assert c['absolute_change_pct'] == -2
        assert c['benchmark_change_pct'] == -3
        assert c['relative_change_pct'] == pytest.approx(1.030928, abs=1e-6)
        assert c['positive_relative_breadth_pct'] == 100

    def test_missing_benchmark_never_falls_back_to_absolute_returns(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':102,'B':99}, self.FIRST)
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100}, self.SECOND)
        assert rows['ai_semiconductors']['intraday_comparison']['status'] == 'benchmark_unavailable'

    def test_early_close_does_not_acquire_an_after_hours_baseline(self, tmp_path, monkeypatch):
        # Existing calendar owner declares Nov 27, 2026 a 13:00 ET close.
        first = datetime(2026,11,27,17,30,tzinfo=timezone.utc)
        late = datetime(2026,11,27,18,30,tzinfo=timezone.utc)
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, first)
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, late)
        # The early close now correctly routes to the settled-session branch,
        # but quotes 29 minutes after the bell still cannot form a comparison.
        assert rows['ai_semiconductors']['intraday_comparison']['status'] == 'benchmark_unavailable'
        retained = json.loads((tmp_path / bp.LASTGOOD_FILENAME).read_text())["observation_baseline"]
        assert all(q["ts"] < _now_ms(datetime(2026,11,27,18,0,tzinfo=timezone.utc))
                   for q in retained["quotes"].values())


    def test_short_intervals_require_tighter_source_alignment(self, tmp_path, monkeypatch):
        from datetime import timedelta
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        def skew(qs): qs['A']['ts'] -= 10000
        _, rows = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100},
                             self.FIRST + timedelta(seconds=30), alter=skew)
        c = rows['ai_semiconductors']['intraday_comparison']
        assert c['status'] == 'insufficient_matched_coverage'
        assert c['max_clock_skew_seconds'] == 3

    def test_real_producer_json_packet_and_grounding_path(self, tmp_path, monkeypatch):
        from engine.neuralweb import market_packet as mp
        self.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, self.FIRST)
        result, _ = self.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, self.SECOND)
        published = tmp_path / 'product' / 'site' / 'live'
        published.mkdir(parents=True)
        (published / 'basket_pulse.json').write_text(json.dumps(result, allow_nan=False))
        monkeypatch.setenv(mp._LIVE_DIR_ENV, str(published))
        packet = mp.build_packet(tmp_path / 'product', now=self.SECOND)
        text = mp.render_digest(packet)
        assert 'since prior observation' in text
        assert '+1.01%' in text and '\u22121.96%' in text
        assert 'not fund flows' in text
        assert len(packet['leaders']['intraday']) == 2
        assert all(r['live_ew_chg_pct'] == 0 for r in result['baskets'])


    def test_member_order_is_not_a_change_in_the_economic_cohort(self, tmp_path, monkeypatch):
        self.build(tmp_path, monkeypatch, {'A':110,'B':90,'SPY':100}, self.FIRST, {'pair':['A','B']})
        _, rows = self.build(tmp_path, monkeypatch, {'A':121,'B':81,'SPY':101}, self.SECOND, {'pair':['B','A']})
        result = rows['pair']['intraday_comparison']
        assert result['status'] == 'observed'
        assert result['absolute_change_pct'] == 0
        assert result['relative_change_pct'] == pytest.approx(-0.990099, abs=1e-6)
        assert result['positive_relative_breadth_pct'] == 50


@pytest.mark.parametrize("kind", ["older_source", "older_build", "missing_benchmark"])
def test_rejected_observation_cannot_roll_back_the_comparison_baseline(tmp_path, monkeypatch, kind):
    from datetime import timedelta
    helper = TestMatchedIntradayComparison()
    prices = {"A":102, "B":99, "SPY":100}
    helper.build(tmp_path, monkeypatch, prices, helper.FIRST)
    helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100}, helper.SECOND)
    path = tmp_path / bp.LASTGOOD_FILENAME
    before = json.loads(path.read_text())["observation_baseline"]
    now = helper.SECOND + timedelta(minutes=5)
    alter = None
    if kind == "older_source":
        def alter(qs):
            for q in qs.values(): q["ts"] = _now_ms(helper.FIRST) - 60000
    elif kind == "older_build":
        now = helper.FIRST + timedelta(minutes=5)
    else:
        prices.pop("SPY")
    helper.build(tmp_path, monkeypatch, prices, now, alter=alter)
    after = json.loads(path.read_text())["observation_baseline"]
    assert after == before
    def repeated(qs):
        for q in qs.values(): q["ts"] = _now_ms(helper.SECOND) - 60000
    _, rows = helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100},
                            helper.SECOND + timedelta(minutes=10), alter=repeated)
    assert all(row["intraday_comparison"]["status"] != "observed" for row in rows.values())


def test_stale_comparison_has_source_age_not_a_live_signal(tmp_path, monkeypatch):
    from datetime import timedelta
    from engine.neuralweb import market_packet as mp
    helper = TestMatchedIntradayComparison()
    helper.build(tmp_path, monkeypatch, {"A":102,"B":99,"SPY":100}, helper.FIRST)
    result, _ = helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100}, helper.SECOND)
    later = helper.SECOND + timedelta(minutes=46)
    block = mp._leaders_block(result, [], now=later)
    assert block is None or not block.get("intraday")


@pytest.mark.parametrize("corrected_ticker", ["A", "SPY"])
def test_equal_timestamp_correction_resets_baseline_without_inventing_interval(tmp_path, monkeypatch, corrected_ticker):
    from datetime import timedelta
    helper = TestMatchedIntradayComparison()
    prices = {"A":100, "B":100, "SPY":100}
    helper.build(tmp_path, monkeypatch, prices, helper.FIRST)
    corrected = {**prices, corrected_ticker:101}
    def same_clock(qs):
        for q in qs.values(): q["ts"] = _now_ms(helper.FIRST) - 60000
    _, corrected_rows = helper.build(tmp_path, monkeypatch, corrected,
                                      helper.FIRST + timedelta(minutes=2), alter=same_clock)
    assert corrected_rows["ai_semiconductors"]["intraday_comparison"]["status"] == "baseline_corrected"
    _, rows = helper.build(tmp_path, monkeypatch, corrected, helper.SECOND)
    c = rows["ai_semiconductors"]["intraday_comparison"]
    assert c["status"] == "observed"
    assert c["absolute_change_pct"] == 0 and c["benchmark_change_pct"] == 0
    assert c["relative_change_pct"] == 0



def test_lastgood_replace_failure_keeps_complete_prior_baseline(tmp_path, monkeypatch):
    original = {"schema":"basket_pulse.v1", "baskets":[], "observation_baseline":{"marker":"old"}}
    path = tmp_path / bp.LASTGOOD_FILENAME
    path.write_text(json.dumps(original))
    before = path.read_bytes()
    def fail_replace(*args, **kwargs):
        raise OSError("synthetic atomic replacement failure")
    monkeypatch.setattr(bp.os, "replace", fail_replace)
    bp._save_lastgood({"schema":"basket_pulse.v1","baskets":[]}, tmp_path,
                     observation_baseline={"marker":"new"})
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [bp.LASTGOOD_FILENAME]



def test_atomic_lastgood_preserves_existing_reader_mode(tmp_path):
    path = tmp_path / bp.LASTGOOD_FILENAME
    path.write_text('{}')
    path.chmod(0o640)
    bp._save_lastgood({"baskets":[]}, tmp_path, observation_baseline={})
    assert path.stat().st_mode & 0o777 == 0o640


def test_atomic_lastgood_new_file_respects_normal_creation_umask(tmp_path):
    control = tmp_path / 'control.json'
    control.write_text('{}')
    bp._save_lastgood({"baskets":[]}, tmp_path, observation_baseline={})
    assert (tmp_path / bp.LASTGOOD_FILENAME).stat().st_mode & 0o777 == control.stat().st_mode & 0o777



class TestClosingComparison:
    """Late-arriving closing prices are not generic after-hours performance."""

    @pytest.mark.parametrize("early_close", [False, True])
    def test_final_regular_interval_survives_post_close_delivery(self, tmp_path, monkeypatch, early_close):
        from datetime import timedelta
        from engine.neuralweb import market_packet as mp
        helper = TestMatchedIntradayComparison()
        close = (datetime(2026,11,27,18,0,tzinfo=timezone.utc) if early_close
                 else datetime(2026,10,13,20,0,tzinfo=timezone.utc))
        helper.build(tmp_path, monkeypatch, {"A":102,"B":99,"SPY":100}, close-timedelta(minutes=15))
        def closing(qs):
            for q in qs.values(): q["ts"] = _now_ms(close)+1000
        delivered = close+timedelta(minutes=16)
        result, rows = helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100},
                                    delivered, alter=closing)
        assert result["mode"] == "last_rth" and result["settled_close"] is True
        comparison = rows["ai_semiconductors"]["intraday_comparison"]
        assert comparison["status"] == "observed"
        assert comparison["observation_kind"] == "settled_regular"
        assert comparison["source_asof"] == (close+timedelta(seconds=1)).isoformat()
        assert comparison["relative_change_pct"] == pytest.approx(-1.960784, abs=1e-6)
        assert "observation_baseline" not in result
        block = mp._leaders_block(result, [], now=delivered)
        assert block["intraday"] and all(r["observation_kind"] == "settled_regular" for r in block["intraday"])
        assert "regular-session close" in mp._render_leaders({"leaders":block})
        _, repeated = helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100},
                                     delivered+timedelta(minutes=5), alter=closing)
        assert all(r["intraday_comparison"]["status"] == "observed" for r in repeated.values())
        assert all(r["intraday_comparison"]["is_new_observation"] is False for r in repeated.values())

    @pytest.mark.parametrize("basis,seconds,accepted", [
        ("regular",1,True), ("regular",90,True), ("regular",91,False),
        ("day",2,True), ("minute",1,False), ("trade",1,False),
        ("regular",-61,False), ("regular",-60,True),
    ])
    def test_closing_point_requires_bounded_explicit_regular_price(self, basis, seconds, accepted):
        from datetime import timedelta
        from engine.session_digest import session_window_et
        opened, close = session_window_et("2026-10-13")
        now = close+timedelta(minutes=15)
        q = _make_quote(1, now=now)
        q.update(basis=basis, ts=_now_ms(close)+seconds*1000)
        point = bp._comparison_point(q, now, opened, close, settled_close=True)
        assert (point is not None) is accepted
        if point is not None:
            assert point["ts"] == q["ts"]  # no clamp or backdating to the bell
        if seconds > 0:
            assert bp._comparison_point(q, now, opened, close) is None

    def test_true_afterhours_price_cannot_become_final_regular_interval(self, tmp_path, monkeypatch):
        from datetime import timedelta
        helper = TestMatchedIntradayComparison()
        close = datetime(2026,10,13,20,0,tzinfo=timezone.utc)
        helper.build(tmp_path, monkeypatch, {"A":102,"B":99,"SPY":100}, close-timedelta(minutes=15))
        def late(qs):
            for q in qs.values(): q["ts"] = _now_ms(close)+5*60000
        result, rows = helper.build(tmp_path, monkeypatch, {"A":100,"B":100,"SPY":100},
                                    close+timedelta(minutes=16), alter=late)
        assert all(row.get("intraday_comparison",{}).get("status") != "observed" for row in rows.values())

    def test_half_day_source_close_comes_from_shared_calendar(self):
        now = datetime(2026,11,27,18,16,tzinfo=timezone.utc)
        assert bp._session_close_utc(now) == datetime(2026,11,27,18,0,tzinfo=timezone.utc)
        assert bp._et_session(now) == "post"



def test_closing_source_transition_is_not_silently_stitched(tmp_path, monkeypatch):
    from datetime import timedelta
    helper = TestMatchedIntradayComparison()
    close = datetime(2026,10,13,20,0,tzinfo=timezone.utc)
    def before(qs):
        for q in qs.values(): q.update(source="polygon",basis="minute")
    helper.build(tmp_path,monkeypatch,{"A":102,"B":99,"SPY":100},close-timedelta(minutes=15),alter=before)
    def after(qs):
        for q in qs.values(): q.update(source="yahoo",basis="regular",ts=_now_ms(close)+1000)
    _, rows = helper.build(tmp_path,monkeypatch,{"A":100,"B":100,"SPY":100},close+timedelta(minutes=16),alter=after)
    assert all(row["intraday_comparison"]["status"] == "benchmark_basis_changed" for row in rows.values())


def test_unchanged_close_retains_measurement_but_is_not_new_and_still_expires(tmp_path, monkeypatch):
    from datetime import timedelta
    from engine.neuralweb import market_packet as mp
    helper = TestMatchedIntradayComparison()
    close = datetime(2026,10,13,20,0,tzinfo=timezone.utc)
    helper.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, close-timedelta(minutes=15))
    def at_close(quotes):
        for q in quotes.values(): q['ts'] = _now_ms(close)+1000
    _, first = helper.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, close+timedelta(minutes=16), alter=at_close)
    original = first['ai_semiconductors']['intraday_comparison']
    assert original['is_new_observation'] is True
    for minute in (21,26,46):
        result, again = helper.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, close+timedelta(minutes=minute), alter=at_close)
        retained = again['ai_semiconductors']['intraday_comparison']
        assert retained['status'] == 'observed'
        assert retained['is_new_observation'] is False and retained['delivery_state'] == 'retained'
        assert retained['reference_asof'] == original['reference_asof']
        assert retained['source_asof'] == original['source_asof']
        assert retained['relative_change_pct'] == original['relative_change_pct']
        assert 'observation_baseline' not in result
        block = mp._intraday_comparison_block(retained, now=close+timedelta(minutes=minute))
        assert (block is not None) is (minute <= 45)
        if block is not None:
            assert block['is_new_observation'] is False
            text = mp._render_leaders({'leaders': {'intraday':[dict(block,id='A',label='A')]}})
            assert 'retained observation' in text


@pytest.mark.parametrize('change',['correction','membership','older_benchmark','missing_member'])
def test_closing_retention_never_reuses_changed_observation(tmp_path, monkeypatch, change):
    from datetime import timedelta
    helper = TestMatchedIntradayComparison()
    close = datetime(2026,10,13,20,0,tzinfo=timezone.utc)
    helper.build(tmp_path, monkeypatch, {'A':102,'B':99,'SPY':100}, close-timedelta(minutes=15))
    def at_close(quotes):
        for q in quotes.values(): q['ts'] = _now_ms(close)+1000
    helper.build(tmp_path, monkeypatch, {'A':100,'B':100,'SPY':100}, close+timedelta(minutes=16), alter=at_close)
    values={'A':100,'B':100,'SPY':100}
    groups=None
    if change=='correction': values['A']=101
    if change=='membership': groups={'ai_semiconductors':['A','B'],'us_sector_health':['B']}
    if change=='missing_member': values.pop('A')
    def altered(quotes):
        at_close(quotes)
        if change=='older_benchmark': quotes['SPY']['ts']-=1000
    _, rows=helper.build(tmp_path,monkeypatch,values,close+timedelta(minutes=21),groups=groups,alter=altered)
    assert rows['ai_semiconductors']['intraday_comparison']['status'] != 'observed'


def test_invalid_evaluation_clock_cannot_read_or_erase_a_retained_baseline(tmp_path,monkeypatch):
    p=tmp_path/bp.LASTGOOD_FILENAME
    original=b'{"observation_baseline":{"sentinel":"preserve"}}'
    p.write_bytes(original)
    def forbidden(*args,**kwargs):
        pytest.fail('Source read attempted before evaluation-clock validation')
    monkeypatch.setattr(bp,'_load_quotes',forbidden)
    with pytest.raises(ValueError,match='timezone-aware'):
        bp.build(now=datetime(2026,10,13,15,59),out_dir=tmp_path)
    assert p.read_bytes()==original
