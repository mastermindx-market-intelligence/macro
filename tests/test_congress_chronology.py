"""Congress disclosure availability at a fixed cutoff, through native consumers.

Synthetic Parquet fixtures isolate configuration, time and ledger output only.
They do not assert historical outcome availability or production incidence.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import Environment

from engine import congress_members as members
from scripts import build_congress as builder

ASOF = date(2026, 11, 11)
SOURCE = Path(__file__).resolve().parents[1]


def trade(ticker="BASE", member="Fixture Current", party="D",
          tx="2026-10-01", report="2026-11-10", excess=0):
    return {
        "Ticker": ticker, "Representative": member,
        "BioGuideID": member.replace(" ", ""), "Party": party, "House": "House",
        "Transaction": "Purchase", "Range": "$1,001 - $15,000", "Amount": 8000,
        "TransactionDate": tx, "ReportDate": report, "ExcessReturn": excess,
    }


@pytest.fixture
def native_inputs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    parquet = data / "quiver" / "congress.parquet"
    parquet.parent.mkdir(parents=True)
    (tmp_path / "site").mkdir()
    (tmp_path / "templates").symlink_to(SOURCE / "templates", target_is_directory=True)
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    monkeypatch.setattr(builder.config, "data_dir", lambda: data)

    def write(rows):
        frame = pd.DataFrame(rows)
        frame.to_parquet(parquet, index=False)
        return frame

    return write, tmp_path


@pytest.mark.parametrize("tx,report,expected", [
    ("2026-11-11", "2026-11-11", True),
    ("2026-10-01", "2026-11-10", True),
    (str(ASOF - timedelta(days=182)), "2026-11-10", True),
    (str(ASOF - timedelta(days=183)), "2026-11-10", False),
    ("2026-11-10", "2026-11-12", False),
    ("2026-10-01", "2026-12-11", False),
    ("2026-11-12", "2026-11-13", False),
    ("2026-12-11", "2026-12-12", False),
    ("2026-11-10", None, False),
    ("2026-11-10", "not-a-date", False),
    (None, "2026-11-10", False),
    ("not-a-date", "2026-11-10", False),
    ("2026-11-11", "2026-11-10", False),
], ids=[
    "same-day", "valid-delayed", "exact-182-day-boundary", "expired",
    "future-report-1d", "future-report-30d", "future-both-1d", "future-both-30d",
    "missing-report", "invalid-report", "missing-transaction",
    "invalid-transaction", "inverted-chronology",
])
def test_date_cases_admit_only_available_window(native_inputs, tx, report, expected):
    write, _ = native_inputs
    write([trade(tx=tx, report=report)])
    by_ticker, feed, total = builder._load_window(ASOF)
    assert ("BASE" in by_ticker) is expected
    assert len(feed) == total == 1  # No rejected source record is deleted.


def test_raw_feed_distinguishes_unknown_invalid_and_excluded(native_inputs):
    write, _ = native_inputs
    rows = [
        trade(),
        trade(member="Missing", report=None),
        trade(member="Malformed", report="not-a-date"),
        trade(member="Inverted", tx="2026-11-11", report="2026-11-10"),
        trade(member="Future", report="2026-11-12"),
    ]
    before = write(rows)
    by_ticker, feed, total = builder._load_window(ASOF)
    status = {r["representative"]: r["chronology_status"] for r in feed}
    assert status == {
        "Fixture Current": "eligible", "Missing": "unknown",
        "Malformed": "invalid", "Inverted": "invalid", "Future": "excluded",
    }
    assert total == len(feed) == len(rows)
    assert len(by_ticker["BASE"]) == 1
    malformed = next(r for r in feed if r["representative"] == "Malformed")
    assert malformed["report_date_raw"] == "not-a-date"
    # Neither reader modifies the source Parquet or the caller's DataFrame.
    members.compute(before, asof=ASOF)
    pd.testing.assert_frame_equal(before, pd.read_parquet(
        builder.config.data_dir() / "quiver" / "congress.parquet"
    ))


def test_member_reader_qualifies_its_independent_full_history():
    good = [trade(member="Fixture Valid", excess=0)]
    bad = [
        trade(member="Future", report="2026-11-12", excess=10),
        trade(member="Unknown", report=None, excess=10),
        trade(member="Invalid", report="not-a-date", excess=10),
        trade(member="Inverted", tx="2026-10-01", report="2026-09-30", excess=10),
        trade(member="MissingTx", tx=None, excess=10),
    ]
    stats = members.compute(pd.DataFrame(good + bad), asof=ASOF)
    assert list(stats) == ["FixtureValid"]
    valid = stats["FixtureValid"]
    assert valid.n_trades == valid.n_eff_valid == 1
    assert valid.n_hits == 0
    assert valid.er_mean == valid.er_median == 0  # Zero is valid, not missing.


def test_member_history_retains_valid_older_observations():
    row = trade(tx=str(ASOF - timedelta(days=300)), report="2026-11-10")
    stats = members.compute(pd.DataFrame([row]), asof=ASOF)
    assert stats["FixtureCurrent"].n_eff_valid == 1


def test_missing_date_columns_fail_closed_without_inventing_dates():
    row = trade()
    del row["ReportDate"]
    assert members.compute(pd.DataFrame([row]), asof=ASOF) == {}


def _native_run(rows, native_inputs, monkeypatch):
    write, root = native_inputs
    write(rows)
    context, snapshots = {}, []

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 11, 10, 38, tzinfo=timezone.utc)

    def env_factory(*args, **kwargs):
        env = Environment(*args, **kwargs)
        original_get = env.get_template

        def get_template(name, *a, **kw):
            template = original_get(name, *a, **kw)
            original_render = template.render

            def render(*args, **kwargs):
                if name == "congress_trades.html.j2":
                    context.update(kwargs)
                return original_render(*args, **kwargs)

            template.render = render
            return template

        env.get_template = get_template
        return env

    def snapshot(desk, rows, asof):
        snapshots.append({"desk": desk, "rows": rows, "asof": asof})
        return {"n_new": 0, "n_departed": 0}

    monkeypatch.setattr(builder, "datetime", Clock)
    monkeypatch.setattr(builder, "Environment", env_factory)
    monkeypatch.setattr(builder, "write_page", lambda p, s: p.write_text(s))
    monkeypatch.setattr(builder.desk_grader, "seed_notes", lambda: None)
    monkeypatch.setattr(builder.desk_grader, "snapshot_desk", snapshot)
    monkeypatch.setattr(builder.desk_grader, "compute", lambda *a: {})
    builder._SD_CACHE.clear()
    builder._ENTRY_CACHE.clear()
    output = root / "site" / "congress_trades.html"
    if output.exists():
        output.unlink()
    assert builder.main() == 0
    assert output.is_file()  # main() deliberately returns 0 even on failure.
    return context, snapshots, output.read_text()


def test_five_native_consumers_keep_the_complete_valid_control(native_inputs, monkeypatch):
    base = trade()
    scenarios = [
        [base],
        [base, trade(member="Fixture Future", party="R", report="2026-11-12")],
        [base, trade(ticker="FUTURE", member="Fixture Future", party="R",
                     tx="2026-12-11", report="2026-12-12")],
        [base, trade(member="Fixture Unknown", party="R", tx="2026-11-10", report=None)],
        [base] + [
            trade(ticker="FUTURE", member="Fixture Future", party="R",
                  tx=str(ASOF - timedelta(days=40 + i)), report="2026-11-12", excess=10)
            for i in range(8)
        ],
    ]
    results = [_native_run(rows, native_inputs, monkeypatch) for rows in scenarios]
    control, control_snapshots, _ = results[0]
    assert control["items"][0]["cluster_score"] == 41.3
    assert control["items"][0]["composite"] == 8.7
    for rows, (context, snapshots, html) in zip(scenarios, results):
        assert context["items"] == control["items"]
        assert context["member_leaderboard"] == control["member_leaderboard"]
        assert snapshots == control_snapshots
        assert context["summary"]["as_of"] == "2026-11-10"
        assert context["summary"]["cutoff_date"] == "2026-11-11"
        assert context["summary"]["n_bipartisan"] == 0
        assert len(context["feed"]) == len(rows)
        assert ">As of</span>" in html and ">截至</span>" in html
        assert 'class="mb-tier-proven">proven</span>' not in html
        assert 'data-chronology-status="eligible"' in html
        assert "Date check" in html and "日期校验" in html
    assert 'data-chronology-status="excluded"' in results[1][2]
    assert 'data-chronology-status="unknown"' in results[3][2]


def test_unknown_and_invalid_feed_does_not_manufacture_page_asof(native_inputs, monkeypatch):
    context, snapshots, html = _native_run([
        trade(member="Unknown", report=None),
        trade(member="Invalid", report="not-a-date"),
    ], native_inputs, monkeypatch)
    assert context["summary"]["as_of"] is None
    assert context["summary"]["cutoff_date"] == ASOF.isoformat()
    assert context["items"] == context["member_leaderboard"] == []
    assert snapshots[0]["rows"] == []
    assert "Unknown date" in html and "日期未知" in html
    assert "Invalid chronology" in html and "日期无效" in html
    assert "No eligible filing date" in html and "无可用披露日期" in html
    assert "not-a-date" in html


def test_calendar_dates_share_timezone_normalization(native_inputs):
    write, _ = native_inputs
    write([trade(tx="2026-10-01T12:00:00Z", report="2026-11-11T23:59:59Z")])
    by_ticker, _, _ = builder._load_window(ASOF)
    assert len(by_ticker["BASE"]) == 1


def test_numeric_date_is_invalid_not_unix_epoch(native_inputs):
    write, _ = native_inputs
    write([trade(tx=123, report=456)])
    by_ticker, feed, _ = builder._load_window(ASOF)
    assert not by_ticker
    assert feed[0]["chronology_status"] == "invalid"
    assert members.compute(pd.DataFrame([trade(tx=123, report=456)]), asof=ASOF) == {}
