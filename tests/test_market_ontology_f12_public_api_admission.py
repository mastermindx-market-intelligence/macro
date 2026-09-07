"""Tests for packet B-F12-5: Public API v0 admission ruling (records only)."""
import csv
import io
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RULING_PATH = REPO_ROOT / "research/market_intelligence_productization/MARKET_ONTOLOGY_F12_PUBLIC_API_ADMISSION_2026-09-06.md"
DEC_PATH = REPO_ROOT / "agentos/decisions/DEC-F12-PUBLIC-API-V0-ADMISSION-2026-09-06.md"
CSV_PATH = REPO_ROOT / "research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv"
DNR_PATH = REPO_ROOT / "research/DO_NOT_REBUILD.md"
LEGACY_JOBS_PATH = REPO_ROOT / ".github/ci/legacy-jobs.yml"
SF_BLOCKLIST_PATH = REPO_ROOT / "config/signal_foundry_blocklist.yml"

SEVEN_IDS = [
    "MO-PAID-055",
    "MO-PAID-084",
    "MO-PAID-056",
    "MO-DELTA-036",
    "MO-DELTA-037",
    "MO-DELTA-038",
    "MO-DELTA-039",
]

EXPECTED_HEADER = (
    "id,family,granular_disposition,capability_state_c2,state_delta,"
    "current_owner,real_producer,real_consumer,missing_contract_or_proof,"
    "correction_behavior,next_bounded_child,acceptance_test,source_rights,"
    "authority_ceiling,adjudication_notes"
)

SECTION_HEADINGS = [
    "## 2. (a) Is there a v0 public API at all",
    "## 3. (b) Key issuance and revocation",
    "## 4. (c) Idempotency-key semantics",
    "## 5. (d) schema_version and inference_metadata",
    "## 6. (e) Webhooks",
    "## Redistribution clause",
    "## 7. (g) MO-DELTA-039 disposition",
]


def _ruling_text():
    return RULING_PATH.read_text(encoding="utf-8")


def _split_sections(text):
    """Split the ruling doc into named sections keyed by heading."""
    indices = []
    for heading in SECTION_HEADINGS:
        idx = text.index(heading)
        indices.append((heading, idx))
    indices.sort(key=lambda t: t[1])
    sections = {}
    for i, (heading, idx) in enumerate(indices):
        end = indices[i + 1][1] if i + 1 < len(indices) else len(text)
        sections[heading] = text[idx:end]
    return sections


def test_ruling_doc_exists_and_answers_seven_questions():
    assert RULING_PATH.exists(), "ruling doc missing"
    text = _ruling_text()
    for heading in SECTION_HEADINGS:
        assert heading in text, f"missing section: {heading}"
    sections = _split_sections(text)
    for heading, body in sections.items():
        assert "Answer:" in body, f"{heading} missing Answer:"
        assert "Rationale:" in body, f"{heading} missing Rationale:"
        assert "Rejected alternative:" in body, f"{heading} missing Rejected alternative:"


def test_answer_a_is_not_a_deferral():
    text = _ruling_text()
    sections = _split_sections(text)
    section_a = sections["## 2. (a) Is there a v0 public API at all"]
    # isolate the Answer: line(s) up to the next label
    m = re.search(r"Answer:(.*?)(?:Rationale:|Rejected alternative:)", section_a, re.S)
    assert m, "could not isolate Answer: text for (a)"
    answer_text = m.group(1)
    assert not re.search(r"(?i)\b(defer|deferred|TBD|pending a later wave)\b", answer_text), (
        "answer to (a) reads as a deferral"
    )


def test_forbidden_second_planes_named():
    text = _ruling_text()
    required_terms = [
        "second auth plane",
        "second tenant plane",
        "second job queue",
        "second event queue",
        "second API truth store",
        "webhook retry DB",
        "second secret store",
        "collaboration state plane",
        "public redistribution rights inferred from internal data rights",
    ]
    for term in required_terms:
        assert term in text, f"missing forbidden-plane term: {term}"
    for owner in ["app/main.py", "app/billing.py", "engine/research_vault/download_quota.py"]:
        assert owner in text, f"missing owner citation: {owner}"


def test_redistribution_clause_names_excluded_sources():
    text = _ruling_text()
    sections = _split_sections(text)
    clause = sections["## Redistribution clause"]
    assert "Case-Shiller" in clause and "S&P" in clause
    assert "Freddie" in clause and "PMMS" in clause
    assert "NAR" in clause
    assert "BIS" in clause
    wire_feeds = ["Benzinga", "Tiingo", "Marketaux", "Finnhub", "Alpha Vantage"]
    present = [w for w in wire_feeds if w in clause]
    assert len(present) >= 3, f"only found {present}"
    assert "transcript" in clause.lower()
    assert "card" in clause.lower() and "panel" in clause.lower()


