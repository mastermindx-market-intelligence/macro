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
) -> dict[str, Any]:
    return {
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
#   ``usd_billions`` receipted against the literal ``US$12.34 billion``.
#
# extract_guidance reads the NEXT-quarter revenue range out of ``bound``
# (the release body), emitting guidance_item.v1 dicts with explicit
# ``currency`` ("USD"), ``basis`` ("reported_ifrs"), and ``fx_assumption``
# (verbatim phrase from the release) — TSM reports USD guidance with an
# explicit exchange-rate assumption.
# ─────────────────────────────────────────────────────────────────────────────

_TSM_NT_REVENUE_RE = re.compile(r"NT\$[\d,]+(?:\.\d+)?\s*million")
# TSMC writes both "US$12.34 billion" and (house style) "$12.34 billion"; the
# lookbehind refuses the "$" inside "NT$…".
_TSM_USD_REVENUE_RE = re.compile(r"(?<![A-Za-z])(?:US)?\$([\d.,]+)\s*billion")
_TSM_GUIDANCE_RANGE_RE = re.compile(
    r"between\s+US\$([\d.]+)\s+billion\s+and\s+US\$([\d.]+)\s+billion"
)
_TSM_GUIDANCE_FX_RE = re.compile(
    r"assuming\s+an\s+exchange\s+rate\s+of\s+(\d+(?:\.\d+)?\s+NTD\s+per\s+USD)\b\.?"
)

# ── Period binding for release text (T05a review fixes) ─────────────────────
# A release names MANY figures: the reported quarter's, the year-ago
# comparative, last quarter's, the range management guided to previously.
# Nothing below chooses "the first match": a figure is bound to the reported
# period only when its own clause carries no comparative marker AND the block
# it sits in names the reported quarter; a guidance range is emitted only
# from a forward-looking sentence that names the horizon quarter AND year
# explicitly.  Anything ambiguous is a typed absence / no item — never a guess.
# Two sentence windows, chosen by which way each fails:
#   * the ABBREVIATION-AWARE window does not break after "U.S." / "Inc." / an
#     initial / a month — the issuer's own prose says "In U.S. Dollars, …" and a
#     naive splitter would sever a recap or comparative marker from the figure it
#     qualifies.  Merging two real sentences can only SUPPRESS a figure, so this
#     window is used for every marker test (fail-closed);
#   * the STRICT window breaks at every terminal punctuation + whitespace +
#     capital.  It is used for every value that is ASSERTED from the sentence —
#     the guidance horizon and the FX assumption — because a merge across
#     "…at TSMC Corp. We expect…" would otherwise read a quarter named in the
#     previous sentence as the range's horizon.  Severing only loses a horizon
#     (no item), never invents one.
_SENTENCE_END_RE = re.compile(r"[.!?]+\s+(?=[A-Z\"'(\[])")
_ABBREVIATION_TAIL_RE = re.compile(
    r"(?:\b(?:U\.S|U\.K|E\.U|Inc|Ltd|Co|Corp|No|Nos|vs|approx|est|etc|e\.g|i\.e|cf|Mr|Mrs|Ms|Dr|Jr|Sr|St|Fig|et\s+al|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)|\b[A-Z])\.$")
# A comma followed by a digit is a thousands separator ("NT$1,234,567"), never a
# clause boundary.  Parentheses and dashes open/close an aside ("revenue (US$8.00
# billion a year ago) reached US$12.34 billion") and are clause boundaries too.
_CLAUSE_SPLIT_RE = re.compile(
    r",(?!\d)|;|[()]|[—–]|\s-\s|\bcompared\s+(?:with|to)\b|\bversus\b|\bvs\.?\b|\bagainst\b|\bthan\b|"
    r"\bup\s+from\b|\bdown\s+from\b|\bfrom\b|\bto\b|\band\b|\bwhile\b|\bwhereas\b", re.I)
# "to" is a boundary but never a connective: "grew from US$8.00 billion TO
# US$12.34 billion" / "rose TO US$12.34 billion" introduce the CURRENT figure.
# Openers that make the clause they introduce a COMPARISON: the figure inside it
# is the thing compared against, never the reported actual.  A bare "from" is a
# connective only after a growth word ("rose 17.8% from …"); "revenue from
# wafer sales" is not a comparison.
_CONNECTIVE_OPENER_RE = re.compile(r"^(?:compared|versus|vs|against|than|up\s+from|down\s+from)", re.I)
_GROWTH_TAIL_RE = re.compile(
    r"(?:\b(?:grew|rose|increased?|declined?|fell|decreased?|improved|expanded|contracted|jumped|dropped|climbed|slipped|"
    r"up|down|higher|lower|growth|increase|decrease|change[ds]?)\b|%|\bpercent\b)[^,;]{0,40}$", re.I)
# Periods that are not a quarter at all: a figure dated to them is never the
# reported quarter's.
_NON_QUARTER_PERIOD_RE = re.compile(
    r"\b(?:(?:six|nine|twelve|three)[-\s]+months?|(?:first|second)[-\s]+half|half[-\s]+year|full[-\s]+year|"
    r"year[-\s]+to[-\s]+date|calendar[-\s]+year|annual(?:ized|ly)?|trailing[-\s]+twelve)\b", re.I)
# Metric positivity: a revenue fact binds only a figure whose own clause says
# revenue, or whose sentence says revenue and names no OTHER metric.
_REVENUE_WORD_RE = re.compile(r"\b(?:net\s+|consolidated\s+|total\s+)?revenues?\b", re.I)
_OTHER_METRIC_RE = re.compile(
    r"\b(?:gross\s+(?:profit|margin)|operating\s+(?:income|expenses?|margin|profit)|net\s+(?:income|profit|loss)|"
    r"earnings\s+per\s+share|EPS|capital\s+expenditures?|capex|free\s+cash\s+flow|EBITDA|dividends?|"
    r"cash\s+and\s+cash\s+equivalents|wafer\s+shipments?)\b", re.I)
# Period-REDIRECTING markers only: they say the figure belongs to another period.
# Every multi-word marker accepts a hyphen OR whitespace between its words
# ("year-earlier quarter" == "year earlier quarter").  Growth qualifiers ("rose
# year-over-year / quarter-on-quarter to US$X") describe the current figure and
# are deliberately absent — including them suppressed the true figure.
_COMPARATIVE_MARKER_RE = re.compile(
    r"\b(?:a\s+year\s+(?:ago|earlier)|year[-\s]+(?:ago|earlier)|"
    r"(?:in\s+the\s+)?(?:prior|previous|preceding|last|corresponding|comparable|same|like)[-\s]+(?:year|quarter|period)|"
    r"sequentially|on\s+a\s+sequential\s+basis)\b", re.I)
_RECAP_MARKER_RE = re.compile(
    r"\b(guided|previously|prior\s+guidance|earlier\s+guidance|last[-\s]+quarter|prior[-\s]+quarter|"
    r"earlier\s+this\s+year|had\s+expected|originally)\b", re.I)
_FORWARD_MARKER_RE = re.compile(
    r"\b(looking\s+ahead|we\s+expect|expects?|anticipates?|guidance|outlook|forecasts?|projects?|is\s+expected)\b", re.I)
_ORDINAL_QUARTERS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
_QUARTER_WORDS = {1: "first", 2: "second", 3: "third", 4: "fourth"}
_QUARTER_PHRASE_RE = re.compile(
    r"\b(first|second|third|fourth|1st|2nd|3rd|4th)[\s-]+quarter(?:\s+of)?(?:\s+fiscal(?:\s+year)?)?\s+(20\d{2})\b", re.I)
# Year-first: "fiscal 2025 second quarter", "2025 second quarter".
_YEAR_FIRST_QUARTER_RE = re.compile(
    r"\b(?:fiscal\s+(?:year\s+)?)?(20\d{2}),?\s+(first|second|third|fourth|1st|2nd|3rd|4th)[\s-]+quarter\b", re.I)
# Ordinal-only / deictic quarter mentions ("second quarter revenue", "Q2",
# "for the quarter"): resolve to the reported quarter only because the BLOCK
# already names the reported quarter+year.
_ORDINAL_ONLY_QUARTER_RE = re.compile(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)[\s-]+quarter\b", re.I)
_BARE_QCODE_RE = re.compile(r"\b(?:Q([1-4])|([1-4])Q)\b")
_DEICTIC_QUARTER_RE = re.compile(r"\b(?:the|this|current)\s+quarter\b", re.I)
_QUARTER_CODE_RE = re.compile(r"\b(?:Q([1-4])\s*(20\d{2})|([1-4])Q(\d{2}|20\d{2})|(20\d{2})\s*Q([1-4]))\b")
_MONTH_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),?\s+(\d{4})\b")
_MONTHS = {name: index for index, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"), start=1)}


def _sentence_bounds(text: str, *, strict: bool = False) -> list[tuple[int, int]]:
    """(start, end) of every sentence.  Abbreviation-aware by default (a candidate
    break after "U.S." / "Inc." / an initial is not a sentence end); ``strict``
    breaks at every candidate.  See the window law above ``_SENTENCE_END_RE``."""
    bounds: list[tuple[int, int]] = []
    start = 0
    for m in _SENTENCE_END_RE.finditer(text):
        if not strict and _ABBREVIATION_TAIL_RE.search(text[start:m.start() + 1].rstrip()):
            continue
        bounds.append((start, m.start()))
        start = m.end()
    bounds.append((start, len(text)))
    return bounds


def _sentence_at(text: str, index: int, *, strict: bool = False) -> tuple[int, str]:
    """The (start, sentence) of ``text`` containing character ``index``."""
    bounds = _sentence_bounds(text, strict=strict)
    for start, end in bounds:
        if start <= index < end:
            return start, text[start:end]
    start, end = bounds[-1]
    return start, text[start:end]


def _both_windows(text: str, index: int) -> tuple[tuple[int, str], tuple[int, str]]:
    """The abbreviation-aware and the strict (start, sentence) windows around
    ``index``; a figure is redirected when EITHER window says so."""
    return _sentence_at(text, index), _sentence_at(text, index, strict=True)


def _clauses(sentence: str) -> list[tuple[int, int, str]]:
    """(start, end, opener) of every clause of ``sentence``; ``opener`` is the
    delimiter text that introduced the clause ("" for the first, "," for a
    comma, "compared with" / "from" / … for a connective)."""
    out: list[tuple[int, int, str]] = []
    start, opener = 0, ""
    for m in _CLAUSE_SPLIT_RE.finditer(sentence):
        out.append((start, m.start(), opener))
        start, opener = m.end(), " ".join(m.group(0).split()).lower()
    out.append((start, len(sentence), opener))
    return out


def _is_connective(opener: str, previous_clause: str) -> bool:
    """Does ``opener`` introduce a comparison clause?  "compared with", "versus",
    "against", "up/down from" always; a bare "from" only after a growth word in
    the tail of the previous clause ("rose 17.8% from …", "an increase from …")."""
    if _CONNECTIVE_OPENER_RE.match(opener):
        return True
    return opener == "from" and _GROWTH_TAIL_RE.search(previous_clause) is not None


def _clause_dated_elsewhere(clause: str, reported: tuple[int, int] | None) -> bool:
    """The clause carries a comparative marker, names quarter+year(s) none of
    which is the reported one, or names a non-quarter period (six months,
    first half, full year, year-to-date, …)."""
    if _COMPARATIVE_MARKER_RE.search(clause):
        return True
    if reported is None:
        return False
    named = _quarters_named(clause)
    if named:
        return reported not in named
    return _NON_QUARTER_PERIOD_RE.search(clause) is not None


def _figure_redirected(
    sentence: str, index: int, pattern: re.Pattern[str], reported: tuple[int, int] | None = None,
) -> bool:
    """True when the figure at ``index`` is redirected away from the reported
    period.  Per clause of the sentence:
      * the figure's OWN clause is dated elsewhere (marker / other quarter /
        non-quarter period) or is opened by a comparison connective
        ("compared with US$8.00 billion", "grew from US$8.00 billion") → redirected;
      * a FIGURE-LESS clause dated elsewhere that is NOT a connective clause is
        an adverbial qualifying the whole sentence ("A year ago, …", "In the
        second quarter of 2025, …") → redirected;
      * a figure-less connective clause ("…, up from last year", "…17.8% from the
        previous quarter") describes growth of the current figure → no effect."""
    clauses = _clauses(sentence)
    for position, (start, end, opener) in enumerate(clauses):
        clause = sentence[start:end]
        previous = sentence[clauses[position - 1][0]:clauses[position - 1][1]] if position else ""
        connective = _is_connective(opener, previous)
        if start <= index < end:
            if _COMPARATIVE_MARKER_RE.search(clause):
                return True
            named = _quarters_named(clause)
            if named:
                # Explicit dating decides, even inside a connective clause:
                # "…a year ago, compared with US$12.34 billion in the second
                # quarter of 2026" dates the compared figure TO the reported quarter.
                return reported is None or reported not in named
            if reported is not None and _NON_QUARTER_PERIOD_RE.search(clause):
                return True
            if connective:
                return True
            continue
        if _clause_dated_elsewhere(clause, reported) and not connective and pattern.search(clause) is None:
            return True
    return False


def _names_reported_quarter(sentence: str, reported: tuple[int, int]) -> bool:
    """Positive period binding: the sentence itself names the reported quarter —
    with its year, or as an ordinal / Q-code / "the quarter" mention that the
    enclosing block (which names the reported quarter+year) resolves.  A sentence
    that names no quarter at all binds nothing."""
    named = _quarters_named(sentence)
    if named:
        return reported in named
    ordinals = {_ORDINAL_QUARTERS[m.group(1).lower()] for m in _ORDINAL_ONLY_QUARTER_RE.finditer(sentence)}
    ordinals |= {int(m.group(1) or m.group(2)) for m in _BARE_QCODE_RE.finditer(sentence)}
    if ordinals:
        return reported[1] in ordinals
    return _DEICTIC_QUARTER_RE.search(sentence) is not None


def _metric_mentions(text: str, metric_re: re.Pattern[str]) -> list[tuple[int, bool]]:
    """(position, is_the_metric) for every metric word in ``text``."""
    mentions = [(m.start(), True) for m in metric_re.finditer(text)]
    mentions += [(m.start(), False) for m in _OTHER_METRIC_RE.finditer(text)
                 if not any(a <= m.start() < a + 1 for a, _ in mentions)]
    return sorted(mentions)


def _names_metric(sentence: str, index: int, metric_re: re.Pattern[str]) -> bool:
    """Positive metric binding by NEAREST attribution: within the figure's own
    clause the closest metric word before the figure decides ("revenue was
    US$12.34 billion" binds; "gross profit was US$7.00 billion" never does);
    a clause whose only metric word follows the figure uses that ("US$7.00
    billion in gross profit"); a clause with no metric word at all ("…, or
    US$12.34 billion") falls back to the nearest metric word before the figure
    in the sentence.  No metric word anywhere → not bound."""
    for start, end, _ in _clauses(sentence):
        if start <= index < end:
            clause = sentence[start:end]
            mentions = _metric_mentions(clause, metric_re)
            rel = index - start
            before = [flag for pos, flag in mentions if pos < rel]
            if before:
                return before[-1]
            after = [flag for pos, flag in mentions if pos > rel]
            if after:
                return after[0]
            break
    before = [flag for pos, flag in _metric_mentions(sentence, metric_re) if pos < index]
    return bool(before) and before[-1]


def _quarters_named(text: str) -> set[tuple[int, int]]:
    """Every (year, quarter) the text names, as words or as Q-codes."""
    found: set[tuple[int, int]] = set()
    for m in _QUARTER_PHRASE_RE.finditer(text):
        found.add((int(m.group(2)), _ORDINAL_QUARTERS[m.group(1).lower()]))
    for m in _YEAR_FIRST_QUARTER_RE.finditer(text):
        found.add((int(m.group(1)), _ORDINAL_QUARTERS[m.group(2).lower()]))
    for m in _QUARTER_CODE_RE.finditer(text):
        if m.group(1):
            found.add((int(m.group(2)), int(m.group(1))))
        elif m.group(3):
            year = int(m.group(4)); year = year + 2000 if year < 100 else year
            found.add((year, int(m.group(3))))
        else:
            found.add((int(m.group(5)), int(m.group(6))))
    return found


def _horizon_named(sentence: str) -> str | None:
    """The ONE horizon a forward sentence names, ``YYYYQn``; None when the
    sentence names no quarter+year or more than one (never inferred)."""
    named = _quarters_named(sentence)
    if len(named) != 1:
        return None
    (year, quarter), = named
    return f"{year}Q{quarter}"


def _parse_month_date(text: str) -> date | None:
    m = _MONTH_DATE_RE.search(text)
    if m is None:
        return None
    try:
        return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))
    except ValueError:
        return None


