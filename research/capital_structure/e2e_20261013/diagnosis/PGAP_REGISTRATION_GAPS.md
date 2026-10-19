# PGAP — why the served state publishes no registration paths for CLNN, LPTH and EDBL

Diagnosis lane `claude/cs-v2-pgap-diag-lane`, based at `3f1a158d5773c0d9d9e67ddcbfb5db048b04bfcf`
(verified by `git log -1 --format=%H` — output `3f1a158d5773c0d9d9e67ddcbfb5db048b04bfcf`).
Read-only: this report is the only file the lane writes. All numbers below are printed by the
quoted commands; snippets live under `/tmp/pgap/` and never in the repository.

**One-paragraph answer.** All three issuers reach `compile_registration_lifecycles`
(`engine/capital_structure/registration_lifecycle.py`) but stop at different walls:
CLNN's ledger rows are all non-candidate forms (424B5/8-K/10-Q) and its shelf S-3 was never
discovered; LPTH's 44 corrected POS AM/EFFECT pairs are all deferred
`correction_group_changed` because the v1→v2 correction *added* the SEC file number, and even
unblocked they would defer `missing_lifecycle_edge` because the amended shelves are absent
from the ledger; EDBL's single S-3+EFFECT lifecycle dies the same `correction_group_changed`
death on its v1→v2 file-number enrichment. The rebuild at the served as_of reproduces the
served gap exactly, so this is live code+data, not drift.

---

## 0. Environment

- Interpreter: `~/lanes/venvs/w12-flaky-31213/bin/python3 --version` → `Python 3.12.13`.
- Worktree: `~/lanes/wt/cs-v2-pgap-diag-lane`, branch `claude/cs-v2-pgap-diag-lane`.
- `git worktree add` resolved the sha on the first attempt (it was present locally; `git fetch
  origin` ran in parallel and exited 0).
- `python3 scripts/worktree_sparse.py auto` → `worktree-sparse: auto skipped — only session
  worktrees are changed`. `add data/capital_structure` reported `not tracked at HEAD:
  data/capital_structure`; the fallback `add data` materialized it (deviation D1 below).
- Read-only check:
  `SENTRY_DSN=https://public@example.invalid/1 PYTHONPATH=. ~/lanes/venvs/w12-flaky-31213/bin/python3 -m pytest -q -p no:cacheprovider -W ignore -rfE tests/test_capital_structure_registration_integration.py tests/test_capital_structure_registration_lifecycle.py`
  → **`52 passed in 1.47s`** (both test files exist at the base; no substitution needed).

## 1. Question 1 — which ledger rows exist per CIK

Command (`/tmp/pgap/q1_counts.py`, quoted in full in the file; core query):

```python
df = pd.read_parquet(path)
cik_cols = [c for c in df.columns if "cik" in c.lower()]
n = sum(((df[c].astype(str) == cik) | (df[c].astype(str) == str(int(cik)))).sum() for c in cik_cols)
```

Note: `event_versions.cik` stores the CIK **unpadded** (`'1822791'`), while `discovery.cik`
stores it zero-padded (`'0001822791'`). The packet's CIKs match both forms.

Output:

```
covenant_term_observations.parquet: rows=0 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
covenant_term_observations.quarantined.parquet: rows=0 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
discovery.parquet: rows=25638 cik_cols=['cik'] per_cik={'CLNN': 12, 'LPTH': 52, 'EDBL': 25}
document_term_observations.parquet: rows=13140 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
event_edges.parquet: rows=1984 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
event_versions.parquet: rows=15087 cik_cols=['cik'] per_cik={'CLNN': 8, 'LPTH': 94, 'EDBL': 10}
index_coverage.parquet: rows=124 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
retrieval_attempts.parquet: rows=16700 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
review_queue.parquet: rows=10009 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
sec_evidence__ingest.parquet: rows=37 cik_cols=[] per_cik={'CLNN': 0, 'LPTH': 0, 'EDBL': 0}
```

(`event_edges` has no CIK column; edge counts per CIK are by endpoint membership below.
`document_term_observations` keys on `issuer_id`, counted separately: CLNN 0, LPTH 0, EDBL 10
rows — EDBL's are the S-3 fee-table terms `amount_to_be_registered`,
`filing_fee_rate`, `proposed_maximum_aggregate_offering_price`,
`proposed_maximum_offering_price_per_unit`, `registration_fee`.)

Distinct forms and dates in `event_versions` per CIK (`/tmp/pgap/q1e_forms.py`):

