"""tests/test_robotics_owner_bundle.py — the Robotics owner-bundle loader.

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier #7908).
``engine/market_ontology/robotics_owner_bundle.py`` is the ``load_bundle``
callable the shared closed registration (#7870 hook 1) names for Robotics. It
serves NOTHING in v1 — the private half is unbound (R4/R5) and no declared
witness cohort owns the Robotics slices — so what these tests pin is that the
emptiness is DECLARED and survives to the wire, that the loader invents no
owner surface to fill the hole, that it reads nothing from the request, and
that RBV-27's rule (never name a withheld family) holds on the served payload.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

try:  # both need #7870's shared assertion contract (Task 1); main alone must still collect
    import engine.market_ontology.robotics_owner_bundle as loader
    import engine.market_ontology.robotics_theme_research as robotics
    HAS_SHARED = True
except ImportError:  # pragma: no cover - carrier base without the shared foundation
    loader = None  # type: ignore[assignment]
    robotics = None  # type: ignore[assignment]
    HAS_SHARED = False

pytestmark = pytest.mark.xfail(
    condition=not HAS_SHARED,
    strict=True,
    reason="engine.theme_graph.curation_assertion (#7870 shared foundation) is not on "
           "this base; flips loudly the day it lands",
)

ROOT = Path(__file__).resolve().parents[1]

#: A snapshot shaped exactly like ``rights.load_registry_snapshot()`` returns.
FAKE_SNAPSHOT = ("rights_test_0123456789abcdef", {})

#: Every field of the bundle that would carry an owner input.
OWNER_FIELDS = (
    "revision_tuple", "assertions", "identity_results", "event_workspaces",
    "financial_packets", "interpretation_blocks", "native_refs",
)


def _query(slice_key="precision_motion", view="composition", time_mode="latest",
           source_cutoff=None, recorded_cutoff=None):
    return robotics.ResearchQuery("robotics_automation", slice_key, view, time_mode,
                                  source_cutoff, recorded_cutoff)


def _bundle(**kwargs):
    return loader.load_robotics_owner_bundle(_query(**kwargs), rights_snapshot=FAKE_SNAPSHOT)


# -- what it serves ---------------------------------------------------------

def test_bundle_declares_both_halves_absent():
    """No owner input, and the two omissions that say which halves are missing."""
    bundle = _bundle()
    for field in OWNER_FIELDS:
        assert getattr(bundle, field) == (), f"{field} must carry no owner input"
    assert bundle.omissions == (loader.PRIVATE_ASSERTIONS_UNBOUND,
                                loader.PUBLIC_COHORT_UNOWNED)


def test_the_emptiness_predicate_has_teeth():
    """A control on the assertion ABOVE, not coverage of the loader: a single
    fabricated row in any owner field flips the predicate, so
    ``test_bundle_declares_both_halves_absent`` cannot pass vacuously. It is
    expected to survive every mutation of the loader — an instrument that fired
    when the loader changed would not be measuring the predicate. Do not count
    it toward loader coverage (R4-reg review, nit 3)."""
    bundle = _bundle()
    for field in OWNER_FIELDS:
        fabricated = dataclasses.replace(bundle, **{field: ({"fabricated": True},)})
        assert getattr(fabricated, field) != (), "control setup failed"
        with pytest.raises(AssertionError):
            for probe in OWNER_FIELDS:
                assert getattr(fabricated, probe) == ()


def test_rights_revision_is_the_snapshot_the_shell_enforced_with():
    """The fingerprinted revision must equal the ENFORCED one, so the shell's
    one read is the one that lands in the bundle."""
    assert _bundle().rights_revision == FAKE_SNAPSHOT[0]


def test_a_direct_caller_gets_the_real_registry_revision():
    """``rights_snapshot=None`` reads the registry itself (direct callers)."""
    from engine.theme_graph.rights import load_registry_snapshot
    expected, _families = load_registry_snapshot()
    bundle = loader.load_robotics_owner_bundle(_query(), rights_snapshot=None)
    assert bundle.rights_revision == expected
    assert bundle.rights_revision


# -- what it reads ----------------------------------------------------------

def test_the_loader_reads_nothing_from_the_request():
    """No request field narrows anything, because there is no surface to
    narrow. Every slice x view x time_mode yields an identical bundle."""
    seen = set()
    for slice_key in robotics.SLICES:
        for view in robotics.VIEWS:
            for time_mode in ("latest", "source_history", "system_replay"):
                bundle = _bundle(slice_key=slice_key, view=view, time_mode=time_mode,
                                 source_cutoff="2026-09-01T00:00:00Z",
                                 recorded_cutoff="2026-09-02T00:00:00Z")
                seen.add(dataclasses.astuple(bundle))
    assert len(seen) == 1, "a request field changed the bundle"
    assert len(robotics.SLICES) * len(robotics.VIEWS) * 3 == 30


# -- when it cannot serve ---------------------------------------------------

@pytest.mark.parametrize("bad", [
    (), ("only-one",), ("rev", {}, "extra"), ("", {}), (None, {}), (7, {}),
    "rights_str", ["rev", {}], {"revision": "rev"}, 0,
])
def test_a_snapshot_without_a_revision_cannot_serve(bad):
    """The revision feeds the composer's generation fingerprint, so serving
    without one would fingerprint a response against nothing: the one genuine
    BundleUnavailable."""
    with pytest.raises(loader.BundleUnavailable):
        loader.load_robotics_owner_bundle(_query(), rights_snapshot=bad)


def test_coverage_absence_is_never_a_refusal():
    """The shared 503's own contract reserves it for a broken owner, never for
    an empty one, so an EMPTY bundle must still serve. Previously this asserted
    the rights revision, character-for-character what
    ``test_rights_revision_is_the_snapshot_the_shell_enforced_with`` already
    asserts (R4-reg review, nit 4); it now exercises the reserved behaviour
    itself across every view and time mode."""
    unavailable = getattr(loader, "BundleUnavailable")
    for view in robotics.VIEWS:
        for mode in ("latest", "source_history", "system_replay"):
            try:
                bundle = _bundle(view=view, time_mode=mode)
            except unavailable as exc:  # pragma: no cover - the defect this pins
                pytest.fail(f"coverage absence raised the 503 for {view}/{mode}: {exc}")
            assert bundle.omissions, f"{view}/{mode} served without declaring absence"
            assert all(getattr(bundle, f) == () for f in OWNER_FIELDS)



def test_r5_cannot_admit_assertions_without_facing_replay_vintage():
    """R5's tripwire, and the reason no blanket ``system_replay`` refusal is
    added here.

    The composer's ``_refuse_unsupported_identity_vintage`` iterates
    ``bundle.identity_results``. This loader hard-codes that field to ``()`` and
    so does ``semiconductor_owner_bundle`` (``:334``, ``:392``) — which is why
    ITS author added an up-front refusal instead of relying on the guard. So the
    guard is inert for both verticals, and admitting assertions would NOT wake
    it: ``assertions`` and ``identity_results`` are separate fields. (Proven by
    experiment in the R4-reg independent review, which falsified the claim that
    the guard "will begin firing on its own once R5 admits real evidence".)

    Today the bundle is empty, so nothing is at risk and this passes. The day R5
    admits any owner material it goes red unless R5 also does one of the two
    lawful things: populate ``identity_results`` with real vintages, or refuse
    ``system_replay`` up front the way semiconductor does.
    """
    try:
        bundle = _bundle(time_mode="system_replay")
    except robotics.ResearchRefusal:
        return  # the loader refuses replay outright — the other lawful answer
    # NB: the except clause is deliberately NOT ``Exception``. A bare except here
    # read any error as "it refuses", which both masked a real loader fault and
    # made this test XPASS on the carrier-alone base where the module cannot
    # import at all — caught by the strict-xfail gate on first run.
    if bundle.identity_results != ():
        return  # vintages present, so the composer guard can do its job
    admitted = [
        field for field in OWNER_FIELDS
        if field != "identity_results" and getattr(bundle, field) != ()
    ]
    assert not admitted, (
        f"owner material {admitted} is served under system_replay while "
        "identity_results is empty, so the composer's vintage guard cannot fire: "
        "populate identity_results with real vintages, or refuse system_replay "
        "up front as semiconductor_owner_bundle.py:369-370 does"
    )

# -- what a member actually receives ---------------------------------------

def test_the_served_response_states_its_own_emptiness():
    """Through the REAL composer: the payload says it is serving nothing, and
    claims no authority while doing so."""
    response = robotics.compose_robotics_research(_query(), _bundle())
    coverage = response["authorized_coverage"]
    assert coverage["status"] == "degraded"
    assert coverage["selected"] == 0
    assert coverage["input_refs"] == []
    assert response["limitations"] == ["rights_partial", "slice_scope_unowned"]
    assert response["companies"]["rows"] == []
    assert response["evidence_refs"] == []
    assert set(response["authority"].values()) == {False}
    assert response["schema"] == robotics.SCHEMA_ID
    assert response["definition_version"] == robotics.DEFINITION_VERSION


def test_rbv27_the_response_never_names_a_withheld_family():
    """RBV-27: a partial-rights state shows that it is partial and NEVER names
    what is withheld. The composer collapses every omission into the single
    ``rights_partial`` token, so neither of the loader's tokens may appear
    anywhere in the served bytes."""
    for view in robotics.VIEWS:
        served = json.dumps(
            robotics.compose_robotics_research(_query(view=view), _bundle()),
            ensure_ascii=False, sort_keys=True)
        assert loader.PRIVATE_ASSERTIONS_UNBOUND not in served
        assert loader.PUBLIC_COHORT_UNOWNED not in served
        assert "rights_partial" in served


def test_the_response_is_pagination_stable_while_empty():
    """An empty companies list must not become a refusal under any page the
    shell may ask for. Paging past the first page requires pinning the
    generation (shared contract: ``expected_generation_required``), so this
    also pins that an empty bundle's generation is stable enough to page."""
    bundle = _bundle()
    first = robotics.compose_robotics_research(_query(), bundle)
    generation = first["generation"]
    assert first["companies"]["rows"] == []
    for offset, limit in ((10, 1), (99, 100)):
        query = dataclasses.replace(_query(), offset=offset, limit=limit,
                                    expected_generation=generation)
        response = robotics.compose_robotics_research(query, bundle)
        assert response["companies"]["rows"] == []
        assert response["generation"] == generation


