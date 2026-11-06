"""FIF A0-SE r2: hermetic receipts tests over the LOCAL fixture store.

Builds the two-generation store through the real publisher CLI with the
publisher tests' offline fakes, then runs the API receipt chain through the
REAL router in production mode over that store. SAFE-ENV: local fixture
store, entitlement satisfied by the router-test dependency override — not
production, not A45. No network, no browser, no R2/RESEARCH_LOCAL_STORE/FIF_*
env (scrubbed by the tool and asserted unset here).

r2 pins the post-#9116 truth: SE1-d /revisions and the SE1-e/SE1-f statements
POSTs answer 200 through the real store (r1's 503s were the D-1/D-2 defects
fixed by #9116), while the SE1-b not_evaluable correction answer, the SE1-c
final-store 503 + night-1 generation-1 witness, and the SE2-b/SE2-c
OBSERVED-ALLOWED law stay as the seat pinned them.
"""
from __future__ import annotations

import pytest

from tests.tools import fif_se_receipts as tool

T1 = "2026-10-12T01:00:00Z"  # night-1 admission (after the rule/registry clock floor)
T2 = "2026-10-13T02:00:00Z"  # night-2 admission (different UTC day, before the run clock)

_SCRUB_PREFIXES = ("R2_", "FF_ATTESTED_", "AWS_")
_SCRUB_NAMES = ("RESEARCH_LOCAL_STORE", "FIF_FINANCIAL_DATASET_MODE",
                "FIF_PRODUCTION_DATASET_LOCAL_STORE")


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """The suite must pass with every store/mode variable unset OR set junk."""
    import os

    for name in sorted(os.environ):
        if name.startswith(_SCRUB_PREFIXES) or name in _SCRUB_NAMES:
            monkeypatch.delenv(name, raising=False)
    yield


def _rows_by_case(document):
    return {row["case"]: row for row in document["rows"]}


def test_correction_store_receipt_chain(tmp_path) -> None:
    build = tool.build_two_generation_store(tmp_path, T1, T2, mode=tool.MODE_CORRECTION)
    assert build.mode == tool.MODE_CORRECTION
    assert build.admitted_at["generation_1"].startswith(T1[:10])
    assert build.admitted_at["generation_2"].startswith(T2[:10])
    assert build.generation_ids["generation_1"] != build.generation_ids["generation_2"]
    assert build.amendment is not None
    assert build.amendment["amended_accession"] != build.amendment["amends_accession"]

    document = tool.api_receipts(
        build.store_dir,
        T1,
        T2,
        night1_store_dir=build.night1_store_dir,
        entity_id=build.entity_id,
        amended_accession=build.amendment["amended_accession"],
        future_cutoff="2026-10-15T06:00:00Z",
    )
    rows = _rows_by_case(document)
    for row in document["rows"]:
        assert row["evidence_class"] == tool.SAFE_ENV_CLASS

    # SE1-a: health names generation 2 and its admitted_at.
    se1a = rows["SE1-a"]
    assert se1a["status"] == 200
    assert se1a["observed"]["mode_header"] == "production"
    assert se1a["observed"]["generation_id"] == build.generation_ids["generation_2"]
    assert se1a["observed"]["admitted_at"].startswith("2026-10-13T02:00:00")

    # SE1-b: a cutoff at/after T2 serves generation 2, bound in the body.
    se1b = rows["SE1-b"]
    assert se1b["status"] == 200
    excerpt = se1b["observed"]["body_excerpt"]
    assert excerpt["delivery_dataset_generation_id"] == build.generation_ids["generation_2"]
    # The correction is admitted but the kernel refuses to select between
    # unlinked vintages (SE1-b SEAT RULING: this not_evaluable answer is
    # CORRECT; typed revision lineage belongs to a later node).
    assert excerpt["revenue"]["state"] == "not_evaluable"
    assert excerpt["revenue"]["reason"] == (
        "unlinked source vintages require an explicit typed revision lineage"
    )

    # SE1-c (final store): a between-cutoff is the typed 503 absence — the
    # installed API serves only the latest generation (A12 admission floor).
    # SE1-c SEAT RULING: installed truth; the generation-1 witness at a
    # between-cutoff is the night-1 row below.
    se1c = rows["SE1-c"]
    assert se1c["status"] == 503

    # SE1-c (night-1 store): the SAME cutoff serves generation 1 bytes.
    se1c1 = rows["SE1-c[night1]"]
    assert se1c1["status"] == 200
    excerpt1 = se1c1["observed"]["body_excerpt"]
    assert excerpt1["delivery_dataset_generation_id"] == build.generation_ids["generation_1"]
    assert excerpt1["revenue"]["value"] == "416161000000"
    assert excerpt1["revenue"]["accession"] == build.amendment["amends_accession"]

    # SE2-a: a cutoff before the first admission is the typed absence.
    assert rows["SE2-a"]["status"] == 503
    assert rows["SE2-a[night1]"]["status"] == 503

    # SE2-b/SE2-c SEAT RULING: OBSERVED-ALLOWED is the request-path law (no
    # wall clock there); pinned as 200 WITH the delivery generation binding.
    se2b = rows["SE2-b"]
    assert se2b["status"] == 200
    assert se2b["verdict"] == "OBSERVED-ALLOWED"
    binding_b = se2b["observed"]["delivery_generation_binding"]
    assert binding_b["dataset_generation_id"] == build.generation_ids["generation_2"]
    assert binding_b["generation_matches_store_pointer"] is True
    assert binding_b["store_pointer_admitted_at"].startswith("2026-10-13T02:00:00")

    se2c = rows["SE2-c"]
    assert se2c["status"] == 200
    assert se2c["verdict"] == "OBSERVED-ALLOWED"
    binding_c = se2c["observed"]["delivery_generation_binding"]
    assert binding_c["dataset_generation_id"] == build.generation_ids["generation_2"]
    assert binding_c["generation_matches_store_pointer"] is True

    # SE1-e (r2 pin, was the r1 503 behind every browser cell): the production
    # statements POST serves the as-reported tree and binds the generation.
    se1e = rows["SE1-e"]
    assert se1e["status"] == 200
    se1e_excerpt = se1e["observed"]["body_excerpt"]
    assert (
        se1e_excerpt["delivery_dataset_generation_id"]
        == build.generation_ids["generation_2"]
    )
    assert se1e_excerpt["filing"]["accession"] == build.amendment["amends_accession"]
    assert se1e_excerpt["filing"]["form"] == "10-K"
    assert se1e_excerpt["statement_titles"]

    # SE1-e[amended]: the corrected vintage IS admitted on the final store and
    # its statement tree carries the corrected value.
    se1ea = rows["SE1-e[amended]"]
    assert se1ea["status"] == 200
    amended_excerpt = se1ea["observed"]["body_excerpt"]
    assert (
        amended_excerpt["delivery_dataset_generation_id"]
        == build.generation_ids["generation_2"]
    )
    assert amended_excerpt["filing"]["accession"] == build.amendment["amended_accession"]
    amended_cells = amended_excerpt["amended_concept_cells"]
    assert amended_cells, "the corrected concept cell must be present"
    assert any(cell["value"] == "416916000000" for cell in amended_cells)

    # SE1-d (r2 pin, was the r1 503 everywhere): /revisions answers through
    # the real store (#9116 D-2 re-keys filing metadata onto occurrence ids)
    # and shows ZERO revision rows — the corrected 10-K vintage does not
    # appear as a revision (no typed linkage exists; consistent with the
    # SE1-b seat ruling that an unlinked newer vintage is never silently
    # chosen).
    se1d = rows["SE1-d[revisions]"]
    assert se1d["status"] == 200
    assert se1d["observed"]["revisions_count"] == 0
    assert se1d["observed"]["revisions_excerpt"] == []
    corrected = se1d["observed"]["corrected_vintage"]
    assert corrected["amended_accession"] == build.amendment["amended_accession"]
    assert corrected["appears_in_revisions"] is False
    assert se1d["request"]["query_state_at_same_cutoff"]["revenue_reason"] == (
        "unlinked source vintages require an explicit typed revision lineage"
    )

    # SE1-f: the same cases on the night-1 store. The primary accession
    # serves generation 1; the amended filing did not exist at that
    # admission, so its statements POST is the typed 400 unknown filing.
    se1f = rows["SE1-f[statements][night1]"]
    assert se1f["status"] == 200
    assert (
        se1f["observed"]["body_excerpt"]["delivery_dataset_generation_id"]
        == build.generation_ids["generation_1"]
    )
    se1fa = rows["SE1-f[statements][amended][night1]"]
    assert se1fa["status"] == 400

    # SE1-d on the night-1 store: 200 with zero rows (the un-amended store).
    se1d1 = rows["SE1-d[revisions][night1]"]
    assert se1d1["status"] == 200
    assert se1d1["observed"]["revisions_count"] == 0


