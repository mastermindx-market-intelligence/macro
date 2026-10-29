---
key: RIC-WRAPPER-DATE-IS-NOT-JOINT-EVIDENCE-FRESHNESS
claim: >
  At Macro commit 1850547c80e92191e6b195acce446c912de7f5e3,
  rates_inflation_command.build_board derives its wrapper asof from the newest
  selected fed-path and transmission dates, or the current date when absent;
  that wrapper does not certify the freshness of all joined policy, commodity,
  market-state and release inputs.
falsifier: >
  Inspect engine/rates_inflation_command.py::build_board at the cited immutable
  commit; this claim is false if the final asof is instead a validated common
  availability cutoff for every contributing input. A later corrected producer
  should supersede this discovery with exact source and consumer proof.
so_what: >
  The integrated regime-outlook consumer must preserve and admit each source's
  own clocks and coverage. Do not use a fresh rates_command wrapper or build
  timestamp as evidence that old policy or missing labor data are current.
kind: architecture
verified_at: 2026-09-12
verified_by: >
  GitHub.fetch_file of engine/rates_inflation_command.py at
  1850547c80e92191e6b195acce446c912de7f5e3, lines1190-1530:
  build_board input reads, candidate_dates, max(candidate_dates), wall-clock
  fallback and pre_artifact construction. Static source evidence only.
scope:
  - rates-inflation-command
  - WS:RATES-INFLATION-COMMAND
  - engine/rates_inflation_command.py
  - research/macro_regime_intelligence/**
confidence: verified
---

# Why this changes the first vertical

A multi-source future-path analysis must distinguish a recently rebuilt container
from recently observed evidence. Policy intelligence has its own `as_of` and
staleness disclosure; the market and economic sources have different cadences.
The existing wrapper can be useful for publication, but must not be promoted
into an undocumented common information set.

The proposed additive `regime_outlook` projection should retain valid partial
analysis and explicitly identify stale, unknown, future or incompatible inputs.
Missing evidence does not count as a condition being false, nor as calm.

This finding does not prove that every existing display hides source ages, that
any live forecast was wrong, or that a production incident was reproduced. No
engine execution or data mutation was performed for this discovery. Existing
consumers and scoring authority are unchanged by the records-only carrier.

The related design is `research/macro_regime_intelligence/PROGRAM_ARCHITECTURE_2026-09-12.md`.
