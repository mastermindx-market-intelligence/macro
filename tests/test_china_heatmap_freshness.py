"""Binding freshness contracts for the China A-share heatmap publication lane.

Incident replay (2026-09-15): ``china_search/closes.parquet`` recovered through
2026-09-15, but ``site/marketdata/china_heatmap.json`` remained at 2026-09-09
because asia-close never invoked its builder.  Generic render lanes occasionally
regenerated the JSON timestamp from whatever close panel happened to be present,
so every workflow stayed green while both public China surfaces served old tiles.
"""
from __future__ import annotations

import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "asia-close.yml"
NOW_DURING_2026_09_16_CN_SESSION = datetime(2026, 9, 16, 4, 0, tzinfo=timezone.utc)


def _checker():
    return importlib.import_module("scripts.check_china_heatmap_freshness")


def _write_closes(tmp_path: Path, sessions: list[str]) -> Path:
    path = tmp_path / "data" / "china_search" / "closes.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame(
        {"600000.SS": [10.0 + i for i in range(len(sessions))]},
        index=pd.to_datetime(sessions),
    ).to_parquet(path)
    return path


def _write_payload(
    tmp_path: Path,
    *,
    asof: str,
    market: str = "china",
    tickers: list[str] | None = None,
    generated_utc: str | None = None,
) -> Path:
    tickers = tickers or ["600000.SS"]
    path = tmp_path / "site" / "marketdata" / "china_heatmap.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "market": market,
                "source": "daily-close",
                "asof": asof,
                "generated_utc": generated_utc or f"{asof} 09:00",
                "n_tiles": len(tickers),
                "tiles": [{"t": ticker, "pct": 1.0} for ticker in tickers],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_members(tmp_path: Path, tickers: list[str]) -> Path:
    path = tmp_path / "data" / "china_search" / "members.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"name": [f"Name {i}" for i in range(len(tickers))]},
        index=pd.Index(tickers, name="ticker"),
    ).to_parquet(path)
    return path


def _write_page(tmp_path: Path, *, asof: str) -> Path:
    path = tmp_path / "site" / "china_heatmap.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<div id="hm-ssr"><span class="hx-pulse-when">'
        f"{asof}</span></div>"
        '<div data-hm-maps="marketdata/china_heatmap.json"></div>',
        encoding="utf-8",
    )
    return path


def test_incident_replay_rejects_2026_09_09_payload_over_2026_09_15_source(
    tmp_path: Path, capsys,
) -> None:
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-09", "2026-09-15"])
    payload = _write_payload(tmp_path, asof="2026-09-09")

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap stale::")
    assert "payload=2026-09-09" in line
    assert "source=2026-09-15" in line


def test_current_payload_and_current_source_pass(tmp_path: Path, capsys) -> None:
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-09", "2026-09-15"])
    payload = _write_payload(tmp_path, asof="2026-09-15")

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 0
    line = capsys.readouterr().out
    assert "China heatmap freshness OK" in line
    assert "payload=source=expected=2026-09-15" in line


def test_settle_boundary_advances_the_required_mainland_session(
    tmp_path: Path, capsys,
) -> None:
    """A long run must not carry yesterday across the 09:00 UTC settle edge."""
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-15"])
    payload = _write_payload(tmp_path, asof="2026-09-15")
    before = datetime(2026, 9, 16, 8, 59, tzinfo=timezone.utc)
    after = datetime(2026, 9, 16, 9, 1, tzinfo=timezone.utc)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=before,
    ) == 0
    assert "expected=2026-09-15" in capsys.readouterr().out

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=after,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap source stale::")
    assert "source=2026-09-15" in line
    assert "expected=2026-09-16" in line


