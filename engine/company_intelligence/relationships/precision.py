"""M2 precision measurement of relationship observation rows: pure logic.

A deterministic, salt-keyed pipeline that turns committed observation rows into
a blind stratified sample of plain-English claims (plus deliberately-wrong
decoy claims), so an independent reviewer can measure whether the rows say what
the filings say.  The scorer turns the reviewer's verdicts into per-stratum
precision with Wilson intervals.  It measures the rows, never the companies:
nothing here scores, ranks, sizes, gates or predicts any issuer.

This module is pure: no file IO, no wall clock, no network import (the excerpt
verifier is injected by the caller so this file never drags ``replay``'s
network module in).  The CLI lives in ``scripts/relationship_m2_precision.py``.
"""
from __future__ import annotations

import hashlib

from engine.company_intelligence.relationships.package_v2 import SPECIES_ROLES

ITEM_SCHEMA_NAME = "gmi_rel_m2.precision_item/v1"
MANIFEST_SCHEMA_NAME = "gmi_rel_m2.precision_manifest/v1"
VERDICT_SCHEMA_NAME = "gmi_rel_m2.precision_verdict/v1"
REPORT_SCHEMA_NAME = "gmi_rel_m2.precision_report/v1"

#: Decoy claim kinds in assignment order; decoy i tries KINDS[i % 5] first.
KINDS = [
    "role_flip",
    "counterparty_swap",
    "magnitude_shift",
    "status_flip",
    "species_swap",
]

#: Wilson z for the 95% interval, pinned by the frozen spec.
WILSON_Z = 1.959963984540054

#: Shortest supporting quote a reviewer may cite (characters of excerpt text).
QUOTE_MIN_CHARS = 20

#: A reviewer is reliable when at least this many decoys were reviewed and at
#: most this share of them were accepted.
RELIABLE_MIN_DECOYS = 10
RELIABLE_MAX_ACCEPTANCE = 0.20

MAX_NOTE_CHARS = 400

# --- output contracts (JSON-Schema dicts) -------------------------------------

_ITEM_CLAIM = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "subject_name",
        "counterparty_name",
        "counterparty_unnamed",
        "species",
        "role",
        "relation_status",
        "magnitudes",
    ],
    "properties": {
        "subject_name": {"type": "string"},
        "counterparty_name": {"type": "string"},
        "counterparty_unnamed": {"type": "boolean"},
        "species": {"enum": sorted(SPECIES_ROLES)},
        "role": {"type": "string"},
        "relation_status": {"enum": ["asserted", "terminated", "denied"]},
        "magnitudes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "value",
                    "value_high",
                    "unit",
                    "precision",
                    "period_label",
                ],
                "properties": {
                    "kind": {
                        "enum": [
                            "seller_revenue_share",
                            "buyer_procurement_share",
                            "contract_value",
                            "purchase_commitment",
                        ]
                    },
                    "value": {"type": "number"},
                    "value_high": {"type": ["number", "null"]},
                    "unit": {"type": "string"},
                    "precision": {
                        "enum": ["exact", "lower_bound", "upper_bound", "range"]
                    },
                    "period_label": {"type": "string"},
                },
            },
        },
    },
}

ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "item_id", "claim_text", "claim", "excerpt"],
    "properties": {
        "schema": {"const": ITEM_SCHEMA_NAME},
        "item_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
        "claim_text": {"type": "string"},
        "claim": _ITEM_CLAIM,
        "excerpt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["accession", "form", "filed_at", "url", "text"],
            "properties": {
                "accession": {
                    "type": "string",
                    "pattern": "^\\d{10}-\\d{2}-\\d{6}$",
                },
                "form": {"type": "string"},
                "filed_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "url": {"type": "string"},
                "text": {"type": "string"},
            },
        },
    },
}

VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema",
        "item_id",
        "relationship",
        "direction",
        "counterparty",
        "status",
        "magnitude",
        "quote",
        "note",
        "reviewer",
    ],
    "properties": {
        "schema": {"const": VERDICT_SCHEMA_NAME},
        "item_id": {"type": "string"},
        "relationship": {"enum": ["supported", "not_supported", "unclear"]},
        "direction": {"enum": ["correct", "wrong", "unclear"]},
        "counterparty": {"enum": ["correct", "wrong", "unclear"]},
        "status": {"enum": ["correct", "wrong", "unclear"]},
        "magnitude": {"enum": ["correct", "wrong", "unclear", "n/a"]},
        "quote": {"type": ["string", "null"]},
        "note": {"type": "string", "maxLength": MAX_NOTE_CHARS},
        "reviewer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["agent", "lane_run_id"],
            "properties": {
                "agent": {"type": "string"},
                "lane_run_id": {"type": ["string", "null"]},
            },
        },
    },
}

MANIFEST_SCHEMA = {
    "type": "object",
    "required": [
        "schema",
        "seed",
        "salt_sha256",
        "n_target",
        "n_effective",
        "floor",
        "pack_size",
        "decoys_requested",
        "decoys_made",
        "items_total",
        "packs",
        "population_below_target",
        "population_total",
        "population_by_stratum",
        "allocation",
        "excluded",
        "counters",
        "inputs",
    ],
    "properties": {
        "schema": {"const": MANIFEST_SCHEMA_NAME},
        "seed": {"type": "string"},
        "salt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "n_target": {"type": "integer", "minimum": 0},
        "n_effective": {"type": "integer", "minimum": 0},
        "floor": {"type": "integer"},
        "pack_size": {"type": "integer", "minimum": 1},
        "decoys_requested": {"type": "integer", "minimum": 0},
        "decoys_made": {"type": "integer", "minimum": 0},
        "items_total": {"type": "integer", "minimum": 0},
        "packs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["pack", "items"],
                "properties": {
                    "pack": {"type": "string"},
                    "items": {"type": "integer", "minimum": 0},
                },
            },
        },
        "population_below_target": {"type": "boolean"},
        "population_total": {"type": "integer", "minimum": 0},
        "population_by_stratum": {"type": "object"},
        "allocation": {"type": "object"},
        "excluded": {
            "type": "object",
            "required": ["EXCERPT_MISSING", "EXCERPT_CORRUPT"],
            "properties": {
                "EXCERPT_MISSING": {"type": "array", "items": {"type": "string"}},
                "EXCERPT_CORRUPT": {"type": "array", "items": {"type": "string"}},
            },
        },
        "counters": {"type": "object"},
        "inputs": {"type": "object"},
    },
}

REPORT_SCHEMA = {
    "type": "object",
    "required": [
        "schema",
        "strata",
        "overall_unweighted",
        "overall_weighted",
        "field_errors",
        "decoys",
        "reviewer_reliable",
        "codes",
        "inputs",
    ],
    "properties": {
        "schema": {"const": REPORT_SCHEMA_NAME},
        "strata": {"type": "object"},
        "overall_unweighted": {"type": "object"},
        "overall_weighted": {"type": "object"},
        "field_errors": {
            "type": "object",
            "required": ["direction", "counterparty", "status", "magnitude"],
        },
        "decoys": {"type": "object"},
        "reviewer_reliable": {"type": "boolean"},
        "codes": {"type": "object"},
        "inputs": {"type": "object"},
    },
}

# --- the reviewer guide ---------------------------------------------------------

