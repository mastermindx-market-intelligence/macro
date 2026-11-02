"""Tests for engine.uk_policy_brain — the UK (HM Treasury / GOV.UK) policy desk.

Mirrors the test shape of tests/test_policy_intent_desk.py: gate-off writes
nothing, network/model failures degrade rather than raise, the model's stance
is clamped to a closed set, and invented numbers/tickers are rejected in code.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine import uk_policy_brain as brain

FIXTURE = Path(__file__).parent / "fixtures" / "uk_policy_govuk_sample.json"

def _load_real_intel() -> dict:
    root = Path(__file__).parent.parent
    p = root / "data" / "policy" / "intel.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"fed": {"task_forces": []}, "administration": {"verified_levers": []},
                "rotation": {}, "predictions": [], "monitor": [], "sources": [], "caveats": []}


_REAL_INTEL = _load_real_intel()


def _clear_env(monkeypatch):
    for k in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", brain.GATE_ENV):
        monkeypatch.delenv(k, raising=False)


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R3 D2 — autouse clear_dead fixture.
# engine.llm_auth._dead_providers is PROCESS-GLOBAL; T1/T2/T3 in this module
# deliberately drive 401 paths to mark rungs dead for the rest of the test
# session. Without this fixture a test that runs after T2 sees rung 2 silently
# skipped and the assertions on rung 2's success/failure no longer hold
# (R3's review found exactly this leak: T2 then T1 short-circuited on the
# already-marked-dead second rung and the FAIL-side observations went red).
# Mirrors the pattern at tests/test_llm_auth.py:14-20 (module-level
# setup_function) plus tests/test_llm_auth.py:20-32 (autouse fixture).
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _clear_llm_auth_dead_providers():
    from engine import llm_auth
    llm_auth.clear_dead()
    yield
    llm_auth.clear_dead()


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R3 D1 — _DEFAULTS pins client_timeout_s=15 and
# client_max_retries=0 so engine.llm_auth._client_tuning_kwargs emits both keys.
# Without this the new make_call path would inherit the SDK defaults (600s +
# 2 retries) and a single stalled rung could eat the entire whitehouse-sentinel
# 10-min budget (.github/workflows/whitehouse-sentinel.yml:28) and kill the
# White House publish — the defect the R2 review caught.
# --------------------------------------------------------------------------- #
def test_client_timeout_and_max_retries_pinned():
    from engine import llm_auth
    cfg = brain._cfg()
    # The defaults are present (not implicit from SDK defaults).
    assert cfg.get("client_timeout_s") == 15, cfg.get("client_timeout_s")
    assert cfg.get("client_max_retries") == 0, cfg.get("client_max_retries")
    # And llm_auth actually consumes them — _client_tuning_kwargs returns
    # `{"max_retries": 0, "timeout": 15}` (httpx.Timeout(15, connect=5.0) in
    # the full dev env, float 15 when httpx is absent — the minimal-deps venv).
    tuning = llm_auth._client_tuning_kwargs(cfg)
    assert tuning.get("max_retries") == 0
    timeout = tuning.get("timeout")
    assert timeout is not None
    if hasattr(timeout, "read"):
        # httpx.Timeout(secs, connect=5.0) — the read timeout is the bound.
        assert float(timeout.read) == 15.0
    else:
        assert float(timeout) == 15.0


def test_gate_off_without_key_returns_none_and_writes_nothing(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    assert brain.enabled() is False
    result = brain.run(root=tmp_path)
    assert result is None
    assert not (tmp_path / "site" / "uk_policy.json").exists()


def test_unreachable_source_degrades_never_raises(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _boom(url, timeout=15):
        raise RuntimeError("network down")

    monkeypatch.setattr(brain, "_fetch", _boom)
    assert brain.collect() == []

    def stub_call(prompt):
        return {"summary_en": "x", "stance": "routine"}

    result = brain.run(root=tmp_path, force=True, call=stub_call)
    # No prior record and no items -> None (degrade, no exception)
    assert result is None


def test_unreachable_source_with_prior_becomes_source_outage(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    site = tmp_path / "site"
    site.mkdir()
    prior = {
        "state": "ok", "stance": "restrictive",
        "headline": "Chancellor confirms new fiscal rules to support growth",
        "source_url": "https://www.gov.uk/government/news/chancellor-confirms-new-fiscal-rules-to-support-growth",
    }
    (site / "uk_policy.json").write_text(json.dumps(prior))
    monkeypatch.setattr(brain, "collect", lambda *a, **k: [])
    result = brain.run(root=tmp_path, force=True, call=lambda p: {"stance": "routine"})
    assert result["state"] == "source_outage"
    assert result["headline"] == prior["headline"]
    assert result["stance"] == "restrictive"
    saved = json.loads((site / "uk_policy.json").read_text())
    assert saved["state"] == "source_outage"


def test_positive_parse():
    raw = FIXTURE.read_bytes()
    items = brain._parse_search_results(raw)
    assert len(items) == 2
    it = items[0]
    assert it["title"] == "Chancellor confirms new fiscal rules to support growth"
    assert it["url"] == (
        "https://www.gov.uk/government/news/chancellor-confirms-new-fiscal-rules-to-support-growth"
    )
    assert it["published"].startswith("2026-09-04T09:30:00")
    assert it["doc_type"] == "News Story"
    assert it["id"] == "uk-2026-09-04-chancellor-confirms-new-fiscal-rules-to-support-growth"
    items2 = brain._parse_search_results(raw)
    assert items2[0]["id"] == it["id"]


def test_stance_is_clamped_to_closed_set():
    assert brain._norm_stance("bullish") == "routine"
    assert brain._norm_stance("restrictive") == "restrictive"
    assert brain._norm_stance(None) == "routine"
    assert brain._norm_stance("SUPPORTIVE") == "supportive"


def test_model_cannot_invent_numbers_or_tickers():
    excerpt = "The Treasury confirmed the plan will proceed as announced."
    bad_number = "This will cost about £4.2bn according to the plan."
    bad_ticker = "Analysts expect HSBA to benefit from this."
    assert brain._sanitize_field(bad_number, excerpt) is None
    assert brain._sanitize_field(bad_ticker, excerpt) is None
    good = "The plan will proceed as announced."
    assert brain._sanitize_field(good, excerpt) == good


def test_source_phrase_inflation_target_is_not_dropped():
    excerpt = "The Bank of England kept the inflation target at 2 percent."
    summary = "The Bank of England kept the inflation target at 2 percent."
    assert brain._sanitize_field(summary, excerpt) == summary


def test_common_policy_acronyms_are_not_invented_tickers():
    excerpt = "The Chancellor restated the fiscal rules."
    summary = "The UK OBR and HMRC figures were not restated."
    assert brain._sanitize_field(summary, excerpt) == summary
    assert brain._sanitize_field("Analysts expect HSBA to benefit.", excerpt) is None


def test_no_scoring_path_imports_this_desk():
    root = Path(__file__).parent.parent
    hits = []
    for base in ("engine", "scripts"):
        for p in (root / base).rglob("*.py"):
            if p.name == "uk_policy_brain.py":
                continue
            try:
                text = p.read_text()
            except Exception:
                continue
            if re.search(r"^\s*(from engine import uk_policy_brain|import engine\.uk_policy_brain)", text, re.M):
                hits.append(str(p.relative_to(root)))
    assert hits == ["scripts/build_whitehouse.py"], hits


def test_panel_renders_every_state(tmp_path):
    jinja2 = pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.build_policy_watch import _uk_desk_view, brief as _brief_fn  # noqa: E402

    root = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    tmpl = env.get_template("policy_watch.html.j2")

    base_ctx = dict(
        intel=_REAL_INTEL, counts={"total": 0, "hit": 0, "miss": 0, "hit_rate": None},
        desk=None, fed_stance=None, fed_hist={}, rot=None, rot_hist={}, dates={},
        catalysts=[], scorecard=None, generated_utc="2026-09-06 00:00 UTC",
        verified_en="", verified_zh="", source_links=[], featured_predictions=[],
        brief=_brief_fn, active_section="research", active_page="policy_watch",
    )
    for state in ("ok", "no_new", "source_outage", "stale", "gate_off", "model_unavailable"):
        raw = None if state == "gate_off" else {
            "state": state,
            "stance": None if state == "model_unavailable" else "restrictive",
            "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
            "body_en": "HM Treasury", "body_zh": "英国财政部",
            "source_label": "GOV.UK", "headline": "Test headline",
            "source_url": "https://www.gov.uk/government/news/test",
            "doc_type_en": "News story", "doc_type_zh": "新闻稿",
            "published_iso": "2026-09-04T09:30:00+00:00",
            "known_at_iso": "2026-09-04T10:00:00+00:00",
            "summary_en": "A plain summary.", "summary_zh": "简单摘要。",
            "watch_en": "Watch the next update.", "watch_zh": "关注下一次更新。",
            "excerpt": "Source excerpt text.", "provider_label": "assistant",
        }
        html = tmpl.render(uk_desk=_uk_desk_view(raw), **base_ctx)
        assert f'data-uk-state="{state}"' in html
        assert 'id="uk"' in html
        assert "United Kingdom" in html and "英国" in html
        if state == "model_unavailable":
            assert "The plain-word read is not ready." in html
            assert "This desk is off right now." not in html
            assert "Routine business" not in html
            assert "例行事务" not in html
            assert "Test headline" in html


def test_panel_register_and_parity(tmp_path):
    pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.build_policy_watch import _uk_desk_view, brief as _brief_fn  # noqa: E402

    root = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    tmpl = env.get_template("policy_watch.html.j2")
    base_ctx = dict(
        intel=_REAL_INTEL, counts={"total": 0, "hit": 0, "miss": 0, "hit_rate": None},
        desk=None, fed_stance=None, fed_hist={}, rot=None, rot_hist={}, dates={},
        catalysts=[], scorecard=None, generated_utc="2026-09-06 00:00 UTC",
        verified_en="", verified_zh="", source_links=[], featured_predictions=[],
        brief=_brief_fn, active_section="research", active_page="policy_watch",
    )
    raw = {
        "state": "ok", "stance": "restrictive",
        "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
        "body_en": "HM Treasury", "body_zh": "英国财政部",
        "source_label": "GOV.UK", "headline": "Test headline",
        "source_url": "https://www.gov.uk/government/news/test",
        "doc_type_en": "News story", "doc_type_zh": "新闻稿",
        "published_iso": "2026-09-04T09:30:00+00:00",
        "known_at_iso": "2026-09-04T10:00:00+00:00",
        "summary_en": "A plain summary.", "summary_zh": "简单摘要。",
        "watch_en": "Watch the next update.", "watch_zh": "关注下一次更新。",
        "excerpt": "Source excerpt text.", "provider_label": "Claude API · test",
    }
    html = tmpl.render(uk_desk=_uk_desk_view(raw), **base_ctx)
    uk_section = html[html.index('id="uk"'):]
    end = uk_section.find('<section class="pw-section"', 1)
    uk_section = uk_section if end == -1 else uk_section[:end]
    for banned in ("falsifier", "refuted", "invalidated", "证伪"):
        assert banned not in uk_section
    for m in re.finditer(r'title="([^"]*)"', uk_section):
        assert not re.search(r"[一-鿿]", m.group(1))
    en_spans = re.findall(r'<span class="l-en">', uk_section)
    zh_spans = re.findall(r'<span class="l-zh">', uk_section)
    assert len(en_spans) == len(zh_spans)


def test_view_builder_never_returns_none():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.build_policy_watch import _uk_desk_view, brief as _brief_fn  # noqa: E402

    v = _uk_desk_view(None)
    assert v["state"] == "gate_off"
    assert v["stance"] is None
    v2 = _uk_desk_view({"state": "garbage", "stance": "garbage"})
    assert v2["state"] == "gate_off"
    assert v2["stance"] is None
    v3 = _uk_desk_view({
        "state": "model_unavailable", "stance": None,
        "headline": "Chancellor confirms new fiscal rules to support growth",
    })
    assert v3["state"] == "model_unavailable"
    assert v3["stance"] is None


def _render_uk(uk_desk):
    jinja2 = pytest.importorskip("jinja2")
    from jinja2 import Environment, FileSystemLoader
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.build_policy_watch import brief as _brief_fn  # noqa: E402
    root = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=True)
    tmpl = env.get_template("policy_watch.html.j2")
    return tmpl.render(
        uk_desk=uk_desk, intel=_REAL_INTEL,
        counts={"total": 0, "hit": 0, "miss": 0, "hit_rate": None},
        desk=None, fed_stance=None, fed_hist={}, rot=None, rot_hist={}, dates={},
        catalysts=[], scorecard=None, generated_utc="2026-09-06 00:00 UTC",
        verified_en="", verified_zh="", source_links=[], featured_predictions=[],
        brief=_brief_fn, active_section="research", active_page="policy_watch",
    )


def test_failed_model_stays_model_unavailable_through_view(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    # Fixture dates are outside the live 4-day window. collect() is replaced
    # wholesale, so treat that return as the already-windowed set this test
    # was written against. Otherwise run() takes the quiet-window branch.
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)

    record = brain.run(root=tmp_path, force=True, call=lambda prompt: {})
    assert record["state"] == "model_unavailable"
    assert record["stance"] is None
    assert record["headline"] == items[0]["title"]

    from scripts.build_policy_watch import _uk_desk_view
    view = _uk_desk_view(record)
    assert view["state"] == "model_unavailable"
    assert view["stance"] is None
    html = _render_uk(view)
    assert 'data-uk-state="model_unavailable"' in html
    assert "The plain-word read is not ready." in html
    assert "平实解读尚未完成。" in html
    assert "This desk is off right now." not in html
    assert "Routine business" not in html
    assert "例行事务" not in html
    assert items[0]["title"] in html


def test_no_new_without_prior_does_not_call_model(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    brain.save_processed(tmp_path, {"seen": {items[0]["id"]: {"at": "2026-09-04T12:00:00+00:00"}}})
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items[:1])
    # Same fixture-date issue as the model-unavailable test: keep this on the
    # already-seen branch rather than the new quiet-window branch.
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    calls = []

    def stub(prompt):
        calls.append(prompt)
        return {"stance": "routine", "summary_en": "should not run"}

    record = brain.run(root=tmp_path, force=True, call=stub)
    assert record["state"] == "no_new"
    assert record["headline"] == items[0]["title"]
    assert record["stance"] is None
    assert calls == []


def test_typed_state_uses_declared_contract():
    assert brain._typed_state("model_unavailable") == "model_unavailable"
    assert brain._typed_state("source_outage") == "source_outage"
    assert brain._typed_state("invented") == "gate_off"
    assert "model_unavailable" in brain._STATES


def test_view_states_match_engine():
    from scripts.build_policy_watch import _UK_VIEW_STATES
    assert _UK_VIEW_STATES == brain._STATES


def test_sentinel_allowlist_publishes_uk_policy_artifact():
    text = (Path(__file__).parent.parent / ".github/workflows/whitehouse-sentinel.yml").read_text()
    assert "site/uk_policy.json" in text
    assert "data/uk_policy" in text
    add_lines = [ln for ln in text.splitlines() if "git add" in ln]
    assert any("site/uk_policy.json" in ln for ln in add_lines)
    assert any("data/uk_policy" in ln for ln in add_lines)


def test_doc_version_and_source_url_nulls_are_printed():
    from scripts.build_policy_watch import _uk_desk_view
    view = _uk_desk_view({
        "state": "ok", "stance": "routine",
        "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
        "body_en": "HM Treasury", "body_zh": "英国财政部",
        "source_label": "GOV.UK",
        "headline": "Chancellor confirms new fiscal rules to support growth",
        "source_url": None, "doc_version": None,
        "doc_type_en": "News story", "doc_type_zh": "新闻稿",
    })
    html = _render_uk(view)
    assert "Not listed on this document." in html
    assert "该文件未列出版本。" in html
    assert "Source link not listed." in html
    assert "未列出原文链接。" in html
    assert 'href=""' not in html
    dated = _uk_desk_view({
        "state": "ok", "stance": "routine",
        "headline": "Chancellor confirms new fiscal rules to support growth",
        "doc_version": "abc-123@2026-09-04T09:30:00+00:00",
        "source_url": "https://www.gov.uk/government/news/test",
        "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "英国",
        "body_en": "HM Treasury", "body_zh": "英国财政部",
        "source_label": "GOV.UK",
    })
    html2 = _render_uk(dated)
    assert "Updated Sep 4, 2026" in html2
    assert "abc-123@" not in html2
    assert "Read the official announcement" in html2
    assert "claude-opus" not in html2
    assert "claude-opus-4-8" not in html2


def test_sentinel_activates_uk_policy_desk_on_credentialed_step():
    """The real hourly publisher must switch on the already-shipped UK desk."""
    text = (
        Path(__file__).parent.parent / ".github" / "workflows" / "whitehouse-sentinel.yml"
    ).read_text(encoding="utf-8")
    marker = "- name: poll White House feed + Opus alert desk"
    assert marker in text
    step = text.split(marker, 1)[1].split("\n      - name:", 1)[0]
    assert 'UK_POLICY_DESK_ENABLED: "1"' in step
    assert "CLAUDE_CODE_OAUTH_TOKEN:" in step
    assert "ANTHROPIC_API_KEY:" in step
    assert "DEEPSEEK_API_KEY:" in step
    assert "python -m scripts.build_whitehouse" in step


def _aged_result(title: str, days_ago: float, slug: str) -> dict:
    published = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )
    return {
        "title": title,
        "link": f"/government/news/{slug}",
        "public_timestamp": published,
        "description": "The Treasury published this note.",
        "content_store_document_type": "news_story",
    }


def _fetch_search(raw: bytes):
    def _fetch(url, timeout=15):
        if url == brain.SEARCH_URL:
            return raw
        return None
    return _fetch


def test_quiet_window_without_prior_persists_no_new_from_newest_item(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    six = _aged_result("Chancellor sets out a six day old note", 6, "six-day-old-note")
    nine = _aged_result("Treasury files a nine day old note", 9, "nine-day-old-note")
    raw = json.dumps({"results": [nine, six]}).encode()
    monkeypatch.setattr(brain, "_fetch", _fetch_search(raw))
    calls = []

    def stub(prompt):
        calls.append(prompt)
        return {"stance": "routine", "summary_en": "should not run"}

    record = brain.run(persist=True, root=tmp_path, call=stub)
    saved_path = tmp_path / "site" / "uk_policy.json"
    assert saved_path.exists()
    saved = json.loads(saved_path.read_text())
    assert record["state"] == "no_new"
    assert saved["state"] == "no_new"
    assert record["headline"] == six["title"]
    assert saved["headline"] == six["title"]
    assert record["stance"] is None
    assert calls == []


def test_quiet_window_with_prior_keeps_prior_headline_as_no_new(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    six = _aged_result("Six day headline that must not replace the prior", 6, "six-day-prior")
    nine = _aged_result("Nine day headline", 9, "nine-day-prior")
    raw = json.dumps({"results": [nine, six]}).encode()
    monkeypatch.setattr(brain, "_fetch", _fetch_search(raw))
    site = tmp_path / "site"
    site.mkdir()
    prior = {
        "state": "ok",
        "stance": "restrictive",
        "headline": "Prior headline stays on a quiet window",
        "source_url": "https://www.gov.uk/government/news/prior",
    }
    (site / "uk_policy.json").write_text(json.dumps(prior))
    calls = []

    def stub(prompt):
        calls.append(prompt)
        return {"stance": "supportive", "summary_en": "should not run"}

    record = brain.run(persist=True, root=tmp_path, call=stub)
    saved = json.loads((site / "uk_policy.json").read_text())
    assert record["state"] == "no_new"
    assert saved["state"] == "no_new"
    assert record["headline"] == prior["headline"]
    assert saved["headline"] == prior["headline"]
    assert record["stance"] == "restrictive"
    assert calls == []


def test_empty_feed_without_prior_logs_warning_and_writes_nothing(tmp_path, monkeypatch, caplog):
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seen = []

    def _fetch(url, timeout=15):
        seen.append(url)
        return None

    monkeypatch.setattr(brain, "_fetch", _fetch)
    with caplog.at_level(logging.WARNING, logger="engine.uk_policy_brain"):
        result = brain.run(persist=True, root=tmp_path)
    assert result is None
    assert not (tmp_path / "site" / "uk_policy.json").exists()
    assert "uk_policy: feed empty" in caplog.text
    assert brain.SEARCH_URL in seen
    assert brain.FALLBACK_ATOM_URL in seen


def test_collect_window_false_returns_all_items_newest_first(monkeypatch):
    older = _aged_result("Older nine day note", 9, "older-nine-day-note")
    middle = _aged_result("Middle six day note", 6, "middle-six-day-note")
    inside = _aged_result("Inside one day note", 1, "inside-one-day-note")
    raw = json.dumps({"results": [older, middle, inside]}).encode()
    monkeypatch.setattr(brain, "_fetch", _fetch_search(raw))
    all_items = brain.collect(4.0, window=False)
    assert [it["title"] for it in all_items] == [
        inside["title"],
        middle["title"],
        older["title"],
    ]
    windowed = brain.collect(4.0, window=True)
    assert [it["title"] for it in windowed] == [inside["title"]]


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R1 T1-T4 — provider waterfall + retry-on-failure + R2 pin.
# These tests run with `call=None` so the real waterfall path
# (engine.llm_auth.build_providers + make_call) executes against fake providers
# monkeypatched into `engine.llm_auth.build_providers`. The fixture idiom mirrors
# tests/test_llm_auth.py:71-105 — provider dicts carry name/env_var/cred/client
# where `client` is a stub whose `.messages.create(**kw)` raises or replies.
# --------------------------------------------------------------------------- #

_WATERFALL_OK_REPLY_JSON = (
    '{"summary_en": "The Chancellor set out updated fiscal rules to support growth.",'
    ' "summary_zh": "财政大臣公布了支持增长的新财政规则。",'
    ' "stance": "supportive",'
    ' "watch_en": "Watch the debt path against the new rule.",'
    ' "watch_zh": "关注债务路径与新规则的关系。"}'
)


class _WaterfallBlock:
    """One text content block in a fake model response."""

    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _WaterfallUsage:
    """Stand-in for the anthropic SDK's Usage object.

    Real Usage has input_tokens, output_tokens, cache_read_input_tokens,
    cache_creation_input_tokens. _capture_usage reads these via getattr with
    a 0 fallback, so we only need to populate what the test cares about."""

    def __init__(self, *, input_tokens: int = 0, output_tokens: int = 0,
                 cache_read_input_tokens: int = 0,
                 cache_creation_input_tokens: int = 0) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = cache_read_input_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens


class _WaterfallResp:
    def __init__(self, text: str, usage: _WaterfallUsage | None = None) -> None:
        self.content = [_WaterfallBlock(text)]
        self.stop_reason = "end_turn"
        # MO-PAID-023_FIX_R3 D5 — make_call reads resp.usage to feed
        # lib.ai_costs. The two-tuple `_do_call` return couldn't carry it; the
        # three-tuple (text, reason, resp) the desk now uses does. Tests that
        # want to assert the ledger row pass a _WaterfallUsage here.
        self.usage = usage


class _WaterfallMessages:
    def __init__(self, *, raise_msg: str | None, reply_text: str | None,
                 usage: _WaterfallUsage | None = None) -> None:
        self.last_kwargs: dict | None = None
        self._raise_msg = raise_msg
        self._reply_text = reply_text
        self._usage = usage

    def create(self, **kw) -> _WaterfallResp:
        self.last_kwargs = kw
        if self._raise_msg is not None:
            raise Exception(self._raise_msg)
        return _WaterfallResp(self._reply_text or "", usage=self._usage)


class _WaterfallClient:
    """Fake llm_auth client. `.messages.create(**kw)` is controllable per-rung."""

    def __init__(self, name: str, *, raise_msg: str | None = None,
                 reply_text: str | None = None,
                 usage: _WaterfallUsage | None = None) -> None:
        self.name = name
        self.messages = _WaterfallMessages(raise_msg=raise_msg, reply_text=reply_text, usage=usage)


def _waterfall_providers(*, raise_first: str | None = None,
                         raise_second: str | None = None,
                         reply_text: str = _WATERFALL_OK_REPLY_JSON,
                         usage: _WaterfallUsage | None = None,
                         ) -> list[dict]:
    """Build the two-rung provider list spec'd in T1/T2/T3 + D5."""
    return [
        {"name": "oauth", "env_var": "CLAUDE_CODE_OAUTH_TOKEN", "cred": "tok-fake",
         "client": _WaterfallClient("oauth", raise_msg=raise_first), "model": "claude-opus-4-8"},
        {"name": "deepseek", "env_var": "DEEPSEEK_API_KEY", "cred": "ds-fake",
         "client": _WaterfallClient("deepseek", raise_msg=raise_second, reply_text=reply_text,
                                    usage=usage),
         "model": "deepseek-v4-pro"},
    ]


