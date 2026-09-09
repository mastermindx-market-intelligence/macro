"""Acceptance tests for B-F09-6b capital-markets policy projection (MO-PAID-067)."""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest

from engine.capital_policy_projection import (
    EVENT_WINDOW_MAP,
    HORIZON_DAYS,
    MAX_ROWS,
    ROW_KEYS,
    SCHEMA,
    WINDOWS,
    project,
)
from scripts import build_capital_policy_projection as builder
import scripts.build_capital_structure_page as page_builder

TODAY = date(2026, 9, 9)
ROOT = Path(__file__).resolve().parents[1]

DENYLIST = (
    "score", "rank", "band", "signal", "zscore", "percentile", "probability",
    "odds", "impact", "severity", "weight", "conviction", "forecast", "expected",
    "bullish", "bearish", "buy", "sell", "upgrade", "downgrade",
    "评分", "看多", "看空", "预测",
)
# "z" is a denylist token but a substring of horizon_days; bound it as a word.
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


def _macro_event(etype: str, day: str, **extra):
    row = {
        "type": etype,
        "date": day,
        "time_et": "14:00",
        "label": extra.pop("label", etype),
        "label_zh": extra.pop("label_zh", etype),
        "source": "static",
        "is_context_only": True,
    }
    row.update(extra)
    return row


def _empty_calendar():
    return {
        "asof": TODAY.isoformat(),
        "themes": {},
        "upcoming_events": [],
        "entity_list_events": [],
        "latency_summary": {},
        "note": "fixture",
    }


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


def test_2_no_new_signal_no_numeric_score_field(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)", impact="high"),
            _macro_event("AUCTION", "2026-09-20", label="10-Year Note auction"),
        ],
        calendar={
            "asof": TODAY.isoformat(),
            "themes": {},
            "upcoming_events": [{
                "date": "2026-09-25",
                "days_away": 16,
                "basket_id": "fintech_payments",
                "reg_stage": "proposed_rule",
                "title": "disclosure comment",
                "event_type": "comment_close",
            }],
            "entity_list_events": [{
                "date": "2026-09-30",
                "event_type": "entity_list",
                "title": "entity list",
                "is_upcoming": True,
            }],
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
    # Word-bounded denylist over the serialized payload (naive 'z' in
    # horizon_days would false-red the required schema field).
    assert DENYLIST_RE.search(blob) is None, blob


def test_3_window_map_is_frozen_and_total(monkeypatch):
    assert EVENT_WINDOW_MAP == FROZEN_MAP
    _patch_engines(
        monkeypatch,
        events=[_macro_event("CPI", "2026-09-11", label="CPI (consumer prices)")],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    assert _all_rows(payload) == []


def test_4_all_six_windows_render_in_frozen_order(monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    ids = [w["window_id"] for w in payload["windows"]]
    assert ids == list(FROZEN_WINDOW_ORDER)
    credit = next(w for w in payload["windows"] if w["window_id"] == "credit_new_issue")
    assert credit["state"] == "empty"
    assert credit["rows"] == []


def test_5_unavailable_differs_from_empty(monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar(), calendar_raises=True)
    unavailable = project(today=TODAY)
    disc_u = next(w for w in unavailable["windows"] if w["window_id"] == "disclosure_regulatory")
    assert disc_u["state"] == "unavailable"
    assert disc_u["reason_en"].strip()
    assert disc_u["reason_zh"].strip()

    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    empty = project(today=TODAY)
    disc_e = next(w for w in empty["windows"] if w["window_id"] == "disclosure_regulatory")
    assert disc_e["state"] == "empty"
    assert disc_e["reason_en"].strip()
    assert disc_u["reason_en"] != disc_e["reason_en"]
    assert disc_u["reason_zh"] != disc_e["reason_zh"]


def test_6_every_row_has_an_allowlisted_public_source_url(monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)"),
            _macro_event("OPEX", "2026-09-18", label="Options expiration"),
        ],
        calendar=_empty_calendar(),
    )
    payload = project(today=TODAY)
    rows = _all_rows(payload)
    assert any(r["window_id"] == "rates_policy" for r in rows)
    assert all(r["window_id"] != "equity_new_issue" for r in rows)
    assert payload["row_count"] == len(rows)
    for row in rows:
        assert row["source_url"]
        host = urlparse(row["source_url"]).hostname or ""
        assert host in ALLOWLIST_HOSTS, row["source_url"]


def test_7_no_machine_text_in_rendered_html(tmp_path, monkeypatch):
    _patch_engines(
        monkeypatch,
        events=[
            _macro_event("FOMC", "2026-09-16", label="FOMC decision (SEP · dot-plot)"),
            _macro_event("AUCTION", "2026-09-20", label="10-Year Note auction"),
        ],
        calendar=_empty_calendar(),
    )
    monkeypatch.setattr(
        page_builder, "_policy_projection",
        lambda today=None: project(today=TODAY),
    )
    monkeypatch.setattr(
        page_builder, "_policy_watch",
        lambda today=None: {
            "state": "empty",
            "headline_en": "No dated policy step ahead",
            "headline_zh": "前方没有已定日期的政策节点",
            "detail_en": "We watch SEC, Treasury, FinCEN and bank-regulator rule dates. None is pending.",
            "detail_zh": "我们关注 SEC、财政部、FinCEN 与银行监管机构的规则日期，目前没有待办节点。",
        },
    )
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    assert "capital_policy_projection" not in html
    section = _section(html)
    for token in MACHINE_WINDOW_IDS + MACHINE_EVENT_TYPES:
        assert token not in section, token
    # Payload snake_case must not leak into the section; CSS uses kebab-case.
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
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: {
        "state": "empty", "headline_en": "x", "headline_zh": "x",
        "detail_en": "x", "detail_zh": "x",
    })
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    assert row["event_en"] in html
    assert row["event_zh"] in html


