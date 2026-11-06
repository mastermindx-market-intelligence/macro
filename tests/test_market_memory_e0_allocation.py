"""Tests for the Market Memory E0 condition-order allocation source utility.

Synthetic identifiers only. These tests pin deterministic source behaviour,
input binding, validation refusals, purity of process state, and the bounded
rejection loop. They are not evidence of statistical inference, of
cryptographic secrecy, of reviewer blinding, or of any actual study allocation.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import itertools
import json
import os
import pathlib
import random
import sys

import pytest

from engine.research_factory import market_memory_e0_allocation as alloc

# --- Fixed preregistration constants, reconstructed independently -----------

SEED_HEX = "7c8013e1e8092bdf91d4598a73c01d9690199dfb6c08db632b81f564367a4b03"
ALGORITHM = "market_memory.e0_condition_order.sha256_rejection_v1"
CONDITIONS = ("no_memory", "recency", "fixed_l1")
ORDERING_SPACE = 6
ACCEPTANCE_BOUND = (2**256 // ORDERING_SPACE) * ORDERING_SPACE

# Python's documented itertools order over the frozen condition tuple.
EXPECTED_PERMUTATIONS = [list(item) for item in itertools.permutations(CONDITIONS)]

# --- Fixed synthetic inputs and independent known vectors ------------------

STUDY_ID = "mm-e0-study-synthetic"
TASKS_SHA256 = "65b22df3c4586f0d3044c5a58b745f86c5e19382630b72ba5a3f00dc7433bce8"
TASK_IDS = ["task-0001", "task-0002", "task-0003"]

# The exact canonical hash input for task-0001 at counter 0, as a fixed string.
CANON_TASK_0001_C0 = (
    '{"algorithm":"market_memory.e0_condition_order.sha256_rejection_v1","counter":0,'
    '"study_id":"mm-e0-study-synthetic","task_id":"task-0001",'
    '"tasks_sha256":"65b22df3c4586f0d3044c5a58b745f86c5e19382630b72ba5a3f00dc7433bce8"}'
)
DIGEST_TASK_0001_C0 = "b91ef22d3a1326fecf7a9511653c27c7d16073a1f02b17ce9480aef18c287797"
INTEGER_TASK_0001_C0 = 83732553841777148443708300000956982803180251066296889111825352905422753265559
INDEX_TASK_0001_C0 = 3
ORDER_TASK_0001 = ["recency", "fixed_l1", "no_memory"]
ORDER_TASK_0002 = ["fixed_l1", "no_memory", "recency"]
ORDER_TASK_0003 = ["no_memory", "recency", "fixed_l1"]

# Whole-record binding vector for TASK_IDS under the fixed inputs above.
EXPECTED_ALLOCATION_SHA256 = "f2d92b31429aab42ee236e6e8604255c750a5fe12b71e2fa8f2debe6548aa7d5"
EXPECTED_RECORD = {
    "schema": "research_factory.market_memory_e0_condition_order.v1",
    "authority": "display_only",
    "algorithm": ALGORITHM,
    "study_id": STUDY_ID,
    "tasks_sha256": TASKS_SHA256,
    "seed_hex": SEED_HEX,
    "seed_is_secret": False,
    "conditions": list(CONDITIONS),
    "assignments": [
        {"task_id": "task-0001", "order": ORDER_TASK_0001},
        {"task_id": "task-0002", "order": ORDER_TASK_0002},
        {"task_id": "task-0003", "order": ORDER_TASK_0003},
    ],
    "operational_admission": False,
    "blinding_established": False,
    "actual_task_provenance_authenticated": False,
    "allocation_sha256": EXPECTED_ALLOCATION_SHA256,
}
RECORD_KEYS = frozenset(EXPECTED_RECORD)
CANARY = "canary_do_not_echo_9e2b"


def canonical_bytes(payload: dict) -> bytes:
    """Independent canonical encoding, written to the documented flags."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def allocate(ids=None, *, study_id=STUDY_ID, tasks_sha256=TASKS_SHA256, seed_hex=SEED_HEX):
    population = list(TASK_IDS if ids is None else ids)
    return alloc.allocate_condition_order(seed_hex=seed_hex, study_id=study_id,
                                          tasks_sha256=tasks_sha256, task_ids=population)


