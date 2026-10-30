"""Tests for scripts/prophet_settlement_manifest.py — the V4-A2 settlement
manifest (masterplan §18.1-§18.2, §21 V4-A2; wave-graph §4 ruling 11).

WHAT THIS ENCODES.  On 2026-10-30 the public R2 health receipt
(``prophet.public_health/v1``) republished fresh while the board's
``source_asof`` lagged the owed session: every publication-side instrument
read HEALTHY and nothing proved a reader ever saw the owed session.  The
manifest is the instrument that closes exactly that hole, so every test below
attacks one way a NON-reader truth could masquerade as settlement:

    wall-clock/receipt false freshness  -> test_oct30_public_health_fresh_source_stale_is_pending
    gate-skip green (no advance)        -> test_gate_skip_night_does_not_advance
    stale served bundle                 -> test_equal_source_dates_but_mismatched_raw_digest_is_pending
    reserialization ≟ byte identity     -> test_reserialized_identical_json_is_a_different_bundle
    missing/unreadable served read      -> test_no_served_read_is_blind_even_with_a_fresh_clock
    missing reader clock                -> test_missing_reader_clock_fails_closed
    mixed vintage                       -> test_vintage_flags_fail_closed
    leaked board content                -> test_no_leaks_in_envelope
    null artifact map (false green)     -> test_missing_artifact_hashes_fails_closed_typed
    index-only map ≟ full bundle        -> test_index_only_mapping_cannot_infer_the_bundle
    unrelated asset entry               -> test_unrelated_asset_entry_is_not_the_accepted_bundle
    subset map (missing hashes)         -> test_missing_asset_entries_are_incomplete
    wrong index hash in a full map      -> test_wrong_index_hash_in_full_map_is_pending
    reader map ≟ issuer accepted map    -> test_reader_map_must_equal_issuer_accepted_map
    issuer map ≟ receipt index hash     -> test_issuer_accepted_map_must_agree_with_receipt_index
    missing trusted references          -> test_missing_accepted_bundle_reference_is_pending
                                           test_missing_reader_proof_is_pending
    malformed trusted reference         -> test_accepted_bundle_reference_shape_is_enforced
                                           test_reader_proof_shape_is_enforced
    bundle id ≟ reader served id        -> test_bundle_ids_must_agree
    bundle id ≅ receipt checkpoint      -> test_bundle_id_may_not_be_the_receipt_checkpoint
    synthetic accepted read (SETTLED)   -> test_synthetic_explicit_accepted_read_is_the_only_settled_shape

Everything is pure and clock-free by construction: fixture stamps are FROZEN
LITERALS, no test opens a socket or reads a clock, and the source guards at the
bottom keep the module that way (the ``test_prophet_rescue`` pattern — a guard
that forbids writing ABOUT the trap stops nothing; these forbid the trap).

Run: python3 -m pytest tests/test_prophet_settlement_manifest.py -q
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "scripts" / "prophet_settlement_manifest.py"

_SPEC = importlib.util.spec_from_file_location("prophet_settlement_manifest_under_test", SCRIPT)
assert _SPEC and _SPEC.loader
MAN = importlib.util.module_from_spec(_SPEC)
sys.modules["prophet_settlement_manifest_under_test"] = MAN
_SPEC.loader.exec_module(MAN)

# ── frozen literals: 2026-10-28/29/30 are Tue-Thu NYSE sessions, ─────────────
# 10-31 is a Saturday; nothing here derives from today.
WED = "2026-10-28"
THU = "2026-10-29"
FRI = "2026-10-30"
PUBLISHED_FRESH = "2026-10-30T22:05:00Z"   # the receipt's own emission stamp
READ_AT = "2026-10-30T22:11:03Z"           # the reader's own observation stamp
COMPUTED_AT = "2026-10-30T21:58:41Z"       # a genuine recorded compute stamp
CHECKPOINT = "c1e2a3b4c1e2a3b4c1e2a3b4c1e2a3b4c1e2a3b4"
BOARD_SHA = "d0e5a1d11804e9458df70e009de268ebce30c21000000000000000000000000a0"
LEAK_PATH = "/opt/macro/data/us_board_ledger/origination_sources/leak-bait.json.gz"

# ── SYNTHETIC §18.2 accepted-bundle fixtures (constructed, NOT observed) ─────
# The bundle identity, board definition and asset hashes below are test
# fixtures built for this suite.  They are never a production publish bundle
# or a production reader proof, and no test here is production proof that any
# real session settled.  The projection's SETTLED path requires the caller to
# inject this binding evidence; these fixtures exist so the suite can pin the
# projection's acceptance and rejection rules around it.
SYNTH_BUNDLE_ID = "SYNTHETIC-TEST-BUNDLE-ID-NOT-A-PRODUCTION-PROOF"
SYNTH_OTHER_BUNDLE_ID = "SYNTHETIC-OTHER-BUNDLE-ID-TEST-ONLY"
SYNTH_BOARD_DEFINITION = "synthetic_board_definition_TEST_ONLY"
SYNTH_CANDIDATE_COUNT = 7

_UNSET = object()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def synthetic_artifact_hashes(index_sha: str) -> dict[str, str]:
    """The full §18.2 four-asset raw hash map for a synthetic accepted read:
    ``index`` is bound to the actual served bytes; the other three assets are
    synthetic fixture digests."""
    return {
        "board": digest(b"synthetic-board-bytes"),
        "candidate_store": digest(b"synthetic-candidate-store-bytes"),
        "index": index_sha,
        "theme_state": digest(b"synthetic-theme-state-bytes"),
    }


def synthetic_accepted_bundle(artifact_hashes: dict[str, str], *,
                              bundle_id: str = SYNTH_BUNDLE_ID) -> dict:
    """A synthetic SOURCE-ISSUED accepted bundle reference (§18.2 publish
    bundle identity plus the bundle-level identity fields).  Fixture only."""
    return {
        "bundle_id": bundle_id,
        "board_definition": SYNTH_BOARD_DEFINITION,
        "candidate_count": SYNTH_CANDIDATE_COUNT,
        "artifact_hashes": dict(artifact_hashes),
    }


def synthetic_reader_proof(*, bundle_id: str = SYNTH_BUNDLE_ID) -> dict:
    """A synthetic reader-served bundle identity (§18.2 reader_proof
    ``served_bundle_id``).  Fixture only."""
    return {"served_bundle_id": bundle_id}


def index_document(*, source_asof: str = FRI, schema: str = MAN.INDEX_SCHEMA,
                   omit: tuple[str, ...] = (), **extra) -> dict:
    """A minimal served ``prophet.index/v1`` body.  Deliberately carries the
    run clock and a snapshot PATH + plan_count as leak bait for the no-leak
    pin: real served bytes hold fields the manifest must never echo."""
    doc: dict = {
        "schema": schema,
        "asof": "2026-10-30T22:00:00Z",
        "recorded_at": "2026-10-30T22:00:00Z",
        "source_asof": source_asof,
        "source_delayed": False,
        "source_unknown": False,
        "source_mixed_vintage": False,
        "source_board_sha256": BOARD_SHA,
        "source_board_snapshot_path": LEAK_PATH,
        "cadence": "nightly-EOD",
        "authority_tier": "display",
        "plan_count": 286,
    }
    doc.update(extra)
    for key in omit:
        doc.pop(key, None)
    return doc


def index_bytes(**kw) -> bytes:
    return json.dumps(index_document(**kw), indent=2).encode("utf-8")


def health_receipt(*, index_sha256: str | None = None,
                   source_asof: str | None = FRI,
                   published_at: str | None = PUBLISHED_FRESH,
                   checkpoint: str | None = CHECKPOINT,
                   schema: str = MAN.HEALTH_SCHEMA,
                   omit: tuple[str, ...] = (), **extra) -> dict:
    """A ``prophet.public_health/v1`` receipt exactly as the daily.yml
    publisher emits it (build_prophet.build_public_health_projection)."""
    doc: dict = {
        "schema": schema,
        "source_asof": source_asof,
        "published_at": published_at,
        "checkpoint": checkpoint,
        "index_sha256": index_sha256,
        "note": "Public publication receipt only.",
    }
    doc.update(extra)
    for key in omit:
        doc.pop(key, None)
    return doc


def evidence(index_kw: dict | None = None,
             health_kw: dict | None = None) -> tuple[bytes, dict]:
    """Served bytes + the receipt the publisher would emit FOR THOSE bytes —
    ``index_sha256`` AND ``source_asof`` both bound to that exact body, as
    build_prophet.build_public_health_projection does.  ``health_kw`` entries
    then override receipt fields (a None overrides to a genuinely absent
    field — ``health_hash_missing`` etc.)."""
    doc = index_document(**(index_kw or {}))
    served = json.dumps(doc, indent=2).encode("utf-8")
    receipt = health_receipt(index_sha256=digest(served),
                             source_asof=doc.get("source_asof", FRI))
    if health_kw:
        receipt.update(health_kw)
    return served, receipt


def manifest_call(*, index_kw: dict | None = None, health_kw: dict | None = None,
                  served_index_bytes=_UNSET, accepted_health=_UNSET,
                  **over) -> dict:
    """One manifest projection over green evidence with surgical overrides.

    Green now INCLUDES the §18.2 full-bundle binding evidence, synthesized
    around the exact served bytes from the SYNTHETIC fixtures above, so each
    mutation can strip exactly one element and pin a single typed failure.
    The binding evidence is constructed for tests only — never production
    proof."""
    served, health = evidence(index_kw, health_kw)
    artifact = synthetic_artifact_hashes(digest(served))
    kwargs = {
        "owed_session": FRI,
        "accepted_health": health if accepted_health is _UNSET else accepted_health,
        "served_index_bytes": served if served_index_bytes is _UNSET else served_index_bytes,
        "reader_observed_at": READ_AT,
        "computed_at": COMPUTED_AT,
        "artifact_hashes": artifact,
        "accepted_bundle": synthetic_accepted_bundle(artifact),
        "reader_proof": synthetic_reader_proof(),
    }
    kwargs.update(over)
    return MAN.project_settlement_manifest(**kwargs)


# ═════════════════════════════ SETTLED ═══════════════════════════════════════

def test_settled_complete_envelope():
    served, health = evidence()
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=FRI, accepted_health=health, served_index_bytes=served,
        reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof(),
    )
    assert out["schema"] == "prophet.settlement_manifest/v1"
    assert out["status"] == "SETTLED"
    assert out["failures"] == []
    assert out["owed_session"] == FRI
    assert out["source_asof"] == FRI              # accepted receipt's claim
    assert out["reader_visible_asof"] == FRI      # what production serves
    assert out["checked_at"] == READ_AT           # the reader's own clock
    assert out["computed_at"] == COMPUTED_AT      # echoed verbatim, not synthesized
    assert out["published_at"] == PUBLISHED_FRESH
    assert out["checkpoint"] == CHECKPOINT
    assert out["artifact_hashes"] == artifact     # the full four-asset map, echoed


def test_envelope_is_closed_and_ordered():
    out = manifest_call()
    assert list(out) == list(MAN.MANIFEST_FIELDS)
    assert set(out) == set(MAN.MANIFEST_FIELDS)


def test_idempotent_and_deterministic():
    served, health = evidence()
    kwargs = dict(owed_session=FRI, accepted_health=health,
                  served_index_bytes=served, reader_observed_at=READ_AT,
                  computed_at=COMPUTED_AT)
    first = MAN.project_settlement_manifest(**kwargs)
    second = MAN.project_settlement_manifest(**kwargs)
    assert first == second
    assert json.dumps(first) == json.dumps(second)


# ═════════════════ the 10-30 incident: receipt-fresh ≠ settled ═══════════════

def test_oct30_public_health_fresh_source_stale_is_pending():
    """MUTATION PIN (the incident itself).  The receipt republished fresh for a
    STALE bundle: published_at minutes old, source_asof a session behind.  A
    fresh receipt must never settle a session the reader cannot see — and
    nothing else may be wrong with this evidence, so the single failure is the
    one the operator acts on."""
    out = manifest_call(index_kw={"source_asof": THU}, owed_session=FRI)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["source_asof_stale"]
    assert out["published_at"] == PUBLISHED_FRESH   # fresh — and worthless alone


def test_gate_skip_night_does_not_advance():
    """MUTATION PIN (A4 'gate-skip success' drill).  The nightly woke, published
    a genuine receipt tonight, but the gate skipped origination so the source
    never advanced.  Same-session-date receipts are not an advance."""
    out = manifest_call(
        index_kw={"source_asof": THU},
        health_kw={"published_at": "2026-10-30T23:40:00Z"},
        computed_at="2026-10-30T23:39:59Z",
    )
    assert out["status"] == "PENDING"
    assert out["failures"] == ["source_asof_stale"]


def test_stale_source_stays_pending_with_every_other_gate_green():
    """The stale night really did serve the accepted stale bundle (digest
    matches, full §18.2 binding green) with a qualified reader clock —
    settlement STILL waits for the source, because §18.1 gates on
    reader_visible_asof >= owed_session."""
    served, health = evidence(index_kw={"source_asof": WED})
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=THU, accepted_health=health,
        served_index_bytes=served, reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof())
    assert out["status"] == "PENDING"
    assert "source_asof_stale" in out["failures"]
    assert out["reader_visible_asof"] == WED


def test_source_asof_equal_to_owed_settles():
    served, health = evidence(index_kw={"source_asof": THU})
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=THU, accepted_health=health,
        served_index_bytes=served, reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof())
    assert out["status"] == "SETTLED"


# ═══════════════════════ served bundle identity (RAW bytes) ══════════════════

def test_equal_source_dates_but_mismatched_raw_digest_is_pending():
    """MUTATION PIN (stale served bundle).  Same session date on both sides,
    but the reader is holding a DIFFERENT bundle than the accepted receipt
    describes.  Matching as-of dates must not paper over a bundle split.
    With the full §18.2 binding green on the receipt's accepted bytes, the
    drifted served tree is accused twice: against the receipt digest AND
    against the reader's own index asset entry."""
    served = index_bytes(source_asof=FRI, plan_count=999)   # other bundle, same session
    health = health_receipt(index_sha256=digest(index_bytes(source_asof=FRI)))
    artifact = synthetic_artifact_hashes(digest(index_bytes(source_asof=FRI)))
    out = MAN.project_settlement_manifest(
        owed_session=FRI, accepted_health=health,
        served_index_bytes=served, reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof())
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_index_digest_mismatch", "served_digest_mismatch"]
    assert out["source_asof"] == out["reader_visible_asof"] == FRI


