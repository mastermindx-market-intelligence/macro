"""SYNTHETIC result-to-cash test fixtures; test-only, never product code.

The comparison contract is exactly ``receipt_id`` (str), ``purpose`` (str),
``operand_refs`` (ordered owner refs), ``checked`` with ``basis``,
``currency``, ``scale``, ``duration``, ``perimeter``, ``definition`` and
``source_mode`` booleans, ``unknowns`` (field names), and ``transformations``
whose entries each contain ``kind`` (str), ``factor`` (decimal text) and
``lineage`` (str).  It precedes T04's production constructor.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from engine.earnings_narrative.private_publication import (
    _put_verified,
    validate_private_pointer,
)
from engine.company_intelligence.documents import ABSENCE_REASONS
from engine.research_vault.r2_store import LocalStore


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "industrials_result_cash"
FIXTURE_NAMES = frozenset(path.stem for path in FIXTURE_DIR.glob("*.json"))
_COMPARISON_PURPOSES = frozenset(
    {"same_period", "year_over_year", "final_vs_preview", "segment_bridge", "rollforward"}
)


def load_case(name: str) -> dict[str, Any]:
    """Return a fresh synthetic fixture and refuse every non-synthetic value."""
    # Mirrors Semiconductor B's unmerged test loader: fixture trust is explicit.
    if name not in FIXTURE_NAMES:
        raise KeyError(f"unknown fixture {name!r}; known names: {', '.join(sorted(FIXTURE_NAMES))}")
    value = json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("synthetic") is not True:
        raise ValueError("fixture must explicitly be synthetic")
    return deepcopy(value)


case = load_case


def cell(value: str, **overrides: Any) -> dict[str, Any]:
    """Build one native-shaped synthetic financial operand."""
    if isinstance(value, (float, bool)) or not isinstance(value, str):
        raise TypeError("cell value must be decimal text")
    try:
        Decimal(value)
    except InvalidOperation as exc:
        raise TypeError("cell value must be decimal text") from exc
    operand: dict[str, Any] = {
        "owner_ref": "synthetic:cell:default",
        "revision": "r1",
        "digest": "a" * 64,
        "semantic_selector": {"statement": "cash-flow", "row": "operating-cash", "column": "quarter"},
        "value": value,
        "metric": "operating_cash_flow",
        "unit": "USD_millions",
        "scale": 1,
        "currency": "USD",
        "stock_or_flow": "flow",
        "period": {"start": "2026-04-03", "end": "2026-07-03", "fiscal_label": "FY2026 Q2", "duration": "quarter"},
        "business_dimensions": {"segment": "testing"},
        "basis": {"accounting": "GAAP", "recast": "as_reported"},
        "source_mode": "release",
        "quality": {"rights_profile": "rp_public_primary_v1", "rights_state": "public_primary", "definition": "cash_generated_by_operations"},
    }
    operand.update(overrides)
    return operand


def typed_absence(reason: str) -> dict[str, str]:
    """Return the owner's only allowed typed-absence shape."""
    if reason not in ABSENCE_REASONS:
        raise ValueError("unknown typed absence reason")
    return {"absence": reason}


def comparison(purpose: str, cells: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the closed T04 qualification receipt without qualifying meaning."""
    if purpose not in _COMPARISON_PURPOSES:
        raise ValueError(f"unknown comparison purpose: {purpose}")
    operands = list(cells)
    if not operands:
        raise ValueError("comparison requires operands")
    refs: list[str] = []
    for operand in operands:
        owner_ref = operand.get("owner_ref")
        if not isinstance(owner_ref, str) or not owner_ref:
            raise TypeError("comparison operand lacks owner_ref")
        refs.append(owner_ref)
    return {
        "receipt_id": "synthetic:comparison:1",
        "purpose": purpose,
        "operand_refs": refs,
        "checked": {name: True for name in ("basis", "currency", "scale", "duration", "perimeter", "definition", "source_mode")},
        "unknowns": [],
        "transformations": [],
    }


def dossier_inputs() -> dict[str, Any]:
    """Return a complete invented event, source and financial bundle."""
    return {
        "synthetic": True,
        "schema": {"role": "synthetic.financial-dossier-input/v1"},
        "subject": {"event_ref": "synthetic:event:flow-q2", "identity": shared_identity()},
        "sources": [case("service_net_gross")["sources"][0]],
        "cells": [cell("21", owner_ref="synthetic:cell:service-net")],
        "dependencies": {"refs": ["synthetic:cell:service-net"], "digests": ["a" * 64]},
        "rights": {"release": {"status": "candidate"}, "private": {"status": "candidate"}},
        "narrative": {"reviewed": True},
        "authority": {"rank": False, "gate": False, "size": False, "originate": False, "entry": False},
    }


def publication_harness() -> Any:
    """Return the six-method synthetic owner-function harness."""
    return _PublicationHarness()


def shared_identity() -> dict[str, Any]:
    return {
        "company_id": "synthetic:northgate",
        "display_name": "Northgate Testing Services",
        "fiscal_year_end_month": 12,
        "reporting_currency": "USD",
        "listings": [],
        "issuer_kind": "industrial",
        "external_ids": {"cik": "0000987654"},
    }


class _MemoryPublicationStore(LocalStore):
    def __init__(self) -> None:
        super().__init__(Path(__file__).resolve().parent / ".industrials_publication_memory")
        self.read_count = 0

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int) -> bytes | None:
        self.read_count += 1
        return super().get_bytes_strict_bounded(key, maximum_bytes)


class _SyntheticClient:
    def get(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "unavailable", "reason": "route_unbound", "status_code": None}

    def post(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"status": "unavailable", "reason": "route_unbound", "status_code": None}


class _PublicationHarness:
    def __init__(self) -> None:
        self.store = _MemoryPublicationStore()
        self.read_count = 0

    def run_refresh(self, _changes: Mapping[str, str], fail_sources: Iterable[str] = ()) -> dict[str, Any]:
        del fail_sources
        return {"status": "unavailable", "reason": "refresh_seam_unbound", "needed": "profile=/issuer= discovery binding"}

    def members(self) -> set[str]:
        return set()

    def get(self, slug: str) -> dict[str, Any]:
        return {"slug": slug, "status": "unavailable", "reason": "refresh_seam_unbound"}

    def publish(self, changes: Mapping[str, Any]) -> dict[str, Any]:
        self.read_count = self.store.read_count
        del changes
        # Bind one real owner publication primitive while the route remains
        # intentionally unbound; no fake success is possible from this harness.
        body = b'{"synthetic":true}'
        _put_verified(
            self.store,
            key="synthetic/industrials-result-cash/binding.json",
            body=body,
            maximum=len(body) * 2,
        )
        validate_private_pointer(
            {
                "schema": "earnings.private_pointer/v1",
                "generation_id": "earnpriv_" + "0" * 32,
                "manifest_key": "earnings-private/manifests/" + "earnpriv_" + "0" * 32 + ".json",
                "manifest_sha256": "0" * 64,
                "manifest_bytes": 2,
                "published_at": "2026-09-24T00:00:00Z",
            }
        )
        return {
            "status": "unavailable",
            "reason": "route_unbound",
            "owner_function": "_put_verified",
        }

    def client(self, entitled: bool) -> _SyntheticClient:
        del entitled
        return _SyntheticClient()
