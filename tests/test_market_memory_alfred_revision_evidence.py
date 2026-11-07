"""Focused tests for the SOURCE_ONLY ALFRED revision source-context producer.

Every happy-path test starts from a GENUINE native intake: the fixture helpers
below are copied verbatim from the existing native source test so that a real
``intake_alfred_cpiaucsl`` publishes a real store, a real generation and real
receipt copies.  No test forges a receipt, a generation or a result dictionary.

Successful qualification substitutes only the two producer path constants
(``_STORE_ROOT`` and ``_REPOSITORY_ROOT``), plus the named synthetic source clock.
Negative tests use I/O/parser spies, tighten bounds, or inject source-file drift;
they do not replace native qualification/security checks with successful mocks.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import io
import json
import math
import shutil
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

from engine import release_target_truth as normalizer
from engine.neuralweb import brain_analogues
from engine.neuralweb import market_memory_alfred_revision_evidence as evidence
from engine.neuralweb import market_memory_sources as sources

ROOT = Path(__file__).resolve().parents[1]
OBSERVED_AT = "2025-02-13T00:03:00Z"
CUTOFF = "2025-02-14T00:00:00Z"

# The supplied immutable base of engine/neuralweb/brain_analogues.py.  The
# append-only consumer must leave this byte prefix exactly as it was.
BRAIN_BASE_BYTES = 32162
BRAIN_BASE_SHA256 = (
    "bf1a9be9770f00e2721b59a8ba0a5a9c08d630f4b4829286f72a7a62e9a0c66b"
)

SCHEMA_PATH = (
    ROOT / "contracts" / "market_memory" / "alfred_revision_source_context.v1.schema.json"
)


# --------------------------------------------------------------------------- #
# Native fixture helpers (copied from tests/test_market_memory_sources.py)
# --------------------------------------------------------------------------- #
def _set_source_clock(monkeypatch: pytest.MonkeyPatch, stamp: str) -> None:
    value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    monkeypatch.setattr(sources, "_utc_now", lambda: value)


@pytest.fixture(autouse=True)
def _fixed_source_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_source_clock(monkeypatch, OBSERVED_AT)


def _matrix(*, latest_value: float = 111.1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "series": "CPIAUCSL",
                "period": "2024-12-01",
                "realtime_start": "2025-01-15",
                "realtime_end": "2025-02-11",
                "value": 100.0,
                "source_output_type": 2,
            },
            {
                "series": "CPIAUCSL",
                "period": "2024-12-01",
                "realtime_start": "2025-02-12",
                "realtime_end": "9999-12-31",
                "value": 110.0,
                "source_output_type": 2,
            },
            {
                "series": "CPIAUCSL",
                "period": "2025-01-01",
                "realtime_start": "2025-02-12",
                "realtime_end": "9999-12-31",
                "value": latest_value,
                "source_output_type": 2,
            },
        ]
    )


def _write_manifest(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _publish_upstream(
    root: Path,
    *,
    frame: pd.DataFrame | None = None,
    hardened: bool = True,
    collected_at: str = "2025-02-13T00:01:00Z",
    completed_at: str = "2025-02-13T00:02:00Z",
) -> tuple[Path, Path, dict]:
    upstream = root / "upstream"
    upstream.mkdir(parents=True, exist_ok=True)
    artifact_path = upstream / "CPIAUCSL_all_vintages.parquet"
    manifest_path = upstream / "manifest.json"
    matrix = (frame if frame is not None else _matrix()).copy()
    matrix.to_parquet(artifact_path, index=False)
    artifact_body = artifact_path.read_bytes()
    periods = pd.to_datetime(matrix["period"])
    releases = pd.to_datetime(matrix["realtime_start"])
    row = {
        "status": "written",
        # A runner-absolute path is untrusted metadata. The explicit input path wins.
        "path": "/hostile/runner/path/CPIAUCSL_all_vintages.parquet",
        "rows": len(matrix),
        "periods": int(periods.nunique()),
        "release_dates": int(releases.nunique()),
        "period_min": periods.min().date().isoformat(),
        "period_max": periods.max().date().isoformat(),
    }
    manifest: dict = {
        "schema": "release_target_vintage_collection.v1",
        "status": "ok",
        "source": "FRED/ALFRED",
        "source_output_type": 2,
        "realtime_start": "1997-01-01",
        "collected_at": collected_at,
        "dry_run": False,
        "series": {"CPIAUCSL": row},
    }
    if hardened:
        manifest.update(
            {
                "integrity_profile": sources.COLLECTOR_INTEGRITY_PROFILE,
                "completed_at": completed_at,
            }
        )
        row.update(
            {
                "artifact_sha256": hashlib.sha256(artifact_body).hexdigest(),
                "artifact_bytes": len(artifact_body),
            }
        )
    _write_manifest(manifest_path, manifest)
    return manifest_path, artifact_path, manifest


def _intake(
    root: Path,
    *,
    hardened: bool = True,
    frame: pd.DataFrame | None = None,
) -> sources.StoredSourceArtifact:
    manifest_path, artifact_path, _manifest = _publish_upstream(
        root, hardened=hardened, frame=frame
    )
    return sources.intake_alfred_cpiaucsl(
        root / "private-source-store",
        manifest_path=manifest_path,
        artifact_path=artifact_path,
    )


# --------------------------------------------------------------------------- #
# Local fixtures
# --------------------------------------------------------------------------- #
def _canonical_path(repo_root: Path) -> Path:
    return normalizer.default_vintage_path(repo_root, "CPIAUCSL")


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Publish one genuine native store and point the producer at it."""
    repo_root = tmp_path / "repo"
    store_root = tmp_path / "private-source-store"
    monkeypatch.setattr(evidence, "_STORE_ROOT", store_root)
    monkeypatch.setattr(evidence, "_REPOSITORY_ROOT", repo_root)
    upstream_root = tmp_path / "upstream"
    manifest_path, artifact_path, _manifest = _publish_upstream(upstream_root)
    canonical = _canonical_path(repo_root)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, canonical)
    stored = sources.intake_alfred_cpiaucsl(
        store_root, manifest_path=manifest_path, artifact_path=artifact_path
    )
    return {
        "repo_root": repo_root,
        "store_root": store_root,
        "canonical": canonical,
        "generation_id": stored.generation_id,
        "receipt_id": stored.receipt["receipt_id"],
        "receipt": stored.receipt,
    }


