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

import os
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

def _broken_earnings(**_kwargs):
    raise RuntimeError("private-path secret should not escape")


@pytest.fixture(scope="module")
def partial_payload(tmp_path_factory):
    """The REAL degraded envelope, served by the REAL route over a REAL store.

    The browser contract is proved against the bytes the route actually
    emits, not against a hand-written imitation of them: a route change that
    breaks the browser, or a browser change that stops understanding the
    route, is visible here rather than in production.
    """
    from engine import prophet_candidate_state as b3_owner
    from tests.test_prophet_candidate_state import ASSEMBLY_NOW, _load_snapshot
    from tests.test_prophet_lab_research_opportunity_context import (
        _build_store, _episode_id,
    )

    root = _build_store(tmp_path_factory.mktemp("browser_partial_store"))
    snapshot = _load_snapshot(root)
    directory = build_episode_directory(snapshot, query="", limit=25, offset=0)
    ladder = {
        "PROPHET_LAB_EPISODE_STORE_ROOT": str(root / "data/us_prophet_rank/episodes"),
        "PROPHET_LAB_SECURITY_MASTER_PATH": str(root / "data/reference/security_master.parquet"),
        "PROPHET_LAB_VENDOR_ALIASES_PATH": str(root / "data/reference/vendor_aliases.parquet"),
    }
    previous_env = {name: os.environ.get(name) for name in ladder}
    previous_vector = api.build_earnings_intelligence_vector
    previous_clock = b3_owner._assembly_now
    views = {}
    try:
        os.environ.pop("PROPHET_LAB_DISABLED", None)
        for name, value in ladder.items():
            os.environ[name] = value
        b3_owner._assembly_now = lambda: ASSEMBLY_NOW
        api.build_earnings_intelligence_vector = _broken_earnings
        for language in ("en", "zh"):
            app = FastAPI()
            app.include_router(api.router)
            app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-entitled"}
            with TestClient(app) as c:
                response = c.get(
                    f"/api/prophet/lab/v1/episodes/{_episode_id(root)}/research-view",
                    params={"language": language},
                )
            assert response.status_code == 200, response.text
            views[language] = response.json()
    finally:
        api.build_earnings_intelligence_vector = previous_vector
        b3_owner._assembly_now = previous_clock
        for name, value in previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    assert views["en"]["view_version"] == "research-opportunity-context/1"
    return {"directory": directory, "view": views}


@pytest.mark.parametrize('scenario', ['opportunity_partial','opportunity_zh','opportunity_injected',
    'opportunity_wrongref','opportunity_nocontract','opportunity_nocontext','opportunity_badstate',
    'opportunity_badentry','opportunity_badauthority','opportunity_focus'])
