"""Static verification for the Consumer R13 review manifest.

Research-only: validates immutable local companion blobs and handoff invariants.
It does not query GitHub, execute application code, stage native files, or claim
that mutable external-owner refs remain current.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = HERE / "R13_REVIEW_MANIFEST.json"


def git_blob(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks: list[str] = []

    assert m["schema"] == "consumer_cyclical.r13_review_manifest.v1"
    checks.append("schema")

    assert m["authority"]["research_only"] is True
    assert not any(
        m["authority"][key]
        for key in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry")
    )
    checks.append("authority_false")

    companions = m["m6_reviewer_packet"]["companions"]
    assert len(companions) == 3
    assert sum(item["mapped_requirements"] for item in companions) == 58
    assert m["m6_reviewer_packet"]["corrected_requirement_universe"] == 174
    assert m["m6_reviewer_packet"]["incorrect_count_to_reject"] == 206
    for item in companions:
        path = ROOT / item["path"]
        assert path.is_file(), item["path"]
        assert git_blob(path.read_bytes()) == item["blob"], item["path"]
    checks.append("m6_companion_blobs_and_counts")

    rights = m["m7_source_rights"]
    allowed = set(rights["qualified_house_representation"])
    denied = set(rights["not_claimed_by_sec_edgar_family"])
    assert allowed and denied
    assert allowed.isdisjoint(denied)
    assert rights["licensing"]["redistribution_ok"] is False
    assert rights["entitlement_never_supplies_source_rights"] is True
    checks.append("m7_representation_partition")

    pins = m["m8_native_pins"]
    assert pins["must_refresh_immediately_before_native_write"] is True
    assert pins["stale_pin_must_not_authorize_write"] is True
    for value in (
        pins["macro_main_at_reconciliation"],
        pins["consumer_pr_head_before_r13"],
        pins["shared_foundation"]["head"],
        pins["template_owner"]["head"],
        pins["theme_graph_store_owner"]["head"],
        pins["company_history_owner"]["pr_head"],
    ):
        assert len(value) == 40
        assert all(char in "0123456789abcdef" for char in value)
    assert pins["stale_historical_native_pin"] not in {
        pins["macro_main_at_reconciliation"],
        pins["shared_foundation"]["head"],
    }
    checks.append("m8_pin_shape_and_refresh_rule")

    pay = m["m9_entitlement_policy"]
    assert pay["status"] == "BOUND_TO_INCUMBENT_ACCEPTED_CODE_AND_TEST"
    assert pay["chosen_semantics"]["configured_grace_is_clamped_seconds"] == [0, 86400]
    assert pay["chosen_semantics"]["failed_store_refresh_does_not_renew_deadline"] is True
    assert pay["chosen_semantics"]["invalid_or_missing_auth_gets_grace"] is False
    assert pay["chosen_semantics"]["fresh_reachable_negative_gets_grace"] is False
    assert pay["chosen_semantics"]["invalidation_removes_cached_positive"] is True
    assert pay["production_acceptance"] is False
    assert len(pay["accepted_test_cases"]) >= 2
    checks.append("m9_policy_binding")

    gates = m["external_gates"]
    assert all(value is False for value in gates.values())
    checks.append("external_gates_still_false")

    profile = m["consumer_profile_binding"]
    assert profile["status"] == "PENDING_SHARED_OWNER_ACCEPTANCE"
    assert profile["must_not_fall_back_to_semiconductor"] is True
    assert profile["unsupported_must_refuse"] is True
    assert profile["reported_economics_must_not_require_fabricated_management_history"] is True
    checks.append("profile_fail_closed")

    sticky = m["sticky_constraints"]
    assert sticky["native_staging_action"].startswith("BLOCKED_DO_NOT_RETRY")
    checks.append("sticky_native_staging_hold")

    result = {
        "kind": "consumer_r13_manifest_verification",
        "passed": len(checks),
        "failed": 0,
        "checks": checks,
        "native_application_tests": 0,
        "native_staging_actions": 0,
        "browser_proofs": 0,
        "production_acceptance": False,
    }
    (HERE / "verification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in result.items() if key != "checks"}))


if __name__ == "__main__":
    main()
