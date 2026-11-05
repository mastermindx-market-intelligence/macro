# GMI balanced diagnostic strata design — 2026-10-19 (lane 7d)

Research artifacts only. Nothing here is admitted to the graph; nothing here writes `data/`. The design judgments below are frozen by the GMI orchestrator (2026-10-19 packet); this file transcribes them faithfully and computes every count from the installed security master and from `cases.jsonl` by script. It is a diagnostic casebook: it is not precision qualification, recall, coverage proof, or the 120-issuer collection.

## 1. The 120-issuer diagnostic: designed 2026-10-08, NEVER COLLECTED

The 120-issuer diagnostic was designed on 2026-10-08 and **never collected**. No issuer cohort was frozen, no vendor output was consumed, and no collection ran. Evidence:

- `research/theme_graph/economic_network_20261008/RESEARCH_FINDINGS.md` line 101: "The diagnostic design contains 120 issuers across five listing strata, with 30 difficult cases independently adjudicated. It is specified and costed as a future reference-set exercise; **it was not collected in this commission.**"
- `research/theme_graph/economic_network_execution_20261009/continuation_pro_003/source_diagnostic_frame_v1/WP02_SAMPLING_FRAME_ASSESSMENT.md` line 3 — disposition **`NOT_READY — NO_120_ISSUER_SELECTION`**: "The accepted diagnostic cannot be instantiated from the inspected current repository inputs without inventing issuer resolution, primary-listing assignments, valuation vintage or selection policy. No issuer cohort was frozen; no relationship-vendor output was consumed."
- `research/theme_graph/economic_network_20261008/INDEPENDENT_REVIEW.md` line 104: the design's arithmetic is internally consistent (5×24=120; six sector groups × 4 per geography; INT 8 UK + 8 Japan + 8 EU = 24; difficult cases 5×6=30) and "It is explicitly diagnostic, not globally representative."
- `INDEPENDENT_REVIEW.md` line 211: "Human-reviewed initial cases are separated from automatic-admission qualification. The 120-issuer diagnostic is not treated as per-stratum precision proof or global recall." Line 236 (finding R4): "The 120-issuer diagnostic is not precision qualification."
- `research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md` §7 (line 182): the diagnostic "remains a useful initial study. It is not sufficient by itself to prove automatic admission or market-wide coverage. Add source-language, sector, disclosure-quality and relationship-type strata; retain hard negatives."

### Planned design (frozen as designed 2026-10-08; sourcing §6, line 132)

- 5 primary-listing strata × 24 issuers = 120: `US`, `CN_MAINLAND`, `HK`, `CA`, `INT`. `INT` is 8 UK + 8 JP + 8 EU issuers.
- Per stratum, 6 sector groups × 4 issuers (2 large, 1 mid, 1 small under an explicitly frozen market-cap date and thresholds — still null per WP02). Sector groups: `semiconductor_cloud`, `industrials`, `consumer`, `energy_materials`, `financials`, `healthcare`.
- 30 difficult cases, 6 per stratum (sourcing §6 stress labels).
- Cross-listed issuers get one primary stratum plus a `cross_listed` flag.
- Diagnostic only. It never qualifies precision, recall or automatic admission (INDEPENDENT_REVIEW lines 104/211/236; sourcing §6 line 150).

## 2. Table A — planned matrix (planned / frozen), 5 listing rows × 6 sector columns

Every cell below is **planned 4 / frozen 0**: the design planned 4 issuers per cell and the 2026-10-08 commission froze (collected) zero of them. No cohort exists; nothing was sampled; WP02 confirms no selection.

| Listing stratum | semiconductor_cloud | industrials | consumer | energy_materials | financials | healthcare |
|---|---|---|---|---|---|---|
| US | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 |
| CN_MAINLAND | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 |
| HK | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 |
| CA | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 |
| INT | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 | planned 4 / frozen 0 |

Column totals: 20 planned / 0 frozen per sector group; 120 planned / 0 frozen overall.

## 3. Table B — fillability per listing stratum from INSTALLED LAWFUL PRIMARY SOURCES

All counts recomputed on 2026-10-19 from `origin/main:data/reference/security_master.parquet` (blob `452fe313fa8d1904539128edbc8fb2fdd7d861d1`, identical at the pinned revision `0221d6e171751c15b24d9f0bea27056aeab2716c` and current `origin/main`). `git rev-parse origin/main:data/reference/security_master.parquet` → `452fe313fa8d1904539128edbc8fb2fdd7d861d1`. The master is a survivorship panel of currently mapped securities (3,105 rows); issuer/security denominators stay separate.

