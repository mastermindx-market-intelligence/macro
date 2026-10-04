---
workstream: WS:TREND-PERSISTENCE
session: claude/ssd-tp-wave-c-sector-substrate-efcf6cc432cf2832
model: fable
ended_because: complete
prs: [8403]
decisions: [DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B]
discoveries: [DSC:IC-GATES-AFTER-RANK-LINEAR-CONTROLS-DO-NOT-SEPARATE-PATH-FEATURES-FROM-VOLATILITY]
mission: >
  Wave C-0. Build the precondition the closed family named for any Wave C (group persistence)
  reopening: a sector label for every S&P 1500 leaver, with the honesty of the label carried in
  the artifact itself. Chairman instruction 2026-10-03: recover the dead m2 session and continue
  the project forward as the new CEO; do not use the Mastermind Executive.
state_before: >
  Family CLOSED at Wave B (Mastermind PR 1155 merged 1c5bc0c3, records macro PR 8355 merged
  51cd2be7). The readout recorded "current sector map covers 3 of 1,083 leavers" and no
  point-in-time sector history existed. Nothing in macro produced sector labels for former
  index members.
changed:
  - path: collectors/sp1500_pit_sectors.py
    what: New collector. One row per ticker ever in data/breadth/sp1500_pit_membership.parquet (2589 tickers, 1083 leavers) with an 11-sector label, basis (gics_current / sic_current / sic_derived / unlabeled), label_join (ticker / cik), sic, sic_desc, cik, cik_method, label_asof, and a constant era_correct=False column. Leavers are labeled ONLY through the EDGAR CIK bridge (dead_name_cik.json methods edgar_fts/seed), SIC mapped text-first via scripts/build_sector_map tables. Bounded, cached SEC submissions lookups; never runs in CI; no dag node.
  - path: data/breadth/sp1500_pit_sectors.parquet
    what: The substrate, produced by ONE live run on 2026-10-04 (label_asof 2026-10-04).
  - path: data/breadth/_sp1500_pit_sectors_coverage.json
    what: Coverage receipt of that run (numbers below).
  - path: data/breadth/_sp1500_pit_sic_cache.json
    what: This collector's own SIC cache (raw SEC sic/sicDescription/name per CIK, blanks included) so re-runs make no network calls. Only writer is this module; data/edgar/cik_sic.json is never written.
  - path: tests/test_sp1500_pit_sectors.py
    what: 24 offline tests; every test redirects data_dir to tmp_path and stubs the SEC fetch.
  - path: .github/ci/legacy-jobs.yml
    what: Wires tests/test_sp1500_pit_sectors.py into the synapse-read-gate job (the job that owns the EDGAR collector suites and the registry-integrity check). Added after the PR's first ci.yml run went red on contract-delta and ci-control-plane-contracts, both for the same cause, a new suite named by no run step.
  - path: config/synapse.yml
    what: Registry entry sp1500-pit-sectors (display tier, horizon_role context, owner_program engine-fix, no scored surfaces).
  - path: agentos/workstreams/WS-TREND-PERSISTENCE.md
    what: status active, repos add macro, wave C-0 done (PR 8403), wave C todo pending a NEW pre-registration, owns_paths and next_action updated.
