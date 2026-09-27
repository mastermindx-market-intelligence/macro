"""Tests for ``engine.sector_intelligence.finance_projection``.

All numbers, issuers and source URIs in this module are SYNTHETIC. No value
is copied from the live research carrier or from the schema fixture.
"""

from __future__ import annotations

import builtins
import datetime as _dt
import hashlib
import json
import re
import socket as _socket
import time as _time
from typing import Any

import pytest

from engine.sector_intelligence.contracts import validate_contract
from engine.sector_intelligence.finance_projection import (
    FinanceOwnerInputs,
    _FINANCE_SLICE_IDS,
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

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "rank" and node is authority_block:
                    pass
                else:
                    assert forbidden.fullmatch(key) is None, key
                walk(child)
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(document)
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
