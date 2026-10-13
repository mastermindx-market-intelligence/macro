"""Activated Options Alpha candidate composition and publication boundary."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.options_alpha_candidate_feed import (  # noqa: E402
    _validate_activation_receipt,
    canonical_bytes,
    compose_candidate_feed,
)
from engine.options_alpha_candidate_outcome_enrichment import (  # noqa: E402
    enrich_candidate_outcomes,
)
from engine.options_signal_campaign import (  # noqa: E402
    CAMPAIGNS_PATH,
    CHECKPOINT_PATH,
    EPISODES_PATH,
    H60_PATH,
    OUTCOMES_PATH,
    SESSION_PATH,
    CorrectionPolicy,
    _load_activation_receipt,
    _load_checkpoint,
    _verify_checkpoint,
    build_effective_outcome_view,
    load_ledger,
)
from scripts.publish_options_alpha_candidate_r2 import (  # noqa: E402
    _load as _load_publisher_journal,
)
from scripts.publish_options_alpha_candidate_r2 import (  # noqa: E402
    publish_pair,
    read_pair,
    recover_pending_pair,
)

ACTIVATION_PATH = Path(
    "research/options_estate/options_alpha_candidate_feed_activation_receipt_v1.json"
)
POLICY_PATH = Path(
    "research/options_estate/options_alpha_candidate_formation_policy_v2.json"
)
CORRECTION_RECEIPT_PATH = Path(
    "research/options_estate/options_signal_campaign_correction_activation_receipt_v1.json"
)
_SESSION = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MEASURED = (
    "source_print_count",
    "nbbo_valid_print_count",
    "nbbo_premium_coverage",
    "nbbo_covered_premium_usd",
    "source_premium_usd",
)


class DailyCandidateError(RuntimeError):
    pass


def _strict_object(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise DailyCandidateError(f"duplicate JSON key in {path}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)),
        )
    except (OSError, TypeError, ValueError) as exc:
        raise DailyCandidateError(f"invalid JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise DailyCandidateError(f"JSON object required: {path}")
    return value


def _clock() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _episode_helpers() -> tuple[Any, Any, Any, Any]:
    # Keep the inactive path independent of optional live-flow dependencies.
    from scripts.build_options_signal_episode import (
        _events_from_stage,
        _r2_client,
        discover_event_sessions,
        fetch_event_stage,
    )

    return _events_from_stage, _r2_client, discover_event_sessions, fetch_event_stage


def _microstructure(
    records: list[dict[str, Any]], session: str
) -> dict[str, dict[str, Any]]:
    """Use exactly the five measured fields from the original decision event."""
    originals: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("kind") == "decision":
            event_id, decision = record.get("event_id"), record.get("event")
            if (
                type(event_id) is not str
                or not isinstance(decision, dict)
                or decision.get("id") != event_id
                or event_id in originals
            ):
                raise DailyCandidateError(
                    "invalid or duplicate original decision event"
                )
            originals[event_id] = decision
    result = {}
    events_from_stage, _, _, _ = _episode_helpers()
    for event in events_from_stage(records, expected_session_date=session):
        event_id = event.get("id")
        original = originals.get(event_id)
        measured = original.get("microstructure") if original else None
        if type(event_id) is not str or not event_id or event_id in result:
            raise DailyCandidateError("invalid or duplicate stage event id")
        # Legacy stage rows predate the additive OA-1T measurement.  Omit
        # those IDs so formation records truthful missing measurement rather
        # than inventing a zero or blocking later measured rows.
        if measured is None:
            continue
        if (
            not isinstance(measured, dict)
            or measured.get("schema") != "options.trade_nbbo_microstructure/v1"
        ):
            raise DailyCandidateError(
                f"event {event_id} has malformed declared microstructure"
            )
        if not set(_MEASURED).issubset(measured):
            continue
        row = {
            "schema": "options.trade_nbbo_microstructure/v1",
            "source_event_id": event_id,
            "event_id": event_id,
            "source_path": f"live_flow/events/{session}.jsonl",
            "event_time": original["ts"],
            "observed_at": original["observed_at"],
            "available_at": event["available_at"],
            "decision_path": "options.trade_nbbo_microstructure/v1",
            "event_digest_sha256": hashlib.sha256(
                canonical_bytes(original)
            ).hexdigest(),
        }
        row.update(
            {key: measured[key] for key in _MEASURED}
        )  # no defaults, rounding, or derived coverage
        result[event_id] = row
    return result


def _load_sources(root: Path, correction_path: Path) -> tuple[Any, Any, dict[str, Any]]:
    campaigns, outcomes = load_ledger(
        root / CAMPAIGNS_PATH, CAMPAIGNS_PATH
    ), load_ledger(root / OUTCOMES_PATH, OUTCOMES_PATH)
    episodes, h60 = load_ledger(root / EPISODES_PATH, EPISODES_PATH), load_ledger(
        root / H60_PATH, H60_PATH
    )
    session = load_ledger(root / SESSION_PATH, SESSION_PATH)
    correction = _load_activation_receipt(correction_path)
    checkpoint = _load_checkpoint(root / CHECKPOINT_PATH)
    if (
        checkpoint is None
        or checkpoint.get("schema") != "options.signal_campaign_checkpoint/v2"
    ):
        raise DailyCandidateError(
            "active publication requires an effective v2 campaign checkpoint"
        )
    _verify_checkpoint(
        checkpoint, episodes, h60, session, campaigns, outcomes, correction
    )
    outputs = checkpoint["outputs"]
    if (
        outputs["campaigns"]["records"] != campaigns.count
        or outputs["outcomes"]["records"] != outcomes.count
    ):
        raise DailyCandidateError(
            "active publication requires checkpoint receipts for the exact current ledger prefixes"
        )
    return (
        campaigns,
        build_effective_outcome_view(
            campaigns,
            outcomes,
            CorrectionPolicy.load_canonical(root),
            activation_receipt=correction,
        ),
        correction,
    )


def run(
    *,
    root: Path,
    client: Any | None,
    bucket: str,
    clock: Callable[[], str] = _clock,
    lock_path: Path | None = None,
    correction_receipt_path: Path | None = None,
    sessions: Callable[[], list[str]] | None = None,
    fetch: Callable[[str], list[dict[str, Any]] | None] | None = None,
    allow_dry_compose: bool = False,
) -> dict[str, Any]:
    activation_path = root / ACTIVATION_PATH
    if not activation_path.exists():
        # Inactive means no R2 reads/writes, no journal recovery and no clock.
        return {
            "produced": False,
            "state": "inactive",
            "reason": "activation_receipt_absent",
        }
    activation, policy = _strict_object(activation_path), _strict_object(
        root / POLICY_PATH
    )
    freeze, boundary = activation.get("policy_freeze_at"), activation.get(
        "activation_boundary_at"
    )
    if activation.get("all_preconditions_cleared") is not True:
        return {
            "produced": False,
            "state": "inactive",
            "reason": "activation_preconditions_uncleared",
        }
    if type(freeze) is not str or type(boundary) is not str:
        raise DailyCandidateError(
            "activation receipt must supply explicit freeze and boundary"
        )
    # Schema, exact named prerequisite order, eligible disposition, and fences
    # are all checked before journal recovery can make any R2 effect.
    normalized_activation = _validate_activation_receipt(
        activation, policy_freeze_at=freeze
    )
    if not allow_dry_compose and (client is None or not bucket):
        raise DailyCandidateError(
            "active publication requires configured R2 client and bucket"
        )
    target_lock = lock_path or root / "data/options_alpha_candidate.lock"
    if client is not None:
        pending = _load_publisher_journal(target_lock.with_suffix(".transaction.json"))
        if pending is not None:
            import base64

            try:
                pending_feed = json.loads(
                    base64.b64decode(pending["payload"], validate=True)
                )
                pending_activation = pending_feed["activation"]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise DailyCandidateError(
                    "pending publisher journal is malformed"
                ) from exc
            if (
                pending_activation.get("activation_receipt_id")
                != normalized_activation["activation_receipt_id"]
                or pending_activation.get("activation_receipt_digest_sha256")
                != normalized_activation["activation_receipt_digest_sha256"]
            ):
                raise DailyCandidateError(
                    "pending publisher journal activation binding differs from current receipt"
                )
        recovered = recover_pending_pair(
            client=client, bucket=bucket, lock_path=target_lock, now=clock
        )
        if recovered is not None:
            return {"produced": True, "state": "recovered", "publication": recovered}
    campaigns, view, correction = _load_sources(
        root, correction_receipt_path or root / CORRECTION_RECEIPT_PATH
    )
    if sessions is None or fetch is None:
        _, _, default_sessions, default_fetch = _episode_helpers()
        sessions, fetch = sessions or default_sessions, fetch or default_fetch
    micro, seen = {}, set()
    for session in sessions():
        if (
            type(session) is not str
            or not _SESSION.fullmatch(session)
            or session in seen
        ):
            raise DailyCandidateError(
                "event-stage sessions must be unique canonical dates"
            )
        seen.add(session)
        rows = fetch(session)
        if rows is None:
            raise DailyCandidateError(f"durable event stage unavailable: {session}")
        for event_id, row in _microstructure(rows, session).items():
            if event_id in micro:
                raise DailyCandidateError(f"duplicate event id: {event_id}")
            micro[event_id] = row
    sealed = read_pair(client, bucket) if client is not None else None
    prior = sealed.feed if sealed is not None else None
    feed = compose_candidate_feed(
        campaigns=campaigns,
        microstructure_map=micro,
        policy=policy,
        activation_receipt=activation,
        observation_clock=clock(),
        prior_feed=prior,
        policy_freeze_at=freeze,
    )
    feed = enrich_candidate_outcomes(
        feed, effective_outcomes=view, correction_activation_receipt=correction
    )
    if client is None:
        if not allow_dry_compose:
            raise DailyCandidateError(
                "active publication requires configured R2 client and bucket"
            )
        return {"produced": True, "state": "composed", "feed": feed}
    state = publish_pair(
        client=client,
        bucket=bucket,
        feed=feed,
        payload=canonical_bytes(feed),
        lock_path=target_lock,
        now=clock,
    )
    return {"produced": True, "state": state, "feed_id": feed["feed_id"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--bucket", default="")
    parser.add_argument("--correction-activation-receipt", type=Path)
    parser.add_argument(
        "--publication-lock",
        type=Path,
        help="Stable host-local journal/lock path outside the checkout for scheduled publication",
    )
    args = parser.parse_args(argv)
    # Do not import optional boto/yaml live-flow dependencies merely to report
    # the ordinary inactive state.
    activation_path = args.root / ACTIVATION_PATH
    if (
        not activation_path.exists()
        or _strict_object(activation_path).get("all_preconditions_cleared") is not True
    ):
        print(
            json.dumps(
                run(root=args.root, client=None, bucket=args.bucket), sort_keys=True
            )
        )
        return 0
    _, r2_client, _, _ = _episode_helpers()
    client = r2_client()
    bucket = args.bucket or os.environ.get("R2_BUCKET", "")
    if client is None or not bucket:
        raise DailyCandidateError("active publication requires R2 client and R2_BUCKET")
    print(
        json.dumps(
            run(
                root=args.root,
                client=client,
                bucket=bucket,
                correction_receipt_path=args.correction_activation_receipt,
                lock_path=args.publication_lock,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
