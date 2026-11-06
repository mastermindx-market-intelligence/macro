# D03 W07 — Winner Health typed source availability

## Outcome and scope

Winner Health now distinguishes a missing, unreadable, malformed, invalid-date,
stale or producer-unavailable source from a valid empty or populated reading.
An unavailable source no longer promises that a nightly read will arrive, shows
no current price/backdrop/cohort cues, and is not an eligibility or market verdict.
English and Chinese copy share the same typed state. A stale read exposes only
its validated source date, not the build clock.

This extends the existing T43 source-date repair on **macro Draft #10709**, not a
new dashboard, ranker, publication plane, research result or release. The accepted
D03 Phase 2A remains at `e521f04dcc5afb4fb06152584d35c8a01dbe21ff` (78 capabilities /
53 acceptance cases). `WS:TOP-ANATOMY` remains the organizational owner; its R0–R6
and frozen OOT registration are unchanged.

## Source and custody

- Admitted base: `005232fa54edbc6d271a796db6b15d5cd7443641`.
- Accepted predecessor: `f9e62dfbecfcf33579ead45ad27cf7a38de734a7`.
  Its CI `41799365514` and fences `41799365457` passed. Those receipts do not
  certify this later W07 extension.
- Original branch:
  `claude/ssd-d03-winner-health-source-date-20261104-c2-c1a4065d36e086ff`.
- Protected procedure pin: Mastermind
  `75a6540519cf519edfef7633e74f57b68aef9329`.
- Root remained the sole writer of these four source/test paths and native board
  `11MU-0`; no competing live lease was observed. Historical #7073 has day-free
  warm-copy overlap but no current START/lease. Its branch was not adopted or
  modified. Original #9495/T004 and the held R8/Fabric effects remain untouched.

The browser receipt records the pre-commit `source_head` and **32 actual source /
asset SHA-256 hashes**, verified unchanged at completion. It does not mislabel
uncommitted bytes as the predecessor's Git tree. Committing these exact bytes
binds the proof to this delivery; current exact-head CI belongs in the existing
[D03 checkpoint](https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6623889088)
and original PR, not in a self-referential commit hash.

| Source path | SHA-256 tested |
| --- | --- |
| `scripts/build_winner_health_page.py` | `c6f12a4371f691da904a6cbd7ee05bc867a544c975c70301ed8f91521097b7ab` |
| `templates/winner_health.html.j2` | `4048a4ec1b08a935a11e1b31d8ff213cacb822a87225ff3d9ddf5915ea7856bf` |
| `tests/test_winner_health_page.py` | `fce606d48f11f7ef36c427f933980a45d5988364f1b8c2c9d0d257fb243e0704` |
| `tests/test_winner_health_source_dates.py` | `a534d9aef8098e8c1d7c715c6021a8a2a1bfc5d8f9304e244c8741de01bf33bc` |

## Availability contract and preserved behavior

The loader reads once and returns context plus a typed `{code, source_asof}`
receipt. Codes are `available`, `missing`, `unreadable`, `invalid_artifact`,
`invalid_date`, `stale` and `producer_unavailable`. The old `_load_context`
interface remains a compatibility wrapper. The renderer suppresses market cues
for any unavailable result.

Producer `null_reason` is arbitrary exception text, not a documented enum; it can
contain filesystem details. It is neither displayed nor mapped by keywords.
`null_state` only establishes a generic producer-unavailable state. Bad source
date and stale-source admission precede this producer state.

Unchanged contracts:

- More than **six calendar days** is stale; six days is still admitted.
- The independent tape warning begins above **five sessions**.
- Timestamp-prefix parsing, explicit historical `fixture=` bypass, legacy
  `states`, and existing future-date admission remain compatible. Preserving
  future-date admission is not a new endorsement of that policy.
- Valid empty/cohort/row-level `no_read`/unreadable-tier/no-analogue states remain
  distinct from page-level source failure. Three cohorts, overlap counts, full
  and thin analogue strata, research populations and authority fences remain.
- No engine, threshold, ranking, producer schema, live data, generated repository
  site output, auth, scheduler or publication-control-plane change.

## Deterministic and minimal-dependency proof

- Expanded source suite: **85 cases**, adding 51 to the accepted T43 suite.
- RED on unchanged predecessor source: **53 failed / 32 passed**.
- Final focused aggregate: **196 passed** across source dates, page behavior,
  maturation and design freeze. Retained warm-copy assertions were updated to
  truthful typed copy; no assertion was disabled or test suppressed.
- Clean Python **3.12.13** with only pytest / PyYAML / Jinja2 and their transitive
  dependencies: **85 passed**, data guard enabled, process exit 0.
- Three existing scope/manifest guards: **3 passed / 235 deselected**. Existing
  code and data owners already select the expanded suite; no new job, suite,
  scope narrowing, weight override or pack-limit change is part of W07.
- Added-line design ratchet: zero blocking findings. `git diff --check` passed.
- Exact existing combined `public-render-fastlane` command: **419 passed /
  1 pre-existing deselection**, in the same clean three-dependency environment.
- Exact existing combined TOP/Winner Health command: **420 passed**, in a new
  isolated Python 3.12 environment installed from the unchanged
  `falsifier-tripwires` dependency line. No dependency or CI manifest was edited.

Focused command:

```sh
python -m pytest tests/test_winner_health_source_dates.py tests/test_winner_health_page.py tests/test_top_maturation.py tests/test_winner_health_design_freeze.py -q --tb=short
```

