"""SPEC_U2 §2 gates 32-37: the saved-scenario monitor producer and runner.

The fixture world is built from the predecessor suites' own constructors BY
IMPORT and never hand-written: two real state generations over three issuers
(``tests.test_capital_structure_state_bundle._built``), the capacity inputs
bundles bound to each (the U1B-1 fixtures re-keyed per issuer), one derived
change ledger between them (``diff_state_generations``), and six saved rows —
one per ``RESTORE_OUTCOMES`` member — whose answers are REAL compositions the
evaluate route would owe.  A saved row is judged against the world its night
published, so the rejected row is an honest record corrupted after
construction, never a fabricated one.

Hermetic: the store adapter's transport and the monitor's own ``_pg`` are
fakes at their single IO seams, and an autouse fixture makes socket connects
raise.  No digest, id or generation is hard-coded; no float literal anywhere.
"""
from __future__ import annotations

import dataclasses
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from engine.capital_structure.issuer_state_contracts import PriceAssumption
from engine.capital_structure.rule_applicability import (
    build_rule_pack,
    load_rule_applicability_pack,
)
from engine.capital_structure.scenario_composition import compose_scenario
from engine.capital_structure.scenario_inputs import (
    BUNDLE_FAMILIES,
    ScenarioInputsUnavailable,
    assemble_scenario_inputs,
)
from engine.capital_structure.saved_scenarios import (
    RESTORE_OUTCOMES,
    SavedScenario,
    result_digest_of,
    result_substance_digest_of,
)
from engine.capital_structure import saved_scenario_monitor as monitor
from engine.capital_structure import saved_scenario_store as store
from engine.capital_structure.state_bundle import state_from_record
from engine.capital_structure.state_changes import diff_state_generations
import tests.test_capital_structure_funding as F
import tests.test_capital_structure_scenario_inputs as inputs_suite
import tests.test_capital_structure_state_api as state_api_suite
import tests.test_capital_structure_supply_scenarios as SS
from tests.test_capital_structure_registration_integration import (
    AS_OF,
    _s1_filed_amended_effective_withdrawn,
)
from tests.test_capital_structure_registration_lifecycle import _event
from tests.test_capital_structure_state_bundle import (
    ISSUER_ONE,
    ISSUER_TWO,
    _built,
    _state_record,
)

ROOT = Path(__file__).resolve().parents[1]

#: The third issuer's inputs lose financial support between the generations;
#: the fourth issuer leaves coverage entirely (the route's refused row).
ISSUER_THREE = "sec:cik:0000000003"
ISSUER_ABSENT = "sec:cik:0000000009"

#: Fixed stamps — never a wall clock.
CHANGES_GENERATED_AT = "2026-10-19T06:00:00Z"
SAVED_AT = "2026-10-19T07:00:00Z"
USER = "user:alpha"
#: A label that is lawful to SAVE (it carries no advisory vocabulary) but
#: fails the producer's glance guard — its payload falls back.
BANNED_LABEL = "falsified thesis watch"
PLAIN_LABEL = "monitor fixture"

_WITHDRAWN_FILE = "333-555"
_SHELF_FILE = "333-777"
_FRESH_FILE = "333-999"
_THIRD_FILE = "333-888"

_PAYLOAD_FIELDS = {
    "category",
    "kind",
    "saved_id",
    "issuer_id",
    "label",
    "from_generation_id",
    "to_generation_id",
    "change_kinds",
    "evidence_url",
}


# ---------------------------------------------------------------------------
# Hermeticity: no socket may leave this suite.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError("network access attempted in a hermetic test")

    monkeypatch.setattr("socket.socket.connect", _refuse, raising=True)


# ---------------------------------------------------------------------------
# The two-generation world over three issuers (every record derived, none
# hand-written)
# ---------------------------------------------------------------------------
def _rows_previous() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Issuer ONE's S-1 lifecycle plus a second shelf the current generation
    will no longer carry; issuer TWO's and issuer THREE's shelves, present in
    both generations."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    events.append(
        _event(
            81, "S-3",
            accepted_at="2026-08-02T10:00:00Z", seen_at="2026-08-02T18:00:00Z",
            file_number=_WITHDRAWN_FILE,
        )
    )
    events.append(
        _event(
            51, "S-3",
            accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T20:00:00Z",
            issuer_id=ISSUER_TWO, cik="2", ticker="XYZ", file_number=_SHELF_FILE,
        )
    )
    events.append(
        _event(
            61, "S-3",
            accepted_at="2026-08-01T11:00:00Z", seen_at="2026-08-01T21:00:00Z",
            issuer_id=ISSUER_THREE, cik="3", ticker="LMN", file_number=_THIRD_FILE,
        )
    )
    return events, list(edges)


