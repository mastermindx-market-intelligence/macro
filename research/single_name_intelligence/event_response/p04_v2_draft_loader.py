"""SNI-local DRAFT loader/validator for the P04 v2 preregistration contract.

DRAFT ONLY. Descriptive-only. Does not register or seal anything. Does not
mint identity ids. All six authority flags stay false: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority,
trade_authority. A caller that sets any of them true is refused (raise).
This module CONSUMES owner-supplied values from Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, and qledger/Evaluation. It does not fork or re-implement those
owners.

Stdlib only (json, datetime, re, pathlib). No pandas/numpy/engine/network.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AS_OF_RULE = {
    "per_episode": True,
    "format": "ISO-8601 UTC with Z suffix",
    "equals": "D(s) decision time",
    "invariant": "input_vintage_utc <= as_of_utc",
}

VINTAGE_REQUIRED_KEYS = (
    "per_episode_pin",
    "cross_vintage_detector",
    "train_read_ceiling",
)

LABELS = (
    "ABSTAIN_NO_EPISODES",
    "ABSTAIN_INSUFFICIENT_CLUSTERS",
    "DESCRIPTIVE_ONLY",
    "TESTED",
)

ABSTENTION_TOKENS = (
    "ABSTAIN_NO_EPISODES",
    "ABSTAIN_INSUFFICIENT_CLUSTERS",
)

REG_SEAL_REQUIREMENT = (
    "v2 membership seal row in REG §6 (not minted by this draft)"
)

IDENTITY_FORBIDDEN = re.compile(r"SEC:|9988|0700")
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
TUNE_MEMBERSHIP_WINDOW = re.compile(
    r"\d{4}-\d{2}-\d{2}\s*<=\s*s\s*<\s*\d{4}-\d{2}-\d{2}"
    r"|s\s*<\s*\d{4}-\d{2}-\d{2}"
    r"|s\s*>=\s*\d{4}-\d{2}-\d{2}"
)


def _fail(rule: str) -> None:
    raise ValueError(rule)


def _require_iso_z(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not ISO_Z.match(value):
        _fail(f"{name} is not ISO-8601 UTC ending in Z: {value!r}")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)


def _parse_utc_timestamp(value: str, name: str) -> datetime:
    if not isinstance(value, str):
        _fail(f"{name} is not a timestamp string: {value!r}")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        _fail(f"{name} is not a parseable timestamp: {value!r}")
    if parsed.tzinfo is None:
        _fail(f"{name} is not timezone-aware UTC: {value!r}")
    return parsed.astimezone(timezone.utc)


def check_episode_as_of(
    as_of_utc: str, decision_utc: str, input_vintage_utc: str
) -> None:
    """Refuse a malformed, non-Z, or then-unknown as_of triple."""
    as_dt = _require_iso_z(as_of_utc, "as_of_utc")
    if as_of_utc != decision_utc:
        _fail(
            f"as_of_utc differs from decision_utc: {as_of_utc!r} != {decision_utc!r}"
        )
    vintage_dt = _parse_utc_timestamp(input_vintage_utc, "input_vintage_utc")
    if vintage_dt > as_dt:
        _fail(
            "input_vintage_utc > as_of_utc invariant violated: "
            f"{input_vintage_utc!r} > {as_of_utc!r}"
        )


def label_for(episodes: int, clusters: int, min_episodes: int) -> str:
    """Return exactly one listed family label. Never TESTED when clusters < 2."""
    for name, value in (
        ("episodes", episodes),
        ("clusters", clusters),
        ("min_episodes", min_episodes),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            _fail(f"{name} must be int, got {value!r}")
        if value < 0:
            _fail(f"{name} must be >= 0, got {value!r}")
    if episodes == 0:
        return "ABSTAIN_NO_EPISODES"
    if clusters < 2:
        return "ABSTAIN_INSUFFICIENT_CLUSTERS"
    if episodes < min_episodes:
        return "DESCRIPTIVE_ONLY"
    return "TESTED"


def _check_authority_block(flags, where: str) -> None:
    if not isinstance(flags, dict):
        _fail(f"{where} is missing")
    for name in AUTHORITY_FLAG_NAMES:
        if name not in flags:
            _fail(f"{where}.{name} is missing")
        if flags[name] is not False:
            _fail(
                f"{where}.{name} must be literally False, got {flags[name]!r}"
            )
    for name, value in flags.items():
        if value is not False:
            _fail(f"{where}.{name} must be literally False, got {value!r}")


def _refuse_smuggled_authority(obj, path: str) -> None:
    """Refuse a non-False *_authority value anywhere in the draft tree."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else str(key)
            if isinstance(key, str):
                if key in AUTHORITY_FLAG_NAMES or key.endswith("_authority"):
                    if value is not False:
                        _fail(
                            f"{here} must be literally False, got {value!r}"
                        )
                if key == "authority_flags":
                    if not isinstance(value, dict) or any(
                        item is not False for item in value.values()
                    ):
                        _fail(
                            f"{here} must be a dict of literal False values, "
                            f"got {value!r}"
                        )
            _refuse_smuggled_authority(value, here)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _refuse_smuggled_authority(item, f"{path}[{index}]")


