# ROR-1 — principal pages were unmounted; held multi-market projection still invisible

**Research-only, October 16, 2026.** This note preserves two independent consumer failures without assuming a production deployment or modifying an incumbent source/alert owner. Root commission: [Mastermind #1478](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1478).

## 1. Exact static script-mount census (source, NOT installed browser)

Machine receipt: `evidence/banner_mount_source_census_20261016.json` (SHA256 `a4514fd28992d3bfa4c7f3cf8bf56a0d0e4420980e1d50ccfbbe7a275105f67d`).

| Source page | Oct13 original Git (`c49e4410`) | Oct16 main Git (`4ae7f2ac`) |
|---|---|---|
| `site/index.html` | **UNMOUNTED** | **UNMOUNTED** |
| `site/macro.html` | **UNMOUNTED** | MOUNTED |
| `site/china.html` | **UNMOUNTED** | MOUNTED |
| `site/hk.html` | **UNMOUNTED** | MOUNTED |
| `site/markets.html` | MOUNTED | MOUNTED |
| `site/status.html` | MOUNTED | MOUNTED |

The registered shared alert client is `wh_banner.js`. The four principal pages were missing the `<script defer data-whb data-root="" src="wh_banner.js?...">` tag at the **actual October 13 main commit** (published 16:32:31 UTC). Two controls already mounted the same client, proving the absence is page-specific rather than the code file's nonexistence. The current homepage remains missing even though the U.S., China and HK pages gained the script. There may be other alert components not tested here; this is not a negative proof of every possible user message path.

Each page was read as `git show <exact-commit>:site/<page>.html` from an existing original repository object database into an **isolated research directory**, then classified with Python `HTMLParser`. The 12 page source blob hashes are bound in the receipt (including Oct13 CN `9254db12acf4f9d3ed7571595669fda0f678400f`, HK `73c3e20d63bf105692010d760196c2f61b4a4c97`, Macro `217a4a1a542c11e795285f6d0d9966c49f70874e`). No worktree/source files were changed.

Reproduce the offline parser from exact Git copies:

```bash
python -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_banner_mount_census.py' -v
```

Pure `audit_banner_mount_census.py`, **12/12** synthetic tests passed after a test-first RED stub and an additional symlink-escape RED→GREEN fix. It rejects comment/text markers, invalid/misrouted scripts, duplicates, missing files, unsafe paths and symlink escapes. It reports `installed_browser_proven=false` and `authenticated_user_delivery_proven=false` by design.

## 2. Actual held PR #8132 Chromium characterization — no country projection and no live refresh

Existing held Grey Deer `templates/wh_banner.js` source Git blob **`9362255160a6a7358014632c53dd865dad163ebe`**. Standalone synthetic Chromium test `test_held_banner_client_gap.py` executes those exact bytes against mocked `wh_banner.json` / `rr_banner.json` on `about:blank`. The only tested network is a local in-page `window.fetch` stub; there is **no request to a production API, no credentials, and no customer message**.

**3/3 browser tests executed and passed**, source blob asserted:

1. `rr_banner.v1` with `alert=null`, `warning_projection` containing native China `critical/risk-off` => **zero banner nodes**. The client only reads `data.alert` and never refers to `warning_projection`.
2. Following an initial `alert=null` boot, the synthetic feed changes to a legacy severe `alert`; a `visibilitychange` and focus event produce **no additional requests** and the banner stays absent. The client calls the two fetches once during `boot`, with only display-alternation on `setInterval`, not a background data refresh.
3. A legacy severe `alert` already in the first fetched response **does render** the critical banner. This separates the missing projection/refresh paths from broken script execution.

Exact browser research receipt: `evidence/held_banner_consumer_gap_verified_20261016.json`, SHA256 `d4e8c2dadb197a5f585c1d2d2b082d8e3d4f6ace3a01efa8da48bc990634537f`.

Reproduce the held candidate only with a **separately obtained original source checkout**, not a private copy inside this research PR:

```bash
export ROR1_BANNER_SOURCE=/trusted/existing-pr8132-worktree/templates/wh_banner.js
export ROR1_BROWSER_RECEIPT=/tmp/unique-ror1-browser-acceptance.json
python research/grey_deer/ror1_risk_attention_20261015/test_held_banner_client_gap.py
```

This research test is for an **explicitly installed local Chromium** on an authorized machine; it cannot substitute for the original release browser matrix and should not be quietly counted as CI browser coverage when absent.

## 3. Product impact and source-owner repair direction

- October 13 had a third independent obstruction beyond detector gating and global attention: **four principal page HTML sources did not mount the shared banner client**. The source dates are older than any current installed client; do not ascribe the failure to a present user without actual response/DOM proof.
- The current main Risk Radar banner payload remains a separate U.S. **legacy extreme-gated** producer; Oct16 inspected `site/rr_banner.json` still has `alert=null`. The original U.S. Radar is Caution while raw ungated is Risk-off. Do not remove its calibrated gate to force an alert; use the existing descriptive projection and competent native hazard source.
- Adding the script alone to the current homepage will **not** display China/HK `warning_projection`, because the held browser candidate never reads that field. Adding a multi-country projection to the JSON alone will **not** deliver a new warning to an already open tab, because the client does not refresh the payload.
- The held #8132 source adapter also reads the wrong China/HK native Radar paths and the existing R2 native feed is on a different U.S. evening schedule and Essential-tier rights. Source/binding/entitlement must be corrected by their respective owners; do not publish raw premium feeds to anonymous users.
- **Correct scope of work:** existing page/site owner resolves homepage mount (check overlapping historical homepage PR #7267); original Grey Deer warning consumer owner adds source-bound, eligible market/attention display with meaningful native dates, safe EN/ZH copy and a governed refresh/episode lifecycle; the existing publisher and auth owner proves installed source version, origin/edge bytes, long-open mobile/desktop display, and notification/acknowledgment.
- Preserve original C1 Macro #9428 CSS and CI contract-delta holds, #8132 REQUEST_CHANGES, the earlier entitlement/SSH refusals, and the separation of Market State backdrop, observed country damage, data health, forecasts and capital policy.

**NOT COMPLETE:** no production deployment, actual user-delivery receipt, newly issued market forecast, or trading instruction is established by these tests.
