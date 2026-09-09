from __future__ import annotations

import json
import os
import re
from pathlib import Path

from scripts.build_policy_watch import (
    _featured_predictions,
    brief,
    decorate_lifecycle_view,
    format_lifecycle_date,
    source_label,
)


ROOT = Path(__file__).resolve().parent.parent


def test_policy_watch_glance_helpers_are_plain_and_deterministic():
    long = "One useful sentence that already says what matters. " + "Detail " * 60
    assert brief(long, 90) == "One useful sentence that already says what matters."
    assert brief("A" * 200, 40) == "A" * 40 + "…"
    assert source_label("https://www.federalreserve.gov/newsevents.htm") == "Federal Reserve"
    assert source_label("https://example.com/policy") == "example.com"


def test_featured_calls_put_needs_review_first():
    calls = [
        {"id": "P1", "status": "open", "check_by": "2026-12-31"},
        {"id": "P2", "status": "hit", "check_by": "2026-06-01"},
        {"id": "P3", "status": "open", "check_by": "2026-07-01"},
    ]
    dates = {"predictions": {"P1": {"overdue": False}, "P2": {"overdue": False}, "P3": {"overdue": True}}}
    rows = _featured_predictions(calls, dates, limit=3)
    assert [row["id"] for row in rows] == ["P3", "P1", "P2"]
    assert rows[0]["needs_review"] is True


def test_broken_ceasefire_call_is_forced_into_review():
    rows = _featured_predictions(
        [{"id": "P44", "status": "open", "check_by": "2026-08-31"}],
        {"predictions": {"P44": {"overdue": False}}},
    )
    assert rows[0]["needs_review"] is True


def test_policy_watch_template_uses_macro_ui_roles_and_plain_labels():
    template = (ROOT / "templates" / "policy_watch.html.j2").read_text(encoding="utf-8")

    for weight in (500, 600, 700):
        assert f'src:url("/fonts/InterDisplay-{weight}.woff2")' in template
    assert "font-family:var(--font-ui)" in template
    assert "font-family:var(--font-display)" in template
    assert "max-width:1500px" in template
    assert "gbtn gbtn-sm" in template
    assert "grid-template-columns:1fr" in template
    assert "overflow-wrap:anywhere" in template

    for old_copy in (
        "Intent Desk",
        "Realpolitik",
        "accountability spine",
        "Read the full thesis",
        "model key",
        "Catalyst spine",
    ):
        assert old_copy not in template

    for new_copy in (
        "What matters now",
        "Fed changes to watch",
        "Stages, dated and sourced",
        "Where policy may help or hurt",
        "Calls and results",
        "See all calls",
    ):
        assert new_copy in template


def test_generated_policy_watch_links_resolvable_page_css():
    page = (ROOT / "site" / "policy_watch.html").read_text(encoding="utf-8")
    match = re.search(r'href="assets/css/([0-9a-f]{8})\.css\?v=\1"', page)
    assert match, "policy_watch.html must link its content-hashed page stylesheet"
    css = (ROOT / "site" / "assets" / "css" / f"{match.group(1)}.css").read_text(encoding="utf-8")

    assert 'url("/fonts/InterDisplay-600.woff2")' in css
    assert 'url("fonts/InterDisplay-600.woff2")' not in css
    assert "The policy moves that matter for markets. Last verified" in page
    assert "See all calls" in page
    assert "Under review after the ceasefire collapsed" in page
    assert "READ BEING UPDATED" not in page
    assert "What policymakers do, not what they say" not in page
    assert "Miran role: authored before CEA/Fed tenure" not in page
    assert "[1]" not in page


