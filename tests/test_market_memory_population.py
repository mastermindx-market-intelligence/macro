"""P0 outcome-blind W2C population manifest contracts.

Every test here drives the real W2C owner: real tracked registration, real
trusted owner captures written by ``market_memory_trusted``, a real private
technical actual-output store created by its own owner module, and real
opportunities/population receipts written by the real accrual writer.  The
population module is only ever exercised as a consumer of the owner's public
outcome-blind read seam and public owner generation readers.

The offline technical fixture uses the owner's own empty-store
initialization because the pinned Massive entitlement record artifact is not
part of this source bundle, so no real technical capture can be created
offline.  That is a fixture limitation only: the manifest contract is still
exercised against real owner-authored stores, rows and receipts, and the
abstained rows those stores produce still declare exact trusted/technical
generation references whose closure is authenticated against the declared
generation.
"""

from __future__ import annotations

import ast
import json
import os
from types import SimpleNamespace
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver
from jsonschema.exceptions import SchemaError

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_experience_accrual as accrual
from engine.neuralweb import market_memory_identity as identity
from engine.neuralweb import market_memory_pit
from engine.neuralweb import market_memory_population as population
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_technical_store as technical_store
from engine.neuralweb import market_memory_trusted as trusted
from lib import nyse_calendar

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
ACTIVATION = date(2026, 8, 17)
INSTALL_CLOCK = "2026-08-11T20:00:00Z"
FIRST_SESSION = "2026-08-17"
FIRST_WINDOW = "2026-08-18T04:40:00Z"
SECOND_WINDOW = "2026-08-19T04:40:00Z"
FROZEN_TECHNICAL_CLOCK = datetime(2026, 8, 18, 2, tzinfo=timezone.utc)
MEMBERSHIP_FIELDS = frozenset(
    {
        "session",
        "opportunity_id",
        "disposition",
        "reason",
        "cutoff",
        "source_pins",
        "decision_state_projection",
        "decision_state_projection_reason",
    }
)
FORBIDDEN_MEMBERSHIP_TOKENS = (
    "latest_outcomes",
    "outcome_revision",
    "outcome_observed",
    "outcome_unavailable",
    "outcome_censored",
    "revision_number",
    "scoreable",
    "matured",
    "maturity",
)
SCHEMA_STORE: dict[str, dict] = {}


def test_schema_store_validates_anonymous_schemas_without_registering_a_fake_id(tmp_path, monkeypatch):
    schema_dir = tmp_path / "contracts" / "market_memory"
    schema_dir.mkdir(parents=True)
    named = {"$id": "https://example.test/fixture.schema.json", "type": "object"}
    (schema_dir / "a-anonymous.schema.json").write_text(json.dumps({"type": "object"}))
    (schema_dir / "b-named.schema.json").write_text(json.dumps(named))
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setitem(globals(), "SCHEMA_STORE", {})
    assert _schema_store() == {named["$id"]: named}


def test_schema_store_does_not_ignore_invalid_anonymous_schemas_or_leave_partial_cache(tmp_path, monkeypatch):
    schema_dir = tmp_path / "contracts" / "market_memory"
    schema_dir.mkdir(parents=True)
    (schema_dir / "a-named.schema.json").write_text(json.dumps({"$id": "https://example.test/fixture.schema.json"}))
    (schema_dir / "b-invalid.schema.json").write_text(json.dumps({"type": "not-a-json-schema-type"}))
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setitem(globals(), "SCHEMA_STORE", {})
    with pytest.raises(SchemaError):
        _schema_store()
    assert SCHEMA_STORE == {}


def _schema_store() -> dict[str, dict]:
    if not SCHEMA_STORE:
        loaded = {}
        for path in sorted((ROOT / "contracts" / "market_memory").glob("*.schema.json")):
            schema = json.loads(path.read_text())
            Draft202012Validator.check_schema(schema)
            # Anonymous schemas are valid JSON Schema, but have no URI to
            # register for reference resolution. Still validate every schema.
            if "$id" in schema:
                loaded[schema["$id"]] = schema
        SCHEMA_STORE.update(loaded)
    return SCHEMA_STORE


def _manifest_validator() -> Draft202012Validator:
    schema = _schema_store()[
        "https://mastermind-x.com/contracts/market_memory/population_manifest.v1.schema.json"
    ]
    return Draft202012Validator(
        schema,
        resolver=RefResolver(
            base_uri=schema["$id"], referrer=schema, store=_schema_store()
        ),
    )


def _clock(value: str):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return lambda: parsed.astimezone(timezone.utc)


def _experience_root(tmp_path: Path) -> Path:
    return tmp_path / "market-memory" / "state" / "experience-v1"


def _technical_root(tmp_path: Path) -> Path:
    return tmp_path / "market-memory" / "state" / "technicals-v1"


def _public_trusted_root(tmp_path: Path) -> Path:
    return tmp_path / "market-memory" / "public" / "trusted-v1"


def _private_trusted_root(tmp_path: Path) -> Path:
    return tmp_path / "market-memory" / "state" / "context-projection"