def test_waterfall_falls_back_when_first_rung_401s(tmp_path, monkeypatch):
    """T1 — rung 1 raises 401; rung 2 succeeds; record ok/stale; item IS seen."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)
    providers = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        raise_second=None,
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers)

    record = brain.run(root=tmp_path, force=True)

    assert record is not None
    assert record["state"] in {"ok", "stale"}, record["state"]
    assert record["stance"] in {"supportive", "restrictive", "mixed", "routine"}
    saved = brain.load_processed(tmp_path)
    assert items[0]["id"] in saved["seen"], (
        "a successful evaluate must mark the item seen"
    )


def test_all_rungs_fail_is_model_unavailable_and_item_stays_unseen(
        tmp_path, monkeypatch, caplog):
    """T2 — both rungs 401; state=model_unavailable; stance None; NOT seen; WARNING logged."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)
    providers = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        raise_second="401 authentication_error: Invalid bearer token",
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers)

    with caplog.at_level(logging.WARNING, logger=brain.log.name):
        record = brain.run(root=tmp_path, force=True)

    assert record is not None
    assert record["state"] == "model_unavailable"
    assert record["stance"] is None
    saved = brain.load_processed(tmp_path)
    assert items[0]["id"] not in saved["seen"], (
        "a failed evaluate must leave the item UNSEEN so the next cycle retries it"
    )
    assert "uk_policy model call failed" in caplog.text, caplog.text


