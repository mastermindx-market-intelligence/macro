"""Tests for ``engine.sector_intelligence.finance_projection``.

All numbers, issuers and source URIs in this module are SYNTHETIC. No value
is copied from the live research carrier or from the schema fixture.
"""

from __future__ import annotations

import builtins
import copy
import dataclasses
import datetime as _dt
import functools
import hashlib
import json
import re
import socket as _socket
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