verified:
  - claim: Leaver coverage after the live run is 281/1083 (sic_derived 281, gics_current 0, sic_current 0, unlabeled 802); all-ticker coverage is 1786/2589.
    command: "python3 -c \"import json;print(json.load(open('data/breadth/_sp1500_pit_sectors_coverage.json')))\"  (at b4cd9990c9c3)"
    result: "basis_counts_leavers=(gics_current  0, sic_current  0, sic_derived  281, unlabeled  802); leavers_with_cik=282; leavers_labeled_by_ticker_string=0; leavers_labeled_by_cik=281; network_lookups_performed=273; network_lookups_failed=0; sic_blank_after_fetch=0; era_correct_count=0"
  - claim: No leaver carries a ticker-string label, and era_correct is False on every row.
    command: "python3 -c \"import pandas as pd;f=pd.read_parquet('data/breadth/sp1500_pit_sectors.parquet');lv=f[f.is_leaver];print((lv.label_join=='ticker').sum(), f.era_correct.any())\""
    result: "0 False"
  - claim: The collector, its tests and the registry pass offline on the CI interpreter.
    command: "python3.12 -m pytest tests/test_sp1500_pit_sectors.py -q && python3 -m pytest tests/test_build_sector_map.py tests/test_gh_annotation_line_start.py -q && python3 scripts/check_synapse_registry.py"
    result: "24 passed; 70 passed; synapse registry OK — 647 artifacts registered, 0 violations"
  - claim: The artifact survived five independent Opus review passes (two refute-and-repair rounds on the frozen spec, two verify passes on the seat rulings R1-R6, plus the mutation-tested final pass) before the live run.
    command: "workflow runs wf_51c33cf5-849 and wf_b5ad7409-015 in the seat's session transcript (journal.jsonl per run)"
    result: "final blocking findings: 0 after the seat applied the R3 null-ticker fix with two pinning tests"
  - claim: The Wave C-1 pre-registration quotes the committed Mastermind pins (B2 result e0b177cb...a443 with model B2 means 0.49461154432499976 / 0.5337496007208158, B2 prereg 79764bf5...0aa, V2 rev 2 2882865d...2d17, protocol ab0ed7fe...0412, readout 7013662f...5443, V2 panel 48cb5e76...f178) and the C-0 snapshot digests.
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/contents/<path> (one call per file, master) then shasum -a 256; python3 -c json.load on research/data/trend_persistence_b2_result.json"
    result: "every digest and both means match the document text; Mastermind PR 1226 head a703cc7c carries the file at sha256 f22b0cee...bf4cc"
unverified:
  - claim: The 267 edgar_fts and 15 seed CIKs in data/edgar/dead_name_cik.json identify the historical filer rather than a later reuser of the ticker.
    what_would_verify: Audit the FTS corroboration gates in data/edgar/_dead_name_fts.json against the membership window (filing dates inside start_date..end_date) for a sample, or a name match against the S&P announcement feed where it exists.
  - claim: The SIC->GICS-style mapping is the membership-era GICS sector.
    what_would_verify: Nothing on disk; it is as-of-now by construction (era_correct=False). Only a licensed historical GICS source could close this.
unresolved:
  - 802 of 1083 leavers remain unlabeled: 801 have no CIK (no verified company name on disk; 663 carry only an unverified FTS top-name candidate), the rest have a CIK whose SEC SIC is blank or unmappable (sic/sic_desc are still recorded on those rows).
  - Labels are as-of-now. A reclassified company (e.g. a 2018 GICS Communication Services move) carries its CURRENT sector, not the one it had while a member.
next_actions:
  - Merge Mastermind PR 1226 (squash at exact head a703cc7c8c5cd3d923772a859a6a10cbf6dcf490; the test check is the only required one) and verify research/TREND_PERSISTENCE_PREREG_C1.md on origin/master (sha256 f22b0cee218c381dd3fd078d67301c985eb9415faa0e75ffdc57d520374bf4cc, 47,329 bytes). Its first master commit is the freeze commit; that commit's UTC date starts the C2 confirmation window.
  - Build research/trend_persistence_group.py and its tests in Mastermind against the C1 document (section 11 pins; the closed-list constants block is machine-written at freeze and is the only text appended), run the C1 development pass exactly once on the embargoed dates (every label exits on or before 2026-06-02), record the attempt publicly on its PR, and never read a confirmation date before n_read is reached.
  - If coverage must rise, the only lawful lever is more CIK resolutions in collectors/edgar_deadnames.py (edgar_fts/seed methods); company_tickers/polygon resolutions are current-universe lookups and are deliberately never bridged for leavers.
