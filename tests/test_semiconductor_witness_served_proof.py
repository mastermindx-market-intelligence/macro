"""T12 — the SERVED proof for the two mandated witnesses.

Every other Semiconductor B suite proves one seam. This one proves the whole
path produces something a member can READ:

    production workspace writer → the Company Intelligence reader's
    model-facing surfaces → the declared witness scope + owner identity join →
    the workspace projector → the composer → the paid route (real app, real
    entitlement dependency, private headers) → the frozen v1 contract →
    the mount partial → the checked-in client JS executed by node → visible,
    bilingual rows.

Two witnesses, both mandatory:

* **W-A — HBM / advanced packaging, with TSMC.** An AI-driven slice.
* **W-B — SiC / GaN specialty devices, with onsemi.** A NON-AI slice, present
  precisely so the vertical cannot be accepted on an AI-only cohort.

Each must show the management sequence the composer built from two consecutive
real releases — prior outlook, the reported actual, the new outlook, and the
comparison between them — with its limitations visible. **An empty economics
panel is a FAILURE here, not a passing "degraded" render**: that is the whole
point of the proof, and the client shipped for two commits rendering every
label as "Unmapped label" while every other suite stayed green.

What this proof does NOT claim: production coverage. The live
``event_workspaces/`` nest carries neither witness and one period per issuer
per generation, so a served production panel still needs #7870 merged, a
nightly that has seen two consecutive releases per witness, and the
publication-retention answer. The nest here is built by the PRODUCTION writer
from real issuer metadata, in a temporary directory, and reached through the
real reader — no base-URL override, no producer surface, no fixture standing
in for the transport.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import earnings as earnings_api
from app.main import app as production_app
from engine.market_ontology import semiconductor_owner_bundle as owner_bundle
from engine.market_ontology.semiconductor_witness_scope import (
    SLICE_SCOPE_UNOWNED,
    WitnessIdentity,
    WitnessScope,
)
from tests.semiconductor_research_helpers import build_witness_nest, wire_witness_nest

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "site" / "assets" / "js" / "theme-research.js"
MOUNT_PATH = ROOT / "templates" / "_theme_research_mount.html.j2"
SCHEMA_PATH = (ROOT / "contracts" / "market_ontology"
               / "semiconductor_theme_research.v1.schema.json")
_BEGIN = "/* THEME-RESEARCH-CONTRACT-BEGIN */"
_END = "/* THEME-RESEARCH-CONTRACT-END */"
_HAN = re.compile(r"[一-鿿]")

needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
_ARTIFACTS_PRESENT = (
    (ROOT / "data" / "reference" / "security_master.parquet").is_file()
    and (ROOT / "data" / "theme_graph" / "nodes.parquet").is_file()
)
needs_identity_artifacts = pytest.mark.skipif(
    not _ARTIFACTS_PRESENT,
    reason="committed Data OS / Theme Graph artifacts absent (sparse checkout)",
)

# The two witnesses, with the identities the Theme Graph / Data OS owners
# resolve live (pinned here so the render proof runs without the parquet
# artifacts; the real-join variant below asserts the owners agree).
W_A = ("hbm_packaging", WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                                        issuer_id="ISS:US-XNYS-TSM", cik="0001046179"))
W_B = ("sic_gan_specialty", WitnessIdentity(ticker="ON", company_node_id="co:us:ON",
                                            issuer_id="ISS:US-XNAS-ON", cik="0001097864"))
_PAID_USER = {"id": "paid-user", "tier": "essential"}
_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}
# Vocabulary this surface must never put on screen (research is context only).
_FORBIDDEN_WORDS = ("can_rank", "can_gate", "can_size", "can_originate",
                    "can_open_entry", "buy", "sell", "position size", "entry")


@pytest.fixture
def entitled_client():
    """The real app with only the existing entitlement seam overridden."""
    production_app.dependency_overrides[earnings_api.require_site_full_user] = (
        lambda: dict(_PAID_USER)
    )
    try:
        with TestClient(production_app, raise_server_exceptions=False) as client:
            yield client
    finally:
        production_app.dependency_overrides.pop(earnings_api.require_site_full_user, None)


@pytest.fixture(scope="module")
def nest_files(tmp_path_factory):
    """Two consecutive periods per witness, written by the PRODUCTION writer."""
    return build_witness_nest(tmp_path_factory.mktemp("served_proof_nest"))


@pytest.fixture
def served_nest(monkeypatch, nest_files):
    return wire_witness_nest(monkeypatch, nest_files)


def _pin(monkeypatch, slice_key, identity):
    scope = WitnessScope(slice_key=slice_key, identities=(identity,),
                         omissions=(SLICE_SCOPE_UNOWNED,))
    monkeypatch.setattr(owner_bundle, "resolve_witness_scope", lambda key: scope)


def _serve(client, slice_key, view="economics"):
    response = client.post("/api/themes/v1/research/query", json={
        "anchor_theme_id": "ai_semiconductors", "slice_key": slice_key, "view": view,
        "time_mode": "latest", "source_cutoff": None, "recorded_cutoff": None,
        "offset": 0, "limit": 50, "expected_generation": None,
    })
    assert response.status_code == 200, response.text
    for name, value in _PRIVATE_HEADERS.items():
        assert response.headers[name] == value, name
    import jsonschema  # noqa: PLC0415
    payload = response.json()
    jsonschema.validate(payload, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    return payload


_RENDER = r"""
%(contract)s

