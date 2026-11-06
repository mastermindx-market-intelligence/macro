# S0 Split and Contamination Law: Single-Name Intelligence (Alibaba / Tencent)

**Status:** S0 FROZEN PROTOCOL. This is a research document and implements nothing.
**Task graph:** S0, domain O3. This document satisfies acceptance case **A23**: "Train/tune/test and event/name/time split membership is immutable; contaminated holdout is retired visibly."
**Companions:**
- **REG** = `S0_PROTOCOL_REGISTER.md`, which holds the Membership Seal table (§6) and the Retirement Log table (§7).
- **IL** = `S0_INDEPENDENCE_LAW.md`, which defines episodes and honest-N.

**Evidence base:** the same as IL.

| Source | Location | Commit |
|---|---|---|
| `engine/qledger.py`, `engine/trial_ledger.py` | origin/main | `31b9647872e1` |
| V0 | origin/main | PR #8834 |
| E0, M0 and coverage profiles | — | `43251ca845b2` (PR #8837) |
| `DEC:PREREG-DESIGN-CHANGE-SUPERSEDES`, `DEC:PREREG-DATA-CONVENTION-CORRECTED-IN-PLACE`, `DEC:E3FMT-STRUCTURAL-SEPARATORS-PROXY-IDENTITY-AND-SOURCE-CONDITIONED-HOLDOUT` | `agentos/decisions/` | origin/main |

## 0. Authority (frozen)

| Scope | rank | gate | size | signal | escalation | trade |
|---|---|---|---|---|---|---|
| every split, seal, retirement and successor defined here | **false** | **false** | **false** | **false** | **false** | **false** |

## 1. Unit and membership key

- **The unit is atomic.** Membership is assigned to the IL episode, separately for each horizon. One episode is never divided across splits. Its evidence rows, bundle members, absorbed members and leg columns all inherit the episode's label.
- **Membership key.** Each membership is identified by `(protocol_id, version, horizon, episode_key)`.
- **`episode_key` for event episodes.** It is `sha256` of the UTF-8 string `issuer_key|opener_family|opener_t_avail_utc_iso8601|opener_evidence_pointer`.
- **`episode_key` for non-event units** (IL §3 step 7). It is `sha256` of `issuer_key|unit|anchor_session_date_iso|counter`. A prospective claim's membership row also records its qledger `claim_id` (`_claim_id`, qledger L1250).

## 2. Time axis (every protocol)

**Date convention.** The date of an episode is the trade date of the opener's first session `s` on the protocol's counting clock (IL §1).

**Splits.**

| Split | Membership |
|---|---|
| **TRAIN** | `s` < 2024-01-01 |
| **TUNE** | 2024-01-01 ≤ `s` < 2026-10-01 |
| **TEST** | **prospective claims only.** See the conditions below. |
| **QUARANTINE** | `s` ≥ 2026-10-01 and not a TEST claim. See below. |

**TEST conditions.** An episode belongs to TEST only if all three hold:
- It was registered through qledger `register` (L2026) before its window began. `_cohort_prospective` (L1722) enforces this, and a backfill is never prospective (V0 matrix row 15).
- It was registered after the **S0 freeze instant**. The freeze instant is the committer time of the first origin/main commit that contains `S0_PROTOCOL_REGISTER.md`.
- It was registered after the REG §2 registration gate opened.

TEST membership is fixed claim by claim, at registration.

**QUARANTINE.** These episodes are listed and counted but never analysed. They are never moved into TRAIN, TUNE or TEST, and the label is permanent.

Quarantine exists for two reasons:
- These dates overlap the period in which E0/M0 qualification looked at live data.
- TEST claims will grade over the same calendar period. Tuning on same-period history would share market shocks with TEST outcomes.

**Prior looks are TUNE at most.** Any period examined before the freeze, including whatever the August behavioral pilot touched, can be TUNE at most. No observation made before the freeze can ever be TEST. That is why TEST is prospective-only by design. August pilot numbers are never current data and never evidence under this law. They are disclosed as prior looks (§5).

**Purge, per `h`.** A purged episode keeps its label and gains a `purged` flag. It is excluded from that split's analysis, counted visibly per `(split, h)`, and never moved to another split. Two cases are purged:

| Split | Purged when |
|---|---|
| TRAIN | the last session of the episode's window `W_h` (IL §1) is on or after 2024-01-01 |
| TUNE | the last session of `W_h` is on or after 2026-10-01 |

## 3. Name axis (cohort protocols only; no cohort protocol is registered at S0)

**Bucket.** Each name is assigned a bucket from 0 to 9:

`bucket = int(sha256(("sni.s0.name-axis.v1:" + canonical_issuer_id).encode("utf-8")).hexdigest(), 16) % 10`

| bucket | role |
|---|---|
| 0–5 | TRAIN |
| 6–7 | TUNE |
| 8–9 | TEST-reserved |

**Why the salt is fixed.**
- The salt is one program-wide constant. It does not depend on protocol id or version. A successor version or a newly numbered protocol therefore cannot re-draw the name split.
- Changing the salt is a design change. It retires every sealed name split visibly under §8.

**Labels.**
- Historical episodes of TEST-reserved names are labelled **NAME-HELD-OUT**.
- For any other name, a historical episode takes the later of its time-axis label and its name-axis label, in the order TRAIN < TUNE.
- Prospective claims are TEST for every name.

**Names without an id.** A name with no owner-recorded `canonical_issuer_id` is excluded and listed. Tencent is the current case (`UNRESOLVED`, tencent.yml L15). Including such a name later is a new version.
- Alibaba has an owner-recorded id: `ISS:US-XNYS-BABA` (alibaba.yml L15), owner `lib/dataos/identity.py` (L16).
- No id is derived from a ticker, name or CIK.

**Own-name protocols.** The own-name protocols of the S0 register (REG P01–P13) are never name holdouts. The name axis is n/a for every one of them.

## 4. Event axis

- **Default.** `event_holdout` is `none` for every S0 protocol.
- **Declaring a holdout.** A protocol version may declare one event family `F` as held out. It must do so at version freeze, before any seal. Then:
  - every historical episode whose opener family is `F` is labelled **EVENT-HELD-OUT**;
  - family `F` is evaluated prospectively only.
- **Label precedence for a historical episode** (highest wins): QUARANTINE > NAME-HELD-OUT > EVENT-HELD-OUT > the time and name label from §3. The `purged` flag is applied on top of the resulting label.

## 5. Seal (before any outcome)

**Manifest.** For each `(protocol_id, version)`, S1 materialises a split manifest. It is canonical JSONL with one line per membership key, sorted by `(h, episode_key)`. Each line carries:
- the label;
- the flags `purged`, `confounded` and `absorbed_count`;
- the counting clock;
- the date of `s`.

**Recording the seal.** The manifest's `sha256`, `sealed_at` and the sealing commit are appended to REG §6 in a PR. That PR merges **before any TRAIN, TUNE or holdout outcome is computed** for that version. The manifest is recorded through the existing immutable-manifest idiom that V0 adopts (V0 extension decision §6). It is not a new store.

**Sealing TEST.** TEST membership accrues claim by claim, so REG §6 seals the TEST **rule**:
- the protocol version;
- the `prereg_digest_sha256` of the version's prereg instance (V0 extension decision §7).

Each TEST membership is its append-only qledger registration. The `claim_id` of that registration includes the computed salt (V0 extension X2, matrix row 7).

**Outcomes computed before the seal** are never evidence for that version. This includes any outcome the August pilot produced. Such outcomes are disclosed in the result receipt as **prior looks**.

## 6. Immutability

- Once sealed, membership on every axis (time, name, event) and in every split (TRAIN, TUNE, TEST, QUARANTINE, holdouts) is **immutable**. A label is never edited, moved, re-drawn, refilled or silently dropped.
- **Design changes.** The following changes create a new protocol version under `DEC:PREREG-DESIGN-CHANGE-SUPERSEDES`, with a new prereg digest, a new computed salt and therefore new `claim_id`s (V0 matrix rows 7, 17):
  - a boundary date;
  - the bucket function or its salt;
  - `event_holdout`;
  - an IL rule (families, classification rules, precedence, `s(c)`, `W_h`, the greedy rule);
  - a counting clock;
  - a bench;
  - a baseline.
- **Data-convention corrections.** These are corrected in place under `DEC:PREREG-DATA-CONVENTION-CORRECTED-IN-PLACE`, but **only if no membership label changes**. If a label would change, the correction is contamination (§7). It goes through §8 and is never edited in place.

## 7. Contamination classes

| # | Class | Definition |
|---|---|---|
| 1 | **OUTCOME-PEEK** | An outcome of a TUNE, TEST or held-out member was computed or viewed before its seal, or before maturity, and was then used for any design choice. |
| 2 | **TUNING-LEAK** | A choice of feature, threshold, bench, baseline, horizon or event rule was made using any member outside TRAIN and TUNE. Data dated on or after 2026-10-01 is outside TRAIN and TUNE. |
| 3 | **INFO-LEAK** | A feature, anchor or outcome read information timestamped after the anchor. Examples include restated values, identity resolved from current facts, and a change of **adjustment vintage**. A vintage change means factors were back-propagated from a corporate action announced after the anchor; M0 gap 1 notes that no reproducible vintage contract exists. |
| 4 | **IDENTITY-REGROUP** | After a seal, a counter or issuer regrouping, a canonical-id resolution or an IL violation changes which rows collapse into which episode. |
| 5 | **POST-UNSEAL-CHANGE** | Code or rules changed after a holdout was unsealed. The fixed rule from `DEC:E3FMT-STRUCTURAL-SEPARATORS-PROXY-IDENTITY-AND-SOURCE-CONDITIONED-HOLDOUT` (L28–L29) applies: "Never replace a dirty/no-QA/mismatched holdout slot and never change code after holdout unseal." |

## 8. Retirement procedure for a contaminated holdout (visible, exact)

A contaminated TUNE or TEST split is **retired**. It is never repaired, refilled or dropped. The procedure has six steps.

**Step 1. Freeze the affected split.** No further outcome of that split is computed or published as confirmatory from this moment.

**Step 2. Append exactly one visible trial-ledger row.** Use the existing `engine/trial_ledger.py` instance API:

```python
from engine.trial_ledger import TrialLedger

ledger = TrialLedger()  # DEFAULT_PATH = data/trial_ledger.jsonl (L48); __init__(path=None, family=None) (L79)
appended = ledger.log_trial(          # log_trial(self, config, *, family=None, info_cutoff=None,
    config={                          #           source="grid", note=None) -> bool   (L126)
        "event": "holdout_retired",
        "protocol_id": "<Pnn>",
        "version": "<vN>",
        "split": "test",              # or "tune"; no other value is admissible
        "membership_sha256": "<REG §6 manifest sha256, or the TEST-rule digest>",
        "contamination_class": "<one of §7>",
        "detected_at": "<UTC ISO-8601>",
        "evidence": "<pointer to the detecting artifact>",
    },
    family="sni.s0.<Pnn>",
    info_cutoff="<detected_at>",
    source="sni_s0_holdout_retirement",
    note="<one plain-word sentence>",
)
```

- **Return value.**
  - `True` means the row was appended.
  - `False` means the same `(family, config)` was already recorded. The row is keyed by `_hash` (L61) over the family and the canonical config, and the timestamp is excluded from the hash. The operation is therefore idempotent. Cite the existing row's `config_hash` instead.
- **Where to run it.** Run from a **full** checkout of fresh origin/main (`python3 scripts/worktree_sparse.py full`).
  - Never run it in a sparse tree, where a write into an omitted `data/` truncates the committed ledger.
  - Never run it in an intraday lane.
- **Diff check.** The resulting diff of `data/trial_ledger.jsonl` must be exactly one added line.
- **Conflicts.** If the file conflicts with a CI append (the existing writers include `daily.yml`, `signal-foundry.yml`, `codex-research.yml`, `cortex-retry.yml` and `metabolism-propose.yml`), reset to fresh main and re-run. Idempotency makes this safe.
- **Who appends.** The trial-ledger owner may read the repository's ledger law as forbidding a PR append to `data/trial_ledger.jsonl`. In that case, the row is handed to the owning CI lane, which appends it.
- **When retirement is complete.** Retirement is not complete until the row is on origin/main.
- **Retirement Log row.** The same PR appends the REG §7 Retirement Log row, which cites the `config_hash`.
- **Trial counts.** The row raises `literal_n` (L210) for the family. That deliberately overcounts trials, which errs toward caution. A declared budget is a floor and is never a cap: `log_declared_budget` (L159, "FLOOR" L163), and `effective_n` returns `max(base, declared, 1)` (L242).

**Step 3. Relabel the protocol.** The protocol's REG §3 status becomes **RETIRED-CONTAMINATED**. The row is never deleted. A retired split's manifest and seal row stay in REG §6.

**Step 4. Preserve results.** Every result already computed on the retired split is preserved and labelled **non-confirmatory**, together with the contamination class. qledger stays append-only and keep-first. No registration or grade is edited or removed.

**Step 5. Successor.** A successor is a **new version**. It never refills, replaces, skips or re-ranks the retired members ("Never replace/skip/rerank", E3FMT L120).
- **Retired TEST.** The successor's TEST admits only claims registered **after** the retirement row's `detected_at`.
- **Retired TUNE.** The successor's TUNE is **empty**. The successor either tunes on TRAIN only or is declared untuned, and its TEST is prospective.
- **Trial count.** The trial count carries over, and the successor's declared budget is at least the carried `literal_n`.
- **Root-cause fix.** The successor's prereg must name what changed to remove the contamination source. For example, a pinned adjustment vintage.

**Step 6. Data-convention fixes.** A fix that changes no label stays in place (§6) and never uses this procedure. The `split` field accepts only `test` or `tune`. TRAIN is never retired. A TRAIN defect is fixed by a new version.

Nothing in this procedure "rescues" a failed model. The masterplan's §8 rule binds, quoted from the masterplan at `7906ef1c`, L268: "do not rescue it by changing the target, cohort or horizon after seeing results. Preserve failed hypotheses and contaminated holdouts as evidence."

## 9. Worked example: INFO-LEAK retirement (symbolic)

1. **The setup.** P01 v1 (REG) seals its TRAIN and TUNE manifest. The digest is recorded in REG §6.
2. **The detection.** S1 later finds that the price vintage it used had back-propagated adjustment factors from a corporate action announced **after** some TUNE anchors. This is class 3, INFO-LEAK (M0 gap 1).
3. **The ledger row.** One `log_trial` row is appended (§8 step 2) with `split: "tune"`, `contamination_class: "INFO-LEAK"`, and `membership_sha256` set to the sealed digest.
4. **The Retirement Log row.** REG §7 gains a row naming P01, `tune`, the digest, the class, `detected_at`, the evidence pointer, `sni.s0.P01` and the successor `P01 v2`.
5. **The protocol status.** P01 v1 becomes RETIRED-CONTAMINATED. Its TUNE results remain visible, labelled non-confirmatory.
6. **The successor.** P01 v2 pins a reproducible adjustment vintage. It has an empty TUNE, a prospective TEST that admits only claims registered after `detected_at`, and a declared budget of at least the carried trial count.
7. **What changes and what does not.** The honest-N of the retired split does not change. It is simply no longer confirmatory.

## 10. Summary of A23 obligations

| Obligation | Where |
|---|---|
| train/tune/test membership immutable | §2, §5, §6 |
| event/name/time membership immutable | §2, §3, §4, §6 |
| exact retirement procedure for a contaminated holdout | §8 steps 1–6 |
| retirement is a visible ledger row, never a silent drop | §8 step 2 (`TrialLedger.log_trial`, L126) plus the REG §7 row |
| successor never refills | §8 step 5 |
| all authority flags false | §0 |
