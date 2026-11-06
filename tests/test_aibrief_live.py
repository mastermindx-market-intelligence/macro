"""Failure-path qualification for the AI Brief live publication and private read.

No network/model/credential effects. The actual template, FastAPI router, atomic
writer and refresh coordinator run against isolated temporary roots.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from app.aibrief import create_router
from engine.aibrief_runtime import Outcome
from lib.aibrief_live import (SCHEMA, content_id, evidence_usable, read_json,
                             health, health_verdict, qualify_inputs, read_publication, validate_brief, view)
from scripts.refresh_aibrief_live import refresh_lens
from scripts.vps_live_orchestrator import atomic_write_json, _lock_lane

NOW = datetime(2026, 11, 6, 20, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def brief(**changes):
    return dict(schema="master_brief.v2", lens="macro", state_asof="2026-11-06",
                generated_at=NOW.isoformat(), summary="Markets remain unsettled.",
                tldr=["Main driver: Existing readings are mixed.", "What to do: Watch"],
                confidence="medium", refresh_days=1, degraded_reason=None,
                **changes) if not changes else {**brief(), **changes}


def publication(**changes):
    return {"schema": SCHEMA, "lens": "macro", "sequence": 1,
            "last_good": brief(), "attempt": {"state": "succeeded"}, **changes}


def render(data, live=None):
    # Deliberately use the legacy autoescape=False environment as well as the
    # API's escaping environment: the shared macro must protect both.
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    return str(env.get_template("_aibrief_body.html.j2").module.aibrief_body(data, "macro", live=live))


def test_october_read_is_stale_even_when_published_today():
    old = brief(state_asof="2026-10-16", generated_at="2026-10-18T06:50:33+00:00")
    result = view(publication(last_good=old, published_at=NOW.isoformat()), None, lens="macro", now=NOW)
    assert result["status"] == "stale" and not result["current"]
    html = render(old, result)
    assert "Updated daily" not in html and "Scheduled daily" in html
    assert "AI update overdue" in html and '<details class="aib2-retained">' in html
    assert "2026-10-16" in html and "2026-10-18" in html


def test_new_ai_timestamp_does_not_freshen_old_evidence():
    assert view(publication(last_good=brief(state_asof="2026-10-16")), None,
                lens="macro", now=NOW)["status"] == "stale"


def test_expiry_advances_without_a_writer_or_frontend_build():
    assert view(publication(), None, lens="macro", now=NOW)["current"]
    later = view(publication(), None, lens="macro", now=NOW + timedelta(days=2))
    assert not later["current"] and later["status"] == "stale"


def test_future_clock_is_never_current():
    for row in (brief(generated_at=(NOW + timedelta(days=1)).isoformat()), brief(state_asof="2026-11-07")):
        assert not view(publication(last_good=row), None, lens="macro", now=NOW)["current"]


def test_cadence_is_not_an_evidence_freshness_exemption():
    row = brief(lens="btc", state_asof="2026-11-03", refresh_days=3)
    assert not view({**publication(last_good=row), "lens": "btc"}, None, lens="btc", now=NOW)["current"]
    # Explicit elapsed-age behavior across a weekend; no guessed holiday rule.
    assert evidence_usable("2026-11-06", lens="macro", now=NOW + timedelta(days=2))
    assert not evidence_usable("2026-11-06", lens="macro", now=NOW + timedelta(days=4))


def test_newer_inputs_archive_previous_interpretation():
    p = publication(last_good=brief(state_asof="2026-11-05"), facts={"state_asof": "2026-11-06"})
    assert view(p, None, lens="macro", now=NOW)["status"] == "stale"


def test_facts_only_never_creates_an_ai_stance_or_confidence():
    fact = {"label_en": "Regime", "value_en": "Reflation"}
    p = publication(last_good=None, facts={"state_asof": "2026-11-06", "key_facts": [fact]},
                    attempt={"state": "unavailable"})
    result = view(p, None, lens="macro", now=NOW)
    assert result["status"] == "facts_only" and result["brief"] is None
    html = render(None, result)
    assert "no new AI interpretation" in html
    assert 'class="aib2-stance ' not in html and 'class="aib2-conf"' not in html


@pytest.mark.parametrize("patch", [
    {"summary": {"bad": "shape"}}, {"tldr": [1]}, {"tldr": "bad"},
    {"zh": {"tldr": [None]}}, {"degraded_reason": "timeout"},
    {"generated_at": "2026-11-06T20:00:00"}, {"state_asof": "tomorrow"},
    {"confidence": "certain"}, {"lens": "china"},
    {"forward_watch": ["bad shape"]}, {"forward_watch": [{"date": "yesterday", "label": "Event"}]},
])
def test_invalid_model_result_cannot_replace_last_good(patch):
    assert not validate_brief(brief(**patch), lens="macro")


def test_all_rendering_paths_escape_model_text():
    injected = '<img src=x onerror="alert(1)">'
    row = brief(summary=injected, tldr=["Main: " + injected, "What to do: " + injected],
                zh={"tldr": ["重点：" + injected, "行动：" + injected]})
    html = render(row)
    assert "<img" not in html and "&lt;img" in html
    assert "not a signal source" in html


def fake_brain(source_date="2026-11-06", enabled=True):
    return SimpleNamespace(
        _cfg=lambda: {"enabled": enabled, "lenses": ["macro"], "refresh_owner": "vps_live"},
        _interval_for=lambda lens, cfg: 1,
        LENSES={"macro": {"state_fn": lambda root: {"macro": {"date": source_date, "quad_name": "Reflation"}}}},
        _key_facts_for=lambda lens, state: [{"label_en": "Regime", "value_en": "Reflation"}],
    )


def seed(tmp_path, old=None):
    path = tmp_path / "data/regime/master_brief.json"
    atomic_write_json(path, old or brief(state_asof="2026-10-16", generated_at="2026-10-18T00:00:00+00:00"))
    return tmp_path / "state"


def invoke(root, state_dir, **kw):
    return refresh_lens(root, state_dir, lens="macro", now=kw.pop("now", NOW),
                        brain=kw.pop("brain", fake_brain()),
                        prepare=kw.pop("prepare", lambda *a: SimpleNamespace(identity="route-1")), **kw)


def test_success_is_atomically_live_without_touching_static_or_ledger(tmp_path):
    state_dir = seed(tmp_path)
    def generate(*args, **kw):
        in_flight = read_json(state_dir / "aibrief-macro.json")
        assert in_flight["attempt"]["state"] == "running"
        assert in_flight["attempt"]["operation_id"] == kw["operation_id"]
        return Outcome("succeeded", "ok", brief(), True)
    assert invoke(tmp_path, state_dir, generate=generate) == "succeeded"
    p, old = read_publication(tmp_path, state_dir, "macro")
    assert p["last_good"]["state_asof"] == "2026-11-06"
    assert old["state_asof"] == "2026-10-16"
    assert "hold" not in p and p["sequence"] == 2
    assert not (tmp_path / "site").exists()
    assert not list(tmp_path.rglob("*.jsonl"))


def test_route_absent_keeps_old_read_and_publishes_facts(tmp_path):
    state_dir = seed(tmp_path)
    def missing(*_):
        raise RuntimeError("sensitive-provider-path")
    def forbidden(*args, **kw):
        pytest.fail("inference must not run")
    assert invoke(tmp_path, state_dir, prepare=missing, generate=forbidden) == "unavailable"
    p, _ = read_publication(tmp_path, state_dir, "macro")
    assert p["last_good"]["state_asof"] == "2026-10-16" and p["facts"]["state_asof"] == "2026-11-06"
    assert "sensitive-provider-path" not in json.dumps(p)


def test_old_inputs_never_trigger_paid_ai(tmp_path):
    state_dir = seed(tmp_path)
    assert invoke(tmp_path, state_dir, brain=fake_brain("2026-10-16"),
                  prepare=lambda *_: pytest.fail("no route needed")) == "source_stale"


@pytest.mark.parametrize("outcome", [Outcome("unavailable", "invalid_output"),
                                     Outcome("refused", "fabric_unavailable"),
                                     Outcome("effect_unknown", "fabric_effect_unknown")])
def test_failed_attempt_never_rewrites_good_clock(tmp_path, outcome):
    state_dir = seed(tmp_path)
    invoke(tmp_path, state_dir, generate=lambda *a, **kw: outcome)
    p, old = read_publication(tmp_path, state_dir, "macro")
    assert p["last_good"] == old
    assert p["attempt"]["state"] == outcome.state


def test_killed_worker_is_never_blindly_replayed(tmp_path):
    state_dir = seed(tmp_path)
    def crash(*a, **kw):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        invoke(tmp_path, state_dir, generate=crash)
    original = read_json(state_dir / "aibrief-macro.json")["attempt"]["operation_id"]
    assert invoke(tmp_path, state_dir, now=NOW + timedelta(hours=2),
                  generate=lambda *a, **kw: pytest.fail("must not replay")) == "effect_unknown"
    assert read_json(state_dir / "aibrief-macro.json")["attempt"]["operation_id"] == original


def test_refusal_survives_missing_route_and_stale_source(tmp_path):
    state_dir = seed(tmp_path)
    invoke(tmp_path, state_dir, generate=lambda *a, **kw: Outcome("refused", "fabric_unavailable"))
    invoke(tmp_path, state_dir, brain=fake_brain("2026-10-16"))
    assert invoke(tmp_path, state_dir, now=NOW + timedelta(hours=2),
                  generate=lambda *a, **kw: pytest.fail("refused owner cannot replay")) == "refused"


def test_changed_source_does_not_clear_unknown_operation(tmp_path):
    state_dir = seed(tmp_path)
    invoke(tmp_path, state_dir, generate=lambda *a, **kw: Outcome("effect_unknown", "timeout"))
    assert invoke(tmp_path, state_dir, brain=fake_brain("2026-11-07"), now=NOW + timedelta(days=1),
                  generate=lambda *a, **kw: pytest.fail("must reconcile original")) == "effect_unknown"


def test_failed_final_publication_preserves_durable_inflight_guard(tmp_path):
    state_dir = seed(tmp_path)
    count = 0
    def disk_full(path, payload):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("disk full")
        atomic_write_json(path, payload)
    with pytest.raises(OSError):
        invoke(tmp_path, state_dir, write=disk_full,
               generate=lambda *a, **kw: Outcome("succeeded", "ok", brief(), True))
    assert read_json(state_dir / "aibrief-macro.json")["attempt"]["state"] == "running"
    assert invoke(tmp_path, state_dir, generate=lambda *a, **kw: pytest.fail("duplicate")) == "effect_unknown"


def test_corrupt_publication_cannot_reset_unknown_dispatch(tmp_path):
    state_dir = seed(tmp_path)
    state_dir.mkdir()
    (state_dir / "aibrief-macro.json").write_text('{"schema":')
    assert invoke(tmp_path, state_dir, generate=lambda *a, **kw: pytest.fail("duplicate")) == "publication_unreadable"


def test_overlapping_timer_tick_coalesces_in_existing_owner(tmp_path):
    first = _lock_lane(tmp_path, "aibrief")
    try:
        assert first is not None and _lock_lane(tmp_path, "aibrief") is None
    finally:
        first.close()


def client(tmp_path, allowed=True):
    def auth():
        if not allowed:
            raise HTTPException(401, "unauthorized")
        return {"id": "test-user"}
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    app = FastAPI()
    app.include_router(create_router(auth, root=tmp_path, state_dir=tmp_path / "state"))
    return TestClient(app)


def test_read_api_updates_without_rebuild_and_is_private(tmp_path):
    state_dir = seed(tmp_path)
    c = client(tmp_path)
    old = c.get("/api/aibrief/v1/macro")
    assert old.status_code == 200 and "2026-10-16" in old.json()["html"]
    atomic_write_json(state_dir / "aibrief-macro.json", publication())
    new = c.get("/api/aibrief/v1/macro")
    assert new.status_code == 200 and "2026-11-06" in new.json()["html"]
    assert new.json()["revision"] != old.json()["revision"]
    assert "no-store" in new.headers["cache-control"] and "Cookie" in new.headers["vary"]
    assert "operation_id" not in new.text and "<script" not in new.json()["html"]


def test_read_api_auth_precedes_private_read(tmp_path, monkeypatch):
    c = client(tmp_path, allowed=False)
    monkeypatch.setattr("app.aibrief.read_publication", lambda *a: pytest.fail("unauthorized read"))
    assert c.get("/api/aibrief/v1/macro").status_code == 401


@pytest.mark.parametrize("url", ["/api/aibrief/v1/unknown", "/api/aibrief/v1/macro?root=/etc", "/api/aibrief/v1/macro?force=1"])
def test_request_cannot_choose_paths_or_trigger_ai(tmp_path, url):
    assert client(tmp_path).get(url).status_code == 400


def test_secondary_inputs_cannot_borrow_the_primary_date():
    selected, manifest = qualify_inputs({
        "macro": {"date": "2026-11-06", "quad": "Reflation"},
        "china": {"date": "2026-10-16", "quad": "Goldilocks"},
        "undated": {"claim": "unsupported"},
        "bonds": {"date": "2026-11-06", "credit": "stable"},
    }, lens="macro", now=NOW)
    assert "china" not in selected and "undated" not in selected and "bonds" in selected
    assert len([row for row in manifest if row["status"] != "included"]) == 2


def test_same_date_correction_supersedes_interpretation():
    row = brief(input_digest="before")
    p = publication(last_good=row, facts={"state_asof": "2026-11-06", "input_digest": "after"})
    assert view(p, None, lens="macro", now=NOW)["status"] == "stale"


def test_refusal_is_not_released_by_a_different_route(tmp_path):
    state_dir = seed(tmp_path)
    invoke(tmp_path, state_dir, generate=lambda *a, **kw: Outcome("refused", "denied"))
    assert invoke(tmp_path, state_dir, now=NOW + timedelta(hours=2),
                  prepare=lambda *a: SimpleNamespace(identity="different-route"),
                  generate=lambda *a, **kw: pytest.fail("must not bypass refusal")) == "refused"


def test_existing_sentinel_uses_content_expiry_not_healthy_file_mtime(tmp_path):
    state_dir = seed(tmp_path)
    data = {"checks": {"ai_brief": health(tmp_path, state_dir, now=NOW)}}
    assert health_verdict(json.dumps(data), now=NOW)[0] == "stale"
    data["checks"]["ai_brief"]["ok"] = True
    assert health_verdict(json.dumps(data), now=NOW)[0] == "stale"
    assert health_verdict(json.dumps(data), now=NOW + timedelta(minutes=6))[0] == "indeterminate"


def test_sentinel_hook_fetches_real_api_body_and_propagates_breach():
    from scripts.freshness_sentinel import SURFACES, FetchResult, check_surface
    surface = next(row for row in SURFACES if row["id"] == "ai_brief")
    data = {"checks": {"ai_brief": {"schema": "aibrief.health.v1", "checked_at": NOW.isoformat(),
            "ok": True, "lenses": {lens: {"status": "available", "current": True,
            "valid_until": (NOW - timedelta(seconds=1)).isoformat()} for lens in ("macro", "china", "btc")}}}}
    fr = FetchResult(status=200, last_modified=NOW, body=json.dumps(data), error=None)
    assert check_surface(surface, fr, NOW)["status"] == "stale"


def test_deploy_refresh_preserves_shell_and_footer_without_private_content(tmp_path):
    from scripts.aibrief_shells import publish_shells
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    (tmp_path / "site").mkdir()
    (tmp_path / "site/master_brief.json").write_text(json.dumps(brief(state_asof="2026-10-16")))
    served = tmp_path / "served"
    served.mkdir()
    shell = ('<!doctype html><html><head><title>Keep me</title></head><body><h1>Unchanged dashboard</h1>'
             '<div class="aib2" data-lens="macro"><div class="aib2-hdr">Old content</div>'
             '<div class="isle-aibrief-footer"><a href="aibrief.html">Full brief</a></div></div>'
             '<p>Keep the rest</p></body></html>')
    (served / "macro.html").write_text(shell)
    assert publish_shells(tmp_path, served) == 1
    output = (served / "macro.html").read_text()
    assert '<h1>Unchanged dashboard</h1>' in output and '<p>Keep the rest</p>' in output
    assert 'href="aibrief.html"' in output and 'Previous AI read' in output and "2026-10-16" in output
    assert "Updated daily" not in output and output.count('src="/aibrief.js?') == 1
    assert "{#" not in output
    assert publish_shells(tmp_path, served) == 0
    again = (served / "macro.html").read_text()
    assert again == output  # exact repeat is byte-stable; no nested footer/styles


def test_nightly_force_cannot_start_second_live_writer():
    import ast
    tree = ast.parse((ROOT / "engine/master_brain.py").read_text())
    for name in ("run", "run_all"):
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        namespace = {"Path": Path, "_cfg": lambda: {"refresh_owner": "vps_live", "enabled": True},
                     "log": SimpleNamespace(info=lambda *a: None)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "master_brain.py", "exec"), namespace)
        result = namespace[name](force=True)
        assert result in (None, {})
