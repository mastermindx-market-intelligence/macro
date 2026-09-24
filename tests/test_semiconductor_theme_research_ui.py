"""tests/test_semiconductor_theme_research_ui.py — T10 part 1 acceptance tests.

Generic, theme-agnostic paid research client (``site/assets/js/theme-research.js``)
mounted hidden + empty in ``templates/state_of_themes.html.j2``. No backend
exists yet: the client is written against the FROZEN response envelope
(operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001, plan §3.2/§3.4)
and exercised here with synthetic payloads only.

Three proof layers:

1. CONTRACT — the DOM-free block between the THEME-RESEARCH-CONTRACT markers is
   lifted verbatim and EXECUTED under node (same idiom as
   tests/test_intelligence_hub_market_pulse_client.py and the dossier test),
   proving the epoch/principal account-safety laws by execution.
2. SOURCE — account-surface regexes on the shipped file: no innerHTML
   assignment with a non-literal RHS, storage only for the single remembered
   'theme_research_sel' key, no cookies, auth via MDXAuth only, fetch targets
   derived only from the mount's data-api-* attributes.
3. TEMPLATE/CSS — the hidden mount renders through the same builder used by
   tests/test_state_of_themes.py, carries no boot payload (no application/json
   script, no 'generation' string), and the stylesheet carries no hardcoded
   hex colors outside comments.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

JS_PATH = REPO_ROOT / "site" / "assets" / "js" / "theme-research.js"
CSS_PATH = REPO_ROOT / "site" / "assets" / "css" / "theme-research.css"
TPL_PATH = REPO_ROOT / "templates" / "state_of_themes.html.j2"

HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

_BEGIN = "/* THEME-RESEARCH-CONTRACT-BEGIN */"
_END = "/* THEME-RESEARCH-CONTRACT-END */"

TOP_KEYS = (
    "schema", "definition_version", "generation", "request", "native_subjects",
    "summary", "companies", "industrial_views", "economics", "expectations",
    "evidence_refs", "authorized_coverage", "limitations", "authority",
)


@pytest.fixture(scope="module")
def js_text() -> str:
    if not JS_PATH.exists():
        pytest.skip("site/ is not checked out in this sparse worktree")
    return JS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css_text() -> str:
    if not CSS_PATH.exists():
        pytest.skip("site/ is not checked out in this sparse worktree")
    return CSS_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Synthetic envelope (FROZEN contract — every closed top-level key present)
# ---------------------------------------------------------------------------

def _envelope(**over) -> dict:
    body = {
        "schema": "semiconductor_theme_research.v1",
        "definition_version": "dv-2026-09-24",
        "generation": "g1",
        "request": {
            "anchor_theme_id": "ai_semiconductors",
            "slice_key": "hbm_packaging",
            "view": "composition",
            "time_mode": "latest",
            "offset": 0,
            "limit": 20,
        },
        "native_subjects": {"status": "ready", "subjects": []},
        "summary": {
            "status": "ready",
            "what_changed": "Advanced-packaging capacity quotes revised up",
            "why_it_matters": "Packaging, not wafer capacity, stays the bottleneck",
            "offset": 0,
            "next_evidence": "Quarterly capex filings",
        },
        "companies": {"status": "ready", "rows": []},
        "industrial_views": {
            "status": "ready",
            "composition": {
                "status": "ready",
                "rows": [{
                    "label": "Packaging share of bill of materials",
                    "value": "rising",
                    "note": "coWoS-style capacity sold out",
                    "label_kind": "fact",
                }],
            },
        },
        "economics": {"status": "ready", "rows": []},
        "expectations": {
            "management": {"status": "ready"},
            "external_consensus": {"status": "ready"},
            "house_forecast": {"status": "degraded"},
            "market_incorporation": {"status": "unavailable"},
        },
        "evidence_refs": ["hbm_capex_2026q3", "packaging_supply_note"],
        "authorized_coverage": {"status": "ready"},
        "limitations": {"status": "ready"},
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate": False,
            "can_open_entry": False,
        },
    }
    body.update(over)
    return body


def _bad_payloads() -> list[dict]:
    bad = []
    for key in TOP_KEYS:
        body = _envelope()
        body.pop(key)
        bad.append({"name": f"missing_{key}", "payload": body})

    body = _envelope()
    body["surprise_key"] = "must not be accepted"
    bad.append({"name": "extra_key", "payload": body})

    bad.append({"name": "wrong_schema", "payload": _envelope(schema="semiconductor_theme_research.v2")})
    bad.append({"name": "generation_not_string", "payload": _envelope(generation=7)})

    body = _envelope()
    body["authority"]["can_rank"] = True
    bad.append({"name": "authority_can_rank_true", "payload": body})

    body = _envelope()
    body["authority"].pop("can_open_entry")
    bad.append({"name": "authority_key_missing", "payload": body})

    body = _envelope()
    body["companies"]["status"] = "ok"
    bad.append({"name": "section_status_ok", "payload": body})

    body = _envelope()
    body["expectations"].pop("management")
    bad.append({"name": "expectation_missing", "payload": body})

    body = _envelope()
    body["expectations"]["management"]["status"] = "pending"
    bad.append({"name": "expectation_status_bad", "payload": body})

    bad.append({"name": "empty_generation", "payload": _envelope(generation="")})
    return bad


# ---------------------------------------------------------------------------
# Node harness — executes the extracted contract block
# ---------------------------------------------------------------------------

_HARNESS = r"""
%(contract)s

