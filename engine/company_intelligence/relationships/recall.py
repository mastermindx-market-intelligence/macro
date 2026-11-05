"""M2 recall measurement primitives: lexicon, scan, compare, intervals.

The recall side of ORCH-REL M2 §8.2: an INDEPENDENT reader's surface over the
same filings.  This module deliberately shares nothing with the harvester's
candidate machinery — no cue patterns, no alias hints, no per-document caps,
no candidate selection — because recall is only meaningful when the reference
set comes from a broader, independent lexicon.  The scan walks the FULL text
of every fetched document (byte-exact segmentation) and emits every sentence
containing a lexicon term as an annotation item; the compare step matches
annotated named relationships against committed extraction rows.

Pure module: no network import, no wall clock, no store.  The CLI lives in
``scripts/relationship_m2_recall.py``.  Nothing here scores, ranks, predicts
or sizes relationships.
"""
from __future__ import annotations

import hashlib
import html
import json
import re

from engine.company_intelligence.relationships.harvest import (
    norm_text,
    segment,
)
from engine.company_intelligence.relationships.package_v2 import (
    SPECIES_ROLES,
    normalize_span,
)
from engine.company_intelligence.relationships.precision import (
    WILSON_Z,
    wilson,
)
from engine.company_intelligence.relationships.resolve import (
    resolve_counterparty,
)

#: The judge's role enum, derived from SPECIES_ROLES (the nine roles are the
#: from/to role pairs of the five species) so recall.py needs no judge import.
ROLES = tuple(
    sorted({role for pair in SPECIES_ROLES.values() for role in pair[:2]})
)

# --- frozen pins ---------------------------------------------------------------

CORPUS_SCHEMA = "orch_rel.m2_recall_corpus_selection/v1"
CORPUS_SHA256 = (
    "96e860d45c83d7d467e0a55abff6335ee8c05973b094038e9e504ea42aa2daed"
)
LEXICON_SHA256 = "bb0add40bc10d88a6891eef2c4b7a339c321ec19bad2a536461f6e9d5157cc70"

ANNOTATION_SCHEMA_NAME = "gmi_rel_m2.recall_annotation/v1"
PACK_SCHEMA_NAME = "gmi_rel_m2.recall_pack/v1"
REPORT_SCHEMA_NAME = "gmi_rel_m2.recall_report/v1"

#: The report says this in its own words: the measurement's blind spot.
CAVEAT = (
    "Misses outside both the harvester cue patterns and the recall lexicon "
    "are not measured."
)

#: Hard safety ceiling on emitted sentences per document (memory bound only).
#: Lexicon-hit sentences beyond it are COUNTED as RECALL_SCAN_OVERFLOW,
#: never silently dropped.
SCAN_SENTENCE_CEILING = 3000

PACK_MAX_ITEMS = 40


class CorpusDrift(Exception):
    """The corpus file does not hash to the frozen pin (rc 2 CORPUS_DRIFT)."""


class OutRefused(Exception):
    """An output path lands under data/ or site/ (rc 2 OUT_REFUSED)."""


# --- R1: the independent lexicon -------------------------------------------------
#: Lowercase terms, matched case-insensitively; word-boundary anchored where
#: the term starts/ends with a word character.  PREFIX_TERMS match as prefixes
#: (royalt -> royalty/royalties, licens -> license/licensed/licensing, ...).
#: The tuple is frozen by tests/test_relationship_m2_recall.py via
#: :func:`lexicon_sha256`; changing it invalidates every recall number.
LEXICON = (
    "customer", "customers", "supplier", "suppliers", "vendor", "vendors",
    "partner", "agreement with", "purchased from", "purchases from",
    "sells to", "sales to", "sold to", "depend", "depends", "dependent",
    "rely", "relies", "reliance", "royalt", "offtake", "off-take",
    "smelter", "refiner", "refinery", "toll", "tolling",
    "processing agreement", "joint venture", "collaborat", "licens",
    "distribut", "foundry", "foundries", "contract manufactur",
    "percent of", "% of",
)

PREFIX_TERMS = frozenset(
    {"royalt", "collaborat", "licens", "distribut", "contract manufactur"}
)


def lexicon_sha256() -> str:
    """The frozen pin over the newline-joined lexicon serialization."""
    serialization = "\n".join(LEXICON) + "\n"
    return hashlib.sha256(serialization.encode("utf-8")).hexdigest()