def _period_bound_literals(
    blocks: Sequence[DisclosureBlock], pattern: re.Pattern[str], fiscal_period: Any,
    metric_re: re.Pattern[str] = _REVENUE_WORD_RE,
) -> list[tuple[DisclosureBlock, re.Match[str]]]:
    """Matches of ``pattern`` bound to the reported period by POSITIVE evidence:
    the block names the reported (year, quarter); the match's own strict
    sentence names the reported quarter (``_names_reported_quarter``) and the
    metric (``_names_metric``); and the match is not redirected — comparative
    marker, comparison connective, other quarter, non-quarter period — in
    EITHER the abbreviation-aware or the strict window around it.  Absence of a
    redirect is never enough on its own: the caller asserts when exactly one
    distinct candidate survives, so a figure that merely fails to say where it
    belongs must not become the sole survivor.  Order preserved."""
    year = getattr(fiscal_period, "year", None)
    quarter = getattr(fiscal_period, "quarter", None)
    if year is None or quarter is None:
        return []
    reported = (int(year), int(quarter))
    bound: list[tuple[DisclosureBlock, re.Match[str]]] = []
    for block in blocks:
        if reported not in _quarters_named(block.text):
            continue
        for m in pattern.finditer(block.text):
            strict_start, strict = _sentence_at(block.text, m.start(), strict=True)
            if not _names_reported_quarter(strict, reported):
                continue
            if not _names_metric(strict, m.start() - strict_start, metric_re):
                continue
            if any(
                _figure_redirected(sentence, m.start() - sentence_start, pattern, reported)
                for sentence_start, sentence in _both_windows(block.text, m.start())
            ):
                continue
            bound.append((block, m))
    return bound


