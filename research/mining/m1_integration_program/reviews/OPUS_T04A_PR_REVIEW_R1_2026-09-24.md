# OPUS ADVERSARIAL REVIEW — PR #7950 (T04a) @ c76aea663a521b78f78d8a2058f4c64ed2f9d9c6
Reviewer: Opus, ROUTE: review / AUDIT, MODE: READ_ONLY. Date 2026-09-24.
Base: merge-base `7d843a4d1760fc82ac7524661396e7b994ddc617`; `origin/main` = `8a8ecbe868ff520607f3da2ec190231a1792049a`.

## VERDICT: REJECT (return to builder for repair)

3 BLOCKER, 6 MAJOR, 3 MINOR, 2 NIT. The suite is green (`37 passed in 1.63s`) and the module is
genuinely NOT a kernel copy — but the central deliverable of T04a, the per-sector composition of the
management point-estimate pair, is dead code that no case and no test reaches, one case composes a
block its own frozen casebook says must be absent, and the closed `limitations` vocabulary is not
closed. Green here measures the parts of the module the casebook happens to touch.

---

## FINDINGS

### BLOCKER-1 — `expectations` is dead code in all 11 cases; the copper one-pair rule is never surfaced
`engine/market_ontology/mining_theme_research.py:543-544`
```python
for packet in bundle.financial_packets:
    mev = packet.get("management_estimate_vs_actual")
```
The composition reads the estimate/actual pair off the **bundle's financial packets**, but the
casebook's packets are built from the fixture `economics` object only
(`tests/mining_casebook.py:76` `financial_packets=(dict(fixture["economics"]),)`), and every fixture's
`economics` carries just `measure/value/basis/positive_witness/stream_threshold`. No fixture has a
`management_estimate_vs_actual` key. The domain file's pair — including the ONE `pairs:` object at
`research/mining/m1_integration_program/domain/MINING_DOMAIN_DEFINITIONS_M1_2026-09-24.md:92-114` — is
never read: `MINING_DEFINITIONS` is consulted **exactly once** in the whole module, for the label
(`mining_theme_research.py:625` `domain_label = MINING_DEFINITIONS[query.slice_key]["anchor_theme_id"]`).
Observed (probe, all 11 cases): `expectations= 0` for every case.
Consequence: lines 539-616 (both the sales pair and the second `pairs` comparison), the
`is_range/is_consensus` hardcodes, and `_summarize_expectations` never execute against real input.
REVIEW STANDARD (3) — "the copper `pairs:` list is exactly one object and is surfaced as a second
comparison" — is **unmet**: it is surfaced zero times. The "closed definitions loaded at import"
claim in the module docstring (`:3-6`) is decorative: the file is parsed and validated, then one
string is taken from it.

### BLOCKER-2 — `same_horizon_revision` composes a signed native block the casebook says must be absent
`engine/market_ontology/mining_theme_research.py:446-450`
```python
_suppress_native_blocks = bool(
    {"missing_issuer", "stream_threshold_unknown", "source_only", "missing_basis",
     "changed_source", "denied_source"} & set(limitations))
```
`missing_derivation` (the `next_period_outlook` omission, `mining_dependency_binding.py:91`) is NOT in
that set. Observed:
```
composed blocks = [{'stable_subject_id':'subject:unknown','measure':'same-horizon guidance',
                    'value':990,'sign':'+','basis':'fictional management estimate','source_label':'source'}]
casebook expected signed_native_blocks = []
reported_only_economics[0].reason = "A same-horizon revision is not a next-period outlook."
```
A **management estimate** on a `fictional management estimate` basis is emitted inside
`economics.native_blocks` — the reported-economics channel — with status `ready`. That is the same
family of defect the domain file's `forbidden_derivations` forbid ("do not rename PPA income as
revenue", domain md:280): a non-reported figure presented in the reported channel. REVIEW STANDARD
(4)/(5) unmet — the module contradicts a frozen input it was commissioned to honor.

### BLOCKER-3 — `limitations` is not a closed vocabulary: any non-string passes
`contracts/market_ontology/mining_theme_research.v1.schema.json:222-237`
```json
"items": { "anyOf": [ {"enum": [...]},
  {"pattern": "^(definition_unqualified|assertion_invalid|omitted):[A-Za-z0-9_.-]+$"} ] }
```
The second branch has **no `"type": "string"`**. In JSON Schema, `pattern` applies only to strings and
is vacuously true for every other instance type, so the `anyOf` always succeeds for a non-string.
Observed: the validator ACCEPTED `limitations: [{"free":"text","number":12345}]` and
`limitations: [12345]`. REVIEW STANDARD (2) — "`limitations` items restricted to the closed
vocabulary, nothing open-ended" — unmet; free text carrying a number rides in a governed field.

