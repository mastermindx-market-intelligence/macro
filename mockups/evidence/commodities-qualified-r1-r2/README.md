# Qualified R1/R2 whole-page browser evidence

Exact source pair: R1 0b2493990358d44dee5b625176c5289eab9a04e4 plus R2 306834682e15121c636db1091a1de8f242c3608e. The source-pair identity matters: the product PRs remain separate and unmerged.

24 whole-page synthetic states cover split, missing and lagging asset inputs in
EN/ZH, dark/light and 1440/390. Mobile contexts use touch emulation. Every state
checks the requested viewport (not an already-expanded layout width), unexpected
overlays, theme/language, page errors, and four card-to-detail interactions: 96
verified selections. The canonical R2 capture now reproduces this mode with:

    python3 scripts/capture_commodity_asset_read_evidence.py --full-page --output-dir <new-proof-directory>

It reuses the existing commodity renderer and R1 capture owner. R1 must be present;
there is no new browser, chart renderer, token family or screenshot control plane.
Without --full-page, the existing component-capture mode is preserved.

The renderer deliberately stubs global navigation and external hydration and uses
synthetic model inputs. This is whole-page fixture proof, NOT production, auth,
current-market, feed-rights or independently reviewed design acceptance. The live.js
fresh/stale/out-of-order packet test is a separately identified synthetic consumer
receipt, not a claim of a live provider connection.

Author visual review inspected both light research surfaces and dark panels, English
and Chinese responsive composition. Independent exact-source review is still owed.
All PNGs are content-addressed; no duplicate aliases are committed.
