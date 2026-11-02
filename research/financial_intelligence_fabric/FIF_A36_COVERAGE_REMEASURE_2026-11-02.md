# A36 coverage remeasure — 2026-11-02 (lane run, local, no network)

Inputs: census r3d outputs (ubuntu1 `~/lanes/out/fif-c2tier-20261018/`, read-only copy):
`coverage_manifest_draft.json` sha256 prefix `eb55b7c5286d6fee3600` (= thresholds `census_identity.manifest_draft_sha256_prefix`),
`slots.csv`, companyfacts cache 3,022 files (cutoff 2026-10-18T00:00:00Z, source_generation `census-20261018-2026-10-18T20:47:45Z`).
Writer/proof at lane worktree HEAD `9ac2df51a83` (writer carries the `--np-linkbases` branch; no code edited in this run).
Linkbase stage `~/lanes/stage/fif-a36np-20261102/` (read-only): `index.json` sha256
`870cf9f438fadf09ee4df9ba21c9dcde1d9b04cb2747a71dda514ae3bf136751`, schema `fif.np_linkbases/v1`,
`captured_at` 2026-11-02T06:28:56Z, user agent `Mastermind FIF research lane fif-lane@mastermind.local`,
2,490 entries — 2,226 `ok`, 264 `no_cal_no_pre`. Stage verification (checker in `/tmp/fif-a36cov-r1/`):
all 4,452 role files of the `ok` entries decompressed and their uncompressed sha256 matched the recorded
digests — 0 mismatches, 0 unreadable, 0 path violations.

Capture provenance: the linkbase stage was captured from public EDGAR at no more than 1 request per second by the capture lane's script; the lane's own background capture ended when that lane exited, so the seat relaunched the same script (byte-identical copy) as a detached low-priority process on ubuntu1 writing the same stage. This seat-direct relaunch is recorded as a deviation from lane-only execution.

Commands (rule clock `--recorded-at`/`--proved-at` = 2026-11-02T10:09:00Z, captured once; outputs and proofs in `/tmp/fif-a36cov-r1/`):
```
python3 scripts/fif_coverage_writer.py rewrite --base-manifest <draft> --slots <slots.csv> --facts-cache <cache> \
  --recorded-at 2026-11-02T10:09:00Z --out /tmp/fif-a36cov-r1/manifest_noflag.json --repo-root <tree>   # rc=0, cells_rewritten=125000
python3 scripts/fif_coverage_writer.py rewrite --base-manifest <draft> --slots <slots.csv> --facts-cache <cache> \
  --recorded-at 2026-11-02T10:09:00Z --out /tmp/fif-a36cov-r1/manifest_np.json --repo-root <tree> \
  --np-linkbases ~/lanes/stage/fif-a36np-20261102                                                                 # rc=0, cells_rewritten=125000
python3 scripts/fif_coverage_proof.py prove --manifest <manifest_noflag|manifest_np>.json \
  --thresholds config/fundamental_forensics/coverage/c2_thresholds_v1.json --proved-at 2026-11-02T10:09:00Z --print   # rc=0 for both manifests
```
Output manifest sha256 prefixes (20 hex): no-flag `e40f721a499d898f91d0`, NP `9711cf863773297ad57b`.

| tier / run | members | issuers passing | target | field presence | rate | bands (complete/high/partial/low) | withheld (formula inputs absent) | stale (companyfacts missing accession) | not applicable (not presented) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deep no-flag | 250 | 0 | 250 | 32,279 / 50,000 | 64.6% | 0 / 1 / 196 / 53 | 5,968 | 1,360 | 0 (0) |
| deep NP | 250 | 0 | 250 | 32,622 / 48,967 | 66.6% | 0 / 7 / 192 / 51 | 5,518 | 1,360 | 1,033 (926) |
| core no-flag | 1,000 | 0 | 1,000 | 63,230 / 100,000 | 63.2% | 0 / 2 / 743 / 255 | 12,259 | 4,007 | 0 (0) |
| core NP | 1,000 | 0 | 1,000 | 64,046 / 97,466 | 65.7% | 0 / 32 / 713 / 255 | 11,016 | 4,007 | 2,534 (2,107) |

