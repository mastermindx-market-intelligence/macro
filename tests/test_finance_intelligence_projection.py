"""Tests for ``engine.sector_intelligence.finance_projection``.

All numbers, issuers and source URIs in this module are SYNTHETIC. No value
is copied from the live research carrier or from the schema fixture.
"""

from __future__ import annotations

import builtins
import collections
import copy
import dataclasses
import datetime as _dt
import functools
import hashlib
import json
import os
import re
import socket as _socket
import subprocess
import sys
import time as _time
from pathlib import Path
from typing import Any

import pytest

from engine.sector_intelligence.contracts import ContractRegistry, ContractValidationError, validate_contract
from engine.sector_intelligence.finance_projection import (
    FinanceOwnerInputs,
    _FINANCE_SLICE_IDS,
    _METRIC_FIELDS,
    _build_primary_metric,
    _has_forbidden_key,
    _owner_key,
    _owner_refs,
    _owner_text,
    _withhold_unevidenced,
    compose_finance_projection,
)


CONTRACT_ID = "finance_intelligence_read_model.v1"

_FIRST_VERTICAL_SLICE_IDS: tuple[str, ...] = (
    "card_networks",
    "merchant_acquiring_processing",
    "issuer_processing",
    "exchanges_trading_venues",
    "custody_asset_servicing",
    "market_reference_data",
    "ratings_credit_information",
    "indices_benchmarks_etf_plumbing",
)


# ---------------------------------------------------------------------------
# Synthetic input factory
# ---------------------------------------------------------------------------


def _today() -> _dt.datetime:
    return _dt.datetime(2026, 9, 24, 0, 0, 0)


def _knowledge_cutoff() -> _dt.datetime:
    return _dt.datetime(2026, 9, 24, 0, 0, 0)


def _base_slice_catalog() -> list[dict]:
    return [
        {
            "slice_id": sid,
            "domain": _domain_for(sid),
            "name": sid.replace("_", " ").title(),
            "name_zh": sid.replace("_", " "),
            "price_basket_posture": "SEMANTIC_ONLY",
        }
        for sid in _FIRST_VERTICAL_SLICE_IDS
    ]


def _domain_for(slice_id: str) -> str:
    return {
        "card_networks": "payments",
        "merchant_acquiring_processing": "payments",
        "issuer_processing": "payments",
        "exchanges_trading_venues": "capital_markets",
        "custody_asset_servicing": "capital_markets",
        "market_reference_data": "capital_markets",
        "ratings_credit_information": "capital_markets",
        "indices_benchmarks_etf_plumbing": "capital_markets",
    }.get(slice_id, "capital_markets")


def _source_payload(
    *,
    publisher: str = "Synthetic Publisher",
    source_family: str = "synthetic_research",
    observed_at: str = "2026-09-20",
    published_at: str = "2026-09-19",
) -> dict:
    return {
        "publisher": publisher,
        "source_family": source_family,
        "source_uri": "https://example.invalid/synthetic-record",
        "locator": "synthetic-locator",
        "published_at": published_at,
        "published_at_grain": "DAY",
        "observed_at": observed_at,
        "retained_at": "2026-09-21",
        "retention_ref": "synthetic-retention",
        "native_digest": None,
    }


def _metric_payload(
    *,
    native_name: str = "synthetic_native",
    family: str = "synthetic_family",
    value: float = 1.0,
    unit: str = "USD",
    measurement_class: str = "REVENUE",
    numerator: str | None = None,
    denominator: str | None = None,
) -> dict:
    return {
        "native_metric_name": native_name,
        "normalized_metric_family": family,
        "value": value,
        "unit": unit,
        "currency": "USD",
        "period_start": "2026-01-01",
        "period_end": "2026-09-20",
        "measurement_class": measurement_class,
        "numerator": numerator,
        "denominator": denominator,
        "gross_net_basis": "NET",
        "average_end": "AVERAGE",
        "reported_derived_estimated": "REPORTED",
    }


def _schema_strict_source_record(
    *,
    slice_id: str,
    metric_class: str = "REVENUE",
    source_family: str = "synthetic_research",
    record_id: str | None = None,
    identity_state: str = "IDENTITY_VALIDATED",
    rights_state: str | None = None,
    excerpt: str | None = "Synthetic excerpt text.",
    observed_at: str = "2026-09-20",
    value: float = 1.0,
    numerator: str | None = None,
    denominator: str | None = None,
) -> dict:
    rec_id = record_id or ("src-" + slice_id + "-" + source_family)
    return {
        "record_id": rec_id,
        "source": _source_payload(source_family=source_family, observed_at=observed_at),
        "business_scope": slice_id,
        "metric": _metric_payload(
            value=value,
            unit="USD",
            measurement_class=metric_class,
            numerator=numerator,
            denominator=denominator,
        ),
        "observation": {
            "value": value,
            "value_high": None,
            "period_start": "2026-01-01",
            "period_end": "2026-09-20",
            "reported_derived_estimated": "REPORTED",
            "precision": "approximate",
        },
        "temporal": {"business_valid_from": "2026-01-01", "business_valid_to": None},
        "limitations": {
            "establishes": "Synthetic evidence establishes an observation.",
            "does_not_establish": "It does not establish a real-world outcome.",
            "coverage": "Synthetic coverage only.",
            "source_dependence": "Depends on the synthetic source.",
            "expiry_trigger": "Synthetic expiry trigger is the document revision.",
        },
        "identity_state": identity_state,
        "rights_state": rights_state,
        "statement_mode": "REPORTED_FACT",
        "correction": {"predecessor_record_id": None, "reason": None},
        "evidence_ref": rec_id,
        "excerpt": excerpt,
    }


def _default_operating_record(
    *,
    slice_id: str,
    metric_class: str = "REVENUE",
    direction: str | None = "UP",
    issuer: str | None = None,
    ticker: str | None = None,
    observed_at: str = "2026-09-20",
    source_family: str = "synthetic_research",
    identity_state: str = "IDENTITY_VALIDATED",
    rights_state: str | None = None,
    excerpt: str | None = "Synthetic excerpt text.",
    value: float = 1.0,
    numerator: str | None = None,
    denominator: str | None = None,
) -> dict:
    """Builder for tests that pass issuer / ticker / direction.

    The schema-strict fields are those accepted by ``_schema_strict_source_record``.
    Issuer / ticker / direction / observed_at are passed through as private
    fields (``_ticker_hint`` / ``_issuer_label`` / ``_direction`` /
    ``_observed_at_override``) that the composer reads BEFORE stripping the
    document to schema-strict shape.
    """
    rec = _schema_strict_source_record(
        slice_id=slice_id,
        metric_class=metric_class,
        source_family=source_family,
        identity_state=identity_state,
        rights_state=rights_state,
        excerpt=excerpt,
        observed_at=observed_at,
        value=value,
        numerator=numerator,
        denominator=denominator,
    )
    if ticker is not None:
        rec["_ticker_hint"] = ticker
    if issuer is not None:
        rec["_issuer_label"] = issuer
    if direction is not None:
        rec["_direction"] = direction
    rec["_observed_at_override"] = observed_at
    return rec


def _make_inputs(
    *,
    sector_dossier: dict | None = None,
    expectation_rows: dict[str, list[dict]] | None = None,
    market_rows: dict[str, list[dict]] | None = None,
    identity_bindings: dict | None = None,
    source_records: list[dict] | None = None,
    regime_breaks: list[dict] | None = None,
    macro_context: dict | None = None,
    basket_context: dict | None = None,
    financial_packets: dict | None = None,
    theme_evidence: list[dict] | None = None,
    rights_snapshot: dict[str, str] | None = None,
) -> FinanceOwnerInputs:
    return FinanceOwnerInputs(
        sector_dossier=sector_dossier,
        theme_evidence=theme_evidence or [],
        financial_packets=financial_packets or {},
        expectation_observations=expectation_rows or {},
        market_observations=market_rows or {},
        basket_context=basket_context or {},
        macro_context=macro_context or {},
        identity_bindings=identity_bindings or {},
        source_records=source_records or [],
        regime_breaks=regime_breaks or [],
        slice_catalog=_base_slice_catalog(),
        rights_snapshot=rights_snapshot
        or {"synthetic_research": "direct_display_ok"},
    )


def _default_8slice_inputs(**overrides) -> FinanceOwnerInputs:
    """Build a minimal-but-covering 8 first-vertical-slice input factory."""
    expectation_rows: dict[str, list[dict]] = overrides.pop("expectation_rows", {}) or {}
    market_rows: dict[str, list[dict]] = overrides.pop("market_rows", {}) or {}
    identity_bindings = overrides.pop("identity_bindings", None) or {
        "SYN1": {
            "state": "IDENTITY_VALIDATED",
            "company_node_id": "company:synthetic-network",
            "security_ref": "security:syn1",
            "listing_note": "Synthetic listing note.",
        },
        "EXAMPLE": {
            "state": "IDENTITY_VALIDATED",
            "company_node_id": "company:synthetic-market-infra",
            "security_ref": "security:example",
            "listing_note": "Synthetic listing note.",
        },
    }
    # financial_packets are keyed by issuer_label and carry per-issuer
    # operating/valuation cells. Each cell ties to one slice_id and
    # carries explicit direction on the observation row (NEVER on the
    # metric — direction lives outside the schema-strict source records).
    financial_packets = overrides.pop("financial_packets", None) or {
        "SYN1": {
            "operating": {
                "cells": [
                    {
                        "slice_id": "card_networks",
                        "role": "DIRECT_PURE_OR_HIGH_EXPOSURE",
                        "basis": "SEGMENT_REVENUE",
                        "numerator": "Synthetic card-network revenue",
                        "denominator": "Synthetic total company revenue",
                        "value": 0.78,
                        "unit": "ratio of revenues",
                        "materiality": "MATERIAL",
                        "retained_risk": "Synthetic retained risk for SYN1 in card networks.",
                        "evidence_date": "2026-09-20",
                        "evidence_refs": ["src-card_networks-synthetic_research"],
                    },
                ],
            },
            "valuation": {"cells": []},
        },
        "EXAMPLE": {
            "operating": {
                "cells": [
                    {
                        "slice_id": "merchant_acquiring_processing",
                        "role": "ENABLER_OR_TOLL_COLLECTOR",
                        "basis": "TRANSACTION_VOLUME",
                        "numerator": "Synthetic merchant transactions",
                        "denominator": "All synthetic merchant transactions in the stated period",
                        "value": 0.42,
                        "unit": "synthetic transactions",
                        "materiality": "PARTIAL",
                        "retained_risk": "Synthetic processing risk remains with the platform.",
                        "evidence_date": "2026-09-20",
                        "evidence_refs": ["src-merchant_acquiring_processing-synthetic_research"],
                    },
                    {
                        "slice_id": "exchanges_trading_venues",
                        "role": "DIRECT_PURE_OR_HIGH_EXPOSURE",
                        "basis": "SEGMENT_REVENUE",
                        "numerator": "Synthetic exchange revenue",
                        "denominator": "Synthetic total company revenue",
                        "value": 0.73,
                        "unit": "ratio of revenues",
                        "materiality": "MATERIAL",
                        "retained_risk": "Synthetic volume dependence remains.",
                        "evidence_date": "2026-09-20",
                        "evidence_refs": ["src-exchanges_trading_venues-synthetic_research"],
                    },
                ],
            },
            "valuation": {"cells": []},
        },
    }
    source_records: list[dict] = overrides.pop("source_records", None)
    if source_records is None:
        source_records = [
            _schema_strict_source_record(slice_id="card_networks"),
            _schema_strict_source_record(slice_id="merchant_acquiring_processing"),
            _schema_strict_source_record(slice_id="issuer_processing"),
            _schema_strict_source_record(slice_id="exchanges_trading_venues"),
            _schema_strict_source_record(slice_id="custody_asset_servicing"),
            _schema_strict_source_record(slice_id="market_reference_data"),
            _schema_strict_source_record(slice_id="ratings_credit_information"),
            _schema_strict_source_record(slice_id="indices_benchmarks_etf_plumbing"),
        ]
    macro_context = overrides.pop("macro_context", None) or {}
    return _make_inputs(
        expectation_rows=expectation_rows,
        market_rows=market_rows,
        identity_bindings=identity_bindings,
        financial_packets=financial_packets,
        source_records=source_records,
        macro_context=macro_context,
        **overrides,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_52_slices_emitted() -> None:
    inputs = _default_8slice_inputs()
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert len(document["slices"]) == 52
    emitted = {sl["slice_id"] for sl in document["slices"]}
    assert emitted == set(_FINANCE_SLICE_IDS)


def test_output_validates_contract() -> None:
    inputs = _default_8slice_inputs()
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    validate_contract(CONTRACT_ID, document)


def test_no_forbidden_keys() -> None:
    inputs = _default_8slice_inputs()
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )

    forbidden = re.compile(r"(^|_)(score|rank|attractiveness|composite)(_|$)", re.IGNORECASE)
    authority_block = document["authority_caps"]

    def walk(node: object) -> list[str]:
        # The pattern carries its own underscore boundaries, so it must be
        # searched: under fullmatch it matches only a bare word, and
        # peer_rank passes.
        found: list[str] = []
        if isinstance(node, dict):
            for key, child in node.items():
                if not (key == "rank" and node is authority_block) and forbidden.search(key):
                    found.append(key)
                found += walk(child)
        elif isinstance(node, list):
            for child in node:
                found += walk(child)
        return found

    # Positive control: a clean document cannot tell a live walk from a dead one.
    assert walk({"slices": [{"peer_rank": 1, "composite_score": 2, "ranking": 3}]}) == [
        "peer_rank",
        "composite_score",
    ]
    assert walk(document) == []
    assert document["authority_caps"]["rank"] is False


