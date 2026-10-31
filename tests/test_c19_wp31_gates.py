"""C19 WP31 GATES lane — battery for scripts/c19_wp31_gates.py.

The property under test is DISCRIMINATION (mirroring the W5 §15.C/D battery
discipline of tests/test_entry_radar_w5_gates.py): every refusal case is
paired with a passing control built from the same fixture, so a gate that
stopped discriminating fails here rather than quietly becoming an
unconditional raise.

Fixtures are SYNTHETIC except the G-1 real-document test, which reads only
the frozen prereg markdown (research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md
— a document read, not label data).  Every ledger under test is a TrialLedger
on a pytest tmp_path file: data/trial_ledger.jsonl is never opened, written or
truncated here.  No network.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.trial_ledger import TrialLedger
from scripts import c19_wp31_gates as gates
from scripts import worktree_sparse

REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_PATH = REPO_ROOT / "research" / "C19_WP31_INCREMENTAL_INFORMATION_PREREG.md"

GOOD_COMMIT = "a" * 40
GOOD_SHA256 = "b" * 64

_AFTER_MARKER = (b"\n*(empty at freeze)*\n\n### A-1 2026-10-17 amendment\n"
                 b"some later, lawful, append-only amendment text\n")


def _doc_bytes(body: bytes = b"# WP31 prereg\n\nfrozen body text\n") -> bytes:
    """A synthetic prereg: frozen body, the §10 marker line, then amendments."""
    marker = gates.PREREG_FROZEN_MARKER.encode("utf-8")
    return body + marker + b", prospective only)\n" + _AFTER_MARKER


def _budget_line(*, family: str | None = None, n: int | None = None,
                 reason: str | None = None, kind: str = "declared_budget") -> str:
    return json.dumps({
        "kind": kind,
        "family": gates.FAMILY if family is None else family,
        "n": gates.BUDGET if n is None else n,
        "reason": (gates.registration_reason() if reason is None else reason),
        "config_hash": "deadbeef",
    })


def _other_family_line() -> str:
    """A pre-existing unrelated family — G-3's anti-truncation evidence."""
    return json.dumps({"family": "commodity_tsmom", "config_hash": "cafe",
                       "config": {"window": 63}})


# --------------------------------------------------------------------------- #
# G-1 — frozen prefix + doc hash, against the REAL prereg bytes
# --------------------------------------------------------------------------- #
def test_frozen_prefix_real_prereg_hashes_to_frozen_constant():
    doc = PREREG_PATH.read_bytes()
    prefix = gates.frozen_prefix(doc)
    assert hashlib.sha256(prefix).hexdigest() == gates.PREREG_DOC_SHA256
    # the prefix ends exactly at the end of the marker line, inclusive of \n
    assert prefix.endswith(b"\n")
    assert gates.PREREG_FROZEN_MARKER.encode("utf-8") in prefix
    last_line = prefix.splitlines()[-1]
    assert last_line.startswith(gates.PREREG_FROZEN_MARKER.encode("utf-8"))
    assert len(doc) > len(prefix)  # the real doc carries the amendments fence


def test_check_doc_hash_passes_on_real_prereg_bytes():
    receipt = gates.check_doc_hash(PREREG_PATH.read_bytes())
    assert receipt["gate"] == "G-1"
    assert gates.PREREG_DOC_SHA256 in receipt["detail"]


def test_check_doc_hash_refuses_on_one_byte_mutation_inside_prefix():
    doc = PREREG_PATH.read_bytes()
    idx = doc.find(gates.PREREG_FROZEN_MARKER.encode("utf-8"))
    mutated = doc[:50] + bytes([doc[50] ^ 0x01]) + doc[51:]
    assert idx > 50  # the mutation is inside the frozen prefix
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_doc_hash(mutated)
    assert ei.value.gate == "G-1"


def test_check_doc_hash_passes_on_appended_amendment_after_marker():
    doc = PREREG_PATH.read_bytes()
    amended = doc + b"\n### A-2 2026-11-01 amendment\nnew prospective rule\n"
    receipt = gates.check_doc_hash(amended)
    assert receipt["gate"] == "G-1"


def test_frozen_prefix_and_check_doc_hash_refuse_when_marker_absent():
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.frozen_prefix(b"# no fence here\njust text\n")
    assert ei.value.gate == "G-1"
    with pytest.raises(gates.WP31Refusal) as ei2:
        gates.check_doc_hash(b"# no fence here\njust text\n")
    assert ei2.value.gate == "G-1"


