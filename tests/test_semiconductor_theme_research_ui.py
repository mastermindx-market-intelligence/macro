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
    # Same-origin guard resolves the mount attribute once, then the runtime
    # references the resolved handle in every fetch(). Both the raw
    # mount attribute AND the resolved URL must reach the fetch call.
    assert "getAttribute('data-api-query')" in js_text
    assert "getAttribute('data-api-evidence')" in js_text
    assert "fetch(queryUrl," in js_text, "fetch must target the same-origin-resolved query URL"
    assert "fetch(evidenceUrl," in js_text, "fetch must target the same-origin-resolved evidence URL"
    # No cross-origin string literals may be passed to fetch.
    assert "fetch('http" not in js_text
    assert 'fetch("http' not in js_text
    # The bare raw mount variables must not appear in a fetch() call.
    bare = set(re.findall(r"fetch\(\s*apiQueryUrl\s*,", js_text))
    bare |= set(re.findall(r"fetch\(\s*apiEvidenceUrl\s*,", js_text))
    assert not bare, (
        "raw mount attribute (apiQueryUrl/apiEvidenceUrl) must reach fetch "
        "through the same-origin guard, not as the literal URL argument"
    )


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


# ---------------------------------------------------------------------------
# 6. T10 review fixes — bilingual option law, limitations render,
#    typed refusals (402, invalid_json, endpoint_not_same_origin), NIT-8
#    qualifier, Next-button-at-end, leak/credential/exfiltration/storage/
#    XSS-sink laws, plus the discriminating node batteries that would fail
#    for a client that violates any of those laws.
# ---------------------------------------------------------------------------

_OPTION_TAB_KEPT = (
    "Build the four tab-row builders identically so the same regex catches "
    "any option-construction regression. If this comment disappears, the "
    "discriminator broke too."
)


# a. Option labels: no dual-span inside <option>, data-en/data-zh set,
#    a langchange listener exists, and optionLabelsFor is a pure helper.

def test_options_no_dual_span_inside_option(js_text):
    """BLOCKING-1. Browsers take an <option>'s label from textContent only;
    any element children render as concatenated raw text. A regression here
    ships a 'Latest build最新构建' closed select. The fix sets single-language
    text plus data-en/data-zh and relabels on theme.js's langchange event."""
    # option construction pattern: opt.setAttribute('data-en', …) AND opt.textContent = …
    option_blocks = re.findall(
        r"MODES\.forEach\(function\s*\(key\)\s*\{(.*?)\}\);",
        js_text,
        re.DOTALL,
    )
    assert option_blocks, "MODES.forEach option builder not found"
    body = option_blocks[0]
    assert "appendChild(t(" not in body, (
        "option construction must NOT append a t(en, zh) span — the closed "
        "<select> shows BOTH languages concatenated"
    )
    assert 'setAttribute(\'data-en\'' in body or 'setAttribute("data-en"' in body, (
        "every option must carry a data-en attribute"
    )
    assert 'setAttribute(\'data-zh\'' in body or 'setAttribute("data-zh"' in body, (
        "every option must carry a data-zh attribute"
    )
    assert re.search(r"opt\.textContent\s*=", body), (
        "every option must set textContent to a single-language string"
    )


def test_langchange_listener_relabels_options(js_text):
    """BLOCKING-1. site/theme.js dispatches 'langchange' on document; the
    shipped a7851105.js pattern is the canonical reference. A regression
    where the listener is dropped leaves the closed select stuck in EN
    even when the user toggles language."""
    assert "addEventListener('langchange'" in js_text, (
        "langchange listener must be registered on document"
    )
    # the relabeling helper must walk the option data-* attributes
    assert "querySelectorAll('option[data-zh]')" in js_text, (
        "langchange relabel must walk every option[data-zh] node"
    )
    # initial label applied at boot from documentElement data-lang
    assert "getAttribute('data-lang')" in js_text, (
        "the boot label must derive from documentElement data-lang"
    )
    # the relabel reads BOTH data-zh and data-en — a regression that only
    # reads one would silently swap a single language on toggle
    assert "getAttribute('data-zh')" in js_text
    assert "getAttribute('data-en')" in js_text
    # relabelModeOptions() must be invoked at least twice — once at boot
    # (so the closed select reflects the initial documentElement data-lang)
    # and once on langchange (so toggles propagate)
    assert js_text.count("relabelModeOptions") >= 2, (
        "relabelModeOptions must be called at boot AND bound to langchange"
    )