def test_missing_consensus_stays_missing() -> None:
    """Card networks has no dated consensus rows; plane state stays MISSING."""
    inputs = _default_8slice_inputs(
        expectation_rows={"card_networks": []},
    )
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    card = next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")
    assert card["rerating"]["expectations"]["state"] == "MISSING"
    assert card["rerating"]["expectations"]["history"]["state"] == "NO_HISTORICAL_CONSENSUS"
    assert card["rerating"]["expectations"]["history"]["observations"] == []
    # valuation.state must NOT be IMPUTED — the closed schema enum rejects it.
    assert card["rerating"]["valuation"]["state"] != "IMPUTED"
    # Imputed is not a member of the schema's plane_state enum.
    validate_contract(CONTRACT_ID, document)


def test_guidance_is_not_consensus() -> None:
    guidance_rows = [
        {
            "as_of": "2026-09-15",
            "source": "src-guidance-001",
            "metric": "guidance:net_revenue_yoy",
            "value": 0.05,
            "unit": "ratio",
        }
    ]
    inputs = _default_8slice_inputs(
        expectation_rows={"card_networks": guidance_rows},
    )
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    card = next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")
    history = card["rerating"]["expectations"]["history"]
    assert history["state"] == "MANAGEMENT_GUIDANCE_ONLY"
    assert all(obs["metric"].startswith("guidance:") for obs in history["observations"])
    # The plane's primary_metric stays None for guidance-only — no consensus
    # value is ever invented from management guidance.
    assert card["rerating"]["expectations"]["primary_metric"] is None
    validate_contract(CONTRACT_ID, document)


def test_identity_unresolved_no_route() -> None:
    # Build a record whose ticker is not in identity_bindings.
    bad_record = _default_operating_record(slice_id="card_networks", ticker="GHOST")
    bad_record["identity_state"] = "IDENTITY_UNRESOLVED"
    inputs = _default_8slice_inputs(source_records=[bad_record])
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    rows = [row for row in document["company_exposures"] if row["ticker_hint"] == "GHOST"]
    assert rows, "expected a GHOST row"
    row = rows[0]
    assert row["identity"]["state"] == "IDENTITY_UNRESOLVED"
    assert row["company_route"]["href"] is None
    assert row["company_route"]["state"] == "IDENTITY_UNRESOLVED"
    validate_contract(CONTRACT_ID, document)


def test_regime_break_suppresses_deltas() -> None:
    regime = [
        {
            "slice_id": "card_networks",
            "plane": "operating",
            "from_basis": "GROSS",
            "to_basis": "NET",
            "effective_at": "2026-07-01",
            "bridge_available": False,
        }
    ]
    inputs = _default_8slice_inputs(regime_breaks=regime)
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    card = next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")
    assert card["rerating"]["operating"]["state"] == "REGIME_BREAK"
    assert card["rerating"]["operating"]["comparability_state"] == "REGIME_BREAK_NOT_COMPARABLE"
    forbidden = ("change_pct", "delta", "delta_pct", "_pp")

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                assert not any(tok in key for tok in forbidden), key
                walk(child)
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(card)
    validate_contract(CONTRACT_ID, document)


def test_adjusted_close_is_not_valuation_quote() -> None:
    market_rows = {
        "card_networks": [
            {
                "as_of": "2026-09-20",
                "price_basis": "ADJUSTED_HISTORICAL",
                "value": 100.0,
                "unit": "USD",
            }
        ]
    }
    inputs = _default_8slice_inputs(market_rows=market_rows)
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    card = next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")
    assert card["rerating"]["valuation"]["state"] == "PRICE_BASIS_UNQUALIFIED"
    assert card["rerating"]["price"]["state"] == "PRICE_BASIS_UNQUALIFIED"
    validate_contract(CONTRACT_ID, document)


def _valuation_of(document: dict[str, Any], slice_id: str) -> dict[str, Any]:
    return next(sl for sl in document["slices"] if sl["slice_id"] == slice_id)["rerating"]["valuation"]


def test_a_valuation_observation_anchors_only_the_slice_it_is_filed_under() -> None:
    """The conflict fixture files one P/E observation under card_networks.
    Give a second slice a qualified price basis of its own and it has a price
    but no valuation anchor: it must say so, not publish card_networks'
    multiple as its own reading. The anchor used to be the first valuation
    observation of any packet, whatever slice it was filed under."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    other = "ach_instant_b2b"
    assert not base.market_observations.get(other)
    market = dict(base.market_observations)
    market[other] = [dict(obs, source="synthetic-market-" + other) for obs in base.market_observations["card_networks"]]
    document = compose_finance_projection(
        dataclasses.replace(base, market_observations=market),
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    validate_contract(CONTRACT_ID, document)
    card = _valuation_of(document, "card_networks")
    assert card["state"] == "OBSERVED" and card["primary_metric"]["value"] == 18.0
    stray = _valuation_of(document, other)
    assert stray["state"] == "VALUATION_ANCHOR_UNAVAILABLE", stray
    assert stray["primary_metric"] is None and stray["clock"] is None


def test_the_valuation_plane_reads_its_slices_freshest_anchor() -> None:
    """card_networks' packet carries two valuation observations on two
    dates. The plane publishes the fresher, in either order. An untagged
    observation is company data and counts for the slice; one filed under
    another slice never does, however fresh. The plane used to publish
    whichever came first."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (anchor,) = packet["valuation"]["observations"]

    def observation(as_of: str, value: float, **tag: Any) -> dict[str, Any]:
        obs = {key: val for key, val in copy.deepcopy(anchor).items() if key != "slice_id"}
        obs.update(tag, as_of=as_of)
        obs["metric"] = dict(obs["metric"], value=value, period_end=as_of)
        return obs

    def anchor_values(*observations: dict[str, Any]) -> set[float]:
        values = set()
        for ordered in (observations, observations[::-1]):
            packets = {ticker: dict(packet, valuation=dict(packet["valuation"], observations=list(ordered)))}
            document = compose_finance_projection(
                dataclasses.replace(base, financial_packets=packets),
                generated_at=_today(),
                knowledge_cutoff=_knowledge_cutoff(),
            )
            validate_contract(CONTRACT_ID, document)
            values.add(_valuation_of(document, "card_networks")["primary_metric"]["value"])
        return values

    stale = observation("2026-06-30", 21.0, slice_id="card_networks")
    assert anchor_values(stale, observation("2026-09-20", 18.0, slice_id="card_networks")) == {18.0}
    assert anchor_values(stale, observation("2026-09-20", 17.0)) == {17.0}
    assert anchor_values(stale, observation("2026-09-23", 30.0, slice_id="ach_instant_b2b")) == {21.0}


def test_an_undated_valuation_observation_never_anchors() -> None:
    """An anchor publishes its date as the slice's information clock, which
    the contract requires, so an observation that carries no date cannot
    anchor. Beside a dated one it is passed over, in either order; alone it
    leaves the slice without an anchor, said in words. It used to refuse the
    whole document whenever it came first."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (anchor,) = packet["valuation"]["observations"]
    undated = {key: val for key, val in copy.deepcopy(anchor).items() if key not in ("as_of", "observed_at")}
    undated["metric"] = dict(undated["metric"], value=99.0)

    def valuation(*observations: dict[str, Any]) -> dict[str, Any]:
        packets = {ticker: dict(packet, valuation=dict(packet["valuation"], observations=list(observations)))}
        document = compose_finance_projection(
            dataclasses.replace(base, financial_packets=packets),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        return _valuation_of(document, "card_networks")

    for ordered in ((anchor, undated), (undated, anchor)):
        assert valuation(*ordered)["primary_metric"]["value"] == 18.0
    alone = valuation(undated)
    assert alone["state"] == "VALUATION_ANCHOR_UNAVAILABLE", alone
    assert alone["primary_metric"] is None and alone["clock"] is None


def _with_valuation_observations(base: FinanceOwnerInputs, *observations: dict[str, Any]) -> dict[str, Any]:
    """Compose the one-packet conflict fixture with its valuation observations
    replaced, in the order given, and return the validated document."""
    (ticker, packet), = base.financial_packets.items()
    packets = {ticker: dict(packet, valuation=dict(packet["valuation"], observations=list(observations)))}
    document = compose_finance_projection(
        dataclasses.replace(base, financial_packets=packets),
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    validate_contract(CONTRACT_ID, document)
    return document


def test_a_conflict_reads_the_direction_of_the_valuation_reading_the_plane_publishes() -> None:
    """EARNINGS_UP_P_E_DOWN compares the operating and valuation readings the
    slice publishes. Beside card_networks' anchor, add an older observation
    saying the opposite, dated by as_of, dated only by observed_at, or not
    dated at all. The plane publishes the anchor, in either order, and the
    conflict follows the anchor's direction: it fires when the published P/E
    is falling and stays silent when it is rising. When the anchor states no
    direction, the older observation says the P/E is falling and the
    conflict still stays silent: the reading the plane publishes does not
    say so. The conflict used to re-select its own valuation direction by
    as_of alone, so an observation the plane had passed over could decide
    it."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (anchor,) = packet["valuation"]["observations"]
    for published, opposite in (("DOWN", "UP"), ("UP", "DOWN"), (None, "DOWN")):
        reading = {key: val for key, val in copy.deepcopy(anchor).items() if key != "direction"}
        if published is not None:
            reading["direction"] = published
        undated = {key: val for key, val in copy.deepcopy(anchor).items() if key not in ("as_of", "observed_at")}
        undated.update(direction=opposite)
        undated["metric"] = dict(undated["metric"], value=21.0)
        for passed_over in (dict(undated, as_of="2026-09-10"), dict(undated, observed_at="2026-06-01"), undated):
            for ordered in ((reading, passed_over), (passed_over, reading)):
                document = _with_valuation_observations(base, *ordered)
                assert _valuation_of(document, "card_networks")["primary_metric"]["value"] == 18.0
                fired = [c["label"] for c in document["conflicts"]].count("EARNINGS_UP_P_E_DOWN")
                clock = (passed_over.get("as_of"), passed_over.get("observed_at"))
                assert fired == (1 if published == "DOWN" else 0), (published, clock, ordered[0] is reading)


