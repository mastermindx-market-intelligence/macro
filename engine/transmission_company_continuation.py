"""TXI W4 Cascade Monitor — affected-company continuation links (MO-J1A).

One bounded consumer projection: every active transmission blast channel carries a
list of company names from the substrate. Each name is a string; we want to
project each one to a Terminal "company research" link, **only if** the
identity is provable through the canonical Data OS artifact. No ticker-equality
fallback, no company-node parsing, no minted ids, no historical alias as
navigation, no theme inference, no ranking/scoring.

The identity law is EXACT and is the only thing the module does:

    security_id      = aliases.resolve(VENDOR, blast_symbol, decision_date)   # None -> NoLink.unresolved
    current_symbol   = aliases.vendor_symbol_for(VENDOR, security_id, decision_date)  # None -> NoLink.no_current_symbol
    require current_symbol == blast_symbol                                    # else NoLink.stale_alias
    require aliases.resolve(VENDOR, current_symbol, decision_date) == security_id  # else NoLink.round_trip_mismatch

The continuation is rendered against the Terminal app at
``TERMINAL_ANALYSIS_URL``. The href carries ONLY ``symbol``, ``page``, ``mo_chain``,
``mo_channel``, ``mo_asof``, ``mo_security_id`` — the routing authority is
``symbol`` (the verified current alias). No source text, no receipts, no JSON.

``enrich_display_chains`` is the page-adapter projection: it walks the
display-subset chains (from engine.transmission_publish.derive_display_subset),
leaves dormant chains alone, and on every other chain builds a per-blast-channel
``companies`` block with linked names (alphabetical), unlinked names
(alphabetical, membership visible, NO CTA), the unevaluable bucket preserved
verbatim, and ``ranked=False``. ``aliases=None`` (artifact unavailable) -> every
non-dormant channel gets ``companies`` with ``linked=[]``, ``unlinked=<all names>``
and ``identity_unavailable=True`` — never an invented link, never a mutated TXI
state. The input dict is never mutated.

This module is PURE — no I/O, no clock, no LLM, no theme. The page template
reads the names and renders UI from them; the build script loads the alias
table and passes it in.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote

from lib.dataos.identity import VendorAliasTable


CONTINUATION_VENDOR = "store"
TERMINAL_ANALYSIS_URL = "https://app.mastermind-x.com/analysis"

_ALLOWED_QUERY_KEYS = frozenset({
    "symbol", "page", "mo_chain", "mo_channel", "mo_asof", "mo_security_id",
})


# ── result types ────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class ContinuationLink:
    """Identity-proved continuation to the Terminal company-research view.

    Carries only what the template + the Terminal consumer need. The href is
    pre-encoded (urllib.parse.quote, safe="") with the EXACT six query keys —
    routing authority is ``symbol`` (the verified current alias)."""

    symbol: str          # the verified current vendor alias
    security_id: str     # canonical SEC:* id, proved through the alias table
    href: str

    def as_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "security_id": self.security_id, "href": self.href}


@dataclass(frozen=True, slots=True)
class NoLink:
    """Typed negative — why the identity proof failed. Never rendered as a link.

    Reasons are the closed enum: unresolved / no_current_symbol / stale_alias /
    round_trip_mismatch. ``symbol`` is the blast ticker (preserved verbatim —
    no minting)."""

    symbol: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "reason": self.reason}


# ── identity proof ──────────────────────────────────────────────────────────
def _build_href(
    *,
    symbol: str,
    security_id: str,
    chain_id: str,
    channel_id: str,
    chain_asof: str,
) -> str:
    """Build the Terminal href with the EXACT six keys (urlencoded).

    ``symbol`` is the routing authority — it must match the verified current
    alias. ``mo_security_id`` is an opaque navigation hint, never an alternate
    key."""
    parts = [
        ("symbol", symbol),
        ("page", "intelligence"),
        ("mo_chain", chain_id),
        ("mo_channel", channel_id),
        ("mo_asof", chain_asof),
        ("mo_security_id", security_id),
    ]
    qs = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in parts)
    return f"{TERMINAL_ANALYSIS_URL}?{qs}"


def continuation_for(
    blast_symbol: str,
    aliases: VendorAliasTable,
    decision_date: date,
    *,
    chain_id: str,
    channel_id: str,
    chain_asof: str,
) -> ContinuationLink | NoLink:
    """Prove a single blast-symbol through the EXACT identity law.

    The order of checks is load-bearing — a blast ticker that is the historical
    alias of a still-listed security (vendor_symbol_for returns the NEW alias,
    not the OLD one we were given) is ``stale_alias``, not ``unresolved``;
    resolving back through the NEW alias must hit the SAME security_id
    (``round_trip_mismatch`` otherwise). No ticker-equality fallback, no
    historical alias as navigation, no theme inference, no ranking."""
    sym = (blast_symbol or "").strip()
    if not sym:
        return NoLink(symbol=blast_symbol or "", reason="unresolved")

    security_id = aliases.resolve(CONTINUATION_VENDOR, sym, decision_date)
    if security_id is None:
        return NoLink(symbol=sym, reason="unresolved")

    current_symbol = aliases.vendor_symbol_for(CONTINUATION_VENDOR, security_id, decision_date)
    if current_symbol is None:
        return NoLink(symbol=sym, reason="no_current_symbol")

    if current_symbol != sym:
        return NoLink(symbol=sym, reason="stale_alias")

    if aliases.resolve(CONTINUATION_VENDOR, current_symbol, decision_date) != security_id:
        return NoLink(symbol=sym, reason="round_trip_mismatch")

    return ContinuationLink(
        symbol=sym,
        security_id=security_id,
        href=_build_href(
            symbol=sym,
            security_id=security_id,
            chain_id=chain_id,
            channel_id=channel_id,
            chain_asof=chain_asof,
        ),
    )


# ── page projection ─────────────────────────────────────────────────────────
_NON_DORMANT_STATES = frozenset({"arming", "propagating", "expressed"})


def _names_in_channel(chan: dict) -> list[str]:
    """Read the names list out of one blast channel. De-duplicated, input order."""
    raw = chan.get("names")
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        sym = entry.strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _unevaluable_count(chan: dict) -> int:
    """Preserve the unevaluable bucket verbatim — a missing field is neither in
    nor out of the blast radius."""
    value = chan.get("unevaluable")
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _project_channel(
    chain_id: str,
    channel_id: str,
    chan: dict,
    aliases: VendorAliasTable | None,
    decision_date: date,
    chain_asof: str,
) -> dict:
    """Project one blast channel to its ``companies`` block."""
    names = _names_in_channel(chan)
    unevaluable = _unevaluable_count(chan)
    channel_label = (chan.get("label") or {}).get("en") or channel_id

    if aliases is None:
        # Identity substrate unavailable — surface the membership as unlinked
        # with an identity_unavailable flag. Never invent links. Never mutate
        # any TXI state.
        return {
            "linked": [],
            "unlinked": sorted(names),
            "n_linked": 0,
            "n_unlinked": len(names),
            "unevaluable": unevaluable,
            "ranked": False,
            "identity_unavailable": True,
            "channel_label": channel_label,
        }

    linked: list[ContinuationLink] = []
    unlinked: list[str] = []
    for sym in names:
        result = continuation_for(
            sym,
            aliases,
            decision_date,
            chain_id=chain_id,
            channel_id=channel_id,
            chain_asof=chain_asof,
        )
        if isinstance(result, ContinuationLink):
            linked.append(result)
        # NoLink: silent — the blast ticker rides the unlinked bucket so the
        # membership is never erased, only its CTA suppressed.

    linked.sort(key=lambda lk: lk.symbol)
    unlinked_sorted = sorted(set(unlinked))
    # ``names`` is already de-duplicated by _names_in_channel; sort the same
    # set so unlinked + linked cover the full union deterministically.
    full_sorted = sorted(set(names))
    seen_linked = {lk.symbol for lk in linked}
    unlinked_sorted = [s for s in full_sorted if s not in seen_linked]

    return {
        "linked": [lk.as_dict() for lk in linked],
        "unlinked": unlinked_sorted,
        "n_linked": len(linked),
        "n_unlinked": len(unlinked_sorted),
        "unevaluable": unevaluable,
        "ranked": False,
        "identity_unavailable": False,
        "channel_label": channel_label,
    }


def enrich_display_chains(
    chains: dict,
    aliases: VendorAliasTable | None,
    decision_date: date,
) -> dict:
    """Walk the display-subset and add a ``companies`` block per non-dormant chain.

    The input dict is NEVER mutated — a new top-level dict + new per-chain dicts
    are emitted. Dormant chains get NO companies key (their blast radius is
    empty by definition; the cascade monitor collapses them to a single
    "Quiet:" line). Non-dormant chains with no blast channels get companies on
    every channel that exists in ch.blast (zero-keyed if none — the order of
    the for-loop naturally skips when blast is empty).

    ``aliases=None`` is the artifact-unavailable path: every non-dormant chain
    gets ``companies`` with ``linked=[]`` and ``unlinked=<all names>``,
    ``identity_unavailable=True``. Never invented links. Names de-duplicated,
    never re-ordered by anything but alphabet.
    """
    if not isinstance(chains, dict):
        return {"chains": []}
    out: dict = {}
    for k, v in chains.items():
        # Copy per-chain dicts we touch; shallow-copy the rest (template never
        # mutates them, but be defensive).
        out[k] = v
    out_chains_in = chains.get("chains")
    if not isinstance(out_chains_in, list):
        return out

    # The TXI display subset keeps the canonical asof under chain_state
    # ``asof`` (string ISO date). enrich_display_chains is called from
    # build_transmission with that date already parsed; the page's render-time
    # ``as_of`` is unrelated.
    chain_asof = ""
    if isinstance(chains.get("asof"), str):
        chain_asof = chains["asof"]

    projected: list[dict] = []
    for chain in out_chains_in:
        if not isinstance(chain, dict):
            projected.append(chain)
            continue
        new_chain = dict(chain)
        state = chain.get("state")
        blast = chain.get("blast") if isinstance(chain.get("blast"), dict) else {}
        if state not in _NON_DORMANT_STATES:
            # Dormant chain: deliberately omit the companies key. The template
            # asserts this with tests.
            projected.append(new_chain)
            continue
        chain_id = str(chain.get("chain") or chain.get("id") or "")
        companies_out: dict[str, dict] = {}
        for channel_id, chan in blast.items():
            if not isinstance(chan, dict):
                continue
            companies_out[str(channel_id)] = _project_channel(
                chain_id=chain_id,
                channel_id=str(channel_id),
                chan=chan,
                aliases=aliases,
                decision_date=decision_date,
                chain_asof=chain_asof,
            )
        if companies_out:
            new_chain["companies"] = companies_out
        projected.append(new_chain)

    out["chains"] = projected
    return out