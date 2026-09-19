# China Gold Basis Proxy — visual evidence

This corpus captures the actual Commodity Vector Gold panel at exact integrated PR #7325 head
`b7a4f813ad939eca6468195ef32b63c48f131f06`. The geometry comparison uses feature-free pickup base
`4b420718773b57df57f5fe779bb990a0b7e7704d`.

## What is proven

The fixture is routed through the production `engine.china_gold_premium` close-proxy
path and the production `commodities.china_gold_premium.close_proxy` config shape.

It demonstrates the **indicative Shanghai-close basis**:

- SGE Au99.99 in RMB/gram, converted with 31.1034768 grams per troy ounce;
- global XAU/CNY spot at the Shanghai 15:30 close clock;
- premium %, CNY/oz spread, and CNY price-level chart modes;
- source/method disclosure without public vendor branding;
- dark/light × EN/ZH × desktop 1440/mobile 390.

The canonical page-evidence manifest contains **8/8 captured states**. Supplemental
`panel-proxy-*.png` files are element crops of the Gold panel itself.

## Geometry / runtime proof

`panel_checks.json` binds the panel to the exact semantic head and compares the feature page
with the feature-free pickup page:

- feature worsened document overflow: **0**
- Gold panel overflow: **0**
- browser page errors: **0**
- wrong display method/currency metadata: **0**

The feature-free commodities page already carries a 390px whole-document overflow owned by
commodity safety R1 #7198. This Gold panel fits at 390px and adds zero document-width regression;
the inherited whole-page defect remains lane-local to R1 rather than being silently reassigned here.

## Source honesty

The visual **available** state uses deterministic source fixtures. It is not a claim that
the live SGE/Tushare and Massive Currencies calls have already run in production.

The implementation wires those governed sources into the existing US-nightly collector
lane, whose authoritative run occurs after the Shanghai close and already carries the required
repository secret bindings. Production source proof still requires that normal secret-bearing
nightly run after lawful merge. If either technical source is unavailable, the product engine
fails closed rather than substituting futures, an ETF, or an unofficial quote.

The official SHAUPM/LBMA-AM canonical benchmark remains a separate method and is not
fabricated by this proxy.
