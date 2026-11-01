"""V0 recovery and correction proofs (SPEC_V0 §3 items 1 and 4) through served paths.

Item 1 (interrupted publication) proves the two existing whole-generation
publication paths end to end, on real disk, through the served API:

- ``scripts/build_capital_structure_state.py::build_from_disk`` publishes
  ``state_bundle.json`` through ``_atomic_write_one`` (same-directory stage,
  fsync, then one ``os.replace`` pointer flip);
- ``scripts/build_capital_structure_projection.py::_promote_pair`` publishes the
  canonical/public pair with per-target backups and rollback, and
  ``_recover_projection_pair`` heals a hard stop between the two replaces.

An interruption is simulated by raising from ``os.replace`` after the staged
payload write and before the target replace.  For the pair path the raise is a
``BaseException`` (not ``Exception``) so it models a process stop exactly as
``_promote_pair``'s docstring frames it: an ordinary exception is rolled back
in-process, while a process stop "cannot be caught between replaces" and is
closed by the next invocation's recovery.

Item 4 (correction) proves A46's second half: an amended filing (the S-1 ->
S-1/A amendment from the registration integration's own lifecycle fixture —
the packet's LPTH archetype: a registration fact later amended by a filing
whose house-knowledge clock is after the cutoff) changes the current view
only; the then-known view at the earlier cutoff is byte-identical before and
after, once the fields the contract defines as echoing the served generation
are removed (each named and cited below).

SPEC_V0 §3 items 2 and 3 need the U2 scenario store and belong to other
lanes; they are deliberately absent here.  No new lock, ledger, queue or
monitor is created: every case drives the existing paths on fixture state in
tmp_path, offline.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi", reason="capital structure API tests need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.capital_structure as api  # noqa: E402
import scripts.build_capital_structure_state as state_builder  # noqa: E402
from engine.capital_structure.ingestion_health import (  # noqa: E402
    evaluate_health,
    write_health,
)
from engine.capital_structure.projection import (  # noqa: E402
    build_projection_bundle,
    validate_projection_bundle,
)
from engine.capital_structure.rule_applicability import (  # noqa: E402
    load_rule_applicability_pack,
)
from engine.capital_structure.state_bundle import (  # noqa: E402
    build_state_bundle,
    validate_state_bundle,
)
from engine.capital_structure.verified_projection_generation import (  # noqa: E402
    VerifiedProjectionGeneration,
)
from scripts.build_capital_structure_projection import (  # noqa: E402
    _recover_projection_pair,
    build_from_disk as build_projection_pair,
)
from scripts.compile_capital_structure_events import compile_from_disk  # noqa: E402
from tests.test_build_capital_structure_projection import (  # noqa: E402
    _compiled_root,
    _manifest,
)
from tests.test_capital_structure_registration_integration import (  # noqa: E402
    AS_OF,
    GENERATED_AT,
    _s1_filed_amended_effective_withdrawn,
)
from tests.test_capital_structure_state_api import _write_json  # noqa: E402
from tests.test_capital_structure_state_bundle import (  # noqa: E402
    HEALTH,
    ISSUER_ONE,
    _telemetry,
)

PREFIX = "/api/capital-structure/v1"
STATE_FILENAME = "state_bundle.json"
PUBLIC_NAME = "latest.json"
STATE_GENERATED_AT = "2026-10-14T07:00:00Z"

#: The disk-fixture timeline.  G1 is compiled and published at T1; the amended
#: generation is compiled at T2 (> every G1 clock), so its bundle would be a new
#: generation if its pointer flip ever landed.
T1_COMPILE = "2026-08-05T00:00:00Z"
T1_HEALTH = "2026-08-05T00:00:01Z"
T1_PAIR_AT = "2026-08-05T01:00:00Z"
T1_STATE_AT = "2026-08-05T02:00:00Z"
T2_COMPILE = "2026-08-06T12:00:00Z"
T2_HEALTH = "2026-08-06T12:00:01Z"
T2_PAIR_AT = "2026-08-06T13:00:00Z"
T2_STATE_AT = "2026-08-06T14:00:00Z"

#: Item 4: the S-1 original is house knowledge 2026-08-01T18:00:00Z; the S-1/A
#: amendment arrives 2026-08-03T12:00:00Z (its ``point_in_time.available_at``).
#: T0 sits strictly between, so the then-known view at T0 predates the amendment.
AMENDMENT_AVAILABLE_AT = "2026-08-03T12:00:00Z"
CUTOFF_T0 = "2026-08-02T00:00:00Z"

#: Fields the contract defines as echoing the served generation; these and only
#: these may differ between two then-known responses taken at the same cutoff
#: across a republication, and they are removed before the byte comparison.
#:
#: - ``view.generation_id`` — the echoed request identity carries the SERVED
#:   state bundle's id: ``app.capital_structure._view``'s ``generation_id``
#:   entry is fed ``str(bundle["generation_id"])`` from ``_state_view``.
#: - ``view.state_id`` — same echo dict; the derived then-known record's
#:   ``state_id`` is "a deterministic function of (generation, cutoff)"
#:   (``engine/capital_structure/state_bundle.py::then_known_state`` docstring),
#:   so a republication moves it without moving the cutoff view.
#: - ``family.provenance.generation_id`` /
#:   ``family.provenance.artifact_sha256`` — the derived family's provenance
#:   rides the input bindings, which ``then_known_state`` reuses "verbatim"
#:   from the served bundle (state_bundle.py's docstring lines 1111-1112,
#:   applied by ``CapitalInputs(bindings=inputs.bindings, ...)`` in the same
#:   function).
ECHO_PATHS = (
    "view.generation_id",
    "view.state_id",
    "family.provenance.generation_id",
    "family.provenance.artifact_sha256",
)

_STATE_NOT_BOUND = "state generation does not bind served projection"


class _InterruptedPublication(BaseException):
    """The simulated process stop.  BaseException on purpose: `_promote_pair`'s
    `except Exception` rollback must NOT catch it — that is what makes the
    resulting on-disk state identical to a real stop between the two
    replaces."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _publish_first_generation(tmp_path: Path) -> dict[str, Any]:
    """One good projection pair plus one good state bundle on a real disk root."""
    root = _compiled_root(tmp_path)
    compile_from_disk(root=root, generated_at=T1_COMPILE)
    write_health(
        evaluate_health(root, generated_at=T1_HEALTH),
        root / "health.json",
    )
    canonical = root / "projection.json"
    public = tmp_path / "site" / "capital-structure-data" / PUBLIC_NAME
    build_projection_pair(
        root=root,
        canonical_path=canonical,
        public_path=public,
        generated_at=T1_PAIR_AT,
    )
    state_builder.build_from_disk(root=root, generated_at=T1_STATE_AT)
    state_bytes = (root / STATE_FILENAME).read_bytes()
    return {
        "root": root,
        "canonical": canonical,
        "public": public,
        "state_bytes": state_bytes,
        "state_id": str(json.loads(state_bytes.decode("utf-8"))["generation_id"]),
    }


