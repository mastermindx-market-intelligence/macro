# R-ENE-41 to R-ENE-43 — the ENERGY directive of 2026-09-29 (module audits paused; the cutoff readers ruled for the integration; a target-window rewind reported)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-29. PR #8002 is at `508d8c206357287a5f8ff9d1596efc32b3749459` (round 11), DRAFT, with no labels and auto-merge null. #7870 is OPEN and DRAFT at `a0d7b054ff2334739f8bd2abcfdc5943dd60ee74`. Neither had moved when read at 2026-09-29T16:10:52Z (#8002 last updated 2026-09-28T13:40:40Z, #7870 13:23:01Z). The Slack root has no reply since 2026-09-28.
- This ruling changes records only. Nothing on #8002 changes under it.

## The ENERGY directive

The operator relayed a portfolio directive into this session at 2026-09-29T16:09:43Z. Its Energy entry is numbered 7 in that list. It is **not** the "item 7" these records already use: that is item 7 of #7870 comment 5868018569, the malformed-cutoff relay (R-ENE-35). These records call the new one **the ENERGY directive**. Verbatim:

> 7. ENERGY — pause additional module audits; first consumer-integration candidate
>
> Preserve #8002 at its actual current head and the completed nuclear-local audit evidence. It is stacked on a base that supplies real imports absent from its intended standalone main integration; do not merge or retarget it prematurely.
>
> No new generic round of test-pin or docstring nits is requested while the engine and upstream dependency are unchanged. New material correctness, privacy or production defects must still be reported.
>
> After the #7870 foundation is released and source custody permits integration, reconcile #8002 onto the actual accepted base, then execute the prepared Energy-owned registration/mount packet with one writer. Resolve the two recorded temporal issues as part of that integration: response-date grammar must match the admitted parser, and outside replay a caller-supplied cutoff must not silently make an overdue review look current. Preserve historical replay semantics through an explicit owner decision and tests.
>
> Prove the nuclear route, browser mount, scoped evidence, private/cache headers, unavailable/revoked behavior and update/restart propagation. Keep the VPS disk hold, production credential boundary and Power-Demand follow-on separate; no bypass or premature nuclear acceptance.

## R-ENE-41 — module audits paused

- While nuclear's engine at `508d8c206357` and #7870's base at `a0d7b054ff23` are unchanged, there is no further audit or review round of nuclear's module and no generic test-pin or docstring round.
- The next review of nuclear's module is at the reconciliation onto #7870's accepted base. Round 11 already set this.
- #8002 stays at `508d8c206357`, DRAFT, with no labels and auto-merge null. It is neither merged nor retargeted before #7870 is released and source custody permits.
- The completed nuclear-local audit evidence stands and is not redone. It is rounds 1 to 11, the reviews in `../reviews/` and the rulings in this directory.
- Material correctness, privacy and production defects are still reported. R-ENE-43 is one.
- Reopens if nuclear's engine or #7870's head changes, or a material defect is found.

## R-ENE-42 — the cutoff readers, ruled for the integration

This is the owner decision the directive asks for. It supersedes R-ENE-18's clause "The review clock (`_now_of_query`) is out of scope and unchanged", effective at the reconciliation. Before then nothing on #8002 changes.

**The rule.** Nuclear uses a query cutoff as a clock only in a time mode whose base time gate reads that cutoff:
- `recorded_cutoff` only in `system_replay`;
- `source_cutoff` only in `source_history` and `system_replay`.

Outside those modes nuclear's clocks stay data-derived, exactly as they are when no cutoff is supplied:
- the review clock is the newest `reviewed_at` in the bundle;
- the target-window reference day is the newest `retained_at` or `published_at` day, disclosed as `target_windows_judged_at:<day>`.

**Validation is unchanged.** Every supplied cutoff is still validated in every mode, with the grammar the accepted base admits, so a malformed cutoff fails the query instead of passing silently. This keeps R-ENE-35, and it keeps R-ENE-40's malformed-cutoff test without asking the base to validate in `latest` and `source_history`. If the accepted base validates every cutoff in every mode itself, nuclear's own validation is redundant, and whether to keep it is decided at the reconciliation.

