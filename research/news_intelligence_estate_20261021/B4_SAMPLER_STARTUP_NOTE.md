# Sampler share-cap startup behaviour — ni-sampler-1 (B4 adjudication note)

Lane NEWS-ORCH3-SAMP, seat 602cd180 (ORCH-3 QUANT), 2026-10-31. Base `6135e2c3c64c`.
This note adjudicates whether the `_share_ok` STARTUP semantics pinned by the new test
module are (a) the behaviour the registered draws were actually produced with, and
(b) still the behaviour of the current code. It contains a PROPOSAL only — no code
change to the sampler is made or proposed for adoption here.

## Strict separation

**600 registration cases / gated_v2 99 drawn of which 74 routed MATCH (scorable) / gated_v3 135 drawn / 40 NEW cases routing-pending / 0 prospective.** The 135 drawn are not 135 scored or gold cases. A shared group id does not transfer a label, a verdict or independence across versions, assets, clocks or horizons. Cluster/group ids are never evidence of independence.

## The behaviour

`engine/news_impact/sampler.py:274-282`, quoted verbatim (base `6135e2c3c64c`):

```python
def _share_ok(used: int, total: int, cap: float) -> bool:
    """True when admitting one more counted item keeps the share <= cap.

    Integer cross-multiplication at a fixed 1e6 scale so 20/200 <= 0.10 is exact
    at the boundary regardless of binary float noise.
    """
    num = round(float(cap) * _SHARE_SCALE)
    return (used + 1) * _SHARE_SCALE <= num * (total + 1)
```

The rule is evaluated **at admission time, over the counter so far**. With an empty
counter (`used == 0`), the first counted item is admitted only once enough
uncounted items have already been admitted: `ceil(1/cap) - 1` of them. For the
registered `megacap_share_cap = 0.10` that is 9 uncounted items first; for the
`economic_cluster_cap = 0.25` it is 3. A candidate refused by this rule is skipped
(`continue`) and never revisited — order, not final share, decides.

Boundary table as pinned by `tests/test_news_impact_sampler_startup.py`
(`test_share_ok_boundaries_as_registered`, all passing):

| used | total | cap | result | arithmetic |
|---|---|---|---|---|
| 0 | 0 | 0.25 | **False** | 1/1 > 0.25 — empty counter refuses the first counted item |
| 0 | 2 | 0.25 | False | 1/3 > 0.25 |
| 0 | 3 | 0.25 | True | 1/4 == 0.25 exactly |
| 0 | 8 | 0.10 | False | 1/9 > 0.10 |
| 0 | 9 | 0.10 | True | 1/10 == 0.10 exactly |
| 19 | 199 | 0.10 | True | 20/200 == 0.10 exactly (integer scale, no float noise) |
| 20 | 200 | 0.10 | False | 21/201 > 0.10 |
| 56 | 99 | 0.57 | True | 57/100 == 0.57 exactly (a naive float compare says False) |

Also pinned: `_SHARE_SCALE == 1_000_000`; the startup ramp
`[_share_ok(0, t, 0.25) for t in 0..4] == [F, F, F, T, T]` and
`[_share_ok(0, t, 0.10) for t in 0..10] == [F]*9 + [T, T]`; and the draw-level
consequence — a mega-cap FIRST in hash order is skipped even when the final share
(1/4 == 0.25 at target 4) would satisfy the cap, while the same pool with the
mega-cap LAST in hash order admits it at exactly that final share.

## Did it change which cases the registered gated_v3 draw admitted?

Measured during a byte-identical replay of the registered gated_v3 draw
(seed 20261014, `ni-sampler-1`), with a recorder wrapped around `S._share_ok` that
calls the original (verified: the replay under the recorder stayed byte-identical,
so the measurement observed the registered behaviour without altering it):

- total `_share_ok` calls: **24**
- calls refusing (result False): **18**
- **startup refusals — refusal on an EMPTY counter (`used == 0`): 2**
- refusals in the startup region (`total < ceil(1/cap) - 1`), by cap: **cap 0.10: 2**;
  the economic-cluster cap 0.25 never appears — the tape_draw path passes no
  `economic_cluster` callable, so all 24 calls were mega-cap calls at cap 0.10
  (distinct cap values seen: `[0.1]`)