def _raw_regime(*, growth_score: float = 0.133) -> dict:
    """Exact fixture body carried from tests/test_market_memory_trusted.py."""

    return {
        "schema_version": 1,
        "asof": "2026-08-10",
        "date": "2026-08-10",
        "quad": "Q2",
        "quad_name": "forbidden human label",
        "label": "must never enter trusted public objects",
        "raw_quad": "Q2",
        "pending_quad": None,
        "pending_days": 0,
        "pending_need": 7,
        "growth_score": growth_score,
        "inflation_score": 0.4,
        "growth_confidence": 0.1,
        "inflation_confidence": 0.3,
        "confidence": 0.2,
        "liquidity_overlay": "contracting",
        "cycle_tag": "late",
        "transition_state": "TRANSITIONING",
        "transition_state_raw": "WEAKENING",
        "transition_ratcheted": True,
        "transition_dwell_remaining": 5,
        "transition_flags": {
            "flag_breadth_price": False,
            "flag_credit_equity": False,
            "flag_ratio_inflection": False,
            "flag_inflation_basket": False,
            "flag_confidence_decay": True,
            "flag_gex": False,
            "flag_rotation_persistence": True,
        },
        "options": {
            "signal_episode": "forbidden",
            "H+60": {"outcome": 0.9},
            "U-CHAIN": {"rank": 1},
        },
        "Prophet": {"candidate": True, "gate": True, "size": 1.0},
        "freshness": {
            "asof": "2026-08-10",
            "built_at": "2026-08-10T09:55:00Z",
            "age_days": 0,
            "age_sessions": 0,
            "max_age_sessions": 1,
            "stale": False,
        },
    }


def _capture_trusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    session: date,
) -> None:
    raw = _raw_regime()
    session_text = session.isoformat()
    built = datetime.combine(
        session, datetime.min.time(), tzinfo=timezone.utc
    ) + timedelta(hours=23)
    raw["asof"] = session_text
    raw["date"] = session_text
    raw["freshness"]["asof"] = session_text
    raw["freshness"]["built_at"] = built.isoformat().replace("+00:00", "Z")
    source = tmp_path / "latest.json"
    body = (
        json.dumps(raw, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode()
    source.write_bytes(body)
    monkeypatch.setattr(projection, "_utc_now", lambda: built + timedelta(minutes=1))
    snapshot = projection.build_macro_regime_snapshot(source)
    monkeypatch.setattr(identity, "_utc_now", lambda: built + timedelta(minutes=2))
    identity_evidence = identity.build_current_spy_identity()
    monkeypatch.setattr(trusted, "_utc_now", lambda: built + timedelta(minutes=3))
    monkeypatch.setattr(pit, "_utc_now", lambda: built + timedelta(minutes=4))
    trusted.capture_trusted_regime_context(
        _public_trusted_root(tmp_path),
        _private_trusted_root(tmp_path),
        snapshot=snapshot,
        identity_evidence=identity_evidence,
        raw_source_body=body,
        deployed_commit=COMMIT,
    )


def _initialize_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    monkeypatch.setattr(
        technical_store, "_utc_now", lambda: FROZEN_TECHNICAL_CLOCK
    )
    technical_store.initialize_technical_actual_output_store(
        _technical_root(tmp_path)
    )
    _capture_trusted(tmp_path, monkeypatch, session=ACTIVATION)
    return _experience_root(tmp_path), _public_trusted_root(tmp_path), _technical_root(tmp_path)


def _run(
    tmp_path: Path,
    *,
    experience: Path,
    trusted_root: Path,
    technical_root: Path,
    clock: str,
) -> accrual.AccrualResult:
    return accrual.accrue_spy_experience(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        writer_commit=COMMIT,
        clock=_clock(clock),
    )


def _real_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, runs: int = 1):
    experience, trusted_root, technical_root = _initialize_store(
        tmp_path, monkeypatch
    )
    install = _run(
        tmp_path,
        experience=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        clock=INSTALL_CLOCK,
    )
    assert install.opportunity_ids == ()
    assert (experience / "registration_installation.json").is_file()
    for index in range(runs):
        _run(
            tmp_path,
            experience=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            clock=_window_clock(index),
        )
    return experience, trusted_root, technical_root


def _window_clock(index: int) -> str:
    day = date(2026, 8, 18) + timedelta(days=index)
    return f"{day.isoformat()}T04:40:00Z"


def _manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    through_session: str,
    trusted_root: Path | None = None,
    technical_root: Path | None = None,
    experience: Path | None = None,
    policy: object | None = None,
    runs: int = 1,
) -> dict:
    if experience is None:
        experience, default_trusted, default_technical = _real_store(
            tmp_path, monkeypatch, runs=runs
        )
    else:
        default_trusted = trusted_root
        default_technical = technical_root
    return population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root if trusted_root is not None else default_trusted,
        technical_root=(
            technical_root if technical_root is not None else default_technical
        ),
        through_session=through_session,
        policy=policy if policy is not None else _AllowPolicy(),
    )


class _AllowPolicy:
    """One explicit trusted-caller policy that returns a typed grant."""

    def __init__(self, scope: str = "research.readonly") -> None:
        self.scope = scope
        self.calls: list[tuple[str | None, str | None]] = []

    def authorize_population_manifest(
        self,
        *,
        repository_root: str,
        experience_root: str,
        through_session: str,
        registration_id: str | None,
        store_id: str | None,
    ) -> population.PopulationAccessGrant:
        self.calls.append((registration_id, store_id))
        return population.PopulationAccessGrant(
            policy_version=population.POPULATION_ACCESS_POLICY_VERSION,
            caller_scope=self.scope,
            granted=True,
            registration_id=registration_id,
            store_id=store_id,
            limitations=("authority_display_context_only",),
        )


class _SequencePolicy:
    """Grant the first N calls and deny every later call."""

    def __init__(self, grants: int) -> None:
        self.grants = grants
        self.calls = 0

    def authorize_population_manifest(
        self,
        *,
        repository_root: str,
        experience_root: str,
        through_session: str,
        registration_id: str | None,
        store_id: str | None,
    ) -> population.PopulationAccessGrant:
        self.calls += 1
        granted = self.calls <= self.grants
        return population.PopulationAccessGrant(
            policy_version=population.POPULATION_ACCESS_POLICY_VERSION,
            caller_scope="research.readonly",
            granted=granted,
            registration_id=registration_id,
            store_id=store_id,
        )


class _RaisingPolicy:
    def authorize_population_manifest(self, **_kwargs):
        raise RuntimeError("policy backend unavailable")