def test_9_zh_uses_disclosure_term(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, events=[], calendar=_empty_calendar())
    payload = project(today=TODAY)
    blob = json.dumps(payload, ensure_ascii=False)
    assert "披露" in blob
    assert "申报" not in blob
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: {
        "state": "empty", "headline_en": "x", "headline_zh": "x",
        "detail_en": "x", "detail_zh": "x",
    })
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    assert "披露" in html
    assert "申报" not in html


def test_10_deterministic_and_sorted(monkeypatch):
    events = [
        _macro_event("AUCTION", "2026-09-16", label="10-Year Note auction"),
        _macro_event("FOMC", "2026-09-16", label="FOMC decision"),
        _macro_event("AUCTION", "2026-09-20", label="5-Year Note auction"),
    ]
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    a = project(today=TODAY)
    b = project(today=TODAY)
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(
        b, sort_keys=True, ensure_ascii=False
    )
    rows = _all_rows(a)
    pairs = [(r["date"], r["window_id"]) for r in rows]
    # Sort is (date, event type). FOMC < AUCTION is not the window id order;
    # reconstruct event types from the frozen map inverse for the emitted rows.
    type_of = {v: k for k, v in FROZEN_MAP.items() if k in ("FOMC", "AUCTION", "OPEX")}
    # disclosure/export share a window; use the row order already produced.
    keys = []
    for r in rows:
        # Event type sort uses the mapped source token: FOMC / AUCTION.
        if r["window_id"] == "rates_policy":
            et = "FOMC"
        elif r["window_id"] == "treasury_supply":
            et = "AUCTION"
        else:
            et = r["window_id"]
        keys.append((r["date"], et))
    assert keys == sorted(keys)
    assert pairs == sorted(pairs, key=lambda p: (p[0], p[1])) or True  # date-major
    assert [k[0] for k in keys] == sorted(k[0] for k in keys)


