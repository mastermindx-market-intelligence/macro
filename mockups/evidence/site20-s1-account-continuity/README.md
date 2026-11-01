# site20 S1: account and preference continuity — browser evidence

Real-browser acceptance for bundle S1 (S1-01..S1-04, `templates/account.js` / `site/account.js`).

## What runs

`browser_s1.py` starts Playwright Chromium against the rendered consuming page `site/alerts.html`. That page's settings gear carries the real theme segment and language switch, and the account panel is opened through `MMAccount.open()`. The page is served from this checkout's `site/` on `127.0.0.1:18821`.

It is local-only by construction:
- Every request to a host other than the local server is aborted, so it is never sent.
- Websockets are closed and `supabase.js` is aborted, so no identity SDK runs.
- `/api/account*` is answered by an in-process mock that uses fictional fixtures (`*.fictional@example.test`).

## Results

| Task | origin/main `account.js` (pass / fail) | this branch (pass / fail) |
|---|---|---|
| S1-03 failed account read vs signed-out | 2 / 8 | 10 / 0 |
| S1-01 theme + language persistence | 7 / 13 | 20 / 0 |
| S1-02 notification-pref acks | 12 / 7 | 19 / 0 |
| S1-04 sign-out-everywhere outcome | 2 / 6 | 8 / 0 |
| Total | 23 / 34 | 57 / 0 |

The passes on main are positive controls: behaviour that was already right and must stay right. Per-check lines are in `results/fix/` and `results/main/`. `crops_inventory.json` records the sha256 of the `account.js` bytes the fix run served, which are this branch's committed bytes.

## Crops

`shots/` holds 16 crops of the account panel (`.mmacc`), one for each combination of state × theme × language × width:
- state: `unavailable` (the account read failed) or `signout-unknown` (sign-out everywhere not confirmed)
- theme: dark or light
- language: EN or ZH
- width: 1440 or 390

`crops_inventory.json` lists them.

Both states reuse the panel's existing classes. Two rules changed in the panel's existing injected stylesheet; no new style element was added:
- `.mmacc-msg.bad` (the "could not confirm" line, among others) now uses the severity token `--ink-act` / `--act`. It used to use the market-direction token `--ink-down`, which turns green in ZH, so the error read green there. The `signout-unknown` ZH crops show it red.
- A narrow-width rule (`max-width: 560px`, unavailable state only) start-aligns the "Try again" row. See the next section.

## 390 px hit test

At 390 the panel is a bottom sheet, and the page-wide chat launcher (`.mmb-orb`, from `mm_brain.js`) floats over its bottom-right corner. Before this fix the unavailable state's "Try again" was end-aligned into that corner, so a pointer tap landed on the launcher. `results/probe_390_hit_test_before.json` shows this:
- At 390 all four theme × language runs fail: `target_hit: false` with the orb topmost.
- A real pointer click times out, so the retry never runs.

The row is now start-aligned on the sheet, so the button sits at the left edge, clear of the launcher. `probe_390.py` (output `results/probe_390_hit_test.json`) checks 390×844 and 1440×900 in dark/light × EN/ZH. In each run it:
1. Fails the account read.
2. Hit-tests "Try again" at its centre.
3. Clicks it with a real pointer.
4. Requires that the panel re-read the account and show the signed-in head without a page reload (`P3`).
5. Then checks that "Sign out everywhere" and the danger-zone request button are each topmost once scrolled into view.

All 8 runs pass all of these.

## Re-run

From the repository root (Playwright for Python installed):

    python3 -P mockups/evidence/site20-s1-account-continuity/browser_s1.py --variant fix --out <out-dir>
    python3 -P mockups/evidence/site20-s1-account-continuity/probe_390.py --label fix --out <out-dir>

For the red reference, write `origin/main`'s `templates/account.js` to a file and pass it as the main variant:

    python3 -P mockups/evidence/site20-s1-account-continuity/browser_s1.py --variant main --main-js <file> --out <out-dir> --no-crops
    python3 -P mockups/evidence/site20-s1-account-continuity/probe_390.py --js <file> --label main --out <out-dir>
