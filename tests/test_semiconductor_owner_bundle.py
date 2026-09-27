"""tests/test_semiconductor_owner_bundle.py — the registered loader serves the
PUBLIC half through the Company Intelligence reader and declares the PRIVATE
half absent (T08c-2).

Laws pinned here
----------------
* ``system_replay`` is refused with ``identity_vintage_unsupported`` BEFORE
  any reader call; ``latest`` and ``source_history`` proceed.
* The reader is reached ONLY through ``read_current_event_workspace`` and
  ``read_event_workspace`` (model-facing, public-hostname-guarded); no
  base-URL override, no producer/raw/chain surface, no snapshot helper.
* Coverage absence is a typed omission; a reader raise or a refusal the
  reader itself documents as a 503 class is ``BundleUnavailable``.
* A workspace whose CIK disagrees with the identity plane never reaches the
  bundle (``identity_mismatch.<TICKER>``); a projector refusal is
  ``workspace_unprojectable.<event_id>``; row-level projector omissions are
  lifted into the bundle.
* Every omission token is wire-normalised to the frozen limitation grammar
  (one colon, added by the composer as ``omitted:``).
* An empty cohort empties data AND evidence; a non-empty cohort keeps only
  verified-CIK workspaces (one scope seam).
* The rights snapshot handed in is the one fingerprinted; the loader never
  re-reads the registry when the shell supplies it.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.market_ontology import semiconductor_owner_bundle as loader_module
from engine.market_ontology.semiconductor_owner_bundle import (
    IDENTITY_MISMATCH,
    IDENTITY_VINTAGE_UNSUPPORTED,
    PRIVATE_ASSERTIONS_UNBOUND,
    WORKSPACE_UNAVAILABLE,
    WORKSPACE_UNVERIFIED,
    WORKSPACE_UNPROJECTABLE,
    WORKSPACE_GENERATION_SPLIT,
    WORKSPACE_GENERATION_UNQUALIFIED,
    load_semiconductor_owner_bundle,
    scope_filter,
    wire_omission,
)
from engine.market_ontology.semiconductor_theme_research import (
    OwnerBundle,
    ResearchQuery,
    ResearchRefusal,
    compose_semiconductor_research,
)
from engine.market_ontology.semiconductor_witness_scope import (
    SLICE_SCOPE_UNOWNED,
    WitnessIdentity,
    WitnessScope,
)
from engine.market_ontology.theme_research_binding import BundleUnavailable
from engine.neuralweb import company_intelligence_reader as reader
from engine.neuralweb.company_intelligence_reader import CompanyIntelligenceReadError
from engine.theme_graph.rights import load_registry_snapshot
from tests.semiconductor_research_helpers import (
    WITNESS_NEST_BASE,
    build_witness_nest,
    wire_witness_nest,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "market_ontology" / "semiconductor_owner_bundle.py"
SCHEMA_TOKEN_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
)

_TSM = WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                       issuer_id="ISS:US-XNYS-TSM", cik="0001046179")
_ON = WitnessIdentity(ticker="ON", company_node_id="co:us:ON",
                      issuer_id="ISS:US-XNAS-ON", cik="0001097864")
_SNAPSHOT = ("rights_synthetic_snapshot", {})


def _query(**overrides) -> ResearchQuery:
    fields = dict(anchor_theme_id="ai_semiconductors", slice_key="hbm_packaging",
                  view="economics", time_mode="latest", source_cutoff=None,
                  recorded_cutoff=None, offset=0, limit=50, expected_generation=None)
    fields.update(overrides)
    return ResearchQuery(**fields)


def _pin_scope(monkeypatch, *identities: WitnessIdentity, slice_key: str = "hbm_packaging") -> None:
    scope = WitnessScope(slice_key=slice_key, identities=tuple(identities),
                         omissions=(SLICE_SCOPE_UNOWNED,))
    monkeypatch.setattr(loader_module, "resolve_witness_scope", lambda key: scope)


def _matches_grammar(limitation: str) -> bool:
    """The frozen v1 limitation grammar ``^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$``."""
    name, colon, detail = limitation.partition(":")
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name):
        return False
    if colon and (not detail or any(c not in SCHEMA_TOKEN_CHARS for c in detail)):
        return False
    return True


@pytest.fixture(scope="module")
def nest_files(tmp_path_factory):
    return build_witness_nest(tmp_path_factory.mktemp("witness_nest"))


@pytest.fixture
def served_nest(monkeypatch, nest_files):
    return wire_witness_nest(monkeypatch, nest_files)


# ─────────────────────────────────────────────────────────────────────────────
# (a) wire grammar
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("token, expected", [
    ("slice_scope_unowned", "slice_scope_unowned"),
    ("identity_unverified:TSM", "identity_unverified.TSM"),
    ("workspace_unavailable:TSM/2026Q1", "workspace_unavailable.TSM-2026Q1"),
    ("reported_malformed:rev enue", "reported_malformed.rev-enue"),
    ("slice_unknown:../x:y", "slice_unknown...-x-y"),  # '.' kept, '/' and ':' → '-'
    ("Bad-Name:x", "omission_malformed.x"),
    ("", "omission_malformed"),
    (None, "omission_malformed"),
    (7, "omission_malformed"),
    ("a:" + "z" * 200, ("a." + "z" * 200)[:64]),
])
def test_wire_omission_normalises_to_the_frozen_grammar(token, expected) -> None:
    wire = wire_omission(token)
    assert wire == expected
    assert _matches_grammar(f"omitted:{wire}"), wire
    assert len(wire) <= 64


def test_wire_omission_never_runs_a_hostile_str_subclass() -> None:
    class Hostile(str):
        def __str__(self):
            raise RuntimeError("never")

        def __format__(self, spec):
            raise RuntimeError("never")

        def __hash__(self):
            raise RuntimeError("never")

    assert wire_omission(Hostile("identity_unverified:TSM")) == "identity_unverified.TSM"


def test_wire_omissions_dedupe_and_bound_the_count() -> None:
    tokens = [f"reported_malformed:m{i}" for i in range(100)] + ["reported_malformed:m0"]
    wired = loader_module._wire_omissions(tokens)
    assert len(wired) == 64 and wired[-1] == "omissions_truncated"
    assert len(set(wired)) == len(wired)
    assert loader_module._wire_omissions(["a", "a", "b"]) == ("a", "b")


# ─────────────────────────────────────────────────────────────────────────────
# (b) period stepping — fiscal labels, uniform
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("period, expected", [
    ({"year": 2026, "quarter": 2}, "TSM/2026Q1"),
    ({"year": 2026, "quarter": 4}, "TSM/2026Q3"),
    ({"year": 2026, "quarter": 1}, "TSM/2025Q4"),
    ({"year": None, "quarter": 2}, None),
    ({"year": 2026, "quarter": 5}, None),
    ({"year": 2026, "quarter": 0}, None),
    ({"year": 999, "quarter": 2}, None),
    ({"year": True, "quarter": 2}, None),
    ({"year": 2026.0, "quarter": 2}, None),
    ({}, None),
])
def test_preceding_alias_steps_the_fiscal_label(period, expected) -> None:
    assert loader_module._preceding_alias("TSM", period) == expected


# ─────────────────────────────────────────────────────────────────────────────
# (c) scope seam — data AND evidence
# ─────────────────────────────────────────────────────────────────────────────

def _bundle(**overrides) -> OwnerBundle:
    fields = dict(
        revision_tuple=(), rights_revision="r", assertions=({"id": "a"},),
        identity_results=({"id": "i"},),
        event_workspaces=({"event_id": "e1", "cik": "0001046179"},
                          {"event_id": "e2", "cik": "0009999999"}),
        financial_packets=({"id": "p"},), interpretation_blocks=({"id": "b"},),
        native_refs=({"id": "n"},), omissions=("x",),
    )
    fields.update(overrides)
    return OwnerBundle(**fields)


def test_empty_cohort_empties_data_and_evidence_never_falls_through() -> None:
    scope = WitnessScope(slice_key="hbm_packaging", identities=(), omissions=(SLICE_SCOPE_UNOWNED,))
    filtered = scope_filter(_bundle(), scope)
    assert filtered.assertions == () and filtered.identity_results == ()
    assert filtered.event_workspaces == () and filtered.financial_packets == ()
    assert filtered.interpretation_blocks == () and filtered.native_refs == ()
    assert filtered.omissions == ("x",) and filtered.rights_revision == "r"


_PUBLIC_ONLY = dict(assertions=(), identity_results=(), financial_packets=(),
                    interpretation_blocks=(), native_refs=())


def test_non_empty_cohort_keeps_only_verified_cik_workspaces() -> None:
    scope = WitnessScope(slice_key="hbm_packaging", identities=(_TSM,), omissions=(SLICE_SCOPE_UNOWNED,))
    filtered = scope_filter(_bundle(**_PUBLIC_ONLY), scope)
    assert [w["event_id"] for w in filtered.event_workspaces] == ["e1"]
    filtered = scope_filter(_bundle(event_workspaces=("not-a-mapping",), **_PUBLIC_ONLY), scope)
    assert filtered.event_workspaces == ()


class _TruthyEq(str):
    """A CIK-shaped str whose ``__eq__`` lies — the seam must go through the
    hardened comparator, not set membership on the workspace value."""
    __slots__ = ()

    def __eq__(self, other):  # noqa: D105
        return True

    __hash__ = str.__hash__


def test_non_empty_cohort_compares_ciks_with_the_hardened_comparator() -> None:
    scope = WitnessScope(slice_key="hbm_packaging", identities=(_TSM,), omissions=(SLICE_SCOPE_UNOWNED,))
    bundle = _bundle(event_workspaces=({"event_id": "e9", "cik": _TruthyEq("0009999999")},
                                       {"event_id": "e1", "cik": "0001046179"},
                                       {"event_id": "e0", "cik": 1046179}), **_PUBLIC_ONLY)
    filtered = scope_filter(bundle, scope)
    assert [w["event_id"] for w in filtered.event_workspaces] == ["e1"]


@pytest.mark.parametrize("private", ["assertions", "identity_results", "financial_packets",
                                     "interpretation_blocks", "native_refs"])
def test_non_empty_cohort_fails_closed_when_a_private_input_reaches_the_seam(private) -> None:
    """R4 is open: no cohort rule for the private tuples has been accepted, so
    a non-empty one is a 503, never an unscoped pass-through."""
    scope = WitnessScope(slice_key="hbm_packaging", identities=(_TSM,), omissions=(SLICE_SCOPE_UNOWNED,))
    fields = dict(_PUBLIC_ONLY)
    fields[private] = ({"id": "leak"},)
    with pytest.raises(BundleUnavailable):
        scope_filter(_bundle(**fields), scope)
    # the EMPTY cohort still empties everything rather than raising (the
    # declared-empty case is a legitimate served answer)
    empty = WitnessScope(slice_key="hbm_packaging", identities=(), omissions=(SLICE_SCOPE_UNOWNED,))
    emptied = scope_filter(_bundle(**fields), empty)
    assert getattr(emptied, private) == () and emptied.event_workspaces == ()


@pytest.mark.parametrize("note, expected", [
    ("event workspace failed immutable receipt verification", "workspace_unverified.TSM-2026Q1"),
    ("Company Intelligence public source unavailable", "workspace_unverified.TSM-2026Q1"),
    ("", "workspace_unverified.TSM-2026Q1"),
    (None, "workspace_unverified.TSM-2026Q1"),
    ("event workspace alias could not be resolved", "workspace_unavailable.TSM-2026Q1"),
    ("event workspace does not cover this event", "workspace_unavailable.TSM-2026Q1"),
])
def test_preceding_read_failure_on_an_advertised_object_is_workspace_unverified(
        monkeypatch, served_nest, note, expected) -> None:
    """The preceding-period read is a single-alias read whose envelope reports
    every refusal as ``available: False`` + note. Only the reader's two
    coverage-absence literals mean 'not published' (``workspace_unavailable``);
    a receipt / validation / transport failure on an object the manifest
    advertises is ``workspace_unverified`` — distinct, never a 503, and the
    economics pane degrades exactly as for a single-period issuer."""
    _pin_scope(monkeypatch, _TSM)
    envelope = {"available": False} if note is None else {"available": False, "note": note}
    monkeypatch.setattr(reader, "read_event_workspace", lambda params: dict(envelope))
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert [w["event_id"] for w in bundle.event_workspaces] == ["evt_cik0001046179_2026q2_results"]
    assert expected in bundle.omissions, bundle.omissions
    other = ("workspace_unavailable" if expected.startswith("workspace_unverified")
             else "workspace_unverified") + ".TSM-2026Q1"
    assert other not in bundle.omissions
    response = compose_semiconductor_research(_query(), bundle)
    assert response["economics"]["status"] == "unavailable"
    assert "witness_economics_missing" in response["limitations"]
    assert f"omitted:{expected}" in response["limitations"]
    assert all(_matches_grammar(item) for item in response["limitations"]), response["limitations"]


def test_tampered_preceding_object_through_the_real_reader_is_workspace_unverified(monkeypatch, tmp_path) -> None:
    """Real chain: the preceding workspace object's bytes are tampered under
    the manifest's sha256 receipt. The production reader refuses the object
    (its note is not a coverage literal) → ``workspace_unverified``; the
    current period is still served."""
    files = build_witness_nest(tmp_path)
    targets = [url for url in files if "0001046179_2026q1" in url and "/workspaces/" in url]
    assert len(targets) == 1, targets
    original = files[targets[0]]
    # A SAME-LENGTH mutation: the reader checks `len(body) != expected_bytes or
    # sha256(body) != expected_hash` and Python short-circuits, so appending a
    # byte would only ever exercise the length half. Swapping two digits inside
    # a figure keeps the length identical and forces the digest comparison.
    for a, b in ((b"16", b"61"), (b"12", b"21"), (b"20", b"02"), (b"34", b"43")):
        if a in original:
            files[targets[0]] = original.replace(a, b, 1)
            break
    else:  # pragma: no cover - the fixture always carries one of these
        pytest.fail("no same-length mutation available in the preceding object")
    assert len(files[targets[0]]) == len(original) and files[targets[0]] != original
    wire_witness_nest(monkeypatch, files)
    _pin_scope(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert [w["event_id"] for w in bundle.event_workspaces] == ["evt_cik0001046179_2026q2_results"]
    assert f"{WORKSPACE_UNVERIFIED}.TSM-2026Q1" in bundle.omissions, bundle.omissions
    assert f"{WORKSPACE_UNAVAILABLE}.TSM-2026Q1" not in bundle.omissions


# ─────────────────────────────────────────────────────────────────────────────
# (d) refusals before any reader call
# ─────────────────────────────────────────────────────────────────────────────

def _forbid_reader(monkeypatch) -> None:
    def boom(*_a, **_kw):
        raise AssertionError("reader reached")

    monkeypatch.setattr(reader, "read_current_event_workspace", boom)
    monkeypatch.setattr(reader, "read_event_workspace", boom)
    monkeypatch.setattr(reader, "_fetch_bytes", boom)


def test_system_replay_is_refused_with_identity_vintage_unsupported_before_the_reader(monkeypatch) -> None:
    _forbid_reader(monkeypatch)
    monkeypatch.setattr(loader_module, "resolve_witness_scope",
                        lambda key: pytest.fail("scope resolved for a refused mode"))
    with pytest.raises(ResearchRefusal) as caught:
        load_semiconductor_owner_bundle(
            _query(time_mode="system_replay", source_cutoff="2026-09-01", recorded_cutoff="2026-09-01"),
            rights_snapshot=_SNAPSHOT,
        )
    assert caught.value.code == IDENTITY_VINTAGE_UNSUPPORTED == "identity_vintage_unsupported"


@pytest.mark.parametrize("snapshot", [("", {}), ("only",), (None, {}), "rights_x", (7, {})])
def test_snapshot_without_a_revision_is_unavailable(monkeypatch, snapshot) -> None:
    _forbid_reader(monkeypatch)
    with pytest.raises(BundleUnavailable):
        load_semiconductor_owner_bundle(_query(), rights_snapshot=snapshot)  # type: ignore[arg-type]


def test_loader_never_rereads_the_registry_when_the_shell_supplies_the_snapshot(monkeypatch) -> None:
    _pin_scope(monkeypatch)  # empty cohort: no reader call either
    monkeypatch.setattr(loader_module, "load_registry_snapshot",
                        lambda *a, **kw: pytest.fail("second registry read"))
    _forbid_reader(monkeypatch)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert bundle.rights_revision == "rights_synthetic_snapshot"
    assert bundle.omissions == (PRIVATE_ASSERTIONS_UNBOUND, SLICE_SCOPE_UNOWNED)
    assert bundle.event_workspaces == () and bundle.assertions == ()
    assert bundle.revision_tuple == ()


def test_direct_caller_without_a_snapshot_reads_the_registry_once(monkeypatch) -> None:
    _pin_scope(monkeypatch)
    _forbid_reader(monkeypatch)
    reads: list[int] = []

    def counted(*a, **kw):
        reads.append(1)
        return load_registry_snapshot(*a, **kw)

    monkeypatch.setattr(loader_module, "load_registry_snapshot", counted)
    bundle = load_semiconductor_owner_bundle(_query())
    assert reads == [1] and bundle.rights_revision == load_registry_snapshot()[0]


# ─────────────────────────────────────────────────────────────────────────────
# (e) reader envelopes → rows, tokens, or unavailability
# ─────────────────────────────────────────────────────────────────────────────

def test_reader_raise_is_bundle_unavailable_and_carries_no_message(monkeypatch) -> None:
    _pin_scope(monkeypatch, _TSM)

    def raising(params):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(reader, "read_current_event_workspace", raising)
    with pytest.raises(BundleUnavailable) as caught:
        load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert "secret" not in str(caught.value)


def test_non_mapping_envelope_is_bundle_unavailable(monkeypatch) -> None:
    _pin_scope(monkeypatch, _TSM)
    monkeypatch.setattr(reader, "read_current_event_workspace", lambda params: None)
    with pytest.raises(BundleUnavailable):
        load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)


def test_coverage_absence_is_a_typed_omission_not_a_failure(monkeypatch) -> None:
    _pin_scope(monkeypatch, _TSM)
    monkeypatch.setattr(reader, "read_current_event_workspace",
                        lambda params: {"available": False, "ticker": "TSM",
                                        "note": reader._NOT_COVERED_NOTE})
    monkeypatch.setattr(reader, "read_event_workspace",
                        lambda params: pytest.fail("preceding period read without a current one"))
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert bundle.event_workspaces == ()
    assert bundle.omissions == (PRIVATE_ASSERTIONS_UNBOUND, SLICE_SCOPE_UNOWNED,
                                f"{WORKSPACE_UNAVAILABLE}.TSM")
    assert bundle.revision_tuple == (("identity", "ISS:US-XNYS-TSM=0001046179"),)


@pytest.mark.parametrize("note", [
    "Company Intelligence public source unavailable",
    "event workspace failed immutable receipt verification",
    "event workspace issuer listings do not include the requested ticker",
    "", None,
])
def test_every_other_current_refusal_is_bundle_unavailable(monkeypatch, note) -> None:
    _pin_scope(monkeypatch, _TSM)
    monkeypatch.setattr(reader, "read_current_event_workspace",
                        lambda params: {"available": False, "ticker": "TSM", "note": note})
    with pytest.raises(BundleUnavailable):
        load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)


def test_available_envelope_without_a_workspace_is_bundle_unavailable(monkeypatch) -> None:
    _pin_scope(monkeypatch, _TSM)
    monkeypatch.setattr(reader, "read_current_event_workspace",
                        lambda params: {"available": True, "workspace": "not-a-mapping"})
    with pytest.raises(BundleUnavailable):
        load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)


def test_unprojectable_current_workspace_is_a_typed_omission(monkeypatch) -> None:
    _pin_scope(monkeypatch, _TSM)
    monkeypatch.setattr(reader, "read_current_event_workspace",
                        lambda params: {"available": True, "event_id": "evt_x",
                                        "workspace": {"event_id": "evt_x"}, "receipt": {}})
    monkeypatch.setattr(reader, "read_event_workspace",
                        lambda params: pytest.fail("preceding period read after a refused current"))
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert bundle.event_workspaces == ()
    assert f"{WORKSPACE_UNPROJECTABLE}.evt_x" in bundle.omissions


# ─────────────────────────────────────────────────────────────────────────────
# (f) the real chain: production writer → real reader → projector → composer
# ─────────────────────────────────────────────────────────────────────────────

def test_two_periods_per_witness_through_the_real_reader(monkeypatch, served_nest) -> None:
    _pin_scope(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert [w["event_id"] for w in bundle.event_workspaces] == [
        "evt_cik0001046179_2026q2_results", "evt_cik0001046179_2026q1_results",
    ]
    for workspace in bundle.event_workspaces:
        assert workspace["cik"] == "0001046179"
        assert workspace["company_node_id"] == "co:us:TSM"
        assert "omissions" not in workspace
        assert set(workspace) == {"event_id", "cik", "company_node_id", "fiscal_period",
                                  "guidance", "reported", "lifecycle"}
    assert bundle.omissions == (PRIVATE_ASSERTIONS_UNBOUND, SLICE_SCOPE_UNOWNED)
    kinds = {kind for kind, _ in bundle.revision_tuple}
    assert kinds == {"event", "generation", "identity"}
    assert ("event", "evt_cik0001046179_2026q1_results") in bundle.revision_tuple
    assert bundle.assertions == () and bundle.native_refs == () and bundle.financial_packets == ()
    # four fetches: marker, immutable manifest, current object, preceding object
    assert [url.rsplit("/", 1)[-1] for url in served_nest] == [
        "manifest.json", "manifest.json",
        "evt_cik0001046179_2026q2_results.json", "evt_cik0001046179_2026q1_results.json",
    ]
    assert all(url.startswith(WITNESS_NEST_BASE + "/event_workspaces/") for url in served_nest)


def test_economics_pane_is_ready_from_the_public_half_alone(monkeypatch, served_nest) -> None:
    _pin_scope(monkeypatch, _ON, slice_key="sic_gan_specialty")
    query = _query(slice_key="sic_gan_specialty")
    bundle = load_semiconductor_owner_bundle(query, rights_snapshot=_SNAPSHOT)
    response = compose_semiconductor_research(query, bundle)
    assert response["economics"]["status"] == "ready"
    assert response["economics"]["witness_gate"] == "positive"
    assert response["economics"]["input_refs"] == [
        "evt_cik0001097864_2026q1_results", "evt_cik0001097864_2026q2_results",
    ]
    assert response["summary"]["status"] == "unavailable"
    assert "omitted:private_assertions_unbound" in response["limitations"]
    assert "omitted:slice_scope_unowned" in response["limitations"]
    assert all(_matches_grammar(item) for item in response["limitations"]), response["limitations"]


def test_identity_plane_disagreement_refuses_the_workspace(monkeypatch, served_nest) -> None:
    wrong = WitnessIdentity(ticker="TSM", company_node_id="co:us:TSM",
                            issuer_id="ISS:US-XNYS-TSM", cik="0009999999")
    _pin_scope(monkeypatch, wrong)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert bundle.event_workspaces == ()
    assert f"{IDENTITY_MISMATCH}.TSM" in bundle.omissions
    # The preceding period is never read once the current workspace is refused.
    assert len(served_nest) == 3
    response = compose_semiconductor_research(_query(), bundle)
    assert response["economics"]["status"] == "unavailable"
    assert "omitted:identity_mismatch.TSM" in response["limitations"]


def test_missing_preceding_period_degrades_to_a_typed_omission(monkeypatch, tmp_path) -> None:
    files = build_witness_nest(tmp_path, periods=(2,))
    calls = wire_witness_nest(monkeypatch, files)
    _pin_scope(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)
    assert [w["event_id"] for w in bundle.event_workspaces] == ["evt_cik0001046179_2026q2_results"]
    assert f"{WORKSPACE_UNAVAILABLE}.TSM-2026Q1" in bundle.omissions
    response = compose_semiconductor_research(_query(), bundle)
    assert response["economics"]["status"] == "unavailable"
    assert "witness_economics_missing" in response["limitations"]
    assert len(calls) == 3  # marker, immutable manifest, current object; the alias miss needs no fetch


def test_source_history_proceeds_like_latest_for_public_workspaces(monkeypatch, served_nest) -> None:
    _pin_scope(monkeypatch, _TSM)
    query = _query(time_mode="source_history", source_cutoff="2026-09-01")
    bundle = load_semiconductor_owner_bundle(query, rights_snapshot=_SNAPSHOT)
    assert len(bundle.event_workspaces) == 2
    assert compose_semiconductor_research(query, bundle)["economics"]["status"] == "ready"


def test_coverage_absence_literals_are_notes_the_reader_can_actually_raise() -> None:
    """DRIFT GUARD. The preceding-period classification turns on two literal
    reader notes. Unlike the current-period note the reader exports as
    ``_NOT_COVERED_NOTE``, these are raise-site strings: if one is reworded,
    every genuinely-unpublished period would silently start reporting
    ``workspace_unverified`` (tampering) instead of ``workspace_unavailable``
    (absence), and every test here would stay green because they hardcode the
    same two strings. So assert them against the reader's own source.
    """
    reader_source = Path(reader.__file__).read_text(encoding="utf-8")
    raised: set[str] = set()
    for node in ast.walk(ast.parse(reader_source)):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        call = node.exc
        if not isinstance(call, ast.Call) or not call.args:
            continue
        name = call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, "attr", "")
        if name != "CompanyIntelligenceReadError":
            continue
        first = call.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            raised.add(first.value)
    assert raised, "no CompanyIntelligenceReadError literals found — the guard is void"
    missing = loader_module._PRECEDING_ABSENT_NOTES - raised
    assert not missing, (
        f"the loader treats {sorted(missing)} as the reader's coverage-absence notes, "
        "but the reader no longer raises them — a reword would silently reclassify "
        "every unpublished preceding period as unverified"
    )


def test_an_unpublished_alias_really_returns_a_coverage_absence_note(monkeypatch, served_nest) -> None:
    """The other half of the guard, live: ask the real reader for an alias the
    published manifest does not carry and confirm the note it hands back is one
    the loader classifies as absence."""
    envelope = reader.read_event_workspace({"event_id": "TSM/2019Q3"})
    assert envelope.get("available") is not True
    assert envelope.get("note") in loader_module._PRECEDING_ABSENT_NOTES, envelope


# ─────────────────────────────────────────────────────────────────────────────
# (g) closure — model-facing reader surfaces only, no override, no authority
# ─────────────────────────────────────────────────────────────────────────────

_FORBIDDEN_READER_SURFACES = {
    "fetch_current_workspace_marker", "fetch_current_workspace_marker_raw",
    "fetch_generation_manifest", "fetch_raw_workspace", "load_current_workspace",
    "load_workspace_with_disposition", "find_current_event_id_for_company",
    "read_all_event_source_revisions", "read_event_source_revisions",
    "_load_workspace_snapshot", "_load_event_workspace", "_public_base_url",
    "_fetch_bytes", "read_company_intelligence",
}


def test_loader_touches_only_the_two_model_facing_reader_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    reader_attrs = {
        node.attr for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        and node.value.id == "reader"
    }
    assert reader_attrs == {"read_current_event_workspace", "read_event_workspace", "_NOT_COVERED_NOTE"}
    assert not (reader_attrs & _FORBIDDEN_READER_SURFACES)
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("base_url", "R2_", "os.environ", "open(", "requests.", "import re\n",
                      "can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"):
        assert forbidden not in source, forbidden
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots == {"__future__", "collections", "dataclasses", "typing", "engine"}, sorted(roots)
    # The request never supplies a locator: only slice_key and time_mode are read off the query.
    query_attrs = {
        node.attr for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        and node.value.id == "query"
    }
    assert query_attrs == {"slice_key", "time_mode"}


def test_reader_error_class_is_swallowed_by_the_reader_and_fails_this_loader(monkeypatch, served_nest) -> None:
    """A transport fault inside the reader surfaces as ``available: False`` with
    a failure note (never the coverage note) — the loader turns it into
    BundleUnavailable, not into a silent empty panel."""
    _pin_scope(monkeypatch, _TSM)

    def failing(url, *, limit):
        raise CompanyIntelligenceReadError("Company Intelligence public source unavailable")

    reader.clear_company_intelligence_cache()
    monkeypatch.setattr(reader, "_fetch_bytes", failing)
    with pytest.raises(BundleUnavailable):
        load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)


# ─────────────────────────────────────────────────────────────────────────────
# (h) ONE OWNER-QUALIFIED SNAPSHOT PER COMPARISON
#     Sol #7780 issuecomment-5825621672 item 3; grain fixed by 5825811888
#     item 4 (same publication domain only, never a cross-domain equality).
# ─────────────────────────────────────────────────────────────────────────────

def _second_generation(tmp_dir, *, generated_at: str) -> dict:
    """A SECOND generation of the same witnesses, written by the production
    writer with a different publication clock so its generation_id differs."""
    from engine.company_intelligence.event_workspace import write_workspace_generation
    from tests.semiconductor_research_helpers import nest_files, witness_workspace_payloads

    out = Path(tmp_dir) / "company_intelligence"
    write_workspace_generation(
        out, witness_workspace_payloads(tickers=("TSM",), periods=(1, 2)),
        generated_at=generated_at, status="ready",
    )
    return nest_files(out)


def test_a_publication_flip_between_the_two_reads_withholds_the_comparison(
    monkeypatch, tmp_path,
) -> None:
    """THE A→B TEST. Publication advances between the current read and the
    preceding read, so the two halves describe two different worlds. The panel
    would otherwise present them as one comparison. Real producer, real
    reader, real receipts — only the byte source flips."""
    files_a = _second_generation(tmp_path / "a", generated_at="2026-09-24T15:00:00Z")
    files_b = _second_generation(tmp_path / "b", generated_at="2026-09-24T18:30:00Z")
    assert files_a != files_b, "the two generations must be distinguishable"

    state = {"files": files_a}
    reader.clear_company_intelligence_cache()
    monkeypatch.setattr(reader, "_public_base_url", lambda: WITNESS_NEST_BASE)

    def fetch(url: str, *, limit: int) -> bytes:
        if url not in state["files"]:
            raise CompanyIntelligenceReadError(
                "Company Intelligence public source unavailable")
        return state["files"][url]

    monkeypatch.setattr(reader, "_fetch_bytes", fetch)

    real_current = reader.read_current_event_workspace

    def flipping_current(params):
        envelope = real_current(params)
        # Publication advances A→B the instant the current half is in hand.
        state["files"] = files_b
        reader.clear_company_intelligence_cache()
        return envelope

    monkeypatch.setattr(reader, "read_current_event_workspace", flipping_current)
    _pin_scope(monkeypatch, _TSM)

    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)

    # The current half is served; the preceding half is WITHHELD, not mixed in.
    assert [w["event_id"] for w in bundle.event_workspaces] == [
        "evt_cik0001046179_2026q2_results"]
    assert f"{WORKSPACE_GENERATION_SPLIT}.TSM-2026Q1" in bundle.omissions, bundle.omissions

    # And the withheld period is not named in the revision fingerprint: the
    # guard runs BEFORE admission, so the bundle never advertises a period it
    # does not serve.
    assert not any(
        kind == "event" and value.endswith("2026q1_results")
        for kind, value in bundle.revision_tuple
    ), bundle.revision_tuple

    response = compose_semiconductor_research(_query(), bundle)
    assert response["economics"]["status"] == "unavailable"
    assert "witness_economics_missing" in response["limitations"]
    assert f"omitted:{WORKSPACE_GENERATION_SPLIT}.TSM-2026Q1" in response["limitations"]
    assert all(_matches_grammar(item) for item in response["limitations"])


def test_one_generation_serves_both_halves_and_raises_no_coherence_omission(
    monkeypatch, served_nest,
) -> None:
    """The permit control. The guard must not empty the product: when both
    halves come from ONE generation — the ordinary case, and what the reader's
    manifest cache produces — the comparison is served."""
    _pin_scope(monkeypatch, _TSM)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)

    assert len(bundle.event_workspaces) == 2
    assert not [o for o in bundle.omissions if "generation" in str(o)], bundle.omissions


@pytest.mark.parametrize("receipt", [
    pytest.param({}, id="no-generation-key"),
    pytest.param({"generation_id": ""}, id="empty-generation"),
    pytest.param({"generation_id": None}, id="null-generation"),
    pytest.param({"generation_id": 7}, id="non-string-generation"),
    pytest.param("not-a-mapping", id="non-mapping-receipt"),
])
def test_a_workspace_with_no_qualified_generation_cannot_join_a_comparison(
    monkeypatch, served_nest, receipt,
) -> None:
    """A generation nobody stamped is a snapshot no owner vouches for. It may
    not anchor or join a comparison, whichever half it is."""
    _pin_scope(monkeypatch, _TSM)
    real_prior = reader.read_event_workspace

    def stripped(params):
        envelope = dict(real_prior(params))
        envelope["receipt"] = receipt
        return envelope

    monkeypatch.setattr(reader, "read_event_workspace", stripped)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)

    assert [w["event_id"] for w in bundle.event_workspaces] == [
        "evt_cik0001046179_2026q2_results"]
    assert f"{WORKSPACE_GENERATION_UNQUALIFIED}.TSM-2026Q1" in bundle.omissions


def test_the_current_half_without_a_generation_cannot_anchor_either(
    monkeypatch, served_nest,
) -> None:
    """Symmetry: an unqualified CURRENT workspace is not a base to compare
    against, so the preceding half is withheld even though ITS receipt is
    perfectly good."""
    _pin_scope(monkeypatch, _TSM)
    real_current = reader.read_current_event_workspace

    def stripped(params):
        envelope = dict(real_current(params))
        envelope["receipt"] = {}
        return envelope

    monkeypatch.setattr(reader, "read_current_event_workspace", stripped)
    bundle = load_semiconductor_owner_bundle(_query(), rights_snapshot=_SNAPSHOT)

    assert [w["event_id"] for w in bundle.event_workspaces] == [
        "evt_cik0001046179_2026q2_results"]
    assert f"{WORKSPACE_GENERATION_UNQUALIFIED}.TSM-2026Q1" in bundle.omissions


def test_the_coherence_rule_is_scoped_to_this_publication_domain():
    """5825811888 item 4 forbids a general equality rule over generation
    strings from independent publication domains: they share no clock to be
    equal in. This guard must therefore compare only the two event-workspace
    receipts it reads itself, and must not reach for any other ref's
    generation."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "_generation_of(current)" in source and "_generation_of(prior)" in source
    # exactly two call sites: the two halves of ONE event-workspace comparison
    assert source.count("_generation_of(") == 3  # the def plus its two uses
