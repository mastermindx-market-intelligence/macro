from __future__ import annotations

import hashlib
import json

from engine.research_intelligence import vault_head as vault_head_mod
from engine.research_intelligence.schema import SCHEMA
from engine.research_intelligence.vault_head import (
    MAX_HEAD_SIZE,
    deep_read_candidate,
    rank_vault_head,
    read_full_vault_body,
    select_ranked_head,
)
from engine.research_vault.r2_store import LocalStore


REPORT_ID = "fixture-research-2026-09-18-amd-demand"
CLAIM = "AMD server demand accelerated by 35% year over year as cloud buyers raised orders."
BODY = (
    CLAIM
    + " Management expects supply to normalize by the December quarter."
    + " An October product launch is the next demand catalyst."
)
ITEM = {
    "id": REPORT_ID,
    "institution": "Fixture Research",
    "desk": "Semiconductors",
    "title": "AMD server demand",
    "published_at": "2026-09-18T12:00:00Z",
    "summary_points": ["AMD demand strengthened.", "Supply should normalize."],
    "tags": ["semiconductors"],
    "tickers": ["AMD"],
    "top_pick": False,
    "pages": 8,
    "language": "en",
    "needs_metadata": False,
}


def _candidate(item=None, rank=1):
    return {
        "item": dict(item or ITEM),
        "triage": {
            "report_id": (item or ITEM)["id"],
            "rank": rank,
            "w_score": 0.91,
            "status": "selected" if rank == 1 else "skipped",
            "tier": "flagship" if rank == 1 else "none",
        },
    }


def _model_call(system, user, *, model_id, max_tokens):
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split(
        "\n\nOUTPUT SHAPE:", 1
    )[0]
    identity = json.loads(identity_text)
    rio = {
        "schema": SCHEMA,
        "document": identity,
        "claims": [
            {
                "statement": CLAIM,
                "evidence": [{"quote_span": CLAIM}],
                "numbers": ["35%"],
                "entities": ["AMD"],
                "horizon": "current",
                "explicit": True,
            }
        ],
        "analysis": {
            "thesis": {
                "summary": "The note argues cloud ordering is strengthening AMD server demand.",
                "direction": "bullish",
                "mechanism": ["stronger cloud ordering supports server demand"],
                "conviction": "moderate",
                "support_claim_indices": [0],
            },
            "assumptions": [],
            "forecasts": [],
            "catalysts": [],
            "falsifiers": [],
            "counterarguments": [],
            "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }
    return json.dumps(rio), "fixture-provider", f"served-{model_id}"


def _seed_pdf(store):
    assert store.put_bytes(
        f"research_vault/{REPORT_ID}.pdf",
        b"%PDF fixture bytes",
        "application/pdf",
    )


def test_ranked_head_is_independent_of_press_publish_tier():
    second = dict(ITEM)
    second["id"] = "fixture-research-2026-09-18-second"
    third = dict(ITEM)
    third["id"] = "fixture-research-2026-09-18-third"
    triage = {
        "rows": [
            {
                "report_id": ITEM["id"],
                "rank": 1,
                "w_score": 0.90,
                "status": "selected",
                "tier": "flagship",
            },
            {
                "report_id": second["id"],
                "rank": 2,
                "w_score": 0.80,
                "status": "skipped",
                "tier": "none",
            },
            {
                "report_id": third["id"],
                "rank": 3,
                "w_score": 0.70,
                "status": "skipped",
                "tier": "none",
            },
        ]
    }
    selected = select_ranked_head([ITEM, second, third], triage, limit=3)
    assert [row["item"]["id"] for row in selected] == [
        ITEM["id"],
        second["id"],
        third["id"],
    ]


def test_ranked_head_limit_is_cost_bounded():
    try:
        select_ranked_head([ITEM], {"rows": []}, limit=MAX_HEAD_SIZE + 1)
    except ValueError as exc:
        assert "head size" in str(exc)
    else:
        raise AssertionError("oversized cognition head must fail closed")


def test_full_body_comes_from_canonical_pdf_and_is_not_truncated(tmp_path):
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    result = read_full_vault_body(store, REPORT_ID, extractor=lambda _pdf: BODY)
    assert result["state"] == "ok"
    assert result["body"] == BODY
    assert result["body_bytes"] == len(BODY.encode("utf-8"))
    assert result["source_content_sha256"] == hashlib.sha256(BODY.encode()).hexdigest()


def test_missing_pdf_and_oversized_body_are_explicit_states(tmp_path):
    store = LocalStore(tmp_path / "vault")
    missing = read_full_vault_body(store, REPORT_ID, extractor=lambda _pdf: BODY)
    assert missing["state"] == "pdf_missing"

    _seed_pdf(store)
    oversized = read_full_vault_body(
        store,
        REPORT_ID,
        extractor=lambda _pdf: BODY,
        body_max_bytes=16,
    )
    assert oversized["state"] == "source_body_too_large"
    assert "body" not in oversized


def test_successful_deep_read_persists_then_exact_rerun_spends_no_model_call(tmp_path):
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        extractor=lambda _pdf: BODY,
    )
    assert first["state"] == "persisted"
    assert first["write_state"] == "created"
    assert first["previous_artifact_sha256"] is None

    def must_not_call(*args, **kwargs):
        raise AssertionError("already-current report must not spend another model call")

    second = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=must_not_call,
        extractor=lambda _pdf: BODY,
    )
    assert second["state"] == "already_current"
    assert second["artifact_sha256"] == first["artifact_sha256"]


def test_model_change_uses_exact_predecessor_correction(tmp_path):
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        extractor=lambda _pdf: BODY,
    )
    second = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-b",
        call=_model_call,
        extractor=lambda _pdf: BODY,
    )
    assert first["state"] == "persisted"
    assert second["state"] == "persisted"
    assert second["write_state"] == "corrected"
    assert second["previous_artifact_sha256"] == first["artifact_sha256"]
    assert second["artifact_sha256"] != first["artifact_sha256"]


def test_catalog_metadata_change_is_not_mistaken_for_current_intelligence(tmp_path):
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)
    first = deep_read_candidate(
        _candidate(),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        extractor=lambda _pdf: BODY,
    )
    changed = dict(ITEM)
    changed["title"] = "AMD server demand — corrected title"
    second = deep_read_candidate(
        _candidate(changed),
        store=store,
        model_id="fixture-model-a",
        call=_model_call,
        extractor=lambda _pdf: BODY,
    )
    assert first["state"] == "persisted"
    assert second["state"] == "persisted"
    assert second["write_state"] == "corrected"


def test_rank_vault_head_refuses_unreconciled_denominator():
    original = vault_head_mod.research_triage.rank
    vault_head_mod.research_triage.rank = lambda *args, **kwargs: {
        "rows": [{"report_id": REPORT_ID, "rank": 1, "w_score": 0.9, "status": "selected"}],
        "reconciled": False,
    }
    try:
        rank_vault_head([ITEM], as_of=__import__("datetime").date(2026, 9, 18), limit=1)
    except ValueError as exc:
        assert "reconcile" in str(exc)
    else:
        raise AssertionError("unreconciled triage must not produce a cognition head")
    finally:
        vault_head_mod.research_triage.rank = original


def test_extractor_exception_is_an_explicit_nontruth_state(tmp_path):
    store = LocalStore(tmp_path / "vault")
    _seed_pdf(store)

    def boom(_pdf):
        raise RuntimeError("extractor exploded")

    result = read_full_vault_body(store, REPORT_ID, extractor=boom)
    assert result["state"] == "extractor_failed"
    assert result["error_class"] == "RuntimeError"
    assert "body" not in result