def _read(store: dict, **kwargs):
    request = {
        "knowledge_cutoff": CUTOFF,
        "periods": ("2024-12-01", "2025-01-01"),
        "maximum_vintages": 32,
    }
    request.update(kwargs)
    return evidence.read_published_alfred_revision_evidence(
        store["generation_id"], store["receipt_id"], **request
    )


def _context(store: dict, **kwargs) -> dict:
    return evidence.disclose_alfred_revision_evidence(_read(store, **kwargs))


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
def test_projection_is_closed_and_validates_against_the_published_schema(
    store: dict,
) -> None:
    context = _context(store)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    validator.validate(context)

    assert set(context) == {
        "schema",
        "mode",
        "authority",
        "audience",
        "knowledge_cutoff",
        "source",
        "clocks",
        "availability_evidence",
        "quality",
        "units",
        "conversion",
        "accounting",
        "periods",
        "claims",
        "limitations",
        "source_ref",
        "context_id",
    }
    assert context["schema"] == "market_memory.alfred_revision_source_context.v1"
    assert context["mode"] == "SOURCE_ONLY_RETROSPECTIVE_EVIDENCE"
    assert context["authority"] == "display_only"
    assert context["audience"] == "internal_unregistered"
    assert context["units"] == "not_retained"
    assert context["conversion"] == "not_performed"


def test_source_block_binds_the_native_receipt(store: dict) -> None:
    context = _context(store)
    source = context["source"]
    assert set(source) == {
        "source_id",
        "series_id",
        "source_output_type",
        "store_id",
        "generation_id",
        "receipt_id",
        "receipt_sha256",
        "capture_id",
        "vintage_id",
        "revision_id",
        "upstream_sha256",
        "upstream_bytes",
    }
    receipt = store["receipt"]
    assert source["source_id"] == "fred_alfred:CPIAUCSL"
    assert source["series_id"] == "CPIAUCSL"
    assert source["source_output_type"] == 2
    assert source["store_id"] == receipt["store_id"]
    assert source["generation_id"] == store["generation_id"]
    assert source["receipt_id"] == store["receipt_id"]
    assert source["receipt_sha256"] == hashlib.sha256(
        sources._canonical_bytes(receipt)
    ).hexdigest()
    assert source["capture_id"] == receipt["capture_id"]
    assert source["vintage_id"] == receipt["vintage_id"]
    assert source["revision_id"] == receipt["revision_id"]
    assert source["upstream_sha256"] == receipt["provenance"]["upstream_artifact_sha256"]
    assert source["upstream_bytes"] == receipt["provenance"]["upstream_artifact_bytes"]


def test_clocks_availability_and_quality_are_the_native_ones(store: dict) -> None:
    context = _context(store)
    receipt = store["receipt"]
    assert context["clocks"] == receipt["clocks"]
    assert context["availability_evidence"] == receipt["availability_evidence"]
    assert context["quality"] == receipt["quality"]
    assert context["quality"]["status"] == "complete"
    assert context["quality"]["reconstruction_only"] is False
    assert context["quality"]["source_evidence_eligible"] is True
    assert context["quality"]["feature_projection_eligible"] is False
    assert context["quality"]["training_eligible"] is False
    assert context["quality"]["promotion_eligible"] is False


