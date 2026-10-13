"""Normal private economic refresh, and the public wire path it must not touch.

Synthetic fixtures only. The driver calls the real public-wire publisher, the
stage augmenter, and the Task-4 prepare/publish/load_economic_closure readers
against a strict local store. It does not construct a fake publication result.
"""
from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

import pytest

from engine.earnings_narrative import private_publication as private_publication
from engine.earnings_narrative.extract import build_evidence_pair
from engine.earnings_narrative.generation import EvidencePair, write_generation
from engine.earnings_narrative.private_economic_stage import (
    AUTHORITY_CEILING,
    PriorClosureUnavailable,
    PrivateEconomicStageError,
    assert_public_workspace_admission,
    augment_private_stage,
    load_verified_prior,
)
from engine.earnings_narrative.private_publication import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_V2,
    RECORD_SCHEMA_V2,
    load_economic_closure,
    load_private_manifest,
    prepare_private_publication,
    publish_private_publication,
)
from engine.earnings_narrative.public_wire import (
    build_public_wire_manifest,
    compile_public_wire_article,
)
from engine.earnings_narrative.story_store import write_story_packet_generation
from engine.earnings_transcript_intake import canonical_body_sha256
from engine.research_vault.r2_store import LocalStore
from scripts import build_earnings_public_wire as wire_builder
from scripts import refresh_event_workspaces
from scripts.build_earnings_public_wire import PublicWireBuildError, publish_public_wire
from tests.earnings_economic_fixtures import fixture_http_get
from tests.earnings_economic_private_fixtures import rights_registry


PINNED_NOW_ISO = "2026-08-01T00:00:00+00:00"
OBSERVED_AT = "2026-07-29T18:00:00Z"
LATER_OBSERVED_AT = "2026-07-30T19:00:00Z"
CURRENTNESS_CLOCK = "2026-07-29T18:30:00Z"
PENDING_CLOCK = "2026-07-30T20:00:00Z"
PRIVATE_SENTINEL_MARKERS = (
    "earnings.economic_interpretation/v1",
    "earnings.tier_payload/v2",
    "pg-economic-dossier",
    "pg_diluted_eps",
)
_COMPANY_READER = lambda _params: {
    "available": True,
    "generation_id": "c" * 24,
    "company": {"display_name": "Apple Inc."},
    "latest_event": {
        "fiscal_year": 2026,
        "fiscal_quarter": 1,
        "call_date": "2026-01-30",
    },
    "history": [],
}


class UnreadableStore(LocalStore):
    """Strict store whose every read fails. The pointer file is left untouched."""

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int):
        raise RuntimeError("injected private store read failure")