def test_failed_item_is_retried_next_cycle(tmp_path, monkeypatch):
    """T3 — T2 cycle fails; flip rung 2 to succeed; second run() produces ok/stale + stance.

    MO-PAID-023_FIX_R3 D2 — the autouse `_clear_llm_auth_dead_providers`
    fixture clears engine.llm_auth._dead_providers BETWEEN tests but does
    not reach into a single test's two run() calls. Cycle 1 in this body
    marks both rungs dead (the 401-fallback contract); cycle 2 then sees
    both as dead and short-circuits to no_provider, which would defeat the
    test. The autouse fixture therefore does NOT make the inline
    `clear_dead()` call between cycles redundant — we keep it. The fixture
    still covers the cross-test leak the D2 review caught (T2 then T1).
    """
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)

    # Cycle 1 — both rungs fail.
    providers_fail = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        raise_second="401 authentication_error: Invalid bearer token",
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers_fail)
    first = brain.run(root=tmp_path, force=True)
    assert first["state"] == "model_unavailable"
    assert first["stance"] is None
    assert items[0]["id"] not in brain.load_processed(tmp_path)["seen"]

    # Cycle 1 marked BOTH providers dead in the process-global dead set (the
    # 401-fallback contract). Clear that between cycles so the second run sees
    # rung 1 fail with 401 → rung 2 attempt it. The autouse fixture clears
    # at test boundaries only, not within a single test — this inline call
    # is therefore still load-bearing for the retry contract.
    from engine import llm_auth
    llm_auth.clear_dead()

    # Cycle 2 — same item, rung 2 now succeeds. If the failed cycle had marked
    # the item seen, new_items() would short-circuit to no_new and the model
    # would never run again. A successful second cycle proves the retry.
    providers_ok = _waterfall_providers(raise_first="401 authentication_error: Invalid bearer token",
                                        raise_second=None)
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers_ok)
    second = brain.run(root=tmp_path, force=True)

    assert second is not None
    assert second["state"] in {"ok", "stale"}, second["state"]
    assert second["stance"] is not None
    assert items[0]["id"] in brain.load_processed(tmp_path)["seen"]


