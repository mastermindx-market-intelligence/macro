"""C19 WP31 evaluator — RUNNER: one injected-I/O evaluator read (wave-2 spec §4).

Governing documents
-------------------
- Preregistration: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``,
  registered as PREREG_COMMIT ``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c``
  (amendments A1-A4 in its §10).  The prereg wins any conflict with the build
  spec; never redesign, never widen.
- Frozen wave-2 build spec: ``WP31_WAVE2_SPEC.md`` (seat stage), sha256
  ``bb0ad59a0671da03c940b1c7f1a97f037146c12e42207bf5d4a7bf96d5de4a17``.

:func:`run_evaluation` composes the wave-1 gates and stats with the wave-1/2
sources into ONE evaluator read whose every I/O is injected, so the wave-3
seat wires production fetchers in without touching statistical logic:

- ``doc_bytes`` / ``is_ancestor_of_head`` / ``ledger_lines`` feed the three
  prereg gates (``scripts/c19_wp31_gates.py``); a ``WP31Refusal`` propagates —
  no read happens without all three gates.
- ``filing_rows`` / ``fetch_index_headers`` feed EX-99.1 enrichment and episode
  enumeration (``scripts/c19_wp31_sources.py``).
- ``k_inputs(issuer, cutoff, period_end)`` returns the kwargs for
  ``sources.k_from_surface`` or ``None``; ``companyfacts(issuer)`` returns the
  facts JSON or ``None``; ``submissions_pages(issuer)`` returns a tuple of
  submissions pages; ``revisions_reader`` is the (batched) revision-chain
  reader; ``resolve_ticker`` the identity resolver; ``exposure_path`` the
  exposure-ledger JSONL; ``now`` the aware-UTC instant of this read.

NO ``__main__``, NO CLI, NO network, NO file read at import time (wave-3 adds
the CLI and the production fetchers).  Standard library plus numpy/pandas only,
with the sibling scripts imported lazily inside :func:`run_evaluation`.

WARNING: the returned ``episodes`` carry LABEL VALUES (prereg §3.3).  The
wave-3 CLI must never print ``episodes`` to a console or log; it prints the
report only.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

__all__ = ["run_evaluation"]

#: Label-maturity bound (prereg §3.3): 120 days after the quarter's period end.
_LABEL_DAYS = 120


def run_evaluation(
    *,
    doc_bytes: bytes,
    is_ancestor_of_head: Callable[[str], bool],
    ledger_lines: Iterable[str],
    filing_rows: Sequence[Mapping[str, Any]],
    fetch_index_headers: Callable[[Any, Any], object],
    k_inputs: Callable[[str, datetime, str], Mapping[str, Any] | None],
    companyfacts: Callable[[str], Any],
    submissions_pages: Callable[[str], Sequence[Any]],
    exposure_path: Any,
    now: datetime,
    prior_reads: Sequence[Mapping[str, Any]] = (),
    resolve_ticker: Callable[..., Any] | None = None,
    revisions_reader: Callable[..., Any] | None = None,
    max_hops: int = 500,
) -> dict[str, Any]:
    """One evaluator read over injected I/O (wave-2 spec §4; prereg §2-§6).

    Steps, in order: (1) the three gates — a ``WP31Refusal`` propagates;
    (2) EX-99.1 enrichment + episode enumeration; (3) per-episode K, an
    unavailable ``k_inputs`` giving ``_empty_k()`` with
    ``abstain_reason="k_inputs_unavailable"``; (4) one batched S chain read
    (:func:`sources.collect_s_legs`) attached as ``ep["s"]``; (5) per-issuer
    facts and prior filings read once, the q filing located BY PERIOD END in
    the original-filing quarterly facts (zero or several matches -> no q
    filing), the exposure ledger recorded BEFORE the label is read (the
    companyfacts read IS the label read, prereg §6), the label and A0
    computed through ``sources.label_and_a0_from_companyfacts`` (with
    ``q_accession=""`` when no q filing — a read is never recorded then; facts
    ``None`` -> ``label=None`` and ``a0=_empty_a0()``); (6) a pre-existing
    non-evaluator label read marks every still-ELIGIBLE episode EXPOSED,
    whether or not step 5 recorded a read; (7) the leak rules; (8) label
    status: ``label_tie`` -> NOT_EVALUABLE, a missing label more than 120
    days after the period end -> ``label_unavailable``, otherwise the episode
    stays ELIGIBLE with ``label=None`` and is counted in ``label_pending``
    (outside common support because the label is not +/-1 — never relabeled
    early); (9) ``stats.build_report(episodes, prior_reads)``.

    Returns ``{"gates", "report", "label_pending", "exhibit_failures",
    "episode_count", "episodes"}``.  ``episodes`` carries label values — the
    wave-3 CLI must print the report only, never the episodes.
    """
    from scripts import c19_wp31_gates as gates
    from scripts import c19_wp31_sources as sources
    from scripts import c19_wp31_stats as stats

    # 1. Gates — a WP31Refusal propagates; no read happens without all three.
    receipts = [
        gates.check_doc_hash(doc_bytes),
        gates.check_merged_ancestry(is_ancestor_of_head),
        gates.check_budget_row(ledger_lines),
    ]

    now_utc = sources._aware_utc(now, label="now")
    now_iso = sources._iso_utc(now_utc)

    # 2. Episodes (EX-99.1 manifest enrichment, then enumeration).
    rows, exhibit_failures = sources.enrich_exhibits(
        filing_rows, fetch_index_headers=fetch_index_headers
    )
    episodes = sources.enumerate_episodes(rows)

    # 3. K per episode.
    for ep in episodes:
        cutoff_dt = sources._parse_utc(ep.get("cutoff"))
        kwargs = k_inputs(ep["issuer"], cutoff_dt, ep["period_end"])
        if kwargs is None:
            k = sources._empty_k()
            k["abstain_reason"] = "k_inputs_unavailable"
        else:
            k = sources.k_from_surface(**kwargs)
        ep["k"] = k

    # 4. S legs — EXACTLY ONE revisions-reader call for all episodes.
    legs = sources.collect_s_legs(
        episodes,
        resolve_ticker=resolve_ticker,
        revisions_reader=revisions_reader,
        max_hops=max_hops,
    )
    for ep in episodes:
        ep["s"] = legs.get((ep["issuer"], ep["q"]), sources._empty_s())

    # 5. Label + A0 — per-issuer facts and prior filings read once; the
    #    exposure ledger is recorded BEFORE the label is read (prereg §6).
    facts_cache: dict[str, Any] = {}
    prior_cache: dict[str, list[dict[str, str]]] = {}
    for ep in episodes:
        issuer = ep["issuer"]
        if issuer not in facts_cache:
            facts_cache[issuer] = companyfacts(issuer)
        if issuer not in prior_cache:
            prior_cache[issuer] = sources.prior_filings_from_submissions(
                *submissions_pages(issuer)
            )
        facts = facts_cache[issuer]
        if facts is None:
            ep["label"] = None
            ep["a0"] = sources._empty_a0()
            continue
        episode_end = sources._parse_day(ep.get("period_end"))
        quarterly = sources._quarterly_eps_filings(facts)
        q_period_matches = _q_period_matches(quarterly, episode_end)
        q_accession = _q_accession_for_period(quarterly, episode_end)
        # Wave-3 spec §3: record whenever the facts JSON holds AT LEAST ONE
        # original-filing EPS context for the episode period (one OR several
        # matches).  Zero matches -> no record (no label value exists to read
        # for this episode).  The whole facts JSON is in memory either way,
        # so this is more conservative under prereg §6 and needs none.
        if q_period_matches:
            gates.record_label_read(
                exposure_path, issuer, ep["q"], gates.EVALUATOR_READER, now_iso
            )
        read = sources.label_and_a0_from_companyfacts(
            facts,
            ep["period_end"],
            q_accession or "",
            sources._parse_utc(ep.get("cutoff")),
            prior_cache[issuer],
        )
        ep["label"] = read["label"]
        ep["a0"] = read["a0"]
        if read["not_evaluable_reason"] and ep.get("not_evaluable_reason") is None:
            ep["not_evaluable_reason"] = read["not_evaluable_reason"]

    # 6. Exposure — an outside read of the release exposes the episode even
    #    when step 5 recorded the evaluator's own first read for another leg.
    for ep in episodes:
        if ep["status"] == "ELIGIBLE" and gates.is_exposed(
            exposure_path, ep["issuer"], ep["q"]
        ):
            ep["status"] = "EXPOSED"

    # 7. Leaks (returns copies — rebind).
    episodes = [sources.apply_leak_rules(ep) for ep in episodes]

    # 8. Label status for still-ELIGIBLE episodes.
    label_pending = 0
    for ep in episodes:
        if ep["status"] != "ELIGIBLE":
            continue
        if ep.get("not_evaluable_reason") == "label_tie":
            ep["status"] = "NOT_EVALUABLE"
            continue
        if ep.get("label") is None:
            period_end = sources._parse_day(ep.get("period_end"))
            if period_end is None or now_utc.date() > period_end + timedelta(
                days=_LABEL_DAYS
            ):
                ep["status"] = "NOT_EVALUABLE"
                ep["not_evaluable_reason"] = "label_unavailable"
            else:
                label_pending += 1  # stays ELIGIBLE, label None; never early-relabeled

    # 9. Report.
    report = stats.build_report(episodes, prior_reads)
    return {
        "gates": receipts,
        "report": report,
        "label_pending": label_pending,
        "exhibit_failures": exhibit_failures,
        "episode_count": len(episodes),
        "episodes": episodes,
    }


def _q_accession_for_period(
    filings: Mapping[str, Mapping[Any, float]], target: Any
) -> str | None:
    """The single accession whose latest fact end equals ``target``, or None.

    Wave-2 semantics retained for the label read: zero or several matches ->
    no q filing for ``_q_accession_for_period`` (the label read refuses an
    ambiguous filing set rather than guessing).  Wave-3 introduces
    :func:`_q_period_matches` so the EXPOSURE LEDGER records whenever at
    least one original-filing EPS context for the episode period exists in
    the facts JSON (one OR several matches), not only exactly one — prereg
    §6: the whole JSON is in memory either way; the more-conservative read
    is to record.
    """
    if target is None:
        return None
    matches = _q_period_matches(filings, target)
    if len(matches) != 1:
        return None
    return matches[0]


def _q_period_matches(
    filings: Mapping[str, Mapping[Any, float]], target: Any
) -> list[str]:
    """Accessions whose latest fact end equals ``target``, sorted (wave-3 §3).

    Returns the empty list when ``target`` is ``None`` or no filing carries
    the episode's period end.  One or several matches -> the episode has at
    least one original-filing EPS context; the exposure ledger is then
    recorded BEFORE the label value is touched.
    """
    if target is None:
        return []
    matches = [
        accession
        for accession, ends in filings.items()
        if ends and max(ends) == target  # ends is never empty (sources builds it so)
    ]
    matches.sort()
    return matches
