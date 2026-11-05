"""Narrow adoption-sidecar binding and exact arithmetic control.

Not a selector, numeric input parser, source verifier, or admission adapter.
Only reads named frozen scratch artifacts and prints a synthetic/binding receipt.
"""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIDE = ROOT / "lanes/source_diagnostic_policy_adoption_v1"


def bind(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "byte_length": len(raw),
            "sha256": sha256(raw).hexdigest()}


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def differences(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            child = path + "/" + key
            result.extend([child] if key not in a or key not in b
                          else differences(a[key], b[key], child))
        return result
    return [] if a == b else [path]


def canonical_binding(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {"byte_length": len(raw), "sha256": sha256(raw).hexdigest()}


def main():
    before = [bind(p) for p in sorted(SIDE.iterdir()) if p.is_file()]
    assert len(before) == 5 and sum(x["byte_length"] for x in before) == 19510
    assert bind(SIDE / "POLICY_ADOPTION.json")["sha256"] == "645a20a39842d9c5a03b4ff39a37280d1aa02c32ef545c061d0aa959f06e0016"
    assert bind(SIDE / "PRINCIPAL_ADOPTION.md")["sha256"] == "1c2d9c72ad7ea969a5b41294845bb55d4fcb0158802b74e5ccff815e36264783"
    assert bind(SIDE / "MANIFEST.json")["sha256"] == "82839b3edfb68baf03ebbc8e435d9c9b63dd7bea50e0c8eb3b17bd52e9194e7e"
    for item in load(SIDE / "MANIFEST.json")["files"]:
        assert bind(ROOT / item["path"]) == item
    adoption = load(SIDE / "POLICY_ADOPTION.json")
    refs = [adoption[k] for k in ("source_policy", "source_memo", "corrective_review",
                                  "corrective_findings", "corrective_review_manifest")]
    for item in refs:
        assert bind(ROOT / item["path"]) == item
    base = load(ROOT / adoption["source_policy"]["path"])
    overrides = adoption["normative_overrides"]
    assert len(overrides) == 1
    override = overrides[0]
    assert override["pointer"] == "/capitalization/numeric_rule" and override["finding"] == "R3"
    assert base["capitalization"]["numeric_rule"] == override["expected_original"]
    effective = deepcopy(base)
    effective["capitalization"]["numeric_rule"] = override["replacement"]
    delta = differences(base, effective)
    assert delta == ["/capitalization/numeric_rule"]
    assert delta == load(SIDE / "ADOPTION_VALIDATION.json")["exact_effective_normative_changed_pointers"]
    decisions = {d["id"]: d for d in adoption["decisions"]}
    assert len(decisions) == len(base["proposed_semantic_adoptions"]) == 3
    for source in base["proposed_semantic_adoptions"]:
        decided = decisions[source["id"]]
        assert decided["adopted_meaning"] == source["proposed"]
        assert decided["decision"] == "ADOPT_FOR_BOUNDED_SOURCE_DIAGNOSTIC_METHOD"
        assert decided["changes_120_quota"] is False
    p, q = adoption["unchanged_parameters"], base["preserved_law"]
    assert p["total_issuers"] == q["total_issuers"] == 120
    assert p["strata_each"] == q["issuer_count_per_stratum"] == 24
    assert p["groups_each"] == q["issuer_count_per_stratum_group"] == 4
    assert p["size_slots"] == q["quota_by_size_slot"] == {"L": 2, "M": 1, "S": 1}
    assert p["INT"] == q["international_country_group_quotas"] == {"UK": 8, "JP": 8, "EU": 8}
    assert p["D"] == base["cutoff_policy"]["proposed_valuation_local_date"] == "2026-09-30"
    assert p["K"] == base["cutoff_policy"]["public_knowledge_cutoff_utc"] == "2026-10-09T00:00:00Z"
    assert p["F"] is None and base["cutoff_policy"]["actual_native_evidence_freeze_at_utc"] is None
    assert p["seed"] == base["deterministic_selection"]["seed_utf8"] == "GMI-WP02-20261009-v1"
    assert p["reference_pool_count"] == base["relative_size"]["pool_count"] == 42
    assert p["difficult_cases_minimum"] == q["difficult_cases_minimum"] == 30
    assert p["difficult_cases_each_stratum_minimum"] == q["difficult_cases_per_stratum_minimum"] == 6
    kernel = adoption["first_executable_scope"]
    for field in ("default_real_source_mode_is_unconditionally_held",
                  "untrusted_receipt_flags_cannot_change_mode",
                  "synthetic_label_does_not_authenticate_or_classify_source_truth"):
        assert kernel[field] is True
    for field in ("callable_real_source_admission_adapter_selected", "real_input_quantiles",
                  "real_input_reference_cap_resolution", "real_input_selected_cohort"):
        assert kernel[field] is None
    assert kernel["source_authority_state"] == "SOURCE_AUTHORITY_UNVERIFIED"
    assert kernel["source_rights_state"] == "SOURCE_RIGHTS_UNVERIFIED"
    assert kernel["real_history_state"] == "FRAME_HISTORY_UNPROVEN"
    assert all(value is False for value in adoption["authority"].values())
    assert adoption["commissioning_sol_ceo_architectural_adjudication"] == "NOT_ASSERTED"
    control = load(SIDE / "NUMERIC_CLARIFICATION_CONTROL.json")
    count, action, price = (Fraction(control[k]) for k in ("base_shares", "signed_retirement", "price"))
    signed, erroneous, unchanged = (count + action) * price, (count + abs(action)) * price, (count + Fraction("0")) * price
    assert signed == Fraction(control["correct_cap"]) == 1800000000
    assert erroneous == Fraction(control["incorrect_abs_delta_cap"]) == 2200000000
    assert unchanged == count * price == 2000000000
    assert signed < 2000000000 <= erroneous
    for item in refs:
        assert bind(ROOT / item["path"]) == item
    assert before == [bind(p) for p in sorted(SIDE.iterdir()) if p.is_file()]
    return {
        "schema": "research.gmi.wp02.independent_adoption_delta_checks/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "PASS_EXACT_BINDINGS_SINGLE_OVERRIDE_AND_SYNTHETIC_ARITHMETIC",
        "sidecar_inputs": before,
        "policy_and_review_bindings_verified": refs,
        "effective_normative_changed_pointers": delta,
        "all_other_policy_values_equal": True,
        "canonical_encoding": "UTF-8 JSON; ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False; no terminal newline",
        "base_policy_canonical_content": canonical_binding(base),
        "effective_policy_canonical_content": canonical_binding(effective),
        "canonical_digest_scope": "Recomputed policy content identity only, not original raw bytes, owner authentication, adoption signature or source admission",
        "all_three_adopted_meanings_match_v2": True,
        "quotas_dates_seed_difficult_case_law_unchanged": True,
        "unconditional_real_source_holds_preserved": True,
        "sol_ceo_architectural_adjudication_claimed": False,
        "synthetic_numeric_control": {
            "negative_delta_cap": str(signed), "incorrect_abs_delta_cap": str(erroneous),
            "zero_delta_cap": str(unchanged), "negative_delta_preserves_sign": True,
            "zero_evidenced_no_change_source_verified": False,
            "actual_numeric_parser_or_kernel_tested": False
        },
        "source_files_changed": False,
        "real_source_authority_rights_or_history_verified": False,
        "native_Git_application_provider_capture_effects": False
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