def _render_policy_watch_with_lifecycle(lifecycle_fixture, monkeypatch, tmp_path):
    """Renders the REAL page via scripts.build_policy_watch.main(), monkeypatching only
    the lifecycle view so every other context var (intel, dates, fed_stance, ...) is the
    real production shape — avoids re-guessing the whole context surface."""
    import scripts.build_policy_watch as bpw
    from engine import policy_intent_desk as _pid

    monkeypatch.setattr(_pid, "lifecycle_view", lambda root=None: lifecycle_fixture)
    monkeypatch.setattr(_pid, "ingest_lifecycle", lambda root=None: 0)

    captured = {}

    def _fake_write_page(path, html):
        captured["html"] = html

    monkeypatch.setattr(bpw, "write_page", _fake_write_page)
    bpw.main()
    assert "html" in captured, "build_policy_watch.main() did not render policy_watch"
    return captured["html"]


LIFECYCLE_FIXTURE = {
    "schema": "policy_lifecycle.v1", "as_of": "2026-09-01", "null_reason": None,
    "counts": {"proposed": 1, "passed": 0, "in_force": 1, "enforced": 0, "other": 0, "unknown": 1},
    "items": [
        {"id": "L1", "title_en": "Lever One", "title_zh": "杠杆一",
         "jurisdiction": "US-FED", "jurisdiction_en": "United States — federal", "jurisdiction_zh": "美国联邦",
         "state": "in_force", "stage_rank": 2, "reached": ["proposed", "passed", "in_force"], "gaps": [],
         "basis": "FACT", "detail_en": "Dated move.", "detail_zh": "已落地。",
         "state_asof": "2026-03-01", "known_at": "2026-03-02T00:00:00Z",
         "source": {"url": "https://www.federalregister.gov/x", "label": "Federal Register", "title": "doc", "doc_id": "1"},
         "next_step": {"stage": "enforced", "date": None},
         "stalled": False, "corrected": False, "conflict": False, "why": None},
        {"id": "L2", "title_en": "Lever Two", "title_zh": "杠杆二",
         "jurisdiction": "US-FED", "jurisdiction_en": "United States — federal", "jurisdiction_zh": "美国联邦",
         "state": "proposed", "stage_rank": 0, "reached": ["proposed"], "gaps": [],
         "state_asof": "2026-01-01", "known_at": "2026-01-02T00:00:00Z",
         "source": {"url": "https://www.federalregister.gov/y", "label": "Federal Register", "title": "doc", "doc_id": "2"},
         "next_step": {"stage": "passed", "date": None},
         "stalled": False, "corrected": False, "conflict": False, "why": None},
        {"id": "L3", "title_en": "Lever Three", "title_zh": "杠杆三",
         "jurisdiction": None, "jurisdiction_en": None, "jurisdiction_zh": None,
         "state": "unknown", "stage_rank": None, "reached": [], "gaps": [],
         "state_asof": None, "known_at": None, "source": None,
         "next_step": None, "stalled": False, "corrected": False, "conflict": False, "why": "no_document"},
    ],
}