def test_matching_payload_cannot_launder_a_stale_source(tmp_path: Path, capsys) -> None:
    """The final commit is ``if: always()``; source parity alone is not enough.

    When collection fails, both a stale payload and stale source can agree.  The
    guard must also bind them to the mainland completed-session clock so the
    always-running commit cannot publish a self-consistent old day.
    """
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-09"])
    payload = _write_payload(tmp_path, asof="2026-09-09")

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap source stale::")
    assert "source=2026-09-09" in line
    assert "expected=2026-09-15" in line


def test_missing_or_malformed_payload_fails_closed(tmp_path: Path, capsys) -> None:
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-15"])
    missing = tmp_path / "site" / "marketdata" / "china_heatmap.json"

    assert m.check_china_heatmap_freshness(
        payload_path=missing,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    assert "China heatmap unreadable" in capsys.readouterr().out

    malformed = _write_payload(tmp_path, asof="2026-09-15", market="hk")
    assert m.check_china_heatmap_freshness(
        payload_path=malformed,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    assert "China heatmap malformed" in capsys.readouterr().out


def test_checker_rejects_a_stale_server_rendered_page(tmp_path: Path, capsys) -> None:
    """No-JS, crawler, and failed-fetch users must not retain the prior session."""
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-15"])
    payload = _write_payload(tmp_path, asof="2026-09-15")
    page = _write_page(tmp_path, asof="2026-09-09")

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        page_path=page,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap page stale::")
    assert "page=2026-09-09" in line
    assert "payload=2026-09-15" in line


def test_checker_requires_a_crawlable_ssr_summary(tmp_path: Path, capsys) -> None:
    """A valid JSON may not leave no-JS and failed-fetch users on an empty shell."""
    m = _checker()
    closes = _write_closes(tmp_path, ["2026-09-15"])
    payload = _write_payload(tmp_path, asof="2026-09-15")
    page = tmp_path / "site" / "china_heatmap.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        '<div data-hm-maps="marketdata/china_heatmap.json"></div>',
        encoding="utf-8",
    )

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        page_path=page,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap page malformed::")
    assert "no #hm-ssr summary" in line


def test_current_session_requires_broad_tile_coverage(tmp_path: Path, capsys) -> None:
    """One fresh ticker must not launder a mostly prior-session heatmap."""
    m = _checker()
    tickers = [f"600{i:03d}.SS" for i in range(20)]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    prior = [10.0 + i for i in range(len(tickers))]
    latest = [11.0] + [float("nan")] * (len(tickers) - 1)
    pd.DataFrame(
        [prior, latest],
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
        columns=tickers,
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15", tickers=tickers)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap source incomplete::")
    assert "latest_session_coverage=1/20 (5.0%)" in line


def test_latest_session_requires_numeric_close_observations(
    tmp_path: Path, capsys,
) -> None:
    """A dated but nonnumeric row is not a real settled-close session."""
    m = _checker()
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        {"600000.SS": ["not-a-close"]},
        index=pd.to_datetime(["2026-09-15"]),
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15")

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    assert "China heatmap source unreadable" in capsys.readouterr().out


def test_current_session_requires_broad_source_representation(
    tmp_path: Path, capsys,
) -> None:
    """A tiny payload must not pass merely because every one of its tiles is fresh."""
    m = _checker()
    tickers = [f"600{i:03d}.SS" for i in range(20)]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        [[10.0 + i for i in range(len(tickers))]],
        index=pd.to_datetime(["2026-09-15"]),
        columns=tickers,
    ).to_parquet(closes)
    payload = _write_payload(
        tmp_path,
        asof="2026-09-15",
        tickers=[tickers[0]],
    )

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap source incomplete::")
    assert "source_representation=1/20 (5.0%)" in line


def test_membership_scope_ignores_current_extra_close_columns(
    tmp_path: Path, capsys,
) -> None:
    """Retained or benchmark columns outside the live universe must not dilute coverage."""
    m = _checker()
    members = [f"600{i:03d}.SS" for i in range(20)]
    extras = [f"900{i:03d}.SS" for i in range(20)]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        [[10.0] * (len(members) + len(extras))],
        index=pd.to_datetime(["2026-09-15"]),
        columns=members + extras,
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15", tickers=members)
    members_path = _write_members(tmp_path, members)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        members_path=members_path,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 0
    assert "source_representation=20/20 (100.0%)" in capsys.readouterr().out


