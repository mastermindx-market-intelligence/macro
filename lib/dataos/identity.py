"""Identity spine — a symbol is NEVER an identity (Data OS §D2).

WHY THIS FILE EXISTS.  ``lib/ticker_aliases.py`` records the incident in its own
docstring: Marsh McLennan changed its NYSE symbol MMC -> MRSH on 2026-01-14
(symbol change only — same listing, same CUSIP, legal name unchanged), Yahoo
migrated the whole history onto MRSH, and the membership's MMC started 404-ing as
"possibly delisted, no price data found".  ``scripts/fetch_basket_extras`` carried
the MMC->MRSH entry while its sibling ``scripts/fetch_basket_ohlcv`` carried only
FI->FISV, so **data/baskets/ohlcv/MMC.parquet came to never exist**: the deep store
skipped Marsh on every run since the store was created (2026-06-19), and for the
seven months after the rename the ``insurance`` basket rendered on 18/19 members and
``us_sector_financials`` on 75/76.  Nothing went red.  The site simply drew one
fewer line.

That is a 7-month silent production loss caused by a two-entry dict living in one
collector and not its sibling.  The repair in that file was the right local repair —
ONE map, imported by every lane.  This module is the general form of it: an identity
that does not move when a symbol moves, and a time-scoped alias table that can answer
"what did this vendor call this security on that date" instead of "what does it call
it now".

THE SHAPES (§D2), and why each is what it is:

    Issuer    ``ISS:<inception listing key>``   ISS:US-XNYS-MMC
    Security  ``SEC:<inception listing key>``   SEC:US-XNYS-MMC
    Listing   ``<CC>-<MIC>-<CODE>``  (bare)     US-XNYS-MMC
    Symbol    a plain string, venue+time scoped MRSH today, MMC before 2026-01-14
    Vendor id an alias ROW, never a key         yahoo:MRSH

* Bare ``<CC>-<MIC>-<CODE>`` is **already in production** for the China estate
  (``CN-XSHG-600519``, ``CN-XSHE-000001``, ``CN-XBSE-920163``, per
  ``research/CN_TUSHARE_FULL_A_SPINE_CONTRACT_2026-08-08.md``).  Adopting it
  unchanged means zero migration there.
* The two genuinely-new and easily-conflated concepts (issuer, security) carry a
  VISIBLE type prefix, so a grep, a parquet dump or a log line tells you which
  concept you are holding.  Type-visibility is what makes misuse hard, which is the
  whole point.
* ``<CODE>`` is the code the listing carried **at inception**, never the current one.
  That is what makes the id survive the exact event that motivates the project:
  Marsh stays ``US-XNYS-MMC`` after MMC->MRSH; Fiserv stays ``US-XNAS-FISV`` after
  FISV->FI.
* **No allocator, no counter, no hash.**  Two parallel sessions minting the same
  security independently produce the SAME id.  This repo routinely runs 20+
  concurrent worktrees; a sequential counter would be a permanent merge-conflict
  surface.
* Ticker reuse on the same venue after a delisting is the one collision case:
  disambiguate explicitly with a ``.2`` suffix (``US-XNYS-MMC.2``).  Rare, greppable,
  never silent.

MINT ONCE AND STORE.  The derivation here is the *allocator*; the value written into
the master is the *authority*.  A later correction to inception facts never re-mints —
it appends an alias row.  This mirrors the CN spine's generation-atomic pointer
promotion and satisfies ``DNR:LAW-RUN-CLOCK-IN-CONTENT-IDENTITY`` (no run clock ever
enters identity).

STDLIB ONLY.  Imported by thin CI lanes and by collectors that must not pay a pandas
import to translate a ticker.
"""
from __future__ import annotations

import re
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum

__all__ = [
    "IdentityError",
    "BATS", "XNYS", "XNAS", "XASE", "ARCX", "XSHG", "XSHE", "XBSE", "XHKG", "XTSE", "XTSX",
    "KNOWN_MICS",
    "ListingKey",
    "parse_listing_key",
    "security_id",
    "issuer_id",
    "listing_id",
    "parse_id",
    "option_contract_id",
    "parse_option_contract_id",
    "future_id",
    "parse_future_id",
    "index_id",
    "parse_index_id",
    "fx_id",
    "parse_fx_id",
    "CNBoard",
    "cn_board",
    "is_legacy_bse_code",
    "normalize_cn_symbol",
    "normalize_hk_symbol",
    "AliasRow",
    "VendorAliasTable",
    "AliasResolution", "ReferenceReadReceipt", "ReferenceSnapshot",
    "validate_reference_snapshot",
    "SecurityIssuerRow",
    "IssuerMaster",
]


class IdentityError(ValueError):
    """A string that cannot be a lawful identity.

    Deliberately a ``ValueError`` subclass: every raise site here is "you handed me
    a malformed id", and callers that already guard parsing with ``except
    ValueError`` keep working.  It is a raise and never a ``None`` return, because a
    silently-degraded identity is the failure class this module exists to end.
    """


# ── MIC (ISO 10383) — the venue authority, §D2 ────────────────────────────────
# Only the venues this repo actually carries.  The list is deliberately CLOSED:
# minting an id on an unknown venue is a decision a human makes once, in a diff,
# not something a normalizer guesses at 03:00 during a nightly.
BATS = "BATS"   # Cboe BZX U.S. Equities Exchange (ISO 10383 segment MIC)
XNYS = "XNYS"   # New York Stock Exchange
XNAS = "XNAS"   # Nasdaq
XASE = "XASE"   # NYSE American (ex-AMEX)
ARCX = "ARCX"   # ISO 10383 NYSE Arca segment; reference-probe admission only
XSHG = "XSHG"   # Shanghai Stock Exchange
XSHE = "XSHE"   # Shenzhen Stock Exchange
XBSE = "XBSE"   # Beijing Stock Exchange
XHKG = "XHKG"   # Hong Kong Exchanges
XTSE = "XTSE"   # Toronto Stock Exchange
XTSX = "XTSX"   # TSX Venture Exchange

KNOWN_MICS: frozenset[str] = frozenset(
    {BATS, XNYS, XNAS, XASE, ARCX, XSHG, XSHE, XBSE, XHKG, XTSE, XTSX}
)

_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
# A listing CODE may carry '.' and '-' (BRK.B, BRK-B): both are real US class
# suffixes.  A '.'-plus-DIGITS tail is the disambiguator and is stripped before
# this pattern is applied, so 'BRK.B' stays one code while 'MMC.2' does not.
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]*$")
_DISAMBIGUATOR_RE = re.compile(r"^(?P<code>.+)\.(?P<n>[0-9]+)$")


@dataclass(frozen=True, slots=True)
class ListingKey:
    """One security on one venue: ``<CC>-<MIC>-<CODE>[.N]``.

    ``code`` is the INCEPTION code, never today's symbol — see the module
    docstring.  ``disambiguator`` is ``None`` for the first listing to ever carry
    this code on this venue, and an integer >= 2 for a later reuse of a retired
    ticker (``US-XNYS-MMC.2``).  ``.1`` is rejected rather than accepted-as-first:
    two spellings of one identity is exactly the ambiguity this type removes.
    """

    country: str
    mic: str
    code: str
    disambiguator: int | None = None

    def __post_init__(self) -> None:
        if not _COUNTRY_RE.match(self.country or ""):
            raise IdentityError(
                f"country must be a 2-letter ISO 3166-1 alpha-2 code, got {self.country!r}"
            )
        if self.mic not in KNOWN_MICS:
            raise IdentityError(
                f"unknown MIC {self.mic!r} — the venue list in lib/dataos/identity.py is "
                f"closed on purpose; add it there with a comment naming the estate that "
                f"needs it. Known: {', '.join(sorted(KNOWN_MICS))}"
            )
        if not _CODE_RE.match(self.code or ""):
            raise IdentityError(
                f"listing code must be uppercase alphanumeric (with '.'/'-' for class "
                f"suffixes), got {self.code!r}"
            )
        if self.disambiguator is not None:
            if isinstance(self.disambiguator, bool) or not isinstance(self.disambiguator, int):
                raise IdentityError(
                    f"disambiguator must be an int >= 2, got {self.disambiguator!r}"
                )
            if self.disambiguator < 2:
                raise IdentityError(
                    "disambiguator starts at 2 — the FIRST listing to carry a code is "
                    f"unsuffixed, so '.{self.disambiguator}' would be a second spelling "
                    "of the same identity"
                )

    def render(self) -> str:
        """The bare listing key: ``US-XNYS-MMC`` / ``US-XNYS-MMC.2``."""
        tail = f".{self.disambiguator}" if self.disambiguator is not None else ""
        return f"{self.country}-{self.mic}-{self.code}{tail}"

    def __str__(self) -> str:  # so an f-string can never print the repr by accident
        return self.render()


def parse_listing_key(text: str) -> ListingKey:
    """``"US-XNYS-MMC.2"`` -> ``ListingKey('US', 'XNYS', 'MMC', 2)``.

    Splits on the FIRST TWO hyphens only: the code itself may contain one
    (``US-XNYS-BRK-B``).  A trailing ``.<digits>`` is the disambiguator; any other
    dotted tail (``BRK.B``) stays part of the code.
    """
    if not isinstance(text, str):
        raise IdentityError(f"listing key must be a string, got {type(text).__name__}")
    raw = text.strip()
    parts = raw.split("-", 2)
    if len(parts) != 3 or not all(parts):
        raise IdentityError(
            f"malformed listing key {text!r} — expected <CC>-<MIC>-<CODE>[.N], "
            "e.g. US-XNYS-MMC or CN-XSHG-600519"
        )
    country, mic, tail = parts
    disambiguator: int | None = None
    m = _DISAMBIGUATOR_RE.match(tail)
    if m:
        tail = m.group("code")
        disambiguator = int(m.group("n"))
    return ListingKey(country.upper(), mic.upper(), tail.upper(), disambiguator)


def _as_listing_key(value: ListingKey | str) -> ListingKey:
    return value if isinstance(value, ListingKey) else parse_listing_key(value)


def listing_id(listing_key: ListingKey | str) -> str:
    """The bare listing id — ``US-XNYS-MMC``.  Deliberately un-prefixed (§D2)."""
    return _as_listing_key(listing_key).render()


def security_id(listing_key: ListingKey | str) -> str:
    """``SEC:US-XNYS-MMC`` — the legal instrument / share class."""
    return f"SEC:{_as_listing_key(listing_key).render()}"


def issuer_id(listing_key: ListingKey | str) -> str:
    """``ISS:US-XNYS-MMC`` — the economic entity behind the security."""
    return f"ISS:{_as_listing_key(listing_key).render()}"


_ID_PREFIXES = {"ISS": "issuer", "SEC": "security"}


def parse_id(text: str) -> tuple[str, ListingKey]:
    """``"SEC:US-XNYS-MMC"`` -> ``("security", ListingKey(...))``.

    ``kind`` is one of ``issuer`` / ``security`` / ``listing``.  Instrument-class
    ids (``OPT:``/``FUT:``/``IDX:``/``FX:``) are NOT listing keys and raise here —
    they have their own parsers, and returning a half-truth for them is how a
    concept confusion gets written to a store.
    """
    if not isinstance(text, str):
        raise IdentityError(f"id must be a string, got {type(text).__name__}")
    raw = text.strip()
    if ":" not in raw:
        return "listing", parse_listing_key(raw)
    prefix, _, rest = raw.partition(":")
    kind = _ID_PREFIXES.get(prefix.upper())
    if kind is None:
        raise IdentityError(
            f"{prefix!r} is not an issuer/security prefix — {raw!r} is not a listing "
            "identity. OPT:/FUT:/IDX:/FX: have their own parsers."
        )
    return kind, parse_listing_key(rest)


