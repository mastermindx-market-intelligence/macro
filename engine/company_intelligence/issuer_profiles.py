"""Per-issuer extraction profiles for ``event_workspace.v1`` (IMCE A5A).

``event_workspace_build.build_event_workspace`` is generic: identity, filing
binding, GAAP figure extraction (``engine.earnings_release.figures``),
lifecycle, and publication all apply the same way to every issuer.  The one
place a real issuer difference belongs is FACT/CLAIM EXTRACTION — what to read
out of the release body and (if held) the transcript — and that seam is what
this module owns.  An :class:`IssuerProfile` bundles exactly two callables:

* ``extract_release_facts`` — additional ``event_fact.v1`` entries read out of
  the bound Exhibit 99.1 body (or its typed absence).
* ``extract_transcript_claims`` — ``event_claim.v1`` entries read out of the
  held earnings-call transcript (or its typed absence).

No generic code branches on ticker (E3C prior-art law — see
``engine/company_intelligence/event_workspace_build.py``).  ``apple_profile()``
reproduces the pre-A5A ``_GLANCE_SPANS`` transcript-claims behavior with zero
output change; the four homebuilder profiles below are new for A5A.

Every homebuilder's registered CIK is sourced from the accreting
``data/edgar/ticker_cik_ledger.json`` ledger (as of ``origin/main`` pin
``0e57b06d8e23``: DHI 882184, PHM 822416, KBH 795266, TOL 794170) and frozen
into code here — identity is code, not a runtime ``data/`` dependency.  Each
issuer's primary-listing MIC and ``fiscal_year_end_month`` were verified
against that issuer's own SEC ``submissions`` JSON (``exchanges`` /
``fiscalYearEnd`` fields); the exact receipts are quoted in the PR body.

Homebuilder fact extraction never infers a missing figure from prose and
never derives one figure from another by arithmetic (docket law, restated in
the A5A commission).  Every numeric fact is read out of a literal, uniquely
addressable span in the release body via the SAME byte-replayable receipt
machinery ``engine.earnings_release.figures`` already uses for GAAP figures
(``engine.earnings_release.receipts.receipt_for_literal``), scoped to the
containing disclosure block or table cell so that a repeated number elsewhere
in a long release cannot collide with it.  Where a fact is not present, or not
uniquely locatable, the profile emits a :class:`TypedAbsence` from the closed
``ABSENCE_REASONS`` vocabulary instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Callable, Mapping, Sequence

from ..earnings_release.binding import BoundRelease
from ..earnings_release.receipts import ReceiptError, SpanReceipt, receipt_for_literal
from ..fundamental_forensics.disclosure_diff import BlockKind, DisclosureBlock
from .documents import text_span
from .event_workspace import _absence, _span_payload_from_transcript
from .identity import IssuerIdentity, ListingAlias, company_id_for_cik


# ─────────────────────────────────────────────────────────────────────────────
# Issuer identity.
#
# CIKs: data/edgar/ticker_cik_ledger.json @ origin/main 0e57b06d8e23 —
#   "DHI": 882184, "PHM": 822416, "KBH": 795266, "TOL": 794170.
# MIC + fiscal_year_end_month: each issuer's SEC submissions JSON
# (https://data.sec.gov/submissions/CIK<cik>.json), `exchanges` and
# `fiscalYearEnd` fields, fetched 2026-08-22 — receipts quoted in the PR body:
#   DHI: exchanges=["NYSE"], fiscalYearEnd="0930" (September)
#   PHM: exchanges=["NYSE"], fiscalYearEnd="1231" (December)
#   KBH: exchanges=["NYSE"], fiscalYearEnd="1130" (November)
#   TOL: exchanges=["NYSE"], fiscalYearEnd="1031" (October)
# NYSE's MIC is XNYS.
# ─────────────────────────────────────────────────────────────────────────────

DHI_CIK = "0000882184"
PHM_CIK = "0000822416"
KBH_CIK = "0000795266"
TOL_CIK = "0000794170"

# Semiconductor witnesses (T05a).  CIKs verified 2026-09-24 against
# data.sec.gov submissions JSON for the named registrant.
TSM_CIK = "0001046179"  # Taiwan Semiconductor Manufacturing Company Limited
ON_CIK = "0001097864"  # ON Semiconductor Corporation

# TSM stays OUT OF FIF (``engine.fundamental_forensics.metric_registry``):
# ALLOWED_FORMS is 10-K/10-K/A/10-Q/10-Q/A, ALLOWED_TAXONOMIES is us-gaap/dei,
# ALLOWED_UNITS is USD/shares/ratio — TSM's IFRS/TWD/20-F combination is
# none of those.  This sentinel is what a later surface renders — never an
# inferred metric, never a widened registry constant.
TSM_FIF_GAP = "ifrs_twd_20f_outside_fif_registry"

HOMEBUILDER_TICKERS: tuple[str, ...] = ("DHI", "PHM", "KBH", "TOL")


def dhi_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(DHI_CIK),
        display_name="D.R. Horton, Inc.",
        fiscal_year_end_month=9,
        reporting_currency="USD",
        listings=(
            ListingAlias(ticker="DHI", mic="XNYS", share_class="common", trading_currency="USD", is_primary=True),
        ),
        external_ids={"cik": DHI_CIK},
    )


def phm_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(PHM_CIK),
        display_name="PulteGroup, Inc.",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            ListingAlias(ticker="PHM", mic="XNYS", share_class="common", trading_currency="USD", is_primary=True),
        ),
        external_ids={"cik": PHM_CIK},
    )


def kbh_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(KBH_CIK),
        display_name="KB Home",
        fiscal_year_end_month=11,
        reporting_currency="USD",
        listings=(
            ListingAlias(ticker="KBH", mic="XNYS", share_class="common", trading_currency="USD", is_primary=True),
        ),
        external_ids={"cik": KBH_CIK},
    )


def tol_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(TOL_CIK),
        display_name="Toll Brothers, Inc.",
        fiscal_year_end_month=10,
        reporting_currency="USD",
        listings=(
            ListingAlias(ticker="TOL", mic="XNYS", share_class="common", trading_currency="USD", is_primary=True),
        ),
        external_ids={"cik": TOL_CIK},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Semiconductor witnesses (T05a).
#
# TSM — Taiwan Semiconductor Manufacturing Company Limited; CIK 0001046179;
# foreign private issuer (Form 6-K results, annual report Form 20-F);
# entityType "other"; fiscal year end 12-31; reports NT$ (TWD) with a USD
# restatement; guidance is in USD with an explicit FX assumption.
# Listing attested by the FY2025 20-F cover filed 2026-04-16 (accession
# 0001628280-26-025362).  No TWSE "2330" alias is registered — the
# estate never sourced that venue, so a listing cannot be asserted for it.
# ─────────────────────────────────────────────────────────────────────────────

def tsm_issuer() -> IssuerIdentity:
    """TSMC's SEC-attested identity as of the FY2025 20-F cover filing.

    Listing ``valid_from = date(2026, 4, 16)`` is attested by the FY2025
    20-F cover (accession 0001628280-26-025362, filed 2026-04-16).  No
    earlier eligibility is asserted.
    """
    return IssuerIdentity(
        company_id=company_id_for_cik(TSM_CIK),
        display_name="Taiwan Semiconductor Manufacturing Company Limited",
        fiscal_year_end_month=12,
        reporting_currency="TWD",
        listings=(
            ListingAlias(
                ticker="TSM",
                mic="XNYS",
                share_class="ADR",
                trading_currency="USD",
                is_primary=True,
                valid_from=date(2026, 4, 16),
            ),
        ),
        issuer_kind="foreign_private_issuer",
        external_ids={
            "cik": TSM_CIK,
            "sec_entity_type": "other",
            "annual_report_form": "20-F",
            "results_form": "6-K",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# ON — ON Semiconductor Corporation; CIK 0001097864; domestic filer
# (8-K/10-Q/10-K); entityType "operating"; fiscal year end 12-31 on a
# 52/53-week calendar (Q1-2026 ended 2026-04-03, Q2-2026 ended 2026-07-03);
# reports USD.  Listing attested by the Q1-2026 results 8-K filing date
# 2026-05-04 (accession 0001140361-26-018868); the 10-K filing date is
# not derivable offline.
# ─────────────────────────────────────────────────────────────────────────────

def on_issuer() -> IssuerIdentity:
    """onsemi's SEC-attested identity as of the Q1-2026 results 8-K filing.

    Listing ``valid_from = date(2026, 5, 4)`` is attested by the Q1-2026
    results 8-K filing date (accession 0001140361-26-018868, filed
    2026-05-04).  The 10-K filing date is not derivable offline.
    """
    return IssuerIdentity(
        company_id=company_id_for_cik(ON_CIK),
        display_name="ON Semiconductor Corporation",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            ListingAlias(
                ticker="ON",
                mic="XNAS",
                share_class="common",
                trading_currency="USD",
                is_primary=True,
                valid_from=date(2026, 5, 4),
            ),
        ),
        issuer_kind="domestic_52_53_week",
        external_ids={
            "cik": ON_CIK,
            "sec_entity_type": "operating",
            "annual_report_form": "10-K",
            "results_form": "8-K",
            "fiscal_calendar": "52_53_week",
        },
    )


_SEMICONDUCTOR_ISSUER_FACTORIES: dict[str, Callable[[], IssuerIdentity]] = {
    "TSM": tsm_issuer,
    "ON": on_issuer,
}


_HOMEBUILDER_ISSUER_FACTORIES: dict[str, Callable[[], IssuerIdentity]] = {
    "DHI": dhi_issuer,
    "PHM": phm_issuer,
    "KBH": kbh_issuer,
    "TOL": tol_issuer,
}


# ``production_registry()`` (apple_issuer() + the four constructors above)
# lives in ``event_workspace.py`` per the A5A file ownership split; it does a
# deferred import of this module to avoid a module-load cycle (this module
# imports private helpers from ``event_workspace`` for the Apple profile).


# ─────────────────────────────────────────────────────────────────────────────
# IssuerProfile — the generic/issuer-specific extraction seam.
# ─────────────────────────────────────────────────────────────────────────────

ReleaseFactExtractor = Callable[..., list[dict[str, Any]]]
TranscriptClaimExtractor = Callable[..., list[dict[str, Any]]]
GuidanceExtractor = Callable[..., list[dict[str, Any]]]


def _no_guidance(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


@dataclass(frozen=True)
class IssuerProfile:
    """Three callables; nothing here inspects ``ticker`` to change behavior.

    ``extract_release_facts(*, bound, document_id, event_id)`` returns
    additional ``event_fact.v1`` entries.

    ``extract_transcript_claims(*, segments, document_id, body_sha256,
    event_id)`` returns ``event_claim.v1`` entries (``[]`` when the issuer's
    profile does not read the transcript, e.g. a homebuilder with no held
    call).

    ``extract_guidance(*, segments, document_id, body_sha256, event_id)``
    returns ``guidance_item.v1`` entries (F6 — this used to be a hardcoded
    Apple-only block sitting in generic ``build_event_workspace`` code:
    fixed segment index, fixed literal, fixed 9.0/11.0 bounds).  Defaults to
    ``[]`` so every homebuilder profile gets it for free.
    """

    ticker: str
    extract_release_facts: ReleaseFactExtractor
    extract_transcript_claims: TranscriptClaimExtractor
    extract_guidance: GuidanceExtractor = _no_guidance


# ─────────────────────────────────────────────────────────────────────────────
# Apple profile — the pre-A5A ``_GLANCE_SPANS`` transcript-claims behavior,
# moved here unchanged.  Output is byte-identical to before A5A.
# ─────────────────────────────────────────────────────────────────────────────

_AAPL_GLANCE_SPANS: tuple[tuple[str, int, str, str, str], ...] = (
    ("claim_revenue_lede", 2, "$109.4 billion in revenue, up 16%", "numeric", "revenue"),
    ("claim_iphone_yoy", 5, "up 22% from a year ago", "numeric", "iphone_revenue_yoy_pct"),
    ("claim_mac_yoy", 6, "growing an impressive 29%", "numeric", "mac_revenue_yoy_pct"),
    ("claim_services_revenue", 11, "$30.7 billion", "numeric", "services_revenue"),
    ("claim_install_base", 17, "over two and a half billion", "numeric", "active_devices"),
    ("claim_demand_vs_supply", 55, "remarkably better than we thought", "quote", "demand_vs_supply"),
    ("claim_memory_flood", 65, "100-year flood", "quote", "memory"),
    (
        "claim_fx_headwind",
        26,
        "two and a half percentage points to the year-over-year total company growth rate",
        "numeric",
        "fx_yoy_headwind",
    ),
)


def _apple_extract_release_facts(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


def _apple_extract_transcript_claims(
    *,
    segments: Sequence[Mapping[str, Any]],
    document_id: str,
    body_sha256: str,
    event_id: str,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for fact_id, index, literal, kind, metric in _AAPL_GLANCE_SPANS:
        if index >= len(segments):
            payload = None
            segment: Mapping[str, Any] = {}
        else:
            segment = segments[index]
            payload = _span_payload_from_transcript(
                document_id=document_id,
                body_sha256=body_sha256,
                segment_index=index,
                segment=segment,
                literal=literal,
            )
        if payload is None:
            claims.append({
                "schema": "event_claim.v1",
                "claim_id": fact_id,
                "text": literal,
                "kind": kind,
                "metric": metric,
                "typed_absence": _absence(
                    reason="no_span_addressable_evidence",
                    subject=metric,
                    detail=f"literal {literal!r} is not uniquely addressable in the transcript",
                    event_id=event_id,
                    document_id=document_id,
                ),
            })
            continue
        claims.append({
            "schema": "event_claim.v1",
            "claim_id": fact_id,
            "text": literal,
            "kind": kind,
            "metric": metric,
            "speaker": segment.get("speaker"),
            "role": segment.get("role") or None,
            "evidence_spans": [payload],
            "source_span": payload,
        })
    return claims


def _apple_extract_guidance(
    *,
    segments: Sequence[Mapping[str, Any]],
    document_id: str,
    body_sha256: str,
    event_id: str,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    """The pre-A5A hardcoded guidance block, moved here unchanged (F6)."""
    if len(segments) <= 26:
        return []
    guide_literal = "grow between 9%-11% year-over-year"
    guide_span = _span_payload_from_transcript(
        document_id=document_id,
        body_sha256=body_sha256,
        segment_index=26,
        segment=segments[26],
        literal=guide_literal,
    )
    if guide_span is None:
        return []
    return [{
        "schema": "guidance_item.v1",
        "metric": "revenue_yoy_pct",
        "low": 9.0,
        "high": 11.0,
        "unit": "percent",
        "horizon": "FY2026 Q4",
        "status": "introduced",
        "source_span": guide_span,
    }]


def apple_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="AAPL",
        extract_release_facts=_apple_extract_release_facts,
        extract_transcript_claims=_apple_extract_transcript_claims,
        extract_guidance=_apple_extract_guidance,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Homebuilder release-fact extraction — shared receipt/absence plumbing.
# ─────────────────────────────────────────────────────────────────────────────

def _release_span_payload(*, document_id: str, bound: BoundRelease, receipt: SpanReceipt) -> dict[str, Any]:
    span = text_span(
        document_id=document_id,
        document_version=1,
        body_sha256=bound.revision.source_sha256,
        segment_index=0,
        segment_text=bound.source,
        start_byte=receipt.byte_start,
        end_byte=receipt.byte_end,
        text=receipt.span_text,
        rights_profile="rp_public_primary_v1",
    )
    return span.to_payload()


def _fact_present(
    *,
    fact_id: str,
    event_id: str,
    metric: str,
    value: Any,
    unit: str | None,
    period: str | None,
    basis: str,
    document_id: str,
    bound: BoundRelease,
    receipt: SpanReceipt,
    currency: str | None = None,
    provenance: str | None = None,
) -> dict[str, Any]:
    # ``currency`` is additive: a profile whose guidance items carry a
    # currency (TSM/ON) states the same closed token on its release facts so
    # the T06 comparison law (guidance_history._classify_prior_vs_actual,
    # None vs non-None is a mismatch) compares like with like. Homebuilder
    # facts pass nothing and their payload is byte-identical.
    payload = {
        "schema": "event_fact.v1",
        "fact_id": fact_id,
        "event_id": event_id,
        "metric": metric,
        "value": value,
        "unit": unit,
        "period": period,
        "basis": basis,
        "source_span": _release_span_payload(document_id=document_id, bound=bound, receipt=receipt),
    }
    if currency is not None:
        payload["currency"] = currency
    if provenance is not None:
        # Non-compared prose about WHERE the figure was read (the T06 law
        # compares metric/unit/basis/currency/perimeter/definition only).
        payload["provenance"] = provenance
    return payload


def _fact_absent(*, fact_id: str, event_id: str, metric: str, detail: str, document_id: str,
                 reason: str = "no_span_addressable_evidence") -> dict[str, Any]:
    return {
        "schema": "event_fact.v1",
        "fact_id": fact_id,
        "event_id": event_id,
        "metric": metric,
        "typed_absence": _absence(
            reason=reason,
            subject=metric,
            detail=detail,
            event_id=event_id,
            document_id=document_id,
        ),
    }


def _literal_receipt(bound: BoundRelease, *, search_start: int, search_end: int, literal: str) -> SpanReceipt | None:
    try:
        return receipt_for_literal(
            source=bound.source,
            source_sha256=bound.revision.source_sha256,
            search_start=search_start,
            search_end=search_end,
            literal=literal,
        )
    except ReceiptError:
        return None


def _find_paragraph_containing(blocks: Sequence[DisclosureBlock], needle: str) -> DisclosureBlock | None:
    lower = needle.lower()
    for block in blocks:
        if lower in block.text.lower():
            return block
    return None


def _find_table_after_heading(blocks: Sequence[DisclosureBlock], heading: str) -> DisclosureBlock | None:
    lower = heading.lower()
    for block in blocks:
        if block.kind is BlockKind.TABLE and block.table is not None and block.table.rows:
            probe = " ".join(cell.text for row in block.table.rows[:3] for cell in row)
            if lower in probe.lower():
                return block
    return None


def _find_row_by_label(blocks: Sequence[DisclosureBlock], label: str, *, block_contains: str | None = None):
    """The row whose first cell equals *label*, optionally scoped to a block
    whose own text also contains *block_contains* (case-insensitive).

    The scope is what tells TOL's quarterly "Net Signed Contracts" row apart
    from the identically-labelled row in its nine-month table (F12): each
    lives in its own table block, and only the quarterly one's own caption
    says "three months" (see ``_dhi_extract_release_facts`` neighbors below
    for the analogous header-row check used where two periods share ONE
    table).
    """
    lower = label.strip().lower()
    required = block_contains.lower() if block_contains else None
    for block in blocks:
        if block.kind is BlockKind.TABLE and block.table is not None:
            if required is not None and required not in block.text.lower():
                continue
            for row in block.table.rows:
                if row and row[0].text.strip().lower() == lower:
                    return row
    return None


def _nonblank_cells(row) -> list:
    return [cell for cell in row if cell.text.strip() not in ("", "$")]


def _period_label(fiscal_period: Any) -> str | None:
    calendar_end = getattr(fiscal_period, "calendar_end", None)
    return calendar_end.isoformat() if calendar_end else None


# Every YTD phrasing observed or plausible across the four issuers' quarters
# (DHI/PHM/KBH: "Six/Nine Months Ended"; a full-year release would say "Twelve
# Months Ended" or "Year Ended").  Matched as a SET, not one hardcoded string
# per issuer (NEW-A) -- Q1 tables carry no YTD column of ANY kind at all,
# because there is nothing to accumulate yet, and a single hardcoded marker
# (e.g. "Nine Months Ended" for DHI) falsely fails to bind DHI's own Q2 table,
# which says "Six Months Ended".
_YTD_MARKERS: tuple[str, ...] = ("Six Months Ended", "Nine Months Ended", "Twelve Months Ended", "Year Ended")


def _quarterly_precedes_ytd(
    table_block: DisclosureBlock, *, quarterly_marker: str, ytd_markers: Sequence[str] = _YTD_MARKERS
) -> bool:
    """F12 binding check, widened for Q1 tables (NEW-A).

    Binds when EITHER:

    (a) the quarterly marker is present somewhere in the block and NO YTD
        marker (from the closed set above) occurs ANYWHERE in the block --
        a genuine Q1 shape, where the table has only a quarterly column
        because there is no year-to-date figure yet (measured: KBH FY2026 Q1
        and PHM FY2026 Q1 real filings carry no YTD column at all); or

    (b) a header row states the quarterly marker in a cell that comes before
        a DIFFERENT cell stating one of the YTD markers.

    A caption line that happens to mention both phrases in ONE cell (e.g.
    KBH's "For the Three Months and Six Months Ended...") does not count
    toward (b) -- only a row where the two markers sit in separate cells
    binds the positions the caller is about to read.  Returning ``False``
    means a reshaped or reordered table mints a typed absence instead of a
    wrong value under a still-valid byte receipt.
    """
    q_lower = quarterly_marker.lower()
    ytd_lowers = [marker.lower() for marker in ytd_markers]
    has_quarterly_anywhere = False
    has_ytd_anywhere = False
    for row in table_block.table.rows:
        for cell in row:
            cell_lower = cell.text.lower()
            if q_lower in cell_lower:
                has_quarterly_anywhere = True
            if any(ytd_lower in cell_lower for ytd_lower in ytd_lowers):
                has_ytd_anywhere = True
    if not has_ytd_anywhere:
        # Rule (a): a Q1-shaped table (or one with no quarterly marker at
        # all, which fails closed via ``has_quarterly_anywhere`` being False).
        return has_quarterly_anywhere
    # Rule (b): a YTD marker exists somewhere in the block, so a genuine
    # multi-period table is in play -- require the two markers to sit in
    # separate cells of the SAME row to bind column order.
    for row in table_block.table.rows:
        q_idx = next((i for i, cell in enumerate(row) if q_lower in cell.text.lower()), None)
        y_idx = next(
            (i for i, cell in enumerate(row) if any(ytd_lower in cell.text.lower() for ytd_lower in ytd_lowers)),
            None,
        )
        if q_idx is not None and y_idx is not None and q_idx != y_idx:
            return q_idx < y_idx
    return False


def _split_disjoint_clauses(full_text: str, marker: str) -> tuple[str, str] | None:
    """Split *full_text* into two DISJOINT literal windows at *marker* (F3).

    Two different byte ranges even when the current and prior VALUES are
    numerically equal: the receipt that proves one can never collide with
    the receipt that proves the other, because *marker* occurs once in the
    matched clause (verified by the caller's own regex construction).
    """
    idx = full_text.find(marker)
    if idx < 0:
        return None
    return full_text[:idx].rstrip(), full_text[idx:].rstrip()


# ─────────────────────────────────────────────────────────────────────────────
# DHI — cancellation rate = cancelled sales orders / gross sales orders.
# Verified against DHI's real FY2026 Q3 8-K, accession 0000882184-26-000092
# (filed 2026-07-21), Exhibit 99.1 — see tests/fixtures/company_intelligence.
# ─────────────────────────────────────────────────────────────────────────────

# Two real net-orders verb phrasings observed across DHI quarters: a bare
# "totaled"/"of" (flat quarter) and an "increased/decreased NN% to" (F2 —
# DHI FY2026 Q2's real "increased 11% to 24,992 homes" was previously missed).
_DHI_NET_ORDERS_RE = re.compile(
    r"Net sales orders (?:totaled|of|(?:increased|decreased) \d+% to) ([\d,]+) homes with an order value of "
    r"\$[\d.,]+ (?:billion|million)"
)
# Two real cancellation phrasings: distinct values ("X% compared to Y%") and
# equal values ("X%, consistent with the prior year quarter" — DHI FY2026 Q2).
_DHI_CANCELLATION_COMPARED_RE = re.compile(
    r"cancellation rate \(([^)]+)\) for the quarter was \d+(?:\.\d+)?% compared to \d+(?:\.\d+)?% "
    r"in the prior year quarter"
)
_DHI_CANCELLATION_CONSISTENT_RE = re.compile(
    r"cancellation rate \(([^)]+)\) for the quarter was \d+(?:\.\d+)?%, consistent with the prior year quarter"
)
_PCT_RE = re.compile(r"\d+(?:\.\d+)?%")


def _dhi_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    blocks = bound.document.blocks
    facts: list[dict[str, Any]] = []

    # (i) net_orders current period.
    para = _find_paragraph_containing(blocks, "net sales orders")
    current_fact: dict[str, Any] | None = None
    if para is not None:
        match = _DHI_NET_ORDERS_RE.search(para.text)
        if match is not None:
            receipt = _literal_receipt(
                bound, search_start=para.source_span.char_start, search_end=para.source_span.char_end,
                literal=match.group(0),
            )
            if receipt is not None:
                current_fact = _fact_present(
                    fact_id="fact_net_orders_current", event_id=event_id, metric="net_orders",
                    value=int(match.group(1).replace(",", "")), unit="homes", period=period,
                    basis="DHI quarterly net sales orders (homes), as disclosed in Exhibit 99.1",
                    document_id=document_id, bound=bound, receipt=receipt,
                )
    facts.append(current_fact or _fact_absent(
        fact_id="fact_net_orders_current", event_id=event_id, metric="net_orders",
        detail="net sales orders is not uniquely addressable in Exhibit 99.1", document_id=document_id,
    ))

    # (ii) net_orders same-basis prior-year comparator — the NET SALES ORDERS
    # table's unlabeled total row, homes column, prior-year quarter.  F12:
    # only trust the column positions if the table's own header confirms
    # "Three Months Ended" precedes a YTD period marker, or (a genuine Q1
    # shape) carries no YTD marker at all (NEW-A).
    prior_fact: dict[str, Any] | None = None
    table_block = _find_table_after_heading(blocks, "NET SALES ORDERS")
    bound_columns = table_block is not None and table_block.table.rows and _quarterly_precedes_ytd(
        table_block, quarterly_marker="Three Months Ended",
    )
    if bound_columns:
        total_row = table_block.table.rows[-1]
        cells = _nonblank_cells(total_row)
        if len(cells) >= 3:
            cell = cells[2]
            receipt = _literal_receipt(
                bound, search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
                literal=cell.text,
            )
            if receipt is not None:
                try:
                    value = int(cell.text.replace(",", ""))
                except ValueError:
                    value = None
                if value is not None:
                    prior_fact = _fact_present(
                        fact_id="fact_net_orders_prior_year", event_id=event_id, metric="net_orders",
                        value=value, unit="homes", period="prior_year_same_quarter",
                        basis="DHI same-quarter-prior-year net sales orders (homes), as disclosed in Exhibit 99.1",
                        document_id=document_id, bound=bound, receipt=receipt,
                    )
    facts.append(prior_fact or _fact_absent(
        fact_id="fact_net_orders_prior_year", event_id=event_id, metric="net_orders",
        detail=(
            "prior-year same-quarter net sales orders total is not uniquely addressable in Exhibit "
            "99.1, or the table's column layout could not be bound to the quarterly period"
        ),
        document_id=document_id,
    ))

    # (iii)/(iv)/(v) cancellation rate current, prior-year comparator, and the
    # stated denominator convention — all three cite the same disclosure
    # sentence.  F3: receipts are minted over DISJOINT clauses (never a bare
    # "NN%"), so a current==prior quarter never collides and never drops a
    # fact.
    cancel_para = _find_paragraph_containing(blocks, "cancellation rate")
    current_receipt = prior_receipt = denom_receipt = None
    current_pct = prior_pct = denom_text = None
    used_equality_clause = False
    if cancel_para is not None:
        compared = _DHI_CANCELLATION_COMPARED_RE.search(cancel_para.text)
        consistent = None if compared is not None else _DHI_CANCELLATION_CONSISTENT_RE.search(cancel_para.text)
        if compared is not None:
            full = compared.group(0)
            denom_text = compared.group(1)
            pcts = _PCT_RE.findall(full)
            current_pct, prior_pct = pcts[0][:-1], pcts[1][:-1]
            split = _split_disjoint_clauses(full, "compared to")
            if split is not None:
                current_clause, prior_clause = split
                current_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=current_clause,
                )
                prior_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=prior_clause,
                )
        elif consistent is not None:
            full = consistent.group(0)
            denom_text = consistent.group(1)
            pcts = _PCT_RE.findall(full)
            current_pct = pcts[0][:-1]
            prior_pct = current_pct
            used_equality_clause = True
            # The current fact keeps a DISJOINT clause ending at its own
            # digits (no inference issue: it has a real "16%" in its span).
            split = _split_disjoint_clauses(full, ", consistent with the prior year quarter")
            if split is not None:
                current_clause, _equality_fragment = split
                current_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=current_clause,
                )
            # The prior-year fact is PRESENT only when its OWN receipt spans
            # the FULL clause -- both the stated current digits AND the
            # equality assertion together.  A receipt over the equality
            # fragment alone ("consistent with the prior year quarter") cites
            # no number and would be prose inference, which is forbidden; the
            # full clause is what the document actually asserts ("16%, ...
            # consistent with the prior year quarter" IS the prior value's
            # only source-stated evidence).
            prior_receipt = _literal_receipt(
                bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                literal=full,
            )
        if denom_text is not None:
            denom_receipt = _literal_receipt(
                bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                literal=denom_text,
            )

    basis_text = "cancelled sales orders divided by gross sales orders (DHI convention)"
    prior_year_basis = (
        f"{basis_text}; prior-year value stated by explicit equality with the current-quarter figure "
        "in the same clause"
    ) if used_equality_clause else basis_text
    prior_absence_detail = (
        "the release states cancellation-rate consistency with the prior year quarter, but its own "
        "clause does not carry a uniquely addressable prior-year value"
    ) if used_equality_clause else "prior-year cancellation rate is not present or not uniquely addressable in Exhibit 99.1"
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_current", event_id=event_id, metric="cancellation_rate",
            value=float(current_pct), unit="percent", period=period, basis=basis_text,
            document_id=document_id, bound=bound, receipt=current_receipt,
        )
        if current_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_current", event_id=event_id, metric="cancellation_rate",
            detail="cancellation rate is not present or not uniquely addressable in Exhibit 99.1",
            document_id=document_id,
        )
    )
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_prior_year", event_id=event_id, metric="cancellation_rate",
            value=float(prior_pct), unit="percent", period="prior_year_same_quarter", basis=prior_year_basis,
            document_id=document_id, bound=bound, receipt=prior_receipt,
        )
        if prior_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_prior_year", event_id=event_id, metric="cancellation_rate",
            detail=prior_absence_detail,
            document_id=document_id,
        )
    )
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            value=denom_text, unit=None, period=None, basis=basis_text,
            document_id=document_id, bound=bound, receipt=denom_receipt,
        )
        if denom_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            detail="the stated cancellation denominator convention is not present in Exhibit 99.1",
            document_id=document_id,
        )
    )
    return facts


def dhi_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="DHI",
        extract_release_facts=_dhi_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# PHM — net new orders by region table; PulteGroup's EX-99.1 press release
# does not always disclose a cancellation rate (verified: its FY2026 Q2 8-K,
# accession 0000822416-26-000034, carries none — a genuine typed absence, not
# a missed pattern).  The optional denominator-clause group covers a quarter
# where PulteGroup DOES spell out the convention (e.g. "as a percentage of
# gross orders"); real fixtures only exercise the no-denominator branch,
# synthetic text exercises the denominator-present branch (F10).
# ─────────────────────────────────────────────────────────────────────────────

_PHM_CANCELLATION_RE = re.compile(
    r"cancellation rate(?:,? as a percent(?:age)? of ([a-z][a-z ]*?),?)? was \d+(?:\.\d+)?%,? compared to \d+(?:\.\d+)?%"
)


def _phm_section_total_row(table_block: DisclosureBlock, section_label: str):
    rows = table_block.table.rows
    in_section = False
    for row in rows:
        first = row[0].text.strip() if row else ""
        if not in_section:
            if first.lower() == section_label.lower():
                in_section = True
            continue
        if first == "" and any(cell.text.strip() not in ("", "$") for cell in row):
            return row
    return None


def _phm_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    blocks = bound.document.blocks
    facts: list[dict[str, Any]] = []

    table_block = _find_paragraph_table(blocks, "Net new orders - units")
    current_fact = prior_fact = None
    # NEW-A: a Q1 filing carries no YTD column at all (nothing to accumulate
    # yet) -- _quarterly_precedes_ytd() binds on that shape too, not only
    # when a YTD marker is present and ordered after the quarterly one.
    bound_columns = table_block is not None and _quarterly_precedes_ytd(
        table_block, quarterly_marker="Three Months Ended",
    )
    if bound_columns:
        total_row = _phm_section_total_row(table_block, "Net new orders - units")
        if total_row is not None:
            cells = _nonblank_cells(total_row)
            if len(cells) >= 2:
                for idx, fact_id, basis_label, period_label in (
                    (0, "fact_net_orders_current", "PulteGroup quarterly net new orders (homes), as disclosed in Exhibit 99.1", period),
                    (1, "fact_net_orders_prior_year", "PulteGroup same-quarter-prior-year net new orders (homes), as disclosed in Exhibit 99.1", "prior_year_same_quarter"),
                ):
                    cell = cells[idx]
                    receipt = _literal_receipt(
                        bound, search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
                        literal=cell.text,
                    )
                    if receipt is None:
                        continue
                    try:
                        value = int(cell.text.replace(",", ""))
                    except ValueError:
                        continue
                    fact = _fact_present(
                        fact_id=fact_id, event_id=event_id, metric="net_orders", value=value, unit="homes",
                        period=period_label, basis=basis_label, document_id=document_id, bound=bound, receipt=receipt,
                    )
                    if idx == 0:
                        current_fact = fact
                    else:
                        prior_fact = fact
    facts.append(current_fact or _fact_absent(
        fact_id="fact_net_orders_current", event_id=event_id, metric="net_orders",
        detail=(
            "net new orders is not uniquely addressable in Exhibit 99.1, or the table's column "
            "layout could not be bound to the quarterly period"
        ),
        document_id=document_id,
    ))
    facts.append(prior_fact or _fact_absent(
        fact_id="fact_net_orders_prior_year", event_id=event_id, metric="net_orders",
        detail=(
            "prior-year same-quarter net new orders total is not uniquely addressable in Exhibit "
            "99.1, or the table's column layout could not be bound to the quarterly period"
        ),
        document_id=document_id,
    ))

    # F3: receipts over DISJOINT clauses either side of "compared to", never a
    # bare "NN%" — a current==prior quarter never collides.  F10: the
    # denominator fact has a genuine present path when the sentence states
    # one (synthetic-text tested; real fixtures exercise the absence path).
    cancel_para = _find_paragraph_containing(blocks, "cancellation rate")
    current_receipt = prior_receipt = denom_receipt = None
    current_pct = prior_pct = denom_text = None
    basis_text = "PulteGroup cancellation rate convention, as stated in Exhibit 99.1"
    if cancel_para is not None:
        match = _PHM_CANCELLATION_RE.search(cancel_para.text)
        if match is not None:
            full = match.group(0)
            denom_text = match.group(1)
            pcts = _PCT_RE.findall(full)
            current_pct, prior_pct = pcts[0][:-1], pcts[1][:-1]
            split = _split_disjoint_clauses(full, "compared to")
            if split is not None:
                current_clause, prior_clause = split
                current_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=current_clause,
                )
                prior_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=prior_clause,
                )
            if denom_text is not None:
                denom_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=denom_text,
                )
    for fact_id, receipt, value, period_label, detail in (
        (
            "fact_cancellation_rate_current", current_receipt,
            float(current_pct) if current_pct else None, period,
            "cancellation rate is not disclosed in this Exhibit 99.1 (PulteGroup does not always state one)",
        ),
        (
            "fact_cancellation_rate_prior_year", prior_receipt,
            float(prior_pct) if prior_pct else None, "prior_year_same_quarter",
            "prior-year cancellation rate is not disclosed in this Exhibit 99.1",
        ),
    ):
        facts.append(
            _fact_present(
                fact_id=fact_id, event_id=event_id, metric="cancellation_rate", value=value, unit="percent",
                period=period_label, basis=basis_text, document_id=document_id, bound=bound, receipt=receipt,
            )
            if receipt is not None
            else _fact_absent(fact_id=fact_id, event_id=event_id, metric="cancellation_rate", detail=detail, document_id=document_id)
        )
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            value=denom_text, unit=None, period=None, basis=basis_text,
            document_id=document_id, bound=bound, receipt=denom_receipt,
        )
        if denom_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            detail=(
                "PulteGroup's cancellation rate sentence does not state an explicit denominator "
                "convention in this Exhibit 99.1 (or none is disclosed at all)"
            ),
            document_id=document_id,
        )
    )
    return facts


def _find_paragraph_table(blocks: Sequence[DisclosureBlock], row_label: str) -> DisclosureBlock | None:
    """A table block located by an exact row label rather than a heading probe."""
    lower = row_label.strip().lower()
    for block in blocks:
        if block.kind is BlockKind.TABLE and block.table is not None:
            for row in block.table.rows:
                if row and row[0].text.strip().lower() == lower:
                    return block
    return None


def phm_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="PHM",
        extract_release_facts=_phm_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# KBH — cancellation rate = percentage of gross orders.
# ─────────────────────────────────────────────────────────────────────────────

_KBH_CANCELLATION_RE = re.compile(
    r"cancellation rate as a percentage of gross orders was \d+(?:\.\d+)?%,? compared to \d+(?:\.\d+)?%"
)


def _kbh_total_row_after_label(blocks: Sequence[DisclosureBlock], section_label: str):
    """The "Total" row following *section_label*, plus its containing table
    block (needed by the caller for the F12 column-binding check)."""
    lower = section_label.strip().lower()
    for block in blocks:
        if block.kind is not BlockKind.TABLE or block.table is None:
            continue
        in_section = False
        for row in block.table.rows:
            first = row[0].text.strip() if row else ""
            if not in_section:
                if first.lower() == lower:
                    in_section = True
                continue
            if first.strip().lower() == "total":
                return row, block
        # keep scanning subsequent table blocks if this one had no section
    return None, None


def _kbh_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    blocks = bound.document.blocks
    facts: list[dict[str, Any]] = []

    total_row, kbh_table = _kbh_total_row_after_label(blocks, "Net orders:")
    current_fact = prior_fact = None
    # NEW-A: a Q1 filing carries no YTD column at all.
    bound_columns = (
        total_row is not None
        and kbh_table is not None
        and _quarterly_precedes_ytd(kbh_table, quarterly_marker="Three Months Ended")
    )
    if bound_columns:
        cells = [cell for cell in total_row[1:] if cell.text.strip() not in ("", "$")]
        if len(cells) >= 2:
            for idx, fact_id, basis_label, period_label in (
                (0, "fact_net_orders_current", "KB Home quarterly net orders (homes), as disclosed in Exhibit 99.1", period),
                (1, "fact_net_orders_prior_year", "KB Home same-quarter-prior-year net orders (homes), as disclosed in Exhibit 99.1", "prior_year_same_quarter"),
            ):
                cell = cells[idx]
                receipt = _literal_receipt(
                    bound, search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
                    literal=cell.text,
                )
                if receipt is None:
                    continue
                try:
                    value = int(cell.text.replace(",", ""))
                except ValueError:
                    continue
                fact = _fact_present(
                    fact_id=fact_id, event_id=event_id, metric="net_orders", value=value, unit="homes",
                    period=period_label, basis=basis_label, document_id=document_id, bound=bound, receipt=receipt,
                )
                if idx == 0:
                    current_fact = fact
                else:
                    prior_fact = fact
    facts.append(current_fact or _fact_absent(
        fact_id="fact_net_orders_current", event_id=event_id, metric="net_orders",
        detail=(
            "net orders is not uniquely addressable in Exhibit 99.1, or the table's column layout "
            "could not be bound to the quarterly period"
        ),
        document_id=document_id,
    ))
    facts.append(prior_fact or _fact_absent(
        fact_id="fact_net_orders_prior_year", event_id=event_id, metric="net_orders",
        detail=(
            "prior-year same-quarter net orders total is not uniquely addressable in Exhibit 99.1, "
            "or the table's column layout could not be bound to the quarterly period"
        ),
        document_id=document_id,
    ))

    # F3: receipts over DISJOINT clauses either side of "compared to" — never
    # a bare "NN%" that could collide when current == prior.
    cancel_para = _find_paragraph_containing(blocks, "cancellation rate as a percentage of gross orders")
    current_receipt = prior_receipt = denom_receipt = None
    current_pct = prior_pct = None
    if cancel_para is not None:
        match = _KBH_CANCELLATION_RE.search(cancel_para.text)
        if match is not None:
            full = match.group(0)
            pcts = _PCT_RE.findall(full)
            current_pct, prior_pct = pcts[0][:-1], pcts[1][:-1]
            split = _split_disjoint_clauses(full, "compared to")
            if split is not None:
                current_clause, prior_clause = split
                current_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=current_clause,
                )
                prior_receipt = _literal_receipt(
                    bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                    literal=prior_clause,
                )
            denom_receipt = _literal_receipt(
                bound, search_start=cancel_para.source_span.char_start, search_end=cancel_para.source_span.char_end,
                literal="as a percentage of gross orders",
            )
    basis_text = "cancellation rate as a percentage of gross orders (KB Home convention)"
    for fact_id, receipt, value, period_label, metric, detail in (
        (
            "fact_cancellation_rate_current", current_receipt, float(current_pct) if current_pct else None, period,
            "cancellation_rate", "cancellation rate is not present or not uniquely addressable in Exhibit 99.1",
        ),
        (
            "fact_cancellation_rate_prior_year", prior_receipt, float(prior_pct) if prior_pct else None,
            "prior_year_same_quarter", "cancellation_rate",
            "prior-year cancellation rate is not present or not uniquely addressable in Exhibit 99.1",
        ),
        (
            "fact_cancellation_rate_denominator", denom_receipt,
            "as a percentage of gross orders" if denom_receipt is not None else None,
            None, "cancellation_rate_basis",
            "the stated cancellation denominator convention is not present in Exhibit 99.1",
        ),
    ):
        facts.append(
            _fact_present(
                fact_id=fact_id, event_id=event_id, metric=metric, value=value,
                unit=("percent" if metric == "cancellation_rate" else None), period=period_label, basis=basis_text,
                document_id=document_id, bound=bound, receipt=receipt,
            )
            if receipt is not None
            else _fact_absent(fact_id=fact_id, event_id=event_id, metric=metric, detail=detail, document_id=document_id)
        )
    return facts


def kbh_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="KBH",
        extract_release_facts=_kbh_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# TOL — primary convention is signed contracts in the quarter; the
# beginning-quarter-backlog cancellation measure is a mandatory sensitivity
# fact carried alongside it (frozen spec item 4(vi)).
# ─────────────────────────────────────────────────────────────────────────────

_TOL_UNITS_RE = re.compile(r"([\d,]+) units")


def _tol_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    blocks = bound.document.blocks
    facts: list[dict[str, Any]] = []

    # F12: scope every lookup to the block whose OWN caption says "three
    # months" — TOL carries an identically-labelled nine-month table too, in
    # a SEPARATE block, and a document-order match on label alone would
    # silently pick either one.
    row = _find_row_by_label(blocks, "Net Signed Contracts", block_contains="three months")
    current_fact = prior_fact = None
    if row is not None:
        cells = [cell for cell in row[1:] if cell.text.strip() != ""]
        if len(cells) >= 2:
            for idx, fact_id, basis_label, period_label in (
                (0, "fact_net_orders_current", "Toll Brothers quarterly net signed contracts (units), as disclosed in Exhibit 99.1", period),
                (1, "fact_net_orders_prior_year", "Toll Brothers same-quarter-prior-year net signed contracts (units), as disclosed in Exhibit 99.1", "prior_year_same_quarter"),
            ):
                cell = cells[idx]
                units_match = _TOL_UNITS_RE.search(cell.text)
                if units_match is None:
                    continue
                literal = units_match.group(0)
                receipt = _literal_receipt(
                    bound, search_start=cell.source_span.char_start, search_end=cell.source_span.char_end,
                    literal=literal,
                )
                if receipt is None:
                    continue
                fact = _fact_present(
                    fact_id=fact_id, event_id=event_id, metric="net_orders",
                    value=int(units_match.group(1).replace(",", "")), unit="homes", period=period_label,
                    basis=basis_label, document_id=document_id, bound=bound, receipt=receipt,
                )
                if idx == 0:
                    current_fact = fact
                else:
                    prior_fact = fact
    facts.append(current_fact or _fact_absent(
        fact_id="fact_net_orders_current", event_id=event_id, metric="net_orders",
        detail="net signed contracts is not uniquely addressable in Exhibit 99.1", document_id=document_id,
    ))
    facts.append(prior_fact or _fact_absent(
        fact_id="fact_net_orders_prior_year", event_id=event_id, metric="net_orders",
        detail="prior-year same-quarter net signed contracts is not uniquely addressable in Exhibit 99.1",
        document_id=document_id,
    ))

    basis_text = "quarterly cancellations as a percentage of signed contracts in the quarter (Toll Brothers primary convention)"
    cancel_row = _find_row_by_label(
        blocks, "Quarterly Cancellations as a Percentage of Signed Contracts in Quarter", block_contains="three months",
    )
    current_receipt = prior_receipt = None
    if cancel_row is not None:
        cells = [cell for cell in cancel_row[1:] if cell.text.strip() not in ("", "%")]
        if len(cells) >= 2:
            current_receipt = _literal_receipt(
                bound, search_start=cells[0].source_span.char_start, search_end=cells[0].source_span.char_end,
                literal=cells[0].text,
            )
            prior_receipt = _literal_receipt(
                bound, search_start=cells[1].source_span.char_start, search_end=cells[1].source_span.char_end,
                literal=cells[1].text,
            )
    for fact_id, receipt, cell_text, period_label, detail in (
        (
            "fact_cancellation_rate_current", current_receipt, cells[0].text if cancel_row is not None and current_receipt else None,
            period, "quarterly cancellation-as-percentage-of-signed-contracts is not present in Exhibit 99.1",
        ),
        (
            "fact_cancellation_rate_prior_year", prior_receipt, cells[1].text if cancel_row is not None and prior_receipt else None,
            "prior_year_same_quarter", "prior-year quarterly cancellation-as-percentage-of-signed-contracts is not present in Exhibit 99.1",
        ),
    ):
        facts.append(
            _fact_present(
                fact_id=fact_id, event_id=event_id, metric="cancellation_rate", value=float(cell_text),
                unit="percent", period=period_label, basis=basis_text, document_id=document_id, bound=bound,
                receipt=receipt,
            )
            if receipt is not None
            else _fact_absent(fact_id=fact_id, event_id=event_id, metric="cancellation_rate", detail=detail, document_id=document_id)
        )

    # F4: the convention fact's VALUE must be the row's own verbatim LABEL
    # text, receipted over that label cell — never a code-authored paraphrase
    # ("signed contracts in quarter") receipted against a numeric "5.4" cell,
    # which is a false receipt (the cited bytes don't say what the value
    # claims).
    denom_receipt = None
    denom_value = None
    if cancel_row is not None:
        label_cell = cancel_row[0]
        denom_receipt = _literal_receipt(
            bound, search_start=label_cell.source_span.char_start, search_end=label_cell.source_span.char_end,
            literal=label_cell.text,
        )
        denom_value = label_cell.text if denom_receipt is not None else None
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            value=denom_value, unit=None, period=None, basis=basis_text,
            document_id=document_id, bound=bound, receipt=denom_receipt,
        )
        if denom_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_denominator", event_id=event_id, metric="cancellation_rate_basis",
            detail="the stated cancellation denominator convention is not present in Exhibit 99.1", document_id=document_id,
        )
    )

    # (vi) TOL only: beginning-quarter-backlog cancellation sensitivity fact,
    # current AND prior-year (IMCE A5C item 7).  The consumption side already
    # exists at engine/cycle_pattern/imce_prospective.py:161
    # (TOL_SENSITIVITY_PRIOR_YEAR_FACT_ID) and is self-healing -- it has been
    # looking this fact_id up since A5A and resolving to typed absence only
    # because extraction never emitted it; this block is extraction only, no
    # consumption-side change.
    # F4: the basis text is the row's own verbatim label (not a paraphrase)
    # when the row is found, and both the current and prior-year facts share
    # that SAME verbatim basis string (frozen spec item 2 -- one row, one
    # stated convention, two cells).
    backlog_row = _find_row_by_label(
        blocks, "Quarterly Cancellations as a Percentage of Beginning-Quarter Backlog", block_contains="three months",
    )
    backlog_basis = "quarterly cancellations as a percentage of beginning-quarter backlog (Toll Brothers sensitivity convention)"
    backlog_receipt = backlog_prior_receipt = None
    backlog_value = backlog_prior_value = None
    backlog_prior_detail = "the prior-year beginning-quarter-backlog cancellation sensitivity measure is not present in Exhibit 99.1"
    if backlog_row is not None:
        backlog_basis = backlog_row[0].text
        cells = [cell for cell in backlog_row[1:] if cell.text.strip() not in ("", "%")]
        if cells:
            backlog_receipt = _literal_receipt(
                bound, search_start=cells[0].source_span.char_start, search_end=cells[0].source_span.char_end,
                literal=cells[0].text,
            )
            backlog_value = cells[0].text if backlog_receipt is not None else None
        # Red-team MINOR-2: the prior-year fact only fires on an
        # UNAMBIGUOUS two-cell row shape (current + prior-year, exactly).
        # This exhibit carries other blocks combining "three months" AND
        # "nine months" columns in one row; a >=3-cell row of that shape
        # would otherwise let cells[1] silently bind to a non-prior-year
        # figure with a byte-exact-but-WRONG receipt. Any shape other than
        # exactly 2 numeric cells is typed absence, never a guess. The
        # current-quarter fact above keeps its existing `if cells:` (>=1)
        # behavior, byte-identical to pre-PR main.
        if len(cells) > 2:
            backlog_prior_detail = (
                f"the beginning-quarter-backlog row carries {len(cells)} numeric cells, an ambiguous "
                "shape (expected exactly 2: current-quarter + prior-year)"
            )
        elif len(cells) == 2:
            # NO inference / NO substitution: the prior-year cell mints its
            # OWN receipt over its OWN span -- if it is absent or its literal
            # fails to replay, the prior-year fact goes typed-absent on its
            # own terms and the current-quarter fact above is unaffected
            # either way (frozen spec item 2).
            backlog_prior_receipt = _literal_receipt(
                bound, search_start=cells[1].source_span.char_start, search_end=cells[1].source_span.char_end,
                literal=cells[1].text,
            )
            if backlog_prior_receipt is not None:
                # Red-team MAJOR-1: guard the parse. A prior-year cell shaped
                # "N/A", "(1)", or any other non-float literal must not raise
                # -- an unhandled ValueError here would propagate out of
                # extract_release_facts and kill the ENTIRE TOL workspace
                # build on the nightly path. Unparseable ⇒ typed absence on
                # its own terms; the current-quarter fact is unaffected
                # either way (frozen spec item 2). This guard is scoped to
                # ONLY the cell this PR newly reads -- the sibling rows'
                # existing unguarded float() idiom (e.g. line below, and the
                # current-quarter fact just above) is left byte-identical.
                try:
                    backlog_prior_value = float(cells[1].text)
                except ValueError:
                    backlog_prior_receipt = None
                    backlog_prior_detail = (
                        f"the prior-year beginning-quarter-backlog cell ({cells[1].text!r}) is not a "
                        "parseable percentage"
                    )
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_beginning_backlog_sensitivity", event_id=event_id,
            metric="cancellation_rate_sensitivity", value=float(backlog_value), unit="percent", period=period,
            basis=backlog_basis, document_id=document_id, bound=bound, receipt=backlog_receipt,
        )
        if backlog_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_beginning_backlog_sensitivity", event_id=event_id,
            metric="cancellation_rate_sensitivity",
            detail="the beginning-quarter-backlog cancellation sensitivity measure is not present in Exhibit 99.1",
            document_id=document_id,
        )
    )
    facts.append(
        _fact_present(
            fact_id="fact_cancellation_rate_beginning_backlog_sensitivity_prior_year", event_id=event_id,
            metric="cancellation_rate_sensitivity", value=backlog_prior_value, unit="percent",
            period="prior_year_same_quarter", basis=backlog_basis, document_id=document_id, bound=bound,
            receipt=backlog_prior_receipt,
        )
        if backlog_prior_receipt is not None
        else _fact_absent(
            fact_id="fact_cancellation_rate_beginning_backlog_sensitivity_prior_year", event_id=event_id,
            metric="cancellation_rate_sensitivity",
            detail=backlog_prior_detail,
            document_id=document_id,
        )
    )
    return facts


def tol_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="TOL",
        extract_release_facts=_tol_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# TSM — Taiwan Semiconductor Manufacturing Company Limited (T05a witness).
#
# Two release facts, both receipted against the same synthetic look-alike
# exhibit body (no real Exhibit 99.1 committed):
#
# * ``fact_revenue_twd`` — the NT$ net revenue figure.  No TWD unit exists
#   in the existing unit vocabulary (``engine.earnings_release.figures
#   ._UNIT_BY_SCALE`` is USD-prefixed), so per the docket this is emitted
#   as a typed absence with detail
#   ``reporting_currency_twd_not_in_unit_vocabulary`` rather than inventing
#   a unit or converting (C4: zero arithmetic).
#
# * ``fact_revenue_usd`` — the USD-restated revenue, present with unit
#   ``usd_billions`` receipted against the literal ``US$12.34 billion``; its
#   closed tokens equal the guidance items' (metric ``revenue``, basis
#   ``reported_ifrs``, currency ``USD``) and the reading location lives in a
#   non-compared ``provenance`` note.
#
# extract_guidance reads the NEXT-quarter revenue range out of ``bound``
# (the release body), emitting guidance_item.v1 dicts with explicit
# ``currency`` ("USD"), ``basis`` ("reported_ifrs"), and ``fx_assumption``
# (verbatim phrase from the release) — TSM reports USD guidance with an
# explicit exchange-rate assumption.
# ─────────────────────────────────────────────────────────────────────────────

# ── TSM / ON extraction: CLOSED HOUSE-STYLE GRAMMARS ─────────────────────────
# Four independent review rounds showed that an open prose parser (sentence
# windows, comparative markers, connectives, clause dating) has an unbounded
# leak surface: every round found a new construction that put a valid receipt
# on a WRONG binding.  The extractors below therefore bind ONLY to the issuer's
# own fixed release templates, anchored on structure the issuer states
# explicitly — the quarter-END DATE in TSMC's headline, the fiscal-quarter
# COLUMN LABELS in onsemi's tables — and refuse everything else with a typed
# absence.  A figure that is not stated in the template is not "found"; it is
# absent.  Templates were read off the issuers' real EX-99.1 exhibits (TSMC
# 6-K 0001046179-26-000199 / -000451, onsemi 8-K 0001140361-26-018868 /
# -030989); the test fixtures are synthetic look-alikes of that structure.
#
# TSMC headline (block anchor; ordinal AND quarter-end date must both match):
#   "… today announced consolidated revenue of NT$1,270.38 billion, net income
#    of …, for the second quarter ended June 30, 2026."
_TSM_HEADLINE_RE = re.compile(
    r"today announced consolidated revenue of (NT\$[\d,]+(?:\.\d+)?\s+(?:billion|million))\b.*?"
    r"\bfor the (first|second|third|fourth) quarter ended "
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\b",
    re.S,
)
# TSMC USD restatement (sentence-initial; ordinal must match the reported quarter):
#   "In US dollars, second quarter revenue was $40.20 billion, which increased …"
# The USD template carries an ordinal but no year: its year is inherited from the
# headline gate (ordinal AND quarter-end date equal the reported period). A
# prior-year recap written in this exact house form would be indistinguishable;
# TSMC states prior years as percentages, and two matches are a typed absence.
_TSM_USD_TEMPLATE_RE = re.compile(
    r"In U\.?S\.? dollars, (first|second|third|fourth) quarter revenue was ((?:US)?\$\d+(?:\.\d+)?\s+billion)\b"
)
# TSMC guidance: a lead sentence naming the horizon, then bullets.
#   "… management expects the overall performance for third quarter 2026 to be as follows:"
#   "•Revenue is expected to be between US$44.6 billion and US$45.8 billion;"
#   "And, based on the exchange rate assumption of 1 US dollar to 32 NT dollars,"
_TSM_GUIDANCE_LEAD_RE = re.compile(
    r"management expects the overall performance for (first|second|third|fourth) quarter (20\d{2}) to be as follows"
)
_TSM_GUIDANCE_REVENUE_RE = re.compile(
    r"^\W{0,3}(Revenue is expected to be between US\$(\d+(?:\.\d+)?) billion and US\$(\d+(?:\.\d+)?) billion)\b"
)
_TSM_GUIDANCE_FX_RE = re.compile(r"based on the exchange rate assumption of (1 US dollar to \d+(?:\.\d+)? NT dollars)\b")
_TSM_GUIDANCE_WINDOW_RE = re.compile(r"^\W{0,3}(?:Revenue|Gross|Operating|And,|based on)", re.I)
_TSM_GUIDANCE_WINDOW_MAX_BLOCKS = 6
_ORDINAL_QUARTERS = {"first": 1, "second": 2, "third": 3, "fourth": 4}
_MONTH_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),?\s+(\d{4})\b")
_MONTHS = {name: index for index, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"), start=1)}


def _parse_month_date(text: str) -> date | None:
    m = _MONTH_DATE_RE.search(text)
    if m is None:
        return None
    try:
        return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        return None


def _reported(fiscal_period: Any) -> tuple[int, int, date] | None:
    """(year, quarter, calendar_end) of the reported period, or None when the
    caller did not say what was reported — nothing binds without it."""
    year = getattr(fiscal_period, "year", None)
    quarter = getattr(fiscal_period, "quarter", None)
    end = getattr(fiscal_period, "calendar_end", None)
    if year is None or quarter is None or not isinstance(end, date):
        return None
    return int(year), int(quarter), end


def _sentence_initial(text: str, index: int) -> bool:
    """The match starts a sentence: at the block start or right after ". "/"? "/"! "."""
    return index == 0 or text[max(0, index - 2):index] in (". ", "? ", "! ")


def _tsm_headline_anchors(blocks: Sequence[DisclosureBlock], reported: tuple[int, int, date]) -> list[tuple[DisclosureBlock, re.Match[str]]]:
    """Blocks whose headline names the reported quarter by ordinal AND by its
    exact quarter-end date. Anything else — another quarter, another year, a
    date one day off — is not an anchor."""
    _, quarter, end = reported
    out: list[tuple[DisclosureBlock, re.Match[str]]] = []
    for block in blocks:
        for m in _TSM_HEADLINE_RE.finditer(block.text):
            if _ORDINAL_QUARTERS[m.group(2).lower()] == quarter and _parse_month_date(m.group(3)) == end:
                out.append((block, m))
    return out


def _tsm_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    reported = _reported(fiscal_period)
    blocks = bound.document.blocks

    def twd_absent(detail: str) -> dict[str, Any]:
        return _fact_absent(fact_id="fact_revenue_twd", event_id=event_id, metric="revenue",
                            detail=detail, document_id=document_id)

    def usd_absent(detail: str) -> dict[str, Any]:
        return _fact_absent(fact_id="fact_revenue_usd", event_id=event_id, metric="revenue",
                            detail=detail, document_id=document_id)

    if reported is None:
        return [twd_absent("no reported fiscal period to anchor the headline to"),
                usd_absent("no reported fiscal period to anchor the headline to")]
    anchors = _tsm_headline_anchors(blocks, reported)
    if len(anchors) != 1:
        detail = (f"{len(anchors)} headline blocks name the reported quarter ended "
                  f"{reported[2].isoformat()}; exactly one is required")
        return [twd_absent(detail), usd_absent(detail)]
    anchor_block, headline = anchors[0]
    facts: list[dict[str, Any]] = []

    # (i) NT$ consolidated revenue — the literal is in the anchor headline; the
    # unit vocabulary has no TWD scale, so a receipted literal is the typed
    # ``missing_units`` state and an unreceiptable one is ``no_span_addressable_evidence``.
    twd_receipt = _literal_receipt(
        bound, search_start=anchor_block.source_span.char_start,
        search_end=anchor_block.source_span.char_end, literal=headline.group(1),
    )
    if twd_receipt is None:
        facts.append(twd_absent("NT$ consolidated revenue literal in the headline is not uniquely addressable"))
    else:
        facts.append(_fact_absent(
            fact_id="fact_revenue_twd", event_id=event_id, metric="revenue", reason="missing_units",
            detail=("reporting_currency_twd_not_in_unit_vocabulary: NT$ consolidated revenue literal is "
                    "present and receipted in the Exhibit 99.1 headline but the existing unit vocabulary is "
                    "USD-prefixed and no TWD scale exists to attach"),
            document_id=document_id,
        ))

    # (ii) USD-restated revenue — exactly ONE sentence-initial template match
    # with the reported ordinal anywhere in the exhibit. Two (e.g. a restated
    # prior-year sentence in the same style) is an absence, never a pick.
    candidates: list[tuple[DisclosureBlock, re.Match[str]]] = []
    for block in blocks:
        for m in _TSM_USD_TEMPLATE_RE.finditer(block.text):
            if _ORDINAL_QUARTERS[m.group(1).lower()] == reported[1] and _sentence_initial(block.text, m.start()):
                candidates.append((block, m))
    if len(candidates) != 1:
        facts.append(usd_absent(
            f"{len(candidates)} 'In US dollars, <reported> quarter revenue was $X billion' template "
            "sentences in Exhibit 99.1; exactly one is required"))
        return facts
    block, m = candidates[0]
    literal = m.group(2)
    usd_receipt = _literal_receipt(
        bound, search_start=block.source_span.char_start,
        search_end=block.source_span.char_end, literal=literal,
    )
    if usd_receipt is None:
        facts.append(usd_absent("USD revenue template literal is not uniquely addressable in its block"))
        return facts
    value = float(re.search(r"\d+(?:\.\d+)?", literal).group(0))
    # TSMC's USD-restated quarterly revenue ("In US dollars, … quarter revenue
    # was …"). The definitional tokens are the SAME closed values the guidance
    # extractor states (metric revenue, basis reported_ifrs, currency USD):
    # TSMC guides in US dollars on the same reported basis, so the T06
    # prior-vs-actual comparison is a genuine like-for-like, not a refusal
    # manufactured by two spellings of one definition (live-EDGAR proof,
    # 2026-09-24: metric_mismatch on the real Q1→Q2 sequence).
    facts.append(_fact_present(
        fact_id="fact_revenue_usd", event_id=event_id, metric="revenue",
        value=value, unit="usd_billions", period=period,
        basis="reported_ifrs", currency="USD",
        provenance="TSMC USD-restated quarterly revenue, as stated in Exhibit 99.1 ('In US dollars, … quarter revenue was')",
        document_id=document_id, bound=bound, receipt=usd_receipt,
    ))
    return facts


def _tsm_guidance_window(blocks: Sequence[DisclosureBlock], lead_index: int) -> list[DisclosureBlock]:
    """The bullet blocks that follow the guidance lead: consecutive blocks that
    look like outlook bullets / the FX clause, at most a few. The window stops
    at the first block that is neither."""
    window: list[DisclosureBlock] = []
    for block in blocks[lead_index + 1: lead_index + 1 + _TSM_GUIDANCE_WINDOW_MAX_BLOCKS]:
        if not _TSM_GUIDANCE_WINDOW_RE.match(block.text.strip()):
            break
        window.append(block)
    return window


def _tsm_extract_guidance(
    *,
    bound: BoundRelease,
    release_document_id: str,
    event_id: str,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    """TSM guidance from the issuer's fixed outlook template: ONE lead sentence
    ("management expects the overall performance for <ordinal> quarter <year>
    to be as follows") whose horizon is strictly after the reported period,
    followed by bullets; the ONE revenue bullet ("Revenue is expected to be
    between US$A billion and US$B billion") in that window is the item, and
    the FX assumption is the verbatim "1 US dollar to N NT dollars" clause in
    the same window (None when absent; two different clauses refuse).  No
    lead, two leads, no/two revenue bullets, a range in prose, a horizon not
    after the reported period, or no reported period → no item."""
    reported = _reported(_kwargs.get("fiscal_period"))
    if reported is None:
        return []
    blocks = bound.document.blocks
    leads: list[tuple[int, str]] = []
    for index, block in enumerate(blocks):
        for m in _TSM_GUIDANCE_LEAD_RE.finditer(block.text):
            horizon = (int(m.group(2)), _ORDINAL_QUARTERS[m.group(1).lower()])
            if horizon > (reported[0], reported[1]):
                leads.append((index, f"{horizon[0]}Q{horizon[1]}"))
    if len(leads) != 1:
        return []
    lead_index, horizon = leads[0]
    window = _tsm_guidance_window(blocks, lead_index)
    ranges = [(block, m) for block in window for m in [_TSM_GUIDANCE_REVENUE_RE.match(block.text.strip())] if m]
    if len(ranges) != 1:
        return []
    range_block, range_match = ranges[0]
    range_receipt = _literal_receipt(
        bound, search_start=range_block.source_span.char_start,
        search_end=range_block.source_span.char_end, literal=range_match.group(1),
    )
    if range_receipt is None:
        return []
    fx_clauses = [(block, m) for block in window for m in _TSM_GUIDANCE_FX_RE.finditer(block.text)]
    if len({m.group(1) for _, m in fx_clauses}) > 1:
        return []
    fx_assumption: str | None = None
    if fx_clauses:
        fx_block, fx_match = fx_clauses[0]
        fx_receipt = _literal_receipt(
            bound, search_start=fx_block.source_span.char_start,
            search_end=fx_block.source_span.char_end, literal=fx_match.group(1),
        )
        if fx_receipt is None:
            return []
        fx_assumption = fx_match.group(1)
    return [{
        "schema": "guidance_item.v1",
        "metric": "revenue",
        "low": float(range_match.group(2)),
        "high": float(range_match.group(3)),
        "unit": "usd_billions",
        "horizon": horizon,
        "status": "introduced",
        "currency": "USD",
        "basis": "reported_ifrs",
        "fx_assumption": fx_assumption,
        "source_span": _release_span_payload(
            document_id=release_document_id, bound=bound, receipt=range_receipt,
        ),
    }]


def tsm_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="TSM",
        extract_release_facts=_tsm_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
        extract_guidance=_tsm_extract_guidance,
    )


# onsemi: label-bound tables.
#   Summary table: a caption cell "(Revenue and Net Income in millions)", a label
#   row carrying fiscal-quarter codes ("Q2 2026", "Q1 2026", "Q2 2025" under GAAP
#   and again under Non-GAAP), and a "Revenue" row whose value sits in the SAME
#   cell index as each reported label ("$" lives in its own cell).
#   Outlook: a lead paragraph "… projected third quarter of 2026 GAAP and non-GAAP
#   outlook." then a table whose header row has "Total onsemi GAAP" and whose
#   "Revenue" row carries "$1,650 to $1,750 million" in that column.
_ON_CAPTION_UNIT_RE = re.compile(r"\bin (millions|billions)\b", re.I)
# Plain positive figure only. A parenthesised (negative) or otherwise decorated
# cell is a typed absence, never a parsed value (review #5 nit 1).
_ON_CELL_VALUE_RE = re.compile(r"^([\d,]+(?:\.\d+)?)$")
_ON_OUTLOOK_LEAD_RE = re.compile(
    r"projected (first|second|third|fourth) quarter of (20\d{2}) (?:GAAP and non-GAAP )?outlook", re.I)
_ON_OUTLOOK_GAAP_HEADER = "total onsemi gaap"
_ON_OUTLOOK_RANGE_RE = re.compile(r"^\$([\d,]+(?:\.\d+)?) to \$([\d,]+(?:\.\d+)?) (million|billion)$")
_USD_UNIT_BY_WORD = {"million": "usd_millions", "billion": "usd_billions"}


def _on_quarter_label(year: int, quarter: int) -> str:
    return f"Q{quarter} {year}"


def _on_summary_tables(blocks: Sequence[DisclosureBlock], label: str) -> list[DisclosureBlock]:
    """TABLE blocks that carry BOTH the unit caption and the reported label."""
    out: list[DisclosureBlock] = []
    for block in blocks:
        if block.kind is not BlockKind.TABLE or block.table is None:
            continue
        if _ON_CAPTION_UNIT_RE.search(block.text) is None:
            continue
        if any(cell.text.strip() == label for row in block.table.rows for cell in row):
            out.append(block)
    return out


def _on_document_names_period_end(blocks: Sequence[DisclosureBlock], end: date) -> bool:
    """Corroboration: some 'Quarters Ended' table dates a column with the
    reported period end. The label binding is the fact's anchor; this only
    refuses a document that never names the period it is said to report."""
    for block in blocks:
        if block.kind is BlockKind.TABLE and block.table is not None and "Quarters Ended" in block.text:
            if any(_parse_month_date(cell.text) == end for row in block.table.rows[:4] for cell in row):
                return True
    return False


def _on_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    reported = _reported(fiscal_period)
    blocks = bound.document.blocks

    def absent(detail: str) -> list[dict[str, Any]]:
        return [_fact_absent(fact_id="fact_revenue", event_id=event_id, metric="revenue",
                             detail=detail, document_id=document_id)]

    if reported is None:
        return absent("no reported fiscal period to bind a quarter label to")
    year, quarter, end = reported
    label = _on_quarter_label(year, quarter)
    if not _on_document_names_period_end(blocks, end):
        return absent(f"no Quarters Ended table dates a column {end.isoformat()}")
    tables = _on_summary_tables(blocks, label)
    if len(tables) != 1:
        return absent(f"{len(tables)} captioned summary tables carry the label {label!r}; exactly one is required")
    table = tables[0].table
    assert table is not None
    unit_word = _ON_CAPTION_UNIT_RE.search(tables[0].text).group(1).lower()  # type: ignore[union-attr]
    unit = _USD_UNIT_BY_WORD["million" if unit_word == "millions" else "billion"]
    label_row = next(row for row in table.rows if any(cell.text.strip() == label for cell in row))
    columns = [index for index, cell in enumerate(label_row) if cell.text.strip() == label]
    revenue_rows = [row for row in table.rows if row and row[0].text.strip().lower() == "revenue"]
    if len(revenue_rows) != 1:
        return absent(f"{len(revenue_rows)} Revenue rows in the captioned summary table; exactly one is required")
    row = revenue_rows[0]
    cells = [row[index] for index in columns if index < len(row)]
    if len(cells) != len(columns):
        return absent("Revenue row is shorter than the label row")
    parsed = [_ON_CELL_VALUE_RE.match(cell.text.strip()) for cell in cells]
    if not parsed or any(m is None for m in parsed):
        return absent(f"Revenue cells under {label!r} are not plain figures")
    values = {m.group(1) for m in parsed if m is not None}
    if len(values) != 1:
        return absent(f"Revenue cells under {label!r} disagree ({', '.join(sorted(values))})")
    cell = cells[0]
    literal = cell.text.strip()
    receipt = _literal_receipt(
        bound, search_start=cell.source_span.char_start,
        search_end=cell.source_span.char_end, literal=literal,
    )
    if receipt is None:
        return absent("Revenue cell bound to the reported label is not receiptable")
    # onsemi GAAP quarterly revenue from the Exhibit 99.1 summary table; the
    # definitional tokens match the outlook table's (basis reported_gaap,
    # currency USD) so the T06 comparison is like-for-like (live-EDGAR proof,
    # 2026-09-24: basis_change on the real Q1→Q2 sequence came from a prose
    # basis string on the fact, not from onsemi).
    return [_fact_present(
        fact_id="fact_revenue", event_id=event_id, metric="revenue",
        value=float(parsed[0].group(1).replace(",", "")), unit=unit, period=period,
        basis="reported_gaap", currency="USD",
        provenance="onsemi GAAP quarterly revenue, as stated in the Exhibit 99.1 summary table",
        document_id=document_id, bound=bound, receipt=receipt,
    )]


def _on_extract_guidance(
    *,
    bound: BoundRelease,
    release_document_id: str,
    event_id: str,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    """ON guidance — the GAAP revenue range from the outlook table that follows
    the ONE lead paragraph naming a horizon strictly after the reported period.
    The column is chosen by the header label 'Total onsemi GAAP', never by
    position; the cell must be exactly '$A to $B million|billion'.  No lead,
    two leads, no table, no GAAP header, a malformed cell, a horizon not after
    the reported period, or no reported period → no item."""
    reported = _reported(_kwargs.get("fiscal_period"))
    if reported is None:
        return []
    blocks = bound.document.blocks
    leads: list[tuple[int, str]] = []
    for index, block in enumerate(blocks):
        if block.kind is BlockKind.TABLE:
            continue
        for m in _ON_OUTLOOK_LEAD_RE.finditer(block.text):
            horizon = (int(m.group(2)), _ORDINAL_QUARTERS[m.group(1).lower()])
            if horizon > (reported[0], reported[1]):
                leads.append((index, f"{horizon[0]}Q{horizon[1]}"))
    if len(leads) != 1:
        return []
    lead_index, horizon = leads[0]
    table_block = next(
        (b for b in blocks[lead_index + 1: lead_index + 3] if b.kind is BlockKind.TABLE and b.table is not None),
        None,
    )
    if table_block is None or table_block.table is None:
        return []
    rows = table_block.table.rows
    header = next((row for row in rows if any(c.text.strip().lower() == _ON_OUTLOOK_GAAP_HEADER for c in row)), None)
    if header is None:
        return []
    columns = [i for i, c in enumerate(header) if c.text.strip().lower() == _ON_OUTLOOK_GAAP_HEADER]
    if len(columns) != 1:
        return []
    revenue_rows = [row for row in rows if row and row[0].text.strip().lower() == "revenue"]
    if len(revenue_rows) != 1 or columns[0] >= len(revenue_rows[0]):
        return []
    cell = revenue_rows[0][columns[0]]
    m = _ON_OUTLOOK_RANGE_RE.match(cell.text.strip())
    if m is None:
        return []
    receipt = _literal_receipt(
        bound, search_start=cell.source_span.char_start,
        search_end=cell.source_span.char_end, literal=cell.text.strip(),
    )
    if receipt is None:
        return []
    return [{
        "schema": "guidance_item.v1",
        "metric": "revenue",
        "low": float(m.group(1).replace(",", "")),
        "high": float(m.group(2).replace(",", "")),
        "unit": _USD_UNIT_BY_WORD[m.group(3).lower()],
        "horizon": horizon,
        "status": "introduced",
        "currency": "USD",
        "basis": "reported_gaap",
        "fx_assumption": None,
        "source_span": _release_span_payload(
            document_id=release_document_id, bound=bound, receipt=receipt,
        ),
    }]


def on_profile() -> IssuerProfile:
    return IssuerProfile(
        ticker="ON",
        extract_release_facts=_on_extract_release_facts,
        extract_transcript_claims=lambda **_kwargs: [],
        extract_guidance=_on_extract_guidance,
    )


_HOMEBUILDER_PROFILE_FACTORIES: dict[str, Callable[[], IssuerProfile]] = {
    "DHI": dhi_profile,
    "PHM": phm_profile,
    "KBH": kbh_profile,
    "TOL": tol_profile,
}


_SEMICONDUCTOR_PROFILE_FACTORIES: dict[str, Callable[[], IssuerProfile]] = {
    "TSM": tsm_profile,
    "ON": on_profile,
}


def issuer_for_ticker(ticker: str) -> IssuerIdentity | None:
    """The registered :class:`IssuerIdentity` for one of the four homebuilders,
    or one of the T05a semiconductor witnesses (TSM/ON).

    ``None`` for AAPL (use :func:`event_workspace.apple_issuer` directly) and
    for any unknown ticker.  Acquisition needs the CIK and
    ``fiscal_year_end_month`` before an event's fiscal period can be derived
    from a discovered filing's ``report_date``, which is why this is exposed
    separately from :func:`profile_for_ticker`.
    """
    normalized = str(ticker or "").strip().upper()
    factory = _HOMEBUILDER_ISSUER_FACTORIES.get(normalized)
    if factory is not None:
        return factory()
    factory = _SEMICONDUCTOR_ISSUER_FACTORIES.get(normalized)
    return factory() if factory is not None else None


def profile_for_ticker(ticker: str) -> IssuerProfile | None:
    """The registered profile for *ticker*, or ``None`` for an unknown ticker.

    ``"AAPL"`` resolves to :func:`apple_profile`; unknown tickers (including
    LEN and NVR, deliberately not added this wave) resolve to ``None`` so a
    caller can fail closed rather than silently defaulting to Apple's profile.
    The four homebuilders and the two T05a semiconductor witnesses (TSM/ON)
    share the same fail-closed contract: an unknown ticker never silently
    routes through Apple's profile.
    """
    normalized = str(ticker or "").strip().upper()
    if normalized == "AAPL":
        return apple_profile()
    factory = _HOMEBUILDER_PROFILE_FACTORIES.get(normalized)
    if factory is not None:
        return factory()
    factory = _SEMICONDUCTOR_PROFILE_FACTORIES.get(normalized)
    return factory() if factory is not None else None


__all__ = [
    "DHI_CIK",
    "PHM_CIK",
    "KBH_CIK",
    "TOL_CIK",
    "TSM_CIK",
    "ON_CIK",
    "TSM_FIF_GAP",
    "HOMEBUILDER_TICKERS",
    "IssuerProfile",
    "apple_profile",
    "dhi_issuer",
    "phm_issuer",
    "kbh_issuer",
    "tol_issuer",
    "tsm_issuer",
    "on_issuer",
    "dhi_profile",
    "phm_profile",
    "kbh_profile",
    "tol_profile",
    "tsm_profile",
    "on_profile",
    "issuer_for_ticker",
    "profile_for_ticker",
]
