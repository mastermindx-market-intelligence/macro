"""Pure validation and saved-source locators for the fitted Brain tool.

Locators confer no authority. The existing saved reader reauthorizes the exact
source on click; neither a URL nor a serialized result can reopen a fitted cap.
"""
import json
import re
from hashlib import sha256

from . import market_memory_brain_citations as baseline

TOOL_NAME = "get_fitted_retained_market_context"
SCHEMA = "brain.retained_fitted_market_context.v2"
MODES = frozenset({"historical_hypothetical", "current_contextual_support"})
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 64 * 1024
MAX_QUERY_BYTES = 1024 * 1024
MAX_LINKS = 9
_REFERENCE_FIELDS = {"operation_id", "intent", "sha256", "bytes"}
_INTENT_FIELDS = {"action", "fit_sha256", "query_id", "generation_id",
                  "generation_sha256", "query_cutoff", "k", "method_spec_id"}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _id(value, prefix):
    return type(value) is str and re.fullmatch(prefix + r"[0-9a-f]{64}", value) is not None


def validate_request(request):
    """Validate an untrusted compact locator; this grants no source access."""
    if (type(request) is not dict or set(request) != {"reference", "mode"}
            or type(request["mode"]) is not str or request["mode"] not in MODES
            or type(request["reference"]) is not dict
            or set(request["reference"]) != _REFERENCE_FIELDS):
        raise ValueError("invalid_fitted_reference_request")
    ref = request["reference"]
    intent = ref["intent"]
    if (type(intent) is not dict or set(intent) != _INTENT_FIELDS
            or intent["action"] != "retained_fitted_query.v2"
            or not _id(ref["operation_id"], "query_")
            or not _id(ref["sha256"], "")
            or type(ref["bytes"]) is not int or not 1 <= ref["bytes"] <= MAX_QUERY_BYTES
            or not _id(intent["fit_sha256"], "")
            or not _id(intent["query_id"], "mmquery_")
            or not _id(intent["generation_id"], "mmgeneration_")
            or not _id(intent["generation_sha256"], "")
            or not _id(intent["method_spec_id"], "mmretainedmethod_")
            or not baseline._is_utc(intent["query_cutoff"])
            or type(intent["k"]) is not int or not 1 <= intent["k"] <= 8
            or ref["operation_id"] != "query_" + sha256(_canonical(intent)).hexdigest()
            or len(_canonical(request)) > MAX_REQUEST_BYTES):
        raise ValueError("invalid_fitted_reference_request")
    return json.loads(_canonical(request))


TOOL_SCHEMA = {
    "name": TOOL_NAME,
    "description": (
        "Reopen an ORIGINAL COMPLETE registered fitted Market Memory query. "
        "Provide its exact compact reference and mode; never invent identifiers "
        "or create a fit/query. Returns original cited house outputs, explicitly "
        "fitted contextual distances and exclusions, without forecast or action authority."
    ),
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["reference", "mode"],
        "properties": {
            "mode": {"type": "string", "enum": sorted(MODES)},
            "reference": {"type": "object", "additionalProperties": False,
                "required": sorted(_REFERENCE_FIELDS), "properties": {
                    "operation_id": {"type": "string", "pattern": "^query_[0-9a-f]{64}$"},
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "bytes": {"type": "integer", "minimum": 1, "maximum": MAX_QUERY_BYTES},
                    "intent": {"type": "object", "additionalProperties": False,
                        "required": sorted(_INTENT_FIELDS), "properties": {
                            "action": {"const": "retained_fitted_query.v2"},
                            "fit_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                            "query_id": {"type": "string", "pattern": "^mmquery_[0-9a-f]{64}$"},
                            "generation_id": {"type": "string", "pattern": "^mmgeneration_[0-9a-f]{64}$"},
                            "generation_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                            "query_cutoff": {"type": "string"},
                            "k": {"type": "integer", "minimum": 1, "maximum": 8},
                            "method_spec_id": {"type": "string", "pattern": "^mmretainedmethod_[0-9a-f]{64}$"},
                        }},
                }},
        },
    },
}


