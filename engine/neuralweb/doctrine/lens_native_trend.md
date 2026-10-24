---
id: lens_native_trend
kind: lens
version: 1
title: Native trend and adaptive settings
priority: 36
triggers:
  - "native[trend/te]"
  - "native[trend/cp]"
  - "native[trend/fb]"
  - "native[trend/vb]"
  - "native[trend/dash]"
  - Trend Engine
  - Auto-Optimize
  - 原生趋势
---
NATIVE TREND — configuration, current signal and historical evidence are separate.
Identify the enabled Trend modules and exact settings. Do not infer a rail, flip or direction merely because a module is attached, or mistake a configured sensitivity for an observed market condition.
The native Trend Engine's Auto-Optimize option can select a sensitivity from a trailing optimization window and recompute the supplied history; the guide warns that past signals can change. Preserve the user's display choice, but do not treat that output as frozen historical ground truth. Research initially uses explicitly fixed settings; adaptive research needs separately qualified walk-forward decisions frozen at each decision time under the existing evaluation owner.
A current rail or flip is not a universal entry rule. Relate a qualified observation to the user's working horizon, price location, trigger, invalidation and next obstacle; expose higher-timeframe conflict without an unconditional weekly veto. Several Trend companion modules can share the same source prices and are not independent probability votes.
Use additive setting edits only when the client advertises support, drawing parameter names/types from native_parameters rather than guessing. After changing a setting, re-read the configuration and obtain a fresh qualified observation before explaining its numerical effect. An application ACK does not prove completed recomputation, rendered pixels, or improved forecasting. 自动优化不是无前视历史标签；配置修改成功不是预测能力证明。
