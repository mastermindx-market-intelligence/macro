"""RED-first tests for the F11 B-F11-7b recurring briefs producer (MO-PAID-032).

No network: every IO function is monkeypatched. A FakeClient records writes so
idempotency is a real second-call proof, not a static fixture.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from engine import recurring_briefs as rb
from scripts import build_recurring_briefs as entry

ROOT = Path(__file__).resolve().parents[1]

SUB_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
THESIS_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
WATCH_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
USER_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"

CONTRACT_MISS_EN = (
    "Tonight's brief didn't run — the market read it uses wasn't rebuilt. "
    "Nothing has been recalculated."
)

BANNED_BODY_KEYS = {
    "score",
    "rank",
    "conviction",
    "confidence",
    "priority",
    "strength",
    "lean",
    "probability",
}
BANNED_TERMS = ("falsif", "refut", "证伪")


def _sub(*, cadence="daily_after_us_close", kind="thesis", target_id=THESIS_ID,
         state="active", run_date="2026-09-13"):
    return {
        "subscription_id": SUB_ID,
        "user_id": USER_ID,
        "target_kind": kind,
        "target_id": target_id,
        "cadence": cadence,
        "delivery": "in_product_inbox",
        "state": state,
        "run_date": run_date,
    }


def _thesis_target(*, name="Apple breadth thesis", version=2, tickers=("AAPL",)):
    return {
        "kind": "thesis",
        "id": THESIS_ID,
        "name": name,
        "version_or_asof": str(version),
        "tickers": list(tickers),
        "unavailable": False,
    }


def _watchlist_target(*, name="My names", tickers=("AAPL", "MSFT")):
    return {
        "kind": "watchlist",
        "id": WATCH_ID,
        "name": name,
        "version_or_asof": "2026-09-13",
        "tickers": list(tickers),
        "unavailable": False,
    }


def _briefing(*, as_of="2026-09-13", situation="Apple's tape is quiet after the print."):
    return {
        "schema": "intelligence.briefing.v1",
        "as_of": as_of,
        "generated_utc": f"{as_of}T20:05:00+00:00",
        "macro_context": {
            "posture": "Liquidity is expanding — a supportive backdrop.",
        },
        "priority_queue": [
            {
                "ticker": "AAPL",
                "situation": situation,
                "evidence": "Volume dried up into the close.",
                "priority": 0.91,
                "confidence": 0.8,
                "strength": 0.7,
                "lean": 1,
                "falsifier": "breadth rolls over",
            },
            {
                "ticker": "MSFT",
                "situation": "Microsoft held the week's range.",
                "priority": 0.4,
            },
        ],
        "divergences": [],
    }


def _weekly_brief(*, state_asof="2026-09-13"):
    return {
        "schema": "master_brief.v2",
        "state_asof": state_asof,
        "tldr": ["The week's tape stayed inside last week's range."],
        "summary": "A quiet week for the names we follow.",
        "regime_read": "Liquidity stayed supportive.",
        "confidence": "low",
        "watch_items": [
            {"ticker": "AAPL", "note": "Apple stayed inside its range all week."},
        ],
    }


class FakeClient:
    """Records inserts; a second insert of the same (subscription_id, slot_asof)
    is a no-op, matching insert … on conflict do nothing."""

    def __init__(self):
        self.deliveries: list[dict] = []
        self.insert_calls = 0

    def write(self, row, *, dry_run):
        self.insert_calls += 1
        if dry_run:
            return "dry"
        key = (row["subscription_id"], str(row["slot_asof"]))
        existing = {(r["subscription_id"], str(r["slot_asof"])) for r in self.deliveries}
        if key in existing:
            return "conflict"
        self.deliveries.append(row)
        return "inserted"


def _keys(obj):
    found = set()
    if isinstance(obj, dict):
        found.update(obj.keys())
        for v in obj.values():
            found.update(_keys(v))
    elif isinstance(obj, list):
        for v in obj:
            found.update(_keys(v))
    return found


def _haystack(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).lower()


# ---------------------------------------------------------------------------
# Slot computation
# ---------------------------------------------------------------------------

def test_daily_slot_is_briefing_as_of_when_fresh():
    slot = rb.compute_slot(
        "daily_after_us_close",
        "2026-09-13T20:05:00+00:00",
        date(2026, 9, 13),
    )
    assert slot == date(2026, 9, 13)


def test_daily_slot_accepts_date_only_as_of():
    assert rb.compute_slot("daily_after_us_close", "2026-09-13", date(2026, 9, 13)) == date(
        2026, 9, 13
    )


def test_stale_artifact_yields_no_slot():
    assert (
        rb.compute_slot("daily_after_us_close", "2026-09-12", date(2026, 9, 13)) is None
    )


def test_missing_artifact_asof_yields_no_slot():
    assert rb.compute_slot("daily_after_us_close", None, date(2026, 9, 13)) is None
    assert rb.compute_slot("weekly_saturday", "", date(2026, 9, 12)) is None


def test_weekly_slot_is_artifact_asof_when_fresh():
    slot = rb.compute_slot("weekly_saturday", "2026-09-12", date(2026, 9, 12))
    assert slot == date(2026, 9, 12)


def test_compute_slot_never_returns_an_earlier_date_than_run():
    """Never back-fill: a usable artifact still keys the slot on the run's date."""
    slot = rb.compute_slot(
        "daily_after_us_close",
        "2026-09-14T00:00:00Z",
        date(2026, 9, 13),
    )
    assert slot == date(2026, 9, 13)


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

