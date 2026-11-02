from copy import deepcopy
from datetime import datetime, time
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from engine.press import adjusted_baseline as B
from scripts import qualify_press_nvda_baseline as C


@pytest.fixture
def payload():
    rows = []
    for i, day in enumerate(B.sessions_between(B.START, B.CUTOFF)):
        close = 100 + i * .1 + math.sin(i / 3) * 3
        rows.append({"t": int(datetime.combine(day, time(0), ZoneInfo("America/New_York")).timestamp() * 1000),
                     "o": close - .2, "h": close + 1, "l": close - 1,
                     "c": close, "v": 1000000 + i})
    return {"status": "OK", "ticker": "NVDA", "adjusted": True,
            "queryCount": len(rows), "resultsCount": len(rows), "results": rows}


def test_baseline_qualifies_without_admitting_press(payload):
    before = deepcopy(payload)
    result = B.qualify(payload)
    assert payload == before
    assert result["cutoff"] == "2026-10-07"
    assert set(result["analytical_results"]) == set(B.METRICS)
    assert not result["allow_stage"] and not result["allow_emit"]
    assert not result["publication_approved"]
    assert result["checks"]["independent_50_and_200_day_arithmetic"]


@pytest.mark.parametrize("field,value", [
    ("status", "NOT_AUTHORIZED"), ("status", "DELAYED"), ("ticker", "nvda"),
    ("ticker", "AMD"), ("adjusted", False), ("adjusted", "true"),
    ("next_url", "https://invalid.example/?apiKey=never-follow"),
    ("resultsCount", 1), ("queryCount", True), ("results", []),
])
def test_response_refusals(payload, field, value):
    payload[field] = value
    with pytest.raises(B.BaselineRefused):
        B.qualify(payload)


@pytest.mark.parametrize("field,value", [
    ("t", True), ("t", 0), ("c", float("nan")), ("h", float("inf")),
    ("c", "100"), ("o", True), ("l", -1), ("v", -1), ("h", 1), ("otc", True),
])
def test_bar_refusals(payload, field, value):
    payload["results"][100][field] = value
    with pytest.raises(B.BaselineRefused):
        B.qualify(payload)


@pytest.mark.parametrize("change", ["duplicate", "missing", "reverse", "post_cutoff", "intraday"])
def test_calendar_is_exact_not_cleaned(payload, change):
    rows = payload["results"]
    if change == "duplicate": rows[100] = deepcopy(rows[99])
    elif change == "missing": rows.pop(100)
    elif change == "reverse": rows.reverse()
    elif change == "post_cutoff": rows[-1]["t"] += 86400000
    elif change == "intraday": rows[100]["t"] += 3600000
    payload["queryCount"] = payload["resultsCount"] = len(rows)
    with pytest.raises(B.BaselineRefused): B.qualify(payload)


@pytest.fixture
def runner(monkeypatch, payload):
    calls = []
    monkeypatch.setattr(C, "source_binding", lambda: {"revision": "a" * 40, "sha256": {}})
    monkeypatch.setattr(C.massive_close, "_base_url", lambda: "https://api.polygon.io")
    monkeypatch.setattr(C.config, "secret", lambda name: "fixture-credential" if name == "MASSIVE_API_KEY" else None)
    def fetch(path, params):
        calls.append((path, params))
        return payload
    monkeypatch.setattr(C.massive_close, "_default_fetch", lambda key, **kwargs: fetch)
    return calls


def test_one_fetch_and_exclusive_artifact(tmp_path, payload, runner):
    output = tmp_path / "one-attempt"
    assert C.run(output) == 0
    assert runner == [(B.PATH, B.PARAMS)]
    result = json.loads((output / "qualification.json").read_text())
    import hashlib
    assert hashlib.sha256((output / "canonical_parsed_payload.json").read_bytes()).hexdigest() == result["canonical_parsed_payload_sha256"]
    assert json.loads((output / "canonical_parsed_payload.json").read_text()) == payload
    assert "fixture-credential" not in "".join(p.read_text() for p in output.iterdir())
    with pytest.raises(FileExistsError): C.run(output)
    assert len(runner) == 1


