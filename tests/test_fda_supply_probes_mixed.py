"""Frozen acceptance probe for Healthcare D1 at the merge window (seat-frozen; never
lane-edited).

Law (R-D1-MERGE-03): the MIXED chip may never name a regulator state whose count is
zero, and may never omit a regulator state whose count is non-zero. A discontinuation is
NOT a resolution — that distinction is the whole point of the D1 taxonomy — so a mixture
of current + discontinued must say so.

Found by running the REAL committed production feed
(`data/fda/shortages.parquet` at origin/main 5e921b1c, 1,787 rows) through
`compute_fda_scarcity` in the state main is in immediately after the D1 merge: parquet
present, observation sidecar not yet written (`legacy=True`, `capture=None`). The live
composition was current=9, resolved=0, discontinued=5, and the accepted head rendered:

    FDA: mixed — current 9 / resolved 0 · capture time unknown
    title="The FDA reports both current and resolved shortages."

Three untruths in one chip: it asserted resolved shortages that do not exist, printed
"resolved 0" beside the word "mixed", and hid five formulation discontinuations entirely.
`summarize_supply` selects MIXED for `current and (resolved or discontinued)`, but the
label and the rationale both hard-coded "resolved" as the second component. Every MIXED
test in the eight suites exercised current + resolved, so no probe reached the branch the
live feed actually takes.

These probes drive the injectable seam (`summarize_supply`, explicit `now`) rather than
the wall-clock path, per R-D1-MERGE-01.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.fda_scarcity import summarize_supply

UTC = timezone.utc

# The D1 banned-copy surface (same list the final probes pin).
BANNED = ("glut", "tell", "all-clear", "catching up",
          "demand exceeds supply", "supply constraint lifted")


def _row(status: str, ndc: str) -> dict:
    return {"generic_name": f"synthetic {ndc}", "status": status,
            "availability": "Available", "package_ndc": ndc}


def _summary(*statuses: str) -> dict:
    now = datetime(2026, 9, 26, 12, tzinfo=UTC)
    return summarize_supply(
        [_row(s, f"TEST-{i}") for i, s in enumerate(statuses)],
        capture={"qualified": True, "finished_at": now.isoformat(),
                 "source_generation": "2026-09-26", "atomic_snapshot_proven": False},
        now=now, max_capture_age=timedelta(days=2))


def test_r_d1_merge_03_mixed_current_and_discontinued_never_claims_resolved():
    """The live composition: current + discontinued, resolved absent."""
    out = _summary("Current", "Current", "To Be Discontinued")
    assert out["source_status"] == "MIXED_REPORTED"
    assert out["counts"]["current"] == 2 and out["counts"]["discontinued"] == 1
    assert out["counts"]["resolved"] == 0

    for label in (out["label"], out["label_zh"]):
        assert "resolved" not in label.casefold(), \
            f"R-D1-MERGE-03: named an absent state — {label!r}"
        assert "已解决" not in label, f"R-D1-MERGE-03: named an absent state — {label!r}"
        assert "resolved 0" not in label and "已解决0" not in label

    assert "discontinued 1" in out["label"], \
        f"R-D1-MERGE-03: hid the discontinuation — {out['label']!r}"
    assert "停产1" in out["label_zh"], \
        f"R-D1-MERGE-03: hid the discontinuation — {out['label_zh']!r}"


def test_r_d1_merge_03_mixed_current_and_resolved_is_unchanged():
    """The case every earlier probe covered must render exactly as it always did."""
    out = _summary("Current", "Resolved")
    assert out["source_status"] == "MIXED_REPORTED"
    assert out["label"].startswith("FDA: mixed — current 1 / resolved 1")
    assert out["label_zh"].startswith("FDA：混合——当前1／已解决1")
    assert "discontinued" not in out["label"].casefold()
    assert "停产" not in out["label_zh"]


def test_r_d1_merge_03_mixed_with_all_three_states_names_all_three():
    out = _summary("Current", "Resolved", "To Be Discontinued")
    assert out["source_status"] == "MIXED_REPORTED"
    # Pin the COMPOSITION segment only. The freshness segments that follow it
    # ("captured N d ago", "source generation ...") belong to other rulings, and
    # pinning the whole string would couple this probe to them.
    assert out["label"].startswith("FDA: mixed — current 1 / resolved 1 / discontinued 1 · ")
    assert out["label_zh"].startswith("FDA：混合——当前1／已解决1／停产1 · ")


def test_r_d1_merge_03_mixed_rationale_matches_the_states_present():
    """The title attribute must assert exactly the states the feed reports."""
    from engine.fda_scarcity import _chip_rationale

    cd = _summary("Current", "To Be Discontinued")
    text = _chip_rationale(cd["source_status"], cd["counts"])
    assert "resolved" not in text.casefold(), \
        f"R-D1-MERGE-03: rationale asserted an absent state — {text!r}"
    assert "discontinuation" in text.casefold()

    cr = _summary("Current", "Resolved")
    assert _chip_rationale(cr["source_status"], cr["counts"]) == \
        "The FDA reports both current and resolved shortages."

    crd = _summary("Current", "Resolved", "To Be Discontinued")
    text = _chip_rationale(crd["source_status"], crd["counts"])
    assert "resolved" in text.casefold() and "discontinuation" in text.casefold()


def test_r_d1_merge_03_every_mixture_keeps_the_d1_copy_invariants():
    """No banned economic copy, ASCII-only title, no literal None/nan, in any mixture."""
    from engine.fda_scarcity import _chip_rationale

    for statuses in (
        ("Current", "Resolved"),
        ("Current", "To Be Discontinued"),
        ("Current", "Resolved", "To Be Discontinued"),
        ("Current", "Current", "Current", "To Be Discontinued"),
    ):
        out = _summary(*statuses)
        text = _chip_rationale(out["source_status"], out["counts"])
        blob = f"{out['label']} {out['label_zh']} {text}"
        for word in BANNED:
            assert word not in blob.casefold(), (word, statuses, blob)
        assert text.isascii(), \
            "the rationale is rendered into title= and must carry no translated text"
        assert "None" not in blob and "nan" not in blob, (statuses, blob)