def _uses(messages):
    def field(block, key):
        return block.get(key) if isinstance(block, dict) else getattr(block, key, None)
    # A repeated call id anywhere in this history is ambiguous, including SDK
    # blocks and a copied earlier result. Never recover links from that id.
    all_ids = [field(b, "id") for message in messages
               if isinstance(message, dict) and message.get("role") == "assistant"
               for b in (baseline._block_list(message) or []) if field(b, "type") == "tool_use"]
    for index, message in enumerate(messages):
        blocks = baseline._block_list(message)
        if blocks is None or message.get("role") != "assistant":
            continue
        for block in blocks:
            use_id = field(block, "id")
            if (field(block, "type") == "tool_use" and field(block, "name") == TOOL_NAME
                    and type(use_id) is str and baseline._TOOL_USE_ID_RE.fullmatch(use_id)
                    and all_ids.count(use_id) == 1 and index + 1 < len(messages)):
                yield use_id, field(block, "input"), messages[index + 1]


def _links(request, value):
    spec = validate_request(request)
    ref, mode = spec["reference"], spec["mode"]
    intent = ref["intent"]
    if (type(value) is not dict or value.get("schema") != SCHEMA
            or value.get("available") is not True or value.get("error")
            or value.get("reopen_reference") != ref or value.get("mode") != mode
            or len(_canonical(value)) > MAX_RESPONSE_BYTES):
        return []
    owner, query, method = value["owner"], value["query"], value["method"]
    eligibility = method["eligibility_method_spec"]
    projection = {key: item for key, item in value.items() if key not in ("context_id", "reopen_reference")}
    method_body = {key: item for key, item in method.items() if key != "method_id"}
    if (not _id(owner["subject_id"], "mmsecurity_")
            or not _id(owner["store_id"], "mmstore_")
            or any(owner[key] != intent[key] for key in
                   ("query_id", "generation_id", "generation_sha256", "query_cutoff"))
            or query["context_id"] != owner["context_id"]
            or eligibility["method_spec_id"] != intent["method_spec_id"]
            or eligibility["mode"] != mode or value["requested_k"] != intent["k"]
            or value.get("context_id") != "mmbrainfittedcontext_" + sha256(_canonical(projection)).hexdigest()
            or method["method_id"] != "mmfittedmethod_" + sha256(_canonical(method_body)).hexdigest()
            or not _id(method["normalizer_id"], "mmfittednormalizer_")
            or not _id(method["normalizer_sha256"], "")
            or not _id(value["index_id"], "mmfittedindex_")
            or not _id(value["index_content_sha256"], "")
            or not _id(value["membership_sha256"], "")
            or not _id(value["selection_sha256"], "")
            or value["retrieval_id"] != "mmfittedretrieval_" + value["selection_sha256"]):
        return []
    rows, cards = value["neighbors"], value["source_cards"]
    if (type(rows) is not list or len(rows) > intent["k"] or type(cards) is not list
            or len(cards) != len(rows) + 1 or value["denominator"]["returned"] != len(rows)
            or value["status"] != ("MATCHES" if rows else "ABSTAINED")):
        return []
    refs = [{**query, "query_id": owner["query_id"]}, *rows]
    contexts = [row["context_id"] for row in refs]
    if len(contexts) != len(set(contexts)):
        return []
    links = []
    for index, (row, card) in enumerate(zip(refs, cards, strict=True)):
        if (not _id(row["query_id"], "mmquery_")
                or not _id(row["packet_sha256"], "")
                or not baseline._card_is_citable(card, owner, contexts[1:])
                or card["role"] != ("query" if index == 0 else "selected_neighbor")
                or any(card[key] != row[key] for key in ("context_id", "capture_id", "packet_sha256"))
                or any(not baseline._utc_leq(clock, owner["query_cutoff"])
                       for clock in card["clocks"].values())):
            return []
        pairs = (("mm_mode", "saved"), ("mm_query", row["query_id"]),
                 ("mm_subject", owner["subject_id"]), ("mm_gen", owner["generation_id"]),
                 ("mm_gen_sha", owner["generation_sha256"]), ("mm_cutoff", owner["query_cutoff"]),
                 ("mm_context", row["context_id"]), ("mm_source_context", row["context_id"]))
        links.append(baseline.BASE_URL + "?" + "&".join(key + "=" + val for key, val in pairs))
    return links


def fitted_source_citations(messages):
    """Strict real-tool association; malformed, ambiguous or refused => no links."""
    if type(messages) is not list:
        return []
    links = []
    try:
        for use_id, request, following in _uses(messages):
            try:
                result = baseline._tool_result_payload(following, use_id)
                links.extend(_links(request, result))
            except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                continue
    except Exception:
        return []
    return list(dict.fromkeys(links))[:MAX_LINKS]
