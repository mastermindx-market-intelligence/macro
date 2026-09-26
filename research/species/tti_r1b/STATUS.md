# TTI R1-B — v4 registered; empirical outcome consumer next

Frozen scientific specification: v4 at `4db8d0edc63997f7f7944c3b35ac04709461b810`.
Prereg SHA256 `a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3`.
Config SHA256 `24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19`.
V1-v3 remain DO_NOT_RUN. No frozen scientific bytes or thresholds changed.

## Accepted predecessors

Terminal D0 #601 received independent APPROVED review on immutable head `c0f36cb16fadd190ad747fc47a28405d9ec0fca4` and squash-merged as `f4bc91827a075748dc5c97c889888ae2ee643a87`.

R1-A #7270 received independent APPROVED source/research review on immutable head `b73f1c7bf13aa386fb11c4fdce762b999e91eae7` after TrialLedger custody checks, a 265-pass causal/registration suite and an independent captured-input rerun whose feature panel and outcomes were byte-identical to canonical run-003. R1-A protected-main merge remains separately blocked by required `ci-gate` because of lane-external HK/Canada stock-dashboard browser-receipt hash drift. DEC:TERMINAL-TACTICAL-R1B-STACKED-RESEARCH-ADMISSION permits corrected-history R1-B research on a branch stacked on that accepted R1-A head without bypassing protected-main release.

The accepted R1-A head was merged into this research branch at `094680febbcd883dd18616c4cb13fbe3c8257997`; frozen v4 prereg/config hashes remained unchanged.

## Built mechanics

`engine/entry_radar/tactical_exhaustion.py` implements causal five-minute candidate/confirmation construction and exact frozen matched-control selection. Candidate, confirmation, latency-entry, candidate-low and episode-low identities remain separate.

`build_prior_normalization` now derives frozen prior-only ATR20 and beta from caller-supplied daily inputs. ATR requires the complete scheduled prior window and beta uses adjacent paired prior stock/QQQ returns; current-session daily values are excluded. The synthetic preview consumes those derived prior inputs instead of a hard-coded ATR. Full Radar regression after this slice: **1,537 passed / 2 skipped**.

## Trial registration

The complete frozen v4 grid was registered **before any R1-B market-outcome read** through the canonical `engine.trial_ledger.TrialLedger.log_grid` writer at commit `350c57e1c6aab6e064c022a483389c905d2b7ad0`.

- ledger rows: **1,760 → 1,820**
- R1-A rows preserved: **84**
- R1-B rows added: **60 / 60**
- R1-B unique selector × horizon × cost keys: **60 / 60**
- pre-ledger SHA256: `beb48ca70d10c81e9c149afea5dbdbc31614bfe2489f2558e8c45d8fb112a794`
- post-ledger SHA256: `904a0799c80cc2ff3629e415e8460d77b2972556b5ef32327de700de496a2f80`
- R1-B grid SHA256: `151c0cb20af85537287413b4ecdeaf2ccad18232ed4eb0a20091cbd46cdb6b17`
- prefix preserved: **true**
- canonical TrialLedger tests after append: **23 passed**

Machine receipt: `research/species/tti_r1b/REGISTRATION_RECEIPT_V4.json`.

## Authority and non-goals

Registration is research accounting only. No R1-B market outcome has yet been opened at this status boundary. No live event, rank, alert, sizing, options expression, order path, production scanner, new minute store or scientific registry is authorized.

R1-A and R1-B protected-main merge/release remain separate from corrected-history research. No failed CI check is waived.

## Next dependency

Build the empirical R1-B outcome/LOD/matched-control consumer from the frozen v4 contract and already-qualified D0 inputs. It must refuse execution unless the 60-cell registration receipt and exact frozen hashes match. Then run the corrected-history study once, preserve every negative/censored/no-control cell, publish the aggregate result, and adjudicate only whether `EXHAUSTION_RECLAIM` qualifies for a later **prospective/shadow preregistration**. It cannot become live authority from this batch.
