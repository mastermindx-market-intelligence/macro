"""The Tushare plane must not be able to go cold silently.

The failure this guards is not "a collector broke" — it is that NOTHING SAID SO.
tushare_client returns None for every failure it has, callers omit the leg rather
than write a zero, and asia-close's collector normally degrades per source. Each
of those is individually correct; together they let flow_hist and moneyflow freeze
at 2026-07-24 and still render on flow_velocity.html on 2026-08-06. Store age is
not root-cause evidence, so the advisory must route operators to the adapter's
transport-vs-auth receipt instead of guessing that the token or tier is wrong.
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.check_tushare_freshness import (  # noqa: E402
    MAX_SESSIONS_BEHIND,
    evaluate,
    selftest,
    sessions_between,
)

WORKFLOW = _ROOT / ".github" / "workflows" / "asia-close.yml"


def test_selftest_passes() -> None:
    assert selftest() == 0


def test_the_real_incident_is_caught() -> None:
    """2026-07-24 data still being served on 2026-08-06 must read stale."""
    status, behind = evaluate("2026-07-24", date(2026, 8, 6))
    assert status == "stale"
    assert behind > MAX_SESSIONS_BEHIND, f"only {behind} sessions behind — threshold too slack"


def test_check_is_anchored_to_the_calendar_not_to_the_store_itself() -> None:
    """The property the whole tripwire rests on.

    A self-relative check — newest row vs the store's own newest row, or vs a
    sibling that froze in the same outage — reads FRESH during a total outage,
    because a frozen feed is perfectly self-consistent. Only an anchor that keeps
    advancing on its own can see a gap. So the same store date must flip from
    fresh to stale purely because the expected session moved forward.
    """
    frozen = "2026-07-24"
    assert evaluate(frozen, date(2026, 7, 27))[0] == "fresh"
    assert evaluate(frozen, date(2026, 8, 6))[0] == "stale"


def test_a_healthy_plane_does_not_trip_over_a_weekend() -> None:
    """Friday data read on Monday must stay quiet, or the warning becomes noise."""
    assert evaluate("2026-07-31", date(2026, 8, 3))[0] == "fresh"   # Fri -> Mon
    assert evaluate("2026-08-05", date(2026, 8, 6))[0] == "fresh"   # yesterday


def test_unreadable_dates_never_read_fresh() -> None:
    """Fail loud, not open: a store whose date column changed shape is not 'fine'."""
    assert evaluate(None, date(2026, 8, 6))[0] == "absent"
    assert evaluate("not-a-date", date(2026, 8, 6))[0] == "stale"
    assert sessions_between("", date(2026, 8, 6)) > MAX_SESSIONS_BEHIND


def test_tripwire_runs_in_the_lane_that_collects_the_data() -> None:
    """A guard nobody invokes is decoration — pin the wiring, not just the script."""
    y = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/check_tushare_freshness.py" in y, \
        "asia-close no longer runs the tripwire — the plane can go cold silently again"
    assert y.index("scripts.collect --group asia") < y.index("check_tushare_freshness"), \
        "the tripwire must run AFTER collection, or it grades the previous run's stores"


def test_annotation_starts_the_line_and_is_flushed(capsys: pytest.CaptureFixture[str]) -> None:
    """GitHub drops an annotation that does not start its line.

    Every builder here logs with a prefixing formatter, so `log.warning("::warning …")`
    emits `WARNING ::warning …` and vanishes from the Actions summary while reviewing
    as a live alarm. This asserts the emitted shape, not the wording.
    """
    src = (_ROOT / "scripts" / "check_tushare_freshness.py").read_text(encoding="utf-8")
    assert not re.search(r"log(?:ger)?\.\w+\(\s*f?[\"']::", src), \
        "annotation emitted through a logger — GitHub will silently drop it"
    assert 'flush=True' in src, "stdout is block-buffered when piped in CI"

    import scripts.check_tushare_freshness as m

    monkey = [("tushare/flow_hist.parquet", "tushare_moneyflow")]
    real_stores, real_latest = m.STORES, m._latest_date
    m.STORES = tuple(monkey)
    m._latest_date = lambda rel: "2026-07-24"
    try:
        m.run()
    finally:
        m.STORES, m._latest_date = real_stores, real_latest
    line = [ln for ln in capsys.readouterr().out.splitlines() if "::warning" in ln]
    assert line, "no annotation emitted for a stale plane"
    assert line[0].startswith("::warning"), f"annotation must start the line, got: {line[0][:40]!r}"
    assert "data/run_status.json" in line[0]
    assert "tushare-transport-outage" in line[0]
    assert "tushare-auth-rejected" in line[0]
    assert "Do not rotate TUSHARE_TOKEN from store age alone" in line[0]
    assert "Check TUSHARE_TOKEN is set and the membership/积分 tier" not in line[0]


def test_china_search_core_gate_catches_the_2026_09_09_freeze(monkeypatch, capsys):
    import scripts.check_tushare_freshness as m

    monkeypatch.setattr(m, "_latest_date", lambda rel: "2026-09-09")
    now = datetime(2026, 9, 14, 4, 0, tzinfo=timezone.utc)

    assert m.check_china_search_core(now) == 3
    line = capsys.readouterr().out
    assert line.startswith("::error title=China core price store stale::")
    assert "expected mainland session 2026-09-11" in line
    assert "2 sessions behind" in line


def test_china_search_core_gate_accepts_current_and_ahead_store(monkeypatch, capsys):
    import scripts.check_tushare_freshness as m

    now = datetime(2026, 9, 14, 4, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(m, "_latest_date", lambda rel: "2026-09-11")
    assert m.check_china_search_core(now) == 0
    assert "freshness OK" in capsys.readouterr().out

    monkeypatch.setattr(m, "_latest_date", lambda rel: "2026-09-14")
    assert m.check_china_search_core(now) == 0
    line = capsys.readouterr().out
    assert line.startswith("::warning title=China core price store ahead of exchange clock::")


def test_latest_date_reads_wide_tz_aware_close_index(monkeypatch, tmp_path):
    import pandas as pd
    import scripts.check_tushare_freshness as m

    store = tmp_path / "china_search" / "closes.parquet"
    store.parent.mkdir(parents=True)
    pd.DataFrame(
        {"600000.SS": [10.0, 10.2]},
        index=pd.DatetimeIndex(["2026-09-10 00:00", "2026-09-11 00:00"],
                               tz="Asia/Shanghai"),
    ).to_parquet(store)
    monkeypatch.setattr(m.config, "data_dir", lambda: tmp_path)

    assert m._latest_date("china_search/closes.parquet") == "2026-09-11"


def test_collect_asia_group_uses_the_binding_core_health_result(monkeypatch):
    import inspect
    import scripts.collect as collect
    import scripts.check_tushare_freshness as freshness

    monkeypatch.setattr(freshness, "check_china_search_core", lambda now=None: 3)
    assert collect._required_group_health("asia") == 3
    assert collect._required_group_health("us") == 0
    source = inspect.getsource(collect.main)
    call = source.rindex("_required_group_health(")
    assert call > source.index("_src_reg_run()"),         "required-store health must run after every post-collect task"
    assert call < source.rindex("return 0 if ok > 0 else 1"),         "the binding result must decide the collect command's final exit"


def test_mainland_session_clock_survives_utc_to_shanghai_midnight(monkeypatch, capsys):
    from lib import cn_calendar
    import scripts.check_tushare_freshness as m

    boundary = datetime(2026, 9, 11, 16, 0, tzinfo=timezone.utc)
    assert cn_calendar.expected_last_session(boundary).isoformat() == "2026-09-11"
    monkeypatch.setattr(m, "_latest_date", lambda rel: "2026-09-11")
    assert m.check_china_search_core(boundary) == 0
    assert "expected mainland session 2026-09-11" in capsys.readouterr().out


def test_collect_asia_binding_can_only_be_bypassed_explicitly(monkeypatch, capsys):
    import scripts.collect as collect

    monkeypatch.setattr(
        "scripts.check_tushare_freshness.check_china_search_core",
        lambda now=None: 3,
    )
    assert collect._required_group_health("asia", skip_quality=False) == 3
    assert collect._required_group_health("asia", skip_quality=True) == 0
    assert "BYPASS" in capsys.readouterr().out


def test_asia_workflow_propagates_collect_failure_before_commit_and_build():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
                "asia-close.yml").read_text(encoding="utf-8")
    collect_start = workflow.index("name: collect China/HK data")
    collect_end = workflow.index("name: timings band — collect-commit-push", collect_start)
    commit_start = workflow.index("name: commit collected asia data", collect_end)
    build_start = workflow.index("name: build china a-share dashboard", commit_start)
    collect_block = workflow[collect_start:collect_end]
    downstream = workflow[commit_start:build_start + 100]

    assert "run: python -m scripts.collect --group asia" in collect_block
    assert "--skip-quality" not in collect_block
    assert "continue-on-error" not in collect_block
    assert "|| true" not in collect_block
    assert "if: always()" not in downstream
    assert collect_start < commit_start < build_start
