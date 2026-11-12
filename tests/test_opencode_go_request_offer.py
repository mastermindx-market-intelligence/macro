"""Request-time offer checks consume existing observations; no live permission."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from engine import provider_subscription_catalog_opencode as go
from engine import provider_subscription_guard_opencode as guard

NOW = "2026-09-14T18:00:00+00:00"
LATER = "2026-09-14T18:30:00+00:00"
FIXTURES = Path(__file__).parent / "fixtures" / "opencode_go"


def metadata():
    return go.Metadata(
        go.parse_models(json.loads((FIXTURES / "inventory.json").read_text()), observed_at=NOW),
        go.parse_terms((FIXTURES / "terms.mdx").read_text(), observed_at=NOW),
    )


def args(value, model="glm-5.3-flash"):
    row = next(m for m in value.terms.models if m.model_id == model)
    return dict(model_id=model, protocol=row.protocol, now=NOW,
                expected_offer_digest=guard.model_offer_digest(value, model),
                expected_policy_digest=value.terms.policy_digest,
                review_valid_until=LATER)


def test_current_reviewed_facts_pass_without_mutating_observations():
    value = metadata(); before = repr(value)
    assert guard.check_request_offer(value, **args(value)) is None
    assert repr(value) == before


@pytest.mark.parametrize("time, reason", [
    (LATER, "OFFER_REVIEW_EXPIRED"),
    ("2026-09-14T17:59:59Z", "INVENTORY_NOT_FRESH"),
    ("2026-09-14T19:00:00Z", "INVENTORY_NOT_FRESH"),
])
def test_request_clock_rechecks_existing_evidence(time, reason):
    value = metadata(); kw = args(value); kw["now"] = time
    with pytest.raises(go.GoCatalogError, match=reason):
        guard.check_request_offer(value, **kw)


def test_new_inventory_does_not_freshen_old_terms():
    value = metadata(); kw = args(value)
    value = replace(value, terms=replace(value.terms, observed_at="2026-09-14T11:59:59Z"))
    with pytest.raises(go.GoCatalogError, match="TERMS_NOT_FRESH"):
        guard.check_request_offer(value, **kw)


def test_unrelated_model_listing_does_not_interrupt_existing_offer():
    value = metadata(); kw = args(value)
    newer = replace(value, inventory=replace(value.inventory,
        model_ids=value.inventory.model_ids + ("synthetic-new-model",)))
    assert guard.model_offer_digest(newer, kw["model_id"]) == kw["expected_offer_digest"]
    guard.check_request_offer(newer, **kw)


def test_removed_model_is_not_silently_substituted():
    value = metadata(); kw = args(value)
    value = replace(value, inventory=replace(value.inventory,
        model_ids=tuple(m for m in value.inventory.model_ids if m != kw["model_id"])))
    with pytest.raises(go.GoCatalogError, match="MODEL_NOT_LISTED"):
        guard.check_request_offer(value, **kw)


def test_rate_change_invalidates_quote_but_does_not_create_account_quota():
    value = metadata(); kw = args(value)
    models = tuple(replace(m, rates=tuple(replace(r, input="999") for r in m.rates))
                   if m.model_id == kw["model_id"] else m for m in value.terms.models)
    changed = replace(value, terms=replace(value.terms, models=models))
    with pytest.raises(go.GoCatalogError, match="OFFER_CHANGED_REQUOTE_REQUIRED"):
        guard.check_request_offer(changed, **kw)


@pytest.mark.parametrize("change", ["policy", "protocol", "fractions", "conditions"])
def test_material_interpretation_drift_blocks_next_request(change):
    value = metadata(); kw = args(value)
    if change == "policy":
        value = replace(value, terms=replace(value.terms, policy_digest="f" * 64))
    elif change == "protocol":
        kw["protocol"] = "responses"
    elif change == "fractions":
        value = replace(value, terms=replace(value.terms, horizon_fractions=("0.1", "0.5", "1")))
    else:
        value = replace(value, terms=replace(value.terms, economic_conditions_digest="f" * 64))
    with pytest.raises(go.GoCatalogError):
        guard.check_request_offer(value, **kw)


@pytest.mark.parametrize("model", ["muse-spark-1.3-contributor", "minimax-m2.5"])
def test_training_or_unknown_privacy_cannot_be_fixed_by_matching_digests(model):
    value = metadata()
    with pytest.raises(go.GoCatalogError, match="PRIVATE_DATA_POLICY_UNSATISFIED"):
        guard.check_request_offer(value, **args(value, model))


def test_promotion_and_retention_need_explicit_unexpired_owner_deadlines():
    value = metadata(); kw = args(value, "deepseek-v4.1-flash")
    with pytest.raises(go.GoCatalogError, match="PROMOTION_REVALIDATION_REQUIRED"):
        guard.check_request_offer(value, **kw)
    kw["promotion_valid_until"] = LATER
    with pytest.raises(go.GoCatalogError, match="CONDITIONAL_RETENTION_REVALIDATION_REQUIRED"):
        guard.check_request_offer(value, **kw)
    kw["retention_valid_until"] = LATER
    guard.check_request_offer(value, **kw)
    kw["promotion_valid_until"] = NOW
    with pytest.raises(go.GoCatalogError, match="PROMOTION_REVALIDATION_REQUIRED"):
        guard.check_request_offer(value, **kw)
    kw["promotion_valid_until"] = LATER
    kw["retention_valid_until"] = NOW
    with pytest.raises(go.GoCatalogError, match="CONDITIONAL_RETENTION_REVALIDATION_REQUIRED"):
        guard.check_request_offer(value, **kw)


@pytest.mark.parametrize("key, val", [("expected_offer_digest", ""),
    ("expected_policy_digest", None), ("model_id", "bad id"),
    ("protocol", "unknown"), ("review_valid_until", "not-a-date")])
def test_invalid_or_missing_review_inputs_fail_closed(key, val):
    value = metadata(); kw = args(value); kw[key] = val
    with pytest.raises(go.GoCatalogError):
        guard.check_request_offer(value, **kw)
