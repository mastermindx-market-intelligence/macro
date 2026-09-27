---
key: THEME-GRAPH-CONTRACTS-GATE-IS-A-COMPOUND-PREDICATE
question: "What is a sound Gate C predicate over scripts/check_theme_graph_contracts.py, given that exit code 0 alone does not prove the theme-graph contracts hold?"
answer: >
  No single signal this script emits is sufficient, and the two obvious
  single-signal candidates are both unsound in OPPOSITE directions. Gate C is
  defined as a compound predicate: invoke with `--strict` on a materialised
  `data/`, and require (1) exit 0, (2) stdout carries no
  `::warning title=theme graph contract breach::` line, and (3) every
  `::notice title=theme graph - <class>::` is enumerated and triaged against the
  script's own taxonomy - `identity resolution census` and
  `licensing snapshots - designed` are designed and non-blocking, while
  `theme graph indeterminate` (store incomplete), either
  `side-car MISSING - half-finished build` and `capability promoted itself` block
  as INDETERMINATE or worse. If `data/` is not materialised the honest verdict is
  INDETERMINATE, not pass. Condition (2) is redundant under `--strict` and is kept
  anyway, because the failure being guarded against is a gate step that silently
  loses the flag.
rationale: >
  A gate whose pass condition is satisfied by a tree that violates the contract is
  not a gate, and neither is one that no clean tree can ever satisfy. Both were
  found here. WITHOUT `--strict` a real breach returns 0 by design - the flag's own
  help text calls the default "advisory rc 0", and the house-law guard-suite row
  states the reason (the graph is display-tier with all six authority booleans
  false, so a breach must not take the nightly collect lane down). That is a
  documented property of the script, not a defect in it, and it was this seat's own
  exposure: every Gate C result this operation had recorded was a bare exit code
  from a non-strict local run, so a breach would have read as green. The same
  house-law row also records that `--strict` is what CI runs, so a lane whose Gate
  C result comes from the CI invocation was never relying on the advisory path. The
  tempting fix - gate on the script's own success line - is WORSE: the marker at
  line 1099 requires `notices` to be empty as well as `breaches`, and the
  identity-resolution census at line 1044 is an unconditional notice whenever the
  sidecar file merely exists. The sidecar is committed. So on any materialised
  store the marker line never prints, clean or not, and a gate built on it is red
  forever and indistinguishable from a real breach. Notices are a mixture of
  designed always-on output and genuine incidents, which is why they must be
  triaged by their printed class titles rather than counted.
alternatives:
  - option: "Gate C := stdout contains the literal `theme graph contracts OK`."
    why_not: >
      Unsatisfiable on a materialised store, and this was this record's own first
      answer. The marker at 1099 is guarded by `not breaches` AND `not notices`,
      and line 1044 appends an identity-resolution census notice whenever
      data/theme_graph/identity_resolution.parquet merely exists - present and
      committed at both #7870's head and main. The script's own selftest calls the
      census "a designed, always-on notice ... printed every run, never an
      incident" and asserts its presence on a store it separately asserts is
      contract-clean. A gate no clean tree can pass is as uninformative as one no
      breach can fail.
  - option: "Gate C := exit code 0, the earlier definition."
    why_not: >
      Hollow without `--strict`: line 1109 returns `1 if strict else 0`, so a
      breach exits 0 on the default path. Confirmed empirically by the shared
      script's owner on materialised data - 1168 identity_resolution rows
      violating the state-to-ids biconditional, which is a breach (line 960), exit
      0 anyway.
  - option: "Patch the script so the notices path also returns non-zero."
    why_not: >
      It is a shared script owned by another lane and consumed by several
      verticals; changing its exit semantics from a Robotics carrier would alter
      other lanes' gate results without their adjudication. It would also make
      every clean run non-zero, because the census notice is always on. Reading
      stdout costs nothing and changes no shared behaviour. The measurement was
      handed to the owner instead.
  - option: "Treat a missing data/ directory as a pass because nothing breached."
    why_not: >
      Nothing could breach, because nothing was read. That is the instrument
      producing a confident null, which is the failure this operation has already
      recorded twice.
