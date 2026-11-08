# Leader lineage — read-path admission (Leader Radar display tier + observation history)

**Date:** 2026-10-17. **Decision:** ADMITTED for the Leader Radar display tier and observation history only,
default-off in code, activated by a separate one-line PR. **Who decided:** the temporary owner of the
leader-lineage read-path admission, appointed on 2026-10-17 by Chairman Chris through the RS LEADER Meta-CEO seat.
That appointment replaces the gate in `CONSUMER_SPEC.md`, "the Leader Pivot owner (#8649) has admitted the
read path". #8649 merged on 2026-10-17 and is not changed by this admission.

## 1. What is admitted

| Effect | Where | Gate |
|---|---|---|
| `rows[i].display_chips.leader_lineage` (CONSUMER_SPEC §2 chip) | `leaderradar/radar.json` (payload schema `leader_radar.v2`, additive keys only) | `leader_radar.lineage_enabled` |
| `lineage_roster` (CONSUMER_SPEC §2 roster), placed right after `recovery_roster` | same file | same flag |
| First-observed lineage seals: `lineage_observed_at`, `lineage_observation_json`, `lineage_observation_sha256` | `data/leader_radar/state_history.parquet` (existing rows; no new ledger) | same flag |

The flag accepts the literal `true` only. The code PR ships it `false`. Activation is a separate one-line PR,
following the recovery pattern: #8750 shipped the code default-off, #8804 activated it, and #9530 fixed the clock.

## 2. Invariants (each is a test in the code PR)

1. **Descriptive only.** `authority` is `{may_rank, may_gate, may_size, may_trade, may_alert}` all `false`.
   It is a fresh copy on every chip and on the roster, and it is forwarded, never dropped. No rank, gate, size,
   trade, alert, ordering or promotion input reads any lineage field.
2. **Reconstructed is labelled reconstructed.** `evidence_mode` stays `RECONSTRUCTED_CURRENT_VINTAGE`.
   Every seal carries `source_first_seen_proven: false`. A seal records when *this system* first observed a
   descriptor. It never claims when the market first showed it.
3. **Seals follow the shipped recovery contract.** The rules are those of `merge_recovery_observations`,
   applied to the lineage columns:
   - **Clocks.** `as_of` is the radar's additive clock. `observed_at` is the bake's real `built_at`
     (timezone-aware, UTC on disk).
   - **No overwrite.** A sealed `(date, ticker)` is never overwritten. Disarming stops new captures and
     deletes nothing.
   - **Lagged cuts.** A lagged cut seals that session's existing native row and never mints a row.
   - **Tamper checks.** Partial, retyped, re-hashed, backdated or identity-mismatched seals are refused.
   - **Recovery isolation.** Recovery columns stay byte- and dtype-identical.
4. **Failure isolation.** The lineage layer computes every descriptor, chip and roster before it attaches
   anything.
   - **Attach failure.** A failure emits a bare `::warning title=leader_lineage::…` and leaves the
     incumbent `radar.json` payload unchanged.
   - **Merge failure.** A failure in the seal merge leaves the incumbent `state_history.parquet`
     write unchanged.
5. **Peers are the radar universe, leave-one-out.** Peers are the issuers in the radar rows that have bars.
   No owner inputs are fed: fundamentals, volume demand and the pivot are not published as descriptors yet,
   so `coverage.with_fundamentals`, `with_volume_demand` and `with_pivot` are 0 and those rungs read
   `UNKNOWN`. No intraday data is read. The leave-one-out basket keeps the incumbent rule: it exists on a
   session only when every peer has a finite close that day. On 2026-10-14, EA (last bar 2026-08-10) and
   WBD (last bar 2026-10-06) have no bar, so `coverage.with_peer_basket` is 0 and the `rs_vs_peer_basket`
   rung reads `UNKNOWN` for current evaluations. This admission reports that honestly and does not change it.
   A point-in-time basket membership rule is the spec owner's decision.

## 3. Not admitted (each needs its own PR by the surface owner)

- Any template or UI change. CONSUMER_SPEC §3 still requires its section, its visual evidence receipt
  (`scripts/check_ui_visual_evidence.py`) and the EN/ZH × dark/light matrix. The page HTML does not change
  with this admission.
- Terminal (§4) and Prophet (§5) consumers.
- Backfill of seals for sessions before activation.
- Any use as a ranking, gating, sizing, trading or alerting input. Any such proposal is a separate
  adjudication under §5.

## 4. Deviations from CONSUMER_SPEC §2 (recorded, deliberate)

- **Chip provenance keys.** The chip also carries `reason`, `source_ref` and `source_fingerprint_sha256`.
  These let a reader verify which bars produced the descriptor; they add no state.
- **Roster count.** `counts` also carries `NO_PRIOR_LEADER`. §2 lists that state as a value of `state`
  but omits it from `counts`. Without it the counts would not sum to `coverage.issuers`.
- **Sealed episode subset.** Seals hold a fixed, enumerated subset of the descriptor. Excluded are
  `ladder_order_violations` (unbounded and reconstructable from the ladder), `sessions_below_*` and
  `authority` (constant).

## 5. Render budget

The naive attach would have called `describe_lineage(..., peers=universe)` for each issuer. Measured on the
real 174-issuer universe, that costs 3.97 s/issuer, about 690 s per bake. The code PR therefore adds
`describe_lineage_universe`, which sources each series once and builds only the final row. It is tested
output-identical to the per-issuer call. Measured nightly cost on 2026-10-17, on the real 174-issuer universe with full history (8,492 sessions,
cut 2026-10-14), with the host at load average 8 to 20: attach 4.20 s plus seal merge 0.19 s, so about
4.4 s per bake. That is under the 10 s ceiling, so no history window is applied.

Payload growth is zero with the flag off. With the flag on, `radar.json` grows by about 976 KB (+55% on
1.77 MB):
- chips: 555 KB, a median of 2.4 KB and a maximum of 7.8 KB per issuer;
- the `early_entry` rows that share `display_chips`: 103 KB;
- the roster: 318 KB, mostly the full-history flattened episodes.

Each seal adds about 1.8 KB of JSON per issuer-session to `state_history.parquet`, which is 174 rows a
night. The page does not fetch `radar.json` and does not read these keys, so the growth is in the
committed artifact only.

## 6. Production proof after activation

On the first nightly or express bake after the activation PR merges:
- **Build log.** The Leader Radar step prints `leader lineage: <N> issuers in <X>s`, with no
  `::warning title=leader_lineage::` line.
- **radar.json.** Every row's `display_chips.leader_lineage.authority` is all-false. Every chip's `as_of` equals
  `lineage_roster.additive_clock.as_of`, which equals `recovery_roster.additive_clock.as_of`. The roster header
  `lineage_roster.as_of` keeps the incumbent clock, as `recovery_roster.as_of` does.
- **state_history.parquet.** Rows dated at that additive-clock session carry non-null `lineage_observed_at`,
  `lineage_observation_json` and `lineage_observation_sha256`:
  - each sha256 equals the digest of its JSON;
  - each JSON has `schema == "leader_lineage_observation.v1"` and `source_first_seen_proven == false`;
  - earlier dated rows are unchanged.

## 7. Rollback

Set `leader_radar.lineage_enabled: false`. The next bake drops the chip and roster from `radar.json`, and
captures stop. Existing seals stay, by design.
