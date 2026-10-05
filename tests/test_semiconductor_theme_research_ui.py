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
import functools
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

JS_PATH = REPO_ROOT / "site" / "assets" / "js" / "theme-research.js"
SCHEMA_PATH = (REPO_ROOT / "contracts" / "market_ontology"
               / "semiconductor_theme_research.v1.schema.json")
CSS_PATH = REPO_ROOT / "site" / "assets" / "css" / "theme-research.css"
AGGREGATOR = "_theme_research_mounts.html.j2"
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

# A COMPOSED RESPONSE, deliberately outside the composer's input-case corpus
# (`tests/fixtures/semiconductor_theme_research/`, whose roster law pins that
# directory to exactly the twenty-eight named input cases). This is the
# composer's OUTPUT, pinned by the composition suite.
ENVELOPE_FIXTURE = (REPO_ROOT / "tests" / "fixtures" / "theme_research_client"
                    / "composed_envelope.json")


@functools.lru_cache(maxsize=1)
def _composed_envelope_text() -> str:
    """The REAL composer's envelope for the synthetic ``witness_hbm_packaging``
    case (economics ready, industrial rows, evidence refs), read from the
    committed fixture.

    It is READ, not composed here, on purpose. This suite tests a JavaScript
    file: importing the composer would drag the whole company-intelligence
    stack (requests, pandas, pyarrow, the reader, the intake) into its import
    closure, and every CI job that declares this suite would then have to
    declare that closure too. ``test_client_contract_envelope_fixture_is_the
    _composer_output`` in the composition suite — where those imports already
    live — pins the fixture to what the composer produces today, so the
    fixture cannot drift back into a hand-written look-alike. Cached as text
    so every test gets a fresh deep copy.
    """
    return json.dumps(json.loads(ENVELOPE_FIXTURE.read_text(encoding="utf-8")), sort_keys=True)


def _envelope(**over) -> dict:
    """The frozen-schema envelope the client must accept — the composer's own
    output. The T10 client was first accepted against a hand-written
    look-alike that had drifted from the schema (``limitations`` and
    ``native_subjects`` as status objects, a top-level ``industrial_views``
    status, string evidence refs); under node the production client refused
    every real response. The valid case is therefore never hand-written."""
    body = json.loads(_composed_envelope_text())
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

    # The shapes the first client accepted and the schema forbids: each must
    # now be refused as invalid_envelope.
    body = _envelope()
    body["native_subjects"] = {"status": "ready", "subjects": []}
    bad.append({"name": "native_subjects_object_not_array", "payload": body})

    body = _envelope()
    body["limitations"] = {"status": "ready", "entries": ["drifted shape"]}
    bad.append({"name": "limitations_object_not_array", "payload": body})

    body = _envelope()
    body["limitations"] = ["ok_token", 7]
    bad.append({"name": "limitations_non_string_entry", "payload": body})

    body = _envelope()
    body["limitations"] = [""]
    bad.append({"name": "limitations_empty_string_entry", "payload": body})

    body = _envelope()
    body["industrial_views"].pop("economics")
    bad.append({"name": "industrial_views_missing_view", "payload": body})

    body = _envelope()
    body["industrial_views"]["status"] = "ready"
    bad.append({"name": "industrial_views_top_level_status", "payload": body})

    body = _envelope()
    body["industrial_views"]["composition"]["status"] = "ok"
    bad.append({"name": "industrial_view_status_bad", "payload": body})

    body = _envelope()
    body["economics"].pop("witness_gate")
    bad.append({"name": "economics_missing_witness_gate", "payload": body})

    body = _envelope()
    body["economics"]["management"] = "ready"
    bad.append({"name": "economics_management_not_object", "payload": body})

    body = _envelope()
    body["evidence_refs"] = {"status": "ready"}
    bad.append({"name": "evidence_refs_object_not_array", "payload": body})

    # The frozen contract pins three expectation buckets to `unavailable`.
    body = _envelope()
    body["expectations"]["external_consensus"]["status"] = "ready"
    bad.append({"name": "expectations_consensus_claims_ready", "payload": body})

    body = _envelope()
    body["expectations"]["market_incorporation"]["status"] = "degraded"
    bad.append({"name": "expectations_incorporation_claims_degraded", "payload": body})

    # The management assessment's OWN authority block, attached to the only
    # paid figures on the page.
    body = _envelope()
    body["economics"]["management"]["authority"]["can_rank"] = True
    bad.append({"name": "management_authority_claims_rank", "payload": body})

    body = _envelope()
    del body["economics"]["management"]["authority"]["can_open_entry"]
    bad.append({"name": "management_authority_flag_missing", "payload": body})

    body = _envelope()
    body["economics"]["management"]["authority"] = None
    bad.append({"name": "management_authority_absent", "payload": body})

    body = _envelope()
    body["economics"]["management"]["authority"]["can_execute"] = False
    bad.append({"name": "management_authority_extra_flag", "payload": body})

    body = _envelope()
    body["authority"]["can_execute"] = False
    bad.append({"name": "authority_extra_flag", "payload": body})

    # The management block's own frozen identity.
    body = _envelope()
    body["economics"]["management"]["schema"] = "management_sequence_assessment.v2"
    bad.append({"name": "management_schema_not_the_accepted_assessment", "payload": body})

    body = _envelope()
    del body["economics"]["management"]["schema"]
    bad.append({"name": "management_schema_missing", "payload": body})
    return bad


# ---------------------------------------------------------------------------
# Node harness — executes the extracted contract block
# ---------------------------------------------------------------------------