def test_supersession_store_serves_clean_values(tmp_path) -> None:
    build = tool.build_two_generation_store(
        tmp_path / "sup", T1, T2, mode=tool.MODE_SUPERSESSION
    )
    assert build.amendment is None
    document = tool.api_receipts(
        build.store_dir, T1, T2, entity_id=build.entity_id,
        future_cutoff="2026-10-15T06:00:00Z",
    )
    rows = _rows_by_case(document)
    se1b = rows["SE1-b"]
    assert se1b["status"] == 200
    excerpt = se1b["observed"]["body_excerpt"]
    assert excerpt["delivery_dataset_generation_id"] == build.generation_ids["generation_2"]
    # Same content, new generation: the value still serves cleanly.
    assert excerpt["revenue"]["state"] == "value"
    assert excerpt["revenue"]["value"] == "416161000000"
    assert rows["SE1-c"]["status"] == 503
    # SE1-e on the supersession store (r2 pin; this store IS the final store
    # here): statements serve generation 2.
    se1e = rows["SE1-e"]
    assert se1e["status"] == 200
    assert (
        se1e["observed"]["body_excerpt"]["delivery_dataset_generation_id"]
        == build.generation_ids["generation_2"]
    )


def test_golden_mode_health_carries_no_generation_header() -> None:
    """With FIF_FINANCIAL_DATASET_MODE unset (golden) there is no generation header."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.forensics as forensics_api

    forensics_api._reset_production_provider_cache()
    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
        "id": "fif-se-receipts-local"
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(tool.HEALTH_PATH)
            assert response.status_code == 200
            assert response.headers.get("X-FIF-Financial-Dataset-Mode") == "golden"
            assert response.headers.get("X-FIF-Dataset-Generation-Id") is None
            assert response.headers.get("X-FIF-Dataset-Admitted-At") is None
    finally:
        forensics_api._reset_production_provider_cache()