def test_reserialized_identical_json_is_a_different_bundle():
    """MUTATION PIN (RAW bytes, never reserialized).  Semantically identical
    JSON in different bytes is NOT the accepted bundle.  A manifest that
    compared parsed objects — or re-dumped the object the way the writer
    writes it and hashed THAT, the shortcut scripts/prophet_rescue.py
    explicitly refuses to make authoritative — would settle a served tree
    nobody accepted.  The trailing-newline case is the realistic drift: one
    byte, invisible to every parsed-object comparison."""
    served = index_bytes()
    variants = [
        json.dumps(json.loads(served), indent=4, sort_keys=True).encode("utf-8"),
        served + b"\n",
    ]
    for reserialized in variants:
        assert json.loads(reserialized) == json.loads(served)
        assert reserialized != served
        out = manifest_call(served_index_bytes=reserialized)
        assert out["status"] == "PENDING", reserialized[:40]
        assert "served_digest_mismatch" in out["failures"]


def test_reader_clock_before_published_at_still_settles():
    """Bundle identity is the bytes, not clock ordering.  A reader whose host
    clock trails the publisher's (cross-host skew) must not flap settlement
    when the served bytes provably ARE the accepted bundle."""
    served, health = evidence()
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=FRI, accepted_health=health, served_index_bytes=served,
        reader_observed_at="2026-10-30T20:00:00Z", computed_at=COMPUTED_AT,   # < published_at
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof())
    assert out["status"] == "SETTLED"


