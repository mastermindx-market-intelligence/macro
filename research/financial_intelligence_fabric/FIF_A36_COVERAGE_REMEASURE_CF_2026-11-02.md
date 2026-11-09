# A36 coverage remeasure with a fresh companyfacts pull — 2026-11-02 (lane run)

## Inputs

Base manifest `~/lanes/out/fif-c2tier-20261018/coverage_manifest_draft.json` (sha256 prefix
`eb55b7c5286d6fee3600`, verified before any run) with `~/lanes/out/fif-c2tier-20261018/slots.csv`.
The comparison cache is the old 2026-10-18 companyfacts snapshot
`~/lanes/out/fif-c2tier-20261018/cache/` (3,022 gzip files, 2026-10-18 cutoff). The fresh pull
lives in the new cache dir `~/lanes/out/fif-a36cf-20261102/cache/` holding 1,000 distinct issuer
CIKs — every distinct issuer CIK of both tier memberships, each stored under the writer's
`companyfacts_cache_key`. The fetch was performed by this lane in two processes (an earlier
interrupted process, then the seat's resume with the identical unchanged script); this run made
no network request. The attempts ledger records 1,001 request attempts for the 1,000 keys (one
in-flight request was lost when the first process ended and was re-requested by the resume; no
retry flags). Fetch ledger outcomes: 989 `ok` rows plus 395 `ok_resume` rows — the resume
re-verified the interrupted process's 395 keys, and 11 of those keys appear only as `ok_resume`
because the first process's ledger buffer was lost — so each key counted once gives 1,000
fetched, with 0 `not_found`, 0 `bad_payload`, 0 HTTP failures and no 403/429 (stop reason null).
First request 2026-11-02T15:00:09Z (first process), resume process first request
2026-11-02T15:08:59Z, last request 2026-11-02T15:19:36Z. User agent
`Mastermind FIF research lane fif-lane@mastermind.local`, one request in flight at a time and at
least 1.05 s between request starts; the minimum start-to-start gap measured from the attempts
ledger is 1.05 s. Freshness, computed from files only, per fetched issuer: 430 issuers whose
newest `filed` date is newer than in the old cache file, 570 unchanged, 0 with no old file;
newest `filed` date seen overall 2026-11-02.

## Commands

Clock `2026-11-02T15:21:00Z` (captured once) used for every `--recorded-at` and `--proved-at`,
run from worktree `ac9b6d5ff47680e9bb43162d2227c1e69347fc87`:

```
python3 scripts/fif_coverage_writer.py rewrite --base-manifest ~/lanes/out/fif-c2tier-20261018/coverage_manifest_draft.json --slots ~/lanes/out/fif-c2tier-20261018/slots.csv --facts-cache ~/lanes/out/fif-a36cf-20261102/cache --recorded-at 2026-11-02T15:21:00Z --out /tmp/fif-a36cf-r1/manifest_cf_noflag.json --repo-root /home/longr/lanes/wt/fif-a36cf-u1-20261102-r4
# rc=0, cells_rewritten=125000, facts_unavailable_issuers=0

python3 scripts/fif_coverage_writer.py rewrite --base-manifest ~/lanes/out/fif-c2tier-20261018/coverage_manifest_draft.json --slots ~/lanes/out/fif-c2tier-20261018/slots.csv --facts-cache ~/lanes/out/fif-a36cf-20261102/cache --recorded-at 2026-11-02T15:21:00Z --out /tmp/fif-a36cf-r1/manifest_cf_np.json --repo-root /home/longr/lanes/wt/fif-a36cf-u1-20261102-r4 --np-linkbases ~/lanes/stage/fif-a36np-20261102
# rc=0, cells_rewritten=125000, facts_unavailable_issuers=0

python3 scripts/fif_coverage_proof.py prove --manifest /tmp/fif-a36cf-r1/manifest_cf_noflag.json --thresholds config/fundamental_forensics/coverage/c2_thresholds_v1.json --proved-at 2026-11-02T15:21:00Z --print
# rc=0  (JSON report written via --out to /tmp/fif-a36cf-r1/proof_cf_noflag.txt; the --print block
#        goes to stderr by the tool's design and is captured at proof_cf_noflag_print.txt)

python3 scripts/fif_coverage_proof.py prove --manifest /tmp/fif-a36cf-r1/manifest_cf_np.json --thresholds config/fundamental_forensics/coverage/c2_thresholds_v1.json --proved-at 2026-11-02T15:21:00Z --print
# rc=0  (JSON report /tmp/fif-a36cf-r1/proof_cf_np.txt; print block proof_cf_np_print.txt)
```

`facts_unavailable_issuers=0` in both rewrite runs: every one of the 1,000 issuers had a fresh
cache file, so no issuer kept its base cells.

Output manifests: `/tmp/fif-a36cf-r1/manifest_cf_noflag.json` sha256 prefix `ddfb3f23595bd4a2242d`;
`/tmp/fif-a36cf-r1/manifest_cf_np.json` sha256 prefix `b716847f5dab99351286`.

## Results

Rate = present / applicable; presence = present / total cells (total = applicable + not
applicable). Withheld = `formula_inputs_absent`; stale = `companyfacts_missing_accession`;
NA = not-applicable cells by basis (kernel / not_presented / class). Bands are
complete / high / partial / low; complete_strict = 0 in every row. "old" = the 2026-11-02
remeasure on the 2026-10-18 cache (`/tmp/fif-a36cov-r1/`), "fresh" = this run.

| tier × run | members | passing | target | presence | rate | bands c/h/p/l | withheld | stale | NA k/np/cl | failing reasons (count) |
|---|---|---|---|---|---|---|---|---|---|---|
| deep old-noflag | 250 | 0 | 250 | 32279/50000 | 64.6% | 0/1/196/53 | 5968 | 1360 | 0/0/0 | absent_no_alias_fact 10361, cell_missing 9500, formula_inputs_absent 5968, companyfacts_missing_accession 1360, missing_member 168, absent_period_mismatch 32 |
| deep old-NP | 250 | 0 | 250 | 32622/50000 (65.2%) | 66.6% | 0/7/192/51 | 5518 | 1360 | 107/926/0 | cell_missing 9500, absent_no_alias_fact 9435, formula_inputs_absent 5518, companyfacts_missing_accession 1360, missing_member 168, absent_period_mismatch 32 |
| deep fresh-noflag | 250 | 0 | 250 | 32772/50000 | 65.5% | 0/1/202/47 | 5914 | 720 | 0/0/0 | absent_no_alias_fact 10561, cell_missing 9500, formula_inputs_absent 5914, companyfacts_missing_accession 720, missing_member 168, absent_period_mismatch 33 |
| deep fresh-NP | 250 | 0 | 250 | 33114/50000 (66.2%) | 67.7% | 0/7/197/46 | 5461 | 720 | 111/943/0 | cell_missing 9500, absent_no_alias_fact 9618, formula_inputs_absent 5461, companyfacts_missing_accession 720, missing_member 168, absent_period_mismatch 33 |
| core old-noflag | 1000 | 0 | 1000 | 63230/100000 | 63.2% | 0/2/743/255 | 12259 | 4007 | 0/0/0 | absent_no_alias_fact 20284, formula_inputs_absent 12259, companyfacts_missing_accession 4007, slot_absent 120, absent_period_mismatch 100 |
| core old-NP | 1000 | 0 | 1000 | 64046/100000 (64.0%) | 65.7% | 0/32/713/255 | 11016 | 4007 | 427/2107/0 | absent_no_alias_fact 18177, formula_inputs_absent 11016, companyfacts_missing_accession 4007, slot_absent 120, absent_period_mismatch 100 |
| core fresh-noflag | 1000 | 0 | 1000 | 65189/100000 | 65.2% | 0/2/794/204 | 12009 | 1687 | 0/0/0 | absent_no_alias_fact 20893, formula_inputs_absent 12009, companyfacts_missing_accession 1687, slot_absent 120, absent_period_mismatch 102 |
| core fresh-NP | 1000 | 0 | 1000 | 66028/100000 (66.0%) | 67.8% | 0/33/764/203 | 10736 | 1687 | 434/2162/0 | absent_no_alias_fact 18731, formula_inputs_absent 10736, companyfacts_missing_accession 1687, slot_absent 120, absent_period_mismatch 102 |

(Presence percentages are shown only where they differ from the rate, i.e. where NA cells exist.
Old manifests: noflag `e40f721a499d898f91d0`, NP `9711cf863773297ad57b`; both rewrote 125000
cells with 0 facts-unavailable issuers.)

### Deltas (fresh minus old)

Members, passing, targets and total cells are unchanged (+0) everywhere; pass stays 0 in all
eight cells.

No-flag family:

- deep: present +493, rate +1.0 pp, stale −640, withheld −54, bands partial +6 / low −6,
  absent_no_alias_fact +200, absent_period_mismatch +1 (cell_missing, missing_member +0).
- core: present +1959, rate +2.0 pp, stale −2320, withheld −250, bands partial +51 / low −51,
  absent_no_alias_fact +609, absent_period_mismatch +2 (slot_absent +0).

NP family:

- deep: present +492, applicable −21 (NA +21: kernel +4, not_presented +17), rate +1.0 pp,
  stale −640, withheld −57, bands partial +5 / low −5, absent_no_alias_fact +183,
  absent_period_mismatch +1 (cell_missing, missing_member +0).
- core: present +1982, applicable −62 (NA +62: kernel +7, not_presented +55), rate +2.1 pp,
  stale −2320, withheld −280, bands high +1 / partial +51 / low −52, absent_no_alias_fact +554,
  absent_period_mismatch +2 (slot_absent +0).

### Frontier (run B = fresh-NP, beside old-NP)

Failing cells per issuer (deep from the prover's failed-field accounting, which includes the
9,500 `cell_missing` deep fields that are not manifest cells; core from tier=core manifest
cells; 250 and 1,000 issuers respectively):

| run | tier | 0 | 1 | 2 | 3–5 | 6–10 | 11–20 | 21–50 | >50 |
|---|---|---|---|---|---|---|---|---|---|
| old-NP | deep | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 246 |
| fresh-NP | deep | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 246 |
| old-NP | core | 0 | 0 | 1 | 14 | 30 | 231 | 486 | 238 |
| fresh-NP | core | 0 | 0 | 1 | 14 | 31 | 246 | 522 | 186 |

The fresh pull shifts 52 core issuers out of the >50 bucket (238 → 186) into 11–20 and 21–50,
and moves the 6–10 bucket from 30 to 31; the closest core issuer still fails 2 cells, so the
0 and 1 buckets stay empty and no issuer completes.

Top failing fields by failing-cell count (field name, count; top 10):

- fresh-NP deep: statement:balance_sheet 1000, statement:cash_flow 1000,
  statement:income_statement 1000, metric:operating_expenses 830, metric:cash_to_total_debt 823,
  metric:net_debt 823, metric:debt_to_equity 817, metric:total_debt 802,
  metric:short_term_investments 693, metric:gross_margin 640.
- old-NP deep: statement:balance_sheet 1000, statement:cash_flow 1000,
  statement:income_statement 1000, metric:operating_expenses 830, metric:cash_to_total_debt 824,
  metric:net_debt 824, metric:debt_to_equity 817, metric:total_debt 803,
  metric:short_term_investments 698, metric:gross_margin 644.
- fresh-NP core: metric:cash_to_total_debt 1609, metric:net_debt 1609, metric:debt_to_equity
  1602, metric:total_debt 1576, metric:operating_expenses 1524, metric:short_term_investments
  1445, metric:short_term_debt 1254, metric:gross_margin 1219, metric:gross_profit 1172,
  metric:long_term_debt_current 1051.
- old-NP core: metric:cash_to_total_debt 1620, metric:net_debt 1620, metric:debt_to_equity
  1612, metric:total_debt 1587, metric:operating_expenses 1539, metric:short_term_investments
  1465, metric:short_term_debt 1277, metric:gross_margin 1245, metric:gross_profit 1200,
  metric:long_term_debt_current 1065.

## Acceptance

Both proofs (fresh no-flag and fresh NP) report, verbatim:

```
acceptance:     eligible=false  blockers=census_identity_mismatch,core_target_not_met,deep_target_not_met,legacy_field_id_alias,manifest_draft,manifest_unattested
```

## Status

The frozen target — 250 deep and 1,000 core issuers complete — is **not met**: both proofs
report 0/250 deep and 0/1000 core issuers passing, on the fresh cache, with or without the
not-presented linkbases. The target is frozen and not worker-editable. A fresh public
companyfacts pull does move real coverage — core present cells +1,982 (NP family, rate +2.1 pp)
and stale `companyfacts_missing_accession` cells down from 4,007 to 1,687 core and 1,360 to 720
deep, with 52 core issuers leaving the >50-failing-cells bucket — but it completes no issuer:
even the closest core issuer still fails 2 cells. The remaining largest failing reasons on the
fresh NP run are, for core, `absent_no_alias_fact` (18,731), `formula_inputs_absent` (10,736)
and residual `companyfacts_missing_accession` (1,687), and for deep, `cell_missing` (9,500),
`absent_no_alias_fact` (9,618), `formula_inputs_absent` (5,461) and `companyfacts_missing_accession`
(720). This is a local manifest run against a fresh public companyfacts pull — not production
and not live proof; no production or live claim is made here.
