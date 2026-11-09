"""E3-A shadow extraction tests — AAPL FY2026 Q3.

Pins fixture SHAs. Validates gold file integrity.
Validates shadow compiler behavior (segmenter, scoring, ledger format).

Frozen source SHAs (load-bearing — any divergence must STOP the eval):
  Exhibit 99.1: 070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb
  Transcript:   a8ff5d03e875fef5604791edbf625186c447af049e6e02f55bb89c68c7cc9f9f

Gold:
  Path:   research/earnings_intelligence/e3/gold/aapl_fy2026_q3_qa_gold.json
  SHA256: fc6df84d2a8d0d96475ce697ba92ffdd071d5c283b8daee97c1b3381382fa42c
  Schema: aapl_fy2026_q3_qa_gold.v2
  Supersedes v1: 6b1100b148396db9a29974da5bc6e0cc55e5534185e50e061fe3635d429ed761

Taxonomy:
  version: qa_topic.v1
  hash:    a928ca72ab2e91bda74bd1e69021e08a5234e501f095610e623655db7e323b5e
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

# ── Constants ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
FIXTURE_DIR = REPO_ROOT / "tests/fixtures/company_intelligence"

FROZEN_EXHIBIT_SHA = "070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb"
FROZEN_TRANSCRIPT_SHA = "a8ff5d03e875fef5604791edbf625186c447af049e6e02f55bb89c68c7cc9f9f"

GOLD_PATH = REPO_ROOT / "research/earnings_intelligence/e3/gold/aapl_fy2026_q3_qa_gold.json"
GOLD_SHA256 = "fc6df84d2a8d0d96475ce697ba92ffdd071d5c283b8daee97c1b3381382fa42c"
SUPERSEDED_GOLD_SHA_V1 = "6b1100b148396db9a29974da5bc6e0cc55e5534185e50e061fe3635d429ed761"

TAXONOMY_VERSION = "qa_topic.v1"
TAXONOMY_HASH = "a928ca72ab2e91bda74bd1e69021e08a5234e501f095610e623655db7e323b5e"

EVENT_ID = "evt_cik0000320193_2026q3_results"
TX_DOC_ID = "tx:AAPL/2026Q3"
RELEASE_DOC_ID = "release:0000320193-26-000018"

EXPECTED_EXCHANGE_COUNT = 7
EXPECTED_SEGMENT_COUNT = 108
EXPECTED_OPERATOR_INTRO_SEGMENTS = [32, 42, 52, 63, 76, 84, 97]

CLOSED_TAXONOMY_MEMBERS = frozenset({
    "demand", "product", "pricing", "costs_supply",
    "capacity", "capital_allocation", "regulation",
    "other", "unavailable",
})


# ── SHA pin tests ──────────────────────────────────────────────────────────────


def test_exhibit_sha_pinned():
    """Exhibit 99.1 SHA must match frozen spec."""
    path = FIXTURE_DIR / "aapl_fy2026_q3_ex99_1.htm"
    assert path.exists(), f"Fixture missing: {path}"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == FROZEN_EXHIBIT_SHA, (
        f"Exhibit 99.1 SHA divergence: actual={actual} frozen={FROZEN_EXHIBIT_SHA}"
    )


def test_transcript_sha_pinned():
    """Transcript SHA (uncompressed) must match frozen spec."""
    path = FIXTURE_DIR / "aapl_fy2026_q3.json.gz"
    assert path.exists(), f"Fixture missing: {path}"
    with gzip.open(path) as f:
        actual = hashlib.sha256(f.read()).hexdigest()
    assert actual == FROZEN_TRANSCRIPT_SHA, (
        f"Transcript SHA divergence: actual={actual} frozen={FROZEN_TRANSCRIPT_SHA}"
    )


def test_gold_sha_pinned():
    """Gold file SHA must match the pinned value (gold is frozen)."""
    assert GOLD_PATH.exists(), f"Gold file missing: {GOLD_PATH}"
    actual = hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest()
    assert actual == GOLD_SHA256, (
        f"Gold SHA divergence: actual={actual} pinned={GOLD_SHA256}\n"
        "If you intentionally updated the gold, update GOLD_SHA256 in this test."
    )


# ── Gold file structural integrity ────────────────────────────────────────────


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_bytes())


def test_gold_schema(gold):
    assert gold["schema"] == "aapl_fy2026_q3_qa_gold.v2"
    assert gold["supersedes"]["gold_sha256"] == SUPERSEDED_GOLD_SHA_V1


def test_gold_exchange_count(gold):
    assert gold["qa_exchange_count"] == EXPECTED_EXCHANGE_COUNT
    assert len(gold["exchanges"]) == EXPECTED_EXCHANGE_COUNT


def test_gold_source_shas(gold):
    pkg = gold["source_package"]
    sources = {s["kind"]: s for s in pkg["sources"]}
    assert sources["issuer_release"]["source_sha256"] == FROZEN_EXHIBIT_SHA
    assert sources["transcript"]["source_sha256_uncompressed"] == FROZEN_TRANSCRIPT_SHA
    assert pkg["sha_divergence_check"] == "pass"


def test_gold_event_id(gold):
    for ex in gold["exchanges"]:
        assert ex["event_id"] == EVENT_ID, f"Exchange {ex['ordinal']} has wrong event_id"


def test_gold_taxonomy_version_and_hash(gold):
    tax = gold["taxonomy"]
    assert tax["version"] == TAXONOMY_VERSION
    assert tax["hash"] == TAXONOMY_HASH
    # Recompute hash from canonical JSON
    canonical = json.dumps(
        {"schema": "qa_topic_taxonomy.v1", "version": TAXONOMY_VERSION,
         "members": sorted(tax["members"])},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    recomputed = hashlib.sha256(canonical).hexdigest()
    assert recomputed == TAXONOMY_HASH, (
        f"Taxonomy hash mismatch: recomputed={recomputed} stored={TAXONOMY_HASH}"
    )


def test_gold_taxonomy_members_closed(gold):
    members = set(gold["taxonomy"]["members"])
    assert members == CLOSED_TAXONOMY_MEMBERS, (
        f"Taxonomy members differ.\nExpected: {sorted(CLOSED_TAXONOMY_MEMBERS)}\n"
        f"Got: {sorted(members)}"
    )


def test_gold_no_open_topic_labels(gold):
    """Every topic label in every exchange must be in the closed taxonomy."""
    for ex in gold["exchanges"]:
        ordinal = ex["ordinal"]
        for topic in ex.get("topics", []):
            assert topic in CLOSED_TAXONOMY_MEMBERS, (
                f"Exchange {ordinal} has unknown topic label: {topic!r}"
            )


def test_gold_ordinals_sequential(gold):
    ordinals = [ex["ordinal"] for ex in gold["exchanges"]]
    assert ordinals == list(range(EXPECTED_EXCHANGE_COUNT))


def test_gold_exchange_ids_format(gold):
    """exchange_id format: qx_{event_id}_{document_sha256[:12]}_{ordinal:02d}"""
    sha_prefix = FROZEN_TRANSCRIPT_SHA[:12]
    for ex in gold["exchanges"]:
        expected = f"qx_{EVENT_ID}_{sha_prefix}_{ex['ordinal']:02d}"
        assert ex["exchange_id"] == expected, (
            f"Exchange {ex['ordinal']} has bad exchange_id: {ex['exchange_id']!r}\n"
            f"Expected: {expected!r}"
        )


def test_gold_document_sha_on_exchanges(gold):
    for ex in gold["exchanges"]:
        assert ex["document_sha256"] == FROZEN_TRANSCRIPT_SHA
        assert ex["document_id"] == TX_DOC_ID


def test_gold_questioner_fields(gold):
    """Questioner must have name/affiliation with source-supported states."""
    for ex in gold["exchanges"]:
        q = ex["questioner"]
        assert q["name"], f"Exchange {ex['ordinal']}: questioner name empty"
        assert q["affiliation"], f"Exchange {ex['ordinal']}: questioner affiliation empty"
        assert q["name_state"] == "source_supported"
        assert q["affiliation_state"] == "source_supported"


def test_gold_no_identity_not_in_source(gold):
    """identity_not_in_source is not a valid absence reason (freeze §7)."""
    raw = json.dumps(gold)
    assert "identity_not_in_source" not in raw, (
        "Found forbidden typed absence reason 'identity_not_in_source'"
    )


def test_gold_respondents_not_collapsed(gold):
    """Exchange 5 (Wamsi Mohan) must have both Tim Cook and John Ternus."""
    ex5 = gold["exchanges"][5]
    names = {r["name"] for r in ex5["respondents"]}
    assert "Tim Cook" in names, "Exchange 5: Tim Cook missing from respondents"
    assert "John Ternus" in names, "Exchange 5: John Ternus missing from respondents"


def test_gold_exchange_0_preserves_two_tim_answer_turns(gold):
    """Kevan 34/35 → Tim 36/37 → analyst 38 → Tim 39/40 is two Tim turns."""
    ex0 = gold["exchanges"][0]
    names = [r["name"] for r in ex0["respondents"]]
    assert names == ["Kevan Parekh", "Tim Cook", "Tim Cook"]
    assert [r["span_indexes"] for r in ex0["respondents"]] == [[0, 1], [2, 3], [4, 5]]
    assert [s["segment_index"] for s in ex0["answer_spans"]] == [34, 35, 36, 37, 39, 40]
    assert ex0["answer_spans"][2]["speaker"] == "Tim Cook"
    assert ex0["answer_spans"][4]["speaker"] == "Tim Cook"


def test_gold_respondents_are_answer_turns_not_unique_speakers(gold):
    """respondents[] partitions answer_spans; same speaker may repeat after a follow-up."""
    for ex in gold["exchanges"]:
        n_ans = len(ex["answer_spans"])
        seen: list[int] = []
        for resp in ex["respondents"]:
            seen.extend(resp["span_indexes"])
        assert seen == list(range(n_ans)), (
            f"Exchange {ex['ordinal']}: respondents do not partition answer_spans "
            f"({seen} vs {list(range(n_ans))})"
        )
    assert sum(len(ex["respondents"]) for ex in gold["exchanges"]) == 26


def test_gold_no_overlay_14(gold):
    """The exchange count must not be 14; overlay 14 is not a valid boundary count."""
    assert gold["qa_exchange_count"] != 14, "exchange_count must not be 14 (freeze §7.2)"
    assert len(gold["exchanges"]) != 14, "exchanges[] length must not be 14"


def test_gold_question_spans_nonempty(gold):
    for ex in gold["exchanges"]:
        assert ex["question_spans"], f"Exchange {ex['ordinal']}: empty question_spans"


def test_gold_span_segment_indexes_valid(gold):
    """All span segment_indexes must be within [0, 107]."""
    for ex in gold["exchanges"]:
        for span in ex["question_spans"] + ex["answer_spans"]:
            idx = span["segment_index"]
            assert 0 <= idx <= 107, (
                f"Exchange {ex['ordinal']}: segment_index {idx} out of range"
            )


def test_gold_span_byte_ranges_valid(gold):
    """All start_byte < end_byte and end_byte <= actual segment UTF-8 length."""
    with gzip.open(FIXTURE_DIR / "aapl_fy2026_q3.json.gz") as f:
        tx = json.load(f)
    segs = tx["segments"]

    for ex in gold["exchanges"]:
        for span in ex["question_spans"] + ex["answer_spans"]:
            idx = span["segment_index"]
            seg_bytes = segs[idx]["text"].encode("utf-8")
            assert span["start_byte"] == 0, (
                f"Exchange {ex['ordinal']} seg {idx}: start_byte != 0"
            )
            assert span["end_byte"] == len(seg_bytes), (
                f"Exchange {ex['ordinal']} seg {idx}: end_byte {span['end_byte']} "
                f"!= actual byte length {len(seg_bytes)}"
            )
            assert span["text_sha256"] == hashlib.sha256(seg_bytes).hexdigest()


def test_gold_respondent_span_indexes_valid(gold):
    """respondents[].span_indexes must reference valid answer_spans indexes."""
    for ex in gold["exchanges"]:
        n_ans = len(ex["answer_spans"])
        for resp in ex["respondents"]:
            for idx in resp["span_indexes"]:
                assert 0 <= idx < n_ans, (
                    f"Exchange {ex['ordinal']} respondent {resp['name']}: "
                    f"span_index {idx} out of range (n_answer_spans={n_ans})"
                )


def test_gold_usefulness_bar_written_refusal(gold):
    bar = gold["usefulness_bar"]
    assert bar["decision"] == "refusal"
    assert bar["numeric_threshold"] is None
    assert isinstance(bar["written_refusal"], str) and len(bar["written_refusal"]) > 50
    assert bar["return_to_sol"] is True


def test_gold_frozen_at_set(gold):
    assert gold.get("frozen_at"), "frozen_at timestamp must be set"


def test_gold_no_event_workspace_advance(gold):
    """Gold must not be an event_workspace.v1 payload (no workspace schema or top-level generation_id)."""
    assert gold.get("schema") != "event_workspace.v1", "Gold must not use event_workspace.v1 schema"
    assert "generation_id" not in gold, "Gold must not have a top-level generation_id (workspace field)"
    # live_generation_id in source_package is a reference, not a promotion — allowed
    assert "qa_exchanges" not in gold, "Gold must not have qa_exchanges (workspace promotion field)"


# ── Shadow compiler unit tests ────────────────────────────────────────────────


def test_verify_fixture_shas_pass():
    """SHA verification must pass on the pinned fixtures."""
    from engine.company_intelligence.e3_shadow_compiler import verify_fixture_shas
    result = verify_fixture_shas(REPO_ROOT)
    assert result["check"] == "pass"
    assert result["exhibit_sha"] == FROZEN_EXHIBIT_SHA
    assert result["transcript_sha"] == FROZEN_TRANSCRIPT_SHA


def test_stable_segment_id_deterministic():
    """stable_segment_id must be deterministic for same inputs."""
    from engine.company_intelligence.e3_shadow_compiler import stable_segment_id
    id1 = stable_segment_id(FROZEN_TRANSCRIPT_SHA, 0)
    id2 = stable_segment_id(FROZEN_TRANSCRIPT_SHA, 0)
    assert id1 == id2
    assert id1.startswith("seg_")
    # Different index → different ID
    id3 = stable_segment_id(FROZEN_TRANSCRIPT_SHA, 1)
    assert id1 != id3


def test_stable_segment_id_format():
    from engine.company_intelligence.e3_shadow_compiler import stable_segment_id
    sid = stable_segment_id(FROZEN_TRANSCRIPT_SHA, 42)
    parts = sid.split("_")
    assert parts[0] == "seg"
    assert parts[1] == FROZEN_TRANSCRIPT_SHA[:16]
    assert parts[2] == "0042"


def test_segment_count():
    from engine.company_intelligence.e3_shadow_compiler import load_transcript_segments
    segs = load_transcript_segments(REPO_ROOT)
    assert len(segs) == EXPECTED_SEGMENT_COUNT


def test_operator_intro_segments():
    """The 7 operator-delimited intro segments must exist and contain 'go ahead'."""
    from engine.company_intelligence.e3_shadow_compiler import load_transcript_segments
    segs = load_transcript_segments(REPO_ROOT)
    for seg_idx in EXPECTED_OPERATOR_INTRO_SEGMENTS:
        seg = segs[seg_idx]
        assert seg.get("role") == "Operator", (
            f"Segment {seg_idx}: expected role='Operator', got {seg.get('role')!r}"
        )
        assert "go ahead" in seg.get("text", "").lower(), (
            f"Segment {seg_idx}: 'go ahead' not found in text: {seg.get('text', '')[:100]!r}"
        )


def test_score_attempt_no_candidates_not_exercised():
    """Zero candidates must NOT report 100% replay or all_pass=true."""
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt,
    )
    attempt = ModelAttempt(provider="test", model="test", status="provider_unavailable")
    gold = json.loads(GOLD_PATH.read_bytes())
    segs = load_transcript_segments(REPO_ROOT)
    score = score_attempt(attempt, gold, segs)
    assert score["hard_gates"]["status"] == "NOT_EXERCISED"
    assert score["hard_gates"]["all_pass"] is False
    assert score["accepted_count"] == 0
    assert score["source_span_replay_success_pct"] is None
    assert score["source_span_replay_success_pct"] != 100.0


def test_score_attempt_cross_event_detected():
    """Foreign event_id is rejected and never trusted as a TP."""
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, gold_exchange_to_candidate, load_transcript_segments,
        score_attempt,
    )
    gold = json.loads(GOLD_PATH.read_bytes())
    segs = load_transcript_segments(REPO_ROOT)
    cand = gold_exchange_to_candidate(gold["exchanges"][0])
    cand["event_id"] = "evt_cik0000000000_2026q3_results"
    attempt = ModelAttempt(provider="test", model="test", status="ok", candidates=[cand])
    score = score_attempt(attempt, gold, segs)
    assert score["cross_event_rejected"] == 1
    assert score["accepted_cross_event"] == 0
    assert score["hard_gates"]["accepted_cross_event"] == 0
    assert score["hard_gates"]["cross_event"] == 0
    assert score["accepted_count"] == 0
    assert score["hard_gates"]["status"] == "NOT_EXERCISED"
    assert score["exchange_boundary_quality"]["tp"] == 0


def test_parse_candidates_valid_json():
    from engine.company_intelligence.e3_shadow_compiler import _parse_candidates
    raw = json.dumps([{"ordinal": 0, "questioner_name": "Test"}])
    result = _parse_candidates(raw)
    assert len(result) == 1
    assert result[0]["ordinal"] == 0


def test_parse_candidates_markdown_wrapped():
    from engine.company_intelligence.e3_shadow_compiler import _parse_candidates
    raw = "```json\n[{\"ordinal\": 0}]\n```"
    result = _parse_candidates(raw)
    assert len(result) == 1


def test_parse_candidates_invalid_returns_empty():
    from engine.company_intelligence.e3_shadow_compiler import _parse_candidates
    result = _parse_candidates("not valid json at all")
    assert result == []


# ── Gold operator boundary matches transcript structure ────────────────────────


def test_gold_exchange_0_questioner():
    gold = json.loads(GOLD_PATH.read_bytes())
    ex = gold["exchanges"][0]
    assert ex["questioner"]["name"] == "Amit Daryanani"
    assert ex["questioner"]["affiliation"] == "Evercore"


def test_gold_exchange_5_has_john_ternus():
    """Exchange 5 (Wamsi Mohan) must include John Ternus as distinct respondent."""
    gold = json.loads(GOLD_PATH.read_bytes())
    ex = gold["exchanges"][5]
    respondent_names = [r["name"] for r in ex["respondents"]]
    assert "John Ternus" in respondent_names
    assert "Tim Cook" in respondent_names
    assert respondent_names[-1] == "John Ternus"
    assert respondent_names.count("John Ternus") == 1
    assert len(respondent_names) == 5


def test_gold_all_seven_questioners(gold):
    names = {ex["questioner"]["name"] for ex in gold["exchanges"]}
    expected = {
        "Amit Daryanani",
        "Michael Ng",
        "Ben Reitzes",
        "Erik Woodring",
        "Aaron Rakers",
        "Wamsi Mohan",
        "Samik Chatterjee",
    }
    assert names == expected


def test_gold_respondent_name_and_role_match_answer_segment_metadata(gold):
    """Pin respondent identity to held transcript metadata, not biography."""
    with gzip.open(FIXTURE_DIR / "aapl_fy2026_q3.json.gz") as f:
        segs = json.load(f)["segments"]
    for ex in gold["exchanges"]:
        for span in ex["answer_spans"]:
            seg = segs[span["segment_index"]]
            assert span["speaker"] == seg["speaker"]
            assert span["role"] == seg["role"]
        for resp in ex["respondents"]:
            assert any(
                span["speaker"] == resp["name"] and span["role"] == resp["role"]
                for span in ex["answer_spans"]
            ), f"exchange {ex['ordinal']}: {resp} not in answer segment metadata"
    ternus_span = segs[94]
    assert ternus_span["speaker"] == "John Ternus"
    assert ternus_span["role"] == "CEO"
    gold_ternus = next(
        r for r in gold["exchanges"][5]["respondents"] if r["name"] == "John Ternus"
    )
    assert gold_ternus["role"] == ternus_span["role"] == "CEO"


def test_adjudication_receipt_dual_session():
    path = REPO_ROOT / "research/earnings_intelligence/e3/gold/aapl_fy2026_q3_adjudication_receipt.json"
    receipt = json.loads(path.read_bytes())
    assert receipt["adjudication_method"] == "dual_session"
    assert receipt["gold_sha256"] == GOLD_SHA256
    assert receipt["gold_correction"] is True
    assert receipt["pass_b"]["pass_kind"] == "independent_pre_inference_dual_adjudication"
    assert receipt["pass_a"]["boundary_segments"] == EXPECTED_OPERATOR_INTRO_SEGMENTS
    assert receipt["pass_b"]["boundary_segments"] == EXPECTED_OPERATOR_INTRO_SEGMENTS
    assert receipt["reconciliation"]["boundaries_agree"] is True
    assert receipt["reconciliation"]["respondents_law"] == "answer_turn"
    assert receipt["reconciliation"]["john_ternus_role"]["pinned"] == "CEO"
    assert receipt["source"]["assumed_from_handoff"] is False
    assert receipt["reconciliation"]["superseded_gold_sha256"] == SUPERSEDED_GOLD_SHA_V1


def test_qwen_resolves_worker_override_before_yaml(monkeypatch):
    from engine.company_intelligence.e3_shadow_compiler import resolve_qwen_openai_compat_cfg
    monkeypatch.delenv("EARNINGS_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("EARNINGS_LLM_MODEL", raising=False)
    cfg = resolve_qwen_openai_compat_cfg(
        REPO_ROOT, {"base_url": "http://localhost:11434/v1", "model": "qwen3.5:9b"}
    )
    assert cfg["base_url"] == "http://127.0.0.1:11435/v1"
    assert cfg["model"] == "qwen3.5:9b"
    assert cfg["base_url_source"] == "earnings_worker_plist"
    monkeypatch.setenv("EARNINGS_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("EARNINGS_LLM_MODEL", "qwen3.5:9b")
    env_cfg = resolve_qwen_openai_compat_cfg(
        REPO_ROOT, {"base_url": "http://localhost:11434/v1", "model": "placeholder"}
    )
    assert env_cfg["base_url_source"] == "env"
    assert env_cfg["base_url"] == "http://127.0.0.1:9/v1"


def _gold_cand(gold, ordinal=0, **overrides):
    from engine.company_intelligence.e3_shadow_compiler import gold_exchange_to_candidate
    cand = gold_exchange_to_candidate(gold["exchanges"][ordinal])
    cand.update(overrides)
    return cand


def test_validator_boundary_need_not_be_in_question_indexes(gold):
    """Closed schema lists boundary_segment_index separately from question indexes."""
    from engine.company_intelligence.e3_shadow_compiler import (
        load_transcript_segments, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=0)
    cand["question_segment_indexes"] = [33, 38]
    cand["boundary_segment_index"] = 32
    result = validate_candidate(cand, segs)
    assert result["ok"] is True


def test_validator_out_of_range_segment_rejected(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        load_transcript_segments, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, question_segment_indexes=[32, 999])
    result = validate_candidate(cand, segs)
    assert result["ok"] is False
    assert result["reason"] == "out_of_range_segment"


def test_validator_unknown_topic_rejected(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        load_transcript_segments, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, topics=["deflection"])
    result = validate_candidate(cand, segs)
    assert result["ok"] is False
    assert result["reason"] == "unknown_topic"


def test_validator_missing_or_wrong_type_rejected(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        load_transcript_segments, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    missing = _gold_cand(gold)
    del missing["affiliation"]
    assert validate_candidate(missing, segs)["reason"] == "invalid_schema"
    wrong = _gold_cand(gold)
    wrong["ordinal"] = "0"
    assert validate_candidate(wrong, segs)["reason"] == "invalid_schema"


def test_validator_foreign_event_field_rejected_never_trusted(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        load_transcript_segments, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, event_id="evt_foreign")
    result = validate_candidate(cand, segs)
    assert result["ok"] is False
    assert result["reason"] == "cross_event"


def test_correct_questioner_wrong_operator_boundary_is_not_tp(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=0)
    cand["boundary_segment_index"] = 42
    cand["question_segment_indexes"] = [42, 43]
    cand["answer_segment_indexes"] = [44]
    cand["respondents"] = [{"name": "Tim Cook", "role": "CEO"}]
    attempt = ModelAttempt(provider="test", model="test", status="ok", candidates=[cand])
    score = score_attempt(attempt, gold, segs)
    matched = [row for row in score["per_exchange"] if row["candidate_ordinal"] == 0]
    assert matched[0]["gold_ordinal"] == 1
    assert score["exchange_boundary_quality"]["tp"] == 1
    assert score["exchange_boundary_quality"]["recall"] <= 1.0


def test_duplicate_prediction_cannot_inflate_tp(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=0)
    dup = dict(cand)
    dup["ordinal"] = 99
    attempt = ModelAttempt(
        provider="test", model="test", status="ok", candidates=[cand, dup],
    )
    score = score_attempt(attempt, gold, segs)
    assert score["exchange_boundary_quality"]["tp"] == 1
    assert score["exchange_boundary_quality"]["recall"] <= 1.0
    assert score["exchange_boundary_quality"]["recall"] == pytest.approx(1.0 / 7)


def test_wrong_respondent_role_is_identity_error(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=5)
    cand["respondents"] = [
        {"name": "Tim Cook", "role": "CEO"},
        {"name": "John Ternus", "role": "SVP Hardware Engineering"},
    ]
    attempt = ModelAttempt(provider="test", model="test", status="ok", candidates=[cand])
    score = score_attempt(attempt, gold, segs)
    row = next(r for r in score["per_exchange"] if r["gold_ordinal"] == 5)
    assert "respondent_roles" in row["identity_errors"]
    ident = score["identity_role_availability"]
    assert ident["respondent_role_order_match_rate"] == 0.0


def test_altered_source_bytes_fail_replay(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        gold_exchange_to_candidate, validate_candidate,
    )
    cand = gold_exchange_to_candidate(gold["exchanges"][0])
    mutated = [{"text": "", "speaker": "x", "role": "y"} for _ in range(108)]
    result = validate_candidate(cand, mutated)
    assert result["ok"] is False
    assert result["reason"] == "span_replay_failure"


def test_valid_synthetic_candidate_is_shadow_admitted_with_real_replay(gold):
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt, validate_candidate,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=0)
    admitted = validate_candidate(cand, segs)
    assert admitted["ok"] is True
    attempt = ModelAttempt(provider="test", model="test", status="ok", candidates=[cand])
    score = score_attempt(attempt, gold, segs)
    assert score["accepted_count"] == 1
    assert score["accepted_span_replay_count"] == 1
    assert score["source_span_replay_success_pct"] == 100.0
    assert score["n_model_candidates"] == 1
    assert score["exchange_boundary_quality"]["tp"] == 1


def test_hardcoded_false_green_cannot_return():
    """If the old 100.0 / 0.0 / accepted_count=0 / all_pass=true path is restored, fail."""
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt,
    )
    segs = load_transcript_segments(REPO_ROOT)
    gold = json.loads(GOLD_PATH.read_bytes())
    empty = score_attempt(
        ModelAttempt(provider="t", model="t", status="provider_unavailable"),
        gold,
        segs,
    )
    assert empty["hard_gates"]["status"] == "NOT_EXERCISED"
    assert empty["hard_gates"]["all_pass"] is not True
    assert empty["source_span_replay_success_pct"] != 100.0
    assert empty["accepted_count"] == 0


def test_rejected_unsupported_is_not_accepted_unsupported(gold):
    """A validator rejection is not an accepted-object hard-gate violation."""
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, load_transcript_segments, score_attempt, validate_candidates,
    )
    segs = load_transcript_segments(REPO_ROOT)
    cand = _gold_cand(gold, ordinal=0)
    mutated = [{"text": "", "speaker": "x", "role": "y"} for _ in range(108)]
    validated = validate_candidates([cand], mutated)
    assert validated["unsupported_rejected"] == 1
    assert validated["accepted_unsupported"] == 0
    assert validated["accepted_count"] == 0
    attempt = ModelAttempt(provider="t", model="t", status="ok", candidates=[cand])
    score = score_attempt(attempt, gold, mutated)
    assert score["unsupported_rejected"] == 1
    assert score["accepted_unsupported"] == 0
    assert score["hard_gates"]["accepted_unsupported"] == 0
    assert score["hard_gates"]["status"] == "NOT_EXERCISED"


def test_moved_current_marker_does_not_rewrite_calibration_gold():
    """Later current-marker generations keep source-SHA calibration; gold stays frozen."""
    from engine.company_intelligence.e3_shadow_compiler import (
        FROZEN_EXHIBIT_SHA,
        FROZEN_GOLD_SHA,
        FROZEN_TRANSCRIPT_SHA,
        PINNED_GENERATION_ID,
        PINNED_WORKSPACE_SHA,
        classify_live_workspace_shas,
    )

    moved = classify_live_workspace_shas(
        available=True,
        generation_id="d7b994675fe59d0181643b8b",
        workspace_sha="d360e1017dea2bbec7d44c37f48cf0565eb4f663edc99f1af00ce1e38dd642c5",
        release_sha=FROZEN_EXHIBIT_SHA,
        transcript_sha=FROZEN_TRANSCRIPT_SHA,
    )
    assert moved["source_shas_match"] is True
    assert moved["matches_frozen_fixtures"] is True
    assert moved["current_marker_is_calibration_generation"] is False
    assert moved["calibration_generation_id"] == PINNED_GENERATION_ID
    assert moved["calibration_workspace_sha256"] == PINNED_WORKSPACE_SHA
    assert hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest() == FROZEN_GOLD_SHA

    drifted = classify_live_workspace_shas(
        available=True,
        generation_id=PINNED_GENERATION_ID,
        workspace_sha=PINNED_WORKSPACE_SHA,
        release_sha="0" * 64,
        transcript_sha=FROZEN_TRANSCRIPT_SHA,
    )
    assert drifted["source_shas_match"] is False
    assert drifted["matches_frozen_fixtures"] is False


def test_run_e3a_eval_hermetic_end_to_end(monkeypatch, tmp_path):
    """Full run_e3a_eval path through telemetry + receipt write.

    Must fail against 3cadd220 (_bounded_telemetry_proof use-before-assignment).
    """
    import engine.company_intelligence.e3_shadow_compiler as e3

    live = {
        "available": True,
        "reader": "engine.neuralweb.company_intelligence_reader.read_event_workspace",
        "generation_id": "later-current-marker",
        "workspace_sha256": "0" * 64,
        "workspace_url": None,
        "marker_url": None,
        "release_source_sha256": e3.FROZEN_EXHIBIT_SHA,
        "transcript_source_sha256": e3.FROZEN_TRANSCRIPT_SHA,
        "source_shas_match": True,
        "current_marker_is_calibration_generation": False,
        "matches_frozen_fixtures": True,
        "assumed_from_handoff": False,
        "note": "current-marker generation moved; gold not rewritten",
    }
    monkeypatch.setattr(e3, "verify_live_workspace_shas", lambda: live)

    qwen = e3.ModelAttempt(
        provider="openai_compat",
        model="qwen3.5:9b",
        status="ok",
        endpoint_class="loopback",
        base_url_source="earnings_worker_plist",
        est_cost_usd=0.0,
        preflight={"status": "ok", "endpoint_class": "loopback"},
    )
    gold = json.loads(GOLD_PATH.read_bytes())
    haiku = e3.ModelAttempt(
        provider="oauth",
        model="claude-haiku-4-5",
        status="ok",
        is_comparator=True,
        candidates=[e3.gold_exchange_to_candidate(gold["exchanges"][0])],
        input_tokens=12,
        output_tokens=8,
        est_cost_usd=0.01,
        comparator_note="benchmark-only",
        preflight={"comparator_freeze": {"status": "frozen"}},
    )
    monkeypatch.setattr(e3, "_attempt_qwen", lambda prompt, root: qwen)
    monkeypatch.setattr(e3, "_attempt_comparator", lambda prompt, root, run_id="": haiku)
    monkeypatch.setattr(
        e3,
        "freeze_comparator_choice",
        lambda root, run_id="": {
            "freeze": {"status": "frozen", "model": "claude-haiku-4-5", "providers": []},
            "providers": [],
            "cfg": {},
        },
    )
    monkeypatch.setattr(e3, "ledger_attempt", lambda *a, **k: None)

    receipt_path = tmp_path / "eval_receipt.json"
    monkeypatch.setattr(e3, "EVAL_RECEIPT_PATH", receipt_path)

    def _shards(run_id: str, repo_root: Path) -> dict[str, str]:
        health = tmp_path / f"provider_health_{run_id}.jsonl"
        health.write_text("", encoding="utf-8")
        return {
            "ai_costs_shard": f"e3a-test-{run_id}",
            "provider_health_path": str(health),
        }

    monkeypatch.setattr(e3, "_enable_eval_shards", _shards)

    receipt = e3.run_e3a_eval(REPO_ROOT)
    assert receipt_path.is_file(), "eval receipt must be written"
    bindings = receipt.get("bindings") or receipt
    for key in (
        "git_head",
        "compiler_sha256",
        "system_prompt_sha256",
        "gold_sha256",
        "taxonomy_hash",
        "run_id",
    ):
        assert bindings.get(key), f"receipt missing binding {key}"
    assert receipt["bindings"]["gold_sha256"] == hashlib.sha256(
        GOLD_PATH.read_bytes()
    ).hexdigest()
    assert receipt["bindings"]["generation_id"] == e3.PINNED_GENERATION_ID
    assert receipt["bindings"]["workspace_sha256"] == e3.PINNED_WORKSPACE_SHA
    proof = receipt["telemetry_proof"]
    assert proof["lane"] == "earnings_event_compiler"
    assert receipt["model_attempts"]["qwen"]["n_candidates"] == 0
    assert receipt["model_attempts"]["comparator"]["n_candidates"] == 1
    assert receipt["summary"]["e3b_auto_unlocked"] is False


def test_local_qwen_cost_is_zero_not_unpriced(tmp_path, monkeypatch):
    """Loopback Ollama transport is local/free $0.00, not an unpriced metered call."""
    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    from engine.company_intelligence.e3_shadow_compiler import (
        ModelAttempt, ledger_attempt,
    )
    attempt = ModelAttempt(
        provider="openai_compat",
        model="qwen3.5:9b",
        endpoint_class="loopback",
        status="ok",
        est_cost_usd=0.0,
        input_tokens=10,
        output_tokens=2,
    )
    ledger_attempt(attempt, tmp_path, "abc123")
    ledger = tmp_path / "data/ai_costs/usage.jsonl"
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert row["est_cost_usd"] == 0.0
    assert row["cost_basis"] == "local"
    assert row["provider"] == "openai_compat"
    assert row["cycle_id"] == "abc123"
    assert row["lane"] == "earnings_event_compiler"


@pytest.fixture
def qwen_observation_repo(tmp_path, monkeypatch):
    import engine.company_intelligence.e3_shadow_compiler as e3

    (tmp_path / "config").mkdir()
    (tmp_path / "config/earnings_qual.yml").write_text(
        "openai_compat:\n  base_url: http://127.0.0.1:11435/v1\n"
        "  model: qwen3.5:9b\n  max_tokens: 1200\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(e3, "resolve_qwen_openai_compat_cfg",
                        lambda root, cfg: {**cfg, "base_url_source": "fixture"})
    monkeypatch.setattr(e3, "preflight_qwen_endpoint", lambda cfg: {"status": "ok"})
    monkeypatch.setattr(e3, "_record_health", lambda **kwargs: None)
    return tmp_path


def test_qwen_attempt_uses_one_detailed_call_and_actual_observation(
    qwen_observation_repo, monkeypatch,
):
    import requests
    import engine.company_intelligence.e3_shadow_compiler as e3

    sent = []
    class Response:
        status_code = 200
        def json(self):
            return {"model": "actual-qwen-serving-id", "choices": [{"message": {"content": "[]"}}],
                    "usage": {"prompt_tokens": 17, "completion_tokens": 0}}

    def post(url, **kwargs):
        sent.append((url, kwargs))
        return Response()

    monkeypatch.setattr(requests, "post", post)
    attempt = e3._attempt_qwen("return JSON", qwen_observation_repo)
    assert requests.post is post
    assert len(sent) == 1
    payload = sent[0][1]["json"]
    assert payload == {
        "model": "qwen3.5:9b",
        "messages": [{"role": "system", "content": e3.SYSTEM_PROMPT},
                     {"role": "user", "content": "return JSON\n\n/no_think"}],
        "max_tokens": 4096, "temperature": 0, "stream": False, "reasoning_effort": "none",
    }
    assert attempt.status == "ok"
    assert attempt.model == "qwen3.5:9b"
    assert attempt.served_model == "actual-qwen-serving-id"
    assert attempt.http_status == 200 and attempt.error_kind is None
    assert (attempt.input_tokens, attempt.output_tokens) == (17, 0)
    assert attempt.observed_usage["total_tokens"] is None


def test_qwen_attempt_does_not_resend_after_helper_exception(qwen_observation_repo, monkeypatch):
    import engine.company_intelligence.e3_shadow_compiler as e3
    from engine import earnings_qual

    calls = []
    def after_send(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("response observation failed after simulated send")

    monkeypatch.setattr(earnings_qual, "_call_openai_compat_detailed", after_send)
    attempt = e3._attempt_qwen("request", qwen_observation_repo)
    assert len(calls) == 1
    assert attempt.status == "provider_unavailable"
    assert attempt.degraded_reason == "exception: RuntimeError"
    assert attempt.input_tokens is None and attempt.output_tokens is None
    assert attempt.served_model is None


def test_qwen_concurrent_observations_do_not_intercept_unrelated_requests(
    qwen_observation_repo, monkeypatch,
):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import requests
    import engine.company_intelligence.e3_shadow_compiler as e3

    barrier = threading.Barrier(3)
    sent = []
    lock = threading.Lock()
    class Response:
        status_code = 200
        def __init__(self, name):
            self.name = name
        def json(self):
            n = {"first": 11, "second": 22, "unrelated": 99}[self.name]
            return {"model": "served-" + self.name,
                    "choices": [{"message": {"content": json.dumps({"name": self.name})}}],
                    "usage": {"input_tokens": n, "output_tokens": 1}}

    def post(url, **kwargs):
        assert requests.post is post
        payload = kwargs["json"]
        name = payload.get("outside") or payload["messages"][1]["content"].split("\n")[0]
        with lock:
            sent.append(name)
        barrier.wait(timeout=10)
        return Response(name)

    monkeypatch.setattr(requests, "post", post)
    with ThreadPoolExecutor(max_workers=3) as workers:
        first = workers.submit(e3._attempt_qwen, "first", qwen_observation_repo)
        second = workers.submit(e3._attempt_qwen, "second", qwen_observation_repo)
        unrelated = workers.submit(requests.post, "https://fixture.invalid/unrelated",
                                   json={"outside": "unrelated"})
        a, b, c = first.result(timeout=15), second.result(timeout=15), unrelated.result(timeout=15)
    assert sorted(sent) == ["first", "second", "unrelated"]
    assert requests.post is post
    assert (a.served_model, a.input_tokens) == ("served-first", 11)
    assert (b.served_model, b.input_tokens) == ("served-second", 22)
    assert c.json()["model"] == "served-unrelated"
    assert a.observed_usage is not b.observed_usage


def test_qwen_empty_answer_retains_observation_without_acceptance(qwen_observation_repo, monkeypatch):
    import requests
    import engine.company_intelligence.e3_shadow_compiler as e3

    class Response:
        status_code = 200
        def json(self):
            return {"model": "actual-empty-model", "choices": [],
                    "usage": {"prompt_tokens": 13, "completion_tokens": 4}}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())
    attempt = e3._attempt_qwen("empty", qwen_observation_repo)
    assert attempt.status == "provider_unavailable" and attempt.raw_response is None
    assert attempt.error_kind == "empty" and attempt.http_status == 200
    assert attempt.served_model == "actual-empty-model"
    assert (attempt.input_tokens, attempt.output_tokens) == (13, 4)


def test_qwen_unknown_usage_is_not_zero_in_existing_ledger(tmp_path, monkeypatch):
    from engine.company_intelligence.e3_shadow_compiler import ModelAttempt, ledger_attempt

    monkeypatch.delenv("AI_COSTS_SHARD", raising=False)
    attempt = ModelAttempt(provider="openai_compat", model="requested",
                           endpoint_class="remote", input_tokens=None,
                           output_tokens=None, est_cost_usd=None)
    ledger_attempt(attempt, tmp_path, "unknown-observation")
    row = json.loads((tmp_path / "data/ai_costs/usage.jsonl").read_text().splitlines()[0])
    assert row["input_tokens"] is None and row["output_tokens"] is None
    assert row["est_cost_usd"] is None and row["cost_basis"] == "unknown"


# Selected E3 composition: real C/auth/client/B/picker/A/H with synthetic upstream.
import copy
import os
import shutil
from dataclasses import replace
from unittest.mock import Mock, patch

from lib.ai_costs import record_usage as _E3_REAL_RECORD_USAGE
from tests.test_fabric_application_binding import binding  # noqa: F401
from tests.test_fabric_exact_scoped_model_composition import exact, exact_native  # noqa: F401


@pytest.fixture
def e3_fabric(exact, monkeypatch):
    from engine.company_intelligence import e3_shadow_compiler as e3
    from engine import llm_auth as fabric_auth
    from lib import ai_costs
    monkeypatch.setattr(ai_costs, "record_usage", _E3_REAL_RECORD_USAGE)
    for capability in exact.manifest["capabilities"]:
        if capability["capability_id"] == exact.batch["capability_id"]:
            capability["allowed_lanes"].append(e3.LANE)
    exact.save()
    for relative in (
        Path("tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm"),
        Path("tests/fixtures/company_intelligence/aapl_fy2026_q3.json.gz"),
        e3.GOLD_PATH,
    ):
        destination = exact.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, destination)
    live = {"available": True, "source_shas_match": True,
        "release_source_sha256": e3.FROZEN_EXHIBIT_SHA,
        "transcript_source_sha256": e3.FROZEN_TRANSCRIPT_SHA,
        "reader": "synthetic_current_workspace_observation"}
    monkeypatch.setattr(e3, "verify_live_workspace_shas", lambda: copy.deepcopy(live))
    gold_document = json.loads(GOLD_PATH.read_bytes())
    candidate = e3.gold_exchange_to_candidate(gold_document["exchanges"][0])
    exact.native.response["output"][0]["content"][0]["text"] = json.dumps([candidate])
    for name in ("_attempt_qwen", "_attempt_comparator", "freeze_comparator_choice",
                 "_enable_eval_shards"):
        monkeypatch.setattr(e3, name, Mock(side_effect=AssertionError("selected legacy effect: " + name)))
    monkeypatch.setenv("AI_COSTS_SHARD", "e3_fabric_test")
    exact.e3 = e3
    exact.auth = fabric_auth
    exact.candidate = candidate
    return exact


@pytest.mark.skipif(not os.environ.get("MM_FABRIC_GATEWAY_SOURCE_ROOT"),
                    reason="paired exact-scoped Mastermind source required")
class TestFabricE3OriginalComposition:
    def test_exact_request_answer_accounting_close_and_selectorless_warm_read(self, e3_fabric, monkeypatch):
        from engine import provider_production_modes as owner
        from lib import ai_costs
        state = e3_fabric
        before_environment = dict(os.environ)
        with patch.object(ai_costs, "record_usage", wraps=ai_costs.record_usage) as ledger:
            result = state.e3.run_e3a_eval(state.root)
            assert ledger.call_count == 1
            assert ledger.call_args.kwargs["provider"] == "bailian"
            assert ledger.call_args.kwargs["model"] == "qwen3.8-flash"
            assert ledger.call_args.kwargs["est_cost_usd"] is None
            assert ledger.call_args.kwargs["cost_basis"] == "unknown"
        assert dict(os.environ) == before_environment
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "complete"
        assert leg["ledger"] == {"phase": "complete", "ack": True}
        assert leg["close"]["outcome"]["closed"] is True
        assert result["model_attempts"]["qwen"]["n_candidates"] == 1
        assert result["model_attempts"]["comparator"]["phase"] == "unattempted"
        assert result["model_attempts"]["comparator"]["requested_model"] == "claude-haiku-4-5"
        assert result["summary"]["usefulness_bar_decision"] == "refusal_n7_too_small"
        assert not any(result["summary"][key] for key in
                       ("e3b_auto_unlocked", "event_workspace_v1_advanced", "r2_written"))
        assert len(state.native.logical_posts) == len(state.native.rows("leases")) == 1
        assert state.native.rows("leases")[0]["state"] == "released"
        route = leg["observation"]["routing"]
        request = state.native.rows("application_requests")[0]
        assert route["requested_model"] == route["selected_model"] == "qwen3.8-flash"
        assert route["pool"] == "bailian"
        assert route["routed_request_digest"] is None
        assert request["request_digest"] == leg["request_digest"] == route["request_digest"]
        wire = json.loads(state.native.logical_posts[0].body)
        assert wire["model"] == "qwen3.8-flash"
        assert wire["max_output_tokens"] == state.e3.EXTRACTION_MAX_TOKENS
        assert type(wire["temperature"]) is int and wire["temperature"] == 0
        assert wire["reasoning"] == {"effort": "none"} and wire["stream"] is False
        original = result[state.e3._FABRIC_E3_KEY]
        user = state.e3._build_user_prompt(original["input"]["segments"]) + "\n\n/no_think"
        assert original["input"]["request"]["messages"] == [{"role": "user", "content": user}]
        assert user.count("/no_think") == 1
        assert (leg["actual_observation"]["input_tokens"],
                leg["actual_observation"]["output_tokens"]) == (11, 7)
        assert (result["model_attempts"]["qwen"]["input_tokens"],
                result["model_attempts"]["qwen"]["output_tokens"]) == (11, 7)
        monkeypatch.delenv(state.auth.APPLICATION_MODE_ENV)
        with patch.object(owner, "make_application_fabric_factory",
                          side_effect=AssertionError("warm discovery")), \
             patch.object(ai_costs, "record_usage", side_effect=AssertionError("warm ledger")):
            warm = state.e3.run_e3a_eval(state.root)
        assert warm == result
        assert len(state.native.logical_posts) == 1

    def test_legacy_receipt_is_retained_as_distinct_evidence(self, e3_fabric):
        from engine import catalyst_tone as cache
        state = e3_fabric
        legacy = {"schema": "e3a_eval_receipt.v1", "run_id": "legacy-original",
                  "model_attempts": {"qwen": {"model": "qwen3.5:9b", "status": "ok"}}}
        cache._cache_save(state.root / state.e3.EVAL_RECEIPT_PATH, legacy)
        result = state.e3.run_e3a_eval(state.root)
        original = result[state.e3._FABRIC_E3_KEY]
        assert original["legacy_receipt"] == legacy
        assert original["legacy_digest"] == state.e3._fabric_e3_hash(legacy)
        assert result["model_attempts"]["qwen"]["requested_model"] == "qwen3.8-flash"
        assert len(state.native.logical_posts) == 1

    def test_unqualified_capability_has_no_allocation_or_fallback(self, e3_fabric):
        state = e3_fabric
        for capability in state.manifest["capabilities"]:
            if capability["capability_id"] == state.batch["capability_id"]:
                capability["allowed_lanes"].remove(state.e3.LANE)
        state.save()
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "unattempted"
        assert leg["reason"] == "fabric_qualification_unavailable"
        assert state.native.logical_posts == state.native.rows("leases") == []
        assert leg["ledger"] == {"phase": "unattempted", "ack": None}

    @staticmethod
    def _delivery_fault(state, monkeypatch, change):
        handler = state.native.server.RequestHandlerClass
        original = handler._application_delivery
        def deliver(instance, observed):
            body = json.loads(observed.body)
            change(body)
            return original(instance, replace(observed, body=json.dumps(body).encode()))
        monkeypatch.setattr(handler, "_application_delivery", deliver)

    @pytest.mark.parametrize("text", ["", "not-json", "{}", '[{"ordinal":0,"ordinal":1}]'])
    def test_invalid_extraction_retains_actual_usage_without_retry(self, e3_fabric, text, monkeypatch):
        from engine import provider_production_modes as owner
        state = e3_fabric
        state.native.response["output"][0]["content"][0]["text"] = text
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "held" and leg["answer_status"] != "ok"
        assert leg["actual_observation"]["input_tokens"] == 11
        assert leg["actual_observation"]["output_tokens"] == 7
        assert result["model_attempts"]["qwen"]["n_candidates"] == 0
        monkeypatch.delenv(state.auth.APPLICATION_MODE_ENV)
        with patch.object(owner, "make_application_fabric_factory",
                          side_effect=AssertionError("invalid original rebound")):
            assert state.e3.run_e3a_eval(state.root) == result
        assert len(state.native.logical_posts) == 1

    def test_empty_array_is_valid_empty_extraction(self, e3_fabric):
        state = e3_fabric
        state.native.response["output"][0]["content"][0]["text"] = "[]"
        result = state.e3.run_e3a_eval(state.root)
        assert result[state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "complete"
        assert result["model_attempts"]["qwen"]["n_candidates"] == 0
        assert result["summary"]["e3b_auto_unlocked"] is False

    @pytest.mark.parametrize("kind", ["length", "tool_calls"])
    def test_incomplete_or_tool_delivery_cannot_become_extraction(self, e3_fabric, monkeypatch, kind):
        state = e3_fabric
        def change(body):
            choice = body["choices"][0]
            choice["finish_reason"] = kind
            if kind == "tool_calls":
                choice["message"]["tool_calls"] = [{
                    "id": "unexpected-tool", "type": "function",
                    "function": {"name": "unexpected", "arguments": "{}"}}]
        self._delivery_fault(state, monkeypatch, change)
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "held" and leg["answer_status"] != "ok"
        assert leg["actual_observation"]["input_tokens"] == 11
        assert result["model_attempts"]["qwen"]["n_candidates"] == 0
        assert len(state.native.logical_posts) == 1

    def test_served_model_mismatch_keeps_actual_model_and_counts(self, e3_fabric):
        state = e3_fabric
        state.native.response["model"] = "qwen3.8-max"
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "held" and leg["answer_status"] != "ok"
        assert leg["observation"]["routing"]["selected_model"] == "qwen3.8-flash"
        assert leg["actual_observation"]["serving_model"] == "qwen3.8-max"
        assert result["model_attempts"]["qwen"]["served_model"] == "qwen3.8-max"
        assert result["model_attempts"]["qwen"]["input_tokens"] == 11
        assert len(state.native.logical_posts) == 1

    @pytest.mark.parametrize("partial", [False, True])
    def test_bad_route_retains_correlated_actual_usage_without_pool_claim(self, e3_fabric, monkeypatch, partial):
        state = e3_fabric
        def change(body):
            body["application"]["routing"] = []
            if partial:
                body["usage"]["completion_tokens"] = None
                body["application"]["usage"]["output_tokens"] = None
        self._delivery_fault(state, monkeypatch, change)
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        actual = leg["actual_observation"]
        assert leg["phase"] == "held" and leg["observation"] is None
        assert actual["request_id"] == leg["request_id"]
        assert actual["serving_model"] == "qwen3.8-flash"
        assert actual["input_tokens"] == 11
        assert actual["output_tokens"] == (None if partial else 7)
        assert leg["usage"]["usage_state"] == "unknown"
        assert leg["usage"]["completed_input_tokens"] == (0 if partial else 11)
        assert result["model_attempts"]["qwen"]["provider"] == "unknown"
        assert result["model_attempts"]["qwen"]["input_tokens"] == 11
        assert result["model_attempts"]["qwen"]["output_tokens"] == (None if partial else 7)
        assert result["model_attempts"]["qwen"]["est_cost_usd"] is None
        assert state.e3.run_e3a_eval(state.root) == result
        assert len(state.native.logical_posts) == 1

    def test_reentrant_reader_observes_claim_without_rebinding(self, e3_fabric, monkeypatch):
        from engine import provider_production_modes as owner
        state = e3_fabric
        nested = []
        def observe(body):
            if not nested:
                with patch.object(owner, "make_application_fabric_factory",
                                  side_effect=AssertionError("duplicate binding")):
                    nested.append(state.e3.run_e3a_eval(state.root))
        self._delivery_fault(state, monkeypatch, observe)
        result = state.e3.run_e3a_eval(state.root)
        assert nested[0][state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "claimed"
        assert result[state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "complete"
        assert len(state.native.logical_posts) == len(state.native.rows("leases")) == 1

    def test_crash_after_claim_cannot_rebind_after_selector_removal(self, e3_fabric, monkeypatch):
        from engine import provider_production_modes as owner
        state = e3_fabric
        monkeypatch.setattr(state.auth, "build_fabric_provider",
                            Mock(side_effect=KeyboardInterrupt("after durable claim")))
        with pytest.raises(KeyboardInterrupt):
            state.e3.run_e3a_eval(state.root)
        monkeypatch.delenv(state.auth.APPLICATION_MODE_ENV)
        with patch.object(owner, "make_application_fabric_factory",
                          side_effect=AssertionError("original rediscovery")):
            restored = state.e3.run_e3a_eval(state.root)
        assert restored[state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "claimed"
        assert state.native.logical_posts == state.native.rows("leases") == []

    def test_cancellation_after_real_reply_closes_once_and_does_not_resend(self, e3_fabric, monkeypatch):
        state = e3_fabric
        original_build = state.auth.build_fabric_provider
        def build(*args, **kwargs):
            provider = original_build(*args, **kwargs)
            original_create = provider["client"].messages.create
            def cancelled(**request):
                original_create(**request)
                raise KeyboardInterrupt("after actual reply")
            provider["client"].messages.create = cancelled
            return provider
        monkeypatch.setattr(state.auth, "build_fabric_provider", build)
        with patch.object(state.auth, "close_fabric_provider",
                          wraps=state.auth.close_fabric_provider) as close:
            with pytest.raises(KeyboardInterrupt):
                state.e3.run_e3a_eval(state.root)
            assert close.call_count == 1
            restored = state.e3.run_e3a_eval(state.root)
            assert close.call_count == 1
        assert restored[state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "claimed"
        assert len(state.native.logical_posts) == 1
        assert state.native.rows("leases")[0]["state"] == "released"

    def test_answer_persistence_failure_closes_original_once(self, e3_fabric, monkeypatch):
        from engine import catalyst_tone as cache
        state = e3_fabric
        save = cache._cache_save
        def refuse_observation(path, document):
            if document.get(state.e3._FABRIC_E3_KEY, {}).get("qwen", {}).get("phase") == "observed":
                raise OSError("original answer storage unavailable")
            return save(path, document)
        monkeypatch.setattr(cache, "_cache_save", refuse_observation)
        with patch.object(state.auth, "close_fabric_provider",
                          wraps=state.auth.close_fabric_provider) as close:
            with pytest.raises(OSError, match="storage unavailable"):
                state.e3.run_e3a_eval(state.root)
            assert close.call_count == 1
            restored = state.e3.run_e3a_eval(state.root)
            assert close.call_count == 1
        assert restored[state.e3._FABRIC_E3_KEY]["qwen"]["phase"] == "claimed"
        assert len(state.native.logical_posts) == 1
        assert state.native.rows("leases")[0]["state"] == "released"

    def test_lost_close_ack_holds_original_without_reclosing(self, e3_fabric, monkeypatch):
        state = e3_fabric
        original_close = state.auth.close_fabric_provider
        calls = []
        def lost_ack(provider):
            calls.append(provider)
            original_close(provider)
            provider["_fabric_close"] = {"disposition": "effect_unknown", "closed": False,
                                        "effect_unknown": True, "attempted": True}
        monkeypatch.setattr(state.auth, "close_fabric_provider", lost_ack)
        result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == "held" and leg["reason"] == "fabric_close_unknown"
        assert leg["answer_status"] == "ok" and leg["answer"]
        assert result["model_attempts"]["qwen"]["n_candidates"] == 0
        assert state.e3.run_e3a_eval(state.root) == result
        assert len(calls) == len(state.native.logical_posts) == 1

    @pytest.mark.parametrize("crash", [False, True])
    def test_ambiguous_ledger_append_never_reappends(self, e3_fabric, monkeypatch, crash):
        from lib import ai_costs
        state = e3_fabric
        calls = []
        def lost_ack(**kwargs):
            calls.append(kwargs)
            assert _E3_REAL_RECORD_USAGE(**kwargs) is True
            if crash:
                raise KeyboardInterrupt("after ledger append")
            return False
        monkeypatch.setattr(ai_costs, "record_usage", lost_ack)
        if crash:
            with pytest.raises(KeyboardInterrupt):
                state.e3.run_e3a_eval(state.root)
            result = state.e3.run_e3a_eval(state.root)
        else:
            result = state.e3.run_e3a_eval(state.root)
        leg = result[state.e3._FABRIC_E3_KEY]["qwen"]
        assert leg["phase"] == ("closed" if crash else "held")
        assert leg["ledger"]["phase"] == ("intent" if crash else "unknown")
        assert state.e3.run_e3a_eval(state.root) == result
        assert len(calls) == len(state.native.logical_posts) == 1

    @pytest.mark.parametrize("tamper", ["closed_without_reply", "null_completed", "known_totals", "request_id"])
    def test_saved_receipt_corruption_refuses_before_effects(self, e3_fabric, monkeypatch, tamper):
        from engine import catalyst_tone as cache, provider_production_modes as owner
        from lib import ai_costs
        state = e3_fabric
        if tamper == "closed_without_reply":
            with patch.object(state.auth, "build_fabric_provider",
                              side_effect=KeyboardInterrupt("after claim")):
                with pytest.raises(KeyboardInterrupt):
                    state.e3.run_e3a_eval(state.root)
        else:
            state.e3.run_e3a_eval(state.root)
        path = state.root / state.e3.EVAL_RECEIPT_PATH
        original = copy.deepcopy(cache._cache_read(path)[state.e3._FABRIC_E3_KEY])
        leg = original["qwen"]
        if tamper == "closed_without_reply":
            leg["phase"] = "closed"
        elif tamper == "null_completed":
            leg["usage"]["completed_input_tokens"] = None
        elif tamper == "known_totals":
            leg["usage"]["input_tokens"] += 1
        else:
            leg["actual_observation"]["request_id"] += ":different"
        cache._cache_save(path, state.e3._fabric_e3_document(original))
        count = len(state.native.logical_posts)
        with patch.object(owner, "make_application_fabric_factory",
                          side_effect=AssertionError("corrupt original rebound")), \
             patch.object(ai_costs, "record_usage", side_effect=AssertionError("corrupt original ledger")):
            with pytest.raises(ValueError, match="fabric_e3_"):
                state.e3.run_e3a_eval(state.root)
        assert len(state.native.logical_posts) == count

    def test_legacy_lock_prevents_selected_takeover_before_native_effect(self, e3_fabric, monkeypatch):
        state = e3_fabric
        e3 = state.e3
        monkeypatch.delenv(state.auth.APPLICATION_MODE_ENV)
        competing = []
        def legacy_call(prompt, root):
            monkeypatch.setenv(state.auth.APPLICATION_MODE_ENV, "shared_fabric")
            try:
                with pytest.raises(BlockingIOError) as refused:
                    e3.run_e3a_eval(root)
                competing.append(refused.value)
            finally:
                monkeypatch.delenv(state.auth.APPLICATION_MODE_ENV)
            return e3.ModelAttempt(provider="unknown", model="qwen3.5:9b", status="held")
        monkeypatch.setattr(e3, "_attempt_qwen", legacy_call)
        monkeypatch.setattr(e3, "_attempt_comparator", lambda *a, **k:
                            e3.ModelAttempt(provider="unknown", model="claude-haiku-4-5", status="held"))
        monkeypatch.setattr(e3, "freeze_comparator_choice", lambda *a, **k: {"freeze": {}, "providers": []})
        monkeypatch.setattr(e3, "_enable_eval_shards", lambda *a, **k: {})
        monkeypatch.setattr(e3, "_bounded_telemetry_proof", lambda *a, **k: {})
        monkeypatch.setattr(e3, "ledger_attempt", lambda *a, **k: False)
        result = e3.run_e3a_eval(state.root)
        assert result["schema"] == "e3a_eval_receipt.v1"
        assert competing and isinstance(competing[0], BlockingIOError)
        assert state.native.logical_posts == state.native.rows("leases") == []