**Securities per country (recomputed):** US 1,939 · CN 1,019 · HK 147 · CA 0 · INT_UK 0 · INT_JP 0 · INT_EU 0. Total 3,105.

**`issuer_state` counts per country, counted in securities (recomputed):**

| Country | RESOLVED | NO_ISSUER_EVIDENCE | EVIDENCE_CONFLICT | DEFERRED_IDENTITY_EXCEPTION |
|---|---|---|---|---|
| US | 1,931 | 5 | 2 | 1 |
| CN | 0 | 1,019 | 0 | 0 |
| HK | 0 | 147 | 0 | 0 |
| CA | — no rows — | — no rows — | — no rows — | — no rows — |
| INT_UK / INT_JP / INT_EU | — no rows — | — no rows — | — no rows — | — no rows — |

**Fillability verdicts** (orchestrator reading, each number verified above; any difference would be reported as a GAP — none was found):

- **US: FILLABLE at issuer level.** 1,939 securities; 1,931 RESOLVED securities belonging to 1,927 distinct RESOLVED issuers (four dual-class issuers carry two US lines each: `ISS:US-XNAS-FOX`, `ISS:US-XNAS-GOOG`, `ISS:US-XNAS-NWS`, `ISS:US-XNYS-UAA`). The 8 non-RESOLVED US rows are 5 NO_ISSUER_EVIDENCE, 2 EVIDENCE_CONFLICT and 1 DEFERRED_IDENTITY_EXCEPTION (NYSE GOLD).
- **CN: security-level only; issuer cells UNFILLABLE today.** 1,019 securities, all NO_ISSUER_EVIDENCE; no issuer-evidence route is installed for mainland China.
- **HK: UNFILLABLE at issuer level.** 147 securities, all NO_ISSUER_EVIDENCE; HKEX scraping is banned, so no lawful issuer-evidence route exists.
- **CA: UNFILLABLE** as a primary-listing stratum — the TSX list route returned 403 and the master has 0 CA rows — **except Canadian issuers cross-listed in the US**, e.g. Cameco via NYSE CCJ (present: `SEC:US-XNYS-CCJ`, RESOLVED).
- **INT_UK / INT_JP / INT_EU: UNFILLABLE.** 0 rows; JPX requires permission and no UK/EU route is installed.

**Bans (permanent for this work):** no HKEX scraping; no paid reads; no new vendors. The route findings above (TSX 403, JPX permission, HKEX ban) are the orchestrator's installed-route reading recorded in the 2026-10-19 packet; every count attributed to the parquet was recomputed here from the blob above.

## 4. The §7 added strata (Table C) — COMPUTED from cases.jsonl by script

`GMI_PROGRAM_RECOVERY_2026-10-16.md` §7 (line 182) adds source-language, sector, disclosure-quality and relationship-type strata and retains hard negatives. The four cross-tabs below are computed from `cases.jsonl` (27 rows) by this script; a reader can re-run it:

```python
#!/usr/bin/env python3
"""Table C: listing x added-strata cross-tabs, computed from cases.jsonl."""
import json
import sys
from collections import Counter

cases_path = sys.argv[1] if len(sys.argv) > 1 else "cases.jsonl"
rows = [json.loads(line) for line in open(cases_path, encoding="utf-8") if line.strip()]
LISTINGS = ["US", "CN_MAINLAND", "HK", "CA", "INT_UK", "INT_JP", "INT_EU", "OTHER"]
AXES = ["source_language", "disclosure_quality", "relationship_type", "sector_group"]

print("=== Table C: listing x added strata (computed from cases.jsonl) ===")
for axis in AXES:
    counts = Counter((r["strata"]["listing"], r["strata"][axis]) for r in rows)
    values = sorted({v for _, v in counts})
    print(f"listing x {axis}:")
    for listing in LISTINGS:
        for v in values:
            n = counts.get((listing, v), 0)
            if n:
                print(f"  {listing:12s} x {v:18s} = {n}")
    zeros = [(l, v) for l in LISTINGS for v in values if (l, v) not in counts]
    print(f"  zero cells: {len(zeros)} -> " + "; ".join(f"{l} x {v}" for l, v in zeros))
```

Script output (2026-10-19; byte-for-byte the output of the script above, re-verified by extraction; the lane check script computes the same counts):