def test_periods_report_the_whole_source_not_only_the_returned_prefix(
    store: dict,
) -> None:
    context = _context(store)
    periods = context["periods"]
    assert [row["period"] for row in periods] == ["2024-12-01", "2025-01-01"]
    changed, unchanged = periods
    assert changed["status"] == "OBSERVED"
    assert changed["total_vintages"] == 2
    assert changed["source_distinct_values"] == 2
    assert changed["returned_distinct_values"] == 2
    assert changed["revision_value_change_observed"] is True
    assert unchanged["total_vintages"] == 1
    assert unchanged["source_distinct_values"] == 1
    assert unchanged["revision_value_change_observed"] is False


def test_rows_preserve_vendor_dates_and_the_open_ended_sentinel(store: dict) -> None:
    context = _context(store)
    rows = context["periods"][0]["rows"]
    assert [row["source_date"] for row in rows] == ["2025-01-15", "2025-02-12"]
    assert rows[0]["source_valid_through_date"] == "2025-02-11"
    assert rows[1]["source_valid_through_date"] == "9999-12-31"
    assert rows[0]["value"] == 100.0
    assert rows[1]["value"] == 110.0
    for row in rows:
        assert math.isfinite(row["value"])
        assert len(row["row_sha256"]) == 64


def test_row_digest_binds_the_canonical_normalized_source_row(store: dict) -> None:
    context = _context(store)
    row = context["periods"][0]["rows"][1]
    expected = hashlib.sha256(
        sources._canonical_bytes(
            {
                "series": "CPIAUCSL",
                "period": "2024-12-01",
                "value": 110.0,
                "realtime_start": "2025-02-12",
                "realtime_end": "9999-12-31",
            }
        )
    ).hexdigest()
    assert row["row_sha256"] == expected


def test_accounting_counts_the_full_normalized_source(store: dict) -> None:
    context = _context(store)
    accounting = context["accounting"]
    assert set(accounting) == {
        "matrix_rows",
        "matrix_periods",
        "matrix_source_dates",
        "periods_with_changed_values",
        "maximum_vintages",
        "requested_periods",
        "observed_requested_periods",
        "absent_requested_periods",
        "returned_rows",
        "omitted_rows",
    }
    assert accounting["matrix_rows"] == 3
    assert accounting["matrix_periods"] == 2
    assert accounting["matrix_source_dates"] == 2
    assert accounting["periods_with_changed_values"] == 1
    assert accounting["maximum_vintages"] == 32
    assert accounting["requested_periods"] == 2
    assert accounting["observed_requested_periods"] == 2
    assert accounting["absent_requested_periods"] == 0
    assert accounting["returned_rows"] == 3
    assert accounting["omitted_rows"] == 0


def test_absent_requested_period_is_explicit(store: dict) -> None:
    context = _context(store, periods=("2024-12-01", "2025-01-01", "2019-03-01"))
    absent = context["periods"][2]
    assert absent["period"] == "2019-03-01"
    assert absent["status"] == "ABSENT"
    assert absent["total_vintages"] == 0
    assert absent["returned_vintages"] == 0
    assert absent["omitted_vintages"] == 0
    assert absent["source_distinct_values"] == 0
    assert absent["returned_distinct_values"] == 0
    assert absent["revision_value_change_observed"] is False
    assert absent["rows"] == []
    assert context["accounting"]["absent_requested_periods"] == 1
    assert context["accounting"]["observed_requested_periods"] == 2


def test_bounded_truncation_accounts_for_omitted_vintages(store: dict) -> None:
    context = _context(store, maximum_vintages=1)
    changed = context["periods"][0]
    assert changed["total_vintages"] == 2
    assert changed["returned_vintages"] == 1
    assert changed["omitted_vintages"] == 1
    assert changed["returned_distinct_values"] == 1
    # The change flag is a property of the full source, not of the prefix.
    assert changed["revision_value_change_observed"] is True
    assert [row["source_date"] for row in changed["rows"]] == ["2025-01-15"]
    assert context["accounting"]["returned_rows"] == 2
    assert context["accounting"]["omitted_rows"] == 1