def _forward_ranges(
    blocks: Sequence[DisclosureBlock], pattern: re.Pattern[str], fiscal_period: Any = None,
) -> list[tuple[DisclosureBlock, re.Match[str], str, str]]:
    """(block, match, horizon, strict_sentence) for every range that is
    guidance: no recap marker in the abbreviation-aware window around it, a
    forward marker in its STRICT sentence, and exactly one quarter+year named
    in that strict sentence (the horizon is read from the range's own sentence,
    never from a neighbour merged across "…Corp. We expect…").  A horizon that
    is not strictly after the reported ``fiscal_period`` is not guidance; with
    no reported period there is nothing to be forward OF, so nothing is
    emitted."""
    year, quarter = getattr(fiscal_period, "year", None), getattr(fiscal_period, "quarter", None)
    if year is None or quarter is None:
        return []
    reported = (int(year), int(quarter))
    found: list[tuple[DisclosureBlock, re.Match[str], str, str]] = []
    for block in blocks:
        for m in pattern.finditer(block.text):
            (_, wide), (_, strict) = _both_windows(block.text, m.start())
            if _RECAP_MARKER_RE.search(wide) or not _FORWARD_MARKER_RE.search(strict):
                continue
            horizon = _horizon_named(strict)
            if horizon is None:
                continue
            if (int(horizon[:4]), int(horizon[-1])) <= reported:
                continue
            found.append((block, m, horizon, strict))
    return found