def test_no_module_level_llm_auth_or_anthropic_import():
    """T4 (R2 pin, R3 D6). AST-based check that uk_policy_brain.py has no
    module-level Import / ImportFrom that names `llm_auth` or `anthropic`.

    R2: lazy import inside `_call_model` is required because the minimal-deps
    CI job A-F02-W2-4 installs only pytest/pyyaml/jinja2 — no anthropic SDK.
    R3 D6: the original regex `^(from engine import llm_auth|import anthropic|from anthropic)`
    matched only three exact column-0 forms and silently let through e.g.
    `from engine import (llm_auth)` (the comma/parenthesis form is exactly
    the one an unguarded refactor could introduce). An AST check catches the
    whole class — any Import / ImportFrom whose `name` or `module` resolves
    to engine.llm_auth or anthropic at module level.
    """
    import ast
    src = Path(brain.__file__).read_text()
    tree = ast.parse(src)
    bad: list[tuple[str, str]] = []
    for node in tree.body:  # module-level only
        if isinstance(node, ast.Import):
            for alias in node.names:
                n = alias.name
                if n == "anthropic" or n.endswith(".anthropic"):
                    bad.append(("Import", n))
                if n == "llm_auth" or n == "engine.llm_auth" or n.endswith(".llm_auth"):
                    bad.append(("Import", n))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                if alias.name == "anthropic" and (mod == "anthropic" or mod.startswith("anthropic.")):
                    bad.append(("ImportFrom", f"{mod}.{alias.name}"))
                if alias.name == "llm_auth" and ("engine" in mod.split(".") or mod == ""):
                    # covers `from engine import llm_auth`,
                    # `from engine.llm_auth import X`,
                    # `from engine import (llm_auth, ...)`.
                    bad.append(("ImportFrom", f"{mod}.{alias.name}"))
    assert not bad, (
        "uk_policy_brain.py must not import llm_auth or anthropic at module "
        f"level — module-level imports break the minimal-deps CI job "
        f"A-F02-W2-4. Found: {bad}"
    )


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R3 D3 — WARNING logging on silent-failure paths.
# (a) build_providers() returns [] (no SDK / no creds) and (b) a successful
# model reply that lacks the JSON block both used to fall through to
# model_unavailable silently. Tests below assert ONE WARNING record per path,
# with a substring pinned to the operator message.
# --------------------------------------------------------------------------- #
def test_no_providers_logs_warning_with_cause(tmp_path, monkeypatch, caplog):
    """D3 (a) — build_providers() returns [] -> WARNING names SDK + credentials state."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)
    # Force build_providers to return [] — exercises the new branch
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: [])

    with caplog.at_level(logging.WARNING, logger=brain.log.name):
        record = brain.run(root=tmp_path, force=True)

    assert record["state"] == "model_unavailable"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == brain.log.name]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
    msg = warnings[0].getMessage()
    # Substring pins — the R3 fix committed to these:
    assert "build_providers()" in msg
    assert "credentials_present" in msg
    # Plain log.warning, not a `::warning` annotation (GitHub would silently
    # drop a logger-prefixed one — see CLAUDE.md §GitHub annotations).
    assert not msg.startswith("::warning")


def test_no_json_in_reply_logs_warning_with_provider_and_first_80_chars(
        tmp_path, monkeypatch, caplog):
    """D3 (b) — model reply has no JSON block -> WARNING with provider label
    and first 80 chars of the reply so the operator can see the off-contract
    text the desk received."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)
    garbage = "I cannot help with that request — please rephrase the question."
    # Rung 1 raises 401 so rung 2 (deepseek) is the one that "serves" the
    # off-contract reply — the provider label in the WARNING is then
    # unambiguous.
    providers = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        reply_text=garbage,
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers)

    with caplog.at_level(logging.WARNING, logger=brain.log.name):
        record = brain.run(root=tmp_path, force=True)

    assert record["state"] == "model_unavailable"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == brain.log.name]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
    msg = warnings[0].getMessage()
    # The second rung is the one that served (deepseek), so the operator can
    # see WHICH provider went off-contract.
    assert "'deepseek'" in msg
    assert "no JSON block" in msg
    # First 80 chars of the off-contract reply:
    assert garbage[:80] in msg


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R3 D4 — retry cap. A failed item is re-called every hourly
# cycle without bound — under max_age_days=4 the desk would burn ~96 paid
# calls on the same 401 cascade. After MODEL_ATTEMPT_CAP failures we mark
# the item seen with model_unavailable=True, model_attempts=N so new_items()
# filters it out and the served chip stays the truthful "unavailable".
# A SUCCESS resets nothing (the item is seen with its stance; new_items
# will skip it regardless — R5).
# --------------------------------------------------------------------------- #
def test_retry_cap_after_three_failures_marks_seen_with_model_attempts(
        tmp_path, monkeypatch):
    """D4 (a) — provider always returns non-JSON garbage. After 3 failed
    cycles the desk marks the item seen (model_unavailable=True,
    model_attempts=3) so cycle 4 makes NO model call (new_items filters it)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())[:1]
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)

    # Rung 1 raises 401 so rung 2 (the only one that "serves") is the one
    # that emits the garbage reply — the cycle is always paid, the model
    # call always fails, and the failure is always JSON-level (matches the
    # production failure shape: model call succeeds, content is off-contract).
    providers_garbage = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        reply_text="no json here, just text",
    )
    build_calls: list[int] = []

    def _tracking_build_providers(*a, **kw):
        build_calls.append(1)
        return providers_garbage

    monkeypatch.setattr("engine.llm_auth.build_providers", _tracking_build_providers)

    # Cycle 1 — paid call, fails, attempts=1, item still unseen.
    record1 = brain.run(root=tmp_path, force=True)
    assert record1["state"] == "model_unavailable"
    assert record1["model_attempts"] == 1, record1
    assert items[0]["id"] not in brain.load_processed(tmp_path)["seen"]

    # Cycle 2 — paid call, fails, attempts=2, item still unseen.
    record2 = brain.run(root=tmp_path, force=True)
    assert record2["model_attempts"] == 2, record2
    assert items[0]["id"] not in brain.load_processed(tmp_path)["seen"]

    # Cycle 3 — paid call, fails, attempts=3, NOW marked seen (model_unavailable=True).
    record3 = brain.run(root=tmp_path, force=True)
    assert record3["model_attempts"] == 3, record3
    saved = brain.load_processed(tmp_path)
    assert items[0]["id"] in saved["seen"], (
        "after MODEL_ATTEMPT_CAP failures the item must be marked seen "
        "so future cycles don't keep billing it"
    )
    seen_entry = saved["seen"][items[0]["id"]]
    assert seen_entry.get("model_unavailable") is True
    assert seen_entry.get("model_attempts") == 3

    # Exactly 3 paid calls across cycles 1-3.
    assert len(build_calls) == 3, build_calls

    # Cycle 4 — item is now seen -> new_items() returns [] -> the run()
    # branch falls through to the no-model-call `no_new` path. build_providers
    # is not consulted.
    build_calls.clear()
    record4 = brain.run(root=tmp_path, force=True)
    assert build_calls == [], (
        "after the item is marked seen the desk must make NO further model calls"
    )
    assert record4["state"] == "no_new", (
        "seen item with no fresh feed -> state=no_new (no model path)"
    )


def test_retry_cap_success_on_cycle_two_marks_seen_with_stance(
        tmp_path, monkeypatch):
    """D4 (b) — control: provider fails cycle 1 (attempts=1), succeeds cycle 2.
    Item is marked seen WITH the stance (mark_seen called with no model_attempts
    kwarg — success path), model_attempts stays at 1 on the record (NOT reset)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)

    # Cycle 1: rung 1 raises 401, rung 2 returns garbage -> failure, attempts=1
    providers_fail = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        reply_text="no json here",
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers_fail)
    record1 = brain.run(root=tmp_path, force=True)
    assert record1["state"] == "model_unavailable"
    assert record1["model_attempts"] == 1, record1
    assert items[0]["id"] not in brain.load_processed(tmp_path)["seen"]

    # Cycle 2: provider now succeeds (rung 2 returns the canonical JSON).
    # Item is marked seen with the stance, NOT as model_unavailable. Counter
    # is preserved on the record (NOT reset).
    providers_ok = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        reply_text=_WATERFALL_OK_REPLY_JSON,
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers_ok)
    record2 = brain.run(root=tmp_path, force=True)
    assert record2["state"] in {"ok", "stale"}, record2["state"]
    assert record2["stance"] is not None
    assert record2["model_attempts"] == 1, (
        "success does NOT reset the counter — the record keeps the prior "
        "attempt count so a downstream consumer can still see the failed "
        "history; the seen-side mark_seen is called without model_attempts"
    )
    saved = brain.load_processed(tmp_path)
    assert items[0]["id"] in saved["seen"]
    # Success path persists NO model_attempts / model_unavailable — the seen
    # entry is the plain {at: ...} form so new_items() filters the item out
    # regardless of how many failures preceded.
    seen_entry = saved["seen"][items[0]["id"]]
    assert "model_unavailable" not in seen_entry, seen_entry


