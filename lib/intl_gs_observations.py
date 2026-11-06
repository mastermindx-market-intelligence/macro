"""Turn the incumbent intl qualification chain into Wave 1 observations.

INTL-GS-W2F-X (X2): the exact incumbent assembly of
``tests/test_intl_global_observation_adapter.py::_chain`` — two
``engine.intl_inputs.source_snapshot`` calls, one
``engine.intl_performance_records.build_return_records`` over the admitted
frame, one ``qualify_return_records`` per supported basis — feeding
``lib.intl_global_observation_adapter.observations_from_qualification`` for
local, usd_unhedged and usd_hedged. The hedged basis receives the
usd_unhedged qualification output, so every hedged observation abstains
``basis_unsupported`` (adapter contract; no hedged observation ever borrows an
unhedged incumbent).

This module computes no value of its own, copies no Wave 1 constant and adds
no second qualifier: the incumbent chain stays the single authority. When
``publication_inputs`` is None the set is withheld — empty qualification, no
source evidence, and the adapter (never this module) assigns the abstain
reasons.
"""
from __future__ import annotations

import json
from pathlib import Path

from engine import intl_inputs
from engine.intl_global_observation import CONTRACT_VERSION
from engine.intl_performance_records import build_return_records
from lib.intl_global_observation_adapter import observations_from_qualification

BASES = ("local", "usd_unhedged", "usd_hedged")
_WITHHELD_REFERENCE = "intl-supplied-close:withheld"


def _run_status_source(data_root) -> dict | None:
    """run_status.json sources.intl_prices, or None on any read/shape error."""
    try:
        document = json.loads((Path(data_root) / "run_status.json").read_text(encoding="utf-8"))
        return document["sources"]["intl_prices"]
    except (OSError, KeyError, TypeError, ValueError):
        return None


def build_observation_set(closes, *, publication_inputs, evaluated_at, data_root,
                          rights) -> dict:
    """One observation set over the incumbent chain; see the module docstring."""
    run_status_source = _run_status_source(data_root)
    if publication_inputs is None:
        source_reference = None
        records = build_return_records(
            closes, market_ids=list(intl_inputs.countries()),
            source_reference=_WITHHELD_REFERENCE)
        qualifications = {"local": {"qualifications": []},
                          "usd_unhedged": {"qualifications": []}}
        source_evidence: list = []
        status = "withheld"
    else:
        pending = intl_inputs.source_snapshot(
            closes, source_reference="intl-supplied-close:pending",
            adjustment_bases=publication_inputs["adjustment_bases"])
        source_reference = "intl-supplied-close:sha256:" + pending["content_sha256"]
        snapshot = intl_inputs.source_snapshot(
            closes, source_reference=source_reference,
            adjustment_bases=publication_inputs["adjustment_bases"])
        records = build_return_records(
            closes, market_ids=list(intl_inputs.countries()),
            source_reference=source_reference)
        qualifications = {
            basis: intl_inputs.qualify_return_records(
                records, snapshot=snapshot,
                source_evidence=publication_inputs["source_evidence"],
                disclosure_decisions=publication_inputs["disclosure_decisions"],
                policy_id=publication_inputs["policy_id"], currency_basis=basis)
            for basis in ("local", "usd_unhedged")}
        source_evidence = publication_inputs["source_evidence"]
        status = "admitted"
    bases = {}
    for basis in BASES:
        qualification = (qualifications["usd_unhedged"] if basis == "usd_hedged"
                         else qualifications[basis])
        bases[basis] = observations_from_qualification(
            records, qualification, closes=closes,
            source_evidence=source_evidence, run_status_source=run_status_source,
            evaluated_at=evaluated_at, rights=rights, currency_basis=basis)
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "source_reference": source_reference,
        "bases": bases,
    }
