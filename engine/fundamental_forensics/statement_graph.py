"""FIF-3A1/3A2 filing-native statement graph.

Walks presentation/calculation/label linkbases and joins them to the strict
offline iXBRL parse. Displayed row/column composition for the bounded AAPL
golden filing set comes from the captured primary HTML tables, not from raw
hypercube order. Deterministic. No network. No implicit now. No LLM.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from collectors.sec_filing_parser import parse_sec_filing_document

from .disclosure_diff import _attribute_map, _span_attribute, _span_overflow

LINK = "http://www.xbrl.org/2003/linkbase"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"

LABEL_STANDARD = "http://www.xbrl.org/2003/role/label"
LABEL_TERSE = "http://www.xbrl.org/2003/role/terseLabel"
LABEL_PERIOD_START = "http://www.xbrl.org/2003/role/periodStartLabel"
LABEL_PERIOD_END = "http://www.xbrl.org/2003/role/periodEndLabel"
LABEL_NEGATED_PERIOD_START = "http://www.xbrl.org/2009/role/negatedPeriodStartLabel"
_PERIOD_START_ROLES = frozenset({LABEL_PERIOD_START, LABEL_NEGATED_PERIOD_START})

PRIMARY_STATEMENT_ROLES: dict[str, str] = {
    "income_statement": "http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFOPERATIONS",
    "balance_sheet": "http://www.apple.com/role/CONSOLIDATEDBALANCESHEETS",
    "cash_flow": "http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFCASHFLOWS",
}

STATEMENT_TITLES: dict[str, str] = {
    "income_statement": "CONSOLIDATED STATEMENTS OF OPERATIONS",
    "balance_sheet": "CONSOLIDATED BALANCE SHEETS",
    "cash_flow": "CONSOLIDATED STATEMENTS OF CASH FLOWS",
}

_ABSTRACT_TOKENS = (
    "Abstract",
    "Axis",
    "Domain",
    "Member",
    "Table",
    "LineItems",
)
_PERIOD_BANNER_LABELS = frozenset(
    {
        "years ended",
        "three months ended",
        "six months ended",
        "nine months ended",
        "twelve months ended",
    }
)

_PREFIXES = (
    "us-gaap_",
    "srt_",
    "dei_",
    "ecd_",
    "country_",
    "iso4217_",
)

_MAX_LINKBASE_BYTES = 8 * 1024 * 1024
_MAX_ARCS = 20_000
_FORBIDDEN_DECL = b"<!DOCTYPE", b"<!ENTITY"
GOLDEN_AAPL_FIXTURES: dict[str, str] = {
    "0000320193-25-000079": "tests/fixtures/fundamental_forensics/aapl_10k_2025",
    "0000320193-26-000020": "tests/fixtures/fundamental_forensics/aapl_10q_2026q3",
}
_DEFAULT_GOLDEN_ACCESSION = "0000320193-25-000079"
_RELATED_EVENT_REF_KEYS = frozenset(
    {"plane", "event_id", "relation", "source_filing_distinction"}
)
# Full month names first, then the longest abbreviation first, so alternation
# cannot take a shorter token out of a longer one ("Sept." before "Sep.").
_MONTH_TOKEN = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
# Word boundaries keep month tokens from matching inside words ("Decor. 31, 2025"
# is not December). The optional period covers EDGAR viewer dates ("Dec. 31, 2025").
# A month token may also start at a lowercase-to-capital seam, where "\b" does
# not fire, so glued banner text like "As ofMarch 31, 2025" still yields a date.
_DATE_RE = re.compile(
    r"(?:\b|(?-i:(?<=[a-z])(?=[A-Z])))(" + _MONTH_TOKEN + r")\.?\s+(\d{1,2}),\s*(\d{4})\b",
    re.I,
)
# A month-day phrase WITHOUT a year ("Fiscal Year Ended January 31,"): the
# negative lookahead rejects the day whenever a 4-digit year follows it, so a
# full date never doubles as a bare month-day phrase.
_MONTH_DAY_RE = re.compile(
    r"(?:\b|(?-i:(?<=[a-z])(?=[A-Z])))(" + _MONTH_TOKEN + r")\.?\s+(\d{1,2})(?!\s*,?\s*\d{4})\b",
    re.I,
)
_YEAR_CELL_RE = re.compile(r"^\d{4}$")
# Month, week and quarter words anywhere in a bare-year header region: a header
# that prints them (including an N-months-ended group banner) names its own
# periods, so the document period end never composes those columns.
_BARE_YEAR_PERIOD_WORD_RE = re.compile(
    r"\b(?:" + _MONTH_TOKEN + r"|months?|weeks?|quarters?)\b", re.IGNORECASE
)
_FULL_MONTH_TOKEN = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
# Some consolidated headers print the numeric day glued to the year ("June 302025")
# with no space or comma. This is a whole-header-cell grammar only: narrative or
# body text never passes it, cells at or below the first fact row are never
# consulted, the day must be valid for that month (February 29 only in a leap
# year) and the year is 1990..2100.
_GLUED_DATE_CELL_RE = re.compile(
    r"^(" + _FULL_MONTH_TOKEN + r") (\d{1,2})(\d{4})$", re.IGNORECASE
)
_GLUED_YEAR_MIN = 1990
_GLUED_YEAR_MAX = 2100
# Banner income/cash-flow column groups ("Three Months Ended June 30") each own
# their own duration; composing one shared end-date row would erase the 3m/6m
# distinction, so a banner row made only of these never takes the same-row or
# the caption/blank-gap year-row composition. A trailing comma ("Three Months
# Ended March 31,") and a glued "EndedJune 30" print the same banner.
_GROUP_BANNER_RE = re.compile(
    r"^(three|six|nine|twelve) months ended(?: |(?-i:(?<=[a-z])(?=[A-Z])))("
    + _FULL_MONTH_TOKEN
    + r") (\d{1,2}),?$",
    re.IGNORECASE,
)
_GROUP_BANNER_MONTHS = {"three": 3, "six": 6, "nine": 9, "twelve": 12}
_STATEMENT_UNIT_BANDS = (
    "(Dollars in millions)",
    "(Dollars in millions except per share data)",
    "(Millions of dollars)",
)
_BARE_MONTH_DAY_RE = re.compile(r"^(" + _FULL_MONTH_TOKEN + r")\.? (\d{1,2})$", re.IGNORECASE)
# A whole-cell unit caption printed in the leading cell of a year row ("(in
# millions)", "In millions, except par value", "(Dollars in millions, except
# per share data)", "(Millions of dollars)"). Consulted only in that leading
# position of a factless year row under one month-day banner; a caption alone
# on its row is never skipped here (only _STATEMENT_UNIT_BANDS may be).
_UNIT_CAPTION_BODY = (
    r"(?:(?:dollars|amounts)\s+in\s+|in\s+)?(?:millions|thousands|billions)"
    r"(?:\s+of\s+dollars)?(?:(?:,\s*|\s+)except\s+[^()]+)?"
)
_UNIT_CAPTION_RE = re.compile(
    r"^(?:\(" + _UNIT_CAPTION_BODY + r"\)|" + _UNIT_CAPTION_BODY + r")$", re.IGNORECASE
)
_R7_DISAGREEMENT = "displayed cell period disagrees with its column"
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sept": 9,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


STATEMENT_REFUSAL_CODES = (
    "displayed_layout_unsupported",
    "displayed_table_absent",
    "displayed_columns_absent",
    "statement_role_not_consolidated",
    "displayed_cell_period_mismatch",
    "displayed_column_period_unbound",
    "statement_role_presentation_absent",
)


class StatementGraphError(ValueError):
    """The filing package cannot yield an as-reported statement tree."""

    def __init__(self, message: str, *, refusal_code: str | None = None) -> None:
        super().__init__(message)
        self.refusal_code = refusal_code


@dataclass(frozen=True)
class GoldenFilingPackage:
    """Pinned AAPL 10-K members plus the complete archive inventory."""

    manifest: dict[str, Any]
    members: dict[str, bytes]


def mint_fixture_recorded_at(now: datetime) -> str:
    """Capture-process clock, injected by the capture script. Request time must never mint this."""
    stamp = now
    if stamp.tzinfo is None:
        raise StatementGraphError("fixture_recorded_at requires an aware UTC clock")
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json_object(path: Path, *, name: str) -> dict[str, Any]:
    raw = path.read_bytes()
    if _FORBIDDEN_DECL[0] in raw or b"\x00" in raw:
        raise StatementGraphError(f"{name} is malformed")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StatementGraphError(f"{name} is malformed") from exc
    if not isinstance(parsed, dict):
        raise StatementGraphError(f"{name} is malformed")
    return parsed


def _admit_statement_roles(manifest: Mapping[str, Any]) -> None:
    extras = manifest.get("statement_roles")
    if extras is None:
        return
    if not isinstance(extras, dict):
        raise StatementGraphError("golden AAPL statement_roles are malformed")
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        spec = extras.get(kind)
        if not isinstance(spec, dict):
            raise StatementGraphError(f"golden AAPL statement role is missing: {kind}")
        if not isinstance(spec.get("role_uri"), str) or not spec["role_uri"]:
            raise StatementGraphError(f"golden AAPL statement role_uri is missing: {kind}")
        if not isinstance(spec.get("title"), str) or not spec["title"]:
            raise StatementGraphError(f"golden AAPL statement title is missing: {kind}")


def _admit_related_event_ref(manifest: Mapping[str, Any]) -> None:
    raw = manifest.get("related_event_ref")
    if raw is None:
        return
    if not isinstance(raw, dict) or set(raw) != _RELATED_EVENT_REF_KEYS:
        raise StatementGraphError("golden AAPL related_event_ref is not the stable reference")
    if "generation_id" in raw:
        raise StatementGraphError("golden AAPL related_event_ref must not mint generation identity")
    if not all(isinstance(raw.get(key), str) and raw[key] for key in ("plane", "event_id", "relation")):
        raise StatementGraphError("golden AAPL related_event_ref is not the stable reference")
    distinction = raw.get("source_filing_distinction")
    if not isinstance(distinction, dict):
        raise StatementGraphError("golden AAPL related_event_ref is not the stable reference")
    eight_k = distinction.get("earnings_release_8k_accession")
    periodic = distinction.get("periodic_report_accession")
    if not isinstance(eight_k, str) or not isinstance(periodic, str) or not eight_k or not periodic:
        raise StatementGraphError("golden AAPL related_event_ref is not the stable reference")
    if eight_k == periodic:
        raise StatementGraphError("golden AAPL related_event_ref collapses distinct filings")
    if periodic != manifest.get("accession"):
        raise StatementGraphError("golden AAPL related_event_ref is not bound to this filing")


def admit_golden_aapl_package(fixture: Path) -> GoldenFilingPackage:
    """Strictly admit the committed AAPL package. No network. No writes."""
    fixture = Path(fixture)
    manifest = _load_json_object(fixture / "package_manifest.json", name="golden AAPL package manifest")
    index_path = fixture / "index.json"
    if not index_path.is_file():
        raise StatementGraphError("golden AAPL archive index is missing")
    index_bytes = index_path.read_bytes()
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    if index_sha != manifest.get("index_sha256"):
        raise StatementGraphError("golden AAPL archive index digest mismatch")
    if len(index_bytes) != manifest.get("index_byte_length"):
        raise StatementGraphError("golden AAPL archive index length mismatch")
    try:
        index_payload = json.loads(index_bytes.decode("utf-8"))
        items = index_payload["directory"]["item"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise StatementGraphError("golden AAPL archive index is malformed") from exc
    if not isinstance(items, list):
        raise StatementGraphError("golden AAPL archive index is malformed")
    index_names = [str(item.get("name") or "") for item in items]
    if any(not name for name in index_names):
        raise StatementGraphError("golden AAPL archive index has an unnamed member")
    if len(index_names) != len(set(index_names)):
        raise StatementGraphError("golden AAPL archive index has duplicate members")
    members_meta = manifest.get("members")
    if not isinstance(members_meta, list):
        raise StatementGraphError("golden AAPL package inventory is malformed")
    manifest_names = [str(item.get("name") or "") for item in members_meta]
    if any(not name for name in manifest_names):
        raise StatementGraphError("golden AAPL package inventory has an unnamed member")
    if len(manifest_names) != len(set(manifest_names)):
        raise StatementGraphError("golden AAPL package inventory has duplicate members")
    extra = set(manifest_names) - set(index_names)
    missing = set(index_names) - set(manifest_names)
    if extra or missing:
        raise StatementGraphError("golden AAPL package inventory does not match the archive index")
    committed = manifest.get("member_count")
    if not isinstance(committed, int) or committed < 1 or len(index_names) != committed:
        raise StatementGraphError("golden AAPL package inventory count does not match the committed index")
    _admit_statement_roles(manifest)
    _admit_related_event_ref(manifest)

    witness_meta = manifest.get("acceptance_witness")
    if not isinstance(witness_meta, dict) or not isinstance(witness_meta.get("path"), str):
        raise StatementGraphError("golden AAPL acceptance witness is missing")
    witness_path = fixture / str(witness_meta["path"])
    if not witness_path.is_file():
        raise StatementGraphError("golden AAPL acceptance witness is missing")
    witness_bytes = witness_path.read_bytes()
    if hashlib.sha256(witness_bytes).hexdigest() != witness_meta.get("content_sha256"):
        raise StatementGraphError("golden AAPL acceptance witness digest mismatch")
    if len(witness_bytes) != witness_meta.get("byte_length"):
        raise StatementGraphError("golden AAPL acceptance witness length mismatch")
    witness = _load_json_object(witness_path, name="golden AAPL acceptance witness")
    expected_bind = {
        "accession": "accessionNumber",
        "form": "form",
        "primary_document": "primaryDocument",
        "period_of_report": "reportDate",
        "filing_date": "filingDate",
        "source_accepted_at": "acceptanceDateTime",
    }
    for manifest_field, witness_field in expected_bind.items():
        if manifest.get(manifest_field) != witness.get(witness_field):
            raise StatementGraphError(f"golden AAPL {manifest_field} is not bound to the acceptance witness")
    if not isinstance(manifest.get("fixture_recorded_at"), str) or not manifest["fixture_recorded_at"]:
        raise StatementGraphError("golden AAPL fixture_recorded_at is missing")

    members: dict[str, bytes] = {}
    stored_count = 0
    for item in members_meta:
        if not isinstance(item, dict):
            raise StatementGraphError("golden AAPL stored member is malformed")
        name = item.get("name")
        if item.get("state") != "stored":
            continue
        stored_count += 1
        if name not in set(index_names):
            raise StatementGraphError(f"golden AAPL stored member is not in the archive index: {name}")
        rel = item.get("path")
        if not isinstance(name, str) or not isinstance(rel, str):
            raise StatementGraphError("golden AAPL stored member is malformed")
        payload = (fixture / rel).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != item.get("content_sha256") or len(payload) != item.get("byte_length"):
            raise StatementGraphError(f"golden AAPL member digest mismatch: {name}")
        members[name] = payload
    if stored_count != manifest.get("retained_count"):
        raise StatementGraphError("golden AAPL retained count does not match stored members")
    if manifest.get("primary_document") not in members:
        raise StatementGraphError("golden AAPL primary document is not retained")
    return GoldenFilingPackage(manifest=manifest, members=members)


def load_golden_aapl_package(repo_root: Path, accession: str | None = None) -> GoldenFilingPackage:
    """Load and strictly admit one committed AAPL golden fixture. Performs no network I/O."""
    chosen = accession or _DEFAULT_GOLDEN_ACCESSION
    relative = GOLDEN_AAPL_FIXTURES.get(chosen)
    if relative is None:
        raise StatementGraphError("unknown golden AAPL filing")
    return admit_golden_aapl_package(Path(repo_root) / relative)


def _stored_member(package: GoldenFilingPackage, role: str) -> bytes:
    for item in package.manifest.get("members") or []:
        if not isinstance(item, dict):
            continue
        if item.get("state") == "stored" and item.get("role") == role:
            name = item.get("name")
            if not isinstance(name, str) or name not in package.members:
                raise StatementGraphError(f"golden AAPL stored {role} member is missing")
            return package.members[name]
    raise StatementGraphError(f"golden AAPL stored {role} member is missing")


def _statement_identity(
    package: GoldenFilingPackage, statement_type: str
) -> tuple[str, str, str | list[str]]:
    """Declared role URI and titles for one statement kind.

    Manifest shape: ``statement_roles[statement_type] = {"role_uri": str,
    "title": str, "title_search": str | list[str]}``. ``title_search`` names the
    row text that locates the captured table: a ``str`` is matched exactly as
    written (the golden AAPL default path, byte-pinned), a ``list`` is tried in
    declared order case-insensitively over whitespace-normalised text and the
    first candidate present in the filing wins. The apple.com defaults are the
    identity of the admitted golden AAPL packages alone (``accession`` keyed by
    ``GOLDEN_AAPL_FIXTURES``, the same keying ``load_golden_aapl_package``
    admits by); any other package without a declared ``statement_roles`` entry
    carrying both ``role_uri`` and ``title`` is refused rather than silently
    searched against Apple's roles.
    """
    extras = package.manifest.get("statement_roles")
    spec = extras.get(statement_type) if isinstance(extras, dict) else None
    if isinstance(spec, dict) and spec.get("role_uri") and spec.get("title"):
        title = str(spec["title"])
        raw_search = spec.get("title_search")
        if isinstance(raw_search, list):
            search: str | list[str] = [str(item) for item in raw_search if str(item).strip()] or [title]
        else:
            search = str(raw_search or title)
        return str(spec["role_uri"]), title, search
    if str(package.manifest.get("accession") or "") not in GOLDEN_AAPL_FIXTURES:
        raise StatementGraphError(
            f"statement identity is not declared for issuer: {statement_type}"
        )
    return (
        PRIMARY_STATEMENT_ROLES[statement_type],
        STATEMENT_TITLES[statement_type],
        STATEMENT_TITLES[statement_type],
    )


def _parse_xml(content: bytes, *, name: str) -> ET.Element:
    if not content or len(content) > _MAX_LINKBASE_BYTES:
        raise StatementGraphError(f"{name} exceeds linkbase bound")
    if b"\x00" in content:
        raise StatementGraphError(f"{name} contains NUL")
    upper = content.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise StatementGraphError(f"{name} declares a DTD or entity")
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise StatementGraphError(f"{name} is not well-formed XML") from exc


def _xlink(el: ET.Element, attr: str) -> str | None:
    return el.get(f"{{{XLINK}}}{attr}")


def concept_from_href(href: str) -> str:
    frag = href.rsplit("#", 1)[-1]
    for prefix in _PREFIXES:
        if frag.startswith(prefix):
            return f"{prefix[:-1]}:{frag[len(prefix):]}"
    if "_" in frag:
        head, rest = frag.split("_", 1)
        return f"{head}:{rest}"
    return frag


def _local_name(concept: str) -> str:
    if ":" in concept:
        return concept.split(":", 1)[1]
    if concept.startswith("{") and "}" in concept:
        return concept.split("}", 1)[1]
    return concept


def fact_matches_concept(concept_qname: str, concept: str) -> bool:
    local = _local_name(concept)
    if not concept_qname.endswith("}" + local) and concept_qname != local:
        return False
    prefix = concept.split(":", 1)[0] if ":" in concept else ""
    if not prefix:
        return True
    return prefix in concept_qname


def _is_abstract_concept(concept: str) -> bool:
    local = _local_name(concept)
    return any(token in local for token in _ABSTRACT_TOKENS)


def parse_presentation_tree(content: bytes, *, role_uri: str) -> list[dict[str, Any]]:
    root = _parse_xml(content, name="presentation linkbase")
    link = None
    for el in root.iter(f"{{{LINK}}}presentationLink"):
        if _xlink(el, "role") == role_uri:
            link = el
            break
    if link is None:
        raise StatementGraphError(
            f"presentation role is absent: {role_uri}",
            refusal_code="statement_role_presentation_absent",
        )
    locs: dict[str, str] = {}
    for loc in link.findall(f"{{{LINK}}}loc"):
        label = _xlink(loc, "label")
        href = _xlink(loc, "href")
        if label and href:
            locs[label] = href
    children: dict[str, list[tuple[float, str, str | None, str | None]]] = {}
    parents: set[str] = set()
    targets: set[str] = set()
    arcs = list(link.findall(f"{{{LINK}}}presentationArc"))
    if len(arcs) > _MAX_ARCS:
        raise StatementGraphError("presentation arc limit exceeded")
    for arc in arcs:
        if arc.get("use") == "prohibited":
            continue
        frm = _xlink(arc, "from")
        to = _xlink(arc, "to")
        if not frm or not to:
            continue
        order_raw = arc.get("order") or "0"
        try:
            order = float(order_raw)
        except ValueError:
            order = 0.0
        children.setdefault(frm, []).append((order, to, arc.get("preferredLabel"), order_raw))
        parents.add(frm)
        targets.add(to)
    roots = sorted(p for p in parents if p not in targets)
    if len(roots) != 1:
        raise StatementGraphError(f"presentation role does not have a unique root: {role_uri}")
    rows: list[dict[str, Any]] = []

    def walk(label: str, depth: int, path: tuple[str, ...], preferred: str | None) -> None:
        href = locs.get(label)
        if href is None:
            raise StatementGraphError("presentation locator is missing")
        concept = concept_from_href(href)
        rows.append(
            {
                "order": len(rows),
                "depth": depth,
                "concept": concept,
                "href": href,
                "preferred_label_role": preferred,
                "presentation_path": list(path + (concept,)),
                "abstract": _is_abstract_concept(concept),
            }
        )
        kids = sorted(children.get(label, []), key=lambda item: (item[0], item[1]))
        for _order, child, pref, _raw in kids:
            walk(child, depth + 1, path + (concept,), pref)

    walk(roots[0], 0, (), None)
    return rows


def parse_labels(content: bytes) -> dict[tuple[str, str], str]:
    root = _parse_xml(content, name="label linkbase")
    out: dict[tuple[str, str], str] = {}
    for link in root.iter(f"{{{LINK}}}labelLink"):
        locs: dict[str, str] = {}
        resources: dict[str, list[tuple[str, str]]] = {}
        for loc in link.iter(f"{{{LINK}}}loc"):
            label = _xlink(loc, "label")
            href = _xlink(loc, "href")
            if label and href:
                locs[label] = concept_from_href(href)
        for lab in link.iter(f"{{{LINK}}}label"):
            key = _xlink(lab, "label")
            role = _xlink(lab, "role") or LABEL_STANDARD
            text = "".join(lab.itertext()).strip()
            if key and text:
                resources.setdefault(key, []).append((role, text))
        for arc in link.iter(f"{{{LINK}}}labelArc"):
            if arc.get("use") == "prohibited":
                continue
            frm = _xlink(arc, "from")
            to = _xlink(arc, "to")
            if frm not in locs or to not in resources:
                continue
            for role, text in resources[to]:
                out[(locs[frm], role)] = text
    return out


def parse_calculations(content: bytes) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    """Map role_uri -> parent concept -> ((child_concept, weight), ...) from calc arcs.

    A primary statement may consume only the relationships belonging to its
    exact xlink:role. Cross-role parents are not merged.
    """
    root = _parse_xml(content, name="calculation linkbase")
    by_role: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for link in root.iter(f"{{{LINK}}}calculationLink"):
        role = _xlink(link, "role")
        if not role:
            raise StatementGraphError("calculation network is missing xlink:role")
        locs: dict[str, str] = {}
        for loc in link.findall(f"{{{LINK}}}loc"):
            label = _xlink(loc, "label")
            href = _xlink(loc, "href")
            if label and href:
                locs[label] = concept_from_href(href)
        by_parent = by_role.setdefault(role, {})
        for arc in link.findall(f"{{{LINK}}}calculationArc"):
            if arc.get("use") == "prohibited":
                continue
            frm = _xlink(arc, "from")
            to = _xlink(arc, "to")
            if frm not in locs or to not in locs:
                continue
            weight = arc.get("weight") or "1"
            by_parent.setdefault(locs[frm], []).append((locs[to], weight))
    return {
        role: {parent: tuple(children) for parent, children in parents.items()}
        for role, parents in by_role.items()
    }


def _search_normalize(text: str) -> str:
    """Case-insensitive, whitespace-normalised form for title search lists."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def _iso_dates_from_text(text: str) -> list[str]:
    out: list[str] = []
    for match in _DATE_RE.finditer(text):
        month = _MONTHS[match.group(1).lower()]
        out.append(f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}")
    return out


