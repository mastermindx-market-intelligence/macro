"""Live-quotes SNAPSHOT builder (scripts.build_live_quotes).

The snapshot is the keyless, no-Worker live path: a GitHub Action runs this and
force-pushes the JSON to the `live-data` branch; the browser live.js fetches it.
These pin the parts that DON'T need a socket: the universe (CORE symbols always
present, junk rejected, de-duped), the engine->Worker-contract mapping live.js
consumes (epoch-ms ts, change%, prevClose), the data-sym site scrape, and the
load-bearing fail-safe (offline = a valid, empty snapshot).
"""
from __future__ import annotations

import json
import pathlib
import re
import pytest

from engine import live_quotes as lq
from scripts import build_live_quotes as blq


def test_yahoo_batch_stays_under_the_spark_cliff():
    # Yahoo spark HTTP-400s a symbols list >20 — the old batch of 50 silently
    # dropped every intl/equity quote. Guard the fix from regressing.
    assert lq._YAHOO_BATCH <= 20


def test_core_index_and_futures_symbols_always_in_universe(tmp_path):
    uni = blq.build_universe(tmp_path)                 # empty site dir -> CORE only
    for sym in ("^GSPC", "^IXIC", "^DJI", "^VIX", "ES=F", "NQ=F", "^HSI",
                "000001.SS", "^N225", "GC=F", "EURUSD=X",
                # All four Yahoo yield-index tenors: the curve read needs a front
                # AND a long leg to name a steepener vs a flattener.
                "^IRX", "^FVX", "^TNX", "^TYX"):
        assert sym in uni, sym


def test_display_snapshot_covers_every_live_tape_symbol():
    """Every macro tape tile needs the same-origin polling fallback.

    The websocket is an enhancement and may stay silent for individual futures;
    omitting a tile from DISPLAY_SYMBOLS leaves its baked value blank forever.
    """
    # Keep this lane dependency-light: app.tape itself imports FastAPI, while
    # the shared symbol contract intentionally has no web-server dependencies.
    from app.tape_symbols import TAPE_SYMBOLS

    assert set(TAPE_SYMBOLS) <= set(blq.DISPLAY_SYMBOLS)


def test_btc_is_in_core_and_routes_to_yahoo(tmp_path):
    # BTC trades 24/7, so it's kept in CORE (always fetched) and the Bitcoin Vector
    # header links data-sym="BTC-USD". A crypto pair must route to Yahoo, never Polygon
    # (crypto isn't entitled on the stocks plan) — pin both.
    assert "BTC-USD" in blq.build_universe(tmp_path)
    assert lq.is_us_symbol("BTC-USD") is False


def test_symbols_override_builds_exact_universe(tmp_path):
    # The hourly btc-live Action passes --symbols BTC-USD to refresh ONLY the crypto
    # leg — the snapshot must contain exactly that, not the whole CORE+scrape universe.
    (tmp_path / "big.html").write_text('<span data-sym="AAPL"><span data-sym="NVDA">')
    snap = blq.build(tmp_path, offline=True, symbols=["BTC-USD"])
    assert snap["meta"]["requested"] == 1          # exactly one symbol, CORE/scrape bypassed
    # offline -> no resolved quotes, but the requested universe was BTC-only
    assert "AAPL" not in snap["quotes"] and "NVDA" not in snap["quotes"]


def test_validate_symbols_dedups_uppercases_and_rejects_junk():
    got = blq._validate_symbols(["btc-usd", "BTC-USD", " eth-usd ", "';DROP", ""])
    assert got == ["BTC-USD", "ETH-USD"]           # upper, de-duped, junk + empty dropped


def test_universe_rejects_junk_and_dedups(tmp_path):
    (tmp_path / "a.html").write_text(
        'x <span class="nb-px" data-sym="AAPL"> '
        'y <span data-sym="aapl"> '              # case-dupe of AAPL after upper
        'z <span data-sym="0700.HK"> '
        'bad <span data-sym="\';DROP TABLE"> '   # junk -> charset-rejected
        'bad2 <span data-sym="<script>">')
    uni = blq.build_universe(tmp_path)
    assert "AAPL" in uni and "0700.HK" in uni
    assert uni.count("AAPL") == 1                 # de-duped (incl. lowercase form)
    assert all(blq._SYMBOL_RE.match(s) for s in uni)   # nothing malformed survives


def test_scrape_site_symbols_extracts_only_valid(tmp_path):
    (tmp_path / "p1.html").write_text('<span data-sym="NVDA"><span data-sym="600519.SS">')
    (tmp_path / "p2.html").write_text('<span data-sym="ES=F"><span data-sym="bad sym!">')
    got = blq.scrape_site_symbols(tmp_path)
    assert set(got) == {"NVDA", "600519.SS", "ES=F"}


def test_to_worker_quotes_maps_engine_dict_to_contract():
    raw = {"AAPL": {"price": 212.5, "quote_ts": "2026-06-23T14:00:00+00:00",
                    "quote_ts_synthetic": False,
                    "source": "polygon", "price_basis": "trade",
                    "prev_close": 210.0, "currency": "USD", "delay_min": 1.0}}
    out = blq.to_worker_quotes(raw)["AAPL"]
    assert out["price"] == 212.5
    assert out["source"] == "polygon" and out["basis"] == "trade"
    assert out["prevClose"] == 210.0
    assert out["changePct"] == round((212.5 / 210.0 - 1) * 100, 2)
    assert isinstance(out["ts"], int) and out["ts"] > 0     # epoch MILLIseconds
    from datetime import datetime
    assert out["ts"] == int(datetime.fromisoformat("2026-06-23T14:00:00+00:00").timestamp() * 1000)
    # The long-standing Worker/browser contract remains unchanged by default.
    assert "quote_ts" not in out
    assert "quote_ts_synthetic" not in out