def orders_by_task(record: dict) -> dict:
    return {item["task_id"]: tuple(item["order"]) for item in record["assignments"]}


def synthetic_population(count: int) -> list:
    return ["synthetic-task-{:06d}".format(index) for index in range(count)]


def digest_of(value: int) -> bytes:
    return value.to_bytes(32, "big")


class StrSubclass(str):
    """Caller-controlled subclass: exactness is about type, not equality."""


class DigestSeam:
    """Test-only stand-in for the private digest step.

    Replacing this internal step is how the rejection loop and the bounded
    refusal are exercised. No production call path accepts outside digest
    values, seed substitution, or any randomness parameter.
    """

    def __init__(self, values, exhausted: bytes | None = None):
        self._values = list(values)
        self._exhausted = digest_of(ACCEPTANCE_BOUND - 1) if exhausted is None else exhausted
        self.payloads: list = []

    def __call__(self, seed_bytes: bytes, payload_bytes: bytes) -> bytes:
        assert type(seed_bytes) is bytes and len(seed_bytes) == 32
        assert type(payload_bytes) is bytes
        self.payloads.append(json.loads(payload_bytes.decode("utf-8")))
        return self._values.pop(0) if self._values else self._exhausted

    @property
    def counters(self) -> list:
        return [entry["counter"] for entry in self.payloads]

    @property
    def calls(self) -> int:
        return len(self.payloads)


@pytest.fixture
def patch_digest(monkeypatch):
    def apply(seam: DigestSeam) -> DigestSeam:
        monkeypatch.setattr(alloc, "_digest", seam)
        return seam
    return apply


# --- Known vectors ----------------------------------------------------------


def test_known_vector_canonical_payload_digest_and_index_are_reproducible_standalone():
    payload = {
        "algorithm": ALGORITHM,
        "study_id": STUDY_ID,
        "tasks_sha256": TASKS_SHA256,
        "task_id": "task-0001",
        "counter": 0,
    }
    encoded = canonical_bytes(payload)
    assert encoded.decode("utf-8") == CANON_TASK_0001_C0
    digest = hashlib.sha256(bytes.fromhex(SEED_HEX) + encoded).hexdigest()
    assert digest == DIGEST_TASK_0001_C0
    value = int.from_bytes(bytes.fromhex(digest), "big")
    assert value == INTEGER_TASK_0001_C0
    assert value < ACCEPTANCE_BOUND, "the known vector must lie inside the accepted range"
    assert value % ORDERING_SPACE == INDEX_TASK_0001_C0
    assert EXPECTED_PERMUTATIONS[INDEX_TASK_0001_C0] == ORDER_TASK_0001


def test_known_vector_end_to_end_record():
    assert allocate() == EXPECTED_RECORD


def test_conditions_and_permutation_space_are_exactly_the_preregistration():
    assert alloc.CONDITIONS == CONDITIONS
    assert EXPECTED_PERMUTATIONS[0] == list(CONDITIONS)
    assert len(EXPECTED_PERMUTATIONS) == ORDERING_SPACE
    assert len({tuple(item) for item in EXPECTED_PERMUTATIONS}) == ORDERING_SPACE
    assert [list(item) for item in alloc.PERMUTATIONS] == EXPECTED_PERMUTATIONS
    assert alloc.ALGORITHM == ALGORITHM
    assert alloc.OUTPUT_SCHEMA == "research_factory.market_memory_e0_condition_order.v1"


