"""Outcome-free projection of untrusted receipts for the already-spent EVAL-1 trial.

This module performs no I/O and does not invoke an emitter, admission inspector,
label function, preprocessing or evaluator. A matching receipt is only structurally
compatible with the frozen EXP1 interface: its claimed producer, source vintage,
rights and population are NOT authenticated. No output is executable eligibility.
The three raw features are not imputed, standardized, fitted or calibrated.
"""
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import re


REGISTRATION_ID = "K3E-EVAL-1-V1"
REGISTRATION_DIGEST = "1ca158a213fca3f90c5c4fdc1359d40bf9146f2400cb10d8caa202b18f293bd4"
CONTRACT_DIR = "research/alpha_intelligence/expectation_market_dynamics/"
# Existing immutable source bytes, not a new registration or trial identity.
CONTRACT_BLOBS = {
    CONTRACT_DIR + "eval1_preregistration.v1.json": "a419e3dc7d8caa747ed94392b9173daff8151d9a",
    CONTRACT_DIR + "eval1_owner_acceptance.v1.json": "e17156ae8319336389c0d08bbe04751a4d9f1665",
    CONTRACT_DIR + "eval1_activation_receipt.v1.json": "d1db3d573455ee763cbc8074c4b6cddff6fd9612",
    CONTRACT_DIR + "eval1_challenger_trial_identity.v1.json": "5a23dd158cf52dbb5ee3d93d83004fecfca13df1",
}
EMITTER = {
    "path": "engine/k3e_expectation_surface.py",
    "function": "inspect_expectation_surface",
    "blob": "3032ad4e8eb1681749cf50d353039015334343b3",
}
FEATURES = ("rights_blocked_state", "true_missing_share",
            "invalid_or_inconsistent_excluded_share")
ROW_FIELDS = ("issuer_ref", "metric", "fiscal_period", "cutoff_session",
              "decision_cutoff", "provider", "ticker_compat", "horizon_label_raw")
INPUT_PATHS = ("data/revisions/expectation_observations.parquet",
               "data/revisions/expectation_attempts.parquet")
ALIAS_PATH = "data/reference/vendor_aliases.parquet"
GAPS = ("RECEIPT_AUTHENTICITY_UNVERIFIED", "POINT_IN_TIME_POPULATION_UNVERIFIED",
        "RIGHTS_ADMISSION_UNVERIFIED", "SOURCE_ONLY_EXECUTION_DISABLED")


