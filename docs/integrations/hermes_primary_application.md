# Hermes primary APPLICATION service composition

Programme: https://github.com/mastermindx-market-intelligence/Mastermind/issues/983#issuecomment-6695933514

This proposal is stacked on the original APPLICATION implementation in Macro
#10740 at `2ef828e569b683b9dfaa94f81116da3ac55f6186`. It does not change that branch,
create another factory, or enroll a live service. Mastermind #2155 supplies the
bounded Hermes conversation/tool adapter and the native v5 enrollment extension.

| Hermes role | Factory service | Lane and native principal | Internal credential reference |
| --- | --- | --- | --- |
| mmsecretary | hermes_secretary_fabric | hermes-secretary | HERMES_SECRETARY_FABRIC_APPLICATION_TOKEN |
| mmmeta | hermes_meta_fabric | hermes-meta-ceo | HERMES_META_FABRIC_APPLICATION_TOKEN |

Both use the original `native_application_v1` client, `site_interactive` workload,
Go transport and fixed `deepseek-v4.1-flash` model for the initial strict slice.
They have separate capability and attribution IDs and no administrator pool-view
permission. Source qualification and ordinary application permission are held.
The shipped `application_fabric_modes` remains empty.

The authenticated native host selects the role's factory after checking its
original SessionAuthority admission. The original admission ID supplies the
APPLICATION operation identity. The retained binding and client survive native
facade reconstruction. Native tool/API-step identifiers are correlation, not
authority. A missing original binding after uncertain execution cannot be
reconstructed as a fresh request.

## Existing-owner enrollment

The native finite installer now accepts a closed v5 `service_profile` with the
exact lane/principal/reference above. Its existing plan, private payload,
publication locks, original intent and completion receipt commit that mapping.
It retains the physical account profile and canonical Broker grant. Multiple
services load into the existing handler's tuple; no service duplicates physical
capacity by model or creates another accounting owner.

Activation still needs genuine implementation qualification, an unexpired owner
mode record, the exact existing capability-manifest relation and the internal
credential issued by that original enrollment. Do not insert fixture-qualified
mode rows or replace source mappings at runtime. Provider credentials stay in the
native provider owner. A native interactive ticket and selected-worker OAuth do
not grant APPLICATION inference.

For each role, the capability-manifest entry uses the transport's capability ID,
its exact internal reference and only that role's lane. The existing mode record
uses the same immutable transport identity, `qualification_ref`, `qualified_until`
and current workload policy. The original factory checks all of these before it
resolves the internal credential. Configuring `qualified=true` elsewhere cannot
override this source's hold.

## Qualification boundary

The new tests reuse the incumbent factory fixture and verify role separation,
held-source rejection before credential access, native protocol selection and
original operation identity. Their synthetic grants are not runtime evidence.

The real canary must join one qualified host admission to one eligible physical
account, observe served model and actual usage, enforce the provider owner's
financial boundary, complete a native tool turn, and recover a timeout without
another provider call or tool execution. The current Go APPLICATION local-cost
projection still needs its existing-owner correction; unknown cost is not zero.

AUTO routing, strict pool constraints and further models extend the incumbent
picker, catalog and qualified transport. This first fixed-model declaration does
not claim those broader routes are active.
