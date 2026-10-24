"""Listing venue and foreign-private-issuer facts (SPEC_G0 Rev 2.2 §2.1).

The exchange a common-equity class trades on and the issuer's foreign-private-
issuer status are ISSUER FACTS, not scenario assumptions.  This module owns the
frozen :class:`ListingFact` record, its exact record round trip, and the pure
builder that derives one from explicit SEC-shaped inputs:

* venue — the SEC submissions ``exchanges`` list;
* ``foreign_private_issuer`` — the annual-report form type (20-F/40-F vs 10-K)
  and the registration-form family (F-* vs S-*) over the trailing 24 calendar
  months of filings;
* ``home_country_practice_5635`` — whether the issuer's Form 20-F Item 16G
  disclosure names Rule 5635 and the home-country practice it follows instead.

A missing or disagreeing source gives ``"unknown"`` with a typed reason code;
there is never a default.  The builder is pure: no network, no file read, no
ticker or CIK branch, and ``available_at`` is always the caller's value.  The
record lives here, not on ``CapitalState``: ``issuer_state_contracts`` stays
frozen at the S0 minor and only :class:`EvidenceRef` is reused from it.

Nothing here decides a route, a pool or an exemption; the consumer is
:mod:`engine.capital_structure.capacity`.  No score, rank, sizing, probability
or recommendation is produced.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from engine.capital_structure.issuer_state_contracts import ContractViolation, EvidenceRef

#: Closed venue vocabulary.  ``none`` is reserved for a future qualified
#: delisting source; the builder never emits it.
LISTING_VENUES = ("nasdaq", "nyse", "nyse_american", "otc", "none", "unknown")

#: Exchange-name map, applied after trim, case-insensitively.
_EXCHANGE_VENUES: Mapping[str, str] = {
    "nasdaq": "nasdaq",
    "nyse": "nyse",
    "nyse american": "nyse_american",
    "nyse mkt": "nyse_american",
    "otc": "otc",
}

#: FPI determination, over filings whose ``filed`` date falls in the 24
#: calendar months ending on ``as_of``.  A trailing ``/A`` counts as its base
#: form; every other form (S-8 included) is ignored.
FPI_ANNUAL_FORMS = frozenset({"20-F", "40-F"})
DOMESTIC_ANNUAL_FORMS = frozenset({"10-K"})
FPI_REGISTRATION_FORMS = frozenset({"F-1", "F-3", "F-3ASR", "F-4", "F-10"})
DOMESTIC_REGISTRATION_FORMS = frozenset({"S-1", "S-3", "S-3ASR", "S-4", "S-11"})
FPI_LOOKBACK_MONTHS = 24

#: Typed reason codes, one per unknown axis.
REASON_EXCHANGES_MISSING = "listing_exchanges_missing"
REASON_EXCHANGE_UNMAPPED = "listing_exchange_unmapped"
REASON_EXCHANGES_DISAGREE = "listing_exchanges_disagree"
REASON_FPI_FORMS_ABSENT = "fpi_forms_absent"
REASON_FPI_FORMS_DISAGREE = "fpi_forms_disagree"
REASON_HCP_FPI_UNKNOWN = "home_country_practice_fpi_unknown"
REASON_ITEM_16G_MISSING = "item_16g_missing"
REASON_ITEM_16G_INCONCLUSIVE = "item_16g_inconclusive"

RECORD_KEYS = (
    "venue",
    "foreign_private_issuer",
    "home_country_practice_5635",
    "reasons",
    "evidence",
    "available_at",
    "as_of",
)

_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _member(value: Any, allowed: Sequence[str], field_name: str) -> str:
    _require(isinstance(value, str) and value in allowed, f"{field_name}: {value!r} not in {list(allowed)}")
    return value


def _iso_utc_instant(value: Any, field_name: str) -> str:
    """An ISO-8601 timestamp that carries a UTC offset (``...Z`` or ``+00:00``)."""
    _require(isinstance(value, str) and bool(value), f"{field_name}: ISO-8601 UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"{field_name}: {value!r} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{field_name}: {value!r} carries no timezone")
    offset = parsed.utcoffset()
    _require(offset is not None and offset.total_seconds() == 0, f"{field_name}: {value!r} is not a UTC instant")
    return value


def _iso_day(value: Any, field_name: str) -> str:
    _require(isinstance(value, str) and bool(_ISO_DATE.match(value)), f"{field_name}: ISO date required, got {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ContractViolation(f"{field_name}: {value!r} is not an ISO date") from exc
    return value


def _months_before(day: str, months: int) -> str:
    """The calendar day ``months`` months before ``day`` (``YYYY-MM-DD``)."""
    base = date.fromisoformat(day)
    total = base.year * 12 + (base.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    try:
        shifted = base.replace(year=year, month=month)
    except ValueError:  # a day the target month lacks, e.g. 05-31 -> 03-31
        next_month = month % 12 + 1
        last_day = (date(year + (month == 12), next_month, 1) - timedelta(days=1)).day
        shifted = base.replace(year=year, month=month, day=last_day)
    return shifted.isoformat()


def _base_form(form: str) -> str:
    """The base form of a filing type; a trailing ``/A`` counts as its base."""
    return form[:-2] if form.endswith("/A") else form


@dataclass(frozen=True)
class ListingFact:
    """One issuer's listing venue, FPI status and 5635 home-country practice.

    ``reasons`` carries exactly one typed reason code per ``unknown`` axis,
    sorted.  ``evidence`` names the retained-byte spans each determined axis
    rests on.  ``available_at`` is the caller's instant (the then-known view of
    the fact) and ``as_of`` the ISO date the builder evaluated at; neither is
    ever invented here.
    """

    venue: str
    foreign_private_issuer: bool | str
    home_country_practice_5635: str
    reasons: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    available_at: str = ""
    as_of: str = ""

    def __post_init__(self) -> None:
        _member(self.venue, LISTING_VENUES, "listing.venue")
        _require(
            self.foreign_private_issuer is True or self.foreign_private_issuer is False or (
                isinstance(self.foreign_private_issuer, str)
                and self.foreign_private_issuer == "unknown"
            ),
            f"listing.foreign_private_issuer: {self.foreign_private_issuer!r} is not True, False or 'unknown'",
        )
        _member(self.home_country_practice_5635, ("elected", "not_elected", "unknown"), "listing.home_country_practice_5635")
        object.__setattr__(self, "reasons", tuple(self.reasons))
        for reason in self.reasons:
            _require(isinstance(reason, str) and bool(reason), "listing.reasons: non-empty reason codes required")
        _require(list(self.reasons) == sorted(set(self.reasons)), "listing.reasons: sorted and unique required")
        if self.venue == "unknown":
            _require(
                any(reason.startswith("listing_") for reason in self.reasons),
                "listing.venue: an unknown venue names its reason",
            )
        if self.foreign_private_issuer == "unknown":
            _require(
                any(reason.startswith("fpi_") for reason in self.reasons),
                "listing.foreign_private_issuer: an unknown FPI axis names its reason",
            )
        if self.home_country_practice_5635 == "unknown":
            _require(
                any(reason.startswith(("item_16g_", "home_country_practice_")) for reason in self.reasons),
                "listing.home_country_practice_5635: an unknown practice axis names its reason",
            )
        object.__setattr__(self, "evidence", tuple(self.evidence))
        for item in self.evidence:
            _require(isinstance(item, EvidenceRef), "listing.evidence: EvidenceRef required")
        _iso_utc_instant(self.available_at, "listing.available_at")
        _iso_day(self.as_of, "listing.as_of")
        _require(
            self.available_at[:10] >= self.as_of,
            f"listing.available_at {self.available_at} precedes the day it describes, {self.as_of}",
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "foreign_private_issuer": self.foreign_private_issuer,
            "home_country_practice_5635": self.home_country_practice_5635,
            "reasons": list(self.reasons),
            "evidence": [item.as_record() for item in self.evidence],
            "available_at": self.available_at,
            "as_of": self.as_of,
        }


def listing_fact_from_record(record: Any) -> ListingFact:
    """Reconstruct a :class:`ListingFact` from its exact record, or refuse it.

    The key set is closed: an extra or missing key, a value outside its
    vocabulary, or an ``unknown`` axis without its reason is a
    :class:`ContractViolation`, never a silent default.
    """
    _require(isinstance(record, Mapping), "listing record: mapping required")
    missing = [key for key in RECORD_KEYS if key not in record]
    _require(not missing, f"listing record: missing keys {sorted(missing)}")
    extra = [key for key in record if key not in RECORD_KEYS]
    _require(not extra, f"listing record: unexpected keys {sorted(extra)}")
    evidence = tuple(
        item if isinstance(item, EvidenceRef) else EvidenceRef(
            manifest_id=item["manifest_id"], span_id=item["span_id"], text_sha256=item["text_sha256"],
        )
        for item in record["evidence"]
    )
    return ListingFact(
        venue=record["venue"],
        foreign_private_issuer=record["foreign_private_issuer"],
        home_country_practice_5635=record["home_country_practice_5635"],
        reasons=tuple(record["reasons"]),
        evidence=evidence,
        available_at=record["available_at"],
        as_of=record["as_of"],
    )


def _venue_of(exchanges: Any) -> tuple[str, str | None]:
    """Rule 1: the venue from the SEC submissions ``exchanges`` list."""
    if exchanges is None or (isinstance(exchanges, (list, tuple)) and len(exchanges) == 0):
        return "unknown", REASON_EXCHANGES_MISSING
    _require(isinstance(exchanges, (list, tuple)), "exchanges: a sequence or null is required")
    mapped: set[str] = set()
    for name in exchanges:
        _require(isinstance(name, str), "exchanges: every exchange name must be a string")
        venue = _EXCHANGE_VENUES.get(name.strip().casefold())
        if venue is None:
            return "unknown", REASON_EXCHANGE_UNMAPPED
        mapped.add(venue)
    if len(mapped) == 1:
        return next(iter(mapped)), None
    return "unknown", REASON_EXCHANGES_DISAGREE


def _fpi_of(filings: Any, as_of: str) -> tuple[bool | str, str | None]:
    """Rule 2: the foreign-private-issuer status over the trailing 24 months."""
    window_start = _months_before(as_of, FPI_LOOKBACK_MONTHS)
    fpi_annual = False
    domestic_annual = False
    fpi_registration = False
    domestic_registration = False
    for filing in filings:
        _require(isinstance(filing, Mapping), "filings: every filing must be a mapping")
        form = filing.get("form")
        filed = filing.get("filed")
        _require(isinstance(form, str) and bool(form), "filings: form required")
        _require(isinstance(filed, str) and bool(_ISO_DATE.match(filed)), "filings: an ISO filed date is required")
        if filed > as_of or filed < window_start:
            continue
        base = _base_form(form)
        if base in FPI_ANNUAL_FORMS:
            fpi_annual = True
        elif base in DOMESTIC_ANNUAL_FORMS:
            domestic_annual = True
        elif base in FPI_REGISTRATION_FORMS:
            fpi_registration = True
        elif base in DOMESTIC_REGISTRATION_FORMS:
            domestic_registration = True
        # Every other form — S-8 included — is ignored.
    if fpi_annual and not domestic_annual and not domestic_registration:
        return True, None
    if domestic_annual and not fpi_annual and not fpi_registration:
        return False, None
    if not fpi_annual and not domestic_annual:
        return "unknown", REASON_FPI_FORMS_ABSENT
    return "unknown", REASON_FPI_FORMS_DISAGREE


#: A Rule 5635 reference, capturing its sub-paragraph letter when one is named.
_RULE_5635 = re.compile(r"5635(?:\s*\(([a-z])\))?")
#: A negation inside a clause.
_NEGATION = re.compile(r"\b(not|no|never|neither|nor)\b")


def _normalized_16g(text: str) -> str:
    """Casefolded, hyphen and no-break-space normalized, whitespace-collapsed."""
    for dash in ("\u2010", "\u2011", "-"):
        text = text.replace(dash, " ")
    return " ".join(text.replace("\u00a0", " ").casefold().split())


def _names_5635d(letters: Sequence[str]) -> bool:
    """Whether Rule 5635 references reach 5635(d): the whole rule or ``(d)``."""
    return any(letter in ("", "d") for letter in letters)


def _practice_of(
    fpi: bool | str, item_16g: Any, as_of: str
) -> tuple[str, str | None]:
    """Rule 3: the Rule 5635(d) home-country practice election.

    The Item 16G text is read clause by clause (split on ``.`` and ``;``).  A
    clause naming home country practice elects it for 5635(d) when it also
    names Rule 5635 as a whole or 5635(d), and is not negated.  A negated
    election, or a home-country-practice clause that names no rule while the
    text names 5635(d) elsewhere, is inconclusive.  A then-current Item 16G is
    one filed inside the same 24-month window as the FPI determination.
    """
    if fpi is False:
        return "not_elected", None
    if fpi == "unknown":
        return "unknown", REASON_HCP_FPI_UNKNOWN
    if item_16g is None:
        return "unknown", REASON_ITEM_16G_MISSING
    _require(isinstance(item_16g, Mapping), "item_16g: a mapping or null is required")
    filed = item_16g.get("filed")
    _require(isinstance(filed, str) and bool(_ISO_DATE.match(filed)), "item_16g: an ISO filed date is required")
    if filed > as_of or filed < _months_before(as_of, FPI_LOOKBACK_MONTHS):
        return "unknown", REASON_ITEM_16G_MISSING
    text = item_16g.get("text")
    complete = item_16g.get("complete")
    _require(isinstance(text, str) and isinstance(complete, bool), "item_16g: text and complete are required")
    normalized = _normalized_16g(text)
    text_names_5635d = _names_5635d(_RULE_5635.findall(normalized))
    elected = ambiguous = cross = False
    for clause in re.split(r"[.;]", normalized):
        if "home country practice" not in clause:
            continue
        letters = _RULE_5635.findall(clause)
        negated = bool(_NEGATION.search(clause))
        if _names_5635d(letters):
            if negated:
                ambiguous = True
            else:
                elected = True
        elif not letters and not negated and text_names_5635d:
            cross = True
    if ambiguous or cross:
        return "unknown", REASON_ITEM_16G_INCONCLUSIVE
    if elected:
        return ("elected", None) if complete else ("unknown", REASON_ITEM_16G_INCONCLUSIVE)
    if not complete:
        return "unknown", REASON_ITEM_16G_INCONCLUSIVE
    return "not_elected", None


def build_listing_fact(
    *,
    exchanges: Any,
    filings: Any,
    item_16g: Any,
    as_of: str,
    available_at: str,
    evidence: Sequence[EvidenceRef] = (),
) -> ListingFact:
    """Derive a :class:`ListingFact` from explicit records (SPEC_G0 §2.1).

    ``exchanges`` is the SEC submissions ``exchanges`` list or ``None``;
    ``filings`` a sequence of ``{"form": str, "filed": "YYYY-MM-DD"}``;
    ``item_16g`` ``None`` or ``{"text": str, "complete": bool, "filed": "YYYY-MM-DD"}``.
    ``available_at`` is the caller's ISO-8601 UTC instant and is validated, never
    invented.  Every rule is exhaustive: anything not covered gives ``unknown``
    with the named typed reason.
    """
    _iso_day(as_of, "as_of")
    _iso_utc_instant(available_at, "available_at")
    venue, venue_reason = _venue_of(exchanges)
    fpi, fpi_reason = _fpi_of(filings, as_of)
    practice, practice_reason = _practice_of(fpi, item_16g, as_of)
    reasons = tuple(sorted({code for code in (venue_reason, fpi_reason, practice_reason) if code}))
    refs = tuple(evidence)
    for item in refs:
        _require(isinstance(item, EvidenceRef), "evidence: EvidenceRef required")
    return ListingFact(
        venue=venue,
        foreign_private_issuer=fpi,
        home_country_practice_5635=practice,
        reasons=reasons,
        evidence=refs,
        available_at=available_at,
        as_of=as_of,
    )


__all__ = [
    "DOMESTIC_ANNUAL_FORMS",
    "DOMESTIC_REGISTRATION_FORMS",
    "FPI_ANNUAL_FORMS",
    "FPI_LOOKBACK_MONTHS",
    "FPI_REGISTRATION_FORMS",
    "LISTING_VENUES",
    "ListingFact",
    "REASON_EXCHANGES_DISAGREE",
    "REASON_EXCHANGES_MISSING",
    "REASON_EXCHANGE_UNMAPPED",
    "REASON_FPI_FORMS_ABSENT",
    "REASON_FPI_FORMS_DISAGREE",
    "REASON_HCP_FPI_UNKNOWN",
    "REASON_ITEM_16G_INCONCLUSIVE",
    "REASON_ITEM_16G_MISSING",
    "RECORD_KEYS",
    "build_listing_fact",
    "listing_fact_from_record",
]