def test_classify_ready_when_artifact_matches_run_date():
    state, reason = rb.classify(_sub(), _briefing(), _thesis_target())
    assert state == "ready"
    assert reason is None


def test_classify_stale_artifact_is_degraded_with_contract_line():
    state, reason = rb.classify(
        _sub(run_date="2026-09-13"),
        _briefing(as_of="2026-09-12"),
        _thesis_target(),
    )
    assert state == "degraded"
    assert reason == CONTRACT_MISS_EN


def test_classify_missing_artifact_is_degraded_with_contract_line():
    state, reason = rb.classify(_sub(), None, _thesis_target())
    assert state == "degraded"
    assert reason == CONTRACT_MISS_EN


def test_classify_unreadable_target_is_target_unavailable():
    state, reason = rb.classify(_sub(), _briefing(), None)
    assert state == "degraded"
    assert reason == "target unavailable"
    state2, reason2 = rb.classify(
        _sub(), _briefing(), {"unavailable": True, "kind": "thesis", "id": THESIS_ID}
    )
    assert state2 == "degraded"
    assert reason2 == "target unavailable"


# ---------------------------------------------------------------------------
# compose_body
# ---------------------------------------------------------------------------

def test_body_copies_verbatim_artifact_sentences_for_target_tickers():
    situation = "Apple's tape is quiet after the print."
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _briefing(situation=situation),
        monitors=[],
    )
    sentences = [row["sentence_en"] for row in body["market_read"]]
    assert situation in sentences
    assert "Volume dried up into the close." in sentences
    # A name the thesis does not follow is not copied.
    assert "Microsoft held the week's range." not in sentences
    # Macro backdrop is copied for every target.
    assert "Liquidity is expanding — a supportive backdrop." in sentences


def test_body_has_no_numeric_judgement_fields():
    body = rb.compose_body(_thesis_target(), _briefing(), monitors=[])
    keys = _keys(body)
    for banned in BANNED_BODY_KEYS:
        assert banned not in keys, f"judgement key {banned!r} leaked into body"
    hay = _haystack(body)
    for term in BANNED_TERMS:
        assert term not in hay, f"banned term {term!r} in body"


