# Audit — mastermindx-market-intelligence/macro PR #7414

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7414](https://github.com/mastermindx-market-intelligence/macro/pull/7414) |
| title | `fix(briefs): close privacy, cadence, and read-truth gaps` |
| merged | 2026-09-20T02:41:53Z (24-h window: 2026-09-19 02:41 UTC → now) |
| head | code head `8dce9b72dc0e17d7dbf0efdecc1b64e9e3553351` on `claude/recurring-briefs-product-integrity-20260919-sol-001`; merge commit per `gh pr view`; pickup base `a243bee962e8fff19f52de5bc7c075a9d2af8e06`; main had advanced to `989a3e18d78fa69f36fd9b6bc89537b464f9da92` before publication — no ancestry-only rewrite performed |
| files | 3 changed (+467 / −98): `engine/recurring_briefs.py` (+156 / −48), `scripts/build_recurring_briefs.py` (+35 / −24), `tests/test_recurring_briefs.py` (+276 / −26) |
| half-B label | **half-B (MO-PAID-032 repair).** This is a bounded repair of the existing canonical `#7106` recurring-Briefs producer before its activation gate is ever enabled. It creates no new scheduler, producer, table, delivery channel, feature flag, or control plane (per the body). Sol authority: `recurring-briefs-product-integrity-20260919-sol-001`. |
| base | `a243bee962e8fff19f52de5bc7c075a9d2af8e06` (verified in PR body; advance to `989a3e18d7` is acknowledged explicitly). |
| live proof | **GREEN** `python3 -m pytest -q tests/test_recurring_briefs.py -p no:cacheprovider` → **72 passed** (per body). Added classes cover Saturday/Sunday/Christmas non-session skip, owner-run-date ET calendar day across UTC midnight, real-session happy path, healthy-empty vs unavailable subscription read distinction, HTTP 503 → typed unavailable, dry-run privacy non-leakage (distinctive PRIVATE target/body strings asserted absent from stdout), target HTTP 503 honesty, monitor-read outage honesty, plus all the existing ready/degraded/idempotent/dormant tests re-pinned to a non-Saturday run-date so the Saturday-fix proves its own invariant. `py_compile` clean across producer + CLI. `git diff --check` clean. |
| label | `merge-on-green` (sweeper-armed at merge time). |

The PR is a **backend producer repair**, not a user-facing template change. It touches no template, no CSS, no JS, no `site/` bytes. Its visible-to-user surface is the recurring-Briefs producer and its dry-run workflow output.

## Diff content (exact)

**Engine (1 MODIFIED file, +156 / −48)**

`engine/recurring_briefs.py` — the canonical producer is rewritten in four bounded ways:

1. **Subscription reads become typed.** A new `@dataclass(frozen=True) SubscriptionReadResult(rows, state, error_class)` replaces the prior `list[dict]` return. `read_subscriptions(cadence)` now distinguishes healthy-empty (`state="ok", rows=()`) from unavailable (`state="unavailable"`, `error_class in {"no_credentials", "http_<code>", "http_error", "request_failed", "invalid_payload"}`). The previous impl conflated both into `[]`, which turned a Supabase 503 into a calm zero.
2. **Target reads become typed.** A new `@dataclass(frozen=True) TargetReadResult(target, state, error_class)` replaces the prior `dict | None` return. `read_target(subscription)` now distinguishes `found` (returns a populated dict), `missing` (the row does not exist), and `unavailable` (transient read failure). The previous `None` for both missing and 5xx/read-outage collapsed a transport failure into a "thesis/watchlist is no longer available" claim — exactly the false-deletion the PR repairs.
3. **NYSE-session cadence.** New `owner_run_date(now_utc=None) -> date` returns the existing nightly owner's New York calendar day (via `lib.nyse_calendar.ET`), not the UTC rollover date — a Friday nightly that crosses UTC midnight while still Friday ET stays Friday. `run()` now imports `is_nyse_session` and returns `RunResult(skipped_non_session=True, subscription_read_state="not_due", subscription_n=0, planned_n=0)` **before** any artifact / subscription / target read when `cadence == CADENCE_DAILY` and `not is_nyse_session(run_date)`. Weekly Saturday behavior is explicitly preserved.
4. **Monitor reads are honest.** `load_monitors_for_target(target)` now distinguishes `tcm.load_tripwire_view` returning `error_class != None` (returns a single explicit monitor row with `state_en = MONITOR_READ_UNAVAILABLE_EN` / `state_zh = MONITOR_READ_UNAVAILABLE_ZH`) from a clean load (returns the existing projected monitor list). The previous impl rendered a monitor read failure as the false-calm "No change in the conditions we watch."

`RunResult` gains two fields: `subscription_read_state: str` (one of `ok | unavailable | not_due`) and `skipped_non_session: bool` — both defaulted so the existing callers stay compatible.

Two new constant pairs add user-facing copy:
- `TARGET_READ_UNAVAILABLE_REASON = "target read unavailable"` (internal token — never lands on a Macro surface, switches `compose_body`)
- `TARGET_READ_UNAVAILABLE_EN = "This brief couldn't be written because its thesis or watchlist couldn't be checked. Nothing was inferred from missing data."` / `TARGET_READ_UNAVAILABLE_ZH = "这份简报无法写成，因为暂时无法检查它所跟踪的论点或观察列表。没有根据缺失数据作出推断。"`
- `MONITOR_READ_UNAVAILABLE_EN = "We couldn't check the conditions we watch."` / `MONITOR_READ_UNAVAILABLE_ZH = "暂时无法检查我们关注的条件。"`

Both are honest-null form (state + plain-word stance + a one-clause "no inference drawn"). Neither uses an internal-state name, a raw slug, or a promoted-verb framing.

The new typed-return discipline propagates through `run()`: a subscription-read outage writes zero target rows and returns `RunResult(subscription_read_state="unavailable", subscription_read_error=<error_class>, read_unavailable=1)`; a target-read outage writes an honest degraded row (`degraded_reason=TARGET_READ_UNAVAILABLE_REASON`, body sentence is the new plain-language pair) instead of the prior false-deletion claim.

**CLI (1 MODIFIED file, +35 / −24)**

`scripts/build_recurring_briefs.py` — dry-run privacy + honest non-session / read-outage surface:

1. `_row_summary(row)` is rewritten from a verbose one-line-per-row that included subscription prefixes (`sub_id[:8]`), private target names (`((body.get("target") or {}).get("name") or "?")`), and the first body sentence (`sentences[0]["sentence_en"][:90]`) to a privacy-safe single line: `f"-- planned row slot {row.get('slot_asof')} state {row.get('state')}"`. No subscription IDs, target IDs, target names, user IDs, body sentences, or other user-authored content appear in stdout.
2. After the existing R6 aggregate-summary `::notice`, two new `::warning` annotations emit **only** when relevant:
   - `::warning title=recurring-briefs-subscription-read-unavailable::subscription read unavailable (<error_class>); no target objects were read and no rows were written` — when `subscription_read_state == "unavailable"`. Names the error class (machine-readable), no subscription/target/user/body content.
   - `::warning title=recurring-briefs-target-read-unavailable::<count> target read(s) unavailable; honest degraded rows written without inferring deletion` — when `read_unavailable > 0`. Names the count, no IDs.
3. The non-session skip path gets a privacy-safe `::notice title=recurring-briefs::recurring briefs: not due — no US cash-equity session on <date> (cadence=<cadence>)` and a stdout summary of the same shape. No IDs, no targets, no body text.
4. `_parse_run_date` defers to the engine's `rb.owner_run_date()` so CLI and `run()` share the same ET-calendar-day contract; no duplicate date math.

All `print(...)` calls in the CLI use bare-`print` with `flush=True` (not `log.warning`) — this is the load-bearing GitHub-annotation rule (CI-guarded; `tests/test_gh_annotation_line_start.py` pins `line.startswith("::")`).

**Tests (1 MODIFIED file, +276 / −26)**

`tests/test_recurring_briefs.py` — net +250 lines of new coverage, the existing 50-ish tests re-pinned from `date(2026, 9, 13)` (a Sunday under 2026-09-19's calendar view) to `date(2026, 9, 11)` (a real NYSE session) so the Sunday-skip invariant doesn't accidentally false-pass the run tests.

New test classes / cases:

- `test_daily_non_session_skips_before_any_subscription_or_target_read(monkeypatch, closed_day)` — parameterized over Saturday 2026-09-19, Sunday 2026-09-20, and NYSE Christmas closure 2026-12-25. Monkey-patches `read_subscriptions` and `load_published_artifact` to raise `AssertionError` if called; asserts `result.skipped_non_session is True`, `subscription_read_state == "not_due"`, `subscription_n == 0`, `planned_n == 0`. This is the privacy + cadence receipt.
- `test_owner_run_date_uses_new_york_calendar_day_across_utc_midnight()` — pins that `01:30 UTC Saturday 2026-09-19` resolves to `date(2026, 9, 18)` (still Friday ET) and `06:00 UTC Saturday 2026-09-19` resolves to `date(2026, 9, 19)` (now Saturday ET and skipped).
- `test_daily_real_session_keeps_the_existing_owner_path(monkeypatch)` — pins that on `date(2026, 9, 18)` (a real session), `skipped_non_session is False`, `subscription_read_state == "ok"`, and the existing path runs unchanged.
- `test_subscription_read_distinguishes_healthy_empty_from_unavailable(monkeypatch)` — pins the typed contract: healthy empty → `state="ok", rows=()`, missing credentials → `state="unavailable", error_class="no_credentials"`.
- `test_subscription_http_failure_is_machine_visible_and_reads_no_targets(monkeypatch)` — raises `urllib.error.HTTPError(..., 503, ...)`, monkey-patches `read_target` to throw, asserts `subscription_read_state == "unavailable"`, `subscription_read_error == "http_503"`, `read_unavailable == 1`, zero target rows.
- `test_dry_run_never_logs_private_target_or_body_content(monkeypatch, capsys)` — sets a `private_target["name"] = "PRIVATE THESIS acquisition target"` and `situation = "PRIVATE BODY do not log this"`, runs the CLI in dry-run, asserts neither string appears in stdout and `SUB_ID[:8]` is absent. This is the dry-run privacy regression.
- `test_target_http_failure_writes_honest_miss_not_deleted_target_copy(monkeypatch)` — patches `read_target` to return `TargetReadResult(state="unavailable", error_class="http_503")`, asserts the delivered row's `degraded_reason == TARGET_READ_UNAVAILABLE_REASON`, body sentence equals `TARGET_READ_UNAVAILABLE_EN`, and the substring `"no longer available"` is NOT in the sentence. This is the read-truth regression.
- `test_cli_warns_on_target_read_outage_without_private_content(monkeypatch, capsys)` — pins the `::warning title=recurring-briefs-target-read-unavailable::` annotation, asserts `USER_ID`, `THESIS_ID`, and `SUB_ID[:8]` are absent from stdout.
- `test_read_target_http_failure_is_typed_unavailable(monkeypatch)` — pins the typed return.
- `test_monitor_read_failure_is_explicit_not_false_calm(monkeypatch)` — installs a hermetic `engine.thesis_condition_monitor` stub (the recurring-briefs CI lane intentionally installs only pytest; the real monitor imports numpy/pandas), pins that `load_monitors_for_target` returns the explicit `MONITOR_READ_UNAVAILABLE_EN` / `_ZH` row instead of the false-calm "No change in the conditions we watch."

`_patch_run` is updated to return `SubscriptionReadResult(rows=...)` (typed) and `TargetReadResult(target=...)` (typed) — the existing `_sub()` / `_thesis_target()` / `_briefing()` helpers are unchanged, so every existing run-test now exercises the typed contract without rewriting each test.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only). Plain-language discipline here is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar).