def _tsm_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    blocks = bound.document.blocks
    facts: list[dict[str, Any]] = []

    # (i) NT$ net revenue.  The unit vocabulary has no TWD scale, so this fact
    # is a typed absence either way — but the two states are DIFFERENT and
    # countable: the literal is present and receipted (``missing_units``), or
    # no NT$ figure is bound to the reported period (``no_span_addressable_evidence``).
    twd_receipt = None
    for block, m in _period_bound_literals(blocks, _TSM_NT_REVENUE_RE, fiscal_period):
        twd_receipt = _literal_receipt(
            bound, search_start=block.source_span.char_start,
            search_end=block.source_span.char_end, literal=m.group(0),
        )
        if twd_receipt is not None:
            break
    if twd_receipt is None:
        facts.append(_fact_absent(
            fact_id="fact_revenue_twd", event_id=event_id, metric="revenue",
            detail="NT$ net revenue for the reported quarter is not present or not uniquely addressable in Exhibit 99.1",
            document_id=document_id,
        ))
    else:
        facts.append(_fact_absent(
            fact_id="fact_revenue_twd", event_id=event_id, metric="revenue",
            reason="missing_units",
            detail=(
                "reporting_currency_twd_not_in_unit_vocabulary: NT$ net revenue "
                "literal is present and receipted in Exhibit 99.1 but the existing unit "
                "vocabulary is USD-prefixed and no TWD scale exists to attach"
            ),
            document_id=document_id,
        ))

    # (ii) USD-restated revenue — present only when exactly ONE distinct USD
    # figure is bound to the reported period; a year-ago comparative in its
    # own clause is never it, and two competing figures are an absence.
    candidates = _period_bound_literals(blocks, _TSM_USD_REVENUE_RE, fiscal_period)
    distinct = {m.group(1).replace(",", "") for _, m in candidates}
    if len(distinct) == 1:
        for block, m in candidates:
            usd_receipt = _literal_receipt(
                bound, search_start=block.source_span.char_start,
                search_end=block.source_span.char_end, literal=m.group(0),
            )
            if usd_receipt is None:
                continue
            facts.append(_fact_present(
                fact_id="fact_revenue_usd", event_id=event_id, metric="revenue_usd",
                value=float(m.group(1).replace(",", "")), unit="usd_billions",
                period=period,
                basis="TSMC USD-restated revenue, as stated in Exhibit 99.1",
                document_id=document_id, bound=bound, receipt=usd_receipt,
            ))
            return facts
    facts.append(_fact_absent(
        fact_id="fact_revenue_usd", event_id=event_id, metric="revenue_usd",
        detail=(
            "USD-restated revenue for the reported quarter is not present or not uniquely "
            f"addressable in Exhibit 99.1 ({len(distinct)} period-bound candidate figures)"
        ),
        document_id=document_id,
    ))
    return facts