# ═══════════════════════ blindness (UNAVAILABLE_DATA) ════════════════════════

def test_no_served_read_is_blind_even_with_a_fresh_clock():
    """MUTATION PIN (wall-clock false freshness).  The reader's clock is
    qualified and recorded, but there are NO served bytes to prove anything
    about.  A fresh observation of nothing settles nothing."""
    out = manifest_call(
        served_index_bytes=None,
        health_kw={"index_sha256": digest(index_bytes())},
    )
    assert out["status"] == "UNAVAILABLE_DATA"
    assert "served_index_unavailable" in out["failures"]
    assert out["checked_at"] == READ_AT            # the clock was fine — and insufficient
    assert out["reader_visible_asof"] is None
    assert out["source_asof"] == FRI               # the receipt's claim still shows


def test_malformed_served_bytes_are_blind():
    out = manifest_call(served_index_bytes=b"<html>404 - not found</html>")
    assert out["status"] == "UNAVAILABLE_DATA"
    assert "served_index_malformed" in out["failures"]
    assert out["reader_visible_asof"] is None


def test_empty_served_read_is_blind():
    out = manifest_call(served_index_bytes=b"")
    assert out["status"] == "UNAVAILABLE_DATA"
    assert "served_index_malformed" in out["failures"]


def test_served_bytes_of_wrong_type_fail_closed():
    out = manifest_call(served_index_bytes="{\"schema\": \"prophet.index/v1\"}")  # str, not bytes
    assert out["status"] == "UNAVAILABLE_DATA"
    assert "served_index_unavailable" in out["failures"]


