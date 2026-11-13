# Macro workspace visual evidence

Source: fca9114d922d21a3b88e6406b02e2368da66db9c. These are explicit representative and unavailable fixtures, not live market observations or production acceptance. Full input provenance is in tests/fixtures/macro_workspace/SOURCE.md.

The canonical capture tool recorded 16/16 states, with no page console errors or failed responses. Its viewport measurements found no horizontal overflow. Authenticated service behavior is outside this fixture.

| State | Layout | Language | Theme | Capture |
|---|---|---|---|---|
| Populated | desktop | en | light | [PNG](19c14295fb404650.png) |
| Populated | desktop | en | dark | [PNG](8997f8fbe91d12b4.png) |
| Populated | desktop | zh | light | [PNG](6ffb0f3e112e9863.png) |
| Populated | desktop | zh | dark | [PNG](83f84a4b36dfdcae.png) |
| Populated | mobile | en | light | [PNG](c4244d9e4a5890da.png) |
| Populated | mobile | en | dark | [PNG](c9a2df07f3a16e5a.png) |
| Populated | mobile | zh | light | [PNG](fe221cba2a44b802.png) |
| Populated | mobile | zh | dark | [PNG](c84e90a95def6310.png) |
| Unavailable | desktop | en | light | [PNG](fad7f009ffdfbdb4.png) |
| Unavailable | desktop | en | dark | [PNG](81c5316dfeac9726.png) |
| Unavailable | desktop | zh | light | [PNG](cd20f6a4f2c0e7ae.png) |
| Unavailable | desktop | zh | dark | [PNG](bf9c816cd6fa0193.png) |
| Unavailable | mobile | en | light | [PNG](ae1735046d11b171.png) |
| Unavailable | mobile | en | dark | [PNG](c042cb6832bb13e9.png) |
| Unavailable | mobile | zh | light | [PNG](fa0eb77677dd85dd.png) |
| Unavailable | mobile | zh | dark | [PNG](6da8301928b6cde0.png) |

## Asserted interaction states

The separate browser suite passed 31 cases on the same source. These five images were taken inside those assertions. See journeys.json for exact input blobs and image hashes.

- [desktop briefing index](journeys/desktop-briefing-index.png)
- [desktop drivers index](journeys/desktop-drivers-index.png)
- [history provisional zh](journeys/history-provisional-zh.png)
- [mobile driver dialog return](journeys/mobile-driver-dialog-return.png)
- [mobile history touch](journeys/mobile-history-touch.png)

## Limits

The shared-navigation cold-load shift remains with held carrier #10261. The frozen rates fixture retains the known source-semantic discrepancy owned by #10493. No screenshot is a claim that either dependency is resolved.
