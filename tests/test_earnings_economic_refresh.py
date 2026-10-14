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



def test_public_admission_refuses_hostile_str_subclass() -> None:
    """A str subclass faking equality cannot smuggle the private profile past admission.

    ``Lie`` returns False from ``__eq__`` and a constant hash, so both the metric
    membership test and the rights-profile comparison are evaded unless the guard
    compares a plain-str copy.
    """
    from engine.company_intelligence.pg_profile import PG_PRIVATE_RIGHTS_PROFILE
    from engine.earnings_narrative import private_economic_stage as stage_module

    class Lie(str):
        def __eq__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return 12345

    assert Lie("pg_diluted_eps") not in stage_module._PRIVATE_METRICS
    assert str.__str__(Lie("pg_diluted_eps")) == "pg_diluted_eps"
    assert type(str.__str__(Lie("pg_diluted_eps"))) is str

    with_metric = {"private": False, "facts": [{"metric": Lie("pg_diluted_eps")}]}
    with pytest.raises(PrivateEconomicStageError, match="private_workspace_refused"):
        assert_public_workspace_admission(with_metric)

    with_profile = {
        "private": False,
        "facts": [{
            "metric": "revenue",
            "source_span": {"rights_profile": Lie(PG_PRIVATE_RIGHTS_PROFILE)},
        }],
    }
    with pytest.raises(PrivateEconomicStageError, match="private_workspace_refused"):
        assert_public_workspace_admission(with_profile)

    # CONTROL: a hostile type carrying public content stays admitted.
    public = {
        "issuer": {"company_id": "cik:0000320193", "ticker": "AAPL"},
        "facts": [{
            "metric": Lie("revenue"),
            "source_span": {"rights_profile": Lie("rp_public_primary_v1")},
        }],
        "authority": "context_only",
    }
    assert_public_workspace_admission(public)