# --------------------------------------------------------------------------- #
# G-2 — merged ancestry (probe injected; monkeypatched constants never edited)
# --------------------------------------------------------------------------- #
def test_check_merged_ancestry_refuses_on_non_hex_commit(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", "not-a-sha")
    calls: list[str] = []
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_merged_ancestry(calls.append)
    assert ei.value.gate == "G-2"
    assert calls == []  # refused before the probe was even consulted


def test_check_merged_ancestry_refuses_when_probe_raises(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)

    def boom(_sha: str) -> bool:
        raise RuntimeError("git exploded")

    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_merged_ancestry(boom)
    assert ei.value.gate == "G-2"


def test_check_merged_ancestry_refuses_on_false(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_merged_ancestry(lambda _sha: False)
    assert ei.value.gate == "G-2"


def test_check_merged_ancestry_receipt_on_true(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    seen: list[str] = []

    def probe(sha: str) -> bool:
        seen.append(sha)
        return True

    receipt = gates.check_merged_ancestry(probe)
    assert receipt["gate"] == "G-2"
    assert seen == [GOOD_COMMIT]


# --------------------------------------------------------------------------- #
# G-3 — declared-budget admission incl. the mirrored anti-truncation block
# --------------------------------------------------------------------------- #
def test_check_budget_row_good_row_with_preexisting_families(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256} x"),
             _other_family_line()]
    receipt = gates.check_budget_row(lines)
    assert receipt["gate"] == "G-3"
    assert "1 pre-existing families" in receipt["detail"]


def test_check_budget_row_refuses_when_reason_lacks_commit(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(reason=f"doc_sha256={GOOD_SHA256} basis=itemized"),
             _other_family_line()]
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_budget_row(lines)
    assert ei.value.gate == "G-3"


def test_check_budget_row_refuses_when_reason_lacks_doc_sha(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(reason=f"w5_prereg={GOOD_COMMIT} basis=itemized"),
             _other_family_line()]
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_budget_row(lines)
    assert ei.value.gate == "G-3"


def test_check_budget_row_refuses_when_below_minimum_n(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(n=gates.BUDGET - 1,
                          reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256}"),
             _other_family_line()]
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_budget_row(lines)
    assert ei.value.gate == "G-3"


def test_check_budget_row_admits_raised_budget_n(monkeypatch):
    """prereg §8.3: budgets only rise — n > BUDGET still admits."""
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(n=gates.BUDGET + 2,
                          reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256}"),
             _other_family_line()]
    assert gates.check_budget_row(lines)["gate"] == "G-3"


def test_check_budget_row_refuses_wrong_kind(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(kind="trial",
                          reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256}"),
             _other_family_line()]
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_budget_row(lines)
    assert ei.value.gate == "G-3"


def test_check_budget_row_refuses_without_preexisting_families(monkeypatch):
    """Anti-truncation: the one-family file is the sparse-tree signature."""
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    lines = [_budget_line(reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256}")]
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.check_budget_row(lines)
    assert ei.value.gate == "G-3"
    assert "truncation" in str(ei.value)


def test_check_budget_row_skips_malformed_lines_exactly_as_entry_radar(monkeypatch):
    monkeypatch.setattr(gates, "PREREG_COMMIT", GOOD_COMMIT)
    monkeypatch.setattr(gates, "PREREG_DOC_SHA256", GOOD_SHA256)
    good = _budget_line(reason=f"w5_prereg={GOOD_COMMIT} doc_sha256={GOOD_SHA256}")
    lines = ["", "   ", "{torn json", "[not, a, dict]", good, _other_family_line()]
    assert gates.check_budget_row(lines)["gate"] == "G-3"


# --------------------------------------------------------------------------- #
# registration_reason — the exact frozen string
# --------------------------------------------------------------------------- #
def test_registration_reason_is_the_exact_literal():
    assert gates.registration_reason() == (
        "w5_prereg=8e1950932b29f89a89da94c50ccef4ef5f2d8d1c "
        "doc_sha256=44c9df659288c64987758f8408c2b7eced41488e57251c4390ddd466bf1f7a43 "
        "basis=itemized:primary_delta,hr_a1_minus_hr_a0,a2_minus_s_vs_a2_minus_k,"
        "economic_translation_a2,split_aapl,split_homebuilders"
    )


# --------------------------------------------------------------------------- #
# REG — register() on a tmp_path TrialLedger (never data/trial_ledger.jsonl)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def tmp_ledger(tmp_path) -> TrialLedger:
    return TrialLedger(path=tmp_path / "trial_ledger.jsonl", family=gates.FAMILY)


def _ledger_lines(ledger: TrialLedger) -> list[dict]:
    text = Path(ledger.path).read_text(encoding="utf-8")
    return [json.loads(l) for l in text.splitlines() if l.strip()]


@pytest.fixture
def full_tree(monkeypatch):
    # Pin a materialized tree so these tests never depend on the checkout's own sparseness.
    monkeypatch.setattr(worktree_sparse, "missing_dirs", lambda root=None: [])


def test_register_writes_one_declared_budget_row_with_identifiers(full_tree, tmp_ledger):
    receipt = gates.register(tmp_ledger)
    assert receipt["gate"] == "REG"
    rows = _ledger_lines(tmp_ledger)
    budget_rows = [r for r in rows if r.get("kind") == "declared_budget"]
    assert len(budget_rows) == 1
    row = budget_rows[0]
    assert row["family"] == gates.FAMILY
    assert row["n"] == gates.BUDGET
    assert gates.PREREG_COMMIT in row["reason"]
    assert gates.PREREG_DOC_SHA256 in row["reason"]
    assert row["reason"] == gates.registration_reason()


def test_register_is_idempotent_no_second_row(full_tree, tmp_ledger):
    gates.register(tmp_ledger)
    before = Path(tmp_ledger.path).read_bytes()
    receipt = gates.register(tmp_ledger)
    after = Path(tmp_ledger.path).read_bytes()
    assert receipt["gate"] == "REG"
    assert before == after
    assert len(_ledger_lines(tmp_ledger)) == 1


def test_register_refuses_none_ledger():
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.register(None)
    assert ei.value.gate == "REG"


def test_register_refuses_on_sparse_tree(monkeypatch, tmp_ledger):
    monkeypatch.setattr(worktree_sparse, "missing_dirs", lambda root=None: ["data"])
    with pytest.raises(gates.WP31Refusal) as ei:
        gates.register(tmp_ledger, repo_root="/nonexistent-for-test")
    assert ei.value.gate == "REG"
    assert not Path(tmp_ledger.path).exists() or _ledger_lines(tmp_ledger) == []


def test_register_allow_sparse_for_test_bypasses(monkeypatch, tmp_ledger):
    monkeypatch.setattr(worktree_sparse, "missing_dirs", lambda root=None: ["data"])
    receipt = gates.register(tmp_ledger, allow_sparse_for_test=True,
                             repo_root="/nonexistent-for-test")
    assert receipt["gate"] == "REG"
    assert len(_ledger_lines(tmp_ledger)) == 1


# --------------------------------------------------------------------------- #
# EXPOSURE — the label-read ledger (tmp_path JSONL, append-only, first-wins)
# --------------------------------------------------------------------------- #
def test_record_label_read_creates_file_and_returns_first_row(tmp_path):
    path = tmp_path / "exposure.jsonl"
    row = gates.record_label_read(path, "DHI", "2026Q3", gates.EVALUATOR_READER,
                                  "2026-10-17T13:00:00Z")
    assert row == {"issuer": "DHI", "q": "2026Q3",
                   "reader": gates.EVALUATOR_READER, "at": "2026-10-17T13:00:00Z"}
    assert path.read_text(encoding="utf-8").splitlines() == [json.dumps(row)]


def test_second_record_label_read_returns_original_and_file_is_byte_identical(tmp_path):
    path = tmp_path / "exposure.jsonl"
    first = gates.record_label_read(path, "DHI", "2026Q3", gates.EVALUATOR_READER,
                                    "2026-10-17T13:00:00Z")
    before = path.read_bytes()
    again = gates.record_label_read(path, "DHI", "2026Q3", "some_human_agent",
                                    "2026-10-18T09:00:00Z")
    after = path.read_bytes()
    assert again == first  # first-read-wins; the later reader is not recorded
    assert before == after  # append-only: never rewrites, never appends a dup
    assert len(after.decode("utf-8").strip().splitlines()) == 1


def test_is_exposed_false_for_evaluator_reader(tmp_path):
    path = tmp_path / "exposure.jsonl"
    gates.record_label_read(path, "AAPL", "2026Q4", gates.EVALUATOR_READER,
                            "2026-10-17T13:00:00Z")
    assert gates.is_exposed(path, "AAPL", "2026Q4") is False


def test_is_exposed_true_for_any_other_reader(tmp_path):
    path = tmp_path / "exposure.jsonl"
    gates.record_label_read(path, "AAPL", "2026Q4", "chairman_chris",
                            "2026-10-17T13:00:00Z")
    assert gates.is_exposed(path, "AAPL", "2026Q4") is True
    # and the reverse: an evaluator first read stays unexposed even if a human
    # read later (the later row is not recorded at all)
    path2 = tmp_path / "exposure2.jsonl"
    gates.record_label_read(path2, "AAPL", "2026Q4", gates.EVALUATOR_READER,
                            "2026-10-17T13:00:00Z")
    gates.record_label_read(path2, "AAPL", "2026Q4", "chairman_chris",
                            "2026-10-18T13:00:00Z")
    assert gates.is_exposed(path2, "AAPL", "2026Q4") is False


def test_first_label_read_none_on_missing_file_and_unknown_episode(tmp_path):
    missing = tmp_path / "nope" / "exposure.jsonl"
    assert gates.first_label_read(missing, "TOL", "2026Q2") is None
    assert gates.is_exposed(missing, "TOL", "2026Q2") is False
    path = tmp_path / "exposure.jsonl"
    gates.record_label_read(path, "PHM", "2026Q1", gates.EVALUATOR_READER,
                            "2026-10-17T13:00:00Z")
    assert gates.first_label_read(path, "KBH", "2026Q1") is None


def test_exposure_rows_distinct_per_episode_key(tmp_path):
    path = tmp_path / "exposure.jsonl"
    r1 = gates.record_label_read(path, "KBH", "2026Q1", "other", "2026-10-17T13:00:00Z")
    r2 = gates.record_label_read(path, "KBH", "2026Q2", gates.EVALUATOR_READER,
                                 "2026-10-17T14:00:00Z")
    assert r1 is not r2 and r1["q"] != r2["q"]
    assert gates.is_exposed(path, "KBH", "2026Q1") is True
    assert gates.is_exposed(path, "KBH", "2026Q2") is False
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2
