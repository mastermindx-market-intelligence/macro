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


# ===========================================================================
# SPEC_V0 §3 items 2 and 3 (lane claude/cs-v2-v0b-lane): failed persistence
# and restore exactness over the U2 saved-scenario API.
#
# Everything above this banner is items 1 and 4, byte-identical to the merged
# lane.  Everything below appends the two remaining recovery proofs through the
# SERVED paths: the U2 saved-scenario routes over the fake PostgREST transport
# (imported by name from the U2 suites, never copied), the real builders for a
# second published generation, and the closed restore vocabulary the engine
# defines.  No new lock, ledger, queue or monitor: every case drives the
# existing paths on fixture state in tmp_path, offline.
# ===========================================================================

from engine.capital_structure import saved_scenario_store as store  # noqa: E402
from engine.capital_structure.issuer_state_contracts import stable_id  # noqa: E402
from engine.capital_structure.saved_scenarios import RESTORE_OUTCOMES  # noqa: E402
import tests.test_capital_structure_saved_scenario_api as saved_api  # noqa: E402
from tests.test_capital_structure_saved_scenario_api import (  # noqa: E402
    NOON_AS_OF,
    SAVED_PATH,
    _PartitionedStore,
    _corrected_financials_inputs,
    _save_body,
    _saved_of_public,
    _serve_noon_generation,
    _serve_second_generation,
    ledger_path,
    moved,
    moved_noon,
    store_transport,
)
from tests.test_capital_structure_saved_scenarios import (  # noqa: E402
    _FakePostgREST,
    _change,
    _changeset,
    _row_for,
)
from tests.test_capital_structure_state_api import (  # noqa: E402
    ISSUER_ONE as _U1_ISSUER_ONE,
    _checked,
    _detail,
    built,
    client,
    served,
    with_inputs,
)

_PARTIAL_USER = "paid-user"
_PARTIAL_SAVED_ID = "saved_scenario:cs:" + "0" * 32


def _canonical_sha256(payload: Any) -> str:
    """The sha256 of one record's canonical JSON (the packet's byte identity)."""
    return _sha256(_canonical(payload))