def test_stage_refuses_cross_issuer_company_id_from_a_hostile_str_subclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``cross_issuer`` guard must compare a plain-str copy, not the caller's id.

    ``company_id != pg_issuer().company_id`` asks a caller-controlled id object
    to perform its own ``__ne__``: a ``str`` subclass overriding both ``__eq__``
    and ``__ne__`` answers "not unequal", so the raw guard never raises and the
    foreign issuer leaks into the interpretation. The guard compares a
    ``_plain_str`` copy instead; a non-str id keeps the same typed refusal
    (``PrivateEconomicStageError("cross_issuer")``, engine/earnings_narrative/
    private_economic_stage.py:472).
    """
    from engine.company_intelligence import pg_profile
    from engine.earnings_narrative import private_economic_stage as stage_module

    class LieIssuerId(str):
        def __eq__(self, other: object) -> bool:
            return False

        def __ne__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return 12345

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    foreign = "cik:0000999999"
    assert str(foreign) != pg_profile.pg_issuer().company_id
    baseline = tmp_path / "issuer-baseline"
    shutil.copytree(receipt.private_dir, baseline)

    for label, forged_id in (("hostile-str", LieIssuerId(foreign)), ("non-str", None)):
        forged = copy.deepcopy(closure)
        forged["chain"][-1]["workspace"]["issuer"]["company_id"] = forged_id
        stage = tmp_path / f"issuer-stage-{label}"
        shutil.copytree(baseline, stage)
        before = _snapshot(stage)
        with pytest.raises(PrivateEconomicStageError, match="cross_issuer"):
            augment_private_stage(
                stage, acquisition=None, prior_closure=forged, observed_at=LATER_OBSERVED_AT,
            )
        assert _snapshot(stage) == before

    # CONTROL: a plain-str same-issuer id stays admitted.
    control = tmp_path / "issuer-stage-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
    assert type(stage_module._plain_str(LieIssuerId(foreign))) is str
    assert str.__str__(LieIssuerId(foreign)) == foreign


def test_hostile_document_id_cannot_dedup_away_a_newly_prepared_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``same_document`` must compare plain-str copies of both ids it is given.

    A stored closure is caller data: with the raw ``==`` a ``str`` subclass
    whose ``__eq__`` answers True makes the dedup believe the freshly prepared
    document is already stored, and the new document is silently dropped from
    the chain. The comparison takes ``_plain_str`` copies of both sides.
    """

    class LieDocId(str):
        def __eq__(self, other: object) -> bool:
            return True

        def __ne__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return 12345

    class ForgingChain(list):
        """Caller-controlled closure chain with a hostile second ``[-1]`` read.

        The first ``[-1]`` read is the prior handed to ``prepare_pg_workspace``
        (private_economic_stage.py:201 via ``_prepare_prior``); it returns the
        genuine stored item so preparation succeeds and produces a new,
        different document. The second ``[-1]`` read is the dedup comparison
        (private_economic_stage.py:222); it returns a copy whose
        ``document_id`` forges equality with anything.
        """

        def __init__(self, items: list, *, forged_doc_id: str) -> None:
            super().__init__(items)
            self._forged_doc_id = forged_doc_id
            self._negative_reads = 0

        def __getitem__(self, index):
            item = list.__getitem__(self, index)
            if index == -1:
                self._negative_reads += 1
                if self._negative_reads >= 2:
                    forged = dict(item)
                    document = dict(item["document"])
                    document["document_id"] = LieDocId(self._forged_doc_id)
                    forged["document"] = document
                    return forged
            return item

    def _links(stage: Path, slug: str) -> list:
        latest = json.loads((stage / "native" / "latest.json").read_bytes())
        return latest["selections"][slug]["chain"]

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    slug = closure["record"]["slug"]
    amendment = _acquire("amendment_sequence", currentness="up_to_date", checked_at=PENDING_CLOCK)

    # CONTROL: plain-str ids still append a genuinely different prepared document.
    control = tmp_path / "stage-dedup-control"
    shutil.copytree(receipt.private_dir, control)
    written = augment_private_stage(
        control, acquisition=copy.deepcopy(amendment), prior_closure=closure,
        observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
    control_links = _links(control, slug)
    assert len(control_links) == 2
    assert control_links[0]["document"] != control_links[1]["document"]

    # HOSTILE: the forged stored id claims equality with the new prepared doc.
    forged = copy.deepcopy(closure)
    forged["chain"] = ForgingChain(
        list(closure["chain"]), forged_doc_id="disclosure_document_" + "f" * 64,
    )
    stage = tmp_path / "stage-dedup-hostile"
    shutil.copytree(receipt.private_dir, stage)
    written = augment_private_stage(
        stage, acquisition=copy.deepcopy(amendment), prior_closure=forged,
        observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
    assert forged["chain"]._negative_reads == 2, (
        "the forged stored id never reached the same_document comparison"
    )
    links = _links(stage, slug)
    assert len(links) == 2, f"hostile __eq__ silently dropped the prepared document: links={links}"
    assert links[-1]["document"] != links[0]["document"]


def test_stage_refuses_a_content_digest_from_a_hostile_str_subclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``mismatched_source`` must compare the computed digest, not the caller's answer.

    The guard reads ``content_digest != item["document"].get("content_sha256")``
    (private_economic_stage.py:521): the right operand is caller data, and for a
    proper ``str`` subclass Python tries the reflected ``__ne__`` first, so a lie
    of ``False`` makes the comparison read "not unequal" and a stored document
    declaring a wrong digest is staged anyway. The guard now reads the declared
    digest into a local and refuses anything that is not an exact ``str`` before
    comparing it, the idiom private_publication.py:1005-1007 uses.
    """

    class LieNe(str):
        def __eq__(self, other: object) -> bool:
            return True

        def __ne__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return 12345

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    stored_digest = closure["chain"][-1]["document"]["content_sha256"]
    assert type(stored_digest) is str
    wrong = sha256(b"a different source body").hexdigest()
    assert wrong != stored_digest

    forged = copy.deepcopy(closure)
    forged["chain"][-1]["document"]["content_sha256"] = LieNe(wrong)
    stage = tmp_path / "stage-digest-hostile"
    shutil.copytree(receipt.private_dir, stage)
    with pytest.raises(PrivateEconomicStageError, match="mismatched_source"):
        augment_private_stage(
            stage, acquisition=None, prior_closure=forged, observed_at=LATER_OBSERVED_AT,
        )
    assert not (stage / "native" / "latest.json").exists()

    # CONTROL: the same replay with a plain-str correct digest stays admitted.
    control = tmp_path / "stage-digest-control"
    shutil.copytree(receipt.private_dir, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
    assert written["source_sha256"] == stored_digest


def test_stage_refuses_a_non_str_text_on_an_older_chain_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every chain item is encoded, so every item's text type must be checked.

    Only the newest item is type-checked today: ``text = newest["text"]`` then
    ``if type(text) is not str`` (private_economic_stage.py:472-474), while the
    body loop encodes every item with ``item["text"].encode("utf-8")``
    (private_economic_stage.py:519). An older stored item carrying bytes or an
    int therefore leaks a bare ``AttributeError`` past the CLI tuple at
    scripts/build_earnings_public_wire.py:1850 instead of a typed refusal.
    """
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    newest = closure["chain"][-1]
    baseline = tmp_path / "older-text-baseline"
    shutil.copytree(receipt.private_dir, baseline)

    for label, bad_text in (("bytes", b"bytes are not a source text"), ("int", 7)):
        older = copy.deepcopy(newest)
        older["workspace"]["generation_id"] = sha256(label.encode("utf-8")).hexdigest()[:24]
        older["text"] = bad_text
        forged = copy.deepcopy(closure)
        forged["chain"] = [older, copy.deepcopy(newest)]
        stage = tmp_path / f"stage-older-text-{label}"
        shutil.copytree(baseline, stage)
        with pytest.raises(PrivateEconomicStageError, match="mismatched_source"):
            augment_private_stage(
                stage, acquisition=None, prior_closure=forged, observed_at=LATER_OBSERVED_AT,
            )
        assert not (stage / "native" / "latest.json").exists()

    # CONTROL: the same two-item chain with plain-str texts is admitted.
    honest_older = copy.deepcopy(newest)
    honest_older["workspace"]["generation_id"] = sha256(b"control-item").hexdigest()[:24]
    control_closure = copy.deepcopy(closure)
    control_closure["chain"] = [honest_older, copy.deepcopy(newest)]
    control = tmp_path / "stage-older-text-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=control_closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


def test_stage_does_not_take_the_malformed_branch_for_a_hostile_outcome_str(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_malformed_marker`` may not ask a caller-owned object what it equals.

    ``acquisition.get("outcome") == "malformed"`` (private_economic_stage.py:321)
    compares the caller-controlled operand on the left with ``==``, while its
    sibling ``_withdrawn`` (private_economic_stage.py:316) already insists on
    ``is True``. A ``str`` subclass answering ``True`` therefore selects the
    malformed branch and the freshly prepared document is dropped. The seam is
    the public ``augment_private_stage``: the malformed branch reuses the stored
    closure only (one link, ``newer_source_pending``), while an honest fresh
    acquisition appends its own document (two links, the prepared currentness).
    """

    class LieEq(str):
        def __eq__(self, other: object) -> bool:
            return True

        def __ne__(self, other: object) -> bool:
            return False

        def __hash__(self) -> int:
            return 12345

    def _links(stage: Path, slug: str) -> list:
        latest = json.loads((stage / "native" / "latest.json").read_bytes())
        return latest["selections"][slug]["chain"]

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    slug = closure["record"]["slug"]
    amendment = _acquire("amendment_sequence", currentness="up_to_date", checked_at=PENDING_CLOCK)

    # PRECONDITION: the lie really does claim to be the malformed marker.
    liar = LieEq("not_a_malformed_marker")
    assert liar == "malformed"
    assert type(liar) is not str

    honest = tmp_path / "stage-marker-honest"
    shutil.copytree(receipt.private_dir, honest)
    honest_written = augment_private_stage(
        honest, acquisition=copy.deepcopy(amendment), prior_closure=closure,
        observed_at=LATER_OBSERVED_AT,
    )
    assert honest_written["wrote"] is True
    honest_links = _links(honest, slug)
    assert len(honest_links) == 2, f"the fixture must append a prepared document: {honest_links}"

    hostile = copy.deepcopy(amendment)
    hostile["outcome"] = LieEq("not_a_malformed_marker")
    stage = tmp_path / "stage-marker-hostile"
    shutil.copytree(receipt.private_dir, stage)
    written = augment_private_stage(
        stage, acquisition=hostile, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert len(_links(stage, slug)) == len(honest_links), (
        f"a hostile outcome str selected the malformed branch and dropped the "
        f"prepared document: written={written}"
    )
    assert written["currentness"] == honest_written["currentness"]

    # CONTROL: a plain "malformed" outcome still selects the malformed branch.
    marker = copy.deepcopy(amendment)
    marker["outcome"] = "malformed"
    control = tmp_path / "stage-marker-control"
    shutil.copytree(receipt.private_dir, control)
    control_written = augment_private_stage(
        control, acquisition=marker, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert control_written["currentness"] == "newer_source_pending"
    assert len(_links(control, slug)) == 1


def test_stage_maps_an_lstat_error_on_the_source_body_to_a_typed_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only ``FileNotFoundError`` means "absent"; any other ``OSError`` must refuse.

    The module does a plain ``import os`` (private_economic_stage.py:19) and the
    body probe calls ``os.lstat(body_path)`` inside ``try``/``except
    FileNotFoundError`` only (private_economic_stage.py:524-527), so a
    ``PermissionError`` or ``NotADirectoryError`` on the source-body path escapes
    raw. That is uncaught by the CLI tuple at
    scripts/build_earnings_public_wire.py:1850
    (``except (PublicWireBuildError, PrivateEconomicStageError) as exc:``). The
    probe now maps any other ``OSError`` to ``unreadable_stage_file``, the code
    the body read beside it already uses (private_economic_stage.py:533-534).
    """
    import os as os_module

    from engine.earnings_narrative import private_economic_stage as stage_module

    class _LstatGate:
        """Every ``os`` attribute delegates; only a source-body ``lstat`` is denied."""

        def __init__(self, real: object) -> None:
            self._real = real
            self.denied: list[str] = []

        def __getattr__(self, name: str):
            return getattr(self._real, name)

        def lstat(self, path, *args, **kwargs):
            as_text = os_module.fspath(path)
            if "source_bodies" in as_text:
                self.denied.append(as_text)
                raise PermissionError(13, "Permission denied", as_text)
            return self._real.lstat(path, *args, **kwargs)

    _permit(monkeypatch, tmp_path)
    permitted_registry = private_publication.NATIVE_RIGHTS_REGISTRY_PATH
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    digest = closure["chain"][-1]["document"]["content_sha256"]
    stage = tmp_path / "stage-lstat-denied"
    shutil.copytree(receipt.private_dir, stage)

    gate = _LstatGate(os_module)
    with monkeypatch.context() as patch:
        patch.setattr(stage_module, "os", gate)
        with pytest.raises(PrivateEconomicStageError, match="unreadable_stage_file"):
            augment_private_stage(
                stage, acquisition=None, prior_closure=closure,
                observed_at=LATER_OBSERVED_AT,
            )
    # The os gate is scoped by its own context, so this test's permit
    # precondition is still installed after the gate is released.
    assert private_publication.NATIVE_RIGHTS_REGISTRY_PATH is permitted_registry, (
        "releasing the os gate also reverted this test's own permit"
    )
    assert gate.denied, "the body probe never reached native/source_bodies"
    assert gate.denied[0].endswith(f"{digest}.txt")
    assert not (stage / "native" / "latest.json").exists()

    # CONTROL: with the real ``os`` the same replay still writes.
    control = tmp_path / "stage-lstat-control"
    shutil.copytree(receipt.private_dir, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


def test_stage_refuses_a_symlinked_source_body_before_reading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source-body read must not follow a planted symlink.

    ``_reset_native`` wipes ``native/`` inside ``_write_stage`` before the body
    loop reads ``native/source_bodies/<digest>.txt``, so a test cannot plant the
    link from outside the call. The narrowest seam that puts the link into the
    gap between the reset and the read is ``_reset_native`` itself: its only
    caller is ``_write_stage`` (engine/earnings_narrative/private_economic_stage.py:503),
    and the wrapper below runs the real reset first, then plants.
    ``_reset_native`` itself is not weakened.
    """
    from engine.earnings_narrative import private_economic_stage as stage_module

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    digest = closure["chain"][-1]["document"]["content_sha256"]
    victim = tmp_path / "outside-victim.txt"
    victim_bytes = b"a victim file outside the stage tree\n" * 8
    victim.write_bytes(victim_bytes)

    real_reset = stage_module._reset_native

    def _reset_then_plant(root: Path) -> Path:
        native = real_reset(root)
        (native / "source_bodies" / f"{digest}.txt").symlink_to(victim)
        return native

    monkeypatch.setattr(stage_module, "_reset_native", _reset_then_plant)
    stage = tmp_path / "stage-symlink-body"
    shutil.copytree(receipt.private_dir, stage)
    with pytest.raises(PrivateEconomicStageError, match="hardlinked_stage_file"):
        augment_private_stage(
            stage, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
        )
    assert victim.read_bytes() == victim_bytes
    link = stage / "native" / "source_bodies" / f"{digest}.txt"
    assert link.is_symlink()
    assert not (stage / "native" / "latest.json").exists()

    # CONTROL: the same replay with no planted link still writes.
    monkeypatch.setattr(stage_module, "_reset_native", real_reset)
    control = tmp_path / "stage-symlink-control"
    shutil.copytree(receipt.private_dir, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


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


def test_stage_refuses_a_hardlinked_stage_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A hardlink planted at a stage write path is refused, never truncated in place.

    ``records/<slug>.json`` is the stage path that pre-exists on a re-stage:
    ``_reset_native`` unlinks everything under ``native/`` before the native
    writes, and ``_stage_root`` only requires ``records/`` to be a directory.
    ``Path.write_bytes`` opens O_TRUNC on the existing inode, so a second name
    linked to it would be rewritten by the stage.
    """
    import os

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    slug = closure["record"]["slug"]
    stage = tmp_path / "stage-hardlink"
    shutil.copytree(receipt.private_dir, stage)

    record = stage / "records" / f"{slug}.json"
    assert record.is_file()
    victim = tmp_path / "victim-outside-stage.json"
    os.link(record, victim)
    original = victim.read_bytes()
    assert os.lstat(victim).st_ino == os.lstat(record).st_ino
    assert os.lstat(record).st_nlink == 2

    with pytest.raises(PrivateEconomicStageError, match="hardlinked_stage_file"):
        augment_private_stage(
            stage,
            acquisition=None,
            prior_closure=closure,
            observed_at=LATER_OBSERVED_AT,
        )
    assert victim.read_bytes() == original
    assert victim.stat().st_nlink == 2

    # CONTROL: the same re-stage over a plain (single-link) record still writes.
    victim.unlink()
    written = augment_private_stage(
        stage,
        acquisition=None,
        prior_closure=closure,
        observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
    assert record.read_bytes() == original
    assert json.loads(record.read_bytes())["slug"] == slug
    assert not [path for path in stage.rglob(".*") if path.is_file()], "temp residue left in the stage"


def test_stage_maps_lstat_errors_on_workspace_and_manifest_paths_to_typed_refusals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_write_stage_file`` must refuse every ``OSError``, not just a missing file.

    Independent review W15-V-9105c on 5951818e: the probe's own ``os.lstat``
    catch (private_economic_stage.py:419-421) maps only ``FileNotFoundError``
    to "absent", so a ``PermissionError`` on a ``native/workspaces/<id>.json``
    or ``native/latest.json`` target escaped raw — the reviewer observed
    ``PermissionError: [Errno 13] Permission denied`` past the CLI tuple at
    scripts/build_earnings_public_wire.py:1850. The probe now appends an
    ``except OSError`` mapped to ``unreadable_stage_file`` (FileNotFoundError
    still matches first), the same code the source-body probe already uses
    (private_economic_stage.py:543-544). The ``OSError`` arm over the swap is
    pinned by ``test_stage_maps_write_block_oserrors_to_a_typed_refusal``.
    """
    import os as os_module

    from engine.earnings_narrative import private_economic_stage as stage_module

    class _LstatGate:
        """Every ``os`` attribute delegates; only ``lstat`` on the needle is denied."""

        def __init__(self, real: object, needle: str) -> None:
            self._real = real
            self._needle = needle
            self.denied: list[str] = []

        def __getattr__(self, name: str):
            return getattr(self._real, name)

        def lstat(self, path, *args, **kwargs):
            as_text = os_module.fspath(path)
            if self._needle in as_text:
                self.denied.append(as_text)
                raise PermissionError(13, "Permission denied", as_text)
            return self._real.lstat(path, *args, **kwargs)

    _permit(monkeypatch, tmp_path)
    permitted_registry = private_publication.NATIVE_RIGHTS_REGISTRY_PATH
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    generation_id = closure["chain"][-1]["workspace"]["generation_id"]
    baseline = tmp_path / "stage-path-lstat-baseline"
    shutil.copytree(receipt.private_dir, baseline)

    def _file_names(root: Path, pattern: str) -> list[str]:
        return sorted(str(path) for path in root.rglob(pattern) if path.is_file())

    for needle, expected_tail, refuses_first_write in (
        ("native/workspaces", f"{generation_id}.json", True),
        # native/latest.json (engine:583) is written after the native chain
        # files; records/<slug>.json follows (engine:584-587). Earlier chain
        # files therefore legitimately land before this denial.
        ("native/latest.json", "latest.json", False),
    ):
        stage = tmp_path / f"stage-path-lstat-{needle.rsplit('/', 1)[-1]}"
        shutil.copytree(baseline, stage)
        gate = _LstatGate(os_module, needle)
        with monkeypatch.context() as patch:
            patch.setattr(stage_module, "os", gate)
            with pytest.raises(PrivateEconomicStageError, match="unreadable_stage_file"):
                augment_private_stage(
                    stage, acquisition=None, prior_closure=closure,
                    observed_at=LATER_OBSERVED_AT,
                )
        # The os gate is scoped by its own context, so this test's permit
        # precondition is still installed after the gate is released.
        assert private_publication.NATIVE_RIGHTS_REGISTRY_PATH is permitted_registry, (
            "releasing the os gate also reverted this test's own permit"
        )
        assert gate.denied, f"the write probe never reached {needle}"
        assert gate.denied[0].endswith(expected_tail)
        if refuses_first_write:
            # ``_reset_native`` wiped native/ before the denial, so a real no-write
            # proof is an empty tree, not byte-identity with a destroyed baseline.
            laid = _file_names(stage / "native", "*")
            assert laid == [], f"the denied first write still laid bytes: {laid}"
        else:
            assert not (stage / "native" / "latest.json").exists()
        residue = _file_names(stage, ".*")
        assert residue == [], f"the denied write left temp residue: {residue}"

    assert private_publication.NATIVE_RIGHTS_REGISTRY_PATH is permitted_registry
    # CONTROL: with the real ``os`` (and this test's own permit) the replay writes.
    control = tmp_path / "stage-path-lstat-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


@pytest.mark.parametrize("fail_on", ("open", "fdopen", "replace", "records", "latest"))
def test_stage_maps_write_block_oserrors_to_a_typed_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on: str,
) -> None:
    """The ``os.open``/``os.fdopen``/``os.replace`` write block maps its ``OSError``
    to the same code.

    Independent review W15-V-9105f on 2a311019: reverting only the write block's
    ``except OSError`` arm (private_economic_stage.py:428-440) left the whole
    owning job green, because every existing arm denies ``os.lstat`` inside
    ``_write_stage_file`` or ``_write_stage``'s body probe (engine:540) and never
    reaches the write itself. A full device is an
    ``OSError`` that is not a ``FileNotFoundError``, so ENOSPC on each of
    ``os.open``, ``os.fdopen`` and ``os.replace`` must refuse with
    ``unreadable_stage_file`` — the code this module already uses — instead of
    leaking raw past the CLI tuple at
    scripts/build_earnings_public_wire.py:1850, and the refusal must still unlink
    its private temp so no ``.``-prefixed residue survives in the stage. The
    ``records`` param denies only the final ``os.replace`` onto
    ``records/<slug>.json`` (private_economic_stage.py:584-587); its temp lands
    outside ``native/``, so the stage-wide ``.*`` scan is the only probe that
    reaches it. The ``latest`` param denies the other final target, the
    ``os.replace`` onto ``native/latest.json`` (engine:583). The fdopen arm
    leaves ``fd`` to the engine (item-1 ruling): on Linux the gated call must
    not leak one descriptor.
    """
    import errno as errno_module
    import os as os_module

    from engine.earnings_narrative import private_economic_stage as stage_module

    class _WriteGate:
        """Every ``os`` attribute delegates; only ``fail_on`` denies a stage write.

        ``records`` and ``latest`` narrow ``os.replace`` to their final target.
        """

        def __init__(self, real: object, fail_on: str, stage: Path) -> None:
            self._real = real
            self._fail_on = fail_on
            self._prefix = str(stage)
            self.denied: list[str] = []
            self._stage_fds: set[int] = set()

        def __getattr__(self, name: str):
            return getattr(self._real, name)

        def _in_stage(self, path: object) -> bool:
            return str(path).startswith(self._prefix)

        def _deny(self, target: str) -> None:
            self.denied.append(target)
            raise OSError(errno_module.ENOSPC, "No space left on device", target)

        def open(self, path, *args, **kwargs):
            if self._fail_on == "open" and self._in_stage(path):
                self._deny(str(path))
            fd = self._real.open(path, *args, **kwargs)
            if self._in_stage(path):
                self._stage_fds.add(fd)
            return fd

        def fdopen(self, fd, *args, **kwargs):
            if self._fail_on == "fdopen" and fd in self._stage_fds:
                # The engine owns fd from os.open until fdopen binds it; a
                # test-side close here would mask an engine descriptor leak.
                self._deny(f"fd={fd}")
            return self._real.fdopen(fd, *args, **kwargs)

        def replace(self, src, dst, *args, **kwargs):
            if self._fail_on == "replace" and self._in_stage(dst):
                self._deny(str(dst))
            if (
                self._fail_on == "records"
                and self._in_stage(dst)
                and Path(str(dst)).parts[-2] == "records"
            ):
                self._deny(str(dst))
            if (
                self._fail_on == "latest"
                and self._in_stage(dst)
                and Path(str(dst)).parts[-2] == "native"
                and Path(str(dst)).name == "latest.json"
            ):
                self._deny(str(dst))
            return self._real.replace(src, dst, *args, **kwargs)

    def _file_names(root: Path, pattern: str, skip_hidden: bool = False) -> list[str]:
        return sorted(
            str(path) for path in root.rglob(pattern)
            if path.is_file() and not (skip_hidden and path.name.startswith("."))
        )

    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    baseline = tmp_path / f"stage-write-{fail_on}-baseline"
    shutil.copytree(receipt.private_dir, baseline)
    stage = tmp_path / f"stage-write-{fail_on}"
    shutil.copytree(baseline, stage)

    gate = _WriteGate(os_module, fail_on, stage)
    fd_probe = Path("/proc/self/fd")
    fd_gate = fail_on == "fdopen" and fd_probe.exists()
    fd_before = len(os_module.listdir(fd_probe)) if fd_gate else 0
    with monkeypatch.context() as patch:
        patch.setattr(stage_module, "os", gate)
        with pytest.raises(PrivateEconomicStageError) as raised:
            augment_private_stage(
                stage, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
            )
    if fd_gate:
        fd_delta = len(os_module.listdir(fd_probe)) - fd_before
        assert fd_delta == 0, "the refused write leaked a file descriptor"
    assert raised.value.reason == "unreadable_stage_file"
    denied_via = "replace" if fail_on in ("records", "latest") else fail_on
    assert gate.denied, f"the write block never called os.{denied_via}"
    residue = _file_names(stage, ".*")
    assert residue == [], f"the refusal left temp residue in the stage: {residue}"
    # residue owns dotfiles, laid owns real bytes: the scans are disjoint.
    laid = _file_names(stage / "native", "*", skip_hidden=True)
    if fail_on == "records":
        # The denial lands on the final write (engine:584-587); the native
        # chain legitimately landed first (engine:526-554, latest.json :583).
        assert (stage / "native" / "latest.json").is_file()
        refused = Path(gate.denied[0])
        assert refused.parts[-2] == "records", f"denied target not in records: {refused}"
        baseline_bytes = (baseline / "records" / refused.name).read_bytes()
        assert refused.read_bytes() == baseline_bytes, (
            "the denied records write still laid bytes"
        )
    elif fail_on == "latest":
        # The denial lands on the final native write (engine:583); the chain
        # legitimately landed first (engine:526-554). _reset_native (engine:641)
        # wiped the baseline latest.json before the refusal, so the only way
        # this target carries bytes is if the denied write laid them.
        refused = Path(gate.denied[0])
        assert refused.parts[-2] == "native", f"denied target not in native: {refused}"
        assert refused.name == "latest.json", f"denied target not latest: {refused}"
        assert laid, f"the chain never landed before the latest denial: {laid}"
        landed_dirs = {Path(p).parts[-2] for p in laid}
        assert {"workspaces", "documents"} <= landed_dirs, (
            f"chain members missing at the latest denial: {sorted(landed_dirs)}"
        )
        assert not (stage / "native" / "latest.json").exists(), (
            "the denied latest write still laid bytes"
        )
        for record in (baseline / "records").glob("*.json"):
            kept = (stage / "records" / record.name).read_bytes()
            assert kept == record.read_bytes(), (
                "the run aborted at latest yet laid the downstream record"
            )
    else:
        assert laid == [], f"the denied write still laid bytes: {laid}"

    # CONTROL: with the real ``os`` and no gate the same replay still writes.
    control = tmp_path / f"stage-write-{fail_on}-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


def test_stage_refuses_a_non_dict_document_on_an_older_chain_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every chain item's document must be a dict before any writer touches it.

    Only the newest item's document is dereferenced by the pre-flight guards;
    older items reach ``item["document"].get("content_sha256")``
    (private_economic_stage.py:527) unchecked, so a forged older item carrying
    ``document = 7`` leaked a bare ``AttributeError: 'int' object has no
    attribute 'get'`` past the CLI tuple at
    scripts/build_earnings_public_wire.py:1850 (review W15-V-9105c on 5951818e).
    ``_write_stage`` now requires ``type(item["document"]) is dict`` for every
    chain item at the top of the function, refusing with ``malformed_prior``,
    the code the module already uses for a malformed prior chain.
    """
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    newest = closure["chain"][-1]
    baseline = tmp_path / "older-doc-baseline"
    shutil.copytree(receipt.private_dir, baseline)

    older = copy.deepcopy(newest)
    older["workspace"]["generation_id"] = sha256(b"forged-document").hexdigest()[:24]
    older["document"] = 7
    forged = copy.deepcopy(closure)
    forged["chain"] = [older, copy.deepcopy(newest)]
    stage = tmp_path / "stage-older-doc-hostile"
    shutil.copytree(baseline, stage)
    with pytest.raises(PrivateEconomicStageError, match="malformed_prior"):
        augment_private_stage(
            stage, acquisition=None, prior_closure=forged, observed_at=LATER_OBSERVED_AT,
        )
    def _native_tree(root: Path) -> dict[str, bytes]:
        native = root / "native"
        return {
            str(rel.relative_to(native)): rel.read_bytes()
            for rel in sorted(native.rglob("*"))
            if rel.is_file()
        }

    assert _native_tree(stage) == _native_tree(baseline), (
        "the pre-write refusal still wrote under native/"
    )

    # CONTROL: the same two-item chain with dict documents still writes.
    honest_older = copy.deepcopy(newest)
    honest_older["workspace"]["generation_id"] = sha256(b"control-doc-item").hexdigest()[:24]
    control_closure = copy.deepcopy(closure)
    control_closure["chain"] = [honest_older, copy.deepcopy(newest)]
    control = tmp_path / "stage-older-doc-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=control_closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True


def test_stage_refuses_a_non_dict_workspace_on_an_older_chain_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_admit_chain_paths`` may not subscript a caller-owned non-dict workspace.

    ``_admit_chain_paths`` reads ``item["workspace"]["generation_id"]`` for every
    chain item (private_economic_stage.py:452) and the path admission happens
    before any write, so an older forged item carrying ``workspace = 7`` leaked a
    bare ``TypeError: 'int' object is not subscriptable`` past the CLI tuple at
    scripts/build_earnings_public_wire.py:1850 (review W15-V-9105c on 5951818e).
    The same top-of-``_write_stage`` type gate as the document case refuses
    with ``malformed_prior`` before ``_admit_chain_paths`` ever sees a non-dict.
    """
    _permit(monkeypatch, tmp_path)
    receipt = run_economic_wire_fixture(tmp_path, wire="w1", source="pg1", observed_at=OBSERVED_AT)
    closure = receipt.closure
    assert closure is not None
    newest = closure["chain"][-1]
    baseline = tmp_path / "older-workspace-baseline"
    shutil.copytree(receipt.private_dir, baseline)

    older = copy.deepcopy(newest)
    older["workspace"] = 7
    forged = copy.deepcopy(closure)
    forged["chain"] = [older, copy.deepcopy(newest)]
    stage = tmp_path / "stage-older-workspace-hostile"
    shutil.copytree(baseline, stage)
    with pytest.raises(PrivateEconomicStageError, match="malformed_prior"):
        augment_private_stage(
            stage, acquisition=None, prior_closure=forged, observed_at=LATER_OBSERVED_AT,
        )
    def _native_tree(root: Path) -> dict[str, bytes]:
        native = root / "native"
        return {
            str(rel.relative_to(native)): rel.read_bytes()
            for rel in sorted(native.rglob("*"))
            if rel.is_file()
        }

    assert _native_tree(stage) == _native_tree(baseline), (
        "the pre-write refusal still wrote under native/"
    )

    # CONTROL: the same two-item chain with dict workspaces still writes.
    honest_older = copy.deepcopy(newest)
    honest_older["workspace"]["generation_id"] = sha256(b"control-workspace-item").hexdigest()[:24]
    control_closure = copy.deepcopy(closure)
    control_closure["chain"] = [honest_older, copy.deepcopy(newest)]
    control = tmp_path / "stage-older-workspace-control"
    shutil.copytree(baseline, control)
    written = augment_private_stage(
        control, acquisition=None, prior_closure=control_closure, observed_at=LATER_OBSERVED_AT,
    )
    assert written["wrote"] is True
