# Seat rulings R-ENE-23..26: round-3 re-review of the nuclear module (PR #8002 @c857ec36) and the registration copy

- **Issued:** 2026-09-25, about 10:45Z.
- **By:** the Energy Fable CEO seat (session 8955bbc3), operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- **Adjudicates:** `../reviews/OPUS-REVIEW-2026-09-25-w2-module-r3.md`.
- **Binding on:** the registration carrier, for R-ENE-23. For R-ENE-24..26: the transcription lane `ene_w2_nuclear_module_r3fix` (m1, GLM, admitted 10:45Z), the round-4 closure check, and every later round.

| Id | Ruling | Evidence | Superseded if |
|---|---|---|---|
| R-ENE-23 | **Registration copy for `nuclear_power`.** Title: "Nuclear power industry research" / 核电产业研究. Note: the shell's reviewed disclaimer, verbatim. Slice labels: "Reactor technology" / 反应堆技术, "Nuclear components" / 核电部件, "Fuel cycle" / 核燃料循环. `uranium_miners` gets no copy, because it never mounts. The registration carrier writes exactly the entry spec in the registration packet (`../REG-PACKET-2026-09-25-nuclear_power.md`), and only after #7870 merges. | Registration packet §1, read at #7870 `6cd958e92b25` and main `90704bbea8f0` | The shell's reviewed disclaimer changes, or the Chairman's plain-language gate rejects a label |
| R-ENE-24 | **Round-3 adjudication.** The reviewer's FIX_REQUIRED is accepted for R3-1 (MAJOR), R3-2 (MINOR), R3-4 and R3-5 (NIT). The seat reproduced R3-1 and R3-2 itself (below). The code is correct; the gaps are tests. ONE transcription round runs: the seat froze the exact test text and verified it against the head and 26 mutants. Acceptance needs all three: (a) the lane's four files are byte-identical to the seat's own application of the packet; (b) the seat's matrix kills every non-equivalent mutant; (c) an independent Opus closure check on the same reviewer carrier. R-ENE-10 stands: nothing leaves the snapshot before #7870 merges. | The review; the seat's reads, probe and matrix below | — |
| R-ENE-25 | **R3-6 is clarified and the behaviour kept.** `next_evidence` judges the target WINDOW at the reference day. The source_history archival rule (the shared `_is_retrospective`) labels a row retrospective, but it never closes an open window. So an archival capture of a target whose window is still open stays in `next_evidence`. R-ENE-11's "judges passed" means the window judgment. Pinned by `test_archival_record_of_an_open_target_stays_next_evidence`, which kills the `next_query` mutant. | `nuclear_theme_research.py:133-143`, `:399`, `:585-592`; `semiconductor_theme_research.py:253-262` | — |
| R-ENE-26 | **Three NITs close without code.** R3-3 is withdrawn as an EQUIVALENT mutant. There is one role entry per assertion, so `assertion_ref` is unique, and the secondary sort key (`predicate` at 9e3237ef, `role` now) can never decide the order; no test can kill it. R3-7 is a family pattern (Robotics does the same): the lineage names a rejected predecessor's revision, which is a pointer, not content. Energy carries it to the shell owner in its next #7870 relay and does not diverge from the family alone. R3-8 is recorded as a deliberate difference: Robotics' `source_platform_label` branch is unreachable for nuclear, per the reviewer. The seat did not re-verify reachability. | Role key at the three heads; Robotics origin/main `:1295-1320` | The shell owner rules on R3-7 |

## What the seat verified at the artifact before ruling

The reviewer's checkout was used read-only: a sparse review worktree `W` on the seat host, HEAD `c857ec36311a0fb52ff61480f860c0f985e2a483`, and `git -C $W status --short` printed 0 lines before and after. Mutants ran from seat-scratch pytest plugins that exec replaced source into the live module; no repository file was edited.