var payload = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
var out = {};
out.valid = validateEnvelope(payload);
var econ = economicsModel(payload);
out.status = econ.status;
out.gate = econ.witnessGate;
out.rows = (econ.rows || []).map(function (row) {
  var label = pair(TR_ECON_LABELS.role, row.role);
  return { role: row.role, label_en: label[0], label_zh: label[1],
           value_en: row.value[0], value_zh: row.value[1],
           note_en: row.note[0], note_zh: row.note[1] };
});
var lim = limitationsModel(payload);
out.limitations = lim.limitations;
out.limitations_status = lim.limitationsStatus;
out.status_word = pair(L.status, payload.economics.status);
out.evidence = evidenceRefsModel(payload);
out.label_self_test = labelMapsSelfTest();
/* every string this render would put on screen, for the vocabulary scans */
var screen = [];
for (var i = 0; i < out.rows.length; i++) {
  var r = out.rows[i];
  screen.push(r.label_en, r.label_zh, r.value_en, r.value_zh, r.note_en, r.note_zh);
}
screen = screen.concat(out.limitations || [], out.status_word);
out.screen = screen;
console.log(JSON.stringify(out));
"""


def _render(payload: dict) -> dict:
    """Run the CHECKED-IN client's contract block over the SERVED bytes."""
    js = JS_PATH.read_text(encoding="utf-8")
    a, b = js.index(_BEGIN), js.index(_END)
    assert a < b
    src = _RENDER % {"contract": js[a:b]}
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "served_render.js"
        script.write_text(src, encoding="utf-8")
        data = Path(td) / "served.json"
        data.write_text(json.dumps(payload), encoding="utf-8")
        run = subprocess.run([shutil.which("node"), str(script), str(data)],
                             capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"node exited {run.returncode}:\n{run.stderr}"
    return json.loads(run.stdout.strip().splitlines()[-1])


def _render_mount(anchor: str) -> str:
    import jinja2  # noqa: PLC0415

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=True, undefined=jinja2.Undefined,
    )
    return env.get_template("_theme_research_mount.html.j2").render(
        theme_research_anchor=anchor,
    )


# ---------------------------------------------------------------------------
# 1. The mount the member's page actually carries
# ---------------------------------------------------------------------------

def test_mount_carries_the_anchor_both_slices_and_the_served_client():
    html = _render_mount("ai_semiconductors")
    assert 'data-anchor-theme-id="ai_semiconductors"' in html
    assert 'data-slices="hbm_packaging,sic_gan_specialty"' in html
    assert 'data-api-query="/api/themes/v1/research/query"' in html
    assert 'data-api-evidence="/api/themes/v1/research/evidence"' in html
    assert "hidden" in html and "theme-research.js" in html
    # No payload, figure or token is rendered at build time.
    assert "revenue" not in html.lower() and "0001046179" not in html
    assert _render_mount("") == "" or _render_mount("").strip() == ""