```text
=== Table C: listing x added strata (computed from cases.jsonl) ===
listing x source_language:
  US           x EN                 = 23
  CN_MAINLAND  x ZH                 = 2
  CA           x EN                 = 2
  zero cells: 13 -> US x ZH; CN_MAINLAND x EN; HK x EN; HK x ZH; CA x ZH; INT_UK x EN; INT_UK x ZH; INT_JP x EN; INT_JP x ZH; INT_EU x EN; INT_EU x ZH; OTHER x EN; OTHER x ZH
listing x disclosure_quality:
  US           x narrative_only     = 11
  US           x none               = 6
  US           x segment_reported   = 6
  CN_MAINLAND  x narrative_only     = 2
  CA           x narrative_only     = 2
  zero cells: 19 -> CN_MAINLAND x none; CN_MAINLAND x segment_reported; HK x narrative_only; HK x none; HK x segment_reported; CA x none; CA x segment_reported; INT_UK x narrative_only; INT_UK x none; INT_UK x segment_reported; INT_JP x narrative_only; INT_JP x none; INT_JP x segment_reported; INT_EU x narrative_only; INT_EU x none; INT_EU x segment_reported; OTHER x narrative_only; OTHER x none; OTHER x segment_reported
listing x relationship_type:
  US           x customer           = 5
  US           x not_applicable     = 11
  US           x planned            = 2
  US           x supplier           = 5
  CN_MAINLAND  x customer           = 2
  CA           x customer           = 1
  CA           x ownership          = 1
  zero cells: 33 -> US x ownership; CN_MAINLAND x not_applicable; CN_MAINLAND x ownership; CN_MAINLAND x planned; CN_MAINLAND x supplier; HK x customer; HK x not_applicable; HK x ownership; HK x planned; HK x supplier; CA x not_applicable; CA x planned; CA x supplier; INT_UK x customer; INT_UK x not_applicable; INT_UK x ownership; INT_UK x planned; INT_UK x supplier; INT_JP x customer; INT_JP x not_applicable; INT_JP x ownership; INT_JP x planned; INT_JP x supplier; INT_EU x customer; INT_EU x not_applicable; INT_EU x ownership; INT_EU x planned; INT_EU x supplier; OTHER x customer; OTHER x not_applicable; OTHER x ownership; OTHER x planned; OTHER x supplier
listing x sector_group:
  US           x consumer           = 4
  US           x energy_materials   = 2
  US           x healthcare         = 2
  US           x industrials        = 1
  US           x semiconductor_cloud = 14
  CN_MAINLAND  x industrials        = 2
  CA           x energy_materials   = 2
  zero cells: 33 -> CN_MAINLAND x consumer; CN_MAINLAND x energy_materials; CN_MAINLAND x healthcare; CN_MAINLAND x semiconductor_cloud; HK x consumer; HK x energy_materials; HK x healthcare; HK x industrials; HK x semiconductor_cloud; CA x consumer; CA x healthcare; CA x industrials; CA x semiconductor_cloud; INT_UK x consumer; INT_UK x energy_materials; INT_UK x healthcare; INT_UK x industrials; INT_UK x semiconductor_cloud; INT_JP x consumer; INT_JP x energy_materials; INT_JP x healthcare; INT_JP x industrials; INT_JP x semiconductor_cloud; INT_EU x consumer; INT_EU x energy_materials; INT_EU x healthcare; INT_EU x industrials; INT_EU x semiconductor_cloud; OTHER x consumer; OTHER x energy_materials; OTHER x healthcare; OTHER x industrials; OTHER x semiconductor_cloud
```

### Zero cells and why they are empty

Reasons used: **(a)** "no installed lawful primary source"; **(b)** "not exercised by the §8 case set"; **(c)** "bilingual: the only bilingual primary sources for the cases here (HKEX filings) are behind the HKEX scraping ban". The script enumerates a zero cell as (listing, value) where the value appears somewhere in the file but not at that listing. Two values appear **nowhere** and are therefore zero at every listing: `source_language=BILINGUAL` — (c); `sector_group=financials` — (b).

