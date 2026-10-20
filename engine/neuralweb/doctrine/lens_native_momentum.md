---
id: lens_native_momentum
kind: lens
version: 1
title: Native momentum instruments
priority: 38
triggers:
  - "native[rsix/eng]"
  - "native[rsix/sig]"
  - "native[rsix/div]"
  - "native[rsix/mtf]"
  - "native[macdx/eng]"
  - "native[macdx/hist]"
  - "native[macdx/sig]"
  - "native[macdx/div]"
  - "native[macdx/mtf]"
  - RSI Ultimate
  - MACD Ultimate
  - 原生动量
---
NATIVE MOMENTUM — use the implementation's units, not textbook assumptions.
A routed lesson means the instrument is relevant, not that its output was observed. Read exact settings and a qualified numerical observation before stating a reading. Do not synthesize RSI/MACD values from configuration, color or a guide.
RSI Ultimate: distinguish the unsmoothed rsi-wave from rsi-smooth. The native engine's 65/35 event bands are not interchangeable with 30/50/70 pane guide rails. State which curve and threshold a claim uses. Source period and smoothing can be normalized by the kernel: requested values alone are not full effective-value proof.
MACD Ultimate: the native engine uses a trailing 250-bar normalization of fast-minus-slow MA and smooths that normalized curve for its signal. It is not the textbook raw price-denominated MACD; neither pane values nor native strengths are dollars, percentage returns or calibrated cross-security probabilities. Native default periods are not a reason to overwrite the user's current configuration. The displayed histogram can be clamped; saturation is not evidence that underlying changes stopped. HeatMap hue describes extremity and may oppose the reading's sign: do not infer slope/direction from color.
Equal fast/slow periods are degenerate; reversed periods change interpretation. Native period rounding means two requested decimal settings may produce identical computation. Do not claim two distinct experiments from different request hashes alone.
Divergence requires the actual pivot pair, confirmation timing and price/indicator direction. A pivot's plotted anchor is not when it became knowable. For MTF tables retain the aggregation/source basis and closed-bar qualification. Daily-only observations cannot classify a current intraday entry.
Explain conditionally: what the actual momentum evidence supports, where it conflicts with price structure, and what observation would change that assessment. Related transformations of the same closes are not independent confirmations. 人机一致：原始曲线与平滑线分开；事件阈值与参考线分开；颜色、强度与胜率分开。
