# Commodities asset-first R1 — browser fixture evidence

Source: `1c0e7f85388be15f102adf1a3e8a7156a1fe91f1`. 32/32 Chromium cells: mixed, incomplete, gold timeframe conflict, and risk board; dark/light × EN/ZH × 1440/390. Every cell passed document-geometry and theme/locale checks.

These are synthetic fixtures rendered with the actual commodity template and producer functions, not current market readings or production-deployment proof. Navigation, live quote hydration, oil episode, coverage matrix and webfonts are omitted. No external network requests were permitted. Source snapshots have no Git metadata; exact published blobs were materialized and recorded before capture.

The old d1163 mobile proof is not accepted: its document overflowed 390px to 517px (EN) and 415px (ZH). This corpus reflects the committed responsive repair and the capture guard that rejects such overflow. Numerical model signs/weights/allocations are unchanged.

Reproduce through `scripts.capture_commodities_w6_evidence.py --subjects r1-mixed-hero,r1-incomplete-hero,r1-gold-conflict,r1-risk-board` at this source, using the normal isolated proof output. Hash-named PNGs are the canonical files; redundant aliases are omitted.