def test_each_task_gets_exactly_three_distinct_conditions():
    record = allocate(synthetic_population(300))
    assert len(record["assignments"]) == 300
    for item in record["assignments"]:
        assert type(item["order"]) is list
        assert len(item["order"]) == 3
        assert len(set(item["order"])) == 3
        assert set(item["order"]) == set(CONDITIONS)


def test_all_six_orderings_are_reachable_under_the_frozen_seed():
    # Structural coverage of the mapping space only. This claims no balance,
    # randomness, or inferential property.
    observed = set(orders_by_task(allocate(synthetic_population(300))).values())
    assert observed == {tuple(item) for item in EXPECTED_PERMUTATIONS}


# --- Determinism, input order, detachment ----------------------------------


def test_caller_input_order_cannot_affect_output():
    population = synthetic_population(40)
    forward = allocate(population)
    reversed_order = allocate(list(reversed(population)))
    rotated = allocate(population[17:] + population[:17])
    reordered = allocate(sorted(population, key=lambda item: hashlib.sha256(item.encode("utf-8")).hexdigest()))
    assert forward == reversed_order == rotated == reordered
    assert [item["task_id"] for item in forward["assignments"]] == sorted(population)


def test_repeated_calls_are_identical_and_independent_objects():
    first = allocate()
    second = allocate()
    assert first == second
    assert first is not second
    assert first["assignments"] is not second["assignments"]
    assert first["conditions"] is not second["conditions"]
    assert first["assignments"][0] is not second["assignments"][0]


def test_mutating_the_result_cannot_affect_later_calls():
    snapshot = allocate()
    expected = copy.deepcopy(snapshot)
    snapshot["conditions"].append("challenger")
    snapshot["assignments"][0]["order"][0] = "tampered"
    snapshot["assignments"].append({"task_id": "injected", "order": []})
    snapshot["schema"] = "tampered-schema"
    assert allocate() == expected
    assert alloc.CONDITIONS == CONDITIONS
    assert alloc.FROZEN_SEED_HEX == SEED_HEX
    assert [list(item) for item in alloc.PERMUTATIONS] == EXPECTED_PERMUTATIONS


def test_mutating_the_input_list_cannot_retroactively_change_a_result():
    ids = ["task-0001", "task-0002"]
    record = allocate(ids)
    ids.append("task-0003")
    ids[0] = "task-mutated"
    assert record == allocate(["task-0001", "task-0002"])


def test_output_is_detached_json_native_with_no_extra_claims():
    record = allocate()
    text = canonical_bytes(record).decode("utf-8")
    assert json.loads(text) == record
    _assert_json_native(record)
    assert set(record) == set(RECORD_KEYS)
    assert record["authority"] == "display_only"
    assert record["seed_is_secret"] is False
    assert record["operational_admission"] is False
    assert record["blinding_established"] is False
    assert record["actual_task_provenance_authenticated"] is False
    forbidden = {"p_value", "pvalues", "confidence", "interval", "acceptance", "admitted",
                 "outcome", "label", "reviewer_id", "source_read", "effect_size",
                 "significance", "secret_bytes", "challenge"}
    assert not set(RECORD_KEYS) & forbidden
    for item in record["assignments"]:
        assert set(item) == {"task_id", "order"}


def _assert_json_native(node):
    assert type(node) in (dict, list, str, bool, int)
    if type(node) is dict:
        for key, value in node.items():
            assert type(key) is str
            _assert_json_native(value)
    elif type(node) is list:
        for value in node:
            _assert_json_native(value)


def test_allocation_digest_binds_the_record_and_excludes_itself():
    record = allocate()
    body = {key: value for key, value in record.items() if key != "allocation_sha256"}
    assert record["allocation_sha256"] == hashlib.sha256(canonical_bytes(body)).hexdigest()
    assert "allocation_sha256" not in json.dumps(body, sort_keys=True)
    tampered = copy.deepcopy(body)
    tampered["assignments"][2]["order"] = list(EXPECTED_PERMUTATIONS[5])
    assert tampered["assignments"][2]["order"] != record["assignments"][2]["order"]
    assert hashlib.sha256(canonical_bytes(tampered)).hexdigest() != record["allocation_sha256"]