- **CLNN (cik `1822791`), 8 rows:** `8-K` ×4 (2026-05-04, 2026-05-05, 2026-05-14, 2026-09-16),
  `424B5` ×3 (2026-05-05 ×2, 2026-09-16), `10-Q` ×1 (2026-05-14).
  All correction_version 1; classification: 424B5/8-K `deferred_ambiguous_content`, 10-Q
  `not_applicable`.
- **LPTH (cik `889971`), 94 rows:** `POS AM` 22 accessions × v1+v2 = 44 rows (all accepted
  2026-07-22 20:43–20:55Z), `EFFECT` 22 accessions × v1+v2 = 44 rows (accepted
  2026-07-24 04:15Z), plus `424B5` ×2 (2026-06-03), `8-K` ×2 (2026-05-07, 2026-09-10),
  `10-Q` (2026-05-07), `10-K` (2026-09-11). POS AM/EFFECT are `classified`; the rest
  `deferred_ambiguous_content`/`not_applicable`.
- **EDBL (cik `1809750`), 10 rows:** `S-3` v1+v2 (accession `0001477932-26-004651`, accepted
  2026-07-31T21:24:02Z), `EFFECT` v1 (`9999999995-26-002592`, accepted 2026-08-10T04:15:21Z,
  available 2026-10-15T03:09:02Z), `PRE 14A`, `DEF 14A`, `8-K` ×4, `10-Q`.

Discovery (`discovery.parquet`, `/tmp/pgap/q5b_discovery.py`): CLNN 12 rows — **no S-3 or other
registration form**; LPTH 52 rows — no S-1/S-3 (the shelves amended by the POS AMs were never
discovered); EDBL 25 rows — includes the `S-3` (2026-07-31), `EFFECT` (2026-08-07) and a
`424B5` (2026-08-11), collection_scope `registration_issuance`.

Edges touching each CIK's events (`/tmp/pgap/q2b_edges.py`): **CLNN 0, LPTH 44 (all
`supersedes`, v2→v1 correction links), EDBL 2** (`supersedes` S-3 v2→v1 +
`effectuates` EFFECT→S-3 v2, link_method `exact_cik_file_number_family_chronology`).

## 2. Question 2 — which rows reach the compiler as candidates

`_is_lifecycle_candidate` is `engine/capital_structure/registration_lifecycle.py:280-284`:
a row is a candidate iff `route_form(form).registration_family in REGISTRATION_FAMILIES`
(`registration_lifecycle.py:44-53`: s1/f1/s3/f3/f10/reg_a) **or**
`route.relationship in {"amendment_of","effectuates","withdraws"}` (`:54-56`).

- **CLNN — 0 of 8.** `route_form("424B5")` (`event_spine.py:201-206`) returns family `other`,
  `registration_family=None`, `relationship=None`, classification
  `DEFERRED_AMBIGUOUS_CONTENT`, reason
  `prospectus_requires_content_to_distinguish_pricing_atm_resale_or_rights`. `8-K` likewise
  (`event_spine.py:207-221`), `10-Q` is `not_applicable` (`:242-244`). No row is a candidate;
  none of the later filters is ever reached.
- **LPTH — 44 of 94 are candidates** (each POS AM and EFFECT row of both versions; the v1 rows
  via `relationship`, the 8-K/10-Q/10-K/424B5 rows not). The v2 rows pass the per-node checks
  (issuer id present, trusted `file_number_provenance` via
  `_trusted_file_number_provenance` `registration_lifecycle.py:211-247`, classified, lifecycle
  state matches route) but every v1/v2 logical pair is killed **before grouping** by the
  correction check at `registration_lifecycle.py:736-765`: the condition
  `... or not current_file or not target_file or current_file != target_file ...` is true
  because v1 carries `filing.file_number: null` while v2 carries the enriched
  `file_number` (e.g. `333-37443`) + provenance — so the pair is deferred
  `correction_group_changed` and both versions enter `blocked_corrections`, removing the whole
  logical observation from `current_events` (`registration_lifecycle.py:824`).
- **EDBL — 4 of 10 rows are candidates** (S-3 v1, S-3 v2 via `registration_s3`; EFFECT via
  `effectuates`). The S-3 pair dies exactly like LPTH's (`not target_file`: v1 has
  `file_number: null`, v2 has `333-297912`). The EFFECT then defers
  `ambiguous_current_event_version` at `registration_lifecycle.py:884-886`:
  `resolve_terminal` finds its edge target (the current S-3 v2) inside
  `blocked_corrections`.

