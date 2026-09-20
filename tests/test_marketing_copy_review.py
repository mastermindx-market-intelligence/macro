"""tests/test_marketing_copy_review.py — quality review over a BATCH.

validate_copy inspects one post at a time, which is structurally blind to the
2026-07-26 failure: eight posts sharing a skeleton, each individually fine. The
mechanical half of copy_review closes that, costs nothing, and must keep working
with no model available — so these tests never touch the network.
"""
from __future__ import annotations

import pytest

from engine.marketing.copy_review import (
    detect_ambiguity,
    detect_repetition,
    lessons_from_rejections,
    review_batch,
)

# The post the operator saw on the flagship account, verbatim. Every clarity
# assertion below is anchored to it so the fixture cannot drift from the defect.
_INCIDENT_HL = "Four up, near highs, VWAP holds"
_INCIDENT_BODY = (
    "$AAPL -0.6% off the 52-week high at 334.99 and up four weeks straight. "
    "That Jun 26 anchored VWAP has held for 20 sessions. I'm watching a close "
    "below it, not chasing."
)


def _p(i, headline, body="Some body with 123 and a level."):
    return {"id": i, "headline": headline, "body": body}


# ─────────────────────────────────────────────────────────────────────────────
# The incident, as a test
# ─────────────────────────────────────────────────────────────────────────────

def test_the_incident_batch_is_caught_without_a_model():
    """Six posts, one skeleton — every one passed validate_copy individually."""
    posts = [_p(t, f"${t} into the week",
                f"Closed {n}, down {n}% on the week, under both the 20- and 50-day.")
             for t, n in [("NVDA", 207), ("TSLA", 313), ("AAPL", 333),
                          ("AMD", 522), ("PLTR", 123), ("MSFT", 382)]]
    findings = detect_repetition(posts)
    kinds = {f["kind"] for f in findings}
    assert "repeated_headline" in kinds
    high = [f for f in findings if f["severity"] == "high"]
    assert high and "6 of 6" in high[0]["detail"]

    r = review_batch(posts)
    assert r["mode"] == "mechanical"                 # no model needed
    assert all(p["verdict"] == "bad" for p in r["posts"])


def test_a_varied_batch_is_clean():
    """The reviewer must not cry wolf, or the marker stops meaning anything.

    Every line here is terse, fragmentary and on-voice — the things the reviewer
    must NOT flag. Two of these fixtures used to read "Four up, near highs, VWAP
    holds" and "Under POC, watching for lower retest"; the incident below is why
    they no longer count as clean.
    """
    posts = [
        _p("AAPL", "Up four weeks, near highs", "Buyers keep showing up. 314 is the line."),
        _p("TSLA", "Eight weeks down, new low. No thanks.", "Nothing says the selling is done."),
        _p("NVDA", "Sellers still have the tape", "Wants 203 before I care."),
        _p("AMZN", "Four red days and counting", "244 is the test."),
        _p("MSFT", "Up big, and I'd rather wait", "Not chasing here."),
    ]
    r = review_batch(posts)
    assert r["batch"] == []
    assert all(p["verdict"] == "ok" for p in r["posts"])


def test_shape_ignores_ticker_and_number_substitution():
    """'$AAPL into the week' and '$TSLA into the week' must collide — the whole
    failure mode is a skeleton whose only variation IS the substitution."""
    posts = [_p("A", "$AAPL into the week"), _p("B", "$TSLA into the week"),
             _p("C", "$MSFT into the week")]
    assert any(f["kind"] == "repeated_headline" for f in detect_repetition(posts))


def test_identical_bodies_are_flagged_as_twins():
    """$AMZN and $META shipped the same sentence with different numbers."""
    posts = [
        _p("AMZN", "A different headline", "Still heavy, down 6% on the week. It has to reclaim 244."),
        _p("META", "Another headline entirely", "Still heavy, down 8% on the week. It has to reclaim 621."),
        _p("NVDA", "Third headline", "Back above its 20-day after a rough stretch."),
    ]
    kinds = {f["kind"] for f in detect_repetition(posts)}
    assert "identical_body" in kinds


def test_small_batches_are_not_judged():
    """Two posts sharing a shape is not evidence of a template."""
    assert detect_repetition([_p("A", "$A into the week"), _p("B", "$B into the week")]) == []