def test_claims_are_all_false_and_limitations_are_fixed(store: dict) -> None:
    context = _context(store)
    assert set(context["claims"]) == {
        "feature_projection_eligible",
        "fit_eligible",
        "training_eligible",
        "promotion_eligible",
        "operational_study_admission",
        "action_admitted",
        "customer_disclosure_admitted",
        "historical_intraday_availability",
        "forecast_skill_established",
        "independent_episodes_established",
        "source_authenticated_by_fresh_provider",
        "source_activated",
    }
    assert all(value is False for value in context["claims"].values())
    assert context["limitations"] == [
        "retained_source_not_fresh_provider_authentication",
        "source_dates_are_retrospective_vendor_dates_not_house_knowledge",
        "units_not_retained_and_conversion_not_performed",
        "no_regime_coordinates_or_retrieval_membership",
        "rows_periods_vintages_not_independent_episodes",
        "internal_source_context_not_customer_or_study_admission",
    ]


def test_context_id_binds_every_other_top_field(store: dict) -> None:
    context = _context(store)
    unsigned = {key: value for key, value in context.items() if key != "context_id"}
    expected = "mmalfredrevision_" + hashlib.sha256(
        sources._canonical_bytes(unsigned)
    ).hexdigest()
    assert context["context_id"] == expected
    assert context["context_id"].startswith("mmalfredrevision_")


def test_source_ref_binds_the_actual_code_bytes(store: dict) -> None:
    context = _context(store)
    source_ref = context["source_ref"]
    assert source_ref["source_owner_module"] == "engine.neuralweb.market_memory_sources"
    assert source_ref["normalizer_module"] == "engine.release_target_truth"
    assert (
        source_ref["producer_module"]
        == "engine.neuralweb.market_memory_alfred_revision_evidence"
    )
    assert source_ref["assurance"] == "imported_source_bytes_not_external_runtime_attestation"
    assert source_ref["source_owner_sha256"] == hashlib.sha256(
        Path(sources.__file__).read_bytes()
    ).hexdigest()
    assert source_ref["normalizer_sha256"] == hashlib.sha256(
        Path(normalizer.__file__).read_bytes()
    ).hexdigest()
    assert source_ref["producer_sha256"] == hashlib.sha256(
        Path(evidence.__file__).read_bytes()
    ).hexdigest()


def test_projection_is_deterministic(store: dict) -> None:
    first = _context(store)
    second = _context(store)
    assert first == second
    assert first["context_id"] == second["context_id"]


def test_producer_writes_nothing(store: dict) -> None:
    before = sorted(path.name for path in store["store_root"].rglob("*"))
    _context(store)
    after = sorted(path.name for path in store["store_root"].rglob("*"))
    assert before == after


# --------------------------------------------------------------------------- #
# The Brain consumer
# --------------------------------------------------------------------------- #
def test_brain_consumer_returns_the_owner_disclosed_context(store: dict) -> None:
    capability = _read(store)
    via_brain = brain_analogues.get_alfred_revision_source_context(capability)
    via_owner = evidence.disclose_alfred_revision_evidence(capability)
    assert via_brain == via_owner
    assert via_brain["schema"] == "market_memory.alfred_revision_source_context.v1"


def test_brain_module_byte_prefix_is_unchanged_and_nothing_is_registered() -> None:
    body = Path(brain_analogues.__file__).read_bytes()
    assert hashlib.sha256(body[:BRAIN_BASE_BYTES]).hexdigest() == BRAIN_BASE_SHA256
    assert body[BRAIN_BASE_BYTES:].lstrip().startswith(
        b"def get_alfred_revision_source_context("
    )

    tool_schemas = {
        name: value
        for name, value in vars(brain_analogues).items()
        if name.endswith("TOOL_SCHEMA") and isinstance(value, dict)
    }
    assert set(tool_schemas) == {
        "ANALOGUES_TOOL_SCHEMA",
        "RETAINED_CONTEXT_TOOL_SCHEMA",
        "RETAINED_CATALOG_TOOL_SCHEMA",
    }
    for schema in tool_schemas.values():
        assert "alfred" not in json.dumps(schema).lower()
        assert "revision" not in json.dumps(schema).lower()


def test_brain_consumer_takes_only_a_capability() -> None:
    signature = inspect.signature(brain_analogues.get_alfred_revision_source_context)
    assert list(signature.parameters) == ["capability"]


# --------------------------------------------------------------------------- #
# Request validation happens before any source open
# --------------------------------------------------------------------------- #
@pytest.fixture
def no_source_open(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    calls: list[str] = []

    def _spy(*args, **kwargs):
        calls.append("owner_state")
        raise AssertionError("the source must not be opened for an invalid request")

    with monkeypatch.context() as scoped:
        scoped.setattr(sources.os, "open", _spy)
        yield calls


@pytest.mark.parametrize(
    "periods",
    [
        (),
        ["2024-12-01"],
        ("2024-12-01", "2024-12-01"),
        ("2024-12-02",),
        ("2024-13-01",),
        ("0000-01-01",),
        tuple(f"2024-{month:02d}-01" for month in range(1, 10)),
    ],
)
def test_invalid_periods_are_refused_before_the_source_opens(
    store: dict, no_source_open: list[str], periods: tuple
) -> None:
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store, periods=periods)
    assert no_source_open == []