## 3. Question 3 — deferred items per CIK

Direct compile (`/tmp/pgap/q3_compile.py`):
`compile_registration_lifecycles(events, edges, "2026-10-17T14:45:44.820502Z", same)` over all
15,087 events / 1,984 edges → coverage
`{"candidate_event_count": 4963, "deferred_count": 2385, "lifecycle_count": 1191, "reason":
"deferred_registration_lifecycle_observations_present", "state": "partial"}`.

- **CLNN: 0 lifecycle records, 0 deferred items.** Nothing reaches the defer ledger; the
  per-issuer `lifecycle_coverage_unavailable` limit comes from
  `registration_lifecycle.py:1667-1670` (`elif not raw_candidate_ids: coverage_state =
  "unavailable"`, reason `no_visible_registration_lifecycle_observations`) surfaced through
  `_support_limits` (`registration_integration.py:471-472`).
- **LPTH: 0 records, 44 deferred items** — every one `correction_group_changed`, one per v1/v2
  POS AM pair (22) and v1/v2 EFFECT pair (22). Full table (generated by `/tmp/pgap/q3_table.py`):

| defer_id | reason | events (form vN accession) | supersedes edge |
|---|---|---|---|
| `defer:registration-lifecycle:cs:014f3ebdae4819d0561c3b38` | correction_group_changed | EFFECT v2 9999999995-26-002429; EFFECT v1 9999999995-26-002429 | `edge:cs:31cc6c1cfd3a03b70be879eb` |
| `defer:registration-lifecycle:cs:01ada466f653f5455e4c5011` | correction_group_changed | POS AM v1 0001437749-26-024169; POS AM v2 0001437749-26-024169 | `edge:cs:5fd7d3a15137fdb66ae04917` |
| `defer:registration-lifecycle:cs:07ae766b2457336bf16540be` | correction_group_changed | EFFECT v1 9999999995-26-002406; EFFECT v2 9999999995-26-002406 | `edge:cs:ff666293f066d1d89bd7a8c2` |
| `defer:registration-lifecycle:cs:0bab35d5c6f1c5992b60a52d` | correction_group_changed | POS AM v2 0001437749-26-024164; POS AM v1 0001437749-26-024164 | `edge:cs:5038f3ba5be8c4a9330cbe15` |
| `defer:registration-lifecycle:cs:0dc6a40dd2d815d92ae7d5b6` | correction_group_changed | EFFECT v1 9999999995-26-002425; EFFECT v2 9999999995-26-002425 | `edge:cs:809959460bbc6281e354610e` |
| `defer:registration-lifecycle:cs:0f9f8d4a3d625e15f5e7e409` | correction_group_changed | POS AM v1 0001437749-26-024172; POS AM v2 0001437749-26-024172 | `edge:cs:6f708551ac9eb47e8f00340d` |
| `defer:registration-lifecycle:cs:1e70579523118d4f5c8a01c0` | correction_group_changed | EFFECT v1 9999999995-26-002426; EFFECT v2 9999999995-26-002426 | `edge:cs:d5f210daee14c5cdaf1763f5` |
| `defer:registration-lifecycle:cs:1ea31d2c8bc06bba043894ce` | correction_group_changed | POS AM v1 0001437749-26-024150; POS AM v2 0001437749-26-024150 | `edge:cs:eb808e137e4e896e5566084a` |
| `defer:registration-lifecycle:cs:1f8fc859e097aa3a92d7a9a8` | correction_group_changed | EFFECT v1 9999999995-26-002397; EFFECT v2 9999999995-26-002397 | `edge:cs:93d271000bd29663a3cfd82d` |
| `defer:registration-lifecycle:cs:208a557516ebcbeebf7effa5` | correction_group_changed | EFFECT v2 9999999995-26-002424; EFFECT v1 9999999995-26-002424 | `edge:cs:97b28609293f87deadc4942c` |
| `defer:registration-lifecycle:cs:2498e98d8ed645f53ff8b9c4` | correction_group_changed | EFFECT v1 9999999995-26-002404; EFFECT v2 9999999995-26-002404 | `edge:cs:a3798d67b71171689f31200c` |
| `defer:registration-lifecycle:cs:25706daf85d83da914470623` | correction_group_changed | POS AM v2 0001437749-26-024157; POS AM v1 0001437749-26-024157 | `edge:cs:6413b04ec1c33eb6e9e99a8d` |
| `defer:registration-lifecycle:cs:27e06f8b2ce9dac682b29152` | correction_group_changed | EFFECT v2 9999999995-26-002423; EFFECT v1 9999999995-26-002423 | `edge:cs:e58fcd5b494eca175508bad4` |
| `defer:registration-lifecycle:cs:38625f90c56cf9b42e2527ce` | correction_group_changed | EFFECT v2 9999999995-26-002428; EFFECT v1 9999999995-26-002428 | `edge:cs:764d85c2b87f58d251bd9de9` |
| `defer:registration-lifecycle:cs:3f5acef7fb39a594dc168732` | correction_group_changed | POS AM v2 0001437749-26-024166; POS AM v1 0001437749-26-024166 | `edge:cs:906cfebeebc10ddf7165fcc4` |
| `defer:registration-lifecycle:cs:4d42e1da4ed7413425939063` | correction_group_changed | POS AM v2 0001437749-26-024165; POS AM v1 0001437749-26-024165 | `edge:cs:68d793f0ecb188a7be2baf77` |
| `defer:registration-lifecycle:cs:53b349eb7439b916edf81908` | correction_group_changed | POS AM v1 0001437749-26-024151; POS AM v2 0001437749-26-024151 | `edge:cs:e217a73f5b05961e9d9f2695` |
| `defer:registration-lifecycle:cs:53c3d90d96c0b0be069b4179` | correction_group_changed | POS AM v1 0001437749-26-024156; POS AM v2 0001437749-26-024156 | `edge:cs:f55b35a71acc82e2f852e2dd` |
| `defer:registration-lifecycle:cs:53d6fe0df1587ab8893f5959` | correction_group_changed | EFFECT v2 9999999995-26-002408; EFFECT v1 9999999995-26-002408 | `edge:cs:b7c39ebff32e0f4ad6a5bc40` |
| `defer:registration-lifecycle:cs:55437a911d3264c900aff972` | correction_group_changed | EFFECT v1 9999999995-26-002407; EFFECT v2 9999999995-26-002407 | `edge:cs:6de873deb68a2b2d259bd2e1` |
| `defer:registration-lifecycle:cs:5b7c2ea232f35ba40b371df7` | correction_group_changed | POS AM v2 0001437749-26-024171; POS AM v1 0001437749-26-024171 | `edge:cs:27cb9ef78c35a86ed6b7a37c` |
| `defer:registration-lifecycle:cs:5e8662f1aea230247563c81e` | correction_group_changed | POS AM v1 0001437749-26-024149; POS AM v2 0001437749-26-024149 | `edge:cs:5c827453ccfb14a87d2b1d6f` |
| `defer:registration-lifecycle:cs:5ea82f5e00a5e4942433e0b7` | correction_group_changed | EFFECT v2 9999999995-26-002430; EFFECT v1 9999999995-26-002430 | `edge:cs:646ff66d774c73b3014d9233` |
| `defer:registration-lifecycle:cs:640eb607d26d94e199a3e5be` | correction_group_changed | EFFECT v1 9999999995-26-002399; EFFECT v2 9999999995-26-002399 | `edge:cs:d262c422de6acb72da7d62dd` |
| `defer:registration-lifecycle:cs:6876c5fb7d0201610f48c2e8` | correction_group_changed | EFFECT v1 9999999995-26-002398; EFFECT v2 9999999995-26-002398 | `edge:cs:f880a9f2b988001a756bab3a` |
| `defer:registration-lifecycle:cs:71793285513fd323382f21de` | correction_group_changed | POS AM v1 0001437749-26-024160; POS AM v2 0001437749-26-024160 | `edge:cs:de182b52bbef30a17d04a59f` |
| `defer:registration-lifecycle:cs:853decb1dbab16d68f3480bb` | correction_group_changed | EFFECT v2 9999999995-26-002401; EFFECT v1 9999999995-26-002401 | `edge:cs:7d0b96641b3ba890351d2638` |
| `defer:registration-lifecycle:cs:8722ef3b650f23a776ea658c` | correction_group_changed | POS AM v1 0001437749-26-024176; POS AM v2 0001437749-26-024176 | `edge:cs:63e7cf282e6c2a2150a9ce22` |
| `defer:registration-lifecycle:cs:9421f4d289dc6fa301745120` | correction_group_changed | POS AM v2 0001437749-26-024170; POS AM v1 0001437749-26-024170 | `edge:cs:f44f44ca36eda0f91cb821de` |
| `defer:registration-lifecycle:cs:94b875ac1c72e36665226d26` | correction_group_changed | EFFECT v2 9999999995-26-002431; EFFECT v1 9999999995-26-002431 | `edge:cs:b0a6c32f6168ac2d7c8ab1ea` |
| `defer:registration-lifecycle:cs:a10a0b99c09533f04d3af135` | correction_group_changed | POS AM v2 0001437749-26-024159; POS AM v1 0001437749-26-024159 | `edge:cs:f3dfbd5a169e851c72a6cfaa` |
| `defer:registration-lifecycle:cs:a5a6733732f8734af75edac5` | correction_group_changed | POS AM v1 0001437749-26-024153; POS AM v2 0001437749-26-024153 | `edge:cs:56f07f4ae6546bb9d6ee1279` |
| `defer:registration-lifecycle:cs:ae0cd81c1d151df3e446851c` | correction_group_changed | EFFECT v2 9999999995-26-002403; EFFECT v1 9999999995-26-002403 | `edge:cs:c7aef6c5045975d4cd870d17` |
| `defer:registration-lifecycle:cs:ba71c473d79d8ca05956043f` | correction_group_changed | EFFECT v1 9999999995-26-002427; EFFECT v2 9999999995-26-002427 | `edge:cs:837390ad463621516971337f` |
| `defer:registration-lifecycle:cs:bfcfd447f71ef70369dd998b` | correction_group_changed | EFFECT v1 9999999995-26-002422; EFFECT v2 9999999995-26-002422 | `edge:cs:724af65b5ea1ce2ae3abde06` |
| `defer:registration-lifecycle:cs:c0f208852fd3c579186e1c63` | correction_group_changed | POS AM v2 0001437749-26-024147; POS AM v1 0001437749-26-024147 | `edge:cs:f47125bf6c73b67cdfd3fd7a` |
| `defer:registration-lifecycle:cs:cba67313ae78719ef602f04e` | correction_group_changed | EFFECT v1 9999999995-26-002400; EFFECT v2 9999999995-26-002400 | `edge:cs:ca26ead95e65f2d658f8be50` |
| `defer:registration-lifecycle:cs:d9c9c062cbd7e4e128457240` | correction_group_changed | POS AM v1 0001437749-26-024168; POS AM v2 0001437749-26-024168 | `edge:cs:48fcf2831b616d865b1d399b` |
| `defer:registration-lifecycle:cs:dc8629d02215c68db3878be6` | correction_group_changed | EFFECT v2 9999999995-26-002402; EFFECT v1 9999999995-26-002402 | `edge:cs:0c3293b8c3015337f08f4f34` |
| `defer:registration-lifecycle:cs:de72cc79b59f2688dc1e0e64` | correction_group_changed | EFFECT v2 9999999995-26-002405; EFFECT v1 9999999995-26-002405 | `edge:cs:8f325b89bcc54e7efdfbd8a1` |
| `defer:registration-lifecycle:cs:ead205164ca34848f5426586` | correction_group_changed | POS AM v2 0001437749-26-024162; POS AM v1 0001437749-26-024162 | `edge:cs:03066010c13a8d56e166bc78` |
| `defer:registration-lifecycle:cs:f1f0002bdd965c7d78efbc87` | correction_group_changed | POS AM v2 0001437749-26-024174; POS AM v1 0001437749-26-024174 | `edge:cs:0eda47fbfe6b968fcd26a11d` |
| `defer:registration-lifecycle:cs:f20d8dc0bb4e26c7e392af64` | correction_group_changed | POS AM v1 0001437749-26-024148; POS AM v2 0001437749-26-024148 | `edge:cs:0936711fdcc79b7045de1886` |
| `defer:registration-lifecycle:cs:ff4aaf83b0d942f6228a9cdd` | correction_group_changed | POS AM v1 0001437749-26-024161; POS AM v2 0001437749-26-024161 | `edge:cs:86585dd47d429b77dcc1f064` |

