"""Recompute the producer rule pins cited by `tests/test_rates_command_outlook_readings.py`.

A pin locks the UTF-8 source of one top-level function, one top-level assignment,
or one dotted key in ``config.yml`` to a sha256 (or a value). Two checks bind:
the pinned value must match the source, and the pinned value must be either the
pin's birth value or the ``to`` of a review entry in
``config/regime_outlook_rule_pins.json`` that names the pin. So when a producer
moves, pasting the new hash alone still fails — the review entry recording the
re-read under contract rule R-E is what makes the new hash acceptable. The birth
values themselves are frozen here, in ``BIRTH_BLOCK_DIGESTS``, keyed by
``pin_commit``: pasting ``birth_sha256`` along with ``sha256`` changes the
digest and fails too. A birth value moves only when the mapping takes a new
``pin_commit`` AND this module gains the matching digest row — both land in one
reviewable diff.
Nothing in this file imports ``engine``; it parses each producer with ``ast``
and hashes the named node's source text by line range.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = REPO_ROOT / "config" / "regime_outlook_rule_pins.json"
MAPPING_PATH = REPO_ROOT / "config" / "regime_outlook_mapping_v2.json"
CONFIG_YML_PATH = REPO_ROOT / "config.yml"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_pins() -> dict:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def _load_mapping() -> dict:
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def _node_lines(path: Path, lineno: int, end_lineno: int) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    return lines[lineno - 1 : end_lineno]


def _find_function_node(tree: ast.Module, name: str):
    return [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]


def _find_constant_node(tree: ast.Module, name: str):
    out = []
    for n in tree.body:
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id == name:
                out.append(n)
    return out


def node_sha256(path: Path, name: str, kind: str) -> str:
    """Hash the named top-level node in ``path``.

    ``kind`` is ``"function"`` (an ``ast.FunctionDef``) or ``"constant"``
    (an ``ast.Assign`` with a single ``ast.Name`` target). Raises
    ``AssertionError`` naming the file and node when the count is not exactly
    one — that is the contract R-1 promise.
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    if kind == "function":
        nodes = _find_function_node(tree, name)
    elif kind == "constant":
        nodes = _find_constant_node(tree, name)
    else:
        raise AssertionError(f"{path}: unknown kind {kind!r}")
    assert len(nodes) == 1, f"{path}: expected exactly one {kind} named {name!r}, found {len(nodes)}"
    node = nodes[0]
    lines = _node_lines(path, node.lineno, node.end_lineno)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def config_value(doc: object, key: list[str]) -> tuple[bool, object]:
    """Walk ``doc`` by ``key``; return ``(present, value)``.

    ``present`` is False and ``value`` is None if any step is missing.
    """
    cur = doc
    for step in key:
        if not isinstance(cur, dict) or step not in cur:
            return False, None
        cur = cur[step]
    return True, cur


def review_problems(review: object, pin_names: set[str]) -> list[str]:
    """Return a list of plain sentences describing problems with ``review``."""
    problems: list[str] = []
    if not isinstance(review, dict):
        problems.append("review is not a dict")
        return problems
    if "date" not in review or not isinstance(review["date"], str) or not _DATE_RE.match(review["date"]):
        problems.append(f"date {review.get('date')!r} does not match YYYY-MM-DD")
    if "reviewer" not in review or not isinstance(review["reviewer"], str) or not review["reviewer"]:
        problems.append("reviewer is missing or empty")
    if "finding" not in review or not isinstance(review["finding"], str) or not review["finding"]:
        problems.append("finding is missing or empty")
    changed = review.get("changed")
    if not isinstance(changed, list) or not changed:
        problems.append("changed is missing or empty")
    else:
        for entry in changed:
            if not isinstance(entry, dict):
                problems.append(f"changed entry {entry!r} is not a dict")
                continue
            pin = entry.get("pin")
            if not isinstance(pin, str):
                problems.append(f"changed entry pin {pin!r} is not a string")
                continue
            if pin not in pin_names:
                problems.append(f"changed entry {pin!r} is not a known pin name")
            for side in ("from", "to"):
                if side not in entry:
                    problems.append(f"changed entry {pin!r} has no {side!r}")
                elif pin.startswith("config.yml:"):
                    if not _config_shape(entry[side]):
                        problems.append(
                            f"changed entry {pin!r} {side!r} is not a {{present, value}} dict with a bool present"
                        )
                elif not (isinstance(entry[side], str) and _SHA_RE.match(entry[side])):
                    problems.append(f"changed entry {pin!r} {side!r} is not a sha256")
            if "from" in entry and "to" in entry and _same_typed(entry["from"], entry["to"]):
                problems.append(f"changed entry {pin!r} records no change")
    return problems