_HARNESS = r"""
%(contract)s

var results = {};
var cases = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));

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
  (sC.payload === cases.valid && sC.generation === cases.valid.generation && sC.error === null);

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
        # The cases go through a FILE, never argv: the valid case is the real
        # composer envelope (~25 KB) and the battery carries one per rejection
        # case, which overran the platform's ~1 MB argument ceiling and
        # surfaced as an opaque node `RangeError: Maximum call stack size
        # exceeded` with no stack — a limit that would only ever bite as the
        # contract grows.
        cases_path = Path(td) / "cases.json"
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        run = subprocess.run(
            [shutil.which("node"), str(path), str(cases_path)],
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
    """The Theme Tracker page rendered from a synthetic root that CARRIES the
    registered anchor as a theme row.

    Shared hook 2: the page mounts a vertical only where its anchor is already
    a row on the board, and the section markup now lives in its own partial, so
    the synthetic root needs both (the tracker suite's fixed support-partial
    list is not this suite's to edit). The live board carries the row — it is
    the first of the eighteen in site/neuralwebdata/theme_state.json."""
    import json  # noqa: PLC0415
    from tests.test_state_of_themes import _make_sot_root
    import scripts.build_state_of_themes as sot
    root = _make_sot_root(tmp_path)
    state = root / "site" / "neuralwebdata" / "theme_state.json"
    document = json.loads(state.read_text(encoding="utf-8"))
    document["themes"][0] = {**document["themes"][0], "theme_id": "ai_semiconductors"}
    state.write_text(json.dumps(document), encoding="utf-8")
    for partial in ("_theme_research_section.html.j2", "_theme_research_mounts.html.j2"):
        source = TPL_PATH.parent / partial
        if source.exists():
            (root / "templates" / partial).write_bytes(source.read_bytes())
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
    assert html.count('<script defer src="assets/js/theme-research.js?v=20260924b"></script>') == 1
    # includes sit immediately after their canonical siblings
    assert '<link rel="stylesheet" href="theme.css">\n<link rel="stylesheet" href="assets/css/theme-research.css">' in html
    assert '<script src="theme.js"></script>\n<script defer src="assets/js/theme-research.js?v=20260924b"></script>' in html


def test_template_source_mounts_through_the_shared_partial():
    """The page no longer carries its own copy of one vertical's mount.

    Shared hook 2: the markup and every string in it come from
    _theme_research_section.html.j2 driven by the registration, so the page
    source must hold the loop-and-include exactly once and the mount literal
    not at all. The position is unchanged — still inside the lanes branch,
    immediately before the disclosure."""
    tpl = TPL_PATH.read_text(encoding="utf-8")
    include = '{%% include "%s" ignore missing %%}' % AGGREGATOR
    assert tpl.count(include) == 1, "the page must mount through the aggregator, once"
    assert tpl.index(include) < tpl.index('<p class="sot-disclosure">')
    assert "data-theme-research-mount" not in tpl, (
        "the mount literal belongs to the section partial, not to this page"
    )
    # The per-vertical loop lives in the aggregator, never inline on this page.
    # This page's LAST `endfor` is the lanes loop, and
    # tests/test_finance_entry_points.py locates that loop with rfind, so an
    # inline loop here moves their anchor past the finance include and fails
    # their ordering guard while the invariant it protects still holds.
    assert "tr_mount" not in tpl, (
        "the per-vertical loop belongs to the aggregator: an inline loop here "
        "moves the last `endfor` and breaks test_finance_entry_points' anchor"
    )
    assert tpl.rfind("{% endfor %}") < tpl.index(include), (
        "the last `endfor` on this page must precede the aggregator include"
    )
    agg = (TPL_PATH.parent / AGGREGATOR).read_text(encoding="utf-8")
    loop = ('{% for tr_mount in theme_research_mounts or [] %}'
            '{% include "_theme_research_section.html.j2" ignore missing %}{% endfor %}')
    assert agg.count(loop) == 1, "the aggregator must own the loop, exactly once"
    assert "data-theme-research-mount" not in agg, (
        "the mount literal belongs to the section partial, not to the aggregator"
    )
    # ALL NINE registration strings, not a sample. An independent review
    # re-inserted the vertical's bilingual title and both schema ids above the
    # loop and every test stayed green, because only the anchor and one slice
    # key were forbidden here — while the partial suite forbade all nine.
    mount = _mount_attrs()
    forbidden = {
        "anchor": mount["anchor"], "schema": mount["schema"],
        "evidence_schema": mount["evidenceSchema"],
    }
    for slice_key in mount["slices"].split(","):
        forbidden[f"slice:{slice_key}"] = slice_key
    for key, pair in json.loads(mount["labels"]).items():
        forbidden[f"label_en:{key}"], forbidden[f"label_zh:{key}"] = pair[0], pair[1]
    from engine.market_ontology.theme_research_mounts import mount_context  # noqa: PLC0415

    registration = mount_context(mount["anchor"])
    for key in ("title_en", "title_zh", "note_en", "note_zh"):
        forbidden[key] = registration[key]
    leaked = sorted(name for name, value in forbidden.items() if value in tpl)
    assert not leaked, f"the page hard-pins registration strings again: {leaked}"


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
    unavailable = out["lim_unavailable"]
    assert unavailable["limitations"] is None and unavailable["limitationsStatus"] == "unavailable", (
        f"the drifted object shape must yield null entries + 'unavailable'; got: {unavailable}"
    )
    empty = out["lim_empty"]
    assert empty["limitations"] == [] and empty["limitationsStatus"] == "ready", (
        f"an empty limitations array is a valid, empty read; got: {empty}"
    )
    for label, model in (("lim_unavailable", unavailable), ("lim_empty", empty)):
        assert model is not None, f"{label}: limitationsModel not executed under node"
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

var cases = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
var results = {};

/* optionLabelsFor under node */
results.opt_en = optionLabelsFor('en');
results.opt_zh = optionLabelsFor('zh');

/* POSITIVE CONTROL for the closed label maps (see labelMapsSelfTest) */
results.label_self_test = labelMapsSelfTest();
results.label_real = {
  status_ready: pair(L.status, 'ready'),
  view_economics: pair(L.view, 'economics'),
  chip_fact: pair(L.label, 'fact'),
  econ_role: pair(TR_ECON_LABELS.role, 'prior_outlook'),
  errcode: pair(L.errcode, 'invalid_envelope')
};
results.bi_matches_pair = {
  known: _bi(L.status, 'ready'),
  unknown: _bi(L.status, 'no_such_status'),
  proto: _bi(L.status, '__proto__'),
  absent_null: _bi(L.status, null),
  absent_undefined: _bi(L.status, undefined),
  null_map: _bi(null, 'ready'),
  econ_unit: _bi(TR_ECON_LABELS.unit, 'usd_billions')
};
results.pair_null_map = pair(null, 'ready');
results.label_fallback = {
  unknown: pair(L.status, 'no_such_status'),
  proto: pair(L.status, '__proto__'),
  ctor: pair(L.label, 'constructor'),
  wrong_shape: pair({k: 'a bare string'}, 'k'),
  three_long: pair({k: ['a', 'b', 'c']}, 'k')
};

/* limitationsModel under node */
results.lim_ready = limitationsModel({
  limitations: ['omitted:private_assertions_unbound', 'witness_economics_missing'],
  authorized_coverage: { status: 'ready' }
});
results.lim_unavailable = limitationsModel({
  limitations: { status: 'ready', entries: ['the drifted object shape'] },
  authorized_coverage: { status: 'ready' }
});
results.lim_empty = limitationsModel({
  limitations: [],
  authorized_coverage: { status: 'degraded' }
});
results.lim_null = limitationsModel(null);
results.lim_real = limitationsModel(cases.valid);

/* economicsModel: the management triple as rows (real composer envelope) */
results.econ = economicsModel(cases.valid);
results.econ_null = economicsModel(null);
results.econ_unavailable = economicsModel({economics: {status: 'unavailable', reason: 'management_sequence_missing',
  input_refs: [], management: null, witness_gate: 'missing'}});
results.econ_unmapped = economicsModel({economics: {status: 'ready', input_refs: ['e1'], witness_gate: 'positive',
  management: {roles: {prior_outlook: {metric: 'constructor', low: 1, high: 2, unit: 'toString', horizon: '2026Q2', status: 'invented'},
                       actual: {metric: 'revenue', value: '<b>3</b>', unit: 'usd_billions', fiscal_period: '2026Q2', basis: 'hasOwnProperty'},
                       new_outlook: null},
               comparisons: {prior_vs_actual: {status: 'refused', reason: 'range_missing', position: null}}}}});

/* viewRowModel on the real composition rows + evidenceRefsModel */
results.view_rows = cases.valid.industrial_views.composition.rows.map(viewRowModel);
results.view_row_scalar = viewRowModel('<i>plain</i>');
results.evidence = evidenceRefsModel(cases.valid);
results.evidence_mixed = evidenceRefsModel({evidence_refs: [
  {kind: 'assertion', assertion_ref: 'gmi-curation://ai_semiconductors/gmirca_' + 'a'.repeat(32), curation_revision: 'gmirca_' + 'a'.repeat(32)},
  {kind: 'native', owner_store: 'earnings', native_identity: {}, reference_id: 'evt_x'},
  'a bare string is not a ref', {kind: 'assertion'}, null
]});

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
        # The cases go through a FILE, never argv: the valid case is the real
        # composer envelope (~25 KB) and the battery carries one per rejection
        # case, which overran the platform's ~1 MB argument ceiling and
        # surfaced as an opaque node `RangeError: Maximum call stack size
        # exceeded` with no stack — a limit that would only ever bite as the
        # contract grows.
        cases_path = Path(td) / "cases.json"
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        run = subprocess.run(
            [shutil.which("node"), str(path), str(cases_path)],
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


# ─────────────────────────────────────────────────────────────────────────────
# T10g — the client contract is the FROZEN v1 schema, and the economics pane
# renders the management triple. Discovered at the seat (2026-09-24): under
# node the production client refused the real composer envelope
# ("section native_subjects is missing or not an object") because the suite's
# hand-written valid case had drifted from the schema.
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_case_is_the_real_composer_output_and_validates_against_the_frozen_schema():
    import jsonschema  # noqa: PLC0415
    assert ENVELOPE_FIXTURE.is_file(), "the pinned composer envelope is missing"
    payload = _envelope()
    jsonschema.validate(payload, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    assert isinstance(payload["limitations"], list)
    assert isinstance(payload["native_subjects"], list)
    assert set(payload["industrial_views"]) == {"composition", "manufacturing", "commercial", "capacity", "economics"}
    assert payload["economics"]["status"] == "ready" and payload["economics"]["management"] is not None
    assert all(isinstance(ref, dict) for ref in payload["evidence_refs"])


@needs_node
def test_drifted_shapes_are_rejected_and_the_real_envelope_is_accepted(js_text):
    out = _run_battery(js_text)
    assert out["validate_ok"] is True and out["accept"] is True
    for name in ("native_subjects_object_not_array", "limitations_object_not_array",
                 "limitations_non_string_entry", "limitations_empty_string_entry",
                 "industrial_views_missing_view", "industrial_views_top_level_status",
                 "industrial_view_status_bad", "economics_missing_witness_gate",
                 "economics_management_not_object", "evidence_refs_object_not_array"):
        assert out["rejects"][name] is True, name


@needs_node
def test_limitations_model_reads_the_real_string_array(js_text):
    out = _run_review_battery(js_text)
    real = out["lim_real"]
    assert real["limitationsStatus"] == "ready" and isinstance(real["limitations"], list)
    assert real["coverageStatus"] in ("ready", "degraded", "unavailable", "refused")


def _js_num(value) -> str:
    """How node's ``String(n)`` spells a JSON number the composer emitted as a
    Python float (``15.0`` → ``"15"``): the client never reformats figures, so
    the test must not expect Python's spelling."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@needs_node
def test_economics_model_yields_the_management_triple_rows_bilingually(js_text):
    """W-A/W-B visible result: prior outlook, reported actual, new outlook,
    the prior-vs-actual comparison and the witness gate, each with an EN and
    a ZH reading; figures pass through as text (no arithmetic)."""
    out = _run_review_battery(js_text)
    econ = out["econ"]
    assert econ["status"] == "ready" and econ["witnessGate"] == "positive"
    roles = [row["role"] for row in econ["rows"]]
    assert roles == ["prior_outlook", "actual", "new_outlook", "prior_vs_actual", "witness_gate"]
    payload = _envelope()
    mgmt = payload["economics"]["management"]
    actual_row = next(row for row in econ["rows"] if row["role"] == "actual")
    assert _js_num(mgmt["roles"]["actual"]["value"]) in actual_row["value"][0]
    assert _js_num(mgmt["roles"]["actual"]["value"]) in actual_row["value"][1]
    prior_row = econ["rows"][0]
    assert _js_num(mgmt["roles"]["prior_outlook"]["low"]) in prior_row["value"][0]
    assert _js_num(mgmt["roles"]["prior_outlook"]["high"]) in prior_row["value"][0]
    assert mgmt["roles"]["prior_outlook"]["horizon"] in prior_row["note"][0]
    # The synthetic fixture's metric/unit slugs (``revenue_usd_bn`` /
    # ``USD_bn``) are NOT the owner vocabulary the client maps (``revenue`` /
    # ``usd_billions``, the reader's guidance-history grammar): they render the
    # typed 'Unmapped label' pair, never the raw slug. The served W-A/W-B
    # payload (real vocabulary) is rendered under node by the served proof.
    for slug in (mgmt["roles"]["prior_outlook"]["metric"], mgmt["roles"]["prior_outlook"]["unit"]):
        if slug not in ("revenue", "usd_billions", "usd_millions"):
            assert slug not in prior_row["value"][0] and "Unmapped label" in prior_row["value"][0]
    for row in econ["rows"]:
        assert isinstance(row["value"], list) and len(row["value"]) == 2
        assert isinstance(row["note"], list) and len(row["note"]) == 2
        assert row["value"][0] and row["value"][1], row
        assert re.search(r"[一-鿿]", row["value"][1]) or row["value"][0] == row["value"][1], row
        for text in row["value"] + row["note"]:
            for token in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry",
                          "rank", "entry", "size"):
                assert token not in text.lower().split(), (token, text)
    assert econ["inputRefs"] == payload["economics"]["input_refs"]
    assert out["econ_null"]["rows"] is None
    assert out["econ_unavailable"]["rows"] is None and out["econ_unavailable"]["status"] == "unavailable"