def _term_pattern(term: str) -> re.Pattern:
    tokens = term.split(" ")
    body = r"\s+".join(re.escape(token) for token in tokens)
    left = r"\b" if term[0].isalnum() else ""
    right = "" if term in PREFIX_TERMS else (r"\b" if term[-1].isalnum() else "")
    return re.compile(left + body + right, re.IGNORECASE)


_TERM_RES = tuple((term, _term_pattern(term)) for term in LEXICON)


def term_hits(text: str) -> list:
    """Sorted lexicon terms hit by one text (case-insensitive)."""
    return sorted({term for term, pattern in _TERM_RES if pattern.search(text)})


# --- R2: the full-text sentence scan ----------------------------------------------


def sentence_id(doc_id: str, byte_start: int, byte_end: int) -> str:
    digest = hashlib.sha256(
        f"{doc_id}:{byte_start}:{byte_end}".encode("utf-8")
    ).hexdigest()
    return "rs:" + digest[:20]


def _lenient_normalize(raw_slice: bytes) -> str:
    """normalize_span that never raises: replacement chars on invalid utf-8."""
    stripped = re.sub(rb"<[^>]+>", b"", raw_slice)
    try:
        text = stripped.decode("utf-8")
    except UnicodeDecodeError:
        text = stripped.decode("utf-8", "replace")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def scan_with_overflow(raw: bytes, *, doc_id: str,
                       max_sentences: int = SCAN_SENTENCE_CEILING):
    """(items, overflow) for one document's FULL text.

    Emits every segmented sentence containing >=1 lexicon term, up to
    ``max_sentences`` per document; lexicon-hit sentences beyond the ceiling
    are counted (RECALL_SCAN_OVERFLOW), never silently dropped.  No alias
    hints, no issuer names, no cue weighting, no per-document candidate cap.
    """
    seg = segment(raw)
    items: list = []
    overflow = 0
    for sent in seg.sentences:
        terms = term_hits(sent.text)
        if not terms:
            continue
        if len(items) >= max_sentences:
            overflow += 1
            continue
        raw_slice = raw[sent.bs:sent.be]
        items.append(
            {
                "sentence_id": sentence_id(doc_id, sent.bs, sent.be),
                "doc_id": doc_id,
                "byte_start": sent.bs,
                "byte_end": sent.be,
                "raw_sha256": hashlib.sha256(raw_slice).hexdigest(),
                "text": _lenient_normalize(raw_slice),
                "terms": terms,
            }
        )
    return items, overflow


def scan(raw: bytes, *, doc_id: str) -> list:
    """The spec signature: every lexicon sentence of one document."""
    items, _overflow = scan_with_overflow(raw, doc_id=doc_id)
    return items


# --- R5: annotation schema ---------------------------------------------------------

_ANNOTATION_RELATIONSHIP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["counterparty_quote", "species", "subject_role"],
    "properties": {
        "counterparty_quote": {"type": "string", "minLength": 1},
        "species": {"enum": sorted(SPECIES_ROLES)},
        "subject_role": {"enum": sorted(ROLES) + [None]},
    },
}

ANNOTATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema", "sentence_id", "annotator", "named_relationship",
        "unclear", "relationships",
    ],
    "properties": {
        "schema": {"const": ANNOTATION_SCHEMA_NAME},
        "sentence_id": {"type": "string", "pattern": "^rs:[0-9a-f]{20}$"},
        "annotator": {
            "type": "object",
            "additionalProperties": False,
            "required": ["agent", "lane_run_id"],
            "properties": {
                "agent": {"type": "string", "minLength": 1},
                "lane_run_id": {"type": ["string", "null"]},
            },
        },
        "named_relationship": {"type": "boolean"},
        "unclear": {"type": "boolean"},
        "relationships": {
            "type": "array",
            "items": _ANNOTATION_RELATIONSHIP,
        },
    },
}