Test-isolation reconciliation: an earlier 85-assertion pass had an overall failed
process because the guarded tests overlapped official sparse materialization of
`mockups`. The transient data/site deletion view was reconciled after that
operation completed: no data/site diff, no user bytes lost, no guard disabled.
The final fixture also redirects `lib.config.ROOT` and resets the shared-page
shim so publication and asset copies stay in a disposable root. Both the minimal
85-case and aggregate 196-case commands then passed with exit 0; the final
browser proof was rerun against those exact test bytes.

The broader public command first found omitted sparse-checkout fixtures
(19 failures, then one remaining glossary asset-pair failure). Missing fixture
and named asset bytes were materialized from the exact tracked index without
overwriting existing files or regenerating data/site; the unchanged command then
passed 419 tests. An initial TOP command used the unrelated six-dependency Pick
Lab environment and stopped at two collection errors for missing `requests`.
The correctly isolated environment with the existing data job's declared
dependencies passed all 420 tests. Final data/site diffs were empty and guards
remained enabled; no failed process is represented as an overall pass.

## Real builder and browser proof

`verify_browser.py` SHA-256:
`206cce48a8c1137c54843ee649564f2eeb1e17df8ddb8ce3d763f1e24479ec2e`.
Final receipt: [browser/browser-proof.json](browser/browser-proof.json).

**144 cases / 148 screenshots**, Chromium **151.0.7922.34**:
12 actual-builder states × 320/390/1440 widths × light/dark × EN/ZH.
States: missing, real directory-read failure, invalid JSON, non-object payload,
invalid date, stale, producer-null, valid empty, populated, five-session lag,
six-session lag, and six-calendar-day age plus six-session lag.

Every fixture enters the normal `build` → `write_page` path, not `fixture=`;
uses frozen calendar day 2026-11-04; and replaces a prior sentinel page in an
isolated root. Source artifacts remain unchanged. Populated fixtures retain
three cohorts and the distinct research/row states described above.

Verified actual runtime theme/language/fonts, text contrast over gradients,
narrow-screen wrapping, overflow/clipping, reduced-motion preference, native
Tab focus on retained header links, and real Enter/hash jumps into existing
cohort targets. Minimum measured text contrast: **5.8884:1**. There were **zero
page errors, asset errors, failed responses or blocked network requests**.
All successful responses came from candidate/generated fixture bytes.

The runner initially assumed the first visible header link was always Home;
actual mobile navigation exposes Terminal first. This was a harness defect,
corrected against retained `_site_nav.html.j2` / `_navlinks.html.j2` source.
No shared navigation was changed. Link presence/focus is proved; a Home/Terminal
destination load, production authentication or external routing is **not**.
The generic fallback state is unit-covered, not falsely forced into this browser
matrix. Local Node is 26.5.0; no local Node 20 result is claimed.

Representative self-QA screenshots:

- [Missing, 320 Light EN](browser/missing-320-light-en.png)
- [Stale, 320 Dark ZH](browser/stale-320-dark-zh.png)
- [Producer unavailable, 390 Light EN](browser/producer-null-390-light-en.png)
- [Populated, 1440 Dark EN](browser/page-populated-1440-dark-en.png)

## Native Paper and canonical capture

Native file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-D-0`, board **`11MU-0`**.
The 960×700 component board contains desktop Light EN stale-state and 320px Dark
ZH unreadable-state references. It is not a full-phone or cross-product board.
Screenshot self-QA found dark heading inheritance; the root repaired only its
owned nodes with existing tokens, inspected again, then extracted JSX and
finished the operation.

- [Actual Paper screenshot](paper-11MU-0.jpg)
- [Post-QA JSX](paper-11MU-0.jsx)
- [Finish / hash receipt](paper-receipt.json)
- Operation `d03-w07-availability-component-finish-20261104-c2`:
  **APPLIED_RESPONSE_OBSERVED**.
- Snapshot `989079ab7271f971a2886d4d7cbe3968ce15a3050d6385cba3fa00dd8510100b`.
- Shared token hash `640746f9` unchanged; active page and other boards untouched.

Repository canonical evidence is at
`mockups/refs/d03-winner-health-availability-20261104/`: **16 real captures**
(8 rest + 8 native header-focus), desktop/mobile × EN/ZH × light/dark, using the
actual stale-page HTML and retained served assets. Its HTML SHA matches the
stale build in the 144-case receipt. The unmodified visual-evidence gate passed.
The canonical HTML is retained byte-exact in deterministic `stale.html.gz`;
compression avoids treating inherited generated whitespace as an authored-code
diff while preserving the exact decompressed proof hash. Captured bytes were
not post-edited or reclassified.
No console errors or failed responses were observed in that capture. Canonical
metrics, including retained-shell layout shift, are recorded honestly; this is
not a whole-page performance or shared-shell acceptance claim.

## Completion boundary and continuation

Source/browser/component proof is complete for this bounded W07 availability
slice. Run the actual committed-tree differential gate, publish **on the original
#10709 branch**, and record exact-head hosted CI on the existing D03 checkpoint.
Do not redo accepted matrices without a source or material acceptance change.

**Draft / HOLD. No Ready, un-draft, label, enqueue, auto-merge, merge or deploy.**
After lawful integration/release, the normal served Winner Health journey and
freshness remain separate acceptance work. Final F01/F02 joint v1, whole-D03
composition, original held effects, research OOT and production acceptance are
not cleared by these receipts.
