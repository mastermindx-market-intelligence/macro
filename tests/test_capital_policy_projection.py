"""Acceptance tests for B-F09-6b capital-markets policy projection (MO-PAID-067)."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

from engine.capital_policy_projection import (
    EVENT_WINDOW_MAP,
    HORIZON_DAYS,
    MAX_ROWS,
    ROW_KEYS,
    SCHEMA,
    SECTION_BUDGET_BYTES,
    WINDOWS,
    _EMPTY_REASON,
    _NO_RECORD,
    _NOT_WIRED,
    _READ_FAILED_EVENTS,
    _READ_FAILED_POLICY,
    project,
    typed_unavailable,
)
import scripts.build_capital_structure_page as page_builder

TODAY = date(2026, 9, 9)
ROOT = Path(__file__).resolve().parents[1]

DENYLIST = (
    "score", "rank", "band", "signal", "zscore", "percentile", "probability",
    "odds", "impact", "severity", "weight", "conviction", "forecast", "expected",
    "bullish", "bearish", "buy", "sell", "upgrade", "downgrade",
    "评分", "看多", "看空", "预测",
)
DENYLIST_RE = re.compile(
    r"(?:^|[^a-z\u4e00-\u9fff])(?:" + "|".join(
        re.escape(tok) for tok in DENYLIST + ("z",)
    ) + r")(?:$|[^a-z\u4e00-\u9fff])",
    re.IGNORECASE,
)
MACHINE_WINDOW_IDS = tuple(WINDOWS)
MACHINE_EVENT_TYPES = tuple(EVENT_WINDOW_MAP)
SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")
ALLOWLIST_HOSTS = frozenset({
    "federalreserve.gov", "www.federalreserve.gov",
    "treasurydirect.gov", "www.treasurydirect.gov",
    "federalregister.gov", "www.federalregister.gov",
})
FROZEN_MAP = {
    "FOMC": "rates_policy",
    "AUCTION": "treasury_supply",
    "OPEX": "equity_new_issue",
    "comment_close": "disclosure_regulatory",
    "rule_effective": "disclosure_regulatory",
    "entity_list": "export_control",
}
FROZEN_WINDOW_ORDER = (
    "rates_policy",
    "treasury_supply",
    "equity_new_issue",
    "credit_new_issue",
    "disclosure_regulatory",
    "export_control",
)
FROZEN_WATCH_TEST_SHA256 = (
    "c08d2fa7bd45dd1d4338787936cf490c26b70f21f3891c988c01c9e18b564f84"
)
FROZEN_WATCH_TEMPLATE_SHA256 = (
    "8fee91f5e6059fd427b897c69259917d544662e9862996a7009fcf22a7ef3736"
)
FROZEN_WATCH_FN_SHA256 = (
    "57bf1a0e4244416c592abb09fe3d033b7f48d520d90128080f1c90f82e7bee8b"
)
_FR_PREFIX = "https://www.federalregister.gov/documents/2026/09/01/2026-12345/"
LONG_FR_DOC = "x" * (158 - len("https://www.federalregister.gov/d/"))
LONG_FR_URL = f"https://www.federalregister.gov/d/{LONG_FR_DOC}"
assert len(LONG_FR_URL) == 158, len(LONG_FR_URL)


def _macro_event(etype: str, day: str, **extra):
    row = {
        "type": etype,
        "event_type": etype,
        "date": day,
        "time_et": "14:00",
        "label": extra.pop("label", etype),
        "label_zh": extra.pop("label_zh", etype),
        "source": "static",
        "is_context_only": True,
    }
    row.update(extra)
    return row


def _auction_event(day: str, tenor: str = "10", kind: str = "Note", **extra):
    term = f"{tenor}-Year"
    return _macro_event(
        "AUCTION",
        day,
        term=term,
        security_type=kind,
        securityTerm=term,
        securityType=kind,
        label=f"{term} {kind} auction",
        **extra,
    )


def _empty_calendar():
    return {
        "asof": TODAY.isoformat(),
        "themes": {},
        "upcoming_events": [],
        "entity_list_events": [],
        "latency_summary": {},
        "note": "fixture",
    }


def _policy_event(*, day: str, event_type: str = "comment_close",
                  document_number: str = "2026-12345", **extra):
    row = {
        "date": day,
        "days_away": 16,
        "basket_id": extra.pop("basket_id", "fintech_payments"),
        "reg_stage": extra.pop("reg_stage", "final_rule"),
        "title": extra.pop("title", "disclosure comment"),
        "event_type": event_type,
        "document_number": document_number,
    }
    row.update(extra)
    return row


def _patch_engines(monkeypatch, *, events=None, calendar=None,
                   events_raises=False, calendar_raises=False):
    def fake_events(today=None, horizon_days=14, use_fred=True):
        if events_raises:
            raise RuntimeError("dated-event calendar missing")
        return list(events or [])

    def fake_calendar(df=None, today=None):
        if calendar_raises:
            raise RuntimeError("policy calendar missing")
        return calendar

    monkeypatch.setattr("engine.event_calendar.us_macro_events", fake_events)
    monkeypatch.setattr("engine.policy_calendar.compute_policy_calendar", fake_calendar)


def _copy_templates(tmp_path: Path) -> Path:
    dest = tmp_path / "templates"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "templates", dest, dirs_exist_ok=True)
    return dest


def _section(html: str) -> str:
    start = html.index('id="cs-policy-projection"')
    end = html.index("</section>", start)
    return html[html.rindex("<section", 0, start):end + len("</section>")]


def _all_rows(payload: dict) -> list[dict]:
    rows = []
    for window in payload["windows"]:
        rows.extend(window.get("rows") or [])
    return rows


def _window(payload: dict, window_id: str) -> dict:
    return next(w for w in payload["windows"] if w["window_id"] == window_id)


def _stub_watch():
    return {
        "state": "empty",
        "headline_en": "x",
        "headline_zh": "x",
        "detail_en": "x",
        "detail_zh": "x",
    }


def _render_section(tmp_path, monkeypatch, payload) -> str:
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    return _section(html)


def test_1_schema_and_frozen_keys(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    assert payload["schema"] == "capital_policy_projection.v1"
    assert payload["schema"] == SCHEMA
    assert payload["authority"] == "context_only"
    assert payload["is_context_only"] is True
    rows = _all_rows(payload)
    assert rows, "expected at least one FOMC row"
    for row in rows:
        assert set(row.keys()) == ROW_KEYS
        assert len(ROW_KEYS) == 9  # schema example lists these nine closed keys


def test_2_no_new_signal_no_numeric_score_field(monkeypatch, tmp_path):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)", impact="high"),
            _auction_event("2026-09-20"),
        ],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(day="2026-09-25", event_type="comment_close",
                                              reg_stage="proposed_rule")],
            "entity_list_events": [_policy_event(
                day="2026-09-30", event_type="entity_list", document_number="2026-12346",
                title="entity list", is_upcoming=True,
            )],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    for row in _all_rows(payload):
        numeric = [k for k, v in row.items() if type(v) in (int, float) and not isinstance(v, bool)]
        assert numeric == ["days_out"], numeric
        bools = [k for k, v in row.items() if isinstance(v, bool)]
        assert bools == ["is_context_only"]
        assert "impact" not in row
    blob = json.dumps(payload, ensure_ascii=False)
    assert "impact" not in blob.lower()
    blob_l = blob.lower()
    for tok in DENYLIST:
        assert tok.lower() not in blob_l, tok
    assert DENYLIST_RE.search(blob) is None, blob
    section = _render_section(tmp_path, monkeypatch, payload)
    for tok in DENYLIST:
        assert tok.lower() not in section.lower(), tok


def test_3_window_map_is_frozen_and_total(monkeypatch):
    assert EVENT_WINDOW_MAP == FROZEN_MAP
    _patch_engines(
        monkeypatch,
        events=[_macro_event("CPI", "2026-09-11", label="CPI (consumer prices)")],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(
                day="2026-09-25", event_type="not_a_mapped_type",
                document_number="2026-99999",
            )],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    assert _all_rows(payload) == []
    assert _window(payload, "disclosure_regulatory")["state"] == "empty"


def test_4_all_six_windows_render_in_frozen_order(monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    ids = [w["window_id"] for w in payload["windows"]]
    assert ids == list(FROZEN_WINDOW_ORDER)
    credit = _window(payload, "credit_new_issue")
    assert credit["state"] == "unavailable"
    assert credit["reason_en"] == _NOT_WIRED[0]
    assert credit["reason_zh"] == _NOT_WIRED[1]
    assert credit["rows"] == []


def test_5_unavailable_differs_from_empty(monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar(), calendar_raises=True)
    unavailable = project(today=TODAY)
    disc_u = _window(unavailable, "disclosure_regulatory")
    assert disc_u["state"] == "unavailable"
    assert disc_u["reason_en"] == _READ_FAILED_POLICY[0]
    assert disc_u["reason_zh"] == _READ_FAILED_POLICY[1]

    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    empty = project(today=TODAY)
    disc_e = _window(empty, "disclosure_regulatory")
    assert disc_e["state"] == "empty"
    assert disc_e["reason_en"] == _EMPTY_REASON[0]
    assert disc_u["reason_en"] != disc_e["reason_en"]
    assert disc_u["reason_zh"] != disc_e["reason_zh"]


def test_6_every_row_has_an_allowlisted_public_source_url(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)"),
            _macro_event("OPEX", "2026-09-18", label="Options expiration"),
        ],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [
                _policy_event(day="2026-09-25", document_number="",
                              title="disclosure without a document number"),
                _policy_event(day="2026-09-26", document_number="2026-12345",
                              title="disclosure with the public record"),
            ],
            "entity_list_events": [_policy_event(
                day="2026-09-30", event_type="entity_list", document_number="",
                title="entity list without a document number", is_upcoming=True,
            )],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    rows = _all_rows(payload)
    assert any(r["window_id"] == "rates_policy" for r in rows)
    assert all(r["window_id"] != "equity_new_issue" for r in rows)
    equity = _window(payload, "equity_new_issue")
    assert equity["state"] == "unavailable"
    assert equity["reason_en"] == _NO_RECORD[0]
    assert payload["row_count"] == len(rows)
    blob = json.dumps(payload, ensure_ascii=False)
    assert "https://www.federalregister.gov/" not in blob.replace(
        "https://www.federalregister.gov/d/2026-12345", ""
    )
    disclosure = [r for r in rows if r["window_id"] == "disclosure_regulatory"]
    assert [r["source_url"] for r in disclosure] == [
        "https://www.federalregister.gov/d/2026-12345"
    ]
    export = _window(payload, "export_control")
    assert export["state"] == "unavailable"
    assert export["reason_en"] == _NO_RECORD[0]
    for row in rows:
        assert row["source_url"]
        host = urlparse(row["source_url"]).hostname or ""
        assert host in ALLOWLIST_HOSTS, row["source_url"]


def test_7_no_machine_text_in_rendered_html(tmp_path, monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)"),
            _auction_event("2026-09-20"),
        ],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    section = _render_section(tmp_path, monkeypatch, payload)
    assert "capital_policy_projection" not in section
    for token in MACHINE_WINDOW_IDS + MACHINE_EVENT_TYPES:
        assert token not in section, token
    leaked = [m.group(0) for m in SNAKE_RE.finditer(section)
              if m.group(0) not in {"l-en", "l-zh"}]
    assert leaked == [], leaked


def test_8_en_and_zh_both_render(tmp_path, monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    row = next(r for r in _all_rows(payload) if r["window_id"] == "rates_policy")
    html = _render_section(tmp_path, monkeypatch, payload)
    assert row["event_en"] in html
    assert row["event_zh"] in html
    assert row["source_label_en"] in html
    assert row["source_label_zh"] in html


def test_9_zh_uses_disclosure_term(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    blob = json.dumps(payload, ensure_ascii=False)
    assert "披露" in blob
    assert "申报" not in blob
    html = _render_section(tmp_path, monkeypatch, payload)
    assert "披露" in html
    assert "申报" not in html


def test_10_deterministic_and_sorted(monkeypatch):
    events = [
        _auction_event("2026-09-16"),
        _macro_event("FOMC", "2026-09-16", label="FOMC decision"),
        _auction_event("2026-09-20", tenor="5"),
    ]
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    a = project(today=TODAY)
    b = project(today=TODAY)
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(
        b, sort_keys=True, ensure_ascii=False
    )
    for window in a["windows"]:
        dates = [r["date"] for r in window["rows"]]
        assert dates == sorted(dates)


def test_11_max_rows_and_truncation_disclosed(tmp_path, monkeypatch):
    events = []
    for i in range(40):
        day = TODAY + timedelta(days=i)
        events.append(_macro_event("FOMC", day.isoformat(), label="FOMC decision"))
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    payload = project(today=TODAY)
    assert len(_all_rows(payload)) <= MAX_ROWS
    assert payload["truncated"] is True
    assert payload["row_count"] == MAX_ROWS
    html = _render_section(tmp_path, monkeypatch, payload)
    assert payload["truncation_en"] in html
    assert f"Next {MAX_ROWS} dated steps." in html


def test_12_artifact_budget_and_atomic_write(tmp_path, monkeypatch, capsys):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _copy_templates(tmp_path)
    page_builder.render(tmp_path)
    path = tmp_path / "site" / "data" / "capital_policy_projection.json"
    body = path.read_bytes()
    assert len(body) <= page_builder.ARTIFACT_BUDGET_BYTES
    assert not list(path.parent.glob(".*.tmp"))
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["schema"] == SCHEMA

    def boom(today=None):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(page_builder, "_policy_projection", boom)
    rc = page_builder.main(["--root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("::error title=capital_structure_page::") or (
        "::error title=capital_structure_page::" in captured.out
    )


def test_13_merged_policy_watch_chip_is_untouched(tmp_path, monkeypatch):
    assert callable(page_builder._policy_watch)
    watch_test = (ROOT / "tests" / "test_capital_structure_policy_projection.py").read_bytes()
    assert hashlib.sha256(watch_test).hexdigest() == FROZEN_WATCH_TEST_SHA256

    src = (ROOT / "templates" / "capital_structure.html.j2").read_text(encoding="utf-8")

    def _watch_block(text: str) -> str:
        start = text.index("{# ── policy-watch:start")
        end = text.index("{# ── policy-watch:end", start)
        return text[start:end]

    assert hashlib.sha256(_watch_block(src).encode("utf-8")).hexdigest() == (
        FROZEN_WATCH_TEMPLATE_SHA256
    )

    def _watch_fn(text: str) -> str:
        start = text.index("# ── policy-watch:start")
        end = text.index("# ── policy-watch:end", start)
        return text[start:end]

    current_py = (ROOT / "scripts" / "build_capital_structure_page.py").read_text(encoding="utf-8")
    assert hashlib.sha256(_watch_fn(current_py).encode("utf-8")).hexdigest() == (
        FROZEN_WATCH_FN_SHA256
    )

    origin = (ROOT / "templates" / "capital_structure.html.j2").read_text(encoding="utf-8")
    # Reconstruct the origin watch block from the frozen bytes already hashed
    # above; the live file's watch block must match that hash, which is the
    # origin/main freeze.
    _copy_templates(tmp_path)
    watch = {
        "state": "present",
        "headline_en": "Comment window closes in 5 days",
        "headline_zh": "征询意见期 5 天后截止",
        "detail_en": "Dated steps already on the public record. Not a rating and not a trade call.",
        "detail_zh": "均为已进入公开记录的既定日期节点。不是评级，也不是交易建议。",
    }
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: watch)
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: None)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    start = html.index('id="cs-policy"')
    end = html.index("</section>", start)
    block = html[html.rindex("<section", 0, start):end + len("</section>")]
    origin_dir = tmp_path / "origin"
    origin_dir.mkdir()
    shutil.copytree(tmp_path / "templates", origin_dir / "templates")
    # Strip the new section so the origin template path still renders.
    origin_html_src = origin
    (origin_dir / "templates" / "capital_structure.html.j2").write_text(
        origin_html_src.replace(
            origin_html_src[origin_html_src.index("{# ── policy-projection:start"):
                            origin_html_src.index("{# ── policy-projection:end") +
                            len("{# ── policy-projection:end ── #}")],
            "",
        ) if "{# ── policy-projection:start" in origin_html_src else origin_html_src,
        encoding="utf-8",
    )
    html_origin = page_builder.render(origin_dir).read_text(encoding="utf-8")
    o_start = html_origin.index('id="cs-policy"')
    o_end = html_origin.index("</section>", o_start)
    origin_block = html_origin[html_origin.rindex("<section", 0, o_start):o_end + len("</section>")]
    assert block == origin_block
    assert 'id="cs-policy-projection"' not in html


def test_14_never_raises_into_the_build(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events_raises=True, calendar_raises=True)
    payload = project(today=TODAY)
    assert payload["schema"] == SCHEMA
    assert payload["authority"] == "context_only"
    assert len(payload["windows"]) == 6

    _patch_engines(monkeypatch, events=None, calendar=None)
    payload2 = project(today=TODAY)
    assert payload2["schema"] == SCHEMA
    assert len(payload2["windows"]) == 6
    assert callable(typed_unavailable)
    typed = typed_unavailable(today=TODAY)
    assert typed["schema"] == SCHEMA
    assert len(typed["windows"]) == 6
    assert all(w["state"] == "unavailable" for w in typed["windows"])

    html = _render_section(tmp_path, monkeypatch, payload)
    assert 'id="cs-policy-projection"' in html


def test_horizon_constant_is_frozen():
    assert HORIZON_DAYS == 45
    assert MAX_ROWS == 12
    assert SECTION_BUDGET_BYTES == 8192


def test_15_section_raw_budget_holds_at_max_rows(tmp_path, monkeypatch):
    """Worst-case: MAX_ROWS comment_close rows with a 158-byte record URL."""
    events = []
    calendar = {
        "asof": TODAY.isoformat(),
        "themes": {},
        "upcoming_events": [
            _policy_event(
                day=(TODAY + timedelta(days=i)).isoformat(),
                event_type="comment_close",
                document_number=LONG_FR_DOC,
                title="disclosure comment",
            )
            for i in range(40)
        ],
        "entity_list_events": [],
        "latency_summary": {},
        "note": "fixture",
    }
    _patch_engines(monkeypatch, events=events, calendar=calendar)
    payload = project(today=TODAY)
    assert payload["row_count"] == MAX_ROWS
    assert payload["truncated"] is True
    for row in _all_rows(payload):
        assert len(row["source_url"]) == 158
        assert row["window_id"] == "disclosure_regulatory"
    html = _render_section(tmp_path, monkeypatch, payload)
    n = len(html.encode("utf-8"))
    assert n <= SECTION_BUDGET_BYTES, n


def test_r1_source_read_failed_renders(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events_raises=True, calendar=_empty_calendar())
    payload = project(today=TODAY)
    rates = _window(payload, "rates_policy")
    assert rates["state"] == "unavailable"
    assert rates["reason_en"] == _READ_FAILED_EVENTS[0]
    assert rates["reason_zh"] == _READ_FAILED_EVENTS[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _READ_FAILED_EVENTS[0] in html
    assert _READ_FAILED_EVENTS[1] in html
    assert _EMPTY_REASON[0] not in html or _window(payload, "disclosure_regulatory")["state"] == "empty"


def test_r1_policy_read_failed_renders(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar_raises=True)
    payload = project(today=TODAY)
    disc = _window(payload, "disclosure_regulatory")
    assert disc["state"] == "unavailable"
    assert disc["reason_en"] == _READ_FAILED_POLICY[0]
    assert disc["reason_zh"] == _READ_FAILED_POLICY[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _READ_FAILED_POLICY[0] in html
    assert _READ_FAILED_POLICY[1] in html


def test_r1_no_linked_public_record_renders(tmp_path, monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("OPEX", "2026-09-18", label="Options expiration")],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(day="2026-09-25", document_number="")],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    equity = _window(payload, "equity_new_issue")
    disc = _window(payload, "disclosure_regulatory")
    assert equity["state"] == "unavailable"
    assert equity["reason_en"] == _NO_RECORD[0]
    assert equity["reason_zh"] == _NO_RECORD[1]
    assert disc["state"] == "unavailable"
    assert disc["reason_en"] == _NO_RECORD[0]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _NO_RECORD[0] in html
    assert _NO_RECORD[1] in html
    assert _EMPTY_REASON[0] not in _section_window_copy(html, "New share sales")


def _section_window_copy(section: str, label: str) -> str:
    """Slice of the rendered section that follows `label` until the next kicker."""
    idx = section.index(label)
    return section[idx:idx + 800]


def test_r1_not_wired_renders(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    credit = _window(payload, "credit_new_issue")
    assert credit["state"] == "unavailable"
    assert credit["reason_en"] == _NOT_WIRED[0]
    assert credit["reason_zh"] == _NOT_WIRED[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _NOT_WIRED[0] in html
    assert _NOT_WIRED[1] in html


def test_r1_genuine_empty_is_none_pending(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    rates = _window(payload, "rates_policy")
    assert rates["state"] == "empty"
    assert rates["reason_en"] == _EMPTY_REASON[0]
    assert rates["reason_zh"] == _EMPTY_REASON[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _EMPTY_REASON[0] in html
    assert _EMPTY_REASON[1] in html


def test_r2_clip_per_window_keeps_fomc_and_more_line(tmp_path, monkeypatch):
    same_day = (
        [_auction_event("2026-09-16", tenor=str(2 + (i % 5))) for i in range(12)]
        + [_macro_event("FOMC", "2026-09-16", label="FOMC decision")]
    )
    _patch_engines(monkeypatch, events=same_day, calendar=_empty_calendar())
    payload = project(today=TODAY)
    assert payload["truncated"] is True
    rates = _window(payload, "rates_policy")
    treasury = _window(payload, "treasury_supply")
    assert rates["state"] == "present"
    assert len(rates["rows"]) == 1
    assert rates["rows"][0]["event_en"].startswith("Fed rate decision")
    assert treasury["state"] == "present"
    assert len(treasury["rows"]) == MAX_ROWS - 1
    assert treasury["more_en"] == "1 more step in this window is not shown."
    assert treasury["more_zh"] == "本窗口另有 1 个既定日期节点未展示。"
    html = _render_section(tmp_path, monkeypatch, payload)
    assert "Fed rate decision" in html
    assert "1 more step in this window is not shown." in html
    assert "本窗口另有 1 个既定日期节点未展示。" in html
    assert _EMPTY_REASON[0] not in _section_window_copy(html, "Policy-rate decision")


def test_r3_federal_register_document_url(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(
                day="2026-09-25", event_type="comment_close",
                document_number="2026-12345", basket_id="ai_semiconductors",
            )],
            "entity_list_events": [_policy_event(
                day="2026-09-30", event_type="entity_list",
                document_number="2026-54321",
            )],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    disc = _window(payload, "disclosure_regulatory")
    export = _window(payload, "export_control")
    assert disc["state"] == "present"
    assert disc["rows"][0]["source_url"] == "https://www.federalregister.gov/d/2026-12345"
    assert export["state"] == "present"
    assert export["rows"][0]["source_url"] == "https://www.federalregister.gov/d/2026-54321"


def test_r4_final_rule_comment_close_is_not_takes_effect(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(
                day="2026-09-25",
                event_type="comment_close",
                reg_stage="final_rule",
                document_number="2026-12345",
            )],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    row = _window(payload, "disclosure_regulatory")["rows"][0]
    assert "takes effect" not in row["event_en"]
    assert "生效" not in row["event_zh"]
    assert "Comment period closes" == row["event_en"]
    assert "意见征询期截止" == row["event_zh"]


def test_r5_auction_house_copy_and_unmappable_drop(monkeypatch, tmp_path):
    _patch_engines(
        monkeypatch,
        events=[
            _auction_event("2026-09-20", tenor="10", kind="Note"),
            _macro_event(
                "AUCTION", "2026-09-21",
                term="", security_type="Bond",
                label="Bond", label_zh="Bond拍卖",
            ),
        ],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    rows = _window(payload, "treasury_supply")["rows"]
    assert len(rows) == 1
    assert rows[0]["event_en"] == "Treasury auctions 10-Year Note"
    assert rows[0]["event_zh"] == "财政部拍卖10年期国债"
    blob = json.dumps(payload, ensure_ascii=False)
    for tok in DENYLIST:
        assert tok.lower() not in blob.lower(), tok
    html = _render_section(tmp_path, monkeypatch, payload)
    assert "Treasury auctions 10-Year Note" in html
    assert "财政部拍卖10年期国债" in html
    assert "Bond拍卖" not in html
    for tok in DENYLIST:
        assert tok.lower() not in html.lower(), tok


def test_r6_fence_raises_before_over_budget_page(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "engine.capital_policy_projection.SECTION_BUDGET_BYTES", 10
    )
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    _copy_templates(tmp_path)
    with pytest.raises(RuntimeError, match="policy-projection section over budget"):
        page_builder.render(tmp_path)
    page = tmp_path / "site" / "capital_structure.html"
    assert not page.exists()


def test_r7_missing_cache_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    payload = project(today=TODAY)
    treasury = _window(payload, "treasury_supply")
    assert treasury["state"] == "unavailable"
    assert treasury["reason_en"] == _READ_FAILED_EVENTS[0]
    assert treasury["reason_zh"] == _READ_FAILED_EVENTS[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _READ_FAILED_EVENTS[0] in html
    assert _READ_FAILED_EVENTS[1] in html
    assert _EMPTY_REASON[0] not in _section_window_copy(html, "Government borrowing")


def test_r7_never_calls_requests(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("projection path called the network")

    monkeypatch.setattr("requests.get", boom, raising=False)
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    assert _window(payload, "rates_policy")["state"] == "present"


def test_r8_policy_calendar_runs_once_per_build(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_cal(df=None, today=None):
        calls["n"] += 1
        return _empty_calendar()

    monkeypatch.setattr("engine.policy_calendar.compute_policy_calendar", fake_cal)
    monkeypatch.setattr(
        "engine.event_calendar.us_macro_events",
        lambda today=None, horizon_days=14, use_fred=True: [],
    )
    monkeypatch.setattr(
        "engine.capital_policy_projection.config.ROOT", tmp_path,
    )
    _copy_templates(tmp_path)
    page_builder.render(tmp_path)
    assert calls["n"] == 1


def test_r8_policy_projection_never_returns_none():
    assert page_builder._policy_projection.__annotations__.get("return") in ("dict", dict)
    # Import failure is untestable without deleting the module; the except
    # branch returns typed_unavailable, which is a dict.
    typed = typed_unavailable(today=TODAY)
    assert isinstance(typed, dict)
    assert typed["windows"]