def test_every_lifecycle_row_carries_state_asof_and_source(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    assert html.count("pw-stage-asof") >= 2  # both dated items
    assert 'href="https://www.federalregister.gov/x"' in html
    assert 'href="https://www.federalregister.gov/y"' in html
    assert "Not tracked yet" in html  # unknown item's typed badge


def test_lifecycle_markup_carries_no_machine_state_names(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    text_only = re.sub(r"<[^>]+>", " ", html)
    for token in ("in_force", "no_document", "struck_down"):
        assert token not in text_only, f"machine token {token!r} leaked into visible text"


def test_lifecycle_strings_are_bilingual_and_never_in_title_attr(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    assert "Not tracked yet" in html and "尚未跟踪" in html
    assert "In force" in html and "已生效" in html
    for m in re.finditer(r'title="([^"]*)"', html):
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in m.group(1)), "CJK found in a title= attribute"


def test_light_mode_changes_the_mechanism_not_only_the_token():
    template = (ROOT / "templates" / "policy_watch.html.j2").read_text(encoding="utf-8")
    m = re.search(r'html\[data-theme="light"\]\s*\.pw-stage-seg\.is-current\{([^}]*)\}', template)
    assert m, "light current-segment rule missing"
    assert "box-shadow:none" in m.group(1)
    assert "outline:" in m.group(1)
    m2 = re.search(r'html\[data-theme="light"\]\s*\.pw-stage\.is-stalled\{([^}]*)\}', template)
    assert m2, "light stalled rule missing"
    assert "border-left" in m2.group(1)
    assert "box-shadow:none" in m2.group(1)
    assert (
        ".pw-stage.is-stalled{border-left:3px solid var(--pw-amber);"
        "background:color-mix(in srgb,var(--pw-amber) 9%,transparent);"
        "box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--pw-amber) 38%,transparent)}"
    ) in template


def test_policy_watch_l1_section_count_is_unchanged():
    template = (ROOT / "templates" / "policy_watch.html.j2").read_text(encoding="utf-8")
    assert template.count('<section class="pw-section"') == 7


def test_stalled_state_prints_plain_words(monkeypatch, tmp_path):
    fixture = json.loads(json.dumps(LIFECYCLE_FIXTURE))
    fixture["intel_as_of"] = "2026-07-13"
    fixture["items"][1]["stalled"] = True
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "No movement for 45+ days as of July 13, 2026" in html
    assert "截至2026年7月13日已超过 45 天没有推进" in html
    assert 'data-intel-as-of="2026-07-13"' in html
    assert "is-stalled" in html
    assert "No movement for 45+ days / 超过 45 天没有推进" in html


def test_jurisdiction_eyebrow_suppressed_when_no_row_has_it(monkeypatch, tmp_path):
    fixture = json.loads(json.dumps(LIFECYCLE_FIXTURE))
    for it in fixture["items"]:
        it["jurisdiction"] = None
        it["jurisdiction_en"] = None
        it["jurisdiction_zh"] = None
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "Jurisdiction not available yet" not in html
    assert "管辖范围暂不可用" not in html
    assert html.count('class="pw-stage"') + html.count('class="pw-stage is-unknown"') >= 3


def test_jurisdiction_eyebrow_prints_only_on_the_missing_row(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    assert html.count("Jurisdiction not available yet") == 1
    assert "United States — federal" in html


def test_newest_dated_stage_chip_is_not_a_last_checked_label(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    assert "Newest dated stage" in html
    assert "最新阶段日期" in html
    assert "Stages as of" not in html
    assert "进程更新于" not in html
    assert 'data-as-of="2026-09-01"' in html
    assert "September 1, 2026" in html
    assert "2026年9月1日" in html


def test_gap_and_next_step_use_short_stop_labels(monkeypatch, tmp_path):
    fixture = json.loads(json.dumps(LIFECYCLE_FIXTURE))
    fixture["items"][0]["gaps"] = ["proposed", "passed"]
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "No published date for" in html
    assert "Passed, not yet in force" not in html.split("No published date for", 1)[1][:80]
    assert "Next step to watch" in html
    next_chunk = html.split("Next step to watch", 1)[1][:120]
    assert "Passed, not yet in force" not in next_chunk


def test_meter_aria_label_is_bilingual(monkeypatch, tmp_path):
    html = _render_policy_watch_with_lifecycle(LIFECYCLE_FIXTURE, monkeypatch, tmp_path)
    assert 'aria-label="In force / 已生效 · March 1, 2026 / 2026年3月1日"' in html
    assert 'aria-label="Proposed / 已提出 · January 1, 2026 / 2026年1月1日"' in html


def test_format_lifecycle_date_day_and_month_en_zh():
    assert format_lifecycle_date("2026-05-01", "day") == ("May 1, 2026", "2026年5月1日")
    assert format_lifecycle_date("2025-11-01", "month") == ("Nov 2025", "2025年11月")
    assert format_lifecycle_date("2026-07-13", "day") == ("July 13, 2026", "2026年7月13日")
    assert format_lifecycle_date("2026-07-01", "month") == ("Jul 2026", "2026年7月")
    assert format_lifecycle_date(None, "undated") == ("date not published", "日期未公布")


def test_month_precision_row_renders_month_only_and_is_not_stalled(monkeypatch, tmp_path):
    from engine.policy_intent_desk import fold_lifecycle

    ev = {
        "item_id": "L1", "type": "in_force", "event_date": "2026-05-01",
        "date_precision": "month", "known_at": "2026-05-01T12:00:00Z",
        "source": {"url": "https://www.federalregister.gov/x", "title": "doc", "doc_id": "1"},
    }
    row = fold_lifecycle(
        [ev], [{"id": "L1", "title_en": "Lever One", "title_zh": "杠杆一"}],
        as_of_date="2026-07-13",
    )[0]
    assert row["stalled"] is False
    fixture = {
        "schema": "policy_lifecycle.v1", "as_of": "2026-05-01", "as_of_precision": "month",
        "intel_as_of": "2026-07-13", "null_reason": None,
        "counts": {"in_force": 1, "proposed": 0, "passed": 0, "enforced": 0,
                   "other": 0, "unknown": 0},
        "items": [row],
    }
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "May 2026" in html
    assert "2026年5月" in html
    assert "May 1, 2026" not in html
    assert "2026年5月1日" not in html
    assert 'class="pw-stage is-stalled' not in html
    assert 'data-state-asof="2026-05-01"' in html
    assert 'data-date-precision="month"' in html


def test_identical_gap_set_prints_one_section_line(monkeypatch, tmp_path):
    fixture = json.loads(json.dumps(LIFECYCLE_FIXTURE))
    for it in fixture["items"]:
        it["gaps"] = ["proposed", "passed"]
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "No published dates for" in html
    assert "Proposed, Passed" in html
    assert "提出、通过" in html
    assert "No published date for Proposed" not in html
    assert "No date published" not in html
    assert "未公布日期：" not in html
    assert "Next step to watch" in html


def test_mixed_gap_sets_keep_per_row_null_lines(monkeypatch, tmp_path):
    fixture = json.loads(json.dumps(LIFECYCLE_FIXTURE))
    fixture["items"][0]["gaps"] = ["proposed", "passed"]
    fixture["items"][1]["gaps"] = ["passed"]
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "No published dates for" not in html
    assert "No published date for" in html
    assert "Next step to watch" in html
    next_chunk = html.split("Next step to watch", 1)[1]
    assert "No date published" in next_chunk[:200]
    assert "it.next_step.date" not in (ROOT / "templates" / "policy_watch.html.j2").read_text()
    assert '<span class="l-en">, </span><span class="l-zh">、</span>' in html
    decorated = decorate_lifecycle_view(fixture)
    assert decorated["shared_gap_set"] is None
    for it in decorated["items"]:
        ns = it.get("next_step")
        if isinstance(ns, dict):
            assert "date_en" not in ns
            assert "date_zh" not in ns


def test_undated_row_renders_copy_is_not_stalled_and_does_not_set_chip(monkeypatch, tmp_path):
    from engine.policy_intent_desk import fold_lifecycle

    dated = {
        "item_id": "L2", "type": "proposed", "event_date": "2026-06-24",
        "known_at": "2026-06-24T12:00:00Z",
        "source": {"url": "https://www.federalregister.gov/y", "title": "doc", "doc_id": "2"},
    }
    undated = {
        "item_id": "L1", "type": "enforced", "event_date": None,
        "date_precision": "undated", "known_at": None,
        "source": {"url": "https://www.energy.gov/x", "title": "doc", "doc_id": "1"},
    }
    prior = {
        "item_id": "L1", "type": "in_force", "event_date": "2025-05-23",
        "known_at": "2025-05-23T12:00:00Z",
        "source": {"url": "https://www.energy.gov/ne", "title": "eo", "doc_id": "0"},
    }
    rows = fold_lifecycle(
        [prior, undated, dated],
        [{"id": "L1", "title_en": "Nuclear", "title_zh": "核电"},
         {"id": "L2", "title_en": "Dollar", "title_zh": "美元"}],
        as_of_date="2026-07-13",
    )
    nuclear = next(it for it in rows if it["id"] == "L1")
    assert nuclear["stalled"] is False
    assert nuclear["date_precision"] == "undated"
    fixture = {
        "schema": "policy_lifecycle.v1", "as_of": "2026-06-24", "as_of_precision": "day",
        "intel_as_of": "2026-07-13", "null_reason": None,
        "counts": {"enforced": 1, "proposed": 1, "passed": 0, "in_force": 0,
                   "other": 0, "unknown": 0},
        "items": rows,
    }
    html = _render_policy_watch_with_lifecycle(fixture, monkeypatch, tmp_path)
    assert "date not published" in html
    assert "日期未公布" in html
    assert "Latest stage has no published date — watch the next document." in html
    assert "最新阶段未公布日期——关注下一份文件。" in html
    assert 'class="pw-stage is-stalled' not in html
    assert "Newest dated stage" in html
    assert "June 24, 2026" in html
    assert "2026年6月24日" in html
    chip = html.split("Newest dated stage", 1)[1][:240]
    assert "June 24, 2026" in chip
    assert "Jul 2026" not in chip
    assert "2026年7月<" not in chip and "2026年7月 " not in chip
    assert 'data-date-precision="undated"' in html


# --------------------------------------------------------------------------- #
# R1 current-source consumer — behavioral tests (tmp_path only)
# --------------------------------------------------------------------------- #

from datetime import datetime, timezone  # noqa: E402
from engine.policy_watch_current import build_current  # noqa: E402


_JULY_STMT = """The Federal Open Market Committee approved the following statement for release by a 9 – 3 vote:

The Committee decided to maintain the target range for the federal funds rate at 3-1/2 to 3-3/4 percent, in support of the Federal Reserve's dual mandate. The Committee is continuing its policy of maintaining ample reserves in the banking system.

Economic activity is expanding at a solid pace despite elevated uncertainty that owes, in part, to the conflict in the Middle East. Productivity growth and capital investment are strong. Job gains have kept pace with the workforce, and the unemployment rate has changed little.

Inflation remains elevated relative to the Committee's 2 percent goal, in part reflecting supply shocks that have driven price increases in certain sectors, including energy. The Committee will deliver price stability.

Voting against the monetary policy action were Beth M. Hammack, Neel Kashkari, and Lorie K. Logan, who preferred to raise the target range for the federal funds rate by 1/4 percentage point at this meeting.
"""

_JUNE_STMT = """The Federal Open Market Committee approved the following statement for release by a 12 – 0 vote:

The Committee decided to maintain the target range for the federal funds rate at 3-1/2 to 3-3/4 percent, in support of the Federal Reserve's dual mandate. The Committee reaffirmed its policy of maintaining ample reserves in the banking system.

Economic activity is expanding at a solid pace despite elevated uncertainty that owes, in part, to the conflict in the Middle East. Productivity growth and capital investment are strong. Job gains have kept pace with the workforce, and the unemployment rate has changed little.

Inflation remains elevated relative to the Committee's 2 percent goal, in part reflecting supply shocks that have driven price increases in certain sectors, including energy. The Committee will deliver price stability.
"""

_CUTOFF = datetime(2026, 9, 8, 16, 0, tzinfo=timezone.utc)


def _write_fomc(root: Path, rows: list[dict], statements: dict[str, str]) -> None:
    store = root / "data" / "marketing" / "fomc"
    (store / "statements").mkdir(parents=True, exist_ok=True)
    for date_s, text in statements.items():
        (store / "statements" / f"{date_s}.txt").write_text(text, encoding="utf-8")
    ledger = store / "statements.jsonl"
    ledger.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _july_row() -> dict:
    return {
        "date": "2026-07-29",
        "fetched_at": "2026-08-08T00:00:00Z",
        "mode": "seed",
        "seed": True,
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
        "paragraphs": 5,
    }


def _june_row() -> dict:
    return {
        "date": "2026-06-17",
        "fetched_at": "2026-08-08T00:00:00Z",
        "mode": "seed",
        "seed": True,
        "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260617a.htm",
        "paragraphs": 4,
    }


def _write_official_cache(root: Path, day: str, payload: dict) -> Path:
    d = root / "data" / "macro" / "official_news_cache"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"official_v3_{day}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fed_item(title: str, url: str, seendate: str) -> dict:
    return {
        "title": title,
        "url": url,
        "domain": "federalreserve.gov",
        "seendate": seendate,
        "theme": "monetary",
        "source": "official",
        "source_tier": "official",
    }


def test_build_current_absent_intel_still_supplies_next_fomc(tmp_path):
    assert not (tmp_path / "data" / "policy" / "intel.json").exists()
    out = build_current(tmp_path, now=_CUTOFF)
    meetings = out["calendar"]["meetings"]
    assert meetings, "calendar must come from existing decision_dates, not intel"
    assert meetings[0]["date"] == "2026-09-16"
    assert out["calendar"]["state"] == "scheduled"
    assert out["calendar"]["calendar_url"] == (
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    )


def test_build_current_excludes_future_statement(tmp_path):
    _write_fomc(
        tmp_path,
        [_june_row(), _july_row(), {
            "date": "2026-09-16",
            "fetched_at": "2026-09-16T18:00:00Z",
            "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        }],
        {"2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT, "2026-09-16": _JULY_STMT},
    )
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["statement"]["state"] == "recorded"
    assert out["statement"]["decision_date"] == "2026-07-29"
    assert out["statement"]["decision_date"] != "2026-09-16"


def test_build_current_awaiting_statement_after_elapsed_decision(tmp_path):
    _write_fomc(tmp_path, [_june_row(), _july_row()], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    after = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
    out = build_current(tmp_path, now=after)
    assert out["statement"]["state"] == "awaiting_statement"
    assert out["statement"].get("facts") in (None, {})
    assert (out["statement"].get("facts") or {}).get("target_range") is None


def test_build_current_rejects_suffix_trick_hostname(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item(
            "Federal Reserve issues FOMC statement",
            "https://federalreserve.gov.evil.test/newsevents/pressreleases/monetary20260729a.htm",
            "2026-07-29T18:00:00+00:00",
        ),
        _fed_item(
            "Warsh, In Our Time",
            "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
            "2026-08-28T14:00:00+00:00",
        ),
    ]})
    out = build_current(tmp_path, now=_CUTOFF)
    urls = [i["url"] for i in out["headlines"]["items"]]
    assert all("evil.test" not in u for u in urls)
    assert any(u.startswith("https://www.federalreserve.gov/") for u in urls)


def test_build_current_excludes_unknown_and_future_dates(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item("No date speech", "https://www.federalreserve.gov/newsevents/speech/a.htm", ""),
        _fed_item("Bad date", "https://www.federalreserve.gov/newsevents/speech/b.htm", "not-a-date"),
        _fed_item(
            "Future speech",
            "https://www.federalreserve.gov/newsevents/speech/c.htm",
            "2026-09-20T12:00:00+00:00",
        ),
        _fed_item(
            "Warsh, In Our Time",
            "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
            "2026-08-28T14:00:00+00:00",
        ),
    ]})
    out = build_current(tmp_path, now=_CUTOFF)
    titles = [i["title"] for i in out["headlines"]["items"]]
    assert "Warsh, In Our Time" in titles
    assert "Future speech" not in titles
    assert "No date speech" not in titles
    assert "Bad date" not in titles


def test_build_current_dedupes_canonical_url(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item(
            "Federal Reserve issues FOMC statement",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
            "2026-07-29T18:00:00+00:00",
        ),
        _fed_item(
            "Federal Reserve issues FOMC statement",
            "https://federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm#top",
            "2026-07-29T18:00:00+00:00",
        ),
    ]})
    out = build_current(tmp_path, now=_CUTOFF)
    assert len(out["headlines"]["items"]) == 1


def test_build_current_source_age_not_reset_by_mtime(tmp_path):
    path = _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item(
            "Warsh, In Our Time",
            "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
            "2026-08-28T14:00:00+00:00",
        ),
    ]})
    later = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc).timestamp()
    os.utime(path, (later, later))
    out = build_current(tmp_path, now=_CUTOFF)
    item = out["headlines"]["items"][0]
    assert item["published_at"].startswith("2026-08-28")
    assert out["headlines"]["saved_date"] == "2026-09-06"
    assert out["headlines"]["saved_date"] != "2026-09-08"
    assert out["headlines"].get("verified_at") is None


