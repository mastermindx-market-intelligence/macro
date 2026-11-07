"""A34 counterparty resolver: a judged object quote -> an issuer identity.

Pure module: no network, no wall clock, no store.  Inputs are the pinned
``curated_aliases_v1`` / ``resolver_us_issuers_v1`` documents and the universe
manifest's issuer map (:func:`package_v2.load_manifest_issuers`).  A quote is
resolved through exactly four steps, in order:

0. an anonymous alias ("Customer A") is kept as an anonymous counterparty;
1. a bare ambiguous name (hp, ge, general electric, arm) is refused before any
   other step — there is no ticker step, so "HP" never becomes Helmerich & Payne;
2. an exact curated-alias match (issuer target, or a non-edge target);
3. a unique suffix-stripped sec_name match;
4. otherwise UNRESOLVED_COUNTERPARTY.

Nothing here guesses: bare ambiguous names, multiple sec_name matches and
out-of-manifest issuers all come back as named non-edges or refusals.
"""
from __future__ import annotations

import re

from engine.company_intelligence.relationships.harvest import (
    _CORP_SUFFIXES,
    norm_text,
)

#: Bare names that are refused before every other step (K4 step 1): each has
#: collided with an unrelated issuer in practice, and quoting them as written
#: is always safer than guessing.
AMBIGUOUS_NAMES = frozenset({"hp", "ge", "general electric", "arm"})

#: Two-token corporate suffix forms: "L.P." / "N.V." / "S.A." normalize to two
#: tokens ("l p", ...), which the single-token suffix strip cannot remove.
_TWO_TOKEN_SUFFIXES = frozenset({("l", "p"), ("n", "v"), ("s", "a")})

MIN_STRIPPED_CHARS = 3


def norm(text) -> str:
    """lowercase, every run of non-[a-z0-9] -> one space, strip."""
    return norm_text(text) if isinstance(text, str) else ""


def strip_norm(norm_name: str) -> str:
    """Trailing corporate suffixes and a leading "the" removed (K4 step 3)."""
    tokens = norm_name.split()
    while tokens and tokens[0] == "the":
        tokens.pop(0)
    changed = True
    while changed and len(tokens) > 1:
        changed = False
        if tokens[-1] in _CORP_SUFFIXES:
            tokens.pop()
            changed = True
            continue
        if len(tokens) > 2 and (tokens[-2], tokens[-1]) in _TWO_TOKEN_SUFFIXES:
            del tokens[-2:]
            changed = True
    return " ".join(tokens)


def resolve_counterparty(
    quote: str,
    *,
    kind: str,
    subject_issuer_id,
    aliases,
    resolver_rows,
    manifest_issuers,
) -> dict:
    """Resolve one judged object quote; never raises.

    Returns a dict with keys ``issuer_id`` (str|None), ``name_as_filed``
    (str|None), ``anonymous_alias`` (str|None), ``non_edge_reason``
    (str|None), ``note`` (str|None — ``ambiguous_bare_name`` /
    ``multiple_sec_name_matches``) and ``refusal`` (str|None —
    ``ALIAS_TARGET_NOT_IN_RESOLVER`` / ``SELF_REFERENCE``).  Exactly one of
    ``issuer_id`` / ``non_edge_reason`` is set unless a ``refusal`` is present.
    """
    #: the display form keeps the quote's case and punctuation: name_as_filed
    #: is the quote exactly as written, only whitespace-collapsed (K4).
    display = " ".join(str(quote).split())
    normalized = norm(quote)
    result = {
        "issuer_id": None,
        "name_as_filed": None,
        "anonymous_alias": None,
        "non_edge_reason": None,
        "note": None,
        "refusal": None,
    }
    if kind == "anonymous_alias":
        result["anonymous_alias"] = display
        result["non_edge_reason"] = "ANONYMOUS_ALIAS"
        return result

    def _unresolved(note=None):
        result["name_as_filed"] = display
        result["non_edge_reason"] = "UNRESOLVED_COUNTERPARTY"
        result["note"] = note
        return result

    # 1. bare ambiguous names refuse before every other step
    if normalized in AMBIGUOUS_NAMES:
        return _unresolved("ambiguous_bare_name")

    # 2. exact curated-alias match
    alias_matches = [a for a in aliases if norm(a.get("alias_norm")) == normalized]
    if alias_matches:
        target = alias_matches[0]
        issuer_id = target.get("issuer_id")
        if issuer_id is None:
            result["name_as_filed"] = display
            result["non_edge_reason"] = target.get("non_edge_reason") or (
                "UNRESOLVED_COUNTERPARTY"
            )
            return result
        if not any(row.get("issuer_id") == issuer_id for row in resolver_rows):
            result["name_as_filed"] = display
            result["refusal"] = "ALIAS_TARGET_NOT_IN_RESOLVER"
            return result
        return _issuer(result, issuer_id, display, subject_issuer_id,
                           manifest_issuers)

    # 3. unique suffix-stripped sec_name match (no ticker step exists)
    stripped_quote = strip_norm(normalized)
    if len(stripped_quote) >= MIN_STRIPPED_CHARS:
        by_issuer: dict = {}
        for row in resolver_rows:
            sec_name = row.get("sec_name")
            if not sec_name:
                continue
            if strip_norm(norm(sec_name)) == stripped_quote:
                by_issuer[row["issuer_id"]] = row
        if len(by_issuer) > 1:
            return _unresolved("multiple_sec_name_matches")
        if len(by_issuer) == 1:
            issuer_id = next(iter(by_issuer))
            return _issuer(result, issuer_id, display, subject_issuer_id,
                           manifest_issuers)

    # 4. unresolved
    return _unresolved()


def _issuer(result, issuer_id, display, subject_issuer_id, manifest_issuers):
    if issuer_id == subject_issuer_id:
        result["name_as_filed"] = display
        result["refusal"] = "SELF_REFERENCE"
        return result
    if issuer_id not in (manifest_issuers or {}):
        result["name_as_filed"] = display
        result["non_edge_reason"] = "OUT_OF_CORE_MARKET"
        return result
    result["issuer_id"] = issuer_id
    result["name_as_filed"] = display
    return result
