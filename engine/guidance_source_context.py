"""Narrow documentary grammar for an explicitly revised total-revenue outlook.

This extracts direction, not a valuation assumption. Unsupported wording stays
unqualified; search snippets and forecasts for other metrics are not substitutes.
"""
from __future__ import annotations

import re
from decimal import Decimal

from bs4 import BeautifulSoup

_MAX_BYTES = 2 * 1024 * 1024
_NUMBER = r"[0-9]{1,12}(?:\.[0-9]{1,8})?"
_SENTENCE = re.compile(
    rf"The company is (?P<verb>raising|lowering) (?P<year>(?:19|20)[0-9]{{2}}) "
    rf"total revenue guidance to \$(?P<new_low>{_NUMBER}) million to "
    rf"\$(?P<new_high>{_NUMBER}) million, or (?P<growth_low>{_NUMBER})% to "
    rf"(?P<growth_high>{_NUMBER})% growth, from prior guidance of "
    rf"\$(?P<old_low>{_NUMBER})(?: million)? to \$(?P<old_high>{_NUMBER}) million, "
    rf"or (?P<old_growth_low>{_NUMBER})% to (?P<old_growth_high>{_NUMBER})% growth\.",
    re.IGNORECASE,
)
_CONTEXT_WARNING = re.compile(
    r"\b(?:if|suppose|assuming|hypothetical|hypothetically|illustrative|example|scenario)\b",
    re.IGNORECASE,
)
_BLOCKS = ("p", "div", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6")


def _answer(reason: str, match=None, quote=None) -> dict:
    return {
        "schema": "guidance_source_context.v1",
        "status": "QUALIFIED" if match else "UNQUALIFIED",
        "metric": "total_revenue" if match else None,
        "direction": ({"raising": "raise", "lowering": "cut"}[match["verb"].lower()]
                      if match else None),
        "fiscal_year": int(match["year"]) if match else None,
        "quote": quote if match else None,
        "reason": reason,
    }


def extract_total_revenue_guidance(content: bytes, expected_direction: str) -> dict:
    """Return only exact, internally consistent, declarative revenue revisions."""
    if (not isinstance(content, bytes) or not content or len(content) > _MAX_BYTES
            or expected_direction not in ("raise", "cut")):
        return _answer("invalid_input")
    try:
        soup = BeautifulSoup(content.decode("utf-8", errors="strict"), "html.parser")
        for node in soup(["script", "style", "noscript", "blockquote", "q", "pre", "code"]):
            node.decompose()
        # Block boundaries must survive: headings are not part of a statement,
        # while inline markup cannot turn a prefixed hypothetical into a fact.
        for node in soup.find_all(_BLOCKS):
            node.insert_before("\x1e")
            node.insert_after("\x1e")
        paragraphs = [" ".join(p.split()) for p in soup.get_text(" ").split("\x1e")]
        paragraphs = [p for p in paragraphs if p]
        found = {}
        for i, paragraph in enumerate(paragraphs):
            # Qualifiers in a preceding heading or in the paragraph apply to
            # its quoted example. No NLP inference may upgrade it to guidance.
            preceding = paragraphs[i - 1] if i else ""
            if _CONTEXT_WARNING.search(paragraph) or (
                    len(preceding) < 160 and _CONTEXT_WARNING.search(preceding)):
                continue
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", paragraph):
                match = _SENTENCE.fullmatch(sentence)
                if match is None:
                    continue
                values = {k: Decimal(match[k]) for k in (
                    "new_low", "new_high", "old_low", "old_high", "growth_low",
                    "growth_high", "old_growth_low", "old_growth_high")}
                if any(values[lo] > values[hi] for lo, hi in (
                        ("new_low", "new_high"), ("old_low", "old_high"),
                        ("growth_low", "growth_high"), ("old_growth_low", "old_growth_high"))):
                    return _answer("unordered_interval")
                direction = "raise" if match["verb"].lower() == "raising" else "cut"
                sign = 1 if direction == "raise" else -1
                if any((values[f"new_{end}"] - values[f"old_{end}"]) * sign <= 0
                       for end in ("low", "high")):
                    return _answer("direction_not_supported_by_both_endpoints")
                if direction != expected_direction:
                    return _answer("direction_mismatch")
                # Repeated SEC exhibit copies are one assertion; unequal
                # intervals or fiscal years in the same document are ambiguous.
                identity = (match["year"], direction, *values.values())
                found.setdefault(identity, (match, sentence))
        if len(found) != 1:
            return _answer("conflicting_revisions" if found else "no_explicit_revenue_revision")
        match, sentence = next(iter(found.values()))
        return _answer("explicit_total_revenue_revision", match, sentence)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        return _answer("malformed_document")