**R3-1: L1 has no test guard.**
- Head code is correct. `compose(reactor_technology, capacity, [X04])` gave limitations `['witness_cohort_excluded:1']` and 0 evidence refs.
- With `WITNESS_COHORT["reactor_technology"]` extended by `co:us:CCJ`, the same call gave limitations `[]` and 1 evidence ref, so X04 leaks into a primary slice. Yet `python3 -m pytest tests/test_*nuclear*.py -q -p no:cacheprovider` printed `55 passed` at the head AND with that mutant loaded.
- Why:
  - `git grep -n -E 'WITNESS_COHORT|\bX04\b|X04C' HEAD -- tests/` shows no test that pins `WITNESS_COHORT`.
  - X04 is used only as a passenger in a `nuclear_components` refusal call (`test_nuclear_research_composition.py:55`, where the facet gate drops it first).
  - The cohort-count test (`:41-51`) still uses SMR variants only.
  - The packet-named L1 test `test_misfaceted_supplemental_assertion_is_dropped_and_counted` (1071dd9 `:37-41`) has been absent since round 1.

**R3-2: the round trip never reaches a collapsed copy.**
- `_apply_syndication` (`:241-270`) collapses a copy only when exactly ONE same-publisher, same-predicate original is current. The lane's bundle (N04, a correction of N04, and a copy of N04's publisher) has two, so `syndicated_collapsed` is absent. N04 plus the copy alone collapses.
- The binding S1(b) text requires "one bundle holding a correction pair and a collapsed syndicated copy".

**R3-3: an equivalent mutant.**
- The role sort key is `(assertion_ref, predicate)` at 1071dd9 and 9e3237ef, and `(assertion_ref, role)` at c857ec3 (`:493-499`).
- Each assertion yields one role entry, and `assertion_ref` is derived from its unique revision.

**R3-6: two judgments of "passed".**
- `_is_passed_target(assertion, reference_day, query=None)` (`:133-143`) returns true for a window passed at the reference day, OR, when a query is given, for the shared archival rule.
- The archival rule is `_is_retrospective`: source_history mode, and `retained_at` later than `published_at`.
- Rows pass the query (`:399`). `next_evidence` does not (`:592`).

**R3-7: a family pattern.** Robotics' `_correction_lineage` (origin/main `:1295-1320`) and nuclear's (`:782-800`) both walk `bundle.assertions`.

**Pre-verification of the round-4 packet.**
- The seat applied the packet text to an extracted copy of `tests/` at c857ec3 (`git archive`; seat script `r4gate/apply.py`):
  - the 8 nuclear test files gave `62 passed`;
  - `pyflakes` on the four files printed nothing;
  - test counts went 20→24, 2→3 and 13→14, and none is missing;
  - the helpers diff is exactly the two X04 lines.
- The full matrix on that simulated head (seat script `r4gate/matrix.sh`):

| Mutant | Result | Mutant | Result |
|---|---|---|---|
| none | 62 passed | sup_off | 3 failed |
| lineage_empty | 1 failed | latest_only | 1 failed |
| lt | 1 failed | refday_pre | 3 failed |
| refday_only | 2 failed | presence_only | 1 failed |
| sel_pre | 1 failed | why_sup | 1 failed |
| cohort_off | 6 failed | codes_off | 1 failed |
| B1_noop | 3 failed | M1M2 | 7 failed |
| M3 | 3 failed | M5 | 4 failed |
| m3 | 2 failed | m7 | 3 failed |
| prd_only | 1 failed | sel_current | 1 failed |
| ccj_rt_exempt | 2 failed | ccj_rt_cohort | 3 failed |
| leu_nc_cohort | 2 failed | nostale | 1 failed |
| next_query | 1 failed | role_pred | 62 passed (equivalent, R-ENE-26) |

- The candidate tests also pass with the original 1071dd9 X04 text substituted, and they kill `ccj_rt_cohort` and `ccj_rt_exempt` in that mode too.

## Binding text as issued to the transcription round (verbatim)