def test_build_current_invalid_newest_cache_is_degraded_not_fresh(tmp_path):
    _write_official_cache(tmp_path, "2026-09-05", {"articles": [
        _fed_item(
            "Warsh, In Our Time",
            "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
            "2026-08-28T14:00:00+00:00",
        ),
    ]})
    bad = tmp_path / "data" / "macro" / "official_news_cache" / "official_v3_2026-09-06.json"
    bad.write_text("{not-json", encoding="utf-8")
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "invalid_newest"
    assert out["headlines"].get("fresh") is not True
    last_good = out["headlines"].get("last_good") or {}
    assert last_good.get("saved_date") == "2026-09-05"
    assert last_good.get("state") == "last_good"
    titles = [i["title"] for i in last_good.get("items") or []]
    assert "Warsh, In Our Time" in titles


def test_build_current_no_prior_statement_comparison_unavailable(tmp_path):
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": _JULY_STMT})
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["statement"]["state"] == "recorded"
    assert out["comparison"]["state"] == "unavailable"


def test_build_current_year_beyond_coverage_is_not_quiet(tmp_path):
    out = build_current(tmp_path, now=datetime(2027, 2, 1, tzinfo=timezone.utc))
    assert out["calendar"]["state"] == "schedule_needs_updating"
    assert out["calendar"]["meetings"] == []
    assert out["calendar"]["state"] != "no_events"
    assert out["calendar"]["state"] != "quiet"