evidence:
  - "scripts/check_theme_graph_contracts.py at #7870 head a0d7b054ff23, 87600B: line 1099 prints \"theme graph contracts OK ...\" guarded by `if not breaches` (1097) AND `if not notices` (1098); line 1101 `return 0`; line 1102 prints `::warning title=theme graph contract breach::`; line 1109 `return 1 if strict else 0`; line 1582 help text \"return 1 on a breach (CI); default is advisory rc 0\""
  - "AST walk of the same blob, parent-chain per call site: the `[identity resolution census]` notice at line 1044 is guarded ONLY by `if idres is not None` (856) nested in `if idres_path.exists()` (850). No content-dependent condition. The other five notice sites are content-guarded; 33 breach sites exist, including the state-to-ids biconditional at 960."
  - "The script's own selftest, lines 1229-1232: \"The identity-resolution CENSUS is a designed, always-on notice (7e - printed every run, never an incident), so it is the one notice a 'fully clean' store may still carry\", and line 1334 asserts `any(\"identity resolution census\" in x for x in n)` with the message \"the identity-resolution census must be printed every run\". Contract statement plus a pin that states it: design, not defect."
  - "data/theme_graph/identity_resolution.parquet is committed: 203378B at a0d7b054ff23 and 204044B at main, with a nonexistent sibling path as negative control. So the census notice fires on any materialised checkout and the marker line at 1099 is unreachable there."
  - "The advisory exit code is DESIGNED and documented: docs/HOUSE_LAW_CI_GUARD_SUITE.md at main, row theme_graph.edge_contract, says the nightly invocation is ADVISORY because the graph is display-tier with all six authority booleans false, so a breach must not take the collect lane down, and that \"--strict is what CI runs\". The same comment appears at the call site, scripts/ci/daily_engine_regional_desk_builders.sh:118-120, whose brun line passes NO --strict."
  - "LANE MAP VERIFIED AGAINST THE WORKFLOWS, not the doc, because the doc row is stale on this point. The --strict invocation is real: .github/ci/legacy-jobs.yml:11456 runs `python -m scripts.check_theme_graph_contracts --strict` after --selftest at 11455. But that file is not under .github/workflows/ and its job unrun-intl-libraries carries `if: false` (11341) and `gate: data` (11342); its steps execute only through scripts/run_ci_pack.py, which filters `job.gate == gate` (run_ci_pack.py:1690). Sweeping all 99 workflow files with the read pipeline positively controlled: `--gate code` appears in ci.yml, selfhosted-ci-canary.yml and trusted-ci-executor.yml; `--gate data` appears in data-health.yml ONLY, whose triggers are schedule, workflow_run on daily, and workflow_dispatch - never pull_request. So NO pull-request lane runs this guard, the house-law row lane: pr_ci is stale, and a carrier PR receives no theme-graph contract verdict from CI at all."
  - "Notice class taxonomy read from the same blob: designed = `[licensing snapshots - designed]` (505), `[identity resolution census]` (1044); incident or indeterminate = store incomplete (375, untagged so it prints as `::notice title=theme graph indeterminate::`), `[capability side-car MISSING - half-finished build]` (843), `[identity resolution side-car MISSING - half-finished build]` (1053), `[capability promoted itself]` (835). Lines 1090-1091 state the intent: distinct titles per class so the designed notice cannot visually mask a half-finished build."
  - "Controls on the read: 21 occurrences of 'def ' (positive), 0 occurrences of a nonsense token (negative). The two blobs at 1e38d5c955dc and a0d7b054ff23 are byte-identical at 87600B, so reading both is one observation and not an independent confirmation."
  - "Macro PR #7780 comment 5852920768 (the exit-code measurement posted to the shared owner on the Sol coordination carrier, including this seat's own exposure; carrier verified by .issue_url, not by recall)"
affects:
  - "WS:GMI-THEME-GRAPH"
  - "scripts/check_theme_graph_contracts.py"
confidence: high
reversibility: easy
decided_by: "session 17c9f82c-8981-43d5-bf95-307691cb27cd (principal seat, operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001)"
decided_at: 2026-09-27
---

# Scope of this record

This fixes what Gate C means for operation `gmi-robotics-fable-ceo-e2e-20260923-chairman-001`,
and reports measured properties of a shared script. It does not redefine any other vertical's
gate and changes no behaviour.

It matters more than it first appeared, because **no pull-request lane runs this guard.** The
`--strict` invocation is real but lives in a `gate: data` job, and the only `--gate data` caller is
`data-health.yml`, which triggers on a schedule and on `daily` completing — never on
`pull_request`. So a carrier PR gets no theme-graph contract verdict from CI, and this local
predicate is not a supplement to a CI gate; for a PR it is the only Gate C there is.

# Why the obvious fix is the wrong fix

The script prints its own success line only when `breaches` AND `notices` are both empty. The
identity-resolution census is a notice, it fires on the mere existence of a sidecar file, and
that file is committed. So on a materialised store the success line never prints - on a clean
store as much as on a broken one. Gating on it produces a permanent red that cannot be told
apart from a real breach, which is the original defect inverted rather than repaired. Nothing
in the repo consumes the marker line today, so nothing would have caught this.

# What the first draft of this record got wrong

This record was first written on 2026-09-26 with the answer "Gate C is the marker line", and an
independent read-only audit of the carrier refuted it before it landed. Two facts were missed by
the same class of instrument error this operation keeps recording: a line-range read of the
return block showed the guard `if not notices` without asking what puts things in `notices`, and
a claim about the script's shared consumers was made without reading the house-law row that
documents them. The general lesson is not new - a read scoped to the lines you already suspect
confirms whatever you brought to it - but the specific trap is: a guard you can see is not a
guard you understand until you have enumerated everything that can trip it.

# The falsifier

If the census notice is later made conditional, or moved out of `notices`, or the script is
changed so the notices path returns non-zero, the marker line becomes reachable on a clean
materialised store and this record should be superseded rather than edited. Until then, a Gate C
claim that cites the marker line is unproven, a claim that cites a bare exit code from a
non-strict run is unproven, and only the compound predicate above decides in either direction.