def test_a_conflict_reads_the_direction_of_the_price_reading_the_plane_publishes() -> None:
    """PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN compares the price reading the
    slice publishes. Beside card_networks' rising qualified price, add a
    falling observation the plane passes over: a fresher one on an adjusted
    historical basis, which is never a qualified price, or an undated one,
    which the plane reads as the oldest. The plane publishes the rising
    price and the conflict fires, in either order. Then add a fresher
    qualified price that states no direction: the plane publishes it and
    the conflict stays silent, in either order, although the rising price
    it passed over says the price is up. The conflict used to re-select its
    own price direction from every market observation by as_of alone, so
    the observation the plane passed over decided it."""
    base = _conflict_inputs_for("PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN")
    (rising,) = base.market_observations["card_networks"]

    def published(*ordered: dict[str, Any]) -> tuple[Any, int]:
        market = dict(base.market_observations, card_networks=list(ordered))
        document = compose_finance_projection(
            dataclasses.replace(base, market_observations=market),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        price = next(s for s in document["slices"] if s["slice_id"] == "card_networks")["rerating"]["price"]
        assert price["state"] == "OBSERVED", price
        fired = [c["label"] for c in document["conflicts"]].count("PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN")
        return price["primary_metric"]["value"], fired

    adjusted = dict(rising, as_of="2026-09-22", price_basis="ADJUSTED_HISTORICAL", direction="DOWN", value=90.0)
    undated = {key: val for key, val in dict(rising, direction="DOWN", value=90.0).items() if key != "as_of"}
    for passed_over in (adjusted, undated):
        for ordered in ((rising, passed_over), (passed_over, rising)):
            assert published(*ordered) == (100.0, 1), (passed_over["price_basis"], "as_of" in passed_over, ordered[0] is rising)
    silent = {key: val for key, val in dict(rising, as_of="2026-09-23", value=95.0).items() if key != "direction"}
    for ordered in ((rising, silent), (silent, rising)):
        assert published(*ordered) == (95.0, 0), ordered[0] is rising


def test_only_an_absent_or_null_slice_tag_means_company_data() -> None:
    """A slice tag files an observation under that slice. Only an absent or
    null tag leaves it untagged, which is company data and reaches every
    slice. Retag card_networks' operating and valuation observations with a
    malformed tag and give ach_instant_b2b a price basis of its own: neither
    slice publishes them. A falsy malformed tag used to count as untagged, so
    the readings reached every slice; a truthy one already reached none."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    other = "ach_instant_b2b"
    market = dict(base.market_observations)
    market[other] = [dict(obs, source="synthetic-market-" + other) for obs in base.market_observations["card_networks"]]
    (ticker, packet), = base.financial_packets.items()

    def states(tag: Any) -> dict[str, tuple[str, str]]:
        retagged = {
            plane: dict(packet[plane], observations=[dict(copy.deepcopy(obs), slice_id=tag) for obs in packet[plane]["observations"]])
            for plane in ("operating", "valuation")
        }
        document = compose_finance_projection(
            dataclasses.replace(base, market_observations=market, financial_packets={ticker: dict(packet, **retagged)}),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        rerating = {s["slice_id"]: s["rerating"] for s in document["slices"]}
        return {sid: (rerating[sid]["operating"]["state"], rerating[sid]["valuation"]["state"]) for sid in ("card_networks", other)}

    untagged = states(None)
    assert untagged == {sid: ("OBSERVED", "OBSERVED") for sid in ("card_networks", other)}, untagged
    for malformed in ("", 0, False, [], {}, ["card_networks"]):
        found = states(malformed)
        assert found == {sid: ("MISSING", "VALUATION_ANCHOR_UNAVAILABLE") for sid in ("card_networks", other)}, (malformed, found)


def test_on_one_date_the_slice_tagged_valuation_observation_anchors() -> None:
    """Two valuation observations share a date: one the owner tags with
    card_networks and one left untagged (company data). The slice's own
    filing is the more specific, so it anchors, in either order. The anchor
    used to be whichever came last."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (anchor,) = packet["valuation"]["observations"]
    untagged = {key: val for key, val in copy.deepcopy(anchor).items() if key != "slice_id"}
    untagged["metric"] = dict(untagged["metric"], value=25.0)
    for ordered in ((anchor, untagged), (untagged, anchor)):
        document = _with_valuation_observations(base, *ordered)
        assert _valuation_of(document, "card_networks")["primary_metric"]["value"] == 18.0, ordered[0] is anchor


def _card_networks(document: dict[str, Any]) -> dict[str, Any]:
    return next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")


def _dated_by_observed_at(row: dict[str, Any]) -> dict[str, Any]:
    """``row`` with its as_of date carried by observed_at: the same date,
    the other clock."""
    moved = {key: value for key, value in row.items() if key != "as_of"}
    moved["observed_at"] = row["as_of"]
    return moved


def test_the_operating_plane_publishes_its_slices_freshest_dated_observation() -> None:
    """card_networks' operating observation reads UP on 2026-09-20 and draws
    the earnings-up / P/E-down conflict. Beside it, in either order, the
    plane passes over an observation reading DOWN that carries no date, and
    one dated earlier by observed_at alone: it publishes the dated, fresher
    reading and its clock, and the conflict is still drawn. Dated later by
    observed_at, the DOWN reading is the fresher, so it is published and the
    conflict is not drawn. Alone, an undated observation is still published,
    without a clock. The plane used to publish an undated observation over
    every dated one, and to count one dated only by observed_at as undated,
    so either one erased the conflict."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (reading,) = packet["operating"]["observations"]
    conflict = "conflict-card_networks-earnings-up-pe-down"

    def down(**dates: str) -> dict[str, Any]:
        obs = {key: val for key, val in copy.deepcopy(reading).items() if key != "as_of"}
        obs.update(dates, direction="DOWN")
        obs["metric"] = dict(obs["metric"], value=7.0)
        return obs

    def published(*observations: dict[str, Any]) -> set[tuple[Any, Any, bool]]:
        seen = set()
        for ordered in (observations, observations[::-1]):
            packets = {ticker: dict(packet, operating=dict(packet["operating"], observations=list(ordered)))}
            card = _card_networks(_composed(dataclasses.replace(base, financial_packets=packets)))
            operating = card["rerating"]["operating"]
            clock = (operating["clock"] or {}).get("observed_at")
            seen.add((operating["primary_metric"]["value"], clock, conflict in card["conflict_ids"]))
        return seen

    assert published(reading, down()) == {(5.0, "2026-09-20", True)}
    assert published(reading, down(observed_at="2026-09-01")) == {(5.0, "2026-09-20", True)}
    assert published(reading, down(observed_at="2026-09-22")) == {(7.0, "2026-09-22", False)}
    assert published(down()) == {(7.0, None, False)}


def test_on_one_date_the_slice_tagged_operating_observation_is_published() -> None:
    """Two operating observations share a date: one the owner tags with
    card_networks, reading UP, and one left untagged (company data), reading
    DOWN. The slice's own filing is the more specific, so it is published
    and the conflict is drawn, in either order, as the valuation anchor
    already rules. The plane used to publish whichever came last."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (tagged,) = packet["operating"]["observations"]
    untagged = {key: val for key, val in copy.deepcopy(tagged).items() if key != "slice_id"}
    untagged.update(direction="DOWN", metric=dict(untagged["metric"], value=7.0))
    for ordered in ((tagged, untagged), (untagged, tagged)):
        packets = {ticker: dict(packet, operating=dict(packet["operating"], observations=list(ordered)))}
        card = _card_networks(_composed(dataclasses.replace(base, financial_packets=packets)))
        assert card["rerating"]["operating"]["primary_metric"]["value"] == 5.0, ordered[0] is tagged
        assert "conflict-card_networks-earnings-up-pe-down" in card["conflict_ids"], ordered[0] is tagged


def test_the_price_plane_dates_a_row_by_its_observed_at() -> None:
    """A market row dated only by observed_at is a dated row: 2026-09-20 by
    observed_at is fresher than 2026-09-01 by as_of, so the price plane
    publishes it and its date, in either order. A row that carries no date
    still counts as the oldest. The plane used to count a row dated only by
    observed_at as undated, so it published the older row."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (row,) = base.market_observations["card_networks"]
    older = dict(row, as_of="2026-09-01", value=80.0)
    newer = _dated_by_observed_at(dict(row, value=90.0))
    undated = {key: val for key, val in row.items() if key != "as_of"} | {"value": 70.0}

    def published(*rows: dict[str, Any]) -> set[tuple[Any, Any]]:
        seen = set()
        for ordered in (rows, rows[::-1]):
            market = dict(base.market_observations, card_networks=list(ordered))
            price = _card_networks(_composed(dataclasses.replace(base, market_observations=market)))["rerating"]["price"]
            seen.add((price["primary_metric"]["value"], (price["clock"] or {}).get("observed_at")))
        return seen

    assert published(older, newer) == {(90.0, "2026-09-20")}
    assert published(older, undated) == {(80.0, "2026-09-01")}


def test_the_expectations_plane_dates_consensus_as_its_clock_does() -> None:
    """Consensus rows dated only by observed_at, or by a timestamp, are
    dated rows. Beside a row dated 2026-09-01 by as_of, one dated 2026-09-20
    either way is the fresher, so the plane publishes it and its date, in
    either order. The history carries both rows under the dates the clock
    reads, and the contract accepts the document. The history used to copy
    each row's as_of as the owner wrote it, so either row made the contract
    refuse the whole document."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    consensus = {"source": "synthetic_consensus", "metric": "eps_next_fy", "unit": "USD"}
    older = dict(consensus, as_of="2026-09-01", value=4.0)
    for fresher in (dict(consensus, observed_at="2026-09-20", value=6.0),
                    dict(consensus, as_of="2026-09-20T07:00:00Z", value=6.0)):
        for ordered in ((older, fresher), (fresher, older)):
            document = _composed(dataclasses.replace(base, expectation_observations={"card_networks": list(ordered)}))
            expectations = _card_networks(document)["rerating"]["expectations"]
            assert expectations["primary_metric"]["value"] == 6.0, ordered
            assert expectations["clock"]["observed_at"] == "2026-09-20", ordered
            assert [row["as_of"] for row in expectations["history"]["observations"]] == [
                "2026-09-01" if row is older else "2026-09-20" for row in ordered
            ], ordered


@pytest.mark.parametrize("when", ["2026-09-24", "2026-09-02"])
@pytest.mark.parametrize("kind", ["market", "consensus", "guidance", "operating", "valuation"])
def test_a_row_dated_by_observed_at_reads_as_the_same_row_dated_by_as_of(kind: str, when: str) -> None:
    """The composer reads one date from an observation: its as_of, else its
    observed_at. So moving the date of a market, consensus, guidance,
    operating or valuation row from as_of to observed_at changes nothing
    but the input digest: not a plane's reading or clock, not the valuation
    anchor, not the history, not the slice's freshness, and not
    common_as_of. Each case first shows the date reaches the document. A
    packet row's date is its plane's clock. Dated after every other input
    (the knowledge cutoff's day), a market or expectations row is the
    slice's latest evidence; dated before, it is the document's common
    as-of. Freshness and common_as_of used to read as_of alone, so a row
    dated by observed_at moved neither, and the expectations history
    refused it."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    if kind in ("operating", "valuation"):
        (ticker, packet), = base.financial_packets.items()
        (row,) = packet[kind]["observations"]

        def inputs_with(row: dict[str, Any]) -> FinanceOwnerInputs:
            block = dict(packet[kind], observations=[row])
            return dataclasses.replace(base, financial_packets={ticker: dict(packet, **{kind: block})})
    else:
        owner = "market_observations" if kind == "market" else "expectation_observations"
        if kind == "market":
            (row,) = base.market_observations["card_networks"]
        else:
            metric = "guidance:eps_next_fy" if kind == "guidance" else "eps_next_fy"
            row = {"source": "synthetic_consensus", "metric": metric, "value": 5.0, "unit": "USD"}

        def inputs_with(row: dict[str, Any]) -> FinanceOwnerInputs:
            return dataclasses.replace(base, **{owner: dict(getattr(base, owner), card_networks=[row])})

    dated = dict(row, as_of=when)
    by_as_of = _without_digest(_composed(inputs_with(dated)))
    if kind in ("operating", "valuation"):
        assert _card_networks(by_as_of)["rerating"][kind]["clock"]["observed_at"] == when
    elif when == "2026-09-24":
        assert _card_networks(by_as_of)["freshness"]["evidence_latest_observed_at"] == when
    else:
        assert by_as_of["common_as_of"] == when
    assert _without_digest(_composed(inputs_with(_dated_by_observed_at(dated)))) == by_as_of


def test_a_valuation_observation_dated_after_the_knowledge_cutoff_never_anchors() -> None:
    """Nothing dated after the knowledge cutoff can be known at it. A
    valuation observation dated the day after the cutoff is passed over
    beside card_networks' anchor, in either order; alone, it leaves the slice
    without an anchor, said in words. One dated on the cutoff itself still
    anchors. The freshest observation used to win however far past the
    cutoff its date was."""
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    (ticker, packet), = base.financial_packets.items()
    (anchor,) = packet["valuation"]["observations"]
    cutoff = _knowledge_cutoff().date()

    def dated(day: _dt.date, value: float) -> dict[str, Any]:
        obs = dict(copy.deepcopy(anchor), as_of=day.isoformat())
        obs["metric"] = dict(obs["metric"], value=value)
        return obs

    after = dated(cutoff + _dt.timedelta(days=1), 55.0)
    for ordered in ((anchor, after), (after, anchor)):
        valuation = _valuation_of(_with_valuation_observations(base, *ordered), "card_networks")
        assert valuation["primary_metric"]["value"] == 18.0, ordered[0] is anchor
    alone = _valuation_of(_with_valuation_observations(base, after), "card_networks")
    assert alone["state"] == "VALUATION_ANCHOR_UNAVAILABLE", alone
    assert alone["primary_metric"] is None and alone["clock"] is None
    on_cutoff = _valuation_of(_with_valuation_observations(base, anchor, dated(cutoff, 19.0)), "card_networks")
    assert on_cutoff["primary_metric"]["value"] == 19.0
    assert on_cutoff["clock"]["observed_at"] == cutoff.isoformat()


def test_a_constraint_is_published_under_the_slice_its_record_is_filed_under() -> None:
    """A source record is filed under its business_scope, and its record_id is
    evidence of that slice only. Its constraints are published under that
    slice, whatever slice_id extra the record carries. They used to follow the
    extra: a foreign one published a constraint under a slice its evidence is
    not filed under, and a record carrying none had its constraints dropped."""
    base = _default_8slice_inputs()
    (target,) = [rec["record_id"] for rec in base.source_records if rec.get("business_scope") == "card_networks"]
    constraint = {"constraint": "capital", "economic_effect": "SYNTHETIC economic effect."}

    def published_constraints(**extra: Any) -> list[tuple[str, list[str]]]:
        records = copy.deepcopy(list(base.source_records))
        for rec in records:
            if rec["record_id"] == target:
                rec.update(extra, constraints=[constraint])
        document = compose_finance_projection(
            dataclasses.replace(base, source_records=records),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        return [(c["slice_id"], c["evidence_refs"]) for c in document["constraints"]]

    filed = [("card_networks", [target])]
    assert published_constraints() == filed
    assert published_constraints(slice_id="issuer_processing") == filed
    assert published_constraints(slice_id="card_networks") == filed


def test_volume_never_populates_revenue_exposure() -> None:
    record = _default_operating_record(
        slice_id="card_networks",
        metric_class="VOLUME_COUNT",
        direction="UP",
        issuer="Synthetic Network Co.",
        ticker="SYN1",
    )
    inputs = _default_8slice_inputs(source_records=[record])
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    row = next(r for r in document["company_exposures"] if r["ticker_hint"] == "SYN1")
    cell = next(c for c in row["cells"] if c["slice_id"] == "card_networks")
    assert cell["exposure"]["basis"] == "TRANSACTION_VOLUME"
    assert cell["exposure"]["basis"] != "SEGMENT_REVENUE"
    validate_contract(CONTRACT_ID, document)


def test_no_segment_denominator_is_not_separately_disclosed() -> None:
    record = _default_operating_record(
        slice_id="card_networks",
        metric_class="REVENUE",
        direction="UP",
        issuer="Synthetic Network Co.",
        ticker="SYN1",
    )
    # Strip the segment denominator from the metric to force the
    # not-separately-disclosed branch.
    record["metric"]["denominator"] = None
    inputs = _default_8slice_inputs(source_records=[record])
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    row = next(r for r in document["company_exposures"] if r["ticker_hint"] == "SYN1")
    cell = next(c for c in row["cells"] if c["slice_id"] == "card_networks")
    assert cell["exposure"]["state"] == "EXPOSURE_NOT_SEPARATELY_DISCLOSED"
    assert cell["exposure"]["value"] is None
    validate_contract(CONTRACT_ID, document)


def _conflict_inputs_for(label: str) -> FinanceOwnerInputs:
    """Build an input bundle that deterministically produces one named conflict."""
    if label == "EARNINGS_UP_P_E_DOWN":
        fp = {
            "SYN1": {
                "operating": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "UP",
                            "metric": _metric_payload(
                                native_name="eps_diluted",
                                family="EPS",
                                value=5.0,
                                unit="USD",
                                measurement_class="PER_SHARE",
                            ),
                            "value": 5.0,
                            "unit": "USD",
                        }
                    ],
                },
                "valuation": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "DOWN",
                            "metric": _metric_payload(
                                native_name="pe_ratio",
                                family="P/E",
                                value=18.0,
                                unit="ratio",
                                measurement_class="RATIO",
                            ),
                            "value": 18.0,
                            "unit": "ratio",
                        }
                    ],
                },
            }
        }
        market = {
            "card_networks": [
                {
                    "as_of": "2026-09-20",
                    "price_basis": "PRICE_RETURN",
                    "value": 90.0,
                    "unit": "USD",
                    "direction": "UP",
                }
            ]
        }
        return _default_8slice_inputs(
            financial_packets=fp,
            market_rows=market,
        )

    if label == "BOOK_UP_P_B_DOWN":
        fp = {
            "SYN1": {
                "operating": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "UP",
                            "metric": _metric_payload(
                                native_name="tangible_book_value",
                                family="TBV",
                                value=100.0,
                                unit="USD",
                                measurement_class="BALANCE",
                            ),
                            "value": 100.0,
                            "unit": "USD",
                        }
                    ],
                },
                "valuation": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "DOWN",
                            "metric": _metric_payload(
                                native_name="pb_ratio",
                                family="P/B",
                                value=1.5,
                                unit="ratio",
                                measurement_class="RATIO",
                            ),
                            "value": 1.5,
                            "unit": "ratio",
                        }
                    ],
                },
            }
        }
        market = {
            "card_networks": [
                {
                    "as_of": "2026-09-20",
                    "price_basis": "PRICE_RETURN",
                    "value": 90.0,
                    "unit": "USD",
                    "direction": "UP",
                }
            ]
        }
        return _default_8slice_inputs(
            financial_packets=fp,
            market_rows=market,
        )

    if label == "POLICY_SUPPORT_NIM_PRESSURE":
        fp = {
            "SYN1": {
                "operating": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "DOWN",
                            "metric": _metric_payload(
                                native_name="nim",
                                family="NIM",
                                value=0.03,
                                unit="ratio",
                                measurement_class="RATIO",
                            ),
                            "value": 0.03,
                            "unit": "ratio",
                        }
                    ],
                },
                "valuation": {"cells": [], "observations": []},
            }
        }
        macro = {
            "card_networks": {
                "policy_rates_support": True,
                "mechanism_by_slice": {
                    "card_networks": {
                        "policy_rates": {
                            "mechanism": "Synthetic macro mechanism for card networks.",
                            "lag": "ONE_QUARTER",
                            "state": "DESCRIBED",
                        }
                    }
                },
            }
        }
        return _default_8slice_inputs(
            financial_packets=fp,
            macro_context=macro,
        )

    if label == "REGULATORY_RATIO_DOWN_REGIME_BREAK":
        fp = {
            "SYN1": {
                "operating": {
                    "cells": [],
                    "observations": [
                        {
                            "as_of": "2026-09-20",
                            "slice_id": "card_networks",
                            "direction": "DOWN",
                            "metric": _metric_payload(
                                native_name="tier1_capital_ratio",
                                family="tier1_capital_ratio",
                                value=0.12,
                                unit="ratio",
                                measurement_class="RATIO",
                            ),
                            "value": 0.12,
                            "unit": "ratio",
                        }
                    ],
                },
                "valuation": {"cells": [], "observations": []},
            }
        }
        regime = [
            {
                "slice_id": "card_networks",
                "plane": "operating",
                "from_basis": "BASEL_3",
                "to_basis": "BASEL_3_1",
                "effective_at": "2026-07-01",
                "bridge_available": False,
            }
        ]
        return _default_8slice_inputs(
            financial_packets=fp,
            regime_breaks=regime,
        )

    if label == "PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN":
        op_record = _schema_strict_source_record(slice_id="card_networks")
        # Inject a material change with CAUSAL_EFFECT_UNMEASURED so the
        # conflict detector recognises the price-up + unproven causal
        # effect pair on the same slice.
        op_record["material_change"] = {
            "change_id": "mc-001",
            "domain_ids": ["payments"],
            "operating_implication": "Synthetic material change.",
            "freshness_state": "CAUSAL_EFFECT_UNMEASURED",
        }
        market = {
            "card_networks": [
                {
                    "as_of": "2026-09-20",
                    "price_basis": "PRICE_RETURN",
                    "value": 100.0,
                    "unit": "USD",
                    "direction": "UP",
                }
            ]
        }
        return _default_8slice_inputs(
            source_records=[op_record],
            market_rows=market,
        )

    raise AssertionError("unknown conflict label: " + label)


def _flipped_inputs(label: str) -> FinanceOwnerInputs:
    base = _conflict_inputs_for(label)
    flipped_market: dict[str, Any] = dict(base.market_observations)
    if "card_networks" in flipped_market:
        rows = []
        for row in flipped_market["card_networks"]:
            row = dict(row)
            if row.get("direction") == "UP":
                row["direction"] = "DOWN"
            elif row.get("direction") == "DOWN":
                row["direction"] = "UP"
            rows.append(row)
        flipped_market["card_networks"] = rows
    new_fp: dict[str, dict[str, Any]] = {}
    for issuer_key, packet in base.financial_packets.items():
        new_packet = dict(packet)
        for plane_key in ("operating", "valuation"):
            plane_value = new_packet.get(plane_key)
            if not isinstance(plane_value, dict):
                continue
            new_plane = dict(plane_value)
            observations = plane_value.get("observations") or []
            new_obs = []
            for obs in observations:
                obs = dict(obs)
                if obs.get("direction") == "UP":
                    obs["direction"] = "DOWN"
                elif obs.get("direction") == "DOWN":
                    obs["direction"] = "UP"
                new_obs.append(obs)
            new_plane["observations"] = new_obs
            new_packet[plane_key] = new_plane
        new_fp[issuer_key] = new_packet
    return FinanceOwnerInputs(
        sector_dossier=base.sector_dossier,
        theme_evidence=base.theme_evidence,
        financial_packets=new_fp,
        expectation_observations=base.expectation_observations,
        market_observations=flipped_market,
        basket_context=base.basket_context,
        macro_context=base.macro_context,
        identity_bindings=base.identity_bindings,
        source_records=list(base.source_records),
        regime_breaks=base.regime_breaks,
        slice_catalog=base.slice_catalog,
        rights_snapshot=base.rights_snapshot,
    )


@pytest.mark.parametrize(
    "label",
    [
        "EARNINGS_UP_P_E_DOWN",
        "BOOK_UP_P_B_DOWN",
        "POLICY_SUPPORT_NIM_PRESSURE",
        "REGULATORY_RATIO_DOWN_REGIME_BREAK",
        "PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN",
    ],
)
def test_conflicts_are_deterministic_from_states(label: str) -> None:
    inputs = _conflict_inputs_for(label)
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    labels = [c["label"] for c in document["conflicts"]]
    assert label in labels, "expected conflict not present: " + label
    matching = next(c for c in document["conflicts"] if c["label"] == label)
    assert matching["resolution"] == "UNRESOLVED_BY_DESIGN"

    flipped = _flipped_inputs(label)
    flipped_doc = compose_finance_projection(
        flipped,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert all(c["label"] != label for c in flipped_doc["conflicts"]), (
        "flipped direction must NOT produce conflict: " + label
    )

    validate_contract(CONTRACT_ID, document)
    validate_contract(CONTRACT_ID, flipped_doc)


def test_rights_held_records_have_no_excerpt() -> None:
    record = _default_operating_record(
        slice_id="card_networks",
        issuer="Synthetic Network Co.",
        ticker="SYN1",
    )
    record["source"]["source_family"] = "internal_only"
    record["rights_state"] = "INTERNAL_ONLY"
    record["excerpt"] = "This should be cleared."
    inputs = _default_8slice_inputs(
        source_records=[record],
        rights_snapshot={"internal_only": "internal_only"},
    )
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    internal = [
        rec for rec in document["source_records"]
        if (rec.get("source") or {}).get("source_family") == "internal_only"
    ]
    assert internal
    for rec in internal:
        assert rec["rights_state"] == "INTERNAL_ONLY"
        assert rec["excerpt"] is None

    # A source_family that is not in the rights_snapshot at all becomes
    # SOURCE_RIGHTS_HELD with no excerpt.
    record2 = _default_operating_record(
        slice_id="merchant_acquiring_processing",
        issuer="Synthetic Market Infrastructure Co.",
        ticker="EXAMPLE",
    )
    record2["source"]["source_family"] = "unknown_family"
    record2["rights_state"] = "DIRECT_DISPLAY_OK"
    record2["excerpt"] = "Should be cleared."
    inputs2 = _default_8slice_inputs(source_records=[record, record2])
    document2 = compose_finance_projection(
        inputs2,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    held = [
        rec for rec in document2["source_records"]
        if (rec.get("source") or {}).get("source_family") == "unknown_family"
    ]
    assert held
    for rec in held:
        assert rec["rights_state"] == "SOURCE_RIGHTS_HELD"
        assert rec["excerpt"] is None
    validate_contract(CONTRACT_ID, document)
    validate_contract(CONTRACT_ID, document2)


def test_stale_evidence_marks_source_stale() -> None:
    record = _default_operating_record(
        slice_id="card_networks",
        observed_at="2025-01-01",  # well outside the 120-day window
    )
    inputs = _default_8slice_inputs(source_records=[record])
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    card = next(sl for sl in document["slices"] if sl["slice_id"] == "card_networks")
    assert card["freshness"]["state"] == "SOURCE_STALE"
    validate_contract(CONTRACT_ID, document)


def test_missing_outer_dossier_degrades_typed() -> None:
    inputs = _default_8slice_inputs(sector_dossier=None)
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert document["outer_dossier_ref"]["state"] == "OUTER_CONTRACT_NOT_ACCEPTED"
    assert document["outer_dossier_ref"]["contract_id"] is None
    sector_receipts = [
        r for r in document["input_receipts"] if r["owner"] == "sector_intelligence"
    ]
    assert sector_receipts and sector_receipts[0]["state"] == "NOT_ACCEPTED"
    validate_contract(CONTRACT_ID, document)


def test_empty_evidence_degrades_sections_not_document() -> None:
    inputs = FinanceOwnerInputs(
        sector_dossier=None,
        theme_evidence=[],
        financial_packets={},
        expectation_observations={},
        market_observations={},
        basket_context={},
        macro_context={},
        identity_bindings={},
        source_records=[],
        regime_breaks=[],
        slice_catalog=_base_slice_catalog(),
        rights_snapshot={},
    )
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    # Document still validates with every required section present.
    validate_contract(CONTRACT_ID, document)
    sections = {s["section"] for s in document["degraded_sections"]}
    assert "evidence_drawer" in sections
    assert "company_exposure" in sections
    evidence_state = next(
        s for s in document["degraded_sections"] if s["section"] == "evidence_drawer"
    )
    assert evidence_state["state"] == "UNAVAILABLE"


def test_digest_is_input_only() -> None:
    inputs = _default_8slice_inputs()
    first = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    second = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert first["snapshot_identity"]["input_digest"] == second["snapshot_identity"]["input_digest"]
    later = compose_finance_projection(
        inputs,
        generated_at=_dt.datetime(2030, 1, 1, 0, 0, 0),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert (
        first["snapshot_identity"]["input_digest"]
        == later["snapshot_identity"]["input_digest"]
    )
    digest_hex = first["snapshot_identity"]["input_digest"]
    assert re.fullmatch(r"[0-9a-f]{64}", digest_hex) is not None
    # Independently re-hash the same canonical payload and confirm equality.
    payload = json.dumps(
        {
            "composer_version": "finance_projection/1",
            "sector_dossier": inputs.sector_dossier,
            "theme_evidence": list(inputs.theme_evidence),
            "financial_packets": dict(inputs.financial_packets),
            "expectation_observations": dict(inputs.expectation_observations),
            "market_observations": dict(inputs.market_observations),
            "basket_context": dict(inputs.basket_context),
            "macro_context": inputs.macro_context,
            "identity_bindings": dict(inputs.identity_bindings),
            "source_records": list(inputs.source_records),
            "regime_breaks": list(inputs.regime_breaks),
            "slice_catalog": list(inputs.slice_catalog),
            "rights_snapshot": dict(inputs.rights_snapshot),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert digest_hex == expected


def test_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Composition must succeed with open / socket / time / datetime.now patched.

    ``builtins.open``, ``socket.socket``, ``time.time`` and ``datetime.now``
    are replaced by sentinels that raise. ``compose_finance_projection``
    must still return a valid document because it must never read the
    clock, open a file, or open a socket.
    """
    def _explode(*_args, **_kwargs):
        raise AssertionError("IO/clock was read by the composer")

    monkeypatch.setattr(builtins, "open", _explode)
    monkeypatch.setattr(_socket, "socket", _explode)
    monkeypatch.setattr(_time, "time", _explode)

    # ``datetime.datetime.now`` is a built-in C-level method on the
    # immutable datetime class, so it cannot be patched directly. The
    # composer imports ``datetime`` by name, so replace the binding inside
    # the composer module with a subclass whose ``now`` and ``utcnow``
    # raise. ``isinstance(value, datetime)`` still returns True because
    # the replacement inherits from the real datetime class.
    class _RaisingDatetime(_dt.datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("datetime.now was called")

        @classmethod
        def utcnow(cls, *args, **kwargs):
            raise AssertionError("datetime.utcnow was called")

    import engine.sector_intelligence.finance_projection as _fp_mod

    monkeypatch.setattr(_fp_mod, "datetime", _RaisingDatetime)

    inputs = _default_8slice_inputs()
    document = compose_finance_projection(
        inputs,
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    validate_contract(CONTRACT_ID, document)


@pytest.mark.parametrize(
    "stated, published",
    [
        (None, "NO_EVIDENCE"),
        ("", "NO_EVIDENCE"),
        ("NOT_A_FRESHNESS_STATE", "NO_EVIDENCE"),
        ("aging", "AGING"),
        ("SOURCE_STALE", "SOURCE_STALE"),
    ],
)
def test_a_material_change_without_a_known_freshness_is_published_as_no_evidence(stated, published) -> None:
    """A material change whose owner states no freshness, or a freshness the
    projection does not recognise, is published as NO_EVIDENCE. It must never
    read as FRESH: freshness is a claim, and an absent claim is not a fresh one
    (``None`` means the key is absent)."""
    op_record = _schema_strict_source_record(slice_id="card_networks")
    material = {
        "change_id": "mc-freshness-001",
        "domain_ids": ["payments"],
        "operating_implication": "Synthetic material change.",
    }
    if stated is not None:
        material["freshness_state"] = stated
    op_record["material_change"] = material
    document = compose_finance_projection(
        _default_8slice_inputs(source_records=[op_record]),
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    validate_contract(CONTRACT_ID, document)
    changes = [c for c in document["material_changes"] if c["change_id"] == "mc-freshness-001"]
    assert [c["freshness_state"] for c in changes] == [published]


# ---------------------------------------------------------------------------
# An owner key the contract does not know never crosses into the document.
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "sector_intelligence"
    / "finance_intelligence_read_model.v1.schema.json"
)
_PLANTED_NOTE = "zz_planted_private_note"
_PLANTED_RANK = "zz_planted_peer_rank"


_PLANTED_KEYS = {_PLANTED_NOTE: "SYNTHETIC-private", _PLANTED_RANK: 1}

# What a plant carries out, however a path reshapes it: the planted key or the
# planted value, in any letter case. A path that hashes, encodes or truncates
# them is beyond this search.
_PLANTED_MARKERS = ("zz_planted", "synthetic-private")


def _carries_planted(text: str) -> bool:
    folded = text.casefold()
    return any(marker in folded for marker in _PLANTED_MARKERS)


def _plant_owner_keys(node: object, keys: dict = _PLANTED_KEYS) -> int:
    """Plant ``keys`` (by default a private note and a peer rank) into every
    owner record under ``node``.

    A dict whose values are all containers is a map keyed by data (issuer
    labels, plane names), not a record, and is left alone, as is an empty
    dict. Returns the number of records planted.
    """
    planted = 0
    if isinstance(node, dict):
        for child in list(node.values()):
            planted += _plant_owner_keys(child, keys)
        if node and not all(isinstance(v, (dict, list, tuple)) for v in node.values()):
            node.update(keys)
            planted += 1
    elif isinstance(node, (list, tuple)):
        for child in node:
            planted += _plant_owner_keys(child, keys)
    return planted


_FENCE_FIXTURES = (
    "default",
    "EARNINGS_UP_P_E_DOWN",
    "BOOK_UP_P_B_DOWN",
    "POLICY_SUPPORT_NIM_PRESSURE",
    "REGULATORY_RATIO_DOWN_REGIME_BREAK",
    "PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN",
)
# A map from source family to rights class, keyed by data: its family names
# are published by design in generation.rights_profile.
_UNPLANTED_FIELDS = frozenset({"rights_snapshot"})


def _extended_owner_inputs(fixture: str) -> FinanceOwnerInputs:
    """The fixture, with the four owner fields every committed fixture leaves
    empty filled in memory with SYNTHETIC records the composer reads. Without
    them a fence over the owner fields never reaches the dossier, theme
    evidence, expectation or basket paths. Two owner keys no committed fixture
    carries are added the same way, since a plant reaches only the keys a
    record holds: a source record's constraints, whose economic effect is
    published as free text, and a material change's conflict_ids."""
    base = _default_8slice_inputs() if fixture == "default" else _conflict_inputs_for(fixture)
    records = copy.deepcopy(list(base.source_records))
    for rec in records:
        if isinstance(rec, dict) and isinstance(rec.get("material_change"), dict):
            rec["material_change"].setdefault("conflict_ids", ["SYNTHETIC-conflict-ref"])
            break
    for rec in records:
        if isinstance(rec, dict) and isinstance(rec.get("business_scope"), str):
            rec.setdefault("slice_id", rec["business_scope"])
            rec.setdefault("constraints", [{"constraint": "capital", "economic_effect": "SYNTHETIC economic effect."}])
            break
    expectations = dict(base.expectation_observations)
    expectations.setdefault("card_networks", [
        {"as_of": "2026-09-15", "source": "src-consensus-001", "metric": "consensus:net_revenue_yoy",
         "value": 0.04, "unit": "ratio"},
    ])
    expectations.setdefault("issuer_processing", [
        {"as_of": "2026-09-15", "source": "src-guidance-002", "metric": "guidance:net_revenue_yoy",
         "value": 0.05, "unit": "ratio"},
    ])
    baskets = dict(base.basket_context)
    baskets.setdefault("card_networks", {
        "posture": "BROAD_CONTEXT_AVAILABLE",
        "incumbent_basket_ids": ["payments_fintech"],
        "membership_state": "CURRENT_MEMBERSHIP_ONLY",
        "member_count": 12,
        "weighting_family": "EQUAL_WEIGHT",
        "price_basis_state": "PRICE_BASIS_UNQUALIFIED",
    })
    return dataclasses.replace(
        base,
        sector_dossier=base.sector_dossier or {
            "schema_version": "sector_dossier_read_model.v1",
            "dossier_id": "SYNTHETIC-dossier-finance",
            "dossier_hash": "SYNTHETIC-dossier-hash",
        },
        theme_evidence=list(base.theme_evidence) or [
            {"theme_id": "SYNTHETIC-theme", "curation_revision": "SYNTHETIC-revision-1"},
        ],
        expectation_observations=expectations,
        basket_context=baskets,
        source_records=records,
    )


def test_the_owner_fences_plant_every_owner_field() -> None:
    """The fences below reach only the records they plant. Across the fixtures,
    every owner field but the one exempted by name carries a record, and each
    extended fixture still composes a document the contract accepts."""
    planted = set()
    for fixture in _FENCE_FIXTURES:
        base = _extended_owner_inputs(fixture)
        validate_contract(
            CONTRACT_ID,
            compose_finance_projection(base, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff()),
        )
        for field in dataclasses.fields(base):
            if field.name not in _UNPLANTED_FIELDS and _plant_owner_keys(copy.deepcopy(getattr(base, field.name))):
                planted.add(field.name)
    assert planted == {field.name for field in dataclasses.fields(FinanceOwnerInputs)} - _UNPLANTED_FIELDS


# Keys the composer reads that no owner record carries, each with its reason.
_COMPOSER_READ_KEYS_NOT_OWNER_CARRIED = frozenset({
    "_freshness_state_raw",  # composer-authored; popped before the document is returned
    "_ticker_hint",  # composer-authored from a source record; compared, never published as read
    "cells", "observations", "operating", "primary_metric", "valuation",  # the composer's own planes and rows
    "clock",  # the composer's own plane clock; published only into a date-format field
    "row_id",  # composer-minted company row id
    "support",  # an owner macro key read only as a truth test; never published
})


def test_every_owner_key_the_composer_reads_is_planted() -> None:
    """The value fence mutates only the keys the fixture records hold, so a key
    the composer reads that no fixture carries is a key no plant reaches. Every
    ``.get()`` key the composer gives as a string literal, in either quote, is
    carried by an owner record of an extended fixture or named above with its
    reason. Bounds: the census is
    by key name, not by owner field, and reads through a variable key or a
    subscript are outside it. The list is non-empty, so a census that matched
    nothing cannot pass."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    source = Path(_fp_mod.__file__).read_text(encoding="utf-8")
    read = set(re.findall(r'\.get\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']', source))
    carried: set[str] = set()
    for fixture in _FENCE_FIXTURES:
        base = _extended_owner_inputs(fixture)
        for field in dataclasses.fields(base):
            if field.name in _UNPLANTED_FIELDS:
                continue
            value = getattr(base, field.name)
            for path in _owner_record_paths(value):
                carried.update(map(str, _owner_record_at(value, path)))
    assert read - carried == _COMPOSER_READ_KEYS_NOT_OWNER_CARRIED, sorted(read - carried)


def test_the_metric_vocabulary_is_the_schemas() -> None:
    metric = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))["$defs"]["metric"]
    assert metric["additionalProperties"] is False
    assert _METRIC_FIELDS == tuple(metric["properties"])
    assert set(_METRIC_FIELDS) == set(metric["required"])


def test_an_owner_metric_crosses_only_through_the_metric_vocabulary() -> None:
    owner = _metric_payload(native_name="nim", family="NIM", value=3.5, unit="%")
    owner.update({_PLANTED_NOTE: "SYNTHETIC-private", _PLANTED_RANK: 1, "composite_score": 0.9})
    metric = _build_primary_metric({"as_of": "2026-09-20", "metric": owner})
    assert tuple(metric) == _METRIC_FIELDS
    # Every stated value is the owner's own object, never a re-derived copy.
    assert all(metric[key] is owner[key] for key in _METRIC_FIELDS)


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_an_owner_key_outside_the_contract_never_reaches_the_document(fixture: str) -> None:
    """Every owner record under one input field at a time carries a private
    note and a peer rank that the contract does not know. The document must
    still validate and must hold neither: the composer projects owner records
    onto the read model's vocabulary and never copies one wholesale."""
    base = _extended_owner_inputs(fixture)
    planted_fields = []
    for field in dataclasses.fields(base):
        if field.name in _UNPLANTED_FIELDS:
            continue
        value = copy.deepcopy(getattr(base, field.name))
        if not _plant_owner_keys(value):
            continue
        planted_fields.append(field.name)
        document = compose_finance_projection(
            dataclasses.replace(base, **{field.name: value}),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        # Assert a bare bool: pytest explains a failed `not in` over this
        # document's 148 KB dump with a superlinear diff, about 130 s per
        # failure (DSC:PYTEST-EXPLAINS-A-FAILED-NOT-IN-OVER-A-LONG-STRING-WITH-A-SUPERLINEAR-DIFF).
        leaked = _carries_planted(json.dumps(document, default=str))
        assert not leaked, field.name
    assert {
        "financial_packets", "sector_dossier", "theme_evidence", "expectation_observations", "basket_context",
    } <= set(planted_fields)


@pytest.mark.parametrize(
    "admitted, refusal",
    [
        (_PLANTED_NOTE, None),
        (_PLANTED_RANK, "forbidden score/rank/attractiveness/composite field under .*slices"),
    ],
)
def test_the_owner_key_fences_fire_on_a_key_the_composer_admits(
    monkeypatch: pytest.MonkeyPatch, admitted: str, refusal: str | None
) -> None:
    """Positive control for the fences above. A composer that admits one more
    metric key lets the planted private note through, and the contract rejects
    the document. If the admitted key is a peer rank, the composer's own emit
    guard refuses it first, naming the section and never the key."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    monkeypatch.setattr(_fp_mod, "_METRIC_FIELDS", _METRIC_FIELDS + (admitted,))
    base = _conflict_inputs_for("EARNINGS_UP_P_E_DOWN")
    packets = copy.deepcopy(base.financial_packets)
    assert _plant_owner_keys(packets)
    inputs = dataclasses.replace(base, financial_packets=packets)
    if refusal is not None:
        with pytest.raises(AssertionError, match=refusal) as excinfo:
            compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
        assert not _carries_planted(str(excinfo.value))
        return
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    carried = admitted in json.dumps(document, default=str)
    assert carried
    with pytest.raises(ContractValidationError):
        validate_contract(CONTRACT_ID, document)


# ---------------------------------------------------------------------------
# An owner value crosses into free text only as a scalar.
#
# Most of the contract's free-text fields ask only for a non-empty string, so
# the key plant above cannot see an owner mapping the composer stringifies: the
# planted keys ride inside one string value and the document still validates.
# The plant below reaches the composer's fallbacks and conversions instead, by
# deleting, emptying or replacing each owner value in turn.
# ---------------------------------------------------------------------------

# The note alone: it carries no authority word, so the composer's emit guard
# cannot intercept it, and only the composer's own projection or the contract
# stands between it and the page. (A structure carrying the peer rank is
# refused by the emit guard wherever it lands, which hides the contract.)
_PLANTED_STRUCTURE = {_PLANTED_NOTE: "SYNTHETIC-private"}


def _owner_record_paths(node: object, path: tuple = ()) -> list[tuple]:
    """The path of every owner record under ``node``, by the rule of :func:`_plant_owner_keys`."""
    paths: list[tuple] = []
    if isinstance(node, dict):
        for key, child in node.items():
            paths += _owner_record_paths(child, path + (key,))
        if node and not all(isinstance(v, (dict, list, tuple)) for v in node.values()):
            paths.append(path)
    elif isinstance(node, (list, tuple)):
        for index, child in enumerate(node):
            paths += _owner_record_paths(child, path + (index,))
    return paths


def _owner_record_at(node: object, path: tuple) -> dict:
    for step in path:
        node = node[step]  # type: ignore[index]
    assert isinstance(node, dict)
    return node


def _owner_value_mutations(base: FinanceOwnerInputs, exercised: set | None = None):
    """Every owner record key, one at a time: deleted, emptied, or replaced by
    a structure carrying a private note (and by a list holding one, where the
    owner value is a list). Every record of the field carries the note as a key
    too, so a fallback that stringifies an owner mapping carries it out.

    Records of one shape at one position are exercised once per fixture, and a
    record already exercised with identical content, at the same position, by
    an earlier fixture sharing ``exercised`` is not exercised again."""
    exercised = set() if exercised is None else exercised
    for field in dataclasses.fields(base):
        if field.name in _UNPLANTED_FIELDS:
            continue
        original = getattr(base, field.name)
        shapes = set()
        for path in _owner_record_paths(original):
            record = _owner_record_at(original, path)
            shape = (tuple("#" if isinstance(step, int) else step for step in path), tuple(sorted(map(str, record))))
            if shape in shapes:
                continue
            shapes.add(shape)
            identity = (field.name, path, json.dumps(record, sort_keys=True, default=str))
            if identity in exercised:
                continue
            exercised.add(identity)
            for key, value in record.items():
                variants = ["absent", "empty", "structure"]
                if isinstance(value, (list, tuple)):
                    variants.append("structure-in-list")
                for variant in variants:
                    mutated = copy.deepcopy(original)
                    _plant_owner_keys(mutated, _PLANTED_STRUCTURE)
                    target = _owner_record_at(mutated, path)
                    if variant == "absent":
                        del target[key]
                    elif variant == "empty":
                        target[key] = ""
                    elif variant == "structure":
                        target[key] = dict(_PLANTED_STRUCTURE)
                    else:
                        target[key] = [dict(_PLANTED_STRUCTURE)]
                    yield (field.name, path, key, variant), dataclasses.replace(base, **{field.name: mutated})


@functools.lru_cache(maxsize=None)
def _contract_registry() -> ContractRegistry:
    # One registry for the whole plant: validate_contract builds a fresh one
    # per call, about 0.9 s against 0.05 s for a reused one.
    return ContractRegistry()


def _owner_fence_outcome(inputs: FinanceOwnerInputs) -> str:
    """``clean``: no planted key or value, in any case, reached the document.
    ``sealed``: one did, and the contract refuses the document. ``refused``:
    the composer raised without repeating anything planted. ``LEAKED``:
    something planted reached a document the contract accepts, or an error
    message."""
    try:
        document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    except Exception as exc:  # a refusal fails closed unless it repeats the planted content
        return "LEAKED" if _carries_planted(str(exc)) else "refused"
    if not _carries_planted(json.dumps(document, default=str)):
        return "clean"
    try:
        _contract_registry().validate(CONTRACT_ID, document)
    except ContractValidationError:
        return "sealed"
    return "LEAKED"


@functools.lru_cache(maxsize=None)
def _value_fence_outcomes() -> tuple[tuple[str, tuple, str], ...]:
    # One pass of the value plant (about 15 s) serves both assertions below.
    exercised: set = set()
    return tuple(
        (fixture, case, _owner_fence_outcome(inputs))
        for fixture in _FENCE_FIXTURES
        for case, inputs in _owner_value_mutations(_extended_owner_inputs(fixture), exercised)
    )


def test_an_owner_value_crosses_into_free_text_only_as_a_scalar() -> None:
    outcomes: dict[str, int] = {}
    for _fixture, _case, outcome in _value_fence_outcomes():
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    leaks = [(fixture, *case) for fixture, case, outcome in _value_fence_outcomes() if outcome == "LEAKED"]
    assert outcomes.get("clean", 0) > 0 and outcomes.get("sealed", 0) > 0, outcomes
    assert not leaks, (outcomes, leaks[:20])


# The owner-text seam with its gate removed: a structure is published as it is,
# upper-cased, or as the mapping's values alone. Scalars keep the real gate.
_RESHAPED_OWNER_TEXT = {
    "str": str,
    "upper": lambda value: str(value).upper(),
    "values": lambda value: " ".join(map(str, value.values())) if isinstance(value, dict) else str(value),
}


@pytest.mark.parametrize("reshape", sorted(_RESHAPED_OWNER_TEXT))
def test_the_owner_value_fence_fires_on_a_stringified_owner_metric(monkeypatch: pytest.MonkeyPatch, reshape: str) -> None:
    """Positive control for the fence above. With the gate removed at the
    owner-text seam, an operating observation whose metric mapping has lost its
    name publishes the mapping as the name, and the contract accepts the
    document: a name only has to be a non-empty string. The fence must call it
    LEAKED however the mapping is rendered, including upper-cased or as its
    values alone, which carry the private note without its key."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    cases = [
        inputs
        for (field, _path, key, variant), inputs in _owner_value_mutations(_extended_owner_inputs("EARNINGS_UP_P_E_DOWN"))
        if field == "financial_packets" and key == "native_metric_name" and variant in ("absent", "empty")
    ]
    assert cases
    assert "LEAKED" not in {_owner_fence_outcome(inputs) for inputs in cases}
    render = _RESHAPED_OWNER_TEXT[reshape]
    monkeypatch.setattr(
        _fp_mod, "_owner_text", lambda value: render(value) if isinstance(value, (dict, list, tuple)) else _owner_text(value)
    )
    assert "LEAKED" in {_owner_fence_outcome(inputs) for inputs in cases}


def test_a_malformed_owner_value_is_refused_by_the_contract_never_by_a_crash() -> None:
    """The same plant, read for totality. A structure where the composer
    looks a value up (a rights family, a slice id, a price basis, a metric
    name) raised TypeError or AttributeError inside the composer, so the
    publish step saw an arbitrary exception instead of the contract's refusal.
    Every such value now reaches the contract or is treated as absent."""
    crashes = [(fixture, *case) for fixture, case, outcome in _value_fence_outcomes() if outcome == "refused"]
    assert not crashes, crashes[:20]


def test_the_owner_value_fence_fires_on_an_ungated_owner_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive control for the totality test above. With the lookup gate
    removed, a structure given as a source family is hashed by the rights
    lookup and the composer raises."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    cases = [
        inputs
        for (field, _path, key, variant), inputs in _owner_value_mutations(_extended_owner_inputs("default"))
        if (field, key, variant) == ("source_records", "source_family", "structure")
    ]
    assert cases
    assert "refused" not in {_owner_fence_outcome(inputs) for inputs in cases}
    monkeypatch.setattr(_fp_mod, "_owner_key", lambda value: value)
    assert "refused" in {_owner_fence_outcome(inputs) for inputs in cases}


def test_owner_text_is_a_scalar_or_nothing() -> None:
    assert _owner_text("nim") == "nim"
    assert _owner_text(3) == "3"
    assert _owner_text(_dt.date(2026, 9, 15)) == "2026-09-15"
    assert _owner_text(None) is None
    assert _owner_text(dict(_PLANTED_STRUCTURE)) is None
    assert _owner_text([_PLANTED_NOTE]) is None
    # A mapping is not a list of references: iterating it would publish its keys.
    assert _owner_refs(dict(_PLANTED_STRUCTURE)) == []
    assert _owner_refs(["ref-1", "", None, dict(_PLANTED_STRUCTURE), 7]) == ["ref-1", "7"]
    # A looked-up value is text or absent: a structure is unhashable.
    assert _owner_key("card_networks") == "card_networks"
    assert _owner_key("") == ""
    assert _owner_key(None) is None
    assert _owner_key(dict(_PLANTED_STRUCTURE)) is None
    assert _owner_key([_PLANTED_NOTE]) is None


def test_the_emit_guard_walks_tuples() -> None:
    assert _has_forbidden_key({"cells": ({"peer_rank": 1},)})
    assert not _has_forbidden_key({"cells": ({"value": 1},)})


# ---------------------------------------------------------------------------
# Evidence refs: every ref is the owner's, and no reading goes unbacked
# ---------------------------------------------------------------------------

_PLANES = ("operating", "expectations", "valuation", "price")
_OWNER_REF_KEYS = frozenset({"record_id", "evidence_ref", "evidence_refs", "source"})


def _owner_ref_values(value: Any) -> set[str]:
    """Every string an owner input carries under a reference key: a record
    id, an evidence ref or ref list, or an observation's source."""
    found: set[str] = set()
    stack: list[Any] = [value]
    while stack:
        node = stack.pop()
        if dataclasses.is_dataclass(node) and not isinstance(node, type):
            stack.extend(getattr(node, field.name) for field in dataclasses.fields(node))
        elif isinstance(node, dict):
            for key, child in node.items():
                if key in _OWNER_REF_KEYS:
                    if isinstance(child, str):
                        found.add(child)
                    elif isinstance(child, (list, tuple)):
                        found.update(item for item in child if isinstance(item, str))
                stack.append(child)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)
    return found


def _published_refs(document: dict[str, Any]) -> list[tuple[str, str]]:
    """(path, ref) for every evidence ref the document publishes."""
    found: list[tuple[str, str]] = []
    stack: list[tuple[str, Any]] = [("", document)]
    while stack:
        path, node = stack.pop()
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "evidence_refs" and isinstance(child, list):
                    found.extend((f"{path}.{key}", ref) for ref in child)
                else:
                    stack.append((f"{path}.{key}", child))
        elif isinstance(node, list):
            stack.extend((f"{path}[]", child) for child in node)
    return found


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_every_published_evidence_ref_is_an_owner_ref(fixture: str) -> None:
    """The composer never mints an evidence ref. It used to publish
    "slice:<id>" for any slice no owner ref backed, so the contract's rule
    that an OBSERVED plane cites evidence could never fail: 220 of the 263
    refs on the default fixture pointed at no record. Every ref is now a
    string the owner inputs carry under a reference key, and every plane that
    publishes a reading cites one."""
    inputs = _extended_owner_inputs(fixture)
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    validate_contract(CONTRACT_ID, document)
    owner_refs = _owner_ref_values(inputs)
    minted = [(path, ref) for path, ref in _published_refs(document) if ref not in owner_refs]
    assert not minted, minted[:10]
    unbacked = [
        (slice_doc["slice_id"], plane)
        for slice_doc in document["slices"]
        for plane in _PLANES
        if slice_doc["rerating"][plane]["primary_metric"] is not None and not slice_doc["rerating"][plane]["evidence_refs"]
    ]
    assert not unbacked, unbacked


@pytest.mark.parametrize("mint", ["prefixed", "bare"])
def test_the_evidence_ref_oracle_fires_on_a_minted_ref(monkeypatch: pytest.MonkeyPatch, mint: str) -> None:
    """Positive control for the test above. Restore the old fallback, or mint
    the bare slice id, and the oracle finds the minted refs: it asks whether
    the owner carries a ref, not whether the ref has a known prefix."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    owner_only = _fp_mod._slice_evidence_refs
    make = {"prefixed": lambda slice_id: "slice:" + slice_id, "bare": lambda slice_id: slice_id}[mint]
    monkeypatch.setattr(
        _fp_mod, "_slice_evidence_refs",
        lambda slice_id, *rest: owner_only(slice_id, *rest) or [make(slice_id)],
    )
    inputs = _extended_owner_inputs("default")
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    owner_refs = _owner_ref_values(inputs)
    assert [ref for _path, ref in _published_refs(document) if ref not in owner_refs]


def _owner_refs_by_slice(inputs: FinanceOwnerInputs) -> dict[str, set[str]]:
    """The refs the owner files under each slice: a source record's by its
    business_scope, an observation's by the slice it is keyed under."""
    owned: dict[str, set[str]] = {}
    for rec in inputs.source_records:
        if isinstance(rec, dict):
            owned.setdefault(rec.get("business_scope"), set()).update(_owner_ref_values(rec))
    for observations in (inputs.expectation_observations, inputs.market_observations):
        for slice_id, obs in (observations or {}).items():
            owned.setdefault(slice_id, set()).update(_owner_ref_values(obs))
    return owned


def _refs_outside_their_slice(inputs: FinanceOwnerInputs, document: dict[str, Any]) -> list[tuple]:
    owned = _owner_refs_by_slice(inputs)
    foreign = [
        (slice_doc["slice_id"], path, ref)
        for slice_doc in document["slices"]
        for path, ref in _published_refs(slice_doc)
        if ref not in owned.get(slice_doc["slice_id"], set())
    ]
    for conflict in document["conflicts"]:
        joined = set().union(*(owned.get(slice_id, set()) for slice_id in conflict["slice_ids"]))
        foreign += [(tuple(conflict["slice_ids"]), path, ref) for path, ref in _published_refs(conflict) if ref not in joined]
    return foreign


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_a_slice_cites_only_evidence_its_owner_files_under_it(fixture: str) -> None:
    """A section's evidence button opens the refs its slice publishes, so a
    ref the owner files under another slice would open that slice's record.
    Each slice, on the slice and on its four planes, cites only refs the owner
    files under it, and a conflict cites only refs of the slices it joins.
    The owner-ref oracle above pools every slice's refs and cannot see this."""
    inputs = _extended_owner_inputs(fixture)
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    foreign = _refs_outside_their_slice(inputs, document)
    assert not foreign, foreign[:10]


def test_the_slice_evidence_oracle_fires_on_an_unscoped_composer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive control for the test above. A composer that stops scoping
    source records by slice cites every record on every slice. Each ref is
    still one the owner carries, so the pooled oracle passes, and only the
    per-slice oracle finds the refs a slice does not own."""
    import engine.sector_intelligence.finance_projection as _fp_mod

    scoped = _fp_mod._slice_evidence_refs

    def unscoped(slice_id, source_records, *rest):
        records = [dict(rec, business_scope=slice_id) if isinstance(rec, dict) else rec for rec in source_records]
        return scoped(slice_id, records, *rest)

    monkeypatch.setattr(_fp_mod, "_slice_evidence_refs", unscoped)
    inputs = _extended_owner_inputs("default")
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    owner_refs = _owner_ref_values(inputs)
    assert not [ref for _path, ref in _published_refs(document) if ref not in owner_refs]
    assert _refs_outside_their_slice(inputs, document)


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES[1:])
def test_a_reading_no_owner_ref_backs_is_withheld(fixture: str) -> None:
    """Drop the one source record behind card_networks in a conflict fixture.
    The old composer still published OBSERVED planes there, citing only the
    minted "slice:card_networks", and the contract accepted the document.
    Now each reading is withheld. An OBSERVED plane becomes MISSING with its
    own plane's note, any other state keeps its words, and the fixture's
    conflict is not drawn, since it rested on those readings. The readings'
    dates are withheld too, so the slice's freshness says it has no evidence.
    The document stays valid, so one slice's missing evidence never refuses
    the other slices."""
    base = _conflict_inputs_for(fixture)
    kept = [rec for rec in base.source_records if not (isinstance(rec, dict) and rec.get("business_scope") == "card_networks")]
    assert len(kept) < len(base.source_records)

    def card_networks(inputs: FinanceOwnerInputs) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
        validate_contract(CONTRACT_ID, document)
        slice_doc = next(s for s in document["slices"] if s["slice_id"] == "card_networks")
        return slice_doc, [c for c in document["conflicts"] if "card_networks" in c["slice_ids"]]

    before, conflicts = card_networks(base)
    assert conflicts and any(before["rerating"][plane]["primary_metric"] is not None for plane in _PLANES)
    after, conflicts = card_networks(dataclasses.replace(base, source_records=kept))
    assert not conflicts, conflicts
    for plane in _PLANES:
        published = after["rerating"][plane]
        assert published["evidence_refs"] == [], plane
        assert published["primary_metric"] is None and published["clock"] is None, plane
        assert published["state"] != "OBSERVED", plane
        if before["rerating"][plane]["state"] == "OBSERVED":
            assert published["note"] == f"{plane.capitalize()} evidence is not available for this slice.", plane
    assert after["freshness"] == {"evidence_latest_observed_at": None, "state": "NO_EVIDENCE"}


def test_a_withheld_reading_publishes_no_date() -> None:
    """A withheld reading's date is withheld with it. Give a slice no owner
    ref backs one qualified price row, dated years before every other input:
    its price plane publishes no reading, its freshness says it has no
    evidence, and the document's common_as_of and freshness are what they are
    without the row. The date used to reach all three, and the document read
    SOURCE_STALE from a price it never published. With an owner source the
    row is evidence: its reading is published and its date counts."""
    base = _default_8slice_inputs()
    row = {"as_of": "2019-01-02", "price_basis": "PRICE_RETURN", "value": 42.0, "unit": "USD", "direction": "UP"}

    def compose_with(market_row: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
        market = dict(base.market_observations)
        if market_row is not None:
            market["private_credit_managers"] = [market_row]
        document = compose_finance_projection(
            dataclasses.replace(base, market_observations=market),
            generated_at=_today(),
            knowledge_cutoff=_knowledge_cutoff(),
        )
        validate_contract(CONTRACT_ID, document)
        return document, next(s for s in document["slices"] if s["slice_id"] == "private_credit_managers")

    baseline, slice_doc = compose_with(None)
    assert not slice_doc["evidence_refs"]
    withheld, slice_doc = compose_with(row)
    assert slice_doc["rerating"]["price"]["primary_metric"] is None
    assert slice_doc["freshness"] == {"evidence_latest_observed_at": None, "state": "NO_EVIDENCE"}
    assert (withheld["common_as_of"], withheld["freshness"]) == (baseline["common_as_of"], baseline["freshness"])

    evidenced, slice_doc = compose_with(dict(row, source="synthetic-market-private_credit_managers"))
    assert slice_doc["rerating"]["price"]["primary_metric"] is not None
    assert slice_doc["freshness"] == {"evidence_latest_observed_at": "2019-01-02", "state": "SOURCE_STALE"}
    assert evidenced["common_as_of"] == "2019-01-02"


def test_a_plane_publishes_a_reading_only_with_an_owner_ref() -> None:
    reading = {
        "state": "OBSERVED",
        "primary_metric": {"value": 1.0},
        "clock": {"as_of": "2026-09-01"},
        "comparability_state": "COMPARABLE",
        "evidence_refs": [],
        "note": "Operating observation is preserved as supplied by the owner.",
    }
    missing = "Operating evidence is not available for this slice."
    assert _withhold_unevidenced(reading, missing) == dict(
        reading, state="MISSING", primary_metric=None, clock=None, comparability_state=None, note=missing,
    )
    regime = dict(reading, state="REGIME_BREAK", comparability_state="REGIME_BREAK_NOT_COMPARABLE", note="A regime break.")
    assert _withhold_unevidenced(regime, missing) == dict(regime, primary_metric=None, clock=None)
    backed = dict(reading, evidence_refs=["src-1"])
    assert _withhold_unevidenced(backed, missing) is backed
    absent = dict(reading, state="MISSING", primary_metric=None, clock=None)
    assert _withhold_unevidenced(absent, missing) is absent


# ---------------------------------------------------------------------------
# Point in time: no owner row dated after the knowledge cutoff is read
# ---------------------------------------------------------------------------

# Keys that date the document itself, or when a row holds in the world. A
# report period, an effective date or a business validity may fall after
# the cutoff for a row known before it.
_NOT_KNOWLEDGE_CLOCKS = frozenset({
    "generated_at",
    "knowledge_cutoff",
    "effective_at",
    "business_valid_from",
    "business_valid_to",
    "period_start",
    "period_end",
})
# The owner clocks that say when a row became knowable.
_OWNER_KNOWN_CLOCKS = frozenset({"as_of", "observed_at", "published_at", "retained_at", "evidence_date"})


def _day(offset: int) -> str:
    """The knowledge cutoff's date moved by ``offset`` days, as ISO text."""
    return (_knowledge_cutoff().date() + _dt.timedelta(days=offset)).isoformat()


def _dates_after_the_cutoff(node: object, key: str = "") -> list[tuple[str, str]]:
    """Every (key, value) in ``node`` whose value is a date after the knowledge
    cutoff, except under the keys that date the document or the world."""
    if isinstance(node, dict):
        return [hit for name, value in node.items() for hit in _dates_after_the_cutoff(value, str(name))]
    if isinstance(node, (list, tuple)):
        return [hit for value in node for hit in _dates_after_the_cutoff(value, key)]
    if isinstance(node, str) and key not in _NOT_KNOWLEDGE_CLOCKS and re.match(r"\d{4}-\d{2}-\d{2}", node):
        return [(key, node)] if node[:10] > _day(0) else []
    return []


def _with_every_known_clock(node: object, when: str) -> object:
    """``node`` with every owner clock that says when a row became knowable set to ``when``."""
    if isinstance(node, dict):
        return {
            name: when if name in _OWNER_KNOWN_CLOCKS and isinstance(value, str) else _with_every_known_clock(value, when)
            for name, value in node.items()
        }
    if isinstance(node, list):
        return [_with_every_known_clock(value, when) for value in node]
    return node


def _composed(inputs: FinanceOwnerInputs) -> dict[str, Any]:
    document = compose_finance_projection(inputs, generated_at=_today(), knowledge_cutoff=_knowledge_cutoff())
    validate_contract(CONTRACT_ID, document)
    return document


def _without_digest(document: dict[str, Any]) -> dict[str, Any]:
    return dict(document, snapshot_identity=dict(document["snapshot_identity"], input_digest=None))


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_nothing_dated_past_the_knowledge_cutoff_reaches_the_document(fixture: str) -> None:
    """Move every owner clock that says when a row became knowable to the
    day after the knowledge cutoff. The document validates, and nothing in
    it is dated after the cutoff. The walk finds the moved clocks in the
    owner inputs, so it can see them. Only the valuation anchor used to
    apply the cutoff: the other planes, the company cells, the source
    records and freshness published the moved dates."""
    base = _extended_owner_inputs(fixture)
    late = dataclasses.replace(base, **{
        field.name: _with_every_known_clock(getattr(base, field.name), _day(1))
        for field in dataclasses.fields(base)
    })
    assert _dates_after_the_cutoff(dataclasses.asdict(late)), "the walk found no moved clock"
    assert _dates_after_the_cutoff(_composed(late)) == []


def _one_more_row(where: str, clock: str, when: str) -> tuple[FinanceOwnerInputs, FinanceOwnerInputs]:
    """A fixture, and the same fixture with one more row at ``where``: a copy
    of a row there, dated on the knowledge cutoff, with a value no other row
    carries and ``clock`` set to ``when``. Theme evidence gets a curation
    revision no other row carries, since the fixture's row has no clocks."""
    on = _day(0)
    if where in ("operating cell", "valuation cell"):
        base = _extended_owner_inputs("default")
        packets = copy.deepcopy(dict(base.financial_packets))
        (cell,) = packets["SYN1"]["operating"]["cells"]
        row = dict(cell, evidence_date=on, value=0.77)
        row[clock] = when
        plane = where.split()[0]
        packets["SYN1"].setdefault(plane, {}).setdefault("cells", []).append(row)
        return base, dataclasses.replace(base, financial_packets=packets)
    base = _extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
    if where == "source record":
        row = copy.deepcopy(dict(base.source_records[0]))
        row.update(record_id="src-one-more-row", evidence_ref="src-one-more-row")
        row["source"] = dict(row["source"], published_at=on, observed_at=on, retained_at=on)
        row["source"][clock] = when
        return base, dataclasses.replace(base, source_records=[*base.source_records, row])
    if where == "theme evidence":
        row = {"theme_id": "SYNTHETIC-theme", "curation_revision": "SYNTHETIC-revision-one-more-row",
               "source": {"published_at": on, "observed_at": on, "retained_at": on}}
        row["source"][clock] = when
        return base, dataclasses.replace(base, theme_evidence=[*base.theme_evidence, row])
    if where in ("market", "expectation"):
        field = f"{where}_observations"
        observations = copy.deepcopy(dict(getattr(base, field)))
        row = dict(observations["card_networks"][0], as_of=on, value=77.0)
        row[clock] = when
        observations["card_networks"].append(row)
        return base, dataclasses.replace(base, **{field: observations})
    packets = copy.deepcopy(dict(base.financial_packets))
    (packet,) = packets.values()
    plane = where.split()[0]
    (reading,) = packet[plane]["observations"]
    row = dict(reading, as_of=on)
    row["metric"] = dict(row["metric"], value=77.0)
    row[clock] = when
    packet[plane]["observations"].append(row)
    return base, dataclasses.replace(base, financial_packets=packets)


_ONE_MORE_ROW_CASES = [
    *((where, clock) for where in ("operating observation", "valuation observation", "market", "expectation")
      for clock in ("as_of", "observed_at", "published_at")),
    *((where, clock) for where in ("operating cell", "valuation cell")
      for clock in ("evidence_date", "as_of", "observed_at", "published_at")),
    *((where, clock) for where in ("source record", "theme evidence")
      for clock in ("published_at", "observed_at", "retained_at")),
]


@pytest.mark.parametrize(("where", "clock"), _ONE_MORE_ROW_CASES)
def test_a_row_dated_past_the_knowledge_cutoff_changes_nothing_but_the_digest(where: str, clock: str) -> None:
    """Add one row, dated on the knowledge cutoff but for ``clock``, which
    falls the day after it. The document is the one composed without that
    row, except the input digest, which still covers every row the owner
    supplied. The same row with ``clock`` on the cutoff is read and changes
    the document, so the row is one a reader publishes."""
    base, late = _one_more_row(where, clock, _day(1))
    _, on_cutoff = _one_more_row(where, clock, _day(0))
    before = _composed(base)
    after = _composed(late)
    assert _without_digest(after) == _without_digest(before)
    assert after["snapshot_identity"]["input_digest"] != before["snapshot_identity"]["input_digest"]
    assert _without_digest(_composed(on_cutoff)) != _without_digest(before)


def test_a_row_known_by_the_cutoff_is_read_however_far_ahead_it_holds() -> None:
    """A row can be known before the time it holds for. An operating
    observation known on the cutoff but effective a month after it is
    published with that effective_at, and so is a material change. Only the
    clocks that say when a row became knowable bind to the cutoff."""
    ahead = _day(30)
    base = _extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
    packets = copy.deepcopy(dict(base.financial_packets))
    (packet,) = packets.values()
    (reading,) = packet["operating"]["observations"]
    reading["effective_at"] = ahead
    document = _composed(dataclasses.replace(base, financial_packets=packets))
    operating = next(s for s in document["slices"] if s["slice_id"] == "card_networks")["rerating"]["operating"]
    assert operating["primary_metric"]["value"] == reading["metric"]["value"], operating
    assert operating["clock"]["effective_at"] == ahead, operating

    base = _extended_owner_inputs("PRICE_UP_CAUSAL_EVENT_EFFECT_UNPROVEN")
    records = copy.deepcopy(list(base.source_records))
    records[0]["material_change"]["effective_at"] = ahead
    document = _composed(dataclasses.replace(base, source_records=records))
    (change,) = document["material_changes"]
    assert change["event_clock"]["effective_at"] == ahead, change


# The knowledge cutoff as an instant late on its day, written in UTC and in a
# zone whose calendar date is already the next day.
_CUTOFF_INSTANT = _dt.datetime(2026, 9, 24, 20, 0, tzinfo=_dt.timezone.utc)
_CUTOFF_WRITTEN = {
    "utc": _CUTOFF_INSTANT,
    "utc+8": _CUTOFF_INSTANT.astimezone(_dt.timezone(_dt.timedelta(hours=8))),
}
# A market row's as_of, and whether the row is read at that cutoff.
_CLOCKS_AT_THE_CUTOFF_INSTANT = [
    ("2026-09-24", True),                  # the start of the cutoff's day in UTC
    ("2026-09-24T19:00:00Z", True),
    ("2026-09-24T12:00:00-07:00", True),   # 19:00 UTC
    ("2026-09-24T21:00:00Z", False),
    ("2026-09-24T20:30:00-08:00", False),  # 04:30 UTC the next day, written on the cutoff's date
    ("2026-09-25T01:00:00+08:00", False),  # 17:00 UTC, but published as the next day's date
    ("2026-09-25Tlate", False),            # no instant, and published as the next day's date
]


@pytest.mark.parametrize("written", sorted(_CUTOFF_WRITTEN))
@pytest.mark.parametrize(("as_of", "read"), _CLOCKS_AT_THE_CUTOFF_INSTANT)
def test_the_knowledge_cutoff_is_an_instant_no_published_date_passes(written: str, as_of: str, read: bool) -> None:
    """The shared contracts read the published knowledge_cutoff as an
    instant, and a published date as the start of its day in UTC. So a row
    is read only when its clock's instant is not past the cutoff instant and
    the date published for it is not past the cutoff's date in UTC. A time
    written late on the cutoff's date in a zone behind UTC is withheld, and
    so is a time written early on the next day in a zone ahead of it, whose
    instant is before the cutoff. The outcome does not depend on the zone
    the cutoff itself is written in."""
    cutoff = _CUTOFF_WRITTEN[written]

    def composed(inputs: FinanceOwnerInputs) -> dict[str, Any]:
        document = compose_finance_projection(inputs, generated_at=cutoff, knowledge_cutoff=cutoff)
        validate_contract(CONTRACT_ID, document)
        return document

    base, one_more = _one_more_row("market", "as_of", as_of)
    before, after = composed(base), composed(one_more)
    assert after["snapshot_identity"]["input_digest"] != before["snapshot_identity"]["input_digest"]
    assert (_without_digest(after) != _without_digest(before)) is read


def _no_dated_evidence() -> FinanceOwnerInputs:
    return FinanceOwnerInputs(
        sector_dossier=None,
        theme_evidence=[],
        financial_packets={},
        expectation_observations={},
        market_observations={},
        basket_context={},
        macro_context={},
        identity_bindings={},
        source_records=[],
        regime_breaks=[],
        slice_catalog=_base_slice_catalog(),
        rights_snapshot={},
    )


@pytest.mark.parametrize("inputs", ["default", "no dated evidence"])
def test_the_zone_a_knowledge_cutoff_is_written_in_changes_only_the_cutoff_published(inputs: str) -> None:
    """The dates the document derives from the knowledge cutoff (staleness,
    and the bound on common_as_of) are the cutoff's date in UTC, the date
    the shared contracts read for it. The same cutoff instant, written in
    UTC and in UTC+8, where its calendar date is already the next day, gives
    documents that differ only in the knowledge_cutoff they publish. With no
    dated evidence, common_as_of is the cutoff's date in UTC. It used to be
    the next day's date, which the contracts read as the start of that day
    in UTC, after the cutoff, and the contract accepted the document."""
    owner_inputs = _no_dated_evidence() if inputs == "no dated evidence" else _default_8slice_inputs()
    documents = {}
    for written, cutoff in _CUTOFF_WRITTEN.items():
        document = compose_finance_projection(owner_inputs, generated_at=_CUTOFF_INSTANT, knowledge_cutoff=cutoff)
        validate_contract(CONTRACT_ID, document)
        documents[written] = document
    assert documents["utc+8"]["knowledge_cutoff"] != documents["utc"]["knowledge_cutoff"]
    assert dict(documents["utc+8"], knowledge_cutoff=None) == dict(documents["utc"], knowledge_cutoff=None)
    if inputs == "no dated evidence":
        assert documents["utc+8"]["common_as_of"] == _CUTOFF_INSTANT.date().isoformat()


# Cutoffs that name no instant: a time of day, and aware times whose instant
# in UTC falls outside the range of a datetime.
_CUTOFFS_WITHOUT_AN_INSTANT = {
    "a time of day": _dt.time(20, 0),
    "an offset past year 9999": _dt.datetime(9999, 12, 31, 23, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=-5))),
    "an offset before year one": _dt.datetime(1, 1, 1, 1, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=5))),
}