class _BrokenGrantPolicy:
    def authorize_population_manifest(self, **_kwargs):
        return {"granted": True}


def _watch_owner_opens(
    monkeypatch: pytest.MonkeyPatch, *roots: Path
) -> list[str]:
    """Record every owner-root file open and directory walk performed."""

    opened: list[str] = []
    targets = tuple(str(Path(root).resolve()) for root in roots)
    real_open = os.open

    def spy_open(path: object, *args: object, **kwargs: object):
        try:
            text = os.fspath(path)  # type: ignore[arg-type]
        except TypeError:
            text = ""
        if text and any(text.startswith(target) for target in targets):
            opened.append(text)
        return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

    real_read_bytes = Path.read_bytes

    def spy_read_bytes(self: Path):
        text = str(self)
        if any(text.startswith(target) for target in targets):
            opened.append(text)
        return real_read_bytes(self)

    real_iterdir = Path.iterdir

    def spy_iterdir(self: Path):
        text = str(self)
        if any(text.startswith(target) for target in targets):
            opened.append(f"{text}#iterdir")
        return real_iterdir(self)

    monkeypatch.setattr(os, "open", spy_open)
    monkeypatch.setattr(Path, "read_bytes", spy_read_bytes)
    monkeypatch.setattr(Path, "iterdir", spy_iterdir)
    return opened


def _strings(value: object) -> list[str]:
    if type(value) is str:
        return [value]
    if type(value) is dict:
        found: list[str] = []
        for key, item in value.items():
            found.append(key)
            found.extend(_strings(item))
        return found
    if type(value) is list:
        found = []
        for item in value:
            found.extend(_strings(item))
        return found
    return []


def test_manifest_keeps_the_complete_declared_denominator_with_typed_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    manifest = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        through_session="2026-08-20",
        policy=_AllowPolicy(),
    )
    assert manifest["through_session"] == "2026-08-20"
    sessions = manifest["expected_sessions"]
    assert sessions == [
        item.isoformat()
        for item in nyse_calendar.sessions_between(
            ACTIVATION, date(2026, 8, 20)
        )
    ]
    rows = manifest["census"]["rows"]
    assert [row["session"] for row in rows] == sessions
    dispositions = [row["disposition"] for row in rows]
    counts = manifest["census"]["counts"]
    assert counts["expected"] == len(sessions)
    assert counts["recorded"] == dispositions.count("admitted") + dispositions.count(
        "abstained"
    ) + dispositions.count("missed")
    assert counts["abstained"] == 1
    assert counts["unrecorded"] == dispositions.count("unrecorded") == 3
    assert [gap["session"] for gap in manifest["census"]["gaps"]] == [
        row["session"] for row in rows if row["disposition"] == "unrecorded"
    ]
    assert all(gap["reason"] == population.GAP_REASON for gap in manifest["census"]["gaps"])
    assert list(_manifest_validator().iter_errors(manifest)) == []


def test_no_population_yet_still_declares_a_finite_gap_only_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _initialize_store(
        tmp_path, monkeypatch
    )
    _run(
        tmp_path,
        experience=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        clock=INSTALL_CLOCK,
    )
    manifest = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        through_session=FIRST_SESSION,
        policy=_AllowPolicy(),
    )
    assert manifest["census"]["counts"] == {
        "expected": 1,
        "recorded": 0,
        "admitted": 0,
        "abstained": 0,
        "missed": 0,
        "unrecorded": 1,
    }
    audit = manifest["audit"]
    assert audit["population_receipt_id"] is None
    assert audit["population_receipt_sha256"] is None
    assert audit["membership_independent_of_audit"] is True
    assert manifest["claims"]["population_receipt_authenticated"] is False
    assert manifest["source_closure"]["status"] == "no_source_refs_declared"
    assert list(_manifest_validator().iter_errors(manifest)) == []


def test_membership_is_invariant_when_population_audit_identity_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    before = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        through_session=FIRST_SESSION,
        policy=_AllowPolicy(),
    )
    _run(
        tmp_path,
        experience=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        clock=SECOND_WINDOW,
    )
    after = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=trusted_root,
        technical_root=technical_root,
        through_session=FIRST_SESSION,
        policy=_AllowPolicy(),
    )
    assert before["membership"]["membership_sha256"]
    assert (
        before["membership"]["membership_sha256"]
        == after["membership"]["membership_sha256"]
    )
    assert (
        before["audit"]["population_receipt_sha256"]
        != after["audit"]["population_receipt_sha256"]
    )
    assert (
        before["audit"]["population_receipt_id"]
        != after["audit"]["population_receipt_id"]
    )
    assert (
        before["audit"]["population_observed_at"]
        != after["audit"]["population_observed_at"]
    )
    assert before["audit"]["population_writer_commit"] == after["audit"][
        "population_writer_commit"
    ]
    assert before["manifest_id"] != after["manifest_id"]
    assert (
        before["audit"]["population_owner_generation_refs"]
        != after["audit"]["population_owner_generation_refs"]
    )
    assert after["audit"]["population_receipt_through_session"] == "2026-08-18"
    assert after["census"]["counts"]["recorded"] == 1
    assert before["census"] == after["census"]
    assert before["source_closure"] == after["source_closure"]