def test_routine_suspensions_fit_the_heatmap_only_coverage_budget(
    tmp_path: Path, capsys,
) -> None:
    """A small routine suspension set stays publishable; a mostly stale row does not."""
    m = _checker()
    tickers = [f"600{i:03d}.SS" for i in range(100)]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        [[10.0] * 100, [11.0] * 96 + [float("nan")] * 4],
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
        columns=tickers,
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15", tickers=tickers)
    members_path = _write_members(tmp_path, tickers)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        members_path=members_path,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 0
    assert "latest_session_coverage=96/100 (96.0%)" in capsys.readouterr().out


def test_membership_denominator_allows_a_small_unpriced_tile_gap(
    tmp_path: Path, capsys,
) -> None:
    """Membership is the truth set; up to the explicit 5% gap may lack tiles."""
    m = _checker()
    members = [f"600{i:03d}.SS" for i in range(100)]
    rendered = members[:96]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        [[11.0] * 96 + [float("nan")] * 4],
        index=pd.to_datetime(["2026-09-15"]),
        columns=members,
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15", tickers=rendered)
    members_path = _write_members(tmp_path, members)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        members_path=members_path,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 0
    line = capsys.readouterr().out
    assert "latest_session_coverage=96/100 (96.0%)" in line
    assert "source_representation=96/96 (100.0%)" in line


