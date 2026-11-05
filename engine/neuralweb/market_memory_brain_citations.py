"""Clickable source citations for the real Brain retained-context result.

Pure standard-library transform over an assistant conversation: successful
``get_retained_market_context`` tool calls (matched by tool_use id, tool name
and exact input binding) paired with their immediately following user
``tool_result`` yield same-origin locator links into market_memory.html.

A returned link is a locator that requires reauthorization on click; it is
never authority, never a fetch, and never a claim of scientific validation.
Anything unavailable, mismatched, malformed or hostile yields no links and
this module never raises.
"""

import json
import re
from datetime import datetime, timezone

TOOL_NAME = "get_retained_market_context"
SCHEMA = "brain.retained_market_context.v1"
MODES = {"historical_hypothetical": "historical",
         "current_contextual_support": "current"}
BASE_URL = "https://www.mastermind-x.com/market_memory.html"
CARD_ROLES = frozenset({"query", "selected_neighbor"})
MAX_LINKS = 9  # query card + 8 selected neighbours

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_QUERY_ID_RE = re.compile(r"^mmquery_[0-9a-f]{64}$")
_SUBJECT_ID_RE = re.compile(r"^mmsecurity_[0-9a-f]{64}$")
_GENERATION_ID_RE = re.compile(r"^mmgeneration_[0-9a-f]{64}$")
_METHOD_ID_RE = re.compile(r"^mmretainedmethod_[0-9a-f]{64}$")
_CAPTURE_ID_RE = re.compile(r"^mmcapture_[0-9a-f]{64}$")
_CONTEXT_ID_RE = re.compile(r"^mmctx_[0-9a-f]{64}$")
_TOOL_USE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
# Six required input fields; the incumbent tool also accepts an optional bounded limit.
_INPUT_FIELDS = ("query_id", "subject_id", "generation_id",
                 "generation_sha256", "query_cutoff", "method_spec_id")
_URL_KEYS = ("mm_mode", "mm_query", "mm_subject", "mm_gen", "mm_gen_sha",
             "mm_cutoff", "mm_method", "mm_context", "mm_source_context")
_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")


def _is_sha256(value):
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _is_utc(value):
    """Bounded UTC clock: strict shape, real instant, 2000..2100."""
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        return False
    try:
        moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ"
                                   if "." in value else "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    moment = moment.replace(tzinfo=timezone.utc)
    return 2000 <= moment.year <= 2100


def _utc_leq(value, bound):
    if not _is_utc(value) or not _is_utc(bound):
        return False
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in value else "%Y-%m-%dT%H:%M:%SZ"
    left = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in bound else "%Y-%m-%dT%H:%M:%SZ"
    right = datetime.strptime(bound, fmt).replace(tzinfo=timezone.utc)
    return left <= right


def _block_list(message):
    """Content blocks of a conversation message, or None when not a list."""
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    return content


def _tool_uses(messages):
    """Yield (tool_use_id, tool_input) for this tool's assistant calls."""
    def field(block, name):
        # The live gateway retains provider SDK blocks in resp.content. Tool
        # results are gateway-owned dicts; serializing the entire conversation
        # merely to recover four call fields would change that transport.
        if isinstance(block, dict):
            return block.get(name)
        try:
            return getattr(block, name, None)
        except Exception:
            return None

    for index, message in enumerate(messages):
        blocks = _block_list(message)
        if blocks is None or message.get("role") != "assistant":
            continue
        use_ids = [field(b, "id") for b in blocks if field(b, "type") == "tool_use"]
        for block in blocks:
            if (field(block, "type") != "tool_use"
                    or field(block, "name") != TOOL_NAME):
                continue
            use_id = field(block, "id")
            tool_input = field(block, "input")
            if not isinstance(use_id, str) or not _TOOL_USE_ID_RE.fullmatch(use_id):
                continue
            if not isinstance(tool_input, dict) or use_ids.count(use_id) != 1:
                continue  # ambiguous or malformed binding: no links
            following = messages[index + 1] if index + 1 < len(messages) else None
            yield use_id, tool_input, following


def _tool_result_payload(message, use_id):
    """Payload dict of the matching user tool_result, else None."""
    blocks = _block_list(message)
    if blocks is None or message.get("role") != "user":
        return None
    matches = [b for b in blocks if isinstance(b, dict)
               and b.get("type") == "tool_result" and b.get("tool_use_id") == use_id]
    if len(matches) != 1:
        return None
    for block in matches:
        if block.get("is_error") is True:
            return None
        payload = block.get("content")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return None
        return payload if isinstance(payload, dict) else None
    return None


