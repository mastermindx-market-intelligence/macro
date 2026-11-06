# Free acquisition estate acceptance repair

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
This is the next bounded source slice, now integrated into [Press PR 8786](https://github.com/mastermindx-market-intelligence/macro/pull/8786).
It uses the existing generator and shared navigation; no new content, styling,
publisher, source store or acquisition flow is introduced.

## Scope and current source

- Fresh main base: `773d6cc2f18fdbce5441e484abc16eb30d8ba3db`.
- Approved SSD helper created the isolated branch from a freshly fetched main.
- Branch: `claude/ssd-mmx-public-estate-20261011-eb397dd43e7ed9f3`.
- Exactly 48 existing non-blog HTML pages receive the accepted Glossary,
  Morning Edition and Help navigation cards: 144 added lines, no removals.
- The initial integration workspace had 50 drifted pages. Fresh main already
  includes complete new compounding and dollar-cost-averaging calculator outputs,
  including their navigation additions. Those two files and their upgrades are
  preserved; the old patch was rejected by `git apply --check`, never forced.
- Targeted ownership checks found no overlapping local modifications or current
  relevant carrier. The global open-PR census was stopped; its incomplete results
  are not presented as universal writer absence.

## Validation and dependency

The original combined integration workspace passed:

- `python3 -m scripts.build_free_content --check`: 68 files byte-identical,
  no orphans; the builder exempts its three hand-authored pages.
- `python3 -m pytest tests/test_free_content.py -q`: 120 passed.
- `git diff --check -- site`: clean.

After moving to fresh main and applying only the remaining 48 files, the
standalone builder check reports exactly seven blog differences. Those are the
existing generated-blog repairs in PR 8786. This follow-up does not duplicate
those files. The fresh-base test run is **119 passed, 1 failed**: the sole
failure is the anti-vacuity orphan-walk sentinel refusing to run over those
seven blog differences. It must stay red until the dependency lands; no test
is deselected or weakened. Both source slices are now integrated on the original PR carrier after merging
main `e5c724d204916a6152c89a52a644537a57a09ab4`. The integrated builder check
passes: **69 files byte-identical, no orphans, three hand-authored exemptions**.
The count increased with accepted main content; no sentinel was weakened.
The integrated `python3 -m pytest tests/test_free_content.py -q` run passed all
**120 tests** (one inherited temporary-directory cleanup warning).
Publication remains disabled.

## Installed origin observation

A read-only SSH check using the existing deploy key reached the documented
origin `146.190.142.17`. Its Macro source was
`773d6cc2f18fdbce5441e484abc16eb30d8ba3db`. `systemctl is-active caddy`
reported active, `/opt/macro/config/press.yml` reported `cutover: false`, and
`/etc/caddy/Caddyfile` contains commented Press virtual hosts inside the marked
cutover block. The actual served-tree front pages already exist:

- `/opt/macro/press_news.served/index.html`: 3,194 bytes.
- `/opt/macro/press_research.served/index.html`: 2,801 bytes.

This verifies installed files and the disabled configuration on disk; it does
not qualify a story, prove every active runtime route, activate either domain,
or prove a customer signup/follow. No runtime settings were changed.

The isolated refresh is retained at `776c532e469c8bdd95df293bd4f45dcb77ea86c0`.
It was cherry-picked as `4ee8bf7bc55c` into the original PR carrier; no second PR
or writer was created. The original 50 local diffs were restored only after an
exact byte comparison with the saved patch and preservation of the committed
48-file slice; fresh main supplies the two already-upgraded calculators.

The existing Agent OS workstream and primary checkpoint are carried by PR 8786.
The story, rights, editorial, mixed-desk and domain-cutover gates remain as
recorded there. This file is supporting evidence, not a new authority record.