@pytest.mark.parametrize("cutoff", sorted(_CUTOFFS_WITHOUT_AN_INSTANT))
def test_a_knowledge_cutoff_that_names_no_instant_is_refused(cutoff: str) -> None:
    """The shared contracts read the published knowledge_cutoff as an
    instant. A cutoff that names none cannot say which rows were known, so
    the composer refuses it with a ValueError that names it, never an error
    from inside the gate, and never a document whose point in time the
    contracts cannot read."""
    with pytest.raises(ValueError, match="knowledge_cutoff names no instant"):
        compose_finance_projection(
            _default_8slice_inputs(), generated_at=_today(), knowledge_cutoff=_CUTOFFS_WITHOUT_AN_INSTANT[cutoff],
        )


# Clocks that name no instant: a time of day with no date, and offsets that
# carry a time outside the range of a datetime. A market row's as_of, and
# whether the date read from it places the row after the cutoff.
_CLOCKS_WITHOUT_AN_INSTANT = {
    "a time of day": (_dt.time(12, 0), False),
    "an offset before year one": ("0001-01-01T00:00:00+05:00", False),
    "an aware datetime before year one": (_dt.datetime(1, 1, 1, tzinfo=_dt.timezone(_dt.timedelta(hours=5))), False),
    "an offset past year 9999": ("9999-12-31T23:59:59-05:00", True),
}


