"""Acceptance tests for B-F09-6b capital-markets policy projection (MO-PAID-067)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

from engine import capital_policy_projection as engine_projection
from engine.capital_policy_projection import (
    EVENT_WINDOW_MAP,
    HORIZON_DAYS,
    MAX_ROWS,
    NOTE_EN,
    NOTE_ZH,
    ROW_KEYS,
    SCHEMA,
    SECTION_BUDGET_BYTES,
    WINDOWS,
    _EMPTY_REASON,
    _NO_RECORD,
    _NOT_WIRED,
    _READ_FAILED_AUCTIONS,
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
# A real Federal Register document number, the shape collectors/federal_register.py
# stores and engine/policy_calendar.py now passes through.
REAL_FR_DOC = "2026-19427"
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_ATTR_RE = re.compile(r'datetime="[^"]*"')


def _production_opex_event(day: str) -> dict:
    """An OPEX row shaped exactly as engine/event_calendar._event emits it.

    Note the absence of an `event_type` key and the presence of `impact`:
    production rows carry `type`, and OPEX is emitted unconditionally on the
    third Friday of every month, so a 45-day horizon always holds one.
    """
    return {
        "type": "OPEX",
        "date": day,
        "time_et": "",
        "label": "Options expiration",
        "label_zh": "期权到期日",
        "impact": "med",
        "source": "computed",
        "is_context_only": True,
    }


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


def _pin_builder_today(monkeypatch, day=TODAY):
    """Pin the page builder's date.today() so render() cannot drift off TODAY."""
    class FrozenDate(date):
        @classmethod
        def today(cls):
            return day

    monkeypatch.setattr(page_builder, "date", FrozenDate)