def _snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _wire_publication(tmp_path: Path, wire: str):
    growth = "12" if wire == "w1" else "14"
    revenue = "120" if wire == "w1" else "130"
    body = {
        "schema": "mastermind.tx/v1",
        "ticker": "AAPL",
        "id": "2026Q1",
        "period": "Q1 FY2026",
        "date": "2026-01-30",
        "title": "AAPL earnings call",
        "segments": [
            {
                "speaker": "Chief Executive Officer",
                "role": "executive",
                "text": (
                    f"Revenue grew {growth}% to {revenue} million, "
                    "while gross margin reached 45%."
                ),
            },
            {
                "speaker": "Chief Financial Officer",
                "role": "executive",
                "text": "We expect revenue of 500 million and an operating margin of 20%.",
            },
            {
                "speaker": "Chief Executive Officer",
                "role": "executive",
                "text": "We will invest 50 million in capacity and continue repurchases.",
            },
            {
                "speaker": "Chief Financial Officer",
                "role": "executive",
                "text": "Supply constraints could pressure margins by 200 bps.",
            },
        ],
    }
    body_sha = canonical_body_sha256(body)
    index = {
        "schema": "mastermind.tx-index/v1",
        "generated_at": "2026-02-01T00:00:00Z",
        "symbols": {"AAPL": ["2026Q1"]},
        "revisions": {"AAPL/2026Q1": body_sha},
        "dates": {"AAPL/2026Q1": "2026-01-30"},
        "body_count": 1,
        "symbol_count": 1,
    }
    fact_pack, claim_graph = build_evidence_pair(
        body,
        index_payload=index,
        indexed_body_sha256=body_sha,
        index_generated_at=index["generated_at"],
    )
    evidence = tmp_path / "evidence"
    write_generation(
        evidence,
        [EvidencePair(fact_pack=fact_pack, claim_graph=claim_graph, transcript=body)],
        coverage={
            "selection_policy": "explicit_input",
            "batch_limit": 1,
            "historical_completeness": False,
            "index_body_count": 1,
            "index_generated_at": index["generated_at"],
        },
    )
    story_store = tmp_path / "story"
    _generation, source_manifest = write_story_packet_generation(story_store, evidence)
    source_manifest_bytes = (story_store / "manifest.json").read_bytes()
    entry = source_manifest["packets"]["AAPL/2026Q1"]
    packet = json.loads((story_store / entry["object_key"]).read_bytes())
    receipt = source_manifest["files"][entry["object_key"]]
    article = compile_public_wire_article(
        packet,
        policy_snapshot=source_manifest["policy"]["snapshot"],
        generation_id=source_manifest["generation_id"],
        object_key=entry["object_key"],
        object_sha256=receipt["sha256"],
        object_bytes=receipt["bytes"],
    )
    publication = build_public_wire_manifest(
        [article],
        source_generation_id=source_manifest["generation_id"],
        source_manifest_sha256=sha256(source_manifest_bytes).hexdigest(),
        source_packet_count=1,
        source_packet_manifest_schema=source_manifest["schema"],
    )
    return publication


def _acquire(case: str, *, currentness: str, checked_at: str) -> dict:
    original = refresh_event_workspaces._PACE_S
    refresh_event_workspaces._PACE_S = 0
    try:
        acquisition = refresh_event_workspaces.acquire_results_filing(
            cik="0000080424",
            http_get=fixture_http_get(case),
            trace=[].append,
        )
    finally:
        refresh_event_workspaces._PACE_S = original
    acquisition["currentness"] = {"state": currentness, "checked_at": checked_at}
    return acquisition


def _source_acquisition(source: str | None):
    if source is None:
        return None
    if source == "pg1":
        return _acquire("same_source_rebuild", currentness="up_to_date", checked_at=CURRENTNESS_CLOCK)
    if source == "pg2_bad":
        return _acquire("newer_fetch_failed", currentness="newer_source_pending", checked_at=PENDING_CLOCK)
    if source == "malformed":
        return {"outcome": "malformed"}
    if source == "withdrawn":
        return {"withdrawn": True}
    if source == "missing_currentness":
        acquisition = _acquire("same_source_rebuild", currentness="up_to_date", checked_at=CURRENTNESS_CLOCK)
        del acquisition["currentness"]
        return acquisition
    raise AssertionError(f"unknown economic source fixture: {source}")


def _permit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        private_publication,
        "NATIVE_RIGHTS_REGISTRY_PATH",
        rights_registry(tmp_path / "rights"),
    )


def _publish_wire(publication, out_dir: Path, private_dir: Path, *, economic_refresh=None):
    from datetime import datetime, timezone
    publish_public_wire(
        publication,
        out_dir=out_dir,
        private_out_dir=private_dir,
        company_reader=_COMPANY_READER,
        now=datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc),
        economic_refresh=economic_refresh,
    )