@pytest.mark.parametrize("clock", sorted(_CLOCKS_WITHOUT_AN_INSTANT))
def test_a_clock_with_no_instant_never_stops_the_composer(clock: str) -> None:
    """A clock the gate cannot turn into an instant is read by its date
    alone, and the composer still returns a document the contract accepts.
    A row whose date is after the cutoff is withheld: it changes nothing but
    the digest. Any other row reaches the readers, whose rule for an undated
    or an old row is unchanged."""
    as_of, after_the_cutoff = _CLOCKS_WITHOUT_AN_INSTANT[clock]
    base, one_more = _one_more_row("market", "as_of", as_of)
    before, after = _composed(base), _composed(one_more)
    assert after["snapshot_identity"]["input_digest"] != before["snapshot_identity"]["input_digest"]
    if after_the_cutoff:
        assert _without_digest(after) == _without_digest(before)


def test_rows_in_any_sequence_are_held_to_the_knowledge_cutoff() -> None:
    """The gate holds every sequence of rows a reader iterates to the
    cutoff, not only a list or a tuple. With the expectation rows in a
    deque, one more row dated the day after the cutoff changes nothing but
    the digest, and the same row on the cutoff changes the document."""

    def in_a_deque(inputs: FinanceOwnerInputs) -> FinanceOwnerInputs:
        observations = {
            slice_id: collections.deque(rows) for slice_id, rows in inputs.expectation_observations.items()
        }
        return dataclasses.replace(inputs, expectation_observations=observations)

    base, late = _one_more_row("expectation", "as_of", _day(1))
    _, on_cutoff = _one_more_row("expectation", "as_of", _day(0))
    before = _composed(in_a_deque(base))
    after = _composed(in_a_deque(late))
    assert _without_digest(after) == _without_digest(before)
    assert after["snapshot_identity"]["input_digest"] != before["snapshot_identity"]["input_digest"]
    assert _without_digest(_composed(in_a_deque(on_cutoff))) != _without_digest(before)