# ── Instrument classes (§D2) ──────────────────────────────────────────────────
_RIGHTS = ("C", "P")
_STRIKE_SCALE = Decimal(1000)
_STRIKE_DIGITS = 8
_OPTION_RE = re.compile(
    r"^OPT:(?P<listing>[^:]+):(?P<expiry>[0-9]{8}):(?P<right>[CP]):(?P<strike>[0-9]{8})$"
)
_FUTURE_RE = re.compile(r"^FUT:(?P<mic>[A-Z0-9]{4}):(?P<root>[A-Z0-9]+):(?P<month>[0-9]{6})$")
_INDEX_RE = re.compile(r"^IDX:(?P<provider>[A-Z0-9]+)-(?P<code>[A-Z0-9.]+)$")
_FX_RE = re.compile(r"^FX:(?P<base>[A-Z]{3})(?P<quote>[A-Z]{3})$")


def _strike_decimal(strike: Decimal | str | int) -> Decimal:
    """Coerce a strike to Decimal, REFUSING float.

    ``float`` is rejected rather than converted because a binary float on a strike
    is a correctness bug, not a formatting preference: 250.10 is not representable,
    so ``Decimal(250.10) * 1000`` is 250099.99999999997 and the id silently becomes
    a different contract.  Pass ``Decimal("250.10")`` or the string ``"250.10"``.
    """
    if isinstance(strike, float):
        raise IdentityError(
            "strike must be Decimal/str/int, never float — binary float cannot "
            f"represent most strikes exactly (got {strike!r}); pass Decimal(\"{strike}\")"
        )
    if isinstance(strike, Decimal):
        return strike
    try:
        return Decimal(str(strike).strip())
    except (InvalidOperation, ValueError) as exc:
        raise IdentityError(f"strike {strike!r} is not a decimal number") from exc


def option_contract_id(
    underlying_listing_key: ListingKey | str,
    expiry: date,
    right: str,
    strike: Decimal | str | int,
) -> str:
    """``OPT:US-XNAS-AAPL:20260918:C:00250000`` (§D2).

    Strike is carried as ``strike x 1000``, zero-padded to 8 digits, so a
    tenth-of-a-cent strike is exact and lexical order is numeric order.  The OCC/OSI
    symbol and any vendor contract id are ALIASES of this, never the key.
    """
    lk = _as_listing_key(underlying_listing_key)
    if not isinstance(expiry, date):
        raise IdentityError(f"expiry must be a datetime.date, got {type(expiry).__name__}")
    r = str(right).strip().upper()
    if r not in _RIGHTS:
        raise IdentityError(f"right must be 'C' or 'P', got {right!r}")
    scaled = _strike_decimal(strike) * _STRIKE_SCALE
    if scaled != scaled.to_integral_value():
        raise IdentityError(
            f"strike {strike!r} is finer than a tenth of a cent — x1000 leaves {scaled}, "
            "which this id form cannot carry without rounding"
        )
    units = int(scaled)
    if units <= 0 or units >= 10 ** _STRIKE_DIGITS:
        raise IdentityError(
            f"strike {strike!r} out of range for an {_STRIKE_DIGITS}-digit x1000 field "
            f"(0 < strike < {10 ** _STRIKE_DIGITS / 1000:g})"
        )
    return (
        f"OPT:{lk.render()}:{expiry.strftime('%Y%m%d')}:{r}:{units:0{_STRIKE_DIGITS}d}"
    )


def parse_option_contract_id(text: str) -> tuple[ListingKey, date, str, Decimal]:
    """Inverse of :func:`option_contract_id` -> ``(underlying, expiry, right, strike)``.

    The strike comes back as a ``Decimal`` scaled down by 1000, so
    ``parse(option_contract_id(...))`` round-trips exactly for every strike the
    forward direction accepted.
    """
    if not isinstance(text, str):
        raise IdentityError(f"option id must be a string, got {type(text).__name__}")
    m = _OPTION_RE.match(text.strip())
    if not m:
        raise IdentityError(
            f"malformed option contract id {text!r} — expected "
            "OPT:<listing key>:<YYYYMMDD>:<C|P>:<strike x1000, 8 digits>"
        )
    lk = parse_listing_key(m.group("listing"))
    raw = m.group("expiry")
    try:
        expiry = date(int(raw[0:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError as exc:
        raise IdentityError(f"option id {text!r} carries an impossible expiry {raw!r}") from exc
    strike = Decimal(m.group("strike")) / _STRIKE_SCALE
    return lk, expiry, m.group("right"), strike


def future_id(mic: str, root: str, contract_month: str | date) -> str:
    """``FUT:XCBF:VX:202609`` — venue, root, delivery month (§D2).

    ``contract_month`` is ``"YYYYMM"`` or any ``date`` in that month.  The MIC is
    NOT validated against :data:`KNOWN_MICS`: the futures estate touches venues no
    equity listing here does, and a normalizer that refuses an unfamiliar futures
    venue would block work it has no authority over.
    """
    m = str(mic).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4}", m):
        raise IdentityError(f"future MIC must be 4 alphanumerics, got {mic!r}")
    r = str(root).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]+", r):
        raise IdentityError(f"future root must be alphanumeric, got {root!r}")
    if isinstance(contract_month, date):
        month = contract_month.strftime("%Y%m")
    else:
        month = str(contract_month).strip()
        if not re.fullmatch(r"[0-9]{6}", month) or not 1 <= int(month[4:6]) <= 12:
            raise IdentityError(f"contract month must be YYYYMM, got {contract_month!r}")
    return f"FUT:{m}:{r}:{month}"


def parse_future_id(text: str) -> tuple[str, str, str]:
    """Inverse of :func:`future_id` -> ``(mic, root, "YYYYMM")``."""
    m = _FUTURE_RE.match(str(text).strip())
    if not m or not 1 <= int(m.group("month")[4:6]) <= 12:
        raise IdentityError(
            f"malformed future id {text!r} — expected FUT:<MIC>:<root>:<YYYYMM>"
        )
    return m.group("mic"), m.group("root"), m.group("month")


def index_id(provider: str, code: str) -> str:
    """``IDX:SPDJI-SPX`` — the index PROVIDER is part of the identity (§D2).

    Two providers publish differently-constructed indices under colliding short
    codes; dropping the provider is how "the S&P 500" silently becomes whichever
    vendor answered.
    """
    p = str(provider).strip().upper()
    c = str(code).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]+", p):
        raise IdentityError(f"index provider must be alphanumeric, got {provider!r}")
    if not re.fullmatch(r"[A-Z0-9.]+", c):
        raise IdentityError(f"index code must be alphanumeric, got {code!r}")
    return f"IDX:{p}-{c}"


def parse_index_id(text: str) -> tuple[str, str]:
    """Inverse of :func:`index_id` -> ``(provider, code)``."""
    m = _INDEX_RE.match(str(text).strip())
    if not m:
        raise IdentityError(f"malformed index id {text!r} — expected IDX:<provider>-<code>")
    return m.group("provider"), m.group("code")


def fx_id(base: str, quote: str) -> str:
    """``FX:USDCNH`` — ordered pair, base first (§D2)."""
    b = str(base).strip().upper()
    q = str(quote).strip().upper()
    for label, cur in (("base", b), ("quote", q)):
        if not re.fullmatch(r"[A-Z]{3}", cur):
            raise IdentityError(f"fx {label} must be a 3-letter code, got {cur!r}")
    if b == q:
        raise IdentityError(f"fx pair needs two different currencies, got {b}/{q}")
    return f"FX:{b}{q}"


def parse_fx_id(text: str) -> tuple[str, str]:
    """Inverse of :func:`fx_id` -> ``(base, quote)``."""
    m = _FX_RE.match(str(text).strip())
    if not m:
        raise IdentityError(f"malformed fx id {text!r} — expected FX:<BASE><QUOTE>")
    return m.group("base"), m.group("quote")


# ── China A-share normalization (§D2) ─────────────────────────────────────────
# The REAL divergence measured here: TuShare emits `600519.SH` while the repository
# ticker is `600519.SS` (research/CN_TUSHARE_FULL_A_SPINE_CONTRACT_2026-08-08.md:
# "Repository tickers are 600519.SS, 000001.SZ and 920163.BJ ... stable IDs are
# CN-XSHG-600519, CN-XSHE-000001, CN-XBSE-920163").  Two spellings of one listing,
# one of which is also a legitimate US-vendor suffix, is precisely the class of
# ambiguity that has to die at the boundary rather than inside a join.

class CNBoard(Enum):
    """Which A-share board a code belongs to.

    The ranges are NOT inferred here — they are the spine contract's, verbatim:
    "SH 688/689 is STAR; the official SZ 300000-309999 allocation is ChiNext
    (including the 309800-309999 CDR range); BJ is BSE; other admitted A code
    families are main board."

    ``BSE`` is reachable ONLY from a canonical ``920xxx`` code.  The old BJ families
    are aliases and are refused rather than classified — :func:`is_legacy_bse_code`.
    """

    MAIN = "MAIN"
    STAR = "STAR"
    CHINEXT = "CHINEXT"
    BSE = "BSE"


_CN_SUFFIX_MICS = {
    "SH": XSHG,   # TuShare / exchange spelling
    "SS": XSHG,   # repository ticker + Yahoo spelling — the divergence, §D2
    "SZ": XSHE,
    "BJ": XBSE,
}
_CN_CODE_RE = re.compile(r"^[0-9]{6}$")


def is_legacy_bse_code(code: str) -> bool:
    """Is this a pre-920xxx BJ code family — i.e. an ALIAS, never a canonical key?

    The 4xxxxx / 8xxxxx families (43xxxx, 83xxxx, 87xxxx, 88xxxx and the old
    third-board 40xxxx/42xxxx transfers) are the codes a BSE listing carried before
    the 920xxx allocation.  The spine contract is explicit and says it twice: "Old BJ
    codes remain aliases. Every canonical BSE mapping target must be ``920xxx``", and
    "other admitted A code families are main board"
    (research/CN_TUSHARE_FULL_A_SPINE_CONTRACT_2026-08-08.md:89-92).
    """
    c = str(code).strip()
    return bool(_CN_CODE_RE.match(c)) and c.startswith(("4", "8"))


