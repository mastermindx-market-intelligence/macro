## Source verdict: PASS for the corrected candidate

**No remaining blocking source findings from the closed R3 review list.** This is approval to continue the root’s validation, conditional on the broader regression, build, and actual-parent evidence.

I reviewed `ROOT_REVIEW_CORRECTION.diff` at SHA256 **`e169ee1993cd500ea3034d99041cb86839e4023448082e96dada43f08db546d5`**, its receipt, and both corrected files directly. Applying that delta in memory to the exact R3 preimages reproduced the observed controller and test source.

Reviewed identities:

| File | SHA256 |
|---|---|
| `templates/intl_country_cockpit.js` | `1ba7eb423077e23142260eb77064afb076f9d8670cdc11d1925b18ebd9323042` |
| `tests/intl_country_cockpit_navigation.test.cjs` | `e5ce4d082e182986931a3d68a6ca6d49ca4e36227df9d4e21cdbdc2064b37f20` |

### Blocking findings are addressed

- **Stale scrolling:** controller lines **169–185** now advance the generation before target validation. The callback also requires the intended encoded fragment and exact current pathname/raw-query snapshot. A newer non-research destination or query change can no longer leave the old callback authorized merely because it did not resolve to research.
- **Native exclusions:** the old root-only literal Tools branch is removed. Active-bridge classification now delegates to the shared helper; standalone exclusions remain in the standalone path. This preserves the bridge’s first-party `role="button"` exception.
- **Already-cancelled activation:** line **228** respects `defaultPrevented` before opening disclosures or scheduling alignment.
- **Nested-repeat discrimination:** the corrected test uses the same deep destination after Library selection, explicitly closes all relevant ancestors, and compares settled navigation/ACK/history counts.
- **Fixture and restoration claims:** the anonymous reference fold now occupies the production-relative position inside legacy research. The modeled history test and header explicitly limit their claim to wrapped child navigation, rather than `INIT.restore` or fresh-frame restoration.

The correction does not add parent, protocol, focus-retry, or navigation-policy work. The bridge classifier architecture remains as reviewed in R3.

### Runtime evidence read

I also read `corrected_targeted/receipt.json`, bound to the two hashes above. It records:

- Corrected navigation suite: **18/18 pass**.
- Unchanged independent root probes: **2/2 pass**.
- Four new discriminators against the rejected R3 controller preimage: **0/4 pass, all four fail as expected**.

Those results support that the corrections address detectable defects. I did not execute tests myself.

### Remaining acceptance boundaries

The actual-parent **saved position away from the hash heading** remains a required gate: matching the current URL is not proof that a deferred alignment preserves a legitimate restored reader position. Broader regression results, built-asset binding, and the actual-parent matrix must still be satisfactory.

The pre-existing parent focus-restoration failure remains separately reported under its exact baseline classification. Later target/bubble cancellation remains explicitly unproved; this source approval does not broaden that claim.

**PASS for the exact corrected source; final runtime acceptance remains conditional.**

STOP.