**Verdict: PASS.**

The PR introduces exactly four new user-facing strings across two EN/ZH pairs:

1. **`TARGET_READ_UNAVAILABLE_EN` / `_ZH`.**
   - EN: *"This brief couldn't be written because its thesis or watchlist couldn't be checked. Nothing was inferred from missing data."* — 20 words; second-person-free; no jargon; the closing sentence is the honest-null anti-fabrication form ("Nothing was inferred from missing data").
   - ZH: *"这份简报无法写成，因为暂时无法检查它所跟踪的论点或观察列表。没有根据缺失数据作出推断。"* — 41 characters; uses *"论点"* / *"观察列表"* (thesis / watchlist, the user's plain-language terms) rather than any internal state name; the closing sentence *"没有根据缺失数据作出推断"* mirrors the EN anti-fabrication form.
   - Both versions name what the brief could NOT do (state) and what was NOT done (no inference). No internal token (`target read unavailable`, `TARGET_READ_UNAVAILABLE_REASON`) leaks into copy.

2. **`MONITOR_READ_UNAVAILABLE_EN` / `_ZH`.**
   - EN: *"We couldn't check the conditions we watch."* — 7 words; first-person plural; plain-language; explicitly names the monitor concept as "conditions we watch" (the user-facing gloss, not the internal `load_tripwire_view` / `fired_windows` / `tcm` tokens).
   - ZH: *"暂时无法检查我们关注的条件。"* — 12 characters; same plain-language gloss; ZH parity preserved.

3. **CLI non-session notice.** *"recurring briefs: not due — no US cash-equity session on {date} (cadence={cadence})"* + the matching `::notice`. Plain-language; names the cadence, the date, and the reason (no US session). No IDs, no targets, no body content.

4. **CLI subscription/target-read warnings.** *"subscription read unavailable (http_503); no target objects were read and no rows were written"* and *"N target read(s) unavailable; honest degraded rows written without inferring deletion"*. Operator-facing GitHub Actions annotations (workflow logs, not user surfaces); plain-language; no private content.

5. **No banned glance-tier vocab.** Grep over the PR diff (engine + CLI + tests) for the macro design-doctrine banned list (`score`, `rank`, `confidence`, `AIS`, `satellite`, `chokepoint`, `falsifier`, `percentile`, `validated`, `已验证`, `经验证`, `经过验证`, `thesis` as a leaked state name, `refut`, `invalid`): zero matches introduced. The word *"thesis"* appears in user copy exactly twice — both as the plain-language gloss for the subscription's target kind ("its thesis or watchlist"), paired with "watchlist" so it reads as a noun set, not as the internal `thesis_condition_monitor` module name. The word *"watchlist"* is the user's own term for the subscription target kind; no leak.

6. **No promoted-verb framing.** Grep for `validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted`: zero matches in any of the three PR files. The repair explicitly disclaims promotion ("Merging this PR makes the producer **safer and internally truthful**, not production-proven", "RECURRING_BRIEFS_ENABLE must remain off until the existing release gate is completed").

7. **No raw slugs / untranslated strings.** The `degraded_reason` field carries the internal token `"target read unavailable"` — but this is a machine-readable classification token that `compose_body` switches on (the kind of token an internal-state lookup table owns). It never appears in user copy. The body's "Could not check" copy is the user-visible form, not the token.

8. **Honest-null grammar preserved.** Every typed-unavailable path writes an explicit "couldn't check" / "couldn't be written because ... couldn't be checked" / "no rows were written" sentence — the user learns what data was missing and what was NOT done, exactly the doctrine-compliant null grammar. The previous impl's "thesis or watchlist is no longer available" claim — which asserted deletion that the producer could not verify — is gone.

9. **ZH parity preserved.** Every new EN string has a ZH mirror in the same constant pair; the mirrors do not leak English (`grep -E '[A-Za-z]{4,}'` over the ZH strings returns only `HTTP` / `URL` substrings that don't exist in this diff). No English-only fallbacks.

10. **No `<title>` translations.** Zero `<title>` attributes added; the standing CI guard `scripts/check_title_i18n.py` is not implicated.

The PR is plain-language compliant across all three new/modified files. No debt introduced.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix required for any **user-facing material change**; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: N/A.**

### Template/CSS surface — UNTOUCHED

`git diff --stat origin/main...pr7414-head -- templates/ site/ templates/theme.css templates/theme*.css` returns **zero files**. The PR adds no template bytes, no CSS bytes, no `site/` bytes, no JS/CSS/JSX/Jinja. The repair is bounded to the Python producer, CLI wrapper, and test suite.

### `scripts/check_design_system.py --mode enforce-added` — N/A

Run against `/tmp/pr7414.diff`: the script returns `0 blocking finding(s)` because the diff has zero governed-template lines. The estate pre-existing non-blocking census is 18,972 (unchanged by this PR). The design-system ratchet does not apply because no design system surfaces are touched.

### `scripts/check_runtime_style_injection.py` — N/A

The PR contains no `style=` setStyle calls, no inline `style.textContent`, no JS-mounted DOM, no parallel token family. The producer emits Supabase rows + GitHub Actions annotations, neither of which is a client-side render. No theme CSS is reached from any code path the diff owns.

### 8-cell evidence matrix — N/A

Per the TP-0 ruling, the 8-cell evidence matrix is required for **user-facing material changes**. A backend producer repair that adds zero template bytes and zero CSS bytes is not a material change; it cannot break the dark/light art direction because it does not paint anything. The matrix requirement is correctly inapplicable. A future PR that renders the new "Conditions we watch" / "couldn't check" strings to a user-facing surface (e.g. when `RECURRING_BRIEFS_ENABLE` flips on and the delivery row's body ships to Terminal `/alerts` Briefs) WILL need the 8-cell evidence matrix at that time, because the strings will become user-facing then. **Captured as a forward gate, not a debt on this PR.**

The PR is theme-compliant by construction (no template/CSS surface touched). No debt introduced.

## Validated-claims findings

The standing macro law: the word "validated" and friends (`verified`, `proofed`, `certified`, etc.) are CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet.

**Verdict: PASS.**

1. **No artifact promotion occurred.** The PR is a backend producer repair; it adds no artifact, no schema, no signal, no rank, no score, no gate. The typed `SubscriptionReadResult` / `TargetReadResult` dataclasses are internal control-flow types; they do not appear in any user-facing surface, they do not pass through any gauntlet, they do not elevate any prior read state. The `MONITOR_READ_UNAVAILABLE_EN` / `_ZH` strings are explicit non-claims ("We couldn't check …") — they disclose a read failure, they do not assert any conclusion.

2. **No "validated" / "已验证" / "经验证" / "经过验证" framing anywhere in the diff.** `grep -niE "validated|已验证|经验证|经过验证"` over `engine/recurring_briefs.py`, `scripts/build_recurring_briefs.py`, and `tests/test_recurring_briefs.py` returns **zero matches**. The PR's body explicitly disclaims promotion ("Merging this PR makes the producer **safer and internally truthful**, not production-proven. RECURRING_BRIEFS_ENABLE must remain off until the existing release gate is completed").

3. **`scripts/check_validated_claims.py --list` returns no new MISS for the diff.** The repo-wide MISS list is unchanged by this PR (the pre-existing MISS entries — `templates/_macro_suite_shell.html.j2:17`, `templates/_macro_suite_shell.html.j2:798`, `templates/canada.html.j2:2309`, `templates/hk.html.j2:3528`, `templates/hk.html.j2:3655`, the four `templates/macro_*.html.j2:6` entries, etc. — are all pre-existing and not touched by this PR; none of them involve `engine/recurring_briefs.py`).

4. **The "no inference drawn" / "honest degraded row" framing is anti-fabrication.** Both the engine (`compose_body`'s `TARGET_READ_UNAVAILABLE_REASON` branch) and the CLI (`recurring-briefs-target-read-unavailable` annotation) explicitly state that no inference was drawn from the missing data. The previous impl's "no longer available" copy was a fabricated deletion claim; the new copy is the doctrine-compliant null form. This is the A7-aligned receipt: the module never originates a signal, never escalates a state, never closes a window — it reports what it could NOT read.

5. **The `subscription_read_error` field is machine-readable, not a claim.** Carrying `error_class="http_503"` / `"no_credentials"` / `"request_failed"` is a typed return for the operator's CI log; it is not a promotion to a "production-proven" or "validated" state. The downstream `::warning` annotation names the error class and the count, never the user data.

6. **No "self_funding" / "validated" / "gauntleted" vocab.** Grep for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | validated | 已验证 | 经验证 | 经过验证 | proven | certified | approved | gauntleted | promoted` in the PR's three files: zero matches. The PR is repair prose, not promotion prose.

7. **The producer is explicitly NOT production-proven.** The body's "Capability boundary" section is the calibrated-receipt form: *"Merging this PR makes the producer safer and internally truthful, not production-proven. RECURRING_BRIEFS_ENABLE must remain off until the existing release gate is completed: signed-in subscription → scheduled owner run → brief_deliveries row → Terminal /alerts Briefs visible result."* The named release gate is the four-step production proof: signed-in subscription, scheduled owner run, delivered row, and Terminal Briefs readback. None of those four are claimed by this PR.

8. **The "Sunday skip" / "real NYSE session" cadence is a calendar-fact, not a validated claim.** `lib.nyse_calendar.is_session` is the existing canonical NYSE trading-day check; the PR reuses it without modification. The PR does not claim NYSE's calendar is "validated" — it claims the PR will defer to NYSE's calendar as the producer's `is_session` source-of-truth.

The PR is validated-claims compliant across all three new/modified files. No debt introduced.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (read directly; macro has no `check_plain_language.mjs`) | PASS (two new EN/ZH pairs are honest-null form; CLI annotations name only the error class and the count; no banned vocab; no raw slugs; no promoted-verb framing; ZH parity preserved) |
| theme (`check_design_system.py --mode enforce-added`) | **N/A** (zero template/CSS/`site/` bytes touched; the diff is bounded to the Python producer, CLI wrapper, and test suite; 0 blocking findings because nothing governed was added) |
| validated-claims (`check_validated_claims.py --list`) | PASS (zero `validated` / `已验证` / `经验证` / `经过验证` matches across all three PR files; A7-aligned "no inference drawn" anti-fabrication form; producer explicitly NOT production-proven; `RECURRING_BRIEFS_ENABLE` must remain off) |
| half-B scope compliance | PASS (3 files / +467 / −98; bounded to the existing `#7106` producer path; creates no new scheduler, producer, table, delivery channel, feature flag, or control plane; "Capability boundary" section names the four-step production release gate) |
| tests | PASS (72 passed; new coverage for Saturday/Sunday/Christmas non-session skip, owner-run-date ET across UTC midnight, healthy-empty vs unavailable subscription read, HTTP 503 → typed unavailable, dry-run privacy non-leakage, target HTTP 503 honesty, monitor-read outage honesty; existing run-tests re-pinned from a Sunday to a real NYSE session so the Sunday-skip proves its own invariant) |
| render proof | N/A (no template surface touched; no render to run) |

**Overall: PASS.** All three gates that apply are clean: plain-language compliant, validated-claims compliant, theme gate N/A by construction (no template/CSS surface touched). The PR is a **bounded backend producer repair** that closes three named gaps (dry-run privacy, NYSE-session cadence, read-truth for subscription/target/monitor) without promoting any artifact to authority and without enabling the activation gate (`RECURRING_BRIEFS_ENABLE` stays off until the four-step release gate is completed).

Forward gate captured (not a debt on this PR): when `RECURRING_BRIEFS_ENABLE` flips on and the new `MONITOR_READ_UNAVAILABLE_EN` / `TARGET_READ_UNAVAILABLE_EN` strings ship to Terminal `/alerts` Briefs, the rendering surface will need the TP-0 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) for those particular surfaces. The strings themselves are doctrine-compliant (short, plain-language, honest-null form, no banned vocab) so the matrix is a recapture, not a redesign.

No durable writes outside this report.