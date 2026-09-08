"""Tests for engine.uk_policy_brain — the UK (HM Treasury / GOV.UK) policy desk.

Mirrors the test shape of tests/test_policy_intent_desk.py: gate-off writes
nothing, network/model failures degrade rather than raise, the model's stance
is clamped to a closed set, and invented numbers/tickers are rejected in code.
"""
from __future__ import annotations

import json
import re
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