class _Receipt:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def run_economic_wire_fixture(tmp_path: Path, *, wire: str, source: str | None, observed_at: str = OBSERVED_AT):
    """Drive one real wire publish plus, when requested, private prepare/publish/read."""
    index = len(list(tmp_path.glob("run-*")))
    run_dir = tmp_path / f"run-{index}-{wire}"
    publication = _wire_publication(run_dir / "inputs", wire)
    public_dir = run_dir / "public"
    private_dir = run_dir / "private-stage"
    store_root = tmp_path / "private-r2"
    store = LocalStore(store_root)
    acquisition = _source_acquisition(source)
    if source is None:
        _publish_wire(publication, public_dir, private_dir)
    else:
        prior = load_verified_prior(store)
        _publish_wire(
            publication,
            public_dir,
            private_dir,
            economic_refresh={
                "acquisition": acquisition,
                "prior_closure": prior,
                "observed_at": observed_at,
                "store": store,
            },
        )
    prepared = prepare_private_publication(private_dir)
    publish_private_publication(store, prepared)
    manifest = load_private_manifest(store)
    public_blob = b"\n".join(payload for _name, payload in sorted(_snapshot(public_dir).items()))
    sentinel = any(marker.encode("utf-8") in public_blob for marker in PRIVATE_SENTINEL_MARKERS)
    closure = None
    verified = False
    if manifest.get("schema") == MANIFEST_SCHEMA_V2:
        slots = manifest["native"]["economic_slots"]
        if slots:
            slug = next(iter(slots.values()))["slug"]
            closure = load_economic_closure(store, manifest=manifest, slug=slug)
            verified = closure["interpretation"]["authority"] == {
                key: False for key in closure["interpretation"]["authority"]
            }
    source_sha = None
    first_observed = None
    interpretation_id = None
    currentness = None
    if closure is not None:
        newest = closure["chain"][-1]
        source_sha = newest["document"]["content_sha256"]
        first_observed = newest["workspace"]["lifecycle"]["observed_at"]
        interpretation_id = closure["interpretation"]["interpretation_id"]
        raw_currentness = closure["selection"]["selection"]["currentness"]
        currentness = raw_currentness["state"] if isinstance(raw_currentness, dict) else "currentness_unverified"
    return _Receipt(
        public_dir=public_dir,
        private_dir=private_dir,
        store=store,
        manifest=manifest,
        closure=closure,
        pg_source_sha=source_sha,
        pg_first_observed_at=first_observed,
        pg_interpretation_id=interpretation_id,
        currentness=currentness,
        native_closure_verified=verified,
        public_contains_private_sentinel=sentinel,
        schema=manifest.get("schema"),
    )


def test_public_output_without_private_stage_is_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")
    from datetime import datetime, timezone
    now = datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc)
    first_public = tmp_path / "first-public"
    second_public = tmp_path / "second-public"
    staged_public = tmp_path / "staged-public"
    first_private = tmp_path / "first-private"
    second_private = tmp_path / "second-private"
    staged_private = tmp_path / "staged-private"
    publish_public_wire(
        publication, out_dir=first_public, private_out_dir=first_private,
        company_reader=_COMPANY_READER, now=now,
    )
    publish_public_wire(
        publication, out_dir=second_public, private_out_dir=second_private,
        company_reader=_COMPANY_READER, now=now, economic_refresh=None,
    )
    assert _snapshot(first_public) == _snapshot(second_public)
    assert _snapshot(first_private) == _snapshot(second_private)
    assert not (first_private / "native").exists()

    _permit(monkeypatch, tmp_path)
    acquisition = _source_acquisition("pg1")
    publish_public_wire(
        publication, out_dir=staged_public, private_out_dir=staged_private,
        company_reader=_COMPANY_READER, now=now,
        economic_refresh={
            "acquisition": acquisition,
            "prior_closure": None,
            "observed_at": OBSERVED_AT,
        },
    )
    assert _snapshot(staged_public) == _snapshot(first_public)
    staged_blob = b"\n".join(payload for _name, payload in sorted(_snapshot(staged_private).items()))
    public_blob = b"\n".join(payload for _name, payload in sorted(_snapshot(staged_public).items()))
    assert b"pg-economic-dossier" in staged_blob
    assert all(marker.encode("utf-8") not in public_blob for marker in PRIVATE_SENTINEL_MARKERS)


def test_absent_economic_refresh_does_not_invoke_the_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    publication = _wire_publication(tmp_path / "inputs", "w1")

    def boom(*_args, **_kwargs):
        raise AssertionError("augment_private_stage must not run without an economic stage")

    monkeypatch.setattr(wire_builder, "augment_private_stage", boom)
    from datetime import datetime, timezone
    publish_public_wire(
        publication,
        out_dir=tmp_path / "public",
        private_out_dir=tmp_path / "private",
        company_reader=_COMPANY_READER,
        now=datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc),
    )
    assert not (tmp_path / "private" / "native").exists()