def test_missing_health_receipt_is_blind():
    out = manifest_call(accepted_health=None)
    assert out["status"] == "UNAVAILABLE_DATA"
    assert "health_receipt_unavailable" in out["failures"]
    assert out["source_asof"] is None
    assert out["checkpoint"] is None


def test_wrong_schema_served_artifact_is_judged_not_blind():
    """Blindness is 'could not read', never 'read something wrong'.  A
    definitive read of a non-index artifact is a JUDGED failure (PENDING),
    mirroring the sentinel's verdict discipline."""
    out = manifest_call(served_index_bytes=b'{"schema": "other.thing/v1"}')
    assert out["status"] == "PENDING"
    assert "served_index_schema_mismatch" in out["failures"]
    assert "served_source_asof_missing" in out["failures"]


def test_malformed_owed_session_is_blind():
    for bad in ("2026-10-3", "2026-13-40", "garbage", "", None):
        out = manifest_call(owed_session=bad)
        assert out["status"] == "UNAVAILABLE_DATA", bad
        assert out["failures"] == ["owed_session_malformed"], bad
        assert out["owed_session"] is None


# ═══════════════════════ clocks fail closed ══════════════════════════════════

def test_missing_reader_clock_fails_closed():
    """A digest match with NO recorded observation is not settlement: nobody
    can later prove a reader ever looked."""
    out = manifest_call(reader_observed_at=None)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["reader_clock_missing"]
    assert out["checked_at"] is None


@pytest.mark.parametrize("bad", [
    "2026-10-30T22:11:03",            # naive — an unconverted local clock
    "2026-10-30T23:11:03+01:00",      # explicit, but not UTC
])
def test_reader_clock_must_be_explicit_utc(bad):
    out = manifest_call(reader_observed_at=bad)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["reader_clock_not_utc"]
    assert out["checked_at"] is None


@pytest.mark.parametrize("bad", ["not-a-time", "2026-13-40T99:00:00Z", 1761891063])
def test_garbage_reader_clock_is_unqualified(bad):
    out = manifest_call(reader_observed_at=bad)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["reader_clock_unqualified"]


def test_computed_at_is_required_and_only_echoed_when_genuine():
    """Never synthesized from run time, and never accepted when the caller's
    'recorded clock' is not an explicit UTC stamp."""
    out = manifest_call(computed_at=None)   # missing real compute recording
    assert out["computed_at"] is None
    assert out["failures"] == ["computed_at_missing"]
    assert out["status"] == "PENDING"

    for bad in ("2026-10-30 21:58:41", "yesterday", 1761891063):
        out = manifest_call(computed_at=bad)
        assert out["failures"] == ["computed_at_unqualified"], bad
        assert out["computed_at"] is None
        assert out["status"] == "PENDING"


# ═══════════════════════ served vs receipt agreement ═════════════════════════

def test_served_and_health_source_asof_disagreement_is_loud():
    """§18.3: make split-brain loud, in the envelope itself — the reader sees
    THU while the receipt claims FRI, for the SAME accepted bytes (the full
    §18.2 hash binding agrees; only the source dates split)."""
    served = index_bytes(source_asof=THU)
    health = health_receipt(index_sha256=digest(served), source_asof=FRI)
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=THU, accepted_health=health,
        served_index_bytes=served, reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof())
    assert out["status"] == "PENDING"
    assert out["failures"] == ["served_source_asof_mismatch"]
    assert out["source_asof"] == FRI
    assert out["reader_visible_asof"] == THU