def _amend_generation(root: Path) -> None:
    """Compile the amended generation and bind health to it (the nightly order)."""
    compile_from_disk(root=root, generated_at=T2_COMPILE)
    write_health(
        evaluate_health(root, generated_at=T2_HEALTH),
        root / "health.json",
    )


@pytest.fixture(scope="module")
def pack():
    return load_rule_applicability_pack()


@pytest.fixture()
def api_client():
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "paid-user"}
    with TestClient(app) as client:
        yield client
    api._reset_cache()
    api._reset_state_cache()


def _point_api_at(
    monkeypatch: pytest.MonkeyPatch, canonical: Path, state_path: Path
) -> None:
    monkeypatch.setattr(api, "PROJECTION_PATH", canonical)
    monkeypatch.setattr(api, "STATE_PATH", state_path)
    api._reset_cache()
    api._reset_state_cache()


def _interrupt_replace_at(
    monkeypatch: pytest.MonkeyPatch, target_name: str
) -> None:
    """Raise from ``os.replace`` when the named target is about to be flipped."""
    real_replace = os.replace

    def interrupting_replace(source, target):  # noqa: ANN001 - os.replace signature
        if Path(target).name == target_name:
            raise _InterruptedPublication(
                f"simulated process stop before the {target_name} pointer flip"
            )
        return real_replace(source, target)

    monkeypatch.setattr(os, "replace", interrupting_replace)


def _staged_or_backup_leftovers(*directories: Path) -> list[str]:
    names: list[str] = []
    for directory in directories:
        for entry in sorted(directory.iterdir()):
            name = entry.name
            if name.endswith(".tmp") or ".backup-" in name or ".publish-" in name:
                names.append(str(entry))
    return names


# ---------------------------------------------------------------------------
# Item 1 — interrupted publication, state bundle path
# ---------------------------------------------------------------------------


