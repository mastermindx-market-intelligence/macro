"""Tape -> sampler candidates (Prophet news-impact, wave w2).

The tape rows are a recall net (PHASE0_FREEZE section 8); this module turns
them into ``engine.news_impact.sampler.Candidate`` value objects plus a
draw manifest and a funnel report. Every candidate's ``source`` is the
issuer's own SEC EDGAR primary filing class
(``agentos/decisions/DEC-NEWS-IMPACT-BENCHMARK-BODY-SOURCE.md``);
``proxy_cell`` is a STRATIFICATION PROXY used only to spread the draw
across cells, never a label (``sampler.py`` module docstring).

The draw replays byte-identically from (tape sha, date bounds, seed,
sampler version); no clock reads, no random module, no network. Short
cells are reported short, never padded.

Issuer resolution reads one ledger by default. An optional fallback ledger
(``--fallback-ledger``) only fills rows the primary ledger leaves unresolved:
the second pass reads the primary entries plus the fallback entries whose
tickers the primary ledger does not carry, so a primary refusal (ambiguous or
not listed at the as-of) stands, and every row the primary ledger resolves keeps
its issuer, tickers and tags. Without the option every output is byte-identical
to a run without it (DEC:NEWS-IMPACT-ISSUER-FALLBACK-LEDGER).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Callable, Iterable, Mapping

from engine.news_impact.issuer import (
    ABSENCE_REASONS,
    Ledger,
    Mention,
    canonical_ticker,
    resolve_mention,
)
from engine.news_impact.sampler import (
    CELLS,
    SAMPLER_VERSION,
    TAG_NAMES,
    TEMPLATES,
    Case,
    Candidate,
    Draw,
    SamplePlan,
    SamplerError,
    build_manifest,
    draw_sample,
    load_tape,
)

__all__ = [
    "TAPE_DRAW_VERSION",
    "BODY_SOURCE_CLASS",
    "EVENT_TYPE_TEMPLATE",
    "TapeDrawError",
    "FAMILY_PATTERNS",
    "NEG_PATTERN",
    "AMB_PATTERN",
    "NOC_PATTERN",
    "family_hits",
    "template_of",
    "proxy_cell_of",
    "default_window",
    "build_candidates",
    "run_draw",
    "attach_body_accounting",
    "candidate_to_dict",
    "load_body_frame",
    "load_gate_frame",
    "main",
]

# --- module constants (S1) ----------------------------------------------------

TAPE_DRAW_VERSION = "ni-tape-draw-1"
BODY_SOURCE_CLASS = "sec_edgar:primary_filing"
EVENT_TYPE_TEMPLATE = {
    "buyback": "T1",
    "dividend_change": "T1",
    "equity_offering": "T1",
    "guidance_raise": "T2",
    "guidance_cut": "T2",
    "contract_award": "T2",
    "customer_win": "T2",
    "product_launch": "T3",
}


class TapeDrawError(ValueError):
    """Invalid tape-draw input or environment (never a short cell)."""


# --- regex patterns (S1, byte-for-byte from the spec block) -------------------

_T1_RE = (
    r"\b(?:dividends?|buy-?backs?|repurchas\w*|offerings?|private placements?|stock splits?|reverse splits?|tender offers?|redeem\w*|redemptions?|senior notes|convertible\w*|notes due|debt (?:offering|issuance|raise)|capital returns?|share sales?|sells? shares|raises? \$[\d.,]+ ?(?:million|billion|m|bn|b)\b)"
)
_T2_RE = (
    r"\b(?:guidance|outlook|forecasts?|reaffirms|reiterates|(?:raises|lifts|cuts|lowers|trims|boosts|ups|slashes|withdraws|narrows|maintains) "
    r"(?:its |full-year |annual |fy\d* |fiscal \d* |\d{4} |q\d )*(?:revenue |sales |earnings |profit |eps )?(?:guidance|outlook|forecast|view|target)"
    r"|profit warning|warns|preannounce|pre-announce|(?:wins|awarded|secures|lands|receives|signs) (?:a |an |the |\$?[\d.,]+ ?(?:million|billion|m|b|bn) )*"
    r"(?:contract|order|deal|award)|contract (?:award|win)|(?:multi-year|multiyear|\$[\d.,]+ ?(?:million|billion|m|b|bn)) (?:contract|order|deal)|backlog|bookings|purchase order)\b"
)
_T3_RE = (
    r"\b(?:partner(?:s|ed|ing)? with|partnerships?|collaborat(?:es?|ion|ions|ing) with|strategic collaboration|alliances?|joint ventures?|team(?:s|ed)? up"
    r"|launch(?:es|ed)?|unveil(?:s|ed)?|rolls? out|licens(?:e|ing) (?:agreement|deal)|fda approv\w*|tie-?ups?|(?:strategic|supply|distribution|commercial|collaboration) agreements?)\b"
)
_NEG_RE = (
    r"(?:\bshould you\b|\bis it time\b|\bbuy or sell\b|\bwhat to expect\b|\bpreview\b|\bahead of\b|\bto watch\b|\bstocks? to (?:buy|watch|own)\b"
    r"|\bhere'?s why\b|\bwhy\b.{0,60}\b(?:stock|shares)\b|\bbest\b.{0,40}\bstocks?\b|\btop \d+\b|\bopinions? on\b|\bexplained\b|\bhistory says\b"
    r"|\$[\d,]+ investment\b|\bcould make you\b|\bdividend (?:stocks?|investing|investors?|focus|strength|growth stocks?)\b|\bgreat\b.{0,30}\bstock\b"
    r"|\b(?:stock|shares) (?:soar|soars|soared|jump|jumps|jumped|surge|surges|surged|fall|falls|fell|drop|drops|dropped|slide|slides|slid|sink|sinks|sank|rise|rises|rose|skyrocket\w*|plunge\w*|tumble\w*)\b"
    r"|\bvs\.? \b|\bshould investors\b|\bwhat\b.{0,40}\bmeans for\b|\bis\b.{0,40}\ba buy\b)"
)
_AMB_RE = (
    r"(?:\bconsider(?:s|ing)?\b|\bexplor(?:es|ing)\b|\bweigh(?:s|ing)?\b|\breportedly\b|\bin talks\b|\btalks (?:with|to|over)\b|\bmulls?\b|\beyes\b"
    r"|\brumou?r\w*\b|\bsources? say\b|\bpeople familiar\b|\bnears?\b|\bpoised to\b|\bseeks?\b|\bcould\b|\bmay\b|\bmight\b|\?\s*$)"
)
_NOC_RE = (
    r"(?:\breaffirm\w*\b|\breiterat\w*\b|\bmaintain\w*\b|\bunchanged\b|\bkeeps?\b|\baffirms?\b|\bholds? (?:steady|its)\b"
    r"|\bdeclares? (?:a |its )?(?:regular |quarterly |monthly |semi-annual |interim )+(?:cash )?dividend\b|\bconfirms? (?:its )?(?:guidance|outlook|dividend)\b|\brenew(?:s|ed|al|als)?\b|\bextend(?:s|ed)? (?:its |their |the )?(?:partnership|agreement|collaboration|alliance|contract)\b|\bexpands? (?:its |their |the )?(?:existing )?(?:partnership|collaboration|alliance)\b)"
)

FAMILY_PATTERNS = {
    "T1": re.compile(_T1_RE, re.IGNORECASE),
    "T2": re.compile(_T2_RE, re.IGNORECASE),
    "T3": re.compile(_T3_RE, re.IGNORECASE),
}
NEG_PATTERN = re.compile(_NEG_RE, re.IGNORECASE)
AMB_PATTERN = re.compile(_AMB_RE, re.IGNORECASE)
NOC_PATTERN = re.compile(_NOC_RE, re.IGNORECASE)


# --- helpers (S2, S3) ---------------------------------------------------------


def _text(v: Any) -> str:
    """Return v when it is a str, else ''. Maps None, pd.NA, NaN to '' (S2)."""
    return v if isinstance(v, str) else ""


def family_hits(title: str) -> dict[str, bool]:
    """Per-family regex hit (search, not match) for the given title (S3)."""
    return {t: bool(p.search(title or "")) for t, p in FAMILY_PATTERNS.items()}


def template_of(hits: dict[str, bool]) -> str | None:
    """First of T1, T2, T3 whose hit is True, else None (S3)."""
    for t in TEMPLATES:
        if hits.get(t):
            return t
    return None


def proxy_cell_of(title: str) -> str:
    """NEG beats AMB beats NOC beats positive (S3). proxy_cell is a proxy only."""
    if NEG_PATTERN.search(title or ""):
        return "negative"
    if AMB_PATTERN.search(title or ""):
        return "ambiguous"
    if NOC_PATTERN.search(title or ""):
        return "no_change"
    return "positive"


def default_window(rows: list[dict]) -> tuple[date, date]:
    """Default window: [max seendate - 89d, max seendate] (S4)."""
    if not rows:
        raise TapeDrawError(
            "tape has no dated rows; provide window_start/window_end or supply dated rows"
        )
    max_seen = max(r["seendate"] for r in rows)
    window_end = max_seen.astimezone(timezone.utc).date()
    window_start = window_end - timedelta(days=89)
    return window_start, window_end


# --- main types ---------------------------------------------------------------


@dataclass(frozen=True)
class CandidateBuild:
    candidates: tuple[Candidate, ...]
    meta: tuple[dict, ...]
    report: dict


@dataclass(frozen=True)
class TapeDrawResult:
    draw: Draw
    manifest: dict
    meta: tuple[dict, ...]
    report: dict
    # Every candidate the build produced, BEFORE any frame filter (defaulted so
    # positional constructions written against the original four fields still work).
    candidates: tuple[Candidate, ...] = ()


@dataclass(frozen=True)
class BodyFrame:
    """A body-available draw frame (DEC-NEWS-IMPACT-BENCHMARK-BODY-SOURCE amendment).

    ``status_map`` is an edgar_body status map (item_id -> "available" |
    "body_unavailable:<reason>") covering the FULL candidate pool; the frame keeps
    the candidates whose status is "available". It is outcome-blind: it reads only
    whether an issuer-filed body exists, never a label.
    """

    status_map: Mapping[str, str]
    status_map_sha256: str


@dataclass(frozen=True)
class GateFrame:
    """A routing-gate draw frame (DEC-NEWS-IMPACT-CONTINUATION-ROUTING-GATES).

    ``gate_map`` is an ``engine.news_impact.routing_gates`` gate map (item_id ->
    "gated_in" | "gated_out:<code>"); applied after a body frame, the draw keeps the
    gated-in candidates. Like the body frame it never reads a label or proxy_cell.
    """

    gate_map: Mapping[str, str]
    gate_map_sha256: str


# --- issuer resolution helpers (S7) -------------------------------------------

_PREFERRED_RE = re.compile(r"^([A-Z]{1,5})p[A-Z]{0,2}$")


def _parse_entities(entities_raw: Any) -> list[str]:
    """Split, strip, drop empties, de-dup keeping first-seen order (S7)."""
    text = _text(entities_raw)
    seen: set[str] = set()
    out: list[str] = []
    for part in text.split(","):
        s = part.strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _event_log_entities(row: dict) -> list[str]:
    """event_log tickers string -> list of str; malformed -> [] (S7)."""
    text = _text(row.get("tickers"))
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(t) for t in parsed if t]


def _resolve_entities(
    entities: list[str],
    title: str,
    asof: date,
    ledger: Any,
) -> tuple[str, str | None, list[str], int]:
    """Walk entities, resolve; first success sets issuer/ticker; collect ciks.

    Returns (issuer, ticker, resolved_ciks, preferred_variant_resolved_count).
    """
    resolved_ciks: list[str] = []
    issuer: str | None = None
    issuer_ticker: str | None = None
    preferred_variant_resolved = 0
    first_absence_reason: str | None = None
    attempted = False

    for idx, raw in enumerate(entities):
        token = _text(raw).strip()
        if not token:
            continue
        if len(token) == 1 and idx > 0:
            continue
        attempted = True
        r = resolve_mention(
            Mention(text=title, ticker=token, cik=None, exchange_mic=None, asof=asof),
            ledger=ledger,
        )
        used_token = token
        if r.company_id is None:
            m = _PREFERRED_RE.match(token)
            if m is not None:
                base = m.group(1)
                r2 = resolve_mention(
                    Mention(text=title, ticker=base, cik=None, exchange_mic=None, asof=asof),
                    ledger=ledger,
                )
                if r2.company_id is not None:
                    preferred_variant_resolved += 1
                    r = r2
                    used_token = base
        if r.company_id is not None and r.company_id not in resolved_ciks:
            if issuer is None:
                issuer = r.company_id
                issuer_ticker = canonical_ticker(used_token)
            resolved_ciks.append(r.company_id)
        if r.absence_reason is not None and first_absence_reason is None:
            first_absence_reason = r.absence_reason

    if not attempted:
        return "unresolved:no_mention", None, [], 0
    if issuer is None:
        reason = first_absence_reason or "no_mention"
        return f"unresolved:{reason}", None, resolved_ciks, preferred_variant_resolved
    return issuer, issuer_ticker, resolved_ciks, preferred_variant_resolved


def fill_only_ledger(primary: Any, fallback: Any) -> Ledger:
    """Primary entries plus the fallback entries for tickers the primary lacks.

    A ticker the primary ledger carries keeps exactly its primary entries, so a
    primary refusal (ambiguous, not listed at the as-of) is never overridden by
    the fallback. Both inputs must be :class:`Ledger` objects from ``load_ledger``.
    """
    if not isinstance(primary, Ledger) or not isinstance(fallback, Ledger):
        raise TapeDrawError("fill_only_ledger needs two Ledger objects from load_ledger")
    entries = {t: fallback[t] for t in fallback if t not in primary}
    entries.update({t: primary[t] for t in primary})
    return Ledger(
        entries,
        has_validity_dates=primary.has_validity_dates or fallback.has_validity_dates,
        source=f"{primary.source}+fill:{fallback.source}",
    )


# --- tag and holdout helpers (S8, S9) -----------------------------------------


def _near_duplicate_keys(in_window_rows: list[dict]) -> set[str]:
    """Event keys shared by 2..5 (inclusive) in-window rows (S8)."""
    counts: dict[str, int] = {}
    for r in in_window_rows:
        ek = _text(r.get("event_key"))
        if ek:
            counts[ek] = counts.get(ek, 0) + 1
    return {ek for ek, c in counts.items() if 2 <= c <= 5}


def _compute_holdout_keys(
    candidates: list[dict],
) -> dict[str, str]:
    """Compute hg: keys via union-find (S9).

    candidates: list of dicts with item_id, issuer, template, seendate, tape_event_key.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for c in candidates:
        iid = c["item_id"]
        if iid in parent:
            raise TapeDrawError(f"duplicate item_id in candidates: {iid!r}")
        parent[iid] = iid

    by_issuer_template: dict[tuple[str, str], list[dict]] = {}
    for c in candidates:
        if c["issuer"].startswith("cik:"):
            by_issuer_template.setdefault((c["issuer"], c["template"]), []).append(c)
    for members in by_issuer_template.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda c: (c["seendate"], c["item_id"]))
        for prev, cur in zip(members, members[1:]):
            prev_d = prev["seendate"].astimezone(timezone.utc).date()
            cur_d = cur["seendate"].astimezone(timezone.utc).date()
            if (cur_d - prev_d).days <= 2:
                union(prev["item_id"], cur["item_id"])

    by_event: dict[str, list[str]] = {}
    for c in candidates:
        ek = c["tape_event_key"]
        if ek:
            by_event.setdefault(ek, []).append(c["item_id"])
    for ids in by_event.values():
        for other in ids[1:]:
            union(ids[0], other)

    components: dict[str, list[str]] = {}
    for item_id in parent:
        components.setdefault(find(item_id), []).append(item_id)
    out: dict[str, str] = {}
    for members in components.values():
        members_sorted = sorted(members)
        gid = "hg:" + sha256("\n".join(members_sorted).encode("utf-8")).hexdigest()[:16]
        for item_id in members:
            out[item_id] = gid
    return out


