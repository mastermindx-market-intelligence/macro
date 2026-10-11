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

The passes on main are positive controls: behaviour that was already right and must stay right. Per-check lines are in `results/fix/` and `results/main/`.

## Crops

`shots/` holds 16 crops of the account panel (`.mmacc`), one for each combination of state × theme × language × width:
- state: `unavailable` (the account read failed) or `signout-unknown` (sign-out everywhere not confirmed)
- theme: dark or light
- language: EN or ZH
- width: 1440 or 390

`crops_inventory.json` lists them. No CSS or runtime style was added: both states reuse the panel's existing classes.

## 390 px hit test

At 390 the panel is a bottom sheet, and the page-wide chat launcher (`#mmb-launch`, `z-index: 2147483000`, from `mm_brain.js`) floats over its bottom-right corner. That launcher already covers the signed-in panel's bottom-right controls on `origin/main`. It also covers the new "Try again" button in the unavailable state, so a pointer tap on that button lands on the launcher.

Recovery without a reload still works at 390 in two ways:
- Close the panel (✕, top right) and reopen it. `open()` retries the read.
- Use the keyboard. "Try again" is focusable and activates with Enter.

The output is in `results/probe_390_hit_test.json` and `results/probe_390_recovery.json`. The launcher's layering belongs to the chat module and global chrome, so it is not changed here.

## Re-run

From the repository root (Playwright for Python installed):

    python3 -P mockups/evidence/site20-s1-account-continuity/browser_s1.py --variant fix --out <out-dir>

For the red reference, write `origin/main`'s `templates/account.js` to a file and pass it as the main variant:

    python3 -P mockups/evidence/site20-s1-account-continuity/browser_s1.py --variant main --main-js <file> --out <out-dir> --no-crops