@pytest.mark.parametrize("flag", ["source_delayed", "source_unknown", "source_mixed_vintage"])
@pytest.mark.parametrize("value", [True, None, "false"])
def test_vintage_flags_fail_closed(flag, value):
    """Only ``is False`` proves a clean single-vintage known-source read.  A
    truthy, null or absent flag cannot prove the negative."""
    out = manifest_call(index_kw={flag: value})
    assert out["status"] == "PENDING"
    assert out["failures"] == [flag]
    assert "source_asof_stale" not in out["failures"]


def test_absent_vintage_flag_fails_closed():
    out = manifest_call(index_kw={"omit": ("source_mixed_vintage",)})
    assert out["status"] == "PENDING"
    assert out["failures"] == ["source_mixed_vintage"]


# ═══════════════════════ accepted receipt shape ══════════════════════════════

def test_health_receipt_shape_is_enforced():
    cases = [
        ({"schema": "other.receipt/v1"}, "health_receipt_schema_mismatch"),
        ({"index_sha256": None}, "health_hash_missing"),
        ({"index_sha256": "deadbeef"}, "health_hash_missing"),
        ({"index_sha256": digest(index_bytes()).upper()}, "health_hash_missing"),
        ({"source_asof": None}, "source_asof_missing"),
        ({"source_asof": "2026-10-3"}, "source_asof_missing"),
        ({"published_at": None}, "published_at_missing"),
        ({"published_at": "2026-10-30 22:05:00"}, "published_at_unqualified"),
        ({"checkpoint": None}, "checkpoint_missing"),
        ({"checkpoint": ""}, "checkpoint_missing"),
    ]
    for health_kw, expected in cases:
        out = manifest_call(health_kw=health_kw)
        assert out["status"] == "PENDING", (health_kw, out)
        assert expected in out["failures"], (health_kw, out)


def test_unpublished_health_hash_blocks_settlement():
    """Missing receipt hash = missing identity: nothing to bind the served
    bytes to, so the digest gate cannot pass — even with dates agreeing."""
    out = manifest_call(health_kw={"index_sha256": None})
    assert out["status"] == "PENDING"
    assert "health_hash_missing" in out["failures"]
    assert "served_digest_mismatch" not in out["failures"]


def test_checkpoint_and_hashes_flow_from_inputs():
    served, health = evidence()
    out = MAN.project_settlement_manifest(
        owed_session=FRI, accepted_health=health, served_index_bytes=served,
        reader_observed_at=READ_AT,
        artifact_hashes={"theme_state": digest(b"t"), "board": digest(b"b"),
                         "index": digest(served)},
    )
    assert out["checkpoint"] == CHECKPOINT
    assert out["artifact_hashes"] == {
        "board": digest(b"b"), "index": digest(served), "theme_state": digest(b"t"),
    }


def test_unqualified_artifact_hashes_are_flagged_not_echoed():
    out = manifest_call(artifact_hashes={"index": digest(index_bytes()),
                                         "board": "NOTAHASH",
                                         "": digest(b"x"), 7: digest(b"y")})
    assert "artifact_hashes_unqualified" in out["failures"]
    assert out["artifact_hashes"] == {"index": digest(index_bytes())}
    assert out["status"] == "PENDING"


# ═══════════════ §18.2 accepted full-bundle binding (fail closed) ════════════

def test_missing_artifact_hashes_fails_closed_typed():
    """MUTATION PIN (the reproduced false green).  Every other gate is green —
    qualified receipt, raw-digest match, owed session, qualified clocks,
    clean vintage, schema — and the caller supplies NO artifact map at all,
    exactly the shape the incumbent sentinel read model emits today.  That
    must never read SETTLED: with ``artifact_hashes`` null the bundle cannot
    be proven, so the verdict is PENDING with the typed missing code."""
    out = manifest_call(artifact_hashes=None)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_hashes_missing"]
    assert out["artifact_hashes"] is None
    assert "artifact_hashes_unqualified" not in out["failures"]


def test_index_only_mapping_cannot_infer_the_bundle():
    """MUTATION PIN (the audit gap).  An index hash that individually matches
    the accepted receipt proves ONE asset, not the accepted multi-asset
    bundle: §18.2 requires candidate_store, board, index and theme_state
    together.  The missing assets are never inferred — not from the receipt,
    not from the served bytes, not from anywhere — so the verdict stays
    PENDING with the typed incomplete-bundle code."""
    out = manifest_call(artifact_hashes={"index": digest(index_bytes())})
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_bundle_incomplete"]
    assert out["artifact_hashes"] == {"index": digest(index_bytes())}


def test_missing_asset_entries_are_incomplete():
    """MUTATION PIN (missing hashes).  Any subset of the four §18.2 assets is
    not the full accepted bundle, even when the surviving entries are
    well-formed."""
    out = manifest_call(artifact_hashes={
        "board": digest(b"b"), "index": digest(index_bytes())})
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_bundle_incomplete"]


def test_unrelated_asset_entry_is_not_the_accepted_bundle():
    """MUTATION PIN (unrelated hashes).  Entries outside the frozen §18.2
    bundle set — however well-formed — are not part of the accepted bundle
    and cannot ride along as one."""
    artifact = synthetic_artifact_hashes(digest(index_bytes()))
    artifact["unrelated_asset"] = digest(b"not-part-of-the-bundle")
    out = manifest_call(artifact_hashes=artifact)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_bundle_unrecognized_entry"]
    assert out["artifact_hashes"]["unrelated_asset"] == \
        digest(b"not-part-of-the-bundle")