def test_membership_truth_rejects_a_large_silently_dropped_tile_subset(
    tmp_path: Path, capsys,
) -> None:
    """A builder cannot make omissions invisible by shrinking ``n_tiles``.

    The separate whole-board breadth feed can cover ~5,000 names, but the
    binding heatmap universe is ``china_search/members.parquet``.  When that
    curated universe contains 100 names, a payload with only 80 current tiles
    is incomplete even though every rendered tile has a fresh close.
    """
    m = _checker()
    members = [f"600{i:03d}.SS" for i in range(100)]
    rendered = members[:80]
    closes = tmp_path / "data" / "china_search" / "closes.parquet"
    closes.parent.mkdir(parents=True)
    pd.DataFrame(
        [[11.0] * 100],
        index=pd.to_datetime(["2026-09-15"]),
        columns=members,
    ).to_parquet(closes)
    payload = _write_payload(tmp_path, asof="2026-09-15", tickers=rendered)
    members_path = _write_members(tmp_path, members)

    assert m.check_china_heatmap_freshness(
        payload_path=payload,
        closes_path=closes,
        members_path=members_path,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China heatmap source incomplete::")
    assert "latest_session_coverage=80/100 (80.0%)" in line
    assert "source_representation=80/100 (80.0%)" in line


def test_builder_refuses_to_overwrite_with_a_stale_china_source(
    tmp_path: Path, monkeypatch,
) -> None:
    """Generic render lanes must not recreate a stale JSON with a fresh timestamp."""
    import pytest
    from scripts import build_market_heatmap as builder

    closes = pd.DataFrame(
        {"600000.SS": [10.0, 10.2]},
        index=pd.to_datetime(["2026-09-08", "2026-09-09"]),
    )
    constituents = pd.DataFrame(
        {"name": ["Bank A"], "sector": ["Financial Services"]},
        index=pd.Index(["600000.SS"], name="ticker"),
    )
    monkeypatch.setitem(
        builder._LOADERS,
        "china",
        lambda: (
            constituents,
            closes,
            {"600000.SS": 1.0e12},
            {},
            {"600000.SS": "银行甲"},
        ),
    )
    monkeypatch.setattr(builder, "_board_breadth", lambda market: None)
    site = tmp_path / "site"

    with pytest.raises(RuntimeError, match="source=2026-09-09.*expected=2026-09-15"):
        builder.build(
            "china",
            site=site,
            generated_utc="2026-09-16 04:00",
            now=NOW_DURING_2026_09_16_CN_SESSION,
        )
    assert not (site / "marketdata" / "china_heatmap.json").exists()


def test_generic_render_never_regresses_a_newer_existing_china_session(
    tmp_path: Path, monkeypatch,
) -> None:
    """An inferior checkout cannot overwrite a newer already-published map.

    Asia may legitimately publish a source session ahead of the pre-settle
    exchange floor. A generic render whose checkout still ends one session
    earlier must fail closed instead of treating the newer JSON as
    "unverifiable" and rewriting it backward.
    """
    import pytest
    from scripts import build_market_heatmap as builder

    ticker = "600000.SS"
    constituents = pd.DataFrame(
        {"name": ["Bank A"], "sector": ["Financial Services"]},
        index=pd.Index([ticker], name="ticker"),
    )
    closes_by_session = {
        "2026-09-15": pd.DataFrame(
            {ticker: [10.0, 10.2]},
            index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
        ),
        "2026-09-14": pd.DataFrame(
            {ticker: [9.8, 10.0]},
            index=pd.to_datetime(["2026-09-11", "2026-09-14"]),
        ),
    }
    selected = {"session": "2026-09-15"}
    monkeypatch.setitem(
        builder._LOADERS,
        "china",
        lambda: (
            constituents,
            closes_by_session[selected["session"]],
            {ticker: 1.0e12},
            {},
            {ticker: "银行甲"},
        ),
    )
    monkeypatch.setattr(builder, "_board_breadth", lambda market: None)
    site = tmp_path / "site"
    output = site / "marketdata" / "china_heatmap.json"

    newer = builder.build(
        "china",
        site=site,
        generated_utc="2026-09-15 07:30",
        now=datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
    )
    newer_bytes = output.read_bytes()
    assert newer["asof"] == "2026-09-15"

    selected["session"] = "2026-09-14"
    with pytest.raises(RuntimeError, match="existing=2026-09-15.*candidate=2026-09-14"):
        builder.build(
            "china",
            site=site,
            generated_utc="2026-09-15 08:00",
            now=datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc),
        )

    assert output.read_bytes() == newer_bytes
    assert json.loads(output.read_text(encoding="utf-8"))["asof"] == "2026-09-15"


def test_current_china_rebuild_does_not_churn_generated_timestamp(
    tmp_path: Path, monkeypatch,
) -> None:
    """The post-rebase repair pass is a no-op when semantic output is current."""
    from scripts import build_market_heatmap as builder

    closes = pd.DataFrame(
        {"600000.SS": [10.0, 10.2]},
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
    )
    constituents = pd.DataFrame(
        {"name": ["Bank A"], "sector": ["Financial Services"]},
        index=pd.Index(["600000.SS"], name="ticker"),
    )
    monkeypatch.setitem(
        builder._LOADERS,
        "china",
        lambda: (
            constituents,
            closes,
            {"600000.SS": 1.0e12},
            {},
            {"600000.SS": "银行甲"},
        ),
    )
    monkeypatch.setattr(builder, "_board_breadth", lambda market: None)
    site = tmp_path / "site"
    output = site / "marketdata" / "china_heatmap.json"

    first = builder.build(
        "china",
        site=site,
        generated_utc="2026-09-16 04:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
        render_page=True,
    )
    first_bytes = output.read_bytes()
    page = site / "china_heatmap.html"
    first_page_bytes = page.read_bytes()
    second = builder.build(
        "china",
        site=site,
        generated_utc="2026-09-16 05:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
        render_page=True,
    )

    assert output.read_bytes() == first_bytes
    assert page.read_bytes() == first_page_bytes
    assert first["generated_utc"] == second["generated_utc"] == "2026-09-16 04:00"


