# A36 coverage remeasure — 2026-10-20 (seat run, local, no network)

Inputs: census r3d outputs (ubuntu1 `~/lanes/out/fif-c2tier-20261018/`, read-only copy):
`coverage_manifest_draft.json` sha256 prefix `eb55b7c5286d6fee3600` (= thresholds `census_identity.manifest_draft_sha256_prefix`),
`slots.csv`, companyfacts cache 3022 files (cutoff 2026-10-18T00:00:00Z, source_generation `census-20261018-2026-10-18T20:47:45Z`).
Registry/writer at fold head 604be72b (metrics dir identical to origin/main 0cfc0d97).

Commands (session tree):
```
python3 scripts/fif_coverage_writer.py rewrite --base-manifest <draft> --slots <slots.csv> --facts-cache <cache> \
  --recorded-at 2026-10-20T12:50:00Z --out coverage_manifest_20261020.json --repo-root <tree>     # rc=0, cells_rewritten=125000
python3 scripts/fif_coverage_proof.py prove --manifest coverage_manifest_20261020.json \
  --thresholds config/fundamental_forensics/coverage/c2_thresholds_v1.json --proved-at 2026-10-20T12:50:00Z --print   # rc=0
```
Output manifest sha256 prefix `8af57eafa805a2d6962f`.

| tier | members | issuers passing | target | field presence | rate | bands (complete/high/partial/low) | withheld (formula inputs absent) | stale (companyfacts missing accession) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deep | 250 | 0 | 250 | 32,267 / 50,000 | 64.5% | 0 / 1 / 196 / 53 | 5,968 | 1,360 |
| core | 1,000 | 0 | 1,000 | 63,202 / 100,000 | 63.2% | 0 / 2 / 742 / 256 | 12,259 | 4,007 |

Prior census r3d (2026-10-18, FIF_C2_COVERAGE_FREEZE.md): deep 63.6%, core 63.0%, 0 issuers complete. Delta at the 10-20 rule clock: deep +0.9pt, core +0.2pt, still 0/250 and 0/1,000.

Failing reasons (core): absent_no_alias_fact 20,312 · formula_inputs_absent 12,259 · companyfacts_missing_accession 4,007 · absent_period_mismatch 100 · slot_absent 120.
Failing reasons (deep): absent_no_alias_fact 10,373 · cell_missing 9,500 (specialist/packet/journey cells not emitted by the census writer) · formula_inputs_absent 5,968 · companyfacts_missing_accession 1,360 · missing_member 168 · absent_period_mismatch 32.

Acceptance: eligible=false; blockers = census_identity_mismatch (rewritten manifest no longer carries the draft prefix — expected for a rewrite), core_target_not_met, deep_target_not_met, legacy_field_id_alias (`package.` → 3,000 cells aliased), manifest_draft, manifest_unattested.

Measured tier proposal (frozen 250/1,000 target NOT met; the target is not worker-editable): per-issuer field-presence band —
deep: high 1 · partial 196 · low 53; core: high 2 · partial 742 · low 256; zero complete in either tier.
Repair order unchanged from the freeze: (a) debt-family mapping (largest absent_no_alias_fact share), (b) bank/insurer/REIT via PK11/PK10, (c) SNOW D0 gap; plus the deep-tier `cell_missing` 9,500 (specialist/packet/journey cells) which the census writer does not emit — those need the twelve-pack fold (#9872) wired into the coverage writer (cov-wire lane, after #9799).

Status for Z0 A36: live_proof obligation → PARTIAL (remeasured by manifest at the 10-20 clock from the 10-18 census cache, not from the 10-20 scheduled publish's own companyfacts pull); a further remeasure after #9794/#9799 land and the 10-21 00:00Z `available_at` clock = PENDING_LIVE follow-up. implementation_gap obligation (measured tier proposal) → MET by this record.
