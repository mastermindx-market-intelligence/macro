# Opus READ_ONLY adversarial review — Mining T01' consumption harness (PR #7932)

- MODE: READ_ONLY · ROUTE: review · Date: 2026-09-24
- Head reviewed: `a27a7262b109` (branch `claude/min-t01-consumption-harness`)
- `origin/main` at review time: `c85272131c0d`; merge-base `e67d3a74963d` (branch is **4 commits behind main**)
- Refs consumed: `refs/remotes/pr/7870` = shared candidate (SEM); `refs/remotes/pr/7891` = TECH precedent;
  `origin/main:research/mining/m1_integration_program/{rulings/R-MIN-2026-09-24-wave1.md,reviews/OPUS_SEAM_AUDIT_B_ONTOLOGY_2026-09-24.md}`;
  `origin/sol/mining-principal-research-20260923:docs/superpowers/plans/2026-09-24-mining-economic-dossier-implementation.md:96-155`
- Suite observed: `TZ=UTC python3 -m pytest tests/test_mining_shared_contract.py -q -p no:cacheprovider` -> `38 passed in 1.32s`

## VERDICT: REJECT

Two BLOCKERs and five MAJORs. The harness is a *consumption seam* that five later Mining PRs import;
its refusal predicates disagree with the kernel it mirrors, and one of its tests turns RED the day the
shared owner merges #7870 to main.

---

## Clean findings (attacks that did NOT land — recorded so they are not re-run)

- **No semiconductor import or copy anywhere on the branch.** `git grep` over the four artifact files
  returns only the guard test's own literal at `tests/test_mining_shared_contract.py:175`.
  `tests/mining_casebook.py:11-14` imports only `mining_dependency_binding`. R-MIN-24 / Audit F5 satisfied on substance.
- **Dataclass mirror is field-for-field.** `MiningResearchQuery` (`engine/market_ontology/mining_dependency_binding.py:120-131`)
  carries all nine SEM:96-106 names in SEM's order with SEM's defaults (`offset=0`, `limit=50`, `expected_generation=None`);
  `MiningOwnerBundle` (:134-146) carries all nine SEM:109-118 names in order. Type relaxation `Literal->str` and the
  added `= ()` defaults are acceptable relaxations (Audit F4: `Literal` has no runtime effect).
- **`True` is rejected as an int for both limit and offset.** `_is_int` (:176-178) plus :195/:197; pinned by
  `tests/test_mining_shared_contract.py:122,125`.
- **`validate_delivery_inputs` is pure.** No file, clock, network or randomness on any path (:209-262); input key set
  is closed (:217-224, raises on extra AND missing); the result dict is exactly `RESULT_KEYS` in order (:252-261 + the
  `assert tuple(result) == RESULT_KEYS` at :261).
- **`research_usable` is derivable only from the closed `omissions` vocabulary** (:254, `len(bundle.omissions) == 0`);
  an unknown omission word raises (:243-246). The vocabulary (:77-87) is disjoint from the composition-limitations
  vocabulary of Audit F3: `missing_derivation`, `stream_threshold_unknown` and `definition_unqualified:*` appear
  nowhere as omission words, and no fixture uses them.
- **`client()` performs zero I/O and returns an equal value for entitled and unentitled callers** (:271-276; `del entitled`).
- **Fixture law satisfied.** All 11 fixtures carry `"synthetic": true`, invented issuers ("Ardent Copper Holdings",
  "Halide Rare Earth Corp"), `https://example.invalid/...` sources, invented CIK-shaped ids (`0000000421`, `0000000732`),
  authority all-false, and no real Freeport/MP figure. Neither `0000831259` nor `0001801368` occurs on the branch's
  fixture set. The non-synthetic loader refusal exists (`tests/mining_casebook.py:90-94`) and is tested (:62-67).
