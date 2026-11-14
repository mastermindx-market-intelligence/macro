"""Bounded provenance handoff from Content Studio's writer to the outbox.

The writer is licensed by deterministic chart/market/filing facts, but its
context is otherwise ephemeral.  Capture that *input* before the model writes;
never derive a whitelist by scraping numbers from the model's final copy.

This packet records what the writer knew, not an independent claim that every
source is fresh or that a sentence is true.  The approval and publish-time
gates retain their own freshness, target and market-verification duties.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

WRITER_PACKET_PRODUCER = "content_studio.writer_context.v1"
_MAX_FACTS = 48
_MAX_TOKENS = 128
_MAX_BYTES = 16_384
_MAX_FACT_TEXT = 360
_MAX_NUMBER_TEXT = 32
_NUMBER_TEXT = re.compile(
    r"[+\-]?(?:\d+(?:\.\d+)?|\.\d+|\d{1,3}(?:,\d{3})+(?:\.\d+)?)(?:[%xXkKmMbB])?\Z"
)


def _valid_day(day: Any) -> bool:
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return False
    try:
        return date.fromisoformat(day).isoformat() == day
    except ValueError:
        return False


def _tokens(values: Any, *, limit: int) -> list[str] | None:
    if not isinstance(values, (list, tuple)) or len(values) > limit:
        return None
    tokens: list[str] = []
    for value in values:
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return None
        token = str(value).strip()
        if (not token or len(token) > _MAX_NUMBER_TEXT
                or not _NUMBER_TEXT.fullmatch(token)):
            return None
        if token not in tokens:
            tokens.append(token)
    return tokens


def valid_writer_packet(packet: Any, *, as_of: str) -> bool:
    """Fail closed for malformed, oversized or mismatched writer provenance."""
    if not isinstance(packet, dict) or not _valid_day(as_of):
        return False
    if (packet.get("producer") != WRITER_PACKET_PRODUCER
            or packet.get("as_of") != as_of):
        return False
    facts = packet.get("facts")
    if not isinstance(facts, list) or not 1 <= len(facts) <= _MAX_FACTS:
        return False
    whitelist = _tokens(packet.get("numbers_whitelist"), limit=_MAX_TOKENS)
    if not whitelist:
        return False
    for fact in facts:
        if not isinstance(fact, dict):
            return False
        if not isinstance(fact.get("id"), str) or len(fact["id"]) > 80:
            return False
        body = fact.get("text")
        if not isinstance(body, str) or not body.strip() or len(body) > _MAX_FACT_TEXT:
            return False
        if _tokens(fact.get("numbers"), limit=32) is None:
            return False
    try:
        return len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) <= _MAX_BYTES
    except (TypeError, ValueError, UnicodeError):
        return False


def capture_writer_packet(ctx: dict, facts: dict | None, *, as_of: str) -> dict | None:
    """Carry verified producer facts and the exact *pre-generation* numeric license.

    An abstract/conceptual post with no source facts gets no fact packet.  A
    plan's forward levels are separately stamped by the outbox, and never
    become a price objective merely because they appear in this whitelist.
    """
    if not isinstance(ctx, dict) or not isinstance(facts, dict):
        return None
    raw_facts = facts.get("facts")
    if not isinstance(raw_facts, list) or not 1 <= len(raw_facts) <= _MAX_FACTS:
        return None
    whitelist = _tokens(ctx.get("numbers_whitelist"), limit=_MAX_TOKENS)
    if not whitelist:
        return None
    clean_facts = []
    for raw in raw_facts:
        if not isinstance(raw, dict):
            return None
        fact_numbers = _tokens(raw.get("numbers") or [], limit=32)
        if fact_numbers is None:
            return None
        clean_facts.append({
            "id": str(raw.get("id") or ""),
            "text": raw.get("text"),
            "numbers": fact_numbers,
        })
    packet = {
        "producer": WRITER_PACKET_PRODUCER,
        "as_of": as_of,
        "facts": clean_facts,
        "numbers_whitelist": whitelist,
    }
    return packet if valid_writer_packet(packet, as_of=as_of) else None