def test_v0_interrupted_state_publication_serves_prior_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_client: TestClient
) -> None:
    published = _publish_first_generation(tmp_path)
    root: Path = published["root"]
    canonical: Path = published["canonical"]
    public: Path = published["public"]
    g1_state: bytes = published["state_bytes"]
    g1_id: str = published["state_id"]
    state_path = root / STATE_FILENAME

    # (a) A re-publication of the SAME generation, interrupted after the staged
    # payload write and before the pointer flip.  The root stays consistent, so
    # the API must keep serving the prior generation by id.
    _interrupt_replace_at(monkeypatch, STATE_FILENAME)
    with pytest.raises(_InterruptedPublication):
        state_builder.build_from_disk(root=root, generated_at=T2_STATE_AT)
    monkeypatch.undo()

    assert state_path.read_bytes() == g1_state, (
        "an interrupted state publication moved the served generation"
    )
    _point_api_at(monkeypatch, canonical, state_path)
    served = api_client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert served.status_code == 200, served.text
    assert served.json()["view"]["generation_id"] == g1_id

    # (b) The amended generation, published in the nightly order (pair first),
    # with the state pointer flip interrupted.  The torn root — new projection,
    # prior state bundle — must be refused as a whole, never half-served, and
    # the served state file must still be the prior generation byte for byte.
    _amend_generation(root)
    build_projection_pair(
        root=root,
        canonical_path=canonical,
        public_path=public,
        generated_at=T2_PAIR_AT,
    )
    _interrupt_replace_at(monkeypatch, STATE_FILENAME)
    with pytest.raises(_InterruptedPublication):
        state_builder.build_from_disk(root=root, generated_at=T2_STATE_AT)
    monkeypatch.undo()

    assert state_path.read_bytes() == g1_state, (
        "an interrupted state publication moved the served generation"
    )
    _point_api_at(monkeypatch, canonical, state_path)
    torn = api_client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert torn.status_code == 503, torn.text
    assert torn.json()["detail"] == _STATE_NOT_BOUND
    assert _staged_or_backup_leftovers(root) == []


def test_v0_interrupted_projection_promotion_serves_prior_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_client: TestClient
) -> None:
    published = _publish_first_generation(tmp_path)
    root: Path = published["root"]
    canonical: Path = published["canonical"]
    public: Path = published["public"]
    g1_public: bytes = published["public"].read_bytes()
    g1_canonical: bytes = canonical.read_bytes()

    # The amended generation is compiled and health-bound first (the nightly
    # order), then its pair promotion is stopped between the two replaces: the
    # canonical replace has landed, the final replace has not.
    _amend_generation(root)
    _interrupt_replace_at(monkeypatch, PUBLIC_NAME)
    with pytest.raises(_InterruptedPublication):
        build_projection_pair(
            root=root,
            canonical_path=canonical,
            public_path=public,
            generated_at=T2_PAIR_AT,
        )
    monkeypatch.undo()

    # The artifact the site serves is the prior publication, byte-identical.
    assert public.read_bytes() == g1_public
    # The canonical copy holds the OTHER complete payload — the documented gap a
    # process stop leaves behind ("A process stop cannot be caught between
    # replaces; startup recovery closes that gap on the next invocation" —
    # _promote_pair docstring).  It is whole and valid, never a half file.
    gap_canonical = canonical.read_bytes()
    assert gap_canonical != g1_canonical
    gap_payload = json.loads(gap_canonical.decode("utf-8"))
    validate_projection_bundle(gap_payload)
    # No staged or backup file survives the stop (_promote_pair's finally).
    assert _staged_or_backup_leftovers(root) == []
    assert _staged_or_backup_leftovers(public.parent) == []
    # The torn root is refused as a whole: the API never serves a state whose
    # projection binding moved under it (_bound_state in app/capital_structure.py
    # — the bundle binds the prior projection_generation_id, the canonical file
    # carries the amended one).
    _point_api_at(monkeypatch, canonical, root / STATE_FILENAME)
    torn = api_client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert torn.status_code == 503, torn.text
    assert torn.json()["detail"] == _STATE_NOT_BOUND

    # The pair is recoverable by the existing path, deterministically, to the
    # canonical copy ("The canonical copy wins when two individually valid
    # payloads differ because normal promotion always replaces it first." —
    # _recover_projection_pair docstring).
    assert _recover_projection_pair(canonical, public) is True
    assert canonical.read_bytes() == gap_canonical
    assert public.read_bytes() == gap_canonical