def _rows_current() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The second shelf is gone (a withdrawal for issuer ONE), issuer TWO has
    a brand-new shelf (a new event), issuer THREE's shelf is unchanged."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    events.append(
        _event(
            51, "S-3",
            accepted_at="2026-08-01T10:00:00Z", seen_at="2026-08-01T20:00:00Z",
            issuer_id=ISSUER_TWO, cik="2", ticker="XYZ", file_number=_SHELF_FILE,
        )
    )
    events.append(
        _event(
            71, "S-3",
            accepted_at="2026-08-03T10:00:00Z", seen_at="2026-08-08T18:00:00Z",
            issuer_id=ISSUER_TWO, cik="2", ticker="XYZ", file_number=_FRESH_FILE,
        )
    )
    events.append(
        _event(
            61, "S-3",
            accepted_at="2026-08-01T11:00:00Z", seen_at="2026-08-01T21:00:00Z",
            issuer_id=ISSUER_THREE, cik="3", ticker="LMN", file_number=_THIRD_FILE,
        )
    )
    return events, list(edges)


def _entries_for(issuer_id: str, as_of: str) -> dict[str, Any]:
    """The S0 §10 per-issuer families re-keyed to ``issuer_id`` — the U1b
    suite's own construction, never a copy of the records."""
    instruments = dataclasses.replace(
        inputs_suite._fixture_instruments(), issuer_id=issuer_id, as_of=as_of
    )
    basis = dataclasses.replace(SS.basis(), issuer_id=issuer_id, as_of=as_of)
    financials = F.financials(F.cash(), F.ocf())
    commitments = F.covenants(
        F.covenant("cov-min-1", "2000000", available_at="2026-10-01T00:00:00Z")
    )
    return {
        inputs_suite.INSTRUMENTS_FAMILY: inputs_suite._entry_for(
            instruments, inputs_suite.INSTRUMENTS_FAMILY
        ),
        inputs_suite.SHARE_BASIS_FAMILY: inputs_suite._entry_for(
            basis, inputs_suite.SHARE_BASIS_FAMILY
        ),
        inputs_suite.FINANCIALS_FAMILY: inputs_suite._entry_for(
            financials, inputs_suite.FINANCIALS_FAMILY
        ),
        inputs_suite.COMMITMENTS_FAMILY: inputs_suite._entry_for(
            commitments, inputs_suite.COMMITMENTS_FAMILY
        ),
    }


def _entries_financials_unavailable(issuer_id: str, as_of: str) -> dict[str, Any]:
    """The whole financials entry replaced with a typed unavailable one — the
    U2-1 suite's own shape."""
    entries = dict(_entries_for(issuer_id, as_of))
    entries[inputs_suite.FINANCIALS_FAMILY] = inputs_suite.FamilyEntry(
        family=inputs_suite.FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )
    return entries


def _inputs_record(bundle: dict[str, Any], *, issuers: dict[str, Any]) -> dict[str, Any]:
    """One serialized capacity inputs bundle bound to a fixture generation."""
    built, unknowns, _conditions, _excluded = build_rule_pack(
        load_rule_applicability_pack(), AS_OF[:10]
    )
    assert built is not None
    inputs = inputs_suite.CapacityInputsBundle(
        as_of=AS_OF,
        generated_at=f"{AS_OF[:10]}T12:00:00Z",
        state_generation_id=bundle["generation_id"],
        source_generation_id=state_api_suite.stable_id_of_projection(),
        rules=inputs_suite.RulesEntry(
            support="supported", unknowns=tuple(unknowns), record=built
        ),
        issuers=issuers,
    )
    return json.loads(json.dumps(inputs.as_record(), sort_keys=True))


class _World(NamedTuple):
    previous: dict[str, Any]
    current: dict[str, Any]
    inputs_previous: dict[str, Any]
    inputs_current: dict[str, Any]
    changes_record: dict[str, Any]


@pytest.fixture(scope="module")
def pack():
    return load_rule_applicability_pack()


