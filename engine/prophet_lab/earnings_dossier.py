"""Human-readable factual earnings detail from the EXISTING admitted D5 vector.

No event discovery, source fetching, episode clock selection, ranking or policy
is implemented here. D5 retains those owners. The optional Q06 companion is the
exact reviewed source record on #8069, not a reconstructed consensus estimate.
Its absence does not remove the existing D5 observation or research candidate.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from engine.prophet_lab.intelligence_vector import validate_intelligence_vector
from engine.sue import aware_utc, factual_dossier

SCHEMA = "prophet.episode_earnings_detail/v1"
Q06_CONTRACT_PATH = "research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_source_contract.v0_2.json"
Q06_CONTRACT_SHA256 = "a0790967ad56740fe740e7026e53eda34f3c2529ca75d6dfca64d28b293a177d"
Q06_RIGHTS_PATH = "research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md"
Q06_RIGHTS_BLOB = "a9ee6f288bfb2716facd88dcf2c5135ca8125303"
Q06_CONTRACT_REF = "macro:8069:ae9409bca5d81dbf7438ff0037a976b324853bdd:q06-source-contract-v0.2"
Q06_CANONICAL_SHA256 = "c3850d365fc855f874125351c0bfa39c7a98195a88c8b4a469d1f58d9304a3af"
Q06_EVENT_ID = "evt_cik0000320193_2026q3_results"
_MAX_SOURCE_BYTES = 262_144
AUTHORITY = {"rank": False, "entry": False, "size": False, "execution": False, "trade": False}


def load_q06_source_field(root: Path) -> tuple[dict[str, Any] | None, str]:
    """Use only the installed canonical source record and unchanged rights record.

    ``root`` comes from the existing server composition root, never request data.
    This is source-byte qualification, NOT authentication of an approval or a
    financial-model promotion. #8069 source release remains a deployment dependency.
    No alternate folder, live fetch, normalized-body guess or latest fallback.
    """
    try:
        path = root / Q06_CONTRACT_PATH
        rights_path = root / Q06_RIGHTS_PATH
        if not path.exists():
            return None, "SOURCE_CONTRACT_NOT_INSTALLED"
        if path.is_symlink() or rights_path.is_symlink():
            return None, "SOURCE_CONTRACT_UNQUALIFIED"
        raw = path.read_bytes()
        rights = rights_path.read_bytes()
        if len(raw) > _MAX_SOURCE_BYTES or len(rights) > _MAX_SOURCE_BYTES:
            return None, "SOURCE_CONTRACT_UNQUALIFIED"
        if sha256(raw).hexdigest() != Q06_CONTRACT_SHA256:
            return None, "SOURCE_CONTRACT_CHANGED"
        rights_blob = sha1(f"blob {len(rights)}\0".encode() + rights).hexdigest()
        if rights_blob != Q06_RIGHTS_BLOB:
            return None, "SOURCE_RIGHTS_CHANGED"
        field = json.loads(raw)
        if not isinstance(field, dict):
            return None, "SOURCE_CONTRACT_UNQUALIFIED"
        return field, "SOURCE_CONTRACT_BOUND"
    except (OSError, ValueError):
        return None, "SOURCE_CONTRACT_UNAVAILABLE"


def _q06_change(
    vector: Mapping[str, Any], family: Mapping[str, Any],
    field: Mapping[str, Any] | None, source_state: str,
) -> tuple[dict[str, Any] | None, str]:
    if field is None:
        return None, source_state
    # This is an internal projection of the fixed accepted field, not a general
    # recipe runner. A changed canonical record must be separately reviewed.
    if field.get("schema") != "prophet.q06.sec_comparable_revenue_source_contract.v0.2":
        return None, "SOURCE_CONTRACT_UNQUALIFIED"
    try:
        raw = json.dumps(field, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError):
        return None, "SOURCE_CONTRACT_UNQUALIFIED"
    if sha256(raw).hexdigest() != Q06_CANONICAL_SHA256:
        return None, "SOURCE_CONTRACT_CHANGED"
    econ = field["economic_identity"]
    provenance = field["field_provenance"]
    binding = family["subject_binding"]
    if (binding.get("owner_subject_id") != Q06_EVENT_ID
            or binding.get("earnings_company_id") != "cik:" + econ["cik"]):
        return None, "SOURCE_FIELD_NOT_APPLICABLE"
    if (family["rights"]["state"] != "ALLOWED"
            or family["point_in_time"]["decision_admissibility"] != "ADMISSIBLE"):
        return None, "SOURCE_FIELD_NOT_ADMISSIBLE"
    decision = vector["decision_cut"]["opened_at"]
    clock = provenance["clocks"]["source_available_at"]
    native_clock = family["point_in_time"]["source_published_at"].get("value")
    if (native_clock is None or aware_utc(native_clock) != aware_utc(clock)
            or aware_utc(clock) > aware_utc(decision)):
        return None, "SOURCE_FIELD_CLOCK_MISMATCH"
    sources = {
        item["source_ref_id"]: item for item in family["source_refs"]
        if item["object_schema"] == "event_workspace.source/issuer_release"
        and item["content_hash"] == provenance["source_document"]["normalized_body_sha256"]
    }
    observations = [
        item for item in family["observations"]
        if item["native_metric_id"] == "fact:revenue"
        and item["value_state"] == "PRESENT"
        and any(ref in sources for ref in item["source_ref_ids"])
    ]
    if len(observations) != 1:
        return None, "SOURCE_FIELD_REVISION_MISMATCH"
    current, prior = econ["current"], econ["prior"]
    observation = observations[0]
    if (current["unit"] != "usd_millions" or prior["unit"] != "usd_millions"
            or current["currency"] != prior["currency"] or current["basis"] != prior["basis"]
            or observation["value_usd"] != current["value"] * 1_000_000):
        return None, "SOURCE_FIELD_VALUE_MISMATCH"
    # Both values are supported by the SAME source release. Do not assign the
    # prior value a fictional older publication/ingestion time or prior event.
    now = current["value"]
    before = prior["value"]
    if before <= 0:
        return None, "SOURCE_FIELD_DENOMINATOR_INVALID"
    pct = (now / before - 1) * 100
    if abs(pct - econ["value_pct"]) > 1e-10:
        return None, "SOURCE_FIELD_ARITHMETIC_MISMATCH"
    result = {
        "schema": "prophet.earnings_evidence/v1",
        "kind": "COMPARABLE_REPORTED_CHANGE",
        "issuer_id": binding["earnings_company_id"],
        "issuer_name": econ["issuer"],
        "metric": econ["metric"],
        "period_role": "QUARTER",
        "current_fiscal_period": econ["fiscal_period"],
        "prior_fiscal_period": prior["period"],
        "current_value": now, "prior_value": before,
        "units": current["unit"], "currency": current["currency"], "basis": current["basis"],
        "signed_difference": now - before,
        "change_fraction": pct / 100, "change_pct": pct,
        "current_event_id": Q06_EVENT_ID, "prior_event_id": Q06_EVENT_ID,
        "comparison_origin": "SAME_CURRENT_RELEASE_COMPARATIVE_TABLE",
        "current_available_at": clock, "prior_available_at": clock,
        "decision_at": decision,
        "economic_id": econ["economic_id"],
        "field_provenance_id": provenance["field_provenance_id"],
        "source_ref_ids": sorted(set(observation["source_ref_ids"]) & sources.keys()),
        "source_contract_ref": Q06_CONTRACT_REF,
        "rank_authority": False, "entry_authority": False,
    }
    return result, "COMPARABLE_REPORTED_CHANGE_BOUND"


def project_earnings_detail(
    vector: Mapping[str, Any], *, source_field: Mapping[str, Any] | None = None,
    source_state: str = "SOURCE_CONTRACT_NOT_INSTALLED",
) -> dict[str, Any]:
    """Project a validated D5 result once, retaining its original decision cut.

    There is no second workspace read. Older episodes keep the original source
    revision selected by D5, never today's body or a current-number substitution.
    Source refs are opaque derived identifiers; raw source/rights paths stay private.
    """
    validate_intelligence_vector(vector)
    family = vector["evidence_families"][0]
    binding = family["subject_binding"]
    changes = []
    change, comparison_state = _q06_change(vector, family, source_field, source_state)
    if change is not None:
        changes.append(change)
    observations = deepcopy(family["observations"])
    revenue = next((x for x in observations
                    if x["native_metric_id"] == "fact:revenue" and x["value_state"] == "PRESENT"), None)
    event_id = binding.get("owner_subject_id")
    issuer_id = binding.get("earnings_company_id")
    dossier = None
    if binding["state"] == "RESOLVED" and event_id and issuer_id:
        dossier = factual_dossier(
            event_id=event_id, issuer_id=issuer_id,
            decision_at=vector["decision_cut"]["opened_at"],
            reported_changes=changes,
            source_contract_refs=([Q06_CONTRACT_REF] if changes else [vector["projection_id"]]),
        )
    headline = (
        f"Revenue grew {change['change_pct']:.1f}% against the comparable prior-year quarter"
        if change is not None else
        "Reported revenue available; comparable growth is not yet verified"
        if revenue is not None else "Earnings evidence is unavailable for this decision"
    )
    return {
        "schema": SCHEMA,
        "episode_ref": deepcopy(vector["episode_ref"]),
        "source_projection_id": vector["projection_id"],
        "decision_cut": deepcopy(vector["decision_cut"]),
        "time_interpretation": "ORIGINAL_SOURCE_VINTAGE_RECONSTRUCTION_NOT_ORIGINAL_RECOMMENDATION",
        "method_scope": "RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION",
        "is_original_as_run_recommendation": False,
        "coverage": deepcopy(family["coverage"]),
        "headline": headline,
        "interpretation": "Reported operating evidence; not a consensus beat, forecast or permission to buy.",
        "comparison_state": comparison_state,
        "current_observations": observations,
        "dossier": dossier,
        "missing": ["QUALIFIED_PRE_RELEASE_EXPECTATION", "MATCHED_FORECAST_REVISIONS",
                    "CURRENT_ENTRY_AND_MARKET_PERMISSION"],
        "authority": dict(AUTHORITY),
    }