def validate_annotation(record) -> list:
    """[] when the record is a valid annotation, else problem messages."""
    import jsonschema

    problems: list = []
    try:
        jsonschema.validate(record, ANNOTATION_SCHEMA)
    except jsonschema.ValidationError as error:
        return [f"schema: {error.json_path}: {error.message}"]
    named = record["named_relationship"]
    unclear = record["unclear"]
    relationships = record["relationships"]
    if named and not relationships:
        problems.append(
            "NAMED_REQUIRES_RELATIONSHIPS: named_relationship true requires "
            "at least one relationship"
        )
    if unclear and (named or relationships):
        problems.append(
            "UNCLEAR_REQUIRES_NO_RELATIONSHIPS: unclear true requires "
            "named_relationship false and relationships []"
        )
    if relationships and not named:
        problems.append(
            "RELATIONSHIPS_REQUIRE_NAMED: relationships require "
            "named_relationship true"
        )
    return problems


# --- R6: counterparty resolution and set compare ------------------------------------


def resolve_quote(quote, *, subject_issuer_id, aliases, resolver_rows,
                  manifest_issuers):
    """(issuer_id|None, key, display, refusal) for one counterparty quote.

    The same resolver the judge uses (K4, kind="named"): resolved issuer_id
    when the quote names a manifest issuer, else a ``name:<norm_text>``
    counterparty key.
    """
    display = " ".join(str(quote).split())
    try:
        normalized = normalize_span(str(quote).encode("utf-8"))
    except UnicodeDecodeError:
        normalized = norm_text(str(quote))
    resolution = resolve_counterparty(
        normalized,
        kind="named",
        subject_issuer_id=subject_issuer_id,
        aliases=aliases,
        resolver_rows=resolver_rows,
        manifest_issuers=manifest_issuers,
    )
    issuer_id = resolution["issuer_id"]
    if issuer_id:
        key = issuer_id
    else:
        key = "name:" + norm_text(normalized)
    return issuer_id, key, display, resolution["refusal"]


def pipeline_triples(rows, corpus_issuers):
    """(triples, counters) from committed observation rows.

    triples are distinct (subject.issuer_id, species, key) with key the
    object's issuer_id when present else ``name:<norm_text(name_as_filed)>``;
    rows outside the corpus issuers and non-observation rows are counted and
    skipped, never silently dropped.
    """
    triples: set = set()
    counters = {
        "PIPELINE_ROW_OUTSIDE_CORPUS": 0,
        "PIPELINE_ROW_SKIPPED": 0,
    }
    for row in rows:
        if row.get("row_kind") != "observation":
            counters["PIPELINE_ROW_SKIPPED"] += 1
            continue
        subject = row.get("subject") or {}
        issuer_id = subject.get("issuer_id")
        if issuer_id not in corpus_issuers:
            counters["PIPELINE_ROW_OUTSIDE_CORPUS"] += 1
            continue
        species = row.get("species")
        obj = row.get("object") or {}
        object_issuer = obj.get("issuer_id")
        if object_issuer:
            key = object_issuer
        else:
            key = "name:" + norm_text(obj.get("name_as_filed") or "")
        triples.add((issuer_id, species, key))
    return triples, counters