- **listing × source_language** — US×ZH: (b). CN_MAINLAND×EN: (b). HK×EN, HK×ZH: (a). CA×ZH: (b). INT_UK×{EN,ZH}, INT_JP×{EN,ZH}, INT_EU×{EN,ZH}: (a). OTHER×{EN,ZH}: (b). `BILINGUAL` at every listing: (c).
- **listing × disclosure_quality** — CN_MAINLAND×{none, segment_reported}: (b). HK×{narrative_only, none, segment_reported}: (a). CA×{none, segment_reported}: (b). INT_UK×{…}, INT_JP×{…}, INT_EU×{…}: (a). OTHER×{…}: (b).
- **listing × relationship_type** — US×ownership: (b). CN_MAINLAND×{not_applicable, ownership, planned, supplier}: (b). HK×{customer, not_applicable, ownership, planned, supplier}: (a). CA×{not_applicable, planned, supplier}: (b). INT_UK×{all five used values}, INT_JP×{…}, INT_EU×{…}: (a). OTHER×{…}: (b). (The `integration` strata value never appears — the two integration rows are typed `planned` at the strata level — so it is zero at every listing: (b).)
- **listing × sector_group** — CN_MAINLAND×{consumer, energy_materials, healthcare, semiconductor_cloud}: (b). HK×{all five used values}: (a). CA×{consumer, healthcare, industrials, semiconductor_cloud}: (b). INT_UK×{…}, INT_JP×{…}, INT_EU×{…}: (a). OTHER×{…}: (b). `financials` at every listing: (b).

Rows ≠ issuers ≠ episodes; no fires are reported anywhere in this file (ADJUDICATION_LOG.md carries the honest-N computation).

## 5. Case schema (frozen, verbatim)

