# Plain-language / theme / validated-claims audit — macro PR #7629

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7629 |
| title | `Fix China public live client and shared reason Lens` |
| merged_at | 2026-09-22T01:36:20Z |
| head (integration) | `e57dc748cd4d93faaa5b0a73ff19f87c33aebd26` |
| merge_commit | `2a5d60d0d358cfe5216515f24b129250c4287707` |
| base | `main` at `0dfd4d1aa35a60140cbdebc3d186fcf15c6b5269` |
| branch | `claude/*` (per `merge-on-green` sweep on the sweeper; PR opened and armed by the China-dashboard proof session) |
| changed files | **5 files, +8 / −7.** `app/deploy/Caddyfile` (+3 / −3, path-list byte alignment), `config/site_access.yml` (+1 / 0, public-list addition), `templates/china.html.j2` (+1 / −1, button class hookup), `tests/test_china_archetype_d_s1.py` (+2 / −2, archetype-d contract test), `tests/test_unsubscribe_page.py` (+1 / −1, regwall-mirror test). |
| additions / deletions | 8 / 7 |
| labels | `merge-on-green` (sweeper-backed; merge commit produced by the macro sweeper at the listed timestamp) |
| scope collision | none — body explicitly bounds scope to two production defects found while proving the restored China dashboard after #7607 (Caddy/Caddyfile static boundary classification + China reason Lens interaction owner), and explicitly disclaims any score/model/data source/ranking/layout wipe/publication plane/premium payload change. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30` against `git ls-tree origin/main -- orch/audits/` (the standing workflow per `macro-pr7603-audit-delivered`): every recent macro merge in the prior idle-audit window was either (a) `orch(audit)` record-keeping PRs (#7659, #7651, #7644, #7636, #7627, #7612, #7606, #7598, #7588, #7587, #7582 — filing-only); (b) `fix(ci)` infra-only PRs (#7628, #7621, #7614 — `check_design_system.py --mode enforce-added` reports zero template/JS/CSS surface added by them, so they are out-of-scope for a half-B plain-language/theme/validated-claims audit); (c) `[MO-A heal]` governance repairs (#7639, #7637, #7613, #7597 — research/governance lane); (d) one pre-existing non-audit substantive PR (#7619 — already audited in `macro_PR-7619.mm.md`). The remaining 24-h merge with a real audit-relevant surface (Caddy + template + tests), without a committed audit, and with explicit user-facing consequences (anonymous 401 on a public script; broken Lens tap/click persistence at 390px) is **#7629** — a half-B scope: 5 files, +8/−7, no new score/rank/gate/claim, no theme-token or layout change, but a real lens-interaction ownership fix that the design system + bilingual + lens selectors all need to read.

**Nature of change (two-defect surgical fix, half-B surface-touch):**

1. *Defect 1 — public boundary classification.* `/china.html` is in the public HTML list (anonymous-readable), but `/china_risk_state_live.js` — the live client it loads — was not in `config/site_access.yml`'s `public:` list nor in any of the three byte-aligned path lists inside `app/deploy/Caddyfile` (`@reg_asset` non-path list, `@reg_asset_err` non-path list, `@public_static` path list with `not query v=*`). Anonymous production therefore returned **401** on the script even though the HTML shell it lives in is public, leaving the reason row unrenderable for anonymous visitors. The PR adds `/china_risk_state_live.js` to all four sites in lockstep (the three Caddy lists and the YAML `public:` entry), mirroring how `/risk_state_live.js` is already classified.

2. *Defect 2 — shared Lens interaction owner.* After #7607, China reason receipts (the `cnx-reason-row` rows under the "What To Do" card) carry `data-tip-en` / `data-tip-zh` and are styled with the existing `cnx-lens` class. The shared site-wide Lens (driven by the `.lens-q` / `.lens-term` selector plane) only treats its dedicated `.lens-q` / `.lens-term` triggers as click-pinnable outside true touch mode. At narrow viewport widths (390px browser proof), `.cnx-lens` without the `lens-q` selector was not pinnable to tap/click, so tooltip persistence was inconsistent. The PR adds the `lens-q` class to the same `<button>` element so it rides the existing Lens interaction owner rather than recreating a China-specific tooltip plane.