@pytest.mark.parametrize("maximum_vintages", [0, 33, True, False, 1.0, "4"])
def test_invalid_maximum_vintages_are_refused_before_the_source_opens(
    store: dict, no_source_open: list[str], maximum_vintages: object
) -> None:
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store, maximum_vintages=maximum_vintages)
    assert no_source_open == []


@pytest.mark.parametrize(
    "cutoff", ["2025-02-14 00:00:00", "2025-02-14", "not-a-time", "", 1757856000]
)
def test_invalid_knowledge_cutoff_is_refused_before_the_source_opens(
    store: dict, no_source_open: list[str], cutoff: object
) -> None:
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store, knowledge_cutoff=cutoff)
    assert no_source_open == []


@pytest.mark.parametrize(
    "generation_id,receipt_id",
    [
        ("mmsgen_nothex", "mmsrc_" + "a" * 64),
        ("mmsgen_" + "a" * 64, "mmsrc_nothex"),
        ("../../etc/passwd", "mmsrc_" + "a" * 64),
        ("mmsgen_" + "a" * 64, "../../etc/passwd"),
    ],
)
def test_invalid_identifiers_are_refused_before_the_source_opens(
    store: dict, no_source_open: list[str], generation_id: str, receipt_id: str
) -> None:
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.read_published_alfred_revision_evidence(
            generation_id,
            receipt_id,
            knowledge_cutoff=CUTOFF,
            periods=("2024-12-01",),
        )
    assert no_source_open == []


def test_the_api_takes_no_path_root_reader_policy_or_callback() -> None:
    signature = inspect.signature(evidence.read_published_alfred_revision_evidence)
    assert list(signature.parameters) == [
        "generation_id",
        "receipt_id",
        "knowledge_cutoff",
        "periods",
        "maximum_vintages",
    ]
    for name in ("path", "root", "rows", "reader", "report", "policy", "callback",
                 "clock", "eligible"):
        assert name not in signature.parameters


# --------------------------------------------------------------------------- #
# Cutoff, hash and ordering guards
# --------------------------------------------------------------------------- #
def test_cutoff_before_the_house_observation_denies_before_the_matrix_opens(
    store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []

    native_open = sources.os.open
    def _spy(path, *args, **kwargs):
        if str(path) == str(store["canonical"]):
            opened.append("matrix")
            raise AssertionError("the canonical matrix must not be opened")
        return native_open(path, *args, **kwargs)

    monkeypatch.setattr(sources.os, "open", _spy)
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store, knowledge_cutoff="2025-02-13T00:02:59Z")
    assert opened == []


def test_cutoff_equal_to_the_observation_clock_is_accepted(store: dict) -> None:
    context = _context(store, knowledge_cutoff=OBSERVED_AT)
    assert context["knowledge_cutoff"] == OBSERVED_AT


def test_replaced_canonical_file_denies_before_the_parser_is_reached(
    store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[str] = []

    def _spy(*args, **kwargs):
        opened.append("matrix")
        raise AssertionError("the canonical matrix must not be materialized")

    monkeypatch.setattr(evidence, "_materialize_matrix", _spy)
    store["canonical"].write_bytes(b"not the published canonical artifact")
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)
    assert opened == []


def test_canonical_file_size_mismatch_denies(store: dict) -> None:
    body = store["canonical"].read_bytes()
    store["canonical"].write_bytes(body[:-1])
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)


# --------------------------------------------------------------------------- #
# Native receipt and generation refusals
# --------------------------------------------------------------------------- #
def test_legacy_reconstruction_receipt_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    store_root = tmp_path / "private-source-store"
    monkeypatch.setattr(evidence, "_STORE_ROOT", store_root)
    monkeypatch.setattr(evidence, "_REPOSITORY_ROOT", repo_root)
    upstream_root = tmp_path / "upstream"
    manifest_path, artifact_path, _manifest = _publish_upstream(
        upstream_root, hardened=False
    )
    canonical = _canonical_path(repo_root)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, canonical)
    stored = sources.intake_alfred_cpiaucsl(
        store_root, manifest_path=manifest_path, artifact_path=artifact_path
    )
    assert stored.receipt["quality"]["reconstruction_only"] is True
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.read_published_alfred_revision_evidence(
            stored.generation_id,
            stored.receipt["receipt_id"],
            knowledge_cutoff=CUTOFF,
            periods=("2024-12-01",),
        )