def test_wrong_index_hash_in_full_map_is_pending():
    """MUTATION PIN (wrong index hash).  A complete, well-formed map whose
    index entry does not hash the bytes production actually serves is a
    misbound read — the manifest accuses both the map's index entry and its
    disagreement with the issuer's accepted map."""
    artifact = synthetic_artifact_hashes(digest(b"bytes-nobody-served"))
    out = manifest_call(artifact_hashes=artifact)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_bundle_mismatch",
                               "artifact_index_digest_mismatch"]


def test_reader_map_must_equal_issuer_accepted_map():
    """MUTATION PIN (map drift).  The reader's raw asset hashes and the
    issuer's accepted bundle hashes must agree entry-for-entry: one drifted
    asset is a different bundle, not a settled one."""
    artifact = synthetic_artifact_hashes(digest(index_bytes()))
    artifact["theme_state"] = digest(b"a-theme-state-the-issuer-never-accepted")
    out = manifest_call(artifact_hashes=artifact)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["artifact_bundle_mismatch"]


def test_issuer_accepted_map_must_agree_with_receipt_index():
    """MUTATION PIN (issuer vs receipt).  The accepted bundle's index hash and
    the accepted receipt's index hash are both issuer claims about the SAME
    bundle; disagreement is a loud PENDING, never settled through."""
    drift = synthetic_artifact_hashes(digest(b"an-index-the-receipt-never-accepted"))
    out = manifest_call(
        artifact_hashes=drift,
        accepted_bundle=synthetic_accepted_bundle(drift),
        health_kw={"index_sha256": digest(b"the-receipts-own-index")},
    )
    assert out["status"] == "PENDING"
    assert "bundle_index_digest_mismatch" in out["failures"]


def test_missing_accepted_bundle_reference_is_pending():
    """MUTATION PIN (missing trusted reference, issuer side).  Without the
    source-issued accepted bundle reference there is no bundle identity to
    bind to — the reader's own hash map alone cannot manufacture one."""
    out = manifest_call(accepted_bundle=None)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["accepted_bundle_missing"]


def test_missing_reader_proof_is_pending():
    """MUTATION PIN (missing trusted reference, reader side).  Without the
    reader-served bundle identity there is no proof production served the
    accepted bundle — settlement waits."""
    out = manifest_call(reader_proof=None)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["reader_proof_missing"]


@pytest.mark.parametrize("bundle_over", [
    {"bundle_id": ""},
    {"bundle_id": "not a single token"},
    {"bundle_id": 1761891063},
    {"board_definition": ""},
    {"board_definition": None},
    {"candidate_count": -1},
    {"candidate_count": "7"},
    {"candidate_count": True},        # bool is an int subclass — not a count
    {"candidate_count": None},
    {"artifact_hashes": {"index": digest(index_bytes())}},   # not the full set
    {"artifact_hashes": "not-a-mapping"},
    {"artifact_hashes": {**synthetic_artifact_hashes(digest(index_bytes())),
                         "extra": digest(b"x")}},
])
def test_accepted_bundle_reference_shape_is_enforced(bundle_over):
    """The source-issued reference must carry the §18.2 identity fields and
    exactly the four frozen asset entries; any defect accuses the
    REFERENCE, not the reader's own map."""
    bundle = synthetic_accepted_bundle(synthetic_artifact_hashes(digest(index_bytes())))
    bundle.update(bundle_over)
    out = manifest_call(accepted_bundle=bundle)
    assert out["status"] == "PENDING"
    assert out["failures"] == ["accepted_bundle_malformed"]


@pytest.mark.parametrize("proof, expected", [
    (None, "reader_proof_missing"),
    ("the reader looked", "reader_proof_malformed"),
    ({"served_bundle_id": None}, "reader_proof_malformed"),
    ({"served_bundle_id": ""}, "reader_proof_malformed"),
    ({"served_bundle_id": "has spaces"}, "reader_proof_malformed"),
    ({"served_bundle_id": 7}, "reader_proof_malformed"),
])
def test_reader_proof_shape_is_enforced(proof, expected):
    out = manifest_call(reader_proof=proof)
    assert out["status"] == "PENDING"
    assert out["failures"] == [expected]


def test_bundle_ids_must_agree():
    """MUTATION PIN (mismatched bundle IDs).  The issuer's accepted bundle
    identity and the reader's served bundle identity are two independent
    claims; settlement requires them to name the same bundle."""
    out = manifest_call(reader_proof=synthetic_reader_proof(
        bundle_id=SYNTH_OTHER_BUNDLE_ID))
    assert out["status"] == "PENDING"
    assert out["failures"] == ["bundle_id_mismatch"]


def test_bundle_id_may_not_be_the_receipt_checkpoint():
    """MUTATION PIN (no silent conflation).  The receipt's ``checkpoint`` is
    the source git archive commit — a different identity from the published
    bundle.  An accepted bundle whose ``bundle_id`` IS the checkpoint string
    is the checkpoint/bundle conflation defect itself and stays PENDING; the
    projection never borrows the checkpoint as a bundle identity."""
    out = manifest_call(
        accepted_bundle=synthetic_accepted_bundle(
            synthetic_artifact_hashes(digest(index_bytes())), bundle_id=CHECKPOINT),
        reader_proof=synthetic_reader_proof(bundle_id=CHECKPOINT),
    )
    assert out["status"] == "PENDING"
    assert out["failures"] == ["bundle_id_checkpoint_conflated"]