### MAJOR-4 — point-estimate law is declared, never enforced by the contract
`contracts/.../mining_theme_research.v1.schema.json:158` required = `["stable_subject_id",
"comparison_kind","earlier_point_estimate","later_actual"]` — `is_range`, `is_consensus` and
`comparison` are **optional**; `:189-190` `"is_range": {"type":"boolean"}` / `"is_consensus":
{"type":"boolean"}` carry no `const: false`; `:163,:174` allow both legs `null`; `:184`
`"comparison": {"type":"string"}` has no `minLength`. Observed: the validator ACCEPTED
`{"stable_subject_id":"s","comparison_kind":"k","earlier_point_estimate":null,"later_actual":null,
"is_range":true,"is_consensus":true}` with no accompanying limitation. The module hardcodes `False`
(`:577-578`, `:613-614`) so the contract is the only guard, and it does not guard. Standard (3):
"`is_range: false` **enforced**, not just declared" — unmet; "all three present or the pair is absent
with a limitation" — unmet (a null leg emits no limitation, `:560-572`).

### MAJOR-5 — `_summarize_expectations` has an inverted guard; production never emits `definition_unqualified:*`
`engine/market_ontology/mining_theme_research.py:230-232`
```python
for field in entry.get("definition_unqualified_fields", []) or []:
    if field in defined_fields:
        continue
```
Production passes `defined_fields = {"basis","unit","perimeter"}` (`:542`) — exactly the three fields
the domain file lists as `definition_fields_required` (domain md:80,:88,:98,:106). So every unqualified
field is skipped and the warning is never minted. Observed:
```
prod   defined_fields={basis,unit,perimeter} -> {'limitations': []}
test   defined_fields={unit,perimeter}       -> {'limitations': ['definition_unqualified:basis']}
```
The IR-01 test `tests/test_mining_composition.py:269-271` passes `defined_fields={"unit","perimeter"}`
— a configuration production never uses — which is what conceals the defect.

### MAJOR-6 — tautological test: the only assertion that the unqualified warning survives cannot fail
`tests/test_mining_composition.py:281-282`
```python
headlines["limitations"].append("definition_unqualified:basis")
assert "definition_unqualified:basis" in headlines["limitations"]
```
The test appends the value it then asserts. Per the commission, a test asserting against state the
test itself produced is a MAJOR. It is also the sole coverage of IR-01's warning-preservation clause.

### MAJOR-7 — `test_industry_total_unknown_propagates_into_limitations` tests something else; the code is unreachable
`tests/test_mining_composition.py:229-235` — the body asserts only
`assert "stream_threshold_unknown" in result["limitations"]`. `industry_total_unknown` appears in the
schema enum (`:233`) and in `_headline_for` (`mining_theme_research.py:356`) but is **no value of**
`OMISSION_TO_LIMITATION` (`mining_dependency_binding.py:85-94`) and is appended nowhere in the module.
The W-R domain block lists it as contracted vocabulary (domain md:278). Contracted, unimplemented, and
the test that names it does not cover it.

### MAJOR-8 — CI `paths:` omits the file the module reads at import
`engine/market_ontology/mining_theme_research.py:142` `text = _DOMAIN_YAML_PATH.read_text(...)`, and
`:165-183` raise on any structural change to it (fence count, `slice_key`, slice set). Observed:
`grep -n "MINING_DOMAIN_DEFINITIONS\|research/mining" .github/ci/legacy-jobs.yml` → **no hit**. The
mining block's `paths:` (`.github/ci/legacy-jobs.yml:16860-16874`) has no `research/mining/**` entry, so
a domain-file edit that breaks module import does not select this job. Static import closure is
otherwise covered.

### MAJOR-9 — the ordering law is never exercised end-to-end and is degenerate in practice
Every composed native block gets `stable_subject_id: "subject:unknown"` (observed, all 11 cases),
because no fixture's economics packet carries one and `mining_theme_research.py:457-465` falls back to
the literal. So `_order_rows_by_stable_source_identity` sorts on a constant key in production.
`tests/test_mining_composition.py:153-177` asserts ordering only on the private helper with
hand-built rows, never through `compose_mining_research`. The blocks are also never bound to the
issuer identity that `companies`/`native_subjects` carry.