def test_v0_projection_pair_recovery_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published = _publish_first_generation(tmp_path)
    root: Path = published["root"]
    canonical: Path = published["canonical"]
    public: Path = published["public"]

    # Produce the exact hard-stop gap: canonical replaced, public not.
    _amend_generation(root)
    _interrupt_replace_at(monkeypatch, PUBLIC_NAME)
    with pytest.raises(_InterruptedPublication):
        build_projection_pair(
            root=root,
            canonical_path=canonical,
            public_path=public,
            generated_at=T2_PAIR_AT,
        )
    monkeypatch.undo()
    gap_canonical = canonical.read_bytes()
    gap_payload = json.loads(gap_canonical.decode("utf-8"))
    assert gap_payload["generated_at"] == T2_PAIR_AT

    # "The canonical copy wins when two individually valid payloads differ
    # because normal promotion always replaces it first."  (_recover_projection_pair
    # docstring, scripts/build_capital_structure_projection.py)
    assert _recover_projection_pair(canonical, public) is True
    assert canonical.read_bytes() == gap_canonical
    assert public.read_bytes() == gap_canonical

    # Deterministic: a healed pair is left alone, and the rule does not depend
    # on invocation order or repetition.
    assert _recover_projection_pair(canonical, public) is False
    assert canonical.read_bytes() == gap_canonical
    assert public.read_bytes() == gap_canonical


def test_v0_no_staged_or_backup_file_is_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_client: TestClient
) -> None:
    published = _publish_first_generation(tmp_path)
    root: Path = published["root"]
    canonical: Path = published["canonical"]
    public: Path = published["public"]
    g1_state: bytes = published["state_bytes"]
    g1_id: str = published["state_id"]
    g1_public = public.read_bytes()
    state_path = root / STATE_FILENAME

    # State path: interrupt the same-generation re-publication at the flip.
    _interrupt_replace_at(monkeypatch, STATE_FILENAME)
    with pytest.raises(_InterruptedPublication):
        state_builder.build_from_disk(root=root, generated_at=T2_STATE_AT)
    monkeypatch.undo()

    # Pair path: interrupt the amended pair at the final replace.
    _amend_generation(root)
    _interrupt_replace_at(monkeypatch, PUBLIC_NAME)
    with pytest.raises(_InterruptedPublication):
        build_projection_pair(
            root=root,
            canonical_path=canonical,
            public_path=public,
            generated_at=T2_PAIR_AT,
        )
    monkeypatch.undo()

    # No staged, backup or publish-temp file remains readable anywhere the
    # served artifacts live, and every served artifact is still exactly the
    # prior publication's bytes — no leftover can be mistaken for a generation.
    assert _staged_or_backup_leftovers(root) == []
    assert _staged_or_backup_leftovers(public.parent) == []
    assert state_path.read_bytes() == g1_state
    assert public.read_bytes() == g1_public

    # And the API answers from that state file alone: the pair is torn here, so
    # the bind is refused whole rather than half-served, while the served state
    # bytes still decode to the prior generation's id.
    _point_api_at(monkeypatch, canonical, state_path)
    torn = api_client.get(f"{PREFIX}/issuers/{ISSUER_ONE}/state")
    assert torn.status_code == 503, torn.text
    assert torn.json()["detail"] == _STATE_NOT_BOUND
    served_state = json.loads(state_path.read_bytes().decode("utf-8"))
    assert served_state["generation_id"] == g1_id


# ---------------------------------------------------------------------------
# Item 4 — correction: an amendment after the cutoff changes the current view
# only (the served-API form of the LPTH archetype)
# ---------------------------------------------------------------------------