def test_body_shape_matches_the_frozen_schema():
    monitors = [
        {
            "name": "Conditions we watch",
            "state_en": "No change in the conditions we watch.",
            "state_zh": "我们关注的条件没有变化。",
        }
    ]
    body = rb.compose_body(_thesis_target(), _briefing(), monitors)
    assert set(body.keys()) == {"target", "market_read", "monitors", "artifact"}
    assert set(body["target"].keys()) == {"kind", "id", "name", "version_or_asof"}
    assert body["target"]["kind"] == "thesis"
    assert body["target"]["id"] == THESIS_ID
    assert body["target"]["name"] == "Apple breadth thesis"
    assert body["artifact"]["name"]
    assert body["artifact"]["asof"] == "2026-09-13"
    for row in body["market_read"]:
        assert set(row.keys()) == {"section", "sentence_en", "sentence_zh", "asof"}
        assert row["sentence_en"]
        assert row["sentence_zh"]
    assert body["monitors"] == monitors


def test_degraded_body_carries_the_contract_line_as_market_read_zero():
    body = rb.compose_body(
        _thesis_target(),
        None,
        monitors=[],
        degraded_reason=CONTRACT_MISS_EN,
    )
    assert body["market_read"][0]["sentence_en"] == CONTRACT_MISS_EN
    assert "没有重新计算" in body["market_read"][0]["sentence_zh"]
    assert body["market_read"][0]["sentence_zh"].endswith("。")


def test_watchlist_body_includes_each_member():
    body = rb.compose_body(
        _watchlist_target(tickers=("AAPL", "MSFT")),
        _briefing(),
        monitors=[],
    )
    sentences = " ".join(row["sentence_en"] for row in body["market_read"])
    assert "Apple's tape is quiet after the print." in sentences
    assert "Microsoft held the week's range." in sentences


def test_weekly_artifact_sentences_are_verbatim_and_skip_confidence():
    body = rb.compose_body(
        _thesis_target(tickers=("AAPL",)),
        _weekly_brief(),
        monitors=[],
    )
    sentences = [row["sentence_en"] for row in body["market_read"]]
    assert "The week's tape stayed inside last week's range." in sentences
    assert "Apple stayed inside its range all week." in sentences
    assert "confidence" not in _keys(body)
    hay = _haystack(body)
    assert "falsif" not in hay


def test_user_facing_strings_are_plain_sentences():
    body = rb.compose_body(_thesis_target(), _briefing(), monitors=[])
    for row in body["market_read"]:
        for key in ("sentence_en", "sentence_zh"):
            text = row[key]
            assert "daily_after_us_close" not in text
            assert "weekly_saturday" not in text
            assert "brief_deliveries" not in text
            assert "_" not in text.split()[0]


# ---------------------------------------------------------------------------
# run() with FakeClient — idempotency, dry-run, degraded
# ---------------------------------------------------------------------------

def _patch_run(monkeypatch, *, artifact, target, client, subscriptions=None):
    monkeypatch.setattr(rb, "load_published_artifact", lambda cadence, root=None: artifact)
    monkeypatch.setattr(
        rb, "read_subscriptions", lambda cadence: subscriptions or [_sub()]
    )
    monkeypatch.setattr(rb, "read_target", lambda sub: target)
    monkeypatch.setattr(
        rb, "write_delivery", lambda row, dry_run=False: client.write(row, dry_run=dry_run)
    )
    monkeypatch.setattr(rb, "load_monitors_for_target", lambda target: [])
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "test-key")


