---
key: TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE
claim: >
  Defense in depth hides its own decay. When two independent gates both refuse the same act, the
  OUTCOME is identical whether both work or only one does — so an outcome-shaped test suite
  certifies a half-dead safety net, and the surviving gate masks the dead one until the day it is
  also removed. Each gate therefore needs a test that observes IT, not the outcome it produces:
  for the far gate that means asserting the wiring (that the caller actually passes it what it
  needs), because a protection computed and never handed to the code that deletes is the same
  defect as a reach figure computed and printed nowhere.
falsifier: >
  Remove `protected=protected` from the `apply_deletions(...)` call in `scripts/worktree_gc.py`
  `main()` and run `tests/test_worktree_gc.py`. Before
  `test_main_actually_threads_the_deny_list_into_the_deletion_belt` existed, all 28 tests passed —
  including the armed-apply test whose whole subject is that a protected tree survives — because
  the `classify()` gate refused first and the tree survived for the other reason. That mutant was
  the one survivor of the first design; it is now caught. If a future refactor can silently drop
  either gate and the suite stays green, this claim is refuted and the wiring test has rotted.
so_what: >
  `human_driven_roots` is what stands between an armed deleter and 527 human-driven SSD checkouts
  whose attachment is undetectable (a ChatGPT-web conversation has no process, no shell, no
  reflog). It is deliberately enforced twice — at `classify()` ahead of every proof, and again at
  the deletion belt, so that removing or reordering one leaves the other. That redundancy is
  correct AND it is the reason a passing test suite is weak evidence here. Anyone adding a third
  belt, or widening `roots` per WS:FLEET-STORAGE-LIFECYCLE gates 1–3, must add a gate-specific
  test at the same time; an end-to-end "the tree survived" assertion will pass on a net with
  exactly one strand left.
kind: landmine
verified_at: 2026-09-29
verified_by: "python3 -m pytest tests/test_worktree_gc.py -q — 29 passed; gates at scripts/worktree_gc.py:526 and scripts/worktree_gc.py:716"
scope: [macro]
confidence: verified
---

## How it was found

Not by reasoning. The protection was written with both gates, the suite went green at 28 passed,
and the design looked finished. Mutation testing was run anyway, six mutants, one per independent
claim. Five died. The survivor was **`main` no longer passing `protected=` to the deletion belt** —
the belt still contained its refusal, the config still contained its entries, and every test
passed, because `classify()` had already assigned `PROTECTED` and the tree survived for a reason
the test could not distinguish from the one it meant to check.

The test that closes it does not check an outcome at all. It spies on the call:

```python
    monkeypatch.setattr(wgc, "apply_deletions", spy)
    _run_main(repo, tmp_path, monkeypatch, cfg=cfg, apply=True)
    assert "protected" in seen, "main never passed protected= to the deletion belt"
    assert seen["protected"], "main passed an EMPTY protection to the belt"
```

## Why this is not just "test your code better"

The generalisable part is the *shape*, and it is the inverse of the usual advice. Testing through
the public outcome is normally the right instinct — it survives refactors and does not pin
implementation detail. Redundant safety is the case where that instinct inverts: the outcome is
deliberately insensitive to which strand held, which is exactly what makes the outcome useless as
evidence about the strands. The more carefully layered the protection, the weaker an end-to-end
test is as proof that the layers are alive.

Two consequences worth carrying:

1. **Count the routes to the observed result, not the assertions.** If a "no deletion" / "no
   findings" / "no violations" result is reachable by two paths the test cannot name apart, the
   test binds neither. This is the same defect as
   `DSC:A-GUARDS-CORRECT-TOLERANCE-FOR-AN-ABSENT-SUBJECT-STILL-LIES-IN-ITS-VERDICT`, where an
   empty violation list had two producers and the reporter could not tell them apart — there it
   deceived a human reader, here it deceives a test.
2. **A far gate's test is a wiring test.** The near gate can be tested behaviourally; the far one
   is reachable only when the near one is broken, which no honest test arranges. So assert that
   it is *connected* instead — the computed value must be observed arriving at its consumer. The
   same instrument family that computes a reach and prints it nowhere computes a protection and
   passes it nowhere.
