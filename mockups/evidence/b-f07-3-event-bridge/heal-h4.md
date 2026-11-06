# Heal h4_7134 — 2026-09-19

Code head: `32408e5e14511d2426cc8e9c83bb400598f69e92`. Source/test repair: `26f63cae402cc4f440e43ba8ba11d3e8b6ad48fd`.
Status: functional fixes complete; CI scope amendment required. PR stays Draft.

## Review of preserved commit 2509328e

- `.github/ci/legacy-jobs.yml`: reverted its `engine/**` wildcard and added only the six exact paths from failed job 105822562046, under the mandated dated comment. All edits are inside conviction-profile's paths list. Other historical PR workflow hunks remain preserved.
- `engine/valuation_assumptions.py`: kept removal of the incorrect “No IO” claim and the production-shaped `controls_blob(v1)` interface. Replaced the hard-coded Chronicle path with the owner's `EVENTS_REL`; also reads the SEC compiler's canonical `_data_root()/event_versions.parquet` through `_load_existing_events`. Removed caller-injected path/class arguments. Selects the latest issuer event with a non-null bridge and skips policy, earnings, prospectus, and deferred SEC rows.
- `engine/valuation_event_bridge.py`: reverted all 16 preserved additions. Seven invented Chronicle/tender keys violated exact closure; the two offering-statement entries duplicated existing typed-null keys. Existing plain bilingual labels, policy separation, and Form 25 null behavior remain.
- `tests/test_valuation_event_bridge.py`: kept the intent of a production-shaped call, replaced the hard-coded path fixture with owner-path fixtures, removed invented expected keys, and added validated Parquet and latest-non-null regressions. Every vocabulary member is rendered and checked for visible machine slugs, including null members.

## Functional evidence

Interpreter command:
`PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 -c "import sys,pytest;print(sys.executable,sys.version.split()[0],pytest.__version__)"`

Output: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 3.12.10 9.1.1`.

RED used in-memory replay of the two engine modules read by `git show <sha>:<file>`;
no other checkout or history rewrite was used. The new tests and unchanged canonical
spine dependencies run in this worktree. `controls_blob(v1)` has no test-only kwarg.

- At `6e391cf1`: **3 failed, 1 passed, 22 deselected**. The JSONL tender-offer fixture, validated capital fixture, and latest-classified selection each fail because the previous producer returns null. The vocabulary closure test passes at that older head.
- At `2509328e`: **4 failed, 22 deselected**. The same producer regressions fail, and exact vocabulary equality additionally rejects the invented keys.
- GREEN: `PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 -m pytest tests/test_valuation_event_bridge.py -q -p no:cacheprovider --basetemp .heal-7134/pytest-final-code` → **26 passed in 3.47s**.
- Regenerated-host verification: same targeted suite with `--basetemp .heal-7134/pytest-evidence` → **26 passed in 4.14s**. The final base merge changed only two research-vault data files; engine, template, test, and workflow bytes remain identical to the tested code commit.

The JSONL fixture deliberately makes 424B5 newer than the mature Tender Offers row;
the rendered bilingual line still names Tender Offers. A newer row for another issuer
is ignored. The real production default also reads the committed Parquet ledger,
whose event schema and immutable IDs are validated by the existing compiler reader.

Real issuer command (reported statements and committed event spine):
```sh
PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:$PATH" python3 -c 'from engine.stock_fundamentals import _load_statements; from engine import valuation_scenario as vs, valuation_assumptions as va; from tests.test_valuation_event_bridge import _render; import re; v1=vs.compute(_load_statements()["NSA"],ticker="NSA"); c=va.controls_blob(v1); print("NSA:"+c["latest_event_bridge"]["event_class"]); print("FY",v1["fy"],"reported SEC statements"); print(" ".join(re.sub("<[^>]+>","",re.search(r"<p[^>]*id=\"va-event-bridge\"[^>]*>(.*?)</p>",_render(c),re.S)[1]).split()))'
```

```text
NSA:post_effective_amendment
FY 2025 reported SEC statements
Latest filing on file (Post-Effective Amendment) usually presses margin.最新备案（生效后修正）通常压缩利润率。
```

This proves the producer/template path against real issuer data. It does not claim a
published NSA page: the existing builder's V1 cohort remains pinned to AAPL, outside
the permitted call-site-only edit. AAPL currently has no eligible event and stays null.

## Contract-delta and authority gap

Failed run **35415253628**, job **105822562046**, names the six branch-caused gaps:
`contracts/capital_structure_document_term_observation.schema.json`,
`contracts/capital_structure_projection.schema.json`,
`engine/capital_structure/__init__.py`, `document_terms.py`, `projection.py`, and
`source_identity.py`. Those six declarations are now fixed exactly as ruled.

The real readers additionally widen dependency closure. The canonical head census
(`scripts.check_contract_delta._head_findings()`) reports the exact remaining paths
in `contract-head.json`, across eight jobs. These are findings, not a passing
contract-delta result. No main-equivalent failure has been established.

The exact local `python3 scripts/check_contract_delta.py --base origin/main` was
not invoked: its `materialize_base_tree()` creates another worktree and runs Git
inside it, violating the user's hard work-only-in-cwd rule. Only its canonical
read-only head census ran here. The final-head hosted check is the differential
acceptance authority. Scope widening has been requested; no unauthorized CI-list
edits or disguised imports were made.

## Visual evidence

24 crops: tender-offer/restructuring/null × dark/light × EN/ZH × desktop/mobile.
All hosts were regenerated after the last merge; one sequential Chromium capture
recorded zero page errors and zero event-line overflows. Event line: 11px; FY
footnote: 11.5px. `capture-metrics.json` carries the visible sentences and geometry.
The static host wrapper omits the unrelated full-site theme JavaScript while
retaining canonical theme.css and the live valuation template's own behavior.

## Merge preservation

Merge 1: `58956d2e90f0ae8f10e2843f36afa5c7359fff46`, base `cafc5c62accb`.
Before and after numstats are identical for all 20 files; no SUPERSEDED path.

Before: `git diff --stat $(git merge-base HEAD origin/main) HEAD`:
```text
 .github/ci/legacy-jobs.yml                         |   23 +
 engine/valuation_assumptions.py                    |   65 +-
 engine/valuation_event_bridge.py                   |  334 +
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   36 +
 .../hosts/valuation-event-bridge-null.html         | 8513 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 8513 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 8513 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   23 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   12 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   36 +
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 10259 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 11782 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 10382 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 12147 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 12800 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 13742 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 12544 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 16229 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  533 ++
 20 files changed, 26633 insertions(+), 3 deletions(-)