def test_study_binding_change_changes_the_digest():
    changed = allocate(study_id="mm-e0-study-other")
    assert changed["allocation_sha256"] != EXPECTED_RECORD["allocation_sha256"]
    assert set(orders_by_task(changed).values()) <= {tuple(item) for item in EXPECTED_PERMUTATIONS}


def test_tasks_digest_binding_change_changes_the_digest_and_the_orders():
    other = hashlib.sha256(b"synthetic-registered-task-manifest-v2").hexdigest()
    changed = allocate(tasks_sha256=other)
    assert changed["tasks_sha256"] == other
    assert changed["allocation_sha256"] != EXPECTED_RECORD["allocation_sha256"]
    assert orders_by_task(changed) != orders_by_task(EXPECTED_RECORD)


def test_changing_any_single_task_id_changes_the_digest():
    baseline = allocate()
    for index in range(len(TASK_IDS)):
        mutated = list(TASK_IDS)
        mutated[index] = "task-000x"
        assert allocate(mutated)["allocation_sha256"] != baseline["allocation_sha256"]
    assert allocate(TASK_IDS[:2])["allocation_sha256"] != baseline["allocation_sha256"]
    assert allocate(TASK_IDS + ["task-0004"])["allocation_sha256"] != baseline["allocation_sha256"]


def test_adding_a_task_does_not_disturb_existing_allocations():
    single = allocate(["task-0001"])
    pair = allocate(["task-0001", "task-0002"])
    assert single["assignments"][0]["order"] == pair["assignments"][0]["order"]
    assert pair["assignments"][1]["order"] == ORDER_TASK_0002


# --- Validation refusals ----------------------------------------------------


def test_seed_must_be_the_frozen_preregistered_value():
    other = hashlib.sha256(b"synthetic-not-the-frozen-seed").hexdigest()
    assert other != SEED_HEX
    for candidate in (other, SEED_HEX.upper(), SEED_HEX[:-1] + "0"):
        with pytest.raises(alloc.AllocationError) as caught:
            allocate(seed_hex=candidate)
        assert caught.value.reason in (alloc.REASON_SEED_FORMAT, alloc.REASON_SEED_NOT_FROZEN)
    with pytest.raises(alloc.AllocationError) as exact:
        allocate(seed_hex=other)
    assert exact.value.reason == alloc.REASON_SEED_NOT_FROZEN


@pytest.mark.parametrize("field", ["seed_hex", "tasks_sha256"])
@pytest.mark.parametrize("bad", ["", "0" * 63, "0" * 65, "z" * 64, " 0" + "0" * 62,
                                 "0" * 64 + "\n", "0" * 32 + "-" + "0" * 31,
                                 "7c8013e1e8092bdf91d4598a73c01d9690199dfb6c08db632b81f564367a4b0",
                                 "7C8013E1E8092BDF91D4598A73C01D9690199DFB6C08DB632B81F564367A4B03"])
def test_malformed_hex_digests_are_refused(field, bad):
    kwargs = {"seed_hex": SEED_HEX, "tasks_sha256": TASKS_SHA256}
    kwargs[field] = bad
    expected = alloc.REASON_SEED_FORMAT if field == "seed_hex" else alloc.REASON_DIGEST_FORMAT
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(**kwargs)
    assert caught.value.reason == expected


@pytest.mark.parametrize("field", ["seed_hex", "study_id", "tasks_sha256"])
@pytest.mark.parametrize("bad", [None, 0, 1, 7, 7.5, True, False, b"", b"task", bytearray(b"task"),
                                 [], (), {}, set(), object()])