@pytest.fixture(scope="module")
def world(pack) -> _World:
    previous_bundle = _built(
        *_rows_previous(), [ISSUER_ONE, ISSUER_TWO, ISSUER_THREE], rule_pack=pack
    )[2]
    current_bundle = _built(
        *_rows_current(), [ISSUER_ONE, ISSUER_TWO, ISSUER_THREE], rule_pack=pack
    )[2]
    inputs_previous = _inputs_record(
        previous_bundle,
        issuers={
            issuer: _entries_for(issuer, AS_OF)
            for issuer in (ISSUER_ONE, ISSUER_TWO, ISSUER_THREE)
        },
    )
    inputs_current = _inputs_record(
        current_bundle,
        issuers={
            ISSUER_ONE: _entries_for(ISSUER_ONE, AS_OF),
            ISSUER_TWO: _entries_for(ISSUER_TWO, AS_OF),
            ISSUER_THREE: _entries_financials_unavailable(ISSUER_THREE, AS_OF),
        },
    )
    changeset = diff_state_generations(
        previous_bundle,
        current_bundle,
        inputs_previous=inputs_previous,
        inputs_current=inputs_current,
        generated_at=CHANGES_GENERATED_AT,
    )
    return _World(
        previous=previous_bundle,
        current=current_bundle,
        inputs_previous=inputs_previous,
        inputs_current=inputs_current,
        changes_record=changeset.as_record(),
    )


def _compose(bundle: dict[str, Any], inputs_record: dict[str, Any], issuer_id: str, pack, price: str) -> dict[str, Any]:
    """The composition the evaluate route owes one issuer's scenario on one
    generation — recomputed from the fixtures alone.  Each fixture row saves
    its OWN price assumption, so every saved_id is a distinct row."""
    state = state_from_record(_state_record(bundle, issuer_id))
    scenario = state_api_suite._test_scenario(
        price=PriceAssumption("fixed", "USD", fixed_price=price)
    )
    assembled = assemble_scenario_inputs(
        inputs_record,
        issuer_id,
        scenario.as_of,
        served_state_generation_id=bundle["generation_id"],
    )
    assert not isinstance(assembled, ScenarioInputsUnavailable)
    result = compose_scenario(
        state,
        assembled.instruments,
        assembled.basis,
        assembled.financials,
        assembled.commitments,
        scenario,
        assembled.rules,
        pack=pack,
    )
    return result.as_record(), scenario


def _make_saved(
    *,
    issuer_id: str,
    state_generation_id: str,
    inputs_generation_id: str,
    result: dict[str, Any],
    scenario: Any,
    label: str = PLAIN_LABEL,
) -> SavedScenario:
    return SavedScenario(
        user_id=USER,
        issuer_id=issuer_id,
        label=label,
        view={"mode": "scenario", "cutoff": None},
        scenario=scenario.as_record(),
        state_generation_id=state_generation_id,
        inputs_generation_id=inputs_generation_id,
        result_id=result["result_id"],
        result_digest=result_digest_of(result),
        result_substance_digest=result_substance_digest_of(result),
        rule_pack_digest=result["capacity_envelope"]["rule_pack_digest"],
        saved_at=SAVED_AT,
    )


def _store_row(saved: SavedScenario, *, record: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "saved_id": saved.saved_id,
        "user_id": saved.user_id,
        "issuer_id": saved.issuer_id,
        "record": json.dumps(
            record if record is not None else saved.as_record(), sort_keys=True
        ),
        "saved_at": saved.saved_at,
        "updated_at": saved.saved_at,
        "last_outcome": saved.last_outcome,
        "last_outcome_generation_id": saved.last_outcome_generation_id,
    }


class _Fixture(NamedTuple):
    """The six saved rows — one per RESTORE_OUTCOMES member — as store rows,
    plus the contract objects the assertions name."""

    rows: list[dict[str, Any]]
    no_change: SavedScenario
    correction: SavedScenario
    new_events: SavedScenario
    unavailable: SavedScenario
    absent: SavedScenario