### MINOR-10 — the closed refusal vocabulary is widened by a subclass that bypasses the base check
`engine/market_ontology/mining_theme_research.py:51-74`
```python
# Bypass the base class CODES check by setting attributes directly.
Exception.__init__(self, f"{code}: {detail}" if detail else code)
```
Three codes (`unknown_definition_version`, `headline_uses_badge_vocabulary`, `interpretation_stale`)
are added outside `MiningResearchRefusal.CODES` (`mining_dependency_binding.py:115-124`), which
R-MIN-24 treats as closed. The widening is invisible to the T01' module's own tests.

### MINOR-11 — sign derivation is fragile; a missing/string value crashes instead of degrading
`:462` / `:471` `"sign": "+" if (_signed_value(packet) or 0) >= 0 else "-"`. A `None` value yields sign
`"+"` and then fails schema (`value` type excludes null, schema `:116`) as a raw
`jsonschema.ValidationError`, not a typed refusal or a limitation; a string value (the schema permits
strings) raises `TypeError` on `>=`. "Unknown data never becomes zero" holds only because no fixture
exercises it.

### MINOR-12 — `summary.headline` is unbounded free text in the contract, and the IR-01 headline is discarded
schema `:58` `"headline": {"type":"string","minLength":1}` — nothing prevents a number in the headline
at the contract level; only `_headline_for`'s fixed strings (`:330-358`) plus a seven-word badge check
(`:629-635`) hold the line. Separately, `_summarize_expectations` returns a `headline` that
`compose_mining_research` **never uses** (`:620-623` consumes only `["limitations"]`), so both IR-01
badge tests (`:255`, `:285`) guard a string that never reaches a payload.

### NIT-13 — docstring says "no I/O" (`:7`) while the module reads the domain file at import (`:142`) and the schema on every validate (`:309`).
### NIT-14 — base is behind main (merge-base `7d843a4d1760` vs `origin/main 8a8ecbe868ff`). No conflict: `git diff --stat <merge-base>..origin/main -- .github/ci/legacy-jobs.yml tests/test_ci_pack.py` → empty output.

---

## MUTANT TABLE

| # | Mutant | Killed? | Why |
|---|---|---|---|
| M1 | flip `"is_range": False` → `True` (`:577`) | **SURVIVES** | no test reads a composed `expectations`; schema allows any boolean (MAJOR-4) |
| M2 | delete the `pairs` loop (`:582-616`) | **SURVIVES** | `expectations == 0` in all 11 cases; `grep pairs tests/test_mining_composition.py` → no hit (BLOCKER-1) |
| M3a | append unknown word `"totally_bogus"` to `limitations` | KILLED | no colon → both `anyOf` branches fail |
| M3b | append `{"x":1}` or `12345` to `limitations` | **SURVIVES** | vacuous `pattern` on non-strings (BLOCKER-3) |
| M4 | `_signed_value` returns `0` instead of `None` (`:209`) | KILLED | `tests:212` `assert composition._signed_value({}) is None` — helper level only, never through `compose` |
| M5 | re-multiply a Morenci-style figure (`value * 0.72` at `:461/:470`) | KILLED | `tests:103` `blocks[0]["value"] == 1250`; `tests:118` `== 940` (literals, not co-varying) |
| M6 | copy a real number into the headline (append `" 1,250 mlb"` in `_headline_for`) | **SURVIVES** | no test asserts composed headline content; badge check bans 7 words only; schema allows any string (MINOR-12) |
| M7 | drop `validate_mining_research(payload)` (`:679`) | KILLED | `tests:374-379` re-validates independently via its own `_validate` |
| M8 | stop suppressing blocks for `missing_derivation` | N/A — **already not suppressed** (BLOCKER-2) |

---

## READY-TO-FREEZE PROBES — `tests/test_mining_composition_probes.py`
Each was executed inline at c76aea66 and observed to fail.