def _month_day_pairs_from_text(text: str) -> list[tuple[int, int]]:
    """Month-day phrases without a year, in text order ("January 31," -> (1, 31))."""
    return [
        (_MONTHS[match.group(1).lower()], int(match.group(2)))
        for match in _MONTH_DAY_RE.finditer(text)
    ]


def _compose_year_row_header(
    rows: list[list[dict[str, Any]]],
) -> tuple[list[str], frozenset[int], str] | None:
    """Compose year-only header columns from a month-day banner over a year row.

    Fiscal-year statements print the period as
    "Fiscal Year Ended January 31," on one header row and bare 4-digit years on
    the next. When no row yields two full dates, the banner's single month-day
    phrase plus the year row's display order compose one ISO date per year
    column. Both rows must sit above the first fact-bearing row and carry no
    facts. An ambiguous banner (two distinct month-days) or a year row that is
    not purely years (fewer than two, or any other non-empty cell besides "$")
    returns None so the caller keeps its existing refusal. Returns the composed
    ISO dates, the consumed row indices, and the composition source:
    ``"composed_title_year_row"`` when a title banner reached its year row
    across one exact unit band, otherwise ``"composed_year_row"``.

    Three source-observed variants compose the same way (each column still
    binds to its own facts' contexts downstream): a banner printed in the
    leading cell of its own year row (``"composed_same_row"``); and, when the
    exact shape above fails under a banner row with no N-months-ended
    group-banner cell, fully blank rows before the year row
    (``"composed_blank_gap_year_row"``) and/or one leading whole-cell unit
    caption in the year row (``"composed_caption_year_row"``).
    """
    first_fact_row = next(
        (index for index, cells in enumerate(rows) if any(cell["facts"] for cell in cells)),
        None,
    )
    header_limit = first_fact_row if first_fact_row is not None else len(rows)
    for index in range(min(header_limit, len(rows) - 1)):
        banner_cells = rows[index]
        if any(cell["facts"] for cell in banner_cells):
            continue
        same_row = _compose_same_row_banner(banner_cells)
        if same_row is not None:
            return same_row, frozenset({index}), "composed_same_row"
        month_days = _month_day_pairs_from_text(
            " ".join(cell["text"] for cell in banner_cells)
        )
        if not month_days:
            continue
        distinct = sorted(set(month_days))
        if len(distinct) != 1:
            return None
        month, day = distinct[0]
        exact = _compose_exact_year_row(rows, index, header_limit, month, day)
        if exact is not None or _has_group_banner_cell(banner_cells):
            return exact
        return _compose_gap_or_caption_year_row(rows, index, header_limit, month, day)
    return None


def _compose_exact_year_row(
    rows: list[list[dict[str, Any]]], index: int, header_limit: int, month: int, day: int
) -> tuple[list[str], frozenset[int], str] | None:
    """The banner's immediate year row, or the year row after one exact unit band."""
    year_row = index + 1
    year_cells = rows[year_row]
    # Some annual statements print a factless, unit-only band between the
    # "at December 31," title and the bare-year comparative row.  This is
    # a narrow, source-observed interstitial, not an invitation to skip any
    # arbitrary narrative or extra header row.
    units = [str(cell["text"]).strip() for cell in year_cells if str(cell["text"]).strip()]
    skip_units = (
        year_row + 1 < header_limit
        and not any(cell["facts"] for cell in year_cells)
        # Other observed annual headings use the same one-row
        # position for different, but exact, statement-unit labels.
        and len(units) == 1
        and units[0] in _STATEMENT_UNIT_BANDS
    )
    if skip_units:
        year_row += 1
        year_cells = rows[year_row]
    if any(cell["facts"] for cell in year_cells):
        return None
    years: list[str] = []
    for cell in year_cells:
        text = str(cell["text"]).strip()
        if not text or text == "$":
            continue
        if not _YEAR_CELL_RE.match(text):
            return None
        years.append(text)
    if len(years) < 2:
        return None
    composed = [f"{int(year):04d}-{month:02d}-{day:02d}" for year in years]
    consumed = {index, year_row}
    if skip_units:
        consumed.add(index + 1)
    source = "composed_title_year_row" if skip_units else "composed_year_row"
    return composed, frozenset(consumed), source


def _header_texts(cells: list[dict[str, Any]]) -> list[str]:
    """A header row's non-empty cell texts besides "$", in display order."""
    texts = [str(cell["text"]).strip() for cell in cells]
    return [text for text in texts if text and text != "$"]


def _has_group_banner_cell(cells: list[dict[str, Any]]) -> bool:
    """True when any header cell is an N-months-ended group banner."""
    texts = [str(cell["text"]).strip() for cell in cells]
    return any(_GROUP_BANNER_RE.match(text) for text in texts)


def _composed_year_dates(years: list[str], month: int, day: int) -> list[str] | None:
    """One ISO date per bare year, or None when the month-day is not a real date that year."""
    if len(years) < 2 or not all(_YEAR_CELL_RE.match(text) for text in years):
        return None
    if any(not 1 <= day <= calendar.monthrange(int(year), month)[1] for year in years):
        return None
    return [f"{int(year):04d}-{month:02d}-{day:02d}" for year in years]


def _compose_same_row_banner(cells: list[dict[str, Any]]) -> list[str] | None:
    """Composed dates when one factless header row prints the banner and its years.

    The leading cell carries exactly one month-day phrase and no full date
    ("years ended December 31 (in millions, except per share data)", "Year
    Ended April 30,"); every other cell besides "$" is a bare 4-digit year, at
    least two. An N-months-ended group banner keeps its own composer. Returns
    None when the row is not this shape.
    """
    texts = _header_texts(cells)
    if len(texts) < 3:
        return None
    banner, years = texts[0], texts[1:]
    if _GROUP_BANNER_RE.match(banner) or _iso_dates_from_text(banner):
        return None
    month_days = _month_day_pairs_from_text(banner)
    if len(month_days) != 1:
        return None
    month, day = month_days[0]
    return _composed_year_dates(years, month, day)