def _check_as_of_rule(vintage_rule: dict) -> None:
    as_of = vintage_rule.get("as_of_utc")
    if not isinstance(as_of, dict):
        _fail("vintage_rule.as_of_utc rule is missing")
    for key, expected in AS_OF_RULE.items():
        if key not in as_of:
            _fail(f"vintage_rule.as_of_utc.{key} is missing")
        if as_of[key] != expected:
            _fail(
                f"vintage_rule.as_of_utc.{key} must be {expected!r}, "
                f"got {as_of[key]!r}"
            )


def _check_tune_empty(splits: dict, draft: dict) -> None:
    if not isinstance(splits, dict):
        _fail("splits is missing")
    if "never_refill" not in splits:
        _fail("splits.never_refill is missing")
    tune = splits.get("TUNE")
    if isinstance(tune, dict):
        members = tune.get("members") or tune.get("membership_table") or []
        if members:
            _fail("splits.TUNE describes members")
        membership = str(tune.get("membership", "")).upper()
        if "EMPTY" not in membership:
            _fail("splits.TUNE is not EMPTY")
    elif isinstance(tune, str):
        if "EMPTY" not in tune:
            _fail("splits.TUNE is not EMPTY")
        if TUNE_MEMBERSHIP_WINDOW.search(tune):
            _fail("splits.TUNE describes members")
    else:
        _fail("splits.TUNE is not EMPTY")
    table = draft.get("membership_table")
    if isinstance(table, list) and table:
        _fail("membership_table is non-empty")
    if isinstance(table, dict):
        nested = table.get("members") or table.get("rows") or []
        if nested:
            _fail("membership_table is non-empty")


