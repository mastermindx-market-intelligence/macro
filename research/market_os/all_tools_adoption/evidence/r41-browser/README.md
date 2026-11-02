# R41 exact-tree browser proof

This directory binds the R41 Shared Shell repair to implementation commit `b50d1bf32c2b3ee74db4a65b451a0dbc284d8a43` on PR #7949. It is a new evidence epoch; historical R33/R35 screenshots and receipts remain untouched.

The first current Chrome run executed all 17 cases. Sixteen passed; `macro.html` at 320×844, light Chinese, with application typography tokens doubled reproduced a real reachability failure. Wrapped category controls consumed enough vertical space to reduce `.mmx-tools-body` to a 155px scrollport while one long destination row grew to roughly 293px. The repair keeps the mobile category rail on one horizontally scrollable line and prevents its buttons from shrinking. A targeted rerun passed 1/1, then the full matrix passed **17/17**.

The 24 PNGs are the exact post-repair captures emitted by the existing Playwright harness: six baseline desktop/mobile views plus top/footer captures for all nine narrow/landscape/double-type scenarios. Representative 320px and 390px captures were reviewed after capture. `receipt.json` records hashes, environment, current source verification, the failure/repair chain, and explicit limits.

This is local exact-tree browser evidence, not deployment or production acceptance. The doubled-type case is an application-token layout stress test, not native browser 200% zoom, physical-device, Safari/Firefox, or assistive-technology certification. No catalogue, router, account state, market preference, persistence authority or pilot scope changed.