**Historical replay is unchanged.**
- A replay judges review expiry at its recorded cutoff (R-ENE-40's replay test, 5 cases) and target windows at its source cutoff.
- `source_history` still judges target windows at its source cutoff.

**Evidence.** The base time gate reads `recorded_cutoff` only in a replay (`probe_selection`). It reads `source_cutoff` only in `source_history` and a replay:
- `probe_third_reader`: in `latest` a malformed source cutoff raises first at nuclear `:142`, and in `source_history` at the base `:159`;
- `probe_target_rewind` (below): in `latest` a `2025-12-31` source cutoff still selects both `2026-09-19` records.

P3 (round-10 closure) and R-ENE-43 show what a mode-blind read does.

**Reopens if** the accepted base gives a cutoff a meaning in another mode, or refuses it there. If it refuses, the hazard closes at the base, and tests 1 to 3 below assert the refusal instead.

### Test obligations (they land with the integration, in nuclear's test files)

1. **Review clock, rewind closed.** In `latest` and `source_history`, take a due time of `2026-09-19` with the newest review at `2026-09-20`. The record is withheld (`review_expired_present`) with no recorded cutoff, with `2026-09-18` and with `1970-01-01`. These last two are P3's served rows.
2. **Review clock, no forward push.** A due time of `2027-01-01` is served with no recorded cutoff and with `2099-12-31`.
3. **Target windows, rewind closed.** In `latest`, with `source_cutoff` absent, `2025-12-31` or `2099-12-31`, the forward set is `N03` alone, and `target_windows_judged_at:2026-09-20` is present in all three.
4. **Replay and source history kept.** R-ENE-40's replay test is unchanged. In `source_history`, `2026-09-30` keeps `N03` forward with no `target_windows_judged_at:` limitation, and `2025-12-31` selects 0.
5. **The failure kept.** R-ENE-40's malformed-cutoff test is unchanged. A malformed `source_cutoff` in `latest`, with a target in the slice, still fails the query.
6. **Mutants.** A mode-blind `_now_of_query` and a mode-blind `_reference_day` are each killed by tests 1 to 3. A mutant that drops the validation is killed by test 5.

## R-ENE-43 — a target-window rewind, reported

The directive asks for material correctness defects to be reported, and this is one.
- `_reference_day` (`nuclear_theme_research.py:118-130` at `508d8c206357`) returns a supplied `source_cutoff` in every mode.
- The base time gate does not read that cutoff in `latest`.

So in `latest` a caller's cutoff moves the target-window reference day while every record stays selected:
- a deployment target whose date has passed (`N03B`, to `2026-01-31`) is served as a forward target;
- a target still ahead (`N03`, to `2027-12-31`) drops out;
- in both cases the `target_windows_judged_at:` disclosure disappears.

This is P3's review-expiry rewind, on the third reader. R-ENE-42 closes both at the integration. The reader is nuclear's, so no #7870 post is owed.

## The two recorded temporal issues, at the integration

1. **The response-date grammar.** Nuclear's response schema `$defs/when` is aligned to the grammar the accepted base admits, which is the grammar R-ENE-42's validation uses. Every cutoff nuclear accepts is then schema-valid in its echo, and every value the schema admits parses.
   - Today the schema refuses `2026-1-5`, `2026-12-31T12:00Z`, `+0800` offsets and full-width digits, and admits `2026-13-45` and `2026-02-29` (round-10 closure, OBS 1).
   - The alignment test covers those values plus `not-a-date` and `20261231`.
2. **The rewind hazard.** R-ENE-42, with the tests above.

## The integration, in order (the directive's sequence)

Only after #7870 is released and source custody permits:
1. Reconcile #8002 onto the accepted base. Re-run REG-PACKET §1c's gates at the post-merge heads, and record `m34_broad` and `my8_swallow_cutoff` per the round-9 closure (NIT-5).
2. ONE writer executes the registration packet: §3, §3b, §4, §4b, §5 and §5b. §5b, added with this ruling, carries R-ENE-42, the `$defs/when` alignment and their tests.
3. Nuclear's module is reviewed at the reconciliation (R-ENE-41), by the carrier's own Opus READ_ONLY review (§5).
4. Proof covers:
   - the nuclear route;
   - the browser mount;
   - scoped evidence;
   - the private, no-store, noindex and noarchive headers, on success and on every error path;
   - unavailable and revoked behaviour;
   - update and restart propagation.
5. These stay separate and are never bypassed:
   - the VPS disk hold (`# MMX-DISK-TRIAGE-HOLD`, #6902, an EXACT_HUMAN_GATE);
   - the production credential boundary (Task 10);
   - Power-Demand (R-ENE-16, after nuclear ACCEPTANCE).

   Nuclear acceptance is never claimed early.

## Reproduction (R-ENE-43)

- **Where it ran.** In the seat's sim `r11gate/simB11f` (#8002's files over #7870 `a0d7b054ff23`), under Python 3.12.13.
- **The bytes are #8002's.** The sim's `engine/market_ontology/nuclear_theme_research.py` and `tests/nuclear_research_helpers.py` hash to sha256 `3a795c54c70e3a08…` and `60801c548c0831b2…`, the same as `git show 508d8c206357:<path>`.
- **This is not a re-probe.** The handoff's `do_not_redo` bars re-probing the third reader, but `probe_third_reader.py` probed malformed values only. This probe asks the well-formed question.
- **What it reads.** The walk collects items that carry `input_refs` and have either a `label` of `target` or a `retrospective` key. `retrospective` was empty in every row, so the forward list is what the probe observes.

```python
"""Seat probe 2026-09-29: can a well-formed caller source_cutoff OUTSIDE a replay move nuclear's
target-window reference day (the ENERGY directive's 'overdue made to look current' class)?
Distinct from probe_third_reader.py, which probed malformed values only."""
import sys
from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N03, N03B, nuclear_bundle, nuclear_query

CASE = {N03["curation_revision"]: "N03(to 2027-12-31)", N03B["curation_revision"]: "N03B(to 2026-01-31)"}

def walk(node, out):
    if isinstance(node, dict):
        refs = node.get("input_refs")
        if isinstance(refs, list) and ("retrospective" in node or node.get("label") == "target"):
            for ref in refs:
                if ref in CASE:
                    out.append((CASE[ref], node.get("label"), node.get("retrospective")))
        for v in node.values(): walk(v, out)
    elif isinstance(node, list):
        for v in node: walk(v, out)

def run(label, **kw):
    q = nuclear_query("reactor_technology", "commercial", **kw)
    p = nuclear.compose_nuclear_research(q, nuclear_bundle(N03, N03B))
    seen = []; walk(p, seen)
    forward = sorted({c for c, lab, _ in seen if lab == "target"})
    retro = sorted({c for c, _, r in seen if r is True})
    lims = sorted(x for x in p["limitations"] if x.startswith("target_windows"))
    print(f"{label:40} selected={p['authorized_coverage'].get('selected')} forward={forward} retrospective={retro} disclosure={lims}")

run("latest, no cutoff (control)")
run("latest, source_cutoff=2025-12-31", source_cutoff="2025-12-31")
run("latest, source_cutoff=2099-12-31", source_cutoff="2099-12-31")
run("source_history, source_cutoff=2026-09-30", time_mode="source_history", source_cutoff="2026-09-30")
run("source_history, source_cutoff=2025-12-31", time_mode="source_history", source_cutoff="2025-12-31")
print(sys.version.split()[0])
```

```text
latest, no cutoff (control)              selected=2 forward=['N03(to 2027-12-31)'] retrospective=[] disclosure=['target_windows_judged_at:2026-09-20']
latest, source_cutoff=2025-12-31         selected=2 forward=['N03(to 2027-12-31)', 'N03B(to 2026-01-31)'] retrospective=[] disclosure=[]
latest, source_cutoff=2099-12-31         selected=2 forward=[] retrospective=[] disclosure=[]
source_history, source_cutoff=2026-09-30 selected=2 forward=['N03(to 2027-12-31)'] retrospective=[] disclosure=[]
source_history, source_cutoff=2025-12-31 selected=0 forward=[] retrospective=[] disclosure=[]
3.12.13
```
