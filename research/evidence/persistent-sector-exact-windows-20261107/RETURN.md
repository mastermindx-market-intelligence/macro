# PSL exact-window measurements — bounded qualification correction

Run: `psl-exact-window-binding-fix-20261107-c4`
Parent/root: `persistent-sector-leadership-20261106-c4` (PR #10806)
Repository: `mastermindx-market-intelligence/macro`
Status: **COMPLETE — candidate committed locally; parent retains integration and release.**

---

## 1. Exact identity

| Fact | Value |
|---|---|
| Exact base | `5b4962a381711328cc01dbe788f9ca4b5f4f7e4d` |
| Returned candidate commit (unpushed, absent from the remote) | `a7774a2c8751e94f33769c6e96c62cf2d6e931e0` — **not present on origin** (`upload-pack: not our ref`) |
| Returned candidate tree | `3abf594c0b7b3c3428aa86c4580f7930a14ccb53` |
| Local baseline commit (input applied to base) | `af952119ec45541082ec8ce7f64800862669abaf` (tree `3abf594…`) |
| **Candidate commit (this run)** | `f55dda94ca7fe283e7066ceaad2d9438956062d9` |
| **Candidate tree** | `e02f5323f418f5333634f3c16e4e970e15b0943a` |
| Branch | `claude/psl-exact-window-binding-fix-20261107-c4` (local only, **not pushed**) |
| Workspace | `/home/ubuntu2/lanes/repos/macro/.claude/worktrees/psl-exact-window-binding-fix-20261107-c4` (sparse profile from `config/sparse_worktree.json`, base `5b4962a`) |

## 2. Input extraction and proof

Source input read from the two canonical PR #10806 comments through the
authorized repo GitHub reader (`/repos/mastermindx-market-intelligence/macro/issues/comments/{id}`):

1. comment `6704194406` → part 1, fenced diff after `PSL_EXACT_INPUT_PART_1_BEGIN`
2. comment `6704194779` → part 2, fenced diff after `PSL_EXACT_INPUT_PART_2_BEGIN`

| Fact | Expected | Observed |
|---|---|---|
| Complete patch bytes | 98222 | **98222** |
| Complete patch SHA256 | `71c3223a167cedf861bd7d46ef6ceaecab5b39b2846e0a7620498f86437a86bb` | **identical** |
| Reconstructed tree after applying to base | `3abf594c0b7b3c3428aa86c4580f7930a14ccb53` | **identical** (byte-identical to the returned candidate) |

Extracted patch retained at `psl_exact_input.patch` in this artifact directory.
No source was reconstructed from prose; no guessed fetch; no host or provider switch.

Post-application hashes (before repair) — all four matched the brief exactly:

| Path | SHA256 | Match |
|---|---|---|
| `engine/leadership_rotation_context.py` | `f541a88cf593df1b4fc8ba3433eb8c5673989511cd4185e6b53766a46b98093a` | yes |
| `tests/test_leadership_measured_read.py` | `3294a5d061dcf55728812f90cb1c2af4b44e5098e97064fd70990bdaeb7ead04` | yes |
| `tests/fixtures/leadership_rotation/sector_window_measurements.complete.v1.json` | `36dd29c106a05ba211d2de0c95fd51ee146897bae1d017bf9e1f7b4d1b01f28a` | yes |
| `tests/fixtures/leadership_rotation/sector_window_measurements.unavailable.v1.json` | `8966899769d9e39c8759ccd085d1572f34dd478a671b5033bcf0519359dc952c` | yes |

## 3. Final candidate file hashes

| Path | SHA256 | git blob id |
|---|---|---|
| `engine/leadership_rotation_context.py` | `43b1cf3a19d3f73dc6a29a319bcc81f3745cda153c3419e492396b48b9068c61` | `270f5a90d1b9bbaaf6fc074ad04a900339de8efe` |
| `tests/test_leadership_measured_read.py` | `77e6e124cb0168e9d7e90ba1a9e3df0a5ca46b8b2d6cf5cda0eaddae5068d3f3` | `d100936525b192643f90e7a2d594fe820c9964d1` |
| `tests/fixtures/leadership_rotation/sector_window_measurements.complete.v1.json` | `6b33895711742dee8cb1366baab5572a6aef31d6ca9ca6d0f81e32ab879e6dae` | `eededaf6779450303fc63d0a7ba836a614e35954` |
| `tests/fixtures/leadership_rotation/sector_window_measurements.unavailable.v1.json` | `e4419e3a4d7dabce4ad4fd760c1fc37d05b8fe1111102ac5b0bb13b1a980f17e` | `c1e17612121267b92922c0dc272b28e72cc14159` |

**Only these four paths changed.** `git diff --name-only 5b4962a… HEAD` lists exactly
these four; the working tree is clean.

Diff vs the **supplied candidate** (`af95211` / tree `3abf594`):
`engine/leadership_rotation_context.py` +279, `tests/test_leadership_measured_read.py` +289,
each fixture 1 line — `4 files changed, 533 insertions(+), 39 deletions(-)`.

Diff vs the **exact base** (`5b4962a`): `4 files changed, 3226 insertions(+), 1 deletion(-)`.

## 4. The four repairs

### 4.1 Post-scaling finiteness (published percentages)
`_window_pct` / `_window_publication` validate finiteness **after** the ×100
scaling for every published absolute, relative and common-benchmark percentage.
A finite fraction near 1e307 overflows the percent scale; the publication is
now null with the stable `non_finite_input` reason instead of an infinity, and
the block still encodes under `json.dumps(out, allow_nan=False)`. An
unpublishable benchmark leaves the member's absolute qualified and its
relative unknown — the same coupling a missing benchmark already had. The
relative-wealth formula, the six-endpoint 5-session span and the six-endpoint
gaps/coverage semantics are unchanged.

### 4.2 Composition bound to the parent generation
`_assert_window_composition_compatible` binds the requested composition to
`result.generation` **before** attachment: `source_session == end_session ==
generation.session_end`; normalized benchmark == `generation.benchmark`;
`cohort_id == generation.cohort_id == US_SECTOR_COHORT_ID`; `price_basis ==
generation.price_basis == total_return`; published population exactly the
native eleven ETF identities in order; published windows exactly `[5,20,63]`.
An unknown or malformed parent identity cannot qualify a populated output.
An unbound composition raises `ValueError` (the module's documented
programmer-error convention) — never attached, never dropped, never restamped;
no generation or compatibility key is minted. `measure_sector_windows` stays
pure and standalone. No legacy row/status availability is required and
`new63 == legacy rs63` is not used as admission.

### 4.3 Bounded, detached source binding
`_window_binding` keeps only the existing seven top-level keys and now bounds
them: short control-free strings (`_window_text`), a strict `YYYY-MM-DD`
session date, clocks that are each null or a **bounded timezone-aware** ISO
timestamp (a naive wall-clock timestamp names no instant and is refused), and
a receipt that must be finite, JSON-publishable, cycle-free and within
byte/depth/container/node budgets, published as a **detached** copy so no
mutable reference crosses into the block. The receipt stays opaque metadata;
no registry, no invented grant shape, and a synthetic `capture_id` stays
synthetic. Supplied clocks/receipts still establish no freshness, availability
or point-in-time admission by themselves. Malformed *data* remains total.

### 4.4 Canonical US session calendar
The test calendar is now derived from **`lib.nyse_calendar`** — the incumbent
canonical US session owner that `engine/session_anchor.py` binds the US market
to — instead of a weekday approximation that counted US Labor Day 2026-09-07
as a session. The 63-session window starts on the canonical **2026-08-07**
(the weekday approximation started on 2026-08-10). Exact N-position start/end
semantics are preserved and asserted against the owner itself. A holiday-gap
counterexample proves a capture row on the holiday is never promoted to a
session and never moves an endpoint. No new calendar owner, collector or
external dependency was added.

**Fixture consequence (expected and disclosed):** both frozen window fixtures
were regenerated. The **only** byte that moved is the 63-session
`start_session` (`2026-08-10` → `2026-08-07`); every measured value is
unchanged, because the synthetic price path is index-based. The closed
`sector_dossiers/v1` block, the legacy `measured_read_v1` fixture and the legacy
default read bytes are **untouched**.

## 5. Commands, exits and receipts

| Command | Exit | Result |
|---|---|---|
| `python3 -m pytest tests/test_leadership_measured_read.py -q` | 0 | **124 passed** |
| `python3 -m pytest tests/test_leadership_rotation_contract.py tests/test_leadership_rotation_countercases.py tests/test_leadership_rotation_run.py tests/test_sector_central_paper.py -q` | 0 | **261 passed** (9 pre-existing `RuntimeWarning`s in `scripts/leadership_rotation_run.py`, unrelated) |
| `python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index N --pack-count 12 --plan-only` (N = 0…11) | 0 | all 12 agree: `Planned 389 of 389 legacy jobs into 12 packs; plan sha256=336f8cb9996613150a0cfb0e9f9155c5b9dc7d9059890b4783c755635ecc25f5` |
| `python3 scripts/check_contract_delta.py --base 5b4962a381711328cc01dbe788f9ca4b5f4f7e4d` | 0 | `0 introduced, 0 inherited (base 5b4962a38171)`, wall 369.0 s |

**Failing-before receipts** (captured against the *unmodified* input state:
engine blob `f541a88c…`, tree `3abf594…`, in a disposable worktree):

- `receipt_before_input_state.txt` — `10 failed, 1 passed`:
  `test_w25_complete_fixture_is_frozen`, `test_w26_unavailable_fixture_is_frozen`,
  `test_w32_…percent_scale…` (DID NOT RAISE / not null),
  `test_w33_the_companion_must_be_bound_to_the_parent_generation` (DID NOT RAISE),
  all five `test_w34_an_unbound_composition_is_never_attached[…]` variants
  (DID NOT RAISE), `test_w36_the_source_binding_is_bounded_and_published_detached`
  (DID NOT RAISE).
- `receipt_before_calendar_state.txt` — `test_w37_…` fails on the original
  weekday helper: `AssertionError: assert '2026-09-07' not in [...]`.

**Passing-after receipts**: `receipt_after_candidate_state.txt` (`11 passed`),
`receipt_after_neighbouring_owner_tests.txt` (`261 passed`),
`receipt_after_ci_pack_plan_only.txt`, `receipt_after_contract_delta.txt`.

## 6. Preserved properties (all asserted by the passing suite)

Relative-wealth formula · six endpoints for a 5-session return · the same T
across all sectors and SPY · no endpoint rolling · gaps disclosed as coverage ·
no ambient reads or clocks · all eleven identities and the all-null case ·
hard-false authority flags and no forecast · input immutability · legacy
`measured_read_v1` byte parity · closed `sector_dossiers/v1` byte parity ·
`measure_sector_windows` purity · strict JSON encoding (`allow_nan=False`) on
adversarial finite inputs.

## 7. Boundaries respected

No push, no PR, no merge, no deploy, no publication. No CI registration
edited, no lock or parent/index edit, no data capture/loader/provider/runtime
change, no new service, no package install, no worker spawn, no paid Fabric.
Only the four permitted paths changed. No source freeze was claimed — the
parent retains integration and release.

**Next dependency:** the parent verifies this correction, integrates commit
`f55dda94ca7fe283e7066ceaad2d9438956062d9` onto its branch, and owns the
release. The two regenerated window fixtures are a reviewable consequence of
repair 4 and should be confirmed as such at integration.