def test_membership_digest_is_recomputable_label_free_and_outcome_blind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session="2026-08-19")
    membership_body = {
        "schema": population.POPULATION_MEMBERSHIP_SCHEMA,
        "membership_version": 1,
        "registration_id": manifest["owner"]["registration_id"],
        "registration_sha256": manifest["owner"]["registration_sha256"],
        "census_basis": manifest["census_basis"],
        "through_session": manifest["through_session"],
        "expected_sessions": manifest["expected_sessions"],
        "rows": manifest["census"]["rows"],
    }
    canonical = json.dumps(
        membership_body,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    import hashlib

    assert (
        hashlib.sha256(canonical).hexdigest()
        == manifest["membership"]["membership_sha256"]
    )
    for row in manifest["census"]["rows"]:
        assert set(row) == MEMBERSHIP_FIELDS
        if row["source_pins"] is not None:
            assert "trusted_capture" in row["source_pins"]
    body = json.dumps(
        {"census": manifest["census"], "eligibility": manifest["eligibility"]},
        sort_keys=True,
    ).encode("utf-8")
    for token in FORBIDDEN_MEMBERSHIP_TOKENS:
        assert token.encode() not in body
    # The only place those dimensions may be named is the membership section's
    # explicit exclusion declaration, and neither the audit section nor any
    # census row carries outcome vocabulary.
    audit_body = json.dumps(manifest["audit"], sort_keys=True).encode("utf-8")
    for token in FORBIDDEN_MEMBERSHIP_TOKENS:
        assert token.encode() not in audit_body
    assert manifest["membership"]["excluded_identity_dimensions"] == list(
        population.MEMBERSHIP_EXCLUDED_DIMENSIONS
    )
    # Label-free: the raw source labels never enter the manifest either.
    full_body = json.dumps(manifest, sort_keys=True).encode("utf-8")
    for label in ("forbidden human label", "quad_name", "transition_state_raw"):
        assert label.encode() not in full_body


def test_manifest_is_deterministic_for_one_authenticated_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    arguments = {
        "experience_root": experience,
        "trusted_root": trusted_root,
        "technical_root": technical_root,
        "through_session": "2026-08-19",
        "policy": _AllowPolicy(),
    }
    first = population.build_population_manifest(ROOT, **arguments)
    second = population.build_population_manifest(ROOT, **arguments)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["manifest_id"] == second["manifest_id"]
    assert (
        first["membership"]["membership_sha256"]
        == second["membership"]["membership_sha256"]
    )
    assert [row["session"] for row in first["census"]["rows"]] == [
        row["session"] for row in second["census"]["rows"]
    ]
    assert [
        item["status"] for item in first["source_closure"]["generation_closures"]
    ] == [item["status"] for item in second["source_closure"]["generation_closures"]]


def test_independent_stores_differ_only_in_owner_identity_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def build(where: Path) -> dict:
        experience, trusted_root, technical_root = _real_store(
            where, monkeypatch, runs=1
        )
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    first = build(tmp_path / "one")
    second = build(tmp_path / "two")
    identity_fields = {
        "store_id",
        "generation_id",
        "generation_sha256",
        "capture_id",
        "context_id",
        "opportunity_id",
        "manifest_id",
        "membership_sha256",
        "installation_id",
    }
    differing: list[str] = []

    def walk(left: object, right: object, path: str) -> None:
        if type(left) is dict and type(right) is dict:
            for key in sorted(set(left) | set(right)):
                walk(left.get(key), right.get(key), f"{path}/{key}")
            return
        if type(left) is list and type(right) is list and len(left) == len(right):
            for index, (one, two) in enumerate(zip(left, right)):
                walk(one, two, f"{path}/{index}")
            return
        if left != right:
            differing.append(path)

    walk(first, second, "")
    assert differing, "independent stores must still be structurally comparable"
    assert all(
        path.rsplit("/", 1)[-1] in identity_fields or path.startswith("/audit/")
        for path in differing
    ), differing
    assert first["census"]["counts"] == second["census"]["counts"]
    assert [
        (row["session"], row["disposition"], row["reason"])
        for row in first["census"]["rows"]
    ] == [
        (row["session"], row["disposition"], row["reason"])
        for row in second["census"]["rows"]
    ]
    assert first["eligibility"]["capture_availability"] == second["eligibility"][
        "capture_availability"
    ]
    assert len(first["membership"]["membership_sha256"]) == 64


def test_rights_are_denied_before_any_owner_path_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    policy = _AllowPolicy()
    opened = _watch_owner_opens(monkeypatch, experience, trusted_root, technical_root)
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_SequencePolicy(grants=0),
        )
    assert opened == []
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=True,
        )
    assert opened == []
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_RaisingPolicy(),
        )
    assert opened == []
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_BrokenGrantPolicy(),
        )
    assert opened == []
    assert policy.calls == []


def test_rights_are_rechecked_on_every_call_and_before_disclosure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    arguments = {
        "experience_root": experience,
        "trusted_root": trusted_root,
        "technical_root": technical_root,
        "through_session": FIRST_SESSION,
    }
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT, policy=_SequencePolicy(grants=1), **arguments
        )
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.build_population_manifest(
            ROOT, policy=_SequencePolicy(grants=2), **arguments
        )
    granted = population.build_population_manifest(
        ROOT, policy=_SequencePolicy(grants=3), **arguments
    )
    assert granted["manifest_id"]
    for grants in range(0, 6):
        policy = _SequencePolicy(grants=grants)
        try:
            population.build_population_manifest(ROOT, policy=policy, **arguments)
        except population.MarketMemoryPopulationAccessError:
            assert grants < 3
        else:
            assert grants >= 3
        assert policy.calls == min(grants + 1, 3)


def test_rights_layer_is_distinct_from_and_precedes_source_authentication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    # A granted rights layer does not authenticate a missing owner store: the
    # source layer still reports typed retained gaps instead of a substitution.
    absent = tmp_path / "absent" / "trusted-v1"
    manifest = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=absent,
        technical_root=technical_root,
        through_session=FIRST_SESSION,
        policy=_AllowPolicy(),
    )
    closure = manifest["source_closure"]
    assert closure["status"] == "retained_gaps"
    trusted_closure = next(
        item
        for item in closure["generation_closures"]
        if item["role"] == "trusted"
    )
    assert trusted_closure["status"] == "owner_store_absent"
    assert trusted_closure["reason"] == population.STORE_ABSENT_REASON
    assert manifest["claims"]["source_closure_complete"] is False
    assert manifest["eligibility"]["row_qualification"][0][
        "capture_available"
    ] == "generation_not_authenticated"
    assert manifest["eligibility"]["row_qualification"][0][
        "comparison_eligibility"
    ] == "blocked_by_source_qualification"


