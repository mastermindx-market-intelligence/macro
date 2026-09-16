---
key: SIGNAL-LAB-REVAMP
title: 'Signal Lab: reliable discovery, evaluation and maturation'
objective: Make the existing research pipeline generate bounded economic hypotheses,
  evaluate them on correct clocks, and advance only supported evidence through visible
  experiment review; prove the production path without manufacturing alpha or a duplicate
  runtime.
status: active
program: research-factory
repos:
- macro
- mastermind
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
waves:
- id: W1
  title: Target-price-clock evaluator correction
  status: in_progress
  next_action: Publish the verified candidate, conclude CI and independent numerical
    review, then obtain real-path production proof.
- id: W2
  title: Complete specification identity and benchmark semantics
  status: todo
  depends_on:
  - W1
- id: W3
  title: Executable experiment maturity and truthful admin states
  status: todo
  depends_on:
  - W1
- id: W4
  title: Web Pro research tools and bounded continuation
  status: todo
  depends_on:
  - W2
  - W3
- id: W5
  title: Controlled discovery and prospective evidence pilot
  status: todo
  depends_on:
  - W4
next_action: Review and publish the clock repair candidate on claude/signal-lab-clock-repair-20260915-sol-001;
  do not enable discovery or alter historical results before review and production
  proof.
owns_paths:
- engine/signal_foundry/harness.py
- tests/test_sf_clock_repair.py
- research/SIGNAL_LAB_CLOCK_REPAIR_2026-09-15.md
- research/evidence/signal-lab-clock-repair-20260915/**
decisions:
- DEC:SIGNAL-LAB-WEB-PRO-FIRST-REPAIR
discoveries:
- DSC:SIGNAL-FOUNDRY-MIXED-FREQUENCY-CLOCK
artifacts:
- research/SIGNAL_LAB_CLOCK_REPAIR_2026-09-15.md
- research/evidence/signal-lab-clock-repair-20260915/same-data-comparison.json
- research/evidence/signal-lab-clock-repair-20260915/verification.json
do_not_redo:
- Do not create a second research/job/identity/queue authority.
- Do not take over alert-trust PR 7173 or Alert Center V2 PR 7022.
- Do not call revised historical data a fresh holdout or point-in-time proof.
- Do not spend Workspace Agent/Codex provider quota for this research program without
  an explicit changed resource decision.
landmines:
- The corrected evaluator remains BUILT_NOT_PROVEN until accepted review and production-path
  evidence.
- Native-observation feature lags and legacy release/vintage semantics are preserved,
  not certified.
- A come-back date does not prove a numerical result exists.
---

# Signal Lab revamp

Created under the current live Chairman commission after a current-pin scan of all 69 existing workstreams found no owner for Signal Lab/Foundry paths. Parent is the existing research-factory program, not a new program or runtime. Source custody remains with this branch; this organizational record is not evidence of an Executive Job, worker lease, review pickup, or production acceptance.