def test_scalar_fields_must_be_native_str_not_coerced(field, bad):
    kwargs = {"seed_hex": SEED_HEX, "study_id": STUDY_ID, "tasks_sha256": TASKS_SHA256}
    kwargs[field] = bad
    with pytest.raises(alloc.AllocationError) as caught:
        alloc.allocate_condition_order(task_ids=TASK_IDS, **kwargs)
    assert caught.value.reason.endswith("_must_be_native_str")


@pytest.mark.parametrize("field", ["seed_hex", "study_id", "tasks_sha256"])
def test_str_subclasses_are_refused_and_never_coerced(field):
    valid = {"seed_hex": SEED_HEX, "study_id": STUDY_ID, "tasks_sha256": TASKS_SHA256}
    kwargs = dict(valid)
    kwargs[field] = StrSubclass(valid[field])
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(**kwargs)
    assert caught.value.reason.endswith("_must_be_native_str")


def test_subclassed_task_ids_are_refused():
    with pytest.raises(alloc.AllocationError) as caught:
        allocate([StrSubclass("task-0001"), StrSubclass("task-0002")])
    assert caught.value.reason == alloc.REASON_TASK_TYPE
    with pytest.raises(alloc.AllocationError) as mixed:
        allocate(["task-0001", StrSubclass("task-0002")])
    assert mixed.value.reason == alloc.REASON_TASK_TYPE


@pytest.mark.parametrize("bad_ids", [[True], [1], [None], [0.5], [object()],
                                     ["task-0001", True], ["task-0001", 2], [bytes(), "task"]])
def test_non_str_task_ids_are_refused(bad_ids):
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(bad_ids)
    assert caught.value.reason == alloc.REASON_TASK_TYPE


@pytest.mark.parametrize("bad_container", [
    ("task-0001", "task-0002"), "task-0001", {"task-0001"}, {"task-0001": True},
    iter(["task-0001"]), 5, None, bytearray(b"task"), str, list])
def test_task_ids_must_be_an_exact_native_list(bad_container):
    with pytest.raises(alloc.AllocationError) as caught:
        alloc.allocate_condition_order(seed_hex=SEED_HEX, study_id=STUDY_ID,
                                       tasks_sha256=TASKS_SHA256, task_ids=bad_container)
    assert caught.value.reason == alloc.REASON_POPULATION_TYPE


def test_empty_and_oversized_populations_are_refused():
    assert alloc.MAX_TASK_IDS == 10000
    with pytest.raises(alloc.AllocationError) as empty:
        allocate([])
    assert empty.value.reason == alloc.REASON_POPULATION_EMPTY
    with pytest.raises(alloc.AllocationError) as oversized:
        allocate(synthetic_population(alloc.MAX_TASK_IDS + 1))
    assert oversized.value.reason == alloc.REASON_POPULATION_OVERSIZED
    assert allocate(synthetic_population(1))["assignments"], "one task is a legal population"


def test_whole_permitted_population_boundary_is_allocated():
    record = allocate(synthetic_population(alloc.MAX_TASK_IDS))
    assert len(record["assignments"]) == alloc.MAX_TASK_IDS
    assert [item["task_id"] for item in record["assignments"]] == sorted(synthetic_population(alloc.MAX_TASK_IDS))
    assert set(orders_by_task(record).values()) == {tuple(item) for item in EXPECTED_PERMUTATIONS}


def test_duplicate_task_ids_are_refused():
    for population in (["task-0001", "task-0001"],
                       ["task-0001", "task-0002", "task-0001"],
                       ["task-0001", "task-0002", "task-0002"]):
        with pytest.raises(alloc.AllocationError) as caught:
            allocate(population)
        assert caught.value.reason == alloc.REASON_TASK_DUPLICATE


IDENTIFIER_REJECTIONS = [
    "", "-", "-task", ".task", "_task", ":task", "task/0001", "task 0001", "task\t0001",
    "task\n0001", "task\x0c", "task+0001", "task#1", "task$1", "task%1", "task'1", 'task"1',
    "task\x00", "taské", "café", "café ", "日本語", "task\ud800", "task\udfff", "task\u200b",
    "task\u00a00001", "task\U0001f600", "task" + "x" * 127, "e" * 129, "task\x1f",
]