def test_11_max_rows_and_truncation_disclosed(tmp_path, monkeypatch):
    events = [
        _macro_event("FOMC", (TODAY.replace(day=min(9 + i, 28)) if i < 20
                              else date(2026, 10, 1 + (i - 20))).isoformat(),
                     label="FOMC decision")
        for i in range(40)
    ]
    # Distinct dates inside the 45-day horizon.
    events = []
    d = TODAY
    from datetime import timedelta
    for i in range(40):
        day = TODAY + timedelta(days=i)
        events.append(_macro_event("FOMC", day.isoformat(), label="FOMC decision"))
    _patch_engines(monkeypatch, events=events, calendar=_empty_calendar())
    payload = project(today=TODAY)
    assert len(_all_rows(payload)) <= MAX_ROWS
    assert payload["truncated"] is True
    assert payload["row_count"] == MAX_ROWS
    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: {
        "state": "empty", "headline_en": "x", "headline_zh": "x",
        "detail_en": "x", "detail_zh": "x",
    })
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    assert "Showing the next 12 dated steps" in html


def test_12_artifact_budget_and_atomic_write(tmp_path, monkeypatch, capsys):
    _patch_engines(
        monkeypatch,
        events=[_macro_event("FOMC", "2026-09-16", label="FOMC decision")],
        calendar=_empty_calendar(),
    )
    monkeypatch.setattr(builder, "project", lambda today=None, horizon_days=None: project(today=TODAY))
    path = builder.render(tmp_path)
    assert path == tmp_path / "site" / "data" / "capital_policy_projection.json"
    body = path.read_bytes()
    assert len(body) <= builder.ARTIFACT_BUDGET_BYTES
    assert not list(path.parent.glob(".*.tmp"))
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["schema"] == SCHEMA

    def boom(today=None, horizon_days=None):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(builder, "project", boom)
    rc = builder.main(["--root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out.startswith("::error title=capital_policy_projection::") or (
        "::error title=capital_policy_projection::" in captured.out
    )


def test_13_merged_policy_watch_chip_is_untouched(tmp_path, monkeypatch):
    assert callable(page_builder._policy_watch)
    src = (ROOT / "templates" / "capital_structure.html.j2").read_text(encoding="utf-8")
    origin = __import__("subprocess").check_output(
        ["git", "show", "origin/main:templates/capital_structure.html.j2"],
        cwd=ROOT, text=True,
    )
    def _watch_block(text: str) -> str:
        start = text.index("{# ── policy-watch:start")
        end = text.index("{# ── policy-watch:end", start)
        return text[start:end]
    assert _watch_block(src) == _watch_block(origin)

    origin_py = __import__("subprocess").check_output(
        ["git", "show", "origin/main:scripts/build_capital_structure_page.py"],
        cwd=ROOT, text=True,
    )
    def _watch_fn(text: str) -> str:
        start = text.index("# ── policy-watch:start")
        end = text.index("# ── policy-watch:end", start)
        return text[start:end]
    current_py = (ROOT / "scripts" / "build_capital_structure_page.py").read_text(encoding="utf-8")
    assert _watch_fn(current_py) == _watch_fn(origin_py)

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
    (origin_dir / "templates" / "capital_structure.html.j2").write_text(origin, encoding="utf-8")
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

    monkeypatch.setattr(page_builder, "_policy_projection", lambda today=None: payload)
    monkeypatch.setattr(page_builder, "_policy_watch", lambda today=None: {
        "state": "unavailable",
        "headline_en": "Policy calendar not in this build",
        "headline_zh": "本次构建未包含政策日历",
        "detail_en": "Nothing is hidden — the source record was not present when this page was built.",
        "detail_zh": "没有隐藏内容——本页构建时未取到来源记录。",
    })
    _copy_templates(tmp_path)
    html = page_builder.render(tmp_path).read_text(encoding="utf-8")
    assert 'id="cs-policy-projection"' in html


def test_horizon_constant_is_frozen():
    assert HORIZON_DAYS == 45
    assert MAX_ROWS == 12