- **EDBL: 0 records, 2 deferred items:**
  - `defer:registration-lifecycle:cs:0c098d6554b3c2513629575f` — `correction_group_changed`,
    key `{file_number: null, issuer_id: "sec:cik:0001809750", registration_family:
    "registration_s3"}`, event_ids `[event:cs:bdcc70bb47bf8fb9e988707a (S-3 v2),
    event:cs:ed6a72eba923afa9bffe779d (S-3 v1)]`, edge `edge:cs:64d3aa4a314b6bf689de6bad`.
  - `defer:registration-lifecycle:cs:e062ef05a613065a9799be71` —
    `ambiguous_current_event_version`, key `{file_number: "333-297912",
    issuer_id: "sec:cik:0001809750", registration_family: null}`, event_ids
    `[event:cs:43026f12e81acff1630fb271 (EFFECT), event:cs:bdcc70bb47bf8fb9e988707a (S-3 v2)]`,
    edge `edge:cs:bb7fdc9e5ab1c164d7649ac2`.

## 4. Question 4 — does the rebuild reproduce the served gap?

The packet's exact command **refused**:

```
PYTHONPATH=. ~/lanes/venvs/w12-flaky-31213/bin/python3 -m scripts.build_capital_structure_state --out-path /tmp/pgap/state_bundle.json --as-of 2026-10-17T14:45:44Z --generated-at 2026-10-17T14:45:44Z
→ RC=2 {"reason": "generated_at cannot precede the verified generation clock", "status": "refused"}
```