def test_private_pg_workspace_is_refused_at_public_admission(tmp_path: Path) -> None:
    acquisition = _source_acquisition("pg1")
    from engine.company_intelligence.pg_profile import prepare_pg_workspace
    prepared = prepare_pg_workspace(acquisition, prior=None, observed_at=OBSERVED_AT)
    workspace = dict(prepared["workspace"])
    workspace["private"] = False
    with pytest.raises(Exception, match="private_workspace_refused"):
        assert_public_workspace_admission(workspace)
    publication = _wire_publication(tmp_path / "inputs", "w1")
    from datetime import datetime, timezone
    with pytest.raises(PublicWireBuildError, match="private economic"):
        publish_public_wire(
            publication,
            out_dir=tmp_path / "public",
            private_out_dir=tmp_path / "private",
            company_reader=_COMPANY_READER,
            now=datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc),
            economic_refresh={"public_workspaces": (workspace,), "acquisition": None},
        )
    assert _snapshot(tmp_path / "public") == {}


def test_public_apple_and_legacy_pg_teaser_stay_admitted() -> None:
    apple = {
        "issuer": {"company_id": "cik:0000320193", "ticker": "AAPL"},
        "facts": [{"metric": "revenue", "source_span": {"rights_profile": "rp_public_primary_v1"}}],
        "authority": "context_only",
    }
    assert_public_workspace_admission(apple)
    teaser = {
        "issuer": {"company_id": "cik:0000080424", "ticker": "PG"},
        "facts": [{"metric": "revenue", "source_span": {"rights_profile": "rp_public_primary_v1"}}],
        "authority": "context_only",
    }
    assert_public_workspace_admission(teaser)


def test_public_admission_refuses_private_content_outside_a_plain_dict() -> None:
    """The guard reads metric ids and the rights profile, not the container type."""
    from collections import OrderedDict
    from types import MappingProxyType

    from engine.company_intelligence.pg_profile import PG_PRIVATE_RIGHTS_PROFILE

    ordered = OrderedDict((
        ("private", False),
        ("metric", "pg_diluted_eps"),
    ))
    with pytest.raises(PrivateEconomicStageError, match="private_workspace_refused"):
        assert_public_workspace_admission(ordered)

    nested_rights = {
        "private": False,
        "facts": MappingProxyType({
            "rows": (
                {
                    "metric": "revenue",
                    "source_span": {"rights_profile": PG_PRIVATE_RIGHTS_PROFILE},
                },
            ),
        }),
    }
    with pytest.raises(PrivateEconomicStageError, match="private_workspace_refused"):
        assert_public_workspace_admission(nested_rights)

    public_proxy = MappingProxyType({
        "issuer": {"company_id": "cik:0000320193", "ticker": "AAPL"},
        "facts": [{"metric": "revenue", "source_span": {"rights_profile": "rp_public_primary_v1"}}],
        "authority": "context_only",
    })
    assert_public_workspace_admission(public_proxy)


def test_public_admission_refuses_str_subclass_private_metric_id() -> None:
    """A str-subclass metric id equal to pg_diluted_eps is the private profile."""

    class _MetricId(str):
        pass

    private_metric = {
        "private": False,
        "facts": [{"metric": _MetricId("pg_diluted_eps")}],
    }
    with pytest.raises(PrivateEconomicStageError, match="private_workspace_refused"):
        assert_public_workspace_admission(private_metric)

    public_metric = {
        "issuer": {"company_id": "cik:0000320193", "ticker": "AAPL"},
        "facts": [{
            "metric": _MetricId("revenue"),
            "source_span": {"rights_profile": "rp_public_primary_v1"},
        }],
        "authority": "context_only",
    }
    assert_public_workspace_admission(public_metric)


def test_clean_v1_baseline_has_no_native_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source=None)
    assert receipt.schema == MANIFEST_SCHEMA
    assert "native" not in receipt.manifest
    assert receipt.native_closure_verified is False
    assert receipt.public_contains_private_sentinel is False
    assert not (receipt.private_dir / "native").exists()