# --- build_candidates (S5-S10) ------------------------------------------------


def build_candidates(
    rows: list[dict],
    *,
    window_start: date,
    window_end: date,
    event_log_rows: list[dict],
    reject_rows: list[dict],
    ledger: Any,
    low_value: Callable[..., bool],
    dropped: dict,
    total_rows: int,
    fallback_ledger: Any = None,
) -> CandidateBuild:
    """Turn load_tape rows into sampler Candidates plus a funnel report.

    With ``fallback_ledger`` a row the primary ledger leaves unresolved is
    re-resolved against :func:`fill_only_ledger`; the report gains a
    ``fallback_ledger`` record and ``issuers.fallback_resolved``, and each meta
    row gains ``issuer_ledger``. Without it the output is unchanged.
    """
    combined_ledger = (
        fill_only_ledger(ledger, fallback_ledger) if fallback_ledger is not None else None
    )
    fallback_resolved = 0
    event_log_by_id: dict[str, dict] = {r["event_id"]: r for r in event_log_rows}
    reject_by_id: dict[str, dict] = {r["event_id"]: r for r in reject_rows}
    tape_item_ids = {_text(r.get("item_id")) for r in rows}
    reject_not_on_tape = sum(1 for eid in reject_by_id if eid not in tape_item_ids)

    in_window_rows: list[dict] = []
    for r in rows:
        d = r["seendate"].astimezone(timezone.utc).date()
        if window_start <= d <= window_end:
            in_window_rows.append(r)
    nd_keys = _near_duplicate_keys(in_window_rows)

    funnel = {
        "seendate_dropped": int(sum(dropped.values())) if dropped else 0,
        "outside_window": 0,
        "non_english": 0,
        "low_value": 0,
        "no_family": 0,
        "candidate": 0,
    }
    feeders = {"event_log": 0, "reject": 0, "regex": 0}
    family_hits_counts = {"T1": 0, "T2": 0, "T3": 0}
    overlap_counts = {"T1&T2": 0, "T1&T3": 0, "T2&T3": 0, "T1&T2&T3": 0}
    unresolved_by_reason: dict[str, int] = {reason: 0 for reason in ABSENCE_REASONS}
    issuers_resolved = 0
    issuers_unresolved = 0
    preferred_variant_resolved = 0
    tags_nd = 0
    tags_it = 0
    pool_cells: dict[str, dict[str, int]] = {t: {c: 0 for c in CELLS} for t in TEMPLATES}

    cand_records: list[tuple[Candidate, dict, dict]] = []

    for row in rows:
        d = row["seendate"].astimezone(timezone.utc).date()
        if d < window_start or d > window_end:
            funnel["outside_window"] += 1
            continue
        lang = _text(row.get("lang")).strip().lower()
        if lang != "en":
            funnel["non_english"] += 1
            continue
        item_id = _text(row.get("item_id"))
        title = _text(row.get("title"))
        source = _text(row.get("source"))
        url = _text(row.get("url"))
        tape_event_key = _text(row.get("event_key"))
        entities = _parse_entities(row.get("entities"))

        is_reject_routed = item_id in reject_by_id

        if not is_reject_routed and bool(low_value(title, domain=source)):
            funnel["low_value"] += 1
            continue

        event_log_row = event_log_by_id.get(item_id)
        event_type: str | None = None
        feeder: str | None = None
        template: str | None = None
        proxy_cell: str | None = None

        if event_log_row is not None:
            et = _text(event_log_row.get("event_type"))
            if et in EVENT_TYPE_TEMPLATE:
                template = EVENT_TYPE_TEMPLATE[et]
                event_type = et
                proxy_cell = "no_change" if NOC_PATTERN.search(title or "") else "positive"
                feeder = "event_log"

        if feeder is None and is_reject_routed:
            hits = family_hits(title)
            t = template_of(hits)
            if t is None:
                funnel["no_family"] += 1
                continue
            template = t
            proxy_cell = "negative"
            feeder = "reject"

        if feeder is None:
            hits = family_hits(title)
            t = template_of(hits)
            if t is None:
                funnel["no_family"] += 1
                continue
            template = t
            proxy_cell = proxy_cell_of(title)
            feeder = "regex"

        feeders[feeder] += 1

        if not entities and event_log_row is not None:
            entities = _event_log_entities(event_log_row)

        issuer, ticker, resolved_ciks, pv_resolved = _resolve_entities(
            entities, title, d, ledger
        )
        issuer_ledger: str | None = None if issuer.startswith("unresolved:") else "primary"
        if combined_ledger is not None and issuer_ledger is None:
            f_issuer, f_ticker, f_ciks, f_pv = _resolve_entities(
                entities, title, d, combined_ledger
            )
            if not f_issuer.startswith("unresolved:"):
                issuer, ticker, resolved_ciks, pv_resolved = f_issuer, f_ticker, f_ciks, f_pv
                issuer_ledger = "fallback"
                fallback_resolved += 1
        preferred_variant_resolved += pv_resolved

        if issuer.startswith("unresolved:"):
            issuers_unresolved += 1
            reason = issuer.split(":", 1)[1]
            if reason in unresolved_by_reason:
                unresolved_by_reason[reason] += 1
        else:
            issuers_resolved += 1

        tags: set[str] = set()
        if len(resolved_ciks) >= 2:
            tags.add("indirect_transfer")
        if tape_event_key and tape_event_key in nd_keys:
            tags.add("near_duplicate")
        if "indirect_transfer" in tags:
            tags_it += 1
        if "near_duplicate" in tags:
            tags_nd += 1

        row_for_hash = {str(k): v for k, v in row.items()}
        source_sha = sha256(
            json.dumps(
                row_for_hash,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()

        cand = Candidate(
            item_id=item_id,
            issuer=issuer,
            ticker=ticker,
            template=template,
            proxy_cell=proxy_cell,
            seendate=row["seendate"],
            source=BODY_SOURCE_CLASS,
            source_sha256=source_sha,
            event_key=None,
            tags=frozenset(t for t in tags if t in TAG_NAMES),
            title=title,
        )

        if feeder in ("regex", "reject"):
            hits = family_hits(title)
            for f, hit in hits.items():
                if hit:
                    family_hits_counts[f] += 1
            if hits["T1"] and hits["T2"] and hits["T3"]:
                overlap_counts["T1&T2&T3"] += 1
            elif hits["T1"] and hits["T2"]:
                overlap_counts["T1&T2"] += 1
            elif hits["T1"] and hits["T3"]:
                overlap_counts["T1&T3"] += 1
            elif hits["T2"] and hits["T3"]:
                overlap_counts["T2&T3"] += 1

        pool_cells[template][proxy_cell] += 1

        meta = {
            "item_id": item_id,
            "title": title,
            "publisher": source,
            "url": url,
            "entities": entities,
            "event_type": event_type,
            "feeder": feeder,
            "tape_event_key": tape_event_key or None,
            "holdout_key": None,
            "family_hits": family_hits(title),
            "resolved_ciks": resolved_ciks,
            "issuer": issuer,
            "ticker": ticker,
            "template": template,
            "proxy_cell": proxy_cell,
        }
        if combined_ledger is not None:
            meta["issuer_ledger"] = issuer_ledger
        cand_records.append(
            (cand, meta, {"tape_event_key": tape_event_key, "row": row})
        )
        funnel["candidate"] += 1

    holdout_info: list[dict] = [
        {
            "item_id": cand.item_id,
            "issuer": cand.issuer,
            "template": cand.template,
            "seendate": cand.seendate,
            "tape_event_key": info["tape_event_key"],
        }
        for cand, _, info in cand_records
    ]
    holdout_keys = _compute_holdout_keys(holdout_info)

    final_candidates: list[Candidate] = []
    final_meta: list[dict] = []
    for (cand, meta, _info), hg_key in zip(
        cand_records, [holdout_keys[c["item_id"]] for c in holdout_info]
    ):
        cand2 = Candidate(
            item_id=cand.item_id,
            issuer=cand.issuer,
            ticker=cand.ticker,
            template=cand.template,
            proxy_cell=cand.proxy_cell,
            seendate=cand.seendate,
            source=cand.source,
            source_sha256=cand.source_sha256,
            event_key=hg_key,
            tags=cand.tags,
            title=cand.title,
        )
        meta2 = dict(meta)
        meta2["holdout_key"] = hg_key
        final_candidates.append(cand2)
        final_meta.append(meta2)

    sorted_pairs = sorted(
        zip(final_candidates, final_meta), key=lambda p: p[0].item_id
    )
    final_candidates_tuple = tuple(c for c, _ in sorted_pairs)
    final_meta_tuple = tuple(m for _, m in sorted_pairs)

    group_sizes: dict[str, int] = {}
    for c in final_candidates_tuple:
        group_sizes[c.event_key] = group_sizes.get(c.event_key, 0) + 1
    size_histogram: dict[int, int] = {}
    for s in group_sizes.values():
        size_histogram[s] = size_histogram.get(s, 0) + 1
    largest_size = max(group_sizes.values(), default=0)
    largest_key: str | None = None
    if largest_size:
        for k, v in group_sizes.items():
            if v == largest_size:
                largest_key = k
                break
    if largest_key is not None:
        largest: dict[str, Any] | None = {"key": largest_key, "size": largest_size}
    else:
        largest = {"key": None, "size": 0}

    funnel_total = sum(funnel.values())
    assert funnel_total == total_rows, (
        f"funnel sum {funnel_total} != total_rows {total_rows}: {funnel!r}"
    )

    report: dict[str, Any] = {
        "version": TAPE_DRAW_VERSION,
        "sampler_version": SAMPLER_VERSION,
        "tape_sha256": None,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "funnel": {
            "seendate_dropped": funnel["seendate_dropped"],
            "outside_window": funnel["outside_window"],
            "non_english": funnel["non_english"],
            "low_value": funnel["low_value"],
            "no_family": funnel["no_family"],
            "candidate": funnel["candidate"],
            "total": total_rows,
            "seendate_dropped_by_reason": dict(dropped) if dropped else {},
        },
        "families": {
            "hits": family_hits_counts,
            "overlaps": overlap_counts,
        },
        "feeders": {
            "event_log": feeders["event_log"],
            "reject": feeders["reject"],
            "regex": feeders["regex"],
            "reject_not_on_tape": reject_not_on_tape,
        },
        "issuers": {
            "resolved": issuers_resolved,
            "unresolved": issuers_unresolved,
            "unresolved_by_reason": unresolved_by_reason,
            "preferred_variant_resolved": preferred_variant_resolved,
        },
        "holdout": {
            "groups": len(group_sizes),
            "size_histogram": size_histogram,
            "largest": largest,
        },
        "tags": {
            "near_duplicate": tags_nd,
            "indirect_transfer": tags_it,
        },
        "pool_cells": pool_cells,
        "drawn_cells": None,
        "manifest_sha256": None,
    }
    if combined_ledger is not None:
        report["issuers"]["fallback_resolved"] = fallback_resolved
        # Inputs are recorded by sha256 only (set in run_draw), never by path,
        # so the report stays byte-reproducible from any checkout.
        report["fallback_ledger"] = {
            "tickers": len(fallback_ledger),
            "fill_only_tickers": sum(1 for t in fallback_ledger if t not in ledger),
            "primary_tickers": len(ledger),
            "sha256": None,
        }

    return CandidateBuild(
        candidates=final_candidates_tuple,
        meta=final_meta_tuple,
        report=report,
    )


# --- default low_value wrapper (S11) ------------------------------------------


def _make_default_low_value() -> Callable[..., bool]:
    def _low_value(title: str, *, domain: str = "") -> bool:
        from engine.news_common import is_low_value

        return is_low_value(title, domain=domain)

    return _low_value


# --- parquet readers (S11) ----------------------------------------------------


def _read_parquet_dicts(path: str) -> list[dict]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise TapeDrawError(
            f"pandas is not installed; cannot read {path!r}: {exc}"
        ) from exc
    frame = pd.read_parquet(path)
    out: list[dict] = []
    for record in frame.to_dict(orient="records"):
        out.append({str(k): v for k, v in record.items()})
    return out


def _read_tape_bytes(path: str) -> str:
    with open(path, "rb") as f:
        return sha256(f.read()).hexdigest()


# --- run_draw (S12) -----------------------------------------------------------


def _resolve_run_window(
    rows: list[dict],
    window_start: date | None,
    window_end: date | None,
) -> tuple[date, date]:
    if window_start is None and window_end is None:
        return default_window(rows)
    if window_end is None and window_start is not None:
        if not rows:
            raise TapeDrawError(
                "window_start given but tape has no dated rows to derive window_end"
            )
        window_end = max(r["seendate"] for r in rows).astimezone(timezone.utc).date()
    if window_start is None and window_end is not None:
        window_start = window_end - timedelta(days=89)
    assert window_start is not None and window_end is not None
    if window_start > window_end:
        raise TapeDrawError(
            f"window_start {window_start.isoformat()} > "
            f"window_end {window_end.isoformat()}"
        )
    return window_start, window_end


def _rights_allow(source: str) -> bool:
    """Default rights_allow: only the body source class (S10, S12)."""
    return source == BODY_SOURCE_CLASS


def candidate_to_dict(c: Candidate) -> dict[str, Any]:
    """JSON-safe dict of one Candidate (seendate as ISO-8601 UTC with trailing Z)."""
    return {
        "item_id": c.item_id,
        "issuer": c.issuer,
        "ticker": c.ticker,
        "template": c.template,
        "proxy_cell": c.proxy_cell,
        "seendate": c.seendate.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": c.source,
        "source_sha256": c.source_sha256,
        "event_key": c.event_key,
        "tags": sorted(c.tags),
        "title": c.title,
    }


def load_body_frame(status_map_path: str) -> BodyFrame:
    """Read an edgar_body status_map.json into a BodyFrame (fail-closed on shape)."""
    with open(status_map_path, "rb") as fh:
        raw = fh.read()
    try:
        status_map = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise TapeDrawError(f"body frame status map is not JSON: {exc}") from exc
    if not isinstance(status_map, dict) or not status_map:
        raise TapeDrawError("body frame status map must be a non-empty JSON object")
    for item_id, status in status_map.items():
        if not isinstance(status, str) or (
            status != "available" and not _STATUS_RE.match(status)
        ):
            raise TapeDrawError(
                f"malformed body status for item_id {item_id!r}: {status!r}"
            )
    return BodyFrame(status_map=status_map, status_map_sha256=sha256(raw).hexdigest())


GATE_STATUS_RE = re.compile(r"^(?:gated_in|gated_out:([a-z0-9_]+))$")


def load_gate_frame(gate_map_path: str) -> GateFrame:
    """Read a routing_gates gate map into a GateFrame (fail-closed on shape)."""
    with open(gate_map_path, "rb") as fh:
        raw = fh.read()
    try:
        gate_map = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise TapeDrawError(f"gate frame map is not JSON: {exc}") from exc
    if not isinstance(gate_map, dict) or not gate_map:
        raise TapeDrawError("gate frame map must be a non-empty JSON object")
    for item_id, status in gate_map.items():
        if not isinstance(status, str) or not GATE_STATUS_RE.match(status):
            raise TapeDrawError(f"malformed gate status for item_id {item_id!r}: {status!r}")
    return GateFrame(gate_map=gate_map, gate_map_sha256=sha256(raw).hexdigest())


def _cell_counts(candidates: Iterable[Candidate]) -> dict[str, dict[str, int]]:
    counts = {t: {c: 0 for c in CELLS} for t in TEMPLATES}
    for cand in candidates:
        counts[cand.template][cand.proxy_cell] += 1
    return counts


def _apply_body_frame(
    candidates: tuple[Candidate, ...], frame: BodyFrame
) -> tuple[tuple[Candidate, ...], dict[str, Any]]:
    """Keep the body-available candidates; every candidate must carry a status."""
    missing = sorted(c.item_id for c in candidates if c.item_id not in frame.status_map)
    if missing:
        raise TapeDrawError(
            f"body frame status map lacks {len(missing)} candidate item_id(s), "
            f"first {missing[:3]!r}: the frame must cover the full pool"
        )
    kept = tuple(c for c in candidates if frame.status_map[c.item_id] == "available")
    reasons: dict[str, int] = {}
    for c in candidates:
        m = _STATUS_RE.match(frame.status_map[c.item_id])
        if m:
            reasons[m.group(1)] = reasons.get(m.group(1), 0) + 1
    pool_ids = {c.item_id for c in candidates}
    record = {
        "kind": "body_available",
        "status_map_sha256": frame.status_map_sha256,
        "n_status_entries": len(frame.status_map),
        "n_status_entries_outside_pool": sum(1 for k in frame.status_map if k not in pool_ids),
        "n_candidates_pre_frame": len(candidates),
        "n_candidates_in_frame": len(kept),
        "excluded_reasons": dict(sorted(reasons.items())),
        "pre_frame_cells": _cell_counts(candidates),
        "frame_cells": _cell_counts(kept),
    }
    return kept, record


def _apply_gate_frame(
    candidates: tuple[Candidate, ...], frame: GateFrame
) -> tuple[tuple[Candidate, ...], dict[str, Any]]:
    """Keep the gated-in candidates of a body-framed pool; every one must carry a status."""
    missing = sorted(c.item_id for c in candidates if c.item_id not in frame.gate_map)
    if missing:
        raise TapeDrawError(
            f"gate frame map lacks {len(missing)} in-frame candidate item_id(s), "
            f"first {missing[:3]!r}: the map must cover the body-available pool"
        )
    stale = sorted(c.item_id for c in candidates if frame.gate_map[c.item_id] == "gated_out:no_body")
    if stale:
        raise TapeDrawError(
            f"gate frame map marks {len(stale)} body-available candidate(s) no_body, "
            f"first {stale[:3]!r}: the map was built from different bodies"
        )
    kept = tuple(c for c in candidates if frame.gate_map[c.item_id] == "gated_in")
    codes: dict[str, int] = {}
    for c in candidates:
        code = GATE_STATUS_RE.match(frame.gate_map[c.item_id]).group(1)
        if code:
            codes[code] = codes.get(code, 0) + 1
    record = {
        "kind": "routing_gates",
        "gate_map_sha256": frame.gate_map_sha256,
        "n_gate_entries": len(frame.gate_map),
        "n_candidates_pre_gate": len(candidates),
        "n_candidates_gated_in": len(kept),
        "excluded_codes": dict(sorted(codes.items())),
        "gated_cells": _cell_counts(kept),
    }
    return kept, record


def run_draw(
    tape_path: str,
    event_log_path: str,
    reject_sample_path: str,
    ledger_path: str,
    *,
    seed: int,
    window_start: date | None = None,
    window_end: date | None = None,
    prospective_from: date | None = None,
    low_value: Callable[..., bool] | None = None,
    body_frame: BodyFrame | None = None,
    gate_frame: GateFrame | None = None,
    fallback_ledger_path: str | None = None,
) -> TapeDrawResult:
    """Run the full tape -> draw pipeline (S12).

    With ``body_frame`` the draw runs over the body-available candidates only, with
    the same seed, sampler and caps; the report records the frame (status-map sha,
    pre-frame and in-frame cell counts, exclusion reasons). Short cells stay short.
    With ``gate_frame`` (which requires ``body_frame``) the draw further keeps the
    gated-in candidates and the report gains a ``gate_frame`` record; without it the
    report is unchanged. With ``fallback_ledger_path`` unresolved rows are re-resolved
    fill-only (:func:`fill_only_ledger`) and the report records the fallback file's
    sha256; without it the report is unchanged.
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TapeDrawError(f"seed must be an int: {seed!r}")
    if gate_frame is not None and body_frame is None:
        raise TapeDrawError("gate_frame requires body_frame: the gates read attached filing bodies")

    if low_value is None:
        low_value = _make_default_low_value()

    event_log_rows = _read_parquet_dicts(event_log_path)
    reject_rows = _read_parquet_dicts(reject_sample_path)

    from engine.news_impact.issuer import load_ledger

    ledger = load_ledger(ledger_path)
    fallback_ledger = load_ledger(fallback_ledger_path) if fallback_ledger_path else None

    dropped: dict[str, int] = {}
    wide_rows = load_tape(
        tape_path,
        window_start=date(1970, 1, 1),
        window_end=date(2100, 12, 31),
        dropped=dropped,
    )

    total_rows = len(wide_rows) + int(sum(dropped.values()))
    window_start, window_end = _resolve_run_window(
        wide_rows, window_start, window_end
    )

    build = build_candidates(
        wide_rows,
        window_start=window_start,
        window_end=window_end,
        event_log_rows=event_log_rows,
        reject_rows=reject_rows,
        ledger=ledger,
        low_value=low_value,
        dropped=dropped,
        total_rows=total_rows,
        fallback_ledger=fallback_ledger,
    )

    tape_sha = _read_tape_bytes(tape_path)
    plan = SamplePlan(
        seed=seed,
        window_start=window_start,
        window_end=window_end,
        tape_sha256=tape_sha,
        prospective_from=prospective_from,
    )

    frame_record: dict[str, Any] | None = None
    draw_pool = build.candidates
    gate_record: dict[str, Any] | None = None
    if body_frame is not None:
        draw_pool, frame_record = _apply_body_frame(build.candidates, body_frame)
    if gate_frame is not None:
        draw_pool, gate_record = _apply_gate_frame(draw_pool, gate_frame)

    draw = draw_sample(
        draw_pool,
        plan,
        rights_allow=_rights_allow,
        economic_cluster=None,
    )

    rebuilt = build_manifest(
        plan,
        draw.cases,
        {
            "outside_window": (
                build.report["funnel"]["outside_window"]
                + draw.manifest["counters"]["outside_window"]
            ),
            "low_value": build.report["funnel"]["low_value"],
            "unresolved_issuer": draw.manifest["counters"]["unresolved_issuer"],
            "rights_refused": 0,
        },
        stats={
            "megacap_share": draw.manifest["megacap_share"],
            "economic_cluster": draw.manifest["economic_cluster"],
        },
    )

    for key in draw.manifest:
        if key in ("counters", "manifest_sha256"):
            continue
        if rebuilt.get(key) != draw.manifest[key]:
            raise TapeDrawError(
                f"rebuilt manifest key {key!r} differs from draw.manifest"
            )

    report = dict(build.report)
    report["tape_sha256"] = tape_sha
    report["drawn_cells"] = rebuilt["cells"]
    report["manifest_sha256"] = rebuilt["manifest_sha256"]
    report["frame"] = frame_record if frame_record is not None else {"kind": "full_pool"}
    if gate_record is not None:
        report["gate_frame"] = gate_record
    if fallback_ledger_path:
        with open(fallback_ledger_path, "rb") as f:
            report["fallback_ledger"]["sha256"] = sha256(f.read()).hexdigest()

    return TapeDrawResult(
        draw=draw,
        manifest=rebuilt,
        meta=build.meta,
        report=report,
        candidates=build.candidates,
    )


# --- attach_body_accounting (S13) --------------------------------------------


_STATUS_RE = re.compile(r"^body_unavailable:([a-z0-9_]+)$")


def attach_body_accounting(
    report: dict,
    status_map: Mapping[str, str],
    cases: Iterable[Case],
) -> dict:
    """Add 'body' accounting to a copy of report (S13). Never mutate the input."""
    new_report = copy.deepcopy(report)
    body: dict[str, dict[str, dict[str, Any]]] = {
        t: {c: {"drawn": 0, "available": 0, "body_unavailable": 0, "reasons": {}} for c in CELLS}
        for t in TEMPLATES
    }
    case_ids: set[str] = set()
    for case in cases:
        item_id = case.item_id
        if item_id in case_ids:
            raise TapeDrawError(f"duplicate case item_id: {item_id!r}")
        case_ids.add(item_id)
        if item_id not in status_map:
            raise TapeDrawError(f"status_map missing item_id: {item_id!r}")
        status = status_map[item_id]
        if status == "available":
            body[case.template][case.proxy_cell]["drawn"] += 1
            body[case.template][case.proxy_cell]["available"] += 1
            continue
        m = _STATUS_RE.match(status)
        if not m:
            raise TapeDrawError(
                f"malformed status for item_id {item_id!r}: {status!r}"
            )
        reason = m.group(1)
        body[case.template][case.proxy_cell]["drawn"] += 1
        body[case.template][case.proxy_cell]["body_unavailable"] += 1
        reasons = body[case.template][case.proxy_cell]["reasons"]
        reasons[reason] = reasons.get(reason, 0) + 1

    for item_id in status_map:
        if item_id not in case_ids:
            raise TapeDrawError(f"status_map has extra item_id: {item_id!r}")

    totals = {"drawn": 0, "available": 0, "body_unavailable": 0}
    for t in TEMPLATES:
        for c in CELLS:
            for k in ("drawn", "available", "body_unavailable"):
                totals[k] += body[t][c][k]

    new_report["body"] = body
    new_report["body_totals"] = totals
    return new_report


# --- CLI (S14) ----------------------------------------------------------------


def _parse_optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise TapeDrawError(f"invalid date {value!r}: {exc}") from exc


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine.news_impact.tape_draw",
        description=(
            "Turn a news tape into sampler Candidates, run the draw, and write "
            "the draw artifacts (cases.jsonl, manifest.json, candidates_meta.jsonl, "
            "draw_report.json) to --out."
        ),
    )
    parser.add_argument("--tape", required=True, help="path to the tape parquet")
    parser.add_argument("--event-log", required=True, help="path to event_log parquet")
    parser.add_argument(
        "--reject-sample", required=True, help="path to reject_sample parquet"
    )
    parser.add_argument("--ledger", required=True, help="path to ticker->CIK ledger json")
    parser.add_argument(
        "--fallback-ledger",
        default=None,
        help=(
            "ticker->CIK ledger json consulted only for rows --ledger leaves unresolved, "
            "and only for tickers --ledger does not carry (report records its sha256)"
        ),
    )
    parser.add_argument("--seed", required=True, type=int, help="sampler seed (int)")
    parser.add_argument("--out", required=True, help="output directory (created if missing)")
    parser.add_argument("--window-start", default=None, help="ISO date override")
    parser.add_argument("--window-end", default=None, help="ISO date override")
    parser.add_argument(
        "--prospective-from", default=None, help="ISO date for the prospective cohort"
    )
    parser.add_argument(
        "--candidates-out",
        default=None,
        help="also write every pre-frame candidate (JSONL, one dict per line) here",
    )
    parser.add_argument(
        "--body-frame",
        default=None,
        help=(
            "edgar_body status_map.json covering the full candidate pool; draw only "
            "over body-available candidates (report records the frame)"
        ),
    )
    parser.add_argument(
        "--gate-frame",
        default=None,
        help=(
            "routing_gates gate map covering the body-available pool; requires "
            "--body-frame and draws only over gated-in candidates"
        ),
    )
    return parser


def main(argv: list[str] | None = None, *, low_value: Callable[..., bool] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        window_start = _parse_optional_date(args.window_start)
        window_end = _parse_optional_date(args.window_end)
        prospective_from = _parse_optional_date(args.prospective_from)
        body_frame = load_body_frame(args.body_frame) if args.body_frame else None
        gate_frame = load_gate_frame(args.gate_frame) if args.gate_frame else None
        result = run_draw(
            args.tape,
            args.event_log,
            args.reject_sample,
            args.ledger,
            seed=args.seed,
            window_start=window_start,
            window_end=window_end,
            prospective_from=prospective_from,
            low_value=low_value,
            body_frame=body_frame,
            gate_frame=gate_frame,
            fallback_ledger_path=args.fallback_ledger,
        )

        out_dir = args.out
        import os
        os.makedirs(out_dir, exist_ok=True)

        cases_path = os.path.join(out_dir, "cases.jsonl")
        with open(cases_path, "w", encoding="utf-8") as f:
            for case in result.draw.cases:
                f.write(json.dumps(case.to_dict(), sort_keys=True) + "\n")

        manifest_path = os.path.join(out_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n")

        meta_path = os.path.join(out_dir, "candidates_meta.jsonl")
        with open(meta_path, "w", encoding="utf-8") as f:
            for meta in result.meta:
                f.write(json.dumps(meta, sort_keys=True, default=str) + "\n")

        if args.candidates_out:
            with open(args.candidates_out, "w", encoding="utf-8") as f:
                for cand in sorted(result.candidates, key=lambda c: c.item_id):
                    f.write(json.dumps(candidate_to_dict(cand), sort_keys=True) + "\n")

        report_path = os.path.join(out_dir, "draw_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(result.report, indent=2, sort_keys=True, default=str) + "\n")

        print(
            json.dumps(
                {
                    "cases": len(result.draw.cases),
                    "manifest_sha256": result.manifest["manifest_sha256"],
                    "frame": result.report["frame"]["kind"],
                    "out": out_dir,
                }
            )
        )
        return 0
    except (TapeDrawError, SamplerError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