def _refuse_legacy_bse(code: str, symbol: object = None) -> None:
    """Raise for an alias code.  Called before ANY key is minted from one.

    WHY REFUSE RATHER THAN CLASSIFY.  Returning ``CNBoard.BSE`` here read as harmless
    — the listing really is on the BSE — but it fed ``_cn_mic_from_code`` -> ``XBSE``
    and minted ``CN-XBSE-430047`` as a CANONICAL key.  That is two identities for one
    security: ``SEC:CN-XBSE-920163`` from the canonical feed and
    ``SEC:CN-XBSE-430047`` from a legacy TuShare pull, joining as different securities
    in the security master with neither side visibly wrong.  It is the exact
    duplicate-identity failure this module was written to end, produced by the module.

    This file holds no ``bse_mapping`` table, so it has no authority to resolve the
    alias to its 920xxx target; that is the alias table's job.  Fail closed, which is
    what the rest of the file already does when it is handed two facts it cannot
    reconcile.
    """
    shown = symbol if symbol is not None else code
    raise IdentityError(
        f"{shown!r} is an old BJ code family (4xxxxx/8xxxxx) — those are ALIASES, and "
        "every canonical BSE mapping target must be 920xxx (CN spine contract). This "
        "module has no bse_mapping table and will not mint a canonical key from an "
        "alias; resolve it through the vendor alias table first."
    )


def cn_board(code: str) -> CNBoard:
    """Board for a 6-digit A-share code, per the spine contract's ranges.

    RAISES on an old BJ alias code — see :func:`_refuse_legacy_bse`.  It is not that
    the board is unknown (it is the BSE); it is that answering at all invites the
    caller to key on the code, which is precisely the defect.
    """
    c = str(code).strip()
    if not _CN_CODE_RE.match(c):
        raise IdentityError(f"A-share code must be 6 digits, got {code!r}")
    if c.startswith(("688", "689")):
        return CNBoard.STAR
    if 300000 <= int(c) <= 309999:
        return CNBoard.CHINEXT
    if c.startswith("920"):
        return CNBoard.BSE
    if is_legacy_bse_code(c):
        _refuse_legacy_bse(c)
    return CNBoard.MAIN


def _cn_mic_from_code(code: str) -> str:
    board = cn_board(code)
    if board is CNBoard.STAR:
        return XSHG
    if board is CNBoard.CHINEXT:
        return XSHE
    if board is CNBoard.BSE:
        return XBSE
    if code.startswith(("6", "9")):     # 6xxxxx main board, 900xxx SH B-shares
        return XSHG
    if code.startswith(("0", "2", "3")):  # 00xxxx/30xxxx main board, 200xxx SZ B-shares
        return XSHE
    raise IdentityError(
        f"A-share code {code!r} is in no admitted family (SH 6/9, SZ 0/2/3, BJ 920) — "
        "pass an explicit .SH/.SS/.SZ/.BJ suffix if this is a real listing"
    )


def normalize_cn_symbol(symbol: str) -> ListingKey:
    """Any in-the-wild A-share spelling -> the canonical ``CN-<MIC>-<code>`` key.

    Accepts ``600519.SH`` (TuShare), ``600519.SS`` (repository ticker / Yahoo),
    ``600519`` (bare), ``sh600519`` (EastMoney-style prefix), and the ``.SZ`` /
    ``.BJ`` families, in any case and with surrounding whitespace.

    An explicit venue suffix is CROSS-CHECKED against the code range and a conflict
    RAISES: ``600519.SZ`` is not a Shenzhen listing with a typo, it is two facts that
    cannot both be true, and picking one silently is how a Shanghai tape ends up
    stored under a Shenzhen key.
    """
    if not isinstance(symbol, str):
        raise IdentityError(f"CN symbol must be a string, got {type(symbol).__name__}")
    raw = symbol.strip().upper()
    if not raw:
        raise IdentityError("CN symbol is empty")
    declared: str | None = None
    if "." in raw:
        code, _, suffix = raw.partition(".")
        declared = _CN_SUFFIX_MICS.get(suffix)
        if declared is None:
            raise IdentityError(
                f"unknown A-share venue suffix {suffix!r} in {symbol!r} "
                f"(known: {', '.join(sorted(_CN_SUFFIX_MICS))})"
            )
    elif raw[:2] in _CN_SUFFIX_MICS and len(raw) == 8:
        declared = _CN_SUFFIX_MICS[raw[:2]]
        code = raw[2:]
    else:
        code = raw
    if not _CN_CODE_RE.match(code):
        raise IdentityError(
            f"{symbol!r} does not contain a 6-digit A-share code (got {code!r})"
        )
    # BEFORE the declared-venue fallback below, which trusts an explicit suffix on an
    # unrecognised family.  That trust is right when the VENUE is the doubt and wrong
    # here: `430047.BJ` says "this is on the BSE", which is true and still does not
    # make `430047` a canonical key.
    if is_legacy_bse_code(code):
        _refuse_legacy_bse(code, symbol)
    try:
        inferred = _cn_mic_from_code(code)
    except IdentityError:
        if declared is None:
            raise
        inferred = declared   # unknown family + an explicit venue: trust the caller
    if declared is not None and declared != inferred:
        raise IdentityError(
            f"{symbol!r} declares venue {declared} but code {code} belongs to {inferred} "
            f"({cn_board(code).value} board) — refusing to guess which fact is wrong"
        )
    return ListingKey("CN", inferred, code)


def normalize_hk_symbol(symbol: str) -> ListingKey:
    """``700`` / ``0700`` / ``0700.HK`` / ``00700`` -> ``HK-XHKG-00700``.

    HKEX board lots are quoted under 1-to-5 digit codes depending on the vendor;
    the canonical form is the exchange's own 5-digit zero-padded code, so
    ``normalize_hk_symbol('700') == normalize_hk_symbol('0700.HK')``.
    """
    if not isinstance(symbol, str):
        raise IdentityError(f"HK symbol must be a string, got {type(symbol).__name__}")
    raw = symbol.strip().upper()
    if raw.endswith(".HK"):
        raw = raw[: -len(".HK")]
    raw = raw.strip()
    if not raw.isdigit() or len(raw) > 5:
        raise IdentityError(
            f"HK symbol must be up to 5 digits (optionally '.HK'-suffixed), got {symbol!r}"
        )
    if int(raw) == 0:
        raise IdentityError(f"HK code 0 is not a listing ({symbol!r})")
    return ListingKey("HK", XHKG, raw.zfill(5))


# ── Vendor alias table (§D2) — the translation layer ──────────────────────────
def _as_date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise IdentityError(f"alias validity bound must be an ISO date, got {value!r}") from exc


# Native reference availability is a source-evidence clock, NOT a Radar read
# receipt. Candidate input consumers must additionally bind their actual snapshot
# read by the decision cutoff in the existing input bundle.
NATIVE_REFERENCE_VENDOR = "polygon"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _aware_utc(value: datetime | str | None, name: str) -> datetime:
    if isinstance(value, str):
        try:
            # Accept one explicit ISO grammar so datetime.fromisoformat cannot
            # silently truncate a fractional variant our ceiling did not inspect.
            clock = re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,9}))?(?:Z|[+-]\d{2}:\d{2})",
                value,
            )
            if clock is None:
                raise ValueError("unsupported clock grammar")
            fraction = clock.group(1) or ""
            round_up = name == "known_at" and any(c != "0" for c in fraction[6:])
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if round_up:
                value += timedelta(microseconds=1)
        except (ValueError, OverflowError) as exc:
            raise IdentityError(f"{name}: invalid UTC clock") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IdentityError(f"{name}: explicit aware decision/evidence clock required")
    return value.astimezone(timezone.utc)