@needs_node
def test_economics_model_never_renders_raw_slugs_or_prototype_keys(js_text):
    """Unknown metric/unit/basis/status tokens (including prototype-key names
    and markup) render the typed 'Unmapped label' pair; a null role is
    skipped; the actual figure is literal text."""
    out = _run_review_battery(js_text)
    econ = out["econ_unmapped"]
    roles = [row["role"] for row in econ["rows"]]
    assert roles == ["prior_outlook", "actual", "prior_vs_actual", "witness_gate"]
    prior = econ["rows"][0]
    assert "Unmapped label" in prior["value"][0] and "constructor" not in prior["value"][0]
    assert "toString" not in prior["value"][0] and "invented" not in prior["note"][0]
    actual = econ["rows"][1]
    assert "<b>3</b>" in actual["value"][0] and "hasOwnProperty" not in actual["note"][0]
    cmp = econ["rows"][2]
    assert cmp["value"][0].startswith("Comparison refused") and "range missing" in cmp["note"][0]


@needs_node
def test_view_row_model_maps_frozen_industrial_rows_to_cells(js_text):
    out = _run_review_battery(js_text)
    rows = out["view_rows"]
    assert rows, "the fixture composition view has rows"
    source_rows = _envelope()["industrial_views"]["composition"]["rows"]
    for cell, raw in zip(rows, source_rows):
        assert set(cell) == {"label_kind", "label", "value", "note"}
        assert cell["label"], raw
        assert cell["label_kind"] in (None, "fact", "target")
        if raw["statement_mode"] == "REPORTED_FACT":
            assert cell["label_kind"] == "fact"
        assert raw["assertion_ref"] not in cell["label"]  # refs are receipts, not labels
        if raw["source_business_label"]:
            assert raw["source_business_label"] in cell["note"]
    scalar = out["view_row_scalar"]
    assert scalar["label"] == "<i>plain</i>" and scalar["label_kind"] is None


@needs_node
def test_evidence_refs_model_separates_assertion_and_native_refs(js_text):
    out = _run_review_battery(js_text)
    real = out["evidence"]
    source = _envelope()["evidence_refs"]
    assert len(real) == len(source)
    for entry, raw in zip(real, source):
        if raw["kind"] == "assertion":
            assert entry["ref"] == raw["assertion_ref"] and entry["label"] == raw["curation_revision"]
        else:
            assert entry["ref"] is None and entry["label"] == raw["reference_id"]
    mixed = out["evidence_mixed"]
    assert [e["kind"] for e in mixed] == ["assertion", "native"]
    assert mixed[1]["ref"] is None and mixed[1]["label"] == "evt_x"


def test_render_table_prefers_the_management_triple_for_the_economics_view(js_text):
    body = js_text[js_text.index("function renderTable()"):js_text.index("function appendStatusRow(")]
    assert "economicsModel(state.payload)" in body
    assert "appendEconomicsRow" in body and "appendIndustrialRow" in body
    assert "viewRowModel(" in js_text[js_text.index("function appendIndustrialRow"):js_text.index("function renderTable()")]
    evidence = js_text[js_text.index("function renderEvidence()"):js_text.index("function renderPager()")]
    assert "evidenceRefsModel(state.payload)" in evidence
    assert "String(ref)" not in evidence