def test_invalid_existing_generation_stamp_is_rewritten(
    tmp_path: Path, monkeypatch,
) -> None:
    """A same-session no-op may preserve only a plausible prior build receipt."""
    from scripts import build_market_heatmap as builder

    closes = pd.DataFrame(
        {"600000.SS": [10.0, 10.2]},
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
    )
    constituents = pd.DataFrame(
        {"name": ["Bank A"], "sector": ["Financial Services"]},
        index=pd.Index(["600000.SS"], name="ticker"),
    )
    monkeypatch.setitem(
        builder._LOADERS,
        "china",
        lambda: (
            constituents,
            closes,
            {"600000.SS": 1.0e12},
            {},
            {"600000.SS": "银行甲"},
        ),
    )
    monkeypatch.setattr(builder, "_board_breadth", lambda market: None)
    site = tmp_path / "site"
    output = site / "marketdata" / "china_heatmap.json"
    builder.build(
        "china", site=site, generated_utc="2026-09-16 04:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
    )
    poisoned = json.loads(output.read_text(encoding="utf-8"))
    poisoned["generated_utc"] = "2099-01-01 00:00"
    output.write_text(json.dumps(poisoned), encoding="utf-8")

    repaired = builder.build(
        "china", site=site, generated_utc="2026-09-16 04:30",
        now=NOW_DURING_2026_09_16_CN_SESSION,
    )
    assert repaired["generated_utc"] == "2026-09-16 04:30"
    assert json.loads(output.read_text(encoding="utf-8"))["generated_utc"] == "2026-09-16 04:30"