def test_forged_registration_is_rejected_before_any_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    forged_repository = tmp_path / "forged-repo"
    (forged_repository / "config").mkdir(parents=True)
    (forged_repository / "lib").mkdir(parents=True)
    (forged_repository / "lib" / "nyse_calendar.py").write_bytes(
        (ROOT / "lib" / "nyse_calendar.py").read_bytes()
    )
    registration = json.loads(
        (ROOT / "config" / "market_memory_spy_experience_registration.v1.json").read_text()
    )
    registration["spec"]["population"]["pilot_expected_sessions"] = 125
    (forged_repository / "config" / "market_memory_spy_experience_registration.v1.json").write_text(
        json.dumps(registration, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with pytest.raises(accrual.MarketMemoryExperienceRegistrationError):
        population.build_population_manifest(
            forged_repository,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )
    with pytest.raises(accrual.MarketMemoryExperienceRegistrationError):
        accrual.read_outcome_blind_population_ledger(
            forged_repository, experience_root=experience
        )


def test_forged_receipt_head_prefix_and_rows_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    head = json.loads((experience / "population_HEAD.json").read_text())
    receipt_path = (
        experience
        / "population_receipts"
        / f"{head['population_receipt_id']}.json"
    )
    original_receipt_bytes = receipt_path.read_bytes()

    def forged_manifest() -> dict:
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    assert forged_manifest()["manifest_id"]

    # Forged receipt body: HEAD no longer binds its full content.
    receipt = json.loads(original_receipt_bytes)
    receipt["counts"]["admitted"] = 1
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()

    # Forged declared denominator: the receipt prefix no longer matches the
    # frozen calendar census it was written from.
    receipt_path.write_bytes(original_receipt_bytes)
    receipt = json.loads(original_receipt_bytes)
    receipt["expected_sessions"] = receipt["expected_sessions"][1:]
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()

    # Restored bytes authenticate again: the census is byte-for-byte stable.
    receipt_path.write_bytes(original_receipt_bytes)
    assert forged_manifest()["manifest_id"]


def test_forged_opportunity_row_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    row_path = experience / "opportunities" / f"{FIRST_SESSION}.json"
    row = json.loads(row_path.read_text())
    row["disposition"] = "admitted"
    row_path.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )


def test_missing_head_unheaded_or_pending_population_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )

    def forged_manifest() -> dict:
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    assert forged_manifest()["manifest_id"]
    (experience / "population_HEAD.json").unlink()
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()


def test_head_without_its_receipt_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )

    def forged_manifest() -> dict:
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    assert forged_manifest()["manifest_id"]
    head = json.loads((experience / "population_HEAD.json").read_text())
    receipt_path = (
        experience
        / "population_receipts"
        / f"{head['population_receipt_id']}.json"
    )
    receipt_path.unlink()
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()


def test_extra_unheaded_population_receipt_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )

    def forged_manifest() -> dict:
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    assert forged_manifest()["manifest_id"]
    head = json.loads((experience / "population_HEAD.json").read_text())
    receipt_path = (
        experience
        / "population_receipts"
        / f"{head['population_receipt_id']}.json"
    )
    forged_id = "mmspyexppop_" + "0" * 64
    (experience / "population_receipts" / f"{forged_id}.json").write_bytes(
        receipt_path.read_bytes()
    )
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()


def test_pending_publication_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )

    def forged_manifest() -> dict:
        return population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )

    assert forged_manifest()["manifest_id"]
    row_path = experience / "opportunities" / f"{FIRST_SESSION}.json"
    body = row_path.read_bytes()
    digest = __import__("hashlib").sha256(body).hexdigest()
    (experience / "opportunities" / f".{FIRST_SESSION}.json.{digest}.pending").write_bytes(
        body
    )
    with pytest.raises(accrual.MarketMemoryExperienceStoreError):
        forged_manifest()


def test_wrong_generation_is_a_typed_gap_and_never_a_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    other = tmp_path / "other" / "public" / "trusted-v1"
    trusted.initialize_trusted_store(other)
    manifest = population.build_population_manifest(
        ROOT,
        experience_root=experience,
        trusted_root=other,
        technical_root=technical_root,
        through_session=FIRST_SESSION,
        policy=_AllowPolicy(),
    )
    closure = manifest["source_closure"]
    assert closure["status"] == "retained_gaps"
    trusted_closure = next(
        item
        for item in closure["generation_closures"]
        if item["role"] == "trusted"
    )
    assert trusted_closure["status"] == "generation_absent_from_active_ancestry"
    assert trusted_closure["generation_id"] != ""
    assert manifest["eligibility"]["row_qualification"][0][
        "capture_available"
    ] == "generation_not_authenticated"
    assert manifest["eligibility"]["row_qualification"][0][
        "comparison_eligibility"
    ] == "blocked_by_source_qualification"
    authenticated = [
        item
        for item in closure["generation_closures"]
        if item["status"] == "authenticated"
    ]
    assert [item["role"] for item in authenticated] == ["technical"]
    assert manifest["claims"]["source_closure_complete"] is False