# -- what it must not drag in ----------------------------------------------

def test_the_loader_pulls_no_reader_or_network_stack():
    """Symmetric to #7870's ``test_registry_import_closure_stays_light``: the
    registration binds this loader lazily precisely so producers importing the
    registry for mount copy never pull a reader. Importing it must not pull one
    either, or the laziness buys nothing."""
    code = (
        "import sys; import engine.market_ontology.robotics_owner_bundle; "
        "print(sorted(m for m in ('requests', 'pandas', 'pyarrow', 'numpy', 'fastapi', "
        "'jinja2', 'engine.neuralweb.company_intelligence_reader') if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True,
                            text=True, cwd=str(ROOT), timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]", result.stdout


def test_the_module_creates_no_robotics_side_owner_plane():
    """Master packet §3: no Robotics-specific store, bucket, publisher,
    evidence ledger or scheduler. This is a DRIFT TRIPWIRE, not a proof: a
    substring scan is defeatable (``from pathlib import Path as _P``, a split
    ``import_module("sqlite"+"3")``, ``getattr(builtins, "op"+"en")`` all pass
    it), so it catches the ordinary way such a plane gets added and nothing
    more. The earlier claim that the loader "reads exactly one owner surface and
    nothing else" overstated what this can give (R4-reg review, nit 5); the
    import-closure test next door is the real instrument."""
    source = Path(loader.__file__).read_text(encoding="utf-8")
    body = source.split('"""', 2)[2]  # laws are discussed in the docstring
    for forbidden in ("sqlite3", "boto3", "requests", "open(", "Path(",
                      "urlopen", "subprocess", "schedule", "parquet"):
        assert forbidden not in body, f"loader body reaches for {forbidden}"
    assert "load_registry_snapshot" in body