# --------------------------------------------------------------------------- #
# MO-PAID-023_FIX_R3 D5 — usage telemetry. _do_call returns the 3-tuple
# (text, reason, resp) the way engine/whitehouse_brain._do_call does, so
# make_call captures resp.usage into lib.ai_costs via _capture_usage. A
# fake response carrying .usage writes ONE row to a ledger redirected to a
# temp path — see lib/ai_costs.py:174-186 for how the path is normally
# resolved (env AI_COSTS_SHARD + _ledger_path) and tests/test_llm_auth.py:20-32
# for the canonical monkeypatch pattern.
# --------------------------------------------------------------------------- #
def test_usage_capture_writes_one_row_to_ledger(tmp_path, monkeypatch):
    """D5 — _do_call returns 3-tuple; make_call passes resp.usage through
    _capture_usage, which writes one row to the AI cost ledger. The ledger
    is monkeypatched to write into tmp_path so the test never touches the
    real data tree (which the sparse-worktree MM_DATA_GUARD forbids)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv(brain.GATE_ENV, "1")
    items = brain._parse_search_results(FIXTURE.read_bytes())
    monkeypatch.setattr(brain, "collect", lambda *a, **k: items)
    monkeypatch.setattr(brain, "_in_window", lambda item, cutoff: True)
    monkeypatch.setattr(brain, "fetch_body", lambda url: items[0]["body_text"])
    monkeypatch.setattr(brain, "fetch_version", lambda url: None)

    # Provider with a fake response carrying .usage (the 3-tuple shape the
    # desk now returns from _do_call). Rung 1 raises 401 so rung 2 — the
    # one carrying the .usage attribute — is the one that "serves".
    usage = _WaterfallUsage(input_tokens=11, output_tokens=22)
    providers = _waterfall_providers(
        raise_first="401 authentication_error: Invalid bearer token",
        reply_text=_WATERFALL_OK_REPLY_JSON,
        usage=usage,
    )
    monkeypatch.setattr("engine.llm_auth.build_providers", lambda *a, **kw: providers)

    # Redirect the ledger write to a tmp path. _capture_usage imports
    # lib.ai_costs lazily and calls `_ac.record_usage(**kw)`; the real
    # implementation writes to data/ai_costs/usage.jsonl. We replace it
    # with one that appends JSONL rows to tmp_path/usage.jsonl.
    ledger_path = tmp_path / "usage.jsonl"
    import lib.ai_costs as _ac

    def _captured_record_usage(**kw):
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "lane": kw.get("lane"),
                "provider": kw.get("provider"),
                "model": kw.get("model"),
                "input_tokens": kw.get("input_tokens", 0),
                "output_tokens": kw.get("output_tokens", 0),
                "cache_read_tokens": kw.get("cache_read_tokens", 0),
                "cache_creation_tokens": kw.get("cache_creation_tokens", 0),
                "stage": kw.get("stage"),
                "cost_basis": kw.get("cost_basis"),
            }, separators=(",", ":")) + "\n")
        return True

    monkeypatch.setattr(_ac, "record_usage", _captured_record_usage)

    record = brain.run(root=tmp_path, force=True)
    assert record["state"] in {"ok", "stale"}, record

    assert ledger_path.exists(), "record_usage must have been called"
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 1, [r for r in rows]
    row = rows[0]
    assert row["input_tokens"] == 11, row
    assert row["output_tokens"] == 22, row
    # The desk names itself via the make_call context= field so the AI Cost
    # page can attribute the spend to this lane.
    assert row["stage"] == "uk_policy_brain", row