def alias_binding_sha256(vendor: str, vendor_symbol: str, security_id_: str,
                         valid_from: date | None, valid_to: date | None,
                         known_at: datetime | str, evidence_sha256: str) -> str:
    """Seal the exact semantic alias tuple and its retained evidence digest."""
    value = {
        "vendor": vendor, "vendor_symbol": vendor_symbol, "security_id": security_id_,
        "valid_from": valid_from.isoformat() if valid_from else None,
        "valid_to": valid_to.isoformat() if valid_to else None,
        "known_at": _aware_utc(known_at, "known_at").isoformat(),
        "evidence_sha256": evidence_sha256,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AliasRow:
    """One ``(vendor, vendor_symbol, security_id)`` binding, valid over a date range.

    ``valid_from`` is INCLUSIVE and ``valid_to`` is EXCLUSIVE — ``valid_to`` is the
    first day the row no longer holds.  An inclusive end would make the changeover
    day ambiguous (two rows valid at once on 2026-01-14, which is exactly the day
    the MMC/MRSH answer has to be unambiguous).  ``None`` on either side is an open
    bound.

    THE DATE IS THE ROW'S OWN CLOCK, AND A VENDOR SPACE DECLARES WHICH CLOCK IT RUNS
    ON.  A DATED row answers HISTORICAL NAMING — "what did this space call the
    security ON that day".  It is NOT a fetch-symbol or store-key resolver, because a
    vendor that renames typically migrates the WHOLE history onto the new name: Yahoo
    serves Marsh's entire tape under ``MRSH`` and ``data/stocks/ECHO.parquet`` holds
    EchoStar's spliced history back to 2008, so a backfill that asked a dated row what
    Yahoo called it in 2020 and then REQUESTED that answer would get "possibly
    delisted, no price data found" — the seven-month ``insurance`` 18/19 outage in a
    new costume.  The CURRENT-CATALOG question ("what string do I use today, for a bar
    of any date") is answered by separate vendor spaces (``yahoo_fetch``/``store``)
    carrying exactly one OPEN-BOUNDED row per security — plus, since 2026-08-28, a
    dated predecessor row when the repo's own stored key changed on a citable day
    (EQR->VMRK, AMENDMENT ruling 9 / m3); historical-mode readers exclude these
    spaces by vendor identity, never by row shape.
    ``config/dataset_registry.yml::reference.vendor_aliases`` names both families,
    and ``scripts/build_security_master.py`` emits them.
    """

    vendor: str
    vendor_symbol: str
    security_id: str
    valid_from: date | None = None
    valid_to: date | None = None
    known_at: datetime | str | None = None
    evidence_sha256: str | None = None
    binding_sha256: str | None = None
    attempt_id: str | None = None
    alias_family_id: str | None = None
    alias_revision_id: str | None = None

    def __post_init__(self) -> None:
        if self.vendor == "listing" or any(v is not None for v in
                (self.attempt_id, self.alias_family_id, self.alias_revision_id)):
            raise IdentityError("revisioned/listing alias requires observation history context")
        if self.vendor != NATIVE_REFERENCE_VENDOR:
            return
        clock = _aware_utc(self.known_at, "known_at")
        object.__setattr__(self, "known_at", clock)
        if self.valid_from is None or isinstance(self.valid_from, datetime):
            raise IdentityError("polygon reference requires a dated valid_from")
        if clock.date() < self.valid_from:
            raise IdentityError("polygon evidence precedes its reference date")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise IdentityError("polygon invalid event-date bounds")
        if not isinstance(self.evidence_sha256, str) or not _SHA256_RE.fullmatch(self.evidence_sha256):
            raise IdentityError("polygon missing evidence digest")
        expected = alias_binding_sha256(self.vendor, self.vendor_symbol, self.security_id,
                                        self.valid_from, self.valid_to, clock,
                                        self.evidence_sha256)
        if self.binding_sha256 != expected:
            raise IdentityError("polygon alias binding seal mismatch")

    def covers(self, on: date, *, decision_at: datetime | str | None = None) -> bool:
        if self.vendor == NATIVE_REFERENCE_VENDOR:
            cutoff = _aware_utc(decision_at, "decision_at")
            if cutoff < self.known_at or on > cutoff.date():
                return False
        if self.valid_from is not None and on < self.valid_from:
            return False
        if self.valid_to is not None and on >= self.valid_to:
            return False
        return True

    def overlaps(self, other: "AliasRow") -> bool:
        lo = max((d for d in (self.valid_from, other.valid_from) if d is not None), default=None)
        hi = min((d for d in (self.valid_to, other.valid_to) if d is not None), default=None)
        return lo is None or hi is None or lo < hi


class VendorAliasTable:
    """Time-scoped vendor-symbol <-> security-id translation.  NO I/O.

    This is the general form of ``lib/ticker_aliases.py``.  That module holds a
    two-entry, Yahoo-only, TIMELESS dict — which is why it can say "MMC means MRSH"
    but cannot say "MMC meant MMC before 2026-01-14".  A backfill that reads history
    through a timeless map re-labels the past, and nothing downstream can see it.

    Both directions are required to be UNAMBIGUOUS in time: constructing a table
    where two rows for one ``(vendor, vendor_symbol)`` — or one
    ``(vendor, security_id)`` — overlap raises, because a translation layer that can
    return either of two answers is not a translation layer.  Loading is from plain
    mappings (:meth:`from_records`); reading a file is the caller's job, so this
    class stays importable in a lane with no filesystem.
    """

    __slots__ = ("_rows", "_observation_state")

    def __init__(self, rows: list[AliasRow] | tuple[AliasRow, ...] = ()) -> None:
        self._observation_state = None
        self._rows: tuple[AliasRow, ...] = tuple(rows)
        self._assert_unambiguous()

    @classmethod
    def from_records(cls, records, *, observation_history=None, original_reference=None,
                     snapshot_contexts=()) -> "VendorAliasTable":
        """Build from a list of dicts (a YAML/JSON payload the caller already read)."""
        if observation_history is not None:
            return _ob_table(cls, records, observation_history, original_reference, snapshot_contexts)
        if original_reference is not None or snapshot_contexts:
            raise IdentityError("observation history required for snapshot context")
        rows: list[AliasRow] = []
        for i, rec in enumerate(records or ()):
            if any(_null_to_none(rec.get(k)) is not None for k in _REVISION_FIELDS):
                raise IdentityError("revisioned alias requires observation history context")
            try:
                rows.append(
                    AliasRow(
                        vendor=str(rec["vendor"]),
                        vendor_symbol=str(rec["vendor_symbol"]),
                        security_id=str(rec["security_id"]),
                        valid_from=_as_date(rec.get("valid_from")),
                        valid_to=_as_date(rec.get("valid_to")),
                        known_at=_null_to_none(rec.get("known_at")),
                        evidence_sha256=_null_to_none(rec.get("evidence_sha256")),
                        binding_sha256=_null_to_none(rec.get("binding_sha256")),
                    )
                )
            except KeyError as exc:
                raise IdentityError(f"alias record {i} is missing {exc.args[0]!r}") from exc
        return cls(rows)

    @property
    def rows(self) -> tuple[AliasRow, ...]:
        if self._observation_state is not None:
            raise IdentityError("observation history requires an explicit eligible view")
        return self._rows

    def _assert_unambiguous(self) -> None:
        for field in ("vendor_symbol", "security_id"):
            buckets: dict[tuple[str, str], list[AliasRow]] = {}
            for row in self._rows:
                buckets.setdefault((row.vendor, getattr(row, field)), []).append(row)
            for (vendor, value), group in buckets.items():
                for i, a in enumerate(group):
                    for b in group[i + 1:]:
                        if a.overlaps(b):
                            raise IdentityError(
                                f"ambiguous alias table: {vendor}/{value} is covered by two "
                                f"overlapping rows ({a.valid_from}..{a.valid_to} and "
                                f"{b.valid_from}..{b.valid_to}) — one of them needs a bound"
                            )

    def resolve(self, vendor: str, vendor_symbol: str, on: date, *,
                decision_at: datetime | str | None = None, snapshot_receipts=()) -> str | None:
        """What security did *vendor* mean by *vendor_symbol* on *on*?  ``None`` = unmapped."""
        if self._observation_state is not None and vendor in _CLOCKED_ALIAS_VENDORS:
            result = self.resolve_binding(vendor, vendor_symbol, on, decision_at=decision_at,
                                          snapshot_receipts=snapshot_receipts)
            return result.security_id if result.status == "BOUND" else None
        if vendor in _CLOCKED_ALIAS_VENDORS:
            _aware_utc(decision_at, "decision_at")
        for row in self._rows:
            if row.vendor == vendor and row.vendor_symbol == vendor_symbol and row.covers(on, decision_at=decision_at):
                return row.security_id
        return None

    def vendor_symbol_for(self, vendor: str, security_id_: str, on: date, *,
                          decision_at: datetime | str | None = None, snapshot_receipts=()) -> str | None:
        """What did *vendor* call *security_id_* on *on*?  ``None`` = the vendor had no name."""
        if self._observation_state is not None and vendor in _CLOCKED_ALIAS_VENDORS:
            result = self.symbol_binding_for(vendor, security_id_, on, decision_at=decision_at,
                                             snapshot_receipts=snapshot_receipts)
            return result.vendor_symbol if result.status == "BOUND" else None
        if vendor in _CLOCKED_ALIAS_VENDORS:
            _aware_utc(decision_at, "decision_at")
        for row in self._rows:
            if row.vendor == vendor and row.security_id == security_id_ and row.covers(on, decision_at=decision_at):
                return row.vendor_symbol
        return None

    @staticmethod
    def legacy_only_records(records):
        """Explicit projection; clocked namespaces never become unsealed legacy rows."""
        out = []
        for record in records:
            _ob_require(type(record) is dict and type(record.get("vendor")) is str,
                        "legacy projection record/vendor")
            if record["vendor"] in _CLOCKED_ALIAS_VENDORS:
                continue
            _ob_require(not any(_null_to_none(record.get(k)) is not None for k in _REVISION_FIELDS),
                        "revision metadata on legacy vendor")
            out.append(dict(record))
        return out

    def resolve_binding(self, vendor: str, vendor_symbol: str, on: date, *,
                        decision_at: datetime | str, snapshot_receipts=()) -> "AliasResolution":
        return _ob_select(self, vendor, vendor_symbol, on, decision_at, snapshot_receipts, False)

    def symbol_binding_for(self, vendor: str, security_id_: str, on: date, *,
                           decision_at: datetime | str, snapshot_receipts=()) -> "AliasResolution":
        return _ob_select(self, vendor, security_id_, on, decision_at, snapshot_receipts, True)



# ── Pure observation history (publication/adapter activation is separate) ──────
_CLOCKED_ALIAS_VENDORS = frozenset({"polygon", "listing"})
_OBSERVATION_SCHEMA = "mastermind.identity_observations.v1"
_ARTIFACT_NAMES = (
    "security_master.parquet", "vendor_aliases.parquet", "issuer_master.parquet",
    "issuer_migrations.parquet", "security_migrations.parquet",
)
_REVISION_FIELDS = ("attempt_id", "alias_family_id", "alias_revision_id")
_REVISION_COLUMNS = frozenset({
    "vendor", "vendor_symbol", "security_id", "valid_from", "valid_to", "ingested_at",
    "known_at", "evidence_sha256", "binding_sha256", *_REVISION_FIELDS,
})
_NATIVE_SCOPE = {"polygon:MU": ("MU", "XNAS", "CS"),
                 "polygon:SPY": ("SPY", "ARCX", "ETF"),
                 "polygon:QQQ": ("QQQ", "XNAS", "ETF"),
                 "polygon:SMH": ("SMH", "XNAS", "ETF")}
_EVIDENCE_COMMON = frozenset({"listing_snapshot", "listing_receipt", "cik_mapping",
                              "mic_evidence", "identity_seams"})
_SOURCE_PATHS = frozenset({"scripts/build_security_master.py", "lib/dataos/identity.py",
                           "config/identity_seams.yml"})
_MIB = 1024 * 1024
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _ob_require(condition, reason):
    if not condition:
        raise IdentityError("identity observations: " + reason)


def _ob_fields(value, names, label):
    _ob_require(type(value) is dict and set(value) == set(names.split()), label + " fields")


def _ob_text(value, label, *, token=False):
    _ob_require(type(value) is str and 0 < len(value) <= 256, label + " string")
    if token:
        _ob_require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}", value) is not None,
                    label + " token")
    return value


def _ob_hash(value, label):
    _ob_require(type(value) is str and _SHA256_RE.fullmatch(value) is not None,
                label + " digest")
    return value


def _ob_ns(value, label):
    _ob_require(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,18}", value) is not None,
                label + " canonical decimal ns")
    number = int(value)
    _ob_require(number <= 2**63 - 1, label + " ns range")
    return number


def _ob_clock(value):
    if type(value) is str:
        match = re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,9}))?(?:Z|[+-]\d{2}:\d{2})",
            value)
        _ob_require(match is not None, "explicit aware decision/evidence clock required")
        if not value.endswith("Z"):
            _ob_require(int(value[-5:-3]) < 24 and int(value[-2:]) < 60,
                        "invalid UTC offset components")
        fraction = (match.group(1) or "").ljust(9, "0")
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, OverflowError) as exc:
            raise IdentityError("identity observations: invalid clock") from exc
        residual = int(fraction[6:])
    else:
        _ob_require(type(value) is datetime, "explicit aware decision/evidence clock required")
        stamp, residual = value, 0
    _ob_require(stamp.tzinfo is not None and stamp.utcoffset() is not None,
                "explicit aware decision/evidence clock required")
    try:
        delta = stamp.astimezone(timezone.utc) - _EPOCH
        return ((delta.days * 86400 + delta.seconds) * 1_000_000_000
                + delta.microseconds * 1000 + residual)
    except (OverflowError, ValueError) as exc:
        raise IdentityError("identity observations: clock range") from exc