@pytest.fixture(scope="module")
def fixture_rows(world: _World, pack) -> _Fixture:
    current_gen = world.current["generation_id"]
    current_inputs_gen = world.inputs_current["generation_id"]
    previous_gen = world.previous["generation_id"]
    previous_inputs_gen = world.inputs_previous["generation_id"]
    result_current_one, scenario_one = _compose(
        world.current, world.inputs_current, ISSUER_ONE, pack, "2.00"
    )
    result_previous_one, scenario_two = _compose(
        world.previous, world.inputs_previous, ISSUER_ONE, pack, "2.10"
    )
    result_previous_two, scenario_three = _compose(
        world.previous, world.inputs_previous, ISSUER_TWO, pack, "2.20"
    )
    result_previous_three, scenario_four = _compose(
        world.previous, world.inputs_previous, ISSUER_THREE, pack, "2.30"
    )
    result_current_five, scenario_five = _compose(
        world.current, world.inputs_current, ISSUER_ONE, pack, "2.40"
    )
    # The absent row's issuer has left coverage, so its stored answer cannot
    # be recomputed in this world — its identity fields are never read (the
    # classification short-circuits before identity), and the pair stored is
    # a real composition, never a fabricated one.
    result_previous_six, scenario_six = _compose(
        world.previous, world.inputs_previous, ISSUER_TWO, pack, "2.50"
    )

    no_change = _make_saved(
        issuer_id=ISSUER_ONE,
        state_generation_id=current_gen,
        inputs_generation_id=current_inputs_gen,
        result=result_current_one,
        scenario=scenario_one,
    )
    correction = _make_saved(
        issuer_id=ISSUER_ONE,
        state_generation_id=previous_gen,
        inputs_generation_id=previous_inputs_gen,
        result=result_previous_one,
        scenario=scenario_two,
        label=BANNED_LABEL,
    )
    new_events = _make_saved(
        issuer_id=ISSUER_TWO,
        state_generation_id=previous_gen,
        inputs_generation_id=previous_inputs_gen,
        result=result_previous_two,
        scenario=scenario_three,
    )
    unavailable = _make_saved(
        issuer_id=ISSUER_THREE,
        state_generation_id=previous_gen,
        inputs_generation_id=previous_inputs_gen,
        result=result_previous_three,
        scenario=scenario_four,
    )
    absent = _make_saved(
        issuer_id=ISSUER_ABSENT,
        state_generation_id=previous_gen,
        inputs_generation_id=previous_inputs_gen,
        result=result_previous_six,
        scenario=scenario_six,
    )
    # The rejected row: the honest record corrupted AFTER construction — the
    # saved body no longer reconstructs under the served contract.
    rejected = _make_saved(
        issuer_id=ISSUER_ONE,
        state_generation_id=current_gen,
        inputs_generation_id=current_inputs_gen,
        result=result_current_five,
        scenario=scenario_five,
    )
    corrupted = rejected.as_record()
    corrupted["scenario"] = dict(corrupted["scenario"], horizon_end="not-a-date")

    rows = [
        _store_row(no_change),
        _store_row(correction),
        _store_row(new_events),
        _store_row(unavailable),
        _store_row(rejected, record=corrupted),
        _store_row(absent),
    ]
    return _Fixture(
        rows=rows,
        no_change=no_change,
        correction=correction,
        new_events=new_events,
        unavailable=unavailable,
        absent=absent,
    )


