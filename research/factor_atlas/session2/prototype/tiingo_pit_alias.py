"""S2 consumer-side PIT-boundary audit of ORIGINAL Data OS selected alias rows.

No file access; no alias lookup, id minting, vendor-symbol selection, source
admission or rights decision. Caller must provide already selected alias rows
from the incumbent Data OS owner. A binding hash is a consistency check, NOT
a source-custody signature or proof of actual historical data availability.

The original Data OS VendorAliasTable is the canonical historical naming
resolver. The current general-vendor resolver does NOT promise to enforce
alias known_at for Tiingo; this downstream as-observed reviewer demands it.
"""
from __future__ import annotations

from collections.abc import Iterable,Mapping
from dataclasses import dataclass
from datetime import date,datetime,timedelta,timezone
from hashlib import sha256
import json
import re

import pressure as m

_HEX=re.compile(r"^[0-9a-f]{64}$")
_SECURITY=re.compile(r"^SEC:[A-Z]{2}-[A-Z0-9]{4}-[A-Z0-9][A-Z0-9.\-]*$")
_SYMBOL=re.compile(r"^[A-Z][A-Z0-9._\-]{0,35}$")


@dataclass(frozen=True)
class TiingoPITAliasReview:
    schema: str
    status: str
    required_symbols: tuple[str,...]
    event_date: str
    decision_cutoff_utc: str
    incumbent_identity_snapshot_ref: str
    missing_tiingo_symbols: tuple[str,...]
    selected_candidate_symbols: tuple[str,...]
    candidate_security_ids: tuple[str,...]
    missing_known_at_symbols: tuple[str,...]
    missing_valid_from_symbols: tuple[str,...]
    out_of_validity_symbols: tuple[str,...]
    late_known_symbols: tuple[str,...]
    spylisting_explicitly_unselected: bool
    all_four_temporally_applicable_claims: bool
    pit_vendor_aliases_admitted: bool
    original_owner_identity_authenticated: bool
    source_rights_or_monetary_basis_admitted: bool
    market_pilot_admitted: bool
    may_use_alias_for_trading: bool
    customer_publishable: bool
    knowledge_class: str
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _date(raw: object, name: str) -> date:
    if type(raw) is not str:
        raise ValueError(name+"_date_invalid")
    try:
        result=date.fromisoformat(raw)
        if result.isoformat()!=raw:
            raise ValueError
        return result
    except (ValueError,TypeError):
        raise ValueError(name+"_date_invalid") from None