def test_browser_runtime_degraded_opportunity_contract(partial_payload, scenario):
    """The DEGRADED envelope drives the REAL browser consumer in REAL node."""
    node = shutil.which('node')
    assert node, 'Node is required by the existing frontend test owner'
    payload = {'partial': partial_payload, 'scenario': scenario}
    result = subprocess.run(
        [node, str(ROOT/'tests/fixtures/prophet_lab/earnings_browser_runtime.mjs'),
         str(T/'_prophet_earnings_browser.js.j2')],
        input=json.dumps(payload), capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['scenario'] == scenario and receipt['status'] == 'PASS'


def test_the_degraded_envelope_is_the_route_s_own_output(partial_payload):
    """The browser fixture is the route's bytes, not an imitation of them."""
    body = partial_payload['view']['en']
    assert body['state'] == 'PARTIAL'
    assert body['reason'] == 'EARNINGS_UNAVAILABLE'
    assert body['earnings_source_state'] == {'state': 'UNAVAILABLE', 'reason': 'EARNINGS_UNAVAILABLE'}
    assert body['opportunity_context']['status'] == 'PARTIAL'
    assert body['opportunity_context']['context']['schema'] == 'prophet.lab_opportunity_context/v1'
    # the envelope binds to the very episode the directory lists
    listed = partial_payload['directory']['episodes'][0]['episode_ref']
    assert body['episode_ref'] == listed
    # and it carries no earnings payload at all
    for key in ('metrics', 'summary', 'expectation_revision', 'availability', 'hold',
                'source_projection_id', 'decision_cut', 'coverage'):
        assert key not in body


def test_the_browser_source_keeps_its_safety_contracts():
    """The new branch may not weaken any incumbent browser guarantee."""
    s = (T/'_prophet_earnings_browser.js.j2').read_text()
    for bad in ("innerHTML", "outerHTML", "DOMParser", "localStorage", "sessionStorage",
                "console.", "document.cookie", "setInterval"):
        assert bad not in s
    # the incumbent full-earnings validator is untouched: it still refuses
    # anything that is not the earnings-detail/1 version.
    assert "v.view_version!=='earnings-detail/1'" in s
    # the degraded envelope has its own closed version and its own validator
    assert "research-opportunity-context/1" in s
    assert "validateOpportunityView" in s
    assert "OPPORTUNITY_VIEW_VERSION" in s
    # focus recovery is present and the focus ring survives
    assert "pendingFocus" in s and "focusChosen" in s
    assert "outline:2px solid var(--info)" in (T/'_prophet_earnings_browser.css.j2').read_text()


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


# --- Design doctrine §3 (2026-10-18): no colored container edges -------------
# docs/DESIGN_DOCTRINE.md §3 bans a colored left border, inset stripe,
# pseudo-element rail, or equivalent edge accent on a container, and forbids
# relocating that stripe to another edge.  Containers use even, neutral
# borders; complete keyboard focus outlines are explicitly exempt and must
# survive the repair.  This regression pins that rule for the Prophet Lab
# evidence drawer, which has two independent CSS owners.
NEUTRAL_BORDER_VALUES = frozenset({"none", "transparent", "inherit", "currentcolor", "0"})
NEUTRAL_SURFACE_TOKENS = frozenset({
    "--line", "--panel", "--panel2", "--panel3", "--text", "--muted", "--bg",
    "--surface", "--card-shadow",
})


def _css_rules(css):
    """(selector, body) pairs for every rule in a stylesheet."""
    return [(m.group(1).strip(), m.group(2))
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def _colored_edge_accents(css):
    """Every colored container-edge accent in a stylesheet, as text lines."""
    accents = []
    for selector, body in _css_rules(css):
        for match in re.finditer(
                r"(?<![\w-])border-(left|right|top|bottom)\s*:\s*([^;}]+)", body):
            value = match.group(2).strip().lower()
            if value in NEUTRAL_BORDER_VALUES or "var(--line)" in value:
                continue
            accents.append(
                f"{selector} :: border-{match.group(1)}: {match.group(2).strip()}")
        for match in re.finditer(r"(?<![\w-])box-shadow\s*:\s*([^;}]+)", body):
            value = match.group(1).strip().lower()
            if "inset" in value and "var(--line)" not in value:
                accents.append(
                    f"{selector} :: inset colour stripe: box-shadow: {match.group(1).strip()}")
        if "::before" in selector or "::after" in selector:
            for match in re.finditer(
                    r"(?<![\w-])background(?:-color)?\s*:\s*([^;}]+)", body):
                tokens = re.findall(r"var\((--[\w-]+)\)", match.group(1))
                if any(token not in NEUTRAL_SURFACE_TOKENS for token in tokens):
                    accents.append(
                        f"{selector} :: pseudo-element rail: background: {match.group(1).strip()}")
    return accents


def test_no_colored_container_edge_accent_in_emitted_and_template_css():
    """Design doctrine §3 (2026-10-18): no colored container edges."""
    env = Environment(loader=FileSystemLoader(T), autoescape=True)
    template_css = env.get_template("_prophet_earnings_browser.css.j2").render()
    fragment = render_earnings_fragment(corrected_payload(), language="en")
    emitted_css = re.search(r"<style>(.*?)</style>", fragment, re.S).group(1)

    # The native STYLE constant and the template are two independent owners of
    # the same rules; the fragment emits the native one at request time.
    for label, css in (("emitted CSS view", emitted_css),
                       ("native STYLE constant", STYLE),
                       ("template CSS", template_css)):
        accents = _colored_edge_accents(css)
        assert not accents, f"{label} still carries a colored container edge: {accents}"

    # The container keeps one even, neutral border and nothing else, so a
    # stripe cannot survive on another edge either.
    for label, css in (("emitted CSS view", emitted_css), ("template CSS", template_css)):
        body = next((b for s, b in _css_rules(css) if s == ".plab-evidence .pe-state"), None)
        assert body is not None, f"{label} lost the .plab-evidence .pe-state rule"
        borders = re.findall(
            r"(?<![\w-])(border|border-(?:left|right|top|bottom))\s*:\s*([^;}]+)", body)
        assert borders == [("border", "1px solid var(--line)")], (
            f"{label} .plab-evidence .pe-state must declare exactly the even "
            f"neutral border, got {borders}")

    # The complete keyboard focus ring is exempt from the doctrine and must
    # survive the repair untouched.
    for label, css in (("emitted CSS view", emitted_css), ("template CSS", template_css)):
        assert "outline:2px solid var(--info)" in css, f"{label} lost the focus ring"
        assert "outline-offset" in css, f"{label} lost the focus ring offset"

    # The two owners stay in lockstep, and native source semantics are
    # unmodified: the evidence still presents the same numbers and the same
    # status callout.
    assert STYLE.strip() in template_css, "template CSS and native STYLE diverged"
    view = build_earnings_view(_build_d5())
    assert view["metrics"][0]["display_value"] == "$109,417,000,000"
    assert view["presentation"]["title"] == "Earnings evidence"
    assert view["presentation"]["separate"][0]["label"] == "Forward expectations"
    assert "Not connected" in view["presentation"]["separate"][0]["note"]
    assert view["expectation_revision"]["state"] == "NOT_CONNECTED"
    assert not any(view["authority"].values())
    assert "class='pe-state'" in fragment and "role='status'" in fragment