@needs_node
def test_option_labels_for_lang_pure_helper(js_text):
    """BLOCKING-1 node battery: optionLabelsFor(lang) returns exactly three
    single-language strings; 'en' yields no zh-only characters and vice
    versa. The same map backs the runtime <option> construction."""
    out = _run_review_battery(js_text)
    en = out.get("opt_en")
    zh = out.get("opt_zh")
    assert en and zh, f"optionLabelsFor result missing: en={en!r} zh={zh!r}"
    assert isinstance(en, list) and isinstance(zh, list), (
        "optionLabelsFor must return arrays"
    )
    assert len(en) == 3 and len(zh) == 3, (
        f"optionLabelsFor must return one string per closed mode key: en={en} zh={zh}"
    )
    for s in en + zh:
        assert isinstance(s, str), f"optionLabelsFor strings must be plain strings: {s!r}"
    # The EN list must NOT contain CJK characters; the ZH list must NOT
    # contain bare English mode labels. Cross-contamination proves the
    # helper has been wired with both data sets.
    for s in en:
        assert not re.search(r"[一-鿿]", s), f"EN label has CJK characters: {s!r}"
    for s in zh:
        assert re.search(r"[一-鿿]", s), f"ZH label has no CJK characters: {s!r}"


# b. Limitations render — visible region, entries or status word, hidden
#    while gated.

@needs_node
def test_limitations_model_ready_yields_entries(js_text):
    """BLOCKING-2. A successful envelope with limitation entries yields
    those entries (text-only) so the renderer can put them on screen."""
    out = _run_review_battery(js_text)
    model = out["lim_ready"]
    assert model is not None, "limitationsModel not executed under node"
    assert isinstance(model.get("limitations"), list), (
        f"ready envelope must yield its limitation entries; got: {model}"
    )
    assert model["limitationsStatus"] == "ready", (
        f"limitationsStatus must be 'ready'; got: {model['limitationsStatus']}"
    )
    assert model["limitations"], "ready envelope must yield at least one entry"
    for entry in model["limitations"]:
        assert isinstance(entry, str), (
            f"limitation entries must be plain strings (renderer is textContent-only); got: {entry!r}"
        )


@needs_node
def test_limitations_model_unavailable_yields_status_word(js_text):
    """BLOCKING-2. A degraded/unavailable envelope (or a ready envelope with
    no entries) yields null entries — the renderer prints the typed status
    word instead of an empty region. Coverage status is reported
    independently so the caveat line is never blank."""
    out = _run_review_battery(js_text)
    for label, model in (
        ("lim_unavailable", out["lim_unavailable"]),
        ("lim_empty", out["lim_empty"]),
    ):
        assert model is not None, f"{label}: limitationsModel not executed under node"
        assert model["limitations"] is None, (
            f"{label}: non-success / empty envelope must yield null entries; "
            f"got: {model['limitations']!r}"
        )
        # Coverage status is whatever the payload carried (the caveat line
        # is always rendered, never an empty region).
        assert model["coverageStatus"] in ("ready", "degraded", "unavailable", "refused"), (
            f"{label}: coverageStatus must be a closed status word; "
            f"got: {model['coverageStatus']!r}"
        )


@needs_node
def test_limitations_model_no_payload_yields_nothing(js_text):
    """BLOCKING-2. The DOM gating (hidden region) is a render concern; the
    pure helper must not assume a payload and must return null/None for
    every field when given no payload at all."""
    out = _run_review_battery(js_text)
    model = out["lim_null"]
    assert model is not None, "limitationsModel not executed under node"
    assert model["limitations"] is None
    assert model["limitationsStatus"] is None
    assert model["coverageStatus"] is None


# c. Arithmetic ban on paid figures.

