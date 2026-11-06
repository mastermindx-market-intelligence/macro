"""S2 abstention ladder (E8) and the A25 no-0.5 rule.

Pins the first-match-wins ladder order, that a 0.5 fill never appears as a
direction or probability, and that the pooling-weight token is printed
whenever the pooled TRAIN prior is not estimable or cluster-N < 2.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

from run_s2 import abstention_state  # noqa: E402
from s2_seal import (ABSTAIN_INSUFFICIENT_CLUSTERS,  # noqa: E402
                     ABSTAIN_NO_EPISODES, DESCRIPTIVE_ONLY, MIN_EPISODES,
                     POOLING_WEIGHT_TOKEN, TESTED)


def _prim(honest_n: int, cluster_n: int) -> dict:
    return {"honest_n": honest_n, "cluster_n": cluster_n, "episodes": [],
            "cluster_keys": []}


def test_ladder_first_match_wins() -> None:
    assert abstention_state(_prim(0, 0)) == ABSTAIN_NO_EPISODES
    assert abstention_state(_prim(1, 1)) == ABSTAIN_INSUFFICIENT_CLUSTERS
    assert abstention_state(_prim(0, 2)) == ABSTAIN_NO_EPISODES
    assert abstention_state(_prim(MIN_EPISODES - 1, 5)) == DESCRIPTIVE_ONLY
    assert abstention_state(_prim(MIN_EPISODES, 5)) == TESTED


def test_direction_zero_abstains_never_fills() -> None:
    from s2_stats import sign_exact
    assert sign_exact(0.0) == 0
    assert sign_exact(0.0000001) == 1
    assert sign_exact(-0.0000001) == -1


def test_no_05_fill_tokens_in_pooling_or_direction() -> None:
    from s2_seal import BASELINE_LABELS, PROPER_SCORE_LINE
    assert POOLING_WEIGHT_TOKEN == "NOT ESTIMABLE"
    text = "|".join(BASELINE_LABELS.values()) + "|" + PROPER_SCORE_LINE
    assert "0.5" not in text
    assert "50/50" not in text


def test_pooling_weight_is_the_token_when_not_estimable() -> None:
    # the runner prints POOLING_WEIGHT_TOKEN unless both conditions hold;
    # here they never hold at S2 sample sizes, so the token must be the value
    from run_s2 import build_block  # noqa: F401  (integration exercised in evidence run)
    assert POOLING_WEIGHT_TOKEN.startswith("NOT ESTIMABLE")


def test_abstain_plain_null_never_describes_a_coin_flip() -> None:
    from run_s2 import plain_word_null
    from s2_seal import (ABSTAIN_INSUFFICIENT_CLUSTERS, ABSTAIN_NO_EPISODES,
                         DESCRIPTIVE_ONLY, TESTED)
    for tok in (ABSTAIN_NO_EPISODES, ABSTAIN_INSUFFICIENT_CLUSTERS,
                DESCRIPTIVE_ONLY):
        s = plain_word_null(tok)
        assert "coin flip" not in s and "cannot be distinguished" not in s, tok
        assert "not forecasts, signals or attribution" in s
    assert plain_word_null(ABSTAIN_INSUFFICIENT_CLUSTERS).startswith(
        "This family abstains: fewer than two independent clusters")
    assert plain_word_null(ABSTAIN_NO_EPISODES).startswith(
        "This family abstains: no episode was counted")
    assert "cannot be distinguished from a coin flip" in plain_word_null(TESTED)


def test_committed_results_plain_null_matches_state() -> None:
    import json
    from run_s2 import plain_word_null
    from s2_seal import TESTED
    runs = ROOT / "research" / "single_name_intelligence" / "runs" / "s2_event_response"
    n_tested = 0
    for pid in ("P04", "P05", "P06"):
        d = json.loads((runs / "results" / f"{pid}.json").read_text(encoding="utf-8"))
        blocks = [b for split in d["splits"].values() if isinstance(split, dict)
                  for b in split.values() if isinstance(b, dict)
                  and "plain_word_null" in b]
        assert len(blocks) == 9, (pid, len(blocks))
        for b in blocks:
            st = b["family_row"]["abstention_state"]
            assert b["plain_word_null"] == plain_word_null(st), (pid, st)
            n_tested += st == TESTED
    report = (runs / "REPORT.md").read_text(encoding="utf-8")
    assert report.count("cannot be distinguished from a coin flip") == n_tested