```
After: `git diff --stat origin/main...HEAD`:
```text
 .github/ci/legacy-jobs.yml                         |   23 +
 engine/valuation_assumptions.py                    |   65 +-
 engine/valuation_event_bridge.py                   |  334 +
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   36 +
 .../hosts/valuation-event-bridge-null.html         | 8513 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 8513 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 8513 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   23 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   12 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   36 +
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 10259 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 11782 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 10382 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 12147 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 12800 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 13742 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 12544 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 16229 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  533 ++
 20 files changed, 26633 insertions(+), 3 deletions(-)
```

Merge 2: `32408e5e14511d2426cc8e9c83bb400598f69e92`, base `5332d876e75837c158c6f42a2862734451bb7158`.
Before and after numstats are identical for all 20 files; no SUPERSEDED path.

Before:
```text
 .github/ci/legacy-jobs.yml                         |   29 +
 engine/valuation_assumptions.py                    |   74 +-
 engine/valuation_event_bridge.py                   |  318 +
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   36 +
 .../hosts/valuation-event-bridge-null.html         | 8513 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 8513 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 8513 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   23 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   12 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   36 +
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 10259 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 11782 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 10382 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 12147 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 12800 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 13742 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 12544 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 16229 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  583 ++
 20 files changed, 26682 insertions(+), 3 deletions(-)
```
After:
```text
 .github/ci/legacy-jobs.yml                         |   29 +
 engine/valuation_assumptions.py                    |   74 +-
 engine/valuation_event_bridge.py                   |  318 +
 mockups/evidence/b-f07-3-event-bridge/EVIDENCE.yml |   36 +
 .../hosts/valuation-event-bridge-null.html         | 8513 ++++++++++++++++++++
 .../valuation-event-bridge-restructuring.html      | 8513 ++++++++++++++++++++
 .../hosts/valuation-event-bridge-tender-offer.html | 8513 ++++++++++++++++++++
 .../evidence/b-f07-3-event-bridge/manifest.json    |   23 +
 mockups/evidence/b-f07-3-event-bridge/smells.json  |   12 +
 mockups/evidence/b-f07-3-event-bridge/smells.md    |   36 +
 ...n-event-bridge-tender-offer_desktop_dark_en.png |  Bin 0 -> 10259 bytes
 ...n-event-bridge-tender-offer_desktop_dark_zh.png |  Bin 0 -> 11782 bytes
 ...-event-bridge-tender-offer_desktop_light_en.png |  Bin 0 -> 10382 bytes
 ...-event-bridge-tender-offer_desktop_light_zh.png |  Bin 0 -> 12147 bytes
 ...on-event-bridge-tender-offer_mobile_dark_en.png |  Bin 0 -> 12800 bytes
 ...on-event-bridge-tender-offer_mobile_dark_zh.png |  Bin 0 -> 13742 bytes
 ...n-event-bridge-tender-offer_mobile_light_en.png |  Bin 0 -> 12544 bytes
 ...n-event-bridge-tender-offer_mobile_light_zh.png |  Bin 0 -> 16229 bytes
 templates/_valuation_assumptions.html.j2           |   35 +-
 tests/test_valuation_event_bridge.py               |  583 ++
 20 files changed, 26682 insertions(+), 3 deletions(-)
```

## Evidence-head law

(a) `EVIDENCE.yml` resolved_sha_or_none equals CODE_HEAD `32408e5e14511d2426cc8e9c83bb400598f69e92`.
(b) The subsequent final commit contains only files under this evidence directory.
(c) `git diff --quiet 32408e5e14511d2426cc8e9c83bb400598f69e92 HEAD -- templates/` exits 0.
The final pushed SHA and the measured check states belong in the PR body, not in a
self-referential receipt.

## Deviations

The hard workspace law supersedes the local differential script's temporary-worktree
behavior. Existing readers are composed because Chronicle's current committed rows
contain no classified issuer filings; the real positive proof comes from the validated
capital-structure spine. The ruling's six-path CI limit prevents declaring that new
closure without an amendment. Existing historical broad workflow edit and restoration
commits were preserved. There were no stale Delisting comments to delete (one unrelated
issue comment; zero review comments). No Ready, label, merge, deployment, or DDL action.
