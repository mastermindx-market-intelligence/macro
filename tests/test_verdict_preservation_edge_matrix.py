"""Edge-matrix characterization of engine/verdict_preservation.py (v-registry-matrix).

Boundary matrix for the display-tier preserved-verdict registry: row validation
edges, registry-level validation edges, pin-anchor edge behavior, and the
build() failure/success shapes. Every case pins behavior OBSERVED on the
accepted V1 base; the two known-defect gaps (non-UTF-8 bytes raising instead of
failing closed) are pinned as strict xfails naming the engine lines.

Hermetic: fixtures live under tmp_path only; the single real-repo touch is the
read-only smoke test. No network, no wall-clock, no randomness.
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engine import verdict_preservation as vp

REGISTRY_PATH = REPO / "config" / "verdict_preservation_registry.json"
LOGGER_NAME = "engine.verdict_preservation"

VALID_ROW = {
    "id": "edge-row",
    "verdict_key": "X1",
    "program": "edge program",
    "status_literal": "NOT SUPPORTED",
    "status_class": "not_supported",
    "actual": True,
    "source_path": "research/edge.md",
    "source_line": 3,
    "qualifiers_en": "edge qualifier",
    "qualifiers_zh": "边界条件",
    "plain_en": "watch, don't chase",
    "plain_zh": "观察，不要追。",
    "owner_ref": "WS:KEY",
    "consume_as": "display-tier",
}

PIN_FILE_LINES = ("alpha literal one", "plain two", "final literal three")


# ---------------------------------------------------------------------------
# fixtures / fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture()
def pin_root(tmp_path: Path) -> Path:
    """A tmp root holding research/pin.md with the 3 known PIN_FILE_LINES."""
    target = tmp_path / "research" / "pin.md"
    target.parent.mkdir(parents=True)
    target.write_text("\n".join(PIN_FILE_LINES) + "\n", encoding="utf-8")
    return tmp_path


def _write_registry_fixture(tmp_path: Path, mutator=None) -> dict:
    """Write a valid tmp registry built from module constants + the real 8 rows.

    Deep-copies the real registry rows, rewrites every pin to a tmp source file
    (literal on line 2 of a 3-line file), and writes the JSON under
    tmp_path/config/. Returns the (possibly mutated) data dict.
    """
    data = copy.deepcopy(json.loads(REGISTRY_PATH.read_text(encoding="utf-8")))
    data["schema"] = vp._SCHEMA
    data["do_not_consume_until_repair"] = list(vp._DNC_EN)
    data["do_not_consume_until_repair_zh"] = list(vp._DNC_ZH)
    for i, row in enumerate(data["rows"]):
        rel = f"research/src_{i}.md"
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        literal = f"EDGE-LITERAL-{i}"
        target.write_text(f"header line\n{literal}\ntrailer line\n", encoding="utf-8")
        row["source_path"] = rel
        row["source_line"] = 2
        row["status_literal"] = literal
    if mutator is not None:
        mutator(data)
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "verdict_preservation_registry.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    return data


# ---------------------------------------------------------------------------
# group 1: _validate_row edges
# ---------------------------------------------------------------------------


def _row_cases():
    cases = []
    for key in vp._ROW_KEYS:
        row = dict(VALID_ROW)
        del row[key]
        cases.append(pytest.param(row, False, id=f"missing-{key}"))

    def mutated(**overrides):
        row = dict(VALID_ROW)
        row.update(overrides)
        return row

    cases.extend(
        [
            pytest.param(["not", "a", "dict"], False, id="non-dict-list"),
            pytest.param("not-a-dict", False, id="non-dict-str"),
            pytest.param(None, False, id="non-dict-none"),
            pytest.param(mutated(id=""), False, id="id-empty-string"),
            pytest.param(mutated(id=7), False, id="id-not-a-str"),
            pytest.param(mutated(verdict_key=5), False, id="verdict-key-int"),
            pytest.param(mutated(program=5), False, id="program-int"),
            pytest.param(mutated(status_literal=5), False, id="status-literal-int"),
            pytest.param(mutated(status_class="verdict"), False, id="status-class-verdict"),
            pytest.param(mutated(status_class="LAW"), False, id="status-class-LAW"),
            pytest.param(mutated(actual=1), False, id="actual-int-1"),
            pytest.param(mutated(actual="true"), False, id="actual-str-true"),
            pytest.param(mutated(source_path=None), False, id="source-path-none"),
            pytest.param(mutated(source_line=0), False, id="source-line-zero"),
            pytest.param(mutated(source_line=-1), False, id="source-line-negative"),
            pytest.param(mutated(source_line=3.0), False, id="source-line-float"),
            pytest.param(mutated(source_line="3"), False, id="source-line-str"),
            pytest.param(mutated(consume_as="authority"), False, id="consume-as-authority"),
            pytest.param(dict(VALID_ROW), True, id="fully-valid"),
        ]
    )
    return cases


@pytest.mark.parametrize(("row", "expected"), _row_cases())
def test_validate_row_edges(row, expected):
    assert vp._validate_row(row) is expected


# ---------------------------------------------------------------------------
# group 2: _OWNER_REF_RE boundaries via _validate_row
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("owner_ref", "expected"),
    [
        pytest.param("WS:KEY", True, id="valid-ws"),
        pytest.param("DEC:A-B-1", True, id="valid-dec"),
        pytest.param("DSC:X", True, id="valid-dsc"),
        pytest.param("DNR:KILL-X", True, id="valid-dnr"),
        pytest.param("ws:KEY", False, id="lowercase-prefix"),
        pytest.param("WS:key", False, id="lowercase-key"),
        pytest.param("WSKEY", False, id="missing-colon"),
        pytest.param("WS:-KEY", False, id="leading-hyphen-key"),
        pytest.param("WS:", False, id="empty-key"),
        pytest.param("LAW:KEY", False, id="other-prefix-law"),
        pytest.param("KILL:KEY", False, id="other-prefix-kill"),
        pytest.param(" WS:KEY", False, id="leading-space"),
        pytest.param("WS:KEY ", False, id="trailing-space"),
        pytest.param("WS:KEY\n", False, id="trailing-newline"),
    ],
)
def test_owner_ref_boundaries(owner_ref, expected):
    row = dict(VALID_ROW)
    row["owner_ref"] = owner_ref
    assert vp._validate_row(row) is expected


# ---------------------------------------------------------------------------
# group 3: _validate_registry edges (synthetic 8-row registry, no disk)
# ---------------------------------------------------------------------------


def _synthetic_registry() -> dict:
    rows = []
    for i in range(8):
        row = dict(VALID_ROW)
        row["id"] = f"synth-{i}"
        row["verdict_key"] = "C2" if i == 0 else f"K{i}"
        row["actual"] = i == 0
        rows.append(row)
    return {
        "schema": vp._SCHEMA,
        "frozen_at": "2026-01-01",
        "source_census": "synthetic-census.md",
        "rows": rows,
        "do_not_consume_until_repair": list(vp._DNC_EN),
        "do_not_consume_until_repair_zh": list(vp._DNC_ZH),
    }


def _registry_cases():
    def base():
        return copy.deepcopy(_synthetic_registry())

    def wrong_schema():
        d = base()
        d["schema"] = "mastermind.verdict_preservation.registry.v2"
        return d

    def schema_missing():
        d = base()
        del d["schema"]
        return d

    def rows_missing():
        d = base()
        del d["rows"]
        return d

    def rows_not_a_list():
        d = base()
        d["rows"] = {"0": dict(VALID_ROW)}
        return d

    def rows_empty():
        d = base()
        d["rows"] = []
        return d

    def rows_of_seven():
        d = base()
        d["rows"] = d["rows"][:7]
        return d

    def rows_of_nine():
        d = base()
        extra = dict(VALID_ROW)
        extra["id"] = "extra-8"
        extra["verdict_key"] = "X8"
        extra["actual"] = False
        d["rows"].append(extra)
        return d

    def one_bad_row():
        d = base()
        d["rows"][3]["consume_as"] = "authority"
        return d

    def duplicate_id():
        d = base()
        d["rows"][5]["id"] = d["rows"][0]["id"]
        return d

    def zero_c2_actual():
        d = base()
        d["rows"][0]["verdict_key"] = "C9"
        return d

    def two_c2_actual():
        d = base()
        d["rows"][1]["verdict_key"] = "C2"
        d["rows"][1]["actual"] = True
        return d

    def dnc_en_reordered():
        d = base()
        d["do_not_consume_until_repair"] = list(reversed(vp._DNC_EN))
        return d

    def dnc_zh_missing():
        d = base()
        del d["do_not_consume_until_repair_zh"]
        return d

    def frozen_at_int():
        d = base()
        d["frozen_at"] = 2026
        return d

    def source_census_missing():
        d = base()
        del d["source_census"]
        return d

    return [
        pytest.param(lambda: [], False, id="non-dict-list"),
        pytest.param(lambda: None, False, id="non-dict-none"),
        pytest.param(wrong_schema, False, id="wrong-schema"),
        pytest.param(schema_missing, False, id="schema-missing"),
        pytest.param(rows_missing, False, id="rows-missing"),
        pytest.param(rows_not_a_list, False, id="rows-not-a-list"),
        pytest.param(rows_empty, False, id="rows-empty"),
        pytest.param(rows_of_seven, False, id="rows-of-7"),
        pytest.param(rows_of_nine, False, id="rows-of-9"),
        pytest.param(one_bad_row, False, id="one-bad-row-poisons-registry"),
        pytest.param(duplicate_id, False, id="duplicate-id"),
        pytest.param(zero_c2_actual, False, id="zero-c2-actual-true"),
        pytest.param(two_c2_actual, False, id="two-c2-actual-true"),
        pytest.param(dnc_en_reordered, False, id="dnc-en-reordered"),
        pytest.param(dnc_zh_missing, False, id="dnc-zh-missing"),
        pytest.param(frozen_at_int, False, id="frozen-at-int"),
        pytest.param(source_census_missing, False, id="source-census-missing"),
        pytest.param(base, True, id="valid-registry"),
    ]


@pytest.mark.parametrize(("make_data", "expected"), _registry_cases())
def test_validate_registry_edges(make_data, expected):
    assert vp._validate_registry(make_data()) is expected


# ---------------------------------------------------------------------------
# group 4: _pin_ok edges against a 3-line tmp file
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source_path", "source_line", "literal", "expected"),
    [
        pytest.param("research/pin.md", 0, "alpha", False, id="line-zero"),
        pytest.param("research/pin.md", -1, "alpha", False, id="line-negative"),
        pytest.param("research/pin.md", 4, "final", False, id="line-past-eof"),
        pytest.param("research/pin.md", 3, "final literal three", True, id="line-last-line"),
        pytest.param("research/pin.md", 2, "alpha", False, id="literal-on-adjacent-line"),
        pytest.param("research/pin.md", 1, "literal", True, id="literal-substring-of-longer-line"),
        pytest.param("research/missing.md", 1, "alpha", False, id="missing-file"),
        pytest.param("research", 1, "alpha", False, id="directory-as-path"),
        pytest.param("/etc/hosts", 1, "root", False, id="absolute-path"),
        pytest.param("../outside.md", 1, "alpha", False, id="parent-traversal"),
        pytest.param("a/../research/pin.md", 2, "plain", False, id="internal-dotdot-stays-in-root"),
    ],
)
def test_pin_ok_edges(pin_root, source_path, source_line, literal, expected):
    assert vp._pin_ok(pin_root, source_path, source_line, literal) is expected


def test_pin_ok_symlink_escaping_root_is_false(tmp_path: Path):
    root = tmp_path / "root"
    (root / "research").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("secret literal\n", encoding="utf-8")
    (root / "research" / "link.md").symlink_to(outside)
    assert vp._pin_ok(root, "research/link.md", 1, "secret literal") is False


def test_pin_ok_symlink_inside_root_pins(tmp_path: Path):
    root = tmp_path / "root"
    (root / "research").mkdir(parents=True)
    real = root / "research" / "real.md"
    real.write_text("inner literal\n", encoding="utf-8")
    (root / "research" / "link.md").symlink_to(real)
    assert vp._pin_ok(root, "research/link.md", 1, "inner literal") is True


# ---------------------------------------------------------------------------
# group 5: candidate gaps, pinned as observed (G-a/G-b/G-c/G-f/G-i/G-j)
# ---------------------------------------------------------------------------


def test_gap_ga_source_line_true_passes_validation():
    # bool is an int subclass: True clears the isinstance(int) gate and >= 1.
    row = dict(VALID_ROW)
    row["source_line"] = True
    assert vp._validate_row(row) is True


def test_gap_ga_source_line_true_pins_line_one(pin_root):
    # True behaves as the int 1 downstream, so it pins line 1.
    assert vp._pin_ok(pin_root, "research/pin.md", True, "alpha literal one") is True


def test_gap_gb_empty_literal_pins_any_existing_line(pin_root):
    assert vp._pin_ok(pin_root, "research/pin.md", 2, "") is True
    assert vp._pin_ok(pin_root, "research/pin.md", 3, "") is True


def test_gap_gc_dotdot_substring_refuses_legit_name(tmp_path: Path):
    # Fail-closed: ".." is substring-matched, so a legitimate in-root filename
    # containing a double dot is refused even though it resolves inside root.
    (tmp_path / "notes..v2.md").write_text("legit literal\n", encoding="utf-8")
    assert vp._pin_ok(tmp_path, "notes..v2.md", 1, "legit literal") is False


def test_gap_gf_splitlines_splits_on_form_feed(tmp_path: Path):
    target = tmp_path / "research" / "ff.md"
    target.parent.mkdir(parents=True)
    target.write_text("one\ntwo\nthree\x0cfour", encoding="utf-8")
    # Only 3 newlines, but splitlines counts 4 lines: the form feed shifts
    # line numbers relative to a newline-only count.
    assert vp._pin_ok(tmp_path, "research/ff.md", 4, "four") is True
    assert vp._pin_ok(tmp_path, "research/ff.md", 3, "three") is True


def test_gap_gf_splitlines_splits_on_unicode_separator(tmp_path: Path):
    target = tmp_path / "research" / "ls.md"
    target.parent.mkdir(parents=True)
    target.write_text("one\ntwo\u2028three", encoding="utf-8")
    assert vp._pin_ok(tmp_path, "research/ls.md", 3, "three") is True


def test_gap_gj_empty_strings_accepted_by_validate_row():
    row = dict(VALID_ROW)
    row["verdict_key"] = ""
    row["program"] = ""
    row["status_literal"] = ""
    assert vp._validate_row(row) is True


def test_gap_gi_unknown_row_keys_pass_through(tmp_path: Path):
    def add_extra_key(data):
        data["rows"][2]["future_field"] = 12345

    _write_registry_fixture(tmp_path, mutator=add_extra_key)
    built = vp.build_verdict_preservation(tmp_path)
    assert built["available"] is True
    assert built["rows"][2]["future_field"] == 12345
    assert built["pin_ok_count"] == 8


# ---------------------------------------------------------------------------
# group 6: known-defect gaps, strict xfails (G-d/G-e: non-UTF-8 raises)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="GAP: engine/verdict_preservation.py:144-146 _pin_ok catches only OSError; "
    "UnicodeDecodeError (a ValueError) escapes, so one non-UTF-8 source file "
    "raises out of build_verdict_preservation instead of yielding pin_ok False",
)
def test_gap_gd_non_utf8_source_should_pin_false(tmp_path: Path):
    data = _write_registry_fixture(tmp_path)
    bad = tmp_path / data["rows"][5]["source_path"]
    bad.write_bytes(b"\xff\xfe bad bytes")
    built = vp.build_verdict_preservation(tmp_path)
    assert built["available"] is True
    assert built["rows"][5]["pin_ok"] is False
    assert built["pin_ok_count"] == 7


@pytest.mark.xfail(
    strict=True,
    reason="GAP: engine/verdict_preservation.py:159-161 build catches only OSError and "
    "json.JSONDecodeError; a non-UTF-8 registry raises UnicodeDecodeError instead "
    "of returning {'available': False}",
)
def test_gap_ge_non_utf8_registry_should_be_unavailable(tmp_path: Path):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "verdict_preservation_registry.json").write_bytes(b"\xff\xfe not json")
    assert vp.build_verdict_preservation(tmp_path) == {"available": False}


# ---------------------------------------------------------------------------
# group 7: build_verdict_preservation failure shapes + warning receipts
# ---------------------------------------------------------------------------


def test_unavailable_returns_exactly_one_key():
    assert vp._unavailable("edge %s", 1) == {"available": False}


def test_build_missing_registry_returns_exactly_unavailable(tmp_path: Path):
    assert vp.build_verdict_preservation(tmp_path) == {"available": False}


def test_build_malformed_json_returns_exactly_unavailable(tmp_path: Path):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "verdict_preservation_registry.json").write_text("{not json", encoding="utf-8")
    assert vp.build_verdict_preservation(tmp_path) == {"available": False}


def test_build_failing_validation_returns_exactly_unavailable(tmp_path: Path):
    def break_one_row(data):
        data["rows"][4]["consume_as"] = "authority"

    _write_registry_fixture(tmp_path, mutator=break_one_row)
    assert vp.build_verdict_preservation(tmp_path) == {"available": False}


def _module_warnings(caplog):
    return [
        r
        for r in caplog.records
        if r.name == LOGGER_NAME and r.levelno == logging.WARNING
    ]


def test_missing_registry_logs_exactly_one_warning(tmp_path: Path, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        vp.build_verdict_preservation(tmp_path)
    warnings = _module_warnings(caplog)
    assert len(warnings) == 1
    assert "not found" in warnings[0].getMessage()


def test_malformed_json_logs_exactly_one_warning(tmp_path: Path, caplog):
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)
    (cfg / "verdict_preservation_registry.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        vp.build_verdict_preservation(tmp_path)
    warnings = _module_warnings(caplog)
    assert len(warnings) == 1
    assert "unreadable" in warnings[0].getMessage()


def test_failed_validation_logs_exactly_one_warning(tmp_path: Path, caplog):
    def break_one_row(data):
        data["rows"][4]["consume_as"] = "authority"

    _write_registry_fixture(tmp_path, mutator=break_one_row)
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        vp.build_verdict_preservation(tmp_path)
    warnings = _module_warnings(caplog)
    assert len(warnings) == 1
    assert "failed validation" in warnings[0].getMessage()


# ---------------------------------------------------------------------------
# group 8: build_verdict_preservation success payload
# ---------------------------------------------------------------------------


def test_build_available_payload_shape(tmp_path: Path):
    data = _write_registry_fixture(tmp_path)
    built = vp.build_verdict_preservation(tmp_path)

    assert built["available"] is True
    assert set(built) == {
        "available",
        "schema",
        "frozen_at",
        "source_census",
        "rows",
        "do_not_consume_until_repair",
        "do_not_consume_until_repair_zh",
        "row_count",
        "pin_ok_count",
    }
    assert built["row_count"] == 8
    assert built["schema"] == vp._SCHEMA
    assert built["frozen_at"] == data["frozen_at"]
    assert built["source_census"] == data["source_census"]
    assert len(built["rows"]) == 8

    by_id = {row["id"]: row for row in data["rows"]}
    for out_row in built["rows"]:
        src = by_id[out_row["id"]]
        # output row = {**registry_row, pin_ok, anchor, badge_en, badge_zh}
        assert set(out_row) == set(src) | {"pin_ok", "anchor", "badge_en", "badge_zh"}
        assert out_row["anchor"] == "vp-" + out_row["id"]
        assert out_row["pin_ok"] is True
        badge_en, badge_zh = vp._BADGE_MAP[src["status_class"]]
        assert out_row["badge_en"] == badge_en
        assert out_row["badge_zh"] == badge_zh
        assert out_row["badge_en"]
        assert out_row["badge_zh"]

    assert built["pin_ok_count"] == 8
    assert built["pin_ok_count"] == sum(1 for r in built["rows"] if r["pin_ok"] is True)


def test_build_single_drifted_pin_stays_available(tmp_path: Path):
    data = _write_registry_fixture(tmp_path)
    drifted = data["rows"][3]
    (tmp_path / drifted["source_path"]).write_text(
        "header line\nliteral is absent\ntrailer line\n", encoding="utf-8"
    )
    built = vp.build_verdict_preservation(tmp_path)
    assert built["available"] is True
    assert built["rows"][3]["pin_ok"] is False
    assert built["row_count"] == 8
    assert built["pin_ok_count"] == 7


def test_build_dnc_lists_are_defensive_copies(tmp_path: Path):
    _write_registry_fixture(tmp_path)
    built = vp.build_verdict_preservation(tmp_path)
    assert built["do_not_consume_until_repair"] == vp._DNC_EN
    assert built["do_not_consume_until_repair_zh"] == vp._DNC_ZH
    assert built["do_not_consume_until_repair"] is not vp._DNC_EN
    assert built["do_not_consume_until_repair_zh"] is not vp._DNC_ZH

    snapshot_en = list(vp._DNC_EN)
    snapshot_zh = list(vp._DNC_ZH)
    built["do_not_consume_until_repair"].append("mutated-en")
    built["do_not_consume_until_repair_zh"].append("mutated-zh")
    assert vp._DNC_EN == snapshot_en
    assert vp._DNC_ZH == snapshot_zh


# ---------------------------------------------------------------------------
# group 9: read-only real-repo smoke test
# ---------------------------------------------------------------------------


def test_real_repo_smoke():
    built = vp.build_verdict_preservation(REPO)
    assert built["available"] is True
    assert built["row_count"] == 8
    assert built["pin_ok_count"] == 8
    assert built["pin_ok_count"] == sum(1 for r in built["rows"] if r["pin_ok"] is True)
