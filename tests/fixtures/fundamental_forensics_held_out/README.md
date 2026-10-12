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