REVIEW_GUIDE = """HOW TO REVIEW THESE CLAIMS

You are holding a pack of plain-English claims, each shown next to one verbatim
filing excerpt. Some of the claims are deliberately wrong. Judge each item on
its own, using nothing but the excerpt printed with it.

Rules

- Judge every item ONLY from the excerpt.text field shown with it. Use no
  outside knowledge, no other items, and no web sources.
- Write exactly one verdict line per item_id. Never skip an item.
- "unclear" is an honest answer; a guess is not. Use it whenever the excerpt
  does not settle the field.

Fields

- relationship: "supported" when the excerpt states this kind of relationship
  between these two parties; "not_supported" when it does not; "unclear" when
  you cannot tell.
- direction: "correct" when who sells/buys, manufactures, licenses, distributes
  or depends is as the claim states; "wrong" when it is not; "unclear" when you
  cannot tell.
- counterparty: "correct" when the excerpt names this counterparty, or, when
  the claim writes "(not named in the filing)", describes an unnamed party
  matching the alias; "wrong" otherwise; "unclear" when you cannot tell.
- status: "correct" when ongoing vs ended vs denied is as the claim states;
  "wrong" otherwise; "unclear" when you cannot tell.
- magnitude: "correct" when every number and period in the claim matches the
  excerpt at the excerpt's own rounding; "wrong" when any of them does not;
  "unclear" when you cannot tell; "n/a" only when the claim states no number.
- quote: when relationship is "supported", the shortest exact passage, copied
  character for character from excerpt.text and at least 20 characters long,
  that supports the claim; otherwise null. A quote that is not a verbatim
  substring of excerpt.text, or that is shorter than 20 characters, is
  discarded and the item is scored as unclear.
- note: free text, at most 400 characters.

One example verdict line (one JSON object per line, one line per item_id):

{"schema": "gmi_rel_m2.precision_verdict/v1", "item_id": "0123456789abcdef", "relationship": "supported", "direction": "correct", "counterparty": "correct", "status": "correct", "magnitude": "correct", "quote": "the exact passage copied character for character from excerpt.text", "note": "", "reviewer": {"agent": "your-agent-name", "lane_run_id": "this-lane-run"}}

Write the lines to one or more .jsonl files in the verdicts directory; every
item_id in the pack needs exactly one line.
"""


# --- salt-keyed determinism -----------------------------------------------------