def test_present_but_corrupt_generation_is_an_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    row = json.loads(
        (experience / "opportunities" / f"{FIRST_SESSION}.json").read_text()
    )
    generation_id = row["source_pins"]["trusted_generation"]["generation_id"]
    generation_path = next(
        path
        for path in sorted(trusted_root.rglob("*.json"))
        if generation_id in path.name
    )
    body = json.loads(generation_path.read_text())
    body["captures"][0]["packet_sha256"] = "0" * 64
    generation_path.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n"
    )
    with pytest.raises(population.MarketMemoryPopulationIntegrityError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )


def test_present_but_corrupt_trusted_capture_is_an_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    row = json.loads(
        (experience / "opportunities" / f"{FIRST_SESSION}.json").read_text()
    )
    query_id = row["source_pins"]["trusted_capture"]["query_id"]
    receipt_path = next(
        path
        for path in sorted(trusted_root.rglob("*.json"))
        if query_id in path.name
    )
    body = json.loads(receipt_path.read_text())
    body["packet_sha256"] = "1" * 64
    receipt_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    with pytest.raises(population.MarketMemoryPopulationIntegrityError):
        population.build_population_manifest(
            ROOT,
            experience_root=experience,
            trusted_root=trusted_root,
            technical_root=technical_root,
            through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )


def test_untyped_pin_refusal_is_conservative_and_never_raises_the_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    over_cap = SimpleNamespace(
        profile=trusted.TRUSTED_STORE_PROFILE,
        store_id="mmstore_" + "0" * 64,
        generation_id="mmgeneration_" + "0" * 64,
        generation_sha256="0" * 64,
        capture_count=accrual.MAX_OWNER_GENERATION_CAPTURES + 1,
    )

    def refused(self, *args, **kwargs):
        raise market_memory_pit.MarketMemoryStoreError(
            "trusted active generation exceeds the caller's pin budget"
        )

    monkeypatch.setattr(
        trusted.TrustedFileAsKnownAtReader,
        "read_pinned_generation",
        refused,
    )
    monkeypatch.setattr(
        trusted.TrustedFileAsKnownAtReader,
        "observe_generation_head",
        lambda self, *args, **kwargs: over_cap,
    )
    with pytest.raises(population.MarketMemoryPopulationIntegrityError):
        population.build_population_manifest(
            ROOT, experience_root=experience, trusted_root=trusted_root,
            technical_root=technical_root, through_session=FIRST_SESSION,
            policy=_AllowPolicy(),
        )


def test_authenticated_closure_binds_exact_declared_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session=FIRST_SESSION)
    row = manifest["census"]["rows"][0]
    closure = manifest["source_closure"]
    assert closure["status"] == "complete"
    assert closure["retained_gap_count"] == 0
    assert closure["component_source_receipts_authenticated"] is False
    assert closure["capture_cap"] == accrual.MAX_OWNER_GENERATION_CAPTURES
    assert [item["role"] for item in closure["generation_closures"]] == [
        "technical",
        "trusted",
    ]
    assert all(
        item["status"] == "authenticated"
        for item in closure["generation_closures"]
    )
    assert [item["role"] for item in closure["capture_closures"]] == ["trusted"]
    trusted_ref = row["source_pins"]["trusted_generation"]
    trusted_closure = next(
        item
        for item in closure["generation_closures"]
        if item["role"] == "trusted"
    )
    assert trusted_closure["generation_id"] == trusted_ref["generation_id"]
    assert trusted_closure["generation_sha256"] == trusted_ref["generation_sha256"]
    assert trusted_closure["capture_count"] == trusted_ref["capture_count"]
    assert trusted_closure["declared_by_session_count"] == 1


def test_eligibility_separates_capture_comparison_and_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session="2026-08-19")
    eligibility = manifest["eligibility"]
    assert eligibility["capture_availability"] == {
        "authenticated": 1,
        "absent_from_authenticated_generation": 0,
        "generation_not_authenticated": 0,
        "not_applicable": 2,
    }
    comparison = eligibility["comparison"]
    assert comparison["performed"] is False
    assert comparison["status"] == population.COMPARISON_STATUS
    assert comparison["rows_with_registered_coordinates"] == 1
    assert comparison["rows_pending_coordinates"] == 0
    assert comparison["rows_blocked_by_source_qualification"] == 0
    assert comparison["rows_not_applicable"] == 2
    fit = eligibility["fit"]
    assert fit["eligible"] is False
    assert fit["training_eligible"] is False
    assert fit["promotion_eligible"] is False
    assert fit["authority"] == dict(mm.AUTHORITY)
    assert manifest["authority"] == dict(mm.AUTHORITY)
    assert manifest["authority"]["tier"] == "display"
    assert manifest["authority"]["context_only"] is True
    assert manifest["authority"]["proposal_weight"] == 0
    qualification = eligibility["row_qualification"]
    assert [item["fit_eligibility"] for item in qualification] == [False, False, False]
    assert qualification[0]["comparison_eligibility"] == (
        population.COMPARISON_ELIGIBLE
    )
    assert qualification[1]["comparison_eligibility"] == (
        population.COMPARISON_NOT_APPLICABLE
    )
    assert qualification[2]["comparison_eligibility"] == (
        population.COMPARISON_NOT_APPLICABLE
    )
    claims = manifest["claims"]
    assert claims["training_eligible"] is False
    assert claims["promotion_eligible"] is False
    assert claims["component_source_receipts_authenticated"] is False
    assert claims["external_clock_authenticated"] is False
    assert claims["aba_resistance_authenticated"] is False
    assert claims["membership_outcome_blind"] is True


def test_abstained_row_is_never_derived_into_permission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session=FIRST_SESSION)
    row = manifest["census"]["rows"][0]
    assert row["disposition"] == "abstained"
    qualification = manifest["eligibility"]["row_qualification"][0]
    assert qualification["opportunity_id"] == row["opportunity_id"]
    assert qualification["fit_eligibility"] is False
    assert qualification["comparison_eligibility"] == (
        population.COMPARISON_ELIGIBLE
    )
    assert manifest["eligibility"]["fit"]["eligible"] is False
    assert manifest["eligibility"]["comparison"]["performed"] is False
    assert manifest["authority"]["may_rank"] is False
    assert manifest["authority"]["may_gate"] is False
    assert manifest["authority"]["may_originate"] is False


