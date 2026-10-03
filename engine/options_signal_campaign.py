"""Independent, nightly-only options campaign revision and outcome ledgers.

The source unit is the immutable ``options.signal_episode/v1`` row. Every valid
exact-contract/session cluster is retained, including singleton controls. A
campaign revision is a census of the exact ordered member set at one append-only
source prefix; a later member may only append a superseding revision.

Campaign outcomes use the final member's availability clock and one exact,
receipt-bound episode outcome. Other member outcomes are references used only to
report coverage. Nothing in this module ranks, scores, gates, sizes, selects,
originates, publishes, trains, or computes option P&L.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from engine.ledger_lane import nightly_advance_enabled
from engine.options_signal_episode_contract import (
    EpisodeSourceContractError,
    session_outcome_logical_bytes as _session_outcome_logical_bytes,
    validate_episode_pit,
    validate_h60_outcome_join,
    validate_session_outcome_join,
)

CAMPAIGN_SCHEMA = "options.signal_campaign/v2"
CAMPAIGN_OUTCOME_SCHEMA = "options.signal_campaign_outcome/v1"
CAMPAIGN_CHECKPOINT_SCHEMA = "options.signal_campaign_checkpoint/v1"
EPISODE_SCHEMA = "options.signal_episode/v1"
H60_SCHEMA = "options.signal_episode_outcome/v1"
SESSION_OUTCOME_SCHEMA = "options.signal_episode_session_outcome/v1"
PRICE_RECEIPT_SCHEMA = "polygon.intraday_price_receipt/v1"

GROUPING_POLICY = "exact-contract-session-census/v2"
ELIGIBILITY_POLICY = "all-valid-options-signal-episodes/v2"
MEMBER_ORDER_POLICY = "available-at-then-episode-id/v1"
REVISION_POLICY = "strict-source-prefix-extension/v1"
OUTCOME_ANCHOR_POLICY = "final-member-availability/v1"
CHECKPOINT_POLICY = "checkpoint-last-exact-prefix/v1"
RULE_FROZEN_AT = "2026-08-12T13:30:00Z"

EPISODES_PATH = "data/options_signal_episode/episodes.jsonl"
H60_PATH = "data/options_signal_episode/outcomes_h60.jsonl"
SESSION_PATH = "data/options_signal_episode/outcomes_session.jsonl"
CAMPAIGNS_PATH = "data/options_signal_campaign/campaigns.jsonl"
OUTCOMES_PATH = "data/options_signal_campaign/outcomes.jsonl"
CHECKPOINT_PATH = "data/options_signal_campaign/checkpoint.json"
HORIZONS = ("h60", "eod", "1d", "3d", "5d", "10d")
CORRECTION_POLICY_PATH = Path(
    "research/options_estate/options_signal_campaign_outcome_correction_prereg_v1.json"
)
CORRECTION_POLICY_SHA256 = (
    "7e6710c8b1ce65f1307f450e50829280548fcd62bd3521c2acf7a5b4ec6ef2ad"
)
CAMPAIGN_CHECKPOINT_V2_SCHEMA = "options.signal_campaign_checkpoint/v2"
CORRECTION_ACTIVATION_SCHEMA = (
    "options.signal_campaign_correction_activation/v1"
)

FALSE_AUTHORITY = {
    "may_originate": False,
    "may_rank": False,
    "may_score": False,
    "may_gate": False,
    "may_size": False,
    "may_issue": False,
    "may_trade": False,
    "may_publish_pick": False,
    "may_train_prophet": False,
    "may_feed_neural_web": False,
    "may_select": False,
    "may_escalate": False,
    "may_compute_option_pnl": False,
}

_CORRECTION_LAW = {
    "retain_original_raw_rows": True,
    "delete_or_truncate_original_rows": False,
    "rewrite_original_rows": False,
    "restamp_expected_hashes": False,
    "backfill_original_historical_keys": False,
    "reinterpret_original_computed_at": False,
    "mutate_campaign_revisions": False,
    "create_replacement_ledger": False,
    "create_replacement_campaign_identity": False,
    "raw_physical_history_remains_audit_visible": True,
    "quarantine_exact_semantic_keys_as_occupied": True,
    "later_valid_rows_must_append_after_incident_generation": True,
    "later_valid_rows_must_pass_normal_source_receipt_validation": True,
    "quarantined_keys_may_not_be_reissued_as_if_original_history_were_valid": True,
    "correction_must_be_owner_native_versioned_and_receipted": True,
}


class CampaignContractError(ValueError):
    """Raised when a source, output, or checkpoint violates the frozen contract."""


@dataclass(frozen=True)
class CorrectionPolicy:
    path: Path
    file_sha256: str
    value: dict[str, Any]

    @classmethod
    def load_canonical(cls, root_dir: Path | None = None) -> "CorrectionPolicy":
        path = (
            root_dir or Path(__file__).resolve().parent.parent
        ).resolve() / CORRECTION_POLICY_PATH
        if path.is_symlink() or not path.is_file():
            raise CampaignContractError("campaign correction policy is unavailable")
        raw = path.read_bytes()
        digest = _sha256(raw)
        if digest != CORRECTION_POLICY_SHA256:
            raise CampaignContractError("campaign correction policy hash is not canonical")
        try:
            value = _strict_loads(raw)
        except Exception as exc:  # noqa: BLE001
            raise CampaignContractError("campaign correction policy is malformed") from exc
        policy = cls(path, digest, value)
        policy._verify()
        return policy

    def _exact(self, name: str, expected: object) -> None:
        if self.value.get(name) != expected:
            raise CampaignContractError(f"campaign correction policy {name} is invalid")

    def _verify(self) -> None:
        expected_keys = {
            "schema",
            "policy_id",
            "policy_version",
            "status",
            "registered_on",
            "operation",
            "parent_operation",
            "source_pin",
            "incident",
            "physical_identity",
            "lawful_prefix",
            "incident_generation",
            "quarantine",
            "correction_law",
            "effective_view_after_activation",
            "implementation_constraints",
            "implementation_entry_preconditions",
            "activation_preconditions",
            "acceptance_postconditions",
            "phase_dependencies",
            "phase_effect_limits",
            "authority",
            "source_pin_observation",
            "activation_identity",
        }
        if set(self.value) != expected_keys:
            raise CampaignContractError("campaign correction policy shape is invalid")
        self._exact("schema", "options.campaign_outcome_correction_prereg/v1")
        self._exact("policy_id", "sep03_mixed_generation_outcome_quarantine/v1")
        self._exact("policy_version", 1)
        self._exact("status", "preregistered_inactive_no_history_mutation")
        self._exact(
            "operation", "oa-campaign-outcome-correction-prereg-20260919-sol-001"
        )
        self._exact(
            "parent_operation",
            "options-alpha-product-integration-20260917-sol-001",
        )
        self._exact("source_pin", "4e7761e42435622ad8ba181ba617e2a4bae6f015")
        self._exact("correction_law", _CORRECTION_LAW)
        self._exact(
            "phase_effect_limits",
            {
                "policy_grants_execution": False,
                "controlled_activation_implies_acceptance": False,
                "fixture_or_manual_run_may_satisfy_normal_nightly_proof": False,
                "failed_postcondition": (
                    "NOT_ACCEPTED_preserve_raw_history_return_to_existing_owner_no_automatic_retry"
                ),
            },
        )
        if self.value["authority"] != {
            name: False
            for name in (
                "may_score",
                "may_rank",
                "may_gate",
                "may_size",
                "may_issue",
                "may_trade",
                "may_train",
                "may_publish_probability",
                "may_compute_option_pnl",
                "may_change_candidate_formation",
                "may_promote",
            )
        }:
            raise CampaignContractError("campaign correction authority is invalid")

    @property
    def quarantine(self) -> dict[str, Any]:
        value = self.value["quarantine"]
        if (
            value.get("applies_to") != OUTCOMES_PATH
            or value.get("start_row") != 24579
            or value.get("end_row") != 28423
            or value.get("record_count") != 3845
            or value.get("computed_at_exact") != "2026-09-03T20:37:25.569588Z"
        ):
            raise CampaignContractError(
                "campaign correction quarantine identity is invalid"
            )
        return value

    @property
    def incident_generation(self) -> dict[str, Any]:
        value = self.value["incident_generation"]
        if (
            value.get("campaigns", {}).get("records") != 8385
            or value.get("outcomes", {}).get("records") != 28423
        ):
            raise CampaignContractError(
                "campaign correction incident identity is invalid"
            )
        return value

    @property
    def activation_preconditions(self) -> tuple[str, ...]:
        value = self.value["activation_preconditions"]
        if not isinstance(value, list) or any(
            not isinstance(item, str) for item in value
        ):
            raise CampaignContractError(
                "campaign correction preconditions are invalid"
            )
        return tuple(value)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _strict_loads(raw: str | bytes) -> Any:
    return json.loads(
        raw,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-standard JSON constant {token}")
        ),
    )


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CampaignContractError("value is not canonical finite JSON") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{_sha256(raw)[:24]}"


def _canonical_utc(value: object, field: str) -> tuple[str, datetime]:
    if type(value) is not str or not value.endswith("Z"):
        raise CampaignContractError(f"{field} must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CampaignContractError(f"{field} is not a timestamp") from exc
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat().replace("+00:00", "Z")
    if canonical != value:
        raise CampaignContractError(f"{field} must be canonical UTC")
    return canonical, parsed


def canonical_strike(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise CampaignContractError("strike must be a finite positive number")
    if isinstance(value, float) and not math.isfinite(value):
        raise CampaignContractError("strike must be finite")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CampaignContractError("strike is invalid") from exc
    if not number.is_finite() or number <= 0:
        raise CampaignContractError("strike must be finite and positive")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _strike_value(strike_key: str) -> int | float:
    if not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]*[1-9])?", strike_key):
        raise CampaignContractError("strike key is not canonical")
    return int(strike_key) if "." not in strike_key else float(strike_key)


@lru_cache(maxsize=8)
def _schema_validator(filename: str) -> Draft202012Validator:
    path = Path(__file__).resolve().parent.parent / "contracts/options" / filename
    try:
        schema = _strict_loads(path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        raise CampaignContractError(f"cannot load schema {path}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(row: dict[str, Any], filename: str) -> None:
    errors = sorted(_schema_validator(filename).iter_errors(row), key=lambda err: list(err.path))
    if errors:
        error = errors[0]
        where = ".".join(str(part) for part in error.path) or "<root>"
        raise CampaignContractError(
            f"{filename} validation failed at {where}: {error.message}"
        )


@dataclass(frozen=True)
class LedgerRow:
    value: dict[str, Any]
    ordinal: int
    raw: bytes
    sha256: str


@dataclass(frozen=True)
class LedgerSnapshot:
    path: Path
    label: str
    rows: tuple[LedgerRow, ...]
    raw: bytes
    digest: str

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def sha256(self) -> str:
        return self.digest

    def prefix_raw(self, count: int) -> bytes:
        if type(count) is not int or count < 0 or count > self.count:
            raise CampaignContractError(f"invalid prefix count for {self.label}")
        return b"".join(item.raw + b"\n" for item in self.rows[:count])

    def prefix(self, count: int) -> "LedgerSnapshot":
        raw = self.prefix_raw(count)
        return LedgerSnapshot(
            self.path,
            self.label,
            self.rows[:count],
            raw,
            _sha256(raw),
        )


def _snapshot_from_raw(path: Path, label: str, raw: bytes) -> LedgerSnapshot:
    if raw and not raw.endswith(b"\n"):
        raise CampaignContractError(f"torn final line: {label}")
    rows: list[LedgerRow] = []
    for ordinal, line in enumerate(raw.splitlines(), start=1):
        if not line:
            raise CampaignContractError(f"blank ledger row: {label}:{ordinal}")
        try:
            value = _strict_loads(line)
        except Exception as exc:  # noqa: BLE001
            raise CampaignContractError(f"malformed JSON: {label}:{ordinal}") from exc
        if not isinstance(value, dict) or canonical_bytes(value) != line:
            raise CampaignContractError(f"noncanonical ledger row: {label}:{ordinal}")
        rows.append(LedgerRow(value, ordinal, line, _sha256(line)))
    return LedgerSnapshot(path, label, tuple(rows), raw, _sha256(raw))


def load_ledger(path: Path, label: str) -> LedgerSnapshot:
    if label == SESSION_PATH:
        # Physical rollover is storage-only. Reconstruct the exact historical
        # byte stream through the shared frozen source contract — never by
        # importing the mutable episode-writer implementation.
        try:
            raw = _session_outcome_logical_bytes(path)
        except EpisodeSourceContractError as exc:
            raise CampaignContractError(str(exc)) from exc
        return _snapshot_from_raw(path, label, raw)
    if not path.exists():
        return LedgerSnapshot(path, label, (), b"", _sha256(b""))
    if path.is_symlink() or not path.is_file():
        raise CampaignContractError(f"ledger is not a regular file: {label}")
    return _snapshot_from_raw(path, label, path.read_bytes())


def _receipt(snapshot: LedgerSnapshot, count: int | None = None) -> dict[str, Any]:
    records = snapshot.count if count is None else count
    if records == snapshot.count:
        digest = snapshot.sha256
    else:
        digest = _sha256(snapshot.prefix_raw(records))
    return {"path": snapshot.label, "records": records, "prefix_sha256": digest}


@dataclass
class _PrefixDigestState:
    digests: tuple[str, ...]


PrefixCache = dict[int, _PrefixDigestState]


def _prefix_sha256(
    snapshot: LedgerSnapshot,
    count: int,
    cache: PrefixCache | None = None,
) -> str:
    if type(count) is not int or count < 0 or count > snapshot.count:
        raise CampaignContractError(f"invalid prefix count for {snapshot.label}")
    if count == snapshot.count:
        return snapshot.sha256
    if cache is None:
        return _sha256(snapshot.prefix_raw(count))

    state = cache.get(id(snapshot))
    if state is None:
        hasher = hashlib.sha256()
        digests = [hasher.hexdigest()]
        for item in snapshot.rows:
            hasher.update(item.raw)
            hasher.update(b"\n")
            digests.append(hasher.hexdigest())
        state = _PrefixDigestState(tuple(digests))
        cache[id(snapshot)] = state
    return state.digests[count]


def _verify_receipt(
    receipt: object,
    snapshot: LedgerSnapshot,
    expected_path: str,
    cache: PrefixCache | None = None,
) -> int:
    if not isinstance(receipt, dict) or set(receipt) != {"path", "records", "prefix_sha256"}:
        raise CampaignContractError("prefix receipt shape is invalid")
    if receipt["path"] != expected_path or snapshot.label != expected_path:
        raise CampaignContractError("prefix receipt path is invalid")
    count = receipt["records"]
    if type(count) is not int or count < 0 or count > snapshot.count:
        raise CampaignContractError(f"ledger shrank behind checkpoint: {expected_path}")
    digest = receipt["prefix_sha256"]
    if type(digest) is not str or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise CampaignContractError("prefix receipt digest is invalid")
    if _prefix_sha256(snapshot, count, cache) != digest:
        raise CampaignContractError(f"ledger prefix changed: {expected_path}")
    return count


def verify_campaign_receipt(
    receipt: object,
    snapshot: LedgerSnapshot,
    expected_path: str | None = None,
) -> int:
    return _verify_receipt(
        receipt, snapshot, snapshot.label if expected_path is None else expected_path
    )


def _episode_id(source: str, source_event_id: str) -> str:
    return _stable_id("osep", EPISODE_SCHEMA, source, source_event_id)


def validate_episode(row: dict[str, Any]) -> None:
    _validate_schema(row, "options.signal_episode.v1.schema.json")
    try:
        validate_episode_pit(row)
    except EpisodeSourceContractError as exc:
        raise CampaignContractError(str(exc)) from exc
    canonical_strike(row["contract"]["strike"])


GroupKey = tuple[str, str, str, str, str]


def _group_key(episode: dict[str, Any]) -> GroupKey:
    contract = episode["contract"]
    return (
        episode["session_date"],
        episode["ticker"],
        contract["right"],
        contract["expiration"],
        canonical_strike(contract["strike"]),
    )


def _group_payload(group: GroupKey) -> dict[str, Any]:
    return {
        "session_date": group[0],
        "ticker": group[1],
        "right": group[2],
        "expiration": group[3],
        "strike": _strike_value(group[4]),
        "strike_key": group[4],
    }


def _group_from_payload(group: dict[str, Any]) -> GroupKey:
    key: GroupKey = (
        group["session_date"],
        group["ticker"],
        group["right"],
        group["expiration"],
        group["strike_key"],
    )
    if canonical_strike(group["strike"]) != key[4] or _group_payload(key) != group:
        raise CampaignContractError("campaign group strike is not canonical")
    return key


def _campaign_id(group: GroupKey) -> str:
    return _stable_id("ocam", CAMPAIGN_SCHEMA, GROUPING_POLICY, *group)


def _revision_id(campaign_id: str, member_ids: Iterable[str]) -> str:
    return _stable_id(
        "ocrev",
        CAMPAIGN_SCHEMA,
        campaign_id,
        REVISION_POLICY,
        MEMBER_ORDER_POLICY,
        ",".join(member_ids),
    )


def _policies() -> dict[str, str]:
    return {
        "grouping": GROUPING_POLICY,
        "eligibility": ELIGIBILITY_POLICY,
        "member_order": MEMBER_ORDER_POLICY,
        "revision": REVISION_POLICY,
        "outcome_anchor": OUTCOME_ANCHOR_POLICY,
        "frozen_at": RULE_FROZEN_AT,
    }


def _member(item: LedgerRow) -> dict[str, Any]:
    row = item.value
    features = row["feature_snapshot"]
    return {
        "episode_id": row["episode_id"],
        "available_at": row["available_at"],
        "source_event_id": row["source_event_id"],
        "source_row": item.ordinal,
        "source_row_sha256": item.sha256,
        "descriptive_evidence": {
            "flow_side": features["flow_side"],
            "repeated": features["repeated"],
            "swept": features["swept"],
            "vol_gt_prior_oi": features["vol_gt_prior_oi"],
            "premium_usd": features["premium_usd"],
            "contracts": features["contracts"],
        },
    }


def _campaign_payload(
    group: GroupKey,
    members: list[LedgerRow],
    source_prefix: LedgerSnapshot,
    prior: dict[str, Any] | None,
    *,
    source_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not members:
        raise CampaignContractError("campaign revision cannot be empty")
    campaign_id = _campaign_id(group)
    member_ids = [item.value["episode_id"] for item in members]
    available = [
        _canonical_utc(item.value["available_at"], "member.available_at")[1]
        for item in members
    ]
    evidence = [item.value["feature_snapshot"] for item in members]
    side_counts = {side: 0 for side in ("~buy", "~sell", "mixed")}
    for item in evidence:
        side_counts[item["flow_side"]] += 1
    formed_at = members[-1].value["available_at"]
    frozen_at = _canonical_utc(RULE_FROZEN_AT, "rule frozen_at")[1]
    evidence_phase = (
        "prospective_after_rule_freeze"
        if _canonical_utc(formed_at, "campaign formed_at")[1] >= frozen_at
        else "retrospective_context"
    )
    row = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_id": campaign_id,
        "campaign_revision_id": _revision_id(campaign_id, member_ids),
        "revision_number": 1 if prior is None else prior["revision_number"] + 1,
        "supersedes_revision_id": (
            None if prior is None else prior["campaign_revision_id"]
        ),
        "formed_at": formed_at,
        "policies": _policies(),
        "group": _group_payload(group),
        "members": [_member(item) for item in members],
        "descriptive": {
            "member_count": len(members),
            "premium_usd_total": round(
                sum(float(item["premium_usd"]) for item in evidence), 8
            ),
            "contracts_total": sum(item["contracts"] for item in evidence),
            "first_available_at": members[0].value["available_at"],
            "last_available_at": formed_at,
            "availability_span_seconds": round(
                (available[-1] - available[0]).total_seconds(), 6
            ),
            "flow_side_counts": side_counts,
            "repeated_count": sum(item["repeated"] is True for item in evidence),
            "swept_count": sum(item["swept"] is True for item in evidence),
            "vol_gt_prior_oi_count": sum(
                item["vol_gt_prior_oi"] is True for item in evidence
            ),
        },
        "intent": {
            "opening_closing": "unavailable",
            "direction_reliability": "soft",
            "accumulation_distribution": "unavailable",
        },
        "source_episode_prefix": (
            dict(source_receipt)
            if source_receipt is not None
            else _receipt(source_prefix)
        ),
        "disposition": "abstain",
        "role": "research_census_only",
        "evidence_phase": evidence_phase,
        "training_eligible": False,
        "authority": dict(FALSE_AUTHORITY),
    }
    validate_campaign(row)
    return row


def validate_campaign(row: dict[str, Any]) -> None:
    _validate_schema(row, "options.signal_campaign.v2.schema.json")
    _canonical_utc(row["formed_at"], "campaign.formed_at")
    group = _group_from_payload(row["group"])
    if row["campaign_id"] != _campaign_id(group):
        raise CampaignContractError("campaign identity disagrees with group")
    members = row["members"]
    member_ids = [item["episode_id"] for item in members]
    if len(member_ids) != len(set(member_ids)):
        raise CampaignContractError("campaign revision has duplicate members")
    order = [
        (
            _canonical_utc(
                item["available_at"], "campaign member available_at"
            )[1],
            item["episode_id"],
        )
        for item in members
    ]
    if order != sorted(order):
        raise CampaignContractError("campaign members are not canonically ordered")
    if row["campaign_revision_id"] != _revision_id(row["campaign_id"], member_ids):
        raise CampaignContractError("campaign revision identity is inconsistent")
    if row["formed_at"] != members[-1]["available_at"]:
        raise CampaignContractError("campaign availability must be the final member clock")
    if row["policies"] != _policies():
        raise CampaignContractError("campaign policies differ from the frozen contract")
    frozen_at = _canonical_utc(RULE_FROZEN_AT, "rule frozen_at")[1]
    expected_phase = (
        "prospective_after_rule_freeze"
        if _canonical_utc(row["formed_at"], "campaign formed_at")[1] >= frozen_at
        else "retrospective_context"
    )
    if row["evidence_phase"] != expected_phase:
        raise CampaignContractError("campaign evidence phase disagrees with rule freeze")
    if row["training_eligible"] is not False or row["authority"] != FALSE_AUTHORITY:
        raise CampaignContractError("campaign authority must remain identically false")


def _validated_episode_groups(snapshot: LedgerSnapshot) -> dict[GroupKey, list[LedgerRow]]:
    groups: dict[GroupKey, list[LedgerRow]] = {}
    seen_ids: set[str] = set()
    seen_sources: set[tuple[str, str]] = set()
    for item in snapshot.rows:
        validate_episode(item.value)
        episode_id = item.value["episode_id"]
        source_key = (item.value["source"], item.value["source_event_id"])
        if episode_id in seen_ids or source_key in seen_sources:
            raise CampaignContractError("duplicate source episode")
        seen_ids.add(episode_id)
        seen_sources.add(source_key)
        groups.setdefault(_group_key(item.value), []).append(item)
    for group, members in groups.items():
        groups[group] = sorted(
            members,
            key=lambda item: (
                _canonical_utc(
                    item.value["available_at"], "episode.available_at"
                )[1],
                item.value["episode_id"],
            ),
        )
    return groups


def _campaign_against_source(
    row: dict[str, Any],
    episodes: LedgerSnapshot,
    groups: dict[GroupKey, list[LedgerRow]],
    prefix_cache: PrefixCache,
) -> None:
    validate_campaign(row)
    count = _verify_receipt(
        row["source_episode_prefix"], episodes, EPISODES_PATH, prefix_cache
    )
    group = _group_from_payload(row["group"])
    members = [item for item in groups.get(group, []) if item.ordinal <= count]
    if not members:
        raise CampaignContractError("campaign group is absent from its source prefix")
    expected = _campaign_payload(
        group,
        members,
        episodes,
        None,
        source_receipt=row["source_episode_prefix"],
    )
    derived_fields = {
        "schema",
        "campaign_id",
        "campaign_revision_id",
        "formed_at",
        "policies",
        "group",
        "members",
        "descriptive",
        "intent",
        "source_episode_prefix",
        "disposition",
        "role",
        "evidence_phase",
        "training_eligible",
        "authority",
    }
    for field in derived_fields:
        if row[field] != expected[field]:
            raise CampaignContractError(f"campaign source-derived field drift: {field}")


def _campaign_history(
    existing: LedgerSnapshot,
    episodes: LedgerSnapshot,
    *,
    groups: dict[GroupKey, list[LedgerRow]] | None = None,
    prefix_cache: PrefixCache | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    source_groups = groups if groups is not None else _validated_episode_groups(episodes)
    cache = prefix_cache if prefix_cache is not None else {}
    revisions: dict[str, dict[str, Any]] = {}
    latest: dict[str, dict[str, Any]] = {}
    for item in existing.rows:
        row = item.value
        _campaign_against_source(row, episodes, source_groups, cache)
        revision_id = row["campaign_revision_id"]
        if revision_id in revisions:
            raise CampaignContractError("duplicate campaign revision")
        prior = latest.get(row["campaign_id"])
        if prior is None:
            if row["revision_number"] != 1 or row["supersedes_revision_id"] is not None:
                raise CampaignContractError("first campaign revision has invalid lineage")
        else:
            prior_ids = [member["episode_id"] for member in prior["members"]]
            ids = [member["episode_id"] for member in row["members"]]
            first_new = row["members"][len(prior_ids)] if len(ids) > len(prior_ids) else None
            if (
                row["revision_number"] != prior["revision_number"] + 1
                or row["supersedes_revision_id"] != prior["campaign_revision_id"]
                or len(ids) <= len(prior_ids)
                or ids[: len(prior_ids)] != prior_ids
                or first_new is None
                or first_new["source_row"] <= prior["source_episode_prefix"]["records"]
                or row["source_episode_prefix"]["records"]
                <= prior["source_episode_prefix"]["records"]
            ):
                raise CampaignContractError(
                    "campaign revision is not a strict later-prefix extension"
                )
        revisions[revision_id] = row
        latest[row["campaign_id"]] = row
    return revisions, latest


def _derive_campaign_revisions_from_groups(
    episodes: LedgerSnapshot,
    groups: dict[GroupKey, list[LedgerRow]],
    latest: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    fresh: list[dict[str, Any]] = []
    for group in sorted(groups):
        members = groups[group]
        prior = latest.get(_campaign_id(group))
        ids = [item.value["episode_id"] for item in members]
        if prior is not None:
            prior_ids = [item["episode_id"] for item in prior["members"]]
            if len(ids) < len(prior_ids):
                raise CampaignContractError("campaign source group shrank")
            if ids[: len(prior_ids)] != prior_ids:
                raise CampaignContractError(
                    "campaign source rewrote or backdated membership"
                )
            if len(ids) == len(prior_ids):
                continue
            first_new = members[len(prior_ids)]
            if first_new.ordinal <= prior["source_episode_prefix"]["records"]:
                raise CampaignContractError(
                    "campaign extension is not a later source-prefix row"
                )
        fresh.append(_campaign_payload(group, members, episodes, prior))
    return fresh


def derive_campaign_revisions(
    episodes: LedgerSnapshot,
    existing: LedgerSnapshot,
) -> list[dict[str, Any]]:
    groups = _validated_episode_groups(episodes)
    _revisions, latest = _campaign_history(existing, episodes, groups=groups)
    return _derive_campaign_revisions_from_groups(episodes, groups, latest)


def _source_outcome_maps(
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    *,
    episode_groups: dict[GroupKey, list[LedgerRow]] | None = None,
) -> tuple[dict[str, LedgerRow], dict[tuple[str, str], LedgerRow]]:
    episode_rows = (
        episode_groups
        if episode_groups is not None
        else _validated_episode_groups(episodes)
    )
    episode_by_id = {
        item.value["episode_id"]: item.value
        for members in episode_rows.values()
        for item in members
    }
    h60_map: dict[str, LedgerRow] = {}
    for item in h60.rows:
        row = item.value
        _validate_schema(row, "options.signal_episode_outcome.v1.schema.json")
        episode = episode_by_id.get(row["episode_id"])
        if episode is None:
            raise CampaignContractError("H+60 outcome has an invalid episode join")
        try:
            validate_h60_outcome_join(row, episode)
        except EpisodeSourceContractError as exc:
            raise CampaignContractError(str(exc)) from exc
        if row["episode_id"] in h60_map:
            raise CampaignContractError("duplicate H+60 outcome semantic key")
        _validate_source_outcome_authority(row)
        h60_map[row["episode_id"]] = item
    session_map: dict[tuple[str, str], LedgerRow] = {}
    for item in session.rows:
        row = item.value
        _validate_schema(row, "options.signal_episode_session_outcome.v1.schema.json")
        episode = episode_by_id.get(row["episode_id"])
        key = (row["episode_id"], row["horizon"])
        if episode is None:
            raise CampaignContractError("session outcome has an invalid episode join")
        try:
            validate_session_outcome_join(row, episode)
        except EpisodeSourceContractError as exc:
            raise CampaignContractError(str(exc)) from exc
        if key in session_map:
            raise CampaignContractError("duplicate session outcome semantic key")
        _validate_source_outcome_authority(row)
        session_map[key] = item
    return h60_map, session_map


def _validate_source_outcome_authority(row: dict[str, Any]) -> None:
    if row["label_authority"] != "research_only":
        raise CampaignContractError("source outcome is not research-only")
    option = row["option"]
    if (
        option["status"] != "unavailable"
        or option["quote_basis"] is not None
        or option["ret"] is not None
        or option["mfe"] is not None
        or option["mae"] is not None
    ):
        raise CampaignContractError("source outcome asserts executable option P&L")
    if row["measurement"]["training_eligible"] is not False:
        raise CampaignContractError("source outcome unexpectedly permits training")
    provenance = row["provenance"]
    if row["status"] == "complete":
        if provenance["source_receipt_schema"] != PRICE_RECEIPT_SCHEMA:
            raise CampaignContractError("complete source outcome lacks the frozen Polygon receipt")
    elif any(
        provenance.get(field) is not None
        for field in ("source_receipt_schema", "price_source", "price_vintage")
    ):
        raise CampaignContractError("incomplete source outcome carries a partial price receipt")


def _campaign_outcome_id(revision_id: str, horizon: str) -> str:
    return _stable_id(
        "ocout", CAMPAIGN_OUTCOME_SCHEMA, revision_id, horizon, OUTCOME_ANCHOR_POLICY
    )


def _outcome_source_for_horizon(
    horizon: str,
    episode_id: str,
    h60_map: dict[str, LedgerRow],
    session_map: dict[tuple[str, str], LedgerRow],
) -> LedgerRow | None:
    return h60_map.get(episode_id) if horizon == "h60" else session_map.get(
        (episode_id, horizon)
    )


def _campaign_outcome_payload(
    campaign: dict[str, Any],
    horizon: str,
    source: LedgerRow,
    source_snapshot: LedgerSnapshot,
    h60_map: dict[str, LedgerRow],
    session_map: dict[tuple[str, str], LedgerRow],
    source_record_limit: int | None = None,
    *,
    source_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    anchor_member = campaign["members"][-1]
    row = source.value
    if row["episode_id"] != anchor_member["episode_id"]:
        raise CampaignContractError("campaign outcome source is not the final member")
    if row["horizon_anchor"] != campaign["formed_at"]:
        raise CampaignContractError("campaign outcome does not use campaign availability")
    references: list[dict[str, Any]] = []
    missing: list[str] = []
    for member in campaign["members"]:
        member_source = _outcome_source_for_horizon(
            horizon, member["episode_id"], h60_map, session_map
        )
        if member_source is None or (
            source_record_limit is not None
            and member_source.ordinal > source_record_limit
        ):
            missing.append(member["episode_id"])
            continue
        references.append(
            {
                "episode_id": member["episode_id"],
                "outcome_id": member_source.value["outcome_id"],
                "status": member_source.value["status"],
                "row": member_source.ordinal,
                "row_sha256": member_source.sha256,
            }
        )
    provenance = row["provenance"]
    outcome = {
        "schema": CAMPAIGN_OUTCOME_SCHEMA,
        "campaign_outcome_id": _campaign_outcome_id(
            campaign["campaign_revision_id"], horizon
        ),
        "campaign_id": campaign["campaign_id"],
        "campaign_revision_id": campaign["campaign_revision_id"],
        "horizon": horizon,
        "anchor_policy": OUTCOME_ANCHOR_POLICY,
        "campaign_available_at": campaign["formed_at"],
        "anchor_episode_id": anchor_member["episode_id"],
        "computed_at": row["computed_at"],
        "status": row["status"],
        "reason": row["reason"],
        "target_time": row["target_time"],
        "matured_at": row["matured_at"],
        "measurement": {
            "kind": row["measurement"]["kind"],
            "target_aligned": row["measurement"]["target_aligned"],
            "source_measurement_sha256": _sha256(canonical_bytes(row["measurement"])),
        },
        "underlying": {
            "status": row["underlying"]["status"],
            "ret": row["underlying"]["ret"],
            "mfe": row["underlying"]["mfe"],
            "mae": row["underlying"]["mae"],
        },
        "option": {
            "status": "unavailable",
            "reason": "no_executable_nbbo_quote_path",
            "quote_basis": None,
            "ret": None,
            "mfe": None,
            "mae": None,
        },
        "source_outcome": {
            "path": source_snapshot.label,
            "row": source.ordinal,
            "row_sha256": source.sha256,
            "schema": row["schema"],
            "outcome_id": row["outcome_id"],
            "episode_id": row["episode_id"],
            "horizon_anchor": row["horizon_anchor"],
            "price_receipt_sha256": (
                _sha256(canonical_bytes(provenance))
                if provenance["source_receipt_schema"] == PRICE_RECEIPT_SCHEMA
                else None
            ),
            "price_source": provenance["price_source"],
            "price_vintage": provenance["price_vintage"],
            "source_receipt_schema": provenance["source_receipt_schema"],
        },
        "source_outcome_prefix": (
            dict(source_receipt)
            if source_receipt is not None
            else _receipt(source_snapshot)
        ),
        "member_outcome_coverage": {
            "expected_member_count": len(campaign["members"]),
            "observed_member_count": len(references),
            "references": references,
            "missing_episode_ids": missing,
        },
        "label_authority": "research_only",
        "training_eligible": False,
        "authority": dict(FALSE_AUTHORITY),
    }
    validate_campaign_outcome(outcome)
    return outcome


def validate_campaign_outcome(row: dict[str, Any]) -> None:
    _validate_schema(row, "options.signal_campaign_outcome.v1.schema.json")
    for field in ("campaign_available_at", "computed_at", "target_time", "matured_at"):
        _canonical_utc(row[field], f"campaign outcome {field}")
    if row["campaign_outcome_id"] != _campaign_outcome_id(
        row["campaign_revision_id"], row["horizon"]
    ):
        raise CampaignContractError("campaign outcome identity is inconsistent")
    coverage = row["member_outcome_coverage"]
    references = coverage["references"]
    missing = coverage["missing_episode_ids"]
    reference_ids = [item["episode_id"] for item in references]
    if len(reference_ids) != len(set(reference_ids)) or len(missing) != len(set(missing)):
        raise CampaignContractError("campaign outcome coverage contains duplicates")
    if set(reference_ids) & set(missing):
        raise CampaignContractError("campaign outcome coverage overlaps missing members")
    if (
        coverage["observed_member_count"] != len(references)
        or coverage["expected_member_count"] != len(references) + len(missing)
    ):
        raise CampaignContractError("campaign outcome coverage counts are inconsistent")
    if row["training_eligible"] is not False or row["authority"] != FALSE_AUTHORITY:
        raise CampaignContractError("campaign outcome authority must remain false")
    if any(value is not None for key, value in row["option"].items() if key in {"quote_basis", "ret", "mfe", "mae"}):
        raise CampaignContractError("campaign outcome option P&L must remain null")


def _campaign_outcome_against_sources(
    row: dict[str, Any],
    campaign_by_revision: dict[str, dict[str, Any]],
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    h60_map: dict[str, LedgerRow],
    session_map: dict[tuple[str, str], LedgerRow],
    prefix_cache: PrefixCache,
) -> None:
    validate_campaign_outcome(row)
    campaign = campaign_by_revision.get(row["campaign_revision_id"])
    if campaign is None or campaign["campaign_id"] != row["campaign_id"]:
        raise CampaignContractError("campaign outcome references a missing revision")
    horizon = row["horizon"]
    snapshot = h60 if horizon == "h60" else session
    expected_path = H60_PATH if horizon == "h60" else SESSION_PATH
    count = _verify_receipt(
        row["source_outcome_prefix"], snapshot, expected_path, prefix_cache
    )
    anchor = _outcome_source_for_horizon(
        horizon, campaign["members"][-1]["episode_id"], h60_map, session_map
    )
    if anchor is None or anchor.ordinal > count:
        raise CampaignContractError("campaign outcome anchor is absent from its prefix")
    expected = _campaign_outcome_payload(
        campaign,
        horizon,
        anchor,
        snapshot,
        h60_map,
        session_map,
        source_record_limit=count,
        source_receipt=row["source_outcome_prefix"],
    )
    if row != expected:
        raise CampaignContractError("campaign outcome differs from its receipt-bound source")



def _campaign_outcome_key(row: dict[str, Any]) -> tuple[str, str]:
    revision_id = row.get("campaign_revision_id")
    horizon = row.get("horizon")
    if not isinstance(revision_id, str) or not isinstance(horizon, str):
        raise CampaignContractError("campaign outcome semantic key is malformed")
    return revision_id, horizon


def _verify_receipt_shape(receipt: object) -> dict[str, Any]:
    """Validate the receipt's structural shape (keys/types/patterns) without
    enforcing digest consistency or policy-block match. The full canonical
    check is performed by `_verify_activation_receipt` on the build path
    and the binding check is performed by `_verify_effective_checkpoint`
    on the v2 continuation path."""
    if not isinstance(receipt, dict):
        raise CampaignContractError(
            "campaign correction activation receipt is malformed"
        )
    if set(receipt) != {
        "schema",
        "receipt_id",
        "activated_at",
        "receipt_sha256",
        "policy",
        "activation_preconditions",
    }:
        raise CampaignContractError(
            "campaign correction activation receipt shape is invalid"
        )
    if receipt["schema"] != CORRECTION_ACTIVATION_SCHEMA:
        raise CampaignContractError("campaign correction activation schema is invalid")
    if not isinstance(receipt["receipt_id"], str) or not receipt["receipt_id"]:
        raise CampaignContractError("campaign correction activation identity is invalid")
    activated_at = receipt["activated_at"]
    if not isinstance(activated_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z", activated_at
    ):
        raise CampaignContractError("campaign correction activation time is malformed")
    receipt_digest = receipt["receipt_sha256"]
    if (
        not isinstance(receipt_digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", receipt_digest)
    ):
        raise CampaignContractError("campaign correction activation digest is malformed")
    return receipt


def _verify_activation_receipt(receipt: object, policy: CorrectionPolicy) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise CampaignContractError(
            "campaign correction activation receipt is malformed"
        )
    if set(receipt) != {
        "schema",
        "receipt_id",
        "activated_at",
        "receipt_sha256",
        "policy",
        "activation_preconditions",
    }:
        raise CampaignContractError(
            "campaign correction activation receipt shape is invalid"
        )
    if receipt["schema"] != CORRECTION_ACTIVATION_SCHEMA:
        raise CampaignContractError("campaign correction activation schema is invalid")
    if not isinstance(receipt["receipt_id"], str) or not receipt["receipt_id"]:
        raise CampaignContractError("campaign correction activation identity is invalid")
    activated_at = receipt["activated_at"]
    if not isinstance(activated_at, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z", activated_at
    ):
        raise CampaignContractError("campaign correction activation time is malformed")
    receipt_digest = receipt["receipt_sha256"]
    if (
        not isinstance(receipt_digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", receipt_digest)
    ):
        raise CampaignContractError("campaign correction activation digest is malformed")
    if receipt["policy"] != {
        "policy_id": policy.value["policy_id"],
        "policy_version": policy.value["policy_version"],
        "path": CORRECTION_POLICY_PATH.as_posix(),
        "file_sha256": policy.file_sha256,
    }:
        raise CampaignContractError(
            "campaign correction activation policy is ineligible"
        )
    observed = receipt["activation_preconditions"]
    expected = policy.activation_preconditions
    if not isinstance(observed, dict) or set(observed) != set(expected):
        raise CampaignContractError(
            "campaign correction activation coverage is invalid"
        )
    if any(value is not True for value in observed.values()):
        raise CampaignContractError(
            "campaign correction activation precondition is unmet"
        )
    unsigned = dict(receipt)
    del unsigned["receipt_sha256"]
    if _sha256(canonical_bytes(unsigned)) != receipt_digest:
        raise CampaignContractError(
            "campaign correction activation digest is inconsistent"
        )
    return receipt


def _verify_policy_prefixes(
    policy: CorrectionPolicy,
    campaigns: LedgerSnapshot,
    outcomes: LedgerSnapshot,
) -> tuple[int, int]:
    generation = policy.incident_generation
    lawful = policy.value["lawful_prefix"]["outcomes"]
    quarantine = policy.quarantine
    if quarantine["record_count"] != 3845:
        raise CampaignContractError(
            "campaign correction incident identity is not canonical"
        )
    campaign_count = generation["campaigns"]["records"]
    outcome_count = generation["outcomes"]["records"]
    if campaigns.count < campaign_count or outcomes.count < outcome_count:
        raise CampaignContractError(
            "campaign correction source is shorter than incident"
        )
    if (
        _prefix_sha256(campaigns, campaign_count)
        != generation["campaigns"]["prefix_sha256"]
    ):
        raise CampaignContractError("campaign incident prefix changed")
    if (
        _prefix_sha256(outcomes, outcome_count)
        != generation["outcomes"]["prefix_sha256"]
    ):
        raise CampaignContractError("outcome incident prefix changed")
    lawful_count = lawful["records"]
    if _prefix_sha256(outcomes, lawful_count) != lawful["prefix_sha256"]:
        raise CampaignContractError("outcome lawful prefix changed")
    if (
        quarantine["start_row"] != lawful_count + 1
        or quarantine["end_row"] != outcome_count
        or quarantine["record_count"] != outcome_count - lawful_count
        or quarantine["contiguous_suffix_of_incident_generation"] is not True
    ):
        raise CampaignContractError(
            "campaign correction quarantine interval is invalid"
        )
    return lawful_count, outcome_count


def build_effective_outcome_view(
    physical_campaigns: LedgerSnapshot,
    physical_outcomes: LedgerSnapshot,
    correction: CorrectionPolicy | None,
    *,
    activation_receipt: object = None,
) -> "EffectiveOutcomeView":
    if correction is None:
        raise CampaignContractError("campaign correction policy is missing")
    canonical = CorrectionPolicy.load_canonical()
    if correction != canonical:
        raise CampaignContractError(
            "campaign correction policy object is not canonical"
        )
    _verify_activation_receipt(activation_receipt, correction)
    lawful_count, incident_count = _verify_policy_prefixes(
        correction, physical_campaigns, physical_outcomes
    )
    quarantined = physical_outcomes.rows[lawful_count:incident_count]
    admitted = (
        *physical_outcomes.rows[:lawful_count],
        *physical_outcomes.rows[incident_count:],
    )
    occupied: set[tuple[str, str]] = set()
    admitted_keys: set[tuple[str, str]] = set()
    computed_at = correction.quarantine["computed_at_exact"]
    for item in quarantined:
        row = item.value
        if not isinstance(row, dict):
            raise CampaignContractError("quarantined outcome is not an object")
        required = {
            "schema",
            "campaign_outcome_id",
            "campaign_revision_id",
            "horizon",
            "computed_at",
            "authority",
        }
        if set(row) < required:
            raise CampaignContractError(
                "quarantined outcome internal schema is invalid"
            )
        if row["schema"] != CAMPAIGN_OUTCOME_SCHEMA:
            raise CampaignContractError("quarantined outcome schema is invalid")
        if row["computed_at"] != computed_at:
            raise CampaignContractError(
                "quarantined outcome incident identity is invalid"
            )
        if row["authority"] != FALSE_AUTHORITY:
            raise CampaignContractError(
                "quarantined outcome authority must remain false"
            )
        key = _campaign_outcome_key(row)
        if key in occupied:
            raise CampaignContractError(
                "duplicate quarantined campaign outcome key"
            )
        occupied.add(key)
    for item in admitted:
        key = _campaign_outcome_key(item.value)
        if key in occupied:
            raise CampaignContractError(
                "duplicate campaign outcome key across populations"
            )
        occupied.add(key)
        admitted_keys.add(key)
    return EffectiveOutcomeView(
        physical_campaigns,
        physical_outcomes,
        correction,
        admitted,
        quarantined,
    )

def _outcome_history(
    existing: Iterable[LedgerRow],
    campaign_by_revision: dict[str, dict[str, Any]],
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    *,
    h60_map: dict[str, LedgerRow] | None = None,
    session_map: dict[tuple[str, str], LedgerRow] | None = None,
    prefix_cache: PrefixCache | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    if h60_map is None or session_map is None:
        h60_map, session_map = _source_outcome_maps(episodes, h60, session)
    cache = prefix_cache if prefix_cache is not None else {}
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    existing_rows = existing.rows if isinstance(existing, LedgerSnapshot) else existing
    for item in existing_rows:
        row = item.value
        _campaign_outcome_against_sources(
            row,
            campaign_by_revision,
            episodes,
            h60,
            session,
            h60_map,
            session_map,
            cache,
        )
        key = (row["campaign_revision_id"], row["horizon"])
        if key in rows:
            raise CampaignContractError("duplicate campaign outcome semantic key")
        rows[key] = row
    return rows


def _derive_campaign_outcomes_from_maps(
    campaigns: LedgerSnapshot,
    existing_rows: dict[tuple[str, str], dict[str, Any]] | Iterable[LedgerRow],
    h60_map: dict[str, LedgerRow],
    session_map: dict[tuple[str, str], LedgerRow],
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
) -> tuple[list[dict[str, Any]], int]:
    occupied_keys = (
        frozenset(existing_rows)
        if isinstance(existing_rows, dict)
        else frozenset(_campaign_outcome_key(item.value) for item in existing_rows)
    )
    fresh: list[dict[str, Any]] = []
    pending = 0
    for campaign_item in campaigns.rows:
        campaign = campaign_item.value
        for horizon in HORIZONS:
            key = (campaign["campaign_revision_id"], horizon)
            if key in occupied_keys:
                continue
            source = _outcome_source_for_horizon(
                horizon,
                campaign["members"][-1]["episode_id"],
                h60_map,
                session_map,
            )
            if source is None:
                pending += 1
                continue
            snapshot = h60 if horizon == "h60" else session
            fresh.append(
                _campaign_outcome_payload(
                    campaign, horizon, source, snapshot, h60_map, session_map
                )
            )
    return fresh, pending


@dataclass(frozen=True)
class EffectiveOutcomeView:
    campaigns: LedgerSnapshot
    outcomes: LedgerSnapshot
    policy: CorrectionPolicy
    admitted_rows: tuple[LedgerRow, ...]
    quarantined_rows: tuple[LedgerRow, ...]

    @cached_property
    def occupied_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            _campaign_outcome_key(item.value)
            for item in (*self.admitted_rows, *self.quarantined_rows)
        )

    @cached_property
    def admitted_keys(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            _campaign_outcome_key(item.value) for item in self.admitted_rows
        )

    @cached_property
    def quarantined_keys(self) -> frozenset[tuple[str, str]]:
        # Quarantined rows reserve the (campaign_revision_id, horizon) tuple
        # even though they are NOT admitted: their raw bytes, hash and
        # physical ordinal remain in the original LedgerSnapshot. A tail
        # append must not collide with any of these reserved keys.
        return frozenset(
            _campaign_outcome_key(item.value) for item in self.quarantined_rows
        )

    @property
    def raw_count(self) -> int:
        return self.outcomes.count

    @property
    def effective_count(self) -> int:
        return len(self.admitted_rows)


def derive_campaign_outcomes(
    campaigns: LedgerSnapshot,
    existing: LedgerSnapshot,
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
) -> tuple[list[dict[str, Any]], int]:
    episode_groups = _validated_episode_groups(episodes)
    h60_map, session_map = _source_outcome_maps(
        episodes, h60, session, episode_groups=episode_groups
    )
    campaign_by_revision, _latest = _campaign_history(
        campaigns, episodes, groups=episode_groups
    )
    existing_rows = _outcome_history(
        existing,
        campaign_by_revision,
        episodes,
        h60,
        session,
        h60_map=h60_map,
        session_map=session_map,
    )
    return _derive_campaign_outcomes_from_maps(
        campaigns, existing_rows, h60_map, session_map, h60, session
    )


def _load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise CampaignContractError("campaign checkpoint is not a regular file")
    raw = path.read_bytes()
    try:
        value = _strict_loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise CampaignContractError("campaign checkpoint is malformed") from exc
    if not isinstance(value, dict) or canonical_bytes(value) + b"\n" != raw:
        raise CampaignContractError("campaign checkpoint is not canonical JSON")
    schema_name = value.get("schema") if isinstance(value, dict) else None
    if schema_name == CAMPAIGN_CHECKPOINT_SCHEMA:
        schema_file = "options.signal_campaign_checkpoint.v1.schema.json"
    elif schema_name == CAMPAIGN_CHECKPOINT_V2_SCHEMA:
        schema_file = "options.signal_campaign_checkpoint.v2.schema.json"
    else:
        raise CampaignContractError("campaign checkpoint schema is unsupported")
    _validate_schema(value, schema_file)
    return value


def _checkpoint_id(sources: dict[str, Any], outputs: dict[str, Any]) -> str:
    return _stable_id(
        "ocp",
        CAMPAIGN_CHECKPOINT_SCHEMA,
        CHECKPOINT_POLICY,
        _sha256(canonical_bytes({"sources": sources, "outputs": outputs})),
    )


def _build_checkpoint(
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    campaigns: LedgerSnapshot,
    outcomes: LedgerSnapshot,
) -> dict[str, Any]:
    sources = {
        "episodes": _receipt(episodes),
        "h60_outcomes": _receipt(h60),
        "session_outcomes": _receipt(session),
    }
    outputs = {
        "campaigns": _receipt(campaigns),
        "outcomes": _receipt(outcomes),
    }
    checkpoint = {
        "schema": CAMPAIGN_CHECKPOINT_SCHEMA,
        "checkpoint_id": _checkpoint_id(sources, outputs),
        "policy": CHECKPOINT_POLICY,
        "sources": sources,
        "outputs": outputs,
        "training_eligible": False,
        "authority": dict(FALSE_AUTHORITY),
    }
    validate_checkpoint(checkpoint)
    return checkpoint


def validate_checkpoint(row: dict[str, Any]) -> None:
    schema_name = row.get("schema")
    if schema_name == CAMPAIGN_CHECKPOINT_SCHEMA:
        _validate_schema(row, "options.signal_campaign_checkpoint.v1.schema.json")
    elif schema_name == CAMPAIGN_CHECKPOINT_V2_SCHEMA:
        _validate_schema(row, "options.signal_campaign_checkpoint.v2.schema.json")
    else:
        raise CampaignContractError("campaign checkpoint schema is unsupported")
    if schema_name == CAMPAIGN_CHECKPOINT_V2_SCHEMA:
        expected = _effective_checkpoint_id(
            row["sources"], row["outputs"], row["correction"]
        )
    else:
        expected = _checkpoint_id(row["sources"], row["outputs"])
    if row["checkpoint_id"] != expected:
        raise CampaignContractError("campaign checkpoint identity is inconsistent")
    if row["training_eligible"] is not False or row["authority"] != FALSE_AUTHORITY:
        raise CampaignContractError("campaign checkpoint authority must remain false")


def _verify_checkpoint(
    checkpoint: dict[str, Any] | None,
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    campaigns: LedgerSnapshot,
    outcomes: LedgerSnapshot,
    activation_receipt: dict[str, Any] | None = None,
) -> None:
    if checkpoint is None:
        return
    validate_checkpoint(checkpoint)
    _verify_receipt(checkpoint["sources"]["episodes"], episodes, EPISODES_PATH)
    _verify_receipt(checkpoint["sources"]["h60_outcomes"], h60, H60_PATH)
    _verify_receipt(
        checkpoint["sources"]["session_outcomes"], session, SESSION_PATH
    )
    _verify_receipt(checkpoint["outputs"]["campaigns"], campaigns, CAMPAIGNS_PATH)
    _verify_receipt(checkpoint["outputs"]["outcomes"], outcomes, OUTCOMES_PATH)
    if checkpoint["schema"] == CAMPAIGN_CHECKPOINT_V2_SCHEMA:
        _verify_effective_checkpoint(
            checkpoint, campaigns, outcomes, activation_receipt
        )


def _checkpoint_policy_receipt(policy: CorrectionPolicy) -> dict[str, Any]:
    return {
        "policy_id": policy.value["policy_id"],
        "policy_version": policy.value["policy_version"],
        "path": CORRECTION_POLICY_PATH.as_posix(),
        "file_sha256": policy.file_sha256,
    }


def _key_digest(keys: Iterable[tuple[str, str]]) -> str:
    encoded = b"".join(
        canonical_bytes({"campaign_revision_id": revision, "horizon": horizon}) + b"\n"
        for revision, horizon in sorted(keys)
    )
    return _sha256(encoded)


def _build_effective_checkpoint(
    episodes: LedgerSnapshot,
    h60: LedgerSnapshot,
    session: LedgerSnapshot,
    view: EffectiveOutcomeView,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    sources = {
        "episodes": _receipt(episodes),
        "h60_outcomes": _receipt(h60),
        "session_outcomes": _receipt(session),
    }
    outputs = {
        "campaigns": _receipt(view.campaigns),
        "outcomes": _receipt(view.outcomes),
    }
    lawful_count = view.policy.value["lawful_prefix"]["outcomes"]["records"]
    incident_count = view.policy.incident_generation["outcomes"]["records"]
    quarantine_keys = view.quarantined_keys
    quarantine_digest = _key_digest(quarantine_keys)
    global_digest = _key_digest(view.occupied_keys)
    correction = {
        "policy": receipt["policy"],
        "activation_receipt_id": receipt["receipt_id"],
        "activation_receipt_time": receipt["activated_at"],
        "activation_receipt_sha256": receipt["receipt_sha256"],
        "lawful_prefix": {
            "path": OUTCOMES_PATH,
            "start_row": 1,
            "end_row": lawful_count,
            "count": lawful_count,
            "prefix_sha256": _prefix_sha256(view.outcomes, lawful_count),
        },
        "incident_prefix": {
            "path": OUTCOMES_PATH,
            "start_row": 1,
            "end_row": incident_count,
            "count": incident_count,
            "prefix_sha256": _prefix_sha256(view.outcomes, incident_count),
        },
        "quarantine": {
            "path": OUTCOMES_PATH,
            "start_row": lawful_count + 1,
            "end_row": incident_count,
            "count": len(view.quarantined_rows),
            # Reserved by the quarantine itself — only the keys present in
            # the quarantined rows. A tail append leaves this fixed while
            # the global occupied key set grows.
            "reserved_key_count": len(quarantine_keys),
            "reserved_key_digest": quarantine_digest,
        },
        "reserved_keys": {
            # Global occupied key set — admitted rows + quarantined rows.
            "count": len(view.occupied_keys),
            "digest": global_digest,
        },
        "physical_raw_outcomes": view.raw_count,
        "effective_outcomes": view.effective_count,
    }
    checkpoint = {
        "schema": CAMPAIGN_CHECKPOINT_V2_SCHEMA,
        "checkpoint_id": _effective_checkpoint_id(sources, outputs, correction),
        "policy": "checkpoint-last-exact-prefix-with-effective-outcome-view/v1",
        "sources": sources,
        "outputs": outputs,
        "correction": correction,
        "training_eligible": False,
        "authority": dict(FALSE_AUTHORITY),
    }
    validate_checkpoint(checkpoint)
    return checkpoint


def _effective_checkpoint_id(
    sources: dict[str, Any],
    outputs: dict[str, Any],
    correction: dict[str, Any],
) -> str:
    # The v2 identity binds to the canonical correction policy + the
    # activation receipt binding (id/time/sha256) + the physical/effective
    # counts and the quarantine/global key digests, in addition to the
    # source/output receipts. Sources alone never identify an effective
    # checkpoint; a different valid receipt for the same physical source
    # yields a different id and any tamper fails verification.
    bound_correction = {
        "policy": correction["policy"],
        "activation_receipt_id": correction["activation_receipt_id"],
        "activation_receipt_time": correction["activation_receipt_time"],
        "activation_receipt_sha256": correction["activation_receipt_sha256"],
        "lawful_prefix": correction["lawful_prefix"],
        "incident_prefix": correction["incident_prefix"],
        "quarantine": correction["quarantine"],
        "reserved_keys": correction["reserved_keys"],
        "physical_raw_outcomes": correction["physical_raw_outcomes"],
        "effective_outcomes": correction["effective_outcomes"],
    }
    return _stable_id(
        "ocp",
        CAMPAIGN_CHECKPOINT_V2_SCHEMA,
        _sha256(
            canonical_bytes(
                {
                    "sources": sources,
                    "outputs": outputs,
                    "correction": bound_correction,
                }
            )
        ),
    )


def _verify_effective_checkpoint(
    checkpoint: dict[str, Any],
    campaigns: LedgerSnapshot,
    outcomes: LedgerSnapshot,
    activation_receipt: dict[str, Any] | None,
) -> None:
    correction = checkpoint["correction"]
    policy = CorrectionPolicy.load_canonical()
    # Quarantined rows occupy physical rows lawful_count+1..incident_count.
    # Their semantic keys are RESERVED by the correction even though the
    # rows themselves are NOT admitted into the effective view. Build the
    # two key sets separately: quarantine reserved keys come ONLY from the
    # quarantined rows, and the global occupied key set is the union.
    quarantine_rows = outcomes.rows[
        correction["lawful_prefix"]["count"]: correction["incident_prefix"]["count"]
    ]
    quarantine_keys = frozenset(
        _campaign_outcome_key(item.value) for item in quarantine_rows
    )
    # The global occupied key set is the union of admitted rows and
    # quarantined rows — i.e. the entire physical ledger.
    view_keys = frozenset(
        _campaign_outcome_key(item.value) for item in outcomes.rows
    )
    lawful = correction["lawful_prefix"]
    incident = correction["incident_prefix"]
    quarantine = correction["quarantine"]
    reserved = correction["reserved_keys"]
    if (
        correction["policy"] != _checkpoint_policy_receipt(policy)
        or lawful["prefix_sha256"]
        != policy.value["lawful_prefix"]["outcomes"]["prefix_sha256"]
        or incident["prefix_sha256"]
        != policy.incident_generation["outcomes"]["prefix_sha256"]
        or _prefix_sha256(outcomes, lawful["count"]) != lawful["prefix_sha256"]
        or _prefix_sha256(outcomes, incident["count"]) != incident["prefix_sha256"]
        or quarantine["reserved_key_count"] != len(quarantine_keys)
        or quarantine["reserved_key_digest"] != _key_digest(quarantine_keys)
        or reserved != {
            "count": len(view_keys),
            "digest": _key_digest(view_keys),
        }
        or correction["physical_raw_outcomes"] != outcomes.count
        or correction["effective_outcomes"]
        != max(outcomes.count - quarantine["count"], 0)
    ):
        raise CampaignContractError(
            "campaign effective checkpoint metadata is inconsistent"
        )
    # The checkpoint identity is bound to the activation receipt: id, time,
    # sha256, policy, and all six preconditions must match the canonical
    # receipt and the recorded binding. Any tamper in the stored metadata or
    # in the receipt itself fails here.
    if activation_receipt is None:
        raise CampaignContractError(
            "campaign effective checkpoint continuation requires an activation receipt"
        )
    if (
        activation_receipt.get("receipt_id")
        != correction["activation_receipt_id"]
        or activation_receipt.get("activated_at")
        != correction["activation_receipt_time"]
        or activation_receipt.get("receipt_sha256")
        != correction["activation_receipt_sha256"]
        or activation_receipt.get("policy") != correction["policy"]
    ):
        raise CampaignContractError(
            "campaign effective checkpoint activation receipt binding is mismatched"
        )
    receipt_preconditions = activation_receipt.get("activation_preconditions")
    expected_preconditions = policy.activation_preconditions
    if not isinstance(receipt_preconditions, dict) or any(
        receipt_preconditions.get(name) is not True
        for name in expected_preconditions
    ):
        raise CampaignContractError(
            "campaign effective checkpoint activation preconditions are unmet"
        )
    unsigned = dict(activation_receipt)
    unsigned.pop("receipt_sha256", None)
    if _sha256(canonical_bytes(unsigned)) != activation_receipt["receipt_sha256"]:
        raise CampaignContractError(
            "campaign effective checkpoint activation receipt digest is inconsistent"
        )
    if (
        checkpoint["checkpoint_id"]
        != _effective_checkpoint_id(
            checkpoint["sources"], checkpoint["outputs"], correction
        )
    ):
        raise CampaignContractError(
            "campaign effective checkpoint identity is inconsistent"
        )


def _append_snapshot(snapshot: LedgerSnapshot, rows: Iterable[dict[str, Any]]) -> LedgerSnapshot:
    raw = snapshot.raw + b"".join(canonical_bytes(row) + b"\n" for row in rows)
    return _snapshot_from_raw(snapshot.path, snapshot.label, raw)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == raw:
        return
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


@dataclass(frozen=True)
class CampaignPlan:
    episodes: LedgerSnapshot
    h60: LedgerSnapshot
    session: LedgerSnapshot
    campaigns_before: LedgerSnapshot
    outcomes_before: LedgerSnapshot
    campaigns_after: LedgerSnapshot
    outcomes_after: LedgerSnapshot
    checkpoint: dict[str, Any]
    campaign_rows: tuple[dict[str, Any], ...]
    outcome_rows: tuple[dict[str, Any], ...]
    pending_outcomes: int
    # The checkpoint that was already on disk before this run — the caller
    # uses its schema to decide whether a v2 continuation requires an
    # activation receipt before any ledger write.
    existing_checkpoint: dict[str, Any] | None


def _plan(
    repo_root: Path,
    *,
    activation_receipt: dict[str, Any] | None = None,
) -> CampaignPlan:
    episodes = load_ledger(repo_root / EPISODES_PATH, EPISODES_PATH)
    h60 = load_ledger(repo_root / H60_PATH, H60_PATH)
    session = load_ledger(repo_root / SESSION_PATH, SESSION_PATH)
    campaigns = load_ledger(repo_root / CAMPAIGNS_PATH, CAMPAIGNS_PATH)
    outcomes = load_ledger(repo_root / OUTCOMES_PATH, OUTCOMES_PATH)
    checkpoint = _load_checkpoint(repo_root / CHECKPOINT_PATH)
    prefix_cache: PrefixCache = {}
    episode_groups = _validated_episode_groups(episodes)
    h60_map, session_map = _source_outcome_maps(
        episodes, h60, session, episode_groups=episode_groups
    )
    campaign_history, latest = _campaign_history(
        campaigns,
        episodes,
        groups=episode_groups,
        prefix_cache=prefix_cache,
    )
    # V2 continuation guard: the binding check fires FIRST, before the
    # canonical receipt validation that runs inside `build_effective_outcome_view`.
    # A tampered receipt on a v2 continuation must surface as "binding is
    # mismatched" (or "requires an activation receipt" when missing) rather
    # than as a canonical-shape failure inside the view builder.
    if (
        checkpoint is not None
        and checkpoint.get("schema") == CAMPAIGN_CHECKPOINT_V2_SCHEMA
    ):
        if activation_receipt is None:
            raise CampaignContractError(
                "campaign v2 checkpoint continuation requires an activation receipt"
            )
        correction_binding = checkpoint["correction"]
        if (
            activation_receipt.get("receipt_id")
            != correction_binding["activation_receipt_id"]
            or activation_receipt.get("activated_at")
            != correction_binding["activation_receipt_time"]
            or activation_receipt.get("receipt_sha256")
            != correction_binding["activation_receipt_sha256"]
            or activation_receipt.get("policy") != correction_binding["policy"]
        ):
            raise CampaignContractError(
                "campaign effective checkpoint activation receipt binding is mismatched"
            )
    # Active correction path: validate the exact physical prefix / policy /
    # receipt first and build the EffectiveOutcomeView BEFORE walking any
    # outcome history. The admitted rows are the only ones that go through
    # normal outcome-source validation; quarantined rows retain their raw
    # bytes / sha256 / physical ordinal and reserve the (revision, horizon)
    # semantic key WITHOUT going through the normal source-receipt path.
    if activation_receipt is not None:
        correction_policy = CorrectionPolicy.load_canonical()
        effective_view = build_effective_outcome_view(
            campaigns,
            outcomes,
            correction_policy,
            activation_receipt=activation_receipt,
        )
        outcome_source = effective_view.admitted_rows
    else:
        outcome_source = outcomes.rows
    existing_outcomes = _outcome_history(
        outcome_source,
        campaign_history,
        episodes,
        h60,
        session,
        h60_map=h60_map,
        session_map=session_map,
        prefix_cache=prefix_cache,
    )
    _verify_checkpoint(
        checkpoint, episodes, h60, session, campaigns, outcomes, activation_receipt
    )

    new_campaigns = _derive_campaign_revisions_from_groups(
        episodes, episode_groups, latest
    )
    campaigns_after = _append_snapshot(campaigns, new_campaigns)
    new_outcomes, pending = _derive_campaign_outcomes_from_maps(
        campaigns_after,
        existing_outcomes,
        h60_map,
        session_map,
        h60,
        session,
    )
    outcomes_after = _append_snapshot(outcomes, new_outcomes)
    next_checkpoint = _build_checkpoint(
        episodes, h60, session, campaigns_after, outcomes_after
    )
    return CampaignPlan(
        episodes=episodes,
        h60=h60,
        session=session,
        campaigns_before=campaigns,
        outcomes_before=outcomes,
        campaigns_after=campaigns_after,
        outcomes_after=outcomes_after,
        checkpoint=next_checkpoint,
        campaign_rows=tuple(new_campaigns),
        outcome_rows=tuple(new_outcomes),
        pending_outcomes=pending,
        existing_checkpoint=checkpoint,
    )


def _summary(
    plan: CampaignPlan,
    *,
    wrote: bool,
    write_skipped: str | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    phases = {"retrospective_context": 0, "prospective_after_rule_freeze": 0}
    for item in plan.campaigns_after.rows:
        phases[item.value["evidence_phase"]] += 1
    summary: dict[str, Any] = {
        "source_episodes": plan.episodes.count,
        "source_h60_outcomes": plan.h60.count,
        "source_session_outcomes": plan.session.count,
        "campaign_revisions_total": plan.campaigns_after.count,
        "campaign_revisions_appended": len(plan.campaign_rows) if wrote else 0,
        "campaign_revision_phases": phases,
        "campaign_outcomes_total": plan.outcomes_after.count,
        "campaign_outcomes_appended": len(plan.outcome_rows) if wrote else 0,
        "campaign_outcomes_pending": plan.pending_outcomes,
        "checkpoint_id": (checkpoint or plan.checkpoint)["checkpoint_id"],
        "wrote": wrote,
    }
    if write_skipped is not None:
        summary["write_skipped"] = write_skipped
    return summary


def run(
    *,
    root_dir: Path | None = None,
    dry_run: bool = False,
    before_checkpoint: Callable[[], None] | None = None,
    correction_activation_receipt_path: Path | None = None,
) -> dict[str, Any]:
    """Validate and, only on the nightly lane, append outputs checkpoint-last."""
    repo_root = (root_dir or Path(__file__).resolve().parent.parent).resolve()
    activation_receipt = (
        _load_activation_receipt(correction_activation_receipt_path)
        if correction_activation_receipt_path is not None
        else None
    )
    if dry_run or not nightly_advance_enabled():
        plan = _plan(repo_root, activation_receipt=activation_receipt)
        checkpoint = _effective_checkpoint_for_plan(plan, activation_receipt)
        return _summary(
            plan,
            wrote=False,
            write_skipped=("dry_run" if dry_run else "COLLECT_LANE is not nightly"),
            checkpoint=checkpoint,
        )

    lock_name = _sha256(str(repo_root).encode("utf-8"))[:16]
    lock_path = Path(tempfile.gettempdir()) / f"options-signal-campaign-{lock_name}.lock"
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        plan = _plan(repo_root, activation_receipt=activation_receipt)
        checkpoint = _effective_checkpoint_for_plan(plan, activation_receipt)
        _atomic_write(repo_root / CAMPAIGNS_PATH, plan.campaigns_after.raw)
        _atomic_write(repo_root / OUTCOMES_PATH, plan.outcomes_after.raw)
        if before_checkpoint is not None:
            before_checkpoint()
        _atomic_write(
            repo_root / CHECKPOINT_PATH,
            canonical_bytes(checkpoint) + b"\n",
        )
        return _summary(plan, wrote=True, checkpoint=checkpoint)


def _load_activation_receipt(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise CampaignContractError(
            "campaign correction activation receipt is unavailable"
        )
    raw = resolved.read_bytes()
    try:
        value = _strict_loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise CampaignContractError(
            "campaign correction activation receipt is malformed"
        ) from exc
    if not isinstance(value, dict) or canonical_bytes(value) + b"\n" != raw:
        raise CampaignContractError(
            "campaign correction activation receipt is not canonical JSON"
        )
    # Validate shape only here. The full canonical check (digest consistency,
    # policy block match against the correction policy) is deferred to
    # `_verify_activation_receipt` so the v2 continuation binding check in
    # `_verify_effective_checkpoint` is the FIRST failure when a tampered
    # receipt continues an existing v2 checkpoint.
    _verify_receipt_shape(value)
    return value


def _effective_checkpoint_for_plan(
    plan: CampaignPlan,
    activation_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    existing_schema = (
        plan.existing_checkpoint["schema"]
        if plan.existing_checkpoint is not None
        else None
    )
    # V2 continuation: once an effective checkpoint has been written to
    # disk, EVERY continuation requires an eligible exact-bound activation
    # receipt that matches the recorded binding. Missing or mismatched
    # receipt fails BEFORE any ledger / checkpoint write here. The default
    # never-activated v1 path is unchanged: no existing v2 → no receipt
    # required → v1 checkpoint returned as before.
    if existing_schema == CAMPAIGN_CHECKPOINT_V2_SCHEMA:
        if activation_receipt is None:
            raise CampaignContractError(
                "campaign v2 checkpoint continuation requires an activation receipt"
            )
        recorded = plan.existing_checkpoint["correction"]
        if (
            activation_receipt["receipt_id"] != recorded["activation_receipt_id"]
            or activation_receipt["activated_at"]
            != recorded["activation_receipt_time"]
            or activation_receipt["receipt_sha256"]
            != recorded["activation_receipt_sha256"]
            or activation_receipt["policy"] != recorded["policy"]
        ):
            raise CampaignContractError(
                "campaign v2 checkpoint activation receipt binding is mismatched"
            )
    if activation_receipt is None:
        return plan.checkpoint
    policy = CorrectionPolicy.load_canonical()
    view = build_effective_outcome_view(
        plan.campaigns_after,
        plan.outcomes_after,
        policy,
        activation_receipt=activation_receipt,
    )
    return _build_effective_checkpoint(
        plan.episodes,
        plan.h60,
        plan.session,
        view,
        activation_receipt,
    )


__all__ = [
    "CAMPAIGN_SCHEMA",
    "CAMPAIGN_OUTCOME_SCHEMA",
    "CAMPAIGN_CHECKPOINT_SCHEMA",
    "CAMPAIGNS_PATH",
    "OUTCOMES_PATH",
    "CHECKPOINT_PATH",
    "FALSE_AUTHORITY",
    "CampaignContractError",
    "LedgerRow",
    "LedgerSnapshot",
    "canonical_bytes",
    "canonical_strike",
    "CAMPAIGN_CHECKPOINT_V2_SCHEMA",
    "CORRECTION_ACTIVATION_SCHEMA",
    "CorrectionPolicy",
    "EffectiveOutcomeView",
    "build_effective_outcome_view",
    "derive_campaign_revisions",
    "derive_campaign_outcomes",
    "load_ledger",
    "verify_campaign_receipt",
    "run",
    "validate_campaign",
    "validate_campaign_outcome",
    "validate_checkpoint",
    "validate_episode",
]