def _compose_gap_or_caption_year_row(
    rows: list[list[dict[str, Any]]], index: int, header_limit: int, month: int, day: int
) -> tuple[list[str], frozenset[int], str] | None:
    """Composed dates across fully blank rows and/or a leading unit caption.

    Observed annual shapes put fully blank rows between the month-day banner
    and its year row ("December 31" / blank / "(Dollars in millions) 2025
    2024"), or print the unit caption in the year row's leading cell ("In
    millions, except par value 2024 2023"). Only rows with no text at all are
    skipped; the first row with text must sit above the first fact row, may
    lead with one whole-cell unit caption, and must otherwise print at least
    two bare years. Returns None for anything else so the caller keeps its
    refusal.
    """
    year_row = index + 1
    while year_row < header_limit and not any(
        str(cell["text"]).strip() for cell in rows[year_row]
    ):
        year_row += 1
    if year_row >= header_limit:
        return None
    texts = _header_texts(rows[year_row])
    caption = bool(texts) and _UNIT_CAPTION_RE.match(texts[0]) is not None
    composed = _composed_year_dates(texts[1:] if caption else texts, month, day)
    if composed is None:
        return None
    source = "composed_caption_year_row" if caption else "composed_blank_gap_year_row"
    return composed, frozenset(range(index, year_row + 1)), source

def _first_fact_row(rows: list[list[dict[str, Any]]]) -> int | None:
    return next(
        (index for index, cells in enumerate(rows) if any(cell["facts"] for cell in cells)),
        None,
    )


def _compose_bare_year_row(
    rows: list[list[dict[str, Any]]], period_end: str
) -> tuple[list[str], frozenset[int], str] | None:
    """Compose bare-year columns from the filing's document period end date.

    Some annual statements print only bare years over their columns ("2025
    2024") and name no month anywhere in the table. When exactly one factless
    row above the first fact row prints two or more distinct bare years --
    optionally after one leading whole-cell unit caption -- and the latest of
    them is the document period end's year, each year takes that date's month
    and day. Any header row naming a month, week, quarter or N-months group,
    a second year row, a single year, a repeated year or a month-day that is
    not a real date in some year returns None, so the caller keeps its
    refusal. Every composed column must still bind exactly to its own facts'
    contexts downstream, so a wrong composed date fails closed.
    """
    header_limit = _first_fact_row(rows)
    if header_limit is None:
        return None
    try:
        end = date.fromisoformat(period_end)
    except ValueError:
        return None
    found: tuple[int, list[str]] | None = None
    for index in range(header_limit):
        cells = rows[index]
        if _BARE_YEAR_PERIOD_WORD_RE.search(" ".join(str(cell["text"]) for cell in cells)):
            return None
        texts = _header_texts(cells)
        if texts and _UNIT_CAPTION_RE.match(texts[0]):
            texts = texts[1:]
        if len(texts) < 2 or not all(_YEAR_CELL_RE.match(text) for text in texts):
            continue
        if found is not None:
            return None
        found = (index, texts)
    if found is None:
        return None
    index, years = found
    if len(set(years)) != len(years) or max(int(year) for year in years) != end.year:
        return None
    composed = _composed_year_dates(years, end.month, end.day)
    if composed is None:
        return None
    return composed, frozenset({index}), "composed_bare_year_row"


def _glued_header_cell_date(text: str) -> str | None:
    """ISO date for a whole header cell like ``June 302025`` (day glued to the year)."""
    match = _GLUED_DATE_CELL_RE.match(text.strip())
    if match is None:
        return None
    month = _MONTHS[match.group(1).lower()]
    day = int(match.group(2))
    year = int(match.group(3))
    if not _GLUED_YEAR_MIN <= year <= _GLUED_YEAR_MAX:
        return None
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _glued_header_columns(
    rows: list[list[dict[str, Any]]],
) -> tuple[list[str], frozenset[int]] | None:
    """Direct glued-date header columns (the glued consolidated balance-sheet shape).

    A row above the first fact row carrying two or more glued date cells is the
    dated header; a rowspan carry repeats the same texts one row down, so every
    such row is header chrome and consumed. Returns the ISO dates in cell order
    plus the consumed row indices, or None when no row qualifies.
    """
    first_fact = _first_fact_row(rows)
    header_limit = first_fact if first_fact is not None else len(rows)
    dates: list[str] = []
    consumed: set[int] = set()
    for index in range(header_limit):
        cells = rows[index]
        if any(cell["facts"] for cell in cells):
            continue
        row_dates = [
            iso
            for cell in cells
            if (iso := _glued_header_cell_date(str(cell["text"]))) is not None
        ]
        if len(row_dates) < 2:
            continue
        if not dates:
            dates = row_dates
        elif row_dates != dates:
            return None
        consumed.add(index)
    if not dates:
        return None
    return dates, frozenset(consumed)


def _is_bare_month_day_row(cells: list[dict[str, Any]]) -> bool:
    """A factless header row whose only text cells are bare month-day phrases."""
    texts = [str(cell["text"]).strip() for cell in cells if str(cell["text"]).strip()]
    if not texts:
        return False
    return all(_BARE_MONTH_DAY_RE.match(text) for text in texts)


def _shift_month_back(year: int, month: int, back: int) -> tuple[int, int]:
    index = month - back
    while index < 1:
        index += 12
        year -= 1
    return year, index


def _compose_grouped_duration_year_row(
    rows: list[list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], frozenset[int], list[int]] | None:
    """Composed duration columns from N-months-ended group banners over a year row.

    The banner consolidated income/cash-flow shape prints one banner per duration
    ("Three Months Ended June 30", "Six Months Ended June 30") with the years
    in a row beneath it; each group owns its own duration and end date, so a
    single composed end-date row would erase the 3m/6m distinction. Fully blank
    rows (and one exact statement unit band) may sit between a banner and its
    year row. Raises a typed refusal when a group's span does not cover an
    exact contiguous run of year cells, or when years within a group are not
    strictly descending; returns None when the header is not this shape.
    Returns the composed column periods, the consumed row indices, and the
    year count per group.
    """
    first_fact = _first_fact_row(rows)
    header_limit = first_fact if first_fact is not None else len(rows)
    banner_row: int | None = None
    groups: list[dict[str, Any]] = []
    for index in range(header_limit):
        cells = rows[index]
        if any(cell["facts"] for cell in cells):
            continue
        row_groups: list[dict[str, Any]] = []
        other_text = False
        for column, cell in enumerate(cells):
            text = str(cell["text"]).strip()
            if not text:
                continue
            match = _GROUP_BANNER_RE.match(text)
            if match is None:
                other_text = True
                break
            row_groups.append(
                {
                    "column": column,
                    "colspan": int(cell.get("colspan") or 1),
                    "months": _GROUP_BANNER_MONTHS[match.group(1).lower()],
                    "month": _MONTHS[match.group(2).lower()],
                    "day": int(match.group(3)),
                }
            )
        if row_groups and not other_text:
            banner_row = index
            groups = row_groups
            break
    if banner_row is None or not groups:
        return None
    year_row: int | None = None
    consumed: set[int] = {banner_row}
    unit_band_consumed = False
    for index in range(banner_row + 1, header_limit):
        cells = rows[index]
        if any(cell["facts"] for cell in cells):
            break
        texts = [str(cell["text"]).strip() for cell in cells]
        nonempty = [text for text in texts if text]
        if not nonempty:
            consumed.add(index)
            continue
        if len(nonempty) == 1 and nonempty[0] in _STATEMENT_UNIT_BANDS:
            if unit_band_consumed:
                return None
            unit_band_consumed = True
            consumed.add(index)
            continue
        year_row = index
        break
    if year_row is None:
        return None
    consumed.add(year_row)
    year_cells: list[tuple[int, int, int]] = []
    for column, cell in enumerate(rows[year_row]):
        text = str(cell["text"]).strip()
        if not text or text == "$":
            continue
        if _YEAR_CELL_RE.match(text):
            year_cells.append((column, int(cell.get("colspan") or 1), int(text)))
    if len(year_cells) < 2:
        return None
    spans = [(group["column"], group["column"] + group["colspan"]) for group in groups]
    for low, high in spans:
        for column, cell in enumerate(rows[year_row]):
            text = str(cell["text"]).strip()
            if not text or text == "$":
                continue
            if low <= column < high and not _YEAR_CELL_RE.match(text):
                raise _layout_unsupported(
                    "grouped duration banner does not cover an exact contiguous run of year cells",
                    refusal_code="displayed_layout_unsupported",
                )
    per_group: list[list[int]] = [[] for _ in groups]
    for start, colspan, year in year_cells:
        covers = [
            group_index
            for group_index, (low, high) in enumerate(spans)
            if low <= start and start + colspan <= high
        ]
        if len(covers) != 1:
            raise _layout_unsupported(
                "grouped duration banner does not cover an exact contiguous run of year cells",
                refusal_code="displayed_layout_unsupported",
            )
        per_group[covers[0]].append(year)
    for years in per_group:
        if not years or years != sorted(years, reverse=True) or len(set(years)) != len(years):
            raise _layout_unsupported(
                "grouped duration years are not strictly descending",
                refusal_code="displayed_layout_unsupported",
            )
    columns_periods: list[dict[str, Any]] = []
    for group, years in zip(groups, per_group):
        for year in years:
            if group["day"] > calendar.monthrange(year, group["month"])[1]:
                return None
            start_year, start_month = _shift_month_back(
                year, group["month"], group["months"] - 1
            )
            columns_periods.append(
                {
                    "kind": "duration",
                    "start": f"{start_year:04d}-{start_month:02d}-01",
                    "end": f"{year:04d}-{group['month']:02d}-{group['day']:02d}",
                }
            )
    return columns_periods, frozenset(consumed), [len(years) for years in per_group]


def _is_ix_numeric(tag: str) -> bool:
    compact = tag.replace("-", "").lower()
    return compact.endswith("nonfraction") or compact.endswith(":nonfraction")


_DISPLAYED_LAYOUT_UNSUPPORTED = "displayed statement layout unsupported:"


def _layout_unsupported(detail: str, *, refusal_code: str | None = None) -> StatementGraphError:
    return StatementGraphError(
        f"{_DISPLAYED_LAYOUT_UNSUPPORTED} {detail}",
        refusal_code=refusal_code,
    )


def _grid_slot(*, text: str, facts: list[dict[str, Any]], colspan: int, rowspan: int, rowspan_carry: bool, colspan_carry: bool) -> dict[str, Any]:
    return {
        "text": text,
        "facts": facts,
        "colspan": colspan,
        "rowspan": rowspan,
        "rowspan_carry": rowspan_carry,
        "colspan_carry": colspan_carry,
    }