def test_first_private_native_launch_publishes_v2_closure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    run_economic_wire_fixture(tmp_path, wire="w1", source=None)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    assert receipt.schema == MANIFEST_SCHEMA_V2
    assert receipt.native_closure_verified is True
    assert receipt.pg_source_sha
    assert receipt.pg_interpretation_id
    assert receipt.currentness == "up_to_date"
    assert receipt.public_contains_private_sentinel is False
    record = receipt.closure["record"]
    assert record["schema"] == RECORD_SCHEMA_V2
    assert record["page"] == "earnings_economic_dossier"
    assert record["public_facts"] == 0
    assert record["facts_html"] == ""
    assert AUTHORITY_CEILING == "research_display_only"
    assert all(value is False for value in record["economic_interpretation"]["authority"].values())


def test_unrelated_wire_update_preserves_private_native_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    calls: list[str] = []
    original = load_economic_closure

    def wrapped(store, *, manifest, slug, interpretation="verify"):
        calls.append(slug)
        return original(store, manifest=manifest, slug=slug, interpretation=interpretation)

    monkeypatch.setattr(
        "engine.earnings_narrative.private_economic_stage.load_economic_closure",
        wrapped,
    )
    first = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    second = run_economic_wire_fixture(tmp_path, wire="w2", source="pg1", observed_at=OBSERVED_AT)
    assert second.pg_source_sha == first.pg_source_sha
    assert second.pg_first_observed_at == first.pg_first_observed_at
    assert second.pg_interpretation_id == first.pg_interpretation_id
    assert second.native_closure_verified
    assert not second.public_contains_private_sentinel
    assert calls, "the refresh must read the prior through load_economic_closure"


def test_unchanged_pg_source_reuses_interpretation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    first = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    second = run_economic_wire_fixture(
        tmp_path, wire="w1", source="pg1", observed_at=LATER_OBSERVED_AT,
    )
    assert second.pg_source_sha == first.pg_source_sha
    assert second.pg_first_observed_at == first.pg_first_observed_at
    assert second.pg_interpretation_id == first.pg_interpretation_id
    assert second.currentness == "up_to_date"


def test_newer_bad_source_keeps_dated_last_good_not_false_freshness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    old = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    new = run_economic_wire_fixture(tmp_path, wire="w2", source="pg2_bad", observed_at=LATER_OBSERVED_AT)
    assert new.pg_source_sha == old.pg_source_sha
    assert new.currentness == "newer_source_pending"
    assert new.pg_first_observed_at == old.pg_first_observed_at
    assert new.public_contains_private_sentinel is False