def _write_artifacts(root: Path, world: _World) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, doc in (
        ("state_bundle.json", world.current),
        ("capacity_inputs.json", world.inputs_current),
        ("state_changes.json", world.changes_record),
    ):
        (root / name).write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Fakes at the two IO seams (the store adapter's transport and the module's
# own _pg).
# ---------------------------------------------------------------------------
class _FakeStore:
    """Canned transport for the saved-scenario store: answers every read with
    the rows and applies every outcome PATCH to them."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = [dict(row) for row in rows]
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6) -> Any:
        self.calls.append((method, path))
        if method == "GET":
            return [dict(row) for row in self.rows]
        if method == "PATCH":
            marker = "saved_id=eq."
            saved_id = urllib.parse.unquote(path.split(marker, 1)[1])
            for row in self.rows:
                if row["saved_id"] == saved_id:
                    row["last_outcome"] = body["last_outcome"]
                    row["last_outcome_generation_id"] = body["last_outcome_generation_id"]
                    return None
            raise AssertionError(f"PATCH for unknown saved_id {saved_id!r}")
        raise AssertionError(f"unexpected {method} {path}")

    def patch_count(self) -> int:
        return sum(1 for method, _path in self.calls if method == "PATCH")

    def written(self) -> dict[str, tuple[Any, Any]]:
        return {
            row["saved_id"]: (row["last_outcome"], row["last_outcome_generation_id"])
            for row in self.rows
        }


class _Http409(urllib.error.HTTPError):
    def __init__(self):
        super().__init__(
            "https://x/rest/v1/alert_outbox", 409, "duplicate key", None, io.BytesIO(b"{}")
        )


class _FakeOutbox:
    """Minimal PostgREST double for the module's own ``_pg``: the dedupe
    probe over alert_outbox and the enqueue POSTs (a replay hits the UNIQUE
    index — a 409 the producer must absorb)."""

    def __init__(self, *, fire_event_ids: list[str] | None = None) -> None:
        self.calls: list[tuple] = []
        self.outbox: list[dict[str, Any]] = [
            {"fire_event_id": fid} for fid in (fire_event_ids or [])
        ]

    @staticmethod
    def _in_param(path: str, key: str) -> list[str]:
        marker = f"{key}=in.("
        if marker not in path:
            return []
        rest = path.split(marker, 1)[1].split(")", 1)[0]
        return [urllib.parse.unquote(x) for x in rest.split(",") if x]

    def __call__(self, method: str, path: str, body: Any = None, prefer: str | None = None, timeout: int = 6) -> Any:
        self.calls.append((method, path, body))
        if method == "GET":
            assert path.startswith("alert_outbox?"), path
            ids = set(self._in_param(path, "fire_event_id"))
            return [
                {"fire_event_id": row["fire_event_id"]}
                for row in self.outbox
                if row["fire_event_id"] in ids
            ]
        if method == "POST":
            assert path == "alert_outbox", path
            for existing in self.outbox:
                if existing["fire_event_id"] == body["fire_event_id"]:
                    raise _Http409()
            self.outbox.append(dict(body))
            return None
        raise AssertionError(f"unexpected {method} {path}")

    def posts(self) -> list[dict[str, Any]]:
        return [body for method, _path, body in self.calls if method == "POST"]

    def fids(self) -> list[str]:
        return [row["fire_event_id"] for row in self.outbox]


def _install(monkeypatch, fixture_rows: _Fixture, *, world: _World | None, root: Path, seeded: list[str]):
    """Wire the monitor to the fake seams; write the world's artifacts when a
    world is given.  Returns (store_fake, outbox_fake)."""
    if world is not None:
        _write_artifacts(root, world)
    store_fake = _FakeStore(fixture_rows.rows)
    monkeypatch.setattr(store, "_transport", store_fake)
    outbox = _FakeOutbox(fire_event_ids=seeded)
    monkeypatch.setattr(monitor, "SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(monitor, "_pg", outbox)
    return store_fake, outbox


# ---------------------------------------------------------------------------
# The ONE shared helper every planned row in this file asserts through.
# ---------------------------------------------------------------------------
def _assert_no_binary_fraction(value: Any) -> None:
    if isinstance(value, bool):
        return
    assert not isinstance(value, float), value
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_binary_fraction(item)
    if isinstance(value, list):
        for item in value:
            _assert_no_binary_fraction(item)


def _check_planned_row(row: dict[str, Any], *, known_users: tuple[str, ...]) -> None:
    assert row["channel"] == monitor.CHANNEL
    assert row["status"] == "pending" and row["attempts"] == 0
    assert row["user_id"] in known_users
    payload = row["payload"]
    assert set(payload) == _PAYLOAD_FIELDS
    assert payload["category"] == monitor.CATEGORY
    assert payload["kind"] in RESTORE_OUTCOMES
    assert payload["kind"] in monitor.FIRING_OUTCOMES
    parts = row["fire_event_id"].split("|")
    assert len(parts) == 5 and parts[0] == "cs_saved_scenario"
    assert monitor.fire_event_id(
        saved_id=parts[1],
        outcome=parts[2],
        to_generation_id=parts[3],
        user_id=parts[4],
    ) == row["fire_event_id"]
    assert parts[4] == row["user_id"]
    assert parts[1] == payload["saved_id"] and parts[2] == payload["kind"]
    # No user id outside the row's own user_id field, ever.
    assert "user_id" not in payload
    for known in known_users:
        assert known not in json.dumps(payload)
    _assert_no_binary_fraction(payload)
    # The glance strings carry no digit and no banned token.
    for field in ("label", "kind", "category"):
        assert re.search(r"\d", str(payload[field])) is None, (field, payload[field])
    for kind in payload["change_kinds"]:
        assert re.search(r"\d", kind) is None
    for token in monitor._BANNED_TERMS:
        assert token not in payload["label"].lower()
    assert payload["evidence_url"] == monitor.evidence_url(
        payload["issuer_id"], payload["saved_id"]
    )


# ---------------------------------------------------------------------------
# Gate 32 — dormancy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "env_overrides",
    [
        {},                                                        # both unset
        {"CS_SAVED_SCENARIO_ENABLE": "1"},                         # drain flag unset
        {"ALERT_DRAIN_ENABLE": "1"},                               # producer flag unset
        {"CS_SAVED_SCENARIO_ENABLE": "true", "ALERT_DRAIN_ENABLE": "1"},  # non-"1"
        {"CS_SAVED_SCENARIO_ENABLE": "0", "ALERT_DRAIN_ENABLE": "0"},     # explicit off
    ],
)
def test_u2_monitor_is_dormant_unless_both_flags_are_1(
    tmp_path, monkeypatch, capsys, env_overrides
):
    monkeypatch.delenv("CS_SAVED_SCENARIO_ENABLE", raising=False)
    monkeypatch.delenv("ALERT_DRAIN_ENABLE", raising=False)
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    # If the runner imported the producer while dormant, this poisoned entry
    # would turn that import into an ImportError (None halts the import).
    monkeypatch.setitem(
        sys.modules, "engine.capital_structure.saved_scenario_monitor", None
    )
    from scripts import run_capital_structure_saved_scenario_monitor as runner

    assert runner.main([]) == 0
    out = capsys.readouterr().out
    assert "DORMANT" in out
    assert "no reads, no writes" in out
    assert not any(tmp_path.iterdir())


def test_u2_monitor_dormant_runner_subprocess_exits_zero():
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("CS_SAVED_SCENARIO_ENABLE", "ALERT_DRAIN_ENABLE")
    }
    res = subprocess.run(
        [sys.executable, "-m", "scripts.run_capital_structure_saved_scenario_monitor"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0
    assert "DORMANT" in res.stdout


def test_u2_monitor_armed_dry_run_flag_never_enqueues_or_writes(monkeypatch, capsys):
    """Armed with no credentials: the first typed read is unavailable and the
    runner STILL exits 0 with zero writes (fail-soft); ``--dry-run`` parses."""
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("CS_SAVED_SCENARIO_ENABLE", "1")
    monkeypatch.setenv("ALERT_DRAIN_ENABLE", "1")
    from scripts import run_capital_structure_saved_scenario_monitor as runner

    assert runner.main(["--dry-run"]) == 0
    assert "READ_UNAVAILABLE" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Gate 34 — the frozen dedupe key
# ---------------------------------------------------------------------------
def test_u2_monitor_fire_event_id_is_literal_concatenation():
    assert monitor.fire_event_id(
        saved_id="saved_scenario:cs:abcdef",
        outcome="correction",
        to_generation_id="state_bundle:cs:1234",
        user_id="user:alpha",
    ) == (
        "cs_saved_scenario|saved_scenario:cs:abcdef|correction"
        "|state_bundle:cs:1234|user:alpha"
    )


# ---------------------------------------------------------------------------
# Gate 33 — only firing outcomes, only on transition
# ---------------------------------------------------------------------------
def test_u2_monitor_fires_only_firing_outcomes_and_only_on_transition(
    world: _World, fixture_rows: _Fixture, tmp_path, monkeypatch
):
    store_fake, outbox = _install(
        monkeypatch, fixture_rows, world=world, root=tmp_path, seeded=[]
    )

    result = monitor.run(root=tmp_path, dry_run=False)
    assert result.outcome == "ok", result.notes
    assert result.read_state == monitor.READ_OK
    assert result.rows_n == 6 and result.classified_n == 6
    posts = outbox.posts()
    served_gen = world.current["generation_id"]
    assert sorted(row["fire_event_id"] for row in posts) == sorted(
        [
            monitor.fire_event_id(
                saved_id=fixture_rows.correction.saved_id,
                outcome="correction",
                to_generation_id=served_gen,
                user_id=USER,
            ),
            monitor.fire_event_id(
                saved_id=fixture_rows.new_events.saved_id,
                outcome="new_events",
                to_generation_id=served_gen,
                user_id=USER,
            ),
        ]
    )
    for row in posts:
        _check_planned_row(row, known_users=(USER,))
    # The outcome write followed each row's OWN successful enqueue, and the
    # non-firing rows stay untouched.
    written = store_fake.written()
    assert written[fixture_rows.correction.saved_id] == ("correction", served_gen)
    assert written[fixture_rows.new_events.saved_id] == ("new_events", served_gen)
    assert written[fixture_rows.no_change.saved_id] == (None, None)
    assert written[fixture_rows.unavailable.saved_id] == (None, None)

    # A second run over the unchanged (outcome, generation) plans nothing.
    second = monitor.run(root=tmp_path, dry_run=False)
    assert second.planned_n == 0 and second.enqueued_n == 0
    assert len(outbox.posts()) == len(posts)
    for row in outbox.posts():
        _check_planned_row(row, known_users=(USER,))


# ---------------------------------------------------------------------------
# Gate 35 — a missing state bundle is the outage signal, once per generation
# ---------------------------------------------------------------------------
def test_u2_monitor_missing_state_bundle_is_source_outage_once_per_generation(
    fixture_rows: _Fixture, tmp_path, monkeypatch
):
    # NO artifacts at all under root: every well-formed row is source_outage.
    store_fake, outbox = _install(
        monkeypatch, fixture_rows, world=None, root=tmp_path, seeded=[]
    )

    first = monitor.run(root=tmp_path, dry_run=False)
    assert first.outcome == "ok"
    assert first.state_state == monitor.READ_UNAVAILABLE
    planned = sorted(row["fire_event_id"] for row in outbox.posts())
    # Five rows plan — every row except the corrupted one, whose saved body no
    # longer reconstructs and which therefore never fires.
    assert len(planned) == 5
    for row in outbox.posts():
        _check_planned_row(row, known_users=(USER,))
        assert row["payload"]["kind"] == "source_outage"
    anchors = {row["fire_event_id"].split("|")[3] for row in outbox.posts()}
    assert anchors == {
        fixture_rows.no_change.state_generation_id,
        fixture_rows.correction.state_generation_id,
    }
    written = store_fake.written()
    assert written[fixture_rows.absent.saved_id] == (
        "source_outage", fixture_rows.absent.state_generation_id,
    )

    # Never again until the generation changes: the second run plans nothing.
    second = monitor.run(root=tmp_path, dry_run=False)
    assert second.planned_n == 0 and second.enqueued_n == 0
    assert sorted(row["fire_event_id"] for row in outbox.posts()) == planned


# ---------------------------------------------------------------------------
# Gate 36 — the payload carries no number and passes the glance guard
# ---------------------------------------------------------------------------
def test_u2_monitor_payload_has_no_numbers_and_passes_plain_guard(
    world: _World, fixture_rows: _Fixture, tmp_path, monkeypatch
):
    store_fake, outbox = _install(
        monkeypatch, fixture_rows, world=world, root=tmp_path, seeded=[]
    )

    result = monitor.run(root=tmp_path, dry_run=False)
    assert result.outcome == "ok"
    posts = outbox.posts()
    assert len(posts) == 2
    for row in posts:
        _check_planned_row(row, known_users=(USER,))
        payload = row["payload"]
        # The named id/generation fields are the only digit-bearing fields.
        for field in ("saved_id", "issuer_id", "from_generation_id", "to_generation_id"):
            assert isinstance(payload[field], str)
    by_saved = {row["payload"]["saved_id"]: row for row in posts}
    # The banned-label row falls back to the fixed plain sentence; every
    # lawful label rides verbatim.
    assert (
        by_saved[fixture_rows.correction.saved_id]["payload"]["label"]
        == monitor._LABEL_FALLBACK
    )
    assert (
        by_saved[fixture_rows.new_events.saved_id]["payload"]["label"] == PLAIN_LABEL
    )
    assert store_fake.patch_count() == 2


# ---------------------------------------------------------------------------
# Gate 37 — dedupe against the outbox, outcomes written only on ok
# ---------------------------------------------------------------------------
def test_u2_monitor_dedupes_against_outbox_and_writes_outcome_only_on_ok(
    world: _World, fixture_rows: _Fixture, tmp_path, monkeypatch
):
    served_gen = world.current["generation_id"]
    both_fids = [
        monitor.fire_event_id(
            saved_id=fixture_rows.correction.saved_id,
            outcome="correction",
            to_generation_id=served_gen,
            user_id=USER,
        ),
        monitor.fire_event_id(
            saved_id=fixture_rows.new_events.saved_id,
            outcome="new_events",
            to_generation_id=served_gen,
            user_id=USER,
        ),
    ]

    # A dry run plans but never enqueues and never writes an outcome.
    _store, outbox = _install(
        monkeypatch, fixture_rows, world=world, root=tmp_path, seeded=[]
    )
    dry = monitor.run(root=tmp_path, dry_run=True)
    assert dry.planned_n == 2 and dry.enqueued_n == 0
    assert outbox.posts() == []
    assert _store.patch_count() == 0

    # A field where the outbox already holds both ids: deduped before the
    # plan, nothing enqueued, NO outcome write.
    _store, outbox = _install(
        monkeypatch, fixture_rows, world=world, root=tmp_path, seeded=both_fids
    )
    armed = monitor.run(root=tmp_path, dry_run=False)
    assert armed.planned_n == 0 and armed.duplicate_n == 2
    assert armed.enqueued_n == 0
    assert outbox.posts() == []
    assert _store.patch_count() == 0
    assert all(row["last_outcome"] is None for row in _store.rows)

    # With the dedupe probe blinded, the UNIQUE index absorbs both replays
    # and an absorbed row still writes no outcome — only an enqueued row does.
    monkeypatch.setattr(
        monitor,
        "read_existing_fire_ids",
        lambda ids: monitor.TypedRead(monitor.READ_OK_ZERO, []),
    )
    blinded = monitor.run(root=tmp_path, dry_run=False)
    assert blinded.enqueued_n == 0 and blinded.duplicate_n == 2
    assert len(outbox.posts()) == 2
    assert _store.patch_count() == 0

    # A clean field for one row: it enqueues and its outcome write follows;
    # the still-deduped sibling stays unwritten.
    _store, outbox = _install(
        monkeypatch, fixture_rows, world=world, root=tmp_path, seeded=both_fids[:1]
    )
    clean = monitor.run(root=tmp_path, dry_run=False)
    assert clean.enqueued_n == 1 and clean.duplicate_n == 1
    written = _store.written()
    assert written[fixture_rows.new_events.saved_id] == ("new_events", served_gen)
    assert written[fixture_rows.correction.saved_id] == (None, None)


# ---------------------------------------------------------------------------
# U2-2 r1 parity — the monitor classifies exactly as the restore route does
# (DEC:CS-V2-U2-RESTORE-REBASES-AS-OF)
# ---------------------------------------------------------------------------
_EARLIER_AS_OF = "2026-10-13T00:00:00Z"


def _saved_at_earlier_as_of(world: _World, pack, *, view: dict[str, Any]) -> tuple[SavedScenario, Any]:
    """One honest composition at the served as_of, saved with its scenario
    anchored one day earlier — the shape every save takes after a nightly
    moves the served as_of."""
    result, scenario = _compose(world.current, world.inputs_current, ISSUER_ONE, pack, "2.70")
    earlier = dataclasses.replace(scenario, as_of=_EARLIER_AS_OF)
    assert earlier.scenario_id != scenario.scenario_id
    saved = _make_saved(
        issuer_id=ISSUER_ONE,
        state_generation_id=world.current["generation_id"],
        inputs_generation_id=world.inputs_current["generation_id"],
        result=result,
        scenario=earlier,
    )
    return dataclasses.replace(saved, view=view), scenario


def test_u2_monitor_rebases_a_scenario_anchor_to_the_served_as_of(world: _World, pack):
    """A ``scenario`` save re-runs its assumptions AT the served as_of, as the
    route's restore_anchor does: a re-run (S′ recomputed), never a rejection."""
    saved, served_scenario = _saved_at_earlier_as_of(
        world, pack, view={"mode": "scenario", "cutoff": None}
    )
    outcome = monitor._restore_outcome_for(
        saved,
        bundle=world.current,
        inputs_doc=world.inputs_current,
        pack=pack,
        changeset=None,
    )
    assert outcome.outcome == "no_change", outcome
    assert outcome.scenario_id_before == saved.scenario_id
    assert outcome.scenario_id_after == served_scenario.scenario_id
    assert outcome.scenario_id_after != saved.scenario_id
    assert outcome.to_as_of == AS_OF


def test_u2_monitor_then_known_anchor_off_the_bundle_as_of_is_inputs_unavailable(
    world: _World, pack
):
    """A ``then_known`` anchor keeps its cutoff as_of; the served inputs bundle
    is bound to another as_of, so — exactly as the route's 409 — every bundle
    family is unavailable, never a refusal or a recomposed number."""
    saved, _served = _saved_at_earlier_as_of(
        world, pack, view={"mode": "then_known", "cutoff": _EARLIER_AS_OF}
    )
    outcome = monitor._restore_outcome_for(
        saved,
        bundle=world.current,
        inputs_doc=world.inputs_current,
        pack=pack,
        changeset=None,
    )
    assert outcome.outcome == "inputs_unavailable", outcome
    assert sorted(outcome.unavailable_components) == sorted(BUNDLE_FAMILIES)
    assert outcome.result_id_after is None
