# D05 audit observations and limits

Audit ran across 2026-11-03/04 UTC. Product source pin df691495abb1c2ba8f61e5624126cb17ad14e056; source paths and owner evidence in SOURCE_EVIDENCE.md. No product source was modified.

## Observed production behavior

| Observation | Evidence class | Interpretation |
|---|---|---|
| Sector Central hydrated after initial as-of dash | Authorized connected-browser read | SSR/loading metadata needs coherent visible source date; settlement itself worked |
| Explore/Map and Energy selection worked | Browser interaction | Core sector inspection remains useful and should be retained |
| Sectors 11 selected while map/list displayed 38 theme entities after settlement | Browser interaction/readback | Scope/population mismatch; actual release falsifier |
| Measured evidence showed all 11 ETFs, Energy rank 1, +12.9% 21-session / +19.8% 63-session, Oct30 | Browser plus source semantics | Dated snapshot used in A01; not current quotes |
| Reconstructed history Nov2 versus current Oct30 was withheld | Browser readback | Correct safety behavior to retain |
| Prophet continuation shape was us_stocks.html?si_sector=XLE#sector-prophet-context | Browser link observation | Destination exists as a source-bound bridge; actual onward/return proof not completed |
| Grader showed about 26%, n=715, v1 through Oct16 | Browser readback | Preserve denominator/date; not a win rate |
| Fast rotation ranks were older, latest Oct16 | Browser readback | Show source freshness separately from the page build |
| Retail click reached /basket/retail.html with HTTP 524 | Same-tab post-timeout reconciliation | Route navigation occurred; successful basket content/journey unproven; no repeated click/reload |
| Canada XEG.TO navigation timed out; same tab remained Retail 524 | One bounded diagnostic | Canadian production path unproven; source route separately confirmed |
| Footer showed Nov3 09:57 UTC | Browser readback | Build timestamp, not a replacement market observation date |

Screenshot before-production-energy.jpg preserves the last useful production state. No account state was changed. No production save or transaction was attempted. No alternate browser/carrier was used to evade the observed failures.

## Source facts that materially change the design

1. The allocation builder was missing in the assignment census but is scripts/build_allocation.py::build_region.
2. The three subsector detail families share build_subsector_confluence.py and subsector_detail.html.j2, with different namespaces.
3. /sectors/ has four implementations. HK slugs are not fund symbols; Canadian “holdings” need constituent-group qualification.
4. subsector_rotation.html is a compatibility redirect, not a separate dashboard to redesign.
5. factors.html is explicitly denied; a polished customer destination would violate current access intent.
6. Current router has 24 aliases, not the old ledger's 21.
7. Current Cycles already includes median-elapsed projection handling. The Retail basket defect is a different source path.
8. Central's research handoff already carries a native subject/digest/generation/return shape, but is adapter_only, with methods/research receiver and governed Dossier fields absent.
9. State of Themes already has source identity, dimension and correction-lineage projection. A D05 provenance service would duplicate an existing owner.
10. Saved sector investigations cloud-store only the subject; full note/context is device-local, and the ETF-only input rejects regional listing strings.
11. The Central relative-trend additive call occurs before its local fdir assignment; the caught exception can skip this emission.
12. Existing partial #9917 merge did not deliver native in-shell Cycles or Dossier Cycle. No design packet can claim that integration complete.
13. Confluence n_priced counts any nonempty price history; native coverage_pct instead measures positive-volume coverage of current live members. A06 was corrected to “Price histories”; no per-member date is supplied.
14. Basket census fields are present in current engine code but absent from the committed basket_confluence payload at the same audit pin. Source, publication and consumer acceptance remain distinct.
15. State of Themes treats explicit positive missing-falsifier count as UNCONFIRMED, but absent thesis/summary currently defaults to NOT_DETECTED. The specification now distinguishes that source gap from the required unavailable/unconfirmed target.

## Paper audit and edits

R3: 23 boards read-only in file 01M2WGNCX9475G79JRKJTCM08P/p-24-0. R4: 24 incumbent boards read-only in file 01M6FAXA774QT1VRDMAG7DFQ2W/p-2-0. Original names, IDs and accepted features remain the baseline.

D05 created p-3-0 and twelve candidate boards. A11 clones the strongest native R4 Brief content; other candidates compose retained behavior into the shared shell, regional journey and explicit semantic states. Actual screenshots were inspected and iterated for clipping, density, copy, source qualification and responsive composition.

All D05 effects have observed responses. Some layout properties on cloned wrappers did not change despite an acknowledged update; those effects were read back and the owned wrapper layout was rebuilt around preserved cloned children. One move to an empty Rectangle failed with explicit zero-move errors; new Frame containers resolved it. No timeout/unknown effect was retried.

Unrelated unknown Paper operations remain frozen and unretried. D05 used one native write carrier, exact file/page/targets and stable operation IDs. The final p-2-0 readback still contained 24 incumbent boards and the file token hash remained unchanged.

## What has not been proven

Actual Company return; regional end-to-end paths; full auth-tier matrix; keyboard/screen-reader/touch behavior; instrumental contrast; all locale/theme/width combinations; saved-record mutation/readback across devices/accounts; all historical availability claims; formal RIG; foundation acceptance; code integration; CI; deployment; natural refresh; production acceptance.

TEST_MATRIX.csv specifies these proofs. It does not report them as executed.