LANE ene_w2_nuclear_module_r3fix — REPAIR round 3 of PR #8002 (branch `claude/energy-nuclear-vertical-module`, head `c857ec36311a0fb52ff61480f860c0f985e2a483`).
- The independent Opus round-3 re-review returned FIX_REQUIRED: 1 MAJOR (R3-1), 1 MINOR (R3-2) and NITs. The module CODE is correct. Every finding is a missing or vacuous TEST.
- Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`, Energy Fable CEO seat (session 8955bbc3). Seat rulings R-ENE-24..26.
- **This round is a TRANSCRIPTION.** The seat wrote every test below.
  - It already ran them against head `c857ec36311a`: all pass.
  - It ran them against the mutant each targets: each fails.
  - It applied this exact packet to a copy of the files: the 8 nuclear test files give `62 passed`.
- Your job: put the text below into the named files EXACTLY as written, run the tests, commit once, and push.
  - Do not redesign, rename, reformat, reorder, "improve" or add anything.
  - The seat diffs your four files byte-for-byte against its own application of this packet.

## HARD LAWS (a breach voids the round)
1. **Push only** with `git push origin HEAD:refs/heads/claude/energy-nuclear-vertical-module`.
   - Never push to main, to `claude/energy-stack-base-b-6cd958e9`, or to any other branch.
   - No force-push, no rebase, and no merge of any branch.
2. **No GitHub writes other than that push.**
   - No `gh pr ready`, `gh pr merge`, `gh pr edit`, or `gh pr comment`. No labels, no workflow dispatch, no `gh api` writes.
   - The seat owns the PR body. Do not update it. This supersedes any template item asking you to.
3. **Exactly FOUR files change, and nothing else:**
   - `tests/nuclear_research_helpers.py`: two string literals (section A);
   - `tests/test_nuclear_research_composition.py`: append only (section B);
   - `tests/test_nuclear_research_codes.py`: one import line plus an append (section C);
   - `tests/test_nuclear_research_temporal.py`: append only (section D).
   - No engine, contract, app, site, data, config or other test file changes.
   - `git diff --name-only c857ec36311a0fb52ff61480f860c0f985e2a483..HEAD` must print exactly those four paths.
4. **Append-only.** Never delete, rename, reorder or edit an existing test or fixture, other than the two X04 literals in section A.
   - Every `def test_` present at `c857ec36311a` must still exist at your head.
5. **Synthetic only.** Nothing reads `data/`, the network, a clock or a credential.

## A. `tests/nuclear_research_helpers.py`: restore X04's packet text (NIT R3-4)
- Edit ONLY inside the block that starts `X04 = _assertion(` (about line 298).
- WARNING: the same product string also appears in the X04B block. Do NOT touch X04B, X04C or any other fixture.
- Inside the X04 block, change exactly these two literals:
  - `product="Synthetic fuel service",` becomes `product="Synthetic misfaceted fuel service",`
  - `establishes=["a synthetic out-of-cohort value exists"],` becomes `establishes=["a mis-faceted synthetic value exists"],`
- Every other X04 argument stays exactly as it is.

## B. `tests/test_nuclear_research_composition.py`: append at the END of the file (MAJOR R3-1, MINOR R3-2)
- No import change is needed. `pytest`, `source_ref_for`, `variant`, `N04`, `X04`, `X04B`, `X04C`, `nuclear_bundle`, `nuclear_query` and `rows()` are already in the file.
- Leave two blank lines after the file's current last line, then append exactly:

```python
def test_misfaceted_supplemental_assertion_is_dropped_and_counted():
    query = nuclear_query("reactor_technology", "capacity")
    bundle = nuclear_bundle(X04)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert rows(payload, "capacity") == []
    assert payload["evidence_refs"] == []
    assert "witness_cohort_excluded:1" in payload["limitations"]
    with pytest.raises(nuclear.ResearchRefusal) as refusal:
        nuclear.select_authorized_evidence(query, bundle, source_ref_for(X04))
    assert refusal.value.args[0] == "not_available"


LEU_IN_COMPONENTS = variant("X04C", "X04L", subject={"company_node_id": "co:us:LEU"})


@pytest.mark.parametrize(("slice_key", "intruders"), [
    ("reactor_technology", (X04, X04B)),
    ("nuclear_components", (X04C, LEU_IN_COMPONENTS)),
])
def test_fuel_cycle_companies_are_out_of_cohort_in_both_primary_slices(slice_key, intruders):
    query = nuclear_query(slice_key, "capacity")
    bundle = nuclear_bundle(*intruders)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert rows(payload, "capacity") == []
    assert payload["evidence_refs"] == []
    assert f"witness_cohort_excluded:{len(intruders)}" in payload["limitations"]
    for intruder in intruders:
        with pytest.raises(nuclear.ResearchRefusal) as refusal:
            nuclear.select_authorized_evidence(query, bundle, source_ref_for(intruder))
        assert refusal.value.args[0] == "not_available"


def test_witness_cohort_is_the_packet_cohort():
    assert nuclear.WITNESS_COHORT == {
        "reactor_technology": ("co:us:SMR", "co:us:OKLO"),
        "nuclear_components": ("co:us:BWXT",),
        "fuel_cycle": ("co:us:CCJ", "co:us:LEU"),
    }


def test_collapsed_copy_and_correction_pair_round_trip():
    original = variant("N05", "N05P", source={"publisher": "Synthetic Trade Journal"})
    corrected = variant(
        "N05", "N05R", source={"publisher": "Synthetic Trade Journal"},
        correction={"predecessor_revision": original["curation_revision"],
                    "reason": "synthetic correction"})
    copy = variant(
        "N04", "N04S", source={"publisher": "Synthetic Wire"},
        limitations={"source_dependence": "syndicated_copy_of:Synthetic Energy Filings"})
    query = nuclear_query("nuclear_components", "economics")
    bundle = nuclear_bundle(N04, original, corrected, copy)
    payload = nuclear.compose_nuclear_research(query, bundle)
    assert "syndicated_collapsed" in payload["limitations"]
    assert "superseded_present" in payload["limitations"]
    corroboration = [
        ref for row in rows(payload, "economics") for ref in row["corroboration_refs"]]
    assert corroboration == [source_ref_for(copy)]
    advertised = {
        ref["assertion_ref"] for ref in payload["evidence_refs"] if ref["kind"] == "assertion"}
    assert source_ref_for(corrected) in advertised
    for assertion_ref in advertised | set(corroboration):
        evidence = nuclear.select_authorized_evidence(query, bundle, assertion_ref)
        assert evidence["assertion_ref"] == assertion_ref
```

## C. `tests/test_nuclear_research_codes.py` (NIT R3-5)
1. Add the line `import dataclasses` directly above the existing line `import re`.
2. Leave two blank lines after the file's current last line, then append exactly:

```python
def test_stale_interpretation_code_is_declared():
    stale_block = {
        "interpretation_id": "synthetic-interpretation", "input_revisions": [],
        "freshness": "stale", "reviewed_at": "2026-09-20",
        "mechanism": "Synthetic demand mechanism.", "offset": "Synthetic model offset.",
        "falsifier": "Synthetic falsifier.", "missing_measurement": None,
    }
    payload = nuclear.compose_nuclear_research(
        nuclear_query("nuclear_components", "economics"),
        dataclasses.replace(nuclear_bundle(N04), interpretation_blocks=(stale_block,)))
    assert "interpretation_stale" in payload["limitations"]
    unmatched = [
        token for token in payload["limitations"]
        if sum(token == code or token.startswith(code)
               for code in nuclear.LIMITATION_CODES) != 1
    ]
    assert unmatched == []
```

## D. `tests/test_nuclear_research_temporal.py`: append at the END of the file (seat ruling R-ENE-25 pin)
- No import change is needed. `N03`, `N03B`, `nuclear_bundle`, `nuclear_query` and `retrospective_by_revision()` are already in the file.
- Leave two blank lines after the file's current last line, then append exactly:

```python
def test_archival_record_of_an_open_target_stays_next_evidence():
    payload = nuclear.compose_nuclear_research(
        nuclear_query("reactor_technology", "commercial",
                      time_mode="source_history", source_cutoff="2026-12-31"),
        nuclear_bundle(N03, N03B))
    assert retrospective_by_revision(payload)[N03["curation_revision"]] is True
    assert N03["curation_revision"] in {
        revision for item in payload["summary"]["next_evidence"]
        for revision in item["input_refs"]}
```

## TESTS (run from the repo root and quote each summary line)
1. `python3 -m pytest tests/test_market_ontology_nuclear_theme_research.py tests/test_nuclear_owner_bundle.py tests/test_nuclear_research_codes.py tests/test_nuclear_research_composition.py tests/test_nuclear_research_inputs.py tests/test_nuclear_research_route.py tests/test_nuclear_research_sections.py tests/test_nuclear_research_temporal.py -q -p no:cacheprovider`
   - It must print `62 passed`: 55 before, plus 7 new (4 tests in B, one of them with 2 parameter cases, plus 1 in C and 1 in D).
   - If it prints anything else: stop, do not push, and return BLOCKED with the output.
2. `pyflakes tests/nuclear_research_helpers.py tests/test_nuclear_research_composition.py tests/test_nuclear_research_codes.py tests/test_nuclear_research_temporal.py` must print nothing.
3. Test names: for each of the four files, the output of `git show c857ec36311a:<file> | grep -E '^def test_'` must be a subset of the same command's output at HEAD. Quote the comparison.
- You do not run mutants. The seat runs its mutant matrix on your head.

## COMMIT
One commit, with this exact message: `test(energy): pin nuclear cohort, round-trip, stale-code and archival next-evidence (round 3 fixes)`

## RETURN
Your final message has exactly these sections:
- `STATUS: COMPLETE|PARTIAL|BLOCKED`
- `RESULT:`
  - the `head_after` sha;
  - the four files;
  - one line each for R3-1, R3-2, R3-4, R3-5 and R-ENE-25, naming the tests or literals changed.
- `EVIDENCE:` the pytest summary line, the pyflakes output, the test-name comparison, and the name-only diff.
- `GAPS`
- `DEVIATIONS`: every byte you wrote that is not in this packet, or `none`.

Nothing is DONE unless all of these hold: `62 passed`; pyflakes prints nothing; no test name has disappeared; the name-only diff is exactly the four files; and the push went to `claude/energy-nuclear-vertical-module` only.

## Addendum — 10:53Z: re-issued after a seat host-assumption error (no ruling changes)

**The first transcription was byte-correct but blocked on the seat's error.** The lane `ene_w2_nuclear_module_r3fix` (m1, 10:45–10:50Z, 309 s) returned `EXECUTOR_BLOCKED`:
- It left its four files uncommitted and pushed nothing: `git ls-remote` still showed `c857ec36311a`.
- It stopped because the packet required `62 passed`, and m1 has no `httpx`. So the route module skips there (`importorskip`), and the run printed `60 passed, 1 skipped`.
- m1 also has no `pyflakes`.

**What the seat checked before re-issuing.**
- It byte-compared the lane's uncommitted files (`ssh m1 cat …/mo-ext-fix-8002/tests/<f>`) with its own application of the packet: 4/4 IDENTICAL.
- It simulated the missing `httpx` by putting a `ModuleNotFoundError` shim first on `PYTHONPATH`. That gave `60 passed, 1 skipped`, with the single skip at `tests/test_nuclear_research_route.py:7: FastAPI TestClient needs httpx`, exactly the lane's line.

**Re-issue.** Lane `ene_w2_nuclear_module_r3fix_b` went out with sections A–D byte-identical (`diff` of the A–D range was empty). Only the TESTS host-tool rules and the DONE line changed:
- the expected line now depends on whether `httpx` imports;
- where `pyflakes` is absent, `py_compile` runs instead;
- the lane may never install anything.

The seat runs the route test and `pyflakes` on the pushed head itself. The acceptance criteria of R-ENE-24 are unchanged.

Packet diff (first issue → re-issue):

```
1c1
< LANE ene_w2_nuclear_module_r3fix — REPAIR round 3 of PR #8002 (branch `claude/energy-nuclear-vertical-module`, head `c857ec36311a0fb52ff61480f860c0f985e2a483`).
---
> LANE ene_w2_nuclear_module_r3fix_b — REPAIR round 3 (re-issue) of PR #8002 (branch `claude/energy-nuclear-vertical-module`, head `c857ec36311a0fb52ff61480f860c0f985e2a483`).
7a8,10
> - **RE-ISSUE NOTE (10:55Z).** The first transcription of this packet (lane `ene_w2_nuclear_module_r3fix`, m1, 10:45Z) was byte-correct. The seat diffed its uncommitted files: all 4 were identical. It stopped only because this packet assumed `httpx` and `pyflakes` exist on the host, and m1 has neither. That was the seat's error, not yours.
>   - This re-issue changes ONLY the TESTS host-tool rules and the DONE line. Every byte of sections A–D is unchanged.
>   - Your worktree is reset to the branch head. Transcribe again from scratch.
149,150c152,156
< 1. `python3 -m pytest tests/test_market_ontology_nuclear_theme_research.py tests/test_nuclear_owner_bundle.py tests/test_nuclear_research_codes.py tests/test_nuclear_research_composition.py tests/test_nuclear_research_inputs.py tests/test_nuclear_research_route.py tests/test_nuclear_research_sections.py tests/test_nuclear_research_temporal.py -q -p no:cacheprovider`
<    - It must print `62 passed`: 55 before, plus 7 new (4 tests in B, one of them with 2 parameter cases, plus 1 in C and 1 in D).
---
> 1. `python3 -m pytest tests/test_market_ontology_nuclear_theme_research.py tests/test_nuclear_owner_bundle.py tests/test_nuclear_research_codes.py tests/test_nuclear_research_composition.py tests/test_nuclear_research_inputs.py tests/test_nuclear_research_route.py tests/test_nuclear_research_sections.py tests/test_nuclear_research_temporal.py -q -rs -p no:cacheprovider`
>    - First run `python3 -c 'import httpx'`. The expected result depends on it:
>      - **httpx imports:** the summary must show `62 passed`, with no skipped, failed or error. That is 55 before, plus 7 new: 4 tests in B, one of them with 2 parameter cases, plus 1 in C and 1 in D.
>      - **httpx does NOT import** (m1 today): the summary must show `60 passed, 1 skipped`, with no failed or error. The `-rs` report must list exactly ONE skip, `tests/test_nuclear_research_route.py:7: FastAPI TestClient needs httpx`. The seat simulated exactly this: `60 passed, 1 skipped`.
>      - The number of warnings does not matter.
151a158
>    - NEVER install `httpx` or anything else. The seat runs the route test on its own host after your push.
152a160,161
>    - If neither `pyflakes` nor `python3 -m pyflakes` exists on the host (m1 today), run `python3 -m py_compile` on the same four files instead. It must print nothing.
>    - Then write `pyflakes: not available on host; py_compile clean` in EVIDENCE. Never install pyflakes; the seat runs it on your pushed head.
170c179
< Nothing is DONE unless all of these hold: `62 passed`; pyflakes prints nothing; no test name has disappeared; the name-only diff is exactly the four files; and the push went to `claude/energy-nuclear-vertical-module` only.
---
> Nothing is DONE unless all of these hold: the TESTS step 1 result for your host (`62 passed`, or `60 passed, 1 skipped` with only the httpx route skip); pyflakes, or its py_compile fallback, prints nothing; no test name has disappeared; the name-only diff is exactly the four files; and the push went to `claude/energy-nuclear-vertical-module` only.
```