def test_no_arithmetic_on_paid_figures(js_text):
    """Zero arithmetic on any paid figure. The only '+'/'-' arithmetic in
    this file is the pagination math on `offset` and `PAGE_LIMIT`; every
    other arithmetic operator on numeric literals is forbidden."""
    # Strip string literals (single + double quoted) so attribute names like
    # `data-theme-research-mount` don't trip the detector; strip comments
    # so a code comment mentioning `textSafe + textContent` doesn't either.
    stripped = re.sub(r"'[^'\n]*'", "", js_text)
    stripped = re.sub(r'"[^"\n]*"', "", stripped)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    # Forbidden primitives
    forbidden = [
        r"parseFloat\(",
        r"\bNumber\(",
        r"\.toFixed\(",
        r"\bmidpoint\b",
        r"\bdelta\b",
        r"\*\s*0\.5",
        r"/\s*2\b",
    ]
    hits = []
    for pat in forbidden:
        for m in re.finditer(pat, stripped):
            hits.append(m.group(0))
    assert not hits, f"forbidden arithmetic on paid figures: {hits}"
    # Pagination math on `offset` and `PAGE_LIMIT` is the only allowed '+'/'-'
    # arithmetic on numeric identifiers in this file. A `data-theme-mount`-
    # style HTML attribute cannot leak through (single-quote strings are
    # stripped above) — every remaining `id <op> id` site must involve at
    # least one of offset / PAGE_LIMIT / a Math.* wrapper.
    sites = re.findall(r"[a-zA-Z_$][\w$]*\s*[+\-]\s*[a-zA-Z_$][\w$]*", stripped)
    paginate_ids = {"offset", "PAGE_LIMIT"}
    unexpected = []
    for s in sites:
        ids = re.findall(r"[a-zA-Z_$][\w$]*", s)
        # at least one operand is pagination (offset / PAGE_LIMIT) or a
        # Math.* wrapper — both safe per the standing arithmetic-on-paid-
        # figures ban.
        if any(i in paginate_ids or i.startswith("Math") for i in ids):
            continue
        unexpected.append(s)
    assert not unexpected, (
        f"non-pagination arithmetic on numeric identifiers: {unexpected}; "
        f"pagination math (offset/PAGE_LIMIT) is the only allowed arithmetic "
        f"on numbers in this file"
    )


# d. Credential ban.

def test_no_credential_literals(js_text):
    """No JWT-shaped string, no Bearer followed by a literal token, no
    apikey/api_key/secret string literals anywhere in the file."""
    offenders = []
    # JWT-shaped literal — only matches an eyJ-shaped string with 10+ chars
    for m in re.finditer(r"['\"]eyJ[A-Za-z0-9_-]{10,}['\"]", js_text):
        offenders.append(("jwt", m.group(0)))
    # Bearer followed by a literal token: 'Bearer ' followed by an alphanumeric
    # run with no `+`/variable — `'Bearer eyJ…'` would match; `'Bearer ' + token`
    # would not.
    for m in re.finditer(r"['\"]Bearer\s+[A-Za-z0-9._\-]{8,}['\"]", js_text):
        offenders.append(("bearer", m.group(0)))
    # apikey / api_key / secret as string literals
    for kw in ("apikey", "api_key", "secret"):
        for m in re.finditer(rf"['\"]{kw}['\"]", js_text, re.IGNORECASE):
            offenders.append((kw, m.group(0)))
    assert not offenders, f"credential literal in source: {offenders}"
    # the only `Bearer` mention is the runtime header format — verify it's a
    # plain string literal followed by a `+` (template-built, never a token).
    bearer = re.findall(r"Bearer", js_text)
    assert bearer, "the only Bearer mention is the Authorization header template"
    for m in re.finditer(r"Bearer[^;]*", js_text):
        seg = m.group(0)
        if "+" in seg:
            continue
        raise AssertionError(f"Bearer used without a + token builder: {seg!r}")


# e. Exfiltration ban.

def test_no_exfiltration_channels(js_text):
    """No sendBeacon, no XMLHttpRequest, no `new Image(`, no WebSocket,
    no EventSource, no postMessage, and no string-literal `fetch('http…)`
    in the shipped file."""
    forbidden = [
        r"\bsendBeacon\s*\(",
        r"\bXMLHttpRequest\b",
        r"\bnew\s+Image\s*\(",
        r"\bWebSocket\s*\(",
        r"\bEventSource\s*\(",
        r"\bpostMessage\s*\(",
    ]
    hits = []
    for pat in forbidden:
        for m in re.finditer(pat, js_text):
            hits.append(m.group(0))
    assert not hits, f"forbidden exfiltration channel: {hits}"
    # No string-literal fetch('http…) — the only fetch() argument is the
    # resolved URL handle (queryUrl/evidenceUrl).
    for m in re.finditer(r"fetch\s*\(\s*['\"]http", js_text):
        hits.append(m.group(0))
    assert not hits, f"cross-origin string-literal fetch: {hits}"