def test_schema_is_strict_and_rejects_membership_and_payload_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session=FIRST_SESSION)
    validator = _manifest_validator()
    assert list(validator.iter_errors(manifest)) == []
    drifted = json.loads(json.dumps(manifest))
    drifted["membership"]["membership_sha256"] = "not-a-digest"
    assert list(validator.iter_errors(drifted)) != []
    drifted = json.loads(json.dumps(manifest))
    drifted["source_closure"]["component_source_receipts_authenticated"] = True
    assert list(validator.iter_errors(drifted)) != []
    drifted = json.loads(json.dumps(manifest))
    drifted["eligibility"]["fit"]["eligible"] = True
    assert list(validator.iter_errors(drifted)) != []
    drifted = json.loads(json.dumps(manifest))
    drifted["unexpected"] = {}
    assert list(validator.iter_errors(drifted)) != []
    drifted = json.loads(json.dumps(manifest))
    drifted["census"]["rows"][0]["disposition"] = "scoreable"
    assert list(validator.iter_errors(drifted)) != []
    assert manifest["schema"] == population.POPULATION_MANIFEST_SCHEMA
    body = json.dumps(manifest, sort_keys=True).encode("utf-8")
    assert 0 < len(body) <= population.MAX_MANIFEST_BYTES
    assert max(len(item) for item in _strings(manifest)) <= 512


def test_manifest_id_binds_its_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path, monkeypatch, through_session=FIRST_SESSION)
    assert manifest["manifest_id"].startswith(
        population.POPULATION_MANIFEST_ID_PREFIX
    )
    core = dict(manifest)
    core["manifest_id"] = ""
    digest = __import__("hashlib").sha256(
        json.dumps(
            core,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert manifest["manifest_id"] == population.POPULATION_MANIFEST_ID_PREFIX + digest


def test_ordinary_input_failures_precede_rights_and_owner_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    opened = _watch_owner_opens(monkeypatch, experience, trusted_root, technical_root)
    policy = _AllowPolicy()
    arguments = {
        "experience_root": experience,
        "trusted_root": trusted_root,
        "technical_root": technical_root,
        "policy": policy,
    }
    for bad in ("nonsense", "", "2026-13-40", 7, None):
        with pytest.raises(population.MarketMemoryPopulationError):
            population.build_population_manifest(
                ROOT, through_session=bad, **arguments
            )
    with pytest.raises(population.MarketMemoryPopulationError):
        population.build_population_manifest(
            ROOT, through_session="2030-01-01", **arguments
        )
    with pytest.raises(population.MarketMemoryPopulationError):
        population.build_population_manifest(
            ROOT, through_session=FIRST_SESSION, **{**arguments, "experience_root": ""}
        )
    assert opened == []
    assert policy.calls == []


def test_consumer_surface_is_public_owner_api_only() -> None:
    population_source = (ROOT / "engine/neuralweb/market_memory_population.py").read_text()
    test_source = Path(__file__).read_text()
    for label, source in (
        ("population module", population_source),
        ("population tests", test_source),
    ):
        tree = ast.parse(source)
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
                "engine.neuralweb.market_memory"
            ):
                for item in node.names:
                    assert not item.name.startswith("_"), (label, item.name)
                    if item.asname:
                        aliases[item.asname] = f"{node.module}.{item.name}"
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("engine.neuralweb.market_memory"):
                        if item.asname:
                            aliases[item.asname] = item.name
                        else:
                            aliases[item.name.split(".")[-1]] = item.name
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and aliases.get(node.value.id, "").startswith(
                    "engine.neuralweb.market_memory"
                )
            ):
                assert not node.attr.startswith("_"), (label, node.attr)


def test_public_additive_surface_is_declared() -> None:
    assert "read_outcome_blind_population_ledger" in accrual.__all__
    assert "OUTCOME_BLIND_LEDGER_SCHEMA" in accrual.__all__
    assert set(population.__all__) == set(
        name for name in dir(population) if not name.startswith("_")
        and name in population.__all__
    )
    exported = {
        "build_population_manifest",
        "PopulationAccessGrant",
        "PopulationAccessPolicy",
        "PopulationAccessGrant",
        "MarketMemoryPopulationError",
        "MarketMemoryPopulationAccessError",
        "MarketMemoryPopulationIntegrityError",
        "POPULATION_MANIFEST_SCHEMA",
        "POPULATION_ACCESS_POLICY_VERSION",
        "MAX_EXPECTED_SESSIONS",
        "MAX_MANIFEST_BYTES",
        "GAP_DISPOSITION",
        "GAP_REASON",
        "CENSUS_BASIS",
        "FIT_REASON",
    }
    assert exported <= set(population.__all__)
    ledger = accrual.read_outcome_blind_population_ledger
    assert callable(ledger)


def test_owner_public_regressions_still_hold_on_the_real_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    experience, trusted_root, technical_root = _real_store(
        tmp_path, monkeypatch, runs=1
    )
    verified = accrual.verify_experience_installation(
        ROOT, experience_root=experience
    )
    assert verified["verified"] is True
    assert verified["installation_status"] == "locally_observed_before_activation"
    assert accrual.verify_terminal_ledger(ROOT, experience_root=experience) is None
    registration = accrual.load_registration(ROOT)
    assert registration.registration_id.startswith("mmspyexpreg_")
    assert accrual.PILOT_EXPECTED_SESSIONS == 126
    assert len(population.FROZEN_PILOT_SESSIONS) == 126
    assert population.FROZEN_PILOT_SESSIONS[0] == FIRST_SESSION
    assert population.FROZEN_PILOT_SESSIONS[-1] == "2027-02-16"