class _FailsBeforeWrite(_PartitionedStore):
    """The store that raises on the upsert write, before anything lands."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        super().__init__(rows=rows)
        self.write_attempts = 0

    def __call__(
        self,
        method: str,
        path: str,
        body: Any = None,
        prefer: str | None = None,
        timeout: int = 6,
    ) -> Any:
        if method == "POST":
            self.write_attempts += 1
            raise TimeoutError(
                "simulated saved-scenario store failure before the row landed"
            )
        return super().__call__(method, path, body=body, prefer=prefer, timeout=timeout)


class _WritesPartialThenFails(_PartitionedStore):
    """The hard stop mid-write: a partial row is recorded, then the write fails.

    The fake's storage model makes the partial row expressible: ``rows`` is a
    plain list, so the half-written row lands exactly as a stopped process
    would have left it, and the failure raises after it.
    """

    def __init__(
        self, rows: list[dict[str, Any]], partial_row: dict[str, Any]
    ) -> None:
        super().__init__(rows=rows)
        self.partial_row = partial_row
        self.write_attempts = 0

    def __call__(
        self,
        method: str,
        path: str,
        body: Any = None,
        prefer: str | None = None,
        timeout: int = 6,
    ) -> Any:
        if method == "POST":
            self.write_attempts += 1
            self.rows.append(dict(self.partial_row))
            raise TimeoutError(
                "simulated saved-scenario store failure after a partial row landed"
            )
        return super().__call__(method, path, body=body, prefer=prefer, timeout=timeout)


def _partial_row_of(saved_public: dict[str, Any]) -> dict[str, Any]:
    """A half-written row: the record text stops mid-write, under the caller."""
    row = _row_for(_saved_of_public(saved_public, _PARTIAL_USER))
    row["saved_id"] = _PARTIAL_SAVED_ID
    row["record"] = '{"schema": "capital_structure.saved_scena'
    return row


# ---------------------------------------------------------------------------
# Item 2 — failed persistence (A46): a failed save is typed, never a half write
# ---------------------------------------------------------------------------


def test_v0_failed_saved_scenario_write_is_typed_and_prior_restores_exactly(
    client: TestClient,
    served: Any,
    built: Any,
    with_inputs: Any,
    store_transport: _FakePostgREST,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S1 is saved through the U2 API on the good transport and reads back
    # through the served restore route: that is the prior state a failed save
    # must leave byte-identically.
    saved_public = _checked(client.post(SAVED_PATH, json=_save_body()), status=201)["saved"]
    saved_id = str(saved_public["saved_id"])
    store_transport.rows = [_row_for(_saved_of_public(saved_public, _PARTIAL_USER))]
    first_read = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    before_sha = _canonical_sha256(first_read["saved"])
    assert before_sha == _canonical_sha256(saved_public), (
        f"the first read-back differs from the 201 record: {before_sha}"
    )

    # The same save again, with the store failing on the upsert write.  The
    # route answers the typed failure it defines (app/capital_structure.py
    # issuer_scenario_save: a write.state != "ok" is _STORE_UNAVAILABLE, 503).
    failing = _FailsBeforeWrite(rows=[_row_for(_saved_of_public(saved_public, _PARTIAL_USER))])
    monkeypatch.setattr(store, "_transport", failing)
    refused = client.post(SAVED_PATH, json=_save_body())
    assert refused.status_code == 503, (refused.status_code, refused.text[:200])
    assert _detail(refused) == api._STORE_UNAVAILABLE, _detail(refused)
    _checked(refused)
    assert failing.write_attempts == 1, (
        f"the store write was attempted {failing.write_attempts} times; "
        "the adapter never retries"
    )

    # The prior saved scenario S1 reads back byte-identically.
    monkeypatch.setattr(
        store,
        "_transport",
        _PartitionedStore(rows=[_row_for(_saved_of_public(saved_public, _PARTIAL_USER))]),
    )
    after_read = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    after_sha = _canonical_sha256(after_read["saved"])
    assert after_sha == before_sha, (
        "a failed saved-scenario write moved the prior saved scenario: "
        f"before sha256 {before_sha}, after sha256 {after_sha}, "
        f"served saved_id {after_read['saved']['saved_id']!r}"
    )


def test_v0_failed_saved_scenario_write_leaves_no_half_record(
    client: TestClient,
    served: Any,
    built: Any,
    with_inputs: Any,
    store_transport: _FakePostgREST,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_public = _checked(client.post(SAVED_PATH, json=_save_body()), status=201)["saved"]
    saved_id = str(saved_public["saved_id"])
    good_row = _row_for(_saved_of_public(saved_public, _PARTIAL_USER))
    store_transport.rows = [dict(good_row)]
    before_sha = _canonical_sha256(saved_public)

    # The upsert lands a partial row, then fails (the hard-stop shape).
    failing = _WritesPartialThenFails(
        rows=[dict(good_row)], partial_row=_partial_row_of(saved_public)
    )
    monkeypatch.setattr(store, "_transport", failing)
    refused = client.post(SAVED_PATH, json=_save_body())
    assert refused.status_code == 503, (refused.status_code, refused.text[:200])
    assert _detail(refused) == api._STORE_UNAVAILABLE, _detail(refused)
    _checked(refused)

    # No half record is readable through get: the typed unavailable, never a
    # partial body.
    half = client.get(f"{SAVED_PATH}/{_PARTIAL_SAVED_ID}")
    assert half.status_code == 503, (half.status_code, half.text[:200])
    assert _detail(half) == api._STORE_UNAVAILABLE, _detail(half)
    _checked(half)

    # No half record is readable through list: the page is refused whole, so a
    # half row can never ride out inside a partial listing.
    listed = client.get(SAVED_PATH)
    assert listed.status_code == 503, (listed.status_code, listed.text[:200])
    assert _detail(listed) == api._STORE_UNAVAILABLE, _detail(listed)
    _checked(listed)

    # The prior scenario S1 still reads back byte-identically.
    after_read = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    after_sha = _canonical_sha256(after_read["saved"])
    assert after_sha == before_sha, (
        "the failed write with a partial row moved the prior saved scenario: "
        f"before sha256 {before_sha}, after sha256 {after_sha}, "
        f"served saved_id {after_read['saved']['saved_id']!r}"
    )


# ---------------------------------------------------------------------------
# Item 3 — restore exactness (A46): a restore after a new generation is exact
# and the outcome set is closed
# ---------------------------------------------------------------------------


def test_v0_restore_after_new_generation_is_exact(
    client: TestClient,
    served: Any,
    built: Any,
    with_inputs: Any,
    moved: saved_api._Moved,
    ledger_path: Path,
    store_transport: _FakePostgREST,
) -> None:
    saved_public = _checked(client.post(SAVED_PATH, json=_save_body()), status=201)["saved"]
    saved_id = str(saved_public["saved_id"])
    g1 = str(built.bundle["generation_id"])
    store_transport.rows = [_row_for(_saved_of_public(saved_public, _PARTIAL_USER))]

    # G2 publishes the way the U2 API tests do: the real builders over the
    # fixture world plus one new issuer filing, with the real S1->S2 ledger.
    served_generation = _serve_second_generation(served, built, moved, ledger_path)
    assert served_generation != g1
    body = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    assert set(body) == {"saved", "current", "unavailable", "restore", "changes"}
    restore = body["restore"]
    assert restore["outcome"] == "new_events", json.dumps(restore, sort_keys=True)
    # The G1 source generation is reported exactly.
    assert restore["from_generation_id"] == g1, (
        f"restore reported source generation {restore['from_generation_id']!r}, "
        f"saved on {g1!r}"
    )
    assert restore["to_generation_id"] == served_generation

    # The saved block is byte-verbatim across the restore.
    saved_block_sha = _canonical_sha256(body["saved"])
    assert saved_block_sha == _canonical_sha256(saved_public), (
        f"the saved block moved across a restore: {saved_block_sha}"
    )

    # The restored assumptions are EXACT: canonical-JSON equality and the same
    # sha256 as the saved body's assumptions (the rebased anchor differs by
    # nothing here — G2 keeps G1's as_of — so the served scenario record must
    # be byte-identical to the saved one).
    saved_scenario_sha = _canonical_sha256(saved_public["scenario"])
    current_scenario_sha = _canonical_sha256(body["current"]["scenario"])
    assert body["current"]["scenario"] == saved_public["scenario"], (
        f"restored assumptions differ from the saved assumptions: saved sha256 "
        f"{saved_scenario_sha}, current sha256 {current_scenario_sha}"
    )
    assert current_scenario_sha == saved_scenario_sha
    # And the re-run binds the served generation it re-ran on.
    assert body["current"]["view"]["generation_id"] == served_generation


def test_v0_classify_restore_distinguishes_the_closed_outcome_set(
    client: TestClient,
    served: Any,
    built: Any,
    with_inputs: Any,
    moved: saved_api._Moved,
    moved_noon: saved_api._Moved,
    ledger_path: Path,
    store_transport: _FakePostgREST,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_public = _checked(client.post(SAVED_PATH, json=_save_body()), status=201)["saved"]
    saved_id = str(saved_public["saved_id"])
    g1 = str(built.bundle["generation_id"])
    store_transport.rows = [_row_for(_saved_of_public(saved_public, _PARTIAL_USER))]
    outcomes: dict[str, str] = {}

    def restored_outcome(label: str) -> str:
        body = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
        outcome = str(body["restore"]["outcome"])
        # The closed set: every served outcome is a member the module defines.
        assert outcome in RESTORE_OUTCOMES, (label, outcome, RESTORE_OUTCOMES)
        # The byte-exactness the U2 restore-outcome test does not assert: the
        # saved block is byte-verbatim in every outcome.
        block_sha = _canonical_sha256(body["saved"])
        assert block_sha == _canonical_sha256(saved_public), (
            f"{label}: the saved block moved across a restore: {block_sha}"
        )
        return outcome

    # no change — the same served state and inputs generations.
    outcomes["no_change"] = restored_outcome("no_change")

    # source outage — no bindable state generation is served.
    served.state_path.write_text("{not-json", encoding="utf-8")
    served.reset()
    outcomes["source_outage"] = restored_outcome("source_outage")
    served.state_path.write_text(built.state_body, encoding="utf-8")
    served.reset()

    # new events — G2 published with the real spanning ledger.
    g2 = _serve_second_generation(served, built, moved, ledger_path)
    outcomes["new_events"] = restored_outcome("new_events")
    new_body = _checked(client.get(f"{SAVED_PATH}/{saved_id}"), status=200)
    assert new_body["restore"]["from_generation_id"] == g1
    assert new_body["restore"]["to_generation_id"] == g2

    # correction — the nightly moved the cut AND a corrected observation was
    # published, attributed by a ledger that spans saved->served.
    noon = _serve_noon_generation(served, moved_noon)
    _corrected_financials_inputs(served, built, NOON_AS_OF, noon)
    corrected = _changeset(
        _change(
            "corrected_observation",
            "correction_version_incremented",
            issuer_id=_U1_ISSUER_ONE,
            subject={
                "logical_observation_id": stable_id("lifecycle", {"probe": "v0-correction"})
            },
            from_generation_id=g1,
            to_generation_id=noon,
        ),
        from_generation_id=g1,
        to_generation_id=noon,
    )
    monkeypatch.setattr(api, "_load_changes", lambda: corrected)
    api._reset_changes_cache()
    outcomes["correction"] = restored_outcome("correction")

    # Each SPEC_V0-named outcome is distinguished, exactly once, by the merged
    # name the module defines (RESTORE_OUTCOMES: the "new event" case is named
    # "new_events").
    assert outcomes == {
        "no_change": "no_change",
        "source_outage": "source_outage",
        "new_events": "new_events",
        "correction": "correction",
    }, json.dumps(outcomes, sort_keys=True)