# f. Storage value — the only stored value is a JSON object whose keys
#    are exactly the three selection keys.

@needs_node
def test_storage_value_only_three_selection_keys(js_text):
    out = _run_review_battery(js_text)
    valid = out["stored_valid"]
    assert isinstance(valid, dict), f"valid stored selection not parsed: {valid!r}"
    assert sorted(valid.keys()) == ["slice_key", "time_mode", "view"], (
        f"stored selection must carry exactly three keys; got: {sorted(valid.keys())}"
    )
    assert valid["slice_key"] in ("hbm_packaging", "sic_gan_specialty"), (
        f"stored slice must be in the closed vocabulary; got: {valid['slice_key']!r}"
    )
    assert valid["view"] in (
        "composition", "manufacturing", "commercial", "capacity", "economics",
    ), f"stored view must be in the closed vocabulary; got: {valid['view']!r}"
    assert valid["time_mode"] in ("latest", "source_history", "system_replay"), (
        f"stored time_mode must be in the closed vocabulary; got: {valid['time_mode']!r}"
    )
    # Every refusal case must yield None
    for label, result in (
        ("stored_payload", out["stored_payload"]),
        ("stored_token", out["stored_token"]),
        ("stored_extra_key", out["stored_extra_key"]),
        ("stored_bad_view", out["stored_bad_view"]),
        ("stored_bad_mode", out["stored_bad_mode"]),
        ("stored_garbage", out["stored_garbage"]),
    ):
        assert result is None, f"{label} must refuse the stored value; got: {result!r}"


# g. XSS sink ban broadened.

def test_no_xss_sinks(js_text):
    """Beyond innerHTML, the broader sink ban covers insertAdjacentHTML,
    outerHTML, document.write, eval(, new Function(, createContextualFragment.
    Any of these in a paid-theme client would be a regression."""
    sinks = [
        r"\binsertAdjacentHTML\s*\(",
        r"\.outerHTML\s*=",
        r"\bdocument\.write\s*\(",
        r"\beval\s*\(",
        r"\bnew\s+Function\s*\(",
        r"\bcreateContextualFragment\s*\(",
    ]
    hits = []
    for pat in sinks:
        for m in re.finditer(pat, js_text):
            hits.append(m.group(0))
    assert not hits, f"forbidden XSS sink in source: {hits}"


# h. Node battery for typed refusals, NIT-8 qualifier, Next-disabled.

@needs_node
def test_402_maps_to_gate_alongside_401_403(js_text):
    """NIT-5. The classifyFetchStatus helper dispatches 401/402/403 to the
    gate lane — only 'gate' allows the runtime to show the gate copy."""
    out = _run_review_battery(js_text)
    for code in (401, 402, 403):
        assert out[f"cls_{code}"] == "gate", (
            f"HTTP {code} must classify as 'gate'; got {out[f'cls_{code}']!r}"
        )
    assert out["cls_409"] == "conflict"
    assert out["cls_200"] == "json"
    assert out["cls_500"] == "http_error"


@needs_node
def test_same_origin_url_resolver_refuses_cross_origin(js_text):
    """NIT-7. resolveSameOrigin refuses a different origin with the typed
    code `endpoint_not_same_origin` and never produces a URL for fetch."""
    out = _run_review_battery(js_text)
    assert out["so_ok"] is True, "same-origin path must resolve"
    assert out["so_cross_origin"] is False, "different origin must be refused"
    assert out["so_cross_code"] == "endpoint_not_same_origin", (
        f"cross-origin refusal must surface the typed code; got: {out['so_cross_code']!r}"
    )
    assert out["so_empty_code"] == "endpoint_not_same_origin", (
        f"empty/missing URL must surface the typed code; got: {out['so_empty_code']!r}"
    )


