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
reader's model-facing surfaces — no producer surface, no predecessor walk.

Stated precisely, because a proof that overstates its own reach is worse than
a narrow one: the reader's HTTP layer IS replaced. ``wire_witness_nest``
substitutes ``_public_base_url`` and ``_fetch_bytes``, so this suite does not
exercise the reader's public-hostname guard, its redirect refusal, its origin
pinning or its size bound — those are the reader owner's own suite
(``tests/test_company_intelligence_neural_reader.py``). What runs here is
everything above the socket: marker → immutable generation → sha256 receipt →
contract validation → projection → composition → route → client. Likewise
``_pin`` fixes the witness cohort for the render cases so they run without the
committed identity artifacts; the unpinned case at the end patches nothing and
asserts the Theme Graph / Data OS owners resolve the same identities.

The mount test renders ``templates/_theme_research_mount.html.j2`` from the
context the page builder resolves for the semiconductor basket. Shared hook 2
closed the half of the earlier finding this suite could reach: a producer now
sets that context (``scripts/build_theme_detail.py``), and the anchor, slices,
schema ids and bilingual copy come from the registration rather than from the
template. The site ALSO ships an inline copy of this mount in
``templates/state_of_themes.html.j2``; retiring that second copy is hook 3's
work, and until it lands the two can still drift.
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
from tests.semiconductor_research_helpers import (
    build_witness_nest,
    wire_witness_nest,
    witness_workspace_payloads,
)

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


@pytest.fixture(scope="module")
def expected():
    """The figures each witness SHOULD show, read from the workspace payloads
    that went INTO the nest — never from the response under test.

    Without this the proof only established that the client faithfully renders
    whatever the route returned: the independent review swapped W-B's
    economics for W-A's, and scaled every figure by ten, and the suite stayed
    green both times. Fidelity is not correctness.
    """
    payloads = witness_workspace_payloads()
    out: dict[str, dict] = {}
    for cik in ("0001046179", "0001097864"):
        events = sorted(k for k in payloads if cik in k)
        assert len(events) == 2, (cik, events)
        prior_event, current_event = events
        current = payloads[current_event]
        fiscal = current["fiscal_period"]
        current_label = f"{fiscal['year']}Q{fiscal['quarter']}"
        facts = [f for f in current.get("facts") or []
                 if f.get("metric") == "revenue" and isinstance(f.get("value"), (int, float))]
        assert len(facts) == 1, (cik, [f.get("fact_id") for f in facts])
        prior_guidance = [g for g in payloads[prior_event].get("guidance") or []
                          if g.get("horizon") == current_label]
        new_guidance = [g for g in current.get("guidance") or []
                        if g.get("horizon") != current_label]
        assert len(prior_guidance) == 1 and len(new_guidance) == 1, cik
        out[cik] = {
            "events": events,
            "actual": facts[0],
            "prior_outlook": prior_guidance[0],
            "new_outlook": new_guidance[0],
            "period": current_label,
        }
    return out


_UNIT_LABEL = {"usd_billions": "US$ bn", "usd_millions": "US$ m"}


def _number_tokens(text: str) -> set[str]:
    """The numbers a rendered cell shows, as whole tokens — a substring test
    would let "13" satisfy a cell that only ever showed "13.5"."""
    return set(re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", text))


def _spelled(value) -> str:
    """How the client's `String(n)` spells a JSON number (15.0 → "15")."""
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


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


def _render_mount(mount: object) -> str:
    import jinja2  # noqa: PLC0415

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        autoescape=True, undefined=jinja2.Undefined,
    )
    return env.get_template("_theme_research_mount.html.j2").render(
        theme_research_mount=mount,
    )


# ---------------------------------------------------------------------------
# 1. The mount the member's page actually carries
# ---------------------------------------------------------------------------

def test_mount_carries_the_anchor_both_slices_and_the_served_client():
    """The mount the semiconductor basket page carries, from the registration.

    The context is the one the page builder itself resolves for this basket
    (``mount_context_for_basket``), not one written here — so this asserts the
    served page's mount, not a shape a test invented.
    """
    from engine.market_ontology.theme_research_mounts import (  # noqa: PLC0415
        mount_context_for_basket,
    )

    mount = mount_context_for_basket("ai_semiconductors")
    assert mount is not None, "the semiconductor basket page mounts no research"
    html = _render_mount(mount)
    assert 'data-anchor-theme-id="ai_semiconductors"' in html
    assert 'data-slices="hbm_packaging,sic_gan_specialty"' in html
    assert 'data-api-query="/api/themes/v1/research/query"' in html
    assert 'data-api-evidence="/api/themes/v1/research/evidence"' in html
    assert "hidden" in html and "theme-research.js" in html
    # Both witnesses' slices reach the page, each with its bilingual label.
    assert W_A[0] in html and W_B[0] in html
    # No payload, figure or token is rendered at build time.
    assert "revenue" not in html.lower() and "0001046179" not in html
    # An unclaimed basket mounts nothing at all.
    assert mount_context_for_basket("ai_infra") is None
    assert _render_mount(None).strip() == ""


# ---------------------------------------------------------------------------
# 2. W-A and W-B — a served, non-empty, readable economics panel
# ---------------------------------------------------------------------------

