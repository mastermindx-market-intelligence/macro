"""Pure projection of the existing Market Reference registry for guide/help consumers.

The caller supplies the canonical registry and coverage validators. This module
never loads live market data, publishes files, or replaces the source validators.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any

SCHEMA = "mastermind.market_guide/v1"
LANGUAGES = ("en", "zh")
SOURCE_FIELDS = ("interpretation_up", "interpretation_down", "interpretation_neutral")
KINDS = {"composite", "risk", "quadrant", "confirmation", "evidence", "rotation", "explanation"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
OWNER = re.compile(r"[a-z0-9_][a-z0-9_-]*\.html(?:#[A-Za-z0-9_-]+)?\Z")


class GuideError(ValueError):
    """Invalid presentation or an unsafe projection; no artifact may be published."""


def normalize(value: str) -> str:
    """Match the browser's NFKC/lowercase policy; punctuation is not a word."""
    text = unicodedata.normalize("NFKC", value).lower()
    return "".join(c for c in text if not c.isspace() and unicodedata.category(c)[0] not in "PZ")


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GuideError(f"{where}: expected nonempty text")
    return value


def _pair(data: Mapping[str, Any], field: str, *, plain_en: bool = False, optional: bool = False) -> dict[str, str] | None:
    en = data.get(field if plain_en else field + "_en")
    zh = data.get(field + "_zh")
    absent = lambda value: value is None or isinstance(value, str) and not value.strip()
    if optional and absent(en) and absent(zh):
        return None
    return {"en": _text(en, field + "_en"), "zh": _text(zh, field + "_zh")}


def _string_list(value: Any, where: str, *, optional: bool = False) -> list[str]:
    if value is None and optional:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise GuideError(f"{where}: expected a list of nonempty strings")
    return list(value)


def _readings(entry: dict, spec: dict) -> list[dict]:
    rows = []
    declared = spec.get("readings")
    if declared is None:
        # Generic entries retain source wording without inventing numeric scales
        # or implying that a higher reading is favorable.
        declared = [{"field": field} for field in SOURCE_FIELDS]
    if not isinstance(declared, list):
        raise GuideError(f"{entry['id']}: readings must be a list")
    seen = set()
    for row in declared:
        if not isinstance(row, dict) or set(row) - {"field", "label_en", "label_zh"}:
            raise GuideError(f"{entry['id']}: invalid reading descriptor")
        field = row.get("field")
        if field not in SOURCE_FIELDS or field in seen:
            raise GuideError(f"{entry['id']}: unknown or repeated reading field")
        seen.add(field)
        value = _pair(entry, field, plain_en=True, optional=True)
        if value is None:
            if spec.get("readings") is not None:
                raise GuideError(f"{entry['id']}: declared reading has no source content")
            continue
        label = _pair(row, "label", optional=True)
        rows.append({"id": field, "label": label, "text": value})
    available = {field for field in SOURCE_FIELDS if _pair(entry, field, plain_en=True, optional=True)}
    if {row["id"] for row in rows} != available:
        raise GuideError(f"{entry['id']}: presentation must not drop a source interpretation")
    return rows