def compute_recall_report(*, ref_items, pipe_set, issuer_domain,
                          sentences_total, annotated_count, counters,
                          corpus_sha256, lexicon_sha256, extraction_sha256):
    """The deterministic recall report over distinct triples (see R6)."""
    ordered = sorted(
        ref_items,
        key=lambda item: (
            item["issuer_id"], item["species"], item["key"],
            item["sentence_id"], item["counterparty"],
        ),
    )
    distinct: list = []
    seen: set = set()
    for item in ordered:
        triple = (item["issuer_id"], item["species"], item["key"])
        if triple in seen:
            continue
        seen.add(triple)
        distinct.append(item)
    ref_set = seen
    hits_set = ref_set & set(pipe_set)
    miss_set = ref_set - hits_set
    hit_count = len(hits_set)
    ref_count = len(ref_set)

    per_issuer: dict = {}
    by_species: dict = {}
    by_domain: dict = {}
    for item in distinct:
        issuer = item["issuer_id"]
        species = item["species"]
        domain = issuer_domain.get(issuer, "UNKNOWN")
        matched = (
            item["issuer_id"],
            item["species"],
            item["key"],
        ) in hits_set
        per_issuer.setdefault(issuer, {"domain": domain, "ref": 0, "hit": 0})
        per_issuer[issuer]["ref"] += 1
        per_issuer[issuer]["hit"] += 1 if matched else 0
        by_species.setdefault(species, {"ref": 0, "hit": 0})
        by_species[species]["ref"] += 1
        by_species[species]["hit"] += 1 if matched else 0
        by_domain.setdefault(domain, {"ref": 0, "hit": 0})
        by_domain[domain]["ref"] += 1
        by_domain[domain]["hit"] += 1 if matched else 0

    def _bucket(entry: dict) -> dict:
        recall_value = (
            round(entry["hit"] / entry["ref"], 4) if entry["ref"] else None
        )
        return {
            **entry,
            "recall": recall_value,
            "wilson_95": wilson(entry["hit"], entry["ref"]),
        }

    per_issuer_rows = []
    for issuer in sorted(per_issuer):
        entry = per_issuer[issuer]
        per_issuer_rows.append(
            {
                "issuer_id": issuer,
                "domain": entry["domain"],
                "ref": entry["ref"],
                "hit": entry["hit"],
                "miss": entry["ref"] - entry["hit"],
            }
        )

    jackknife_issuers = sorted(per_issuer)
    jackknife = None
    jackknife_se = None
    if ref_count and len(jackknife_issuers) >= 2:
        loo_recalls = []
        for dropped in jackknife_issuers:
            sub_ref = ref_set - {
                (i, s, k)
                for (i, s, k) in ref_set
                if i == dropped
            }
            if not sub_ref:
                loo_recalls = None
                break
            loo_recalls.append(len(sub_ref & set(pipe_set)) / len(sub_ref))
        if loo_recalls is not None:
            count = len(loo_recalls)
            mean = sum(loo_recalls) / count
            variance = sum((value - mean) ** 2 for value in loo_recalls)
            se = ((count - 1) / count * variance) ** 0.5
            point = hit_count / ref_count
            low = max(0.0, point - WILSON_Z * se)
            high = min(1.0, point + WILSON_Z * se)
            jackknife = [round(low, 4), round(high, 4)]
            jackknife_se = round(se, 4)

    misses = sorted(
        (
            {
                "issuer_id": item["issuer_id"],
                "domain": issuer_domain.get(item["issuer_id"], "UNKNOWN"),
                "species": item["species"],
                "counterparty": item["counterparty"],
                "key": item["key"],
                "sentence_id": item["sentence_id"],
            }
            for item in distinct
            if (item["issuer_id"], item["species"], item["key"]) in miss_set
        ),
        key=lambda miss: (
            miss["issuer_id"], miss["species"], miss["key"], miss["sentence_id"]
        ),
    )

    return {
        "schema": REPORT_SCHEMA_NAME,
        "caveat": CAVEAT,
        "corpus_sha256": corpus_sha256,
        "lexicon_sha256": lexicon_sha256,
        "extraction_sha256": dict(sorted(extraction_sha256.items())),
        "counters": dict(sorted(counters.items())),
        "sentences": {
            "total": sentences_total,
            "annotated": annotated_count,
            "coverage": (
                round(annotated_count / sentences_total, 4)
                if sentences_total
                else None
            ),
        },
        "reference_set_size": ref_count,
        "pipeline_set_size": len(pipe_set),
        "hits": hit_count,
        "misses_count": ref_count - hit_count,
        "recall": {
            "value": round(hit_count / ref_count, 4) if ref_count else None,
            "wilson_95": wilson(hit_count, ref_count),
            "jackknife_95": jackknife,
            "jackknife_se": jackknife_se,
            "jackknife_issuers": len(jackknife_issuers),
        },
        "by_species": {
            species: _bucket(by_species[species]) for species in sorted(by_species)
        },
        "by_domain": {
            domain: _bucket(by_domain[domain]) for domain in sorted(by_domain)
        },
        "per_issuer": per_issuer_rows,
        "misses": misses,
    }


def load_corpus(path, expected_sha256: str = CORPUS_SHA256) -> dict:
    """The frozen corpus document, sha256-verified (CorpusDrift on drift)."""
    with open(path, "rb") as handle:
        raw = handle.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise CorpusDrift(
            f"corpus {path} hashes to {digest}, pin expects {expected_sha256}"
        )
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema") != CORPUS_SCHEMA:
        raise CorpusDrift(f"corpus schema {doc.get('schema')!r} is not {CORPUS_SCHEMA}")
    return doc