def _clock(raw: object, name: str) -> datetime:
    if not isinstance(raw,str):
        raise ValueError(name+"_clock_invalid")
    try:
        # Mirror the ORIGINAL Data OS native source-known-at policy:
        # Python truncates fractions beyond 6 places, but a source receipt
        # at 19:59:59.999999001 must not be treated as known at .999999.
        # Only source-known_at is CEILED; decision cutoffs are floored, so
        # neither clock acquires an extra microsecond of foreknowledge.
        fraction=re.search(r"\.(\d+)(?:Z|[+-]\d{2}:\d{2})$",raw)
        beyond=(fraction.group(1)[6:] if fraction else "")
        round_source_up=(name=="alias_known_at" and any(c!="0" for c in beyond))
        parsed=datetime.fromisoformat(raw.replace("Z","+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        if round_source_up:
            parsed+=timedelta(microseconds=1)
        return parsed.astimezone(timezone.utc)
    except (TypeError,ValueError,OverflowError):
        raise ValueError(name+"_clock_invalid") from None


def _hex(raw: object,name: str) -> str:
    if type(raw) is not str or not _HEX.fullmatch(raw):
        raise ValueError(name+"_missing_identity_evidence")
    return raw


def _snapshot_ref(raw: object) -> str:
    if not isinstance(raw,str) or not raw.strip() or len(raw)>512:
        raise ValueError("incumbent_identity_snapshot_ref_invalid")
    return raw


def _binding_digest(row: Mapping,known_at:datetime) -> str:
    """Mirror original Data OS alias_binding_sha256 semantic tuple only.

    Do not invent or select aliases; this checks whether the ORIGINAL
    already-supplied owner selection's self-hash matches its own contents.
    """
    payload={
      "vendor":row["vendor"],"vendor_symbol":row["vendor_symbol"],
      "security_id":row["security_id"],
      "valid_from":row["valid_from"],
      "valid_to":row["valid_to"],
      "known_at":known_at.isoformat(),
      "evidence_sha256":row["evidence_sha256"]
    }
    return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def review_tiingo_pit_aliases(
    selected_owner_alias_rows: Iterable[Mapping], *,
    required_symbols: tuple[str,...]=("AAPL","MSFT","NVDA","SPY"),
    on: str,
    decision_at_utc: str,
    incumbent_identity_snapshot_ref: str
) -> TiingoPITAliasReview:
    """Bounded negative PIT review of *owner-selected* candidate aliases.

    No output can authenticate actual Tiingo Data OS permissions, source
    custody, economic price×share-volume basis or use in trading.
    """
    if (not isinstance(required_symbols,tuple) or len(required_symbols)!=4
        or any(type(s) is not str or not _SYMBOL.fullmatch(s)
               for s in required_symbols)
        or len(set(required_symbols))!=4):
        raise ValueError("required_tiingo_symbols_invalid")
    day=_date(on,"decision_event")
    cutoff=_clock(decision_at_utc,"decision")
    if day>cutoff.date():
        raise ValueError("event_date_after_decision_clock")
    owner_ref=_snapshot_ref(incumbent_identity_snapshot_ref)
    rows=tuple(selected_owner_alias_rows)
    if len(rows)>8:
        raise ValueError("bounded_owner_selection_required")
    selected={}
    security_ids=set()
    documents={}
    missing_known=[];missing_valid=[];out_of_validity=[];late=[]
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise ValueError("owner_selected_alias_mapping_required")
        vendor=raw.get("vendor")
        if vendor!="tiingo":
            raise ValueError("selected_alias_not_tiingo")
        sym=raw.get("vendor_symbol")
        if type(sym) is not str or sym not in required_symbols:
            raise ValueError("selected_alias_outside_pilot")
        if sym in selected:
            raise ValueError("duplicate_owner_selected_alias")
        sid=raw.get("security_id")
        if type(sid) is not str or len(sid)>256 or not _SECURITY.fullmatch(sid):
            raise ValueError("original_security_id_shape_invalid")
        if sid in security_ids:
            raise ValueError("duplicate_security_id")
        security_ids.add(sid)
        evidence=_hex(raw.get("evidence_sha256"),"selected_alias")
        source_from=raw.get("valid_from")
        source_to=raw.get("valid_to")
        source_known=raw.get("known_at")
        if source_from is None:
            missing_valid.append(sym)
            from_date=None
        else:
            from_date=_date(source_from,"valid_from")
        to_date=_date(source_to,"valid_to") if source_to is not None else None
        if from_date is not None and to_date is not None and to_date<=from_date:
            raise ValueError("original_alias_validity_interval_invalid")
        if source_known is None:
            missing_known.append(sym)
            known=None
        else:
            known=_clock(source_known,"alias_known_at")
        if from_date is not None and (day<from_date or
                to_date is not None and day>=to_date):
            out_of_validity.append(sym)
        if known is not None and known>cutoff:
            late.append(sym)
        # When clock/valid-start is missing the original S1 legacy aliases
        # cannot be PIT proven; keep the negative metadata for owner review,
        # but never self-seal a missing value as historical knowledge.
        if known is not None and from_date is not None:
            expected=_binding_digest(raw,known)
            if _hex(raw.get("binding_sha256"),"selected_binding")!=expected:
                raise ValueError("native_alias_binding_mismatch")
        selected[sym]=sid
        documents[sym]={
          "vendor":"tiingo","vendor_symbol":sym,"security_id":sid,
          "valid_from":source_from,"valid_to":source_to,
          "known_at":known.isoformat() if known is not None else None,
          "evidence_sha256":evidence,
          "binding_sha256":raw.get("binding_sha256"),
        }
    missing=tuple(s for s in required_symbols if s not in selected)
    had=tuple(s for s in required_symbols if s in selected)
    missing_known=tuple(s for s in required_symbols if s in missing_known)
    missing_valid=tuple(s for s in required_symbols if s in missing_valid)
    out_of_validity=tuple(s for s in required_symbols if s in out_of_validity)
    late=tuple(s for s in required_symbols if s in late)
    complete=(not missing and not missing_known and not missing_valid and
              not out_of_validity and not late)
    if missing:
        status="NO_SELECTED_TIINGO_ALIASES"
    elif missing_known or missing_valid:
        status="MISSING_ALIAS_TEMPORAL_PROOF"
    elif out_of_validity:
        status="ALIAS_OUTSIDE_HISTORICAL_VALIDITY"
    elif late:
        status="SELECTED_ALIASES_NOT_KNOWN_AT_DECISION"
    else:
        status="OWNER_PIT_CANDIDATES_NOT_AUTHENTICATED"
    fingerprint=m.digest({
       "schema":"factor_atlas.tiingo_pit_alias_owner_review.v1",
       "required":required_symbols,"event_date":day.isoformat(),
       "cutoff":cutoff.isoformat(),"owner_ref":owner_ref,
       "candidates":[documents[s] for s in had],
    })
    return TiingoPITAliasReview(
        "factor_atlas.tiingo_pit_alias_owner_review.v1",
        status,required_symbols,day.isoformat(),cutoff.isoformat(),owner_ref,
        missing,had,tuple(selected[s] for s in had),
        missing_known,missing_valid,out_of_validity,late,
        "SPY" in missing,complete,
        False,False,False,False,False,False,
        "OWNER_SELECTED_ALIAS_SHAPE_NOT_AUTHENTICATED_PIT_OR_DATA_RIGHTS",
        fingerprint)