def compile_guide(raw: dict, presentation: dict, *, validate_registry: Callable, validate_coverage: Callable) -> dict:
    """Validate through existing owners, then produce a deterministic public view.

    ``validate_registry`` is normally a closure calling
    ``scripts.build_market_reference.validate(raw, repo_root=...)``; coverage
    uses that module's ``validate_coverage_exceptions``. No permissive default
    validator or network/publication side effect is provided here.
    """
    if not isinstance(raw, dict) or raw.get("schema") != "mastermind.market_reference/v1":
        raise GuideError("wrong reference source schema")
    if not isinstance(presentation, dict) or presentation.get("schema") != "mastermind.market_guide_presentation/v1":
        raise GuideError("wrong presentation schema")
    if set(presentation) - {"schema", "entries", "questions"}:
        raise GuideError("unknown presentation field")
    # Give the validation owner a copy; accidental validator mutation must not
    # alter source content or produce a digest for bytes we did not consume.
    source = copy.deepcopy(raw)
    entries = validate_registry(source)
    coverage = validate_coverage(source, entries)
    if not isinstance(entries, list) or not entries:
        raise GuideError("validator returned no entries")
    if not isinstance(coverage, list):
        raise GuideError("coverage validator returned a non-list")
    if source != raw or entries != raw.get("entries") or coverage != (raw.get("coverage_exceptions") if raw.get("coverage_exceptions") is not None else []):
        raise GuideError("validation must not rewrite, drop, or reorder source content")
    specs = presentation.get("entries", {})
    if not isinstance(specs, dict):
        raise GuideError("presentation entries must be a mapping")
    ids = [e.get("id") if isinstance(e, dict) else None for e in entries]
    if any(not isinstance(eid, str) or not SLUG.fullmatch(eid) for eid in ids) or len(set(ids)) != len(ids):
        raise GuideError("invalid or duplicate entry IDs")
    if set(specs) - set(ids):
        raise GuideError("presentation references a missing entry")
    by_id = {e["id"]: e for e in entries}
    output = []
    lookup: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        eid = entry["id"]
        if entry.get("authority_ceiling") != "reference_only":
            raise GuideError(f"{eid}: reference-only authority required")
        if entry.get("status") not in {"active", "deprecated"}:
            raise GuideError(f"{eid}: unsupported lifecycle status")
        owner = _text(entry.get("owner_ref"), f"{eid}.owner_ref")
        if not OWNER.fullmatch(owner):
            raise GuideError(f"{eid}: unsafe owner target")
        spec = specs.get(eid, {})
        if not isinstance(spec, dict) or set(spec) - {"kind", "readings"}:
            raise GuideError(f"{eid}: unsupported presentation properties")
        kind = spec.get("kind", "explanation")
        if not isinstance(kind, str) or kind not in KINDS:
            raise GuideError(f"{eid}: unsupported presentation kind")
        labels = _pair(entry, "label")
        aliases = {lang: _string_list(entry.get("aliases_" + lang, []), f"{eid}.aliases_{lang}", optional=True) for lang in LANGUAGES}
        caveats = {lang: _string_list(entry.get("caveats_" + lang, []), f"{eid}.caveats_{lang}", optional=True) for lang in LANGUAGES}
        if len(caveats["en"]) != len(caveats["zh"]):
            raise GuideError(f"{eid}: caveat translation count differs")
        if entry.get("kind") == "indicator" and not caveats["en"]:
            raise GuideError(f"{eid}: an indicator needs a visible limitation")
        sources = _string_list(entry.get("public_source_refs", []), f"{eid}.sources", optional=True)
        if any(not url.startswith("https://") or any(c.isspace() for c in url) for url in sources):
            raise GuideError(f"{eid}: unsafe public source target")
        related = _string_list(entry.get("related_ids", []), f"{eid}.related_ids", optional=True)
        if set(related) - set(ids):
            raise GuideError(f"{eid}: unresolved related entry")
        row = {"id": eid, "kind": entry.get("kind"), "family": entry.get("family"),
               "status": entry["status"], "authority_ceiling": "reference_only",
               "label": labels, "aliases": aliases,
               "definition": _pair(entry, "short_definition"),
               "why": _pair(entry, "why_it_matters"),
               "basis": _pair(entry, "unit_or_basis", plain_en=True, optional=True),
               "caveats": caveats,
               "visible_caveat": {lang: caveats[lang][0] for lang in LANGUAGES} if caveats["en"] else None,
               "owner_ref": owner, "public_source_refs": sources, "related_ids": related,
               "presentation": {"kind": kind, "readings": _readings(entry, spec)}}
        current, visited, chain = entry, {eid}, []
        while current.get("status") == "deprecated":
            successor = current.get("superseded_by")
            if successor not in by_id or successor in visited:
                raise GuideError(f"{eid}: broken or cyclic replacement chain")
            visited.add(successor); chain.append(successor); current = by_id[successor]
        row["replacement_chain"] = chain
        output.append(row)
        for value in [eid, *labels.values(), *aliases["en"], *aliases["zh"]]:
            lookup[normalize(value)].add(eid)
        row["search_key"] = normalize(" ".join([eid, *labels.values(), *aliases["en"], *aliases["zh"]]))
    coverage_items = []
    coverage_names = set()
    for item in coverage:
        if not isinstance(item, dict) or item.get("state") not in {"covered_by", "not_an_indicator", "not_covered"}:
            raise GuideError("unknown coverage state")
        label = _pair(item, "element")
        key = "coverage-" + re.sub(r"[^a-z0-9]+", "-", label["en"].lower()).strip("-")
        if not SLUG.fullmatch(key) or key in set(ids) or key in coverage_names:
            raise GuideError("duplicate or invalid coverage link")
        coverage_names.add(key)
        related = _string_list(item.get("see_ids", []), key + ".see_ids", optional=True)
        if set(related) - set(ids) or len(set(related)) != len(related):
            raise GuideError(f"{key}: invalid coverage targets")
        reason = _pair(item, "reason", optional=True)
        if item["state"] == "covered_by" and not related:
            raise GuideError(f"{key}: covered entry has no target")
        if item["state"] != "covered_by" and reason is None:
            raise GuideError(f"{key}: missing coverage reason")
        target = related[0] if item["state"] == "covered_by" and len(related) == 1 else key
        if not isinstance(item.get("surface"), str) or not OWNER.fullmatch(item["surface"]) or "#" in item["surface"]:
            raise GuideError(f"{key}: unsafe coverage surface")
        coverage_items.append({"id": key, "state": item["state"], "label": label,
                               "reason": reason, "related_ids": related, "surface": item["surface"],
                               "target": target, "search_key": normalize(" ".join(label.values()))})
        for alias in [key, key.removeprefix("coverage-"), *label.values()]:
            lookup[normalize(alias)].add(target)
    questions, question_ids = [], set()
    raw_questions = presentation.get("questions", [])
    if not isinstance(raw_questions, list):
        raise GuideError("questions must be a list")
    for q in raw_questions:
        if not isinstance(q, dict) or set(q) - {"id", "label_en", "label_zh", "entry_ids"}:
            raise GuideError("unknown question field")
        qid = q.get("id")
        if not isinstance(qid, str) or not SLUG.fullmatch(qid) or qid in question_ids:
            raise GuideError("invalid or duplicate question ID")
        members = _string_list(q.get("entry_ids"), qid + ".entry_ids")
        if not members or set(members) - set(ids) or len(members) != len(set(members)):
            raise GuideError(f"{qid}: invalid question membership")
        question_ids.add(qid)
        questions.append({"id": qid, "label": _pair(q, "label"), "entry_ids": members})
    payload = {"schema": SCHEMA, "authority_ceiling": "reference_only", "live_values": False,
               "entries": output, "coverage": coverage_items, "questions": questions,
               "lookup": {key: sorted(targets) for key, targets in sorted(lookup.items())}}
    # Content version, not a market timestamp, freshness assertion, or evidence receipt.
    payload["content_revision"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                                           separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return payload


def script_json(manifest: dict) -> str:
    """JSON safe inside a script-data element, including hostile editorial text."""
    return json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