@needs_node
def test_every_closed_label_map_entry_resolves_to_its_own_label(js_text):
    """POSITIVE CONTROL. Every key of every closed bilingual map must resolve
    through `pair` to its own entry — never to the typed unmapped fallback.

    Found at the seat on 2026-09-24: the lookup guard read
    `!Array.isArray(entry)` while every entry IS a two-string array, so EVERY
    label on the page — status words, view tabs, slice tabs, chips, time-basis
    options, error lines and the economics role labels — rendered
    'Unmapped label / 未映射标签'. The suite stayed green because `pair` and
    the maps sat outside the node-executed contract block and were only ever
    checked by source-substring assertions. Both now live inside it.
    """
    out = _run_review_battery(js_text)
    assert out["label_self_test"] == [], (
        "these label-map keys fall back instead of resolving: "
        + ", ".join(out["label_self_test"])
    )
    real = out["label_real"]
    assert real["status_ready"] == ["Ready", "就绪"]
    assert real["view_economics"] == ["Economics", "经济性"]
    assert real["chip_fact"] == ["Fact", "事实"]
    assert real["econ_role"] == ["Prior outlook", "此前展望"]
    assert real["errcode"][0].startswith("The server reply did not match")
    for key, got in real.items():
        assert got[0] != "Unmapped label" and got[1] != "未映射标签", key


@needs_node
def test_unknown_and_hostile_label_keys_still_yield_the_typed_fallback(js_text):
    """The repair must not open the prototype or accept a foreign entry
    shape: unknown keys, prototype keys and non-tuple entries all resolve to
    the typed bilingual fallback."""
    out = _run_review_battery(js_text)
    for name, got in out["label_fallback"].items():
        assert got == ["Unmapped label", "未映射标签"], (name, got)


def test_label_maps_and_lookup_live_inside_the_node_executed_contract(js_text):
    """Structural guard for the blind spot above: if the maps or the lookup
    drift back outside the contract block, no node battery can reach them."""
    contract = _contract(js_text)
    for needle in ("var L = {", "function pair(map, key)", "function labelMapsSelfTest()",
                   "var TR_ECON_LABELS = {"):
        assert needle in contract, f"{needle} must stay inside the contract block"


@needs_node
def test_expectation_buckets_pinned_to_unavailable_and_nested_authority_refused(js_text):
    """The three non-management expectation buckets are `const: unavailable`
    in the frozen contract, and the management assessment carries its own
    authority block over the paid figures."""
    out = _run_battery(js_text)
    for name in ("expectations_consensus_claims_ready", "expectations_incorporation_claims_degraded",
                 "management_authority_claims_rank", "management_authority_flag_missing",
                 "management_authority_absent"):
        assert out["rejects"][name] is True, name
    assert out["validate_ok"] is True and out["accept"] is True


@needs_node
def test_the_economics_lookup_is_the_same_lookup_and_the_control_walks_both(js_text):
    """The economics maps resolve through `_bi`, not `pair`. While `_bi` was a
    second, laxer implementation, a defect in it was invisible to the label
    positive control: the review of the blocker fix reproduced the old
    `!Array.isArray` bug in `_bi` alone and the self-test still came back
    clean while every served figure read "Unmapped label". `_bi` now
    delegates, and the control walks both names and compares them."""
    contract = _contract(js_text)
    body = contract[contract.index("function _bi(map, key)"):]
    body = body[:body.index("\n  }")]
    assert "return pair(map, key);" in body, "the economics lookup must delegate"
    assert "Array.isArray" not in body and "hasOwnProperty" not in body, (
        "a second lookup implementation is what this fix removed"
    )
    control = contract[contract.index("function labelMapsSelfTest()"):]
    assert "_bi(map, keys[j])" in control, "the control must walk the economics lookup too"

    out = _run_review_battery(js_text)
    bi = out["bi_matches_pair"]
    assert bi["known"] == ["Ready", "就绪"]
    assert bi["econ_unit"] == ["US$ bn", "十亿美元"]
    for name in ("unknown", "proto", "null_map"):
        assert bi[name] == ["Unmapped label", "未映射标签"], name
    # An ABSENT field renders as nothing — the one case the economics lookup
    # adds, and the only difference between the two names.
    assert bi["absent_null"] == ["", ""] and bi["absent_undefined"] == ["", ""]
    assert out["pair_null_map"] == ["Unmapped label", "未映射标签"]


@needs_node
def test_management_schema_and_closed_authority_are_refused_when_wrong(js_text):
    """The management block carries the only paid figures: its frozen schema
    id is checked, and neither authority block may carry a flag this client
    cannot evaluate (the contract closes both objects)."""
    out = _run_battery(js_text)
    for name in ("management_schema_not_the_accepted_assessment", "management_schema_missing",
                 "management_authority_extra_flag", "authority_extra_flag"):
        assert out["rejects"][name] is True, name
    assert out["validate_ok"] is True and out["accept"] is True


