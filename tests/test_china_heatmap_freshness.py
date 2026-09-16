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
    )
    first_bytes = output.read_bytes()
    second = builder.build(
        "china",
        site=site,
        generated_utc="2026-09-16 05:00",
        now=NOW_DURING_2026_09_16_CN_SESSION,
    )

    assert output.read_bytes() == first_bytes
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


def test_asia_lane_builds_heatmap_after_data_commit_before_china_consumers() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    commit_data = workflow.index("name: commit collected asia data")
    heatmap = workflow.index("name: build + verify China A-share heatmap")
    heatmap_end = workflow.index("name: timings band — build-china", heatmap)
    dashboard = workflow.index("name: build china a-share dashboard", heatmap_end)
    block = workflow[heatmap:heatmap_end]

    assert commit_data < heatmap < heatmap_end < dashboard
    build = "python -m scripts.build_market_heatmap --market china"
    check = "python -m scripts.check_china_heatmap_freshness"
    assert build in block
    assert check in block
    assert block.index(build) < block.index(check)
    assert "continue-on-error" not in block
    assert "|| true" not in block


def test_always_commit_rechecks_heatmap_before_broad_staging() -> None:
    """A failed/skipped upstream step must not be laundered by ``if: always()``."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("name: commit engine outputs")
    end = workflow.index("name: publish CN/HK stores to R2", start)
    block = workflow[start:end]
    guard = "python -m scripts.check_china_heatmap_freshness"
    stage = "git add data/ site/"

    assert "if: always()" in block
    assert guard in block
    assert block.index(guard) < block.index(stage)
    guard_line = next(line for line in block.splitlines() if guard in line)
    assert "||" not in guard_line


def test_post_rebase_tree_is_rebuilt_and_rechecked_before_push() -> None:
    """The tree pushed after a race is the rebased tree, not the pre-commit tree."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("name: commit engine outputs")
    end = workflow.index("name: publish CN/HK stores to R2", start)
    block = workflow[start:end]
    rebase = block.index("git pull --rebase --autostash -X theirs origin main")
    push = block.index("if push_do", rebase)
    post_rebase = block[rebase:push]
    build = "python -m scripts.build_market_heatmap --market china"
    check = "python -m scripts.check_china_heatmap_freshness"

    assert build in post_rebase
    assert check in post_rebase
    assert post_rebase.index(build) < post_rebase.index(check)
    assert "|| true" not in next(
        line for line in post_rebase.splitlines() if build in line
    )
    assert "|| true" not in next(
        line for line in post_rebase.splitlines() if check in line
    )
