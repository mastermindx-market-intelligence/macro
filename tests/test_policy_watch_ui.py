from __future__ import annotations

import json
import os
import re
import shutil
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


def test_resolved_ceasefire_entry_is_not_forced_back_into_review():
    rows = _featured_predictions(
        [{"id": "P44", "status": "void", "check_by": "2026-08-31", "reviewed_on": "2026-09-08"}],
        {"predictions": {"P44": {"overdue": False}}},
    )
    assert rows[0]["needs_review"] is False


def test_recent_reviews_are_featured_ahead_of_still_open_calls():
    calls = [
        {"id": "P1", "status": "open", "check_by": "2026-12-31"},
        {"id": "P2", "status": "hit", "check_by": "2026-08-01", "reviewed_on": "2026-09-07"},
        {"id": "P3", "status": "void", "check_by": "2026-07-01", "reviewed_on": "2026-09-08"},
    ]
    rows = _featured_predictions(calls, {"predictions": {}}, limit=3)
    assert [row["id"] for row in rows] == ["P3", "P2", "P1"]

def test_policy_watch_review_batch_is_resolved_and_auditable():
    intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in intel["predictions"]}
    assert {pid: by_id[pid]["status"] for pid in ("P6", "P16", "P40", "P41", "P43", "P44")} == {
        "P6": "hit", "P16": "hit", "P40": "hit", "P41": "hit", "P43": "void", "P44": "void",
    }
    for pid in ("P6", "P16", "P40", "P41", "P43", "P44"):
        assert by_id[pid]["reviewed_on"] == "2026-09-08"
        assert by_id[pid]["result_en"] and by_id[pid]["result_zh"] and by_id[pid]["result_code"]
    assert by_id["P16"]["result_source"].endswith("R_20260827_1.pdf")
    assert "2.73x bid-to-cover" in by_id["P16"]["result_en"]
    assert by_id["P43"]["result_code"] == "outcome_predated_call"
    assert by_id["P44"]["result_code"] == "premise_broken_at_entry"

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


def test_generated_policy_watch_links_resolvable_page_css(monkeypatch, tmp_path):
    """Renders the REAL page via build_policy_watch.main() + externalize_css, in an
    isolated tmp_path — never against a stale committed site/policy_watch.html and
    never mutating the shared rotation/fed-stance history files."""
    import scripts.build_policy_watch as bpw
    from scripts import externalize_css
    from engine import fed_stance as _fs
    from engine import policy_rotation_check as _rotc
    from lib.pages import write_page as _real_write_page

    site_dir = tmp_path / "site"
    site_dir.mkdir()
    monkeypatch.setattr(_fs, "append_history", lambda *a, **k: False)
    monkeypatch.setattr(_rotc, "append_history", lambda *a, **k: False)
    monkeypatch.setattr(
        bpw, "write_page", lambda path, html: _real_write_page(site_dir / Path(path).name, html)
    )
    assert bpw.main() == 0
    externalize_css.externalize(site_dir)

    page = (site_dir / "policy_watch.html").read_text(encoding="utf-8")
    match = re.search(r'href="assets/css/([0-9a-f]{8})\.css\?v=\1"', page)
    assert match, "policy_watch.html must link its content-hashed page stylesheet"
    css = (site_dir / "assets" / "css" / f"{match.group(1)}.css").read_text(encoding="utf-8")

    assert 'url("/fonts/InterDisplay-600.woff2")' in css
    assert 'url("fonts/InterDisplay-600.woff2")' not in css
    hero = page.split('class="pw-hero ', 1)[1].split("</section>", 1)[0]
    assert "The policy moves that matter for markets." in hero
    assert "See all calls" in page
    assert "READ BEING UPDATED" not in page
    assert "What policymakers do, not what they say" not in page
    assert "Miran role: authored before CEA/Fed tenure" not in page
    assert "[1]" not in page


def _render_policy_watch_with_lifecycle(lifecycle_fixture, monkeypatch, tmp_path):
    """Renders the REAL page via scripts.build_policy_watch.main(), monkeypatching only
    the lifecycle view so every other context var (intel, dates, fed_stance, ...) is the
    real production shape — avoids re-guessing the whole context surface."""
    import scripts.build_policy_watch as bpw
    from engine import fed_stance as _fs
    from engine import policy_intent_desk as _pid
    from engine import policy_rotation_check as _rotc

    monkeypatch.setattr(_pid, "lifecycle_view", lambda root=None: lifecycle_fixture)
    monkeypatch.setattr(_pid, "ingest_lifecycle", lambda root=None: 0)
    # This helper is a render-only fixture. Production history appenders are
    # deliberately disabled so the test cannot mutate the repository merely
    # because today's idempotency row is absent from an older feature base.
    monkeypatch.setattr(_fs, "append_history", lambda *args, **kwargs: False)
    monkeypatch.setattr(_rotc, "append_history", lambda *args, **kwargs: False)

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

from datetime import date, datetime, timezone  # noqa: E402
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