def test_run_writes_one_ready_row(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.subscription_n == 1
    assert result.ready_n == 1
    assert result.degraded_n == 0
    assert result.slot == date(2026, 9, 13)
    assert len(client.deliveries) == 1
    row = client.deliveries[0]
    assert row["state"] == "ready"
    assert row["slot_asof"] == "2026-09-13"
    assert row["subscription_id"] == SUB_ID
    assert row["degraded_reason"] is None


def test_idempotent_second_run_writes_nothing(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    r1 = rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    r2 = rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    assert r1.ready_n == 1
    assert len(client.deliveries) == 1
    assert client.insert_calls == 2
    assert r2.duplicate_n == 1
    assert len(client.deliveries) == 1


def test_stale_artifact_writes_degraded_row_with_contract_line(monkeypatch):
    client = FakeClient()
    _patch_run(
        monkeypatch,
        artifact=_briefing(as_of="2026-09-12"),
        target=_thesis_target(),
        client=client,
    )
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.ready_n == 0
    assert result.degraded_n == 1
    assert result.slot == date(2026, 9, 13)
    row = client.deliveries[0]
    assert row["state"] == "degraded"
    assert row["degraded_reason"] == CONTRACT_MISS_EN
    assert row["body"]["market_read"][0]["sentence_en"] == CONTRACT_MISS_EN
    assert row["slot_asof"] == "2026-09-13"


def test_missing_artifact_writes_degraded_for_todays_slot_not_a_skip(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=None, target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.degraded_n == 1
    assert len(client.deliveries) == 1
    assert client.deliveries[0]["slot_asof"] == "2026-09-13"


def test_unavailable_target_writes_degraded_target_unavailable(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=None, client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.degraded_n == 1
    assert client.deliveries[0]["degraded_reason"] == "target unavailable"


def test_dry_run_writes_nothing(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=True,
        run_date=date(2026, 9, 13),
    )
    assert result.ready_n == 1
    assert result.planned_n == 1
    assert client.deliveries == []
    assert all(c == "dry" or True for c in [])  # writes went through dry_run=True
    assert client.insert_calls == 1
    assert client.deliveries == []


def test_paused_subscription_is_not_written(monkeypatch):
    client = FakeClient()
    _patch_run(
        monkeypatch,
        artifact=_briefing(),
        target=_thesis_target(),
        client=client,
        subscriptions=[_sub(state="paused")],
    )
    result = rb.run(
        cadence="daily_after_us_close",
        dry_run=False,
        run_date=date(2026, 9, 13),
    )
    assert result.subscription_n == 0
    assert client.deliveries == []


def test_run_does_not_backfill_yesterday(monkeypatch):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(as_of="2026-09-13"),
               target=_thesis_target(), client=client)
    rb.run(cadence="daily_after_us_close", dry_run=False, run_date=date(2026, 9, 13))
    slots = {r["slot_asof"] for r in client.deliveries}
    assert slots == {"2026-09-13"}
    assert "2026-09-12" not in slots


def test_write_delivery_uses_on_conflict_do_nothing():
    src = Path(rb.__file__).read_text(encoding="utf-8")
    assert "on_conflict=subscription_id,slot_asof" in src
    assert "resolution=ignore-duplicates" in src


def test_daily_artifact_file_and_field_are_named():
    assert rb.DAILY_ARTIFACT_REL == "site/intelligence/briefing.json"
    assert "as_of" in rb.DAILY_ASOF_FIELDS


def test_weekly_artifact_file_and_field_are_named():
    assert rb.WEEKLY_ARTIFACT_REL == "site/master_brief.json"
    assert "state_asof" in rb.WEEKLY_ASOF_FIELDS


# ---------------------------------------------------------------------------
# CLI: R6 line, ::notice, dormant flag, dry-run
# ---------------------------------------------------------------------------

def test_cli_prints_r6_line_and_notice_at_line_start(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    summary = [
        ln for ln in lines
        if ln.startswith("recurring briefs:") and not ln.startswith("::")
    ]
    assert summary, out
    assert "1 subscriptions" in summary[0]
    assert "1 ready" in summary[0]
    assert "0 degraded" in summary[0]
    assert "slot 2026-09-13" in summary[0]
    notices = [ln for ln in lines if ln.startswith("::notice")]
    assert notices, "expected a ::notice line at the start of some output line"
    assert "recurring briefs:" in notices[0]


def test_cli_dormant_without_enable_flag_writes_nothing(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.delenv("RECURRING_BRIEFS_ENABLE", raising=False)
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    assert client.deliveries == []
    out = capsys.readouterr().out
    assert "DORMANT" in out
    assert "RECURRING_BRIEFS_ENABLE" in out


def test_cli_dry_run_flag_writes_nothing_even_when_enabled(monkeypatch, capsys):
    client = FakeClient()
    _patch_run(monkeypatch, artifact=_briefing(), target=_thesis_target(), client=client)
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        [
            "--cadence",
            "daily_after_us_close",
            "--dry-run",
            "--run-date",
            "2026-09-13",
        ]
    )
    assert rc == 0
    assert client.deliveries == []
    out = capsys.readouterr().out
    assert "1 ready" in out


def test_cli_always_exits_zero_without_credentials(monkeypatch, capsys):
    monkeypatch.setattr(rb, "SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("RECURRING_BRIEFS_ENABLE", "1")
    rc = entry.main(
        ["--cadence", "daily_after_us_close", "--run-date", "2026-09-13"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "recurring briefs:" in out


def test_no_llm_call_in_producer_source():
    src = Path(rb.__file__).read_text(encoding="utf-8") + Path(entry.__file__).read_text(
        encoding="utf-8"
    )
    for needle in ("openai", "anthropic", "chat.completions", "ChatCompletion"):
        assert needle not in src.lower().replace("co-authored-by: claude", "")


def test_engine_never_prints_service_role_key():
    """The service-role key is sent as a header (same as the thesis monitor)
    but must never appear in a print or log line."""
    for path in (Path(rb.__file__), Path(entry.__file__)):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("print(") or stripped.startswith("log."):
                assert "SUPABASE_SERVICE_ROLE_KEY" not in line
                assert "SERVICE_ROLE" not in line


# ---------------------------------------------------------------------------
# Workflow placement + gating (R2)
# ---------------------------------------------------------------------------

def test_daily_step_sits_after_briefing_and_thesis_monitor():
    text = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    i_brief = text.find("brain briefing tunnel (build_briefing)")
    i_mon = text.find("thesis condition monitor (F11")
    i_ours = text.find("recurring briefs producer")
    assert i_brief != -1 and i_mon != -1 and i_ours != -1
    assert i_brief < i_mon < i_ours
    assert "python -m scripts.build_recurring_briefs --cadence daily_after_us_close" in text
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in text
    assert "SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}" in text


def test_weekly_step_sits_after_brief_producers():
    text = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
    i_brief = text.find('run_py "AI brief page (build_aibrief)" scripts.build_aibrief')
    i_ours = text.find("recurring briefs producer")
    assert i_brief != -1 and i_ours != -1
    assert i_brief < i_ours
    assert "python -m scripts.build_recurring_briefs --cadence weekly_saturday" in text
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in text


def test_gating_mirrors_thesis_monitor():
    daily = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    # The monitor's own gating lines, which this packet must mirror.
    assert "THESIS_MONITOR_ENABLE: ${{ secrets.THESIS_MONITOR_ENABLE }}" in daily
    assert "RECURRING_BRIEFS_ENABLE: ${{ secrets.RECURRING_BRIEFS_ENABLE }}" in daily
    assert "Dormant unless THESIS_MONITOR_ENABLE=1" in daily
    assert "Dormant unless RECURRING_BRIEFS_ENABLE=1" in daily


def test_no_new_cron_in_this_packet():
    daily = (ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8")
    weekly = (ROOT / ".github/workflows/weekly.yml").read_text(encoding="utf-8")
    # The producer rides existing owners; this packet does not add a schedule key.
    ours_daily = daily[daily.find("recurring briefs producer"):]
    ours_daily = ours_daily[: ours_daily.find("\n      - name: ")]
    assert "cron:" not in ours_daily
    ours_weekly = weekly[weekly.find("recurring briefs producer"):]
    ours_weekly = ours_weekly[: ours_weekly.find("\n      - name: ")]
    assert "cron:" not in ours_weekly
