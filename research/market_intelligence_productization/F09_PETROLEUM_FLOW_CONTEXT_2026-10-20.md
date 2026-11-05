# F09 petroleum flow context

MO-PAID-040 / MO-DELTA-027: give the Commodities reader a sourced, three-stage
physical-flow chain for one commodity, alongside the existing coverage explanation.
This closes a different capability from the annual USGS concentration read.

Use the existing EIA weekly stores: US crude field production, refinery crude
inputs, and gasoline/distillate products supplied. Select one common observation
period across all four series. These are aggregate industry stages, not tracked
movements of the same barrels. Do not derive a conversion yield or balance.
Products supplied approximates consumption through disappearance from primary
supplies; it is not measured final consumption.

The native source's nine-day stale threshold is explicit. Old values remain
visible as historical context with the observation date, age and evaluation date.
Missing or invalid coverage is unknown; do not substitute zero, align different
weeks, forward-fill, or claim knowledge/release timestamps absent from the store.
The computation remains display-only and outside signals, allocation and latest.json.

## Consumer and composition

Primary question: where in the US petroleum chain do these weekly quantities
belong, and how recent are they? Archetype D: the existing Commodities regime
dashboard. Reuse the coverage section's secondary reading depth and the existing
neutral `.panel`, `.cm-context`, `.cm-row` and `.cm-source` components. Three
ordered definition rows convey production, processing and product supply. No
new chart, palette, token family, navigation, scoring badge or directional color.
Keep the established page hierarchy and density; this is evidence under coverage.

**Dark treatment:** existing graphite surface, restrained neutral rules, high
contrast numeric text and muted explanatory text. No glow or bullish/bearish fill.
**Light treatment:** existing white research surface on the cool canvas, hairline
row separation and the established panel depth. The layout is shared because
these are neutral definitions, while canonical theme surfaces supply the distinct
material treatment. No runtime styling.

Both themes keep stale/unavailable language visible without relying on color.
EN/ZH labels and units are paired. Mobile stacks existing label/value columns;
there are no fixed-width tables. Native details/summary exposes the four EIA
source links, period rules and measurement limits, with the existing focus style.

## Acceptance

Pure helper tests cover common-period selection, freshness boundaries, invalid
values, missing series, future periods, conflicting duplicates and unchanged inputs.
Consumer tests prove honest unavailable/stale copy, units, distinct clocks and
source links. Rebuild the full page from the existing committed research payload;
verify its inline chart/script bytes and unrelated machine data remain unchanged.

Inspect the actual page at EN/ZH × dark/light × desktop 1440/mobile 390, including
keyboard disclosure and a controlled missing-source state. Record source binding
and real crops through the existing visual-evidence mechanism. After protected
merge/publication, verify the actual served module and retained source values.