def _built_amendment_fixtures(pack: Any, tmp_path: Path) -> dict[str, Any]:
    """G1 (original only) and G2 (original + its S-1/A amendment), built,
    validated, and serialized through the same builders the state API suite
    uses.  Returns per phase the verified generation plus the served bodies."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    original, amendment = events[0], events[1]
    amend_edge = edges[0]
    resolved_row = _resolved_evidence_row(original)

    def build(event_rows, edge_rows, label):
        telemetry = _telemetry(event_rows, edge_rows)
        telemetry["counts"] = {
            "event_versions": len(event_rows),
            "event_edges": len(edge_rows),
            "review_queue": 0,
        }
        generation = VerifiedProjectionGeneration(
            tuple(event_rows), tuple(edge_rows), (), telemetry
        )
        projection = build_projection_bundle(
            list(event_rows),
            list(edge_rows),
            (),
            telemetry,
            as_of=AS_OF,
            generated_at=GENERATED_AT,
        )
        projection_body = _write_json(tmp_path / f"{label}-projection.json", projection)
        bundle = build_state_bundle(
            generation=generation,
            projection=projection,
            health=HEALTH,
            rule_pack=pack,
            as_of=AS_OF,
            generated_at=STATE_GENERATED_AT,
            projection_sha256=_sha256(projection_body.encode("utf-8")),
            source_manifests=(resolved_row,),
        )
        validate_state_bundle(bundle)
        state_body = _write_json(tmp_path / f"{label}-state.json", bundle)
        return {
            "generation": generation,
            "projection_body": projection_body,
            "state_body": state_body,
        }

    return {
        "before": build([original], [], "before"),
        "after": build([original, amendment], [amend_edge], "after"),
    }


def _resolved_evidence_row(event: dict[str, Any]) -> dict[str, Any]:
    """The same resolved evidence row the state API suite binds: the projection
    suite's manifest builder by name, with the event's own evidence identity —
    no fixture body is copied here."""
    first = event["evidence"][0]
    row = _manifest(role="primary")
    return {
        **row,
        "manifest_id": first["manifest_id"],
        "spans": [
            {
                **row["spans"][0],
                "span_id": first["span_id"],
                "text_sha256": first["text_sha256"],
            }
        ],
    }


def _serve_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    holder: dict[str, Any],
    fixture: dict[str, Any],
) -> TestClient:
    """Publish one built generation over the served paths and wire the API to
    it exactly the way the state API suite's ``served`` fixture does."""
    projection_path = tmp_path / "projection.json"
    state_path = tmp_path / STATE_FILENAME
    projection_path.write_text(fixture["projection_body"], encoding="utf-8")
    state_path.write_text(fixture["state_body"], encoding="utf-8")
    holder["generation"] = fixture["generation"]

    def published_generation():
        return holder["generation"]

    monkeypatch.setattr(api, "PROJECTION_PATH", projection_path)
    monkeypatch.setattr(api, "STATE_PATH", state_path)
    monkeypatch.setattr(api, "_load_generation", published_generation)
    api._reset_cache()
    api._reset_state_cache()
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "paid-user"}
    return TestClient(app)