@needs_node
def test_200_non_json_yields_invalid_json_typed_code(js_text):
    """NIT-4. A 200 with a non-JSON body surfaces the `invalid_json`
    typed code — never a SyntaxError whose message embeds the bytes."""
    out = _run_review_battery(js_text)
    assert out["invalid_json_code"] == "invalid_json", (
        f"non-JSON body must yield typed invalid_json; got: {out['invalid_json_code']!r}"
    )
    # the error message must NOT carry any of the response bytes
    msg = out.get("invalid_json_msg") or ""
    assert "<html" not in msg.lower() and "secret-token" not in msg.lower(), (
        f"invalid_json error message leaked response bytes: {msg!r}"
    )
    assert msg == "invalid_json", (
        f"invalid_json message must be the literal code only; got: {msg!r}"
    )


@needs_node
def test_apply_research_response_keeps_previous_payload_with_qualifier(js_text):
    """NIT-8. A valid envelope followed by an invalid one keeps the
    previously good payload on screen (state.payload stays set) — the
    qualify-the-previous-read behaviour matches the network-error branch
    rather than contradicting ourselves in the status line."""
    out = _run_review_battery(js_text)
    assert out["nit8_accept"] is True, "first envelope must be accepted"
    assert out["nit8_state_payload_kept"] is True, (
        "after the invalid second envelope, the previous good payload must "
        "stay set (NIT-8 decision: qualifier, not clear)"
    )
    assert out["nit8_state_error_set"] is True, (
        "after the invalid second envelope, state.error must record invalid_envelope"
    )
    # The renderStatus qualifier copy must exist in source — proves the
    # qualify-the-previous-read behaviour reaches the user.
    assert "Showing the previous successful read." in js_text, (
        "renderStatus must surface the qualifier for an invalid-envelope "
        "branch that keeps the previous payload on screen"
    )
    assert "当前显示上一次成功读取的内容" in js_text, (
        "renderStatus must surface the Chinese qualifier"
    )


@needs_node
def test_next_disabled_when_page_holds_fewer_than_page_limit(js_text):
    """NIT-9. isFinalPage(section, pageLimit) returns true when the current
    page holds fewer rows than the page limit, false otherwise. The
    runtime wires this directly into the Next button's disabled state."""
    out = _run_review_battery(js_text)
    assert out["next_full"] is False, "full page (rows == PAGE_LIMIT) must NOT be final"
    assert out["next_partial"] is True, "partial page (rows < PAGE_LIMIT) MUST be final"
    assert out["next_empty"] is True, "empty page (rows == 0) MUST be final"
    assert out["next_missing"] is True, "missing section MUST be final"


# ---------------------------------------------------------------------------
# Helpers — node battery inputs the contract tests share
# ---------------------------------------------------------------------------