@pytest.mark.parametrize("bad_id", IDENTIFIER_REJECTIONS)
def test_malformed_task_ids_are_refused(bad_id):
    with pytest.raises(alloc.AllocationError) as caught:
        allocate([bad_id])
    assert caught.value.reason == alloc.REASON_TASK_FORMAT


@pytest.mark.parametrize("bad_id", IDENTIFIER_REJECTIONS)
def test_malformed_study_ids_are_refused(bad_id):
    # study_id and task_id share the registry alphabet, so the same malformed
    # values must be refused with the study-specific reason.
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(study_id=bad_id)
    assert caught.value.reason == alloc.REASON_STUDY_FORMAT


def test_permitted_identifier_alphabet_boundaries_are_accepted():
    longest = "z" + "0" * 127
    assert len(longest) == 128
    for identifier in ("a", "9", "z" + "0" * 127, "a.b:c-d_e", "A1_", "task.0001:rev-2"):
        record = allocate([identifier])
        assert record["assignments"][0]["task_id"] == identifier
        assert len(record["assignments"][0]["order"]) == 3


def test_allocation_error_is_a_valueerror_carrying_only_a_stable_reason():
    assert issubclass(alloc.AllocationError, ValueError)
    with pytest.raises(ValueError):
        allocate([])
    error = alloc.AllocationError(alloc.REASON_TASK_DUPLICATE)
    assert str(error) == error.reason == "duplicate_task_id"
    assert repr(error) == "AllocationError('duplicate_task_id')"


def test_errors_never_echo_the_rejected_input():
    cases = [
        {"study_id": CANARY + "$"},
        {"tasks_sha256": CANARY + "0" * 42},
        {"seed_hex": CANARY + "0" * 42},
    ]
    for case in cases:
        arguments = {"study_id": STUDY_ID, "tasks_sha256": TASKS_SHA256, "seed_hex": SEED_HEX}
        arguments.update(case)
        with pytest.raises(alloc.AllocationError) as caught:
            allocate(**arguments)
        assert CANARY not in str(caught.value)
        assert CANARY not in repr(caught.value)
    with pytest.raises(alloc.AllocationError) as duplicate:
        allocate([CANARY, CANARY])
    assert duplicate.value.reason == alloc.REASON_TASK_DUPLICATE
    assert CANARY not in str(duplicate.value)
    for case in cases:
        arguments = {"study_id": STUDY_ID, "tasks_sha256": TASKS_SHA256, "seed_hex": SEED_HEX}
        arguments.update(case)
        with pytest.raises(alloc.AllocationError) as caught:
            allocate(**arguments)
        message = str(caught.value)
        assert message == message.lower() and " " not in message and len(message) < 64
        assert message.startswith(("seed_", "study_", "tasks_", "task_", "empty_",
                                   "oversized_", "duplicate_", "allocation_", "invalid_"))


# --- Call form, surface, and purity ----------------------------------------


def test_signature_is_closed_keyword_only_with_no_randomness_knob():
    signature = inspect.signature(alloc.allocate_condition_order)
    parameters = list(signature.parameters.values())
    assert [item.name for item in parameters] == ["seed_hex", "study_id", "tasks_sha256", "task_ids"]
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in parameters)
    for extra in ("rng", "random_seed", "algorithm", "conditions", "counter", "seed_bytes",
                  "digest_fn", "hash_fn", "rejection_bound", "attempts", "task_id"):
        arguments = {"seed_hex": SEED_HEX, "study_id": STUDY_ID, "tasks_sha256": TASKS_SHA256,
                     "task_ids": TASK_IDS, extra: 1}
        with pytest.raises(TypeError):
            alloc.allocate_condition_order(**arguments)
    with pytest.raises(TypeError):
        alloc.allocate_condition_order(SEED_HEX, STUDY_ID, TASKS_SHA256, TASK_IDS)