do_not_redo:
  - Do not relabel leavers by ticker string from ticker_sectors.parquet or profiles.parquet; the readout's "3 of 1,083" were recycled tickers (ECHO/FI/MMC) and never real coverage.
  - Do not re-run the collector expecting more coverage; re-runs read the own cache and only fetch CIKs that failed (404/retries). Coverage moves only when dead_name_cik.json gains edgar_fts/seed resolutions.
  - Do not add this collector to dag.yml or a workflow; it is on-demand, display-tier substrate.
  - Everything in the 2026-10-03 handoff's do_not_redo still binds (no V2/B2 re-run, no prereg edits, no profile from the 29 tests).
  - Do not spawn Opus, Sonnet or Haiku workers for this program; the operator ruled on 2026-10-04 that drafting, review and analysis happen in the Fable main loop. The data_honesty analyst lens that returned nothing was covered by the seat's own pass, not by a replacement worker.
  - Do not re-synthesize the Wave C design from the analyst digests or edit research/TREND_PERSISTENCE_PREREG_C1.md after its merge; the seat's rulings (gating baseline B*, seven group features, labelled-only primary with two brackets, rel_spy at h 20/60 as the only gated label, n_read power rule, fixed-sequence 0.025, one read) are in the document, and a changed gate needs a new pre-registration.
danger_areas:
  - .github/ci/legacy-jobs.yml is a CI-authority path, so this PR's ci.yml run is the full legacy suite and the merged head carries authority_changed=true; a red on that merged head clears only through a green ci.yml run on a main descendant, never through candidate-era evidence.
  - A write into data/ from a SPARSE worktree truncates committed artifacts; this tree opted into data/ (scripts/worktree_sparse.py add data) before the live run.
  - data/edgar/cik_sic.json is owned by collectors/edgar_emergence.py; the collector reads it and a test pins that its bytes never change.
  - The text-first SIC order is deliberate (scripts/build_sector_map.py convention); range-first mislabels about 12 percent of SICs (UEIC 3651 Household Audio = Consumer Discretionary by text, IT by range).
---

## Context

Wave C-0 exists because the Chairman reopened the project forward after the family closed at
Wave B. It builds only the precondition; it does not reopen the pre-registered family, score
anything, or build a profile. Every label is as-of-now and the artifact says so in its own
columns (`era_correct`, `basis`, `label_join`). Leaver coverage is bounded above by the CIK
bridge (282 of 1083 leavers have a trusted CIK).

## Addendum 2026-10-04 (Wave C-1, same seat)

The Wave C pre-registration the C-0 handoff asked for is written: `research/TREND_PERSISTENCE_PREREG_C1.md`
on Mastermind PR 1226 (branch `claude/ssd-tp-wave-c1-prereg-6f56f95579d01f3b`). It is one authored
document with two parts. C1 is a development pass scored once on the formation dates V2/B2 already used
and is a claim about nothing; C2 fixes every construction, gate and constant now plus the rule that
yields the one constant that cannot be known yet (the forward read size n_read in {48, 96, 144}, power
0.80 at delta* = max(0.008, 0.5 x development mean)), and is read once on formation dates after the
freeze commit. Unlabelled leavers are handled before any scoring, as the C-0 handoff required: the
primary is labelled-only, the two brackets are neutral imputation and current members, and the
"unlabelled" pseudo-sector is forbidden because it is 100 percent future leavers on every date. The
document was drafted, reviewed and checked in the Fable main loop after the operator order of
2026-10-04 (no Opus, Sonnet or Haiku workers). Wave C-2 (instrument plus one C1 run) is not started.


## Addendum 2026-10-04 (Wave C-1 merged, C-2 built, same seat)

Mastermind PR 1226 merged to master as `521720b09be2` through the repository's merge queue; the UTC committer date of that squash commit, 2026-10-04, is the C2 freeze date (interim = freeze + 182 days). The Wave C-2 instrument `research/trend_persistence_group.py` and `tests/test_trend_persistence_group.py` (18 tests, the eight section-11 tests among them) were built in the seat's main loop and opened as Mastermind PR 1230; the C1 development run has NOT been made yet and must be made exactly once from a committed clean tree. Verified: `python3 -m pytest tests/test_trend_persistence_group.py` 18 passed; noncentral t against scipy max |diff| 2.9e-15.