def _input_matches_owner(tool_input, owner, method_spec):
    """Exact six-field binding of the call input to response owner/spec."""
    if not isinstance(owner, dict) or not isinstance(method_spec, dict):
        return False
    fields = set(tool_input)
    if not set(_INPUT_FIELDS) <= fields or fields - set(_INPUT_FIELDS) - {"limit"}:
        return False
    if "limit" in tool_input and (type(tool_input["limit"]) is not int
                                  or not 1 <= tool_input["limit"] <= 8):
        return False
    if not isinstance(owner.get("context_id"), str) or not _CONTEXT_ID_RE.fullmatch(owner["context_id"]):
        return False
    checks = (
        (_QUERY_ID_RE.fullmatch(str(tool_input.get("query_id") or ""))
         and tool_input.get("query_id") == owner.get("query_id")),
        (_SUBJECT_ID_RE.fullmatch(str(tool_input.get("subject_id") or ""))
         and tool_input.get("subject_id") == owner.get("subject_id")),
        (_GENERATION_ID_RE.fullmatch(str(tool_input.get("generation_id") or ""))
         and tool_input.get("generation_id") == owner.get("generation_id")),
        (_is_sha256(tool_input.get("generation_sha256"))
         and tool_input.get("generation_sha256") == owner.get("generation_sha256")),
        (_is_utc(tool_input.get("query_cutoff"))
         and tool_input.get("query_cutoff") == owner.get("query_cutoff")),
        (_METHOD_ID_RE.fullmatch(str(tool_input.get("method_spec_id") or ""))
         and tool_input.get("method_spec_id") == method_spec.get("method_spec_id")),
    )
    return all(checks)


def _card_is_citable(card, owner, neighbor_context_ids):
    """Bounded ids, clocks, subject, role and context membership."""
    if not isinstance(card, dict):
        return False
    role = card.get("role")
    context_id = card.get("context_id")
    if not isinstance(role, str) or role not in CARD_ROLES:
        return False
    if not isinstance(context_id, str) or not _CONTEXT_ID_RE.fullmatch(context_id):
        return False
    capture_id = card.get("capture_id")
    if not isinstance(capture_id, str) or not _CAPTURE_ID_RE.fullmatch(capture_id):
        return False
    if card.get("subject_id") != owner.get("subject_id"):
        return False
    if card.get("evidence_basis") != "retained_original_house_output":
        return False
    if role == "query":
        if context_id != owner.get("context_id"):
            return False
    elif context_id not in neighbor_context_ids:
        return False  # context membership: only disclosed neighbours
    clocks = card.get("clocks")
    if not isinstance(clocks, dict):
        return False
    for name in ("captured_at", "knowledge_cutoff", "as_known_at"):
        if not _utc_leq(clocks.get(name), owner.get("query_cutoff")):
            return False
    receipts = card.get("source_receipt_ids")
    if not isinstance(receipts, list) or not receipts:
        return False
    for receipt in receipts:
        if not isinstance(receipt, str) or not re.fullmatch(r"mmsrc_[0-9a-f]{64}", receipt):
            return False
    return True


def _neighbor_context_ids(value):
    ids = []
    if isinstance(value, list):
        for row in value:
            if isinstance(row, dict):
                ids.append(row.get("context_id"))
    return ids


def retained_source_citations(messages):
    """Same-origin locator links for successful retained-context tool calls.

    Returns a deduplicated list of at most 9 URL strings (query card first,
    then selected neighbours in card order). Never raises; any failure,
    unavailability, binding mismatch, spoofed prose or malformed payload
    contributes no links.
    """
    if not isinstance(messages, list):
        return []
    links = []
    for use_id, tool_input, following in _tool_uses(messages):
        payload = _tool_result_payload(following, use_id) if following else None
        if payload is None:
            continue
        if payload.get("schema") != SCHEMA:
            continue
        if payload.get("available") is not True:
            continue
        mode = payload.get("mode")
        if not isinstance(mode, str) or mode not in MODES:
            continue
        owner = payload.get("owner")
        method_spec = payload.get("method_spec")
        if not _input_matches_owner(tool_input, owner, method_spec):
            continue
        if method_spec.get("mode") != mode:
            continue
        if not _is_utc(owner.get("query_cutoff")):
            continue
        neighbor_ids = _neighbor_context_ids(payload.get("neighbors"))
        cards = payload.get("source_cards")
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not _card_is_citable(card, owner, neighbor_ids):
                continue
            query = [
                ("mm_mode", MODES[mode]),
                ("mm_query", owner["query_id"]),
                ("mm_subject", owner["subject_id"]),
                ("mm_gen", owner["generation_id"]),
                ("mm_gen_sha", owner["generation_sha256"]),
                ("mm_cutoff", owner["query_cutoff"]),
                ("mm_method", method_spec["method_spec_id"]),
                ("mm_context", owner["context_id"]),
                ("mm_source_context", card["context_id"]),
            ]
            links.append(BASE_URL + "?" + "&".join(
                name + "=" + str(value) for name, value in query))
    return list(dict.fromkeys(links))[:MAX_LINKS]