def test_module_surface_has_no_write_access_budget_or_reservation_api():
    public = {name for name in dir(alloc) if not name.startswith("_")}
    assert {name for name in public if callable(getattr(alloc, name))} == {
        "AllocationError", "allocate_condition_order"}
    assert not public & {"open", "write", "save", "reserve", "budget", "grant", "access",
                         "register", "submit", "execute", "run", "random", "seed"}


def test_global_random_state_is_unchanged():
    random.seed(20261012)
    before = random.getstate()
    reference = [random.random(), random.getrandbits(256), random.choice(CONDITIONS)]
    random.seed(20261012)
    held_state = random.getstate()
    allocate()
    allocate(synthetic_population(120))
    allocate(["task-0001"], study_id="mm-e0-study-other")
    assert random.getstate() == held_state, "allocation must not consume global randomness"
    after = [random.random(), random.getrandbits(256), random.choice(CONDITIONS)]
    assert after == reference
    assert before == held_state


def test_source_is_free_of_nondeterministic_entropy_and_io_uses():
    source = pathlib.Path(alloc.__file__).read_text(encoding="utf-8")
    for token in ("import random", "from random", "random.", "import time", "from time",
                  "datetime", "perf_counter", "monotonic", "time()", "urandom", "token_hex",
                  "os.environ", "environ[", "getenv", "hash(", "secrets", "uuid", "socket",
                  "subprocess", "threading", "multiprocessing", "open(", "__import__",
                  "eval(", "exec("):
        assert token not in source, token
    assert "itertools.permutations(CONDITIONS)" in source
    for flag in ("sort_keys=True", 'separators=(",", ":")', "ensure_ascii=False", "allow_nan=False"):
        assert flag in source, flag
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name.split(".")[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            raise AssertionError("module mutates shared state")
        elif isinstance(node, ast.Call):
            called = node.func
            name = getattr(called, "id", None) or getattr(called, "attr", None) or ""
            assert name not in {"open", "eval", "exec", "__import__", "input", "locals", "vars"}, name
    assert imports <= {"__future__", "hashlib", "itertools", "json", "re"}, imports
    # The frozen preregistration constants are module-level literal bindings.
    bindings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None):
                    bindings[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None):
            bindings[node.target.id] = node.value
    for constant in ("CONDITIONS", "FROZEN_SEED_HEX", "ALGORITHM", "OUTPUT_SCHEMA",
                     "MAX_TASK_IDS", "MAX_HASH_ATTEMPTS_PER_TASK"):
        assert isinstance(bindings[constant], (ast.Constant, ast.Call, ast.Tuple)), constant


# --- Controlled digest seam: rejection loop and bounded refusal -------------


def test_seam_rejection_advances_the_counter_and_selects_the_accepted_index(patch_digest):
    seam = patch_digest(DigestSeam([digest_of(2**256 - 1), digest_of(2**256 - 2),
                                    digest_of(ACCEPTANCE_BOUND - 1)]))
    record = allocate(["task-0001"])
    assert record["assignments"][0]["order"] == EXPECTED_PERMUTATIONS[5]
    assert seam.calls == 3
    assert seam.counters == [0, 1, 2]
    for entry in seam.payloads:
        assert entry["task_id"] == "task-0001"
        assert entry["study_id"] == STUDY_ID
        assert entry["tasks_sha256"] == TASKS_SHA256
        assert entry["algorithm"] == ALGORITHM
        assert set(entry) == {"algorithm", "study_id", "tasks_sha256", "task_id", "counter"}


def test_seam_acceptance_bound_is_exclusive(patch_digest):
    assert ACCEPTANCE_BOUND % ORDERING_SPACE == 0
    assert alloc.MAX_HASH_ATTEMPTS_PER_TASK == 1024
    seam = patch_digest(DigestSeam([digest_of(ACCEPTANCE_BOUND), digest_of(ACCEPTANCE_BOUND - 1)]))
    record = allocate(["task-0001"])
    assert record["assignments"][0]["order"] == EXPECTED_PERMUTATIONS[5]
    assert seam.counters == [0, 1]