def _ob_iso(ns):
    stamp = _EPOCH + timedelta(seconds=ns // 1_000_000_000)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S") + f".{ns % 1_000_000_000:09d}Z"


def _ob_date(value, label, *, nullable=False):
    if nullable and value is None:
        return None
    _ob_require(type(value) is str, label + " date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise IdentityError("identity observations: " + label + " date") from exc
    _ob_require(parsed.isoformat() == value, label + " canonical date")
    return parsed


def _ob_json(value, limit=8 * _MIB):
    # Bound mappings before serialization, including adversarial Python inputs.
    count, byte_count = 0, 0
    def budget(size):
        nonlocal byte_count
        byte_count += size
        _ob_require(byte_count <= limit, "JSON byte bound")
    def visit(item, depth):
        nonlocal count
        count += 1
        _ob_require(count <= 100_000 and depth <= 16, "JSON structural bound")
        kind = type(item)
        if kind is dict:
            budget(2 + max(0, len(item) - 1) + len(item))
            for key, child in item.items():
                _ob_require(type(key) is str, "JSON object key")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            budget(2 + max(0, len(item) - 1))
            for child in item:
                visit(child, depth + 1)
        elif kind is str:
            try:
                size = len(item.encode("utf-8"))
            except UnicodeError as exc:
                raise IdentityError("identity observations: invalid UTF-8") from exc
            _ob_require(size <= 262_144, "JSON string bound")
            budget(len(json.dumps(item, ensure_ascii=True).encode()))
        elif kind is int:
            _ob_require(-(2**63) <= item < 2**63, "JSON integer bound")
            budget(len(str(item)))
        elif kind is float:
            _ob_require(item == item and abs(item) != float("inf"), "finite JSON number")
            budget(len(json.dumps(item)))
        else:
            _ob_require(item is None or kind is bool, "JSON primitive required")
            budget(4 if item is None or item is True else 5)
    visit(value, 0)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode()
    _ob_require(len(encoded) <= limit, "JSON byte bound")
    return encoded


def _ob_load(raw, limit=8 * _MIB, *, record_set=False):
    _ob_require(type(raw) is bytes and len(raw) <= limit, "bounded JSON bytes required")
    def pairs(items):
        result = {}
        for key, value in items:
            _ob_require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def constant(_value):
        raise IdentityError("identity observations: nonfinite JSON constant")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IdentityError("identity observations: unreadable JSON") from exc
    if record_set:
        _ob_records(value)
    else:
        _ob_json(value, limit)
    return value


def _ob_digest(value):
    return hashlib.sha256(_ob_json(value, 9 * _MIB)).hexdigest()


def _ob_seal(value, field):
    _ob_hash(value.get(field), field)
    _ob_require(value[field] == _ob_digest({k: v for k, v in value.items() if k != field}),
                field + " mismatch")


def _ob_records(records):
    _ob_require(type(records) in (list, tuple) and len(records) <= 100_000,
                "bounded record sequence")
    encoded, size = [], 2
    for record in records:
        _ob_require(type(record) is dict, "record object")
        item = _ob_json(record)
        size += len(item) + (1 if encoded else 0)
        _ob_require(size <= 64 * _MIB, "record-set byte bound")
        encoded.append(item)
    encoded.sort()
    _ob_require(len(set(encoded)) == len(encoded), "duplicate semantic record")
    result = b"[" + b",".join(encoded) + b"]"
    _ob_require(len(result) <= 64 * _MIB, "record-set byte bound")
    return result


def _ob_record_digest(records):
    return hashlib.sha256(_ob_records(records)).hexdigest()


def _ob_artifact_hashes(value):
    _ob_require(type(value) is dict and set(value) == set(_ARTIFACT_NAMES),
                "complete artifact hash vector")
    return tuple((name, _ob_hash(value[name], name)) for name in _ARTIFACT_NAMES)


@dataclass(frozen=True, slots=True)
class AliasResolution:
    """A bounded reader result, never a publication or authority receipt."""
    status: str
    vendor: str
    vendor_symbol: str | None = None
    security_id: str | None = None
    attempt_id: str | None = None
    alias_revision_id: str | None = None
    known_at_utc_ns: str | None = None
    receipt_sha256: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceReadReceipt:
    """Externally recorded clock; this pure value never samples or attests time."""
    receipt_sha256: str
    generation_id: str
    artifact_sha256: tuple[tuple[str, str], ...]
    history_prefix_sha256: str
    read_started_at_utc_ns: str
    read_completed_at_utc_ns: str

    @classmethod
    def from_record(cls, record):
        _ob_fields(record, "schema receipt_sha256 generation_id artifact_sha256 "
                   "history_prefix_sha256 read_started_at_utc_ns read_completed_at_utc_ns",
                   "read receipt")
        _ob_require(record["schema"] == "mastermind.identity_read_receipt.v1",
                    "read receipt schema")
        for name in ("receipt_sha256", "generation_id", "history_prefix_sha256"):
            _ob_hash(record[name], name)
        started = _ob_ns(record["read_started_at_utc_ns"], "read start")
        completed = _ob_ns(record["read_completed_at_utc_ns"], "read completion")
        _ob_require(started <= completed, "read clock order")
        return cls(record["receipt_sha256"], record["generation_id"],
                   _ob_artifact_hashes(record["artifact_sha256"]), record["history_prefix_sha256"],
                   record["read_started_at_utc_ns"], record["read_completed_at_utc_ns"])

    def as_record(self):
        _ob_require(type(self.artifact_sha256) is tuple
                    and len(self.artifact_sha256) == len(_ARTIFACT_NAMES), "read artifact vector")
        for pair in self.artifact_sha256:
            _ob_require(type(pair) is tuple and len(pair) == 2
                        and type(pair[0]) is str and type(pair[1]) is str,
                        "read artifact vector entry")
        _ob_require(len({pair[0] for pair in self.artifact_sha256}) == len(_ARTIFACT_NAMES),
                    "duplicate read artifact")
        return {"schema": "mastermind.identity_read_receipt.v1",
                "receipt_sha256": self.receipt_sha256, "generation_id": self.generation_id,
                "artifact_sha256": dict(self.artifact_sha256),
                "history_prefix_sha256": self.history_prefix_sha256,
                "read_started_at_utc_ns": self.read_started_at_utc_ns,
                "read_completed_at_utc_ns": self.read_completed_at_utc_ns}


@dataclass(frozen=True, slots=True)
class ReferenceSnapshot:
    """Sealed bytes/semantic context; parser custody belongs to the file adapter."""
    receipt_bytes: bytes
    artifact_bytes: tuple[tuple[str, bytes], ...]
    alias_json: bytes
    master_json: bytes


def validate_reference_snapshot(receipt_before, artifact_bytes, receipt_after, *,
                                alias_records, master_records):
    """Validate a complete supplied set, without I/O, Parquet decoding or a clock."""
    _ob_require(type(receipt_before) is bytes and receipt_before == receipt_after
                and type(receipt_after) is bytes, "receipt changed during read")
    receipt = _ob_load(receipt_before, 9 * _MIB)
    _ob_require(type(receipt) is dict, "receipt object")
    _ob_require({"publication", "identity_observations", "prospective_reference"} <= set(receipt),
                "snapshot owner context missing")
    pub = receipt["publication"]
    _ob_fields(pub, "schema generation_id predecessor_receipt_sha256 code_version artifacts "
               "history_sha256", "publication")
    _ob_require(pub["schema"] == "mastermind.identity_publication.v1", "publication schema")
    _ob_seal(pub, "generation_id")
    if pub["predecessor_receipt_sha256"] is not None:
        _ob_hash(pub["predecessor_receipt_sha256"], "predecessor receipt")
    _ob_require(type(pub["code_version"]) is str
                and re.fullmatch("[0-9a-f]{40}", pub["code_version"]) is not None, "code version")
    _ob_require(type(artifact_bytes) is dict and set(artifact_bytes) == set(_ARTIFACT_NAMES),
                "complete artifact bytes")
    _ob_require(type(pub["artifacts"]) is dict
                and set(pub["artifacts"]) == set(_ARTIFACT_NAMES), "complete artifact manifest")
    aliases = _ob_records(alias_records)
    master = _ob_records(master_records)
    semantic = {"vendor_aliases.parquet": hashlib.sha256(aliases).hexdigest(),
                "security_master.parquet": hashlib.sha256(master).hexdigest()}
    for name in _ARTIFACT_NAMES:
        entry, raw = pub["artifacts"][name], artifact_bytes[name]
        _ob_fields(entry, "sha256 bytes semantic_sha256", "artifact")
        _ob_require(type(raw) is bytes and len(raw) <= 64 * _MIB, "artifact byte bound")
        _ob_require(type(entry["bytes"]) is int and entry["bytes"] > 0
                    and entry["bytes"] == len(raw), "artifact byte count")
        _ob_hash(entry["sha256"], "artifact")
        _ob_require(entry["sha256"] == hashlib.sha256(raw).hexdigest(), "artifact byte seal")
        _ob_require(entry["semantic_sha256"] == semantic.get(name), "semantic record seal")
    _ob_require(pub["history_sha256"] == _ob_digest(receipt["identity_observations"]),
                "history manifest seal")
    _ob_validate_history(receipt["identity_observations"], receipt["prospective_reference"],
                         json.loads(aliases))
    return ReferenceSnapshot(receipt_before, tuple((n, artifact_bytes[n]) for n in _ARTIFACT_NAMES),
                             aliases, master)


def _ob_validate_history(history, original, records):
    _ob_json(history)
    _ob_fields(history, "schema anchor attempts", "history")
    _ob_require(history["schema"] == _OBSERVATION_SCHEMA, "history schema")
    anchor = history["anchor"]
    _ob_fields(anchor, "schema anchor_id original_reference_sha256 original_native_rows_sha256 "
               "owner_read_completed_at_utc_ns anchor_sha256", "anchor")
    _ob_require(anchor["schema"] == "mastermind.identity_anchor.v1", "anchor schema")
    _ob_seal(anchor, "anchor_sha256")
    _ob_hash(anchor["original_reference_sha256"], "original reference")
    _ob_require(anchor["anchor_id"] == "anchor:" + anchor["original_reference_sha256"],
                "anchor identity")
    _ob_require(type(original) is dict and _ob_digest(original) == anchor["original_reference_sha256"],
                "original reference seal")
    _ob_require(original.get("schema") == "mastermind.prospective_reference.v1",
                "original reference schema")
    clock = _ob_ns(anchor["owner_read_completed_at_utc_ns"], "anchor owner read")
    _ob_require(type(original.get("source_read_completed_at_utc_ns")) is int
                and original["source_read_completed_at_utc_ns"] == clock,
                "original owner clock")
    base, revisioned = [], []
    for row in records:
        metadata = [row.get(k) for k in _REVISION_FIELDS]
        if any(v is not None for v in metadata):
            _ob_fields(row, " ".join(_REVISION_COLUMNS), "revision row")
            for k in _REVISION_FIELDS:
                _ob_text(row[k], k)
            for k in ("vendor", "vendor_symbol", "security_id", "ingested_at", "known_at"):
                _ob_text(row[k], k)
            for k in ("valid_from", "valid_to"):
                _ob_require(row[k] is None or type(row[k]) is str, "row date type")
            for k in ("evidence_sha256", "binding_sha256"):
                _ob_hash(row[k], k)
            _ob_require(row["alias_revision_id"] == row["attempt_id"] + "/" + row["alias_family_id"],
                        "row revision identity")
            expected = _ob_digest({"schema": "mastermind.identity_alias_revision.v1",
                                  **{k: v for k, v in row.items() if k != "binding_sha256"}})
            _ob_require(row["binding_sha256"] == expected, "row binding seal")
            revisioned.append(row)
        else:
            _ob_require(row.get("vendor") != "listing", "listing requires revision context")
            base.append({k: v for k, v in row.items() if k not in _REVISION_FIELDS})
    native = [r for r in base if r.get("vendor") == "polygon"]
    _ob_require(_ob_record_digest(native) == anchor["original_native_rows_sha256"],
                "original native prefix changed")
    probes = original.get("probes")
    _ob_require(type(probes) is dict and set(probes) == {"MU", "SPY", "QQQ", "SMH"},
                "original probes")
    accounted = []
    for symbol, probe in probes.items():
        _ob_require(type(probe) is dict and probe.get("status") in ("BOUND", "REFUSED"),
                    "original disposition")
        _ob_require(probe.get("symbol") == symbol, "original symbol")
        _ob_require(_ob_clock(probe.get("known_at")) >= clock, "original evidence clock")
        _ob_hash(probe.get("evidence_sha256"), "original evidence")
        matches = [r for r in native if r.get("vendor_symbol") == symbol]
        if probe["status"] == "REFUSED":
            _ob_require(not matches, "original refusal has binding rows")
            _ob_text(probe.get("code"), "original refusal reason")
        else:
            _ob_require(len(matches) == 1, "original bound row membership")
            row = matches[0]
            parsed = VendorAliasTable.from_records([row]).rows[0]
            _ob_require(type(row["vendor_symbol"]) is str and type(row["security_id"]) is str,
                        "original native identity strings")
            _ob_require(row["security_id"] == probe.get("security_id")
                        and row["evidence_sha256"] == probe["evidence_sha256"]
                        and row["binding_sha256"] == probe.get("binding_sha256")
                        and _ob_clock(row["known_at"]) == _ob_clock(probe["known_at"]),
                        "original binding evidence mismatch")
            _ob_require(parsed.vendor == "polygon", "original native row")
            accounted.append(row)
    _ob_require(len(accounted) == len(native), "orphan original native row")
    attempts = history["attempts"]
    _ob_require(type(attempts) is list and len(attempts) <= 64, "attempt count bound")
    predecessor, previous_hash = anchor["anchor_id"], anchor["anchor_sha256"]
    by_id = {}
    for sequence, attempt in enumerate(attempts, 1):
        _ob_json(attempt, _MIB)
        _ob_fields(attempt, "schema attempt_id sequence predecessor_attempt_id predecessor_sha256 "
                   "kind scope input_file_sha256 input_sha256 dependencies_sha256 acquisition_sha256 "
                   "owner_read_completed_at_utc_ns row_membership payload attempt_sha256", "attempt")
        _ob_require(attempt["schema"] == "mastermind.identity_attempt_envelope.v1", "envelope schema")
        aid = _ob_text(attempt["attempt_id"], "attempt ID", token=True)
        _ob_require(aid not in by_id, "duplicate attempt ID")
        _ob_require(type(attempt["sequence"]) is int and attempt["sequence"] == sequence,
                    "attempt sequence")
        _ob_require(attempt["predecessor_attempt_id"] == predecessor
                    and attempt["predecessor_sha256"] == previous_hash, "attempt predecessor")
        _ob_text(attempt["kind"], "attempt kind")
        scope = attempt["scope"]
        _ob_require(type(scope) is list and 1 <= len(scope) <= 4, "attempt scope bound")
        for fid in scope:
            _ob_text(fid, "family ID")
        _ob_require(len(set(scope)) == len(scope), "duplicate family scope")
        membership = attempt["row_membership"]
        _ob_require(type(membership) is dict and set(membership) == set(scope),
                    "envelope row membership scope")
        total = 0
        for members in membership.values():
            _ob_require(type(members) is list and len(members) <= 65, "row membership bound")
            for member in members:
                _ob_hash(member, "row membership")
            _ob_require(len(set(members)) == len(members), "duplicate row membership")
            total += len(members)
        _ob_require(total <= 260, "attempt row membership bound")
        for field in ("input_file_sha256", "input_sha256", "dependencies_sha256", "acquisition_sha256"):
            _ob_hash(attempt[field], field)
        now = _ob_ns(attempt["owner_read_completed_at_utc_ns"], "owner read")
        _ob_require(now > clock, "owner clock must strictly increase")
        _ob_seal(attempt, "attempt_sha256")
        by_id[aid] = attempt
        predecessor, previous_hash, clock = aid, attempt["attempt_sha256"], now
    physical = {(a["attempt_id"], fid): [] for a in attempts for fid in a["scope"]}
    for row in revisioned:
        route = (row["attempt_id"], row["alias_family_id"])
        _ob_require(route in physical, "orphan row attempt/scope")
        owner_ns = _ob_ns(by_id[row["attempt_id"]]["owner_read_completed_at_utc_ns"], "owner read")
        _ob_require(row["known_at"] == _ob_iso(owner_ns), "row evidence clock")
        lo = _ob_date(row["valid_from"], "valid_from", nullable=True)
        hi = _ob_date(row["valid_to"], "valid_to", nullable=True)
        _ob_require(lo is None or hi is None or lo < hi, "event interval width")
        physical[route].append(_ob_digest(row))
    # This sealed envelope membership is independent of payload version/semantics.
    for attempt in attempts:
        for fid, members in attempt["row_membership"].items():
            _ob_require(sorted(members) == sorted(physical[(attempt["attempt_id"], fid)]),
                        "missing/duplicate row membership")
    return base


def _ob_table(cls, records, history, original, contexts):
    raw = json.loads(_ob_records(records))
    history = json.loads(_ob_json(history))
    original = json.loads(_ob_json(original))
    base = _ob_validate_history(history, original, raw)
    _ob_require(type(contexts) in (tuple, list) and 1 <= len(contexts) <= 65,
                "snapshot context count 1..65 required")
    normalized = {}
    complete = False
    for context in contexts:
        _ob_require(type(context) is ReferenceSnapshot, "validated snapshot context required")
        _ob_require(type(context.artifact_bytes) is tuple
                    and len(context.artifact_bytes) == len(_ARTIFACT_NAMES), "snapshot artifact vector")
        for pair in context.artifact_bytes:
            _ob_require(type(pair) is tuple and len(pair) == 2
                        and type(pair[0]) is str and type(pair[1]) is bytes,
                        "snapshot artifact vector entry")
        _ob_require(len({pair[0] for pair in context.artifact_bytes}) == len(_ARTIFACT_NAMES),
                    "duplicate snapshot artifact")
        checked = validate_reference_snapshot(
            context.receipt_bytes, dict(context.artifact_bytes), context.receipt_bytes,
            alias_records=_ob_load(context.alias_json, 64 * _MIB, record_set=True),
            master_records=_ob_load(context.master_json, 64 * _MIB, record_set=True))
        receipt = _ob_load(checked.receipt_bytes, 9 * _MIB)
        older = receipt["identity_observations"]
        _ob_require(older["anchor"] == history["anchor"]
                    and receipt["prospective_reference"] == original, "snapshot original context")
        n = len(older["attempts"])
        _ob_require(n <= len(history["attempts"]) and older["attempts"] == history["attempts"][:n],
                    "snapshot changed or truncated prefix")
        if n == len(history["attempts"]) and checked.alias_json == _ob_records(raw):
            complete = True
        normalized[hashlib.sha256(checked.receipt_bytes).hexdigest()] = checked
    _ob_require(complete, "complete current snapshot context required")
    table = cls.from_records(cls.legacy_only_records(base))
    table._observation_state = (_ob_json(history), _ob_json(original), normalized)
    return table


def _ob_initial_families(history, original, records):
    state = {}
    anchor = history["anchor"]
    for fid, (symbol, mic, security_class) in _NATIVE_SCOPE.items():
        probe = original["probes"][symbol]
        rows = [r for r in records if r.get("vendor") == "polygon"
                and r.get("vendor_symbol") == symbol and not r.get("attempt_id")]
        state[fid] = {
            "family_id": fid, "vendor": "polygon", "symbols": [symbol],
            "security_id": probe.get("security_id") if probe["status"] == "BOUND" else None,
            "country": "US", "mic": mic, "security_class": security_class,
            "status": probe["status"], "reason": probe.get("code"),
            "alias_revision_id": anchor["anchor_id"] + "/" + fid,
            "_rows": rows, "_attempt_id": anchor["anchor_id"],
            "_known_at": str(max(_ob_clock(probe["known_at"]),
                                 _ob_ns(anchor["owner_read_completed_at_utc_ns"], "anchor"))),
        }
    return state


def _ob_apply_attempt(state, attempt, records):
    payload = attempt["payload"]
    _ob_fields(payload, "schema dependencies acquisition families", "visible payload")
    _ob_require(payload["schema"] == "mastermind.identity_attempt_payload.v1",
                "visible payload schema unsupported")
    deps, acquisition = payload["dependencies"], payload["acquisition"]
    _ob_fields(deps, "source_commit source_blobs prior_receipt_sha256 artifact_sha256 evidence_sha256", "dependencies")
    _ob_require(type(deps["source_commit"]) is str
                and re.fullmatch("[0-9a-f]{40}", deps["source_commit"]) is not None, "source commit")
    blobs = deps["source_blobs"]
    _ob_require(type(blobs) is dict and set(blobs) == _SOURCE_PATHS, "source blob paths")
    for blob in blobs.values():
        _ob_require(type(blob) is str and re.fullmatch("[0-9a-f]{40}", blob) is not None,
                    "source blob identity")
    _ob_hash(deps["prior_receipt_sha256"], "prior receipt")
    _ob_artifact_hashes(deps["artifact_sha256"])
    evidence = deps["evidence_sha256"]
    kind = attempt["kind"]
    if kind == "NATIVE_REFERENCE":
        roles = ("native_response", "owner_fences")
    elif kind == "SAME_VENUE_RENAME":
        roles = ("listing_binding_spec", "continuity_evidence", "owner_fences")
    else:
        raise IdentityError("identity observations: visible attempt kind unsupported")
    required = _EVIDENCE_COMMON | {fid + "/" + role for fid in attempt["scope"] for role in roles}
    _ob_require(type(evidence) is dict and set(evidence) == required, "dependency evidence roles")
    for key, value in evidence.items():
        _ob_text(key, "dependency key")
        if value is not None:
            _ob_hash(value, "dependency evidence")
    _ob_require(_ob_digest(deps) == attempt["dependencies_sha256"], "dependencies seal")
    _ob_require(type(acquisition) is dict and set(acquisition) == set(attempt["scope"]),
                "shared acquisition custody")
    _ob_require(_ob_digest(acquisition) == attempt["acquisition_sha256"], "acquisition seal")
    kind = attempt["kind"]
    if kind == "NATIVE_REFERENCE":
        _ob_require(set(attempt["scope"]) == set(_NATIVE_SCOPE), "native scope")
        expected_vendor = "polygon"
    elif kind == "SAME_VENUE_RENAME":
        _ob_require(len(attempt["scope"]) == 2
                    and all(fid.startswith("listing:") and re.fullmatch(
                        r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}", fid[8:]) for fid in attempt["scope"]),
                    "listing scope")
        expected_vendor = "listing"
    else:
        raise IdentityError("identity observations: visible attempt kind unsupported")
    families = payload["families"]
    _ob_require(type(families) is list and len(families) == len(attempt["scope"]),
                "visible family count")
    seen = set()
    known_ns = _ob_ns(attempt["owner_read_completed_at_utc_ns"], "owner read")
    for family in families:
        _ob_fields(family, "family_id alias_revision_id predecessor_revision_id vendor symbols "
                   "security_id country mic security_class status reason evidence_sha256 "
                   "row_sha256 family_sha256", "family")
        _ob_seal(family, "family_sha256")
        fid = _ob_text(family["family_id"], "family ID")
        _ob_require(fid in attempt["scope"] and fid not in seen, "family scope membership")
        seen.add(fid)
        _ob_require(family["alias_revision_id"] == attempt["attempt_id"] + "/" + fid,
                    "family revision identity")
        prior = state.get(fid)
        _ob_require(family["predecessor_revision_id"] == (
            prior["alias_revision_id"] if prior else None), "family predecessor")
        _ob_require(type(family["vendor"]) is str and family["vendor"] == expected_vendor,
                    "family vendor")
        symbols = family["symbols"]
        _ob_require(type(symbols) is list and (len(symbols) == 1 if expected_vendor == "polygon" else 2 <= len(symbols) <= 65),
                    "family symbols")
        for symbol in symbols:
            _ob_require(type(symbol) is str and re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,31}", symbol),
                        "family symbol string")
        _ob_require(len(set(symbols)) == len(symbols), "duplicate family symbol")
        _ob_require(family["country"] == "US", "family country")
        if expected_vendor == "polygon":
            sym, mic, klass = _NATIVE_SCOPE[fid]
            _ob_require(symbols == [sym] and family["mic"] == mic
                        and family["security_class"] == klass, "native family class/MIC")
        else:
            _ob_require(family["mic"] == "XNAS"
                        and family["security_class"] in ("COMMON_CLASS_B", "ORDINARY_CLASS_A"),
                        "listing family class/MIC")
        if prior:
            for key in ("vendor", "country", "mic", "security_class"):
                _ob_require(family[key] == prior[key], "family identity changed")
            _ob_require(symbols[:len(prior["symbols"])] == prior["symbols"],
                        "family symbol chain changed")
            if prior["security_id"] is not None:
                _ob_require(family["security_id"] == prior["security_id"], "family security changed")
        if family["security_id"] is not None:
            _ob_text(family["security_id"], "family security")
            _ob_require(parse_id(family["security_id"])[0] == "security", "family security kind")
        _ob_hash(family["evidence_sha256"], "family evidence")
        members = family["row_sha256"]
        _ob_require(type(members) is list and len(members) <= 65, "family row count")
        for member in members:
            _ob_hash(member, "row membership")
        _ob_require(len(set(members)) == len(members), "duplicate row membership")
        _ob_require(members == attempt["row_membership"][fid], "visible envelope row membership")
        observed = acquisition[fid]
        _ob_fields(observed, "started_at_utc_ns completed_at_utc_ns outcome representation "
                   "response_sha256 source_published_at published_date", "acquisition entry")
        start = _ob_ns(observed["started_at_utc_ns"], "acquisition start")
        end = _ob_ns(observed["completed_at_utc_ns"], "acquisition complete")
        _ob_require(start <= end <= known_ns, "acquisition clock order")
        _ob_require(observed["outcome"] in ("SUCCESS", "FAILED"), "acquisition outcome")
        _ob_require(observed["representation"] in (None, "raw_bytes", "decoded_document", "decoded_json"),
                    "acquisition representation")
        if observed["response_sha256"] is not None:
            _ob_hash(observed["response_sha256"], "response")
        if observed["outcome"] == "SUCCESS":
            _ob_require(observed["representation"] is not None
                        and observed["response_sha256"] is not None, "successful acquisition custody")
        if observed["source_published_at"] is not None:
            _ob_clock(observed["source_published_at"])
        _ob_date(observed["published_date"], "publication", nullable=True)
        response_role = "native_response" if expected_vendor == "polygon" else "continuity_evidence"
        _ob_require(evidence[fid + "/" + response_role] == observed["response_sha256"],
                    "acquisition dependency response mismatch")
        expected_evidence = _ob_digest({
            "schema": "mastermind.identity_family_evidence.v1", "family_id": fid,
            "input_file_sha256": attempt["input_file_sha256"], "input_sha256": attempt["input_sha256"],
            "dependencies_sha256": attempt["dependencies_sha256"], "acquisition": observed})
        _ob_require(family["evidence_sha256"] == expected_evidence, "family evidence seal")
        available_rows = {_ob_digest(r): r for r in records
                          if r.get("attempt_id") == attempt["attempt_id"]
                          and r.get("alias_family_id") == fid}
        _ob_require(set(available_rows) == set(members), "family row membership")
        rows = [available_rows[member] for member in members]
        status = family["status"]
        _ob_require(status in ("BOUND", "REFUSED"), "accepted family disposition")
        if status == "REFUSED":
            _ob_text(family["reason"], "refusal reason")
            _ob_require(not rows, "refused family has binding rows")
        else:
            _ob_require(family["reason"] is None and family["security_id"] is not None,
                        "bound disposition")
            own_dependencies = _EVIDENCE_COMMON | {fid + "/" + role for role in roles}
            _ob_require(observed["outcome"] == "SUCCESS"
                        and all(evidence[key] is not None for key in own_dependencies),
                        "bound dependencies unavailable")
            _ob_require(len(rows) == len(symbols), "bound row count")
            for row in rows:
                for key in ("vendor", "vendor_symbol", "security_id", "ingested_at"):
                    _ob_text(row[key], key)
                _ob_require(row["vendor"] == expected_vendor and row["vendor_symbol"] in symbols
                            and row["security_id"] == family["security_id"]
                            and row["evidence_sha256"] == family["evidence_sha256"],
                            "row family identity")
                _ob_require(row["known_at"] == _ob_iso(known_ns), "row evidence clock")
                lo = _ob_date(row["valid_from"], "valid_from", nullable=True)
                hi = _ob_date(row["valid_to"], "valid_to", nullable=True)
                _ob_require(lo is None or hi is None or lo < hi, "event interval width")
            if expected_vendor == "polygon":
                _ob_require(rows[0]["valid_from"] is not None, "native dated interval")
            else:
                by_symbol = {r["vendor_symbol"]: r for r in rows}
                _ob_require([r["vendor_symbol"] for r in rows] == symbols,
                            "listing row symbol order")
                _ob_require(set(by_symbol) == set(symbols), "listing row symbols")
                chain = [by_symbol[s] for s in symbols]
                _ob_require(chain[-1]["valid_to"] is None, "listing interval endpoints")
                for old, new in zip(chain, chain[1:]):
                    _ob_require(old["valid_to"] is not None
                                and old["valid_to"] == new["valid_from"], "listing interval tiling")
        state[fid] = {**family, "_rows": rows, "_attempt_id": attempt["attempt_id"],
                      "_known_at": str(known_ns)}


def _ob_validate_master(family, master):
    hits = [r for r in master if r.get("security_id") == family["security_id"]]
    _ob_require(len(hits) == 1, "canonical master identity not unique")
    row = hits[0]
    _ob_require(row.get("security_state") in (None, ""), "canonical master inactive")
    key = parse_listing_key(_ob_text(row.get("listing_key"), "master listing"))
    _ob_require(row.get("country") == family["country"] == key.country
                and row.get("mic") == family["mic"] == key.mic
                and row.get("inception_code") == key.code, "canonical master class/MIC binding")


def _ob_select(table, vendor, value, on, decision_at, receipts, inverse):
    _ob_text(vendor, "query vendor")
    _ob_text(value, "query identity")
    cutoff = _ob_clock(decision_at)
    _ob_require(type(on) is date, "event date required")
    if vendor not in _CLOCKED_ALIAS_VENDORS:
        return AliasResolution("UNAVAILABLE", vendor, reason="CLOCKED_NAMESPACE_REQUIRED")
    if table._observation_state is None:
        return AliasResolution("UNAVAILABLE", vendor, reason="OBSERVATION_CONTEXT_REQUIRED")
    history_json, original_json, contexts = table._observation_state
    history, original = json.loads(history_json), json.loads(original_json)
    _ob_require(type(receipts) in (tuple, list) and len(receipts) <= 256,
                "read receipt sequence bound")
    eligible = []
    for receipt in receipts:
        _ob_require(type(receipt) is ReferenceReadReceipt, "read receipt value required")
        checked_read = ReferenceReadReceipt.from_record(receipt.as_record())
        _ob_require(checked_read == receipt, "read receipt canonical vector")
        receipt = checked_read
        snapshot = contexts.get(receipt.receipt_sha256)
        _ob_require(snapshot is not None, "read receipt has no exact snapshot")
        context = _ob_load(snapshot.receipt_bytes, 9 * _MIB)
        prefix, pub = context["identity_observations"], context["publication"]
        vector = tuple((n, pub["artifacts"][n]["sha256"]) for n in _ARTIFACT_NAMES)
        _ob_require(receipt.generation_id == pub["generation_id"]
                    and receipt.artifact_sha256 == vector
                    and receipt.history_prefix_sha256 == _ob_digest(prefix), "read receipt snapshot mismatch")
        last_clock = (prefix["attempts"][-1]["owner_read_completed_at_utc_ns"]
                      if prefix["attempts"] else prefix["anchor"]["owner_read_completed_at_utc_ns"])
        _ob_require(_ob_ns(receipt.read_completed_at_utc_ns, "read") >= _ob_ns(last_clock, "owner"),
                    "consumer read precedes owner observation")
        if _ob_ns(receipt.read_completed_at_utc_ns, "read") <= cutoff:
            eligible.append((len(prefix["attempts"]), receipt, snapshot, context))
    if on > (_EPOCH + timedelta(seconds=cutoff // 1_000_000_000)).date():
        return AliasResolution("UNAVAILABLE", vendor, reason="EVENT_AFTER_DECISION")
    if not eligible:
        return AliasResolution("UNAVAILABLE", vendor, reason="NO_ENROLLED_SNAPSHOT_BY_CUTOFF")
    n = max(item[0] for item in eligible)
    choices = [item for item in eligible if item[0] == n]
    semantic_pairs = {(item[3]["publication"]["artifacts"]["vendor_aliases.parquet"]["semantic_sha256"],
                       item[3]["publication"]["artifacts"]["security_master.parquet"]["semantic_sha256"])
                      for item in choices}
    _ob_require(len(semantic_pairs) == 1, "ambiguous same-prefix snapshot semantics")
    _, read, snapshot, context = min(
        choices, key=lambda item: (_ob_ns(item[1].read_completed_at_utc_ns, "read"),
                                  item[1].receipt_sha256))
    records, master = json.loads(snapshot.alias_json), json.loads(snapshot.master_json)
    state = _ob_initial_families(history, original, records)
    for attempt in history["attempts"][:n]:
        _ob_apply_attempt(state, attempt, records)
    active = []
    refused = []
    for family in state.values():
        if int(family["_known_at"]) > cutoff:
            continue
        if family["status"] == "BOUND":
            _ob_validate_master(family, master)
        if family["vendor"] != vendor:
            continue
        if family["status"] == "REFUSED":
            if (family["security_id"] == value if inverse else value in family["symbols"]):
                refused.append(family)
            continue
        for row in family["_rows"]:
            lo = _ob_date(row.get("valid_from"), "valid_from", nullable=True)
            hi = _ob_date(row.get("valid_to"), "valid_to", nullable=True)
            if (lo is None or lo <= on) and (hi is None or on < hi):
                active.append((row, family))
    for field in ("vendor_symbol", "security_id"):
        seen = set()
        for row, _family in active:
            key = row[field]
            _ob_require(key not in seen, "ambiguous selected alias " + field)
            seen.add(key)
    matches = [(row, fam) for row, fam in active
               if row["security_id" if inverse else "vendor_symbol"] == value]
    _ob_require(len(refused) <= 1 and not (refused and matches), "ambiguous refused family")
    if refused:
        family = refused[0]
        return AliasResolution("REFUSED", vendor, attempt_id=family["_attempt_id"],
                               alias_revision_id=family["alias_revision_id"],
                               known_at_utc_ns=family["_known_at"], receipt_sha256=read.receipt_sha256,
                               reason=family["reason"])
    if not matches:
        return AliasResolution("UNAVAILABLE", vendor, receipt_sha256=read.receipt_sha256,
                               reason="NO_BINDING_AT_EVENT_DATE")
    row, family = matches[0]
    return AliasResolution("BOUND", vendor, row["vendor_symbol"], row["security_id"],
                           family["_attempt_id"], family["alias_revision_id"],
                           family["_known_at"], read.receipt_sha256)


# ── Issuer master reader (§D2B1) — the economic-entity axis over the security master ──
def _null_to_none(value: object) -> object | None:
    """``None`` for ``None`` OR a ``float('nan')`` cell; the value unchanged otherwise.

    STDLIB-ONLY NaN check (no ``pandas`` import in this module): ``float('nan') !=
    float('nan')`` is the one universal, dependency-free way to detect it — every
    other float compares equal to itself.  See :meth:`IssuerMaster.from_records`.
    """
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # noqa: PLR0124 — the NaN test itself
        return None
    return value


_CIK_RE = re.compile(r"^\d{1,10}$")


def _normalize_issuer_cik(value: object) -> str | None:
    """Normalize a nullable issuer-master CIK to its ten-digit SEC spelling."""
    value = _null_to_none(value)
    if value is None:
        return None
    text = str(value).strip()
    if not _CIK_RE.fullmatch(text):
        raise IdentityError(f"issuer CIK is not a 1-10 digit SEC value: {value!r}")
    return text.zfill(10)


@dataclass(frozen=True, slots=True)
class SecurityIssuerRow:
    """One ``security_master.parquet`` row's issuer axis, as read by :class:`IssuerMaster`.

    Carries only the columns the issuer reader needs — not a copy of the whole master
    row shape, so a future master column never forces a change here.

    ``security_state``/``superseded_by`` (V4-D2B1-R1 §3.6) are the SECURITY axis —
    orthogonal to ``issuer_state`` above, which is the ISSUER axis.  ``security_state``
    is ``None`` for an active row and the closed enum's one value this era
    (``SUPERSEDED_DUPLICATE_MINT``) for a row this builder corrected onto
    ``superseded_by``; a consumer that needs "is this security still active" reads
    this field, never ``issuer_state``.
    """

    security_id: str
    issuer_id: str | None
    issuer_state: str
    listing_key: str
    security_state: str | None = None
    superseded_by: str | None = None
    issuer_cik: str | None = None


class IssuerMaster:
    """Issuer <-> security lookups over the committed security-master rows.  NO I/O.

    ``scripts/build_security_master.py`` is the ALLOCATOR/AUTHORITY for the issuer
    axis (mint-once, era-gated correction, spec D2B1 §2/§4); this class is the ONE
    canonical READER (spec §3 "Reader API" — no competing issuer allocator or reader
    anywhere else).  Construct it from the security master's rows via
    :meth:`from_records`; reading the parquet is the caller's job, exactly like
    :class:`VendorAliasTable`.

    HISTORICAL LIMITATION (spec §5).  CIK evidence is a CURRENT-registrant
    observation: the newest ``data/symbol_directory/cik_map/*.parquet`` snapshot
    proves who owns a ticker TODAY, never what the issuer mapping was on a past date
    — it does not prove what the issuer mapping was in 2015.  This reader therefore
    carries NO ``asof`` parameter and answers only "which securities does this issuer
    own, right now" / "what is this security's issuer, right now" — the answer is
    canonical for CURRENT identity and must never be read as a historical lineage
    claim.  (This is the issuer-axis analogue of the two-clock law
    :class:`VendorAliasTable` enforces for vendor symbols — a current observation
    answering a historical question is exactly the defect that class exists to
    prevent, one layer up.)
    """

    __slots__ = ("_by_security", "_by_issuer", "_ciks_by_issuer", "_listing_keys_by_security")

    def __init__(self, rows: list[SecurityIssuerRow] | tuple[SecurityIssuerRow, ...] = ()) -> None:
        by_security: dict[str, SecurityIssuerRow] = {}
        by_issuer: dict[str, list[str]] = {}
        ciks_by_issuer: dict[str, set[str]] = {}
        for row in rows:
            issuer_cik = _normalize_issuer_cik(row.issuer_cik)
            if issuer_cik != row.issuer_cik:
                row = replace(row, issuer_cik=issuer_cik)
            by_security[row.security_id] = row
            # V4-D2B1-R1 §3.6: a security-axis-superseded row (a tombstone) is
            # excluded from issuer aggregation by default — it is still readable via
            # `_by_security` (so a caller CAN look it up and see its security_state),
            # but `securities_of_issuer` must never hand back a corrected duplicate as
            # if it were a live member of the issuer's roster.
            if row.issuer_id is not None and not row.security_state:
                by_issuer.setdefault(row.issuer_id, []).append(row.security_id)
                if issuer_cik is not None:
                    ciks_by_issuer.setdefault(row.issuer_id, set()).add(issuer_cik)
        self._by_security = by_security
        self._by_issuer: dict[str, tuple[str, ...]] = {
            k: tuple(sorted(v)) for k, v in by_issuer.items()
        }
        self._ciks_by_issuer: dict[str, tuple[str, ...]] = {
            k: tuple(sorted(v)) for k, v in ciks_by_issuer.items()
        }
        listing_keys_by_security: dict[str, set[str]] = {}
        for row in rows:
            # V4-D2B1-R1 §3.6: a security-axis-superseded row (a tombstone) is
            # excluded from listing-key aggregation, same as `by_issuer` above --
            # a stale key on a corrected duplicate must never be handed back as
            # if it were the security's current listing key.
            if row.listing_key and not row.security_state:
                listing_keys_by_security.setdefault(row.security_id, set()).add(row.listing_key)
        self._listing_keys_by_security: dict[str, tuple[str, ...]] = {
            k: tuple(sorted(v)) for k, v in listing_keys_by_security.items()
        }

    @classmethod
    def from_records(cls, records) -> "IssuerMaster":
        """Build from a list of dicts — a ``security_master.parquet`` read the caller
        already did (``to_dict("records")`` or equivalent).

        NaN-SAFE WITHOUT PANDAS (V4-D2B1 FIX 3 / M1).  This module is stdlib-only
        (module docstring), so it cannot reach for ``pd.isna``.  A ``pandas``
        ``to_dict("records")`` round-trip can hand back a genuine ``float('nan')`` —
        never Python ``None`` — for a null cell in a nullable string column that also
        carries real strings (the same trap ``scripts/build_security_master.py``
        documents at its own ``_read_existing``/``_write_parquet``).  ``value is None``
        alone misses it, and NaN is TRUTHY, so the old ``rec.get(...) or ""`` fallback
        used for ``issuer_state``/``listing_key`` would also stringify a NaN cell into
        the literal string ``"nan"`` rather than treating it as absent.  A NaN
        ``issuer_id`` must index as NO issuer, never the string ``'nan'``.
        """
        rows: list[SecurityIssuerRow] = []
        for i, rec in enumerate(records or ()):
            try:
                sec = str(rec["security_id"])
            except KeyError as exc:
                raise IdentityError(
                    f"security master record {i} is missing {exc.args[0]!r}"
                ) from exc
            issuer = _null_to_none(rec.get("issuer_id"))
            state = _null_to_none(rec.get("issuer_state"))
            listing_key = _null_to_none(rec.get("listing_key"))
            issuer_cik = _normalize_issuer_cik(rec.get("issuer_cik"))
            # V4-D2B1-R1 §3.6: absent on a pre-repair master (era-seam, same NaN trap
            # as the fields above) — `.get(...)` + `_null_to_none` handles both the
            # missing-key and the NaN-cell shapes uniformly.
            security_state = _null_to_none(rec.get("security_state"))
            superseded_by = _null_to_none(rec.get("superseded_by"))
            rows.append(
                SecurityIssuerRow(
                    security_id=sec,
                    issuer_id=None if issuer is None else str(issuer),
                    issuer_state=str(state) if state is not None else "",
                    listing_key=str(listing_key) if listing_key is not None else "",
                    issuer_cik=issuer_cik,
                    security_state=None if security_state is None else str(security_state),
                    superseded_by=None if superseded_by is None else str(superseded_by),
                )
            )
        return cls(rows)

    @property
    def rows(self) -> tuple[SecurityIssuerRow, ...]:
        return tuple(self._by_security.values())

    def issuer_of_security(self, security_id: str) -> str | None:
        """This security's CURRENT issuer_id, or ``None`` (unknown security, or a
        known one with no evidenced/legacy issuer_id — spec §3 ``NO_ISSUER_EVIDENCE``
        + null case)."""
        row = self._by_security.get(security_id)
        return row.issuer_id if row is not None else None

    def securities_of_issuer(self, issuer_id_: str) -> tuple[str, ...]:
        """Every ``security_id`` CURRENTLY carrying this ``issuer_id`` — the §9.7
        canonical query.  Sorted; empty tuple if the issuer id is unknown or unused.

        EXCLUDES a security-axis-superseded row (V4-D2B1-R1 §3.6) by construction —
        see :meth:`__init__`.
        """
        return self._by_issuer.get(issuer_id_, ())

    def cik_of_issuer(self, issuer_id_: str) -> str | None:
        """This issuer's evidenced CURRENT CIK, or ``None`` when unobserved.

        CIK evidence in the master is a current-registrant observation only; this
        method intentionally has no ``asof`` parameter and cannot establish a
        historical issuer binding.  Multiple active rows may repeat one CIK (for
        example, dual share classes), but differing non-null CIKs are an ambiguous
        identity fact and are refused rather than guessed.
        """
        ciks = self._ciks_by_issuer.get(issuer_id_, ())
        if not ciks:
            return None
        if len(ciks) != 1:
            raise IdentityError(
                f"conflicting current issuer CIK observations for {issuer_id_!r}: "
                f"{', '.join(ciks)}"
            )
        return ciks[0]

    def listing_key_of_security(self, security_id: str) -> str | None:
        """This security's CURRENT listing key as evidenced by the master, or None.

        Current-identity only (same limitation the class docstring already states
        for issuer/CIK evidence): no asof-scoped listing lineage.
        """
        keys = self._listing_keys_by_security.get(security_id, ())
        if not keys:
            return None
        if len(keys) != 1:
            raise IdentityError(
                f"conflicting current listing key observations for {security_id!r}: "
                f"{', '.join(keys)}"
            )
        return keys[0]

    def security_state_of(self, security_id: str) -> str | None:
        """This security's ``security_state`` (V4-D2B1-R1 §3.6) — ``None`` for an
        active row, ``"SUPERSEDED_DUPLICATE_MINT"`` for a corrected duplicate, or
        ``None`` for an unknown ``security_id`` (indistinguishable from active; check
        membership via :attr:`rows` / ``by_security`` lookups first if that matters)."""
        row = self._by_security.get(security_id)
        return row.security_state if row is not None else None

    def superseded_by_of(self, security_id: str) -> str | None:
        """The ``security_id`` this row was corrected onto, or ``None`` when it is
        active (or unknown) — V4-D2B1-R1 §3.6."""
        row = self._by_security.get(security_id)
        return row.superseded_by if row is not None else None
