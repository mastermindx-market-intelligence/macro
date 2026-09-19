"""Source and native presentation contracts for the existing Prophet evidence drawer."""
from pathlib import Path
import json
import re
from jinja2 import Environment, FileSystemLoader
from engine.prophet_lab.earnings_view import build_earnings_view, render_earnings_fragment, STYLE
from tests.test_prophet_lab import _build_d5
from tests.test_prophet_lab_earnings_view import corrected_payload
ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "templates"

def test_native_presentation_is_one_numeric_and_interpretation_source():
    v = build_earnings_view(_build_d5())
    assert v["metrics"][0]["display_value"] == "$109,417,000,000"
    assert v["metrics"][1]["display_value"] == "9 – 11%"
    assert v["presentation"]["title"] == "Earnings evidence"
    assert v["presentation"]["separate"][0]["label"] == "Forward expectations"
    assert "Not connected" in v["presentation"]["separate"][0]["note"]
    assert v["expectation_revision"]["state"] == "NOT_CONNECTED"
    assert not any(v["authority"].values())

def test_native_correction_wording_is_shared_by_html_and_browser_json():
    p=corrected_payload()
    for lang in ("en", "zh"):
        v=build_earnings_view(p,language=lang)
        assert v["presentation"]["correction_note"] in render_earnings_fragment(p,language=lang)
        assert v["metrics"][0]["display_value"] == "$109,417,000,000"
        assert "108,000,000,000" not in json.dumps(v["metrics"])

def test_shell_is_data_free_and_reuses_native_controls():
    env=Environment(loader=FileSystemLoader(T),autoescape=True)
    html=env.get_template("_prophet_earnings_browser.html.j2").render()
    assert "data-prophet-earnings-browser" in html
    assert "<details" in html and "<noscript" in html
    assert "<form" in html and 'maxlength="80"' in html
    assert "<script" in html
    assert "pe:SEC:" not in html
    # JavaScript contains header-construction code, not a session value.
    # The data-free HTML assertion applies to the rendered markup.
    markup = re.sub(r"<script>.*?</script>", "", html, flags=re.S)
    assert "Bearer " not in markup
    assert "private-test-session-token" not in html
    assert "data-pe-status" in html and 'aria-live="polite"' in html

def test_existing_us_board_mounts_exactly_one_data_free_shell():
    s=(T/"dashboard.html.j2").read_text()
    marker="{% include '_prophet_earnings_browser.html.j2' %}"
    assert s.count(marker)==1
    assert s.index('id="us-standouts"') < s.index(marker)
    assert s.index(marker) < s.index("W-L1 SLOT B")

def test_browser_never_injects_html_or_persists_private_evidence():
    p=T/"_prophet_earnings_browser.js.j2"
    assert p.is_file(), "missing real browser consumer"
    s=p.read_text()
    for bad in ("innerHTML", "outerHTML", "DOMParser", "localStorage", "sessionStorage", "console.", "document.cookie", "setInterval"):
        assert bad not in s
    assert "MDXAuth" in s and "getSession" in s and "mdx-auth" in s
    assert "AbortController" in s and "expected_generation" in s
    assert "redirect: 'error'" in s and "cache: 'no-store'" in s
    assert "credentials: 'same-origin'" in s

def test_browser_style_uses_existing_tokens_and_exact_native_evidence_style():
    p=T/"_prophet_earnings_browser.css.j2"
    assert p.is_file(), "missing governed presentation source"
    s=p.read_text()
    assert STYLE.strip() in s
    assert ":root" not in s
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b",s)
    assert 'html[data-theme="light"]' in s

import subprocess
import shutil
from copy import deepcopy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.prophet_lab as api
from engine.prophet_lab.episode_directory import build_episode_directory
from tests.test_prophet_lab_api import (
    _d5_snapshot,
    _d5_master as _api_master,
    _D5_EPISODE_ID,
)

@pytest.fixture(scope="module")
def runtime_payload():
    snapshot = _d5_snapshot()
    rows = [deepcopy(snapshot.generation.episodes[0]) for _ in range(27)]
    for i, row in enumerate(rows[:-1], 1):
        row['episode_id'] += '-browser-fixture-' + str(i)
    # Opaque identity fixtures exercise the UI only; the B1 reader is tested natively elsewhere.
    directory = build_episode_directory(_d5_snapshot(episodes=tuple(rows)), query='', limit=100, offset=0)
    vector = _build_d5(episode=rows[-1], episode_generation_id=snapshot.generation_id,
                       episode_known_at=snapshot.generation.events[0]['known_at'])
    views = {language: build_earnings_view(vector, language=language) for language in ('en', 'zh')}
    assert directory['episodes'][0]['episode_ref'] == views['en']['episode_ref']
    return {'directory': directory, 'view': views}

@pytest.mark.parametrize('scenario', ['happy','anonymous','absent_auth','auth_race','timeout',
    'late_response','wronglink','rank','nonjson','oversize','search','pagination','distinct_episodes',
    'wrongref','http401','http402','http403','http409','http503','late_account_response','language',
    'close','signout','account_change','hidden','pagehide','token_refresh','user_updated','superseded_response','unsubmitted_input',
    'unsubmitted_pagination','unsubmitted_first','first_generation','changed_first_generation',
    'signin_recovery','expired_signin_recovery','signin_closed','signin_repeat','signin_forbidden'])
def test_browser_runtime_contract(runtime_payload, scenario):
    node = shutil.which('node')
    assert node, 'Node is required by the existing frontend test owner'
    payload = {**runtime_payload, 'scenario': scenario}
    result = subprocess.run(
        [node, str(ROOT/'tests/fixtures/prophet_lab/earnings_browser_runtime.mjs'),
         str(T/'_prophet_earnings_browser.js.j2')],
        input=json.dumps(payload), capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['scenario'] == scenario and receipt['status'] == 'PASS'


def test_matching_generation_pin_reuses_one_atomic_b1_snapshot(monkeypatch):
    monkeypatch.delenv("PROPHET_LAB_DISABLED", raising=False)
    snapshot = _d5_snapshot()
    loads = []

    def load_snapshot(_root):
        loads.append(snapshot.generation_id)
        return snapshot

    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", load_snapshot)
    monkeypatch.setattr(api, "_load_issuer_master", lambda _: _api_master(include_cik=False))
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as client:
        response = client.get(
            f"/api/prophet/lab/v1/episodes/{_D5_EPISODE_ID}/research-view",
            params={"expected_generation": snapshot.generation_id},
        )
    assert response.status_code == 200
    assert loads == [snapshot.generation_id]