def test_review_marks_which_posts_collide_not_just_that_some_do():
    # Distinct bodies on purpose: this isolates the HEADLINE collision. Sharing
    # a body would (correctly) flag every post as a twin and prove nothing.
    posts = [_p("A", "$A into the week", "Reclaimed the 20-day, 203 next."),
             _p("B", "$B into the week", "Sellers still in charge under 128."),
             _p("C", "$C into the week", "Flat week, sitting at the highs."),
             _p("D", "Something else entirely", "Value area low is 244, that is the test.")]
    r = review_batch(posts)
    verdicts = {p["id"]: v["verdict"] for p, v in zip(posts, r["posts"])}
    assert verdicts["A"] == verdicts["B"] == verdicts["C"] == "bad"
    assert verdicts["D"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Clarity: the post that was clean, unique, on-voice, and unreadable
# ─────────────────────────────────────────────────────────────────────────────

def test_the_unreadable_post_is_caught_without_a_model():
    """"wtf is four up?" — the operator, looking at a post that broke no rule."""
    findings = detect_ambiguity([_p("AAPL", _INCIDENT_HL, _INCIDENT_BODY)])
    kinds = {f["kind"] for f in findings}
    assert "headless_count" in kinds, "'Four up' has no noun and nothing caught it"
    assert "unnamed_level" in kinds, (
        "'watching a close below it' is the whole trade and names no price")

    r = review_batch([_p("AAPL", _INCIDENT_HL, _INCIDENT_BODY)])
    assert r["mode"] == "mechanical"                  # no model needed
    assert r["posts"][0]["verdict"] == "bad"


def test_ambiguity_is_per_post_so_a_single_bad_post_is_caught():
    """detect_repetition needs 3+ posts to mean anything. A post that nobody can
    read is bad on its own, so the clarity pass must not inherit that floor."""
    assert detect_repetition([_p("A", _INCIDENT_HL, _INCIDENT_BODY)]) == []
    assert detect_ambiguity([_p("A", _INCIDENT_HL, _INCIDENT_BODY)]) != []


def test_house_voice_is_not_ambiguity():
    """Terse, fragmentary, pronoun-carrying house copy must stay clean, or the
    marker becomes noise and the operator learns to ignore it."""
    posts = [
        # Fragments and counts WITH their nouns.
        _p("A", "$A is grinding higher", "Up four weeks straight. 328.40 is the line."),
        _p("B", "Eight weeks down in $B", "Nothing says the selling is done."),
        _p("C", "Four red days in $C", "244 is the test. Watching, no position."),
        # The house exemplars: pronouns with a real antecedent (the stock).
        _p("D", "$D down 14% today", "The dip buyers get to find out who was early. "
                                     "Watching for a bottom setup, not catching it yet."),
        _p("E", "Hard to argue with $E here", "I'd rather respect that than argue "
                                              "with it. 512.00 is the line I want kept."),
        # A watched level named by pronoun, but PRICED in the same sentence.
        _p("F", "$F is still holding", "It has stayed above 328.40 for 20 sessions. "
                                       "A close under that is what changes my mind."),
    ]
    assert detect_ambiguity(posts) == [], "the reviewer is crying wolf on house voice"


def test_headless_count_needs_the_noun_missing_not_merely_a_count():
    from engine.marketing.copywriter import headless_counts
    assert headless_counts("Four up, near highs") == ["Four up"]
    assert headless_counts("Two down. That settles that.") == ["Two down"]
    assert headless_counts("8 green, no volume") == ["8 green"]
    # The noun arrives → readable → clean.
    assert headless_counts("Eight weeks down, new low") == []
    assert headless_counts("Four red days, watching 244") == []
    assert headless_counts("Up four weeks straight") == []
    assert headless_counts("$AAPL down 3% today") == []


def test_unnamed_level_fires_on_the_level_pronoun_not_every_pronoun():
    from engine.marketing.copywriter import dangling_levels
    assert dangling_levels("I'm watching a close below it, not chasing.")
    assert dangling_levels("A break under that and I'm out.")
    # Same sentence, level printed → clean.
    assert dangling_levels("I'm watching a close below 328.40.") == []
    # Pronouns with a real antecedent, no level preposition → clean.
    assert dangling_levels("Watching for a bottom setup, not catching it yet.") == []
    assert dangling_levels("I'd rather respect that than argue with it.") == []
    assert dangling_levels("Getting back over the 20-day is what settles it.") == []


# ─────────────────────────────────────────────────────────────────────────────
# The loop: the operator's rejections become the reviewer's rules
# ─────────────────────────────────────────────────────────────────────────────

def test_rejection_reasons_become_lessons(tmp_path):
    from admin import marketing as M
    from engine.marketing.outbox import make_item, enqueue

    (tmp_path / "data" / "marketing" / "outbox").mkdir(parents=True)
    for i, why in enumerate(["reads like a brochure", "no stance at all"]):
        it = make_item(account="flagship", kind="watchlist",
                       text=f"$AAA post {i}\n\nbody {i}.", as_of="2026-07-26",
                       provenance="weekend_levels", source={"ticker": f"T{i}"})
        enqueue(it, root=tmp_path)
        M.reject_outbox(it["id"], reason=why, root=tmp_path)

    lessons = lessons_from_rejections(tmp_path)
    assert "reads like a brochure" in lessons
    assert "no stance at all" in lessons


def test_lessons_are_deduped_and_newest_first(tmp_path):
    from engine.marketing import rejections as R
    (tmp_path / "data" / "marketing").mkdir(parents=True)
    for why in ["stiff", "stiff", "brochure-ish"]:
        R.record({"id": f"ob-{why}-{len(why)}", "text": "x"}, reason=why, root=tmp_path)
    lessons = lessons_from_rejections(tmp_path)
    assert lessons[0] == "brochure-ish"          # newest first
    assert lessons.count("stiff") == 1           # deduped


def test_lessons_are_fail_soft_with_no_ledger(tmp_path):
    assert lessons_from_rejections(tmp_path) == []


def test_llm_lane_is_off_without_the_env_gate(monkeypatch):
    """Same double gate as write_posts_llm — tests never reach the network."""
    from engine.marketing.copy_review import review_posts_llm
    monkeypatch.delenv("MARKETING_LLM_ENABLED", raising=False)
    assert review_posts_llm([_p("A", "x")], {"llm": {"enabled": True}}) is None


def test_review_never_raises_on_junk():
    assert review_batch([]) ["batch"] == []
    assert review_batch([{"id": "A"}, {"id": "B"}, {"id": "C"}])["mode"] == "mechanical"


# ─────────────────────────────────────────────────────────────────────────────
# B2 held-out editorial benchmark — evaluation only, never a publish/learning gate
# ─────────────────────────────────────────────────────────────────────────────

class TestEditorialBenchmark:
    @staticmethod
    def _packets():
        return [
            {
                "packet_id": "p-a1", "family": "AAPL:event-earnings",
                "kind": "event", "account": "flagship", "ticker": "AAPL",
                "source_state": "complete",
                "observation_clock": "2026-09-18T20:00:00Z",
                "source_clock": "2026-09-18T20:00:00Z",
                "facts": {"move_pct": 4.2, "event": "earnings"},
                "image": {"present": False, "digest": None},
            },
            {
                "packet_id": "p-a2", "family": "AAPL:event-earnings",
                "kind": "event", "account": "flagship", "ticker": "AAPL",
                "source_state": "partial",
                "observation_clock": "2026-09-19T14:00:00Z",
                "source_clock": "2026-09-19T13:59:00Z",
                "facts": {"move_pct": None, "event": "followthrough"},
                "image": {"present": False, "digest": None},
            },
            {
                "packet_id": "p-m1", "family": "macro:cpi-2026-09",
                "kind": "macro", "account": "founder", "ticker": None,
                "source_state": "complete",
                "observation_clock": "2026-09-17T12:30:00Z",
                "source_clock": "2026-09-17T12:30:00Z",
                "facts": {"cpi_yoy": 2.8, "consensus": 3.0},
                "image": {"present": True, "digest": "sha256:chart-m1"},
            },
            {
                "packet_id": "p-q1", "family": "MSFT:chart-weekly",
                "kind": "chart", "account": "flagship", "ticker": "MSFT",
                "source_state": "unknown",
                "observation_clock": "2026-09-19T20:00:00Z",
                "source_clock": None, "facts": {},
                "image": {"present": False, "digest": None, "required": True},
            },
        ]

    @staticmethod
    def _runs(packet_ids):
        rows = []
        for candidate in ("baseline", "candidate"):
            for packet_id in packet_ids:
                if packet_id == "p-q1":
                    rows.append({
                        "packet_id": packet_id, "candidate_id": candidate,
                        "decision": "no_post", "text": "",
                        "first_pass_accepted": True, "repair_count": 0,
                        "latency_ms": 40 if candidate == "baseline" else 25,
                        "cost_usd": 0.0, "requested_model": "hidden-request",
                        "served_provider": "hidden-provider", "served_model": "hidden-model",
                        "validator_reasons": [],
                    })
                    continue
                text = {
                    ("baseline", "p-a1"): "$AAPL into the week. Up 4.2%.",
                    ("baseline", "p-a2"): "$AAPL into the week. Followthrough still unclear.",
                    ("baseline", "p-m1"): "CPI 2.8% vs 3.0% consensus. The miss is visible in the chart.",
                    ("candidate", "p-a1"): "$AAPL gained 4.2% after earnings. The move changed the range.",
                    ("candidate", "p-a2"): "Followthrough is unresolved because the move is missing.",
                    ("candidate", "p-m1"): "CPI printed 2.8% against 3.0% consensus. The chart shows the gap.",
                }[(candidate, packet_id)]
                rows.append({
                    "packet_id": packet_id, "candidate_id": candidate,
                    "decision": "post", "text": text,
                    "first_pass_accepted": candidate == "candidate",
                    "repair_count": 1 if candidate == "baseline" else 0,
                    "latency_ms": 120 if candidate == "baseline" else 80,
                    "cost_usd": 0.02 if candidate == "baseline" else 0.01,
                    "requested_model": "hidden-request",
                    "served_provider": "hidden-provider", "served_model": "hidden-model",
                    "validator_reasons": [],
                })
        return rows

    def test_split_is_family_grouped_and_independent_of_outputs(self):
        from engine.marketing import editorial_benchmark as eb

        m1 = eb.freeze_packets(self._packets(), seed="b2-test", holdout_fraction=0.5)
        m2 = eb.freeze_packets(list(reversed(self._packets())),
                               seed="b2-test", holdout_fraction=0.5)
        assert m1["packet_digest"] == m2["packet_digest"]
        split_by_family = {}
        for row in m1["packets"]:
            split_by_family.setdefault(row["family"], set()).add(row["split"])
        assert all(len(splits) == 1 for splits in split_by_family.values())
        assert {row["split"] for row in m1["packets"]} == {"train", "holdout"}

    def test_blind_bundle_hides_candidate_and_runtime_identity(self):
        from engine.marketing import editorial_benchmark as eb

        manifest = eb.freeze_packets(self._packets(), seed="b2-blind",
                                     holdout_fraction=0.5)
        runs = self._runs([row["packet_id"] for row in manifest["packets"]])
        review, key = eb.prepare_blinded_review(manifest, runs, seed="review-seed")
        encoded = __import__("json").dumps(review, sort_keys=True)
        for forbidden in ("candidate_id", "served_model", "served_provider",
                          "requested_model", "baseline", "candidate"):
            assert forbidden not in encoded
        assert key["assignments"]
        assert {row["candidate_id"] for row in key["assignments"]} == {
            "baseline", "candidate"}

    def test_unknown_and_no_post_stay_in_the_denominator(self):
        from engine.marketing import editorial_benchmark as eb

        manifest = eb.freeze_packets(self._packets(), seed="all-holdout",
                                     holdout_fraction=1.0)
        assert len(manifest["packets"]) == 4
        runs = self._runs([row["packet_id"] for row in manifest["packets"]])
        review, key = eb.prepare_blinded_review(manifest, runs, seed="r")
        packet_labels = [
            {"review_id": row["review_id"], "should_post": row["packet"]["packet_id"] != "p-q1",
             "source_sufficient": row["packet"]["packet_id"] != "p-q1"}
            for row in review["items"]
        ]
        ratings = []
        for item in review["items"]:
            for variant in item["variants"]:
                if variant["decision"] != "post":
                    continue
                ratings.append({
                    "review_id": item["review_id"], "variant": variant["variant"],
                    "factual_correctness": 5, "usefulness": 4, "naturalness": 4,
                    "repetitive_framing": False,
                    "image_text_consistency": 5 if item["packet"]["image"]["present"] else None,
                    "publishable_without_rewrite": True,
                    "critical_fabrication": False,
                })
        report = eb.grade(manifest, runs, key, packet_labels, ratings)
        for candidate in ("baseline", "candidate"):
            c = report["candidates"][candidate]
            assert c["denominators"]["holdout_packets"] == 4
            assert c["selection"]["correct_abstain"] == 1
            assert c["selection"]["missing_or_error"] == 0
            assert c["content"]["critical_fabrications"] == 0
            assert c["runtime"]["latency_ms_per_accepted"] is not None
            assert c["runtime"]["cost_usd_per_accepted"] is not None

    def test_missing_ratings_are_reported_not_dropped(self):
        from engine.marketing import editorial_benchmark as eb

        manifest = eb.freeze_packets(self._packets(), seed="all-holdout",
                                     holdout_fraction=1.0)
        runs = self._runs([row["packet_id"] for row in manifest["packets"]])
        review, key = eb.prepare_blinded_review(manifest, runs, seed="r")
        report = eb.grade(manifest, runs, key, [], [])
        assert report["state"] == "partial"
        assert report["missing"]["packet_labels"] == len(review["items"])
        assert report["missing"]["output_ratings"] > 0

    def test_unknown_runtime_receipts_stay_unknown_not_false_or_zero(self):
        from engine.marketing import editorial_benchmark as eb

        packets = [self._packets()[0]]
        manifest = eb.freeze_packets(packets, seed="one", holdout_fraction=1.0)
        runs = [{
            "packet_id": "p-a1", "candidate_id": "baseline",
            "decision": "post", "text": "$AAPL gained after earnings.",
            "latency_ms": None, "cost_usd": None,
            "requested_model": None, "served_provider": None, "served_model": None,
            "validator_reasons": [],
        }]
        review, key = eb.prepare_blinded_review(manifest, runs, seed="r")
        review_id = review["items"][0]["review_id"]
        variant = review["items"][0]["variants"][0]["variant"]
        labels = [{"review_id": review_id, "should_post": True,
                   "source_sufficient": True}]
        ratings = [{
            "review_id": review_id, "variant": variant,
            "factual_correctness": 5, "usefulness": 4, "naturalness": 4,
            "repetitive_framing": False, "image_text_consistency": None,
            "publishable_without_rewrite": True, "critical_fabrication": False,
        }]
        runtime = eb.grade(manifest, runs, key, labels, ratings)[
            "candidates"]["baseline"]["runtime"]
        assert runtime["first_pass_acceptance"]["d"] == 0
        assert runtime["first_pass_acceptance"]["rate"] is None
        assert runtime["first_pass_coverage"] == 0
        assert runtime["repair_coverage"] == 0
        assert runtime["repair_count_total"] is None
        assert runtime["latency_coverage"] == 0
        assert runtime["latency_ms_per_accepted"] is None
        assert runtime["cost_coverage"] == 0
        assert runtime["cost_usd_per_accepted"] is None

    def test_committed_b2_capture_is_frozen_and_source_backed(self):
        import json
        from pathlib import Path
        from engine.marketing import editorial_benchmark as eb

        root = Path(__file__).resolve().parents[1]
        docket = root / "research" / "marketing_dockets"
        manifest = json.loads((
            docket / "MX_X_B2_EDITORIAL_BENCHMARK_MANIFEST_2026-09-19.json"
        ).read_text(encoding="utf-8"))
        runs = json.loads((
            docket / "MX_X_B2_INCUMBENT_BASELINE_RUN_2026-09-19.json"
        ).read_text(encoding="utf-8"))

        assert manifest["manifest_id"] == "18293e3ba3bfcb2127d04907"
        assert manifest["packet_digest"] == (
            "bfc9d8212f7b64cadb068c06896290573ba5bda806b8951d91c6d488c656fe71"
        )
        assert len(manifest["packets"]) == 8
        assert all(row["split"] == "holdout" for row in manifest["packets"])
        assert len(runs) == 8
        assert {row["packet_id"] for row in runs} == {
            row["packet_id"] for row in manifest["packets"]
        }
        source_pin = "macro@25153e3027bfe71c85cedf05da75101c0da215af:"
        assert all(
            any(str(ref).startswith(source_pin) for ref in row.get("source_refs", []))
            for row in manifest["packets"]
        )
        assert any(
            row["image"]["state"] == "unverified_plan_reference"
            for row in manifest["packets"]
        )
        assert not any(row["image"]["present"] for row in manifest["packets"])
        review, key = eb.prepare_blinded_review(
            manifest, runs, seed="mx-x-b2-review-v1")
        assert len(review["items"]) == 8
        assert key["candidate_ids"] == ["incumbent_current_plan"]

    def test_benchmark_is_explicitly_non_authoritative_and_offline(self):
        import inspect
        from engine.marketing import editorial_benchmark as eb

        assert eb.GATES_NOTHING is True
        assert eb.CALLS_MODELS is False
        source = inspect.getsource(eb)
        for forbidden in (
            "llm_auth", "make_call(", "enqueue(", "approve_outbox",
            "marketing_publisher", "labels.record", "learned_rules",
        ):
            assert forbidden not in source
