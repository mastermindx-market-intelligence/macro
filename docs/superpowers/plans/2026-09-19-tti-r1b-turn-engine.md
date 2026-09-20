# TTI R1-B Turn Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the frozen R1-B v4 causal fresh-low/exhaustion/reclaim-versus-continuation episode extractor without reading market outcomes or mutating the TrialLedger.

**Architecture:** Extend the existing pure `engine/entry_radar/tactical_research.py` research owner on a branch stacked from exact R1-A head `b73f1c7...`. Operate only on caller-supplied five-minute frames and prior-only ATR/close inputs. Keep selector fires, confirmation race, delayed price references, and control-census identity deterministic and separate from outcomes/event emission.

**Tech Stack:** Python, pandas, numpy, pytest.

**Spec:** Macro #7274 `research/species/TTI_R1B_V4_PREREG.md` + `research/species/tti_r1b/config_v4.json` frozen at `4db8d0ed...`.

## Global Constraints
- No market-data outcome read and no `data/trial_ledger.jsonl` mutation in this slice.
- Five-minute normal-RTH candidate decisions only; candidate-time evidence must be causal and positive-volume where required.
- One full five-minute processing-latency bar after decision/confirmation.
- First qualifying event per selector/session; no global first-event gate.
- Candidate-anchor LOD and episode-low LOD remain separate downstream labels; this slice only preserves both anchors.
- No rank, alert, live event, sizing, option, or trade authority.

## Review Focus
- Future malformed/duplicate rows must not erase an earlier lawful base/forming fire.
- Earlier unqualified anchors must not consume a later event for another/that selector.
- Zero-volume or missing confirmation bars must not become an implicit expiration/reclaim.
- Confirmation and processing latency must not backpaint entry onto the candidate/confirmation bar.
- Control census membership must not depend on future selector labels.

### Task 1: Synthetic causal episode extractor
**Files:** modify `engine/entry_radar/tactical_research.py`; modify `tests/test_tactical_research.py`.
- [ ] Add RED tests for strict fresh-low, forming exhaustion, equality/volume refusal, reclaim/continuation/expiry race, and delayed entry.
- [ ] Run only new tests and verify failures are feature-absence failures.
- [ ] Implement minimal pure candidate/race/selector functions.
- [ ] Run new tests green.

### Task 2: Identity and mutation hardening
**Files:** same two files.
- [ ] Add RED tests for per-selector uniqueness, later qualifying anchor survival, shared-anchor selectors, future mutation/duplicate isolation, and bin-local BASE control census.
- [ ] Implement minimal hardening without whole-frame lookahead validation.
- [ ] Run focused and full tactical research tests.

### Task 3: Verify stack and publish bounded carrier
- [ ] Run full Live Entry Radar test step, compileall, and `git diff --check`.
- [ ] Verify no TrialLedger/config/outcome file changed.
- [ ] Commit/push branch and open a stacked draft PR whose base is the R1-A branch.
- [ ] Keep empirical runner/registration/outcomes explicitly held until v4 review and canonical registration gate are satisfied.