Cause: the committed verified generation's clock is
`telemetry.json as_of = 2026-10-17T14:45:44.820502+00:00` — 820.5 ms **after** the packet's
`14:45:44Z`, and `scripts/build_capital_structure_state.py` (via the projection verifier)
refuses a clock that precedes it. The served bundle's as_of is that same generation clock.
Retry at the generation's own clocks (`--as-of 2026-10-17T14:45:44.820502Z --generated-at
2026-10-17T15:25:17.094128Z`, the served `projection.json generated_at`) — last 10 lines of
output:

```
RC=0
{"as_of": "2026-10-17T14:45:44.820502Z", "byte_length": 31044247, "evidence_entries": 1728, "generation_id": "state_bundle:cs:7eb073ae272fe90596e46fb05b2514ee", "issuers": 3157, "out_path": "/tmp/pgap/state_bundle.json", "status": "partial"}
--- stderr:
```

(The rebuilt `generation_id` differs from the served `state_bundle:cs:2be6a6164f1d6fd9a5bd5c89375d21b6`
because `generated_at` enters the identity; the per-issuer content is the comparison that matters.)

**The gap reproduces exactly.** Per-issuer `issuer_index` entries in the rebuild
(`/tmp/pgap/q4f_fullidx.py`):

- CLNN: `event_count 8, edge_count 0, path_evidence {}`, coverage
  `unexamined_reason_codes: ["lifecycle_coverage_unavailable", "no_shelf_form_family_observed",
  "offering_role_unknown", "replacement_not_extracted", "rule_pack_gap:pre_2016_form_editions"]`,
  `total 0`.
- LPTH: `event_count 94, edge_count 44, path_evidence {}`, codes
  `["deferred:correction_group_changed", "lifecycle_coverage_partial",
  "no_shelf_form_family_observed", ...]`, `total 0`.
- EDBL: `event_count 10, edge_count 2, path_evidence {}`, codes
  `["deferred:ambiguous_current_event_version", "deferred:correction_group_changed",
  "lifecycle_coverage_partial", "no_shelf_form_family_observed", ...]`, `total 0`.
- Bundle-level `evidence_index` has **0 entries** for all three issuer ids
  (`/tmp/pgap/q4c_ciks.py`: `CLNN evidence entries: 0  LPTH evidence entries: 0  EDBL evidence
  entries: 0`).

Conclusion: no data or code drift — the served night's empty records, `partial` support,
`lifecycle_coverage_*` limits and empty `path_evidence` are all re-derived from this tree at
the served as_of.

## 5. Question 5 — the absent families and their producers

The served state bundle publishes **only the `registration` family** for every issuer —
`build_state_bundle` seals `families=(reg.family_state(),)` at
`engine/capital_structure/state_bundle.py:399`. Across all 3,157 issuers in the rebuild the
family census is `{registration: 3157}` (`/tmp/pgap/q5_families.py`). The other
`STATE_FAMILIES` (`issuer_state_contracts.py:122-131`: identity, share_basis, instruments,
cash_funding, transactions, uncertainty, change_events) are declared vocabulary, not wired
producers. Per family:

| family | issuer(s) | producer that should emit it | status for the CIK |
|---|---|---|---|
| `instruments` | CLNN | `scripts/compile_capital_structure_instrument_candidate_terms` → `instrument_candidate_terms.parquet`, bound by `_bind_instruments` (`scripts/build_capital_structure_capacity_inputs.py:185`) | **produced zero rows — the ledger file does not exist** under `data/capital_structure/` (verified by `ls`). Nightly step `cs_candidates` is `continue-on-error` and carries `DSC:CS-INSTRUMENT-AND-LIFECYCLE-COMPILERS-NOT-NIGHTLY` (`.github/workflows/daily.yml`, the step comment: "today the main reason an issuer's instruments family is unavailable is that this compiler is simply never invoked nightly"). |
| `cash_funding` | CLNN | none nightly: `state_bundle.py:399` publishes registration only; `project_funding` (`engine/capital_structure/funding.py`) requires `FinancialInputs`, and capacity inputs' own docstring states financials are "unavailable until the F0b binder exists on an admitted companyfacts artifact". CLNN also has 0 document-term rows. | **refused by contract shape** — no producer is wired into any nightly bundle. |
| `change_events` | LPTH | none — `STATE_FAMILIES` names it (`issuer_state_contracts.py:130`) but grep over `engine/`+`scripts/` finds no producer module. | **no producer exists at all.** |
| `share_basis` | EDBL | `select_share_basis` (`engine/capital_structure/share_basis.py:499`) via `_bind_share_basis` (`build_capital_structure_capacity_inputs.py:249`); needs `share_count_observations.jsonl` + `corporate_actions.jsonl` under `data/capital_structure/` | **produced zero rows — neither input file exists** (verified by `ls`); EDBL has no admitted share-count observation and no corporate-action record. |
| `transactions` | EDBL | `engine/capital_structure/transactions.py` exists but is bound by no nightly producer (state bundle: registration only; capacity inputs: instruments/share_basis/financials/commitments/rules, `build_capital_structure_capacity_inputs.py:406-411`). | **not invoked nightly.** |

The dossier's "no split rule example in the packs" is confirmed at the producer level:
`evaluate_split_actions` (`share_basis.py:281`) judges
`capital_structure.corporate_action_observation.v1` records against the four-stage gate
`SPLIT_STAGES = ("authorization", "vote", "effective", "exchange_adjustment")`
(`share_basis.py:83`); no nightly producer emits corporate-action observations, so no split
record — and therefore no split example — can exist in any pack today.

## 6. Question 6 — minimal fixes and regression tests

### EDBL (the only pure-code fix; also serves the whole enrichment class)

Root cause: `engine/capital_structure/registration_lifecycle.py:736-765` — the
correction-pair check treats a v1→v2 correction that **adds** the SEC file number (v1
`file_number: null`, no provenance; v2 `333-297912` with trusted
`sec_header_file_number` provenance) as a group change and defers both versions
(`correction_group_changed`), which also poisons the EFFECT that points at the corrected S-3
(`ambiguous_current_event_version`, `registration_lifecycle.py:884-886`).

Minimal fix (in words): in the condition at `registration_lifecycle.py:736-746`, when the
*current* version's issuer id and route-derived family equal the target's (or the target has
none) and the target carries **no file number at all** while the current version carries
exactly one trusted-provenance value (already checked by
`_trusted_file_number_provenance`), treat the pair as a file-number **enrichment**: keep the
group from the current version instead of emitting `correction_group_changed`. This mirrors
the tolerance the edge-target check already has at `registration_lifecycle.py:1238-1251`
(`or (old_key is not None and old_key != target_key)` — a keyless old target is not a
mismatch there). No classification is hand-written; the trusted-provenance gate stays.

Evidence this is the only EDBL blocker (counterfactual, `/tmp/pgap/q6_counterfactual2.py`,
using the real S-3 v1 body with its v2's real file-number fields as a single non-corrected
observation plus the real EFFECT event and a spine-`_edge`-shaped effectuates edge):

```
EDBL enriched-v1 world: records: 1 deferred: 0
  RECORD {'issuer_id': 'sec:cik:0001809750', 'cik': '1809750', 'ticker': 'EDBL', ...} registration_s3 333-297912 -> effective
     S-3 filed -> filed @ 2026-07-31T21:24:02Z
     EFFECT effective -> effective @ 2026-08-10T04:15:21Z