# The input receipt that answers for each owner input a reader can publish rows from.
_RECEIPT_FOR_INPUT = {
    "financial_packets": "financial_intelligence",
    "expectation_observations": "expectations_revisions",
    "market_observations": "market_data",
    "theme_evidence": "theme_graph",
    "source_records": "private_publication",
}


@pytest.mark.parametrize("field", sorted(_RECEIPT_FOR_INPUT))
def test_an_input_the_knowledge_cutoff_withholds_is_received_as_degraded(field: str) -> None:
    """An input receipt reads READ only while the document holds rows from
    that input. Move every knowledge clock of one input a day past the
    cutoff: that input's receipt turns from READ to DEGRADED, and no other
    receipt changes. The gate keeps the keyed maps of packets, expectation
    and market rows, so their receipts used to read READ over an input the
    document held no row of."""
    base = _extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
    # The fixture's theme evidence has no clocks; give it its source's.
    base = dataclasses.replace(base, theme_evidence=[
        dict(row, source={"retained_at": _day(0)}) for row in base.theme_evidence
    ])
    late = dataclasses.replace(base, **{field: _with_every_known_clock(getattr(base, field), _day(1))})

    def receipts(inputs: FinanceOwnerInputs) -> dict[str, str]:
        return {receipt["owner"]: receipt["state"] for receipt in _composed(inputs)["input_receipts"]}

    before, after = receipts(base), receipts(late)
    owner = _RECEIPT_FOR_INPUT[field]
    assert before[owner] == "READ", before
    assert after[owner] == "DEGRADED", after
    assert {o: s for o, s in after.items() if o != owner} == {o: s for o, s in before.items() if o != owner}