- the other 16 refusals all had `used > 0` (mid-stream cap pressure after admissions)

So during the registered draw the startup condition refused an admission exactly
**2 times**, both on a completely empty counter — the earliest possible point of
the ramp. Each refused candidate is skipped and never revisited, so these 2
admission opportunities did not reach the draw. What the note does **not** claim:
whether an `admit_first` rule would have admitted a different case set — that is a
counterfactual under a different admission rule (a different sampler version), and
no such draw was run. The honest statement is narrower: **the registered draw was
produced WITH this startup behaviour, it is byte-identically reproducible with it
in place, and the pinned semantics are exactly the semantics the registration
carries.** The 135 drawn cases are the registered 135 drawn cases, unchanged.

Per-item attribution (WHICH item_ids were refused): **UNMEASURED.** The candidate
is in scope of the call site (`sampler.py:465-490`), but the recorder wrapper sees
only `(used, total, cap)`; wrapping the enclosing loop would require an engine
edit, which this lane may not make. The receipts carry no skip/startup counter:
`draw_report.json` has none of `skip*`/`refused*`/`startup*`;
`manifest.json` carries `rights_refused: 0` (a rights counter, not this rule),
`megacap_share` per template, and `megacap_share_cap: 0.1` — no startup count.

## Reproduction of the registered gated_v3 draw

**REPRODUCED BYTE-IDENTICAL** — cases + manifest + draw_report, all three.

Inputs (read-only lane host, never committed): all four sha256 OK against
`CENSUS.md` §1, and the committed fallback ledger matches its recorded value:

| Input | sha256 | OK/BAD |
|---|---|---|
| `items.parquet` | `bab574014865532c63977e44f12be0e8a3234ba9faa8253d2717e43d67580e17` | OK |
| `event_log.parquet` | `2345274391433d6e448a5cce9c70bea9c9a1c4efd26f6ef2f7f9106ef185ac18` | OK |
| `reject_sample.parquet` | `5aed74fdc6adb208064005ad2b2634a91287d4a43f8eddecae2335cb0f6beeb0` | OK |
| `ticker_cik_ledger.json` | `6fe2459b360e16f5da1ac7f659feafb0eee3d11bb6c6477ff4fc05d4bf74621e` | OK |
| `sec_fallback_ledger.json` (repo, base) | `b046d8515b2a5ea9e26680011a3afd8d46c15689e2ea82ffb32b7be6a956494c` | OK (== CENSUS §1 recorded) |

Classifier pin (working-tree only, never committed): `engine/news_common.py` set to
blob `ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156` (the CENSUS §2 deviation pin, from
commit `6fc028727a5a`), verified via `git hash-object`; BASE blob
`71e153136d66dad02239325a6927510a965d7026` restored after the draw and measurement,
`git status --porcelain` clean of `engine/` afterwards.