```

Regression test: `tests/test_capital_structure_registration_lifecycle.py` — e.g.
"correction that adds a trusted SEC file number keeps the lifecycle group and admits the
pair" (today the file carries correction-group tests only for genuine changes).

### LPTH — two-layer cause; code fix necessary, not sufficient

Layer 1 is the same `correction_group_changed` enrichment bug (44 pairs).
Layer 2 is data: even unblocked, every LPTH POS AM/EFFECT defers
`missing_lifecycle_edge` (`registration_lifecycle.py:1132-1144`) because the amended
registration statements — shelves `333-37443`, `333-39641`, `333-47905`, `333-113814`, … (22
distinct old file numbers across the v2 POS AMs and EFFECTs) — are in **neither**
`event_versions` nor `discovery` (discovery window starts 2026-05). Counterfactual
(`/tmp/pgap/q6_counterfactual2.py`):

```
LPTH parentless world: records: 0 deferred: 1
  DEFER defer:registration-lifecycle:cs:22174a4caf6a1f597871dde7 missing_lifecycle_edge [...]
```

Fix: apply the EDBL enrichment fix (code), then backfill discovery for the 22 shelf file
numbers (collection-scope decision — a real repair needs those S-3/S-1 filings retained and
compiled; the compiler must keep deferring until then, never guess). No code change can
manufacture the missing parents.

### CLNN — genuinely unsupported path; data + policy, not code

CLNN's only registration evidence is 424B5 takedowns of a shelf S-3 that the ledger never
discovered (no S-3 row for CLNN in `event_versions` or `discovery`). `424B5` is collected
(`wave1_discovery` in `telemetry.json form_policy`) but routed by
`event_spine.py:201-206` to `deferred_ambiguous_content` with no registration family and no
relationship — by design, since a prospectus form token cannot distinguish pricing/ATM/resale
without document content. The missing entries are:

- discovery backfill of CLNN's shelf S-3 (the 424B5s amend it; its `EFFECT` would then give
  the lifecycle a root), and
- a **content-based classification path for 424B5 takedowns** — the form policy
  (`capital-structure-sec-form-policy/1.2.0`) has no rule that admits a 424B5 to any
  registration family, and none may be invented from the form token (A23). Until such a
  classifier exists in the spine, CLNN's `424B5` rows are correctly deferred and the
  `clnn:atm_programme_remaining` gap is honest.

Proposed test carrier for any spine-side follow-up:
`tests/test_capital_structure_event_spine.py` (form routing) /
`tests/test_capital_structure_registration_lifecycle.py` (lifecycle admission).

### Summary table per issuer

| | CLNN | LPTH | EDBL |
|---|---|---|---|
| event_versions rows | 8 | 94 | 10 |
| candidates | 0 | 44 (+ their v1 twins, all blocked) | 4 (all blocked) |
| lifecycle records | 0 | 0 | 0 |
| deferred items | 0 | 44 × `correction_group_changed` | 2 (`correction_group_changed`, `ambiguous_current_event_version`) |
| absent families | instruments (producer ran, zero rows — ledger absent), cash_funding (no producer wired) | change_events (no producer exists) | share_basis (inputs absent), transactions (not wired nightly) |
| root cause (`file:line`) | `event_spine.py:201-206` — 424B5/8-K/10-Q are non-candidates; shelf S-3 never discovered | `registration_lifecycle.py:736-765` — enrichment read as group change; plus missing parent filings | `registration_lifecycle.py:736-765` — same, on the S-3 v1→v2 pair |
| minimal fix | backfill S-3 + content-based 424B5 classification (policy, no code today) | enrichment fix + discovery backfill of 22 shelves | enrichment tolerance at `registration_lifecycle.py:736-746`, mirroring `:1250` |
| proposed test file | `tests/test_capital_structure_event_spine.py` | `tests/test_capital_structure_registration_lifecycle.py` | `tests/test_capital_structure_registration_lifecycle.py` |

## DEVIATIONS

1. **Sparse materialization beyond the packet's list.** `data/capital_structure` was not
   sparse-tracked at the base (`worktree_sparse.py add data/capital_structure` → `not tracked
   at HEAD`); the packet's own fallback `add data` was used, plus read-only materialization of
   `contracts/` (the builder refuses without
   `contracts/capital_structure_document_term_observation.schema.json`),
   `.github/` (to quote `daily.yml`), and `research/` (to place this report beside the
   dossiers). No file was modified.
2. **Rebuild clocks.** The packet's exact `--as-of/--generated-at 2026-10-17T14:45:44Z`
   refused (`"generated_at cannot precede the verified generation clock"`); the rebuild used
   the verified generation's own clock `2026-10-17T14:45:44.820502Z` and the served
   projection's `generated_at 2026-10-17T15:25:17.094128Z`. The refusal and the retry are both
   quoted in §4.
3. **Counterfactual compiles.** Per the packet's allowance to call
   `compile_registration_lifecycles` directly, two counterfactuals were run in `/tmp/pgap/`
   on copies of real ledger rows (never on repository state) to prove the EDBL-only-blocker
   and the LPTH two-layer claims. One helper re-derives an event/edge id with the modules' own
   identity functions; no production artifact is touched.

## GAPS

None. All six questions are answered for all three issuers from quoted commands.