@needs_node
@pytest.mark.parametrize("witness, slice_key, identity", [
    ("W-A HBM / advanced packaging (TSMC)", W_A[0], W_A[1]),
    ("W-B SiC / GaN specialty devices (onsemi)", W_B[0], W_B[1]),
])
def test_served_witness_panel_is_non_empty_and_readable(
    monkeypatch, entitled_client, served_nest, expected, witness, slice_key, identity,
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

    # The panel is READ, not merely present: every cell — NOTES INCLUDED —
    # carries text in both languages and nothing fell back to the unmapped
    # label. The note cells were unchecked until the independent review broke
    # the economics lookup for `basis` and `outlook_status` alone and every
    # note read "Unmapped label" with this suite still green.
    for row in view["rows"]:
        for key in ("label_en", "label_zh", "value_en", "value_zh", "note_en", "note_zh"):
            if key.startswith("note") and row["role"] == "prior_vs_actual":
                continue  # the comparison row's note is legitimately empty
            assert row[key].strip(), (witness, row["role"], key)
            assert "Unmapped label" not in row[key], (witness, row["role"], key, row[key])
        assert _HAN.search(row["label_zh"]), (witness, row["role"], row["label_zh"])
        # The Chinese column must be a Chinese READING, not the English string
        # repeated — a join that returned `en` twice passed before. An
        # identifier list (the gate's event ids) is correctly untranslated and
        # must then be IDENTICAL, not silently half-rendered.
        for en, zh in ((row["value_en"], row["value_zh"]), (row["note_en"], row["note_zh"])):
            if not en.strip():
                continue
            if "evt_" in en:
                assert zh == en, (witness, row["role"], en, zh)
            else:
                assert _HAN.search(zh), (witness, row["role"], en, zh)

    # THE CORRECTNESS CHECK. Everything above proves the client renders what
    # the route returned; this proves the route returned THIS issuer's real
    # figures. The expectation comes from the workspace payloads that went
    # into the nest, never from the response.
    truth = expected[identity.cik]
    by_role = {row["role"]: row for row in view["rows"]}
    assert payload["economics"]["input_refs"] == truth["events"], (witness, payload["economics"])

    for role in ("prior_outlook", "new_outlook"):
        want = truth[role]
        shown = _number_tokens(by_role[role]["value_en"])
        assert {_spelled(want["low"]), _spelled(want["high"])} == shown, (
            witness, role, want, by_role[role]["value_en"])
        assert _UNIT_LABEL[want["unit"]] in by_role[role]["value_en"], (witness, role)
        assert want["horizon"] in by_role[role]["note_en"], (witness, role)

    want_actual = truth["actual"]
    assert _number_tokens(by_role["actual"]["value_en"]) == {_spelled(want_actual["value"])}, (
        witness, want_actual, by_role["actual"]["value_en"])
    assert _UNIT_LABEL[want_actual["unit"]] in by_role["actual"]["value_en"], witness
    assert truth["period"] in by_role["actual"]["note_en"], witness

    # And the other witness's distinctive figure must be nowhere on this panel
    # — the cheapest, bluntest guard against a swapped payload.
    other = next(v for k, v in expected.items() if k != identity.cik)
    other_actual = _spelled(other["actual"]["value"])
    assert other_actual not in " ".join(view["screen"]), (witness, other_actual)

    # The two outlooks are DIFFERENT reads, not the same guidance shown twice.
    # The synthetic issuer repeats its range across releases, so the figures
    # alone cannot discriminate: the prior outlook is the EARLIER release's
    # guidance for the period that was then reported, and the new outlook is
    # the reported release's guidance for the period after it. Their horizons
    # must therefore differ, and the prior must name the reported period.
    mgmt = payload["economics"]["management"]["roles"]
    assert mgmt["prior_outlook"]["horizon"] != mgmt["new_outlook"]["horizon"], witness
    assert mgmt["prior_outlook"]["horizon"] == mgmt["actual"]["fiscal_period"], witness
    assert by_role["prior_outlook"]["note_en"] != by_role["new_outlook"]["note_en"], witness
    # Stronger than the horizons: the two outlooks were read from DIFFERENT
    # source documents, so a reader that returned one guidance object twice
    # fails here even if the horizons were somehow equal.
    assert (truth["prior_outlook"]["source_span"]["document_id"]
            != truth["new_outlook"]["source_span"]["document_id"]), witness
    assert (mgmt["prior_outlook"].get("source_span", {}).get("document_id")
            != mgmt["new_outlook"].get("source_span", {}).get("document_id")), witness

    # The comparison the reader's guidance-history owner returned, in words.
    comparison = payload["economics"]["management"]["comparisons"]["prior_vs_actual"]
    rendered = by_role["prior_vs_actual"]["value_en"]
    if comparison["status"] == "comparable":
        assert rendered.startswith("Comparable"), (witness, rendered)
        assert comparison["position"].replace("_", " ").split()[0] in rendered.lower()
    elif comparison["status"] == "refused":
        assert "refused" in rendered.lower(), (witness, rendered)
    else:  # not_comparable — the owner's third verdict, rendered in words
        assert rendered.startswith("Not comparable"), (witness, comparison, rendered)

    # Both event ids back the gate; the limitations SAY what is missing.
    assert payload["economics"]["input_refs"], "an unbacked witness gate is not a gate"
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
    assert a["economics"]["input_refs"] and b["economics"]["input_refs"]
    assert a["economics"]["input_refs"] != b["economics"]["input_refs"]
    assert all("0001046179" in ref for ref in a["economics"]["input_refs"])
    assert all("0001097864" in ref for ref in b["economics"]["input_refs"])
    # Different issuers must also show different FIGURES — identical numbers
    # under different event ids is the swapped-payload case.
    assert (a["economics"]["management"]["roles"]["actual"]["value"]
            != b["economics"]["management"]["roles"]["actual"]["value"])
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