def _tsm_extract_guidance(
    *,
    bound: BoundRelease,
    release_document_id: str,
    event_id: str,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    """TSM guidance — USD revenue range with an explicit FX assumption.

    Emits the ONE range that sits in a forward-looking sentence naming its
    horizon quarter and year (``horizon`` is read from the range's own strict
    sentence, never assumed, and must be after the reported ``fiscal_period``
    — without one nothing is emitted); a recap of prior guidance, a range
    without a forward marker, or two competing forward ranges yield no item.
    ``fx_assumption`` is the verbatim rate stated in THAT strict sentence and
    ``None`` when it states none — the key is always present, so None IS the
    typed "not stated" state (guidance_item.v1 has a closed key set; no extra
    key is invented).  More than one FX statement in the sentence refuses the
    item: competing or repeated assumptions are never resolved by picking one.
    """
    blocks = bound.document.blocks
    forward = _forward_ranges(blocks, _TSM_GUIDANCE_RANGE_RE, _kwargs.get("fiscal_period"))
    if len(forward) != 1:
        return []
    range_para, range_match, horizon, forward_sentence = forward[0]
    range_receipt = _literal_receipt(
        bound,
        search_start=range_para.source_span.char_start,
        search_end=range_para.source_span.char_end,
        literal=range_match.group(0),
    )
    if range_receipt is None:
        return []
    # The FX assumption is the one stated IN the strict forward sentence that
    # carries the range — a rate stated for a recap, in a neighbouring sentence
    # merged across an abbreviation, or elsewhere in the release is not this
    # range's rate. None when the sentence states none; more than one FX
    # statement (competing rates, or one rate repeated so that no single literal
    # receipt addresses it) refuses the item rather than picking.
    fx_assumption: str | None = None
    fx_matches = list(_TSM_GUIDANCE_FX_RE.finditer(forward_sentence))
    if len(fx_matches) > 1:
        return []
    fx_match = fx_matches[0] if fx_matches else None
    if fx_match is not None:
        fx_receipt = _literal_receipt(
            bound,
            search_start=range_para.source_span.char_start,
            search_end=range_para.source_span.char_end,
            literal=fx_match.group(0),
        )
        if fx_receipt is not None:
            fx_assumption = fx_match.group(1).strip()
    return [{
        "schema": "guidance_item.v1",
        "metric": "revenue",
        "low": float(range_match.group(1)),
        "high": float(range_match.group(2)),
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


# ─────────────────────────────────────────────────────────────────────────────
# ON — ON Semiconductor Corporation (T05a witness).
#
# Single release fact — GAAP revenue read out of the "Quarters Ended" table
# in the COLUMN whose header date equals the reported period end — and a
# forward revenue range (USD, no FX assumption) whose horizon is read from
# the sentence that states it.
# ─────────────────────────────────────────────────────────────────────────────

_ON_REVENUE_RE = re.compile(r"\$([\d,]+(?:\.\d+)?)\s*(million|billion)")
_ON_GUIDANCE_RANGE_RE = re.compile(
    r"(?:range\s+of|between)\s+\$([\d,]+(?:\.\d+)?)\s*(million|billion)\s+(?:to|and)\s+\$([\d,]+(?:\.\d+)?)\s*(million|billion)",
    re.I,
)
_USD_UNIT_BY_WORD = {"million": "usd_millions", "billion": "usd_billions"}


def _on_extract_release_facts(*, bound: BoundRelease, document_id: str, event_id: str, **kwargs: Any) -> list[dict[str, Any]]:
    fiscal_period = kwargs.get("fiscal_period")
    period = _period_label(fiscal_period)
    period_end = getattr(fiscal_period, "calendar_end", None)
    blocks = bound.document.blocks

    def absent(detail: str) -> list[dict[str, Any]]:
        return [_fact_absent(
            fact_id="fact_revenue", event_id=event_id, metric="revenue",
            detail=detail, document_id=document_id,
        )]

    if period_end is None:
        return absent("no reported period end to bind a Quarters Ended column to")
    target_block: DisclosureBlock | None = None
    for block in blocks:
        if block.kind is BlockKind.TABLE and block.table is not None and "Quarters Ended" in block.text:
            target_block = block
            break
    if target_block is None or target_block.table is None:
        return absent("Quarters Ended table is not present in Exhibit 99.1")

    # The header row is the first row carrying month-day-year dates; each
    # date owns one value column. The Revenue row's non-separator cells must
    # line up one-to-one with those dates, else the table is not addressable.
    header_dates: list[date] = []
    for row in target_block.table.rows[:4]:
        parsed = [_parse_month_date(cell.text) for cell in row]
        if any(parsed):
            header_dates = [d for d in parsed if d is not None]
            break
    if not header_dates:
        return absent("Quarters Ended table names no period-end dates")
    if header_dates.count(period_end) != 1:
        return absent(
            f"{header_dates.count(period_end)} Quarters Ended columns are dated {period_end.isoformat()} "
            f"(columns: {', '.join(d.isoformat() for d in header_dates)}); exactly one is required"
        )
    column = header_dates.index(period_end)
    for row in target_block.table.rows:
        if not row or row[0].text.strip().lower() != "revenue":
            continue
        values = [cell for cell in row[1:] if cell.text.strip() not in ("", "$")]
        if len(values) != len(header_dates):
            return absent(
                f"Revenue row has {len(values)} value cells for {len(header_dates)} dated columns"
            )
        cell = values[column]
        m = _ON_REVENUE_RE.search(cell.text)
        if m is None:
            return absent("Revenue cell bound to the reported period carries no $-million/billion figure")
        receipt = _literal_receipt(
            bound, search_start=cell.source_span.char_start,
            search_end=cell.source_span.char_end, literal=m.group(0),
        )
        if receipt is None:
            return absent("Revenue cell bound to the reported period is not receiptable")
        return [_fact_present(
            fact_id="fact_revenue", event_id=event_id, metric="revenue",
            value=float(m.group(1).replace(",", "")), unit=_USD_UNIT_BY_WORD[m.group(2).lower()],
            period=period,
            basis="onsemi GAAP quarterly revenue, as stated in Exhibit 99.1",
            document_id=document_id, bound=bound, receipt=receipt,
        )]
    return absent("Quarters Ended table has no Revenue row")


def _on_extract_guidance(
    *,
    bound: BoundRelease,
    release_document_id: str,
    event_id: str,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    """ON guidance — USD revenue range, no FX assumption (domestic filer).
    The horizon is read from the range's own strict forward sentence and must
    be after the reported ``fiscal_period`` (none → no item); both ends must
    share one magnitude word (million/billion) or the range is not emitted."""
    blocks = bound.document.blocks
    forward = _forward_ranges(blocks, _ON_GUIDANCE_RANGE_RE, _kwargs.get("fiscal_period"))
    if len(forward) != 1:
        return []
    range_para, range_match, horizon, _sentence = forward[0]
    if range_match.group(2).lower() != range_match.group(4).lower():
        return []
    range_receipt = _literal_receipt(
        bound,
        search_start=range_para.source_span.char_start,
        search_end=range_para.source_span.char_end,
        literal=range_match.group(0),
    )
    if range_receipt is None:
        return []
    return [{
        "schema": "guidance_item.v1",
        "metric": "revenue",
        "low": float(range_match.group(1).replace(",", "")),
        "high": float(range_match.group(3).replace(",", "")),
        "unit": _USD_UNIT_BY_WORD[range_match.group(2).lower()],
        "horizon": horizon,
        "status": "introduced",
        "currency": "USD",
        "basis": "reported_gaap",
        "fx_assumption": None,
        "source_span": _release_span_payload(
            document_id=release_document_id, bound=bound, receipt=range_receipt,
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