def reviewed_values(reviews: object) -> dict[str, list]:
    """Map each pin name to every ``to`` value some review recorded for it."""
    out: dict[str, list] = {}
    if not isinstance(reviews, list):
        return out
    for review in reviews:
        if not isinstance(review, dict):
            continue
        for entry in review.get("changed") or []:
            if isinstance(entry, dict) and isinstance(entry.get("pin"), str) and "to" in entry:
                out.setdefault(entry["pin"], []).append(entry["to"])
    return out


def acceptance_problems(pin_name: str, current: object, birth: object, reviews: object) -> list[str]:
    """A pin is accepted at its birth value or at a value a review named as ``to``.

    Anything else is a blind update: the hash (or value) was pasted without the
    R-E re-read being recorded, which is exactly what the pin file exists to
    refuse.
    """
    if _same_typed(current, birth):
        return []
    if any(_same_typed(current, v) for v in reviewed_values(reviews).get(pin_name, [])):
        return []
    return [
        f"{pin_name} carries {current!r}, which is neither its birth value "
        f"{birth!r} nor the 'to' of any review entry naming it — a pin is never "
        f"updated without a review record (contract rule R-E)"
    ]


def _same_typed(a: object, b: object) -> bool:
    """Equality that also demands identical types, recursively: 1.0 != 1, True != 1."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same_typed(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same_typed(x, y) for x, y in zip(a, b))
    return a == b


def _config_shape(value: object) -> bool:
    """A config-value review side is a ``{present, value}`` dict with a bool ``present``."""
    return isinstance(value, dict) and set(value) == {"present", "value"} and isinstance(value["present"], bool)


def birth_block(pins: dict) -> list[list]:
    """Every pin's name and birth value, sorted by name: the thing the digest freezes."""
    rows: list[list] = []
    for entry in pins["functions"]:
        rows.append([f"{entry['file']}:{entry['name']}", entry["birth_sha256"]])
    for entry in pins["constants"]:
        rows.append([f"{entry['file']}:{entry['name']}", entry["birth_sha256"]])
    for entry in pins["config_values"]:
        rows.append([
            f"config.yml:{'.'.join(entry['key'])}",
            {"present": entry["birth_present"], "value": entry["birth_value"]},
        ])
    rows.sort(key=lambda row: row[0])
    return rows