# ---------------------------------------------------------------------------
# 2. W-A and W-B — a served, non-empty, readable economics panel
# ---------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("witness, slice_key, identity", [
    ("W-A HBM / advanced packaging (TSMC)", W_A[0], W_A[1]),
    ("W-B SiC / GaN specialty devices (onsemi)", W_B[0], W_B[1]),
])
def test_served_witness_panel_is_non_empty_and_readable(
    monkeypatch, entitled_client, served_nest, witness, slice_key, identity,
):
    _pin(monkeypatch, slice_key, identity)
    payload = _serve(entitled_client, slice_key)
    view = _render(payload)

    assert view["valid"]["ok"] is True, (witness, view["valid"])
    assert view["label_self_test"] == [], (witness, view["label_self_test"])
    assert view["status"] == "ready" and view["gate"] == "positive", (witness, view)
    roles = [row["role"] for row in view["rows"]]
    assert roles == ["prior_outlook", "actual", "new_outlook",
                     "prior_vs_actual", "witness_gate"], (witness, roles)

    # The panel is READ, not merely present: every cell carries text in both
    # languages and no cell fell back to the unmapped label.
    for row in view["rows"]:
        for key in ("label_en", "label_zh", "value_en", "value_zh"):
            assert row[key].strip(), (witness, row["role"], key)
        assert row["label_en"] != "Unmapped label", (witness, row["role"])
        assert "Unmapped label" not in row["value_en"], (witness, row)
        assert _HAN.search(row["label_zh"]), (witness, row["role"], row["label_zh"])

    # The management sequence the composer actually built, verbatim from the
    # served bytes — the figures pass through as text, never recomputed.
    mgmt = payload["economics"]["management"]["roles"]
    by_role = {row["role"]: row for row in view["rows"]}
    for role, field in (("prior_outlook", "low"), ("new_outlook", "low")):
        spelled = str(mgmt[role][field]).rstrip("0").rstrip(".") or "0"
        assert spelled in by_role[role]["value_en"], (witness, role, by_role[role])
        assert mgmt[role]["horizon"] in by_role[role]["note_en"], (witness, role)
    actual = str(mgmt["actual"]["value"]).rstrip("0").rstrip(".") or "0"
    assert actual in by_role["actual"]["value_en"], (witness, by_role["actual"])
    assert mgmt["actual"]["fiscal_period"] in by_role["actual"]["note_en"], witness

    # The two outlooks are DIFFERENT reads, not the same guidance shown twice.
    # The synthetic issuer repeats its range across releases, so the figures
    # alone cannot discriminate: the prior outlook is the EARLIER release's
    # guidance for the period that was then reported, and the new outlook is
    # the reported release's guidance for the period after it. Their horizons
    # must therefore differ, and the prior must name the reported period.
    assert mgmt["prior_outlook"]["horizon"] != mgmt["new_outlook"]["horizon"], witness
    assert mgmt["prior_outlook"]["horizon"] == mgmt["actual"]["fiscal_period"], witness
    assert by_role["prior_outlook"]["note_en"] != by_role["new_outlook"]["note_en"], witness

    # The comparison the reader's guidance-history owner returned, in words.
    comparison = payload["economics"]["management"]["comparisons"]["prior_vs_actual"]
    rendered = by_role["prior_vs_actual"]["value_en"]
    if comparison["status"] == "comparable":
        assert rendered.startswith("Comparable"), (witness, rendered)
        assert comparison["position"].replace("_", " ").split()[0] in rendered.lower()
    else:
        assert "refused" in rendered.lower(), (witness, rendered)

    # Both event ids back the gate; the limitations SAY what is missing.
    for event_id in payload["economics"]["input_refs"]:
        assert event_id in by_role["witness_gate"]["note_en"], (witness, event_id)
    assert view["limitations_status"] == "ready"
    assert "omitted:private_assertions_unbound" in view["limitations"], witness
    assert "omitted:slice_scope_unowned" in view["limitations"], witness


@needs_node
@pytest.mark.parametrize("slice_key, identity", [W_A, W_B])
def test_served_panel_never_renders_authority_or_trading_vocabulary(
    monkeypatch, entitled_client, served_nest, slice_key, identity,
):
    """Research is context only: no rank, gate, size, entry or origination
    word reaches the screen, and every authority flag on the wire is false."""
    _pin(monkeypatch, slice_key, identity)
    payload = _serve(entitled_client, slice_key)
    view = _render(payload)
    haystack = " ".join(view["screen"]).lower()
    for word in _FORBIDDEN_WORDS:
        assert word not in haystack, (slice_key, word, haystack[:200])
    for block in (payload["authority"], payload["economics"]["management"]["authority"]):
        assert set(block.values()) == {False}, (slice_key, block)


@needs_node
def test_the_two_witnesses_are_different_issuers_and_one_is_not_an_ai_slice(
    monkeypatch, entitled_client, served_nest,
):
    """W-B exists so the vertical cannot be accepted on an AI-only cohort:
    the non-AI slice must serve its own issuer's figures, not W-A's."""
    _pin(monkeypatch, *W_A)
    a = _serve(entitled_client, W_A[0])
    _pin(monkeypatch, *W_B)
    b = _serve(entitled_client, W_B[0])
    assert a["request"]["slice_key"] == "hbm_packaging"
    assert b["request"]["slice_key"] == "sic_gan_specialty"
    assert a["economics"]["input_refs"] != b["economics"]["input_refs"]
    assert all("0001046179" in ref for ref in a["economics"]["input_refs"])
    assert all("0001097864" in ref for ref in b["economics"]["input_refs"])
    for payload in (a, b):
        assert _render(payload)["rows"], "an empty economics panel fails this proof"


@needs_node
@needs_identity_artifacts
@pytest.mark.parametrize("slice_key, identity", [W_A, W_B])
def test_the_owners_resolve_the_same_witness_identity_the_proof_pins(
    entitled_client, served_nest, slice_key, identity,
):
    """Nothing patched: the declared roster resolves each witness through the
    Theme Graph / Data OS owners, and the served panel is the same one."""
    from engine.market_ontology.semiconductor_witness_scope import resolve_witness_scope

    scope = resolve_witness_scope(slice_key)
    resolved = {w.ticker: w for w in scope.identities}
    assert identity.ticker in resolved, (slice_key, sorted(resolved))
    live = resolved[identity.ticker]
    assert (live.cik, live.company_node_id, live.issuer_id) == (
        identity.cik, identity.company_node_id, identity.issuer_id)
    assert SLICE_SCOPE_UNOWNED in scope.omissions
    view = _render(_serve(entitled_client, slice_key))
    assert view["status"] == "ready" and view["rows"]