CJK_RE = re.compile(r"[一-鿿]")
BANNED_TERMS = [
    "falsifier",
    "refuted",
    "证伪",
    "MO-PAID-",
    "MO-DELTA-",
    "schema_version",
    "inference_metadata",
    "K1",
    "K3",
    "K5",
    "401",
    "403",
    "429",
]


def test_customer_copy_is_bilingual_and_plain():
    text = _ruling_text()
    start = text.index("## Customer-facing copy (frozen)")
    end = text.index("## Admission gate G1-G4")
    block = text[start:end]
    # table rows: skip header/separator rows
    rows = [
        line for line in block.splitlines()
        if line.strip().startswith("|") and "---" not in line and "Situation" not in line
    ]
    assert len(rows) >= 8, f"expected at least 8 copy rows, found {len(rows)}"
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert len(cells) == 3, f"malformed copy row: {row}"
        _situation, en, zh = cells
        assert en, f"empty EN cell in row: {row}"
        assert zh, f"empty ZH cell in row: {row}"
        assert CJK_RE.search(zh), f"ZH cell has no CJK characters: {row}"
    for term in BANNED_TERMS:
        assert term not in block, f"banned term '{term}' found in customer copy block"


def _load_csv_rows():
    raw = CSV_PATH.read_bytes()
    return raw, list(csv.reader(io.StringIO(raw.decode("utf-8"))))


def test_ledger_rows_carry_dec_key_and_wave():
    _, rows = _load_csv_rows()
    header = rows[0]
    by_id = {r[0]: r for r in rows[1:] if r}
    for row_id in SEVEN_IDS:
        assert row_id in by_id, f"row {row_id} not found in ledger"
        row = by_id[row_id]
        notes = row[header.index("adjudication_notes")]
        next_child = row[header.index("next_bounded_child")]
        assert "DEC:F12-PUBLIC-API-V0-ADMISSION-2026-09-06" in notes, (
            f"{row_id} adjudication_notes missing DEC key"
        )
        assert re.search(r"wave MARKET-OS-[CDE]", notes), (
            f"{row_id} adjudication_notes missing wave reference"
        )
        assert not next_child.strip().upper().startswith("DEFER"), (
            f"{row_id} next_bounded_child still starts with DEFER"
        )


def test_ledger_structure_unchanged():
    raw, rows = _load_csv_rows()
    assert len(rows) == 131, f"expected 131 rows, found {len(rows)}"
    for i, row in enumerate(rows):
        assert len(row) == 15, f"row {i} has {len(row)} columns, expected 15"
    header_line = raw.decode("utf-8").split("\r\n")[0]
    assert header_line == EXPECTED_HEADER, "CSV header changed unexpectedly"
    # every physical line must end \r\n
    text = raw.decode("utf-8")
    # strip trailing newline before checking, then verify CRLF discipline
    body = text[:-2] if text.endswith("\r\n") else text
    assert "\r\n" in body
    # no bare \n without preceding \r within the row-ending positions
    # (a lightweight check: count \r\n occurrences vs \n occurrences)
    assert text.count("\n") == text.count("\r\n"), "found a bare LF not paired with CR"


def test_dec_record_shape():
    assert DEC_PATH.exists(), "DEC record missing"
    text = DEC_PATH.read_text(encoding="utf-8")
    assert text.startswith("---"), "DEC record missing frontmatter delimiter"
    parts = text.split("---", 2)
    assert len(parts) >= 3, "DEC record frontmatter malformed"
    frontmatter = yaml.safe_load(parts[1])
    required_keys = {
        "key", "question", "answer", "rationale", "alternatives", "evidence",
        "affects", "confidence", "reversibility", "decided_by", "decided_at",
    }
    missing = required_keys - set(frontmatter.keys())
    assert not missing, f"DEC record missing keys: {missing}"
    assert frontmatter["reversibility"] in {"easy", "costly", "one_way"}
    assert frontmatter["confidence"] in {"high", "medium", "low"}
    assert isinstance(frontmatter["alternatives"], list) and len(frontmatter["alternatives"]) >= 1
    for alt in frontmatter["alternatives"]:
        assert "option" in alt and "why_not" in alt
    assert "created" not in frontmatter
    assert "updated" not in frontmatter


# ---------------------------------------------------------------------------
# PR #6925 review round 1 — RED-first pins (minor-3) + MAJOR-3 G2 locator fix
# ---------------------------------------------------------------------------

def _dnr_text():
    return DNR_PATH.read_text(encoding="utf-8")