```python
"""Adversarial probes for the T04a Mining composition (frozen at c76aea66 — all FAIL)."""
from __future__ import annotations
import json
from pathlib import Path

import jsonschema
import pytest

from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import CASE_NAMES, synthetic_case

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "contracts" / "market_ontology"
     / "mining_theme_research.v1.schema.json").read_text(encoding="utf-8")
)
_V = jsonschema.Draft202012Validator(SCHEMA)


def test_probe_blocker1_management_pair_is_actually_composed():
    """BLOCKER-1: the copper sales pair and its ONE `pairs:` cost pair must be surfaced."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert len(result["expectations"]) == 2, (
        "copper must surface the sales pair AND the one `pairs:` cost pair as a second "
        f"comparison; got {len(result['expectations'])}"
    )
    assert result["expectations"][0] is not result["expectations"][1]
    for row in result["expectations"]:
        assert row["is_range"] is False and row["is_consensus"] is False
        assert row["comparison"], "comparison text must be present on every pair"


def test_probe_blocker2_same_horizon_revision_emits_no_signed_block():
    """BLOCKER-2: a same-horizon management estimate is not reported economics."""
    case = synthetic_case("same_horizon_revision")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["economics"]["native_blocks"] == case.expected["signed_native_blocks"]


@pytest.mark.parametrize("name", CASE_NAMES)
def test_probe_blocker2b_native_blocks_match_the_frozen_casebook(name):
    """BLOCKER-2 (general): compose must agree with every case's frozen block expectation."""
    case = synthetic_case(name)
    result = composition.compose_mining_research(case.query, case.bundle)
    expected = case.expected["signed_native_blocks"]
    assert len(result["economics"]["native_blocks"]) == len(expected), name
    for got, want in zip(result["economics"]["native_blocks"], expected):
        assert got["value"] == want["value"] and got["measure"] == want["measure"]


@pytest.mark.parametrize("bad", [[{"free": "text", "number": 12345}], [12345], [None], [["x"]]])
def test_probe_blocker3_limitations_rejects_every_non_string(bad):
    """BLOCKER-3: `pattern` is vacuous for non-strings; the branch needs `type: string`."""
    case = synthetic_case("copper_complete")
    payload = composition.compose_mining_research(case.query, case.bundle)
    payload["limitations"] = bad
    with pytest.raises(jsonschema.ValidationError):
        _V.validate(payload)


def test_probe_major4_point_estimate_law_is_enforced_by_the_contract():
    """MAJOR-4: is_range/is_consensus must be required const false; comparison required non-empty."""
    item = SCHEMA["properties"]["expectations"]["items"]
    for key in ("is_range", "is_consensus", "comparison"):
        assert key in item["required"], f"{key} must be required on every expectations row"
    assert item["properties"]["is_range"].get("const") is False
    assert item["properties"]["is_consensus"].get("const") is False
    assert item["properties"]["comparison"].get("minLength", 0) >= 1


def test_probe_major4b_null_leg_requires_a_limitation():
    """MAJOR-4: an absent leg must not pass silently."""
    case = synthetic_case("copper_complete")
    payload = composition.compose_mining_research(case.query, case.bundle)
    payload["expectations"] = [{
        "stable_subject_id": "subject:x", "comparison_kind": "earlier_point_estimate_vs_later_actual",
        "earlier_point_estimate": None, "later_actual": None, "comparison": "",
        "is_range": True, "is_consensus": True,
    }]
    with pytest.raises(jsonschema.ValidationError):
        _V.validate(payload)


def test_probe_major5_definition_unqualified_uses_production_defined_fields():
    """MAJOR-5: the guard is inverted — an unqualified field must MINT the warning."""
    entry = [{"definition_unqualified_fields": ["basis", "unit", "perimeter"]}]
    out = composition._summarize_expectations(entry, defined_fields={"basis", "unit", "perimeter"})
    assert out["limitations"] == [
        "definition_unqualified:basis",
        "definition_unqualified:unit",
        "definition_unqualified:perimeter",
    ]


def test_probe_major8_ci_paths_cover_the_domain_file_read_at_import():
    """MAJOR-8: the module imports the domain md; the job must select on it."""
    ci = (Path(__file__).parent.parent / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    assert "research/mining/m1_integration_program/domain/" in ci


def test_probe_major9_native_blocks_bind_to_a_real_subject_identity():
    """MAJOR-9: ordering by stable source identity is degenerate while every id is the fallback."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    ids = [b["stable_subject_id"] for b in result["economics"]["native_blocks"]]
    assert ids and all(i != "subject:unknown" for i in ids), ids
```