def _render_current_page(current, intel=None, dates=None, uk_desk=None, background_unavailable=False):
    from jinja2 import Environment, FileSystemLoader

    if intel is None:
        intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    preds = intel.get("predictions") or []
    if uk_desk is None:
        uk_desk = {
            "state": "gate_off",
            "jurisdiction_en": "United Kingdom",
            "jurisdiction_zh": "英国",
            "body_en": "HM Treasury",
            "body_zh": "英国财政部",
            "source_label": "GOV.UK",
            "headline": None,
            "stance": None,
            "model_unavailable": False,
        }
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
        lifecycle=None, current=current, uk_desk=uk_desk,
        background_unavailable=background_unavailable,
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


def test_rendered_page_keeps_44_calls_and_july_13_verification(tmp_path):
    intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": _JULY_STMT})
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item("Waller, The Economic Outlook",
                  "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm",
                  "2026-09-03T12:30:00+00:00"),
    ]})
    html = _render_current_page(build_current(tmp_path, now=_CUTOFF), intel=intel)
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
    assert "Build time is not evidence" not in html
    assert "Cache saved date" not in html
    assert "Needs refresh" not in html
    assert "Background needs review" in html
    assert "历史研究待复核" in html
    assert "Official records above" not in html
    assert "上方官方记录单独列示" not in html
    # Glance must not use green buy-like decision card.
    assert 'id="pw-last-decision"' in html
    assert 'id="pw-last-decision" class="pw-card green"' not in html
    assert 'class="pw-card green" id="pw-last-decision"' not in html


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


# --------------------------------------------------------------------------- #
# R1 repair-1 — headlines health, release clock, statement admit, builder
# --------------------------------------------------------------------------- #

from zoneinfo import ZoneInfo  # noqa: E402

_ET = ZoneInfo("America/New_York")


def _fed_feeds(outcomes: list[dict]) -> list[dict]:
    return outcomes