def test_malformed_new_source_keeps_last_good(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    old = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    new = run_economic_wire_fixture(tmp_path, wire="w1", source="malformed", observed_at=LATER_OBSERVED_AT)
    assert new.pg_source_sha == old.pg_source_sha
    assert new.pg_first_observed_at == old.pg_first_observed_at
    assert new.currentness == "newer_source_pending"
    assert new.native_closure_verified


def test_source_withdrawal_does_not_fabricate_a_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    old = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    new = run_economic_wire_fixture(tmp_path, wire="w1", source="withdrawn", observed_at=LATER_OBSERVED_AT)
    assert new.pg_source_sha == old.pg_source_sha
    assert new.pg_first_observed_at == old.pg_first_observed_at
    assert new.pg_interpretation_id == old.pg_interpretation_id
    assert len(new.closure["chain"]) == len(old.closure["chain"])


def test_unreadable_prior_does_not_mint_a_root_or_move_the_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    baseline = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    pointer_key = private_publication.POINTER_KEY
    before = baseline.store.get_bytes_strict_bounded(pointer_key, private_publication.MAX_POINTER_BYTES)
    boom = UnreadableStore(tmp_path / "private-r2")
    publication = _wire_publication(tmp_path / "blocked-inputs", "w2")
    from datetime import datetime, timezone
    with pytest.raises(PriorClosureUnavailable):
        publish_public_wire(
            publication,
            out_dir=tmp_path / "blocked-public",
            private_out_dir=tmp_path / "blocked-private",
            company_reader=_COMPANY_READER,
            now=datetime.fromisoformat(PINNED_NOW_ISO).astimezone(timezone.utc),
            economic_refresh={
                "store": boom,
                "acquisition": _source_acquisition("pg1"),
                "observed_at": LATER_OBSERVED_AT,
            },
        )
    after = LocalStore(tmp_path / "private-r2").get_bytes_strict_bounded(
        pointer_key, private_publication.MAX_POINTER_BYTES,
    )
    assert after == before
    assert _snapshot(tmp_path / "blocked-public") == {}
    assert not (tmp_path / "blocked-private").exists()
    reloaded = load_private_manifest(LocalStore(tmp_path / "private-r2"))
    assert reloaded["generation_id"] == baseline.manifest["generation_id"]


def test_missing_collector_currentness_is_not_fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(
        tmp_path, wire="w1", source="missing_currentness", observed_at=OBSERVED_AT,
    )
    assert receipt.currentness == "currentness_unverified"
    assert receipt.currentness != "up_to_date"
    assert receipt.native_closure_verified
    stored = receipt.closure["selection"]["selection"]["currentness"]
    assert stored is None


def _replay_forged(
    stage: Path,
    closure: dict,
    *,
    generation_id: str | None = None,
    slug: str | None = None,
) -> None:
    forged = copy.deepcopy(closure)
    if generation_id is not None:
        forged["chain"][-1]["workspace"]["generation_id"] = generation_id
        # A stored handle list would die in interpretation before the writer.
        # Clearing it keeps the refusal on the path join itself.
        forged["selection"]["selection"]["facts"] = None
    if slug is not None:
        forged["record"]["slug"] = slug
    augment_private_stage(
        stage,
        acquisition=None,
        prior_closure=forged,
        observed_at=OBSERVED_AT,
    )


def test_generation_id_and_slug_must_stay_inside_the_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generation id is 24 hex chars and a validate_slug, and both files stay in the stage."""
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    original = closure["chain"][-1]["workspace"]["generation_id"]
    assert re.fullmatch(r"[a-f0-9]{24}", original)
    baseline = tmp_path / "baseline-stage"
    shutil.copytree(receipt.private_dir, baseline)
    outside_dir = tmp_path / "escaped"
    outside_dir.mkdir()
    absolute_target = outside_dir / "pwn.json"
    short = "a" * 23
    slug_dir = tmp_path / "slug-escaped"
    slug_dir.mkdir()
    slug_target = slug_dir / "pwn.json"
    cases: list[tuple[str, dict, Path]] = [
        ("generation ../x", {"generation_id": "../x"}, Path("native") / "x.json"),
        (
            "generation absolute",
            {"generation_id": str(absolute_target.with_suffix(""))},
            absolute_target,
        ),
        (
            "generation 23-char",
            {"generation_id": short},
            Path("native") / "workspaces" / f"{short}.json",
        ),
        ("slug ../x", {"slug": "../x"}, Path("x.json")),
        ("slug absolute", {"slug": str(slug_target.with_suffix(""))}, slug_target),
        ("slug Bad", {"slug": "Bad"}, Path("records") / "Bad.json"),
    ]
    failures: list[str] = []
    for label, forged_fields, leaked_path in cases:
        stage = tmp_path / f"stage-{label.replace(' ', '-')}"
        shutil.copytree(baseline, stage)
        leaked = leaked_path if leaked_path.is_absolute() else stage / leaked_path
        before = sorted(path.name for path in (stage / "native" / "workspaces").glob("*.json"))
        assert before, label
        try:
            _replay_forged(stage, closure, **forged_fields)
        except PrivateEconomicStageError as exc:
            after = sorted(path.name for path in (stage / "native" / "workspaces").glob("*.json"))
            if exc.reason != "unsafe_path" or leaked.exists() or after != before:
                failures.append(
                    f"{label} reason={exc.reason} leaked={leaked.exists()} "
                    f"preserved={after == before} path={leaked}"
                )
        else:
            failures.append(
                f"DID NOT RAISE PrivateEconomicStageError for {label}; "
                f"leaked={leaked.exists()} path={leaked}"
            )
    assert not failures, "\n".join(failures)