def test_to_worker_quotes_private_provenance_preserves_source_clock_truth():
    raw = {
        "REAL": {
            "price": 212.5,
            "quote_ts": "2026-06-23T14:00:00.123456+00:00",
            "quote_ts_synthetic": False,
            "source": "polygon",
            "price_basis": "trade",
            "prev_close": 210.0,
            "currency": "USD",
            "delay_min": 1.0,
        },
        "SYNTH": {
            "price": 7400.0,
            "quote_ts": "2026-06-23T14:00:01+00:00",
            "quote_ts_synthetic": True,
            "source": "polygon",
            "price_basis": "day",
            "prev_close": 7390.0,
            "currency": "USD",
            "delay_min": 0.0,
        },
        "UNKNOWN": {
            "price": 100.0,
            "quote_ts": "2026-06-23T14:00:02+00:00",
            "source": "fixture",
            "price_basis": "trade",
            "prev_close": 99.0,
            "currency": "USD",
            "delay_min": 0.0,
        },
    }

    out = blq.to_worker_quotes(raw, include_private_provenance=True)

    assert out["REAL"]["quote_ts"] == raw["REAL"]["quote_ts"]
    assert out["REAL"]["quote_ts_synthetic"] is False
    assert out["SYNTH"]["quote_ts"] == raw["SYNTH"]["quote_ts"]
    assert out["SYNTH"]["quote_ts_synthetic"] is True
    # Missing provenance is never guessed from a non-null timestamp.
    assert out["UNKNOWN"]["quote_ts_synthetic"] is None


def test_synthetic_quote_keeps_public_clock_refusal_with_private_opt_in():
    clock = "2026-10-08T14:30:00.123456+00:00"
    raw = {"UNIT": {"price": 10.0, "quote_ts": clock,
                    "quote_ts_synthetic": True, "price_basis": "day"}}

    public = blq.to_worker_quotes(raw)["UNIT"]
    private = blq.to_worker_quotes(raw, include_private_provenance=True)["UNIT"]

    assert public["ts"] is None
    assert public["tsSynthetic"] is True
    assert "quote_ts" not in public and "quote_ts_synthetic" not in public
    assert private["ts"] is None
    assert private["tsSynthetic"] is True
    assert private["quote_ts"] == clock
    assert private["quote_ts_synthetic"] is True
    assert {k: v for k, v in private.items()
            if k not in {"quote_ts", "quote_ts_synthetic", "day_open",
                         "bid_price", "ask_price", "nbbo_ts", "nbbo_source"}} == public


@pytest.mark.parametrize("provenance", [None, 0, 1, "false", "true", [], {}])
def test_private_quote_provenance_does_not_coerce_nonboolean_values(provenance):
    clock = "2026-10-08T14:30:00+00:00"
    raw = {"UNIT": {"price": 10.0, "quote_ts": clock,
                    "quote_ts_synthetic": provenance}}

    private = blq.to_worker_quotes(raw, include_private_provenance=True)["UNIT"]

    assert private["quote_ts"] == clock
    assert private["quote_ts_synthetic"] is None