Verification at c76aea66 (inline `python3 -c`, observed):
- BLOCKER-1: `expectations= 0` for all 11 cases (would-be `== 2` → fail).
- BLOCKER-2: composed `[{... 'value': 990 ...}]` vs expected `[]` → `FAILS-AT-HEAD: True`.
- BLOCKER-3: `schema ACCEPTED an object in limitations`; `schema ACCEPTED integer 12345`.
- MAJOR-4: `schema ACCEPTED is_range=True, is_consensus=True, both legs null, no comparison`.
- MAJOR-5: prod defined_fields → `{'limitations': []}`.
- MAJOR-8: `NO PATH ENTRY for the domain file the module reads at import`.
- MAJOR-9: every composed block id is `subject:unknown`.

---

## REPAIR PACKET (≤10 lines)
1. Bind `expectations` to the domain file's `management_estimate_vs_actual` (+ its ONE `pairs:` object)
   for the queried slice, not only to bundle packets; assert exactly one `pairs` entry and surface it
   as a SECOND row, never merged into the sales pair.
2. Add `missing_derivation` to `_suppress_native_blocks` (`:446-450`), or gate on the case's
   `research_usable`; a management estimate must never appear in `economics.native_blocks`.
3. Schema `limitations`: add `"type": "string"` to the pattern branch (and to the enum branch).
4. Schema `expectations.items`: require `is_range`/`is_consensus`/`comparison`; `const: false` on both
   booleans; `minLength: 1` on `comparison`; a null leg must force a limitation.
5. Fix `_summarize_expectations` (`:230-232`) to mint on membership, not skip it; delete the test-only
   `defined_fields` divergence; replace the self-appending assert at `tests:281-282`.
6. Add `research/mining/m1_integration_program/domain/**` to the mining block `paths:`.
7. Either implement `industry_total_unknown` or drop it from the schema enum; rename the test at
   `tests:229` to what it asserts.
8. Bind native blocks to `identity_results`' `stable_subject_id`; assert ordering through
   `compose_mining_research`, not only through the private helper.
9. Freeze the probe file above as `tests/test_mining_composition_probes.py` and add it to the CI block.

---

## ATTACKS THAT DID NOT LAND (do not re-run)
- **Kernel copy.** `git show refs/remotes/pr/7870:engine/market_ontology/semiconductor_theme_research.py`
  (1072 lines) vs the Mining module (761): `difflib.SequenceMatcher` found **no matching run of ≥4
  lines**; the function-name sets are fully disjoint (`diff` of sorted `def` lines shows 37 semi names
  removed, 12 mining names added, no common line). Refusal strings, docstrings and helper decomposition
  differ. The identical 14 top-level schema keys and 14-entry `required` list are R-MIN-25 compliance,
  not copy. **No kernel copy.**
- **Import ban (R-MIN-24/21).** No `semiconductor_theme_research`, `engine.market_ontology.semiconductor`
  or `engine.theme_graph` import in the module or the tests.
- **Synthetic-only (standard 6).** `grep -rniE "0000831259|0001801368|freeport|fcx|mp materials|mountain pass|morenci|cerro verde|grasberg|lynas"` over all four changed files → `NO HITS`.
  (The real issuer names live in the domain md already on main; this PR does not change it.)
- **CI block shape.** The `mining-economic-dossier` block is still the LAST block of
  `.github/ci/legacy-jobs.yml`; the append is to that ONE block; every test named in `run:` is in
  `paths:`; `pip install pytest jsonschema pyyaml` covers both third-party imports —
  `yaml` is genuinely used (`:158` `yaml.safe_load`) and `jsonschema` at `:310`.
- **Morenci re-multiplication.** No multiplication exists anywhere in the module, and the literal
  assertions at `tests:103`/`tests:118` would kill one on both complete cases.
- **Authority.** Five `const: false` flags, non-overridable (`schema:241-253`), echoed on the response
  (`:675`) and on every evidence object (`:535`, `:745`). `authorized_coverage.industry_total` is
  `{"type": "null"}` (`schema:217`). No `neighborhood` key. `additionalProperties: false` at every
  object level.
- **W-R nulls → zeros.** The W-R block's `earlier_point_estimate: null` / `later_actual: null`
  (domain md:257-258) cannot become zeros — because the module never reads them at all (see BLOCKER-1).
  Vacuously satisfied, not implemented.
- **Suite health.** `TZ=UTC python3 -m pytest tests/test_mining_composition.py -q` → `37 passed in 1.63s`.
- **Base conflict.** Branch is behind main but neither `.github/ci/legacy-jobs.yml` nor
  `tests/test_ci_pack.py` moved between the merge-base and `origin/main` (empty `git diff --stat`).