_REVIEW_HARNESS = r"""
%(contract)s

var cases = JSON.parse(process.argv[2]);
var results = {};

/* optionLabelsFor under node */
results.opt_en = optionLabelsFor('en');
results.opt_zh = optionLabelsFor('zh');

/* limitationsModel under node */
results.lim_ready = limitationsModel({
  limitations: { status: 'ready', entries: ['paid data ends at fiscal Q3'] },
  authorized_coverage: { status: 'ready' }
});
results.lim_unavailable = limitationsModel({
  limitations: { status: 'unavailable' },
  authorized_coverage: { status: 'ready' }
});
results.lim_empty = limitationsModel({
  limitations: { status: 'ready', entries: [] },
  authorized_coverage: { status: 'degraded' }
});
results.lim_null = limitationsModel(null);

/* classifyFetchStatus under node */
results.cls_401 = classifyFetchStatus(401);
results.cls_402 = classifyFetchStatus(402);
results.cls_403 = classifyFetchStatus(403);
results.cls_409 = classifyFetchStatus(409);
results.cls_200 = classifyFetchStatus(200);
results.cls_500 = classifyFetchStatus(500);

/* resolveSameOrigin under node — exercise the same-origin guard directly. */
var HOME = 'http://example.test';
try {
  /* Strict-mode-safe stub: globalThis.location is writable on Node 18+ and
   * provides the canonical same-origin baseline the guard checks against. */
  if (typeof globalThis.location === 'undefined') {
    globalThis.location = { origin: HOME };
  }
  var okSame = resolveSameOrigin('/api/themes/v1/research/query');
  var cross = resolveSameOrigin('https://attacker.test/exfil');
  var empty = resolveSameOrigin('');
  results.so_ok = (okSame.ok === true && typeof okSame.url === 'string');
  results.so_cross_origin = (cross.ok === true);
  results.so_cross_code = cross.code;
  results.so_empty_code = empty.code;
} catch (e) {
  results.so_error = String(e);
}

/* NIT-4: a 200 with a non-JSON body surfaces the typed `invalid_json`
 * code — never a SyntaxError whose message embeds the response bytes.
 * The runtime delegates the typed-error construction to newInvalidJsonError
 * so the message is the literal code and the response bytes never reach
 * the user. */
var ije = newInvalidJsonError();
results.invalid_json_code = ije.code;
results.invalid_json_msg = ije.message;

/* NIT-8: a valid envelope followed by an invalid one keeps the previous
 * good payload and records invalid_envelope (qualifier, not clear). */
var sN = {epoch: 1, principalKey: 'user-A', payload: null, error: null,
          generation: null, selection: null};
applyResearchResponse(sN, 1, 'user-A', cases.valid);
results.nit8_accept = (sN.payload === cases.valid && sN.error === null);
applyResearchResponse(sN, 1, 'user-A', {surprise_key: 'breaks the closed key set'});
results.nit8_state_payload_kept = (sN.payload === cases.valid);
results.nit8_state_error_set = (sN.error && sN.error.code === 'invalid_envelope');

/* NIT-9: isFinalPage on full / partial / empty / missing. */
results.next_full = isFinalPage({rows: new Array(20).fill({})}, 20);
results.next_partial = isFinalPage({rows: new Array(7).fill({})}, 20);
results.next_empty = isFinalPage({rows: []}, 20);
results.next_missing = isFinalPage(null, 20);

/* f. parseStoredSelection under node. */
results.stored_valid = parseStoredSelection(JSON.stringify({
  slice_key: 'hbm_packaging', view: 'composition', time_mode: 'latest'
}));
results.stored_payload = parseStoredSelection(JSON.stringify({
  generation: 'g1', schema: 'semiconductor_theme_research.v1'
}));
results.stored_token = parseStoredSelection(JSON.stringify({
  access_token: 'eyJabc.def.ghi', refresh_token: 'rt'
}));
results.stored_extra_key = parseStoredSelection(JSON.stringify({
  slice_key: 'hbm_packaging', view: 'composition', time_mode: 'latest',
  note: 'something else crept in'
}));
results.stored_bad_view = parseStoredSelection(JSON.stringify({
  slice_key: 'hbm_packaging', view: 'not-a-real-view', time_mode: 'latest'
}));
results.stored_bad_mode = parseStoredSelection(JSON.stringify({
  slice_key: 'hbm_packaging', view: 'composition', time_mode: 'definitely-not-closed'
}));
results.stored_garbage = parseStoredSelection('not even json {');

console.log(JSON.stringify(results));
"""


def _run_review_battery(js_text: str) -> dict:
    assert shutil.which("node"), "node not on PATH"
    src = _REVIEW_HARNESS % {"contract": _contract(js_text)}
    cases = {"valid": _envelope(), "bad": _bad_payloads()}
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "theme_research_review.js"
        path.write_text(src, encoding="utf-8")
        run = subprocess.run(
            [shutil.which("node"), str(path), json.dumps(cases)],
            capture_output=True, text=True, timeout=60,
        )
    assert run.returncode == 0, f"node exited {run.returncode}:\n{run.stderr}\n{run.stdout}"
    assert run.stdout.strip(), f"no stdout; stderr:\n{run.stderr}"
    return json.loads(run.stdout.strip().splitlines()[-1])


# ─────────────────────────────────────────────────────────────────────────────
# Second-review fixes (seat): closed bilingual error codes, fetch hardening,
# limitations/coverage wiring pinned at source level.
# ─────────────────────────────────────────────────────────────────────────────

def _fn_body(js_text: str, name: str) -> str:
    start = js_text.index(f"function {name}(")
    nxt = re.search(r"\n  function [A-Za-z_]+\(", js_text[start + 1:])
    return js_text[start:start + 1 + (nxt.start() if nxt else len(js_text))]


