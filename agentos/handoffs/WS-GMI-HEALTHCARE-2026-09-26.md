---
workstream: "WS:GMI-HEALTHCARE"
session: claude/healthcare-seat-wave2
model: fable
ended_because: complete
mission: >
  D1 of the Healthcare Fable CEO program (operation gmi-healthcare-fable-ceo-e2e-20260924-chairman-001,
  research carrier #7788): make the incumbent visible FDA supply consumer truthful — T02 collector sweep
  qualification, observation sidecar, non-destructive failed refresh, retention by distinct source
  generation, drip receipt; T01 summarize_supply with seven truthful bilingual display-only chip states.
  Shipped as ONE implementation carrier (PR #7930, branch claude/healthcare-d1-fda-supply) built by
  external GLM lanes on the fabric, gated by independent Opus reviews and seat-frozen probe files.
state_before: >
  At pickup (2026-09-24 10:00Z) no review return, no ACK/START, no implementation PR; the D1 files on
  main matched the R7 probe pins (fda_scarcity d081b19c, fda_shortages 23b5e6f7); tests/test_foresight_cascade.py
  ran in no CI job; #7870 (shared foundation) DRAFT/unmerged so D2–D4 were held by the independent review's
  scoped HOLD. Records PRs #7928/#7933/#7948 landed the program README, WS record, reviews and rulings.
changed:
  - path: collectors/fda_shortages.py
    what: "collect_shortage_sweep / save_shortage_observation / read_shortage_observation / format_observation_receipt: qualification taxonomy (incl. NO_SOURCE_GENERATION at the seam), sidecar with parquet digest + predecessor fence, non-destructive failed refresh, guarded reads, retention by distinct generation, pure clock."
  - path: engine/fda_scarcity.py
    what: "summarize_supply(rows, *, capture=...): observation reader emits qualified + observation_state; seven source_status chips; unavailable variants not-observed / unreadable / refresh-failed; no None/banned substrings; ASCII-only tooltip contract."
  - path: templates/foresight.html.j2
    what: "chip label rendered via t(tfs.label, tfs.label_zh)."
  - path: scripts/build_foresight.py
    what: "one drip receipt line `fda_shortages: observation ...` in the nightly log."
  - path: .github/ci/legacy-jobs.yml
    what: "gate:code exclusive job healthcare-fda-supply (paths = measured closure + the template) running the generation, cascade and six frozen probe suites; listed in CURATED_EXCLUSIVE."
  - path: tests/test_fda_supply_probes*.py
    what: "six seat-frozen probe files authored by independent Opus reviewers (14+8+6+1+7+4 tests); lanes never edited them (git log --format=%an shows only the seat)."
  - path: research/healthcare/hc_program/
    what: "README checkpoints, every Opus review (R1 independent, T02 R1/R2, T01 R1, D1 FINAL, D1 ACCEPTANCE), every seat ruling set (T02 R1–R4, T01 R1–R3) and the merge-window rulings R-D1-MERGE-00/01."
verified:
  - claim: "All six frozen probe files plus the generation, cascade and policy-calendar suites are green at the accepted head."
    command: "PYTHONPATH=. python3 -m pytest tests/test_fda_supply_probes.py tests/test_fda_supply_probes_t02r.py tests/test_fda_supply_probes_t02r2.py tests/test_fda_supply_probes_t02r3.py tests/test_fda_supply_probes_t01r.py tests/test_fda_supply_probes_final.py tests/test_fda_shortages_generation.py tests/test_foresight_cascade.py tests/test_policy_calendar.py -q -p no:cacheprovider"
    result: "135 passed at 9abf409a"
  - claim: "The PR introduces no contract-delta and its exclusive job validates."
    command: "python3 scripts/check_contract_delta.py --base origin/main; python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only; PYTHONPATH=. python3 -m pytest tests/test_ci_pack.py -k 'exclusive or curated or contract or legacy_jobs' -q"
    result: "contract-delta 0 introduced (1 inherited); Validated 229 legacy jobs; 16 passed"
  - claim: "Independent Opus acceptance at the exact head."
    command: "reviewer child ROUTE review / MODE READ_ONLY at 9abf409a; end-to-end truth path re-executed through the real seams"
    result: "ACCEPT — 0 blockers, 0 majors, 3 records-level minors (research/healthcare/hc_program/reviews/OPUS_D1_ACCEPTANCE_2026-09-24.md)"
  - claim: "No lane pushed to main; every frozen probe file is seat-authored only."
    command: "git log origin/main --author='Claude Code' --since=2026-09-24T10:00Z; git log --format=%an -- 'tests/test_fda_supply_probes*.py' | sort -u"
    result: "no lane-identity commits on main; only 'Sol CEO' (the seat's git identity)"
  - claim: "The accepted head was two days stale at the merge window: main had to be merged in and the re-run found one wall-clock-rotted test, repaired by the seat."
    command: "git merge origin/main (conflict: tests/test_ci_pack.py CURATED_EXCLUSIVE only, resolved additively = f9258b0d); PYTHONPATH=. python3 -m pytest <the job's eight suites> -q; python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only"
    result: "127 passed at 4a6cf768 (probes 40 + generation 25 + cascade 62 — identical counts to 9abf409a); validate-only exit 0, 236 legacy jobs, healthcare-fda-supply in scope; repair 4a6cf768 anchors the fixture to the clock compute_fda_scarcity reads (R-D1-MERGE-01); the six frozen probe files untouched"
  - claim: "PR #7930 merged."
    command: "gh pr view 7930 --json state,mergedAt,mergeCommit"
    result: >-
      state MERGED, mergedAt 2026-09-27T02:45:57Z, mergeCommit
      1c85f27bfe7e3bcbbb7ce323a2bdab0839527c59 — squash-merged by the seat on concluded green
      (pending=0, CLEAN/MERGEABLE; sole red = the fleet-wide
      ci-authority/codex/merge-queue-pilot inactive-base-context check that is red on every
      sibling carrier); 15 files, +3993/-293;
      `git merge-base --is-ancestor 1c85f27bfe7e origin/main` exits 0
unverified:
  - claim: "The nightly drip receipt line `fda_shortages: observation qualified=... source_generation=...` appears in the next daily run log and the sidecar data/fda/shortages.parquet.observation.json is written by the nightly."
    what_would_verify: >-
      EXACTLY ONE lane emits it. `scripts/build_foresight.py` is the sole production caller of
      fetch_shortages / format_observation_receipt, and the call sits behind `_no_drip()`
      (RENDER_NO_DRIP=1). Verified 2026-09-26 by reading every call site: render.yml step
      "re-render pages from committed data" (L763) and engine-render.yml step L369 both SET
      RENDER_NO_DRIP=1 in the same step that defines `foresightpage()`, so those lanes never
      emit the receipt and never persist the sidecar (they discard data/ writes by design).
      The nightly does: daily.yml step "run regime engine + build dashboard + daily brief
      (resilient)" (L2250, sentinel UNSET) runs `bash scripts/ci/daily_engine_regime_dashboard.sh`,
      whose L240 is `run_py "thematic foresight desk (build_foresight)" scripts.build_foresight`.
      So: open the newest completed daily.yml run, that step's log, and grep
      `fda_shortages: observation`; then `git show origin/main:data/fda/shortages.parquet.observation.json`
      after the nightly's `engine: regime update <date>` commit (written by
      scripts/ci/daily_engine_commit_outputs.sh:210). DO NOT conclude the drip is dead from a
      render.yml log — it is sentinel-skipped there by design. Cadence evidence: the committed
      parquet's max `fetched_utc` advanced 2026-09-26T07:07:08Z -> 17:43:51Z across the two
      `engine: regime update 2026-09-26` commits (49b379ee -> 5e921b1c), i.e. the drip runs ~2x/day.
  - claim: "The rendered foresight chip on the deployed site shows a truthful state in EN and ZH, dark and light."
    what_would_verify: "The covering lane is render.yml run 36289463335 (event push, headSha 1c85f27bfe7e, queued 2026-09-27T02:46:00Z behind in-flight run 36265067738 — never cancel or re-run either). Once it concludes success, read the Healthcare theme's `fx-chip feed-*` row in the deployed site/foresight.html in EN and ZH, dark and light, from an EXTERNAL browser lane (not the seat). EXPECT TWO STAGES and do not read stage one as a defect: this first post-merge render runs BEFORE any nightly has written the observation sidecar, so the parquet is still legacy-with-no-capture and the chip legitimately renders the `capture time unknown` freshness form rather than `source generation <gen>`; the `source generation` form can only appear after the first nightly drip writes data/fda/shortages.parquet.observation.json. What the render DOES prove at stage one is the truthful composition copy and the new glyph: no banned substring, no literal None/nan, and a MIXED label that names only the states present (R-D1-MERGE-03)."
unresolved:
  - "D2–D4 remain held until #7870 (shared theme-graph/evidence/rights foundation) lands on main with one accepted pin; then re-commission a scoped independent review before any D2 write (per the R1 review's HOLD)."
  - >-
    DISCLOSURE DELTA measured against the LIVE surface on 2026-09-26 (not a blocker, not a
    re-open of the accepted design — fold into the same D2/D3 engine lane as the three
    acceptance minors). main's live site/foresight.html renders exactly one such chip:
    `<span class="fx-chip feed-warn" title="3 active shortage record(s) - demand exceeds supply
    (drove band: liraglutide; no records: semaglutide, tirzepatide)">[pill] FDA shortage ACTIVE
    (3 records)</span>`. D1 correctly deletes the banned "demand exceeds supply" (and the
    RESOLVED branch's "glut tell: supply constraint lifted", three banned substrings in one
    string, engine/fda_scarcity.py:158-170 on main) and the visible label GAINS provenance
    ("source generation <gen>") and a ZH half. But the molecule-level coverage the old title
    carried - which molecule drove the band, and which configured molecules have NO records -
    now lives only in summary.coverage.molecules_checked, which templates/foresight.html.j2
    never renders. "no records: semaglutide, tirzepatide" is a NULL DISCLOSURE, and the title
    attribute is this component's only hover tier, so the null is no longer printed anywhere
    user-visible. It cannot simply be re-appended to the title: _chip_rationale raises on
    non-ASCII by design (house law forbids translated text in title=), so a longer English
    title would have no ZH counterpart. The right home is a Tier-2 receipt or popover on the
    theme detail surface, which is D2/D3 territory. Recorded so the next reviewer does not
    read it as a silent regression: it was measured, it is intentional for D1, and it is owed."
  - "Records-level minors from the acceptance review (unreachable no-digest read guard; unreachable else at engine/fda_scarcity.py:~309; collapsed _UNAVAILABLE rationale) — fold into the first D2/D3 engine lane, never a standalone PR."
next_actions:
  - "Confirm the nightly drip receipt and the sidecar on main after the next daily run; report PRODUCTION_PROOF on #7788 only then."
  - "When #7870 merges: pin its head, commission a scoped Opus review of D2 (T03 v1.1 shared branch consumption, T04 private Research Vault binding — note the vault store falls back to the PUBLIC bucket when R2_RESEARCH_* are unset, so the binding lane needs a fail-closed privacy gate; T05 Healthcare profile on the common POST routes per the per-sector precedent), then lanes hc_t03/hc_t04/hc_t05 in that order on a fresh carrier from main."
  - "D3 T06 (GLP-1 five-part explanation) and D4 T07 (correction + non-metabolic mechanism) after D2; T08 adjudication per release."
do_not_redo:
  - "Never re-ACK #7788 (PICKUP_ACK 5811997064) or re-START (5812282470); never implement on the research branch or on #7870."
  - "Never rebuild the shared foundation (theme graph / evidence / rights vocabularies) — consume #7870 when it lands."
  - "Do not reopen the D1 rulings: R-T01-12 (no invented capture-age limit) stands; the reviewer's staleness-budget probe was lawfully removed; the t02r2 generation-less probe was lawfully amended to the seam ruling."
  - "Do not add a test that imports scripts.build_foresight into the exclusive job's suites — it smears the closure (round-2 defect)."
danger_areas:
  - "GLM lanes: one long exec degenerates (r1 timed out at 7200 s with an 8-byte transcript) — every packet carries commit-and-push-per-step; a lane that returns in minutes with an empty lane dir was REFUSED (host load gate), not done."
  - "The marker-count admission dispatcher cannot see host load; mb refused at load1 93. m1 was the reliable host at the end of D1."
  - >-
    A status chosen by a DISJUNCTION needs its copy checked against every disjunct.
    summarize_supply picks MIXED for `current and (resolved or discontinued)`, but the label and
    rationale hard-coded "resolved", so the live feed (current=9, resolved=0, discontinued=5)
    rendered "mixed - current 9 / resolved 0" and claimed the FDA "reports both current and
    resolved shortages" while hiding five discontinuations. Every MIXED fixture in the eight
    suites used current + resolved, so six Opus rounds and an exact-head ACCEPT all missed it.
    Before merging any change to a data-driven consumer, render the COMMITTED production
    artifact through the engine in the post-merge state (sidecar absent) - the ten-line recipe
    is in DSC:A-SYNTHETIC-FIXTURES-NEVER-REACHED-THE-BRANCH-THE-LIVE-FEED-TAKES. R-D1-MERGE-03."
  - "A copy-only or translation-only edit can red a DESIGN pack. `check_design_system.py --mode enforce-added` scores the lines a diff ADDS, so touching a line adopts its inherited debt: adding this chip's ZH label re-presented the line's years-old 💊 as a new forbidden decision and failed ci-pack-8 → ci-gate. Reproduce the gate against the FULL PR diff before pushing any template edit, and repair by moving to the sanctioned glyph band (U+2600–27BF, reported-but-never-blocking) rather than stripping the icon — DSC:A-DESIGN-RATCHET-REPORTS-WIDER-THAN-IT-BLOCKS, R-D1-MERGE-02."
  - "legacy-jobs.yml is contested by many open PRs; a non-unique anchor silently no-ops a patch (8654985e's message claimed wiring that only landed in 14da0762) — patch inside the job block and verify with grep before committing."
  - "A GLM lane reviewer's PASS/FIX_REQUIRED is not the verdict; exact-head Opus red-teams found real blockers after two lane PASSes (T01 r1/r2)."
  - "`DSC:A-WALL-CLOCK-AGE-ASSERTION-PASSES-ONLY-ON-ITS-AUTHORING-DAY` — an ACCEPTED head decays while the PR waits. `engine/fda_scarcity.compute_fda_scarcity` reads the wall clock, so a test that pins its fixture to a calendar date and asserts a fixed `captured N d ago` passes only on its authoring day — one such test went red two days after acceptance (R-D1-MERGE-01). Re-run the job's suites on the merged head before every merge, and never trust an acceptance run as proof for a later head."
  - "`DSC:A-CONFLICTING-ARMED-PR-WAITS-IN-SILENCE` — a conflict is SILENT: the sweeper refuses an armed PR with `mergeable: CONFLICTING` without a `merge-blocked` label or a comment, so read mergeable/mergeStateStatus before suspecting the sweeper (R-D1-MERGE-00). `tests/test_ci_pack.py` CURATED_EXCLUSIVE is the hot spot — every sector program registers its exclusive job at the same place; resolve additively."
prs: [7788, 7930, 7928, 7933, 7948]
decisions: []
discoveries: []
---

# GMI Healthcare — D1 handoff (2026-09-24)

Cold-stranger summary: D1 (T02 + T01) shipped on PR #7930 after five independent Opus review rounds; every
accepted behaviour is pinned by a seat-frozen probe file that no lane may edit. Live proof owed: the next
nightly's drip receipt and the rendered chip. D2–D4 wait for #7870.