def test_dnr_key_is_refused_not_scoped():
    """A silent revert of the DNR row's Key column back to the withdrawn
    r2 name (`...-SCOPED`) must be caught here, not just by format-only
    checks (tests/test_dnr_registry_keys.py validates key *shape*, not
    *identity* — review r1 minor-3)."""
    text = _dnr_text()
    assert "LAW-F12-PUBLIC-API-V0-REFUSED" in text
    assert "LAW-F12-PUBLIC-API-V0-SCOPED" not in text


def test_dnr_row_g2_locator_names_the_open_terminal_migration():
    """MAJOR-3 (ruling r4): the G2 locator must name the actual open Terminal
    migration + tracking issue the spec's own G2 wording gates on, and must
    NOT claim macro's own DDL ledger is the locator (review r1: no such row
    exists past macro's `0008`)."""
    text = _dnr_text()
    start = text.index("LAW-F12-PUBLIC-API-V0-REFUSED")
    end = text.index("\n", start)
    row = text[start:end]
    for needle in [
        "0014_tenancy_foundation.sql",
        "charting-app",
        "supabase/migrations",
        "terminal#514",
        "open at the time of writing",
        "posted readback",
        "B-F12-1",
        "WS:MARKET-OS A2-A6",
    ]:
        assert needle in row, f"G2 locator missing {needle!r}: {row[:400]}"
    assert "macro's own DDL ledger" not in row, (
        "G2 locator must not claim macro's own DDL ledger is the locator (ruling r4 MAJOR-3)"
    )


def test_self_mod_fence_paths_include_the_three_f12_artifacts():
    """The self-mod-fence job's `paths:` must list the DEC record, the ledger
    CSV, and the ruling doc beyond a `run_ci_pack --validate-only` probe
    (review r1 minor-3) — a silent removal here would desync the fence from
    the artifacts it is meant to guard."""
    text = LEGACY_JOBS_PATH.read_text(encoding="utf-8")
    header = "\n  self-mod-fence:\n"
    header_start = text.index(header)
    body_start = header_start + len(header)
    # Bound the search to this job block: up to the next top-level job key
    # at the same 2-space indent (a bare "  <name>:" line).
    next_job = re.search(r"\n  [a-zA-Z][\w-]*:\n", text[body_start:])
    block = text[header_start: body_start + next_job.start()] if next_job else text[header_start:]
    for path in [
        "agentos/decisions/DEC-F12-PUBLIC-API-V0-ADMISSION-2026-09-06.md",
        "research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv",
        "research/market_intelligence_productization/MARKET_ONTOLOGY_F12_PUBLIC_API_ADMISSION_2026-09-06.md",
    ]:
        assert path in block, f"self-mod-fence paths missing {path}"


def test_bl_g099_reason_has_no_unbalanced_backtick():
    """Review r1 minor-2: the 200-char reason truncation used to cut mid-token
    and mid-backtick. Pins the fixed behavior against the real compiled
    artifact (not just a hermetic fixture)."""
    data = yaml.safe_load(SF_BLOCKLIST_PATH.read_text(encoding="utf-8"))
    entry = next(e for e in data["entries"] if e["id"] == "BL-G099")
    reason = entry["reason"]
    assert reason.count("`") % 2 == 0, f"unbalanced backtick in BL-G099 reason: {reason!r}"
    # No mid-word cut: the reason must not end with a truncated fragment
    # glued to the next word — every wrapped reason in this file ends on a
    # real word boundary once truncated at all.
    assert not reason.rstrip().endswith(("-", "/", "_")), reason


def test_bl_g099_any_of_matches_all_six_ruling_phrasings():
    """MAJOR-1 (ruling r4, amended): BL-G099's `any_of` must match each of the
    six real proposer phrasings the ruling named, standalone — the derived
    single conjunctive `.{0,30}` signature matched none of them (review r1
    major-1, falsified against `scripts/compile_loop_blocklists.py`).
    Mirrors the runtime match in `engine/signal_foundry/screen.py`
    (`re.search(pattern, combined_text, re.IGNORECASE)`)."""
    data = yaml.safe_load(SF_BLOCKLIST_PATH.read_text(encoding="utf-8"))
    entry = next(e for e in data["entries"] if e["id"] == "BL-G099")
    patterns = entry["match"]["any_of"]
    phrasings = [
        "we want to ship an api key for partners",
        "add an api_key column to the users table",
        "expose a public api for this",
        "send a webhook when the trade closes",
        "we need a second quota meter for this tier",
        "add a keyed endpoint for read access",
    ]
    for phrase in phrasings:
        hit = any(re.search(pat, phrase, re.IGNORECASE) for pat in patterns)
        assert hit, f"phrase {phrase!r} did not match any BL-G099 pattern: {patterns}"
