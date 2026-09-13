"""Validated static subscription-plan semantics for shared provider control.

This module is deliberately *not* live capacity truth.  It records provider-published
plan shapes so Provider Control can interpret authenticated usage observations once a
provider slot is enrolled.  Unknown product/tier selection yields no inferred quota.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "mastermind.provider_subscription_plans/v1"
DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "config" / "provider_subscription_plans.v1.json"
_ALLOWED_HORIZONS = {"five_hour", "weekly", "monthly", "billing_cycle", "daily", "custom"}
_ALLOWED_WINDOWS = {"rolling", "fixed", "billing_cycle", "instant", "unknown"}
_ALLOWED_METRICS = {"prompts", "requests", "credits", "tokens", "mcp_web_calls", "m2_7_requests", "m2_7_highspeed_requests"}


class SubscriptionPlanError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class PlanSelection:
    provider: str
    product: str
    tier: str | None
    known: bool
    limits: tuple[Mapping[str, Any], ...]
    telemetry: Mapping[str, Any] | None
    reason: str | None = None
    usage_policy: Mapping[str, Any] | None = None


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or not value.replace("_", "").isalnum():
        raise SubscriptionPlanError(f"invalid {label}: {value!r}")
    return value


def _validate_limit(row: Any, *, reference: bool = False) -> None:
    if not isinstance(row, Mapping):
        raise SubscriptionPlanError("limit must be a mapping")
    horizon = row.get("horizon")
    metric = row.get("metric")
    if horizon not in _ALLOWED_HORIZONS:
        raise SubscriptionPlanError(f"unsupported quota horizon {horizon!r}")
    if metric not in _ALLOWED_METRICS:
        raise SubscriptionPlanError(f"unsupported quota metric {metric!r}")
    limit = row.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit <= 0:
        raise SubscriptionPlanError("quota limit must be positive")
    if not reference and row.get("window_type") not in _ALLOWED_WINDOWS:
        raise SubscriptionPlanError("authoritative limit requires a supported window_type")
    if row.get("enforced") is False and not row.get("temporary_policy"):
        raise SubscriptionPlanError("unenforced limit must identify temporary policy")


def validate_catalog(document: Any) -> Mapping[str, Any]:
    if not isinstance(document, Mapping) or document.get("schema") != SCHEMA:
        raise SubscriptionPlanError("unsupported subscription-plan catalog schema")
    if document.get("unknown_selection_policy") != "NO_CAPACITY_INFERENCE":
        raise SubscriptionPlanError("unknown plan selection must fail closed")
    providers = document.get("providers")
    if not isinstance(providers, Mapping) or not providers:
        raise SubscriptionPlanError("providers are required")
    for provider_name, provider in providers.items():
        _require_id(provider_name, "provider id")
        if not isinstance(provider, Mapping) or not isinstance(provider.get("products"), Mapping):
            raise SubscriptionPlanError(f"provider {provider_name!r} requires products")
        for product_name, product in provider["products"].items():
            _require_id(product_name, "product id")
            if not isinstance(product, Mapping) or not isinstance(product.get("tiers"), Mapping):
                raise SubscriptionPlanError(f"product {product_name!r} requires tiers")
            if not product["tiers"]:
                raise SubscriptionPlanError(f"product {product_name!r} has no tiers")
            telemetry = product.get("telemetry")
            if telemetry is not None and (not isinstance(telemetry, Mapping) or not telemetry.get("kind")):
                raise SubscriptionPlanError(f"product {product_name!r} has invalid telemetry")
            usage_policy = product.get("usage_policy")
            if usage_policy is not None:
                if not isinstance(usage_policy, Mapping) or not usage_policy:
                    raise SubscriptionPlanError(f"product {product_name!r} has invalid usage policy")
                allowed_policy = {
                    "interactive_only", "interactive_tool_use", "supported_tool_required",
                    "background_automation_allowed", "production_backend_allowed",
                    "single_user_only", "payg_recommended_for_production",
                }
                if set(usage_policy) - allowed_policy or any(type(value) is not bool for value in usage_policy.values()):
                    raise SubscriptionPlanError(f"product {product_name!r} has invalid usage policy")
            aliases: dict[str, str] = {}
            for tier_name, tier in product["tiers"].items():
                _require_id(tier_name, "tier id")
                if not isinstance(tier, Mapping) or not isinstance(tier.get("limits"), list):
                    raise SubscriptionPlanError(f"tier {tier_name!r} requires limits")
                for row in tier["limits"]:
                    _validate_limit(row)
                for row in tier.get("reference_limits", []):
                    _validate_limit(row, reference=True)
                for alias in tier.get("aliases", []):
                    alias = _require_id(alias, "tier alias")
                    if alias in product["tiers"] or alias in aliases:
                        raise SubscriptionPlanError(f"duplicate tier alias {alias!r}")
                    aliases[alias] = tier_name
    return document


def load_catalog(path: Path | str = DEFAULT_CATALOG) -> Mapping[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return validate_catalog(json.load(handle))


def resolve_plan(provider: str, product: str, tier: str | None, *, catalog: Mapping[str, Any] | None = None) -> PlanSelection:
    document = validate_catalog(catalog) if catalog is not None else load_catalog()
    provider_key = _require_id(provider.strip().lower(), "provider id")
    product_key = _require_id(product.strip().lower(), "product id")
    providers = document["providers"]
    provider_row = providers.get(provider_key)
    if not isinstance(provider_row, Mapping):
        return PlanSelection(provider_key, product_key, tier, False, (), None, "UNKNOWN_PROVIDER")
    product_row = provider_row["products"].get(product_key)
    if not isinstance(product_row, Mapping):
        return PlanSelection(provider_key, product_key, tier, False, (), None, "UNKNOWN_PRODUCT")
    telemetry = product_row.get("telemetry")
    usage_policy = product_row.get("usage_policy")
    if tier is None or not str(tier).strip():
        return PlanSelection(
            provider_key, product_key, None, False, (), telemetry, "UNKNOWN_TIER", usage_policy
        )
    tier_key = _require_id(str(tier).strip().lower(), "tier id")
    tiers = product_row["tiers"]
    selected = tiers.get(tier_key)
    canonical = tier_key
    if selected is None:
        for candidate, candidate_row in tiers.items():
            if tier_key in candidate_row.get("aliases", []):
                canonical, selected = candidate, candidate_row
                break
    if not isinstance(selected, Mapping):
        return PlanSelection(
            provider_key, product_key, tier_key, False, (), telemetry, "UNKNOWN_TIER", usage_policy
        )
    return PlanSelection(
        provider_key, product_key, canonical, True, tuple(selected["limits"]),
        telemetry, None, usage_policy
    )


__all__ = ["DEFAULT_CATALOG", "PlanSelection", "SCHEMA", "SubscriptionPlanError", "load_catalog", "resolve_plan", "validate_catalog"]