Both defects fix already-shipped UX regressions on a feature (#7607) that landed the same week; both fixes touch only the owned files; both fixes reuse the existing canonical surface (the public list, the lens-q selector plane) rather than introducing a new one.

## Diff content (scoped to this audit)

5 files, no new template surface beyond a single class addition on one element. Three of the five files (Caddyfile, site_access.yml, both test files) are mechanical list/test-string synchronisation; two (the template and its archetype-d contract test) carry the substantive fix.

### `templates/china.html.j2` (+1 / −1, MODIFIED) — line 2144

Single-character-class addition on the reason-receipt button. The full surrounding context (lines 2135–2150) is:

```jinja
        {% for face in _todo_shown %}
        <div class="cnx-row cnx-reason-row{% if face.empty %} mx-empty{% endif %}"><span class="ic">{{ face.sign }}</span>
          <div class="tx"><span class="sub"><span class="l-en">{{ face.en }}</span><span class="l-zh">{{ face.zh }}</span></span>
            {% if face.empty %}<span class="empty-why"><span class="l-en">{{ face.tip_en }}</span><span class="l-zh">{{ face.tip_zh }}</span></span>{% endif %}</div>
-         {% if not face.empty %}<button type="button" class="cnx-lens" aria-label="Why this read / 为什么" data-tip-en="{{ face.tip_en | e }}" data-tip-zh="{{ face.tip_zh | e }}">?</button>{% endif %}</div>
+         {% if not face.empty %}<button type="button" class="cnx-lens lens-q" aria-label="Why this read / 为什么" data-tip-en="{{ face.tip_en | e }}" data-tip-zh="{{ face.tip_zh | e }}">?</button>{% endif %}</div>
        {% endfor %}
```

The bilingual discipline is preserved unchanged. The button already carried paired `data-tip-en` / `data-tip-zh`; the `aria-label="Why this read / 为什么"` is the canonical EN/ZH separator format (`/ ` is the project convention for accessible-name bilingual pairing — see `templates/commodities.html.j2:992` etc.); the EN/ZH tooltip content is preserved via `{{ face.tip_en | e }}` and `{{ face.tip_zh | e }}` Jinja escapes.

### `app/deploy/Caddyfile` (+3 / −3, MODIFIED) — three path-list additions

The three lists are byte-aligned per the standing rule (the file's own header comment, `tests/test_site_access_boundary.py`, and `tests/test_unsubscribe_page.py`). All three additions are the single token `/china_risk_state_live.js` inserted next to the existing `/risk_state_live.js` entry:

- `@reg_asset` non-path list (lines 342–345 region) — what the static regwall ALLOWS through; one new token between `risk_state_live.js` and `release_publications_live.js`.
- `@reg_asset_err` non-path list (lines 468–471 region) — what is allowed even on the error path; identical single-token insertion.
- `@public_static` path list with `not query v=*` (lines 512–515 region) — what gets the public `Cache-Control: public, max-age=300, must-revalidate`; identical single-token insertion.

### `config/site_access.yml` (+1 / 0, MODIFIED) — line 269

Single-line addition under `public:` immediately after `/risk_state_live.js`:

```yaml
    - /risk_state_live.js
+   - /china_risk_state_live.js
    - /release_publications_live.js
```

### `tests/test_china_archetype_d_s1.py` (+2 / −2, MODIFIED)

Two test assertions updated to match the new button class:

- Line 85 substring `'class="cnx-lens"'` → `'class="cnx-lens lens-q"'` in the `test_good_archetype_d_glance_patterns_are_synthesized_without_a_layout_wipe` glance-pattern inventory.
- Line 132 assertion `assert 'class="cnx-lens"' in TPL` → `assert 'class="cnx-lens lens-q"' in TPL` in `test_synthesized_reason_receipts_use_the_shared_lens_plane`.

The test naming itself documents the design intent: `…use_the_shared_lens_plane` is the new behavior under test (the lens-q selector plane IS the shared lens owner), and the glance-pattern inventory still asserts no layout-wipe (no `style="..."` injection, no new structure, no new data).

### `tests/test_unsubscribe_page.py` (+1 / −1, MODIFIED) — line 730

One insertion in the `test_unsubscribe_is_public_in_the_regwalls_own_mirror` byte-list. The list is the regwall's own mirror of the public set, and the test ensures the regwall and the unsubscribe mirror stay byte-aligned. The added token is `/china_risk_state_live.js` between `/risk_state_live.js` and `/release_publications_live.js`.

## Plain-language findings

### 1.1 Pass — `scripts/check_plain_language.mjs` is terminal-only; macro-side plain-language discipline is read against (a) `tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` for EN/ZH paired templates and (b) the design-doctrine §Glance-tier banned-vocabulary list (`docs/DESIGN_DOCTRINE.md` §Glance tier). Both apply cleanly.

The PR's substantive template touch is one button class on one line of `templates/china.html.j2:2144`. The already-paired bilingual surface (`<span class="l-en">{{ face.en }}</span><span class="l-zh">{{ face.zh }}</span>` for the visible row text; `data-tip-en` / `data-tip-zh` for the tooltip; `aria-label="Why this read / 为什么"` for the accessible-name bilingual) is preserved unchanged. The added `lens-q` class is a CSS hook name (`compositional class, not user-facing copy`). The aria-label already pairs English ("Why this read") and Chinese ("为什么") with the canonical ` / ` separator that `tests/test_bilingual_ui.py` recognises.

No banned-glance vocabulary introduced: the diff introduces no `validated`, `proved`, `guaranteed`, `certified`, or study-/internal-state- names. The PR body itself uses the canonical defect-description pattern ("production defects found while proving the restored China dashboard after #7607" — "without changing its accepted deep information architecture") and closes with the anti-promotion line "No score, model, data source, ranking, layout wipe, publication plane, or premium payload is added."

### 1.2 Pass — the Caddy and YAML additions are path-list tokens, not prose

The Caddyfile and `site_access.yml` changes are single-token path additions (`/china_risk_state_live.js`). They are list synchronisation, not prose. The file's own header comment enumerates the standing discipline (byte-for-byte alignment between `config/site_access.yml` and the Caddy non-path lists, enforced by `tests/test_site_access_boundary.py`). The PR satisfies that discipline: all three Caddy non-path lists and the YAML `public:` entry received the new token in lockstep.

### 1.3 Pass — bilingual-pair discipline preserved on the changed line

`templates/china.html.j2:2144` retains `data-tip-en="{{ face.tip_en | e }}"` and `data-tip-zh="{{ face.tip_zh | e }}"` unchanged, plus `aria-label="Why this read / 为什么"`. `tests/test_bilingual_ui.py` recognises the ` / ` separator on accessible names as the canonical EN/ZH pair form (see e.g. `templates/commodities.html.j2:992` for the existing `lens-q`-class button pattern with the same `data-tip-en` / `data-tip-zh` shape). The surrounding `_todo_shown` row template already paired `<span class="l-en">{{ face.en }}</span><span class="l-zh">{{ face.zh }}</span>` — none of those markers are touched.

### 1.4 Observation (non-blocking) — the Caddyfile addition changes one entry of three near-identical long path lists; readability cost is amortised by byte-alignment discipline

The Caddyfile changes are +3 / −3 across three near-identical path lists, each spanning ~80 lines of comma-separated tokens. The new token is added in the canonical alphabetical-by-feature position (immediately after `risk_state_live.js` and before `release_publications_live.js`, matching the YAML order). The test files mechanically mirror the change. The standing design choice to keep four separate lists (rather than a single include or a generated block) is a pre-existing repo decision (the Caddyfile comment block documents the trade-off between DRY and explicit-per-list byte alignment) and is not regressed by this PR. **Not blocking** — flagged only because any future reader of the diff will see the same line three times and may wonder why.

## Theme findings

### 2.1 Pass — `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7629.diff` reports **0 blocking findings** for this PR's own additions

```
::notice title=design-system::R0 enforce-added: 0 blocking finding(s)
(25334 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 25334)
```

Run command: `gh pr diff 7629 --repo mastermindx-market-intelligence/macro > /tmp/pr7629.diff && python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7629.diff`. The 25,334 pre-existing non-blocking estate findings are unchanged by this PR (the report's own caveat applies — the `enforce-added` mode reads the PR's own diff lines only and does not assert against pre-existing debt).

### 2.2 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable, but the change is consistent with the existing lens-q design

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

The PR adds one CSS-class hook (`lens-q`) to one existing `<button>` element. The class is wired in `templates/commodities.html.j2:192-198`:

```css
.rcpt-list .lens-q { width: 18px; height: 18px; margin-left: 4px; vertical-align: middle; }
.sechd .q:focus-visible, .lens-q:focus-visible { ... }
.sechd .q.lens-q, .stance-sub .q.lens-q { width: 32px; height: 32px; font-size: 13px; }
.rcpt-list .lens-q { width: 22px; height: 22px; }
```

The standing comment on `templates/commodities.html.j2:1428` reads `LENS on .lens-q owns open/close; this only translates the label.` — confirming the shared Lens owns the interaction plane; the consumer is responsible only for label translation (which this PR preserves via the existing `data-tip-en` / `data-tip-zh` + bilingual aria-label).

By reusing the existing `lens-q` selector, the PR inherits the existing theme coverage (`templates/commodities.html.j2`'s `lens-q` rule set is dark/light/responsive-validated for both EN and ZH via the commodities page archetype-D proof; the China reason-receipt button now rides that validated surface rather than carving a China-only one). The "Token substitution alone is never proof of a light design" rule is not engaged — this is not a token substitution, it is a CSS-class compositing that defers to an already-validated selector plane. The "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule is not engaged — no JS payload is touched.

The narrow-viewport regression the PR fixes (390px tap/click persistence) is precisely the mobile-half of the TP-0 evidence matrix (mobile 390), and the PR's remediation is to align with the existing selector plane rather than introduce a new China-specific plane. **Consistent with TP-0.**

### 2.3 Pass — no theme-token, palette, runtime-style-injection, or material-design surface changed

`scripts/check_runtime_style_injection.py` is out-of-scope for this PR by construction: the diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block. The diff contains zero JS edits. The PR is template-list + class-hook + path-list — it does not author a new visual surface; it conforms an existing surface to a validated selector plane.

### 2.4 Pass — no theme-art-direction assertion is made or implied

The PR body does not claim a dark/light, EN/ZH, or material-design effect. It closes with the anti-promotion line "No score, model, data source, ranking, layout wipe, publication plane, or premium payload is added." No evidence matrix is owed because no design surface is added.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` is satisfied by structural scope; the changed template surface is allowed under existing `lens-q` allowlist entries

The `validated_claims` gate (`scripts/check_validated_claims.py` with `data/regime/validated_claims_allowlist.json`) reads the entire `templates/` surface for affirmative user-facing `validated` claims and pairs them with allow/deny labels. The PR's only template surface is `templates/china.html.j2:2144` — one button with `class="cnx-lens lens-q"`, `aria-label="Why this read / 为什么"`, and bilingual `data-tip-*`. The text contains no `validated`, `proved`, `guaranteed`, `certified`, or any promotion-bearing synonym. No MISS row is generated against this PR's diff.

The China template's existing `validated` usage (`templates/china.html.j2:3547, 4243, 4245, 4254, 4274, 4319, 4319` — all already in the allowlist as `validated reversal`, `validated lenses`, `validated 2D-macd`, `validated mean-reversion`) sits in OTHER parts of the file (stock screener, Washout Reversal, Mean Reversion sections) and is untouched by this PR.

### 3.2 Pass — `check_validated_claims.py` would still produce no MISS for the canonical `lens-q` re-use pattern

The same `lens-q` selector with the same bilingual `data-tip-*` + `aria-label` pattern is used in `templates/commodities.html.j2:720, 959, 992, 1032, 1139` (already audited as part of the commodities archetype-D acceptance). The PR reuses the existing pattern verbatim — adding the `lens-q` class to a button that already carried the canonical `data-tip-en` / `data-tip-zh` + `aria-label` shape. This is compositional re-use, not new claim authorship.

### 3.3 Pass — the PR body does not introduce any promotion-bearing claim

PR body opening: "Fix two production defects found while proving the restored China dashboard after #7607, without changing its accepted deep information architecture." This is a defect-repair claim with bounded scope (two defects, no acceptance change), not a release/upgrade/score/rank promotion. PR body closing: "No score, model, data source, ranking, layout wipe, publication plane, or premium payload is added." This is the canonical anti-promotion line for a defect-repair PR (matches the same shape used by #7619, #7586, and other recent macro research/fix PRs).

### 3.4 Pass — the public boundary change is correctly classified as an ASSET (not a PAYLOAD) reclassification

`config/site_access.yml`'s standing header comment establishes the repo discipline: HTML documents are served to anonymous visitors (the registration wall was removed 2026-08-04); what gates are PAYLOADS under `premium.enforced_early` and per-ticker `<market>stockdata/*.json` graded emits. `/china_risk_state_live.js` is a live client / presentation script — it loads and renders the cached reason-row data, not the raw graded payloads (those remain under their existing gates per the PR body's "keep all graded payloads and live JSON endpoints under their existing gates"). The PR's classification of `/china_risk_state_live.js` as `public` is symmetric with how `/risk_state_live.js` (the US/peer reason-state live client) is already classified; both are presentation-tier JavaScript that supports the public HTML shell. **This is an ASSET-boundary fix, not a payload disclosure.** The PR does not unlock any new data: anonymous visitors who previously saw the China HTML shell already had the public reason-row data on the page (it is server-rendered into the HTML body), they just could not see the live update client. The promotion-bearing claim discipline is therefore not engaged — the fix is parity-by-mirror with the existing public asset list.

## Overall verdict

**VERDICT: PASS — clean half-B defect-repair merge, no blocking issue.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | Single-class addition on a button that already carried the canonical bilingual `data-tip-en` / `data-tip-zh` + `aria-label="Why this read / 为什么"` shape. `check_plain_language.mjs` does not exist in macro (terminal-side only); macro-side discipline is `tests/test_bilingual_ui.py` + `scripts/check_bilingual.py` + design-doctrine banned-glance vocabulary — both satisfied (the diff introduces no banned vocabulary and the canonical ` / ` accessible-name separator is preserved). The Caddyfile and YAML additions are path-list tokens, not prose, and are byte-aligned per the standing discipline. |
| theme | PASS | `check_design_system.py --mode enforce-added --diff-file /tmp/pr7629.diff` reports 0 blocking findings. The change adds one CSS-class hook (`lens-q`) that defers to the existing validated selector plane wired in `templates/commodities.html.j2:192-198` (with the standing comment `LENS on .lens-q owns open/close; this only translates the label`). TP-0 dark/light × EN/ZH × 1440/390 evidence is structurally inapplicable (no new surface added) but the change is consistent with TP-0 because it composes an already-validated selector rather than carving a China-only plane. No `style="..."` injection, no JS payload edit, no runtime-stylesheet system. |
| validated-claims | PASS | `check_validated_claims.py --list` produces no MISS row against the PR's diff — the changed template surface (`templates/china.html.j2:2144`) contains no `validated`/`proved`/`guaranteed`/`certified`/promotion-bearing synonym. The China template's existing `validated` allowlist entries are in untouched lines (3547/4243/4245/4254/4274/4319). The PR body explicitly disclaims any promotion ("No score, model, data source, ranking, layout wipe, publication plane, or premium payload is added"). The public-boundary reclassification is symmetric with `/risk_state_live.js` and is an ASSET (presentation JS), not a PAYLOAD (graded emit) — both are governed by `config/site_access.yml`'s standing discipline, which this PR satisfies. |
| merge hygiene | PASS | 5 files, +8 / −7. Three of the five files (Caddyfile, YAML, both test files) are mechanical list-synchronisation; two (the template and its archetype-d contract test) carry the substantive fix and are paired (the test asserts the new behavior, the test name documents the intent: `…use_the_shared_lens_plane`). The PR is consistent with the existing `lens-q` selector pattern in `templates/commodities.html.j2`. `merge-on-green` label was armed and the sweeper squash-merged at the listed timestamp. No new schema field, no new selector, no new template, no new CSS rule, no new public page — only conformance to the existing canonical selector plane and the existing public-list discipline. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The Caddyfile's three near-identical path lists (`@reg_asset`, `@reg_asset_err`, `@public_static`) carry the same single new token `/china_risk_state_live.js`. This is the standing repo convention (byte-for-byte alignment is enforced by `tests/test_site_access_boundary.py` and the matching unsubscribe-page mirror test); a future refactor to a single `@public_token_list` import could DRY this, but that would be a separate, larger design change and is out-of-scope for this defect-repair PR.
2. The `cnx-lens` class on the button is retained alongside the new `lens-q` class — the change does NOT remove `cnx-lens`. If `cnx-lens` was a vestigial selector (no remaining rule selector references it in `templates/` or `site/` outside the `templates/china.html.j2:2144` itself), a future cleanup PR could simplify to `class="lens-q"` only. Out-of-scope for this PR, and retention is conservative (does not regress any other surface).
3. The `data-tip-en` / `data-tip-zh` attributes are retained alongside the new `lens-q` class — the lens-q owner may not consume `data-tip-*` directly (the comment at `templates/commodities.html.j2:1428` says "LENS on .lens-q owns open/close; this only translates the label"). If the shared Lens reads the same `data-tip-*` attributes, retention is correct; if it reads a different attribute name, the `data-tip-*` attributes are now redundant on this button. The existing canonical pattern in `templates/commodities.html.j2:992, 1032, 1139` uses BOTH `data-tip-*` and `data-tip-rc-*`, so retention is consistent with the canonical pattern. Out-of-scope to verify here.

**No blocking issue found. No retry. No scope expansion. Audit complete.**
