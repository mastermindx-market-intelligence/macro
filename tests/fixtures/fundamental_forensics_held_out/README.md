# FIF held-out isolation root

This directory is the only held-out root for Financial Intelligence Fabric
pack evaluation (`protocol_id` `fif-q0-quality-protocol/v1`).

Builders, production providers, query services, and pack code never read this
tree. Independent Q1 evaluation is the only reader after builders freeze.

Labels arrive later, under `packs/PKxx/labels/`, together with a `_SEALED`
marker file. Until that seal exists, this root holds no label JSON and no
SEC packages.

The AAPL golden pair under `tests/fixtures/fundamental_forensics/` is
calibration. It is never copied here and never counted as held-out proof.

Protocol: `research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.md`
Manifest: `research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json`

## Packages (2026-10-20)

Held-out filing packages now exist as digest-only manifests, selected by
`held_out_contract.json` in this directory (`contract_id` `fif-held-out-v1`).
Layout: `packages/<cik10>/<accession>/package_manifest.json` plus a per-CIK
`capture_index.json` and `request_log.jsonl` written by
`scripts/capture_fif_issuer_packages.py --out-root`. Filing bytes are staged
outside git at `~/lanes/stage/fif-heldout` on host `mastermind-pc` (lane
packet named `ubuntu1`; the stage lives on the host that ran the capture) and
reach git only as sha256 digests in the manifests.

## Labels (2026-10-21)

Label JSON files and their `_SEALED` markers live under `packs/PKxx/labels/`.
They are written only by independent labeler lanes (`fif-heldout-lab-<x>-20261021`),
never by pack lanes, build lanes or the integrating seat, and the seat merges
them unchanged. A seal's `sealed_by` line carries the lane id named in that
lane's packet; the admitted run that performed the work is recorded in the
pull request that merged the labels. The isolation test requires a seal beside
every label file. Packs without a `labels/` directory are not yet labelled.
