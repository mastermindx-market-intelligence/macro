from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

FORBIDDEN_OUTCOME_FIELDS = {
    "entry_price", "fwd_ret", "bench_ret", "excess_spy", "fwd_mfe", "fwd_mdd",
    "return", "score_after_fit", "predicted_return", "rank_after_fit",
}
KEY = ("stamp_date", "ticker", "board_definition")
SUPPORTED_GROUP = "SOLE_ACTIVE_MEMBERSHIP"

@dataclass(frozen=True)
class Verdict:
    state: str
    detail: str


def _key(row: dict[str, Any]) -> tuple[str, str, str]:
    return tuple(str(row.get(k) or "") for k in KEY)  # type: ignore[return-value]


def assert_outcome_redacted(payload: dict[str, Any]) -> None:
    seen: set[str] = set()
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k in FORBIDDEN_OUTCOME_FIELDS:
                    seen.add(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    if seen:
        raise ValueError("OUTCOME_FIELD_PRESENT:" + ",".join(sorted(seen)))


def dedupe_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        k = _key(row)
        if not all(k):
            raise ValueError("MISSING_NATIVE_KEY")
        if k in out and out[k] != row:
            raise ValueError("CONFLICTING_ORIGINAL_KEY")
        out.setdefault(k, row)
    return list(out.values())


def q1_ready(row: dict[str, Any]) -> bool:
    return all([
        row.get("security_id"), row.get("issuer_id"), row.get("identity_epoch"),
        row.get("theme_capture_group_state") == SUPPORTED_GROUP,
        row.get("theme_capture_group_id"),
        row.get("theme_capture_group_weighting") == "equal",
        row.get("peer_current_complete") is True,
        row.get("peer_prior_complete") is True,
        row.get("focal_issuer_excluded") is True,
    ])


def route_arm(row: dict[str, Any]) -> str:
    return "C1_C2_PEER" if q1_ready(row) else "C0_FALLBACK"


def source_readiness(row: dict[str, Any]) -> Verdict:
    if not row.get("security_id") or not row.get("issuer_id"):
        return Verdict("IDENTITY_UNRESOLVED", "missing canonical security/economic issuer")
    group = row.get("theme_capture_group_state")
    if group in (None, "SOURCE_UNAVAILABLE"):
        return Verdict("GROUP_SOURCE_UNAVAILABLE", "membership source unavailable")
    if group == "AMBIGUOUS_OVERLAP":
        return Verdict("GROUP_AMBIGUOUS_OVERLAP", "multiple active PIT memberships")
    if group == "UNSUPPORTED_WEIGHTING":
        return Verdict("UNSUPPORTED_WEIGHTING", "group is not accepted equal weighting")
    if group == "MEMBERSHIP_ROSTER_INCOHERENT":
        return Verdict("MEMBERSHIP_ROSTER_INCOHERENT", "roster witness inconsistent")
    if row.get("price_receipt_state") != "EXACT_ENCODED_OBJECT":
        return Verdict("PRICE_EVIDENCE_UNAVAILABLE", "selected price object is unattested")
    if row.get("price_basis") not in {"raw", "sadj", "tradj"}:
        return Verdict("PRICE_BASIS_UNATTESTED", "selected price basis missing")
    if row.get("rights_verified") is not True:
        return Verdict("RIGHTS_UNVERIFIED", "source rights are not attested")
    feature_end = row.get("feature_support_end")
    label_fill = row.get("label_fill")
    label_mark = row.get("label_mark")
    label_known = row.get("label_known_at")
    if not all([feature_end, label_fill, label_mark, label_known]):
        return Verdict("LABEL_USABLE_TIME_UNVERIFIED", "support/known-at receipt incomplete")
    # Feature and outcome support are deliberately not the same clock.
    if feature_end == label_mark:
        return Verdict("LABEL_USABLE_TIME_UNVERIFIED", "feature and label clocks collapsed")
    return Verdict("SOURCE_READY_FOR_REGISTERED_BATCH", "pre-outcome source gates represented")


def coverage(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("UNESTIMABLE_DENOMINATOR")
    n = len(rows)
    base = sum(bool(r.get("base_inputs_complete")) for r in rows) / n
    base_rows = [r for r in rows if r.get("base_inputs_complete")]
    q1 = (sum(q1_ready(r) for r in base_rows) / len(base_rows)) if base_rows else float("nan")
    return {"base": base, "q1_within_base": q1}


def main() -> None:
    good = {
        "stamp_date": "2027-01-05", "ticker": "AAA", "board_definition": "v1",
        "security_id": "SEC:AAA", "issuer_id": "ISS:AAA", "identity_epoch": "epoch_0",
        "theme_capture_group_state": SUPPORTED_GROUP, "theme_capture_group_id": "basket-x",
        "theme_capture_group_weighting": "equal", "peer_current_complete": True,
        "peer_prior_complete": True, "focal_issuer_excluded": True,
        "price_receipt_state": "EXACT_ENCODED_OBJECT", "price_basis": "tradj",
        "rights_verified": True, "base_inputs_complete": True,
        "feature_support_end": "2027-01-05", "label_fill": "2027-01-06",
        "label_mark": "2027-01-20", "label_known_at": "2027-01-20T21:30:00Z",
    }
    checks: list[dict[str, Any]] = []
    def check(name: str, got: Any, want: Any) -> None:
        ok = got == want
        checks.append({"name": name, "pass": ok, "got": repr(got), "want": repr(want)})
        if not ok:
            raise AssertionError(f"{name}: {got!r} != {want!r}")

    assert_outcome_redacted({"candidate": good, "grade_metadata": {"mark_date": "2027-01-20"}})
    check("outcome-redacted accepted metadata", True, True)
    try:
        assert_outcome_redacted({"candidate": good, "grade_metadata": {"excess_spy": 0.1}})
        leaked = False
    except ValueError:
        leaked = True
    check("outcome field rejected", leaked, True)

    check("identical duplicate collapses", len(dedupe_candidates([good, dict(good)])), 1)
    baddup = dict(good); baddup["issuer_id"] = "ISS:OTHER"
    try:
        dedupe_candidates([good, baddup]); conflict = False
    except ValueError:
        conflict = True
    check("conflicting original key fails", conflict, True)

    check("q1 row uses peer arm", route_arm(good), "C1_C2_PEER")
    overlap = dict(good); overlap["theme_capture_group_state"] = "AMBIGUOUS_OVERLAP"
    check("ambiguous group uses common fallback", route_arm(overlap), "C0_FALLBACK")
    focal = dict(good); focal["focal_issuer_excluded"] = False
    check("focal issuer leak uses common fallback", route_arm(focal), "C0_FALLBACK")
    prior = dict(good); prior["peer_prior_complete"] = False
    check("missing prior peer window uses common fallback", route_arm(prior), "C0_FALLBACK")

    check("fully represented source is ready", source_readiness(good).state, "SOURCE_READY_FOR_REGISTERED_BATCH")
    noid = dict(good); noid["security_id"] = None
    check("identity missing typed refusal", source_readiness(noid).state, "IDENTITY_UNRESOLVED")
    noprice = dict(good); noprice["price_receipt_state"] = "SOURCE_OBJECT_UNATTESTED"
    check("price receipt missing typed refusal", source_readiness(noprice).state, "PRICE_EVIDENCE_UNAVAILABLE")
    norights = dict(good); norights["rights_verified"] = False
    check("rights missing typed refusal", source_readiness(norights).state, "RIGHTS_UNVERIFIED")
    collapsed = dict(good); collapsed["feature_support_end"] = collapsed["label_mark"]
    check("feature/label clocks cannot collapse", source_readiness(collapsed).state, "LABEL_USABLE_TIME_UNVERIFIED")

    second = dict(good); second.update({"ticker": "BBB", "security_id": "SEC:BBB", "issuer_id": "ISS:BBB",
                                       "base_inputs_complete": False, "peer_prior_complete": False})
    cov = coverage([good, second])
    check("original denominator retained", cov["base"], 0.5)
    check("q1 denominator is within base only", cov["q1_within_base"], 1.0)

    result = {
        "schema": "mastermind.prophet.h1.prospective_known_answer.v1",
        "kind": "OUTCOME_REDACTED_SYNTHETIC_SMOKE",
        "checks": checks,
        "passed": len(checks),
        "failed": 0,
        "market_data_read": False,
        "protected_outcomes_read": False,
        "model_fit_executed": False,
        "ranking_changed": False,
        "trading_authority": False,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    out = Path(__file__).with_name("PROSPECTIVE_H1_KNOWN_ANSWER_RECEIPT.json")
    out.write_bytes(payload)
    print(json.dumps({"passed": len(checks), "failed": 0,
                      "receipt_sha256": hashlib.sha256(payload).hexdigest(),
                      "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}))

if __name__ == "__main__":
    main()