Every line of `cases.jsonl` is one JSON object conforming to this schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "gmi.diagnostic_case/v1",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema","case_id","episode_id","title","origin","subject","counterparty","relation_type","lifecycle","magnitude","citations","strata","expected_behaviour","refusal_code","hard_negative","human_disposition","store_mutation"],
  "properties": {
    "schema": {"const": "gmi.diagnostic_case/v1"},
    "case_id": {"type": "string", "pattern": "^DX-[0-9]{2}$"},
    "episode_id": {"type": "string", "pattern": "^ep:[a-z0-9_-]+$"},
    "title": {"type": "string", "minLength": 1},
    "origin": {"enum": ["SECTION8", "CASEBOOK_20261008", "HARD_NEGATIVE_20261008", "HARD_NEGATIVE_20261019"]},
    "subject": {"$ref": "#/$defs/party"},
    "counterparty": {"oneOf": [{"type": "null"}, {"$ref": "#/$defs/party"}]},
    "relation_type": {"enum": ["customer", "supplier", "ownership", "integration", "activity_membership", "identity"]},
    "lifecycle": {"enum": ["current", "planned", "historical", "not_applicable"]},
    "magnitude": {"$ref": "#/$defs/magnitude"},
    "citations": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/citation"}},
    "strata": {"$ref": "#/$defs/strata"},
    "expected_behaviour": {"enum": ["ADMIT_PROPOSED", "REFUSE", "ANONYMOUS_RETAINED", "IDENTITY_SPLIT"]},
    "refusal_code": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^[A-Z][A-Z0-9_]+$"}]},
    "hard_negative": {"type": "boolean"},
    "human_disposition": {"$ref": "#/$defs/disposition"},
    "store_mutation": {"const": false}
  },
  "allOf": [
    {"if": {"properties": {"expected_behaviour": {"const": "REFUSE"}}},
     "then": {"properties": {"refusal_code": {"type": "string"}}},
     "else": {"properties": {"refusal_code": {"type": "null"}}}},
    {"if": {"properties": {"hard_negative": {"const": true}}},
     "then": {"properties": {"expected_behaviour": {"const": "REFUSE"}}}}
  ],
  "$defs": {
    "party": {
      "type": "object", "additionalProperties": false,
      "required": ["label", "anonymous", "issuer_id", "security_ids", "unresolved_reason"],
      "properties": {
        "label": {"type": "string", "minLength": 1},
        "anonymous": {"type": "boolean"},
        "issuer_id": {"type": "string", "pattern": "^(ISS:[A-Z0-9:._-]+|UNRESOLVED)$"},
        "security_ids": {"type": "array", "items": {"type": "string", "pattern": "^SEC:[A-Z0-9:._-]+$"}},
        "unresolved_reason": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^[A-Z][A-Z0-9_]+$"}]}
      },
      "allOf": [
        {"if": {"properties": {"issuer_id": {"const": "UNRESOLVED"}}},
         "then": {"properties": {"unresolved_reason": {"type": "string"}}},
         "else": {"properties": {"unresolved_reason": {"type": "null"}}}},
        {"if": {"properties": {"anonymous": {"const": true}}},
         "then": {"properties": {"issuer_id": {"const": "UNRESOLVED"}, "security_ids": {"maxItems": 0}, "unresolved_reason": {"const": "ANONYMOUS_BY_DISCLOSURE"}}}}
      ]
    },
    "magnitude": {
      "type": "object", "additionalProperties": false,
      "required": ["species", "value", "unit", "denominator", "applies_to", "state", "citation_index"],
      "properties": {
        "species": {"enum": ["share", "rank", "roster", "none"]},
        "value": {"oneOf": [{"type": "null"}, {"type": "number"}]},
        "unit": {"oneOf": [{"type": "null"}, {"type": "string"}]},
        "denominator": {"oneOf": [{"type": "null"}, {"type": "string"}]},
        "applies_to": {"enum": ["PAIR", "ROSTER", "SUBJECT_TOTAL", "NONE"]},
        "state": {"enum": ["KNOWN", "UNDISCLOSED", "NOT_APPLICABLE"]},
        "citation_index": {"type": "integer", "minimum": 0}
      },
      "allOf": [
        {"if": {"properties": {"species": {"const": "none"}}},
         "then": {"properties": {"value": {"type": "null"}, "unit": {"type": "null"}, "denominator": {"type": "null"}, "applies_to": {"const": "NONE"}, "state": {"enum": ["UNDISCLOSED", "NOT_APPLICABLE"]}}},
         "else": {"properties": {"value": {"type": "number"}, "unit": {"type": "string"}, "denominator": {"type": "string"}, "state": {"const": "KNOWN"}}}}
      ]
    },
    "citation": {
      "type": "object", "additionalProperties": false,
      "required": ["source", "url_or_path", "period", "locator", "language"],
      "properties": {
        "source": {"type": "string", "minLength": 1},
        "url_or_path": {"type": "string", "minLength": 1},
        "period": {"type": "string", "minLength": 1},
        "locator": {"type": "string", "minLength": 1},
        "language": {"enum": ["EN", "ZH", "BILINGUAL"]}
      }
    },
    "strata": {
      "type": "object", "additionalProperties": false,
      "required": ["listing", "cross_listed", "sector_group", "source_language", "disclosure_quality", "relationship_type"],
      "properties": {
        "listing": {"enum": ["US", "CN_MAINLAND", "HK", "CA", "INT_UK", "INT_JP", "INT_EU", "OTHER"]},
        "cross_listed": {"type": "boolean"},
        "sector_group": {"enum": ["semiconductor_cloud", "industrials", "consumer", "energy_materials", "financials", "healthcare"]},
        "source_language": {"enum": ["EN", "ZH", "BILINGUAL"]},
        "disclosure_quality": {"enum": ["segment_reported", "narrative_only", "none"]},
        "relationship_type": {"enum": ["customer", "supplier", "ownership", "integration", "planned", "not_applicable"]}
      }
    },
    "disposition": {
      "type": "object", "additionalProperties": false,
      "required": ["status", "decided_by", "decided_at", "note"],
      "properties": {
        "status": {"enum": ["HUMAN_RULED", "PRIOR_REVIEW_PENDING_HUMAN", "MODEL_PROPOSED_PENDING_HUMAN"]},
        "decided_by": {"type": "string", "minLength": 1},
        "decided_at": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}]},
        "note": {"type": "string"}
      }
    }
  }
}
```

### 5.1 Code-checked rules (R1–R5)

Run by the lane check script against `cases.jsonl`; each result is printed:

- **R1** — `magnitude.citation_index < len(citations)` for every row.
- **R2** — no duplicate `case_id` values.
- **R3** — no line contains `finviz`, `ltheme:`, `basket:`, `ths_concepts`, `china_ths`, or the word THS (regex `\bTHS\b`, case-sensitive). The ban may be *named* in docs; no such id is used as an activity label anywhere in `cases.jsonl`.
- **R4** — every party with `anonymous: true` sits on a row whose `expected_behaviour` is `ANONYMOUS_RETAINED` or `REFUSE`, and no anonymous party label names a company (checked against every resolved party label and its first token in the file).
- **R5** — every `ISS:` id in the file exists in `security_master.parquet.issuer_id`, and every `SEC:` id exists in `security_master.parquet.security_id` (parquet read via `git show origin/main:…`; this sparse tree has no `data/`).

## 6. What this file is not

This is a diagnostic casebook over 27 authored rows. It does not satisfy the 120-issuer design (Table A: all cells frozen 0), does not measure recall or coverage, and does not qualify precision for automatic admission (INDEPENDENT_REVIEW lines 104/211/236). See `ADJUDICATION_LOG.md` §"Who is missing from the panel" for the honest population gaps.