# ---------------------------------------------------------------------------
# Every owner container is read by what it holds.
# ---------------------------------------------------------------------------


class _RowsWithNoLength:
    """A sequence of rows that can be read again but has no length."""

    def __init__(self, rows: Any) -> None:
        self._rows = list(rows)

    def __iter__(self) -> Any:
        return iter(self._rows)


_CONTAINERS = {
    "a generator": lambda rows: (row for row in list(rows)),
    "a deque": collections.deque,
    "an iterable with no length": _RowsWithNoLength,
}


def _gated_rows_in(inputs: FinanceOwnerInputs, field: str, container: Any) -> FinanceOwnerInputs:
    """``inputs`` with every sequence of rows of ``field`` the knowledge gate reads held by ``container``."""
    value = getattr(inputs, field)
    if field in ("theme_evidence", "source_records"):
        return dataclasses.replace(inputs, **{field: container(value)})
    if field in ("expectation_observations", "market_observations"):
        return dataclasses.replace(inputs, **{field: {slice_id: container(rows) for slice_id, rows in value.items()}})
    packets = copy.deepcopy(dict(value))
    for packet in packets.values():
        for plane in ("operating", "valuation"):
            block = packet.get(plane)
            for key in ("observations", "cells"):
                if isinstance(block, dict) and key in block:
                    block[key] = container(block[key])
    return dataclasses.replace(inputs, financial_packets=packets)