def test_receipt_outside_the_pinned_generation_is_refused(store: dict) -> None:
    unbound = "mmsrc_" + "0" * 64
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.read_published_alfred_revision_evidence(
            store["generation_id"],
            unbound,
            knowledge_cutoff=CUTOFF,
            periods=("2024-12-01",),
        )


def test_removed_publication_denies_the_read(store: dict) -> None:
    generation_path = (
        store["store_root"]
        / "source_generations"
        / store["generation_id"][7:9]
        / f"{store['generation_id']}.json"
    )
    generation_path.unlink()
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)


def test_a_pinned_generation_may_stay_an_ancestor_of_the_new_head(
    store: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    second = pd.DataFrame(
        [
            {
                "series": "CPIAUCSL",
                "period": "2024-12-01",
                "realtime_start": "2025-01-15",
                "realtime_end": "9999-12-31",
                "value": 105.0,
                "source_output_type": 2,
            },
            {
                "series": "CPIAUCSL",
                "period": "2025-01-01",
                "realtime_start": "2025-01-15",
                "realtime_end": "9999-12-31",
                "value": 106.0,
                "source_output_type": 2,
            },
        ]
    )
    upstream_root = tmp_path / "upstream-second"
    manifest_path, artifact_path, _manifest = _publish_upstream(
        upstream_root, frame=second
    )
    stored = sources.intake_alfred_cpiaucsl(
        store["store_root"], manifest_path=manifest_path, artifact_path=artifact_path
    )
    head = sources.SourceArtifactReader(store["store_root"]).head_generation_id()
    assert head == stored.generation_id
    assert stored.generation_id != store["generation_id"]

    # The pinned generation is still published as an ancestor of the new HEAD
    # and is NOT silently repinned to it.
    context = _context(store)
    assert context["source"]["generation_id"] == store["generation_id"]
    assert context["source"]["receipt_id"] == store["receipt_id"]

    # The new HEAD receipt is bound to the new revision's bytes, but the
    # canonical vintage artifact still holds the old revision.  The producer
    # refuses rather than refreshing to the newest published receipt.
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.read_published_alfred_revision_evidence(
            stored.generation_id,
            stored.receipt["receipt_id"],
            knowledge_cutoff=CUTOFF,
            periods=("2024-12-01",),
        )

    # Once the canonical artifact is the new revision, the new receipt projects
    # and the old receipt is refused: a changed source denies.
    shutil.copyfile(artifact_path, store["canonical"])
    new_context = evidence.disclose_alfred_revision_evidence(
        evidence.read_published_alfred_revision_evidence(
            stored.generation_id,
            stored.receipt["receipt_id"],
            knowledge_cutoff=CUTOFF,
            periods=("2024-12-01",),
        )
    )
    assert new_context["source"]["generation_id"] == stored.generation_id
    assert new_context["periods"][0]["rows"][0]["value"] == 105.0
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)


# --------------------------------------------------------------------------- #
# Disclosure refusals
# --------------------------------------------------------------------------- #
def test_forged_dictionaries_are_not_capabilities(store: dict) -> None:
    context = _context(store)
    for forged in (
        context,
        dict(context),
        {"schema": context["schema"]},
        "context",
        None,
    ):
        with pytest.raises(evidence.AlfredRevisionEvidenceError):
            evidence.disclose_alfred_revision_evidence(forged)


def test_a_capability_subclass_is_refused(store: dict) -> None:
    class Forged(evidence.AlfredRevisionEvidenceCapability):
        pass

    forged = object.__new__(Forged)
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(forged)


def test_a_tampered_capability_body_is_refused(store: dict) -> None:
    capability = _read(store)
    tampered = copy.deepcopy(capability)
    value = json.loads(tampered._body)
    value["authority"] = "customer_disclosure"
    object.__setattr__(tampered, "_body", sources._canonical_bytes(value))
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(tampered)


def test_disclosure_denies_a_removed_publication(store: dict) -> None:
    capability = _read(store)
    shutil.rmtree(store["store_root"])
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(capability)


def test_disclosure_denies_a_disappeared_canonical_file(store: dict) -> None:
    capability = _read(store)
    store["canonical"].unlink()
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(capability)


def test_disclosure_denies_a_replaced_canonical_file(store: dict) -> None:
    capability = _read(store)
    store["canonical"].write_bytes(b"replacement bytes that are not the source")
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(capability)