def test_build_current_network_is_forbidden(monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise AssertionError("network forbidden from build_current")

    monkeypatch.setattr("requests.get", boom, raising=False)
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    import engine.event_calendar as ec
    monkeypatch.setattr(
        ec, "us_macro_events",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("us_macro_events forbidden")),
    )
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["calendar"]["meetings"][0]["date"] == "2026-09-16"


def test_build_current_leaves_inputs_byte_identical(tmp_path):
    _write_fomc(tmp_path, [_june_row(), _july_row()], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    cache = _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item(
            "Warsh, In Our Time",
            "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
            "2026-08-28T14:00:00+00:00",
        ),
    ]})
    before = {
        p: p.read_bytes()
        for p in [cache, tmp_path / "data/marketing/fomc/statements.jsonl",
                  tmp_path / "data/marketing/fomc/statements/2026-07-29.txt"]
    }
    build_current(tmp_path, now=_CUTOFF)
    for p, blob in before.items():
        assert p.read_bytes() == blob


def test_build_current_records_real_statement_facts_and_changes(tmp_path):
    _write_fomc(tmp_path, [_june_row(), _july_row()], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    out = build_current(tmp_path, now=_CUTOFF)
    facts = out["statement"]["facts"]
    assert facts["target_range"] == "3-1/2 to 3-3/4 percent"
    assert facts["action"] == "maintain"
    assert out["statement"]["collected_at"].startswith("2026-08-08")
    assert out["statement"]["seed"] is True
    assert out["comparison"]["state"] == "available"
    assert out["comparison"]["prior_date"] == "2026-06-17"
    phrases = " ".join(out["comparison"].get("added_phrases") or [])
    removed = " ".join(out["comparison"].get("removed_phrases") or [])
    assert phrases or removed or out["comparison"].get("highlights")


def test_build_current_omits_enforcement_noise(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item(
            "Federal Reserve Board announces termination of enforcement actions",
            "https://www.federalreserve.gov/newsevents/pressreleases/enforcement20260904a.htm",
            "2026-09-04T15:00:00+00:00",
        ),
        _fed_item(
            "Waller, The Economic Outlook",
            "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm",
            "2026-09-03T12:30:00+00:00",
        ),
    ]})
    out = build_current(tmp_path, now=_CUTOFF)
    titles = [i["title"] for i in out["headlines"]["items"]]
    assert "Waller, The Economic Outlook" in titles
    assert not any("enforcement" in t.lower() for t in titles)