def _expand_displayed_statement_grid(raw_rows: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    """Place source cells onto a (row, col) grid honoring rowspan/colspan.

    Origin slots keep text and facts. Colspan continuations are empty placeholders so
    spacer groups (the AAPL pattern) do not duplicate dates or facts. A label rowspan
    carries its text down the occupied rows with ``rowspan_carry``. A fact-free row
    narrower than the grid gets ``edge_pad`` slots on its right edge only. Overlap,
    a span past the captured table, a span overflow, or an interior hole after
    expansion is ``displayed statement layout unsupported``.
    """
    if not raw_rows:
        return []
    occupied: dict[int, dict[int, dict[str, Any]]] = {}
    row_count = len(raw_rows)
    max_col = 0

    def place(row: int, col: int, cell: dict[str, Any]) -> None:
        slot = occupied.setdefault(row, {})
        if col in slot:
            raise _layout_unsupported(
                f"overlapping cell at row {row} column {col}",
                refusal_code="displayed_layout_unsupported",
            )
        slot[col] = cell

    for row_index, raw in enumerate(raw_rows):
        column = 0
        for source in raw:
            if source.get("span_overflow"):
                raise _layout_unsupported(
                    "span exceeds the supported bound",
                    refusal_code="displayed_layout_unsupported",
                )
            colspan = int(source.get("colspan") or 1)
            rowspan = int(source.get("rowspan") or 1)
            if rowspan == 0:
                rowspan = row_count - row_index
            if colspan < 1 or rowspan < 1:
                raise _layout_unsupported(
                    "span is not a positive occupancy",
                    refusal_code="displayed_layout_unsupported",
                )
            while column in occupied.get(row_index, {}):
                column += 1
            for row_delta in range(rowspan):
                target_row = row_index + row_delta
                if target_row >= row_count:
                    raise _layout_unsupported(
                        "rowspan overruns the table",
                        refusal_code="displayed_layout_unsupported",
                    )
                for col_delta in range(colspan):
                    target_col = column + col_delta
                    if row_delta == 0 and col_delta == 0:
                        cell = _grid_slot(
                            text=str(source.get("text") or ""),
                            facts=list(source.get("facts") or []),
                            colspan=colspan,
                            rowspan=rowspan,
                            rowspan_carry=False,
                            colspan_carry=False,
                        )
                    elif row_delta == 0:
                        cell = _grid_slot(
                            text="",
                            facts=[],
                            colspan=1,
                            rowspan=1,
                            rowspan_carry=False,
                            colspan_carry=True,
                        )
                    elif col_delta == 0:
                        cell = _grid_slot(
                            text=str(source.get("text") or ""),
                            facts=[],
                            colspan=1,
                            rowspan=1,
                            rowspan_carry=True,
                            colspan_carry=False,
                        )
                    else:
                        cell = _grid_slot(
                            text="",
                            facts=[],
                            colspan=1,
                            rowspan=1,
                            rowspan_carry=True,
                            colspan_carry=True,
                        )
                    place(target_row, target_col, cell)
            column += colspan
            if column > max_col:
                max_col = column
        while column in occupied.get(row_index, {}):
            column += 1
            if column > max_col:
                max_col = column

    grid: list[list[dict[str, Any]]] = []
    for row_index in range(row_count):
        row_map = occupied.get(row_index, {})
        row_cells: list[dict[str, Any]] = []
        # k is one past this row's highest occupied column. A hole below k (or a
        # row with no occupied slot at all, k is None) is still unsupported;
        # missing slots from k to the table's right edge belong to a banner row
        # narrower than the body (an observed income-statement shape) and are
        # padded fact-free so the row expands onto the body's grid. Only a
        # fact-free row is padded: a narrow row carrying a fact would bind it to
        # whichever column its left-packed position happens to land on.
        k = max(row_map) + 1 if row_map else None
        row_has_facts = any(slot.get("facts") for slot in row_map.values())
        for column in range(max_col):
            cell = row_map.get(column)
            if cell is None and (k is None or column < k or row_has_facts):
                raise _layout_unsupported(
                    f"ragged grid at row {row_index} column {column}",
                    refusal_code="displayed_layout_unsupported",
                )
            if cell is None:
                cell = _grid_slot(
                    text="",
                    facts=[],
                    colspan=1,
                    rowspan=1,
                    rowspan_carry=False,
                    colspan_carry=True,
                )
                cell["edge_pad"] = True
            row_cells.append(cell)
        grid.append(row_cells)
    return grid


_TITLE_FOLD_DASH = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_TITLE_FOLD_QUOTE = re.compile("[\u2018\u2019\u02bc\u2032]")
# What may follow a folded title in a text node that arms the fold pass: an
# optional plural "s" (never after a title that already ends in "s"), then
# only these whole parenthesised qualifiers -- "(unaudited)", "(loss)", a
# footnote marker 1-99, or a unit caption whose "except" (or "except for")
# clause names only share, per-share, earnings-per-share, par-value,
# stated-value, unit, ratio or percentage amounts -- shares may be counted
# "in thousands" or "in millions" -- optionally closed by ", unaudited", such
# as "(in thousands, except share data)" or "(in millions, except per share
# data, unaudited)".  A sentence that merely names the statement ("We have
# audited the accompanying consolidated balance sheets") never arms it, and
# neither does an entity or continuation qualifier in the arming node
# ("(parent company only)", "(guarantor subsidiaries)", "(continued)"):
# those name a different table than the one the title declares.  A
# continuation marker printed in a neighbouring node before the capture
# holds any fact drops that capture (``_TITLE_FOLD_CONTINUED_RE``); an
# entity qualifier printed in a neighbouring node is invisible here, and the
# captured table's own contexts decide that case (``context_dimensions``).
_TITLE_FOLD_EXCEPT_ITEM = (
    r"(?:(?:earnings\s+)?per[\s-]share|shares?(?:\s+in\s+(?:thousands|millions))?"
    r"|number\s+of\s+shares|par\s+value|stated\s+value|per[\s-]unit|units?|ratios?"
    r"|percentages?)(?:\s+(?:data|amounts?|information|values?))?"
)
_TITLE_FOLD_UNIT_CAPTION = (
    r"(?:(?:dollars|amounts)\s+in\s+|in\s+)?(?:millions|thousands|billions)(?:\s+of\s+dollars)?"
    r"(?:(?:,\s*|\s+)except\s+(?:for\s+)?" + _TITLE_FOLD_EXCEPT_ITEM
    + r"(?:(?:\s*,\s*and\s+|\s*,\s*|\s+and\s+)" + _TITLE_FOLD_EXCEPT_ITEM + r")*)?"
    r"(?:\s*,\s*unaudited)?"
)
_TITLE_FOLD_QUALIFIER_RE = re.compile(
    r"^s?(?:\s*\((?:unaudited|loss|[1-9][0-9]?|" + _TITLE_FOLD_UNIT_CAPTION + r")\))*$"
)
# A folded continuation marker, after any leading title is removed:
# "(continued)", "continued", "- continued", ", continued:", the abbreviated
# "(cont'd)", "(cont'd.)", "(contd.)", "(con't)", "cont." and "cont",
# "continued from previous page" or "continued from page 45", or one after
# whole parenthesised qualifiers ("(in millions) (continued)").  It never
# matches "discontinued", "contingencies" or "(continued on next page)".
_TITLE_FOLD_CONTINUED_RE = re.compile(
    r"^s?(?:\s*\([^()]*\))*\s*[-,]?\s*\(?(?:continued|cont(?:'?d\.?|\.)?|con't\.?)"
    r"(?:\s+from\s+(?:(?:the\s+)?(?:previous|prior|preceding)\s+page|page\s+[0-9]{1,4}))?"
    r"\)?[.:]?$"
)


def _title_fold(text: str) -> str:
    """Case, dash and quote fold for the second displayed-title pass."""
    folded = re.sub(r"\s+", " ", text).strip().casefold()
    folded = _TITLE_FOLD_QUOTE.sub("'", _TITLE_FOLD_DASH.sub("-", folded))
    return re.sub(r"\s*-\s*", "-", folded)


def _title_fold_suffix_arms(folded_title: str, suffix: str) -> bool:
    """Whether ``suffix``, printed after a folded title, may arm the fold pass."""
    if folded_title.endswith("s") and suffix.startswith("s"):
        return False
    return _TITLE_FOLD_QUALIFIER_RE.match(suffix) is not None


# Title-block carry (``carry=True``): the most rows a factless heading table
# may print and still hand its title to the table after it, and the page
# reference ("45", "F-12") whose presence marks a contents table instead.
# A line naming another statement ("Balance Sheets", "Statements of
# Operations", "Cash Flow Statement", "Notes to ...", "Report of ...") that is
# not the declared title, or naming a non-consolidated entity ("Parent
# Company", "Registrant", "Guarantor", "(Parent Only)", "Holding Company
# Only", "Bank Only"), marks a contents table or another entity's heading
# when the heading table prints it, and a table with a heading of its own
# when the carried table prints it before its first fact.  Both match the
# line with its whitespace removed, so a ``<br>``-broken heading
# ("Statements of<br>Operations") is still in view.  ``_TITLE_BLOCK_BLANK_RE``
# is what a browser does not print (whitespace, zero-width and soft-hyphen
# characters); ``_TITLE_BLOCK_CONTINUED_TAIL_RE`` is a continuation marker
# ending a ``_title_fold`` line that names the title somewhere before it
# ("... of Operations and Comprehensive Income (Continued)"), its boundary
# keeping "discontinued" out; ``_TITLE_BLOCK_LINE_TAGS`` end a line of text
# printed outside cells, which inline tags (``<b>``, ``<span>``, ``<br>``)
# do not.
_TITLE_BLOCK_MAX_ROWS = 6
_TITLE_BLOCK_PAGE_REF_RE = re.compile(r"^(?:[A-Z]{1,2}-)?[0-9]{1,3}$")
_TITLE_BLOCK_OTHER_STATEMENT_RE = re.compile(
    r"balancesheets?|statements?of|incomestatements?|cashflowstatements?|notesto|reportof",
    re.IGNORECASE,
)
_TITLE_BLOCK_ENTITY_RE = re.compile(
    r"parentcompany|registrant|guarantor|parentonly|companyonly|bankonly", re.IGNORECASE
)
_TITLE_BLOCK_BLANK_RE = re.compile(r"[\s\u200b\ufeff\u00ad\u2060]+")
_TITLE_BLOCK_CONTINUED_TAIL_RE = re.compile(
    r"(?:^|[\s(,-])\(?(?:continued|cont(?:'?d\.?|\.)|con't\.?)"
    r"(?:\s+from\s+(?:(?:the\s+)?(?:previous|prior|preceding)\s+page|page\s+[0-9]{1,4}))?"
    r"\)?[.:]?$"
)
_TITLE_BLOCK_LINE_TAGS = frozenset(
    {
        "article", "blockquote", "body", "caption", "center", "div", "footer", "h1", "h2",
        "h3", "h4", "h5", "h6", "header", "hr", "html", "li", "ol", "p", "pre", "section",
        "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }
)


class _StatementTableParser(HTMLParser):
    """Visible HTML table for one captured primary statement title.

    ``title`` is a single string (matched exactly as written -- the byte-pinned
    golden AAPL path) or a list of candidates tried in declared order
    case-insensitively over whitespace-normalised text; the first candidate
    present in the filing locates the table.  A single string is matched
    exactly as written, and ``parse_displayed_primary_table`` retries a single
    string once with ``fold=True`` (``_title_fold``: case, dashes, quotes)
    when the exact search finds no table.  On that fold pass, when
    ``context_dimensions`` maps the filing's context ids to their dimension
    signatures, a capture is kept only if a strict majority of its value
    facts sit in undimensioned contexts or it is an entity-grouped face
    (``_capture_is_consolidated``), and a continuation marker seen before
    the capture holds any fact drops that capture.  With ``carry=True`` a
    factless title-block table hands its title to the next table instead of
    being discarded (``_carries_title_block``); ``parse_displayed_primary_table``
    runs that pass only after the exact and fold passes find no table.
    """

    def __init__(
        self,
        title: str | list[str],
        *,
        fold: bool = False,
        context_dimensions: Mapping[str, frozenset[tuple[str, str]]] | None = None,
        carry: bool = False,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._fold = fold
        self._carry = carry
        self._carried = False
        self.carried_capture = False
        self.carry_end_pos: tuple[int, int] | None = None
        self.carry_end_depth = 0
        self._tb_rows = 0
        self._tb_facts = 0
        self._tb_title_only = False
        self._tb_companion = False
        self._tb_title_named = False
        self._tb_other_table = False
        self._tb_page_ref = False
        self._tb_continued = False
        self._tb_loose: list[str] = []
        self._context_dimensions = (
            None if context_dimensions is None else dict(context_dimensions)
        )
        if isinstance(title, str):
            self._titles: tuple[str, ...] = (title,)
            self._folded_titles: tuple[str, ...] | None = None
        else:
            candidates = tuple(str(item) for item in title if str(item).strip())
            self._titles = candidates
            self._folded_titles = tuple(_search_normalize(item) for item in candidates)
        self.rows: list[list[dict[str, Any]]] = []
        self.chrome_row_indices: set[int] = set()
        self._hidden = 0
        self._table_depth = 0
        self._capturing = False
        self._seen_title = False
        self._discarded = False
        self._ended = False
        self._in_row = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self._cell_facts: list[dict[str, Any]] = []
        self._row_cells: list[dict[str, Any]] = []
        self._ix_open: dict[str, Any] | None = None
        self._cell_colspan = 1
        self._cell_rowspan = 1
        self._cell_span_overflow = False
        self._grid_finalized = False

    def _title_hit(self, text: str) -> str | None:
        """The first declared title present in ``text``, or None.

        After a factless capture has been discarded, a title only re-arms the
        capture when ``text`` is the title itself: a narrative sentence or a
        note row that merely names the statement no longer qualifies.  The
        fold pass never arms on containment, before or after a discard:
        ``text`` must fold to the title, optionally followed by a plural "s"
        and whole parenthesised qualifiers (``_TITLE_FOLD_QUALIFIER_RE``).
        """
        if self._folded_titles is None:
            if self._fold:
                folded_text = _title_fold(text)
                for candidate in self._titles:
                    folded_candidate = _title_fold(candidate)
                    if not folded_candidate:
                        continue
                    if folded_text.startswith(folded_candidate) and _title_fold_suffix_arms(
                        folded_candidate, folded_text[len(folded_candidate):]
                    ):
                        return candidate
                return None
            stripped = re.sub(r"\s+", " ", text).strip()
            for candidate in self._titles:
                if not candidate:
                    continue
                if self._discarded:
                    if stripped == candidate.strip():
                        return candidate
                elif candidate in text:
                    return candidate
            return None
        normalized = _search_normalize(text)
        for candidate, folded_candidate in zip(self._titles, self._folded_titles):
            if not folded_candidate:
                continue
            if self._discarded:
                if normalized == folded_candidate:
                    return candidate
            elif folded_candidate in normalized:
                return candidate
        return None

    def _title_only(self, text: str) -> bool:
        """Whether ``text`` is a declared title itself: equal to it after
        whitespace normalisation (a list candidate after ``_search_normalize``),
        or on the fold pass the folded title with only the qualifiers
        ``_title_fold_suffix_arms`` allows."""
        if self._folded_titles is None:
            if self._fold:
                folded_text = _title_fold(text)
                for candidate in self._titles:
                    folded_candidate = _title_fold(candidate)
                    if (
                        folded_candidate
                        and folded_text.startswith(folded_candidate)
                        and _title_fold_suffix_arms(
                            folded_candidate, folded_text[len(folded_candidate):]
                        )
                    ):
                        return True
                return False
            stripped = re.sub(r"\s+", " ", text).strip()
            return any(
                candidate.strip() and stripped == candidate.strip() for candidate in self._titles
            )
        normalized = _search_normalize(text)
        return any(folded and normalized == folded for folded in self._folded_titles)

    def _title_named(self, text: str) -> bool:
        """Whether ``text`` names a declared title anywhere in it, after
        ``_title_fold`` (a list candidate after ``_search_normalize``), with
        whitespace ignored so a ``<br>``-broken heading still names it.
        Containment, not equality: the carry pass uses it only to decline."""
        haystack, needles = self._title_needles(text)
        return any(needle in haystack for needle in needles)

    def _title_repeated(self, text: str) -> bool:
        """``_title_named`` except where the title only heads a longer
        statement title ("... of Operations and Comprehensive Income"): the
        carry follower's split test, so a qualified, recased or
        entity-prefixed repeat of the heading still marks a split."""
        haystack, needles = self._title_needles(text)
        for needle in needles:
            start = haystack.find(needle)
            while start >= 0:
                if not re.match(r"(?:and|&)", haystack[start + len(needle):]):
                    return True
                start = haystack.find(needle, start + 1)
        return False

    def _title_needles(self, text: str) -> tuple[str, list[str]]:
        if self._folded_titles is None:
            haystack = re.sub(r"\s+", "", _title_fold(text))
            folded = [_title_fold(candidate) for candidate in self._titles]
        else:
            haystack = re.sub(r"\s+", "", _search_normalize(text))
            folded = list(self._folded_titles)
        return haystack, [needle for needle in (re.sub(r"\s+", "", item) for item in folded) if needle]

    def _note_title_block_row(self, cells: list[dict[str, Any]], hit: str | None) -> None:
        # Carry pass only: what the current outermost table has printed so far,
        # for ``_carries_title_block`` and ``_close_capture`` at its end.  A
        # cell printing only characters a browser does not show is no
        # companion line, and a continuation marker before the first fact
        # marks a later part of a statement.
        prior_facts = self._tb_facts
        self._tb_rows += 1
        self._tb_facts += sum(len(cell.get("facts") or []) for cell in cells)
        nonblank = [cell["text"].strip() for cell in cells if cell["text"].strip()]
        visible = [item for item in nonblank if _TITLE_BLOCK_BLANK_RE.sub("", item)]
        if any(_TITLE_BLOCK_PAGE_REF_RE.match(item) for item in nonblank):
            self._tb_page_ref = True
        if hit is not None and len(visible) == 1 and self._title_only(visible[0]):
            self._tb_title_only = True
        joined = " ".join(visible)
        named = bool(visible) and self._title_named(joined)
        if visible and not named:
            self._tb_companion = True
        if named and not prior_facts:
            self._tb_title_named = True
        if nonblank and not prior_facts and self._names_other_table(joined, named):
            self._tb_other_table = True
        if (
            nonblank
            and not prior_facts
            and (
                any(self._continued(item) for item in nonblank)
                or self._continued(joined)
                or self._continuation_tail(joined)
            )
        ):
            self._tb_continued = True

    def _note_title_block_text(self, text: str) -> None:
        # Carry pass only: a line the current outermost table prints outside
        # its cells before its first numeric fact (a caption, or text a
        # browser hoists above the table) is a heading of that table and
        # declines the carry as the same line in a row would: naming the
        # title, another statement or entity, or a continuation marker.
        if not _TITLE_BLOCK_BLANK_RE.sub("", text):
            return
        named = self._title_named(text)
        if named:
            self._tb_title_named = True
        if self._names_other_table(text, named):
            self._tb_other_table = True
        if self._continued(text) or self._continuation_tail(text):
            self._tb_continued = True

    def _title_block_tag(self, tag: str) -> None:
        # Carry pass: a line tag ends the text buffered outside cells since
        # the last one (``_note_title_block_text``); a ``<br>`` in it is a
        # space.
        if not self._tb_loose:
            return
        if tag == "br":
            self._tb_loose.append(" ")
        elif tag in _TITLE_BLOCK_LINE_TAGS:
            text = "".join(self._tb_loose)
            self._tb_loose = []
            self._note_title_block_text(text)

    def _continuation_tail(self, text: str) -> bool:
        """Whether ``text`` names a declared title and ends in a continuation
        marker ("... of Operations and Comprehensive Income (Continued)"): a
        later part of a statement whose title only starts with the declared
        one, which ``_continued`` does not see."""
        return (
            self._title_named(text)
            and _TITLE_BLOCK_CONTINUED_TAIL_RE.search(_title_fold(text)) is not None
        )

    @staticmethod
    def _names_other_table(text: str, named: bool) -> bool:
        # Another statement than the declared one, or a non-consolidated entity.
        compact = re.sub(r"\s+", "", text)
        return (
            not named and _TITLE_BLOCK_OTHER_STATEMENT_RE.search(compact) is not None
        ) or _TITLE_BLOCK_ENTITY_RE.search(compact) is not None

    def _carries_title_block(self) -> bool:
        # A filing may print the statement title in a small heading table of
        # its own and the statement body, untitled, in the next table.  On the
        # carry pass such a heading table is not discarded like a contents
        # table: it holds no numeric fact, at most _TITLE_BLOCK_MAX_ROWS rows
        # and no page reference, one of its rows is the declared title alone in
        # its only nonblank cell, and another row prints a line that does not
        # name the title (an entity name, a units caption, "(Unaudited)", a
        # back-link).  A table printing the title and nothing else stays a
        # discarded factless capture (P5B R3): it reads like a contents entry
        # or a bare heading.  A heading table that names another statement
        # (a contents table without page references) or a non-consolidated
        # entity, or prints a continuation marker (a later part of a
        # statement), is not carried either.  Its title then arms the next
        # table.
        return (
            self._carry
            and self._table_depth == 0
            and self._tb_title_only
            and self._tb_companion
            and not self._tb_other_table
            and not self._tb_page_ref
            and not self._tb_continued
            and self._tb_facts == 0
            and 0 < self._tb_rows <= _TITLE_BLOCK_MAX_ROWS
        )

    def _row_title_hit(self, cells: list[dict[str, Any]]) -> str | None:
        """Title hit for a finished row: the joined row text, or after a
        discard, any single cell whose whole text is the title."""
        if not self._discarded:
            return self._title_hit(" ".join(cell["text"] for cell in cells))
        # Some annual balance sheets render the entire title in one cell with a
        # terminal comma ("... December 31,").  After a discarded factless TOC,
        # accept that precise punctuation variant only if the title is the
        # row's sole nonblank text and the row carries no numeric facts.  The
        # ordinary full-cell exact-title rule below remains unchanged; a note
        # with neighboring text or any other suffix cannot exploit this seam.
        nonblank = [cell for cell in cells if cell["text"].strip()]
        if len(nonblank) == 1 and not any(cell.get("facts") for cell in cells):
            title_text = nonblank[0]["text"].strip()
            if title_text.endswith(","):
                hit = self._title_hit(title_text[:-1].rstrip())
                if hit is not None:
                    return hit
        for cell in cells:
            hit = self._title_hit(cell["text"])
            if hit is not None:
                return hit
        return None

    def _continued(self, text: str) -> bool:
        """Whether ``text`` folds to a continuation marker, with or without
        a leading declared title ("(Continued)", "Balance Sheets - Continued")."""
        folded = _title_fold(text)
        for candidate in self._titles:
            folded_candidate = _title_fold(candidate)
            if folded_candidate and folded.startswith(folded_candidate):
                folded = folded[len(folded_candidate):]
                break
        return _TITLE_FOLD_CONTINUED_RE.match(folded.strip()) is not None

    def _continuation_before_facts(self, texts: list[str]) -> bool:
        # Fold and carry passes: a "(Continued)" marker printed with or next
        # to the title before the capture holds any fact marks a later part
        # of a statement whose first part did not arm the pass.  Serving it
        # would serve that part as the whole statement, so the capture is
        # dropped like a factless one; once facts are captured a marker
        # changes nothing.
        if not (self._fold or self._carry) or self._capture_has_facts():
            return False
        return any(self._continued(text) for text in texts)

    def _finalize_grid(self) -> None:
        if self._grid_finalized:
            return
        self._grid_finalized = True
        self.rows = _expand_displayed_statement_grid(self.rows)

    def _capture_has_facts(self) -> bool:
        return any(cell.get("facts") for cells in self.rows for cell in cells)

    def _capture_is_consolidated(self) -> bool:
        # Fold and carry passes: an entity qualifier printed in a node next to the
        # title (a "(Parent Company Only)" paragraph, a "GUARANTOR
        # SUBSIDIARIES" row, a heading above it) is invisible to the title
        # match.  Such a table is tagged on an entity axis, so its facts sit
        # mostly in dimensioned contexts, while the consolidated statement's
        # facts sit mostly in undimensioned ones.  An entity-grouped
        # consolidated face (manufacturing-group and finance-group lines on
        # one legal-entity axis, consolidated totals undimensioned) is kept
        # too: it carries undimensioned facts, every row's served facts sit
        # on a single signature, every dimensioned signature is one member of
        # the same axis, and two or more members appear.  A row's served facts
        # are the ones the line builder reads: those in cells after its label
        # cell, so a label that prints an inline amount ("less accumulated
        # depreciation of $X") does not split the row.  A consolidating schedule
        # mixes members within a row and a parent-only table names one
        # member, so both stay dropped.  A fact whose context has no known
        # signature only counts against the majority.  The exact pass and a
        # caller that supplies no contexts are unchanged.  The check reads the
        # grid the line builder reads, so a label carried down by rowspan is
        # its row's label; a layout that cannot expand is judged on its raw
        # rows, and _finalize_grid refuses it as before.
        if not (self._fold or self._carry) or self._context_dimensions is None:
            return True
        try:
            rows = _expand_displayed_statement_grid(self.rows)
        except StatementGraphError:
            rows = self.rows
        total = plain = 0
        entity_grouped = True
        members: set[tuple[str, str]] = set()
        for cells in rows:
            row_signatures: set[frozenset[tuple[str, str]] | None] = set()
            label_cell = next(
                (cell for cell in cells if cell.get("text") and cell.get("text") != "$"),
                None,
            )
            seen_label = False
            for cell in cells:
                served = seen_label and cell.get("text") != "$"
                if cell is label_cell:
                    seen_label = True
                for fact in cell.get("facts") or []:
                    total += 1
                    signature = self._context_dimensions.get(fact.get("context_ref"))
                    if served:
                        row_signatures.add(signature)
                    if signature is None:
                        entity_grouped = False
                    elif not signature:
                        plain += 1
                    elif len(signature) == 1:
                        members |= signature
                    else:
                        entity_grouped = False
            if len(row_signatures) > 1:
                entity_grouped = False
        if 2 * plain > total:
            return True
        return (
            entity_grouped
            and plain > 0
            and len(members) >= 2
            and len({axis for axis, _ in members}) == 1
        )

    def _close_capture(self) -> None:
        if self._capture_has_facts() and self._capture_is_consolidated():
            self._ended = True
            if (
                self._carried
                and not self._tb_title_named
                and not self._tb_other_table
                and not self._tb_continued
            ):
                # A carried table that names the title itself before its
                # first numeric fact is left to the exact and fold passes
                # and their re-arm rules; the carry never overrides them.
                # One that names another statement or entity there, or
                # prints a continuation marker, has a heading of its own and
                # is not carried either.
                self.carried_capture = True
                self.carry_end_pos = self.getpos()
                self.carry_end_depth = self._table_depth
            if not self._carry:
                # The carry pass builds a grid only for the carried table
                # it keeps (``_carried_title_block_parse``), so a declined
                # carry raises nothing and the earlier refusal stands.
                self._finalize_grid()
        elif self._carries_title_block():
            self.rows = []
            self.chrome_row_indices = set()
            self._capturing = False
            self._seen_title = True
            self._carried = True
        else:
            self._discard_factless_capture()

    def _discard_factless_capture(self) -> None:
        # A capture with zero inline-XBRL numeric facts is not the statement
        # (a table of contents naming it carries none), and neither is a fold
        # capture that fails ``_capture_is_consolidated`` or a fold or carry
        # capture that a continuation marker precedes: drop it and keep
        # parsing, so the next
        # title hit starts a fresh capture.
        self.rows = []
        self.chrome_row_indices = set()
        self._capturing = False
        self._seen_title = False
        self._discarded = True
        self._carried = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._ended:
            return
        self._title_block_tag(tag)
        ad = {key.lower(): value for key, value in attrs}
        if tag.endswith(":hidden") or tag == "ix:hidden":
            self._hidden += 1
            return
        if self._hidden:
            return
        if tag == "table":
            if not self._table_depth:
                # A row left open before an outermost table belongs to no row;
                # dropping it keeps handle_data from reading its facts.
                self._in_row = False
                self._row_cells = []
                self._tb_rows = 0
                self._tb_facts = 0
                self._tb_title_only = False
                self._tb_companion = False
                self._tb_title_named = False
                self._tb_other_table = False
                self._tb_page_ref = False
                self._tb_continued = False
            self._table_depth += 1
            return
        if tag == "tr":
            # Rows buffer even before the title is seen: EDGAR R-file viewer
            # chrome prints the statement title inside the first header row's
            # th cells, so that row must be capturable for the decision at its
            # own </tr>. Pre-title rows are dropped at their row end.
            self._in_row = True
            self._row_cells = []
            return
        if tag in {"td", "th"} and self._in_row:
            attr_map = _attribute_map(attrs)
            self._in_cell = True
            self._cell_text = []
            self._cell_facts = []
            self._cell_colspan = _span_attribute(attr_map.get("colspan"))
            self._cell_rowspan = _span_attribute(attr_map.get("rowspan"), rowspan=True)
            self._cell_span_overflow = _span_overflow(attr_map.get("colspan")) or _span_overflow(
                attr_map.get("rowspan")
            )
            return
        if self._in_cell and _is_ix_numeric(tag):
            self._ix_open = {
                "name": ad.get("name"),
                "context_ref": ad.get("contextref"),
                "fact_id": ad.get("id"),
                "unit_ref": ad.get("unitref"),
                "scale": ad.get("scale"),
                "decimals": ad.get("decimals"),
                "nil": (ad.get("xsi:nil") or ad.get("nil") or "").lower() in {"true", "1"},
            }

    def handle_endtag(self, tag: str) -> None:
        if self._ended:
            return
        self._title_block_tag(tag)
        if tag.endswith(":hidden") or tag == "ix:hidden":
            if self._hidden:
                self._hidden -= 1
            return
        if self._hidden:
            return
        if tag in {"td", "th"} and self._in_cell:
            text = re.sub(r"\s+", " ", "".join(self._cell_text)).strip()
            self._row_cells.append(
                {
                    "text": text,
                    "facts": list(self._cell_facts),
                    "colspan": self._cell_colspan,
                    "rowspan": self._cell_rowspan,
                    "span_overflow": self._cell_span_overflow,
                    "rowspan_carry": False,
                    "colspan_carry": False,
                }
            )
            self._in_cell = False
            self._cell_text = []
            self._cell_facts = []
            self._cell_colspan = 1
            self._cell_rowspan = 1
            self._cell_span_overflow = False
            return
        if tag == "tr" and self._in_row:
            self._in_row = False
            if self._row_cells:
                joined = " ".join(cell["text"] for cell in self._row_cells)
                hit = self._row_title_hit(self._row_cells)
                if hit is not None and self._continuation_before_facts(
                    [cell["text"] for cell in self._row_cells]
                ):
                    hit = None
                if self._carry and self._table_depth:
                    self._note_title_block_row(self._row_cells, hit)
                if hit is not None:
                    self._seen_title = True
                    self._capturing = True
                    if self._carries_span_structure(self._row_cells):
                        # EDGAR R-file viewer chrome carries the header block's
                        # spans on the title row itself (label th rowspan over
                        # the date row, period-group th colspan defining the
                        # width). Dropping that row would tear the grid, so it
                        # stays captured for structure; the composer skips it as
                        # a display row. A span-free title row (the AAPL shape)
                        # stays dropped exactly as before.
                        self.chrome_row_indices.add(len(self.rows))
                        self.rows.append(self._row_cells)
                elif self._capturing or self._seen_title:
                    self._capturing = True
                    if "see accompanying notes" in joined.lower():
                        self._row_cells = []
                        self._close_capture()
                        return
                    if not any(cell.get("facts") for cell in self._row_cells) and (
                        self._continuation_before_facts(
                            [cell["text"] for cell in self._row_cells]
                        )
                    ):
                        self._row_cells = []
                        self._discard_factless_capture()
                        return
                    self.rows.append(self._row_cells)
            self._row_cells = []
            return
        if tag == "table" and self._table_depth:
            self._table_depth -= 1
            if not self._table_depth:
                # A row whose </tr> never came ends with its outermost table.
                self._in_row = False
                self._row_cells = []
            if self._capturing and self._table_depth == 0:
                self._close_capture()
        if self._ix_open is not None and _is_ix_numeric(tag):
            self._cell_facts.append(self._ix_open)
            self._ix_open = None

    @staticmethod
    def _carries_span_structure(cells: list[dict[str, Any]]) -> bool:
        return any(
            int(cell.get("colspan") or 1) > 1 or int(cell.get("rowspan") or 1) > 1
            for cell in cells
        )

    def handle_data(self, data: str) -> None:
        if self._ended or self._hidden:
            return
        if (
            self._carry
            and self._table_depth
            and not self._in_cell
            and not self._tb_facts
            and (self._tb_loose or _TITLE_BLOCK_BLANK_RE.sub("", data))
        ):
            # Carry pass: text a table prints outside its cells before its
            # first numeric fact is buffered to the next line tag and read
            # there as a heading of that table (``_title_block_tag``).
            self._tb_loose.append(data)
        if (
            self._carried
            and not self._table_depth
            and re.sub(r"[\s\u200b\ufeff]+", "", data)
        ):
            # Carry pass: text printed between the title block and the table
            # after it (a heading, a caption, or a stray row outside any table,
            # which a browser shows as plain text) belongs to that table, which
            # is then no longer the untitled body of the block; drop the carry.
            self._discard_factless_capture()
        elif self._in_cell:
            self._cell_text.append(data)
        elif self._titles and self._title_hit(data) is not None:
            self._seen_title = True
        elif (
            (self._seen_title or self._capturing)
            and not any(cell.get("facts") for cell in self._row_cells)
            and self._continuation_before_facts([data])
        ):
            self._discard_factless_capture()


class _TitleBlockFollower(HTMLParser):
    """What follows a carried capture, up to the end of the next outermost
    table holding a numeric fact: a cell or line of text that repeats the
    declared title (``_title_repeated``: with a qualifier, in another case
    or after an entity name), prints a continuation marker, or names the
    title and ends in one (``_continuation_tail``), marks the statement as
    split across tables (``split``).  Text outside cells is read node by
    node and also as a line joined up to the next line tag, so a heading
    broken by ``<br>`` or inline markup is read whole.  The rest of a table
    its capture closed inside (``depth``) is read too: a heading there marks
    the split once a numeric fact follows it, and its facts do not otherwise
    end the search."""

    def __init__(self, probe: _StatementTableParser, depth: int = 0) -> None:
        super().__init__(convert_charrefs=True)
        self._probe = probe
        self._hidden = 0
        self._table_depth = depth
        self._skip = depth > 0
        self._split_pending = False
        self._table_facts = 0
        self._cell_text: list[str] | None = None
        self._loose: list[str] = []
        self._done = False
        self.split = False

    def _check(self, text: str) -> None:
        if text.strip() and (
            self._probe._title_repeated(text)
            or self._probe._continued(text)
            or self._probe._continuation_tail(text)
        ):
            if self._skip:
                self._split_pending = True
            else:
                self.split = True
                self._done = True

    def _line(self, tag: str) -> None:
        if tag == "br":
            if self._loose:
                self._loose.append(" ")
        elif tag in _TITLE_BLOCK_LINE_TAGS and self._loose:
            text = "".join(self._loose)
            self._loose = []
            self._check(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        if tag.endswith(":hidden") or tag == "ix:hidden":
            self._hidden += 1
            return
        if self._hidden:
            return
        self._line(tag)
        if self._done:
            return
        if tag == "table":
            if not self._table_depth:
                self._table_facts = 0
            self._table_depth += 1
        elif tag in {"td", "th"} and self._table_depth:
            self._cell_text = []
        elif tag == "br" and self._cell_text is not None:
            self._cell_text.append(" ")
        elif self._table_depth and _is_ix_numeric(tag):
            if self._split_pending:
                self.split = True
                self._done = True
            elif not self._skip:
                self._table_facts += 1

    def handle_endtag(self, tag: str) -> None:
        if self._done:
            return
        if tag.endswith(":hidden") or tag == "ix:hidden":
            if self._hidden:
                self._hidden -= 1
            return
        if self._hidden:
            return
        self._line(tag)
        if self._done:
            return
        if tag in {"td", "th"} and self._cell_text is not None:
            self._check("".join(self._cell_text))
            self._cell_text = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if not self._table_depth:
                self._cell_text = None
                if self._skip:
                    self._skip = False
                elif self._table_facts:
                    self._done = True

    def handle_data(self, data: str) -> None:
        if self._done or self._hidden:
            return
        if self._cell_text is not None:
            self._cell_text.append(data)
        else:
            self._check(data)
            if not self._done and (self._loose or data.strip()):
                self._loose.append(data)

    def close(self) -> None:
        super().close()
        if not self._done and self._loose:
            text = "".join(self._loose)
            self._loose = []
            self._check(text)


def _title_block_split(html: str, parser: _StatementTableParser) -> bool:
    if parser.carry_end_pos is None:
        return True
    line, column = parser.carry_end_pos
    offset = 0
    for _ in range(line - 1):
        offset = html.index("\n", offset) + 1
    follower = _TitleBlockFollower(parser, parser.carry_end_depth)
    follower.feed(html[offset + column:])
    follower.close()
    return follower.split


def _carried_title_block_parse(
    html: str,
    title: str | list[str],
    context_dimensions: Mapping[str, frozenset[tuple[str, str]]] | None,
) -> _StatementTableParser | None:
    """The carry pass: the exact (then, for a single string, the fold) search
    again, letting a factless title-block table hand its title to the next
    table (``_carries_title_block``).  A capture is kept only when it is that
    carried table, it names neither the title nor another statement or
    entity, nor prints a continuation marker, before its first fact (in a
    row or outside its cells, as a caption), no text sits between the block
    and it, it passes ``_capture_is_consolidated`` when contexts are
    supplied, and nothing after it, through the rest of its own table and
    to the end of the next table holding a fact, names the title again,
    prints a continuation marker or names the title ending in one; a table
    printing its own heading, or a statement split across tables, keeps its
    refusal.
    The grid is built only for a kept capture, so a declined carry raises
    nothing and the exact and fold passes' refusal stands."""
    attempts: list[dict[str, Any]] = [{"carry": True, "context_dimensions": context_dimensions}]
    if isinstance(title, str):
        attempts.append({"fold": True, "context_dimensions": context_dimensions, "carry": True})
    for kwargs in attempts:
        parser = _StatementTableParser(title, **kwargs)
        parser.feed(html)
        parser.close()
        if parser.carried_capture and not _title_block_split(html, parser):
            parser._finalize_grid()
            if parser.rows:
                return parser
    return None


def parse_displayed_primary_table(
    html: str,
    *,
    title: str | list[str],
    context_dimensions: Mapping[str, frozenset[tuple[str, str]]] | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Source-backed composition of one captured primary filing table.

    ``title`` follows ``_StatementTableParser``: a single string matched exactly
    as written -- and retried once through ``_title_fold`` (case, dashes,
    quotes) when the exact search finds no table -- or a list of candidates
    tried in order.  ``context_dimensions`` (each filing context id's
    dimension signature, from ``_context_dimension_sets``) is used only by that
    fold retry, which keeps a captured table only when most of its value facts
    are undimensioned or it is an entity-grouped face. Columns come from a
    header row printing two or more full dates; when no row does, a month-day
    banner over a bare-year row (fiscal-year statements) composes the
    columns and the output carries ``"columns_source": "composed_year_row"``;
    a title banner composed across one exact unit band carries
    ``"composed_title_year_row"``; a banner printed in the same row as its
    years carries ``"composed_same_row"``; a banner reaching its year row
    across fully blank rows carries ``"composed_blank_gap_year_row"``, or
    ``"composed_caption_year_row"`` when that year row leads with a unit
    caption. Duration groups ("Three Months Ended
    June 30" over a year row) carry ``"composed_grouped_duration_year_row"``
    plus each column's own period under ``"columns_periods"``; a glued-date
    header row ("June 302025") composes plain dated columns like the full-date
    path (both absent on the full-date path). When ``period_end`` (the
    filing's single document period end date) is given and no other path
    yields columns, one bare-year row whose latest year is that date's year
    takes its month and day (``"composed_bare_year_row"``); a header naming
    any month, week, quarter or N-months group never does. Without
    ``period_end`` the output is unchanged.
    """
    title_label = title if isinstance(title, str) else ", ".join(str(item) for item in title)
    if not title_label.strip():
        raise StatementGraphError("displayed statement title search is empty")
    parser = _StatementTableParser(title)
    parser.feed(html)
    parser.close()
    parser._finalize_grid()
    if not parser.rows and isinstance(title, str):
        parser = _StatementTableParser(
            title, fold=True, context_dimensions=context_dimensions
        )
        parser.feed(html)
        parser.close()
        parser._finalize_grid()
    carried = None
    if not parser.rows:
        carried = _carried_title_block_parse(html, title, context_dimensions)
        if carried is not None:
            parser = carried
    if not parser.rows:
        raise StatementGraphError(
            f"displayed statement table is absent: {title_label}",
            refusal_code="displayed_table_absent",
        )
    composed: tuple[list[str], frozenset[int], str] | None = None
    grouped: tuple[list[dict[str, Any]], frozenset[int], list[int]] | None = None
    glued: tuple[list[str], frozenset[int]] | None = None
    if not any(
        len(_iso_dates_from_text(" ".join(cell["text"] for cell in cells))) >= 2
        for cells in parser.rows
    ):
        composed = _compose_year_row_header(parser.rows)
        if composed is None:
            grouped = _compose_grouped_duration_year_row(parser.rows)
        if composed is None and grouped is None:
            glued = _glued_header_columns(parser.rows)
        if composed is None and grouped is None and glued is None and period_end is not None:
            composed = _compose_bare_year_row(parser.rows, period_end)
    if composed is not None:
        consumed = composed[1]
    elif grouped is not None:
        consumed = grouped[1]
    elif glued is not None:
        consumed = glued[1]
    else:
        consumed = frozenset()
    first_fact_row = _first_fact_row(parser.rows)
    fact_row_limit = first_fact_row if first_fact_row is not None else len(parser.rows)
    header_dates: list[str] = []
    display_rows: list[dict[str, Any]] = []
    for index, cells in enumerate(parser.rows):
        if index in consumed:
            continue
        if (
            glued is not None
            and index < fact_row_limit
            and not any(cell["facts"] for cell in cells)
            and _is_bare_month_day_row(cells)
        ):
            # A bare "December 31" banner fragment above a glued-date header.
            continue
        joined = " ".join(cell["text"] for cell in cells)
        dates = _iso_dates_from_text(joined)
        if not header_dates and len(dates) >= 2:
            header_dates = dates
            continue
        if index in parser.chrome_row_indices and not any(cell["facts"] for cell in cells):
            # Viewer-chrome title row kept only so its spans expand; no facts, no dates.
            continue
        label_cell = next((cell for cell in cells if cell["text"] and cell["text"] != "$"), None)
        if label_cell is None and not any(cell["facts"] for cell in cells):
            continue
        label = str(label_cell["text"]).strip() if label_cell else ""
        if not label and not any(cell["facts"] for cell in cells):
            continue
        if label.strip().lower() in _PERIOD_BANNER_LABELS:
            continue
        value_facts: list[dict[str, Any]] = []
        seen_label = False
        for cell in cells:
            if not seen_label:
                if cell is label_cell:
                    seen_label = True
                continue
            if cell["text"] == "$":
                continue
            value_facts.extend(cell["facts"])
        display_rows.append(
            {
                "label": label,
                "value_facts": value_facts,
                "abstract": not bool(value_facts),
                "rowspan_carry": bool(label_cell and label_cell.get("rowspan_carry")),
                "order": len(display_rows),
            }
        )
    if composed is not None:
        header_dates = composed[0]
    if glued is not None:
        header_dates = glued[0]
    if grouped is not None:
        header_dates = [spec["end"] for spec in grouped[0]]
        years_per_group = grouped[2]
        fact_columns = max(
            (len(spec["value_facts"]) for spec in display_rows), default=0
        )
        if fact_columns > 0 and (
            len(set(years_per_group)) != 1
            or years_per_group[0] * len(years_per_group) != fact_columns
        ):
            raise _layout_unsupported(
                "grouped duration groups do not match the displayed fact columns",
                refusal_code="displayed_layout_unsupported",
            )
    if len(header_dates) < 2:
        raise StatementGraphError(
            f"displayed statement columns are absent: {title_label}",
            refusal_code="displayed_columns_absent",
        )
    # Values bind to columns by position, so a row carrying more values than the
    # table prints dated columns would silently lose its trailing values. The
    # right-edge pad lets a narrow banner row widen onto the body's grid; it must
    # never let a body value sit beyond the dated columns.
    for spec in display_rows:
        if len(spec["value_facts"]) > len(header_dates):
            raise _layout_unsupported(
                f"row {spec['order']} carries {len(spec['value_facts'])} values for {len(header_dates)} dated columns",
                refusal_code="displayed_layout_unsupported",
            )
    output: dict[str, Any] = {"columns_iso": header_dates, "rows": display_rows}
    if composed is not None:
        output["columns_source"] = composed[2]
    if grouped is not None:
        output["columns_source"] = "composed_grouped_duration_year_row"
        output["columns_periods"] = grouped[0]
    if carried is not None:
        output["table_source"] = "carried_title_block"
    return output


def resolve_label(labels: Mapping[tuple[str, str], str], concept: str, preferred: str | None) -> tuple[str, str]:
    for role in (preferred, LABEL_TERSE, LABEL_STANDARD):
        if role and (concept, role) in labels:
            return labels[(concept, role)], role
    return _local_name(concept), "concept_local_name"


def _undimensioned(context: Mapping[str, Any]) -> bool:
    dims = context.get("dimensions") or []
    return isinstance(dims, list) and len(dims) == 0


def _document_date_value(fact: Mapping[str, Any]) -> str | None:
    """One ISO date from a dei date fact: its ISO value, else one printed date."""
    for value in (fact.get("normalized_value"), fact.get("raw_value")):
        if value is None:
            continue
        try:
            return date.fromisoformat(str(value).strip()).isoformat()
        except ValueError:
            continue
    dates = set(_iso_dates_from_text(str(fact.get("raw_value") or "")))
    return dates.pop() if len(dates) == 1 else None


def _document_period_end(
    facts: list[Mapping[str, Any]], contexts: Mapping[str, Mapping[str, Any]]
) -> str | None:
    """The filing's DocumentPeriodEndDate when its undimensioned facts agree.

    Only nonnumeric dei DocumentPeriodEndDate facts in undimensioned contexts
    count. Two distinct dates, or any value that is not one readable date,
    return None.
    """
    values: set[str | None] = set()
    for fact in facts:
        qname = str(fact.get("concept_qname") or "")
        if not qname.startswith("{http://xbrl.sec.gov/dei/"):
            continue
        if not qname.endswith("}DocumentPeriodEndDate") or fact.get("kind") != "nonnumeric":
            continue
        context = contexts.get(str(fact.get("context_ref") or ""))
        if context is None or not _undimensioned(context):
            continue
        values.add(_document_date_value(fact))
    return values.pop() if len(values) == 1 else None


def _context_dimension_sets(
    contexts: Mapping[str, Any],
) -> dict[str, frozenset[tuple[str, str]]]:
    """Each context id's dimension signature: its (axis, member) pairs, a
    typed dimension contributing its typed value, empty when undimensioned.
    A context whose dimensions are not a list of mappings is left out, so
    its facts carry no known signature."""
    signatures: dict[str, frozenset[tuple[str, str]]] = {}
    for context_id, context in contexts.items():
        if not isinstance(context, Mapping):
            continue
        dims = context.get("dimensions") or []
        if not isinstance(dims, list) or not all(isinstance(dim, Mapping) for dim in dims):
            continue
        signatures[context_id] = frozenset(
            (
                str(dim.get("dimension_qname")),
                str(
                    dim.get("member_qname")
                    if dim.get("member_qname") is not None
                    else dim.get("typed_value_xml")
                ),
            )
            for dim in dims
        )
    return signatures


def _unit_label(units: Mapping[str, Any], unit_ref: str | None) -> str | None:
    if not unit_ref or unit_ref not in units:
        return None
    unit = units[unit_ref]
    nums = [m.rsplit("}", 1)[-1] for m in unit.get("numerator_measures") or []]
    dens = [m.rsplit("}", 1)[-1] for m in unit.get("denominator_measures") or []]
    if nums and dens:
        return f"{nums[0]}/{'*'.join(dens)}"
    if nums:
        return nums[0]
    return unit_ref


def _period_key(context: Mapping[str, Any]) -> tuple[str, str | None, str | None]:
    period = context.get("period") or {}
    kind = str(period.get("kind") or "")
    if kind == "instant":
        return ("instant", None, period.get("instant_date"))
    return ("duration", period.get("start_date"), period.get("end_date"))


def _period_for_displayed_column(
    *,
    index: int,
    iso: str,
    prefer_kind: str,
    displayed_rows: list[dict[str, Any]],
    facts_by_id: Mapping[str, dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
    require_start: str | None = None,
) -> dict[str, Any] | None:
    """Bind one displayed column from same-column facts of the preferred period kind."""
    for spec in displayed_rows:
        value_facts = spec.get("value_facts") or []
        if index >= len(value_facts):
            continue
        html_fact = value_facts[index]
        parsed = facts_by_id.get(str(html_fact.get("fact_id") or ""))
        context_ref = (parsed or {}).get("context_ref") or html_fact.get("context_ref")
        context = contexts.get(str(context_ref or ""))
        if not context:
            continue
        period = context.get("period") or {}
        if period.get("kind") != prefer_kind:
            continue
        if prefer_kind == "instant" and period.get("instant_date") == iso:
            return period
        if prefer_kind == "duration" and period.get("end_date") == iso and period.get("start_date"):
            if require_start is not None and period.get("start_date") != require_start:
                continue
            return period
    return None


def _columns_from_display(
    *,
    statement_type: str,
    iso_dates: list[str],
    displayed_rows: list[dict[str, Any]],
    facts_by_id: Mapping[str, dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
    explicit_periods: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Columns are the dates printed on the captured table, bound to complete filing periods.

    ``explicit_periods`` (the grouped-duration composition) carries each
    column's own start and end from the display; every such column must still
    bind to a same-column filing context with exactly that period.
    """
    if explicit_periods is not None:
        if len(explicit_periods) < 2:
            raise StatementGraphError(
                "displayed statement columns are absent",
                refusal_code="displayed_columns_absent",
            )
        columns: list[dict[str, Any]] = []
        seen: set[tuple[str, str | None, str]] = set()
        for index, spec in enumerate(explicit_periods):
            iso = str(spec["end"])
            start = str(spec["start"])
            period = _period_for_displayed_column(
                index=index,
                iso=iso,
                prefer_kind="duration",
                displayed_rows=displayed_rows,
                facts_by_id=facts_by_id,
                contexts=contexts,
                require_start=start,
            )
            if period is None or period.get("start_date") != start:
                raise StatementGraphError(
                    "displayed duration column is not bound to the filing period",
                    refusal_code="displayed_column_period_unbound",
                )
            identity: tuple[str, str | None, str] = ("duration", start, iso)
            if identity in seen:
                raise StatementGraphError(
                    "displayed statement columns collapse distinct filing periods",
                    refusal_code="displayed_column_period_unbound",
                )
            seen.add(identity)
            columns.append({"kind": "duration", "start": start, "end": iso, "label": iso})
        return columns
    if len(iso_dates) < 2:
        raise StatementGraphError(
            "displayed statement columns are absent",
            refusal_code="displayed_columns_absent",
        )
    prefer_kind = "instant" if statement_type == "balance_sheet" else "duration"
    columns: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str]] = set()
    for index, iso in enumerate(iso_dates):
        period = _period_for_displayed_column(
            index=index,
            iso=iso,
            prefer_kind=prefer_kind,
            displayed_rows=displayed_rows,
            facts_by_id=facts_by_id,
            contexts=contexts,
        )
        if prefer_kind == "instant":
            if not period:
                raise StatementGraphError(
                    "displayed balance-sheet column is not bound to the filing date",
                    refusal_code="displayed_column_period_unbound",
                )
            identity: tuple[str, str | None, str] = ("instant", None, iso)
            columns.append({"kind": "instant", "start": None, "end": iso, "label": iso})
        else:
            if not period:
                raise StatementGraphError(
                    "displayed duration column is not bound to the filing period",
                    refusal_code="displayed_column_period_unbound",
                )
            start = str(period.get("start_date"))
            identity = ("duration", start, iso)
            columns.append({"kind": "duration", "start": start, "end": iso, "label": iso})
        if identity in seen:
            raise StatementGraphError(
                "displayed statement columns collapse distinct filing periods",
                refusal_code="displayed_column_period_unbound",
            )
        seen.add(identity)
    return columns


def _period_label(period: Mapping[str, Any]) -> str:
    if str(period.get("kind") or "") == "instant":
        return f"instant {period.get('instant_date')}"
    return f"duration {period.get('start_date')}..{period.get('end_date')}"


def _column_label(column: Mapping[str, Any]) -> str:
    if str(column.get("kind") or "") == "instant":
        return f"instant {column.get('end')}"
    return f"duration {column.get('start')}..{column.get('end')}"


def _duration_days(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        return None


def _cell_period_disagreement(
    index: int,
    label: str,
    fact: Mapping[str, Any],
    period: Mapping[str, Any],
    column: Mapping[str, Any],
    detail: str,
) -> StatementGraphError:
    return StatementGraphError(
        f"{_R7_DISAGREEMENT} {index}: row {label!r} fact {fact.get('fact_id')} "
        f"context {_period_label(period)} vs column {_column_label(column)}: {detail}",
        refusal_code="displayed_cell_period_mismatch",
    )


# Cash-flow cash positions are tagged as instants: the balance at the column's
# end date, or at the day before its start (the canonical beginning-of-period
# instant). Those two instants agree with a duration column; none other does.
_R7_LENGTH_TOLERANCE_DAYS = 7


def _enforce_cell_period_agreement(
    *,
    columns: list[dict[str, Any]],
    displayed_rows: list[dict[str, Any]],
    facts_by_id: Mapping[str, dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
    exact_starts: bool,
    row_preferred_label_roles: list[str | None] | None = None,
) -> None:
    """R7: a displayed numeric cell never sits in a column its context contradicts.

    Every value cell with a resolvable inline-XBRL context must agree with its
    dated column: kind, end date, and — for grouped columns that print their
    own duration — the exact start; annual/quarterly columns bound without a
    printed start accept any context within 7 days of the column's own period
    length. A cell without a context (chrome, subtotals rendered without ix
    tags) is left as today. A contradiction refuses; a cell is never
    reassigned, reordered or dropped.
    """
    for row_index, spec in enumerate(displayed_rows):
        label = str(spec.get("label") or "")
        preferred_role = (
            row_preferred_label_roles[row_index]
            if row_preferred_label_roles is not None and row_index < len(row_preferred_label_roles)
            else None
        )
        for index, html_fact in enumerate(spec.get("value_facts") or []):
            if index >= len(columns):
                break
            column = columns[index]
            parsed = facts_by_id.get(str(html_fact.get("fact_id") or ""))
            if parsed is None:
                continue
            context = contexts.get(str(parsed.get("context_ref") or ""))
            if context is None:
                continue
            period = context.get("period") or {}
            kind = str(period.get("kind") or "")
            if str(column.get("kind") or "") == "instant":
                if kind != "instant":
                    raise _cell_period_disagreement(
                        index, label, parsed, period, column, "period kind disagrees"
                    )
                if period.get("instant_date") != column.get("end"):
                    raise _cell_period_disagreement(
                        index, label, parsed, period, column, "instant date is not the column end"
                    )
                continue
            if kind == "instant":
                start = column.get("start")
                day_before_start = None
                if start:
                    try:
                        day_before_start = (date.fromisoformat(str(start)) - timedelta(days=1)).isoformat()
                    except ValueError:
                        day_before_start = None
                instant_date = period.get("instant_date")
                column_end = column.get("end")
                # The anchor follows the row's presentation label role: a
                # (negated) periodStartLabel row anchors to the day before the
                # column start, every other row (periodEndLabel, any other
                # role or none) to the column end. R7 does not read labels; a
                # label can only choose among roles the filing declares, and
                # only when the row maps to its presentation unambiguously.
                if preferred_role in _PERIOD_START_ROLES:
                    if instant_date == day_before_start:
                        continue
                elif instant_date == column_end:
                    continue
                raise _cell_period_disagreement(
                    index,
                    label,
                    parsed,
                    period,
                    column,
                    "instant is not the row's period anchor",
                )
            if kind != "duration":
                continue
            if period.get("end_date") != column.get("end"):
                raise _cell_period_disagreement(
                    index, label, parsed, period, column, "duration end is not the column end"
                )
            if exact_starts:
                if period.get("start_date") != column.get("start"):
                    raise _cell_period_disagreement(
                        index, label, parsed, period, column, "duration start is not the grouped column start"
                    )
                continue
            length = _duration_days(
                str(period.get("start_date") or ""), str(period.get("end_date") or "")
            )
            column_length = _duration_days(
                str(column.get("start") or ""), str(column.get("end") or "")
            )
            if (
                length is None
                or column_length is None
                or abs(length - column_length) > _R7_LENGTH_TOLERANCE_DAYS
            ):
                raise _cell_period_disagreement(
                    index,
                    label,
                    parsed,
                    period,
                    column,
                    "duration length is outside the statement period semantics",
                )


def _values_agree(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return Decimal(left) == Decimal(right)
    except (InvalidOperation, ValueError):
        return False


def _cell_dimensions(context: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not context:
        return []
    out: list[dict[str, Any]] = []
    for dim in context.get("dimensions") or []:
        out.append(
            {
                "kind": dim.get("kind"),
                "dimension_qname": dim.get("dimension_qname"),
                "member_qname": dim.get("member_qname"),
            }
        )
    return out


def _duplicate_identity_occurrences(
    displayed: Mapping[str, Any], facts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """All occurrences sharing concept/context/unit. Agreement is not pre-filtered."""
    identity = (
        displayed.get("concept_qname"),
        displayed.get("context_ref"),
        displayed.get("unit_ref"),
    )
    siblings = [
        fact
        for fact in facts
        if (
            fact.get("concept_qname"),
            fact.get("context_ref"),
            fact.get("unit_ref"),
        )
        == identity
    ]
    siblings.sort(
        key=lambda fact: (
            (fact.get("source_span") or {}).get("start", 0),
            str(fact.get("fact_id") or ""),
        )
    )
    return siblings


def _presentation_occurrences(presentation: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_concept: dict[str, list[dict[str, Any]]] = {}
    for row in presentation:
        if _is_abstract_concept(row["concept"]):
            continue
        by_concept.setdefault(row["concept"], []).append(row)
    return by_concept


def _select_presentation_row(
    spec: Mapping[str, Any],
    occurrences: list[dict[str, Any]],
    ordinal: int = 0,
) -> dict[str, Any] | None:
    if not occurrences:
        return None
    if len(occurrences) == 1:
        return occurrences[0]
    label = str(spec.get("label") or "").strip().lower()
    if "beginning" in label:
        start = [row for row in occurrences if row.get("preferred_label_role") == LABEL_PERIOD_START]
        if start:
            return start[0]
    if "ending" in label:
        end = [row for row in occurrences if row.get("preferred_label_role") == LABEL_PERIOD_END]
        if end:
            return end[0]
    # A concept presented more than once (a cash flow's beginning and ending
    # cash) maps its k-th displayed row to its k-th presentation occurrence,
    # so the ending row carries the ending role rather than the first one.
    if ordinal < len(occurrences):
        return occurrences[ordinal]
    return occurrences[0]


def _row_explicit_dimensions(
    *,
    value_facts: list[Mapping[str, Any]],
    facts_by_id: Mapping[str, dict[str, Any]],
    contexts: Mapping[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    for item in value_facts:
        fact = facts_by_id.get(str(item.get("fact_id") or ""))
        if fact is None:
            continue
        context = contexts.get(str(fact.get("context_ref") or ""))
        dims = _cell_dimensions(context)
        if dims:
            return dims
    return []


def _empty_cell(*, column: Mapping[str, Any], quality_state: str) -> dict[str, Any]:
    return {
        "period": dict(column),
        "value": None,
        "unit": None,
        "scale": None,
        "decimals": None,
        "dimensions": [],
        "direct_or_calculated": None,
        "quality_state": quality_state,
        "source_receipt": None,
    }


def _cell_from_facts(
    *,
    facts: list[dict[str, Any]],
    column: Mapping[str, Any],
    units: dict[str, Any],
    document_name: str,
    content_sha256: str,
    abstract: bool,
    contexts: Mapping[str, dict[str, Any]] | None = None,
    representative: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if abstract:
        return _empty_cell(column=column, quality_state="abstract")
    if not facts:
        return _empty_cell(column=column, quality_state="missing_fact")
    values = [f.get("normalized_value") for f in facts]
    comparable = [("" if v is None else str(v)) for v in values]
    if representative is None:
        representative = min(
            facts,
            key=lambda f: ((f.get("source_span") or {}).get("start", 0), str(f.get("fact_id") or "")),
        )
    disagree = any(
        not _values_agree(comparable[0], item) if comparable[0] != "" or item != "" else False
        for item in comparable[1:]
    )
    mixed_nil = any(bool(f.get("nil")) for f in facts) and not all(bool(f.get("nil")) for f in facts)
    mixed_presence = any(v is None for v in values) and any(v is not None for v in values)
    context = None
    if contexts is not None:
        context = contexts.get(str(representative.get("context_ref") or ""))
    dimensions = _cell_dimensions(context)
    if disagree or mixed_nil or mixed_presence:
        return {
            "period": dict(column),
            "value": None,
            "unit": None,
            "scale": None,
            "decimals": None,
            "dimensions": dimensions,
            "direct_or_calculated": None,
            "quality_state": "ambiguous",
            "source_receipt": {
                "document_name": document_name,
                "content_sha256": content_sha256,
                "occurrence_count": len(facts),
                "competing_fact_ids": sorted(str(f.get("fact_id")) for f in facts),
                "competing_values": comparable,
            },
        }
    if representative.get("nil") or representative.get("normalized_value") is None:
        cell = _empty_cell(column=column, quality_state="nil")
        cell["dimensions"] = dimensions
        cell["source_receipt"] = {
            "document_name": document_name,
            "content_sha256": content_sha256,
            "fact_id": representative.get("fact_id"),
            "concept_qname": representative.get("concept_qname"),
            "context_ref": representative.get("context_ref"),
            "unit_ref": representative.get("unit_ref"),
            "source_span": representative.get("source_span"),
            "occurrence_count": len(facts),
        }
        return cell
    span = representative.get("source_span")
    return {
        "period": dict(column),
        "value": representative.get("normalized_value"),
        "unit": _unit_label(units, representative.get("unit_ref")),
        "scale": representative.get("scale"),
        "decimals": representative.get("decimals"),
        "dimensions": dimensions,
        "direct_or_calculated": "direct",
        "quality_state": "available",
        "source_receipt": {
            "document_name": document_name,
            "content_sha256": content_sha256,
            "fact_id": representative.get("fact_id"),
            "concept_qname": representative.get("concept_qname"),
            "context_ref": representative.get("context_ref"),
            "unit_ref": representative.get("unit_ref"),
            "source_span": span,
            "occurrence_count": len(facts),
        },
    }


def map_standardized_metric(
    concept: str,
    registry: Any,
    *,
    dimensions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    local = _local_name(concept)
    prefix = concept.split(":", 1)[0] if ":" in concept else ""
    hits: list[str] = []
    contracts = getattr(registry, "contracts", None)
    if contracts is None:
        return {"metric_id": None, "mapping_state": "unmapped", "mapping_receipt": None}
    iterable = contracts.values() if isinstance(contracts, dict) else contracts
    for contract in iterable:
        for alias in getattr(contract, "taxonomy_concept_aliases", ()):
            if alias.concept == local and alias.taxonomy == prefix:
                hits.append(contract.metric_id)
    unique = sorted(set(hits))
    if len(unique) == 1:
        metric_id = unique[0]
        contract = None
        metric_lookup = getattr(registry, "metric", None)
        if callable(metric_lookup):
            try:
                contract = metric_lookup(metric_id)
            except KeyError:
                contract = None
        if contract is None:
            contract = next((item for item in iterable if getattr(item, "metric_id", None) == metric_id), None)
        profile = getattr(contract, "dimensional_profile", None) if contract is not None else None
        mode = getattr(profile, "mode", None)
        if mode == "consolidated_only" and dimensions:
            return {
                "metric_id": None,
                "mapping_state": "unmapped",
                "mapping_receipt": {
                    "taxonomy": prefix,
                    "concept": local,
                    "reason": "dimensional_profile",
                    "mode": mode,
                },
            }
        return {
            "metric_id": metric_id,
            "mapping_state": "mapped",
            "mapping_receipt": {
                "taxonomy": prefix,
                "concept": local,
                "metric_id": metric_id,
            },
        }
    if len(unique) > 1:
        return {
            "metric_id": None,
            "mapping_state": "ambiguous_mapping",
            "mapping_receipt": {"taxonomy": prefix, "concept": local, "metric_ids": unique},
        }
    return {"metric_id": None, "mapping_state": "unmapped", "mapping_receipt": None}


def _matched_alias_priority(taxonomy: str, concept: str, metric_id: str, registry: Any) -> int | None:
    contracts = getattr(registry, "contracts", None)
    if contracts is None:
        return None
    iterable = contracts.values() if isinstance(contracts, dict) else contracts
    priorities = [
        alias.priority
        for contract in iterable
        if getattr(contract, "metric_id", None) == metric_id
        for alias in getattr(contract, "taxonomy_concept_aliases", ())
        if alias.concept == concept and alias.taxonomy == taxonomy
    ]
    return min(priorities) if priorities else None


def _is_total_label(row: dict[str, Any]) -> bool:
    """Same total-line predicate ``_assign_display_depth`` keys on."""
    label = str(row.get("as_reported_label") or "").strip().lower()
    return label.startswith("total ")


def _recoverable_columns(demoted: dict[str, Any], governing: dict[str, Any]) -> list[str]:
    """Column keys a demoted row fills where the governing row holds null.

    Demotion is row-level, so a value only the loser carries would otherwise
    lose its standardized binding with no receipt letting a consumer find it
    again. Keys are the cell's period label (falling back to the period end).
    """
    keys: list[str] = []
    for demoted_cell, governing_cell in zip(
        demoted.get("cells") or (), governing.get("cells") or ()
    ):
        if demoted_cell.get("value") is None or governing_cell.get("value") is not None:
            continue
        period = demoted_cell.get("period") or {}
        keys.append(str(period.get("label") or period.get("end") or period))
    return keys


def _apply_alias_priority(rows: list[dict[str, Any]], registry: Any) -> None:
    """Keep one governed alias per standardized metric within a statement.

    The kernel resolves a metric through its alias with the lowest priority
    number. A statement can present two concepts that alias the same metric
    (``Assets`` at priority 10 and its ``LiabilitiesAndStockholdersEquity``
    alias at 20 both map to ``total_assets``). Only the rows matched at the
    lowest priority keep the standardized mapping; every lower-priority row
    becomes ``unmapped`` with an ``alias_priority`` receipt that names the
    governing concept. Rows tied at one priority are left unchanged.

    A ``total_*`` metric whose contenders disagree on wearing a ``Total ...``
    label first restricts the contest to the rows that do — a statement total
    must not land on a component line — and marks those receipts with
    ``reason_detail``. A demoted row that alone fills columns the governing
    row leaves null lists them under ``recoverable_columns``.
    """
    by_metric: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for row in rows:
        metric_id = row.get("standardized_metric_id")
        receipt = row.get("mapping_receipt")
        if row.get("mapping_state") != "mapped" or not metric_id or not isinstance(receipt, dict):
            continue
        priority = _matched_alias_priority(receipt["taxonomy"], receipt["concept"], metric_id, registry)
        if priority is not None:
            by_metric.setdefault(metric_id, []).append((priority, row))
    for metric_id, entries in by_metric.items():
        contest = entries
        label_preferred = False
        if metric_id.startswith("total_"):
            preferred = [entry for entry in entries if _is_total_label(entry[1])]
            if preferred and len(preferred) < len(entries):
                contest = preferred
                label_preferred = True
        best = min(priority for priority, _row in contest)
        kept = [row for priority, row in contest if priority == best]
        governing = kept[0]
        for priority, row in entries:
            if any(row is keeper for keeper in kept):
                continue
            receipt = row["mapping_receipt"]
            demotion = {
                "taxonomy": receipt["taxonomy"],
                "concept": receipt["concept"],
                "reason": "alias_priority",
                "metric_id": metric_id,
                "priority": priority,
                "governing_concept": governing["mapping_receipt"]["concept"],
                "governing_priority": best,
            }
            if label_preferred:
                demotion["reason_detail"] = "total_label_preferred"
            recoverable = _recoverable_columns(row, governing)
            if recoverable:
                demotion["recoverable_columns"] = recoverable
            row["standardized_metric_id"] = None
            row["mapping_state"] = "unmapped"
            row["mapping_receipt"] = demotion


def _assign_display_depth(rows: list[dict[str, Any]]) -> None:
    open_header = False
    for row in rows:
        if row["abstract"]:
            row["depth"] = 0
            open_header = True
            continue
        label = row["as_reported_label"].strip().lower()
        if open_header and not label.startswith("total "):
            row["depth"] = 1
        else:
            row["depth"] = 0
            if label.startswith("total "):
                open_header = False


def _prefixed_from_html_name(name: str | None) -> str:
    if not name:
        return ""
    return name.replace("_", ":", 1) if ":" not in name and "_" in name else name


def reconstruct_statement(
    *,
    statement_type: str,
    package: GoldenFilingPackage,
    parsed_instance: Mapping[str, Any],
    registry: Any,
) -> dict[str, Any]:
    role_uri, title, title_search = _statement_identity(package, statement_type)
    if (
        re.match(r"^\d+ - Disclosure - ", title)
        or "parent company" in title.casefold()
        or "parentcompany" in role_uri.casefold()
    ):
        raise StatementGraphError(
            f"statement role is not the consolidated statement: {title}",
            refusal_code="statement_role_not_consolidated",
        )
    pre = _stored_member(package, "presentation")
    lab = _stored_member(package, "label")
    cal = _stored_member(package, "calculation")
    presentation = parse_presentation_tree(pre, role_uri=role_uri)
    by_concept = _presentation_occurrences(presentation)
    parse_labels(lab)
    calcs = parse_calculations(cal).get(role_uri) or {}
    facts = list(parsed_instance.get("facts") or [])
    facts_by_id = {str(f.get("fact_id")): f for f in facts if f.get("fact_id")}
    contexts = {c["context_id"]: c for c in parsed_instance.get("contexts") or []}
    units = {u["unit_id"]: u for u in parsed_instance.get("units") or []}
    primary = package.manifest["primary_document"]
    primary_sha = next(
        item["content_sha256"]
        for item in package.manifest["members"]
        if item.get("name") == primary and item.get("state") == "stored"
    )
    html = package.members[primary].decode("utf-8")
    displayed = parse_displayed_primary_table(
        html,
        title=title_search,
        context_dimensions=_context_dimension_sets(contexts),
        period_end=_document_period_end(facts, contexts),
    )
    table_facts: list[dict[str, Any]] = []
    for spec in displayed["rows"]:
        for item in spec["value_facts"]:
            fact = facts_by_id.get(str(item.get("fact_id") or ""))
            if fact is None:
                raise StatementGraphError("displayed statement fact is missing from the iXBRL parse")
            table_facts.append(fact)
    if not table_facts:
        raise StatementGraphError(f"displayed statement has no numeric rows: {title}")
    columns = _columns_from_display(
        statement_type=statement_type,
        iso_dates=displayed["columns_iso"],
        displayed_rows=displayed["rows"],
        facts_by_id=facts_by_id,
        contexts=contexts,
        explicit_periods=displayed.get("columns_periods"),
    )
    row_presentation: list[dict[str, Any] | None] = []
    row_preferred_label_roles: list[str | None] = []
    row_concepts: list[str] = []
    for spec in displayed["rows"]:
        value_facts = spec["value_facts"]
        concept = ""
        if value_facts:
            names = sorted({_prefixed_from_html_name(item.get("name")) for item in value_facts})
            concept = names[0]
        row_concepts.append(concept)
    displayed_counts: dict[str, int] = {}
    for concept in row_concepts:
        displayed_counts[concept] = displayed_counts.get(concept, 0) + 1
    concept_seen: dict[str, int] = {}
    for spec, concept in zip(displayed["rows"], row_concepts, strict=True):
        ordinal = concept_seen.get(concept, 0)
        concept_seen[concept] = ordinal + 1
        occurrences = by_concept.get(concept) or []
        presentation_row = _select_presentation_row(spec, occurrences, ordinal)
        row_presentation.append(presentation_row)
    selected_occurrences: dict[str, list[int]] = {}
    for concept, presentation_row in zip(row_concepts, row_presentation, strict=True):
        if presentation_row is not None:
            selected_occurrences.setdefault(concept, []).append(id(presentation_row))
    for concept, presentation_row in zip(row_concepts, row_presentation, strict=True):
        role = presentation_row.get("preferred_label_role") if presentation_row else None
        # R7 trusts a row's period role only when the concept is displayed
        # exactly as many times as it is presented and each displayed row
        # selects a different occurrence. An extra or missing displayed row
        # has no defined occurrence, and two rows selecting the same one
        # cannot both carry its role, so they anchor at the column end like
        # role-less rows.
        occurrences = by_concept.get(concept) or []
        selected = selected_occurrences.get(concept, [])
        if displayed_counts[concept] != len(occurrences) or len(set(selected)) != len(selected):
            role = None
        row_preferred_label_roles.append(role)
    _enforce_cell_period_agreement(
        columns=columns,
        displayed_rows=displayed["rows"],
        facts_by_id=facts_by_id,
        contexts=contexts,
        exact_starts=displayed.get("columns_periods") is not None,
        row_preferred_label_roles=row_preferred_label_roles,
    )
    out_rows: list[dict[str, Any]] = []
    for spec, presentation_row in zip(displayed["rows"], row_presentation, strict=True):
        value_facts = spec["value_facts"]
        concept = ""
        if value_facts:
            names = sorted({_prefixed_from_html_name(item.get("name")) for item in value_facts})
            concept = names[0]
        preferred = presentation_row.get("preferred_label_role") if presentation_row else None
        path = list(presentation_row["presentation_path"]) if presentation_row else ([concept] if concept else [spec["label"]])
        first_fact = facts_by_id.get(str(value_facts[0].get("fact_id") or "")) if value_facts else None
        first_context = contexts.get(str(first_fact.get("context_ref") or "")) if first_fact else None
        dimensions = _cell_dimensions(first_context)
        if dimensions:
            member = dimensions[0].get("member_qname")
            if member and member not in path:
                path = path + [str(member)]
        mapping_dimensions = _row_explicit_dimensions(
            value_facts=value_facts,
            facts_by_id=facts_by_id,
            contexts=contexts,
        )
        mapping = map_standardized_metric(
            concept,
            registry,
            dimensions=mapping_dimensions,
        ) if concept else {
            "metric_id": None,
            "mapping_state": "unmapped",
            "mapping_receipt": None,
        }
        children = calcs.get(concept) if concept and not dimensions else None
        formula = None
        if children:
            formula = [{"concept": child, "weight": weight} for child, weight in children]
        cells = []
        for index, column in enumerate(columns):
            html_fact = value_facts[index] if index < len(value_facts) else None
            parsed_fact = facts_by_id.get(str(html_fact.get("fact_id") or "")) if html_fact else None
            selected = _duplicate_identity_occurrences(parsed_fact, facts) if parsed_fact else []
            cell = _cell_from_facts(
                facts=selected,
                column=column,
                units=units,
                document_name=primary,
                content_sha256=primary_sha,
                abstract=spec["abstract"],
                contexts=contexts,
                representative=parsed_fact,
            )
            cells.append(cell)
        out_rows.append(
            {
                "order": len(out_rows),
                "depth": 0,
                "concept": concept or None,
                "abstract": spec["abstract"],
                "as_reported_label": spec["label"],
                "preferred_label_role": preferred,
                "label_role_used": "filing_display",
                "presentation_path": path,
                "standardized_metric_id": mapping["metric_id"],
                "mapping_state": mapping["mapping_state"],
                "mapping_receipt": mapping["mapping_receipt"],
                "formula_dependencies": formula,
                "cells": cells,
            }
        )
    _apply_alias_priority(out_rows, registry)
    _assign_display_depth(out_rows)
    return {
        "statement_type": statement_type,
        "role_uri": role_uri,
        "title": title,
        "columns": columns,
        "row_count": len(out_rows),
        "rows": out_rows,
    }


def reconstruct_primary_statements(
    *,
    package: GoldenFilingPackage,
    registry: Any,
) -> dict[str, Any]:
    primary = package.manifest["primary_document"]
    parsed = parse_sec_filing_document(package.members[primary], document_name=primary)
    entity_ids = []
    for context in parsed.get("contexts") or []:
        ident = ((context.get("entity") or {}).get("identifier"))
        if ident:
            entity_ids.append(str(ident))
    unique_entities = sorted(set(entity_ids))
    if unique_entities != [package.manifest["cik"]]:
        raise StatementGraphError("XBRL entity identifier is not the package manifest CIK")
    statements: list[dict[str, Any]] = []
    for kind in ("income_statement", "balance_sheet", "cash_flow"):
        try:
            statements.append(
                reconstruct_statement(
                    statement_type=kind,
                    package=package,
                    parsed_instance=parsed,
                    registry=registry,
                )
            )
        except StatementGraphError as exc:
            if exc.refusal_code in STATEMENT_REFUSAL_CODES:
                role_uri = title = None
                if exc.refusal_code != "statement_role_not_consolidated":
                    role_uri, title, _ = _statement_identity(package, kind)
                statements.append(
                    {
                        "statement_type": kind,
                        "role_uri": role_uri,
                        "title": title,
                        "columns": [],
                        "row_count": 0,
                        "rows": [],
                        "refusal": {"code": exc.refusal_code},
                    }
                )
            else:
                raise
    return {
        "parsed_document_kind": (parsed.get("document") or {}).get("kind"),
        "fact_count": len(parsed.get("facts") or []),
        "context_count": len(parsed.get("contexts") or []),
        "statements": statements,
    }


__all__ = [
    "GOLDEN_AAPL_FIXTURES",
    "GoldenFilingPackage",
    "LABEL_PERIOD_END",
    "LABEL_PERIOD_START",
    "PRIMARY_STATEMENT_ROLES",
    "STATEMENT_REFUSAL_CODES",
    "STATEMENT_TITLES",
    "StatementGraphError",
    "admit_golden_aapl_package",
    "concept_from_href",
    "fact_matches_concept",
    "load_golden_aapl_package",
    "mint_fixture_recorded_at",
    "parse_calculations",
    "parse_displayed_primary_table",
    "parse_labels",
    "parse_presentation_tree",
    "map_standardized_metric",
    "reconstruct_primary_statements",
    "reconstruct_statement",
]

