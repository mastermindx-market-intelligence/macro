"""Descriptive relationship renderer (GMI ORCH-REL M3): "if X, the filing says".

Renders each relationship edge as plain-language sentences built ONLY from the
frozen premise templates (``describe_premises_v1.json``, sha-pinned below) plus
the filing's own verbatim words re-derived from pinned excerpt bytes.  A fixed
premise ("If the agreement is terminated") is followed by the lead-in and the
verbatim condition text; a disclosed magnitude is restated with the filing's
own scope strings; a correction history is narrated publication by publication.
No consequence, probability, score, ranking or advice is ever inferred or
added, and a quote that cannot be re-derived from pinned bytes is never
printed (QUOTE_UNVERIFIED).

Pure module: no network import, no wall-clock call.  Point-in-time behaviour is
a pure function of the bytes handed in — the caller decides which package is
"current".  This module is a renderer, not a producer of record, not a store,
not a gate and not a site page (ORCH-UI consumes its JSON later).
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.company_intelligence.relationships import (
    CORRUPT,
    normalize_span,
    sha,
)
from engine.company_intelligence.relationships.replay import verify_excerpt

PREMISES_RELPATH = (
    "research/theme_graph/gmi_relationships_20261021/m3/describe_premises_v1.json"
)
#: sha256 of the frozen premise-table bytes (ORCH-REL, 2026-10-22).  Any other
#: bytes are refused (PremisesDrift -> the CLI exits 2 PREMISES_DRIFT).
PREMISES_SHA256 = "0394589fe14e92a7f9c3963a9b8adb8fa6477cc4fc66bd1a7c5f40ecadba6786"
REPORT_SCHEMA = "gmi_rel_m3.describe_report/v1"
DEMO_SCHEMA = "gmi_rel_m3.correction_demo/v1"

#: The per-edge rights line (spec-pinned text; the state slot is the edge's
#: own ``rights.public_display``).  Public display rights are the Chairman's
#: A7 ruling alone — this renderer decides nothing.
RIGHTS_LINE_EN = (
    "display rights: {state}; public display of verbatim excerpts awaits the "
    "Chairman rights ruling (A7)"
)
RIGHTS_LINE_ZH = "展示权限：{state}；逐字引文的公开展示须待主席权利裁定（A7）"

#: Counted kind for an unverifiable per-source_ref quote (conditions count
#: under their own condition kind).
SOURCE_REF_KIND = "source_ref"


class PremisesDrift(Exception):
    """The premise-table bytes do not hash to the pinned PREMISES_SHA256."""


# --- premise table -------------------------------------------------------------


def load_premises(data: bytes) -> dict:
    """Parse the premise table from exact bytes; refuse any drift."""
    if sha(data) != PREMISES_SHA256:
        raise PremisesDrift(
            f"premises bytes hash {sha(data)} != pinned {PREMISES_SHA256}"
        )
    return json.loads(data.decode("utf-8"))


def load_premises_file(path) -> dict:
    return load_premises(Path(path).read_bytes())


# --- excerpts ------------------------------------------------------------------


def load_excerpt_map(sources_root, accessions, base=None) -> tuple[dict, dict]:
    """(excerpts, inputs) for exactly the needed accessions.

    Layout follows the producer's A33 convention: a flat
    ``<dirs>/<accession>.json`` or a nested ``<dirs>/<accession>/<sha20>.json``.
    Excerpts bind by CONTENT (``span.raw_sha256``), so the citation key always
    selects the pinned bytes; two files claiming the same span with different
    bytes poison the whole accession (CORRUPT), exactly like the producer.
    ``inputs`` maps path -> sha256 for every file actually read; paths are
    relativized against ``base`` (repo-relative when inside it, absolute
    otherwise).
    """
    wanted = set(accessions)
    groups: dict = {}
    root = Path(sources_root)
    paths = sorted(
        (path for path in root.rglob("*.json") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    ) if root.is_dir() else []
    for path in paths:
        if path.stem in wanted:  # flat <accession>.json
            groups.setdefault(path.stem, []).append(path)
        elif path.parent.name in wanted:  # nested <accession>/<sha20>.json
            groups.setdefault(path.parent.name, []).append(path)

    excerpts: dict = {}
    inputs: dict = {}
    base = Path(base).resolve() if base is not None else None

    def _record(path, payload):
        resolved = Path(path).resolve()
        rel = str(path)
        if base is not None:
            try:
                rel = resolved.relative_to(base).as_posix()
            except ValueError:
                rel = str(resolved)
        inputs[rel] = sha(payload)

    for accession in sorted(groups):
        keyed: dict = {}  # span raw_sha256 -> (payload sha, doc)
        poisoned = False
        for path in groups[accession]:
            try:
                payload = path.read_bytes()
                doc = json.loads(payload.decode("utf-8"))
            except (OSError, ValueError):
                poisoned = True
                continue
            _record(path, payload)
            span = doc.get("span") if isinstance(doc, dict) else None
            span_sha = span.get("raw_sha256") if isinstance(span, dict) else None
            if (
                not isinstance(doc, dict)
                or doc.get("accession") != accession
                or not isinstance(span_sha, str)
            ):
                poisoned = True
                continue
            prior = keyed.get(span_sha)
            if prior is not None and prior[0] != sha(payload):
                poisoned = True  # same span, differing bytes
                continue
            keyed[span_sha] = (sha(payload), doc)
        if poisoned:
            excerpts[accession] = CORRUPT
            continue
        for span_sha, (_psha, doc) in keyed.items():
            excerpts[(accession, span_sha)] = doc
        if len(keyed) == 1:
            excerpts[accession] = next(iter(keyed.values()))[1]
    for accession in sorted(wanted - set(groups)):
        excerpts[accession] = None
    return excerpts, inputs


def lookup_excerpt(excerpts: dict, accession, span_sha256=None):
    """Poison sentinel, then the (accession, span) key, then the plain view."""
    plain = excerpts.get(accession)
    if isinstance(plain, str):  # CORRUPT wins over everything
        return plain
    if span_sha256 is not None:
        keyed = excerpts.get((accession, span_sha256))
        if keyed is not None:
            return keyed
    return plain


def excerpt_usable(excerpt) -> bool:
    """True when the excerpt dict re-derives every pinned hash (offline)."""
    return isinstance(excerpt, dict) and not verify_excerpt(excerpt)


# --- naming and value formatting ------------------------------------------------


def sec_name_map(resolver_rows) -> dict:
    """issuer_id -> sec_name from resolver_us_issuers_v1.json rows."""
    names = {}
    for row in resolver_rows or []:
        if isinstance(row, dict) and isinstance(row.get("issuer_id"), str):
            names[row["issuer_id"]] = row.get("sec_name")
    return names


def party_name(issuer_id, edge_side, sec_names: dict) -> str:
    """resolver sec_name, else the edge side's name_as_filed, else the
    ticker-shaped suffix of the issuer id."""
    if issuer_id in sec_names:
        return sec_names[issuer_id]
    name = (edge_side or {}).get("name_as_filed")
    if isinstance(name, str) and name:
        return name
    return issuer_id.rsplit("-", 1)[-1] if issuer_id else "unknown"


def _number(value) -> str:
    if value is None or isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, int):
        return str(value)
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(value)


def _fmt_value(value, value_high, unit, precision) -> str:
    """The one magnitude rendering: a ratio at exact precision is value*100
    rounded to 0 dp with the template's own ``%``; a range is the raw
    ``value..value_high``; anything else is ``value unit``."""
    if (
        unit == "ratio"
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        if precision == "range" and isinstance(value_high, (int, float)):
            return f"{_number(value)}..{_number(value_high)}"
        return f"{round(value * 100)}%"
    text = _number(value)
    if unit:
        text = f"{text} {unit}"
    return text


def _fmt_revision(revision: dict) -> str:
    return _fmt_value(
        revision.get("value"),
        revision.get("value_high"),
        revision.get("unit"),
        revision.get("precision"),
    )


def _pct_slot(entry: dict) -> str:
    """The {pct} slot of a share template (frozen rule (a)): value*100 at 0 dp
    when exact (the template carries its own ``%``), else raw
    ``value..value_high``; a non-ratio unit falls through unchanged."""
    if entry.get("unit") == "ratio":
        text = _fmt_value(
            entry.get("value"), entry.get("value_high"), "ratio",
            entry.get("precision"),
        )
        return text[:-1] if text.endswith("%") else text
    return _fmt_value(
        entry.get("value"), entry.get("value_high"), entry.get("unit"),
        entry.get("precision"),
    )


# --- line builders ---------------------------------------------------------------


def line(display_class: str, en: str, zh: str, citation) -> dict:
    return {
        "display_class": display_class,
        "en": en,
        "zh": zh,
        "citation": citation,
    }


def _citation(
    accession=None, form=None, byte_start=None, byte_end=None,
    span_sha256=None, url=None,
) -> dict:
    return {
        "accession": accession,
        "form": form,
        "byte_start": byte_start,
        "byte_end": byte_end,
        "span_sha256": span_sha256,
        "url": url,
    }


def condition_verified(condition: dict, excerpts: dict) -> bool:
    """Re-derive the condition text from the pinned excerpt bytes.

    A candidate excerpt for ``condition.accession`` must carry a span covering
    ``[byte_start, byte_end)``; the raw UTF-8 bytes sliced at
    ``(byte_start - span.byte_start, byte_end - span.byte_start)`` must hash
    (raw or normalized) to ``condition.span_sha256`` AND normalize to the same
    text as ``condition.text``.  Anything else refuses the quote.  Candidates
    are every excerpt of the accession (its span key binds by content), walked
    in sorted span-sha order.
    """
    accession = condition.get("accession")
    candidates = [
        doc
        for key, doc in sorted(excerpts.items(), key=lambda item: str(item[0]))
        if isinstance(key, tuple) and key[0] == accession and isinstance(doc, dict)
    ]
    plain = excerpts.get(accession)
    if isinstance(plain, dict) and all(plain is not doc for doc in candidates):
        candidates.append(plain)
    start, end = condition.get("byte_start"), condition.get("byte_end")
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    text = condition.get("text") or ""
    for excerpt in candidates:
        if not excerpt_usable(excerpt):
            continue
        span = excerpt["span"]
        raw = span["raw"].encode("utf-8")
        if not (span["byte_start"] <= start < end <= span["byte_end"]):
            continue
        slice_bytes = raw[start - span["byte_start"]: end - span["byte_start"]]
        if (
            sha(slice_bytes) != condition.get("span_sha256")
            and sha(normalize_span(slice_bytes)) != condition.get("span_sha256")
        ):
            continue
        if normalize_span(slice_bytes) == normalize_span(text.encode("utf-8")):
            return True
    return False


# --- the renderer ----------------------------------------------------------------


def describe_edges(edges, excerpts: dict, premises: dict,
                   sec_names: dict) -> tuple[list, dict]:
    """(entries, counters) for the given edges, sorted by relationship_key."""
    entries = [
        _render_edge(edge, premises, sec_names, excerpts)
        for edge in sorted(edges, key=lambda e: e["relationship_key"])
    ]
    counters = {
        "edges": len(entries),
        "lines_by_class": {},
        "quote_verified": 0,
        "quote_unverified_by_kind": {},
        "conditions_by_kind": {},
        "restatements_found": 0,
        "reassertions_found": 0,
    }
    for entry in entries:
        for line in entry["lines"]:
            klass = line["display_class"]
            counters["lines_by_class"][klass] = (
                counters["lines_by_class"].get(klass, 0) + 1
            )
            if klass == "verbatim_excerpt":
                counters["quote_verified"] += 1
        counters["quote_unverified_by_kind"] = _merge_counts(
            counters["quote_unverified_by_kind"], entry["_quote_unverified"]
        )
        counters["conditions_by_kind"] = _merge_counts(
            counters["conditions_by_kind"], entry["_conditions_by_kind"]
        )
        counters["restatements_found"] += entry["_restatements"]
        counters["reassertions_found"] += entry["_reassertions"]
        for private in ("_quote_unverified", "_conditions_by_kind",
                        "_restatements", "_reassertions"):
            del entry[private]
    return entries, counters


def _merge_counts(base: dict, extra: dict) -> dict:
    merged = dict(base)
    for key, count in extra.items():
        merged[key] = merged.get(key, 0) + count
    return merged


def _render_edge(edge: dict, premises: dict, sec_names: dict,
                 excerpts: dict) -> dict:  # noqa: C901
    direction = edge.get("direction") or {}
    from_side = edge.get("from") or {}
    to_side = edge.get("to") or {}
    from_name = party_name(direction.get("from_issuer_id"), from_side, sec_names)
    to_name = party_name(direction.get("to_issuer_id"), to_side, sec_names)
    lead_in_en = premises["lead_in"]["en"]
    lead_in_zh = premises["lead_in"]["zh"]

    lines: list = []
    unverified: dict = {}
    conditions_by_kind: dict = {}
    restatements = 0
    reassertions = 0

    def _count(bucket: dict, key: str) -> None:
        bucket[key] = bucket.get(key, 0) + 1

    # (a) derived facts — one per current_magnitudes entry, from the frozen
    # magnitude templates; a conflicted (kind, period) renders the conflict
    # sentence for each disagreeing party instead of choosing a value.
    conflicted_kinds = {c["kind"] for c in edge.get("conflicts") or []}
    if edge.get("magnitude_state") == "undisclosed":
        undisclosed = premises["magnitude"]["undisclosed"]
        lines.append(line(
            "derived_fact",
            undisclosed["en"].format(party=from_name),
            undisclosed["zh"].format(party=from_name),
            None,
        ))
    for magnitude in edge.get("current_magnitudes") or []:
        kind = magnitude["kind"]
        if kind in conflicted_kinds:
            continue  # rendered as corrections.conflict below — never chosen
        party = party_name(magnitude.get("asserting_party"), from_side, sec_names)
        period = (magnitude.get("period") or {}).get("label")
        template = premises["magnitude"].get(kind) or premises["magnitude"]["default"]
        if "pct" in template["en"]:
            slots = {
                "party": party,
                "numerator_scope": magnitude.get("numerator_scope"),
                "denominator_scope": magnitude.get("denominator_scope"),
                "pct": _pct_slot(magnitude),
                "period": period,
            }
        else:
            slots = {
                "party": party,
                "kind": kind,
                "value": _fmt_value(
                    magnitude.get("value"), magnitude.get("value_high"),
                    magnitude.get("unit"), magnitude.get("precision"),
                ),
                "unit": magnitude.get("unit"),
                "period": period,
            }
        source = magnitude.get("source_ref") or {}
        lines.append(line(
            "derived_fact",
            template["en"].format(**slots),
            template["zh"].format(**slots),
            _citation(
                accession=source.get("accession"),
                form=source.get("form"),
                byte_start=source.get("byte_start"),
                byte_end=source.get("byte_end"),
                span_sha256=source.get("span_sha256"),
            ),
        ))
    for conflict in edge.get("conflicts") or []:
        template = premises["corrections"]["conflict"]
        values = conflict.get("values") or []
        revisions = {
            revision["revision_id"]: revision
            for revision in edge.get("magnitude_history") or []
        }
        slots = []
        for side in values[:2]:
            revision = revisions.get(side.get("revision_id")) or {}
            slots.append((
                party_name(side.get("asserting_party"), from_side, sec_names),
                _fmt_value(
                    side.get("value"), revision.get("value_high"),
                    revision.get("unit"), revision.get("precision"),
                ),
            ))
        while len(slots) < 2:
            slots.append(("unknown", "unknown"))
        named = {
            "period": (conflict.get("period") or {}).get("label"),
            "party_a": slots[0][0],
            "value_a": slots[0][1],
            "party_b": slots[1][0],
            "value_b": slots[1][1],
        }
        lines.append(line(
            "conflict", template["en"].format(**named),
            template["zh"].format(**named), None,
        ))

    # (b) one verbatim line per source_ref — ONLY after offline re-derivation.
    for source in edge.get("source_refs") or []:
        excerpt = lookup_excerpt(
            excerpts, source.get("accession"), source.get("span_sha256")
        )
        span = excerpt.get("span") if isinstance(excerpt, dict) else None
        span_ok = (
            isinstance(span, dict)
            and span.get("raw_sha256") == source.get("span_sha256")
        )
        if not span_ok or not excerpt_usable(excerpt):
            _count(unverified, SOURCE_REF_KIND)
            continue
        text = span["normalized"]
        lines.append(line(
            "verbatim_excerpt",
            f"{lead_in_en} {text}",
            f"{lead_in_zh}{text}",
            _citation(
                accession=source.get("accession"),
                form=source.get("form"),
                byte_start=source.get("byte_start"),
                byte_end=source.get("byte_end"),
                span_sha256=source.get("span_sha256"),
                url=source.get("url"),
            ),
        ))

    # (c) one verbatim line per condition — premise + lead_in + the condition
    # text, printed ONLY when re-derived from the pinned bytes.
    for condition in edge.get("conditions") or []:
        kind = condition.get("kind")
        _count(conditions_by_kind, kind)
        if not condition_verified(condition, excerpts):
            _count(unverified, kind)
            continue
        premise = premises["premises"].get(kind) or premises["premises"]["other"]
        slots = {"counterparty": to_name}
        text = condition.get("text") or ""
        lines.append(line(
            "verbatim_excerpt",
            f"{premise['en'].format(**slots)}, {lead_in_en} {text}",
            f"{premise['zh'].format(**slots)}，{lead_in_zh}{text}",
            _citation(
                accession=condition.get("accession"),
                form=None,
                byte_start=condition.get("byte_start"),
                byte_end=condition.get("byte_end"),
                span_sha256=condition.get("span_sha256"),
            ),
        ))

    # (d) correction lines from the edge's magnitude-revision chains, grouped
    # by (kind, period label, asserting party) and ordered by revision_seq.
    chains: dict = {}
    for revision in edge.get("magnitude_history") or []:
        key = (
            revision["kind"],
            (revision.get("period") or {}).get("label"),
            revision.get("asserting_party"),
        )
        chains.setdefault(key, []).append(revision)
    by_revision_id = {
        revision["revision_id"]: revision
        for revision in edge.get("magnitude_history") or []
    }

    def _chain_order(key):
        first = chains[key][0]
        period = first.get("period") or {}
        return (
            key[0],
            period.get("start") or "",
            period.get("end") or "",
            key[1] or "",
            key[2] or "",
        )

    for key in sorted(chains, key=_chain_order):
        group = sorted(chains[key], key=lambda r: r["revision_seq"])
        first = group[0]
        period = (first.get("period") or {}).get("label")
        party = party_name(first.get("asserting_party"), from_side, sec_names)
        source = first.get("source_ref") or {}
        known_date = (first.get("known_at") or "")[:10]
        template = premises["corrections"]["first_published"]
        slots = {
            "party": party,
            "value": _fmt_revision(first),
            "period": period,
            "form": source.get("form"),
            "accession": source.get("accession"),
            "date": known_date,
        }
        lines.append(line(
            "first_published", template["en"].format(**slots),
            template["zh"].format(**slots),
            _citation(
                accession=source.get("accession"),
                form=source.get("form"),
                byte_start=source.get("byte_start"),
                byte_end=source.get("byte_end"),
                span_sha256=source.get("span_sha256"),
            ),
        ))
        for revision in group[1:]:
            source = revision.get("source_ref") or {}
            known_date = (revision.get("known_at") or "")[:10]
            citation = _citation(
                accession=source.get("accession"),
                form=source.get("form"),
                byte_start=source.get("byte_start"),
                byte_end=source.get("byte_end"),
                span_sha256=source.get("span_sha256"),
            )
            base = {
                "form": source.get("form"),
                "accession": source.get("accession"),
                "date": known_date,
                "value": _fmt_revision(revision),
            }
            if revision.get("revision_kind") == "restatement":
                superseded = by_revision_id.get(revision.get("supersedes")) or {}
                template = premises["corrections"]["restatement"]
                slots = dict(base, old_value=_fmt_revision(superseded))
                restatements += 1
                klass = "restatement"
            else:
                template = premises["corrections"]["reassertion"]
                slots = dict(base)
                reassertions += 1
                klass = "reassertion"
            lines.append(line(
                klass, template["en"].format(**slots),
                template["zh"].format(**slots), citation,
            ))

    for row in edge.get("correction_lineage") or []:
        if row.get("assessment") != "not_restated":
            continue
        template = premises["corrections"]["amendment_not_restated"]
        slots = {
            "accession": row.get("accession"),
            "amends_accession": row.get("amends_accession"),
            "reason": row.get("reason"),
        }
        lines.append(line(
            "amendment_not_restated", template["en"].format(**slots),
            template["zh"].format(**slots),
            _citation(accession=row.get("accession")),
        ))

    # (e) footer + the rights line, always.
    footer = premises["footer"]
    lines.append(line("footer", footer["en"], footer["zh"], None))
    state = (edge.get("rights") or {}).get("public_display")
    lines.append(line(
        "rights",
        RIGHTS_LINE_EN.format(state=state),
        RIGHTS_LINE_ZH.format(state=state),
        None,
    ))

    return {
        "relationship_key": edge["relationship_key"],
        "species": edge["species"],
        "from": {"issuer_id": direction.get("from_issuer_id"), "name": from_name},
        "to": {"issuer_id": direction.get("to_issuer_id"), "name": to_name},
        "from_role": direction.get("from_role"),
        "to_role": direction.get("to_role"),
        "magnitude_state": edge.get("magnitude_state"),
        "freshness_state": edge.get("freshness_state"),
        "asserted_period": edge.get("asserted_period"),
        "rights": edge.get("rights"),
        "lines": lines,
        "_quote_unverified": unverified,
        "_conditions_by_kind": conditions_by_kind,
        "_restatements": restatements,
        "_reassertions": reassertions,
    }


# --- report assembly ---------------------------------------------------------------


def report_text(entries: list) -> str:
    """The plain-text report: EN then ZH for every line, EN entry first."""
    blocks = []
    for entry in entries:
        asserted = entry.get("asserted_period") or {}
        out = [
            f"## relationship {entry['relationship_key']}",
            (
                f"species: {entry['species']}; "
                f"{entry['from']['name']} ({entry['from_role']}) -> "
                f"{entry['to']['name']} ({entry['to_role']})"
            ),
            (
                f"magnitude_state: {entry['magnitude_state']}; "
                f"freshness_state: {entry['freshness_state']}; "
                f"asserted_period: {asserted.get('start')}..{asserted.get('end')}"
            ),
            f"rights: {(entry.get('rights') or {}).get('public_display')}",
        ]
        for line in entry["lines"]:
            out.append(f"[{line['display_class']}] {line['en']}")
            out.append(f"[{line['display_class']}/zh] {line['zh']}")
            citation = line["citation"]
            if citation:
                out.append(
                    f"    citation: {citation.get('accession')} "
                    f"{citation.get('form')} bytes "
                    f"{citation.get('byte_start')}..{citation.get('byte_end')} "
                    f"{citation.get('span_sha256')}".rstrip()
                )
        blocks.append("\n".join(out))
    return "\n\n".join(blocks) + "\n"


def canonical_json_bytes(document) -> bytes:
    """The repo's canonical JSON form: sorted keys, indent 1, LF, UTF-8."""
    text = json.dumps(document, sort_keys=True, indent=1, ensure_ascii=False)
    return (text + "\n").encode("utf-8")