Field presence and rate are the prover's basis (denominator = applicable cells, N/A excluded; the no-flag runs have no N/A cells so the denominator is the full 50,000 / 100,000). N/A column = not_applicable cells, with the `not_presented_item` share in parentheses; the remainder is `na_basis: kernel` (deep 107, core 427; manifest-wide 2,610 `not_presented_item` + 483 `kernel` over 3,093 cells). On an all-cells denominator the NP rates are 65.2% (deep) and 64.0% (core).

Delta at the 10-20 figures (deep 64.5%, core 63.2%, 0 passing): run A (plain writer, 11-02 clock) reproduces the baseline within rule-clock drift — deep 64.6%, core 63.2%, absent_no_alias_fact 10,361/20,284 vs 10,373/20,312, core bands 743/255 vs 742/256. Run B (governed not-presented rules from the captured linkbases) moves deep to 66.6% (+2.1pt) and core to 65.7% (+2.5pt) on the N/A-excluded basis: present cells +343 (deep, 32,279→32,622) and +816 (core, 63,230→64,046), withheld −450 (deep) / −1,243 (core), absent_no_alias_fact −938 (deep) / −2,135 (core). All of the new present cells are qualified (not-presented-policy labelled): present_strict is unchanged at 31,997 (deep) / 62,765 (core), while present_qualified rises 282→625 (deep) and 465→1,281 (core). Bands shift up inside partial: deep high 1→7, core high 2→32. Still 0/250 deep and 0/1,000 core issuers passing.

Failing reasons, run B, core: absent_no_alias_fact 18,177 · formula_inputs_absent 11,016 · companyfacts_missing_accession 4,007 · absent_period_mismatch 100 · slot_absent 120.
Failing reasons, run B, deep: absent_no_alias_fact 9,435 · cell_missing 9,500 (specialist/packet/journey cells not emitted by the census writer) · formula_inputs_absent 5,518 · companyfacts_missing_accession 1,360 · missing_member 168 · absent_period_mismatch 32.

Acceptance (both runs, verbatim from the proofs): eligible=false; blockers = census_identity_mismatch, core_target_not_met, deep_target_not_met, legacy_field_id_alias, manifest_draft, manifest_unattested.

NP counter block (run B, writer counts, verbatim — counter names and integers only):
```
np_alias_fact_other_accession 622
np_conflicting_value 25
np_formula_outcome:not_applicable 669
np_formula_outcome:present 1745
np_no_linkbase_entry 4008
np_outcome:not_presented 6071
np_outcome:np_children_no_facts 28
np_outcome:np_container_leaf 1905
np_outcome:np_extension_child 8115
np_outcome:np_family_fact 2102
np_outcome:np_family_in_calc 7788
np_outcome:np_family_in_statement_pre 483
np_outcome:np_no_parent 7443
np_outcome:np_no_rule 12015
np_outcome:np_unbalanced 444
np_skipped_amended_slot 558
np_span_not_requested 20
```
(`np_no_linkbase_entry` 4008 = NP attempts whose accession has no `ok` staged entry — count close to, but not verified equal to, the 4,007 stale core cells; 264 staged entries are `no_cal_no_pre` and fail closed.)

Status: the frozen 250-deep / 1,000-core target is NOT met — the proofs state deep 0/250 and core 0/1,000 with `target_met=false` for both tiers in both runs; the target is frozen in the thresholds config and is not worker-editable. The governed not-presented rules move real but modest ground (deep +2.1pt, core +2.5pt N/A-excluded; +343/+816 present cells, all qualified; withheld −450/−1,243) and do not change the largest failing reasons: absent_no_alias_fact remains first (core 18,177, deep 9,435 — debt-family mapping and bank/insurer/REIT families), then the deep-tier cell_missing 9,500 (twelve-pack fold #9872 still to be wired into the coverage writer) and companyfacts_missing_accession (core 4,007, deep 1,360 — not fixable from the 10-18 census cache; needs a newer companyfacts pull). Z0 A36 therefore stays PENDING_LIVE. This is a local manifest run proved against the 2026-10-18 census cache, not a production or live proof.