def test_disclosure_denies_source_code_drift(
    store: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capability = _read(store)
    altered = tmp_path / "altered_producer.py"
    altered.write_bytes(Path(evidence.__file__).read_bytes() + b"\n# synthetic code drift\n")
    # Adversarial source-file metadata substitution. The real hash reader and
    # native receipt/canonical-file qualification still execute unchanged.
    monkeypatch.setattr(evidence, "__file__", str(altered))
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.disclose_alfred_revision_evidence(capability)


def test_disclosure_returns_a_detached_copy(store: dict) -> None:
    capability = _read(store)
    disclosed = evidence.disclose_alfred_revision_evidence(capability)
    disclosed["claims"]["training_eligible"] = True
    disclosed["periods"][0]["rows"].clear()
    again = evidence.disclose_alfred_revision_evidence(capability)
    assert again["claims"]["training_eligible"] is False
    assert again["periods"][0]["rows"]


# --------------------------------------------------------------------------- #
# Materialization guards
# --------------------------------------------------------------------------- #
def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _native_receipt(store: dict) -> dict:
    reader = sources.SourceArtifactReader(
        store["store_root"], generation_id=store["generation_id"]
    )
    return reader.read_receipt(store["receipt_id"], generation_id=store["generation_id"])


def test_materialization_refuses_a_missing_output_type_marker(store: dict) -> None:
    receipt = _native_receipt(store)
    frame = _matrix().drop(columns=["source_output_type"])
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence._materialize_matrix(_parquet_bytes(frame), receipt)


def test_materialization_refuses_output_type_four(store: dict) -> None:
    receipt = _native_receipt(store)
    frame = _matrix()
    frame["source_output_type"] = 4
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence._materialize_matrix(_parquet_bytes(frame), receipt)


def test_materialization_refuses_conflicting_duplicates(store: dict) -> None:
    receipt = _native_receipt(store)
    frame = _matrix()
    conflict = frame.iloc[[1]].copy()
    conflict["value"] = 111.0
    frame = pd.concat([frame, conflict], ignore_index=True)
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence._materialize_matrix(_parquet_bytes(frame), receipt)


def test_materialization_refuses_a_nonfinite_value(store: dict) -> None:
    receipt = _native_receipt(store)
    frame = _matrix()
    frame.loc[0, "value"] = float("inf")
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence._materialize_matrix(_parquet_bytes(frame), receipt)


def test_materialization_refuses_a_row_count_loss(store: dict) -> None:
    receipt = _native_receipt(store)
    frame = _matrix()
    frame.loc[0, "value"] = float("nan")
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence._materialize_matrix(_parquet_bytes(frame), receipt)


def test_the_native_intake_refuses_the_same_bad_matrices(tmp_path: Path) -> None:
    bad_frames = {
        "output_type_4": _matrix().assign(source_output_type=4),
        "nonfinite": _matrix().assign(value=[float("inf"), 110.0, 111.1]),
        "row_count_loss": _matrix().assign(value=[float("nan"), 110.0, 111.1]),
    }
    conflict = _matrix()
    conflicting = conflict.iloc[[1]].copy()
    conflicting["value"] = 111.0
    bad_frames["duplicate_conflict"] = pd.concat([conflict, conflicting], ignore_index=True)

    for label, frame in bad_frames.items():
        upstream = tmp_path / label
        manifest_path, artifact_path, _manifest = _publish_upstream(upstream, frame=frame)
        with pytest.raises(sources.SourceIntakeError):
            sources.intake_alfred_cpiaucsl(
                tmp_path / "store" / label,
                manifest_path=manifest_path,
                artifact_path=artifact_path,
            )


# --------------------------------------------------------------------------- #
# Bounds
# --------------------------------------------------------------------------- #
def test_the_canonical_context_byte_bound_is_enforced(
    store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evidence, "CONTEXT_MAX_BYTES", 512)
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)