def test_synthetic_explicit_accepted_read_is_the_only_settled_shape():
    """The §18.2 settled shape, end to end, with ALL binding evidence
    EXPLICIT: the full four-asset raw hash map, the source-issued accepted
    bundle reference (bundle_id, board_definition, candidate_count, artifact
    hashes), and a reader-served bundle identity naming the same bundle.

    The identities and hashes are SYNTHETIC TEST FIXTURES (see the constants
    above) — this test proves the projection accepts a well-formed accepted
    read; it is NOT production proof that any real session settled."""
    served, health = evidence()
    artifact = synthetic_artifact_hashes(digest(served))
    out = MAN.project_settlement_manifest(
        owed_session=FRI, accepted_health=health, served_index_bytes=served,
        reader_observed_at=READ_AT, computed_at=COMPUTED_AT,
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof(),
    )
    assert out["status"] == "SETTLED"
    assert out["failures"] == []
    assert out["artifact_hashes"] == artifact


def test_artifact_hashes_omitted_is_pending_not_settled():
    """MUTATION PIN (artifact_hashes=None default).  Omitting the map is not
    neutrality — it is missing bundle evidence, typed and fail closed."""
    out = manifest_call(artifact_hashes=None)
    assert out["artifact_hashes"] is None
    assert "artifact_hashes_unqualified" not in out["failures"]
    assert "artifact_hashes_missing" in out["failures"]
    assert out["status"] == "PENDING"


# ═══════════════════════ public safety ═══════════════════════════════════════

def test_no_leaks_in_envelope():
    """Preserve DEC:B1-PROPHET-PUBLIC-SPLIT hygiene: the manifest may accuse,
    but it may not echo.  No paths, no plan book, no board bytes — even when
    the served bytes, receipt and accepted bundle reference carry them in
    plain sight."""
    served = index_bytes()
    artifact = synthetic_artifact_hashes(digest(served))
    out = manifest_call(
        served_index_bytes=served,
        accepted_health=health_receipt(index_sha256=digest(served)),
        artifact_hashes=artifact,
        accepted_bundle=synthetic_accepted_bundle(artifact),
        reader_proof=synthetic_reader_proof(),
        computed_at=COMPUTED_AT,
    )
    text = json.dumps(out)
    for banned in ("/opt/", "snapshot", "leak-bait", ".json.gz", "plan_count",
                   "286", BOARD_SHA, "nightly-EOD"):
        assert banned not in text, banned
    assert set(out["failures"]) <= MAN.FAILURE_CODES
    assert out["status"] == "SETTLED"   # the leak bait was lawful evidence


def test_failure_codes_are_never_paths_or_hosts():
    for code in MAN.FAILURE_CODES:
        assert "/" not in code and "." not in code and " " not in code, code
        assert code == code.lower()


# ═══════════════════════ structural guards (source-level) ════════════════════

def test_imports_are_stdlib_only():
    """stdlib-only is a CAST LAW for this module (its sibling rescue lane reads
    it from hosts that must not need dependencies): the import set is closed,
    and every root is a real stdlib module."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert roots == {"__future__", "hashlib", "json", "re", "collections", "datetime"}
    assert roots <= set(sys.stdlib_module_names)


def _non_docstring_nodes(tree):
    """Nodes whose line does not sit inside a docstring — the
    ``test_no_stop_run_code_path_exists`` scan discipline: a guard that forbids
    writing ABOUT the trap would stop the fix and the postmortem."""
    doc_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is None:
                continue
            for probe in ast.walk(node):
                if (isinstance(probe, ast.Constant) and probe.value is doc) or \
                        (isinstance(probe, ast.Expr) and isinstance(probe.value, ast.Constant)
                         and probe.value.value == doc):
                    doc_lines.update(range(probe.lineno, (probe.end_lineno or probe.lineno) + 1))
    return doc_lines


def test_no_io_no_net_no_global_clock_source_guard():
    """MUTATION PIN (module laws).  This module's entire authority is that it
    manufactures nothing: no socket, no subprocess, no filesystem, no wall
    clock.  Add ANY of those — ``datetime.now()``, ``date.today()``,
    ``urllib.request.urlopen``, ``open()`` — and this goes red before a
    manifest built on it can lie."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    doc_lines = _non_docstring_nodes(tree)

    banned_imports = {
        "urllib", "socket", "http", "ssl", "ftplib", "smtplib", "subprocess",
        "shutil", "tempfile", "random", "pickle", "ctypes", "requests", "os",
        "time", "pathlib",
    }
    banned_calls = {
        "open", "urlopen", "system", "popen", "write_text", "write_bytes",
        "mkdir", "makedirs", "unlink", "remove", "rmtree", "touch", "rename",
        "now", "utcnow", "today", "time", "monotonic", "perf_counter",
        "time_ns", "getclock_info",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert node.lineno not in doc_lines, "no banned import may be needed"
            names = [a.name for a in node.names] if isinstance(node, ast.Import) \
                else ([node.module] if node.module else [])
            for name in names:
                assert name.split(".")[0] not in banned_imports, name
        elif isinstance(node, ast.Call) and node.lineno not in doc_lines:
            func = node.func
            label = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None)
            assert label not in banned_calls, f"banned call at line {node.lineno}: {label}"


