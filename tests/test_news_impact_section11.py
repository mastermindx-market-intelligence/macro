"""Tests for the section 11 draws and registration (DEC:NEWS-IMPACT-SECTION11-REPORT).

The draw and join tests are synthetic: neutral ids, no filing text, no labeled values. The
registration tests rebuild the committed registration from the committed benchmark inputs,
which hold ids, enums and counts only, and check the clauses the DEC freezes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from engine.news_impact import eval_receipt as er
from engine.news_impact import section11_draws as draws
from engine.news_impact import section11_registration as reg


def _cases(spec: dict[str, int]) -> list[dict[str, str]]:
    rows = []
    for key, n in spec.items():
        template, cell = key.split("-", 1)
        rows += [{"case_id": f"c-{key}-{i:03d}", "template": template, "proxy_cell": cell} for i in range(n)]
    return rows


# --- frontier_only_audit_draw -------------------------------------------------------


def test_frontier_draw_takes_ceil_of_rate_in_every_cell():
    out = draws.frontier_only_audit_draw(_cases({"T1-positive": 30, "T1-negative": 1, "T2-ambiguous": 4}))
    assert out["per_cell"] == {
        "T1-negative": {"n": 1, "drawn": 1},
        "T1-positive": {"n": 30, "drawn": 3},
        "T2-ambiguous": {"n": 4, "drawn": 1},
    }
    assert out["n_population"] == 35 and out["n_drawn"] == 5 == len(out["case_ids"])
    assert out["seed"] == 20261021 and out["rate"] == 0.10


def test_frontier_draw_is_deterministic_and_order_free():
    rows = _cases({"T1-positive": 20, "T2-negative": 7})
    a = draws.frontier_only_audit_draw(rows)
    b = draws.frontier_only_audit_draw(list(reversed(rows)))
    assert a == b


def test_frontier_draw_depends_on_seed():
    rows = _cases({"T1-positive": 40})
    picks = {tuple(draws.frontier_only_audit_draw(rows, seed=s)["case_ids"]) for s in (1, 2, 3, 4)}
    assert len(picks) > 1


def test_frontier_draw_is_nested_when_the_rate_grows():
    rows = _cases({"T1-positive": 50})
    small = set(draws.frontier_only_audit_draw(rows, rate=0.10)["case_ids"])
    large = set(draws.frontier_only_audit_draw(rows, rate=0.20)["case_ids"])
    assert small < large


@pytest.mark.parametrize("rate", [0.0, -0.1, 1.5])
def test_frontier_draw_refuses_a_bad_rate(rate):
    with pytest.raises(ValueError):
        draws.frontier_only_audit_draw(_cases({"T1-positive": 3}), rate=rate)


def test_frontier_draw_refuses_duplicates_and_empty_fields():
    rows = _cases({"T1-positive": 2})
    with pytest.raises(ValueError):
        draws.frontier_only_audit_draw(rows + [dict(rows[0])])
    with pytest.raises(ValueError):
        draws.frontier_only_audit_draw([{"case_id": "c1", "template": "T1", "proxy_cell": ""}])


# --- gold_agreed_audit_draw ---------------------------------------------------------


def _slots(spec: dict[str, int]) -> list[tuple[str, str, str, str]]:
    out = []
    for key, n in spec.items():
        template, kind = key.split("-", 1)
        out += [(f"c-{key}-{i:03d}", template, "stated_amount", kind) for i in range(n)]
    return out


def test_gold_draw_takes_every_slot_when_the_population_is_small():
    slots = _slots({"T1-present": 10, "T2-absent": 5})
    out = draws.gold_agreed_audit_draw(slots, size=40)
    assert out["n_drawn"] == 15 == out["n_population"]
    assert out["seed"] == 20261022


def test_gold_draw_is_proportional_by_template_and_kind():
    out = draws.gold_agreed_audit_draw(_slots({"T1-present": 60, "T1-absent": 20, "T2-present": 20}), size=40)
    assert out["per_cell"] == {
        "T1-absent": {"n": 20, "drawn": 8},
        "T1-present": {"n": 60, "drawn": 24},
        "T2-present": {"n": 20, "drawn": 8},
    }
    assert out["n_drawn"] == 40


def test_gold_draw_is_deterministic_and_keys_on_case_and_field():
    slots = _slots({"T1-present": 70}) + [("c-x", "T1", "incremental_amount", "present")]
    a = draws.gold_agreed_audit_draw(slots, size=10)
    b = draws.gold_agreed_audit_draw(list(reversed(slots)), size=10)
    assert a == b
    assert all(len(s) == 2 for s in a["slots"])


def test_gold_draw_refuses_bad_input():
    with pytest.raises(ValueError):
        draws.gold_agreed_audit_draw(_slots({"T1-present": 2}), size=0)
    with pytest.raises(ValueError):
        draws.gold_agreed_audit_draw([("c1", "T1", "stated_amount", "disputed")])
    with pytest.raises(ValueError):
        draws.gold_agreed_audit_draw([("c1", "T1", "stated_amount", "present")] * 2)


# --- registration joins (synthetic) -------------------------------------------------


def _routing(ids_templates: dict[str, str]) -> dict:
    return {
        "scorable_match": list(ids_templates),
        "routing_map": {cid: {"template": t, "class": "MATCH"} for cid, t in ids_templates.items()},
    }


def _case(cid: str, template: str, fold: str = "f1") -> dict:
    return {"item_id": cid, "template": template, "proxy_cell": "positive", "fold": fold}


def test_match_rows_join_routing_to_cases():
    rows = reg.match_rows(_routing({"b": "T2", "a": "T1"}), [_case("a", "T1"), _case("b", "T2", "f3"), _case("z", "T1")])
    assert rows == [
        {"case_id": "a", "template": "T1", "proxy_cell": "positive", "fold": "f1"},
        {"case_id": "b", "template": "T2", "proxy_cell": "positive", "fold": "f3"},
    ]


@pytest.mark.parametrize(
    "routing, cases, code",
    [
        (_routing({"a": "T1"}), [_case("b", "T1")], "MATCH_ID_NOT_IN_CASES"),
        (_routing({"a": "T1"}), [_case("a", "T2")], "TEMPLATE_DISAGREES"),
        (_routing({"a": "T1"}), [_case("a", "T1", "f9")], "NON_HISTORICAL_FOLD"),
        ({"scorable_match": ["a", "a"], "routing_map": {"a": {"template": "T1"}}}, [_case("a", "T1")], "DUPLICATE_MATCH_ID"),
    ],
)
def test_match_rows_refuse_a_broken_join(routing, cases, code):
    with pytest.raises(reg.RegistrationError) as exc:
        reg.match_rows(routing, cases)
    assert exc.value.code == code


def _slot(cid: str, field: str, template: str = "T2", version: str = "prompt-v1.1") -> dict:
    return {"case_id": cid, "field": field, "template": template, "prompt_version": version}


@pytest.fixture
def two_cases(monkeypatch):
    monkeypatch.setattr(reg, "EXPECTED_CRITICAL_SLOTS", {"T2": {"stated_amount": 2}})
    rows = [{"case_id": "a", "template": "T2"}, {"case_id": "q", "template": "T2"}]
    return rows, ["q"]


def test_slot_counts_take_queue_cases_from_w2q_only(two_cases):
    rows, queue = two_cases
    w2 = [_slot("a", "stated_amount"), _slot("q", "stated_amount"), _slot("other", "stated_amount")]
    w2q = [_slot("q", "stated_amount", version="prompt-v1.2")]
    counts, versions = reg.critical_slot_counts(rows, queue, w2, w2q)
    assert counts == {"T2": {"stated_amount": 2}}
    assert versions == {"w2": {"prompt-v1.1": 1}, "w2q": {"prompt-v1.2": 1}}


@pytest.mark.parametrize(
    "w2, w2q, code",
    [
        ([_slot("a", "stated_amount"), _slot("a", "stated_amount")], [_slot("q", "stated_amount")], "DUPLICATE_SLOT"),
        ([_slot("a", "headline_word")], [_slot("q", "stated_amount")], "NOT_A_CRITICAL_FIELD"),
        ([_slot("a", "stated_amount")], [], "MATCH_CASE_WITHOUT_SLOTS"),
        ([], [_slot("a", "stated_amount"), _slot("q", "stated_amount")], "W2Q_SLOT_OUTSIDE_QUEUE"),
        ([_slot("a", "stated_amount")], [_slot("q", "stated_amount", "T3")], "CRITICAL_SLOT_COUNTS_CHANGED"),
    ],
)
def test_slot_counts_refuse(two_cases, w2, w2q, code):
    rows, queue = two_cases
    with pytest.raises(reg.RegistrationError) as exc:
        reg.critical_slot_counts(rows, queue, w2, w2q)
    assert exc.value.code == code


def test_self_check_refuses_a_forbidden_key_and_a_forbidden_word():
    with pytest.raises(reg.RegistrationError) as exc:
        reg.self_check({"gold": {"rating_rule": "x"}})
    assert exc.value.code == "FORBIDDEN_KEY"
    with pytest.raises(er.EvalReceiptError):
        reg.self_check({"note": "this " + "will hold"})


def test_pin_inputs_refuses_a_missing_file(tmp_path):
    with pytest.raises(reg.RegistrationError) as exc:
        reg.pin_inputs(tmp_path)
    assert exc.value.code == "INPUT_MISSING"


def test_pin_inputs_refuses_a_changed_frozen_input(monkeypatch):
    monkeypatch.setitem(reg.FROZEN_SHA256, "sut_prompt", "0" * 64)
    with pytest.raises(reg.RegistrationError) as exc:
        reg.pin_inputs(reg.ROOT)
    assert exc.value.code == "FROZEN_INPUT_CHANGED"


# --- the committed registration -----------------------------------------------------


@pytest.fixture(scope="module")
def built():
    return reg.build_historical_registration_v1()


def test_committed_registration_matches_explicit_historical_v1(built):
    committed = (reg.ROOT / reg.DEFAULT_OUT).read_bytes()
    assert committed == reg.render(built).encode("utf-8")
    assert hashlib.sha256(committed).hexdigest() == "5637cbea2d44533db77d7c77051996cd27dad5e1bb16ba483fd5b1ffeb02a71a"
    assert built["code_versions"]["producer_facts"] == "ni-producer-facts-1"


def test_registration_freezes_the_a3_pins(built):
    a3 = built["a3_registration"]
    assert a3["mode"] == "confirm"
    assert a3["t_prospective"] == "2026-10-15T00:00:00Z"
    assert a3["endpoints_sha256"] == er.load_registry(er.default_registry_path()).sha256
    assert a3["prompt_corpus_sha256"] == built["inputs"]["sut_prompt"]["sha256"]
    assert a3["contract_sha256_prefix"] == er.CONTRACT_SHA256_PREFIX
    assert a3["sampling_seed"] == 20261014


def test_system_under_test_and_gold_are_vendor_disjoint(built):
    sut = built["system_under_test"]
    assert sut["family"] == "qwen" and sut["prompt_version"] == "prompt-v1.2"
    models = [sut["cheap_extractor_no_frontier"]["model"], sut["proposed_cascade"]["frontier_model"]]
    assert all(m.startswith("qwen") for m in models)
    gold = built["gold"]
    assert not any(f.lower().startswith("qwen") for f in gold["families"])
    third = [c["model"] for c in built["third_family"]["order"]]
    assert third and not any(m.lower().startswith(("qwen", "glm", "minimax", "mimo")) for m in third)
    assert [c["rank"] for c in built["third_family"]["order"]] == list(range(1, len(third) + 1))


def test_registration_draws_use_the_reserved_seeds(built):
    d = built["draws"]
    assert d["frontier_only_audit"]["seed"] == 20261021
    assert d["gold_agreed_audit"]["seed"] == 20261022
    match_ids = {r[0] for r in built["populations"]["v2_match"]["rows"]}
    drawn = d["frontier_only_audit"]["v2_match_case_ids"]
    assert drawn == built["baselines"]["frontier_only_audit"]["v2_match_draw"]["case_ids"]
    assert set(drawn) <= match_ids
    cells = Counter(f"{r[1]}-{r[2]}" for r in built["populations"]["v2_match"]["rows"])
    assert set(built["baselines"]["frontier_only_audit"]["v2_match_draw"]["per_cell"]) == set(cells)


def test_registration_populations_and_slots(built):
    v2 = built["populations"]["v2_match"]
    assert v2["n"] == 74 == len(v2["rows"])
    assert {t: c["scorable_match"] for t, c in v2["per_template"].items()} == {"T1": 34, "T2": 36, "T3": 4}
    assert all(c["shortfall_vs_200"] == 200 - c["scorable_match"] for c in v2["per_template"].values())
    queue = built["populations"]["label_queue"]["case_ids"]
    assert len(queue) == 12 and set(queue) <= {r[0] for r in v2["rows"]}
    assert built["gold"]["critical_slots_v2_match_total"] == 142
    by_version = built["gold"]["critical_slots_v2_match_by_prompt_version"]
    assert sum(sum(v.values()) for v in by_version.values()) == 142
    assert set(by_version["w2q"]) == {"prompt-v1.2"}


def test_registration_names_every_operator_tap_lane(built):
    cascade = json.loads((reg.ROOT / reg.PINNED_INPUTS["cascade"]).read_text(encoding="utf-8"))
    assert built["operator_tap"]["lanes"] == cascade["lanes_require_operator_tap"]
    assert built["operator_tap"]["measurement_run_slot_caps"] == cascade["measurement_run_slot_caps"]


def test_registration_holds_no_forbidden_key_or_word(built):
    _, stripped = er.strip_forbidden_keys(built)
    assert stripped == []
    reg.self_check(built)

# --- historical integrity is separate from current implementation eligibility -------


def test_historical_reconstruction_does_not_relabel_current_code(built):
    assert reg.current_code_versions()["producer_facts"] == "ni-producer-facts-2"
    assert built["code_versions"]["producer_facts"] == "ni-producer-facts-1"


def test_default_builder_refuses_unregistered_current_implementation():
    with pytest.raises(reg.RegistrationError, match="producer_facts") as exc:
        reg.build_registration()
    assert exc.value.code == "REGISTERED_IMPLEMENTATION_MISMATCH"
    assert "registered=ni-producer-facts-1, current=ni-producer-facts-2" in str(exc.value)


def test_historical_result_cannot_qualify_current_implementation(built):
    with pytest.raises(reg.RegistrationError) as exc:
        reg.require_registered_implementation(built)
    assert exc.value.code == "REGISTERED_IMPLEMENTATION_MISMATCH"


@pytest.mark.parametrize("change", ["changed_component", "missing_component", "extra_component"])
def test_eligibility_checks_the_complete_version_profile(built, monkeypatch, change):
    versions = dict(built["code_versions"])
    if change == "changed_component":
        versions["cluster"] = "ni-cluster-next"
        component = "cluster"
    elif change == "missing_component":
        del versions["issuer"]
        component = "issuer"
    else:
        versions["unregistered_component"] = "unregistered-1"
        component = "unregistered_component"
    monkeypatch.setattr(reg, "current_code_versions", lambda: versions)
    with pytest.raises(reg.RegistrationError, match=component) as exc:
        reg.require_registered_implementation(built)
    assert exc.value.code == "REGISTERED_IMPLEMENTATION_MISMATCH"


def test_matching_profile_passes_only_the_version_guard(built, monkeypatch):
    # Synthetic identity comparison, not execution of the historical producer.
    monkeypatch.setattr(reg, "current_code_versions", lambda: dict(built["code_versions"]))
    assert reg.require_registered_implementation(built) is None


@pytest.mark.parametrize("change", ["code_versions", "registration_version", "population"])
def test_changed_historical_identity_cannot_qualify(built, change):
    forged = copy.deepcopy(built)
    if change == "code_versions":
        forged["code_versions"] = reg.current_code_versions()
    elif change == "registration_version":
        forged["registration_version"] = "ni-section11-registration-2"
    else:
        forged["populations"]["v2_match"]["n"] += 1
    with pytest.raises(reg.RegistrationError) as exc:
        reg.require_registered_implementation(forged)
    assert exc.value.code == "HISTORICAL_REGISTRATION_CHANGED"


def test_historical_profile_is_immutable_and_not_selectable(monkeypatch):
    with pytest.raises(TypeError):
        reg.HISTORICAL_V1_CODE_VERSIONS["producer_facts"] = "ni-producer-facts-2"
    changed = dict(reg.HISTORICAL_V1_CODE_VERSIONS, producer_facts="ni-producer-facts-2")
    monkeypatch.setattr(reg, "HISTORICAL_V1_CODE_VERSIONS", changed)
    with pytest.raises(reg.RegistrationError) as exc:
        reg.build_historical_registration_v1()
    assert exc.value.code == "HISTORICAL_REGISTRATION_CHANGED"


def test_historical_rebuild_refuses_changed_pinned_metadata(tmp_path):
    for rel in reg.PINNED_INPUTS.values():
        destination = tmp_path / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reg.ROOT / rel, destination)
    changed = tmp_path / reg.PINNED_INPUTS["w2_summary"]
    changed.write_bytes(changed.read_bytes() + b"\n")
    with pytest.raises(reg.RegistrationError) as exc:
        reg.build_historical_registration_v1(tmp_path)
    assert exc.value.code == "HISTORICAL_REGISTRATION_CHANGED"


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "engine.news_impact.section11_registration", *map(str, args)],
        cwd=reg.ROOT, capture_output=True, text=True, timeout=45,
    )


@pytest.mark.parametrize("historical", [False, True])
def test_real_cli_distinguishes_historical_integrity_from_current_eligibility(historical):
    frozen = reg.ROOT / reg.DEFAULT_OUT
    before = frozen.read_bytes()
    result = _cli("--check-historical-v1" if historical else "--check")
    assert frozen.read_bytes() == before
    if historical:
        assert result.returncode == 0, result.stderr
        assert "historical v1 integrity ok; current eligibility not checked" in result.stdout
    else:
        assert result.returncode == 1
        assert "REGISTERED_IMPLEMENTATION_MISMATCH" in result.stderr
        assert "registered=ni-producer-facts-1, current=ni-producer-facts-2" in result.stderr


def _alias(tmp_path, kind):
    frozen_copy = tmp_path / "frozen-registration.json"
    frozen_copy.write_bytes((reg.ROOT / reg.DEFAULT_OUT).read_bytes())
    target = tmp_path / "alias.json"
    if kind == "symlink":
        target.symlink_to(frozen_copy)
    elif kind == "hardlink":
        target.hardlink_to(frozen_copy)
    else:
        target = frozen_copy
    return frozen_copy, target


@pytest.mark.parametrize("kind", ["exact", "symlink", "hardlink"])
def test_real_cli_refuses_current_output_without_touching_existing_aliases(tmp_path, kind):
    frozen_copy, target = _alias(tmp_path, kind)
    before = frozen_copy.read_bytes()
    result = _cli("--out", target)
    assert result.returncode == 1
    assert "REGISTERED_IMPLEMENTATION_MISMATCH" in result.stderr
    assert frozen_copy.read_bytes() == target.read_bytes() == before


def test_real_cli_cannot_create_unregistered_v1_copy(tmp_path):
    target = tmp_path / "new-directory" / "unregistered.json"
    result = _cli("--out", target)
    assert result.returncode == 1
    assert "REGISTERED_IMPLEMENTATION_MISMATCH" in result.stderr
    assert not target.parent.exists()


def test_no_argument_default_refuses_and_preserves_an_isolated_frozen_target(tmp_path):
    # Exercise the actual CLI entry point with only its destination root isolated.
    # Builder input defaults remain the real committed inputs; no real freeze is writable.
    frozen = tmp_path / reg.DEFAULT_OUT
    frozen.parent.mkdir(parents=True)
    before = (reg.ROOT / reg.DEFAULT_OUT).read_bytes()
    frozen.write_bytes(before)
    code = (
        "import sys; from pathlib import Path; "
        "from engine.news_impact import section11_registration as reg; "
        "reg.ROOT = Path(sys.argv[1]); raise SystemExit(reg.main([]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=reg.ROOT, capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 1
    assert "REGISTERED_IMPLEMENTATION_MISMATCH" in result.stderr
    assert frozen.read_bytes() == before


@pytest.mark.parametrize("check", ["--check", "--check-historical-v1"])
def test_check_and_out_are_mutually_exclusive_and_cannot_write(tmp_path, check):
    target = tmp_path / "no-output.json"
    result = _cli(check, "--out", target)
    assert result.returncode == 2
    assert not target.exists()


def test_cli_check_modes_are_mutually_exclusive():
    result = _cli("--check", "--check-historical-v1")
    assert result.returncode == 2


def test_historical_check_detects_changed_committed_bytes(tmp_path, monkeypatch, capsys):
    frozen = tmp_path / reg.DEFAULT_OUT
    frozen.parent.mkdir(parents=True)
    tampered = (reg.ROOT / reg.DEFAULT_OUT).read_bytes() + b"\n"
    frozen.write_bytes(tampered)
    monkeypatch.setattr(reg, "ROOT", tmp_path)
    assert reg.main(["--check-historical-v1"]) == 1
    assert "HISTORICAL_REGISTRATION_CHANGED" in capsys.readouterr().err
    assert frozen.read_bytes() == tampered


@pytest.mark.parametrize("kind", ["exact", "symlink", "hardlink"])
def test_eligible_write_path_never_overwrites_existing_aliases(tmp_path, kind):
    frozen_copy, target = _alias(tmp_path, kind)
    before = frozen_copy.read_bytes()
    assert reg._write_new_or_identical(target, before) is False
    with pytest.raises(reg.RegistrationError) as exc:
        reg._write_new_or_identical(target, b"changed")
    assert exc.value.code == "REGISTRATION_OVERWRITE_REFUSED"
    assert frozen_copy.read_bytes() == target.read_bytes() == before


def test_exclusive_creation_refuses_a_destination_arriving_during_write(tmp_path, monkeypatch):
    target = tmp_path / "racing-destination.json"
    original_open = Path.open

    def race(path, mode="r", *args, **kwargs):
        if path == target and mode == "xb":
            with original_open(path, "wb") as stream:
                stream.write(b"arrived-before-create")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", race)
    with pytest.raises(reg.RegistrationError) as exc:
        reg._write_new_or_identical(target, b"must-not-replace")
    assert exc.value.code == "REGISTRATION_OVERWRITE_REFUSED"
    assert target.read_bytes() == b"arrived-before-create"