def test_build_private_opt_in_preserves_all_session_receipts(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from lib.market_session import session_status

    clock = datetime(2026, 10, 8, 14, 30, tzinfo=timezone.utc)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz is not None else clock.replace(tzinfo=None)

    raw = {"UNIT": {"price": 10.0, "quote_ts": clock.isoformat(),
                    "quote_ts_synthetic": False}}
    calls = []

    def fake_fetch_quotes(universe, *, offline=False, diag=None):
        calls.append((universe, offline))
        assert universe == ["UNIT"] and offline is False
        return raw

    monkeypatch.setattr(blq, "datetime", FrozenDatetime)
    monkeypatch.setattr(blq.live_quotes, "fetch_quotes", fake_fetch_quotes)
    public = blq.build(tmp_path, symbols=["UNIT"])
    private = blq.build(tmp_path, symbols=["UNIT"], include_private_provenance=True)

    expected = {market: session_status(market, clock)
                for market in ("us", "cn", "hk", "ca", "connect")}
    assert set(expected) == {"us", "cn", "hk", "ca", "connect"}
    assert public["sessions"] == private["sessions"] == expected
    assert public["asof"] == private["asof"] == clock.isoformat()
    assert public["ts"] == private["ts"] == int(clock.timestamp() * 1000)
    assert private["quotes"]["UNIT"]["quote_ts"] == clock.isoformat()
    assert "quote_ts" not in public["quotes"]["UNIT"]
    assert len(calls) == 2


def test_build_private_provenance_is_opt_in(monkeypatch, tmp_path):
    raw = {
        "AAPL": {
            "price": 212.5,
            "quote_ts": "2026-06-23T14:00:00+00:00",
            "quote_ts_synthetic": False,
            "source": "polygon",
            "price_basis": "trade",
            "prev_close": 210.0,
            "currency": "USD",
            "delay_min": 1.0,
        }
    }

    def fake_fetch_quotes(universe, *, offline=False, diag=None):
        assert universe == ["AAPL"]
        assert offline is False
        if diag is not None:
            diag["polygon_status"] = "fixture"
        return raw

    monkeypatch.setattr(blq.live_quotes, "fetch_quotes", fake_fetch_quotes)

    public = blq.build(tmp_path, symbols=["AAPL"])
    private = blq.build(
        tmp_path,
        symbols=["AAPL"],
        include_private_provenance=True,
    )

    assert "quote_ts" not in public["quotes"]["AAPL"]
    assert "quote_ts_synthetic" not in public["quotes"]["AAPL"]
    assert private["quotes"]["AAPL"]["quote_ts"] == raw["AAPL"]["quote_ts"]
    assert private["quotes"]["AAPL"]["quote_ts_synthetic"] is False


def test_to_worker_quotes_handles_missing_prevclose_and_price():
    raw = {
        "IDX": {"price": 7400.0, "quote_ts": None, "source": "yahoo",
                "price_basis": "regular", "prev_close": None, "currency": None},
        "DEAD": {"price": None, "source": "yahoo"},        # priceless -> dropped
    }
    out = blq.to_worker_quotes(raw)
    assert "DEAD" not in out
    assert out["IDX"]["prevClose"] is None
    assert out["IDX"]["changePct"] is None
    assert out["IDX"]["ts"] is None                         # missing quote_ts -> None


def test_build_offline_is_a_valid_empty_snapshot(tmp_path):
    snap = blq.build(tmp_path, offline=True)
    assert snap["source"] == "snapshot"
    assert snap["quotes"] == {}
    assert snap["meta"]["offline"] is True
    assert snap["meta"]["requested"] > 0                    # universe still assembled
    assert isinstance(snap["ts"], int) and snap["ts"] > 0


# ── Cap-raise regression guards (2026-07-09) ─────────────────────────────────
# Problem: build_universe capped at 800 (default), truncating alphabetically.
# At cap=800 only ~249/680 basket members survived. Cap raised to 2200 to cover
# the full ~1942-symbol scraped universe (CORE 39 + site data-sym ~1918) with
# headroom. Measured: 1938/1942 resolved in 53 s on Yahoo path (< 8-min timeout).
# File size at full universe: ~275 KB (< 500 KB browser-fetch budget).

def test_default_cap_is_2200():
    """Cap default must be at least 2200 to cover the full scraped universe."""
    import inspect
    sig = inspect.signature(blq.build_universe)
    assert sig.parameters["cap"].default >= 2200, (
        f"build_universe default cap is {sig.parameters['cap'].default} — "
        "must be >= 2200 to cover the full ~1942-symbol scraped universe"
    )


def test_build_default_cap_is_2200():
    """build() inherits the raised cap — pin it so a build() caller without
    an explicit cap= argument still gets the full universe."""
    import inspect
    sig = inspect.signature(blq.build)
    assert sig.parameters["cap"].default >= 2200


def test_cap_high_enough_for_full_scraped_universe(tmp_path):
    """Universe of ~1942 symbols (CORE + site data-sym) must fit under the cap
    without truncation, so no basket member is silently dropped."""
    # Simulate the full-size scraped universe: write a page with 1960 fake symbols
    # (A0000..A1959 — all pass the charset) to verify the cap doesn't truncate them.
    syms = [f"A{i:04d}" for i in range(1960)]        # 1960 valid-looking symbols
    html_lines = " ".join(f'<span data-sym="{s}">' for s in syms)
    (tmp_path / "big.html").write_text(html_lines)
    uni = blq.build_universe(tmp_path)                # uses default cap=2200
    # CORE (44) + 1960 scraped = 2004 unique; all must survive under cap=2200
    assert len(uni) >= 1999, (
        f"universe len {len(uni)} — default cap truncated symbols that should survive"
    )
    # Every scraped symbol must be present (no alphabetical truncation)
    uni_set = set(uni)
    missing = [s for s in syms if s not in uni_set]
    assert not missing, f"{len(missing)} scraped symbols truncated: {missing[:5]}..."


def test_universe_includes_basket_members(tmp_path, monkeypatch):
    """The membership leg (GAP-3 HK pulse): every active US + HK basket member
    joins the universe even when no built page emits its data-sym."""
    import json as _json

    data_dir = tmp_path / "data"
    (data_dir / "baskets").mkdir(parents=True)
    (data_dir / "baskets_hk").mkdir(parents=True)
    (data_dir / "baskets" / "membership.json").write_text(_json.dumps({"baskets": {
        "us_a": {"members": [{"ticker": "FAKEUS1", "removed": None},
                             {"ticker": "GONE", "removed": "2026-01-01"}]},
    }}))
    (data_dir / "baskets_hk" / "membership.json").write_text(_json.dumps({"baskets": {
        "hk_a": {"members": [{"ticker": "0700.HK", "removed": None},
                             {"ticker": "9988.HK", "removed": None}]},
    }}))
    monkeypatch.setattr(blq.config, "data_dir", lambda: data_dir)

    site = tmp_path / "site"
    site.mkdir()
    uni = blq.build_universe(site)

    assert "FAKEUS1" in uni
    assert "0700.HK" in uni and "9988.HK" in uni
    assert "GONE" not in uni, "removed members must not be fetched"
    # members outrank the scrape: they sit immediately after CORE
    assert uni.index("FAKEUS1") >= len(blq.CORE_SYMBOLS) - 1


# ── Brain market-packet curve feed (Mastermind W1, 2026-07-29) ───────────────
# The brain's Live Market State Packet reads its CURVE tenors and ^VIX tape row
# from THIS display snapshot (the VPS macro-live-fast lane runs --display).
# W1 diagnosis findings the tests below pin:
#   * The tenors were never "failing to resolve" — ^TNX only entered the display
#     universe on 2026-07-29 (#3963) and repo-committed snapshots had gone stale
#     two days earlier when production moved to the VPS timers (a code-vs-
#     artifact vintage skew, not a code bug). Probed from the VPS: Yahoo spark
#     resolves all five (^IRX ^FVX ^TNX ^TYX ^VIX) 5/5.
#   * Yield-index UNITS ARE FEED-DEPENDENT: this spark path delivers percent
#     directly; the /ws/tape relay streams the CBOE ×10 convention (see
#     templates/live.js tnxPct() and tests/test_tape_decode.py).


def test_display_universe_carries_the_packet_curve_inputs():
    """All four curve tenors + ^VIX must be in the same-origin display snapshot:
    the packet reads site/live/quotes.json only — a tenor missing here silently
    removes the CURVE line (and its FLAGS) from every brain grounding turn."""
    for sym in ("^IRX", "^FVX", "^TNX", "^TYX", "^VIX"):
        assert sym in blq.DISPLAY_SYMBOLS, sym


def test_display_universe_carries_the_china_index_face_tiles():
    """china.html's four index face tiles hydrate from the same-origin display
    snapshot. CSI 300 (000300.SS) and ChiNext (399006.SZ) are LIVE-ONLY tiles —
    they bake "—" because Yahoo serves no honest daily history for the real
    indexes — so a symbol dropped here leaves the tile a permanent dash. (The
    2026-08-11 production bug was the inverse: the tiles baked 510300.SS /
    159915.SZ ETF NAVs ~4.7/~3.6 as "index levels" and carried no data-sym.)"""
    for sym in ("000001.SS", "000300.SS", "399006.SZ", "^HSI"):
        assert sym in blq.DISPLAY_SYMBOLS, sym


def test_display_universe_survives_validation_undropped(tmp_path):
    """meta.requested == the defined display list, exactly — a static guard that
    no DISPLAY entry is silently eaten by the charset regex or by de-duping
    before the fetch (^VIX is hard-listed while ^TNX arrives via *TAPE_SYMBOLS;
    a symbol later added to BOTH would vanish as a dupe with no error anywhere).
    NOTE this cannot catch the vintage skew that actually produced the W1
    "27 requested vs 30 defined" artifact — a stale deployed producer running
    an older list — it pins the current literal only."""
    dupes = {s for s in blq.DISPLAY_SYMBOLS if blq.DISPLAY_SYMBOLS.count(s) > 1}
    assert not dupes, f"duplicate DISPLAY_SYMBOLS entries: {sorted(dupes)}"
    snap = blq.build(tmp_path, offline=True, symbols=list(blq.DISPLAY_SYMBOLS))
    assert snap["meta"]["requested"] == len(blq.DISPLAY_SYMBOLS)


def test_display_universe_carries_the_board_cards_not_only_the_tiles(tmp_path):
    """The bug this leg fixes: china_stocks.html renders 133 single-name Prophet
    cards, each a `.nb-px`/`.nb-chg` pill bound to a `data-sym`, but the display
    snapshot only ever fetched the ~34 hand-listed macro TILES — so live.js had
    no reading for a single one of them, patchChgNode() bailed on `chg == null`,
    and every percentage pill held its baked "—" through a live A-share session.
    A page that renders a data-sym must be IN the universe the producer fetches."""
    (tmp_path / "china_stocks.html").write_text(
        '<span class="nb-px" data-sym="001301.SZ" data-mkt="cn">54.38</span>'
        '<span class="nb-chg" data-sym="001301.SZ" data-mkt="cn">—</span>'
        '<span class="nb-px" data-sym="603308.SS" data-mkt="cn">48.40</span>'
        '<span class="nb-chg" data-sym="bad sym!" data-mkt="cn">—</span>'
    )
    uni = blq.display_universe(tmp_path)
    assert "001301.SZ" in uni and "603308.SS" in uni
    assert "BAD SYM!" not in uni                       # charset gate still holds
    # tiles first: a cap squeeze or a board surprise can never cost the market
    # strips their feed, and no tile is duplicated by a board page that shows it.
    assert uni[:len(blq.DISPLAY_SYMBOLS)] == list(blq.DISPLAY_SYMBOLS)
    assert len(uni) == len(set(uni))


def test_display_board_leg_is_capped_and_tiles_survive_the_cap(tmp_path):
    """The board's names are re-picked nightly, so the leg is unbounded by
    construction — cap it, and order the cap so the truncation can only ever eat
    board names, never a macro tile."""
    page = "".join(f'<span data-sym="{i:06d}.SZ"></span>' for i in range(400))
    (tmp_path / "china_stocks.html").write_text(page)
    board = blq.board_display_symbols(tmp_path)
    assert len(board) == blq.DISPLAY_BOARD_CAP
    uni = blq.display_universe(tmp_path)
    assert len(uni) == len(blq.DISPLAY_SYMBOLS) + blq.DISPLAY_BOARD_CAP
    for sym in blq.DISPLAY_SYMBOLS:
        assert sym in uni, sym


def test_display_board_leg_degrades_to_the_tiles_when_the_page_is_missing(tmp_path):
    """A checkout without the built page (or a renamed board) must not fail the
    once-a-minute lane — it degrades to exactly the pre-board behaviour."""
    assert blq.board_display_symbols(tmp_path) == []
    assert blq.display_universe(tmp_path) == list(blq.DISPLAY_SYMBOLS)


def test_display_board_pages_are_pages_this_repo_actually_builds():
    """A typo'd or renamed board page scrapes to nothing and reads exactly like
    the bug — silently back to tiles-only. Pin the names against the templates
    that opt their cards into the live percentage (show_change=true)."""
    for name in blq.DISPLAY_BOARD_PAGES:
        assert name.endswith(".html"), name
    assert "china_stocks.html" in blq.DISPLAY_BOARD_PAGES
    src = (blq._ROOT / "scripts" / "build_china.py").read_text(encoding="utf-8")
    assert '"china_stocks.html"' in src


# ── Board coverage expansion (2026-08-19, wave 2) ────────────────────────────
# Root cause: DISPLAY_BOARD_PAGES was china_stocks.html only, so us_stocks.html,
# hk_stocks.html and canada_stocks.html rendered a `.nb-chg` live-change pill
# live.js could never patch — the number stayed whatever the nightly render
# baked while looking intraday. Measured in production 2026-08-19 against
# https://www.mastermind-x.com/live/quotes.json (89 symbols): china_stocks.html
# 54/54 covered, us_stocks.html 0/3, hk_stocks.html 0/4, canada_stocks.html
# 0/10. These tests pin the expanded coverage and add the standing invariant
# that makes a future dead pill fail CI instead of shipping silently.
import logging


@pytest.mark.parametrize("page,valid_syms,malformed", [
    ("us_stocks.html", ["AAPL", "MSFT"], "bad sym!"),
    ("china_stocks.html", ["600519.SS", "000001.SZ"], "bad sym!"),
    ("hk_stocks.html", ["0700.HK", "9988.HK"], "bad sym!"),
    ("canada_stocks.html", ["RY.TO", "SHOP.TO"], "bad sym!"),
])
def test_board_coverage_per_market_format(tmp_path, page, valid_syms, malformed):
    """Every board named in DISPLAY_BOARD_PAGES must contribute its valid
    data-sym values to board_display_symbols(), in that market's own symbol
    format (bare US ticker, .SS/.SZ China, .HK Hong Kong, .TO Canada) — and
    a malformed value on the same page must never survive the charset gate."""
    assert page in blq.DISPLAY_BOARD_PAGES, f"{page} missing from DISPLAY_BOARD_PAGES"
    tags = "".join(
        f'<span class="nb-chg" data-sym="{s}">—</span>' for s in valid_syms
    )
    tags += f'<span class="nb-chg" data-sym="{malformed}">—</span>'
    (tmp_path / page).write_text(tags)
    board = blq.board_display_symbols(tmp_path)
    for sym in valid_syms:
        assert sym.upper() in board, sym
    assert malformed.upper() not in board


def test_board_duplicate_symbol_across_pages_collapses_to_one(tmp_path):
    """The same symbol rendered on two different board pages must appear
    exactly once in the fetched board leg — no double-counting toward the cap."""
    (tmp_path / "china_stocks.html").write_text(
        '<span class="nb-chg" data-sym="0700.HK">—</span>'
    )
    (tmp_path / "hk_stocks.html").write_text(
        '<span class="nb-chg" data-sym="0700.HK">—</span>'
    )
    board = blq.board_display_symbols(tmp_path)
    assert board.count("0700.HK") == 1


def test_board_rejects_the_real_world_js_template_artifact(tmp_path):
    """The built us_stocks.html carries a literal unrendered JS-template
    artifact `data-sym="'+sym+'"` (a client-side string-concat placeholder
    that never got substituted server-side) — it must never reach the fetched
    universe, where it would poison a batch feed request."""
    (tmp_path / "us_stocks.html").write_text(
        '<span class="nb-chg" data-sym="AAPL">—</span>'
        "<span class=\"nb-chg\" data-sym=\"'+sym+'\">—</span>"
    )
    board = blq.board_display_symbols(tmp_path)
    assert "AAPL" in board
    assert not any("SYM" in s or "+" in s or "'" in s for s in board)


def test_macro_tiles_keep_priority_over_an_oversized_board(tmp_path):
    """display_universe() must return every DISPLAY_SYMBOLS entry before any
    board-only symbol, and a board leg at or over DISPLAY_BOARD_CAP must never
    evict or reorder a macro tile."""
    page = "".join(
        f'<span class="nb-chg" data-sym="{i:06d}.SZ">—</span>'
        for i in range(blq.DISPLAY_BOARD_CAP + 50)
    )
    (tmp_path / "china_stocks.html").write_text(page)
    uni = blq.display_universe(tmp_path)
    n_tiles = len(blq.DISPLAY_SYMBOLS)
    assert uni[:n_tiles] == list(blq.DISPLAY_SYMBOLS)
    assert len(uni) == n_tiles + blq.DISPLAY_BOARD_CAP
    for sym in blq.DISPLAY_SYMBOLS:
        assert sym in uni, sym


def test_missing_board_page_degrades_visibly_with_a_named_warning(tmp_path, caplog):
    """A missing board file must not fail the build — the universe still
    assembles — but must log a warning NAMING the missing page, so a silently
    empty board leg (which looks exactly like the bug this PR fixes) is
    diagnosable. log.warning is correct here (this path never runs inside a
    GitHub Actions step), not the bare ::warning print the CI-annotation rule
    requires for Actions-step code."""
    with caplog.at_level(logging.WARNING, logger="live_quotes_build"):
        board = blq.board_display_symbols(tmp_path, pages=("us_stocks.html",))
    assert board == []
    assert any("us_stocks.html" in rec.message for rec in caplog.records), (
        "missing board page must be named in a warning log line"
    )


def test_visible_nb_chg_board_pages_are_covered_or_explicitly_exempt():
    """THE INVARIANT: scan the built site/*.html for every page emitting a
    `data-sym` inside a tag whose class contains `nb-chg` (a visible live-
    change claim) and assert each such page is either in DISPLAY_BOARD_PAGES
    or in DISPLAY_BOARD_EXEMPT_PAGES with a written reason. This is what makes
    a future board that renders the live-change pill without producer
    coverage fail CI instead of shipping a dead pill silently. Skips cleanly
    when site/ is not checked out (sparse worktree)."""
    site_dir = blq._ROOT / "site"
    if not site_dir.is_dir():
        pytest.skip("site/ not checked out (sparse worktree) — nothing to scan")

    tag_re = re.compile(r"<[a-zA-Z][^>]*>")
    class_re = re.compile(r'class="([^"]*)"')
    sym_re = re.compile(r'data-sym="([^"]*)"')

    offenders = []
    for html in sorted(site_dir.glob("*.html")):
        text = html.read_text(errors="ignore")
        emits_visible_live_change = False
        for tag in tag_re.findall(text):
            cm = class_re.search(tag)
            if not cm or "nb-chg" not in cm.group(1).split():
                continue
            if sym_re.search(tag):
                emits_visible_live_change = True
                break
        if not emits_visible_live_change:
            continue
        if html.name in blq.DISPLAY_BOARD_PAGES:
            continue
        if html.name in blq.DISPLAY_BOARD_EXEMPT_PAGES:
            continue
        offenders.append(html.name)

    assert not offenders, (
        f"page(s) render a visible .nb-chg live-change pill with no producer "
        f"coverage and no exemption reason: {offenders} — add to "
        f"DISPLAY_BOARD_PAGES (if the pill should go live) or to "
        f"DISPLAY_BOARD_EXEMPT_PAGES with a written reason (if it genuinely "
        f"should not)"
    )


# ── The GATED half of a board (2026-08-20) ───────────────────────────────────
# Reported live: most US Prophet cards showed a price beside a dead "—" percent.
# Root cause: the scrape stopped at `site/<page>.html`, but a tier-gated board
# server-renders only `preview_rows` cards there and writes the withheld
# remainder — same partial, same visible `.nb-chg` pill — into
# `site/premiumdata/<page>.json`, which the page splices into the SAME grid
# post-auth. Measured in production 2026-08-20: us_stocks.html carried 3 board
# symbols (all covered, all moving) while premiumdata/us_stocks.json carried 60
# more, 0 of which were in /live/quotes.json's 146.
#
# Note what the invariant above could NOT see: a gated page's VISIBLE pills are
# genuinely covered, so the page passes while 60 dead pills sit in the JSON
# beside it. That blind spot is the point of the payload invariant below.

def _payload_syms(blob: str) -> set:
    return {s.strip().upper() for s in blq._DATA_SYM_RE.findall(blob)
            if blq._SYMBOL_RE.match(s.strip().upper())}


def test_a_gated_boards_withheld_cards_reach_the_display_universe(tmp_path):
    """THE BUG. A board page whose shell holds 1 card and whose tier payload
    holds 3 must contribute all four — the wall decides who may READ a name, not
    which names the quote producer fetches."""
    (tmp_path / "us_stocks.html").write_text(
        '<span class="nb-chg" data-sym="BIIB">—</span>'
    )
    (tmp_path / "premiumdata").mkdir()
    (tmp_path / "premiumdata" / "us_stocks.json").write_text(json.dumps({
        "schema": "tier_payload.v1", "page": "us_stocks", "gated": True,
        "cards_html": '<span class="nb-chg" data-sym="HWM">—</span>'
                      '<span class="nb-chg" data-sym="GNW">—</span>',
        "actnow_html": '<span class="nb-chg" data-sym="SPOT">—</span>',
        # rows[] carries tickers too but no markup — the pills are what matter,
        # and scraping data-sym (not "any ticker-shaped string") is what keeps
        # this leg the same contract the page half has always had.
        "rows": [{"ticker": "NEVERMIND"}],
    }))
    board = blq.board_display_symbols(tmp_path)
    assert board == ["BIIB", "GNW", "HWM", "SPOT"], board
    assert "NEVERMIND" not in board
    assert set(board) <= set(blq.display_universe(tmp_path))


def test_payload_markup_is_json_escaped_so_a_raw_text_scrape_would_miss_it(tmp_path):
    """Why payload_html() parses JSON instead of regexing the raw bytes: inside
    the file the markup reads `data-sym=\\"HWM\\"`, which _DATA_SYM_RE cannot
    match — and a scrape that silently finds nothing is indistinguishable from a
    board that renders nothing."""
    p = tmp_path / "us_stocks.json"
    p.write_text(json.dumps({"cards_html": '<span class="nb-chg" data-sym="HWM">—</span>'}))
    assert 'data-sym=\\"HWM\\"' in p.read_text()
    assert not _payload_syms(p.read_text()), "raw-text scrape must be the broken path"
    assert _payload_syms(blq.payload_html(p)) == {"HWM"}


def test_a_symbol_on_both_sides_of_the_wall_costs_one_slot(tmp_path):
    (tmp_path / "us_stocks.html").write_text(
        '<span class="nb-chg" data-sym="BIIB">—</span>'
    )
    (tmp_path / "premiumdata").mkdir()
    (tmp_path / "premiumdata" / "us_stocks.json").write_text(json.dumps({
        "cards_html": '<span class="nb-chg" data-sym="BIIB">—</span>'
    }))
    assert blq.board_display_symbols(tmp_path).count("BIIB") == 1


def test_the_payload_leg_keeps_the_charset_gate(tmp_path):
    """A junk data-sym behind the wall must be rejected exactly as one on the
    page is — the payload is not a trusted shortcut into a feed request."""
    (tmp_path / "us_stocks.html").write_text('<span data-sym="BIIB"></span>')
    (tmp_path / "premiumdata").mkdir()
    (tmp_path / "premiumdata" / "us_stocks.json").write_text(json.dumps({
        "cards_html": '<span data-sym="HWM"></span><span data-sym="bad sym!"></span>'
                      "<span data-sym=\"'+sym+'\"></span>",
    }))
    board = blq.board_display_symbols(tmp_path)
    assert "HWM" in board
    assert not any("+" in s or "'" in s or " " in s for s in board)


@pytest.mark.parametrize("body", ["not json at all", "[1, 2, 3]", '"a string"', ""])
def test_an_unusable_payload_degrades_to_the_shell_and_never_raises(tmp_path, body):
    """This feeds the once-a-minute snapshot lane. A corrupt payload must cost
    the withheld cards their live percentage — the pre-fix behaviour — not cost
    every macro tile its feed."""
    (tmp_path / "us_stocks.html").write_text('<span data-sym="BIIB"></span>')
    (tmp_path / "premiumdata").mkdir()
    (tmp_path / "premiumdata" / "us_stocks.json").write_text(body)
    assert blq.board_display_symbols(tmp_path) == ["BIIB"]


def test_an_ungated_board_with_no_payload_is_unchanged(tmp_path):
    """Most board pages ship no payload at all; that is the normal case, not a
    fault, and must stay silent."""
    (tmp_path / "canada_stocks.html").write_text('<span data-sym="RY.TO"></span>')
    assert blq.board_display_symbols(tmp_path) == ["RY.TO"]


def test_tier_payload_pills_are_covered_by_the_producer():
    """THE INVARIANT the page-only scan could not express: for every shipped
    tier payload that carries a visible `.nb-chg` + data-sym, those symbols must
    actually land in the fetched board leg. This is what makes a future gated
    board fail CI instead of shipping 60 dead pills to the paying tier.
    Skips cleanly when site/ is not checked out (sparse worktree)."""
    site_dir = blq._ROOT / "site"
    payload_dir = site_dir / blq.DISPLAY_BOARD_PAYLOAD_DIR
    if not payload_dir.is_dir():
        pytest.skip("site/ not checked out (sparse worktree) — nothing to scan")

    board = set(blq.board_display_symbols(site_dir))
    uncovered = {}
    for path in sorted(payload_dir.glob("*.json")):
        blob = blq.payload_html(path)
        if 'class="nb-chg' not in blob:
            continue
        syms = _payload_syms(blob)
        missing = syms - board
        if missing:
            uncovered[path.name] = sorted(missing)[:8]

    assert not uncovered, (
        f"tier payload(s) render a visible .nb-chg pill for symbols the producer "
        f"never fetches: {uncovered} — every one of those cards shows a live "
        f"price beside a dead '—'. The owning page must be in "
        f"DISPLAY_BOARD_PAGES (its payload is scraped with it), and the board "
        f"leg must not be truncating at DISPLAY_BOARD_CAP "
        f"({blq.DISPLAY_BOARD_CAP})"
    )


def test_the_board_leg_has_headroom_over_the_cap():
    """`out[:cap]` truncates ALPHABETICALLY, which on the page reads as exactly
    the dead-pill bug — silently, on whichever names sort last. Fail while there
    is still room to think, not on the night the board grows."""
    site_dir = blq._ROOT / "site"
    if not site_dir.is_dir():
        pytest.skip("site/ not checked out (sparse worktree) — nothing to scan")
    n = len(blq.board_display_symbols(site_dir))
    assert n < blq.DISPLAY_BOARD_CAP, (
        f"board leg is AT the cap ({n}/{blq.DISPLAY_BOARD_CAP}) — names are "
        f"already being dropped"
    )
    assert n <= blq.DISPLAY_BOARD_CAP * 0.85, (
        f"board leg {n} is within 15% of DISPLAY_BOARD_CAP "
        f"({blq.DISPLAY_BOARD_CAP}); the US board is re-picked nightly, so raise "
        f"the cap with a fresh size/latency measurement before a heavy board "
        f"night truncates it"
    )


def test_yahoo_spark_yield_indexes_are_percent_direct_scale():
    """Documents the OBSERVED scale of this feed and guards the parser side of
    it: Yahoo spark delivered yield indexes as the yield percent directly
    (^TNX 4.622 = 4.622%, not the CBOE ×10 convention 46.22) — probed live from
    the VPS 2026-07-29: ^IRX 3.658 / ^FVX 4.352 / ^TNX 4.622 / ^TYX 5.143,
    matching that day's actual ~3.66%/4.35%/4.62%/5.14% tenors. parse_yahoo_spark
    must pass the number through unscaled — anyone "normalizing" ×10/÷10 inside
    the parser breaks every consumer at once. A fixture cannot detect Yahoo
    itself flipping conventions upstream; the runtime tripwires for that are
    scale detection at the consumer (templates/live.js tnxPct(), >15 → ÷10) and
    the packet's 0–20% level sanity band, which drops a ×10-scale print with a
    visible gap note. bp math is over price/prevClose LEVELS — the snapshot's
    `changePct` field is the relative day change, never basis points."""
    payload = {"spark": {"result": [{
        "symbol": "^TNX",
        "response": [{"meta": {"regularMarketPrice": 4.622,
                               "previousClose": 4.604,
                               "regularMarketTime": 1785351595,
                               "currency": "USD"}}],
    }]}}
    out = lq.parse_yahoo_spark(payload)
    assert out["^TNX"]["price"] == 4.622           # pass-through — no rescale
    assert out["^TNX"]["prev_close"] == 4.604
    # the real bp move is (4.622 - 4.604) × 100 = 1.8bp: percent→bp is ×100 on
    # the level difference (a ÷10 mis-scale would render the ten-year as 0.46%
    # and understate the move 10×; live.js:105 has the reference formula)
    assert round((out["^TNX"]["price"] - out["^TNX"]["prev_close"]) * 100, 1) == 1.8


# ---------------------------------------------------------------------------
# live.js currency-glyph contract: a patched price must keep the "$" the board
# BAKED, or a card visibly loses its currency symbol the moment it goes live.
#
# This only became reachable when the Canada/HK boards joined the live universe
# (the DISPLAY_BOARD_PAGES expansion above): before that live.js never patched
# those cards at all, so the mismatch could not show. Measured on the served
# pages 2026-08-19 — us "$212.55", ca "$15.20", hk "6.22", cn "37.70".
# ---------------------------------------------------------------------------
_LIVE_JS = pathlib.Path(__file__).resolve().parents[1] / "templates" / "live.js"

# market -> does its board bake a "$" on the nightly price
_BAKES_DOLLAR = {"us": True, "ca": True, "hk": False, "cn": False}


def _dollar_markets_from_live_js() -> set[str]:
    """The DOLLAR_MKT table as live.js actually declares it."""
    src = _LIVE_JS.read_text()
    m = re.search(r"var\s+DOLLAR_MKT\s*=\s*\{([^}]*)\}", src)
    assert m, "live.js no longer declares DOLLAR_MKT — update this contract test"
    return set(re.findall(r"([A-Za-z_]+)\s*:\s*1", m.group(1)))


def test_live_js_dollar_markets_match_the_boards_that_bake_a_dollar():
    """`ca` was missing, so every .TO card dropped its "$" on the first patch."""
    assert _dollar_markets_from_live_js() == {m for m, b in _BAKES_DOLLAR.items() if b}


def test_live_js_never_prefixes_a_dollar_onto_hkd_or_cny():
    """HK is HKD and China is CNY — a "$" there would be wrong, not merely ugly."""
    dollar = _dollar_markets_from_live_js()
    assert "hk" not in dollar and "cn" not in dollar


def test_fmt_price_uses_the_table_rather_than_a_hardcoded_us_test():
    """Regression guard: the old body was `(mkt === "us" ? "$" : "")`, which no
    amount of table-editing could fix. The table must be what fmtPrice reads."""
    src = _LIVE_JS.read_text()
    body = re.search(r"function fmtPrice\(price, mkt\)\s*\{(.*?)\n  \}", src, re.S)
    assert body, "fmtPrice not found in templates/live.js"
    assert "DOLLAR_MKT[mkt]" in body.group(1)
    assert 'mkt === "us" ? "$"' not in body.group(1)


def test_built_board_pages_bake_the_prefix_live_js_will_restore():
    """End-to-end: for every built board page, the glyph the page bakes is the
    glyph live.js puts back. Skips on a sparse checkout (no site/)."""
    site = pathlib.Path(__file__).resolve().parents[1] / "site"
    if not site.is_dir():
        pytest.skip("sparse worktree — site/ not checked out")
    dollar = _dollar_markets_from_live_js()
    checked = 0
    for page, mkt in (("us_stocks.html", "us"), ("canada_stocks.html", "ca"),
                      ("hk_stocks.html", "hk"), ("china_stocks.html", "cn")):
        p = site / page
        if not p.is_file():
            continue
        baked = re.findall(
            r'<span class="nb-px[^"]*"[^>]*data-mkt="' + mkt + r'"[^>]*>([^<]+)</span>',
            p.read_text(errors="ignore"))
        baked = [b.strip() for b in baked if b.strip() and b.strip() != "—"]
        if not baked:
            continue
        checked += 1
        has_dollar = all(b.startswith("$") for b in baked)
        assert has_dollar == (mkt in dollar), (
            f"{page} bakes {baked[:3]} for data-mkt={mkt!r} but live.js "
            f"{'adds' if mkt in dollar else 'omits'} the $ — a patch would change the glyph")
    assert checked, "no board page contributed a baked price — contract unverified"

def test_private_snapshot_preserves_measured_b4_evidence_without_clock_substitution():
    evidence = {
        "day_open": 210.1256,
        "bid_price": 212.1234,
        "ask_price": 212.2345,
        "nbbo_ts": "2026-10-08T14:29:58.987654+00:00",
        "nbbo_source": "polygon_lastQuote",
    }
    raw = {"UNIT": {
        "price": 212.2,
        "quote_ts": "2026-10-08T14:30:00.123456+00:00",
        "quote_ts_synthetic": False,
        "source": "polygon",
        "price_basis": "trade",
        **evidence,
    }}

    private = blq.to_worker_quotes(raw, include_private_provenance=True)["UNIT"]

    assert {field: private[field] for field in evidence} == evidence
    assert private["nbbo_ts"] != private["quote_ts"]
    assert private["quote_ts"] == raw["UNIT"]["quote_ts"]
    assert raw["UNIT"]["nbbo_ts"] == evidence["nbbo_ts"]
    assert not {"liquidity_fillability", "ENTRY_OPEN", "availability"} & private.keys()


def test_b4_evidence_does_not_change_the_public_projection():
    plain = {"UNIT": {
        "price": 212.2,
        "quote_ts": "2026-10-08T14:30:00+00:00",
        "quote_ts_synthetic": False,
        "source": "polygon",
        "price_basis": "trade",
    }}
    enriched = {"UNIT": {**plain["UNIT"],
        "day_open": 210.0, "bid_price": 212.1, "ask_price": 212.3,
        "nbbo_ts": "2026-10-08T14:29:59+00:00",
        "nbbo_source": "polygon_lastQuote",
    }}

    assert json.dumps(blq.to_worker_quotes(enriched), sort_keys=True) == json.dumps(
        blq.to_worker_quotes(plain), sort_keys=True,
    )
    assert not {"day_open", "bid_price", "ask_price", "nbbo_ts", "nbbo_source"} & (
        blq.to_worker_quotes(enriched)["UNIT"].keys()
    )


@pytest.mark.parametrize("evidence", [
    {},
    {"day_open": None, "bid_price": None, "ask_price": None,
     "nbbo_ts": None, "nbbo_source": None},
])
def test_private_b4_evidence_missingness_is_not_repaired_from_price_or_clock(evidence):
    raw = {"UNIT": {
        "price": 212.2, "prev_close": 210.0, "day_high": 213.0, "day_low": 209.0,
        "quote_ts": "2026-10-08T14:30:00+00:00",
        "quote_ts_synthetic": False, **evidence,
    }}

    private = blq.to_worker_quotes(raw, include_private_provenance=True)["UNIT"]

    for field in ("day_open", "bid_price", "ask_price", "nbbo_ts", "nbbo_source"):
        assert field in private and private[field] is None
    assert private["price"] == 212.2
    assert private["quote_ts"] == raw["UNIT"]["quote_ts"]


def test_build_private_b4_evidence_uses_the_existing_single_fetch(monkeypatch, tmp_path):
    evidence = {
        "day_open": 210.0, "bid_price": 212.1, "ask_price": 212.3,
        "nbbo_ts": "2026-10-08T14:29:59+00:00",
        "nbbo_source": "polygon_lastQuote",
    }
    raw = {"UNIT": {"price": 212.2, "quote_ts": "2026-10-08T14:30:00+00:00",
                    "quote_ts_synthetic": False, **evidence}}
    calls = []

    def fake_fetch_quotes(universe, *, offline=False, diag=None):
        calls.append((list(universe), offline))
        return raw

    monkeypatch.setattr(blq.live_quotes, "fetch_quotes", fake_fetch_quotes)

    result = blq.build(tmp_path, symbols=["UNIT"], include_private_provenance=True)

    assert calls == [(["UNIT"], False)]
    assert {field: result["quotes"]["UNIT"][field] for field in evidence} == evidence


def test_current_polygon_parser_missing_evidence_remains_null_in_private_snapshot():
    from datetime import datetime, timezone

    clock = datetime(2026, 10, 8, 14, 30, tzinfo=timezone.utc)
    raw = lq.parse_polygon_snapshot({"tickers": [{
        "ticker": "UNIT",
        "lastTrade": {"p": 212.2, "t": 1791469800000000000},
    }]}, now=clock)

    private = blq.to_worker_quotes(raw, include_private_provenance=True)["UNIT"]

    # Current main omits these keys; a later admitted producer may emit nulls.
    # Neither representation can manufacture measured evidence.
    for field in ("day_open", "bid_price", "ask_price", "nbbo_ts", "nbbo_source"):
        assert raw["UNIT"].get(field) is None
        assert field in private and private[field] is None
    assert private["quote_ts"] == raw["UNIT"]["quote_ts"]
    assert private["quote_ts_synthetic"] is False


def test_private_snapshot_cli_to_public_intraday_cli_keeps_b4_evidence_private(
    monkeypatch, tmp_path,
):
    import sys
    from scripts import build_intraday_flow_quotes as public_quotes

    evidence = {
        "day_open": 210.0, "bid_price": 212.1, "ask_price": 212.3,
        "nbbo_ts": "2026-10-08T14:29:59+00:00",
        "nbbo_source": "polygon_lastQuote",
    }
    raw = {"UNIT": {
        "price": 212.2, "prev_close": 210.0, "currency": "USD",
        "quote_ts": "2026-10-08T14:30:00+00:00",
        "quote_ts_synthetic": False, "source": "polygon",
        "price_basis": "trade", **evidence,
    }}
    calls = []

    def fake_fetch_quotes(universe, *, offline=False, diag=None):
        calls.append((list(universe), offline))
        return raw

    monkeypatch.setattr(blq.live_quotes, "fetch_quotes", fake_fetch_quotes)
    monkeypatch.setattr(blq.config, "load", lambda: {"live": {}})
    private_path = tmp_path / "private" / "quotes_full.json"
    default_path = tmp_path / "default" / "quotes.json"
    base_path = tmp_path / "base.json"
    public_path = tmp_path / "public" / "intraday_quotes.json"
    base_path.write_text(json.dumps({"leaders": [{"ticker": "UNIT"}]}))

    monkeypatch.setattr(sys, "argv", [
        "build_live_quotes", "--site", str(tmp_path), "--symbols", "UNIT",
        "--private-provenance", "--out", str(private_path),
    ])
    assert blq.main() is None
    private_bytes = private_path.read_bytes()
    private = json.loads(private_bytes)
    assert {field: private["quotes"]["UNIT"][field] for field in evidence} == evidence

    monkeypatch.setattr(sys, "argv", [
        "build_live_quotes", "--site", str(tmp_path), "--symbols", "UNIT",
        "--out", str(default_path),
    ])
    assert blq.main() is None
    default = json.loads(default_path.read_text())

    monkeypatch.setattr(sys, "argv", [
        "build_intraday_flow_quotes", "--base", str(base_path),
        "--quotes", str(private_path), "--out", str(public_path),
    ])
    assert public_quotes.main() == 0
    published = json.loads(public_path.read_text())

    assert published["quotes"]["UNIT"] == default["quotes"]["UNIT"]
    assert not set(evidence) & published["quotes"]["UNIT"].keys()
    assert published["ts"] == private["ts"]
    assert published["asof"] == private["asof"]
    assert private_path.read_bytes() == private_bytes
    assert calls == [(["UNIT"], False), (["UNIT"], False)]
