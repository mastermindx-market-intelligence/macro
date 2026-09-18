# TTI R1-B status — frozen design, no outcomes

Frozen prereg/config commit: `0c54e10e20c43827802d3d829505f74f57f8eb5f`. Pickup base: `2f1eeaecd2a526853aa5e3fd4a102395380bd00c`.

Prereg SHA256: `7658e7695cf7ef5282478cc81f55422fc506789e4b270d89ea2e9ae14d26c118`. Config SHA256: `b4cb8b474bb0b3c77f2847e8ef0227c03d0071d360fa2ea398f30c54fbc595d2`. The selector × horizon × cost grid is **60 cells** and is **not registered or run**. `data/trial_ledger.jsonl` was not modified by this freeze.

R1-B is long-side exhaustion/reclaim versus continuation research only. Primary selector: `EXHAUSTION_RECLAIM`; opposing control: `CONTINUATION_RISK`. The frozen design uses causal five-minute RTH decisions, explicit reclaim/continuation race, delayed price-reference entries, local-turn and LOD labels kept separate, deterministic matched controls, and a no-live-promotion ceiling.

Current dependency: R1-A shared TrialLedger/source carrier Macro #7270 must clear its own current-head source/CI gate before R1-B trial registration or implementation writes touch shared research paths. The R1-B prereg carrier is docs/config only and may proceed independently through review.

Do not open R1-B outcome columns, append its trial rows, alter thresholds, add options/news/regime/sector rescue filters, or infer short/HOD symmetry from this freeze. Top-side work must separately reconcile `WS:TOP-ANATOMY`.