def _render_current_page(current, intel=None, dates=None):
    from jinja2 import Environment, FileSystemLoader

    if intel is None:
        intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    preds = intel.get("predictions") or []
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("policy_watch.html.j2").render(
        intel=intel,
        counts={"total": len(preds), "open": 0, "hit": 0, "miss": 0,
                "policy_action": 0, "market_outcome": 0, "hit_rate": None},
        desk=None, fed_stance=None, fed_hist={}, rot=None, rot_hist={},
        dates=dates if dates is not None else {"staleness": {"age_days": 57}},
        catalysts=None, scorecard=None,
        generated_utc="2026-09-08 12:00 UTC",
        verified_en="July 13, 2026", verified_zh="2026年7月13日",
        source_links=[], featured_predictions=[], brief=brief,
        active_section="research", active_page="policy_watch",
        lifecycle=None, current=current,
    )


def test_rendered_page_changes_when_headline_and_decision_change(tmp_path):
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": _JULY_STMT})
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item("Warsh, In Our Time",
                  "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                  "2026-08-28T14:00:00+00:00"),
    ]})
    first = _render_current_page(build_current(tmp_path, now=_CUTOFF))
    assert "Warsh, In Our Time" in first
    assert "2026-07-29" in first

    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item("Waller, The Economic Outlook",
                  "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm",
                  "2026-09-03T12:30:00+00:00"),
    ]})
    second = _render_current_page(build_current(tmp_path, now=_CUTOFF))
    assert "Waller, The Economic Outlook" in second
    assert "Warsh, In Our Time" not in second


