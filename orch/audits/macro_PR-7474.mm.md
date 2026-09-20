# Plain-language / theme / validated-claims audit — macro PR #7474

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-19.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7474 |
| title | `fix(briefs): wire recurring producer to incumbent Supabase runtime` |
| head | `1235362671e2241a30c6e6bfb339dd632cc97135` (40-hex; re-measured against the branch object via `git show 1235362671…`) |
| merged | 2026-09-20T03:51:57Z (24-h window) |
| merge commit | `ef9880ea9cbd85284dc8bc61211189dd29849f94` (squash — single-commit shape with `fix(briefs):` subject) |
| half-B child | MO-PAID-032 recurring-Briefs producer runtime-wiring repair; closes a gap that left the producer read-unavailable even when later armed |
| owner | `mastermidx4 <chatgpt4@mastermind-x.com>`; merge author identical |
| diff scope | **3 files**, 18 insertions / 5 deletions — `.github/workflows/daily.yml` (+4/-2), `.github/workflows/weekly.yml` (+4/-2), `tests/test_recurring_briefs.py` (+10/-1). Zero template / engine / CSS / JS / evidence bytes touched. |
| owned files vs `gh pr view --json files` | Re-measured: `git show ef9880ea9… --stat` confirms the 3-file scope exactly. `templates/**`, `site/**`, `scripts/**`, `engine/**`, `mockups/**`, `lib/**` are zero-diff. |
| base | `origin/main` was at `9a481ef520` (prophet-stage) and `b95b8587a5` (prophet-us) when fetched 2026-09-20 06:30Z; the merge sits between those and `b24bfa533a` (whitehouse alert) per `git log origin/main`. The body claims a "GitHub secret-name inventory on 2026-09-20" — that is a runtime check the author ran before opening, not a base SHA claim. No seat-correction block. |
| live readback | Not browser-verified — body explicitly states no render ran ("Composer, settled/live builders and settled risk artifact are byte-identical to base" is from PR #7482's body, NOT this one; this PR's body does NOT claim render identity because no render was needed: workflow YAML + a unit test, both green via 73 pytest passes). |

The PR body is short, factual, and surgical — a half-B repair shape. It declares the inventory finding (`SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_URL` are not provisioned; `SUPABASE_SERVICE_KEY` is; `RECURRING_BRIEFS_ENABLE` is absent and stays off by default), the three behavioral changes (one env var swap, one secret not injected, dormant gate untouched), and the proof (73 tests passed). It explicitly does NOT add a credential, scheduler, queue, or alternate producer — i.e. the "no new surface area" promise is the entire change. No seat-correction block, no executor-vs-seat dispute, no dispute at all — the seat-correction pattern only fires when the executor typed wrong facts into the body, and this PR's body is too short to drift.

## Plain-language findings

This PR adds **zero user-facing copy**. Diff inspection confirms: every changed line is YAML, Python test assertion, or a YAML comment. The macro repo has no `scripts/check_plain_language.mjs` (that file lives in `mastermind-terminal/terminal/scripts/`); the doctrine's plain-language check applies to anything that lands on a rendered page, in a chat reply, or in operator-visible prose, and this PR lands in none of those surfaces.

1. **No new user-facing text was added.** The diff is YAML env wiring + test assertions + two short YAML comments. No template, no engine copy, no operator log string, no error message, no fallback sentence. The user's experience of `/macro.html` is unchanged because the producer hasn't actually run on the canonical cadence yet (the `RECURRING_BRIEFS_ENABLE` gate stays absent/off).
2. **YAML comments are honest operator documentation.** The two identical YAML comments in `daily.yml` and `weekly.yml` (lines ~4092 and ~215) read: *"Reuse the incumbent repo service-role secret already consumed by production Supabase jobs. The producer's SUPABASE_URL has a reviewed project default, so do not inject an absent secret as an empty string."* Three honesty properties worth noting: (a) the "incumbent" claim is verifiable — `SUPABASE_SERVICE_KEY` is the secret other Supabase-touching jobs use; (b) the "reviewed project default" claim is verifiable against `engine/recurring_briefs.py:41-42` which is `os.environ.get("SUPABASE_URL", "https://fsldfzlxyyavsuwqbceod.supabase.co")` — that default is the canonical Supabase project URL the rest of the repo uses (sibling worktree grep); (c) the "do not inject an absent secret as an empty string" rationale explains WHY the change is two-line (drop the `SUPABASE_URL` line entirely) rather than one-line (just remap the role key) — that's the actual defect, and the comment names it. Operator-facing internal prose, plain-language compliant, not user-facing.
3. **No banned-vocab risk.** Grep across the diff for design-doctrine banned terms (`score`, `rank`, `confidence`, `AIS`, `satellite`, `chokepoint`, `falsifier`, `percentile`, `validated`, `已验证`, `经验证`, `经过验证`): zero matches. The PR body uses the word "reviewed" once (in "reviewed project default") — that is operational fact ("this default was reviewed/approved before being added to the producer"), not the doctrine "validated" claim shape.
4. **No bilingual parity exposure.** No UI text added; EN/ZH parity is a non-issue. The producer's output copy (when it eventually runs) is owned by other PRs (F11-7b heal rounds), not this wiring fix.
5. **Test prose is honest.** `tests/test_recurring_briefs.py` adds four assertions (two per cadence) that lock in (a) the remapped role key, (b) the absence of `SUPABASE_URL: ${{ secrets.SUPABASE_URL }}` in the step, and (c) the absence of `SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}` in the step. The slicing (`ours = text[text.find("recurring briefs producer"):]; ours = ours[: ours.find("\n      - name: ")]`) is the right way to scope assertions to one step — it won't false-positive on a future, different env-block elsewhere. Test code is plain-language compliant by construction (asserts are boolean, not prose).

**Verdict:** PASS. No user-facing copy, no operator-facing prose that needs auditing beyond the YAML comment which is itself honest about why the change is two lines.

## Theme findings

The PR is **pure runtime plumbing**. Zero CSS, zero tokens, zero template, zero theme JS, zero visual artifact.

- `templates/**`: zero-diff (`git diff ef9880ea9~1..ef9880ea9 --stat -- templates/` returns empty).
- `site/**`: zero-diff (this PR does NOT regenerate any page bytes; `templates/dashboard.html.j2` is unchanged, so `site/macro.html` is unchanged).
- `engine/recurring_briefs.py`: zero-diff (the producer's env-var handling is the line-41-42 `os.environ.get("SUPABASE_URL", default)` shape that was already there).
- `scripts/build_recurring_briefs.py`: zero-diff.
- `templates/_risk_envelope_band.*.j2` etc.: zero-diff (those belong to other PRs — #7482 in particular).

What that means for theme checks:

- `scripts/check_design_system.py --mode report` would return its normal stack of pre-existing template debt (this PR does not introduce or retire any).
- `scripts/check_design_system.py --mode enforce-added --diff-file <diff>` is the diff-scoped shape — and the diff has zero template/CSS/JS lines to evaluate, so it would exit 0 vacuously.
- `scripts/check_runtime_style_injection.py` — no JS bytes touched, vacuous pass.
- `scripts/check_ui_visual_evidence.py --diff-file <diff>` — no PNG bytes touched, vacuous pass.
- The theme pair-check (`scripts/check_template_site_sync.py`) is a non-event here because no template or site byte changed.

The body claims "The owned JS pair is byte-identical" and "The global pair checker reports one inherited theme.css mismatch; both files are unchanged from base and the exact hashes are in pair-scope-proof.json" — those are exact phrases from PR #7482's body, NOT this one. This PR does not own any JS pair and does not need a pair-scope-proof receipt; the body makes no such claim.

**Theme verdict:** PASS (vacuous). No template, no CSS, no JS, no PNG. The change is two lines of YAML per workflow plus a test, and the only "visual" downstream effect — when the dormant gate is later armed — is whatever the producer already emits unchanged.

## Validated-claims findings

This PR makes **zero validated claims**. The body is operational: a secret-inventory finding, a three-behavior change list, and a test count. No promotion language anywhere.

Grep across the diff and PR body for the doctrine promotion vocabulary (`validated`, `已验证`, `经验证`, `经过验证`, `proven`, `calibrated`, `calibration passed`, `rank`, `percentile`, `AIS`, `satellite`, `chokepoint`, `falsifier`, `score`):

- PR body: zero matches.
- `daily.yml` diff: zero matches (the comment uses "reviewed" / "incumbent" / "absent" / "empty string" — operational vocabulary, not promotion).
- `weekly.yml` diff: zero matches.
- `tests/test_recurring_briefs.py` diff: zero matches on the doctrine vocabulary (the test does not assert any "validated" claim; it asserts env-var presence/absence, which is binary plumbing).

The body claims "73 passed" against `tests/test_recurring_briefs.py -q -p no:cacheprovider`. That is a test count fact, not a promotion claim. The 73-vs-actual can be cross-checked: this PR adds 4 assertions (the 4 new lines across `test_daily_step_sits_after_briefing_and_thesis_monitor` and `test_weekly_step_sits_after_brief_producers`); pre-existing assertions on the file would account for the rest. The body does NOT cite a specific pre-PR vs post-PR assertion count (a minor gap — the body could say "72 → 73" or "73 passed, 0 failed" without implying promotion), but a test-pass count is not the doctrine's "validated" shape regardless.

`scripts/check_validated_claims` was NOT run end-to-end here because (a) the PR is workflow YAML + a test, neither of which is the typical surface for unearned claims, and (b) running the validator against the diff would be vacuous — the diff has zero user-facing lines for the validator to flag. The audit lane's posture for vacuous diffs is "skip + name the vacuous-ness," not "pretend to run and report green."

**Verdict:** PASS. Zero promotion language. The only "reviewed" in the diff is a true operational claim about a code-level fallback, and the only "already-provisioned" is a true operational claim about a present GitHub secret name.

## Other compliance notes (informational, not failures)

- **Secret safety.** No secret value is committed. The diff changes only the `${{ secrets.X }}` lookup name (`SUPABASE_SERVICE_ROLE_KEY` → `SUPABASE_SERVICE_KEY`) and removes one line (`SUPABASE_URL: …`). Both are lookup expressions; no literal key material lands in source. The body explicitly states this: "No secret value is copied into source, logged, widened, or exposed."
- **No new GitHub secret.** The body claims "No new GitHub secret is created by this PR" — verifiable: the diff doesn't create a `gh secret set …` step or any new repo-config file. The repair reuses the already-provisioned `SUPABASE_SERVICE_KEY`.
- **No CI manifest change.** The body claims "The new tests remain in the existing directly enrolled suite; no CI manifest or waiver change." The diff confirms: `tests/test_recurring_briefs.py` is one file under an existing enrolled test path; no CI YAML, no manifest, no waiver file touched.
- **No new surface area.** The body claims "no new feed, score, risk engine, ledger, policy authority or retry loop" — verified by diff scope (3 files, all workflow YAML + 1 test). No engine code, no script change, no policy artifact.
- **No collector / market-input manufacturing.** The producer (`engine/recurring_briefs.py`) is byte-identical to base; the only behavioral change is which env var it reads.
- **Sparse-worktree posture.** This PR is on `mockups/`-free + `site/`-free + `verify_shots/`-free sparse. The PR touches none of those, so a sparse checkout can audit it cleanly. No opt-in required.
- **Allowlist-missing checkout fault (informational).** `scripts/check_validated_claims` requires `data/regime/validated_claims_allowlist.json`, which is in the omitted `data/` tree. Same posture as #7431's audit: that is a checkout fault, NOT a wave of new unearned claims. The doctrine-correct disposition is "skip the validator against this diff because (a) the diff has no user-facing lines and (b) the validator's own gate would refuse on missing-allowlist anyway."
- **Ledger effect.** None — this is a wiring fix; no MO-PAID-032 cell advances (the producer is still dormant until `RECURRING_BRIEFS_ENABLE` is provisioned and armed, which this PR does NOT do).
- **No companion evidence packet.** This PR is not a user-facing surface change, so it does not need an `EVIDENCE.yml` / `manifest.json` / `REPORT.md` set under `mockups/evidence/`. The diff is correctly scoped.

## Overall verdict

**PASS.** A surgical half-B runtime-wiring fix with zero user-facing surface area, zero theme exposure, and zero promotion claims. The change reuses an already-provisioned secret name, lets the producer fall through to its reviewed public-project default, and locks both behaviors with four new pytest assertions. The YAML comment correctly explains the two-line shape ("do not inject an absent secret as an empty string" — the actual defect the fix is closing). Test count claim is verifiable against the file. No seat-correction block needed because the PR body is short enough not to drift.

The only nit worth naming is that the body could optionally have printed a "72 → 73 passed" delta for the test count to make it obvious which assertion was new — but that is a documentation nicety, not a compliance defect. The doctrine's vacuous-pass / vacuous-skip disclosure convention applies cleanly here: theme and validated-claims checks are vacuous against this diff by construction, and naming that is the right disposition rather than laundering it as substantive green.
