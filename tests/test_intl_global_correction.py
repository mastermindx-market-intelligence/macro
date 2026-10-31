"""IM12 E3 contract checks: superseding correction receipts, dependent-result
invalidation and saved-evidence preservation (masterplan §14 row 16,
"Correction propagation"). Fixture helpers are copied from
tests/test_intl_global_observation.py, never imported from it."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from engine.intl_global_correction import (
    CONTRACT_VERSION,
    CorrectionError,
    correction_chain,
    correction_receipt,
    invalidated,
    saved_evidence,
)
from engine.intl_global_observation import CONTRACT_VERSION as OBSERVATION_CONTRACT_VERSION
from engine.intl_global_observation import build_observation

CLOCKED = {
    "observation": {"at": "2026-10-07T00:00:00", "precision": "session_date"},
    "source_publication": {"at": "2026-10-09T15:00:00+00:00", "precision": "upper_bound"},
    "ingestion": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
    "computation": {"at": "2026-10-09T20:30:00+00:00", "precision": "exact"},
}
RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"

VALUES = {"local_pct": 5.0, "usd_pct": -5.5, "fx_pct": -10.0}
CORRECTED_VALUES = {"local_pct": 6.0, "usd_pct": -4.6, "fx_pct": -10.0}

#: The closed changed_fields path list, in the contract's fixed order.
TRACKED_PATHS = (
    "state",
    "abstain_reasons",
    "value.pct",
    "decomposition.local_pct",
    "decomposition.fx_pct",
    "decomposition.usd_pct",
    "clocks.observation",
    "clocks.source_publication",
    "evidence_ref",
)

RECEIPT_KEYS = {
    "contract_version", "correction_id", "slot", "original_id", "corrected_id",
    "revision", "clocks", "changed_fields", "caveats", "state",
    "abstain_reasons", "display",
}


def _identity(**overrides) -> dict:
    identity = {
        "universe_id": "JP", "market_id": "JP", "index_id": "^N225",
        "fx_id": "USDJPY=X", "horizon": "1m", "currency_basis": "usd_unhedged",
        "return_basis": "price", "window_start": "2026-09-08T00:00:00",
        "window_end": "2026-10-07T00:00:00", "source_content_sha256": "a" * 64,
    }
    identity.update(overrides)
    return identity


def _clocks(ingestion_at="2026-10-09T15:00:00+00:00",
            source_publication_at="2026-10-09T15:00:00+00:00",
            computation_at="2026-10-09T20:30:00+00:00") -> dict:
    return {
        "observation": {"at": "2026-10-07T00:00:00", "precision": "session_date"},
        "source_publication": {"at": source_publication_at, "precision": "upper_bound"},
        "ingestion": {"at": ingestion_at, "precision": "exact"},
        "computation": {"at": computation_at, "precision": "exact"},
    }


def _observation(*, source="a" * 64, values=None, clocks=None,
                 evidence_ref=EVIDENCE, rights=None, **identity_overrides) -> dict:
    return build_observation(
        identity=_identity(source_content_sha256=source, **identity_overrides),
        clocks=clocks if clocks is not None else _clocks(),
        values=VALUES if values is None else values,
        rights=dict(RIGHTS) if rights is None else rights,
        incumbent=dict(INCUMBENT),
        evidence_ref=evidence_ref,
    )


def _pair() -> "tuple[dict, dict]":
    """Original plus a cleanly superseding corrected record (later ingestion,
    different source content, everything else identical)."""
    return (_observation(),
            _observation(source="b" * 64,
                         clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00")))


def _corrected_receipt(**kwargs) -> dict:
    original, corrected = _pair()
    return correction_receipt(original, corrected, **kwargs)


# ---------------------------------------------------------------------------
# Contract identity and receipt shape
# ---------------------------------------------------------------------------

def test_contract_versions_pinned():
    assert CONTRACT_VERSION == "intl-global-correction-v1"
    # The observation gate is a literal in the correction module; this pin
    # keeps it from drifting away from the authority that owns the string.
    import engine.intl_global_correction as correction_module
    assert correction_module.OBSERVATION_CONTRACT_VERSION == OBSERVATION_CONTRACT_VERSION


def test_corrected_receipt_shape_and_keys():
    original = _observation()
    corrected = _observation(source="b" * 64, values=CORRECTED_VALUES,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(original, corrected)
    assert receipt["contract_version"] == CONTRACT_VERSION
    assert set(receipt) == RECEIPT_KEYS
    assert receipt["state"] == "corrected"
    assert receipt["abstain_reasons"] == []
    assert receipt["caveats"] == []
    assert receipt["original_id"] == original["observation_id"]
    assert receipt["corrected_id"] == corrected["observation_id"]
    assert receipt["slot"].startswith("slot:sha256:")
    assert receipt["correction_id"].startswith("corr:sha256:")
    assert receipt["revision"] == {"revision": 1, "supersedes": original["observation_id"]}
    assert receipt["clocks"] == {
        "original_ingestion": copy.deepcopy(CLOCKED["ingestion"]),
        "corrected_ingestion": {
            "at": "2026-10-09T16:00:00+00:00", "precision": "exact"},
        "corrected_source_publication": copy.deepcopy(CLOCKED["source_publication"]),
    }


def test_slot_excludes_source_content_sha256():
    # Same identity apart from the source digest: one slot, so the receipt
    # corrects rather than abstaining not_same_slot.
    receipt = _corrected_receipt()
    assert receipt["state"] == "corrected"
    original, _corrected = _pair()
    other_market = _observation(source="c" * 64, window_end="2026-10-08T00:00:00",
                                clocks=_clocks(ingestion_at="2026-10-09T17:00:00+00:00"))
    other_receipt = correction_receipt(original, other_market)
    assert other_receipt["abstain_reasons"] == ["not_same_slot"]
    assert other_receipt["slot"] != receipt["slot"]


def test_receipt_clock_is_none_when_clock_dict_absent():
    original = _observation(clocks={
        "observation": CLOCKED["observation"],
        "source_publication": CLOCKED["source_publication"],
        "computation": CLOCKED["computation"],
    })
    corrected = _observation(source="b" * 64,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(original, corrected)
    assert receipt["abstain_reasons"] == ["clock_missing"]
    assert receipt["state"] == "abstain"
    assert receipt["clocks"]["original_ingestion"] is None


def test_non_observation_inputs_raise_not_an_observation():
    original, corrected = _pair()
    with pytest.raises(CorrectionError, match="not_an_observation"):
        correction_receipt({"contract_version": "intl-global-dislocation-v1"}, corrected)
    with pytest.raises(CorrectionError, match="not_an_observation"):
        correction_receipt(original, {"contract_version": "intl-global-x-v1"})
    with pytest.raises(CorrectionError, match="not_an_observation"):
        correction_receipt("obs:sha256:x", corrected)


# ---------------------------------------------------------------------------
# Abstain reasons, each alone, and combinations in the fixed order
# ---------------------------------------------------------------------------

def test_clock_missing_alone_when_original_ingestion_unparseable():
    original = _observation(clocks=_clocks(ingestion_at="not-a-timestamp"))
    corrected = _observation(source="b" * 64,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(original, corrected)
    assert receipt["abstain_reasons"] == ["clock_missing"]
    assert receipt["state"] == "abstain"
    assert receipt["revision"] is None
    assert receipt["display"] is None


def test_clock_order_violation_alone():
    corrected = _observation(
        source="b" * 64,
        clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00",
                       source_publication_at="2026-10-06T15:00:00+00:00"))
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == ["clock_order_violation"]


def test_not_same_slot_alone():
    corrected = _observation(source="b" * 64, window_end="2026-10-08T00:00:00",
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == ["not_same_slot"]


def test_identical_content_alone():
    # Same identity (so same observation_id and source digest) but ingested
    # later: identical content is the ONLY reason it cannot supersede itself.
    corrected = _observation(clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == ["identical_content"]


def test_not_later_version_alone_on_equal_ingestion_instants():
    # Same ingestion instant, different source content: the corrected record
    # is NOT a later version (<= is a violation, not just <).
    corrected = _observation(source="b" * 64)
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == ["not_later_version"]


def test_session_date_ingestion_counts_as_next_day_midnight():
    session_dated = _observation(clocks={
        "observation": CLOCKED["observation"],
        "source_publication": CLOCKED["source_publication"],
        "ingestion": {"at": "2026-10-09T00:00:00", "precision": "session_date"},
        "computation": CLOCKED["computation"],
    })
    # 23:00Z on the session date is still BEFORE next-day 00:00Z: not later.
    same_day_later = _observation(
        source="b" * 64,
        clocks=_clocks(ingestion_at="2026-10-09T23:00:00+00:00",
                       computation_at="2026-10-10T00:30:00+00:00"))
    receipt = correction_receipt(session_dated, same_day_later)
    assert receipt["abstain_reasons"] == ["not_later_version"]
    # One second past next-day midnight IS later.
    next_day = _observation(
        source="b" * 64,
        clocks=_clocks(ingestion_at="2026-10-10T00:00:01+00:00",
                       computation_at="2026-10-10T01:00:00+00:00"))
    assert correction_receipt(session_dated, next_day)["state"] == "corrected"


def test_abstain_combination_keeps_the_fixed_order():
    corrected = _observation(
        source="a" * 64, window_end="2026-10-08T00:00:00",
        clocks=_clocks(ingestion_at=""))
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == [
        "clock_missing", "clock_order_violation", "not_same_slot", "identical_content"]
    # A second combination: same ingestion instant, different slot.
    corrected = _observation(source="b" * 64, window_end="2026-10-08T00:00:00")
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["abstain_reasons"] == ["not_same_slot", "not_later_version"]


def test_abstained_receipt_withholds_revision_display_and_caveat():
    corrected = _observation(source="b" * 64, window_end="2026-10-08T00:00:00")
    receipt = correction_receipt(_observation(), corrected)
    assert receipt["state"] == "abstain"
    assert receipt["revision"] is None
    assert receipt["display"] is None
    assert receipt["caveats"] == []


# ---------------------------------------------------------------------------
# changed_fields (closed list, fixed order) and caveats
# ---------------------------------------------------------------------------

def test_changed_fields_closed_list_and_order():
    original = _observation()
    corrected = _observation(source="b" * 64, values=CORRECTED_VALUES,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(original, corrected)
    assert [entry["path"] for entry in receipt["changed_fields"]] == [
        "value.pct", "decomposition.local_pct", "decomposition.usd_pct"]
    for entry in receipt["changed_fields"]:
        assert set(entry) == {"path", "old", "new"}
        assert entry["path"] in TRACKED_PATHS
    by_path = {entry["path"]: entry for entry in receipt["changed_fields"]}
    assert by_path["value.pct"]["old"] == -5.5
    assert by_path["value.pct"]["new"] == -4.6
    assert by_path["decomposition.local_pct"] == {"path": "decomposition.local_pct",
                                                  "old": 5.0, "new": 6.0}
    assert by_path["decomposition.usd_pct"]["old"] == -5.5
    assert by_path["decomposition.usd_pct"]["new"] == -4.6
    assert receipt["caveats"] == []


def test_changed_field_on_evidence_ref_and_state_paths():
    corrected = _observation(source="b" * 64, evidence_ref="saved-parquet:sha256:three",
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(_observation(), corrected)
    assert [entry["path"] for entry in receipt["changed_fields"]] == ["evidence_ref"]
    assert receipt["changed_fields"][0]["old"] == EVIDENCE
    assert receipt["changed_fields"][0]["new"] == "saved-parquet:sha256:three"


def test_missing_tracked_path_renders_none():
    withheld = _observation(rights={"decision_ref": ""})  # abstains: rights_unconfirmed
    assert withheld["state"] == "abstain"
    assert withheld["value"] is None
    corrected = _observation(source="b" * 64, values=CORRECTED_VALUES,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(withheld, corrected)
    by_path = {entry["path"]: entry for entry in receipt["changed_fields"]}
    assert by_path["state"] == {"path": "state", "old": "abstain", "new": "qualified"}
    assert by_path["abstain_reasons"]["old"] == ["rights_unconfirmed"]
    assert by_path["abstain_reasons"]["new"] == []
    assert by_path["value.pct"]["old"] is None
    assert by_path["value.pct"]["new"] == -4.6


def test_no_tracked_field_change_caveat():
    original, corrected = _pair()
    receipt = correction_receipt(original, corrected)
    assert receipt["changed_fields"] == []
    assert receipt["caveats"] == ["content_changed_no_tracked_field"]


# ---------------------------------------------------------------------------
# display (EN/ZH exact strings)
# ---------------------------------------------------------------------------

def test_display_exact_strings_for_value_pct_change():
    original = _observation()
    corrected = _observation(source="b" * 64, values=CORRECTED_VALUES,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    receipt = correction_receipt(original, corrected)
    assert set(receipt["display"]) == {"en", "zh"}
    assert receipt["display"]["en"] == (
        "Corrected 9 Oct 15:00 UTC · JP 1m return -5.50% → -4.60%")
    assert receipt["display"]["zh"] == (
        "已更正 10月9日 15:00 UTC · JP 1m 收益 -5.50% → -4.60%")


def test_display_prefers_the_first_numeric_path():
    # value.pct and decomposition.usd_pct BOTH differ; value.pct wins and the
    # label is "return", never the USD/local/FX leg label.
    original = _observation()
    corrected = _observation(source="b" * 64, values=CORRECTED_VALUES,
                             clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    display = correction_receipt(original, corrected)["display"]
    assert " return " in display["en"]
    assert "收益" in display["zh"]
    assert "USD return" not in display["en"]


def test_display_exact_strings_for_clocks_only_change():
    corrected = _observation(
        source="b" * 64,
        clocks=_clocks(ingestion_at="2026-10-10T16:00:00+00:00",
                       source_publication_at="2026-10-10T15:00:00+00:00",
                       computation_at="2026-10-10T20:30:00+00:00"))
    receipt = correction_receipt(_observation(), corrected)
    assert [entry["path"] for entry in receipt["changed_fields"]] == [
        "clocks.source_publication"]
    assert receipt["display"]["en"] == "Corrected 10 Oct 15:00 UTC · JP 1m"
    assert receipt["display"]["zh"] == "已更正 10月10日 15:00 UTC · JP 1m"


def test_display_falls_back_when_no_numeric_path_differs():
    original, corrected = _pair()
    receipt = correction_receipt(original, corrected)
    assert receipt["display"]["en"] == "Corrected 9 Oct 15:00 UTC · JP 1m"
    assert receipt["display"]["zh"] == "已更正 10月9日 15:00 UTC · JP 1m"


# ---------------------------------------------------------------------------
# correction_chain
# ---------------------------------------------------------------------------

def _chain_versions():
    v1 = _observation()
    v2 = _observation(source="b" * 64,
                      clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    v3 = _observation(source="c" * 64,
                      clocks=_clocks(ingestion_at="2026-10-09T17:00:00+00:00"))
    return v1, v2, v3


def test_chain_orders_versions_and_numbers_revisions():
    v1, v2, v3 = _chain_versions()
    chain = correction_chain([v3, v1, copy.deepcopy(v2), v2])
    assert chain["contract_version"] == CONTRACT_VERSION
    assert chain["slot"] == correction_receipt(v1, v2)["slot"]
    assert chain["versions"] == [v1["observation_id"], v2["observation_id"],
                                 v3["observation_id"]]
    assert len(chain["receipts"]) == 2
    first, second = chain["receipts"]
    assert first["original_id"] == v1["observation_id"]
    assert first["corrected_id"] == v2["observation_id"]
    assert first["revision"] == {"revision": 1, "supersedes": v1["observation_id"]}
    assert second["original_id"] == v2["observation_id"]
    assert second["corrected_id"] == v3["observation_id"]
    assert second["revision"] == {"revision": 2, "supersedes": v2["observation_id"]}
    assert chain["head"] == v3["observation_id"]


def test_chain_with_fewer_than_two_versions_has_no_receipts():
    v1 = _observation()
    single = correction_chain([v1])
    assert single["versions"] == [v1["observation_id"]]
    assert single["receipts"] == []
    assert single["head"] == v1["observation_id"]
    empty = correction_chain([])
    assert empty["versions"] == []
    assert empty["receipts"] == []
    assert empty["head"] is None


def test_chain_orders_equal_instants_by_observation_id():
    v2 = _observation(source="b" * 64)
    v_c = _observation(source="c" * 64)
    chain = correction_chain([v_c, v2])
    assert chain["versions"] == sorted([v2["observation_id"], v_c["observation_id"]])
    assert chain["head"] == max(v2["observation_id"], v_c["observation_id"])


def test_chain_rejects_mixed_slots():
    v1 = _observation()
    other = _observation(source="b" * 64, window_end="2026-10-08T00:00:00",
                         clocks=_clocks(ingestion_at="2026-10-09T16:00:00+00:00"))
    with pytest.raises(CorrectionError, match="not_same_slot"):
        correction_chain([v1, other])


def test_chain_rejects_non_observation_versions():
    with pytest.raises(CorrectionError, match="not_an_observation"):
        correction_chain([_observation(), {"contract_version": "intl-global-x-v1"}])


# ---------------------------------------------------------------------------
# invalidated (dependent derived results)
# ---------------------------------------------------------------------------

def _dislocation(dependency_id, subject_id, used=(), blocks=()):
    return {
        "contract_version": "intl-global-dislocation-v1",
        "dislocation_id": dependency_id,
        "subject": {"observation_id": subject_id},
        "references": {
            "used_observation_ids": list(used),
            "subject_block_ids": list(blocks),
        },
    }


def _result_invalidated_inputs():
    original, corrected = _pair()
    receipt = correction_receipt(original, corrected)
    direct = _dislocation("disl:sha256:aaa", original["observation_id"],
                          used=["obs:sha256:peer"], blocks=["obs:sha256:block1"])
    return receipt, [direct]


def test_invalidated_direct_dislocation_dependency():
    receipt, derived = _result_invalidated_inputs()
    result = invalidated(receipt, derived)
    assert set(result) == {"correction_id", "invalidated", "unaffected_count",
                           "paths", "withheld_reason"}
    assert result["correction_id"] == receipt["correction_id"]
    assert result["invalidated"] == ["disl:sha256:aaa"]
    assert result["unaffected_count"] == 0
    assert result["withheld_reason"] is None
    assert result["paths"] == {
        "disl:sha256:aaa": [receipt["original_id"], "disl:sha256:aaa"]}


def test_invalidated_is_transitive_through_generic_records():
    receipt, [direct] = _result_invalidated_inputs()
    second_hop = {"dependency_id": "watch:row:1",
                  "consumes": ["disl:sha256:aaa"]}
    unaffected = {"dependency_id": "watch:row:2",
                  "consumes": ["obs:sha256:unrelated"]}
    result = invalidated(receipt, [direct, second_hop, unaffected])
    assert result["invalidated"] == ["disl:sha256:aaa", "watch:row:1"]
    assert result["unaffected_count"] == 1
    assert result["paths"] == {
        "disl:sha256:aaa": [receipt["original_id"], "disl:sha256:aaa"],
        "watch:row:1": [receipt["original_id"], "disl:sha256:aaa", "watch:row:1"],
    }


def test_invalidated_shortest_path_wins_with_ascending_ties():
    receipt, [direct] = _result_invalidated_inputs()
    # watch:slow reaches watch:target in two hops; watch:fast in one. The
    # recorded chain for watch:target must be the one-hop chain.
    slow = {"dependency_id": "watch:slow", "consumes": ["disl:sha256:aaa"]}
    target = {"dependency_id": "watch:target",
              "consumes": ["watch:slow", "disl:sha256:aaa"]}
    result = invalidated(receipt, [direct, slow, target])
    assert result["paths"]["watch:target"] == [
        receipt["original_id"], "disl:sha256:aaa", "watch:target"]


def test_invalidated_withholds_when_receipt_not_corrected():
    abstained = correction_receipt(_observation(), _observation(
        source="b" * 64, window_end="2026-10-08T00:00:00"))
    derived = [{"dependency_id": "watch:row:1", "consumes": ["obs:sha256:any"]}]
    result = invalidated(abstained, derived)
    assert result["invalidated"] == []
    assert result["unaffected_count"] == 1
    assert result["paths"] == {}
    assert result["withheld_reason"] == "receipt_not_corrected"


def test_invalidated_rejects_undeclared_derived_shape():
    receipt, [direct] = _result_invalidated_inputs()
    with pytest.raises(CorrectionError, match="derived_record_shape"):
        invalidated(receipt, [direct, {"contract_version": OBSERVATION_CONTRACT_VERSION}])
    with pytest.raises(CorrectionError, match="derived_record_shape"):
        invalidated(receipt, [direct, {"consumes": ["obs:sha256:x"]}])
    with pytest.raises(CorrectionError, match="derived_record_shape"):
        invalidated(receipt, [direct, {"dependency_id": "watch:row:1",
                                       "consumes": "obs:sha256:x"}])


def test_invalidated_never_mutates_or_deletes_derived_records():
    receipt, [direct] = _result_invalidated_inputs()
    snapshot = copy.deepcopy([direct])
    invalidated(receipt, [direct])
    assert [direct] == snapshot


# ---------------------------------------------------------------------------
# saved_evidence (digest stability, affected, superseded_by)
# ---------------------------------------------------------------------------

def _canonical_digest(record) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_saved_evidence_preserves_record_and_flags_affected():
    receipt = _corrected_receipt()
    saved = {
        "kind": "saved_investigation",
        "thesis": f"JP dislocation reading rests on {receipt['original_id']}",
        "evidence_refs": [EVIDENCE],
    }
    snapshot = copy.deepcopy(saved)
    result = saved_evidence(saved, receipt)
    assert set(result) == {"record_digest_before", "record_digest_after",
                           "preserved", "affected", "superseded_by"}
    assert result["record_digest_before"] == _canonical_digest(snapshot)
    assert result["record_digest_after"] == result["record_digest_before"]
    assert result["preserved"] is True
    assert result["affected"] is True
    assert result["superseded_by"] == receipt["corrected_id"]
    assert saved == snapshot


def test_saved_evidence_unaffected_record_has_no_successor():
    receipt = _corrected_receipt()
    saved = {"kind": "saved_investigation", "thesis": "GB reading", "rows": []}
    result = saved_evidence(saved, receipt)
    assert result["affected"] is False
    assert result["superseded_by"] is None
    assert result["preserved"] is True


def test_saved_evidence_finds_original_id_in_nested_string_values():
    receipt = _corrected_receipt()
    saved = {"blocks": [{"refs": ["intro", receipt["original_id"]]}],
             "note": None}
    assert saved_evidence(saved, receipt)["affected"] is True


def test_saved_evidence_supersede_requires_corrected_receipt():
    abstained = correction_receipt(_observation(), _observation(
        source="b" * 64, window_end="2026-10-08T00:00:00"))
    saved = {"thesis": f"rests on {abstained['original_id']}"}
    result = saved_evidence(saved, abstained)
    assert result["affected"] is True
    assert result["superseded_by"] is None
    assert result["preserved"] is True


# ---------------------------------------------------------------------------
# purity and determinism
# ---------------------------------------------------------------------------

def test_correction_inputs_are_never_mutated():
    original, corrected = _pair()
    left, right = copy.deepcopy(original), copy.deepcopy(corrected)
    correction_receipt(original, corrected, prior_revision=3)
    correction_chain([original, corrected])
    assert original == left
    assert corrected == right


def test_correction_id_is_deterministic():
    original, corrected = _pair()
    first = correction_receipt(original, corrected)
    second = correction_receipt(copy.deepcopy(original), copy.deepcopy(corrected))
    assert first["correction_id"] == second["correction_id"]
    # A different prior revision is a different receipt.
    later = correction_receipt(original, corrected, prior_revision=1)
    assert later["correction_id"] != first["correction_id"]
    assert later["revision"] == {"revision": 2, "supersedes": original["observation_id"]}
    # A different corrected record is a different receipt.
    third = _observation(source="c" * 64,
                         clocks=_clocks(ingestion_at="2026-10-09T17:00:00+00:00"))
    assert correction_receipt(original, third)["correction_id"] != first["correction_id"]