def test_rendered_page_drops_fixed_bottom_line_and_view_copy():
    template = (ROOT / "templates" / "policy_watch.html.j2").read_text(encoding="utf-8")
    include = (ROOT / "templates" / "_policy_watch_current.html.j2").read_text(encoding="utf-8")
    text = template + include
    assert "VIEW_COPY" not in template
    assert "Energy may stay supported while Iran risk keeps oil prices elevated." not in text
    assert "The Fed is staying tough on inflation while Treasury tries to lower borrowing costs" not in text
    html = _render_current_page(build_current(ROOT, now=_CUTOFF))
    assert "Energy may stay supported while Iran risk keeps oil prices elevated." not in html
    assert "The Fed is staying tough on inflation while Treasury tries to lower borrowing costs" not in html


def test_rendered_page_keeps_44_calls_and_july_13_verification():
    intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    html = _render_current_page(build_current(ROOT, now=_CUTOFF), intel=intel)
    assert html.count("P44") >= 1
    assert len(intel["predictions"]) == 44
    for pred in intel["predictions"]:
        assert f'data-policy-id="full-{pred["id"]}"' in html
    assert "July 13, 2026" in html
    assert "2026年7月13日" in html
    assert "Dated policy changes and the next decision" in html
    assert "Last recorded decision" in html
    assert "最近一次已收录决议" in html
    assert "Background research" in html
    assert "历史研究" in html
    assert "Next Fed decisions" in html
    assert "09-16" in html
    assert "Original source text" in html
    assert "原文" in html
    assert "Build time is not evidence" in html


def test_missing_intel_still_renders_current_when_calendar_exists():
    html = _render_current_page(
        build_current(ROOT, now=_CUTOFF),
        intel={"as_of": "", "predictions": [], "fed": {"task_forces": []},
               "administration": {"verified_levers": [], "theaters": []},
               "rotation": {"targeted": [], "starved": []}, "sources": []},
        dates=None,
    )
    assert "No background research in this update" in html
    assert "本次更新没有历史研究" in html
    assert "Next Fed decisions" in html
    assert "09-16" in html