- **CI shape.** The job is the LAST block of `.github/ci/legacy-jobs.yml` (appended at :16784, file EOF), carries
  `if: ${{ false }}` / `gate: code` / `scope: exclusive`, and the `CURATED_EXCLUSIVE` entry exists
  (`tests/test_ci_pack.py:3537`). Measured: importing the suite pulls **zero** third-party modules, so
  `pip install pytest jsonschema pyyaml` is sufficient (over-provisioned, per R-MIN-26's measured line). `TZ=UTC`
  cannot change any result — no clock is read anywhere in the harness.
- **Mutant 1 of the frozen spec IS killed.** Deleting a `CASE_NAMES` entry fails the literal-tuple assertion at
  `tests/test_mining_shared_contract.py:27-39`.

---

## F1 — BLOCKER — Mining's query predicates disagree with the kernel they mirror (3 of 7 codes)

`engine/market_ontology/mining_dependency_binding.py:111` — `_LIMIT_MAX = 500`
`:195` — `query.limit > _LIMIT_MAX`
`:199` — `if not query.expected_generation:`
`:201` — `if not query.source_cutoff or not query.recorded_cutoff:`

Against `SEM@pr/7870:90,171-181` (the exact mirror target R-MIN-24 names):

| code | shared kernel (SEM) | this PR | effect at the seam |
|---|---|---|---|
| `limit_out_of_range` | `_MIN_LIMIT, _MAX_LIMIT = 1, 100` (SEM:90), refuses `limit > 100` | refuses only `limit > 500` (:111,:195) | **false ADMIT**: `limit=101..500` passes Mining and is refused by the kernel |
| `expected_generation_required` | fires only `if query.offset > 0 and query.expected_generation is None` (SEM:177-178) | fires on every query with a falsy generation, offset irrelevant (:199) | **false REFUSE** of a legal `offset=0` query; also refuses `""` where SEM tests `is None` |
| `replay_cutoffs_required` | fires only `if query.time_mode == "system_replay" and ...` (SEM:179-181) | fires for every `time_mode` (:201) | **false REFUSE** of a legal `time_mode="latest"` query |

Ruling violated: R-MIN-24 ("mirroring SEM:96-118 field-for-field ... Mining owns its refusals: ... `limit_out_of_range`,
`expected_generation_required`, `replay_cutoffs_required`") read with R-MIN-06 ("If/when the shared owner delivers a
generalized kernel, the Mining wrapper **delegates to it**"). A wrapper whose predicates differ cannot delegate without
a behaviour change, and T02/T03/T04/T07 will build their query fixtures against the wrong bound.

The module docstring compounds it: `:14-16` claims the validator "owns the Mining query refusals **the shared kernel
does not perform**". Audit F4 says the kernel does not check `slice_key`/`anchor_theme_id` — it *does* check all four
of limit/offset/expected_generation/replay_cutoffs (SEM:171-181). The stated rationale is false for four of seven codes.

No test pins any boundary: `tests/test_mining_shared_contract.py:122-124` tests only `limit=True` and `limit=0`;
nothing tests `100`, `101`, `500`, `501`, `offset=0 + expected_generation=None`, or `time_mode="latest"`.

**Repair (exact):**
1. `:111` -> `_LIMIT_MIN, _LIMIT_MAX = 1, 100  # SEM:90 _MIN_LIMIT/_MAX_LIMIT — mirror, do not widen`
2. `:195` -> `if not _is_int(query.limit) or query.limit < _LIMIT_MIN or query.limit > _LIMIT_MAX:`
3. `:199` -> `if query.offset > 0 and query.expected_generation is None:` (SEM:177-178)
4. `:201` -> `if query.time_mode == "system_replay" and (query.source_cutoff is None or query.recorded_cutoff is None):`
5. Rewrite `:14-16` to say the Mining-owned refusals are `unknown_slice` and `slice_theme_mismatch`, and that the
   remaining five **mirror SEM:171-181 predicate-for-predicate**.
6. If T01' deliberately wants a stricter Mining contract, that is a RULING the seat must mint (it changes the
   delegation contract for five PRs) — not an undocumented divergence.

## F2 — BLOCKER — the shared-contract test asserts the ABSENCE of #7870 and has no strict xfail; it reds main on the day the base lands

`tests/test_mining_shared_contract.py:147-152`
```
def test_shared_contract_is_probed_lazily_and_degrades_to_a_typed_refusal():
    with pytest.raises(MiningResearchRefusal) as raised:
```
`engine/market_ontology/mining_dependency_binding.py:278-292` — `find_spec(...) is None -> refusal`.

`engine/theme_graph/curation_assertion.py` is absent on `origin/main` (`git cat-file -e` -> `does not exist`) and
present on `refs/remotes/pr/7870` with a **callable `validate_assertion` at :265**. The instant #7870 merges,
`find_spec` resolves, `getattr(module, "validate_assertion")` is callable, `shared_contract()` returns the probe,
`pytest.raises` finds no exception, and this suite goes RED — on somebody else's PR, in a job named
`mining-economic-dossier`.

Ruling violated (verbatim): R-MIN-26 — "**Pin the unmerged base with a STRICT xfail (never a skip) where a test
depends on #7870-only behaviour.**" This test depends on #7870-only behaviour (its absence) and carries no pin.
Nothing else in the suite is conditioned on the base either.

Second half of the same defect: the degrade is **not exception-safe**. `find_spec` is not the TECH idiom.
TECH@pr/7891:340 does `from engine.theme_graph import curation_assertion as shared` inside a `try/except ImportError`
and probes **both** `validate_assertion` and `curation_revision` (TECH:343-344). This PR probes one callable and uses
`find_spec`, which (a) imports the parent package as a side effect (measured: `shared_contract()` adds
`engine.theme_graph` to `sys.modules`) and (b) leaves a TOCTOU window: measured, with `find_spec` returning non-None
and the module absent, `shared_contract()` raises **`ModuleNotFoundError`, not `shared_contract_unavailable`**.

**Repair (exact):** replace `:278-292` with the TECH idiom and make the test two-armed.
```python
def shared_contract(self) -> Callable[..., Any]:
    try:
        from engine.theme_graph import curation_assertion as shared
    except ImportError:
        raise MiningResearchRefusal("shared_contract_unavailable", f"{_SHARED_CONTRACT_MODULE} is not on this checkout")
    if not callable(getattr(shared, "validate_assertion", None)) or not callable(getattr(shared, "curation_revision", None)):
        raise MiningResearchRefusal("shared_contract_unavailable", f"{_SHARED_CONTRACT_MODULE} exposes neither required callable")
    return shared.validate_assertion
```
and in the test, branch on `importlib.util.find_spec(_SHARED_CONTRACT_MODULE) is None`: absent -> assert the typed
refusal; present -> assert a callable comes back. Either arm must be a real assertion, never a skip (R-MIN-26).

## F3 — MAJOR — `read_count` is decorative; the frozen spec's mutant 2 is not killed by the assertion that names it

`engine/market_ontology/mining_dependency_binding.py:265-269` (`Harness.__init__` sets `self.read_count = 0`; nothing
ever increments it) and `:149-159` (`RouteUnbound.read_count: int = 0`, a constant default).
`tests/test_mining_shared_contract.py:152,158` assert `read_count == 0`.

The frozen spec (Audit B §3, MUTANT line) names: "make `client()` return a 200 stub -> **read_count assertion fails**".
It does not. `client()` returns a fresh `RouteUnbound()` whose `read_count` is a literal `0` unrelated to the harness;
measured: setting `harness.read_count = 3` still yields `harness.client().read_count == 0`. A mutant that performs a
real protected read and still returns `RouteUnbound()` is invisible to every test in the suite. Both `read_count`
assertions are tautologies that no implementation change can falsify — the exact "test that cannot fail" the
commission asks me to hunt.

**Repair:** make the counter load-bearing — `Harness.client()` returns `RouteUnbound(read_count=self.read_count)`
and `shared_contract()` likewise reports `self.read_count`; keep the counter as the single place any future read
would be recorded. Then the spec's mutant 2 is genuinely killed.

## F4 — MAJOR — the import-law guard scans one file and one AST node type

`tests/test_mining_shared_contract.py:167-175`
```
source = Path(__file__).with_name("mining_casebook.py").read_text(...)
... if isinstance(node, ast.ImportFrom) and node.module
```
It never reads `engine/market_ontology/mining_dependency_binding.py` — the module that actually defines the mirrors and
is the likeliest place a repair lane reaches for `ResearchQuery`. It also misses `import engine.market_ontology.
semiconductor_theme_research as sem` (an `ast.Import`, not `ImportFrom`) and
`from engine.market_ontology import semiconductor_theme_research` (`node.module == "engine.market_ontology"`).

Ruling violated: R-MIN-24 — "`from engine.market_ontology.semiconductor_theme_research import ResearchQuery, OwnerBundle`
is FORBIDDEN **in Mining code and in Mining tests**" (Audit F5). The guard covers neither Mining code nor two of the
three import spellings.

**Repair:** parametrize over `[tests/mining_casebook.py, tests/test_mining_shared_contract.py,
engine/market_ontology/mining_dependency_binding.py]`; collect `ast.Import` `alias.name` **and** `ast.ImportFrom`
`node.module`, and assert no collected name starts with `engine.market_ontology.semiconductor_theme_research`
nor equals `engine.market_ontology` with a `semiconductor_theme_research` alias.

## F5 — MAJOR — `expected` is a mandatory input the validator never reads, and no test pins its per-case shape

`engine/market_ontology/mining_dependency_binding.py:217` requires the key `expected`; it is never referenced again on
any path (:219-262). `tests/test_mining_shared_contract.py:54` asserts only `set(case.expected) ==
{"signed_native_blocks", "reported_only_economics"}` — the key set, never the contents.

Measured consequence: `synthetic_case("source_only", expected={"signed_native_blocks": [ ... ], "reported_only_economics": []})`
— a case that claims a signed block while omitting all economics — is **admitted** by `validate_delivery_inputs` with no
error. The `expected` slots are dead data, and they are the oracle T02/T04 will consume (plan §4, PLAN:132: the dataclass
"returns ... `query`, `bundle`, `expected`, `account_generation`").

The commission's per-case emptiness law is true in the fixtures today but unpinned: complete cases -> exactly one signed
block (`copper_complete.json:32-40`, `rare_earth_complete.json:32-40`); `signed_loss.json:31-41` -> one **negative**
block (`"value": -375`); the other eight -> `signed_native_blocks: []` with one `reported_only_economics` entry.
Nothing fails if a later lane edits any of them.

**Repair:** (a) have `validate_delivery_inputs` cross-check `expected` against `omissions` — a non-empty
`signed_native_blocks` with a non-empty `omissions` set other than `{"positive_witness"}` raises `ValueError`; or, if
T01' must stay a pure input validator, drop `expected` from the required key set and state why. (b) Add the literal
per-case emptiness table as a test (hand-written, not derived from the fixtures).

## F6 — MAJOR — `signed_loss` is the only case whose expected output is a signed block, and it is the one case marked not research-usable

`engine/market_ontology/mining_dependency_binding.py:83` —
`"positive_witness": "The signed result is a loss; it is retained as a signed native block, not a positive witness."`
`tests/fixtures/mining_economic_dossier/signed_loss.json:8-10` — `"omissions": ["positive_witness"]`
`...signed_loss.json:31-41` — `expected.signed_native_blocks` = one block, `"value": -375`, `"sign_preserved": true`

Measured: `research_usable is False` for `signed_loss` while its own `expected` carries a retained signed native block.
The reason string states the block **is** retained; the boolean says the case is unusable. `research_usable` is thereby
overloaded to mean two different things — "no omissions" and "no usable research" — and T04 inherits the confusion for
the exact case (sign preservation) that R-MIN-07 / IR-02 exist to protect ("elimination sign ... travel with every
literal"). `tests/test_mining_shared_contract.py:81` freezes `("signed_loss", False)` as a hand-copied expectation, so
the contradiction is ratified rather than caught.

**Repair (pick one, then record it as a ruling):** either (a) remove `positive_witness` from `OMISSION_REASONS`,
give `signed_loss.json` `"omissions": []`, and let the negative sign live in `expected` only — `research_usable` then
means what it says; or (b) keep the word but split the result: `research_usable` from the omissions minus
`{"positive_witness"}`, plus a separate `positive_witness: bool` key (which changes `RESULT_KEYS` and needs a ruling).

## F7 — MAJOR — the `scope: exclusive` + `CURATED_EXCLUSIVE` claim is falsified by the suite's transitive imports

`.github/ci/legacy-jobs.yml:16789-16790` — "Gate-code pure: the suites import only the standard library,
jsonschema/pyyaml and the Mining modules"
`tests/test_ci_pack.py:3537-3540` — "its curated scope is exactly the Mining files it names"
`paths:` (`.github/ci/legacy-jobs.yml:16794-16798`) lists four files.

Measured import closure of `tests/mining_casebook.py`: `engine`, `engine.market_ontology`,
**`engine.market_ontology.exposure_map`**, `engine.market_ontology.mining_dependency_binding`. Importing the Mining
module executes `engine/market_ontology/__init__.py:13` (`from engine.market_ontology.exposure_map import ShockSpec,
compose_exposure_map, to_json`). `tests/__init__.py` is also required for `from tests.mining_casebook import ...`.
Additionally, `shared_contract()` imports `engine.theme_graph` (measured), which the job's minimal venv must be able to
import. None of `engine/market_ontology/__init__.py`, `engine/market_ontology/exposure_map.py`, `tests/__init__.py`
appears in `paths:`, and the CURATED_EXCLUSIVE entry suppresses the closure expansion that would have added them.

This is a real (if narrow) hole: a change to `exposure_map.py` that breaks `engine/market_ontology/__init__.py` breaks
this suite and will not schedule this job. The dependency claim in the comment is also simply untrue as written.

**Repair:** add `"engine/market_ontology/__init__.py"` and `"engine/market_ontology/exposure_map.py"` to `paths:`
(and `"tests/__init__.py"` if the checker's convention requires it), and correct the comment at :16789-16790 to
"imports the standard library plus `engine.market_ontology.__init__` -> `exposure_map` (stdlib-only) and, lazily,
`engine.theme_graph`." Keep the CURATED_EXCLUSIVE entry — with the paths corrected it is then accurate.

## F8 — MINOR — the KeyError-message assertion is rebuilt from the code under test

`tests/test_mining_shared_contract.py:42-44` — `", ".join(CASE_NAMES)` where `CASE_NAMES` is imported from
`tests.mining_casebook` (:14). The message assertion co-varies with the module under test and can only fail because the
preceding literal-tuple assertion (:27-39) fails first. Remove the dependency: build the expected message from the same
literal tuple the test already writes.

## F9 — MINOR — a dead escape hatch weakens the plain-word assertion

`tests/test_mining_shared_contract.py:100` — `all(reason == "" or reason.endswith(".") for reason in ...)`.
No reason can ever be `""` (every string comes from `OMISSION_REASONS` or `_LIVE_ADMISSION_REASON`, all of which end in
a period), so the `reason == ""` disjunct only licenses a future empty reason. Drop it.

## F10 — MINOR — the `page_generation_change` fixture's own generation mismatch is inert

`tests/fixtures/mining_economic_dossier/page_generation_change.json:18` — `"account_generation": "synthetic-rare-earth-page-7"`
vs `:21-24` — `revision_tuple` carries `["account_generation", "synthetic-rare-earth-page-6"]`.
`tests/mining_casebook.py:63` sets `expected_generation=fixture["account_generation"]`, so the query and the account
agree and `generation_changed` never fires; the case is "unusable" solely because of its hand-written omission word,
and `validate_delivery_inputs` copies the contradictory `revision_tuple` into `bindings` (:248) unexamined. Either make
the fixture exercise the real refusal (drive `account_generation` from the revision tuple) or add a comment saying the
mismatch is deliberate decoration.

## F11 — MINOR — three parallel vocabularies for one concept, with no mapping

Case names (`missing_basis`, `missing_issuer`, `source_only`) vs omission words
(`engine/market_ontology/mining_dependency_binding.py:78-80`: `reporting_basis`, `issuer`, `economics`) vs the T04
`limitations` enum Audit F3 freezes (`missing_basis`, `missing_issuer`, `source_only`). They are disjoint today (good —
the commission's non-overlap test passes), but nothing pins the disjointness or the mapping, so T04 will have to invent
the correspondence. Add a frozen `OMISSION_TO_LIMITATION: dict[str, str]` (or a docstring table) plus a test asserting
`set(OMISSION_REASONS) & set(AUDIT_F3_LIMITATIONS) == set()` and that no omission word matches
`^definition_unqualified:` / equals `missing_derivation` / `stream_threshold_unknown`.

## F12 — MINOR — the branch is 4 commits behind `origin/main`; `git diff origin/main..HEAD` is unreadable

`merge-base e67d3a74963d` vs `origin/main c85272131c0d`. The two-dot diff reports 2,491 insertions across
`scripts/build_am_edition.py` (+745), `tests/test_am_edition_producer.py` (+527), `data/research_vault/catalog.json`
and two deleted research records — all of it main's revert `c85272131c0d Revert "feat(am-edition): MOR-2b Lane A"`
(#7927) reflected backwards. Per-commit inspection confirms the six branch commits touch **only** the artifact files,
so there is no content contamination and no conflict (main has not touched `legacy-jobs.yml`). But R-MIN-26 requires
"append at EOF of a **freshly fetched main**" and the file is contested by >=6 open PRs: re-fetch and rebase before
push/merge, and quote three-dot diffs in the PR body.

## F13 — NIT — history noise

`6e5926d41dbe` commits a stray root `mining_dependency.py` that `1d0b0c7cb4bb` deletes. Harmless after squash-merge;
worth a note only because the WIP message says "uncommitted worktree state".

---

## Frozen-spec mutant re-derivation (Audit B §3 MUTANT line) — do not trust the PR body

| spec mutant | killed? | evidence |
|---|---|---|
| delete one `CASE_NAMES` entry -> KeyError message test fails | **YES** (incidentally) | dies at the literal tuple `tests/test_mining_shared_contract.py:27-39`; the message assertion at :42-44 co-varies and would survive alone (F8) |
| `client()` returns a 200 stub -> **read_count assertion fails** | **NO** | `read_count` is a constant (F3). The stub dies at the `.code == "route_unbound"` assertion (:157), a different assertion; a mutant that reads and still returns `RouteUnbound()` survives every test |
| import `ResearchQuery` from the semiconductor module -> import-law test fails | **PARTIAL** | only for the exact `from engine.market_ontology.semiconductor_theme_research import ...` spelling, in `mining_casebook.py` only (F4) |

---

## `tests/test_mining_shared_contract_probes.py` — freeze RED at `a27a7262` before any repair lane

Every body below is hand-written with synthetic literals, imports only the engine module + the fixtures, and was
executed against `a27a7262` — each one fails **now**, for its finding's reason.

```python
"""Opus R1 probes for PR #7932 — every test here FAILS at a27a7262. Freeze RED (R-MIN-04)."""
import dataclasses
import importlib.util

import pytest

from engine.market_ontology.mining_dependency_binding import (
    MiningResearchRefusal,
    publication_harness,
    validate_delivery_inputs,
)
from tests.mining_casebook import synthetic_case


def _inputs(case, query=None, expected=None):
    return {
        "query": query if query is not None else case.query,
        "bundle": case.bundle,
        "expected": expected if expected is not None else case.expected,
        "account_generation": case.account_generation,
    }


# F1 — the mirrored kernel refuses limit > 100 (SEM@pr/7870:90 _MAX_LIMIT); this harness admits up to 500.
@pytest.mark.parametrize("limit", [101, 250, 500])
def test_probe_limit_above_the_shared_kernel_ceiling_is_refused(limit):
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, limit=limit)
    with pytest.raises(MiningResearchRefusal) as raised:
        validate_delivery_inputs(_inputs(case, query=query))
    assert raised.value.code == "limit_out_of_range"


def test_probe_limit_one_hundred_is_admitted():
    case = synthetic_case("copper_complete")
    result = validate_delivery_inputs(_inputs(case, query=dataclasses.replace(case.query, limit=100)))
    assert result["live_admission"] == "refused"


# F1 — SEM:177-178 fires expected_generation_required only when offset > 0.
def test_probe_offset_zero_without_expected_generation_is_admitted():
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, offset=0, expected_generation=None)
    result = validate_delivery_inputs(_inputs(case, query=query))
    assert result["live_admission"] == "refused"


# F1 — SEM:179-181 fires replay_cutoffs_required only for time_mode == "system_replay".
def test_probe_latest_time_mode_needs_no_replay_cutoffs():
    case = synthetic_case("copper_complete")
    query = dataclasses.replace(case.query, time_mode="latest", source_cutoff=None, recorded_cutoff=None)
    result = validate_delivery_inputs(_inputs(case, query=query))
    assert result["live_admission"] == "refused"


# F2 — the degrade must be typed even when the module resolves and then fails to import.
def test_probe_shared_contract_degrade_is_exception_safe(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    with pytest.raises(MiningResearchRefusal) as raised:
        publication_harness().shared_contract()
    assert raised.value.code == "shared_contract_unavailable"


# F3 — the refusal must report the harness's own read counter, not a constant.
def test_probe_route_unbound_reports_the_harness_read_counter():
    harness = publication_harness()
    harness.read_count = 3
    assert harness.client().read_count == 3


# F5 — a case that claims a signed block while omitting its economics must be refused.
def test_probe_expected_contradicting_omissions_is_refused():
    case = synthetic_case(
        "source_only",
        expected={
            "signed_native_blocks": [
                {"measure": "fictional operating income", "value": 111, "basis": "fictional reported dollars"}
            ],
            "reported_only_economics": [],
        },
    )
    with pytest.raises(ValueError):
        validate_delivery_inputs(_inputs(case))


# F6 — the one case whose expected output is a retained signed block must not be "not research usable".
def test_probe_a_retained_signed_block_is_research_usable():
    case = synthetic_case("signed_loss")
    assert case.expected["signed_native_blocks"][0]["value"] == -375
    result = validate_delivery_inputs(_inputs(case))
    assert result["research_usable"] is True
```

Observed at `a27a7262` via inline probes (no file written):
`limit=101 ADMITTED`; `limit=500 ADMITTED`; monkeypatched `find_spec` -> `ModuleNotFoundError` (untyped);
`harness.read_count=3 -> refusal.read_count = 0`; contradictory `expected` admitted;
`signed_loss research_usable = False` with `expected.signed_native_blocks[0].value == -375`.

---

## Repair packet (<=10 lines)

1. `mining_dependency_binding.py:111,195` — `_LIMIT_MIN, _LIMIT_MAX = 1, 100`; refuse `<1` or `>100` (SEM:90).
2. `:199` — `if query.offset > 0 and query.expected_generation is None:` (SEM:177-178).
3. `:201` — gate on `query.time_mode == "system_replay"` and `is None` cutoffs (SEM:179-181).
4. `:14-16` — rewrite: only `unknown_slice`/`slice_theme_mismatch` are Mining-invented; the other five mirror SEM:171-181.
5. `:278-292` — TECH:340-344 idiom (`try/except ImportError`, probe `validate_assertion` AND `curation_revision`).
6. `test_mining_shared_contract.py:147-152` — two-armed on `find_spec(...) is None`; never a skip (R-MIN-26).
7. `:265-276` + `:149-159` — `client()` returns `RouteUnbound(read_count=self.read_count)`.
8. `:167-175` — guard both Mining source files and both `ast.Import`/`ast.ImportFrom` spellings.
9. Decide F6 by ruling (drop `positive_witness` as an omission, or split the boolean); then pin the per-case
   `expected` emptiness table and the omission/limitations disjointness as literal tests.
10. `legacy-jobs.yml:16789-16798` — add `engine/market_ontology/__init__.py` + `exposure_map.py` to `paths:` and fix
    the dependency comment; rebase onto fresh `origin/main` before push.