def key(salt: bytes, seed: str, x: str) -> str:
    """The one keyed hash: sha256(salt + 0x00 + seed + 0x00 + x), as hex.

    The salt never leaves the caller; only its sha256 is ever recorded.
    """
    digest = hashlib.sha256()
    digest.update(salt)
    digest.update(b"\x00")
    digest.update(seed.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(x.encode("utf-8"))
    return digest.hexdigest()


# --- Q5: claims ------------------------------------------------------------------


#: The exact base sentence per (species, role); {S} subject, {O} counterparty.
_BASE_SENTENCES = {
    ("supplier_customer", "supplier"): "{S} sells products or services to {O}.",
    ("supplier_customer", "customer"): "{S} buys products or services from {O}.",
    ("contract_manufacturing", "manufacturer"): "{S} manufactures products for {O}.",
    ("contract_manufacturing", "client"): "{O} manufactures products for {S}.",
    ("licensing", "licensor"): "{S} licenses technology or rights to {O}.",
    ("licensing", "licensee"): "{S} licenses technology or rights from {O}.",
    ("distribution", "manufacturer"): "{O} distributes {S}'s products.",
    ("distribution", "distributor"): "{S} distributes {O}'s products.",
    (
        "component_dependency",
        "provider",
    ): "{S} provides a component or input that {O} depends on.",
    (
        "component_dependency",
        "dependent",
    ): "{S} depends on a component or input from {O}.",
}

_STATUS_PREFIX = {
    "asserted": "",
    "terminated": "The filing says this has ENDED: ",
    "denied": "The filing says this is NOT the case: ",
}

_Q_WORD = {
    "exact": "",
    "lower_bound": "at least ",
    "upper_bound": "at most ",
    "range": "approximately ",  # range with a null value_high
}

_SHARE_KINDS = ("seller_revenue_share", "buyer_procurement_share")


def claim_from_row(row: dict) -> dict:
    """The Q5 claim object for one observation row.

    The effective role is ``subject_role`` or the species default.  A magnitude
    whose value is null states no number and is not carried; a row whose
    magnitudes are all null-valued gets ``magnitudes: []``.
    """
    species = row["species"]
    role = row.get("subject_role") or SPECIES_ROLES[species][2]
    object_party = row.get("object") or {}
    alias = object_party.get("anonymous_alias")
    magnitudes = []
    for magnitude in row.get("magnitudes") or []:
        if magnitude.get("value") is None:
            continue
        magnitudes.append(
            {
                "kind": magnitude["kind"],
                "value": magnitude["value"],
                "value_high": magnitude.get("value_high"),
                "unit": magnitude["unit"],
                "precision": magnitude["precision"],
                "period_label": magnitude["period"]["label"],
            }
        )
    return {
        "subject_name": row["subject"]["name_as_filed"],
        "counterparty_name": (
            alias if alias is not None else object_party.get("name_as_filed")
        ),
        "counterparty_unnamed": alias is not None,
        "species": species,
        "role": role,
        "relation_status": row["relation_status"],
        "magnitudes": magnitudes,
    }


def _amount(kind: str, unit: str, value) -> str:
    """One formatted amount: a percentage for ratio shares, otherwise the
    ``num unit`` form (``num = format(value, ',g')``) — the same formatting for
    both bounds of a range."""
    if kind in _SHARE_KINDS and unit == "ratio":
        return format(round(value * 100, 4), "g") + "%"
    return format(value, ",g") + " " + unit


def _magnitude_sentence(claim: dict, magnitude: dict, subject: str, other: str) -> str:
    kind = magnitude["kind"]
    unit = magnitude["unit"]
    value = magnitude["value"]
    value_high = magnitude.get("value_high")
    precision = magnitude["precision"]
    label = magnitude["period_label"]
    if precision == "range" and value_high is not None:
        q = "between "
        number = f"{_amount(kind, unit, value)} and {_amount(kind, unit, value_high)}"
    else:
        q = _Q_WORD[precision]
        number = _amount(kind, unit, value)
    if kind == "seller_revenue_share":
        return f"{other} accounted for {q}{number} of {subject}'s revenue in {label}."
    if kind == "buyer_procurement_share":
        return (
            f"{other} accounted for {q}{number} of {subject}'s purchases in {label}."
        )
    if kind == "contract_value":
        return f"The contract value is {q}{number} ({label})."
    return f"The purchase commitment is {q}{number} ({label})."


def render_claim(claim: dict) -> str:
    """The one plain-English rendering of a claim object."""
    subject = claim["subject_name"]
    if claim.get("counterparty_unnamed"):
        other = f"{claim['counterparty_name']} (not named in the filing)"
    else:
        other = claim["counterparty_name"]
    base = (
        _BASE_SENTENCES[(claim["species"], claim["role"])]
        .replace("{S}", subject)
        .replace("{O}", other)
    )
    parts = [_STATUS_PREFIX[claim["relation_status"]] + base]
    for magnitude in claim["magnitudes"]:
        parts.append(_magnitude_sentence(claim, magnitude, subject, other))
    return " ".join(parts)


# --- Q3: allocation ---------------------------------------------------------------


def allocate(sizes: dict, n: int, floor: int) -> tuple[dict, bool]:
    """(alloc, population_below_target) over {stratum: size}.

    Floors first (``min(size, floor)`` per nonempty stratum); when their sum
    already reaches n the floors win.  Otherwise the remaining units are handed
    out in quota rounds — ``floor(R * size_s / T)`` capped by each stratum's
    remaining capacity, then this round's leftovers one at a time by largest
    fractional quota, ties by stratum name — until n is met or the population
    is exhausted (``population_below_target``).
    """
    strata = sorted(s for s, size in sizes.items() if size > 0)
    alloc = {s: min(sizes[s], floor) for s in strata}
    remaining = n - sum(alloc.values())
    while remaining > 0 and any(sizes[s] - alloc[s] > 0 for s in strata):
        eligible = [s for s in strata if sizes[s] - alloc[s] > 0]
        total = sum(sizes[s] for s in eligible)
        quota = {s: remaining * sizes[s] / total for s in eligible}
        given = {s: min(int(quota[s]), sizes[s] - alloc[s]) for s in eligible}
        left = remaining - sum(given.values())
        for s in sorted(eligible, key=lambda s: (-(quota[s] % 1), s)):
            if left <= 0:
                break
            take = min(sizes[s] - alloc[s] - given[s], left)
            given[s] += take
            left -= take
        for s in eligible:
            alloc[s] += given[s]
        if not any(given.values()):
            break  # defensive: no stratum could take a unit
        remaining = left
    return alloc, remaining > 0


# --- Q4: decoys --------------------------------------------------------------------


def decoy_kinds_in_order(index: int) -> list:
    """The cyclic try-order for decoy `index`: KINDS[index % 5] first."""
    return [KINDS[(index + offset) % len(KINDS)] for offset in range(len(KINDS))]


def shifted_value(value, unit: str):
    """The magnitude_shift transform: ratio values move +0.15 when <= 0.80 and
    -0.25 above; every other unit doubles."""
    if unit == "ratio":
        if value <= 0.80:
            return round(value + 0.15, 4)
        return round(value - 0.25, 4)
    return value * 2


def flip_status(status: str) -> str:
    """asserted -> terminated; terminated or denied -> asserted."""
    return "terminated" if status == "asserted" else "asserted"


def swapped_species_role(species: str, role: str) -> tuple:
    """(species, role) one step cyclically along sorted(SPECIES_ROLES), keeping
    the role position (from_role <-> index 0, to_role <-> index 1)."""
    ordered = sorted(SPECIES_ROLES)
    target = ordered[(ordered.index(species) + 1) % len(ordered)]
    positions = SPECIES_ROLES[species][:2]
    if role in positions:
        index = positions.index(role)
    else:  # defensive: an unknown effective role keeps the default position
        index = 0
    return target, SPECIES_ROLES[target][index]


def try_decoy(claim: dict, kind: str, swap_name: str | None):
    """The claim mutated by one decoy kind, or None when it does not apply."""
    if kind == "role_flip":
        roles = SPECIES_ROLES[claim["species"]][:2]
        other = roles[1] if claim["role"] == roles[0] else roles[0]
        return dict(claim, role=other)
    if kind == "counterparty_swap":
        if not swap_name:
            return None
        return dict(
            claim, counterparty_name=swap_name, counterparty_unnamed=False
        )
    if kind == "magnitude_shift":
        magnitudes = claim["magnitudes"]
        if not magnitudes:
            return None
        first = magnitudes[0]
        shifted = dict(first)
        shifted["value"] = shifted_value(first["value"], first["unit"])
        if first.get("value_high") is not None:
            shifted["value_high"] = shifted_value(
                first["value_high"], first["unit"]
            )
        return dict(claim, magnitudes=[shifted])
    if kind == "status_flip":
        return dict(claim, relation_status=flip_status(claim["relation_status"]))
    if kind == "species_swap":
        species, role = swapped_species_role(claim["species"], claim["role"])
        return dict(claim, species=species, role=role)
    return None


def first_applicable_decoy(claim: dict, index: int, swap_names, key_fn):
    """(kind, claim) for the first applicable kind of decoy `index`'s try-order.

    ``swap_names`` are the already-filtered counterparty candidates; they are
    ordered by ``key_fn('swap:' + name)`` here.  (None, None) when nothing
    applies.
    """
    for kind in decoy_kinds_in_order(index):
        if kind == "counterparty_swap":
            if not swap_names:
                continue
            ordered = sorted(swap_names, key=lambda name: key_fn("swap:" + name))
            mutated = try_decoy(claim, kind, ordered[0])
        else:
            mutated = try_decoy(claim, kind, None)
        if mutated is not None:
            return kind, mutated
    return None, None


def swap_candidates(names, text: str) -> list:
    """The candidate counterparty names whose casefolded form — and whose first
    word, when that word has at least 4 letters — is absent from the
    casefolded excerpt text."""
    cased = text.casefold()
    out = []
    for name in names:
        low = name.casefold()
        if low in cased:
            continue
        words = low.split()
        first = words[0] if words else ""
        if len(first) >= 4 and first in cased:
            continue
        out.append(name)
    return out


def swap_name_pool(population: list, entry: dict) -> list:
    """The distinct subject.name_as_filed values of other issuers in the
    population (issuers other than the entry's subject and object)."""
    row = entry["row"]
    excluded = {row["subject"]["issuer_id"]}
    object_party = row.get("object") or {}
    if object_party.get("issuer_id") is not None:
        excluded.add(object_party["issuer_id"])
    names = []
    seen = set()
    for other in population:
        candidate = other["row"]["subject"]
        if candidate["issuer_id"] in excluded:
            continue
        name = candidate["name_as_filed"]
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def build_decoys(population: list, selected_ids: set, d: int, key_fn) -> tuple:
    """(decoys, counters) from the unselected population.

    The pool is ordered fresh-span rows first (spans unused by any selected
    row), then the rest, each group by ``key_fn('decoy:' + observation_id)``.
    Decoy i tries ``KINDS[i % 5]`` and falls through cyclically; a row where
    nothing applies is counted under ``decoy_inapplicable`` and skipped.
    Each decoy entry is {observation_id, kind, claim}.
    """
    used = set()
    for entry in population:
        if entry["observation_id"] in selected_ids:
            source = entry["row"]["source_ref"]
            used.add((source["accession"], source["span_sha256"]))
    fresh, stale = [], []
    for entry in population:
        if entry["observation_id"] in selected_ids:
            continue
        source = entry["row"]["source_ref"]
        group = fresh if (source["accession"], source["span_sha256"]) not in used else stale
        group.append(entry)
    fresh.sort(key=lambda e: key_fn("decoy:" + e["observation_id"]))
    stale.sort(key=lambda e: key_fn("decoy:" + e["observation_id"]))
    decoys: list = []
    counters: dict = {}
    for entry in fresh + stale:
        if len(decoys) >= d:
            break
        claim = claim_from_row(entry["row"])
        text = entry["excerpt"]["span"]["normalized"]
        names = swap_candidates(swap_name_pool(population, entry), text)
        kind, mutated = first_applicable_decoy(claim, len(decoys), names, key_fn)
        if kind is None:
            counters["decoy_inapplicable"] = counters.get("decoy_inapplicable", 0) + 1
            continue
        decoys.append(
            {
                "observation_id": entry["observation_id"],
                "kind": kind,
                "claim": mutated,
            }
        )
    return decoys, counters


# --- Q1/Q3: population and selection ------------------------------------------------


def build_population(file_rows, excerpt_index, domain_of: dict, verify) -> tuple:
    """(population entries, excluded) over observation rows in visit order.

    ``file_rows`` is [(relpath, lineno, row)] for every observation-kind row in
    sorted-file, in-file order.  ``excerpt_index`` maps
    (accession, span.raw_sha256) -> (excerpt doc, relpath).  ``verify`` is the
    injected offline excerpt verifier (``replay.verify_excerpt``); a nonempty
    problem list marks the row EXCERPT_CORRUPT, an absent key EXCERPT_MISSING —
    both recorded, never dropped silently.
    """
    population: list = []
    excluded = {"EXCERPT_MISSING": [], "EXCERPT_CORRUPT": []}
    for relpath, lineno, row in file_rows:
        observation_id = row.get("observation_id") or f"{relpath}:{lineno}"
        source = row.get("source_ref") or {}
        held = excerpt_index.get(
            (source.get("accession"), source.get("span_sha256"))
        )
        if held is None:
            excluded["EXCERPT_MISSING"].append(observation_id)
            continue
        excerpt, excerpt_relpath = held
        if verify(excerpt):
            excluded["EXCERPT_CORRUPT"].append(observation_id)
            continue
        subject_iid = (row.get("subject") or {}).get("issuer_id")
        domain = domain_of.get(subject_iid, "UNMAPPED")
        population.append(
            {
                "observation_id": observation_id,
                "row": row,
                "stratum": f"{domain}|{row.get('species')}",
                "excerpt": excerpt,
                "excerpt_relpath": excerpt_relpath,
            }
        )
    return population, excluded


def select_sample(population: list, n: int, floor: int, key_fn) -> dict:
    """Allocation plus the per-stratum selection for one sample.

    Within a stratum the first ``alloc[s]`` rows in ``key_fn(observation_id)``
    order are taken.  Returns {selected, sizes, alloc, below_target}.
    """
    sizes: dict = {}
    for entry in population:
        sizes[entry["stratum"]] = sizes.get(entry["stratum"], 0) + 1
    alloc, below = allocate(sizes, n, floor)
    by_stratum: dict = {}
    for entry in population:
        by_stratum.setdefault(entry["stratum"], []).append(entry)
    selected: list = []
    for stratum in sorted(by_stratum):
        ordered = sorted(
            by_stratum[stratum],
            key=lambda e: key_fn(e["observation_id"]),
        )
        selected.extend(ordered[: alloc[stratum]])
    return {
        "selected": selected,
        "sizes": sizes,
        "alloc": alloc,
        "below_target": below,
    }


# --- Q9: scoring ---------------------------------------------------------------------


def wilson(accepted, reviewed, z: float = WILSON_Z):
    """The Wilson 95% interval rounded to 4 dp, or None with nothing reviewed."""
    if not reviewed:
        return None
    share = accepted / reviewed
    denominator = 1 + z * z / reviewed
    center = (share + z * z / (2 * reviewed)) / denominator
    half = (
        z
        * (
            share * (1 - share) / reviewed + z * z / (4 * reviewed * reviewed)
        ) ** 0.5
        / denominator
    )
    return [round(center - half, 4), round(center + half, 4)]


def quote_problem(verdict: dict, excerpt_text: str):
    """QUOTE_NOT_FOUND | QUOTE_MISSING for a verdict's quote, else None.

    A non-null quote must be a verbatim substring of the excerpt text of at
    least QUOTE_MIN_CHARS characters; a supported relationship needs a quote.
    """
    quote = verdict.get("quote")
    if quote is not None and (len(quote) < QUOTE_MIN_CHARS or quote not in excerpt_text):
        return "QUOTE_NOT_FOUND"
    if quote is None and verdict["relationship"] == "supported":
        return "QUOTE_MISSING"
    return None


def effective_relationship(verdict: dict, excerpt_text: str) -> str:
    """The verdict's relationship after the quote rules: a quote problem scores
    the item as unclear."""
    if quote_problem(verdict, excerpt_text) is not None:
        return "unclear"
    return verdict["relationship"]


def verdict_accepts(verdict: dict, excerpt_text: str, claim_magnitude_count: int) -> bool:
    """The one acceptance rule: relationship supported (after the quote rules),
    direction/counterparty/status correct, and magnitude correct — or n/a on a
    claim that states no number."""
    if effective_relationship(verdict, excerpt_text) != "supported":
        return False
    if (
        verdict["direction"] != "correct"
        or verdict["counterparty"] != "correct"
        or verdict["status"] != "correct"
    ):
        return False
    magnitude = verdict["magnitude"]
    if magnitude == "correct":
        return True
    return magnitude == "n/a" and claim_magnitude_count == 0
