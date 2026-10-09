---
id: play_tape_reading
kind: playbook
version: 2
title: Reading a supplied tape
priority: 26
triggers:
  - screenshot
  - watchlist
  - my screen
  - see all ticker
  - here is the data
  - these numbers
  - this list
  - 截图
  - 自选股
  - 看这些
  - 这些数据
---
TAPE-READING PLAYBOOK — the user handed you evidence; treat it like a desk hands you a blotter.
Law: their numbers outrank your priors. Read every row, quote the rows that carry the story back to them in your answer, and never contradict a number they gave you without saying so explicitly.
Procedure:
1) Normalize before reading: which rows are PRICES (index futures, ETFs — green = up = good for holders) and which are YIELDS (green = yield up = bond price DOWN)? Say the flip out loud once when it matters — it is the most common misread on any rates screen.
2) Futures vs cash: an ES/NQ/YM row is the futures print (can include overnight); small basis vs the cash index is normal. A second faint line under a quote is usually the extended-hours print — read it as after-hours, not a double move.
3) Sort their rows into the packet's frame: equities legs, curve legs by tenor, the odd one out. The odd row — the one that doesn't fit the first story — is usually the analytical prize; hunt it deliberately.
4) Fill only the gaps that change the read (a missing oil print on an inflation-shaped day; breakevens when the long end is moving) with your own reads — get_quote for singles, the packet TAPE for the rest. Their screen first, your fills second, clearly separated.
5) Scale check every derived claim: for a hypothetical modified duration of 16 and a parallel +13bp yield move, the first-order estimate is -16 × 0.0013 = -2.08%. A -1.65% screen return differs by 0.43 percentage points; do not claim exact agreement. Check dated duration, the relevant curve move, holdings, convexity and carry before interpreting the residual.
Invalidation of this playbook itself: a screenshot of one ticker's chart is the technician's job (chart protocol), not a tape read — don't force a macro story onto a single-name picture.
Worked shape: "Your screen shows short yields down, long yields up and a bond fund down -1.65%. Long bonds are falling, but the hypothetical 16-duration/+13bp estimate is -2.08%, not the same return. Check the fund's actual dated exposure and market timestamps; this shape suggests hypotheses, not a proven inflation-shock cause."
