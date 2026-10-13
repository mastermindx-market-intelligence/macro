"""Seal tests for SNI S0 register amendment A01 DRAFT.

Reads only the owned A01 files, the frozen register at its committed
worktree path, and tmp_path. Stdlib + pytest only.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.md"
JSON_PATH = ROOT / "research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.json"
REGISTER_PATH = ROOT / "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md"

AUTHORITY_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
SUCCESSOR_FIELDS = (
    "protocol_id",
    "retired_version",
    "split",
    "retirement_source",
    "successor_pointer",
    "successor_status",
    "budget_floor_carried",
    "owner",
)
ALLOWED_SUCCESSOR_STATUS = {
    "DRAFT",
    "NOT DRAFTED",
    "BRIDGE-FROZEN",
    "DRAFT IN FLIGHT",
    "DRAFT — pointer only",
}
P04_V2_PATH = (
    "research/single_name_intelligence/event_response/P04_V2_PREREG_DRAFT.md"
)
PROTOCOL_IDS = ("P01", "P02", "P03", "P04")
IDENTITY_ID_EXEMPT = {"protocol_id"}
BANNED_PHRASES = (
    "validated",
    "transfer shown",
    "forecast skill",
    "calibrated",
    "admitted",
    "resolved",
)
BANNED_EXCEPTIONS = (
    "NOT ADMITTED",
    "is not admission",
    "UNRESOLVED",
)
ORIGIN_MAIN_REGISTER_BLOB = "18cb5aa3a611bf1bc394d49d690e2059f68c4225"
ORIGIN_MAIN_BLOBS = {
    "data/yahoo/TCEHY.parquet": "0c03b5f83178ddf2ed9c25f39ef7688139ed24be",
    "data/yahoo/KWEB.parquet": "d42bd75db56f8ad5c2530ee415262a0c68b913bd",
    "data/reference/security_master.parquet": "85ef75104840b6b5be3aceeac21f1dbfabad6472",
    "data/reference/issuer_master.parquet": "6643e7eae37940d800659f7b4589f242ec70ef45",
    "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md": (
        ORIGIN_MAIN_REGISTER_BLOB
    ),
}
PATH_THEN_SHA_RE = re.compile(
    r"(?P<path>(?:data|research|config|engine)/[A-Za-z0-9_./-]+)"
    r"(?:.|\n){0,220}?"
    r"(?P<sha>[0-9a-f]{40})",
)
REGISTER_PATH_LINE_RE = re.compile(r"S0_PROTOCOL_REGISTER\.md:(\d+)")
REGISTER_LINE_RANGE_RE = re.compile(
    r"(?:origin/main |register §8 (?:origin/main )?)L(\d+)[–-]L(\d+)"
)
PROTOCOL_ID_RE = re.compile(r"\b(P0[1-4]|P13)\b")
FREEZE_QUOTE = "frozen before the bridge"


def git_blob_sha(data: bytes) -> str:
    """Git blob SHA-1: sha1(b'blob %d\\0' + bytes). Do not shell out."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def refuse_if_authority_true(doc: dict) -> dict:
    """Refuse a caller that tries to set any authority flag true."""
    if not isinstance(doc, dict):
        raise TypeError("amendment document must be a dict")

    def _walk(obj, path: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{path}.{key}" if path else key
                if key in AUTHORITY_KEYS and value is True:
                    raise ValueError(
                        f"refusing to set {here} true; SNI A01 authority flags stay false"
                    )
                _walk(value, here)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(doc, "")
    for key in AUTHORITY_KEYS:
        if key not in doc:
            raise ValueError(f"missing authority key {key}")
        if doc[key] is not False:
            raise ValueError(f"{key} must be false, got {doc[key]!r}")
    return doc


def load_amendment() -> dict:
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return refuse_if_authority_true(doc)


def parse_md_pipe_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def successor_table_from_md(text: str) -> dict[str, dict[str, str]]:
    tables = parse_md_pipe_tables(text)
    for table in tables:
        header = table[0]
        if header and header[0] == "protocol_id":
            rows = {}
            for raw in table[1:]:
                row = dict(zip(header, raw))
                rows[row["protocol_id"]] = row
            return rows
    raise AssertionError("markdown successor table with protocol_id header not found")


def tcehy_table_from_md(text: str) -> dict[str, object]:
    tables = parse_md_pipe_tables(text)
    for table in tables:
        header = table[0]
        if header[:2] == ["field", "value"]:
            out: dict[str, object] = {}
            for raw in table[1:]:
                key, value = raw[0], raw[1]
                if value == "null":
                    out[key] = None
                else:
                    out[key] = value
            return out
    raise AssertionError("markdown TCEHY field/value table not found")


def mask_banned_exceptions(text: str) -> str:
    masked = text
    for phrase in BANNED_EXCEPTIONS:
        masked = masked.replace(phrase, " " * len(phrase))
    return masked


def banned_hits(text: str) -> list[str]:
    masked = mask_banned_exceptions(text)
    lowered = masked.lower()
    hits = []
    for phrase in BANNED_PHRASES:
        if phrase.lower() in lowered:
            hits.append(phrase)
    return hits


def assert_no_banned_language(text: str, *, label: str = "text") -> None:
    hits = banned_hits(text)
    assert not hits, f"banned language in {label}: {hits}"


def walk_non_null_id_fields(obj, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else key
            if key.endswith("_id") and key not in IDENTITY_ID_EXEMPT and value is not None:
                found.append(f"{here}={value!r}")
            found.extend(walk_non_null_id_fields(value, here))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(walk_non_null_id_fields(item, f"{path}[{i}]"))
    return found


def register_line(n: int) -> str:
    lines = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
    assert 1 <= n <= len(lines), f"register line {n} out of range (n={len(lines)})"
    return lines[n - 1]


def path_sha_pairs(text: str) -> dict[str, str]:
    """First 40-hex sha that follows each known path in text."""
    pairs: dict[str, str] = {}
    for path in ORIGIN_MAIN_BLOBS:
        start = 0
        while True:
            idx = text.find(path, start)
            if idx < 0:
                break
            window = text[idx + len(path) : idx + len(path) + 220]
            match = re.search(r"[0-9a-f]{40}", window)
            if match:
                sha = match.group(0)
                prev = pairs.get(path)
                if prev is not None and prev != sha:
                    raise AssertionError(
                        f"{path} has disagreeing shas {prev} vs {sha}"
                    )
                pairs[path] = sha
                break
            start = idx + len(path)
    return pairs


def test_json_loads_status_draft_applied_false():
    doc = load_amendment()
    assert doc["status"] == "DRAFT"
    assert doc["applied"] is False


def test_amends_blob_matches_git_blob_hash():
    doc = load_amendment()
    blob = doc["amends_blob"]
    assert isinstance(blob, str)
    assert re.fullmatch(r"[0-9a-f]{40}", blob)
    register_bytes = REGISTER_PATH.read_bytes()
    assert git_blob_sha(register_bytes) == blob


def test_successor_rows_have_eight_fields_and_allowed_status():
    doc = load_amendment()
    rows = doc["successor_rows"]
    assert isinstance(rows, list) and rows
    for row in rows:
        for field in SUCCESSOR_FIELDS:
            assert field in row, f"missing {field} on {row!r}"
        assert row["successor_status"] in ALLOWED_SUCCESSOR_STATUS


def test_p01_p02_p03_p04_each_appear_exactly_once():
    doc = load_amendment()
    ids = [row["protocol_id"] for row in doc["successor_rows"]]
    for pid in PROTOCOL_IDS:
        assert ids.count(pid) == 1, f"{pid} count={ids.count(pid)}"


def test_p04_successor_path_matches_p04_v2_draft():
    doc = load_amendment()
    p04 = next(row for row in doc["successor_rows"] if row["protocol_id"] == "P04")
    assert P04_V2_PATH in p04["successor_pointer"]
    start = p04["successor_pointer"].index(P04_V2_PATH)
    assert p04["successor_pointer"][start : start + len(P04_V2_PATH)] == P04_V2_PATH


def test_us_row_contains_not_p07():
    doc = load_amendment()
    us_row = doc["us_mag7_pointer"]
    blob = json.dumps(us_row)
    assert "NOT P07" in blob
    assert "NOT P07" in us_row["not_p07"]
    md = MD_PATH.read_text(encoding="utf-8")
    assert "NOT P07" in md


def test_tcehy_ids_null_unresolved_not_admitted():
    tcehy = load_amendment()["tcehy"]
    assert tcehy["label"] == "TCEHY"
    assert tcehy["canonical_issuer_id"] is None
    assert tcehy["security_id"] is None
    assert tcehy["issuer_link"] == "UNRESOLVED"
    assert tcehy["admission"] == "NOT ADMITTED"


def test_recursive_walk_no_non_null_identity_id():
    doc = load_amendment()
    found = walk_non_null_id_fields(doc)
    assert found == [], f"non-null *_id fields: {found}"


def test_every_exit_condition_names_owner():
    conditions = load_amendment()["tcehy"]["exit_conditions"]
    assert conditions, "exit_conditions empty"
    for item in conditions:
        owner = item.get("owner")
        assert isinstance(owner, str) and owner.strip(), f"owner missing on {item!r}"


def test_six_authority_keys_present_and_false():
    doc = load_amendment()
    for key in AUTHORITY_KEYS:
        assert key in doc
        assert doc[key] is False


def test_md_json_agree_protocols_statuses_tcehy():
    doc = load_amendment()
    md = MD_PATH.read_text(encoding="utf-8")
    md_rows = successor_table_from_md(md)
    json_rows = {row["protocol_id"]: row for row in doc["successor_rows"]}
    assert set(md_rows) == set(json_rows) == set(PROTOCOL_IDS)
    for pid in PROTOCOL_IDS:
        assert md_rows[pid]["successor_status"] == json_rows[pid]["successor_status"]
    md_tcehy = tcehy_table_from_md(md)
    json_tcehy = doc["tcehy"]
    for field in (
        "label",
        "canonical_issuer_id",
        "security_id",
        "issuer_link",
        "admission",
    ):
        assert md_tcehy[field] == json_tcehy[field], field


def test_banned_language_owned_files_clean():
    assert_no_banned_language(MD_PATH.read_text(encoding="utf-8"), label="md")
    assert_no_banned_language(JSON_PATH.read_text(encoding="utf-8"), label="json")


def test_banned_language_poisoned_tmp_copy(tmp_path: Path):
    clean = MD_PATH.read_text(encoding="utf-8")
    assert_no_banned_language(clean, label="source md")
    poisoned = tmp_path / "S0_AMENDMENT_A01_DRAFT.md"
    poisoned.write_text(clean + "\nThis draft is validated.\n", encoding="utf-8")
    with pytest.raises(AssertionError):
        assert_no_banned_language(poisoned.read_text(encoding="utf-8"), label="poison md")
    json_poison = tmp_path / "S0_AMENDMENT_A01_DRAFT.json"
    json_poison.write_text(
        JSON_PATH.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    # Bare banned tokens, not the explicit exceptions.
    with pytest.raises(AssertionError):
        assert_no_banned_language("the name is admitted as a security", label="bare admitted")
    with pytest.raises(AssertionError):
        assert_no_banned_language("identity is resolved", label="bare resolved")
    with pytest.raises(AssertionError):
        assert_no_banned_language("forecast skill claimed", label="forecast skill")
    with pytest.raises(AssertionError):
        assert_no_banned_language("transfer shown for Mag-7", label="transfer shown")
    with pytest.raises(AssertionError):
        assert_no_banned_language("calibrated residual", label="calibrated")
    # Explicit exceptions must pass.
    assert_no_banned_language(
        "issuer_link UNRESOLVED; admission NOT ADMITTED; presence is not admission.",
        label="exceptions",
    )


def test_register_byte_identical_to_origin_main():
    doc = load_amendment()
    register_bytes = REGISTER_PATH.read_bytes()
    assert git_blob_sha(register_bytes) == doc["amends_blob"]
    assert doc["amends_blob"] == ORIGIN_MAIN_REGISTER_BLOB


def test_authority_true_refused():
    doc = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    for key in AUTHORITY_KEYS:
        tainted = dict(doc)
        tainted[key] = True
        with pytest.raises(ValueError, match="refusing to set"):
            refuse_if_authority_true(tainted)


def test_p01_p03_not_drafted_p02_bridge_frozen_p04_draft():
    rows = {row["protocol_id"]: row for row in load_amendment()["successor_rows"]}
    assert rows["P01"]["successor_status"] == "NOT DRAFTED"
    assert rows["P02"]["successor_status"] == "BRIDGE-FROZEN"
    assert rows["P03"]["successor_status"] == "NOT DRAFTED"
    assert rows["P04"]["successor_status"] == "DRAFT"


def test_header_and_frozen_effect_sentence():
    md = MD_PATH.read_text(encoding="utf-8")
    doc = load_amendment()
    assert md.splitlines()[0] == "# S0 register amendment A01 — DRAFT"
    assert doc["title"] == "S0 register amendment A01 — DRAFT"
    assert doc["drafted_by"] == "grok-4.6 lane S0D under seat 508c3757"
    assert doc["drafted_at"].endswith("Z")
    assert doc["amends"] == (
        "research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md"
    )
    needle = (
        "A01 changes no status, budget, split, horizon, null or retirement "
        "rule of the frozen register"
    )
    assert needle in md
    assert needle in doc["effect"]


def test_tcehy_mint_ban_and_exit_order():
    tcehy = load_amendment()["tcehy"]
    assert "No SNI lane may mint" in tcehy["mint_ban"]
    orders = [item["order"] for item in tcehy["exit_conditions"]]
    assert orders == sorted(orders)
    assert len(orders) == 4
    md = MD_PATH.read_text(encoding="utf-8")
    assert "## 7. Authority" in md
    assert "## 8. Language" in md
    assert "**OWNER FOLLOW-ON**" in md


def test_r1_02_register_citations_resolve():
    """Every register line citation resolves on the merged origin/main register.

    Old numbers (P01 :290, P03 :291, P02 :303, floors L302–L305, P13 :611)
    fail against this register; the repaired numbers pass.
    """
    md = MD_PATH.read_text(encoding="utf-8")
    js = JSON_PATH.read_text(encoding="utf-8")
    doc = load_amendment()

    path_cites: list[tuple[str, int, str]] = []
    for label, text in (("md", md), ("json", js)):
        for match in REGISTER_PATH_LINE_RE.finditer(text):
            n = int(match.group(1))
            ctx = text[max(0, match.start() - 100) : match.end() + 120]
            path_cites.append((label, n, ctx))
    assert path_cites, "no S0_PROTOCOL_REGISTER.md:N citations"

    for label, n, ctx in path_cites:
        text_line = register_line(n)
        if FREEZE_QUOTE in ctx:
            assert FREEZE_QUOTE in text_line, (
                f"{label} :{n} missing freeze quote in {text_line!r}"
            )
            continue
        pids = PROTOCOL_ID_RE.findall(ctx)
        assert pids, f"{label} :{n} has no protocol id in context {ctx!r}"
        if "P13" in pids:
            assert (
                "P13" in text_line
                or "KWEB" in text_line
                or "M0 gap 3" in text_line
            ), f"{label} :{n} P13 citation missed {text_line!r}"
        else:
            assert any(pid in text_line for pid in pids), (
                f"{label} :{n} expected one of {pids} in {text_line!r}"
            )

    for row in doc["successor_rows"]:
        match = REGISTER_PATH_LINE_RE.search(row["retirement_source"])
        assert match, row["protocol_id"]
        text_line = register_line(int(match.group(1)))
        assert row["protocol_id"] in text_line
        if row["protocol_id"] in ("P01", "P03", "P04"):
            assert "information_leak" in text_line
        if row["protocol_id"] == "P02":
            assert FREEZE_QUOTE in text_line

    range_hits = 0
    for label, text in (("md", md), ("json", js)):
        for match in REGISTER_LINE_RANGE_RE.finditer(text):
            start_n, end_n = int(match.group(1)), int(match.group(2))
            chunk = "\n".join(register_line(i) for i in range(start_n, end_n + 1))
            for pid in PROTOCOL_IDS:
                assert pid in chunk, f"{label} L{start_n}–L{end_n} missing {pid}"
            range_hits += 1
    assert range_hits >= 2, "budget-floor L-range must appear in both files"

    for label, text in (("md", md), ("json", js)):
        succ = re.search(r"Successors\** L(\d+)", text)
        assert succ, f"{label} missing Successors L citation"
        assert "Successors" in register_line(int(succ.group(1)))
        deleted = re.search(r"register §7 L(\d+)", text)
        assert deleted, f"{label} missing §7 L citation"
        assert "deleted" in register_line(int(deleted.group(1)))
        p02 = re.search(r"§9 P02 L(\d+)", text)
        assert p02, f"{label} missing §9 P02 L citation"
        assert "P02" in register_line(int(p02.group(1)))
        for match in re.finditer(r"register P13 L(\d+)", text):
            text_line = register_line(int(match.group(1)))
            assert (
                "P13" in text_line
                or "KWEB" in text_line
                or "M0 gap 3" in text_line
            ), text_line


def test_r1_03_no_stale_branch_citations():
    for path in (MD_PATH, JSON_PATH):
        text = path.read_text(encoding="utf-8")
        assert "not on origin/main" not in text, path
        assert "413ea4ad" not in text, path
        assert "claude/sni-s2-ship" not in text, path


def test_r1_04_blob_citations_agree():
    md = MD_PATH.read_text(encoding="utf-8")
    js = JSON_PATH.read_text(encoding="utf-8")
    md_map = path_sha_pairs(md)
    js_map = path_sha_pairs(js)
    common = set(md_map) & set(js_map)
    assert common, "expected shared path+sha citations in json and md"
    for path in sorted(common):
        assert md_map[path] == js_map[path], (path, md_map[path], js_map[path])
    for path, sha in ORIGIN_MAIN_BLOBS.items():
        assert js_map.get(path) == sha, (path, js_map.get(path), sha)
        assert md_map.get(path) == sha, (path, md_map.get(path), sha)
    blobs = load_amendment()["tcehy"]["blobs_metadata_only"]
    for path, sha in blobs.items():
        assert ORIGIN_MAIN_BLOBS[path] == sha


def test_r1_05_us_pointer_merge_order_independent():
    us_row = load_amendment()["us_mag7_pointer"]
    assert us_row["status"] == "DRAFT — pointer only"
    assert "exists_on_main" not in us_row
    assert us_row["family"] == "sni.us_transfer.RESID-DIR-US"
    assert (
        us_row["path"]
        == "research/single_name_intelligence/us_transfer/A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.md"
    )
    md = MD_PATH.read_text(encoding="utf-8")
    assert "DRAFT — pointer only" in md
    assert "A01 points at this path only" in md
    assert (
        "Whether or not the file is present, A01 does not register it "
        "and does not claim it is registered."
    ) in md
    assert "exists_on_main" not in JSON_PATH.read_text(encoding="utf-8")
