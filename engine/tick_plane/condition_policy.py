"""Point-in-time Massive equity sale-condition reference and admission policy.

The `/v3/reference/conditions` update rules establish which prints may update
consolidated volume, high/low and open/close. They DO NOT themselves prove
aggressor identity, customer intent or forecast value. This is an owner-supplied
complete REFERENCE snapshot parser, not a new REST collector/condition registry.
No in-chat fake clock, default trade-code guesses or API calls.

Source: https://massive.com/docs/rest/stocks/market-operations/condition-codes
Preserve original response bytes/digest, request ID, receipt, source vintage.
A later snapshot cannot be retroactively treated as available to an earlier
decision even when a condition code and its description appear unchanged.
"""

from __future__ import annotations

import hashlib
import json

from engine.tick_plane.stream_events import FrameContractError, _integer, _text

SCHEMA = "equity.tick_plane.condition_reference/v0"
POLICY_SCHEMA = "equity.tick_plane.trade_condition_admission/v0"
MAX_REFERENCE_BYTES = 2 * 1024 * 1024
MAX_REFERENCE_RECORDS = 512
MAX_TRADE_CONDITIONS = 32
_REQUIRED_RULES = ("updates_volume", "updates_high_low", "updates_open_close")


def parse_condition_reference(*, raw_response_bytes, reference_received_ns,
                              source_receipt_id):
    """Retain exact native reference evidence, with no retrospective policy lift."""
    _integer(reference_received_ns, "reference_received_ns", minimum=1)
    _text(source_receipt_id, "source_receipt_id")
    if (type(raw_response_bytes) is not bytes or
            not 0 < len(raw_response_bytes) <= MAX_REFERENCE_BYTES):
        raise FrameContractError("missing or oversized condition reference bytes")
    try:
        response = json.loads(raw_response_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FrameContractError("invalid UTF-8 condition reference JSON") from exc
    if (not isinstance(response, dict) or response.get("status") != "OK"
            or type(response.get("results")) is not list
            or not 0 < len(response["results"]) <= MAX_REFERENCE_RECORDS
            or type(response.get("request_id")) is not str
            or not response["request_id"].strip()):
        raise FrameContractError("source condition reference is not an attested response")
    if response.get("next_url"):
        raise FrameContractError("condition reference pagination is not complete")
    rules = {}
    for item in response["results"]:
        if type(item) is not dict:
            raise FrameContractError("malformed vendor condition record")
        if item.get("asset_class") != "stocks" or "trade" not in item.get("data_types", []):
            continue
        code = _integer(item.get("id"), "native condition id")
        if item.get("type") not in ("condition", "sale_condition"):
            raise FrameContractError("unsupported native trade-condition type")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise FrameContractError("missing native condition name")
        consolidated = (item.get("update_rules") or {}).get("consolidated")
        if not isinstance(consolidated, dict):
            raise FrameContractError("missing consolidated update rules")
        if any(type(consolidated.get(key)) is not bool for key in _REQUIRED_RULES):
            raise FrameContractError("incomplete or ambiguous consolidated eligibility")
        canonical = {key: consolidated[key] for key in _REQUIRED_RULES}
        prior = rules.get(code)
        if prior is not None and prior != canonical:
            raise FrameContractError("conflicting native condition ID in one reference")
        rules[code] = canonical
    if not rules:
        raise FrameContractError("no qualified stock trade conditions in reference")
    return {
        "schema": SCHEMA, "reference_received_ns": reference_received_ns,
        "source_receipt_id": source_receipt_id,
        "source_request_id": response["request_id"],
        "reference_sha256": hashlib.sha256(raw_response_bytes).hexdigest(),
        "rule_count": len(rules),
        "trade_condition_rules": rules,
        "reference_vintage": "RECEIVED_AT_ONLY_NOT_HISTORICAL_VALIDITY",
        "authority": "SOURCE_CONDITION_CONTEXT_ONLY",
    }


def evaluate_trade_conditions(*, trade_conditions, reference, decision_ns,
                              original_reference_custody_attested):
    """Condition-derived candidate for quote-location analysis, never signed fact.

    Volume-only prints are not eligible for the price-response *proxy*. A vendor
    update_rule alone is insufficient for actual aggressor ground truth; here
    'eligible_for_pressure' denotes eligibility for tentative quote-rule study.
    Explicit empty arrays and unknown codes are UNKNOWN until the source-owner
    separately admits the no-condition default. No arbitrary fallback to True.
    """
    def result(*, eligible, reason, volume=None, price=None, rule_ref=None):
        return {"schema": POLICY_SCHEMA, "eligible_for_pressure": eligible,
                "reason": reason, "volume_eligible": volume,
                "price_stat_eligible": price,
                "conditions_rules_ref": rule_ref,
                "method": "CONSOLIDATED_UPDATES_V0_CONSERVATIVE_PROXY",
                "authority": "OBSERVATIONAL_ONLY"}

    if (not isinstance(reference, dict)
            or reference.get("schema") != SCHEMA
            or not isinstance(reference.get("reference_sha256"), str)
            or len(reference["reference_sha256"]) != 64):
        return result(eligible=None, reason="UNQUALIFIED_REFERENCE")
    if type(decision_ns) is not int or decision_ns < 0:
        return result(eligible=None, reason="INVALID_DECISION_CLOCK")
    if original_reference_custody_attested is not True:
        return result(eligible=None, reason="ORIGINAL_REFERENCE_CUSTODY_UNATTESTED")
    if reference["reference_received_ns"] > decision_ns:
        return result(eligible=None, reason="REFERENCE_NOT_YET_AVAILABLE")
    if not isinstance(trade_conditions, (list, tuple)):
        return result(eligible=None, reason="UNKNOWN_CONDITION_ARRAY")
    if len(trade_conditions) > MAX_TRADE_CONDITIONS or any(
        type(code) is not int or code < 0 for code in trade_conditions
    ):
        return result(eligible=None, reason="INVALID_CONDITION_ARRAY")
    if not trade_conditions:
        return result(eligible=None, reason="EMPTY_ARRAY_NEEDS_NATIVE_DEFAULT_POLICY")
    rule_ref = reference["reference_sha256"]
    definitions = reference.get("trade_condition_rules", {})
    if not isinstance(definitions, dict):
        return result(eligible=None, reason="UNQUALIFIED_REFERENCE")
    looked_up = []
    for code in trade_conditions:
        rule = definitions.get(code)
        if not isinstance(rule, dict) or any(
            type(rule.get(k)) is not bool for k in _REQUIRED_RULES
        ):
            return result(eligible=None, reason="UNKNOWN_OR_INVALID_CONDITION_CODE",
                          rule_ref=rule_ref)
        looked_up.append(rule)
    # CTA/UTP combination policy: when ANY condition prohibits an update,
    # that prohibition overrides other conditions' permissions.
    volume = all(rule["updates_volume"] for rule in looked_up)
    price = all(rule["updates_high_low"] and rule["updates_open_close"]
                for rule in looked_up)
    if not volume:
        return result(eligible=False, reason="CONSOLIDATED_VOLUME_NOT_ELIGIBLE",
                      volume=False, price=price, rule_ref=rule_ref)
    if not price:
        return result(eligible=False, reason="VOLUME_ONLY_OR_NON_PRICE_FORMING",
                      volume=True, price=False, rule_ref=rule_ref)
    return result(eligible=True, reason="CONSERVATIVE_PRICE_FORMING_CANDIDATE",
                  volume=True, price=True, rule_ref=rule_ref)