def test_failed_fetch_is_not_retried(tmp_path, runner, monkeypatch):
    calls = []
    def fetch(*args):
        calls.append(args)
        return None
    monkeypatch.setattr(C.massive_close, "_default_fetch", lambda key, **kwargs: fetch)
    output = tmp_path / "refused"
    assert C.run(output) == 1
    assert len(calls) == 1
    assert not (output / "qualification.json").exists()
    assert json.loads((output / "failure.json").read_text())["reason"] == "response_not_successful"


def test_credential_echo_is_not_retained(tmp_path, payload, runner):
    payload["unexpected"] = "fixture-credential"
    output = tmp_path / "echo"
    assert C.run(output) == 1
    assert not (output / "canonical_parsed_payload.json").exists()
    assert "fixture-credential" not in "".join(p.read_text() for p in output.iterdir())


def test_unqualified_origin_never_gets_credential(tmp_path, runner, monkeypatch):
    monkeypatch.setattr(C.massive_close, "_base_url", lambda: "https://untrusted.example")
    with pytest.raises(B.BaselineRefused, match="unqualified_api_origin"):
        C.run(tmp_path / "origin")
    assert not runner


def test_workflow_is_manual_main_only_and_artifact_only():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github/workflows/press-source-qualification.yml").read_text()
    workflow = yaml.safe_load(text)
    assert set(workflow.get("on", workflow.get(True))) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["qualify"]["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert "persist-credentials: false" in text
    assert "secrets.R2" not in text and "ANTHROPIC" not in text and "DEEPSEEK" not in text
    assert "git push" not in text and "run_press" not in text


def test_absent_credential_never_fetches(tmp_path, runner, monkeypatch):
    monkeypatch.setattr(C.config, "secret", lambda name: None)
    output = tmp_path / "no-credential"
    assert C.run(output) == 1
    assert not runner
    assert json.loads((output / "failure.json").read_text())["reason"] == "configured_market_data_credential_absent"


def test_symlink_output_parent_never_fetches(tmp_path, runner):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(B.BaselineRefused, match="output_must_be_outside"):
        C.run(alias / "attempt")
    assert not runner


def test_dirty_bound_source_never_fetches(tmp_path, runner, monkeypatch):
    def refused():
        raise B.BaselineRefused("working_source_not_bound")
    monkeypatch.setattr(C, "source_binding", refused)
    with pytest.raises(B.BaselineRefused, match="working_source_not_bound"):
        C.run(tmp_path / "dirty")
    assert not runner


@pytest.mark.parametrize("field,value", [("unexpected", "https://invalid.example"),
                                          ("request_id", "https://invalid.example")])
def test_unqualified_response_metadata_refused(payload, field, value):
    payload[field] = value
    with pytest.raises(B.BaselineRefused): B.qualify(payload)


@pytest.mark.parametrize("field,value", [("unexpected", "credential"), ("vw", "secret"), ("n", 1.5)])
def test_unqualified_row_metadata_refused(payload, field, value):
    payload["results"][100][field] = value
    with pytest.raises(B.BaselineRefused): B.qualify(payload)


@pytest.mark.parametrize("location", ["https://api.polygon.io/other", "https://untrusted.example/redirect"])
def test_redirect_is_terminal_and_disabled(monkeypatch, location):
    import requests
    calls = []
    class Response:
        status_code = 302
        headers = {"Location": location}
        def json(self): raise AssertionError("plausible OK redirect body must not be consumed")
    class Session:
        headers = {}
        def get(self, *args, **kwargs):
            calls.append(kwargs)
            return Response()
    monkeypatch.setattr(requests, "Session", Session)
    assert C.massive_close._default_fetch("fixture-key", allow_redirects=False)(B.PATH, B.PARAMS) is None
    assert len(calls) == 1
    assert calls[0]["allow_redirects"] is False


def test_parent_traversal_into_checkout_refused(tmp_path, runner, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    monkeypatch.setattr(C, "ROOT", checkout)
    with pytest.raises(B.BaselineRefused, match="output_must_be_outside"):
        C.run(sibling / ".." / "checkout" / "attempt")
    assert not runner and not (checkout / "attempt").exists()


def test_other_git_checkout_refused(tmp_path, runner):
    other = tmp_path / "another-checkout"
    other.mkdir()
    (other / ".git").write_text("gitdir: shared-git-store")
    with pytest.raises(B.BaselineRefused, match="output_must_be_outside"):
        C.run(other / "attempt")
    assert not runner and not (other / "attempt").exists()