def _then_known_registration(client: TestClient, cutoff: str):
    response = client.get(
        f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"
        f"?mode=then_known&cutoff={cutoff}"
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_v0_amendment_after_cutoff_changes_current_view_only(
    pack, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = _built_amendment_fixtures(pack, tmp_path)
    holder: dict[str, Any] = {}
    route = f"{PREFIX}/issuers/{ISSUER_ONE}/state/registration"

    client = _serve_phase(tmp_path, monkeypatch, holder, fixtures["before"])
    before_current = client.get(route)
    assert before_current.status_code == 200, before_current.text
    before = before_current.json()

    # The amendment arrives: the amended generation is published over the same
    # served paths (a real rebuild), exactly as a correction lands.
    client = _serve_phase(tmp_path, monkeypatch, holder, fixtures["after"])
    after_current = client.get(route)
    assert after_current.status_code == 200, after_current.text
    after = after_current.json()

    # The amended field, quoted before and after: the registration path's
    # amendment chain is empty before the S-1/A arrives and carries exactly the
    # amending filing afterwards.
    before_chain = before["paths"][0]["amendment_chain"]
    after_chain = after["paths"][0]["amendment_chain"]
    assert before_chain == []
    assert len(after_chain) == 1, f"after amendment_chain: {after_chain!r}"
    entry = after_chain[0]
    assert entry["form"] == "S-1/A"
    assert entry["accession"] == "0000000001-26-000002"
    assert entry["mastermind_available_at"] == AMENDMENT_AVAILABLE_AT
    assert entry["relationship"]["relationship"] == "amendment_of"
    # Its supporting carriers move with it: one interval becomes two and the
    # observed registration state is re-derived.
    assert len(before["paths"][0]["intervals"]) == 1
    assert len(after["paths"][0]["intervals"]) == 2
    assert (
        before["paths"][0]["observed_registration_state"]
        != after["paths"][0]["observed_registration_state"]
    )
    # And the view answers as the current mode over the amended generation.
    assert before["view"]["mode"] == "current"
    assert after["view"]["mode"] == "current"
    assert after["view"]["generation_id"] != before["view"]["generation_id"]


def test_v0_then_known_at_prior_cutoff_is_byte_identical_after_amendment(
    pack, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = _built_amendment_fixtures(pack, tmp_path)
    holder: dict[str, Any] = {}

    client = _serve_phase(tmp_path, monkeypatch, holder, fixtures["before"])
    before_view = _then_known_registration(client, CUTOFF_T0)
    assert before_view["paths"][0]["amendment_chain"] == []

    client = _serve_phase(tmp_path, monkeypatch, holder, fixtures["after"])
    after_view = _then_known_registration(client, CUTOFF_T0)
    assert after_view["paths"][0]["amendment_chain"] == []

    # Classify every difference between the two served responses.  Anything
    # outside the contract's served-generation echo set is a defect: a later
    # correction must never rewrite what was known at an earlier cutoff.
    unexpected = [
        path
        for path in _differing_paths(before_view, after_view)
        if path not in ECHO_PATHS
    ]
    if unexpected:
        raise AssertionError(
            "then-known view at cutoff "
            f"{CUTOFF_T0} changed outside the served-generation echo fields "
            f"{list(ECHO_PATHS)}: unexpected paths {unexpected}; "
            f"before sha256 {_sha256(_canonical(before_view))}, "
            f"after sha256 {_sha256(_canonical(after_view))}"
        )

    # With exactly the echo fields removed (each named and cited at
    # ECHO_PATHS), the two served responses are byte-identical canonical JSON.
    stripped_before = _canonical(_without_paths(before_view, ECHO_PATHS))
    stripped_after = _canonical(_without_paths(after_view, ECHO_PATHS))
    assert stripped_before == stripped_after, (
        "then-known view at cutoff "
        f"{CUTOFF_T0} is not byte-identical across the amendment: "
        f"before sha256 {_sha256(stripped_before)}, "
        f"after sha256 {_sha256(stripped_after)}"
    )


def test_v0_cutoff_equal_to_amendment_available_at_follows_contract(
    pack, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = _built_amendment_fixtures(pack, tmp_path)
    holder: dict[str, Any] = {}
    client = _serve_phase(tmp_path, monkeypatch, holder, fixtures["after"])

    # The contract's side (engine/capital_structure/state_bundle.py,
    # then_known_state): an input row survives when its
    # point_in_time.available_at is "<= moment" (line 1128) — a cutoff EXACTLY
    # equal to the amendment's available_at INCLUDES it; one second earlier
    # EXCLUDES it.
    at_boundary = _then_known_registration(client, AMENDMENT_AVAILABLE_AT)
    before_boundary = _then_known_registration(client, "2026-08-03T11:59:59Z")

    included = at_boundary["paths"][0]["amendment_chain"]
    excluded = before_boundary["paths"][0]["amendment_chain"]
    assert len(excluded) == 0, f"one second early must exclude: {excluded!r}"
    assert len(included) == 1, f"at the instant must include: {included!r}"
    entry = included[0]
    assert entry["form"] == "S-1/A"
    assert entry["mastermind_available_at"] == AMENDMENT_AVAILABLE_AT
    assert entry["relationship"]["relationship"] == "amendment_of"

    # And each view echoes the cutoff it was cut at, exactly as requested.
    assert at_boundary["view"]["as_of"] == AMENDMENT_AVAILABLE_AT
    assert before_boundary["view"]["as_of"] == "2026-08-03T11:59:59Z"


def _differing_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Dotted paths where two decoded JSON documents differ."""
    differences: list[str] = []
    if type(before) is not type(after):
        return [prefix or "$"]
    if isinstance(before, dict):
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in before or key not in after:
                differences.append(path)
            else:
                differences.extend(_differing_paths(before[key], after[key], path))
    elif isinstance(before, list):
        if len(before) != len(after):
            differences.append(prefix or "$")
        else:
            for index, (one, other) in enumerate(zip(before, after)):
                differences.extend(_differing_paths(one, other, f"{prefix}[{index}]"))
    elif before != after:
        differences.append(prefix or "$")
    return differences


def _without_paths(payload: Any, paths: tuple[str, ...]) -> Any:
    """Drop exactly the named dotted paths from a decoded JSON document."""
    cleaned = json.loads(json.dumps(payload))
    for path in paths:
        node = cleaned
        parts = path.split(".")
        for part in parts[:-1]:
            node = node[part]
        node.pop(parts[-1], None)
    return cleaned