def test_seam_smallest_and_largest_accepted_values(patch_digest):
    seam = patch_digest(DigestSeam([digest_of(0)]))
    assert allocate(["task-0001"])["assignments"][0]["order"] == list(CONDITIONS)
    assert seam.counters == [0]
    second = patch_digest(DigestSeam([digest_of(5)]))
    assert allocate(["task-0002"])["assignments"][0]["order"] == EXPECTED_PERMUTATIONS[5]
    assert second.counters == [0]


def test_seam_refuses_after_exactly_the_documented_attempt_bound(patch_digest):
    refused = digest_of(2**256 - 1)
    seam = patch_digest(DigestSeam([refused] * (alloc.MAX_HASH_ATTEMPTS_PER_TASK + 8)))
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(["task-0001"])
    assert caught.value.reason == alloc.REASON_ENTROPY_BOUND == "allocation_entropy_bound"
    assert seam.calls == alloc.MAX_HASH_ATTEMPTS_PER_TASK
    assert seam.counters == list(range(alloc.MAX_HASH_ATTEMPTS_PER_TASK))


def test_seam_refusal_is_per_task_and_emits_no_partial_record(patch_digest):
    seam = patch_digest(DigestSeam([digest_of(2**256 - 1)] * 4096))
    with pytest.raises(alloc.AllocationError) as caught:
        allocate(synthetic_population(3))
    assert caught.value.reason == alloc.REASON_ENTROPY_BOUND
    assert seam.calls == alloc.MAX_HASH_ATTEMPTS_PER_TASK, "refusal must stop at the first task"


def test_seam_all_tasks_may_reject_independently_and_still_allocate(patch_digest):
    seam = patch_digest(DigestSeam([digest_of(2**256 - 1), digest_of(1),
                                    digest_of(2**256 - 2), digest_of(2),
                                    digest_of(3)]))
    record = allocate(synthetic_population(3))
    assert [item["order"] for item in record["assignments"]] == [
        EXPECTED_PERMUTATIONS[1], EXPECTED_PERMUTATIONS[2], EXPECTED_PERMUTATIONS[3]]
    assert seam.counters == [0, 1, 0, 1, 0]


def test_seam_path_still_produces_a_wellformed_display_only_record(patch_digest):
    patch_digest(DigestSeam([digest_of(0)] * 3))
    record = allocate(synthetic_population(3))
    assert record["authority"] == "display_only"
    assert record["seed_hex"] == SEED_HEX
    assert record["conditions"] == list(CONDITIONS)
    assert [item["order"] for item in record["assignments"]] == [EXPECTED_PERMUTATIONS[0]] * 3
    assert len(set(orders_by_task(record).values())) == 1
    body = {key: value for key, value in record.items() if key != "allocation_sha256"}
    assert record["allocation_sha256"] == hashlib.sha256(canonical_bytes(body)).hexdigest()
    assert record["operational_admission"] is False
    assert record["blinding_established"] is False
    assert record["actual_task_provenance_authenticated"] is False
    assert record["seed_is_secret"] is False


def test_the_private_digest_step_is_the_unpatched_documentary_formula():
    # Reference behaviour with no seam in place: the real step is exactly
    # SHA-256 over the frozen seed bytes concatenated with the canonical payload.
    assert alloc._digest(bytes.fromhex(SEED_HEX), CANON_TASK_0001_C0.encode("utf-8"))
    assert hashlib.sha256(bytes.fromhex(SEED_HEX) + CANON_TASK_0001_C0.encode("utf-8")).digest() == \
        bytes.fromhex(DIGEST_TASK_0001_C0)
    assert allocate() == EXPECTED_RECORD
