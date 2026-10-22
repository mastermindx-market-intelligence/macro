"""CN/HK news symbols derived through the incumbent DataOS identity grammar.

No allocation, alias discovery, name matching, or issuer/listing fan-out. Provider
entities must supply a MIC; the news universe supplies the existing security id.
"""
from __future__ import annotations

from lib.dataos.identity import (
    IdentityError, normalize_cn_symbol, normalize_hk_symbol, parse_listing_key,
)

CN_HK_MICS = frozenset({"XSHG", "XSHE", "XBSE", "XHKG"})
_SUFFIX = {"XSHG": "SS", "XSHE": "SZ", "XBSE": "BJ", "XHKG": "HK"}


def cn_hk_news_symbol(symbol: str, mic: str) -> str:
    """Return an exchange-qualified alias, never a newly allocated security id."""
    if not isinstance(symbol, str) or not isinstance(mic, str):
        raise IdentityError("news listing requires a string ticker and MIC")
    mic = mic.strip().upper()
    if mic not in CN_HK_MICS:
        raise IdentityError("unsupported news listing MIC")
    raw = symbol.strip().upper()
    if mic == "XHKG":
        listing = normalize_hk_symbol(raw)
    else:
        # An explicit suffix is checked by the owner; a bare code is qualified
        # with the independently supplied MIC before the same check.
        listing = normalize_cn_symbol(raw if "." in raw else raw + "." + _SUFFIX[mic])
    if listing.mic != mic:
        raise IdentityError("news listing exchange mismatch")
    return listing.code + "." + _SUFFIX[mic]


def cn_hk_news_aliases(symbol: str, mic: str) -> tuple[str, ...]:
    canonical = cn_hk_news_symbol(symbol, mic)
    code = canonical.split(".")[0]
    aliases = {canonical}
    if "." in symbol:
        aliases.add(symbol.strip().upper())
    if mic == "XSHG":
        aliases.add(code + ".SH")
    elif mic == "XHKG":
        # All spellings retain the HK suffix. Bare numeric codes are never aliases.
        aliases.update({str(int(code)) + ".HK", str(int(code)).zfill(4) + ".HK"})
    return tuple(sorted(aliases))


def cn_hk_news_securities(aliases, security_master, *, observed_at):
    """Current news selection from existing master + theme_graph_native aliases.

    This is a present-catalog observation, not historical membership evidence.
    The current alias owner, rather than the inception code, supplies each symbol.
    """
    rows = []
    for security in security_master.rows:
        if security.security_state or not security.listing_key:
            continue
        listing = parse_listing_key(security.listing_key)
        if listing.country not in {"CN", "HK"}:
            continue
        if listing.mic not in CN_HK_MICS or (
            (listing.country == "HK") != (listing.mic == "XHKG")
        ):
            raise IdentityError("news listing country/MIC mismatch")
        symbol = aliases.vendor_symbol_for(
            "theme_graph_native", security.security_id, observed_at.date(),
        )
        if not symbol or "." not in symbol:
            raise IdentityError("CN/HK current news alias unresolved")
        canonical = cn_hk_news_symbol(symbol, listing.mic)
        if aliases.resolve("theme_graph_native", symbol, observed_at.date()) != security.security_id:
            raise IdentityError("CN/HK current news alias ambiguous")
        rows.append({
            "security_id": security.security_id,
            "ticker": canonical,
            "aliases": list(cn_hk_news_aliases(symbol, listing.mic)),
            "valid_from": observed_at.isoformat(),
            "valid_to": None,
            "known_at": observed_at.isoformat(),
            "membership_basis": "current_security_master_observation",
        })
    if not rows:
        raise IdentityError("CN/HK news selection empty")
    return sorted(rows, key=lambda row: row["security_id"])