def _errcode_map(js_text: str) -> dict:
    block = re.search(r"errcode:\s*\{(.*?)\n    \}", js_text, re.S).group(1)
    return dict(re.findall(r"([a-z_]+):\s*\['([^']*)',\s*'([^']*)'\]", block) and
                [(k, (en, zh)) for k, en, zh in re.findall(r"([a-z_]+):\s*\['([^']*)',\s*'([^']*)'\]", block)])


def test_every_error_code_the_client_can_raise_is_in_the_closed_bilingual_map(js_text):
    codes = _errcode_map(js_text)
    assert set(codes) >= {"endpoint_not_same_origin", "cross_origin_redirect", "invalid_content_type",
                          "invalid_json", "invalid_envelope", "body_too_large", "request_failed"}
    for key, (en, zh) in codes.items():
        assert not re.search(r"[一-鿿]", en), (key, en)
        assert re.search(r"[一-鿿]", zh), (key, zh)
        assert "_" not in en and "_" not in zh, f"{key}: slug leaked into copy"
    raised = set(re.findall(r"typedError\('([a-z_]+)'\)", js_text))
    raised |= set(re.findall(r"errorText\s*=\s*'([a-z_]+)'", js_text))
    raised |= set(re.findall(r"errorWord\('([a-z_]+)'\)", js_text))
    raised |= set(re.findall(r"\.code\s*=\s*'([a-z_]+)'", js_text))
    assert raised and raised <= set(codes), raised - set(codes)
    assert "return (typeof code === 'string' && Object.prototype.hasOwnProperty.call(L.errcode, code)) ? code : 'request_failed';" in js_text


def test_error_codes_never_reach_the_dom_raw(js_text):
    """No error string is written as textContent; every visible failure goes
    through errorWord() → pair(L.errcode) → t(), and a server action string or
    err.message is never a render input."""
    assert not re.search(r"textContent\s*=\s*(textSafe\()?\s*(ui\.errorText|err\.(code|message))", js_text)
    assert "err.message" not in js_text
    assert "'request failed'" not in js_text
    assert not re.search(r"throw new Error\(\(?err", js_text)
    assert "error.action" not in js_text and ".action ||" not in js_text
    assert js_text.count("errorWord(") >= 3


def test_render_limitations_is_wired_and_always_emits_the_coverage_caveat(js_text):
    assert "renderLimitations();" in _fn_body(js_text, "renderAll")
    body = _fn_body(js_text, "renderLimitations")
    assert "pair(L.status, covStatus" in body
    assert "覆盖范围" in body and "Coverage" in body
    assert "限制" in body and "Limitations" in body


def test_fetch_calls_are_same_origin_and_refuse_redirect_content_type_and_size(js_text):
    fetches = re.findall(r"fetch\((?:queryUrl|evidenceUrl), \{(.*?)\}\);", js_text, re.S)
    assert len(fetches) == 2
    for block in fetches:
        assert "credentials: 'same-origin'" in block and "method: 'POST'" in block
    assert js_text.count("refuseCrossOriginRedirect(resp);") == 2
    assert js_text.count("return readJsonBody(resp);") == 2
    assert re.search(r"var MAX_BODY_BYTES = \d+;", js_text)
    body = _fn_body(js_text, "readJsonBody")
    assert "typedError('invalid_content_type')" in body and "typedError('body_too_large')" in body
    assert "JSON.parse(text)" in body and "newInvalidJsonError()" in body
    assert "resp.json().catch(function () { throw newInvalidJsonError(); })" not in js_text
    redirect = _fn_body(js_text, "refuseCrossOriginRedirect")
    assert "resp.redirected" in redirect and "target.origin !== window.location.origin" in redirect


def test_chip_class_token_is_whitelisted_against_the_label_map(js_text):
    body = _fn_body(js_text, "chip")
    assert "Object.prototype.hasOwnProperty.call(L.label, kind) ? kind : 'unknown'" in body
    assert "'tr-chip tr-chip-' + known" in body
    assert "textSafe(kind)" not in body


def test_pager_never_prints_rows_one_to_zero(js_text):
    assert "var from = rowCount === 0 ? 0 : offset + 1;" in _fn_body(js_text, "renderPager")