def test_build_current_fed_feed_outage_degrades_even_with_items(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-06T12:00:00Z",
        "feed_status": "mixed",
        "feeds": [
            {"name": "BEA - News Releases", "url": "https://apps.bea.gov/rss/rss.xml", "status": "ok", "item_count": 3},
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
             "status": "fail", "item_count": 0},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml",
             "status": "ok", "item_count": 1},
        ],
        "articles": [
            _fed_item("Warsh, In Our Time",
                      "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                      "2026-08-28T14:00:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "source_outage"
    assert out["headlines"]["fresh"] is False
    assert out["headlines"]["items"]


def test_build_current_mixed_feeds_ok_when_relevant_fed_ok(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-08T12:00:00Z",
        "feed_status": "mixed",
        "feeds": [
            {"name": "BEA - News Releases", "url": "https://apps.bea.gov/rss/rss.xml", "status": "fail", "item_count": 0},
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
             "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml",
             "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - All Press",
             "url": "https://www.federalreserve.gov/feeds/press_all.xml",
             "status": "ok", "item_count": 1},
        ],
        "articles": [
            _fed_item("Warsh, In Our Time",
                      "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                      "2026-08-28T14:00:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "ok"
    assert out["headlines"]["fresh"] is True


def test_build_current_stale_acquisition_over_24h(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-06T12:00:00Z",
        "feed_status": "ok",
        "feeds": [
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml", "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - All Press",
             "url": "https://www.federalreserve.gov/feeds/press_all.xml", "status": "ok", "item_count": 1},
        ],
        "articles": [
            _fed_item("Warsh, In Our Time",
                      "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                      "2026-08-28T14:00:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "stale"
    assert out["headlines"]["fresh"] is False
    assert out["headlines"]["items"]
    assert out["headlines"]["items"][0]["published_at"].startswith("2026-08-28")


def test_build_current_legacy_cache_without_fetched_at_not_fresh(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {"articles": [
        _fed_item("Warsh, In Our Time",
                  "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                  "2026-08-28T14:00:00+00:00"),
    ]})
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["fetched_at"] is None
    assert out["headlines"]["saved_date"] == "2026-09-06"
    assert out["headlines"]["fresh"] is False
    assert out["headlines"]["state"] == "ok"


def test_build_current_invalid_and_future_fetched_at(tmp_path):
    _write_official_cache(tmp_path, "2026-09-05", {"articles": [
        _fed_item("Warsh, In Our Time",
                  "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                  "2026-08-28T14:00:00+00:00"),
    ]})
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "not-a-timestamp",
        "articles": [
            _fed_item("Waller, The Economic Outlook",
                      "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm",
                      "2026-09-03T12:30:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "invalid_newest"
    assert out["headlines"]["fresh"] is not True
    assert out["headlines"]["items"] == []
    assert (out["headlines"].get("last_good") or {}).get("saved_date") == "2026-09-05"

    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-20T12:00:00Z",
        "articles": [
            _fed_item("Waller, The Economic Outlook",
                      "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm",
                      "2026-09-03T12:30:00+00:00"),
        ],
    })
    out2 = build_current(tmp_path, now=_CUTOFF)
    assert out2["headlines"]["state"] == "invalid_newest"
    assert out2["headlines"]["fresh"] is not True


def test_build_current_future_filename_day_invalid(tmp_path):
    _write_official_cache(tmp_path, "2026-09-20", {
        "fetched_at": "2026-09-08T12:00:00Z",
        "articles": [
            _fed_item("Warsh, In Our Time",
                      "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                      "2026-08-28T14:00:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "invalid_newest"
    assert out["headlines"]["fresh"] is not True


def test_build_current_successful_fed_zero_items_is_no_new(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-08T12:00:00Z",
        "feed_status": "ok",
        "feeds": [
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "status": "ok", "item_count": 0},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml", "status": "ok", "item_count": 0},
            {"name": "Federal Reserve - All Press",
             "url": "https://www.federalreserve.gov/feeds/press_all.xml", "status": "ok", "item_count": 0},
        ],
        "articles": [
            _fed_item("Federal Reserve Board announces termination of enforcement actions",
                      "https://www.federalreserve.gov/newsevents/pressreleases/enforcement20260904a.htm",
                      "2026-09-04T15:00:00+00:00"),
        ],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "no_new"
    assert out["headlines"]["fresh"] is False


def test_build_current_failed_input_cannot_be_no_new(tmp_path):
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-08T12:00:00Z",
        "feed_status": "failed",
        "feeds": [
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "status": "error", "item_count": 0},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml", "status": "error", "item_count": 0},
            {"name": "Federal Reserve - All Press",
             "url": "https://www.federalreserve.gov/feeds/press_all.xml", "status": "fail", "item_count": 0},
        ],
        "articles": [],
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["headlines"]["state"] == "source_outage"
    assert out["headlines"]["state"] != "no_new"


def test_build_current_release_clock_before_and_after_statement_time(tmp_path):
    _write_fomc(tmp_path, [_june_row(), _july_row()], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    before = datetime(2026, 9, 16, 13, 59, tzinfo=_ET)
    out_before = build_current(tmp_path, now=before)
    assert out_before["statement"]["state"] == "recorded"
    assert out_before["statement"]["decision_date"] == "2026-07-29"
    assert out_before["calendar"]["meetings"][0]["date"] == "2026-09-16"
    assert out_before["calendar"]["meetings"][0]["days_to"] == 0

    after = datetime(2026, 9, 16, 14, 1, tzinfo=_ET)
    out_after = build_current(tmp_path, now=after)
    assert out_after["statement"]["state"] == "awaiting_statement"
    assert out_after["statement"]["elapsed_decision"] == "2026-09-16"

    utc_midnight = datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc)
    out_utc = build_current(tmp_path, now=utc_midnight)
    assert out_utc["statement"]["state"] == "recorded"
    assert out_utc["statement"]["decision_date"] == "2026-07-29"


def test_build_current_strict_day_parse_rejects_trailing_junk(tmp_path):
    from engine import policy_watch_current as pwc
    assert pwc._parse_day("2026-09-16") == date(2026, 9, 16)
    assert pwc._parse_day("2026-09-16junk") is None
    assert pwc._parse_day("2026-09-16T14:00:00Z") is None


def test_build_current_rejects_malicious_or_mismatched_statement_url(tmp_path):
    bad = dict(_july_row())
    bad["url"] = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm?x=1"
    _write_fomc(tmp_path, [_june_row(), bad], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["statement"]["state"] == "unavailable"
    assert out["statement"]["url"] is None

    wrong_date = dict(_july_row())
    wrong_date["url"] = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260617a.htm"
    _write_fomc(tmp_path, [_june_row(), wrong_date], {
        "2026-06-17": _JUNE_STMT, "2026-07-29": _JULY_STMT,
    })
    out2 = build_current(tmp_path, now=_CUTOFF)
    assert out2["statement"]["state"] == "unavailable"


def test_build_current_oversized_statement_body_unavailable(tmp_path):
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": "x" * (4 * 1024 * 1024 + 10)})
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["statement"]["state"] == "unavailable"
    assert out["statement"]["reason"] == "statement_oversized_or_unreadable"


def test_build_current_malformed_ledger_skips_bad_rows(tmp_path):
    store = tmp_path / "data" / "marketing" / "fomc"
    (store / "statements").mkdir(parents=True, exist_ok=True)
    (store / "statements" / "2026-07-29.txt").write_text(_JULY_STMT, encoding="utf-8")
    (store / "statements.jsonl").write_text(
        "{not-json\n" + json.dumps(_july_row()) + "\n",
        encoding="utf-8",
    )
    out = build_current(tmp_path, now=_CUTOFF)
    assert out["statement"]["state"] == "recorded"
    assert out["statement"]["decision_date"] == "2026-07-29"


def test_builder_invalid_intel_json_still_renders_current(tmp_path, monkeypatch):
    import scripts.build_policy_watch as bpw
    from jinja2 import Environment, FileSystemLoader

    # Isolate ROOT/data for builder path via config monkeypatch.
    monkeypatch.setattr(bpw.config, "ROOT", tmp_path)
    monkeypatch.setattr(bpw.config, "data_dir", lambda: tmp_path / "data")
    (tmp_path / "data" / "policy").mkdir(parents=True)
    (tmp_path / "templates").mkdir(parents=True)
    # Minimal template stubs so builder can render.
    for name in ("policy_watch.html.j2", "_policy_watch_current.html.j2",
                 "_site_nav.html.j2", "_navlinks.html.j2"):
        src = ROOT / "templates" / name
        if src.exists():
            (tmp_path / "templates" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    # Copy only what render needs — use real templates from ROOT via monkeypatch of FileSystemLoader.
    monkeypatch.setattr(
        bpw, "Environment",
        lambda **kw: Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True),
    )
    (tmp_path / "data" / "policy" / "intel.json").write_text("{not-json", encoding="utf-8")
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": _JULY_STMT})
    _write_official_cache(tmp_path, "2026-09-06", {
        "fetched_at": "2026-09-08T12:00:00Z",
        "feeds": [
            {"name": "Federal Reserve - Monetary Policy",
             "url": "https://www.federalreserve.gov/feeds/press_monetary.xml", "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - Speeches",
             "url": "https://www.federalreserve.gov/feeds/speeches.xml", "status": "ok", "item_count": 1},
            {"name": "Federal Reserve - All Press",
             "url": "https://www.federalreserve.gov/feeds/press_all.xml", "status": "ok", "item_count": 1},
        ],
        "articles": [
            _fed_item("Warsh, In Our Time",
                      "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
                      "2026-08-28T14:00:00+00:00"),
        ],
    })
    (tmp_path / "site").mkdir(parents=True, exist_ok=True)
    # Disable history writers that touch real/sibling ledgers.
    monkeypatch.setattr(bpw, "decorate_lifecycle_view", lambda x: x)
    rc = bpw.main()
    assert rc == 0
    html = (tmp_path / "site" / "policy_watch.html").read_text(encoding="utf-8")
    assert "Background research unavailable" in html or "无法加载历史研究" in html
    assert "Next Fed decisions" in html
    assert "09-16" in html
    assert "Warsh, In Our Time" in html


def test_builder_composer_problem_renders_explanation(tmp_path, monkeypatch):
    import scripts.build_policy_watch as bpw
    from jinja2 import Environment, FileSystemLoader

    monkeypatch.setattr(bpw.config, "ROOT", tmp_path)
    monkeypatch.setattr(bpw.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(
        bpw, "Environment",
        lambda **kw: Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True),
    )
    (tmp_path / "data" / "policy").mkdir(parents=True)
    # Valid original July 13 intel preserved.
    intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    (tmp_path / "data" / "policy" / "intel.json").write_text(
        json.dumps(intel), encoding="utf-8",
    )
    assert intel.get("as_of") == "2026-07-13"

    def boom(*_a, **_k):
        raise RuntimeError("composer exploded")

    monkeypatch.setattr(bpw, "build_current", boom)
    (tmp_path / "site").mkdir(parents=True, exist_ok=True)
    rc = bpw.main()
    assert rc == 0
    html = (tmp_path / "site" / "policy_watch.html").read_text(encoding="utf-8")
    assert "Current official view problem" in html or "当前官方视图问题" in html
    assert "composer exploded" in html or "RuntimeError" in html
    assert "July 13, 2026" in html


# --------------------------------------------------------------------------- #
# R1 repair-1 — consolidated adversarial/regression suite (from the removed
# tests/test_policy_watch_release_regressions.py, folded in so CI's selected
# test_policy_watch_ui.py actually exercises it).
# --------------------------------------------------------------------------- #

from engine import macro_news as _r1_macro_news  # noqa: E402

_R1_NOW = datetime(2026, 9, 9, 22, 0, tzinfo=timezone.utc)
_R1_URL = "https://www.federalreserve.gov/newsevents/speech/waller20260903a.htm"
_R1_FEEDS = [
    {"url": f"https://www.federalreserve.gov/feeds/{name}.xml", "status": "ok"}
    for name in ("press_monetary", "press_all", "speeches")
]


def _r1_item(url: str = _R1_URL) -> dict:
    return {"title": "Source statement", "url": url, "seendate": "2026-09-03T12:30:00Z"}


def _r1_write(root: Path, day: str, blob: dict) -> Path:
    path = root / f"data/macro/official_news_cache/official_v3_{day}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob))
    return path


def test_r1_aggregate_failure_is_not_quiet(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [], "feed_status": "failed",
        "degraded_reason": "official_fetch_error", "fetched_at": "2026-09-09T20:00:00Z",
    })
    view = build_current(tmp_path, now=_R1_NOW)
    assert view["headlines"]["state"] == "source_outage"


def test_r1_legacy_aggregate_failure_without_timestamp_is_not_empty(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [], "degraded_reason": "official_fetch_error"})
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["state"] == "source_outage"


def test_r1_invalid_earlier_snapshot_is_not_last_good(tmp_path):
    _r1_write(tmp_path, "2026-09-07", {"articles": [_r1_item()], "fetched_at": "2099-01-01T00:00:00Z"})
    bad = _r1_write(tmp_path, "2026-09-09", {"articles": []})
    bad.write_text("{broken")
    fallback = build_current(tmp_path, now=_R1_NOW)["headlines"].get("last_good")
    assert not fallback or not fallback["items"]


def test_r1_one_bad_url_does_not_remove_valid_updates(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [
        _r1_item("https://www.federalreserve.gov:bad/newsevents/speech/x.htm"), _r1_item(),
    ]})
    view = build_current(tmp_path, now=_R1_NOW)
    assert [row["url"] for row in view["headlines"]["items"]] == [_R1_URL]


def test_r1_embedded_control_char_url_is_rejected_sibling_survives(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [
        _r1_item("https://www.federalreserve.gov/newsevents/speech/x\r\nEvil: 1.htm"), _r1_item(),
    ]})
    view = build_current(tmp_path, now=_R1_NOW)
    assert [row["url"] for row in view["headlines"]["items"]] == [_R1_URL]


def test_r1_userinfo_in_url_is_rejected_sibling_survives(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [
        _r1_item("https://user:pass@www.federalreserve.gov/newsevents/speech/x.htm"), _r1_item(),
    ]})
    view = build_current(tmp_path, now=_R1_NOW)
    assert [row["url"] for row in view["headlines"]["items"]] == [_R1_URL]


def test_r1_ledger_overflow_reports_unavailable_not_awaiting(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    padding = [{"date": f"1999-01-{(i % 28) + 1:02d}", "fetched_at": "1999-01-01T00:00:00Z", "url": ""}
               for i in range(600)]
    ledger.write_text("".join(json.dumps(row) + "\n" for row in padding + rows))
    statement = build_current(tmp_path, now=_R1_NOW)["statement"]
    assert statement["state"] == "unavailable"
    assert statement.get("reason") == "ledger_overflow"


def test_r1_overflow_does_not_hide_corrections_after_current_record(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows) + ("{}\n" * 501))
    assert build_current(tmp_path, now=_R1_NOW)["statement"]["state"] == "unavailable"


def test_r1_stale_successful_empty_feed_stays_stale(tmp_path):
    _r1_write(tmp_path, "2026-09-07", {
        "articles": [], "fetched_at": "2026-09-07T12:00:00Z", "feeds": _R1_FEEDS, "feed_status": "ok",
    })
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["state"] == "stale"


def test_r1_no_source_receipt_is_not_a_fresh_check(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z"})
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["fresh"] is False


def test_r1_unknown_empty_acquisition_is_not_confirmed_no_new(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [], "fetched_at": "2026-09-09T20:00:00Z"})
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["state"] != "no_new"


def test_r1_missing_new_decision_preserves_explicit_historical_record(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    view = build_current(tmp_path, now=datetime(2026, 9, 17, 18, tzinfo=timezone.utc))
    assert view["statement"]["state"] == "awaiting_statement"
    assert "2026-07-29" in json.dumps(view), "Latest missing must not erase last recorded historical decision"


def test_r1_html_login_is_not_a_successful_empty_feed():
    feed = {"name": "Federal Reserve - Monetary Policy", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml"}
    rejected = False
    try:
        _r1_macro_news._parse_feed("<html><body><h1>Login required</h1></body></html>", feed)
    except (ValueError, _r1_macro_news.ET.ParseError):
        rejected = True
    assert rejected, "HTTP200 HTML is not an empty RSS/Atom success"


def test_r1_statement_hash_mismatch_is_not_a_verified_record(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[-1]["sha"] = "0" * 64
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    statement = build_current(tmp_path, now=_R1_NOW)["statement"]
    assert statement["state"] == "unavailable"


def test_r1_future_statement_acquisition_is_not_a_verified_record(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[-1]["fetched_at"] = "2099-01-01T00:00:00Z"
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    statement = build_current(tmp_path, now=_R1_NOW)["statement"]
    assert statement["state"] == "unavailable"


def test_r1_prior_body_hash_mismatch_cannot_supply_comparison(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[0]["sha"] = "0" * 64
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    v = build_current(tmp_path, now=_R1_NOW)
    assert v["statement"]["state"] == "recorded"
    assert v["comparison"]["state"] == "unavailable"


def test_r1_prior_future_acquisition_cannot_supply_comparison(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[0]["fetched_at"] = "2099-01-01T00:00:00Z"
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert build_current(tmp_path, now=_R1_NOW)["comparison"]["state"] == "unavailable"


def test_r1_historical_fallback_uses_same_receipt_validation(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    ledger = tmp_path / "data/marketing/fomc/statements.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[-1]["sha"] = "0" * 64
    ledger.write_text("".join(json.dumps(row) + "\n" for row in rows))
    v = build_current(tmp_path, now=datetime(2026, 9, 17, 18, tzinfo=timezone.utc))
    assert (v["statement"].get("last_recorded") or {}).get("decision_date") != "2026-07-29"


def test_r1_spoofed_feed_name_or_url_cannot_establish_freshness(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z",
        "feeds": [{
            "name": "press_all.xml speeches.xml press_monetary.xml",
            "url": "https://example.invalid/feeds/press_all.xml", "status": "ok",
        }],
    })
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["fresh"] is False


def test_r1_incomplete_fed_feed_coverage_does_not_claim_fresh(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z", "feeds": _R1_FEEDS[:1]})
    assert build_current(tmp_path, now=_R1_NOW)["headlines"]["fresh"] is False


def test_r1_last_good_skips_bad_candidate_to_find_valid_older_snapshot(tmp_path):
    _r1_write(tmp_path, "2026-09-06", {"articles": [_r1_item()], "fetched_at": "2026-09-06T20:00:00Z", "feeds": _R1_FEEDS})
    _r1_write(tmp_path, "2026-09-07", {"articles": [_r1_item()], "fetched_at": "2099-01-01T00:00:00Z", "feeds": _R1_FEEDS})
    _r1_write(tmp_path, "2026-09-09", {"articles": []}).write_text("{broken")
    fallback = build_current(tmp_path, now=_R1_NOW)["headlines"].get("last_good")
    assert fallback and fallback["saved_date"] == "2026-09-06" and fallback["items"]


def test_r1_last_good_does_not_hide_failed_candidate_receipt(tmp_path):
    _r1_write(tmp_path, "2026-09-06", {"articles": [_r1_item()], "fetched_at": "2026-09-06T20:00:00Z", "feeds": _R1_FEEDS})
    _r1_write(tmp_path, "2026-09-07", {"articles": [_r1_item()], "fetched_at": "2026-09-07T20:00:00Z", "feed_status": "failed"})
    _r1_write(tmp_path, "2026-09-09", {"articles": []}).write_text("{broken")
    fallback = build_current(tmp_path, now=_R1_NOW)["headlines"].get("last_good")
    assert fallback and fallback["saved_date"] == "2026-09-06"


def _r1_render_page(current, intel=None, catalysts=None):
    from jinja2 import Environment, FileSystemLoader

    if intel is None:
        intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text(encoding="utf-8"))
    preds = intel.get("predictions") or []
    uk_desk = {
        "state": "gate_off", "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
        "body_en": "HM Treasury", "body_zh": "英国财政部", "source_label": "GOV.UK",
        "headline": None, "stance": None, "model_unavailable": False,
    }
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("policy_watch.html.j2").render(
        intel=intel,
        counts={"total": len(preds), "open": 0, "hit": 0, "miss": 0,
                "policy_action": 0, "market_outcome": 0, "hit_rate": None},
        desk=None, fed_stance=None, fed_hist={}, rot=None, rot_hist={},
        dates={"staleness": {"age_days": 57}}, catalysts=catalysts, scorecard=None,
        generated_utc="2026-09-08 12:00 UTC", verified_en="July 13, 2026", verified_zh="2026年7月13日",
        source_links=[], featured_predictions=[], brief=brief,
        active_section="research", active_page="policy_watch",
        lifecycle=None, current=current, uk_desk=uk_desk, background_unavailable=False,
    )


def test_r1_historical_record_is_visible_in_real_current_panel(tmp_path):
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    current = build_current(tmp_path, now=datetime(2026, 9, 17, 18, tzinfo=timezone.utc))
    html = _r1_render_page(current)
    panel = html.split('id="pw-last-decision">', 1)[1].split("</article>", 1)[0]
    assert "2026-07-29" in panel, "Historical record exists in Python but must reach the user"
    assert any(word in panel.lower() for word in ["historical", "earlier recorded", "earlier decision"])


def test_r1_recorded_vote_uses_source_facts_and_changes_with_input(tmp_path):
    _write_fomc(tmp_path, [_july_row()], {"2026-07-29": _JULY_STMT})
    html = _r1_render_page(build_current(tmp_path, now=_R1_NOW))
    panel = html.split('id="pw-last-decision">', 1)[1].split("</article>", 1)[0]
    assert "9" in panel and "3" in panel

    # A different (unanimous) elapsed decision must change the visible vote text
    # — not a fixed "9/3" baked into the template.
    tmp2 = tmp_path.parent / (tmp_path.name + "_2")
    june_row = {**_june_row(), "fetched_at": "2026-06-18T00:00:00Z"}
    _write_fomc(tmp2, [june_row], {"2026-06-17": _JUNE_STMT})
    html2 = _r1_render_page(build_current(tmp2, now=datetime(2026, 7, 1, tzinfo=timezone.utc)))
    panel2 = html2.split('id="pw-last-decision">', 1)[1].split("</article>", 1)[0]
    assert "12" in panel2 and "0" in panel2
    assert panel != panel2


def test_r1_missing_background_does_not_render_dead_toc_links(tmp_path):
    empty = {"as_of": "", "predictions": [], "fed": {"task_forces": []},
             "administration": {"verified_levers": [], "theaters": []},
             "rotation": {"targeted": [], "starved": []}, "sources": []}
    html = _r1_render_page(build_current(tmp_path, now=_R1_NOW), intel=empty)
    nav = html.split('<nav class="pw-toc"', 1)[1].split("</nav>", 1)[0]
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    dead = [target for target in re.findall(r'href="#([^"]+)"', nav) if target not in ids]
    assert not dead, f"TOC links to absent sections: {dead}"


def test_r1_missing_background_does_not_invent_legacy_fed_claims(tmp_path):
    empty = {"as_of": "", "predictions": [], "fed": {"task_forces": []},
             "administration": {"verified_levers": [], "theaters": []},
             "rotation": {"targeted": [], "starved": []}, "sources": []}
    html = _r1_render_page(build_current(tmp_path, now=_R1_NOW), intel=empty)
    assert "Warsh is pushing a stricter 2% target" not in html
    assert "Rule changes could make a later pivot easier" not in html


def test_r1_positive_calendar_uses_existing_next_decision(tmp_path):
    assert build_current(tmp_path, now=_R1_NOW)["calendar"]["meetings"][0]["date"] == "2026-09-16"


def test_r1_positive_valid_empty_rss_remains_empty():
    feed = {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml"}
    assert _r1_macro_news._parse_feed('<rss version="2.0"><channel><title>Fed</title></channel></rss>', feed) == []


def test_r1_positive_valid_update_survives_with_original_date(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {"articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z", "feeds": _R1_FEEDS})
    v = build_current(tmp_path, now=_R1_NOW)
    assert v["headlines"]["items"][0]["published_at"].startswith("2026-09-03")
    assert v["headlines"]["fresh"] is True


def test_r1_positive_original_44_calls_preserved_in_fresh_render():
    intel = json.loads((ROOT / "data" / "policy" / "intel.json").read_text())
    assert len(intel["predictions"]) == 44


# --------------------------------------------------------------------------- #
# R1 repair-1 — final UI treatment (scoped nowrap date column, minute-precision
# acquired label, closed bilingual Sources state labels, other-dates group)
# --------------------------------------------------------------------------- #

def test_r1_official_row_date_column_is_scoped_nowrap():
    template = (ROOT / "templates" / "policy_watch.html.j2").read_text(encoding="utf-8")
    assert '.pw-current .pw-event{grid-template-columns:100px minmax(0,1fr) auto}' in template
    assert '.pw-current .pw-date{white-space:nowrap;overflow-wrap:normal;word-break:normal}' in template


def test_r1_glance_shows_minute_precision_acquired_label(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z", "feeds": _R1_FEEDS,
    })
    current = build_current(tmp_path, now=_R1_NOW)
    assert current["headlines"]["fetched_at_display"] == "2026-09-09 20:00 UTC"
    html = _r1_render_page(current)
    glance = html.split('id="pw-official-updates">', 1)[1].split("</article>", 1)[0]
    assert "Last checked" in glance and "2026-09-09 20:00 UTC" in glance
    visible_text = re.sub(r'\sdata-[\w-]+="[^"]*"', "", glance)
    assert "2026-09-09T20:00:00Z" not in visible_text
    sources = html.split('id="pw-sources-changes">', 1)[1]
    assert "2026-09-09T20:00:00Z" in sources


def test_r1_sources_state_labels_are_closed_bilingual_not_raw_tokens(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [], "feed_status": "failed",
        "degraded_reason": "official_fetch_error", "fetched_at": "2026-09-09T20:00:00Z",
    })
    current = build_current(tmp_path, now=_R1_NOW)
    assert current["headlines"]["state"] == "source_outage"
    html = _r1_render_page(current)
    sources = html.split('id="pw-sources-changes">', 1)[1]
    assert "Some sources did not answer" in sources and "部分来源未响应" in sources
    assert "source_outage" not in sources


def test_r1_unknown_headline_state_falls_back_to_closed_default_label():
    current = {
        "schema": "policy_watch_current.v1", "calendar": {"state": "scheduled", "meetings": []},
        "headlines": {"state": "totally_unrecognized_token", "items": [], "fetched_at": None, "saved_date": None},
        "statement": {"state": "none"}, "comparison": {"state": "unavailable"},
    }
    html = _r1_render_page(current)
    assert "Official updates unavailable" in html and "官方动态暂不可用" in html
    assert "totally_unrecognized_token" not in html


def test_r1_other_policy_dates_group_shown_when_non_fomc_upcoming_exists():
    catalysts = {"spine": [
        {"date": "2026-09-25", "event_en": "CPI release", "event_zh": "CPI 数据发布", "past": False, "days_to": 16},
        {"date": "2026-09-16", "event_en": "FOMC rate decision", "event_zh": "FOMC 利率决议", "past": False, "days_to": 7},
    ]}
    html = _r1_render_page({"calendar": {"state": "scheduled", "meetings": []},
                             "headlines": {"state": "missing", "items": []},
                             "statement": {"state": "none"}, "comparison": {"state": "unavailable"}},
                            catalysts=catalysts)
    assert "Other policy dates" in html and "其他政策日期" in html
    assert "CPI release" in html


def test_r1_other_policy_dates_excludes_actual_producer_decision_label():
    # data/policy/intel.json's real catalyst spine uses "FOMC rate decision",
    # not "FOMC decision" (that's the calendar-meetings label) — both aliases
    # must be excluded, case-insensitively, or this duplicates the decision.
    catalysts = {"spine": [
        {"date": "2026-09-16", "event_en": "FOMC rate decision", "event_zh": "FOMC 利率决议", "past": False, "days_to": 7},
        {"date": "2026-10-28", "event_en": "fomc decision", "event_zh": "FOMC决议", "past": False, "days_to": 50},
    ]}
    html = _r1_render_page({"calendar": {"state": "scheduled", "meetings": []},
                             "headlines": {"state": "missing", "items": []},
                             "statement": {"state": "none"}, "comparison": {"state": "unavailable"}},
                            catalysts=catalysts)
    other = html.split("Other policy dates", 1)[1] if "Other policy dates" in html else ""
    assert "FOMC rate decision" not in other
    assert "fomc decision" not in other.lower()


def test_r1_other_policy_dates_keeps_legitimate_fomc_related_event():
    catalysts = {"spine": [
        {"date": "2026-09-20", "event_en": "FOMC minutes release", "event_zh": "FOMC会议纪要发布", "past": False, "days_to": 11},
    ]}
    html = _r1_render_page({"calendar": {"state": "scheduled", "meetings": []},
                             "headlines": {"state": "missing", "items": []},
                             "statement": {"state": "none"}, "comparison": {"state": "unavailable"}},
                            catalysts=catalysts)
    assert "Other policy dates" in html
    assert "FOMC minutes release" in html


def test_r1_other_policy_dates_group_hidden_when_empty():
    html = _r1_render_page({"calendar": {"state": "scheduled", "meetings": []},
                             "headlines": {"state": "missing", "items": []},
                             "statement": {"state": "none"}, "comparison": {"state": "unavailable"}},
                            catalysts=None)
    assert "Other policy dates" not in html and "其他政策日期" not in html


def test_r1_legacy_snapshot_cannot_render_sources_checked(tmp_path):
    _r1_write(tmp_path, "2026-09-07", {"articles": [_r1_item()]})
    view = build_current(tmp_path, now=_R1_NOW)
    html = _r1_render_page(view)
    details = html.split('id="pw-sources-changes">', 1)[1].split("</details>", 1)[0]
    assert "Sources checked" not in details
    assert "Saved records" in details and "已保存记录" in details


def test_r1_fallback_metadata_matches_the_records_actually_shown(tmp_path):
    _r1_write(tmp_path, "2026-09-07", {
        "articles": [_r1_item()], "fetched_at": "2026-09-07T20:00:00Z", "feeds": _R1_FEEDS,
    })
    _r1_write(tmp_path, "2026-09-09", {"articles": []}).write_text("{broken")
    view = build_current(tmp_path, now=_R1_NOW)
    html = _r1_render_page(view)
    panel = html.split('id="pw-official-updates">', 1)[1].split("</article>", 1)[0]
    assert 'data-fetched-at="2026-09-07T20:00:00Z"' in panel
    assert "Last checked" not in panel  # earlier fallback, never labeled a new check


def test_r1_complete_current_receipt_can_render_sources_checked(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z", "feeds": _R1_FEEDS,
    })
    html = _r1_render_page(build_current(tmp_path, now=_R1_NOW))
    details = html.split('id="pw-sources-changes">', 1)[1].split("</details>", 1)[0]
    assert "Sources checked" in details


def test_r1_aggregate_ok_alone_cannot_claim_scoped_fed_freshness(tmp_path):
    _r1_write(tmp_path, "2026-09-09", {
        "articles": [_r1_item()], "fetched_at": "2026-09-09T20:00:00Z", "feed_status": "ok",
    })
    view = build_current(tmp_path, now=_R1_NOW)
    assert view["headlines"]["fed_feed_health"] is None
    assert view["headlines"]["fresh"] is False


# --------------------------------------------------------------------------- #
# R1 final fail-closed repair — fallback proof and unreadable statement bodies
# --------------------------------------------------------------------------- #


def test_r1_unknown_empty_snapshot_is_not_last_good(tmp_path):
    """An empty cache with no acquisition/feed receipt is not a usable fallback."""
    _r1_write(tmp_path, "2026-09-08", {"articles": []})
    _r1_write(tmp_path, "2026-09-09", {"articles": []}).write_text("{broken")

    fallback = build_current(tmp_path, now=_R1_NOW)["headlines"].get("last_good")

    assert fallback is None


def test_r1_invalid_utf8_statement_is_unavailable_not_exception(tmp_path):
    """A corrupt stored statement must fail closed without taking down the page."""
    shutil.copytree(ROOT / "data/marketing/fomc", tmp_path / "data/marketing/fomc")
    statement_path = tmp_path / "data/marketing/fomc/statements/2026-07-29.txt"
    statement_path.write_bytes(b"\xff\xfe\x80")

    statement = build_current(tmp_path, now=_R1_NOW)["statement"]

    assert statement["state"] == "unavailable"
    assert statement.get("reason") == "statement_oversized_or_unreadable"


def test_r1_unverified_fallback_copy_does_not_claim_success(tmp_path):
    """A legacy saved record may be shown, but its acquisition was not proven."""
    _r1_write(tmp_path, "2026-09-08", {"articles": [_r1_item()]})
    _r1_write(tmp_path, "2026-09-09", {"articles": []}).write_text("{broken")

    html = _r1_render_page(build_current(tmp_path, now=_R1_NOW))
    panel = html.split('id="pw-official-updates">', 1)[1].split("</article>", 1)[0]

    assert "earlier successful copy" not in panel.lower()
    assert "earlier saved copy" in panel.lower()