def validate_draft(d: dict) -> None:
    """Raise ValueError naming the first failed rule. Never registers or seals."""
    if not isinstance(d, dict):
        _fail("draft must be a dict")
    if d.get("status") != "DRAFT":
        _fail("status must be DRAFT")
    if d.get("registered") is not False:
        _fail("registered must be false")
    if d.get("outcome") is not None:
        _fail("outcome must be null")
    if d.get("seal") is not None:
        _fail("seal must be null")

    _check_authority_block(d.get("authority_flags"), "authority_flags")
    labels_obj = d.get("labels")
    if not isinstance(labels_obj, dict):
        _fail("labels is missing")
    _check_authority_block(
        labels_obj.get("authority_flags"), "labels.authority_flags"
    )
    _refuse_smuggled_authority(d, "")

    vintage_rule = d.get("vintage_rule")
    if not isinstance(vintage_rule, dict):
        _fail("vintage_rule is missing")
    for key in VINTAGE_REQUIRED_KEYS:
        value = vintage_rule.get(key)
        if not isinstance(value, str) or not value.strip():
            _fail(f"vintage_rule.{key} is missing")
    _check_as_of_rule(vintage_rule)

    if "info_leak_predicate" not in d:
        _fail("info_leak_predicate is missing")

    clock_rules = d.get("clock_rules")
    if not isinstance(clock_rules, dict):
        _fail("clock_rules is missing")
    if "detection_before_outcome" not in clock_rules:
        _fail("clock_rules.detection_before_outcome is missing")

    successor = d.get("successor_of")
    if not isinstance(successor, dict):
        _fail("successor_of is missing")
    citation = successor.get("register_citation")
    if not isinstance(citation, dict):
        _fail("successor_of.register_citation is missing")
    digest = citation.get("digest")
    composite = successor.get("composite_split_digest")
    if digest != composite:
        _fail(
            "successor_of.register_citation digest differs from "
            "successor_of.composite_split_digest"
        )

    gate = d.get("registration_gate")
    if not isinstance(gate, dict):
        _fail("registration_gate is missing")
    requires = gate.get("requires")
    if not isinstance(requires, list) or REG_SEAL_REQUIREMENT not in requires:
        _fail("registration_gate.requires is missing the v2 REG §6 seal row")

    tuning = d.get("tuning")
    if not isinstance(tuning, dict):
        _fail("tuning is missing")
    if tuning.get("mode") != "UNTUNED":
        _fail('tuning.mode must be "UNTUNED"')
    selectors = tuning.get("selectors")
    if not isinstance(selectors, list) or len(selectors) != 0:
        _fail("tuning.selectors must be empty")
    if tuning.get("test_conditional_selection") != "REFUSED":
        _fail('tuning.test_conditional_selection must be "REFUSED"')

    ledger = d.get("trial_ledger")
    if not isinstance(ledger, dict):
        _fail("trial_ledger is missing")
    if ledger.get("declared_budget_floor") != 6:
        _fail("trial_ledger.declared_budget_floor must be 6")
    source = ledger.get("declared_budget_floor_source")
    if not isinstance(source, str) or "SEAL_AND_BUDGET.json" not in source:
        _fail(
            "trial_ledger.declared_budget_floor_source must name "
            "SEAL_AND_BUDGET.json"
        )
    family_n = ledger.get("family_n")
    if not isinstance(family_n, str) or not family_n.strip():
        _fail("trial_ledger.family_n is missing")

    semantics = d.get("label_semantics")
    if not isinstance(semantics, dict):
        _fail("label_semantics is missing")
    listed = semantics.get("labels")
    if not isinstance(listed, list) or set(listed) != set(LABELS):
        _fail("label_semantics.labels must be the four family labels")
    label_order = d.get("label_order")
    if not isinstance(label_order, list) or set(label_order) != set(listed):
        _fail("set(label_order) != set(label_semantics.labels)")
    ladder = d.get("abstention_ladder")
    if not isinstance(ladder, list):
        _fail("abstention_ladder is missing")
    for item in ladder:
        text = str(item)
        if "TESTED" in text or "DESCRIPTIVE_ONLY" in text:
            _fail("abstention_ladder contains TESTED or DESCRIPTIVE_ONLY")
    ladder_tokens = [str(item).split()[0] for item in ladder]
    if ladder_tokens != list(ABSTENTION_TOKENS):
        _fail("abstention_ladder must list only ABSTAIN_* tokens in order")

    rule = semantics.get("rule")
    if not isinstance(rule, dict):
        _fail("label_semantics.rule is missing")
    tested = rule.get("TESTED")
    if not isinstance(tested, dict):
        _fail("label_semantics.rule.TESTED is missing")
    min_clusters = tested.get("min_clusters")
    if not isinstance(min_clusters, int) or isinstance(min_clusters, bool):
        _fail("TESTED reachable with clusters < 2")
    if min_clusters < 2:
        _fail("TESTED reachable with clusters < 2")

    _check_tune_empty(d.get("splits"), d)

    blob = json.dumps(d, ensure_ascii=False)
    if IDENTITY_FORBIDDEN.search(blob):
        _fail("draft contains forbidden identity literal (SEC:, 9988, or 0700)")


def load_draft(path) -> dict:
    """Parse the DRAFT JSON and run validate_draft. Does not register or seal."""
    text = Path(path).read_text(encoding="utf-8")
    if IDENTITY_FORBIDDEN.search(text):
        _fail("draft contains forbidden identity literal (SEC:, 9988, or 0700)")
    draft = json.loads(text)
    validate_draft(draft)
    return draft