var results = {};
var cases = JSON.parse(process.argv[2]);

/* The accepted plan's assertion, verbatim semantics: a late response for
   another epoch/user is dropped, and clearResearchState keeps payload null. */
const state = {epoch: 2, principalKey: 'user-B', payload: null};
results.plan_step1 =
  (applyResearchResponse(state, 1, 'user-A', {generation: 'old'}) === false
   && state.payload === null);
results.plan_error_untouched = (state.error === undefined);
clearResearchState(state);
results.plan_step2 = (state.payload === null);

/* epoch matches, principalKey differs → dropped, nothing changes */
var sA = {epoch: 3, principalKey: 'user-A', payload: null, error: null, generation: null};
results.drop_principal =
  (applyResearchResponse(sA, 3, 'user-B', cases.valid) === false
   && sA.payload === null && sA.error === null && sA.generation === null);

/* epoch differs, principalKey matches → dropped, nothing changes */
var sB = {epoch: 3, principalKey: 'user-A', payload: null, error: null, generation: null};
results.drop_epoch =
  (applyResearchResponse(sB, 2, 'user-A', cases.valid) === false
   && sB.payload === null && sB.error === null && sB.generation === null);

/* valid envelope accepted */
var sC = {epoch: 7, principalKey: 'user-A', payload: null, error: null, generation: null, selection: null};
results.accept = (applyResearchResponse(sC, 7, 'user-A', cases.valid) === true);
results.accept_state =
  (sC.payload === cases.valid && sC.generation === 'g1' && sC.error === null);

/* every mutation → invalid_envelope, payload stays null */
results.rejects = {};
cases.bad.forEach(function (c) {
  var st = {epoch: 1, principalKey: 'user-A', payload: null, error: null, generation: null};
  var applied = applyResearchResponse(st, 1, 'user-A', c.payload);
  results.rejects[c.name] =
    (applied === false && st.payload === null
     && st.error && st.error.code === 'invalid_envelope');
});

/* validateEnvelope direct contract */
results.validate_ok = (validateEnvelope(cases.valid).ok === true);
results.validate_reason_null = (validateEnvelope(cases.valid).reason === null);

/* nextEpoch: increments, rebinds principal, clears payload/generation/error */
var sD = {epoch: 5, principalKey: 'user-A', payload: {x: 1}, generation: 'g9',
          error: {code: 'service_unavailable'}, selection: {slice_key: 'a'}};
var nextVal = nextEpoch(sD, 'user-B');
results.next_epoch = (nextVal === 6 && sD.epoch === 6 && sD.principalKey === 'user-B'
  && sD.payload === null && sD.generation === null && sD.error === null);

/* clearResearchState keeps epoch/principalKey/selection */
var sE = {epoch: 9, principalKey: 'user-C', payload: {y: 2}, generation: 'g2',
          error: {code: 'x'}, selection: {slice_key: 'b'}};
var retE = clearResearchState(sE);
results.clear_keeps = (retE === sE && sE.epoch === 9 && sE.principalKey === 'user-C'
  && sE.payload === null && sE.error === null && sE.generation === null
  && sE.selection && sE.selection.slice_key === 'b');

/* textSafe: literal text, no HTML interpretation */
var t1 = textSafe('<b>x</b>');
results.textsafe_literal = (typeof t1 === 'string' && t1.indexOf('<b>') >= 0);

/* newResearchState shape */
var s0 = newResearchState();
results.new_state = (s0.epoch === 0 && s0.principalKey === 'anon'
  && s0.payload === null && s0.error === null && s0.generation === null
  && s0.selection === null);