Interpreter: the r2 venv `Python 3.12.13` (pandas 3.0.6, pyarrow 26.0.0; pytest
9.1.1), `PYTHONPATH=.`, command per `issuer_fallback/README.md` "Next draw:
gated_v3" step 4 (`tape_draw --seed 20261014 --body-frame …/status_map.json
--gate-frame …/gates2_map.json --fallback-ledger …/sec_fallback_ledger.json
--candidates-out …`), frames and registered artifacts read from commit
`01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` (FETCH_HEAD verified), outputs to lane
scratch. rc=0; `cases: 135`; the run's own summary printed
`manifest_sha256 0429d76e9931caafbde34fccde80ef8a1da12a89996d5b2680ea037f46575f09`.

| File | reproduced sha256 (raw bytes) | registered sha256 (raw bytes) | identical |
|---|---|---|---|
| `cases.jsonl` | `7b0b9df76539bfc4f433045e6f3f529d9f25a6842ccd134d937d748bf1035746` | `7b0b9df76539bfc4f433045e6f3f529d9f25a6842ccd134d937d748bf1035746` | **YES (cmp)** |
| `manifest.json` | `81355b1d36467fa7af56c0635885e2ef2b6ec36f1be8106ce6b0061e44fab56f` | `81355b1d36467fa7af56c0635885e2ef2b6ec36f1be8106ce6b0061e44fab56f` | **YES (cmp)** |
| `draw_report.json` | `7beac17e8fa3cb18b3d887367305731b6405922936d4f3a542fda16c1fe479b3` | `7beac17e8fa3cb18b3d887367305731b6405922936d4f3a542fda16c1fe479b3` | **YES (cmp)** |

Manifest field hashes recomputed the way `build_manifest` computes them:
`cases_sha256` over the canonical JSON of the 135 case dicts =
`c4c98483812029abdbeb6a5f9254d3b893128366097169d4731bb44a5cae5ca5` = stored (MATCH);
`manifest_sha256` over the canonical JSON of the manifest without its self-hash =
`0429d76e9931caafbde34fccde80ef8a1da12a89996d5b2680ea037f46575f09` = stored (MATCH).
The raw-file sha256 values differ from the manifest fields by construction
(canonical JSON vs file bytes); the byte-identity claim rests on `cmp` of the raw
files plus the field recomputation, both given here.

`draw_report.json` diff: none — `cmp` identical, no differing keys.

No repo fixture was added: the inputs are 10.8 MB of tape on the lane host
(`items.parquet` 10,774,070 bytes; all four inputs together 11,057,480 bytes), the
evidence is the hash table above. The `candidates_meta.jsonl` side file tape_draw
writes went to lane scratch and is not committed (same handling as the registered
run's CENSUS §2 deviation).

## Test module

`tests/test_news_impact_sampler_startup.py` — 12 tests (8 boundary parameter
cases + scale + startup ramp + first-in-order skip + last-in-order admit);
self-contained helpers copied from `tests/test_news_impact_sampler.py`.

Registered run line (`.github/ci/legacy-jobs.yml`, "news impact phase 1 leaf"
step, base line 43298):

```
python -m pytest tests/test_news_impact_validate.py tests/test_news_impact_hostile.py tests/test_news_impact_sampler.py tests/test_news_impact_sampler_startup.py tests/test_news_impact_cluster.py tests/test_news_impact_issuer.py -q
```

Closure guard `python3 scripts/check_ci_trigger_closure.py` -> rc=0
("OK — every module a gated suite reads can start the job that runs it"; 3376
suites, 0 trigger gaps).

Pytest (r2 venv, `PYTHONPATH=.`):
`tests/test_news_impact_sampler_startup.py tests/test_news_impact_sampler.py -q
-p no:cacheprovider` -> **56 passed in 1.01s** (12 + 44); the new module alone ->
**12 passed in 0.74s**.

Discrimination proof: monkeypatching `_share_ok` to the admit-first variant
`lambda u, t, c: (u + 1) * 1e6 <= round(c * 1e6) * (t + 1) or t == 0` and re-running
the two pinned bodies raises `AssertionError` in both:

```
test_share_ok_boundaries_as_registered_one_case: AssertionError
test_startup_refuses_first_counted_item_until_enough_uncounted_precede_it: AssertionError
variant _share_ok(0,0,0.25) = True            (registered expectation: False)
variant [cap0.25 t=0..4]    = [True, False, False, True, True]
registered expectation      = [False, False, False, True, True]
```

So the module does not merely pass — it fails against a plausible variant of the
rule and would catch a regression to admit-first semantics.

## PROPOSAL (no code change)

**PROPOSAL — not adopted, not implemented.** A flag-gated alternative for a future
sampler version:

- New `SamplePlan` field `share_cap_startup: Literal["refuse_until_fit", "admit_first"] = "refuse_until_fit"`.
- `"refuse_until_fit"` (the default) reproduces the current `_share_ok` gate exactly
  and therefore every registered draw byte for byte, registered artifacts being
  frozen bytes that are never re-rendered.
- `"admit_first"` would evaluate the share cap only once the counter is non-empty
  (equivalently: `used == 0 -> True`), admitting the first counted item of a cell
  and letting the running share clamp later admissions.
- The manifest/plan hash would change whenever the field is set to a non-default
  value, and a default value must be omitted from the serialized plan block (or the
  plan-hash recipe changed under a version bump) so that default-mode manifests
  stay byte-identical to the current recipe.
- Consequence, stated as law: because the plan hash changes under the non-default,
  the flag can only ever ship as a **NEW sampler version + NEW draw** — never a
  redraw of gated_v2 or gated_v3. What would have to be re-registered under an
  `admit_first` draw: a new sampler version id (successor to `ni-sampler-1`), the
  new draw's `cases.jsonl`/`manifest.json`/`draw_report.json` with their hashes, a
  fresh census of that draw, and routing verdicts for every case NEW to it (only
  MATCH scores); existing gated_v2/gated_v3 registrations and their 74-scorable /
  135-drawn / 40-NEW bookkeeping stay frozen and untouched.

## Evidence

Commands and outputs (base `6135e2c3c64c`, lane scratch `~/lanes/tmp/news-orch3-samp-r2`,
read-only lane dirs `ne-b4-gated-v3-20261022-r3` (inputs) and `…-r2` (venv)):

1. `git rev-parse HEAD` -> `6135e2c3c64cd62258f176b234c6bb27960e3adb`; `git status --porcelain` -> empty; branch `lane/news-orch3-samp-r2`.
2. `$VENV -c 'import pandas, pyarrow; …'` -> `3.0.6 26.0.0`; `$VENV -m pytest --version` -> `pytest 9.1.1` (no deviation needed).
3. `grep -c "tests/test_news_impact_sampler.py tests/test_news_impact_cluster.py" .github/ci/legacy-jobs.yml` -> 1 (one match); python3 insert of ` tests/test_news_impact_sampler_startup.py`; `git diff --stat` -> 1 file, 1 insertion, 1 deletion.
4. `python3 scripts/check_ci_trigger_closure.py; echo rc=$?` -> `…TRIGGER GAP: 0 … OK`, `rc=0`.
5. `git fetch origin 01f9e0a50f17879f5a13a5fe10eff14c52fb4cc2` -> `FETCH_HEAD-OK`; artifacts extracted with `git show $B4:<path>` into lane scratch (frames + gated_v3 files).
6. `sha256sum $W/b4/cases.jsonl $W/b4/manifest.json` -> `7b0b9df7…`, `81355b1d…`; manifest field recomputation -> both MATCH (see table above).
7. `sha256sum $R3/in/…` -> all four == CENSUS §1 expected (OK lines above).
8. `git show ea8ada59ea34cbba3b55c2bdaa1f72a5c0a58156 > engine/news_common.py` -> `PIN-OK` (`git hash-object` = `ea8ada59…`; `git status --porcelain` = ` M engine/news_common.py` + owned files).
9. `PYTHONPATH=. $VENV -m engine.news_impact.tape_draw … --seed 20261014 …` -> rc=0, `{"cases": 135, "manifest_sha256": "0429d76e…"}`; `sha256sum $W/v3/*` + `cmp` vs `$W/b4/` -> all three IDENTICAL.
10. `$VENV $W/measure.py` (recorder around `S._share_ok`, argv as step 9 with `--out $W/v3m --candidates-out $W/candm.jsonl`) -> rc 0; byte-identity v3m vs v3 OK; counts as in §"Did it change…" (24 / 18 / 2 / caps `[0.1]` / 16 mid-stream).
11. `grep -o '"[a-z_]*\(skip\|refus\|startup\|share\)[a-z_]*"[^,}]*'` over receipts -> `rights_refused: 0`, `megacap_share`, `megacap_share_cap: 0.1`; no skip/startup counters.
12. `git checkout -- engine/news_common.py` -> `RESTORE-OK` (`git hash-object` = `71e153136d66dad02239325a6927510a965d7026`); `rm -f $W/cand.jsonl $W/candm.jsonl` (headlines; never kept).
13. `PT -m pytest tests/test_news_impact_sampler_startup.py tests/test_news_impact_sampler.py -q -p no:cacheprovider` -> `56 passed in 1.01s`; discrimination heredoc (never committed) -> both AssertionError lines as quoted above.