def test_builder_renders_current_standalone_ssr_from_the_same_payload(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    from scripts import build_market_heatmap as builder

    ticker = "600000.SS"
    closes = pd.DataFrame(
        {ticker: [10.0, 10.2]},
        index=pd.to_datetime(["2026-09-14", "2026-09-15"]),
    )
    constituents = pd.DataFrame(
        {"name": ["Bank A"], "sector": ["Financial Services"]},
        index=pd.Index([ticker], name="ticker"),
    )
    monkeypatch.setitem(
        builder._LOADERS,
        "china",
        lambda: (constituents, closes, {ticker: 1.0e12}, {}, {ticker: "银行甲"}),
    )
    monkeypatch.setattr(builder, "_board_breadth", lambda market: None)
    site = tmp_path / "site"

    payload = builder.build(
        "china",
        site=site,
        generated_utc="2026-09-16 04:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
        render_page=True,
    )
    page = site / "china_heatmap.html"
    html = page.read_text(encoding="utf-8")
    assert 'class="hx-pulse-when">2026-09-15</span>' in html
    assert "marketdata/china_heatmap.json" in html

    closes_path = tmp_path / "data" / "china_search" / "closes.parquet"
    closes_path.parent.mkdir(parents=True, exist_ok=True)
    closes.to_parquet(closes_path)
    members_path = _write_members(tmp_path, [ticker])
    m = _checker()
    assert m.check_china_heatmap_freshness(
        payload_path=site / "marketdata" / "china_heatmap.json",
        closes_path=closes_path,
        members_path=members_path,
        page_path=page,
        now=NOW_DURING_2026_09_16_CN_SESSION,
    ) == 0
    assert payload["asof"] == "2026-09-15"
    assert "page_ssr=2026-09-15" in capsys.readouterr().out


def test_build_all_forwards_one_frozen_now_to_every_market(monkeypatch, tmp_path: Path) -> None:
    from scripts import build_market_heatmap as builder

    seen: list[tuple[str, datetime | None]] = []

    def fake_build(market, site=None, *, generated_utc=None, now=None, render_page=False):
        seen.append((market, now))
        return {"market": market}

    monkeypatch.setattr(builder, "build", fake_build)
    result = builder.build_all(
        tmp_path,
        generated_utc="2026-09-16 04:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
    )
    assert seen == [
        ("china", NOW_DURING_2026_09_16_CN_SESSION),
        ("hk", NOW_DURING_2026_09_16_CN_SESSION),
        ("canada", NOW_DURING_2026_09_16_CN_SESSION),
    ]
    assert set(result) == {"china", "hk", "canada"}


def test_asia_lane_owns_heatmap_without_blocking_other_markets() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    commit_data = workflow.index("name: commit collected asia data")
    heatmap = workflow.index("name: build + verify China A-share heatmap")
    heatmap_end = workflow.index("name: timings band — build-china", heatmap)
    dashboard = workflow.index("name: build china a-share dashboard", heatmap_end)
    block = workflow[heatmap:heatmap_end]

    assert commit_data < heatmap < heatmap_end < dashboard
    assert "continue-on-error: true" in block
    assert 'marker="$RUNNER_TEMP/china-heatmap-failed"' in block
    assert 'heatmap_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"' in block
    assert 'china-heatmap-now' not in block
    assert '--market china --render-page --now "$heatmap_now"' in block
    assert 'scripts.check_china_heatmap_freshness --now "$heatmap_now"' in block
    assert 'touch "$marker"' in block
    assert "git checkout HEAD -- site/marketdata/china_heatmap.json site/china_heatmap.html" in block
    assert "exit 1" in block


def test_asia_broad_publishers_exclude_options_narrow_roots_around_staging() -> None:
    """Asia must never acquire the Options PIT/campaign roots owned by narrow publishers."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    exclusion = "bash scripts/ci/options_signal_nightly.sh exclude-broad"

    collected_start = workflow.index("name: commit collected asia data")
    collected_end = workflow.index("name: build + verify China A-share heatmap", collected_start)
    collected = workflow[collected_start:collected_end]
    collected_stage = collected.index("git add data/ site/qledger/")
    collected_exclusions = [
        match.start() for match in re.finditer(exclusion, collected)
    ]
    assert len(collected_exclusions) == 2
    assert collected_exclusions[0] < collected_stage < collected_exclusions[1]

    output_start = workflow.index("name: commit engine outputs")
    output_end = workflow.index("name: publish CN/HK stores to R2", output_start)
    output = workflow[output_start:output_end]
    output_stage = output.index("git add data/ site/")
    output_exclusions = [
        match.start() for match in re.finditer(exclusion, output)
    ]
    assert len(output_exclusions) == 2
    assert output_exclusions[0] < output_stage < output_exclusions[1]


def test_always_commit_rechecks_before_the_no_change_early_exit() -> None:
    """Crossing 09:00 must be caught even when no engine bytes changed.

    The commit step exits early when broad staging is empty.  Therefore the
    current-clock heatmap check and heatmap-only rollback must happen before
    both staging and the cached-diff early exit, without aborting unrelated
    China/HK publication.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("name: commit engine outputs")
    end = workflow.index("name: publish CN/HK stores to R2", start)
    block = workflow[start:end]
    stage = "git add data/ site/"
    no_change = "if git diff --cached --quiet; then echo \"no engine output changes\"; exit 0; fi"
    check = 'python -m scripts.check_china_heatmap_freshness --now "$heatmap_now"'
    restore = "git checkout HEAD -- site/marketdata/china_heatmap.json site/china_heatmap.html"
    pre_stage = block[:block.index(stage)]

    assert "if: always()" in block
    assert 'heatmap_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"' in pre_stage
    assert check in pre_stage
    assert 'touch "$RUNNER_TEMP/china-heatmap-failed"' in pre_stage
    assert restore in pre_stage
    assert "exit 1" not in pre_stage[pre_stage.index(check):]
    assert block.index(check) < block.index(stage) < block.index(no_change)


def test_post_rebase_tree_resamples_the_session_clock_and_isolates_failure() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("name: commit engine outputs")
    end = workflow.index("name: publish CN/HK stores to R2", start)
    block = workflow[start:end]
    rebase = block.index("git pull --rebase --autostash -X theirs origin main")
    push = block.index("if push_do", rebase)
    post_rebase = block[rebase:push]

    # A long run can cross the 09:00 UTC mainland-settle boundary.  Freeze one
    # clock only for this build/check pair; never reuse the job-start clock.
    assert 'heatmap_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"' in post_rebase
    assert 'cat "$RUNNER_TEMP/china-heatmap-now"' not in post_rebase
    assert '--market china --render-page --now "$heatmap_now"' in post_rebase
    assert 'scripts.check_china_heatmap_freshness --now "$heatmap_now"' in post_rebase
    assert 'rm -f "$RUNNER_TEMP/china-heatmap-failed"' in post_rebase
    assert 'touch "$RUNNER_TEMP/china-heatmap-failed"' in post_rebase
    # HEAD contains this run's engine commit and may already carry a heatmap that
    # became stale while the long job crossed the settle boundary. Roll back to
    # post-fetch origin/main and commit that compensation before any push.
    restore = "git checkout origin/main -- site/marketdata/china_heatmap.json site/china_heatmap.html"
    stage = "git add site/marketdata/china_heatmap.json site/china_heatmap.html"
    compensate = 'git commit -m "render-heal: hold stale China heatmap at origin main"'
    assert restore in post_rebase
    assert stage in post_rebase
    assert compensate in post_rebase
    assert "git checkout HEAD -- site/marketdata/china_heatmap.json site/china_heatmap.html" not in post_rebase
    assert post_rebase.index(restore) < post_rebase.index(stage) < post_rebase.index(compensate)


def test_heatmap_failure_turns_the_job_red_only_after_publish_tail() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    publish = workflow.index("name: publish CN/HK stores to R2")
    failure = workflow.index("name: fail if China heatmap missed settled close", publish)
    timings = workflow.index("name: timings ledger + 85% budget tripwire", failure)
    end = workflow.index("\n  ths_rescrape:", timings)
    block = workflow[failure:end]

    # The failure is delayed until after the publication tail, while the final
    # always-running timings step still records the failed night.
    assert publish < failure < timings
    assert "if: always()" in block
    assert 'china-heatmap-failed' in block
    assert "exit 1" in block


def test_generic_render_owner_reaches_the_guarded_builder() -> None:
    source = (ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "from scripts.build_market_heatmap import build_all as build_market_heatmaps" in source
    assert "_hm_payloads = build_market_heatmaps(site, generated_utc=generated)" in source


def test_ci_routes_checker_and_regression_suite_to_the_heatmap_owner() -> None:
    """Checker-only and test-only edits must still select the owning CI pack."""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    legacy = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")

    assert '- "scripts/check_china_heatmap_freshness.py"' in workflow
    assert '- "tests/test_china_heatmap_freshness.py"' in workflow
    owner_start = legacy.index("  china-board-breadth:")
    owner_end = legacy.index("\n  china-search-universe:", owner_start)
    owner = legacy[owner_start:owner_end]
    assert '"scripts/check_china_heatmap_freshness.py"' in legacy
    assert "tests/test_china_heatmap_freshness.py" in owner


def test_dag_declares_settled_heatmap_producer_and_checker() -> None:
    """DAG authority must match the two new live Asia workflow modules."""
    dag = (ROOT / "config" / "dag.yml").read_text(encoding="utf-8")
    start = dag.index("- workflow: .github/workflows/asia-close.yml")
    end = dag.index("\n  # ── engine-render.yml", start)
    lane = dag[start:end]

    build = lane.index("module: scripts.build_market_heatmap")
    check = lane.index("module: scripts.check_china_heatmap_freshness")
    spine = lane.index("module: scripts.build_china")

    assert build < check < spine
    assert lane.count("module: scripts.build_market_heatmap") == 1
    assert lane.count("module: scripts.check_china_heatmap_freshness") == 1