def test_the_matrix_metadata_row_bound_is_enforced_before_materialization(
    store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(evidence, "MAX_MATRIX_ROWS", 1)
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        _read(store)


def test_parent_body_mutation_during_real_native_io_is_refused(store, monkeypatch):
    """I/O spy passes through every real native read; no qualification is skipped."""
    cap = _read(store)
    native_read = sources.os.read
    mutated = []
    def mutate_after_native_read(fd, size):
        result = native_read(fd, size)
        if not mutated:
            mutated.append(True)
            if type(cap._body) is dict:
                cap._body["claims"]["training_eligible"] = True
            else:
                value = json.loads(cap._body)
                value["claims"]["training_eligible"] = True
                object.__setattr__(cap, "_body", sources._canonical_bytes(value))
        return result
    with monkeypatch.context() as change:
        change.setattr(sources.os, "read", mutate_after_native_read)
        with pytest.raises(evidence.AlfredRevisionEvidenceError):
            evidence.disclose_alfred_revision_evidence(cap)
    assert mutated


def test_parent_capability_has_immutable_payload_and_private_constructor(store):
    cap = _read(store)
    assert type(cap._body) is bytes
    with pytest.raises(evidence.AlfredRevisionEvidenceError, match="owner-produced"):
        evidence.AlfredRevisionEvidenceCapability(cap._body, cap._request, cap._lineage)


@pytest.mark.parametrize("field", ["generation_id", "receipt_id", "knowledge_cutoff", "period"])
def test_parent_string_subclasses_refuse_before_source_io(store, no_source_open, field):
    class StringSubclass(str):
        pass
    request = dict(generation_id=store["generation_id"], receipt_id=store["receipt_id"],
                   knowledge_cutoff=CUTOFF, periods=("2024-12-01",), maximum_vintages=32)
    if field == "period":
        request["periods"] = (StringSubclass(request["periods"][0]),)
    else:
        request[field] = StringSubclass(request[field])
    with pytest.raises(evidence.AlfredRevisionEvidenceError):
        evidence.read_published_alfred_revision_evidence(**request)
    assert no_source_open == []


@pytest.mark.parametrize("flat_only,maximum,expected_values,changes,unchanged,omitted_change", [
    (False, 2, [100.0, 110.0], 2, 39, 1),
    (False, 3, [100.0, 110.0, 100.0], 2, 39, 0),
    (True, 3, [100.0], 0, 41, 0),
])
def test_long_flat_vintage_run_exposes_change_and_reversion_through_brain(
        tmp_path, monkeypatch, flat_only, maximum, expected_values,
        changes, unchanged, omitted_change):
    """Actual native publication; no qualification guard is mocked."""
    values = [100.0] * 42 if flat_only else [100.0] * 40 + [110.0, 100.0]
    start = datetime(2025, 1, 1)
    frame = pd.DataFrame([{
        "series": "CPIAUCSL", "period": "2020-01-01",
        "realtime_start": (start + timedelta(days=i)).date().isoformat(),
        "realtime_end": ((start + timedelta(days=i)).date().isoformat()
                         if i < 41 else "9999-12-31"),
        "value": value, "source_output_type": 2,
    } for i, value in enumerate(values)])
    repo = tmp_path / "repo"
    store_root = tmp_path / "private-source-store"
    monkeypatch.setattr(evidence, "_STORE_ROOT", store_root)
    monkeypatch.setattr(evidence, "_REPOSITORY_ROOT", repo)
    manifest, artifact, _ = _publish_upstream(tmp_path / "source", frame=frame)
    canonical = _canonical_path(repo)
    canonical.parent.mkdir(parents=True)
    shutil.copyfile(artifact, canonical)
    stored = sources.intake_alfred_cpiaucsl(
        store_root, manifest_path=manifest, artifact_path=artifact)
    cap = evidence.read_published_alfred_revision_evidence(
        stored.generation_id, stored.receipt["receipt_id"],
        knowledge_cutoff=CUTOFF, periods=("2020-01-01",), maximum_vintages=maximum)
    view = brain_analogues.get_alfred_revision_source_context(cap)
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA_PATH.read_text()), format_checker=jsonschema.FormatChecker()).validate(view)
    period = view["periods"][0]
    assert period["selection_rule"] == "first_observation_then_value_changes.v1"
    assert [row["value"] for row in period["rows"]] == expected_values
    assert period["source_value_change_count"] == changes
    assert period["unchanged_vintages_omitted"] == unchanged
    assert period["omitted_change_rows"] == omitted_change
    assert period["total_vintages"] == 42
    assert period["source_distinct_values"] == (1 if flat_only else 2)
    assert period["returned_vintages"] == len(expected_values)
    assert period["omitted_vintages"] == 42 - len(expected_values)
    assert period["omitted_vintages"] == unchanged + omitted_change
    assert view["accounting"]["matrix_rows"] == 42
    assert view["accounting"]["returned_rows"] == len(expected_values)
    assert view["accounting"]["omitted_rows"] == 42 - len(expected_values)
    assert view["accounting"]["periods_with_changed_values"] == (0 if flat_only else 1)


def test_future_cutoff_refuses_before_matrix_open_using_actual_native_clock(store, monkeypatch):
    # The publishing fixture's source observation clock is synthetic/history.
    # This check uses actual current UTC; no current-clock guard is patched.
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    opened = []
    native_open = sources.os.open
    def observe(path, *args, **kwargs):
        if str(path) == str(store["canonical"]):
            opened.append(str(path))
        return native_open(path, *args, **kwargs)
    with monkeypatch.context() as change:
        change.setattr(sources.os, "open", observe)
        with pytest.raises(evidence.AlfredRevisionEvidenceError, match="future"):
            _read(store, knowledge_cutoff=future)
    assert opened == []
