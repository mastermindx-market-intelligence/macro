---
id: play_financial_thesis
kind: playbook
version: 1
title: Financial thesis reconciliation
priority: 35
triggers:
  - investment thesis
  - gross margin
  - cash flow
  - working capital
  - capital expenditure
  - 毛利率
  - 现金流
  - 現金流
  - 投资论点
  - 投資論點
  - 营运资金
  - 營運資金
  - 资本支出
  - 資本支出
---
FINANCIAL THESIS — inspect the economics before repeating the growth story.
1) Establish the actual question, comparison periods, common currency/scale, and accounting definitions. Keep verified source facts, user assumptions and your own hypotheses distinct. Do not assume missing figures or convert incompatible periods/currencies silently.
2) For supplied revenue/margin/expense/cash assumptions, use calculate_financial_bridge when that tool is offered and the arithmetic matters. Pass only values supported by the question or cited evidence. The tool cannot verify their provenance. If that tool is not offered, keep any standard arithmetic transparent and do not pretend a tool ran. Cash adjustments include applicable noncash addbacks, taxes and interest; leave unknown adjustments null. Never infer zero from silence, and never substitute an ending working-capital balance for its increase.
3) Explain the returned or transparently derived profit-and-cash bridge in plain language. Its additive attribution is an accounting calculation with a chosen order, not evidence of economic causation. A correct calculation on an unsupported input is still unsupported analysis.
4) Build the claim from observation -> expectations (only when dated evidence exists) -> plausible mechanism -> financial consequence -> valuation and horizon. Revenue growth is not automatically profit growth; profit growth is not automatically cash generation; business improvement is not automatically an attractive price.
5) Test a competing explanation at the weakest material link. A temporary mix/ramp or inventory investment may differ from weak pricing or demand; seek the segment, order, inventory-aging or subsequent-conversion evidence that discriminates. Do not assert the benign explanation merely because it is possible.
6) End with what the evidence establishes, what remains unknown and the next useful observation. Do not invent consensus, prior cash flow, a probability, target price or house signal. Self-contained arithmetic needs no compulsory web search; a material current-source gap must be named rather than filled from memory.
