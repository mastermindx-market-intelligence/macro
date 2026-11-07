# Basket extras: captured acquisition and actual thematic selection

Source continuation over `765cd41712a0a838f7ec68c659dd6dd3e8c092a9` in the original
Macro #10780 carrier. Qualified source only; no production activation.

## Existing owners

`scripts.fetch_basket_extras.acquire_extras_from_inputs` accepts captured dated
membership, a frozen primary panel, prior extras, the primary source owner's
qualified-member set, a primary history threshold, an aware evaluation instant,
request policy, aliases and an explicit history-start date. The qualified-member
set is a supplied input fact; this seam does not invent source qualification.

The existing `_download_closes` remains the sole extras request/retry owner. Its
legacy defaults remain intact; the explicit path supplies detached policy and
uses strict completed-session response capture. No `main`, `_seed_proxies`,
configuration/path read, cache write or independent selector runs in this path.
The original Yahoo owners retain their proxy dependencies.

Close-only matrices reuse the scalar/date/size validation from the adjusted-price
capture module. They do not manufacture high, low or volume to impersonate a
four-field capture. Canonical/vendor mappings are captured for the requested set,
reject collisions and unknown provider symbols, and retain canonical output keys.
The completed target uses the existing verified US market-session owner. Provider
publication/first-availability clocks remain unknown.

## Download planning follows the consumer

The existing `resolve_thematic_close_panel` selects later observed whole columns,
with extras winning same-date ties. The new seam uses that owner before planning
and again after acquisition; it does not create another resolver or change its
stitching rule.

A download is skipped only when the **actual selected primary column** has the
required observation, passes the caller's history-depth planning threshold and
belongs to the supplied primary qualified-member set. A deep/current column in
an unrelated source cannot authorize that skip. Retained extras that win a date
tie are requested, so a corrected primary cannot be silently presented as the
chosen thematic history while older extras still win.

Depth is a download-planning condition, not a minimum for newly observed IPOs.
A new member with two observed sessions can be acquired honestly. The existing
basket owner still decides partial history, effective start, return availability
and per-basket coverage. No new global extras percentage gate is introduced.

## Historical population and frozen clock

The full dated-membership universe remains available to historical resolution.
Current eligible populations come from the existing `population_observation`
owner. Historical obligations retain the final frozen-calendar observation within
members' original added/removed intervals. Removed members are not required to
print today's close, and future/outside-calendar members are not invented into
current coverage. Existing archived columns remain in the union even when no
longer requested.

The primary panel must have an actual observation on its last row. An all-null
future tail cannot become the desk date merely because extras has data there.
The resolver stays on that frozen calendar; a newer extras observation cannot
advance it. Caller-side broad/SPY alignment remains an independent input obligation.

Before both resolver calls, the projection's row/column cross-product is bounded.
The resolver receives only the required historical-member supplemental view;
the complete union archive remains separately retained. Input/archive bounds alone
would not have bounded the resolver's reindex allocation.

## Replacement and evidence

An accepted replacement must contain the required active or historical observation
and all prior non-null observation dates. A thin or failed response retains the
original prior column. The request uses the captured history-start policy exactly;
it never silently broadens that start or erases earlier retained history. Full
columns replace as one captured adjusted series, without filling a correction's
holes from an older basis.

Evidence keeps these facts distinct:

- Download requested/returned, observed response span and acquisition outcome.
- Prior archive retained and refresh unresolved.
- Actual final source/selection reason and selected history span/count.
- Observation at the provider target versus observation at the frozen desk date.
- Selected prior versus selected data acquired in this attempt.
- Current membership versus historical obligation and its actual selected observation.

A same-date prior may remain observed at the target during an outage without being
a successful correction. Conversely, a successful historical download does not
prove consumption: if the resolver chooses a later primary column that lacks the
required historical observation and cannot stitch, acquisition remains recorded
but the final result is partial with a separate selection-history shortfall.

The resolver accepts an optional explicit basis receipt without changing its
legacy default or selection arithmetic. New extras receipts conservatively default
to `unrecorded`; successfully refreshed members separately record the observed
`provider_auto_adjusted` acquisition basis. A supplied primary basis claim must
come from demonstrated capture provenance. Adjustment vintage remains unrecorded.
The later complete-runtime input assembler must propagate that source evidence
through the explicit basket/theme contracts; no legacy frame is relabeled here.

## Qualification

Command:

```text
python -m pytest -q tests/test_basket_extras_acquisition.py tests/test_breadth_price_acquisition.py tests/test_closes_panel_freshness.py tests/test_basket_index_recency_guard.py
```

Result: **103 passed, six existing temporary-directory cleanup warnings**, exit 0.
`git diff --check` returned 0. Log:
`/tmp/mmx-extras-capture-expanded-20261106.log`.

The literal legacy downloader is frozen from the base source in
`tests/fixtures/base_extras_download_765cd.py`, function SHA-256
`98a534528ad9254869405f4aea331f9fbbaf423e932841b42320c5f856819a95`.
Single/multiple-symbol and retry tests compare output and request/backoff events
with that source. Other tests cover no ambient effects, detached inputs/policy,
tie corrections, outage retention, short IPOs, historical backfill, source-clock
non-advancement, invalid inputs, pre-allocation bounds and final selection gaps.
Counts overlap the prior 56-test run and breadth qualification.

## Next integration

The source does not establish live provider availability or a private published
broad/member generation. Remaining work includes captured wide-panel storage,
coherent input identity/selection through the incumbent publisher, propagation of
source evidence through explicit consumers, pure basket handoff/board assembly,
and full Sector composition. Updater recovery/first-install fencing, legacy drain
and anti-downgrade, existing API/Terminal wiring, CI capability-owner policy
resolution, protected release and authenticated beta source-to-screen acceptance
remain open. The complete dashboard migration is not accepted by this checkpoint.