@pytest.mark.parametrize("container", sorted(_CONTAINERS))
@pytest.mark.parametrize("field", sorted(_RECEIPT_FOR_INPUT))
def test_an_input_whose_every_row_the_cutoff_withholds_is_degraded_whatever_holds_its_rows(field: str, container: str) -> None:
    """The receipts answer from the rows the gate read and kept, so a
    sequence of rows need not have a length. With the rows of one input in
    a generator, a deque or an iterable with no length, moving every
    knowledge clock of that input a day past the cutoff turns its receipt
    from READ to DEGRADED, as it does for a list. The receipts used to count
    rows with len(), so a generator whose every row the cutoff withheld was
    received as READ."""
    base = _extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
    # The fixture's theme evidence has no clocks; give it its source's.
    base = dataclasses.replace(base, theme_evidence=[
        dict(row, source={"retained_at": _day(0)}) for row in base.theme_evidence
    ])
    late = dataclasses.replace(base, **{field: _with_every_known_clock(getattr(base, field), _day(1))})

    def receipt(inputs: FinanceOwnerInputs) -> str:
        document = _composed(_gated_rows_in(inputs, field, _CONTAINERS[container]))
        return next(r["state"] for r in document["input_receipts"] if r["owner"] == _RECEIPT_FOR_INPUT[field])

    assert (receipt(base), receipt(late)) == ("READ", "DEGRADED")


def _as_generators(node: object) -> object:
    """``node`` with every list in it, however deep, a generator of the same items."""
    if isinstance(node, dict):
        return {name: _as_generators(value) for name, value in node.items()}
    if isinstance(node, list):
        return (_as_generators(value) for value in node)
    return node


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_owner_inputs_in_generators_compose_the_document_their_lists_compose(fixture: str) -> None:
    """A one-shot iterator is read once, where the owner inputs enter. With
    every list in the owner inputs, however deep, turned into a generator of
    the same items, the composer returns the same document, input digest
    included. The knowledge gate used to read a generator before the
    digest did: theme evidence in a generator had the digest of no theme
    evidence, and a generator in a packet hashed by its address."""
    base = _extended_owner_inputs(fixture)
    generated = dataclasses.replace(base, **{
        field.name: _as_generators(getattr(base, field.name)) for field in dataclasses.fields(base)
    })
    assert _composed(generated) == _composed(base)


@pytest.mark.parametrize("fixture", _FENCE_FIXTURES)
def test_rows_the_gate_reads_in_deques_compose_the_document_their_lists_compose(fixture: str) -> None:
    """The input digest hashes what a container holds, never the container.
    With every sequence of rows the knowledge gate reads held in a deque,
    the composer returns the same document, input digest included. A deque
    used to hash by its repr, so the same rows had one digest in a list and
    another in a deque. (Only the gate reads any sequence of rows: a deque
    of references elsewhere is read by its reader's own rule.)"""
    base = _extended_owner_inputs(fixture)
    in_deques = base
    for field in _RECEIPT_FOR_INPUT:
        in_deques = _gated_rows_in(in_deques, field, collections.deque)
    assert _composed(in_deques) == _composed(base)


_DIGEST_OF_A_ROW_HOLDING_A_SET = """
import dataclasses
import tests.test_finance_intelligence_projection as tp
base = tp._extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
first, *rest = base.theme_evidence
tagged = dict(first, synthetic_tags={f"SYNTHETIC-tag-{i}" for i in range(12)})
document = tp._composed(dataclasses.replace(base, theme_evidence=[tagged, *rest]))
print(document["snapshot_identity"]["input_digest"])
"""


def test_the_input_digest_of_a_set_does_not_depend_on_the_hash_seed() -> None:
    """A set is hashed in the order of its members' JSON. Composed in three
    processes with three hash seeds, an owner row that holds a set of text
    has one input digest. A set used to hash in its iteration order, which
    the hash seed changes, so one snapshot had a digest per process."""
    digests = set()
    for seed in ("1", "2", "3"):
        result = subprocess.run(
            [sys.executable, "-c", _DIGEST_OF_A_ROW_HOLDING_A_SET],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        digests.add(result.stdout.strip())
    assert len(digests) == 1, digests


def test_an_owner_mapping_with_keys_of_two_types_never_stops_the_composer() -> None:
    """A mapping whose keys are not all text is hashed as its [key, value]
    pairs, each key written as the JSON it is. An owner row holding one
    composes a document the contract accepts, and its digest tells a key
    that is a number from the same key written as text, whether the other
    key is text or a number. The digest used to sort the keys before
    writing them, and the sort raised TypeError."""
    base = _extended_owner_inputs("EARNINGS_UP_P_E_DOWN")
    first, *rest = base.theme_evidence

    def digest(mapping: dict[Any, str]) -> str:
        row = dict(first, synthetic_map=mapping)
        document = _composed(dataclasses.replace(base, theme_evidence=[row, *rest]))
        return document["snapshot_identity"]["input_digest"]

    assert digest({1: "SYNTHETIC-a", "b": "SYNTHETIC-b"}) != digest({"1": "SYNTHETIC-a", "b": "SYNTHETIC-b"})
    assert digest({1: "SYNTHETIC-a", 2: "SYNTHETIC-b"}) != digest({"1": "SYNTHETIC-a", 2: "SYNTHETIC-b"})
