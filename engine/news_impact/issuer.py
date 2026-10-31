"""``engine/news_impact/issuer.py`` — the news-mention issuer resolution ladder.

Implements the masterplan §3.1 capture rule (MASTERPLAN.md §3.1, "Capture and
eligibility") as constrained by PHASE0_FREEZE_2026-10-11.md §6: population
items must "resolve to an issuer with a ``cik:`` identity" and "items that
fail resolution are counted, never silently dropped".  A news mention that
names a company therefore gets exactly one ladder answer here: a canonical
``cik:`` company id, or a typed absence with a closed reason, plus a receipt
for every hop.

The ladder (first success wins, every attempted rung receipted):

1. ``explicit_cik``   — ``mention.cik`` normalised through the owner
   ``engine.company_intelligence.identity.company_id_for_cik``.  A malformed
   explicit cik terminates the ladder as ``malformed_identifier``: the source
   asserted an issuer identity and failed; resolving a different identifier
   in its place would be a guess, and a guessed issuer is worse than a typed
   absence (identity.py module docstring).  The ticker, if any, is recorded
   in the rung input but deliberately not consulted.
2. ``registry``       — ``IssuerRegistry.resolve_ticker`` at ``mention.asof``
   (point-in-time windows from ``ListingAlias``), with sibling security ids
   from the resolved issuer's ``security_ids_at`` (the same set
   ``siblings_of`` enumerates by ticker: docket §4.2 rule 4 — dual classes
   share an issuer and stay distinct securities).
3. ``ledger``         — ``ticker -> [(company_id, valid_from, valid_to)]``
   entries valid at ``asof`` (half-open windows, ``valid_to`` exclusive, the
   owner's semantics).  Exactly one distinct cik resolves; more than one is
   ``ambiguous_ticker`` with every candidate listed; entries present but none
   covering ``asof`` is ``not_listed_at_asof``.  When the entries carry no
   validity dates the rung outcome carries the exact note
   ``ledger has no validity dates`` — the hop is then identity-*now*, not
   point-in-time, and the receipt says so.
4. ``absent``         — ``unknown_ticker`` (a ticker that matched nothing),
   ``name_only_mention`` (text only: v1 does no fuzzy name matching), or
   ``no_mention`` (no usable identifier and empty text).

The program mints no new identifier family (freeze §6; identity.py §4.2):
every company id here is the owner's ``cik:`` + 10 digits, and every security
id is the owner's ``mic:ticker``.

Absence rendering: the frozen schema requires a non-nullable ``company_id``
on every event template (news_impact_event.v1.schema.json lines 1147/1192,
1588/1633), so an issuer absence can never ride on an event.  The schema's
absence vocabulary offers ``absence_union`` = ``field_absence.v1`` |
``owner_typed_absence_v1``; ``field_absence.v1``'s reasons
(not_stated/stated_without_number/range_only/redacted_rights/parse_failed)
are quantity-field shaped, while ``owner_typed_absence_v1`` (schema line 554)
carries ``unjoinable_filing_identity`` (line 586) — the identity-join
failure.  ``absence_payload`` therefore renders every ladder absence as
``owner_typed_absence_v1`` with reason ``unjoinable_filing_identity``; the
precise ladder reason rides in ``detail`` and the reason stays on the
``IssuerResolution`` for counting.

Mention text is DATA (masterplan §3.5): nothing in it is ever interpreted as
an instruction, and no fragment of it reaches a receipt or payload verbatim.

Build-gate compliance: pure functions over frozen value objects, no
module-level I/O, no clock reads (``asof`` is always a parameter), and
deterministic output (sorted candidates, sorted ledger iteration, fixed
receipt key order).  No confidence, probability, score, price-target or
fair-value field is defined anywhere in this module.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from engine.company_intelligence.contracts import ContractError
from engine.company_intelligence.identity import (
    IdentityError,
    IssuerRegistry,
    company_id_for_cik,
)

RESOLVER_VERSION = "ni-issuer-1"
RUNGS = ("explicit_cik", "registry", "ledger", "absent")
ABSENCE_REASONS = (
    "unknown_ticker",
    "ambiguous_ticker",
    "not_listed_at_asof",
    "name_only_mention",
    "malformed_identifier",
    "no_mention",
)

# Exact receipt note emitted when a ledger hop consulted entries that carry no
# validity dates (the estate file has none): the hop cannot be point-in-time.
NO_VALIDITY_DATES_NOTE = "ledger has no validity dates"

class LedgerError(Exception):
    """The ticker->CIK ledger file is unreadable or wrongly shaped."""


def canonical_ticker(raw: object) -> str | None:
    """Return the canonical lookup form of a mention ticker, or ``None``.

    One documented rule, applied before both the registry and ledger rungs:

    * upper-case, surrounding whitespace stripped;
    * a single leading ``$`` is stripped (``$TSLA`` -> ``TSLA``) and only one;
    * a ``.`` share-class separator is rewritten to ``-`` (``BRK.B`` ->
      ``BRK-B``), matching the estate ledger's native form (``BRK-B``,
      ``BF-B``, ``CRD-A`` in ``data/edgar/ticker_cik_ledger.json``).

    Empty input (or whitespace only) is ``None``: the mention carries no
    ticker and the identifier rungs are not attempted.
    """
    text = str(raw if raw is not None else "").strip().upper()
    if text.startswith("$"):
        text = text[1:]
    if not text:
        return None
    return text.replace(".", "-")


@dataclass(frozen=True)
class Mention:
    """One company mention exactly as the source carried it.

    ``text`` is the literal mention (DATA, never instructions; never copied
    verbatim into receipts).  ``cik`` is the raw digit string as found, any
    width, with or without a ``cik:`` prefix.  ``asof`` is the instant the
    resolution must be true at — a parameter, never a clock read.
    """

    text: str
    ticker: str | None
    cik: str | None
    exchange_mic: str | None
    asof: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", str(self.text or ""))
        for name in ("ticker", "cik", "exchange_mic"):
            value = getattr(self, name)
            if value is not None:
                value = str(value).strip() or None
            object.__setattr__(self, name, value)
        asof = self.asof
        if isinstance(asof, datetime):
            object.__setattr__(self, "asof", asof.date())
        elif not isinstance(asof, date):
            raise ValueError(f"Mention.asof must be a datetime.date: {asof!r}")


@dataclass(frozen=True)
class IssuerResolution:
    """The ladder's answer for one mention: an issuer, or a typed absence.

    ``candidates`` is every sorted company id a rung considered; it is empty
    unless the ledger rung actually found entries.  ``receipt`` records each
    attempted rung in order, each with its input and outcome, plus
    ``resolver_version``; rungs not attempted are simply absent.
    """

    company_id: str | None
    rung: str
    absence_reason: str | None
    candidates: tuple[str, ...]
    sibling_security_ids: tuple[str, ...]
    receipt: dict = field(default_factory=dict)


class Ledger(Mapping):
    """Immutable ``ticker -> tuple of (company_id, valid_from, valid_to)``.

    Returned by :func:`load_ledger`.  Iteration is sorted and entries under a
    key are ordered by ``(company_id, valid_from)`` so every consumer that
    walks the mapping sees one deterministic order.  ``has_validity_dates``
    records whether any entry in the file carried a window at all.
    """

    __slots__ = ("_entries", "_has_validity_dates", "_source")

    def __init__(
        self,
        entries: Mapping[str, tuple[tuple[str, date | None, date | None], ...]],
        *,
        has_validity_dates: bool,
        source: str,
    ) -> None:
        self._entries = {
            ticker: tuple(sorted(set(entries_of_ticker)))
            for ticker, entries_of_ticker in entries.items()
        }
        self._has_validity_dates = bool(has_validity_dates)
        self._source = str(source)

    @property
    def has_validity_dates(self) -> bool:
        """Whether any entry in the source file carried a validity window."""
        return self._has_validity_dates

    @property
    def source(self) -> str:
        """A string naming where this ledger was loaded from."""
        return self._source

    def __getitem__(self, ticker: str) -> tuple[tuple[str, date | None, date | None], ...]:
        return self._entries[ticker]

    def __iter__(self):
        return iter(sorted(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Ledger(source={self._source!r}, tickers={len(self._entries)}, has_validity_dates={self._has_validity_dates})"


def _ledger_date(value: object, ticker: str, key: str, source: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise LedgerError(
            f"ledger entry date not ISO: {ticker}.{key}={value!r} in {source}"
        ) from exc


def _ledger_entry(ticker: str, value: object, source: str) -> tuple[str, date | None, date | None]:
    """Coerce one ledger value into ``(company_id, valid_from, valid_to)``."""
    if isinstance(value, bool) or value is None:
        raise LedgerError(f"ledger entry malformed: {ticker}={value!r} in {source}")
    if isinstance(value, (str, int)):
        # Flat estate shape: {"AAPL": 320193}.  No dates.
        try:
            return company_id_for_cik(value), None, None
        except ContractError as exc:
            raise LedgerError(
                f"ledger entry not a CIK: {ticker}={value!r} in {source}"
            ) from exc
    if isinstance(value, Mapping):
        cik = value.get("cik")
        if cik is None:
            raise LedgerError(f"ledger entry missing 'cik': {ticker} in {source}")
        try:
            company_id = company_id_for_cik(cik)
        except ContractError as exc:
            raise LedgerError(
                f"ledger entry not a CIK: {ticker}={cik!r} in {source}"
            ) from exc
        valid_from = _ledger_date(value.get("valid_from"), ticker, "valid_from", source)
        valid_to = _ledger_date(value.get("valid_to"), ticker, "valid_to", source)
        if valid_from is not None and valid_to is not None and valid_to <= valid_from:
            raise LedgerError(
                f"ledger entry window empty: {ticker}=[{valid_from},{valid_to}] in {source}"
            )
        return company_id, valid_from, valid_to
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return (
            _ledger_entry(ticker, value[0], source)[0],
            _ledger_date(value[1], ticker, "valid_from", source),
            _ledger_date(value[2], ticker, "valid_to", source),
        )
    raise LedgerError(f"ledger entry malformed: {ticker}={value!r} in {source}")


def _iter_ledger_values(value: object) -> list[object]:
    """Split one ledger value into the entry values it denotes.

    A 3-item sequence of scalars is one positional ``(cik, valid_from,
    valid_to)`` entry; any other sequence is a list of entries (a ticker that
    changed hands); anything else is a single entry.
    """
    if isinstance(value, (list, tuple)):
        positional = (
            len(value) == 3
            and all(
                item is None
                or (isinstance(item, (str, int)) and not isinstance(item, bool))
                for item in value
            )
        )
        if positional:
            return [tuple(value)]
        return list(value)
    return [value]


def load_ledger(path: object) -> Ledger:
    """Parse a ticker->CIK ledger file into an immutable :class:`Ledger`.

    Accepted shapes (whatever date fields the file actually has):

    * the estate shape ``{"note": ..., "tickers": {"AAPL": 320193, ...}}``
      where each CIK is an int or digit string and no validity dates exist;
    * dated single entries ``{"tickers": {"AAPL": {"cik": "320193",
      "valid_from": "1998-01-02", "valid_to": null}}}``;
    * dated entry lists ``{"tickers": {"WAVE": [{"cik": ..., "valid_from":
      ..., "valid_to": ...}, ...]}}`` (a ticker that changed hands).

    Raises :class:`LedgerError` (never a bare ``OSError``/``ValueError``) for
    an unreadable file, non-JSON content, a non-object root, a missing
    ``tickers`` mapping, or an entry that is not a CIK or not ISO dates.
    """
    source = str(path)
    p = Path(path)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError(f"ledger unreadable: {source} ({exc})") from exc
    if not isinstance(doc, Mapping):
        raise LedgerError(f"ledger not a JSON object: {source}")
    tickers = doc.get("tickers")
    if not isinstance(tickers, Mapping):
        raise LedgerError(f"ledger missing 'tickers' mapping: {source}")
    entries: dict[str, tuple[tuple[str, date | None, date | None], ...]] = {}
    has_validity_dates = False
    for ticker, value in tickers.items():
        parsed = []
        for item in _iter_ledger_values(value):
            company_id, valid_from, valid_to = _ledger_entry(ticker, item, source)
            if valid_from is not None or valid_to is not None:
                has_validity_dates = True
            parsed.append((company_id, valid_from, valid_to))
        entries[canonical_ticker(ticker) or str(ticker)] = tuple(parsed)
    return Ledger(entries, has_validity_dates=has_validity_dates, source=source)


def _valid_at(entry: tuple[str, date | None, date | None], asof: date) -> bool:
    """Half-open validity (owner ``ListingAlias.covers`` semantics)."""
    _, valid_from, valid_to = entry
    if valid_from is not None and asof < valid_from:
        return False
    return valid_to is None or asof < valid_to


def resolve_mention(
    mention: Mention,
    *,
    registry: IssuerRegistry | None = None,
    ledger: Mapping[str, tuple[tuple[str, date | None, date | None], ...]] | None = None,
) -> IssuerResolution:
    """Resolve one mention through the ladder; first success wins.

    Rungs not attempted (no cik / no ticker / no registry / no ledger) are
    simply absent from the receipt.  Never raises on unresolvable input: an
    unresolvable mention IS the typed absence this module exists to count.
    """
    rungs: list[dict[str, Any]] = []
    ticker = canonical_ticker(mention.ticker)
    asof_iso = mention.asof.isoformat()

    def record(rung: str, rung_input: dict[str, Any], outcome: str, **extra: Any) -> None:
        rungs.append({"rung": rung, "input": rung_input, "outcome": outcome, **extra})

    def finish(
        company_id: str | None,
        rung: str,
        absence_reason: str | None,
        candidates: Iterable[str] = (),
        sibling_security_ids: Iterable[str] = (),
    ) -> IssuerResolution:
        return IssuerResolution(
            company_id=company_id,
            rung=rung,
            absence_reason=absence_reason,
            candidates=tuple(sorted(set(candidates))),
            sibling_security_ids=tuple(sorted(set(sibling_security_ids))),
            receipt={"resolver_version": RESOLVER_VERSION, "rungs": rungs},
        )

    # Rung 1: explicit cik -------------------------------------------------
    if mention.cik is not None:
        rung_input = {"cik": mention.cik, "ticker": ticker, "asof": asof_iso}
        try:
            company_id = company_id_for_cik(mention.cik)
        except ContractError:
            note = (
                "malformed cik; ticker not consulted (never a guess)"
                if ticker is not None
                else "malformed cik"
            )
            record("explicit_cik", rung_input, "malformed", note=note)
            record(
                "absent",
                {"ticker": ticker, "cik": mention.cik, "asof": asof_iso},
                "malformed_identifier",
            )
            return finish(None, "absent", "malformed_identifier")
        if ticker is not None:
            record(
                "explicit_cik",
                rung_input,
                "resolved",
                company_id=company_id,
                note="ticker not consulted (explicit identifier wins)",
            )
        else:
            record("explicit_cik", rung_input, "resolved", company_id=company_id)
        return finish(company_id, "explicit_cik", None, [company_id])

    # Rungs 2 and 3 both key off a ticker ----------------------------------
    if ticker is not None:
        # Rung 2: registry -------------------------------------------------
        if registry is not None:
            rung_input = {"ticker": ticker, "asof": asof_iso}
            hit = None
            recorded = False
            try:
                hit = registry.resolve_ticker(ticker, asof=mention.asof)
            except IdentityError as exc:
                # Two issuers claim the symbol at asof inside the registry
                # itself.  Recorded, then fall through: the ledger rung may
                # still answer from a coarser source, with the ambiguity in
                # the receipt either way.
                record("registry", rung_input, "ambiguous", note=str(exc))
                recorded = True
            except ContractError as exc:
                record("registry", rung_input, "unsafe_ticker", note=str(exc))
                recorded = True
            if hit is not None:
                record("registry", rung_input, "resolved", company_id=hit.company_id)
                issuer = registry.issuer(hit.company_id)
                resolution = finish(
                    hit.company_id,
                    "registry",
                    None,
                    [hit.company_id],
                    tuple(
                        security_id
                        for security_id in issuer.security_ids_at(mention.asof)
                        if security_id != hit.security_id
                    ),
                )
                resolution.receipt["sibling_tickers"] = tuple(
                    sorted(set(registry.siblings_of(ticker, asof=mention.asof)))
                )
                return resolution
            if not recorded:
                record("registry", rung_input, "not_found")

        # Rung 3: ledger ---------------------------------------------------
        if ledger is not None:
            rung_input = {"ticker": ticker, "asof": asof_iso}
            entries = ledger.get(ticker) or ()
            entries = tuple(entries)
            if entries:
                dated = any(vf is not None or vt is not None for _, vf, vt in entries)
                all_candidates = {company_id for company_id, _, _ in entries}
                valid = {
                    company_id
                    for company_id, vf, vt in entries
                    if _valid_at((company_id, vf, vt), mention.asof)
                }
                if len(valid) == 1:
                    company_id = next(iter(valid))
                    record(
                        "ledger",
                        rung_input,
                        "resolved",
                        company_id=company_id,
                        **({} if dated else {"note": NO_VALIDITY_DATES_NOTE}),
                    )
                    return finish(company_id, "ledger", None, [company_id])
                if len(valid) > 1:
                    record(
                        "ledger",
                        rung_input,
                        "ambiguous",
                        candidates=tuple(sorted(valid)),
                    )
                    record(
                        "absent",
                        {"ticker": ticker, "cik": mention.cik, "asof": asof_iso},
                        "ambiguous_ticker",
                    )
                    return finish(None, "absent", "ambiguous_ticker", valid)
                record(
                    "ledger",
                    rung_input,
                    "not_valid_at_asof",
                    candidates=tuple(sorted(all_candidates)),
                )
                record(
                    "absent",
                    {"ticker": ticker, "cik": mention.cik, "asof": asof_iso},
                    "not_listed_at_asof",
                )
                return finish(None, "absent", "not_listed_at_asof", all_candidates)
            record("ledger", rung_input, "not_found")

    # Rung 4: absent --------------------------------------------------------
    reason = "unknown_ticker" if ticker is not None else (
        "no_mention" if not mention.text.strip() else "name_only_mention"
    )
    record("absent", {"ticker": ticker, "cik": mention.cik, "asof": asof_iso}, reason)
    return finish(None, "absent", reason)


def absence_payload(resolution: IssuerResolution) -> dict:
    """Render an absent resolution as the frozen schema's absence payload.

    Targets ``$defs/owner_typed_absence_v1`` (schema line 554): the event
    templates require a non-nullable ``company_id``, and of the two absence
    defs only the owner one carries an identity-join reason
    (``unjoinable_filing_identity``, line 586).  The ladder's precise reason
    rides in ``detail``; built only from fields the schema has.

    Raises ``ValueError`` for a resolved resolution — there is nothing absent
    to render.
    """
    if resolution.company_id is not None:
        raise ValueError(
            f"resolution is not an absence: {resolution.company_id}"
        )
    reason = resolution.absence_reason
    if reason not in ABSENCE_REASONS:
        raise ValueError(f"unknown absence reason: {reason!r}")
    absent_input: dict[str, Any] | None = None
    for rung in resolution.receipt.get("rungs", ()):
        if rung.get("rung") == "absent":
            absent_input = rung.get("input")
    detail_ticker = ""
    detail_asof = ""
    if isinstance(absent_input, dict):
        if absent_input.get("ticker"):
            detail_ticker = f"; ticker {absent_input['ticker']}"
        if absent_input.get("asof"):
            detail_asof = f"; as of {absent_input['asof']}"
    detail = f"issuer identity unresolved: {reason}{detail_ticker}{detail_asof}"
    return {
        "schema": "typed_absence.v1",
        "authority": "context_only",
        "reason": "unjoinable_filing_identity",
        "subject": "company_id",
        "detail": detail[:240],
        "missing_fields": ["company_id"],
        "event_id": None,
        "document_id": None,
    }


def resolve_batch(
    mentions: Iterable[Mention],
    *,
    registry: IssuerRegistry | None = None,
    ledger: Mapping[str, tuple[tuple[str, date | None, date | None], ...]] | None = None,
) -> tuple[list[IssuerResolution], dict]:
    """Resolve many mentions in input order and count the outcomes.

    The counts dict has ``by_rung`` (every rung in :data:`RUNGS`) and
    ``by_absence_reason`` (every reason in :data:`ABSENCE_REASONS`), each key
    present with ``0`` when unused — the freeze §6 "counted, never dropped"
    guarantee in one shape.
    """
    resolutions = [
        resolve_mention(mention, registry=registry, ledger=ledger)
        for mention in mentions
    ]
    by_rung = {rung: 0 for rung in RUNGS}
    by_absence_reason = {reason: 0 for reason in ABSENCE_REASONS}
    for resolution in resolutions:
        by_rung[resolution.rung] += 1
        if resolution.absence_reason is not None:
            by_absence_reason[resolution.absence_reason] += 1
    return resolutions, {"by_rung": by_rung, "by_absence_reason": by_absence_reason}