class SourceRefusal(ValueError):
    """Structural refusal; never permission to retrieve replacement inputs."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _utc(value):
    if not isinstance(value, str):
        raise SourceRefusal("INVALID_DECISION_CUTOFF")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceRefusal("INVALID_DECISION_CUTOFF") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise SourceRefusal("INVALID_DECISION_CUTOFF")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bind_contracts(artifacts):
    if not isinstance(artifacts, dict) or set(artifacts) != set(CONTRACT_BLOBS):
        raise SourceRefusal("FROZEN_SOURCE_ARTIFACTS_REQUIRED")
    for path, expected in CONTRACT_BLOBS.items():
        raw = artifacts[path]
        if not isinstance(raw, bytes) or _git_blob(raw) != expected:
            raise SourceRefusal("FROZEN_SOURCE_ARTIFACT_MISMATCH")
    # Exact bytes bind all seven elements, including preprocessing/seed, without
    # executing any of them or treating historical admission as a current grant.


def _row_identity(row):
    if not isinstance(row, dict):
        raise SourceRefusal("INVALID_DECISION_ROW")
    if any(not isinstance(row.get(k), str) or not row[k].strip()
           or row[k] != row[k].strip() or len(row[k]) > 200 for k in ROW_FIELDS):
        raise SourceRefusal("INCOMPLETE_DECISION_ROW_IDENTITY")
    if row["metric"] not in {"EPS", "revenue"}:
        raise SourceRefusal("INVALID_METRIC")
    try:
        if date.fromisoformat(row["cutoff_session"]).isoformat() != row["cutoff_session"]:
            raise ValueError
    except ValueError as exc:
        raise SourceRefusal("INVALID_CUTOFF_SESSION") from exc
    identity = {k: row[k] for k in ROW_FIELDS}
    identity["decision_cutoff"] = _utc(row["decision_cutoff"])
    if identity["decision_cutoff"][:10] != identity["cutoff_session"]:
        raise SourceRefusal("CUTOFF_SESSION_CLOCK_MISMATCH")
    return identity


def _trial_row_key(identity):
    # Frozen fit ordering identifies one row per issuer/metric/period/session.
    # Two source generations for that row are ambiguity, never a latest winner.
    return tuple(identity[k] for k in ("issuer_ref", "metric", "fiscal_period", "cutoff_session"))


def _pin(item):
    return (isinstance(item, dict) and set(item) == {"sha256", "git_blob_id"}
            and isinstance(item["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None
            and isinstance(item["git_blob_id"], str)
            and re.fullmatch(r"[0-9a-f]{40}", item["git_blob_id"]) is not None)


def _project(identity, receipt):
    if not isinstance(receipt, dict):
        raise SourceRefusal("PINNED_EXP1_RECEIPT_REQUIRED")
    if receipt.get("emitter") != EMITTER:
        raise SourceRefusal("FROZEN_EMITTER_IDENTITY_MISMATCH")
    payload = receipt.get("semantic_payload")
    if not isinstance(payload, dict) or payload.get("schema") != "k3e.declared_capture_inspection.v1":
        raise SourceRefusal("INVALID_EXP1_PAYLOAD")
    if receipt.get("semantic_digest") != _digest(payload):
        raise SourceRefusal("EXP1_SEMANTIC_DIGEST_MISMATCH")
    query = {k: identity[k] for k in ("provider", "ticker_compat", "metric", "horizon_label_raw")}
    query["as_of"] = identity["decision_cutoff"]
    if payload.get("query") != query:
        raise SourceRefusal("EXACT_ROW_CUTOFF_QUERY_REQUIRED")
    source = payload.get("source")
    if not isinstance(source, dict) or set(source) != {"source_revision", "inputs"}:
        raise SourceRefusal("IMMUTABLE_SOURCE_PINS_REQUIRED")
    revision, inputs = source["source_revision"], source["inputs"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SourceRefusal("IMMUTABLE_SOURCE_PINS_REQUIRED")
    if (not isinstance(inputs, dict) or not set(INPUT_PATHS) <= set(inputs)
            or not set(inputs) <= set(INPUT_PATHS) | {ALIAS_PATH}
            or not all(_pin(inputs[p]) for p in INPUT_PATHS)):
        raise SourceRefusal("PAIRED_INPUT_PINS_REQUIRED")
    if ALIAS_PATH in inputs:
        alias = inputs[ALIAS_PATH]
        absent = (isinstance(alias, dict) and set(alias) == {"absent_at_revision"}
                  and alias["absent_at_revision"] is True)
        if not (_pin(alias) or absent):
            raise SourceRefusal("INVALID_ALIAS_PIN")
    query_identity = _digest({"schema": payload["schema"], "query": query, "source": source})
    if payload.get("query_identity") != query_identity:
        raise SourceRefusal("EXP1_QUERY_IDENTITY_MISMATCH")
    den = payload.get("denominators")
    counts = ("capture_clock_bounded_relevant_records", "true_missing_records",
              "invalid_or_inconsistent_excluded_records")
    if not isinstance(den, dict) or any(type(den.get(k)) is not int or den[k] < 0 for k in counts):
        raise SourceRefusal("INVALID_FEATURE_DENOMINATORS")
    total = den[counts[0]]
    if any(den[k] > total for k in counts[1:]):
        raise SourceRefusal("INVALID_FEATURE_DENOMINATORS")
    baseline = payload.get("normalized_baseline")
    if not isinstance(baseline, dict) or baseline.get("rights_state") not in {"RIGHTS_BLOCKED", "UNKNOWN"}:
        raise SourceRefusal("INVALID_FROZEN_RIGHTS_STATE")
    values = (float(baseline["rights_state"] == "RIGHTS_BLOCKED"),
              den[counts[1]] / total if total else None,
              den[counts[2]] / total if total else None)
    # Rights/identity/correction exclusions remain in the emitter's total. No
    # selected/latest-supported snapshot is used as a smaller denominator.
    return {"features": dict(zip(FEATURES, values)),
            "feature_denominators": {k: total for k in FEATURES},
            "source_denominators": {k: den[k] for k in counts},
            "claimed_source": json.loads(json.dumps(source)),
            "claimed_emitter": dict(EMITTER), "query_identity": query_identity,
            "receipt_semantic_digest": receipt["semantic_digest"]}


def prepare_source_rows(rows, *, frozen_artifacts):
    """Project untrusted in-memory EXP1 receipts; preserve every declared row.

    Each row contains the eight ROW_FIELDS plus optional ``exp1_receipt``. Extra
    keys (including claimed admission, labels and results) grant nothing and are
    never returned. Source artifacts are bytes supplied by the caller, not read
    here. Neither their match nor any receipt digest proves canonical admission,
    authenticity, NYSE membership, original vintage, correction or source rights.
    """
    if not isinstance(rows, (list, tuple)):
        raise SourceRefusal("DECISION_ROW_SEQUENCE_REQUIRED")
    binding_error = None
    try:
        _bind_contracts(frozen_artifacts)
    except SourceRefusal as exc:
        binding_error = exc.reason
    identities, errors = [], []
    for row in rows:
        try:
            identities.append(_row_identity(row))
            errors.append(None)
        except SourceRefusal as exc:
            identities.append(None)
            errors.append(exc.reason)
    multiplicity = Counter(_trial_row_key(i) for i in identities if i is not None)
    result = []
    for ordinal, (row, identity, error) in enumerate(zip(rows, identities, errors)):
        projected = {"features": dict.fromkeys(FEATURES),
                     "feature_denominators": dict.fromkeys(FEATURES)}
        reasons = [e for e in (binding_error, error) if e]
        if identity is not None and multiplicity[_trial_row_key(identity)] > 1:
            reasons.append("DUPLICATE_TRIAL_ROW_GENERATIONS")
        if not reasons:
            try:
                projected = _project(identity, row.get("exp1_receipt"))
            except SourceRefusal as exc:
                reasons.append(exc.reason)
            except (TypeError, ValueError, OverflowError, RecursionError):
                reasons.append("NON_CANONICAL_EXP1_RECEIPT")
        result.append({"ordinal": ordinal, "row_identity": identity,
                       "projection_status": "UNAVAILABLE" if reasons else "STRUCTURALLY_COMPATIBLE_UNTRUSTED",
                       **projected, "refusals": reasons,
                       "eligible_for_execution": False, "qualification_gaps": list(GAPS)})
    return {"schema": "k3e.eval1_source_projection/v1", "registration_id": REGISTRATION_ID,
            "registration_digest_sha256": REGISTRATION_DIGEST,
            "frozen_contract_blobs": dict(CONTRACT_BLOBS),
            "source_binding_status": "UNAVAILABLE" if binding_error else "EXACT_SOURCE_BYTES_ONLY",
            "target": "T1_NEXT_REVISION_DIRECTION", "horizon": {"sessions": 21, "calendar": "NYSE"},
            "feature_names": list(FEATURES), "rows": result,
            "denominators": {"declared_decision_rows": len(rows),
                             "structurally_projected_rows": sum(not r["refusals"] for r in result),
                             "unavailable_rows": sum(bool(r["refusals"]) for r in result),
                             "eligible_for_execution_rows": 0},
            "outcome_access_allowed": False, "financial_influence": False,
            "promotion_eligible": False, "qualification_gaps": list(GAPS)}


def run_eval1(*, outcome_access_allowed=False):
    """Refusal-only seam. Even a true admission flag cannot start any effect.

    Deliberately accepts no reader, dataset, callback, model or execution handle.
    There is no positive branch and no original-run restoration/replay mechanism.
    """
    return {"schema": "k3e.eval1_execution_refusal/v1", "status": "REFUSED",
            "reason": "SOURCE_ONLY_EXECUTION_DISABLED", "registration_id": REGISTRATION_ID,
            "outcome_access_allowed": False, "execution_started": False,
            "qualification_gaps": list(GAPS)}