@pytest.mark.parametrize("pending_only", [False, True])
def test_matured_admitted_pending_outcome_never_recovers_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pending_only: bool,
) -> None:
    from tests import test_market_memory_experience_accrual as owner_tests
    from hashlib import sha256
    experience, trusted_root, technical_root = owner_tests._initialize_sources(tmp_path, monkeypatch)
    owner_tests._install(tmp_path, experience=experience, trusted_root=trusted_root,
                         technical_root=technical_root)
    owner_tests._run(tmp_path, experience=experience, trusted_root=trusted_root,
                     technical_root=technical_root, clock="2026-08-18T04:35:00Z")
    before = population.build_population_manifest(
        ROOT, experience_root=experience, trusted_root=trusted_root,
        technical_root=technical_root, through_session=FIRST_SESSION, policy=_AllowPolicy(),
    )
    assert before["census"]["counts"]["admitted"] == 1
    owner_tests._run(tmp_path, experience=experience, trusted_root=trusted_root,
                     technical_root=technical_root, clock="2026-08-25T04:31:00Z")
    row = json.loads((experience / "opportunities" / (FIRST_SESSION + ".json")).read_bytes())
    final = experience / "outcomes" / row["opportunity_id"] / "000001.json"
    body = final.read_bytes()
    assert json.loads(body)["status"] == "unavailable"
    def forbidden(*args, **kwargs):
        raise AssertionError("read-only census invoked recovery")
    monkeypatch.setattr(accrual, "_recover_immutable_json", forbidden)
    monkeypatch.setattr(accrual, "_recover_mutable_head", forbidden)
    # Real matured receipt and final outcome authenticate with no recovery at all.
    after = population.build_population_manifest(
        ROOT, experience_root=experience, trusted_root=trusted_root,
        technical_root=technical_root, through_session=FIRST_SESSION, policy=_AllowPolicy(),
    )
    assert before["membership"] == after["membership"]
    assert before["audit"]["population_receipt_sha256"] != after["audit"]["population_receipt_sha256"]
    pending = final.with_name("." + final.name + "." + sha256(body).hexdigest() + ".pending")
    pending.write_bytes(body)
    if pending_only:
        final.unlink()
    def snapshot():
        return {str(path.relative_to(experience)): path.read_bytes()
                for path in experience.rglob("*") if path.is_file()}
    original = snapshot()
    with pytest.raises(accrual.MarketMemoryExperienceStoreError, match="pending|noncanonical"):
        population.build_population_manifest(
            ROOT, experience_root=experience, trusted_root=trusted_root,
            technical_root=technical_root, through_session=FIRST_SESSION, policy=_AllowPolicy(),
        )
    assert snapshot() == original


def test_large_current_head_never_masks_corrupt_original_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    experience, trusted_root, technical_root = _real_store(tmp_path, monkeypatch)
    def corrupt(*args, **kwargs):
        raise market_memory_pit.MarketMemoryStoreError("historical generation digest mismatch")
    def unrelated_head(*args, **kwargs):
        raise AssertionError("unrelated head must not classify failed pin")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", corrupt)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "observe_generation_head", unrelated_head)
    with pytest.raises(population.MarketMemoryPopulationIntegrityError):
        population.build_population_manifest(
            ROOT, experience_root=experience, trusted_root=trusted_root,
            technical_root=technical_root, through_session=FIRST_SESSION, policy=_AllowPolicy(),
        )


def test_owner_loaded_capability_rejects_json_and_preserves_frozen_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    experience, trusted_root, technical_root = _real_store(tmp_path, monkeypatch)
    policy = _AllowPolicy()
    capability = population.read_population_manifest_capability(
        ROOT, experience_root=experience, trusted_root=trusted_root,
        technical_root=technical_root, through_session=FIRST_SESSION, policy=policy,
    )
    original = population.disclose_population_manifest(capability, policy=policy)
    altered = json.loads(json.dumps(original))
    altered["census"]["rows"] = []
    with pytest.raises(population.MarketMemoryPopulationError, match="capability_required"):
        population.disclose_population_manifest(altered, policy=policy)
    with pytest.raises(population.MarketMemoryPopulationError, match="capability_required"):
        population.PopulationManifestCapability(b"{}", b"{}")
    original["census"]["rows"] = []
    assert population.disclose_population_manifest(capability, policy=policy)["census"]["rows"]
    with pytest.raises(population.MarketMemoryPopulationAccessError):
        population.disclose_population_manifest(capability, policy=_SequencePolicy(0))


@pytest.mark.parametrize("budget", ["bytes", "calls", "inventory"])
def test_owner_read_pass_has_aggregate_and_inventory_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: str,
) -> None:
    experience, trusted_root, technical_root = _real_store(tmp_path, monkeypatch)
    name = {"bytes": "_MAX_OUTCOME_BLIND_READ_BYTES",
            "calls": "_MAX_OUTCOME_BLIND_READ_CALLS",
            "inventory": "_MAX_OUTCOME_BLIND_RECEIPTS"}[budget]
    monkeypatch.setattr(accrual, name, 1 if budget == "bytes" else 0)
    before = {str(p.relative_to(experience)): p.read_bytes()
              for p in experience.rglob("*") if p.is_file()}
    with pytest.raises(accrual.MarketMemoryExperienceStoreError, match="bound"):
        population.build_population_manifest(
            ROOT, experience_root=experience, trusted_root=trusted_root,
            technical_root=technical_root, through_session=FIRST_SESSION, policy=_AllowPolicy(),
        )
    assert before == {str(p.relative_to(experience)): p.read_bytes()
                      for p in experience.rglob("*") if p.is_file()}
