# China Gold Basis Proxy — visual evidence

This corpus captures the actual Commodity Vector Gold panel at semantic head
`84172b5f4b9f2c556b9d5bf4a46c01f113f304a3`, stacked on parent PR #7325 head
`bd51c2b286827956d54c1afc0af78df4ffc797a2`.

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

`panel_checks.json` binds the panel to the exact semantic head and compares the child
page with the exact stacked parent page:

- feature worsened document overflow: **0**
- Gold panel overflow: **0**
- browser page errors: **0**
- wrong display method/currency metadata: **0**

The parent commodities page already carries a 390px whole-document overflow owned by
commodity safety R1 #7198. This child does not worsen it; final whole-page mobile proof
remains dependent on the incumbent R1 integration.

## Source honesty

The visual **available** state uses deterministic source fixtures. It is not a claim that
the live SGE/Tushare and Massive Currencies calls have already run in production.

The implementation wires those existing governed sources into the Asia collector, but
production source proof still requires a real secret-bearing Asia run after lawful merge.
If either technical source is unavailable, the product engine fails closed rather than
substituting futures, an ETF, or an unofficial quote.

The official SHAUPM/LBMA-AM canonical benchmark remains a separate method and is not
fabricated by this proxy.
