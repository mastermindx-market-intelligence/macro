# Bonds warning-token correction — screenshot evidence

**Exact source commit:** `4213eaea17b248da0ea5c634102d6256e1a00eff` (Macro PR #9590, Draft/HOLD).

**Verified Vercel preview artifact:** `e1e344265048db3227d7a3a6beb46031179b8c25`, deployment `dpl_7x9GmeNAfBtAzXF8XnL8RVCwQeRD`, preview: `https://macro-5o37k7yw7-chriswong6031-creator.vercel.app/bonds.html`. This is the corrected candidate, **not** the earlier preview `macro-g197gve9p-...` bound to 653399.

## Actual evidence and source binding

- The artifact-only preview Git tree contains exactly 30 files (one rendered HTML + 29 support assets), total 1,852,259 bytes. The local capture tree was extracted verbatim from that Git commit using `git archive`, not rebuilt or synthesized from another source. It is retained at `.cdi-proof/integration-20261022/preview-e1e344-site-verified` in the original local worktree. That archive's complete 30-file manifest was verified against `git ls-tree` and the three affected emitted files were byte-compared with the current source worktree.
- Rendered `bonds.html` SHA-256: `15c2e9a83b4943dba46b52de76637ff62cc41a7f085cd5a665c293f209456b2a`; light/dark template CSS assets SHA-256: `41a0f008c61f32b16ea86bb4e5dadb8a37c6b0573a99e57fffe81612e0b7c234` and `e42cc80f1de90ba7a40613f56b257de5a9b94f354e44d58c222056d83bd2c6c6`.
- `manifest.json` is the existing canonical `mastermind.p0_evidence.v2` schema from `scripts/capture_page_evidence.py`, with **16/16 real Chromium full-page screenshots** in `evidence/`: 8 rest views plus 8 clearly declared browser-focused `cdi_focus:focus(#cdi-search)` states. They cover desktop 1440×900 and mobile 390×844 × English/Chinese × dark/light. Each PNG was verified against its byte length and SHA-256, and requested theme/locale agrees with actual `<html>` state in every cell. The focus states are labeled browser-applied presentation checks, not evidence that a human navigated every cell by keyboard. The screenshots are full page; image pixel height can exceed viewport height.
- `supplemental-observations.json` and `supplemental/` contain **8 additional real Chromium viewport screenshots**, in desktop English dark/light: illustrative duration launcher, CDI search field keyboard-focus styling, CDI issuer summary hover, and the duration dialog opened through its actual enabled launcher followed by a real `Tab` keyboard focus. Each screenshot has SHA-256/byte-length verification, and the interaction-gallery is a reduced-size visual index, not an independent evidence source.
- The source's scenario explicitly has `data-duration-origin="illustrative"` and is **not live portfolio holdings**. The credit panel shows its source as historical (October 15, 2026), 0/18 paired issuer comparisons and 311 mapped bond holdings; those data restrictions remain unchanged. The orange warning border, disabled release gate and other risk language cannot be interpreted as current verified credit conditions.

## Scope and residual gaps

The capture ran against **anonymous local HTTP serving the exact Vercel-deployed 30-file package**, not the signed-in Chrome remote Vercel origin. The connected Chrome browser exposed that URL but only read-only page context was available to this session; therefore do **not** call these signed-in Chrome screenshots or full production-path browser acceptance. The manifest's nearest-Git-HEAD `4213eaea` provenance is a repository relationship and, as the tool itself warns, is not alone proof of the served archive; the artifact-source binding is the explicit Git-tree and SHA verification above.

The preview package emitted one `/account.js?v=20261018-shared-shell-source-join` 404 (the file is absent from the 30-file preview package). All 8 screenshots were still real captures with the corrected CSS loaded, but this missing asset remains a disclosed browser-console defect/gap. An initial **invalid** local capture served the sparse checkout, incurred many asset 404s and was quarantined under `.cdi-proof/integration-20261022/incomplete-sparse-site-capture-4213-20261025`; its screenshots were **not** adopted here.

A visual acceptance reviewer must independently adjudicate actual theme appearance and any layout/accessibility issues. CI, data freshness, source adoption, release permission, and Forex/SQL privacy/operator activation holds are separate; `EVIDENCE.yml` is an evidence receipt, **not** a merge/deploy/acceptance authorization.

## Reproduction

```sh
# From a checkout that has both exact commits in the Git object store:
git archive e1e344265048db3227d7a3a6beb46031179b8c25 | tar -xf - -C "$VERIFIED_30_FILE_PREVIEW_DIR"
python3 scripts/capture_page_evidence.py --site-dir "$VERIFIED_30_FILE_PREVIEW_DIR" --routes /bonds.html --viewports desktop,mobile --locales en,zh --themes dark,light --settle-ms 1200 --delay-ms 150 --timeout-s 25 --max-pages 1 --force-state "cdi_focus:focus(#cdi-search)" --output-dir mockups/evidence/bonds-warning-token-4213-20261025/evidence --manifest mockups/evidence/bonds-warning-token-4213-20261025/manifest.json --smells mockups/evidence/bonds-warning-token-4213-20261025/smells.json
```

The supplemental capture script and unmodified run logs are retained in the local source proof directory; their state observations and PNG hashes are included here. No screenshots were retouched or substituted as original captures; only `interaction-gallery.png` resizes source screenshots for the index.