def _write_auction_cache(root: Path, asof: date, records: list) -> Path:
    path = (
        root / "data" / "macro" / "auction_cache"
        / f"upcoming_{asof.isoformat()}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


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
    assert "max_rows" not in payload
    assert "max_rows" not in typed_unavailable(today=TODAY)
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
    """T4, with the credit window under DEVIATION 13.

    Spec §2.4, §2.6 and the §6 T4 row freeze `credit_new_issue` as `empty`.
    §2.6 defines `empty` as "sources present, no dated step inside the horizon"
    — and no bond-issuance source exists in v1, so `empty` would tell the
    reader something untrue. The seat ruled in round 6 (R1) that the shipped
    `unavailable` state with a not-wired sentence stands and is recorded as
    numbered DEVIATION 13. This test therefore asserts the deviation, not the
    frozen row; the frozen ORDER and the six-window guarantee are unchanged.
    """
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    ids = [w["window_id"] for w in payload["windows"]]
    assert ids == list(FROZEN_WINDOW_ORDER)
    credit = _window(payload, "credit_new_issue")
    assert credit["state"] == "unavailable"
    assert credit["reason_en"] == _NOT_WIRED["credit_new_issue"][0]
    assert credit["reason_zh"] == _NOT_WIRED["credit_new_issue"][1]
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
    # OPEX is wired to no source at all: that is the not-wired cause, not the
    # no-linked-record cause the number-less Federal Register rows carry.
    assert equity["reason_en"] == _NOT_WIRED["equity_new_issue"][0]
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
    assert f"Showing the next {MAX_ROWS} dated steps; more are scheduled." in html
    assert f"仅显示接下来的 {MAX_ROWS} 个既定日期节点，后续仍有安排。" in html
    # A bare count would not tell the reader that anything was withheld.
    assert "more are scheduled" in payload["truncation_en"]
    assert "后续仍有安排" in payload["truncation_zh"]


def test_12_artifact_budget_and_atomic_write(tmp_path, monkeypatch, capsys):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _copy_templates(tmp_path)
    _pin_builder_today(monkeypatch)
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
    """Worst case against the PRODUCTION window mix, with real record URLs.

    Round-4 R5(b): the previous shape fed `events=[]`, which suppressed the
    OPEX drop production always carries, and used a synthetic 158-byte document
    number no Federal Register record has. This models what a build actually
    sees: the monthly OPEX row present (so `equity_new_issue` renders its own
    sentence), MAX_ROWS comment-close rows carrying a real ~10-character
    document number, at the largest days_out the horizon allows (the longest
    human date form), and the truncation banner. No length cap is imposed on
    the document number; this test measures the headroom instead.
    """
    events = [_production_opex_event((TODAY + timedelta(days=9)).isoformat())]
    calendar = {
        "asof": TODAY.isoformat(),
        "themes": {},
        "upcoming_events": [
            _policy_event(
                day=(TODAY + timedelta(days=33 + i)).isoformat(),
                event_type="comment_close",
                document_number=REAL_FR_DOC,
                title="disclosure comment",
            )
            for i in range(13)
        ],
        "entity_list_events": [],
        "latency_summary": {},
        "note": "fixture",
    }
    _patch_engines(monkeypatch, events=events, calendar=calendar)
    payload = project(today=TODAY)
    assert payload["row_count"] == MAX_ROWS
    assert payload["truncated"] is True
    assert _window(payload, "equity_new_issue")["state"] == "unavailable"
    assert _window(payload, "equity_new_issue")["reason_en"] == _NOT_WIRED["equity_new_issue"][0]
    for row in _all_rows(payload):
        assert row["source_url"] == f"https://www.federalregister.gov/d/{REAL_FR_DOC}"
        assert len(row["source_url"]) == 44
        assert row["window_id"] == "disclosure_regulatory"
        assert row["days_out"] >= 33
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
    """A window whose rows were read but carry no citable record.

    Round-4 R1 separates the two causes: a row dropped because its own record
    is missing (a Federal Register step with no document number) is the
    no-record case; an event type wired to no source at all is `not wired`
    and is covered by test_r4_1.
    """
    _patch_engines(
        monkeypatch,
        events=[],
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
    disc = _window(payload, "disclosure_regulatory")
    assert disc["state"] == "unavailable"
    assert disc["reason_en"] == _NO_RECORD[0]
    assert disc["reason_zh"] == _NO_RECORD[1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _NO_RECORD[0] in html
    assert _NO_RECORD[1] in html
    assert _EMPTY_REASON[0] not in _section_window_copy(html, "Disclosure rules")


def test_r4_1_production_opex_window_is_not_wired(tmp_path, monkeypatch):
    """R1: a source-less event type is NOT WIRED, never `no linked record`.

    `OPEX` is the only event type mapped to `equity_new_issue`, and it has no
    entry in `_FROZEN_SOURCE`, so no OPEX row can ever carry a citation. That
    is a wiring gap, not a gap in the public record, and the sentence the
    reader sees has to say so.
    """
    _patch_engines(
        monkeypatch,
        events=[_production_opex_event("2026-09-18")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    equity = _window(payload, "equity_new_issue")
    assert equity["state"] == "unavailable"
    assert equity["rows"] == []
    assert equity["reason_en"] == _NOT_WIRED["equity_new_issue"][0]
    assert equity["reason_zh"] == _NOT_WIRED["equity_new_issue"][1]
    assert equity["reason_en"] != _NO_RECORD[0]
    html = _render_section(tmp_path, monkeypatch, payload)
    slice_ = _section_window_copy(html, "New share sales")
    assert _NOT_WIRED["equity_new_issue"][0] in slice_
    assert _NOT_WIRED["equity_new_issue"][1] in slice_
    assert _NO_RECORD[0] not in slice_
    assert _EMPTY_REASON[0] not in slice_


def test_r4_2_dates_render_in_the_pages_human_form(tmp_path, monkeypatch):
    """R2: visible dates are relative and human; ISO lives in the attribute."""
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", TODAY.isoformat(), label="FOMC decision"),
            _macro_event("FOMC", "2026-09-10", label="FOMC decision"),
            _macro_event("FOMC", "2026-09-16", label="FOMC decision"),
        ],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    rows = _window(payload, "rates_policy")["rows"]
    assert [r["days_out"] for r in rows] == [0, 1, 7]
    section = _render_section(tmp_path, monkeypatch, payload)

    # The machine date is present, and only inside the datetime attribute.
    assert 'datetime="2026-09-16"' in section
    visible = DATETIME_ATTR_RE.sub("", section)
    assert ISO_DATE_RE.search(visible) is None, ISO_DATE_RE.search(visible).group(0)

    # The page's own relative form, in both languages.
    for token in ("today", "今天", "in 1 day", "1 天后", "in 7 days", "7 天后"):
        assert token in section, token


def _section_window_copy(section: str, label: str) -> str:
    """Exactly one window's rendered block: its label up to the next window."""
    idx = section.index(label)
    nxt = section.find('class="cs-policy-window"', idx)
    return section[idx:] if nxt == -1 else section[idx:nxt]


def test_r1_not_wired_renders(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    credit = _window(payload, "credit_new_issue")
    assert credit["state"] == "unavailable"
    assert credit["reason_en"] == _NOT_WIRED["credit_new_issue"][0]
    assert credit["reason_zh"] == _NOT_WIRED["credit_new_issue"][1]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _NOT_WIRED["credit_new_issue"][0] in html
    assert _NOT_WIRED["credit_new_issue"][1] in html


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
    assert treasury["more_en"] == "1 more dated step is not shown."
    assert treasury["more_zh"] == "另有 1 个既定日期节点未展示。"
    html = _render_section(tmp_path, monkeypatch, payload)
    assert "Fed rate decision" in html
    assert "1 more dated step is not shown." in html
    assert "另有 1 个既定日期节点未展示。" in html
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
                document_number="2026-54321", is_upcoming=True,
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
    assert rows[0]["event_zh"] == "财政部拍卖10年期中期国债"
    blob = json.dumps(payload, ensure_ascii=False)
    for tok in DENYLIST:
        assert tok.lower() not in blob.lower(), tok
    html = _render_section(tmp_path, monkeypatch, payload)
    assert "Treasury auctions 10-Year Note" in html
    assert "财政部拍卖10年期中期国债" in html
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


def test_r4_3_fence_trip_leaves_the_artifact_untouched(tmp_path, monkeypatch):
    """R5(a): the JSON artifact is written only after the byte fence passes."""
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    _copy_templates(tmp_path)

    artifact = tmp_path / "site" / "data" / "capital_policy_projection.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    stale = b'{"schema": "stale-from-the-last-good-build"}\n'
    artifact.write_bytes(stale)

    monkeypatch.setattr("engine.capital_policy_projection.SECTION_BUDGET_BYTES", 10)
    with pytest.raises(RuntimeError, match="policy-projection section over budget"):
        page_builder.render(tmp_path)
    assert not (tmp_path / "site" / "capital_structure.html").exists()
    assert artifact.read_bytes() == stale
    assert not list(artifact.parent.glob(".*.tmp"))


def test_r4_4_cache_staleness_uses_the_cache_date_not_mtime(tmp_path, monkeypatch):
    """R5(f): the same `today` and the same files give the same bytes.

    The cache file is named for the day it covers, so its own date — never the
    wall clock — decides whether it is stale. An old mtime must not flip a
    window from `present` to `unavailable`.
    """
    cache = tmp_path / "data" / "macro" / "auction_cache" / f"upcoming_{TODAY.isoformat()}.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([
        {"securityType": "Note", "securityTerm": "10-Year", "auctionDate": "2026-09-20"},
    ]), encoding="utf-8")
    os.utime(cache, (0, 0))  # written a lifetime ago by the clock

    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    first = project(today=TODAY)
    treasury = _window(first, "treasury_supply")
    assert treasury["state"] == "present"
    assert treasury["rows"][0]["event_en"] == "Treasury auctions 10-Year Note"

    second = project(today=TODAY)
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
        second, sort_keys=True, ensure_ascii=False
    )

    # The cache file is found by the day in its own name, so each day answers
    # from its own file and a day with no file answers `missing`.
    other = tmp_path / "data" / "macro" / "auction_cache" / "upcoming_2026-09-08.json"
    other.write_text("[]", encoding="utf-8")
    assert engine_projection._read_auction_cache(TODAY)[0] == "ok"
    assert engine_projection._read_auction_cache(date(2026, 9, 8))[0] == "ok"
    cache.unlink()
    assert engine_projection._read_auction_cache(TODAY)[0] == "missing"


def test_r4_5_section_kicker_reads_dated_steps(tmp_path, monkeypatch):
    """R5(g): the section never labels itself a policy calendar.

    The frozen chip immediately above can read "Policy calendar not in this
    build"; a second element calling itself POLICY CALENDAR while showing rows
    makes the page look as though it denies and then displays the same thing.
    """
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    section = _render_section(tmp_path, monkeypatch, payload)
    kicker = section[section.index('id="cs-pp-kicker"'):]
    kicker = kicker[:kicker.index("</p>")]
    assert "Dated steps" in kicker
    assert "既定日期节点" in kicker
    assert "Policy calendar" not in section
    assert "政策日历" not in section


def test_r4_6_engine_carries_no_denylisted_token(tmp_path, monkeypatch):
    """R5(h): §2.3 forbids the tokens in the engine, not only the artifact."""
    source = (ROOT / "engine" / "capital_policy_projection.py").read_text(encoding="utf-8")
    doc = engine_projection.__doc__ or ""
    for tok in DENYLIST:
        assert tok.lower() not in doc.lower(), tok
    leaked = sorted({m.group(0).strip() for m in DENYLIST_RE.finditer(source)})
    assert leaked == [], leaked


def test_r4_7_ceiling_note_omits_the_public_record_clause(tmp_path, monkeypatch):
    """The section note is the authority clause only, not the chip's live wording."""
    assert NOTE_EN == "Not a rating, not a trade call."
    assert NOTE_ZH == "不是评级，也不是交易建议。"
    # The heading already carries the "dated steps on the public record"
    # phrase; the note must not repeat it.
    assert "public record" not in NOTE_EN
    assert "公开记录" not in NOTE_ZH
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    assert payload["note_en"] == NOTE_EN
    assert payload["note_zh"] == NOTE_ZH
    section = _render_section(tmp_path, monkeypatch, payload)
    assert NOTE_EN in section
    assert NOTE_ZH in section
    assert section.count("公开记录上的既定日期节点") == 1


def test_r7_missing_cache_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    payload = project(today=TODAY)
    treasury = _window(payload, "treasury_supply")
    assert treasury["state"] == "unavailable"
    # R6(R2): the missing file is the cached Treasury auction schedule. Naming
    # the dated-event calendar here contradicts the window above, which the
    # same build fills from that calendar.
    assert treasury["reason_en"] == _READ_FAILED_AUCTIONS[0]
    assert treasury["reason_zh"] == _READ_FAILED_AUCTIONS[1]
    assert treasury["reason_en"] != _READ_FAILED_EVENTS[0]
    html = _render_section(tmp_path, monkeypatch, payload)
    assert _READ_FAILED_AUCTIONS[0] in html
    assert _READ_FAILED_AUCTIONS[1] in html
    assert _EMPTY_REASON[0] not in _section_window_copy(html, "Government borrowing")
    # The event-calendar sentence never lands on the rates window in the same
    # build: that calendar was read, it simply had nothing pending.
    rates_copy = _section_window_copy(html, "Policy-rate decision")
    assert _READ_FAILED_AUCTIONS[0] not in rates_copy
    assert _READ_FAILED_AUCTIONS[1] not in rates_copy
    assert _window(payload, "rates_policy")["reason_en"] != _READ_FAILED_AUCTIONS[0]


def test_r7_never_calls_requests(tmp_path, monkeypatch):
    """R7 on the LIVE branch: `us_macro_events` is the real one here.

    Round-4 R5(c): the previous shape monkeypatched `us_macro_events`, which
    made `live_macro` False, so `_read_auction_cache` — the only code that can
    reach the network — was never entered and no implementation could have
    called `requests.get`. This run leaves the real event source in place
    (`use_fred=False` is passed by `project()`), redirects `config.ROOT` at an
    empty tree, and arms `requests.get` to raise.
    """
    def boom(*args, **kwargs):
        raise AssertionError("projection path called the network")

    monkeypatch.setattr("requests.get", boom, raising=False)
    monkeypatch.setattr("requests.post", boom, raising=False)
    monkeypatch.setattr("requests.Session.request", boom, raising=False)
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    # The policy half stays stubbed: compute_policy_calendar reads a parquet and
    # appends a ledger under data/, which no test may touch.
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    assert engine_projection.event_calendar.us_macro_events is (
        engine_projection._LIVE_US_MACRO_EVENTS
    )
    payload = project(today=TODAY)
    assert payload["schema"] == SCHEMA
    # The cache is absent under the redirected root, so the live branch was
    # entered and closed honestly rather than fetching.
    treasury = _window(payload, "treasury_supply")
    assert treasury["state"] == "unavailable"
    assert treasury["reason_en"] == _READ_FAILED_AUCTIONS[0]
    assert not (tmp_path / "data").exists()
    # The real event source is restored for the next test.
    assert engine_projection.event_calendar._fetch_upcoming_auctions.__name__ != "_closed"


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
    _pin_builder_today(monkeypatch)
    page_builder.render(tmp_path)
    assert calls["n"] == 1


def test_r8_policy_projection_never_returns_none(monkeypatch):
    """R5(d): the import-failure fallback is reachable, and it is exercised.

    Previously `typed_unavailable` was imported inside the handler for a failed
    import of the same module, so the fallback could never run. It is now
    imported before the guarded import, and deleting `project` from the module
    drives the real branch.
    """
    assert page_builder._policy_projection.__annotations__.get("return") in ("dict", dict)
    monkeypatch.delattr(engine_projection, "project")
    payload = page_builder._policy_projection(today=TODAY)
    assert isinstance(payload, dict)
    assert payload["schema"] == SCHEMA
    assert payload["authority"] == "context_only"
    assert len(payload["windows"]) == 6
    assert all(w["state"] == "unavailable" for w in payload["windows"])
    assert all(w["reason_en"] for w in payload["windows"])


def test_r6_1_not_wired_copy_names_the_missing_calendar(tmp_path, monkeypatch):
    """R6(R4 a): the sentence names the object, never an internal referent.

    Nothing on the page is called a "window", so "this window" / "本窗口"
    pointed at a word the reader never sees. Each window now says which
    calendar is absent, and the two v1-reachable sentences differ from each
    other so a reader can tell the share window from the bond window.
    """
    _patch_engines(
        monkeypatch,
        events=[_production_opex_event("2026-09-18")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    equity = _window(payload, "equity_new_issue")
    credit = _window(payload, "credit_new_issue")
    assert equity["reason_en"] == (
        "The equity-issuance calendar is not yet connected to this section."
    )
    assert equity["reason_zh"] == "本栏目暂未收录股票发行日历。"
    assert credit["reason_en"] == (
        "The bond-issuance calendar is not yet connected to this section."
    )
    assert credit["reason_zh"] == "本栏目暂未收录债券发行日历。"
    assert equity["reason_en"] != credit["reason_en"]
    assert equity["reason_zh"] != credit["reason_zh"]

    section = _render_section(tmp_path, monkeypatch, payload)
    assert equity["reason_en"] in _section_window_copy(section, "New share sales")
    assert credit["reason_zh"] in _section_window_copy(section, "New bond sales")
    # The internal referent and the IT-integration verb are gone from the
    # whole rendered section, not only from these two sentences.
    for token in ("this window", "本窗口", "接入", "wired"):
        assert token not in section, token


def test_r6_2_section_uses_one_chinese_name_for_the_object(tmp_path, monkeypatch):
    """R6(R4 b): 既定日期节点 everywhere — kicker, headline, reasons, overflow."""
    events = [
        _macro_event("FOMC", (TODAY + timedelta(days=i)).isoformat(), label="FOMC decision")
        for i in range(40)
    ]
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    payload = project(today=TODAY)
    assert payload["truncated"] is True
    section = _render_section(tmp_path, monkeypatch, payload)
    kicker = section[section.index('id="cs-pp-kicker"'):]
    kicker = kicker[:kicker.index("</p>")]
    assert "既定日期节点" in kicker
    # Every occurrence of the noun in the section is the same full name.
    assert section.count("节点") == section.count("既定日期节点")
    assert section.count("节点") >= 3, section.count("节点")


def test_r6_3_export_control_copy_follows_is_upcoming(monkeypatch):
    """Export-control copy is typed by is_upcoming, never Entity List."""
    _patch_engines(
        monkeypatch,
        events=[],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [],
            "entity_list_events": [
                _policy_event(
                    day="2026-09-30", event_type="entity_list",
                    document_number="2026-19427", is_upcoming=True,
                ),
                _policy_event(
                    day=TODAY.isoformat(), event_type="entity_list",
                    document_number="2026-19428", is_upcoming=False,
                ),
            ],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    rows = _window(payload, "export_control")["rows"]
    assert [r["event_en"] for r in rows] == [
        "A Federal Register document is published",
        "Comment period closes on a Federal Register document",
    ]
    assert [r["event_zh"] for r in rows] == [
        "一份联邦公报文件发布",
        "一份联邦公报文件的意见征询期截止",
    ]
    blob = json.dumps(payload, ensure_ascii=False)
    assert "Entity List" not in blob
    assert "实体清单" not in blob


def test_r6_4_auction_chinese_distinguishes_note_from_bond(monkeypatch):
    """R6(R4 d): 中期国债 and 长期国债, not one 国债 for both."""
    _patch_engines(
        monkeypatch,
        events=[
            _auction_event("2026-09-20", tenor="10", kind="Note"),
            _auction_event("2026-09-24", tenor="30", kind="Bond"),
        ],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    rows = _window(payload, "treasury_supply")["rows"]
    assert [r["event_en"] for r in rows] == [
        "Treasury auctions 10-Year Note",
        "Treasury auctions 30-Year Bond",
    ]
    assert [r["event_zh"] for r in rows] == [
        "财政部拍卖10年期中期国债",
        "财政部拍卖30年期长期国债",
    ]
    assert rows[0]["event_zh"] != rows[1]["event_zh"]
    # Spec §2.4 freezes the placed auction types; the Chinese table may name a
    # Bill, but a Bill row is never ingested by this section.
    assert engine_projection._AUCTION_TYPE_ZH["Bill"] == "短期国债"
    assert "Bill" not in engine_projection._AUCTION_TYPES


def test_r6_5_a_none_payload_never_overwrites_the_artifact(tmp_path, monkeypatch):
    """R6(R4 f): a build with no payload leaves the last good JSON alone."""
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: None)
    _copy_templates(tmp_path)
    artifact = tmp_path / "site" / "data" / "capital_policy_projection.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    good = b'{"schema": "capital_policy_projection.v1"}\n'
    artifact.write_bytes(good)

    page_builder.render(tmp_path)
    assert artifact.read_bytes() == good
    assert b"null" not in artifact.read_bytes()
    assert not list(artifact.parent.glob(".*.tmp"))
    # The page itself still builds; only the section is withheld.
    html = (tmp_path / "site" / "capital_structure.html").read_text(encoding="utf-8")
    assert 'id="cs-policy-projection"' not in html


def test_r6_6_the_build_memo_refuses_a_second_day(tmp_path, monkeypatch):
    """R6(R4 g): the once-per-build memo cannot answer for a day it never ran.

    `_compute_once` stores one result keyed on nothing, so a caller asking for
    a different day was handed the first call's answer in silence. The chip
    asks with `today=None` and the section leaf asks with a concrete date, and
    both mean the same day — so the guard resolves `None` before comparing and
    only a genuinely different day raises. A guard on `today is not None`
    instead would fire on every real build: `project()` resolves `None` to
    `date.today()` before it calls the calendar, and it swallows exceptions
    into an `unavailable` window, so the two policy windows would silently go
    dark. This test proves both halves: the real build still fills them, and a
    differing day is refused in words.
    """
    calls = {"n": 0}

    def fake_cal(df=None, today=None):
        calls["n"] += 1
        return {
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(
                day=(TODAY + timedelta(days=16)).isoformat(),
                event_type="comment_close",
                document_number=REAL_FR_DOC,
            )],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        }

    monkeypatch.setattr("engine.policy_calendar.compute_policy_calendar", fake_cal)
    monkeypatch.setattr(
        "engine.event_calendar.us_macro_events",
        lambda today=None, horizon_days=14, use_fred=True: [],
    )
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: _stub_watch())
    _copy_templates(tmp_path)
    _pin_builder_today(monkeypatch)

    seen = {}
    real_projection = page_builder._policy_projection

    def capture(today=None):
        import engine.policy_calendar as _pc
        seen["fn"] = _pc.compute_policy_calendar
        seen["today"] = today
        return real_projection(today=today)

    monkeypatch.setattr(page_builder, "_policy_projection", capture)
    page_builder.render(tmp_path)
    assert seen["today"] == TODAY

    # The guard did not fire on the real build: one call, and the window the
    # policy calendar feeds is filled rather than blanked.
    assert calls["n"] == 1
    artifact = json.loads(
        (tmp_path / "site" / "data" / "capital_policy_projection.json").read_text(
            encoding="utf-8"
        )
    )
    disclosure = _window(artifact, "disclosure_regulatory")
    assert disclosure["state"] == "present", disclosure

    wrapper = seen["fn"]
    assert wrapper is not fake_cal
    other_day = TODAY - timedelta(days=400)
    with pytest.raises(RuntimeError, match="one day only"):
        wrapper(today=other_day)
    assert calls["n"] == 1


def test_heal_export_control_copy_is_type_neutral(monkeypatch):
    """REQUIRED 1 / A1: each reachable entity_list shape has a true sentence."""
    _patch_engines(
        monkeypatch,
        events=[],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [],
            "entity_list_events": [_policy_event(
                day="2026-09-30", event_type="entity_list",
                document_number=REAL_FR_DOC, is_upcoming=True,
                title="Addition of Entities to the Entity List",
            )],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    upcoming = project(today=TODAY)
    row = _window(upcoming, "export_control")["rows"][0]
    assert row["event_en"] == "Comment period closes on a Federal Register document"
    assert row["event_zh"] == "一份联邦公报文件的意见征询期截止"
    assert "Entity List" not in json.dumps(upcoming)

    _patch_engines(
        monkeypatch,
        events=[],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [],
            "entity_list_events": [_policy_event(
                day=TODAY.isoformat(), event_type="entity_list",
                document_number="2026-19428", is_upcoming=False,
                title="Entity List investigation notice",
            )],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    published = project(today=TODAY)
    row = _window(published, "export_control")["rows"][0]
    assert row["event_en"] == "A Federal Register document is published"
    assert row["event_zh"] == "一份联邦公报文件发布"
    blob = json.dumps(published, ensure_ascii=False)
    assert "Entity List" not in blob
    assert "实体清单" not in blob


def test_heal_same_date_comment_close_rows_collapse(monkeypatch):
    """REQUIRED 3 / A3: seven same-day comment_close rows collapse; auctions do not."""
    docs = [
        "2026-70007", "2026-70001", "2026-70003", "2026-70002",
        "2026-70006", "2026-70005", "2026-70004",
    ]
    _patch_engines(
        monkeypatch,
        events=[
            _auction_event("2026-09-20", tenor="10", kind="Note"),
            _auction_event("2026-09-20", tenor="30", kind="Bond"),
            _macro_event("FOMC", "2026-09-20", label="FOMC decision"),
        ],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [
                _policy_event(
                    day="2026-09-20", event_type="comment_close",
                    document_number=doc,
                )
                for doc in docs
            ],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    payload = project(today=TODAY)
    disc = _window(payload, "disclosure_regulatory")
    assert len(disc["rows"]) == 1
    row = disc["rows"][0]
    assert row["event_en"] == (
        "Comment periods close on 7 Federal Register documents"
    )
    assert row["event_zh"] == "7 份联邦公报文件的意见征询期截止"
    assert row["source_url"] == "https://www.federalregister.gov/d/2026-70001"
    treasury = _window(payload, "treasury_supply")
    assert len(treasury["rows"]) == 2
    rates = _window(payload, "rates_policy")
    assert len(rates["rows"]) == 1
    assert "max_rows" not in payload


def test_heal_hidden_implies_a_surviving_row(monkeypatch):
    """REQUIRED 7: hidden>0 cannot empty a window; the dead disjunct is gone."""
    events = [
        _macro_event("FOMC", (TODAY + timedelta(days=i)).isoformat(),
                     label="FOMC decision")
        for i in range(20)
    ]
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    payload = project(today=TODAY)
    rates = _window(payload, "rates_policy")
    assert rates["more_en"]
    assert len(rates["rows"]) >= 1
    assert rates["state"] == "present"
    source = (ROOT / "engine" / "capital_policy_projection.py").read_text(
        encoding="utf-8"
    )
    assert "or hidden[window_id]" not in source


def test_heal_auction_cache_survives_event_calendar_failure(tmp_path, monkeypatch):
    """REQUIRED 5 / A5 half 1: the auction window renders from its own cache."""
    def boom(*args, **kwargs):
        raise RuntimeError("dated-event calendar missing")

    monkeypatch.setattr("engine.event_calendar.us_macro_events", boom)
    monkeypatch.setattr(engine_projection, "_LIVE_US_MACRO_EVENTS", boom)
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    _write_auction_cache(tmp_path, TODAY, [{
        "securityType": "Note",
        "auctionDate": "2026-09-20",
        "securityTerm": "10-Year",
    }])
    payload = project(today=TODAY)
    treasury = _window(payload, "treasury_supply")
    assert treasury["state"] == "present"
    assert treasury["rows"][0]["event_en"] == "Treasury auctions 10-Year Note"
    rates = _window(payload, "rates_policy")
    assert rates["state"] == "unavailable"
    assert rates["reason_en"] == _READ_FAILED_EVENTS[0]
    assert treasury["reason_en"] != _READ_FAILED_EVENTS[0]


def test_heal_auction_reason_only_when_auction_cache_fails(tmp_path, monkeypatch):
    """REQUIRED 5 / A5 half 2: _READ_FAILED_AUCTIONS only when the cache fails."""
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: _empty_calendar(),
    )
    payload = project(today=TODAY)
    treasury = _window(payload, "treasury_supply")
    assert treasury["state"] == "unavailable"
    assert treasury["reason_en"] == _READ_FAILED_AUCTIONS[0]
    assert treasury["reason_zh"] == _READ_FAILED_AUCTIONS[1]
    assert treasury["reason_en"] != _READ_FAILED_EVENTS[0]


def test_heal_render_resolves_one_day_for_both_callees(tmp_path, monkeypatch):
    """REQUIRED 6 / A6: a clock that advances between the two calls still agrees."""
    calls = {"n": 0}

    class Advancing(date):
        @classmethod
        def today(cls):
            d = TODAY + timedelta(days=calls["n"])
            calls["n"] += 1
            return d

    monkeypatch.setattr(page_builder, "date", Advancing)
    monkeypatch.setattr(engine_projection, "date", Advancing)
    monkeypatch.setattr(
        "engine.policy_calendar.compute_policy_calendar",
        lambda df=None, today=None: {
            "asof": (today or TODAY).isoformat() if not isinstance(today, date)
            else today.isoformat(),
            "themes": {},
            "upcoming_events": [_policy_event(
                day=(TODAY + timedelta(days=16)).isoformat(),
                event_type="comment_close",
                document_number=REAL_FR_DOC,
            )],
            "entity_list_events": [],
            "latency_summary": {},
            "note": "fixture",
        },
    )
    monkeypatch.setattr(
        "engine.event_calendar.us_macro_events",
        lambda today=None, horizon_days=14, use_fred=True: [],
    )
    monkeypatch.setattr("engine.capital_policy_projection.config.ROOT", tmp_path)
    _copy_templates(tmp_path)
    page_builder.render(tmp_path)
    artifact = json.loads(
        (tmp_path / "site" / "data" / "capital_policy_projection.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["asof"] == TODAY.isoformat()
    assert _window(artifact, "disclosure_regulatory")["state"] == "present"
    assert calls["n"] == 1


def test_heal_empty_reason_is_the_frozen_sentence(monkeypatch):
    """REQUIRED 9: empty EN is the frozen sentence; ZH is unchanged."""
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    rates = _window(payload, "rates_policy")
    assert rates["reason_en"] == "No dated step is pending right now."
    assert rates["reason_zh"] == "目前没有待办的既定日期节点。"


def test_publication_compaction_preserves_inline_separators():
    """Publication compaction removes indentation, not visible inline spacing."""
    raw = (
        '<section id="cs-policy-projection">\n'
        '    <div>\n'
        '      <li><strong>Event</strong> <time>in 2 days</time> '
        '<a href="https://example.com">Source</a></li>\n'
        '    </div>\n'
        '</section>'
    )
    compact = page_builder._compact_policy_projection_section(raw)
    section = page_builder._section_html(compact)
    assert "\n" not in section
    assert "</strong> <time>" in section
    assert "</time> <a " in section
    assert len(section.encode("utf-8")) < len(
        page_builder._section_html(raw).encode("utf-8")
    )


def test_publication_lanes_execute_capital_structure_page_builder():
    """The F09 page builder must execute, not merely appear in trigger paths."""
    daily = (ROOT / "scripts" / "ci" / "daily_engine_regime_dashboard.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts.build_capital_structure_page" in daily
    assert daily.index("scripts.build_capital_structure_page") > daily.index("scripts.build_site")

    import yaml

    render = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "render.yml").read_text(encoding="utf-8")
    )
    run_bodies = "\n".join(
        str(step.get("run") or "")
        for job in (render.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
        if isinstance(step, dict)
    )
    assert "scripts.build_capital_structure_page" in run_bodies
    assert run_bodies.index("scripts.build_capital_structure_page") > run_bodies.index("scripts.build_site")


def test_publication_dag_declares_capital_structure_page_builder():
    """DAG truth must match the two executable publication lanes."""
    import yaml

    dag = yaml.safe_load((ROOT / "config" / "dag.yml").read_text(encoding="utf-8"))

    def serial_modules(workflow: str, job: str) -> list[str]:
        lane = next(
            lane
            for lane in dag["lanes"]
            if lane.get("workflow") == workflow and lane.get("job") == job
        )
        return [
            step["module"]
            for step in lane.get("steps") or []
            if isinstance(step, dict) and isinstance(step.get("module"), str)
        ]

    daily_modules = serial_modules(".github/workflows/daily.yml", "engine")
    render_modules = serial_modules(".github/workflows/render.yml", "render")
    target = "scripts.build_capital_structure_page"
    for modules in (daily_modules, render_modules):
        assert target in modules
        assert modules.index(target) > modules.index("scripts.build_site")
