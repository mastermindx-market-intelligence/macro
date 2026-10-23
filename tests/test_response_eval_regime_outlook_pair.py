"""G1 — regime-outlook analytical pair (Sol's first pair still first; second is additive).

Eight checks per the frozen G1 spec. Mirrors the analytical-pair tests in
test_response_eval.py and the digest fixture pattern (assert_no_authority import law)
in tests/test_regime_outlook_reader_digest.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from engine.neuralweb import response_eval as ev
from engine.neuralweb._law import assert_no_authority

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Fixture schema: frozen, exact two case roles, stance_required False,
#    every case has >=8 expected_properties each with tag + check.
# ---------------------------------------------------------------------------

def test_regime_outlook_pair_fixture_is_frozen_and_has_exact_two_case_roles():
    case = ev.load_benchmark(ev.REGIME_OUTLOOK_PAIR_BENCHMARK)
    assert case["benchmark_id"] == "regime-outlook-pair-2026-10-05"
    assert case["frozen"] is True
    assert case["lane"] == "fast" and case["lang"] == "en"
    roles = [row["case_id"] for row in case["cases"]]
    assert roles == ["natural", "coached"]
    assert "synthetic" in case["source"].lower()
    assert "rates-desk" in case["source"] or "rates desk" in case["source"].lower()
    for row in case["cases"]:
        assert row["stance_required"] is False
        assert len(row["expected_properties"]) >= 8
        for prop in row["expected_properties"]:
            assert isinstance(prop.get("tag"), str) and prop["tag"], row
            assert isinstance(prop.get("check"), str) and prop["check"], row


# ---------------------------------------------------------------------------
# 2. OUTLOOK grammar pin by HEADER (not byte-equality): the fixture's line 3
#    starts with `OUTLOOK (read prepared `, contains `+fits -does-not-fit ~mixed): `,
#    ends with `; full readings: world_state.rates_command.regime_outlook`,
#    and carries no digit after the `): ` header (E3 gate 4); line 2 starts with
#    `RATES DESK (`.
# ---------------------------------------------------------------------------

def test_regime_outlook_pair_packet_lines_match_outlook_header_grammar():
    case = ev.load_benchmark(ev.REGIME_OUTLOOK_PAIR_BENCHMARK)
    digest = case["packet_digest_fixture"]
    lines = digest.split("\n")
    assert len(lines) >= 4, digest
    # Header + closing tags.
    assert lines[0].startswith("[FROZEN ANALYTICAL BENCHMARK — synthetic; no live tools]")
    assert lines[-1].startswith("MISSING:")
    # Line 2: RATES DESK.
    assert lines[1].startswith("RATES DESK ("), lines[1]
    # Line 3: OUTLOOK grammar.
    outlook = lines[2]
    assert outlook.startswith("OUTLOOK (read prepared "), outlook
    assert "+fits -does-not-fit ~mixed): " in outlook, outlook
    assert outlook.endswith("; full readings: world_state.rates_command.regime_outlook"), outlook
    # E3 gate 4: no digit anywhere after the `): ` header.
    header_end = outlook.index("): ") + len("): ")
    body = outlook[header_end:]
    assert re.search(r"\d", body) is None, body
    assert "%" not in body


# ---------------------------------------------------------------------------
# 3. Tuple wiring: Sol's first pair is first; the regime-outlook pair is second;
#    the original 2026-09-19 ANALYTICAL_PAIR_BENCHMARK string is untouched.
# ---------------------------------------------------------------------------

def test_pair_benchmark_tuple_keeps_sol_first_and_outlook_second():
    assert ev.ANALYTICAL_PAIR_BENCHMARKS == (
        ev.ANALYTICAL_PAIR_BENCHMARK,
        ev.REGIME_OUTLOOK_PAIR_BENCHMARK,
    )
    assert ev.ANALYTICAL_PAIR_BENCHMARKS[0] == "benchmark_natural_vs_coached_causality_2026-09-19.json"
    assert ev.ANALYTICAL_PAIR_BENCHMARKS[1] == "benchmark_regime_outlook_pair_2026-10-05.json"


# ---------------------------------------------------------------------------
# 4. run_benchmark_pairs order + fail-soft second: with names=(A, "missing.json")
#    the second is benchmark_absent / unjudged and the first is still classified.
# ---------------------------------------------------------------------------

def test_run_benchmark_pairs_returns_in_order_and_fails_soft_on_missing():
    calls = []

    def _answer(system, user):
        calls.append((system, user))
        # Coached clearing text.
        if "overlapping paths, not a forecast" in user:
            return (
                "orderly_disinflation fits on core PCE and labour; growth_deterioration does not fit on "
                "the curve against the bear-flattener; the 09-30 09:43Z read is redrawn nightly; the "
                "next core PCE and labour prints are the discriminator; nothing here is a trade instruction."
            )
        # Natural clearing text.
        return (
            "As of 09-30 09:43Z, orderly disinflation fits on core PCE and labour while growth does not "
            "fit on the bear-flattener curve with rising term premium; the packet gives no probabilities "
            "and the next inflation and labour prints are the discriminator."
        )

    _answer.model_id = "fake-answerer"

    def _judge_reply(prompt):
        if "overlapping paths, not a forecast" in prompt:
            return json.dumps({"scores": {k: w for k, w in ev.RUBRIC.items()}, "tags": [], "note": "coached clears"})
        return json.dumps({"scores": {k: w for k, w in ev.RUBRIC.items()}, "tags": [], "note": "natural clears"})

    out = ev.run_benchmark_pairs(
        ROOT,
        lambda p: _judge_reply(p),
        _answer,
        names=(ev.ANALYTICAL_PAIR_BENCHMARK, "benchmark_does_not_exist_2026-10-05.json"),
    )
    assert len(out) == 2
    # Order: Sol's first.
    assert out[0]["benchmark_id"] == "natural-vs-coached-causal-reasoning-2026-09-19"
    # Fail-soft second: absent fixture.
    assert out[1]["benchmark_id"] == ""
    assert out[1]["error"] == "benchmark_absent"
    assert out[1]["classification"] == "unjudged"
    # The first entry was still classified.
    assert out[0]["classification"] in {"pass", "analytical_regression", "coaching_regression", "general_reasoning_failure"}
    # Stub answerer still served both calls for the first pair (two cases).
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# 5. Factories are resolved ONCE before the loop when None is passed.
# ---------------------------------------------------------------------------

def test_run_benchmark_pairs_resolves_factories_at_most_once_each(monkeypatch):
    answer_calls = {"n": 0}
    judge_calls = {"n": 0}

    def _fake_answer_factory(root=None):
        answer_calls["n"] += 1
        return _answer

    def _fake_judge_factory(root=None):
        judge_calls["n"] += 1
        return _judge

    def _answer(system, user):
        if "overlapping paths, not a forecast" in user:
            return (
                "orderly_disinflation fits on core PCE and labour; growth_deterioration does not fit on "
                "the curve against the bear-flattener; the 09-30 09:43Z read is redrawn nightly; the "
                "next core PCE and labour prints are the discriminator; nothing here is a trade instruction."
            )
        return (
            "As of 09-30 09:43Z, orderly disinflation fits on core PCE and labour while growth does not "
            "fit on the bear-flattener curve with rising term premium; the packet gives no probabilities "
            "and the next inflation and labour prints are the discriminator."
        )
    _answer.model_id = "fake-answerer"

    def _judge(prompt):
        return json.dumps({"scores": {k: w for k, w in ev.RUBRIC.items()}, "tags": [], "note": "clear"})

    monkeypatch.setattr(ev, "fast_answer_via_llm_auth", _fake_answer_factory)
    monkeypatch.setattr(ev, "judge_via_llm_auth", _fake_judge_factory)

    ev.run_benchmark_pairs(ROOT)  # default names = ANALYTICAL_PAIR_BENCHMARKS (2 entries)

    assert answer_calls["n"] == 1
    assert judge_calls["n"] == 1


# ---------------------------------------------------------------------------
# 6. scripts/run_brain_eval.py --dry-run: 2 pair dry-run dicts both dry_run,
#    analytical_pair back-compat is pairs[0], and the ::notice line carries
#    BOTH analytical-pair dry_run AND outlook-pair dry_run tokens.
# ---------------------------------------------------------------------------

def test_run_brain_eval_dry_run_summary_and_notice_carry_both_pair_tokens():
    # Run the actual script via subprocess to capture the ::notice line and the
    # on-disk summary json without import-side effects on the test process.
    proc = subprocess.run(
        [sys.executable, "scripts/run_brain_eval.py", "--dry-run"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    # Find the ::notice line — must START the line, per the gh-annotation rule.
    notice_lines = [ln for ln in out.splitlines() if ln.startswith("::notice")]
    assert notice_lines, "no ::notice line emitted"
    notice = notice_lines[-1]
    assert "analytical-pair dry_run" in notice, notice
    assert "outlook-pair dry_run" in notice, notice

    # The dry-run summary JSON lives at data/mastermind/eval_summary_latest.json
    # (scripts/run_brain_eval.py:60 SUMMARY_NAME).
    summary_path = ROOT / "data" / "mastermind" / "eval_summary_latest.json"
    assert summary_path.exists(), summary_path
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    pairs = summary.get("analytical_pairs") or []
    assert len(pairs) == 2, summary
    for row in pairs:
        assert row["classification"] == "dry_run", row
        assert row["fixture_loaded"] is True, row
    # Back-compat: analytical_pair is analytical_pairs[0].
    assert summary["analytical_pair"] == summary["analytical_pairs"][0]


# ---------------------------------------------------------------------------
# 7. Compaction: a fake live pair list with answer/mech keys in both pairs
#    drops them from BOTH pairs and BOTH case sides.
# ---------------------------------------------------------------------------

def test_compact_analytical_pair_strips_answer_mech_from_both_pairs():
    import scripts.run_brain_eval as rbe
    raw_pairs = [
        {
            "benchmark_id": "x-1",
            "natural": {"answer": "natural-answer-1", "mech": {"k": 1}, "ok": True,
                        "score": 90, "analytical_pass": True},
            "coached": {"answer": "coached-answer-1", "mech": {"k": 2}, "ok": True,
                        "score": 90, "analytical_pass": True},
        },
        {
            "benchmark_id": "x-2",
            "natural": {"answer": "natural-answer-2", "mech": {"k": 3}, "ok": True,
                        "score": 90, "analytical_pass": True},
            "coached": {"answer": "coached-answer-2", "mech": {"k": 4}, "ok": True,
                        "score": 90, "analytical_pass": True},
        },
    ]
    compacted = [rbe._compact_analytical_pair(p) for p in raw_pairs]
    assert len(compacted) == 2
    for row in compacted:
        for side in ("natural", "coached"):
            assert "answer" not in row[side], row
            assert "mech" not in row[side], row


# ---------------------------------------------------------------------------
# 8. assert_no_authority import law: response_eval and the new fixture carry
#    no live-data import (MACRO_LIVE_DIR / market_packet / world_state).
# ---------------------------------------------------------------------------

def test_response_eval_and_outlook_fixture_hold_the_authority_law():
    src = (ROOT / "engine/neuralweb/response_eval.py").read_text(encoding="utf-8")
    for sentinel in ("MACRO_LIVE_DIR", "market_packet", "world_state"):
        assert sentinel not in src, sentinel
    # The fixture path itself is referenced only as a string constant; the file
    # must not itself import market_packet or world_state.
    fixture_src = (ROOT / "engine/neuralweb/eval/benchmark_regime_outlook_pair_2026-10-05.json").read_text(encoding="utf-8")
    assert "import " not in fixture_src
    # _law.assert_no_authority is callable on plain dicts and is what the digest
    # test uses to assert the same on market_packet output.
    assert assert_no_authority({}) == []