def test_failure_vocabulary_is_closed_and_fully_exercised():
    """Every code the module can emit has at least one discriminating case
    here, and nothing is emitted outside the frozen vocabulary."""
    battery = [
        ({"owed_session": "garbage"}, {"owed_session_malformed"}),
        ({"served_index_bytes": None}, {"served_index_unavailable"}),
        ({"served_index_bytes": b""}, {"served_index_malformed"}),
        ({"served_index_bytes": b'{"schema": "x/v1"}'},
         {"served_index_schema_mismatch", "served_source_asof_missing"}),
        ({"accepted_health": None}, {"health_receipt_unavailable"}),
        ({"health_kw": {"schema": "x/v1"}}, {"health_receipt_schema_mismatch"}),
        ({"health_kw": {"index_sha256": None}}, {"health_hash_missing"}),
        ({"health_kw": {"source_asof": None}}, {"source_asof_missing"}),
        ({"index_kw": {"source_asof": THU}}, {"source_asof_stale"}),
        ({"index_kw": {"source_asof": THU}, "owed_session": THU,
          "health_kw": {"source_asof": FRI}}, {"served_source_asof_mismatch"}),
        ({"reader_observed_at": None}, {"reader_clock_missing"}),
        ({"reader_observed_at": "2026-10-30T22:11:03"}, {"reader_clock_not_utc"}),
        ({"reader_observed_at": "garbage"}, {"reader_clock_unqualified"}),
        ({"computed_at": None}, {"computed_at_missing"}),
        ({"computed_at": "2026-10-30 21:58:41"}, {"computed_at_unqualified"}),
        ({"health_kw": {"published_at": None}}, {"published_at_missing"}),
        ({"health_kw": {"published_at": "nope"}}, {"published_at_unqualified"}),
        ({"health_kw": {"checkpoint": ""}}, {"checkpoint_missing"}),
        ({"index_kw": {"source_delayed": True}}, {"source_delayed"}),
        ({"index_kw": {"source_unknown": True}}, {"source_unknown"}),
        ({"index_kw": {"source_mixed_vintage": True}}, {"source_mixed_vintage"}),
        ({"artifact_hashes": {"index": "nope"}},
         {"artifact_hashes_unqualified", "artifact_bundle_incomplete"}),
        ({"artifact_hashes": None}, {"artifact_hashes_missing"}),
        ({"artifact_hashes": {"index": digest(index_bytes())}},
         {"artifact_bundle_incomplete"}),
        ({"artifact_hashes": {**synthetic_artifact_hashes(digest(index_bytes())),
                              "unrelated": digest(b"unrelated-bytes")}},
         {"artifact_bundle_unrecognized_entry"}),
        ({"artifact_hashes": {**synthetic_artifact_hashes(digest(index_bytes())),
                              "board": "NOTAHASH"}},
         {"artifact_hashes_unqualified"}),
        ({"accepted_bundle": None}, {"accepted_bundle_missing"}),
        ({"accepted_bundle": "the receipt says so"}, {"accepted_bundle_malformed"}),
        ({"accepted_bundle": synthetic_accepted_bundle(
            synthetic_artifact_hashes(digest(index_bytes())), bundle_id="")},
         {"accepted_bundle_malformed"}),
        ({"accepted_bundle": {**synthetic_accepted_bundle(
            synthetic_artifact_hashes(digest(index_bytes()))),
            "artifact_hashes": {"index": digest(index_bytes())}}},
         {"accepted_bundle_malformed"}),
        ({"reader_proof": None}, {"reader_proof_missing"}),
        ({"reader_proof": {"served_bundle_id": "has spaces"}},
         {"reader_proof_malformed"}),
        ({"reader_proof": synthetic_reader_proof(bundle_id=SYNTH_OTHER_BUNDLE_ID)},
         {"bundle_id_mismatch"}),
        ({"artifact_hashes": {**synthetic_artifact_hashes(digest(index_bytes())),
                              "theme_state": digest(b"drifted-theme-state")}},
         {"artifact_bundle_mismatch"}),
        ({"artifact_hashes": {**synthetic_artifact_hashes(digest(index_bytes())),
                              "index": digest(b"not-the-served-bytes")}},
         {"artifact_bundle_mismatch", "artifact_index_digest_mismatch"}),
        ({"artifact_hashes": synthetic_artifact_hashes(digest(b"drifted-index-bytes")),
          "accepted_bundle": synthetic_accepted_bundle(
              synthetic_artifact_hashes(digest(b"drifted-index-bytes"))),
          "health_kw": {"index_sha256": digest(b"a-third-bundle")}},
         {"served_digest_mismatch", "artifact_index_digest_mismatch",
          "bundle_index_digest_mismatch"}),
        ({"accepted_bundle": synthetic_accepted_bundle(
            synthetic_artifact_hashes(digest(index_bytes())), bundle_id=CHECKPOINT),
          "reader_proof": synthetic_reader_proof(bundle_id=CHECKPOINT)},
         {"bundle_id_checkpoint_conflated"}),
    ]
    seen: set[str] = set()
    for over, expected in battery:
        out = manifest_call(**over)
        assert out["failures"], over
        seen.update(out["failures"])
        assert expected <= set(out["failures"]), (over, out["failures"])
    assert seen == set(MAN.FAILURE_CODES)