console.log(JSON.stringify(results));
"""


def _contract(js_text: str) -> str:
    a = js_text.index(_BEGIN)
    b = js_text.index(_END)
    assert a < b, f"{_BEGIN} must precede {_END}"
    return js_text[a:b]


def _run_battery(js_text: str) -> dict:
    assert shutil.which("node"), "node not on PATH"
    src = _HARNESS % {"contract": _contract(js_text)}
    cases = {"valid": _envelope(), "bad": _bad_payloads()}
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "theme_research_contract.js"
        path.write_text(src, encoding="utf-8")
        run = subprocess.run(
            [shutil.which("node"), str(path), json.dumps(cases)],
            capture_output=True, text=True, timeout=60,
        )
    assert run.returncode == 0, f"node exited {run.returncode}:\n{run.stderr}\n{run.stdout}"
    assert run.stdout.strip(), f"no stdout; stderr:\n{run.stderr}"
    return json.loads(run.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# 1. Contract markers
# ---------------------------------------------------------------------------

def test_contract_markers_present_exactly_once(js_text):
    assert js_text.count(_BEGIN) == 1, "THEME-RESEARCH-CONTRACT-BEGIN must appear exactly once"
    assert js_text.count(_END) == 1, "THEME-RESEARCH-CONTRACT-END must appear exactly once"
    assert js_text.index(_BEGIN) < js_text.index(_END)


# ---------------------------------------------------------------------------
# 2. Executed contract (node)
# ---------------------------------------------------------------------------

@needs_node
def test_plan_verbatim_late_response_assertion(js_text):
    out = _run_battery(js_text)
    assert out["plan_step1"] is True, "late response for another epoch/user must be dropped"
    assert out["plan_step2"] is True, "clearResearchState must keep payload null"
    assert out["plan_error_untouched"] is True, "a dropped response must change NOTHING"


@needs_node
def test_epoch_and_principal_each_independently_drop(js_text):
    out = _run_battery(js_text)
    assert out["drop_principal"] is True, "matching epoch + different principal must drop"
    assert out["drop_epoch"] is True, "different epoch + matching principal must drop"


@needs_node
def test_valid_synthetic_envelope_accepted(js_text):
    out = _run_battery(js_text)
    assert out["accept"] is True, out
    assert out["accept_state"] is True, out
    assert out["validate_ok"] is True, out
    assert out["validate_reason_null"] is True, out


@needs_node
def test_envelope_mutations_rejected_as_invalid_envelope(js_text):
    out = _run_battery(js_text)
    rejects = out["rejects"]
    expected = {c["name"] for c in _bad_payloads()}
    assert set(rejects) == expected, rejects
    failures = [name for name, ok in rejects.items() if ok is not True]
    assert not failures, f"mutations not refused as invalid_envelope: {failures}"


@needs_node
def test_next_epoch_and_clear_semantics(js_text):
    out = _run_battery(js_text)
    assert out["next_epoch"] is True, out
    assert out["clear_keeps"] is True, out
    assert out["new_state"] is True, out


@needs_node
def test_textsafe_returns_literal_text(js_text):
    out = _run_battery(js_text)
    assert out["textsafe_literal"] is True, out


@needs_node
def test_node_syntax_check():
    result = subprocess.run(
        ["node", "--check", str(JS_PATH)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"node --check failed:\n{result.stderr}"


# ---------------------------------------------------------------------------
# 3. Source-level account-safety surface
# ---------------------------------------------------------------------------

def test_no_innerhtml_assignment_with_nonliteral_rhs(js_text):
    """Only `innerHTML = ''` is allowed; the client must use textContent."""
    offenders = []
    for m in re.finditer(r"innerHTML\s*=(.{0,40})", js_text):
        rhs = m.group(1).strip()
        if rhs.startswith("''") or rhs.startswith('""'):
            continue
        offenders.append(m.group(0))
    assert not offenders, f"non-literal innerHTML assignment: {offenders}"


def test_storage_surface_only_remembered_selection_key(js_text):
    assert "sessionStorage" not in js_text
    assert "indexedDB" not in js_text.lower()
    assert "document.cookie" not in js_text
    uses = re.findall(
        r"localStorage\s*\.\s*(?:getItem|setItem|removeItem)\s*\(\s*(['\"])([^'\"]*)\1",
        js_text,
    )
    assert uses, "expected the single allowed remembered-selection key"
    bad_keys = {key for _, key in uses if key != "theme_research_sel"}
    assert not bad_keys, f"storage keys beyond theme_research_sel: {bad_keys}"
    # every bare mention of localStorage is one of the audited calls
    assert len(re.findall(r"localStorage", js_text)) == len(uses), (
        "localStorage referenced outside the audited getItem/setItem/removeItem calls"
    )


def test_auth_acquisition_is_mdxauth_only(js_text):
    assert "MDXAuth.client()" in js_text, "session token must come from MDXAuth.client()"
    assert "MDXAuth.onChange(" in js_text, "auth changes must be observed via MDXAuth.onChange"
    low = js_text.lower()
    assert "supabase" not in low, "no second auth SDK may be referenced"
    assert "createclient" not in low


def test_fetch_targets_derive_from_mount_dataset(js_text):
    targets = set(re.findall(r"fetch\(\s*([A-Za-z_$][\w$]*)\s*,", js_text))
    assert targets == {"apiQueryUrl", "apiEvidenceUrl"}, (
        f"every fetch() must target a mount-derived variable; found: {targets}"
    )
    assert "getAttribute('data-api-query')" in js_text
    assert "getAttribute('data-api-evidence')" in js_text


def test_abortcontroller_used(js_text):
    assert "AbortController" in js_text
    assert ".abort()" in js_text


# ---------------------------------------------------------------------------
# 4. Template mount — rendered through the state_of_themes builder
# ---------------------------------------------------------------------------

def _render_page(tmp_path: Path) -> str:
    from tests.test_state_of_themes import _make_sot_root
    import scripts.build_state_of_themes as sot
    root = _make_sot_root(tmp_path)
    return sot.render(root)


def test_template_mount_renders_hidden_and_empty(tmp_path):
    html = _render_page(tmp_path)

    # exactly one mount, hidden
    assert html.count("data-theme-research-mount") == 1, "mount must render exactly once"
    m = re.search(r'<section class="theme-research"[^>]*>', html)
    assert m, "mount <section> not found in rendered page"
    assert "hidden" in m.group(0), "mount must carry the hidden attribute"

    # the four data attributes, exactly as frozen
    for attr, val in (
        ("data-anchor-theme-id", "ai_semiconductors"),
        ("data-slices", "hbm_packaging,sic_gan_specialty"),
        ("data-api-query", "/api/themes/v1/research/query"),
        ("data-api-evidence", "/api/themes/v1/research/evidence"),
    ):
        assert f'{attr}="{val}"' in html, f"{attr} missing/wrong in mount"

    # bilingual title + note (both spans render; CSS picks the language)
    assert "Semiconductor industry research" in html
    assert "半导体产业研究" in html

    # no boot payload of any kind
    assert "application/json" not in html, "no JSON boot script allowed in the template"
    assert "generation" not in html, "no generation/payload data may ship in the shell"


def test_template_asset_includes_exactly_once(tmp_path):
    html = _render_page(tmp_path)
    assert html.count('<link rel="stylesheet" href="assets/css/theme-research.css">') == 1
    assert html.count('<script defer src="assets/js/theme-research.js?v=20260924a"></script>') == 1
    # includes sit immediately after their canonical siblings
    assert '<link rel="stylesheet" href="theme.css">\n<link rel="stylesheet" href="assets/css/theme-research.css">' in html
    assert '<script src="theme.js"></script>\n<script defer src="assets/js/theme-research.js?v=20260924a"></script>' in html


def test_template_source_mount_block_is_frozen():
    tpl = TPL_PATH.read_text(encoding="utf-8")
    # the mount sits inside the lanes branch, immediately before the disclosure
    assert tpl.index("data-theme-research-mount") < tpl.index('<p class="sot-disclosure">')
    assert tpl.count("data-theme-research-mount") == 1


# ---------------------------------------------------------------------------
# 5. CSS
# ---------------------------------------------------------------------------

def test_css_no_hardcoded_hex_outside_comments(css_text):
    stripped = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    hits = re.findall(r"#[0-9a-fA-F]{3,8}\b", stripped)
    assert not hits, f"hardcoded hex colors outside comments: {hits}"


def test_css_has_overflow_wrap_and_bilingual_rules(css_text):
    assert "overflow-wrap" in css_text, "long labels must wrap (overflow-wrap)"
    assert ".l-en" in css_text and ".l-zh" in css_text, (
        "bilingual pair rules must ship with the component"
    )
    assert "[hidden]" in css_text, "hidden-attribute rules must ship with the component"