def _code_only(js_text: str) -> str:
    """The file with block and line comments removed, so a scan reads code."""
    out = re.sub(r"/\*.*?\*/", " ", js_text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", out)


def test_no_bare_label_map_read_survives_in_the_render_path(js_text):
    """Every label lookup goes through the closed helpers. A bare `map[key]`
    read is truthy for prototype keys (`status: "constructor"` wrote payload
    text into a class name) and its miss branch rendered a raw internal slug
    in one language only."""
    code = _code_only(js_text)
    for bare in ("L.status[", "L.label[", "L.view[", "L.slice[", "L.expectation[",
                 "L.errcode[", "TR_ECON_LABELS.role[", "TR_ECON_LABELS.metric["):
        assert bare not in code, f"bare map read survives: {bare}"


# ---------------------------------------------------------------------------
# 12. Shared hook 4a — the contract applied to a MOUNT's spec, not to
#     constants compiled into this file. One anchor, one slice vocabulary and
#     one schema id were baked in; a second vertical mounting the same client
#     needs the same laws applied to ITS registration.
# ---------------------------------------------------------------------------

_MOUNT_HARNESS = r"""
%(contract)s

var cases = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
var out = {spec: null, specReject: {}, envelope: {}, evidence: {}, stored: {}, apply: {}};

var built = mountSpecFrom(cases.attrs);
out.spec = built.ok ? {ok: true, spec: built.spec} : {ok: false, reason: built.reason};
var spec = built.ok ? built.spec : null;

cases.badAttrs.forEach(function (c) {
  var r = mountSpecFrom(c.attrs);
  out.specReject[c.name] = r.ok ? 'ACCEPTED' : r.reason;
});

cases.envelopeCases.forEach(function (c) {
  var useSpec = c.spec ? c.spec : spec;
  out.envelope[c.name] = validateEnvelopeFor(useSpec, c.payload, c.expected).reason;
});

cases.evidenceCases.forEach(function (c) {
  out.evidence[c.name] = validateEvidenceFor(spec, c.payload, c.generation).reason;
});

cases.storedCases.forEach(function (c) {
  out.stored[c.name] = parseStoredSelectionFor(spec, c.raw) === null ? null : 'restored';
});

/* The SAME law under a spec whose slice vocabulary is disjoint from the one
   compiled into this file — the only way to tell a spec-driven check from a
   constant-driven one. */
out.storedAlt = {};
if (cases.altSpec) {
  cases.storedAltCases.forEach(function (c) {
    out.storedAlt[c.name] =
      parseStoredSelectionFor(cases.altSpec, c.raw) === null ? null : 'restored';
  });
}

/* applyResearchResponseFor mirrors the epoch/principal drop laws exactly. */
var sLate = {epoch: 3, principalKey: 'user-A', payload: null, error: null, generation: null};
out.apply.late_epoch = (applyResearchResponseFor(sLate, 2, 'user-A', spec, cases.valid, cases.expected) === false
  && sLate.payload === null && sLate.error === null && sLate.generation === null);
var sPrincipal = {epoch: 3, principalKey: 'user-A', payload: null, error: null, generation: null};
out.apply.foreign_principal = (applyResearchResponseFor(sPrincipal, 3, 'user-B', spec, cases.valid, cases.expected) === false
  && sPrincipal.payload === null && sPrincipal.error === null && sPrincipal.generation === null);
var sOk = {epoch: 4, principalKey: 'user-A', payload: null, error: null, generation: null};
out.apply.accepted = (applyResearchResponseFor(sOk, 4, 'user-A', spec, cases.valid, cases.expected) === true
  && sOk.payload === cases.valid && sOk.generation === cases.valid.generation && sOk.error === null);
var sWrong = {epoch: 5, principalKey: 'user-A', payload: null, error: null, generation: null};
out.apply.wrong_mount_rejected = (applyResearchResponseFor(sWrong, 5, 'user-A', spec, cases.valid, cases.foreignExpected) === false
  && sWrong.payload === null && sWrong.generation === null
  && sWrong.error && sWrong.error.code === 'invalid_envelope');

/* A label pair is returned literally — never interpreted as markup. */
out.labels_literal = spec ? spec.labels : null;

console.log(JSON.stringify(out));
"""


def _mount_attrs() -> dict:
    """The attributes the rendered mount actually carries, from the registration.

    Read from the leaf mounts module, never retyped and never from the
    registry: importing the registry would drag the composer, the Company
    Intelligence reader and the frozen theme-graph store into this suite's CI
    closure (measured 2026-09-24: 55 files against the leaf's 2).
    """
    from engine.market_ontology.theme_research_mounts import mount_context

    mount = mount_context("ai_semiconductors")
    assert mount is not None
    return {
        "anchor": mount["anchor_theme_id"],
        "slices": mount["slices"],
        "schema": mount["schema_id"],
        "evidenceSchema": mount["evidence_schema_id"],
        "labels": mount["slice_labels_json"],
        "apiQuery": "/api/themes/v1/research/query",
        "apiEvidence": "/api/themes/v1/research/evidence",
    }


def _run_mount_battery(js_text: str) -> dict:
    assert shutil.which("node"), "node not on PATH"
    attrs = _mount_attrs()
    valid = _envelope()
    anchor, first_slice = attrs["anchor"], attrs["slices"].split(",")[0]
    other_slice = attrs["slices"].split(",")[1]
    expected = {"anchor": anchor, "slice": first_slice}

    def mutate(**changes):
        payload = _envelope()
        payload.update(changes)
        return payload

    foreign_schema_spec = {
        "anchor": anchor, "slices": attrs["slices"].split(","),
        "schema": "synthetic_theme_research.v1",
        "evidenceSchema": "synthetic_theme_research.evidence.v1",
        "labels": {}, "apiQuery": "/q", "apiEvidence": "/e",
    }
    evidence_ok = {
        "schema": attrs["evidenceSchema"], "generation": valid["generation"],
        "authority": dict(valid["authority"]),
    }
    request_other_anchor = {**valid["request"], "anchor_theme_id": "robotics_automation"}
    request_other_slice = {**valid["request"], "slice_key": "not_a_declared_slice"}

    cases = {
        "attrs": attrs,
        "valid": valid,
        "expected": expected,
        "foreignExpected": {"anchor": "robotics_automation", "slice": first_slice},
        "badAttrs": [
            {"name": "empty_schema", "attrs": {**attrs, "schema": ""}},
            {"name": "schema_equals_evidence",
             "attrs": {**attrs, "evidenceSchema": attrs["schema"]}},
            {"name": "anchor_with_dash", "attrs": {**attrs, "anchor": "ai-semiconductors"}},
            {"name": "anchor_empty", "attrs": {**attrs, "anchor": ""}},
            {"name": "duplicate_slices",
             "attrs": {**attrs, "slices": f"{first_slice},{first_slice}"}},
            {"name": "slice_with_space", "attrs": {**attrs, "slices": "hbm packaging"}},
            {"name": "labels_extra_key",
             "attrs": {**attrs, "labels": json.dumps(
                 {**json.loads(attrs["labels"]), "ghost_slice": ["G", "鬼"]})}},
            {"name": "labels_missing_slice",
             "attrs": {**attrs, "labels": json.dumps(
                 {first_slice: json.loads(attrs["labels"])[first_slice]})}},
            {"name": "label_not_pair",
             "attrs": {**attrs, "labels": json.dumps(
                 {first_slice: ["only-one"], other_slice: ["A", "乙"]})}},
            {"name": "label_half_empty",
             "attrs": {**attrs, "labels": json.dumps(
                 {first_slice: ["A", ""], other_slice: ["B", "乙"]})}},
            {"name": "labels_array", "attrs": {**attrs, "labels": "[1,2]"}},
            {"name": "labels_invalid_json", "attrs": {**attrs, "labels": "{not json"}},
            {"name": "api_query_empty", "attrs": {**attrs, "apiQuery": ""}},
            {"name": "not_an_object", "attrs": None},
        ],
        "envelopeCases": [
            {"name": "valid", "payload": valid, "expected": expected},
            {"name": "not_object", "payload": "a string", "expected": expected},
            {"name": "foreign_schema",
             "payload": mutate(schema="robotics_theme_research.v1"), "expected": expected},
            {"name": "schema_v1_1",
             "payload": mutate(schema="semiconductor_theme_research.v1.1"),
             "expected": expected},
            {"name": "schema_trailing_space",
             "payload": mutate(schema="semiconductor_theme_research.v1 "),
             "expected": expected},
            {"name": "valid_but_wrong_vertical", "spec": foreign_schema_spec,
             "payload": valid, "expected": expected},
            {"name": "other_anchor_in_request",
             "payload": mutate(request=request_other_anchor), "expected": expected},
            {"name": "slice_outside_spec",
             "payload": mutate(request=request_other_slice),
             "expected": {"anchor": anchor, "slice": "not_a_declared_slice"}},
            {"name": "request_is_a_string",
             "payload": mutate(request="hbm_packaging"), "expected": expected},
            {"name": "authority_can_rank_true",
             "payload": mutate(authority={**valid["authority"], "can_rank": True}),
             "expected": expected},
            {"name": "authority_missing_can_size",
             "payload": mutate(authority={k: v for k, v in valid["authority"].items()
                                          if k != "can_size"}),
             "expected": expected},
            {"name": "extra_top_level_key",
             "payload": mutate(house_view={"status": "ready"}), "expected": expected},
            {"name": "summary_bad_status",
             "payload": mutate(summary={**valid["summary"], "status": "ok"}),
             "expected": expected},
            {"name": "generation_empty", "payload": mutate(generation=""),
             "expected": expected},
            {"name": "limitations_not_an_array", "payload": mutate(limitations={}),
             "expected": expected},
            {"name": "expectations_house_forecast_ready",
             "payload": mutate(expectations={
                 **valid["expectations"],
                 "house_forecast": {**valid["expectations"]["house_forecast"],
                                    "status": "ready"}}),
             "expected": expected},
        ],
        "evidenceCases": [
            {"name": "valid", "payload": evidence_ok, "generation": valid["generation"]},
            {"name": "no_expected_generation", "payload": evidence_ok, "generation": None},
            {"name": "research_schema",
             "payload": {**evidence_ok, "schema": attrs["schema"]},
             "generation": valid["generation"]},
            {"name": "generation_mismatch", "payload": evidence_ok, "generation": "other"},
            {"name": "authority_true",
             "payload": {**evidence_ok,
                         "authority": {**valid["authority"], "can_gate": True}},
             "generation": valid["generation"]},
            {"name": "not_object", "payload": None, "generation": None},
        ],
        "storedCases": [
            {"name": "declared_slice", "raw": json.dumps(
                {"slice_key": first_slice, "view": "economics", "time_mode": "latest"})},
            {"name": "foreign_slice", "raw": json.dumps(
                {"slice_key": "not_a_declared_slice", "view": "economics",
                 "time_mode": "latest"})},
            {"name": "four_keys", "raw": json.dumps(
                {"slice_key": first_slice, "view": "economics", "time_mode": "latest",
                 "token": "x"})},
        ],
        # A spec whose slices are disjoint from the vocabulary compiled into
        # the client. Without it, "spec-driven" is indistinguishable from
        # "reads the module constant": every case would agree.
        "altSpec": {
            "anchor": "synthetic_vertical",
            "slices": ["alpha_slice", "beta_slice"],
            "schema": "synthetic_theme_research.v1",
            "evidenceSchema": "synthetic_theme_research.evidence.v1",
            "labels": {}, "apiQuery": "/q", "apiEvidence": "/e",
        },
        "storedAltCases": [
            {"name": "its_own_slice", "raw": json.dumps(
                {"slice_key": "alpha_slice", "view": "economics", "time_mode": "latest"})},
            {"name": "the_incumbents_slice", "raw": json.dumps(
                {"slice_key": first_slice, "view": "economics", "time_mode": "latest"})},
        ],
    }
    src = _MOUNT_HARNESS % {"contract": _contract(js_text)}
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "mount_contract.js"
        script.write_text(src, encoding="utf-8")
        cases_path = Path(td) / "cases.json"
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        run = subprocess.run(
            [shutil.which("node"), str(script), str(cases_path)],
            capture_output=True, text=True, timeout=60,
        )
    assert run.returncode == 0, f"node exited {run.returncode}:\n{run.stderr}\n{run.stdout}"
    return json.loads(run.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def mount_battery(js_text):
    if not HAS_NODE:
        pytest.skip("node not on PATH")
    return _run_mount_battery(js_text)


@needs_node
def test_mount_spec_is_built_from_the_rendered_registration(mount_battery):
    """The mount the page renders configures the client — no constant does."""
    assert mount_battery["spec"]["ok"] is True, mount_battery["spec"]
    spec = mount_battery["spec"]["spec"]
    attrs = _mount_attrs()
    assert spec["anchor"] == attrs["anchor"]
    assert spec["slices"] == attrs["slices"].split(",")
    assert spec["schema"] == attrs["schema"]
    assert spec["evidenceSchema"] == attrs["evidenceSchema"]
    assert spec["labels"] == json.loads(attrs["labels"])


@needs_node
@pytest.mark.parametrize("case, reason", [
    ("empty_schema", "unconfigured:schema"),
    ("schema_equals_evidence", "unconfigured:evidenceSchema"),
    ("anchor_with_dash", "unconfigured:anchor"),
    ("anchor_empty", "unconfigured:anchor"),
    ("duplicate_slices", "unconfigured:slices"),
    ("slice_with_space", "unconfigured:slices"),
    ("labels_extra_key", "unconfigured:labels"),
    ("labels_missing_slice", "unconfigured:labels"),
    ("label_not_pair", "unconfigured:labels"),
    ("label_half_empty", "unconfigured:labels"),
    ("labels_array", "unconfigured:labels"),
    ("labels_invalid_json", "unconfigured:labels"),
    ("api_query_empty", "unconfigured:apiQuery"),
    ("not_an_object", "unconfigured:attrs"),
])
def test_an_unconfigured_mount_is_refused_by_field(mount_battery, case, reason):
    """A mount that cannot say what it is renders nothing, and says which field."""
    assert mount_battery["specReject"][case] == reason


@needs_node
def test_labels_round_trip_literally(js_text):
    """A label is text. It is never interpreted as markup, anywhere."""
    attrs = _mount_attrs()
    hostile = {key: ['<b>&"\'</b>', "值"] for key in attrs["slices"].split(",")}
    attrs = {**attrs, "labels": json.dumps(hostile, ensure_ascii=False)}
    src = _MOUNT_HARNESS % {"contract": _contract(js_text)}
    cases = {"attrs": attrs, "valid": _envelope(),
             "expected": {"anchor": attrs["anchor"], "slice": attrs["slices"].split(",")[0]},
             "foreignExpected": {"anchor": "other", "slice": "x"},
             "badAttrs": [], "envelopeCases": [], "evidenceCases": [],
             "storedCases": [], "altSpec": None, "storedAltCases": []}
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "mount_contract.js"
        script.write_text(src, encoding="utf-8")
        cases_path = Path(td) / "cases.json"
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        run = subprocess.run([shutil.which("node"), str(script), str(cases_path)],
                             capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    labels = json.loads(run.stdout.strip().splitlines()[-1])["labels_literal"]
    assert labels == hostile, "a label pair must survive byte-for-byte"


@needs_node
@pytest.mark.parametrize("case, reason", [
    ("valid", None),
    ("not_object", "not_object"),
    ("foreign_schema", "schema_mismatch"),
    ("schema_v1_1", "schema_mismatch"),
    ("schema_trailing_space", "schema_mismatch"),
    ("valid_but_wrong_vertical", "schema_mismatch"),
    ("other_anchor_in_request", "wrong_mount"),
    ("slice_outside_spec", "wrong_mount"),
    ("request_is_a_string", "wrong_mount"),
    ("authority_can_rank_true", "authority_not_false"),
    ("authority_missing_can_size", "authority_not_false"),
    ("extra_top_level_key", "extra_key:house_view"),
    ("summary_bad_status", "malformed:summary"),
    ("generation_empty", "malformed:generation"),
    ("limitations_not_an_array", "malformed:limitations"),
    ("expectations_house_forecast_ready", "malformed:expectations.house_forecast"),
])
def test_the_spec_driven_envelope_law(mount_battery, case, reason):
    """Every law the single-vertical validator applies, plus the mount check.

    `valid_but_wrong_vertical` is the one a single-vertical client could not
    express: a payload that is perfectly valid for ANOTHER registration must
    not render here, and it is refused on the schema it declares — compared
    with `===`, never by prefix, so `…v1.1` and a trailing space are both
    different contracts rather than compatible ones.
    """
    assert mount_battery["envelope"][case] == reason


@needs_node
@pytest.mark.parametrize("case, reason", [
    ("valid", None),
    ("no_expected_generation", None),
    ("research_schema", "schema_mismatch"),
    ("generation_mismatch", "generation_mismatch"),
    ("authority_true", "authority_not_false"),
    ("not_object", "not_object"),
])
def test_the_spec_driven_evidence_law(mount_battery, case, reason):
    """The evidence envelope is its own contract: schema, authority, generation."""
    assert mount_battery["evidence"][case] == reason


@needs_node
def test_a_stored_selection_belongs_to_the_mount_that_stored_it(mount_battery):
    """The slice vocabulary is the SPEC's, not the one compiled into the file.

    The second pair is what discriminates: under a spec whose slices are
    disjoint from this client's constants, its own slice must restore and the
    incumbent vertical's must not. A check that quietly consulted the compiled
    list instead would pass every case above and fail both of these — it did,
    when the suite had only the cases above.
    """
    assert mount_battery["stored"]["declared_slice"] == "restored"
    assert mount_battery["stored"]["foreign_slice"] is None
    assert mount_battery["stored"]["four_keys"] is None
    assert mount_battery["storedAlt"]["its_own_slice"] == "restored"
    assert mount_battery["storedAlt"]["the_incumbents_slice"] is None


@needs_node
def test_the_spec_driven_apply_keeps_every_drop_law(mount_battery):
    """A late or foreign answer changes nothing; a wrong-mount answer is refused."""
    assert mount_battery["apply"] == {
        "late_epoch": True, "foreign_principal": True,
        "accepted": True, "wrong_mount_rejected": True,
    }


def test_the_mount_driven_block_compares_schemas_only_by_identity(js_text):
    """No pattern matching on a schema id, anywhere in the contract block.

    A prefix or substring test would make `semiconductor_theme_research.v1.1`
    — a different contract — look compatible with this client.
    """
    contract = _code_only(_contract(js_text))
    assert "new RegExp(" not in contract
    for banned in (".startsWith(", ".endsWith(", ".indexOf('semiconductor",
                   'schema.indexOf(', "schema.match(", "schema.replace("):
        assert banned not in contract, banned
    assert "/^\\s+|\\s+$/" not in contract, (
        "the block trims by character, so no regex literal survives in it"
    )


# ---------------------------------------------------------------------------
# 13. Shared hook 4b — one instance per mount, executed.
#
# The 900 lines of page wiring below the contract marker had no execution
# coverage at all: the node batteries lift only the contract block, so every
# statement that touches the DOM was covered by source scans alone. The stub
# below is the smallest document/window/localStorage/fetch that lets the WHOLE
# file run under node, which is what makes "two verticals mount on one page"
# an executed claim rather than a described one.
# ---------------------------------------------------------------------------

_DOM_STUB = r"""
const fs = require('fs');
function mkEl(tag) {
  return {
    tagName: tag, children: [], attrs: {}, style: {}, dataset: {}, handlers: {},
    className: '', textContent: '', hidden: false, value: '', disabled: false,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) {
      return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
    },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(type, fn) {
      (this.handlers[type] = this.handlers[type] || []).push(fn);
    },
    removeEventListener() {}, focus() {}, blur() {},
    click() { (this.handlers.click || []).forEach(function (fn) { fn({}); }); },
    querySelector() { return null; }, querySelectorAll() { return []; },
    insertBefore(c) { this.children.push(c); return c; },
    contains() { return false; }
  };
}
const mounts = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')).map(function (attrs) {
  const el = mkEl('section');
  Object.keys(attrs).forEach(function (k) {
    /* A mount marked hostile throws the moment the instance builds its DOM —
       the cheapest true exception, used to prove failure ISOLATION rather
       than a stubbed one. */
    if (k === '__throws') { el.appendChild = function () { throw new Error('hostile mount'); }; return; }
    if (attrs[k] !== null) el.setAttribute(k, attrs[k]);
  });
  return el;
});
global.document = {
  createElement: mkEl,
  createDocumentFragment: function () { return mkEl('#fragment'); },
  createTextNode: function (t) { return { nodeValue: t, textContent: t, children: [] }; },
  querySelector: function () { return null; },
  querySelectorAll: function (sel) {
    return sel === '[data-theme-research-mount]' ? mounts : [];
  },
  addEventListener: function () {},
  documentElement: mkEl('html'), body: mkEl('body')
};
global.window = {
  setTimeout: function () { return 0; }, addEventListener: function () {},
  location: { origin: 'https://example.test', href: 'https://example.test/x' }
};
global.localStorage = {
  store: process.argv[4] ? JSON.parse(fs.readFileSync(process.argv[4], 'utf8')) : {},
  reads: [],
  getItem: function (k) {
    this.reads.push(k);
    return Object.prototype.hasOwnProperty.call(this.store, k) ? this.store[k] : null;
  },
  writes: [],
  setItem: function (k, v) { this.writes.push({ key: k, value: v }); this.store[k] = v; },
  removeItem: function (k) { delete this.store[k]; }
};
const fetchCalls = [];
global.fetch = function (url, init) {
  fetchCalls.push({ url: String(url), body: (init && init.body) || null });
  return Promise.resolve({
    ok: true, status: 200, headers: { get: function () { return 'application/json'; } },
    json: function () { return Promise.resolve({}); }
  });
};
global.AbortController = function () { this.signal = {}; this.abort = function () {}; };
global.URL = URL;

function textOf(el, out) {
  if (!el || typeof el !== 'object') return out;
  if (typeof el.textContent === 'string' && el.textContent) out.push(el.textContent);
  (el.children || []).forEach(function (c) { textOf(c, out); });
  return out;
}

var failure = null;
try {
  new Function(fs.readFileSync(process.argv[2], 'utf8'))();
} catch (e) {
  failure = String(e && e.message);
}

/* Post-boot clicks, so a RESTORED selection can be observed behaviourally:
   the chip handler returns early when the clicked slice is already current
   (`if (currentSlice === key) return;`), so clicking the slice a member is
   supposed to have remembered must issue NO request. */
function findChip(el, key, out) {
  if (!el || typeof el !== 'object') return out;
  if (el.attrs && el.attrs['data-tr-slice'] === key) out.push(el);
  (el.children || []).forEach(function (c) { findChip(c, key, out); });
  return out;
}
if (process.argv[5]) {
  JSON.parse(fs.readFileSync(process.argv[5], 'utf8')).forEach(function (c) {
    findChip(mounts[c.mount], c.slice, []).forEach(function (chip) { chip.click(); });
  });
}
console.log(JSON.stringify({
  bootFailure: failure,
  states: mounts.map(function (m) { return m.getAttribute('data-tr-state'); }),
  text: mounts.map(function (m) { return textOf(m, []); }),
  storageKeys: Object.keys(global.localStorage.store),
  storageReads: global.localStorage.reads,
  storageWrites: global.localStorage.writes,
  fetchCalls: fetchCalls
}));
"""


def _run_page(mount_attrs: list[dict], seed: dict | None = None,
              clicks: list[dict] | None = None) -> dict:
    """Execute the WHOLE client — contract block and wiring — over stub mounts.

    ``seed`` pre-populates localStorage, so a remembered selection can be shown
    to survive (or not) a real boot rather than being reasoned about."""
    assert shutil.which("node"), "node not on PATH"
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "page_stub.js"
        stub.write_text(_DOM_STUB, encoding="utf-8")
        cases = Path(td) / "mounts.json"
        cases.write_text(json.dumps(mount_attrs), encoding="utf-8")
        argv = [shutil.which("node"), str(stub), str(JS_PATH), str(cases)]
        if seed is not None or clicks is not None:
            seed_file = Path(td) / "seed.json"
            seed_file.write_text(json.dumps(seed or {}), encoding="utf-8")
            argv.append(str(seed_file))
        if clicks is not None:
            click_file = Path(td) / "clicks.json"
            click_file.write_text(json.dumps(clicks), encoding="utf-8")
            argv.append(str(click_file))
        run = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"node exited {run.returncode}:\n{run.stderr}"
    return json.loads(run.stdout.strip().splitlines()[-1])


def _mount_element(**over) -> dict:
    attrs = _mount_attrs()
    element = {
        "data-theme-research-mount": "",
        "data-anchor-theme-id": attrs["anchor"],
        "data-slices": attrs["slices"],
        "data-schema-id": attrs["schema"],
        "data-evidence-schema-id": attrs["evidenceSchema"],
        "data-slice-labels": attrs["labels"],
        "data-api-query": attrs["apiQuery"],
        "data-api-evidence": attrs["apiEvidence"],
    }
    element.update(over)
    return element


_SECOND_VERTICAL = {
    "data-theme-research-mount": "",
    "data-anchor-theme-id": "synthetic_vertical",
    "data-slices": "alpha_slice,beta_slice",
    "data-schema-id": "synthetic_theme_research.v1",
    "data-evidence-schema-id": "synthetic_theme_research.evidence.v1",
    "data-slice-labels": json.dumps(
        {"alpha_slice": ["Alpha slice", "甲切片"], "beta_slice": ["Beta slice", "乙切片"]},
        ensure_ascii=False,
    ),
    "data-api-query": "/api/themes/v1/research/query",
    "data-api-evidence": "/api/themes/v1/research/evidence",
}


@needs_node
def test_two_verticals_mount_on_one_page():
    """The hook's claim, executed: both sections bind, each with its OWN copy.

    Before this, the page bound `querySelector` — the FIRST mount — and read
    its anchor and slice list as the client's only configuration. A second
    registered vertical on the same page was invisible, and its slice chips
    would have rendered the typed "Unmapped label" fallback from a map that
    knows one vertical's slices.
    """
    page = _run_page([_mount_element(), _SECOND_VERTICAL])
    assert page["bootFailure"] is None, page["bootFailure"]
    assert page["states"] == ["mounted", "mounted"], page["states"]
    incumbent, second = page["text"][0], page["text"][1]
    labels = json.loads(_mount_attrs()["labels"])
    for pair in labels.values():
        assert pair[0] in incumbent and pair[1] in incumbent, pair
    assert "Alpha slice" in second and "甲切片" in second
    assert "Beta slice" in second and "乙切片" in second
    # Neither vertical renders the other's copy, and neither falls back.
    assert "Alpha slice" not in incumbent
    for pair in labels.values():
        assert pair[0] not in second, pair
    for rendered in (incumbent, second):
        assert not any("Unmapped label" in line for line in rendered), rendered


@needs_node
def test_each_mount_reads_its_selection_under_its_own_anchor():
    """One storage family, one key per anchor — never one shared selection.

    Restoring is what happens at mount time (a write needs a click), so the
    READ keys are what this asserts. Two verticals sharing one key would let
    one mount restore a slice the other stored.
    """
    page = _run_page([_mount_element(), _SECOND_VERTICAL])
    reads = sorted(set(page["storageReads"]))
    assert reads == ["theme_research_sel:ai_semiconductors",
                     "theme_research_sel:synthetic_vertical"], reads


@needs_node
def test_an_unconfigured_mount_renders_a_static_note_and_nothing_else():
    """A mount that cannot say what it is fetches nothing and renders copy."""
    page = _run_page([_mount_element(**{"data-slice-labels": "{not json"})])
    assert page["states"] == ["unconfigured"], page["states"]
    rendered = page["text"][0]
    assert "Research mount is not configured on this page." in rendered
    assert "本页的研究模块未配置。" in rendered
    assert page["storageKeys"] == []
    assert page["storageReads"] == [], "an unconfigured mount touches no storage"


@needs_node
def test_a_repeated_anchor_is_refused_not_bound_twice():
    """Two sections for one anchor would share a storage key and an epoch."""
    page = _run_page([_mount_element(), _mount_element()])
    assert page["states"] == ["mounted", "duplicate"], page["states"]
    assert page["text"][1] == []


@needs_node
def test_one_failing_instance_never_stops_the_others():
    """Failure isolation, executed: the mount AFTER a thrower still binds.

    The first mount throws for real while its instance builds its DOM, so
    this asserts the loop's own try boundary — a `break` or an unguarded call
    there would take the whole page's research down with one vertical.
    """
    hostile = _mount_element(**{
        "data-anchor-theme-id": "hostile_vertical", "__throws": True,
    })
    page = _run_page([hostile, _SECOND_VERTICAL])
    assert page["bootFailure"] is None, page["bootFailure"]
    assert page["states"] == ["failed", "mounted"], page["states"]


@needs_node
def test_a_cross_origin_endpoint_is_refused_without_a_request():
    """A mount pointed off-site binds but sends nothing — the existing law."""
    page = _run_page([_mount_element(**{
        "data-anchor-theme-id": "offsite_vertical",
        "data-api-query": "https://elsewhere.example/api",
    })])
    assert page["bootFailure"] is None, page["bootFailure"]
    assert page["states"] == ["mounted"], page["states"]


def test_the_wiring_binds_every_mount_not_the_first(js_text):
    wiring = _code_only(js_text[js_text.index(_END):])
    assert "querySelectorAll('[data-theme-research-mount]')" in wiring
    assert "querySelector('[data-theme-research-mount]')" not in wiring
    assert js_text.count("function mountInstance(") == 1
    for state in ("'unconfigured'", "'duplicate'", "'failed'", "'mounted'"):
        assert state in wiring, state


def test_the_wiring_validates_through_the_mounts_spec(js_text):
    """The wiring must call the SPEC-driven contract, not the fixed one.

    The node batteries execute only the contract block, so a wiring that kept
    calling the single-vertical functions would leave every spec-driven test
    green while the page still validated against one vertical's constants.
    """
    wiring = _code_only(js_text[js_text.index(_END):])
    assert "applyResearchResponseFor(state," in wiring
    assert "validateEvidenceFor(SPEC," in wiring
    assert "parseStoredSelectionFor(SPEC," in wiring
    assert re.search(r"(?<!For)\bapplyResearchResponse\(", wiring) is None, (
        "the wiring must not call the fixed-vertical response applier"
    )
    assert re.search(r"(?<!For)\bparseStoredSelection\(", wiring) is None
    assert "pair(L.slice" not in wiring, "slice chips must read the mount's labels"
    assert "SPEC.labels" in wiring


def test_every_storage_key_is_scoped_to_its_anchor(js_text):
    wiring = _code_only(js_text[js_text.index(_END):])
    calls = re.findall(r"localStorage\s*\.\s*(?:getItem|setItem|removeItem)\s*\([^)]*", wiring)
    assert calls, "no localStorage call found in the wiring"
    for call in calls:
        assert "'theme_research_sel'" in call, call
        assert "+ ':' + SPEC.anchor" in call, call


@needs_node
def test_a_second_verticals_remembered_slice_actually_restores():
    """A live defect only a second vertical could expose.

    The restore test conjoined SLICES — the mount's own vocabulary, which is
    the correct check — with TR_SLICE_KEYS, one vertical's list compiled into
    this file. For every other vertical the conjunction is unsatisfiable, so a
    VALID stored selection was silently discarded and the default tab stood.
    No error, no console line: the member's remembered tab just never came
    back. Found by the Robotics receiver reading the wiring.

    Observed behaviourally, not by reading a variable: the chip handler
    returns early when the clicked slice is already current, and a selection
    change always persists. So clicking the slice a member is supposed to have
    remembered must write NOTHING — and the control proves the probe can see a
    write at all.
    """
    stored = json.dumps(
        {"slice_key": "beta_slice", "view": "economics", "time_mode": "latest"})
    seeded = _run_page(
        [_mount_element(), _SECOND_VERTICAL],
        seed={"theme_research_sel:synthetic_vertical": stored},
        clicks=[{"mount": 1, "slice": "beta_slice"}],
    )
    assert seeded["states"][1] == "mounted", seeded["states"]
    assert seeded["storageWrites"] == [], (
        "the remembered slice was not restored: clicking it counted as a "
        "CHANGE, which only happens when it was not already current"
    )

    # CONTROL — with nothing remembered the default (first) slice stands, so
    # the same click IS a change and DOES persist.
    control = _run_page(
        [_mount_element(), _SECOND_VERTICAL],
        clicks=[{"mount": 1, "slice": "beta_slice"}],
    )
    assert control["storageWrites"], "the probe cannot see a write at all"
    assert control["storageWrites"][0]["key"] == \
        "theme_research_sel:synthetic_vertical", control["storageWrites"]
    assert "beta_slice" in control["storageWrites"][0]["value"]


def test_the_wiring_never_consults_one_verticals_slice_list(js_text):
    """The regression that made the bug above possible: a mount-scoped check
    beside a file-scoped one. TR_SLICE_KEYS knows a single vertical, so the
    wiring must not read it anywhere."""
    wiring = _code_only(js_text[js_text.index(_END):])
    assert "TR_SLICE_KEYS" not in wiring, (
        "the wiring must validate slices against the MOUNT's vocabulary"
    )