def birth_block_digest(pins: dict) -> str:
    """sha256 of the canonical JSON of ``birth_block`` (types are visible: 1.0, 1 and true differ)."""
    canonical = json.dumps(birth_block(pins), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def births(pins: dict) -> dict[str, object]:
    """Pin name -> birth value."""
    return {name: value for name, value in birth_block(pins)}


# Frozen. Keyed by ``pin_commit``: the births of every pin at the commit the
# mapping was pinned against. A birth may change only together with a new
# ``pin_commit`` in the pins file AND a new row here, so "paste birth_sha256 too"
# (review r1 B1) fails the same way a bare paste does.
BIRTH_BLOCK_DIGESTS: dict[str, str] = {
    "698f58a0c74beff717cd6b69bb728fd7e21581f2": "7fd568a3865d7c3622dc08254d4262ccbe91c763fb06c71aac85c87456e431bd",
}


def review_chain_problems(reviews: object, birth_values: dict[str, object]) -> list[str]:
    """Walk ``reviews`` in order; each entry's ``from`` must be the pin's birth value or an earlier entry's ``to``.

    Unknown pins, malformed entries and non-dict reviews are left to
    ``review_problems``; this function judges only the chain. The chain is
    seeded with the CURRENT births only, so a new ``pin_commit`` starts an
    empty ``reviews`` list by design: entries written against an earlier
    pin_commit's births are refused, and the earlier reviews remain in
    version history.
    """
    if not isinstance(reviews, list):
        return ["reviews is not a list"]
    problems: list[str] = []
    seen: dict[str, list] = {name: [value] for name, value in birth_values.items()}
    for i, review in enumerate(reviews):
        if not isinstance(review, dict):
            continue
        for entry in review.get("changed") or []:
            if not isinstance(entry, dict) or not isinstance(entry.get("pin"), str):
                continue
            if "from" not in entry or "to" not in entry:
                continue
            known = seen.get(entry["pin"])
            if known is None:
                continue
            if not any(_same_typed(entry["from"], v) for v in known):
                problems.append(
                    f"reviews[{i}] {entry['pin']!r} 'from' {entry['from']!r} is neither the birth value "
                    f"nor an earlier review's 'to' for that pin"
                )
            known.append(entry["to"])
    return problems


# --- P1 ----------------------------------------------------------------------


def test_schema_and_mapping_link():
    pins = _load_pins()
    mapping = _load_mapping()
    assert pins["schema"] == "regime_outlook_rule_pins.v1"
    assert pins["mapping_version"] == mapping["mapping_version"]
    assert pins["pin_commit"] == mapping["producer_pin"]


# --- P2 / P3 -----------------------------------------------------------------


def _pin_names_for_functions(pins: dict) -> Iterable[tuple[str, dict]]:
    for entry in pins["functions"]:
        yield entry["name"], entry


@pytest.mark.parametrize(
    "entry",
    _load_pins()["functions"],
    ids=lambda e: f"{e['file']}:{e['name']}",
)
def test_function_pin_matches_source(entry):
    pins = _load_pins()
    file = entry["file"]
    name = entry["name"]
    actual = node_sha256(REPO_ROOT / file, name, "function")
    assert actual == entry["sha256"], (
        f"{file}:{name} changed since the pin. Re-read the rows it decides "
        f"({', '.join(entry['decides'])}) under contract rule R-E and record "
        f"the review in the pin file's reviews list. Never paste a new hash "
        f"without a review entry."
    )
    assert acceptance_problems(f"{file}:{name}", entry["sha256"], entry["birth_sha256"], pins["reviews"]) == []


@pytest.mark.parametrize(
    "entry",
    _load_pins()["constants"],
    ids=lambda e: f"{e['file']}:{e['name']}",
)
def test_constant_pin_matches_source(entry):
    pins = _load_pins()
    file = entry["file"]
    name = entry["name"]
    actual = node_sha256(REPO_ROOT / file, name, "constant")
    assert actual == entry["sha256"], (
        f"{file}:{name} changed since the pin. Re-read the rows it decides "
        f"({', '.join(entry['decides'])}) under contract rule R-E and record "
        f"the review in the pin file's reviews list. Never paste a new hash "
        f"without a review entry."
    )
    assert acceptance_problems(f"{file}:{name}", entry["sha256"], entry["birth_sha256"], pins["reviews"]) == []


# --- P4 ----------------------------------------------------------------------


def _dotted(entry: dict) -> str:
    return ".".join(entry["key"])


@pytest.mark.parametrize(
    "entry",
    _load_pins()["config_values"],
    ids=_dotted,
)
def test_config_value_pin_matches(entry):
    file = entry["file"]
    dotted = _dotted(entry)
    assert file == "config.yml", (
        f"config value pin {dotted} must read config.yml, not {file!r}: a pin "
        f"pointed at another file is a blind update."
    )
    raw = CONFIG_YML_PATH.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    present, value = config_value(doc, entry["key"])
    assert present == entry["present"], (
        f"config value {dotted} changed since the pin. Re-read the rows it "
        f"decides ({', '.join(entry['decides'])}) under contract rule R-E and "
        f"record the review in the pin file's reviews list. Never paste a "
        f"new value without a review entry."
    )
    if entry["present"]:
        assert value == entry["value"] and type(value) is type(entry["value"]), (
            f"config value {dotted} changed since the pin. Re-read the rows "
            f"it decides ({', '.join(entry['decides'])}) under contract rule "
            f"R-E and record the review in the pin file's reviews list. Never "
            f"paste a new value without a review entry."
        )
    assert acceptance_problems(
        f"config.yml:{'.'.join(entry['key'])}",
        {"present": entry["present"], "value": entry["value"]},
        {"present": entry["birth_present"], "value": entry["birth_value"]},
        _load_pins()["reviews"],
    ) == []


# --- P5 ----------------------------------------------------------------------


def _all_decides(pins: dict) -> set[str]:
    out: set[str] = set()
    for section in ("functions", "constants", "config_values"):
        for entry in pins[section]:
            for row in entry["decides"]:
                out.add(row)
    return out


def test_decides_are_field_ids():
    pins = _load_pins()
    mapping = _load_mapping()
    field_ids = {f["field_id"] for f in mapping["fields"]}
    decided = _all_decides(pins)
    assert decided.issubset(field_ids), (
        f"decides entries not present as mapping field_id: "
        f"{sorted(decided - field_ids)}"
    )
    functions_decided = set()
    for entry in pins["functions"]:
        for row in entry["decides"]:
            functions_decided.add(row)
    missing = field_ids - functions_decided
    assert not missing, f"mapping field_id not decided by any function: {sorted(missing)}"


# --- P6 ----------------------------------------------------------------------


def _all_pin_names(pins: dict) -> set[str]:
    names: set[str] = set()
    for entry in pins["functions"]:
        names.add(f"{entry['file']}:{entry['name']}")
    for entry in pins["constants"]:
        names.add(f"{entry['file']}:{entry['name']}")
    for entry in pins["config_values"]:
        names.add(f"config.yml:{'.'.join(entry['key'])}")
    return names


def test_review_problems_synthetic():
    pins = _load_pins()
    pin_names = _all_pin_names(pins)
    sample_pin = next(n for n in sorted(pin_names) if not n.startswith("config.yml:"))
    sha_a = "a" * 64
    sha_b = "b" * 64

    valid = {
        "date": "2026-10-03",
        "reviewer": "qa",
        "finding": "ok",
        "changed": [{"pin": sample_pin, "from": sha_a, "to": sha_b}],
    }
    assert review_problems(valid, pin_names) == []

    no_finding = {**valid, "finding": ""}
    assert any("finding" in p for p in review_problems(no_finding, pin_names))

    empty_changed = {**valid, "changed": []}
    assert any("changed" in p for p in review_problems(empty_changed, pin_names))

    unknown_pin = {**valid, "changed": [{"pin": "nonexistent:ghost", "from": sha_a, "to": sha_b}]}
    assert any("not a known pin" in p for p in review_problems(unknown_pin, pin_names))

    bare_name = {**valid, "changed": [sample_pin]}
    assert any("not a dict" in p for p in review_problems(bare_name, pin_names))

    no_to = {**valid, "changed": [{"pin": sample_pin, "from": sha_a}]}
    assert any("has no 'to'" in p for p in review_problems(no_to, pin_names))

    not_sha = {**valid, "changed": [{"pin": sample_pin, "from": sha_a, "to": "new"}]}
    assert any("not a sha256" in p for p in review_problems(not_sha, pin_names))

    no_change = {**valid, "changed": [{"pin": sample_pin, "from": sha_a, "to": sha_a}]}
    assert any("records no change" in p for p in review_problems(no_change, pin_names))

    bad_type = "not a dict"
    assert any("not a dict" in p for p in review_problems(bad_type, pin_names))


def test_blind_update_is_refused_until_reviewed():
    """Pasting a new hash without a review entry fails; the review naming it passes."""
    pins = _load_pins()
    entry = pins["functions"][0]
    pin_name = f"{entry['file']}:{entry['name']}"
    birth = entry["birth_sha256"]
    moved = "0" * 64

    assert acceptance_problems(pin_name, birth, birth, pins["reviews"]) == []
    assert acceptance_problems(pin_name, moved, birth, []) != []
    assert acceptance_problems(pin_name, moved, birth, "not a list") != []

    review = {
        "date": "2026-10-04",
        "reviewer": "qa",
        "finding": "re-read under R-E",
        "changed": [{"pin": pin_name, "from": birth, "to": moved}],
    }
    assert review_problems(review, _all_pin_names(pins)) == []
    assert acceptance_problems(pin_name, moved, birth, [review]) == []
    # a review naming a DIFFERENT pin does not excuse this one
    other = {**review, "changed": [{"pin": f"{pins['functions'][1]['file']}:{pins['functions'][1]['name']}", "from": birth, "to": moved}]}
    assert acceptance_problems(pin_name, moved, birth, [other]) != []


def test_birth_values_are_well_formed():
    pins = _load_pins()
    for group in ("functions", "constants"):
        for entry in pins[group]:
            assert _SHA_RE.match(entry["birth_sha256"]), f"{group}:{entry['name']} birth_sha256 malformed"
    for entry in pins["config_values"]:
        assert "birth_present" in entry and "birth_value" in entry, f"config pin {entry['key']} lacks birth values"
        assert isinstance(entry["birth_present"], bool)


def test_birth_block_is_frozen_by_digest():
    """Review r1 B1: pasting birth_sha256 along with sha256 passes acceptance_problems alone;
    the frozen digest is what refuses it. A birth moves only with a new pin_commit + digest row."""
    pins = _load_pins()
    assert pins["pin_commit"] in BIRTH_BLOCK_DIGESTS, "a new pin_commit needs a reviewed digest row in this module"
    assert birth_block_digest(pins) == BIRTH_BLOCK_DIGESTS[pins["pin_commit"]]

    forged = json.loads(json.dumps(pins))
    entry = forged["functions"][0]
    entry["sha256"] = entry["birth_sha256"] = "0" * 64
    # the hole: acceptance alone cannot see a double paste ...
    assert acceptance_problems(f"{entry['file']}:{entry['name']}", "0" * 64, "0" * 64, []) == []
    # ... the digest can.
    assert birth_block_digest(forged) != BIRTH_BLOCK_DIGESTS[pins["pin_commit"]]

    forged_cfg = json.loads(json.dumps(pins))
    cfg = forged_cfg["config_values"][0]
    cfg["value"] = cfg["birth_value"] = "pasted"
    assert birth_block_digest(forged_cfg) != BIRTH_BLOCK_DIGESTS[pins["pin_commit"]]

    # types are part of the digest: 1.0 -> 1 is a move
    forged_type = json.loads(json.dumps(pins))
    numeric = next(e for e in forged_type["config_values"] if isinstance(e["birth_value"], float))
    numeric["birth_value"] = int(numeric["birth_value"])
    assert birth_block_digest(forged_type) != BIRTH_BLOCK_DIGESTS[pins["pin_commit"]]


def test_config_acceptance_is_type_strict():
    """Review r1 S2: the source check is type-strict, so acceptance is too (1.0, 1 and True differ)."""
    birth = {"present": True, "value": 1.0}
    assert acceptance_problems("config.yml:x", {"present": True, "value": 1.0}, birth, []) == []
    assert acceptance_problems("config.yml:x", {"present": True, "value": 1}, birth, []) != []
    assert acceptance_problems("config.yml:x", {"present": True, "value": True}, birth, []) != []
    assert acceptance_problems(
        "config.yml:x", {"present": True, "value": [1, 3]}, {"present": True, "value": [1.0, 3.0]}, []
    ) != []
    review = {
        "date": "2026-10-04", "reviewer": "qa", "finding": "re-read",
        "changed": [{"pin": "config.yml:x", "from": birth, "to": {"present": True, "value": 1}}],
    }
    assert acceptance_problems("config.yml:x", {"present": True, "value": 1}, birth, [review]) == []
    # a reviewed 'to' is also matched type-strictly
    assert acceptance_problems("config.yml:x", {"present": True, "value": 1.0}, {"present": True, "value": 2.0}, [review]) != []


def test_review_entry_shapes_and_chain():
    """Review r1 M1 / N1 / S1: config sides are {present, value} dicts; a non-string pin is a
    sentence, not a TypeError; a 'from' must be the birth value or an earlier 'to'."""
    pins = _load_pins()
    pin_names = _all_pin_names(pins)
    cfg_pin = next(n for n in sorted(pin_names) if n.startswith("config.yml:"))
    src_pin = next(n for n in sorted(pin_names) if not n.startswith("config.yml:"))
    base = {"date": "2026-10-04", "reviewer": "qa", "finding": "re-read"}

    bare_values = {**base, "changed": [{"pin": cfg_pin, "from": 1.0, "to": 2.0}]}
    assert any("not a {present, value} dict" in p for p in review_problems(bare_values, pin_names))
    shaped = {**base, "changed": [{"pin": cfg_pin, "from": {"present": True, "value": 1.0}, "to": {"present": True, "value": 2.0}}]}
    assert review_problems(shaped, pin_names) == []
    bad_present = {**base, "changed": [{"pin": cfg_pin, "from": {"present": 1, "value": 1.0}, "to": {"present": True, "value": 2.0}}]}
    assert any("not a {present, value} dict" in p for p in review_problems(bad_present, pin_names))

    list_pin = {**base, "changed": [{"pin": ["x"], "from": "a" * 64, "to": "b" * 64}]}
    assert any("is not a string" in p for p in review_problems(list_pin, pin_names))
    assert reviewed_values([list_pin]) == {}

    birth_values = {src_pin: "a" * 64, cfg_pin: {"present": True, "value": 1.0}}
    ok_chain = [
        {**base, "changed": [{"pin": src_pin, "from": "a" * 64, "to": "b" * 64}]},
        {**base, "changed": [{"pin": src_pin, "from": "b" * 64, "to": "c" * 64}]},
        {**base, "changed": [{"pin": src_pin, "from": "a" * 64, "to": "d" * 64}]},  # an earlier value is allowed
    ]
    assert review_chain_problems(ok_chain, birth_values) == []
    forged_from = [{**base, "changed": [{"pin": src_pin, "from": "f" * 64, "to": "0" * 64}]}]
    assert review_chain_problems(forged_from, birth_values) != []
    typed_from = [{**base, "changed": [{"pin": cfg_pin, "from": {"present": True, "value": 1}, "to": {"present": True, "value": 2.0}}]}]
    assert review_chain_problems(typed_from, birth_values) != []
    assert review_chain_problems("not a list", birth_values) == ["reviews is not a list"]


def test_real_reviews_are_well_formed():
    pins = _load_pins()
    pin_names = _all_pin_names(pins)
    for i, review in enumerate(pins["reviews"]):
        problems = review_problems(review, pin_names)
        assert not problems, f"reviews[{i}] problems: {problems}"
    assert review_chain_problems(pins["reviews"], births(pins)) == []


# --- P7 ----------------------------------------------------------------------


def test_no_duplicate_pins():
    pins = _load_pins()
    func_keys = [(e["file"], e["name"]) for e in pins["functions"]]
    const_keys = [(e["file"], e["name"]) for e in pins["constants"]]
    cfg_keys = [tuple(e["key"]) for e in pins["config_values"]]
    assert len(set(func_keys)) == len(func_keys), "duplicate function pins"
    assert len(set(const_keys)) == len(const_keys), "duplicate constant pins"
    assert len(set(cfg_keys)) == len(cfg_keys), "duplicate config value pins"


# --- P8 ----------------------------------------------------------------------


def test_helper_detects_change_only(tmp_path):
    pins = _load_pins()
    src = REPO_ROOT / "engine" / "fed_path.py"
    original = src.read_text(encoding="utf-8")
    try:
        # (a) constant text change -> hash changes
        changed = original.replace("_QUARTER = 0.25", "_QUARTER = 0.50", 1)
        copy_a = tmp_path / "fed_path_a.py"
        copy_a.write_text(changed, encoding="utf-8")
        pin = next(e for e in pins["constants"] if e["name"] == "_QUARTER")
        new_hash = node_sha256(copy_a, "_QUARTER", "constant")
        assert new_hash != pin["sha256"]

        # (b) comment at the top of a fresh copy -> function hash unchanged
        commented = "# note\n" + original
        copy_b = tmp_path / "fed_path_b.py"
        copy_b.write_text(commented, encoding="utf-8")
        pin_compute = next(e for e in pins["functions"] if e["name"] == "compute")
        assert node_sha256(copy_b, "compute", "function") == pin_compute["sha256"]

        # (c) a second top-level def with the same name -> raises
        doubled = original + "\n\ndef compute():\n    pass\n"
        copy_c = tmp_path / "fed_path_c.py"
        copy_c.write_text(doubled, encoding="utf-8")
        with pytest.raises(AssertionError):
            node_sha256(copy_c, "compute", "function")
    finally:
        # nothing to restore — we wrote copies under tmp_path; src was never modified.
        del original


# --- P9 ----------------------------------------------------------------------


def test_no_engine_import():
    src = Path(__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.lstrip()
        assert not re.match(r"^(from|import)\s+engine\b", stripped), (
            f"this test must not import engine: {line!r}"
        )