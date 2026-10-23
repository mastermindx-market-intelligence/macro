"""Pin invariants of the A8 US residual-transfer pre-registration DRAFT.

Each test reads only the four owned files and tmp_path, except the
GRADE_HORIZONS observation which reads engine/qledger.py as text (no import).
This test consumes the draft documents. It does not mint identity ids, does
not load outcomes, and does not register or seal. All authority flags stay
false; a caller that sets any of them true is refused (raise).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OWNED_DIR = ROOT / "research" / "single_name_intelligence" / "us_transfer"
JSON_PATH = OWNED_DIR / "A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.json"
MD_PATH = OWNED_DIR / "A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.md"
LOADER_PATH = OWNED_DIR / "a8_draft_loader.py"

if str(OWNED_DIR) not in sys.path:
    sys.path.insert(0, str(OWNED_DIR))

import a8_draft_loader as draft_loader  # noqa: E402

FAMILY_ID = "sni.us_transfer.RESID-DIR-US"
NAMES = ["AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA"]
HORIZONS = [5, 21, 63]
BUDGET = 21
THEN_KNOWN_FIELDS = ("fact", "effective_date_or_null", "source", "treatment")
IDENTITY_KEYS = frozenset({"canonical_issuer_id", "security_id"})
AUTHORITY_KEYS = frozenset(
    {
        "rank_authority",
        "gate_authority",
        "size_authority",
        "signal_authority",
        "escalation_authority",
        "trade_authority",
    }
)
BANNED_PHRASES = (
    "validated",
    "transfer shown",
    "forecast skill",
    "calibrated",
    "P07",
)
NEGATION = re.compile(
    r"\b(?:not|never|no|none|nothing|neither|nor|without)\b",
    re.IGNORECASE,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
GRADE_HORIZONS_RE = re.compile(
    r"^GRADE_HORIZONS\s*=\s*\(([^)]+)\)", re.MULTILINE
)


def _raw_draft() -> dict:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def _write_poison(tmp_path: Path, draft: dict) -> Path:
    path = tmp_path / "poison.json"
    path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    return path


def sentences_of(text: str) -> list[str]:
    parts = SENTENCE_SPLIT.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def banned_phrase_is_negated(sentence: str, phrase: str) -> bool:
    """True iff the sentence contains the phrase and also a negation token."""
    if phrase.lower() not in sentence.lower():
        return True
    return NEGATION.search(sentence) is not None


def md_banned_violations(md: str) -> list[str]:
    hits = []
    for sentence in sentences_of(md):
        for phrase in BANNED_PHRASES:
            if phrase.lower() in sentence.lower() and not banned_phrase_is_negated(
                sentence, phrase
            ):
                hits.append(f"{phrase!r} in {sentence!r}")
    return hits


def parse_md_fields(md: str) -> dict:
    def labeled(name: str) -> str:
        match = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", md)
        if match is None:
            raise AssertionError(f"markdown missing labeled field {name}")
        return match.group(1).strip()

    family_line = labeled("Family id")
    family_match = re.search(r"`([^`]+)`", family_line)
    names_line = labeled("Names")
    horizons_line = labeled("Horizons")
    budget_line = labeled("Declared budget")
    status_line = labeled("Status")
    status_match = re.search(r"`([^`]+)`", status_line)
    budget_match = re.search(r"`(\d+)`", budget_line)
    return {
        "family_id": family_match.group(1) if family_match else family_line.strip("`"),
        "names": re.findall(r"`([A-Z0-9]+)`", names_line),
        "horizons": [int(x) for x in re.findall(r"`(\d+)`", horizons_line)],
        "budget": int(budget_match.group(1)) if budget_match else int(budget_line),
        "status": status_match.group(1) if status_match else status_line.strip("`"),
    }


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_dicts(item)


def _poison_registered(draft: dict) -> dict:
    draft["registered"] = True
    return draft


def _poison_authority(draft: dict) -> dict:
    draft["cells"][0]["Signal_Authority"] = "yes"
    return draft


def _poison_identity(draft: dict) -> dict:
    draft["cells"][0]["canonical_issuer_id"] = "synthetic-opaque"
    return draft


def _poison_cohort_selection(draft: dict) -> dict:
    draft["cohort"]["selection"] = "ex-post Mag-7"
    return draft


def _poison_survivorship(draft: dict) -> dict:
    draft["cohort"]["survivorship"] = False
    return draft


def _poison_horizons(draft: dict) -> dict:
    draft["horizons"] = [5, 21]
    return draft


def _poison_cell_count(draft: dict) -> dict:
    draft["cells"] = draft["cells"][:-1]
    return draft


def _poison_then_known(draft: dict) -> dict:
    del draft["then_known"][0]["source"]
    return draft


def _poison_banned(draft: dict) -> dict:
    draft["labels"][0] = draft["labels"][0] + " calibrated"
    return draft


def _poison_unknown_key(draft: dict) -> dict:
    draft["unexpected_top_level"] = 1
    return draft


POISONS = [
    ("REGISTERED_NOT_FALSE", _poison_registered),
    ("AUTHORITY_TRUTHY", _poison_authority),
    ("IDENTITY_NON_NULL", _poison_identity),
    ("COHORT_NOT_HINDSIGHT", _poison_cohort_selection),
    ("COHORT_SURVIVORSHIP_NOT_TRUE", _poison_survivorship),
    ("HORIZONS_MISMATCH", _poison_horizons),
    ("CELL_COUNT_MISMATCH", _poison_cell_count),
    ("THEN_KNOWN_INCOMPLETE", _poison_then_known),
    ("BANNED_PHRASE", _poison_banned),
    ("UNKNOWN_TOP_LEVEL_KEY", _poison_unknown_key),
]


def test_owned_files_exist() -> None:
    assert JSON_PATH.is_file()
    assert MD_PATH.is_file()
    assert LOADER_PATH.is_file()


def test_committed_json_loads() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert loaded["family_id"] == FAMILY_ID
    assert loaded["registered"] is False
    assert loaded["status"] == "DRAFT"
    assert loaded["outcome"] == "none"
    assert loaded["version"] == "v0-draft"


def test_md_json_agree_family_names_horizons_budget_status() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    parsed = parse_md_fields(MD_PATH.read_text(encoding="utf-8"))
    assert parsed["family_id"] == loaded["family_id"] == FAMILY_ID
    assert parsed["names"] == loaded["names"] == NAMES
    assert parsed["horizons"] == loaded["horizons"] == HORIZONS
    assert parsed["budget"] == loaded["budget"]["declared_trials"] == BUDGET
    assert parsed["status"] == loaded["status"] == "DRAFT"


@pytest.mark.parametrize("code,mutator", POISONS, ids=[c for c, _ in POISONS])
def test_refusal_code_fires_on_poisoned_copy(code, mutator, tmp_path: Path) -> None:
    poisoned = mutator(deepcopy(_raw_draft()))
    path = _write_poison(tmp_path, poisoned)
    with pytest.raises(draft_loader.A8DraftRefused) as excinfo:
        draft_loader.load_draft(path)
    assert excinfo.value.code == code
    assert code in draft_loader.REFUSAL_CODES


def test_refusal_codes_are_exactly_the_ten() -> None:
    assert draft_loader.REFUSAL_CODES == frozenset(code for code, _ in POISONS)


def test_xlc_leg_window_declared_for_googl_and_meta() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    for name in ("GOOGL", "META"):
        secondary = loaded["benches"]["secondary_by_name"][name]
        assert secondary["display_label"] == "XLC"
        window = secondary["then_known_valid_window"]
        assert window["start"] == "2018-06-19"
        assert secondary["abstain_outside_window_reason"] == "bench_not_then_known"
        cells = [
            cell
            for cell in loaded["cells"]
            if cell["name"] == name
        ]
        assert cells
        for cell in cells:
            assert cell["secondary_bench"] == "XLC"
            assert cell["secondary_leg_valid_from"] == "2018-06-19"
            assert cell["secondary_leg_abstain_reason"] == "bench_not_then_known"
    md = MD_PATH.read_text(encoding="utf-8")
    assert "2018-06-19" in md
    assert "bench_not_then_known" in md
    assert re.search(r"GOOGL.*XLC|XLC.*GOOGL", md) is not None
    assert re.search(r"META.*XLC|XLC.*META", md) is not None


def test_then_known_four_fields() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert isinstance(loaded["then_known"], list)
    assert loaded["then_known"]
    for row in loaded["then_known"]:
        for field in THEN_KNOWN_FIELDS:
            assert field in row
        assert set(THEN_KNOWN_FIELDS) <= set(row.keys())


def test_no_id_field_non_null_recursive() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)

    def walk(obj, path: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                norm = key.strip().lower().replace("-", "_")
                if norm in IDENTITY_KEYS:
                    assert value is None, f"{path}.{key}={value!r}"
                walk(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                walk(item, f"{path}[{index}]")

    walk(loaded, "$")


def test_horizons_equal_grade_horizons() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    qledger = (ROOT / "engine" / "qledger.py").read_text(encoding="utf-8")
    match = GRADE_HORIZONS_RE.search(qledger)
    assert match is not None
    parsed = [int(part.strip()) for part in match.group(1).split(",")]
    assert loaded["horizons"] == parsed == HORIZONS


def test_input_pins_blob_shas_are_40_hex() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    pins = loaded["input_pins"]
    assert pins
    for path, blob in pins.items():
        assert isinstance(path, str) and path.startswith("data/")
        assert isinstance(blob, str) and SHA40.match(blob)
    for key, rec in loaded["s0_blobs"].items():
        assert SHA40.match(rec["blob"]), key


def test_md_first_40_lines_contain_hindsight() -> None:
    lines = MD_PATH.read_text(encoding="utf-8").splitlines()[:40]
    assert any("HINDSIGHT" in line for line in lines)


def test_md_banned_phrases_only_negated() -> None:
    md = MD_PATH.read_text(encoding="utf-8")
    assert md_banned_violations(md) == []


def test_negation_check_explicit() -> None:
    assert banned_phrase_is_negated(
        "Surfaces never claim forecast skill.", "forecast skill"
    )
    assert banned_phrase_is_negated(
        "It is not P07 (P07 is EVT-RESPONSE-WINDOW).", "P07"
    )
    assert banned_phrase_is_negated(
        "This draft is not validated as confirmatory evidence.", "validated"
    )
    assert not banned_phrase_is_negated("The surface shows forecast skill.", "forecast skill")
    assert not banned_phrase_is_negated("Results are calibrated.", "calibrated")
    assert md_banned_violations("The method is calibrated on TRAIN.") == [
        "'calibrated' in 'The method is calibrated on TRAIN.'"
    ]
    assert md_banned_violations("The method is never calibrated on TRAIN.") == []


def test_r1_01_status_draft_unregistered_no_outcome() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    assert loaded["status"] == "DRAFT"
    assert loaded["registered"] is False
    assert loaded["outcome"] == "none"
    assert loaded["version"] == "v0-draft"
    assert loaded["drafted_by"] == "grok-4.6 lane A8 under seat 508c3757"
    assert loaded["drafted_at"].endswith("Z")
    assert "This draft registers nothing" in loaded["registration_note"]
    assert "This draft registers nothing" in md
    assert "R1 Chairman gate" in md


def test_r1_02_authority_false_top_and_cells() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    for key in AUTHORITY_KEYS:
        assert loaded["authority_flags"][key] is False
    for cell in loaded["cells"]:
        for key in AUTHORITY_KEYS:
            assert cell[key] is False


def test_r1_03_cohort_hindsight_survivorship_not_transfer_evidence() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    assert loaded["cohort"]["selection"].startswith("HINDSIGHT")
    assert loaded["cohort"]["survivorship"] is True
    assert "STRESS test" in loaded["cohort"]["role"]
    assert loaded["cohort"]["bridge_status"] == "NOT SUPPORTED — BRIDGE REQUIRED"
    assert "HINDSIGHT — 2026 market-cap leaders" in md
    assert "STRESS test" in md
    assert "BRIDGE REQUIRED" in md


def test_r1_04_declared_budget_21_holm() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    assert loaded["budget"]["declared_trials"] == 21
    assert loaded["budget"]["n_cells"] == 21
    assert loaded["budget"]["n_open_arms"] == 1
    assert loaded["budget"]["citation"] == "engine/trial_ledger.py L204"
    assert "Holm" in loaded["multiplicity"]["rule"]
    assert loaded["multiplicity"]["min_clusters"] == 2
    assert "Holm" in md
    assert "21" in md


def test_r1_05_p01_null_quoted_verbatim() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    null = loaded["p01_copy"]["register_row_citation"]["pre_registered_null"]
    retirement = loaded["p01_copy"]["register_row_citation"]["retirement_rule"]
    assert null == "H0₁: hit rate = 0.50 per horizon. H0₂: median excess = 0."
    assert retirement == "Visible retirement"
    assert loaded["p01_copy"]["register_row_citation"]["line"] == 115
    assert null in md
    assert "Visible retirement" in md


def test_r1_06_identity_null_unresolved() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert loaded["identity"]["canonical_issuer_id"] is None
    assert loaded["identity"]["security_id"] is None
    assert loaded["identity"]["issuer_link"] == "UNRESOLVED"
    for cell in loaded["cells"]:
        assert cell["canonical_issuer_id"] is None
        assert cell["security_id"] is None
        assert cell["issuer_link"] == "UNRESOLVED"


def test_r1_07_secondary_bench_map() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    expected = {
        "AAPL": "XLK",
        "MSFT": "XLK",
        "NVDA": "XLK",
        "AMZN": "XLY",
        "TSLA": "XLY",
        "GOOGL": "XLC",
        "META": "XLC",
    }
    for name, etf in expected.items():
        assert loaded["benches"]["secondary_by_name"][name]["display_label"] == etf
    assert loaded["benches"]["primary"]["display_label"] == "SPY"


def test_r1_08_cell_count_is_names_times_horizons() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert len(loaded["cells"]) == len(loaded["names"]) * len(loaded["horizons"]) == 21
    pairs = {(cell["name"], cell["horizon"]) for cell in loaded["cells"]}
    assert pairs == {(n, h) for n in NAMES for h in HORIZONS}


def test_r1_09_prospective_named_not_opened() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    assert loaded["arms"]["open"] == ["HISTORICAL-DESCRIPTIVE"]
    assert "PROSPECTIVE" in loaded["arms"]["named_not_opened"]


def test_r1_10_grading_directional_only() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    assert loaded["grading"]["surface_language"] == (
        "direction right/wrong over N matured beliefs"
    )
    assert "direction right/wrong over N matured beliefs" in md
    assert loaded["grading"]["primitive"].startswith("qledger grade_claim")


def test_r1_11_input_pins_include_subjects_and_benches() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    pins = loaded["input_pins"]
    for name in NAMES:
        assert f"data/yahoo/{name}.parquet" in pins
    for bench in ("SPY", "XLK", "XLY", "XLC"):
        assert f"data/yahoo/{bench}.parquet" in pins
    assert "data/yahoo/FB.parquet" not in pins


def test_r1_12_authority_true_refused_on_tmp_copy(tmp_path: Path) -> None:
    draft = deepcopy(_raw_draft())
    draft["authority_flags"]["rank_authority"] = 1
    path = _write_poison(tmp_path, draft)
    with pytest.raises(draft_loader.A8DraftRefused) as excinfo:
        draft_loader.load_draft(path)
    assert excinfo.value.code == "AUTHORITY_TRUTHY"


REGISTER_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "protocols"
    / "S0_PROTOCOL_REGISTER.md"
)
S0_CITE_RE = re.compile(r"S0_PROTOCOL_REGISTER\.md(?:\s+L|:)\s*(\d+)")
MD_PIN_ROW_RE = re.compile(
    r"^\|\s*(REG|IL|SL)\s*\|\s*(\S+)\s*\|\s*`([0-9a-f]{40})`\s*\|",
    re.MULTILINE,
)
PROTO_ID_RE = re.compile(r"\bP\d{2}\b")
ALLOWED_REGISTERED_FORM = re.compile(
    r"unregistered|not\s+registered|pre-registered|"
    r"\*\*registered:\*\*\s*false",
    re.IGNORECASE,
)
REGISTERED_WORD = re.compile(r"\bregistered\b", re.IGNORECASE)


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_r1_01_s0_blobs_match_disk() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    blobs = loaded["s0_blobs"]
    assert blobs
    for key, rec in blobs.items():
        data = (ROOT / rec["path"]).read_bytes()
        actual = _git_blob_sha(data)
        assert actual == rec["blob"], f"{key}: pinned {rec['blob']} != disk {actual}"


def test_r1_02_md_pin_table_matches_json() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    rows = {
        match.group(1): (match.group(2), match.group(3))
        for match in MD_PIN_ROW_RE.finditer(md)
    }
    assert set(rows) == set(loaded["s0_blobs"])
    for key, rec in loaded["s0_blobs"].items():
        path, sha = rows[key]
        assert path == rec["path"], key
        assert sha == rec["blob"], key


def test_r1_03_register_line_citations_resolve() -> None:
    register_lines = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
    found = 0
    for source, text in (
        ("json", JSON_PATH.read_text(encoding="utf-8")),
        ("md", MD_PATH.read_text(encoding="utf-8")),
    ):
        for match in S0_CITE_RE.finditer(text):
            found += 1
            line_no = int(match.group(1))
            assert 1 <= line_no <= len(register_lines), f"{source} L{line_no}"
            register_line = register_lines[line_no - 1]
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end < 0:
                line_end = len(text)
            sentence = text[line_start:line_end]
            protos = PROTO_ID_RE.findall(sentence) or ["P01"]
            for proto in protos:
                assert proto in register_line, (
                    f"{source} citation L{line_no} names {proto}; "
                    f"register line is {register_line!r}"
                )
            assert register_line.startswith("| P01 ") or any(
                register_line.startswith(f"| {proto} ") for proto in protos
            ), f"{source} L{line_no}: {register_line!r}"
    assert found >= 1


def test_r1_04_still_unregistered_draft() -> None:
    loaded = draft_loader.load_draft(JSON_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    assert loaded["status"] == "DRAFT"
    assert loaded["registered"] is False
    assert loaded["outcome"] == "none"
    assert loaded["family_id"] == FAMILY_ID
    flags = loaded["authority_flags"]
    assert set(flags) == AUTHORITY_KEYS
    for key in AUTHORITY_KEYS:
        assert flags[key] is False
    remainder = ALLOWED_REGISTERED_FORM.sub("", md)
    leftover = []
    for sentence in sentences_of(remainder):
        if REGISTERED_WORD.search(sentence) and not banned_phrase_is_negated(
            sentence, "registered"
        ):
            leftover.append(sentence)
    assert leftover == []
